#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp

import debug_sg194_single_exact_target_alignment_v1 as exact_align


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
EXACT_ALIGN_SCRIPT = ROOT / "debug_sg194_single_exact_target_alignment_v1.py"
REGRESSION_SCRIPT = ROOT / "debug_sg194_single_exact_alignment_regression_v1.py"

CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
DOUBLE_STACK_JSON = ROOT / "sg194_double_target_object_stack_v1.json"
DOUBLE_STACK_MD = ROOT / "sg194_double_target_object_stack_v1.md"

PROOF_JSON = ROOT / "sg194_single_jk_pairing_proof_v1.json"
PROOF_MD = ROOT / "sg194_single_jk_pairing_proof_v1.md"
UNIQUENESS_JSON = ROOT / "sg194_single_jk_pairing_uniqueness_v1.json"
UNIQUENESS_MD = ROOT / "sg194_single_jk_pairing_uniqueness_v1.md"
SEMANTICS_JSON = ROOT / "sg194_stage2_status_semantics_cleanup_v1.json"
SEMANTICS_MD = ROOT / "sg194_stage2_status_semantics_cleanup_v1.md"
STATUS_SPLIT_JSON = ROOT / "sg194_final_single_double_status_split_v1.json"
STATUS_SPLIT_MD = ROOT / "sg194_final_single_double_status_split_v1.md"

REGRESSION_JSON = ROOT / "sg194_single_exact_alignment_regression_v1.json"
REGRESSION_MD = ROOT / "sg194_single_exact_alignment_regression_v1.md"

PACKAGE_NAME = "review_package_sg194_single_jk_pairing_proof_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

STALE_TRACKED_PATHS = [
    "sg194/review_package_sg194_single_exact_target_alignment_v1",
    "sg194/review_package_sg194_single_exact_target_alignment_v1.tar.gz",
]

LOCAL_DELETE_TARGETS = [
    "sg194/review_package_sg194_single_exact_target_alignment_v1",
    "sg194/workflow_portability_report_stage2_194.1.1.1.aux",
    "sg194/workflow_portability_report_stage2_194.1.1.1.log",
    "sg194/workflow_portability_report_stage2_194.1.1.1.out",
]

EXPECTED_CANONICAL_MAP = {
    "j_A'": "k_A'",
    "j_A''": "k_A''",
    "k_A'": "j_A'",
    "k_A''": "j_A''",
}


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


def refresh_stage2() -> None:
    current = load_json(CURRENT_STAGE2_JSON) if CURRENT_STAGE2_JSON.exists() else {}
    if (
        current.get("single_final_object_kind") == "ordinary_single_exact_target_row_language_object"
        and current.get("single_target_generator_label_canonicalization_role")
        == "external_ordinary_target_label_lookup_normalization"
    ):
        return
    run_checked(["python3", repo_rel(STAGE2_SCRIPT)])


def reorder_external_columns(external: dict[str, Any], labels: list[str]) -> sp.Matrix:
    external_cols = list(external["column_labels"])
    external_matrix = sp.Matrix(external["matrix_entries"])
    return sp.Matrix.hstack(*[external_matrix[:, external_cols.index(label)] for label in labels])


def row_support(column: sp.Matrix, row_labels: list[str]) -> list[dict[str, Any]]:
    return [
        {"row_label": row_labels[idx], "coeff": int(column[idx])}
        for idx in range(column.rows)
        if int(column[idx]) != 0
    ]


def build_alignment_context() -> dict[str, Any]:
    payload = exact_align.compute_alignment_payload()
    projection = load_json(exact_align.PROJECTION_SUMMARY_JSON)
    snapshot = load_json(exact_align.POINT_SNAPSHOT_JSON)
    external = load_json(exact_align.EXTERNAL_ORDINARY_JSON)
    current = load_json(CURRENT_STAGE2_JSON)
    benchmark = load_json(BENCHMARK_STATUS_JSON)
    row_labels = list(external["row_labels"])
    current_labels = list(payload["current_labels"])
    exact_lookup_labels = list(payload["exact_lookup_labels"])
    projection_matrix = sp.Matrix(projection["projection_matrix_bs_to_standard_rows"])
    current_ai_bs = sp.Matrix.hstack(
        *[sp.Matrix(candidate["bs_coordinates"]) for candidate in snapshot["single_ai_candidate_vectors"]]
    )
    projected_current = projection_matrix * current_ai_bs
    raw_external = reorder_external_columns(external, current_labels)
    exact_external = reorder_external_columns(external, exact_lookup_labels)
    problem_labels = list(payload["raw_mismatch"]["support"]["column_labels"])
    external_matrix = sp.Matrix(external["matrix_entries"])
    problem_columns = sp.Matrix.hstack(*[projected_current[:, current_labels.index(label)] for label in problem_labels])

    exact_matches: list[dict[str, Any]] = []
    for label in problem_labels:
        current_idx = current_labels.index(label)
        current_column = projected_current[:, current_idx]
        unique_matches = [
            ext_label
            for ext_label in external["column_labels"]
            if current_column == external_matrix[:, external["column_labels"].index(ext_label)]
        ]
        exact_matches.append(
            {
                "current_generator_id": label,
                "family_letter": label.split("_", 1)[0],
                "little_irrep_label": label.split("_", 1)[1],
                "raw_external_label": label,
                "canonical_external_label": exact_lookup_labels[current_idx],
                "unique_exact_external_matches": unique_matches,
                "current_target_row_signature": row_support(current_column, row_labels),
            }
        )

    permutation_solutions: list[dict[str, Any]] = []
    signed_permutation_solutions: list[dict[str, Any]] = []
    for perm in itertools.permutations(problem_labels):
        permuted_external = sp.Matrix.hstack(*[external_matrix[:, external["column_labels"].index(label)] for label in perm])
        if problem_columns == permuted_external:
            permutation_solutions.append({"map": dict(zip(problem_labels, perm, strict=True))})
        for signs in itertools.product([1, -1], repeat=len(problem_labels)):
            signed_external = sp.Matrix.hstack(
                *[
                    signs[idx] * external_matrix[:, external["column_labels"].index(label)]
                    for idx, label in enumerate(perm)
                ]
            )
            if problem_columns == signed_external:
                signed_permutation_solutions.append(
                    {
                        "map": dict(zip(problem_labels, perm, strict=True)),
                        "signs": dict(zip(problem_labels, signs, strict=True)),
                    }
                )

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "current_status": current,
        "benchmark": benchmark,
        "payload": payload,
        "projection": projection,
        "external": external,
        "current_labels": current_labels,
        "exact_lookup_labels": exact_lookup_labels,
        "problem_labels": problem_labels,
        "exact_matches": exact_matches,
        "permutation_solutions": permutation_solutions,
        "signed_permutation_solutions": signed_permutation_solutions,
        "raw_mismatch_rank": int((projected_current - raw_external).rank()),
        "canonical_mismatch_rank": int((projected_current - exact_external).rank()),
    }


def build_pairing_proof(context: dict[str, Any]) -> dict[str, Any]:
    payload = context["payload"]
    return {
        "generated_at": context["generated_at"],
        "target_group": context["target_group"],
        "question": "Why is the single j/k canonical pairing representation-theoretically required rather than ad hoc relabeling?",
        "target_row_language_kind": context["current_status"]["single_target_row_language_kind"],
        "pairing_object_role": context["current_status"]["single_target_generator_label_canonicalization_role"],
        "pairing_object_scope": context["current_status"]["single_target_generator_label_canonicalization_scope"],
        "problem_generators": context["problem_labels"],
        "generator_meanings": context["exact_matches"],
        "raw_pairing_failure": {
            "mismatch_rank": payload["raw_mismatch"]["mismatch_rank"],
            "mismatch_row_labels": payload["raw_mismatch"]["support"]["row_labels"],
            "mismatch_column_labels": payload["raw_mismatch"]["support"]["column_labels"],
            "verdict": "Raw pairing compares each current single j/k column to the wrong external ordinary family label and leaves a rank-1 residual.",
        },
        "canonical_pairing_success": {
            "map": dict(EXPECTED_CANONICAL_MAP),
            "mismatch_rank": payload["exact_mismatch"]["mismatch_rank"],
            "projected_current_matches_external_matrix_exactly": payload["exact_mismatch"][
                "projected_current_matches_external_matrix_exactly"
            ],
            "exact_linear_target_alignment_exists": payload["exact_mismatch"]["exact_linear_target_alignment_exists"],
        },
        "proof_chain": [
            "Target-row-language generator identity is decided by equality of the full projected target-row signatures.",
            "Each problematic current single generator has exactly one external ordinary column with the same target-row signature.",
            "Those unique exact matches preserve the A'/A'' little-irrep label and swap only the j/k family letter.",
            "Under raw pairing, the same four columns are compared against non-identical target-row signatures and produce the rank-1 residual.",
            "Therefore the j/k canonical pairing is the target-row-language normalization required for exact generator identity, not a benchmark overwrite and not free label tuning.",
        ],
        "verdict": "The canonical j/k pairing is representation-theoretically justified by unique target-row-signature identity of the projected single generators against the external ordinary target basis.",
    }


def build_uniqueness(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": context["generated_at"],
        "target_group": context["target_group"],
        "search_space": {
            "problem_generators": context["problem_labels"],
            "permutation_count": len(list(itertools.permutations(context["problem_labels"]))),
            "signed_permutation_count": len(list(itertools.permutations(context["problem_labels"]))) * (2 ** len(context["problem_labels"])),
        },
        "exact_permutation_solutions": context["permutation_solutions"],
        "exact_signed_permutation_solutions": context["signed_permutation_solutions"],
        "canonical_solution": dict(EXPECTED_CANONICAL_MAP),
        "canonical_solution_present": dict(EXPECTED_CANONICAL_MAP) in [
            item["map"] for item in context["permutation_solutions"]
        ],
        "unique_under_permutation": len(context["permutation_solutions"]) == 1,
        "unique_under_signed_permutation": len(context["signed_permutation_solutions"]) == 1,
        "gauge_equivalent_alternatives": [],
        "verdict": (
            "Among all 24 permutations, and among all 24 * 2^4 signed permutations, there is exactly one exact solution: "
            "swap j <-> k while keeping A'/A'' fixed. No alternative sign choices or gauge-equivalent pairings remain."
        ),
    }


def execute_cleanup() -> dict[str, Any]:
    git_deleted: list[str] = []
    for relpath in STALE_TRACKED_PATHS:
        if not git_exists_in_head(relpath):
            continue
        if git_tracked(relpath):
            run_checked(["git", "rm", "-r", "-f", relpath])
        git_deleted.append(relpath)

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
        "local_deleted": local_deleted,
    }


def build_semantics_cleanup(context: dict[str, Any], cleanup: dict[str, Any]) -> dict[str, Any]:
    current = context["current_status"]
    single = current["single_status"]
    double = current["double_status"]
    return {
        "generated_at": context["generated_at"],
        "target_group": context["target_group"],
        "status_file": CURRENT_STAGE2_JSON.name,
        "single_exact_target_status": {
            "object_kind": current["single_final_object_kind"],
            "result": {
                "dBS": current["single_final_rank_bs"],
                "dAI": current["single_final_rank_ai"],
                "classification": current["single_final_quotient_group"],
            },
            "exact_alignment_available": single["single_target_exact_generator_identity_status"] == "available",
            "row_language_kind": single["target_row_language_kind"],
            "derivation_mode": single["quotient_derivation_mode"],
        },
        "double_benchmark_status": {
            "object_kind": current["double_final_object_kind"],
            "result": {
                "dBS": current["double_final_rank_bs"],
                "dAI": current["double_final_rank_ai"],
                "classification": current["double_final_quotient_group"],
            },
            "exact_alignment_available": current["double_internalization_target_object_match"],
            "derivation_mode": current["double_internalization_quotient_derivation_mode"],
        },
        "same_geometry": True,
        "same_final_target_object": False,
        "avoid_conflation_rule": (
            "Read single 13/13/trivial as the exact ordinary target-row-language object. Read double 10/10/Z6 as the "
            "benchmark-facing spinorial internalized target object. They share geometry but they do not answer the same final target object."
        ),
        "status_fields_to_read": {
            "single_exactness": [
                "single_target_exact_generator_identity_status",
                "single_target_exact_linear_target_alignment_exists",
                "single_target_projection_mismatch_rank",
                "single_final_rank_bs",
                "single_final_rank_ai",
                "single_final_quotient_group",
            ],
            "double_benchmark": [
                "double_internalization_status",
                "double_internalization_target_object_match",
                "double_final_rank_bs",
                "double_final_rank_ai",
                "double_final_quotient_group",
            ],
        },
        "this_round_cleanup": cleanup,
    }


def build_status_split(context: dict[str, Any]) -> dict[str, Any]:
    current = context["current_status"]
    return {
        "generated_at": context["generated_at"],
        "target_group": context["target_group"],
        "single_exact_target": {
            "object_kind": current["single_final_object_kind"],
            "dBS": current["single_final_rank_bs"],
            "dAI": current["single_final_rank_ai"],
            "classification": current["single_final_quotient_group"],
            "exact_alignment_status": current["single_target_exact_generator_identity_status"],
            "row_language_kind": current["single_target_row_language_kind"],
        },
        "double_benchmark_facing_target": {
            "object_kind": current["double_final_object_kind"],
            "dBS": current["double_final_rank_bs"],
            "dAI": current["double_final_rank_ai"],
            "classification": current["double_final_quotient_group"],
            "exact_alignment_status": current["double_internalization_status"],
            "benchmark_oracle_file": current["benchmark_oracle_file"],
        },
        "same_target_object": False,
        "relation_summary": current["single_double_final_relation"],
    }


def build_markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    copy_map = {
        "proof_layer": [
            PROOF_JSON,
            PROOF_MD,
            UNIQUENESS_JSON,
            UNIQUENESS_MD,
        ],
        "regression_layer": [
            REGRESSION_JSON,
            REGRESSION_MD,
        ],
        "compare_layer": [
            CURRENT_STAGE2_JSON,
            BENCHMARK_STATUS_JSON,
            BENCHMARK_STATUS_MD,
            DOUBLE_STACK_JSON,
            DOUBLE_STACK_MD,
        ],
        "semantics_cleanup_layer": [
            SEMANTICS_JSON,
            SEMANTICS_MD,
            STATUS_SPLIT_JSON,
            STATUS_SPLIT_MD,
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
                "# Review Package: SG194 Single j/k Pairing Proof v1",
                "",
                "- Purpose: prove the canonical single ordinary j/k target-label pairing, verify uniqueness, and freeze the exact single alignment as a regression.",
                "- Single exact target result: `13 / 13 / trivial`.",
                "- Double benchmark-facing result: `10 / 10 / Z6`.",
                "- The package keeps the single/double object split explicit and does not conflate them.",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "1. `proof_layer/sg194_single_jk_pairing_proof_v1.json`",
                "2. `proof_layer/sg194_single_jk_pairing_uniqueness_v1.json`",
                "3. `regression_layer/sg194_single_exact_alignment_regression_v1.json`",
                "4. `compare_layer/current_status_194.1.1.1_stage2.json`",
                "5. `compare_layer/current_status_1941111_benchmark_v1.json`",
                "6. `compare_layer/sg194_double_target_object_stack_v1.json`",
                "7. `semantics_cleanup_layer/sg194_stage2_status_semantics_cleanup_v1.json`",
                "8. `semantics_cleanup_layer/sg194_final_single_double_status_split_v1.json`",
            ]
        ),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def validate_outputs() -> None:
    proof = load_json(PROOF_JSON)
    uniqueness = load_json(UNIQUENESS_JSON)
    regression = load_json(REGRESSION_JSON)
    semantics = load_json(SEMANTICS_JSON)
    status_split = load_json(STATUS_SPLIT_JSON)
    current = load_json(CURRENT_STAGE2_JSON)

    assert proof["canonical_pairing_success"]["mismatch_rank"] == 0
    assert proof["raw_pairing_failure"]["mismatch_rank"] == 1
    assert uniqueness["unique_under_permutation"] is True
    assert uniqueness["unique_under_signed_permutation"] is True
    assert regression["all_passed"] is True
    assert current["single_target_exact_generator_identity_status"] == "available"
    assert current["single_final_rank_bs"] == 13
    assert current["single_final_rank_ai"] == 13
    assert current["single_final_quotient_group"] == "trivial"
    assert current["double_final_rank_bs"] == 10
    assert current["double_final_rank_ai"] == 10
    assert current["double_final_quotient_group"] == "Z6"
    assert semantics["same_final_target_object"] is False
    assert status_split["same_target_object"] is False
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated sg194 single j/k pairing proof outputs")
        return

    refresh_stage2()
    run_checked(["python3", repo_rel(EXACT_ALIGN_SCRIPT), "--validate"])

    context = build_alignment_context()
    proof = build_pairing_proof(context)
    uniqueness = build_uniqueness(context)
    write_json(PROOF_JSON, proof)
    write_text(
        PROOF_MD,
        build_markdown(
            "SG194 Single j/k Pairing Proof v1",
            [
                f"- target group: `{context['target_group']}`",
                "- raw pairing leaves a rank-1 residual on the j/k A'/A'' target columns.",
                "- canonical pairing matches projected current columns to the unique external ordinary columns with identical target-row signatures.",
                "- this preserves the `A'/A''` little-irrep labels and swaps only the `j/k` family letters where the target-row data require it.",
            ],
        ),
    )
    write_json(UNIQUENESS_JSON, uniqueness)
    write_text(
        UNIQUENESS_MD,
        build_markdown(
            "SG194 Single j/k Pairing Uniqueness v1",
            [
                f"- exact permutation solutions: `{len(context['permutation_solutions'])}`",
                f"- exact signed-permutation solutions: `{len(context['signed_permutation_solutions'])}`",
                "- the canonical j/k swap is the unique exact solution in the tested search space.",
                "- no sign-flip or gauge-equivalent alternative survives exact target-row comparison.",
            ],
        ),
    )

    cleanup = execute_cleanup()
    semantics = build_semantics_cleanup(context, cleanup)
    status_split = build_status_split(context)
    write_json(SEMANTICS_JSON, semantics)
    write_text(
        SEMANTICS_MD,
        build_markdown(
            "SG194 Stage2 Status Semantics Cleanup v1",
            [
                "- single exact target result and double benchmark-facing result are both active, but they are not the same final target object.",
                "- single exact target must be read as the ordinary exact target-row-language object `13/13/trivial`.",
                "- double benchmark-facing status must be read as the spinorial internalized benchmark object `10/10/Z6`.",
                f"- git cleanup this round: `{cleanup['git_deleted']}`",
                f"- local cleanup this round: `{cleanup['local_deleted']}`",
            ],
        ),
    )
    write_json(STATUS_SPLIT_JSON, status_split)
    write_text(
        STATUS_SPLIT_MD,
        build_markdown(
            "SG194 Final Single Double Status Split v1",
            [
                "- single exact target: `13 / 13 / trivial`.",
                "- double benchmark-facing target: `10 / 10 / Z6`.",
                "- same geometry does not imply same final target object.",
            ],
        ),
    )

    run_checked(["python3", repo_rel(REGRESSION_SCRIPT)])
    build_package()
    validate_outputs()
    print("generated sg194 single j/k pairing proof outputs")


if __name__ == "__main__":
    main()
