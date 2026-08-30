import os

from dotenv import load_dotenv

load_dotenv()
import argparse
import asyncio
import json
import math
import threading
import time
import zipfile
from collections import deque, defaultdict
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlsplit, urlunsplit

# Allow unsupported MPS ops to fall back to CPU instead of erroring
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import cv2
import numpy as np
import supervision as sv
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from inference import get_model
from sports.annotators.soccer import (
    draw_pitch,
    draw_pitch_voronoi_diagram,
    draw_points_on_pitch,
)
from sports.common.team import TeamClassifier
from sports.common.view import ViewTransformer
from sports.configs.soccer import SoccerPitchConfiguration

from analytics_core import (
    AnalyticsEngine,
    FrameObservation,
    PlayerObservation,
    PITCH_LENGTH_M,
    PITCH_WIDTH_M,
)
from live_state import LiveMatchController
from live_payload import build_payload_v2
from observation_io import ObservationRecorder, RecordingHeader
from event_clips import EncodedClipBuffer, configured_clip_buffer
from pitch_calibration import field_keypoint_correspondences

API_KEY = os.environ.get("ROBOFLOW_API_KEY")
CONFIG = SoccerPitchConfiguration()
DISPLAY_WINDOWS = os.environ.get("HEADLESS", "").lower() not in {"1", "true", "yes"}

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

# ── Expected Goals (xG) ─────────────────────────────────────────────────
GOAL_WIDTH = 7.32              # meters, standard goal mouth
BALL_HISTORY_LEN = 10          # frames of ball positions kept for velocity
SHOT_SPEED_THRESHOLD = 4.0     # meters/frame; minimum ball speed for a shot
SHOT_MAX_DISTANCE = 35.0       # meters; shots only count this close to a goal
SHOT_COOLDOWN_FRAMES = 20      # frames before another shot can register
XG_DISPLAY_DURATION = 90       # frames to keep a shot marker on the radar

# ── Zone-entry tracking ─────────────────────────────────────────────────
# Each half (along pitch length) is split into 4 equal width-wise lanes.
NUM_LANES = 4
LANE_HEIGHT = CONFIG.goal_box_width
LANE_OFFSET = (CONFIG.width - NUM_LANES * LANE_HEIGHT) / 2.0
TEAM0_ATTACKS_RIGHT = True     # Team 0 attacks the goal at x = config.length

# ── Coach reporting ─────────────────────────────────────────────────────
INTERVAL_MINUTES = 15

# ── xG logistic-model coefficients ──────────────────────────────────────
# log_odds = intercept + distance*distance_coef + angle*angle_coef
# (linear in distance and angle; the coefficient names are "distance"/"angle")
# Defaults; train_xg.py can overwrite via xg_coeffs.json.
XG_COEFFS = {"intercept": 0.6, "distance": -0.18, "angle": 3.0}

_XG_COEFFS_PATH = os.path.join(os.path.dirname(__file__), "xg_coeffs.json")
if os.path.exists(_XG_COEFFS_PATH):
    try:
        with open(_XG_COEFFS_PATH) as _f:
            _loaded = json.load(_f)
        _meta = _loaded.get("_meta", {})
        if _meta and (
            float(_meta.get("pitch_length_m", 105.0)) != 105.0
            or float(_meta.get("pitch_width_m", 68.0)) != 68.0
        ):
            raise ValueError("xG coefficients were trained for a different pitch size")
        XG_COEFFS.update({k: float(_loaded[k]) for k in XG_COEFFS if k in _loaded})
        print(f"✅ Loaded trained xG coefficients from {_XG_COEFFS_PATH}")
    except (ValueError, KeyError, OSError) as _e:
        print(f"⚠️  Could not load xg_coeffs.json ({_e}); using defaults")


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


def get_device() -> str:
    """Pick the best available torch device: Apple MPS, CUDA, else CPU."""
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def calculate_xg(shot_x: float, shot_y: float, goal_x: float,
                 config: SoccerPitchConfiguration) -> float:
    """
    Estimate Expected Goals (xG) from a shot location using a simple
    distance + angle logistic model. Coordinates are in pitch space (cm).

    shot_x, shot_y: shot location on the pitch
    goal_x: x-coordinate of the goal being attacked (0 or config.length)
    """
    # Work in meters (sports pitch config is in centimeters)
    sx, sy = shot_x / 100.0, shot_y / 100.0
    gx = goal_x / 100.0
    gy = (config.width / 100.0) / 2.0

    # Distance from shot to goal center
    distance = math.hypot(gx - sx, gy - sy)

    # Angle of the visible goal mouth from the shot location
    post1 = (gx, gy - GOAL_WIDTH / 2.0)
    post2 = (gx, gy + GOAL_WIDTH / 2.0)
    a1 = math.atan2(post1[1] - sy, post1[0] - sx)
    a2 = math.atan2(post2[1] - sy, post2[0] - sx)
    angle = abs(a2 - a1)

    # Logistic model. Coefficients come from XG_COEFFS, which may be the
    # rough defaults or values trained on real data via train_xg.py.
    log_odds = (
        XG_COEFFS["intercept"]
        + XG_COEFFS["distance"] * distance
        + XG_COEFFS["angle"] * angle
    )
    xg = 1.0 / (1.0 + math.exp(-log_odds))
    return float(min(max(xg, 0.01), 0.99))


def detect_shot(ball_history: deque, config: SoccerPitchConfiguration):
    """
    Detect a shot from recent pitch-space ball positions.

    A movement is treated as a shot only when it is (a) fast enough,
    (b) heading consistently toward one goal across the window, and
    (c) close enough to that goal. This rejects ordinary passes and
    clearances that merely happen to be quick.

    Returns (is_shot, velocity_x). velocity_x sign indicates direction:
    positive => moving toward the goal at x = config.length,
    negative => moving toward the goal at x = 0.
    """
    if len(ball_history) < 4:
        return False, 0.0

    recent = list(ball_history)[-4:]

    # Net displacement over the window (meters)
    vx = (recent[-1][0] - recent[0][0]) / 100.0
    vy = (recent[-1][1] - recent[0][1]) / 100.0
    speed = math.hypot(vx, vy)
    if speed <= SHOT_SPEED_THRESHOLD:
        return False, vx

    # Per-step x deltas must share a sign => sustained, not a bounce
    step_dx = [recent[i + 1][0] - recent[i][0] for i in range(len(recent) - 1)]
    consistent = all(d > 0 for d in step_dx) or all(d < 0 for d in step_dx)
    if not consistent:
        return False, vx

    # Ball must be near the goal it is heading toward
    goal_x = config.length if vx >= 0 else 0.0
    dist_to_goal = abs(goal_x - recent[-1][0]) / 100.0
    if dist_to_goal > SHOT_MAX_DISTANCE:
        return False, vx

    return True, vx


def nearest_team(point_xy: np.ndarray, pitch_detections: sv.Detections) -> int:
    """Return the team id (0 or 1) of the closest player to a pitch point."""
    if len(pitch_detections) == 0:
        return 0
    players_xy = pitch_detections.get_anchors_coordinates(
        sv.Position.BOTTOM_CENTER)
    dists = np.linalg.norm(players_xy - point_xy, axis=1)
    closest = int(np.argmin(dists))
    team = int(pitch_detections.class_id[closest])
    return team if team in (0, 1) else 0


def ball_zone(bx: float, by: float, config: SoccerPitchConfiguration):
    """
    Map a pitch-space ball position to a zone (half, lane).

    half: 'R' if the ball is in the x >= length/2 half, else 'L'.
    lane: 0..NUM_LANES-1 across the width (y), 0 = lowest y.
    """
    half = 'R' if bx >= config.length / 2.0 else 'L'
    lane = int((by - LANE_OFFSET) / LANE_HEIGHT)
    lane = min(max(lane, 0), NUM_LANES - 1)
    return half, lane


def zone_kind(team: int, half: str) -> str:
    """Return 'OFF' or 'DEF' for a team given an absolute half ('L'/'R')."""
    attacks_right = TEAM0_ATTACKS_RIGHT if team == 0 else not TEAM0_ATTACKS_RIGHT
    off_half = 'R' if attacks_right else 'L'
    return 'OFF' if half == off_half else 'DEF'


def team_halves(team: int):
    """Return (offensive_half, defensive_half) as 'L'/'R' for a team."""
    attacks_right = TEAM0_ATTACKS_RIGHT if team == 0 else not TEAM0_ATTACKS_RIGHT
    off_half = 'R' if attacks_right else 'L'
    def_half = 'L' if off_half == 'R' else 'R'
    return off_half, def_half


def total_entries(zone_entries: dict, team: int) -> int:
    """Total ball entries across all zones for a team."""
    return int(sum(zone_entries[team].values()))


def format_clock(seconds: float) -> str:
    """Format a number of seconds as MM:SS."""
    return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"


def print_interval_report(interval_idx: int, clock_str: str,
                          team_xg: dict, zone_entries: dict,
                          prev: dict) -> None:
    """Print a per-interval coach update (cumulative totals + deltas)."""
    print(f"\n===== Coach update @ {clock_str} "
          f"(interval {interval_idx}, last {INTERVAL_MINUTES} min) =====")
    for team in (0, 1):
        tot = total_entries(zone_entries, team)
        d_xg = team_xg[team] - prev['xg'][team]
        d_ent = tot - prev['entries'][team]
        print(f"  Team {team + 1}: xG {team_xg[team]:.2f} (+{d_xg:.2f})  |  "
              f"entries {tot} (+{d_ent})")
        prev['xg'][team] = team_xg[team]
        prev['entries'][team] = tot


def draw_zone_overlay(pitch_img: np.ndarray, zone_entries: dict,
                      config: SoccerPitchConfiguration,
                      scale: float = 0.1, padding: int = 50) -> np.ndarray:
    """Draw width-wise lane lines and per-zone entry counts on the radar."""
    x0 = padding
    x1 = int(config.length * scale) + padding

    # Lane dividing lines (horizontal, constant y), clamped to the pitch
    for k in range(1, NUM_LANES):
        y_coord = min(max(LANE_OFFSET + LANE_HEIGHT * k, 0), config.width)
        y = int(y_coord * scale) + padding
        cv2.line(pitch_img, (x0, y), (x1, y), (200, 200, 200), 1, cv2.LINE_AA)

    # Per-zone counts: Team 1 (cyan) left number, Team 2 (pink) right number
    for half in ('L', 'R'):
        cx_coord = config.length * (0.25 if half == 'L' else 0.75)
        cx = int(cx_coord * scale) + padding
        for lane in range(NUM_LANES):
            band_top = max(LANE_OFFSET + lane * LANE_HEIGHT, 0)
            band_bottom = min(LANE_OFFSET + (lane + 1) * LANE_HEIGHT, config.width)
            cy_coord = (band_top + band_bottom) / 2.0
            cy = int(cy_coord * scale) + padding
            t0 = zone_entries[0][(half, lane)]
            t1 = zone_entries[1][(half, lane)]
            cv2.putText(pitch_img, str(t0), (cx - 22, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 191, 0), 2, cv2.LINE_AA)
            cv2.putText(pitch_img, str(t1), (cx + 6, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (147, 20, 255), 2, cv2.LINE_AA)
    return pitch_img


def draw_dashboard(team_xg: dict, zone_entries: dict,
                   match_time: str = "") -> np.ndarray:
    """
    Render a coach-facing dashboard with the two new metrics:
    cumulative Expected Goals (xG) and ball entries by zone.
    """
    W, H = 560, 640
    dash = np.full((H, W, 3), 28, dtype=np.uint8)

    cyan = (255, 191, 0)     # Team 1 (BGR)
    pink = (147, 20, 255)    # Team 2 (BGR)
    white = (255, 255, 255)
    gray = (165, 165, 165)
    font = cv2.FONT_HERSHEY_SIMPLEX

    def text(s, org, scale, color, thick=1):
        cv2.putText(dash, s, org, font, scale, color, thick, cv2.LINE_AA)

    # Title
    text("COACH DASHBOARD", (20, 42), 0.9, white, 2)
    if match_time:
        text(match_time, (W - 120, 42), 0.8, (0, 255, 255), 2)
    cv2.line(dash, (20, 58), (W - 20, 58), gray, 1)

    # Team column headers
    text("TEAM 1", (165, 96), 0.75, cyan, 2)
    text("TEAM 2", (390, 96), 0.75, pink, 2)

    # --- Expected Goals ---
    text("EXPECTED GOALS (xG)", (20, 140), 0.6, gray, 1)
    text(f"{team_xg[0]:.2f}", (165, 195), 1.3, cyan, 3)
    text(f"{team_xg[1]:.2f}", (390, 195), 1.3, pink, 3)
    cv2.line(dash, (20, 225), (W - 20, 225), (60, 60, 60), 1)

    # --- Ball entries by zone ---
    text("BALL ENTRIES BY ZONE", (20, 262), 0.6, gray, 1)
    text("DEF  OFF", (140, 296), 0.5, gray, 1)
    text("DEF  OFF", (370, 296), 0.5, gray, 1)

    col = {0: (150, 218), 1: (380, 448)}  # (DEF x, OFF x) per team
    row_y0, row_dy = 330, 40
    totals = {0: 0, 1: 0}
    for lane in range(NUM_LANES):
        y = row_y0 + lane * row_dy
        text(f"Lane {lane + 1}", (20, y), 0.55, white, 1)
        for team, color in ((0, cyan), (1, pink)):
            off_h, def_h = team_halves(team)
            d = zone_entries[team][(def_h, lane)]
            o = zone_entries[team][(off_h, lane)]
            totals[team] += d + o
            dx, ox = col[team]
            text(str(d), (dx, y), 0.6, color, 2)
            text(str(o), (ox, y), 0.6, color, 2)

    # Totals
    ty = row_y0 + NUM_LANES * row_dy + 10
    cv2.line(dash, (20, ty - 28), (W - 20, ty - 28), (60, 60, 60), 1)
    text("TOTAL", (20, ty), 0.6, white, 2)
    text(str(totals[0]), (150, ty), 0.6, cyan, 2)
    text(str(totals[1]), (380, ty), 0.6, pink, 2)

    return dash


def resolve_video_source(source: str) -> str:
    """
    Resolve a video source to something OpenCV can open.

    - Local file paths are returned unchanged.
    - http(s) URLs (including YouTube) are resolved to a direct stream URL
      using yt-dlp, preferring a progressive MP4 ≤720p for stable decoding.
    """
    if not source.lower().startswith(("http://", "https://")):
        return source

    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError(
            "yt-dlp is required for URL/YouTube input. "
            "Install it with: pip install yt-dlp")

    print(f"🔗 Resolving stream URL via yt-dlp: {source}")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        # Prefer a single progressive MP4 stream <=720p (no separate audio)
        "format": "best[ext=mp4][height<=720]/best[height<=720]/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(source, download=False)
        # For playlists, take the first entry
        if "entries" in info:
            info = info["entries"][0]
        stream_url = info.get("url")

    if not stream_url:
        raise RuntimeError(f"Could not resolve a stream URL for: {source}")

    print("✅ Stream URL resolved")
    return stream_url


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


def show_window(name: str, image: np.ndarray) -> None:
    """Display a diagnostic frame unless the runtime is headless."""
    if DISPLAY_WINDOWS:
        cv2.imshow(name, image)


def quit_requested() -> bool:
    """Handle the OpenCV Q shortcut when diagnostic windows are enabled."""
    return DISPLAY_WINDOWS and (cv2.waitKey(1) & 0xFF == ord("q"))


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
        show_window("Calibration (press Q to finish early)", preview)

        if frame_count % 30 == 0:
            print(f"   … frame {frame_count}, {len(crops)} crops so far")

        if quit_requested() or len(crops) >= MIN_CROPS * 2:
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

    device = get_device()
    print(f"🖥️  Team classifier device: {device}")
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
match_controller = LiveMatchController()
analytics_engine = AnalyticsEngine(XG_COEFFS)
analytics_lock = threading.RLock()
_runtime_lock = threading.RLock()
_runtime_state: dict = {
    "run_id": os.environ.get("RTGS_RUN_ID", f"live-{int(time.time())}"),
    "mode": "live",
    "source_state": "waiting",
    "inference_fps": 0.0,
    "payload_fps": 0.0,
    "processing_latency_ms": None,
    "last_frame_at": None,
    "reconnect_count": 0,
    "frame_times": deque(maxlen=120),
}
_observation_recorder: ObservationRecorder | None = None


def update_runtime(**values):
    with _runtime_lock:
        _runtime_state.update(values)


def runtime_snapshot() -> dict:
    with _runtime_lock:
        now = time.monotonic()
        recent = [sample for sample in _runtime_state["frame_times"] if now - sample <= 2]
        last_frame_at = _runtime_state.get("last_frame_at")
        return {
            "run_id": _runtime_state["run_id"],
            "mode": "live",
            "source_state": _runtime_state["source_state"],
            "inference_fps": round(len(recent) / 2, 2),
            "payload_fps": round(len(recent) / 2, 2),
            "processing_latency_ms": _runtime_state.get("processing_latency_ms"),
            "last_frame_age_ms": round((now - last_frame_at) * 1000) if last_frame_at else None,
            "reconnect_count": _runtime_state["reconnect_count"],
        }


async def broadcast_loop():
    """Wait for new analytics data and broadcast to all connected WebSocket clients."""
    loop = asyncio.get_running_loop()
    while True:
        await loop.run_in_executor(None, _new_data.wait)
        _new_data.clear()
        if _latest_payload and connection_manager.active_connections:
            await connection_manager.broadcast(_latest_payload)


async def heartbeat_loop():
    """Keep stream-health changes visible while frames are stalled."""
    global _latest_payload
    while True:
        await asyncio.sleep(1)
        if not _latest_payload or not connection_manager.active_connections:
            continue
        try:
            payload = json.loads(_latest_payload)
            payload["runtime"] = runtime_snapshot()
            payload["frame"]["emitted_at_ms"] = round(time.time() * 1000)
            _latest_payload = json.dumps(payload)
            await connection_manager.broadcast(_latest_payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue


def safe_source_label(stream_url: str) -> str:
    """Return a log-safe stream URL with any embedded credentials removed."""
    parsed = urlsplit(stream_url)
    if not parsed.hostname:
        return stream_url
    host = parsed.hostname
    if ":" in host:
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def open_live_stream(stream_url: str) -> cv2.VideoCapture:
    """Open a direct network camera feed without passing it through yt-dlp."""
    print(f"📱 Connecting to live camera stream: {safe_source_label(stream_url)}")
    cap = cv2.VideoCapture(stream_url)
    # Keep latency bounded when the selected OpenCV backend supports this option.
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def main(
    video_path: Optional[str] = None,
    server_port: int = 8001,
    stream_url: Optional[str] = None,
):
    if video_path and stream_url:
        raise ValueError("Choose either video_path or stream_url, not both")

    # Bring up liveness and the dashboard WebSocket before waiting for a phone
    # publisher. A disposable cloud pod must remain useful while the operator
    # is still setting up the camera.
    app = create_app()
    print(f"\n🚀 Live server starting on http://0.0.0.0:{server_port}  (WS: /ws, Health: /health)")
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=server_port), daemon=True
    )
    server_thread.start()

    is_url = bool(video_path) and video_path.lower().startswith(("http://", "https://"))
    reopen_source: Callable[[], cv2.VideoCapture] | None = None
    if stream_url:
        cap = open_live_stream(stream_url)
        reopen_source = lambda: open_live_stream(stream_url)
        source_desc = f"live stream '{safe_source_label(stream_url)}'"
    elif video_path:
        if not is_url and not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return
        try:
            resolved = resolve_video_source(video_path)
        except RuntimeError as e:
            print(f"❌ {e}")
            return
        print(f"🎞️  Using video source: {video_path}")
        cap = cv2.VideoCapture(resolved)
        source_desc = f"video '{video_path if is_url else os.path.basename(video_path)}'"
    else:
        cam_id = select_camera()
        cap = cv2.VideoCapture(cam_id)
        source_desc = f"Camera {cam_id}"

    if stream_url and not cap.isOpened() and reopen_source is not None:
        update_runtime(source_state="waiting")
        while not cap.isOpened():
            print("⏳ Waiting for the phone publisher at the configured relay…")
            time.sleep(2)
            cap = reopen_source()
    elif not cap.isOpened():
        print("❌ Could not open video source")
        return

    if stream_url and reopen_source is not None:
        update_runtime(source_state="waiting")
        while True:
            ok, _first_frame = cap.read()
            if ok:
                break
            cap.release()
            time.sleep(1)
            cap = reopen_source()

    update_runtime(source_state="calibrating")
    clip_buffer = configured_clip_buffer(stream_url)
    if clip_buffer is not None:
        clip_buffer.start()
    team_classifier = calibrate_team_classifier(cap)
    update_runtime(source_state="live")

    # Rewind local video so calibration frames are not skipped.
    # (Network/YouTube streams are usually not seekable, so skip the rewind.)
    if video_path and not is_url:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    stop_hint = "Press Q in a CV window to stop." if DISPLAY_WINDOWS else "Press Ctrl+C to stop."
    print(f"\n{source_desc} started. {stop_hint}")
    analytics_loop(
        cap,
        team_classifier,
        tolerate_read_failures=video_path is None or stream_url is not None,
        reopen_source=reopen_source,
        clip_buffer=clip_buffer,
    )


def analytics_loop(
    cap: cv2.VideoCapture,
    team_classifier: TeamClassifier,
    tolerate_read_failures: bool = False,
    reopen_source: Callable[[], cv2.VideoCapture] | None = None,
    clip_buffer: EncodedClipBuffer | None = None,
):
    """
    Main detection/tracking/projection loop. Runs on the main thread so OpenCV
    GUI operations (imshow, waitKey) work correctly. Publishes payloads to
    shared state for the asyncio broadcast task in the server thread.
    """
    global _latest_payload, _observation_recorder

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

    fps = cap.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 1 else 30.0
    print(f"   Video ~{fps:.1f} fps; live coaching payload on /ws\n")

    match_start = time.time()
    source_start_monotonic = time.monotonic()
    frame_idx = 0
    cached_annotated = None
    cached_pitch = None
    cached_voronoi = None
    failed_reads = 0
    preserved_event_ids: set[str] = set()
    recording_path = os.environ.get("RTGS_OBSERVATION_RECORDING")
    recorder = ObservationRecorder(
        recording_path,
        RecordingHeader(
            scenario=os.environ.get("RTGS_RUN_ID", "live-recording"),
            match=match_controller.snapshot(),
        ),
    ) if recording_path else None
    _observation_recorder = recorder

    while True:
        ret, frame = cap.read()
        if not ret:
            if not tolerate_read_failures:
                break
            failed_reads += 1
            if failed_reads == 1 or failed_reads % 30 == 0:
                print(f"⚠️  Camera frame unavailable; waiting for DroidCam (attempt {failed_reads})")
            update_runtime(source_state="stalled")
            if reopen_source is not None and failed_reads >= 20:
                cap.release()
                update_runtime(
                    source_state="reconnecting",
                    reconnect_count=runtime_snapshot()["reconnect_count"] + 1,
                )
                cap = reopen_source()
                tracker.reset()
                M_buffer.clear()
                failed_reads = 0
            time.sleep(0.25)
            continue
        if failed_reads:
            print("✅ Camera frames resumed")
            failed_reads = 0
        update_runtime(source_state="live")
        frame_idx += 1
        source_timestamp_ms = round(cap.get(cv2.CAP_PROP_POS_MSEC))
        if source_timestamp_ms <= 0:
            source_timestamp_ms = round((time.monotonic() - source_start_monotonic) * 1000)

        if (
            PROCESS_EVERY > 1
            and frame_idx % PROCESS_EVERY != 1
            and cached_annotated is not None
        ):
            show_window("Camera View", cached_annotated)
            if cached_pitch is not None:
                show_window("Pitch Radar", cached_pitch)
            if cached_voronoi is not None:
                show_window("Voronoi", cached_voronoi)
            if quit_requested():
                break
            continue

        processing_started = time.monotonic()

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
        frame_reference_points, pitch_reference_points, keypoint_confidences = (
            field_keypoint_correspondences(result_field, CONFIG.vertices)
        )
        frame_reference_points /= INFER_SCALE

        if len(frame_reference_points) < 4:
            cached_annotated = annotated_frame
            show_window("Camera View", annotated_frame)
            if quit_requested():
                break
            continue

        transformer = ViewTransformer(source=frame_reference_points, target=pitch_reference_points)
        robust_m, inlier_mask = cv2.findHomography(
            frame_reference_points.astype(np.float32),
            pitch_reference_points.astype(np.float32),
            cv2.RANSAC,
            5.0,
        )
        if robust_m is not None:
            transformer.m = robust_m
        normalized_m = transformer.m / max(abs(transformer.m[2, 2]), 1e-9)
        M_buffer.append(normalized_m)
        transformer.m = np.mean(np.array(M_buffer), axis=0)

        reprojected = transformer.transform_points(frame_reference_points)
        reprojection_error_m = float(
            np.mean(np.linalg.norm(reprojected - pitch_reference_points, axis=1)) / 100.0
        )
        visible_pitch_fraction = min(
            float(
                cv2.contourArea(cv2.convexHull(frame_reference_points.astype(np.float32)))
                / max(frame.shape[0] * frame.shape[1], 1)
            ),
            1.0,
        )
        keypoint_confidence = float(np.mean(keypoint_confidences))
        inlier_ratio = float(np.mean(inlier_mask)) if inlier_mask is not None else 0.0
        calibration_confidence = float(
            max(0.0, min(
                keypoint_confidence
                * inlier_ratio
                * math.exp(-reprojection_error_m / 2.0)
                * min(visible_pitch_fraction / 0.25, 1.0),
                1.0,
            ))
        )

        pitch_detections = sv.Detections.merge(
            [players_detections, goalkeepers_detections]
        )

        if len(pitch_detections) == 0 and len(ball_detections) == 0:
            cached_annotated = annotated_frame
            show_window("Camera View", annotated_frame)
            if quit_requested():
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

        player_observations = []
        for index, point in enumerate(pitch_players_xy):
            team_id = int(pitch_detections.class_id[index])
            if team_id not in (0, 1):
                continue
            confidence = (
                float(pitch_detections.confidence[index])
                if pitch_detections.confidence is not None
                else 0.0
            )
            tracker_id = (
                int(payload_tracker_ids[index])
                if index < len(payload_tracker_ids)
                else None
            )
            player_observations.append(PlayerObservation(
                team="team0" if team_id == 0 else "team1",
                point=(
                    float(point[0]) / CONFIG.length * PITCH_LENGTH_M,
                    float(point[1]) / CONFIG.width * PITCH_WIDTH_M,
                ),
                confidence=confidence,
                track_id=tracker_id,
                role="outfield" if index < len(players_detections) else "goalkeeper",
            ))

        canonical_ball = None
        ball_confidence = None
        if len(pitch_ball_xy) > 0:
            canonical_ball = (
                float(pitch_ball_xy[0, 0]) / CONFIG.length * PITCH_LENGTH_M,
                float(pitch_ball_xy[0, 1]) / CONFIG.width * PITCH_WIDTH_M,
            )
            if ball_detections.confidence is not None:
                ball_confidence = float(ball_detections.confidence[0])

        live_match_state = match_controller.snapshot()
        observation = FrameObservation(
            frame_id=frame_idx,
            timestamp_ms=source_timestamp_ms,
            players=player_observations,
            ball=canonical_ball,
            ball_confidence=ball_confidence,
            calibration_confidence=calibration_confidence,
            visible_pitch_fraction=visible_pitch_fraction,
            reprojection_error_m=reprojection_error_m,
            match_clock_s=float(live_match_state["clock_s"]),
            period=live_match_state["period"],
            phase=live_match_state["phase"],
        )
        if recorder is not None:
            recorder.record_frame(observation)
        directions = match_controller.directions()
        with analytics_lock:
            analytics = analytics_engine.update(observation, directions)
        if clip_buffer is not None:
            for event in analytics.get("events", []):
                event_id = str(event.get("id", ""))
                if event_id and event_id not in preserved_event_ids and event.get("type") == "shot":
                    preserved_event_ids.add(event_id)
                    clip_buffer.preserve(event_id)
        payload = build_payload_v2(
            observation=observation,
            analytics=analytics,
            match_state=live_match_state,
            runtime=runtime_snapshot(),
        )
        processed_at = time.monotonic()
        with _runtime_lock:
            _runtime_state["last_frame_at"] = processed_at
            _runtime_state["frame_times"].append(processed_at)
            _runtime_state["processing_latency_ms"] = round((processed_at - processing_started) * 1000, 2)
        payload["runtime"] = runtime_snapshot()
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

        # Reviewed and provisional shot origins from the shared analytics engine.
        for shot in analytics["chance_quality"]["shots"]:
            if shot.get("location"):
                px = int(float(shot["location"][0]) / PITCH_LENGTH_M * CONFIG.length * 0.1) + 50
                py = int(float(shot["location"][1]) / PITCH_WIDTH_M * CONFIG.width * 0.1) + 50
                cv2.putText(pitch_img, f"xG {shot['xg']:.2f}",
                            (px + 8, py), cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.circle(pitch_img, (px, py), 8, (0, 0, 255), 2)
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

                show_window("Voronoi", voronoi_img)

        # Cumulative xG overlay from the same data sent to the web dashboard.
        team_chance = analytics["chance_quality"]["teams"]
        cv2.putText(annotated_frame, f"Team 1 xG: {team_chance[0]['xg']:.2f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 191, 0), 2, cv2.LINE_AA)
        cv2.putText(annotated_frame, f"Team 2 xG: {team_chance[1]['xg']:.2f}",
                    (10, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (147, 20, 255), 2, cv2.LINE_AA)

        cached_annotated = annotated_frame
        cached_pitch = pitch_img
        cached_voronoi = voronoi_img
        show_window("Camera View", annotated_frame)
        show_window("Pitch Radar", pitch_img)
        if voronoi_img is not None:
            show_window("Voronoi", voronoi_img)

        if quit_requested():
            break

    cap.release()
    if recorder is not None:
        recorder.close()
    _observation_recorder = None
    if clip_buffer is not None:
        clip_buffer.stop()
    update_runtime(source_state="finished")
    if DISPLAY_WINDOWS:
        cv2.destroyAllWindows()

    final = analytics_engine.snapshot()
    print("\n=== Final quality-gated team summary ===")
    for team, label in enumerate(("Team 1", "Team 2")):
        chance = final["chance_quality"]["teams"][team]
        progression = final["progression"]["teams"][team]
        print(f"{label}: shots {chance['shots']} | xG {chance['xg']:.2f} | final-third entries {progression['final_third_entries']} | box entries {progression['penalty_area_entries']}")


def create_app() -> FastAPI:
    """Create the FastAPI app with health check and WebSocket endpoints."""
    app = FastAPI()

    @app.get("/health")
    @app.get("/health/live")
    async def health():
        return {"status": "ok", "service": "live", **runtime_snapshot()}

    @app.get("/health/ready")
    async def ready():
        status = runtime_snapshot()
        ready_now = status["source_state"] == "live" and status["last_frame_age_ms"] is not None and status["last_frame_age_ms"] <= 3000
        return {"status": "ok" if ready_now else "starting", "ready": ready_now, **status}

    @app.get("/api/live/status")
    async def live_status():
        return {**runtime_snapshot(), "match": match_controller.snapshot()}

    @app.get("/api/live/artifacts")
    async def live_artifacts():
        data_root = Path(os.environ.get("RTGS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
        data_root.mkdir(parents=True, exist_ok=True)
        bundle = data_root / "live-artifacts.zip"
        with analytics_lock:
            summary = {
                "runtime": runtime_snapshot(),
                "match": match_controller.snapshot(),
                "analytics": analytics_engine.snapshot(),
            }
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("run-summary.json", json.dumps(summary, indent=2))
            for filename in ("live-observations.jsonl.gz", "live_match_state.json"):
                path = data_root / filename
                if path.is_file():
                    archive.write(path, filename)
            clips = data_root / "live-clips"
            if clips.is_dir():
                for path in clips.glob("*.mp4"):
                    archive.write(path, f"event-clips/{path.name}")
        return FileResponse(bundle, filename=f"rtgs-{_runtime_state['run_id']}-live.zip")

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await connection_manager.connect(ws)
        try:
            while True:
                raw = await ws.receive_text()
                command_id = None
                try:
                    command = json.loads(raw)
                    command_id = command.get("command_id")
                    if _observation_recorder is not None:
                        source_ms = 0
                        try:
                            source_ms = int(json.loads(_latest_payload).get("frame", {}).get("source_timestamp_ms", 0))
                        except (TypeError, ValueError, json.JSONDecodeError):
                            pass
                        _observation_recorder.record_command(source_ms, command)
                    if command.get("type") == "event.review":
                        payload = command.get("payload") or {}
                        with analytics_lock:
                            existing = next((item for item in analytics_engine.events if item["id"] == str(payload.get("event_id", ""))), None)
                            previous_goal = bool(existing and existing.get("outcome") == "goal" and existing.get("status") != "rejected")
                            ok = analytics_engine.review_event(
                                str(payload.get("event_id", "")),
                                payload,
                                match_controller.directions(),
                            )
                            updated = next((item for item in analytics_engine.events if item["id"] == str(payload.get("event_id", ""))), None)
                            current_goal = bool(updated and updated.get("outcome") == "goal" and updated.get("status") != "rejected")
                        if ok and previous_goal != current_goal and updated and updated.get("team") in ("team0", "team1"):
                            state = match_controller.snapshot()
                            score = list(state["score"])
                            team_index = 0 if updated["team"] == "team0" else 1
                            score[team_index] = max(0, score[team_index] + (1 if current_goal else -1))
                            match_controller.apply({"type": "match.set_score", "payload": {"score": score}})
                        error = None if ok else "event not found"
                    else:
                        ok, error, reset_metrics = match_controller.apply(command)
                        if reset_metrics:
                            with analytics_lock:
                                analytics_engine.reset()
                    await ws.send_text(json.dumps({
                        "type": "command.ack",
                        "command_id": command_id,
                        "ok": ok,
                        "error": error,
                    }))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    await ws.send_text(json.dumps({
                        "type": "command.ack",
                        "command_id": command_id,
                        "ok": False,
                        "error": str(exc),
                    }))
        except WebSocketDisconnect:
            connection_manager.disconnect(ws)

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(broadcast_loop())
        asyncio.create_task(heartbeat_loop())

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Real-time soccer analytics with Expected Goals (xG).")
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--video", type=str, default=None,
        help="Path to a video file OR a URL (including YouTube). "
             "If omitted, a live camera is used.")
    source_group.add_argument(
        "--stream", type=str, default=None,
        help="Direct live-camera URL (for example an iPhone app's RTSP or "
             "MJPEG/HTTP URL). The URL is passed directly to OpenCV.")
    parser.add_argument(
        "--headless", action="store_true",
        help="Run without OpenCV preview windows; analytics still publish to the dashboard.")
    parser.add_argument("--port", type=int, default=8001, help="Live API/WebSocket port.")
    args = parser.parse_args()
    if args.headless:
        DISPLAY_WINDOWS = False
    main(video_path=args.video, stream_url=args.stream, server_port=args.port)
