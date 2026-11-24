"""View-model helpers shared by the dashboard, job editor, and job detail.

Pure formatting/preparation over repositories/services so route handlers stay
thin and the templates receive ready-to-render structures.
"""

from __future__ import annotations

from datetime import datetime

from . import config, repositories
from .models import Job, Run
from .services import schedule
from .services.timezones import TIMEZONE_OPTIONS, normalize_timezone

DEFAULT_TZ = "America/Chicago"


def _tz(tz_name: str):
    import pytz

    return pytz.timezone(normalize_timezone(tz_name))


def next_run_view(job: Job) -> str:
    if not job.enabled:
        return ""
    dt = schedule.next_run_for_job(job)
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M %Z")


def _spark_for(runs: list[Run]) -> list[dict]:
    """Build up to 10 sparkline bars (oldest→newest) from recent runs."""
    recent = list(reversed(runs[:10]))
    if not recent:
        return []
    durs = [r.duration_seconds for r in recent]
    peak = max((d for d in durs if d is not None), default=0) or 1
    bars: list[dict] = []
    for r, d in zip(recent, durs):
        if r.status == "running":
            bars.append({"level": 0.9, "kind": ""})
            continue
        kind = "danger" if r.status not in ("success",) else ""
        level = 0.15 if d is None else max(0.15, min(1.0, d / peak))
        bars.append({"level": level, "kind": kind})
    return bars


def _status_of(job: Job, last: Run | None) -> str:
    if repositories.active_run_for_job(job.id):
        return "running"
    if last:
        return last.status
    return "scheduled" if (job.enabled and schedule.effective_kind(job) != "none") else "no_runs"


def job_card(job: Job) -> dict:
    runs = repositories.list_runs_for_job(job.id, limit=10)
    last = runs[0] if runs else None
    return {
        "job": job,
        "last_run": last,
        "status": _status_of(job, last),
        "spark": _spark_for(runs),
        "next_run": next_run_view(job),
        "schedule_desc": schedule.describe_job(job),
    }


def dashboard_context() -> dict:
    jobs = repositories.list_jobs()
    cards = [job_card(j) for j in jobs]
    running = sum(1 for j in jobs if repositories.active_run_for_job(j.id))
    return {
        "cards": cards,
        "metrics": {
            "total": len(jobs),
            "scheduled": sum(1 for j in jobs if j.enabled and schedule.effective_kind(j) != "none"),
            "running": running,
            "recent": len(repositories.list_runs(limit=25)),
        },
    }



def _truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "checked"}


def _default_schedule_fields() -> dict:
    today = datetime.now().date().isoformat()
    return {
        "schedule_kind": "none",
        "schedule_start_date": today,
        "schedule_run_time": "02:00",
        "schedule_interval_value": "1",
        "schedule_interval_unit": "days",
    }


def _schedule_fields_from_data(data: dict) -> dict:
    return {
        "schedule_kind": data.get("schedule_kind") or "none",
        "schedule_start_date": data.get("schedule_start_date") or "",
        "schedule_run_time": data.get("schedule_run_time") or "",
        "schedule_interval_value": str(data.get("schedule_interval_value") or ""),
        "schedule_interval_unit": data.get("schedule_interval_unit") or "days",
    }


def _schedule_fields_from_job(job: Job) -> dict:
    if schedule.effective_kind(job) == "interval":
        return {
            "schedule_kind": "interval",
            "schedule_start_date": job.schedule_start_date or "",
            "schedule_run_time": job.schedule_run_time or "",
            "schedule_interval_value": str(job.schedule_interval_value or ""),
            "schedule_interval_unit": job.schedule_interval_unit or "days",
        }
    # "none" or a legacy cron job: the editor offers interval controls only
    # (cron is never surfaced to users), so default to manual.
    base = _default_schedule_fields()
    return base


def form_values(job: Job | None, data: dict | None) -> dict:
    """Repopulate editor fields from submitted data (error re-render) or a job."""
    if data is not None:
        excl = data.get("exclusions")
        if isinstance(excl, (list, tuple)):
            excl_text = "\n".join(str(x) for x in excl)
        else:
            excl_text = str(excl or "")
        values = {
            "name": data.get("name", "") or "",
            "source_path": data.get("source_path", "") or "",
            "dest_root": data.get("dest_root", "") or "",
            "dest_name_override": data.get("dest_name_override", "") or "",
            "enabled": _truthy(data.get("enabled", "1")),
            "timezone": data.get("timezone") or DEFAULT_TZ,
            "delete_mode": _truthy(data.get("delete_mode")),
            "checksum_mode": _truthy(data.get("checksum_mode")),
            "metadata_mode": _truthy(data.get("metadata_mode", "1")),
            "exclusions": excl_text,
            "confirm_missing_destination": _truthy(data.get("confirm_missing_destination")),
            "confirm_dest_inside_source": _truthy(data.get("confirm_dest_inside_source")),
            "confirm_delete_mode": _truthy(data.get("confirm_delete_mode")),
        }
        values.update(_schedule_fields_from_data(data))
        return values
    if job is not None:
        values = {
            "name": job.name,
            "source_path": job.source_path,
            "dest_root": job.dest_root,
            "dest_name_override": job.dest_name_override or "",
            "enabled": job.enabled,
            "timezone": job.timezone,
            "delete_mode": job.delete_mode,
            "checksum_mode": job.checksum_mode,
            "metadata_mode": job.metadata_mode,
            "exclusions": "\n".join(job.exclusions),
            "confirm_missing_destination": False,
            "confirm_dest_inside_source": False,
            "confirm_delete_mode": job.delete_mode,
        }
        values.update(_schedule_fields_from_job(job))
        return values
    values = {
        "name": "",
        "source_path": "",
        "dest_root": "",
        "dest_name_override": "",
        "enabled": True,
        "timezone": DEFAULT_TZ,
        "delete_mode": False,
        "checksum_mode": False,
        "metadata_mode": True,
        "exclusions": "",
        "confirm_missing_destination": False,
        "confirm_dest_inside_source": False,
        "confirm_delete_mode": False,
    }
    values.update(_default_schedule_fields())
    return values


def detail_context(job: Job) -> dict:
    runs = repositories.list_runs_for_job(job.id, limit=config.max_runs_per_job())
    last = runs[0] if runs else None
    return {
        "job": job,
        "runs": runs,
        "last_run": last,
        "status": _status_of(job, last),
        "spark": _spark_for(runs),
        "next_run": next_run_view(job),
        "schedule_desc": schedule.describe_job(job),
        "timezone_options": TIMEZONE_OPTIONS,
    }