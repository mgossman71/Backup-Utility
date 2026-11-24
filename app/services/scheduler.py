"""APScheduler wiring: cron schedules in per-job IANA timezones.

Enabled jobs with a valid cron are registered on startup (restart resume). A
disabled job registers no trigger. Scheduled runs honour the per-job conflict
lock, so an overlapping fire is skipped rather than queued.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .. import config, repositories
from . import executor, schedule
from .timezones import normalize_timezone

logger = logging.getLogger("backup-ui.scheduler")

_scheduler: BackgroundScheduler | None = None


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running


def start() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": None}
    )
    _scheduler.start()
    load_jobs()
    return _scheduler


def shutdown() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def _scheduled_run(job_id: str) -> None:
    job = repositories.get_job(job_id)
    if not job or not job.enabled:
        return
    try:
        executor.request_run(job, operation="backup", background=True)
    except executor.ConflictError:
        logger.info("Skipped scheduled run for '%s': already running", job.name)


def register_job(job) -> None:
    """Add or refresh the trigger for a single job."""
    if not _scheduler or not _scheduler.running:
        return
    existing = _scheduler.get_job(job.id)
    if existing:
        _scheduler.remove_job(job.id)
    if not job.enabled or not job.schedule_cron:
        return
    try:
        schedule.validate_cron(job.schedule_cron)
        trigger = CronTrigger.from_crontab(
            job.schedule_cron, timezone=normalize_timezone(job.timezone)
        )
    except (schedule.CronError, Exception) as exc:  # noqa: BLE001
        logger.warning("Not scheduling job '%s': %s", job.name, exc)
        return
    _scheduler.add_job(
        _scheduled_run,
        trigger=trigger,
        id=job.id,
        args=[job.id],
        name=job.name,
        replace_existing=True,
    )


def remove_job(job_id: str) -> None:
    if _scheduler and _scheduler.running:
        try:
            _scheduler.remove_job(job_id)
        except Exception:
            pass


def load_jobs() -> None:
    for job in repositories.list_enabled_jobs():
        register_job(job)


def next_run_time(job) -> str | None:
    """Return the trigger's next fire time (tz-aware ISO) for display, or None."""
    if not job.enabled or not job.schedule_cron:
        return None
    dt = schedule.next_run(job.schedule_cron, job.timezone)
    return dt.isoformat() if dt else None


def next_run_display(job) -> str:
    iso = next_run_time(job)
    if not iso:
        return ""
    return iso
