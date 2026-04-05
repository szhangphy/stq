from __future__ import annotations

from typing import Any

from .generic_builders import generic_result_objects
from .group_target_registry import get_group_target_spec
from .models import GroupSpec
from .utils import now_iso


def _is_generic_spec(spec: GroupSpec) -> bool:
    return spec.builder_backend == "generic_symmetry_ops"


def _build_generic_result_objects(
    spec: GroupSpec,
    geometry: dict[str, Any],
    alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    del geometry
    current_row_status = alignment["current_row_shell"]["status"]
    local_ai_status = alignment["local_ai_seed_builder"]["status"]
    quotient_prereq_status = "available" if current_row_status == "available" and local_ai_status == "available" else "blocked"
    raw_row_language = alignment["current_row_shell"]["row_language_kind"]
    records = []
    for mode in ("single", "double"):
        target_alignment = alignment.get(mode, {}).get("target", {})
        blocked = (
            target_alignment.get("blocker")
            or alignment.get("compatibility_builder", {}).get(f"{mode}_blocker")
            or alignment.get("compatibility_builder", {}).get("single_blocker")
            or alignment.get("compatibility_builder", {}).get("double_blocker")
            or "generic_current_row_compatibility_builder"
        )
        records.append(
            {
                "object_id": f"{mode}_raw_shell",
                "mode": mode,
                "row_language_level": "raw",
                "row_language_kind": raw_row_language,
                "object_kind": "generic_current_row_shell_with_local_ai_seed",
                "availability": "partial",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "quotient_derivation_mode": "quotient_prerequisites_only",
                "exact_alignment_status": "not_built",
                "current_row_shell_status": current_row_status,
                "local_ai_seed_status": local_ai_status,
                "quotient_prerequisites_status": quotient_prereq_status,
                "blocker": blocked,
                "source_files": [],
            }
        )
        records.append(
            {
                "object_id": f"{mode}_target_pending",
                "mode": mode,
                "row_language_level": "target",
                "row_language_kind": target_alignment.get("row_language_kind", "generic_same_shell_published_target"),
                "object_kind": target_alignment.get("object_kind", "generic_same_shell_target_object"),
                "availability": target_alignment.get("availability", "blocked"),
                "dBS": target_alignment.get("dBS"),
                "dAI": target_alignment.get("dAI"),
                "ai_image_rank_in_bs": target_alignment.get("ai_image_rank_in_bs"),
                "dbs_minus_ai_image_rank": target_alignment.get("dbs_minus_ai_image_rank"),
                "classification": target_alignment.get("classification"),
                "free_rank": target_alignment.get("free_rank"),
                "finite_part": list(target_alignment.get("finite_part", [])),
                "quotient_derivation_mode": target_alignment.get(
                    "direct_quotient_status",
                    "blocked_missing_generic_direct_quotient_builder",
                ),
                "exact_alignment_status": target_alignment.get(
                    "exact_alignment_status",
                    "blocked_missing_generic_current_row_compatibility_builder",
                ),
                "current_row_shell_status": current_row_status,
                "local_ai_seed_status": local_ai_status,
                "quotient_prerequisites_status": quotient_prereq_status,
                "generic_builder_ready": bool(target_alignment.get("generic_builder_ready", False)),
                "generic_published_classification_ready": bool(
                    target_alignment.get("generic_published_classification_ready", False)
                ),
                "reported_dbs_semantics": target_alignment.get("reported_dbs_semantics"),
                "reported_dai_semantics": target_alignment.get("reported_dai_semantics"),
                "classification_derivation_basis": target_alignment.get("classification_derivation_basis"),
                "object_semantics": target_alignment.get("object_semantics"),
                "same_shell_semantics": target_alignment.get("same_shell_semantics"),
                "quotient_semantics": target_alignment.get("quotient_semantics"),
                "promotion_reason": target_alignment.get("promotion_reason"),
                "same_shell_rank_check": target_alignment.get("same_shell_rank_check"),
                "full_current_shell_quotient": target_alignment.get("full_current_shell_quotient"),
                "projected_point_shell_attempt": target_alignment.get("projected_point_shell_attempt"),
                "blocker_stage": target_alignment.get("blocker_stage"),
                "blocker_evidence": target_alignment.get("blocker_evidence"),
                "direct_quotient_status": target_alignment.get("direct_quotient_status"),
                "verification_status": target_alignment.get("verification_status"),
                "blocker": target_alignment.get("blocker", blocked),
                "source_files": [],
            }
        )
    return records


def _target_semantics_verified(item: dict[str, Any]) -> bool:
    if item.get("availability") != "available":
        return False
    if item.get("object_semantics") != "published_target_object":
        return False
    d_bs = item.get("dBS")
    d_ai = item.get("dAI")
    if d_bs is None or d_ai is None:
        return False
    if d_bs != d_ai:
        return False
    if item.get("classification") is None:
        return False
    if item.get("same_shell_semantics") != "published_target_object":
        return False
    if item.get("quotient_semantics") != "same_shell_published_target_quotient":
        return False
    if item.get("verification_status") != "semantic_pass":
        return False
    return True


def _infer_result_mode(
    item: dict[str, Any],
    spec: GroupSpec,
) -> tuple[str, bool, str]:
    target_spec = get_group_target_spec(spec.group_id)
    if not _is_generic_spec(spec):
        explicit_mode = item.get("final_result_mode")
        explicit_status = item.get("status")
        if explicit_mode is not None and explicit_status is not None:
            return str(explicit_mode), bool(item.get("classification_is_published_final")), str(explicit_status)
    is_target = item.get("row_language_level") == "target"
    availability = item.get("availability")
    classification = item.get("classification")
    generic_ready = bool(item.get("generic_builder_ready", False))
    generic_published_ok = bool(item.get("generic_published_classification_ready", False))
    semantic_ok = _target_semantics_verified(item)

    if (
        is_target
        and target_spec.generic_builders_expected
        and target_spec.require_same_shell_target_builder_for_generic_final
        and generic_ready
        and generic_published_ok
        and availability == "available"
        and classification is not None
        and semantic_ok
    ):
        return "generic_final", True, "success"

    return target_spec.default_nonfinal_mode, False, "not_final"


def _annotate_result_mode(
    records: list[dict[str, Any]],
    spec: GroupSpec,
) -> list[dict[str, Any]]:
    target_spec = get_group_target_spec(spec.group_id)
    for item in records:
        mode, is_final, status = _infer_result_mode(item, spec)
        item["truth_compare_available"] = target_spec.truth_compare_available
        item["benchmark_oracle_available"] = False
        item["final_result_mode"] = mode
        item["classification_is_published_final"] = is_final
        item["status"] = status
    return records


def build_result_objects(
    spec: GroupSpec,
    adapter,
    artifacts: dict[str, Any],
    geometry: dict[str, Any] | None = None,
    alignment: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if _is_generic_spec(spec):
        try:
            records = generic_result_objects(spec.group_id)
        except Exception as exc:
            records = _build_generic_result_objects(
                spec,
                geometry or {},
                alignment or {},
            )
            for item in records:
                item["generic_builder_error"] = str(exc)
        return _annotate_result_mode(records, spec)
    return _annotate_result_mode(adapter.build_result_objects(spec, artifacts), spec)


def filter_result_objects(records: list[dict[str, Any]], mode: str, row_language: str) -> list[dict[str, Any]]:
    selected = records
    if mode != "both":
        selected = [item for item in selected if item["mode"] == mode]
    if row_language != "all":
        selected = [item for item in selected if item["row_language_level"] == row_language]
    return selected


def build_bs_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "builder_prerequisites": [
            {
                "object_id": item["object_id"],
                "current_row_shell_status": item.get("current_row_shell_status"),
                "local_ai_seed_status": item.get("local_ai_seed_status"),
                "quotient_prerequisites_status": item.get("quotient_prerequisites_status"),
            }
            for item in records
            if item.get("current_row_shell_status") is not None
        ],
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "availability": item["availability"],
                "dBS": item["dBS"],
                "ai_image_rank_in_bs": item.get("ai_image_rank_in_bs"),
                "generic_builder_ready": item.get("generic_builder_ready"),
                "generic_published_classification_ready": item.get(
                    "generic_published_classification_ready"
                ),
                "exact_alignment_status": item.get("exact_alignment_status"),
                "final_result_mode": item.get("final_result_mode"),
                "classification_is_published_final": item.get("classification_is_published_final"),
                "status": item.get("status"),
                "blocker_stage": item.get("blocker_stage"),
                "blocker_evidence": item.get("blocker_evidence"),
                "direct_quotient_status": item.get("direct_quotient_status"),
                "classification": item.get("classification"),
                "reported_dbs_semantics": item.get("reported_dbs_semantics"),
                "reported_dai_semantics": item.get("reported_dai_semantics"),
                "classification_derivation_basis": item.get("classification_derivation_basis"),
                "object_semantics": item.get("object_semantics"),
                "same_shell_semantics": item.get("same_shell_semantics"),
                "quotient_semantics": item.get("quotient_semantics"),
                "promotion_reason": item.get("promotion_reason"),
                "same_shell_rank_check": item.get("same_shell_rank_check"),
                "verification_status": item.get("verification_status"),
                "blocker": item.get("blocker"),
            }
            for item in records
        ],
    }


def build_ai_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "builder_prerequisites": [
            {
                "object_id": item["object_id"],
                "current_row_shell_status": item.get("current_row_shell_status"),
                "local_ai_seed_status": item.get("local_ai_seed_status"),
                "quotient_prerequisites_status": item.get("quotient_prerequisites_status"),
            }
            for item in records
            if item.get("current_row_shell_status") is not None
        ],
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "availability": item["availability"],
                "dAI": item["dAI"],
                "ai_image_rank_in_bs": item.get("ai_image_rank_in_bs"),
                "generic_builder_ready": item.get("generic_builder_ready"),
                "generic_published_classification_ready": item.get(
                    "generic_published_classification_ready"
                ),
                "exact_alignment_status": item.get("exact_alignment_status"),
                "final_result_mode": item.get("final_result_mode"),
                "classification_is_published_final": item.get("classification_is_published_final"),
                "status": item.get("status"),
                "blocker_stage": item.get("blocker_stage"),
                "blocker_evidence": item.get("blocker_evidence"),
                "direct_quotient_status": item.get("direct_quotient_status"),
                "classification": item.get("classification"),
                "reported_dbs_semantics": item.get("reported_dbs_semantics"),
                "reported_dai_semantics": item.get("reported_dai_semantics"),
                "classification_derivation_basis": item.get("classification_derivation_basis"),
                "object_semantics": item.get("object_semantics"),
                "same_shell_semantics": item.get("same_shell_semantics"),
                "quotient_semantics": item.get("quotient_semantics"),
                "promotion_reason": item.get("promotion_reason"),
                "same_shell_rank_check": item.get("same_shell_rank_check"),
                "verification_status": item.get("verification_status"),
                "blocker": item.get("blocker"),
            }
            for item in records
        ],
    }
