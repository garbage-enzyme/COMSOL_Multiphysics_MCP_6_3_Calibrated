"""Versioned canonicalization and durable I/O primitive tests."""

from __future__ import annotations

import hashlib

import pytest

from src.durable import (
    append_csv_row,
    append_jsonl_record,
    atomic_write_bytes,
    canonical_json_v1,
    canonical_sha256_v1,
    domain_sha256_v2,
    read_complete_jsonl,
    sha256_file_bounded,
)


def test_legacy_canonical_bytes_and_hash_are_golden_and_order_independent():
    first = {"b": 1, "a": "é", "n": None}
    second = {"n": None, "a": "é", "b": 1}
    expected = b'{"a":"\xc3\xa9","b":1,"n":null}'

    assert canonical_json_v1(first) == canonical_json_v1(second) == expected
    assert canonical_sha256_v1(first) == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {"x": object()}])
def test_canonical_json_rejects_nonfinite_and_unsupported_values(value):
    with pytest.raises(ValueError):
        canonical_json_v1(value)


def test_domain_separation_changes_new_identities_without_changing_legacy_bytes():
    value = {"state": "accepted", "ordinal": 1}
    legacy = canonical_json_v1(value)
    first = domain_sha256_v2("job.state", value)
    second = domain_sha256_v2("artifact.state", value)

    assert first != second
    assert canonical_json_v1(value) == legacy


def test_bounded_file_hash_reports_exact_bytes_and_refuses_overflow(tmp_path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"complete-artifact")
    receipt = sha256_file_bounded(path, max_bytes=64)

    assert receipt == {
        "sha256": hashlib.sha256(b"complete-artifact").hexdigest(),
        "byte_count": 17,
    }
    with pytest.raises(ValueError, match="hashing limit"):
        sha256_file_bounded(path, max_bytes=16)


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("before_temporary_write", b"old"),
        ("after_temporary_write", b"old"),
        ("after_file_fsync", b"old"),
        ("after_replace", b"new-complete"),
        ("after_directory_fsync", b"new-complete"),
    ],
)
def test_atomic_fault_injection_never_exposes_partial_terminal_bytes(
    tmp_path,
    stage,
    expected,
):
    path = tmp_path / "state.json"
    path.write_bytes(b"old")

    def fail(observed_stage, _path):
        if observed_stage == stage:
            raise RuntimeError("injected crash")

    with pytest.raises(RuntimeError, match="injected crash"):
        atomic_write_bytes(path, b"new-complete", stage_hook=fail)

    assert path.read_bytes() == expected
    assert list(tmp_path.glob(".*.tmp")) == []


def test_jsonl_recovery_distinguishes_absent_valid_incomplete_and_corrupt(tmp_path):
    path = tmp_path / "events.jsonl"
    assert read_complete_jsonl(path)["state"] == "absent"

    append_jsonl_record(path, {"sequence": 1})
    append_jsonl_record(path, {"sequence": 2})
    valid = read_complete_jsonl(path)
    assert valid["state"] == "current_valid"
    assert valid["records"] == [{"sequence": 1}, {"sequence": 2}]

    path.write_bytes(path.read_bytes() + b'{"sequence":3')
    incomplete = read_complete_jsonl(path)
    assert incomplete["state"] == "incomplete"
    assert incomplete["records"] == valid["records"]
    assert incomplete["trailing_byte_count"] > 0

    path.write_bytes(b'{"sequence":1}\nnot-json\n')
    assert read_complete_jsonl(path)["state"] == "corrupt"


def test_versioned_jsonl_recovery_distinguishes_legacy_without_rewriting(tmp_path):
    path = tmp_path / "legacy.jsonl"
    append_jsonl_record(path, {"schema_version": "1", "sequence": 1})
    original = path.read_bytes()

    receipt = read_complete_jsonl(
        path,
        version_field="schema_version",
        current_version="2",
        legacy_versions=("1",),
    )

    assert receipt["state"] == "legacy_valid"
    assert path.read_bytes() == original


def test_csv_append_quotes_one_complete_row_per_fsync_boundary(tmp_path):
    path = tmp_path / "rows.csv"
    append_csv_row(path, ["a,b", 1, "line"])
    append_csv_row(path, ["c", 2, "next"])

    assert path.read_text(encoding="utf-8").splitlines() == [
        '"a,b",1,line',
        "c,2,next",
    ]
