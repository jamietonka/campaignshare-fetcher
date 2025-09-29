from __future__ import annotations
import datetime as dt
from typing import Any


def parse_since(val: Any | None) -> float | None:
    """Return epoch seconds or None. Accepts float/int, numeric str, or YYYY-MM-DD."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    try:
        return float(s)  # numeric string
    except Exception:
        pass
    try:
        y, m, d = map(int, s.split("-"))
        return dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()
    except Exception:
        return None
