"""Anthropic summary client for optional portfolio narrative generation."""

from __future__ import annotations

import json
from typing import Any

import requests

from mcp_server.providers.http import ProviderError


class AnthropicClient:
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 20.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.anthropic.com/v1/messages"

    def generate_summary(self, prompt: str) -> str | None:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 350,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            response = requests.post(
                self.base_url,
                timeout=self.timeout_seconds,
                headers=headers,
                data=json.dumps(payload),
            )
        except requests.RequestException as error:
            raise ProviderError("anthropic", "NETWORK", f"Anthropic request failed: {error}") from error
        if response.status_code == 401:
            raise ProviderError("anthropic", "AUTH", "Anthropic authentication failed.", response.status_code)
        if response.status_code == 429:
            raise ProviderError("anthropic", "RATE_LIMIT", "Anthropic rate limit reached.", response.status_code)
        if not response.ok:
            raise ProviderError(
                "anthropic",
                "UPSTREAM",
                f"Anthropic request failed with status {response.status_code}.",
                response.status_code,
            )
        try:
            data = response.json()
        except ValueError:
            raise ProviderError("anthropic", "BAD_RESPONSE", "Anthropic returned non-JSON response.", response.status_code)
        content = data.get("content")
        if not isinstance(content, list):
            return None
        texts = [item.get("text") for item in content if isinstance(item, dict) and isinstance(item.get("text"), str)]
        return "\n".join(texts).strip() if texts else None


