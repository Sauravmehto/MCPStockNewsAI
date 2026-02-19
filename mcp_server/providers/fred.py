"""FRED adapter."""

from __future__ import annotations

from urllib.parse import urlencode

from mcp_server.providers.http import fetch_json


class FredClient:
    def __init__(self, api_key: str, timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.base = "https://api.stlouisfed.org/fred/series/observations"

    def get_series(self, series_id: str, limit: int = 12) -> list[dict[str, str]] | None:
        params = urlencode(
            {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": max(1, limit),
            }
        )
        url = f"{self.base}?{params}"
        data = fetch_json(url, provider="fred", timeout_seconds=self.timeout_seconds)
        observations = (data or {}).get("observations") if isinstance(data, dict) else None
        if not isinstance(observations, list):
            return None
        out: list[dict[str, str]] = []
        for item in observations:
            if not isinstance(item, dict):
                continue
            out.append({"date": str(item.get("date") or ""), "value": str(item.get("value") or "")})
        return out or None


