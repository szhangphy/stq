from __future__ import annotations

from typing import Any

from .coordinates import build_kspace_geometry, build_realspace_geometry
from .generic_builders import generic_alignment_summary
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
        return generic_alignment_summary(spec.group_id)
    return adapter.build_alignment_summary(spec, artifacts)
