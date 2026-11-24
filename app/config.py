"""Runtime configuration for MountGuard Backup.

All paths and bind settings are read from the environment on every access so
tests and deployments can override them without importing-time side effects.
Defaults follow the architecture spec: bind 0.0.0.0:8009, state under
``/var/lib/backup-ui``, logs under ``/var/log/backup-ui``.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8009
DEFAULT_STATE_DIR = "/var/lib/backup-ui"
DEFAULT_LOG_DIR = "/var/log/backup-ui"
DEFAULT_TIMEZONE = "America/Chicago"

# When a privileged default path (e.g. /var/lib/...) is not writable, fall back
# to a project-local directory so the dashboard still starts for development.
FALLBACK_STATE_DIR = "./data"
FALLBACK_LOG_DIR = "./logs"


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _resolve_dir(name: str, default: str, fallback: str) -> Path:
    """Resolve a directory path, preferring the configured/default path.

    If neither the configured path nor the default is writable, fall back to a
    project-local directory so the application can still start without root
    privileges during development.
    """
    candidates: list[str] = []
    configured = os.environ.get(name)
    if configured:
        candidates.append(configured)
    candidates.append(default)
    # Only consider the fallback when the caller did not explicitly configure
    # an (unwritable) directory; explicit configuration should surface errors.
    if not configured:
        candidates.append(fallback)

    last_error: Exception | None = None
    for candidate in candidates:
        path = Path(candidate).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Validate writability by creating a sentinel file.
            probe = path / ".writeable-probe"
            probe.write_text("ok")
            probe.unlink()
            return path
        except OSError as exc:  # pragma: no cover - depends on host perms
            last_error = exc
            continue
    # If nothing worked, return the first candidate and let callers raise.
    assert last_error is not None
    raise last_error


def host() -> str:
    return _env("BACKUP_UI_HOST", DEFAULT_HOST)


def port() -> int:
    return int(_env("BACKUP_UI_PORT", str(DEFAULT_PORT)))


def state_dir() -> Path:
    return _resolve_dir("BACKUP_UI_STATE_DIR", DEFAULT_STATE_DIR, FALLBACK_STATE_DIR)


def log_dir() -> Path:
    return _resolve_dir("BACKUP_UI_LOG_DIR", DEFAULT_LOG_DIR, FALLBACK_LOG_DIR)


def db_path() -> Path:
    return state_dir() / "backup.db"


def default_timezone() -> str:
    return _env("BACKUP_UI_TIMEZONE", DEFAULT_TIMEZONE)


def max_runs_per_job() -> int:
    """Bounded run-history retention per job."""
    return int(_env("BACKUP_UI_MAX_RUNS", "50"))


def log_max_bytes() -> int:
    """Maximum bytes retained per run log file."""
    return int(_env("BACKUP_UI_LOG_MAX_BYTES", str(256 * 1024)))


def rsync_binary() -> str:
    """Path to the rsync executable used for all operations."""
    return _env("BACKUP_UI_RSYNC", "rsync")


def require_same_origin() -> bool:
    """Whether mutating requests must match the request Origin host."""
    return _env("BACKUP_UI_REQUIRE_SAME_ORIGIN", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
