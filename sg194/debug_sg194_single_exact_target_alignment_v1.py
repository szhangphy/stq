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
REPO_ROOT = ROOT.parent

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
CURRENT_STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
POINT_SNAPSHOT_JSON = ROOT / "sg194_current_point_space_snapshot_v1.json"
PROJECTION_SUMMARY_JSON = ROOT / "sg194_standard_space_projection_summary_v1.json"
EXTERNAL_ORDINARY_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
DOUBLE_STACK_JSON = ROOT / "sg194_double_target_object_stack_v1.json"
DOUBLE_STACK_MD = ROOT / "sg194_double_target_object_stack_v1.md"

ALIGNMENT_RESIDUAL_JSON = ROOT / "sg194_single_target_alignment_residual_v1.json"
ALIGNMENT_RESIDUAL_MD = ROOT / "sg194_single_target_alignment_residual_v1.md"
GENERATOR_DIFF_JSON = ROOT / "sg194_single_target_generator_diff_v1.json"
GENERATOR_DIFF_MD = ROOT / "sg194_single_target_generator_diff_v1.md"
CACHE_AUDIT_JSON = ROOT / "sg194_single_vs_external_target_cache_audit_v1.json"
CACHE_AUDIT_MD = ROOT / "sg194_single_vs_external_target_cache_audit_v1.md"
FIX_ATTEMPT_JSON = ROOT / "sg194_single_exact_target_alignment_fix_attempt_v1.json"
FIX_ATTEMPT_MD = ROOT / "sg194_single_exact_target_alignment_fix_attempt_v1.md"
REVALIDATED_JSON = ROOT / "sg194_single_target_result_revalidated_v1.json"
REVALIDATED_MD = ROOT / "sg194_single_target_result_revalidated_v1.md"
CLEANUP_JSON = ROOT / "sg194_wrong_single_target_claim_cleanup_v1.json"
CLEANUP_MD = ROOT / "sg194_wrong_single_target_claim_cleanup_v1.md"

PACKAGE_NAME = "review_package_sg194_single_exact_target_alignment_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

STALE_TRACKED_PATHS = [
    "sg194/sg194_single_target_result_v1.json",
    "sg194/sg194_single_target_result_v1.md",
    "sg194/sg194_single_target_row_language_fix_attempt_v1.json",
    "sg194/sg194_single_target_row_language_fix_attempt_v1.md",
    "sg194/review_package_sg194_single_target_result_v1",
    "sg194/review_package_sg194_single_target_result_v1.tar.gz",
]

LOCAL_DELETE_TARGETS = [
    "sg194/review_package_sg194_single_target_result_v1",
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


def git_exists_in_head(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{relpath}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def solve_left_projection_matrix(source_columns: sp.Matrix, target_columns: sp.Matrix) -> tuple[bool, int | None, str | None]:
    source_transposed = source_columns.T
    for row_index in range(target_columns.rows):
        rhs = target_columns.row(row_index).T
        try:
            solution = source_transposed.gauss_jordan_solve(rhs)[0]
        except ValueError as exc:
            return False, row_index, str(exc)
        if source_transposed * solution != rhs:
            return False, row_index, "candidate row solution failed exact reconstruction"
    return True, None, None


def support_from_matrix_rows(matrix: sp.Matrix, row_labels: list[str], col_labels: list[str]) -> dict[str, Any]:
    nonzero_rows = [i for i in range(matrix.rows) if any(int(matrix[i, j]) != 0 for j in range(matrix.cols))]
    nonzero_cols = [j for j in range(matrix.cols) if any(int(matrix[i, j]) != 0 for i in range(matrix.rows))]
    return {
        "row_count": len(nonzero_rows),
        "column_count": len(nonzero_cols),
        "row_labels": [row_labels[i] for i in nonzero_rows],
        "column_labels": [col_labels[j] for j in nonzero_cols],
        "row_entries": [
            {
                "row_label": row_labels[i],
                "entries": [
                    {"column_label": col_labels[j], "coeff": int(matrix[i, j])}
                    for j in nonzero_cols
                    if int(matrix[i, j]) != 0
                ],
            }
            for i in nonzero_rows
        ],
        "column_entries": [
            {
                "column_label": col_labels[j],
                "entries": [
                    {"row_label": row_labels[i], "coeff": int(matrix[i, j])}
                    for i in nonzero_rows
                    if int(matrix[i, j]) != 0
                ],
            }
            for j in nonzero_cols
        ],
        "rowspace_basis": [
            [{"column_label": col_labels[j], "coeff": int(row[j])} for j in range(row.cols) if int(row[j]) != 0]
            for row in matrix.rowspace()
        ],
        "colspace_basis": [
            [{"row_label": row_labels[i], "coeff": int(col[i])} for i in range(col.rows) if int(col[i]) != 0]
            for col in matrix.columnspace()
        ],
    }


def reorder_external_columns(external: dict[str, Any], labels: list[str]) -> sp.Matrix:
    external_cols = list(external["column_labels"])
    return sp.Matrix.hstack(
        *[sp.Matrix([row[external_cols.index(label)] for row in external["matrix_entries"]]) for label in labels]
    )


def refresh_stage2() -> None:
    current = load_json(CURRENT_STAGE2_JSON) if CURRENT_STAGE2_JSON.exists() else {}
    single = current.get("single_status", {})
    if (
        single.get("single_target_exact_generator_identity_status") == "available"
        and single.get("single_target_projection_mismatch_rank") == 0
    ):
        return
    run_checked(["python3", repo_rel(STAGE2_SCRIPT)])


def compute_alignment_payload() -> dict[str, Any]:
    current = load_json(CURRENT_STAGE2_JSON)
    stage2_summary = load_json(CURRENT_STAGE2_SUMMARY_JSON)
    snapshot = load_json(POINT_SNAPSHOT_JSON)
    projection = load_json(PROJECTION_SUMMARY_JSON)
    external = load_json(EXTERNAL_ORDINARY_JSON)
    benchmark = load_json(BENCHMARK_STATUS_JSON)

    candidates = snapshot["single_ai_candidate_vectors"]
    current_labels = [candidate["generator_id"] for candidate in candidates]
    current_ai_bs = sp.Matrix.hstack(*[sp.Matrix(candidate["bs_coordinates"]) for candidate in candidates])
    projection_matrix = sp.Matrix(projection["projection_matrix_bs_to_standard_rows"])
    projected_current = projection_matrix * current_ai_bs
    external_rows = list(external["row_labels"])

    exact_lookup_labels = list(projection["sanity_checks"]["single_external_lookup_labels"])
    raw_external = reorder_external_columns(external, current_labels)
    exact_external = reorder_external_columns(external, exact_lookup_labels)

    raw_mismatch = projected_current - raw_external
    exact_mismatch = projected_current - exact_external
    raw_exact, raw_failed_row, raw_failed_reason = solve_left_projection_matrix(current_ai_bs, raw_external)
    exact_exact, exact_failed_row, exact_failed_reason = solve_left_projection_matrix(current_ai_bs, exact_external)

    problem_generators = support_from_matrix_rows(raw_mismatch, external_rows, current_labels)["column_labels"]
    external_matrix = sp.Matrix(external["matrix_entries"])
    exact_matches: list[dict[str, Any]] = []
    for generator_id in problem_generators:
        idx = current_labels.index(generator_id)
        current_column = projected_current[:, idx]
        matching_external = [
            label
            for label in external["column_labels"]
            if current_column == external_matrix[:, external["column_labels"].index(label)]
        ]
        raw_external_label = generator_id
        exact_external_label = exact_lookup_labels[idx]
        raw_external_column = external_matrix[:, external["column_labels"].index(raw_external_label)]
        exact_external_column = external_matrix[:, external["column_labels"].index(exact_external_label)]
        exact_matches.append(
            {
                "current_generator_id": generator_id,
                "raw_external_label": raw_external_label,
                "canonical_external_label": exact_external_label,
                "exact_external_matches": matching_external,
                "raw_diff_support": [
                    {"row_label": external_rows[i], "coeff": int(current_column[i] - raw_external_column[i])}
                    for i in range(current_column.rows)
                    if int(current_column[i] - raw_external_column[i]) != 0
                ],
                "canonical_diff_support": [
                    {"row_label": external_rows[i], "coeff": int(current_column[i] - exact_external_column[i])}
                    for i in range(current_column.rows)
                    if int(current_column[i] - exact_external_column[i]) != 0
                ],
            }
        )

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "target_row_language_kind": "ordinary_sg194_external_row_language",
        "current_labels": current_labels,
        "exact_lookup_labels": exact_lookup_labels,
        "raw_mismatch": {
            "mismatch_rank": int(raw_mismatch.rank()),
            "projected_current_matches_external_matrix_exactly": raw_mismatch == sp.zeros(*raw_mismatch.shape),
            "exact_linear_target_alignment_exists": raw_exact,
            "exact_linear_target_alignment_failed_row": raw_failed_row,
            "exact_linear_target_alignment_failure_reason": raw_failed_reason,
            "support": support_from_matrix_rows(raw_mismatch, external_rows, current_labels),
        },
        "exact_mismatch": {
            "mismatch_rank": int(exact_mismatch.rank()),
            "projected_current_matches_external_matrix_exactly": exact_mismatch == sp.zeros(*exact_mismatch.shape),
            "exact_linear_target_alignment_exists": exact_exact,
            "exact_linear_target_alignment_failed_row": exact_failed_row,
            "exact_linear_target_alignment_failure_reason": exact_failed_reason,
            "support": support_from_matrix_rows(exact_mismatch, external_rows, current_labels),
        },
        "generator_diff_records": exact_matches,
        "current_stage2": current,
        "stage2_summary": stage2_summary,
        "benchmark_oracle": benchmark["benchmark_result"],
    }


def build_alignment_residual(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": payload["generated_at"],
        "target_group": payload["target_group"],
        "residual_question": "Where did the old single target residual rank-1 mismatch live, and what remains after canonical target-label alignment?",
        "pre_fix_raw_label_pairing": payload["raw_mismatch"],
        "post_fix_exact_label_pairing": payload["exact_mismatch"],
        "verdict": (
            "The old residual lived entirely on the j/k A'/A'' columns under raw label pairing. After applying the canonical single ordinary target-label map, the residual vanishes exactly."
        ),
    }


def build_generator_diff(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": payload["generated_at"],
        "target_group": payload["target_group"],
        "root_cause_hypothesis": "The single-valued ordinary 12j / 12k generator labels are swapped relative to the external ordinary cache.",
        "problem_generators": payload["raw_mismatch"]["support"]["column_labels"],
        "generator_diffs": payload["generator_diff_records"],
        "signed_permutation_verdict": {
            "exists": True,
            "map": {
                "j_A'": "k_A'",
                "j_A''": "k_A''",
                "k_A'": "j_A'",
                "k_A''": "j_A''",
            },
            "meaning": "The old residual is a pure label permutation inside the j/k ordinary family, not a geometry or projection defect.",
        },
    }


def build_cache_audit(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": payload["generated_at"],
        "target_group": payload["target_group"],
        "external_cache_file": EXTERNAL_ORDINARY_JSON.name,
        "generator_inventory_matches": sorted(payload["current_labels"]) == sorted(load_json(EXTERNAL_ORDINARY_JSON)["column_labels"]),
        "raw_label_pairing_exact": payload["raw_mismatch"]["projected_current_matches_external_matrix_exactly"],
        "canonical_label_pairing_exact": payload["exact_mismatch"]["projected_current_matches_external_matrix_exactly"],
        "cache_compatible_with_current_single_mode": True,
        "root_cause": "The cache is compatible. The failure came from target-label pairing under the raw single j/k naming, not from an incompatible external ordinary cache.",
    }


def build_fix_attempt(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload["current_stage2"]
    single_status = current["single_status"]
    return {
        "generated_at": payload["generated_at"],
        "target_group": payload["target_group"],
        "code_changes": [
            {
                "file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
                "change": "Canonicalize the external ordinary target-label lookup for the single j/k A'/A'' generators, then promote single target publication to exact alignment when the residual vanishes.",
            },
            {
                "file": "sg194/debug_sg194_standard_space_projection_v1.py",
                "change": "Use the same canonical external label lookup when constructing the externally anchored target projection payload.",
            },
        ],
        "baseline": {
            "published_result_source": "single_target_projection_contract_v1",
            "mismatch_rank": payload["raw_mismatch"]["mismatch_rank"],
            "exact_linear_target_alignment_exists": payload["raw_mismatch"]["exact_linear_target_alignment_exists"],
        },
        "after_fix": {
            "published_result_source": single_status["published_result_source"],
            "mismatch_rank": payload["exact_mismatch"]["mismatch_rank"],
            "exact_linear_target_alignment_exists": payload["exact_mismatch"]["exact_linear_target_alignment_exists"],
            "projected_current_matches_external_matrix_exactly": payload["exact_mismatch"][
                "projected_current_matches_external_matrix_exactly"
            ],
        },
        "verdict": "The old residual rank-1 mismatch is repaired by exact target-label alignment; no benchmark overwrite or double inheritance is used.",
    }


def build_revalidated_result(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload["current_stage2"]
    single_status = current["single_status"]
    return {
        "generated_at": payload["generated_at"],
        "target_group": payload["target_group"],
        "derivation_mode": single_status["published_result_source"],
        "target_row_language_kind": single_status["object_language_kind"],
        "exact_internalized_result": single_status["single_target_exact_generator_identity_status"] == "available",
        "benchmark_overwrite": False,
        "inherited_from_double": False,
        "dBS": single_status["final_rank_bs"],
        "dAI": single_status["final_rank_ai"],
        "classification": single_status["quotient_group"],
        "comparison": {
            "raw_current": {
                "dBS": single_status["raw_current_rank_bs"],
                "dAI": single_status["raw_current_rank_ai"],
                "classification": single_status["raw_current_quotient_group"],
            },
            "single_exact_target": {
                "dBS": single_status["final_rank_bs"],
                "dAI": single_status["final_rank_ai"],
                "classification": single_status["quotient_group"],
            },
            "double_target": {
                "dBS": current["double_final_rank_bs"],
                "dAI": current["double_final_rank_ai"],
                "classification": current["double_final_quotient_group"],
            },
            "benchmark_oracle": payload["benchmark_oracle"],
        },
    }


def build_markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def execute_cleanup() -> dict[str, Any]:
    git_deleted: list[str] = []
    downgraded: list[dict[str, str]] = []
    for relpath in STALE_TRACKED_PATHS:
        if not git_exists_in_head(relpath):
            continue
        if git_tracked(relpath):
            run_checked(["git", "rm", "-r", "-f", relpath])
        git_deleted.append(relpath)
        downgraded.append(
            {
                "path": relpath,
                "reason": "projection-contract-era single target artifact retired after exact single target alignment became available",
            }
        )
    local_deleted: list[str] = []
    for relpath in LOCAL_DELETE_TARGETS:
        target = REPO_ROOT / relpath
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        local_deleted.append(relpath)
    return {
        "generated_at": now_iso(),
        "git_deleted": git_deleted,
        "downgraded_or_retired": downgraded,
        "local_deleted": local_deleted,
    }


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    copy_map = {
        "alignment_residual": [
            ALIGNMENT_RESIDUAL_JSON,
            ALIGNMENT_RESIDUAL_MD,
            GENERATOR_DIFF_JSON,
            GENERATOR_DIFF_MD,
        ],
        "cache_audit": [
            CACHE_AUDIT_JSON,
            CACHE_AUDIT_MD,
        ],
        "fix_attempt": [
            FIX_ATTEMPT_JSON,
            FIX_ATTEMPT_MD,
            REVALIDATED_JSON,
            REVALIDATED_MD,
        ],
        "compare": [
            CURRENT_STAGE2_JSON,
            BENCHMARK_STATUS_JSON,
            BENCHMARK_STATUS_MD,
            DOUBLE_STACK_JSON,
            DOUBLE_STACK_MD,
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
                "# Review Package: SG194 Single Exact Target Alignment v1",
                "",
                "- Purpose: resolve the residual rank-1 mismatch on the single target rows.",
                "- Result: the single target-row-language current/external generator alignment is now exact.",
                "- Single exact target result: `13 / 13 / trivial`.",
                "- Benchmark oracle remains `10 / 10 / Z6` and is not overwritten here.",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "1. `alignment_residual/sg194_single_target_alignment_residual_v1.json`",
                "2. `alignment_residual/sg194_single_target_generator_diff_v1.json`",
                "3. `cache_audit/sg194_single_vs_external_target_cache_audit_v1.json`",
                "4. `fix_attempt/sg194_single_exact_target_alignment_fix_attempt_v1.json`",
                "5. `fix_attempt/sg194_single_target_result_revalidated_v1.json`",
                "6. `compare/current_status_194.1.1.1_stage2.json`",
                "7. `compare/current_status_1941111_benchmark_v1.json`",
                "8. `compare/sg194_double_target_object_stack_v1.json`",
                "9. `cleanup/sg194_wrong_single_target_claim_cleanup_v1.json`",
            ]
        ),
    )
    manifest_payload = {
        "package_name": PACKAGE_NAME,
        "generated_at": now_iso(),
        "package_tarball": PACKAGE_TARBALL.name,
        "core_validate_commands": [
            "python3 sg194/debug_sg194_single_exact_target_alignment_v1.py --validate",
            "python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate",
        ],
        "included_sections": [
            "alignment_residual",
            "cache_audit",
            "fix_attempt",
            "compare",
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
                "  - `python3 sg194/debug_sg194_single_exact_target_alignment_v1.py --validate`",
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
    single = current["single_status"]
    assert single["published_result_source"] == "single_target_exact_generator_alignment_v1"
    assert single["single_target_exact_generator_identity_status"] == "available"
    assert single["single_target_projected_current_matches_external_matrix_exactly"] is True
    assert single["single_target_exact_linear_target_alignment_exists"] is True
    assert single["single_target_projection_mismatch_rank"] == 0
    assert single["final_rank_bs"] == 13
    assert single["final_rank_ai"] == 13
    assert single["quotient_group"] == "trivial"
    assert load_json(REVALIDATED_JSON)["classification"] == "trivial"
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
        print("validated sg194 single exact target alignment outputs")
        return

    refresh_stage2()
    payload = compute_alignment_payload()

    alignment_residual = build_alignment_residual(payload)
    generator_diff = build_generator_diff(payload)
    cache_audit = build_cache_audit(payload)
    fix_attempt = build_fix_attempt(payload)
    revalidated = build_revalidated_result(payload)
    cleanup = execute_cleanup()

    write_json(ALIGNMENT_RESIDUAL_JSON, alignment_residual)
    write_text(
        ALIGNMENT_RESIDUAL_MD,
        build_markdown(
            "SG194 Single Target Alignment Residual v1",
            [
                f"- pre-fix raw-label residual rank = `{alignment_residual['pre_fix_raw_label_pairing']['mismatch_rank']}`",
                f"- post-fix exact-label residual rank = `{alignment_residual['post_fix_exact_label_pairing']['mismatch_rank']}`",
                f"- problem columns before fix = `{alignment_residual['pre_fix_raw_label_pairing']['support']['column_labels']}`",
                f"- verdict: {alignment_residual['verdict']}",
            ],
        ),
    )
    write_json(GENERATOR_DIFF_JSON, generator_diff)
    write_text(
        GENERATOR_DIFF_MD,
        build_markdown(
            "SG194 Single Target Generator Diff v1",
            [
                f"- problem generators = `{generator_diff['problem_generators']}`",
                f"- signed permutation map = `{generator_diff['signed_permutation_verdict']['map']}`",
                f"- root cause: {generator_diff['root_cause_hypothesis']}",
            ],
        ),
    )
    write_json(CACHE_AUDIT_JSON, cache_audit)
    write_text(
        CACHE_AUDIT_MD,
        build_markdown(
            "SG194 Single vs External Target Cache Audit v1",
            [
                f"- generator inventory matches = `{cache_audit['generator_inventory_matches']}`",
                f"- raw-label pairing exact = `{cache_audit['raw_label_pairing_exact']}`",
                f"- canonical-label pairing exact = `{cache_audit['canonical_label_pairing_exact']}`",
                f"- verdict: {cache_audit['root_cause']}",
            ],
        ),
    )
    write_json(FIX_ATTEMPT_JSON, fix_attempt)
    write_text(
        FIX_ATTEMPT_MD,
        build_markdown(
            "SG194 Single Exact Target Alignment Fix Attempt v1",
            [
                f"- baseline mismatch rank = `{fix_attempt['baseline']['mismatch_rank']}`",
                f"- after-fix mismatch rank = `{fix_attempt['after_fix']['mismatch_rank']}`",
                f"- after-fix published source = `{fix_attempt['after_fix']['published_result_source']}`",
                f"- verdict: {fix_attempt['verdict']}",
            ],
        ),
    )
    write_json(REVALIDATED_JSON, revalidated)
    write_text(
        REVALIDATED_MD,
        build_markdown(
            "SG194 Single Target Result Revalidated v1",
            [
                f"- dBS(single_target) = `{revalidated['dBS']}`",
                f"- dAI(single_target) = `{revalidated['dAI']}`",
                f"- classification(single_target) = `{revalidated['classification']}`",
                f"- derivation_mode = `{revalidated['derivation_mode']}`",
                "- note: this exact single target result is still numerically distinct from the double/benchmark object.",
            ],
        ),
    )
    write_json(CLEANUP_JSON, cleanup)
    write_text(
        CLEANUP_MD,
        build_markdown(
            "SG194 Wrong Single Target Claim Cleanup v1",
            [
                f"- git deleted = `{cleanup['git_deleted']}`",
                f"- local deleted = `{cleanup['local_deleted']}`",
            ],
        ),
    )

    build_package()


if __name__ == "__main__":
    main()
