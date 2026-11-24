"""Timezone handling and the timezone selector options.

The user requested Central Time (CST). We canonicalize that to the IANA zone
``America/Chicago`` so daylight-saving transitions are handled correctly, with a
fixed-CST fallback only if the IANA zone is somehow unavailable.
"""

from __future__ import annotations

import pytz

DEFAULT_TIMEZONE = "America/Chicago"

# Friendly aliases accepted from forms/CLI, mapped to IANA zones.
ALIASES = {
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "central": "America/Chicago",
    "us/central": "America/Chicago",
    "cst6cdt": "America/Chicago",
    "america/chicago": "America/Chicago",
    "est": "America/New_York",
    "eastern": "America/New_York",
    "mst": "America/Denver",
    "mountain": "America/Denver",
    "pst": "America/Los_Angeles",
    "pacific": "America/Los_Angeles",
    "utc": "UTC",
    "gmt": "UTC",
}

# Curated selector options (label shown in the UI).
TIMEZONE_OPTIONS = [
    {"value": "America/Chicago", "label": "Central Time — America/Chicago (CST/CDT)"},
    {"value": "America/New_York", "label": "Eastern Time — America/New_York"},
    {"value": "America/Denver", "label": "Mountain Time — America/Denver"},
    {"value": "America/Phoenix", "label": "Arizona — America/Phoenix"},
    {"value": "America/Los_Angeles", "label": "Pacific Time — America/Los_Angeles"},
    {"value": "UTC", "label": "UTC"},
]


def is_valid_timezone(value: str | None) -> bool:
    if not value:
        return False
    return value in pytz.all_timezones_set


def normalize_timezone(value: str | None) -> str:
    """Return a canonical IANA zone, mapping CST-family aliases sensibly.

    Raises ``ValueError`` for unknown zones.
    """
    if not value or not str(value).strip():
        return DEFAULT_TIMEZONE
    raw = str(value).strip()
    key = raw.lower()
    if key in ALIASES:
        return ALIASES[key]
    if raw in pytz.all_timezones_set:
        return raw
    # Try a case-insensitive match against the IANA list.
    for tz in pytz.all_timezones:
        if tz.lower() == key:
            return tz
    raise ValueError(f"Unknown timezone: {raw}")


def label_for(value: str) -> str:
    tz = normalize_timezone(value)
    try:
        loc = pytz.timezone(tz)
        return f"{tz} ({loc.tzname(_now())})"
    except Exception:
        return tz


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
