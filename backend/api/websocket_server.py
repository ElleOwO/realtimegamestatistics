"""FastAPI websocket helpers for the analytics backend."""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Tracks active websocket connections and broadcasts updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

    async def broadcast(self, message: str):
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.active_connections.remove(ws)


def register_routes(app: FastAPI, manager: ConnectionManager, health_payload: dict | None = None):
    """Register health and websocket routes on the given app."""

    @app.get("/health")
    async def health_check():
        return health_payload or {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await manager.connect(ws)
        try:
            while True:
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            manager.disconnect(ws)
