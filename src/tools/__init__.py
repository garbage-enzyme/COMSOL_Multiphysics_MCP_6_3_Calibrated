"""Lazy MCP tool registration that keeps startup profile gates solver-free."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from importlib import import_module
from typing import Any, Callable


_REGISTRAR_PATHS = (
    "src.tools.capabilities.register_capability_tools",
    "src.tools.ownership.register_ownership_tools",
    "src.tools.jobs.register_job_tools",
    "src.tools.session.register_session_tools",
    "src.tools.model.register_model_tools",
    "src.tools.parameters.register_parameter_tools",
    "src.tools.geometry.register_geometry_tools",
    "src.tools.physics.register_physics_tools",
    "src.tools.mesh.register_mesh_tools",
    "src.tools.study.register_study_tools",
    "src.tools.results.register_results_tools",
    "src.tools.mim_patch.register_mim_patch_tools",
    "src.tools.workflow.register_workflow_tools",
    "src.tools.properties.register_property_tools",
    "src.tools.wave_optics_preflight.register_wave_optics_preflight_tools",
    "src.tools.periodic_mesh_audit.register_periodic_mesh_audit_tools",
    "src.tools.derived_geometry.register_derived_geometry_tools",
    "src.tools.incidence_config.register_incidence_config_tools",
    "src.tools.wave_optics_audit.register_wave_optics_audit_tools",
    "src.tools.material_expressions.register_material_expression_tools",
    "src.tools.visual_review.register_visual_review_tools",
    "src.tools.field_evidence.register_field_evidence_tools",
    "src.tools.semantic_docs.register_semantic_doc_tools",
    "src.tools.spectral_characterization.register_spectral_characterization_tools",
    "src.tools.convergence_evaluation.register_convergence_evaluation_tools",
    "src.tools.branch_continuation.register_branch_continuation_tools",
    "src.tools.shared_session.register_shared_session_tools",
)


def _load_symbol(path: str) -> Any:
    module_name, symbol_name = path.rsplit(".", 1)
    return getattr(import_module(module_name), symbol_name)


class _LazyRegistrarSequence(Sequence[Callable[..., Any]]):
    def __len__(self) -> int:
        return len(_REGISTRAR_PATHS)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(_load_symbol(path) for path in _REGISTRAR_PATHS[index])
        return _load_symbol(_REGISTRAR_PATHS[index])

    def __iter__(self) -> Iterator[Callable[..., Any]]:
        return (_load_symbol(path) for path in _REGISTRAR_PATHS)


TOOL_REGISTRARS: Sequence[Callable[..., Any]] = _LazyRegistrarSequence()


def register_tool_modules(mcp, profile="full") -> None:
    """Import and register only after the static profile gate is accepted."""
    from .profiles import ProfileSelection, resolve_profile, tool_names_for_profile

    selection = (
        profile if isinstance(profile, ProfileSelection) else resolve_profile(profile)
    )
    enabled_names = tool_names_for_profile(selection.name)
    for register in TOOL_REGISTRARS:
        from .profiles import register_profiled

        register_profiled(mcp, register, enabled_names, selection)


_REGISTER_EXPORTS = {
    path.rsplit(".", 1)[-1]: path for path in _REGISTRAR_PATHS
}


def __getattr__(name: str) -> Any:
    path = _REGISTER_EXPORTS.get(name)
    if path is not None:
        return _load_symbol(path)
    raise AttributeError(name)


__all__ = [*_REGISTER_EXPORTS, "TOOL_REGISTRARS", "register_tool_modules"]
