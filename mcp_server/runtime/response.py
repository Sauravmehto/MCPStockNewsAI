"""Response shaping helpers for production MCP tools."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, is_dataclass
from typing import Any

from mcp_server.services.base import ServiceResult

DISCLAIMER = "Data is for informational purposes only and does not constitute financial advice."
DEFAULT_LICENSE = "Provider terms apply"


def _convert_data(data: Any) -> Any:
    if is_dataclass(data):
        return asdict(data)
    if isinstance(data, list):
        return [_convert_data(item) for item in data]
    if isinstance(data, dict):
        return {key: _convert_data(value) for key, value in data.items()}
    return data


def _freshness(fetched_at: float | None) -> dict[str, Any]:
    ts = fetched_at or time.time()
    age_seconds = max(0.0, time.time() - ts)
    return {"timestamp": int(ts), "age_seconds": round(age_seconds, 3)}


def success_response(result: ServiceResult[Any]) -> str:
    payload: dict[str, Any] = {
        "data": _convert_data(result.data),
        "data_freshness": _freshness(result.fetched_at),
        "disclaimer": DISCLAIMER,
        "data_provider": result.data_provider or result.source or "unknown",
        "data_license": result.data_license or DEFAULT_LICENSE,
    }
    if result.source:
        payload["source"] = result.source
    if result.warning:
        payload["warning"] = result.warning
    return json.dumps(payload, ensure_ascii=True)


def error_response(code: str, message: str) -> str:
    return json.dumps(
        {
            "error": True,
            "code": code,
            "message": message,
            "timestamp": int(time.time()),
        },
        ensure_ascii=True,
    )


