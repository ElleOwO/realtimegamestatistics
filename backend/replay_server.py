"""CPU-only live WebSocket server driven by canonical observations."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager, suppress
from dataclasses import replace
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from analytics_core import AnalyticsEngine, FrameObservation
from live_payload import build_payload_v2
from live_state import LiveMatchController
from observation_io import ObservationRecording, read_recording
from replay_scenarios import get_scenario


def load_coefficients() -> dict[str, float]:
    coeffs = {"intercept": 0.6, "distance": -0.18, "angle": 3.0}
    try:
        value = json.loads((Path(__file__).parent / "xg_coeffs.json").read_text())
        coeffs.update({key: float(value[key]) for key in coeffs if key in value})
    except (OSError, ValueError, KeyError):
        pass
    return coeffs


class ReplayRuntime:
    def __init__(self, recording: ObservationRecording, speed: float = 1.0):
        frames = recording.frames
        if not frames:
            raise ValueError("Replay requires at least one frame")
        self.recording = recording
        self.frames = frames
        self.commands = tuple(item for item in recording.items if item.command is not None)
        self.speed = max(speed, 0.1)
        self.controller = LiveMatchController()
        self.engine = AnalyticsEngine(load_coefficients())
        self.run_id = f"replay-{uuid.uuid4().hex[:10]}"
        self.index = 0
        self.command_index = 0
        self.latest_payload: dict[str, Any] | None = None
        self.last_frame_at: float | None = None
        self.frame_times: deque[float] = deque(maxlen=100)
        self.lock = threading.RLock()
        self.new_payload = threading.Event()
        self.stopping = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stopping.clear()
        self.thread = threading.Thread(target=self._run, name="rtgs-replay", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stopping.set()
        self.new_payload.set()
        if self.thread:
            self.thread.join(timeout=3)

    def _runtime_status(self, state: str) -> dict[str, Any]:
        now = time.monotonic()
        recent = [sample for sample in self.frame_times if now - sample <= 2]
        return {
            "run_id": self.run_id,
            "mode": "replay",
            "source_state": state,
            "inference_fps": round(len(recent) / 2, 2),
            "payload_fps": round(len(recent) / 2, 2),
            "processing_latency_ms": 0.0,
            "last_frame_age_ms": round((now - self.last_frame_at) * 1000) if self.last_frame_at else None,
            "reconnect_count": 0,
        }

    def _publish(self, source: FrameObservation, source_state: str) -> None:
        match_state = self.controller.snapshot()
        observation = replace(
            source,
            match_clock_s=float(match_state["clock_s"]),
            period=match_state["period"],
            phase=match_state["phase"],
        )
        started = time.monotonic()
        directions = self.controller.directions()
        analytics = self.engine.update(observation, directions)
        self.last_frame_at = time.monotonic()
        self.frame_times.append(self.last_frame_at)
        runtime = self._runtime_status(source_state)
        runtime["processing_latency_ms"] = round((self.last_frame_at - started) * 1000, 2)
        self.latest_payload = build_payload_v2(observation, analytics, match_state, runtime=runtime)
        self.new_payload.set()

    def _run(self) -> None:
        last_heartbeat = 0.0
        while not self.stopping.is_set():
            with self.lock:
                self._apply_recorded_commands(self.frames[self.index].timestamp_ms)
            state = self.controller.snapshot()
            phase = state["phase"]
            if phase not in ("first_half", "second_half"):
                if time.monotonic() - last_heartbeat >= 1:
                    with self.lock:
                        self._publish(self.frames[min(self.index, len(self.frames) - 1)], "waiting" if phase == "pregame" else "stalled")
                    last_heartbeat = time.monotonic()
                self.stopping.wait(0.05)
                continue
            with self.lock:
                self._publish(self.frames[self.index], "live")
                current = self.frames[self.index]
                following = self.frames[self.index + 1] if self.index + 1 < len(self.frames) else None
                self.index += 1
                if self.index >= len(self.frames):
                    self.controller.apply({"type": "match.set_phase", "payload": {"phase": "full_time"}})
                    self.index = len(self.frames) - 1
            delay = max(((following.timestamp_ms - current.timestamp_ms) / 1000) / self.speed, 0.01) if following else 0.1
            self.stopping.wait(min(delay, 2.0))

    def _apply_recorded_commands(self, through_ms: int) -> None:
        while self.command_index < len(self.commands):
            item = self.commands[self.command_index]
            if item.at_ms > through_ms:
                return
            self.command_index += 1
            command = item.command or {}
            if command.get("type") == "event.review":
                # Event IDs are intentionally regenerated on replay; reviews
                # remain operator-driven instead of guessing an event match.
                continue
            _ok, _error, reset_metrics = self.controller.apply(command)
            if reset_metrics:
                self.engine.reset()

    def apply_command(self, command: dict[str, Any]) -> tuple[bool, str | None]:
        with self.lock:
            if command.get("type") == "event.review":
                payload = command.get("payload") or {}
                ok = self.engine.review_event(str(payload.get("event_id", "")), payload, self.controller.directions())
                return ok, None if ok else "event not found"
            ok, error, reset_metrics = self.controller.apply(command)
            if reset_metrics:
                self.engine.reset()
                self.index = 0
                self.command_index = 0
            return ok, error

    def status(self) -> dict[str, Any]:
        with self.lock:
            phase = self.controller.snapshot()["phase"]
            source_state = "live" if phase in ("first_half", "second_half") else "waiting"
            return self._runtime_status(source_state)


def create_app(recording: ObservationRecording | None = None, speed: float = 1.0) -> FastAPI:
    runtime = ReplayRuntime(recording or get_scenario("standard"), speed=speed)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        runtime.start()
        yield
        runtime.stop()

    app = FastAPI(title="RTGS Replay API", version="1.0.0", lifespan=lifespan)
    app.state.runtime = runtime

    @app.get("/health")
    @app.get("/health/live")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "service": "replay", **runtime.status()}

    @app.get("/health/ready")
    async def ready() -> dict[str, Any]:
        status = runtime.status()
        return {"status": "ok" if runtime.latest_payload else "starting", **status}

    @app.get("/api/live/status")
    async def live_status() -> dict[str, Any]:
        return runtime.status()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        send_lock = asyncio.Lock()
        last_payload: str | None = None

        async def send(value: dict[str, Any]) -> None:
            async with send_lock:
                await websocket.send_text(json.dumps(value))

        async def stream_payloads() -> None:
            nonlocal last_payload
            while True:
                payload = runtime.latest_payload
                if payload is not None:
                    serialized = json.dumps(payload)
                    if serialized != last_payload:
                        async with send_lock:
                            await websocket.send_text(serialized)
                        last_payload = serialized
                await asyncio.sleep(0.02)

        sender = asyncio.create_task(stream_payloads())
        try:
            while True:
                raw = await websocket.receive_text()
                command_id = None
                try:
                    command = json.loads(raw)
                    command_id = command.get("command_id")
                    ok, error = runtime.apply_command(command)
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    ok, error = False, str(exc)
                await send({
                    "type": "command.ack", "command_id": command_id, "ok": ok, "error": error,
                })
        except WebSocketDisconnect:
            pass
        finally:
            sender.cancel()
            with suppress(asyncio.CancelledError):
                await sender

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RTGS without video or GPU dependencies")
    parser.add_argument("--recording", type=Path)
    parser.add_argument("--scenario", default=os.environ.get("RTGS_REPLAY_SCENARIO", "standard"))
    parser.add_argument("--speed", type=float, default=float(os.environ.get("RTGS_REPLAY_SPEED", "1")))
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    recording = read_recording(args.recording) if args.recording else get_scenario(args.scenario)
    uvicorn.run(create_app(recording, speed=args.speed), host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
