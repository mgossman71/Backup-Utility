"""Job routes: pages (dashboard, editor, detail) + CRUD (all mutating CSRF-safe)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .. import repositories, views
from ..security import verify_csrf
from ..services import job_service, schedule, scheduler
from ..services.job_service import JobValidationError
from ..services.timezones import TIMEZONE_OPTIONS
from ..templating import render
from ..webforms import form_token, parse_form

router = APIRouter()


def _form_response(request, *, job, data, exc, is_new):
    """Re-render the job editor with the offending field flagged (HTML path)."""
    values = views.form_values(job, data)
    return render(
        request,
        "job_form.html",
        {
            "nav": "new" if is_new else "jobs",
            "job": job,
            "is_new": is_new,
            "values": values,
            "timezone_options": TIMEZONE_OPTIONS,
            "interval_unit_options": schedule.INTERVAL_UNITS,
            "next_run": views.next_run_view(job) if job else "",
            "error": exc.message,
            "error_field": exc.field,
        },
        status_code=422,
    )


def _wants_html(request) -> bool:
    return "text/html" in request.headers.get("accept", "")


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@router.get("/")
async def dashboard(request: Request):
    ctx = views.dashboard_context()
    ctx["nav"] = "dashboard"
    return render(request, "dashboard.html", ctx)


@router.get("/jobs")
async def jobs_index(request: Request):
    ctx = views.dashboard_context()
    ctx["nav"] = "jobs"
    return render(request, "dashboard.html", ctx)


@router.get("/jobs/new")
async def job_new(request: Request):
    return render(
        request,
        "job_form.html",
        {
            "nav": "new",
            "job": None,
            "is_new": True,
            "values": views.form_values(None, None),
            "timezone_options": TIMEZONE_OPTIONS,
            "interval_unit_options": schedule.INTERVAL_UNITS,
            "next_run": "",
            "error": None,
            "error_field": None,
        },
    )


@router.get("/jobs/{job_id}")
async def job_detail(job_id: str, request: Request):
    job = repositories.get_job(job_id)
    if job is None:
        return render(request, "job_detail.html", {"job": None, "nav": "jobs"}, status_code=404)
    ctx = views.detail_context(job)
    ctx["nav"] = "jobs"
    return render(request, "job_detail.html", ctx)


@router.get("/jobs/{job_id}/edit")
async def job_edit(job_id: str, request: Request):
    job = repositories.get_job(job_id)
    if job is None:
        return RedirectResponse(url="/jobs", status_code=303)
    return render(
        request,
        "job_form.html",
        {
            "nav": "jobs",
            "job": job,
            "is_new": False,
            "values": views.form_values(job, None),
            "timezone_options": TIMEZONE_OPTIONS,
            "interval_unit_options": schedule.INTERVAL_UNITS,
            "next_run": views.next_run_view(job),
            "error": None,
            "error_field": None,
        },
    )


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------
@router.post("/jobs")
async def create_job(request: Request):
    data = await parse_form(request)
    verify_csrf(request, form_token(data))
    try:
        job = job_service.create_job(data)
    except JobValidationError as exc:
        if _wants_html(request):
            return _form_response(request, job=None, data=data, exc=exc, is_new=True)
        return JSONResponse(status_code=422, content={"error": exc.message, "field": exc.field})
    scheduler.register_job(job)
    return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)


@router.post("/jobs/{job_id}")
async def edit_job(job_id: str, request: Request):
    data = await parse_form(request)
    verify_csrf(request, form_token(data))
    try:
        job = job_service.update_job(job_id, data)
    except JobValidationError as exc:
        if _wants_html(request):
            return _form_response(request, job=repositories.get_job(job_id), data=data, exc=exc, is_new=False)
        return JSONResponse(status_code=422, content={"error": exc.message, "field": exc.field})
    scheduler.register_job(job)
    return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)


@router.post("/jobs/{job_id}/delete")
async def delete_job_post(job_id: str, request: Request):
    data = await parse_form(request)
    verify_csrf(request, form_token(data))
    scheduler.remove_job(job_id)
    # Deleting only the job record never touches source/destination files.
    repositories.delete_job(job_id)
    if _wants_html(request):
        return RedirectResponse(url="/jobs", status_code=303)
    return JSONResponse(status_code=200, content={"deleted": job_id})


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, request: Request):
    token = request.headers.get("X-CSRF-Token")
    if not token:
        data = await parse_form(request)
        token = form_token(data)
    verify_csrf(request, token)
    scheduler.remove_job(job_id)
    repositories.delete_job(job_id)
    return RedirectResponse(url="/", status_code=303)
