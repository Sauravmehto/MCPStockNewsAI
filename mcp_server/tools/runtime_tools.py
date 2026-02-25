"""Runtime and operations tools."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_runtime_tools(mcp: FastMCP, services: "ToolServices") -> None:
    @mcp.tool(description="Get server health metrics for uptime, request/error rates, latency, and providers.")
    def get_server_health() -> str:
        metrics = services.runtime.get_server_health()
        return json.dumps(asdict(metrics), ensure_ascii=True)


