from postgame.analytics import (
    EntryDetector,
    PossessionTracker,
    ShotDetector,
    classify_possession_change,
    counterattack_initiated,
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
    calculate_xg,
    shot_features,
)


PERIODS = [
    {"number": 1, "start_ms": 10_000, "end_ms": 20_000},
    {"number": 2, "start_ms": 30_000, "end_ms": 40_000},
]


def test_period_clock_excludes_breaks():
    assert match_phase(5_000, PERIODS) == "pregame"
    assert period_at(15_000, PERIODS) == 1
    assert match_clock_ms(15_000, PERIODS) == 5_000
    assert match_phase(25_000, PERIODS) == "halftime"
    assert match_clock_ms(35_000, PERIODS) == 15_000
    assert match_phase(45_000, PERIODS) == "finished"


def test_direction_normalization():
    assert normalize_longitudinal(20, "right") == 20
    assert normalize_longitudinal(20, "left") == 85


def test_possession_hysteresis_and_unknown_gap():
    tracker = PossessionTracker()
    players = {"home": [(11.0, 10.0)], "away": [(30.0, 30.0)]}
    assert tracker.update(0, (10.0, 10.0), players, True) == "unknown"
    assert tracker.update(399, (10.0, 10.0), players, True) == "unknown"
    assert tracker.update(400, (10.0, 10.0), players, True) == "home"
    changed = {"home": [(30.0, 30.0)], "away": [(10.5, 10.0)]}
    assert tracker.update(700, (10.0, 10.0), changed, True) == "home"
    assert tracker.update(1_299, (10.0, 10.0), changed, True) == "home"
    assert tracker.update(1_300, (10.0, 10.0), changed, True) == "away"
    assert tracker.update(1_700, None, changed, False) == "away"
    assert tracker.update(1_801, None, changed, False) == "unknown"


def test_possession_contested_when_distances_are_similar():
    tracker = PossessionTracker()
    assert tracker.update(
        0,
        (10, 10),
        {"home": [(9, 10)], "away": [(11.2, 10)]},
        True,
    ) == "contested"


def test_entry_crossings_are_controlled_and_debounced():
    detector = EntryDetector()
    assert detector.update(0, "home", (69, 10), "right", True) == []
    events = detector.update(100, "home", (71, 10), "right", True)
    assert [(event.kind, event.lane) for event in events] == [("final_third", "left")]
    detector.update(500, "home", (69, 10), "right", True)
    assert detector.update(1_000, "home", (71, 10), "right", True) == []
    detector.update(2_200, "home", (68, 10), "right", True)
    assert len(detector.update(2_300, "home", (71, 10), "right", True)) == 1
    detector.update(3_000, "home", (88, 34), "right", False)
    assert detector.update(3_100, "home", (90, 34), "right", False) == []


def test_turnover_and_counterattack_classification():
    change = classify_possession_change(
        1_000, "away", "home", (80, 34), {"home": "right", "away": "left"}
    )
    assert change.high_turnover
    assert change.dangerous_turnover
    assert counterattack_initiated(
        1_000,
        (30, 34),
        [(2_000, (35, 34)), (8_000, (46, 34))],
        "right",
    )
    assert not counterattack_initiated(
        1_000,
        (30, 34),
        [(12_000, (60, 34))],
        "right",
    )


def test_shot_requires_fast_consistent_goalward_motion():
    detector = ShotDetector()
    assert detector.update(0, (70, 34), "right") == (False, 0.0)
    detector.update(100, (72, 34), "right")
    detector.update(200, (74, 34), "right")
    shot, speed = detector.update(300, (76, 34), "right")
    assert shot and speed >= 14


def test_shape_metrics_require_visibility_gate():
    players = [(10, 10), (15, 20), (20, 30), (30, 15), (40, 25), (50, 35), (60, 45)]
    assert shape_metrics(players[:6], "right", 0.9) is None
    assert shape_metrics(players, "right", 0.4) is None
    metrics = shape_metrics(players, "right", 0.8, (45, 34))
    assert metrics is not None
    assert metrics["team_length_m"] == 50
    assert metrics["width_m"] == 35
    assert metrics["convex_hull_area_m2"] > 0


def test_xg_features_are_symmetric_and_use_canonical_pitch():
    right = shot_features((90, 30), "right")
    left = shot_features((15, 38), "left")
    assert right[0] == left[0]
    assert abs(right[1] - left[1]) < 1e-12
    value = calculate_xg((90, 30), "right", {"intercept": -1.8, "distance": -0.06, "angle": 1.0})
    assert 0.01 <= value <= 0.99


def test_shot_detector_retains_origin_not_detection_endpoint():
    detector = ShotDetector()
    for timestamp, point in ((0, (72, 34)), (100, (74, 34)), (200, (76, 34))):
        assert detector.update(timestamp, point, "right")[0] is False
    shot, _ = detector.update(300, (78, 34), "right")
    assert shot
    assert detector.last_origin == (72, 34)


def test_engine_emits_quality_gated_true_entries_and_reviewable_shots():
    engine = AnalyticsEngine({"intercept": -1.8, "distance": -0.06, "angle": 1.0})
    directions = {"team0": "right", "team1": "left"}

    def frame(timestamp: int, ball: tuple[float, float]) -> FrameObservation:
        players = [
            PlayerObservation("team0", (ball[0] - 1, ball[1]), 0.9, index)
            for index in range(7)
        ] + [
            PlayerObservation("team1", (90, 10 + index * 4), 0.9, 20 + index)
            for index in range(7)
        ]
        return FrameObservation(timestamp // 100 + 1, timestamp, players, ball, 0.9, 0.9, 0.8, 0.4)

    for timestamp in (0, 200, 400, 600):
        engine.update(frame(timestamp, (68, 20)), directions)
    engine.update(frame(700, (71, 20)), directions)
    assert engine.snapshot()["progression"]["teams"][0]["final_third_entries"] == 1

    for timestamp, point in ((1_000, (72, 34)), (1_100, (74, 34)), (1_200, (76, 34)), (1_300, (78, 34))):
        engine.update(frame(timestamp, point), directions)
    shots = engine.snapshot()["chance_quality"]["shots"]
    assert shots and shots[0]["location"] == [72, 34]
    assert engine.review_event(shots[0]["id"], {"status": "confirmed", "on_target": True}, directions)
    assert engine.snapshot()["chance_quality"]["teams"][0]["shots_on_target"] == 1
