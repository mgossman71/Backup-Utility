"""Cron validation and timezone-aware next-run computation.

Shared by job validation (save-time) and the scheduler (runtime). Cron uses the
5-field crontab form; scheduling is interpreted in the job's IANA timezone.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytz
from apscheduler.triggers.cron import CronTrigger

from .timezones import normalize_timezone


class CronError(ValueError):
    pass


def validate_cron(expr: str | None) -> None:
    """Raise :class:`CronError` for an invalid 5-field cron expression."""
    if expr is None:
        return
    expr = expr.strip()
    if not expr:
        return
    try:
        CronTrigger.from_crontab(expr, timezone="UTC")
    except Exception as exc:  # noqa: BLE001
        raise CronError(f"Invalid cron expression '{expr}': {exc}") from exc


def next_run(expr: str | None, tz_name: str, after: datetime | None = None) -> datetime | None:
    """Return the next fire time (tz-aware) for ``expr`` in ``tz_name``.

    ``after`` lets tests drive a controlled clock; defaults to now.
    """
    if not expr or not expr.strip():
        return None
    tz = pytz.timezone(normalize_timezone(tz_name))
    trigger = CronTrigger.from_crontab(expr.strip(), timezone=tz)
    if after is None:
        after = datetime.now(tz)
    elif after.tzinfo is None:
        after = tz.localize(after)
    return trigger.get_next_fire_time(None, after)


def next_run_iso(expr: str | None, tz_name: str) -> str | None:
    dt = next_run(expr, tz_name)
    return dt.isoformat() if dt else None
