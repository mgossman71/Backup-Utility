"""Job validation and persistence orchestration.

Centralizes the safety rules from the requirements:
  * empty/missing/unreadable source or unwritable destination are rejected;
  * a missing destination is allowed only when its parent is writable and the
    user explicitly confirms;
  * a destination inside the source requires explicit confirmation;
  * invalid cron or timezone are rejected (prevents save and enable);
  * delete mode is opt-in and requires confirmation.
"""

from __future__ import annotations

import os
import posixpath

from .. import fs, repositories
from ..models import Job
from . import schedule
from .timezones import normalize_timezone


class JobValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def _as_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "checked"}


def _parse_exclusions(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = str(value).replace("\r", "\n").split("\n")
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in items:
        item = str(raw).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def validate_and_build(data: dict, existing: Job | None = None) -> Job:
    """Validate raw form data and return a (unsaved) :class:`Job`.

    Raises :class:`JobValidationError` on the first failed rule.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise JobValidationError("A job name is required.", field="name")

    source_path = (data.get("source_path") or "").strip()
    if not source_path:
        raise JobValidationError("A source path is required.", field="source_path")
    if not fs.is_existing_dir(source_path):
        raise JobValidationError(
            f"Source path does not exist or is not a directory: {source_path}",
            field="source_path",
        )
    if not os.access(source_path, os.R_OK):
        raise JobValidationError(
            f"Source path is not readable by the backup process: {source_path}",
            field="source_path",
        )

    dest_root = (data.get("dest_root") or "").strip()
    if not dest_root:
        raise JobValidationError("A destination path is required.", field="dest_root")
    confirm_missing = _as_bool(data.get("confirm_missing_destination"))
    if fs.is_existing_dir(dest_root):
        if not os.access(dest_root, os.W_OK):
            raise JobValidationError(
                f"Destination path is not writable: {dest_root}", field="dest_root"
            )
    elif fs.can_create_under(dest_root):
        if not confirm_missing:
            raise JobValidationError(
                "Destination does not exist yet but its parent is writable. "
                "Confirm to create it on the next run.",
                field="confirm_missing_destination",
            )
    else:
        raise JobValidationError(
            f"Destination path is missing and its parent is not writable: {dest_root}",
            field="dest_root",
        )

    # Safety: warn when the destination is inside the source.
    if fs.is_within(dest_root, source_path):
        if not _as_bool(data.get("confirm_dest_inside_source")):
            raise JobValidationError(
                "The destination is inside the source. Confirm to proceed — "
                "this can copy a folder into itself.",
                field="confirm_dest_inside_source",
            )

    # Schedule + timezone.
    cron = (data.get("schedule_cron") or "").strip() or None
    try:
        schedule.validate_cron(cron)
    except schedule.CronError as exc:
        raise JobValidationError(str(exc), field="schedule_cron") from exc
    try:
        tz = normalize_timezone(data.get("timezone"))
    except ValueError as exc:
        raise JobValidationError(str(exc), field="timezone") from exc

    delete_mode = _as_bool(data.get("delete_mode"))
    if delete_mode and not _as_bool(data.get("confirm_delete_mode")):
        raise JobValidationError(
            "Delete mode removes files from the destination. Confirm Delete Mode "
            "to enable it.",
            field="confirm_delete_mode",
        )

    job = existing or Job(id=repositories.new_id(), name="", source_path="", dest_root="")
    job.name = name
    job.source_path = source_path.rstrip("/") or "/"
    job.dest_root = dest_root.rstrip("/") or "/"
    job.dest_name_override = (data.get("dest_name_override") or "").strip() or None
    job.enabled = _as_bool(data.get("enabled"), default=True)
    job.schedule_cron = cron
    job.timezone = tz
    job.delete_mode = delete_mode
    job.checksum_mode = _as_bool(data.get("checksum_mode"))
    job.metadata_mode = _as_bool(data.get("metadata_mode"), default=True)
    job.exclusions = _parse_exclusions(data.get("exclusions"))
    return job


def create_job(data: dict) -> Job:
    job = validate_and_build(data)
    return repositories.create_job(job)


def update_job(job_id: str, data: dict) -> Job:
    existing = repositories.get_job(job_id)
    if existing is None:
        raise JobValidationError("Job not found.", field="id")
    updated = validate_and_build(data, existing=existing)
    updated.id = job_id
    return repositories.update_job(updated)
