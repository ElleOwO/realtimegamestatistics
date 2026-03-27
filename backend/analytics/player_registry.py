"""Persistent per-player match statistics."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

import numpy as np

from ..constants import HEATMAP_H, HEATMAP_W, PITCH_HALF_LENGTH, PITCH_HALF_WIDTH, SPRINT_THRESHOLD_MS
from .tactical_metrics import assign_zone


@dataclass
class PlayerStats:
    """Full statistical profile for one tracked player."""

    tracker_id: int = 0
    team_id: int = -1
    distance_km: float = 0.0
    top_speed_ms: float = 0.0
    sprint_count: int = 0
    sprint_dist_km: float = 0.0
    speed_buffer: Deque = field(default_factory=lambda: deque(maxlen=10))
    last_x_m: float = 0.0
    last_y_m: float = 0.0
    last_seen_ts: float = 0.0
    passes_attempted: int = 0
    passes_completed: int = 0
    shots: int = 0
    shots_on_target: int = 0
    total_xg: float = 0.0
    zone_frames: Dict[str, int] = field(default_factory=lambda: {"Q1_def_left": 0, "Q2_atk_left": 0, "Q3_def_right": 0, "Q4_atk_right": 0})
    frames_in_attack_zone: int = 0
    heatmap: np.ndarray = field(default_factory=lambda: np.zeros((HEATMAP_H, HEATMAP_W), dtype=np.float32))

    @property
    def pass_accuracy(self) -> float:
        if self.passes_attempted == 0:
            return 0.0
        return round(100.0 * self.passes_completed / self.passes_attempted, 1)

    @property
    def time_in_attack_zone_s(self) -> float:
        return round(self.frames_in_attack_zone / 30.0, 1)


player_registry: Dict[int, PlayerStats] = {}


def update_player_registry(
    tracker_id: int,
    team_id: int,
    current_xy: np.ndarray,
    now: float,
    registry: Dict[int, PlayerStats],
) -> PlayerStats:
    """Create or update a player's stats entry for this frame."""
    if tracker_id not in registry:
        registry[tracker_id] = PlayerStats(tracker_id=tracker_id, team_id=team_id, last_x_m=float(current_xy[0]), last_y_m=float(current_xy[1]), last_seen_ts=now)
        return registry[tracker_id]

    stats = registry[tracker_id]
    stats.team_id = team_id

    prev_xy = np.array([stats.last_x_m, stats.last_y_m])
    delta_m = float(np.linalg.norm(current_xy - prev_xy))
    elapsed = now - stats.last_seen_ts

    if delta_m < 10.0 and elapsed > 0:
        stats.distance_km += delta_m / 1000.0
        speed = delta_m / elapsed
        stats.speed_buffer.append(speed)
        smooth_speed = float(np.mean(stats.speed_buffer))
        if smooth_speed > stats.top_speed_ms:
            stats.top_speed_ms = round(smooth_speed, 2)

        sprinting_now = sum(1 for s in stats.speed_buffer if s > SPRINT_THRESHOLD_MS)
        sprinting_prev = sum(1 for s in list(stats.speed_buffer)[:-2] if s > SPRINT_THRESHOLD_MS)
        if sprinting_now >= 2:
            if sprinting_prev == 0:
                stats.sprint_count += 1
            stats.sprint_dist_km += delta_m / 1000.0

    x_m, y_m = float(current_xy[0]), float(current_xy[1])
    stats.zone_frames[assign_zone(x_m, y_m)] += 1
    if x_m > 35.0:
        stats.frames_in_attack_zone += 1

    col = int(np.clip(x_m + PITCH_HALF_LENGTH, 0, HEATMAP_W - 1))
    row = int(np.clip(y_m + PITCH_HALF_WIDTH, 0, HEATMAP_H - 1))
    stats.heatmap[row, col] += 1.0

    stats.last_x_m = x_m
    stats.last_y_m = y_m
    stats.last_seen_ts = now
    return stats


def serialize_player(stats: PlayerStats) -> dict:
    """Convert a PlayerStats to a JSON-safe dict for the WebSocket payload."""
    return {
        "id": stats.tracker_id,
        "team": stats.team_id,
        "distance_km": round(stats.distance_km, 3),
        "top_speed_kmh": round(stats.top_speed_ms * 3.6, 1),
        "sprint_count": stats.sprint_count,
        "sprint_distance_km": round(stats.sprint_dist_km, 3),
        "pass_accuracy": stats.pass_accuracy,
        "passes_attempted": stats.passes_attempted,
        "shots": stats.shots,
        "shots_on_target": stats.shots_on_target,
        "total_xg": round(stats.total_xg, 3),
        "time_in_attack_zone_s": stats.time_in_attack_zone_s,
        "dominant_zone": max(stats.zone_frames, key=stats.zone_frames.get),
        "x_m": round(stats.last_x_m, 2),
        "y_m": round(stats.last_y_m, 2),
    }
