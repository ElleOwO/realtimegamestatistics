from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ConfidenceSample, Match, MatchEvent, MatchSummary, Observation, TimeSeriesPoint
from .schemas import MatchEventRead, MatchReport, MetricValue


def metric(
    value: Any,
    unit: str | None,
    confidence: float,
    coverage: float,
    *,
    experimental: bool = False,
    minimum_coverage: float = 0.0,
    unavailable_reason: str | None = None,
) -> MetricValue[Any]:
    confidence = max(0.0, min(float(confidence), 1.0))
    coverage = max(0.0, min(float(coverage), 1.0))
    if value is None or coverage <= 0:
        return MetricValue(
            value=None,
            unit=unit,
            confidence=confidence,
            sample_coverage=coverage,
            status="unavailable",
            explanation=unavailable_reason or "No validated observations are available.",
        )
    if experimental:
        status = "experimental"
        explanation = "Experimental until manually validated across at least three Veo matches."
    elif coverage < minimum_coverage:
        status = "partial"
        explanation = f"Only {coverage:.0%} of eligible samples met the observation gate."
    else:
        status = "available"
        explanation = None
    return MetricValue(
        value=value,
        unit=unit,
        confidence=confidence,
        sample_coverage=coverage,
        status=status,
        explanation=explanation,
    )


def _coverage(session: Session, match_id: str, object_type: str, expected_samples: int) -> float:
    if expected_samples <= 0:
        return 0.0
    observed = session.scalar(
        select(func.count(func.distinct(Observation.timestamp_ms))).where(
            Observation.match_id == match_id, Observation.object_type == object_type
        )
    ) or 0
    return min(float(observed) / expected_samples, 1.0)


def build_report(session: Session, match: Match, provisional: bool) -> MatchReport:
    events = list(
        session.scalars(
            select(MatchEvent)
            .where(MatchEvent.match_id == match.id, MatchEvent.review_status != "rejected")
            .order_by(MatchEvent.timestamp_ms)
        )
    )
    confidence_samples = list(
        session.scalars(
            select(ConfidenceSample).where(ConfidenceSample.match_id == match.id)
        )
    )
    active_ms = sum(int(period["end_ms"]) - int(period["start_ms"]) for period in match.periods)
    expected_samples = max(round(active_ms / 100), 1)
    player_coverage = _coverage(session, match.id, "player", expected_samples)
    ball_coverage = _coverage(session, match.id, "ball", expected_samples)
    calibration_coverage = (
        sum(sample.calibration_confidence is not None and sample.calibration_confidence >= 0.5 for sample in confidence_samples)
        / len(confidence_samples)
        if confidence_samples
        else 0.0
    )
    average_detection = (
        sum(sample.detection_confidence or 0.0 for sample in confidence_samples) / len(confidence_samples)
        if confidence_samples
        else 0.0
    )
    average_calibration = (
        sum(sample.calibration_confidence or 0.0 for sample in confidence_samples) / len(confidence_samples)
        if confidence_samples
        else 0.0
    )

    event_counts = Counter(event.type for event in events)
    team_events: dict[str, Counter] = defaultdict(Counter)
    xg = {"home": 0.0, "away": 0.0}
    xg_complete = {"home": True, "away": True}
    context_xg = {"home": {"open_play": 0.0, "set_piece": 0.0}, "away": {"open_play": 0.0, "set_piece": 0.0}}
    context_shots = {"home": Counter(), "away": Counter()}
    context_xg_missing = {"home": Counter(), "away": Counter()}
    reviewed_on_target = {"home": [], "away": []}
    entry_lanes: dict[str, Counter] = {"home": Counter(), "away": Counter()}
    recovery_times: dict[str, list[float]] = {"home": [], "away": []}
    pressure_counts: dict[str, Counter] = {"home": Counter(), "away": Counter()}
    pressure_escape_times: dict[str, list[float]] = {"home": [], "away": []}
    shot_map = []
    for event in events:
        if event.team:
            team_events[event.team][event.type] += 1
        if event.type == "shot" and event.team in xg:
            raw_xg = event.details.get("xg")
            event_xg = float(raw_xg) if raw_xg is not None else None
            if event_xg is None:
                xg_complete[event.team] = False
            else:
                xg[event.team] += event_xg
            if event.play_context in ("open_play", "set_piece"):
                if event_xg is not None:
                    context_xg[event.team][event.play_context] += event_xg
                else:
                    context_xg_missing[event.team][event.play_context] += 1
                context_shots[event.team][event.play_context] += 1
            if event.review_status in ("confirmed", "corrected") and event.details.get("on_target") is not None:
                reviewed_on_target[event.team].append(bool(event.details["on_target"]))
            shot_map.append(
                {
                    "event_id": event.id,
                    "team": event.team,
                    "timestamp_ms": event.timestamp_ms,
                    "x_m": event.pitch_x_m,
                    "y_m": event.pitch_y_m,
                    "xg": event_xg,
                    "on_target": event.details.get("on_target"),
                    "play_context": event.play_context,
                    "review_status": event.review_status,
                }
            )
        if event.type in ("final_third_entry", "penalty_area_entry") and event.team in entry_lanes:
            entry_lanes[event.team][f"{event.type}:{event.details.get('lane', 'unknown')}"] += 1
        if event.type == "possession_win" and event.team in recovery_times:
            recovery = event.details.get("recovery_time_s")
            if recovery is not None:
                recovery_times[event.team].append(float(recovery))
        if event.type in ("pressure_attempt", "pressure_success", "forced_long_candidate") and event.team in pressure_counts:
            pressure_counts[event.team][event.type] += 1
            if event.type == "pressure_attempt" and event.details.get("high_press"):
                pressure_counts[event.team]["high_press_attempt"] += 1
        if event.type == "pressure_escape" and event.details.get("pressing_team") in pressure_counts:
            pressing_team = event.details["pressing_team"]
            pressure_counts[pressing_team]["escape"] += 1
            pressure_counts[pressing_team]["central_escape"] += int(bool(event.details.get("central")))
            pressure_counts[pressing_team]["forced_backward"] += int(bool(event.details.get("forced_backward")))
            if event.details.get("escape_time_s") is not None:
                pressure_escape_times[pressing_team].append(float(event.details["escape_time_s"]))

    series_rows = list(
        session.scalars(
            select(TimeSeriesPoint)
            .where(TimeSeriesPoint.match_id == match.id)
            .order_by(TimeSeriesPoint.timestamp_ms)
        )
    )
    time_series: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for point in series_rows:
        time_series[point.metric].append(
            {"timestamp_ms": point.timestamp_ms, "value": point.value, "confidence": point.confidence}
        )

    possession_samples = [point.value.get("team") for point in series_rows if point.metric == "possession"]
    controlled = [team for team in possession_samples if team in ("home", "away")]
    home_possession = controlled.count("home") / len(controlled) * 100 if controlled else None
    away_possession = 100 - home_possession if home_possession is not None else None
    possession_coverage = len(controlled) / max(len(possession_samples), 1)

    tilt_samples = [point.value for point in series_rows if point.metric == "attacking_third_control"]
    home_tilt = sum(value.get("team") == "home" for value in tilt_samples)
    away_tilt = sum(value.get("team") == "away" for value in tilt_samples)
    field_tilt = home_tilt / (home_tilt + away_tilt) * 100 if home_tilt + away_tilt else None

    shape_by_phase: dict[str, list[dict[str, float]]] = defaultdict(list)
    for point in series_rows:
        if point.metric == "shape":
            shape_by_phase[point.value.get("phase", "unknown")].append(point.value)

    def average_shape(field: str, phase: str) -> float | None:
        values = [float(sample[field]) for sample in shape_by_phase[phase] if field in sample]
        return sum(values) / len(values) if values else None

    shape_coverage = sum(len(values) for values in shape_by_phase.values()) / expected_samples
    report = MatchReport(
        match_id=match.id,
        provisional=provisional,
        generated_at=datetime.now(timezone.utc),
        score={
            "home_team": match.home_team,
            "away_team": match.away_team,
            "home": match.home_score,
            "away": match.away_score,
            "source": "operator",
            "reconciled_goals": {
                "home": team_events["home"]["goal"],
                "away": team_events["away"]["goal"],
                "matches_final_score": (
                    team_events["home"]["goal"] == match.home_score
                    and team_events["away"]["goal"] == match.away_score
                ),
            },
        },
        summary={
            "home_possession": metric(home_possession, "%", average_detection, possession_coverage),
            "away_possession": metric(away_possession, "%", average_detection, possession_coverage),
            "home_shots": metric(team_events["home"]["shot"], "shots", average_detection, ball_coverage, experimental=True),
            "away_shots": metric(team_events["away"]["shot"], "shots", average_detection, ball_coverage, experimental=True),
            "home_xg": metric(round(xg["home"], 3) if xg_complete["home"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="At least one reviewed shot has no modelled location/xG value."),
            "away_xg": metric(round(xg["away"], 3) if xg_complete["away"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="At least one reviewed shot has no modelled location/xG value."),
            "home_shots_on_target": metric(sum(reviewed_on_target["home"]) if reviewed_on_target["home"] else None, "shots", 1.0 if reviewed_on_target["home"] else 0.0, len(reviewed_on_target["home"]) / max(team_events["home"]["shot"], 1), unavailable_reason="Shots on target require operator review because monocular video cannot reliably classify height, saves, or blocks."),
            "away_shots_on_target": metric(sum(reviewed_on_target["away"]) if reviewed_on_target["away"] else None, "shots", 1.0 if reviewed_on_target["away"] else 0.0, len(reviewed_on_target["away"]) / max(team_events["away"]["shot"], 1), unavailable_reason="Shots on target require operator review because monocular video cannot reliably classify height, saves, or blocks."),
            "home_open_play_xg": metric(round(context_xg["home"]["open_play"], 3) if context_shots["home"]["open_play"] and not context_xg_missing["home"]["open_play"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="Review shot context and ensure every shot has a modelled location."),
            "home_set_piece_xg": metric(round(context_xg["home"]["set_piece"], 3) if context_shots["home"]["set_piece"] and not context_xg_missing["home"]["set_piece"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="Review shot context and ensure every shot has a modelled location."),
            "away_open_play_xg": metric(round(context_xg["away"]["open_play"], 3) if context_shots["away"]["open_play"] and not context_xg_missing["away"]["open_play"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="Review shot context and ensure every shot has a modelled location."),
            "away_set_piece_xg": metric(round(context_xg["away"]["set_piece"], 3) if context_shots["away"]["set_piece"] and not context_xg_missing["away"]["set_piece"] else None, "xG", average_detection, ball_coverage, experimental=True, unavailable_reason="Review shot context and ensure every shot has a modelled location."),
        },
        events=[MatchEventRead.model_validate(event) for event in events],
        shot_map=shot_map,
        territorial={
            "home_final_third_entries": metric(team_events["home"]["final_third_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
            "away_final_third_entries": metric(team_events["away"]["final_third_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
            "home_penalty_area_entries": metric(team_events["home"]["penalty_area_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
            "away_penalty_area_entries": metric(team_events["away"]["penalty_area_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
            "field_tilt_home": metric(field_tilt, "%", average_calibration, calibration_coverage, experimental=True),
            "home_entry_lanes": metric(dict(entry_lanes["home"]), "entries", average_calibration, calibration_coverage, experimental=True),
            "away_entry_lanes": metric(dict(entry_lanes["away"]), "entries", average_calibration, calibration_coverage, experimental=True),
            "home_behind_line_entries": metric(team_events["home"]["behind_line_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
            "away_behind_line_entries": metric(team_events["away"]["behind_line_entry"], "entries", average_calibration, calibration_coverage, experimental=True),
        },
        transitions={
            "home_possession_wins": metric(team_events["home"]["possession_win"], "events", average_calibration, possession_coverage, experimental=True),
            "away_possession_wins": metric(team_events["away"]["possession_win"], "events", average_calibration, possession_coverage, experimental=True),
            "high_turnovers": metric(event_counts["high_turnover"], "events", average_calibration, possession_coverage, experimental=True),
            "dangerous_turnovers": metric(event_counts["dangerous_turnover"], "events", average_calibration, possession_coverage, experimental=True),
            "counterattacks": metric(event_counts["counterattack"], "events", average_calibration, possession_coverage, experimental=True),
            "home_recovery_time": metric(sum(recovery_times["home"]) / len(recovery_times["home"]) if recovery_times["home"] else None, "s", average_calibration, possession_coverage, experimental=True, unavailable_reason="No complete loss-to-regain sequence was observed."),
            "away_recovery_time": metric(sum(recovery_times["away"]) / len(recovery_times["away"]) if recovery_times["away"] else None, "s", average_calibration, possession_coverage, experimental=True, unavailable_reason="No complete loss-to-regain sequence was observed."),
            "shots_after_regain": metric(sum(event.type == "shot" and bool(event.details.get("shot_after_regain")) for event in events), "shots", average_detection, possession_coverage, experimental=True),
        },
        shape={
            f"{phase}_{field}": metric(
                average_shape(field, phase),
                "m²" if field == "convex_hull_area_m2" else "players" if field == "players_behind_ball" else "m",
                average_calibration,
                shape_coverage,
                minimum_coverage=0.5,
                unavailable_reason="Fewer than seven players or insufficient visible pitch in eligible samples.",
            )
            for phase in ("in_possession", "out_of_possession")
            for field in (
                "defensive_line_height_m", "team_length_m", "width_m",
                "convex_hull_area_m2", "compactness_m", "line_gap_1_m",
                "line_gap_2_m", "players_behind_ball", "goalkeeper_line_gap_m",
            )
        },
        pressing={
            f"{team}_{name}": metric(
                (
                    sum(pressure_escape_times[team]) / len(pressure_escape_times[team])
                    if name == "average_escape_time_s" and pressure_escape_times[team]
                    else None if name == "average_escape_time_s"
                    else pressure_counts[team][event_name]
                ),
                "s" if name == "average_escape_time_s" else "events",
                average_calibration,
                possession_coverage,
                experimental=True,
                unavailable_reason="No complete pressure episode was observed.",
            )
            for team in ("home", "away")
            for name, event_name in (
                ("attempts", "pressure_attempt"),
                ("successes", "pressure_success"),
                ("high_press_attempts", "high_press_attempt"),
                ("central_escapes", "central_escape"),
                ("forced_backward", "forced_backward"),
                ("forced_long_candidates", "forced_long_candidate"),
                ("average_escape_time_s", "escape"),
            )
        },
        set_pieces=None,
        time_series=dict(time_series),
        quality={
            "player_detection_coverage": metric(player_coverage * 100, "%", average_detection, player_coverage),
            "ball_observation_coverage": metric(ball_coverage * 100, "%", average_detection, ball_coverage),
            "valid_calibration_coverage": metric(calibration_coverage * 100, "%", average_calibration, calibration_coverage),
        },
        diagnostics=([] if confidence_samples else ["No quality samples have been produced yet."])
        + (
            []
            if team_events["home"]["goal"] == match.home_score
            and team_events["away"]["goal"] == match.away_score
            else ["Reviewed goal events do not yet reconcile with the operator-supplied final score."]
        ),
    )
    return report


def persist_report(session: Session, match: Match, provisional: bool) -> MatchReport:
    report = build_report(session, match, provisional)
    summary = session.get(MatchSummary, match.id)
    if summary is None:
        summary = MatchSummary(match_id=match.id)
        session.add(summary)
    summary.report = report.model_dump(mode="json")
    summary.provisional = provisional
    summary.version = (summary.version or 0) + 1
    return report
