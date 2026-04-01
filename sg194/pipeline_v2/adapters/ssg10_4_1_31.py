from __future__ import annotations

from typing import Any

from ..models import GroupSpec
from ..utils import now_iso


class SSG104131OpsOnlyAdapter:
    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        probe = artifacts["ops_onboarding"]
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "symmetry_ops_probe_only",
            "shared_backbone_available": False,
            "shared_backbone_mode": "not_built_from_symmetry_ops_only",
            "object_counts": probe["sample_probe"]["object_counts"],
            "compatibility_matrix_shape": None,
            "probe_anchor": probe["sample_probe"]["anchor_name"],
            "trusted_source_files": probe["trusted_source_files"],
            "blockers": probe["missing_generic_builders"],
        }

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        probe = artifacts["ops_onboarding"]
        blocked_state = {
            "row_language_kind": "not_built_from_symmetry_ops_only",
            "exact_alignment_status": "blocked_missing_generic_row_language_builder",
            "object_kind": "not_available_from_symmetry_ops_only",
            "availability": "blocked",
            "blocker": probe["primary_blocker"],
        }
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "special_rules": spec.special_rules,
            "single": {"raw": dict(blocked_state), "target": dict(blocked_state)},
            "double": {"raw": dict(blocked_state), "target": dict(blocked_state)},
        }

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        probe = artifacts["ops_onboarding"]
        def blocked_record(mode: str) -> dict[str, Any]:
            return {
                "object_id": f"{mode}_symmetry_ops_probe",
                "mode": mode,
                "row_language_level": "raw",
                "row_language_kind": "not_built_from_symmetry_ops_only",
                "object_kind": "ops_only_probe",
                "availability": "blocked",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "quotient_derivation_mode": "blocked_missing_generic_builders",
                "exact_alignment_status": "not_constructed",
                "blocker": probe["primary_blocker"],
                "trusted_evidence": probe["trust_policy"],
                "source_files": [artifacts["_artifact_paths"]["ops_onboarding"]],
            }
        return [blocked_record("single"), blocked_record("double")]

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        probe = artifacts["ops_onboarding"]
        blocked = {
            "object_kind": "not_available_from_symmetry_ops_only",
            "dBS": None,
            "dAI": None,
            "classification": None,
            "row_language_kind": "not_built_from_symmetry_ops_only",
            "blocker": probe["primary_blocker"],
        }
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "partial_onboarding_only",
            "single_final": dict(blocked),
            "double_final": dict(blocked),
            "same_final_object": None,
            "relation": "final_objects_not_constructed_from_symmetry_ops_only",
            "note": probe["readiness_note"],
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
        probe = artifacts["ops_onboarding"]
        return [
            {
                "name": "symmetry_ops_probe_valid",
                "passed": probe["sample_probe"]["probe_passed"] is True,
                "actual": probe["sample_probe"],
            },
            {
                "name": "trust_policy_is_symmetry_ops_only",
                "passed": probe["trust_policy"] == "symmetry_operations_only",
                "actual": probe["trust_policy"],
            },
            {
                "name": "no_untrusted_existing_conclusions_consumed",
                "passed": probe["untrusted_result_files_consumed"] == [],
                "actual": probe["untrusted_result_files_consumed"],
            },
            {
                "name": "missing_generic_builders_explicit",
                "passed": len(probe["missing_generic_builders"]) >= 3,
                "actual": probe["missing_generic_builders"],
            },
            {
                "name": "final_results_intentionally_blocked",
                "passed": (
                    final_status["single_final"]["dBS"] is None
                    and final_status["double_final"]["dBS"] is None
                    and final_status["status"] == "partial_onboarding_only"
                ),
                "actual": final_status,
            },
        ]
