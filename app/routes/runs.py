"""Run routes: trigger a run, list runs, view a run and its log."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from .. import config, repositories
from ..security import verify_csrf
from ..services import executor
from ..templating import render
from ..webforms import form_token, parse_form

router = APIRouter()


@router.post("/jobs/{job_id}/run")
async def run_now(job_id: str, request: Request):
    data = await parse_form(request)
    verify_csrf(request, form_token(data))
    job = repositories.get_job(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found."})
    try:
        run = executor.request_run(job, operation="backup", background=True)
    except executor.ConflictError as exc:
        return JSONResponse(status_code=409, content={"error": str(exc)})
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url=f"/runs/{run.id}", status_code=303)
    return JSONResponse(
        status_code=202,
        content={"run_id": run.id, "status": run.status},
    )


@router.get("/jobs/{job_id}/runs")
async def job_runs(job_id: str):
    runs = repositories.list_runs_for_job(job_id, limit=config.max_runs_per_job())
    return [
        {
            "id": r.id,
            "operation": r.operation,
            "status": r.status,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "exit_code": r.exit_code,
            "stats": r.stats,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, request: Request):
    run = repositories.get_run(run_id)
    if run is None:
        return render(request, "run_detail.html", {"run": None, "nav": "jobs"}, status_code=404)
    log_lines = _read_log_lines(run.log_path)
    return render(request, "run_detail.html", {"run": run, "log_lines": log_lines, "nav": "jobs"})


@router.get("/runs/{run_id}/log")
async def run_log(run_id: str):
    run = repositories.get_run(run_id)
    if run is None or not run.log_path:
        return Response(content="", media_type="text/plain; charset=utf-8")
    try:
        text = open(run.log_path, "r", encoding="utf-8", errors="replace").read()
    except OSError:
        text = ""
    return Response(content=text, media_type="text/plain; charset=utf-8")


def _read_log_lines(path: str | None) -> list[dict]:
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return []
    lines = []
    for ln in raw.splitlines():
        cls = ""
        low = ln.lower()
        if ln.startswith("$ "):
            cls = "cmd"
        elif low.startswith("rsync:") or "error" in low:
            cls = "stderr"
        elif low.startswith(("number of", "total", "sent", "speedup", "file list")):
            cls = "stat"
        lines.append({"text": ln, "cls": cls})
    return lines
