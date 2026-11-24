"""Task 1 acceptance tests: host/health/root binding and CSRF protection."""

from __future__ import annotations

from fastapi import Request

from app import config, security


def test_health_returns_200(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_returns_200_without_auth(client):
    resp = client.get("/")
    assert resp.status_code == 200
    # No application-level auth challenge (no 401/403, no WWW-Authenticate).
    assert resp.status_code not in (401, 403)
    assert "WWW-Authenticate" not in resp.headers
    assert "text/html" in resp.headers["content-type"]


def test_default_bind_host_is_all_interfaces():
    # The default bind host must be 0.0.0.0 so LAN clients can reach the UI.
    import os

    os.environ.pop("BACKUP_UI_HOST", None)
    assert config.host() == "0.0.0.0"


def test_csrf_mismatched_origin_rejected(client):
    # Register a throwaway mutating route to exercise the CSRF helper.
    app = client.app

    from app.security import verify_csrf

    @app.post("/_csrf_probe")
    async def _probe(request: Request):
        verify_csrf(request, None)
        return {"ok": True}

    # 1) Mismatched Origin -> 403 even with a (would-be) valid token.
    resp = client.post(
        "/_csrf_probe",
        headers={"Origin": "http://evil.example", "X-CSRF-Token": "whatever"},
    )
    assert resp.status_code == 403, resp.text

    # 2) Same-origin but no token at all -> 403.
    resp = client.post("/_csrf_probe")
    assert resp.status_code == 403
