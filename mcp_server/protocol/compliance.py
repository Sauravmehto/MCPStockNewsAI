"""MCP protocol compliance wiring for prompts/resources behavior."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from types import MethodType
from threading import Lock

import mcp.types as mcp_types
from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel.server import NotificationOptions, request_ctx
from mcp.shared.exceptions import McpError


RESOURCE_NOT_FOUND_CODE = -32002


class ProtocolCompliance:
    """Tracks resource subscriptions and sends protocol notifications."""

    def __init__(self, mcp: FastMCP) -> None:
        self.mcp = mcp
        self._subscribers: dict[str, set[Any]] = defaultdict(set)
        self._subscribers_lock = Lock()
        self._patch_initialization_capabilities()
        self._register_subscribe_handlers()
        self._register_error_mapped_handlers()

    def _patch_initialization_capabilities(self) -> None:
        server = self.mcp._mcp_server
        original_create = server.create_initialization_options

        def patched_create_initialization_options(server_self, notification_options=None, experimental_capabilities=None):
            options = original_create(
                notification_options
                or NotificationOptions(
                    prompts_changed=True,
                    resources_changed=True,
                    tools_changed=False,
                ),
                experimental_capabilities or {},
            )
            options.capabilities.prompts = mcp_types.PromptsCapability(listChanged=True)
            options.capabilities.resources = mcp_types.ResourcesCapability(subscribe=True, listChanged=True)
            return options

        server.create_initialization_options = MethodType(patched_create_initialization_options, server)

    def register_explicit_list_handlers(self) -> None:
        """Re-register list handlers explicitly so capabilities and discovery are always available."""
        server = self.mcp._mcp_server

        @server.list_prompts()
        async def list_prompts():
            return await self.mcp.list_prompts()

        @server.list_resources()
        async def list_resources():
            return await self.mcp.list_resources()

        @server.list_resource_templates()
        async def list_resource_templates():
            return await self.mcp.list_resource_templates()

    def _register_subscribe_handlers(self) -> None:
        server = self.mcp._mcp_server

        @server.subscribe_resource()
        async def subscribe_resource(uri) -> None:
            uri_str = str(uri)
            context = request_ctx.get(None)
            if context is None:
                return
            with self._subscribers_lock:
                self._subscribers[uri_str].add(context.session)

        @server.unsubscribe_resource()
        async def unsubscribe_resource(uri) -> None:
            uri_str = str(uri)
            context = request_ctx.get(None)
            if context is None:
                return
            with self._subscribers_lock:
                sessions = self._subscribers.get(uri_str)
                if not sessions:
                    return
                sessions.discard(context.session)
                if not sessions:
                    self._subscribers.pop(uri_str, None)

    def _register_error_mapped_handlers(self) -> None:
        server = self.mcp._mcp_server

        @server.get_prompt()
        async def mapped_get_prompt(name: str, arguments: dict[str, str] | None = None):
            try:
                return await self.mcp.get_prompt(name, arguments)
            except ValueError as error:
                raise McpError(mcp_types.ErrorData(code=mcp_types.INVALID_PARAMS, message=str(error), data=None))
            except Exception:
                raise McpError(mcp_types.ErrorData(code=mcp_types.INTERNAL_ERROR, message="Internal error", data=None))

        @server.read_resource()
        async def mapped_read_resource(uri):
            try:
                return await self.mcp.read_resource(uri)
            except Exception as error:
                message = str(error)
                if "Unknown resource" in message or "not found" in message.lower():
                    raise McpError(
                        mcp_types.ErrorData(
                            code=RESOURCE_NOT_FOUND_CODE,
                            message="Resource not found",
                            data={"uri": str(uri)},
                        )
                    )
                raise McpError(mcp_types.ErrorData(code=mcp_types.INTERNAL_ERROR, message="Internal error", data=None))

    async def notify_resource_updated(self, uri: str) -> None:
        with self._subscribers_lock:
            sessions = list(self._subscribers.get(uri, set()))
        if not sessions:
            return
        for session in sessions:
            await session.send_resource_updated(uri)

    def notify_resource_updated_sync(self, uri: str) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.notify_resource_updated(uri))

    def get_subscribed_uris(self, prefix: str | None = None) -> list[str]:
        with self._subscribers_lock:
            uris = list(self._subscribers.keys())
        if prefix is None:
            return uris
        return [uri for uri in uris if uri.startswith(prefix)]


def configure_protocol_compliance(mcp: FastMCP) -> ProtocolCompliance:
    """Configure protocol compliance hooks and return notifier state."""
    compliance = ProtocolCompliance(mcp)
    compliance.register_explicit_list_handlers()
    return compliance


