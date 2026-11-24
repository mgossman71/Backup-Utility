"""Task 7 acceptance tests: rsync executor + run logging + copy behaviors.

Copy-behavior tests drive the executor synchronously against the real system
rsync; the HTTP/conflict tests live in test_task7_http.py using a fake rsync.
"""

from __future__ import annotations

import os
from pathlib import Path

from app import repositories
from app.models import Job, Run, now_iso
from app.services import executor

from helpers import make_job, run_backup


def test_build_command_contains_rsync_paths_and_flags():
    cmd = executor.build_command(source="/srv/data", dest="/mnt/backup/data", exclusions=["tmp", "*.log"])
    assert cmd[0]
    assert "-a" in cmd
    assert "--exclude=tmp" in cmd
    assert "--exclude=*.log" in cmd
    joined = " ".join(cmd)
    assert "/srv/data/" in joined and "/mnt/backup/data/" in joined
    assert "--delete-after" not in cmd


def test_build_command_delete_and_checksum_modes():
    cmd = executor.build_command(source="/a", dest="/b", delete=True, checksum=True)
    assert "--delete-after" in cmd
    assert "--checksum" in cmd


def test_first_run_copies_all_included_files(tmp_path):
    job = make_job(tmp_path)
    run = run_backup(job)
    assert run.status == "success", run.message
    dest_data = Path(job.dest_path())
    assert dest_data.is_dir()
    assert (dest_data / "keep" / "a.txt").read_text() == "alpha"
    assert (dest_data / "top.txt").exists()


def test_excluded_files_not_copied(tmp_path):
    job = make_job(tmp_path, exclusions=["skipme", "top.txt"])
    run = run_backup(job)
    assert run.status == "success", run.message
    dest_data = Path(job.dest_path())
    assert not (dest_data / "skipme" / "secret.txt").exists()
    assert not (dest_data / "top.txt").exists()
    assert (dest_data / "keep" / "a.txt").exists()


def test_second_run_transfers_zero(tmp_path):
    job = make_job(tmp_path)
    run_backup(job)
    run2 = run_backup(job)
    assert run2.status == "success", run2.message
    assert run2.stats.get("files_transferred") == 0


def test_modified_file_is_transferred(tmp_path):
    job = make_job(tmp_path)
    run_backup(job)
    Path(job.source_path, "keep", "a.txt").write_text("alpha-changed!!")
    run2 = run_backup(job)
    assert run2.status == "success", run2.message
    assert run2.stats.get("files_transferred", 0) >= 1
    assert Path(job.dest_path(), "keep", "a.txt").read_text() == "alpha-changed!!"


def test_new_file_is_copied(tmp_path):
    job = make_job(tmp_path)
    run_backup(job)
    Path(job.source_path, "newfile.txt").write_text("fresh")
    run2 = run_backup(job)
    assert run2.status == "success", run2.message
    assert Path(job.dest_path(), "newfile.txt").read_text() == "fresh"


def test_default_does_not_delete_destination_extras(tmp_path):
    job = make_job(tmp_path)
    run_backup(job)
    os.remove(Path(job.source_path, "keep", "b.txt"))
    run2 = run_backup(job)
    assert run2.status == "success", run2.message
    assert Path(job.dest_path(), "keep", "b.txt").exists()
