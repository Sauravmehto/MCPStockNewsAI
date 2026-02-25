"""Time helpers for MCP prompt argument scaffolding."""

from __future__ import annotations

import time


def get_unix_range(days_back: int) -> dict[str, int]:
    """Return unix second range for now and now-days_back days."""
    bounded_days = max(1, min(int(days_back), 3650))
    to_unix = int(time.time())
    from_unix = to_unix - bounded_days * 24 * 60 * 60
    return {"from_unix": from_unix, "to_unix": to_unix}


