import asyncio
from types import SimpleNamespace

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError

from mcp_server.protocol.compliance import RESOURCE_NOT_FOUND_CODE, configure_protocol_compliance
from mcp_server.prompts.portfolio_prompts import register_portfolio_prompts
from mcp_server.resources.portfolio_resources import register_portfolio_resources


class _MockPortfolioService:
    def __init__(self) -> None:
        self.snapshot: dict[str, object] | None = {
            "uri": "portfolio://current",
            "report_type": "analysis",
            "source_file_path": "C:/tmp/sample.xlsx",
            "payload": {"ok": True},
        }

    def get_current_resource_snapshot(self) -> dict[str, object] | None:
        return self.snapshot

    def get_resource_snapshot(self, report_type: str) -> dict[str, object] | None:
        if not self.snapshot:
            return None
        if self.snapshot.get("report_type") != report_type:
            return None
        return self.snapshot


class _FakeSession:
    def __init__(self) -> None:
        self.updated_uris: list[str] = []

    async def send_resource_updated(self, uri: str) -> None:
        self.updated_uris.append(uri)


def test_capabilities_advertise_prompts_resources_features() -> None:
    mcp = FastMCP(name="test-capabilities")
    configure_protocol_compliance(mcp)
    register_portfolio_prompts(mcp)
    register_portfolio_resources(mcp, SimpleNamespace(portfolio=_MockPortfolioService()))

    options = mcp._mcp_server.create_initialization_options()
    assert options.capabilities.prompts is not None
    assert options.capabilities.prompts.listChanged is True
    assert options.capabilities.resources is not None
    assert options.capabilities.resources.listChanged is True
    assert options.capabilities.resources.subscribe is True


def test_get_prompt_error_mapping_invalid_params() -> None:
    mcp = FastMCP(name="test-get-prompt-errors")
    configure_protocol_compliance(mcp)
    register_portfolio_prompts(mcp)

    handler = mcp._mcp_server.request_handlers[mcp_types.GetPromptRequest]
    request = mcp_types.GetPromptRequest(
        params=mcp_types.GetPromptRequestParams(name="unknown_prompt", arguments={"portfolio": "x"})
    )
    try:
        asyncio.run(handler(request))
        raise AssertionError("Expected McpError for invalid prompt name")
    except McpError as error:
        assert error.error.code == mcp_types.INVALID_PARAMS


def test_read_resource_error_mapping_not_found() -> None:
    mcp = FastMCP(name="test-read-resource-errors")
    configure_protocol_compliance(mcp)
    register_portfolio_resources(mcp, SimpleNamespace(portfolio=_MockPortfolioService()))

    handler = mcp._mcp_server.request_handlers[mcp_types.ReadResourceRequest]
    request = mcp_types.ReadResourceRequest(
        params=mcp_types.ReadResourceRequestParams(uri="portfolio://missing")
    )
    try:
        asyncio.run(handler(request))
        raise AssertionError("Expected McpError for resource not found")
    except McpError as error:
        assert error.error.code == RESOURCE_NOT_FOUND_CODE
        assert error.error.data == {"uri": "portfolio://missing"}


def test_resource_updated_notification_to_subscribers() -> None:
    mcp = FastMCP(name="test-resource-updated-notify")
    compliance = configure_protocol_compliance(mcp)
    fake_session = _FakeSession()
    compliance._subscribers["portfolio://current"].add(fake_session)  # intentional white-box assertion

    asyncio.run(compliance.notify_resource_updated("portfolio://current"))
    assert fake_session.updated_uris == ["portfolio://current"]


