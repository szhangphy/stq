from __future__ import annotations

from typing import Any

from ..models import GroupSpec
from ..utils import now_iso


class SSG2221111Adapter:
    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("222.1.1.1 geometry must be built by the generic symmetry-ops builder.")

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("222.1.1.1 alignment must be built by the generic symmetry-ops builder.")

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        raise RuntimeError("222.1.1.1 result objects must be built by the generic symmetry-ops builder.")

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        del artifacts
        record_map = {item["object_id"]: item for item in records}
        single_target = record_map["single_target_direct"]
        double_target = record_map["double_target_direct"]
        single_raw = record_map["single_raw_shell"]
        relation = "single_and_double_generic_direct_results"
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "available",
            "single_final": {
                "object_kind": single_target["object_kind"],
                "dBS": single_target["dBS"],
                "dAI": single_target["dAI"],
                "classification": single_target["classification"],
                "row_language_kind": single_target["row_language_kind"],
                "blocker": None,
                "derivation_mode": single_target["quotient_derivation_mode"],
                "verification_status": single_target["verification_status"],
                "ai_filter_mode": single_target.get("ai_filter_mode"),
            },
            "double_final": {
                "object_kind": double_target["object_kind"],
                "dBS": double_target["dBS"],
                "dAI": double_target["dAI"],
                "classification": double_target["classification"],
                "row_language_kind": double_target["row_language_kind"],
                "blocker": None,
                "derivation_mode": double_target["quotient_derivation_mode"],
                "verification_status": double_target["verification_status"],
                "ai_filter_mode": double_target.get("ai_filter_mode"),
            },
            "same_final_object": (
                single_target["dBS"] == double_target["dBS"]
                and single_target["dAI"] == double_target["dAI"]
                and single_target["classification"] == double_target["classification"]
            ),
            "relation": relation,
            "builder_layers": {
                "geometry": "available",
                "current_row_shell": single_raw["current_row_shell_status"],
                "current_row_compatibility": single_target["current_row_compatibility_status"],
                "target_alignment": single_target["target_alignment_status"],
                "local_ai_embedding": single_target["local_ai_embedding_status"],
                "direct_quotient": single_target["direct_quotient_status"],
                "ai_filter": single_target.get("ai_filter_mode"),
            },
            "note": spec.readiness_note,
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
        del artifacts, records
        return [
            {
                "name": "trust_policy_is_symmetry_ops_only",
                "passed": spec.special_rules.get("trust_policy") == "symmetry_operations_only",
                "actual": spec.special_rules.get("trust_policy"),
            },
            {
                "name": "generic_geometry_available",
                "passed": geometry.get("shared_backbone_available") is True,
                "actual": geometry.get("status"),
            },
            {
                "name": "generic_current_row_compatibility_available",
                "passed": alignment.get("compatibility_builder", {}).get("status") == "available",
                "actual": alignment.get("compatibility_builder"),
            },
            {
                "name": "generic_single_target_available",
                "passed": alignment.get("single", {}).get("target", {}).get("availability") == "available",
                "actual": alignment.get("single", {}).get("target"),
            },
            {
                "name": "generic_double_target_available",
                "passed": alignment.get("double", {}).get("target", {}).get("availability") == "available",
                "actual": alignment.get("double", {}).get("target"),
            },
            {
                "name": "generic_final_results_available",
                "passed": (
                    final_status["single_final"]["dBS"] is not None
                    and final_status["double_final"]["dBS"] is not None
                ),
                "actual": {
                    "single": final_status["single_final"],
                    "double": final_status["double_final"],
                },
            },
        ]
