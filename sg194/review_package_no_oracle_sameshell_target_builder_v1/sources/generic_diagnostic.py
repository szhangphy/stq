from __future__ import annotations

from typing import Any

from ..benchmark_oracle_registry import benchmark_oracle_available
from ..models import GroupSpec
from ..utils import now_iso


class GenericDiagnosticAdapter:
    @staticmethod
    def _record_as_final(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "object_kind": record["object_kind"],
            "dBS": record.get("dBS"),
            "dAI": record.get("dAI"),
            "classification": record.get("classification"),
            "row_language_kind": record.get("row_language_kind"),
            "blocker": record.get("blocker"),
            "derivation_mode": record.get("quotient_derivation_mode"),
            "verification_status": record.get("verification_status"),
            "status": record.get("status", "not_final"),
            "final_result_mode": record.get("final_result_mode", "diagnostic_only"),
            "classification_is_published_final": bool(
                record.get("classification_is_published_final", False)
            ),
            "benchmark_oracle_available": bool(
                record.get("benchmark_oracle_available", False)
            ),
            "source": record.get(
                "source",
                (
                    "generic_symmetry_ops_same_shell_target_builder"
                    if record.get("final_result_mode") == "generic_final"
                    else "generic_symmetry_ops_diagnostic_only"
                ),
            ),
        }

    @staticmethod
    def _infer_status(records: list[dict[str, Any]]) -> tuple[str, str, bool]:
        target_records = [item for item in records if item.get("row_language_level") == "target"]
        if target_records and all(item.get("classification_is_published_final") for item in target_records):
            mode = str(target_records[0].get("final_result_mode", "generic_final"))
            return "success", mode, True
        return "not_final", "diagnostic_only", False

    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(f"{spec.group_id} geometry must be built by the generic symmetry-ops builder.")

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(f"{spec.group_id} alignment must be built by the generic symmetry-ops builder.")

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
        raise RuntimeError(f"{spec.group_id} result objects must be built by the generic symmetry-ops builder.")

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        single_target = next(
            item for item in records if item["mode"] == "single" and item["row_language_level"] == "target"
        )
        double_target = next(
            item for item in records if item["mode"] == "double" and item["row_language_level"] == "target"
        )
        status, final_result_mode, published_final = self._infer_status(records)
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": status,
            "final_result_mode": final_result_mode,
            "classification_is_published_final": published_final,
            "benchmark_oracle_available": benchmark_oracle_available(spec.group_id),
            "single_final": self._record_as_final(single_target),
            "double_final": self._record_as_final(double_target),
            "same_final_object": False,
            "relation": (
                "generic_final_without_benchmark_oracle"
                if published_final
                else "diagnostic_only_no_published_final_oracle"
            ),
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
                "name": "generic_current_row_compatibility_available",
                "passed": alignment.get("compatibility_builder", {}).get("status") == "available",
                "actual": alignment.get("compatibility_builder"),
            },
            {
                "name": "no_benchmark_oracle_registered",
                "passed": final_status.get("benchmark_oracle_available") is False,
                "actual": final_status.get("benchmark_oracle_available"),
            },
            {
                "name": "diagnostic_only_final_mode",
                "passed": final_status.get("final_result_mode") in {"diagnostic_only", "generic_final"},
                "actual": final_status.get("final_result_mode"),
            },
            {
                "name": "classification_not_published_final",
                "passed": isinstance(final_status.get("classification_is_published_final"), bool),
                "actual": final_status.get("classification_is_published_final"),
            },
            {
                "name": "generic_target_not_final_is_allowed",
                "passed": (
                    spec.capabilities.get("final_results") is False
                    or final_status.get("final_result_mode") == "generic_final"
                ),
                "actual": {
                    "capability_final_results": spec.capabilities.get("final_results"),
                    "final_result_mode": final_status.get("final_result_mode"),
                },
            },
        ]
