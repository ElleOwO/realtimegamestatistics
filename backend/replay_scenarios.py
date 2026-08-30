"""Deterministic observation scenarios for local and CI testing."""

from __future__ import annotations

import json
from pathlib import Path

from analytics_core import FrameObservation, PlayerObservation
from observation_io import ObservationRecording, RecordingHeader, ReplayItem


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"


def _players(ball: tuple[float, float], controlling_team: int, frame: int) -> list[PlayerObservation]:
    ball_x, ball_y = ball
    players: list[PlayerObservation] = []
    for team in (0, 1):
        direction = 1 if team == 0 else -1
        base_x = ball_x - direction * 2 if team == controlling_team else (35 if team == 0 else 70)
        for index in range(10):
            row, column = divmod(index, 5)
            x = max(2.0, min(103.0, base_x + direction * row * 8 + (column % 2)))
            y = 8.0 + column * 12.5 + row * 2
            if team == controlling_team and index == 0:
                x, y = ball_x, ball_y
            players.append(PlayerObservation(
                team="team0" if team == 0 else "team1",
                point=(x, y),
                confidence=0.92,
                track_id=team * 100 + index,
                role="outfield",
            ))
        players.append(PlayerObservation(
            team="team0" if team == 0 else "team1",
            point=(3.0 if team == 0 else 102.0, 34.0),
            confidence=0.94,
            track_id=team * 100 + 99,
            role="goalkeeper",
        ))
    return players


def fixture_recording(name: str) -> ObservationRecording:
    """Expand a compact, data-only fixture into canonical observations."""
    path = FIXTURE_ROOT / f"{name}.json"
    try:
        fixture = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"Unknown replay scenario: {name}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid replay scenario {name}: {exc}") from exc
    if fixture.get("schema_version") != 1 or fixture.get("name") != name:
        raise ValueError(f"Unsupported replay scenario: {name}")
    interval_ms = max(1, int(fixture.get("frame_interval_ms", 200)))
    timeline: list[tuple[tuple[float, float], int]] = []
    for segment in fixture.get("segments", []):
        control = int(segment["control"])
        if control not in (0, 1):
            raise ValueError(f"Replay scenario {name} has an invalid controlling team")
        if "points" in segment:
            points = segment["points"]
        else:
            points = [segment["ball"]] * max(1, int(segment.get("repeat", 1)))
        timeline.extend(((float(point[0]), float(point[1])), control) for point in points)
    if not timeline:
        raise ValueError(f"Replay scenario {name} has no frames")
    header = RecordingHeader(
        scenario=name,
        match=dict(fixture.get("match") or {}),
    )
    items: list[ReplayItem] = []
    for frame_id, (point, controlling_team) in enumerate(timeline):
        timestamp_ms = frame_id * interval_ms
        observation = FrameObservation(
            frame_id=frame_id,
            timestamp_ms=timestamp_ms,
            players=_players(point, controlling_team, frame_id),
            ball=point,
            ball_confidence=0.93,
            calibration_confidence=0.9,
            visible_pitch_fraction=0.78,
            reprojection_error_m=0.35,
            match_clock_s=timestamp_ms / 1000,
            period=1,
            phase="first_half",
        )
        items.append(ReplayItem(kind="frame", at_ms=timestamp_ms, observation=observation))
    timestamp_ms = len(timeline) * interval_ms
    if fixture.get("quality_drop", False):
        items.append(ReplayItem(kind="frame", at_ms=timestamp_ms, observation=FrameObservation(
            frame_id=len(timeline),
            timestamp_ms=timestamp_ms,
            players=[],
            ball=None,
            ball_confidence=None,
            calibration_confidence=0.1,
            visible_pitch_fraction=0.1,
            reprojection_error_m=8.0,
            match_clock_s=timestamp_ms / 1000,
            period=1,
            phase="first_half",
        )))
    if expectation := fixture.get("expectation"):
        items.append(ReplayItem(kind="expectation", at_ms=timestamp_ms, expectation=dict(expectation)))
    return ObservationRecording(header=header, items=tuple(items))


def standard_recording() -> ObservationRecording:
    return fixture_recording("standard")


SCENARIOS = {"standard": standard_recording}


def get_scenario(name: str) -> ObservationRecording:
    try:
        return SCENARIOS[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown replay scenario: {name}") from exc
