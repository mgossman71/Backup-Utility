"""Data-access functions for jobs and runs.

All functions open their own connection through :mod:`app.db`, so they are safe
to call from request handlers and background scheduler threads alike.
"""

from __future__ import annotations

import json
import os
import uuid

from . import config, db
from .models import Job, Run, now_iso


def new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def create_job(job: Job) -> Job:
    job.created_at = job.created_at or now_iso()
    job.updated_at = now_iso()
    with db.db_session() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, name, source_path, dest_root, dest_name_override, enabled,
                schedule_cron, timezone, delete_mode, checksum_mode,
                metadata_mode, exclusions_json, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                job.id,
                job.name,
                job.source_path,
                job.dest_root,
                job.dest_name_override,
                1 if job.enabled else 0,
                job.schedule_cron,
                job.timezone,
                1 if job.delete_mode else 0,
                1 if job.checksum_mode else 0,
                1 if job.metadata_mode else 0,
                json.dumps(job.exclusions),
                job.created_at,
                job.updated_at,
            ),
        )
    return job


def get_job(job_id: str) -> Job | None:
    with db.db_session() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return Job.from_row(row) if row else None


def list_jobs() -> list[Job]:
    with db.db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at ASC, name ASC"
        ).fetchall()
    return [Job.from_row(r) for r in rows]


def list_enabled_jobs() -> list[Job]:
    with db.db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE enabled = 1 ORDER BY created_at ASC"
        ).fetchall()
    return [Job.from_row(r) for r in rows]


def update_job(job: Job) -> Job:
    job.updated_at = now_iso()
    with db.db_session() as conn:
        conn.execute(
            """
            UPDATE jobs SET
                name=?, source_path=?, dest_root=?, dest_name_override=?,
                enabled=?, schedule_cron=?, timezone=?, delete_mode=?,
                checksum_mode=?, metadata_mode=?, exclusions_json=?, updated_at=?
            WHERE id=?
            """,
            (
                job.name,
                job.source_path,
                job.dest_root,
                job.dest_name_override,
                1 if job.enabled else 0,
                job.schedule_cron,
                job.timezone,
                1 if job.delete_mode else 0,
                1 if job.checksum_mode else 0,
                1 if job.metadata_mode else 0,
                json.dumps(job.exclusions),
                job.updated_at,
                job.id,
            ),
        )
    return job


def delete_job(job_id: str) -> bool:
    """Delete only the job record; leaves source/destination files untouched."""
    with db.db_session() as conn:
        conn.execute("UPDATE runs SET job_id = NULL WHERE job_id = ?", (job_id,))
        cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cur.rowcount > 0


def set_job_enabled(job_id: str, enabled: bool) -> bool:
    with db.db_session() as conn:
        cur = conn.execute(
            "UPDATE jobs SET enabled=?, updated_at=? WHERE id=?",
            (1 if enabled else 0, now_iso(), job_id),
        )
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------
def insert_run(run: Run) -> Run:
    with db.db_session() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                id, job_id, operation, source_path, destination_path, status,
                started_at, finished_at, exit_code, message, stats_json, log_path
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run.id,
                run.job_id,
                run.operation,
                run.source_path,
                run.destination_path,
                run.status,
                run.started_at,
                run.finished_at,
                run.exit_code,
                run.message,
                json.dumps(run.stats),
                run.log_path,
            ),
        )
    return run


def update_run(run: Run) -> Run:
    with db.db_session() as conn:
        conn.execute(
            """
            UPDATE runs SET
                status=?, finished_at=?, exit_code=?, message=?,
                stats_json=?, log_path=?
            WHERE id=?
            """,
            (
                run.status,
                run.finished_at,
                run.exit_code,
                run.message,
                json.dumps(run.stats),
                run.log_path,
                run.id,
            ),
        )
    return run


def get_run(run_id: str) -> Run | None:
    with db.db_session() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return Run.from_row(row) if row else None


def list_runs_for_job(job_id: str, limit: int = 50) -> list[Run]:
    with db.db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE job_id = ? ORDER BY started_at DESC LIMIT ?",
            (job_id, limit),
        ).fetchall()
    return [Run.from_row(r) for r in rows]


def list_runs(limit: int = 200) -> list[Run]:
    with db.db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [Run.from_row(r) for r in rows]


def latest_run_for_job(job_id: str) -> Run | None:
    runs = list_runs_for_job(job_id, limit=1)
    return runs[0] if runs else None


def active_run_for_job(job_id: str) -> Run | None:
    with db.db_session() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE job_id = ? AND status = 'running' "
            "ORDER BY started_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    return Run.from_row(row) if row else None


def prune_runs(job_id: str, keep: int | None = None) -> int:
    """Delete the oldest runs (and their log files) beyond the retention count."""
    keep = keep if keep is not None else config.max_runs_per_job()
    with db.db_session() as conn:
        rows = conn.execute(
            "SELECT id, log_path FROM runs WHERE job_id = ? "
            "ORDER BY started_at DESC LIMIT -1 OFFSET ?",
            (job_id, keep),
        ).fetchall()
    ids = [r["id"] for r in rows]
    if not ids:
        return 0
    with db.db_session() as conn:
        conn.execute(
            "DELETE FROM runs WHERE id IN (%s)" % ",".join("?" * len(ids)), ids
        )
    for r in rows:
        if r["log_path"]:
            try:
                os.remove(r["log_path"])
            except OSError:
                pass
    return len(ids)

