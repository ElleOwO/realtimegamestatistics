import os

from dotenv import load_dotenv

load_dotenv()
import asyncio
import json
import threading
import time
from collections import deque
from typing import Optional

import cv2
import numpy as np
import supervision as sv
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from inference import get_model
from sports.annotators.soccer import (
    draw_pitch,
    draw_pitch_voronoi_diagram,
    draw_points_on_pitch,
)
from sports.common.team import TeamClassifier
from sports.common.view import ViewTransformer
from sports.configs.soccer import SoccerPitchConfiguration

API_KEY = os.environ.get("ROBOFLOW_API_KEY")
CONFIG = SoccerPitchConfiguration()

BALL_ID = 0
GOALKEEPER_ID = 1
PLAYER_ID = 2
REFEREE_ID = 3

MAX_BALLS = 1
MAX_GOALKEEPERS = 2
MAX_PLAYERS = 20
MAX_REFEREES = 3

CALIBRATION_FRAMES = 100
CALIBRATION_STRIDE = 3

MAXLEN = 5

PROCESS_EVERY = int(os.environ.get("PROCESS_EVERY", "3"))
INFER_SCALE = float(os.environ.get("INFER_SCALE", "0.5"))
CONFIDENCE = float(os.environ.get("CONFIDENCE", "0.3"))


PLAYER_DETECTION_MODEL = get_model(model_id="spen-rtgs-oc4ez/4", api_key=API_KEY)

FIELD_DETECTION_MODEL = get_model(
    model_id="football-field-detection-f07vi/14", api_key=API_KEY
)


def resolve_goalkeepers_team_id(
    players: sv.Detections, goalkeepers: sv.Detections
) -> np.ndarray:
    """Assign each goalkeeper to the nearest team based on centroid distance."""
    players_xy = players.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
    if (
        len(players_xy[players.class_id == 0]) == 0
        or len(players_xy[players.class_id == 1]) == 0
    ):
        return np.zeros(len(goalkeepers), dtype=int)

    team0 = players_xy[players.class_id == 0].mean(axis=0)
    team1 = players_xy[players.class_id == 1].mean(axis=0)

    team_ids = []
    for gk_xy in goalkeepers.get_anchors_coordinates(sv.Position.BOTTOM_CENTER):
        team_ids.append(
            0 if np.linalg.norm(gk_xy - team0) < np.linalg.norm(gk_xy - team1) else 1
        )
    return np.array(team_ids, dtype=int)


def draw_pitch_voronoi_diagram_2(
    config: SoccerPitchConfiguration,
    team_1_xy: np.ndarray,
    team_2_xy: np.ndarray,
    team_1_color: sv.Color = sv.Color.RED,
    team_2_color: sv.Color = sv.Color.WHITE,
    opacity: float = 0.5,
    padding: int = 50,
    scale: float = 0.1,
    pitch: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Draws a Voronoi diagram on a soccer pitch representing the control areas of two
    teams with smooth color transitions.
    """
    if pitch is None:
        pitch = draw_pitch(config=config, padding=padding, scale=scale)

    scaled_width = int(config.width * scale)
    scaled_length = int(config.length * scale)

    voronoi = np.zeros_like(pitch, dtype=np.uint8)

    team_1_color_bgr = np.array(team_1_color.as_bgr(), dtype=np.uint8)
    team_2_color_bgr = np.array(team_2_color.as_bgr(), dtype=np.uint8)

    y_coordinates, x_coordinates = np.indices(
        (scaled_width + 2 * padding, scaled_length + 2 * padding)
    )

    y_coordinates -= padding
    x_coordinates -= padding

    def calculate_distances(xy, x_coords, y_coords):
        return np.sqrt(
            (xy[:, 0][:, None, None] * scale - x_coords) ** 2
            + (xy[:, 1][:, None, None] * scale - y_coords) ** 2
        )

    distances_team_1 = calculate_distances(team_1_xy, x_coordinates, y_coordinates)
    distances_team_2 = calculate_distances(team_2_xy, x_coordinates, y_coordinates)

    min_distances_team_1 = np.min(distances_team_1, axis=0)
    min_distances_team_2 = np.min(distances_team_2, axis=0)

    steepness = 15
    distance_ratio = min_distances_team_2 / np.clip(
        min_distances_team_1 + min_distances_team_2, a_min=1e-5, a_max=None
    )
    blend_factor = np.tanh((distance_ratio - 0.5) * steepness) * 0.5 + 0.5

    for c in range(3):
        voronoi[:, :, c] = (
            blend_factor * team_1_color_bgr[c]
            + (1 - blend_factor) * team_2_color_bgr[c]
        ).astype(np.uint8)

    overlay = cv2.addWeighted(voronoi, opacity, pitch, 1 - opacity, 0)
    return overlay


def select_camera() -> int:
    """Scan available cameras and let the user pick one."""
    env_cam = os.environ.get("WEBCAM_INDEX")
    if env_cam is not None and env_cam != "":
        cam = int(env_cam)
        print(f"\nUsing WEBCAM_INDEX={cam} (non-interactive)")
        return cam

    available = []
    for i in range(10):
        test_cap = cv2.VideoCapture(i)
        if test_cap.isOpened():
            ret, frame = test_cap.read()
            if ret:
                h, w = frame.shape[:2]
                available.append((i, w, h))
            test_cap.release()

    if not available:
        raise RuntimeError("No cameras found")

    print("\nAvailable cameras:")
    for idx, (cam_id, w, h) in enumerate(available):
        print(f"  [{idx}] Camera {cam_id}  ({w}x{h})")

    choice = input("\nSelect camera number [0]: ").strip()
    choice = int(choice) if choice else 0
    return available[choice][0]


MIN_CROPS = 20


def calibrate_team_classifier(cap: cv2.VideoCapture) -> TeamClassifier:
    """
    Read a burst of frames from the webcam, collect player crops,
    and fit the SiGLIP-based TeamClassifier.
    """
    print(
        f"\nCalibrating team classifier "
        f"(up to {CALIBRATION_FRAMES} frames, need ≥{MIN_CROPS} crops)..."
    )

    crops = []
    frame_count = 0

    while frame_count < CALIBRATION_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % CALIBRATION_STRIDE != 0:
            continue

        result = PLAYER_DETECTION_MODEL.infer(frame, confidence=0.3)[0]
        detections = sv.Detections.from_inference(result)
        detections = detections.with_nms(threshold=0.5, class_agnostic=True)
        players = detections[detections.class_id == PLAYER_ID]
        player_crops = [sv.crop_image(frame, xyxy) for xyxy in players.xyxy]
        crops += player_crops

        preview = frame.copy()
        if len(players) > 0:
            sv.BoxAnnotator(color=sv.Color.from_hex("#00FF00")).annotate(
                scene=preview, detections=players
            )
        cv2.putText(
            preview,
            f"frame {frame_count}/{CALIBRATION_FRAMES}  "
            f"crops {len(crops)}/{MIN_CROPS}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        cv2.imshow("Calibration (press Q to finish early)", preview)

        if frame_count % 30 == 0:
            print(f"   … frame {frame_count}, {len(crops)} crops so far")

        if (cv2.waitKey(1) & 0xFF == ord("q")) or len(crops) >= MIN_CROPS * 2:
            print(f"Finishing calibration early ({len(crops)} crops)")
            break

    if len(crops) < MIN_CROPS:
        if len(crops) == 0:
            print("No player crops found. Using blank fallback crops.")
            crops = [np.zeros((64, 32, 3), dtype=np.uint8)] * MIN_CROPS
        else:
            print(f"Only {len(crops)} crops, duplicating to reach {MIN_CROPS}")
            while len(crops) < MIN_CROPS:
                crops.append(crops[len(crops) % len(crops)])

    device = "cpu"
    team_classifier = TeamClassifier(device=device)
    team_classifier.fit(crops)

    print(f"Team classifier fitted on {len(crops)} crops")
    return team_classifier


class ConnectionManager:
    """Manages active WebSocket connections with thread-safe broadcast."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = threading.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        with self._lock:
            self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        with self._lock:
            if ws in self.active_connections:
                self.active_connections.remove(ws)

    async def broadcast(self, message: str):
        with self._lock:
            connections = list(self.active_connections)
        disconnected = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


_latest_payload: str = ""
_new_data = threading.Event()
connection_manager = ConnectionManager()


def build_payload(
    frame_idx: int,
    match_start: float,
    tracker_ids: np.ndarray,
    team_ids: np.ndarray,
    pitch_player_xy: np.ndarray,
    pitch_ball_xy: np.ndarray,
) -> dict:
    """
    Assemble the JSON payload that matches the frontend AnalyticsPayload contract.

    Parameters
    ----------
    frame_idx : int
        Current frame number.
    match_start : float
        Epoch time when the analytics loop started.
    tracker_ids : np.ndarray
        ByteTrack IDs for players + goalkeepers (post-tracker, class_id < 2).
    team_ids : np.ndarray
        Team IDs (0 or 1) for the same detections.
    pitch_player_xy : np.ndarray
        Pitch-projected positions in centimeters, shape (N, 2).
    pitch_ball_xy : np.ndarray
        Ball pitch-projected position in centimeters, shape (1, 2) or empty.
    """
    players = []
    for i in range(len(tracker_ids)):
        x_m = float(pitch_player_xy[i, 0]) / 100.0 - 60.0
        y_m = float(pitch_player_xy[i, 1]) / 100.0 - 35.0
        players.append(
            {
                "id": int(tracker_ids[i]),
                "team": int(team_ids[i]),
                "x_m": round(x_m, 2),
                "y_m": round(y_m, 2),
            }
        )

    ball = None
    if len(pitch_ball_xy) > 0:
        bx = float(pitch_ball_xy[0, 0]) / 100.0 - 60.0
        by = float(pitch_ball_xy[0, 1]) / 100.0 - 35.0
        ball = [round(bx, 2), round(by, 2)]

    return {
        "frame_id": frame_idx,
        "timestamp": time.time(),
        "match_clock": round(time.time() - match_start, 2),
        "possession": {
            "team0_pct": 50,
            "team1_pct": 50,
            "team0_name": "Team 0",
            "team1_name": "Team 1",
        },
        "transition_speed_s": 0.0,
        "total_xg_team0": 0.0,
        "total_xg_team1": 0.0,
        "defensive_line_height_m": 0.0,
        "width_of_attack_m": 0.0,
        "convex_hull_area_m2": 0.0,
        "players": players,
        "ball": ball,
        "zone_stats": {"team0": {}, "team1": {}},
        "heatmaps": None,
    }


async def broadcast_loop():
    """Wait for new analytics data and broadcast to all connected WebSocket clients."""
    loop = asyncio.get_running_loop()
    while True:
        await loop.run_in_executor(None, _new_data.wait)
        _new_data.clear()
        if _latest_payload and connection_manager.active_connections:
            await connection_manager.broadcast(_latest_payload)


def main():
    cam_id = select_camera()
    cap = cv2.VideoCapture(cam_id)

    if not cap.isOpened():
        print("❌ Could not open webcam")
        return

    team_classifier = calibrate_team_classifier(cap)

    app = create_app()
    print("\n🚀 Server starting on http://0.0.0.0:8000  (WS: /ws, Health: /health)")
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000), daemon=True
    )
    server_thread.start()

    analytics_loop(cap, team_classifier)


def analytics_loop(cap: cv2.VideoCapture, team_classifier: TeamClassifier):
    """
    Main detection/tracking/projection loop. Runs on the main thread so OpenCV
    GUI operations (imshow, waitKey) work correctly. Publishes payloads to
    shared state for the asyncio broadcast task in the server thread.
    """
    global _latest_payload

    ellipse_annotator = sv.EllipseAnnotator(
        color=sv.ColorPalette.from_hex(["#00BFFF", "#FF1493", "#FFD700"]), thickness=2
    )
    label_annotator = sv.LabelAnnotator(
        color=sv.ColorPalette.from_hex(["#00BFFF", "#FF1493", "#FFD700"]),
        text_color=sv.Color.from_hex("#000000"),
        text_position=sv.Position.BOTTOM_CENTER,
    )
    triangle_annotator = sv.TriangleAnnotator(
        color=sv.Color.from_hex("#FFD700"), base=20, height=17
    )

    tracker = sv.ByteTrack()
    tracker.reset()

    M_buffer = deque(maxlen=MAXLEN)

    print(f"\nAnalytics loop started. Press Q in a CV window to stop.")
    print(
        f"   PROCESS_EVERY={PROCESS_EVERY}  INFER_SCALE={INFER_SCALE}  "
        f"CONFIDENCE={CONFIDENCE}\n"
    )

    match_start = time.time()
    frame_idx = 0
    cached_annotated = None
    cached_pitch = None
    cached_voronoi = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        if (
            PROCESS_EVERY > 1
            and frame_idx % PROCESS_EVERY != 1
            and cached_annotated is not None
        ):
            cv2.imshow("Camera View", cached_annotated)
            if cached_pitch is not None:
                cv2.imshow("Pitch Radar", cached_pitch)
            if cached_voronoi is not None:
                cv2.imshow("Voronoi", cached_voronoi)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        if INFER_SCALE != 1.0:
            infer_frame = cv2.resize(frame, (0, 0), fx=INFER_SCALE, fy=INFER_SCALE)
        else:
            infer_frame = frame

        result = PLAYER_DETECTION_MODEL.infer(infer_frame, confidence=CONFIDENCE)[0]
        detections = sv.Detections.from_inference(result)
        if INFER_SCALE != 1.0:
            detections.xyxy = detections.xyxy / INFER_SCALE

        ball_detections = detections[detections.class_id == BALL_ID]
        if len(ball_detections) > MAX_BALLS:
            ball_detections = ball_detections[:MAX_BALLS]
        ball_detections.xyxy = sv.pad_boxes(ball_detections.xyxy, px=10)

        all_detections = detections[detections.class_id != BALL_ID]
        all_detections = all_detections.with_nms(threshold=0.5, class_agnostic=True)

        goalkeepers_detections = all_detections[
            all_detections.class_id == GOALKEEPER_ID
        ][:MAX_GOALKEEPERS]
        players_detections = all_detections[all_detections.class_id == PLAYER_ID][
            :MAX_PLAYERS
        ]
        referees_detections = all_detections[all_detections.class_id == REFEREE_ID][
            :MAX_REFEREES
        ]

        if len(players_detections) > 0:
            player_crops = [
                sv.crop_image(frame, xyxy) for xyxy in players_detections.xyxy
            ]
            players_detections.class_id = team_classifier.predict(player_crops)

        goalkeepers_detections.class_id = resolve_goalkeepers_team_id(
            players_detections, goalkeepers_detections
        )

        referees_detections.class_id -= 1

        merged_detections = sv.Detections.merge(
            [players_detections, goalkeepers_detections, referees_detections]
        )
        merged_detections = tracker.update_with_detections(detections=merged_detections)
        merged_detections.class_id = merged_detections.class_id.astype(int)

        labels = [f"#{tracker_id}" for tracker_id in merged_detections.tracker_id]

        annotated_frame = frame.copy()
        annotated_frame = ellipse_annotator.annotate(
            scene=annotated_frame, detections=merged_detections
        )
        annotated_frame = label_annotator.annotate(
            scene=annotated_frame, detections=merged_detections, labels=labels
        )
        annotated_frame = triangle_annotator.annotate(
            scene=annotated_frame, detections=ball_detections
        )

        result_field = FIELD_DETECTION_MODEL.infer(infer_frame, confidence=CONFIDENCE)[
            0
        ]
        keypoints = sv.KeyPoints.from_inference(result_field)

        if (
            keypoints.xy is None
            or len(keypoints.xy) == 0
            or keypoints.confidence is None
        ):
            cached_annotated = annotated_frame
            cv2.imshow("Camera View", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        filter_mask = keypoints.confidence[0] > 0.5
        frame_reference_points = keypoints.xy[0][filter_mask] / INFER_SCALE
        pitch_reference_points = np.array(CONFIG.vertices)[filter_mask]

        if len(frame_reference_points) < 4:
            cached_annotated = annotated_frame
            cv2.imshow("Camera View", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        transformer = ViewTransformer(
            source=frame_reference_points, target=pitch_reference_points
        )

        M_buffer.append(transformer.m)
        transformer.m = np.mean(np.array(M_buffer), axis=0)

        pitch_detections = sv.Detections.merge(
            [players_detections, goalkeepers_detections]
        )

        if len(pitch_detections) == 0 and len(ball_detections) == 0:
            cached_annotated = annotated_frame
            cv2.imshow("Camera View", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        frame_ball_xy = ball_detections.get_anchors_coordinates(
            sv.Position.BOTTOM_CENTER
        )
        pitch_ball_xy = (
            transformer.transform_points(points=frame_ball_xy)
            if len(frame_ball_xy) > 0
            else np.array([])
        )

        players_xy = pitch_detections.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
        pitch_players_xy = (
            transformer.transform_points(points=players_xy)
            if len(players_xy) > 0
            else np.array([])
        )

        referees_xy = referees_detections.get_anchors_coordinates(
            sv.Position.BOTTOM_CENTER
        )
        pitch_referees_xy = (
            transformer.transform_points(points=referees_xy)
            if len(referees_xy) > 0
            else np.array([])
        )

        payload_mask = merged_detections.class_id < 2
        if payload_mask.any():
            payload_dets = merged_detections[payload_mask]
            payload_tracker_ids = payload_dets.tracker_id
            payload_team_ids = payload_dets.class_id
            payload_frame_xy = payload_dets.get_anchors_coordinates(
                sv.Position.BOTTOM_CENTER
            )
            payload_pitch_xy = transformer.transform_points(points=payload_frame_xy)
        else:
            payload_tracker_ids = np.array([], dtype=int)
            payload_team_ids = np.array([], dtype=int)
            payload_pitch_xy = np.empty((0, 2))

        payload = build_payload(
            frame_idx=frame_idx,
            match_start=match_start,
            tracker_ids=payload_tracker_ids,
            team_ids=payload_team_ids,
            pitch_player_xy=payload_pitch_xy,
            pitch_ball_xy=pitch_ball_xy,
        )
        _latest_payload = json.dumps(payload)
        _new_data.set()

        pitch_img = draw_pitch(CONFIG)

        if len(pitch_ball_xy) > 0:
            pitch_img = draw_points_on_pitch(
                config=CONFIG,
                xy=pitch_ball_xy,
                face_color=sv.Color.WHITE,
                edge_color=sv.Color.BLACK,
                radius=10,
                pitch=pitch_img,
            )

        if len(pitch_players_xy) > 0 and len(pitch_detections) > 0:
            team0_mask = pitch_detections.class_id == 0
            if team0_mask.any():
                pitch_img = draw_points_on_pitch(
                    config=CONFIG,
                    xy=pitch_players_xy[team0_mask],
                    face_color=sv.Color.from_hex("00BFFF"),
                    edge_color=sv.Color.BLACK,
                    radius=16,
                    pitch=pitch_img,
                )

        if len(pitch_players_xy) > 0 and len(pitch_detections) > 0:
            team1_mask = pitch_detections.class_id == 1
            if team1_mask.any():
                pitch_img = draw_points_on_pitch(
                    config=CONFIG,
                    xy=pitch_players_xy[team1_mask],
                    face_color=sv.Color.from_hex("FF1493"),
                    edge_color=sv.Color.BLACK,
                    radius=16,
                    pitch=pitch_img,
                )

        if len(pitch_referees_xy) > 0:
            pitch_img = draw_points_on_pitch(
                config=CONFIG,
                xy=pitch_referees_xy,
                face_color=sv.Color.from_hex("FFD700"),
                edge_color=sv.Color.BLACK,
                radius=16,
                pitch=pitch_img,
            )

        voronoi_img = None
        if len(pitch_players_xy) > 0 and len(pitch_detections) > 0:
            team0_mask = pitch_detections.class_id == 0
            team1_mask = pitch_detections.class_id == 1
            if team0_mask.any() and team1_mask.any():
                voronoi_img = draw_pitch(
                    config=CONFIG,
                    background_color=sv.Color.WHITE,
                    line_color=sv.Color.BLACK,
                )
                voronoi_img = draw_pitch_voronoi_diagram_2(
                    config=CONFIG,
                    team_1_xy=pitch_players_xy[team0_mask],
                    team_2_xy=pitch_players_xy[team1_mask],
                    team_1_color=sv.Color.from_hex("00BFFF"),
                    team_2_color=sv.Color.from_hex("FF1493"),
                    pitch=voronoi_img,
                )
                if len(pitch_ball_xy) > 0:
                    voronoi_img = draw_points_on_pitch(
                        config=CONFIG,
                        xy=pitch_ball_xy,
                        face_color=sv.Color.WHITE,
                        edge_color=sv.Color.WHITE,
                        radius=8,
                        thickness=1,
                        pitch=voronoi_img,
                    )
                voronoi_img = draw_points_on_pitch(
                    config=CONFIG,
                    xy=pitch_players_xy[team0_mask],
                    face_color=sv.Color.from_hex("00BFFF"),
                    edge_color=sv.Color.WHITE,
                    radius=16,
                    thickness=1,
                    pitch=voronoi_img,
                )
                voronoi_img = draw_points_on_pitch(
                    config=CONFIG,
                    xy=pitch_players_xy[team1_mask],
                    face_color=sv.Color.from_hex("FF1493"),
                    edge_color=sv.Color.WHITE,
                    radius=16,
                    thickness=1,
                    pitch=voronoi_img,
                )

                cv2.imshow("Voronoi", voronoi_img)

        cached_annotated = annotated_frame
        cached_pitch = pitch_img
        cached_voronoi = voronoi_img
        cv2.imshow("Camera View", annotated_frame)
        cv2.imshow("Pitch Radar", pitch_img)
        if voronoi_img is not None:
            cv2.imshow("Voronoi", voronoi_img)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def create_app() -> FastAPI:
    """Create the FastAPI app with health check and WebSocket endpoints."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await connection_manager.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            connection_manager.disconnect(ws)

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(broadcast_loop())

    return app


if __name__ == "__main__":
    main()

