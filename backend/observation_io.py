"""Portable, video-free recordings at the CV/analytics boundary.

Recordings are JSON Lines (optionally gzip compressed).  They intentionally
contain only canonical pitch observations and operator commands: no source
frames, image boxes, names, or model-specific objects.
"""

from __future__ import annotations

import gzip
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, TextIO

from analytics_core import FrameObservation, PlayerObservation, PITCH_LENGTH_M, PITCH_WIDTH_M


RECORDING_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RecordingHeader:
    scenario: str
    match: dict[str, Any] = field(default_factory=dict)
    directions: dict[str, dict[str, str]] = field(default_factory=lambda: {
        "first_half": {"team0": "right", "team1": "left"},
        "second_half": {"team0": "left", "team1": "right"},
    })
    pitch_length_m: float = PITCH_LENGTH_M
    pitch_width_m: float = PITCH_WIDTH_M


@dataclass(frozen=True)
class ReplayItem:
    kind: str
    at_ms: int
    observation: FrameObservation | None = None
    command: dict[str, Any] | None = None
    expectation: dict[str, Any] | None = None


@dataclass(frozen=True)
class ObservationRecording:
    header: RecordingHeader
    items: tuple[ReplayItem, ...]

    @property
    def frames(self) -> tuple[FrameObservation, ...]:
        return tuple(item.observation for item in self.items if item.observation is not None)


def observation_to_dict(observation: FrameObservation) -> dict[str, Any]:
    return {
        "frame_id": observation.frame_id,
        "timestamp_ms": observation.timestamp_ms,
        "players": [
            {
                "team": player.team,
                "point": [player.point[0], player.point[1]],
                "confidence": player.confidence,
                "track_id": player.track_id,
                "role": player.role,
            }
            for player in observation.players
        ],
        "ball": list(observation.ball) if observation.ball is not None else None,
        "ball_confidence": observation.ball_confidence,
        "calibration_confidence": observation.calibration_confidence,
        "visible_pitch_fraction": observation.visible_pitch_fraction,
        "reprojection_error_m": observation.reprojection_error_m,
        "match_clock_s": observation.match_clock_s,
        "period": observation.period,
        "phase": observation.phase,
    }


def _point(value: Any, field_name: str) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field_name} must contain exactly two coordinates")
    point = (float(value[0]), float(value[1]))
    if not (-5 <= point[0] <= PITCH_LENGTH_M + 5 and -5 <= point[1] <= PITCH_WIDTH_M + 5):
        raise ValueError(f"{field_name} is outside the canonical pitch")
    return point


def observation_from_dict(value: dict[str, Any]) -> FrameObservation:
    players = []
    for item in value.get("players", []):
        team = item.get("team")
        if team not in ("team0", "team1"):
            raise ValueError("player team must be team0 or team1")
        role = item.get("role", "outfield")
        if role not in ("outfield", "goalkeeper"):
            raise ValueError("player role must be outfield or goalkeeper")
        confidence = float(item.get("confidence", 0.0))
        if not 0 <= confidence <= 1:
            raise ValueError("player confidence must be between zero and one")
        players.append(PlayerObservation(
            team=team,
            point=_point(item.get("point"), "player point"),
            confidence=confidence,
            track_id=int(item["track_id"]) if item.get("track_id") is not None else None,
            role=role,
        ))
    calibration_confidence = float(value.get("calibration_confidence", 0.0))
    visible_pitch_fraction = float(value.get("visible_pitch_fraction", 0.0))
    if not 0 <= calibration_confidence <= 1 or not 0 <= visible_pitch_fraction <= 1:
        raise ValueError("calibration values must be between zero and one")
    ball_value = value.get("ball")
    ball_confidence = value.get("ball_confidence")
    return FrameObservation(
        frame_id=int(value["frame_id"]),
        timestamp_ms=max(0, int(value["timestamp_ms"])),
        players=players,
        ball=_point(ball_value, "ball") if ball_value is not None else None,
        ball_confidence=float(ball_confidence) if ball_confidence is not None else None,
        calibration_confidence=calibration_confidence,
        visible_pitch_fraction=visible_pitch_fraction,
        reprojection_error_m=(
            float(value["reprojection_error_m"])
            if value.get("reprojection_error_m") is not None else None
        ),
        match_clock_s=float(value["match_clock_s"]) if value.get("match_clock_s") is not None else None,
        period=int(value["period"]) if value.get("period") is not None else None,
        phase=str(value["phase"]) if value.get("phase") is not None else None,
    )


def _open_text(path: Path, mode: str) -> TextIO:
    if ".gz" in path.suffixes:
        return gzip.open(path, mode + "t", encoding="utf-8")
    return path.open(mode, encoding="utf-8")


def write_recording(
    path: str | Path,
    header: RecordingHeader,
    items: Iterable[ReplayItem],
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    with _open_text(temporary, "w") as stream:
        stream.write(json.dumps({
            "type": "header",
            "schema_version": RECORDING_SCHEMA_VERSION,
            "scenario": header.scenario,
            "pitch": {"length_m": header.pitch_length_m, "width_m": header.pitch_width_m},
            "match": header.match,
            "directions": header.directions,
        }, separators=(",", ":")) + "\n")
        for item in items:
            value: dict[str, Any] = {"type": item.kind, "at_ms": item.at_ms}
            if item.observation is not None:
                value["observation"] = observation_to_dict(item.observation)
            if item.command is not None:
                value["command"] = item.command
            if item.expectation is not None:
                value["expectation"] = item.expectation
            stream.write(json.dumps(value, separators=(",", ":")) + "\n")
    temporary.replace(destination)


class ObservationRecorder:
    """Append-only writer used by expensive CV runs."""

    def __init__(self, path: str | Path, header: RecordingHeader):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._stream = _open_text(self.path, "w")
        self._stream.write(json.dumps({
            "type": "header",
            "schema_version": RECORDING_SCHEMA_VERSION,
            "scenario": header.scenario,
            "pitch": {"length_m": header.pitch_length_m, "width_m": header.pitch_width_m},
            "match": header.match,
            "directions": header.directions,
        }, separators=(",", ":")) + "\n")
        self._stream.flush()

    def record_frame(self, observation: FrameObservation) -> None:
        with self._lock:
            self._stream.write(json.dumps({
                "type": "frame",
                "at_ms": observation.timestamp_ms,
                "observation": observation_to_dict(observation),
            }, separators=(",", ":")) + "\n")
            self._stream.flush()

    def record_command(self, at_ms: int, command: dict[str, Any]) -> None:
        with self._lock:
            self._stream.write(json.dumps({
                "type": "command", "at_ms": at_ms, "command": command,
            }, separators=(",", ":")) + "\n")
            self._stream.flush()

    def close(self) -> None:
        with self._lock:
            if not self._stream.closed:
                self._stream.close()

    def __enter__(self) -> "ObservationRecorder":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()


def _lines(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with _open_text(path, "r") as stream:
        for line_number, raw in enumerate(stream, 1):
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on recording line {line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Recording line {line_number} must be an object")
            yield line_number, value


def read_recording(path: str | Path) -> ObservationRecording:
    source = Path(path)
    iterator = _lines(source)
    try:
        line_number, first = next(iterator)
    except StopIteration as exc:
        raise ValueError("Observation recording is empty") from exc
    if first.get("type") != "header" or first.get("schema_version") != RECORDING_SCHEMA_VERSION:
        raise ValueError(f"Recording line {line_number} has an unsupported header")
    pitch = first.get("pitch") or {}
    if float(pitch.get("length_m", 0)) != PITCH_LENGTH_M or float(pitch.get("width_m", 0)) != PITCH_WIDTH_M:
        raise ValueError("Recording pitch does not match the canonical 105 x 68 pitch")
    header = RecordingHeader(
        scenario=str(first.get("scenario") or source.stem),
        match=dict(first.get("match") or {}),
        directions=dict(first.get("directions") or {}),
    )
    items: list[ReplayItem] = []
    previous_at = -1
    for line_number, value in iterator:
        kind = value.get("type")
        if kind not in ("frame", "command", "expectation"):
            raise ValueError(f"Unsupported recording item on line {line_number}")
        at_ms = int(value.get("at_ms", -1))
        if at_ms < previous_at:
            raise ValueError("Recording timeline must be monotonically increasing")
        previous_at = at_ms
        items.append(ReplayItem(
            kind=kind,
            at_ms=at_ms,
            observation=observation_from_dict(value["observation"]) if kind == "frame" else None,
            command=dict(value.get("command") or {}) if kind == "command" else None,
            expectation=dict(value.get("expectation") or {}) if kind == "expectation" else None,
        ))
    if not any(item.observation is not None for item in items):
        raise ValueError("Recording does not contain any frames")
    return ObservationRecording(header=header, items=tuple(items))
