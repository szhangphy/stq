#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sympy import Matrix, ZZ
from sympy.matrices.normalforms import smith_normal_form


SG194_DIR = Path(__file__).resolve().parent
REPO_ROOT = SG194_DIR.parent
OUTPUT_DIR = SG194_DIR / "topmat_reference_v3" / "data" / "output"

LINDEX_PATH = OUTPUT_DIR / "Lindex_194.263.txt"
BASIS_PATH = OUTPUT_DIR / "basis_194.263.txt"
MSG_AI_PATH = OUTPUT_DIR / "MsgAI_194.263.txt"

OUTPUT_JSON = SG194_DIR / "sg194_topmat_independent_verify_v1.json"
OUTPUT_MD = SG194_DIR / "sg194_topmat_independent_verify_v1.md"

TARGET_STATEMENT = (
    "SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal "
    "magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round "
    "treats them as the same benchmark target for topological classification / "
    "dBS / dAI comparison."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def format_group(finite_part: list[int], free_rank: int) -> str:
    terms: list[str] = [f"Z{value}" for value in finite_part]
    if free_rank == 1:
        terms.append("Z")
    elif free_rank > 1:
        terms.append(f"Z^{free_rank}")
    return " x ".join(terms) if terms else "trivial"


def parse_lindex_factors(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        num_indicators, num_kirreps = map(int, handle.readline().split())
        indicator_group_factors = list(map(int, handle.readline().split()))
    return {
        "path": repo_rel(path),
        "num_indicators": num_indicators,
        "num_kirreps": num_kirreps,
        "indicator_group_factors": indicator_group_factors,
    }


def parse_basis(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    num_rows, num_cols = map(int, lines[0].split())
    invariants = list(map(int, lines[1].replace("Ind:", "").split()))
    labels: list[str] = []
    rows: list[list[int]] = []
    for line in lines[2 : 2 + num_rows]:
        parts = line.split()
        labels.append(parts[0])
        rows.append([int(token) for token in parts[1:]])
    matrix = Matrix(rows)
    independent_row_indices = list(matrix.T.rref()[1])
    if len(independent_row_indices) != num_cols:
        raise ValueError("basis row-minor selection did not recover full column rank")
    invertible_minor = matrix.extract(independent_row_indices, list(range(num_cols)))
    determinant = int(invertible_minor.det())
    if determinant == 0:
        raise ValueError("selected basis row minor is singular")
    return {
        "path": repo_rel(path),
        "labels": labels,
        "shape": [num_rows, num_cols],
        "invariants": invariants,
        "matrix": matrix,
        "independent_row_indices": independent_row_indices,
        "invertible_minor": invertible_minor,
        "invertible_minor_determinant": determinant,
    }


def parse_msg_ai(path: Path) -> dict[str, Any]:
    lines = path.read_text().splitlines()
    _group, num_rows, num_cols = map(int, lines[0].split())
    labels: list[str] = []
    rows: list[list[int]] = []
    generator_names: list[str] = []
    for line in lines[1 : 1 + num_rows]:
        parts = line.split()
        labels.append(parts[0])
        rows.append([int(token) for token in parts[1:]])
    for line in lines[1 + num_rows :]:
        stripped = line.strip()
        if stripped:
            generator_names.append(stripped)
    return {
        "path": repo_rel(path),
        "labels": labels,
        "shape": [num_rows, num_cols],
        "matrix": Matrix(rows),
        "generator_names": generator_names,
    }


def lift_ai_columns_via_row_minor(
    basis: dict[str, Any],
    msg_ai: dict[str, Any],
) -> Matrix:
    if basis["labels"] != msg_ai["labels"]:
        raise ValueError("basis and MsgAI row labels do not match")
    basis_matrix: Matrix = basis["matrix"]
    ai_matrix: Matrix = msg_ai["matrix"]
    independent_rows = basis["independent_row_indices"]
    minor: Matrix = basis["invertible_minor"]
    coords: list[Matrix] = []
    for col_index in range(ai_matrix.cols):
        rhs = ai_matrix.extract(independent_rows, [col_index])
        coordinate = minor.LUsolve(rhs)
        if any(value.q != 1 for value in coordinate):
            raise ValueError(f"AI column {col_index + 1} has non-integral BS coordinates")
        lifted = Matrix([int(value) for value in coordinate])
        if basis_matrix * lifted != ai_matrix[:, col_index]:
            raise ValueError(f"AI column {col_index + 1} failed full-row reconstruction check")
        coords.append(lifted)
    return Matrix.hstack(*coords)


def compute_independent_verification() -> dict[str, Any]:
    lindex = parse_lindex_factors(LINDEX_PATH)
    basis = parse_basis(BASIS_PATH)
    msg_ai = parse_msg_ai(MSG_AI_PATH)

    ai_in_bs = lift_ai_columns_via_row_minor(basis, msg_ai)
    smith = smith_normal_form(ai_in_bs, domain=ZZ)
    smith_diagonal_nonzero = [
        int(smith[index, index])
        for index in range(min(smith.rows, smith.cols))
        if smith[index, index] != 0
    ]
    finite_part = [abs(value) for value in smith_diagonal_nonzero if abs(value) > 1]
    d_bs = int(basis["matrix"].rank())
    d_ai = int(ai_in_bs.rank())
    free_rank = basis["shape"][1] - d_ai
    quotient_group = format_group(finite_part, free_rank)

    return {
        "generated_at": now_iso(),
        "target": {
            "spin_space_group": "194.1.1.1",
            "magnetic_group_og": "194.1.1494",
            "magnetic_group_bns": "194.263",
            "magnetic_type": "Type-I",
            "time_reversal": "absent",
            "project_round_unification_statement": TARGET_STATEMENT,
            "external_mapping_caveat": (
                "Accessible external magnetic-group sources in this round directly "
                "confirm the OG/BNS object and its Type-I character. They do not "
                "independently expose the suffixless SSG label 194.1.1.1 used in "
                "this repo, so the suffixless SSG identification remains a "
                "project/user benchmark convention layer."
            ),
        },
        "input_files": {
            "lindex": lindex["path"],
            "basis": basis["path"],
            "msg_ai": msg_ai["path"],
        },
        "independent_method": {
            "summary": (
                "Independent verifier that parses the copied topmat reference data, "
                "selects a full-rank 10x10 basis row minor from basis_194.263.txt, "
                "solves each MsgAI column through that row minor, verifies full-row "
                "reconstruction, and then performs Smith decomposition on the "
                "resulting AI-in-BS integer matrix."
            ),
            "does_not_reuse_sg194_topmat_experimental_compute_v2_internal_functions": True,
            "basis_row_minor_indices_0_based": basis["independent_row_indices"],
            "basis_row_minor_determinant": basis["invertible_minor_determinant"],
        },
        "shapes": {
            "basis": basis["shape"],
            "msg_ai": msg_ai["shape"],
            "ai_in_bs": [ai_in_bs.rows, ai_in_bs.cols],
        },
        "consistency_cross_checks": {
            "lindex_indicator_group_factors": lindex["indicator_group_factors"],
            "basis_invariants": basis["invariants"],
            "basis_invariants_match_smith_diagonal": basis["invariants"] == smith_diagonal_nonzero,
            "lindex_finite_factors_match_quotient": lindex["indicator_group_factors"] == finite_part,
        },
        "result": {
            "classification": quotient_group,
            "indicator_group": quotient_group,
            "dBS": d_bs,
            "dAI": d_ai,
            "smith_diagonal_nonzero": smith_diagonal_nonzero,
            "finite_part": finite_part,
            "free_rank": free_rank,
        },
    }


def render_md(payload: dict[str, Any]) -> str:
    result = payload["result"]
    method = payload["independent_method"]
    checks = payload["consistency_cross_checks"]
    lines = [
        "# SG194 topmat independent verify v1",
        "",
        payload["target"]["project_round_unification_statement"],
        "",
        "## Result",
        "",
        f"- classification / indicator group: `{result['classification']}`",
        f"- dBS: `{result['dBS']}`",
        f"- dAI: `{result['dAI']}`",
        f"- Smith nonzero diagonal: `{result['smith_diagonal_nonzero']}`",
        f"- finite part: `{result['finite_part']}`",
        f"- free rank: `{result['free_rank']}`",
        "",
        "## Independent method",
        "",
        f"- summary: {method['summary']}",
        f"- basis row minor indices (0-based): `{method['basis_row_minor_indices_0_based']}`",
        f"- basis row minor determinant: `{method['basis_row_minor_determinant']}`",
        "",
        "## Cross-checks",
        "",
        f"- Lindex indicator factors: `{checks['lindex_indicator_group_factors']}`",
        f"- basis invariants: `{checks['basis_invariants']}`",
        f"- basis invariants match Smith diagonal: `{str(checks['basis_invariants_match_smith_diagonal']).lower()}`",
        f"- Lindex finite factors match quotient: `{str(checks['lindex_finite_factors_match_quotient']).lower()}`",
        "",
        "## Input files",
        "",
        f"- Lindex: `{payload['input_files']['lindex']}`",
        f"- basis: `{payload['input_files']['basis']}`",
        f"- MsgAI: `{payload['input_files']['msg_ai']}`",
    ]
    return "\n".join(lines)


def main() -> int:
    payload = compute_independent_verification()
    write_json(OUTPUT_JSON, payload)
    write_text(OUTPUT_MD, render_md(payload))
    print(
        json.dumps(
            {
                "status": "ok",
                "output_json": repo_rel(OUTPUT_JSON),
                "output_md": repo_rel(OUTPUT_MD),
                "result": payload["result"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
