from __future__ import annotations

from typing import Any

from ..models import GroupSpec
from ..utils import now_iso


def _parse_group(group: str) -> tuple[int, list[int]]:
    if group == "trivial":
        return 0, []
    if group.startswith("Z^"):
        return int(group[2:]), []
    if group == "Z":
        return 1, []
    if group.startswith("Z") and group[1:].isdigit():
        return 0, [int(group[1:])]
    free_rank = 0
    finite_part: list[int] = []
    for token in group.split(" x "):
        if token == "Z":
            free_rank += 1
        elif token.startswith("Z^"):
            free_rank += int(token[2:])
        elif token.startswith("Z") and token[1:].isdigit():
            finite_part.append(int(token[1:]))
    return free_rank, finite_part


class SG194Adapter:
    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        kmanifolds = artifacts["single_kmanifolds"]
        connectivity = artifacts["single_connectivity"]
        compatibility = artifacts["single_full_compatibility"]
        stage2 = artifacts["stage2_status"]
        objects = kmanifolds["objects"]
        object_counts = {
            "points": sum(1 for item in objects if item.get("type") == "point"),
            "lines": sum(1 for item in objects if item.get("type") == "line"),
            "planes": sum(1 for item in objects if item.get("type") == "plane"),
        }
        single_status = stage2["single_status"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "available",
            "shared_backbone_available": True,
            "shared_backbone_mode": single_status.get("geometry_backbone_mode", "shared_with_double_runtime_by_construction"),
            "object_counts": object_counts,
            "connectivity_counts": {
                "point_line": len(connectivity.get("point_line", [])),
                "line_plane": len(connectivity.get("line_plane", [])),
                "unmatched_line_endpoints": len(connectivity.get("unmatched_line_endpoints", [])),
                "unmatched_plane_boundaries": len(connectivity.get("unmatched_plane_boundaries", [])),
            },
            "compatibility_matrix_shape": compatibility.get(
                "matrix_shape",
                [len(compatibility["global_matrix"]), len(compatibility["global_unknown_ordering"])],
            ),
            "global_unknown_count": len(compatibility["global_unknown_ordering"]),
            "global_row_count": len(compatibility["global_matrix_rows"]),
            "source_files": list(artifacts["_artifact_paths"].values()),
        }

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        stage2 = artifacts["stage2_status"]
        single = stage2["single_status"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "special_rules": spec.special_rules,
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

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        stage2 = artifacts["stage2_status"]
        single = stage2["single_status"]
        double = stage2["double_status"]
        benchmark = artifacts["benchmark_status"]["benchmark_result"]

        single_raw_group = single["raw_current_quotient_group"]
        double_raw_group = double["raw_internal_quotient_group"]
        single_target_group = stage2["single_final_quotient_group"]
        double_target_group = stage2["double_final_quotient_group"]

        single_raw_free, single_raw_finite = _parse_group(single_raw_group)
        double_raw_free, double_raw_finite = _parse_group(double_raw_group)
        single_target_free, single_target_finite = _parse_group(single_target_group)

        return [
            {
                "object_id": "single_raw_current",
                "mode": "single",
                "row_language_level": "raw",
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "object_kind": "raw_current_provenance_object",
                "availability": "available",
                "dBS": single["raw_current_rank_bs"],
                "dAI": single["raw_current_rank_ai"],
                "classification": single_raw_group,
                "free_rank": single_raw_free,
                "finite_part": single_raw_finite,
                "quotient_derivation_mode": "direct_raw_current_provenance",
                "exact_alignment_status": "not_applicable",
                "source_files": [artifacts["_artifact_paths"]["stage2_status"]],
            },
            {
                "object_id": "single_target_exact",
                "mode": "single",
                "row_language_level": "target",
                "row_language_kind": stage2["single_target_row_language_kind"],
                "object_kind": stage2["single_final_object_kind"],
                "availability": "available",
                "dBS": stage2["single_final_rank_bs"],
                "dAI": stage2["single_final_rank_ai"],
                "classification": single_target_group,
                "free_rank": single_target_free,
                "finite_part": single_target_finite,
                "quotient_derivation_mode": stage2["single_final_quotient_derivation_mode"],
                "exact_alignment_status": stage2["single_target_exact_generator_identity_status"],
                "source_files": [
                    artifacts["_artifact_paths"]["stage2_status"],
                    artifacts["_artifact_paths"]["projection_summary"],
                ],
            },
            {
                "object_id": "double_raw_current",
                "mode": "double",
                "row_language_level": "raw",
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "object_kind": "raw_current_provenance_object",
                "availability": "available",
                "dBS": double["rank_bs_raw_internal"],
                "dAI": double["rank_ai_raw_internal"],
                "classification": double_raw_group,
                "free_rank": double_raw_free,
                "finite_part": double_raw_finite,
                "quotient_derivation_mode": "direct_raw_current_provenance",
                "exact_alignment_status": "not_applicable",
                "source_files": [artifacts["_artifact_paths"]["stage2_status"]],
            },
            {
                "object_id": "double_target_benchmark_facing",
                "mode": "double",
                "row_language_level": "target",
                "row_language_kind": spec.special_rules["target_row_language_kind"],
                "object_kind": stage2["double_final_object_kind"],
                "availability": "available",
                "dBS": stage2["double_final_rank_bs"],
                "dAI": stage2["double_final_rank_ai"],
                "classification": double_target_group,
                "free_rank": int(benchmark["free_rank"]),
                "finite_part": list(benchmark["finite_part"]),
                "quotient_derivation_mode": stage2["double_final_quotient_derivation_mode"],
                "exact_alignment_status": stage2["double_internalization_status"],
                "source_files": [
                    artifacts["_artifact_paths"]["stage2_status"],
                    artifacts["_artifact_paths"]["benchmark_status"],
                ],
            },
        ]

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        record_map = {item["object_id"]: item for item in records}
        stage2 = artifacts["stage2_status"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "available",
            "single_final": {
                "object_kind": stage2["single_final_object_kind"],
                "dBS": record_map["single_target_exact"]["dBS"],
                "dAI": record_map["single_target_exact"]["dAI"],
                "classification": record_map["single_target_exact"]["classification"],
                "row_language_kind": record_map["single_target_exact"]["row_language_kind"],
            },
            "double_final": {
                "object_kind": stage2["double_final_object_kind"],
                "dBS": record_map["double_target_benchmark_facing"]["dBS"],
                "dAI": record_map["double_target_benchmark_facing"]["dAI"],
                "classification": record_map["double_target_benchmark_facing"]["classification"],
                "row_language_kind": record_map["double_target_benchmark_facing"]["row_language_kind"],
            },
            "same_final_object": stage2["single_double_final_same_target_object"],
            "relation": stage2["single_double_final_relation"],
        }

    def build_extra_checks(
        self,
        spec: GroupSpec,
        artifacts: dict[str, Any],
        geometry: dict[str, Any],
        alignment: dict[str, Any],
        records: list[dict[str, Any]],
        final_status: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stage2 = artifacts["stage2_status"]
        stage2_summary = artifacts["stage2_summary"]
        return [
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
                "passed": final_status["same_final_object"] is False,
                "actual": final_status["relation"],
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
                    "single": [
                        stage2["single_final_rank_bs"],
                        stage2["single_final_rank_ai"],
                        stage2["single_final_quotient_group"],
                    ],
                    "double": [
                        stage2["double_final_rank_bs"],
                        stage2["double_final_rank_ai"],
                        stage2["double_final_quotient_group"],
                    ],
                },
            },
        ]
