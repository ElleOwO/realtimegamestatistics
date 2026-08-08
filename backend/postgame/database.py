from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import AnalysisJob, Base, utcnow


class Database:
    def __init__(self, url: str):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args, future=True)
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._configure_sqlite)
        self.Session = sessionmaker(self.engine, expire_on_commit=False, class_=Session)

    @staticmethod
    def _configure_sqlite(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    def migrate(self) -> None:
        """Apply the current schema and record its migration version.

        Production upgrades are also represented in ``alembic/``; create_all keeps
        first-run workstation setup and isolated tests dependency-free.
        """
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            if self.engine.url.get_backend_name() == "sqlite":
                columns = {row[1] for row in connection.execute(text("PRAGMA table_info(matches)"))}
                if "tactical_targets" not in columns:
                    connection.execute(text("ALTER TABLE matches ADD COLUMN tactical_targets JSON NOT NULL DEFAULT '{}'"))
            connection.execute(
                text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)")
            )
            connection.execute(text("INSERT OR IGNORE INTO schema_version(version) VALUES (2)"))

    def mark_interrupted_jobs(self) -> None:
        with self.session() as session:
            jobs = session.query(AnalysisJob).filter(
                AnalysisJob.state.in_(("preflight", "running"))
            )
            for job in jobs:
                job.state = "interrupted"
                job.finished_at = utcnow()
                job.failure_code = "process_restarted"
                job.failure_detail = "The server restarted. This analysis can be restarted from the beginning."

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
