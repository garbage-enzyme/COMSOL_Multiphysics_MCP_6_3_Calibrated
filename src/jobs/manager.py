"""Solver-free H1 control plane for durable job submission and reconciliation."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import psutil

from .store import (
    ACTIVE_STATES,
    JOB_SCHEMA_VERSION,
    TRANSITIONS,
    JobStore,
    atomic_write_json,
    process_identity,
    process_identity_state,
)


def _fingerprint(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_staged_sweep_spec(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Job specification must be an object")
    spec = dict(raw)
    if spec.get("job_type") != "staged_sweep":
        raise ValueError("Production jobs require job_type='staged_sweep'")
    required_strings = ("source_model_path", "parameter_name")
    for key in required_strings:
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    source = Path(spec["source_model_path"]).expanduser().resolve()
    if not source.is_file() or source.suffix.casefold() != ".mph":
        raise ValueError("source_model_path must name an existing MPH file")
    values = spec.get("parameter_values")
    if not isinstance(values, list) or not values:
        raise ValueError("parameter_values must be a nonempty list")
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError("parameter_values must contain only finite numbers")
    expressions = spec.get("expressions")
    if not isinstance(expressions, list) or not expressions or not all(
        isinstance(item, str) and item.strip() for item in expressions
    ):
        raise ValueError("expressions must be a nonempty string list")
    smoke_points = spec.get("smoke_points", 1)
    if smoke_points not in (1, 2) or smoke_points > len(values):
        raise ValueError("smoke_points must be 1 or 2 and no larger than the sweep")
    checkpoint = spec.get("checkpoint_model_path")
    if checkpoint and Path(checkpoint).expanduser().resolve() == source:
        raise ValueError("checkpoint_model_path must not overwrite the source model")
    spec["source_model_path"] = str(source)
    spec["smoke_points"] = smoke_points
    spec["schema_version"] = JOB_SCHEMA_VERSION
    spec["spec_fingerprint"] = _fingerprint({k: v for k, v in spec.items() if k != "spec_fingerprint"})
    return spec


def _validate_test_spec(raw: dict[str, Any]) -> dict[str, Any]:
    spec = dict(raw)
    if spec.get("job_type") != "test_sequence":
        raise ValueError("Injected test manager accepts only job_type='test_sequence'")
    delays = spec.get("delays", [0.05])
    if not isinstance(delays, list) or not delays or any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
        or float(value) > 30
        for value in delays
    ):
        raise ValueError("test_sequence delays must be finite values between 0 and 30 seconds")
    spec = {"job_type": "test_sequence", "delays": [float(value) for value in delays]}
    spec["schema_version"] = JOB_SCHEMA_VERSION
    spec["spec_fingerprint"] = _fingerprint(spec)
    return spec


class JobManager:
    """Persist and reconcile jobs without importing or starting COMSOL."""

    def __init__(self, root: str | Path | None = None, *, allow_test_jobs: bool = False):
        self.store = JobStore(root)
        self.allow_test_jobs = bool(allow_test_jobs)

    def submit(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        job_type = raw_spec.get("job_type") if isinstance(raw_spec, dict) else None
        if job_type == "test_sequence":
            if not self.allow_test_jobs:
                raise ValueError("test_sequence jobs are disabled")
            spec = _validate_test_spec(raw_spec)
        else:
            spec = validate_staged_sweep_spec(raw_spec)
            raise NotImplementedError("staged_sweep worker launch is implemented in H1b")
        now = time.time()
        state = {
            "schema_version": JOB_SCHEMA_VERSION,
            "status": "submitted",
            "attempt": 1,
            "created_at_epoch": now,
            "updated_at_epoch": now,
            "worker_pid": None,
            "worker_process_create_time": None,
            "worker_command_signature": None,
            "progress": {"completed": 0, "total": len(spec["delays"])},
            "last_error": None,
        }
        job_id = self.store.create(spec, state)
        self.store.append_event(job_id, "submitted", {"spec_fingerprint": spec["spec_fingerprint"]})
        try:
            identity = self._launch_test_worker(job_id)
            self.store.update_state(
                job_id,
                patch={
                    "worker_pid": identity["pid"],
                    "worker_process_create_time": identity["process_create_time"],
                    "worker_command_signature": identity["command_signature"],
                },
                event="worker_launched",
                event_data={"pid": identity["pid"]},
            )
        except Exception as exc:
            self.store.update_state(
                job_id,
                "failed",
                patch={"last_error": {"type": type(exc).__name__, "message": str(exc)}},
                event="launch_failed",
            )
            raise
        return {"success": True, "job_id": job_id, "status": "submitted"}

    def _launch_test_worker(self, job_id: str) -> dict[str, Any]:
        directory = self.store.job_dir(job_id)
        command = [sys.executable, "-m", "src.jobs.sequence_worker", str(self.store.root), job_id]
        flags = 0
        if os.name == "nt":
            flags = (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        with (directory / "worker.log").open("ab", buffering=0) as log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                close_fds=True,
                creationflags=flags,
                start_new_session=(os.name != "nt"),
            )
        deadline = time.monotonic() + 2.0
        while True:
            try:
                return process_identity(process.pid)
            except psutil.NoSuchProcess:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Detached test worker exited before its identity was recorded")
                time.sleep(0.01)

    def status(self, job_id: str) -> dict[str, Any]:
        with self.store.lock(job_id):
            state = self.store.read_state(job_id)
            if state.get("status") in ACTIVE_STATES and state.get("worker_pid") is not None:
                identity = {
                    "pid": state["worker_pid"],
                    "process_create_time": state.get("worker_process_create_time"),
                    "command_signature": state.get("worker_command_signature"),
                }
                process_state, reason = process_identity_state(identity)
                if process_state == "stale":
                    current = str(state["status"])
                    if "interrupted" not in TRANSITIONS[current]:
                        raise RuntimeError(f"Cannot reconcile state {current} as interrupted")
                    state["status"] = "interrupted"
                    state["last_error"] = {"type": "WorkerInterrupted", "message": reason}
                    state["updated_at_epoch"] = time.time()
                    atomic_write_json(self.store.job_dir(job_id) / "state.json", state)
                    self.store._append_event_unlocked(job_id, "worker_interrupted", {"reason": reason}, "interrupted")
                else:
                    state["worker_process_state"] = process_state
                    state["worker_process_reason"] = reason
            return {"success": True, "job_id": job_id, **state}

    def tail(self, job_id: str, n: int = 20) -> dict[str, Any]:
        return {"success": True, **self.store.tail(job_id, n)}
