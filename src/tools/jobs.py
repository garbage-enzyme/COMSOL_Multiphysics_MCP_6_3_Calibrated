"""MCP control-plane tools for durable H1 background jobs."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from src.jobs.manager import JobManager


job_manager = JobManager()


def register_job_tools(mcp: FastMCP) -> None:
    """Register durable submit/status/tail/cooperative-cancel/resume tools."""

    @mcp.tool()
    def job_submit(spec: dict[str, Any]) -> dict[str, Any]:
        """Validate and detach one durable staged_sweep job; returns without waiting for COMSOL."""
        try:
            return job_manager.submit(spec)
        except Exception as exc:
            return {"success": False, "error_type": type(exc).__name__, "error": str(exc)}

    @mcp.tool()
    def job_status(job_id: str) -> dict[str, Any]:
        """Read and reconcile durable job state without starting COMSOL."""
        try:
            return job_manager.status(job_id)
        except Exception as exc:
            return {"success": False, "job_id": job_id, "error_type": type(exc).__name__, "error": str(exc)}

    @mcp.tool()
    def job_tail(job_id: str, n: int = 20) -> dict[str, Any]:
        """Return at most 200 trailing event and worker-log lines without solver side effects."""
        try:
            return job_manager.tail(job_id, n)
        except Exception as exc:
            return {"success": False, "job_id": job_id, "error_type": type(exc).__name__, "error": str(exc)}

    @mcp.tool()
    def job_cancel(job_id: str) -> dict[str, Any]:
        """Request cooperative stop between solve points; H1 never claims a blocking COMSOL solve was cancelled."""
        try:
            return job_manager.cancel(job_id)
        except Exception as exc:
            return {"success": False, "job_id": job_id, "error_type": type(exc).__name__, "error": str(exc)}

    @mcp.tool()
    def job_resume(job_id: str) -> dict[str, Any]:
        """Resume only failed/interrupted jobs with an unchanged immutable specification and M1 journal."""
        try:
            return job_manager.resume(job_id)
        except Exception as exc:
            return {"success": False, "job_id": job_id, "error_type": type(exc).__name__, "error": str(exc)}
