"""Tactical analytics helpers for pitch-space summaries."""

from __future__ import annotations

from collections import deque

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import ConvexHull

from ..constants import HEATMAP_H, HEATMAP_W, PITCH_HALF_LENGTH, PITCH_HALF_WIDTH

ZONE_X_SPLIT = 0.0
ZONE_Y_SPLIT = 0.0


def assign_zone(x_m: float, y_m: float) -> str:
    """Return the pitch quarter label for a coordinate pair."""
    left = y_m <= ZONE_Y_SPLIT
    defensive = x_m <= ZONE_X_SPLIT
    if defensive and left:
        return "Q1_def_left"
    if not defensive and left:
        return "Q2_atk_left"
    if defensive:
        return "Q3_def_right"
    return "Q4_atk_right"


def compute_possession(possession_log: deque) -> float:
    """Return Team 0's possession percentage over the rolling window."""
    if not possession_log:
        return 50.0
    return round(100.0 * sum(1 for t in possession_log if t == 0) / len(possession_log), 1)


def update_possession_log(
    possession_log: deque,
    ball_pitch_xy: np.ndarray,
    team0_pitch_xy: np.ndarray,
    team1_pitch_xy: np.ndarray,
):
    """Append the possessing team for this frame to the rolling window."""
    if len(ball_pitch_xy) == 0:
        return
    ball = ball_pitch_xy[0]

    def nearest_dist(xy):
        return float(np.min(np.linalg.norm(xy - ball, axis=1))) if len(xy) > 0 else float("inf")

    possession_log.append(0 if nearest_dist(team0_pitch_xy) <= nearest_dist(team1_pitch_xy) else 1)


def compute_defensive_line_height(defensive_team_xy: np.ndarray) -> float:
    """Metres from own goal line to the average depth of the deepest defenders."""
    if len(defensive_team_xy) < 2:
        return 0.0
    sorted_x = np.sort(defensive_team_xy[:, 0])
    return round(float(np.mean(sorted_x[: min(4, len(sorted_x))])), 1)


def compute_width_of_attack(attacking_team_xy: np.ndarray) -> float:
    """Lateral spread in metres of the attacking team."""
    if len(attacking_team_xy) < 2:
        return 0.0
    return round(float(np.ptp(attacking_team_xy[:, 1])), 1)


def compute_transition_speed(
    ball_positions: deque,
    defensive_third_end_m: float = 35.0,
    attacking_third_start_m: float = 70.0,
) -> float:
    """Average seconds for the ball to travel from defensive to attacking third."""
    if len(ball_positions) < 2:
        return 0.0
    transition_times = []
    entered_attacking = None
    for timestamp, bx, _ in reversed(list(ball_positions)):
        if entered_attacking is None:
            if bx >= attacking_third_start_m:
                entered_attacking = timestamp
        else:
            if bx <= defensive_third_end_m:
                transition_times.append(entered_attacking - timestamp)
                entered_attacking = None
                if len(transition_times) >= 3:
                    break
    return round(float(np.mean(transition_times)), 1) if transition_times else 0.0


def compute_convex_hull_area(team_xy: np.ndarray) -> float:
    """Area in square metres of the convex hull of the team positions."""
    if len(team_xy) < 3:
        return 0.0
    try:
        return round(float(ConvexHull(team_xy).volume), 1)
    except Exception:
        return 0.0


def compute_zone_stats(team_xy: np.ndarray) -> dict:
    """Count players in each zone and third for dashboard summaries."""
    counts = {z: 0 for z in ("Q1_def_left", "Q2_atk_left", "Q3_def_right", "Q4_atk_right")}
    def_third = 0
    atk_third = 0
    for x_m, y_m in team_xy:
        counts[assign_zone(x_m, y_m)] += 1
        if x_m < -35.0:
            def_third += 1
        if x_m > 35.0:
            atk_third += 1
    dominant = max(counts, key=counts.get) if len(team_xy) > 0 else "unknown"
    return {**counts, "dominant_zone": dominant, "defensive_third_count": def_third, "attacking_third_count": atk_third}


def update_heatmap(heatmap: np.ndarray, pitch_xy: np.ndarray):
    """Increment heatmap cells for every coordinate."""
    for x_m, y_m in pitch_xy:
        col = int(np.clip(x_m + PITCH_HALF_LENGTH, 0, HEATMAP_W - 1))
        row = int(np.clip(y_m + PITCH_HALF_WIDTH, 0, HEATMAP_H - 1))
        heatmap[row, col] += 1.0


def get_heatmap_payload(heatmap: np.ndarray) -> dict:
    """Normalise, smooth, and serialise a heatmap for JSON transport."""
    peak = float(heatmap.max()) or 1.0
    smoothed = gaussian_filter(heatmap / peak, sigma=2.5)
    return {"grid": smoothed.tolist(), "max": peak, "width": HEATMAP_W, "height": HEATMAP_H}
