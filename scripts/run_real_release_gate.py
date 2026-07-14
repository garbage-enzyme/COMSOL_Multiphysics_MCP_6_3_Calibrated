"""Explicit serial real-COMSOL release gate for a licensed pinned host."""

from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import psutil

from src.tools.ownership import SolverOwnership


ROOT = Path(__file__).resolve().parents[1]


def _comsol_pids() -> set[int]:
    names = {"comsol", "comsolmphserver", "comsolbatch"}
    found: set[int] = set()
    for process in psutil.process_iter(["pid", "name"]):
        try:
            if (process.info.get("name") or "").lower().split(".")[0] in names:
                found.add(int(process.info["pid"]))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True, choices=["RUN_REAL_COMSOL"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    owner = SolverOwnership()
    before_status = owner.status()
    before_pids = _comsol_pids()
    if before_status["collision"] or before_status["lease"]["state"] != "absent":
        raise SystemExit("real release gate requires no external solver and no lease")

    started = time.monotonic()
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "integration",
            "tests/integration/test_real_comsol.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    after_status = owner.status()
    after_pids = _comsol_pids()
    cleanup_passed = (
        after_pids == before_pids
        and after_status["lease"]["state"] == "absent"
        and not after_status["collision"]
    )

    receipt = {
        "schema_version": "1.0.0",
        "gate": "serial_real_comsol_release",
        "test_target": "tests/integration/test_real_comsol.py",
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "cleanup": {
            "comsol_pid_set_unchanged": after_pids == before_pids,
            "lease_absent": after_status["lease"]["state"] == "absent",
            "collision_absent": not after_status["collision"],
            "passed": cleanup_passed,
        },
        "environment": {
            "python": platform.python_version(),
            "mph": version("mph"),
            "mcp": version("mcp"),
            "comsol_build": "must_match_release/support_matrix.json and probe evidence",
            "java": "must_match_release/support_matrix.json and probe evidence",
        },
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if completed.returncode != 0 or not cleanup_passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
