"""Schedule engine: interval triggers (primary) + cron (legacy).

Users schedule by picking a start date, a clock time, and a plain interval
("every N minutes/hours/days/weeks"). Arbitrary intervals like "every 5 days"
cannot be expressed in cron, so the primary engine is APScheduler's
IntervalTrigger. Legacy jobs that store a raw cron expression are still honored
via CronTrigger, and their schedules are shown in human words (never raw).
"""

from __future__ import annotations

from datetime import date, datetime, time

import pytz
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .timezones import normalize_timezone


class CronError(ValueError):
    pass


class ScheduleError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Legacy cron validation (still used for jobs saved with a raw cron string).
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Interval scheduling — the friendly, cron-free model.
# ---------------------------------------------------------------------------
SCHEDULE_KINDS = ["none", "interval"]

# Units accepted for "every N <unit>". These map directly to IntervalTrigger
# keyword arguments. (Calendar months are intentionally excluded: they are not a
# fixed interval and would need the cron engine.)
INTERVAL_UNITS = [
    {"value": "minutes", "label": "minutes"},
    {"value": "hours", "label": "hours"},
    {"value": "days", "label": "days"},
    {"value": "weeks", "label": "weeks"},
]
_UNIT_VALUES = {u["value"] for u in INTERVAL_UNITS}
_UNIT_SINGULAR = {
    "minutes": "minute",
    "hours": "hour",
    "days": "day",
    "weeks": "week",
}


def effective_kind(job) -> str:
    """Resolve a job's schedule kind, tolerating legacy cron-only rows."""
    if getattr(job, "schedule_interval_unit", None) and getattr(job, "schedule_interval_value", None):
        return "interval"
    if getattr(job, "schedule_cron", None):
        return "cron"
    return getattr(job, "schedule_kind", "none") or "none"


def _parse_clock(value: str) -> time:
    text = (value or "").strip()
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise ScheduleError("Choose a valid time (for example 2:30 AM).")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise ScheduleError("Choose a valid time (for example 2:30 AM).") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ScheduleError("Choose a valid time (for example 2:30 AM).")
    return time(hour, minute)


def _parse_date(value: str) -> date:
    text = (value or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ScheduleError("Choose a valid start date.") from exc


def build_interval_spec(start_date: str, run_time: str, value, unit: str) -> dict:
    """Validate and normalize interval fields into a storable spec dict.

    Raises :class:`ScheduleError` on any invalid input.
    """
    d = _parse_date(start_date)
    t = _parse_clock(run_time)
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ScheduleError("Choose how often it should repeat (a whole number).") from exc
    if n < 1:
        raise ScheduleError("Repeats must be at least 1.")
    if n > 1000:
        raise ScheduleError("That interval is too large.")
    if unit not in _UNIT_VALUES:
        raise ScheduleError("Choose a valid interval unit.")
    return {
        "start_date": d.isoformat(),
        "run_time": t.strftime("%H:%M"),
        "value": n,
        "unit": unit,
    }


def _combine_local(start_date: str, run_time: str, tz_name: str):
    """Localize a start date + clock time into a tz-aware datetime."""
    tz = pytz.timezone(normalize_timezone(tz_name))
    d = _parse_date(start_date)
    t = _parse_clock(run_time)
    naive = datetime(d.year, d.month, d.day, t.hour, t.minute)
    return tz.localize(naive)


def make_trigger(job):
    """Build the APScheduler trigger for a job, or None if unscheduled."""
    kind = effective_kind(job)
    tz_name = normalize_timezone(getattr(job, "timezone", "UTC"))
    if kind == "interval":
        start = _combine_local(job.schedule_start_date, job.schedule_run_time, tz_name)
        return IntervalTrigger(
            **{job.schedule_interval_unit: job.schedule_interval_value},
            start_date=start,
            timezone=tz_name,
        )
    if kind == "cron":
        return CronTrigger.from_crontab(job.schedule_cron, timezone=tz_name)
    return None


def next_run_for_job(job, after: datetime | None = None) -> datetime | None:
    """Next fire time (tz-aware) for a job's schedule, or None."""
    kind = effective_kind(job)
    if kind not in ("interval", "cron"):
        return None
    try:
        trigger = make_trigger(job)
    except Exception:  # noqa: BLE001
        return None
    if trigger is None:
        return None
    tz = pytz.timezone(normalize_timezone(job.timezone))
    if after is None:
        after = datetime.now(tz)
    elif after.tzinfo is None:
        after = tz.localize(after)
    try:
        return trigger.get_next_fire_time(None, after)
    except Exception:  # noqa: BLE001
        return None


def next_run(expr: str | None, tz_name: str, after: datetime | None = None) -> datetime | None:
    """Next fire time for a raw cron expression (legacy helper for tests/tools)."""
    if not expr or not expr.strip():
        return None
    tz = pytz.timezone(normalize_timezone(tz_name))
    trigger = CronTrigger.from_crontab(expr.strip(), timezone=tz)
    if after is None:
        after = datetime.now(tz)
    elif after.tzinfo is None:
        after = tz.localize(after)
    return trigger.get_next_fire_time(None, after)


# ---------------------------------------------------------------------------
# Human-readable descriptions (never show a raw cron to end users).
# ---------------------------------------------------------------------------
def _fmt_clock(hour: int, minute: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {suffix}"


def _fmt_date(iso: str) -> str:
    d = _parse_date(iso)
    return f"{d:%B} {d.day}, {d.year}"


def describe_job(job) -> str:
    """Plain-English summary of a job's schedule."""
    kind = effective_kind(job)
    if kind == "interval":
        n = job.schedule_interval_value
        unit = _UNIT_SINGULAR.get(job.schedule_interval_unit, job.schedule_interval_unit)
        word = unit if n == 1 else f"{unit}s"
        t = _parse_clock(job.schedule_run_time)
        clock = _fmt_clock(t.hour, t.minute)
        try:
            when = _fmt_date(job.schedule_start_date)
            return f"Every {n} {word} starting {when} at {clock}"
        except ScheduleError:
            return f"Every {n} {word} at {clock}"
    if kind == "cron":
        return _describe_cron(job.schedule_cron)
    return "Not scheduled"


# --- legacy cron description (kept for older jobs; shown in words, never raw)
_DOW_NAME = {
    "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat", "0": "Sun",
}


def _describe_cron(expr: str | None) -> str:
    if not expr or not expr.strip():
        return "Not scheduled"
    fields = expr.split()
    if len(fields) != 5 or not (fields[0].isdigit() and fields[1].isdigit()):
        return "Custom schedule"
    minute, hour, dom, month, dow = fields
    clock = _fmt_clock(int(hour), int(minute))
    if month == "*" and dom == "*" and dow == "*":
        return f"Every day at {clock}"
    if month == "*" and dom == "*" and dow != "*":
        parts = dow.split(",")
        if all(p.isdigit() for p in parts):
            ordered = sorted(parts, key=lambda x: (int(x) == 0, int(x)))
            names = ", ".join(_DOW_NAME.get(p, "?") for p in ordered)
            return f"Every week on {names} at {clock}"
        return "Custom schedule"
    if month == "*" and dow == "*" and dom.isdigit():
        return f"Every month on day {int(dom)} at {clock}"
    return "Custom schedule"

