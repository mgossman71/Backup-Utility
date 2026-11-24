"""Task 6 acceptance tests: job CRUD, path validation, exclusion persistence."""

from __future__ import annotations

import os
from pathlib import Path

from app import repositories
from app.services import timezones


def _payload(src, dest, **overrides):
    data = {
        "name": "Docs Backup",
        "source_path": src,
        "dest_root": dest,
        "schedule_cron": "0 2 * * *",
        "timezone": "CST",
        "enabled": "1",
        "metadata_mode": "1",
    }
    data.update(overrides)
    return data


def test_create_job_persists_and_lists(client, csrf_headers, backup_dirs):
    resp = client.post("/jobs", data=_payload(backup_dirs["src"], backup_dirs["dest"]), headers=csrf_headers)
    assert resp.status_code == 303
    jobs = repositories.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].name == "Docs Backup"


def test_cst_stored_as_america_chicago(client, csrf_headers, backup_dirs):
    client.post("/jobs", data=_payload(backup_dirs["src"], backup_dirs["dest"]), headers=csrf_headers)
    job = repositories.list_jobs()[0]
    assert job.timezone == "America/Chicago"


def test_invalid_cron_rejected(client, csrf_headers, backup_dirs):
    resp = client.post(
        "/jobs",
        data=_payload(backup_dirs["src"], backup_dirs["dest"], schedule_cron="not a cron"),
        headers=csrf_headers,
    )
    assert resp.status_code == 422
    assert repositories.list_jobs() == []


def test_exclusions_persisted(client, csrf_headers, backup_dirs):
    resp = client.post(
        "/jobs",
        data=_payload(backup_dirs["src"], backup_dirs["dest"], exclusions="skipme\ntop.txt"),
        headers=csrf_headers,
    )
    assert resp.status_code == 303
    job = repositories.list_jobs()[0]
    assert job.exclusions == ["skipme", "top.txt"]


def test_edit_job_updates_fields(client, csrf_headers, backup_dirs):
    client.post("/jobs", data=_payload(backup_dirs["src"], backup_dirs["dest"]), headers=csrf_headers)
    job = repositories.list_jobs()[0]
    resp = client.post(
        f"/jobs/{job.id}",
        data=_payload(backup_dirs["src"], backup_dirs["dest"], name="Renamed", delete_mode="1", confirm_delete_mode="1", exclusions="keep"),
        headers=csrf_headers,
    )
    assert resp.status_code == 303
    updated = repositories.get_job(job.id)
    assert updated.name == "Renamed"
    assert updated.delete_mode is True
    assert updated.exclusions == ["keep"]


def test_delete_mode_requires_confirmation(client, csrf_headers, backup_dirs):
    resp = client.post(
        "/jobs",
        data=_payload(backup_dirs["src"], backup_dirs["dest"], delete_mode="1"),
        headers=csrf_headers,
    )
    assert resp.status_code == 422
    assert repositories.list_jobs() == []


def test_missing_source_rejected(client, csrf_headers, backup_dirs, tmp_path):
    resp = client.post(
        "/jobs",
        data=_payload(str(tmp_path / "ghost"), backup_dirs["dest"]),
        headers=csrf_headers,
    )
    assert resp.status_code == 422


def test_missing_destination_needs_confirmation(client, csrf_headers, backup_dirs, tmp_path):
    missing = str(Path(backup_dirs["dest"]) / "newdest")  # parent writable
    # Without confirmation -> rejected.
    resp = client.post(
        "/jobs",
        data=_payload(backup_dirs["src"], missing),
        headers=csrf_headers,
    )
    assert resp.status_code == 422
    # With confirmation -> saved.
    resp = client.post(
        "/jobs",
        data=_payload(backup_dirs["src"], missing, confirm_missing_destination="1"),
        headers=csrf_headers,
    )
    assert resp.status_code == 303


def test_delete_job_leaves_files(client, csrf_headers, backup_dirs):
    client.post("/jobs", data=_payload(backup_dirs["src"], backup_dirs["dest"]), headers=csrf_headers)
    job = repositories.list_jobs()[0]
    src = Path(backup_dirs["src"])
    before = sorted(p.name for p in src.iterdir())
    resp = client.delete(f"/jobs/{job.id}", headers=csrf_headers)
    assert resp.status_code == 303
    assert repositories.get_job(job.id) is None
    after = sorted(p.name for p in src.iterdir())
    assert before == after  # files intact


def test_post_without_csrf_token_rejected(client, backup_dirs):
    resp = client.post("/jobs", data=_payload(backup_dirs["src"], backup_dirs["dest"]))
    assert resp.status_code == 403


def test_timezone_normalization_helper():
    assert timezones.normalize_timezone("CST") == "America/Chicago"
    assert timezones.normalize_timezone("America/Chicago") == "America/Chicago"
