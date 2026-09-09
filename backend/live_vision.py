"""Broadcast vision adapter; metric definitions stay in analytics_core."""
from __future__ import annotations

from collections import deque

import numpy as np

from analytics_core import FrameObservation, PlayerObservation
from pitch_calibration import field_keypoint_correspondences
from team_tracking import TrackTeamAssigner


class BroadcastVision:
    def __init__(self, api_key: str, *, keypoint_interval=15):
        import cv2
        import supervision as sv
        import torch
        from inference import get_model
        from sports.common.team import TeamClassifier
        from sports.configs.soccer import SoccerPitchConfiguration

        if not torch.cuda.is_available():
            raise RuntimeError("A CUDA GPU is required for live broadcast analysis.")
        self.cv2, self.sv = cv2, sv
        self.player_model = get_model(model_id="spen-rtgs-oc4ez/4", api_key=api_key)
        self.field_model = get_model(model_id="football-field-detection-f07vi/14", api_key=api_key)
        # ONNX models expose their provider list through the inference session.
        for model in (self.player_model, self.field_model):
            session = getattr(model, "onnx_session", None)
            if session is not None and hasattr(session, "get_providers") and not any(
                p in session.get_providers() for p in ("CUDAExecutionProvider", "TensorrtExecutionProvider")
            ):
                raise RuntimeError("A detection model is using CPU inference; check the CUDA image.")
        self.classifier = TeamClassifier(device="cuda")
        self.config = SoccerPitchConfiguration()
        self.tracker = sv.ByteTrack(frame_rate=10)
        self.teams = TrackTeamAssigner()
        self.crops, self.calibrated = [], False
        self.frame_id, self.keypoint_interval = 0, max(1, keypoint_interval)
        self.reset()

    def reset(self):
        self.tracker.reset()
        self.teams.reset()
        self.matrices = deque(maxlen=5)
        self.matrix = self.previous_gray = None
        self.confidence, self.visible = 0.0, 0.0
        self.error = None

    def process(self, image, timestamp_ms, discontinuity=False):
        cv2, sv = self.cv2, self.sv
        if discontinuity:
            self.reset()
        self.frame_id += 1
        observation = FrameObservation(self.frame_id, timestamp_ms, [], None, None, 0, 0)
        gray = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (160, 90))
        motion = float(np.mean(cv2.absdiff(gray, self.previous_gray))) if self.previous_gray is not None else 255
        self.scene_changed = motion > 35
        if self.scene_changed:
            self.reset()
        self.previous_gray = gray
        detections = sv.Detections.from_inference(self.player_model.infer(image, confidence=0.3)[0])
        players = detections[detections.class_id == 2]
        if not self.calibrated:
            self.crops.extend(sv.crop_image(image, box) for box in players.xyxy)
            self.crops = self.crops[:100]
            if len(self.crops) >= 40 or self.frame_id >= 30 and len(self.crops) >= 20:
                self.classifier.fit(self.crops)
                self.crops.clear()
                self.calibrated = True
            else:
                return observation, image, False
        tracked = self.tracker.update_with_detections(detections[detections.class_id != 0])
        players = tracked[tracked.class_id == 2]
        indices = [i for i, tid in enumerate(players.tracker_id) if self.teams.needs_prediction(int(tid))]
        if indices:
            predictions = self.classifier.predict([sv.crop_image(image, players.xyxy[i]) for i in indices])
            for i, team in zip(indices, predictions):
                self.teams.observe(int(players.tracker_id[i]), int(team))
        assigned = [(int(tid), self.teams.team_for(int(tid)), box, float(conf))
                    for tid, box, conf in zip(players.tracker_id, players.xyxy, players.confidence)]
        preview = image.copy()
        for tid, team, box, _ in assigned:
            x1, y1, x2, y2 = map(int, box)
            color = (255, 191, 0) if team == 0 else (147, 20, 255)
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
            cv2.putText(preview, f"{team} #{tid}", (x1, max(18, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 2)
        if self.matrix is None or motion > 8 or self.frame_id % self.keypoint_interval == 0:
            result = self.field_model.infer(image, confidence=.3)[0]
            source, target, confidence = field_keypoint_correspondences(result, self.config.vertices)
            target = target * np.array([105 / self.config.length, 68 / self.config.width])
            matrix, inliers = cv2.findHomography(source, target, cv2.RANSAC, 2.0) if len(source) >= 4 else (None, None)
            if matrix is not None and np.isfinite(matrix).all() and abs(matrix[2, 2]) > 1e-9:
                if motion > 8:
                    self.matrices.clear()
                self.matrices.append(matrix / matrix[2, 2])
                self.matrix = np.mean(self.matrices, axis=0)
                projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), self.matrix).reshape(-1, 2)
                self.error = float(np.mean(np.linalg.norm(projected - target, axis=1)))
                self.confidence = float(np.mean(confidence) * np.mean(inliers) * np.exp(-self.error / 2))
                h, w = image.shape[:2]
                corners = np.array([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]], dtype=np.float32)
                hull = cv2.convexHull(cv2.perspectiveTransform(corners, self.matrix))
                pitch = np.array([[0, 0], [105, 0], [105, 68], [0, 68]], dtype=np.float32)
                area, _ = cv2.intersectConvexConvex(hull, pitch)
                self.visible = min(1.0, max(0.0, float(area) / (105 * 68)))
            elif motion > 8:
                self.matrix, self.confidence = None, 0.0
            else:
                self.confidence *= .7
        if self.matrix is None:
            return observation, preview, True
        observation.calibration_confidence = self.confidence
        observation.visible_pitch_fraction = self.visible
        observation.reprojection_error_m = self.error
        def project(box):
            x1, _, x2, y2 = box
            xy = cv2.perspectiveTransform(np.array([[[float((x1 + x2) / 2), float(y2)]]], np.float32), self.matrix)[0, 0]
            return (float(xy[0]), float(xy[1])) if np.isfinite(xy).all() and -5 <= xy[0] <= 110 and -5 <= xy[1] <= 73 else None
        for tid, team, box, confidence in assigned:
            point = project(box)
            if point:
                observation.players.append(PlayerObservation(f"team{team}", point, confidence, tid))
        balls = detections[detections.class_id == 0]
        if len(balls):
            best = int(np.argmax(balls.confidence))
            observation.ball = project(balls.xyxy[best])
            observation.ball_confidence = float(balls.confidence[best])
        return observation, preview, True
