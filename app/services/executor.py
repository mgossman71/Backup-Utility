"""rsync backup/restore executor with per-job conflict lock and run logging.

Design notes:
  * Every run creates a persistent run record (status Running) before rsync is
    launched, so the UI and the conflict lock agree on what is in flight.
  * A per-job lock prevents a second run of the SAME job; a single global slot
    keeps only one backup/restore touching the disk at a time.
  * rsync is invoked as a subprocess ARGUMENT ARRAY (never through a shell).
"""

from __future__ import annotations

import os
import posixpath
import subprocess
import threading

from .. import config, repositories
from ..models import Run, now_iso
from . import rsync_stats


class ConflictError(Exception):
    pass


# --- in-flight registry -----------------------------------------------------
_lock = threading.Lock()
_running: dict[str, str] = {}                       # job_id -> run_id
_global_slot = threading.BoundedSemaphore(1)        # one operation at a time


def is_job_running(job_id: str) -> bool:
    with _lock:
        return job_id in _running


def try_reserve(job_id: str) -> bool:
    with _lock:
        if job_id in _running:
            return False
        _running[job_id] = ""
        return True


def release(job_id: str) -> None:
    with _lock:
        _running.pop(job_id, None)


# --- command construction ---------------------------------------------------
def build_command(
    *,
    source: str,
    dest: str,
    metadata: bool = True,
    checksum: bool = False,
    delete: bool = False,
    exclusions: list[str] | None = None,
) -> list[str]:
    args: list[str] = [config.rsync_binary()]
    if metadata:
        # -a already includes --owner --group --perms --links --times (--devices).
        args += ["-a", "-H", "--safe-links", "--keep-dirlinks"]
    else:
        args += ["-r", "-l", "-t", "-H", "--safe-links", "--keep-dirlinks"]
    if checksum:
        args.append("--checksum")
    args += ["-v", "--stats"]
    for pattern in exclusions or []:
        args.append("--exclude=" + pattern)
    if delete:
        args.append("--delete-after")
    # Copy *contents* of source into dest.
    args += [source.rstrip("/") + "/", dest.rstrip("/") + "/"]
    return args


def _log_path(run_id: str) -> str:
    return os.path.join(str(config.log_dir()), f"{run_id}.log")


def _ensure_dest(dest: str) -> str | None:
    """Create ``dest`` when missing but its parent is writable. Returns error."""
    if os.path.isdir(dest):
        return None
    parent = posixpath.dirname(dest.rstrip("/")) or "/"
    if os.path.isdir(parent) and os.access(parent, os.W_OK):
        try:
            os.makedirs(dest, exist_ok=True)
            return None
        except OSError as exc:
            return f"Could not create destination {dest}: {exc}"
    return f"Destination parent is not writable: {parent}"


def _run_rsync(command: list[str], log_file: str) -> tuple[int, str]:
    max_bytes = config.log_max_bytes()
    collected: list[str] = []
    with open(log_file, "w", encoding="utf-8") as fh:
        fh.write("$ " + " ".join(command) + "\n")
        fh.flush()
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            msg = (
                f"rsync executable not found ({config.rsync_binary()}). "
                "Install rsync on the host or set BACKUP_UI_RSYNC.\n"
            )
            fh.write(msg)
            return 127, msg
        written = 0
        truncated = False
        assert proc.stdout is not None
        for line in proc.stdout:
            fh.write(line)
            if written < max_bytes:
                collected.append(line)
            written += len(line)
            if written > max_bytes:
                proc.kill()
                truncated = True
                break
        exit_code = proc.wait()
        if truncated:
            fh.write("\n[log truncated at size limit]\n")
    return exit_code, "".join(collected)


def _finalize(run: Run, exit_code: int, output: str, log_file: str) -> Run:
    stats = rsync_stats.parse_stats(output)
    run.exit_code = exit_code
    run.finished_at = now_iso()
    run.stats = stats
    run.log_path = log_file
    if exit_code == 0:
        run.status = "success"
        transferred = stats.get("files_transferred")
        run.message = (
            f"Completed; {transferred} file(s) transferred"
            if transferred is not None
            else "Completed successfully"
        )
    else:
        run.status = "failure"
        err_lines = [ln for ln in output.splitlines() if ln.strip()]
        tail = err_lines[-1] if err_lines else "no output"
        run.message = (
            f"rsync failed (exit {exit_code}): {tail}. "
            "Check that the source exists and the destination is writable."
        )
    return repositories.update_run(run)


def execute(run: Run, *, metadata: bool, checksum: bool, delete: bool,
            exclusions: list[str]) -> Run:
    """Run rsync to completion synchronously, persisting status + log."""
    log_file = _log_path(run.id)
    command = build_command(
        source=run.source_path,
        dest=run.destination_path,
        metadata=metadata,
        checksum=checksum,
        delete=delete,
        exclusions=exclusions,
    )
    err = _ensure_dest(run.destination_path)
    if err:
        with open(log_file, "w", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(command) + "\n")
            fh.write(err + "\n")
        run.exit_code = 1
        run.message = err
        run.log_path = log_file
        run.finished_at = now_iso()
        run.status = "failure"
        return repositories.update_run(run)
    exit_code, output = _run_rsync(command, log_file)
    return _finalize(run, exit_code, output, log_file)


def request_run(job, *, operation: str = "backup", override_dest: str | None = None,
                override_delete: bool | None = None, background: bool = True) -> Run:
    """Create a run and (by default) execute it on a background thread.

    Raises :class:`ConflictError` if the job is already running (no second rsync
    process is started).
    """
    if not try_reserve(job.id):
        raise ConflictError(f"Job '{job.name}' is already running.")

    if operation == "restore":
        source = job.dest_path()
        dest = override_dest or job.source_path
    else:
        source = job.source_path
        dest = override_dest or job.dest_path()

    run = Run(
        id=repositories.new_id(),
        job_id=job.id,
        operation=operation,
        source_path=source,
        destination_path=dest,
        status="running",
        started_at=now_iso(),
        message="Delete mode active" if job.delete_mode else None,
    )
    repositories.insert_run(run)

    delete = job.delete_mode if override_delete is None else override_delete

    def _worker():
        try:
            _global_slot.acquire()
            execute(
                run,
                metadata=job.metadata_mode,
                checksum=job.checksum_mode,
                delete=delete,
                exclusions=job.exclusions,
            )
        finally:
            try:
                _global_slot.release()
            finally:
                release(job.id)

    if background:
        threading.Thread(target=_worker, daemon=True).start()
    else:
        _worker()
    return run
