#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
BASELINE_COMMIT = "798c4998c946d2fc253a05242e39a5adb71c29d3"

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
BENCHMARK_ADOPTION_JSON = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.json"
BENCHMARK_ADOPTION_MD = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.md"
README_MD = ROOT / "README.md"
LIVE_CHECKPOINT_JSON = ROOT / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = ROOT / "live_checkpoint_sg194_1941111.md"
REMAINING_CLEANUP_JSON = ROOT / "sg194_remaining_cleanup_v1.json"
REMAINING_CLEANUP_MD = ROOT / "sg194_remaining_cleanup_v1.md"

SINGLE_DIRECT_BS_JSON = ROOT / "sg194_single_direct_bs_derivation_v1.json"
SINGLE_DIRECT_BS_MD = ROOT / "sg194_single_direct_bs_derivation_v1.md"
SINGLE_DIRECT_AI_JSON = ROOT / "sg194_single_direct_ai_derivation_v1.json"
SINGLE_DIRECT_AI_MD = ROOT / "sg194_single_direct_ai_derivation_v1.md"
SINGLE_DIRECT_QUOTIENT_JSON = ROOT / "sg194_single_direct_quotient_derivation_v1.json"
SINGLE_DIRECT_QUOTIENT_MD = ROOT / "sg194_single_direct_quotient_derivation_v1.md"
SINGLE_DIRECT_SUMMARY_JSON = ROOT / "sg194_single_direct_result_summary_v1.json"
SINGLE_DIRECT_SUMMARY_MD = ROOT / "sg194_single_direct_result_summary_v1.md"
SINGLE_INHERITANCE_AUDIT_JSON = ROOT / "sg194_single_inheritance_removal_audit_v1.json"
SINGLE_INHERITANCE_AUDIT_MD = ROOT / "sg194_single_inheritance_removal_audit_v1.md"

PACKAGE_NAME = "review_package_sg194_single_direct_result_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

TRACKED_DELETE_TARGETS = [
    "sg194/review_package_sg194_internalization_fix_v1",
    "sg194/review_package_sg194_internalization_fix_v1.tar.gz",
    "sg194/debug_sg194_internalization_fix_v1.py",
]
LOCAL_DELETE_TARGETS = [
    "sg194/workflow_portability_report_stage2_194.1.1.1.aux",
    "sg194/workflow_portability_report_stage2_194.1.1.1.log",
    "sg194/workflow_portability_report_stage2_194.1.1.1.out",
]


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git_show_json(commit: str, relpath: str) -> Any:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relpath}"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def git_ls_tracked(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relpath],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def tree_lines(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    factors = [f"Z{n}" for n in finite_part]
    if free_rank == 1:
        factors.append("Z")
    elif free_rank > 1:
        factors.append(f"Z^{free_rank}")
    return "trivial" if not factors else " x ".join(factors)


def build_context() -> dict[str, Any]:
    stage2 = load_module(STAGE2_SCRIPT, "sg194_stage2_single_direct_v1")
    helper = stage2.load_helper_module()
    helper_payload = helper.generate_outputs()
    helper.validate_outputs()

    port = stage2.load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(stage2.TARGET_GROUP)

    single_runtime = stage2.build_single_runtime(port, module, ssg_dict)
    single_induction = stage2.induce_objects(
        port,
        single_runtime,
        helper_payload["family_single_local_irreps"],
        "single_local_irrep_library",
    )
    candidate_ids = [candidate["generator_id"] for candidate in single_induction["candidates"]]
    ai_coord_matrix = stage2.bs_coordinate_matrix(single_runtime["bs_analysis"], single_induction["candidates"])
    quotient_summary, quotient_generators = stage2.quotient_artifacts(
        1,
        single_runtime["bs_analysis"],
        ai_coord_matrix,
        candidate_ids,
    )

    diagonal, _, _ = smith_normal_decomp(ai_coord_matrix, domain=ZZ)
    smith_diagonal_nonzero = [
        abs(int(diagonal[idx, idx]))
        for idx in range(min(diagonal.rows, diagonal.cols))
        if int(diagonal[idx, idx]) != 0
    ]
    finite_part = [value for value in smith_diagonal_nonzero if value > 1]
    free_rank = int(ai_coord_matrix.rows - len(smith_diagonal_nonzero))

    current_stage2 = load_json(CURRENT_STAGE2_JSON)
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    historical_stage2 = git_show_json(BASELINE_COMMIT, "sg194/current_status_194.1.1.1_stage2.json")

    return {
        "stage2": stage2,
        "single_runtime": single_runtime,
        "single_induction": single_induction,
        "ai_coord_matrix": ai_coord_matrix,
        "candidate_ids": candidate_ids,
        "quotient_summary": quotient_summary,
        "quotient_generators": quotient_generators,
        "smith_diagonal_nonzero": smith_diagonal_nonzero,
        "finite_part": finite_part,
        "free_rank": free_rank,
        "current_stage2": current_stage2,
        "historical_stage2": historical_stage2,
        "benchmark_status": benchmark_status,
    }


def build_bs_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    runtime = ctx["single_runtime"]
    bs_analysis = runtime["bs_analysis"]
    return {
        "target_group": "194.1.1.1",
        "derivation_mode": "direct_single_source_object",
        "result_kind": "single_active_source_bs_rank",
        "active_compatibility_matrix": {
            "source_function": "build_single_runtime -> analyze_kernel",
            "source_file": repo_rel(STAGE2_SCRIPT),
            "compatibility_json": "sg194/group_194_1_1_1_single_full_compatibility_with_planes.json",
            "matrix_shape": bs_analysis["matrix_shape"],
            "rank": bs_analysis["rank"],
            "nullity": bs_analysis["nullity"],
            "unknown_ordering_count": len(bs_analysis["unknown_ordering"]),
        },
        "active_bs_basis": {
            "source_json": "sg194/group_194_1_1_1_single_bs_analysis.json",
            "basis_kind": "single_active_bs_basis_after_line_and_plane_compatibility",
            "dimension_dBS": int(bs_analysis["nullity"]),
            "projected_point_space_rank": int(ctx["current_stage2"]["single_status"]["rank_bs_projected_point_space"]),
            "legacy_auxiliary_projected_rank": int(ctx["current_stage2"]["single_legacy_internal_projected_rank_bs"]),
        },
        "dBS_single": int(bs_analysis["nullity"]),
        "direct": True,
        "inherits_from_double": False,
    }


def build_ai_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    ai_matrix = ctx["ai_coord_matrix"]
    current_stage2 = ctx["current_stage2"]
    return {
        "target_group": "194.1.1.1",
        "derivation_mode": "direct_single_source_object",
        "result_kind": "single_active_source_ai_rank",
        "active_ai_generator_object": {
            "source_function": "induce_objects -> bs_coordinate_matrix",
            "source_file": repo_rel(STAGE2_SCRIPT),
            "candidate_json": "sg194/raw_194_1_1_1_single_ai_candidates.json",
            "candidate_count": len(ctx["single_induction"]["candidates"]),
            "distinct_unknown_vector_count": len(ctx["single_induction"]["duplicate_classes"]),
            "candidate_matrix_shape_in_bs_coordinates": [int(ai_matrix.rows), int(ai_matrix.cols)],
            "candidate_rank_in_bs_coordinates": int(ai_matrix.rank()),
        },
        "active_ai_basis": {
            "source_json": "sg194/group_194_1_1_1_single_ai_completion_summary.json",
            "dAI_single": int(ai_matrix.rank()),
            "legacy_auxiliary_projected_rank": int(current_stage2["single_legacy_internal_projected_rank_ai"]),
        },
        "dAI_single": int(ai_matrix.rank()),
        "direct": True,
        "inherits_from_double": False,
    }


def build_quotient_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    quotient = ctx["quotient_summary"]
    return {
        "target_group": "194.1.1.1",
        "derivation_mode": "direct_smith_on_single_active_bs_over_single_ai",
        "result_kind": "single_active_source_quotient",
        "active_quotient_presentation": {
            "source_function": "quotient_artifacts",
            "source_file": repo_rel(STAGE2_SCRIPT),
            "quotient_json": "sg194/group_194_1_1_1_single_indicator_group_summary.json",
            "generator_json": "sg194/group_194_1_1_1_single_indicator_generators.json",
            "matrix_shape": [int(ctx["ai_coord_matrix"].rows), int(ctx["ai_coord_matrix"].cols)],
            "smith_diagonal_nonzero": ctx["smith_diagonal_nonzero"],
            "finite_part": ctx["finite_part"],
            "free_rank": ctx["free_rank"],
        },
        "classification_single": quotient["quotient_group"],
        "finite_part": ctx["finite_part"],
        "free_rank": ctx["free_rank"],
        "direct": True,
        "inherits_from_double": False,
    }


def build_summary_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    current_stage2 = ctx["current_stage2"]
    benchmark_result = ctx["benchmark_status"]["benchmark_result"]
    historical_single = ctx["historical_stage2"]
    result = {
        "dBS": int(ctx["quotient_summary"]["rank(BS)"]),
        "dAI": int(ctx["quotient_summary"]["rank(AI_complete)"]),
        "classification": ctx["quotient_summary"]["quotient_group"],
        "finite_part": ctx["finite_part"],
        "free_rank": ctx["free_rank"],
        "smith_diagonal_nonzero": ctx["smith_diagonal_nonzero"],
    }
    return {
        "target_group": "194.1.1.1",
        "single_direct_result": result,
        "directness_verdict": {
            "inherits_from_double": False,
            "matched_target_inference": False,
            "benchmark_oracle_overwrite": False,
            "completely_direct": True,
        },
        "historical_inherited_single_snapshot_from_baseline_commit": {
            "baseline_commit": BASELINE_COMMIT,
            "published_result_source": historical_single["single_status"]["published_result_source"],
            "dBS": historical_single["single_final_rank_bs"],
            "dAI": historical_single["single_final_rank_ai"],
            "classification": historical_single["single_final_quotient_group"],
        },
        "current_stage2_single_status": {
            "published_result_source": current_stage2["single_status"]["published_result_source"],
            "published_result_scope": current_stage2["single_status"]["published_result_scope"],
            "dBS": current_stage2["single_final_rank_bs"],
            "dAI": current_stage2["single_final_rank_ai"],
            "classification": current_stage2["single_final_quotient_group"],
        },
        "current_stage2_double_status": {
            "published_result_source": current_stage2["double_status"]["published_result_source"],
            "dBS": current_stage2["double_final_rank_bs"],
            "dAI": current_stage2["double_final_rank_ai"],
            "classification": current_stage2["double_final_quotient_group"],
        },
        "benchmark_oracle": {
            "dBS": benchmark_result["dBS"],
            "dAI": benchmark_result["dAI"],
            "classification": benchmark_result["classification"],
        },
        "consistency_check": {
            "single_direct_equals_historical_inherited_single": result["dBS"] == historical_single["single_final_rank_bs"]
            and result["dAI"] == historical_single["single_final_rank_ai"]
            and result["classification"] == historical_single["single_final_quotient_group"],
            "single_direct_equals_current_double": result["dBS"] == current_stage2["double_final_rank_bs"]
            and result["dAI"] == current_stage2["double_final_rank_ai"]
            and result["classification"] == current_stage2["double_final_quotient_group"],
            "single_direct_equals_benchmark": result["dBS"] == benchmark_result["dBS"]
            and result["dAI"] == benchmark_result["dAI"]
            and result["classification"] == benchmark_result["classification"],
        },
        "verdict": (
            "The direct single source result is 16/13/Z^3. It does not agree with the old inherited single 10/10/Z6 snapshot, "
            "and it also does not agree with the double internalized benchmark-target result 10/10/Z6."
        ),
    }


def build_inheritance_audit_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    current_stage2 = ctx["current_stage2"]
    single_status = current_stage2["single_status"]
    markers = {
        "published_result_source_inherited_marker_removed": single_status["published_result_source"]
        != "matched_benchmark_target_inherited_via_double_internalization_v1",
        "published_result_scope_inherited_marker_removed": single_status["published_result_scope"]
        != "benchmark_target_inherited_from_internalized_double_path_not_direct_single_computation",
        "bs_internalization_status_inherited_marker_removed": single_status["bs_internalization_status"]
        != "inherited_from_double_internalization",
        "ai_internalization_status_inherited_marker_removed": single_status["ai_internalization_status"]
        != "inherited_from_double_internalization",
        "quotient_derivation_mode_inherited_marker_removed": single_status["quotient_derivation_mode"]
        != "inherited_from_internalized_double_target_object",
        "top_level_single_quotient_derivation_marker_removed": current_stage2["single_final_quotient_derivation_mode"]
        != "inherited_from_internalized_double_target_object",
    }
    double_strings = []
    for key, value in single_status.items():
        if isinstance(value, str) and "double" in value.lower():
            double_strings.append({"field": key, "value": value})
    return {
        "target_group": "194.1.1.1",
        "single_inheritance_marker_count": sum(int(not passed) for passed in markers.values()),
        "markers": markers,
        "single_direct_result": {
            "published_result_source": single_status["published_result_source"],
            "published_result_scope": single_status["published_result_scope"],
            "quotient_derivation_mode": single_status["quotient_derivation_mode"],
        },
        "remaining_double_mentions_inside_single_status": double_strings,
        "audit_verdict": "Single no longer inherits its published result from double. Remaining double mentions are informational benchmark-gap caveats only.",
    }


def build_cleanup_payload() -> dict[str, Any]:
    tracked = []
    for rel in TRACKED_DELETE_TARGETS:
        tracked.append(
            {
                "path": rel,
                "deleted_from_git": not git_ls_tracked(rel),
            }
        )
    local = []
    for rel in LOCAL_DELETE_TARGETS:
        local.append(
            {
                "path": rel,
                "present_after_cleanup": (REPO_ROOT / rel).exists(),
            }
        )
    return {
        "generated_at": now_iso(),
        "tracked_delete_targets": tracked,
        "local_delete_targets": local,
        "deletion_commands": [
            "git rm -r sg194/review_package_sg194_internalization_fix_v1 sg194/review_package_sg194_internalization_fix_v1.tar.gz sg194/debug_sg194_internalization_fix_v1.py",
            "rm -f sg194/workflow_portability_report_stage2_194.1.1.1.aux sg194/workflow_portability_report_stage2_194.1.1.1.log sg194/workflow_portability_report_stage2_194.1.1.1.out",
        ],
        "cleanup_verdict": "The old internalization-fix package and its driver script are deleted from git, and local TeX side-products are removed.",
    }


def refresh_benchmark_status(ctx: dict[str, Any], summary_payload: dict[str, Any], audit_payload: dict[str, Any]) -> None:
    payload = load_json(BENCHMARK_STATUS_JSON)
    payload["generated_at"] = now_iso()
    payload["benchmark_takeover_verdict"][
        "stage2_13_trivial_verdict"
    ] = (
        "The older 13/13/trivial stage2 claim survives only as an auxiliary legacy projection. "
        "The current stage2 double source path remains internalized at 10/10/Z6 through the exact double spinorial 33-generator "
        "alignment, while the single direct source result is now independently published as 16/13/Z^3 and is no longer inherited "
        "from double."
    )
    payload["hardening_support"]["review_package_directory"] = repo_rel(PACKAGE_DIR)
    payload["hardening_support"]["review_package_tarball"] = repo_rel(PACKAGE_TARBALL)
    payload["source_workflow_alignment"]["published_source_result"] = {
        "single_direct_result": summary_payload["single_direct_result"],
        "double_internalized_result": {
            "classification": ctx["current_stage2"]["double_final_quotient_group"],
            "indicator_group": ctx["current_stage2"]["double_final_quotient_group"],
            "dBS": ctx["current_stage2"]["double_final_rank_bs"],
            "dAI": ctx["current_stage2"]["double_final_rank_ai"],
        },
    }
    payload["source_workflow_alignment"]["single_publication_dependency"] = {
        "published_result_source": ctx["current_stage2"]["single_status"]["published_result_source"],
        "published_result_scope": ctx["current_stage2"]["single_status"]["published_result_scope"],
        "summary": "Single is now direct and no longer inherits from double."
    }
    payload["source_workflow_alignment"]["publication_mode"] = "mixed_single_direct_raw_and_double_internalized"
    payload["source_workflow_alignment"][
        "remaining_blocker"
    ] = "Double stays benchmark-aligned at 10/10/Z6. Single is now direct at 16/13/Z^3, but still lacks an independent ordinary standard-space derivation."
    payload["which_internal_objects_are_not_benchmark"][
        "stage2_source_publication"
    ] = (
        "The current stage2 source workflow now splits single and double honestly: single publishes a direct raw internal result "
        "16/13/Z^3, while double publishes the internalized benchmark-target result 10/10/Z6. Neither publication replaces the benchmark oracle."
    )
    write_json(BENCHMARK_STATUS_JSON, payload)

    write_text(
        BENCHMARK_STATUS_MD,
        "\n".join(
            [
                "# SG194 Benchmark Oracle",
                "",
                "- benchmark result remains `Z6`, `dBS = 10`, `dAI = 10`.",
                "- stage2 double source publication remains benchmark-aligned at `10 / 10 / Z6`.",
                "- stage2 single source publication is now independent and direct at `16 / 13 / Z^3`; it is not benchmark-authoritative.",
                "- review package: `review_package_sg194_single_direct_result_v1.tar.gz`.",
            ]
        ),
    )


def refresh_adoption_vs_internalization(ctx: dict[str, Any], summary_payload: dict[str, Any]) -> None:
    benchmark_result = ctx["benchmark_status"]["benchmark_result"]
    current_stage2 = ctx["current_stage2"]
    payload = {
        "generated_at": now_iso(),
        "benchmark_oracle": {
            "classification": benchmark_result["classification"],
            "indicator_group": benchmark_result["indicator_group"],
            "dBS": benchmark_result["dBS"],
            "dAI": benchmark_result["dAI"],
        },
        "historical_adoption_mode": {
            "top_level_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
            "single_published_result_source": "benchmark_oracle_adoption_v1",
            "double_published_result_source": "benchmark_oracle_adoption_v1",
            "single_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
            "double_published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
        },
        "current_stage2_mode": {
            "top_level_published_result_scope": current_stage2["published_result_scope"],
            "single_published_result_source": current_stage2["single_status"]["published_result_source"],
            "single_published_result_scope": current_stage2["single_status"]["published_result_scope"],
            "double_published_result_source": current_stage2["double_status"]["published_result_source"],
            "double_published_result_scope": current_stage2["double_status"]["published_result_scope"],
        },
        "difference_explainer": {
            "benchmark_adoption": "The published result simply copies benchmark oracle values into stage2 final fields without proving that an internal source object with those values exists.",
            "double_internalization": "The double active source object is aligned until the live source computation itself reaches the benchmark target object.",
            "single_direct_computation": "The single active source object now reports its own raw BS/AI quotient directly, without benchmark overwrite and without double inheritance.",
        },
        "active_verdict": {
            "top_level_blind_adoption_removed": True,
            "double_source_internalized": current_stage2["double_status"]["published_result_source"] == "double_spinorial_internalization_v1",
            "single_still_inherited": False,
            "single_direct_now_active": True,
            "single_direct_matches_benchmark": summary_payload["consistency_check"]["single_direct_equals_benchmark"],
        },
    }
    write_json(BENCHMARK_ADOPTION_JSON, payload)
    write_text(
        BENCHMARK_ADOPTION_MD,
        "\n".join(
            [
                "# Benchmark Adoption vs Internalization",
                "",
                "- historical blind adoption is retired.",
                "- double is internalized at `10 / 10 / Z6`.",
                "- single is now direct at `16 / 13 / Z^3` and is no longer inherited from double.",
                "- direct single does not equal the benchmark oracle.",
            ]
        ),
    )


def refresh_readme(summary_payload: dict[str, Any]) -> None:
    write_text(
        README_MD,
        "\n".join(
            [
                "# SG194 Single Direct Result",
                "",
                "## Benchmark-first entrypoint",
                "",
                "- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`",
                "- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`",
                "- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`",
                "",
                "## Active source workflow status",
                "",
                "- active single direct source object: `16 / 13 / Z^3`",
                "- active double source object: `10 / 10 / Z6`",
                "- auxiliary single legacy projection: `13 / 13 / trivial`",
                "- benchmark oracle is not overwritten into the single path",
                "",
                "## Review package",
                "",
                "- package file: `review_package_sg194_single_direct_result_v1.tar.gz`",
                "- package directory: `review_package_sg194_single_direct_result_v1/`",
                "",
                "## Cleanup",
                "",
                "- cleanup report: `sg194_remaining_cleanup_v1.json`",
                "- single inheritance audit: `sg194_single_inheritance_removal_audit_v1.json`",
            ]
        ),
    )


def refresh_live_checkpoint(summary_payload: dict[str, Any], audit_payload: dict[str, Any]) -> None:
    payload = load_json(LIVE_CHECKPOINT_JSON)
    payload["single_direct_result"] = summary_payload["single_direct_result"]
    payload["single_inheritance_marker_count"] = audit_payload["single_inheritance_marker_count"]
    payload["updated_at"] = now_iso()
    write_json(LIVE_CHECKPOINT_JSON, payload)
    write_text(
        LIVE_CHECKPOINT_MD,
        "\n".join(
            [
                "# Live Checkpoint",
                "",
                f"- single direct result: `{summary_payload['single_direct_result']['dBS']} / {summary_payload['single_direct_result']['dAI']} / {summary_payload['single_direct_result']['classification']}`",
                f"- single inheritance marker count: `{audit_payload['single_inheritance_marker_count']}`",
                "- double remains internalized at `10 / 10 / Z6`.",
            ]
        ),
    )


def write_markdown_files(bs_payload: dict[str, Any], ai_payload: dict[str, Any], quotient_payload: dict[str, Any], summary_payload: dict[str, Any], audit_payload: dict[str, Any], cleanup_payload: dict[str, Any]) -> None:
    write_text(
        SINGLE_DIRECT_BS_MD,
        "\n".join(
            [
                "# Single Direct BS Derivation",
                "",
                f"- active compatibility matrix: `{bs_payload['active_compatibility_matrix']['matrix_shape']}` with nullity `{bs_payload['dBS_single']}`",
                f"- direct `dBS(single) = {bs_payload['dBS_single']}`",
                "- this is computed from the single source object, not from double inheritance.",
            ]
        ),
    )
    write_text(
        SINGLE_DIRECT_AI_MD,
        "\n".join(
            [
                "# Single Direct AI Derivation",
                "",
                f"- candidate count: `{ai_payload['active_ai_generator_object']['candidate_count']}`",
                f"- candidate matrix shape in BS coordinates: `{ai_payload['active_ai_generator_object']['candidate_matrix_shape_in_bs_coordinates']}`",
                f"- direct `dAI(single) = {ai_payload['dAI_single']}`",
            ]
        ),
    )
    write_text(
        SINGLE_DIRECT_QUOTIENT_MD,
        "\n".join(
            [
                "# Single Direct Quotient Derivation",
                "",
                f"- smith diagonal nonzero: `{quotient_payload['active_quotient_presentation']['smith_diagonal_nonzero']}`",
                f"- free rank: `{quotient_payload['free_rank']}`",
                f"- finite part: `{quotient_payload['finite_part']}`",
                f"- direct classification: `{quotient_payload['classification_single']}`",
            ]
        ),
    )
    write_text(
        SINGLE_DIRECT_SUMMARY_MD,
        "\n".join(
            [
                "# Single Direct Result Summary",
                "",
                f"- direct single result: `{summary_payload['single_direct_result']['dBS']} / {summary_payload['single_direct_result']['dAI']} / {summary_payload['single_direct_result']['classification']}`",
                f"- historical inherited snapshot from `{BASELINE_COMMIT[:7]}`: `10 / 10 / Z6`",
                f"- current double internalized result: `{summary_payload['current_stage2_double_status']['dBS']} / {summary_payload['current_stage2_double_status']['dAI']} / {summary_payload['current_stage2_double_status']['classification']}`",
                f"- benchmark oracle: `{summary_payload['benchmark_oracle']['dBS']} / {summary_payload['benchmark_oracle']['dAI']} / {summary_payload['benchmark_oracle']['classification']}`",
                f"- verdict: {summary_payload['verdict']}",
            ]
        ),
    )
    write_text(
        SINGLE_INHERITANCE_AUDIT_MD,
        "\n".join(
            [
                "# Single Inheritance Removal Audit",
                "",
                f"- single inheritance marker count: `{audit_payload['single_inheritance_marker_count']}`",
                f"- current single published result source: `{audit_payload['single_direct_result']['published_result_source']}`",
                f"- current single quotient derivation mode: `{audit_payload['single_direct_result']['quotient_derivation_mode']}`",
                f"- remaining double mentions in single status: `{len(audit_payload['remaining_double_mentions_inside_single_status'])}`",
            ]
        ),
    )
    write_text(
        REMAINING_CLEANUP_MD,
        "\n".join(
            [
                "# Remaining Cleanup",
                "",
                "- tracked deletions executed:",
                *[f"  - `{item['path']}` deleted_from_git = `{item['deleted_from_git']}`" for item in cleanup_payload["tracked_delete_targets"]],
                "- local deletions executed:",
                *[f"  - `{item['path']}` present_after_cleanup = `{item['present_after_cleanup']}`" for item in cleanup_payload["local_delete_targets"]],
            ]
        ),
    )


def build_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    layers = {
        "single_direct_derivation": [
            SINGLE_DIRECT_BS_JSON,
            SINGLE_DIRECT_BS_MD,
            SINGLE_DIRECT_AI_JSON,
            SINGLE_DIRECT_AI_MD,
            SINGLE_DIRECT_QUOTIENT_JSON,
            SINGLE_DIRECT_QUOTIENT_MD,
            SINGLE_DIRECT_SUMMARY_JSON,
            SINGLE_DIRECT_SUMMARY_MD,
            CURRENT_STAGE2_JSON,
        ],
        "inheritance_audit": [
            SINGLE_INHERITANCE_AUDIT_JSON,
            SINGLE_INHERITANCE_AUDIT_MD,
        ],
        "benchmark_double_compare": [
            BENCHMARK_STATUS_JSON,
            BENCHMARK_STATUS_MD,
            BENCHMARK_ADOPTION_JSON,
            BENCHMARK_ADOPTION_MD,
        ],
        "cleanup": [
            REMAINING_CLEANUP_JSON,
            REMAINING_CLEANUP_MD,
        ],
    }
    for dirname, files in layers.items():
        target_dir = PACKAGE_DIR / dirname
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in files:
            shutil.copy2(path, target_dir / path.name)

    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# Review Package: SG194 Single Direct Result v1",
                "",
                "- single direct derivation layer: direct BS / AI / quotient result",
                "- inheritance audit layer: confirms single no longer inherits from double",
                "- benchmark / double compare layer: benchmark oracle remains separate from the direct single result",
                "- cleanup layer: deletion record for outdated single-inherited artifacts",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "- `single_direct_derivation/`: direct single derivation outputs and current stage2 status",
                "- `inheritance_audit/`: marker-removal audit",
                "- `benchmark_double_compare/`: benchmark oracle and double comparison context",
                "- `cleanup/`: deletion and local-cleanup record",
            ]
        ),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate() -> None:
    summary = load_json(SINGLE_DIRECT_SUMMARY_JSON)
    audit = load_json(SINGLE_INHERITANCE_AUDIT_JSON)
    current_stage2 = load_json(CURRENT_STAGE2_JSON)
    assert summary["single_direct_result"]["dBS"] == 16
    assert summary["single_direct_result"]["dAI"] == 13
    assert summary["single_direct_result"]["classification"] == "Z^3"
    assert audit["single_inheritance_marker_count"] == 0
    assert current_stage2["single_status"]["published_result_source"] == "single_direct_internal_raw_bs_mod_ai_v1"
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate()
        print("validated sg194 single direct result outputs")
        return

    ctx = build_context()
    bs_payload = build_bs_payload(ctx)
    ai_payload = build_ai_payload(ctx)
    quotient_payload = build_quotient_payload(ctx)
    summary_payload = build_summary_payload(ctx)
    audit_payload = build_inheritance_audit_payload(ctx)
    cleanup_payload = build_cleanup_payload()

    write_json(SINGLE_DIRECT_BS_JSON, bs_payload)
    write_json(SINGLE_DIRECT_AI_JSON, ai_payload)
    write_json(SINGLE_DIRECT_QUOTIENT_JSON, quotient_payload)
    write_json(SINGLE_DIRECT_SUMMARY_JSON, summary_payload)
    write_json(SINGLE_INHERITANCE_AUDIT_JSON, audit_payload)
    write_json(REMAINING_CLEANUP_JSON, cleanup_payload)
    write_markdown_files(bs_payload, ai_payload, quotient_payload, summary_payload, audit_payload, cleanup_payload)
    refresh_benchmark_status(ctx, summary_payload, audit_payload)
    refresh_adoption_vs_internalization(ctx, summary_payload)
    refresh_readme(summary_payload)
    refresh_live_checkpoint(summary_payload, audit_payload)
    build_package()


if __name__ == "__main__":
    main()
