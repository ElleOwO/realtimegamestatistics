"""Always-on browser session API and authenticated proxy to the active GPU."""
from __future__ import annotations

import asyncio
import base64
import inspect
import os
import sys
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from live_sessions import SessionManager


def create_app(manager: SessionManager, *, monitor=True):
    @asynccontextmanager
    async def lifespan(app):
        async def watch():
            while True:
                try:
                    await asyncio.to_thread(manager.tick)
                except Exception:
                    pass  # Next pass retries persisted work; no secrets in logs.
                await asyncio.sleep(5)
        task = asyncio.create_task(watch()) if monitor else None
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        from urllib.parse import urlsplit
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and urlsplit(origin).netloc != request.headers.get("host"):
            return Response(status_code=403)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/live/sessions/current")
    def current():
        return {"managed": True, "session": manager.public(manager.current())}

    @app.post("/api/live/sessions")
    def start(payload: dict):
        try:
            return manager.public(manager.start(payload.get("event_url", "")))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    @app.post("/api/live/sessions/{run_id}/{action}")
    def action(run_id: str, action: str):
        try:
            return manager.public(manager.action(run_id, action))
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/api/live/sessions/{run_id}/artifacts")
    def archive(run_id: str):
        row = manager.get(run_id)
        if not row or not manager.artifact_path(row).exists():
            raise HTTPException(404, "No checkpoint is available yet")
        return FileResponse(manager.artifact_path(row), filename=f"rtgs-{run_id}.zip")

    @app.get("/api/live/{path:path}")
    def proxy(path: str):
        if path not in {"status", "preview"} and not path.startswith("clips/"):
            raise HTTPException(404)
        if path.startswith("clips/"):
            import uuid
            try:
                uuid.UUID(path.removeprefix("clips/"))
            except ValueError:
                raise HTTPException(404)
        try:
            result = manager.http(manager.current()).request("GET", f"/api/live/{path}", timeout=5)
        except Exception:
            raise HTTPException(503, "Worker is not ready") from None
        if isinstance(result, bytes):
            return Response(result, media_type="image/jpeg" if path == "preview" else "video/mp4", headers={"Cache-Control": "no-store"})
        return result

    @app.websocket("/ws")
    async def websocket(ws: WebSocket):
        from urllib.parse import urlsplit
        origin = ws.headers.get("origin")
        if origin and urlsplit(origin).netloc != ws.headers.get("host"):
            await ws.close(code=1008)
            return
        row = await asyncio.to_thread(manager.current)
        if not row or not row.get("pod_id") or not row.get("worker_started"):
            await ws.close(code=1013)
            return
        import websockets
        auth = "Basic " + base64.b64encode(f"rtgs:{row['token']}".encode()).decode()
        header = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
        try:
            async with websockets.connect(f"wss://{row['pod_id']}-8080.proxy.runpod.net/ws", **{header: {"Authorization": auth}}) as upstream:
                await ws.accept()
                async def incoming():
                    while True:
                        await upstream.send(await ws.receive_text())
                async def outgoing():
                    async for value in upstream:
                        await ws.send_text(value)
                tasks = [asyncio.create_task(incoming()), asyncio.create_task(outgoing())]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            with suppress(Exception):
                await ws.close(code=1013)

    return app


if __name__ == "__main__":
    import uvicorn
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts.cloud import load_config, RunPodClient, RTGSHTTP
    config = load_config()
    manager = SessionManager(Path(os.environ.get("RTGS_CONTROL_DATA_DIR", "data/control")), config,
                             RunPodClient(config.get("runpod_api_key", "")), RTGSHTTP)
    uvicorn.run(create_app(manager), host="127.0.0.1", port=8002)
