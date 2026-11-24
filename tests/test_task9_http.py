"""Task 9 acceptance: dashboard, job editor, detail, HTML validation re-render."""

from __future__ import annotations


def _form(client):
    # First navigation sets the csrf_token cookie (double-submit).
    if not client.cookies.get("csrf_token"):
        client.get("/")
    return {"csrf_token": client.cookies.get("csrf_token")}


def test_dashboard_renders_empty_state(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Unix Backup Jobs You Can Trust" in r.text
    assert "No backup jobs yet" in r.text


def test_dashboard_lists_created_job(client, tmp_path):
    src, dst = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    r = client.post("/jobs", data={**_form(client), "name": "Prod", "source_path": str(src), "dest_root": str(dst)})
    assert r.status_code == 303
    r = client.get("/jobs")
    assert "Prod" in r.text
    assert str(src) in r.text


def test_job_new_renders_editor(client):
    r = client.get("/jobs/new")
    assert r.status_code == 200
    assert "Create Backup Job" in r.text
    assert "Save Job" in r.text
    assert 'name="csrf_token"' in r.text


def test_html_validation_re_renders_form_with_error(client, tmp_path):
    dst = tmp_path / "d"
    dst.mkdir()
    bad = str(tmp_path / "nope")
    r = client.post(
        "/jobs",
        headers={"Accept": "text/html"},
        data={**_form(client), "name": "Bad", "source_path": bad, "dest_root": str(dst)},
    )
    assert r.status_code == 422
    assert "Source path does not exist" in r.text  # server error shown
    assert 'value="' + bad + '"' in r.text  # offending field repopulated
    assert "Create Backup Job" in r.text  # still the editor, not a bare JSON blob


def test_job_detail_and_edit(client, tmp_path):
    src, dst = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    r = client.post(
        "/jobs",
        data={**_form(client), "name": "Detail", "source_path": str(src), "dest_root": str(dst), "schedule_cron": "0 2 * * *"},
    )
    loc = r.headers["location"]
    r = client.get(loc)
    assert r.status_code == 200
    assert "Detail" in r.text
    assert "Every day at 2:00 AM" in r.text  # human-readable schedule, not raw cron
    edit = client.get(loc + "/edit")
    assert edit.status_code == 200
    assert 'value="' + str(src) + '"' in edit.text


def test_delete_via_post_removes_job(client, tmp_path):
    src, dst = tmp_path / "s", tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    r = client.post("/jobs", data={**_form(client), "name": "Del", "source_path": str(src), "dest_root": str(dst)})
    jid = r.headers["location"].rsplit("/", 1)[-1]
    r = client.post(f"/jobs/{jid}/delete", headers={"Accept": "text/html"}, data=_form(client))
    assert r.status_code == 303
    assert client.get(f"/jobs/{jid}").status_code == 404
