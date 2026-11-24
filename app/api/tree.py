"""Lazy directory browse API (GET /api/tree)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .. import fs

router = APIRouter()


@router.get("/api/tree")
def browse(path: str = Query(default="/")):
    """Return only the immediate children of ``path``.

    Large directories load one level at a time. There is no source-root
    allowlist: any path visible to the (root) process may be browsed.
    """
    try:
        return fs.list_children(path)
    except fs.FsError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": str(exc), "path": path},
        )
