from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from analytics_core import AnalyticsEngine
from observation_io import read_recording, write_recording
from replay_scenarios import standard_recording
from replay_server import create_app as create_replay_app
from postgame.shared_adapter import AnalyticsBatchAdapter
from postgame.api import create_app as create_postgame_app
from postgame.config import Settings
from postgame.database import Database


def test_recording_round_trip_is_compact_and_video_free(tmp_path) -> None:
    recording = standard_recording()
    path = tmp_path / "standard.jsonl.gz"
    write_recording(path, recording.header, recording.items)
    loaded = read_recording(path)
    assert loaded.header.scenario == "standard"
    assert len(loaded.frames) == len(recording.frames)
    assert path.stat().st_size < 10_000
    raw = path.read_bytes()
    assert b"image_box" not in raw


def test_shared_adapter_emits_expected_replay_events() -> None:
    recording = standard_recording()
    adapter = AnalyticsBatchAdapter(AnalyticsEngine({"intercept": 0.6, "distance": -0.18, "angle": 3.0}))
    events = []
    for observation in recording.frames:
        batch = adapter.update(observation, {"team0": "right", "team1": "left"})
        events.extend(batch.events)
    assert any(event["type"] == "final_third_entry" for event in events)
    assert any(event["type"] == "shot" and event["team"] == "home" for event in events)
    assert all(event["review_status"] == "pending" for event in events)


def test_replay_websocket_accepts_operator_phase_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RTGS_DATA_DIR", str(tmp_path))
    app = create_replay_app(standard_recording(), speed=1)
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                initial = json.loads(websocket.receive_text())
                assert initial["schema_version"] == 2
                assert initial["runtime"]["mode"] == "replay"
                websocket.send_text(json.dumps({
                    "type": "match.set_phase",
                    "command_id": "phase-1",
                    "payload": {"phase": "first_half"},
                }))
                for _ in range(10):
                    acknowledgement = json.loads(websocket.receive_text())
                    if acknowledgement.get("type") == "command.ack":
                        break
                assert acknowledgement == {
                    "type": "command.ack", "command_id": "phase-1", "ok": True, "error": None,
                }
    finally:
        app.state.runtime.stop()


def test_test_mode_scenario_runs_postgame_without_video(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RTGS_TEST_TOKEN", "top-secret")
    settings = Settings(
        data_root=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'replay.sqlite3'}",
        mode="test",
        artifact_policy="compact",
    )
    app = create_postgame_app(settings=settings, database=Database(settings.database_url))
    with TestClient(app) as client:
        assert client.post("/api/test/scenarios/standard").status_code == 401
        created = client.post(
            "/api/test/scenarios/standard",
            headers={"X-RTGS-Authorization": "Bearer top-secret"},
        )
        assert created.status_code == 201
        match_id = created.json()["id"]
        for _ in range(100):
            match = client.get(f"/api/v1/matches/{match_id}").json()
            if match["latest_job"]["state"] == "completed":
                break
            time.sleep(0.02)
        assert match["source_codec"] == "rtgs-observation"
        assert match["latest_job"]["state"] == "completed"
        report = client.get(f"/api/v1/matches/{match_id}/report").json()
        assert any(event["type"] == "shot" for event in report["events"])
        assert (tmp_path / "matches" / match_id / "observations.jsonl.gz").is_file()
