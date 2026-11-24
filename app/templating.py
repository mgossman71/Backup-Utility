"""Jinja2 setup and a render helper that injects shared context.

Shared context includes the approved copy deck, the active navigation key, the
CSRF token, and the application version, so every template can rely on them.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from . import copy as copy_module
from .security import CSRF_COOKIE

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def configure(app: FastAPI) -> None:
    """Register template globals/filters on the shared Jinja environment."""
    env = templates.env
    env.globals["copy"] = copy_module.COPY
    env.globals["brand_name"] = copy_module.BRAND_NAME


def render(
    request: Request,
    name: str,
    context: dict | None = None,
    *,
    status_code: int = 200,
):
    ctx: dict = dict(context or {})
    ctx.setdefault("nav", ctx.get("nav", ""))
    ctx.setdefault("copy", copy_module.COPY)
    ctx.setdefault("brand_name", copy_module.BRAND_NAME)
    ctx.setdefault("csrf_token", request.state.csrf_token)
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)
