from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import uuid

import pytest

from src.jobs.manager import JobManager
from src.jobs.store import JobStore, process_identity
from src.jobs.validation_matrix import normalize_validation_matrix_spec
from src.jobs.validation_rows import read_validation_rows
from src.jobs.validation_worker import _run


@pytest.fixture
def ascii_root():
    root = Path("D:/comsol_runtime_test") / f"pytest-validation-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _raw_spec(source: Path, *, points=2):
    matrix = []
    for index in range(points):
        point_id = f"point-{index}"
        matrix.append(
            {
                "point_id": point_id,
                "configuration_sha256": f"{index + 1:x}" * 64,
                "wavelength": {"value": 5.1 + 0.1 * index, "unit": "um", "parameter": "wl"},
                "collectors": [
                    {"name": "wave_optics_point_audit", "inputs": {"component_tag": "comp1"}}
                ],
                "expected_artifact_ids": [f"audit-{index}"],
            }
        )
    return {
        "job_type": "validation_matrix",
        "source_model_path": str(source),
        "points": matrix,
        "point_limit": points,
        "cores": 1,
        "resource_policy": {
            "wall_time_budget_seconds": 120,
            "minimum_next_point_seconds": 1,
            "max_mesh_elements": 100,
        },
    }


def _create_job(root: Path, spec):
    store = JobStore(root)
    identity = process_identity(os.getpid())
    job_id = store.create(
        spec,
        {
            "schema_version": "2",
            "status": "submitted",
            "attempt": 1,
            "worker_pid": identity["pid"],
            "worker_process_create_time": identity["process_create_time"],
            "worker_command_signature": identity["command_signature"],
            "progress": {"completed": 0, "total": len(spec["points"])},
            "last_error": None,
        },
    )
    return store, job_id


class FakeModel:
    def name(self):
        return "fixture"


class FakeClient:
    port = None

    def __init__(self):
        self.cleared = False

    def load(self, _path):
        return FakeModel()

    def clear(self):
        self.cleared = True


class FakeOwnership:
    def __init__(self):
        self.acquired = False
        self.released = False
        self.heartbeats = 0

    def preflight(self, **_kwargs):
        return {"ready": True, "blockers": []}

    def acquire(self, **_kwargs):
        self.acquired = True
        return {"success": True}

    def heartbeat(self, **_kwargs):
        self.heartbeats += 1
        return {"success": True}

    def release(self):
        self.released = True
        return {"success": True}


def _telemetry(mesh_elements=10):
    def provide(stage, _point_id, _model, _directory, elapsed):
        return {
            "stage": stage,
            "observed_at_epoch": 1.0 + elapsed,
            "mesh_elements": mesh_elements,
            "elapsed_wall_seconds": elapsed,
        }

    return provide


def _collector(point, _collector, artifact_dir):
    manifest = artifact_dir / "manifest.json"
    manifest.write_text(json.dumps({"point": point["point_id"]}), encoding="utf-8")
    return {
        "success": True,
        "audit_status": "measurement_complete",
        "artifacts": {"manifest": str(manifest)},
    }


def test_validation_worker_reuses_one_claim_and_completes_exact_rows(tmp_path, ascii_root):
    source = tmp_path / "fixture.mph"
    source.write_bytes(b"model")
    spec = normalize_validation_matrix_spec(_raw_spec(source))
    store, job_id = _create_job(ascii_root / "jobs", spec)
    ownership = FakeOwnership()
    client = FakeClient()

    code = _run(
        str(store.root),
        job_id,
        ownership_factory=lambda *_args: ownership,
        client_factory=lambda _spec: client,
        collector_executor=_collector,
        telemetry_provider=_telemetry(),
        native_cancel_enabled=False,
    )

    state = store.read_state(job_id)
    assert code == 0
    assert state["status"] == "completed"
    assert state["progress"] == {"completed": 2, "total": 2}
    assert state["source_unchanged"] is True
    assert ownership.acquired and ownership.released
    assert ownership.heartbeats >= 3
    assert client.cleared
    assert [row["point_id"] for row in read_validation_rows(store.job_dir(job_id) / "matrix_rows.jsonl", spec)] == [
        "point-0",
        "point-1",
    ]


def test_validation_worker_resource_refusal_is_resumable_without_false_row(tmp_path, ascii_root):
    source = tmp_path / "fixture.mph"
    source.write_bytes(b"model")
    spec = normalize_validation_matrix_spec(_raw_spec(source, points=1))
    store, job_id = _create_job(ascii_root / "jobs", spec)
    ownership = FakeOwnership()

    code = _run(
        str(store.root),
        job_id,
        ownership_factory=lambda *_args: ownership,
        client_factory=lambda _spec: FakeClient(),
        collector_executor=lambda *_args: (_ for _ in ()).throw(AssertionError("must not solve")),
        telemetry_provider=_telemetry(mesh_elements=101),
        native_cancel_enabled=False,
    )

    state = store.read_state(job_id)
    assert code == 0
    assert state["status"] == "interrupted"
    assert state["last_error"]["type"] == "ResourceAdmissionStop"
    assert not (store.job_dir(job_id) / "matrix_rows.jsonl").exists()
    assert ownership.released


def test_manager_routes_validation_submit_and_resume_to_dedicated_worker(tmp_path, ascii_root, monkeypatch):
    source = tmp_path / "fixture.mph"
    source.write_bytes(b"model")
    manager = JobManager(ascii_root / "jobs", preflight=lambda **_kwargs: {"ready": True})
    identity = process_identity(os.getpid())
    modules = []

    def launch(_job_id, module):
        modules.append(module)
        return identity

    monkeypatch.setattr(manager, "_launch_worker", launch)
    submitted = manager.submit(_raw_spec(source))
    assert manager.store.read_state(submitted["job_id"])["progress"] == {
        "completed": 0,
        "total": 2,
    }
    assert modules == ["src.jobs.validation_worker"]

    manager.store.update_state(submitted["job_id"], "interrupted", event="test_interrupt")
    resumed = manager.resume(submitted["job_id"])
    assert resumed["attempt"] == 2
    assert modules == ["src.jobs.validation_worker", "src.jobs.validation_worker"]


def test_manager_rejects_matrix_bounds_before_preflight_or_launch(tmp_path, ascii_root, monkeypatch):
    source = tmp_path / "fixture.mph"
    source.write_bytes(b"model")
    calls = []
    manager = JobManager(ascii_root / "jobs", preflight=lambda **_kwargs: calls.append("preflight"))
    monkeypatch.setattr(manager, "_launch_worker", lambda *_args: calls.append("launch"))
    raw = _raw_spec(source, points=1)
    raw["point_limit"] = 0

    try:
        manager.submit(raw)
    except ValueError as exc:
        assert "point_limit" in str(exc)
    else:
        raise AssertionError("invalid matrix must fail")
    assert calls == []
