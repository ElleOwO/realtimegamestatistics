"""WebSocket payload assembly helpers."""

from __future__ import annotations

from typing import Optional


def build_payload(
    frame_id: int,
    timestamp: float,
    possession_pct: float,
    defensive_line_height: float,
    width_of_attack: float,
    transition_speed: float,
    convex_hull_area: float,
    total_xg_team0: float,
    total_xg_team1: float,
    xg_timeline: list,
    pitch_players: list,
    pitch_ball: Optional[list],
    key_events: list,
    zone_stats_team0: dict,
    zone_stats_team1: dict,
    heatmap_payload: Optional[dict] = None,
    ai_insight: Optional[dict] = None,
    team0_name: str = "U of S",
    team1_name: str = "Calgary",
) -> dict:
    """Assemble the JSON payload sent to the dashboard."""
    insights = []

    if convex_hull_area > 800:
        insights.append(
            {
                "type": "warning",
                "title": "Defensive Vulnerability Detected",
                "body": (
                    f"Defensive shape area is {convex_hull_area:.0f} m² — stretched. "
                    "Opponent may exploit right flank. "
                    "Instruct midfield to drop deeper and close the channel."
                ),
            }
        )

    if possession_pct < 40:
        insights.append(
            {
                "type": "warning",
                "title": "Possession Under Pressure",
                "body": (
                    f"Ball possession at {possession_pct}%. "
                    "Consider a more direct shape or pressing trigger to win the ball back."
                ),
            }
        )

    if width_of_attack > 50:
        insights.append(
            {
                "type": "info",
                "title": "Possession Pattern Analysis",
                "body": (
                    f"Wide attacking shape ({width_of_attack} m spread). "
                    "Strong possession in the middle third. "
                    "Try central runs to break the defensive line."
                ),
            }
        )

    if 0 < transition_speed < 6:
        insights.append(
            {
                "type": "positive",
                "title": "Fast Transition Detected",
                "body": f"Avg attacking transition: {transition_speed}s — exploit on set pieces.",
            }
        )

    if ai_insight:
        insights.append(ai_insight)

    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "match_clock": round(timestamp / 60, 2),
        "possession": {
            "team0_pct": possession_pct,
            "team1_pct": round(100.0 - possession_pct, 1),
            "team0_name": team0_name,
            "team1_name": team1_name,
        },
        "transition_speed_s": transition_speed,
        "total_xg_team0": round(total_xg_team0, 2),
        "total_xg_team1": round(total_xg_team1, 2),
        "defensive_line_height_m": defensive_line_height,
        "width_of_attack_m": width_of_attack,
        "convex_hull_area_m2": convex_hull_area,
        "players": pitch_players,
        "ball": pitch_ball,
        "zone_stats": {
            "team0": zone_stats_team0,
            "team1": zone_stats_team1,
        },
        "heatmaps": heatmap_payload,
        "xg_timeline": xg_timeline,
        "insights": insights,
        "key_events": key_events,
    }
