"""Task 2 acceptance tests: SQLite persistence, WAL mode, schema columns."""

from __future__ import annotations

from app import config, db, repositories
from app.models import Job, Run


def _make_job(name: str = "Docs") -> Job:
    return Job(
        id=repositories.new_id(),
        name=name,
        source_path="/srv/src",
        dest_root="/mnt/backup",
        enabled=True,
        schedule_cron="0 2 * * *",
        timezone="America/Chicago",
        delete_mode=False,
        checksum_mode=False,
        metadata_mode=True,
        exclusions=["tmp", "cache/*.log"],
    )


def test_init_db_creates_state_and_db(client):
    path = config.db_path()
    assert path.exists()
    assert path.parent.is_dir()


def test_wal_mode_enabled(client):
    assert db.is_wal() is True


def test_runs_schema_stores_required_columns(client):
    conn = db.connect()
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(runs)")}
    finally:
        conn.close()
    expected = {
        "operation",
        "status",
        "started_at",
        "finished_at",
        "exit_code",
        "stats_json",
        "log_path",
    }
    assert expected.issubset(cols)


def test_job_and_run_persist_across_restart(client):
    # 1) Create a job and a run.
    job = repositories.create_job(_make_job())
    run = repositories.insert_run(
        Run(
            id=repositories.new_id(),
            job_id=job.id,
            operation="backup",
            source_path=job.source_path,
            destination_path=job.dest_root,
            status="success",
            started_at="2026-01-01T02:00:00+00:00",
            finished_at="2026-01-01T02:00:05+00:00",
            exit_code=0,
            message="ok",
            stats={"files_transferred": 3, "bytes_transferred": 1234},
            log_path="/var/log/backup-ui/run.log",
        )
    )

    # 2) Simulate an application restart: re-init the schema (idempotent) and
    #    re-open fresh connections through the repositories.
    db.init_db()

    loaded = repositories.get_job(job.id)
    assert loaded is not None
    assert loaded.name == "Docs"
    assert loaded.exclusions == ["tmp", "cache/*.log"]

    runs = repositories.list_runs_for_job(job.id)
    assert len(runs) == 1
    assert runs[0].stats["files_transferred"] == 3
    assert runs[0].log_path == "/var/log/backup-ui/run.log"


def test_delete_job_leaves_runs_detached(client):
    job = repositories.create_job(_make_job(name="Temp"))
    repositories.insert_run(
        Run(
            id=repositories.new_id(),
            job_id=job.id,
            operation="backup",
            source_path="/srv/src",
            destination_path="/mnt/backup",
            status="success",
            started_at="2026-01-01T02:00:00+00:00",
        )
    )
    assert repositories.delete_job(job.id) is True
    assert repositories.get_job(job.id) is None
    # Run history survives with job_id detached.
    assert len(repositories.list_runs()) == 1
