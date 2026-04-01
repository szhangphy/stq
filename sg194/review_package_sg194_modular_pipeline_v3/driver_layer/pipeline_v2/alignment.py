from __future__ import annotations

from typing import Any

from .coordinates import build_kspace_geometry, build_realspace_geometry
from .models import GroupSpec
from .utils import now_iso


def _is_generic_spec(spec: GroupSpec) -> bool:
    return spec.builder_backend == "generic_symmetry_ops"


def _safe_len(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return len(value)
    except TypeError:
        return None


def _build_current_row_shell(entries: list[dict[str, Any]], coord_key: str) -> dict[str, Any]:
    seeds = []
    for idx, item in enumerate(entries):
        seeds.append(
            {
                "seed_id": f"k_{idx}",
                "dim": item.get("dim"),
                "mult": item.get("mult"),
                "representative_coordinate": item.get("representative_coordinate"),
                "coordinate_list_size": _safe_len(item.get(coord_key)),
                "basis_vector_count": _safe_len(item.get("basis_vecs")),
                "rep_size": _safe_len(item.get("rep")),
            }
        )
    return {
        "status": "available",
        "row_language_kind": "generic_current_row_shell_from_symmetry_ops",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "seed_count": len(seeds),
        "sample_seeds": seeds[:5],
    }


def _build_local_ai_seed(entries: list[dict[str, Any]], coord_key: str) -> dict[str, Any]:
    seeds = []
    for idx, item in enumerate(entries):
        seeds.append(
            {
                "seed_id": f"r_{idx}",
                "dim": item.get("dim"),
                "mult": item.get("mult"),
                "representative_coordinate": item.get("representative_coordinate"),
                "coordinate_list_size": _safe_len(item.get(coord_key)),
                "basis_vector_count": _safe_len(item.get("basis_vecs")),
                "site_symmetry": item.get("site_symmetry"),
            }
        )
    return {
        "status": "available",
        "row_language_kind": "generic_local_ai_seed_from_site_symmetry_data",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "seed_count": len(seeds),
        "sample_seeds": seeds[:5],
    }


def build_alignment_summary(spec: GroupSpec, adapter, artifacts: dict[str, Any]) -> dict[str, Any]:
    if _is_generic_spec(spec):
        kspace = build_kspace_geometry(spec.group_id)
        realspace = build_realspace_geometry(spec.group_id)
        current_row_shell = _build_current_row_shell(kspace["entries"], kspace["coord_key"])
        local_ai_seed = _build_local_ai_seed(realspace["entries"], realspace["coord_key"])
        blocked_target = {
            "row_language_kind": "target_row_language_not_yet_built",
            "exact_alignment_status": "blocked_missing_generic_current_row_compatibility_builder",
            "object_kind": "target_object_not_available",
            "availability": "blocked",
            "blocker": "generic_current_row_compatibility_builder",
        }
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "trust_policy": spec.special_rules.get("trust_policy"),
            "current_row_shell": current_row_shell,
            "local_ai_seed_builder": local_ai_seed,
            "single": {
                "raw": {
                    "row_language_kind": current_row_shell["row_language_kind"],
                    "exact_alignment_status": "not_applicable_current_row_shell_only",
                    "object_kind": "generic_current_row_shell",
                    "availability": "available",
                },
                "target": dict(blocked_target),
            },
            "double": {
                "raw": {
                    "row_language_kind": current_row_shell["row_language_kind"],
                    "exact_alignment_status": "not_applicable_current_row_shell_only",
                    "object_kind": "generic_current_row_shell",
                    "availability": "available",
                },
                "target": dict(blocked_target),
            },
        }
    return adapter.build_alignment_summary(spec, artifacts)
