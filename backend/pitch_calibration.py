from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def field_keypoint_correspondences(
    inference_result: Any,
    pitch_vertices: Sequence[Sequence[float]],
    confidence_threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map detected field landmarks to their semantic pitch vertices.

    Roboflow may omit low-confidence landmark classes from a keypoint response.
    The remaining points therefore cannot be matched to the full pitch vertex
    array with a positional boolean mask. Numeric class names (``01`` through
    ``32`` for the current field model) retain the original landmark identity.
    """
    predictions = _field(inference_result, "predictions", ()) or ()
    raw_keypoints = _field(predictions[0], "keypoints", ()) if predictions else ()
    vertices = np.asarray(pitch_vertices, dtype=np.float32)
    frame_points: list[tuple[float, float]] = []
    matched_vertices: list[np.ndarray] = []
    confidences: list[float] = []
    used_vertices: set[int] = set()

    for position, keypoint in enumerate(raw_keypoints):
        vertex_index: int | None = None
        class_name = str(_field(keypoint, "class_name", "")).strip()
        if class_name:
            try:
                candidate = int(class_name) - 1
            except ValueError:
                candidate = -1
            if 0 <= candidate < len(vertices):
                vertex_index = candidate

        # Some inference adapters do not expose semantic class names. A
        # positional/class-id fallback is safe only when no landmarks vanished.
        if vertex_index is None and len(raw_keypoints) == len(vertices):
            class_id = _field(keypoint, "class_id")
            try:
                candidate = int(class_id)
            except (TypeError, ValueError):
                candidate = position
            if 0 <= candidate < len(vertices):
                vertex_index = candidate

        try:
            x = float(_field(keypoint, "x"))
            y = float(_field(keypoint, "y"))
            confidence = float(_field(keypoint, "confidence"))
        except (TypeError, ValueError):
            continue
        if (
            vertex_index is None
            or vertex_index in used_vertices
            or confidence <= confidence_threshold
            or not np.isfinite((x, y, confidence)).all()
        ):
            continue

        used_vertices.add(vertex_index)
        frame_points.append((x, y))
        matched_vertices.append(vertices[vertex_index])
        confidences.append(confidence)

    return (
        np.asarray(frame_points, dtype=np.float32).reshape(-1, 2),
        np.asarray(matched_vertices, dtype=np.float32).reshape(-1, 2),
        np.asarray(confidences, dtype=np.float32),
    )
