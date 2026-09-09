import pytest

from team_tracking import TrackTeamAssigner


def test_track_team_assignment_votes_then_locks():
    assigner = TrackTeamAssigner(vote_frames=5)

    assert assigner.observe(17, 1) == 1
    assert assigner.observe(17, 0) == 0
    assert assigner.observe(17, 1) == 1
    assert assigner.observe(17, 1) == 1
    assert assigner.needs_prediction(17)

    assert assigner.observe(17, 0) == 1
    assert not assigner.needs_prediction(17)
    assert assigner.locked_count == 1

    # A locked track ignores later classifier noise.
    assert assigner.observe(17, 0) == 1
    assert assigner.team_for(17) == 1


def test_provisional_tie_uses_latest_prediction_instead_of_team_zero_bias():
    assigner = TrackTeamAssigner(vote_frames=5)

    assigner.observe(4, 0)
    assert assigner.observe(4, 1) == 1


def test_reset_forgets_ids_before_tracker_id_reuse():
    assigner = TrackTeamAssigner(vote_frames=1)
    assigner.observe(1, 0)

    assigner.reset()

    assert assigner.needs_prediction(1)
    assert assigner.observe(1, 1) == 1


def test_invalid_configuration_and_predictions_are_rejected():
    with pytest.raises(ValueError):
        TrackTeamAssigner(vote_frames=0)

    assigner = TrackTeamAssigner()
    with pytest.raises(ValueError):
        assigner.observe(1, 2)
    with pytest.raises(KeyError):
        assigner.team_for(99)
