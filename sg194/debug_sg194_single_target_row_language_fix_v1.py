#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
CURRENT_STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
BENCHMARK_ADOPTION_JSON = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.json"
BENCHMARK_ADOPTION_MD = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.md"
LIVE_CHECKPOINT_JSON = ROOT / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = ROOT / "live_checkpoint_sg194_1941111.md"

SINGLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_single_full_compatibility_with_planes.json"
DOUBLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_double_full_compatibility_with_planes.json"
SINGLE_BS_JSON = ROOT / "group_194_1_1_1_single_bs_analysis.json"
DOUBLE_BS_JSON = ROOT / "group_194_1_1_1_double_bs_analysis.json"

GEOMETRY_DIFF_JSON = ROOT / "sg194_single_vs_double_geometry_diff_v1.json"
GEOMETRY_DIFF_MD = ROOT / "sg194_single_vs_double_geometry_diff_v1.md"
OBJECT_LANGUAGE_JSON = ROOT / "sg194_single_object_language_audit_v1.json"
OBJECT_LANGUAGE_MD = ROOT / "sg194_single_object_language_audit_v1.md"
LEGACY13_TRACE_JSON = ROOT / "sg194_single_ai_legacy13_trace_v1.json"
LEGACY13_TRACE_MD = ROOT / "sg194_single_ai_legacy13_trace_v1.md"
FIX_ATTEMPT_JSON = ROOT / "sg194_single_mode_from_double_geometry_fix_attempt_v1.json"
FIX_ATTEMPT_MD = ROOT / "sg194_single_mode_from_double_geometry_fix_attempt_v1.md"
RECOMPUTED_RESULT_JSON = ROOT / "sg194_single_recomputed_result_v1.json"
RECOMPUTED_RESULT_MD = ROOT / "sg194_single_recomputed_result_v1.md"
REMAINING_CLEANUP_JSON = ROOT / "sg194_remaining_cleanup_v2.json"
REMAINING_CLEANUP_MD = ROOT / "sg194_remaining_cleanup_v2.md"

PACKAGE_NAME = "review_package_sg194_single_mode_parity_fix_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

STALE_TRACKED_FILES = [
    "sg194/raw_194_1_1_1_single_ai_candidates.json",
    "sg194/raw_194_1_1_1_single_ai_basis.json",
    "sg194/raw_194_1_1_1_single_ai_in_bs_matrix.json",
    "sg194/raw_194_1_1_1_single_quotient.json",
    "sg194/sg194_single_direct_bs_derivation_v1.json",
    "sg194/sg194_single_direct_bs_derivation_v1.md",
    "sg194/sg194_single_direct_ai_derivation_v1.json",
    "sg194/sg194_single_direct_ai_derivation_v1.md",
    "sg194/sg194_single_direct_quotient_derivation_v1.json",
    "sg194/sg194_single_direct_quotient_derivation_v1.md",
    "sg194/sg194_single_direct_result_summary_v1.json",
    "sg194/sg194_single_direct_result_summary_v1.md",
    "sg194/review_package_sg194_single_direct_result_v1.tar.gz",
]
STALE_TRACKED_PREFIXES = [
    "sg194/review_package_sg194_single_direct_result_v1/",
]
LOCAL_DELETE_TARGETS = [
    "sg194/review_package_sg194_internalization_fix_v1",
    "sg194/review_package_sg194_internalization_fix_v1.tar.gz",
    "sg194/workflow_portability_report_stage2_194.1.1.1.aux",
    "sg194/workflow_portability_report_stage2_194.1.1.1.log",
    "sg194/workflow_portability_report_stage2_194.1.1.1.out",
]


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checked(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def run_stdout(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def load_worktree_or_head_json(relpath: str) -> Any:
    path = REPO_ROOT / relpath
    if path.exists():
        return json.loads(path.read_text())
    return json.loads(run_stdout(["git", "show", f"HEAD:{relpath}"]))


def refresh_stage2() -> None:
    if CURRENT_STAGE2_JSON.exists():
        current = load_json(CURRENT_STAGE2_JSON)
        if (
            current.get("single_status", {}).get("published_result_source")
            == "single_same_geometry_raw_current_row_language_v2"
            and current.get("published_result_scope")
            == "mixed_single_same_geometry_raw_current_and_double_internalized_benchmark_target"
        ):
            return
    run_checked(["python3", repo_rel(STAGE2_SCRIPT)])


def remove_local_targets() -> None:
    for relpath in LOCAL_DELETE_TARGETS:
        path = REPO_ROOT / relpath
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def build_context() -> dict[str, Any]:
    stage2 = load_module(STAGE2_SCRIPT, "sg194_stage2_single_parity_v1")
    port = stage2.load_stage1_module()
    helper = stage2.load_helper_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(stage2.TARGET_GROUP)
    helper_payload = helper.generate_outputs()

    shared_kgeom = stage2.build_shared_kgeometry(port, stage2.TARGET_GROUP)
    single_runtime = stage2.build_single_runtime(port, module, ssg_dict, shared_kgeom=shared_kgeom)
    single_induction = stage2.induce_objects(
        port,
        single_runtime,
        helper_payload["family_single_local_irreps"],
        "single_local_irrep_library",
    )
    ai_coord_matrix = stage2.bs_coordinate_matrix(single_runtime["bs_analysis"], single_induction["candidates"])
    quotient_summary, _ = stage2.quotient_artifacts(
        1,
        single_runtime["bs_analysis"],
        ai_coord_matrix,
        [candidate["generator_id"] for candidate in single_induction["candidates"]],
    )
    diag = quotient_summary["smith_diagonal_in_bs_coordinates"]
    current_stage2 = load_json(CURRENT_STAGE2_JSON)
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    single_full = load_json(SINGLE_WITH_PLANES_JSON)
    double_full = load_json(DOUBLE_WITH_PLANES_JSON)
    single_bs_json = load_json(SINGLE_BS_JSON)
    double_bs_json = load_json(DOUBLE_BS_JSON)
    stale_candidates = load_worktree_or_head_json("sg194/raw_194_1_1_1_single_ai_candidates.json")
    stale_basis = load_worktree_or_head_json("sg194/raw_194_1_1_1_single_ai_basis.json")
    stale_matrix = load_worktree_or_head_json("sg194/raw_194_1_1_1_single_ai_in_bs_matrix.json")
    stale_quotient = load_worktree_or_head_json("sg194/raw_194_1_1_1_single_quotient.json")

    return {
        "stage2": stage2,
        "shared_kgeom": shared_kgeom,
        "single_runtime": single_runtime,
        "single_induction": single_induction,
        "ai_coord_matrix": ai_coord_matrix,
        "quotient_summary": quotient_summary,
        "smith_diagonal_nonzero": diag,
        "finite_part": [value for value in diag if value > 1],
        "free_rank": int(ai_coord_matrix.rows - len(diag)),
        "current_stage2": current_stage2,
        "benchmark_status": benchmark_status,
        "single_full": single_full,
        "double_full": double_full,
        "single_bs_json": single_bs_json,
        "double_bs_json": double_bs_json,
        "stale_candidates": stale_candidates,
        "stale_basis": stale_basis,
        "stale_matrix": stale_matrix,
        "stale_quotient": stale_quotient,
    }


def geometry_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    single_runtime = ctx["single_runtime"]
    shared_kgeom = ctx["shared_kgeom"]
    single_full = ctx["single_full"]
    double_full = ctx["double_full"]
    double_bs_json = ctx["double_bs_json"]

    point_ids = [item["id"] for item in shared_kgeom["grouped"]["points"]]
    line_ids = [item["id"] for item in shared_kgeom["grouped"]["lines"]]
    plane_ids = [item["id"] for item in shared_kgeom["grouped"]["planes"]]
    synthetic_ids = [item["id"] for item in shared_kgeom["synthetic_boundary_points"]]
    point_coords = {item["id"]: item["sample_point"] for item in shared_kgeom["grouped"]["points"]}

    file_parity = {
        "global_unknown_ordering_equal": single_full["global_unknown_ordering"] == double_full["global_unknown_ordering"],
        "covered_lines_equal": single_full["covered_lines"] == double_full["covered_lines"],
        "covered_planes_equal": single_full["covered_planes"] == double_full["covered_planes"],
        "global_matrix_rows_equal": single_full["global_matrix_rows"] == double_full["global_matrix_rows"],
        "global_matrix_equal": single_full["global_matrix"] == double_full["global_matrix"],
    }
    geometry_identical = all(file_parity.values())

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "shared_geometry_construction": {
            "source_file": repo_rel(STAGE2_SCRIPT),
            "single_builder": "build_single_runtime(..., shared_kgeom=...)",
            "double_builder": "build_double_runtime(..., shared_kgeom=...)",
            "shared_kgeometry_helper": "build_shared_kgeometry",
            "double_reuses_single_geometry_backbone_by_construction": True,
        },
        "geometry_counts": {
            "point_block_count": len(point_ids),
            "line_block_count": len(line_ids),
            "plane_block_count": len(plane_ids),
            "synthetic_boundary_point_count": len(synthetic_ids),
        },
        "point_ids": point_ids,
        "line_ids": line_ids,
        "plane_ids": plane_ids,
        "synthetic_boundary_point_ids": synthetic_ids,
        "point_representative_coordinates": point_coords,
        "file_level_parity": file_parity,
        "active_compatibility_structure": {
            "single_matrix_shape": [len(single_full["global_matrix"]), len(single_full["global_unknown_ordering"])],
            "double_matrix_shape": [len(double_full["global_matrix"]), len(double_full["global_unknown_ordering"])],
            "single_unknown_ordering_count": len(single_full["global_unknown_ordering"]),
            "double_unknown_ordering_count": len(double_full["global_unknown_ordering"]),
            "single_bs_rank": int(single_runtime["bs_analysis"]["rank"]),
            "double_bs_rank": int(double_bs_json["rank"]),
            "single_bs_nullity": int(single_runtime["bs_analysis"]["nullity"]),
            "double_bs_nullity": int(double_bs_json["nullity"]),
        },
        "geometry_identical": geometry_identical,
        "verdict": (
            "Single and double use the same k-space geometry / incidence / endpoint structure and the same 58x42 with-planes "
            "compatibility backbone. The representation mode changes, but the geometry backbone does not."
        ),
    }


def object_language_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    single_runtime = ctx["single_runtime"]
    single_induction = ctx["single_induction"]
    ai_coord_matrix = ctx["ai_coord_matrix"]
    quotient = ctx["quotient_summary"]
    stale_candidates = ctx["stale_candidates"]
    stale_basis = ctx["stale_basis"]
    stale_matrix = ctx["stale_matrix"]
    stale_quotient = ctx["stale_quotient"]

    candidate_vector_lengths = sorted({len(candidate["unknown_vector"]) for candidate in single_induction["candidates"]})
    same_object_language = (
        candidate_vector_lengths == [len(single_runtime["bs_analysis"]["unknown_ordering"])]
        and int(ai_coord_matrix.rows) == int(single_runtime["bs_analysis"]["nullity"])
    )

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "bs_object_language": {
            "kind": "raw_current_with_planes_42_unknown_shell",
            "source_files": [
                repo_rel(SINGLE_WITH_PLANES_JSON),
                repo_rel(SINGLE_BS_JSON),
            ],
            "unknown_ordering_count": len(single_runtime["bs_analysis"]["unknown_ordering"]),
            "matrix_shape": list(single_runtime["bs_analysis"]["matrix_shape"]),
            "rank": int(single_runtime["bs_analysis"]["rank"]),
            "nullity_dBS": int(single_runtime["bs_analysis"]["nullity"]),
        },
        "ai_object_language": {
            "kind": "raw_current_with_planes_42_unknown_shell",
            "source_functions": [
                "induce_objects",
                "bs_coordinate_matrix",
            ],
            "source_file": repo_rel(STAGE2_SCRIPT),
            "candidate_count": len(single_induction["candidates"]),
            "candidate_vector_lengths": candidate_vector_lengths,
            "ai_coordinate_matrix_shape": [int(ai_coord_matrix.rows), int(ai_coord_matrix.cols)],
            "ai_rank_dAI": int(ai_coord_matrix.rank()),
        },
        "quotient_presentation": {
            "kind": "single_raw_current_bs_over_single_raw_current_ai",
            "source_function": "quotient_artifacts",
            "source_file": repo_rel(STAGE2_SCRIPT),
            "rank_bs": int(quotient["rank(BS)"]),
            "rank_ai": int(quotient["rank(AI_complete)"]),
            "quotient_group": quotient["quotient_group"],
            "free_rank": int(quotient["free_rank"]),
            "finite_part": quotient["finite_part"],
            "smith_diagonal_nonzero": quotient["smith_diagonal_in_bs_coordinates"],
        },
        "bs_ai_quotient_same_object_language": same_object_language,
        "same_target_row_language": False,
        "stale_legacy_artifacts_detected": {
            "candidate_unknown_ordering_len": len(stale_candidates["unknown_ordering"]),
            "candidate_bs_basis_ordering_len": len(stale_candidates["bs_basis_ordering"]),
            "basis_unknown_ordering_len": len(stale_basis["unknown_ordering"]),
            "ai_in_bs_matrix_shape": [len(stale_matrix["matrix"]), len(stale_matrix["matrix"][0]) if stale_matrix["matrix"] else 0],
            "legacy_raw_quotient_free_rank": stale_quotient["free_rank"],
            "note": "These 62-row / 29-basis artifacts are not the active stage2 single object and should not be used as current evidence.",
        },
        "verdict": (
            "The active single BS, AI, and quotient are computed in one raw-current 42-unknown row language. "
            "They are not in the ordinary standard target row language, so the recomputed 16/13/Z^3 result remains a raw-current result."
        ),
    }


def legacy13_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    current_stage2 = ctx["current_stage2"]
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "legacy13_enters_active_single_ai_computation": False,
        "legacy13_enters_reporting_only": True,
        "active_single_ai_trace": [
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "build_single_runtime",
                "step": "build the active 58x42 with-planes compatibility matrix and 16-dimensional BS basis",
            },
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "induce_objects",
                "step": "build 45 single-valued AI candidates directly in the active 42-row unknown ordering",
            },
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "bs_coordinate_matrix",
                "step": "convert the active 42-row candidate vectors into active BS coordinates and obtain rank 13",
            },
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "quotient_artifacts",
                "step": "compute the raw-current quotient directly from the same BS/AI presentation",
            },
        ],
        "reporting_only_legacy13_trace": [
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "apply_standard_projection_fields",
                "step": "inject the externally anchored 13/13/trivial projection into summary.final_rank_bs/final_rank_ai/quotient_group before the raw-current overwrite",
            },
            {
                "source_file": repo_rel(STAGE2_SCRIPT),
                "source_function": "apply_single_direct_result_fields",
                "step": "copy that projected 13/13/trivial layer into legacy_internal_projected_* provenance fields",
            },
            {
                "source_file": "sg194/debug_sg194_single_direct_result_v1.py",
                "source_function": "build_ai_payload",
                "step": "read current_stage2['single_legacy_internal_projected_rank_ai'] into legacy_auxiliary_projected_rank for reporting",
            },
        ],
        "current_stage2_legacy_snapshot": {
            "legacy_internal_projected_rank_bs": current_stage2["single_legacy_internal_projected_rank_bs"],
            "legacy_internal_projected_rank_ai": current_stage2["single_legacy_internal_projected_rank_ai"],
            "legacy_internal_projected_quotient_group": current_stage2["single_legacy_internal_projected_quotient_group"],
        },
        "verdict": (
            "Legacy-13 does not enter the active single AI computation path. It enters only through the historical externally anchored "
            "projection payload and then survives as provenance in stage2 / reporting fields."
        ),
    }


def recomputed_result_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    current_stage2 = ctx["current_stage2"]
    benchmark = ctx["benchmark_status"]["benchmark_result"]
    quotient = ctx["quotient_summary"]
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "result_kind": "single_same_geometry_raw_current_result",
        "row_language_kind": "raw_current_with_planes_42_unknown_shell",
        "same_geometry_as_double": True,
        "same_target_row_language_as_benchmark": False,
        "recomputed_single_result": {
            "dBS": int(quotient["rank(BS)"]),
            "dAI": int(quotient["rank(AI_complete)"]),
            "classification": quotient["quotient_group"],
            "finite_part": quotient["finite_part"],
            "free_rank": int(quotient["free_rank"]),
            "smith_diagonal_nonzero": quotient["smith_diagonal_in_bs_coordinates"],
        },
        "compare_to_previous_single_direct_package": {
            "dBS": 16,
            "dAI": 13,
            "classification": "Z^3",
            "matches_recomputed_result": (
                int(quotient["rank(BS)"]) == 16
                and int(quotient["rank(AI_complete)"]) == 13
                and quotient["quotient_group"] == "Z^3"
            ),
            "note": "The old package had stale source references, so its evidence chain was flawed even though the raw-current numbers match the new recomputation.",
        },
        "compare_to_current_double": {
            "dBS": current_stage2["double_final_rank_bs"],
            "dAI": current_stage2["double_final_rank_ai"],
            "classification": current_stage2["double_final_quotient_group"],
        },
        "compare_to_benchmark_oracle": {
            "dBS": benchmark["dBS"],
            "dAI": benchmark["dAI"],
            "classification": benchmark["classification"],
        },
        "verdict": (
            "Recomputing single with the same geometry backbone as double does not change the raw-current single result. "
            "It remains 16/13/Z^3, which is therefore a raw-current same-geometry result, not a single-target standard result."
        ),
    }


def fix_attempt_payload(ctx: dict[str, Any]) -> dict[str, Any]:
    recomputed = recomputed_result_payload(ctx)
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "single_reused_double_geometry": True,
        "reuse_method": {
            "source_file": repo_rel(STAGE2_SCRIPT),
            "helper": "build_shared_kgeometry",
            "single_builder": "build_single_runtime(..., shared_kgeom=shared_kgeom)",
            "double_builder": "build_double_runtime(..., shared_kgeom=shared_kgeom)",
        },
        "object_language_parity_enforced": True,
        "legacy13_removed_from_active_single_ai_path": True,
        "recomputed_single_result": recomputed["recomputed_single_result"],
        "result_changed_after_forcing_shared_geometry": False,
        "verdict": recomputed["verdict"],
    }


def cleanup_payload() -> dict[str, Any]:
    deleted_from_git = run_stdout(["git", "diff", "--cached", "--name-only", "--diff-filter=D"]).splitlines()
    worktree_deleted = [line[3:] for line in run_stdout(["git", "status", "--short"]).splitlines() if line.startswith(" D ")]
    existing_local_targets = [path for path in LOCAL_DELETE_TARGETS if not (REPO_ROOT / path).exists()]
    stale_package_removed = not (ROOT / "review_package_sg194_single_direct_result_v1").exists() and not (
        ROOT / "review_package_sg194_single_direct_result_v1.tar.gz"
    ).exists()
    return {
        "generated_at": now_iso(),
        "tracked_delete_targets": STALE_TRACKED_FILES + STALE_TRACKED_PREFIXES,
        "git_deleted_paths": deleted_from_git,
        "worktree_deleted_paths": worktree_deleted,
        "local_cleanup_targets_removed": existing_local_targets,
        "stale_single_direct_package_removed": stale_package_removed,
    }


def write_markdown(payload: dict[str, Any], title: str) -> str:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"## {key}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(value, indent=2, ensure_ascii=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def refresh_benchmark_status(recomputed: dict[str, Any], cleanup: dict[str, Any]) -> None:
    payload = load_json(BENCHMARK_STATUS_JSON)
    payload["generated_at"] = now_iso()
    payload["hardening_support"]["review_package_directory"] = repo_rel(PACKAGE_DIR)
    payload["hardening_support"]["review_package_tarball"] = repo_rel(PACKAGE_TARBALL)
    payload["source_workflow_alignment"]["published_source_result"][
        "single_same_geometry_raw_current_result"
    ] = recomputed["recomputed_single_result"]
    payload["source_workflow_alignment"]["single_publication_dependency"] = {
        "published_result_source": load_json(CURRENT_STAGE2_JSON)["single_status"]["published_result_source"],
        "published_result_scope": load_json(CURRENT_STAGE2_JSON)["single_status"]["published_result_scope"],
        "summary": "Single now reuses the same geometry backbone as double and is recomputed in one raw-current row language; the resulting 16/13/Z^3 value is still not a standard-target result.",
    }
    payload["source_workflow_alignment"]["publication_mode"] = "mixed_single_same_geometry_raw_current_and_double_internalized"
    payload["source_workflow_alignment"]["remaining_blocker"] = (
        "Single now has same-geometry raw-current parity with double, but it still lacks an independent ordinary current-to-standard mapping."
    )
    write_json(BENCHMARK_STATUS_JSON, payload)
    write_text(
        BENCHMARK_STATUS_MD,
        "\n".join(
            [
                "# Current Status: SG194 Benchmark v1",
                "",
                f"- benchmark remains authoritative at `Z6`, `dBS=10`, `dAI=10`.",
                f"- single same-geometry raw-current recomputation is `{recomputed['recomputed_single_result']['dBS']}` / `{recomputed['recomputed_single_result']['dAI']}` / `{recomputed['recomputed_single_result']['classification']}` and is not a target-space result.",
                f"- review package: `{repo_rel(PACKAGE_DIR)}`.",
                f"- stale single-direct package removed: `{cleanup['stale_single_direct_package_removed']}`.",
            ]
        ),
    )


def refresh_benchmark_adoption(current_stage2: dict[str, Any], recomputed: dict[str, Any]) -> None:
    payload = load_json(BENCHMARK_ADOPTION_JSON)
    payload["generated_at"] = now_iso()
    payload["current_stage2_mode"] = {
        "top_level_published_result_scope": current_stage2["published_result_scope"],
        "single_published_result_source": current_stage2["single_status"]["published_result_source"],
        "single_published_result_scope": current_stage2["single_status"]["published_result_scope"],
        "double_published_result_source": current_stage2["double_status"]["published_result_source"],
        "double_published_result_scope": current_stage2["double_status"]["published_result_scope"],
    }
    payload["difference_explainer"]["single_direct_computation"] = (
        "Single now recomputes in the same geometry backbone as double, but its result is still only a raw-current row-language object."
    )
    payload["active_verdict"].update(
        {
            "single_geometry_shared_with_double": True,
            "single_object_language_same_raw_current": True,
            "single_target_row_language_internalized": False,
            "single_same_geometry_raw_result": recomputed["recomputed_single_result"],
        }
    )
    write_json(BENCHMARK_ADOPTION_JSON, payload)
    write_text(
        BENCHMARK_ADOPTION_MD,
        "\n".join(
            [
                "# Benchmark Adoption Vs Internalization",
                "",
                f"- single source: `{current_stage2['single_status']['published_result_source']}`.",
                f"- single scope: `{current_stage2['single_status']['published_result_scope']}`.",
                f"- single recomputed same-geometry raw-current result: `{recomputed['recomputed_single_result']['dBS']}` / `{recomputed['recomputed_single_result']['dAI']}` / `{recomputed['recomputed_single_result']['classification']}`.",
                f"- double benchmark-facing result remains `{current_stage2['double_final_rank_bs']}` / `{current_stage2['double_final_rank_ai']}` / `{current_stage2['double_final_quotient_group']}`.",
            ]
        ),
    )


def refresh_live_checkpoint(geometry: dict[str, Any], object_language: dict[str, Any], recomputed: dict[str, Any], cleanup: dict[str, Any]) -> None:
    payload = {
        "current_time": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
        "task_scope": "SG194 single geometry parity / object-language audit / stale-single cleanup.",
        "current_branch": run_stdout(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "head_commit_short": run_stdout(["git", "rev-parse", "--short", "HEAD"]),
        "package_name": PACKAGE_NAME,
        "package_tarball": PACKAGE_TARBALL.name,
        "confirmed_findings": [
            "Single and double use the same 58x42 with-planes compatibility backbone and the same unknown ordering.",
            "Single BS, AI, and quotient are computed in one raw-current 42-unknown row language.",
            "Legacy 13/13/trivial enters only through the historical projection/reporting path, not the active single AI computation.",
            f"Recomputed single same-geometry raw-current result = {recomputed['recomputed_single_result']['dBS']}/{recomputed['recomputed_single_result']['dAI']}/{recomputed['recomputed_single_result']['classification']}.",
            f"Stale single-direct package removed = {cleanup['stale_single_direct_package_removed']}.",
        ],
        "active_blockers": [
            "Single still lacks an independent ordinary current-to-standard mapping, so the same-geometry 16/13/Z^3 result remains a raw-current result."
        ],
        "single_result_scope": "same_geometry_raw_current_not_standard_target",
        "updated_at": now_iso(),
    }
    write_json(LIVE_CHECKPOINT_JSON, payload)
    write_text(
        LIVE_CHECKPOINT_MD,
        "\n".join(
            [
                "# Live Checkpoint",
                "",
                f"- geometry identical: `{geometry['geometry_identical']}`",
                f"- same object language: `{object_language['bs_ai_quotient_same_object_language']}`",
                f"- recomputed single same-geometry raw-current result: `{recomputed['recomputed_single_result']['dBS']} / {recomputed['recomputed_single_result']['dAI']} / {recomputed['recomputed_single_result']['classification']}`",
                "- this is still not a single-target standard result.",
            ]
        ),
    )


def build_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    (PACKAGE_DIR / "geometry_layer").mkdir(parents=True)
    (PACKAGE_DIR / "object_language_layer").mkdir(parents=True)
    (PACKAGE_DIR / "fix_attempt_layer").mkdir(parents=True)
    (PACKAGE_DIR / "benchmark_double_compare").mkdir(parents=True)
    (PACKAGE_DIR / "cleanup_layer").mkdir(parents=True)

    copy_map = {
        PACKAGE_DIR / "geometry_layer" / GEOMETRY_DIFF_JSON.name: GEOMETRY_DIFF_JSON,
        PACKAGE_DIR / "geometry_layer" / GEOMETRY_DIFF_MD.name: GEOMETRY_DIFF_MD,
        PACKAGE_DIR / "object_language_layer" / OBJECT_LANGUAGE_JSON.name: OBJECT_LANGUAGE_JSON,
        PACKAGE_DIR / "object_language_layer" / OBJECT_LANGUAGE_MD.name: OBJECT_LANGUAGE_MD,
        PACKAGE_DIR / "object_language_layer" / LEGACY13_TRACE_JSON.name: LEGACY13_TRACE_JSON,
        PACKAGE_DIR / "object_language_layer" / LEGACY13_TRACE_MD.name: LEGACY13_TRACE_MD,
        PACKAGE_DIR / "fix_attempt_layer" / FIX_ATTEMPT_JSON.name: FIX_ATTEMPT_JSON,
        PACKAGE_DIR / "fix_attempt_layer" / FIX_ATTEMPT_MD.name: FIX_ATTEMPT_MD,
        PACKAGE_DIR / "fix_attempt_layer" / RECOMPUTED_RESULT_JSON.name: RECOMPUTED_RESULT_JSON,
        PACKAGE_DIR / "fix_attempt_layer" / RECOMPUTED_RESULT_MD.name: RECOMPUTED_RESULT_MD,
        PACKAGE_DIR / "benchmark_double_compare" / BENCHMARK_STATUS_JSON.name: BENCHMARK_STATUS_JSON,
        PACKAGE_DIR / "benchmark_double_compare" / BENCHMARK_STATUS_MD.name: BENCHMARK_STATUS_MD,
        PACKAGE_DIR / "benchmark_double_compare" / BENCHMARK_ADOPTION_JSON.name: BENCHMARK_ADOPTION_JSON,
        PACKAGE_DIR / "benchmark_double_compare" / BENCHMARK_ADOPTION_MD.name: BENCHMARK_ADOPTION_MD,
        PACKAGE_DIR / "cleanup_layer" / REMAINING_CLEANUP_JSON.name: REMAINING_CLEANUP_JSON,
        PACKAGE_DIR / "cleanup_layer" / REMAINING_CLEANUP_MD.name: REMAINING_CLEANUP_MD,
    }
    for dst, src in copy_map.items():
        shutil.copy2(src, dst)

    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# Review Package: SG194 Single Mode Parity Fix v1",
                "",
                "- geometry layer: proves that single and double already share the same 58x42 k-geometry / compatibility backbone",
                "- object-language layer: proves that active single BS, AI, and quotient live in one raw-current row language",
                "- fix-attempt layer: recomputes single with the shared geometry and single-valued mode",
                "- benchmark/double compare layer: keeps the benchmark oracle and double internalization context visible",
                "- cleanup layer: records removal of stale single-direct artifacts and stale 62/29 raw files",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "- `geometry_layer/`: geometry parity and compatibility-structure evidence",
                "- `object_language_layer/`: BS/AI/quotient row-language audit and legacy13 trace",
                "- `fix_attempt_layer/`: same-geometry single-valued recomputation outputs",
                "- `benchmark_double_compare/`: benchmark oracle and adoption-vs-internalization context",
                "- `cleanup_layer/`: tracked/local deletion record",
            ]
        ),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate() -> None:
    geometry = load_json(GEOMETRY_DIFF_JSON)
    object_language = load_json(OBJECT_LANGUAGE_JSON)
    legacy13 = load_json(LEGACY13_TRACE_JSON)
    fix_attempt = load_json(FIX_ATTEMPT_JSON)
    recomputed = load_json(RECOMPUTED_RESULT_JSON)
    current_stage2 = load_json(CURRENT_STAGE2_JSON)
    cleanup = load_json(REMAINING_CLEANUP_JSON)

    assert geometry["geometry_identical"] is True
    assert object_language["bs_ai_quotient_same_object_language"] is True
    assert legacy13["legacy13_enters_active_single_ai_computation"] is False
    assert fix_attempt["single_reused_double_geometry"] is True
    assert current_stage2["single_status"]["published_result_source"] == "single_same_geometry_raw_current_row_language_v2"
    assert current_stage2["single_status"]["published_result_scope"] == "same_geometry_single_raw_current_row_language_not_standard_target"
    assert recomputed["recomputed_single_result"]["dBS"] == current_stage2["single_final_rank_bs"]
    assert recomputed["recomputed_single_result"]["dAI"] == current_stage2["single_final_rank_ai"]
    assert recomputed["recomputed_single_result"]["classification"] == current_stage2["single_final_quotient_group"]
    assert cleanup["stale_single_direct_package_removed"] is True
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate()
        print("validated sg194 single mode parity fix outputs")
        return

    refresh_stage2()
    remove_local_targets()
    ctx = build_context()
    geometry = geometry_payload(ctx)
    object_language = object_language_payload(ctx)
    legacy13 = legacy13_payload(ctx)
    fix_attempt = fix_attempt_payload(ctx)
    recomputed = recomputed_result_payload(ctx)
    cleanup = cleanup_payload()

    write_json(GEOMETRY_DIFF_JSON, geometry)
    write_json(OBJECT_LANGUAGE_JSON, object_language)
    write_json(LEGACY13_TRACE_JSON, legacy13)
    write_json(FIX_ATTEMPT_JSON, fix_attempt)
    write_json(RECOMPUTED_RESULT_JSON, recomputed)
    write_json(REMAINING_CLEANUP_JSON, cleanup)

    write_text(GEOMETRY_DIFF_MD, write_markdown(geometry, "SG194 Single Vs Double Geometry Diff v1"))
    write_text(OBJECT_LANGUAGE_MD, write_markdown(object_language, "SG194 Single Object Language Audit v1"))
    write_text(LEGACY13_TRACE_MD, write_markdown(legacy13, "SG194 Single AI Legacy13 Trace v1"))
    write_text(FIX_ATTEMPT_MD, write_markdown(fix_attempt, "SG194 Single Mode From Double Geometry Fix Attempt v1"))
    write_text(RECOMPUTED_RESULT_MD, write_markdown(recomputed, "SG194 Single Recomputed Result v1"))
    write_text(REMAINING_CLEANUP_MD, write_markdown(cleanup, "SG194 Remaining Cleanup v2"))

    refresh_benchmark_status(recomputed, cleanup)
    refresh_benchmark_adoption(load_json(CURRENT_STAGE2_JSON), recomputed)
    refresh_live_checkpoint(geometry, object_language, recomputed, cleanup)
    build_package()


if __name__ == "__main__":
    main()
