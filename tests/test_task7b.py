"""Task 7 (part 2): delete mode, failures, run history, log, symlink preserve."""

from __future__ import annotations

import os
from pathlib import Path

from app import repositories
from app.models import Run, now_iso
from app.services import executor

from helpers import make_job, run_backup


def test_delete_mode_removes_extras_keeps_excluded(tmp_path):
    job = make_job(tmp_path, delete=True)
    run_backup(job, delete=True, exclusions=["skipme"])
    dest = Path(job.dest_path())
    # Manually place an excluded file in the destination to prove it survives.
    (dest / "skipme").mkdir(exist_ok=True)
    (dest / "skipme" / "keepme.txt").write_text("keepme")
    os.remove(Path(job.source_path, "keep", "b.txt"))
    run2 = run_backup(job, delete=True, exclusions=["skipme"])
    assert run2.status == "success", run2.message
    assert not (dest / "keep" / "b.txt").exists()          # removed (AC-RUN-009)
    assert (dest / "skipme" / "keepme.txt").exists()       # excluded survives (AC-RUN-010)


def test_missing_source_fails_with_actionable_message(tmp_path):
    job = make_job(tmp_path)
    run = Run(
        id=repositories.new_id(),
        job_id=job.id,
        operation="backup",
        source_path=str(tmp_path / "does-not-exist"),
        destination_path=job.dest_path(),
        status="running",
        started_at=now_iso(),
    )
    repositories.insert_run(run)
    out = executor.execute(run, metadata=True, checksum=False, delete=False, exclusions=[])
    assert out.status == "failure"
    assert out.exit_code and out.exit_code != 0
    assert out.message  # actionable message present


def test_missing_destination_created_when_parent_writable(tmp_path):
    job = make_job(tmp_path)
    new_dest = Path(job.dest_root, "created-sub")
    run = Run(
        id=repositories.new_id(),
        job_id=job.id,
        operation="backup",
        source_path=job.source_path,
        destination_path=str(new_dest),
        status="running",
        started_at=now_iso(),
    )
    repositories.insert_run(run)
    out = executor.execute(run, metadata=True, checksum=False, delete=False, exclusions=[])
    assert out.status == "success", out.message
    assert new_dest.is_dir()


def test_run_history_has_required_fields(tmp_path):
    job = make_job(tmp_path)
    run = run_backup(job)
    loaded = repositories.get_run(run.id)
    assert loaded is not None
    assert loaded.status in ("success", "failure")
    assert loaded.started_at and loaded.finished_at
    assert loaded.exit_code is not None
    assert loaded.log_path and os.path.isfile(loaded.log_path)
    assert "files_transferred" in loaded.stats


def test_run_log_contains_rsync_source_destination(tmp_path):
    job = make_job(tmp_path)
    run = run_backup(job)
    log = open(run.log_path, encoding="utf-8", errors="replace").read()
    assert "rsync" in log
    assert job.source_path in log
    assert job.dest_path() in log


def test_symlink_preserved_as_symlink(tmp_path):
    job = make_job(tmp_path)
    src = Path(job.source_path)
    os.symlink("keep/a.txt", str(src / "link.txt"))
    run = run_backup(job)
    assert run.status == "success", run.message
    assert Path(job.dest_path(), "link.txt").is_symlink()
