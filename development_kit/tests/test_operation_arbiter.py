"""Durable operation-arbitration and responsive-control regression tests."""

from __future__ import annotations

import json
import threading

import psutil

from src.operation_arbiter import OperationArbiter, guard_tool_call
from src.tools.catalog import TOOL_METADATA


def test_concurrent_comsol_bound_calls_fail_fast_with_retry_evidence(tmp_path, monkeypatch):
    arbiter = OperationArbiter(
        tmp_path,
        pid=100,
        process_create_time=10.0,
        process_probe=lambda pid: 10.0,
        clock=lambda: 20.0,
    )
    monkeypatch.setattr("src.operation_arbiter.get_operation_arbiter", lambda: arbiter)
    entered = threading.Event()
    release = threading.Event()

    def blocking_call():
        entered.set()
        assert release.wait(2.0)
        return {"success": True, "value": "first"}

    first_tool = guard_tool_call(
        blocking_call,
        tool_name="study_solve",
        side_effect_class="solver_execution",
        concurrency_class="comsol_bound",
    )
    second_tool = guard_tool_call(
        lambda: {"success": True, "value": "second"},
        tool_name="param_set",
        side_effect_class="model_mutation",
        concurrency_class="comsol_bound",
    )
    first_result = {}
    thread = threading.Thread(target=lambda: first_result.update(first_tool()))
    thread.start()
    assert entered.wait(1.0)

    busy = second_tool()
    release.set()
    thread.join(2.0)

    assert busy["success"] is False
    assert busy["operation_gate"]["state"] == "active"
    assert busy["operation_gate"]["retryable"] is True
    assert busy["operation_gate"]["active_operation"]["tool_name"] == "study_solve"
    assert first_result["success"] is True
    assert first_result["operation_gate"]["release"]["verified"] is True
    assert not arbiter.lock_path.exists()


def test_control_plane_call_remains_responsive_while_solver_call_blocks(
    tmp_path, monkeypatch
):
    arbiter = OperationArbiter(
        tmp_path,
        pid=100,
        process_create_time=10.0,
        process_probe=lambda pid: 10.0,
    )
    monkeypatch.setattr("src.operation_arbiter.get_operation_arbiter", lambda: arbiter)
    claim, _ = arbiter.try_acquire(
        tool_name="study_solve", side_effect_class="solver_execution"
    )
    assert claim is not None
    called = []
    status = guard_tool_call(
        lambda: called.append(True) or {"success": True},
        tool_name="solver_status",
        side_effect_class="read_only",
        concurrency_class="control_plane",
    )

    assert status()["success"] is True
    assert called == [True]
    assert arbiter.release(claim)["verified"] is True


def test_stale_lock_is_recovered_after_coordinator_restart(tmp_path):
    missing_pid = 999_999_991

    def probe(pid):
        if pid == missing_pid:
            raise psutil.NoSuchProcess(pid)
        return 20.0

    stale = {
        "schema_name": "comsol_mcp.operation_lock",
        "schema_version": "1.0.0",
        "operation_id": "old-operation",
        "tool_name": "param_set",
        "side_effect_class": "model_mutation",
        "pid": missing_pid,
        "process_create_time": 1.0,
        "acquired_at_epoch": 2.0,
    }
    (tmp_path / "operation.lock").write_text(
        json.dumps(stale, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    arbiter = OperationArbiter(
        tmp_path,
        pid=200,
        process_create_time=20.0,
        process_probe=probe,
    )

    claim, evidence = arbiter.try_acquire(
        tool_name="study_solve", side_effect_class="solver_execution"
    )

    assert claim is not None
    assert evidence["state"] == "acquired"
    assert evidence["recovered_stale_lock"] is True
    assert arbiter.release(claim)["verified"] is True


def test_malformed_lock_fails_closed(tmp_path):
    (tmp_path / "operation.lock").write_bytes(b"not-json")
    arbiter = OperationArbiter(
        tmp_path,
        pid=200,
        process_create_time=20.0,
        process_probe=lambda pid: 20.0,
    )

    claim, evidence = arbiter.try_acquire(
        tool_name="study_solve", side_effect_class="solver_execution"
    )

    assert claim is None
    assert evidence["state"] == "uncertain"
    assert evidence["retryable"] is False
    assert (tmp_path / "operation.lock").read_bytes() == b"not-json"


def test_metadata_keeps_required_tools_outside_comsol_mutex():
    for name in (
        "capabilities", "solver_status", "job_status", "job_cancel",
        "manual_search", "manual_read_pages", "spectral_characterize",
        "convergence_evaluate", "branch_continuation_plan",
    ):
        assert TOOL_METADATA[name].concurrency_class != "comsol_bound"
    assert TOOL_METADATA["study_solve"].concurrency_class == "comsol_bound"
    assert TOOL_METADATA["param_set"].concurrency_class == "comsol_bound"
