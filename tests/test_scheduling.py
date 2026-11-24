"""Interval scheduling: start date + clock + every-N-units -> trigger + words.

The user never sees a cron string. Cron is only a legacy fallback (tested in
test_task6) for jobs saved with a raw expression.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app import repositories
from app.models import Job
from app.services import schedule


# --- Unit: interval spec --------------------------------------------------

def test_build_spec_normalizes():
    spec = schedule.build_interval_spec("2026-01-05", "14:30", "2", "days")
    assert spec == {"start_date": "2026-01-05", "run_time": "14:30", "value": 2, "unit": "days"}


def test_build_spec_rejects_zero_and_bad_unit():
    with pytest.raises(schedule.ScheduleError):
        schedule.build_interval_spec("2026-01-05", "14:30", "0", "days")
    with pytest.raises(schedule.ScheduleError):
        schedule.build_interval_spec("2026-01-05", "14:30", "2", "months")


def test_build_spec_rejects_bad_date_and_time():
    with pytest.raises(schedule.ScheduleError):
        schedule.build_interval_spec("nope", "14:30", "2", "days")
    with pytest.raises(schedule.ScheduleError):
        schedule.build_interval_spec("2026-01-05", "25:00", "2", "days")


def _interval_job(value, unit, start="2026-01-05", run="02:00"):
    return Job(
        id="j1", name="J", source_path="/s", dest_root="/d",
        enabled=True, schedule_kind="interval",
        schedule_start_date=start, schedule_run_time=run,
        schedule_interval_value=value, schedule_interval_unit=unit,
        timezone="America/Chicago",
    )


def test_effective_kind_resolves():
    assert schedule.effective_kind(_interval_job(2, "days")) == "interval"
    assert schedule.effective_kind(Job(id="x", name="n", source_path="/s", dest_root="/d",
                                        schedule_cron="0 2 * * *")) == "cron"
    assert schedule.effective_kind(Job(id="x", name="n", source_path="/s", dest_root="/d")) == "none"


def test_describe_interval_and_none():
    assert schedule.describe_job(_interval_job(1, "days")) == "Every 1 day starting January 5, 2026 at 2:00 AM"
    assert schedule.describe_job(_interval_job(2, "hours", run="09:30")) == "Every 2 hours starting January 5, 2026 at 9:30 AM"
    assert schedule.describe_job(_interval_job(3, "weeks")) == "Every 3 weeks starting January 5, 2026 at 2:00 AM"
    assert schedule.describe_job(Job(id="x", name="n", source_path="/s", dest_root="/d")) == "Not scheduled"


def test_describe_legacy_cron_in_words():
    job = Job(id="x", name="n", source_path="/s", dest_root="/d", schedule_cron="0 2 * * *")
    assert schedule.describe_job(job) == "Every day at 2:00 AM"


def test_next_run_interval_honours_interval():
    job = _interval_job(3, "days", start="2026-01-05", run="02:00")
    after = datetime(2026, 1, 5, 12, 0)  # naive -> localized to job tz
    nxt = schedule.next_run_for_job(job, after=after)
    assert nxt is not None
    assert nxt.strftime("%Y-%m-%d %H:%M") == "2026-01-08 02:00"


def test_make_trigger_unscheduled_is_none():
    assert schedule.make_trigger(Job(id="x", name="n", source_path="/s", dest_root="/d")) is None


# --- HTTP: friendly fields drive persistence + display --------------------

def _base(src, dest, **over):
    data = {"name": "Sched", "source_path": src, "dest_root": dest, "enabled": "1",
            "timezone": "America/Chicago", "metadata_mode": "1"}
    data.update(over)
    return data


def test_http_every_2_days(client, csrf_headers, backup_dirs):
    resp = client.post("/jobs", data=_base(
        backup_dirs["src"], backup_dirs["dest"],
        schedule_kind="interval", schedule_start_date="2026-01-05",
        schedule_run_time="02:00", schedule_interval_value="2", schedule_interval_unit="days",
    ), headers=csrf_headers)
    assert resp.status_code == 303
    job = repositories.list_jobs()[0]
    assert job.schedule_kind == "interval"
    assert job.schedule_interval_value == 2
    assert job.schedule_interval_unit == "days"
    assert job.schedule_cron is None


def test_http_manual_only(client, csrf_headers, backup_dirs):
    resp = client.post("/jobs", data=_base(backup_dirs["src"], backup_dirs["dest"],
                                          schedule_kind="none"), headers=csrf_headers)
    assert resp.status_code == 303
    job = repositories.list_jobs()[0]
    assert schedule.effective_kind(job) == "none"


def test_http_invalid_interval_rejected(client, csrf_headers, backup_dirs):
    resp = client.post("/jobs", data=_base(
        backup_dirs["src"], backup_dirs["dest"],
        schedule_kind="interval", schedule_start_date="2026-01-05",
        schedule_run_time="02:00", schedule_interval_value="0", schedule_interval_unit="days",
    ), headers=csrf_headers)
    assert resp.status_code == 422
    assert repositories.list_jobs() == []


def test_http_legacy_cron_still_works(client, csrf_headers, backup_dirs):
    resp = client.post("/jobs", data=_base(backup_dirs["src"], backup_dirs["dest"],
                                          schedule_cron="0 2 * * *"), headers=csrf_headers)
    assert resp.status_code == 303
    job = repositories.list_jobs()[0]
    assert job.schedule_kind == "cron"
    assert job.schedule_cron == "0 2 * * *"


def test_new_form_has_no_cron(client):
    r = client.get("/jobs/new")
    assert r.status_code == 200
    assert 'name="schedule_kind"' in r.text
    assert 'type="date"' in r.text
    assert 'name="schedule_interval_value"' in r.text
    assert 'name="schedule_cron"' not in r.text  # cron never surfaced


def test_edit_prefills_interval(client, csrf_headers, backup_dirs):
    client.post("/jobs", data=_base(
        backup_dirs["src"], backup_dirs["dest"],
        schedule_kind="interval", schedule_start_date="2026-02-10",
        schedule_run_time="09:30", schedule_interval_value="5", schedule_interval_unit="days",
    ), headers=csrf_headers)
    job = repositories.list_jobs()[0]
    r = client.get(f"/jobs/{job.id}/edit")
    assert 'value="2026-02-10"' in r.text
    assert 'value="09:30"' in r.text
    assert 'value="5"' in r.text
    assert '<option value="days" selected>' in r.text


def test_detail_shows_words_not_cron(client, csrf_headers, backup_dirs):
    client.post("/jobs", data=_base(
        backup_dirs["src"], backup_dirs["dest"],
        schedule_kind="interval", schedule_start_date="2026-01-05",
        schedule_run_time="02:00", schedule_interval_value="2", schedule_interval_unit="days",
    ), headers=csrf_headers)
    job = repositories.list_jobs()[0]
    r = client.get(f"/jobs/{job.id}")
    assert "Every 2 days starting January 5, 2026 at 2:00 AM" in r.text

    assert schedule.make_trigger(Job(id="x", name="n", source_path="/s", dest_root="/d")) is None
