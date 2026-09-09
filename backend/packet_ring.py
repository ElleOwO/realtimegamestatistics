"""Remux the existing demuxer's packets; never open another upstream stream."""
from __future__ import annotations

import shutil
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from pathlib import Path


class PacketRing:
    def __init__(self, root: Path):
        self.root = root / "live-clips"
        self.ring = self.root / ".ring"
        shutil.rmtree(self.ring, ignore_errors=True)
        self.ring.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.parts = deque()
        self.pending = {}
        self.container = None
        self.index = self.start = self.end = 0
        self.encoder = ThreadPoolExecutor(max_workers=1, thread_name_prefix="event-clip")
        self.slots = threading.BoundedSemaphore(4)

    def write(self, packet, stream, timestamp_ms):
        import av
        with self.lock:
            if packet.is_keyframe and (self.container is None or timestamp_ms - self.start >= 2000):
                self.rotate()
                self.index += 1
                self.path = self.ring / f"{self.index:08d}.ts"
                self.container = av.open(str(self.path), "w", format="mpegts")
                self.output = self.container.add_stream_from_template(stream)
                self.start = timestamp_ms
            if self.container is not None:
                self.end = timestamp_ms
                packet.stream = self.output
                self.container.mux(packet)

    def preserve(self, event_id, timestamp_ms):
        with self.lock:
            event_id = str(uuid.UUID(event_id))
            if (self.root / f"{event_id}.mp4").exists():
                return
            self.pending[event_id] = (max(0, timestamp_ms - 10000), timestamp_ms + 10000)

    def rotate(self):
        with self.lock:
            if self.container:
                self.container.close()
                self.container = None
                self.parts.append((self.start, self.end, self.path))
                self._finish()
            while self.parts and self.parts[0][1] < self.end - 120000:
                self.parts.popleft()[2].unlink(missing_ok=True)

    def _finish(self, force=False):
        for event_id, (start, end) in list(self.pending.items()):
            if not force and self.end < end:
                continue
            parts = [p for a, b, p in self.parts if b >= start and a <= end]
            if not parts:
                continue
            if not self.slots.acquire(blocking=False):
                continue
            staging = self.ring / event_id
            try:
                staging.mkdir(exist_ok=True)
                for part in parts:
                    # Hard links retain immutable segments after ring eviction.
                    (staging / part.name).hardlink_to(part)
                self.encoder.submit(self._encode, event_id, staging, parts)
            except Exception:
                self.slots.release()
                shutil.rmtree(staging, ignore_errors=True)
            del self.pending[event_id]

    def _encode(self, event_id, staging, parts):
        temporary = self.root / f".{event_id}.partial"
        try:
            listing = staging / "concat.txt"
            listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
            result = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                                     "-i", str(listing), "-c", "copy", "-movflags", "+faststart", "-f", "mp4", str(temporary)],
                                    capture_output=True, timeout=20)
            if result.returncode == 0:
                temporary.replace(self.root / f"{event_id}.mp4")
        except (OSError, subprocess.TimeoutExpired):
            pass  # A failed clip never interrupts live analytics.
        finally:
            temporary.unlink(missing_ok=True)
            shutil.rmtree(staging, ignore_errors=True)
            self.slots.release()

    def close(self):
        with self.lock:
            self.rotate()
            self._finish(force=True)
        self.encoder.shutdown(wait=True)
        shutil.rmtree(self.ring, ignore_errors=True)
