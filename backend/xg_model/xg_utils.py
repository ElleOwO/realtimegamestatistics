"""Expected goals helpers for the backend analytics engine."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import xgboost as xgb

from ..constants import XG_MODEL_PATH


def load_xg_model() -> Optional[xgb.Booster]:
    """Load the trained xGBoost model from disk if available."""
    if os.path.exists(XG_MODEL_PATH):
        model = xgb.Booster()
        model.load_model(XG_MODEL_PATH)
        print(f"✅ xG model loaded from {XG_MODEL_PATH}")
        return model
    print(f"⚠️  xG model not found at '{XG_MODEL_PATH}' — using formula fallback.")
    print("   Train the model in backend/training_notebooks/football_ai.ipynb and set XG_MODEL_PATH.")
    return None


def compute_xg(
    shot_xy: np.ndarray,
    goal_xy: np.ndarray,
    under_pressure: bool = False,
    is_header: bool = False,
    xg_model: Optional[xgb.Booster] = None,
) -> float:
    """Compute shot probability using the trained model or a fallback formula."""
    dx = goal_xy[0] - shot_xy[0]
    dy = goal_xy[1] - shot_xy[1]
    distance_m = float(max(np.hypot(dx, dy), 0.5))

    goal_half_width = 3.66
    angle_rad = np.arctan2(
        goal_half_width * distance_m,
        distance_m ** 2 + goal_half_width ** 2,
    )
    angle_deg = float(np.degrees(angle_rad))

    if xg_model is not None:
        features = np.array([[distance_m, angle_deg, int(distance_m < 16.5), int(under_pressure), int(is_header), 0, 0, 0.0]], dtype=np.float32)
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

    base_xg = (angle_deg / 90.0) * np.exp(-distance_m / 16.0)
    if under_pressure:
        base_xg *= 0.72
    if is_header:
        base_xg *= 0.62
    return float(np.clip(base_xg, 0.0, 1.0))
