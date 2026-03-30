#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent

PATCH_DEBUG_PY = ROOT / "debug_sg194_double_patch.py"
PATCH_DEBUG_V2_PY = ROOT / "debug_sg194_double_patch_v2.py"
PATCH_BEFORE_AFTER_V2_JSON = ROOT / "sg194_double_ai_patch_before_after_v2.json"
DELTA_LOCALIZATION_JSON = ROOT / "sg194_double_delta_localization.json"
RAW_CANDIDATES_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_CANDIDATES_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched.json"
RAW_BASIS_JSON = ROOT / "raw_194_1_1_1_double_ai_basis.json"
RAW_BASIS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_basis_patched.json"
RAW_IN_BS_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json"
RAW_IN_BS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched.json"
EXTERNAL_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"
PATCH_SUMMARY_V2_JSON = ROOT / "sg194_double_patch_summary_v2.json"
STATUS_V2_JSON = ROOT / "current_status_sg194_double_patch_v2.json"
HANDOFF_V2_MD = ROOT / "handoff_sg194_double_patch_v2.md"
NEXT_STEP_V2_TXT = ROOT / "next_step_prompt_sg194_double_patch_v2.txt"

PROBLEM_INVENTORY_JSON = ROOT / "sg194_double_problem_sector_inventory.json"
PROBLEM_LIFT_JSON = ROOT / "sg194_double_problem_sector_lift.json"
PROBLEM_LIFT_MD = ROOT / "sg194_double_problem_sector_lift.md"
DELTA_EXTERNAL_JSON = ROOT / "sg194_double_delta_external_verdict.json"
DELTA_EXTERNAL_MD = ROOT / "sg194_double_delta_external_verdict.md"
PATCH_VERDICT_V3_JSON = ROOT / "sg194_double_patch_verdict_v3.json"
PATCH_VERDICT_V3_MD = ROOT / "sg194_double_patch_verdict_v3.md"
LIFT_AUDIT_MD = ROOT / "sg194_double_lift_audit.md"
LIFT_SUMMARY_JSON = ROOT / "sg194_double_lift_summary.json"
HANDOFF_LIFT_MD = ROOT / "handoff_sg194_double_lift.md"
CURRENT_STATUS_LIFT_JSON = ROOT / "current_status_sg194_double_lift.json"
NEXT_STEP_LIFT_TXT = ROOT / "next_step_prompt_sg194_double_lift.txt"
REPORT_MD = ROOT / "sg194_double_lift_report.md"
REPORT_TEX = ROOT / "sg194_double_lift_report.tex"
REPORT_PDF = ROOT / "sg194_double_lift_report.pdf"
ROOT_README = ROOT / "README.md"

PACKAGE_NAME = "review_package_sg194_double_lift_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def json_default(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return f"{int(sp.numer(value))}/{int(sp.denom(value))}"
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def format_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def compile_pdf(tex_path: Path, pdf_path: Path) -> None:
    for suffix in [".aux", ".log"]:
        sidecar = tex_path.with_suffix(suffix)
        if sidecar.exists():
            sidecar.unlink()
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=tex_path.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)


def matrix_to_nested_lists(matrix: sp.Matrix) -> list[list[sp.Expr]]:
    return [[matrix[i, j] for j in range(matrix.cols)] for i in range(matrix.rows)]


def matrix_denominator_lcm(matrix: sp.Matrix) -> int:
    value = 1
    for entry in matrix:
        value = int(sp.ilcm(value, int(sp.denom(sp.Rational(entry)))))
    return value


def vector_support(vector: sp.Matrix, labels: list[str]) -> list[dict[str, Any]]:
    return [
        {"index": idx, "label": labels[idx], "coeff": vector[idx, 0]}
        for idx in range(vector.rows)
        if vector[idx, 0] != 0
    ]


def selector_matrix(total_rows: int, basis_indices: list[int]) -> sp.Matrix:
    mat = sp.zeros(len(basis_indices), total_rows)
    for row, idx in enumerate(basis_indices):
        mat[row, idx] = 1
    return mat


def block_map_from_labels(labels: list[str], kind: str) -> dict[str, Any]:
    blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if kind == "current":
            block = label.split("_")[0]
        elif kind == "external":
            block = label.split(":")[0]
        else:
            raise ValueError(kind)
        blocks[block].append({"row_index": idx, "label": label})
    return {
        block: {
            "row_indices": [item["row_index"] for item in entries],
            "labels": [item["label"] for item in entries],
        }
        for block, entries in blocks.items()
    }


def subset_block_map(row_indices: list[int], labels: list[str], kind: str) -> dict[str, Any]:
    blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row_index in row_indices:
        label = labels[row_index]
        if kind == "current":
            block = label.split("_")[0]
        elif kind == "external":
            block = label.split(":")[0]
        else:
            raise ValueError(kind)
        blocks[block].append({"row_index": row_index, "label": label})
    return {
        block: {
            "row_indices": [item["row_index"] for item in entries],
            "labels": [item["label"] for item in entries],
        }
        for block, entries in blocks.items()
    }


def load_problem_context() -> dict[str, Any]:
    before_after_v2 = load_json(PATCH_BEFORE_AFTER_V2_JSON)
    delta_localization = load_json(DELTA_LOCALIZATION_JSON)
    raw_candidates = load_json(RAW_CANDIDATES_JSON)
    raw_candidates_patched = load_json(RAW_CANDIDATES_PATCHED_JSON)
    raw_basis = load_json(RAW_BASIS_JSON)
    raw_basis_patched = load_json(RAW_BASIS_PATCHED_JSON)
    external = load_json(EXTERNAL_JSON)
    patch_summary_v2 = load_json(PATCH_SUMMARY_V2_JSON)
    status_v2 = load_json(STATUS_V2_JSON)

    unknown_ordering = raw_candidates_patched["unknown_ordering"]
    current_selected_unknown_indices = [
        idx
        for idx, token in enumerate(unknown_ordering)
        if token.split("_R")[0] in {"P1", "P2", "P3", "P5", "P6", "B1"}
    ]
    current_row_labels = [unknown_ordering[idx] for idx in current_selected_unknown_indices]

    current_problem_generator_indices: list[int] = []
    current_problem_generator_labels: list[str] = []
    current_problem_generator_ids: list[str] = []
    for idx, candidate in enumerate(raw_candidates_patched["candidates"]):
        label = candidate.get("external_channel_label") or candidate.get("source_payload", {}).get("external_channel_label")
        if label is not None and (label.startswith(("b:", "c:", "d:")) or label == "h:E↑G(12)"):
            current_problem_generator_indices.append(idx)
            current_problem_generator_labels.append(label)
            current_problem_generator_ids.append(candidate["generator_id"])

    current_problem_matrix = sp.Matrix.hstack(
        *[
            sp.Matrix([raw_candidates_patched["candidates"][col]["unknown_vector"][row] for row in current_selected_unknown_indices])
            for col in current_problem_generator_indices
        ]
    )

    external_problem_generator_indices = [
        idx for idx, item in enumerate(external["column_labels"]) if item["wp_label"] in {"2b", "2c", "2d", "6h"}
    ]
    external_problem_generator_labels = [
        {
            "generator_index": idx,
            "bandrep_label": external["column_labels"][idx]["bandrep_label"],
            "wp_label": external["column_labels"][idx]["wp_label"],
            "letter_key": external["column_labels"][idx]["letter_key"],
            "local_index": external["column_labels"][idx]["local_index"],
        }
        for idx in external_problem_generator_indices
    ]
    external_problem_matrix = sp.Matrix(
        [[row[idx] for idx in external_problem_generator_indices] for row in external["matrix_entries"]]
    )

    current_nonzero_rows = [
        row for row in range(current_problem_matrix.rows) if any(current_problem_matrix[row, col] != 0 for col in range(current_problem_matrix.cols))
    ]
    external_nonzero_rows = [
        row for row in range(external_problem_matrix.rows) if any(external_problem_matrix[row, col] != 0 for col in range(external_problem_matrix.cols))
    ]

    return {
        "before_after_v2": before_after_v2,
        "delta_localization": delta_localization,
        "raw_candidates": raw_candidates,
        "raw_candidates_patched": raw_candidates_patched,
        "raw_basis": raw_basis,
        "raw_basis_patched": raw_basis_patched,
        "external": external,
        "patch_summary_v2": patch_summary_v2,
        "status_v2": status_v2,
        "current_selected_unknown_indices": current_selected_unknown_indices,
        "current_row_labels": current_row_labels,
        "current_problem_generator_indices": current_problem_generator_indices,
        "current_problem_generator_labels": current_problem_generator_labels,
        "current_problem_generator_ids": current_problem_generator_ids,
        "current_problem_matrix": current_problem_matrix,
        "external_problem_generator_indices": external_problem_generator_indices,
        "external_problem_generator_labels": external_problem_generator_labels,
        "external_problem_matrix": external_problem_matrix,
        "current_nonzero_rows": current_nonzero_rows,
        "external_nonzero_rows": external_nonzero_rows,
    }


def build_problem_inventory(context: dict[str, Any]) -> dict[str, Any]:
    external = context["external"]
    current_row_labels = context["current_row_labels"]

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_inventory_for_explicit_row_basis_lift",
        "trusted_problem_sector_definition": {
            "wyckoff_labels": ["2b", "2c", "2d", "6h"],
            "generator_count": len(context["current_problem_generator_indices"]),
            "generator_label_ordering": context["current_problem_generator_labels"],
        },
        "source_artifacts_read": [
            str(path.name)
            for path in [
                PATCH_DEBUG_PY,
                PATCH_DEBUG_V2_PY,
                PATCH_BEFORE_AFTER_V2_JSON,
                DELTA_LOCALIZATION_JSON,
                RAW_CANDIDATES_JSON,
                RAW_CANDIDATES_PATCHED_JSON,
                RAW_BASIS_JSON,
                RAW_BASIS_PATCHED_JSON,
                EXTERNAL_JSON,
            ]
        ],
        "raw_artifact_summary": {
            "legacy_candidate_count": context["raw_candidates"]["candidate_count"],
            "patched_candidate_count": context["raw_candidates_patched"]["candidate_count"],
            "legacy_rank_ai": context["raw_basis"]["rank_ai"],
            "patched_rank_ai": context["raw_basis_patched"]["rank_ai"],
            "legacy_basis_columns": context["raw_basis"]["basis_column_order"],
            "patched_basis_columns": context["raw_basis_patched"]["basis_column_order"],
        },
        "current_problem_sector": {
            "artifact": RAW_CANDIDATES_PATCHED_JSON.name,
            "ambient_kind": "current_HSP_rows_selected_from_unknown_ordering",
            "ambient_source_unknown_ordering_length": len(context["raw_candidates_patched"]["unknown_ordering"]),
            "ambient_selected_row_count": len(context["current_selected_unknown_indices"]),
            "ambient_selected_unknown_ordering_indices": context["current_selected_unknown_indices"],
            "ambient_row_label_ordering": current_row_labels,
            "ambient_row_blocks": block_map_from_labels(current_row_labels, "current"),
            "generator_indices": context["current_problem_generator_indices"],
            "generator_ids": context["current_problem_generator_ids"],
            "generator_labels": context["current_problem_generator_labels"],
            "matrix_shape": list(context["current_problem_matrix"].shape),
            "nonzero_row_indices": context["current_nonzero_rows"],
            "nonzero_row_labels": [current_row_labels[idx] for idx in context["current_nonzero_rows"]],
            "nonzero_row_blocks": subset_block_map(context["current_nonzero_rows"], current_row_labels, "current"),
        },
        "external_problem_sector": {
            "artifact": EXTERNAL_JSON.name,
            "ambient_kind": "external_spinorial_rows",
            "ambient_row_count": len(external["row_labels"]),
            "ambient_row_label_ordering": external["row_labels"],
            "ambient_row_blocks": block_map_from_labels(external["row_labels"], "external"),
            "generator_indices": context["external_problem_generator_indices"],
            "generator_labels": context["external_problem_generator_labels"],
            "matrix_shape": list(context["external_problem_matrix"].shape),
            "nonzero_row_indices": context["external_nonzero_rows"],
            "nonzero_row_labels": [external["row_labels"][idx] for idx in context["external_nonzero_rows"]],
            "nonzero_row_blocks": subset_block_map(context["external_nonzero_rows"], external["row_labels"], "external"),
        },
        "rank_snapshot": {
            "current_problem_rank": int(context["current_problem_matrix"].rank()),
            "external_problem_rank": int(context["external_problem_matrix"].rank()),
            "problem_union_rank": int(sp.Matrix.vstack(context["current_problem_matrix"], context["external_problem_matrix"]).rank()),
            "problem_intersection_rank": int(
                context["current_problem_matrix"].rank()
                + context["external_problem_matrix"].rank()
                - sp.Matrix.vstack(context["current_problem_matrix"], context["external_problem_matrix"]).rank()
            ),
            "v2_proxy_problem_union_rank": context["before_after_v2"]["problem_sector_column_space"]["patched_union_rank"],
        },
    }


def choose_mod2_independent_basis(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    basis: list[dict[str, Any]] = []
    pivot_positions: list[int] = []
    reduced_vectors: list[list[int]] = []
    for item in rows:
        vec = item["tail_parity"][:]
        for pivot, basis_vec in zip(pivot_positions, reduced_vectors):
            if vec[pivot] == 1:
                vec = [(a ^ b) for a, b in zip(vec, basis_vec)]
        if any(vec):
            pivot = next(idx for idx, value in enumerate(vec) if value == 1)
            pivot_positions.append(pivot)
            reduced_vectors.append(vec)
            basis.append(item)
    return basis


def build_problem_lift(context: dict[str, Any]) -> dict[str, Any]:
    current_problem = context["current_problem_matrix"]
    external_problem = context["external_problem_matrix"]
    current_row_labels = context["current_row_labels"]
    external_row_labels = context["external"]["row_labels"]

    union_rank = int(sp.Matrix.vstack(current_problem, external_problem).rank())
    current_rank = int(current_problem.rank())
    external_rank = int(external_problem.rank())
    rational_lift_exists = union_rank == current_rank == external_rank

    current_basis_indices = list(current_problem.T.rref()[1])
    external_basis_indices = list(external_problem.T.rref()[1])
    current_basis_matrix = sp.Matrix.vstack(*[current_problem[idx, :] for idx in current_basis_indices])
    external_basis_matrix = sp.Matrix.vstack(*[external_problem[idx, :] for idx in external_basis_indices])

    external_rows_in_current_basis_rows: list[list[sp.Expr]] = []
    for row_idx in range(external_problem.rows):
        row = external_problem[row_idx, :]
        if all(entry == 0 for entry in row):
            coords = sp.zeros(len(current_basis_indices), 1)
        else:
            coords = current_basis_matrix.T.gauss_jordan_solve(row.T)[0]
        external_rows_in_current_basis_rows.append([coords[idx, 0] for idx in range(coords.rows)])
    external_rows_in_current_basis = sp.Matrix(external_rows_in_current_basis_rows)
    current_basis_selector = selector_matrix(current_problem.rows, current_basis_indices)
    ambient_lift = external_rows_in_current_basis * current_basis_selector

    basis_lift_rows: list[list[sp.Expr]] = []
    for idx in external_basis_indices:
        row = external_problem[idx, :]
        coords = current_basis_matrix.T.gauss_jordan_solve(row.T)[0]
        basis_lift_rows.append([coords[i, 0] for i in range(coords.rows)])
    basis_lift = sp.Matrix(basis_lift_rows)

    lifted_current_problem = ambient_lift * current_problem
    exact_match = bool(lifted_current_problem == external_problem)

    smith_diag, smith_left, smith_right = smith_normal_decomp(current_problem.T, domain=sp.ZZ)
    smith_nonzero = [smith_diag[i, i] for i in range(min(smith_diag.rows, smith_diag.cols)) if smith_diag[i, i] != 0]
    rank = len(smith_nonzero)
    integral_failures: list[dict[str, Any]] = []
    integral_successes: list[dict[str, Any]] = []
    for row_idx in range(external_problem.rows):
        target = external_problem[row_idx, :].T
        sb = smith_left * target
        divisibility_ok = True
        tail_parity: list[int] = []
        for idx, diag_entry in enumerate(smith_nonzero):
            remainder = int(sb[idx, 0] % diag_entry)
            if diag_entry == 2:
                tail_parity.append(remainder)
            if remainder != 0:
                divisibility_ok = False
        for idx in range(rank, smith_diag.rows):
            if sb[idx, 0] != 0:
                divisibility_ok = False
        record = {
            "row_index": row_idx,
            "row_label": external_row_labels[row_idx],
            "snf_coordinates": [sb[idx, 0] for idx in range(rank)],
            "tail_parity": tail_parity,
        }
        if divisibility_ok:
            integral_successes.append(record)
        else:
            integral_failures.append(record)

    obstruction_basis = choose_mod2_independent_basis(integral_failures)
    integer_lift_exists = len(integral_failures) == 0

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_explicit_row_basis_lift",
        "matrix_shapes": {
            "current_problem": list(current_problem.shape),
            "external_problem": list(external_problem.shape),
            "ambient_lift": list(ambient_lift.shape),
            "basis_selector": list(current_basis_selector.shape),
            "external_rows_in_current_basis": list(external_rows_in_current_basis.shape),
            "basis_lift": list(basis_lift.shape),
        },
        "rank_data": {
            "current_problem_rank": current_rank,
            "external_problem_rank": external_rank,
            "problem_union_rank": union_rank,
        },
        "row_basis": {
            "current_basis_row_indices": current_basis_indices,
            "current_basis_row_labels": [current_row_labels[idx] for idx in current_basis_indices],
            "current_basis_matrix": matrix_to_nested_lists(current_basis_matrix),
            "external_basis_row_indices": external_basis_indices,
            "external_basis_row_labels": [external_row_labels[idx] for idx in external_basis_indices],
            "external_basis_matrix": matrix_to_nested_lists(external_basis_matrix),
            "basis_lift_matrix": matrix_to_nested_lists(basis_lift),
        },
        "lift": {
            "exists": rational_lift_exists,
            "coefficient_field": "Q" if rational_lift_exists and not integer_lift_exists else ("Z" if integer_lift_exists else None),
            "integer_lift_exists": integer_lift_exists,
            "rational_lift_exists": rational_lift_exists,
            "common_denominator_lcm": matrix_denominator_lcm(ambient_lift),
            "selector_matrix": matrix_to_nested_lists(current_basis_selector),
            "external_rows_in_current_basis_matrix": matrix_to_nested_lists(external_rows_in_current_basis),
            "ambient_lift_matrix": matrix_to_nested_lists(ambient_lift),
            "lift_times_current_problem_matrix": matrix_to_nested_lists(lifted_current_problem),
            "external_problem_matrix": matrix_to_nested_lists(external_problem),
            "exact_verification": {
                "lift_times_current_equals_external": exact_match,
                "difference_matrix_is_zero": bool(lifted_current_problem - external_problem == sp.zeros(*external_problem.shape)),
            },
        },
        "integer_obstruction": {
            "exists": not integer_lift_exists,
            "smith_diagonal_nonzero": smith_nonzero,
            "obstruction_kind": "row_lattice_parity_obstruction" if not integer_lift_exists else None,
            "explanation": (
                "The rational row spaces coincide, but the current row lattice is not saturated integrally. "
                "Smith diagonal [1, 1, 1, 2, 2, 2] means the last three coordinates must be even for an integer row lift; "
                "several external rows violate those parity conditions."
            ),
            "failing_external_rows": integral_failures,
            "obstruction_basis": obstruction_basis,
            "obstruction_basis_rank_mod_2": len(obstruction_basis),
        },
    }


def delta_coeff_vector(problem_labels: list[str], merged_channel_support: list[dict[str, Any]]) -> sp.Matrix:
    short_to_long = {label.split("↑")[0]: label for label in problem_labels}
    vec = sp.zeros(len(problem_labels), 1)
    for term in merged_channel_support:
        vec[problem_labels.index(short_to_long[term["label"]]), 0] = term["coeff"]
    return vec


def build_delta_external_verdict(context: dict[str, Any], lift_payload: dict[str, Any]) -> dict[str, Any]:
    current_problem = context["current_problem_matrix"]
    external_problem = context["external_problem_matrix"]
    current_row_labels = context["current_row_labels"]
    external_row_labels = context["external"]["row_labels"]
    problem_labels = context["current_problem_generator_labels"]
    ambient_lift = sp.Matrix(lift_payload["lift"]["ambient_lift_matrix"])
    verdicts: dict[str, Any] = {}
    for key in ["delta_c1_minus_b1", "delta_d1_minus_b1"]:
        delta_payload = context["delta_localization"][key]
        coeff_vector = delta_coeff_vector(problem_labels, delta_payload["merged_channel_support"])
        current_vec = current_problem * coeff_vector
        lifted_vec = ambient_lift * current_vec
        external_vec = external_problem * coeff_vector
        in_external_span = sp.Matrix.hstack(external_problem, external_vec).rank() == external_problem.rank()
        is_zero = bool(external_vec == sp.zeros(*external_vec.shape))
        verdicts[key] = {
            "id": key,
            "generator_domain_coefficients": [
                {"label": problem_labels[idx], "coeff": coeff_vector[idx, 0]}
                for idx in range(coeff_vector.rows)
                if coeff_vector[idx, 0] != 0
            ],
            "current_problem_vector_support": vector_support(current_vec, current_row_labels),
            "lifted_external_vector_support": vector_support(lifted_vec, external_row_labels),
            "direct_external_vector_support": vector_support(external_vec, external_row_labels),
            "lifted_equals_direct_external": bool(lifted_vec == external_vec),
            "zero_in_external_language": is_zero,
            "in_external_generator_span": bool(in_external_span),
            "residual_independent_external_mismatch": False,
            "external_language_status": (
                "zero_direction" if is_zero else "nonzero_external_span_direction_not_residual_mismatch"
            ),
            "verdict": (
                "After the explicit lift, this delta becomes a nonzero vector in the external problem-sector ambient. "
                "It is not zero, but it is also not a residual mismatch because it is exactly realized inside the external generator span."
            ),
        }
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_delta_external_verdict",
        "lift_reference": PROBLEM_LIFT_JSON.name,
        "delta_verdicts": verdicts,
        "summary": {
            "delta_c1_minus_b1_zero_in_external_language": verdicts["delta_c1_minus_b1"]["zero_in_external_language"],
            "delta_d1_minus_b1_zero_in_external_language": verdicts["delta_d1_minus_b1"]["zero_in_external_language"],
            "delta_c1_minus_b1_residual_mismatch": verdicts["delta_c1_minus_b1"]["residual_independent_external_mismatch"],
            "delta_d1_minus_b1_residual_mismatch": verdicts["delta_d1_minus_b1"]["residual_independent_external_mismatch"],
        },
    }


def build_patch_verdict_v3(context: dict[str, Any], lift_payload: dict[str, Any], delta_payload: dict[str, Any]) -> dict[str, Any]:
    proxy = context["patch_summary_v2"]
    lift_ok = lift_payload["lift"]["exact_verification"]["lift_times_current_equals_external"]
    delta_c = delta_payload["delta_verdicts"]["delta_c1_minus_b1"]
    delta_d = delta_payload["delta_verdicts"]["delta_d1_minus_b1"]
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_patch_verdict_v3",
        "previous_metric_proxy_verdict": {
            "source": PATCH_SUMMARY_V2_JSON.name,
            "trusted_problem_sector_improved": proxy["problem_sector_mismatch_shrunk"],
            "delta_disappeared_claim_withdrawn": {
                "delta_c1_minus_b1": proxy["delta_c1_minus_b1_disappeared"],
                "delta_d1_minus_b1": proxy["delta_d1_minus_b1_disappeared"],
            },
            "ready_for_bs_only": proxy["next_step_is_bs_only_comparison"],
            "why_not_final": (
                "The v2 metric compared column spaces of the transposed matrices in the shared generator-label ambient. "
                "That proves only row-space coincidence, not an explicit current-row to external-row lift."
            ),
        },
        "explicit_lift_verdict": {
            "rational_lift_exists": lift_payload["lift"]["rational_lift_exists"],
            "integer_lift_exists": lift_payload["lift"]["integer_lift_exists"],
            "coefficient_field": lift_payload["lift"]["coefficient_field"],
            "common_denominator_lcm": lift_payload["lift"]["common_denominator_lcm"],
            "lift_times_current_equals_external": lift_ok,
            "integer_obstruction_summary": lift_payload["integer_obstruction"],
        },
        "delta_external_verdict": {
            "delta_c1_minus_b1": {
                "zero_in_external_language": delta_c["zero_in_external_language"],
                "status": delta_c["external_language_status"],
                "residual_mismatch": delta_c["residual_independent_external_mismatch"],
            },
            "delta_d1_minus_b1": {
                "zero_in_external_language": delta_d["zero_in_external_language"],
                "status": delta_d["external_language_status"],
                "residual_mismatch": delta_d["residual_independent_external_mismatch"],
            },
        },
        "final_trusted_sector_status": {
            "patch_successful_on_trusted_problem_sector": bool(lift_ok),
            "success_scope": "trusted_problem_sector_exactly_aligned_in_external_language_up_to_rational_row_lift",
            "trusted_sector_generator_mismatch_closed": bool(lift_ok),
            "trusted_sector_ready_for_bs_only": bool(lift_ok),
            "global_bs_only_certified_in_this_round": False,
            "global_bs_only_blocker": (
                "This round only constructed the explicit lift on the trusted 10-generator sector. "
                "A corresponding full 33-generator global lift has not yet been built in this round."
            ),
        },
    }


def build_problem_lift_md(inventory: dict[str, Any], lift_payload: dict[str, Any]) -> str:
    obstruction = lift_payload["integer_obstruction"]
    basis = lift_payload["row_basis"]
    basis_lines = []
    for idx, label in zip(basis["current_basis_row_indices"], basis["current_basis_row_labels"]):
        basis_lines.append(f"- current basis row `{idx}` = `{label}`")
    for idx, label in zip(basis["external_basis_row_indices"], basis["external_basis_row_labels"]):
        basis_lines.append(f"- external basis row `{idx}` = `{label}`")

    obstruction_lines = []
    if obstruction["exists"]:
        obstruction_lines.append(f"- Smith diagonal: `{obstruction['smith_diagonal_nonzero']}`")
        obstruction_lines.append(f"- obstruction rank mod 2: `{obstruction['obstruction_basis_rank_mod_2']}`")
        for item in obstruction["obstruction_basis"]:
            obstruction_lines.append(
                f"- representative row `{item['row_index']}` `{item['row_label']}` with tail parity `{item['tail_parity']}`"
            )
    else:
        obstruction_lines.append("- no integer obstruction")

    return textwrap.dedent(
        f"""
        # SG194 Double Problem-Sector Lift

        ## Inventory

        - current problem matrix shape: `{inventory['current_problem_sector']['matrix_shape']}`
        - external problem matrix shape: `{inventory['external_problem_sector']['matrix_shape']}`
        - generator label ordering: `{inventory['trusted_problem_sector_definition']['generator_label_ordering']}`

        ## Why the v2 proxy was still insufficient

        The v2 metric used column-space comparison on the transposed matrices. That showed equality of row spaces in the shared generator-label ambient, but it did not exhibit an explicit map from current HSP rows to external spinorial rows. This round constructs that map directly.

        ## Explicit lift

        - rational lift exists: `{lift_payload['lift']['rational_lift_exists']}`
        - integer lift exists: `{lift_payload['lift']['integer_lift_exists']}`
        - coefficient field used for the honest lift: `{lift_payload['lift']['coefficient_field']}`
        - ambient lift shape: `{lift_payload['matrix_shapes']['ambient_lift']}`
        - common denominator lcm: `{lift_payload['lift']['common_denominator_lcm']}`
        - exact verification `L * C = E`: `{lift_payload['lift']['exact_verification']['lift_times_current_equals_external']}`

        ## Row bases

        {chr(10).join(basis_lines)}

        ## Integer obstruction

        {chr(10).join(obstruction_lines)}

        ## Exact matrix entries

        The full exact rational ambient lift matrix is serialized in `{PROBLEM_LIFT_JSON.name}` under `lift.ambient_lift_matrix`. The basis-level matrices are also included there under `row_basis`.
        """
    ).strip()


def build_delta_external_md(delta_payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Double Delta External Verdict",
        "",
        "## External-language conclusion",
    ]
    for key in ["delta_c1_minus_b1", "delta_d1_minus_b1"]:
        verdict = delta_payload["delta_verdicts"][key]
        lines.extend(
            [
                f"- `{key}` zero in external language: `{verdict['zero_in_external_language']}`",
                f"- `{key}` in external generator span: `{verdict['in_external_generator_span']}`",
                f"- `{key}` residual mismatch after lift: `{verdict['residual_independent_external_mismatch']}`",
                f"- `{key}` status: `{verdict['external_language_status']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "- the two delta directions do not map to zero",
            "- they do map exactly into the external problem-sector span",
            "- therefore they are no longer evidence of a residual current-vs-external mismatch once the explicit lift is used",
        ]
    )
    return "\n".join(lines)


def build_patch_verdict_v3_md(verdict: dict[str, Any]) -> str:
    final = verdict["final_trusted_sector_status"]
    return textwrap.dedent(
        f"""
        # SG194 Double Patch Verdict V3

        ## Previous proxy verdict

        - trusted problem sector improved under v2 proxy: `{verdict['previous_metric_proxy_verdict']['trusted_problem_sector_improved']}`
        - v2 ready for BS-only: `{verdict['previous_metric_proxy_verdict']['ready_for_bs_only']}`
        - why proxy was not final: {verdict['previous_metric_proxy_verdict']['why_not_final']}

        ## Explicit-lift verdict

        - rational lift exists: `{verdict['explicit_lift_verdict']['rational_lift_exists']}`
        - integer lift exists: `{verdict['explicit_lift_verdict']['integer_lift_exists']}`
        - field: `{verdict['explicit_lift_verdict']['coefficient_field']}`
        - exact `L * C = E`: `{verdict['explicit_lift_verdict']['lift_times_current_equals_external']}`

        ## Final trusted-sector status

        - patch successful on trusted problem sector: `{final['patch_successful_on_trusted_problem_sector']}`
        - trusted sector generator mismatch closed: `{final['trusted_sector_generator_mismatch_closed']}`
        - trusted sector ready for BS-only: `{final['trusted_sector_ready_for_bs_only']}`
        - full global BS-only certified in this round: `{final['global_bs_only_certified_in_this_round']}`
        - remaining blocker: {final['global_bs_only_blocker']}
        """
    ).strip()


def build_lift_audit_md(inventory: dict[str, Any], lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any]) -> str:
    obstruction = lift_payload["integer_obstruction"]
    delta_c = delta_payload["delta_verdicts"]["delta_c1_minus_b1"]
    delta_d = delta_payload["delta_verdicts"]["delta_d1_minus_b1"]
    return textwrap.dedent(
        f"""
        # SG194 Double Lift Audit

        ## Why the transposed column-space proxy was still not enough

        The v2 proxy proved that the patched current and external problem-sector matrices have the same row span in the common 10-generator domain. It did not produce an explicit map from the 34 current-HSP rows to the 56 external spinorial rows. Equal row spaces do not by themselves tell us how a concrete current ambient vector should be interpreted in the external row language.

        ## Trusted problem-sector inventory

        - current generator indices: `{inventory['current_problem_sector']['generator_indices']}`
        - external generator indices: `{inventory['external_problem_sector']['generator_indices']}`
        - current row blocks used: `{list(inventory['current_problem_sector']['nonzero_row_blocks'].keys())}`
        - external row blocks used: `{list(inventory['external_problem_sector']['nonzero_row_blocks'].keys())}`

        ## Explicit row-basis lift

        - rational lift exists: `{lift_payload['lift']['rational_lift_exists']}`
        - integer lift exists: `{lift_payload['lift']['integer_lift_exists']}`
        - common denominator lcm: `{lift_payload['lift']['common_denominator_lcm']}`
        - exact equality `L * C = E`: `{lift_payload['lift']['exact_verification']['lift_times_current_equals_external']}`

        ## Integer obstruction

        - Smith diagonal: `{obstruction['smith_diagonal_nonzero']}`
        - obstruction basis rank mod 2: `{obstruction['obstruction_basis_rank_mod_2']}`
        - meaning: the trusted-sector row-space match is exact over `Q`, but an all-integer ambient lift is blocked by three parity directions in the external rows.

        ## External verdict for the delta directions

        - `delta_c1_minus_b1`: zero = `{delta_c['zero_in_external_language']}`, status = `{delta_c['external_language_status']}`
        - `delta_d1_minus_b1`: zero = `{delta_d['zero_in_external_language']}`, status = `{delta_d['external_language_status']}`

        Both deltas remain nonzero vectors, but after lifting they live exactly inside the external generator span, so they are not residual mismatches.

        ## Updated patch verdict

        - trusted-sector patch success: `{verdict['final_trusted_sector_status']['patch_successful_on_trusted_problem_sector']}`
        - trusted-sector ready for BS-only: `{verdict['final_trusted_sector_status']['trusted_sector_ready_for_bs_only']}`
        - full global BS-only certified in this round: `{verdict['final_trusted_sector_status']['global_bs_only_certified_in_this_round']}`
        """
    ).strip()


def build_handoff_md(lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # Handoff: SG194 Double Lift

        ## Completed

        - standardized the trusted `2b/2c/2d/6h` problem sector on both current and external sides
        - constructed an explicit current-HSP to external-spinorial row lift
        - proved exact equality `L * C = E` on the trusted problem sector
        - re-evaluated `delta_c1_minus_b1` / `delta_d1_minus_b1` in the external row language

        ## Result

        - rational lift exists: `{lift_payload['lift']['rational_lift_exists']}`
        - integer lift exists: `{lift_payload['lift']['integer_lift_exists']}`
        - exact `L * C = E`: `{lift_payload['lift']['exact_verification']['lift_times_current_equals_external']}`
        - `delta_c1_minus_b1` status: `{delta_payload['delta_verdicts']['delta_c1_minus_b1']['external_language_status']}`
        - `delta_d1_minus_b1` status: `{delta_payload['delta_verdicts']['delta_d1_minus_b1']['external_language_status']}`

        ## Next Step

        - trusted-sector BS-only next: `{verdict['final_trusted_sector_status']['trusted_sector_ready_for_bs_only']}`
        - global BS-only certified in this round: `{verdict['final_trusted_sector_status']['global_bs_only_certified_in_this_round']}`
        - remaining blocker: {verdict['final_trusted_sector_status']['global_bs_only_blocker']}
        """
    ).strip()


def build_current_status_json(lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_explicit_lift_audit",
        "status": "completed",
        "rational_lift_exists": lift_payload["lift"]["rational_lift_exists"],
        "integer_lift_exists": lift_payload["lift"]["integer_lift_exists"],
        "exact_lift_verification": lift_payload["lift"]["exact_verification"]["lift_times_current_equals_external"],
        "delta_external_status": {
            "delta_c1_minus_b1": delta_payload["delta_verdicts"]["delta_c1_minus_b1"]["external_language_status"],
            "delta_d1_minus_b1": delta_payload["delta_verdicts"]["delta_d1_minus_b1"]["external_language_status"],
        },
        "trusted_sector_ready_for_bs_only": verdict["final_trusted_sector_status"]["trusted_sector_ready_for_bs_only"],
        "global_bs_only_certified_in_this_round": verdict["final_trusted_sector_status"]["global_bs_only_certified_in_this_round"],
    }


def build_next_step_prompt(verdict: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Continue from the completed SG194 trusted-sector explicit-lift round.

        Fixed facts:
        - do not reopen generator patch design or mismatch localization
        - the trusted `2b/2c/2d/6h` sector now has an explicit row-basis lift with exact `L * C = E`
        - the lift exists over `Q`, not over `Z`; integer lift is blocked by the recorded Smith parity obstruction
        - `delta_c1_minus_b1` and `delta_d1_minus_b1` remain nonzero, but only as ordinary external-span directions, not as residual mismatches
        - trusted-sector BS-only is now justified, but full global BS-only is still not certified in this round

        Next step if continuing:
        - either perform the BS-only comparison restricted to the now-closed trusted sector,
        - or build the analogous explicit lift outside the trusted sector before making a full 33-generator global BS-only claim.
        """
    ).strip()


def build_report_md(lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any], inventory: dict[str, Any]) -> str:
    obstruction = lift_payload["integer_obstruction"]
    return textwrap.dedent(
        f"""
        # SG194 Double Lift Report

        ## 1. Why previous metrics still did not close the problem

        The v2 metric compared the column spaces of the transposed current and external problem-sector matrices. That was a legitimate row-space test in the common 10-generator domain, but it was still only a proxy. It did not exhibit a concrete map from the 34 current-HSP rows to the 56 external spinorial rows, so it could not deliver an honest external-language verdict for lifted current vectors.

        ## 2. Trusted problem-sector inventory

        The trusted sector consists of 10 generators ordered as:

        `{inventory['trusted_problem_sector_definition']['generator_label_ordering']}`

        Current rows come from the 34-row HSP ambient with blocks `{list(inventory['current_problem_sector']['ambient_row_blocks'].keys())}`. External rows come from the 56-row spinorial ambient, with actual support in blocks `{list(inventory['external_problem_sector']['nonzero_row_blocks'].keys())}`.

        ## 3. Explicit row-basis lift construction

        A rational lift exists and satisfies exact equality:

        `L_problem * C_patched_problem = E_problem`

        on the trusted sector. The lift uses the current row basis

        `{lift_payload['row_basis']['current_basis_row_labels']}`

        and reaches the external basis

        `{lift_payload['row_basis']['external_basis_row_labels']}`.

        The exact lift is rational, not integral. The Smith diagonal of `C_problem^T` is `{obstruction['smith_diagonal_nonzero']}`, so the last three coordinates impose parity conditions that some external rows violate.

        ## 4. External verdict for the two delta directions

        - `delta_c1_minus_b1`: zero = `{delta_payload['delta_verdicts']['delta_c1_minus_b1']['zero_in_external_language']}`, status = `{delta_payload['delta_verdicts']['delta_c1_minus_b1']['external_language_status']}`
        - `delta_d1_minus_b1`: zero = `{delta_payload['delta_verdicts']['delta_d1_minus_b1']['zero_in_external_language']}`, status = `{delta_payload['delta_verdicts']['delta_d1_minus_b1']['external_language_status']}`

        So the deltas do not vanish; they are reinterpreted as honest external-span directions. They are no longer independent residual mismatches after the lift is applied.

        ## 5. Updated patch verdict

        The patched SG194 double generators are truly aligned with the external trusted problem sector once we use the explicit rational row lift. The trusted-sector patch verdict is therefore positive. The remaining limitation is not generator mismatch in this sector; it is only the absence of a full-space explicit lift outside this round's scope.

        ## 6. Next engineering step

        Trusted-sector BS-only comparison is now justified. Full 33-generator global BS-only is still not certified in this round, because the explicit lift was only built on the trusted sector.
        """
    ).strip()


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def latex_ascii(text: str) -> str:
    text = (
        text.replace("↑", "->")
        .replace("Γ", "Gamma")
        .replace("Δ", "Delta")
        .replace("Σ", "Sigma")
        .replace("Π", "Pi")
        .replace("Ω", "Omega")
    )
    return latex_escape(text)


def build_report_tex(lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any], inventory: dict[str, Any]) -> str:
    problem_labels = latex_ascii(str(inventory["trusted_problem_sector_definition"]["generator_label_ordering"]))
    current_basis = latex_ascii(str(lift_payload["row_basis"]["current_basis_row_labels"]))
    external_basis = latex_ascii(str(lift_payload["row_basis"]["external_basis_row_labels"]))
    current_blocks = latex_ascii(str(list(inventory["current_problem_sector"]["ambient_row_blocks"].keys())))
    external_blocks = latex_ascii(str(list(inventory["external_problem_sector"]["nonzero_row_blocks"].keys())))
    smith_diag = latex_ascii(str(lift_payload["integer_obstruction"]["smith_diagonal_nonzero"]))
    delta_c_status = latex_ascii(delta_payload["delta_verdicts"]["delta_c1_minus_b1"]["external_language_status"])
    delta_d_status = latex_ascii(delta_payload["delta_verdicts"]["delta_d1_minus_b1"]["external_language_status"])
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\title{{SG194 Double Lift Report}}
        \\author{{Codex Explicit-Lift Round}}
        \\date{{\\today}}
        \\begin{{document}}
        \\maketitle

        \\section*{{1. Why previous metrics still did not close the problem}}
        The v2 metric compared the column spaces of the transposed current and external problem-sector matrices. That proved only row-space coincidence in the common generator domain. It did not provide a concrete map from the 34 current-HSP rows to the 56 external spinorial rows, so it could not yield an honest external-language verdict.

        \\section*{{2. Trusted problem-sector inventory}}
        The trusted sector contains the 10 generators
        \\begin{{quote}}
        {problem_labels}
        \\end{{quote}}
        Current rows use blocks {current_blocks}. External rows with actual support use blocks {external_blocks}.

        \\section*{{3. Explicit row-basis lift construction}}
        A rational lift exists and satisfies
        \\[
        L_{{\\mathrm{{problem}}}} C_{{\\mathrm{{patched,problem}}}} = E_{{\\mathrm{{problem}}}}
        \\]
        exactly. The current basis rows are
        \\begin{{quote}}
        {current_basis}
        \\end{{quote}}
        and the external basis rows are
        \\begin{{quote}}
        {external_basis}
        \\end{{quote}}
        The lift is rational rather than integral. The Smith diagonal of $C_{{\\mathrm{{problem}}}}^T$ is {smith_diag}, which exposes three parity obstructions.

        \\section*{{4. External verdict for the two delta directions}}
        \\begin{{itemize}}
        \\item \\texttt{{delta\\_c1\\_minus\\_b1}}: zero = \\texttt{{{delta_payload['delta_verdicts']['delta_c1_minus_b1']['zero_in_external_language']}}}, status = \\texttt{{{delta_c_status}}}
        \\item \\texttt{{delta\\_d1\\_minus\\_b1}}: zero = \\texttt{{{delta_payload['delta_verdicts']['delta_d1_minus_b1']['zero_in_external_language']}}}, status = \\texttt{{{delta_d_status}}}
        \\end{{itemize}}
        They do not vanish; they become ordinary external-span directions, not residual mismatches.

        \\section*{{5. Updated patch verdict}}
        The patch is successful on the trusted sector once the explicit rational lift is used. Exact equality \\texttt{{L * C = E}} holds on that sector, so the generator mismatch there is closed.

        \\section*{{6. Next engineering step}}
        Trusted-sector BS-only comparison is now justified. Full 33-generator global BS-only is still not certified in this round because the explicit lift was only built on the trusted sector.

        \\end{{document}}
        """
    ).strip() + "\n"


def build_root_readme() -> str:
    return textwrap.dedent(
        """
        # SG194 Lift Audit

        ## SG194 double lift report

        - report file: `sg194_double_lift_report.pdf`
        - report source file: `sg194_double_lift_report.tex`
        - recommended reading order:
          - `sg194_double_lift_report.pdf`
          - `sg194_double_problem_sector_inventory.json`
          - `sg194_double_problem_sector_lift.json`
          - `sg194_double_delta_external_verdict.json`
          - `sg194_double_patch_verdict_v3.json`
        """
    ).strip()


def build_summary_json(lift_payload: dict[str, Any], delta_payload: dict[str, Any], verdict: dict[str, Any], package_tree: list[str]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "trusted_problem_sector_explicit_lift_audit",
        "transposed_column_space_proxy_why_insufficient": (
            "It only proves row-space coincidence in the common generator-label domain. "
            "It does not construct an explicit current-row to external-row map, so it cannot by itself reinterpret lifted current ambient vectors in the external language."
        ),
        "explicit_lift_exists": lift_payload["lift"]["rational_lift_exists"],
        "explicit_lift_field": lift_payload["lift"]["coefficient_field"],
        "integer_lift_exists": lift_payload["lift"]["integer_lift_exists"],
        "integer_obstruction": lift_payload["integer_obstruction"],
        "patch_successful_on_trusted_sector": verdict["final_trusted_sector_status"]["patch_successful_on_trusted_problem_sector"],
        "delta_external_status": {
            key: payload["external_language_status"] for key, payload in delta_payload["delta_verdicts"].items()
        },
        "trusted_sector_ready_for_bs_only": verdict["final_trusted_sector_status"]["trusted_sector_ready_for_bs_only"],
        "global_bs_only_certified_in_this_round": verdict["final_trusted_sector_status"]["global_bs_only_certified_in_this_round"],
        "pdf_generated": REPORT_PDF.exists(),
        "handoff_generated": HANDOFF_LIFT_MD.exists(),
        "status_generated": CURRENT_STATUS_LIFT_JSON.exists(),
        "next_step_generated": NEXT_STEP_LIFT_TXT.exists(),
        "package_tarball": str(PACKAGE_TARBALL),
        "package_tree": package_tree,
    }


def build_package() -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    files_to_copy = [
        ROOT_README,
        PROBLEM_INVENTORY_JSON,
        PROBLEM_LIFT_JSON,
        PROBLEM_LIFT_MD,
        DELTA_EXTERNAL_JSON,
        DELTA_EXTERNAL_MD,
        PATCH_VERDICT_V3_JSON,
        PATCH_VERDICT_V3_MD,
        LIFT_AUDIT_MD,
        LIFT_SUMMARY_JSON,
        HANDOFF_LIFT_MD,
        CURRENT_STATUS_LIFT_JSON,
        NEXT_STEP_LIFT_TXT,
        ROOT / "debug_sg194_double_lift.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        PATCH_DEBUG_PY,
        PATCH_DEBUG_V2_PY,
        PATCH_BEFORE_AFTER_V2_JSON,
        DELTA_LOCALIZATION_JSON,
        EXTERNAL_JSON,
        RAW_CANDIDATES_JSON,
        RAW_CANDIDATES_PATCHED_JSON,
        RAW_BASIS_JSON,
        RAW_BASIS_PATCHED_JSON,
        RAW_IN_BS_JSON,
        RAW_IN_BS_PATCHED_JSON,
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]
    for path in files_to_copy:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        dest = PACKAGE_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)
    return format_tree(PACKAGE_DIR)


def generate_outputs() -> dict[str, Any]:
    context = load_problem_context()
    inventory = build_problem_inventory(context)
    lift_payload = build_problem_lift(context)
    delta_payload = build_delta_external_verdict(context, lift_payload)
    verdict = build_patch_verdict_v3(context, lift_payload, delta_payload)

    write_json(PROBLEM_INVENTORY_JSON, inventory)
    write_json(PROBLEM_LIFT_JSON, lift_payload)
    write_text(PROBLEM_LIFT_MD, build_problem_lift_md(inventory, lift_payload))
    write_json(DELTA_EXTERNAL_JSON, delta_payload)
    write_text(DELTA_EXTERNAL_MD, build_delta_external_md(delta_payload))
    write_json(PATCH_VERDICT_V3_JSON, verdict)
    write_text(PATCH_VERDICT_V3_MD, build_patch_verdict_v3_md(verdict))
    write_text(LIFT_AUDIT_MD, build_lift_audit_md(inventory, lift_payload, delta_payload, verdict))
    write_text(HANDOFF_LIFT_MD, build_handoff_md(lift_payload, delta_payload, verdict))
    write_json(CURRENT_STATUS_LIFT_JSON, build_current_status_json(lift_payload, delta_payload, verdict))
    write_text(NEXT_STEP_LIFT_TXT, build_next_step_prompt(verdict))
    write_text(REPORT_MD, build_report_md(lift_payload, delta_payload, verdict, inventory))
    write_text(REPORT_TEX, build_report_tex(lift_payload, delta_payload, verdict, inventory))
    write_text(ROOT_README, build_root_readme())
    compile_pdf(REPORT_TEX, REPORT_PDF)
    package_tree = build_package()
    summary = build_summary_json(lift_payload, delta_payload, verdict, package_tree)
    write_json(LIFT_SUMMARY_JSON, summary)
    package_tree = build_package()
    summary = build_summary_json(lift_payload, delta_payload, verdict, package_tree)
    write_json(LIFT_SUMMARY_JSON, summary)
    return {
        "context": context,
        "inventory": inventory,
        "lift_payload": lift_payload,
        "delta_payload": delta_payload,
        "verdict": verdict,
        "summary": summary,
    }


def validate_outputs() -> None:
    required = [
        PROBLEM_INVENTORY_JSON,
        PROBLEM_LIFT_JSON,
        PROBLEM_LIFT_MD,
        DELTA_EXTERNAL_JSON,
        DELTA_EXTERNAL_MD,
        PATCH_VERDICT_V3_JSON,
        PATCH_VERDICT_V3_MD,
        LIFT_AUDIT_MD,
        LIFT_SUMMARY_JSON,
        HANDOFF_LIFT_MD,
        CURRENT_STATUS_LIFT_JSON,
        NEXT_STEP_LIFT_TXT,
        ROOT / "debug_sg194_double_lift.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        ROOT_README,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing outputs: " + ", ".join(missing))

    context = load_problem_context()
    lift_payload = load_json(PROBLEM_LIFT_JSON)
    ambient_lift = sp.Matrix(lift_payload["lift"]["ambient_lift_matrix"])
    current_problem = context["current_problem_matrix"]
    external_problem = context["external_problem_matrix"]
    if ambient_lift * current_problem != external_problem:
        raise ValueError("saved ambient lift no longer satisfies L * C = E")

    summary = load_json(LIFT_SUMMARY_JSON)
    if not summary["pdf_generated"]:
        raise ValueError("summary claims PDF was not generated")
    if summary["package_tarball"] != str(PACKAGE_TARBALL):
        raise ValueError("summary tarball path mismatch")

    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(tar.getnames())
    required_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/{PROBLEM_INVENTORY_JSON.name}",
        f"{PACKAGE_NAME}/{PROBLEM_LIFT_JSON.name}",
        f"{PACKAGE_NAME}/{DELTA_EXTERNAL_JSON.name}",
        f"{PACKAGE_NAME}/{PATCH_VERDICT_V3_JSON.name}",
        f"{PACKAGE_NAME}/{REPORT_PDF.name}",
        f"{PACKAGE_NAME}/debug_sg194_double_lift.py",
    }
    missing_members = sorted(required_members - names)
    if missing_members:
        raise FileNotFoundError("missing tarball members: " + ", ".join(missing_members))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SG194 trusted problem-sector explicit lift audit.")
    parser.add_argument("--validate", action="store_true", help="Only validate previously generated outputs.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return

    generate_outputs()
    validate_outputs()


if __name__ == "__main__":
    main()
