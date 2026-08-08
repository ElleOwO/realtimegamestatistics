from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select

from .config import Settings
from .database import Database
from .media import (
    BROWSER_CODECS,
    atomic_import,
    enumerate_inbox,
    generate_browser_proxy,
    probe_video,
    range_video_response,
    resolve_inbox_file,
)
from .models import AnalysisJob, EventReview, Match, MatchEvent, Observation, new_id
from .processing import RoboflowVideoProcessor
from .reporting import build_report, persist_report
from .schemas import (
    AnalysisJobRead,
    EventUpdate,
    ImportMatchRequest,
    InboxFile,
    MatchEventRead,
    MatchRead,
    MatchReport,
    MatchSetup,
    ObservationRead,
    PreflightResponse,
    TeamMappingUpdate,
)
from .streaming import MatchEventBus
from .worker import AnalysisProcessor, AnalysisWorker


def _latest_job(session, match_id: str) -> AnalysisJob | None:
    return session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.match_id == match_id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )


def _match_read(session, match: Match) -> MatchRead:
    result = MatchRead.model_validate(match)
    result.latest_job = AnalysisJobRead.model_validate(job) if (job := _latest_job(session, match.id)) else None
    return result


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    processor: AnalysisProcessor | None = None,
    start_worker: bool = True,
) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    database = database or Database(settings.database_url)
    database.migrate()
    bus = MatchEventBus()
    processor = processor or RoboflowVideoProcessor(settings.analysis_hz, settings.keypoint_hz)
    worker = AnalysisWorker(database, processor, bus, settings.matches_dir)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        bus.bind(asyncio.get_running_loop())
        database.mark_interrupted_jobs()
        if start_worker:
            worker.start()
        yield
        if start_worker:
            worker.stop()

    app = FastAPI(title="RTGS Post-Game API", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.worker = worker
    app.state.bus = bus
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=settings.cors_origins != ("*",),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "postgame"}

    @app.get("/api/v1/inbox", response_model=list[InboxFile])
    def list_inbox() -> list[InboxFile]:
        return [
            InboxFile(
                filename=path.name,
                size_bytes=path.stat().st_size,
                modified_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
            )
            for path in enumerate_inbox(settings.inbox_dir)
        ]

    @app.post("/api/v1/matches/import", response_model=MatchRead, status_code=201)
    def import_match(body: ImportMatchRequest) -> MatchRead:
        source = resolve_inbox_file(settings.inbox_dir, body.filename)
        try:
            metadata = probe_video(source)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        match_id = new_id()
        match_dir = settings.matches_dir / match_id
        destination = atomic_import(source, match_dir)
        proxy_path: str | None = None
        try:
            if metadata.codec not in BROWSER_CODECS:
                proxy = match_dir / "source-browser.mp4"
                generate_browser_proxy(destination, proxy)
                proxy_path = str(proxy)
            match = Match(
                id=match_id,
                source_filename=body.filename,
                source_path=str(destination),
                source_codec=metadata.codec,
                source_width=metadata.width,
                source_height=metadata.height,
                duration_ms=metadata.duration_ms,
                fps=metadata.fps,
                proxy_path=proxy_path,
            )
            with database.session() as session:
                session.add(match)
                session.flush()
                return _match_read(session, match)
        except Exception:
            # Keep the source in its managed match directory for diagnosis; never
            # silently move an imported match back over a newer inbox filename.
            raise

    @app.get("/api/v1/matches", response_model=list[MatchRead])
    def list_matches() -> list[MatchRead]:
        with database.session() as session:
            matches = list(session.scalars(select(Match).order_by(Match.created_at.desc())))
            return [_match_read(session, match) for match in matches]

    @app.get("/api/v1/matches/{match_id}", response_model=MatchRead)
    def get_match(match_id: str) -> MatchRead:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            return _match_read(session, match)

    @app.patch("/api/v1/matches/{match_id}/setup", response_model=MatchRead)
    def update_setup(match_id: str, body: MatchSetup) -> MatchRead:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            if any(period.end_ms > match.duration_ms for period in body.periods):
                raise HTTPException(status_code=422, detail="Period boundaries exceed video duration")
            for field, value in body.model_dump(mode="json").items():
                setattr(match, field, value)
            match.setup_complete = True
            match.status = "setup"
            session.flush()
            return _match_read(session, match)

    @app.post("/api/v1/matches/{match_id}/preflight", response_model=PreflightResponse)
    async def preflight(match_id: str) -> PreflightResponse:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            if not match.setup_complete:
                raise HTTPException(status_code=409, detail="Complete match setup before preflight")
        try:
            clusters = await asyncio.to_thread(processor.preflight, match, settings.matches_dir / match_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with database.session() as session:
            current = session.get(Match, match_id)
            current.thumbnail_paths = [cluster["preview_url"] for cluster in clusters]
            current.status = "waiting_for_setup"
        return PreflightResponse(match_id=match_id, state="waiting_for_setup", clusters=clusters)

    @app.get("/api/v1/matches/{match_id}/preflight/{filename}")
    def preflight_image(match_id: str, filename: str) -> FileResponse:
        if filename not in ("cluster-0.jpg", "cluster-1.jpg"):
            raise HTTPException(status_code=404, detail="Preview not found")
        path = settings.matches_dir / match_id / "preflight" / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Preview not found")
        return FileResponse(path)

    @app.patch("/api/v1/matches/{match_id}/team-mapping", response_model=MatchRead)
    def update_team_mapping(match_id: str, body: TeamMappingUpdate) -> MatchRead:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            if not match.thumbnail_paths:
                raise HTTPException(status_code=409, detail="Run preflight before choosing a team cluster")
            match.team_mapping = {"usask_cluster": body.usask_cluster, "opponent_cluster": 1 - body.usask_cluster}
            match.status = "ready"
            session.flush()
            return _match_read(session, match)

    @app.post("/api/v1/matches/{match_id}/analysis", response_model=AnalysisJobRead, status_code=202)
    def start_analysis(match_id: str) -> AnalysisJobRead:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            if not match.setup_complete or "usask_cluster" not in match.team_mapping:
                raise HTTPException(status_code=409, detail="Complete setup, preflight, and team mapping first")
            existing = session.scalar(
                select(AnalysisJob).where(
                    AnalysisJob.match_id == match_id,
                    AnalysisJob.state.in_(("queued", "running", "preflight")),
                )
            )
            if existing:
                raise HTTPException(status_code=409, detail="This match already has an active analysis job")
            job = AnalysisJob(match_id=match_id, state="queued")
            session.add(job)
            match.status = "queued"
            session.flush()
            response = AnalysisJobRead.model_validate(job)
        worker.enqueue(job.id)
        bus.publish(match_id, "job_status", {"job_id": job.id, "state": "queued"})
        return response

    @app.post("/api/v1/matches/{match_id}/cancel", response_model=AnalysisJobRead)
    def cancel_analysis(match_id: str) -> AnalysisJobRead:
        with database.session() as session:
            job = session.scalar(
                select(AnalysisJob)
                .where(AnalysisJob.match_id == match_id, AnalysisJob.state.in_(("queued", "running")))
                .order_by(AnalysisJob.created_at.desc())
            )
            if job is None:
                raise HTTPException(status_code=409, detail="No cancellable analysis job")
            job.cancel_requested = True
            if job.state == "queued":
                job.state = "cancelled"
                job.finished_at = datetime.now(timezone.utc)
            session.flush()
            return AnalysisJobRead.model_validate(job)

    @app.get("/api/v1/matches/{match_id}/report", response_model=MatchReport)
    def get_report(match_id: str) -> MatchReport:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            return build_report(session, match, provisional=match.status != "completed")

    @app.get("/api/v1/matches/{match_id}/events", response_model=list[MatchEventRead])
    def list_events(match_id: str) -> list[MatchEventRead]:
        with database.session() as session:
            if session.get(Match, match_id) is None:
                raise HTTPException(status_code=404, detail="Match not found")
            events = session.scalars(
                select(MatchEvent).where(MatchEvent.match_id == match_id).order_by(MatchEvent.timestamp_ms)
            )
            return [MatchEventRead.model_validate(event) for event in events]

    @app.post("/api/v1/matches/{match_id}/events", response_model=MatchEventRead, status_code=201)
    def add_event(match_id: str, body: EventUpdate) -> MatchEventRead:
        if body.type is None or body.timestamp_ms is None:
            raise HTTPException(status_code=422, detail="Manual events require type and timestamp_ms")
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            event = MatchEvent(
                match_id=match_id, type=body.type, team=body.team,
                timestamp_ms=body.timestamp_ms, pitch_x_m=body.pitch_x_m,
                pitch_y_m=body.pitch_y_m, play_context=body.play_context,
                review_status=body.review_status, confidence=1.0,
                details={"manual": True},
            )
            session.add(event)
            persist_report(session, match, provisional=match.status != "completed")
            session.flush()
            result = MatchEventRead.model_validate(event)
        bus.publish(match_id, "report_updated", {"reason": "manual_event", "event": result.model_dump(mode="json")})
        return result

    @app.patch("/api/v1/matches/{match_id}/events/{event_id}", response_model=MatchEventRead)
    def update_event(match_id: str, event_id: str, body: EventUpdate) -> MatchEventRead:
        with database.session() as session:
            match = session.get(Match, match_id)
            event = session.get(MatchEvent, event_id)
            if match is None or event is None or event.match_id != match_id:
                raise HTTPException(status_code=404, detail="Event not found")
            previous = MatchEventRead.model_validate(event).model_dump(mode="json")
            updates = body.model_dump(exclude_none=True, exclude={"note", "on_target"})
            for field, value in updates.items():
                setattr(event, field, value)
            if body.on_target is not None:
                event.details = {**event.details, "on_target": body.on_target}
            session.flush()
            updated = MatchEventRead.model_validate(event).model_dump(mode="json")
            session.add(EventReview(event_id=event.id, previous=previous, updated=updated, note=body.note))
            persist_report(session, match, provisional=match.status != "completed")
            result = MatchEventRead.model_validate(event)
        bus.publish(match_id, "review_updated", {"event": result.model_dump(mode="json")})
        bus.publish(match_id, "report_updated", {"reason": "event_review", "event_id": event_id})
        return result

    @app.get("/api/v1/matches/{match_id}/observations", response_model=list[ObservationRead])
    def list_observations(
        match_id: str,
        from_ms: int = Query(0, ge=0),
        to_ms: int | None = Query(None, ge=0),
    ) -> list[ObservationRead]:
        if to_ms is not None and to_ms < from_ms:
            raise HTTPException(status_code=422, detail="to_ms must be greater than from_ms")
        with database.session() as session:
            query = select(Observation).where(
                Observation.match_id == match_id, Observation.timestamp_ms >= from_ms
            )
            if to_ms is not None:
                query = query.where(Observation.timestamp_ms <= to_ms)
            rows = session.scalars(query.order_by(Observation.timestamp_ms).limit(20_000))
            return [ObservationRead.model_validate(row) for row in rows]

    @app.get("/api/v1/matches/{match_id}/video/{kind}")
    def get_video(match_id: str, kind: str, request: Request):
        if kind not in ("source", "annotated"):
            raise HTTPException(status_code=404, detail="Unknown video kind")
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise HTTPException(status_code=404, detail="Match not found")
            if kind == "source":
                path = Path(match.proxy_path or match.source_path)
            else:
                path = Path(match.annotated_path) if match.annotated_path else settings.matches_dir / match_id / "annotated.mp4"
        return range_video_response(path, request)

    @app.websocket("/api/v1/matches/{match_id}/stream")
    async def match_stream(websocket: WebSocket, match_id: str) -> None:
        with database.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                await websocket.close(code=4404)
                return
            job = _latest_job(session, match_id)
            initial = {
                "type": "job_status", "match_id": match_id,
                "payload": AnalysisJobRead.model_validate(job).model_dump(mode="json") if job else {"state": match.status},
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        await websocket.accept()
        await websocket.send_json(initial)
        queue = bus.subscribe(match_id)
        try:
            while True:
                await websocket.send_json(await queue.get())
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            bus.unsubscribe(match_id, queue)

    @app.websocket("/ws")
    async def legacy_live_stream(websocket: WebSocket) -> None:
        """Retained for the live pipeline; the post-game server sends no fake frames."""
        await websocket.accept()
        try:
            await websocket.send_json({"type": "backend_state", "state": "postgame_only", "data": None})
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass

    return app
