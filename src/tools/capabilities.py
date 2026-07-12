"""Machine-readable capability reporting for the default MCP profile."""

from mcp.server.fastmcp import FastMCP

from .session import session_manager


def get_capabilities() -> dict:
    """Describe supported, experimental, and disabled behavior without startup."""
    status = session_manager.get_status()
    return {
        "success": True,
        "profile": "default",
        "targets": {
            "comsol": "6.4+",
            "mph": "1.3.1 standalone clientapi",
        },
        "session": {
            "connected": bool(status.get("connected")),
            "starting": bool(status.get("starting")),
        },
        "verified": [
            "session_status_and_idempotent_start",
            "model_load_create_clone_save",
            "parameters",
            "geometry",
            "physics_and_multiphysics",
            "mesh",
            "study",
            "results_transport",
            "staged_csv_workflows",
            "bounded_lexical_manual_search",
            "solver_ownership_and_preflight",
            "durable_background_staged_sweep_jobs",
            "durable_job_real_cancellation_and_resume",
        ],
        "experimental": {
            "async_solver": {
                "progress": "synthetic checkpoints, not COMSOL solver percentage",
                "cancellation": (
                    "cooperative Python flag; does not interrupt a blocking "
                    "COMSOL study.run()"
                ),
            },
            "semantic_pdf_search": "source retained for an explicit isolated profile",
        },
        "disabled_by_default": [
            "pdf_search",
            "pdf_search_status",
            "pdf_list_modules",
        ],
        "manual_search": {
            "backend": "sqlite_fts5_bm25",
            "isolated_worker": True,
            "hard_deadline": True,
            "semantic_embeddings": False,
        },
        "long_jobs": {
            "durable_background_jobs": True,
            "job_types": ["staged_sweep"],
            "control_tools": ["job_submit", "job_status", "job_tail", "job_cancel", "job_resume"],
            "cancellation_scope": "same-host durable staged_sweep jobs owned by this runtime root",
            "cancellation_strategy": (
                "attempt-bound native cancellation on the verified COMSOL 6.4.0.293 profile; "
                "exact-identity owned-process fallback elsewhere; cancelled is committed only after "
                "worker/descendant/port/lease cleanup verification"
            ),
            "external_solver_ownership": True,
            "real_cancellation": True,
            "native_cancel_profile": "comsol-6.4.0.293-progress-context-20260712",
            "cross_host_cancellation": False,
            "staged_csv_resume": True,
        },
        "restart_required_after_source_changes": True,
    }


def startup_capability_summary() -> str:
    """Return a compact startup summary without initializing external services."""
    capabilities = get_capabilities()
    targets = capabilities["targets"]
    return (
        f"profile={capabilities['profile']}; "
        f"target=COMSOL {targets['comsol']} / MPh {targets['mph']}; "
        "lexical_manual=enabled; semantic_pdf=disabled; durable_jobs=staged_sweep; "
        "solver_ownership=enforced; durable_job_cancellation=verified"
    )


def register_capability_tools(mcp: FastMCP) -> None:
    """Register dependency-free server capability tools."""

    @mcp.tool()
    def capabilities() -> dict:
        """
        Report the default tool profile and the maturity of risky operations.

        This read-only call does not start COMSOL or initialize PDF/ML services.
        """
        return get_capabilities()
