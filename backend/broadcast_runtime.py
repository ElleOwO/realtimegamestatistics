"""Recoverable source-time orchestration around the one shared analytics engine."""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import replace
from pathlib import Path

from analytics_core import AnalyticsEngine
from live_state import LiveMatchController
from observation_io import (RecordingHeader, ReplayItem, observation_from_dict,
                            observation_to_dict, write_recording)


class BroadcastRuntime:
    def __init__(self, root: Path, run_id: str, coeffs: dict):
        self.root, self.run_id, self.coeffs = root, run_id, coeffs
        root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.records = []
        self.path = root / "timeline.jsonl"
        if self.path.exists():
            lines = self.path.read_text().splitlines()
            for index, line in enumerate(lines):
                try:
                    self.records.append(json.loads(line))
                except json.JSONDecodeError:
                    if index != len(lines) - 1:
                        raise ValueError("Recovery journal is corrupt before its final record.") from None
                    break  # A killed writer can leave only the final line incomplete.
        self._rebuild()
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            for value in self.records:
                stream.write(json.dumps(value, separators=(",", ":")) + "\n")
        temporary.replace(self.path)
        self.writer = self.path.open("a")
        self.last_observed_at = time.time()

    def _reset(self):
        self.source_ms = 0
        self.enabled = False
        self.teams_confirmed = False
        self.usask_cluster = 0
        self.controller = LiveMatchController(clock=lambda: self.source_ms / 1000, persist=False, load_existing=False)
        self.engine = AnalyticsEngine(self.coeffs, event_namespace=self.run_id)
        self.latest = None
        self.covered_ms = self.active_ms = 0
        self.previous_ms = None
        self.pending_gap = False

    def _rebuild(self):
        self._reset()
        exclusions = [v["command"]["payload"] for v in self.records
                      if v.get("command", {}).get("type") == "analysis.exclude_interval"]
        for value in sorted(enumerate(self.records), key=lambda v: (v[1]["at_ms"], v[0])):
            item = value[1]
            self.source_ms = item["at_ms"]
            if "command" in item:
                self._command(item["command"], rebuilding=True)
            else:
                observation = observation_from_dict(item["observation"])
                excluded = any(e["start_ms"] <= self.source_ms <= e["end_ms"] for e in exclusions)
                self._frame(observation, excluded=excluded, gap=item.get("gap", False))

    def _append(self, value):
        self.records.append(value)
        self.writer.write(json.dumps(value, separators=(",", ":")) + "\n")
        self.writer.flush()

    def _frame(self, observation, *, excluded=False, gap=False):
        gap = gap or self.pending_gap
        self.pending_gap = False
        self.source_ms = observation.timestamp_ms
        state = self.controller.snapshot()
        active = state["phase"] in ("first_half", "second_half")
        elapsed = max(0, self.source_ms - self.previous_ms) if self.previous_ms is not None else 0
        self.previous_ms = self.source_ms
        usable = self.enabled and self.teams_confirmed and not excluded and not gap
        if active:
            self.active_ms += elapsed
            if usable and elapsed <= 1000 and observation.calibration_confidence >= 0.5 and observation.ball is not None:
                self.covered_ms += elapsed
        if not usable or elapsed > 1000 or observation.calibration_confidence < .5 or observation.ball is None:
            self.engine.discontinuity()
        players = observation.players
        if self.usask_cluster == 1:
            players = [replace(p, team="team1" if p.team == "team0" else "team0") for p in players]
        self.latest = replace(observation, players=players if usable else [],
                              ball=observation.ball if usable else None,
                              calibration_confidence=observation.calibration_confidence if usable else 0,
                              phase=state["phase"], period=state["period"], match_clock_s=state["clock_s"])
        self.engine.update(self.latest, self.controller.directions())

    def frame(self, observation, gap=False):
        with self.lock:
            if self.latest and observation.timestamp_ms <= self.latest.timestamp_ms:
                return
            self._append({"at_ms": observation.timestamp_ms, "observation": observation_to_dict(observation), "gap": gap})
            self._frame(observation, gap=gap)
            self.last_observed_at = time.time()

    def _command(self, command, rebuilding=False):
        kind, payload = command.get("type"), command.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("Command payload must be an object.")
        if kind == "analysis.discontinuity":
            self.engine.discontinuity()
            self.pending_gap = True
        elif kind == "analysis.invalidate_teams":
            self.enabled = self.teams_confirmed = False
            self.engine.discontinuity()
        elif kind == "analysis.set_enabled":
            if not isinstance(payload.get("enabled"), bool):
                raise ValueError("enabled must be true or false")
            if payload["enabled"] and not self.teams_confirmed:
                raise ValueError("Confirm team colors first.")
            self.enabled = payload["enabled"]
            self.engine.discontinuity()
        elif kind == "analysis.confirm_teams":
            if type(payload.get("usask_cluster")) is not int or payload["usask_cluster"] not in (0, 1):
                raise ValueError("Choose team color 0 or 1.")
            if self.enabled:
                raise ValueError("Pause analysis before changing team mapping.")
            self.usask_cluster = payload["usask_cluster"]
            self.teams_confirmed = True
        elif kind == "analysis.exclude_interval":
            start, end = float(payload["start_ms"]), float(payload["end_ms"])
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end <= self.source_ms):
                raise ValueError("Choose an interval within the processed broadcast.")
        elif kind == "event.review":
            event_id = payload.get("event_id")
            previous = next((dict(e) for e in self.engine.events if e["id"] == event_id), None)
            if previous is None:
                if rebuilding:
                    return  # The source interval that produced this event was excluded.
                raise ValueError("Event not found.")
            patch = payload.get("patch", payload)
            if not isinstance(patch, dict):
                raise ValueError("Review patch must be an object.")
            if "team" in patch and patch["team"] not in ("team0", "team1"):
                raise ValueError("Invalid team.")
            if "location" in patch:
                point = patch["location"]
                if not isinstance(point, list) or len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in point) or not (0 <= point[0] <= 105 and 0 <= point[1] <= 68):
                    raise ValueError("Shot location must be on the pitch.")
            if "on_target" in patch and patch["on_target"] is not None and type(patch["on_target"]) is not bool:
                raise ValueError("on_target must be true, false, or unavailable.")
            if patch.get("status", "candidate") not in ("candidate", "confirmed", "corrected", "rejected"):
                raise ValueError("Invalid review status.")
            self.engine.review_event(event_id, patch, self.controller.directions())
            current = next(e for e in self.engine.events if e["id"] == event_id)
            score = self.controller.snapshot()["score"]
            for event, delta in ((previous, -1), (current, 1)):
                if event.get("outcome") == "goal" and event.get("status") in ("confirmed", "corrected") and event.get("team") in ("team0", "team1"):
                    score[0 if event["team"] == "team0" else 1] += delta
            self.controller.apply({"type": "match.set_score", "payload": {"score": score}})
        else:
            ok, error, reset = self.controller.apply(command)
            if not ok:
                raise ValueError(error)
            if reset:
                self.engine.reset()
                self.active_ms = self.covered_ms = 0
                self.enabled = False

    def command(self, command):
        with self.lock:
            if not isinstance(command, dict):
                raise ValueError("Command must be an object.")
            at_ms = command.get("source_timestamp_ms", self.source_ms)
            if not isinstance(at_ms, (int, float)) or not math.isfinite(at_ms) or not 0 <= at_ms <= self.source_ms:
                raise ValueError("Command time must refer to a processed frame.")
            command_id = command.get("command_id")
            if command_id and any(v.get("command", {}).get("command_id") == command_id for v in self.records):
                return
            if command.get("type") == "event.review":
                event = next((e for e in self.engine.events if e["id"] == command.get("payload", {}).get("event_id")), None)
                if event is None or at_ms < event["timestamp_ms"]:
                    raise ValueError("Review must refer to an event already observed at that video time.")
            item = {"at_ms": int(at_ms), "command": command}
            # Validate the entire resulting timeline before writing. A retroactive
            # command can be valid now but invalid at its selected video time.
            self.records.append(item)
            try:
                self._rebuild()
            except (ValueError, TypeError, KeyError):
                self.records.pop()
                self._rebuild()
                raise
            self.writer.write(json.dumps(item, separators=(",", ":")) + "\n")
            self.writer.flush()

    def snapshot(self):
        result = self.engine.snapshot()
        result["quality_coverage"] = self.covered_ms / self.active_ms if self.active_ms else 0
        # Preserve the existing engine contract; confirmed totals are an additive
        # presentation field, so replay/post-game consumers remain compatible.
        for index, chance in enumerate(result["chance_quality"]["teams"]):
            confirmed = [e for e in self.engine.events if e["type"] == "shot" and e["team"] == f"team{index}" and e["status"] in ("confirmed", "corrected")]
            chance["confirmed_shots"] = len(confirmed)
            chance["confirmed_xg"] = round(sum(e.get("xg", 0) for e in confirmed), 3)
        return result

    def export(self):
        with self.lock:
            # Each snapshot is closed and atomically replaced. No open gzip is exported.
            items = []
            for v in self.records:
                if v.get("gap"):
                    items.append(ReplayItem("command", v["at_ms"], command={"type": "analysis.discontinuity"}))
                items.append(ReplayItem("frame" if "observation" in v else "command", v["at_ms"],
                                        observation=observation_from_dict(v["observation"]) if "observation" in v else None,
                                        command=v.get("command")))
            write_recording(self.root / "observations.jsonl.gz", RecordingHeader(scenario=self.run_id, match={"runtime": "broadcast"}),
                            sorted(items, key=lambda item: item.at_ms))
            summary = {"match": self.controller.snapshot(), "analytics": self.snapshot(), "run_id": self.run_id,
                       "last_observed_at": self.last_observed_at}
            (self.root / "run-summary.json").write_text(json.dumps(summary))
            return summary

    def close(self):
        self.export()
        self.writer.close()
