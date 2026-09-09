"""Single upstream decoder with a bounded latest-frame handoff."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from canadawest import SourceError


@dataclass
class SourceFrame:
    image: object
    timestamp_ms: int
    arrived_at: float
    discontinuity: bool = False


class SourceTimeline:
    def __init__(self, start_ms=0):
        self.last = start_ms - 1
        self.offset = None
        self.last_raw = None

    def map(self, raw_ms: int, discontinuity=False) -> int | None:
        if self.offset is None or discontinuity:
            self.offset = self.last + 1 - raw_ms
        elif self.last_raw is not None and raw_ms < self.last_raw - 10000:
            # A reset PTS epoch, not ordinary replay of a few old packets.
            self.offset = self.last + 1 - raw_ms
        value = raw_ms + self.offset
        if value <= self.last:
            return None
        self.last_raw, self.last = raw_ms, value
        return value


class BroadcastSource:
    def __init__(self, connector, *, start_ms=0, ring=None):
        self.connector, self.ring = connector, ring
        self.timeline = SourceTimeline(start_ms)
        self.condition = threading.Condition()
        self.stop_event = threading.Event()
        self.latest = None
        self.state, self.error = "waiting", None
        self.dropped = self.reconnects = 0
        self.thread = None
        self.resume_gap = start_ms > 1

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True, name="broadcast-capture")
        self.thread.start()

    def read(self, timeout=1) -> SourceFrame | None:
        with self.condition:
            self.condition.wait_for(lambda: self.latest is not None or self.stop_event.is_set(), timeout)
            frame, self.latest = self.latest, None
            return frame

    def put(self, frame):
        with self.condition:
            if self.latest is not None:
                self.dropped += 1
                frame.discontinuity = frame.discontinuity or self.latest.discontinuity
            self.latest = frame
            self.condition.notify_all()

    def _run(self):
        attempts = 0
        last_arrival = None
        try:
            import av
            av.logging.set_level(av.logging.PANIC)  # FFmpeg diagnostics can contain signed URLs.
            while not self.stop_event.is_set():
                try:
                    self.state = "reconnecting" if attempts else "waiting"
                    playback = self.connector.refresh()
                    options = {"headers": "".join(f"{k}: {v}\r\n" for k, v in playback.headers.items()),
                               "cookies": playback.cookies, "live_start_index": "-2"}
                    with av.open(playback.url, options=options, timeout=(15, 10)) as container:
                        stream = min((s for s in container.streams.video if s.codec_context.height <= 1080),
                                     key=lambda s: -s.codec_context.height, default=None)
                        if stream is None:
                            stream = container.streams.video[0]
                        self.state, self.error = "live", None
                        first = True
                        for packet in container.demux(stream):
                            if self.stop_event.is_set():
                                break
                            frames = packet.decode()
                            for decoded in frames:
                                if decoded.pts is None:
                                    continue
                                raw_ms = round(float(decoded.pts * decoded.time_base) * 1000)
                                now = time.monotonic()
                                reset_epoch = self.timeline.last_raw is not None and raw_ms < self.timeline.last_raw - 10000
                                changed = (first and (attempts > 0 or self.resume_gap)) or reset_epoch
                                if reset_epoch and last_arrival is not None:
                                    self.timeline.last += round((now - last_arrival) * 1000)
                                # A reopened HLS playlist often repeats segments. Keep
                                # the existing PTS mapping and reject overlaps.
                                timestamp = self.timeline.map(raw_ms)
                                if timestamp is None:
                                    continue
                                first = False
                                last_arrival = now
                                self.put(SourceFrame(decoded.to_ndarray(format="bgr24"), timestamp, now, changed))
                            if self.ring is not None and not first and packet.size and packet.pts is not None:
                                self.ring.write(packet, stream, self.timeline.last)
                        if not self.stop_event.is_set():
                            raise SourceError("Broadcast ended or interrupted. Waiting for playback to resume.")
                except Exception as exc:
                    self.error = str(exc) if isinstance(exc, SourceError) else "Broadcast connection interrupted. Retrying playback."
                    self.state = "reconnecting" if attempts else "waiting"
                    attempts += 1
                    self.reconnects = attempts
                    if self.ring:
                        self.ring.rotate()
                    self.stop_event.wait(min(2 ** min(attempts, 5), 30))
        except Exception:
            self.state, self.error = "interrupted", "Video decoder failed. Check the worker image and resume."
        finally:
            self.connector.close()
            if self.ring:
                self.ring.close()

    def close(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread:
            self.thread.join(timeout=70)
            if self.thread.is_alive():
                raise RuntimeError("The upstream capture has not stopped yet.")
