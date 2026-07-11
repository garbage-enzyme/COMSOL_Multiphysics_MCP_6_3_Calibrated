"""Tests for MCP server construction without starting a transport."""

from mcp.server.fastmcp import FastMCP

from src.knowledge.embedded import register_knowledge_tools
from src.server import create_server, register_all_resources, register_all_tools
from src.tools.capabilities import get_capabilities


def test_server_registration_is_idempotent():
    server = create_server("registration-test")
    tool_names = set(server._tool_manager._tools)
    resource_names = set(server._resource_manager._resources)

    assert "comsol_start" in tool_names
    assert "capabilities" in tool_names
    assert "model_create" in tool_names
    assert "study_solve" in tool_names
    assert "docs_get" in tool_names
    assert "pdf_search" not in tool_names
    assert "pdf_search_status" not in tool_names
    assert "pdf_list_modules" not in tool_names
    assert resource_names

    register_all_tools(server)
    register_all_resources(server)

    assert set(server._tool_manager._tools) == tool_names
    assert set(server._resource_manager._resources) == resource_names


def test_semantic_pdf_tools_require_explicit_opt_in():
    server = FastMCP("pdf-opt-in-test")

    register_knowledge_tools(server, include_pdf_search=True)

    tool_names = set(server._tool_manager._tools)
    assert {"pdf_search", "pdf_search_status", "pdf_list_modules"} <= tool_names


def test_capabilities_report_risky_operations_without_starting_comsol(monkeypatch):
    import src.tools.capabilities as capability_module

    monkeypatch.setattr(
        capability_module.session_manager,
        "get_status",
        lambda: {"connected": False, "starting": False},
    )

    result = get_capabilities()

    assert result["profile"] == "default"
    assert result["session"] == {"connected": False, "starting": False}
    assert result["long_jobs"]["real_cancellation"] is False
    assert "pdf_search" in result["disabled_by_default"]
