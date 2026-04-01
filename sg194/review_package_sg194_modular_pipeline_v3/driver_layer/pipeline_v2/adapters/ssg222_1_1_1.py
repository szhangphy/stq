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
        record_map = {item["object_id"]: item for item in records}
        single_target = record_map["single_target_pending"]
        double_target = record_map["double_target_pending"]
        single_raw = record_map["single_raw_shell"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "generic_builders_partial",
            "single_final": {
                "object_kind": single_target["object_kind"],
                "dBS": single_target["dBS"],
                "dAI": single_target["dAI"],
                "classification": single_target["classification"],
                "row_language_kind": single_target["row_language_kind"],
                "blocker": single_target["blocker"],
            },
            "double_final": {
                "object_kind": double_target["object_kind"],
                "dBS": double_target["dBS"],
                "dAI": double_target["dAI"],
                "classification": double_target["classification"],
                "row_language_kind": double_target["row_language_kind"],
                "blocker": double_target["blocker"],
            },
            "same_final_object": None,
            "relation": "final_target_objects_not_constructed_yet",
            "builder_layers": {
                "geometry": "available",
                "current_row_shell": single_raw["current_row_shell_status"],
                "local_ai_seed": single_raw["local_ai_seed_status"],
                "quotient_prerequisites": single_raw["quotient_prerequisites_status"],
                "target_alignment": "blocked",
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
                "name": "generic_current_row_shell_available",
                "passed": alignment.get("current_row_shell", {}).get("status") == "available",
                "actual": alignment.get("current_row_shell"),
            },
            {
                "name": "generic_local_ai_seed_available",
                "passed": alignment.get("local_ai_seed_builder", {}).get("status") == "available",
                "actual": alignment.get("local_ai_seed_builder"),
            },
            {
                "name": "final_results_explicitly_blocked",
                "passed": (
                    final_status["single_final"]["dBS"] is None
                    and final_status["double_final"]["dBS"] is None
                    and final_status["status"] == "generic_builders_partial"
                ),
                "actual": final_status["builder_layers"],
            },
        ]
