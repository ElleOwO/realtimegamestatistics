from __future__ import annotations

import json
import os
import pickle
import subprocess
from collections import deque
from pathlib import Path
from typing import Any, Callable

from .analytics import (
    EntryDetector,
    PossessionTracker,
    ShotDetector,
    classify_possession_change,
    match_clock_ms,
    match_phase,
    normalize_longitudinal,
    period_at,
    shape_metrics,
)
from analytics_core import (
    AnalyticsEngine,
    FrameObservation,
    PlayerObservation,
    calculate_xg as shared_calculate_xg,
)
from .media import extract_preflight_frames
from .models import Match
from .worker import AnalysisBatch


class RoboflowVideoProcessor:
    """Lazy GPU processor for Veo MP4s.

    Heavy model packages are imported only inside preflight/analysis, keeping the
    API and report library usable on machines without the vision environment.
    """

    PLAYER_MODEL_ID = "spen-rtgs-oc4ez/4"
    FIELD_MODEL_ID = "football-field-detection-f07vi/14"

    def __init__(self, analysis_hz: float = 10.0, keypoint_hz: float = 2.0):
        self.analysis_hz = analysis_hz
        self.keypoint_hz = keypoint_hz
        self._runtime: dict[str, Any] | None = None
        self._classifiers: dict[str, Any] = {}

    def _load_runtime(self) -> dict[str, Any]:
        if self._runtime is not None:
            return self._runtime
        api_key = os.environ.get("ROBOFLOW_API_KEY")
        if not api_key:
            raise RuntimeError("ROBOFLOW_API_KEY is required for preflight and analysis")
        try:
            import cv2
            import numpy as np
            import supervision as sv
            import torch
            from inference import get_model
            from sports.common.team import TeamClassifier
            from sports.common.view import ViewTransformer
            from sports.configs.soccer import SoccerPitchConfiguration
        except ImportError as exc:
            raise RuntimeError(
                "The vision environment is incomplete. Install backend/requirements.txt with Python 3.11 or 3.12."
            ) from exc
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self._runtime = {
            "cv2": cv2,
            "np": np,
            "sv": sv,
            "TeamClassifier": TeamClassifier,
            "ViewTransformer": ViewTransformer,
            "config": SoccerPitchConfiguration(),
            "player_model": get_model(model_id=self.PLAYER_MODEL_ID, api_key=api_key),
            "field_model": get_model(model_id=self.FIELD_MODEL_ID, api_key=api_key),
            "device": device,
        }
        return self._runtime

    @staticmethod
    def _player_crops(runtime: dict[str, Any], frame: Any) -> tuple[Any, list[Any]]:
        sv = runtime["sv"]
        result = runtime["player_model"].infer(frame, confidence=0.3)[0]
        detections = sv.Detections.from_inference(result)
        detections = detections.with_nms(threshold=0.5, class_agnostic=True)
        players = detections[detections.class_id == 2]
        return players, [sv.crop_image(frame, box) for box in players.xyxy]

    def preflight(self, match: Match, match_dir: Path) -> list[dict[str, Any]]:
        runtime = self._load_runtime()
        cv2, np = runtime["cv2"], runtime["np"]
        source = Path(match.source_path)
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise RuntimeError("Could not open imported match video")
        crops: list[Any] = []
        for fraction in (0.05, 0.12, 0.25, 0.38, 0.55, 0.68, 0.82, 0.92):
            cap.set(cv2.CAP_PROP_POS_MSEC, match.duration_ms * fraction)
            ok, frame = cap.read()
            if not ok:
                continue
            _, frame_crops = self._player_crops(runtime, frame)
            crops.extend(frame_crops)
            if len(crops) >= 80:
                break
        cap.release()
        if len(crops) < 20:
            raise RuntimeError(
                f"Preflight found only {len(crops)} player crops; at least 20 clear player detections are required"
            )
        classifier = runtime["TeamClassifier"](device=runtime["device"])
        classifier.fit(crops)
        labels = classifier.predict(crops)
        self._classifiers[match.id] = classifier
        try:
            with (match_dir / "team_classifier.pkl").open("wb") as destination:
                pickle.dump(classifier, destination)
        except Exception:
            (match_dir / "team_classifier.pkl").unlink(missing_ok=True)

        previews = match_dir / "preflight"
        previews.mkdir(exist_ok=True)
        clusters: list[dict[str, Any]] = []
        for cluster in (0, 1):
            selected = [crop for crop, label in zip(crops, labels) if int(label) == cluster][:12]
            if not selected:
                continue
            tiles = [cv2.resize(crop, (80, 140)) for crop in selected]
            while len(tiles) < 12:
                tiles.append(np.zeros_like(tiles[0]))
            rows = [np.hstack(tiles[index : index + 4]) for index in range(0, 12, 4)]
            mosaic = np.vstack(rows)
            path = previews / f"cluster-{cluster}.jpg"
            cv2.imwrite(str(path), mosaic)
            clusters.append(
                {
                    "cluster": cluster,
                    "preview_url": f"/api/v1/matches/{match.id}/preflight/{path.name}",
                    "sample_count": sum(int(label) == cluster for label in labels),
                }
            )
        if len(clusters) != 2:
            raise RuntimeError("Team classification did not produce two usable kit clusters")
        return clusters

    def _classifier(self, match: Match, match_dir: Path) -> Any:
        if match.id in self._classifiers:
            return self._classifiers[match.id]
        saved = match_dir / "team_classifier.pkl"
        if saved.is_file():
            try:
                with saved.open("rb") as source:
                    classifier = pickle.load(source)
                self._classifiers[match.id] = classifier
                return classifier
            except Exception:
                saved.unlink(missing_ok=True)
        self.preflight(match, match_dir)
        return self._classifiers[match.id]

    @staticmethod
    def _xg(point: tuple[float, float], attacks: str) -> float:
        coeff_path = Path(__file__).resolve().parents[1] / "xg_coeffs.json"
        coeffs = {"intercept": 0.6, "distance": -0.18, "angle": 3.0}
        try:
            coeffs.update(json.loads(coeff_path.read_text()))
        except (OSError, ValueError):
            pass
        return shared_calculate_xg(point, attacks, coeffs)

    def process(
        self,
        match: Match,
        match_dir: Path,
        emit: Callable[[AnalysisBatch], None],
        cancelled: Callable[[], bool],
    ) -> None:
        runtime = self._load_runtime()
        cv2, np, sv = runtime["cv2"], runtime["np"], runtime["sv"]
        classifier = self._classifier(match, match_dir)
        cap = cv2.VideoCapture(match.source_path)
        if not cap.isOpened():
            raise RuntimeError("Could not open imported match video")
        source_fps = cap.get(cv2.CAP_PROP_FPS) or match.fps or 30.0
        sample_stride = max(round(source_fps / self.analysis_hz), 1)
        keypoint_interval_ms = round(1000 / self.keypoint_hz)
        tracker = sv.ByteTrack()
        tracker.reset()
        possession = PossessionTracker()
        entry_detector = EntryDetector()
        shot_detectors = {"home": ShotDetector(), "away": ShotDetector()}
        coeff_path = Path(__file__).resolve().parents[1] / "xg_coeffs.json"
        core_coeffs = {"intercept": 0.6, "distance": -0.18, "angle": 3.0}
        try:
            core_coeffs.update({key: float(value) for key, value in json.loads(coeff_path.read_text()).items() if key in core_coeffs})
        except (OSError, ValueError):
            pass
        shared_engine = AnalyticsEngine(core_coeffs)
        shared_event_count = 0
        last_possession = "unknown"
        last_loss_ms: dict[str, int] = {}
        pending_counters: dict[str, dict[str, Any]] = {}
        previous_hist = None
        transformer = None
        transformer_confidence = 0.0
        last_keypoint_ms = -keypoint_interval_ms
        total_samples = 0
        player_samples = 0
        calibration_samples = 0
        frame_index = -1
        annotated_temp = match_dir / "annotated-temp.mp4"
        writer = cv2.VideoWriter(
            str(annotated_temp),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.analysis_hz,
            (1280, 720),
        )
        mapping = match.team_mapping
        usask_cluster = int(mapping["usask_cluster"])
        cluster_to_side = {
            usask_cluster: match.usask_side,
            1 - usask_cluster: "away" if match.usask_side == "home" else "home",
        }
        config = runtime["config"]

        try:
            while not cancelled():
                ok, frame = cap.read()
                if not ok:
                    break
                frame_index += 1
                if frame_index % sample_stride:
                    continue
                timestamp_ms = round(cap.get(cv2.CAP_PROP_POS_MSEC))
                if timestamp_ms <= 0:
                    timestamp_ms = round(frame_index / source_fps * 1000)
                if period_at(timestamp_ms, match.periods) is None:
                    continue
                total_samples += 1
                annotated = frame.copy()
                gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (160, 90))
                histogram = cv2.calcHist([gray], [0], None, [32], [0, 256])
                cv2.normalize(histogram, histogram, 1.0, 0.0, cv2.NORM_L1)
                camera_cut = previous_hist is not None and cv2.compareHist(previous_hist, histogram, cv2.HISTCMP_BHATTACHARYYA) > 0.62
                previous_hist = histogram
                if camera_cut:
                    tracker.reset()
                    transformer = None
                    transformer_confidence = 0.0
                    last_keypoint_ms = -keypoint_interval_ms

                result = runtime["player_model"].infer(frame, confidence=0.3)[0]
                detections = sv.Detections.from_inference(result)
                ball_detections = detections[detections.class_id == 0][:1]
                others = detections[detections.class_id != 0].with_nms(threshold=0.5, class_agnostic=True)
                players = others[others.class_id == 2][:20]
                goalkeepers = others[others.class_id == 1][:2]
                player_labels = classifier.predict([sv.crop_image(frame, box) for box in players.xyxy]) if len(players) else np.array([], dtype=int)
                players.class_id = player_labels
                if len(goalkeepers):
                    player_anchors = players.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                    goalkeeper_anchors = goalkeepers.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                    team_centres = {
                        team: player_anchors[player_labels == team].mean(axis=0)
                        for team in (0, 1)
                        if np.any(player_labels == team)
                    }
                    goalkeepers.class_id = np.array([
                        min(team_centres, key=lambda team: np.linalg.norm(anchor - team_centres[team]))
                        if team_centres else 0
                        for anchor in goalkeeper_anchors
                    ], dtype=int)
                tracked = sv.Detections.merge([players, goalkeepers])
                tracked = tracker.update_with_detections(tracked)

                reprojection_error_m = None
                visible_fraction = None
                if transformer is None or timestamp_ms - last_keypoint_ms >= keypoint_interval_ms:
                    field_result = runtime["field_model"].infer(frame, confidence=0.3)[0]
                    keypoints = sv.KeyPoints.from_inference(field_result)
                    if keypoints.xy is not None and len(keypoints.xy) and keypoints.confidence is not None:
                        mask = keypoints.confidence[0] > 0.5
                        frame_points = keypoints.xy[0][mask]
                        pitch_points = np.array(config.vertices)[mask]
                        if len(frame_points) >= 4:
                            transformer = runtime["ViewTransformer"](source=frame_points, target=pitch_points)
                            projected = transformer.transform_points(frame_points)
                            reprojection_error_m = float(np.mean(np.linalg.norm(projected - pitch_points, axis=1)) / 100)
                            visible_fraction = min(float(cv2.contourArea(cv2.convexHull(frame_points.astype(np.float32))) / (frame.shape[0] * frame.shape[1])), 1.0)
                            transformer_confidence = max(0.0, min(1.0 - reprojection_error_m / 4.0, 1.0))
                            last_keypoint_ms = timestamp_ms
                    elif transformer is not None:
                        transformer_confidence *= 0.9
                else:
                    transformer_confidence *= 0.99

                observations: list[dict[str, Any]] = []
                pitch_players: dict[str, list[tuple[float, float]]] = {"home": [], "away": []}
                core_players: list[PlayerObservation] = []
                ball_point: tuple[float, float] | None = None
                if transformer is not None:
                    anchors = tracked.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                    projected_players = transformer.transform_points(anchors) if len(anchors) else np.empty((0, 2))
                    for index, (detection, pitch) in enumerate(zip(tracked.xyxy, projected_players)):
                        cluster = int(tracked.class_id[index]) if int(tracked.class_id[index]) in (0, 1) else 0
                        side = cluster_to_side[cluster]
                        point = (float(pitch[0] / config.length * 105), float(pitch[1] / config.width * 68))
                        pitch_players[side].append(point)
                        confidence = float(tracked.confidence[index]) if tracked.confidence is not None else 0.0
                        core_players.append(PlayerObservation(
                            team="team0" if side == "home" else "team1",
                            point=point,
                            confidence=confidence,
                            track_id=int(tracked.tracker_id[index]) if tracked.tracker_id is not None else None,
                            role="outfield" if index < len(players) else "goalkeeper",
                        ))
                        observations.append({
                            "object_type": "player",
                            "track_id": int(tracked.tracker_id[index]) if tracked.tracker_id is not None else None,
                            "team": side,
                            "image_box": [float(value) for value in detection],
                            "pitch_x_m": point[0],
                            "pitch_y_m": point[1],
                            "detection_confidence": confidence,
                            "calibration_confidence": transformer_confidence,
                        })
                        x1, y1, x2, y2 = map(int, detection)
                        color = (65, 106, 11) if side == match.usask_side else (82, 204, 219)
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    if len(ball_detections):
                        anchor = ball_detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                        pitch = transformer.transform_points(anchor)[0]
                        ball_point = (float(pitch[0] / config.length * 105), float(pitch[1] / config.width * 68))
                        confidence = float(ball_detections.confidence[0]) if ball_detections.confidence is not None else 0.0
                        observations.append({
                            "object_type": "ball", "track_id": None, "team": None,
                            "image_box": [float(value) for value in ball_detections.xyxy[0]],
                            "pitch_x_m": ball_point[0], "pitch_y_m": ball_point[1],
                            "detection_confidence": confidence,
                            "calibration_confidence": transformer_confidence,
                        })
                        x1, y1, x2, y2 = map(int, ball_detections.xyxy[0])
                        cv2.circle(annotated, ((x1 + x2) // 2, (y1 + y2) // 2), 8, (255, 255, 255), 2)

                if pitch_players["home"] or pitch_players["away"]:
                    player_samples += 1
                if transformer is not None and transformer_confidence >= 0.5:
                    calibration_samples += 1
                state = possession.update(timestamp_ms, ball_point, pitch_players, transformer_confidence >= 0.5)
                series = [
                    {"metric": "possession", "value": {"team": state}, "confidence": transformer_confidence},
                    {
                        "metric": "match_clock",
                        "value": {
                            "elapsed_ms": match_clock_ms(timestamp_ms, match.periods),
                            "phase": match_phase(timestamp_ms, match.periods),
                            "period": period_at(timestamp_ms, match.periods),
                        },
                        "confidence": 1.0,
                    },
                ]
                events: list[dict[str, Any]] = []
                period = period_at(timestamp_ms, match.periods)
                usask_direction = match.directions.get(str(period), "right")
                directions = {
                    match.usask_side: usask_direction,
                    ("away" if match.usask_side == "home" else "home"): "left" if usask_direction == "right" else "right",
                }
                if state in ("home", "away") and last_possession in ("home", "away") and state != last_possession:
                    change = classify_possession_change(timestamp_ms, last_possession, state, ball_point, directions)
                    recovery_seconds = (timestamp_ms - last_loss_ms[state]) / 1000 if state in last_loss_ms else None
                    base = {"team": state, "period": period, "pitch_x_m": ball_point[0] if ball_point else None, "pitch_y_m": ball_point[1] if ball_point else None, "possession_context": state, "play_context": None, "confidence": transformer_confidence, "review_status": "pending", "details": {"previous_team": last_possession, "recovery_time_s": recovery_seconds}}
                    events.append({"type": "possession_win", **base})
                    events.append({"type": "possession_loss", **{**base, "team": last_possession, "details": {"new_team": state}}})
                    last_loss_ms[last_possession] = timestamp_ms
                    if ball_point:
                        pending_counters[state] = {"timestamp_ms": timestamp_ms, "initial_progress": normalize_longitudinal(ball_point[0], directions[state]), "created": False}
                    if change.high_turnover:
                        events.append({"type": "high_turnover", **base})
                    if change.dangerous_turnover:
                        events.append({"type": "dangerous_turnover", **base})
                if state in ("home", "away"):
                    last_possession = state
                    attacks = directions[state]
                    if ball_point:
                        pending = pending_counters.get(state)
                        if pending and timestamp_ms - pending["timestamp_ms"] <= 10_000 and not pending["created"]:
                            progress = normalize_longitudinal(ball_point[0], attacks)
                            if progress - pending["initial_progress"] >= 15 or progress >= 70:
                                events.append({"type": "counterattack", "team": state, "period": period, "pitch_x_m": ball_point[0], "pitch_y_m": ball_point[1], "possession_context": state, "play_context": "open_play", "confidence": transformer_confidence, "review_status": "pending", "details": {"regain_timestamp_ms": pending["timestamp_ms"]}})
                                pending["created"] = True
                        for entry in entry_detector.update(timestamp_ms, state, ball_point, attacks, True):
                            events.append({"type": f"{entry.kind}_entry", "team": state, "period": period, "pitch_x_m": entry.point[0], "pitch_y_m": entry.point[1], "possession_context": state, "play_context": None, "confidence": transformer_confidence, "review_status": "pending", "details": {"lane": entry.lane}})
                        shot, speed = shot_detectors[state].update(timestamp_ms, ball_point, attacks)
                        if shot:
                            regain = pending_counters.get(state)
                            shot_after_regain = bool(regain and timestamp_ms - regain["timestamp_ms"] <= 10_000)
                            events.append({"type": "shot", "team": state, "period": period, "pitch_x_m": ball_point[0], "pitch_y_m": ball_point[1], "possession_context": state, "play_context": None, "confidence": min(transformer_confidence, 0.8), "review_status": "pending", "details": {"xg": self._xg(ball_point, attacks), "speed_mps": speed, "on_target": None, "requires_review": True, "shot_after_regain": shot_after_regain}})
                        if normalize_longitudinal(ball_point[0], attacks) >= 70:
                            series.append({"metric": "attacking_third_control", "value": {"team": state}, "confidence": transformer_confidence})
                for side in ("home", "away"):
                    attacks = directions.get(side, "right")
                    values = shape_metrics(pitch_players[side], attacks, visible_fraction or 0.0, ball_point)
                    if values:
                        values.update({"team": side, "phase": "in_possession" if state == side else "out_of_possession"})
                        series.append({"metric": "shape", "value": values, "confidence": transformer_confidence})

                core_directions = {"team0": directions["home"], "team1": directions["away"]}
                shared_snapshot = shared_engine.update(
                    FrameObservation(
                        frame_id=frame_index,
                        timestamp_ms=timestamp_ms,
                        players=core_players,
                        ball=ball_point,
                        ball_confidence=(float(ball_detections.confidence[0]) if len(ball_detections) and ball_detections.confidence is not None else None),
                        calibration_confidence=transformer_confidence,
                        visible_pitch_fraction=visible_fraction or 0.0,
                        reprojection_error_m=reprojection_error_m,
                        match_clock_s=match_clock_ms(timestamp_ms, match.periods) / 1000,
                        period=period,
                        phase=match_phase(timestamp_ms, match.periods),
                    ),
                    core_directions,
                )
                new_shared_events = shared_engine.events[shared_event_count:]
                shared_event_count = len(shared_engine.events)
                for shared in new_shared_events:
                    if shared["type"] not in {"behind_line_entry", "pressure_attempt", "pressure_success", "pressure_escape", "forced_long_candidate"}:
                        continue
                    team_code = shared.get("team")
                    event_team = "home" if team_code == "team0" else "away" if team_code == "team1" else None
                    location = shared.get("location")
                    details = {
                        key: value for key, value in shared.items()
                        if key not in {"id", "type", "timestamp_ms", "team", "location", "status", "confidence", "period", "match_clock_s"}
                    }
                    if details.get("pressing_team") in ("team0", "team1"):
                        details["pressing_team"] = "home" if details["pressing_team"] == "team0" else "away"
                    events.append({
                        "type": shared["type"], "team": event_team, "period": period,
                        "pitch_x_m": location[0] if location else None,
                        "pitch_y_m": location[1] if location else None,
                        "possession_context": state, "play_context": "open_play",
                        "confidence": shared["confidence"], "review_status": "pending",
                        "details": details,
                    })
                series.append({"metric": "pressing", "value": shared_snapshot["pressing"], "confidence": transformer_confidence})

                confidence_values = [item["detection_confidence"] for item in observations]
                detection_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None
                emit(AnalysisBatch(
                    timestamp_ms=timestamp_ms,
                    observations=observations,
                    events=events,
                    time_series=series,
                    confidence={"reprojection_error_m": reprojection_error_m, "visible_pitch_fraction": visible_fraction, "detection_confidence": detection_confidence, "calibration_confidence": transformer_confidence if transformer else None, "camera_cut": camera_cut},
                    detection_coverage=player_samples / total_samples,
                    calibration_coverage=calibration_samples / total_samples,
                    log=f"Camera cut at {timestamp_ms / 1000:.1f}s; tracker reset" if camera_cut else None,
                ))
                annotated = cv2.resize(annotated, (1280, 720))
                cv2.putText(annotated, f"{timestamp_ms / 60000:05.2f}  possession: {state}", (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                writer.write(annotated)
        finally:
            cap.release()
            writer.release()

        if not cancelled() and annotated_temp.is_file():
            annotated = match_dir / "annotated.mp4"
            command = ["ffmpeg", "-y", "-i", str(annotated_temp), "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-movflags", "+faststart", str(annotated)]
            subprocess.run(command, check=True, capture_output=True)
            annotated_temp.unlink(missing_ok=True)
