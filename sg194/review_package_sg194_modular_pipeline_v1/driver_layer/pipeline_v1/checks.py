from __future__ import annotations

from typing import Any

from .models import GroupSpec
from .utils import now_iso


def build_consistency_checks(
    spec: GroupSpec,
    artifacts: dict[str, Any],
    geometry: dict[str, Any],
    alignment: dict[str, Any],
    selected_records: list[dict[str, Any]],
    bridge_status: dict[str, Any],
) -> dict[str, Any]:
    if not spec.runnable:
        checks = [
            {
                "name": "template_spec_shape_valid",
                "passed": True,
                "actual": spec.readiness_note,
            }
        ]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "checks": checks,
            "all_passed": True,
        }

    stage2 = artifacts["stage2_status"]
    stage2_summary = artifacts["stage2_summary"]
    expected = spec.expected_results
    final_records = {item["object_id"]: item for item in selected_records}

    checks = [
        {
            "name": "legacy_validation_commands",
            "passed": bridge_status["all_passed"],
            "actual": bridge_status["commands"],
        },
        {
            "name": "shared_geometry_backbone",
            "passed": geometry["shared_backbone_available"],
            "actual": geometry["shared_backbone_mode"],
        },
        {
            "name": "single_target_bs_ai_same_object_language",
            "passed": alignment["single"]["target"]["bs_ai_same_object_language"] is True,
            "actual": alignment["single"]["target"]["row_language_kind"],
        },
        {
            "name": "single_target_exact_alignment",
            "passed": alignment["single"]["target"]["exact_alignment_status"] == "available",
            "actual": {
                "exact_alignment_status": alignment["single"]["target"]["exact_alignment_status"],
                "projection_mismatch_rank": alignment["single"]["target"]["projection_mismatch_rank"],
            },
        },
        {
            "name": "double_target_exact_alignment",
            "passed": alignment["double"]["target"]["target_object_match"] is True,
            "actual": alignment["double"]["target"]["exact_alignment_status"],
        },
        {
            "name": "single_double_final_objects_differ",
            "passed": stage2["single_double_final_same_target_object"] is False,
            "actual": stage2["single_double_final_relation"],
        },
        {
            "name": "stage2_summary_matches_current_status",
            "passed": (
                stage2["single_final_rank_bs"] == stage2_summary["single_final_rank_bs"]
                and stage2["single_final_rank_ai"] == stage2_summary["single_final_rank_ai"]
                and stage2["single_final_quotient_group"] == stage2_summary["single_final_quotient_group"]
                and stage2["double_final_rank_bs"] == stage2_summary["double_final_rank_bs"]
                and stage2["double_final_rank_ai"] == stage2_summary["double_final_rank_ai"]
                and stage2["double_final_quotient_group"] == stage2_summary["double_final_quotient_group"]
            ),
            "actual": {
                "stage2_current_single": [
                    stage2["single_final_rank_bs"],
                    stage2["single_final_rank_ai"],
                    stage2["single_final_quotient_group"],
                ],
                "stage2_summary_single": [
                    stage2_summary["single_final_rank_bs"],
                    stage2_summary["single_final_rank_ai"],
                    stage2_summary["single_final_quotient_group"],
                ],
                "stage2_current_double": [
                    stage2["double_final_rank_bs"],
                    stage2["double_final_rank_ai"],
                    stage2["double_final_quotient_group"],
                ],
                "stage2_summary_double": [
                    stage2_summary["double_final_rank_bs"],
                    stage2_summary["double_final_rank_ai"],
                    stage2_summary["double_final_quotient_group"],
                ],
            },
        },
        {
            "name": "single_target_expected_result",
            "passed": (
                final_records["single_target_exact"]["dBS"] == expected["single_target"]["dBS"]
                and final_records["single_target_exact"]["dAI"] == expected["single_target"]["dAI"]
                and final_records["single_target_exact"]["classification"] == expected["single_target"]["classification"]
            ),
            "actual": final_records["single_target_exact"],
        },
        {
            "name": "double_target_expected_result",
            "passed": (
                final_records["double_target_benchmark_facing"]["dBS"] == expected["double_target"]["dBS"]
                and final_records["double_target_benchmark_facing"]["dAI"] == expected["double_target"]["dAI"]
                and final_records["double_target_benchmark_facing"]["classification"] == expected["double_target"]["classification"]
            ),
            "actual": final_records["double_target_benchmark_facing"],
        },
    ]
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "checks": checks,
        "all_passed": all(item["passed"] for item in checks),
    }
