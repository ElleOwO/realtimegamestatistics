"""Compatibility exports for the shared live/post-game analytics core."""

from analytics_core import (  # noqa: F401
    EntryDetector,
    PossessionTracker,
    ShotDetector,
    attacking_channel,
    calculate_xg,
    camera_cut_score,
    classify_possession_change,
    counterattack_initiated,
    euclidean,
    match_clock_ms,
    match_phase,
    normalize_longitudinal,
    period_at,
    polygon_area,
    shape_metrics,
    shot_features,
)

__all__ = [
    "EntryDetector",
    "PossessionTracker",
    "ShotDetector",
    "attacking_channel",
    "calculate_xg",
    "camera_cut_score",
    "classify_possession_change",
    "counterattack_initiated",
    "euclidean",
    "match_clock_ms",
    "match_phase",
    "normalize_longitudinal",
    "period_at",
    "polygon_area",
    "shape_metrics",
    "shot_features",
]
