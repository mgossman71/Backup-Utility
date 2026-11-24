"""Task 7 (HTTP): Run Now status transitions, conflict lock, log endpoint.

A deterministic fake rsync sleeps so the run stays 'running', letting us assert
that a second run-now is rejected as a conflict and that only ONE rsync process
is ever started for the job.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app import repositories
from app.models import Job
from app.services import executor


def _fake_rsync(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    rs = bin_dir / "rsync"
    counter = tmp_path / "counter.log"
    rs.write_text(
        "#!/bin/sh\n"
        'echo start >> "$RSYNC_COUNTER"\n'
        "sleep 0.4\n"
        "echo 'Number of files: 2'\n"
        "echo 'Number of files transferred: 0'\n"
        "echo 'Total file size: 10 B'\n"
        "exit 0\n"
    )
    os.chmod(rs, 0o755)
    return str(rs), str(counter)


def _wait_until(predicate, timeout=4.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def test_run_now_success_and_conflict_lock(make_client, tmp_path, monkeypatch):
    rs, counter = _fake_rsync(tmp_path)
    monkeypatch.setenv("RSYNC_COUNTER", counter)
    src = tmp_path / "s"
    dst = tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("x")

    with make_client(BACKUP_UI_RSYNC=rs) as client:
        client.get("/")
        token = client.cookies.get("csrf_token")
        job = repositories.create_job(
            Job(
                id=repositories.new_id(),
                name="C",
                source_path=str(src),
                dest_root=str(dst),
                enabled=False,
            )
        )
        # 1) Start a run.
        r1 = client.post(f"/jobs/{job.id}/run", headers={"X-CSRF-Token": token}, data={})
        assert r1.status_code == 202, r1.text
        run_id = r1.json()["run_id"]

        # 2) Wait until the fake rsync actually launched.
        assert _wait_until(lambda: os.path.exists(counter) and os.path.getsize(counter) > 0)

        # 3) A second run-now is a conflict.
        r2 = client.post(f"/jobs/{job.id}/run", headers={"X-CSRF-Token": token}, data={})
        assert r2.status_code == 409

        # 4) Let the first finish; exactly ONE rsync invocation happened.
        assert _wait_until(lambda: (repositories.get_run(run_id) or _dummy()).status != "running")
        invocations = len([l for l in Path(counter).read_text().splitlines() if l.strip()])
        assert invocations == 1

        final = repositories.get_run(run_id)
        assert final.status == "success"
        assert final.exit_code == 0

    # The job lock is released after completion.
    assert not executor.is_job_running(job.id)


def _dummy():
    class R:
        status = "running"

    return R()


def test_run_log_endpoint_and_detail(make_client, tmp_path):
    src = tmp_path / "s"
    dst = tmp_path / "d"
    src.mkdir()
    dst.mkdir()
    (src / "a.txt").write_text("hello")
    with make_client() as client:
        client.get("/")
        token = client.cookies.get("csrf_token")
        job = repositories.create_job(
            Job(id=repositories.new_id(), name="L", source_path=str(src), dest_root=str(dst), enabled=False)
        )
        r1 = client.post(f"/jobs/{job.id}/run", headers={"X-CSRF-Token": token}, data={})
        run_id = r1.json()["run_id"]
        assert _wait_until(lambda: (repositories.get_run(run_id) or _dummy()).status != "running")

        log = client.get(f"/runs/{run_id}/log")
        assert log.status_code == 200
        assert "rsync" in log.text
        assert job.source_path in log.text

        detail = client.get(f"/runs/{run_id}")
        assert detail.status_code == 200
        assert "Run Log" in detail.text
        assert "Success" in detail.text  # approved status label rendered
