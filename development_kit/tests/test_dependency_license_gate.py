"""Dependency-license review and fail-closed receipt tests."""

from __future__ import annotations

import json
from datetime import date
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

import pytest

from development_kit.scripts.dependency_license_gate import (
    build_license_receipt,
    declared_runtime_dependencies,
    load_license_review,
)

ROOT = Path(__file__).parents[2]
PYPROJECT = ROOT / "pyproject.toml"
REVIEW = ROOT / "development_kit" / "release" / "dependency_license_review.json"


def test_committed_runtime_dependencies_have_a_live_license_review() -> None:
    receipt = build_license_receipt(
        PYPROJECT,
        REVIEW,
        as_of=date(2026, 7, 18),
    )

    assert receipt["status"] == "passed"
    assert receipt["dependency_count"] == 7
    assert receipt["failures"] == []
    assert len(receipt["pyproject_sha256"]) == 64
    assert len(receipt["review_sha256"]) == 64
    assert "Users" not in json.dumps(receipt)


def _metadata(name: str, version: str, license_value: str) -> SimpleNamespace:
    message = Message()
    message["Name"] = name
    message["Version"] = version
    message["License"] = license_value
    return SimpleNamespace(metadata=message)


def test_review_fails_closed_for_unreviewed_and_stale_dependencies(
    tmp_path: Path,
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\ndependencies = ["alpha>=1", "beta>=1"]\n',
        encoding="utf-8",
    )
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "schema_name": "comsol_mcp.dependency_license_review",
                "schema_version": "1.0.0",
                "reviewed_on": "2026-01-01",
                "expires_on": "2027-01-01",
                "entries": [
                    {
                        "dependency": "alpha",
                        "accepted_signals": ["license:MIT"],
                        "reason": "Reviewed.",
                    },
                    {
                        "dependency": "stale",
                        "accepted_signals": ["license:MIT"],
                        "reason": "Reviewed.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    receipt = build_license_receipt(
        pyproject,
        review,
        as_of=date(2026, 7, 18),
        distribution_provider=lambda name: _metadata(name, "1.0", "MIT"),
    )

    assert receipt["status"] == "failed"
    assert {item["reason_code"] for item in receipt["failures"]} >= {
        "unreviewed_dependency",
        "stale_review_entry",
    }


def test_expired_or_unmatched_license_review_fails_closed(tmp_path: Path) -> None:
    review_value = json.loads(REVIEW.read_text(encoding="utf-8"))
    review_value["reviewed_on"] = "2025-01-01"
    review_value["expires_on"] = "2026-01-01"
    review = tmp_path / "review.json"
    review.write_text(json.dumps(review_value), encoding="utf-8")

    receipt = build_license_receipt(
        PYPROJECT,
        review,
        as_of=date(2026, 7, 18),
        distribution_provider=lambda name: _metadata(name, "1.0", "UNKNOWN"),
    )

    reasons = {item["reason_code"] for item in receipt["failures"]}
    assert "review_expired" in reasons
    assert "license_metadata_unmatched" in reasons


def test_review_schema_and_dependency_declarations_are_bounded(tmp_path: Path) -> None:
    invalid_review = tmp_path / "review.json"
    invalid_review.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="fields"):
        load_license_review(invalid_review)

    duplicate = tmp_path / "pyproject.toml"
    duplicate.write_text(
        '[project]\ndependencies = ["same>=1", "same<2"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        declared_runtime_dependencies(duplicate)
