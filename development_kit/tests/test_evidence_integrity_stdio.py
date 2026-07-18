"""Real stdio discovery and invocation of solver-free evidence guard tools."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import timedelta

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from development_kit.tests.test_portfolio_verifier import _fixture
from src.evidence.integrity_controls import EVIDENCE_SETTINGS_ENV
from src.path_policy import ARTIFACT_WRITE_ROOT_ENV


ROOT = Path(__file__).parents[2]


def _decode(result) -> dict:
    if getattr(result, "isError", False):
        raise RuntimeError(f"MCP tool returned an error: {result}")
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        value = structured.get("result", structured)
        if isinstance(value, dict):
            return value
    for item in getattr(result, "content", []):
        text = getattr(item, "text", None)
        if text:
            value = json.loads(text)
            if isinstance(value, dict):
                return value
    raise ValueError("MCP result did not contain a JSON object")


async def _exercise(request: dict, artifact_root: Path, runtime_root: Path) -> None:
    environment = os.environ.copy()
    environment.pop(EVIDENCE_SETTINGS_ENV, None)
    environment.update(
        {
            "COMSOL_MCP_PROFILE": "core",
            "COMSOL_MCP_RUNTIME_DIR": str(runtime_root),
            ARTIFACT_WRITE_ROOT_ENV: str(runtime_root),
        }
    )
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        cwd=ROOT,
        env=environment,
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(
            read,
            write,
            read_timeout_seconds=timedelta(seconds=30),
        ) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert {"evidence_integrity_status", "evidence_integrity_verify"} <= names

            capabilities = _decode(await session.call_tool("capabilities", {}))
            status = _decode(await session.call_tool("evidence_integrity_status", {}))
            verification = _decode(
                await session.call_tool(
                    "evidence_integrity_verify",
                    {
                        "portfolio_request": request,
                        "artifact_roots": {"case-one": str(artifact_root)},
                    },
                )
            )

    assert capabilities["evidence_integrity"]["strict_verification_active"] is True
    assert capabilities["evidence_integrity"]["settings_fingerprint_sha256"] == status[
        "settings_fingerprint_sha256"
    ]
    assert status["strict_verification_active"] is True
    assert verification["success"] is True
    assert verification["verification_state"] == "verified"
    assert verification["strictly_verified"] is True
    assert verification["artifact_root_validation"]["paths_included"] is False


def test_source_stdio_client_discovers_and_invokes_both_guard_tools():
    base = Path("D:/comsol_runtime") if Path("D:/").exists() else Path(
        os.environ.get("SystemRoot", "C:/Windows")
    ) / "Temp"
    runtime_root = Path(tempfile.mkdtemp(prefix="evidence_stdio_", dir=base))
    artifact_root = runtime_root / "case-one"
    artifact_root.mkdir()
    try:
        request, _raw, _fit = _fixture(artifact_root)
        anyio.run(_exercise, request, artifact_root, runtime_root)
    finally:
        shutil.rmtree(runtime_root, ignore_errors=True)
