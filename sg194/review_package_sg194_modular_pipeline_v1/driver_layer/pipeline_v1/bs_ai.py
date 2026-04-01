from __future__ import annotations

from typing import Any

from .models import GroupSpec
from .utils import now_iso


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


def build_result_objects(spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    if not spec.runnable:
        return []

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
            "dBS": single["raw_current_rank_bs"],
            "dAI": single["raw_current_rank_ai"],
            "classification": single_raw_group,
            "free_rank": single_raw_free,
            "finite_part": single_raw_finite,
            "quotient_derivation_mode": "direct_raw_current_provenance",
            "exact_alignment_status": "not_applicable",
            "source_files": [spec.artifacts["stage2_status"]],
        },
        {
            "object_id": "single_target_exact",
            "mode": "single",
            "row_language_level": "target",
            "row_language_kind": stage2["single_target_row_language_kind"],
            "object_kind": stage2["single_final_object_kind"],
            "dBS": stage2["single_final_rank_bs"],
            "dAI": stage2["single_final_rank_ai"],
            "classification": single_target_group,
            "free_rank": single_target_free,
            "finite_part": single_target_finite,
            "quotient_derivation_mode": stage2["single_final_quotient_derivation_mode"],
            "exact_alignment_status": stage2["single_target_exact_generator_identity_status"],
            "source_files": [
                spec.artifacts["stage2_status"],
                spec.artifacts["projection_summary"],
            ],
        },
        {
            "object_id": "double_raw_current",
            "mode": "double",
            "row_language_level": "raw",
            "row_language_kind": spec.special_rules["raw_row_language_kind"],
            "object_kind": "raw_current_provenance_object",
            "dBS": double["rank_bs_raw_internal"],
            "dAI": double["rank_ai_raw_internal"],
            "classification": double_raw_group,
            "free_rank": double_raw_free,
            "finite_part": double_raw_finite,
            "quotient_derivation_mode": "direct_raw_current_provenance",
            "exact_alignment_status": "not_applicable",
            "source_files": [spec.artifacts["stage2_status"]],
        },
        {
            "object_id": "double_target_benchmark_facing",
            "mode": "double",
            "row_language_level": "target",
            "row_language_kind": spec.special_rules["target_row_language_kind"],
            "object_kind": stage2["double_final_object_kind"],
            "dBS": stage2["double_final_rank_bs"],
            "dAI": stage2["double_final_rank_ai"],
            "classification": double_target_group,
            "free_rank": int(benchmark["free_rank"]),
            "finite_part": list(benchmark["finite_part"]),
            "quotient_derivation_mode": stage2["double_final_quotient_derivation_mode"],
            "exact_alignment_status": stage2["double_internalization_status"],
            "source_files": [
                spec.artifacts["stage2_status"],
                spec.artifacts["benchmark_status"],
            ],
        },
    ]


def filter_result_objects(records: list[dict[str, Any]], mode: str, row_language: str) -> list[dict[str, Any]]:
    selected = records
    if mode != "both":
        selected = [item for item in selected if item["mode"] == mode]
    if row_language != "all":
        selected = [item for item in selected if item["row_language_level"] == row_language]
    return selected


def build_bs_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "dBS": item["dBS"],
            }
            for item in records
        ],
    }


def build_ai_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "dAI": item["dAI"],
            }
            for item in records
        ],
    }
