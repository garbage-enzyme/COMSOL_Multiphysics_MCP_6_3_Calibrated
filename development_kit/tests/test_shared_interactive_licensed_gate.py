"""Solver-free contract tests for the licensed shared interactive gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).parents[1] / "scripts" / "shared_interactive_licensed_gate.py"


def _ascii_receipt() -> str:
    return (
        "D:/shared_interactive_gate_test_receipt.json"
        if os.name == "nt"
        else "/tmp/shared_interactive_gate_test_receipt.json"
    )


def test_shared_interactive_gate_dry_run_is_solver_free(tmp_path):
    receipt = Path(_ascii_receipt())
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "prepare",
            "--model-tag",
            "Model1",
            "--expected-label",
            "Untitled.mph",
            "--receipt",
            str(receipt),
            "--dry-run",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["spec"]["selector"] == {
        "tag": "Model1",
        "expected_label": "Untitled.mph",
        "expected_unsaved": True,
    }
    assert result["spec"]["solver_gate"]["publication_claim"] is False
    assert not receipt.exists()


def test_shared_interactive_readback_requires_declared_desktop_value(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "readback",
            "--model-tag",
            "Model1",
            "--expected-label",
            "Untitled.mph",
            "--receipt",
            _ascii_receipt(),
            "--dry-run",
        ],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 2
    assert "requires --expected-desktop-value" in completed.stderr
