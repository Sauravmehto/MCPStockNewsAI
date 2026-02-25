"""HTTP utilities and normalized provider errors."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Literal

import requests
from requests.adapters import HTTPAdapter

from mcp_server.providers.models import ProviderName

ProviderErrorCode = Literal["RATE_LIMIT", "AUTH", "NOT_FOUND", "UPSTREAM", "NETWORK", "BAD_RESPONSE"]
TRANSIENT_CODES = {408, 425, 429, 500, 502, 503, 504}

_SESSION = requests.Session()
_SESSION.mount("https://", HTTPAdapter(pool_connections=50, pool_maxsize=100))
_SESSION.mount("http://", HTTPAdapter(pool_connections=50, pool_maxsize=100))


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
    max_retries: int = 3,
) -> Any:
    """Fetch JSON with uniform provider/network error mapping."""
    attempts = max(1, max_retries)
    last_error: ProviderError | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = _SESSION.get(url, timeout=timeout_seconds, headers=headers)
        except requests.RequestException as error:
            mapped = ProviderError(provider, "NETWORK", "Provider request failed due to network error.")
            last_error = mapped
            if attempt < attempts:
                time.sleep(0.25 * (2 ** (attempt - 1)))
                continue
            raise mapped from error

        raw = response.text or ""
        parsed: Any = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as error:
                mapped = ProviderError(
                    provider,
                    "BAD_RESPONSE",
                    "Provider returned non-JSON content.",
                    response.status_code,
                )
                last_error = mapped
                if response.status_code in TRANSIENT_CODES and attempt < attempts:
                    time.sleep(0.25 * (2 ** (attempt - 1)))
                    continue
                raise mapped from error

        if not response.ok:
            mapped = ProviderError(
                provider,
                map_status_to_code(response.status_code),
                f"Provider request failed with status {response.status_code}.",
                response.status_code,
            )
            last_error = mapped
            if response.status_code in TRANSIENT_CODES and attempt < attempts:
                time.sleep(0.25 * (2 ** (attempt - 1)))
                continue
            raise mapped

        return parsed

    if last_error:
        raise last_error
    raise ProviderError(provider, "UPSTREAM", "Provider request failed.")


