from live_state import LiveMatchController


def test_backend_match_state_controls_phase_direction_and_reset(tmp_path, monkeypatch):
    monkeypatch.setenv("RTGS_DATA_DIR", str(tmp_path))
    controller = LiveMatchController()
    ok, error, reset = controller.apply({"type": "match.set_phase", "payload": {"phase": "first_half"}})
    assert ok and error is None and not reset
    assert controller.snapshot()["clock_running"]
    assert controller.directions() == {"team0": "right", "team1": "left"}

    controller.apply({"type": "match.set_score", "payload": {"score": [2, 1]}})
    controller.apply({"type": "match.set_clock", "payload": {"clock_s": 123.5}})
    state = controller.snapshot()
    assert state["score"] == [2, 1]
    assert state["clock_s"] >= 123.5

    ok, _, reset = controller.apply({"type": "match.reset"})
    assert ok and reset
    state = controller.snapshot()
    assert state["phase"] == "pregame"
    assert state["score"] == [0, 0]


def test_tactical_target_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("RTGS_DATA_DIR", str(tmp_path))
    controller = LiveMatchController()
    ok, error, _ = controller.apply({
        "type": "match.set_targets",
        "payload": {"tactical_targets": {"team0": {"out_of_possession": {"team_length_m": {"min": 35, "max": 30}}}}},
    })
    assert not ok
    assert "minimum" in str(error)
