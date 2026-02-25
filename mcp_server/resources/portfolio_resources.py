"""Portfolio resource definitions."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices

CURRENT_PORTFOLIO_URI = "portfolio://current"
PORTFOLIO_SNAPSHOT_TEMPLATE_URI = "portfolio://snapshot/{report_type}"


def register_portfolio_resources(mcp: FastMCP, services: "ToolServices") -> None:
    @mcp.resource(
        CURRENT_PORTFOLIO_URI,
        name="current-portfolio",
        title="Current Portfolio Snapshot",
        description="Latest successful portfolio analysis payload captured by the portfolio workflow.",
        mime_type="application/json",
    )
    def current_portfolio_resource() -> str:
        snapshot = services.portfolio.get_current_resource_snapshot()
        if not snapshot:
            raise ValueError("Portfolio resource not found. Run a portfolio workflow first.")
        return json.dumps(snapshot, ensure_ascii=True)

    @mcp.resource(
        PORTFOLIO_SNAPSHOT_TEMPLATE_URI,
        name="portfolio-snapshot",
        title="Portfolio Snapshot By Report Type",
        description="Returns the latest snapshot for a specific report type (analysis, benchmark, stress_test).",
        mime_type="application/json",
    )
    def portfolio_snapshot_by_type(report_type: str) -> str:
        snapshot = services.portfolio.get_resource_snapshot(report_type)
        if not snapshot:
            raise ValueError("Portfolio resource not found for the given report_type.")
        return json.dumps(snapshot, ensure_ascii=True)


