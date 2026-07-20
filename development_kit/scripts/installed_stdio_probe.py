"""Probe the installed console entry point over real MCP stdio transport."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _tool_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        if set(structured) == {"result"} and isinstance(structured["result"], dict):
            return structured["result"]
        return structured
    for content in getattr(result, "content", []):
        text = getattr(content, "text", None)
        if isinstance(text, str):
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    raise RuntimeError("tool result does not contain one JSON object")


async def _expect_rejection(
    session: ClientSession,
    *,
    case_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    try:
        result = await session.call_tool(
            tool_name,
            arguments,
            read_timeout_seconds=timedelta(seconds=10),
        )
    except Exception as exc:
        return {
            "case_id": case_id,
            "rejected": True,
            "mode": "protocol_exception",
            "exception_type": type(exc).__name__,
        }
    rejected = bool(getattr(result, "isError", False))
    return {
        "case_id": case_id,
        "rejected": rejected,
        "mode": "tool_error_result" if rejected else "unexpected_success",
        "exception_type": None,
    }


async def _probe(command: Path, workdir: Path, stderr_path: Path) -> dict[str, Any]:
    environment = {
        "COMSOL_MCP_PROFILE": "core",
        "COMSOL_MCP_RUNTIME_DIR": str(workdir / "runtime"),
    }
    parameters = StdioServerParameters(
        command=str(command),
        args=[],
        cwd=str(workdir),
        env=environment,
    )
    with stderr_path.open("w", encoding="utf-8") as errlog:
        async with stdio_client(parameters, errlog=errlog) as streams:
            async with ClientSession(
                streams[0],
                streams[1],
                read_timeout_seconds=timedelta(seconds=15),
            ) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                tool_names = sorted(tool.name for tool in listed.tools)
                preflight_result = await session.call_tool(
                    "solver_preflight",
                    {},
                    read_timeout_seconds=timedelta(seconds=15),
                )
                if getattr(preflight_result, "isError", False):
                    raise RuntimeError("installed cold solver_preflight call returned a tool error")
                preflight = _tool_payload(preflight_result)
                capabilities_result = await session.call_tool(
                    "capabilities",
                    {},
                    read_timeout_seconds=timedelta(seconds=15),
                )
                if getattr(capabilities_result, "isError", False):
                    raise RuntimeError("installed capabilities call returned a tool error")
                capabilities = _tool_payload(capabilities_result)
                malformed = [
                    await _expect_rejection(
                        session,
                        case_id="unknown_tool",
                        tool_name="__unknown_tool__",
                        arguments={},
                    ),
                    await _expect_rejection(
                        session,
                        case_id="invalid_job_identifier_type",
                        tool_name="job_status",
                        arguments={"job_id": {"invalid": True}},
                    ),
                    await _expect_rejection(
                        session,
                        case_id="missing_job_identifier",
                        tool_name="job_status",
                        arguments={},
                    ),
                ]
    if not malformed or not all(item["rejected"] for item in malformed):
        raise RuntimeError(f"malformed request matrix did not fail closed: {malformed}")
    if capabilities.get("profile") != "core":
        raise RuntimeError("installed stdio probe did not activate the core profile")
    if preflight.get("control_plane", {}).get("operation") != "solver_preflight":
        raise RuntimeError("installed cold solver_preflight call omitted timing evidence")
    session_state = capabilities.get("session", {})
    if session_state.get("connected") or session_state.get("starting"):
        raise RuntimeError("installed stdio probe unexpectedly started COMSOL")
    names_payload = json.dumps(tool_names, separators=(",", ":")).encode("utf-8")
    return {
        "schema_name": "comsol_mcp.installed_stdio_probe",
        "schema_version": "1.0.0",
        "transport": "stdio",
        "initialize": {
            "protocol_version": initialized.protocolVersion,
            "server_name": initialized.serverInfo.name,
            "server_version": initialized.serverInfo.version,
        },
        "tool_count": len(tool_names),
        "tool_names_sha256": hashlib.sha256(names_payload).hexdigest(),
        "capabilities": {
            "profile": capabilities["profile"],
            "package_version": capabilities["deployment_identity"]["package_version"],
            "build_identity_sha256": capabilities["deployment_identity"]["build_identity"]["build_identity_sha256"],
            "schema_registry_sha256": capabilities["schema_registry"]["registry_sha256"],
            "catalog_contract_sha256": capabilities["deployment_identity"]["catalog_contract_sha256"],
        },
        "cold_solver_preflight": {
            "ready": preflight.get("ready"),
            "blocker_count": len(preflight.get("blockers", [])),
            "latency_seconds": preflight["control_plane"]["latency_seconds"],
            "outcome": preflight["control_plane"]["outcome"],
        },
        "malformed_request_matrix": malformed,
        "comsol_client_started": False,
        "stderr_byte_count": stderr_path.stat().st_size,
        "paths_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    command = args.command.resolve(strict=True)
    workdir = args.workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    stderr_path = workdir / "server-stderr.log"
    result = asyncio.run(_probe(command, workdir, stderr_path))
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
