from types import SimpleNamespace

import numpy as np

from postgame.processing import JerseyBrightnessClassifier, RoboflowVideoProcessor, preflight_sample_timestamps


def test_preflight_timestamps_sample_each_active_period() -> None:
    periods = [
        {"number": 1, "start_ms": 1_000, "end_ms": 41_000},
        {"number": 2, "start_ms": 51_000, "end_ms": 91_000},
    ]

    timestamps = preflight_sample_timestamps(periods, duration_ms=100_000)

    assert len(timestamps) == 14
    assert all(1_000 <= timestamp <= 41_000 for timestamp in timestamps[:7])
    assert all(51_000 <= timestamp <= 91_000 for timestamp in timestamps[7:])
    assert 41_000 < timestamps[7]


def test_preflight_timestamps_fall_back_for_match_without_periods() -> None:
    timestamps = preflight_sample_timestamps([], duration_ms=100_000)

    assert timestamps == [8_000, 22_000, 36_000, 50_000, 64_000, 78_000, 92_000]


def test_jersey_brightness_classifier_separates_dark_and_light_kits() -> None:
    dark_crops = [np.full((100, 40, 3), 45 + offset, dtype=np.uint8) for offset in (0, 4, 8)]
    light_crops = [np.full((100, 40, 3), 205 + offset, dtype=np.uint8) for offset in (0, 4, 8)]
    classifier = JerseyBrightnessClassifier()

    classifier.fit(dark_crops + light_crops)

    assert classifier.predict(dark_crops).tolist() == [0, 0, 0]
    assert classifier.predict(light_crops).tolist() == [1, 1, 1]


def test_team_classifier_cache_is_versioned_json(tmp_path, monkeypatch) -> None:
    (tmp_path / "team_classifier.json").write_text(
        '{"schema_version":1,"kind":"jersey-brightness","centers":[42.0,210.0]}'
    )
    # A legacy pickle-shaped file is deliberately irrelevant to loading.
    (tmp_path / "team_classifier.pkl").write_bytes(b"not-a-trusted-cache")
    processor = RoboflowVideoProcessor()
    monkeypatch.setattr(processor, "_load_runtime", lambda: {"np": np})

    classifier = processor._classifier(SimpleNamespace(id="match-1"), tmp_path)

    np.testing.assert_allclose(classifier.centers, [42.0, 210.0])
