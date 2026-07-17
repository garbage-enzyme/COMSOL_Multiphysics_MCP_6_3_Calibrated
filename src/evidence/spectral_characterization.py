"""Deterministic solver-free characterization of provenance-bound spectra."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from typing import Any, Mapping


SPECTRAL_BUNDLE_SCHEMA = "comsol_mcp.spectral_point_bundle"
SPECTRAL_DECISION_SCHEMA = "comsol_mcp.spectral_analysis_decision"
SPECTRAL_SCHEMA_VERSION = "1.0.0"
MAX_SPECTRAL_POINTS = 4096
MAX_PARAMETER_STATE_BYTES = 64 * 1024

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_SOURCE_FIELDS = {"relative_identity", "sha256"}
_WAVELENGTH_FIELDS = {
    "unit",
    "requested_field",
    "evaluated_field",
    "frequency_derived_field",
    "frequency_relation",
}
_ROW_FIELDS = {
    "row_id",
    "raw_row_sha256",
    "configuration_sha256",
    "requested_wavelength_m",
    "evaluated_wavelength_m",
    "frequency_wavelength_m",
    "R",
    "T",
    "A",
}
_POLICY_FIELDS = {
    "response_quantity",
    "candidate_polarity",
    "passivity_abs_tolerance",
    "closure_abs_tolerance",
    "wavelength_sync_abs_m",
    "flat_response_abs_tolerance",
    "minimum_point_count",
}


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("spectral evidence must contain finite JSON values") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be an object with string keys")
    return dict(value)


def _exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    item = _mapping(value, label)
    if set(item) != expected:
        raise ValueError(f"{label} fields are invalid")
    return item


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a bounded portable identifier")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value.lower()):
        raise ValueError(f"{label} must be exactly 64 hexadecimal characters")
    return value.lower()


def _finite(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    if nonnegative and result < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return result


def _relative_identity(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError(f"{label} must be a bounded relative identity")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"{label} must be relative and traversal-free")
    return normalized


def _bounded_text(value: Any, label: str, *, maximum: int = 1024) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{label} must be nonempty and at most {maximum} characters")
    return value


def _normalize_source(value: Any) -> dict[str, str]:
    item = _exact_fields(value, _SOURCE_FIELDS, "source_model")
    return {
        "relative_identity": _relative_identity(
            item["relative_identity"], "source_model.relative_identity"
        ),
        "sha256": _hash(item["sha256"], "source_model.sha256"),
    }


def _normalize_wavelength_convention(value: Any) -> dict[str, str]:
    item = _exact_fields(value, _WAVELENGTH_FIELDS, "wavelength_convention")
    if item["unit"] != "m":
        raise ValueError("wavelength_convention.unit must be 'm'")
    if item["frequency_relation"] != "c_const/frequency":
        raise ValueError(
            "wavelength_convention.frequency_relation must be 'c_const/frequency'"
        )
    return {
        key: _bounded_text(item[key], f"wavelength_convention.{key}", maximum=128)
        for key in sorted(_WAVELENGTH_FIELDS)
    }


def _normalize_expressions(value: Any) -> dict[str, str]:
    item = _exact_fields(value, {"R", "T", "A"}, "expressions")
    return {
        name: _bounded_text(item[name], f"expressions.{name}")
        for name in ("R", "T", "A")
    }


def _normalize_row(value: Any, index: int, configuration_sha256: str) -> dict[str, Any]:
    label = f"rows[{index}]"
    item = _exact_fields(value, _ROW_FIELDS, label)
    row_configuration = _hash(
        item["configuration_sha256"], f"{label}.configuration_sha256"
    )
    if row_configuration != configuration_sha256:
        raise ValueError(f"{label}.configuration_sha256 does not match the bundle")
    return {
        "row_id": _identifier(item["row_id"], f"{label}.row_id"),
        "raw_row_sha256": _hash(item["raw_row_sha256"], f"{label}.raw_row_sha256"),
        "configuration_sha256": row_configuration,
        "requested_wavelength_m": _finite(
            item["requested_wavelength_m"], f"{label}.requested_wavelength_m"
        ),
        "evaluated_wavelength_m": _finite(
            item["evaluated_wavelength_m"], f"{label}.evaluated_wavelength_m"
        ),
        "frequency_wavelength_m": _finite(
            item["frequency_wavelength_m"], f"{label}.frequency_wavelength_m"
        ),
        "R": _finite(item["R"], f"{label}.R"),
        "T": _finite(item["T"], f"{label}.T"),
        "A": _finite(item["A"], f"{label}.A"),
    }


def build_spectral_point_bundle(
    *,
    bundle_id: str,
    source_model: Mapping[str, Any],
    configuration_sha256: str,
    parameter_state: Mapping[str, Any],
    wavelength_convention: Mapping[str, Any],
    expressions: Mapping[str, Any],
    rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Normalize immutable point projections and bind them to their raw row hashes."""
    configuration = _hash(configuration_sha256, "configuration_sha256")
    if not isinstance(rows, list) or not 3 <= len(rows) <= MAX_SPECTRAL_POINTS:
        raise ValueError(f"rows must contain 3..{MAX_SPECTRAL_POINTS} entries")
    parameters = _mapping(parameter_state, "parameter_state")
    if len(_canonical_bytes(parameters)) > MAX_PARAMETER_STATE_BYTES:
        raise ValueError("parameter_state exceeds its byte limit")
    normalized_rows = [
        _normalize_row(row, index, configuration) for index, row in enumerate(rows)
    ]
    row_ids = [row["row_id"] for row in normalized_rows]
    raw_hashes = [row["raw_row_sha256"] for row in normalized_rows]
    wavelengths = [row["requested_wavelength_m"] for row in normalized_rows]
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("row IDs must be unique")
    if len(raw_hashes) != len(set(raw_hashes)):
        raise ValueError("raw row hashes must be unique")
    if any(value <= 0.0 for value in wavelengths):
        raise ValueError("requested wavelengths must be positive")
    if any(right <= left for left, right in zip(wavelengths, wavelengths[1:])):
        raise ValueError("requested wavelengths must be sorted and unique")
    body = {
        "schema_name": SPECTRAL_BUNDLE_SCHEMA,
        "schema_version": SPECTRAL_SCHEMA_VERSION,
        "bundle_id": _identifier(bundle_id, "bundle_id"),
        "source_model": _normalize_source(source_model),
        "configuration_sha256": configuration,
        "parameter_state": deepcopy(parameters),
        "parameter_state_sha256": _sha256(parameters),
        "wavelength_convention": _normalize_wavelength_convention(
            wavelength_convention
        ),
        "expressions": _normalize_expressions(expressions),
        "rows": normalized_rows,
    }
    return {**body, "bundle_sha256": _sha256(body)}


def validate_spectral_point_bundle(value: Any) -> dict[str, Any]:
    """Validate a canonical spectral point bundle without mutating it."""
    item = _mapping(value, "spectral_bundle")
    expected = {
        "schema_name",
        "schema_version",
        "bundle_id",
        "source_model",
        "configuration_sha256",
        "parameter_state",
        "parameter_state_sha256",
        "wavelength_convention",
        "expressions",
        "rows",
        "bundle_sha256",
    }
    if set(item) != expected:
        raise ValueError("spectral bundle fields are invalid")
    if (
        item["schema_name"] != SPECTRAL_BUNDLE_SCHEMA
        or item["schema_version"] != SPECTRAL_SCHEMA_VERSION
    ):
        raise ValueError("spectral bundle schema is unsupported")
    rebuilt = build_spectral_point_bundle(
        bundle_id=item["bundle_id"],
        source_model=item["source_model"],
        configuration_sha256=item["configuration_sha256"],
        parameter_state=item["parameter_state"],
        wavelength_convention=item["wavelength_convention"],
        expressions=item["expressions"],
        rows=item["rows"],
    )
    if item["parameter_state_sha256"] != rebuilt["parameter_state_sha256"]:
        raise ValueError("parameter state hash does not match")
    if item["bundle_sha256"] != rebuilt["bundle_sha256"] or item != rebuilt:
        raise ValueError("spectral bundle is noncanonical or its hash does not match")
    return deepcopy(rebuilt)


def _normalize_analysis_policy(value: Any) -> dict[str, Any]:
    item = _exact_fields(value, _POLICY_FIELDS, "analysis_policy")
    response = item["response_quantity"]
    polarity = item["candidate_polarity"]
    if response not in {"R", "T", "A"}:
        raise ValueError("analysis_policy.response_quantity must be R, T, or A")
    if polarity not in {"maximum", "minimum"}:
        raise ValueError(
            "analysis_policy.candidate_polarity must be maximum or minimum"
        )
    minimum = item["minimum_point_count"]
    if isinstance(minimum, bool) or not isinstance(minimum, int) or not 3 <= minimum <= 101:
        raise ValueError("analysis_policy.minimum_point_count must be 3..101")
    return {
        "response_quantity": response,
        "candidate_polarity": polarity,
        "passivity_abs_tolerance": _finite(
            item["passivity_abs_tolerance"],
            "analysis_policy.passivity_abs_tolerance",
            nonnegative=True,
        ),
        "closure_abs_tolerance": _finite(
            item["closure_abs_tolerance"],
            "analysis_policy.closure_abs_tolerance",
            nonnegative=True,
        ),
        "wavelength_sync_abs_m": _finite(
            item["wavelength_sync_abs_m"],
            "analysis_policy.wavelength_sync_abs_m",
            nonnegative=True,
        ),
        "flat_response_abs_tolerance": _finite(
            item["flat_response_abs_tolerance"],
            "analysis_policy.flat_response_abs_tolerance",
            nonnegative=True,
        ),
        "minimum_point_count": minimum,
    }


def build_spectral_analysis_decision(
    bundle: Mapping[str, Any], analysis_policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply caller-declared evidence gates and classify spectral candidates."""
    normalized = validate_spectral_point_bundle(bundle)
    policy = _normalize_analysis_policy(analysis_policy)
    rows = normalized["rows"]
    passivity_tolerance = policy["passivity_abs_tolerance"]
    closure_tolerance = policy["closure_abs_tolerance"]
    sync_tolerance = policy["wavelength_sync_abs_m"]
    row_checks = []
    invalid_rows = []
    for row in rows:
        closure = abs(1.0 - row["R"] - row["T"] - row["A"])
        sync_error = max(
            abs(row["requested_wavelength_m"] - row["evaluated_wavelength_m"]),
            abs(row["requested_wavelength_m"] - row["frequency_wavelength_m"]),
        )
        passive = all(
            -passivity_tolerance <= row[name] <= 1.0 + passivity_tolerance
            for name in ("R", "T", "A")
        )
        checks = {
            "row_id": row["row_id"],
            "raw_row_sha256": row["raw_row_sha256"],
            "passivity_passed": passive,
            "closure_abs": closure,
            "closure_passed": closure <= closure_tolerance,
            "wavelength_sync_abs_m": sync_error,
            "wavelength_sync_passed": sync_error <= sync_tolerance,
        }
        if not all(
            checks[name]
            for name in (
                "passivity_passed",
                "closure_passed",
                "wavelength_sync_passed",
            )
        ):
            invalid_rows.append(row["row_id"])
        row_checks.append(checks)

    response = [row[policy["response_quantity"]] for row in rows]
    oriented = response if policy["candidate_polarity"] == "maximum" else [-v for v in response]
    span = max(response) - min(response)
    local_indices = [
        index
        for index in range(1, len(rows) - 1)
        if oriented[index] > oriented[index - 1]
        and oriented[index] > oriented[index + 1]
    ]
    boundary_indices = []
    if oriented[0] > oriented[1]:
        boundary_indices.append(0)
    if oriented[-1] > oriented[-2]:
        boundary_indices.append(len(rows) - 1)

    if invalid_rows:
        classification = "invalid_evidence"
    elif len(rows) < policy["minimum_point_count"]:
        classification = "under_sampled"
    elif span <= policy["flat_response_abs_tolerance"]:
        classification = "flat"
    elif boundary_indices and max(oriented[index] for index in boundary_indices) >= max(oriented):
        classification = "boundary_high"
    elif len(local_indices) > 1:
        classification = "multi_candidate"
    elif len(local_indices) == 1:
        classification = "interior_candidate"
    else:
        classification = "no_candidate"

    evidence_rows = [
        {"row_id": row["row_id"], "raw_row_sha256": row["raw_row_sha256"]}
        for row in rows
    ]
    body = {
        "schema_name": SPECTRAL_DECISION_SCHEMA,
        "schema_version": SPECTRAL_SCHEMA_VERSION,
        "bundle_id": normalized["bundle_id"],
        "bundle_sha256": normalized["bundle_sha256"],
        "configuration_sha256": normalized["configuration_sha256"],
        "analysis_policy": policy,
        "analysis_policy_sha256": _sha256(policy),
        "classification": classification,
        "candidate_row_ids": [rows[index]["row_id"] for index in local_indices],
        "boundary_row_ids": [rows[index]["row_id"] for index in boundary_indices],
        "invalid_row_ids": invalid_rows,
        "response_span": span,
        "row_checks": row_checks,
        "evidence_rows": evidence_rows,
    }
    return {**body, "decision_sha256": _sha256(body)}


def validate_spectral_analysis_decision(
    value: Any, *, bundle: Mapping[str, Any]
) -> dict[str, Any]:
    """Recompute a decision from its exact bundle and reject hash tampering."""
    item = _mapping(value, "spectral_decision")
    expected = {
        "schema_name",
        "schema_version",
        "bundle_id",
        "bundle_sha256",
        "configuration_sha256",
        "analysis_policy",
        "analysis_policy_sha256",
        "classification",
        "candidate_row_ids",
        "boundary_row_ids",
        "invalid_row_ids",
        "response_span",
        "row_checks",
        "evidence_rows",
        "decision_sha256",
    }
    if set(item) != expected:
        raise ValueError("spectral decision fields are invalid")
    rebuilt = build_spectral_analysis_decision(bundle, item["analysis_policy"])
    if item != rebuilt:
        raise ValueError("spectral decision is noncanonical or its hash does not match")
    return deepcopy(rebuilt)


__all__ = [
    "MAX_SPECTRAL_POINTS",
    "SPECTRAL_BUNDLE_SCHEMA",
    "SPECTRAL_DECISION_SCHEMA",
    "SPECTRAL_SCHEMA_VERSION",
    "build_spectral_analysis_decision",
    "build_spectral_point_bundle",
    "validate_spectral_analysis_decision",
    "validate_spectral_point_bundle",
]
