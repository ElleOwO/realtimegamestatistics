"""Shared, dependency-light soccer analytics primitives.

The live camera runtime and the post-game worker both feed canonical 105 x 68
metre observations into this module.  Nothing here imports the CV stack,
FastAPI, or SQLAlchemy, so the metric definitions remain cheap to test.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal, Sequence

PitchPoint = tuple[float, float]
TeamCode = Literal["team0", "team1"]
PossessionState = Literal["team0", "team1", "contested", "unknown"]
Direction = Literal["left", "right"]
MatchPhase = Literal["pregame", "first_half", "halftime", "second_half", "full_time"]

PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
GOAL_WIDTH_M = 7.32
FINAL_THIRD_M = 70.0
PENALTY_AREA_M = 88.5
PENALTY_HALF_WIDTH_M = 20.16
CONTROL_RADIUS_M = 2.5


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def euclidean(first: PitchPoint, second: PitchPoint) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def normalize_longitudinal(x_m: float, attacks: Direction) -> float:
    """Return progress from the team's own goal (0) to opponent goal (105)."""
    return x_m if attacks == "right" else PITCH_LENGTH_M - x_m


def attacking_channel(y_m: float, attacks: Direction) -> Literal["left", "centre", "right"]:
    """Return a flank from the attacking team's perspective."""
    oriented_y = y_m if attacks == "right" else PITCH_WIDTH_M - y_m
    if oriented_y < PITCH_WIDTH_M / 3:
        return "left"
    if oriented_y < PITCH_WIDTH_M * 2 / 3:
        return "centre"
    return "right"


def shot_features(point: PitchPoint, attacks: Direction) -> tuple[float, float]:
    """Distance and robust goal-mouth angle on the canonical pitch."""
    goal_x = PITCH_LENGTH_M if attacks == "right" else 0.0
    goal_y = PITCH_WIDTH_M / 2
    left_post = (goal_x, goal_y - GOAL_WIDTH_M / 2)
    right_post = (goal_x, goal_y + GOAL_WIDTH_M / 2)
    first = (left_post[0] - point[0], left_post[1] - point[1])
    second = (right_post[0] - point[0], right_post[1] - point[1])
    cross = abs(first[0] * second[1] - first[1] * second[0])
    dot = first[0] * second[0] + first[1] * second[1]
    angle = math.atan2(cross, dot)
    return math.hypot(goal_x - point[0], goal_y - point[1]), angle


def calculate_xg(
    point: PitchPoint,
    attacks: Direction,
    coeffs: dict[str, float],
) -> float:
    distance, angle = shot_features(point, attacks)
    log_odds = coeffs["intercept"] + coeffs["distance"] * distance + coeffs["angle"] * angle
    return clamp(1.0 / (1.0 + math.exp(-log_odds)), 0.01, 0.99)


def metric(
    value: Any,
    *,
    confidence: float,
    coverage: float,
    status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    confidence = clamp(float(confidence), 0.0, 1.0)
    coverage = clamp(float(coverage), 0.0, 1.0)
    if value is None:
        return {
            "value": None,
            "confidence": confidence,
            "coverage": coverage,
            "status": "unavailable",
            "reason": reason or "No quality-gated observations are available.",
        }
    return {
        "value": value,
        "confidence": confidence,
        "coverage": coverage,
        "status": status or ("available" if coverage >= 0.5 else "partial"),
        "reason": reason,
    }


def period_at(timestamp_ms: int, periods: Sequence[dict]) -> int | None:
    for period in periods:
        if int(period["start_ms"]) <= timestamp_ms <= int(period["end_ms"]):
            return int(period["number"])
    return None


def match_phase(timestamp_ms: int, periods: Sequence[dict]) -> str:
    ordered = sorted(periods, key=lambda item: item["start_ms"])
    if not ordered or timestamp_ms < ordered[0]["start_ms"]:
        return "pregame"
    current = period_at(timestamp_ms, ordered)
    if current == 1:
        return "first_half"
    if current == 2:
        return "second_half"
    if current is not None:
        return f"period_{current}"
    if timestamp_ms > ordered[-1]["end_ms"]:
        return "finished"
    return "halftime"


def match_clock_ms(timestamp_ms: int, periods: Sequence[dict]) -> int:
    elapsed = 0
    for period in sorted(periods, key=lambda item: item["number"]):
        start, end = int(period["start_ms"]), int(period["end_ms"])
        if timestamp_ms >= end:
            elapsed += end - start
        elif timestamp_ms > start:
            elapsed += timestamp_ms - start
            break
        else:
            break
    return elapsed


class PossessionTracker:
    """Timestamp-based control hysteresis with explicit unknown coverage."""

    def __init__(self) -> None:
        self.state: PossessionState = "unknown"
        self._candidate: PossessionState | None = None
        self._candidate_since_ms: int | None = None
        self._last_usable_ms: int | None = None

    def reset(self) -> None:
        self.__init__()

    def update(
        self,
        timestamp_ms: int,
        ball: PitchPoint | None,
        players: dict[str, Sequence[PitchPoint]],
        calibration_usable: bool,
    ) -> PossessionState:
        if ball is None or not calibration_usable:
            if self._last_usable_ms is None or timestamp_ms - self._last_usable_ms > 500:
                self.state = "unknown"
                self._candidate = None
            return self.state

        self._last_usable_ms = timestamp_ms
        team_keys = ("home", "away") if "home" in players or "away" in players else ("team0", "team1")
        closest = {
            team: min((euclidean(ball, point) for point in players.get(team, [])), default=math.inf)
            for team in team_keys
        }
        candidates = [team for team, distance in closest.items() if distance <= CONTROL_RADIUS_M]
        if len(candidates) == 2 and abs(closest[team_keys[0]] - closest[team_keys[1]]) <= 0.5:
            observed: PossessionState = "contested"
        elif candidates:
            observed = min(candidates, key=lambda team: closest[team])  # type: ignore[assignment]
        else:
            observed = "unknown"

        if observed in ("unknown", "contested"):
            self.state = observed
            self._candidate = None
            return self.state
        if observed == self.state:
            self._candidate = None
            return self.state
        if observed != self._candidate:
            self._candidate = observed
            self._candidate_since_ms = timestamp_ms
            return self.state
        threshold = 400 if self.state in ("unknown", "contested") else 600
        if self._candidate_since_ms is not None and timestamp_ms - self._candidate_since_ms >= threshold:
            self.state = observed
            self._candidate = None
        return self.state


@dataclass(frozen=True)
class BoundaryEntry:
    timestamp_ms: int
    team: str
    kind: Literal["final_third", "penalty_area"]
    lane: Literal["left", "centre", "right"]
    point: PitchPoint


class EntryDetector:
    """Quality-gated, hysteretic controlled boundary crossings."""

    def __init__(self) -> None:
        self._previous: dict[str, tuple[int, float]] = {}
        self._armed: dict[tuple[str, str], bool] = defaultdict(lambda: True)
        self._last_entry_ms: dict[tuple[str, str], int] = {}

    def reset(self) -> None:
        self.__init__()

    def update(
        self,
        timestamp_ms: int,
        team: str,
        ball: PitchPoint,
        attacks: Direction,
        controlled: bool,
    ) -> list[BoundaryEntry]:
        progress = normalize_longitudinal(ball[0], attacks)
        previous_sample = self._previous.get(team)
        self._previous[team] = (timestamp_ms, progress)
        for kind, boundary in (("final_third", FINAL_THIRD_M), ("penalty_area", PENALTY_AREA_M)):
            if progress <= boundary - 2.0:
                self._armed[(team, kind)] = True
        if not controlled or previous_sample is None or timestamp_ms - previous_sample[0] > 500:
            return []
        previous = previous_sample[1]
        lane = attacking_channel(ball[1], attacks)
        entries: list[BoundaryEntry] = []
        for kind, boundary in (("final_third", FINAL_THIRD_M), ("penalty_area", PENALTY_AREA_M)):
            key = (team, kind)
            inside_width = kind == "final_third" or abs(ball[1] - PITCH_WIDTH_M / 2) <= PENALTY_HALF_WIDTH_M
            if (
                self._armed[key]
                and previous < boundary <= progress
                and inside_width
                and timestamp_ms - self._last_entry_ms.get(key, -10_000) >= 2000
            ):
                entries.append(BoundaryEntry(timestamp_ms, team, kind, lane, ball))  # type: ignore[arg-type]
                self._last_entry_ms[key] = timestamp_ms
                self._armed[key] = False
        return entries


@dataclass(frozen=True)
class PossessionChange:
    timestamp_ms: int
    previous_team: str
    new_team: str
    location: PitchPoint | None
    high_turnover: bool
    dangerous_turnover: bool


def classify_possession_change(
    timestamp_ms: int,
    previous_team: str,
    new_team: str,
    ball: PitchPoint | None,
    directions: dict[str, Direction],
) -> PossessionChange:
    regain_progress = normalize_longitudinal(ball[0], directions[new_team]) if ball else 0.0
    loss_progress = normalize_longitudinal(ball[0], directions[previous_team]) if ball else PITCH_LENGTH_M
    return PossessionChange(
        timestamp_ms,
        previous_team,
        new_team,
        ball,
        bool(ball and regain_progress >= FINAL_THIRD_M),
        bool(ball and loss_progress <= PITCH_LENGTH_M / 3),
    )


def counterattack_initiated(
    regain_ms: int,
    regain_point: PitchPoint,
    samples: Iterable[tuple[int, PitchPoint]],
    attacks: Direction,
) -> bool:
    initial = normalize_longitudinal(regain_point[0], attacks)
    for timestamp_ms, point in samples:
        if timestamp_ms - regain_ms > 10_000:
            break
        progress = normalize_longitudinal(point[0], attacks)
        if progress - initial >= 15.0 or progress >= FINAL_THIRD_M:
            return True
    return False


def polygon_area(points: Sequence[PitchPoint]) -> float:
    ordered = sorted(set(points))
    if len(ordered) < 3:
        return 0.0

    def cross(origin: PitchPoint, first: PitchPoint, second: PitchPoint) -> float:
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])

    lower: list[PitchPoint] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[PitchPoint] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return abs(sum(hull[index][0] * hull[(index + 1) % len(hull)][1] - hull[(index + 1) % len(hull)][0] * hull[index][1] for index in range(len(hull)))) / 2


def shape_metrics(
    players: Sequence[PitchPoint],
    attacks: Direction,
    visible_pitch_fraction: float,
    ball: PitchPoint | None = None,
    goalkeeper: PitchPoint | None = None,
) -> dict[str, float] | None:
    if len(players) < 7 or visible_pitch_fraction < 0.55:
        return None
    progress = sorted(normalize_longitudinal(point[0], attacks) for point in players)
    lateral = [point[1] for point in players]
    centers = [progress[len(progress) // 6], progress[len(progress) // 2], progress[min(len(progress) * 5 // 6, len(progress) - 1)]]
    for _ in range(20):
        groups: list[list[float]] = [[], [], []]
        for value in progress:
            groups[min(range(3), key=lambda candidate: abs(value - centers[candidate]))].append(value)
        updated = [sum(group) / len(group) if group else centers[index] for index, group in enumerate(groups)]
        if max(abs(first - second) for first, second in zip(centers, updated)) < 0.01:
            break
        centers = updated
    lines = sorted(centers)
    centroid_x = sum(point[0] for point in players) / len(players)
    centroid_y = sum(lateral) / len(lateral)
    centroid = (centroid_x, centroid_y)
    length = max(progress) - min(progress)
    width = max(lateral) - min(lateral)
    behind_ball = 0
    if ball is not None:
        ball_progress = normalize_longitudinal(ball[0], attacks)
        behind_ball = sum(value < ball_progress for value in progress)
    result = {
        "defensive_line_height_m": lines[0],
        "team_length_m": length,
        "width_m": width,
        "centroid_x_m": centroid_x,
        "centroid_y_m": centroid_y,
        "convex_hull_area_m2": polygon_area(players),
        "compactness_m": sum(euclidean(point, centroid) for point in players) / len(players),
        "players_behind_ball": float(behind_ball),
        "line_1_centroid_m": lines[0],
        "line_2_centroid_m": lines[1],
        "line_3_centroid_m": lines[2],
        "line_gap_1_m": lines[1] - lines[0],
        "line_gap_2_m": lines[2] - lines[1],
    }
    if goalkeeper is not None:
        result["goalkeeper_line_gap_m"] = max(0.0, lines[0] - normalize_longitudinal(goalkeeper[0], attacks))
    return result


class ShotDetector:
    """Timestamp-aware shot detector retaining the acceleration origin."""

    def __init__(self) -> None:
        self.history: deque[tuple[int, PitchPoint]] = deque(maxlen=5)
        self.last_shot_ms = -10_000
        self.last_origin: PitchPoint | None = None

    def reset(self) -> None:
        self.__init__()

    def update(self, timestamp_ms: int, ball: PitchPoint | None, attacks: Direction) -> tuple[bool, float]:
        if ball is None:
            return False, 0.0
        if self.history and timestamp_ms - self.history[-1][0] > 500:
            self.history.clear()
        if self.history:
            previous = self.history[-1][1]
            longitudinal = abs(normalize_longitudinal(ball[0], attacks) - normalize_longitudinal(previous[0], attacks))
            lateral = abs(ball[1] - previous[1])
            if lateral > max(8.0, longitudinal * 2.0):
                self.history.clear()
        self.history.append((timestamp_ms, ball))
        if len(self.history) < 4 or timestamp_ms - self.last_shot_ms < 2000:
            return False, 0.0
        start_ms, start = self.history[0]
        elapsed = max((timestamp_ms - start_ms) / 1000, 0.001)
        speed = euclidean(start, ball) / elapsed
        samples = list(self.history)
        progression = normalize_longitudinal(ball[0], attacks) - normalize_longitudinal(start[0], attacks)
        steps = [normalize_longitudinal(second[1][0], attacks) - normalize_longitudinal(first[1][0], attacks) for first, second in zip(samples, samples[1:])]
        if speed >= 14.0 and progression > 0 and all(value > 0 for value in steps) and normalize_longitudinal(start[0], attacks) >= FINAL_THIRD_M:
            self.last_shot_ms = timestamp_ms
            self.last_origin = start
            return True, speed
        return False, speed


@dataclass
class PlayerObservation:
    team: TeamCode
    point: PitchPoint
    confidence: float
    track_id: int | None = None
    role: Literal["outfield", "goalkeeper"] = "outfield"


@dataclass
class FrameObservation:
    frame_id: int
    timestamp_ms: int
    players: list[PlayerObservation]
    ball: PitchPoint | None
    ball_confidence: float | None
    calibration_confidence: float
    visible_pitch_fraction: float
    reprojection_error_m: float | None = None
    match_clock_s: float | None = None
    period: int | None = None
    phase: str | None = None


@dataclass
class PressureEpisode:
    team: TeamCode
    start_ms: int
    start_point: PitchPoint
    zone: str
    close_since_ms: int
    far_since_ms: int | None = None
    active: bool = False
    initial_opponent_progress: float = 0.0
    forced_long_created: bool = False


@dataclass
class AnalyticsEngine:
    coeffs: dict[str, float]
    possession: PossessionTracker = field(default_factory=PossessionTracker)
    entries: EntryDetector = field(default_factory=EntryDetector)
    shots: dict[str, ShotDetector] = field(default_factory=lambda: {"team0": ShotDetector(), "team1": ShotDetector()})
    events: list[dict[str, Any]] = field(default_factory=list)
    current_state: PossessionState = "unknown"
    last_controlled_team: TeamCode | None = None
    last_timestamp_ms: int | None = None
    state_durations_ms: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    attacking_third_control_ms: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    quality_samples: int = 0
    usable_samples: int = 0
    shape_samples: dict[str, dict[str, deque]] = field(default_factory=lambda: {
        team: {phase: deque() for phase in ("in_possession", "out_of_possession")}
        for team in ("team0", "team1")
    })
    last_loss_ms: dict[str, int] = field(default_factory=dict)
    pending_counters: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_pressures: dict[str, PressureEpisode] = field(default_factory=dict)
    last_line_sample: dict[str, tuple[int, float, float, int | None]] = field(default_factory=dict)
    line_armed: dict[str, bool] = field(default_factory=lambda: defaultdict(lambda: True))
    current_match_clock_s: float | None = None
    current_period: int | None = None
    current_phase: str | None = None

    def reset(self) -> None:
        coeffs = self.coeffs
        self.__dict__.update(AnalyticsEngine(coeffs).__dict__)

    def _event(self, kind: str, timestamp_ms: int, team: str | None, point: PitchPoint | None, **details: Any) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "type": kind,
            "timestamp_ms": timestamp_ms,
            "team": team,
            "location": list(point) if point else None,
            "status": "candidate",
            "confidence": details.pop("confidence", 0.0),
            "match_clock_s": self.current_match_clock_s,
            "period": self.current_period,
            **details,
        }
        self.events.append(event)
        return event

    def review_event(self, event_id: str, patch: dict[str, Any], directions: dict[str, Direction]) -> bool:
        event = next((item for item in self.events if item["id"] == event_id), None)
        if event is None:
            return False
        for key in ("status", "team", "on_target", "outcome", "play_context"):
            if key in patch:
                event[key] = patch[key]
        if "location" in patch and isinstance(patch["location"], (list, tuple)) and len(patch["location"]) == 2:
            event["location"] = [float(patch["location"][0]), float(patch["location"][1])]
        if event["type"] == "shot" and event.get("team") in directions and event.get("location"):
            event["xg"] = calculate_xg(tuple(event["location"]), directions[event["team"]], self.coeffs)
            event["box_shot"] = self._inside_penalty_area(tuple(event["location"]), directions[event["team"]])
        return True

    @staticmethod
    def _inside_penalty_area(point: PitchPoint, attacks: Direction) -> bool:
        return normalize_longitudinal(point[0], attacks) >= PENALTY_AREA_M and abs(point[1] - PITCH_WIDTH_M / 2) <= PENALTY_HALF_WIDTH_M

    def update(self, observation: FrameObservation, directions: dict[str, Direction]) -> dict[str, Any]:
        timestamp_ms = observation.timestamp_ms
        self.current_match_clock_s = observation.match_clock_s
        self.current_period = observation.period
        self.quality_samples += 1
        if observation.phase is not None and observation.phase != self.current_phase:
            self.possession.reset()
            self.entries.reset()
            for detector in self.shots.values():
                detector.reset()
            self.current_state = "unknown"
            self.last_controlled_team = None
            self.last_timestamp_ms = None
            self.pending_counters.clear()
            self.active_pressures.clear()
            self.last_line_sample.clear()
            self.line_armed.clear()
            self.current_phase = observation.phase
        if observation.phase is not None and observation.phase not in ("first_half", "second_half"):
            self.last_timestamp_ms = None
            self.current_state = "unknown"
            self.possession.reset()
            return self.snapshot()
        usable = observation.calibration_confidence >= 0.5 and observation.ball is not None
        if usable:
            self.usable_samples += 1
        players: dict[str, list[PitchPoint]] = {"team0": [], "team1": []}
        outfield: dict[str, list[PitchPoint]] = {"team0": [], "team1": []}
        goalkeepers: dict[str, PitchPoint | None] = {"team0": None, "team1": None}
        for player in observation.players:
            players[player.team].append(player.point)
            if player.role == "goalkeeper":
                goalkeepers[player.team] = player.point
            else:
                outfield[player.team].append(player.point)

        previous_state = self.current_state
        self.current_state = self.possession.update(timestamp_ms, observation.ball, players, usable)
        elapsed = 0
        if self.last_timestamp_ms is not None:
            elapsed = max(0, min(timestamp_ms - self.last_timestamp_ms, 2000))
            self.state_durations_ms[previous_state] += elapsed
        self.last_timestamp_ms = timestamp_ms

        if self.current_state in ("team0", "team1"):
            team: TeamCode = self.current_state
            if observation.ball and normalize_longitudinal(observation.ball[0], directions[team]) >= FINAL_THIRD_M:
                self.attacking_third_control_ms[team] += elapsed
            if self.last_controlled_team and self.last_controlled_team != team:
                change = classify_possession_change(timestamp_ms, self.last_controlled_team, team, observation.ball, directions)
                recovery = (timestamp_ms - self.last_loss_ms[team]) / 1000 if team in self.last_loss_ms else None
                self._event("possession_win", timestamp_ms, team, observation.ball, confidence=observation.calibration_confidence, recovery_time_s=recovery)
                self._event("possession_loss", timestamp_ms, self.last_controlled_team, observation.ball, confidence=observation.calibration_confidence, new_team=team)
                self.last_loss_ms[self.last_controlled_team] = timestamp_ms
                if change.high_turnover:
                    self._event("high_turnover", timestamp_ms, team, observation.ball, confidence=observation.calibration_confidence)
                if change.dangerous_turnover:
                    self._event("dangerous_turnover", timestamp_ms, self.last_controlled_team, observation.ball, confidence=observation.calibration_confidence)
                if observation.ball:
                    self.pending_counters[team] = {
                        "timestamp_ms": timestamp_ms,
                        "initial_progress": normalize_longitudinal(observation.ball[0], directions[team]),
                        "created": False,
                    }
            self.last_controlled_team = team

            if observation.ball and usable:
                pending = self.pending_counters.get(team)
                if pending and timestamp_ms - pending["timestamp_ms"] <= 10_000 and not pending["created"]:
                    progress = normalize_longitudinal(observation.ball[0], directions[team])
                    if progress - pending["initial_progress"] >= 15 or progress >= FINAL_THIRD_M:
                        self._event("counterattack", timestamp_ms, team, observation.ball, confidence=observation.calibration_confidence)
                        pending["created"] = True
                for entry in self.entries.update(timestamp_ms, team, observation.ball, directions[team], True):
                    self._event(f"{entry.kind}_entry", timestamp_ms, team, entry.point, confidence=observation.calibration_confidence, lane=entry.lane)
                shot, speed = self.shots[team].update(timestamp_ms, observation.ball, directions[team])
                if shot and self.shots[team].last_origin:
                    origin = self.shots[team].last_origin
                    regain = self.pending_counters.get(team)
                    self._event(
                        "shot",
                        timestamp_ms,
                        team,
                        origin,
                        confidence=min(observation.calibration_confidence, observation.ball_confidence or 0.0, 0.8),
                        xg=calculate_xg(origin, directions[team], self.coeffs),
                        speed_mps=speed,
                        box_shot=self._inside_penalty_area(origin, directions[team]),
                        on_target=None,
                        outcome=None,
                        play_context=None,
                        shot_after_regain=bool(regain and timestamp_ms - regain["timestamp_ms"] <= 10_000),
                    )

        current_shapes = self._update_shapes(observation, outfield, goalkeepers, directions)
        self._update_line_breaks(observation, players, current_shapes, directions)
        self._update_pressing(observation, players, directions)
        return self.snapshot()

    def _update_shapes(
        self,
        observation: FrameObservation,
        outfield: dict[str, list[PitchPoint]],
        goalkeepers: dict[str, PitchPoint | None],
        directions: dict[str, Direction],
    ) -> dict[str, dict[str, float] | None]:
        current: dict[str, dict[str, float] | None] = {"team0": None, "team1": None}
        for team in ("team0", "team1"):
            values = shape_metrics(outfield[team], directions[team], observation.visible_pitch_fraction, observation.ball, goalkeepers[team])
            if values is None or observation.calibration_confidence < 0.5:
                continue
            current[team] = values
            phase = "in_possession" if self.current_state == team else "out_of_possession"
            samples = self.shape_samples[team][phase]
            samples.append((observation.timestamp_ms, values))
            while samples and observation.timestamp_ms - samples[0][0] > 10_000:
                samples.popleft()
        return current

    def _update_line_breaks(
        self,
        observation: FrameObservation,
        players: dict[str, list[PitchPoint]],
        shapes: dict[str, dict[str, float] | None],
        directions: dict[str, Direction],
    ) -> None:
        if self.current_state not in ("team0", "team1") or observation.ball is None:
            return
        team: TeamCode = self.current_state
        opponent: TeamCode = "team1" if team == "team0" else "team0"
        opponent_shape = shapes[opponent]
        if opponent_shape is None:
            self.last_line_sample.pop(team, None)
            return
        opponent_height = opponent_shape["defensive_line_height_m"]
        line_x = opponent_height if directions[opponent] == "right" else PITCH_LENGTH_M - opponent_height
        line_progress = normalize_longitudinal(line_x, directions[team])
        ball_progress = normalize_longitudinal(observation.ball[0], directions[team])
        team_observations = [player for player in observation.players if player.team == team and player.role == "outfield"]
        nearest = min(team_observations, key=lambda player: euclidean(player.point, observation.ball), default=None)
        possessor = nearest.track_id if nearest and euclidean(nearest.point, observation.ball) <= CONTROL_RADIUS_M else None
        previous = self.last_line_sample.get(team)
        self.last_line_sample[team] = (observation.timestamp_ms, ball_progress, line_progress, possessor)
        if ball_progress <= line_progress - 2:
            self.line_armed[team] = True
        if not previous or observation.timestamp_ms - previous[0] > 500:
            return
        previous_gap = previous[1] - previous[2]
        current_gap = ball_progress - line_progress
        if self.line_armed[team] and previous_gap < 0 <= current_gap:
            method = "carry" if possessor is not None and possessor == previous[3] else "pass" if possessor is not None and previous[3] is not None else "unknown"
            self._event("behind_line_entry", observation.timestamp_ms, team, observation.ball, confidence=observation.calibration_confidence, method=method, lane=attacking_channel(observation.ball[1], directions[team]))
            self.line_armed[team] = False

    def _update_pressing(self, observation: FrameObservation, players: dict[str, list[PitchPoint]], directions: dict[str, Direction]) -> None:
        if self.current_state not in ("team0", "team1") or observation.ball is None or observation.calibration_confidence < 0.5:
            return
        possessing: TeamCode = self.current_state
        defending: TeamCode = "team1" if possessing == "team0" else "team0"
        nearest = min((euclidean(observation.ball, point) for point in players[defending]), default=math.inf)
        episode = self.active_pressures.get(defending)
        now = observation.timestamp_ms
        if nearest <= 3.0:
            if episode is None:
                episode = PressureEpisode(
                    defending,
                    now,
                    observation.ball,
                    attacking_channel(observation.ball[1], directions[defending]),
                    now,
                    initial_opponent_progress=normalize_longitudinal(observation.ball[0], directions[possessing]),
                )
                self.active_pressures[defending] = episode
            if not episode.active and now - episode.close_since_ms >= 300:
                episode.active = True
                self._event("pressure_attempt", episode.start_ms, defending, episode.start_point, confidence=observation.calibration_confidence, zone=episode.zone, high_press=normalize_longitudinal(episode.start_point[0], directions[defending]) >= FINAL_THIRD_M)
            episode.far_since_ms = None
        elif episode is not None:
            if nearest > 5.0:
                episode.far_since_ms = episode.far_since_ms or now
            if episode.far_since_ms is not None and now - episode.far_since_ms >= 500:
                if episode.active:
                    elapsed = (now - episode.start_ms) / 1000
                    opponent_progress = normalize_longitudinal(observation.ball[0], directions[possessing])
                    self._event("pressure_escape", now, possessing, observation.ball, confidence=observation.calibration_confidence, pressing_team=defending, escape_time_s=elapsed, central=attacking_channel(observation.ball[1], directions[possessing]) == "centre", forced_backward=opponent_progress <= episode.initial_opponent_progress - 8)
                self.active_pressures.pop(defending, None)

        episode = self.active_pressures.get(defending)
        if episode and episode.active and not episode.forced_long_created and now - episode.start_ms <= 3000 and euclidean(episode.start_point, observation.ball) >= 25:
            self._event("forced_long_candidate", now, defending, observation.ball, confidence=observation.calibration_confidence, zone=episode.zone)
            episode.forced_long_created = True

        for pressing_team, active in list(self.active_pressures.items()):
            if pressing_team == self.current_state and active.active:
                if now - active.start_ms <= 5000:
                    self._event("pressure_success", now, pressing_team, observation.ball, confidence=observation.calibration_confidence, zone=active.zone)
                self.active_pressures.pop(pressing_team, None)

    @staticmethod
    def _median_shape(samples: deque) -> dict[str, float] | None:
        if not samples:
            return None
        keys = set.intersection(*(set(values) for _, values in samples))
        result: dict[str, float] = {}
        for key in keys:
            ordered = sorted(float(values[key]) for _, values in samples)
            middle = len(ordered) // 2
            result[key] = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        return result

    def snapshot(self) -> dict[str, Any]:
        controlled_ms = self.state_durations_ms["team0"] + self.state_durations_ms["team1"]
        possession_coverage = controlled_ms / max(sum(self.state_durations_ms.values()), 1)
        possession = {
            "state": self.current_state,
            "team0_pct": (self.state_durations_ms["team0"] / controlled_ms * 100) if controlled_ms else None,
            "team1_pct": (self.state_durations_ms["team1"] / controlled_ms * 100) if controlled_ms else None,
            "coverage": possession_coverage,
        }
        usable_events = [event for event in self.events if event.get("status") != "rejected"]
        chance: list[dict[str, Any]] = []
        progression: list[dict[str, Any]] = []
        transitions: list[dict[str, Any]] = []
        pressing: list[dict[str, Any]] = []
        quality_coverage = self.usable_samples / max(self.quality_samples, 1)
        event_status = "unavailable" if self.usable_samples == 0 else "experimental" if quality_coverage >= 0.5 else "partial"
        tilt_total = self.attacking_third_control_ms["team0"] + self.attacking_third_control_ms["team1"]
        for team in ("team0", "team1"):
            shots = [event for event in usable_events if event["type"] == "shot" and event["team"] == team]
            chance.append({
                "status": event_status,
                "shots": len(shots),
                "pending_shots": sum(event["status"] == "candidate" for event in shots),
                "shots_on_target": sum(event.get("on_target") is True for event in shots),
                "reviewed_on_target": sum(event.get("on_target") is not None for event in shots),
                "box_shots": sum(bool(event.get("box_shot")) for event in shots),
                "xg": round(sum(float(event.get("xg", 0.0)) for event in shots), 3),
                "open_play_shots": sum(event.get("play_context") == "open_play" for event in shots),
                "open_play_xg": round(sum(float(event.get("xg", 0.0)) for event in shots if event.get("play_context") == "open_play"), 3),
                "set_piece_shots": sum(event.get("play_context") == "set_piece" for event in shots),
                "set_piece_xg": round(sum(float(event.get("xg", 0.0)) for event in shots if event.get("play_context") == "set_piece"), 3),
            })
            team_entries = [event for event in usable_events if event["team"] == team and event["type"] in ("final_third_entry", "penalty_area_entry")]
            lanes = {lane: sum(event.get("lane") == lane and event["type"] == "final_third_entry" for event in team_entries) for lane in ("left", "centre", "right")}
            progression.append({
                "status": event_status,
                "final_third_entries": sum(event["type"] == "final_third_entry" for event in team_entries),
                "penalty_area_entries": sum(event["type"] == "penalty_area_entry" for event in team_entries),
                "entry_channels": lanes,
                "field_tilt_pct": self.attacking_third_control_ms[team] / tilt_total * 100 if tilt_total else None,
                "behind_line_entries": sum(event["team"] == team and event["type"] == "behind_line_entry" for event in usable_events),
                "line_break_methods": {
                    method: sum(event["team"] == team and event["type"] == "behind_line_entry" and event.get("method") == method for event in usable_events)
                    for method in ("pass", "carry", "unknown")
                },
            })
            wins = [event for event in usable_events if event["team"] == team and event["type"] == "possession_win"]
            recoveries = [float(event["recovery_time_s"]) for event in wins if event.get("recovery_time_s") is not None]
            transitions.append({
                "status": event_status,
                "high_regains": sum(event["team"] == team and event["type"] == "high_turnover" for event in usable_events),
                "dangerous_losses": sum(event["team"] == team and event["type"] == "dangerous_turnover" for event in usable_events),
                "counterattacks": sum(event["team"] == team and event["type"] == "counterattack" for event in usable_events),
                "shots_after_regain": sum(event["team"] == team and event["type"] == "shot" and event.get("shot_after_regain") for event in usable_events),
                "opponent_shots_after_loss": sum(event["team"] != team and event["type"] == "shot" and event.get("shot_after_regain") for event in usable_events),
                "average_recovery_s": sum(recoveries) / len(recoveries) if recoveries else None,
            })
            attempts = [event for event in usable_events if event["team"] == team and event["type"] == "pressure_attempt"]
            successes = [event for event in usable_events if event["team"] == team and event["type"] == "pressure_success"]
            escapes = [event for event in usable_events if event["type"] == "pressure_escape" and event.get("pressing_team") == team]
            pressing.append({
                "attempts": len(attempts),
                "successes": len(successes),
                "success_pct": len(successes) / len(attempts) * 100 if attempts else None,
                "high_press_attempts": sum(bool(event.get("high_press")) for event in attempts),
                "central_escapes": sum(bool(event.get("central")) for event in escapes),
                "forced_backward": sum(bool(event.get("forced_backward")) for event in escapes),
                "forced_long_candidates": sum(event["team"] == team and event["type"] == "forced_long_candidate" for event in usable_events),
                "average_escape_s": sum(float(event["escape_time_s"]) for event in escapes) / len(escapes) if escapes else None,
                "success_by_zone": {
                    zone: sum(event.get("zone") == zone for event in successes)
                    for zone in ("left", "centre", "right")
                },
                "opponent_final_third_entries_allowed": sum(event["team"] != team and event["type"] == "final_third_entry" for event in usable_events),
                "status": "unavailable" if self.usable_samples == 0 else "experimental",
            })
        return {
            "possession": possession,
            "chance_quality": {"teams": chance, "shots": [event for event in usable_events if event["type"] == "shot"]},
            "progression": {"teams": progression},
            "transitions": {"teams": transitions},
            "shape": {"teams": [{phase: self._median_shape(self.shape_samples[team][phase]) for phase in ("in_possession", "out_of_possession")} for team in ("team0", "team1")]},
            "pressing": {"teams": pressing},
            "events": usable_events[-100:],
            "quality_coverage": quality_coverage,
        }


def camera_cut_score(previous_histogram: Sequence[float], current_histogram: Sequence[float]) -> float:
    if len(previous_histogram) != len(current_histogram) or not previous_histogram:
        return 1.0
    return sum(abs(first - second) for first, second in zip(previous_histogram, current_histogram)) / 2.0
