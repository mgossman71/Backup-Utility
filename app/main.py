"""Application entry point and FastAPI wiring for MountGuard Backup.

The app binds to ``0.0.0.0`` by default and exposes an unauthenticated dashboard
intended for a trusted network. Mutating routes are protected by CSRF + same
origin checks (see :mod:`app.security`).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .security import CSRF_COOKIE, generate_csrf_token
from .templating import BASE_DIR, configure, render

logger = logging.getLogger("backup-ui")


def _ensure_dirs() -> None:
    try:
        config.state_dir()
        config.log_dir()
    except OSError as exc:  # pragma: no cover - host perms dependent
        logger.warning("Could not create default state/log directories: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_dirs()
    from . import db
    from .services import scheduler as sched

    db.init_db()
    try:
        sched.start()
    except Exception as exc:  # pragma: no cover - scheduler should not block startup
        logger.warning("Scheduler failed to start: %s", exc)
    try:
        yield
    finally:
        sched.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MountGuard Backup",
        description="Unix backup operations dashboard.",
        lifespan=lifespan,
    )

    configure(app)

    # --- CSRF double-submit cookie -----------------------------------------
    @app.middleware("http")
    async def csrf_cookie_middleware(request: Request, call_next):
        token = request.cookies.get(CSRF_COOKIE) or generate_csrf_token()
        request.state.csrf_token = token
        response = await call_next(request)
        if request.cookies.get(CSRF_COOKIE) != token:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                httponly=False,  # readable by JS to attach X-CSRF-Token header
                samesite="lax",
                secure=False,    # trusted-network deployment; set via proxy TLS
                path="/",
            )
        return response

    # --- Static assets ------------------------------------------------------
    static_dir = BASE_DIR / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # --- API / feature routers ---------------------------------------------
    from .api import tree as tree_api
    from .routes import jobs as jobs_routes
    from .routes import runs as runs_routes

    app.include_router(tree_api.router)
    app.include_router(jobs_routes.router)
    app.include_router(runs_routes.router)

    # --- Core routes --------------------------------------------------------
    @app.get("/health", include_in_schema=False)
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/settings", response_class=HTMLResponse)
    async def settings(request: Request):
        return render(request, "settings.html", {"nav": "settings"})

    return app


app = create_app()
