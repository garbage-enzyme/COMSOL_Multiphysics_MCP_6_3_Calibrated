"""Unit tests for durable workflow execution without a COMSOL client."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from src.tools.workflow import (
    _csv_value,
    _scalarize,
    run_mesh_convergence,
    run_staged_parametric_sweep,
)


class FakeEntityList:
    def __init__(self, entities):
        self.entities = entities

    def tags(self):
        return list(self.entities)

    def get(self, tag):
        return self.entities[tag]


class FakeStep:
    def __init__(self):
        self.properties = {}

    def set(self, key, value):
        self.properties[key] = value


class FakeStudy:
    def __init__(self, java):
        self.java = java
        self.step = FakeStep()
        self.run_count = 0

    def label(self):
        return "Study 1"

    def feature(self, _tag):
        return self.step

    def run(self):
        self.run_count += 1
        value = self.java.parameters.values.get("wl")
        remaining = self.java.failures.get(value, 0)
        if remaining:
            self.java.failures[value] = remaining - 1
            raise RuntimeError(f"planned failure for {value}")


class FakeParameters:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value


class FakeSize:
    def __init__(self):
        self.properties = {}

    def set(self, key, value):
        self.properties[key] = value


class FakeMesh:
    def __init__(self):
        self.size = FakeSize()
        self.run_count = 0

    def feature(self, _tag):
        return self.size

    def run(self):
        self.run_count += 1

    def getNumElem(self):
        return 1000 + self.run_count

    def getNumVertex(self):
        return 500 + self.run_count


class FakeComponent:
    def __init__(self):
        self.mesh_node = FakeMesh()

    def mesh(self, _tag):
        return self.mesh_node


class FakeJava:
    def __init__(self, failures=None):
        self.parameters = FakeParameters()
        self.failures = dict(failures or {})
        self.study_node = FakeStudy(self)
        self.studies = FakeEntityList({"std1": self.study_node})
        self.component_node = FakeComponent()
        self.saved = []

    def param(self):
        return self.parameters

    def study(self, tag=None):
        return self.studies if tag is None else self.studies.get(tag)

    def component(self, _tag):
        return self.component_node

    def save(self, path):
        self.saved.append(path)


class FakeModel:
    def __init__(self, failures=None):
        self.java = FakeJava(failures)

    def name(self):
        return "fake"

    def evaluate(self, expressions):
        raw = self.java.parameters.values.get("wl", "0")
        value = float(str(raw).split("[", 1)[0])
        arrays = [np.array([value + index]) for index, _ in enumerate(expressions)]
        return arrays[0] if len(arrays) == 1 else arrays


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_staged_sweep_retries_and_checkpoints(tmp_path):
    csv_path = tmp_path / "sweep.csv"
    checkpoint = tmp_path / "checkpoint.mph"
    model = FakeModel(failures={"1[m]": 1})

    result = run_staged_parametric_sweep(
        model,
        "wl",
        [1, 2],
        ["A"],
        parameter_unit="m",
        study_step_tag="wave",
        study_step_unit="m",
        csv_path=str(csv_path),
        max_retries=1,
        checkpoint_model_path=str(checkpoint),
    )

    assert result["success"] is True
    assert result["n_points"] == 2
    assert result["rows"][0]["attempt"] == 2
    assert [row["status"] for row in read_csv(csv_path)] == ["success", "success"]
    assert len(model.java.saved) == 2


def test_staged_sweep_resumes_legacy_csv(tmp_path):
    csv_path = tmp_path / "legacy.csv"
    csv_path.write_text(
        "wl,parameter_value,solve_sec,A\n1,1[m],0.1,1.0\n",
        encoding="utf-8",
    )
    model = FakeModel()

    result = run_staged_parametric_sweep(
        model,
        "wl",
        [1, 2],
        ["A"],
        parameter_unit="m",
        csv_path=str(csv_path),
        resume_csv=True,
    )

    rows = read_csv(csv_path)
    assert result["n_skipped"] == 1
    assert result["n_points"] == 1
    assert [row["parameter_value"] for row in rows] == ["1[m]", "2[m]"]
    assert [row["status"] for row in rows] == ["success", "success"]


def test_staged_sweep_records_error_and_continues(tmp_path):
    csv_path = tmp_path / "errors.csv"
    model = FakeModel(failures={"2[m]": 1})

    result = run_staged_parametric_sweep(
        model,
        "wl",
        [1, 2, 3],
        ["A"],
        parameter_unit="m",
        csv_path=str(csv_path),
        continue_on_error=True,
    )

    assert result["success"] is False
    assert result["n_points"] == 2
    assert result["n_failed"] == 1
    assert [row["status"] for row in read_csv(csv_path)] == [
        "success",
        "error",
        "success",
    ]


def test_mesh_convergence_resumes_completed_levels(tmp_path):
    csv_path = tmp_path / "mesh.csv"
    model = FakeModel()
    first = run_mesh_convergence(
        model,
        [{"name": "coarse", "properties": {"hmax": "0.1"}}],
        ["A"],
        csv_path=str(csv_path),
    )
    resumed = run_mesh_convergence(
        model,
        [
            {"name": "coarse", "properties": {"hmax": "0.1"}},
            {"name": "fine", "properties": {"hmax": "0.05"}},
        ],
        ["A"],
        csv_path=str(csv_path),
        resume_csv=True,
    )

    assert first["success"] is True
    assert resumed["n_skipped"] == 1
    assert resumed["n_levels"] == 1
    assert [row["level"] for row in read_csv(csv_path)] == ["coarse", "fine"]


def test_complex_values_are_json_safe_and_csv_serializable():
    value = _scalarize(np.array([1.5 - 0.25j]))

    assert value == {"real": 1.5, "imag": -0.25}
    assert _csv_value(value) == "1.5+-0.25i"
