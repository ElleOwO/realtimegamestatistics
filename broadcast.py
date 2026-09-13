"""
Live stats broadcaster for the coach dashboard.

Pushes the latest stats payload to a Firebase Realtime Database via its REST
API. A background thread does the network I/O so it never stalls the video
loop, and updates are throttled/coalesced (only the newest payload is sent).

Configuration (environment variables):
  FIREBASE_DB_URL   Realtime DB base URL, e.g.
                    https://my-project-default-rtdb.firebaseio.com
  FIREBASE_AUTH     (optional) database secret or auth token for writes
  BROADCAST_PATH    (optional) DB path/key to write to (default: "broadcast")

If FIREBASE_DB_URL is unset, the broadcaster is a no-op, so the app runs
normally without any cloud setup.
"""

import os
import json
import time
import threading
import urllib.request
from typing import Optional


class StatsBroadcaster:
    def __init__(self, db_url: Optional[str] = None, auth: Optional[str] = None,
                 path: str = "broadcast", min_interval: float = 1.5):
        self.db_url = (db_url or "").rstrip("/")
        self.auth = auth
        self.path = path
        self.min_interval = min_interval
        self.enabled = bool(self.db_url)

        self._latest: Optional[dict] = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        if self.enabled:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            print(f"📡 Broadcasting stats to {self.db_url}/{self.path}.json")
        else:
            print("📡 Broadcast disabled (set FIREBASE_DB_URL to enable)")

    @classmethod
    def from_env(cls) -> "StatsBroadcaster":
        return cls(
            db_url=os.environ.get("FIREBASE_DB_URL"),
            auth=os.environ.get("FIREBASE_AUTH"),
            path=os.environ.get("BROADCAST_PATH", "broadcast"),
        )

    def update(self, payload: dict) -> None:
        """Set the latest payload to broadcast (cheap; safe to call per frame)."""
        if not self.enabled:
            return
        with self._lock:
            self._latest = payload

    def _endpoint(self) -> str:
        url = f"{self.db_url}/{self.path}.json"
        if self.auth:
            url += f"?auth={self.auth}"
        return url

    def _put(self, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint(), data=data, method="PUT",
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()

    def _run(self) -> None:
        last_sent: Optional[dict] = None
        while not self._stop.is_set():
            time.sleep(self.min_interval)
            with self._lock:
                payload = self._latest
            if payload is None or payload is last_sent:
                continue
            try:
                self._put(payload)
                last_sent = payload
            except Exception as exc:  # network hiccups must not crash the app
                print(f"⚠️  Broadcast failed: {exc}")

    def stop(self) -> None:
        self._stop.set()
