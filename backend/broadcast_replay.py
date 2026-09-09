"""CPU playback of broadcast observations through the production runtime."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from broadcast_runtime import BroadcastRuntime
from live_payload import build_payload_v2
from replay_server import ReplayRuntime, load_coefficients


class BroadcastReplayRuntime(ReplayRuntime):
    def __init__(self, recording, speed=1):
        super().__init__(recording, speed)
        self.directory = tempfile.TemporaryDirectory(prefix="rtgs-broadcast-replay-")
        self.broadcast = BroadcastRuntime(Path(self.directory.name), recording.header.scenario, load_coefficients())
        self.run_id = recording.header.scenario
        self.state = "waiting"

    def step(self, item):
        with self.lock, self.broadcast.lock:
            runtime = self.broadcast
            runtime.source_ms = item.at_ms
            if item.observation is not None:
                runtime.frame(item.observation)
            elif item.command is not None:
                # Preserve reviews invalidated by a later exclusion, and command
                # ordering at a frame boundary, exactly as journal recovery does.
                runtime._append({"at_ms": item.at_ms, "command": item.command})
                if item.command.get("type") == "analysis.exclude_interval":
                    runtime._rebuild()
                else:
                    runtime._command(item.command, rebuilding=True)
            self.controller, self.engine = runtime.controller, runtime.engine
            if runtime.latest:
                self.last_frame_at = time.monotonic()
                self.frame_times.append(self.last_frame_at)
                self.latest_payload = build_payload_v2(runtime.latest, runtime.snapshot(), runtime.controller.snapshot(), runtime=self.status())
                self.new_payload.set()

    def _run(self):
        self.state = "live"
        previous = self.recording.items[0].at_ms
        for item in self.recording.items:
            if self.stopping.wait(max(0, item.at_ms - previous) / 1000 / self.speed):
                return
            self.step(item)
            previous = item.at_ms
        self.state = "finished"
        if self.latest_payload:
            self.latest_payload["runtime"] = self.status()

    def apply_command(self, command):
        try:
            self.broadcast.command(command)
            return True, None
        except (ValueError, TypeError, KeyError):
            return False, "Invalid broadcast command"

    def status(self):
        return {**self._runtime_status(self.state), "source_provider": "canadawest",
                "teams_confirmed": self.broadcast.teams_confirmed,
                "analysis_state": "analyzing" if self.broadcast.enabled else "paused"}

    def stop(self):
        super().stop()
        self.broadcast.writer.close()
        self.directory.cleanup()
