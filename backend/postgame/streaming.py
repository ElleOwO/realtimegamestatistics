from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


class MatchEventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = threading.Lock()

    def bind(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, match_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        with self._lock:
            self._subscribers[match_id].add(queue)
        return queue

    def unsubscribe(self, match_id: str, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers[match_id].discard(queue)

    def publish(self, match_id: str, message_type: str, payload: dict[str, Any]) -> None:
        message = {
            "type": message_type,
            "match_id": match_id,
            "payload": payload,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            queues = list(self._subscribers.get(match_id, ()))
        if self._loop and self._loop.is_running():
            for queue in queues:
                self._loop.call_soon_threadsafe(self._put_latest, queue, message)

    @staticmethod
    def _put_latest(queue: asyncio.Queue, message: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(message)
