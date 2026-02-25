import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_server.prompts.portfolio_prompts import register_portfolio_prompts
from mcp_server.resources.portfolio_resources import register_portfolio_resources


class _MockPortfolioService:
    def __init__(self) -> None:
        self.snapshot: dict[str, object] | None = None

    def get_current_resource_snapshot(self) -> dict[str, object] | None:
        return self.snapshot

    def get_resource_snapshot(self, report_type: str) -> dict[str, object] | None:
        if not self.snapshot:
            return None
        if self.snapshot.get("report_type") != report_type:
            return None
        return self.snapshot


def test_prompts_list_and_get_happy_path() -> None:
    mcp = FastMCP(name="test-prompts")
    register_portfolio_prompts(mcp)

    prompts = asyncio.run(mcp.list_prompts())
    assert any(prompt.name == "portfolio_analysis" for prompt in prompts)

    prompt_result = asyncio.run(mcp.get_prompt("portfolio_analysis", {"portfolio": "US Core"}))
    rendered = str(prompt_result.messages[0].content.text)
    assert "US Core" in rendered
    assert "Allocation diagnostics" in rendered


def test_prompt_invalid_name() -> None:
    mcp = FastMCP(name="test-prompts-invalid-name")
    register_portfolio_prompts(mcp)

    with pytest.raises(ValueError, match="Unknown prompt"):
        asyncio.run(mcp.get_prompt("unknown_prompt", {"portfolio": "x"}))


def test_prompt_missing_required_argument() -> None:
    mcp = FastMCP(name="test-prompts-missing-arg")
    register_portfolio_prompts(mcp)

    with pytest.raises(ValueError, match="Missing required arguments"):
        asyncio.run(mcp.get_prompt("portfolio_analysis", {}))


def test_resources_list_and_read_happy_path() -> None:
    mcp = FastMCP(name="test-resources")
    portfolio_service = _MockPortfolioService()
    portfolio_service.snapshot = {
        "uri": "portfolio://current",
        "report_type": "analysis",
        "source_file_path": "C:/tmp/sample.xlsx",
        "payload": {"ok": True},
    }
    register_portfolio_resources(mcp, SimpleNamespace(portfolio=portfolio_service))

    resources = asyncio.run(mcp.list_resources())
    assert any(str(resource.uri) == "portfolio://current" for resource in resources)

    contents = asyncio.run(mcp.read_resource("portfolio://current"))
    assert len(contents) == 1
    assert contents[0].mime_type == "application/json"
    data = json.loads(contents[0].content)
    assert data["report_type"] == "analysis"

    templates = asyncio.run(mcp.list_resource_templates())
    assert any(template.uriTemplate == "portfolio://snapshot/{report_type}" for template in templates)


def test_resource_invalid_uri() -> None:
    mcp = FastMCP(name="test-resources-invalid-uri")
    portfolio_service = _MockPortfolioService()
    register_portfolio_resources(mcp, SimpleNamespace(portfolio=portfolio_service))

    with pytest.raises(Exception):
        asyncio.run(mcp.read_resource("portfolio://unknown"))


def test_resource_not_found_and_error_safety() -> None:
    mcp = FastMCP(name="test-resources-not-found")
    portfolio_service = _MockPortfolioService()
    register_portfolio_resources(mcp, SimpleNamespace(portfolio=portfolio_service))

    with pytest.raises(Exception) as exc:
        asyncio.run(mcp.read_resource("portfolio://current"))

    message = str(exc.value)
    assert "Portfolio resource not found" in message
    assert "api_key" not in message.lower()
    assert "authorization" not in message.lower()
    assert "token" not in message.lower()


