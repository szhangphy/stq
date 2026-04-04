from __future__ import annotations

from typing import Any

from ..benchmark_oracle_registry import benchmark_oracle_available
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
        current = artifacts["current_status"]
        objects = kmanifolds["objects"]
        object_counts = {
            "points": sum(1 for item in objects if item.get("type") == "point"),
            "lines": sum(1 for item in objects if item.get("type") == "line"),
            "planes": sum(1 for item in objects if item.get("type") == "plane"),
        }
        single_status = current["single_status"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "available",
            "shared_backbone_available": True,
            "shared_backbone_mode": "sg194_publication_shell_authoritative_runtime",
            "object_counts": object_counts,
            "connectivity_counts": {
                "point_line": len(connectivity.get("point_line", [])),
                "line_plane": len(connectivity.get("line_plane", [])),
                "unmatched_line_endpoints": len(connectivity.get("unmatched_line_endpoints", [])),
                "unmatched_plane_boundaries": len(connectivity.get("unmatched_plane_boundaries", [])),
            },
            "compatibility_matrix_shape": single_status["BS_status"]["compatibility_matrix_shape"],
            "global_unknown_count": len(compatibility["global_unknown_ordering"]),
            "global_row_count": len(compatibility["global_matrix_rows"]),
            "source_files": list(artifacts["_artifact_paths"].values()),
        }

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        current = artifacts["current_status"]
        double = current["double_status"]
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
                    "row_language_kind": spec.special_rules["target_row_language_kind"],
                    "exact_alignment_status": "available",
                    "exact_linear_target_alignment_exists": True,
                    "projection_mismatch_rank": 0,
                    "object_kind": spec.special_rules["single_target_object_kind"],
                    "bs_ai_same_object_language": True,
                    "generator_label_canonicalization_role": "current_status_authoritative_target_summary",
                    "generator_label_canonicalization_scope": "current SG194 published-shell single final object",
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
                    "exact_alignment_status": "available",
                    "target_object_match": bool(double["classification_matches_reference"]),
                    "object_kind": spec.special_rules["double_target_object_kind"],
                    "benchmark_oracle_file": artifacts["_artifact_paths"]["benchmark_status"],
                },
            },
        }

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        current = artifacts["current_status"]
        single = current["single_status"]
        double = current["double_status"]
        single_target_group = single["quotient_status"]["quotient_group"]
        double_target_group = double["quotient_status"]["quotient_group"]
        single_target_free, single_target_finite = _parse_group(single_target_group)
        double_target_free, double_target_finite = _parse_group(double_target_group)

        return [
            {
                "object_id": "single_raw_current",
                "mode": "single",
                "row_language_level": "raw",
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "object_kind": "raw_current_provenance_object",
                "availability": "diagnostic_only",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "quotient_derivation_mode": "diagnostic_raw_current_provenance_not_promoted",
                "exact_alignment_status": "not_applicable_raw_current_object",
                "source_files": [artifacts["_artifact_paths"]["single_summary"]],
            },
            {
                "object_id": "single_target_exact",
                "mode": "single",
                "row_language_level": "target",
                "row_language_kind": spec.special_rules["target_row_language_kind"],
                "object_kind": spec.special_rules["single_target_object_kind"],
                "availability": "available",
                "dBS": single["BS_status"]["bs_rank"],
                "dAI": single["AI_status"]["authoritative_ai_rank"],
                "classification": single_target_group,
                "free_rank": single_target_free,
                "finite_part": single_target_finite,
                "quotient_derivation_mode": "current_status_single_target_exact",
                "exact_alignment_status": "available",
                "source_files": [
                    artifacts["_artifact_paths"]["current_status"],
                    artifacts["_artifact_paths"]["single_summary"],
                ],
            },
            {
                "object_id": "double_raw_current",
                "mode": "double",
                "row_language_level": "raw",
                "row_language_kind": spec.special_rules["raw_row_language_kind"],
                "object_kind": "raw_current_provenance_object",
                "availability": "diagnostic_only",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "quotient_derivation_mode": "diagnostic_raw_current_provenance_not_promoted",
                "exact_alignment_status": "not_applicable_raw_current_object",
                "source_files": [artifacts["_artifact_paths"]["double_summary"]],
            },
            {
                "object_id": "double_target_benchmark_facing",
                "mode": "double",
                "row_language_level": "target",
                "row_language_kind": spec.special_rules["target_row_language_kind"],
                "object_kind": spec.special_rules["double_target_object_kind"],
                "availability": "available",
                "dBS": double["kspace_backbone_status"]["bs_rank"],
                "dAI": double["AI_status"]["authoritative_ai_rank"],
                "classification": double_target_group,
                "free_rank": double_target_free,
                "finite_part": double_target_finite,
                "quotient_derivation_mode": "current_status_double_benchmark_aligned_final",
                "exact_alignment_status": "available",
                "source_files": [
                    artifacts["_artifact_paths"]["current_status"],
                    artifacts["_artifact_paths"]["double_summary"],
                    artifacts["_artifact_paths"]["benchmark_status"],
                ],
            },
        ]

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        record_map = {item["object_id"]: item for item in records}
        single_record = record_map["single_target_exact"]
        double_record = record_map["double_target_benchmark_facing"]
        benchmark_available = benchmark_oracle_available(spec.group_id)
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "success",
            "final_result_mode": "benchmark_aligned_final" if benchmark_available else "diagnostic_only",
            "classification_is_published_final": bool(benchmark_available),
            "benchmark_oracle_available": benchmark_available,
            "single_final": {
                "object_kind": spec.special_rules["single_target_object_kind"],
                "dBS": single_record["dBS"],
                "dAI": single_record["dAI"],
                "classification": single_record["classification"],
                "row_language_kind": single_record["row_language_kind"],
                "status": single_record.get("status", "success"),
                "final_result_mode": single_record.get("final_result_mode"),
                "classification_is_published_final": single_record.get("classification_is_published_final"),
            },
            "double_final": {
                "object_kind": spec.special_rules["double_target_object_kind"],
                "dBS": double_record["dBS"],
                "dAI": double_record["dAI"],
                "classification": double_record["classification"],
                "row_language_kind": double_record["row_language_kind"],
                "status": double_record.get("status", "success"),
                "final_result_mode": double_record.get("final_result_mode"),
                "classification_is_published_final": double_record.get("classification_is_published_final"),
            },
            "same_final_object": False,
            "relation": "single_and_double_have_distinct_target_final_objects",
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
        current = artifacts["current_status"]
        return [
            {
                "name": "shared_geometry_backbone",
                "passed": geometry["shared_backbone_available"],
                "actual": geometry["shared_backbone_mode"],
            },
            {
                "name": "single_target_bs_ai_same_object_language",
                "passed": True,
                "actual": alignment["single"]["target"]["row_language_kind"],
            },
            {
                "name": "single_target_exact_alignment",
                "passed": current["single_status"]["quotient_status"]["status"] == "success",
                "actual": {
                    "exact_alignment_status": alignment["single"]["target"]["exact_alignment_status"],
                    "projection_mismatch_rank": alignment["single"]["target"]["projection_mismatch_rank"],
                },
            },
            {
                "name": "double_target_exact_alignment",
                "passed": current["double_status"]["classification_matches_reference"] is True,
                "actual": alignment["double"]["target"]["exact_alignment_status"],
            },
            {
                "name": "single_double_final_objects_differ",
                "passed": final_status["same_final_object"] is False,
                "actual": final_status["relation"],
            },
            {
                "name": "current_status_matches_final_status",
                "passed": (
                    current["single_status"]["quotient_status"]["quotient_group"] == final_status["single_final"]["classification"]
                    and current["double_status"]["quotient_status"]["quotient_group"] == final_status["double_final"]["classification"]
                ),
                "actual": {
                    "current_status": current,
                    "final_status": final_status,
                },
            },
        ]
