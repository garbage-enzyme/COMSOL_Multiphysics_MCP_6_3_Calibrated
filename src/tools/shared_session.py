"""Public adapters for the default-off attached shared-session lifecycle."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from src.operation_arbiter import get_operation_status
from src.shared_session.contracts import normalize_shared_server_feature_gate
from src.shared_session.lifecycle import SharedSessionManager
from src.shared_session.preflight import classify_shared_server_preflight
from src.shared_session.process_probe import collect_shared_preflight_snapshot


shared_session_manager = SharedSessionManager()


def register_shared_session_tools(mcp: FastMCP) -> None:
    """Register explicit local attached-server lifecycle tools."""
    selection = getattr(mcp, "profile_selection", None)
    profile_name = getattr(selection, "name", "unknown")

    @mcp.tool()
    def shared_server_preflight(host: str, port: int) -> dict[str, Any]:
        """Classify one existing local Desktop/Server endpoint without MPh."""
        gate = normalize_shared_server_feature_gate(profile_name)
        if not gate.gate_open:
            return {
                "success": False,
                "state": "feature_gate_closed",
                "feature_gate": gate.to_dict(),
                "mph_imported": False,
                "client_constructed": False,
            }
        first = collect_shared_preflight_snapshot()
        second = collect_shared_preflight_snapshot()
        return classify_shared_server_preflight(
            endpoint={"host": host, "port": port},
            first_probe=first,
            second_probe=second,
        )

    @mcp.tool()
    def shared_server_attach(
        host: str,
        port: int,
        model_tag: str,
        user_confirmed: bool,
        expected_label: str | None = None,
        expected_file_path: str | None = None,
        expected_unsaved: bool | None = None,
    ) -> dict[str, Any]:
        """Attach to one existing server and resolve one exact model selector."""
        selector: dict[str, Any] = {"tag": model_tag}
        if expected_label is not None:
            selector["expected_label"] = expected_label
        if expected_file_path is not None:
            selector["expected_file_path"] = expected_file_path
        if expected_unsaved is not None:
            selector["expected_unsaved"] = expected_unsaved
        return shared_session_manager.attach(
            {
                "endpoint": {"host": host, "port": port},
                "model_selector": selector,
                "user_confirmed": user_confirmed,
            },
            profile=profile_name,
        )

    @mcp.tool()
    def shared_server_detach() -> dict[str, Any]:
        """Disconnect only the MCP client and preserve external resources."""
        return shared_session_manager.detach()

    @mcp.tool()
    def shared_server_status() -> dict[str, Any]:
        """Return bounded attached-session and operation-arbiter status."""
        return {
            **shared_session_manager.status(),
            "operation": get_operation_status(),
        }


__all__ = ["register_shared_session_tools", "shared_session_manager"]
