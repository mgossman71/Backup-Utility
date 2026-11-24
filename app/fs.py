"""Filesystem helpers shared by the browse API and job validation.

All listing is single-level (``os.scandir``) so the UI can navigate huge trees
one directory at a time without recursive scans.
"""

from __future__ import annotations

import os


class FsError(Exception):
    """Base class for filesystem browse/validation errors with a status code."""

    status_code = 400


class PathNotFound(FsError):
    status_code = 404


class NotADirectory(FsError):
    status_code = 400


class NotReadable(FsError):
    status_code = 403


def _kind(entry: os.DirEntry) -> str:
    try:
        if entry.is_symlink():
            return "symlink"
        if entry.is_dir(follow_symlinks=False):
            return "dir"
        return "file"
    except OSError:
        return "file"


def list_children(raw_path: str) -> dict:
    """Return one directory level: {path, parent, children:[...]}.

    Raises :class:`PathNotFound`, :class:`NotADirectory`, or
    :class:`NotReadable` with an actionable message.
    """
    if not raw_path or not str(raw_path).strip():
        raise PathNotFound("A directory path is required.")
    path = os.path.abspath(raw_path)
    if not os.path.exists(path):
        raise PathNotFound(f"Path does not exist: {path}")
    if not os.path.isdir(path):
        raise NotADirectory(f"Not a directory: {path}")

    entries: list[dict] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                item = {"name": entry.name, "kind": _kind(entry), "error": None}
                item["path"] = os.path.join(path, entry.name)
                try:
                    st = entry.stat(follow_symlinks=False)
                    item["size"] = st.st_size
                    item["mtime"] = st.st_mtime
                except OSError as exc:
                    item["size"] = None
                    item["mtime"] = None
                    item["error"] = str(exc)
                # Accessibility reflects the process credentials (root by design).
                try:
                    item["readable"] = os.access(item["path"], os.R_OK)
                    item["writable"] = os.access(item["path"], os.W_OK)
                except OSError:
                    item["readable"] = False
                    item["writable"] = False
                entries.append(item)
    except PermissionError:
        raise NotReadable(f"Directory is not readable: {path}")
    except OSError as exc:
        raise NotReadable(f"Could not list directory {path}: {exc}")

    entries.sort(key=lambda e: (e["kind"] != "dir", e["name"].lower()))
    parent = os.path.dirname(path) or None
    if parent == path:  # reached filesystem root
        parent = None
    return {"path": path, "parent": parent, "children": entries}


def is_existing_dir(path: str) -> bool:
    return bool(path) and os.path.isdir(path)


def is_writable_dir(path: str) -> bool:
    return is_existing_dir(path) and os.access(path, os.W_OK)


def can_create_under(path: str) -> bool:
    """True when *path* is missing but its nearest existing parent is writable."""
    if os.path.isdir(path):
        return False
    parent = os.path.dirname(path)
    while parent and not os.path.isdir(parent):
        parent = os.path.dirname(parent)
    if not parent:
        return False
    return os.access(parent, os.W_OK)


def is_within(child: str, parent: str) -> bool:
    """Return True when ``child`` is equal to or inside ``parent``."""
    child = os.path.abspath(child)
    parent = os.path.abspath(parent)
    return child == parent or child.startswith(parent.rstrip("/") + os.sep)
