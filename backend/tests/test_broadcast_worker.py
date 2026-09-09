from fastapi.testclient import TestClient

from broadcast_worker import BroadcastWorker, create_app
from test_broadcast_runtime import frame, enable


def test_worker_api_starts_without_gpu_and_exports_recoverable_state(tmp_path, monkeypatch):
    monkeypatch.setenv("RTGS_WORKER_MANAGED", "1")
    worker = BroadcastWorker(tmp_path / "first", "same-run")
    enable(worker.runtime)
    worker.runtime.frame(frame(100))
    with TestClient(create_app(worker)) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "analysis.set_enabled", "payload": {"enabled": False}, "command_id": "pause"})
            for _ in range(10):
                message = ws.receive_json()
                if message.get("type") == "command.ack":
                    assert message["ok"]
                    break
            else:
                raise AssertionError("Missing command acknowledgement")
        archive = client.get("/api/live/artifacts")
        assert archive.status_code == 200
        assert client.post("/api/live/stop").json()["finalized"]
    import base64
    recovered = BroadcastWorker(tmp_path / "second", "same-run")
    with TestClient(create_app(recovered)) as client:
        result = client.post("/api/live/restore", json={"archive": base64.b64encode(archive.content).decode()})
        assert result.status_code == 200
        assert recovered.runtime.snapshot() == worker.runtime.snapshot()
        assert not recovered.runtime.enabled
        assert recovered.runtime.latest.timestamp_ms == 100
