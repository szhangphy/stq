from __future__ import annotations

from typing import Any

from .models import GroupSpec
from .sg194_special import special_rule_summary
from .utils import now_iso


def build_alignment_summary(spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
    if not spec.runnable:
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "template_only",
            "special_rules": special_rule_summary(spec),
        }

    stage2 = artifacts["stage2_status"]
    single = stage2["single_status"]
    double = stage2["double_status"]

    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "special_rules": special_rule_summary(spec),
        "single": {
            "raw": {
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "exact_alignment_status": "not_applicable_raw_current_object",
                "object_kind": "raw_current_provenance_object",
            },
            "target": {
                "row_language_kind": stage2["single_target_row_language_kind"],
                "exact_alignment_status": stage2["single_target_exact_generator_identity_status"],
                "exact_linear_target_alignment_exists": stage2["single_target_exact_linear_target_alignment_exists"],
                "projection_mismatch_rank": stage2["single_target_projection_mismatch_rank"],
                "object_kind": stage2["single_final_object_kind"],
                "bs_ai_same_object_language": single["bs_ai_same_object_language"],
                "generator_label_canonicalization_role": stage2["single_target_generator_label_canonicalization_role"],
                "generator_label_canonicalization_scope": stage2["single_target_generator_label_canonicalization_scope"],
            },
        },
        "double": {
            "raw": {
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "exact_alignment_status": "not_applicable_raw_current_object",
                "object_kind": "raw_current_provenance_object",
            },
            "target": {
                "row_language_kind": spec.special_rules["target_row_language_kind"],
                "exact_alignment_status": stage2["double_internalization_status"],
                "target_object_match": stage2["double_internalization_target_object_match"],
                "object_kind": stage2["double_final_object_kind"],
                "benchmark_oracle_file": stage2["benchmark_oracle_file"],
            },
        },
    }
