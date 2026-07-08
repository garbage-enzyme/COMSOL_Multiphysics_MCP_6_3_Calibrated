"""Reusable workflow tools for COMSOL studies.

These tools capture patterns that are useful across projects:

- staged parameter sweeps that write CSV rows after each solved point
- mesh-convergence checks that rebuild, solve, and evaluate per mesh level

They intentionally do not encode project-specific physics, materials, or
variable names. Callers provide the parameter, study step, mesh feature, and
expressions that make sense for the model at hand.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
from mcp.server.fastmcp import FastMCP

from .session import session_manager
from .study import _resolve_study_tag


def _format_parameter_value(value: Any, unit: Optional[str] = None) -> str:
    """Format a COMSOL parameter value, adding a unit for numeric inputs."""
    if isinstance(value, str):
        return value
    if unit:
        return f"{value}[{unit}]"
    return str(value)


def _format_study_step_value(value: Any) -> str:
    """Format a study-step property value such as a Wavelength plist entry."""
    if isinstance(value, str):
        # Study step lists usually want the bare value, not "4e-6[m]".
        if "[" in value and value.endswith("]"):
            return value.split("[", 1)[0]
        return value
    return str(value)


def _ensure_parent_dir(file_path: Optional[str]) -> None:
    if not file_path:
        return
    Path(file_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _scalarize(value: Any) -> Any:
    """Return a JSON/CSV-friendly scalar or list from an MPh evaluate result."""
    arr = np.asarray(value)
    if arr.size == 0:
        return None
    if arr.size == 1:
        scalar = arr.reshape(-1)[0]
        if np.iscomplexobj(arr):
            return complex(scalar)
        return float(scalar)
    if np.iscomplexobj(arr):
        return [complex(v) for v in arr.reshape(-1)]
    return [float(v) for v in arr.reshape(-1)]


def _csv_value(value: Any) -> Any:
    if isinstance(value, complex):
        return f"{value.real}+{value.imag}i"
    if isinstance(value, list):
        return ";".join(_csv_value(v) for v in value)
    return value


def _evaluate_expressions(model, expressions: Sequence[str]) -> dict[str, Any]:
    results = model.evaluate(list(expressions))
    if len(expressions) == 1:
        return {expressions[0]: _scalarize(results)}
    return {
        expr: _scalarize(value)
        for expr, value in zip(expressions, results)
    }


def _write_rows_csv(
    csv_path: Optional[str],
    fieldnames: Sequence[str],
    rows: Sequence[dict[str, Any]],
    append: bool,
) -> None:
    if not csv_path:
        return
    _ensure_parent_dir(csv_path)
    path = Path(csv_path)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        if mode == "w":
            writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})
        handle.flush()


def run_staged_parametric_sweep(
    model,
    parameter_name: str,
    parameter_values: Sequence[Any],
    expressions: Sequence[str],
    *,
    parameter_unit: Optional[str] = None,
    study_name: Optional[str] = None,
    study_step_tag: Optional[str] = None,
    study_step_property: str = "plist",
    study_step_unit: Optional[str] = None,
    study_step_unit_property: str = "punit",
    csv_path: Optional[str] = None,
    append_csv: bool = False,
    save_model_path: Optional[str] = None,
) -> dict[str, Any]:
    """Run a parameter sweep one point at a time and append CSV rows eagerly."""
    if not parameter_values:
        return {"success": False, "error": "parameter_values must not be empty."}
    if not expressions:
        return {"success": False, "error": "expressions must not be empty."}

    jm = model.java
    study_tag = _resolve_study_tag(model, study_name)
    if study_tag is None:
        tags = list(jm.study().tags())
        if not tags:
            return {"success": False, "error": "No studies found in model."}
        study_tag = tags[0]

    fieldnames = [
        parameter_name,
        "parameter_value",
        "solve_sec",
        *list(expressions),
    ]
    rows: list[dict[str, Any]] = []
    total_start = time.time()

    for value in parameter_values:
        parameter_value = _format_parameter_value(value, parameter_unit)
        jm.param().set(parameter_name, parameter_value)

        if study_step_tag:
            step = jm.study(study_tag).feature(study_step_tag)
            step.set(study_step_property, _format_study_step_value(value))
            if study_step_unit:
                step.set(study_step_unit_property, study_step_unit)

        solve_start = time.time()
        jm.study(study_tag).run()
        solve_sec = time.time() - solve_start

        evaluated = _evaluate_expressions(model, expressions)
        row = {
            parameter_name: value,
            "parameter_value": parameter_value,
            "solve_sec": solve_sec,
            **evaluated,
        }
        rows.append(row)
        _write_rows_csv(csv_path, fieldnames, [row], append=True)

    if save_model_path:
        model.save(path=save_model_path)

    return {
        "success": True,
        "model": model.name(),
        "study": study_name,
        "resolved_study_tag": study_tag,
        "parameter": parameter_name,
        "n_points": len(rows),
        "csv_path": csv_path,
        "save_model_path": save_model_path,
        "total_sec": time.time() - total_start,
        "rows": rows,
    }


def run_mesh_convergence(
    model,
    levels: Sequence[dict[str, Any]],
    expressions: Sequence[str],
    *,
    component_name: str = "comp1",
    mesh_name: str = "mesh1",
    size_feature_tag: str = "sz1",
    parameter_name: Optional[str] = None,
    parameter_value: Optional[Any] = None,
    parameter_unit: Optional[str] = None,
    study_name: Optional[str] = None,
    study_step_tag: Optional[str] = None,
    study_step_property: str = "plist",
    study_step_unit: Optional[str] = None,
    study_step_unit_property: str = "punit",
    csv_path: Optional[str] = None,
    append_csv: bool = False,
    save_model_path: Optional[str] = None,
) -> dict[str, Any]:
    """Run mesh rebuild + solve + evaluation for each mesh-property level."""
    if not levels:
        return {"success": False, "error": "levels must not be empty."}
    if not expressions:
        return {"success": False, "error": "expressions must not be empty."}

    jm = model.java
    study_tag = _resolve_study_tag(model, study_name)
    if study_tag is None:
        tags = list(jm.study().tags())
        if not tags:
            return {"success": False, "error": "No studies found in model."}
        study_tag = tags[0]

    if parameter_name is not None and parameter_value is not None:
        jm.param().set(parameter_name, _format_parameter_value(parameter_value, parameter_unit))
        if study_step_tag:
            step = jm.study(study_tag).feature(study_step_tag)
            step.set(study_step_property, _format_study_step_value(parameter_value))
            if study_step_unit:
                step.set(study_step_unit_property, study_step_unit)

    mesh = jm.component(component_name).mesh(mesh_name)
    size_feature = mesh.feature(size_feature_tag)

    property_keys: list[str] = []
    for level in levels:
        for key in (level.get("properties") or {}).keys():
            if key not in property_keys:
                property_keys.append(key)

    fieldnames = [
        "level",
        *property_keys,
        "mesh_elements",
        "mesh_vertices",
        "mesh_sec",
        "solve_sec",
        *list(expressions),
    ]
    rows: list[dict[str, Any]] = []
    total_start = time.time()

    for idx, level in enumerate(levels, start=1):
        label = str(level.get("name") or f"level_{idx}")
        properties = level.get("properties") or {}
        for key, value in properties.items():
            size_feature.set(key, value)

        mesh_start = time.time()
        mesh.run()
        mesh_sec = time.time() - mesh_start
        try:
            mesh_elements = int(mesh.getNumElem())
            mesh_vertices = int(mesh.getNumVertex())
        except Exception:
            mesh_elements = None
            mesh_vertices = None

        solve_start = time.time()
        jm.study(study_tag).run()
        solve_sec = time.time() - solve_start

        evaluated = _evaluate_expressions(model, expressions)
        row = {
            "level": label,
            "mesh_elements": mesh_elements,
            "mesh_vertices": mesh_vertices,
            "mesh_sec": mesh_sec,
            "solve_sec": solve_sec,
            **{key: properties.get(key) for key in property_keys},
            **evaluated,
        }
        rows.append(row)
        _write_rows_csv(csv_path, fieldnames, [row], append=True)

    if save_model_path:
        model.save(path=save_model_path)

    return {
        "success": True,
        "model": model.name(),
        "component": component_name,
        "mesh": mesh_name,
        "size_feature": size_feature_tag,
        "study": study_name,
        "resolved_study_tag": study_tag,
        "n_levels": len(rows),
        "csv_path": csv_path,
        "save_model_path": save_model_path,
        "total_sec": time.time() - total_start,
        "rows": rows,
    }


def register_workflow_tools(mcp: FastMCP) -> None:
    """Register generic workflow tools."""

    @mcp.tool()
    def study_staged_parametric_sweep(
        parameter_name: str,
        parameter_values: Sequence[Any],
        expressions: Sequence[str],
        parameter_unit: Optional[str] = None,
        study_name: Optional[str] = None,
        study_step_tag: Optional[str] = None,
        study_step_property: str = "plist",
        study_step_unit: Optional[str] = None,
        study_step_unit_property: str = "punit",
        csv_path: Optional[str] = None,
        append_csv: bool = False,
        save_model_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run a parameter sweep one point at a time and write CSV incrementally.

        This avoids losing all results when a long COMSOL Parametric Sweep or
        MCP call times out: each parameter value is solved and appended to the
        CSV immediately.

        Args:
            parameter_name: COMSOL parameter name to set before each solve.
            parameter_values: Values to sweep. Numeric values can receive
                parameter_unit; strings are passed directly.
            expressions: Global expressions to evaluate after each solve.
            parameter_unit: Optional unit for numeric parameter values, e.g. "m".
            study_name: Study tag or label. Defaults to first study.
            study_step_tag: Optional study step to update per point, e.g.
                "wl_step" for Wavelength Domain.
            study_step_property: Step property to update, default "plist".
            study_step_unit: Optional unit property value for the step, e.g. "m".
            study_step_unit_property: Step unit property name, default "punit".
            csv_path: Optional CSV output path. Rows are written after each point.
            append_csv: Append to existing CSV instead of replacing it.
            save_model_path: Optional path to save the model after the sweep.
            model_name: Model name (default: current).

        Returns:
            Rows containing parameter value, solve time, and expression values.
        """
        model = session_manager.get_model(model_name)
        if model is None:
            return {"success": False, "error": f"Model not found: {model_name or 'no current model'}"}

        try:
            if csv_path and not append_csv:
                Path(csv_path).unlink(missing_ok=True)
            return run_staged_parametric_sweep(
                model,
                parameter_name,
                parameter_values,
                expressions,
                parameter_unit=parameter_unit,
                study_name=study_name,
                study_step_tag=study_step_tag,
                study_step_property=study_step_property,
                study_step_unit=study_step_unit,
                study_step_unit_property=study_step_unit_property,
                csv_path=csv_path,
                append_csv=append_csv,
                save_model_path=save_model_path,
            )
        except Exception as exc:
            return {"success": False, "error": f"staged sweep failed: {exc}"}

    @mcp.tool()
    def mesh_convergence_study(
        levels: Sequence[dict[str, Any]],
        expressions: Sequence[str],
        component_name: str = "comp1",
        mesh_name: str = "mesh1",
        size_feature_tag: str = "sz1",
        parameter_name: Optional[str] = None,
        parameter_value: Optional[Any] = None,
        parameter_unit: Optional[str] = None,
        study_name: Optional[str] = None,
        study_step_tag: Optional[str] = None,
        study_step_property: str = "plist",
        study_step_unit: Optional[str] = None,
        study_step_unit_property: str = "punit",
        csv_path: Optional[str] = None,
        append_csv: bool = False,
        save_model_path: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run mesh-convergence solves for a size feature.

        Each level supplies a name and a property dictionary, for example:

        ``{"name": "fine", "properties": {"hmax": "0.03*wl", "hmin": "0.0012*wl"}}``

        Args:
            levels: Mesh levels with ``name`` and ``properties``.
            expressions: Global expressions to evaluate after each solve.
            component_name: Component tag containing the mesh.
            mesh_name: Mesh sequence tag.
            size_feature_tag: Mesh Size feature tag to modify.
            parameter_name: Optional model parameter to set once before all levels.
            parameter_value: Optional value for parameter_name.
            parameter_unit: Optional unit for numeric parameter_value.
            study_name: Study tag or label. Defaults to first study.
            study_step_tag: Optional study step to update with parameter_value.
            study_step_property: Step property to update, default "plist".
            study_step_unit: Optional unit property value for the step.
            study_step_unit_property: Step unit property name, default "punit".
            csv_path: Optional CSV output path. Rows are written per level.
            append_csv: Append to existing CSV instead of replacing it.
            save_model_path: Optional path to save the model after the run.
            model_name: Model name (default: current).

        Returns:
            Rows containing mesh counts, timings, and expression values.
        """
        model = session_manager.get_model(model_name)
        if model is None:
            return {"success": False, "error": f"Model not found: {model_name or 'no current model'}"}

        try:
            if csv_path and not append_csv:
                Path(csv_path).unlink(missing_ok=True)
            return run_mesh_convergence(
                model,
                levels,
                expressions,
                component_name=component_name,
                mesh_name=mesh_name,
                size_feature_tag=size_feature_tag,
                parameter_name=parameter_name,
                parameter_value=parameter_value,
                parameter_unit=parameter_unit,
                study_name=study_name,
                study_step_tag=study_step_tag,
                study_step_property=study_step_property,
                study_step_unit=study_step_unit,
                study_step_unit_property=study_step_unit_property,
                csv_path=csv_path,
                append_csv=append_csv,
                save_model_path=save_model_path,
            )
        except Exception as exc:
            return {"success": False, "error": f"mesh convergence failed: {exc}"}
