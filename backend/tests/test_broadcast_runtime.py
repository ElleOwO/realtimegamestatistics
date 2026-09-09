import gzip
import json
from dataclasses import replace

import pytest

from analytics_core import AnalyticsEngine, FrameObservation, PlayerObservation
from broadcast_runtime import BroadcastRuntime
from broadcast_source import BroadcastSource, SourceFrame, SourceTimeline
from canadawest import validate_event_url


COEFFS = {"intercept": .6, "distance": -.18, "angle": 3.0}


def frame(at, x=50):
    return FrameObservation(at, at, [PlayerObservation("team0", (x, 34), .9)], (x, 34), .9, .9, .7)


def enable(runtime):
    runtime.command({"type": "analysis.confirm_teams", "payload": {"usask_cluster": 0}})
    runtime.command({"type": "analysis.set_enabled", "payload": {"enabled": True}})
    runtime.command({"type": "match.set_phase", "payload": {"phase": "first_half"}})


def test_clock_and_recovery_follow_video_not_wall_time(tmp_path):
    runtime = BroadcastRuntime(tmp_path, "one", COEFFS)
    enable(runtime)
    for at in range(100, 2100, 100):
        runtime.frame(frame(at))
    assert runtime.controller.snapshot()["clock_s"] == 2
    expected = runtime.snapshot()
    runtime.close()
    restored = BroadcastRuntime(tmp_path, "one", COEFFS)
    assert restored.snapshot() == expected
    assert restored.controller.snapshot()["clock_s"] == 2
    assert restored.enabled
    restored.close()
    gzip.decompress((tmp_path / "observations.jsonl.gz").read_bytes())


def test_exclusion_rebuilds_entries_and_survives_restart(tmp_path):
    runtime = BroadcastRuntime(tmp_path, "one", COEFFS)
    enable(runtime)
    for at in range(100, 1500, 100):
        runtime.frame(frame(at, 69 if at < 1000 else 72))
    assert runtime.snapshot()["progression"]["teams"][0]["final_third_entries"] == 1
    runtime.command({"type": "analysis.exclude_interval", "payload": {"start_ms": 900, "end_ms": 1200}})
    assert runtime.snapshot()["progression"]["teams"][0]["final_third_entries"] == 0
    runtime.close()
    recovered = BroadcastRuntime(tmp_path, "one", COEFFS)
    assert recovered.snapshot()["progression"]["teams"][0]["final_third_entries"] == 0
    recovered.close()


def test_paused_and_gap_observations_do_not_bridge_events(tmp_path):
    runtime = BroadcastRuntime(tmp_path, "one", COEFFS)
    enable(runtime)
    for at in range(100, 900, 100):
        runtime.frame(frame(at, 69))
    runtime.command({"type": "analysis.set_enabled", "payload": {"enabled": False}})
    runtime.frame(frame(1000, 75))
    runtime.command({"type": "analysis.set_enabled", "payload": {"enabled": True}})
    runtime.frame(frame(20000, 95), gap=True)
    assert runtime.snapshot()["progression"]["teams"][0]["final_third_entries"] == 0
    assert runtime.snapshot()["quality_coverage"] < .1
    runtime.close()


def test_rejected_command_is_not_journaled(tmp_path):
    runtime = BroadcastRuntime(tmp_path, "one", COEFFS)
    with pytest.raises(ValueError):
        runtime.command({"type": "analysis.set_enabled", "payload": {"enabled": True}})
    assert runtime.records == []
    runtime.close()


def test_deterministic_event_ids_and_gap_reset():
    first, second = AnalyticsEngine(COEFFS, event_namespace="one"), AnalyticsEngine(COEFFS, event_namespace="one")
    first._event("shot", 200, "team0", (80, 34))
    second._event("shot", 200, "team0", (80, 34))
    assert first.events[0]["id"] == second.events[0]["id"]
    first.discontinuity()
    assert len(first.events) == 1


def test_url_validation_rejects_credentials_and_other_hosts():
    assert validate_event_url("https://canadawest.tv/events/123")
    for url in ("http://canadawest.tv/game", "https://canadawest.tv.evil.test/game", "https://name:secret@canadawest.tv", "https://127.0.0.1/game"):
        with pytest.raises(ValueError):
            validate_event_url(url)


def test_bounded_capture_and_timestamp_duplicates():
    source = BroadcastSource(None)
    source.put(SourceFrame(None, 1, 1, True))
    source.put(SourceFrame(None, 2, 2))
    assert source.dropped == 1
    assert source.read().discontinuity
    timeline = SourceTimeline()
    assert timeline.map(1000) == 0
    assert timeline.map(1100) == 100
    assert timeline.map(1050) is None
    assert timeline.map(1200) == 200


def test_export_replays_source_commands_exclusions_and_gaps(tmp_path):
    from observation_io import read_recording
    from broadcast_replay import BroadcastReplayRuntime
    runtime = BroadcastRuntime(tmp_path, "roundtrip", COEFFS)
    enable(runtime)
    for at in range(100, 1500, 100):
        runtime.frame(frame(at, 69 if at < 1000 else 72), gap=at == 500)
    runtime.command({"type": "analysis.exclude_interval", "source_timestamp_ms": 1300,
                     "payload": {"start_ms": 900, "end_ms": 1200}})
    runtime.export()
    recording = read_recording(tmp_path / "observations.jsonl.gz")
    replay = BroadcastReplayRuntime(recording)
    # Use identical coefficients, independent of the project's trained file.
    replay.broadcast.coeffs = COEFFS
    replay.broadcast._rebuild()
    for item in recording.items:
        replay.step(item)
    assert replay.broadcast.snapshot() == runtime.snapshot()
    assert replay.broadcast.controller.snapshot() == runtime.controller.snapshot()
    replay.stop()
    runtime.close()
