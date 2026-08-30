from types import SimpleNamespace

import numpy as np

from pitch_calibration import field_keypoint_correspondences


def test_maps_partial_reordered_keypoints_by_semantic_class_name():
    vertices = [(float(index), float(index + 100)) for index in range(32)]
    keypoints = [
        SimpleNamespace(x=10, y=20, confidence=0.9, class_id=0, class_name="01"),
        SimpleNamespace(x=30, y=40, confidence=0.2, class_id=13, class_name="15"),
        SimpleNamespace(x=50, y=60, confidence=0.8, class_id=29, class_name="32"),
        SimpleNamespace(x=70, y=80, confidence=0.7, class_id=30, class_name="14"),
    ]
    result = SimpleNamespace(
        predictions=[SimpleNamespace(keypoints=keypoints)]
    )

    frame, pitch, confidence = field_keypoint_correspondences(result, vertices)

    np.testing.assert_array_equal(frame, [[10, 20], [50, 60], [70, 80]])
    np.testing.assert_array_equal(pitch, [vertices[0], vertices[31], vertices[13]])
    np.testing.assert_allclose(confidence, [0.9, 0.8, 0.7])


def test_falls_back_to_class_ids_only_for_a_complete_landmark_set():
    vertices = [(float(index), 0.0) for index in range(4)]
    keypoints = [
        {"x": index, "y": index + 1, "confidence": 0.9, "class_id": index}
        for index in range(4)
    ]

    frame, pitch, _ = field_keypoint_correspondences(
        {"predictions": [{"keypoints": keypoints}]}, vertices
    )

    np.testing.assert_array_equal(frame, [[0, 1], [1, 2], [2, 3], [3, 4]])
    np.testing.assert_array_equal(pitch, vertices)


def test_returns_empty_arrays_when_partial_points_lack_semantic_labels():
    result = {
        "predictions": [
            {"keypoints": [{"x": 1, "y": 2, "confidence": 0.9, "class_id": 0}]}
        ]
    }

    frame, pitch, confidence = field_keypoint_correspondences(
        result, [(0.0, 0.0), (1.0, 1.0)]
    )

    assert frame.shape == (0, 2)
    assert pitch.shape == (0, 2)
    assert confidence.shape == (0,)
