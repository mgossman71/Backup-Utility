"""SQLite connection management and schema bootstrap.

A new short-lived connection is opened per operation so the app can move freely
across threads (APScheduler jobs, request handlers) without sharing a connection.
WAL mode is enabled on every connect for safe concurrent readers.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect() -> sqlite3.Connection:
    """Open a configured SQLite connection (WAL + foreign keys + row factory)."""
    path = config.db_path()
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db() -> Path:
    """Create the state directory and schema if missing; return the DB path."""
    path = config.db_path()  # ensures state dir exists via config resolver
    conn = connect()
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()
    return path


@contextmanager
def db_session():
    """Context manager yielding a connection with commit/rollback semantics."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_wal() -> bool:
    """Return True when the database is running in WAL journal mode."""
    conn = connect()
    try:
        row = conn.execute("PRAGMA journal_mode").fetchone()
        return (row[0] or "").lower() == "wal"
    finally:
        conn.close()
