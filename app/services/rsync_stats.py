"""Parse ``rsync --stats`` output into a normalized dict.

Supports both GNU rsync and BSD/openrsync phrasings so transfer counts are
available on every platform.
"""

from __future__ import annotations

import re

_INT = re.compile(r"[-+]?\d[\d,]*")


def _to_int(text: str) -> int | None:
    m = _INT.search(text)
    if not m:
        return None
    return int(m.group(0).replace(",", ""))


# Each key -> list of accepted (case-insensitive) label substrings.
_LABELS = {
    "files_transferred": [
        "number of regular files transferred",
        "number of files transferred",
    ],
    "files_total": [
        "number of files:",
    ],
    "bytes_transferred": [
        "total transferred file size",
    ],
    "bytes_total": [
        "total file size",
    ],
    "total_sent": ["total bytes sent", "total sent"],
    "total_received": ["total bytes received", "total received"],
}


def parse_stats(output: str) -> dict:
    result: dict = {}
    for line in output.splitlines():
        low = line.lower().strip()
        if ":" not in low:
            continue
        label, _, value = low.partition(":")
        label = label.strip()
        for key, matches in _LABELS.items():
            if key in result:
                continue
            for cand in matches:
                if label == cand.rstrip(":") or label == cand or label.startswith(cand.rstrip(":")):
                    num = _to_int(value)
                    if num is not None:
                        result[key] = num
                    break
    # "Number of files:" must not be confused with "transferred"; guard order.
    if "files_total" in result and "files_transferred" not in result:
        # Some rsync builds only emit total; leave transferred absent.
        pass
    return result


def transferred_files(stats: dict) -> int | None:
    return stats.get("files_transferred")
