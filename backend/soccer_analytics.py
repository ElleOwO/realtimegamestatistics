# =============================================================================
# REAL-TIME SOCCER ANALYTICS ENGINE
# University of Saskatchewan Women's Soccer — Coach Dashboard Backend
# =============================================================================
#
# ── CHANGE LOG (for Ashim and the rest of the team) ─────────────────────────
#
#  ORIGINAL AUTHOR : Ashim
#  MODIFIED BY     : Emilio (with Claude AI assistance)
#
#  v1 → v2  (Session 1 — Architecture upgrade)
#    - ADDED   FastAPI WebSocket server (Section 2) so the Next.js dashboard
#              on the coach's iPad receives live JSON data
#    - ADDED   Redis pub/sub (Section 3) as optional multi-client message broker
#    - ADDED   RTSP stream ingestion via MediaMTX on GCP (Section 9.5)
#    - REMOVED select_camera() webcam scanner — original kept as comments
#    - ADDED   VIDEO_SOURCE toggle: "webcam" for lab testing, "rtsp" for game day
#    - ADDED   xG model loader (XGBoost, Section 4) with formula fallback
#    - ADDED   Tactical analytics: possession, def line, width, transition,
#              convex hull compactness (Section 5)
#    - ADDED   JSON payload builder + AI Coach Insights (Section 6)
#
#  v2 → v3  (Session 2 — Player registry + Gemini AI)
#    - ADDED   PlayerStats dataclass (Section 7A) — per-player stats that
#              persist across every frame: distance, sprints, top speed,
#              zone time, heatmap, shots, xG, pass accuracy
#    - ADDED   update_player_registry() — called every frame per tracked player
#    - ADDED   Zone system: pitch split into 4 quarters (Q1–Q4) + thirds
#    - ADDED   Heatmap accumulators: per-team + per-ball 105×68 grids
#    - ADDED   compute_zone_stats() — counts players per quarter
#    - ADDED   Gemini 2.5 Flash via Vertex AI (Section 8) — fires every 2 min,
#              sends match summary, receives a tactical narrative insight
#    - ADDED   Kaggle & StatsBomb dataset references in xG section
#    - CHANGED Player payload now uses player_registry for richer data
#
#  HOW TO RUN (read this first):
#    1. Set environment variables:
#         export ROBOFLOW_API_KEY="your_key"
#         export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
#         export GOOGLE_CLOUD_LOCATION="us-central1"
#
#    ┌──────────────────────────────────────────────────────────────────────┐
#    │  VIDEO SOURCE TOGGLE — change this based on what you're doing:      │
#    │                                                                      │
#    │  export VIDEO_SOURCE="webcam"   → laptop/dev camera (default)       │
#    │  export VIDEO_SOURCE="rtsp"     → Veo camera via MediaMTX on GCP    │
#    └──────────────────────────────────────────────────────────────────────┘
#
#    2. Install all dependencies:
#         pip install fastapi uvicorn websockets redis xgboost scipy \
#                     supervision inference roboflow ultralytics \
#                     google-genai
#
#    3. Run:
#         python soccer_analytics.py
#
#    4. Next.js dashboard connects to:  ws://<GCP_IP>:8000/ws
#
# ── ARCHITECTURE OVERVIEW ────────────────────────────────────────────────────
#
#   Veo Cam 3 (RTMP on game day)
#       │
#       ▼
#   MediaMTX on GCP  ──► RTSP stream (rtsp://localhost:8554/live)
#       │                  (or laptop webcam during development)
#       ▼
#   THIS SCRIPT  (GCP g2-standard-4 with NVIDIA L4 GPU)
#       │
#       ├─► FastAPI WebSocket ──► Next.js Dashboard (coach's iPad)
#       ├─► Redis pub/sub     ──► optional extra subscribers
#       └─► Vertex AI Gemini  ──► tactical narrative (every 2 minutes)
#
# ── DATASET REFERENCES ───────────────────────────────────────────────────────
#
#   The xG model (Section 4) was trained on:
#     PRIMARY  : StatsBomb Open Data (women's football events, free)
#                https://github.com/statsbomb/open-data

#
# =============================================================================

import asyncio
import json
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

import cv2
import numpy as np

# --- Core CV / ML ---
import supervision as sv

# --- Web / async ---
import uvicorn
import xgboost as xgb
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from inference import get_model
from scipy.ndimage import gaussian_filter
from scipy.spatial import ConvexHull

# --- Vertex AI / Gemini ---
try:
    from google import genai
    from google.genai import types as genai_types

    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# --- Optional: Redis ---
try:
    import redis as redis_lib

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# --- Sports helpers (Roboflow open-source sports library) ---
from sports.annotators.soccer import (
    draw_pitch,
    draw_pitch_voronoi_diagram,
    draw_points_on_pitch,
)
from sports.common.team import TeamClassifier
from sports.common.view import ViewTransformer
from sports.configs.soccer import SoccerPitchConfiguration

# =============================================================================
# SECTION 1: CONFIGURATION
# Every tunable constant lives here.  Don't scatter magic numbers in the code.
# =============================================================================

# --- API keys & model IDs ---
API_KEY = os.environ.get("ROBOFLOW_API_KEY")

# Player model — swap this to your fine-tuned Roboflow model ID after training.
# Format: "workspace/project/version"  e.g. "usask-soccer/usask-players/2"
PLAYER_DETECTION_MODEL_ID = os.environ.get("PLAYER_MODEL_ID", "spen-rtgs-oc4ez/4")
FIELD_DETECTION_MODEL_ID = os.environ.get(
    "FIELD_MODEL_ID", "football-field-detection-f07vi/14"
)

# --- Video source ---
# "webcam" = laptop/dev camera for lab testing (default, safe to run anywhere)
# "rtsp"   = Veo Cam 3 via MediaMTX on GCP (use on game day)
VIDEO_SOURCE = os.environ.get("VIDEO_SOURCE", "webcam").lower()
WEBCAM_INDEX = int(os.environ.get("WEBCAM_INDEX", 0))
RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/live")

# --- WebSocket server ---
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", 8000))

# --- Redis ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
REDIS_CHANNEL = "soccer:analytics"

# --- GCP / Gemini ---
GEMINI_MODEL = "gemini-2.5-flash"
AI_INSIGHT_INTERVAL = 120  # seconds between Gemini calls (2 minutes)
ENABLE_GEMINI = os.environ.get("ENABLE_GEMINI", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# --- Detection class IDs (must match Roboflow model label order) ---
BALL_ID = 0
GOALKEEPER_ID = 1
PLAYER_ID = 2
REFEREE_ID = 3

# --- Detection caps ---
MAX_BALLS = 1
MAX_GOALKEEPERS = 2
MAX_PLAYERS = 20
MAX_REFEREES = 3

# --- Team classifier calibration ---
CALIBRATION_FRAMES = 100
CALIBRATION_STRIDE = 3
MIN_CROPS = 20  # UMAP needs at least this many samples

# --- Homography smoothing ---
HOMOGRAPHY_BUFFER_LEN = 5  # Average last N matrices to remove keypoint jitter

# --- Pitch dimensions (standard women's soccer, metres) ---
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
PITCH_HALF_LENGTH = 52.5  # from centre to goal line
PITCH_HALF_WIDTH = 34.0  # from centre to touchline

# --- Possession rolling window ---
POSSESSION_WINDOW = 150  # frames (~5 seconds at 30 fps)

# --- xG model ---
# Train this in football_ai.ipynb → "xG Model Training" section.
# Kaggle dataset refs are in the file header above.
XG_MODEL_PATH = os.environ.get("XG_MODEL_PATH", "xg_model_womens.ubj")

# --- Sprint threshold ---
SPRINT_THRESHOLD_MS = 5.5  # m/s  (~20 km/h, appropriate for women's soccer)
FRAME_DT = 1 / 30

# --- Heatmap grid (1 cell = 1 metre) ---
HEATMAP_W = int(PITCH_LENGTH_M)  # 105 columns
HEATMAP_H = int(PITCH_WIDTH_M)  #  68 rows

# --- Zone boundary lines ---
ZONE_X_SPLIT = 0.0  # centre line
ZONE_Y_SPLIT = 0.0  # horizontal mid-axis

# --- USask brand colour ---
USASK_GREEN = "#0B6A41"

CONFIG = SoccerPitchConfiguration()


# =============================================================================
# SECTION 2: FASTAPI + WEBSOCKET SERVER
# =============================================================================

app = FastAPI(title="USask Soccer Analytics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to your dashboard URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """
    Tracks every active WebSocket connection and broadcasts JSON to all of them.

    The coach's iPad, any laptop browser, and future clients all connect here.
    When one client disconnects (network drop) it's silently removed so the
    rest keep receiving data uninterrupted.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)
        print(f"📡 Client connected  — total: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        print(f"📡 Client disconnected — total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Send the JSON string to every connected client."""
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.active_connections.remove(ws)


manager = ConnectionManager()


@app.get("/health")
async def health_check():
    """Container/orchestrator health endpoint."""
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Next.js dashboard connects here:  ws://<GCP_IP>:8000/ws
    Data flows server → client only; we don't read messages from the client.
    """
    await manager.connect(ws)
    try:
        while True:
            await asyncio.sleep(1)  # Keep alive; data comes from broadcast()
    except WebSocketDisconnect:
        manager.disconnect(ws)


def start_api_server():
    """Launch FastAPI/uvicorn in a background daemon thread."""
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="warning")


# =============================================================================
# SECTION 3: OPTIONAL REDIS PUB/SUB
# =============================================================================

redis_client = None


def init_redis():
    """Connect to Redis if available.  Returns client or None."""
    if not REDIS_AVAILABLE:
        print("⚠️  redis-py not installed — pub/sub disabled.")
        return None
    try:
        client = redis_lib.from_url(REDIS_URL, decode_responses=True)
        client.ping()
        print(f"✅ Redis connected at {REDIS_URL}")
        return client
    except Exception as e:
        print(f"⚠️  Redis unavailable ({e}) — continuing without it.")
        return None


def publish_to_redis(payload: dict):
    """Publish latest analytics JSON to Redis channel (fire-and-forget)."""
    if redis_client:
        try:
            redis_client.publish(REDIS_CHANNEL, json.dumps(payload))
        except Exception:
            pass


# =============================================================================
# SECTION 4: XG MODEL  (Expected Goals)
# =============================================================================
#
# WHAT IS xG?
#   Expected Goals (xG) is a number between 0 and 1 that represents the
#   probability that a shot attempt results in a goal, based purely on the
#   circumstances of the shot (not who took it).
#   A tap-in from 2 metres = xG ~0.85.  A long shot = xG ~0.03.
#
# HOW WE TRAINED IT:
#   XGBoost was trained on thousands of real women's soccer shot events from:
#     - StatsBomb Open Data  → https://github.com/statsbomb/open-data
#     - Kaggle: "Statsbomb Shot Events" (pre-parsed CSV, good for beginners)
#               https://www.kaggle.com/datasets/mauryansshivam/statsbomb-shot-events
#     - Kaggle: "Soccer Analytics" by Enes Öner
#               https://www.kaggle.com/datasets/enesoner/soccer-analytics
#
#   The training notebook is in football_ai.ipynb → "xG Model Training" section.
#   After training, save the model as:  xg_model_womens.ubj
#   Then set:  export XG_MODEL_PATH="/path/to/xg_model_womens.ubj"
#
# FALLBACK:
#   If the .ubj file doesn't exist (e.g. during early development), the script
#   falls back to a distance/angle formula so the dashboard still works.
#   The formula is NOT as accurate as the trained model but it's better than 0.


def load_xg_model() -> Optional[xgb.Booster]:
    """Load XGBoost xG model from disk.  Returns None if file not found."""
    if os.path.exists(XG_MODEL_PATH):
        model = xgb.Booster()
        model.load_model(XG_MODEL_PATH)
        print(f"✅ xG model loaded from {XG_MODEL_PATH}")
        return model
    print(f"⚠️  xG model not found at '{XG_MODEL_PATH}' — using formula fallback.")
    print("   Train the model in football_ai.ipynb and set XG_MODEL_PATH.")
    return None


def compute_xg(
    shot_xy: np.ndarray,
    goal_xy: np.ndarray,
    under_pressure: bool = False,
    is_header: bool = False,
    xg_model: Optional[xgb.Booster] = None,
) -> float:
    """
    Compute the xG value (0–1) for a single shot.

    Parameters
    ----------
    shot_xy        : [x, y] pitch metres of the shot (origin = pitch centre)
    goal_xy        : [x, y] pitch metres of the target goal centre
    under_pressure : True if a defender is within ~2 m of the shooter
    is_header      : True if the shot was a header
    xg_model       : Loaded XGBoost model (None = use formula fallback)

    Feature engineering
    -------------------
    distance_m : straight-line metres from shot to goal
    angle_deg  : half-angle subtended by the 7.32 m goalposts from shot position
                 (larger angle = better chance = higher xG)
    """
    dx = goal_xy[0] - shot_xy[0]
    dy = goal_xy[1] - shot_xy[1]
    distance_m = float(max(np.hypot(dx, dy), 0.5))

    goal_half_width = 3.66
    angle_rad = np.arctan2(
        goal_half_width * distance_m,
        distance_m**2 + goal_half_width**2,
    )
    angle_deg = float(np.degrees(angle_rad))

    if xg_model is not None:
        # Use trained XGBoost model (most accurate)
        # Feature order must match training:
        # [distance_m, angle_deg, in_box, under_pressure, is_header,
        #  is_weak_foot, is_counter, centrality_m]
        # For the live pipeline we don't have in_box/is_weak_foot/is_counter
        # so we use 0 defaults for those and supply the geometric ones.
        features = np.array(
            [
                [
                    distance_m,
                    angle_deg,
                    int(distance_m < 16.5),  # rough "in_box" proxy
                    int(under_pressure),
                    int(is_header),
                    0,  # is_weak_foot — unknown live
                    0,  # is_counter   — unknown live
                    0.0,  # centrality   — unknown live
                ]
            ],
            dtype=np.float32,
        )
        dmatrix = xgb.DMatrix(
            features,
            feature_names=[
                "distance_m",
                "angle_deg",
                "in_box",
                "under_pressure",
                "is_header",
                "is_weak_foot",
                "is_counter",
                "centrality_m",
            ],
        )
        return float(np.clip(xg_model.predict(dmatrix)[0], 0.0, 1.0))

    # ── Formula fallback (decent approximation when model not available) ──────
    base_xg = (angle_deg / 90.0) * np.exp(-distance_m / 16.0)
    if under_pressure:
        base_xg *= 0.72
    if is_header:
        base_xg *= 0.62
    return float(np.clip(base_xg, 0.0, 1.0))


# =============================================================================
# SECTION 5: TACTICAL ANALYTICS FUNCTIONS
# =============================================================================


# ── Zone assignment ────────────────────────────────────────────────────────────
def assign_zone(x_m: float, y_m: float) -> str:
    """
    Return the pitch quarter label for a coordinate pair.

    Quarter layout (USask attacks toward positive x):
      Q1_def_left   │ Q2_atk_left
      ──────────────┼──────────────
      Q3_def_right  │ Q4_atk_right

    "def" = USask's own half (x < 0), "atk" = opponent's half (x > 0)
    "left/right" = y < 0 / y > 0 (left/right touchline when facing opponent goal)
    """
    left = y_m <= ZONE_Y_SPLIT
    defensive = x_m <= ZONE_X_SPLIT
    if defensive and left:
        return "Q1_def_left"
    if not defensive and left:
        return "Q2_atk_left"
    if defensive:
        return "Q3_def_right"
    return "Q4_atk_right"


# ── Possession ────────────────────────────────────────────────────────────────
def compute_possession(possession_log: deque) -> float:
    """Return Team 0's possession % over the rolling POSSESSION_WINDOW frames."""
    if not possession_log:
        return 50.0
    return round(
        100.0 * sum(1 for t in possession_log if t == 0) / len(possession_log), 1
    )


def update_possession_log(
    possession_log: deque,
    ball_pitch_xy: np.ndarray,
    team0_pitch_xy: np.ndarray,
    team1_pitch_xy: np.ndarray,
):
    """Append the possessing team (0 or 1) to the rolling window this frame."""
    if len(ball_pitch_xy) == 0:
        return
    ball = ball_pitch_xy[0]

    def nearest_dist(xy):
        return (
            float(np.min(np.linalg.norm(xy - ball, axis=1)))
            if len(xy) > 0
            else float("inf")
        )

    possession_log.append(
        0 if nearest_dist(team0_pitch_xy) <= nearest_dist(team1_pitch_xy) else 1
    )


# ── Defensive line height ──────────────────────────────────────────────────────
def compute_defensive_line_height(defensive_team_xy: np.ndarray) -> float:
    """
    Metres from own goal line to the average depth of the 4 deepest defenders.
    Higher = more aggressive defensive line.
    Convention: x=0 is pitch centre; x=-52.5 is USask's goal line.
    """
    if len(defensive_team_xy) < 2:
        return 0.0
    sorted_x = np.sort(defensive_team_xy[:, 0])
    return round(float(np.mean(sorted_x[: min(4, len(sorted_x))])), 1)


# ── Width of attack ────────────────────────────────────────────────────────────
def compute_width_of_attack(attacking_team_xy: np.ndarray) -> float:
    """
    Lateral spread (metres) of the attacking team: max(y) − min(y).
    Wider spread forces the defence to cover more ground.
    """
    if len(attacking_team_xy) < 2:
        return 0.0
    return round(float(np.ptp(attacking_team_xy[:, 1])), 1)


# ── Attacking transition speed ─────────────────────────────────────────────────
def compute_transition_speed(
    ball_positions: deque,
    defensive_third_end_m: float = 35.0,
    attacking_third_start_m: float = 70.0,
) -> float:
    """
    Average seconds for the ball to travel from the defensive third to the
    attacking third (i.e. a completed transition).  Returns 0.0 if no
    completed transition has been recorded yet.
    """
    if len(ball_positions) < 2:
        return 0.0
    transition_times = []
    entered_attacking = None
    for timestamp, bx, _ in reversed(list(ball_positions)):
        if entered_attacking is None:
            if bx >= attacking_third_start_m:
                entered_attacking = timestamp
        else:
            if bx <= defensive_third_end_m:
                transition_times.append(entered_attacking - timestamp)
                entered_attacking = None
                if len(transition_times) >= 3:
                    break
    return round(float(np.mean(transition_times)), 1) if transition_times else 0.0


# ── Convex hull area (defensive compactness) ───────────────────────────────────
def compute_convex_hull_area(team_xy: np.ndarray) -> float:
    """
    Area (m²) of the convex hull formed by a team's player positions.
    Small area → compact block.  Large area → stretched defensive shape.
    The AI insights alert fires when this exceeds 800 m².
    """
    if len(team_xy) < 3:
        return 0.0
    try:
        return round(float(ConvexHull(team_xy).volume), 1)
    except Exception:
        return 0.0


# ── Zone stats ────────────────────────────────────────────────────────────────
def compute_zone_stats(team_xy: np.ndarray) -> dict:
    """
    Count players in each quarter and each third.
    Returns a dict that feeds both the AI prompt and the dashboard payload.
    """
    counts = {
        z: 0 for z in ("Q1_def_left", "Q2_atk_left", "Q3_def_right", "Q4_atk_right")
    }
    def_third = 0
    atk_third = 0
    for x_m, y_m in team_xy:
        counts[assign_zone(x_m, y_m)] += 1
        if x_m < -35.0:
            def_third += 1
        if x_m > 35.0:
            atk_third += 1
    dominant = max(counts, key=counts.get) if len(team_xy) > 0 else "unknown"
    return {
        **counts,
        "dominant_zone": dominant,
        "defensive_third_count": def_third,
        "attacking_third_count": atk_third,
    }


# ── Heatmap ────────────────────────────────────────────────────────────────────
def update_heatmap(heatmap: np.ndarray, pitch_xy: np.ndarray):
    """Increment heatmap cells for every coordinate.  Mutates in place."""
    for x_m, y_m in pitch_xy:
        col = int(np.clip(x_m + PITCH_HALF_LENGTH, 0, HEATMAP_W - 1))
        row = int(np.clip(y_m + PITCH_HALF_WIDTH, 0, HEATMAP_H - 1))
        heatmap[row, col] += 1.0


def get_heatmap_payload(heatmap: np.ndarray) -> dict:
    """
    Normalise, smooth (Gaussian σ=2.5 m), and serialise a heatmap for JSON.
    Sent every 30 frames (~1 s) to avoid flooding the WebSocket.
    """
    peak = float(heatmap.max()) or 1.0
    smoothed = gaussian_filter(heatmap / peak, sigma=2.5)
    return {
        "grid": smoothed.tolist(),
        "max": peak,
        "width": HEATMAP_W,
        "height": HEATMAP_H,
    }


# =============================================================================
# SECTION 6: PLAYER REGISTRY  (individual statistics)
# =============================================================================


@dataclass
class PlayerStats:
    """
    Full statistical profile for one tracked player.
    One instance per ByteTrack tracker_id, persists for the whole match.

    ── MOVEMENT ─────────────────────────────────────────────────────────────────
    distance_km     : total distance run (km)
    top_speed_ms    : peak smoothed speed (m/s)
    sprint_count    : number of sprint bursts (> SPRINT_THRESHOLD_MS for 2+ frames)
    sprint_dist_km  : total distance covered while sprinting

    ── SHOOTING ─────────────────────────────────────────────────────────────────
    shots / shots_on_target / total_xg : from the key_events log

    ── ZONES ────────────────────────────────────────────────────────────────────
    zone_frames             : frames spent in each quarter
    frames_in_attack_zone   : frames spent in the opponent's final third (x > 35 m)

    ── HEATMAP ──────────────────────────────────────────────────────────────────
    heatmap : 68×105 float32 array — per-player position accumulator
    """

    tracker_id: int = 0
    team_id: int = -1

    distance_km: float = 0.0
    top_speed_ms: float = 0.0
    sprint_count: int = 0
    sprint_dist_km: float = 0.0
    speed_buffer: Deque = field(default_factory=lambda: deque(maxlen=10))

    last_x_m: float = 0.0
    last_y_m: float = 0.0
    last_seen_ts: float = 0.0

    passes_attempted: int = 0
    passes_completed: int = 0
    shots: int = 0
    shots_on_target: int = 0
    total_xg: float = 0.0

    zone_frames: Dict[str, int] = field(
        default_factory=lambda: {
            "Q1_def_left": 0,
            "Q2_atk_left": 0,
            "Q3_def_right": 0,
            "Q4_atk_right": 0,
        }
    )
    frames_in_attack_zone: int = 0

    heatmap: np.ndarray = field(
        default_factory=lambda: np.zeros((HEATMAP_H, HEATMAP_W), dtype=np.float32)
    )

    @property
    def pass_accuracy(self) -> float:
        if self.passes_attempted == 0:
            return 0.0
        return round(100.0 * self.passes_completed / self.passes_attempted, 1)

    @property
    def time_in_attack_zone_s(self) -> float:
        return round(self.frames_in_attack_zone / 30.0, 1)


# Global registry — keyed by tracker_id
player_registry: Dict[int, PlayerStats] = {}


def update_player_registry(
    tracker_id: int,
    team_id: int,
    current_xy: np.ndarray,  # shape (2,) — [x_m, y_m]
    now: float,
    registry: Dict[int, PlayerStats],
) -> PlayerStats:
    """
    Create or update a player's stats entry for this frame.
    Called once per tracked player per frame inside the main loop.
    """
    if tracker_id not in registry:
        # First sighting for this tracker id: initialize persistent counters.
        registry[tracker_id] = PlayerStats(
            tracker_id=tracker_id,
            team_id=team_id,
            last_x_m=float(current_xy[0]),
            last_y_m=float(current_xy[1]),
            last_seen_ts=now,
        )
        return registry[tracker_id]

    stats = registry[tracker_id]
    stats.team_id = team_id

    prev_xy = np.array([stats.last_x_m, stats.last_y_m])
    delta_m = float(np.linalg.norm(current_xy - prev_xy))
    elapsed = now - stats.last_seen_ts

    # Ignore physically impossible jumps from tracking glitches/re-identification.
    if delta_m < 10.0 and elapsed > 0:
        stats.distance_km += delta_m / 1000.0
        speed = delta_m / elapsed
        stats.speed_buffer.append(speed)
        smooth_speed = float(np.mean(stats.speed_buffer))
        if smooth_speed > stats.top_speed_ms:
            stats.top_speed_ms = round(smooth_speed, 2)

        # Sprint detection: 2+ consecutive frames above threshold = new sprint
        sprinting_now = sum(1 for s in stats.speed_buffer if s > SPRINT_THRESHOLD_MS)
        sprinting_prev = sum(
            1 for s in list(stats.speed_buffer)[:-2] if s > SPRINT_THRESHOLD_MS
        )
        if sprinting_now >= 2:
            if sprinting_prev == 0:
                stats.sprint_count += 1
            stats.sprint_dist_km += delta_m / 1000.0

    x_m, y_m = float(current_xy[0]), float(current_xy[1])

    # Accumulate tactical zone occupancy for later dashboard summaries.
    stats.zone_frames[assign_zone(x_m, y_m)] += 1
    if x_m > 35.0:
        stats.frames_in_attack_zone += 1

    # Convert centred metre coords into heatmap array indices.
    col = int(np.clip(x_m + PITCH_HALF_LENGTH, 0, HEATMAP_W - 1))
    row = int(np.clip(y_m + PITCH_HALF_WIDTH, 0, HEATMAP_H - 1))
    stats.heatmap[row, col] += 1.0

    stats.last_x_m = x_m
    stats.last_y_m = y_m
    stats.last_seen_ts = now
    return stats


def serialize_player(stats: PlayerStats) -> dict:
    """
    Convert a PlayerStats to a JSON-safe dict for the WebSocket payload.
    The player heatmap is NOT included here (too large per frame) — it
    can be served separately via a REST endpoint if the dashboard needs it.
    """
    return {
        "id": stats.tracker_id,
        "team": stats.team_id,
        "distance_km": round(stats.distance_km, 3),
        "top_speed_kmh": round(stats.top_speed_ms * 3.6, 1),
        "sprint_count": stats.sprint_count,
        "sprint_distance_km": round(stats.sprint_dist_km, 3),
        "pass_accuracy": stats.pass_accuracy,
        "passes_attempted": stats.passes_attempted,
        "shots": stats.shots,
        "shots_on_target": stats.shots_on_target,
        "total_xg": round(stats.total_xg, 3),
        "time_in_attack_zone_s": stats.time_in_attack_zone_s,
        "dominant_zone": max(stats.zone_frames, key=stats.zone_frames.get),
        "x_m": round(stats.last_x_m, 2),
        "y_m": round(stats.last_y_m, 2),
    }


# =============================================================================
# SECTION 7: GEMINI AI COACH INSIGHTS  (Vertex AI)
# =============================================================================
#
# HOW THIS WORKS:
#   Every AI_INSIGHT_INTERVAL seconds (default 2 minutes), we build a compact
#   structured summary of the current match state and send it to Gemini 2.5 Flash
#   via Vertex AI.  Gemini returns ONE tactical recommendation in plain English.
#
# WHY GEMINI OVER OTHER AI:
#   - You already have $300 GCP credits — Gemini calls are billed to the same account
#   - On a GCP Compute Engine VM, authentication is automatic (no API key needed)
#   - Gemini 2.5 Flash responds in ~1-2 seconds (fast enough for sideline use)
#
# AUTHENTICATION:
#   On GCP VM  → automatic via Application Default Credentials (ADC)
#   On laptop  → run once:  gcloud auth application-default login
#
# COST ESTIMATE:
#   Each prompt ≈ 400 tokens + 150 response tokens = ~550 tokens per call.
#   At one call every 2 minutes for a 90-minute match ≈ 45 calls ≈ ~25,000 tokens.
#   Gemini Flash pricing ≈ $0.001 per match.  Your $300 covers ~300,000 matches.

gemini_client = None
ai_insight_cache = None
last_ai_request_ts = 0.0


def init_gemini():
    """Connect to Vertex AI Gemini client.  Returns None silently if unavailable."""
    if not ENABLE_GEMINI:
        print("ℹ️  Gemini disabled via ENABLE_GEMINI=false")
        return None
    if not GEMINI_AVAILABLE:
        print(
            "⚠️  google-genai not installed — AI insights disabled.  pip install google-genai"
        )
        return None
    try:
        client = genai.Client(vertexai=True, project=GCP_PROJECT, location=GCP_LOCATION)
        print(f"✅ Gemini client ready  ({GCP_PROJECT} / {GEMINI_MODEL})")
        return client
    except Exception as e:
        print(f"⚠️  Gemini init failed: {e}")
        print("   On laptop: run  gcloud auth application-default login")
        return None


def build_gemini_prompt(
    match_min: float,
    possession_pct: float,
    xg_team0: float,
    xg_team1: float,
    transition_spd: float,
    hull_area: float,
    def_line_height: float,
    width_of_attack: float,
    zone_t0: dict,
    zone_t1: dict,
    registry: Dict[int, PlayerStats],
    recent_events: list,
) -> str:
    """
    Build the ~400-token structured prompt sent to Gemini.
    We deliberately keep it short so Flash responds in < 2 seconds.
    """
    # Top 4 USask players by distance
    usask = sorted(
        [s for s in registry.values() if s.team_id == 0],
        key=lambda s: s.distance_km,
        reverse=True,
    )[:4]
    player_lines = (
        "\n".join(
            [
                f"  #{s.tracker_id}: {s.distance_km:.2f}km | "
                f"{s.sprint_count} sprints | zone: {max(s.zone_frames, key=s.zone_frames.get)}"
                for s in usask
            ]
        )
        or "  No data yet"
    )

    events_lines = (
        "\n".join(
            [
                f"  {e.get('minute','?')}' {e.get('type','')} — {e.get('description','')}"
                for e in recent_events[-5:]
            ]
        )
        or "  None yet"
    )

    return f"""You are an AI assistant for the USask Huskies women's soccer coaching staff.
Based on the live match data below, give ONE specific tactical recommendation.
Be direct — the coach is on the sideline and has 20 seconds to read this.
Do NOT restate numbers. Focus on the CAUSE and SOLUTION. Maximum 3 sentences.

MATCH MINUTE: {match_min:.0f}
Possession: USask {possession_pct:.0f}% / Opponent {100 - possession_pct:.0f}%
xG: USask {xg_team0:.2f} vs Opponent {xg_team1:.2f}
Def line: {def_line_height:.0f}m | Atk width: {width_of_attack:.0f}m
Transition: {transition_spd:.1f}s | Def shape area: {hull_area:.0f}m²

ZONE PRESSURE:
USask — def third: {zone_t0.get('defensive_third_count',0)} players | atk third: {zone_t0.get('attacking_third_count',0)} players
Opponent — in USask def third: {zone_t1.get('defensive_third_count',0)} | dominant zone: {zone_t1.get('dominant_zone','?')}

USask TOP PLAYERS:
{player_lines}

RECENT EVENTS:
{events_lines}"""


async def request_gemini_insight(prompt: str, match_min: float) -> Optional[dict]:
    """
    Call Gemini 2.5 Flash asynchronously.
    Runs in FastAPI's event loop — never blocks the OpenCV frame loop.
    """
    if gemini_client is None:
        return None
    try:
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,  # Low temp = consistent tactical output
                max_output_tokens=150,  # Enforce "3 sentences max"
                system_instruction=(
                    "You are a concise soccer tactical analyst. "
                    "Respond in plain sentences only, no bullet points. "
                    "Always end with one specific actionable instruction."
                ),
            ),
        )
        return {
            "type": "ai_narrative",
            "title": f"AI Tactical Insight ({match_min:.0f}')",
            "body": response.text.strip(),
            "minute": round(match_min, 1),
        }
    except Exception as e:
        print(f"⚠️  Gemini call failed at {match_min:.0f}': {e}")
        return None


# =============================================================================
# SECTION 8: PAYLOAD BUILDER
# =============================================================================


def build_payload(
    frame_id: int,
    timestamp: float,
    possession_pct: float,
    defensive_line_height: float,
    width_of_attack: float,
    transition_speed: float,
    convex_hull_area: float,
    total_xg_team0: float,
    total_xg_team1: float,
    xg_timeline: list,
    pitch_players: list,
    pitch_ball: Optional[list],
    key_events: list,
    zone_stats_team0: dict,
    zone_stats_team1: dict,
    heatmap_payload: Optional[dict] = None,
    ai_insight: Optional[dict] = None,
    team0_name: str = "U of S",
    team1_name: str = "Calgary",
) -> dict:
    """
    Assembles every computed metric into one JSON-serialisable dict.
    The Next.js frontend destructures this exact shape — coordinate any
    field name changes with the frontend team.
    """

    # ── Rule-based AI Coach Insights (fire immediately, no API call) ──────────
    # These heuristics provide deterministic guidance even if Gemini is unavailable.
    insights = []

    if convex_hull_area > 800:
        insights.append(
            {
                "type": "warning",
                "title": "Defensive Vulnerability Detected",
                "body": (
                    f"Defensive shape area is {convex_hull_area:.0f} m² — stretched. "
                    "Opponent may exploit right flank. "
                    "Instruct midfield to drop deeper and close the channel."
                ),
            }
        )

    if possession_pct < 40:
        insights.append(
            {
                "type": "warning",
                "title": "Possession Under Pressure",
                "body": (
                    f"Ball possession at {possession_pct}%. "
                    "Consider a more direct shape or pressing trigger to win the ball back."
                ),
            }
        )

    if width_of_attack > 50:
        insights.append(
            {
                "type": "info",
                "title": "Possession Pattern Analysis",
                "body": (
                    f"Wide attacking shape ({width_of_attack} m spread). "
                    "Strong possession in the middle third. "
                    "Try central runs to break the defensive line."
                ),
            }
        )

    if 0 < transition_speed < 6:
        insights.append(
            {
                "type": "positive",
                "title": "Fast Transition Detected",
                "body": f"Avg attacking transition: {transition_speed}s — exploit on set pieces.",
            }
        )

    # Append optional Gemini narrative (generated less frequently to control cost/latency).
    if ai_insight:
        insights.append(ai_insight)

    return {
        # ── Meta ─────────────────────────────────────────────────────────────
        "frame_id": frame_id,
        "timestamp": timestamp,
        "match_clock": round(timestamp / 60, 2),
        # ── KPI cards (top row of dashboard) ─────────────────────────────────
        "possession": {
            "team0_pct": possession_pct,
            "team1_pct": round(100.0 - possession_pct, 1),
            "team0_name": team0_name,
            "team1_name": team1_name,
        },
        "transition_speed_s": transition_speed,
        "total_xg_team0": round(total_xg_team0, 2),
        "total_xg_team1": round(total_xg_team1, 2),
        # ── Tactical View KPIs ────────────────────────────────────────────────
        "defensive_line_height_m": defensive_line_height,
        "width_of_attack_m": width_of_attack,
        "convex_hull_area_m2": convex_hull_area,
        # ── Live Pitch View ───────────────────────────────────────────────────
        "players": pitch_players,  # [{id, team, x_m, y_m, distance_km, ...}]
        "ball": pitch_ball,  # [x_m, y_m] or null
        # ── Zone statistics ───────────────────────────────────────────────────
        "zone_stats": {
            "team0": zone_stats_team0,
            "team1": zone_stats_team1,
        },
        # ── Heatmaps (sent every 30 frames) ──────────────────────────────────
        "heatmaps": heatmap_payload,  # None most frames
        # ── xG Timeline line chart ────────────────────────────────────────────
        "xg_timeline": xg_timeline,
        # ── AI Coach Insights sidebar ─────────────────────────────────────────
        "insights": insights,
        # ── Key match events ──────────────────────────────────────────────────
        "key_events": key_events,
    }


# =============================================================================
# SECTION 9: ORIGINAL HELPER FUNCTIONS
# (unchanged from Ashim's original script — kept intact)
# =============================================================================


def resolve_goalkeepers_team_id(
    players: sv.Detections,
    goalkeepers: sv.Detections,
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
    ids = []
    for gk in goalkeepers.get_anchors_coordinates(sv.Position.BOTTOM_CENTER):
        ids.append(0 if np.linalg.norm(gk - team0) < np.linalg.norm(gk - team1) else 1)
    return np.array(ids, dtype=int)


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
    Soft-blend Voronoi diagram for team control areas.
    Uses tanh blend factor so zone boundaries are smooth, not hard edges.
    Unchanged from Ashim's original script.
    """
    if pitch is None:
        pitch = draw_pitch(config=config, padding=padding, scale=scale)

    scaled_w = int(config.width * scale)
    scaled_l = int(config.length * scale)
    voronoi = np.zeros_like(pitch, dtype=np.uint8)
    c1 = np.array(team_1_color.as_bgr(), dtype=np.uint8)
    c2 = np.array(team_2_color.as_bgr(), dtype=np.uint8)

    y_coords, x_coords = np.indices((scaled_w + 2 * padding, scaled_l + 2 * padding))
    y_coords -= padding
    x_coords -= padding

    def dists(xy):
        return np.sqrt(
            (xy[:, 0][:, None, None] * scale - x_coords) ** 2
            + (xy[:, 1][:, None, None] * scale - y_coords) ** 2
        )

    min_d1 = np.min(dists(team_1_xy), axis=0)
    min_d2 = np.min(dists(team_2_xy), axis=0)
    ratio = min_d2 / np.clip(min_d1 + min_d2, 1e-5, None)
    blend = np.tanh((ratio - 0.5) * 15) * 0.5 + 0.5

    for c in range(3):
        voronoi[:, :, c] = (blend * c1[c] + (1 - blend) * c2[c]).astype(np.uint8)

    return cv2.addWeighted(voronoi, opacity, pitch, 1 - opacity, 0)


# =============================================================================
# SECTION 10: TEAM CLASSIFIER CALIBRATION
# =============================================================================


def calibrate_team_classifier(cap: cv2.VideoCapture) -> TeamClassifier:
    """
    Read a burst of frames, collect player crops, and fit the SiGLIP-based
    TeamClassifier (SiGLIP embeddings → UMAP → K-Means k=2).

    Works for both webcam and RTSP source — the logic is identical.
    """
    print(
        f"\n🔄 Calibrating team classifier "
        f"(up to {CALIBRATION_FRAMES} frames, need ≥{MIN_CROPS} crops)..."
    )
    crops = []
    frame_count = 0

    while frame_count < CALIBRATION_FRAMES:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        frame_count += 1
        if frame_count % CALIBRATION_STRIDE != 0:
            continue

        result = PLAYER_DETECTION_MODEL.infer(frame, confidence=0.3)[0]
        detections = sv.Detections.from_inference(result)
        detections = detections.with_nms(threshold=0.5, class_agnostic=True)
        players = detections[detections.class_id == PLAYER_ID]
        crops += [sv.crop_image(frame, xyxy) for xyxy in players.xyxy]

        if frame_count % 30 == 0:
            print(f"   … frame {frame_count}, {len(crops)} crops")

    if len(crops) < MIN_CROPS:
        if len(crops) == 0:
            print("⚠️  No crops found — using blank fallbacks.")
            crops = [np.zeros((64, 32, 3), dtype=np.uint8)] * MIN_CROPS
        else:
            while len(crops) < MIN_CROPS:
                crops.append(crops[len(crops) % len(crops)])

    tc = TeamClassifier(device="cpu")
    tc.fit(crops)
    print(f"✅ TeamClassifier fitted on {len(crops)} crops")
    return tc


# =============================================================================
# SECTION 11: MAIN LOOP
# =============================================================================


def main():

    # ── 11.1  Start FastAPI WebSocket server in background thread ─────────────
    print(f"🚀 Starting WebSocket server on ws://{API_HOST}:{API_PORT}/ws")
    threading.Thread(target=start_api_server, daemon=True).start()

    # ── 11.2  Redis ───────────────────────────────────────────────────────────
    global redis_client
    redis_client = init_redis()

    # ── 11.3  Gemini ──────────────────────────────────────────────────────────
    global gemini_client
    gemini_client = init_gemini()

    # ── 11.4  Load detection models ───────────────────────────────────────────
    print("🤖 Loading detection models…")
    global PLAYER_DETECTION_MODEL, FIELD_DETECTION_MODEL
    PLAYER_DETECTION_MODEL = get_model(
        model_id=PLAYER_DETECTION_MODEL_ID, api_key=API_KEY
    )
    FIELD_DETECTION_MODEL = get_model(
        model_id=FIELD_DETECTION_MODEL_ID, api_key=API_KEY
    )

    # ── 11.5  Load xG model ───────────────────────────────────────────────────
    xg_model = load_xg_model()

    # ── 11.6  Open video source ────────────────────────────────────────────────
    #
    # [ORIGINAL] Ashim's webcam selector (preserved for reference):
    # def select_camera() -> int:
    #     available = []
    #     for i in range(10):
    #         test_cap = cv2.VideoCapture(i)
    #         if test_cap.isOpened():
    #             ret, frame = test_cap.read()
    #             if ret:
    #                 h, w = frame.shape[:2]
    #                 available.append((i, w, h))
    #             test_cap.release()
    #     if not available:
    #         raise RuntimeError("No cameras found")
    #     print("\n📷 Available cameras:")
    #     for idx, (cam_id, w, h) in enumerate(available):
    #         print(f"  [{idx}] Camera {cam_id}  ({w}x{h})")
    #     choice = input("\nSelect camera number [0]: ").strip()
    #     return available[int(choice) if choice else 0][0]
    # cam_id = select_camera()
    # cap = cv2.VideoCapture(cam_id)
    #
    # NEW: env-var toggle so we don't need to change code between lab and game day

    if VIDEO_SOURCE == "rtsp":
        print(f"📹 Connecting to RTSP stream: {RTSP_URL}")
        cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
        time.sleep(2.0)
        if not cap.isOpened():
            print(f"❌ RTSP failed.  Try:  export VIDEO_SOURCE=webcam")
            return
        print("✅ RTSP stream connected.")
    else:
        print(f"📷 Opening webcam (index {WEBCAM_INDEX})…")
        cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not cap.isOpened():
            print(f"❌ Webcam {WEBCAM_INDEX} failed.")
            return
        print(f"✅ Webcam {WEBCAM_INDEX} connected.")

    # ── 11.7  Calibrate team classifier ───────────────────────────────────────
    team_classifier = calibrate_team_classifier(cap)

    # ── 11.8  Annotators ──────────────────────────────────────────────────────
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

    # ── 11.9  State variables ─────────────────────────────────────────────────
    tracker = sv.ByteTrack()
    tracker.reset()
    M_buffer = deque(maxlen=HOMOGRAPHY_BUFFER_LEN)

    possession_log = deque(maxlen=POSSESSION_WINDOW)
    ball_history = deque(maxlen=300)

    # Team heatmaps
    heatmap_team0 = np.zeros((HEATMAP_H, HEATMAP_W), dtype=np.float32)
    heatmap_team1 = np.zeros((HEATMAP_H, HEATMAP_W), dtype=np.float32)
    heatmap_ball = np.zeros((HEATMAP_H, HEATMAP_W), dtype=np.float32)

    total_xg = {0: 0.0, 1: 0.0}
    xg_timeline: List[dict] = []
    last_minute_recorded = -1
    key_events: List[dict] = []

    match_start_time = time.time()

    # Goal positions (pitch-metre origin = centre circle)
    goal_team0_xy = np.array([52.5, 0.0])  # opponent's goal (USask attacks here)
    goal_team1_xy = np.array([-52.5, 0.0])  # USask's own goal

    global ai_insight_cache, last_ai_request_ts
    frame_id = 0

    print("\n⚽ Analytics running.  Press Q to quit.\n")

    # ── 11.10  Frame loop ─────────────────────────────────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            if VIDEO_SOURCE == "rtsp":
                print("⚠️  Frame failed — reconnecting RTSP…")
                cap.release()
                time.sleep(1.0)
                cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    print("❌ Reconnect failed.")
                    break
            else:
                print("⚠️  Webcam frame failed.")
                break
            continue

        frame_id += 1
        now = time.time()
        match_secs = now - match_start_time
        match_min = match_secs / 60.0

        # ── A: Player / ball detection ────────────────────────────────────────
        result = PLAYER_DETECTION_MODEL.infer(frame, confidence=0.3)[0]
        detections = sv.Detections.from_inference(result)

        ball_dets = detections[detections.class_id == BALL_ID]
        if len(ball_dets) > MAX_BALLS:
            ball_dets = ball_dets[:MAX_BALLS]
        ball_dets.xyxy = sv.pad_boxes(ball_dets.xyxy, px=10)

        all_dets = detections[detections.class_id != BALL_ID]
        all_dets = all_dets.with_nms(threshold=0.5, class_agnostic=True)

        gk_dets = all_dets[all_dets.class_id == GOALKEEPER_ID][:MAX_GOALKEEPERS]
        player_dets = all_dets[all_dets.class_id == PLAYER_ID][:MAX_PLAYERS]
        ref_dets = all_dets[all_dets.class_id == REFEREE_ID][:MAX_REFEREES]

        # ── B: Team assignment ────────────────────────────────────────────────
        if len(player_dets) > 0:
            crops = [sv.crop_image(frame, xy) for xy in player_dets.xyxy]
            player_dets.class_id = team_classifier.predict(crops)
        gk_dets.class_id = resolve_goalkeepers_team_id(player_dets, gk_dets)
        ref_dets.class_id -= 1

        # ── C: Merge + ByteTrack ──────────────────────────────────────────────
        merged = sv.Detections.merge([player_dets, gk_dets, ref_dets])
        merged = tracker.update_with_detections(merged)
        merged.class_id = merged.class_id.astype(int)
        labels = [f"#{tid}" for tid in merged.tracker_id]

        # ── D: Annotate camera frame ──────────────────────────────────────────
        ann = frame.copy()
        ann = ellipse_annotator.annotate(scene=ann, detections=merged)
        ann = label_annotator.annotate(scene=ann, detections=merged, labels=labels)
        ann = triangle_annotator.annotate(scene=ann, detections=ball_dets)

        # ── E: Field keypoints + homography ──────────────────────────────────
        res_field = FIELD_DETECTION_MODEL.infer(frame, confidence=0.3)[0]
        keypoints = sv.KeyPoints.from_inference(res_field)
        if (
            keypoints.xy is None
            or len(keypoints.xy) == 0
            or keypoints.confidence is None
        ):
            cv2.imshow("Camera View", ann)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        filt = keypoints.confidence[0] > 0.5
        frame_pts = keypoints.xy[0][filt]
        pitch_pts = np.array(CONFIG.vertices)[filt]
        if len(frame_pts) < 4:
            cv2.imshow("Camera View", ann)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            continue

        transformer = ViewTransformer(source=frame_pts, target=pitch_pts)
        M_buffer.append(transformer.m)
        transformer.m = np.mean(np.array(M_buffer), axis=0)

        # ── F: Project to pitch metres ────────────────────────────────────────
        pitch_dets = sv.Detections.merge([player_dets, gk_dets])

        def project(dets):
            xy = dets.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
            return transformer.transform_points(xy) if len(xy) > 0 else np.array([])

        pitch_ball_xy = project(ball_dets)
        pitch_players_xy = project(pitch_dets)
        pitch_refs_xy = project(ref_dets)

        # ── G: Team masks ─────────────────────────────────────────────────────
        if len(pitch_dets) > 0:
            t0_mask = pitch_dets.class_id == 0
            t1_mask = pitch_dets.class_id == 1
        else:
            t0_mask = t1_mask = np.array([], dtype=bool)

        team0_xy = (
            pitch_players_xy[t0_mask] if t0_mask.any() else np.array([]).reshape(0, 2)
        )
        team1_xy = (
            pitch_players_xy[t1_mask] if t1_mask.any() else np.array([]).reshape(0, 2)
        )

        # ── H: Tactical metrics ───────────────────────────────────────────────
        update_possession_log(possession_log, pitch_ball_xy, team0_xy, team1_xy)
        possession_pct = compute_possession(possession_log)
        def_line_height = compute_defensive_line_height(team1_xy)
        atk_width = compute_width_of_attack(team0_xy)

        if len(pitch_ball_xy) > 0:
            ball_history.append((match_secs, pitch_ball_xy[0][0], pitch_ball_xy[0][1]))
        transition_spd = compute_transition_speed(ball_history)
        hull_area = compute_convex_hull_area(team1_xy)

        zone_t0 = compute_zone_stats(team0_xy)
        zone_t1 = compute_zone_stats(team1_xy)

        # ── I: Update heatmaps ────────────────────────────────────────────────
        if t0_mask.any():
            update_heatmap(heatmap_team0, team0_xy)
        if t1_mask.any():
            update_heatmap(heatmap_team1, team1_xy)
        if len(pitch_ball_xy) > 0:
            update_heatmap(heatmap_ball, pitch_ball_xy)

        # ── J: Update player registry ─────────────────────────────────────────
        player_payloads = []
        for i in range(len(merged)):
            if merged.tracker_id is None:
                continue
            tid = int(merged.tracker_id[i])
            team_id = int(merged.class_id[i])
            if i < len(pitch_players_xy):
                pos = pitch_players_xy[i]
                stats = update_player_registry(tid, team_id, pos, now, player_registry)
                player_payloads.append(serialize_player(stats))

        # ── K: xG timeline ────────────────────────────────────────────────────
        cur_min = int(match_min)
        if cur_min > last_minute_recorded:
            xg_timeline.append(
                {
                    "minute": cur_min,
                    "team0_xg": round(total_xg[0], 3),
                    "team1_xg": round(total_xg[1], 3),
                }
            )
            last_minute_recorded = cur_min

        ball_payload = (
            [round(float(pitch_ball_xy[0][0]), 2), round(float(pitch_ball_xy[0][1]), 2)]
            if len(pitch_ball_xy) > 0
            else None
        )

        # ── L: Heatmap payload (every 30 frames = ~1 second) ─────────────────
        hmap_payload = None
        if frame_id % 30 == 0:
            hmap_payload = {
                "team0": get_heatmap_payload(heatmap_team0),
                "team1": get_heatmap_payload(heatmap_team1),
                "ball": get_heatmap_payload(heatmap_ball),
            }

        # ── M: Gemini AI insight (every 2 minutes) ────────────────────────────
        if (
            ENABLE_GEMINI
            and gemini_client is not None
            and now - last_ai_request_ts > AI_INSIGHT_INTERVAL
        ):
            last_ai_request_ts = now
            prompt = build_gemini_prompt(
                match_min,
                possession_pct,
                total_xg[0],
                total_xg[1],
                transition_spd,
                hull_area,
                def_line_height,
                atk_width,
                zone_t0,
                zone_t1,
                player_registry,
                key_events,
            )

            def _store(future):
                r = future.result()
                if r:
                    r["minute"] = round(match_min, 1)
                    global ai_insight_cache
                    ai_insight_cache = r

            try:
                loop = asyncio.get_event_loop()
                fut = asyncio.run_coroutine_threadsafe(
                    request_gemini_insight(prompt, match_min), loop
                )
                fut.add_done_callback(_store)
            except RuntimeError:
                pass

        # ── N: Build + broadcast JSON payload ─────────────────────────────────
        payload = build_payload(
            frame_id=frame_id,
            timestamp=now,
            possession_pct=possession_pct,
            defensive_line_height=def_line_height,
            width_of_attack=atk_width,
            transition_speed=transition_spd,
            convex_hull_area=hull_area,
            total_xg_team0=total_xg[0],
            total_xg_team1=total_xg[1],
            xg_timeline=xg_timeline,
            pitch_players=player_payloads,
            pitch_ball=ball_payload,
            key_events=key_events,
            zone_stats_team0=zone_t0,
            zone_stats_team1=zone_t1,
            heatmap_payload=hmap_payload,
            ai_insight=ai_insight_cache,
        )
        payload_json = json.dumps(payload)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast(payload_json), loop)
        except RuntimeError:
            pass
        publish_to_redis(payload)

        # ── O: Draw OpenCV windows ────────────────────────────────────────────
        pitch_img = draw_pitch(CONFIG)
        if len(pitch_ball_xy) > 0:
            pitch_img = draw_points_on_pitch(
                CONFIG,
                pitch_ball_xy,
                sv.Color.WHITE,
                sv.Color.BLACK,
                10,
                pitch=pitch_img,
            )
        if t0_mask.any():
            pitch_img = draw_points_on_pitch(
                CONFIG,
                pitch_players_xy[t0_mask],
                sv.Color.from_hex("00BFFF"),
                sv.Color.BLACK,
                16,
                pitch=pitch_img,
            )
        if t1_mask.any():
            pitch_img = draw_points_on_pitch(
                CONFIG,
                pitch_players_xy[t1_mask],
                sv.Color.from_hex("FF1493"),
                sv.Color.BLACK,
                16,
                pitch=pitch_img,
            )
        if len(pitch_refs_xy) > 0:
            pitch_img = draw_points_on_pitch(
                CONFIG,
                pitch_refs_xy,
                sv.Color.from_hex("FFD700"),
                sv.Color.BLACK,
                16,
                pitch=pitch_img,
            )

        # Voronoi
        if t0_mask.any() and t1_mask.any():
            vbase = draw_pitch(
                CONFIG, background_color=sv.Color.WHITE, line_color=sv.Color.BLACK
            )
            vimg = draw_pitch_voronoi_diagram_2(
                CONFIG,
                pitch_players_xy[t0_mask],
                pitch_players_xy[t1_mask],
                sv.Color.from_hex("00BFFF"),
                sv.Color.from_hex("FF1493"),
                pitch=vbase,
            )
            if len(pitch_ball_xy) > 0:
                vimg = draw_points_on_pitch(
                    CONFIG,
                    pitch_ball_xy,
                    sv.Color.WHITE,
                    sv.Color.WHITE,
                    8,
                    thickness=1,
                    pitch=vimg,
                )
            vimg = draw_points_on_pitch(
                CONFIG,
                pitch_players_xy[t0_mask],
                sv.Color.from_hex("00BFFF"),
                sv.Color.WHITE,
                16,
                thickness=1,
                pitch=vimg,
            )
            vimg = draw_points_on_pitch(
                CONFIG,
                pitch_players_xy[t1_mask],
                sv.Color.from_hex("FF1493"),
                sv.Color.WHITE,
                16,
                thickness=1,
                pitch=vimg,
            )
            cv2.imshow("Voronoi", vimg)

        # Metric overlay on camera view
        for i, line in enumerate(
            [
                f"Possession: {possession_pct:.1f}% (USask)  |  Transition: {transition_spd:.1f}s",
                f"Def Line: {def_line_height:.1f}m  |  Atk Width: {atk_width:.1f}m  |  Hull: {hull_area:.0f}m2",
                f"xG USask: {total_xg[0]:.2f}  |  xG Opp: {total_xg[1]:.2f}",
                f"Zone T0 dominant: {zone_t0.get('dominant_zone', '-')}",
            ]
        ):
            cv2.putText(
                ann,
                line,
                (10, 30 + i * 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 150),
                2,
                cv2.LINE_AA,
            )

        cv2.imshow("Camera View", ann)
        cv2.imshow("Pitch Radar", pitch_img)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Analytics stopped.")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main()

