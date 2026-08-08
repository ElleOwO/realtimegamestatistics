"""Thread-safe operator-controlled state for the live analytics runtime."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

VALID_PHASES = {"pregame", "first_half", "halftime", "second_half", "full_time"}


class LiveMatchController:
    def __init__(self) -> None:
        data_root = Path(os.environ.get("RTGS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
        self._path = data_root / "live_match_state.json"
        self._lock = threading.RLock()
        self._clock_anchor = time.monotonic()
        self._state: dict[str, Any] = {
            "team_names": ["USask", "Opponent"],
            "score": [0, 0],
            "phase": "pregame",
            "period": None,
            "clock_s": 0.0,
            "directions": {"first_half": ["right", "left"], "second_half": ["left", "right"]},
            "tactical_targets": {"team0": {"in_possession": {}, "out_of_possession": {}}, "team1": {"in_possession": {}, "out_of_possession": {}}},
        }
        self._load()

    @staticmethod
    def _running(phase: str) -> bool:
        return phase in ("first_half", "second_half")

    def _materialize_clock(self) -> None:
        now = time.monotonic()
        if self._running(self._state["phase"]):
            self._state["clock_s"] += max(0.0, now - self._clock_anchor)
        self._clock_anchor = now

    def _load(self) -> None:
        try:
            loaded = json.loads(self._path.read_text())
            if isinstance(loaded, dict):
                self._state.update(loaded)
        except (OSError, ValueError):
            pass
        self._clock_anchor = time.monotonic()

    def _persist(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self._state, indent=2))
            temporary.replace(self._path)
        except OSError:
            pass

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._materialize_clock()
            state = json.loads(json.dumps(self._state))
            state["clock_s"] = round(float(state["clock_s"]), 2)
            state["clock_running"] = self._running(state["phase"])
            return state

    def directions(self) -> dict[str, str]:
        state = self.snapshot()
        phase = state["phase"]
        key = "second_half" if phase == "second_half" else "first_half"
        return {"team0": state["directions"][key][0], "team1": state["directions"][key][1]}

    def apply(self, command: dict[str, Any]) -> tuple[bool, str | None, bool]:
        """Apply a command and return (ok, error, reset_metrics)."""
        kind = command.get("type")
        payload = command.get("payload") or {}
        reset_metrics = False
        with self._lock:
            self._materialize_clock()
            try:
                if kind == "match.configure":
                    if "team_names" in payload:
                        names = payload["team_names"]
                        if not isinstance(names, list) or len(names) != 2 or not all(str(name).strip() for name in names):
                            raise ValueError("team_names must contain two non-empty names")
                        self._state["team_names"] = [str(name).strip()[:80] for name in names]
                    if "directions" in payload:
                        directions = payload["directions"]
                        for phase in ("first_half", "second_half"):
                            values = directions.get(phase)
                            if values not in (["left", "right"], ["right", "left"]):
                                raise ValueError(f"{phase} directions must be opposing left/right values")
                        self._state["directions"] = directions
                elif kind == "match.set_phase":
                    phase = payload.get("phase")
                    if phase not in VALID_PHASES:
                        raise ValueError("invalid match phase")
                    self._state["phase"] = phase
                    self._state["period"] = 1 if phase == "first_half" else 2 if phase == "second_half" else None
                elif kind == "match.set_clock":
                    self._state["clock_s"] = max(0.0, float(payload["clock_s"]))
                elif kind == "match.set_score":
                    score = payload.get("score")
                    if not isinstance(score, list) or len(score) != 2:
                        raise ValueError("score must contain two values")
                    self._state["score"] = [max(0, int(score[0])), max(0, int(score[1]))]
                elif kind == "match.set_targets":
                    targets = payload.get("tactical_targets")
                    if not isinstance(targets, dict):
                        raise ValueError("tactical_targets must be an object")
                    for team, phases in targets.items():
                        if team not in ("team0", "team1") or not isinstance(phases, dict):
                            raise ValueError("targets must be grouped by team0/team1")
                        for phase, values in phases.items():
                            if phase not in ("in_possession", "out_of_possession") or not isinstance(values, dict):
                                raise ValueError("targets must be grouped by possession phase")
                            for bounds in values.values():
                                if not isinstance(bounds, dict):
                                    raise ValueError("each target must contain min/max bounds")
                                lower, upper = bounds.get("min"), bounds.get("max")
                                if lower is not None:
                                    float(lower)
                                if upper is not None:
                                    float(upper)
                                if lower is not None and upper is not None and float(lower) > float(upper):
                                    raise ValueError("target minimum cannot exceed maximum")
                    self._state["tactical_targets"] = targets
                elif kind == "match.reset":
                    self._state.update({"score": [0, 0], "phase": "pregame", "period": None, "clock_s": 0.0})
                    reset_metrics = True
                else:
                    return False, "unsupported command", False
            except (KeyError, TypeError, ValueError) as exc:
                return False, str(exc), False
            self._clock_anchor = time.monotonic()
            self._persist()
            return True, None, reset_metrics
