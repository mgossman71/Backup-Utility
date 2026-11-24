"""Shared request body parsing for HTML form posts (urlencoded or multipart)."""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import Request


async def parse_form(request: Request) -> dict:
    ctype = request.headers.get("content-type", "")
    if "multipart/form-data" in ctype or "application/x-www-form-urlencoded" not in ctype:
        try:
            form = await request.form()
            data: dict = {}
            for key in form.keys():
                values = form.getlist(key)
                data[key] = values if len(values) > 1 else values[0]
            return data
        except Exception:
            pass
    body = (await request.body()).decode("utf-8", "replace")
    parsed = parse_qs(body, keep_blank_values=True)
    return {k: (v if len(v) > 1 else v[0]) for k, v in parsed.items()}


def form_token(data: dict) -> str | None:
    value = data.get("csrf_token")
    return value if isinstance(value, str) else None
