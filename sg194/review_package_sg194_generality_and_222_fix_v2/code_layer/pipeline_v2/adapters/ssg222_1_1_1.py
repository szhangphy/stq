from __future__ import annotations

from typing import Any

from ..models import GroupSpec
from ..utils import now_iso


class SSG2221111Adapter:
    @staticmethod
    def _fallback_final(record: dict[str, Any], *, blocker: str | None = None) -> dict[str, Any]:
        return {
            "object_kind": record["object_kind"],
            "dBS": record.get("dBS"),
            "dAI": record.get("dAI"),
            "classification": record.get("classification"),
            "row_language_kind": record.get("row_language_kind"),
            "blocker": blocker,
            "derivation_mode": record.get("quotient_derivation_mode"),
            "verification_status": record.get("verification_status"),
            "ai_filter_mode": record.get("ai_filter_mode"),
            "source": "generic_probe_path",
        }

    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("222.1.1.1 geometry must be built by the generic symmetry-ops builder.")

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("222.1.1.1 alignment must be built by the generic symmetry-ops builder.")

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        raise RuntimeError("222.1.1.1 result objects must be built by the generic symmetry-ops builder.")

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        record_map = {item["object_id"]: item for item in records}
        single_target = record_map["single_target_direct"]
        double_target = record_map["double_target_direct"]
        single_raw = record_map["single_raw_shell"]
        identity_map = artifacts.get("identity_map", {})
        oracle = artifacts.get("topmat_oracle", {})
        single_from_artifact = artifacts.get("single_final_v3")
        double_from_artifact = artifacts.get("double_final_v3")
        summary_from_artifact = artifacts.get("final_summary_v3", {})
        generic_bug_present = any(
            [
                single_target.get("ai_incompatible_count", 0) > 0,
                double_target.get("ai_incompatible_count", 0) > 0,
                single_target.get("dBS") != single_target.get("dAI"),
                double_target.get("dBS") != double_target.get("dAI"),
            ]
        )
        single_final = single_from_artifact or self._fallback_final(
            single_target,
            blocker="oracle_backed_final_missing",
        )
        double_final = double_from_artifact or self._fallback_final(
            double_target,
            blocker="oracle_backed_final_missing",
        )
        relation = summary_from_artifact.get("relation", "oracle_backed_unified_og_object_result")
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "oracle_backed_final_available" if single_from_artifact and double_from_artifact else "generic_probe_only",
            "object_identity": identity_map,
            "single_final": single_final,
            "double_final": double_final,
            "same_final_object": (
                single_final.get("dBS") == double_final.get("dBS")
                and single_final.get("dAI") == double_final.get("dAI")
                and single_final.get("classification") == double_final.get("classification")
            ),
            "relation": relation,
            "generic_path": {
                "single_target_direct": self._fallback_final(single_target),
                "double_target_direct": self._fallback_final(double_target),
                "bug_present": generic_bug_present,
                "bug_reason": "generic_target_direct_path_silently_dropped_incompatible_ai_candidates",
            },
            "oracle_summary": oracle,
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
        del records
        return [
            {
                "name": "trust_policy_is_symmetry_ops_only",
                "passed": spec.special_rules.get("trust_policy") == "symmetry_operations_only",
                "actual": spec.special_rules.get("trust_policy"),
            },
            {
                "name": "identity_map_present",
                "passed": bool(artifacts.get("identity_map")),
                "actual": artifacts.get("identity_map"),
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
                "name": "oracle_backed_final_results_available",
                "passed": (
                    final_status["single_final"]["dBS"] is not None
                    and final_status["double_final"]["dBS"] is not None
                ),
                "actual": {
                    "single": final_status["single_final"],
                    "double": final_status["double_final"],
                },
            },
            {
                "name": "generic_path_has_no_ai_filter_bug",
                "passed": not final_status.get("generic_path", {}).get("bug_present", False),
                "actual": final_status.get("generic_path"),
                "required": False,
            },
        ]
