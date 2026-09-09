"""Durable, single-match RunPod lifecycle. No CV dependencies or web requests in constructors."""
from __future__ import annotations

import gzip
import io
import json
import re
import secrets
import sqlite3
import threading
import time
import uuid
import zipfile
from pathlib import Path

from canadawest import validate_event_url


ACTIVE = {"starting", "waiting", "calibrating", "live", "reconnecting", "stopping"}


def validate_artifacts(data: bytes):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if "timeline.jsonl" not in archive.namelist() or "observations.jsonl.gz" not in archive.namelist():
            raise ValueError("Worker export is missing its recovery recording.")
        if sum(i.file_size for i in archive.infolist()) > 512 * 1024 * 1024:
            raise ValueError("Worker export exceeds the compact artifact limit.")
        with gzip.GzipFile(fileobj=io.BytesIO(archive.read("observations.jsonl.gz"))) as stream:
            decoded = stream.read(512 * 1024 * 1024 + 1)
        if len(decoded) > 512 * 1024 * 1024:
            raise ValueError("Observation recording is too large.")
        header = json.loads(decoded.splitlines()[0])
        if header.get("type") != "header" or header.get("schema_version") != 1:
            raise ValueError("Invalid observation recording header.")
        for line in archive.read("timeline.jsonl").splitlines():
            item = json.loads(line)
            if not isinstance(item, dict) or not isinstance(item.get("at_ms"), (int, float)):
                raise ValueError("Invalid timeline item.")
            if "observation" in item:
                from observation_io import observation_from_dict
                observation_from_dict(item["observation"])
            elif not isinstance(item.get("command"), dict):
                raise ValueError("Invalid timeline command.")


class SessionManager:
    def __init__(self, root: Path, config: dict, client, http_factory):
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)
        self.root, self.config = root, config
        self.client, self.http_factory = client, http_factory
        self.lock = threading.RLock()
        self.tick_lock = threading.Lock()
        self.db = sqlite3.connect(root / "sessions.sqlite3", check_same_thread=False)
        (root / "sessions.sqlite3").chmod(0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.commit()

    def rows(self):
        with self.lock:
            return sorted((json.loads(row[0]) for row in self.db.execute("SELECT value FROM sessions")), key=lambda row: row["created_at"], reverse=True)

    def get(self, run_id):
        return next((r for r in self.rows() if r["id"] == run_id), None)

    def save(self, row):
        with self.lock:
            current = self.get(row["id"])
            if current and current.get("control_revision", 0) > row.get("control_revision", 0):
                # Preserve Stop/Extend received while the monitor was doing I/O.
                row["deadline"] = current["deadline"]
                row["control_revision"] = current["control_revision"]
                if current["state"] == "stopping" and row["state"] != "finished":
                    row["state"] = "stopping"
            self.db.execute("INSERT INTO sessions(id,value) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (row["id"], json.dumps(row)))
            self.db.commit()

    def public(self, row):
        if not row:
            return None
        return {key: row.get(key) for key in ("id", "event_url", "state", "source_state", "error", "deadline", "created_at", "image", "artifacts_ready", "worker_started", "last_checkpoint")}

    def current(self):
        rows = self.rows()
        return next((r for r in rows if r["state"] in ACTIVE), rows[0] if rows else None)

    def start(self, event_url):
        event_url = validate_event_url(event_url)
        with self.lock:
            current = self.current()
            if current and current["state"] in ACTIVE:
                if current["event_url"] == event_url:
                    return current
                raise ValueError("End the active match before starting another.")
            if any(r.get("pod_id") or r.get("creating") for r in self.rows()):
                raise ValueError("Wait for worker cleanup before starting another match.")
            for field in ("runpod_api_key", "roboflow_api_key", "canadawest_email", "canadawest_password"):
                if not self.config.get(field):
                    raise ValueError("The administrator must configure RunPod, Roboflow, and CanadaWest credentials first.")
            image = self.config.get("gpu_image", "")
            if not re.search(r":[0-9a-f]{40}$", image):
                raise ValueError("Configure a test-passed GPU image tagged with its full commit SHA.")
            now = time.time()
            row = {"id": uuid.uuid4().hex, "event_url": event_url, "state": "starting", "created_at": now,
                   "deadline": now + 10800, "image": image, "token": secrets.token_urlsafe(32),
                   "pod_id": None, "error": None, "worker_started": False, "last_checkpoint": 0,
                   "artifacts_ready": False, "creating": False, "control_revision": 0}
            self.save(row)
            return row

    def action(self, run_id, action):
        with self.lock:
            row = self.get(run_id)
            if not row:
                raise ValueError("Session not found.")
            if action == "stop":
                if row["state"] not in {"finished", "failed"}:
                    row["state"] = "stopping"
            elif action == "extend":
                if row["state"] not in ACTIVE or row["state"] == "stopping":
                    raise ValueError("Only an active session can be extended.")
                row["deadline"] = max(time.time(), row["deadline"]) + 3600
            elif action == "resume":
                if row["state"] not in {"interrupted", "failed"} or row.get("pod_id") or row.get("creating"):
                    raise ValueError("Wait for the failed worker to be cleaned up before resuming.")
                if any(r["state"] in ACTIVE for r in self.rows()):
                    raise ValueError("Another session is active.")
                row.update(state="starting", creating=False, worker_started=False, created_at=time.time(),
                           deadline=time.time() + 10800, error=None, token=secrets.token_urlsafe(32))
                row.pop("stop_started_at", None)
                row.pop("last_seen", None)
            else:
                raise ValueError("Unsupported session action.")
            row["control_revision"] = row.get("control_revision", 0) + 1
            self.save(row)
            return row

    def http(self, row):
        if not row or not row.get("pod_id"):
            raise ValueError("Worker is starting.")
        return self.http_factory(f"https://{row['pod_id']}-8080.proxy.runpod.net", row["token"])

    def artifact_path(self, row):
        return self.root / f"{row['id']}.zip"

    def checkpoint(self, row):
        path = self.artifact_path(row)
        temporary = path.with_suffix(".tmp")
        self.http(row).download("/api/live/artifacts", temporary)
        validate_artifacts(temporary.read_bytes())
        temporary.replace(path)
        row.update(last_checkpoint=time.time(), artifacts_ready=True)

    def tick(self):
        # Network I/O never holds the database/UI lock. Only one monitor runs.
        with self.tick_lock:
            for row in self.rows():
                self._tick(row)

    def _tick(self, row):
        now = time.time()
        if row["state"] in ACTIVE and now >= row["deadline"]:
            row["state"] = "stopping"
        if row["state"] in {"finished", "failed", "interrupted"} and not row.get("pod_id") and not row.get("creating"):
            return
        try:
            if row.get("creating") and not row.get("pod_id"):
                matches = [p for p in self.client.pods() if p.get("name") == f"rtgs-{row['id']}"]
                if matches:
                    row.update(pod_id=matches[0]["id"], creating=False)
                    self.save(row)
                    for extra in matches[1:]:
                        self.client.delete(extra["id"])
                else:
                    if now - row.get("create_at", now) > 900:
                        row.update(state="failed", creating=False, error="Pod creation was not confirmed after 15 minutes. Check RunPod before retrying.")
                    return
            if row["state"] == "stopping":
                if row.get("pod_id"):
                    row.setdefault("stop_started_at", now)
                    try:
                        status = self.http(row).request("POST", "/api/live/stop", {}, timeout=5)
                        if not status.get("finalized", False):
                            if now - row["stop_started_at"] < 120:
                                return
                            raise TimeoutError("Finalization timed out")
                        self.checkpoint(row)
                    except Exception:
                        if now - row["stop_started_at"] < 120:
                            return
                        row["error"] = "Final export unavailable; the last saved checkpoint was retained."
                    self.client.delete(row["pod_id"])
                row.update(state="finished", pod_id=None, creating=False)
            elif row["state"] in {"interrupted", "failed"}:
                self.client.delete(row["pod_id"])
                row.update(pod_id=None, creating=False)
            elif not row.get("pod_id"):
                row.update(creating=True, create_at=now)
                self.save(row)
                config = {**self.config, "gpu_image": row["image"], "canadawest_event_url": row["event_url"], "session_deadline": row["deadline"]}
                pod = self.client.create(config, "live", row["id"], row["token"])
                row.update(pod_id=pod["id"], creating=False)
                self.save(row)  # Persist ownership before any readiness request.
            else:
                http = self.http(row)
                if not row["worker_started"]:
                    http.request("GET", "/healthz/live", timeout=5)
                    path = self.artifact_path(row)
                    if path.exists():
                        import base64
                        http.request("POST", "/api/live/restore", {"archive": base64.b64encode(path.read_bytes()).decode()}, timeout=30)
                    http.request("POST", "/api/live/start", {}, timeout=10)
                    row["worker_started"] = True
                status = http.request("GET", "/api/live/status", timeout=5)
                row.update(state=status.get("session_state", "waiting"), source_state=status.get("source_state"),
                           error=status.get("error"), last_seen=now)
                if row["state"] not in ACTIVE | {"interrupted", "finished"}:
                    row["state"] = "waiting"
                if row["state"] == "finished":
                    row["state"] = "stopping"
                if now - row["last_checkpoint"] >= 60:
                    self.checkpoint(row)
                if status.get("deadline") != row["deadline"]:
                    http.request("POST", "/api/live/deadline", {"deadline": row["deadline"]}, timeout=5)
        except Exception:
            # Provider exceptions may include credentials; never persist raw messages.
            row["error"] = "Worker is unavailable; retrying and checking cleanup."
            if row.get("pod_id") and row["state"] not in {"stopping", "interrupted", "failed"}:
                limit = 900 if not row["worker_started"] else 90
                if now - row.get("last_seen", row["created_at"]) > limit:
                    row["state"] = "interrupted"
        finally:
            self.save(row)
