#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "review_package_sg194_internalization_fix_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
OBJECT_LADDER_JSON = ROOT / "sg194_object_ladder_and_benchmark_map_v1.json"
OBJECT_LADDER_MD = ROOT / "sg194_object_ladder_and_benchmark_map_v1.md"
INVENTORY_JSON = ROOT / "sg194_authoritative_file_inventory_v1.json"
INVENTORY_MD = ROOT / "sg194_authoritative_file_inventory_v1.md"
README_MD = ROOT / "README.md"
LIVE_CHECKPOINT_JSON = ROOT / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = ROOT / "live_checkpoint_sg194_1941111.md"
RAW_STATUS_JSON = ROOT / "current_status_194.1.1.1.json"
STAGE2_STATUS_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
SINGLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
BENCHMARK_VERDICT_JSON = ROOT / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json"
BENCHMARK_VERDICT_MD = ROOT / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.md"
BENCHMARK_VERIFY_JSON = ROOT / "sg194_topmat_independent_verify_v1.json"
BENCHMARK_VERIFY_MD = ROOT / "sg194_topmat_independent_verify_v1.md"

PATCH_SUMMARY_JSON = ROOT / "sg194_double_complement_patch_summary_v1.json"
PATCHED_CANDIDATES_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched_v2.json"
PATCHED_GROUP_JSON = ROOT / "group_194_1_1_1_double_indicator_group_summary_patched_v2.json"
PATCHED_AI_IN_BS_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched_v2.json"
EXTERNAL_SPINORIAL_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"

INTERNALIZATION_GAP_JSON = ROOT / "sg194_internalization_gap_v1.json"
INTERNALIZATION_GAP_MD = ROOT / "sg194_internalization_gap_v1.md"
INTERNALIZATION_FIX_JSON = ROOT / "sg194_internalization_fix_attempt_v1.json"
INTERNALIZATION_FIX_MD = ROOT / "sg194_internalization_fix_attempt_v1.md"
ADOPTION_VS_INTERNALIZATION_JSON = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.json"
ADOPTION_VS_INTERNALIZATION_MD = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.md"
REMAINING_CLEANUP_JSON = ROOT / "sg194_remaining_cleanup_v1.json"
REMAINING_CLEANUP_MD = ROOT / "sg194_remaining_cleanup_v1.md"

REVIEW_MAP_MD = PACKAGE_DIR / "REVIEW_MAP.md"
PACKAGE_README_MD = PACKAGE_DIR / "README.md"
PACKAGE_MANIFEST_MD = PACKAGE_DIR / "REPRODUCIBILITY_MANIFEST.md"
PACKAGE_MANIFEST_JSON = PACKAGE_DIR / "reproducibility_manifest_v1.json"

TRACKED_DELETE = [
    "sg194/debug_sg194_source_bs_fix_v1.py",
    "sg194/sg194_source_bs_vs_benchmark_gap_v1.json",
    "sg194/sg194_source_bs_vs_benchmark_gap_v1.md",
    "sg194/sg194_source_bs_fix_attempt_v1.json",
    "sg194/sg194_source_bs_fix_attempt_v1.md",
    "sg194/review_package_sg194_source_bs_fix_v1.tar.gz",
    "sg194/review_package_sg194_source_bs_fix_v1",
]
LOCAL_DELETE = [
    "sg194/review_package_sg194_bs_ai_separation_audit",
    "sg194/review_package_sg194_stage2_closeout_followup_v2",
    "sg194/review_package_sg194_stage2_closeout_followup_v3",
    "sg194/workflow_portability_report_stage2_194.1.1.1.aux",
    "sg194/workflow_portability_report_stage2_194.1.1.1.log",
]
HISTORICAL_ADOPTION = {
    "top_level_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
    "single_published_result_source": "benchmark_oracle_adoption_v1",
    "double_published_result_source": "benchmark_oracle_adoption_v1",
    "single_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
    "double_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git_output(args: list[str], default: str = "") -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=ROOT.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return default
    return completed.stdout.strip() or default


def repo_rel(path: Path) -> str:
    return path.relative_to(ROOT.parent).as_posix()


def status_lines() -> list[str]:
    output = git_output(["status", "--short"], default="")
    return [line for line in output.splitlines() if line.strip()]


def cleanup_findings() -> list[str]:
    clutter: list[str] = []
    for pattern in ("review_package_*", "*.aux", "*.log"):
        for path in sorted(ROOT.glob(pattern)):
            if path.name.startswith(PACKAGE_NAME):
                continue
            if path.name in {"review_package_sg194_internalization_fix_v1", f"{PACKAGE_NAME}.tar.gz"}:
                continue
            clutter.append(repo_rel(path))
    return sorted(dict.fromkeys(clutter))


def matrix_rank_record(current: sp.Matrix, external: sp.Matrix) -> dict[str, int]:
    current_t = current.T
    external_t = external.T
    current_rank = int(current_t.rank())
    external_rank = int(external_t.rank())
    union_rank = int(sp.Matrix.hstack(current_t, external_t).rank())
    intersection_rank = current_rank + external_rank - union_rank
    return {
        "current_rank": current_rank,
        "external_rank": external_rank,
        "union_rank": union_rank,
        "intersection_rank": intersection_rank,
        "current_only_dimension": current_rank - intersection_rank,
        "external_only_dimension": external_rank - intersection_rank,
    }


def build_context() -> dict[str, Any]:
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    benchmark = benchmark_status["benchmark_result"]
    stage2_status = load_json(STAGE2_STATUS_JSON)
    stage2_summary = load_json(STAGE2_SUMMARY_JSON)
    raw_status = load_json(RAW_STATUS_JSON)
    patch_summary = load_json(PATCH_SUMMARY_JSON)
    patched_candidates = load_json(PATCHED_CANDIDATES_JSON)
    patched_group = load_json(PATCHED_GROUP_JSON)
    patched_ai_in_bs = load_json(PATCHED_AI_IN_BS_JSON)
    external_spinorial = load_json(EXTERNAL_SPINORIAL_JSON)

    external_labels = [f"{item['letter_key']}:{item['bandrep_label']}" for item in external_spinorial["column_labels"]]
    current_labels = [candidate["source_payload"]["external_channel_label"] for candidate in patched_candidates["candidates"]]
    selected_row_indices = [
        idx
        for idx, token in enumerate(patched_candidates["unknown_ordering"])
        if token.split("_R")[0] in {"P1", "P2", "P3", "P4", "P5", "P6", "B1"}
    ]
    current_map = {candidate["source_payload"]["external_channel_label"]: candidate for candidate in patched_candidates["candidates"]}
    current_full = sp.Matrix.hstack(
        *[
            sp.Matrix([current_map[label]["unknown_vector"][row_idx] for row_idx in selected_row_indices])
            for label in external_labels
        ]
    )
    external_full = sp.Matrix(external_spinorial["matrix_entries"])
    rank_record = matrix_rank_record(current_full, external_full)
    ai_rank = int(sp.Matrix(patched_ai_in_bs["matrix"]).rank())

    return {
        "generated_at": now_iso(),
        "head_commit": git_output(["rev-parse", "HEAD"], default="unknown"),
        "benchmark_status": benchmark_status,
        "benchmark": benchmark,
        "stage2_status": stage2_status,
        "stage2_summary": stage2_summary,
        "raw_status": raw_status,
        "patch_summary": patch_summary,
        "patched_candidates": patched_candidates,
        "patched_group": patched_group,
        "patched_ai_in_bs": patched_ai_in_bs,
        "external_spinorial": external_spinorial,
        "external_labels": external_labels,
        "current_labels": current_labels,
        "selected_row_indices": selected_row_indices,
        "rank_record": rank_record,
        "ai_rank": ai_rank,
    }


def build_internalization_gap_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    stage2 = ctx["stage2_status"]
    benchmark = ctx["benchmark"]
    return {
        "generated_at": ctx["generated_at"],
        "target_group": "194.1.1.1",
        "benchmark_target_result": {
            "classification": benchmark["classification"],
            "indicator_group": benchmark["indicator_group"],
            "dBS": int(benchmark["dBS"]),
            "dAI": int(benchmark["dAI"]),
        },
        "layer_table": [
            {
                "layer_name": "raw_internal_layer",
                "source_file": repo_rel(STAGE2_STATUS_JSON),
                "object_kind": "direct_source_raw_internal",
                "direct_source_computation": True,
                "bs_rank": 16,
                "ai_rank": 13,
                "quotient": stage2["double_raw_internal_quotient_group"],
                "benchmark_match": False,
                "gap_to_benchmark": "BS +6, AI +3, quotient mismatch due to the 16-dimensional raw internal BS ambient",
            },
            {
                "layer_name": "legacy_internal_reduced_13_layer",
                "source_file": repo_rel(STAGE2_STATUS_JSON),
                "object_kind": "historical_internal_reduced_layer",
                "direct_source_computation": True,
                "bs_rank": stage2["double_legacy_internal_projected_rank_bs"],
                "ai_rank": stage2["double_legacy_internal_projected_rank_ai"],
                "quotient": stage2["double_legacy_internal_projected_quotient_group"],
                "benchmark_match": False,
                "gap_to_benchmark": "The historical current-to-standard projection stays at 13/13/trivial and is retained only as provenance",
            },
            {
                "layer_name": "active_double_internalized_layer",
                "source_file": repo_rel(STAGE2_STATUS_JSON),
                "object_kind": "active_source_internalized_target_object",
                "direct_source_computation": True,
                "bs_rank": stage2["double_final_rank_bs"],
                "ai_rank": stage2["double_final_rank_ai"],
                "quotient": stage2["double_final_quotient_group"],
                "quotient_derivation_mode": stage2["double_final_quotient_derivation_mode"],
                "benchmark_match": True,
                "gap_to_benchmark": "None at BS/AI rank. Quotient is matched-target inference after exact generator-space identity rather than a direct raw-current Smith derivation.",
            },
            {
                "layer_name": "single_publication_layer",
                "source_file": repo_rel(STAGE2_STATUS_JSON),
                "object_kind": "single_inherited_publication_layer",
                "direct_source_computation": False,
                "bs_rank": stage2["single_final_rank_bs"],
                "ai_rank": stage2["single_final_rank_ai"],
                "quotient": stage2["single_final_quotient_group"],
                "quotient_derivation_mode": stage2["single_final_quotient_derivation_mode"],
                "benchmark_match": True,
                "gap_to_benchmark": "The single ordinary line is still inherited from the double internalized target object rather than directly derived as a single benchmark-layer computation.",
            },
        ],
        "active_double_internalization_evidence": {
            "current_label_order_matches_external": ctx["current_labels"] == ctx["external_labels"],
            "selected_row_count": len(ctx["selected_row_indices"]),
            "generator_count": len(ctx["external_labels"]),
            "rank_record": ctx["rank_record"],
            "patched_ai_rank": ctx["ai_rank"],
            "patched_group_rank_ai_complete": int(ctx["patched_group"]["rank(AI_complete)"]),
            "stored_patch_summary_rank_record": ctx["patch_summary"]["rank_before_after"]["new_v2"]["full"],
        },
        "direct_answers": {
            "current_internal_source_bs_true_to_10": int(stage2["double_final_rank_bs"]) == 10
            and stage2["double_status"]["published_result_source"] == "double_spinorial_internalization_v1",
            "current_internal_source_ai_true_to_10": ctx["ai_rank"] == 10
            and int(stage2["double_final_rank_ai"]) == 10,
            "current_internal_source_quotient_true_to_Z6": stage2["double_final_quotient_group"] == "Z6",
            "quotient_direct_current_lattice_derivation": bool(stage2["double_status"]["quotient_direct_current_lattice_derivation"]),
            "single_path_directly_internalized": stage2["single_status"]["published_result_source"]
            == "single_direct_internalization_v1",
        },
        "remaining_gaps": [
            "The active double target object is internalized at BS/AI = 10/10, but the final Z6 quotient is still recorded as matched-target inference rather than as a standalone raw-current lattice derivation.",
            "The single ordinary publication still inherits the target result from the internalized double path instead of exposing a direct single benchmark-layer computation.",
            "The legacy 13-dimensional reduced layer is still preserved inside stage2 outputs as historical provenance.",
        ],
    }


def build_internalization_fix_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    stage2 = ctx["stage2_status"]
    return {
        "generated_at": ctx["generated_at"],
        "baseline_commit": "3538eca483ef9592331e0538d846eb9e8d50b77a",
        "working_head_before_commit": ctx["head_commit"],
        "touched_source_files": [
            repo_rel(ROOT / "debug_workflow_portability_194.1.1.1.py"),
            repo_rel(ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"),
            repo_rel(ROOT / "debug_sg194_internalization_fix_v1.py"),
        ],
        "source_change_summary": [
            "stage2 no longer accepts direct benchmark-oracle adoption for the active double benchmark-facing object",
            "stage2 now recomputes the exact 33-channel current/external generator-space identity from the patched current candidates and the external spinorial matrix",
            "stage2 now treats the single ordinary line as inherited from the internalized double target object instead of pretending it is a direct benchmark-layer source computation",
            "stage1 raw current status is explicitly tagged as raw_internal_source_layer_only so it cannot be misread as a benchmark-layer result",
        ],
        "active_double_result": {
            "published_result_source": stage2["double_status"]["published_result_source"],
            "published_result_scope": stage2["double_status"]["published_result_scope"],
            "bs_rank": stage2["double_final_rank_bs"],
            "ai_rank": stage2["double_final_rank_ai"],
            "quotient_group": stage2["double_final_quotient_group"],
            "quotient_derivation_mode": stage2["double_final_quotient_derivation_mode"],
            "rank_record": stage2["double_internalization_rank_record"],
        },
        "single_result_status": {
            "published_result_source": stage2["single_status"]["published_result_source"],
            "published_result_scope": stage2["single_status"]["published_result_scope"],
            "remaining_internal_mapping_blocker": stage2["single_status"]["remaining_internal_mapping_blocker"],
        },
        "verdict": {
            "blind_benchmark_publication_overwrite_removed": True,
            "active_double_source_internalized": True,
            "active_single_direct_internalization_complete": False,
            "active_double_direct_raw_current_quotient_derivation_complete": False,
        },
    }


def build_adoption_vs_internalization_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    stage2 = ctx["stage2_status"]
    return {
        "generated_at": ctx["generated_at"],
        "benchmark_oracle": {
            "classification": ctx["benchmark"]["classification"],
            "indicator_group": ctx["benchmark"]["indicator_group"],
            "dBS": int(ctx["benchmark"]["dBS"]),
            "dAI": int(ctx["benchmark"]["dAI"]),
        },
        "historical_adoption_mode": HISTORICAL_ADOPTION,
        "current_stage2_mode": {
            "top_level_published_result_scope": stage2["published_result_scope"],
            "single_published_result_source": stage2["single_status"]["published_result_source"],
            "single_published_result_scope": stage2["single_status"]["published_result_scope"],
            "double_published_result_source": stage2["double_status"]["published_result_source"],
            "double_published_result_scope": stage2["double_status"]["published_result_scope"],
        },
        "difference_explainer": {
            "benchmark_adoption": "The published result simply copies benchmark oracle values into stage2 final fields without proving that an internal source object with those values exists.",
            "internalization": "An internal source object is repaired or aligned until the active source computation itself lands on the benchmark target object. In the current SG194 state this is true on the double spinorial 33-generator active path.",
        },
        "active_verdict": {
            "top_level_blind_adoption_removed": stage2["published_result_scope"]
            != HISTORICAL_ADOPTION["top_level_published_result_scope"],
            "double_source_internalized": stage2["double_status"]["published_result_source"]
            == "double_spinorial_internalization_v1",
            "single_still_inherited": stage2["single_status"]["published_result_source"]
            == "matched_benchmark_target_inherited_via_double_internalization_v1",
            "quotient_still_not_direct_raw_current_derivation": not stage2["double_status"][
                "quotient_direct_current_lattice_derivation"
            ],
        },
    }


def build_cleanup_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    tracked_deleted = [path for path in TRACKED_DELETE if not (ROOT.parent / path).exists()]
    local_deleted = [path for path in LOCAL_DELETE if not (ROOT.parent / path).exists()]
    return {
        "generated_at": ctx["generated_at"],
        "tracked_git_delete_candidates": TRACKED_DELETE,
        "tracked_git_deleted_confirmed": tracked_deleted,
        "local_cleanup_candidates": LOCAL_DELETE,
        "local_deleted_confirmed": local_deleted,
        "executed_git_rm_commands": [
            "git rm -r sg194/review_package_sg194_source_bs_fix_v1",
            "git rm sg194/review_package_sg194_source_bs_fix_v1.tar.gz",
            "git rm sg194/debug_sg194_source_bs_fix_v1.py sg194/sg194_source_bs_vs_benchmark_gap_v1.json sg194/sg194_source_bs_vs_benchmark_gap_v1.md sg194/sg194_source_bs_fix_attempt_v1.json sg194/sg194_source_bs_fix_attempt_v1.md",
        ],
        "executed_local_rm_commands": [
            "rm -rf sg194/review_package_sg194_bs_ai_separation_audit sg194/review_package_sg194_stage2_closeout_followup_v2 sg194/review_package_sg194_stage2_closeout_followup_v3",
            "rm -f sg194/workflow_portability_report_stage2_194.1.1.1.aux sg194/workflow_portability_report_stage2_194.1.1.1.log",
        ],
        "remaining_local_clutter": cleanup_findings(),
        "git_status_after": status_lines(),
        "kept_intentionally": [
            "sg194/sg194_phase_aware_l2_compatibility_v1.json",
            "sg194/sg194_phase_aware_l2_compatibility_v1.md",
            "sg194/current_status_sg194_external_matrix_final.json",
            "sg194/current_status_sg194_1941111_bs_ai_bug_audit_v1.json",
        ],
    }


def markdown_for_gap(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Internalization Gap v1",
        "",
        "## Direct Answers",
        "",
    ]
    for key, value in payload["direct_answers"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Layer Table",
            "",
        ]
    )
    for entry in payload["layer_table"]:
        lines.extend(
            [
                f"### {entry['layer_name']}",
                "",
                f"- object kind: `{entry['object_kind']}`",
                f"- source file: `{entry['source_file']}`",
                f"- direct source computation: `{entry['direct_source_computation']}`",
                f"- current value: `BS={entry['bs_rank']}, AI={entry['ai_rank']}, quotient={entry['quotient']}`",
                f"- benchmark match: `{entry['benchmark_match']}`",
                f"- gap: {entry['gap_to_benchmark']}",
                "",
            ]
        )
    lines.extend(["## Remaining Gaps", ""])
    lines.extend(f"- {item}" for item in payload["remaining_gaps"])
    return "\n".join(lines)


def markdown_for_fix(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Internalization Fix Attempt v1",
        "",
        f"- baseline commit: `{payload['baseline_commit']}`",
        f"- working head before commit: `{payload['working_head_before_commit']}`",
        "",
        "## Source Changes",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["source_change_summary"])
    lines.extend(
        [
            "",
            "## Active Double Result",
            "",
            f"- published result source: `{payload['active_double_result']['published_result_source']}`",
            f"- published result scope: `{payload['active_double_result']['published_result_scope']}`",
            f"- rank(BS/AI): `{payload['active_double_result']['bs_rank']}/{payload['active_double_result']['ai_rank']}`",
            f"- quotient: `{payload['active_double_result']['quotient_group']}`",
            f"- quotient derivation mode: `{payload['active_double_result']['quotient_derivation_mode']}`",
            "",
            "## Verdict",
            "",
        ]
    )
    for key, value in payload["verdict"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines)


def markdown_for_adoption(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Benchmark Adoption vs Internalization v1",
        "",
        "## Historical Adoption",
        "",
    ]
    for key, value in payload["historical_adoption_mode"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Current Stage2 Mode", ""])
    for key, value in payload["current_stage2_mode"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Difference",
            "",
            f"- benchmark adoption: {payload['difference_explainer']['benchmark_adoption']}",
            f"- internalization: {payload['difference_explainer']['internalization']}",
            "",
            "## Verdict",
            "",
        ]
    )
    for key, value in payload["active_verdict"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines)


def markdown_for_cleanup(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Remaining Cleanup v1",
        "",
        "## Tracked Deletions",
        "",
    ]
    lines.extend(f"- `{item}`" for item in payload["tracked_git_deleted_confirmed"])
    lines.extend(["", "## Local Cleanup", ""])
    lines.extend(f"- `{item}`" for item in payload["local_deleted_confirmed"])
    lines.extend(["", "## Remaining Local Clutter", ""])
    if payload["remaining_local_clutter"]:
        lines.extend(f"- `{item}`" for item in payload["remaining_local_clutter"])
    else:
        lines.append("- none")
    return "\n".join(lines)


def update_raw_status_file() -> None:
    payload = load_json(RAW_STATUS_JSON)
    payload["benchmark_authoritative"] = False
    payload["object_scope"] = "raw_internal_source_layer_only"
    payload["benchmark_relation"] = (
        "This stage1 workflow only emits raw/current SG194 source objects. "
        "Benchmark-facing internalization happens later in debug_workflow_portability_stage2_194.1.1.1.py."
    )
    write_json(RAW_STATUS_JSON, payload)


def update_benchmark_status(ctx: dict[str, Any]) -> None:
    payload = ctx["benchmark_status"]
    stage2 = ctx["stage2_status"]
    payload["generated_at"] = ctx["generated_at"]
    payload["benchmark_takeover_verdict"]["stage2_13_trivial_verdict"] = (
        "The older 13/13/trivial stage2 claim survives only as the historical snapshot below. "
        "The active stage2 double source path is now internalized at 10/10/Z6 through the exact double spinorial 33-generator alignment, "
        "while the single ordinary publication still inherits that target result."
    )
    payload["conflict_resolution"]["reason"] = (
        "The copied topmat magnetic benchmark remains the SG194 oracle. The current stage2 source workflow no longer uses blind publication adoption on the active double path; "
        "instead it reaches the benchmark target object through the exact double spinorial 33-generator current/external alignment. Benchmark authority still resides here."
    )
    payload["hardening_support"]["review_package_directory"] = f"sg194/{PACKAGE_NAME}"
    payload["hardening_support"]["review_package_tarball"] = f"sg194/{PACKAGE_NAME}.tar.gz"
    payload["hardening_support"]["source_bs_fix_attempt_file"] = "sg194/sg194_internalization_fix_attempt_v1.json"
    payload["hardening_support"]["source_bs_gap_file"] = "sg194/sg194_internalization_gap_v1.json"
    payload["source_workflow_alignment"] = {
        "current_stage2_status_file": "sg194/current_status_194.1.1.1_stage2.json",
        "current_stage2_summary_file": "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
        "internalization_gap_report_file": "sg194/sg194_internalization_gap_v1.json",
        "internalization_fix_attempt_file": "sg194/sg194_internalization_fix_attempt_v1.json",
        "benchmark_adoption_vs_internalization_file": "sg194/sg194_benchmark_adoption_vs_internalization_v1.json",
        "published_source_result": {
            "classification": "Z6",
            "indicator_group": "Z6",
            "dBS": 10,
            "dAI": 10,
        },
        "active_double_source_internalization": {
            "published_result_source": stage2["double_status"]["published_result_source"],
            "published_result_scope": stage2["double_status"]["published_result_scope"],
            "rank_record": stage2["double_internalization_rank_record"],
            "quotient_derivation_mode": stage2["double_final_quotient_derivation_mode"],
        },
        "single_publication_dependency": {
            "published_result_source": stage2["single_status"]["published_result_source"],
            "published_result_scope": stage2["single_status"]["published_result_scope"],
        },
        "legacy_internal_reduced_layer": {
            "single_rank_bs": 13,
            "double_rank_bs": 13,
            "single_rank_ai": 13,
            "double_rank_ai": 13,
            "single_quotient_group": "trivial",
            "double_quotient_group": "trivial",
        },
        "publication_mode": "active_double_source_internalization_with_single_inheritance",
        "remaining_blocker": (
            "The active double benchmark-target object is internalized. Remaining source follow-up is narrower: direct single ordinary identification and a standalone raw-current lattice derivation of the final Z6 quotient are still absent."
        ),
    }
    payload["which_internal_objects_are_not_benchmark"][
        "stage2_source_publication"
    ] = (
        "The current stage2 source workflow is no longer blind benchmark adoption on the active double path, but it is still not the benchmark oracle. "
        "The single ordinary publication remains inherited from the internalized double target object."
    )
    write_json(BENCHMARK_STATUS_JSON, payload)
    write_text(
        BENCHMARK_STATUS_MD,
        "\n".join(
            [
                "# SG194 Benchmark Status v1",
                "",
                "- benchmark authoritative result: `classification = Z6`, `dBS = 10`, `dAI = 10`",
                "- oracle file: `sg194/current_status_1941111_benchmark_v1.json`",
                "- active source status: the double spinorial stage2 path is internalized at `10/10/Z6`; the single ordinary publication still inherits that matched target result",
                "- active source alignment file: `sg194/sg194_internalization_fix_attempt_v1.json`",
                "- cleanup/package file: `sg194/sg194_remaining_cleanup_v1.json`",
            ]
        ),
    )


def update_object_ladder(ctx: dict[str, Any]) -> None:
    payload = load_json(OBJECT_LADDER_JSON)
    for entry in payload["entries"]:
        if entry["object_name"] == "stage2 published source status":
            entry["coordinate_language"] = "active double spinorial target-object layer plus inherited single ordinary publication"
            entry["current_value"] = "double active path 10/10/Z6 internalized; single publication inherits the same target result; legacy 13/13/trivial preserved as provenance"
            entry["relation_to_benchmark"] = (
                "The active double path now reaches the benchmark target object through exact current/external 33-generator alignment. "
                "The single ordinary publication still inherits that internalized target result rather than deriving it directly."
            )
            entry["status"] = "internalized_double_active_single_inherited"
    payload["generated_at"] = ctx["generated_at"]
    payload["verdicts"]["closest_to_benchmark_truth"] = (
        "The copied topmat magnetic benchmark remains authoritative. The active double stage2 source object now lands on the same target object through exact 33-generator alignment, while the single ordinary publication still inherits that result."
    )
    payload["verdicts"]["hardening_package"] = f"sg194/{PACKAGE_NAME}"
    payload["verdicts"]["source_publication_verdict"] = (
        "The old benchmark-adoption publication layer is gone on the active double path. Current stage2 now exposes a source-internalized double target object at 10/10/Z6, with a still-inherited single ordinary publication and a preserved historical 13-layer snapshot."
    )
    write_json(OBJECT_LADDER_JSON, payload)
    write_text(
        OBJECT_LADDER_MD,
        "\n".join(
            [
                "# SG194 Object Ladder and Benchmark Map v1",
                "",
                "- benchmark authoritative object: `sg194/current_status_1941111_benchmark_v1.json`",
                "- raw current object: `16 / 13 / Z^3` in `sg194/current_status_194.1.1.1.json`",
                "- legacy reduced layer: `13 / 13 / trivial` preserved in `sg194/current_status_194.1.1.1_stage2.json`",
                "- active double source object: `10 / 10 / Z6` via exact 33-channel double spinorial internalization",
                "- single ordinary publication: inherits the matched target result from the internalized double path",
            ]
        ),
    )


def update_inventory(ctx: dict[str, Any]) -> None:
    payload = load_json(INVENTORY_JSON)
    for item in payload["entries"]:
        if item["path"] == "sg194/current_status_194.1.1.1_stage2.json":
            item["current_value"] = "active double source internalization drives stage2 to 10/10/Z6; single publication inherits the same target result"
            item["classification"] = "internalized_double_active_layer"
            item["notes"] = "Stage2 is no longer a blind benchmark-adoption wrapper on the active double path."
        if item["path"] == "sg194/group_194_1_1_1_single_ai_completion_summary.json":
            item["notes"] = "Single-group completion summary now marks the target result as inherited from the internalized double path."
        if item["path"] == "sg194/group_194_1_1_1_double_ai_completion_summary.json":
            item["notes"] = "Double-group completion summary now reflects the active double spinorial internalization path."
    payload["generated_at"] = ctx["generated_at"]
    write_json(INVENTORY_JSON, payload)
    write_text(
        INVENTORY_MD,
        "\n".join(
            [
                "# SG194 Authoritative File Inventory v1",
                "",
                "- benchmark oracle remains `sg194/current_status_1941111_benchmark_v1.json`",
                "- `sg194/current_status_194.1.1.1_stage2.json` is now an internalized-double active source status, not a blind benchmark-adoption wrapper",
                "- single/double completion summaries are benchmark-facing but non-authoritative source artifacts",
                "- raw current and phase-aware files remain internal / prototype only",
            ]
        ),
    )


def update_readme_and_checkpoint(ctx: dict[str, Any], cleanup_payload: dict[str, Any]) -> None:
    write_text(
        README_MD,
        "\n".join(
            [
                "# SG194 Internalization Fix",
                "",
                "## Benchmark-first entrypoint",
                "",
                "- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`",
                "- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`",
                "- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`",
                "- second independent verifier: `sg194_topmat_independent_verify_v1.json`",
                "",
                "## Active source workflow status",
                "",
                "- active double source object: exact 33-channel double spinorial internalization at `10 / 10 / Z6`",
                "- single ordinary publication: inherits the matched target result from the internalized double path",
                "- raw current layer remains `16 / 13 / Z^3`; historical reduced layer remains `13 / 13 / trivial` as provenance only",
                "- internalization gap report: `sg194_internalization_gap_v1.json`",
                "- internalization fix report: `sg194_internalization_fix_attempt_v1.json`",
                "",
                "## Review package",
                "",
                f"- package file: `{PACKAGE_TARBALL.name}`",
                f"- package directory: `{PACKAGE_NAME}/`",
                f"- package map: `{PACKAGE_NAME}/REVIEW_MAP.md`",
                "- package layers: benchmark authoritative, internalization, cleanup, source code",
                "",
                "## Cleanup",
                "",
                f"- tracked/local cleanup report: `{REMAINING_CLEANUP_JSON.name}`",
                f"- remaining local clutter count after cleanup: `{len(cleanup_payload['remaining_local_clutter'])}`",
            ]
        ),
    )
    checkpoint_payload = load_json(LIVE_CHECKPOINT_JSON)
    checkpoint_payload["checkpoint_scope"] = "sg194_internalization_fix_v1"
    checkpoint_payload["active_double_source_internalization"] = {
        "rank_bs": 10,
        "rank_ai": 10,
        "quotient_group": "Z6",
        "quotient_derivation_mode": ctx["stage2_status"]["double_final_quotient_derivation_mode"],
    }
    checkpoint_payload["single_publication_dependency"] = {
        "published_result_source": ctx["stage2_status"]["single_status"]["published_result_source"],
        "remaining_internal_mapping_blocker": ctx["stage2_status"]["single_status"]["remaining_internal_mapping_blocker"],
    }
    checkpoint_payload["cleanup_this_round"] = {
        "tracked_deleted_count": len(cleanup_payload["tracked_git_deleted_confirmed"]),
        "local_deleted_count": len(cleanup_payload["local_deleted_confirmed"]),
    }
    write_json(LIVE_CHECKPOINT_JSON, checkpoint_payload)
    write_text(
        LIVE_CHECKPOINT_MD,
        "\n".join(
            [
                "# Live Checkpoint",
                "",
                "- active double source object: internalized at `10 / 10 / Z6` through exact 33-channel double spinorial alignment",
                "- single ordinary publication: inherited from the internalized double path",
                "- remaining follow-up: direct single ordinary benchmark-layer identification and standalone raw-current quotient derivation",
                f"- cleanup report: `{REMAINING_CLEANUP_JSON.name}`",
            ]
        ),
    )


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dest_root: Path, rel: str) -> None:
    dest = dest_root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def build_package(ctx: dict[str, Any]) -> None:
    ensure_clean_dir(PACKAGE_DIR)
    benchmark_files = [
        BENCHMARK_STATUS_JSON,
        BENCHMARK_STATUS_MD,
        BENCHMARK_VERDICT_JSON,
        BENCHMARK_VERDICT_MD,
        BENCHMARK_VERIFY_JSON,
        BENCHMARK_VERIFY_MD,
    ]
    internalization_files = [
        INTERNALIZATION_GAP_JSON,
        INTERNALIZATION_GAP_MD,
        INTERNALIZATION_FIX_JSON,
        INTERNALIZATION_FIX_MD,
        ADOPTION_VS_INTERNALIZATION_JSON,
        ADOPTION_VS_INTERNALIZATION_MD,
        STAGE2_STATUS_JSON,
        STAGE2_SUMMARY_JSON,
        SINGLE_COMPLETION_JSON,
        DOUBLE_COMPLETION_JSON,
    ]
    cleanup_files = [
        REMAINING_CLEANUP_JSON,
        REMAINING_CLEANUP_MD,
    ]
    source_files = [
        ROOT / "debug_workflow_portability_194.1.1.1.py",
        ROOT / "debug_workflow_portability_stage2_194.1.1.1.py",
        ROOT / "debug_sg194_internalization_fix_v1.py",
    ]
    for src in benchmark_files:
        copy_file(src, PACKAGE_DIR, f"benchmark_authoritative/{src.name}")
    for src in internalization_files:
        copy_file(src, PACKAGE_DIR, f"internalization/{src.name}")
    for src in cleanup_files:
        copy_file(src, PACKAGE_DIR, f"cleanup/{src.name}")
    for src in source_files:
        copy_file(src, PACKAGE_DIR, f"source_code/{src.name}")
    write_text(
        PACKAGE_README_MD,
        "\n".join(
            [
                "# SG194 Internalization Fix Review Package",
                "",
                "- benchmark layer: authoritative `Z6`, `dBS = 10`, `dAI = 10`",
                "- internalization layer: active double source object internalized to the benchmark target; single ordinary publication still inherited",
                "- cleanup layer: tracked/local deletions executed this round",
                "- source code layer: the exact scripts used for the internalization transition",
            ]
        ),
    )
    write_text(
        REVIEW_MAP_MD,
        "\n".join(
            [
                "# Review Map",
                "",
                "## benchmark_authoritative",
                "- current_status_1941111_benchmark_v1.json/md",
                "- sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json/md",
                "- sg194_topmat_independent_verify_v1.json/md",
                "",
                "## internalization",
                "- sg194_internalization_gap_v1.json/md",
                "- sg194_internalization_fix_attempt_v1.json/md",
                "- sg194_benchmark_adoption_vs_internalization_v1.json/md",
                "- current_status_194.1.1.1_stage2.json",
                "- workflow_portability_stage2_summary_194.1.1.1.json",
                "- group_194_1_1_1_single_ai_completion_summary.json",
                "- group_194_1_1_1_double_ai_completion_summary.json",
                "",
                "## cleanup",
                "- sg194_remaining_cleanup_v1.json/md",
                "",
                "## source_code",
                "- debug_workflow_portability_194.1.1.1.py",
                "- debug_workflow_portability_stage2_194.1.1.1.py",
                "- debug_sg194_internalization_fix_v1.py",
            ]
        ),
    )
    manifest_payload = {
        "generated_at": ctx["generated_at"],
        "head_commit_before_commit": ctx["head_commit"],
        "package_name": PACKAGE_NAME,
        "creation_command": "python3 sg194/debug_sg194_internalization_fix_v1.py",
        "file_inventory": sorted(
            repo_rel(path) for path in PACKAGE_DIR.rglob("*") if path.is_file()
        ),
    }
    write_json(PACKAGE_MANIFEST_JSON, manifest_payload)
    write_text(
        PACKAGE_MANIFEST_MD,
        "\n".join(
            [
                "# Reproducibility Manifest",
                "",
                f"- generated at: `{ctx['generated_at']}`",
                f"- head before commit: `{ctx['head_commit']}`",
                "- creation command: `python3 sg194/debug_sg194_internalization_fix_v1.py`",
            ]
        ),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate(ctx: dict[str, Any]) -> None:
    stage2 = ctx["stage2_status"]
    assert ctx["current_labels"] == ctx["external_labels"]
    assert ctx["rank_record"] == {
        "current_rank": 10,
        "external_rank": 10,
        "union_rank": 10,
        "intersection_rank": 10,
        "current_only_dimension": 0,
        "external_only_dimension": 0,
    }
    assert ctx["ai_rank"] == 10
    assert stage2["published_result_scope"] != HISTORICAL_ADOPTION["top_level_published_result_scope"]
    assert stage2["double_status"]["published_result_source"] == "double_spinorial_internalization_v1"
    assert stage2["single_status"]["published_result_source"] == "matched_benchmark_target_inherited_via_double_internalization_v1"
    assert stage2["double_final_rank_bs"] == 10
    assert stage2["double_final_rank_ai"] == 10
    assert stage2["double_final_quotient_group"] == "Z6"
    assert BENCHMARK_STATUS_JSON.exists()
    assert INTERNALIZATION_GAP_JSON.exists()
    assert INTERNALIZATION_FIX_JSON.exists()
    assert ADOPTION_VS_INTERNALIZATION_JSON.exists()
    assert REMAINING_CLEANUP_JSON.exists()
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()
    assert PACKAGE_MANIFEST_MD.exists()
    assert PACKAGE_MANIFEST_JSON.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    ctx = build_context()
    if args.validate:
        validate(ctx)
        print("validated sg194 internalization fix outputs")
        return

    gap_payload = build_internalization_gap_payload(ctx)
    fix_payload = build_internalization_fix_payload(ctx)
    adoption_payload = build_adoption_vs_internalization_payload(ctx)
    cleanup_payload = build_cleanup_payload(ctx)

    write_json(INTERNALIZATION_GAP_JSON, gap_payload)
    write_text(INTERNALIZATION_GAP_MD, markdown_for_gap(gap_payload))
    write_json(INTERNALIZATION_FIX_JSON, fix_payload)
    write_text(INTERNALIZATION_FIX_MD, markdown_for_fix(fix_payload))
    write_json(ADOPTION_VS_INTERNALIZATION_JSON, adoption_payload)
    write_text(ADOPTION_VS_INTERNALIZATION_MD, markdown_for_adoption(adoption_payload))
    write_json(REMAINING_CLEANUP_JSON, cleanup_payload)
    write_text(REMAINING_CLEANUP_MD, markdown_for_cleanup(cleanup_payload))

    update_raw_status_file()
    update_benchmark_status(ctx)
    update_object_ladder(ctx)
    update_inventory(ctx)
    update_readme_and_checkpoint(ctx, cleanup_payload)
    build_package(ctx)
    print("generated sg194 internalization fix artifacts")


if __name__ == "__main__":
    main()
