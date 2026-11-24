"""Shared, non-test helpers for backup execution tests (real rsync)."""

from __future__ import annotations

from pathlib import Path

from app import repositories
from app.models import Job, Run, now_iso
from app.services import executor


def make_job(tmp_path, *, delete=False, checksum=False, exclusions=None) -> Job:
    src = tmp_path / "src"
    dest = tmp_path / "out"
    (src / "keep").mkdir(parents=True, exist_ok=True)
    (src / "keep" / "a.txt").write_text("alpha")
    (src / "keep" / "b.txt").write_text("beta")
    (src / "skipme").mkdir(exist_ok=True)
    (src / "skipme" / "secret.txt").write_text("secret")
    (src / "top.txt").write_text("top-level")
    dest.mkdir(exist_ok=True)
    return repositories.create_job(
        Job(
            id=repositories.new_id(),
            name="Real",
            source_path=str(src),
            dest_root=str(dest),
            enabled=False,
            delete_mode=delete,
            checksum_mode=checksum,
            metadata_mode=True,
            exclusions=exclusions or [],
        )
    )


def run_backup(job: Job, *, delete=None, exclusions=None) -> Run:
    run = Run(
        id=repositories.new_id(),
        job_id=job.id,
        operation="backup",
        source_path=job.source_path,
        destination_path=job.dest_path(),
        status="running",
        started_at=now_iso(),
    )
    repositories.insert_run(run)
    return executor.execute(
        run,
        metadata=job.metadata_mode,
        checksum=job.checksum_mode,
        delete=job.delete_mode if delete is None else delete,
        exclusions=job.exclusions if exclusions is None else exclusions,
    )
