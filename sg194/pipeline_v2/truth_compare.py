from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark_oracle_registry import load_group_truth_reference
from .utils import now_iso


def _target_record(records: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    for item in records:
        if item.get("row_language_level") == "target" and item.get("mode") == mode:
            return item
    raise ValueError(f"missing target record for mode={mode}")


def _compare_mode(record: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    comparable_fields = ("dBS", "dAI", "classification")
    truth_available = bool(truth) and any(truth.get(field) is not None for field in comparable_fields)
    field_matches = {
        field: (
            None
            if truth.get(field) is None
            else record.get(field) == truth.get(field)
        )
        for field in comparable_fields
    }
    comparable_available_fields = [field for field in comparable_fields if truth.get(field) is not None]
    return {
        "solver_object_id": record.get("object_id"),
        "solver_availability": record.get("availability"),
        "solver_final_result_mode": record.get("final_result_mode"),
        "solver_classification_is_published_final": record.get("classification_is_published_final"),
        "solver_verification_status": record.get("verification_status"),
        "solver_same_shell_semantics": record.get("same_shell_semantics"),
        "solver_dBS": record.get("dBS"),
        "solver_dAI": record.get("dAI"),
        "solver_ai_image_rank_in_bs": record.get("ai_image_rank_in_bs"),
        "solver_classification": record.get("classification"),
        "truth_reference_available": truth_available,
        "truth_available_fields": comparable_available_fields,
        "truth_dBS": truth.get("dBS"),
        "truth_dAI": truth.get("dAI"),
        "truth_classification": truth.get("classification"),
        "field_matches": field_matches,
        "all_fields_match": (
            None
            if not comparable_available_fields
            else all(bool(field_matches[field]) for field in comparable_available_fields)
        ),
    }


def build_truth_compare_report(
    repo_root: Path,
    group_id: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = load_group_truth_reference(repo_root, group_id)
    if truth is None:
        return {
            "generated_at": now_iso(),
            "group": group_id,
            "truth_compare_available": False,
            "status": "unavailable",
            "matches_truth": None,
        }

    single_record = _target_record(records, "single")
    double_record = _target_record(records, "double")
    single_compare = _compare_mode(single_record, truth["single_truth"])
    double_compare = _compare_mode(double_record, truth["double_truth"])
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "truth_compare_available": True,
        "status": "available",
        "truth_source_kind": truth.get("source_kind"),
        "truth_compare_only": truth.get("truth_compare_only", True),
        "status_file": truth.get("status_file"),
        "verdict_file": truth.get("verdict_file"),
        "external_object_label": truth.get("external_object_label"),
        "reference_scope": truth.get("reference_scope"),
        "note": truth.get("note"),
        "single": single_compare,
        "double": double_compare,
        "matches_truth": (
            None
            if not any(
                item["all_fields_match"] is not None
                for item in (single_compare, double_compare)
            )
            else all(
                item["all_fields_match"]
                for item in (single_compare, double_compare)
                if item["all_fields_match"] is not None
            )
        ),
    }


def build_truth_compare_markdown(report: dict[str, Any]) -> str:
    if not report.get("truth_compare_available"):
        return "\n".join(
            [
                f"# Generic Solver vs Truth Compare: {report['group']}",
                "",
                "- truth compare available: `False`.",
                f"- status: `{report['status']}`.",
            ]
        )
    return "\n".join(
        [
            f"# Generic Solver vs Truth Compare: {report['group']}",
            "",
            f"- truth compare available: `{report['truth_compare_available']}`.",
            f"- matches truth: `{report['matches_truth']}`.",
            f"- truth source kind: `{report['truth_source_kind']}`.",
            f"- external object label: `{report.get('external_object_label')}`.",
            f"- reference scope: `{report.get('reference_scope')}`.",
            f"- single solver vs truth: `({report['single']['solver_dBS']}, {report['single']['solver_dAI']}, {report['single']['solver_classification']})` vs `({report['single']['truth_dBS']}, {report['single']['truth_dAI']}, {report['single']['truth_classification']})`; available fields=`{report['single']['truth_available_fields']}`.",
            f"- double solver vs truth: `({report['double']['solver_dBS']}, {report['double']['solver_dAI']}, {report['double']['solver_classification']})` vs `({report['double']['truth_dBS']}, {report['double']['truth_dAI']}, {report['double']['truth_classification']})`; available fields=`{report['double']['truth_available_fields']}`.",
        ]
    )
