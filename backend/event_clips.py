"""Bounded encoded-video ring buffer for live event diagnostics."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path


SAFE_ID = re.compile(r"[^a-zA-Z0-9_-]+")


class EncodedClipBuffer:
    """Keep a short segment ring and preserve only windows around events."""

    def __init__(self, stream_url: str, data_root: Path, segment_seconds: int = 2, buffer_seconds: int = 120):
        self.stream_url = stream_url
        self.root = data_root / "live-clips"
        self.ring = self.root / ".ring"
        self.segment_seconds = max(segment_seconds, 1)
        self.segment_count = max(buffer_seconds // self.segment_seconds, 10)
        self.process: subprocess.Popen[bytes] | None = None
        self.stopping = threading.Event()

    def start(self) -> None:
        self.ring.mkdir(parents=True, exist_ok=True)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "warning"]
        if self.stream_url.lower().startswith(("rtsp://", "rtsps://")):
            command += ["-rtsp_transport", "tcp"]
        command += [
            "-i", self.stream_url,
            "-map", "0:v:0", "-c", "copy", "-an",
            "-f", "segment", "-segment_time", str(self.segment_seconds),
            "-segment_wrap", str(self.segment_count), "-reset_timestamps", "1",
            str(self.ring / "segment-%06d.ts"),
        ]
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def preserve(self, event_id: str, before_seconds: int = 10, after_seconds: int = 10) -> None:
        safe_id = SAFE_ID.sub("-", event_id).strip("-")[:80] or f"event-{int(time.time())}"
        threading.Thread(
            target=self._preserve_after_delay,
            args=(safe_id, before_seconds, after_seconds),
            name=f"clip-{safe_id}",
            daemon=True,
        ).start()

    def _preserve_after_delay(self, event_id: str, before_seconds: int, after_seconds: int) -> None:
        requested_at = time.time()
        if self.stopping.wait(after_seconds):
            return
        earliest = requested_at - before_seconds
        latest = requested_at + after_seconds + self.segment_seconds
        candidates = sorted(
            (path for path in self.ring.glob("segment-*.ts") if earliest <= path.stat().st_mtime <= latest),
            key=lambda path: path.stat().st_mtime,
        )
        if not candidates:
            return
        staging = self.root / f".{event_id}-parts"
        staging.mkdir(parents=True, exist_ok=True)
        copies: list[Path] = []
        for index, source in enumerate(candidates):
            destination = staging / f"{index:04d}.ts"
            shutil.copy2(source, destination)
            copies.append(destination)
        concat = staging / "concat.txt"
        concat.write_text("".join(f"file '{path.name}'\n" for path in copies))
        destination = self.root / f"{event_id}.mp4"
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(destination)],
            cwd=staging,
            capture_output=True,
        )
        shutil.rmtree(staging, ignore_errors=True)
        if result.returncode != 0:
            destination.unlink(missing_ok=True)

    def stop(self) -> None:
        self.stopping.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        shutil.rmtree(self.ring, ignore_errors=True)


def configured_clip_buffer(stream_url: str | None) -> EncodedClipBuffer | None:
    if not stream_url or os.environ.get("RTGS_EVENT_CLIPS", "1").lower() not in {"1", "true", "yes"}:
        return None
    data_root = Path(os.environ.get("RTGS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
    return EncodedClipBuffer(stream_url, data_root)
