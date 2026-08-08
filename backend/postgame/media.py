from __future__ import annotations

import json
import mimetypes
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse


SAFE_MP4 = re.compile(r"^[^/\\\x00]+\.mp4$", re.IGNORECASE)
BROWSER_CODECS = {"h264", "av1", "vp8", "vp9"}


@dataclass(frozen=True)
class VideoMetadata:
    duration_ms: int
    codec: str
    width: int
    height: int
    fps: float


def enumerate_inbox(inbox: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in inbox.iterdir()
            if path.is_file() and SAFE_MP4.fullmatch(path.name)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def resolve_inbox_file(inbox: Path, filename: str) -> Path:
    if not SAFE_MP4.fullmatch(filename):
        raise HTTPException(status_code=400, detail="Only enumerated MP4 filenames are accepted")
    candidate = (inbox / filename).resolve()
    if candidate.parent != inbox.resolve() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Inbox file not found")
    if candidate not in enumerate_inbox(inbox):
        raise HTTPException(status_code=404, detail="Inbox file is no longer available")
    return candidate


def probe_video(path: Path) -> VideoMetadata:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,avg_frame_rate:format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
        numerator, denominator = stream.get("avg_frame_rate", "0/1").split("/", 1)
        fps = float(numerator) / max(float(denominator), 1.0)
        if duration <= 0 or int(stream["width"]) <= 0 or int(stream["height"]) <= 0:
            raise ValueError("invalid media dimensions or duration")
        return VideoMetadata(
            duration_ms=round(duration * 1000),
            codec=str(stream["codec_name"]).lower(),
            width=int(stream["width"]),
            height=int(stream["height"]),
            fps=fps,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required to import match video") from exc
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid or unreadable MP4: {path.name}") from exc


def atomic_import(source: Path, match_dir: Path) -> Path:
    match_dir.mkdir(parents=True, exist_ok=False)
    destination = match_dir / "source.mp4"
    try:
        os.replace(source, destination)
    except Exception:
        match_dir.rmdir()
        raise
    return destination


def generate_browser_proxy(source: Path, destination: Path) -> None:
    temporary = destination.with_suffix(".tmp.mp4")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        "scale=-2:min(720\\,ih)",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(temporary),
    ]
    subprocess.run(command, check=True, capture_output=True)
    os.replace(temporary, destination)


def extract_preflight_frames(source: Path, match_dir: Path, duration_ms: int) -> list[str]:
    frames_dir = match_dir / "preflight"
    frames_dir.mkdir(exist_ok=True)
    timestamps = [max(0, int(duration_ms * fraction)) for fraction in (0.08, 0.25, 0.55, 0.78)]
    relative_paths: list[str] = []
    for index, timestamp_ms in enumerate(timestamps):
        destination = frames_dir / f"cluster-preview-{index}.jpg"
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{timestamp_ms / 1000:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            "-q:v",
            "3",
            str(destination),
        ]
        subprocess.run(command, check=True, capture_output=True)
        relative_paths.append(str(destination))
    return relative_paths


def _file_chunks(path: Path, start: int, end: int, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as source:
        source.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = source.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def range_video_response(path: Path, request: Request) -> StreamingResponse:
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video is not available")
    size = path.stat().st_size
    start, end = 0, size - 1
    status_code = 200
    range_header = request.headers.get("range")
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        if not match:
            raise HTTPException(status_code=416, detail="Invalid byte range")
        raw_start, raw_end = match.groups()
        if raw_start:
            start = int(raw_start)
            end = min(int(raw_end), end) if raw_end else end
        elif raw_end:
            start = max(size - int(raw_end), 0)
        if start > end or start >= size:
            raise HTTPException(
                status_code=416,
                detail="Requested range is outside the video",
                headers={"Content-Range": f"bytes */{size}"},
            )
        status_code = 206
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(end - start + 1),
        "Content-Type": mimetypes.guess_type(path.name)[0] or "video/mp4",
    }
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        _file_chunks(path, start, end), status_code=status_code, headers=headers
    )
