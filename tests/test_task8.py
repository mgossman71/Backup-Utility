"""Task 8 acceptance tests: cron, timezone-aware next runs, restart resume."""

from __future__ import annotations

from datetime import datetime

import pytz

from app import repositories
from app.models import Job
from app.services import schedule, scheduler
from app.services.timezones import normalize_timezone


def _enabled_job(tmp_path, cron="0 2 * * *", tz="America/Chicago", enabled=True) -> Job:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(exist_ok=True)
    dst.mkdir(exist_ok=True)
    return repositories.create_job(
        Job(
            id=repositories.new_id(),
            name="Sched",
            source_path=str(src),
            dest_root=str(dst),
            enabled=enabled,
            schedule_cron=cron,
            timezone=tz,
        )
    )


def test_controlled_clock_fires_0200_central_not_utc():
    tz = pytz.timezone("America/Chicago")
    after = tz.localize(datetime(2026, 1, 1, 1, 30))  # 01:30 local
    dt = schedule.next_run("0 2 * * *", "America/Chicago", after=after)
    assert dt is not None
    assert dt.hour == 2 and dt.minute == 0
    # Must be Central Time (UTC-6 in January), never 02:00 UTC.
    assert dt.utcoffset().total_seconds() != 0
    assert (dt.astimezone(pytz.utc)).hour != 2


def test_invalid_cron_not_registered():
    scheduler.start()
    try:
        job = Job(
            id="badc",
            name="Bad",
            source_path="/x",
            dest_root="/y",
            enabled=True,
            schedule_cron="definitely not cron",
            timezone="America/Chicago",
        )
        scheduler.register_job(job)
        assert scheduler._scheduler.get_job(job.id) is None
    finally:
        scheduler.shutdown()


def test_enabled_job_registers_future_next_run(tmp_path):
    job = _enabled_job(tmp_path)
    scheduler.start()
    try:
        scheduler.register_job(job)
        apjob = scheduler._scheduler.get_job(job.id)
        assert apjob is not None
        assert apjob.next_run_time is not None
        tzinfo = apjob.next_run_time.tzinfo
        tz_name = getattr(tzinfo, "key", None) or getattr(tzinfo, "zone", None)
        assert tz_name == "America/Chicago"
        assert apjob.next_run_time.hour == 2
    finally:
        scheduler.shutdown()


def test_cst_maps_to_chicago_and_shows_next_run(tmp_path):
    stored = repositories.create_job(
        Job(
            id="cst1",
            name="CST",
            source_path="/x",
            dest_root="/y",
            enabled=True,
            schedule_cron="0 2 * * *",
            timezone=normalize_timezone("CST"),
        )
    )
    assert stored.timezone == "America/Chicago"
    iso = scheduler.next_run_time(stored)
    assert iso is not None and "02:00" in iso


def test_disabled_job_has_no_trigger_and_blank_next(tmp_path):
    job = _enabled_job(tmp_path, enabled=False)
    scheduler.start()
    try:
        scheduler.register_job(job)
        assert scheduler._scheduler.get_job(job.id) is None
        assert scheduler.next_run_time(job) is None
    finally:
        scheduler.shutdown()


def test_restart_reload_registers_enabled_jobs(tmp_path):
    j1 = _enabled_job(tmp_path, cron="0 2 * * *")
    j2 = _enabled_job(tmp_path, cron="*/15 * * * *")
    _enabled_job(tmp_path, enabled=False)  # should not register

    def started_ids():
        return {j.id for j in scheduler._scheduler.get_jobs()}

    scheduler.start()
    first = started_ids()
    scheduler.shutdown()

    # Simulate a fresh process: start again, loading from the DB.
    scheduler.start()
    second = started_ids()
    scheduler.shutdown()

    assert {j1.id, j2.id}.issubset(first)
    assert {j1.id, j2.id}.issubset(second)
    assert len(second) == 2  # disabled job excluded
