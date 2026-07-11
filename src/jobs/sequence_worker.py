"""Injected process-only worker used to prove H1 durability without COMSOL."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time

from .store import JobStore, process_identity


def run(root: str, job_id: str) -> int:
    store = JobStore(Path(root))
    spec = store.read_spec(job_id)
    if spec.get("job_type") != "test_sequence":
        raise ValueError("Sequence worker refuses non-test jobs")
    identity = process_identity(os.getpid())
    deadline = time.monotonic() + 2.0
    while store.read_state(job_id).get("worker_pid") != identity["pid"]:
        if time.monotonic() >= deadline:
            raise RuntimeError("Control plane did not durably record the worker identity")
        time.sleep(0.01)
    store.update_state(
        job_id,
        "starting",
        patch={
            "worker_pid": identity["pid"],
            "worker_process_create_time": identity["process_create_time"],
            "worker_command_signature": identity["command_signature"],
        },
        event="worker_started",
    )
    store.update_state(job_id, "smoke_running", event="smoke_started")
    delays = spec["delays"]
    for index, delay in enumerate(delays):
        time.sleep(float(delay))
        next_status = None
        if index == 0:
            next_status = "smoke_validated"
        store.update_state(
            job_id,
            next_status,
            patch={"progress": {"completed": index + 1, "total": len(delays)}},
            event="sequence_step",
            event_data={"index": index},
        )
        if index == 0 and len(delays) > 1:
            store.update_state(job_id, "running", event="broad_phase_started")
    store.update_state(job_id, "completed", event="completed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run(sys.argv[1], sys.argv[2]))
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
