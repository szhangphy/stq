from __future__ import annotations

from typing import Any

from .benchmark_oracle_registry import benchmark_oracle_available
from .coordinates import coordinate_usage_audit
from .models import GroupSpec
from .utils import now_iso


def _verification_ready(entry: dict[str, Any]) -> bool:
    status = entry.get("verification_status")
    if status is None:
        return True
    lowered = str(status).lower()
    return not any(token in lowered for token in ("missing", "blocked", "failed", "warning"))


def _check(name: str, passed: bool, actual: Any, *, required: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "actual": actual,
        "required": required,
    }


def build_consistency_checks(
    spec: GroupSpec,
    artifacts: dict[str, Any],
    geometry: dict[str, Any],
    alignment: dict[str, Any],
    records: list[dict[str, Any]],
    bridge_status: dict[str, Any],
    final_status: dict[str, Any],
    adapter,
) -> dict[str, Any]:
    record_map = {item["object_id"]: item for item in records}
    coordinate_audit = coordinate_usage_audit()
    checks = [
        _check("producer_commands_passed", bridge_status["all_passed"], bridge_status["commands"]),
        _check("geometry_summary_present", bool(geometry), geometry.get("status", geometry.get("shared_backbone_available"))),
        _check("result_object_ids_unique", len(record_map) == len(records), [item["object_id"] for item in records]),
        _check("coordinate_contract_audit", coordinate_audit["all_passed"], coordinate_audit["violations"]),
    ]

    if spec.final_object_ids:
        status_matches = True
        actual = {}
        for mode, object_id in spec.final_object_ids.items():
            record = record_map.get(object_id)
            final_key = f"{mode}_final"
            final_entry = final_status.get(final_key, {})
            actual[mode] = {
                "record": record,
                "final": final_entry,
            }
            if record is None:
                status_matches = False
                continue
            for field in ("dBS", "dAI", "classification", "object_kind"):
                record_value = record.get(field if field != "object_kind" else "object_kind")
                final_value = final_entry.get(field)
                if final_value != record_value:
                    status_matches = False
        checks.append(_check("final_status_matches_records", status_matches, actual))

    for object_id, expected in spec.expected_results.items():
        actual = record_map.get(object_id)
        passed = actual is not None
        if actual is not None:
            passed = (
                actual.get("dBS") == expected.get("dBS")
                and actual.get("dAI") == expected.get("dAI")
                and actual.get("classification") == expected.get("classification")
            )
        checks.append(_check(f"expected_result::{object_id}", passed, actual))

    if spec.builder_backend == "generic_symmetry_ops":
        target_records = [
            item
            for item in records
            if item.get("row_language_level") == "target"
        ]
        oracle_available = benchmark_oracle_available(spec.group_id)

        def _target_mode_ok(item: dict[str, Any]) -> bool:
            mode = item.get("final_result_mode")
            published = item.get("classification_is_published_final")
            status = item.get("status")
            classification = item.get("classification")
            if oracle_available:
                return (
                    mode == "benchmark_aligned_final"
                    and published is True
                    and status == "success"
                    and classification is not None
                )
            if mode == "generic_final":
                return (
                    published is True
                    and status == "success"
                    and classification is not None
                    and item.get("verification_status") == "semantic_pass"
                    and item.get("same_shell_semantics") == "published_target_object"
                    and item.get("dBS") == item.get("dAI")
                )
            if mode == "diagnostic_only":
                return (
                    published is False
                    and status == "not_final"
                )
            return False

        checks.extend(
            [
                {
                    "name": "generic_geometry_from_trusted_ops_available",
                    "passed": geometry.get("status") == "built_from_trusted_symmetry_ops",
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
                    "name": "generic_current_row_compatibility_available",
                    "passed": alignment.get("compatibility_builder", {}).get("status") == "available",
                    "actual": alignment.get("compatibility_builder"),
                },
                {
                    "name": "generic_result_mode_matches_oracle_policy",
                    "passed": all(_target_mode_ok(item) for item in target_records),
                    "actual": {
                        "benchmark_oracle_available": oracle_available,
                        "allowed_final_modes": (
                            ["benchmark_aligned_final"]
                            if oracle_available
                            else ["diagnostic_only", "generic_final"]
                        ),
                        "target_records": [
                            {
                                "object_id": item.get("object_id"),
                                "final_result_mode": item.get("final_result_mode"),
                                "status": item.get("status"),
                                "classification_is_published_final": item.get(
                                    "classification_is_published_final"
                                ),
                            }
                            for item in target_records
                        ],
                    },
                },
                {
                    "name": "generic_ai_filter_is_exact",
                    "passed": all(
                        item.get("ai_failure_count", 0) == 0
                        and item.get("ai_embedding_failure_count", 0) == 0
                        and item.get("ai_incompatible_count", 0) == 0
                        for item in target_records
                    ),
                    "actual": [
                        {
                            "object_id": item.get("object_id"),
                            "ai_failure_count": item.get("ai_failure_count"),
                            "ai_incompatible_count": item.get("ai_incompatible_count"),
                            "ai_embedding_failure_count": item.get("ai_embedding_failure_count"),
                            "ai_filter_mode": item.get("ai_filter_mode"),
                        }
                        for item in target_records
                    ],
                    "required": False,
                },
                {
                    "name": "generic_no_dbs_dai_gap",
                    "passed": all(
                        (
                            item.get("final_result_mode") != "generic_final"
                            or item.get("dBS") == item.get("dAI")
                        )
                        for item in target_records
                    ),
                    "actual": [
                        {
                            "object_id": item.get("object_id"),
                            "dBS": item.get("dBS"),
                            "dAI": item.get("dAI"),
                            "dbs_dai_gap": item.get("dbs_dai_gap"),
                        }
                        for item in target_records
                    ],
                    "required": False,
                },
            ]
        )

    checks.extend(adapter.build_extra_checks(spec, artifacts, geometry, alignment, records, final_status))
    required_checks = [item for item in checks if item.get("required", True)]
    diagnostic_checks = [item for item in checks if not item.get("required", True)]
    checks_passed = all(item["passed"] for item in required_checks)
    diagnostic_checks_passed = all(item["passed"] for item in diagnostic_checks) if diagnostic_checks else True
    final_results_available = bool(
        final_status.get("single_final", {}).get("classification_is_published_final") is True
        and final_status.get("single_final", {}).get("dBS") is not None
        and final_status.get("single_final", {}).get("dAI") is not None
        and final_status.get("single_final", {}).get("classification") is not None
        and final_status.get("double_final", {}).get("classification_is_published_final") is True
        and final_status.get("double_final", {}).get("dBS") is not None
        and final_status.get("double_final", {}).get("dAI") is not None
        and final_status.get("double_final", {}).get("classification") is not None
    )
    final_results_verified = bool(
        checks_passed
        and final_results_available
        and _verification_ready(final_status.get("single_final", {}))
        and _verification_ready(final_status.get("double_final", {}))
    )
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "checks": checks,
        "checks_passed": checks_passed,
        "diagnostic_checks_passed": diagnostic_checks_passed,
        "final_results_available": final_results_available,
        "final_results_verified": final_results_verified,
        "all_passed": checks_passed and diagnostic_checks_passed,
    }
