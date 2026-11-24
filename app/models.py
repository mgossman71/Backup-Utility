"""Dataclass models mirroring the SQLite schema.

These are lightweight transport objects; the repositories build them from
``sqlite3.Row`` instances and accept them on write paths.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    name: str
    source_path: str
    dest_root: str
    dest_name_override: str | None = None
    enabled: bool = True
    schedule_cron: str | None = None
    timezone: str = "America/Chicago"
    delete_mode: bool = False
    checksum_mode: bool = False
    metadata_mode: bool = True
    exclusions: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Job":
        return cls(
            id=row["id"],
            name=row["name"],
            source_path=row["source_path"],
            dest_root=row["dest_root"],
            dest_name_override=row["dest_name_override"],
            enabled=bool(row["enabled"]),
            schedule_cron=row["schedule_cron"],
            timezone=row["timezone"],
            delete_mode=bool(row["delete_mode"]),
            checksum_mode=bool(row["checksum_mode"]),
            metadata_mode=bool(row["metadata_mode"]),
            exclusions=json.loads(row["exclusions_json"] or "[]"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def dest_path(self) -> str:
        """Effective destination path for a run (root + optional override)."""
        import posixpath

        if self.dest_name_override:
            return posixpath.join(self.dest_root, self.dest_name_override)
        return posixpath.join(self.dest_root, posixpath.basename(self.source_path.rstrip("/")) or "backup")


@dataclass
class Run:
    id: str
    job_id: str | None
    operation: str
    source_path: str
    destination_path: str
    status: str
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    message: str | None = None
    stats: dict = field(default_factory=dict)
    log_path: str | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Run":
        return cls(
            id=row["id"],
            job_id=row["job_id"],
            operation=row["operation"],
            source_path=row["source_path"],
            destination_path=row["destination_path"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            exit_code=row["exit_code"],
            message=row["message"],
            stats=json.loads(row["stats_json"] or "{}"),
            log_path=row["log_path"],
        )

    @property
    def duration_seconds(self) -> float | None:
        if not self.finished_at:
            return None
        from datetime import datetime as _dt

        start = _dt.fromisoformat(self.started_at)
        end = _dt.fromisoformat(self.finished_at)
        return (end - start).total_seconds()
