#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

BENCHMARK_VERDICT_JSON = ROOT / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json"
EXTERNAL_BENCHMARK_JSON = ROOT / "sg194_external_benchmark_from_topmat_v3.json"
OBJECT_MATCHING_JSON = ROOT / "sg194_current_vs_external_object_matching_v3.json"
STAGE2_STATUS_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
WORKFLOW_STAGE2_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
SINGLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
CURRENT_RAW_STATUS_JSON = ROOT / "current_status_194.1.1.1.json"
PHASE_AWARE_JSON = ROOT / "sg194_phase_aware_l2_compatibility_v1.json"
EXTERNAL_MATRIX_FINAL_JSON = ROOT / "current_status_sg194_external_matrix_final.json"
README_MD = ROOT / "README.md"
HANDOFF_STAGE2_MD = ROOT / "handoff_194.1.1.1_stage2.md"
LIVE_CHECKPOINT_JSON = ROOT / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = ROOT / "live_checkpoint_sg194_1941111.md"

OUTPUT_BENCHMARK_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
OUTPUT_BENCHMARK_MD = ROOT / "current_status_1941111_benchmark_v1.md"
OUTPUT_LADDER_JSON = ROOT / "sg194_object_ladder_and_benchmark_map_v1.json"
OUTPUT_LADDER_MD = ROOT / "sg194_object_ladder_and_benchmark_map_v1.md"
OUTPUT_INVENTORY_JSON = ROOT / "sg194_authoritative_file_inventory_v1.json"
OUTPUT_INVENTORY_MD = ROOT / "sg194_authoritative_file_inventory_v1.md"
OUTPUT_REPORT_MD = ROOT / "sg194_benchmark_takeover_report_v1.md"

PACKAGE_DIR = ROOT / "review_package_sg194_benchmark_takeover_v1"
PACKAGE_TAR = ROOT / "review_package_sg194_benchmark_takeover_v1.tar.gz"

PACKAGE_COPY_TARGETS = [
    OUTPUT_BENCHMARK_JSON.name,
    OUTPUT_BENCHMARK_MD.name,
    OUTPUT_LADDER_JSON.name,
    OUTPUT_LADDER_MD.name,
    OUTPUT_INVENTORY_JSON.name,
    OUTPUT_INVENTORY_MD.name,
    OUTPUT_REPORT_MD.name,
    BENCHMARK_VERDICT_JSON.name,
    BENCHMARK_VERDICT_JSON.with_suffix(".md").name,
    EXTERNAL_BENCHMARK_JSON.name,
    EXTERNAL_BENCHMARK_JSON.with_suffix(".md").name,
    OBJECT_MATCHING_JSON.name,
    OBJECT_MATCHING_JSON.with_suffix(".md").name,
    STAGE2_STATUS_JSON.name,
    WORKFLOW_STAGE2_JSON.name,
    SINGLE_COMPLETION_JSON.name,
    DOUBLE_COMPLETION_JSON.name,
    CURRENT_RAW_STATUS_JSON.name,
    PHASE_AWARE_JSON.name,
    PHASE_AWARE_JSON.with_suffix(".md").name,
    EXTERNAL_MATRIX_FINAL_JSON.name,
    README_MD.name,
    HANDOFF_STAGE2_MD.name,
    LIVE_CHECKPOINT_JSON.name,
    LIVE_CHECKPOINT_MD.name,
]

REQUIRED_INVENTORY_PATHS = [
    "sg194/current_status_194.1.1.1_stage2.json",
    "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
    "sg194/group_194_1_1_1_single_ai_completion_summary.json",
    "sg194/group_194_1_1_1_double_ai_completion_summary.json",
    "sg194/current_status_sg194_external_matrix_final.json",
    "sg194/sg194_external_benchmark_from_topmat_v3.json",
    "sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
    "sg194/current_status_1941111_benchmark_v1.json",
    "sg194/README.md",
    "sg194/handoff_194.1.1.1_stage2.md",
    "sg194/live_checkpoint_sg194_1941111.json",
    "sg194/live_checkpoint_sg194_1941111.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def build_benchmark_status() -> dict[str, Any]:
    benchmark_verdict = load_json(BENCHMARK_VERDICT_JSON)
    external_benchmark = load_json(EXTERNAL_BENCHMARK_JSON)
    object_matching = load_json(OBJECT_MATCHING_JSON)
    stage2_status = load_json(STAGE2_STATUS_JSON)
    external_matrix_final = load_json(EXTERNAL_MATRIX_FINAL_JSON)

    target = object_matching["target"]
    benchmark = benchmark_verdict["benchmark_result"]

    return {
        "version": 1,
        "generated_at": utc_now(),
        "status": "authoritative_benchmark_oracle",
        "benchmark_authoritative": True,
        "benchmark_target": {
            "spin_space_group": target["spin_space_group"],
            "magnetic_group_og": target["magnetic_group_og"],
            "magnetic_group_bns": target["magnetic_group_bns"],
            "magnetic_type": target["magnetic_type"],
            "time_reversal": target["time_reversal"],
            "project_round_unification_statement": target["project_round_unification_statement"],
            "external_mapping_caveat": target["external_mapping_caveat"],
        },
        "benchmark_result": {
            "classification": benchmark["classification"],
            "indicator_group": benchmark["indicator_group"],
            "dBS": benchmark["dBS"],
            "dAI": benchmark["dAI"],
            "smith_diagonal_nonzero": benchmark["smith_diagonal_nonzero"],
            "finite_part": benchmark["finite_part"],
            "free_rank": benchmark["free_rank"],
        },
        "source_of_truth": {
            "primary_benchmark_verdict_json": rel(BENCHMARK_VERDICT_JSON),
            "supporting_external_benchmark_json": rel(EXTERNAL_BENCHMARK_JSON),
            "supporting_object_matching_json": rel(OBJECT_MATCHING_JSON),
            "topmat_direct_run_available": external_benchmark["availability_verdict"]["can_topmat_src_directly_give_classification"],
            "topmat_direct_dBS_available": external_benchmark["availability_verdict"]["can_topmat_src_directly_give_dBS"],
            "topmat_direct_dAI_available": external_benchmark["availability_verdict"]["can_topmat_src_directly_give_dAI"],
        },
        "which_internal_objects_are_not_benchmark": {
            "current_raw": {
                "status": "internal_raw_object",
                "files": object_matching["current_raw"]["files"],
                "summary": "Current raw stays a 16-dimensional internal BS-space object with quotient Z^3, not the magnetic benchmark.",
            },
            "phase_aware_prototype": {
                "status": "local_prototype",
                "files": object_matching["phase_aware_prototype_raw"]["files"],
                "summary": object_matching["comparison_verdict"]["which_object_is_local_prototype"],
            },
            "anchored_stage2_final_claim": {
                "status": "superseded_internal_reduced_quotient_claim",
                "file": rel(STAGE2_STATUS_JSON),
                "older_claim": object_matching["anchored_final_quotient"]["older_stage2_claim"],
                "summary": object_matching["comparison_verdict"]["which_object_is_reduced_quotient"],
            },
            "external_matrix_final_status": {
                "status": "unresolved_mapping_layer",
                "file": rel(EXTERNAL_MATRIX_FINAL_JSON),
                "summary": external_matrix_final["main_blocker"],
            },
        },
        "benchmark_takeover_verdict": {
            "phase_aware_verdict": (
                "still potentially needed, but only after object mapping to benchmark is clarified"
            ),
            "phase_aware_detail": benchmark_verdict["repo_object_verdict"]["phase_aware_role"],
            "stage2_13_trivial_verdict": (
                "The older 13/13/trivial stage2 claim is retained only as an internally anchored reduced quotient claim and is superseded for benchmark use."
            ),
        },
        "conflict_resolution": {
            "superseded_files_for_benchmark_use": [
                rel(STAGE2_STATUS_JSON),
                rel(WORKFLOW_STAGE2_JSON),
                rel(SINGLE_COMPLETION_JSON),
                rel(DOUBLE_COMPLETION_JSON),
            ],
            "unresolved_mapping_file": rel(EXTERNAL_MATRIX_FINAL_JSON),
            "reason": (
                "The copied topmat magnetic benchmark fixes the benchmark result at Z6 / dBS 10 / dAI 10. "
                "The older stage2 13/13/trivial result is therefore not allowed to remain the repo's benchmark-final claim."
            ),
        },
        "superseded_stage2_snapshot": {
            "single_final_rank_bs": stage2_status["single_final_rank_bs"],
            "single_final_rank_ai": stage2_status["single_final_rank_ai"],
            "single_final_quotient_group": stage2_status["single_final_quotient_group"],
            "double_final_rank_bs": stage2_status["double_final_rank_bs"],
            "double_final_rank_ai": stage2_status["double_final_rank_ai"],
            "double_final_quotient_group": stage2_status["double_final_quotient_group"],
        },
    }


def render_benchmark_status_md(payload: dict[str, Any]) -> str:
    target = payload["benchmark_target"]
    result = payload["benchmark_result"]
    return f"""# SG194 benchmark authoritative status v1

{target["project_round_unification_statement"]}

## Status

- benchmark-authoritative: `true`
- status: `{payload["status"]}`
- classification / indicator group: `{result["classification"]}`
- dBS: `{result["dBS"]}`
- dAI: `{result["dAI"]}`
- Smith nonzero diagonal: `{result["smith_diagonal_nonzero"]}`

## Source of truth

- primary: `{payload["source_of_truth"]["primary_benchmark_verdict_json"]}`
- support: `{payload["source_of_truth"]["supporting_external_benchmark_json"]}`
- support: `{payload["source_of_truth"]["supporting_object_matching_json"]}`
- direct topmat classification available: `{str(payload["source_of_truth"]["topmat_direct_run_available"]).lower()}`
- direct topmat dBS available: `{str(payload["source_of_truth"]["topmat_direct_dBS_available"]).lower()}`
- direct topmat dAI available: `{str(payload["source_of_truth"]["topmat_direct_dAI_available"]).lower()}`

## Caveat

- {target["external_mapping_caveat"]}

## Not benchmark

- current raw: {payload["which_internal_objects_are_not_benchmark"]["current_raw"]["summary"]}
- phase-aware prototype: {payload["which_internal_objects_are_not_benchmark"]["phase_aware_prototype"]["summary"]}
- anchored stage2 final claim: {payload["which_internal_objects_are_not_benchmark"]["anchored_stage2_final_claim"]["summary"]}
- external-matrix-final status: {payload["which_internal_objects_are_not_benchmark"]["external_matrix_final_status"]["summary"]}

## Takeover verdict

- phase-aware verdict: {payload["benchmark_takeover_verdict"]["phase_aware_verdict"]}
- phase-aware detail: {payload["benchmark_takeover_verdict"]["phase_aware_detail"]}
- stage2 13/trivial verdict: {payload["benchmark_takeover_verdict"]["stage2_13_trivial_verdict"]}
"""


def build_object_ladder(benchmark_status: dict[str, Any]) -> dict[str, Any]:
    object_matching = load_json(OBJECT_MATCHING_JSON)
    benchmark_verdict = load_json(BENCHMARK_VERDICT_JSON)
    external_matrix_final = load_json(EXTERNAL_MATRIX_FINAL_JSON)
    phase_aware = load_json(PHASE_AWARE_JSON)
    current_raw = load_json(CURRENT_RAW_STATUS_JSON)
    stage2_status = load_json(STAGE2_STATUS_JSON)

    entries = [
        {
            "object_name": "topmat magnetic benchmark oracle",
            "source_file": rel(BENCHMARK_VERDICT_JSON),
            "object_kind": "external magnetic benchmark oracle",
            "coordinate_language": "topmat magnetic BS/AI lattice for OG 194.1.1494 / BNS 194.263",
            "complete_classification": True,
            "benchmark_authoritative": False,
            "current_value": "classification Z6, dBS 10, dAI 10",
            "relation_to_benchmark": "raw oracle payload from copied topmat reference benchmark",
            "status": "authoritative_oracle_support",
        },
        {
            "object_name": "benchmark authoritative status",
            "source_file": rel(OUTPUT_BENCHMARK_JSON),
            "object_kind": "authoritative benchmark status",
            "coordinate_language": "project benchmark convention: SSG 194.1.1.1 paired with OG 194.1.1494 / BNS 194.263",
            "complete_classification": True,
            "benchmark_authoritative": True,
            "current_value": "classification Z6, dBS 10, dAI 10",
            "relation_to_benchmark": "authoritative repo-level benchmark status",
            "status": "authoritative",
        },
        {
            "object_name": "current raw",
            "source_file": rel(CURRENT_RAW_STATUS_JSON),
            "object_kind": "internal raw object",
            "coordinate_language": "repo 16-dimensional raw internal BS space",
            "complete_classification": False,
            "benchmark_authoritative": False,
            "current_value": (
                "single blocked before honest AI completion; double blocked before honest AI completion; "
                f"matrix nullity {current_raw['key_matrices']['single_nullity']}"
            ),
            "relation_to_benchmark": object_matching["current_raw"]["reason"],
            "status": "internal",
        },
        {
            "object_name": "phase-aware raw prototype",
            "source_file": rel(PHASE_AWARE_JSON),
            "object_kind": "local prototype",
            "coordinate_language": "phase-aware line/endpoint compatibility repair layer",
            "complete_classification": False,
            "benchmark_authoritative": False,
            "current_value": (
                f"raw BS rank 16 -> {phase_aware['local_validation']['refined_raw_rank_bs_single']} "
                "after local phase-aware refinement"
            ),
            "relation_to_benchmark": benchmark_status["benchmark_takeover_verdict"]["phase_aware_detail"],
            "status": "prototype",
        },
        {
            "object_name": "anchored stage2 final quotient claim",
            "source_file": rel(STAGE2_STATUS_JSON),
            "object_kind": "anchored internal reduced quotient claim",
            "coordinate_language": "repo current-to-standard ordinary row language",
            "complete_classification": False,
            "benchmark_authoritative": False,
            "current_value": (
                f"single {stage2_status['single_final_rank_bs']}/{stage2_status['single_final_rank_ai']}/"
                f"{stage2_status['single_final_quotient_group']}; double {stage2_status['double_final_rank_bs']}/"
                f"{stage2_status['double_final_rank_ai']}/{stage2_status['double_final_quotient_group']}"
            ),
            "relation_to_benchmark": (
                "Retained as an internal reduced quotient claim only; superseded for benchmark use by the magnetic benchmark oracle."
            ),
            "status": "superseded",
        },
        {
            "object_name": "external matrix final status",
            "source_file": rel(EXTERNAL_MATRIX_FINAL_JSON),
            "object_kind": "unresolved mapping layer",
            "coordinate_language": "current internal generator images vs cached external standard row spaces",
            "complete_classification": False,
            "benchmark_authoritative": False,
            "current_value": (
                f"single final_external_quotient {external_matrix_final['single_status']['final_external_quotient']}; "
                f"double final_external_quotient {external_matrix_final['double_status']['final_external_quotient']}"
            ),
            "relation_to_benchmark": external_matrix_final["main_blocker"],
            "status": "unresolved",
        },
    ]

    return {
        "generated_at": utc_now(),
        "benchmark_authoritative_file": rel(OUTPUT_BENCHMARK_JSON),
        "entries": entries,
        "verdicts": {
            "closest_to_benchmark_truth": benchmark_verdict["repo_object_verdict"]["closest_to_external_truth"],
            "phase_aware_verdict": benchmark_status["benchmark_takeover_verdict"]["phase_aware_verdict"],
            "benchmark_oracle_result": benchmark_status["benchmark_result"],
        },
    }


def render_object_ladder_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 object ladder and benchmark map v1",
        "",
        f"- benchmark authoritative file: `{payload['benchmark_authoritative_file']}`",
        "",
        "| object | kind | complete classification | benchmark-authoritative | current value | relation to benchmark | status |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in payload["entries"]:
        lines.append(
            "| "
            f"{entry['object_name']} | "
            f"{entry['object_kind']} | "
            f"{str(entry['complete_classification']).lower()} | "
            f"{str(entry['benchmark_authoritative']).lower()} | "
            f"{entry['current_value']} | "
            f"{entry['relation_to_benchmark']} | "
            f"{entry['status']} |"
        )
    lines.extend(
        [
            "",
            "## Verdicts",
            "",
            f"- closest to benchmark truth: {payload['verdicts']['closest_to_benchmark_truth']}",
            f"- phase-aware verdict: {payload['verdicts']['phase_aware_verdict']}",
            (
                f"- benchmark oracle result: classification `{payload['verdicts']['benchmark_oracle_result']['classification']}`, "
                f"dBS `{payload['verdicts']['benchmark_oracle_result']['dBS']}`, "
                f"dAI `{payload['verdicts']['benchmark_oracle_result']['dAI']}`"
            ),
        ]
    )
    return "\n".join(lines)


def build_authoritative_inventory() -> dict[str, Any]:
    benchmark_status = load_json(OUTPUT_BENCHMARK_JSON) if OUTPUT_BENCHMARK_JSON.exists() else build_benchmark_status()

    entries = [
        {
            "path": "sg194/current_status_1941111_benchmark_v1.json",
            "classification": "benchmark_authoritative_status",
            "benchmark_authoritative": True,
            "object_kind": "authoritative benchmark status",
            "current_value": "Z6 / dBS 10 / dAI 10",
            "notes": "Primary benchmark-first status file for SG194 after takeover.",
        },
        {
            "path": "sg194/current_status_1941111_benchmark_v1.md",
            "classification": "benchmark_authoritative_status",
            "benchmark_authoritative": True,
            "object_kind": "human-readable benchmark status",
            "current_value": "benchmark-first summary",
            "notes": "Markdown companion to the authoritative benchmark JSON.",
        },
        {
            "path": "sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
            "classification": "benchmark_oracle",
            "benchmark_authoritative": False,
            "object_kind": "benchmark oracle payload",
            "current_value": "Z6 / dBS 10 / dAI 10",
            "notes": "Copied topmat-derived oracle verdict.",
        },
        {
            "path": "sg194/sg194_external_benchmark_from_topmat_v3.json",
            "classification": "benchmark_oracle_support",
            "benchmark_authoritative": False,
            "object_kind": "benchmark support data",
            "current_value": "topmat direct-vs-copied capability audit",
            "notes": "Records what topmat_src gives directly and what had to be computed locally.",
        },
        {
            "path": "sg194/sg194_current_vs_external_object_matching_v3.json",
            "classification": "reconciliation_support",
            "benchmark_authoritative": False,
            "object_kind": "benchmark reconciliation map",
            "current_value": "raw / phase-aware / stage2 matched against benchmark",
            "notes": "Explains which internal objects are not the benchmark.",
        },
        {
            "path": "sg194/current_status_194.1.1.1.json",
            "classification": "internal_raw_object",
            "benchmark_authoritative": False,
            "object_kind": "raw internal status",
            "current_value": "pre-stage2 blocked current raw object",
            "notes": "Raw internal SG194 object before later internal reductions.",
        },
        {
            "path": "sg194/group_194_1_1_1_single_indicator_group_summary.json",
            "classification": "internal_raw_object",
            "benchmark_authoritative": False,
            "object_kind": "single raw quotient summary",
            "current_value": "Z^3 in raw internal BS space",
            "notes": "Not benchmark; internal raw quotient only.",
        },
        {
            "path": "sg194/group_194_1_1_1_double_indicator_group_summary.json",
            "classification": "internal_raw_object",
            "benchmark_authoritative": False,
            "object_kind": "double raw quotient summary",
            "current_value": "Z^3 in raw internal BS space",
            "notes": "Not benchmark; internal raw quotient only.",
        },
        {
            "path": "sg194/sg194_phase_aware_l2_compatibility_v1.json",
            "classification": "local_prototype",
            "benchmark_authoritative": False,
            "object_kind": "phase-aware raw repair prototype",
            "current_value": "raw BS rank 16 -> 13 locally",
            "notes": benchmark_status["benchmark_takeover_verdict"]["phase_aware_detail"],
        },
        {
            "path": "sg194/current_status_194.1.1.1_stage2.json",
            "classification": "stale_superseded",
            "benchmark_authoritative": False,
            "object_kind": "anchored internal reduced quotient claim",
            "current_value": "13 / 13 / trivial",
            "notes": "Retained as internal stage2 claim only; superseded for benchmark use.",
        },
        {
            "path": "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
            "classification": "stale_superseded",
            "benchmark_authoritative": False,
            "object_kind": "stage2 workflow summary",
            "current_value": "13 / 13 / trivial",
            "notes": "Internal stage2 summary; no longer benchmark-final.",
        },
        {
            "path": "sg194/group_194_1_1_1_single_ai_completion_summary.json",
            "classification": "stale_superseded",
            "benchmark_authoritative": False,
            "object_kind": "single internal completion summary",
            "current_value": "13 / 13 / trivial",
            "notes": "Internal completion summary only; not the benchmark classification.",
        },
        {
            "path": "sg194/group_194_1_1_1_double_ai_completion_summary.json",
            "classification": "stale_superseded",
            "benchmark_authoritative": False,
            "object_kind": "double internal completion summary",
            "current_value": "13 / 13 / trivial",
            "notes": "Internal completion summary only; not the benchmark classification.",
        },
        {
            "path": "sg194/current_status_sg194_external_matrix_final.json",
            "classification": "unresolved_mapping_layer",
            "benchmark_authoritative": False,
            "object_kind": "mapping-layer unresolved status",
            "current_value": "single null / double null",
            "notes": "Still useful, but only as current-to-external mapping blocker status.",
        },
        {
            "path": "sg194/README.md",
            "classification": "benchmark_portal",
            "benchmark_authoritative": False,
            "object_kind": "repo SG194 entrypoint",
            "current_value": "benchmark-first index",
            "notes": "Should point readers to the new benchmark authoritative status first.",
        },
        {
            "path": "sg194/handoff_194.1.1.1_stage2.md",
            "classification": "stale_superseded",
            "benchmark_authoritative": False,
            "object_kind": "internal stage2 handoff",
            "current_value": "13 / 13 / trivial handoff",
            "notes": "Retained only as internal stage2 handoff, not benchmark-final.",
        },
        {
            "path": "sg194/live_checkpoint_sg194_1941111.json",
            "classification": "benchmark_portal",
            "benchmark_authoritative": False,
            "object_kind": "rolling checkpoint",
            "current_value": "benchmark takeover checkpoint",
            "notes": "Checkpoint should summarize the benchmark takeover state, not the old stage2 final claim.",
        },
        {
            "path": "sg194/live_checkpoint_sg194_1941111.md",
            "classification": "benchmark_portal",
            "benchmark_authoritative": False,
            "object_kind": "rolling checkpoint markdown",
            "current_value": "benchmark takeover checkpoint",
            "notes": "Human-readable checkpoint companion.",
        },
        {
            "path": "sg194/review_package_sg194_stage2_closeout_followup_v3/README.md",
            "classification": "stale_package_portal",
            "benchmark_authoritative": False,
            "object_kind": "historical stage2 package portal",
            "current_value": "package says 13 / 13 / trivial",
            "notes": "Historical internal package; superseded for benchmark use by the benchmark takeover artifacts.",
        },
        {
            "path": "sg194/review_package_sg194_stage2_closeout_followup_v3/handoff_194.1.1.1_stage2.md",
            "classification": "stale_package_portal",
            "benchmark_authoritative": False,
            "object_kind": "historical stage2 package handoff",
            "current_value": "package handoff says trivial",
            "notes": "Historical internal package handoff; not benchmark authoritative.",
        },
        {
            "path": "sg194/review_package_sg194_stage2_closeout_followup_v3/live_checkpoint_sg194_1941111.md",
            "classification": "stale_package_portal",
            "benchmark_authoritative": False,
            "object_kind": "historical stage2 package checkpoint",
            "current_value": "package checkpoint says trivial",
            "notes": "Historical internal package checkpoint; not benchmark authoritative.",
        },
    ]

    return {
        "generated_at": utc_now(),
        "benchmark_authoritative_file": "sg194/current_status_1941111_benchmark_v1.json",
        "entries": entries,
        "inventory_verdict": {
            "benchmark_authoritative_count": sum(1 for entry in entries if entry["benchmark_authoritative"]),
            "mandatory_paths_present": all(path in {entry["path"] for entry in entries} for path in REQUIRED_INVENTORY_PATHS),
            "stage2_files_marked_superseded": True,
        },
    }


def render_inventory_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 authoritative-looking file inventory v1",
        "",
        f"- benchmark authoritative file: `{payload['benchmark_authoritative_file']}`",
        "",
        "| path | classification | benchmark-authoritative | object kind | current value | notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in payload["entries"]:
        lines.append(
            "| "
            f"{entry['path']} | "
            f"{entry['classification']} | "
            f"{str(entry['benchmark_authoritative']).lower()} | "
            f"{entry['object_kind']} | "
            f"{entry['current_value']} | "
            f"{entry['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Inventory verdict",
            "",
            f"- benchmark-authoritative file count: `{payload['inventory_verdict']['benchmark_authoritative_count']}`",
            f"- mandatory paths present: `{str(payload['inventory_verdict']['mandatory_paths_present']).lower()}`",
            f"- stage2 files marked superseded: `{str(payload['inventory_verdict']['stage2_files_marked_superseded']).lower()}`",
        ]
    )
    return "\n".join(lines)


def build_takeover_report(
    benchmark_status: dict[str, Any],
    ladder: dict[str, Any],
    inventory: dict[str, Any],
) -> str:
    result = benchmark_status["benchmark_result"]
    return f"""# SG194 benchmark takeover report v1

## Summary

- benchmark authoritative status file: `{rel(OUTPUT_BENCHMARK_JSON)}`
- benchmark result: classification `{result["classification"]}`, dBS `{result["dBS"]}`, dAI `{result["dAI"]}`
- benchmark-authoritative count in inventory: `{inventory["inventory_verdict"]["benchmark_authoritative_count"]}`

## Takeover

- The repo now has one benchmark-authoritative SG194 conclusion: `Z6`, `dBS = 10`, `dAI = 10`.
- The benchmark oracle comes from the copied topmat magnetic benchmark tracked in `{rel(BENCHMARK_VERDICT_JSON)}`.
- `current raw` remains an internal raw object.
- `phase-aware` remains a local prototype.
- `current_status_194.1.1.1_stage2.json` and the stage2 workflow/completion summaries are retained only as internally anchored reduced-quotient claims and are superseded for benchmark use.
- `current_status_sg194_external_matrix_final.json` remains an unresolved current-to-external mapping layer, not the benchmark oracle.

## Phase-aware verdict

- formal verdict: {benchmark_status["benchmark_takeover_verdict"]["phase_aware_verdict"]}
- detail: {benchmark_status["benchmark_takeover_verdict"]["phase_aware_detail"]}

## Object ladder

- authoritative entry count: `{sum(1 for entry in ladder["entries"] if entry["status"] == "authoritative")}`
- superseded entry count: `{sum(1 for entry in ladder["entries"] if entry["status"] == "superseded")}`
- unresolved entry count: `{sum(1 for entry in ladder["entries"] if entry["status"] == "unresolved")}`

## Review package

- directory: `{rel(PACKAGE_DIR)}`
- tarball: `{rel(PACKAGE_TAR)}`
- package includes the benchmark authoritative status, object ladder, authoritative file inventory, topmat benchmark verdict, current-vs-external matching, README, live checkpoint, and relevant status summaries.
"""


def build_package_readme() -> str:
    return """# Review Package: SG194 Benchmark Takeover v1

## Scope

- unify SG194 onto the copied topmat magnetic benchmark oracle
- make `Z6 / dBS 10 / dAI 10` the only benchmark-authoritative conclusion
- de-authorize old stage2 `13 / trivial` files for benchmark use

## Included files

- benchmark authoritative status: `current_status_1941111_benchmark_v1.json` and `.md`
- object ladder / benchmark map: `sg194_object_ladder_and_benchmark_map_v1.json` and `.md`
- authoritative-looking file inventory: `sg194_authoritative_file_inventory_v1.json` and `.md`
- benchmark takeover report: `sg194_benchmark_takeover_report_v1.md`
- topmat benchmark verdict: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json` and `.md`
- external benchmark support: `sg194_external_benchmark_from_topmat_v3.json` and `.md`
- current-vs-external reconciliation: `sg194_current_vs_external_object_matching_v3.json` and `.md`
- updated repo entry files: `README.md`, `live_checkpoint_sg194_1941111.json`, `live_checkpoint_sg194_1941111.md`
- relevant downgraded internal status summaries: `current_status_194.1.1.1_stage2.json`, `workflow_portability_stage2_summary_194.1.1.1.json`, `group_194_1_1_1_single_ai_completion_summary.json`, `group_194_1_1_1_double_ai_completion_summary.json`, `handoff_194.1.1.1_stage2.md`
"""


def write_outputs() -> None:
    benchmark_status = build_benchmark_status()
    ladder = build_object_ladder(benchmark_status)
    inventory = build_authoritative_inventory()

    write_json(OUTPUT_BENCHMARK_JSON, benchmark_status)
    write_text(OUTPUT_BENCHMARK_MD, render_benchmark_status_md(benchmark_status))
    write_json(OUTPUT_LADDER_JSON, ladder)
    write_text(OUTPUT_LADDER_MD, render_object_ladder_md(ladder))
    write_json(OUTPUT_INVENTORY_JSON, inventory)
    write_text(OUTPUT_INVENTORY_MD, render_inventory_md(inventory))
    write_text(OUTPUT_REPORT_MD, build_takeover_report(benchmark_status, ladder, inventory))

    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir()
    write_text(PACKAGE_DIR / "README.md", build_package_readme())
    for filename in PACKAGE_COPY_TARGETS:
        src = ROOT / filename
        if src.exists():
            shutil.copy2(src, PACKAGE_DIR / src.name)
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as handle:
        handle.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate() -> list[str]:
    errors: list[str] = []

    if not OUTPUT_BENCHMARK_JSON.exists():
        errors.append("missing current_status_1941111_benchmark_v1.json")
        return errors

    benchmark_status = load_json(OUTPUT_BENCHMARK_JSON)
    if benchmark_status.get("benchmark_authoritative") is not True:
        errors.append("benchmark status is not marked benchmark_authoritative=true")
    result = benchmark_status.get("benchmark_result", {})
    if result.get("classification") != "Z6":
        errors.append("benchmark classification is not Z6")
    if result.get("dBS") != 10:
        errors.append("benchmark dBS is not 10")
    if result.get("dAI") != 10:
        errors.append("benchmark dAI is not 10")

    for path in [STAGE2_STATUS_JSON, WORKFLOW_STAGE2_JSON, SINGLE_COMPLETION_JSON, DOUBLE_COMPLETION_JSON]:
        payload = load_json(path)
        if payload.get("benchmark_authoritative") is not False:
            errors.append(f"{path.name} is not marked benchmark_authoritative=false")
        status = str(payload.get("status", ""))
        if "superseded" not in status and "deauthorized" not in status:
            errors.append(f"{path.name} status is not explicitly superseded/deauthorized")

    readme_text = README_MD.read_text()
    if "current_status_1941111_benchmark_v1.json" not in readme_text:
        errors.append("README does not point to current_status_1941111_benchmark_v1.json")
    if "historical internal references" not in readme_text.lower():
        errors.append("README does not clearly label old stage2 material as historical internal references")

    live_checkpoint_text = LIVE_CHECKPOINT_MD.read_text()
    if "benchmark takeover" not in live_checkpoint_text.lower():
        errors.append("live checkpoint markdown does not mention benchmark takeover")
    if "Z6" not in live_checkpoint_text or "dBS = 10" not in live_checkpoint_text or "dAI = 10" not in live_checkpoint_text:
        errors.append("live checkpoint markdown does not carry benchmark values")

    inventory = load_json(OUTPUT_INVENTORY_JSON)
    inventory_paths = {entry["path"] for entry in inventory["entries"]}
    for path in REQUIRED_INVENTORY_PATHS:
        if path not in inventory_paths:
            errors.append(f"inventory missing required path {path}")
    benchmark_count = sum(1 for entry in inventory["entries"] if entry["benchmark_authoritative"])
    if benchmark_count != 2:
        errors.append(f"expected 2 benchmark-authoritative inventory entries, found {benchmark_count}")

    ladder = load_json(OUTPUT_LADDER_JSON)
    authoritative_entries = [entry for entry in ladder["entries"] if entry["benchmark_authoritative"]]
    if len(authoritative_entries) != 1:
        errors.append(f"expected 1 benchmark-authoritative ladder entry, found {len(authoritative_entries)}")

    if not PACKAGE_DIR.exists():
        errors.append("review package directory is missing")
    if not PACKAGE_TAR.exists():
        errors.append("review package tarball is missing")
    required_package_files = {
        "README.md",
        OUTPUT_BENCHMARK_JSON.name,
        OUTPUT_LADDER_JSON.name,
        OUTPUT_INVENTORY_JSON.name,
        OUTPUT_REPORT_MD.name,
        BENCHMARK_VERDICT_JSON.name,
        OBJECT_MATCHING_JSON.name,
        README_MD.name,
        LIVE_CHECKPOINT_JSON.name,
        LIVE_CHECKPOINT_MD.name,
        STAGE2_STATUS_JSON.name,
        WORKFLOW_STAGE2_JSON.name,
        SINGLE_COMPLETION_JSON.name,
        DOUBLE_COMPLETION_JSON.name,
    }
    if PACKAGE_DIR.exists():
        package_files = {path.name for path in PACKAGE_DIR.iterdir()}
        for name in required_package_files:
            if name not in package_files:
                errors.append(f"review package missing {name}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write benchmark takeover outputs and review package")
    parser.add_argument("--validate", action="store_true", help="validate benchmark takeover consistency")
    args = parser.parse_args()

    if args.write:
        write_outputs()

    if args.validate:
        errors = validate()
        summary = {
            "status": "ok" if not errors else "error",
            "errors": errors,
            "benchmark_status": rel(OUTPUT_BENCHMARK_JSON),
            "review_package_dir": rel(PACKAGE_DIR),
            "review_package_tar": rel(PACKAGE_TAR),
        }
        print(json.dumps(summary, indent=2))
        return 0 if not errors else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
