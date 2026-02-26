"""Runtime and operations tools."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_server.tools.registry import ToolServices


def register_runtime_tools(mcp: FastMCP, services: "ToolServices") -> None:
    def _run_async(coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(coro)).result()

    @mcp.tool(description="Get server health metrics for uptime, request/error rates, latency, and providers.")
    def get_server_health() -> str:
        metrics = services.runtime.get_server_health()
        return json.dumps(asdict(metrics), ensure_ascii=True)

    @mcp.tool(description="Compatibility tool: list MCP prompts from server prompt registry.")
    def list_mcp_prompts() -> str:
        prompts = _run_async(mcp.list_prompts())
        payload = [
            {
                "name": prompt.name,
                "title": prompt.title,
                "description": prompt.description,
                "arguments": [
                    {"name": arg.name, "required": bool(arg.required), "description": arg.description}
                    for arg in (prompt.arguments or [])
                ],
            }
            for prompt in prompts
        ]
        return json.dumps({"prompts": payload}, ensure_ascii=True)

    @mcp.tool(description="Compatibility tool: get MCP prompt text by name and JSON arguments.")
    def get_mcp_prompt(prompt_name: str, arguments_json: str = "{}") -> str:
        try:
            arguments = json.loads(arguments_json) if arguments_json.strip() else {}
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        result = _run_async(mcp.get_prompt(prompt_name, arguments))
        messages = [
            {
                "role": msg.role,
                "text": getattr(msg.content, "text", ""),
            }
            for msg in result.messages
        ]
        return json.dumps({"description": result.description, "messages": messages}, ensure_ascii=True)

    @mcp.tool(description="Compatibility tool: list MCP resources from server registry.")
    def list_mcp_resources() -> str:
        resources = _run_async(mcp.list_resources())
        payload = [
            {
                "uri": str(resource.uri),
                "name": resource.name,
                "title": resource.title,
                "description": resource.description,
                "mimeType": resource.mimeType,
            }
            for resource in resources
        ]
        return json.dumps({"resources": payload}, ensure_ascii=True)

    @mcp.tool(description="Compatibility tool: list MCP resource templates from server registry.")
    def list_mcp_resource_templates() -> str:
        templates = _run_async(mcp.list_resource_templates())
        payload = [
            {
                "uriTemplate": template.uriTemplate,
                "name": template.name,
                "title": template.title,
                "description": template.description,
                "mimeType": template.mimeType,
            }
            for template in templates
        ]
        return json.dumps({"resourceTemplates": payload}, ensure_ascii=True)

    @mcp.tool(description="Compatibility tool: read an MCP resource by URI.")
    def read_mcp_resource(uri: str) -> str:
        contents = _run_async(mcp.read_resource(uri))
        payload = [
            {
                "mimeType": item.mime_type,
                "content": item.content,
            }
            for item in contents
        ]
        return json.dumps({"contents": payload}, ensure_ascii=True)


