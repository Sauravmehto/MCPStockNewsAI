"""Response formatting helpers."""

from __future__ import annotations

from datetime import datetime, timezone

FINANCIAL_DISCLAIMER = "Informational use only. This is not financial advice."


def _fmt_number(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}"


def _fmt_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def _fmt_date_from_unix(timestamp: int | None) -> str:
    if not timestamp:
        return "n/a"
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def format_response(
    title: str,
    lines: list[str],
    source: str | None = None,
    warning: str | None = None,
    include_disclaimer: bool = True,
) -> str:
    chunks: list[str] = [title]
    if source:
        chunks.append(f"Source: {source}")
    if warning:
        chunks.append(f"Warning: {warning}")
    chunks.extend(lines)
    if include_disclaimer:
        chunks.extend(["---", FINANCIAL_DISCLAIMER])
    return "\n".join(chunks)


def line_money(label: str, value: float | None) -> str:
    return f"{label}: ${_fmt_number(value)}"


def line_number(label: str, value: float | None, decimals: int = 2) -> str:
    return f"{label}: {_fmt_number(value, decimals)}"


def line_percent(label: str, value: float | None) -> str:
    return f"{label}: {_fmt_percent(value)}"


def line_date(label: str, timestamp: int | None) -> str:
    return f"{label}: {_fmt_date_from_unix(timestamp)}"


