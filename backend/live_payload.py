"""Construction of the frontend's live AnalyticsPayload contract."""

from __future__ import annotations

import time
from typing import Any

from analytics_core import FrameObservation, PITCH_LENGTH_M, PITCH_WIDTH_M


def build_payload_v2(
    observation: FrameObservation,
    analytics: dict[str, Any],
    match_state: dict[str, Any],
    emitted_at: float | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    players = [
        {
            "id": player.track_id,
            "team": 0 if player.team == "team0" else 1,
            "role": player.role,
            "x_m": round(player.point[0], 2),
            "y_m": round(player.point[1], 2),
            "confidence": round(player.confidence, 3),
        }
        for player in observation.players
    ]
    ball = None
    if observation.ball is not None:
        ball = {
            "x_m": round(observation.ball[0], 2),
            "y_m": round(observation.ball[1], 2),
            "confidence": round(float(observation.ball_confidence or 0.0), 3),
        }
    detection_values = [player.confidence for player in observation.players]
    detection_confidence = sum(detection_values) / len(detection_values) if detection_values else None
    emitted_at_ms = round((emitted_at or time.time()) * 1000)
    runtime_value = {
        "run_id": "local",
        "mode": "live",
        "source_state": "live",
        "inference_fps": 0.0,
        "payload_fps": 0.0,
        "processing_latency_ms": None,
        "last_frame_age_ms": 0,
        "reconnect_count": 0,
    }
    runtime_value.update(runtime or {})
    return {
        "schema_version": 2,
        "pitch": {"length_m": PITCH_LENGTH_M, "width_m": PITCH_WIDTH_M},
        "frame": {
            "id": observation.frame_id,
            "source_timestamp_ms": observation.timestamp_ms,
            "emitted_at_ms": emitted_at_ms,
        },
        "runtime": runtime_value,
        "frame_quality": {
            "visible_players": len(players),
            "ball_visible": ball is not None,
            "detection_confidence": round(detection_confidence, 3) if detection_confidence is not None else None,
            "ball_confidence": observation.ball_confidence,
            "calibration_confidence": round(observation.calibration_confidence, 3),
            "visible_pitch_fraction": round(observation.visible_pitch_fraction, 3),
            "reprojection_error_m": round(observation.reprojection_error_m, 3) if observation.reprojection_error_m is not None else None,
            "observation_coverage": round(float(analytics["quality_coverage"]), 3),
        },
        "match": match_state,
        "observations": {"players": players, "ball": ball},
        "possession": analytics["possession"],
        "chance_quality": analytics["chance_quality"],
        "progression": analytics["progression"],
        "transitions": analytics["transitions"],
        "shape": analytics["shape"],
        "pressing": analytics["pressing"],
        "events": analytics["events"],
    }
