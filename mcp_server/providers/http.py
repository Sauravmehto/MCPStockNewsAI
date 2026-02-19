"""HTTP utilities and normalized provider errors."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

import requests

from mcp_server.providers.models import ProviderName

ProviderErrorCode = Literal["RATE_LIMIT", "AUTH", "NOT_FOUND", "UPSTREAM", "NETWORK", "BAD_RESPONSE"]


@dataclass
class ProviderError(Exception):
    provider: ProviderName
    code: ProviderErrorCode
    message: str
    status: int | None = None

    def __str__(self) -> str:
        return self.message


def map_status_to_code(status: int) -> ProviderErrorCode:
    if status in {401, 403}:
        return "AUTH"
    if status == 404:
        return "NOT_FOUND"
    if status == 429:
        return "RATE_LIMIT"
    return "UPSTREAM"


def fetch_json(
    url: str,
    provider: ProviderName,
    timeout_seconds: float = 15.0,
    headers: dict[str, str] | None = None,
) -> Any:
    """Fetch JSON with uniform provider/network error mapping."""

    try:
        response = requests.get(url, timeout=timeout_seconds, headers=headers)
    except requests.RequestException as error:
        raise ProviderError(provider, "NETWORK", f"Provider request failed: {error}") from error

    raw = response.text or ""
    parsed: Any = {}
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderError(
                provider,
                "BAD_RESPONSE",
                "Provider returned non-JSON content.",
                response.status_code,
            ) from error

    if not response.ok:
        raise ProviderError(
            provider,
            map_status_to_code(response.status_code),
            f"Provider request failed with status {response.status_code}.",
            response.status_code,
        )

    return parsed


