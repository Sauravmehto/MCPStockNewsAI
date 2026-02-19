"""Shared tool-layer helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from mcp_server.services.base import ErrorEnvelope


def ensure_data(data: object | None, error: ErrorEnvelope | None, default_message: str = "No data returned.") -> object:
    if data is not None:
        return data
    if error:
        raise ValueError(f"[{error.code}] {error.message}")
    raise ValueError(default_message)


def format_news_line(idx: int, headline: str, source: str | None, timestamp: int | None, url: str | None) -> str:
    date = (
        datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        if timestamp
        else "unknown-date"
    )
    source_name = source or "unknown-source"
    link = f" ({url})" if url else ""
    return f"{idx}. [{date}] {headline} - {source_name}{link}"


