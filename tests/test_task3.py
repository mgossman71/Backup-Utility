"""Task 3 acceptance tests: lazy one-level directory browse API."""

from __future__ import annotations

import os

from app import fs


def test_root_returns_direct_children_only(client):
    resp = client.get("/api/tree", params={"path": "/"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == "/"
    assert data["parent"] is None
    assert len(data["children"]) > 0
    # Every child must be exactly one level below "/" (no recursion).
    for child in data["children"]:
        rel = child["path"].lstrip("/")
        assert "/" not in rel  # single path segment


def test_nested_directory_is_not_recursed(tmp_path, client):
    root = tmp_path / "browse"
    (root / "alpha").mkdir(parents=True)
    (root / "alpha" / "deep_child").write_text("x")
    (root / "beta.txt").write_text("hello")

    resp = client.get("/api/tree", params={"path": str(root)})
    assert resp.status_code == 200
    names = {c["name"] for c in resp.json()["children"]}
    assert names == {"alpha", "beta.txt"}
    # "deep_child" must NOT appear: only one level is enumerated.
    assert "deep_child" not in names
    # The directory child is marked as dir; the file as file with size.
    alpha = next(c for c in resp.json()["children"] if c["name"] == "alpha")
    assert alpha["kind"] == "dir"
    beta = next(c for c in resp.json()["children"] if c["name"] == "beta.txt")
    assert beta["kind"] == "file"
    assert beta["size"] == 5


def test_arbitrary_host_path_outside_allowlist_succeeds(tmp_path, client):
    # No configured allowlist: any accessible path resolves fine.
    resp = client.get("/api/tree", params={"path": str(tmp_path)})
    assert resp.status_code == 200
    assert resp.json()["path"] == str(os.path.abspath(tmp_path))


def test_missing_directory_returns_404(client, tmp_path):
    resp = client.get("/api/tree", params={"path": str(tmp_path / "nope")})
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_non_directory_returns_4xx(client, tmp_path):
    a_file = tmp_path / "plain.txt"
    a_file.write_text("data")
    resp = client.get("/api/tree", params={"path": str(a_file)})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_unreadable_directory_returns_403(client, tmp_path):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return  # root bypasses POSIX mode bits; skip in privileged CI
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "secret").write_text("x")
    os.chmod(locked, 0o000)
    try:
        resp = client.get("/api/tree", params={"path": str(locked)})
        assert resp.status_code == 403
        assert "error" in resp.json()
    finally:
        os.chmod(locked, 0o755)


def test_within_helper():
    assert fs.is_within("/data/sub", "/data") is True
    assert fs.is_within("/data", "/data") is True
    assert fs.is_within("/other", "/data") is False
