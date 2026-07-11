"""Process-only acceptance tests for the H1a durable job control plane."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

import psutil
import pytest

from src.jobs.manager import JobManager, validate_staged_sweep_spec
from src.jobs.store import JobLock, JobStore, atomic_write_json, process_identity


@pytest.fixture()
def jobs_root():
    root = Path("D:/comsol_runtime_test/jobs") / uuid.uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def wait_for(manager: JobManager, job_id: str, statuses: set[str], timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        state = manager.status(job_id)
        if state["status"] in statuses:
            return state
        time.sleep(0.025)
    raise AssertionError(f"Job did not reach {statuses}: {manager.status(job_id)}")


def test_submit_returns_promptly_and_second_manager_observes_completion(jobs_root):
    first = JobManager(jobs_root, allow_test_jobs=True)
    started = time.monotonic()
    result = first.submit({"job_type": "test_sequence", "delays": [0.1, 0.1]})
    elapsed = time.monotonic() - started

    second = JobManager(jobs_root, allow_test_jobs=True)
    completed = wait_for(second, result["job_id"], {"completed"})

    assert elapsed < 1.0
    assert completed["progress"] == {"completed": 2, "total": 2}
    assert second.tail(result["job_id"], 2)["events"]


def test_killed_worker_is_reconciled_as_interrupted(jobs_root):
    manager = JobManager(jobs_root, allow_test_jobs=True)
    result = manager.submit({"job_type": "test_sequence", "delays": [0.05, 10.0]})
    running = wait_for(manager, result["job_id"], {"running"})
    worker = psutil.Process(running["worker_pid"])
    worker.terminate()
    worker.wait(timeout=5)

    interrupted = wait_for(JobManager(jobs_root, allow_test_jobs=True), result["job_id"], {"interrupted"})

    assert interrupted["last_error"]["type"] == "WorkerInterrupted"
    assert interrupted["progress"]["completed"] == 1


def test_completed_state_is_immutable(jobs_root):
    manager = JobManager(jobs_root, allow_test_jobs=True)
    result = manager.submit({"job_type": "test_sequence", "delays": [0.01]})
    wait_for(manager, result["job_id"], {"completed"})

    with pytest.raises(ValueError, match="Invalid job state transition"):
        manager.store.update_state(result["job_id"], "failed")
    with pytest.raises(ValueError, match="immutable"):
        manager.store.update_state(result["job_id"], patch={"last_error": {"message": "rewrite"}})


def test_lock_removes_only_proven_stale_identity(jobs_root):
    store = JobStore(jobs_root)
    job_id = store.create(
        {"schema_version": "1", "job_type": "test"},
        {"schema_version": "1", "status": "submitted"},
    )
    lock_path = store.job_dir(job_id) / ".state.lock"
    stale = process_identity(__import__("os").getpid())
    stale["process_create_time"] -= 1000
    atomic_write_json(lock_path, stale)

    with JobLock(lock_path, timeout=0.5):
        assert lock_path.exists()
    assert not lock_path.exists()


def test_tail_is_bounded(jobs_root):
    store = JobStore(jobs_root)
    job_id = store.create(
        {"schema_version": "1", "job_type": "test"},
        {"schema_version": "1", "status": "submitted"},
    )
    for index in range(10):
        store.append_event(job_id, "line", {"index": index})

    tail = store.tail(job_id, 3)

    assert len(tail["events"]) == 3
    assert json.loads(tail["events"][-1])["data"]["index"] == 9


def test_production_schema_is_solver_free_and_guards_source(jobs_root):
    source = jobs_root / "baseline.mph"
    source.write_bytes(b"model")
    spec = validate_staged_sweep_spec(
        {
            "job_type": "staged_sweep",
            "source_model_path": str(source),
            "parameter_name": "wl",
            "parameter_values": [4.25, 4.251],
            "expressions": ["ewfd.Rtotal", "ewfd.Ttotal", "ewfd.Atotal"],
            "smoke_points": 1,
        }
    )

    assert len(spec["spec_fingerprint"]) == 64
    with pytest.raises(ValueError, match="must not overwrite"):
        validate_staged_sweep_spec({**spec, "checkpoint_model_path": str(source)})


def test_test_jobs_require_explicit_injection(jobs_root):
    with pytest.raises(ValueError, match="disabled"):
        JobManager(jobs_root).submit({"job_type": "test_sequence", "delays": [0.01]})
