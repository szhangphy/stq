from __future__ import annotations

from typing import Any

from .coordinates import coordinate_usage_audit
from .models import GroupSpec
from .utils import now_iso


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
        {
            "name": "producer_commands_passed",
            "passed": bridge_status["all_passed"],
            "actual": bridge_status["commands"],
        },
        {
            "name": "geometry_summary_present",
            "passed": bool(geometry),
            "actual": geometry.get("status", geometry.get("shared_backbone_available")),
        },
        {
            "name": "result_object_ids_unique",
            "passed": len(record_map) == len(records),
            "actual": [item["object_id"] for item in records],
        },
        {
            "name": "coordinate_contract_audit",
            "passed": coordinate_audit["all_passed"],
            "actual": coordinate_audit["violations"],
        },
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
        checks.append(
            {
                "name": "final_status_matches_records",
                "passed": status_matches,
                "actual": actual,
            }
        )

    for object_id, expected in spec.expected_results.items():
        actual = record_map.get(object_id)
        passed = actual is not None
        if actual is not None:
            passed = (
                actual.get("dBS") == expected.get("dBS")
                and actual.get("dAI") == expected.get("dAI")
                and actual.get("classification") == expected.get("classification")
            )
        checks.append(
            {
                "name": f"expected_result::{object_id}",
                "passed": passed,
                "actual": actual,
            }
        )

    if spec.builder_backend == "generic_symmetry_ops":
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
                    "name": "second_group_target_is_222_1_1_1",
                    "passed": spec.group_id == "222.1.1.1",
                    "actual": spec.group_id,
                },
                {
                    "name": "generic_final_results_explicitly_blocked",
                    "passed": final_status.get("status") == "generic_builders_partial",
                    "actual": final_status.get("builder_layers"),
                },
            ]
        )

    checks.extend(adapter.build_extra_checks(spec, artifacts, geometry, alignment, records, final_status))
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "checks": checks,
        "all_passed": all(item["passed"] for item in checks),
    }
