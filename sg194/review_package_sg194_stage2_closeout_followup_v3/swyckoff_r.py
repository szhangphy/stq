#!/usr/bin/env python3
"""
Standalone quotient-based real-space Wyckoff enumerator.

This file is derived from the standalone swyckoff_k core plus the quotient
expansion logic from swyckoff_r.py, so it no longer imports local helper
modules such as mwyckoff.py or swyckoff_k.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
import os
import re
import string
import sys
import time
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

Vec = List[Fraction]
Mat = List[List[Fraction]]
NumericVec = List[float]
NumericMat = List[List[float]]

SCHOENFLIES_TO_HM = {
    "C1": "1",
    "Ci": "-1",
    "C2": "2",
    "Cs": "m",
    "C2h": "2/m",
    "D2": "222",
    "C2v": "mm2",
    "D2h": "mmm",
    "C4": "4",
    "S4": "-4",
    "C4h": "4/m",
    "D4": "422",
    "C4v": "4mm",
    "D2d": "-42m",
    "D4h": "4/mmm",
    "C3": "3",
    "C3h": "-6",
    "C3i": "-3",
    "D3": "32",
    "C3v": "3m",
    "D3d": "-3m",
    "D3h": "-6m2",
    "C6": "6",
    "C6h": "6/m",
    "C6v": "6mm",
    "D6": "622",
    "D6h": "6/mmm",
    "T": "23",
    "Th": "m-3",
    "O": "432",
    "Td": "-43m",
    "Oh": "m-3m",
}

# global flag toggled inside derive_wyckoff to simplify plumbing
RECIPROCAL_MODE = False

# --- optional sympy SNF (import once) ----------------------------------------
try:
    import sympy as _sp  # type: ignore
    from sympy.matrices.normalforms import smith_normal_decomp as _smith_normal_decomp  # type: ignore

    _HAVE_SYMPY_SNF = True
except Exception:
    _sp = None
    _smith_normal_decomp = None
    _HAVE_SYMPY_SNF = False


# --- linear algebra over fractions ------------------------------------------

def frac(x: float, max_den: int = 48) -> Fraction:
    return Fraction(x).limit_denominator(max_den)


def mod1(v: Fraction) -> Fraction:
    v = v % 1
    if v < 0:
        v += 1
    return v


def mod1_vec(vec: Sequence[Fraction]) -> List[Fraction]:
    return [mod1(x) for x in vec]


def identity_mat() -> Mat:
    return [
        [Fraction(1), Fraction(0), Fraction(0)],
        [Fraction(0), Fraction(1), Fraction(0)],
        [Fraction(0), Fraction(0), Fraction(1)],
    ]


def mat_transpose(M: Mat) -> Mat:
    return [[M[j][i] for j in range(3)] for i in range(3)]


def mat_mul(A: Mat, B: Mat) -> Mat:
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def mat_inv(M: Mat) -> Mat:
    det = (
        M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
        - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
        + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
    )
    if det == 0:
        raise ValueError("Matrix is not invertible")

    cof = [
        [
            (M[(i + 1) % 3][(j + 1) % 3] * M[(i + 2) % 3][(j + 2) % 3]
             - M[(i + 1) % 3][(j + 2) % 3] * M[(i + 2) % 3][(j + 1) % 3])
            for j in range(3)
        ]
        for i in range(3)
    ]
    adj = mat_transpose(cof)
    return [[adj[i][j] / det for j in range(3)] for i in range(3)]


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Return (g, x, y) with ax + by = g = gcd(a, b)."""
    old_r, r = abs(a), abs(b)
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    g = old_r
    x = old_s if a >= 0 else -old_s
    y = old_t if b >= 0 else -old_t
    return g, x, y


def smith_normal_form_fallback(mat_int: List[List[int]]) -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
    """
    Pure-python Smith normal form (fallback).
    SymPy fast path is handled globally in _smith_cached (import once + cache).
    """
    A = [row[:] for row in mat_int]
    m = len(A)
    n = len(A[0]) if m else 0

    def eye(k: int) -> List[List[int]]:
        return [[1 if i == j else 0 for j in range(k)] for i in range(k)]

    def swap_rows(M: List[List[int]], i: int, j: int) -> None:
        M[i], M[j] = M[j], M[i]

    def swap_cols(M: List[List[int]], i: int, j: int) -> None:
        for r in range(len(M)):
            M[r][i], M[r][j] = M[r][j], M[r][i]

    def row_add(M: List[List[int]], dst: int, src: int, k: int) -> None:
        if k == 0:
            return
        M[dst] = [a + k * b for a, b in zip(M[dst], M[src])]

    def col_add(M: List[List[int]], dst: int, src: int, k: int) -> None:
        if k == 0:
            return
        for r in range(len(M)):
            M[r][dst] += k * M[r][src]

    def row_neg(M: List[List[int]], i: int) -> None:
        M[i] = [-x for x in M[i]]

    def absmin_pos(sub_i: int, sub_j: int) -> Tuple[int, int]:
        best = None
        pi, pj = -1, -1
        for r in range(sub_i, m):
            for c in range(sub_j, n):
                if A[r][c] != 0:
                    v = abs(A[r][c])
                    if best is None or v < best:
                        best = v
                        pi, pj = r, c
        return pi, pj

    U = eye(m)
    V = eye(n)

    i = j = 0
    while i < m and j < n:
        pi, pj = absmin_pos(i, j)
        if pi == -1:
            break
        if pi != i:
            swap_rows(A, i, pi)
            swap_rows(U, i, pi)
        if pj != j:
            swap_cols(A, j, pj)
            swap_cols(V, j, pj)

        changed = True
        guard = 0
        while changed:
            guard += 1
            if guard > 2000:
                raise RuntimeError("SNF reduction did not converge (guard exceeded)")
            changed = False

            for r in range(m):
                if r == i:
                    continue
                while A[r][j] != 0:
                    a = A[i][j]
                    b = A[r][j]
                    if b == 0:
                        break
                    q = a // b
                    row_add(A, i, r, -q)
                    row_add(U, i, r, -q)
                    if abs(A[i][j]) > abs(A[r][j]):
                        swap_rows(A, i, r)
                        swap_rows(U, i, r)
                    changed = True

            for c in range(n):
                if c == j:
                    continue
                while A[i][c] != 0:
                    a = A[i][j]
                    b = A[i][c]
                    if b == 0:
                        break
                    q = a // b
                    col_add(A, j, c, -q)
                    col_add(V, j, c, -q)
                    if abs(A[i][j]) > abs(A[i][c]):
                        swap_cols(A, j, c)
                        swap_cols(V, j, c)
                    changed = True

        if A[i][j] < 0:
            row_neg(A, i)
            row_neg(U, i)

        piv = A[i][j]
        if piv != 0:
            for r in range(m):
                if r != i and A[r][j] != 0:
                    q = A[r][j] // piv
                    row_add(A, r, i, -q)
                    row_add(U, r, i, -q)
            for c in range(n):
                if c != j and A[i][c] != 0:
                    q = A[i][c] // piv
                    col_add(A, c, j, -q)
                    col_add(V, c, j, -q)

        i += 1
        j += 1

    r = min(m, n)
    for k in range(r):
        if A[k][k] < 0:
            row_neg(A, k)
            row_neg(U, k)

    for k in range(r - 1):
        if A[k][k] == 0:
            continue
        for l in range(k + 1, r):
            if A[l][l] == 0:
                continue
            a = A[k][k]
            b = A[l][l]
            g = math.gcd(a, b)
            if g == 0:
                continue
            if b % a == 0:
                continue
            _, x, y = extended_gcd(a, b)
            t11, t12 = x, y
            t21, t22 = -b // g, a // g

            rk = A[k][:]
            rl = A[l][:]
            A[k] = [t11 * rk[c] + t12 * rl[c] for c in range(n)]
            A[l] = [t21 * rk[c] + t22 * rl[c] for c in range(n)]
            uk = U[k][:]
            ul = U[l][:]
            U[k] = [t11 * uk[c] + t12 * ul[c] for c in range(m)]
            U[l] = [t21 * uk[c] + t22 * ul[c] for c in range(m)]

            for rr in range(m):
                ck = A[rr][k]
                cl = A[rr][l]
                A[rr][k] = t11 * ck + t12 * cl
                A[rr][l] = t21 * ck + t22 * cl
            for rr in range(n):
                vk = V[k][rr]
                vl = V[l][rr]
                V[k][rr] = t11 * vk + t12 * vl
                V[l][rr] = t21 * vk + t22 * vl

            if A[l][k] != 0 and A[k][k] != 0:
                q = A[l][k] // A[k][k]
                row_add(A, l, k, -q)
                row_add(U, l, k, -q)
            if A[k][l] != 0 and A[k][k] != 0:
                q = A[k][l] // A[k][k]
                col_add(A, l, k, -q)
                col_add(V, l, k, -q)
            if A[k][k] < 0:
                row_neg(A, k)
                row_neg(U, k)

    return A, U, V


def smith_normal_form(mat_int: List[List[int]]) -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
    if _HAVE_SYMPY_SNF:
        M = _sp.Matrix(mat_int)  # type: ignore[union-attr]
        D_sym, U_sym, V_sym = _smith_normal_decomp(M, domain=_sp.ZZ)  # type: ignore[misc,union-attr]
        D = [[int(D_sym[i, j]) for j in range(D_sym.cols)] for i in range(D_sym.rows)]
        U = [[int(U_sym[i, j]) for j in range(U_sym.cols)] for i in range(U_sym.rows)]
        V = [[int(V_sym[i, j]) for j in range(V_sym.cols)] for i in range(V_sym.rows)]
        return D, U, V
    return smith_normal_form_fallback(mat_int)


def lcm_for_fractions(values: Iterable[Fraction]) -> int:
    lcm = 1
    for v in values:
        lcm = abs(math.lcm(lcm, v.denominator))
    return lcm


def rref(mat: Mat) -> Mat:
    """Reduced row echelon form (fraction arithmetic)."""
    key = tuple(tuple(row) for row in mat)
    cached = _rref_cache.get(key)
    if cached is not None:
        return [row[:] for row in cached]
    A = [row[:] for row in mat]
    m = len(A)
    n = len(A[0]) if m else 0
    r = 0
    for c in range(n):
        pivot = None
        for i in range(r, m):
            if A[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        A[r], A[pivot] = A[pivot], A[r]
        pv = A[r][c]
        A[r] = [v / pv for v in A[r]]
        for i in range(m):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [A[i][j] - f * A[r][j] for j in range(n)]
        r += 1
        if r == m:
            break
    A = [row for row in A if any(row)]
    _rref_cache[key] = tuple(tuple(row) for row in A)
    return A


_rref_cache: Dict[Tuple[Tuple[Fraction, ...], ...], Tuple[Tuple[Fraction, ...], ...]] = {}


def nullspace(mat: Mat) -> Mat:
    """Nullspace basis of mat (rows)."""
    if not mat:
        return [
            [Fraction(1), Fraction(0), Fraction(0)],
            [Fraction(0), Fraction(1), Fraction(0)],
            [Fraction(0), Fraction(0), Fraction(1)],
        ]
    key = tuple(tuple(row) for row in mat)
    cached = _nullspace_cache.get(key)
    if cached is not None:
        return [list(row) for row in cached]
    A = rref(mat)
    m = len(A)
    n = len(A[0]) if m else 3
    pivot_cols = []
    for row in A:
        for j, v in enumerate(row):
            if v != 0:
                pivot_cols.append(j)
                break
    free = [c for c in range(n) if c not in pivot_cols]
    basis = []
    for f in free:
        vec = [Fraction(0) for _ in range(n)]
        vec[f] = Fraction(1)
        for i, pc in enumerate(pivot_cols):
            vec[pc] = -A[i][f]
        basis.append(vec)
    _nullspace_cache[key] = tuple(tuple(row) for row in basis)
    return basis


_nullspace_cache: Dict[Tuple[Tuple[Fraction, ...], ...], Tuple[Tuple[Fraction, ...], ...]] = {}


def solve_affine(A: Mat, b: List[Fraction]) -> Tuple[Vec, Mat]:
    """Solve A x = b (A rows), returning one particular x0 and a nullspace basis."""
    if not A:
        return [Fraction(0), Fraction(0), Fraction(0)], identity_mat()
    Aaug = [row + [b[i]] for i, row in enumerate(A)]
    m = len(Aaug)
    n = len(Aaug[0]) - 1
    r = 0
    pivots = []
    for c in range(n):
        pivot = None
        for i in range(r, m):
            if Aaug[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        Aaug[r], Aaug[pivot] = Aaug[pivot], Aaug[r]
        pv = Aaug[r][c]
        Aaug[r] = [v / pv for v in Aaug[r]]
        for i in range(m):
            if i != r and Aaug[i][c] != 0:
                f = Aaug[i][c]
                Aaug[i] = [Aaug[i][j] - f * Aaug[r][j] for j in range(n + 1)]
        pivots.append(c)
        r += 1
        if r == m:
            break
    free = [c for c in range(n) if c not in pivots]
    x0 = [Fraction(0) for _ in range(n)]
    for i, p in enumerate(pivots):
        x0[p] = Aaug[i][-1]
    basis = []
    for f in free:
        vec = [Fraction(0) for _ in range(n)]
        vec[f] = Fraction(1)
        for i, p in enumerate(pivots):
            vec[p] = -Aaug[i][f]
        basis.append(vec)
    return x0, basis


def normalize_basis(basis: Mat) -> Mat:
    if not basis:
        return []
    return rref(basis)


def point_on_subspace(x0: Vec, basis: Mat, target: Vec) -> Vec:
    """Return a representative on the affine subspace closest to the sampled target."""
    if not basis:
        return mod1_vec(x0)
    dim = len(basis)
    # Build 3 x dim matrix with basis vectors as columns
    M = [[basis[col][row] for col in range(dim)] for row in range(3)]
    diff = [target[i] - x0[i] for i in range(3)]
    coeffs, _ = solve_affine(M, diff)
    rep = [
        x0[i] + sum(coeffs[j] * basis[j][i] for j in range(dim))
        for i in range(3)
    ]
    return mod1_vec(rep)


# --- global caches for SNF + congruence solving ------------------------------

@lru_cache(maxsize=200000)
def _smith_cached(A_key: Tuple[Tuple[int, ...], ...]) -> Tuple[
    Tuple[Tuple[int, ...], ...],
    Tuple[Tuple[int, ...], ...],
    Tuple[Tuple[int, ...], ...],
]:
    mat = [list(row) for row in A_key]
    if _HAVE_SYMPY_SNF:
        M = _sp.Matrix(mat)  # type: ignore[union-attr]
        D_sym, U_sym, V_sym = _smith_normal_decomp(M, domain=_sp.ZZ)  # type: ignore[misc,union-attr]
        D = tuple(tuple(int(D_sym[i, j]) for j in range(D_sym.cols)) for i in range(D_sym.rows))
        U = tuple(tuple(int(U_sym[i, j]) for j in range(U_sym.cols)) for i in range(U_sym.rows))
        V = tuple(tuple(int(V_sym[i, j]) for j in range(V_sym.cols)) for i in range(V_sym.rows))
        return D, U, V

    D_list, U_list, V_list = smith_normal_form_fallback(mat)
    D = tuple(tuple(int(x) for x in row) for row in D_list)
    U = tuple(tuple(int(x) for x in row) for row in U_list)
    V = tuple(tuple(int(x) for x in row) for row in V_list)
    return D, U, V


def _mult_mat_vec_int_frac(M: Tuple[Tuple[int, ...], ...], vec: List[Fraction]) -> List[Fraction]:
    out: List[Fraction] = []
    for r in range(len(M)):
        s = Fraction(0)
        row = M[r]
        for c in range(len(vec)):
            if row[c] != 0:
                s += Fraction(row[c]) * vec[c]
        out.append(s)
    return out


def _normalize_basis_tuple(basis: List[List[Fraction]]) -> Tuple[Tuple[Fraction, ...], ...]:
    nb = normalize_basis(basis)
    return tuple(tuple(v for v in row) for row in nb)


@lru_cache(maxsize=400000)
def _solve_congruence_int_cached(
    mod_val: int,
    A_key: Tuple[Tuple[int, ...], ...],
    b_key: Tuple[int, ...],
) -> Tuple[
    Tuple[Tuple[Fraction, ...], Tuple[Tuple[Fraction, ...], ...]],
    ...
]:
    if not A_key:
        x0 = (Fraction(0), Fraction(0), Fraction(0))
        basis = (
            (Fraction(1), Fraction(0), Fraction(0)),
            (Fraction(0), Fraction(1), Fraction(0)),
            (Fraction(0), Fraction(0), Fraction(1)),
        )
        return ((x0, basis),)

    D, U, V = _smith_cached(A_key)
    m = len(D)
    n = len(D[0]) if m else 0

    b_hat = [0] * m
    for i in range(m):
        s = 0
        for k in range(m):
            if U[i][k] != 0:
                s += U[i][k] * b_key[k]
        b_hat[i] = s

    rank = 0
    for i in range(min(m, n)):
        if D[i][i] != 0:
            rank += 1
        else:
            break

    for i in range(rank, m):
        if b_hat[i] % mod_val != 0:
            return tuple()

    residue_choices_per_coord: List[List[Fraction]] = [[] for _ in range(rank)]
    for i in range(rank):
        d_val = D[i][i]
        if d_val == 0:
            if b_hat[i] != 0:
                return tuple()
            residue_choices_per_coord[i] = [Fraction(0)]
            continue
        base = Fraction(b_hat[i], d_val)
        step = Fraction(mod_val, abs(d_val))
        residue_choices_per_coord[i] = [base + k * step for k in range(abs(d_val))]

    residue_lists: List[List[Fraction]] = [[]]
    for i in range(rank):
        new_lists: List[List[Fraction]] = []
        for cur in residue_lists:
            for val in residue_choices_per_coord[i]:
                new_lists.append(cur + [val])
        residue_lists = new_lists
    if not residue_lists:
        residue_lists = [[Fraction(0) for _ in range(rank)]]

    sols: List[Tuple[Tuple[Fraction, ...], Tuple[Tuple[Fraction, ...], ...]]] = []

    for residues in residue_lists:
        y0 = [Fraction(0) for _ in range(n)]
        for i in range(rank):
            y0[i] = residues[i]

        x0_int = _mult_mat_vec_int_frac(V, y0)
        x0 = tuple(mod1(v / mod_val) for v in x0_int)

        basis_rows: List[List[Fraction]] = []
        for j in range(rank, n):
            step_vec = [Fraction(0) for _ in range(n)]
            step_vec[j] = Fraction(1)
            vec_int = _mult_mat_vec_int_frac(V, step_vec)
            basis_rows.append([v / mod_val for v in vec_int])

        basis_t = _normalize_basis_tuple(basis_rows)

        x0_list = [x0[0], x0[1], x0[2]]
        basis_list = [list(row) for row in basis_t]
        x0_list = point_on_subspace(x0_list, basis_list, x0_list)
        x0 = (x0_list[0], x0_list[1], x0_list[2])
        sols.append((x0, basis_t))

    return tuple(sols)


def solve_congruence(A: Mat, b: List[Fraction]) -> List[Tuple[Vec, Mat]]:
    """
    Solve A x ≡ b (mod 1) for x in Q^3.
    Returns a list of affine solution subspaces (x0, basis); empty if inconsistent.
    Uses Smith normal form on an integer lift of the congruence.
    """
    if not A:
        return [([Fraction(0), Fraction(0), Fraction(0)], identity_mat())]
    cols = 3
    all_fracs = [v for row in A for v in row] + b
    L = lcm_for_fractions(all_fracs)
    if L == 0:
        L = 1
    mod_val = L
    A_int = [[int(v * mod_val) for v in row] for row in A]
    b_int = [int(v * mod_val) for v in b]

    @lru_cache(maxsize=None)
    def solve_cached(key: Tuple[int, Tuple[Tuple[int, ...], ...]]) -> Tuple[List[List[int]], List[List[int]], List[List[int]]]:
        _, A_key = key
        mat = [list(row) for row in A_key]
        D, U, V = smith_normal_form(mat)
        return D, U, V

    cache_key = (mod_val, tuple(tuple(row) for row in A_int))
    D, U, V = solve_cached(cache_key)
    m = len(D)
    n = len(D[0]) if m else 0
    b_hat = [sum(U[i][k] * b_int[k] for k in range(m)) for i in range(m)]

    rank = 0
    diag = []
    for i in range(min(m, n)):
        if D[i][i] != 0:
            rank += 1
            diag.append(D[i][i])
        else:
            break

    @lru_cache(maxsize=None)
    def solve_core(
        D_key: Tuple[Tuple[int, ...], ...],
        U_key: Tuple[Tuple[int, ...], ...],
        V_key: Tuple[Tuple[int, ...], ...],
        b_key: Tuple[int, ...],
        mod_val_local: int,
    ) -> Tuple[Tuple[Tuple[Fraction, ...], Tuple[Tuple[Fraction, ...], ...]], ...]:
        D_local = [list(row) for row in D_key]
        V_local = [list(row) for row in V_key]
        m_local = len(D_local)
        n_local = len(D_local[0]) if m_local else 0

        b_hat_local = list(b_key)
        residue_choices_per_coord: List[List[Fraction]] = [[] for _ in range(rank)]
        for i in range(rank):
            d_val = D_local[i][i]
            if d_val == 0:
                if b_hat_local[i] != 0:
                    return tuple()
                residue_choices_per_coord[i] = [Fraction(0)]
                continue
            base = Fraction(b_hat_local[i], d_val)
            step = Fraction(mod_val_local, abs(d_val))
            residue_choices_per_coord[i] = [base + k * step for k in range(abs(d_val))]

        for i in range(rank, m_local):
            if b_hat_local[i] % mod_val_local != 0:
                return tuple()

        def mult_mat_vec(M: List[List[int]], vec: List[Fraction]) -> List[Fraction]:
            return [sum(Fraction(M[r][c]) * vec[c] for c in range(len(vec))) for r in range(len(M))]

        residue_lists: List[List[Fraction]] = [[]]
        for i in range(rank):
            choices = residue_choices_per_coord[i]
            new_lists: List[List[Fraction]] = []
            for base_list in residue_lists:
                for val in choices:
                    new_lists.append(base_list + [val])
            residue_lists = new_lists
        if not residue_lists:
            residue_lists = [[Fraction(0) for _ in range(rank)]]

        sol_tuples: List[Tuple[Tuple[Fraction, ...], Tuple[Tuple[Fraction, ...], ...]]] = []
        for residues in residue_lists:
            y0 = [Fraction(0) for _ in range(n_local)]
            for idx in range(rank):
                y0[idx] = residues[idx]
            x0_int = mult_mat_vec(V_local, y0)
            x0 = [mod1(v) for v in x0_int]

            basis: Mat = []
            for j in range(rank, n_local):
                step_vec = [Fraction(0) for _ in range(n_local)]
                step_vec[j] = Fraction(1, 1)
                vec_int = mult_mat_vec(V_local, step_vec)
                basis.append(vec_int)
            basis = normalize_basis(basis)
            x0 = point_on_subspace(x0, basis, x0)
            sol_tuples.append((tuple(x0), tuple(tuple(v for v in row) for row in basis)))

        return tuple(sol_tuples)

    solutions_raw = solve_core(
        tuple(tuple(row) for row in D),
        tuple(tuple(row) for row in U),
        tuple(tuple(row) for row in V),
        tuple(b_hat),
        mod_val,
    )
    solutions: List[Tuple[Vec, Mat]] = []
    for x0_t, basis_t in solutions_raw:
        x0 = [Fraction(v) for v in x0_t]
        basis = [[Fraction(v) for v in row] for row in basis_t]
        solutions.append((x0, basis))
    return solutions


# --- quick rank prune for intersections --------------------------------------

def rank_rref(A: Mat) -> int:
    return len(rref([row[:] for row in A]))


def will_reduce_dim(A_cur_rref: Mat, A_extra: Mat) -> bool:
    """
    If rank(A_cur + A_extra) == rank(A_cur), adding constraints can't reduce subspace dimension.
    Since we only push intersections when dim drops, we can skip expensive solve_congruence.
    """
    if not A_extra:
        return False
    r0 = len(A_cur_rref)
    r1 = rank_rref(A_cur_rref + A_extra)
    return r1 > r0


# --- group utilities ---------------------------------------------------------

@dataclass(frozen=True)
class Op:
    W: Tuple[Tuple[Fraction, Fraction, Fraction], ...]
    t: Tuple[Fraction, Fraction, Fraction]

    def apply(self, r: Sequence[Fraction]) -> List[Fraction]:
        return [
            sum(self.W[i][k] * r[k] for k in range(3)) + self.t[i]
            for i in range(3)
        ]


@dataclass(frozen=True)
class SpinOp:
    W: Tuple[Tuple[Fraction, Fraction, Fraction], ...]
    t: Tuple[Fraction, Fraction, Fraction]
    tr: bool
    spin: Tuple[Tuple[float, float, float], ...]

    def apply(self, r: Sequence[Fraction]) -> List[Fraction]:
        return [
            sum(self.W[i][k] * r[k] for k in range(3)) + self.t[i]
            for i in range(3)
        ]


def op_from_json(op: dict) -> Op:
    W = tuple(tuple(frac(x) for x in row) for row in op["matrix"])
    t = tuple(frac(x) for x in op.get("translation", [0, 0, 0]))
    return Op(W=W, t=t)


def op_key(op: Op) -> Tuple[Tuple[Fraction, ...], Tuple[Fraction, ...]]:
    return (tuple(x for row in op.W for x in row), tuple(mod1(v) for v in op.t))


def rotation_key(op: Op) -> Tuple[Fraction, ...]:
    return tuple(x for row in op.W for x in row)


def dedup_ops(ops: Iterable[Op]) -> List[Op]:
    seen = set()
    unique: List[Op] = []
    for op in ops:
        key = op_key(op)
        if key in seen:
            continue
        seen.add(key)
        unique.append(op)
    return unique


def expand_with_centering(base_ops: List[Op], centering_vectors: List[Tuple[Fraction, Fraction, Fraction]]) -> List[Op]:
    expanded: List[Op] = []
    for op in base_ops:
        for c in centering_vectors:
            t_new = tuple(mod1(op.t[i] + c[i]) for i in range(3))
            expanded.append(Op(op.W, t_new))
    return dedup_ops(expanded)


def apply_op_basis(op: Op, basis: Mat) -> Mat:
    out = []
    for v in basis:
        out.append([sum(op.W[i][k] * v[k] for k in range(3)) for i in range(3)])
    return out


def to_reciprocal_op(op: Op) -> Op:
    """Convert a real-space Seitz operation (W|t) to reciprocal space (W*|t*)."""
    W_inv_T = mat_transpose(mat_inv([[Fraction(x) for x in row] for row in op.W]))
    W_rec = tuple(tuple(Fraction(val) for val in row) for row in W_inv_T)
    t_rec = (Fraction(0), Fraction(0), Fraction(0))
    return Op(W=W_rec, t=t_rec)


def time_reversal_op() -> Op:
    minus = Fraction(-1)
    W = (
        (minus, Fraction(0), Fraction(0)),
        (Fraction(0), minus, Fraction(0)),
        (Fraction(0), Fraction(0), minus),
    )
    return Op(W=W, t=(Fraction(0), Fraction(0), Fraction(0)))


def primitive_matrix_from_centering(symbol: str) -> Mat:
    s = (symbol or "").upper()
    half = Fraction(1, 2)

    if s == "P" or s == "":
        return identity_mat()
    if s == "I":
        return [
            [-half,  half,  half],
            [ half, -half,  half],
            [ half,  half, -half],
        ]
    if s == "F":
        return [
            [0,    half, half],
            [half, 0,    half],
            [half, half, 0   ],
        ]
    if s == "C":
        return [
            [ half, -half, 0],
            [ half,  half, 0],
            [ 0,     0,    1],
        ]
    if s == "A":
        return [
            [1, 0,    0   ],
            [0, half, -half],
            [0, half,  half],
        ]
    if s == "B":
        return [
            [ half, 0, -half],
            [ 0,    1,  0   ],
            [ half, 0,  half],
        ]
    if s == "R":
        return [
            [Fraction(2, 3), Fraction(-1, 3), Fraction(-1, 3)],
            [Fraction(1, 3), Fraction( 1, 3), Fraction(-2, 3)],
            [Fraction(1, 3), Fraction( 1, 3), Fraction( 1, 3)],
        ]
    return identity_mat()


# def change_basis_ops(ops: List[Op], P: Mat, P_inv: Mat) -> List[Op]:
#     out: List[Op] = []
#     for op in ops:
#         W_new = mat_mul(mat_mul(P_inv, [[Fraction(x) for x in row] for row in op.W]), P)
#         t_new = mat_vec_mul(P_inv, op.t)
#         out.append(Op(tuple(tuple(w for w in row) for row in W_new), tuple(t_new)))
#     return out

def change_basis_ops(ops: List[Op]) -> List[Op]:
    out: List[Op] = []
    for op in ops:
        W_new = mat_inv(mat_transpose(op.W))
        t_new = _sp.zeros(1,3)
        out.append(Op(tuple(tuple(w for w in row) for row in W_new), tuple(t_new)))
    return out


def shift_op(op: Op, shift: Tuple[Fraction, Fraction, Fraction]) -> Op:
    t_new = []
    for i in range(3):
        t_new.append(
            mod1(op.t[i] + shift[i] - sum(op.W[i][k] * shift[k] for k in range(3)))
        )
    return Op(op.W, tuple(t_new))


def compose(op1: Op, op2: Op) -> Op:
    W = tuple(
        tuple(sum(op1.W[i][k] * op2.W[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )
    t = tuple(
        mod1(sum(op1.W[i][k] * op2.t[k] for k in range(3)) + op1.t[i])
        for i in range(3)
    )
    return Op(W=W, t=t)


def build_multiplication_table(ops: List[Op]) -> Tuple[List[List[int]], int, List[int]]:
    n = len(ops)
    key_to_idx = {op_key(op): idx for idx, op in enumerate(ops)}

    identity_probe_idx = next((i for i, op in enumerate(ops) if is_identity_op(op)), -1)
    if identity_probe_idx == -1:
        raise ValueError("No identity operation found in the group.")
    identity_idx = key_to_idx[op_key(ops[identity_probe_idx])]

    mult: List[List[int]] = [[-1] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            prod = compose(ops[i], ops[j])
            idx = key_to_idx.get(op_key(prod))
            if idx is None:
                raise ValueError("Group not closed under composition; missing element.")
            mult[i][j] = idx

    inverses: List[int] = [-1] * n
    for i in range(n):
        inv_idx = next(
            (j for j in range(n) if mult[i][j] == identity_idx and mult[j][i] == identity_idx),
            -1,
        )
        if inv_idx == -1:
            raise ValueError(f"No inverse found for operation index {i}.")
        inverses[i] = inv_idx

    return mult, identity_idx, inverses


def subgroup_closure(
    generators: Iterable[int],
    mult_table: List[List[int]],
    identity_idx: int,
) -> FrozenSet[int]:
    closure: set = set(generators)
    closure.add(identity_idx)
    changed = True
    while changed:
        changed = False
        elems = list(closure)
        for a in elems:
            for b in elems:
                prod = mult_table[a][b]
                if prod not in closure:
                    closure.add(prod)
                    changed = True
    return frozenset(closure)


def enumerate_all_subgroups(
    mult_table: List[List[int]], identity_idx: int
) -> List[FrozenSet[int]]:
    n = len(mult_table)
    all_indices = list(range(n))
    seen: set = set()
    queue: List[FrozenSet[int]] = [frozenset([identity_idx])]
    subgroups: List[FrozenSet[int]] = []

    while queue:
        subgroup = queue.pop()
        if subgroup in seen:
            continue
        seen.add(subgroup)
        subgroups.append(subgroup)
        for g in all_indices:
            if g in subgroup:
                continue
            new_subgroup = subgroup_closure(subgroup | {g}, mult_table, identity_idx)
            if new_subgroup not in seen:
                queue.append(new_subgroup)
    return subgroups


def conjugate_subgroup(
    subgroup: FrozenSet[int],
    g_idx: int,
    mult_table: List[List[int]],
    inverses: List[int],
) -> FrozenSet[int]:
    g_inv = inverses[g_idx]
    return frozenset(mult_table[mult_table[g_idx][h]][g_inv] for h in subgroup)


def subgroup_conjugacy_reps(
    subgroups: List[FrozenSet[int]],
    mult_table: List[List[int]],
    inverses: List[int],
) -> List[FrozenSet[int]]:
    remaining = set(subgroups)
    reps: List[FrozenSet[int]] = []
    n = len(mult_table)
    while remaining:
        subgroup = remaining.pop()
        conj_class: set = set()
        for g in range(n):
            conj_class.add(conjugate_subgroup(subgroup, g, mult_table, inverses))
        rep = min(conj_class, key=lambda s: tuple(sorted(s)))
        reps.append(rep)
        remaining -= conj_class
    return reps


def rotation_subgroup_reps_from_point_group(rotations: List[Mat]) -> List[FrozenSet[int]]:
    rot_ops = [Op(tuple(tuple(v for v in row) for row in rot), (Fraction(0), Fraction(0), Fraction(0))) for rot in rotations]
    mult_table, identity_idx, inverses = build_multiplication_table(rot_ops)
    all_subgroups = enumerate_all_subgroups(mult_table, identity_idx)
    return subgroup_conjugacy_reps(all_subgroups, mult_table, inverses)


def compose_translation(
    rot: Mat,
    t1: Tuple[Fraction, Fraction, Fraction],
    t2: Tuple[Fraction, Fraction, Fraction],
) -> Tuple[Fraction, Fraction, Fraction]:
    return tuple(
        mod1(sum(rot[i][k] * t2[k] for k in range(3)) + t1[i])
        for i in range(3)
    )


def solve_translations_for_rotation_subgroup(
    rot_subgroup: FrozenSet[int],
    rotations: List[Mat],
    rot_mult_table: List[List[int]],
    rot_translation_options: Dict[int, List[Tuple[Fraction, Fraction, Fraction]]],
    identity_rot_idx: Optional[int],
    solution_limit: Optional[int] = None,
    combo_limit: Optional[int] = None,
) -> List[Dict[int, Tuple[Fraction, Fraction, Fraction]]]:
    idx_list = sorted(rot_subgroup)
    domains: Dict[int, List[Tuple[Fraction, Fraction, Fraction]]] = {}
    for ridx in idx_list:
        opts = rot_translation_options.get(ridx, [])
        if ridx == identity_rot_idx:
            opts = [(Fraction(0), Fraction(0), Fraction(0))]
        if not opts:
            return []
        domains[ridx] = list(opts)

    total = 1
    for opts in domains.values():
        total *= len(opts)
    if combo_limit is not None and total > combo_limit:
        for ridx in list(domains):
            opts = sorted(domains[ridx], key=dedup_coord_score)
            domains[ridx] = opts[:2]
        total = 1
        for opts in domains.values():
            total *= len(opts)
        if total > combo_limit:
            for ridx in list(domains):
                domains[ridx] = domains[ridx][:1]
            total = 1
            for opts in domains.values():
                total *= len(opts)

    var_index = {ridx: i for i, ridx in enumerate(idx_list)}
    var_count = len(idx_list)
    A_base: Mat = []
    c_base: List[Fraction] = []
    zero = Fraction(0)
    if var_count <= 10:
        for a in idx_list:
            for b in idx_list:
                if not (
                    (identity_rot_idx is not None and (a == identity_rot_idx or b == identity_rot_idx))
                    or a == b
                ):
                    continue
                prod = rot_mult_table[a][b]
                if prod not in var_index:
                    continue
                pa = var_index[a]
                pb = var_index[b]
                pp = var_index[prod]
                rot_a = rotations[a]
                for k in range(3):
                    row = [zero] * (3 * var_count)
                    row[3 * pp + k] = Fraction(1)
                    row[3 * pa + k] -= Fraction(1)
                    for j in range(3):
                        row[3 * pb + j] -= rot_a[k][j]
                    A_base.append(row)
                    c_base.append(Fraction(0))

    if A_base:
        base_solutions = solve_congruence(A_base, c_base)
        if not base_solutions:
            return []

    if combo_limit is not None and A_base and total > combo_limit * 5:
        for ridx in list(domains.keys()):
            filtered: List[Tuple[Fraction, Fraction, Fraction]] = []
            for opt in domains[ridx]:
                A_eq = list(A_base)
                c_eq = list(c_base)
                offset = 3 * var_index[ridx]
                for k in range(3):
                    row = [zero] * (3 * var_count)
                    row[offset + k] = Fraction(1)
                    A_eq.append(row)
                    c_eq.append(opt[k])
                if solve_congruence(A_eq, c_eq):
                    filtered.append(opt)
            if not filtered:
                return []
            domains[ridx] = filtered
        total = 1
        for opts in domains.values():
            total *= len(opts)
        if total > combo_limit:
            for ridx in list(domains):
                domains[ridx] = [min(domains[ridx], key=dedup_coord_score)]

    def arc_prune(doms: Dict[int, List[Tuple[Fraction, Fraction, Fraction]]]) -> bool:
        changed = True
        while changed:
            changed = False
            for a in idx_list:
                for b in idx_list:
                    prod = rot_mult_table[a][b]
                    da = doms[a]
                    db = doms[b]
                    if combo_limit is not None and len(da) * len(db) > combo_limit:
                        continue
                    allowed_prod: set = set()
                    for ta in da:
                        for tb in db:
                            allowed_prod.add(compose_translation(rotations[a], ta, tb))
                    new_prod = [t for t in doms[prod] if t in allowed_prod]
                    if not new_prod:
                        return False
                    if len(new_prod) < len(doms[prod]):
                        doms[prod] = new_prod
                        changed = True
        return True

    if not arc_prune(domains):
        return []

    solutions: List[Dict[int, Tuple[Fraction, Fraction, Fraction]]] = []
    assignments: Dict[int, Tuple[Fraction, Fraction, Fraction]] = {}

    def forward_check(
        new_ridx: int,
        new_t: Tuple[Fraction, Fraction, Fraction],
        doms: Dict[int, List[Tuple[Fraction, Fraction, Fraction]]],
    ) -> bool:
        for ridx2, t2 in assignments.items():
            for a, ta, b, tb in (
                (new_ridx, new_t, ridx2, t2),
                (ridx2, t2, new_ridx, new_t),
            ):
                prod = rot_mult_table[a][b]
                t_prod = compose_translation(rotations[a], ta, tb)
                if prod not in doms:
                    continue
                if t_prod not in doms[prod]:
                    return False
                if prod in assignments:
                    if assignments[prod] != t_prod:
                        return False
                elif len(doms[prod]) > 1:
                    doms[prod] = [t_prod]
        return True

    def backtrack() -> None:
        if len(assignments) == len(domains):
            solutions.append(dict(assignments))
            return
        if solution_limit is not None and len(solutions) >= solution_limit:
            return
        ridx = min((r for r in domains if r not in assignments), key=lambda r: len(domains[r]))
        current_domain = domains[ridx][:]
        for t in current_domain:
            assignments[ridx] = t
            saved_domains = {k: v[:] for k, v in domains.items()}
            domains[ridx] = [t]
            ok = forward_check(ridx, t, domains)
            if ok:
                backtrack()
            if solution_limit is not None and len(solutions) >= solution_limit:
                return
            domains.clear()
            domains.update(saved_domains)
            assignments.pop(ridx, None)

    backtrack()
    return solutions


def subgroup_from_translation_choice(
    translation_choice: Dict[int, Tuple[Fraction, Fraction, Fraction]],
    rot_trans_to_op_idx: Dict[Tuple[int, Tuple[Fraction, Fraction, Fraction]], int],
    op_mult_table: List[List[int]],
    op_rot_idx: List[int],
    op_trans: List[Tuple[Fraction, Fraction, Fraction]],
    identity_op_idx: int,
) -> Optional[FrozenSet[int]]:
    seeds: List[int] = [identity_op_idx]
    for ridx, t in translation_choice.items():
        idx = rot_trans_to_op_idx.get((ridx, t))
        if idx is None:
            return None
        seeds.append(idx)

    subgroup = set(seeds)
    stack = list(seeds)
    while stack:
        a = stack.pop()
        for b in list(subgroup):
            for prod_idx in (op_mult_table[a][b], op_mult_table[b][a]):
                ridx = op_rot_idx[prod_idx]
                t = op_trans[prod_idx]
                if translation_choice.get(ridx) != t:
                    return None
                if prod_idx not in subgroup:
                    subgroup.add(prod_idx)
                    stack.append(prod_idx)
    return frozenset(subgroup)


def fixed_subspaces_for_subgroup(
    subgroup: FrozenSet[int],
    ops: List[Op],
) -> List[Tuple[Vec, Mat]]:
    A_all: Mat = []
    c_all: List[Fraction] = []
    for idx in subgroup:
        A, c = op_fix_constraints(ops[idx])
        A_all += A
        c_all += c
    if not A_all:
        return [([Fraction(0), Fraction(0), Fraction(0)], identity_mat())]
    return solve_congruence(A_all, c_all)


def is_identity_op(op: Op) -> bool:
    return all(op.W[i][j] == (1 if i == j else 0) for i in range(3) for j in range(3)) and all(
        mod1(op.t[i]) == 0 for i in range(3)
    )


def unique_rotations(ops: List[Op]) -> List[Mat]:
    seen = set()
    R_list: List[Mat] = []
    for op in ops:
        key = tuple(x for row in op.W for x in row)
        if key in seen:
            continue
        seen.add(key)
        R_list.append([[Fraction(x) for x in row] for row in op.W])
    return R_list


# --- wyckoff / subspace machinery -------------------------------------------

def equal_mod1(a: Sequence[Fraction], b: Sequence[Fraction]) -> bool:
    return all((a[i] - b[i]) % 1 == 0 for i in range(3))


def stabilizer(pt: Vec, ops: List[Op]) -> List[int]:
    return [
        idx for idx, op in enumerate(ops)
        if equal_mod1(op.apply(pt), pt)
    ]


def canonical_subspace_key(x0: Vec, basis: Mat) -> Tuple[Tuple[Tuple[Fraction, ...], ...], Tuple[Fraction, ...]]:
    ns = nullspace(basis)
    ns_r = rref(ns)
    c_vals = tuple(mod1(sum(n[i] * x0[i] for i in range(3))) for n in ns_r)
    return (tuple(tuple(row) for row in ns_r), c_vals)


def constraints_from_subspace(x0: Vec, basis: Mat) -> Tuple[Mat, List[Fraction]]:
    A = nullspace(basis)
    A_r = rref(A)
    c = [mod1(sum(row[i] * x0[i] for i in range(3))) for row in A_r]
    return A_r, c


def subspace_orbit_key(x0: Vec, basis: Mat, ops: List[Op]) -> Tuple[Tuple[Tuple[Fraction, ...], ...], Tuple[Fraction, ...]]:
    keys = []
    for op in ops:
        x1 = mod1_vec(op.apply(x0))
        b1 = apply_op_basis(op, basis)
        keys.append(canonical_subspace_key(x1, b1))
    return min(keys)


def canonicalize_axis_aligned_basis(basis: Mat) -> Mat:
    if not basis:
        return []
    if any(len(vec) != 3 for vec in basis):
        return basis

    axis_for_vec: List[int] = []
    for vec in basis:
        nonzero = [i for i, v in enumerate(vec) if v != 0]
        if len(nonzero) != 1:
            return basis
        axis_idx = nonzero[0]
        if abs(vec[axis_idx]) != 1:
            return basis
        axis_for_vec.append(axis_idx)

    if len(set(axis_for_vec)) != len(axis_for_vec):
        return basis

    ordered: Mat = []
    for axis in range(3):
        if len(ordered) == len(basis):
            break
        if axis in axis_for_vec:
            vec = list(basis[axis_for_vec.index(axis)])
            if vec[axis] < 0:
                vec = [-v for v in vec]
            ordered.append(vec)
    return ordered if len(ordered) == len(basis) else basis


def primitive_int_vec(vec: Sequence[Fraction]) -> Tuple[int, int, int]:
    vals = [Fraction(v) for v in vec]
    lcm = 1
    for v in vals:
        lcm = abs(math.lcm(lcm, v.denominator))
    ints = [int(v * lcm) for v in vals]
    nonzero = [abs(x) for x in ints if x != 0]
    if nonzero:
        g = nonzero[0]
        for x in nonzero[1:]:
            g = math.gcd(g, x)
        if g:
            ints = [x // g for x in ints]
    for x in ints:
        if x != 0:
            if x < 0:
                ints = [-v for v in ints]
            break
    return tuple(ints)


def scale_basis_to_primitive(basis: Mat) -> Mat:
    scaled: Mat = []
    for vec in basis:
        prim = primitive_int_vec(vec)
        if any(prim):
            scaled.append([Fraction(v, 1) for v in prim])
        else:
            scaled.append([Fraction(v) for v in vec])
    return scaled


def stabilizer_for_subspace(x0: Vec, basis: Mat, ops: List[Op]) -> List[Op]:
    """Pointwise stabilizer of the subspace (affine set)."""
    ops_sig = _ops_signature(ops)
    key = (
        tuple(Fraction(v) for v in x0),
        tuple(tuple(Fraction(v) for v in row) for row in basis),
        ops_sig,
        RECIPROCAL_MODE,
    )
    cached = _stabilizer_cache.get(key)
    if cached is not None:
        return [ops[i] for i in cached]

    stab_indices: List[int] = []
    for idx, op in enumerate(ops):
        if not equal_mod1(op.apply(x0), x0):
            continue
        ok = True
        for bvec in basis:
            img = [sum(op.W[i][k] * bvec[k] for k in range(3)) for i in range(3)]
            if any(img[i] != bvec[i] for i in range(3)):
                ok = False
                break
        if ok:
            stab_indices.append(idx)
    _stabilizer_cache[key] = tuple(stab_indices)
    return [ops[i] for i in stab_indices]


def stabilizer_indices_for_subspace(x0: Vec, basis: Mat, ops: List[Op]) -> List[int]:
    stab_indices: List[int] = []
    for idx, op in enumerate(ops):
        if not equal_mod1(op.apply(x0), x0):
            continue
        ok = True
        for bvec in basis:
            img = [sum(op.W[i][k] * bvec[k] for k in range(3)) for i in range(3)]
            if any(img[i] != bvec[i] for i in range(3)):
                ok = False
                break
        if ok:
            stab_indices.append(idx)
    return stab_indices


def _ops_signature(ops: List[Op]) -> Tuple:
    return tuple(op_key(op) for op in ops)


_stabilizer_cache: Dict[
    Tuple[
        Tuple[Fraction, ...],
        Tuple[Tuple[Fraction, ...], ...],
        Tuple,
        bool,
    ],
    Tuple[int, ...],
] = {}


def op_fix_constraints(op: Op) -> Tuple[Mat, List[Fraction]]:
    A: Mat = []
    c: List[Fraction] = []
    W_minus_I = [[op.W[row][col] - (1 if row == col else 0) for col in range(3)] for row in range(3)]
    b = [Fraction(0) if RECIPROCAL_MODE else mod1(-op.t[i]) for i in range(3)]
    for row, rhs in zip(W_minus_I, b):
        if any(val != 0 for val in row) or rhs != 0:
            A.append([Fraction(v) for v in row])
            c.append(Fraction(rhs))
    return A, c


def is_pure_translation(op: Op) -> bool:
    return all(op.W[i][j] == (1 if i == j else 0) for i in range(3) for j in range(3))


def constraints_from_subspace_cached(x0: Vec, basis: Mat) -> Tuple[Mat, List[Fraction]]:
    # (kept simple; hook point if you want more caching)
    return constraints_from_subspace(x0, basis)


def intersect_with_constraints_precomputed(
    A_cur: Mat,
    c_cur: List[Fraction],
    A_extra: Mat,
    c_extra: List[Fraction],
) -> List[Tuple[Vec, Mat]]:
    A_comb = A_cur + A_extra
    c_comb = c_cur + c_extra
    return solve_congruence(A_comb, c_comb)


def closure_under_stabilizer(
    x0: Vec,
    basis: Mat,
    ops: List[Op],
) -> List[Tuple[Vec, Mat]]:
    """Compute Fix(stab(subspace)) to close under the full pointwise stabilizer."""
    A_all: Mat = []
    c_all: List[Fraction] = []
    stab_ops = stabilizer_for_subspace(x0, basis, ops)
    for op in stab_ops:
        A, c = op_fix_constraints(op)
        A_all += A
        c_all += c
    if not A_all:
        return [(x0, basis)]
    return solve_congruence(A_all, c_all)


# --- symbolic expressions for output ----------------------------------------

Expr = Tuple[Fraction, Dict[str, Fraction]]  # (constant, coeffs)

ORIGIN_SHIFTS: List[Tuple[Fraction, Fraction, Fraction]] = [
    (Fraction(0), Fraction(0), Fraction(0)),
    (Fraction(0), Fraction(0), Fraction(1, 2)),
    (Fraction(0), Fraction(1, 2), Fraction(0)),
    (Fraction(1, 2), Fraction(0), Fraction(0)),
    (Fraction(0), Fraction(1, 2), Fraction(1, 2)),
    (Fraction(1, 2), Fraction(0), Fraction(1, 2)),
    (Fraction(1, 2), Fraction(1, 2), Fraction(0)),
]


def expr_from_const(c: Fraction) -> Expr:
    return Fraction(c), {}


def expr_from_param(name: str, coeff: Fraction) -> Expr:
    return Fraction(0), {name: Fraction(coeff)}


def expr_add(a: Expr, b: Expr) -> Expr:
    const = a[0] + b[0]
    coeffs: Dict[str, Fraction] = dict(a[1])
    for k, v in b[1].items():
        coeffs[k] = coeffs.get(k, Fraction(0)) + v
        if coeffs[k] == 0:
            coeffs.pop(k)
    return const, coeffs


def expr_scale(expr: Expr, s: Fraction) -> Expr:
    return expr[0] * s, {k: v * s for k, v in expr[1].items()}


def substitute_param(vec: List[Expr], param: str, value: Fraction) -> List[Expr]:
    out: List[Expr] = []
    for const, coeffs in vec:
        coeff = coeffs.get(param, Fraction(0))
        new_const = mod1(const + coeff * value)
        new_coeffs = dict(coeffs)
        if param in new_coeffs:
            new_coeffs.pop(param)
        out.append((new_const, new_coeffs))
    return out


def normalize_expr(expr: Expr) -> Expr:
    const, coeffs = expr
    return mod1(const), coeffs


def normalize_expr_nonneg(expr: Expr) -> Expr:
    const, coeffs = expr
    while const < 0:
        const += 1
    return const, coeffs


def expr_vec_signature(
    vec: List[Expr],
    centering_vecs: Optional[List[Tuple[Fraction, Fraction, Fraction]]] = None,
    origin_shifts: Optional[List[Tuple[Fraction, Fraction, Fraction]]] = None,
) -> Tuple:
    if centering_vecs is None:
        return tuple(
            (const, tuple(sorted(coeffs.items())))
            for const, coeffs in (normalize_expr(expr) for expr in vec)
        )
    if origin_shifts is None:
        origin_shifts = ORIGIN_SHIFTS
    vec_key = tuple((expr[0], tuple(sorted(expr[1].items()))) for expr in vec)
    centering_key = tuple(tuple(c) for c in centering_vecs)
    origin_key = tuple(tuple(o) for o in origin_shifts)
    return _expr_vec_signature_cached(vec_key, centering_key, origin_key)


@lru_cache(maxsize=4096)
def _expr_vec_signature_cached(
    vec_key: Tuple[Tuple[Fraction, Tuple[Tuple[str, Fraction], ...]], ...],
    centering_key: Tuple[Tuple[Fraction, Fraction, Fraction], ...],
    origin_key: Tuple[Tuple[Fraction, Fraction, Fraction], ...],
) -> Tuple[Tuple, Tuple[Fraction, Fraction, Fraction]]:
    vec = [(const, dict(coeffs)) for const, coeffs in vec_key]
    centering_vecs = [tuple(c) for c in centering_key]
    origin_shifts = [tuple(o) for o in origin_key]
    return _expr_vec_signature_impl(vec, centering_vecs, origin_shifts)


def _expr_vec_signature_impl(
    vec: List[Expr],
    centering_vecs: List[Tuple[Fraction, Fraction, Fraction]],
    origin_shifts: List[Tuple[Fraction, Fraction, Fraction]],
) -> Tuple[Tuple, Tuple[Fraction, Fraction, Fraction]]:
    coeff_sig = tuple(tuple(sorted(expr[1].items())) for expr in vec)
    consts = [expr[0] for expr in vec]
    best_key = None
    dedup_sig = None
    for origin_shift in origin_shifts:
        origin_bias = 0 if all(val == 0 for val in origin_shift) else 1
        for centering in centering_vecs:
            centering_bias = 0 if all(val == 0 for val in centering) else 1
            shifted = [mod1(consts[i] - centering[i] - origin_shift[i]) for i in range(3)]
            score = dedup_coord_score(shifted)
            sig = (score, tuple(shifted), coeff_sig)
            if dedup_sig is None or sig < dedup_sig:
                dedup_sig = sig
            score_main, score_tail = score[:-1], score[-1]
            half_bias = tuple(1 if val > Fraction(1, 2) else 0 for val in shifted)
            key = (score_main, centering_bias, origin_bias, half_bias, score_tail, tuple(shifted), coeff_sig)
            if best_key is None or key < best_key:
                best_key = key
    if dedup_sig is None:
        base = tuple(mod1_vec(consts))
        return ((dedup_coord_score(base), base, coeff_sig), base)
    return dedup_sig, dedup_sig[1]


def frac_str(x: Fraction, max_den: int = 12) -> str:
    f = Fraction(x).limit_denominator(max_den)
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


def expr_to_str(expr: Expr) -> str:
    const, coeffs = expr
    terms = []
    for name in sorted(coeffs):
        coeff = coeffs[name]
        if coeff == 1:
            terms.append(name)
        elif coeff == -1:
            terms.append(f"-{name}")
        else:
            terms.append(f"{frac_str(coeff)}{name}")
    if const != 0 or not terms:
        terms.append(frac_str(const))
    out = terms[0]
    for t in terms[1:]:
        if t.startswith("-"):
            out += f" {t}"
        else:
            out += f" + {t}"
    return out


def vector_expr_str(vec: List[Expr]) -> str:
    return ", ".join(expr_to_str(e).replace("+ -", "- ") for e in vec)


def format_coordinate_with_moment(coord_str: str, moment_str: str) -> str:
    return f"({coord_str} | {moment_str})"


def param_names_for_basis(basis: Mat, axis_letters: Optional[List[str]] = None) -> List[str]:
    dim = len(basis)
    if dim == 0:
        return []
    axis_letters = axis_letters or ["x", "y", "z"]
    names: List[str] = []
    used = set()
    for vec in basis:
        abs_vals = [abs(v) for v in vec]
        axis_idx = max(range(3), key=lambda i: abs_vals[i])
        chosen = None
        if abs_vals[axis_idx] != 0 and axis_letters[axis_idx] not in used:
            chosen = axis_letters[axis_idx]
        else:
            for a in axis_letters:
                if a not in used:
                    chosen = a
                    break
        if chosen is None:
            chosen = f"t{len(names)}"
        names.append(chosen)
        used.add(chosen)
    return names


def build_symbolic_rep(x0: Vec, basis: Mat, axis_letters: Optional[List[str]] = None) -> List[Expr]:
    params = param_names_for_basis(basis, axis_letters=axis_letters)
    vec = []
    for coord in range(3):
        expr = expr_from_const(x0[coord])
        for p, bvec in zip(params, basis):
            expr = expr_add(expr, expr_from_param(p, bvec[coord]))
        vec.append(expr)
    return vec


def reparam_expr_vec(vec: List[Expr], param: str, scale: Fraction, shift: Fraction) -> List[Expr]:
    out: List[Expr] = []
    for const, coeffs in vec:
        coeff = coeffs.get(param, Fraction(0))
        new_const = const + coeff * shift
        new_coeffs = dict(coeffs)
        if param in new_coeffs:
            new_coeffs[param] = new_coeffs[param] * scale
            if new_coeffs[param] == 0:
                new_coeffs.pop(param)
        out.append((new_const, new_coeffs))
    return out


def apply_op_expr(op: Op, vec: List[Expr]) -> List[Expr]:
    out: List[Expr] = []
    for i in range(3):
        expr = expr_from_const(op.t[i])
        for k in range(3):
            expr = expr_add(expr, expr_scale(vec[k], op.W[i][k]))
        out.append(expr)
    return out


def apply_mat_to_vec_expr(M: Mat, v: List[Expr]) -> List[Expr]:
    out: List[Expr] = []
    zero: Expr = (Fraction(0), {})
    for i in range(3):
        acc: Expr = zero
        for j in range(3):
            if M[i][j] == 0:
                continue
            acc = expr_add(acc, expr_scale(v[j], M[i][j]))
        out.append(acc)
    return out


def ordered_unique(seq: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for item in seq:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def float_matrix_tuple(mat: Sequence[Sequence[float]]) -> Tuple[Tuple[float, float, float], ...]:
    arr = np.asarray(mat, dtype=float)
    if arr.shape != (3, 3):
        raise ValueError(f"Expected 3x3 matrix, got shape {arr.shape}")
    return tuple(tuple(float(arr[i, j]) for j in range(3)) for i in range(3))


def clean_numeric(value: float, tol: float = 1e-9) -> float:
    value = float(value)
    if abs(value) <= tol:
        return 0.0
    for target in (-1.0, 1.0):
        if abs(value - target) <= tol:
            return target
    return value


def clean_numeric_vec(vec: Sequence[float], tol: float = 1e-9) -> NumericVec:
    return [clean_numeric(v, tol=tol) for v in vec]


def clean_numeric_mat(mat: Sequence[Sequence[float]], tol: float = 1e-9) -> NumericMat:
    return [clean_numeric_vec(row, tol=tol) for row in mat]


@dataclass(frozen=True)
class MagneticOp:
    W: Tuple[Tuple[Fraction, Fraction, Fraction], ...]
    t: Tuple[Fraction, Fraction, Fraction]
    tr: bool = False

    def apply(self, r: Sequence[Fraction]) -> List[Fraction]:
        return [
            sum(self.W[i][k] * r[k] for k in range(3)) + self.t[i]
            for i in range(3)
        ]


def mw_det3(M: Mat) -> int:
    d = (
        M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
        - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
        + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0])
    )
    return int(d)


def mw_mat_equal(A: Mat, B: Mat) -> bool:
    return all(A[i][j] == B[i][j] for i in range(3) for j in range(3))


def mw_mat_trace(M: Mat) -> Fraction:
    return M[0][0] + M[1][1] + M[2][2]


def mw_rotation_order(R: Mat, max_order: int = 12) -> int:
    identity = identity_mat()
    cur = identity_mat()
    for order in range(1, max_order + 1):
        cur = mat_mul(cur, R)
        if mw_mat_equal(cur, identity):
            return order
    return max_order


def mw_normalize_dir(vec: Sequence[Fraction]) -> Tuple[int, int, int]:
    direction = primitive_int_vec(vec)
    for value in direction:
        if value == 0:
            continue
        if value < 0:
            direction = tuple(-entry for entry in direction)
        break
    return direction


def mw_rotation_axis(R: Mat) -> Optional[Vec]:
    basis = nullspace([[R[i][j] - (1 if i == j else 0) for j in range(3)] for i in range(3)])
    return basis[0] if basis else None


def mw_mirror_normal(R: Mat) -> Optional[Vec]:
    basis = nullspace([[R[i][j] + (1 if i == j else 0) for j in range(3)] for i in range(3)])
    return basis[0] if basis else None


def mw_rotoinversion_axis(R: Mat) -> Optional[Vec]:
    axis = mw_rotation_axis(mat_mul(R, R))
    if axis is not None:
        return axis
    return mw_rotation_axis(R)


def mw_is_minus_identity(R: Mat) -> bool:
    return all(R[i][j] == (-1 if i == j else 0) for i in range(3) for j in range(3))


def mw_is_identity_matrix(R: Mat) -> bool:
    return all(R[i][j] == (1 if i == j else 0) for i in range(3) for j in range(3))


def mw_direction_to_custom_axis_label(direction: Optional[Tuple[int, int, int]]) -> Optional[str]:
    if direction is None:
        return None
    axis_map = {
        (1, 0, 0): "x",
        (0, 1, 0): "y",
        (0, 0, 1): "z",
    }
    if direction in axis_map:
        return axis_map[direction]
    return "".join("0" if value == 0 else str(value) for value in direction)


def mw_magnetic_symmetry_element(op: MagneticOp) -> Optional[dict]:
    rotation = [[Fraction(x) for x in row] for row in op.W]
    det = mw_det3(rotation)
    order = mw_rotation_order(rotation)

    if mw_is_identity_matrix(rotation):
        if op.tr:
            return {
                "kind": "identity",
                "symbol": "1",
                "axis_direction": None,
                "axis_label": None,
                "time_reversal": True,
                "order": 1,
            }
        return None

    if det == -1 and mw_is_minus_identity(rotation):
        return {
            "kind": "inversion",
            "symbol": "-1",
            "axis_direction": None,
            "axis_label": None,
            "time_reversal": op.tr,
            "order": 1,
        }

    if det == 1:
        axis = mw_rotation_axis(rotation)
        if axis is None:
            return None
        axis_direction = mw_normalize_dir(axis)
        return {
            "kind": "rotation",
            "symbol": str(order),
            "axis_direction": axis_direction,
            "axis_label": mw_direction_to_custom_axis_label(axis_direction),
            "time_reversal": op.tr,
            "order": order,
        }

    if order == 2:
        normal = mw_mirror_normal(rotation)
        if normal is None:
            return None
        axis_direction = mw_normalize_dir(normal)
        return {
            "kind": "mirror",
            "symbol": "m",
            "axis_direction": axis_direction,
            "axis_label": mw_direction_to_custom_axis_label(axis_direction),
            "time_reversal": op.tr,
            "order": 2,
        }

    axis = mw_rotoinversion_axis(rotation)
    if axis is None:
        return None
    axis_direction = mw_normalize_dir(axis)
    hm_order = order
    rotation_cubed = mat_mul(mat_mul(rotation, rotation), rotation)
    if order == 6 and mw_is_minus_identity(rotation_cubed):
        hm_order = 3
    return {
        "kind": "rotoinversion",
        "symbol": f"-{hm_order}",
        "axis_direction": axis_direction,
        "axis_label": mw_direction_to_custom_axis_label(axis_direction),
        "time_reversal": op.tr,
        "order": hm_order,
    }


def mw_magnetic_element_priority(elem: dict) -> Tuple[int, int]:
    kind_rank = {
        "rotation": 0,
        "rotoinversion": 1,
        "mirror": 2,
        "inversion": 3,
        "identity": 4,
    }
    return (-int(elem.get("order", 0)), kind_rank.get(str(elem.get("kind")), 9))


def mw_magnetic_element_axis_sort_key(
    axis_label: Optional[str],
    axis_direction: Optional[Tuple[int, int, int]],
) -> Tuple:
    if axis_label is None:
        return (2, 99, "", ())
    if axis_label == "x":
        return (0, 0, "x", ())
    if axis_label == "y":
        return (0, 1, "y", ())
    if axis_label == "z":
        return (0, 2, "z", ())
    direction = axis_direction or (0, 0, 0)
    return (1, sum(abs(v) for v in direction), axis_label, tuple(abs(v) for v in direction))


def mw_format_custom_site_symmetry_token(elem: dict) -> str:
    symbol = str(elem["symbol"])
    if elem.get("time_reversal"):
        symbol += "'"
    axis_label = elem.get("axis_label")
    if axis_label is None:
        return symbol
    return f"{symbol}[{axis_label}]"


def mw_collect_custom_site_symmetry_elements(stab_ops: List[MagneticOp]) -> List[dict]:
    elements = [mw_magnetic_symmetry_element(op) for op in stab_ops]
    has_antiidentity = any(elem and elem["kind"] == "identity" for elem in elements)
    best: Dict[Tuple, dict] = {}
    for elem in elements:
        if elem is None:
            continue
        if has_antiidentity and elem["time_reversal"] and elem["kind"] != "identity":
            continue
        key = (elem["kind"], elem["axis_direction"], elem["time_reversal"])
        if key not in best or mw_magnetic_element_priority(elem) < mw_magnetic_element_priority(best[key]):
            best[key] = elem
    out = list(best.values())
    kind_order = {
        "rotation": 0,
        "mirror": 1,
        "rotoinversion": 2,
        "inversion": 3,
        "identity": 4,
    }
    out.sort(
        key=lambda elem: (
            mw_magnetic_element_axis_sort_key(elem.get("axis_label"), elem.get("axis_direction")),
            kind_order.get(str(elem.get("kind")), 9),
            -int(elem.get("order", 0)),
            1 if elem.get("time_reversal") else 0,
            str(elem.get("symbol", "")),
        )
    )
    return out


def mw_serialize_custom_site_symmetry_ops(stab_ops: List[MagneticOp]) -> List[dict]:
    serialized: List[dict] = []
    for elem in mw_collect_custom_site_symmetry_elements(stab_ops):
        axis_direction = elem.get("axis_direction")
        serialized.append(
            {
                "token": mw_format_custom_site_symmetry_token(elem),
                "type": elem["symbol"],
                "kind": elem["kind"],
                "axis": elem.get("axis_label"),
                "axis_direction": list(axis_direction) if axis_direction is not None else None,
                "time_reversal": bool(elem.get("time_reversal", False)),
            }
        )
    return serialized


def mw_build_custom_site_symmetry(stab_ops: List[MagneticOp]) -> Tuple[str, List[dict]]:
    ops = mw_serialize_custom_site_symmetry_ops(stab_ops)
    if not ops:
        return "1", []
    return " * ".join(op["token"] for op in ops), ops


def mw_bilbao_magnetic_point_group_symbol(
    site_symmetry_ops: List[dict],
    *,
    crystal_system: str,
) -> Optional[str]:
    system = str(crystal_system or "").strip().lower()
    tokens = tuple(sorted(str(op.get("token", "")).strip() for op in site_symmetry_ops if op.get("token")))
    if not tokens:
        return "1"

    if system == "monoclinic":
        mapping = {
            ("1'",): "11'",
            ("-1",): "-1",
            ("-1'",): "-1'",
            ("2[y]",): "2",
            ("2'[y]",): "2'",
            ("m[y]",): "m",
            ("m'[y]",): "m'",
            ("1'", "2[y]"): "21'",
            ("1'", "m[y]"): "m1'",
            ("-1", "2[y]", "m[y]"): "2/m",
            ("-1'", "2'[y]", "m[y]"): "2'/m",
            ("-1'", "2[y]", "m'[y]"): "2/m'",
            ("-1", "2'[y]", "m'[y]"): "2'/m'",
        }
        return mapping.get(tokens)

    return None


_POINT_GROUP_SIGNATURES: Dict[str, Dict[Tuple, str]] = {}


def mw_rotation_signature(rotations: List[Mat]) -> Tuple:
    counts: Counter[Tuple[int, int, Fraction]] = Counter()
    for rotation in rotations:
        counts[(mw_det3(rotation), mw_rotation_order(rotation), mw_mat_trace(rotation))] += 1
    return tuple(sorted(counts.items()))


def mw_resolve_space_group_json_dir(base_dir: Path) -> Path:
    script_dir = Path(__file__).resolve().parent
    candidates = [
        Path(base_dir),
        script_dir / "space_groups_json",
        script_dir.parent / "wyckoff_Kpoint" / "space_groups_json",
        script_dir.parent / "wyckoff_kpoints" / "space_groups_json",
    ]
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if (candidate / "space-groups.pretty_sg-1.json").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find a usable space_groups_json directory. Tried: "
        + ", ".join(str(path) for path in candidates)
    )


def mw_build_point_group_signature_lookup(json_dir: Optional[Path] = None) -> Dict[Tuple, str]:
    if json_dir is None:
        json_dir = Path(__file__).resolve().parent / "space_groups_json"
    json_dir = mw_resolve_space_group_json_dir(json_dir)
    cache_key = str(json_dir)
    if cache_key in _POINT_GROUP_SIGNATURES:
        return _POINT_GROUP_SIGNATURES[cache_key]

    sig_map: Dict[Tuple, str] = {}
    for path in sorted(json_dir.glob("space-groups.pretty_sg-*.json")):
        data = json.loads(path.read_text())
        point_group = data.get("point_group")
        if not point_group:
            continue
        hm = SCHOENFLIES_TO_HM.get(point_group, point_group)
        rotations = unique_rotations([op_from_json(op) for op in data.get("operations", [])])
        sig = mw_rotation_signature(rotations)
        sig_map.setdefault(sig, hm)

    _POINT_GROUP_SIGNATURES[cache_key] = sig_map
    return sig_map


def mw_classify_site_symmetry(rotations: List[Mat], lookup: Dict[Tuple, str]) -> str:
    if not rotations:
        return "?"
    sig = mw_rotation_signature(rotations)
    if sig in lookup:
        return lookup[sig]
    if len(rotations) == 1:
        return "1"
    return "?"


def mw_axial_vector_action(op: MagneticOp) -> Mat:
    sign = Fraction(mw_det3([[Fraction(x) for x in row] for row in op.W]), 1)
    if op.tr:
        sign *= -1
    return [[sign * Fraction(op.W[i][j]) for j in range(3)] for i in range(3)]


def mw_shift_op(op: MagneticOp, shift: Tuple[Fraction, Fraction, Fraction]) -> MagneticOp:
    shifted = shift_op(Op(W=op.W, t=op.t), shift)
    return MagneticOp(W=shifted.W, t=shifted.t, tr=op.tr)


def mw_mat_vec_fraction(
    W: Sequence[Sequence[Fraction]],
    v: Sequence[Fraction],
) -> List[Fraction]:
    out: List[Fraction] = []
    for i in range(3):
        total = Fraction(0)
        for j in range(3):
            total += Fraction(W[i][j]) * Fraction(v[j])
        out.append(total)
    return out


def mw_phase_from_fraction(value: Fraction) -> complex:
    angle = -2.0 * math.pi * float(value)
    z = complex(math.cos(angle), math.sin(angle))
    if abs(z.real) < 1e-12:
        z = complex(0.0, z.imag)
    if abs(z.imag) < 1e-12:
        z = complex(z.real, 0.0)
    return z


def mw_realify_fourier_action_matrix(action: np.ndarray, antiunitary: bool) -> np.ndarray:
    real = action.real
    imag = action.imag
    if antiunitary:
        return np.block([[real, imag], [imag, -real]])
    return np.block([[real, -imag], [imag, real]])


def mw_numeric_rref(matrix: np.ndarray, tol: float = 1e-9) -> Tuple[np.ndarray, List[int]]:
    mat = np.array(matrix, dtype=float, copy=True)
    if mat.ndim != 2:
        raise ValueError("numeric_rref expects a 2D matrix")
    rows, cols = mat.shape
    pivots: List[int] = []
    row = 0
    scale = max(1.0, float(np.max(np.abs(mat)))) if mat.size else 1.0
    eps = tol * scale
    for col in range(cols):
        if row >= rows:
            break
        pivot = max(range(row, rows), key=lambda idx: abs(mat[idx, col]))
        if abs(mat[pivot, col]) <= eps:
            continue
        if pivot != row:
            mat[[row, pivot]] = mat[[pivot, row]]
        mat[row] = mat[row] / mat[row, col]
        for ridx in range(rows):
            if ridx == row:
                continue
            factor = mat[ridx, col]
            if abs(factor) <= eps:
                continue
            mat[ridx] -= factor * mat[row]
        pivots.append(col)
        row += 1
    mat[np.abs(mat) <= eps] = 0.0
    return mat, pivots


def mw_canonical_real_nullspace_basis(
    constraints: np.ndarray,
    ncols: int,
    tol: float = 1e-9,
) -> np.ndarray:
    if constraints.size == 0:
        return np.eye(ncols, dtype=float)
    rref_mat, pivots = mw_numeric_rref(constraints, tol=tol)
    free_cols = [idx for idx in range(ncols) if idx not in pivots]
    if not free_cols:
        return np.zeros((ncols, 0), dtype=float)
    basis = np.zeros((ncols, len(free_cols)), dtype=float)
    pivot_rows = {pivot: ridx for ridx, pivot in enumerate(pivots)}
    for bidx, free_col in enumerate(free_cols):
        basis[free_col, bidx] = 1.0
        for pivot_col, row_idx in pivot_rows.items():
            basis[pivot_col, bidx] = -rref_mat[row_idx, free_col]
    scale = max(1.0, float(np.max(np.abs(basis)))) if basis.size else 1.0
    eps = tol * scale
    basis[np.abs(basis) <= eps] = 0.0
    for col in range(basis.shape[1]):
        for row in range(basis.shape[0]):
            value = basis[row, col]
            if abs(value) <= eps:
                continue
            if value < 0:
                basis[:, col] *= -1
            break
    return basis


def mw_real_basis_to_complex_columns(real_basis: np.ndarray, tol: float = 1e-9) -> List[np.ndarray]:
    if real_basis.size == 0:
        return []
    cols: List[np.ndarray] = []
    scale = max(1.0, float(np.max(np.abs(real_basis)))) if real_basis.size else 1.0
    eps = tol * scale
    for idx in range(real_basis.shape[1]):
        col = real_basis[:, idx]
        real = np.where(np.abs(col[:3]) <= eps, 0.0, col[:3])
        imag = np.where(np.abs(col[3:]) <= eps, 0.0, col[3:])
        cols.append((real + 1j * imag).astype(np.complex128))
    return cols


def mw_approx_fraction_from_float(
    value: float,
    tol: float = 1e-8,
    max_den: int = 24,
) -> Optional[Fraction]:
    if abs(value) <= tol:
        return Fraction(0)
    rounded = round(value)
    if abs(value - rounded) <= tol:
        return Fraction(int(rounded), 1)
    approx = Fraction(value).limit_denominator(max_den)
    if abs(float(approx) - value) <= 1e-6:
        return approx
    return None


def mw_real_display_vector_from_complex_column(
    column: np.ndarray,
    tol: float = 1e-8,
    max_den: int = 24,
) -> Optional[List[Fraction]]:
    if column.size == 0:
        return [Fraction(0), Fraction(0), Fraction(0)]
    scale = max(1.0, float(np.max(np.abs(column))))
    eps = tol * scale
    phase = 1.0 + 0.0j
    for value in column:
        if abs(value) > eps:
            phase = np.conjugate(value) / abs(value)
            break
    rotated = phase * column
    if any(abs(complex(value).imag) > 1e-6 * scale for value in rotated):
        return None
    real_values = [float(complex(value).real) for value in rotated]
    ref = next((abs(v) for v in real_values if abs(v) > eps), None)
    if ref is None:
        return [Fraction(0), Fraction(0), Fraction(0)]
    normalized = [v / ref for v in real_values]
    approx = [mw_approx_fraction_from_float(v, tol=1e-6, max_den=max_den) for v in normalized]
    if any(value is None for value in approx):
        return None
    primitive = primitive_int_vec([Fraction(v) for v in approx if v is not None])
    return [Fraction(value, 1) for value in primitive]


def mw_reduce_real_display_basis(basis: Mat) -> Mat:
    if not basis:
        return []
    reduced = rref([list(vec) for vec in basis])
    reduced = [vec for vec in reduced if any(value != 0 for value in vec)]
    reduced = scale_basis_to_primitive(reduced)
    reduced = canonicalize_axis_aligned_basis(reduced)
    return reduced


def mw_build_symbolic_rep_with_params(basis: Mat, param_names: List[str]) -> List[Expr]:
    vec: List[Expr] = []
    for coord in range(3):
        expr = expr_from_const(Fraction(0))
        for param, bvec in zip(param_names, basis):
            expr = expr_add(expr, expr_from_param(param, bvec[coord]))
        vec.append(expr)
    return vec


def mw_fraction_basis_vector_strings(basis: Mat) -> List[str]:
    return [", ".join(frac_str(value) for value in vec) for vec in basis]


def mw_support_only_display_constraints(
    basis_columns: List[np.ndarray],
    axis_letters: Optional[List[str]] = None,
    tol: float = 1e-8,
) -> Tuple[List[str], str]:
    axis_letters = axis_letters or ["mx", "my", "mz"]
    support: List[str] = []
    for comp_idx in range(3):
        nonzero = any(abs(complex(column[comp_idx])) > tol for column in basis_columns)
        support.append(axis_letters[comp_idx] if nonzero else "0")
    nonzero_axes = [axis_letters[i] for i in range(3) if support[i] != "0"]
    basis_strings = [
        "1, 0, 0" if name == "mx" else "0, 1, 0" if name == "my" else "0, 0, 1"
        for name in nonzero_axes
    ]
    return basis_strings, ", ".join(support)


def mw_wyckoff_like_display_from_complex_basis(
    basis_columns: List[np.ndarray],
    *,
    axis_letters: Optional[List[str]] = None,
    tol: float = 1e-8,
    max_den: int = 24,
) -> Tuple[List[str], str]:
    axis_letters = axis_letters or ["mx", "my", "mz"]
    if not basis_columns:
        return [], "0, 0, 0"
    display_vectors: Mat = []
    for column in basis_columns:
        real_vec = mw_real_display_vector_from_complex_column(column, tol=tol, max_den=max_den)
        if real_vec is None:
            return mw_support_only_display_constraints(
                basis_columns,
                axis_letters=axis_letters,
                tol=tol,
            )
        if any(real_vec):
            display_vectors.append(real_vec)
    display_basis = mw_reduce_real_display_basis(display_vectors)
    if not display_basis:
        return [], "0, 0, 0"
    params = param_names_for_basis(display_basis, axis_letters=axis_letters)
    rep_vec = mw_build_symbolic_rep_with_params(display_basis, params)
    return mw_fraction_basis_vector_strings(display_basis), vector_expr_str(rep_vec)


def mw_normalize_bilbao_point_group_symbol(symbol: str) -> str:
    return str(symbol or "").replace(".", "").strip()


def mw_generic_site_symmetry_signature(site_symmetry_ops: List[dict]) -> str:
    tokens: List[str] = []
    for op in site_symmetry_ops or []:
        base = str(op.get("type", "")).strip()
        if not base:
            continue
        if op.get("time_reversal"):
            base += "'"
        tokens.append(base)
    if not tokens:
        return "1"
    return " * ".join(sorted(tokens))


def mw_resolve_magnetic_point_group_lookup_path(base_path: Optional[Path] = None) -> Optional[Path]:
    script_dir = Path(__file__).resolve().parent
    candidates: List[Path] = []
    if base_path is not None:
        candidates.append(Path(base_path))
    candidates.append(script_dir / "all_magnetic_groups_wyckoff_moments_custom_site.json")
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=2)
def mw_load_magnetic_point_group_bilbao_maps(
    path: str,
) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]], Dict[str, str], Dict[str, str]]:
    data = json.loads(Path(path).read_text())
    exact_counts: Dict[str, Dict[str, Counter[str]]] = {}
    generic_counts: Dict[str, Dict[str, Counter[str]]] = {}
    for group in data.get("groups", []):
        for wp in group.get("wyckoff_positions", []):
            custom = str(wp.get("site_symmetry_custom", "")).strip()
            bilbao = mw_normalize_bilbao_point_group_symbol(wp.get("site_symmetry", ""))
            unitary = mw_normalize_bilbao_point_group_symbol(wp.get("unitary_site_symmetry", ""))
            generic = mw_generic_site_symmetry_signature(wp.get("site_symmetry_ops", []))
            if not bilbao:
                continue
            if custom:
                exact_counts.setdefault(custom, {}).setdefault(unitary, Counter())[bilbao] += 1
            generic_counts.setdefault(generic, {}).setdefault(unitary, Counter())[bilbao] += 1

    def finalize(counts: Dict[str, Dict[str, Counter[str]]]) -> Dict[str, Dict[str, str]]:
        return {
            key: {
                unitary: counter.most_common(1)[0][0]
                for unitary, counter in unitary_map.items()
                if counter
            }
            for key, unitary_map in counts.items()
        }

    def flatten(counts: Dict[str, Dict[str, Counter[str]]]) -> Dict[str, str]:
        flattened: Dict[str, str] = {}
        for key, unitary_map in counts.items():
            merged: Counter[str] = Counter()
            for counter in unitary_map.values():
                merged.update(counter)
            if merged:
                flattened[key] = merged.most_common(1)[0][0]
        return flattened

    exact = finalize(exact_counts)
    generic = finalize(generic_counts)
    return exact, generic, flatten(exact_counts), flatten(generic_counts)


def mw_lookup_magnetic_bilbao_symbol(
    custom_symbol: str,
    unitary_bilbao_symbol: str,
    site_symmetry_ops: Optional[List[dict]] = None,
) -> Optional[str]:
    resolved = mw_resolve_magnetic_point_group_lookup_path()
    if resolved is None:
        return None
    exact, generic, exact_flat, generic_flat = mw_load_magnetic_point_group_bilbao_maps(str(resolved))
    custom = str(custom_symbol).strip()
    unitary = mw_normalize_bilbao_point_group_symbol(unitary_bilbao_symbol)
    signature = mw_generic_site_symmetry_signature(site_symmetry_ops or [])
    if custom:
        if unitary and unitary in exact.get(custom, {}):
            return exact[custom][unitary]
        if custom in exact_flat:
            return exact_flat[custom]
    if unitary and unitary in generic.get(signature, {}):
        return generic[signature][unitary]
    return generic_flat.get(signature)


mw = SimpleNamespace(
    Op=MagneticOp,
    axial_vector_action=mw_axial_vector_action,
    shift_op=mw_shift_op,
    build_point_group_signature_lookup=mw_build_point_group_signature_lookup,
    classify_site_symmetry=mw_classify_site_symmetry,
    build_custom_site_symmetry=mw_build_custom_site_symmetry,
    lookup_magnetic_bilbao_symbol=mw_lookup_magnetic_bilbao_symbol,
    bilbao_magnetic_point_group_symbol=mw_bilbao_magnetic_point_group_symbol,
    mat_vec_fraction=mw_mat_vec_fraction,
    phase_from_fraction=mw_phase_from_fraction,
    realify_fourier_action_matrix=mw_realify_fourier_action_matrix,
    canonical_real_nullspace_basis=mw_canonical_real_nullspace_basis,
    real_basis_to_complex_columns=mw_real_basis_to_complex_columns,
    wyckoff_like_display_from_complex_basis=mw_wyckoff_like_display_from_complex_basis,
)


def spin_matrix_key(mat: Sequence[Sequence[float]], digits: int = 8) -> Tuple[float, ...]:
    arr = np.asarray(mat, dtype=float)
    return tuple(round(float(x), digits) for x in arr.reshape(-1))


def spin_op_key(op: SpinOp) -> Tuple[Tuple[Fraction, ...], Tuple[Fraction, ...], int, Tuple[float, ...]]:
    return (
        tuple(x for row in op.W for x in row),
        tuple(mod1(v) for v in op.t),
        1 if op.tr else 0,
        spin_matrix_key(op.spin),
    )


def shift_spin_op(op: SpinOp, shift: Tuple[Fraction, Fraction, Fraction]) -> SpinOp:
    shifted = shift_op(Op(W=op.W, t=op.t), shift)
    return SpinOp(W=shifted.W, t=shifted.t, tr=op.tr, spin=op.spin)


def axial_spin_matrix_for_op(op: Op, tr: bool) -> Tuple[Tuple[float, float, float], ...]:
    axial = mw.axial_vector_action(
        mw.Op(
            W=tuple(tuple(Fraction(x) for x in row) for row in op.W),
            t=tuple(Fraction(v) for v in op.t),
            tr=bool(tr),
        )
    )
    return tuple(tuple(float(x) for x in row) for row in axial)


def build_magnetic_ops(ops: Sequence[Op], time_revs: Sequence[bool]) -> List[mw.Op]:
    if len(ops) != len(time_revs):
        raise ValueError(f"operations/time_revs length mismatch: {len(ops)} vs {len(time_revs)}")
    return [
        mw.Op(
            W=tuple(tuple(Fraction(x) for x in row) for row in op.W),
            t=tuple(Fraction(v) for v in op.t),
            tr=bool(tr),
        )
        for op, tr in zip(ops, time_revs)
    ]


def build_spin_ops(
    ops: Sequence[Op],
    time_revs: Sequence[bool],
    spin_matrices: Optional[Sequence[Sequence[Sequence[float]]]] = None,
) -> List[SpinOp]:
    if len(ops) != len(time_revs):
        raise ValueError(f"operations/time_revs length mismatch: {len(ops)} vs {len(time_revs)}")
    if spin_matrices is not None and len(spin_matrices) != len(ops):
        raise ValueError(
            f"operations/spin_matrices length mismatch: {len(ops)} vs {len(spin_matrices)}"
        )
    spin_ops: List[SpinOp] = []
    for idx, (op, tr) in enumerate(zip(ops, time_revs)):
        spin = (
            float_matrix_tuple(spin_matrices[idx])
            if spin_matrices is not None
            else axial_spin_matrix_for_op(op, bool(tr))
        )
        spin_ops.append(SpinOp(W=op.W, t=op.t, tr=bool(tr), spin=spin))
    return spin_ops


def build_reciprocal_spin_data(
    real_ops: Sequence[Op],
    time_revs: Sequence[bool],
    spin_matrices: Optional[Sequence[Sequence[Sequence[float]]]] = None,
) -> Tuple[List[Op], List[mw.Op], List[SpinOp], List[SpinOp]]:
    if len(real_ops) != len(time_revs):
        raise ValueError(f"operations/time_revs length mismatch: {len(real_ops)} vs {len(time_revs)}")
    if spin_matrices is not None and len(spin_matrices) != len(real_ops):
        raise ValueError(
            f"operations/spin_matrices length mismatch: {len(real_ops)} vs {len(spin_matrices)}"
        )

    tr_op = time_reversal_op()
    paired_ops: List[Tuple[Op, mw.Op, SpinOp, SpinOp]] = []
    for idx, (real_op, tr) in enumerate(zip(real_ops, time_revs)):
        rec_op = to_reciprocal_op(real_op)
        k_op = compose(tr_op, rec_op) if tr else rec_op
        spin = (
            float_matrix_tuple(spin_matrices[idx])
            if spin_matrices is not None
            else axial_spin_matrix_for_op(real_op, bool(tr))
        )
        mag_op = mw.Op(
            W=tuple(tuple(Fraction(x) for x in row) for row in real_op.W),
            t=tuple(Fraction(v) for v in real_op.t),
            tr=bool(tr),
        )
        reciprocal_spin_op = SpinOp(W=k_op.W, t=k_op.t, tr=bool(tr), spin=spin)
        symbolic_spin_op = SpinOp(W=real_op.W, t=real_op.t, tr=bool(tr), spin=spin)
        paired_ops.append((k_op, mag_op, reciprocal_spin_op, symbolic_spin_op))

    paired_ops.sort(key=lambda item: op_key(item[0]))
    return (
        [op for op, _, _, _ in paired_ops],
        [op for _, op, _, _ in paired_ops],
        [op for _, _, op, _ in paired_ops],
        [op for _, _, _, op in paired_ops],
    )


def sort_ops_with_time_reversal(ops: Sequence[Op], time_revs: Sequence[bool]) -> Tuple[List[Op], List[bool]]:
    if len(ops) != len(time_revs):
        raise ValueError(f"operations/time_revs length mismatch: {len(ops)} vs {len(time_revs)}")
    pairs = sorted(
        zip(ops, time_revs),
        key=lambda item: (op_key(item[0]), 1 if item[1] else 0),
    )
    return [op for op, _ in pairs], [bool(tr) for _, tr in pairs]


def sort_spin_ops(spin_ops: Sequence[SpinOp]) -> List[SpinOp]:
    return sorted(spin_ops, key=spin_op_key)


def numeric_basis_projector(basis: Sequence[Sequence[float]], tol: float = 1e-8) -> np.ndarray:
    if not basis:
        return np.zeros((3, 3), dtype=float)
    cols = np.column_stack([np.asarray(vec, dtype=float) for vec in basis])
    q, _ = np.linalg.qr(cols)
    dim = cols.shape[1]
    q = q[:, :dim]
    if q.size == 0:
        return np.zeros((3, 3), dtype=float)
    return q @ q.T


def canonicalize_numeric_basis(basis: Sequence[Sequence[float]], tol: float = 1e-8) -> NumericMat:
    if not basis:
        return []
    projector = numeric_basis_projector(basis, tol=tol)
    if np.linalg.norm(projector) <= tol:
        return []
    dim = int(round(float(np.trace(projector))))
    out: List[np.ndarray] = []
    for axis in np.eye(3):
        vec = projector @ axis
        for prev in out:
            vec = vec - np.dot(prev, vec) * prev
        norm = np.linalg.norm(vec)
        if norm <= tol:
            continue
        vec = vec / norm
        lead = int(np.argmax(np.abs(vec)))
        if vec[lead] < 0:
            vec = -vec
        out.append(vec)
        if len(out) == dim:
            break
    if len(out) < dim:
        cols = np.linalg.eigh(projector)[1][:, ::-1]
        for idx in range(cols.shape[1]):
            vec = cols[:, idx]
            for prev in out:
                vec = vec - np.dot(prev, vec) * prev
            norm = np.linalg.norm(vec)
            if norm <= tol:
                continue
            vec = vec / norm
            lead = int(np.argmax(np.abs(vec)))
            if vec[lead] < 0:
                vec = -vec
            out.append(vec)
            if len(out) == dim:
                break
    cleaned = [clean_numeric_vec(vec.tolist(), tol=tol) for vec in out]
    return cleaned[:dim]


def allowed_spin_moment_basis(stab_ops: Sequence[SpinOp], tol: float = 1e-8) -> NumericMat:
    if not stab_ops:
        return canonicalize_numeric_basis(np.eye(3).tolist(), tol=tol)
    constraints = [np.asarray(op.spin, dtype=float) - np.eye(3) for op in stab_ops]
    stacked = np.vstack(constraints)
    _u, s, vh = np.linalg.svd(stacked)
    rank = int(np.sum(s > tol))
    raw_basis = [vh[rank + i, :] for i in range(max(0, vh.shape[0] - rank))]
    return canonicalize_numeric_basis(raw_basis, tol=tol)


def transform_moment_basis(spin_matrix: Sequence[Sequence[float]], basis: NumericMat, tol: float = 1e-8) -> NumericMat:
    if not basis:
        return []
    arr = np.asarray(spin_matrix, dtype=float)
    out = [(arr @ np.asarray(vec, dtype=float)).tolist() for vec in basis]
    return clean_numeric_mat(out, tol=tol)


def spin_fourier_action_matrix(k_point: Vec, reciprocal_op: Op, symbolic_op: SpinOp) -> np.ndarray:
    k_image = mw.mat_vec_fraction(reciprocal_op.W, k_point)
    phase_arg = sum(Fraction(k_image[i]) * Fraction(symbolic_op.t[i]) for i in range(3))
    phase = mw.phase_from_fraction(phase_arg)
    spin = np.asarray(symbolic_op.spin, dtype=np.complex128)
    return phase * spin


def build_spin_fourier_mode_basis(
    k_point: Vec,
    reciprocal_ops: Sequence[Op],
    symbolic_spin_ops: Sequence[SpinOp],
    tol: float = 1e-9,
) -> List[np.ndarray]:
    constraints: List[np.ndarray] = []
    identity = np.eye(6, dtype=float)
    for reciprocal_op, symbolic_op in zip(reciprocal_ops, symbolic_spin_ops):
        action = spin_fourier_action_matrix(k_point, reciprocal_op, symbolic_op)
        real_action = mw.realify_fourier_action_matrix(action, symbolic_op.tr)
        constraints.append(real_action - identity)
    constraint_matrix = np.vstack(constraints) if constraints else np.zeros((0, 6), dtype=float)
    real_basis = mw.canonical_real_nullspace_basis(constraint_matrix, 6, tol=tol)
    return mw.real_basis_to_complex_columns(real_basis, tol=tol)


def spin_fourier_basis_transform(
    basis_columns: Sequence[np.ndarray],
    k_point: Vec,
    reciprocal_op: Op,
    symbolic_op: SpinOp,
) -> List[np.ndarray]:
    if not basis_columns:
        return []
    action = spin_fourier_action_matrix(k_point, reciprocal_op, symbolic_op)
    transformed: List[np.ndarray] = []
    for column in basis_columns:
        vec = np.conjugate(column) if symbolic_op.tr else column
        transformed.append(action @ vec)
    return transformed


def format_numeric_value(value: float, *, tol: float = 1e-8, max_den: int = 12) -> str:
    value = clean_numeric(value, tol=tol)
    frac_val = Fraction(value).limit_denominator(max_den)
    if abs(float(frac_val) - value) <= tol:
        return frac_str(frac_val, max_den=max_den)
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text


def moment_param_names_for_numeric_basis(basis: NumericMat, tol: float = 1e-8) -> List[str]:
    axis_names = ["mx", "my", "mz"]
    used_axes = set()
    names: List[str] = []
    for idx, vec in enumerate(basis):
        nz = [i for i, v in enumerate(vec) if abs(v) > tol]
        if (
            len(nz) == 1
            and abs(abs(vec[nz[0]]) - 1.0) <= tol
            and nz[0] not in used_axes
        ):
            names.append(axis_names[nz[0]])
            used_axes.add(nz[0])
        else:
            names.append(f"m{idx + 1}")
    return names


def format_linear_combo(coeffs: Sequence[float], params: Sequence[str], tol: float = 1e-8) -> str:
    pieces: List[str] = []
    for coeff, param in zip(coeffs, params):
        coeff = clean_numeric(coeff, tol=tol)
        if abs(coeff) <= tol:
            continue
        if abs(coeff - 1.0) <= tol:
            term = param
        elif abs(coeff + 1.0) <= tol:
            term = f"-{param}"
        else:
            mag = format_numeric_value(abs(coeff), tol=tol)
            term = f"{mag}{param}"
            if coeff < 0:
                term = f"-{term}"
        pieces.append(term)
    if not pieces:
        return "0"
    out = pieces[0]
    for piece in pieces[1:]:
        if piece.startswith("-"):
            out += f" - {piece[1:]}"
        else:
            out += f" + {piece}"
    return out


def moment_basis_to_string(
    basis: NumericMat,
    param_names: Optional[Sequence[str]] = None,
    tol: float = 1e-8,
) -> str:
    if not basis:
        return "0, 0, 0"
    params = list(param_names) if param_names is not None else moment_param_names_for_numeric_basis(basis, tol=tol)
    components = []
    for coord in range(3):
        coeffs = [vec[coord] for vec in basis]
        components.append(format_linear_combo(coeffs, params, tol=tol))
    return ", ".join(components)


def _axis_direction_label(vec: np.ndarray, tol: float = 1e-6) -> Tuple[Optional[str], Optional[Tuple[int, int, int]]]:
    norm = np.linalg.norm(vec)
    if norm <= tol:
        return None, None
    arr = np.asarray(vec, dtype=float) / norm
    lead = int(np.argmax(np.abs(arr)))
    if arr[lead] < 0:
        arr = -arr
    axis_basis = np.eye(3)
    axis_names = ["x", "y", "z"]
    for idx, basis_vec in enumerate(axis_basis):
        if np.allclose(arr, basis_vec, atol=tol):
            direction = [0, 0, 0]
            direction[idx] = 1
            return axis_names[idx], tuple(direction)  # type: ignore[return-value]
    scaled = arr / max(abs(v) for v in arr if abs(v) > tol)
    rounded = np.rint(scaled).astype(int)
    if np.allclose(scaled, rounded, atol=0.08):
        nonzero = [abs(int(v)) for v in rounded if int(v) != 0]
        gcd = math.gcd(*nonzero) if nonzero else 1
        if gcd:
            rounded = (rounded // gcd).astype(int)
        parts = []
        for value in rounded.tolist():
            if value == 0:
                parts.append("0")
            elif value == 1:
                parts.append("1")
            elif value == -1:
                parts.append("-1")
            else:
                parts.append(str(int(value)))
        return "".join(parts), tuple(int(v) for v in rounded.tolist())
    label = "(" + ", ".join(format_numeric_value(v, tol=tol) for v in arr.tolist()) + ")"
    return label, None


def spin_symmetry_element(op: SpinOp, tol: float = 1e-6) -> Optional[dict]:
    spin = np.asarray(op.spin, dtype=float)
    eye = np.eye(3)
    if np.allclose(spin, eye, atol=tol):
        token = "1'" if op.tr else "1"
        return {
            "token": token,
            "type": "1",
            "kind": "identity",
            "axis": None,
            "axis_direction": None,
            "time_reversal": bool(op.tr),
            "spin_matrix": clean_numeric_mat(spin.tolist(), tol=tol),
        }
    if np.allclose(spin, -eye, atol=tol):
        token = "-1'" if op.tr else "-1"
        return {
            "token": token,
            "type": "-1",
            "kind": "inversion",
            "axis": None,
            "axis_direction": None,
            "time_reversal": bool(op.tr),
            "spin_matrix": clean_numeric_mat(spin.tolist(), tol=tol),
        }

    det = float(np.linalg.det(spin))
    trace = float(np.trace(spin))

    if det > 0:
        cos_theta = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
        theta = math.acos(cos_theta)
        order = None
        for candidate, target in ((2, math.pi), (3, 2.0 * math.pi / 3.0), (4, math.pi / 2.0), (6, math.pi / 3.0)):
            if abs(theta - target) <= 1e-5:
                order = candidate
                break
        eigvals, eigvecs = np.linalg.eig(spin)
        axis = None
        for idx, eigval in enumerate(eigvals):
            if abs(eigval.real - 1.0) <= 1e-5 and abs(eigval.imag) <= 1e-5:
                axis = np.real(eigvecs[:, idx])
                break
        axis_label, axis_dir = _axis_direction_label(axis if axis is not None else np.zeros(3), tol=tol)
        if order is not None and axis_label is not None:
            token = f"{order}'[{axis_label}]" if op.tr else f"{order}[{axis_label}]"
            return {
                "token": token,
                "type": str(order),
                "kind": "rotation",
                "axis": axis_label,
                "axis_direction": axis_dir,
                "time_reversal": bool(op.tr),
                "spin_matrix": clean_numeric_mat(spin.tolist(), tol=tol),
            }
    else:
        eigvals, eigvecs = np.linalg.eig(spin)
        minus_axis = None
        plus_axes = 0
        for idx, eigval in enumerate(eigvals):
            if abs(eigval.imag) > 1e-5:
                continue
            if abs(eigval.real + 1.0) <= 1e-5 and minus_axis is None:
                minus_axis = np.real(eigvecs[:, idx])
            elif abs(eigval.real - 1.0) <= 1e-5:
                plus_axes += 1
        if plus_axes >= 2 and minus_axis is not None:
            axis_label, axis_dir = _axis_direction_label(minus_axis, tol=tol)
            if axis_label is not None:
                token = f"m'[{axis_label}]" if op.tr else f"m[{axis_label}]"
                return {
                    "token": token,
                    "type": "m",
                    "kind": "mirror",
                    "axis": axis_label,
                    "axis_direction": axis_dir,
                    "time_reversal": bool(op.tr),
                    "spin_matrix": clean_numeric_mat(spin.tolist(), tol=tol),
                }

    return {
        "token": "op'" if op.tr else "op",
        "type": "op",
        "kind": "matrix",
        "axis": None,
        "axis_direction": None,
        "time_reversal": bool(op.tr),
        "spin_matrix": clean_numeric_mat(spin.tolist(), tol=tol),
    }


def build_spin_site_symmetry(stab_ops: Sequence[SpinOp]) -> Tuple[Optional[str], List[dict]]:
    elems: List[dict] = []
    seen = set()
    for op in stab_ops:
        elem = spin_symmetry_element(op)
        if elem is None:
            continue
        key = (elem["token"], tuple(tuple(row) for row in elem["spin_matrix"]))
        if key in seen:
            continue
        seen.add(key)
        elems.append(elem)

    if not elems:
        return None, []

    nontrivial = [
        elem
        for elem in elems
        if not (elem["kind"] == "identity" and not elem["time_reversal"])
    ]
    elems_out = nontrivial or elems
    order = {"1": 0, "-1": 1, "m": 2, "2": 3, "3": 4, "4": 5, "6": 6, "op": 7}
    elems_out.sort(
        key=lambda elem: (
            order.get(str(elem.get("type")), 99),
            1 if elem.get("time_reversal") else 0,
            elem.get("axis") or "",
            elem.get("token") or "",
        )
    )
    return " * ".join(elem["token"] for elem in elems_out), elems_out


def dedup_coord_score(coords: Sequence[Fraction]) -> Tuple[int, int, Fraction, Fraction, int, Tuple[int, int, int], Tuple[Fraction, Fraction, Fraction]]:
    mod = mod1_vec(coords)
    nonzero = sum(1 for c in mod if c != 0)
    first_idx = next((i for i, c in enumerate(mod) if c != 0), 3)
    dist0_sum = sum(min(c, 1 - c) for c in mod)
    dist_half_sum = sum(abs(c - Fraction(1, 2)) for c in mod)
    den_sum = sum(c.denominator for c in mod)
    tup = tuple(mod + [Fraction(0)] * (3 - len(mod)))
    gt_half_flags = tuple(1 if val > Fraction(1, 2) else 0 for val in mod)
    return (nonzero, first_idx, dist0_sum, dist_half_sum, den_sum, gt_half_flags, tup)


def basis_score(basis: Mat) -> Tuple[Tuple[int, int, int, int, Tuple[int, int, int]], ...]:
    prims = [primitive_int_vec(b) for b in basis]
    scored = []
    for v in prims:
        max_abs = max(abs(x) for x in v) if v else 0
        sum_abs = sum(abs(x) for x in v)
        first_idx = next((i for i, x in enumerate(v) if x != 0), 3)
        neg_count = sum(1 for x in v if x < 0)
        scored.append((max_abs, sum_abs, first_idx, neg_count, v))
    return tuple(sorted(scored))


def normalize_coord_string(coord: str) -> str:
    coord = coord.strip()
    if coord.startswith("(") and coord.endswith(")"):
        coord = coord[1:-1]
    coord = coord.replace(" ", "")

    def normalize_component(comp: str) -> str:
        tokens = re.findall(r"[+-]?[^+-]+", comp)
        const = Fraction(0)
        coeffs: Dict[str, Fraction] = {}
        for tok in tokens:
            if not tok:
                continue
            sign = 1
            if tok[0] == "+":
                tok = tok[1:]
            elif tok[0] == "-":
                sign = -1
                tok = tok[1:]
            if not tok:
                continue
            if any(ch.isalpha() for ch in tok):
                m = re.match(r"([0-9./]*)?([A-Za-z]+)", tok)
                if m:
                    coeff_str, var = m.groups()
                    coeff = Fraction(coeff_str) if coeff_str else Fraction(1)
                    coeffs[var] = coeffs.get(var, Fraction(0)) + sign * coeff
                else:
                    coeffs[tok] = coeffs.get(tok, Fraction(0)) + sign
            else:
                try:
                    const += sign * Fraction(tok)
                except Exception:
                    return comp
        const = mod1(const)
        expr = (const, {k: v for k, v in coeffs.items() if v != 0})
        return expr_to_str(expr).replace(" ", "")

    parts = coord.split(",")
    if len(parts) == 3:
        new_parts = []
        for part in parts:
            if part:
                try:
                    new_parts.append(normalize_component(part))
                    continue
                except Exception:
                    pass
            new_parts.append(part)
        coord = ",".join(new_parts)
    elif coord and not any(ch.isalpha() for ch in coord):
        try:
            coord_val = mod1(Fraction(coord))
            coord = frac_str(coord_val)
        except Exception:
            pass
    return coord


def intrinsic_order_key(entry: dict) -> Tuple:
    x0 = entry.get("x0", [Fraction(0), Fraction(0), Fraction(0)])
    x0_sig = dedup_coord_score(x0)
    norm_orbit = tuple(sorted(normalize_coord_string(c) for c in entry.get("orbit", [])))
    basis_sig = basis_score(entry.get("basis_vecs", []))
    return (
        -x0_sig[0],
        x0_sig[1:],
        norm_orbit,
        basis_sig,
    )


def coord_score_for_entry(entry: dict) -> Tuple:
    coords = entry.get("x0", [Fraction(0), Fraction(0), Fraction(0)])
    system = (entry.get("system", "") or "").strip().lower()
    axis_order_map = {
        "triclinic": (0, 1, 2),
        "monoclinic": (1, 0, 2),
        "orthorhombic": (0, 1, 2),
    }
    axis_order = axis_order_map.get(system, (2, 1, 0))
    mod = mod1_vec(coords)
    nonzero = sum(1 for c in mod if c != 0)
    dist_sum = sum(min(c, 1 - c) for c in mod)
    den_sum = sum(c.denominator for c in mod)
    tup = tuple(mod + [Fraction(0)] * (3 - len(mod)))
    ordered = tuple(tup[i] for i in axis_order)
    gt_half_flags = tuple(1 if c > Fraction(1, 2) else 0 for c in ordered)
    lex_pref = tuple(tup[i] for i in axis_order) if nonzero >= 2 else tuple(-c for c in ordered)
    return (-nonzero, dist_sum, den_sum, tuple(-f for f in gt_half_flags), lex_pref)


def sort_for_ita_letters(wps: List[dict], number: Optional[int] = None) -> List[dict]:
    def sort_key(e):
        return (
            -e["mult"],
            -e.get("dim", 0),
            coord_score_for_entry(e),
            e.get("orbit_coord_score", (99, 99, Fraction(0), (Fraction(9), Fraction(9), Fraction(9)))),
            intrinsic_order_key(e),
        )

    ordered = sorted(wps, key=sort_key)
    letters = string.ascii_lowercase + string.ascii_uppercase
    for idx, wp in enumerate(reversed(ordered)):
        wp["letter"] = letters[idx] if idx < len(letters) else f"pos{idx}"
    return ordered


def origin_score(wps: List[dict]) -> Tuple:
    ordered = sorted(
        wps,
        key=lambda e: (
            -e["mult"],
            -e.get("dim", 0),
            dedup_coord_score(e.get("x0", [Fraction(0), Fraction(0), Fraction(0)])),
            intrinsic_order_key(e),
        ),
    )
    return tuple(
        (
            -e["mult"],
            -e.get("dim", 0),
            dedup_coord_score(e.get("x0", [Fraction(0), Fraction(0), Fraction(0)])),
            intrinsic_order_key(e),
        )
        for e in ordered
    )


def centering_vectors_from_symbol(symbol: str) -> List[Tuple[Fraction, Fraction, Fraction]]:
    centering_map = {
        "P": [(0, 0, 0)],
        "I": [(0, 0, 0), (Fraction(1, 2), Fraction(1, 2), Fraction(1, 2))],
        "F": [
            (0, 0, 0),
            (Fraction(0, 1), Fraction(1, 2), Fraction(1, 2)),
            (Fraction(1, 2), Fraction(0, 1), Fraction(1, 2)),
            (Fraction(1, 2), Fraction(1, 2), Fraction(0, 1)),
        ],
        "C": [(0, 0, 0), (Fraction(1, 2), Fraction(1, 2), Fraction(0, 1))],
        "A": [(0, 0, 0), (Fraction(0, 1), Fraction(1, 2), Fraction(1, 2))],
        "B": [(0, 0, 0), (Fraction(1, 2), Fraction(0, 1), Fraction(1, 2))],
        "R": [
            (0, 0, 0),
            (Fraction(2, 3), Fraction(1, 3), Fraction(1, 3)),
            (Fraction(1, 3), Fraction(2, 3), Fraction(2, 3)),
        ],
    }
    return [
        tuple(Fraction(x) for x in vec)
        for vec in centering_map.get(symbol.upper(), [(0, 0, 0)])
    ]


def generic_point_on_subspace(x0: Vec, basis: List[Vec]) -> Vec:
    primes = [5, 7, 11, 13, 17, 19, 23, 29, 31]
    u = [Fraction(1, primes[i % len(primes)]) for i in range(len(basis))]
    x: Vec = [x0[0], x0[1], x0[2]]
    for i, b in enumerate(basis):
        for j in range(3):
            x[j] += u[i] * b[j]
    return [mod1(x[0]), mod1(x[1]), mod1(x[2])]


def derive_wyckoff(
    data: dict,
    origin_shift: Tuple[Fraction, Fraction, Fraction] = (Fraction(0), Fraction(0), Fraction(0)),
    reciprocal: bool = False,
    fast: bool = True,
) -> Tuple[List[dict], List[Tuple[Fraction, Fraction, Fraction]], Tuple[Fraction, Fraction, Fraction]]:
    """
    reciprocal=False: Wyckoff positions in real space.
    reciprocal=True : k-space special points/lines/planes (Wyckoff analogue).

    fast=True: skip expensive "best rep within orbit" scans.
    """
    global RECIPROCAL_MODE
    RECIPROCAL_MODE = reciprocal

    centering_symbol = (data.get("centering_symbol") or "P")[0].upper()
    primitive_direct = primitive_matrix_from_centering(centering_symbol)

    centering_full = centering_vectors_from_symbol(centering_symbol)
    centering_vectors = [(Fraction(0), Fraction(0), Fraction(0))] if reciprocal else centering_full
    op_builder = to_reciprocal_op if reciprocal else (lambda o: o)

    full_ops_raw = [op_from_json(op) for op in data["operations"]]
    base_ops_raw = [op_builder(op) for op in full_ops_raw]
    time_revs_raw = data.get("time_revs", [False] * len(base_ops_raw))
    spin_matrices_raw = data.get("spin_matrices")
    if not isinstance(time_revs_raw, list):
        raise TypeError(f"time_revs must be a list, got {type(time_revs_raw)}")
    if len(time_revs_raw) != len(base_ops_raw):
        raise ValueError(
            f"time_revs length {len(time_revs_raw)} does not match operations length {len(base_ops_raw)}"
        )
    print(f"[progress] base ops: {len(base_ops_raw)}", file=sys.stderr)

    if reciprocal:
        ops, mag_ops_real, spin_ops_real, spin_ops_symbolic = build_reciprocal_spin_data(
            full_ops_raw,
            time_revs_raw,
            spin_matrices_raw,
        )
        print(f"[progress] k-space time_revs applied: {len(ops)}", file=sys.stderr)
    else:
        geom_ops = dedup_ops(base_ops_raw)
        mag_ops_real = build_magnetic_ops(base_ops_raw, time_revs_raw)
        spin_ops_real = build_spin_ops(base_ops_raw, time_revs_raw, spin_matrices_raw)
        if origin_shift != (Fraction(0), Fraction(0), Fraction(0)):
            geom_ops = [shift_op(op, origin_shift) for op in geom_ops]
            mag_ops_real = [mw.shift_op(op, origin_shift) for op in mag_ops_real]
            spin_ops_real = [shift_spin_op(op, origin_shift) for op in spin_ops_real]
        ops = sorted(geom_ops, key=op_key)
        mag_ops_real = sorted(
            mag_ops_real,
            key=lambda op: (
                tuple(x for row in op.W for x in row),
                tuple(mod1(v) for v in op.t),
                1 if op.tr else 0,
            ),
        )
        spin_ops_real = sort_spin_ops(spin_ops_real)
        spin_ops_symbolic = list(spin_ops_real)
    print(f"[progress] expanded ops: {len(ops)}", file=sys.stderr)
    try:
        pg_lookup = mw.build_point_group_signature_lookup()
    except FileNotFoundError:
        # The lookup only improves standardized point-group labels.
        # Enumeration can continue without bundled space-group JSON files.
        pg_lookup = {}
        print(
            "[warning] space_groups_json not found; site-symmetry labels may be less specific",
            file=sys.stderr,
        )

    group_order = len(ops)
    rotations = unique_rotations(ops)
    pg_rotation_count = len(rotations) if reciprocal else None

    ops_mult_table, ops_identity_idx, ops_inverses = build_multiplication_table(ops)
    ops_signature = _ops_signature(ops)
    op_rot_idx: List[int] = []
    op_trans: List[Tuple[Fraction, Fraction, Fraction]] = []
    rot_key_to_idx_full: Dict[Tuple[Fraction, ...], int] = {}
    for idx, rot in enumerate(rotations):
        rot_key_to_idx_full[tuple(x for row in rot for x in row)] = idx
    for op in ops:
        rot_key = tuple(x for row in op.W for x in row)
        op_rot_idx.append(rot_key_to_idx_full[rot_key])
        op_trans.append(tuple(mod1(v) for v in op.t))

    rot_ops = [Op(tuple(tuple(v for v in row) for row in rot), (Fraction(0), Fraction(0), Fraction(0))) for rot in rotations]
    rot_key_to_idx: Dict[Tuple[Fraction, ...], int] = {rotation_key(op): i for i, op in enumerate(rot_ops)}
    rot_mult_table, rot_identity_idx_full, rot_inverses = build_multiplication_table(rot_ops)

    identity_rot_key = tuple(x for row in identity_mat() for x in row)
    identity_rot_idx = rot_key_to_idx.get(identity_rot_key)

    rot_translation_options: Dict[int, List[Tuple[Fraction, Fraction, Fraction]]] = {}
    rot_trans_to_op_idx: Dict[Tuple[int, Tuple[Fraction, Fraction, Fraction]], int] = {}
    identity_op_idx = None
    for idx, op in enumerate(ops):
        rkey = rotation_key(op)
        ridx = rot_key_to_idx[rkey]
        t_mod = tuple(mod1(v) for v in op.t)
        if ridx == identity_rot_idx:
            if all(val == 0 for val in t_mod):
                identity_op_idx = idx
            else:
                continue
        rot_translation_options.setdefault(ridx, [])
        if t_mod not in rot_translation_options[ridx]:
            rot_translation_options[ridx].append(t_mod)
        rot_trans_to_op_idx.setdefault((ridx, t_mod), idx)

    if identity_rot_idx is not None and (identity_rot_idx, (Fraction(0), Fraction(0), Fraction(0))) not in rot_trans_to_op_idx:
        raise ValueError("Identity operation with zero translation not found.")
    if identity_op_idx is None and identity_rot_idx is not None:
        identity_op_idx = rot_trans_to_op_idx[(identity_rot_idx, (Fraction(0), Fraction(0), Fraction(0)))]

    subgroup_reps = rotation_subgroup_reps_from_point_group(rotations)

    fix_cache: Dict[Tuple[Tuple[int, ...], Tuple, bool], List[Tuple[Vec, Mat]]] = {}

    def fixed_subspaces_cached(subgroup: FrozenSet[int]) -> List[Tuple[Vec, Mat]]:
        key = (tuple(sorted(subgroup)), ops_signature, RECIPROCAL_MODE)
        if key not in fix_cache:
            fix_cache[key] = fixed_subspaces_for_subgroup(subgroup, ops)
        return fix_cache[key]

    unique_subspaces: List[Tuple[Vec, Mat, List[int]]] = []
    seen_subspace_keys: set = set()
    for rot_subgroup in subgroup_reps:
        translation_choices = solve_translations_for_rotation_subgroup(
            rot_subgroup,
            rotations,
            rot_mult_table,
            rot_translation_options,
            identity_rot_idx,
        )
        for assignment in translation_choices:
            if identity_rot_idx is not None:
                assignment[identity_rot_idx] = (Fraction(0), Fraction(0), Fraction(0))
            subgroup = subgroup_from_translation_choice(
                assignment,
                rot_trans_to_op_idx,
                ops_mult_table,
                op_rot_idx,
                op_trans,
                identity_op_idx if identity_op_idx is not None else ops_identity_idx,
            )
            if subgroup is None:
                continue
            fix_solutions = fixed_subspaces_cached(subgroup)
            for x0, basis in fix_solutions:
                closed_list = closure_under_stabilizer(x0, basis, ops)
                for closed_x0, closed_basis in closed_list:
                    key = subspace_orbit_key(closed_x0, closed_basis, ops)
                    if key in seen_subspace_keys:
                        continue
                    seen_subspace_keys.add(key)
                    unique_subspaces.append((closed_x0, closed_basis, []))

    wyckoff: List[dict] = []
    for x0, basis, _ in unique_subspaces:
        if fast:
            rep_x0, rep_basis = x0, basis
        else:
            orbit_keys = []
            orbit_reps = []
            for op in ops:
                x1 = mod1_vec(op.apply(x0))
                b1 = apply_op_basis(op, basis)
                orbit_reps.append((x1, b1))
                orbit_keys.append(canonical_subspace_key(x1, b1))
            min_idx = min(
                range(len(orbit_reps)),
                key=lambda i: (
                    basis_score(orbit_reps[i][1]),
                    dedup_coord_score(orbit_reps[i][0]),
                    orbit_keys[i],
                ),
            )
            rep_x0, rep_basis = orbit_reps[min_idx]
        rep_x0 = [Fraction(v) for v in rep_x0]
        rep_basis = [[Fraction(x) for x in row] for row in rep_basis]
        rep_basis = canonicalize_axis_aligned_basis(rep_basis)
        rep_basis = scale_basis_to_primitive(rep_basis)
        site_symmetry = None
        unitary_site_symmetry = None
        site_symmetry_custom = None
        site_symmetry_ops: List[dict] = []
        spatial_site_symmetry_custom = None
        spatial_site_symmetry_ops: List[dict] = []
        moment_basis: List = []
        rep_moment_basis: NumericMat = []
        moment_param_names: List[str] = []
        moment_constraints = None
        spin_stab_ops: List[SpinOp] = []
        spin_stab_ops_symbolic: List[SpinOp] = []
        rep_fourier_basis_columns: List[np.ndarray] = []
        moment_dim = 0
        has_magnetic_moment = False

        if reciprocal:
            if len(rep_basis) == 0:
                gen_pt = rep_x0
            else:
                gen_pt = generic_point_on_subspace(rep_x0, rep_basis)
            gen_stab_indices = stabilizer(gen_pt, ops)
            gen_stab_ops = [ops[i] for i in gen_stab_indices]
            little_size = len(unique_rotations(gen_stab_ops))
            pg_order = pg_rotation_count if pg_rotation_count is not None else len(unique_rotations(ops))
            arms = pg_order // max(1, little_size)
            mult = arms * len(centering_full)
            stab_ops = gen_stab_ops
            mag_stab_ops = [mag_ops_real[i] for i in gen_stab_indices]
            spin_stab_ops = [spin_ops_real[i] for i in gen_stab_indices]
            spin_stab_ops_symbolic = [spin_ops_symbolic[i] for i in gen_stab_indices]
            unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]
            unitary_site_symmetry = mw.classify_site_symmetry(unique_rotations(unitary_mag_stab_ops), pg_lookup or {})
            spatial_site_symmetry_custom, spatial_site_symmetry_ops = mw.build_custom_site_symmetry(mag_stab_ops)
            site_symmetry_custom, site_symmetry_ops = build_spin_site_symmetry(spin_stab_ops_symbolic)
            if site_symmetry_custom is None:
                site_symmetry_custom = spatial_site_symmetry_custom
                site_symmetry_ops = spatial_site_symmetry_ops
            site_symmetry = (
                mw.lookup_magnetic_bilbao_symbol(
                    spatial_site_symmetry_custom or site_symmetry_custom or "",
                    unitary_site_symmetry or "",
                    spatial_site_symmetry_ops or site_symmetry_ops,
                )
                or
                mw.bilbao_magnetic_point_group_symbol(
                    spatial_site_symmetry_ops or site_symmetry_ops,
                    crystal_system=str(data.get("crystal_system", "")),
                )
                or spatial_site_symmetry_custom
                or site_symmetry_custom
                or unitary_site_symmetry
            )
            rep_fourier_basis_columns = build_spin_fourier_mode_basis(
                gen_pt,
                gen_stab_ops,
                spin_stab_ops_symbolic,
            )
            moment_basis, moment_constraints = mw.wyckoff_like_display_from_complex_basis(
                rep_fourier_basis_columns,
                axis_letters=["mx", "my", "mz"],
            )
            moment_dim = len(moment_basis)
            has_magnetic_moment = bool(moment_basis)
        else:
            stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, ops)
            stab_ops = [ops[i] for i in stab_indices]
            mult = group_order // max(1, len(stab_ops))
            mag_stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, mag_ops_real)
            mag_stab_ops = [mag_ops_real[i] for i in mag_stab_indices]
            spin_stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, spin_ops_real)
            spin_stab_ops = [spin_ops_real[i] for i in spin_stab_indices]
            unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]
            unitary_site_symmetry = mw.classify_site_symmetry(unique_rotations(unitary_mag_stab_ops), pg_lookup or {})
            spatial_site_symmetry_custom, spatial_site_symmetry_ops = mw.build_custom_site_symmetry(mag_stab_ops)
            site_symmetry_custom, site_symmetry_ops = build_spin_site_symmetry(spin_stab_ops)
            if site_symmetry_custom is None:
                site_symmetry_custom = spatial_site_symmetry_custom
                site_symmetry_ops = spatial_site_symmetry_ops
            site_symmetry = (
                mw.lookup_magnetic_bilbao_symbol(
                    spatial_site_symmetry_custom or site_symmetry_custom or "",
                    unitary_site_symmetry or "",
                    spatial_site_symmetry_ops or site_symmetry_ops,
                )
                or
                mw.bilbao_magnetic_point_group_symbol(
                    spatial_site_symmetry_ops or site_symmetry_ops,
                    crystal_system=str(data.get("crystal_system", "")),
                )
                or spatial_site_symmetry_custom
                or site_symmetry_custom
                or unitary_site_symmetry
            )
            rep_moment_basis = allowed_spin_moment_basis(spin_stab_ops)
            moment_param_names = moment_param_names_for_numeric_basis(rep_moment_basis)
            moment_basis = [", ".join(format_numeric_value(v) for v in vec) for vec in rep_moment_basis]
            moment_constraints = moment_basis_to_string(rep_moment_basis, moment_param_names)
            moment_dim = len(rep_moment_basis)
            has_magnetic_moment = bool(rep_moment_basis)
        ns, c_vals = canonical_subspace_key(rep_x0, rep_basis)

        A_cons = [list(row) for row in ns]
        disp_x0, _ = solve_affine(A_cons, list(c_vals))
        disp_x0 = mod1_vec(disp_x0)

        axis_letters = ["u", "v", "w"] if reciprocal else None
        rep_vec = build_symbolic_rep(disp_x0, rep_basis, axis_letters=axis_letters)
        rep_vec_display = [normalize_expr(e) for e in rep_vec]
        ops_for_expr = spin_ops_real if spin_ops_real else ops
        if len(rep_basis) == 1:
            bvec = rep_basis[0]
            nz_idx = [i for i, v in enumerate(bvec) if v != 0]
            if (
                len(nz_idx) == 2
                and bvec[2] == 0
                and abs(bvec[nz_idx[0]]) == abs(bvec[nz_idx[1]])
                and bvec[nz_idx[0]] != bvec[nz_idx[1]]
            ):
                mag = abs(bvec[nz_idx[0]])
                if mag != 0:
                    scale = Fraction(1, 1) / mag
                    if bvec[nz_idx[0]] < 0:
                        scale = -scale
                    param_name = None
                    for expr in rep_vec:
                        if expr[1]:
                            param_name = next(iter(expr[1]))
                            break
                    if param_name:
                        rep_vec = reparam_expr_vec(rep_vec, param_name, scale=scale, shift=Fraction(0))
                        rep_basis = [[v * scale for v in bvec]]
            if bvec[2] == 0 and bvec[0] == bvec[1] and bvec[0] != 0:
                param_name = next(iter(rep_vec[0][1].keys()), None)
                if param_name and len(rep_vec) >= 3 and rep_vec[2][0] == Fraction(1, 2):
                    rep_vec = reparam_expr_vec(rep_vec, param_name, scale=Fraction(-1, 1), shift=Fraction(1, 2))
                    rep_basis = [[-bvec[0], -bvec[1], -bvec[2]]]
            if reciprocal and bvec[2] == 0 and bvec[0] == bvec[1] and bvec[0] != 0:
                param_name = next(iter(rep_vec[0][1].keys()), None)
                consts = [expr[0] for expr in rep_vec]
                if param_name and consts[0] == consts[1] == Fraction(1, 2):
                    scale = Fraction(-1, bvec[0])
                    shift = Fraction(1, 2)
                    rep_vec = reparam_expr_vec(rep_vec, param_name, scale=scale, shift=shift)
                    rep_basis = [[Fraction(1), Fraction(1), Fraction(0)]]
        rep_vec_display = [normalize_expr(e) for e in rep_vec]
        orbit_expr_pairs = []
        orbit_moment_map: Dict[Tuple, str] = {}
        orbit_with_moments_map: Dict[Tuple, str] = {}
        arms_prim: List[str] = []
        seen_sig = set()
        orbit_min_score = None
        dedup_centers = [(Fraction(0), Fraction(0), Fraction(0))]
        for idx, op in enumerate(ops_for_expr):
            vec = apply_op_expr(op, rep_vec)
            vec_norm = [normalize_expr(e) for e in vec]
            sig, _ = expr_vec_signature(
                vec_norm,
                dedup_centers,
                origin_shifts=[(Fraction(0), Fraction(0), Fraction(0))],
            )
            # Fold constants modulo 1 so equivalent forms (e.g., u+1, u+3) are normalized.
            adjusted = [normalize_expr(e) for e in vec]

            if reciprocal:
                prim_str = vector_expr_str(adjusted)
                arms_prim.append(prim_str)
                symbolic_spin_op = spin_ops_symbolic[idx]
                transformed_basis = spin_fourier_basis_transform(
                    rep_fourier_basis_columns,
                    gen_pt,
                    ops[idx],
                    symbolic_spin_op,
                )
                _, moment_str = mw.wyckoff_like_display_from_complex_basis(
                    transformed_basis,
                    axis_letters=["mx", "my", "mz"],
                )
                coord_with_moment = format_coordinate_with_moment(prim_str, moment_str)
                if sig in seen_sig:
                    continue
                seen_sig.add(sig)
                orbit_expr_pairs.append((sig, prim_str))
                orbit_moment_map[sig] = moment_str
                orbit_with_moments_map[sig] = coord_with_moment
            else:
                prim_str = vector_expr_str(adjusted)
                arms_prim.append(prim_str)
                moment_str = moment_basis_to_string(
                    transform_moment_basis(op.spin, rep_moment_basis),
                    moment_param_names,
                )
                coord_with_moment = format_coordinate_with_moment(prim_str, moment_str)
                if sig in seen_sig:
                    continue
                seen_sig.add(sig)
                orbit_expr_pairs.append((sig, prim_str))
                orbit_moment_map[sig] = moment_str
                orbit_with_moments_map[sig] = coord_with_moment

            score = dedup_coord_score([expr[0] for expr in vec_norm])
            if orbit_min_score is None or score < orbit_min_score:
                orbit_min_score = score
        sort_small_diag = (
            mult <= 4
            and len(rep_basis) == 1
            and rep_basis[0][2] == 0
            and rep_basis[0][0] == rep_basis[0][1] != 0
            and len(rep_vec) >= 3
            and rep_vec[2][0] == Fraction(1, 2)
        )
        if sort_small_diag:
            def coeff_order_key(coeff_sig):
                key_parts = []
                for coord in coeff_sig:
                    coord_key = []
                    for name, val in coord:
                        coord_key.append((name, abs(val), -val))
                    key_parts.append(tuple(coord_key))
                return tuple(key_parts)

            orbit_expr_pairs.sort(key=lambda p: (p[0][0], p[0][1], coeff_order_key(p[0][2])))
        orbit_expr = [prim for _, prim in orbit_expr_pairs]
        orbit_moments = [orbit_moment_map[sig] for sig, _ in orbit_expr_pairs]
        orbit_with_moments = [orbit_with_moments_map[sig] for sig, _ in orbit_expr_pairs]

        _, best_consts = expr_vec_signature(
            rep_vec,
            dedup_centers,
            origin_shifts=[(Fraction(0), Fraction(0), Fraction(0))],
        )
        arms_out = ordered_unique(arms_prim)
        representative_coordinate = vector_expr_str(rep_vec_display)
        representative_moment = (
            moment_constraints
            if reciprocal
            else moment_basis_to_string(rep_moment_basis, moment_param_names)
        )
        representative_with_moment = format_coordinate_with_moment(
            representative_coordinate,
            representative_moment,
        )

        wyckoff.append(
            {
                "mult": mult,
                "stab": len(stab_ops),
                "stab_rotations": unique_rotations(stab_ops),
                "dim": len(rep_basis),
                "ns": ns,
                "c": c_vals,
                "rep": rep_vec,
                "orbit": orbit_expr,
                "orbit_conv": orbit_expr[:],
                "orbit_moments": orbit_moments,
                "orbit_with_moments": orbit_with_moments,
                "orbit_conv_with_moments": orbit_with_moments[:],
                "arms": arms_out,
                "arms_conv": arms_out[:],
                "x0": list(best_consts),
                "basis_vecs": rep_basis,
                "orbit_coord_score": orbit_min_score,
                "system": data.get("crystal_system", ""),
                "site_symmetry": site_symmetry,
                "unitary_site_symmetry": unitary_site_symmetry,
                "site_symmetry_custom": site_symmetry_custom,
                "site_symmetry_ops": site_symmetry_ops,
                "spatial_site_symmetry_custom": spatial_site_symmetry_custom,
                "spatial_site_symmetry_ops": spatial_site_symmetry_ops,
                "moment_basis": moment_basis,
                "moment_dim": moment_dim,
                "moment_constraints": moment_constraints,
                "has_magnetic_moment": has_magnetic_moment,
                "representative_coordinate": representative_coordinate,
                "representative_moment": representative_moment,
                "representative_with_moment": representative_with_moment,
            }
        )

    wyckoff = sort_for_ita_letters(wyckoff, number=data.get("number"))
    
    return wyckoff, centering_vectors, origin_shift


def select_best_origin(
    data: dict,
    origin_candidates: List[Tuple[Fraction, Fraction, Fraction]],
    reciprocal: bool = False,
    fast: bool = True,
) -> Tuple[List[dict], List[Tuple[Fraction, Fraction, Fraction]], Tuple[Fraction, Fraction, Fraction]]:
    best = None
    best_key = None
    best_cent = None

    candidate_list = [(Fraction(0), Fraction(0), Fraction(0))] if reciprocal else origin_candidates[:2]
    for shift in candidate_list:
        print(f"[progress] origin shift: {tuple(float(s) for s in shift)}", file=sys.stderr)
        wps, centering_vectors, used_shift = derive_wyckoff(
            data,
            origin_shift=shift,
            reciprocal=reciprocal,
            fast=fast,
        )
        print(f"[progress] wyckoff count: {len(wps)}", file=sys.stderr)
        score = origin_score(wps)
        bias = 0 if all(s == 0 for s in shift) else 1
        key = (bias, score)
        if best is None or key < best_key:
            best = wps
            best_key = key
            best_cent = centering_vectors, used_shift
    assert best is not None and best_cent is not None
    cent_vecs, used_shift = best_cent
    best_sorted = sort_for_ita_letters(best, number=data.get("number"))
    return best_sorted, cent_vecs, used_shift


# --- CLI / formatting --------------------------------------------------------

def output_coord_key(*, kspace: bool = False, basis: str = "primitive", stars: bool = False) -> str:
    coord_key = "orbit_with_moments"
    if kspace:
        if stars:
            coord_key = "arms_conv" if basis == "conventional" else "arms"
        else:
            coord_key = "orbit_conv" if basis == "conventional" else "orbit"
    return coord_key


def representative_coord_key(*, kspace: bool = False, basis: str = "primitive") -> str:
    if kspace:
        return "orbit_conv" if basis == "conventional" else "orbit"
    return "orbit_with_moments"


def compute_wyckoff_output(
    data: Union[dict, str],
    *,
    kspace: bool = False,
    basis: str = "primitive",
    stars: bool = False,
    fast: bool = False,
) -> Tuple[List[dict], str]:
    if isinstance(data, str):
        data, _time_revs = load_irssg_data(data, 0)
    if kspace:
        used_shift = (Fraction(0), Fraction(0), Fraction(0))
        wyckoff, _centering_vectors, _ = derive_wyckoff(
            data,
            origin_shift=used_shift,
            reciprocal=True,
            fast=fast,
        )
    else:
        wyckoff, _centering_vectors, _used_shift = select_best_origin(
            data, origin_candidates=ORIGIN_SHIFTS, reciprocal=False, fast=fast
        )
    return wyckoff, output_coord_key(kspace=kspace, basis=basis, stars=stars)


DEFAULT_JSON_DROP_FIELDS = frozenset(
    {
        "orbit",
        "orbit_conv",
        "orbit_moments",
        "arms",
        "arms_conv",
        "basis_vecs",
        "stab_rotations",
        "orbit_conv_with_moments",
        "site_symmetry_custom",
        "unitary_site_symmetry",
        "system",
        "moment_basis",
        "moment_dim",
        "moment_constraints",
        "has_magnetic_moment",
        "representative_coordinate",
        "representative_moment",
        "representative_with_moment",
        "orbit_coord_score",
        "x0",
        "spin_matrix",
        "stab",
        "site_symmetry",
        "time_reversal",
        "kind",
        "axis",
        "axis_direction",
        "ns",
        "c",
        "spatial_site_symmetry_ops",
        "rep",
        "site_symmetry_ops",
        "spatial_site_symmetry_custom",
        "dim",
    }
)


def _prune_json_fields(value, drop_fields: set[str]):
    if isinstance(value, dict):
        return {
            key: _prune_json_fields(item, drop_fields)
            for key, item in value.items()
            if key not in drop_fields
        }
    if isinstance(value, list):
        return [_prune_json_fields(item, drop_fields) for item in value]
    if isinstance(value, tuple):
        return [_prune_json_fields(item, drop_fields) for item in value]
    return value


def compact_wyckoff_entries(
    wyckoff: List[dict],
    *,
    drop_fields: Optional[Sequence[str]] = None,
) -> List[dict]:
    drop = set(drop_fields or DEFAULT_JSON_DROP_FIELDS)
    return [_prune_json_fields(entry, drop) for entry in wyckoff]


def build_compact_json_payload(
    data: Union[dict, str],
    *,
    kspace: bool = False,
    basis: str = "primitive",
    stars: bool = False,
    fast: bool = False,
    drop_fields: Optional[Sequence[str]] = None,
) -> dict:
    wyckoff, _coord_key = compute_wyckoff_output(
        data,
        kspace=kspace,
        basis=basis,
        stars=stars,
        fast=fast,
    )
    payload = {
        "ssgnum": str(data) if isinstance(data, str) else str(data.get("number", "?")),
        "wyckoff": compact_wyckoff_entries(wyckoff, drop_fields=drop_fields),
    }
    return payload


def build_wyckoff_table_string(
    data: Union[dict, str],
    *,
    kspace: bool = False,
    basis: str = "primitive",
    stars: bool = False,
    fast: bool = False,
) -> str:
    wyckoff, coord_key = compute_wyckoff_output(
        data, kspace=kspace, basis=basis, stars=stars, fast=fast
    )
    return format_wyckoff_table(wyckoff, coord_key=coord_key)


def _format_decimal12(value: Fraction) -> str:
    return f"{float(value):.12f}"


def parse_numeric_kpoint(coord: str) -> Optional[List[str]]:
    compact = coord.replace(" ", "")
    if any(ch.isalpha() for ch in compact):
        return None
    parts = compact.split(",")
    if len(parts) != 3:
        return None
    try:
        vals = [Fraction(part) for part in parts]
    except Exception:
        return None
    return [_format_decimal12(val) for val in vals]


def extract_high_symmetry_kpoints(wyckoff: List[dict], coord_key: str) -> List[dict]:
    source_key = coord_key
    if coord_key in {"arms", "arms_conv"}:
        source_key = representative_coord_key(
            kspace=True,
            basis="conventional" if coord_key.endswith("_conv") else "primitive",
        )

    points: List[dict] = []
    for entry in wyckoff:
        coords = entry.get(source_key, entry.get("orbit", []))
        numeric_coords: List[List[str]] = []
        for coord in coords:
            parsed = parse_numeric_kpoint(coord)
            if parsed is not None:
                numeric_coords.append(parsed)
        if numeric_coords:
            points.append(
                {
                    "letter": entry["letter"],
                    "mult": entry["mult"],
                    "coordinates": numeric_coords,
                }
            )
    return points

def format_wyckoff_table(wyckoff: List[dict], coord_key: str = "orbit_with_moments") -> str:
    lines = []
    show_site = any(
        (entry.get("site_symmetry") or entry.get("site_symmetry_custom")) not in (None, "")
        for entry in wyckoff
    )
    show_moment = any(entry.get("moment_constraints") not in (None, "") for entry in wyckoff)
    site_width = (
        max(
            len("Site"),
            *(len(str(entry.get("site_symmetry") or entry.get("site_symmetry_custom") or "")) for entry in wyckoff),
        )
        if show_site
        else 0
    )
    moment_width = max(len("Moment"), *(len(str(entry.get("moment_constraints") or "")) for entry in wyckoff)) if show_moment else 0
    header = f"{'Mult':>4} {'Let':>3}"
    if show_site:
        header += f" {'Site':<{site_width}}"
    if show_moment:
        header += f" {'Moment':<{moment_width}}"
    header += " Coordinates"
    lines.append(header)
    for entry in wyckoff:
        coords = ";".join(entry.get(coord_key, entry["orbit"]))
        row = f"{entry['mult']:>4} {entry['letter']:>3}"
        if show_site:
            site_str = entry.get("site_symmetry") or entry.get("site_symmetry_custom") or "?"
            row += f" {site_str:<{site_width}}"
        if show_moment:
            row += f" {(entry.get('moment_constraints') or '-'):<{moment_width}}"
        row += f" {coords}"
        lines.append(row)
    return "\n".join(lines)


def _append_jsonl_alert(path_str: str, payload: dict) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def _report_non_integer_rotation(rot: np.ndarray, *, ssg1: int, ssg_label: str, h_index: int, q_index: int) -> None:
    alert_path = os.environ.get("SSWYCKOFF_NON_INTEGER_ALERT_FILE")
    if not alert_path:
        return
    payload = {
        "type": "non_integer_rotation",
        "sg": ssg1,
        "ssg": ssg_label,
        "h_index": h_index,
        "q_index": q_index,
        "rotation": rot.tolist(),
        "hostname": os.environ.get("SLURMD_NODENAME") or os.uname().nodename,
        "pid": os.getpid(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
    }
    _append_jsonl_alert(alert_path, payload)



def _require_integer_rotation(rot: np.ndarray, *, ssg1: int, ssg_label: str, h_index: int, q_index: int) -> np.ndarray:
    rot_int = np.rint(rot)
    if not np.allclose(rot, rot_int):
        _report_non_integer_rotation(
            rot,
            ssg1=ssg1,
            ssg_label=ssg_label,
            h_index=h_index,
            q_index=q_index,
        )
        raise ValueError(
            "construct_std_operations produced a non-integer rotation matrix "
            f"for SG {ssg1} (SSG {ssg_label}) at HRot[{h_index}], QRot[{q_index}]:\n{rot}"
        )
    return rot_int.astype(int)


def construct_std_operations(ssg_dic: dict, ssg1: int, spin_id: Optional[int] = None):
    HRot = ssg_dic["HRotC"]
    HTau = ssg_dic["HTauC"]
    QRot = ssg_dic["QRotC"]
    QTau = ssg_dic["QTauC"]

    if spin_id is not None:
        URot = ssg_dic["URot"][spin_id]
    else:
        URots = ssg_dic["URot"]

    rots = []
    taus = []
    spins = []

    superCell = ssg_dic['superCell']
    ssg_label = str(ssg_dic.get("ssgNum", f"{ssg1}"))
    trans_mat_BP_SP = identify_SG_lattice(ssg1)[1]@superCell

    S = trans_mat_BP_SP
    invS = np.linalg.inv(S)

    if spin_id is None:
        for _ in URots:
            spins.append([])

    for i, hrot in enumerate(HRot):
        htau = HTau[i]
        if spin_id is not None:
            for j, spin in enumerate(URot):
                qrot = QRot[j]
                qtau = QTau[j]
                rot_new = qrot @ hrot
                tau_new = qrot @ htau + qtau
                rot_std = _require_integer_rotation(
                    invS @ rot_new @ S,
                    ssg1=ssg1,
                    ssg_label=ssg_label,
                    h_index=i,
                    q_index=j,
                )
                spins.append(spin)
                rots.append(rot_std)
                taus.append(invS @ tau_new)
        else:
            for j, _ in enumerate(URots[0]):
                qrot = QRot[j]
                qtau = QTau[j]
                rot_new = qrot @ hrot
                tau_new = qrot @ htau + qtau
                rot_std = _require_integer_rotation(
                    invS @ rot_new @ S,
                    ssg1=ssg1,
                    ssg_label=ssg_label,
                    h_index=i,
                    q_index=j,
                )
                rots.append(rot_std)
                taus.append(invS @ tau_new)
                for k in range(len(URots)):
                    spins[k].append(URots[k][j])

    return rots, taus, spins

def identify_SG_lattice(gid):
    # identify Bravais lattice for a given sg, return: Brav_latt
    SGTricP = [1, 2]
    SGMonoP = [3, 4, 6, 7, 10, 11, 13, 14]
    SGMonoB = [5, 8, 9, 12, 15]
    SGOrthP = [16, 17, 18, 19, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 47,
               48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62]
    SGOrthB1 = [20, 21, 35, 36, 37, 63, 64, 65, 66, 67, 68]
    SGOrthB2 = [38, 39, 40, 41]
    SGOrthF = [22, 42, 43, 69, 70]
    SGOrthI = [23, 24, 44, 45, 46, 71, 72, 73, 74]
    SGTetrP = [75, 76, 77, 78, 81, 83, 84, 85, 86, 89, 90, 91, 92, 93, 94,
               95, 96, 99, 100, 101, 102, 103, 104, 105, 106, 111, 112,
               113, 114, 115, 116, 117, 118, 123, 124, 125, 126, 127,
               128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138]
    SGTetrI = [79, 80, 82, 87, 88, 97, 98, 107, 108, 109, 110, 119, 120,
               121, 122, 139, 140, 141, 142]
    SGTrigP = [146, 148, 155, 160, 161, 166, 167]
    SGHexaP = [143, 144, 145, 147, 149, 150, 151, 152, 153, 154, 156,
               157, 158, 159, 162, 163, 164, 165, 168, 169, 170, 171,
               172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182,
               183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194]
    SGCubcP = [195, 198, 200, 201, 205, 207, 208, 212, 213, 215, 218,
               221, 222, 223, 224]
    SGCubcF = [196, 202, 203, 209, 210, 216, 219, 225, 226, 227, 228]
    SGCubcI = [197, 199, 204, 206, 211, 214, 217, 220, 229, 230]

    # each row of prim_vec is a primitive base vector, and each column of prim_vec^-1 is a primitive base vec of BZ.
    if gid in SGTricP + SGMonoP + SGOrthP + SGTetrP + SGHexaP + SGCubcP:
        latt = 'P'
        prim_vec = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    elif gid in SGMonoB + SGOrthB1:
        latt = 'B'
        prim_vec = np.array([[1. / 2, -1. / 2, 0.], [1. / 2, 1. / 2, 0.], [0., 0., 1.]])
    elif gid in SGOrthB2:
        latt = 'B2'
        prim_vec = np.array([[1., 0., 0.], [0., 1. / 2, 1. / 2], [0., -1. / 2, 1. / 2]])
    elif gid in SGOrthI + SGTetrI + SGCubcI:
        latt = 'I'
        prim_vec = np.array([[-1. / 2, 1. / 2, 1. / 2], [1. / 2, -1. / 2, 1. / 2], [1. / 2, 1. / 2, -1. / 2]])
    elif gid in SGOrthF + SGCubcF:
        latt = 'F'
        prim_vec = np.array([[0., 1. / 2, 1. / 2], [1. / 2, 0., 1. / 2], [1. / 2, 1. / 2, 0.]])
    elif gid in SGTrigP:
        latt = 'R'
        prim_vec = np.array([[2. / 3, 1. / 3, 1. / 3], [-1. / 3, 1. / 3, 1. / 3], [-1. / 3, -2. / 3, 1. / 3]])
    else:
        raise ValueError('Wrong gid!', gid)
    # return transposed prim_vec, i.e., each col a prim vector
    return latt, prim_vec.T

def identify_lattice_type(gid: int) -> str:
    SGTricP = {1, 2}
    SGMonoP = {3, 4, 6, 7, 10, 11, 13, 14}
    SGMonoB = {5, 8, 9, 12, 15}
    SGOrthP = {
        16, 17, 18, 19, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 47,
        48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
    }
    SGOrthB1 = {20, 21, 35, 36, 37, 63, 64, 65, 66, 67, 68}
    SGOrthB2 = {38, 39, 40, 41}
    SGOrthF = {22, 42, 43, 69, 70}
    SGOrthI = {23, 24, 44, 45, 46, 71, 72, 73, 74}
    SGTetrP = {
        75, 76, 77, 78, 81, 83, 84, 85, 86, 89, 90, 91, 92, 93, 94,
        95, 96, 99, 100, 101, 102, 103, 104, 105, 106, 111, 112, 113,
        114, 115, 116, 117, 118, 123, 124, 125, 126, 127, 128, 129,
        130, 131, 132, 133, 134, 135, 136, 137, 138,
    }
    SGTetrI = {79, 80, 82, 87, 88, 97, 98, 107, 108, 109, 110, 119, 120, 121, 122, 139, 140, 141, 142}
    SGTrigP = {146, 148, 155, 160, 161, 166, 167}
    SGHexaP = {
        143, 144, 145, 147, 149, 150, 151, 152, 153, 154, 156, 157,
        158, 159, 162, 163, 164, 165, 168, 169, 170, 171, 172, 173,
        174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185,
        186, 187, 188, 189, 190, 191, 192, 193, 194,
    }
    SGCubcP = {195, 198, 200, 201, 205, 207, 208, 212, 213, 215, 218, 221, 222, 223, 224}
    SGCubcF = {196, 202, 203, 209, 210, 216, 219, 225, 226, 227, 228}
    SGCubcI = {197, 199, 204, 206, 211, 214, 217, 220, 229, 230}

    if gid in SGTricP | SGMonoP | SGOrthP | SGTetrP | SGHexaP | SGCubcP:
        return "P"
    if gid in SGMonoB | SGOrthB1:
        return "C"
    if gid in SGOrthB2:
        return "A"
    if gid in SGOrthI | SGTetrI | SGCubcI:
        return "I"
    if gid in SGOrthF | SGCubcF:
        return "F"
    if gid in SGTrigP:
        return "R"
    raise ValueError(f"Wrong gid! {gid}")


def sgnum_to_centering_symbol(sgnum: int) -> str:
    if not isinstance(sgnum, int) or not (1 <= sgnum <= 230):
        raise ValueError(f"sgnum must be int in [1, 230], got {sgnum!r}")
    cent = identify_lattice_type(sgnum)
    if cent not in {"P", "A", "B", "C", "I", "F", "R"}:
        raise RuntimeError(f"Unexpected centering letter {cent!r}")
    return cent


def crystal_system_from_sgnum(sgnum: int) -> str:
    if 1 <= sgnum <= 2:
        return "triclinic"
    if 3 <= sgnum <= 15:
        return "monoclinic"
    if 16 <= sgnum <= 74:
        return "orthorhombic"
    if 75 <= sgnum <= 142:
        return "tetragonal"
    if 143 <= sgnum <= 167:
        return "trigonal"
    if 168 <= sgnum <= 194:
        return "hexagonal"
    if 195 <= sgnum <= 230:
        return "cubic"
    return ""


def construct_std_ssg_operations(
    ssg_dic: dict,
    ssg_label: str,
    spin_id: Optional[int] = None,
) -> Tuple[List[np.ndarray], List[np.ndarray], List[np.ndarray], List[bool]]:
    first_tag = ssg_label.split(".")[0]
    last_tag = ssg_label[-1].strip() if ssg_label else ""
    ssg1 = int(first_tag)

    HRot = ssg_dic["HRotC"]
    HTau = ssg_dic["HTauC"]
    QRot = ssg_dic["QRotC"]
    QTau = ssg_dic["QTauC"]
    URot = ssg_dic["URot"][spin_id if spin_id is not None else -1]

    rots: List[np.ndarray] = []
    taus: List[np.ndarray] = []
    spins: List[np.ndarray] = []
    time_revs: List[bool] = []

    super_cell = ssg_dic["superCell"]
    trans_mat_bp_sp = identify_SG_lattice(ssg1)[1] @ super_cell
    S = trans_mat_bp_sp
    invS = np.linalg.inv(S)

    def append_std(
        rot_new: np.ndarray,
        tau_new: np.ndarray,
        spin_new: np.ndarray,
        tr_flag: bool,
        h_index: int,
        q_index: int,
    ) -> None:
        rot_std = _require_integer_rotation(
            invS @ rot_new @ S,
            ssg1=ssg1,
            ssg_label=ssg_label,
            h_index=h_index,
            q_index=q_index,
        )
        rots.append(rot_std)
        taus.append(invS @ tau_new)
        spins.append(np.asarray(spin_new, dtype=float))
        time_revs.append(bool(tr_flag))

    unitary_entries: List[Tuple[np.ndarray, np.ndarray, np.ndarray, int, int]] = []

    if last_tag == "P":
        anti_spin = np.diag([1.0, 1.0, -1.0])
        anti_rot = np.eye(3)
        anti_tau = np.zeros(3)
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                spin_arr = np.asarray(spin, dtype=float)
                if np.linalg.det(spin_arr) < 0:
                    spin_arr = anti_spin @ spin_arr
                rot_new = QRot[j] @ hrot
                tau_new = QRot[j] @ htau + QTau[j]
                append_std(rot_new, tau_new, spin_arr, False, i, j)
                unitary_entries.append((rot_new, tau_new, spin_arr, i, j))
        for rot_new, tau_new, spin_arr, i, j in unitary_entries:
            append_std(anti_rot @ rot_new, anti_rot @ tau_new + anti_tau, anti_spin @ spin_arr, True, i, j)
    elif last_tag == "L":
        anti_spin = np.diag([-1.0, 1.0, 1.0])
        anti_rot = np.eye(3)
        anti_tau = np.zeros(3)
        c2z = np.diag([-1.0, -1.0, 1.0])
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                spin_arr = np.asarray(spin, dtype=float)
                if np.linalg.det(spin_arr) < 0:
                    spin_arr = anti_spin @ spin_arr
                rot_new = QRot[j] @ hrot
                tau_new = QRot[j] @ htau + QTau[j]
                append_std(rot_new, tau_new, spin_arr, False, i, j)
                unitary_entries.append((rot_new, tau_new, spin_arr, i, j))
                spin_c2z = c2z @ spin_arr
                append_std(rot_new, tau_new, spin_c2z, False, i, j)
                unitary_entries.append((rot_new, tau_new, spin_c2z, i, j))
        for rot_new, tau_new, spin_arr, i, j in unitary_entries:
            append_std(anti_rot @ rot_new, anti_rot @ tau_new + anti_tau, anti_spin @ spin_arr, True, i, j)
    else:
        anti_idx = next((idx for idx, spin in enumerate(URot) if np.linalg.det(spin) < 0), None)
        anti_spin = np.asarray(URot[anti_idx], dtype=float) if anti_idx is not None else None
        anti_rot = np.asarray(QRot[anti_idx], dtype=float) if anti_idx is not None else None
        anti_tau = np.asarray(QTau[anti_idx], dtype=float) if anti_idx is not None else None
        for i, hrot in enumerate(HRot):
            htau = HTau[i]
            for j, spin in enumerate(URot):
                spin_arr = np.asarray(spin, dtype=float)
                if np.linalg.det(spin_arr) <= 0:
                    continue
                rot_new = QRot[j] @ hrot
                tau_new = QRot[j] @ htau + QTau[j]
                append_std(rot_new, tau_new, spin_arr, False, i, j)
                unitary_entries.append((rot_new, tau_new, spin_arr, i, j))
        if anti_idx is not None and anti_spin is not None and anti_rot is not None and anti_tau is not None:
            for rot_new, tau_new, spin_arr, i, j in unitary_entries:
                append_std(anti_rot @ rot_new, anti_rot @ tau_new + anti_tau, anti_spin @ spin_arr, True, i, j)

    return rots, taus, spins, time_revs


def irssg_entry_to_data(
    operation: dict,
    ssgnum: Optional[str] = None,
    spin_id: Optional[int] = None,
) -> Tuple[dict, List[bool]]:
    ssg_label = operation.get("ssgNum", ssgnum or "?")
    first_tag = ssg_label.split(".")[0]
    centering_symbol = sgnum_to_centering_symbol(int(first_tag))
    rots, taus, spins, time_revs = construct_std_ssg_operations(operation, ssg_label, spin_id=spin_id)

    operations = []
    spin_matrices = []
    for rot, tau, spin in zip(rots, taus, spins):
        rot_list = rot.tolist() if hasattr(rot, "tolist") else rot
        tau_list = tau.tolist() if hasattr(tau, "tolist") else tau
        operations.append({"matrix": rot_list, "translation": tau_list})
        spin_matrices.append(np.asarray(spin, dtype=float).tolist())

    data = {
        "centering_symbol": "P",
        "number": ssg_label,
        "display_name": f"SSG {ssg_label}",
        "crystal_system": crystal_system_from_sgnum(int(first_tag)),
        "operations": operations,
        "time_revs": time_revs,
        "spin_matrices": spin_matrices,
        "source_centering_symbol": centering_symbol,
    }
    return data, time_revs


def load_irssg_data(ssgnum: str, spin_id: int) -> Tuple[dict, List[bool]]:
    load_one_ssg = None
    try:
        import irssg  # type: ignore
        load_one_ssg = getattr(irssg, "load_one_ssg", None)
    except Exception:
        irssg = None  # type: ignore[assignment]

    if load_one_ssg is None:
        try:
            from irssg.ssg.load_ssgdata import load_one_ssg as _load_one_ssg  # type: ignore
            load_one_ssg = _load_one_ssg
        except Exception:
            site_packages = (
                Path(__file__).resolve().parents[2]
                / "irssg"
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
            )
            if site_packages.exists():
                site_packages_str = str(site_packages)
                if site_packages_str not in sys.path:
                    sys.path.insert(0, site_packages_str)
                data_file = site_packages / "irssg" / "ssg" / "ssg_data" / "identify.pkl"
                if data_file.exists():
                    import pickle

                    def _load_one_ssg_from_pickle(query_ssgnum: str):
                        with open(data_file, "rb") as fh:
                            ssg_list = pickle.load(fh)
                        for ssg in ssg_list:
                            if ssg.get("ssgNum") == query_ssgnum:
                                return ssg
                        raise ValueError(f"Cannot load SSG number {query_ssgnum} from {data_file}")

                    load_one_ssg = _load_one_ssg_from_pickle
            try:
                if load_one_ssg is None:
                    # A namespace package from /data/home/tmy/irssg can shadow the
                    # real installed irssg package, so clear cached imports first.
                    for mod_name in list(sys.modules):
                        if mod_name == "irssg" or mod_name.startswith("irssg."):
                            sys.modules.pop(mod_name, None)
                    import irssg  # type: ignore
                    load_one_ssg = getattr(irssg, "load_one_ssg", None)
            except Exception as exc:
                raise ImportError("irssg + numpy are required for --irssg-ssgnum.") from exc
            if load_one_ssg is None:
                try:
                    from irssg.ssg.load_ssgdata import load_one_ssg as _load_one_ssg  # type: ignore
                    load_one_ssg = _load_one_ssg
                except Exception as exc:
                    raise ImportError("irssg.load_one_ssg is not available in the current environment.") from exc

    operation = load_one_ssg(ssgnum)
    return irssg_entry_to_data(operation, ssgnum=ssgnum, spin_id=spin_id)


def main():
    parser = argparse.ArgumentParser(description="Compute Wyckoff positions from space-group JSON (accelerated).")
    parser.add_argument(
        "--irssg-ssgnum",
        default=None,
        help="Load operations via irssg.load_one_ssg(ssgnum).",
    )
    parser.add_argument(
        "--kspace",
        action="store_true",
        help="Compute high-symmetry k-space points (reciprocal-space Wyckoff analogue).",
    )
    parser.add_argument(
        "--basis",
        choices=["primitive", "conventional"],
        default="primitive",
        help="Coordinate basis for k-space output: primitive (default) or conventional reciprocal coordinates.",
    )
    parser.add_argument(
        "--stars",
        action="store_true",
        help="For k-space, list star arms instead of orbit representatives.",
    )
    parser.add_argument(
        "--fast",
        dest="fast",
        action="store_true",
        default=False,
        help="Fast output: skip expensive 'best rep' scans.",
    )

    args = parser.parse_args()

    if not args.irssg_ssgnum:
        parser.error("Please provide --irssg-ssgnum.")

    data, _time_revs = load_irssg_data(args.irssg_ssgnum, 0)

    if args.kspace:
        used_shift = (Fraction(0), Fraction(0), Fraction(0))
        print("[progress] k-space mode", file=sys.stderr)

        wyckoff, centering_vectors, _ = derive_wyckoff(
            data,
            origin_shift=used_shift,
            reciprocal=True,
            fast=args.fast,
        )
    else:
        print("[progress] real-space mode", file=sys.stderr)
        wyckoff, centering_vectors, used_shift = select_best_origin(
            data, origin_candidates=ORIGIN_SHIFTS, reciprocal=False, fast=args.fast
        )

    op_builder = to_reciprocal_op if args.kspace else (lambda o: o)
    base_ops = [op_builder(op_from_json(op)) for op in data["operations"]]

    expanded_ops = expand_with_centering(base_ops, centering_vectors)
    if not args.kspace and used_shift != (Fraction(0), Fraction(0), Fraction(0)):
        expanded_ops = [shift_op(op, used_shift) for op in expanded_ops]

    centering_symbol = (data.get("centering_symbol") or "P")[0].upper()
    label = "k-space special points" if args.kspace else "Wyckoff positions"
    display_name = data.get("display_name") or f"SG/SSG {data.get('number','?')}"
    print(f"{label} for {display_name} (No. {data.get('number','?')})")
    print(f"Operations in JSON: {len(base_ops)}; expanded with centering: {len(expanded_ops)}")
    centering_str = " + ".join("(" + ", ".join(frac_str(c) for c in vec) + ")" for vec in centering_vectors)
    if args.kspace and centering_symbol != "P":
        centering_str += " (ignored in k-space)"
    print(f"Centering translations: {centering_str}")
    if not args.kspace and used_shift != (Fraction(0), Fraction(0), Fraction(0)):
        shift_str = "(" + ", ".join(frac_str(s) for s in used_shift) + ")"
        print(f"Selected origin shift: {shift_str}")
    print()

    coord_key = output_coord_key(kspace=args.kspace, basis=args.basis, stars=args.stars)
    print(format_wyckoff_table(wyckoff, coord_key=coord_key))



from sympy import Matrix
from sympy.matrices.normalforms import hermite_normal_form

Vec3 = Tuple[Fraction, Fraction, Fraction]
Mat3 = List[List[Fraction]]


def mat_mul(A: Mat3, B: Mat3) -> Mat3:
    return [
        [sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def mat_vec_mul(A: Mat3, v: Sequence[Fraction]) -> List[Fraction]:
    return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]


def tuple3(v: Sequence[Fraction]) -> Vec3:
    return (Fraction(v[0]), Fraction(v[1]), Fraction(v[2]))


def collect_pure_translations(ops: Iterable[Op]) -> List[Vec3]:
    I = tuple(tuple(x for x in row) for row in identity_mat())
    zero = (Fraction(0), Fraction(0), Fraction(0))
    seen = set()
    pure: List[Vec3] = []
    for op in ops:
        if op.W != I:
            continue
        t = tuple(mod1(v) for v in op.t)
        if t in seen:
            continue
        seen.add(t)
        pure.append(t)  # type: ignore[arg-type]
    if zero not in seen:
        pure.insert(0, zero)
    pure.sort()
    return pure


def lcm_denominators(vectors: Iterable[Vec3]) -> int:
    out = 1
    for vec in vectors:
        for x in vec:
            out = math.lcm(out, x.denominator)
    return out


def quotient_lattice_basis(pure_translations: List[Vec3]) -> Tuple[Mat3, int]:
    nontrivial = [t for t in pure_translations if any(v != 0 for v in t)]
    if not nontrivial:
        I = identity_mat()
        return [[Fraction(x) for x in row] for row in I], 1

    D = lcm_denominators(nontrivial)

    cols: List[List[int]] = [
        [D, 0, 0],
        [0, D, 0],
        [0, 0, D],
    ]
    for t in nontrivial:
        cols.append([int(D * t[0]), int(D * t[1]), int(D * t[2])])

    gen_mat = Matrix([[col[r] for col in cols] for r in range(3)])
    hnf = hermite_normal_form(gen_mat)
    if hnf.shape != (3, 3):
        raise RuntimeError(f"Unexpected HNF shape {hnf.shape}, expected (3, 3)")

    basis = [
        [Fraction(int(hnf[i, j]), D) for j in range(3)]
        for i in range(3)
    ]

    det_h = abs(int(hnf.det()))
    if det_h == 0:
        raise RuntimeError("Degenerate quotient lattice basis (det=0)")
    index = (D ** 3) // det_h
    if index <= 0:
        raise RuntimeError(f"Invalid lattice index {index}")
    return basis, index


def transform_ops_to_basis(ops: List[Op], basis_old_from_new: Mat3) -> List[Op]:
    basis_new_from_old = mat_inv(basis_old_from_new)
    out: List[Op] = []
    for op in ops:
        W_old = [[Fraction(x) for x in row] for row in op.W]
        W_new = mat_mul(mat_mul(basis_new_from_old, W_old), basis_old_from_new)
        t_new = tuple(mod1(v) for v in mat_vec_mul(basis_new_from_old, op.t))
        out.append(
            Op(
                W=tuple(tuple(Fraction(x) for x in row) for row in W_new),
                t=tuple3(t_new),
            )
        )
    return sorted(dedup_ops(out), key=op_key)


def op_to_json(op: Op) -> Dict[str, List[List[Fraction]]]:
    return {
        "matrix": [[Fraction(x) for x in row] for row in op.W],
        "translation": [Fraction(v) for v in op.t],
    }


def expand_quotient_wyckoff(
    *,
    wyckoff_q: List[dict],
    full_ops: List[Op],
    full_time_revs: List[bool],
    full_spin_ops: List[SpinOp],
    basis_old_from_new: Mat3,
    system: str,
    number: str,
) -> List[dict]:
    zero = (Fraction(0), Fraction(0), Fraction(0))
    dedup_centers = [zero]
    expanded: List[dict] = []
    seen_wps = set()
    full_ops_sorted = full_ops
    if len(full_ops_sorted) != len(full_time_revs):
        raise ValueError(
            f"full_ops/full_time_revs length mismatch: {len(full_ops_sorted)} vs {len(full_time_revs)}"
        )
    if len(full_ops_sorted) != len(full_spin_ops):
        raise ValueError(
            f"full_ops/full_spin_ops length mismatch: {len(full_ops_sorted)} vs {len(full_spin_ops)}"
        )
    mag_full_ops_sorted = build_magnetic_ops(full_ops_sorted, full_time_revs)
    spin_full_ops_sorted = full_spin_ops
    try:
        pg_lookup = mw.build_point_group_signature_lookup()
    except FileNotFoundError:
        # The lookup only improves standardized point-group labels.
        # Enumeration can continue without bundled space-group JSON files.
        pg_lookup = {}
        print(
            "[warning] space_groups_json not found; site-symmetry labels may be less specific",
            file=sys.stderr,
        )

    for entry in wyckoff_q:
        # Initial lift only to identify the geometric subspace in old coordinates.
        rep_q = entry["rep"]
        rep_old_lift = [normalize_expr(e) for e in apply_mat_to_vec_expr(basis_old_from_new, rep_q)]

        basis_old_lift = [
            [Fraction(v) for v in mat_vec_mul(basis_old_from_new, bvec)]
            for bvec in entry.get("basis_vecs", [])
        ]
        if basis_old_lift:
            basis_old_lift = canonicalize_axis_aligned_basis(basis_old_lift)
            basis_old_lift = scale_basis_to_primitive(basis_old_lift)

        x0_raw = [mod1(e[0]) for e in rep_old_lift]
        wp_key = subspace_orbit_key(x0_raw, basis_old_lift, full_ops_sorted)
        if wp_key in seen_wps:
            continue
        seen_wps.add(wp_key)

        # Reconstruct a canonical representative from the subspace key so
        # parameterization stays close to getwyckoff.py output style.
        ns_key, c_vals = wp_key
        A_cons = [list(row) for row in ns_key]
        rep_x0, rep_basis = solve_affine(A_cons, list(c_vals))
        rep_x0 = mod1_vec(rep_x0)

        orbit_reps: List[Tuple[List[Fraction], List[List[Fraction]]]] = []
        orbit_keys: List[Tuple] = []
        for op in full_ops_sorted:
            x1 = mod1_vec(op.apply(rep_x0))
            b1 = apply_op_basis(op, rep_basis)
            orbit_reps.append((x1, b1))
            orbit_keys.append(canonical_subspace_key(x1, b1))
        min_idx = min(
            range(len(orbit_reps)),
            key=lambda i: (
                basis_score(orbit_reps[i][1]),
                dedup_coord_score(orbit_reps[i][0]),
                orbit_keys[i],
            ),
        )
        rep_x0, rep_basis = orbit_reps[min_idx]

        rep_basis = canonicalize_axis_aligned_basis(rep_basis)
        rep_basis = scale_basis_to_primitive(rep_basis)
        if len(rep_basis) == 3:
            rep_x0 = [Fraction(0), Fraction(0), Fraction(0)]
            rep_basis = [
                [Fraction(1), Fraction(0), Fraction(0)],
                [Fraction(0), Fraction(1), Fraction(0)],
                [Fraction(0), Fraction(0), Fraction(1)],
            ]

        rep_old = build_symbolic_rep(rep_x0, rep_basis)
        if len(rep_basis) == 1:
            bvec = rep_basis[0]
            nz_idx = [i for i, v in enumerate(bvec) if v != 0]
            if (
                len(nz_idx) == 2
                and bvec[2] == 0
                and abs(bvec[nz_idx[0]]) == abs(bvec[nz_idx[1]])
                and bvec[nz_idx[0]] != bvec[nz_idx[1]]
            ):
                mag = abs(bvec[nz_idx[0]])
                if mag != 0:
                    scale = Fraction(1, 1) / mag
                    if bvec[nz_idx[0]] < 0:
                        scale = -scale
                    param_name = None
                    for expr in rep_old:
                        if expr[1]:
                            param_name = next(iter(expr[1]))
                            break
                    if param_name:
                        rep_old = reparam_expr_vec(rep_old, param_name, scale=scale, shift=Fraction(0))
                        rep_basis = [[v * scale for v in bvec]]
            if bvec[2] == 0 and bvec[0] == bvec[1] and bvec[0] != 0:
                param_name = next(iter(rep_old[0][1].keys()), None)
                if param_name and len(rep_old) >= 3 and rep_old[2][0] == Fraction(1, 2):
                    rep_old = reparam_expr_vec(rep_old, param_name, scale=Fraction(-1, 1), shift=Fraction(1, 2))
                    rep_basis = [[-bvec[0], -bvec[1], -bvec[2]]]

        orbit_expr: List[str] = []
        orbit_sig_order: List[Tuple] = []
        seen_sig = set()
        orbit_min_score = None
        for op in full_ops_sorted:
            vec = [normalize_expr(e) for e in apply_op_expr(op, rep_old)]
            sig, _ = expr_vec_signature(
                vec,
                dedup_centers,
                origin_shifts=[zero],
            )
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            orbit_sig_order.append(sig)
            orbit_expr.append(vector_expr_str(vec))
            score = dedup_coord_score([expr[0] for expr in vec])
            if orbit_min_score is None or score < orbit_min_score:
                orbit_min_score = score

        _, best_consts = expr_vec_signature(
            rep_old,
            dedup_centers,
            origin_shifts=[zero],
        )

        stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, full_ops_sorted)
        stab_ops = [full_ops_sorted[i] for i in stab_indices]
        mag_stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, mag_full_ops_sorted)
        mag_stab_ops = [mag_full_ops_sorted[i] for i in mag_stab_indices]
        spin_stab_indices = stabilizer_indices_for_subspace(rep_x0, rep_basis, spin_full_ops_sorted)
        spin_stab_ops = [spin_full_ops_sorted[i] for i in spin_stab_indices]
        unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]
        unitary_site_symmetry = mw.classify_site_symmetry(unique_rotations(unitary_mag_stab_ops), pg_lookup)
        spatial_site_symmetry_custom, spatial_site_symmetry_ops = mw.build_custom_site_symmetry(mag_stab_ops)
        site_symmetry_custom, site_symmetry_ops = build_spin_site_symmetry(spin_stab_ops)
        if site_symmetry_custom is None:
            site_symmetry_custom = spatial_site_symmetry_custom
            site_symmetry_ops = spatial_site_symmetry_ops
        site_symmetry = (
            mw.lookup_magnetic_bilbao_symbol(
                spatial_site_symmetry_custom or site_symmetry_custom or "",
                unitary_site_symmetry or "",
                spatial_site_symmetry_ops or site_symmetry_ops,
            )
            or
            mw.bilbao_magnetic_point_group_symbol(
                spatial_site_symmetry_ops or site_symmetry_ops,
                crystal_system=str(system or ""),
            )
            or spatial_site_symmetry_custom
            or site_symmetry_custom
            or unitary_site_symmetry
        )
        moment_basis = allowed_spin_moment_basis(spin_stab_ops)
        moment_param_names = moment_param_names_for_numeric_basis(moment_basis)
        moment_constraints = moment_basis_to_string(moment_basis, moment_param_names)

        orbit_moment_map: Dict[Tuple, str] = {}
        orbit_with_moments_map: Dict[Tuple, str] = {}
        for op, spin_op in zip(full_ops_sorted, spin_full_ops_sorted):
            vec = [normalize_expr(e) for e in apply_op_expr(op, rep_old)]
            sig, _ = expr_vec_signature(
                vec,
                dedup_centers,
                origin_shifts=[zero],
            )
            moment_str = moment_basis_to_string(
                transform_moment_basis(spin_op.spin, moment_basis),
                moment_param_names,
            )
            orbit_moment_map[sig] = moment_str
            orbit_with_moments_map[sig] = format_coordinate_with_moment(vector_expr_str(vec), moment_str)
        orbit_moments = [orbit_moment_map[sig] for sig in orbit_sig_order]
        orbit_expr_with_moments = [orbit_with_moments_map[sig] for sig in orbit_sig_order]

        representative_coordinate = vector_expr_str([normalize_expr(e) for e in rep_old])
        representative_moment = moment_basis_to_string(moment_basis, moment_param_names)
        representative_with_moment = format_coordinate_with_moment(representative_coordinate, representative_moment)

        expanded.append(
            {
                "mult": len(orbit_expr),
                "dim": entry.get("dim", len(rep_basis)),
                "x0": list(best_consts),
                "basis_vecs": rep_basis,
                "rep": rep_old,
                "orbit": orbit_expr,
                "orbit_conv": orbit_expr[:],
                "orbit_moments": orbit_moments,
                "orbit_with_moments": orbit_expr_with_moments,
                "orbit_conv_with_moments": orbit_expr_with_moments[:],
                "arms": orbit_expr[:],
                "arms_conv": orbit_expr[:],
                "orbit_coord_score": orbit_min_score,
                "system": system,
                "number": number,
                "stab": len(stab_ops),
                "stab_rotations": unique_rotations(stab_ops),
                "site_symmetry": site_symmetry,
                "unitary_site_symmetry": unitary_site_symmetry,
                "site_symmetry_custom": site_symmetry_custom,
                "site_symmetry_ops": site_symmetry_ops,
                "spatial_site_symmetry_custom": spatial_site_symmetry_custom,
                "spatial_site_symmetry_ops": spatial_site_symmetry_ops,
                "moment_basis": moment_basis,
                "moment_param_names": moment_param_names,
                "moment_dim": len(moment_basis),
                "moment_constraints": moment_constraints,
                "has_magnetic_moment": bool(moment_basis),
                "representative_coordinate": representative_coordinate,
                "representative_moment": representative_moment,
                "representative_with_moment": representative_with_moment,
            }
        )

    return sort_for_ita_letters(expanded, number=number)


def vec3_str(v: Vec3) -> str:
    return "(" + ", ".join(frac_str(x) for x in v) + ")"


def compute_wyckoff_output(
    data: Union[dict, str],
    *,
    kspace: bool = False,
    basis: str = "primitive",
    stars: bool = False,
    fast: bool = False,
):
    if kspace:
        raise ValueError("getwyckoff_quotient.py only supports real-space Wyckoff output.")
    del basis, stars
    if isinstance(data, str):
        data, _time_revs = load_irssg_data(data, 0)

    base_ops = [op_from_json(op) for op in data["operations"]]
    time_revs = data.get("time_revs", [False] * len(base_ops))
    spin_matrices = data.get("spin_matrices")
    full_spin_ops_unsorted = build_spin_ops(base_ops, time_revs, spin_matrices)
    full_pairs = sorted(
        zip(base_ops, time_revs, full_spin_ops_unsorted),
        key=lambda item: spin_op_key(item[2]),
    )
    full_ops = [op for op, _, _ in full_pairs]
    full_time_revs = [bool(tr) for _, tr, _ in full_pairs]
    full_spin_ops = [spin_op for _, _, spin_op in full_pairs]
    pure_trans = collect_pure_translations(full_ops)

    basis_old_from_new, _trans_index = quotient_lattice_basis(pure_trans)
    quotient_ops = transform_ops_to_basis(full_ops, basis_old_from_new)

    quotient_time_revs = [False] * len(quotient_ops)
    q_data = {
        "centering_symbol": "P",
        "number": f"{data.get('number', '?')}/Q",
        "display_name": f"{data.get('display_name', 'SSG')}/Q",
        "operations": [op_to_json(op) for op in quotient_ops],
        "time_revs": quotient_time_revs,
        "crystal_system": data.get("crystal_system", ""),
    }

    zero = (Fraction(0), Fraction(0), Fraction(0))
    wyckoff_q, _qcent, used_shift_q = select_best_origin(
        q_data,
        origin_candidates=ORIGIN_SHIFTS,
        reciprocal=False,
        fast=fast,
    )

    used_shift = tuple3([mod1(v) for v in mat_vec_mul(basis_old_from_new, used_shift_q)])
    if used_shift != zero:
        shifted_pairs = sorted(
            [
                (shift_op(op, used_shift), tr, shift_spin_op(spin_op, used_shift))
                for op, tr, spin_op in zip(full_ops, full_time_revs, full_spin_ops)
            ],
            key=lambda item: spin_op_key(item[2]),
        )
        full_ops = [op for op, _, _ in shifted_pairs]
        full_time_revs = [bool(tr) for _, tr, _ in shifted_pairs]
        full_spin_ops = [spin_op for _, _, spin_op in shifted_pairs]

    wyckoff_full = expand_quotient_wyckoff(
        wyckoff_q=wyckoff_q,
        full_ops=full_ops,
        full_time_revs=full_time_revs,
        full_spin_ops=full_spin_ops,
        basis_old_from_new=basis_old_from_new,
        system=data.get("crystal_system", ""),
        number=str(data.get("number", "?")),
    )
    return wyckoff_full, "orbit_with_moments"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute Wyckoff positions via quotient by pure translations, then expand back."
    )
    parser.add_argument(
        "--irssg-ssgnum",
        required=True,
        help="Load operations via irssg.load_one_ssg(ssgnum).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        default=False,
        help="Pass --fast to quotient-group Wyckoff enumeration.",
    )
    parser.add_argument(
        "--origin-mode",
        choices=["auto", "zero"],
        default="auto",
        help="Origin selection: 'auto' matches getwyckoff.py candidate-origin choice; 'zero' forces (0,0,0).",
    )
    args = parser.parse_args()

    data, _ = load_irssg_data(args.irssg_ssgnum, 0)

    base_ops = [op_from_json(op) for op in data["operations"]]
    time_revs = data.get("time_revs", [False] * len(base_ops))
    spin_matrices = data.get("spin_matrices")
    full_spin_ops_unsorted = build_spin_ops(base_ops, time_revs, spin_matrices)
    full_pairs = sorted(
        zip(base_ops, time_revs, full_spin_ops_unsorted),
        key=lambda item: spin_op_key(item[2]),
    )
    full_ops = [op for op, _, _ in full_pairs]
    full_time_revs = [bool(tr) for _, tr, _ in full_pairs]
    full_spin_ops = [spin_op for _, _, spin_op in full_pairs]
    pure_trans = collect_pure_translations(full_ops)

    basis_old_from_new, trans_index = quotient_lattice_basis(pure_trans)
    quotient_ops = transform_ops_to_basis(full_ops, basis_old_from_new)

    quotient_time_revs = [False] * len(quotient_ops)
    q_data = {
        "centering_symbol": "P",
        "number": f"{data.get('number', '?')}/Q",
        "display_name": f"{data.get('display_name', 'SSG')}/Q",
        "operations": [op_to_json(op) for op in quotient_ops],
        "time_revs": quotient_time_revs,
        "crystal_system": data.get("crystal_system", ""),
    }

    zero = (Fraction(0), Fraction(0), Fraction(0))
    if args.origin_mode == "auto":
        wyckoff_q, _qcent, used_shift_q = select_best_origin(
            q_data,
            origin_candidates=ORIGIN_SHIFTS,
            reciprocal=False,
            fast=args.fast,
        )
    else:
        wyckoff_q, _qcent, used_shift_q = derive_wyckoff(
            q_data,
            origin_shift=zero,
            reciprocal=False,
            fast=args.fast,
        )

    used_shift = tuple3([mod1(v) for v in mat_vec_mul(basis_old_from_new, used_shift_q)])
    if used_shift != zero:
        shifted_pairs = sorted(
            [
                (shift_op(op, used_shift), tr, shift_spin_op(spin_op, used_shift))
                for op, tr, spin_op in zip(full_ops, full_time_revs, full_spin_ops)
            ],
            key=lambda item: spin_op_key(item[2]),
        )
        full_ops = [op for op, _, _ in shifted_pairs]
        full_time_revs = [bool(tr) for _, tr, _ in shifted_pairs]
        full_spin_ops = [spin_op for _, _, spin_op in shifted_pairs]

    wyckoff_full = expand_quotient_wyckoff(
        wyckoff_q=wyckoff_q,
        full_ops=full_ops,
        full_time_revs=full_time_revs,
        full_spin_ops=full_spin_ops,
        basis_old_from_new=basis_old_from_new,
        system=data.get("crystal_system", ""),
        number=str(data.get("number", "?")),
    )

    nontrivial = [t for t in pure_trans if any(v != 0 for v in t)]
    display_name = data.get("display_name") or f"SSG {data.get('number','?')}"
    print(f"Wyckoff positions for {display_name} (No. {data.get('number','?')})")
    print(
        f"Full operations: {len(full_ops)}; quotient operations: {len(quotient_ops)}; "
        f"pure-translation subgroup size: {len(pure_trans)}"
    )
    print(f"Quotient index from lattice construction: {trans_index}")
    print(f"Selected origin shift: {vec3_str(used_shift)}")
    if nontrivial:
        print("Nontrivial pure translations: " + ", ".join(vec3_str(v) for v in nontrivial))
    else:
        print("Nontrivial pure translations: none")
    print()
    print(format_wyckoff_table(wyckoff_full, coord_key="orbit_with_moments"))


if __name__ == "__main__":
    main()
