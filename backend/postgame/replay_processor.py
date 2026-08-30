"""Post-game AnalysisProcessor backed by a compact observation recording."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Callable

from analytics_core import AnalyticsEngine
from observation_io import read_recording

from .models import Match
from .shared_adapter import AnalyticsBatchAdapter
from .worker import AnalysisBatch, AnalysisProcessor


_ONE_PIXEL_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABAf/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPxB//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPxB//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxB//9k="
)


def load_coefficients() -> dict[str, float]:
    coeffs = {"intercept": 0.6, "distance": -0.18, "angle": 3.0}
    try:
        value = json.loads((Path(__file__).resolve().parents[1] / "xg_coeffs.json").read_text())
        coeffs.update({key: float(value[key]) for key in coeffs if key in value})
    except (OSError, ValueError, KeyError):
        pass
    return coeffs


class ReplayAnalysisProcessor:
    def preflight(self, match: Match, match_dir: Path) -> list[dict[str, Any]]:
        previews = match_dir / "preflight"
        previews.mkdir(parents=True, exist_ok=True)
        for cluster in (0, 1):
            (previews / f"cluster-{cluster}.jpg").write_bytes(_ONE_PIXEL_JPEG)
        return [
            {"cluster": cluster, "preview_url": f"/api/v1/matches/{match.id}/preflight/cluster-{cluster}.jpg", "sample_count": 11}
            for cluster in (0, 1)
        ]

    def process(
        self,
        match: Match,
        match_dir: Path,
        emit: Callable[[AnalysisBatch], None],
        cancelled: Callable[[], bool],
    ) -> None:
        recording = read_recording(match.source_path)
        adapter = AnalyticsBatchAdapter(AnalyticsEngine(load_coefficients()))
        for observation in recording.frames:
            if cancelled():
                return
            period = observation.period or 1
            usask_direction = match.directions.get(str(period), "right")
            home_direction = usask_direction if match.usask_side == "home" else ("left" if usask_direction == "right" else "right")
            directions = {"team0": home_direction, "team1": "left" if home_direction == "right" else "right"}
            emit(adapter.update(observation, directions))


class RoutedAnalysisProcessor:
    """Route observation fixtures around the GPU while preserving the real path."""

    def __init__(self, video: AnalysisProcessor, replay: AnalysisProcessor | None = None):
        self.video = video
        self.replay = replay or ReplayAnalysisProcessor()

    @staticmethod
    def _is_replay(match: Match) -> bool:
        return match.source_codec == "rtgs-observation"

    def preflight(self, match: Match, match_dir: Path) -> list[dict[str, Any]]:
        return (self.replay if self._is_replay(match) else self.video).preflight(match, match_dir)

    def process(self, match: Match, match_dir: Path, emit, cancelled) -> None:
        return (self.replay if self._is_replay(match) else self.video).process(match, match_dir, emit, cancelled)

    def cleanup(self, match: Match, match_dir: Path) -> None:
        processor = self.replay if self._is_replay(match) else self.video
        cleanup = getattr(processor, "cleanup", None)
        if cleanup:
            cleanup(match, match_dir)
