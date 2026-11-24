"""Shared pytest fixtures for MountGuard Backup.

The application is imported *inside* fixtures so tests can point state/log
directories at temporary locations before the app (and its SQLite layer) is
created.
"""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def env_db(tmp_path, monkeypatch):
    """Point state/log dirs at a temp location and initialize the schema.

    Autouse so even tests that exercise repositories/executor directly (without
    an HTTP client + lifespan) have a real, isolated SQLite database.
    """
    monkeypatch.setenv("BACKUP_UI_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BACKUP_UI_LOG_DIR", str(tmp_path / "logs"))
    import app.db as _db

    _db.init_db()


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Return a factory producing a fully-configured TestClient context."""

    @contextmanager
    def _make(**env_overrides):
        state = tmp_path / "state"
        logs = tmp_path / "logs"
        monkeypatch.setenv("BACKUP_UI_STATE_DIR", str(state))
        monkeypatch.setenv("BACKUP_UI_LOG_DIR", str(logs))
        monkeypatch.setenv("BACKUP_UI_HOST", "0.0.0.0")
        monkeypatch.setenv("BACKUP_UI_PORT", "8000")
        for key, value in env_overrides.items():
            monkeypatch.setenv(key, value)
        app_main = importlib.import_module("app.main")
        importlib.reload(app_main)
        app = app_main.create_app()
        with TestClient(app, follow_redirects=False) as client:
            yield client

    return _make


@pytest.fixture
def client(make_client):
    with make_client() as c:
        yield c


@pytest.fixture
def auth_token(client):
    """Perform a GET so the CSRF cookie is set, then return the token."""
    client.get("/")
    return client.cookies.get("csrf_token")


@pytest.fixture
def csrf_headers(auth_token):
    """Headers that satisfy the CSRF double-submit + same-origin check."""
    return {"X-CSRF-Token": auth_token}


@pytest.fixture
def backup_dirs(tmp_path):
    """Create a source tree with files and an empty destination directory."""
    import os

    src = tmp_path / "source"
    dest = tmp_path / "dest"
    (src / "keep").mkdir(parents=True)
    (src / "keep" / "a.txt").write_text("alpha")
    (src / "keep" / "b.txt").write_text("beta")
    (src / "skipme").mkdir()
    (src / "skipme" / "hidden.txt").write_text("hidden")
    (src / "top.txt").write_text("top-level")
    dest.mkdir()
    return {"src": str(src), "dest": str(dest)}

