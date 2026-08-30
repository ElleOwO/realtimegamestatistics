from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_root: Path
    database_url: str
    analysis_hz: float = 10.0
    keypoint_hz: float = 2.0
    progress_hz: float = 2.0
    cors_origins: tuple[str, ...] = ("*",)
    mode: str = "live"
    artifact_policy: str = "compact"

    @classmethod
    def from_env(cls) -> "Settings":
        backend_root = Path(__file__).resolve().parents[1]
        data_root = Path(
            os.environ.get("RTGS_DATA_DIR", str(backend_root.parent / "data"))
        ).resolve()
        database_url = os.environ.get(
            "RTGS_DATABASE_URL", f"sqlite:///{data_root / 'rtgs.sqlite3'}"
        )
        return cls(
            data_root=data_root,
            database_url=database_url,
            analysis_hz=float(os.environ.get("ANALYSIS_HZ", "10")),
            keypoint_hz=float(os.environ.get("KEYPOINT_HZ", "2")),
            progress_hz=float(os.environ.get("PROGRESS_HZ", "2")),
            mode=os.environ.get("RTGS_MODE", "live").strip().lower(),
            artifact_policy=os.environ.get("RTGS_ARTIFACT_POLICY", "compact").strip().lower(),
            cors_origins=tuple(
                origin.strip()
                for origin in os.environ.get("RTGS_CORS_ORIGINS", "*").split(",")
                if origin.strip()
            ),
        )

    @property
    def inbox_dir(self) -> Path:
        return self.data_root / "inbox"

    @property
    def matches_dir(self) -> Path:
        return self.data_root / "matches"

    def ensure_directories(self) -> None:
        if self.mode not in {"live", "test", "replay"}:
            raise ValueError("RTGS_MODE must be live, test, or replay")
        if self.artifact_policy not in {"compact", "source", "full"}:
            raise ValueError("RTGS_ARTIFACT_POLICY must be compact, source, or full")
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.matches_dir.mkdir(parents=True, exist_ok=True)
