import gzip
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from control_server import create_app
from live_sessions import SessionManager


class Client:
    def __init__(self):
        self.created = []
        self.deleted = []

    def create(self, config, mode, run_id, token):
        self.created.append(run_id)
        return {"id": "pod-one"}

    def delete(self, pod_id):
        self.deleted.append(pod_id)

    def pods(self):
        return []


class HTTP:
    fails = False
    requests = []
    def __init__(self, *args):
        pass

    def request(self, method, path, payload=None, timeout=None):
        self.requests.append(path)
        if self.fails:
            raise RuntimeError("private URL must not escape")
        return {"session_state": "live", "source_state": "live", "finalized": path == "/api/live/stop"}

    def download(self, path, destination):
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("timeline.jsonl", "")
            archive.writestr("observations.jsonl.gz", gzip.compress(b'{"type":"header","schema_version":1}\n'))


def manager(tmp_path):
    config = {"gpu_image": "ghcr.io/example/rtgs:" + "a" * 40,
              "runpod_api_key": "fake", "roboflow_api_key": "fake",
              "canadawest_email": "fake", "canadawest_password": "fake"}
    return SessionManager(tmp_path, config, Client(), HTTP)


def test_start_is_idempotent_and_one_match_only(tmp_path):
    m = manager(tmp_path)
    first = m.start("https://canadawest.tv/events/123")
    assert first["id"] == m.start(first["event_url"])["id"]
    with pytest.raises(ValueError):
        m.start("https://canadawest.tv/events/456")
    m.tick()
    assert len(m.client.created) == 1
    m.tick()
    assert m.current()["state"] == "live"
    assert m.current()["artifacts_ready"]
    m.action(first["id"], "stop")
    m.tick()
    assert m.client.deleted == ["pod-one"]
    assert m.current()["state"] == "finished"


def test_startup_timeout_keeps_cleanup_ownership(tmp_path, monkeypatch):
    m = manager(tmp_path)
    row = m.start("https://canadawest.tv/events/123")
    m.tick()
    monkeypatch.setattr(HTTP, "fails", True)
    monkeypatch.setattr("live_sessions.time.time", lambda: row["created_at"] + 950)
    m.tick()
    assert m.current()["state"] == "interrupted"
    m.tick()
    assert m.client.deleted == ["pod-one"]
    assert "private" not in m.current()["error"]


def test_controller_restart_recovers_active_pod_and_expiry(tmp_path, monkeypatch):
    m = manager(tmp_path)
    row = m.start("https://canadawest.tv/events/123")
    m.tick()
    resumed = manager(tmp_path)
    assert resumed.current()["pod_id"] == "pod-one"
    monkeypatch.setattr("live_sessions.time.time", lambda: row["deadline"] + 1)
    resumed.tick()
    assert resumed.client.deleted == ["pod-one"]


def test_web_contract_hides_secrets_and_rejects_cross_origin(tmp_path):
    m = manager(tmp_path)
    with TestClient(create_app(m, monitor=False)) as client:
        result = client.post("/api/live/sessions", json={"event_url": "https://canadawest.tv/events/123"})
        assert result.status_code == 200
        assert "token" not in result.json()
        assert "fake" not in result.text
        assert client.get("/api/live/sessions/current").json()["managed"]
        assert client.post("/api/live/sessions", json={}, headers={"Origin": "https://evil.test"}).status_code == 403


def test_resume_restores_checkpoint_before_start(tmp_path):
    m = manager(tmp_path)
    m.start("https://canadawest.tv/events/123")
    m.tick()
    m.tick()
    row = m.current()
    row["state"] = "interrupted"
    m.save(row)
    m.tick()
    m.action(row["id"], "resume")
    HTTP.requests = []
    m.tick()
    m.tick()
    assert HTTP.requests.index("/api/live/restore") < HTTP.requests.index("/api/live/start")


def test_stop_remains_responsive_during_pod_create(tmp_path):
    import threading
    m = manager(tmp_path)
    row = m.start("https://canadawest.tv/events/123")
    entered, release = threading.Event(), threading.Event()
    def create(*args):
        entered.set()
        assert release.wait(3)
        return {"id": "pod-one"}
    m.client.create = create
    monitor = threading.Thread(target=m.tick)
    monitor.start()
    assert entered.wait(1)
    try:
        assert m.action(row["id"], "stop")["state"] == "stopping"
    finally:
        release.set()
        monitor.join(3)
    assert m.current()["state"] == "stopping"
    m.tick()
    assert m.client.deleted == ["pod-one"]


def test_wait_for_final_export_before_delete(tmp_path, monkeypatch):
    m = manager(tmp_path)
    row = m.start("https://canadawest.tv/events/123")
    m.tick()
    m.action(row["id"], "stop")
    monkeypatch.setattr(HTTP, "request", lambda *args, **kwargs: {"finalized": False})
    m.tick()
    assert not m.client.deleted
    assert m.current()["state"] == "stopping"
    monkeypatch.setattr(HTTP, "request", lambda *args, **kwargs: {"finalized": True})
    m.tick()
    assert m.current()["artifacts_ready"]
    assert m.client.deleted == ["pod-one"]


def test_corrupt_checkpoint_keeps_previous_archive(tmp_path, monkeypatch):
    m = manager(tmp_path)
    m.start("https://canadawest.tv/events/123")
    m.tick()
    row = m.current()
    m.checkpoint(row)
    saved = m.artifact_path(row).read_bytes()
    monkeypatch.setattr(HTTP, "download", lambda self, path, destination: destination.write_bytes(b"broken"))
    with pytest.raises(zipfile.BadZipFile):
        m.checkpoint(row)
    assert m.artifact_path(row).read_bytes() == saved
