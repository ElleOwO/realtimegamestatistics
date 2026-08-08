from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_codec: Mapped[str | None] = mapped_column(String(64))
    source_width: Mapped[int | None] = mapped_column(Integer)
    source_height: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    fps: Mapped[float | None] = mapped_column(Float)
    proxy_path: Mapped[str | None] = mapped_column(Text)
    annotated_path: Mapped[str | None] = mapped_column(Text)
    thumbnail_paths: Mapped[list] = mapped_column(JSON, default=list)
    home_team: Mapped[str | None] = mapped_column(String(160))
    away_team: Mapped[str | None] = mapped_column(String(160))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    usask_side: Mapped[str | None] = mapped_column(String(16))
    periods: Mapped[list] = mapped_column(JSON, default=list)
    directions: Mapped[dict] = mapped_column(JSON, default=dict)
    tactical_targets: Mapped[dict] = mapped_column(JSON, default=dict)
    team_mapping: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="imported", index=True)
    setup_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    jobs: Mapped[list["AnalysisJob"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_video_ms: Mapped[int] = mapped_column(Integer, default=0)
    processing_fps: Mapped[float | None] = mapped_column(Float)
    eta_seconds: Mapped[float | None] = mapped_column(Float)
    detection_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    calibration_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    failure_code: Mapped[str | None] = mapped_column(String(80))
    failure_detail: Mapped[str | None] = mapped_column(Text)
    log_tail: Mapped[list] = mapped_column(JSON, default=list)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    match: Mapped[Match] = relationship(back_populates="jobs")


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (Index("ix_observations_match_timestamp", "match_id", "timestamp_ms"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    object_type: Mapped[str] = mapped_column(String(24))
    track_id: Mapped[int | None] = mapped_column(Integer)
    team: Mapped[str | None] = mapped_column(String(16))
    image_box: Mapped[list | None] = mapped_column(JSON)
    pitch_x_m: Mapped[float | None] = mapped_column(Float)
    pitch_y_m: Mapped[float | None] = mapped_column(Float)
    detection_confidence: Mapped[float] = mapped_column(Float)
    calibration_confidence: Mapped[float | None] = mapped_column(Float)


class MatchEvent(Base):
    __tablename__ = "match_events"
    __table_args__ = (Index("ix_events_match_timestamp", "match_id", "timestamp_ms"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    team: Mapped[str | None] = mapped_column(String(16))
    period: Mapped[int | None] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    pitch_x_m: Mapped[float | None] = mapped_column(Float)
    pitch_y_m: Mapped[float | None] = mapped_column(Float)
    possession_context: Mapped[str | None] = mapped_column(String(32))
    play_context: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    review_status: Mapped[str] = mapped_column(String(16), default="pending")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EventReview(Base):
    __tablename__ = "event_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("match_events.id"), index=True)
    previous: Mapped[dict] = mapped_column(JSON)
    updated: Mapped[dict] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TimeSeriesPoint(Base):
    __tablename__ = "time_series"
    __table_args__ = (Index("ix_series_match_metric_timestamp", "match_id", "metric", "timestamp_ms"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    metric: Mapped[str] = mapped_column(String(64))
    value: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)


class MatchSummary(Base):
    __tablename__ = "match_summaries"

    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), primary_key=True)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    provisional: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ConfidenceSample(Base):
    __tablename__ = "confidence_samples"
    __table_args__ = (Index("ix_confidence_match_timestamp", "match_id", "timestamp_ms"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(ForeignKey("matches.id"), index=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    reprojection_error_m: Mapped[float | None] = mapped_column(Float)
    visible_pitch_fraction: Mapped[float | None] = mapped_column(Float)
    detection_confidence: Mapped[float | None] = mapped_column(Float)
    calibration_confidence: Mapped[float | None] = mapped_column(Float)
    camera_cut: Mapped[bool] = mapped_column(Boolean, default=False)
