"""Central configuration for the soccer analytics backend.

This mirrors the reference repos' constants modules so runtime settings stay
discoverable and easy to migrate into smaller modules later.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# API keys and model identifiers
ROBOFLOW_API_KEY = os.environ.get("ROBOFLOW_API_KEY")
PLAYER_MODEL_ID = os.environ.get("PLAYER_MODEL_ID", "spen-rtgs-oc4ez/4")
FIELD_MODEL_ID = os.environ.get("FIELD_MODEL_ID", "football-field-detection-f07vi/14")
XG_MODEL_PATH = os.environ.get("XG_MODEL_PATH", "xg_model_womens.ubj")

# Runtime settings
VIDEO_SOURCE = os.environ.get("VIDEO_SOURCE", "webcam").lower()
WEBCAM_INDEX = int(os.environ.get("WEBCAM_INDEX", "0"))
RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/live")
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))

# GCP / Gemini
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-project-id")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
ENABLE_GEMINI = os.environ.get("ENABLE_GEMINI", "false").strip().lower() in {"1", "true", "yes", "on"}

# Tracking and analytics defaults
POSSESSION_WINDOW = 150
FRAME_DT = 1 / 30
SPRINT_THRESHOLD_MS = 5.5
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0
PITCH_HALF_LENGTH = 52.5
PITCH_HALF_WIDTH = 34.0
