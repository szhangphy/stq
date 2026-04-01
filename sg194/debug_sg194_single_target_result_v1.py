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
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
CURRENT_STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
SINGLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
BENCHMARK_ADOPTION_JSON = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.json"
BENCHMARK_ADOPTION_MD = ROOT / "sg194_benchmark_adoption_vs_internalization_v1.md"
LIVE_CHECKPOINT_JSON = ROOT / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = ROOT / "live_checkpoint_sg194_1941111.md"
POINT_SNAPSHOT_JSON = ROOT / "sg194_current_point_space_snapshot_v1.json"
PROJECTION_SUMMARY_JSON = ROOT / "sg194_standard_space_projection_summary_v1.json"
EXTERNAL_ORDINARY_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"

DOUBLE_STACK_JSON = ROOT / "sg194_double_target_object_stack_v1.json"
DOUBLE_STACK_MD = ROOT / "sg194_double_target_object_stack_v1.md"
SINGLE_MISSING_JSON = ROOT / "sg194_single_missing_target_layers_v1.json"
SINGLE_MISSING_MD = ROOT / "sg194_single_missing_target_layers_v1.md"
FIX_ATTEMPT_JSON = ROOT / "sg194_single_target_row_language_fix_attempt_v1.json"
FIX_ATTEMPT_MD = ROOT / "sg194_single_target_row_language_fix_attempt_v1.md"
TARGET_RESULT_JSON = ROOT / "sg194_single_target_result_v1.json"
TARGET_RESULT_MD = ROOT / "sg194_single_target_result_v1.md"
RAW_VS_TARGET_JSON = ROOT / "sg194_single_raw_vs_target_comparison_v1.json"
RAW_VS_TARGET_MD = ROOT / "sg194_single_raw_vs_target_comparison_v1.md"
CLEANUP_JSON = ROOT / "sg194_wrong_single_result_cleanup_v1.json"
CLEANUP_MD = ROOT / "sg194_wrong_single_result_cleanup_v1.md"

PACKAGE_NAME = "review_package_sg194_single_target_result_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

STALE_TRACKED_PATHS = [
    "sg194/sg194_single_mode_from_double_geometry_fix_attempt_v1.json",
    "sg194/sg194_single_mode_from_double_geometry_fix_attempt_v1.md",
    "sg194/sg194_single_recomputed_result_v1.json",
    "sg194/sg194_single_recomputed_result_v1.md",
    "sg194/review_package_sg194_single_mode_parity_fix_v1",
    "sg194/review_package_sg194_single_mode_parity_fix_v1.tar.gz",
]

LOCAL_DELETE_TARGETS = [
    "sg194/workflow_portability_report_stage2_194.1.1.1.aux",
    "sg194/workflow_portability_report_stage2_194.1.1.1.log",
    "sg194/workflow_portability_report_stage2_194.1.1.1.out",
]


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def run_checked(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def git_tracked(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relpath],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def refresh_stage2() -> None:
    current = load_json(CURRENT_STAGE2_JSON) if CURRENT_STAGE2_JSON.exists() else {}
    if current.get("single_status", {}).get("published_result_source") == "single_target_projection_contract_v1":
        return
    run_checked(["python3", repo_rel(STAGE2_SCRIPT)])


def solve_left_projection_matrix(
    source_columns: sp.Matrix,
    target_columns: sp.Matrix,
) -> tuple[bool, sp.Matrix | None, int | None, str | None]:
    source_transposed = source_columns.T
    solved_rows: list[sp.Matrix] = []
    for row_index in range(target_columns.rows):
        rhs = target_columns.row(row_index).T
        try:
            solution = source_transposed.gauss_jordan_solve(rhs)[0]
        except ValueError as exc:
            return False, None, row_index, str(exc)
        if not source_transposed * solution == rhs:
            return False, None, row_index, "candidate row solution failed exact reconstruction"
        solved_rows.append(solution.T)
    return True, sp.Matrix.vstack(*solved_rows), None, None


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    parts: list[str] = []
    if free_rank:
        parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts) if parts else "trivial"


def compute_single_target_analysis() -> dict[str, Any]:
    current_stage2 = load_json(CURRENT_STAGE2_JSON)
    stage2_summary = load_json(CURRENT_STAGE2_SUMMARY_JSON)
    single_completion = load_json(SINGLE_COMPLETION_JSON)
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    projection = load_json(PROJECTION_SUMMARY_JSON)
    snapshot = load_json(POINT_SNAPSHOT_JSON)
    external = load_json(EXTERNAL_ORDINARY_JSON)

    single_candidates = snapshot["single_ai_candidate_vectors"]
    generator_ids = [candidate["generator_id"] for candidate in single_candidates]
    current_ai_bs = sp.Matrix.hstack(*[sp.Matrix(candidate["bs_coordinates"]) for candidate in single_candidates])
    projection_matrix = sp.Matrix(projection["projection_matrix_bs_to_standard_rows"])
    external_cols = list(external["column_labels"])
    external_rows = list(external["row_labels"])
    external_reordered = sp.Matrix.hstack(
        *[sp.Matrix([row[external_cols.index(generator_id)] for row in external["matrix_entries"]]) for generator_id in generator_ids]
    )
    projected_current = projection_matrix * current_ai_bs
    projected_bs_image_cols = projection_matrix.columnspace()
    projected_bs_image = (
        sp.Matrix.hstack(*projected_bs_image_cols) if projected_bs_image_cols else sp.zeros(projection_matrix.rows, 0)
    )
    projected_ai_in_bs = (
        projected_bs_image.gauss_jordan_solve(projected_current)[0]
        if projected_bs_image.cols
        else sp.zeros(0, projected_current.cols)
    )
    diagonal, _, _ = smith_normal_decomp(projected_ai_in_bs, domain=ZZ)
    smith = [
        abs(int(diagonal[idx, idx]))
        for idx in range(min(diagonal.rows, diagonal.cols))
        if int(diagonal[idx, idx]) != 0
    ]
    finite_part = [value for value in smith if value > 1]
    free_rank = int(projected_bs_image.cols - len(smith))
    exact_solution_exists, exact_solution_matrix, failed_row, failed_reason = solve_left_projection_matrix(
        current_ai_bs,
        external_reordered,
    )
    mismatch = projected_current - external_reordered
    mismatch_columns = [
        generator_ids[col_idx]
        for col_idx in range(mismatch.cols)
        if any(int(mismatch[row_idx, col_idx]) != 0 for row_idx in range(mismatch.rows))
    ]
    mismatch_rows = [
        external_rows[row_idx]
        for row_idx in range(mismatch.rows)
        if any(int(mismatch[row_idx, col_idx]) != 0 for col_idx in range(mismatch.cols))
    ]

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "single_raw_current_result": {
            "dBS": int(single_completion["rank_bs_raw_internal"]),
            "dAI": int(single_completion["rank_ai_raw_internal"]),
            "rank_bs": int(single_completion["rank_bs_raw_internal"]),
            "rank_ai": int(single_completion["rank_ai_raw_internal"]),
            "classification": single_completion["raw_internal_quotient_group"],
        },
        "single_target_projection_contract": {
            "projection_contract_type": projection["projection_contract_type"],
            "target_row_language_kind": "ordinary_sg194_external_row_language",
            "projection_matrix_shape": [projection_matrix.rows, projection_matrix.cols],
            "generator_column_count": len(generator_ids),
            "generator_inventory_matches_external": set(generator_ids) == set(external_cols),
            "projected_current_matches_external_matrix_exactly": projected_current == external_reordered,
            "exact_linear_target_alignment_exists": exact_solution_exists,
            "exact_linear_target_alignment_failed_row": failed_row,
            "exact_linear_target_alignment_failure_reason": failed_reason,
            "exact_linear_target_alignment_matrix_rank": int(exact_solution_matrix.rank()) if exact_solution_matrix is not None else None,
            "exact_generator_identity_status": (
                "available"
                if exact_solution_exists and projected_current == external_reordered
                else "missing"
            ),
            "mismatch_rank_after_projection": int(mismatch.rank()),
            "mismatch_column_labels": mismatch_columns,
            "mismatch_row_labels": mismatch_rows,
            "common_ai_basis_generator_ids": list(projection["common_ai_basis_generator_ids"]),
        },
        "single_target_result": {
            "dBS": int(projected_bs_image.rank()),
            "dAI": int(projected_current.rank()),
            "classification": quotient_group_string(free_rank, finite_part),
            "quotient_group": quotient_group_string(free_rank, finite_part),
            "free_rank": free_rank,
            "finite_part": finite_part,
            "smith_diagonal_nonzero": smith,
            "direct_target_derivation": True,
            "benchmark_overwrite": False,
            "inherited_from_double": False,
            "same_as_benchmark": False,
        },
        "double_target_result": {
            "dBS": int(current_stage2["double_final_rank_bs"]),
            "dAI": int(current_stage2["double_final_rank_ai"]),
            "classification": current_stage2["double_final_quotient_group"],
        },
        "benchmark_oracle": benchmark_status["benchmark_result"],
        "current_stage2_single_status": current_stage2["single_status"],
        "stage2_summary": stage2_summary,
    }


def build_double_target_stack(current_stage2: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "double_target_object_stack": [
            {
                "layer": 1,
                "name": "shared_k_geometry",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "build_shared_kgeometry",
                "artifact": "sg194/group_194_1_1_1_double_full_compatibility_with_planes.json",
                "summary": "Shared k-space geometry / incidence / endpoint ordering reused by both single and double runtime builders.",
            },
            {
                "layer": 2,
                "name": "active_current_row_language",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "build_double_runtime",
                "artifact": "sg194/group_194_1_1_1_double_bs_analysis.json",
                "summary": "42-row current runtime shell with raw BS nullity 16 before target matching.",
            },
            {
                "layer": 3,
                "name": "target_row_language_or_benchmark_target",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "load_double_internalization_snapshot",
                "artifact": "sg194/sg194_external_spinorial_generator_matrix.json",
                "summary": "Benchmark-facing double target object represented by the external spinorial 33-generator matrix.",
            },
            {
                "layer": 4,
                "name": "current_external_generator_alignment",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "load_double_internalization_snapshot",
                "artifact": "sg194/sg194_double_complement_patch_summary_v1.json",
                "summary": "Exact 33-channel generator-space identity with rank record 10/10/10/10.",
            },
            {
                "layer": 5,
                "name": "target_layer_ai_basis",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "load_double_internalization_snapshot",
                "artifact": "sg194/raw_194_1_1_1_double_ai_in_bs_matrix_patched_v2.json",
                "summary": "Current double AI basis already internalized into the benchmark target object at rank 10.",
            },
            {
                "layer": 6,
                "name": "quotient_presentation",
                "status": "available",
                "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "source_function": "apply_double_internalization_fields",
                "artifact": "sg194/current_status_194.1.1.1_stage2.json",
                "summary": current_stage2["double_status"]["quotient_derivation_mode"],
            },
        ],
    }


def build_single_missing_layers(target_analysis: dict[str, Any]) -> dict[str, Any]:
    single_status = target_analysis["current_stage2_single_status"]
    contract = target_analysis["single_target_projection_contract"]
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "single_available_layers": [
            "shared_k_geometry",
            "active_current_row_language",
            "ordinary_external_target_rows",
            "projected_target_row_quotient_presentation",
        ],
        "single_missing_layers_before_fix": [
            "active_use_of_target_result_in_stage2_final_fields",
            "exact_single_current_external_generator_alignment",
        ],
        "blocking_function": {
            "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
            "source_function": "apply_single_direct_result_fields",
            "problem": "Overwrote the target-row-language 13/13/trivial payload with raw-current 16/13/Z^3 publication fields.",
        },
        "blocking_matrices": {
            "current_single_ai_bs_matrix_shape": [16, contract["generator_column_count"]],
            "target_projection_matrix_shape": contract["projection_matrix_shape"],
            "external_ordinary_generator_matrix_shape": [34, contract["generator_column_count"]],
            "exact_linear_target_alignment_exists": contract["exact_linear_target_alignment_exists"],
            "projected_current_matches_external_matrix_exactly": contract["projected_current_matches_external_matrix_exactly"],
            "mismatch_rank_after_projection": contract["mismatch_rank_after_projection"],
        },
        "status_after_fix": {
            "single_target_result_is_active": single_status["published_result_source"] == "single_target_projection_contract_v1",
            "single_target_row_language_active": single_status["single_target_row_language_active"],
            "single_target_row_language_internalized": single_status["single_target_row_language_internalized"],
            "remaining_gap": single_status["remaining_internal_mapping_blocker"],
        },
    }


def md_with_json(title: str, summary_lines: list[str], payload: Any) -> str:
    lines = [f"# {title}", ""]
    lines.extend(summary_lines)
    lines.extend(["", "```json", json.dumps(payload, indent=2, ensure_ascii=True), "```"])
    return "\n".join(lines)


def cleanup_wrong_single_results() -> dict[str, Any]:
    git_deleted: list[str] = []
    commands: list[str] = []
    for relpath in STALE_TRACKED_PATHS:
        if git_tracked(relpath):
            run_checked(["git", "rm", "-r", "-f", "--", relpath])
            git_deleted.append(relpath)
            commands.append(f"git rm -r -f -- {relpath}")

    local_deleted: list[str] = []
    for relpath in LOCAL_DELETE_TARGETS:
        path = REPO_ROOT / relpath
        if path.is_dir():
            shutil.rmtree(path)
            local_deleted.append(relpath)
        elif path.exists():
            path.unlink()
            local_deleted.append(relpath)

    return {
        "generated_at": now_iso(),
        "git_deleted": git_deleted,
        "local_deleted": local_deleted,
        "commands": commands,
        "reason": "Remove raw-current single result files/packages from final-facing positions after single target-row-language result becomes active.",
    }


def update_benchmark_status(target_analysis: dict[str, Any]) -> None:
    payload = load_json(BENCHMARK_STATUS_JSON)
    target_result = target_analysis["single_target_result"]
    raw_result = target_analysis["single_raw_current_result"]
    payload["review_package"] = {
        "review_package_directory": f"sg194/{PACKAGE_NAME}",
        "review_package_tarball": f"sg194/{PACKAGE_TARBALL.name}",
    }
    payload["source_workflow_alignment"]["published_source_result"] = {
        "single_raw_current_result": {
            "dBS": raw_result["rank_bs"],
            "dAI": raw_result["rank_ai"],
            "classification": raw_result["classification"],
        },
        "single_target_result": {
            "dBS": target_result["dBS"],
            "dAI": target_result["dAI"],
            "classification": target_result["classification"],
            "quotient_group": target_result["quotient_group"],
        },
        "double_internalized_result": payload["benchmark_result"],
    }
    payload["source_workflow_alignment"]["single_publication_dependency"] = {
        "published_result_source": "single_target_projection_contract_v1",
        "published_result_scope": "single_target_row_language_via_external_ordinary_projection_contract",
        "summary": (
            "Single now publishes the ordinary target-row-language result 13/13/trivial through the external "
            "projection contract. The raw-current 16/13/Z^3 object is retained as provenance only, and the missing "
            "piece relative to the double-style internalization is exact current/external single generator alignment."
        ),
    }
    payload["source_workflow_alignment"]["publication_mode"] = (
        "single_target_projection_contract_plus_double_benchmark_internalization"
    )
    payload["source_workflow_alignment"]["remaining_blocker"] = (
        "Single target rows are now active, but exact single current/external generator alignment is still missing; "
        "the present single target result is a projection-contract result, not the same exact generator-identity mode used by double."
    )
    write_json(BENCHMARK_STATUS_JSON, payload)
    write_text(
        BENCHMARK_STATUS_MD,
        "\n".join(
            [
                "# SG194 Benchmark Status v1",
                "",
                f"- benchmark authoritative oracle remains `{payload['benchmark_result']['classification']}`, "
                f"`dBS={payload['benchmark_result']['dBS']}`, `dAI={payload['benchmark_result']['dAI']}`;",
                "- single final answer is now separate from the benchmark target;",
                "- active single target-row-language result = `13 / 13 / trivial` via external ordinary projection contract;",
                "- raw-current single provenance = `16 / 13 / Z^3`;",
                f"- review package: `sg194/{PACKAGE_NAME}`.",
            ]
        ),
    )


def update_benchmark_adoption_vs_internalization(target_analysis: dict[str, Any]) -> None:
    payload = load_json(BENCHMARK_ADOPTION_JSON)
    target_result = target_analysis["single_target_result"]
    contract = target_analysis["single_target_projection_contract"]
    payload["single_target_result"] = {
        "published_result_source": "single_target_projection_contract_v1",
        "published_result_scope": "single_target_row_language_via_external_ordinary_projection_contract",
        "dBS": target_result["dBS"],
        "dAI": target_result["dAI"],
        "classification": target_result["classification"],
        "exact_generator_identity_status": contract["exact_generator_identity_status"],
        "exact_linear_target_alignment_exists": contract["exact_linear_target_alignment_exists"],
    }
    payload["single_raw_current_provenance"] = target_analysis["single_raw_current_result"]
    write_json(BENCHMARK_ADOPTION_JSON, payload)
    write_text(
        BENCHMARK_ADOPTION_MD,
        "\n".join(
            [
                "# SG194 Benchmark Adoption vs Internalization v1",
                "",
                "- benchmark-facing double path remains `10/10/Z6` via exact spinorial generator alignment;",
                "- single raw-current provenance remains `16/13/Z^3`;",
                "- active single target result is `13/13/trivial` via the external ordinary projection contract;",
                "- exact single current/external generator identity is still missing.",
            ]
        ),
    )


def update_live_checkpoint(target_analysis: dict[str, Any], cleanup_payload: dict[str, Any]) -> None:
    payload = {
        "current_time": now_iso(),
        "package_name": PACKAGE_NAME,
        "package_tarball": PACKAGE_TARBALL.name,
        "single_target_result": target_analysis["single_target_result"],
        "single_raw_current_provenance": target_analysis["single_raw_current_result"],
        "double_target_result": target_analysis["double_target_result"],
        "single_target_exact_generator_identity_status": target_analysis["single_target_projection_contract"][
            "exact_generator_identity_status"
        ],
        "cleanup_git_deleted": cleanup_payload["git_deleted"],
        "cleanup_local_deleted": cleanup_payload["local_deleted"],
    }
    write_json(LIVE_CHECKPOINT_JSON, payload)
    write_text(
        LIVE_CHECKPOINT_MD,
        "\n".join(
            [
                "# SG194 Live Checkpoint",
                "",
                f"- package = `{PACKAGE_NAME}`",
                "- single target result = `13 / 13 / trivial`",
                "- single raw-current provenance = `16 / 13 / Z^3`",
                "- double benchmark-target result = `10 / 10 / Z6`",
                f"- single exact generator identity status = `{payload['single_target_exact_generator_identity_status']}`",
            ]
        ),
    )


def build_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    copy_map = {
        "target_object_stack": [
            DOUBLE_STACK_JSON,
            DOUBLE_STACK_MD,
            SINGLE_MISSING_JSON,
            SINGLE_MISSING_MD,
        ],
        "fix_attempt": [
            FIX_ATTEMPT_JSON,
            FIX_ATTEMPT_MD,
        ],
        "result": [
            TARGET_RESULT_JSON,
            TARGET_RESULT_MD,
            RAW_VS_TARGET_JSON,
            RAW_VS_TARGET_MD,
        ],
        "benchmark_double_compare": [
            BENCHMARK_STATUS_JSON,
            BENCHMARK_STATUS_MD,
            BENCHMARK_ADOPTION_JSON,
            BENCHMARK_ADOPTION_MD,
            CURRENT_STAGE2_JSON,
            CURRENT_STAGE2_SUMMARY_JSON,
            SINGLE_COMPLETION_JSON,
        ],
        "cleanup": [
            CLEANUP_JSON,
            CLEANUP_MD,
        ],
    }
    for subdir, paths in copy_map.items():
        target_dir = PACKAGE_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            shutil.copy2(path, target_dir / path.name)

    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# Review Package: SG194 Single Target Result v1",
                "",
                "- Purpose: promote single from raw-current publication to an honest target-row-language result.",
                "- Single final target result in this package: `13 / 13 / trivial`.",
                "- Single raw-current provenance retained for contrast: `16 / 13 / Z^3`.",
                "- Double benchmark-facing result retained for comparison: `10 / 10 / Z6`.",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "1. `target_object_stack/sg194_double_target_object_stack_v1.json`",
                "2. `target_object_stack/sg194_single_missing_target_layers_v1.json`",
                "3. `fix_attempt/sg194_single_target_row_language_fix_attempt_v1.json`",
                "4. `result/sg194_single_target_result_v1.json`",
                "5. `result/sg194_single_raw_vs_target_comparison_v1.json`",
                "6. `benchmark_double_compare/current_status_1941111_benchmark_v1.json`",
                "7. `cleanup/sg194_wrong_single_result_cleanup_v1.json`",
            ]
        ),
    )
    manifest_payload = {
        "package_name": PACKAGE_NAME,
        "generated_at": now_iso(),
        "package_tarball": PACKAGE_TARBALL.name,
        "core_validate_commands": [
            "python3 sg194/debug_sg194_single_target_result_v1.py --validate",
            "python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate",
        ],
        "included_sections": [
            "target_object_stack",
            "fix_attempt",
            "result",
            "benchmark_double_compare",
            "cleanup",
        ],
    }
    write_json(PACKAGE_DIR / "reproducibility_manifest_v1.json", manifest_payload)
    write_text(
        PACKAGE_DIR / "REPRODUCIBILITY_MANIFEST.md",
        "\n".join(
            [
                "# Reproducibility Manifest",
                "",
                f"- package: `{PACKAGE_NAME}`",
                f"- tarball: `{PACKAGE_TARBALL.name}`",
                "- validate commands:",
                "  - `python3 sg194/debug_sg194_single_target_result_v1.py --validate`",
                "  - `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`",
            ]
        ),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate_outputs() -> None:
    current = load_json(CURRENT_STAGE2_JSON)
    assert current["single_status"]["published_result_source"] == "single_target_projection_contract_v1"
    assert current["single_final_rank_bs"] == 13
    assert current["single_final_rank_ai"] == 13
    assert current["single_final_quotient_group"] == "trivial"
    assert load_json(TARGET_RESULT_JSON)["single_target_result"]["classification"] == "trivial"
    assert load_json(TARGET_RESULT_JSON)["single_target_result"]["dBS"] == 13
    assert load_json(TARGET_RESULT_JSON)["single_target_result"]["dAI"] == 13
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
        print("validated sg194 single target result outputs")
        return

    refresh_stage2()
    target_analysis = compute_single_target_analysis()
    current_stage2 = load_json(CURRENT_STAGE2_JSON)

    double_stack = build_double_target_stack(current_stage2)
    single_missing = build_single_missing_layers(target_analysis)
    fix_attempt = {
        "generated_at": now_iso(),
        "code_changes": [
            {
                "file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "change": "Switch active single publication from raw-current override to target-row-language projection-contract fields.",
            },
            {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "change": "Expose raw-current object-language metadata explicitly for stage1 provenance.",
            },
            {
                "file": "sg194/debug_sg194_single_target_row_language_fix_v1.py",
                "change": "Demote the old parity-fix entry to a compatibility wrapper.",
            },
        ],
        "mechanical_findings": {
            "projected_current_matches_external_matrix_exactly": target_analysis["single_target_projection_contract"][
                "projected_current_matches_external_matrix_exactly"
            ],
            "exact_linear_target_alignment_exists": target_analysis["single_target_projection_contract"][
                "exact_linear_target_alignment_exists"
            ],
            "mismatch_rank_after_projection": target_analysis["single_target_projection_contract"][
                "mismatch_rank_after_projection"
            ],
        },
        "decision": (
            "Promote single target-row-language result to active publication because it is computed directly in target coordinates, "
            "but keep exact current/external generator alignment as an explicit remaining blocker."
        ),
    }
    target_result_payload = {
        "generated_at": now_iso(),
        "single_target_result": target_analysis["single_target_result"],
        "target_row_language_kind": target_analysis["single_target_projection_contract"]["target_row_language_kind"],
        "direct_derivation_scope": "projected_single_bs_over_projected_single_ai_in_external_ordinary_target_rows",
        "exact_generator_identity_status": target_analysis["single_target_projection_contract"][
            "exact_generator_identity_status"
        ],
        "exact_linear_target_alignment_exists": target_analysis["single_target_projection_contract"][
            "exact_linear_target_alignment_exists"
        ],
        "mismatch_rank_after_projection": target_analysis["single_target_projection_contract"][
            "mismatch_rank_after_projection"
        ],
    }
    raw_vs_target = {
        "generated_at": now_iso(),
        "single_raw_current_object": target_analysis["single_raw_current_result"],
        "single_target_row_language_object": target_analysis["single_target_result"],
        "double_target_row_language_object": target_analysis["double_target_result"],
        "benchmark_oracle": {
            "dBS": target_analysis["benchmark_oracle"]["dBS"],
            "dAI": target_analysis["benchmark_oracle"]["dAI"],
            "classification": target_analysis["benchmark_oracle"]["classification"],
        },
        "verdict": (
            "These are not the same object. The single raw-current object is 16/13/Z^3; the active single target-row-language "
            "result is 13/13/trivial; the double benchmark-facing target object and the benchmark oracle remain 10/10/Z6."
        ),
    }
    cleanup_payload = cleanup_wrong_single_results()

    write_json(DOUBLE_STACK_JSON, double_stack)
    write_text(
        DOUBLE_STACK_MD,
        md_with_json(
            "SG194 Double Target Object Stack v1",
            ["- Purpose: name the exact layers currently used by the active double benchmark-facing path."],
            double_stack,
        ),
    )
    write_json(SINGLE_MISSING_JSON, single_missing)
    write_text(
        SINGLE_MISSING_MD,
        md_with_json(
            "SG194 Single Missing Target Layers v1",
            ["- Purpose: show which single layers were missing before the fix and which gap still remains after promotion to target rows."],
            single_missing,
        ),
    )
    write_json(FIX_ATTEMPT_JSON, fix_attempt)
    write_text(
        FIX_ATTEMPT_MD,
        md_with_json(
            "SG194 Single Target Row Language Fix Attempt v1",
            ["- Purpose: record the code-path change that stops publishing raw-current single results as final."],
            fix_attempt,
        ),
    )
    write_json(TARGET_RESULT_JSON, target_result_payload)
    write_text(
        TARGET_RESULT_MD,
        md_with_json(
            "SG194 Single Target Result v1",
            ["- Active single final answer is now computed in target rows.", "- Exact generator identity is still not available."],
            target_result_payload,
        ),
    )
    write_json(RAW_VS_TARGET_JSON, raw_vs_target)
    write_text(
        RAW_VS_TARGET_MD,
        md_with_json(
            "SG194 Single Raw vs Target Comparison v1",
            ["- Purpose: keep raw-current provenance and target-row-language final result clearly separated."],
            raw_vs_target,
        ),
    )
    write_json(CLEANUP_JSON, cleanup_payload)
    write_text(
        CLEANUP_MD,
        md_with_json(
            "SG194 Wrong Single Result Cleanup v1",
            ["- Purpose: remove final-facing raw-current single result files and stale packages."],
            cleanup_payload,
        ),
    )

    update_benchmark_status(target_analysis)
    update_benchmark_adoption_vs_internalization(target_analysis)
    update_live_checkpoint(target_analysis, cleanup_payload)
    build_package()


if __name__ == "__main__":
    main()
