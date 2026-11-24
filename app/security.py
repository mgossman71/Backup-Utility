"""CSRF and same-origin protection.

The dashboard intentionally ships without built-in authentication because it is
meant to be bound to a trusted network (see the architecture and README). To
still defend mutating actions against cross-site request forgery we use a
double-submit cookie paired with an explicit token submitted in the request, and
we reject requests whose ``Origin``/``Referer`` host does not match the request
host.

Every mutating route must call :func:`verify_csrf` before performing writes.
"""

from __future__ import annotations

import hmac
import secrets
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from . import config

CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "csrf_token"


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _origin_host(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    netloc = parsed.netloc or parsed.path
    return netloc.lower()


def same_origin(request: Request) -> bool:
    """Return True when Origin/Referer matches the request host.

    Requests with no Origin and no Referer are treated as same-origin (simple
    top-level navigations do not always send them); CSRF token validation still
    applies to those.
    """
    if not config.require_same_origin():
        return True
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return True
    request_host = request.headers.get("host", "").lower()
    return _origin_host(origin) == request_host


def _submitted_token(request: Request, form_token: str | None) -> str | None:
    header_token = request.headers.get(CSRF_HEADER)
    return header_token or form_token


def verify_csrf(request: Request, form_token: str | None = None) -> None:
    """Raise HTTP 403 unless the request is same-origin and carries a valid token.

    ``form_token`` is the value parsed from the submitted form, if any. A token
    may also be supplied through the ``X-CSRF-Token`` header (used by HTMX/JS).
    """
    if not same_origin(request):
        raise HTTPException(
            status_code=403,
            detail="Cross-origin request rejected.",
        )
    cookie_token = request.cookies.get(CSRF_COOKIE)
    submitted = _submitted_token(request, form_token)
    if not cookie_token or not submitted:
        raise HTTPException(
            status_code=403,
            detail="Missing CSRF token. Reload the page and try again.",
        )
    if not hmac.compare_digest(cookie_token, submitted):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token. Reload the page and try again.",
        )
