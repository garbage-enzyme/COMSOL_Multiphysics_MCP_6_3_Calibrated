"""Read-only, threshold-free evidence collection for Wave Optics models."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any

from .ownership import ownership_manager


@dataclass
class EvidenceLedger:
    """Collect stable evidence codes without turning observations into policy."""

    observations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    unknowns: list[dict[str, Any]] = field(default_factory=list)
    integrity_errors: list[dict[str, Any]] = field(default_factory=list)

    def add(self, level: str, code: str, message: str, **evidence: Any) -> None:
        record = {"code": code, "message": message}
        if evidence:
            record["evidence"] = evidence
        target = {
            "observation": self.observations,
            "warning": self.warnings,
            "unknown": self.unknowns,
            "integrity_error": self.integrity_errors,
        }.get(level)
        if target is None:
            raise ValueError(f"unsupported evidence level: {level}")
        target.append(record)

    @property
    def inspection_status(self) -> str:
        if self.integrity_errors:
            return "integrity_blocked"
        if self.unknowns:
            return "partial"
        return "complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "observations": self.observations,
            "warnings": self.warnings,
            "unknowns": self.unknowns,
            "integrity_errors": self.integrity_errors,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_text(callable_value, ledger: EvidenceLedger, code: str) -> str | None:
    try:
        value = callable_value()
        return None if value is None else str(value)
    except Exception as exc:
        ledger.add("unknown", code, "Model metadata could not be read.", error=str(exc)[:300])
        return None


def collect_preflight_foundation(
    model,
    *,
    model_name: str,
    session_state: dict[str, Any],
    active_profile: str,
    expected_source_path: str | None = None,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Collect provenance and ownership without running or mutating clientapi."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be exact and non-empty")

    ledger = EvidenceLedger()
    loaded_path_text = _safe_text(model.file, ledger, "model_file_unreadable")
    model_label = _safe_text(model.name, ledger, "model_label_unreadable")
    comsol_version = _safe_text(model.version, ledger, "comsol_version_unreadable")
    loaded_path = Path(loaded_path_text).resolve() if loaded_path_text else None
    source_sha256 = None

    if loaded_path is None or not loaded_path.is_file():
        ledger.add(
            "unknown",
            "source_file_unavailable",
            "The loaded model has no readable source file for hashing.",
            loaded_path=loaded_path_text,
        )
    else:
        try:
            source_sha256 = _sha256(loaded_path)
            ledger.add(
                "observation",
                "source_hash_measured",
                "The loaded source file was hashed without modification.",
                sha256=source_sha256,
            )
        except OSError as exc:
            ledger.add(
                "unknown",
                "source_hash_unavailable",
                "The loaded source file could not be hashed.",
                error=str(exc)[:300],
            )

    if expected_source_path is not None:
        expected_path = Path(expected_source_path).resolve()
        if loaded_path is None or loaded_path != expected_path:
            ledger.add(
                "integrity_error",
                "source_path_mismatch",
                "Loaded source path does not match the caller-declared path.",
                expected=str(expected_path),
                actual=str(loaded_path) if loaded_path else None,
            )
    if expected_source_sha256 is not None:
        normalized_expected = expected_source_sha256.strip().lower()
        if source_sha256 is None or source_sha256.lower() != normalized_expected:
            ledger.add(
                "integrity_error",
                "source_hash_mismatch",
                "Measured source hash does not match the caller-declared hash.",
                expected=normalized_expected,
                actual=source_sha256,
            )

    ownership = ownership_manager.status(session_state=session_state)
    collision = bool(ownership.get("collision"))
    if collision:
        ledger.add(
            "integrity_error",
            "solver_collision",
            "Solver ownership evidence reports a collision.",
        )
    else:
        ledger.add(
            "observation",
            "solver_ownership_inspected",
            "Solver ownership was inspected without starting COMSOL.",
        )

    for section, code in (
        ("topology", "topology_not_inspected"),
        ("periodicity", "periodicity_not_inspected"),
        ("ports", "ports_not_inspected"),
        ("incidence", "incidence_not_inspected"),
        ("wavelength", "wavelength_not_inspected"),
        ("mesh_study_results", "mesh_study_results_not_inspected"),
    ):
        ledger.add(
            "unknown",
            code,
            f"The {section} evidence collector has not populated this section yet.",
        )

    return {
        "inspection_status": ledger.inspection_status,
        "assessment": {
            "mode": "evidence_only",
            "project_verdict": None,
            "long_sweep_recommendation": None,
        },
        "evidence": ledger.to_dict(),
        "provenance": {
            "requested_model_name": model_name,
            "model_label": model_label,
            "loaded_path": str(loaded_path) if loaded_path else loaded_path_text,
            "source_sha256": source_sha256,
            "comsol_version": comsol_version,
            "active_profile": active_profile,
        },
        "ownership": {
            "session": ownership.get("session"),
            "lease": ownership.get("lease"),
            "external_solver_processes": ownership.get("external_solver_processes", []),
            "collision": collision,
            "solve_permitted": not collision,
        },
        "topology": {},
        "periodicity": {},
        "ports": {},
        "incidence": {"physical_polarization_evidence": "label_only"},
        "wavelength": {},
        "mesh_study_results": {},
        "next_call": {
            "tool": "wave_optics_point_audit",
            "available": False,
            "missing_evidence": [
                "topology", "periodicity", "ports", "incidence", "wavelength",
                "mesh_study_results",
            ],
        },
    }


__all__ = ["EvidenceLedger", "collect_preflight_foundation"]
