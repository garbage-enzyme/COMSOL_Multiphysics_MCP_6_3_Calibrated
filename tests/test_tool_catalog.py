"""Compatibility gates for the pre-H3 MCP discovery surface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.server import create_server
from src.tools.catalog import snapshot_tool_schemas


SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "full_tool_schemas.json"


def test_full_tool_schema_snapshot_is_stable():
    server = create_server("full-schema-snapshot-test")
    actual = asyncio.run(snapshot_tool_schemas(server))
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    assert len(actual) == 96
    assert actual == expected


def test_registered_tool_names_are_unique():
    server = create_server("unique-tool-name-test")
    tools = asyncio.run(server.list_tools())
    names = [tool.name for tool in tools]

    assert len(names) == len(set(names))
