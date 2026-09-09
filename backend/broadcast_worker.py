"""Managed CanadaWest GPU worker. API starts before expensive model imports."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import threading
import tempfile
import time
import zipfile
from collections import deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from broadcast_runtime import BroadcastRuntime
from live_payload import build_payload_v2
from live_sessions import validate_artifacts


class BroadcastWorker:
    def __init__(self, root: Path, run_id: str):
        self.root, self.run_id = root, run_id
        coeffs = json.loads(Path(__file__).with_name("xg_coeffs.json").read_text())
        self.runtime = BroadcastRuntime(root, run_id, {k: float(coeffs[k]) for k in ("intercept", "distance", "angle")})
        self.state, self.error = "waiting", None
        self.deadline = float(os.environ.get("RTGS_SESSION_DEADLINE") or time.time() + 10800)
        self.stop_event = threading.Event()
        self.thread = self.source = None
        self.preview = None
        self.preview_at = 0
        self.frames = deque(maxlen=120)
        self.processing_ms = self.queue_ms = self.last_frame_at = None
        self.last_export = 0
        self.lock = threading.RLock()
        self.finalized = False
        self.resume_delay_ms = 0
        self.preview_timestamp_ms = None
        self.clips_ready = set()

    def start(self):
        with self.lock:
            if self.thread is not None:
                return
            self.thread = threading.Thread(target=self._run, daemon=True, name="broadcast-analysis")
            self.thread.start()

    def _run(self):
        try:
            from canadawest import CanadaWestConnector
            from broadcast_source import BroadcastSource
            from live_vision import BroadcastVision
            from packet_ring import PacketRing
            import cv2

            self.state = "calibrating"
            vision = BroadcastVision(os.environ.get("ROBOFLOW_API_KEY", ""))
            vision.frame_id = self.runtime.latest.frame_id if self.runtime.latest else 0
            ring = PacketRing(self.root)
            connector = CanadaWestConnector(os.environ["RTGS_CANADAWEST_EVENT_URL"],
                                           os.environ.get("RTGS_CANADAWEST_EMAIL", ""),
                                           os.environ.get("RTGS_CANADAWEST_PASSWORD", ""))
            if self.runtime.latest:
                self.runtime.command({"type": "analysis.invalidate_teams"})
            self.source = BroadcastSource(connector, start_ms=self.runtime.source_ms + self.resume_delay_ms + 1, ring=ring)
            self.source.start()
            next_frame = 0
            seen_events = {e["id"] for e in self.runtime.engine.events}
            while not self.stop_event.is_set() and time.time() < self.deadline:
                frame = self.source.read()
                if frame is None:
                    self.state = self.source.state
                    self.error = self.source.error
                    continue
                if frame.timestamp_ms < next_frame and not frame.discontinuity:
                    continue
                next_frame = frame.timestamp_ms + 100
                started = time.monotonic()
                self.queue_ms = max(0, (started - frame.arrived_at) * 1000)
                observation, preview, calibrated = vision.process(frame.image, frame.timestamp_ms, frame.discontinuity)
                self.runtime.frame(observation, gap=frame.discontinuity or vision.scene_changed)
                self.clips_ready = {p.stem for p in (self.root / "live-clips").glob("*.mp4")}
                self.state, self.error = ("live" if calibrated else "calibrating"), None
                self.last_frame_at = time.monotonic()
                self.frames.append(self.last_frame_at)
                self.processing_ms = (self.last_frame_at - started) * 1000
                if time.monotonic() - self.preview_at >= .5:
                    height, width = preview.shape[:2]
                    small = cv2.resize(preview, (720, max(1, round(height * 720 / width))))
                    ok, encoded = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok:
                        self.preview = encoded.tobytes()
                        self.preview_at = time.monotonic()
                        self.preview_timestamp_ms = frame.timestamp_ms
                with self.runtime.lock:
                    for event in self.runtime.engine.events:
                        if event["type"] == "shot" and event["id"] not in seen_events:
                            ring.preserve(event["id"], event["timestamp_ms"])
                            seen_events.add(event["id"])
                    if self.runtime.controller.snapshot()["phase"] == "full_time":
                        self.stop_event.set()
                if time.monotonic() - self.last_export >= 60:
                    self.runtime.export()
                    self.last_export = time.monotonic()
                    self.clips_ready = {p.stem for p in (self.root / "live-clips").glob("*.mp4")}
            self.state = "finished"
        except Exception:
            self.state, self.error = "interrupted", "Analysis worker failed. Check GPU/model readiness and resume the session."
        finally:
            try:
                if self.source:
                    self.source.close()
                self.runtime.export()
                self.finalized = True
            except Exception:
                self.state, self.error = "interrupted", "Finalization failed; the last checkpoint is retained."

    def status(self):
        now = time.monotonic()
        state = self.source.state if self.source and self.source.state != "live" and self.state not in {"finished", "interrupted"} else self.state
        if state == "interrupted":
            state = "stalled"
        return {"run_id": self.run_id, "mode": "live", "source_state": state,
                "session_state": self.state, "source_provider": "canadawest",
                "analysis_state": "analyzing" if self.runtime.enabled else "paused",
                "teams_confirmed": self.runtime.teams_confirmed, "source_playhead_ms": self.runtime.source_ms,
                "broadcast_delay_ms": None, "queue_delay_ms": self.queue_ms,
                "dropped_frames": self.source.dropped if self.source else 0,
                "reconnect_count": self.source.reconnects if self.source else 0,
                "inference_fps": sum(now - t <= 2 for t in self.frames) / 2,
                "payload_fps": sum(now - t <= 2 for t in self.frames) / 2,
                "processing_latency_ms": self.processing_ms,
                "last_frame_age_ms": (now - self.last_frame_at) * 1000 if self.last_frame_at else None,
                "deadline": self.deadline, "finalized": self.finalized,
                "preview_timestamp_ms": self.preview_timestamp_ms,
                "clips_ready": sorted(self.clips_ready),
                "error": self.error or (self.source.error if self.source else None),
                "match": self.runtime.controller.snapshot()}

    def payload(self):
        with self.runtime.lock:
            if self.runtime.latest is None:
                return None
            return build_payload_v2(observation=self.runtime.latest, analytics=self.runtime.snapshot(),
                                    match_state=self.runtime.controller.snapshot(), runtime=self.status())

    def request_stop(self):
        self.stop_event.set()
        if self.source:
            self.source.stop_event.set()
        if self.thread is None:
            self.runtime.export()
            self.state, self.finalized = "finished", True

    def stop(self):
        self.request_stop()
        if self.thread:
            self.thread.join(timeout=75)
            if self.thread.is_alive():
                raise RuntimeError("Worker has not stopped yet.")
        self.state = "finished"
        self.runtime.export()

    def archive(self):
        with self.runtime.lock:
            self.runtime.export()
            output = self.root / "live-artifacts.zip"
            temporary = output.with_suffix(".tmp")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for name in ("timeline.jsonl", "observations.jsonl.gz", "run-summary.json"):
                    archive.write(self.root / name, name)
                for path in (self.root / "live-clips").glob("*.mp4"):
                    archive.write(path, f"event-clips/{path.name}")
            temporary.replace(output)
            return output


def create_app(worker: BroadcastWorker):
    @asynccontextmanager
    async def lifespan(app):
        if os.environ.get("RTGS_WORKER_MANAGED") != "1":
            worker.start()
        yield
        await asyncio.to_thread(worker.stop)

    app = FastAPI(lifespan=lifespan)

    @app.get("/health/live")
    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/health/ready")
    def ready():
        status = worker.status()
        ok = status["source_state"] == "live" and status["last_frame_age_ms"] is not None and status["last_frame_age_ms"] < 3000
        from fastapi.responses import JSONResponse
        return JSONResponse({"ready": ok, **status}, status_code=200 if ok else 503)

    @app.get("/api/live/status")
    def status():
        return worker.status()

    @app.post("/api/live/start")
    def start():
        worker.start()
        return worker.status()

    @app.post("/api/live/stop")
    def stop():
        worker.request_stop()
        return worker.status()

    @app.post("/api/live/deadline")
    def deadline(payload: dict):
        value = payload.get("deadline")
        if not isinstance(value, (int, float)) or not time.time() < value <= time.time() + 86400:
            raise HTTPException(400, "Invalid session deadline")
        worker.deadline = value
        return {"ok": True}

    @app.post("/api/live/restore")
    def restore(payload: dict):
        if worker.thread is not None:
            raise HTTPException(409, "Worker has already started")
        try:
            data = base64.b64decode(payload["archive"], validate=True)
            validate_artifacts(data)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                summary = json.loads(archive.read("run-summary.json")) if "run-summary.json" in archive.namelist() else {}
                if summary.get("run_id") != worker.run_id:
                    raise ValueError("Recovery archive belongs to a different run")
                # Prove journal recovery before replacing the working state.
                with tempfile.TemporaryDirectory(prefix="rtgs-restore-") as directory:
                    candidate_root = Path(directory)
                    (candidate_root / "timeline.jsonl").write_bytes(archive.read("timeline.jsonl"))
                    candidate = BroadcastRuntime(candidate_root, worker.run_id, worker.runtime.coeffs)
                    candidate.writer.close()
                worker.resume_delay_ms = max(0, round((time.time() - summary.get("last_observed_at", time.time())) * 1000))
                worker.runtime.writer.close()
                temporary = worker.runtime.path.with_suffix(".restore")
                temporary.write_bytes(archive.read("timeline.jsonl"))
                temporary.replace(worker.runtime.path)
                for name in archive.namelist():
                    if name.startswith("event-clips/") and name.endswith(".mp4"):
                        import uuid
                        try:
                            clip_id = str(uuid.UUID(Path(name).stem))
                        except ValueError:
                            continue
                        destination = worker.root / "live-clips" / f"{clip_id}.mp4"
                        destination.parent.mkdir(exist_ok=True)
                        destination.write_bytes(archive.read(name))
            worker.runtime = BroadcastRuntime(worker.root, worker.run_id, worker.runtime.coeffs)
        except Exception:
            raise HTTPException(400, "Invalid recovery archive") from None
        return {"ok": True}

    @app.get("/api/live/preview")
    def preview():
        if worker.preview is None:
            raise HTTPException(503, "Preview not ready")
        return Response(worker.preview, media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-RTGS-Source-Time-Ms": str(worker.preview_timestamp_ms or 0)})

    @app.get("/api/live/artifacts")
    def artifacts():
        return FileResponse(worker.archive(), filename=f"{worker.run_id}.zip")

    @app.get("/api/live/clips/{event_id}")
    def clip(event_id: str):
        import uuid
        try:
            name = str(uuid.UUID(event_id))
        except ValueError:
            raise HTTPException(404)
        path = worker.root / "live-clips" / f"{name}.mp4"
        if not path.exists():
            raise HTTPException(404, "Clip is not available yet")
        return FileResponse(path)

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        await ws.accept()
        send_lock = asyncio.Lock()
        async def send(value):
            async with send_lock:
                await ws.send_json(value)
        async def publish():
            while True:
                payload = await asyncio.to_thread(worker.payload)
                if payload:
                    await send(payload)
                await asyncio.sleep(.1)
        task = asyncio.create_task(publish())
        try:
            while True:
                command = await ws.receive_json()
                command_id = command.get("command_id") if isinstance(command, dict) else None
                try:
                    await asyncio.to_thread(worker.runtime.command, command)
                    if worker.runtime.controller.snapshot()["phase"] == "full_time":
                        worker.request_stop()
                    await send({"type": "command.ack", "command_id": command_id, "ok": True})
                except (ValueError, KeyError, TypeError):
                    await send({"type": "command.ack", "command_id": command_id, "ok": False,
                                        "error": "Invalid command. Confirm team colors and check the selected interval."})
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await task

    return app


if __name__ == "__main__":
    import uvicorn
    worker = BroadcastWorker(Path(os.environ.get("RTGS_DATA_DIR", "data/broadcast")), os.environ.get("RTGS_RUN_ID", "broadcast-local"))
    uvicorn.run(create_app(worker), host="0.0.0.0", port=8001)
