from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from sqlalchemy import select

from .database import Database
from .models import AnalysisJob, ConfidenceSample, Match, MatchEvent, Observation, TimeSeriesPoint
from .reporting import persist_report
from .streaming import MatchEventBus


@dataclass
class AnalysisBatch:
    timestamp_ms: int
    observations: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    time_series: list[dict[str, Any]] = field(default_factory=list)
    confidence: dict[str, Any] | None = None
    detection_coverage: float = 0.0
    calibration_coverage: float = 0.0
    log: str | None = None


class AnalysisProcessor(Protocol):
    def preflight(self, match: Match, match_dir: Path) -> list[dict[str, Any]]: ...

    def process(
        self,
        match: Match,
        match_dir: Path,
        emit: Callable[[AnalysisBatch], None],
        cancelled: Callable[[], bool],
    ) -> None: ...


class AnalysisWorker:
    """One durable queue consumer: exactly one analysis can use the GPU."""

    def __init__(self, database: Database, processor: AnalysisProcessor, bus: MatchEventBus, matches_dir: Path):
        self.database = database
        self.processor = processor
        self.bus = bus
        self.matches_dir = matches_dir
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stopping.clear()
        with self.database.session() as session:
            queued_ids = list(
                session.scalars(
                    select(AnalysisJob.id)
                    .where(AnalysisJob.state == "queued")
                    .order_by(AnalysisJob.created_at)
                )
            )
        for job_id in queued_ids:
            self._queue.put(job_id)
        self._thread = threading.Thread(target=self._run, name="postgame-gpu-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stopping.set()
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def _run(self) -> None:
        while not self._stopping.is_set():
            job_id = self._queue.get()
            if job_id is None:
                return
            try:
                self._process_job(job_id)
            except Exception as exc:
                with self.database.session() as session:
                    job = session.get(AnalysisJob, job_id)
                    if job:
                        job.state = "failed"
                        job.failure_code = type(exc).__name__
                        job.failure_detail = str(exc)
                        job.finished_at = datetime.now(timezone.utc)
                        match_id = job.match_id
                    else:
                        match_id = ""
                if match_id:
                    self.bus.publish(match_id, "error", {"job_id": job_id, "detail": str(exc)})

    def _process_job(self, job_id: str) -> None:
        with self.database.session() as session:
            job = session.get(AnalysisJob, job_id)
            if job is None or job.state != "queued":
                return
            match = session.get(Match, job.match_id)
            if match is None:
                raise RuntimeError("Match was removed before analysis started")
            if not match.setup_complete or "usask_cluster" not in match.team_mapping:
                job.state = "waiting_for_setup"
                return
            job.state = "running"
            job.started_at = datetime.now(timezone.utc)
            job.failure_code = None
            job.failure_detail = None
            match.status = "running"
            match_id = match.id
            duration_ms = match.duration_ms
        self.bus.publish(match_id, "job_status", {"job_id": job_id, "state": "running"})
        started = time.monotonic()
        last_report_at = -10_000
        last_broadcast_at = -10_000

        def is_cancelled() -> bool:
            if self._stopping.is_set():
                return True
            with self.database.session() as session:
                current = session.get(AnalysisJob, job_id)
                return current is None or current.cancel_requested

        def emit(batch: AnalysisBatch) -> None:
            nonlocal last_report_at, last_broadcast_at
            with self.database.session() as session:
                current_job = session.get(AnalysisJob, job_id)
                current_match = session.get(Match, match_id)
                if current_job is None or current_match is None:
                    return
                for item in batch.observations:
                    session.add(Observation(match_id=match_id, timestamp_ms=batch.timestamp_ms, **item))
                for item in batch.events:
                    session.add(MatchEvent(match_id=match_id, timestamp_ms=batch.timestamp_ms, **item))
                for item in batch.time_series:
                    session.add(TimeSeriesPoint(match_id=match_id, timestamp_ms=batch.timestamp_ms, **item))
                if batch.confidence is not None:
                    session.add(ConfidenceSample(match_id=match_id, timestamp_ms=batch.timestamp_ms, **batch.confidence))
                elapsed = max(time.monotonic() - started, 0.001)
                current_job.current_video_ms = batch.timestamp_ms
                current_job.progress = min(batch.timestamp_ms / max(duration_ms, 1), 1.0)
                current_job.processing_fps = (batch.timestamp_ms / 1000 * 10) / elapsed
                video_rate = (batch.timestamp_ms / 1000) / elapsed
                current_job.eta_seconds = max((duration_ms - batch.timestamp_ms) / 1000 / max(video_rate, 0.001), 0)
                current_job.detection_coverage = batch.detection_coverage
                current_job.calibration_coverage = batch.calibration_coverage
                if batch.log:
                    current_job.log_tail = (current_job.log_tail + [batch.log])[-30:]
                progress_payload = {
                    "job_id": job_id,
                    "state": current_job.state,
                    "progress": current_job.progress,
                    "current_video_ms": current_job.current_video_ms,
                    "processing_fps": current_job.processing_fps,
                    "eta_seconds": current_job.eta_seconds,
                    "detection_coverage": current_job.detection_coverage,
                    "calibration_coverage": current_job.calibration_coverage,
                    "log": batch.log,
                }
                if batch.timestamp_ms - last_report_at >= 5000:
                    report_payload = persist_report(session, current_match, provisional=True).model_dump(mode="json")
                    last_report_at = batch.timestamp_ms
                else:
                    report_payload = None
            if batch.timestamp_ms - last_broadcast_at >= 500:
                self.bus.publish(match_id, "progress", progress_payload)
                last_broadcast_at = batch.timestamp_ms
            if report_payload:
                self.bus.publish(match_id, "provisional_report", report_payload)

        with self.database.session() as session:
            match = session.get(Match, match_id)
        if match is None:
            return
        self.processor.process(match, self.matches_dir / match_id, emit, is_cancelled)

        with self.database.session() as session:
            job = session.get(AnalysisJob, job_id)
            match = session.get(Match, match_id)
            if job is None or match is None:
                return
            if job.cancel_requested or self._stopping.is_set():
                job.state = "cancelled" if job.cancel_requested else "interrupted"
                match.status = job.state
                report = persist_report(session, match, provisional=True)
                message_type = "job_status"
            else:
                job.state = "completed"
                job.progress = 1.0
                job.current_video_ms = match.duration_ms
                match.status = "completed"
                annotated_path = self.matches_dir / match_id / "annotated.mp4"
                match.annotated_path = str(annotated_path) if annotated_path.is_file() else None
                report = persist_report(session, match, provisional=False)
                message_type = "completed"
            job.finished_at = datetime.now(timezone.utc)
            payload = {"job_id": job.id, "state": job.state, "report": report.model_dump(mode="json")}
        self.bus.publish(match_id, message_type, payload)
