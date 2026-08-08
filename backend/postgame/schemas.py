from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


JobState = Literal[
    "queued",
    "preflight",
    "waiting_for_setup",
    "running",
    "completed",
    "failed",
    "cancelled",
    "interrupted",
]
ReviewStatus = Literal["pending", "confirmed", "corrected", "rejected"]
MetricStatus = Literal["available", "partial", "experimental", "unavailable"]
TeamSide = Literal["home", "away"]
TeamCode = Literal["home", "away", "contested", "unknown"]


class Period(BaseModel):
    number: int = Field(ge=1, le=4)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_bounds(self) -> "Period":
        if self.end_ms <= self.start_ms:
            raise ValueError("period end_ms must be after start_ms")
        return self


class InboxFile(BaseModel):
    filename: str
    size_bytes: int
    modified_at: datetime


class ImportMatchRequest(BaseModel):
    filename: str


class MatchSetup(BaseModel):
    home_team: str = Field(min_length=1, max_length=160)
    away_team: str = Field(min_length=1, max_length=160)
    home_score: int = Field(ge=0, le=99)
    away_score: int = Field(ge=0, le=99)
    usask_side: TeamSide
    periods: list[Period] = Field(min_length=1, max_length=4)
    directions: dict[str, Literal["left", "right"]]
    tactical_targets: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_periods(self) -> "MatchSetup":
        periods = sorted(self.periods, key=lambda period: period.start_ms)
        for previous, current in zip(periods, periods[1:]):
            if current.start_ms < previous.end_ms:
                raise ValueError("period boundaries may not overlap")
        required = {str(period.number) for period in periods}
        if set(self.directions) != required:
            raise ValueError("directions must contain exactly one entry for each period")
        return self


class TeamMappingUpdate(BaseModel):
    usask_cluster: int = Field(ge=0, le=1)


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    state: JobState
    progress: float
    current_video_ms: int
    processing_fps: float | None
    eta_seconds: float | None
    detection_coverage: float
    calibration_coverage: float
    failure_code: str | None
    failure_detail: str | None
    log_tail: list[str]
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_filename: str
    source_codec: str | None
    source_width: int | None
    source_height: int | None
    duration_ms: int
    fps: float | None
    home_team: str | None
    away_team: str | None
    home_score: int | None
    away_score: int | None
    usask_side: str | None
    periods: list[dict[str, Any]]
    directions: dict[str, str]
    tactical_targets: dict[str, Any]
    team_mapping: dict[str, Any]
    thumbnail_paths: list[str]
    status: str
    setup_complete: bool
    created_at: datetime
    updated_at: datetime
    latest_job: AnalysisJobRead | None = None


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: str
    timestamp_ms: int
    object_type: str
    track_id: int | None
    team: str | None
    image_box: list[float] | None
    pitch_x_m: float | None
    pitch_y_m: float | None
    detection_confidence: float
    calibration_confidence: float | None


class MatchEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    match_id: str
    type: str
    team: str | None
    period: int | None
    timestamp_ms: int
    pitch_x_m: float | None
    pitch_y_m: float | None
    possession_context: str | None
    play_context: str | None
    confidence: float
    review_status: ReviewStatus
    details: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EventUpdate(BaseModel):
    type: str | None = None
    team: TeamSide | None = None
    timestamp_ms: int | None = Field(default=None, ge=0)
    pitch_x_m: float | None = None
    pitch_y_m: float | None = None
    play_context: Literal["open_play", "set_piece"] | None = None
    on_target: bool | None = None
    review_status: ReviewStatus
    note: str | None = Field(default=None, max_length=1000)


T = TypeVar("T")


class MetricValue(BaseModel, Generic[T]):
    value: T | None
    unit: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    sample_coverage: float = Field(ge=0.0, le=1.0)
    status: MetricStatus
    explanation: str | None = None


class MatchReport(BaseModel):
    match_id: str
    provisional: bool
    generated_at: datetime
    score: dict[str, Any]
    summary: dict[str, MetricValue[Any]]
    events: list[MatchEventRead]
    shot_map: list[dict[str, Any]]
    territorial: dict[str, MetricValue[Any]]
    transitions: dict[str, MetricValue[Any]]
    shape: dict[str, MetricValue[Any]]
    pressing: dict[str, MetricValue[Any]] | None = None
    set_pieces: dict[str, MetricValue[Any]] | None = None
    time_series: dict[str, list[dict[str, Any]]]
    quality: dict[str, MetricValue[Any]]
    diagnostics: list[str]


class PreflightResponse(BaseModel):
    match_id: str
    state: Literal["waiting_for_setup"]
    clusters: list[dict[str, Any]]


class StreamMessage(BaseModel):
    type: Literal[
        "job_status",
        "progress",
        "provisional_report",
        "review_updated",
        "report_updated",
        "completed",
        "error",
    ]
    match_id: str
    payload: dict[str, Any]
    sent_at: datetime
