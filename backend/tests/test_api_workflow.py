from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

import postgame.api as api_module
from postgame.api import create_app
from postgame.config import Settings
from postgame.database import Database
from postgame.media import VideoMetadata
from postgame.worker import AnalysisBatch


class FakeProcessor:
    def preflight(self, match, match_dir: Path):
        preview = match_dir / "preflight"
        preview.mkdir(exist_ok=True)
        for cluster in (0, 1):
            (preview / f"cluster-{cluster}.jpg").write_bytes(b"jpeg")
        return [
            {"cluster": cluster, "preview_url": f"/api/v1/matches/{match.id}/preflight/cluster-{cluster}.jpg", "sample_count": 24}
            for cluster in (0, 1)
        ]

    def process(self, match, match_dir: Path, emit, cancelled):
        for timestamp_ms in (100, 200, 300):
            if cancelled():
                return
            emit(
                AnalysisBatch(
                    timestamp_ms=timestamp_ms,
                    observations=[
                        {
                            "object_type": "player", "track_id": 7, "team": "home",
                            "image_box": [1, 2, 3, 4], "pitch_x_m": 40.0,
                            "pitch_y_m": 30.0, "detection_confidence": 0.95,
                            "calibration_confidence": 0.9,
                        },
                        {
                            "object_type": "ball", "track_id": None, "team": None,
                            "image_box": [2, 2, 3, 3], "pitch_x_m": 42.0,
                            "pitch_y_m": 30.0, "detection_confidence": 0.8,
                            "calibration_confidence": 0.9,
                        },
                    ],
                    events=[{
                        "type": "shot", "team": "home", "period": 1,
                        "pitch_x_m": 42.0, "pitch_y_m": 30.0,
                        "possession_context": "home", "play_context": None,
                        "confidence": 0.8, "review_status": "pending",
                        "details": {"xg": 0.2, "on_target": None},
                    }] if timestamp_ms == 200 else [],
                    time_series=[{"metric": "possession", "value": {"team": "home"}, "confidence": 0.9}],
                    confidence={
                        "reprojection_error_m": 0.5, "visible_pitch_fraction": 0.8,
                        "detection_confidence": 0.9, "calibration_confidence": 0.9,
                        "camera_cut": False,
                    },
                    detection_coverage=1.0,
                    calibration_coverage=1.0,
                )
            )
        (match_dir / "annotated.mp4").write_bytes(b"annotated-video")


def test_import_setup_analysis_review_report_and_range(tmp_path, monkeypatch):
    settings = Settings(
        data_root=tmp_path,
        database_url=f"sqlite:///{tmp_path / 'test.sqlite3'}",
    )
    settings.ensure_directories()
    source = settings.inbox_dir / "veo-match.mp4"
    source.write_bytes(b"source-video-bytes")
    monkeypatch.setattr(
        api_module,
        "probe_video",
        lambda _path: VideoMetadata(duration_ms=10_000, codec="h264", width=1920, height=1080, fps=30),
    )
    app = create_app(
        settings=settings,
        database=Database(settings.database_url),
        processor=FakeProcessor(),
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/inbox").json()[0]["filename"] == "veo-match.mp4"
        imported = client.post("/api/v1/matches/import", json={"filename": "veo-match.mp4"})
        assert imported.status_code == 201
        match_id = imported.json()["id"]
        setup = client.patch(
            f"/api/v1/matches/{match_id}/setup",
            json={
                "home_team": "USask", "away_team": "Regina",
                "home_score": 2, "away_score": 1, "usask_side": "home",
                "periods": [{"number": 1, "start_ms": 0, "end_ms": 4_000}, {"number": 2, "start_ms": 5_000, "end_ms": 10_000}],
                "directions": {"1": "right", "2": "left"},
            },
        )
        assert setup.status_code == 200
        assert client.post(f"/api/v1/matches/{match_id}/preflight").status_code == 200
        assert client.patch(f"/api/v1/matches/{match_id}/team-mapping", json={"usask_cluster": 0}).status_code == 200
        started = client.post(f"/api/v1/matches/{match_id}/analysis")
        assert started.status_code == 202

        for _ in range(100):
            current = client.get(f"/api/v1/matches/{match_id}").json()
            if current["latest_job"]["state"] == "completed":
                break
            time.sleep(0.02)
        assert current["latest_job"]["state"] == "completed"

        report = client.get(f"/api/v1/matches/{match_id}/report")
        assert report.status_code == 200
        payload = report.json()
        assert payload["score"]["home"] == 2
        assert payload["summary"]["home_xg"]["value"] == 0.2
        assert payload["shape"]["in_possession_width_m"]["value"] is None
        assert payload["shape"]["in_possession_width_m"]["status"] == "unavailable"

        events = client.get(f"/api/v1/matches/{match_id}/events").json()
        corrected = client.patch(
            f"/api/v1/matches/{match_id}/events/{events[0]['id']}",
            json={"review_status": "corrected", "play_context": "set_piece"},
        )
        assert corrected.json()["review_status"] == "corrected"
        assert corrected.json()["play_context"] == "set_piece"

        observations = client.get(
            f"/api/v1/matches/{match_id}/observations?from_ms=150&to_ms=250"
        ).json()
        assert len(observations) == 2
        source_range = client.get(
            f"/api/v1/matches/{match_id}/video/source",
            headers={"Range": "bytes=0-5"},
        )
        assert source_range.status_code == 206
        assert source_range.content == b"source"
        annotated_range = client.get(
            f"/api/v1/matches/{match_id}/video/annotated",
            headers={"Range": "bytes=0-8"},
        )
        assert annotated_range.status_code == 206


def test_contract_exposes_all_versioned_routes(tmp_path):
    settings = Settings(data_root=tmp_path, database_url=f"sqlite:///{tmp_path / 'contract.sqlite3'}")
    app = create_app(settings=settings, database=Database(settings.database_url), processor=FakeProcessor(), start_worker=False)
    paths = app.openapi()["paths"]
    expected = {
        "/api/v1/inbox",
        "/api/v1/matches/import",
        "/api/v1/matches",
        "/api/v1/matches/{match_id}",
        "/api/v1/matches/{match_id}/setup",
        "/api/v1/matches/{match_id}/preflight",
        "/api/v1/matches/{match_id}/team-mapping",
        "/api/v1/matches/{match_id}/analysis",
        "/api/v1/matches/{match_id}/cancel",
        "/api/v1/matches/{match_id}/report",
        "/api/v1/matches/{match_id}/events",
        "/api/v1/matches/{match_id}/events/{event_id}",
        "/api/v1/matches/{match_id}/observations",
        "/api/v1/matches/{match_id}/video/{kind}",
    }
    assert expected <= set(paths)
