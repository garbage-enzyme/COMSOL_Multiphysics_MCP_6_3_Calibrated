"""Mock gates for threshold-free, read-only Wave Optics preflight evidence."""

from __future__ import annotations

import hashlib

import pytest

from src.tools.wave_optics_preflight import EvidenceLedger, collect_preflight_foundation


class MetadataOnlyModel:
    def __init__(self, path):
        self._path = path

    def file(self):
        return str(self._path)

    def name(self):
        return "LoadedModel"

    def version(self):
        return "6.4.0.293"

    @property
    def java(self):
        raise AssertionError("foundation collector must not touch clientapi")


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_evidence_ledger_has_stable_status_precedence():
    ledger = EvidenceLedger()
    assert ledger.inspection_status == "complete"
    ledger.add("warning", "warning_code", "warning")
    assert ledger.inspection_status == "complete"
    ledger.add("unknown", "unknown_code", "unknown")
    assert ledger.inspection_status == "partial"
    ledger.add("integrity_error", "integrity_code", "blocked")
    assert ledger.inspection_status == "integrity_blocked"


def test_foundation_reports_evidence_only_and_preserves_source(tmp_path, monkeypatch):
    source = tmp_path / "source.mph"
    source.write_bytes(b"immutable model bytes")
    source_hash = _hash(source)
    monkeypatch.setattr(
        "src.tools.wave_optics_preflight.ownership_manager.status",
        lambda **_kwargs: {
            "session": {"connected": True},
            "lease": {"state": "absent"},
            "external_solver_processes": [],
            "collision": False,
        },
    )

    result = collect_preflight_foundation(
        MetadataOnlyModel(source),
        model_name="ExactModel",
        session_state={"connected": True},
        active_profile="wave_optics",
        expected_source_path=str(source),
        expected_source_sha256=source_hash,
    )

    assert result["inspection_status"] == "partial"
    assert result["assessment"] == {
        "mode": "evidence_only",
        "project_verdict": None,
        "long_sweep_recommendation": None,
    }
    assert result["provenance"]["source_sha256"] == source_hash
    assert result["ownership"]["solve_permitted"] is True
    assert result["incidence"]["physical_polarization_evidence"] == "label_only"
    assert _hash(source) == source_hash


@pytest.mark.parametrize("mismatch", ["path", "hash"])
def test_foundation_blocks_only_declared_integrity_mismatch(tmp_path, monkeypatch, mismatch):
    source = tmp_path / "source.mph"
    source.write_bytes(b"source")
    monkeypatch.setattr(
        "src.tools.wave_optics_preflight.ownership_manager.status",
        lambda **_kwargs: {"collision": False},
    )
    kwargs = {
        "expected_source_path": str(source),
        "expected_source_sha256": _hash(source),
    }
    if mismatch == "path":
        kwargs["expected_source_path"] = str(tmp_path / "other.mph")
    else:
        kwargs["expected_source_sha256"] = "0" * 64

    result = collect_preflight_foundation(
        MetadataOnlyModel(source),
        model_name="ExactModel",
        session_state={},
        active_profile="full",
        **kwargs,
    )

    assert result["inspection_status"] == "integrity_blocked"
    codes = {item["code"] for item in result["evidence"]["integrity_errors"]}
    assert f"source_{mismatch}_mismatch" in codes


def test_foundation_treats_solver_collision_as_integrity_blocker(tmp_path, monkeypatch):
    source = tmp_path / "source.mph"
    source.write_bytes(b"source")
    monkeypatch.setattr(
        "src.tools.wave_optics_preflight.ownership_manager.status",
        lambda **_kwargs: {"collision": True, "external_solver_processes": [{"pid": 1}]},
    )

    result = collect_preflight_foundation(
        MetadataOnlyModel(source),
        model_name="ExactModel",
        session_state={},
        active_profile="core",
    )

    assert result["inspection_status"] == "integrity_blocked"
    assert result["ownership"]["solve_permitted"] is False


def test_foundation_requires_exact_nonempty_model_name(tmp_path):
    with pytest.raises(ValueError, match="exact and non-empty"):
        collect_preflight_foundation(
            MetadataOnlyModel(tmp_path / "missing.mph"),
            model_name="",
            session_state={},
            active_profile="full",
        )
