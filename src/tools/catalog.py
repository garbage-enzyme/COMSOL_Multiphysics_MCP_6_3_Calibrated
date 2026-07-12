"""Deterministic inspection helpers for the registered MCP tool surface."""

from __future__ import annotations

from typing import Any


async def snapshot_tool_schemas(server: Any) -> dict[str, dict[str, Any]]:
    """Return name-keyed public input schemas for every registered tool."""
    tools = await server.list_tools()
    return {
        tool.name: tool.inputSchema
        for tool in sorted(tools, key=lambda item: item.name)
    }


__all__ = ["snapshot_tool_schemas"]
