"""Exact-identity process inspection used by the H2 cancellation coordinator."""

from __future__ import annotations

from typing import Any

import psutil

from .store import process_identity, process_identity_state


def inspect_identity(identity: dict[str, Any]) -> dict[str, Any]:
    """Return an exact identity verdict without acting on a process."""
    state, reason = process_identity_state(identity)
    return {"identity": identity, "state": state, "reason": reason}


def capture_owned_descendants(worker_identity: dict[str, Any]) -> dict[str, Any]:
    """Capture only descendants of a worker whose full identity still matches."""
    verdict = inspect_identity(worker_identity)
    if verdict["state"] != "active":
        return {"worker": verdict, "descendants": []}
    try:
        worker = psutil.Process(int(worker_identity["pid"]))
        descendants = [process_identity(item.pid) for item in worker.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError) as exc:
        return {
            "worker": {**verdict, "state": "uncertain", "reason": f"cannot inspect descendants: {exc}"},
            "descendants": [],
        }
    return {"worker": verdict, "descendants": descendants}


def terminate_exact(identity: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    """Terminate one process only after immediate full-identity revalidation."""
    before = inspect_identity(identity)
    if before["state"] != "active":
        return {"acted": False, "before": before, "reason": "identity_not_active"}
    try:
        process = psutil.Process(int(identity["pid"]))
        if force:
            process.kill()
            action = "kill"
        else:
            process.terminate()
            action = "terminate"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError) as exc:
        return {
            "acted": False,
            "before": before,
            "reason": f"process_action_failed: {type(exc).__name__}: {exc}",
        }
    return {"acted": True, "action": action, "before": before}


def verify_absent(identities: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify every captured identity is stale; uncertainty is never absence."""
    verdicts = [inspect_identity(identity) for identity in identities]
    return {
        "absent": all(item["state"] == "stale" for item in verdicts),
        "verdicts": verdicts,
    }
