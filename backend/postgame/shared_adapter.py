"""Translate canonical analytics output into durable post-game batches."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from analytics_core import AnalyticsEngine, FrameObservation

from .worker import AnalysisBatch


@dataclass
class AnalyticsBatchAdapter:
    engine: AnalyticsEngine
    event_count: int = 0
    sample_count: int = 0
    player_sample_count: int = 0
    calibration_sample_count: int = 0

    @staticmethod
    def _side(team: str | None) -> str | None:
        return "home" if team == "team0" else "away" if team == "team1" else None

    def update(
        self,
        observation: FrameObservation,
        directions: dict[str, str],
        image_observations: list[dict[str, Any]] | None = None,
        log: str | None = None,
    ) -> AnalysisBatch:
        self.sample_count += 1
        if observation.players:
            self.player_sample_count += 1
        if observation.calibration_confidence >= 0.5:
            self.calibration_sample_count += 1
        snapshot = self.engine.update(observation, directions)
        new_events = self.engine.events[self.event_count:]
        self.event_count = len(self.engine.events)

        events: list[dict[str, Any]] = []
        possession_team = self._side(snapshot["possession"]["state"])
        for event in new_events:
            location = event.get("location")
            details = {
                key: value for key, value in event.items()
                if key not in {
                    "id", "type", "timestamp_ms", "team", "location", "status",
                    "confidence", "period", "match_clock_s", "play_context",
                }
            }
            for key in ("new_team", "pressing_team"):
                if details.get(key) in ("team0", "team1"):
                    details[key] = self._side(details[key])
            events.append({
                "type": event["type"],
                "team": self._side(event.get("team")),
                "period": event.get("period") or observation.period,
                "pitch_x_m": location[0] if location else None,
                "pitch_y_m": location[1] if location else None,
                "possession_context": possession_team,
                "play_context": event.get("play_context"),
                "confidence": float(event.get("confidence", 0.0)),
                "review_status": "pending" if event.get("status") == "candidate" else event.get("status", "pending"),
                "details": details,
            })

        observations = image_observations if image_observations is not None else [
            {
                "object_type": "player",
                "track_id": player.track_id,
                "team": self._side(player.team),
                "image_box": None,
                "pitch_x_m": player.point[0],
                "pitch_y_m": player.point[1],
                "detection_confidence": player.confidence,
                "calibration_confidence": observation.calibration_confidence,
            }
            for player in observation.players
        ]
        if image_observations is None and observation.ball is not None:
            observations.append({
                "object_type": "ball",
                "track_id": None,
                "team": None,
                "image_box": None,
                "pitch_x_m": observation.ball[0],
                "pitch_y_m": observation.ball[1],
                "detection_confidence": float(observation.ball_confidence or 0.0),
                "calibration_confidence": observation.calibration_confidence,
            })

        series: list[dict[str, Any]] = [
            {"metric": "possession", "value": {"team": possession_team or snapshot["possession"]["state"]}, "confidence": observation.calibration_confidence},
            {"metric": "match_clock", "value": {"elapsed_ms": round((observation.match_clock_s or 0) * 1000), "phase": observation.phase, "period": observation.period}, "confidence": 1.0},
            {"metric": "pressing", "value": snapshot["pressing"], "confidence": observation.calibration_confidence},
        ]
        for team_index, side in enumerate(("home", "away")):
            for phase, values in snapshot["shape"]["teams"][team_index].items():
                if values:
                    series.append({
                        "metric": "shape",
                        "value": {**values, "team": side, "phase": phase},
                        "confidence": observation.calibration_confidence,
                    })
        detection_values = [item["detection_confidence"] for item in observations]
        detection_confidence = sum(detection_values) / len(detection_values) if detection_values else None
        return AnalysisBatch(
            timestamp_ms=observation.timestamp_ms,
            observations=observations,
            events=events,
            time_series=series,
            confidence={
                "reprojection_error_m": observation.reprojection_error_m,
                "visible_pitch_fraction": observation.visible_pitch_fraction,
                "detection_confidence": detection_confidence,
                "calibration_confidence": observation.calibration_confidence,
                "camera_cut": False,
            },
            detection_coverage=self.player_sample_count / self.sample_count,
            calibration_coverage=self.calibration_sample_count / self.sample_count,
            log=log,
        )
