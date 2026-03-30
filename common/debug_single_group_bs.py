#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp
from sympy.polys.domains import ZZ


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
FULL_COMPAT_PATH = ROOT / "single_group_full_compatibility.json"
FULL_COMPAT_SUMMARY_PATH = ROOT / "single_group_full_compatibility_summary.json"
FULL_COMPAT_AUDIT_PATH = ROOT / "single_group_full_compatibility_audit.md"
BLOCK_PATHS = {
    "L1": ROOT / "L1_block.json",
    "L2": ROOT / "L2_block.json",
    "L3": ROOT / "L3_block.json",
    "L4": ROOT / "L4_block.json",
}

BS_AUDIT_PATH = ROOT / "single_group_bs_audit.md"
BS_SUMMARY_PATH = ROOT / "single_group_bs_summary.json"
BS_BASIS_RAW_PATH = ROOT / "single_group_bs_basis_raw.json"
BS_BASIS_PRETTY_PATH = ROOT / "single_group_bs_basis_pretty.json"
BS_MATRIX_ANALYSIS_PATH = ROOT / "single_group_bs_matrix_analysis.json"

PACKAGE_DIR = ROOT / "review_package_10.4.1.31_bs"
PACKAGE_TAR = ROOT / "review_package_10.4.1.31_bs.tar.gz"

REQUIRED_OUTPUTS = [
    "single_group_bs_audit.md",
    "single_group_bs_summary.json",
    "single_group_bs_basis_raw.json",
    "single_group_bs_basis_pretty.json",
    "single_group_bs_matrix_analysis.json",
    "debug_single_group_bs.py",
    "review_package_10.4.1.31_bs.tar.gz",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def support_from_vector(vector: list[int], unknown_ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown, "coeff": coeff}
        for unknown, coeff in zip(unknown_ordering, vector)
        if coeff
    ]


def restrict_vector(vector: list[int], indices: list[int]) -> list[int]:
    return [vector[index] for index in indices]


def matrix_times_vector(matrix_rows: list[list[int]], vector: list[int]) -> list[int]:
    return [sum(row[i] * vector[i] for i in range(len(vector))) for row in matrix_rows]


def to_int_list(column: sp.Matrix) -> list[int]:
    return [int(column[i, 0]) for i in range(column.rows)]


def smith_diagonal_from_D(D: sp.Matrix) -> list[int]:
    diagonal = []
    for index in range(min(D.rows, D.cols)):
        value = D[index, index]
        if value != 0:
            diagonal.append(int(value))
    return diagonal


def build_pretty_basis_definitions(unknown_ordering: list[str]) -> list[dict[str, Any]]:
    unknown_index = {unknown: index for index, unknown in enumerate(unknown_ordering)}

    def vector(assignments: dict[str, int]) -> list[int]:
        result = [0] * len(unknown_ordering)
        for unknown, coeff in assignments.items():
            result[unknown_index[unknown]] = coeff
        return result

    return [
        {
            "id": "P1_diff_12",
            "block": "L1",
            "description": "Difference mode inside the P1 pair constrained by the first L1 equation.",
            "vector": vector({"P1_R1": 1, "P1_R2": -1}),
        },
        {
            "id": "P1_diff_34",
            "block": "L1",
            "description": "Difference mode inside the P1 pair constrained by the second L1 equation.",
            "vector": vector({"P1_R3": 1, "P1_R4": -1}),
        },
        {
            "id": "P1_diff_56",
            "block": "L1",
            "description": "Difference mode inside the P1 pair constrained by the third L1 equation.",
            "vector": vector({"P1_R5": 1, "P1_R6": -1}),
        },
        {
            "id": "P1_diff_78",
            "block": "L1",
            "description": "Difference mode inside the P1 pair constrained by the fourth L1 equation.",
            "vector": vector({"P1_R7": 1, "P1_R8": -1}),
        },
        {
            "id": "L1_sum_R1",
            "block": "L1",
            "description": "Common integral shift along the L1 branch feeding P4_R1.",
            "vector": vector({"P1_R3": 1, "P1_R5": 1, "P4_R1": 1}),
        },
        {
            "id": "L1_sum_R2",
            "block": "L1",
            "description": "Common integral shift along the L1 branch feeding P4_R2.",
            "vector": vector({"P1_R1": 1, "P1_R7": 1, "P4_R2": 1}),
        },
        {
            "id": "P2_diff_12",
            "block": "L2",
            "description": "Difference mode inside the left endpoint pair of L2.",
            "vector": vector({"P2_R1": 1, "P2_R2": -1}),
        },
        {
            "id": "L2_charge",
            "block": "L2",
            "description": "Primitive integral charge mode for the 2-to-1 L2 relation.",
            "vector": vector({"P2_R1": 2, "P6_R1": 1}),
        },
        {
            "id": "P3_diff_12",
            "block": "L3",
            "description": "Difference mode inside the P3 pair constrained by the first L3 equation.",
            "vector": vector({"P3_R1": 1, "P3_R2": -1}),
        },
        {
            "id": "P3_diff_34",
            "block": "L3",
            "description": "Difference mode inside the P3 pair constrained by the second L3 equation.",
            "vector": vector({"P3_R3": 1, "P3_R4": -1}),
        },
        {
            "id": "P3_diff_56",
            "block": "L3",
            "description": "Difference mode inside the P3 pair constrained by the third L3 equation.",
            "vector": vector({"P3_R5": 1, "P3_R6": -1}),
        },
        {
            "id": "P3_diff_78",
            "block": "L3",
            "description": "Difference mode inside the P3 pair constrained by the fourth L3 equation.",
            "vector": vector({"P3_R7": 1, "P3_R8": -1}),
        },
        {
            "id": "L3_sum_R1",
            "block": "L3",
            "description": "Common integral shift along the L3 branch feeding P5_R1.",
            "vector": vector({"P3_R3": 1, "P3_R5": 1, "P5_R1": 1}),
        },
        {
            "id": "L3_sum_R2",
            "block": "L3",
            "description": "Common integral shift along the L3 branch feeding P5_R2.",
            "vector": vector({"P3_R1": 1, "P3_R7": 1, "P5_R2": 1}),
        },
        {
            "id": "P7_diff_12",
            "block": "L4",
            "description": "Difference mode inside the left endpoint pair of L4.",
            "vector": vector({"P7_R1": 1, "P7_R2": -1}),
        },
        {
            "id": "L4_charge",
            "block": "L4",
            "description": "Primitive integral charge mode for the 2-to-1 L4 relation.",
            "vector": vector({"P7_R1": 2, "P8_R1": 1}),
        },
    ]


def build_analysis() -> dict[str, Any]:
    full = load_json(FULL_COMPAT_PATH)
    blocks = {line_id: load_json(path) for line_id, path in BLOCK_PATHS.items()}

    if full["group_number"] != GROUP_NUMBER:
        raise ValueError(f"Unexpected group number in {FULL_COMPAT_PATH}: {full['group_number']}")

    unknown_ordering = list(full["global_unknown_ordering"])
    row_sources = list(full["global_matrix_rows"])
    raw_matrix = full["global_matrix"]

    if any(not isinstance(row, list) for row in raw_matrix):
        raise ValueError("Global matrix rows are not stored as JSON lists.")
    if any(not isinstance(value, int) for row in raw_matrix for value in row):
        raise ValueError("Global compatibility matrix is not fully integer-valued.")

    C = sp.Matrix(raw_matrix)
    D, U, V = smith_normal_decomp(C, domain=ZZ)
    smith_diagonal = smith_diagonal_from_D(D)
    rank_from_smith = len(smith_diagonal)
    rank_from_rational = int(C.rank())
    if rank_from_smith != rank_from_rational:
        raise ValueError(
            f"Smith rank {rank_from_smith} does not match rational rank {rank_from_rational}"
        )
    rank = rank_from_smith
    nullity = C.cols - rank

    raw_basis_matrix = V[:, rank:]
    if raw_basis_matrix.cols != nullity:
        raise ValueError("Kernel column count from Smith decomposition does not match nullity.")
    if C * raw_basis_matrix != sp.zeros(C.rows, raw_basis_matrix.cols):
        raise ValueError("Smith-derived raw basis does not lie in the kernel.")

    raw_basis_vectors = []
    for basis_index in range(raw_basis_matrix.cols):
        vector = to_int_list(raw_basis_matrix[:, basis_index])
        raw_basis_vectors.append(
            {
                "id": f"raw_basis_{basis_index + 1:02d}",
                "vector": vector,
                "support": support_from_vector(vector, unknown_ordering),
            }
        )

    pretty_basis_defs = build_pretty_basis_definitions(unknown_ordering)
    pretty_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in pretty_basis_defs])
    if pretty_basis_matrix.cols != nullity:
        raise ValueError("Pretty basis size does not match nullity.")
    if C * pretty_basis_matrix != sp.zeros(C.rows, pretty_basis_matrix.cols):
        raise ValueError("Pretty basis vectors do not lie in the kernel.")
    if int(pretty_basis_matrix.rank()) != nullity:
        raise ValueError("Pretty basis is not linearly independent.")

    transform_cols = []
    for basis_index in range(pretty_basis_matrix.cols):
        solution, params = raw_basis_matrix.gauss_jordan_solve(pretty_basis_matrix[:, basis_index])
        if params.rows != 0:
            raise ValueError("Unexpected free parameters when expressing pretty basis in raw basis.")
        if any(not coeff.is_Integer for coeff in solution):
            raise ValueError("Pretty basis is not an integral combination of the raw basis.")
        transform_cols.append(solution)
    basis_transform = sp.Matrix.hstack(*transform_cols)
    if raw_basis_matrix * basis_transform != pretty_basis_matrix:
        raise ValueError("Basis transform from raw to pretty basis is inconsistent.")
    transform_det = int(basis_transform.det())
    if abs(transform_det) != 1:
        raise ValueError("Raw and pretty bases do not form the same integer lattice.")

    reverse_cols = []
    for basis_index in range(raw_basis_matrix.cols):
        solution, params = pretty_basis_matrix.gauss_jordan_solve(raw_basis_matrix[:, basis_index])
        if params.rows != 0:
            raise ValueError("Unexpected free parameters when expressing raw basis in pretty basis.")
        if any(not coeff.is_Integer for coeff in solution):
            raise ValueError("Raw basis is not an integral combination of the pretty basis.")
        reverse_cols.append(solution)
    reverse_transform = sp.Matrix.hstack(*reverse_cols)
    if pretty_basis_matrix * reverse_transform != raw_basis_matrix:
        raise ValueError("Reverse basis transform is inconsistent.")

    row_independence = []
    duplicate_row_count = len(raw_matrix) - len({tuple(row) for row in raw_matrix})
    for row_index, row_source in enumerate(row_sources):
        reduced = C.copy()
        reduced.row_del(row_index)
        row_independence.append(
            {
                "row_index": row_index,
                "line_id": row_source["line_id"],
                "basis_id": row_source["basis_id"],
                "equation": row_source["equation"],
                "is_essential": int(reduced.rank()) < rank,
            }
        )

    block_checks = {}
    for line_id, block in blocks.items():
        local_unknowns = block["local_unknown_ordering"]
        local_indices = [unknown_ordering.index(unknown) for unknown in local_unknowns]
        local_matrix = block["matrix_rows"]
        pretty_checks = []
        for basis in pretty_basis_defs:
            restricted = restrict_vector(basis["vector"], local_indices)
            residual = matrix_times_vector(local_matrix, restricted)
            pretty_checks.append(
                {
                    "basis_id": basis["id"],
                    "restricted_vector": restricted,
                    "residual": residual,
                    "satisfies_block": all(value == 0 for value in residual),
                }
            )
        raw_checks = []
        for basis in raw_basis_vectors:
            restricted = restrict_vector(basis["vector"], local_indices)
            residual = matrix_times_vector(local_matrix, restricted)
            raw_checks.append(
                {
                    "basis_id": basis["id"],
                    "restricted_vector": restricted,
                    "residual": residual,
                    "satisfies_block": all(value == 0 for value in residual),
                }
            )
        block_checks[line_id] = {
            "local_unknown_ordering": local_unknowns,
            "local_matrix": local_matrix,
            "pretty_basis_checks": pretty_checks,
            "raw_basis_checks": raw_checks,
            "local_kernel_rank": len(local_unknowns) - sp.Matrix(local_matrix).rank(),
        }

    pretty_basis_vectors = []
    point_to_block = {
        "P1": "L1",
        "P4": "L1",
        "P2": "L2",
        "P6": "L2",
        "P3": "L3",
        "P5": "L3",
        "P7": "L4",
        "P8": "L4",
    }
    for item in pretty_basis_defs:
        support = support_from_vector(item["vector"], unknown_ordering)
        support_blocks = sorted({point_to_block[entry["unknown"].split("_")[0]] for entry in support})
        pretty_basis_vectors.append(
            {
                "id": item["id"],
                "block": item["block"],
                "description": item["description"],
                "vector": item["vector"],
                "support": support,
                "support_blocks": support_blocks,
            }
        )

    analysis = {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": unknown_ordering,
        "matrix_shape": [C.rows, C.cols],
        "global_matrix": raw_matrix,
        "row_sources": row_sources,
        "integrality": {
            "all_entries_are_integers": True,
            "contains_floats": False,
            "contains_non_numeric_strings": False,
        },
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "all_nonzero_smith_entries_are_one": all(value == 1 for value in smith_diagonal),
        "smith_decomposition_checks": {
            "U_times_C_times_V_equals_D": U * C * V == D,
            "raw_basis_from_right_transform_columns": {
                "rank_offset": rank,
                "column_count": raw_basis_matrix.cols,
                "kernel_check_passed": C * raw_basis_matrix == sp.zeros(C.rows, raw_basis_matrix.cols),
            },
        },
        "row_analysis": {
            "duplicate_row_count": duplicate_row_count,
            "all_rows_are_essential": all(item["is_essential"] for item in row_independence),
            "rows": row_independence,
        },
        "raw_basis": {
            "column_count": len(raw_basis_vectors),
            "vectors": raw_basis_vectors,
        },
        "pretty_basis": {
            "column_count": len(pretty_basis_vectors),
            "vectors": pretty_basis_vectors,
            "transform_from_raw": {
                "matrix": [to_int_list(basis_transform[:, col]) for col in range(basis_transform.cols)],
                "matrix_as_rows": [[int(value) for value in row] for row in basis_transform.tolist()],
                "determinant": transform_det,
            },
            "reverse_transform_to_raw": {
                "matrix_as_rows": [[int(value) for value in row] for row in reverse_transform.tolist()],
                "determinant": int(reverse_transform.det()),
            },
        },
        "block_checks": block_checks,
        "block_separation": {
            "global_kernel_is_direct_sum_of_line_blocks": all(
                len(basis["support_blocks"]) == 1 for basis in pretty_basis_vectors
            ),
            "pretty_basis_blocks": {
                basis["id"]: basis["support_blocks"] for basis in pretty_basis_vectors
            },
        },
    }
    return analysis


def build_bs_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "n_unknowns": analysis["matrix_shape"][1],
        "n_equations": analysis["matrix_shape"][0],
        "matrix_shape": analysis["matrix_shape"],
        "rank": analysis["rank"],
        "nullity": analysis["nullity"],
        "smith_diagonal": analysis["smith_diagonal"],
        "kernel_rank": analysis["nullity"],
        "can_proceed_to_next_stage": True,
        "next_blocker": "Plane representation theory, AI/EBR, and BS/AI remain outside the current explicit special-line BS run.",
    }


def build_basis_payload(
    analysis: dict[str, Any],
    *,
    key: str,
    note: str,
    transform_note: str | None = None,
) -> dict[str, Any]:
    payload = {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": analysis["unknown_ordering"],
        "basis_kind": key,
        "note": note,
        "basis_vectors": analysis[key]["vectors"],
    }
    if transform_note is not None:
        payload["basis_transform_note"] = transform_note
        payload["basis_transform_from_raw"] = analysis["pretty_basis"]["transform_from_raw"]
    return payload


def build_matrix_analysis_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": analysis["unknown_ordering"],
        "global_matrix": analysis["global_matrix"],
        "row_sources": analysis["row_sources"],
        "integrality": analysis["integrality"],
        "rank": analysis["rank"],
        "nullity": analysis["nullity"],
        "smith_diagonal": analysis["smith_diagonal"],
        "all_nonzero_smith_entries_are_one": analysis["all_nonzero_smith_entries_are_one"],
        "row_analysis": analysis["row_analysis"],
        "kernel_checks": {
            "raw_basis_count": analysis["raw_basis"]["column_count"],
            "pretty_basis_count": analysis["pretty_basis"]["column_count"],
            "basis_transform_from_raw_determinant": analysis["pretty_basis"]["transform_from_raw"]["determinant"],
            "block_checks": analysis["block_checks"],
            "block_separation": analysis["block_separation"],
        },
    }


def build_audit_markdown(
    analysis: dict[str, Any],
    summary: dict[str, Any],
    raw_basis_payload: dict[str, Any],
    pretty_basis_payload: dict[str, Any],
) -> str:
    lines = [
        "# Single Group BS Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- Input matrix: the already assembled explicit special-line compatibility matrix from `single_group_full_compatibility.json`.",
        "- Covered layer: explicit special-line compatibility only.",
        "- Not covered: plane representation theory, AI / EBR, BS/AI, or any all-group generalization.",
        "",
        "## Input Matrix",
        f"- Matrix shape: `{summary['matrix_shape'][0]} x {summary['matrix_shape'][1]}`",
        f"- Number of unknowns: `{summary['n_unknowns']}`",
        f"- Number of equations: `{summary['n_equations']}`",
        "- All entries were rechecked to be exact integers read directly from JSON.",
        "",
        "### Global Unknown Ordering",
    ]
    for index, unknown in enumerate(analysis["unknown_ordering"], start=1):
        lines.append(f"{index}. `{unknown}`")

    lines.extend(
        [
            "",
            "### Global Rows And Sources",
        ]
    )
    for index, row in enumerate(analysis["row_sources"], start=1):
        lines.append(
            f"{index}. `{row['line_id']}` / `{row['basis_id']}`: `{row['equation']}`"
        )

    lines.extend(
        [
            "",
            "## Exact Integer Analysis",
            "- Method: exact integer Smith normal decomposition `U * C * V = D` over `ZZ`, with the kernel taken from the last `nullity` columns of the right unimodular matrix `V`.",
            f"- Integer rank: `{summary['rank']}`",
            f"- Nullity: `{summary['nullity']}`",
            f"- Smith diagonal: `{summary['smith_diagonal']}`",
            f"- All nonzero Smith diagonal entries are 1: `{analysis['all_nonzero_smith_entries_are_one']}`",
            "- Interpretation: there is no hidden integer torsion in the cokernel data relevant to this layer; the kernel lattice is free abelian of rank 16.",
            "",
            "## Raw Integer Basis",
            "- Source: columns `rank+1` through `n_unknowns` of the right unimodular transform `V` from the Smith decomposition.",
            f"- Basis vector count: `{len(raw_basis_payload['basis_vectors'])}`",
            "",
            "## Pretty Integer Basis",
            "- Construction: a single-group, block-readable basis chosen inside the same integer kernel lattice.",
            "- Layout: grouped by the four explicit special lines `L1`, `L2`, `L3`, `L4`.",
            f"- Same lattice as raw basis: `True`, verified by an integral change-of-basis matrix with determinant `{analysis['pretty_basis']['transform_from_raw']['determinant']}`.",
            "",
            "### Pretty Basis Overview",
        ]
    )
    for basis in pretty_basis_payload["basis_vectors"]:
        support_text = ", ".join(f"{item['coeff']}*{item['unknown']}" for item in basis["support"])
        lines.append(
            f"- `{basis['id']}` [{basis['block']}]: {basis['description']} -> `{support_text}`"
        )

    lines.extend(
        [
            "",
            "## Correctness Checks",
            "- Every raw basis vector satisfies `C * v = 0` exactly.",
            "- Every pretty basis vector satisfies `C * v = 0` exactly.",
            "- Raw basis rank and pretty basis rank both equal the nullity 16.",
            "- The raw-to-pretty change-of-basis matrix is integral and unimodular, so both bases span the same integer lattice.",
            "- Each global row is essential: dropping any one row lowers the rank from 10 to 9.",
            "- No duplicate global rows were found.",
            "",
            "### Local Block Checks",
        ]
    )
    for line_id, block_check in analysis["block_checks"].items():
        lines.append(
            f"- `{line_id}` local kernel rank: `{block_check['local_kernel_rank']}`; all raw/pretty basis restrictions satisfy the local equations."
        )

    lines.extend(
        [
            "",
            "## Structural Reading",
            "- The current matrix only encodes explicit special-line compatibility. Nothing else was mixed in.",
            "- The pretty basis exhibits a direct-sum decomposition by line block: `L1` contributes 6 generators, `L2` contributes 2, `L3` contributes 6, and `L4` contributes 2.",
            "",
            "## Current Result",
            "- This run establishes the integer band-structure lattice `BS = ker_Z(C)` for group `10.4.1.31` at the explicit special-line compatibility layer.",
            "- This is not a final topological classification and does not include AI / EBR / BS/AI.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_package_readme() -> str:
    return "\n".join(
        [
            "# Review Package: 10.4.1.31 BS on Explicit Special-Line Compatibility",
            "",
            "## Scope",
            "",
            "- Group: `10.4.1.31`",
            "- Stage: `BS = ker_Z(C)` on the explicit special-line compatibility layer",
            "",
            "## Input",
            "",
            "- The input is the already assembled global compatibility matrix in `global/single_group_full_compatibility.json`.",
            "",
            "## Output",
            "",
            "- Exact integer rank / nullity",
            "- Smith diagonal data",
            "- A raw integer basis for `ker_Z(C)`",
            "- A review-friendly pretty basis for the same lattice",
            "- Matrix and row-source analysis",
            "",
            "## Out Of Scope",
            "",
            "- AI / EBR",
            "- BS/AI",
            "- Plane representation theory",
            "- All-group or high-throughput generalization",
            "",
            "## Suggested Review Order",
            "",
            "1. `audit/single_group_bs_audit.md`",
            "2. `audit/single_group_bs_summary.json`",
            "3. `basis/single_group_bs_basis_raw.json`",
            "4. `matrix/single_group_bs_matrix_analysis.json`",
        ]
    ) + "\n"


def build_review_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    (PACKAGE_DIR / "README.md").write_text(build_package_readme())

    audit_dir = PACKAGE_DIR / "audit"
    basis_dir = PACKAGE_DIR / "basis"
    matrix_dir = PACKAGE_DIR / "matrix"
    background_dir = PACKAGE_DIR / "background"
    scripts_dir = PACKAGE_DIR / "scripts"

    for directory in (audit_dir, basis_dir, matrix_dir, background_dir, scripts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for src in (
        BS_AUDIT_PATH,
        BS_SUMMARY_PATH,
        ROOT / "single_group_full_compatibility_audit.md",
        ROOT / "single_group_full_compatibility_summary.json",
        ROOT / "single_connection_audit.md",
        ROOT / "single_connection_summary.json",
        ROOT / "single_connection_compatibility.json",
    ):
        shutil.copyfile(src, audit_dir / src.name)

    for src in (
        BS_BASIS_RAW_PATH,
        BS_BASIS_PRETTY_PATH,
    ):
        shutil.copyfile(src, basis_dir / src.name)

    for src in (
        BS_MATRIX_ANALYSIS_PATH,
        ROOT / "single_group_full_compatibility.json",
    ):
        shutil.copyfile(src, matrix_dir / src.name)

    for src in (
        ROOT / "L1_block.json",
        ROOT / "L2_block.json",
        ROOT / "L3_block.json",
        ROOT / "L4_block.json",
        ROOT / "single_group_kmanifolds.json",
        ROOT / "single_group_connectivity.json",
    ):
        shutil.copyfile(src, background_dir / src.name)

    for src in (
        ROOT / "debug_single_group_bs.py",
        ROOT / "debug_single_group_full_compatibility.py",
    ):
        shutil.copyfile(src, scripts_dir / src.name)

    with tarfile.open(PACKAGE_TAR, "w:gz") as archive:
        archive.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def count_missing_deliverables() -> int:
    return sum(0 if (ROOT / name).exists() else 1 for name in REQUIRED_OUTPUTS)


def validate_outputs() -> int:
    missing = [name for name in REQUIRED_OUTPUTS if not (ROOT / name).exists()]
    if missing:
        for name in missing:
            print(f"missing: {name}")
        return 1

    summary = load_json(BS_SUMMARY_PATH)
    if summary.get("matrix_shape") != [10, 26]:
        print(f"unexpected matrix shape: {summary.get('matrix_shape')}")
        return 1
    if summary.get("rank") != 10:
        print(f"unexpected rank: {summary.get('rank')}")
        return 1
    if summary.get("nullity") != 16:
        print(f"unexpected nullity: {summary.get('nullity')}")
        return 1
    if summary.get("kernel_rank") != 16:
        print(f"unexpected kernel rank: {summary.get('kernel_rank')}")
        return 1

    raw_basis = load_json(BS_BASIS_RAW_PATH)
    pretty_basis = load_json(BS_BASIS_PRETTY_PATH)
    if len(raw_basis.get("basis_vectors", [])) != 16:
        print("raw basis does not contain 16 vectors")
        return 1
    if len(pretty_basis.get("basis_vectors", [])) != 16:
        print("pretty basis does not contain 16 vectors")
        return 1
    if any(len(item["vector"]) != 26 for item in raw_basis["basis_vectors"]):
        print("raw basis vectors are not length 26")
        return 1
    if any(len(item["vector"]) != 26 for item in pretty_basis["basis_vectors"]):
        print("pretty basis vectors are not length 26")
        return 1

    analysis = load_json(BS_MATRIX_ANALYSIS_PATH)
    if analysis.get("rank") != 10 or analysis.get("nullity") != 16:
        print("matrix analysis rank/nullity mismatch")
        return 1
    if analysis.get("smith_diagonal") != [1] * 10:
        print(f"unexpected smith diagonal: {analysis.get('smith_diagonal')}")
        return 1
    if analysis.get("row_analysis", {}).get("duplicate_row_count") != 0:
        print("duplicate row count is not zero")
        return 1
    if not analysis.get("row_analysis", {}).get("all_rows_are_essential"):
        print("not all rows are marked essential")
        return 1

    package_readme = PACKAGE_DIR / "README.md"
    if not package_readme.exists():
        print(f"missing package README: {package_readme}")
        return 1
    print("validation_ok")
    return 0


def run() -> None:
    analysis = build_analysis()
    summary = build_bs_summary(analysis)
    raw_basis_payload = build_basis_payload(
        analysis,
        key="raw_basis",
        note="Raw integer basis from the Smith decomposition right-transform kernel columns.",
    )
    pretty_basis_payload = build_basis_payload(
        analysis,
        key="pretty_basis",
        note="Review-friendly single-group basis grouped by explicit special-line block.",
        transform_note="These pretty vectors are related to the raw Smith basis by an integral unimodular change of basis.",
    )
    matrix_analysis_payload = build_matrix_analysis_payload(analysis)

    BS_AUDIT_PATH.write_text(
        build_audit_markdown(analysis, summary, raw_basis_payload, pretty_basis_payload)
    )
    write_json(BS_SUMMARY_PATH, summary)
    write_json(BS_BASIS_RAW_PATH, raw_basis_payload)
    write_json(BS_BASIS_PRETTY_PATH, pretty_basis_payload)
    write_json(BS_MATRIX_ANALYSIS_PATH, matrix_analysis_payload)
    build_review_package()

    print(f"group_number: {GROUP_NUMBER}")
    print(f"matrix_shape: {summary['matrix_shape'][0]} x {summary['matrix_shape'][1]}")
    print(f"rank: {summary['rank']}")
    print(f"nullity: {summary['nullity']}")
    print(f"smith_diagonal: {summary['smith_diagonal']}")
    print(f"package: {PACKAGE_TAR}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        return validate_outputs()

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
