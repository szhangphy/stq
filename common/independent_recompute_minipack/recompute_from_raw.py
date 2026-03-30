#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CASES = [
    ("10.4.1.31", 1, "raw_10_4_1_31_single"),
    ("10.4.1.31", 2, "raw_10_4_1_31_double"),
    ("194.1.1.1", 1, "raw_194_1_1_1_single"),
    ("194.1.1.1", 2, "raw_194_1_1_1_double"),
]


def load_json(path: Path):
    return json.loads(path.read_text())


def matrix_from_rows(rows):
    return sp.Matrix(rows)


def matrix_from_columns(columns):
    if not columns:
        return sp.zeros(0, 0)
    return sp.Matrix.hstack(*[sp.Matrix(column) for column in columns])


def smith_rank_and_diagonal(D: sp.Matrix):
    diagonal = []
    for idx in range(min(D.rows, D.cols)):
        value = int(D[idx, idx])
        if value != 0:
            diagonal.append(abs(value))
    return len(diagonal), diagonal


def quotient_string(free_rank, finite_part):
    parts = []
    if free_rank > 0:
        parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts) if parts else "trivial"


def main():
    for group, group_type, prefix in CASES:
        raw_c = load_json(RAW / f"{prefix}_C.json")
        raw_bs = load_json(RAW / f"{prefix}_bs_basis_raw.json")
        raw_ai = load_json(RAW / f"{prefix}_ai_basis.json")

        C = matrix_from_rows(raw_c["matrix"])
        D_C, _, V_C = smith_normal_decomp(C, domain=ZZ)
        rank_C, _ = smith_rank_and_diagonal(D_C)
        bs_basis = matrix_from_columns([item["vector"] for item in raw_bs["basis_vectors"]])
        rank_BS = int(bs_basis.cols)

        ai_basis = matrix_from_columns(raw_ai["basis_bs_coefficients"])
        D_AI, _, _ = smith_normal_decomp(ai_basis, domain=ZZ)
        rank_AI, diag_AI = smith_rank_and_diagonal(D_AI)
        free_rank = int(ai_basis.rows - rank_AI)
        finite_part = [value for value in diag_AI if value > 1]
        ai_unknown = bs_basis * ai_basis if ai_basis.cols else sp.zeros(bs_basis.rows, 0)
        ai_subset_bs = C * ai_unknown == sp.zeros(C.rows, ai_unknown.cols)

        print(f"{group} / groupType={group_type}")
        print(f"  rank(C) = {rank_C}")
        print(f"  rank(BS) = {rank_BS}")
        print(f"  rank(AI) = {rank_AI}")
        print(f"  AI subset BS = {ai_subset_bs}")
        print(f"  coker(AI->BS) = {quotient_string(free_rank, finite_part)}")
        print(f"  free rank = {free_rank}")
        print(f"  finite part = {finite_part}")
        print()


if __name__ == "__main__":
    main()
