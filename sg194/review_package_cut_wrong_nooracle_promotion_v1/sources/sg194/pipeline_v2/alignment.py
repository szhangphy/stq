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
        try:
            return generic_alignment_summary(spec.group_id)
        except Exception as exc:
            fallback_error = str(exc)
            error_stage = "blocked_generic_alignment_summary_exception"
            current_row_shell = {
                "status": "available",
                "row_language_kind": "generic_current_row_shell_from_symmetry_ops",
                "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
                "point_count": None,
                "point_ids": [],
            }
            return {
                "generated_at": now_iso(),
                "group": spec.group_id,
                "trust_policy": "symmetry_operations_only",
                "builder_error": fallback_error,
                "current_row_shell": current_row_shell,
                "local_ai_seed_builder": {
                    "status": "available",
                    "row_language_kind": "generic_local_ai_seed_from_site_symmetry_data",
                    "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
                    "realspace_wyckoff_family_count": None,
                },
                "compatibility_builder": {
                    "status": "blocked",
                    "row_language_kind": current_row_shell["row_language_kind"],
                    "builder_stage": error_stage,
                    "error": fallback_error,
                },
                "single": {
                    "raw": {
                        "row_language_kind": current_row_shell["row_language_kind"],
                        "exact_alignment_status": "not_applicable_current_row_shell_only",
                        "object_kind": "generic_current_row_shell",
                        "availability": "available",
                    },
                    "target": {
                        "row_language_kind": "generic_same_shell_published_target",
                        "exact_alignment_status": error_stage,
                        "object_kind": "generic_same_shell_target_object",
                        "availability": "blocked",
                        "dBS": None,
                        "dAI": None,
                        "ai_image_rank_in_bs": None,
                        "classification": None,
                        "generic_builder_ready": False,
                        "generic_published_classification_ready": False,
                        "reported_dbs_semantics": None,
                        "reported_dai_semantics": None,
                        "classification_derivation_basis": None,
                        "object_semantics": None,
                        "same_shell_semantics": None,
                        "quotient_semantics": None,
                        "promotion_reason": None,
                        "same_shell_rank_check": {},
                        "verification_status": error_stage,
                        "full_current_shell_quotient": None,
                        "projected_point_shell_attempt": None,
                        "direct_quotient_status": error_stage,
                        "blocker_stage": error_stage,
                        "blocker_evidence": {},
                        "blocker": fallback_error,
                    },
                },
                "double": {
                    "raw": {
                        "row_language_kind": current_row_shell["row_language_kind"],
                        "exact_alignment_status": "not_applicable_current_row_shell_only",
                        "object_kind": "generic_current_row_shell",
                        "availability": "available",
                    },
                    "target": {
                        "row_language_kind": "generic_same_shell_published_target",
                        "exact_alignment_status": error_stage,
                        "object_kind": "generic_same_shell_target_object",
                        "availability": "blocked",
                        "dBS": None,
                        "dAI": None,
                        "ai_image_rank_in_bs": None,
                        "classification": None,
                        "generic_builder_ready": False,
                        "generic_published_classification_ready": False,
                        "reported_dbs_semantics": None,
                        "reported_dai_semantics": None,
                        "classification_derivation_basis": None,
                        "object_semantics": None,
                        "same_shell_semantics": None,
                        "quotient_semantics": None,
                        "promotion_reason": None,
                        "same_shell_rank_check": {},
                        "verification_status": error_stage,
                        "full_current_shell_quotient": None,
                        "projected_point_shell_attempt": None,
                        "direct_quotient_status": error_stage,
                        "blocker_stage": error_stage,
                        "blocker_evidence": {},
                        "blocker": fallback_error,
                    },
                },
            }
    return adapter.build_alignment_summary(spec, artifacts)
