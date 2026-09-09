"""Stable team assignments for tracked live-player detections.

The SiGLIP team classifier is comparatively expensive. A tracked player's team
does not change during a match, so live inference only needs a few predictions
for a new ByteTrack id. This module keeps that policy independent of the CV
runtime so it can be regression-tested without loading Roboflow or torch.
"""

from dataclasses import dataclass, field


@dataclass
class TrackTeamAssigner:
    """Vote on new tracks, then lock and reuse their team assignment."""

    vote_frames: int = 5
    _votes: dict[int, list[int]] = field(default_factory=dict, init=False)
    _latest: dict[int, int] = field(default_factory=dict, init=False)
    _locked: dict[int, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.vote_frames < 1:
            raise ValueError("vote_frames must be at least 1")

    def needs_prediction(self, track_id: int) -> bool:
        """Return whether this track still needs a classifier prediction."""
        return int(track_id) not in self._locked

    def observe(self, track_id: int, predicted_team: int) -> int:
        """Record one prediction and return the current stable/provisional team."""
        track_id = int(track_id)
        predicted_team = int(predicted_team)
        if predicted_team not in (0, 1):
            raise ValueError("predicted_team must be 0 or 1")
        if track_id in self._locked:
            return self._locked[track_id]

        votes = self._votes.setdefault(track_id, [0, 0])
        votes[predicted_team] += 1
        self._latest[track_id] = predicted_team
        if sum(votes) >= self.vote_frames:
            self._locked[track_id] = self._majority(track_id)
        return self.team_for(track_id)

    def team_for(self, track_id: int) -> int:
        """Return a locked or provisional team for a previously observed track."""
        track_id = int(track_id)
        if track_id in self._locked:
            return self._locked[track_id]
        if track_id not in self._votes:
            raise KeyError(f"track {track_id} has no team predictions")
        return self._majority(track_id)

    def reset(self) -> None:
        """Forget all ids when ByteTrack resets and may reuse its id sequence."""
        self._votes.clear()
        self._latest.clear()
        self._locked.clear()

    @property
    def locked_count(self) -> int:
        return len(self._locked)

    def _majority(self, track_id: int) -> int:
        votes = self._votes[track_id]
        if votes[0] == votes[1]:
            return self._latest[track_id]
        return 0 if votes[0] > votes[1] else 1
