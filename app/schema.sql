-- MountGuard Backup schema (SQLite, WAL mode set at connect time).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS jobs (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    source_path        TEXT NOT NULL,
    dest_root          TEXT NOT NULL,
    dest_name_override TEXT,
    enabled            INTEGER NOT NULL DEFAULT 1,
    schedule_cron      TEXT,
    timezone           TEXT NOT NULL DEFAULT 'America/Chicago',
    delete_mode        INTEGER NOT NULL DEFAULT 0,
    checksum_mode      INTEGER NOT NULL DEFAULT 0,
    metadata_mode      INTEGER NOT NULL DEFAULT 1,
    exclusions_json    TEXT NOT NULL DEFAULT '[]',
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id               TEXT PRIMARY KEY,
    job_id           TEXT,
    operation        TEXT NOT NULL,            -- backup | restore
    source_path      TEXT NOT NULL,
    destination_path TEXT NOT NULL,
    status           TEXT NOT NULL,            -- running | success | failure | skipped
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    exit_code        INTEGER,
    message          TEXT,
    stats_json       TEXT NOT NULL DEFAULT '{}',
    log_path         TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_job     ON runs(job_id);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_enabled ON jobs(enabled);
