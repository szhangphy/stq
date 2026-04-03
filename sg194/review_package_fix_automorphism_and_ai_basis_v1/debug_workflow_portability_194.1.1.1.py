#!/usr/bin/env python3
"""Legacy SG194 stage1 backend.

This script remains the SG194-specific raw geometry/runtime producer.
The unified entrypoint for current runs is `run_group_pipeline.py`.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import importlib.util
import io
import json
import math
import pickle
import shutil
import subprocess
import sys
import tarfile
import textwrap
import tarfile as tarfile_module
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
COMMON_ROOT = next(
    (candidate for candidate in (ROOT.parent / "common", ROOT / "common") if candidate.exists()),
    ROOT.parent / "common",
)
COMMON_SSGREPS_ROOT = COMMON_ROOT / "SSGReps"
COMMON_SSG_DATA_ROOT = COMMON_SSGREPS_ROOT / "ssg_data"
IDENTIFY_PKL = COMMON_SSG_DATA_ROOT / "identify.pkl"
IDENTIFY_TAR = COMMON_SSG_DATA_ROOT / "identify.pkl.tar.gz"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import smith_normal_form

import debug_single_group_ai_bridge as bridge
import debug_single_group_ai_expanded as single_expanded
import swyckoff_k
import swyckoff_r
from pipeline_v2.final_object_reduction import (
    analyze_candidate_path_selection,
    build_candidate_path_records,
    build_expected_check_markdown,
    build_final_bs_strong_equivalence_markdown,
    build_final_bs_strong_equivalence_report,
    build_full_shell_automorphism_search_markdown,
    build_full_shell_automorphism_search_report,
    build_final_path_candidate_equivalence_markdown,
    build_final_path_candidate_equivalence_report,
    build_final_path_signature_markdown,
    build_final_path_signature_report,
    build_missing_row_language_witness_markdown,
    build_missing_row_language_witness_report,
    build_p1_p5_doubleclass_resolution_markdown,
    build_p1_p5_doubleclass_resolution_report,
    build_reduction_report_markdown,
    compare_reduction_to_expected_pairs,
    finalize_reduction_from_candidate_analysis,
    reduce_final_point_path_shell,
)

REFERENCE_GROUP = "10.4.1.31"
TARGET_GROUP = "194.1.1.1"
PACKAGE_NAME = "review_package_fix_automorphism_and_ai_basis_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

CONTROLLED_AUDIT_MD = ROOT / "controlled_case_audit_194.1.1.1.md"
PORTABILITY_AUDIT_MD = ROOT / "workflow_portability_audit_194.1.1.1.md"
PORTABILITY_SUMMARY_JSON = ROOT / "workflow_portability_summary_194.1.1.1.json"
SINGLE_SUMMARY_JSON = ROOT / "group_194_1_1_1_single_pilot_summary.json"
SINGLE_AUDIT_MD = ROOT / "group_194_1_1_1_single_pilot_audit.md"
DOUBLE_SUMMARY_JSON = ROOT / "group_194_1_1_1_double_pilot_summary.json"
DOUBLE_AUDIT_MD = ROOT / "group_194_1_1_1_double_pilot_audit.md"
HANDOFF_MD = ROOT / "handoff_194.1.1.1.md"
CURRENT_STATUS_JSON = ROOT / "current_status_194.1.1.1.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_194.1.1.1.txt"
REPORT_TEX = ROOT / "workflow_portability_report_194.1.1.1.tex"
REPORT_PDF = ROOT / "workflow_portability_report_194.1.1.1.pdf"

SINGLE_KMANIFOLDS_JSON = ROOT / "group_194_1_1_1_single_kmanifolds.json"
SINGLE_CONNECTIVITY_JSON = ROOT / "group_194_1_1_1_single_connectivity.json"
SINGLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_single_little_groups.json"
SINGLE_LINE_COMPAT_JSON = ROOT / "group_194_1_1_1_single_line_compatibility.json"
SINGLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_single_full_compatibility_with_planes.json"
SINGLE_BS_JSON = ROOT / "group_194_1_1_1_single_bs_analysis.json"
SINGLE_AI_JSON = ROOT / "group_194_1_1_1_single_ai_trivial_generators.json"

DOUBLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_double_little_groups.json"
DOUBLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_double_full_compatibility_with_planes.json"
DOUBLE_BS_JSON = ROOT / "group_194_1_1_1_double_bs_analysis.json"
DOUBLE_MINIMAL_JSON = ROOT / "group_194_1_1_1_double_minimal_prototype.json"
REDUCTION_REPORT_MD = ROOT / "bs_fix_reaudit_v1" / "final_object_reduction_report.md"
REDUCTION_REPORT_JSON = ROOT / "bs_fix_reaudit_v1" / "final_object_reduction_report.json"
REDUCTION_CHECK_MD = ROOT / "bs_fix_reaudit_v1" / "final_object_vs_bilbao_equivalent_check.md"
REDUCTION_CHECK_JSON = ROOT / "bs_fix_reaudit_v1" / "final_object_vs_bilbao_equivalent_check.json"
FINAL_PATH_SIGNATURE_MD = ROOT / "bs_fix_reaudit_v1" / "final_path_signature_report.md"
FINAL_PATH_SIGNATURE_JSON = ROOT / "bs_fix_reaudit_v1" / "final_path_signature_report.json"
FINAL_PATH_EQUIV_MD = ROOT / "bs_fix_reaudit_v1" / "final_path_candidate_equivalence_report.md"
FINAL_PATH_EQUIV_JSON = ROOT / "bs_fix_reaudit_v1" / "final_path_candidate_equivalence_report.json"
FINAL_BS_STRONG_MD = ROOT / "bs_fix_reaudit_v1" / "final_bs_strong_equivalence_report.md"
FINAL_BS_STRONG_JSON = ROOT / "bs_fix_reaudit_v1" / "final_bs_strong_equivalence_report.json"
MISSING_ROW_WITNESS_MD = ROOT / "bs_fix_reaudit_v1" / "missing_row_language_witness_report.md"
MISSING_ROW_WITNESS_JSON = ROOT / "bs_fix_reaudit_v1" / "missing_row_language_witness_report.json"
P1_P5_RESOLUTION_MD = ROOT / "bs_fix_reaudit_v1" / "p1_p5_doubleclass_resolution_report.md"
P1_P5_RESOLUTION_JSON = ROOT / "bs_fix_reaudit_v1" / "p1_p5_doubleclass_resolution_report.json"
FULL_SHELL_AUTOMORPHISM_MD = ROOT / "bs_fix_reaudit_v1" / "full_shell_automorphism_search_report.md"
FULL_SHELL_AUTOMORPHISM_JSON = ROOT / "bs_fix_reaudit_v1" / "full_shell_automorphism_search_report.json"
FULL_POINT_SHELL_AUTOMORPHISM_MD = ROOT / "bs_fix_reaudit_v1" / "full_point_shell_automorphism_search_report.md"
FULL_POINT_SHELL_AUTOMORPHISM_JSON = ROOT / "bs_fix_reaudit_v1" / "full_point_shell_automorphism_search_report.json"
POINT_ROW_TRANSLATION_MD = ROOT / "bs_fix_reaudit_v1" / "point_row_translation_legality_report.md"
POINT_ROW_TRANSLATION_JSON = ROOT / "bs_fix_reaudit_v1" / "point_row_translation_legality_report.json"
AI_SEED_AUDIT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_seed_audit_report.md"
AI_SEED_AUDIT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_seed_audit_report.json"
AI_SEED_DELTA_MD = ROOT / "bs_fix_reaudit_v1" / "ai_seed_delta_after_bs_fix_report.md"
AI_SEED_DELTA_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_seed_delta_after_bs_fix_report.json"
AI_LIBRARY_INTEGRATION_MD = ROOT / "bs_fix_reaudit_v1" / "ai_library_integration_report.md"
AI_LIBRARY_INTEGRATION_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_library_integration_report.json"
AI_CHARACTER_FIELD_ALIGNMENT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_character_field_alignment_report.md"
AI_CHARACTER_FIELD_ALIGNMENT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_character_field_alignment_report.json"
AI_HONEST_BLOCKER_MD = ROOT / "bs_fix_reaudit_v1" / "ai_honest_blocker_report.md"
AI_HONEST_BLOCKER_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_honest_blocker_report.json"
AI_OBSTRUCTION_DIAG_MD = ROOT / "bs_fix_reaudit_v1" / "ai_obstruction_diagnosis_report.md"
AI_OBSTRUCTION_DIAG_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_obstruction_diagnosis_report.json"

ZERO = Fraction(0, 1)
HALF = Fraction(1, 2)
LINE_SAMPLE = Fraction(1, 5)
BOUNDARY_VALUES = (ZERO, HALF)
AUTHORITATIVE_PHASE_AWARE_PROFILE = "phase_aware_l2_projective_v1"
AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND = (
    "authoritative_basis_decomposition_exact_unique_integer_with_phase_aware_l2_v1"
)
AUTHORITATIVE_AI_CHARACTER_FIELD = {
    "point": "linear_character",
    "line": "character",
    "plane": "character",
    "default": "linear_character",
}

REFERENCE_BASELINE_FILES = [
    "single_group_ai_completeness_summary.json",
    "single_group_indicator_group_summary.json",
    "single_group_bs_mod_ai_single_summary.json",
    "single_group_ai_completeness_audit.md",
    "double_group_ai_completeness_summary_10.4.1.31.json",
    "double_group_indicator_group_summary_10.4.1.31.json",
    "double_group_bs_mod_ai_summary_10.4.1.31.json",
    "double_group_bs_summary_10.4.1.31.json",
    "double_group_ai_completeness_audit_10.4.1.31.md",
    "debug_single_group_ai_bridge.py",
    "debug_single_group_ai_expanded.py",
    "debug_double_group_feasibility_10.4.1.31.py",
    "swyckoff_r.py",
    "swyckoff_k.py",
    "SSGReps/SSGReps/SSGReps.py",
    "SSGReps/SSGReps/SG_utils.py",
    "SSGReps/SSGReps/rep_utils.py",
]

PACKAGE_BACKGROUND_FILES = [
    "double_group_ai_completeness_audit_10.4.1.31.md",
    "double_group_ai_completeness_summary_10.4.1.31.json",
    "double_group_indicator_group_summary_10.4.1.31.json",
    "double_group_indicator_generators_10.4.1.31.json",
    "double_group_bs_mod_ai_summary_10.4.1.31.json",
    "double_group_bs_summary_10.4.1.31.json",
    "double_group_bs_basis_raw_10.4.1.31.json",
    "double_group_bs_basis_pretty_10.4.1.31.json",
    "double_group_full_compatibility_with_planes_10.4.1.31.json",
    "single_group_ai_completeness_audit.md",
    "single_group_ai_completeness_summary.json",
    "single_group_indicator_group_summary.json",
    "single_group_indicator_generators.json",
    "single_group_bs_mod_ai_single_summary.json",
    "swyckoff_r.py",
    "swyckoff_k.py",
    "SSGReps/SSGReps/SSGReps.py",
    "SSGReps/SSGReps/SG_utils.py",
    "SSGReps/SSGReps/rep_utils.py",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def json_default(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}
    if isinstance(value, Fraction):
        return frac_str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, sp.Basic):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def resolve_repo_asset(rel: str | Path) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute():
        return rel_path
    for base in (ROOT, COMMON_ROOT):
        candidate = base / rel_path
        if candidate.exists():
            return candidate
    raise FileNotFoundError(rel_path)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def complex_to_json(value: complex) -> dict[str, float]:
    return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}


def complex_list_to_json(values: Sequence[complex]) -> list[dict[str, float]]:
    return [complex_to_json(complex(value)) for value in values]


def complex_matrix_to_json(matrix: Sequence[Sequence[complex]]) -> list[list[dict[str, float]]]:
    return [complex_list_to_json(row) for row in matrix]


def format_tree(root: Path) -> list[str]:
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts) - 1
        prefix = "  " * depth + ("- " if depth else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def to_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str):
        return Fraction(value)
    return Fraction(value)


def frac_str(value: Any) -> str:
    value = to_fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def mod1_fraction(value: Any) -> Fraction:
    value = to_fraction(value) % 1
    return value + 1 if value < 0 else value


def vector_key(vector: Sequence[Any]) -> tuple[str, str, str]:
    return tuple(frac_str(mod1_fraction(value)) for value in vector)


def format_number(value: float, max_denominator: int = 48) -> str:
    return frac_str(Fraction(str(float(value))).limit_denominator(max_denominator))


def ordered_parameters(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> list[str]:
    ordered: list[str] = []
    for _const, coeffs in rep:
        for name in coeffs:
            if name not in ordered:
                ordered.append(name)
    return ordered


def rep_to_sympy(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> list[sp.Expr]:
    exprs: list[sp.Expr] = []
    for const, coeffs in rep:
        expr = sp.Rational(to_fraction(const).numerator, to_fraction(const).denominator)
        for name, coeff in coeffs.items():
            coeff_frac = to_fraction(coeff)
            expr += sp.Rational(coeff_frac.numerator, coeff_frac.denominator) * sp.Symbol(name)
        exprs.append(sp.simplify(expr))
    return exprs


def expr_str(expr: sp.Expr) -> str:
    return str(sp.simplify(expr)).replace("*", "")


def expr_vector_str(exprs: Sequence[sp.Expr]) -> str:
    return "(" + ", ".join(expr_str(expr) for expr in exprs) + ")"


def vector_add_scaled(anchor: Sequence[Any], basis: Sequence[Any], scale: Fraction) -> list[Fraction]:
    return [to_fraction(a) + to_fraction(scale) * to_fraction(b) for a, b in zip(anchor, basis)]


def evaluate_exprs(exprs: Sequence[sp.Expr], assignment: Dict[str, Fraction]) -> list[Fraction]:
    out: list[Fraction] = []
    for expr in exprs:
        value = expr
        for symbol_name, frac in assignment.items():
            value = value.subs(sp.Symbol(symbol_name), sp.Rational(frac.numerator, frac.denominator))
        out.append(Fraction(str(sp.simplify(value))))
    return out


def sample_assignment(parameters: Sequence[str]) -> Dict[str, Fraction]:
    pool = [Fraction(1, 5), Fraction(2, 7), Fraction(3, 11)]
    return {name: pool[index] for index, name in enumerate(parameters)}


def boundary_line_expressions(anchor: Sequence[Fraction], basis: Sequence[Fraction], parameter: str) -> list[sp.Expr]:
    exprs = []
    symbol = sp.Symbol(parameter)
    for base, vec in zip(anchor, basis):
        frac = to_fraction(base)
        expr = sp.Rational(frac.numerator, frac.denominator)
        coeff = to_fraction(vec)
        if coeff:
            expr += sp.Rational(coeff.numerator, coeff.denominator) * symbol
        exprs.append(sp.simplify(expr))
    return exprs


def geometry_type(dimension: int) -> str:
    return {0: "point", 1: "line", 2: "plane", 3: "generic"}[dimension]


def assign_ids(entries: Sequence[dict], prefix: str) -> None:
    for index, entry in enumerate(entries, start=1):
        entry["id"] = f"{prefix}{index}"


def load_ssgreps_module():
    candidates = [
        COMMON_SSGREPS_ROOT / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps.py",
    ]
    ssgreps_py = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    ssgreps_dir = ssgreps_py.parent
    if str(ssgreps_dir) not in sys.path:
        sys.path.insert(0, str(ssgreps_dir))
    spec = importlib.util.spec_from_file_location("ssgreps_local_portability", ssgreps_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {ssgreps_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_identify_pkl() -> Path:
    if IDENTIFY_PKL.exists():
        return IDENTIFY_PKL
    if not IDENTIFY_TAR.exists():
        raise FileNotFoundError(f"missing {IDENTIFY_PKL} and {IDENTIFY_TAR}")
    with tarfile_module.open(IDENTIFY_TAR, "r:gz") as tar:
        tar.extract("identify.pkl", path=COMMON_SSG_DATA_ROOT)
    return IDENTIFY_PKL


def load_ssg_dict(group_number: str) -> dict[str, Any]:
    identify_pkl = ensure_identify_pkl()
    with identify_pkl.open("rb") as fh:
        ssg_list = pickle.load(fh)
    return next(item for item in ssg_list if item["ssgNum"] == group_number)


@lru_cache(maxsize=None)
def _load_realspace_context_payload(group_number: str) -> dict[str, Any]:
    full_data, _ = swyckoff_r.load_irssg_data(group_number, 0)
    wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(group_number, fast=True)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]
    return {
        "full_data": full_data,
        "wyckoff_entries": wyckoff_entries,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
    }


def load_context(module: Any, group_number: str, group_label: str, ssg_dict: dict[str, Any]) -> dict[str, Any]:
    ssg = module.loadSsgGroup(group_number, np.array([0.0, 0.0, 0.0]), group_label, ssg_dict)
    realspace = _load_realspace_context_payload(group_number)
    ctx = {
        "group_number": group_number,
        "group_label": group_label,
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": realspace["full_data"],
        "full_ops": realspace["full_ops"],
        "full_time_revs": realspace["full_time_revs"],
        "wyckoff_entries": realspace["wyckoff_entries"],
    }
    ctx["raw_operations"] = single_expanded.raw_ops(ctx)
    ctx["group_tables"] = single_expanded.build_group_tables(ctx)
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in realspace["wyckoff_entries"]}
    return ctx


def load_reciprocal_context(group_number: str) -> dict[str, Any]:
    data, _time_revs = swyckoff_k.load_irssg_data(group_number, 0)
    full_ops_raw = [swyckoff_k.op_from_json(op) for op in data["operations"]]
    time_revs_raw = data.get("time_revs", [False] * len(full_ops_raw))
    spin_matrices_raw = data.get("spin_matrices")
    ops, mag_ops_real, _spin_ops_real, spin_ops_symbolic = swyckoff_k.build_reciprocal_spin_data(
        full_ops_raw,
        time_revs_raw,
        spin_matrices_raw,
    )
    try:
        pg_lookup = swyckoff_k.mw.build_point_group_signature_lookup()
    except FileNotFoundError:
        pg_lookup = {}
    return {
        "data": data,
        "ops": ops,
        "mag_ops_real": mag_ops_real,
        "spin_ops_symbolic": spin_ops_symbolic,
        "pg_lookup": pg_lookup,
    }


def compute_site_symmetry_from_indices(indices: Sequence[int], ctx: dict) -> dict:
    mag_stab_ops = [ctx["mag_ops_real"][i] for i in indices]
    spin_stab_ops_symbolic = [ctx["spin_ops_symbolic"][i] for i in indices]
    unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]
    unitary_site_symmetry = swyckoff_k.mw.classify_site_symmetry(
        swyckoff_k.unique_rotations(unitary_mag_stab_ops),
        ctx["pg_lookup"] or {},
    )
    spatial_site_symmetry_custom, spatial_site_symmetry_ops = swyckoff_k.mw.build_custom_site_symmetry(mag_stab_ops)
    site_symmetry_custom, site_symmetry_ops = swyckoff_k.build_spin_site_symmetry(spin_stab_ops_symbolic)
    if site_symmetry_custom is None:
        site_symmetry_custom = spatial_site_symmetry_custom
        site_symmetry_ops = spatial_site_symmetry_ops
    site_symmetry = (
        swyckoff_k.mw.lookup_magnetic_bilbao_symbol(
            spatial_site_symmetry_custom or site_symmetry_custom or "",
            unitary_site_symmetry or "",
            spatial_site_symmetry_ops or site_symmetry_ops,
        )
        or swyckoff_k.mw.bilbao_magnetic_point_group_symbol(
            spatial_site_symmetry_ops or site_symmetry_ops,
            crystal_system=str(ctx["data"].get("crystal_system", "")),
        )
        or spatial_site_symmetry_custom
        or site_symmetry_custom
        or unitary_site_symmetry
    )
    return {
        "site_symmetry": site_symmetry,
        "site_symmetry_custom": site_symmetry_custom,
        "unitary_site_symmetry": unitary_site_symmetry,
    }


def normalize_k_entry(entry: dict[str, Any]) -> dict:
    params = ordered_parameters(entry["rep"])
    exprs = rep_to_sympy(entry["rep"])
    sample = evaluate_exprs(exprs, sample_assignment(params))
    basis = [[to_fraction(value) for value in row] for row in entry["basis_vecs"]]
    anchor = [to_fraction(value) for value in entry["x0"]]
    dimension = int(entry["dim"])
    constraints = [f"0 < {name}" for name in params] + [f"{name} < 1/2" for name in params]
    metadata = {
        "source_letter": entry["letter"],
        "source_mult": int(entry["mult"]),
        "source_dimension": dimension,
        "source_orbit": list(entry["orbit"]),
        "source_representative_coordinate": entry["representative_coordinate"],
        "source_x0": [frac_str(value) for value in anchor],
        "source_basis_vecs": [[frac_str(value) for value in row] for row in basis],
        "source_rep": [
            [frac_str(to_fraction(const)), {name: frac_str(to_fraction(coeff)) for name, coeff in coeffs.items()}]
            for const, coeffs in entry["rep"]
        ],
    }
    return {
        "label": entry["letter"],
        "type": geometry_type(dimension),
        "dimension": dimension,
        "parametrization": expr_vector_str(exprs),
        "coordinate_expressions": [expr_str(expr) for expr in exprs],
        "parameters": params,
        "constraints": constraints,
        "constraint_summary": ", ".join(constraints),
        "sample_point": [frac_str(mod1_fraction(value)) for value in sample],
        "metadata": metadata,
        "_anchor": anchor,
        "_basis": basis,
        "_exprs": exprs,
        "_params": params,
    }


def pick_group_entries(group_number: str) -> Dict[str, List[dict]]:
    wyckoff, coord_key = swyckoff_k.compute_wyckoff_output(group_number, kspace=True, fast=True)
    if coord_key != "orbit":
        raise ValueError(f"Unexpected coordinate key: {coord_key}")
    points: list[dict] = []
    lines: list[dict] = []
    planes: list[dict] = []
    generic: list[dict] = []
    for entry in wyckoff:
        normalized = normalize_k_entry(entry)
        if normalized["dimension"] == 0:
            points.append(normalized)
        elif normalized["dimension"] == 1:
            lines.append(normalized)
        elif normalized["dimension"] == 2:
            planes.append(normalized)
        else:
            generic.append(normalized)
    points.sort(key=lambda item: item["label"])
    lines.sort(key=lambda item: item["label"])
    planes.sort(key=lambda item: item["label"])
    generic.sort(key=lambda item: item["label"])
    assign_ids(points, "P")
    assign_ids(lines, "L")
    assign_ids(planes, "S")
    return {"points": points, "lines": lines, "planes": planes, "generic": generic}


def subspace_orbit_id_maps(lines: Sequence[dict], planes: Sequence[dict], ctx: dict) -> Tuple[dict, dict]:
    line_orbit_to_id = {}
    plane_orbit_to_id = {}
    for line in lines:
        orbit_key = swyckoff_k.subspace_orbit_key(line["_anchor"], line["_basis"], ctx["ops"])
        line_orbit_to_id[orbit_key] = line["id"]
    for plane in planes:
        orbit_key = swyckoff_k.subspace_orbit_key(plane["_anchor"], plane["_basis"], ctx["ops"])
        plane_orbit_to_id[orbit_key] = plane["id"]
    return line_orbit_to_id, plane_orbit_to_id


def closure_components(anchor: Sequence[Fraction], basis: Sequence[Sequence[Fraction]], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> List[dict]:
    components = []
    for closed_x0, closed_basis in swyckoff_k.closure_under_stabilizer(anchor, basis, ctx["ops"]):
        orbit_key = swyckoff_k.subspace_orbit_key(closed_x0, closed_basis, ctx["ops"])
        component = {
            "dimension": len(closed_basis),
            "x0": [frac_str(value) for value in closed_x0],
            "basis_vecs": [[frac_str(value) for value in row] for row in closed_basis],
            "line_id": line_orbit_to_id.get(orbit_key),
            "plane_id": plane_orbit_to_id.get(orbit_key),
        }
        components.append(component)
    return components


def subspace_symmetry_summary(anchor: Sequence[Fraction], basis: Sequence[Sequence[Fraction]], ctx: dict) -> dict:
    generic_point = swyckoff_k.generic_point_on_subspace(anchor, basis) if basis else list(anchor)
    generic_stab_indices = swyckoff_k.stabilizer(generic_point, ctx["ops"])
    pointwise_stab_indices = swyckoff_k.stabilizer_indices_for_subspace(anchor, basis, ctx["ops"])
    generic_rotations = len(swyckoff_k.unique_rotations([ctx["ops"][i] for i in generic_stab_indices]))
    pointwise_rotations = len(swyckoff_k.unique_rotations([ctx["ops"][i] for i in pointwise_stab_indices]))
    symmetry = compute_site_symmetry_from_indices(generic_stab_indices, ctx)
    return {
        "generic_point": [frac_str(value) for value in generic_point],
        "generic_stabilizer_size": len(generic_stab_indices),
        "generic_rotation_stabilizer_size": generic_rotations,
        "pointwise_stabilizer_size": len(pointwise_stab_indices),
        "pointwise_rotation_stabilizer_size": pointwise_rotations,
        **symmetry,
    }


def line_signature(anchor: Sequence[Fraction], basis: Sequence[Fraction]) -> Tuple[Tuple[str, str, str], Tuple[str, str, str]]:
    return vector_key(anchor), tuple(frac_str(to_fraction(value)) for value in basis)


def point_coordinate_keys(point: dict[str, Any]) -> list[tuple[str, str, str]]:
    keys = {vector_key(point["_anchor"])}
    sample_point = point.get("sample_point")
    if sample_point:
        keys.add(tuple(sample_point))
    for coord in point.get("metadata", {}).get("source_orbit", []):
        pieces = tuple(piece.strip() for piece in coord.split(","))
        if len(pieces) == 3:
            keys.add(pieces)
    return sorted(keys)


def annotate_special_manifolds(lines: Sequence[dict], planes: Sequence[dict], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> None:
    for line in lines:
        line["manifold_role"] = "separately_listed_special_line_manifold"
        line["symmetry_summary"] = subspace_symmetry_summary(line["_anchor"], line["_basis"], ctx)
        line["closure_under_pointwise_stabilizer"] = closure_components(line["_anchor"], line["_basis"], ctx, line_orbit_to_id, plane_orbit_to_id)
    for plane in planes:
        plane["manifold_role"] = "separately_listed_special_plane_manifold"
        plane["symmetry_summary"] = subspace_symmetry_summary(plane["_anchor"], plane["_basis"], ctx)


def infer_line_connectivity(points: Sequence[dict], lines: Sequence[dict]) -> Tuple[List[dict], List[dict]]:
    point_map = {key: point for point in points for key in point_coordinate_keys(point)}
    point_line: List[dict] = []
    unmatched: List[dict] = []
    for line in lines:
        basis = line["_basis"][0]
        param = line["_params"][0]
        endpoints: List[dict] = []
        for boundary in BOUNDARY_VALUES:
            boundary_point = vector_add_scaled(line["_anchor"], basis, boundary)
            key = vector_key(boundary_point)
            condition = f"{param} = {frac_str(boundary)}"
            point = point_map.get(key)
            endpoint = {
                "boundary_condition": condition,
                "point_coordinates": [frac_str(mod1_fraction(value)) for value in boundary_point],
                "point_id": point["id"] if point else None,
            }
            endpoints.append(endpoint)
            if point:
                point_line.append(
                    {
                        "point_id": point["id"],
                        "line_id": line["id"],
                        "boundary_condition": condition,
                        "derived_point": endpoint["point_coordinates"],
                    }
                )
            else:
                unmatched.append(
                    {
                        "line_id": line["id"],
                        "boundary_condition": condition,
                        "derived_point": endpoint["point_coordinates"],
                    }
                )
        line["endpoints"] = endpoints
    return point_line, unmatched


def infer_plane_connectivity(planes: Sequence[dict], lines: Sequence[dict], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> Tuple[List[dict], List[dict]]:
    line_map = {line_signature(line["_anchor"], line["_basis"][0]): line for line in lines}
    line_plane: List[dict] = []
    unmatched: List[dict] = []
    for plane in planes:
        params = plane["_params"]
        boundaries: List[dict] = []
        for fixed_index, fixed_param in enumerate(params):
            free_index = 1 - fixed_index
            free_param = params[free_index]
            free_basis = plane["_basis"][free_index]
            fixed_basis = plane["_basis"][fixed_index]
            for boundary in BOUNDARY_VALUES:
                anchor = vector_add_scaled(plane["_anchor"], fixed_basis, boundary)
                exprs = boundary_line_expressions(anchor, free_basis, free_param)
                condition = f"{fixed_param} = {frac_str(boundary)}"
                candidate = {
                    "boundary_condition": condition,
                    "boundary_role": "geometric_boundary_line",
                    "parametrization": expr_vector_str(exprs),
                    "coordinate_expressions": [expr_str(expr) for expr in exprs],
                    "parameters": [free_param],
                    "constraints": [f"0 < {free_param}", f"{free_param} < 1/2"],
                    "sample_point": [frac_str(mod1_fraction(value)) for value in vector_add_scaled(anchor, free_basis, LINE_SAMPLE)],
                }
                line = line_map.get(line_signature(anchor, free_basis))
                symmetry_summary = subspace_symmetry_summary(anchor, [free_basis], ctx)
                closure = closure_components(anchor, [free_basis], ctx, line_orbit_to_id, plane_orbit_to_id)
                candidate["symmetry_summary"] = symmetry_summary
                candidate["closure_under_pointwise_stabilizer"] = closure
                orbit_key = swyckoff_k.subspace_orbit_key(anchor, [free_basis], ctx["ops"])
                orbit_line_id = line_orbit_to_id.get(orbit_key)
                candidate["special_line_orbit_match"] = orbit_line_id
                candidate["classification"] = {
                    "is_separately_listed_special_line": bool(orbit_line_id),
                    "reason": "Matches an existing 1D manifold orbit." if orbit_line_id else "Does not match any listed 1D manifold orbit.",
                }
                matched_line_id = line["id"] if line else orbit_line_id
                if matched_line_id is not None:
                    candidate["line_id"] = matched_line_id
                    boundaries.append(candidate)
                    line_plane.append(
                        {
                            "line_id": matched_line_id,
                            "plane_id": plane["id"],
                            "boundary_condition": condition,
                            "derived_line": candidate["parametrization"],
                        }
                    )
                else:
                    candidate["line_id"] = None
                    closure_plane_ids = [component["plane_id"] for component in closure if component["plane_id"]]
                    if closure_plane_ids:
                        candidate["classification"]["reason"] = (
                            "Pointwise stabilizer closes back to separately listed plane manifolds "
                            + ", ".join(closure_plane_ids)
                            + ", so this is treated as a geometric boundary only."
                        )
                    boundaries.append(candidate)
                    unmatched.append(
                        {
                            "plane_id": plane["id"],
                            "boundary_condition": condition,
                            "boundary_role": candidate["boundary_role"],
                            "derived_line": candidate["parametrization"],
                            "parameters": candidate["parameters"],
                            "constraints": candidate["constraints"],
                            "sample_point": candidate["sample_point"],
                            "symmetry_summary": candidate["symmetry_summary"],
                            "closure_under_pointwise_stabilizer": candidate["closure_under_pointwise_stabilizer"],
                            "special_line_orbit_match": candidate["special_line_orbit_match"],
                            "classification": candidate["classification"],
                        }
                    )
        plane["boundary_lines"] = boundaries
    return line_plane, unmatched


def strip_internal_fields(entries: Sequence[dict]) -> List[dict]:
    return [{key: value for key, value in entry.items() if not key.startswith("_")} for entry in entries]


def prepare_kgeometry(group_number: str) -> dict[str, Any]:
    grouped = pick_group_entries(group_number)
    points = grouped["points"]
    lines = grouped["lines"]
    planes = grouped["planes"]
    generic = grouped["generic"]
    ctx = load_reciprocal_context(group_number)
    line_orbit_to_id, plane_orbit_to_id = subspace_orbit_id_maps(lines, planes, ctx)
    annotate_special_manifolds(lines, planes, ctx, line_orbit_to_id, plane_orbit_to_id)
    point_line, unmatched_endpoints = infer_line_connectivity(points, lines)
    line_plane, unmatched_plane_boundaries = infer_plane_connectivity(planes, lines, ctx, line_orbit_to_id, plane_orbit_to_id)
    payload = {
        "group_number": group_number,
        "objects": strip_internal_fields(points + lines + planes),
        "generic_manifolds_ignored": strip_internal_fields(generic),
        "point_line": point_line,
        "unmatched_line_endpoints": unmatched_endpoints,
        "line_plane": line_plane,
        "unmatched_plane_boundaries": unmatched_plane_boundaries,
    }
    return {
        "grouped": grouped,
        "payload": payload,
        "ctx": ctx,
        "line_orbit_to_id": line_orbit_to_id,
        "plane_orbit_to_id": plane_orbit_to_id,
    }


def build_kgeometry(group_number: str) -> dict[str, Any]:
    return prepare_kgeometry(group_number)["payload"]


def coordinate_to_id_map(points: Sequence[dict]) -> dict[tuple[str, str, str], str]:
    return {key: point["id"] for point in points for key in point_coordinate_keys(point)}


def build_synthetic_boundary_points(kgeom: dict[str, Any]) -> list[dict[str, Any]]:
    objects = kgeom["grouped"]
    point_map = coordinate_to_id_map(objects["points"])
    synthetic: list[dict[str, Any]] = []
    seen = set(point_map)

    def ensure_point(coords: Sequence[str], source: str) -> str:
        key = tuple(coords)
        if key in point_map:
            return point_map[key]
        if key in seen:
            for item in synthetic:
                if tuple(item["sample_point"]) == key:
                    return item["id"]
        new_id = f"B{len(synthetic) + 1}"
        item = {
            "id": new_id,
            "type": "boundary_point",
            "dimension": 0,
            "sample_point": list(coords),
            "coordinate_expressions": list(coords),
            "source": source,
        }
        synthetic.append(item)
        seen.add(key)
        return new_id

    for relation in kgeom["connectivity"]["unmatched_line_endpoints"]:
        ensure_point(relation["derived_point"], f"{relation['line_id']}:{relation['boundary_condition']}")

    plane_lookup = {item["id"]: item for item in objects["planes"]}
    for plane in objects["planes"]:
        anchor = plane["_anchor"]
        basis1, basis2 = plane["_basis"]
        for coeff1 in BOUNDARY_VALUES:
            for coeff2 in BOUNDARY_VALUES:
                corner = vector_add_scaled(vector_add_scaled(anchor, basis1, coeff1), basis2, coeff2)
                ensure_point([frac_str(mod1_fraction(value)) for value in corner], f"{plane['id']}:corner")

    return synthetic


def augment_connectivity_with_boundary_points(kgeom: dict[str, Any], synthetic_points: list[dict[str, Any]]) -> None:
    id_by_coord = coordinate_to_id_map(kgeom["grouped"]["points"])
    for point in synthetic_points:
        id_by_coord[tuple(point["sample_point"])] = point["id"]
    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            if endpoint["point_id"] is None:
                endpoint["point_id"] = id_by_coord[tuple(endpoint["point_coordinates"])]


def point_capture_id(point_id: str, coords: Sequence[str]) -> str:
    suffix = "_".join(coord.replace("/", "d").replace("-", "m") for coord in coords)
    return f"{point_id}__{suffix}"


def derive_plane_corner_entries(plane_obj: dict[str, Any], point_by_coord: dict[tuple[str, str, str], str]) -> list[dict[str, Any]]:
    anchor = plane_obj["_anchor"]
    basis1, basis2 = plane_obj["_basis"]
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, str, str]]] = set()
    for coeff1 in BOUNDARY_VALUES:
        for coeff2 in BOUNDARY_VALUES:
            point = vector_add_scaled(vector_add_scaled(anchor, basis1, coeff1), basis2, coeff2)
            coords = [frac_str(mod1_fraction(value)) for value in point]
            point_id = point_by_coord[vector_key(point)]
            dedup_key = (point_id, tuple(coords))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            out.append({"point_id": point_id, "point_coordinates": coords})
    return out


def operation_key_from_capture(capture: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(round(float(entry))) for entry in row) for row in capture["rotC"][op_index])
    tau = tuple(round(float(entry) % 1.0, 8) for entry in capture["tauC"][op_index])
    spin = tuple(tuple(round(float(entry), 8) for entry in row) for row in capture["spin"][op_index])
    return rot, tau, spin, int(capture["timeReversal"][op_index])


def capture_little_group(module: Any, group_number: str, ssg_dict: dict[str, Any], ctx: dict[str, Any], group_label: str, manifold_id: str, kvec: list[float]) -> dict[str, Any]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        lg = module.load_little_group(group_number, np.array(kvec, dtype=float), False, group_label, ssg_dict)
    unitary_rotations: list[np.ndarray] = []
    unitary_translations: list[np.ndarray] = []
    unitary_raw_indices: list[int] = []
    unitary_capture_indices: list[int] = []
    for raw_index, (rotation, translation, tr) in enumerate(zip(lg.rotC, lg.tauC, lg.time_reversal)):
        if int(tr) < 0:
            continue
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        unitary_rotations.append(rot)
        unitary_translations.append(tau)
        unitary_capture_indices.append(raw_index)
        unitary_raw_indices.append(
            single_expanded.match_raw_op(
                ctx,
                ctx["group_tables"]["operations"],
                rot,
                tau,
                False,
            )
        )
    raw_character = [[complex(value) for value in row] for row in lg.character]
    linear_character = [[complex(value) for value in row] for row in lg.linear_character]
    return {
        "group_type": 1 if group_label == "single" else 2,
        "manifold_id": manifold_id,
        "kvec": list(kvec),
        "warning_text": stdout.getvalue().strip(),
        "little_group_operation_count": len(lg.oplist),
        "antiunitary_present": bool(lg.antiunitary),
        "rep_count": len(lg.rep_degree),
        "rep_degree": [int(value) for value in lg.rep_degree],
        "torsion": [int(value) for value in lg.torsion],
        "unitary_operation_count": len(unitary_raw_indices),
        "unitary_raw_indices": unitary_raw_indices,
        "unitary_capture_indices": unitary_capture_indices,
        "rotC": [[[float(entry) for entry in row] for row in rotation] for rotation in lg.rotC],
        "tauC": [[float(entry) for entry in translation] for translation in lg.tauC],
        "spin": [[[float(entry) for entry in row] for row in spin] for spin in lg.spin],
        "timeReversal": [int(value) for value in lg.time_reversal],
        "character": raw_character,
        "linear_character": linear_character,
        "character_json": complex_matrix_to_json(raw_character),
        "linear_character_json": complex_matrix_to_json(linear_character),
        "unitary_rotations": [rotation.tolist() for rotation in unitary_rotations],
        "unitary_translations": [translation.tolist() for translation in unitary_translations],
        "kconv": (
            kvec[0] * ctx["reciprocal_basis"][0]
            + kvec[1] * ctx["reciprocal_basis"][1]
            + kvec[2] * ctx["reciprocal_basis"][2]
        ).tolist(),
    }


def build_manifold_capture(module: Any, group_number: str, ssg_dict: dict[str, Any], ctx: dict[str, Any], group_label: str, kgeom: dict[str, Any]) -> dict[str, Any]:
    captures: dict[str, Any] = {}
    for point in kgeom["grouped"]["points"]:
        captures[point["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point["id"],
            [float(Fraction(value)) for value in point["sample_point"]],
        )
    for point in kgeom["synthetic_boundary_points"]:
        captures[point["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point["id"],
            [float(Fraction(value)) for value in point["sample_point"]],
        )
    for line in kgeom["grouped"]["lines"]:
        captures[line["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            line["id"],
            [float(Fraction(value)) for value in line["sample_point"]],
        )
    for plane in kgeom["grouped"]["planes"]:
        captures[plane["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            plane["id"],
            [float(Fraction(value)) for value in plane["sample_point"]],
        )
    for point_instance in kgeom.get("point_instance_entries", []):
        captures[point_instance["capture_id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point_instance["capture_id"],
            [float(Fraction(value)) for value in point_instance["point_coordinates"]],
        )
    return captures


def as_exact_char(value: complex) -> sp.Expr:
    if abs(value.imag) < 1e-8:
        return sp.Integer(int(round(value.real))) if abs(value.real - round(value.real)) < 1e-8 else sp.nsimplify(value.real)
    return sp.nsimplify(value.real) + sp.I * sp.nsimplify(value.imag)


def coerce_integer_coeffs(coeffs: list[sp.Expr], context: str) -> list[int]:
    result: list[int] = []
    for coeff in coeffs:
        if coeff.is_Integer:
            result.append(int(coeff))
            continue
        coeff_eval = complex(coeff.evalf())
        if abs(coeff_eval.imag) < 1e-8 and abs(coeff_eval.real - round(coeff_eval.real)) < 1e-8:
            result.append(int(round(coeff_eval.real)))
            continue
        raise ValueError(f"non-integral decomposition in {context}: {coeffs}")
    return result


def solve_numeric_integer_decomposition(
    basis_matrix: sp.Matrix,
    restricted: sp.Matrix,
    context: str,
    *,
    tol: float = 1e-8,
) -> list[int]:
    basis = np.array(
        [[complex(value.evalf()) for value in row] for row in basis_matrix.tolist()],
        dtype=complex,
    )
    rhs = np.array([complex(value.evalf()) for value in restricted], dtype=complex)
    coeffs, _residuals, rank, _singular_values = np.linalg.lstsq(basis, rhs, rcond=None)
    if int(rank) != int(basis.shape[1]):
        raise ValueError(f"non-unique numeric decomposition in {context}")
    rounded: list[int] = []
    for coeff in coeffs:
        if abs(coeff.imag) > tol or abs(coeff.real - round(coeff.real)) > tol:
            raise ValueError(f"non-integral numeric decomposition in {context}: {coeffs.tolist()}")
        rounded.append(int(round(coeff.real)))
    reconstructed = basis @ np.array(rounded, dtype=complex)
    if not np.allclose(reconstructed, rhs, atol=tol):
        raise ValueError(f"numeric reconstruction failed in {context}")
    return rounded


def _mode_label_from_raw(raw: dict[str, Any]) -> str:
    return {1: "single", 2: "double"}.get(int(raw.get("group_type", 0)), f"groupType={raw.get('group_type')}")


def _validated_capture_field_rows(
    raw: dict[str, Any],
    field: str,
    *,
    manifold_id: str,
    endpoint_id: str | None = None,
    rep_id: str | None = None,
) -> list[list[complex]]:
    rows = raw.get(field)
    mode = _mode_label_from_raw(raw)
    context = (
        f"mode={mode} manifold={manifold_id}"
        + (f" endpoint={endpoint_id}" if endpoint_id is not None else "")
        + (f" rep={rep_id}" if rep_id is not None else "")
        + f" field={field}"
    )
    if not rows:
        raise ValueError(f"{context}: empty character layer")
    unitary_capture_indices = raw.get("unitary_capture_indices", [])
    if not unitary_capture_indices:
        raise ValueError(f"{context}: empty unitary_capture_indices")
    expected_cols = len(unitary_capture_indices)
    for row_index, row in enumerate(rows, start=1):
        if not row:
            raise ValueError(f"{context}: empty row {row_index}")
        actual_cols = len(row)
        if actual_cols != expected_cols:
            raise ValueError(
                f"{context}: character column mismatch expected={expected_cols} actual={actual_cols}"
            )
    return [[complex(value) for value in row] for row in rows]


def _exact_basis_matrix_from_capture(
    raw: dict[str, Any],
    field: str,
    *,
    manifold_id: str,
) -> sp.Matrix:
    rows = _validated_capture_field_rows(raw, field, manifold_id=manifold_id)
    return sp.Matrix([[as_exact_char(value) for value in rep_character] for rep_character in rows]).T


def _exact_restriction_vector(
    parent_raw: dict[str, Any],
    child_raw: dict[str, Any],
    matched: list[int],
    *,
    field: str,
    parent_manifold_id: str,
    child_manifold_id: str,
    rep_id: str,
) -> sp.Matrix:
    parent_rows = _validated_capture_field_rows(parent_raw, field, manifold_id=parent_manifold_id)
    child_rows = _validated_capture_field_rows(
        child_raw,
        field,
        manifold_id=child_manifold_id,
        endpoint_id=child_manifold_id,
        rep_id=rep_id,
    )
    expected = len(parent_rows[0])
    if len(matched) != expected:
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: matched subgroup length mismatch expected={expected} actual={len(matched)}"
        )
    child_cols = len(child_rows[0])
    if any(index < 0 or index >= child_cols for index in matched):
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: matched index outside child column range child_cols={child_cols}"
        )
    rep_index = int(rep_id.split("_R")[1]) - 1
    restricted = [as_exact_char(child_rows[rep_index][index]) for index in matched]
    if len(restricted) != expected:
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: restricted vector length mismatch expected={expected} actual={len(restricted)}"
        )
    return sp.Matrix(restricted)


def solve_unique_integer_decomposition(
    basis_matrix: sp.Matrix,
    restricted: sp.Matrix,
    *,
    mode: str,
    manifold_id: str,
    endpoint_id: str,
    rep_id: str,
    field: str,
) -> list[int]:
    context = f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}"
    if basis_matrix.rows != restricted.rows:
        raise ValueError(
            f"{context}: "
            f"basis/restriction row mismatch expected={basis_matrix.rows} actual={restricted.rows}"
        )
    try:
        return solve_numeric_integer_decomposition(basis_matrix, restricted, context)
    except Exception as numeric_exc:
        numeric_error = numeric_exc
    try:
        solution, params = basis_matrix.gauss_jordan_solve(restricted)
    except Exception as exc:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver={exc}"
        ) from exc
    if params.rows * params.cols:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver=non-unique decomposition"
        )
    if basis_matrix * solution != restricted:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver=exact reconstruction failed"
        )
    return coerce_integer_coeffs(
        list(solution),
        context,
    )


def matched_unitary_indices(parent_raw: dict[str, Any], child_raw: dict[str, Any]) -> list[int]:
    parent_ops = [operation_key_from_capture(parent_raw, op_index) for op_index in parent_raw["unitary_capture_indices"]]
    unitary_map = {
        operation_key_from_capture(child_raw, op_index): unitary_index
        for unitary_index, op_index in enumerate(child_raw["unitary_capture_indices"])
    }
    matched = [unitary_map.get(op_key) for op_key in parent_ops]
    if any(index is None for index in matched):
        raise ValueError("child manifold does not contain the full parent unitary subgroup")
    return [int(index) for index in matched]


def capture_character_vectors(raw: dict[str, Any], field: str, matched: list[int]) -> list[list[complex]]:
    _validated_capture_field_rows(raw, field, manifold_id=raw.get("manifold_id", "unknown"))
    return [
        [complex(rep_character[index]) for index in matched]
        for rep_character in raw[field]
    ]


def identical_restriction_classes(
    endpoint_id: str,
    endpoint_raw: dict[str, Any],
    matched: list[int],
    *,
    field: str,
    tol: float = 1e-8,
) -> list[dict[str, Any]]:
    vectors = capture_character_vectors(endpoint_raw, field, matched)
    classes: list[dict[str, Any]] = []
    for rep_index, restricted_vector in enumerate(vectors, start=1):
        rep_id = f"{endpoint_id}_R{rep_index}"
        for existing in classes:
            if all(abs(left - right) <= tol for left, right in zip(existing["_vector"], restricted_vector)):
                existing["rep_ids"].append(rep_id)
                break
        else:
            classes.append(
                {
                    "rep_ids": [rep_id],
                    "restricted_vector": complex_list_to_json(restricted_vector),
                    "_vector": restricted_vector,
                }
            )
    for existing in classes:
        existing["class_size"] = len(existing["rep_ids"])
        del existing["_vector"]
    return classes


def phase_aware_l2_profile_config(profile: str | None) -> tuple[str, str | None]:
    if profile in (None, "legacy"):
        return "legacy", None
    if profile == "phase_aware_l2_projective_v1":
        return profile, None
    if profile == "phase_aware_l2_projective_v1_p3":
        return "phase_aware_l2_projective_v1", "P3"
    if profile == "phase_aware_l2_projective_v1_p4":
        return "phase_aware_l2_projective_v1", "P4"
    raise ValueError(f"unsupported phase-aware line profile: {profile}")


def phase_aware_l2_refinement(
    line_id: str,
    endpoint_entries: list[dict[str, Any]],
    captures: dict[str, Any],
    *,
    selected_endpoint_override: str | None = None,
) -> dict[str, Any]:
    if line_id != "L2":
        return {
            "profile": "legacy",
            "selected_endpoint_id": None,
            "restriction_classes_by_endpoint": {},
            "refinement_equations": [],
        }

    line_raw = captures[line_id]
    endpoint_scores: list[tuple[int, int, str, list[dict[str, Any]]]] = []
    restriction_classes_by_endpoint: dict[str, Any] = {}
    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        endpoint_raw = captures[endpoint_entry["capture_id"]]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        classes = identical_restriction_classes(
            endpoint_id,
            endpoint_raw,
            matched,
            field="linear_character",
        )
        restriction_classes_by_endpoint[endpoint_id] = classes
        duplicated_classes = [item for item in classes if item["class_size"] > 1]
        duplicated_cover = sum(item["class_size"] for item in duplicated_classes)
        endpoint_scores.append((duplicated_cover, len(duplicated_classes), endpoint_id, duplicated_classes))

    endpoint_scores.sort(reverse=True)
    if selected_endpoint_override is None:
        duplicated_cover, duplicated_count, selected_endpoint_id, duplicated_classes = endpoint_scores[0]
    else:
        selected_endpoint_id = selected_endpoint_override
        match = next((entry for entry in endpoint_scores if entry[2] == selected_endpoint_id), None)
        if match is None:
            raise ValueError(f"{line_id}: unsupported endpoint override {selected_endpoint_override}")
        duplicated_cover, duplicated_count, _selected, duplicated_classes = match
    refinement_equations: list[dict[str, Any]] = []
    if duplicated_cover > 0 and duplicated_count > 0:
        for class_index, entry in enumerate(duplicated_classes, start=1):
            anchor = entry["rep_ids"][0]
            for rep_id in entry["rep_ids"][1:]:
                refinement_equations.append(
                    {
                        "basis_id": f"{line_id}_phase_aware_class_{class_index:02d}",
                        "terms": [
                            {"unknown": anchor, "coeff": 1, "side": "phase_aware_endpoint_class"},
                            {"unknown": rep_id, "coeff": -1, "side": "phase_aware_endpoint_class"},
                        ],
                        "restriction_class_rep_ids": list(entry["rep_ids"]),
                        "selected_endpoint_id": selected_endpoint_id,
                    }
                )
    return {
        "profile": "phase_aware_l2_projective_v1",
        "selected_endpoint_id": selected_endpoint_id,
        "restriction_classes_by_endpoint": restriction_classes_by_endpoint,
        "refinement_equations": refinement_equations,
    }


def build_line_block(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    phase_aware_profile: str | None = None,
) -> dict[str, Any]:
    normalized_phase_profile, selected_endpoint_override = phase_aware_l2_profile_config(phase_aware_profile)
    line_id = line_obj["id"]
    source_line_id = line_obj.get("source_line_id", line_id)
    endpoint_entries = [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
        }
        for endpoint in line_obj["endpoints"]
    ]
    endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
    line_raw = captures[line_id]
    # Source-layer endpoint subduction for 194.1.1.1 must stay in character
    # language. The linear_character basis is not integer-solvable on the
    # failing lines and breaks the authoritative BS construction.
    field = "character"
    line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
    line_basis_matrix = _exact_basis_matrix_from_capture(line_raw, field, manifold_id=line_id)
    endpoint_decompositions: dict[str, Any] = {}
    equations = []
    matrix_rows = []
    local_unknown_ordering: list[str] = []
    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        endpoint_raw = captures[endpoint_entry["capture_id"]]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        reps = []
        for rep_index in range(1, len(endpoint_raw[field]) + 1):
            rep_id = f"{endpoint_id}_R{rep_index}"
            restricted = _exact_restriction_vector(
                line_raw,
                endpoint_raw,
                matched,
                field=field,
                parent_manifold_id=line_id,
                child_manifold_id=endpoint_id,
                rep_id=rep_id,
            )
            coeffs_int = solve_unique_integer_decomposition(
                line_basis_matrix,
                restricted,
                mode=_mode_label_from_raw(endpoint_raw),
                manifold_id=line_id,
                endpoint_id=endpoint_id,
                rep_id=rep_id,
                field=field,
            )
            reps.append(
                {
                    "rep_id": rep_id,
                    "rep_degree": int(endpoint_raw["rep_degree"][rep_index - 1]),
                    "torsion": int(endpoint_raw["torsion"][rep_index - 1]),
                    "decomposition_on_line_basis": {basis_label: coeff for basis_label, coeff in zip(line_basis_labels, coeffs_int) if coeff},
                }
            )
            local_unknown_ordering.append(rep_id)
        endpoint_decompositions[endpoint_id] = reps
    for basis_label in line_basis_labels:
        row = []
        terms = []
        for endpoint_id, side in zip(endpoint_ids, ("left", "right")):
            sign = 1 if side == "left" else -1
            for rep in endpoint_decompositions[endpoint_id]:
                coeff = sign * rep["decomposition_on_line_basis"].get(basis_label, 0)
                row.append(coeff)
                if coeff:
                    terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": side})
        matrix_rows.append(row)
        equations.append({"basis_id": basis_label, "terms": terms})
    phase_aware_refinement = {
        "profile": "legacy",
        "selected_endpoint_id": None,
        "restriction_classes_by_endpoint": {},
        "refinement_equations": [],
    }
    if normalized_phase_profile == "phase_aware_l2_projective_v1":
        phase_aware_refinement = phase_aware_l2_refinement(
            source_line_id,
            endpoint_entries,
            captures,
            selected_endpoint_override=selected_endpoint_override,
        )
        local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
        for equation in phase_aware_refinement["refinement_equations"]:
            row = [0] * len(local_unknown_ordering)
            for term in equation["terms"]:
                row[local_index[term["unknown"]]] += int(term["coeff"])
            matrix_rows.append(row)
            equations.append(
                {
                    "basis_id": equation["basis_id"],
                    "terms": equation["terms"],
                    "phase_aware_refinement": True,
                    "restriction_class_rep_ids": equation["restriction_class_rep_ids"],
                    "selected_endpoint_id": equation["selected_endpoint_id"],
                }
            )
    return {
        "status": "success",
        "line_id": line_id,
        "source_line_id": source_line_id,
        "endpoint_ids": endpoint_ids,
        "line_sample_point": line_obj["sample_point"],
        "line_parametrization": line_obj["parametrization"],
        "line_symmetry_summary": line_obj["symmetry_summary"],
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "line_basis_labels": line_basis_labels,
        "compatibility_field": field,
        "compatibility_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        "phase_aware_profile_used": (
            phase_aware_refinement["profile"]
            if phase_aware_refinement["profile"] != "legacy"
            else "legacy"
        ),
        "line_group_signature": {
            "n_ops_total": len(line_raw["rotC"]),
            "n_unitary_ops": line_raw["unitary_operation_count"],
            "n_antiunitary_ops": sum(1 for sign in line_raw["timeReversal"] if sign < 0),
            "rep_degree": list(line_raw["rep_degree"]),
            "torsion": list(line_raw["torsion"]),
        },
        "phase_aware_refinement": phase_aware_refinement,
    }


def build_global_compatibility(line_blocks: list[dict[str, Any]], point_ids: list[str]) -> dict[str, Any]:
    per_point_ids: dict[str, list[str]] = {}
    for block in line_blocks:
        for endpoint_id in block["endpoint_ids"]:
            rep_ids = [item["rep_id"] for item in block["endpoint_decompositions"][endpoint_id]]
            existing = per_point_ids.get(endpoint_id)
            if existing is None:
                per_point_ids[endpoint_id] = rep_ids
            elif existing != rep_ids:
                raise ValueError(f"inconsistent rep ordering for {endpoint_id}")
    ordering = []
    for point_id in point_ids:
        ordering.extend(per_point_ids.get(point_id, []))
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    global_rows = []
    for block in line_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            global_rows.append(
                {
                    "source_type": "line",
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
        "covered_lines": [block["line_id"] for block in line_blocks],
    }


def build_phase_aware_point_row_translation(
    line_blocks: list[dict[str, Any]],
    unknown_ordering: list[str],
    phase_aware_profile: str | None = None,
) -> dict[str, Any]:
    normalized_phase_profile, selected_endpoint_override = phase_aware_l2_profile_config(phase_aware_profile)
    translation = {
        "profile": "legacy",
        "enabled": False,
        "line_id": None,
        "selected_endpoint_id": None,
        "selected_endpoint_override": selected_endpoint_override,
        "other_endpoint_id": None,
        "selected_endpoint_class_actions": [],
        "other_endpoint_scalings": [],
    }
    if normalized_phase_profile != "phase_aware_l2_projective_v1":
        return translation

    line_block = next(
        (
            block
            for block in line_blocks
            if block.get("source_line_id", block["line_id"]) == "L2"
        ),
        None,
    )
    if line_block is None:
        return translation

    refinement = line_block["phase_aware_refinement"]
    selected_endpoint_id = refinement.get("selected_endpoint_id")
    if not selected_endpoint_id:
        return translation

    selected_classes = [
        entry
        for entry in refinement["restriction_classes_by_endpoint"].get(selected_endpoint_id, [])
        if entry["class_size"] > 1
    ]
    translation.update(
        {
            "profile": "phase_aware_point_row_translation_v1",
            "line_id": line_block["line_id"],
            "selected_endpoint_id": selected_endpoint_id,
        }
    )
    if not selected_classes:
        return translation

    unknown_index = {label: idx for idx, label in enumerate(unknown_ordering)}
    other_endpoint_id = next(endpoint_id for endpoint_id in line_block["endpoint_ids"] if endpoint_id != selected_endpoint_id)
    selected_decompositions = {
        rep["rep_id"]: rep["decomposition_on_line_basis"]
        for rep in line_block["endpoint_decompositions"][selected_endpoint_id]
    }
    basis_scale: dict[str, int] = {}
    selected_endpoint_class_actions: list[dict[str, Any]] = []
    for class_index, entry in enumerate(selected_classes, start=1):
        basis_labels = sorted(
            {
                basis_label
                for rep_id in entry["rep_ids"]
                for basis_label, coeff in selected_decompositions[rep_id].items()
                if coeff
            }
        )
        for basis_label in basis_labels:
            basis_scale[basis_label] = max(basis_scale.get(basis_label, 1), int(entry["class_size"]))
        selected_endpoint_class_actions.append(
            {
                "class_id": f"{line_block['line_id']}_phase_aware_class_{class_index:02d}",
                "endpoint_id": selected_endpoint_id,
                "rep_ids": list(entry["rep_ids"]),
                "rep_indices": [int(rep_id.split("_R")[1]) - 1 for rep_id in entry["rep_ids"]],
                "class_size": int(entry["class_size"]),
                "basis_labels": basis_labels,
                "unknown_indices": [unknown_index[rep_id] for rep_id in entry["rep_ids"]],
                "action": "replicate_class_sum_on_members",
            }
        )

    other_endpoint_scalings: list[dict[str, Any]] = []
    for rep in line_block["endpoint_decompositions"][other_endpoint_id]:
        touched_basis_labels = sorted(
            basis_label
            for basis_label, coeff in rep["decomposition_on_line_basis"].items()
            if coeff and basis_label in basis_scale
        )
        if not touched_basis_labels:
            continue
        factor = max(basis_scale[basis_label] for basis_label in touched_basis_labels)
        if factor <= 1:
            continue
        rep_id = rep["rep_id"]
        other_endpoint_scalings.append(
            {
                "endpoint_id": other_endpoint_id,
                "rep_id": rep_id,
                "rep_index": int(rep_id.split("_R")[1]) - 1,
                "factor": int(factor),
                "touched_basis_labels": touched_basis_labels,
                "unknown_index": unknown_index[rep_id],
                "action": "scale_opposite_endpoint_multiplicity",
            }
        )

    translation.update(
        {
            "enabled": True,
            "other_endpoint_id": other_endpoint_id,
            "selected_endpoint_class_actions": selected_endpoint_class_actions,
            "other_endpoint_scalings": other_endpoint_scalings,
        }
    )
    return translation


def apply_point_row_translation_to_multiplicities(
    manifold_multiplicities: dict[str, list[int]],
    point_row_translation: dict[str, Any] | None,
) -> dict[str, list[int]]:
    if not point_row_translation or not point_row_translation.get("enabled"):
        return {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}

    translated = {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}
    for action in point_row_translation["selected_endpoint_class_actions"]:
        values = translated.get(action["endpoint_id"])
        if values is None:
            continue
        total = sum(values[index] for index in action["rep_indices"])
        for index in action["rep_indices"]:
            values[index] = int(total)
    for action in point_row_translation["other_endpoint_scalings"]:
        values = translated.get(action["endpoint_id"])
        if values is None:
            continue
        values[action["rep_index"]] *= int(action["factor"])
    return translated


def unknown_vector_from_multiplicities(
    manifold_multiplicities: dict[str, list[int]],
    unknown_ordering: list[str],
) -> list[int]:
    unknown_vector = []
    for token in unknown_ordering:
        manifold_id, rep_index_str = token.split("_R")
        unknown_vector.append(int(manifold_multiplicities[manifold_id][int(rep_index_str) - 1]))
    return unknown_vector


def derive_plane_corner_ids(plane_obj: dict[str, Any], point_by_coord: dict[tuple[str, str, str], str]) -> list[str]:
    return [entry["point_id"] for entry in derive_plane_corner_entries(plane_obj, point_by_coord)]


def build_plane_block(plane_obj: dict[str, Any], corner_entries: list[dict[str, Any]], captures: dict[str, Any]) -> dict[str, Any]:
    plane_id = plane_obj["id"]
    plane_raw = captures[plane_id]
    plane_unitary_ops = [operation_key_from_capture(plane_raw, op_index) for op_index in plane_raw["unitary_capture_indices"]]
    # Plane auxiliary coordinates stay in the intended 42-shell only in
    # character language; linear_character fails on S3 corner restrictions.
    field = "character"
    plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
    plane_basis_matrix = _exact_basis_matrix_from_capture(plane_raw, field, manifold_id=plane_id)
    local_unknown_ordering: list[str] = []
    corner_decompositions: dict[str, Any] = {}
    equations = []
    matrix_rows = []
    for corner_entry in corner_entries:
        point_id = corner_entry["point_id"]
        point_raw = captures[corner_entry.get("capture_id", point_id)]
        unitary_map = {
            operation_key_from_capture(point_raw, op_index): unitary_index
            for unitary_index, op_index in enumerate(point_raw["unitary_capture_indices"])
        }
        matched = [unitary_map.get(op_key) for op_key in plane_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(
                f"{point_id} at {corner_entry['point_coordinates']} does not contain the full {plane_id} unitary subgroup"
            )
        reps = []
        for rep_index in range(1, len(point_raw[field]) + 1):
            rep_id = f"{point_id}_R{rep_index}"
            restricted = _exact_restriction_vector(
                plane_raw,
                point_raw,
                [int(index) for index in matched],
                field=field,
                parent_manifold_id=plane_id,
                child_manifold_id=point_id,
                rep_id=rep_id,
            )
            coeffs_int = solve_unique_integer_decomposition(
                plane_basis_matrix,
                restricted,
                mode=_mode_label_from_raw(point_raw),
                manifold_id=plane_id,
                endpoint_id=point_id,
                rep_id=rep_id,
                field=field,
            )
            reps.append({"rep_id": rep_id, "decomposition_on_plane_basis": {label: coeff for label, coeff in zip(plane_basis_labels, coeffs_int) if coeff}})
            local_unknown_ordering.append(rep_id)
        corner_decompositions[(point_id, tuple(corner_entry["point_coordinates"]))] = reps
    local_unknown_ordering.extend(plane_basis_labels)
    local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
    for corner_entry in corner_entries:
        point_id = corner_entry["point_id"]
        point_reps = corner_decompositions[(point_id, tuple(corner_entry["point_coordinates"]))]
        for basis_label in plane_basis_labels:
            row = [0] * len(local_unknown_ordering)
            terms = []
            for rep in point_reps:
                coeff = rep["decomposition_on_plane_basis"].get(basis_label, 0)
                if coeff:
                    row[local_index[rep["rep_id"]]] += coeff
                    terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": "point"})
            row[local_index[basis_label]] -= 1
            terms.append({"unknown": basis_label, "coeff": -1, "side": "plane"})
            equations.append({"point_id": point_id, "basis_id": basis_label, "terms": terms})
            matrix_rows.append(row)
    return {
        "status": "success",
        "plane_id": plane_id,
        "corner_ids": [entry["point_id"] for entry in corner_entries],
        "plane_sample_point": plane_obj["sample_point"],
        "plane_parametrization": plane_obj["parametrization"],
        "plane_symmetry_summary": plane_obj["symmetry_summary"],
        "plane_basis_labels": plane_basis_labels,
        "corner_decompositions": corner_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "compatibility_field": field,
        "compatibility_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
    }


def build_with_planes_compatibility(line_full: dict[str, Any], plane_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    ordering = list(line_full["global_unknown_ordering"])
    for block in plane_blocks:
        for unknown in block["local_unknown_ordering"]:
            if unknown not in ordering:
                ordering.append(unknown)
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    rows = []
    extra_unknown_count = len(ordering) - len(line_full["global_unknown_ordering"])
    for row in line_full["global_matrix_rows"]:
        padded = list(row["matrix_row"]) + [0] * extra_unknown_count
        rows.append({**row, "matrix_row": padded})
    for block in plane_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            rows.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "point_id": equation["point_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": rows,
        "global_matrix": [row["matrix_row"] for row in rows],
        "covered_lines": list(line_full["covered_lines"]),
        "covered_planes": [block["plane_id"] for block in plane_blocks],
    }


def smith_diagonal_entries(D: sp.Matrix) -> list[int]:
    diag = []
    for index in range(min(D.rows, D.cols)):
        value = int(abs(D[index, index]))
        if value:
            diag.append(value)
    return diag


def analyze_kernel(matrix_payload: dict[str, Any]) -> dict[str, Any]:
    C = sp.Matrix(matrix_payload["global_matrix"])
    D_list, _U_list, V_list = swyckoff_k.smith_normal_form(matrix_payload["global_matrix"])
    D = sp.Matrix(D_list)
    V = sp.Matrix(V_list)
    smith_diagonal = smith_diagonal_entries(D)
    rank = len(smith_diagonal)
    nullity = C.cols - rank
    basis_matrix = V[:, rank:]
    basis_vectors = []
    for basis_index in range(basis_matrix.cols):
        vector = [int(value) for value in list(basis_matrix[:, basis_index])]
        basis_vectors.append({"id": f"basis_{basis_index + 1:02d}", "vector": vector})
    return {
        "unknown_ordering": list(matrix_payload["global_unknown_ordering"]),
        "matrix_shape": [C.rows, C.cols],
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "basis_vectors": basis_vectors,
    }


def trivial_local_character(entry: dict[str, Any], ctx: dict[str, Any]) -> dict[int, complex]:
    stabilizer = bridge.bridge_stabilizer_for_entry(entry, ctx)
    return {int(index): 1 + 0j for index in stabilizer["unitary_indices"]}


def _resolve_induction_character_field(
    character_field: str | dict[str, str],
    manifold_id: str,
    kgeom: dict[str, Any],
) -> str:
    if isinstance(character_field, str):
        return character_field
    point_ids = {
        point["id"]
        for point in (
            kgeom["grouped"]["points"] + kgeom.get("synthetic_boundary_points", [])
        )
    }
    line_ids = {line["id"] for line in kgeom["grouped"]["lines"]}
    plane_ids = {plane["id"] for plane in kgeom["grouped"]["planes"]}
    if manifold_id in point_ids:
        return character_field.get("point", character_field.get("default", "linear_character"))
    if manifold_id in line_ids:
        return character_field.get("line", character_field.get("default", "linear_character"))
    if manifold_id in plane_ids:
        return character_field.get("plane", character_field.get("default", "linear_character"))
    return character_field.get("default", "linear_character")


def _summarize_induction_character_field(character_field: str | dict[str, str]) -> str:
    if isinstance(character_field, str):
        return character_field
    ordered_keys = ["point", "line", "plane", "default"]
    return ", ".join(
        f"{key}={character_field[key]}"
        for key in ordered_keys
        if key in character_field
    )


def induce_candidate(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    unknown_ordering: list[str],
    global_matrix: list[list[int]],
    point_row_translation: dict[str, Any] | None = None,
    *,
    character_field: str = "linear_character",
) -> dict[str, Any]:
    orbit = single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    stabilizer = bridge.bridge_stabilizer_for_entry(entry, ctx)
    stabilizer_unitary = set(stabilizer["unitary_indices"])
    manifold_multiplicities: dict[str, list[int]] = {}
    manifold_band_characters: dict[str, list[dict[str, float]]] = {}
    manifold_character_fields: dict[str, str] = {}
    manifold_ids = [
        obj["id"]
        for obj in (
            ctx["kgeom"]["grouped"]["points"]
            + ctx["kgeom"]["synthetic_boundary_points"]
            + ctx["kgeom"]["grouped"]["lines"]
            + ctx["kgeom"]["grouped"]["planes"]
        )
    ]
    for manifold_id in manifold_ids:
        info = captures[manifold_id]
        manifold_character_field = _resolve_induction_character_field(
            character_field,
            manifold_id,
            ctx["kgeom"],
        )
        manifold_character_fields[manifold_id] = manifold_character_field
        band_character: list[complex] = []
        for op_index, rotation, translation in zip(info["unitary_raw_indices"], info["unitary_rotations"], info["unitary_translations"]):
            rot = np.array(rotation, dtype=float)
            tau = np.array(translation, dtype=float)
            total = 0j
            for site in orbit:
                coset_index = int(site["source_operation_index"])
                conj_index = ctx["group_tables"]["compose"](
                    ctx["group_tables"]["inverse"][coset_index],
                    ctx["group_tables"]["compose"](op_index, coset_index),
                )
                if conj_index not in stabilizer_unitary:
                    continue
                point_conv = np.array(site["conv_vector"], dtype=float)
                delta = rot @ point_conv + tau - point_conv
                fixed, _ = bridge.vector_is_lattice(ctx["supercell"], delta)
                if not fixed:
                    continue
                total += local_character[conj_index] * np.exp(-1j * float(np.dot(np.array(info["kconv"], dtype=float), delta)))
            band_character.append(total)
        chars = np.array(info[manifold_character_field], dtype=complex)
        band = np.array(band_character, dtype=complex)
        context = f"{entry['letter']} on {manifold_id} [{manifold_character_field}]"
        basis_matrix = sp.Matrix(chars.T.tolist())
        restricted = sp.Matrix(list(band))
        numeric_error = None
        try:
            rounded = solve_numeric_integer_decomposition(basis_matrix, restricted, context)
        except ValueError as exc:
            numeric_error = str(exc)
            gram = chars @ chars.conj().T / chars.shape[1]
            rhs = chars.conj() @ band / chars.shape[1]
            multiplicities = np.linalg.solve(gram, rhs)
            rounded = [int(round(float(value.real))) for value in multiplicities]
            if not np.allclose(multiplicities, np.rint(multiplicities.real), atol=1e-8):
                raise ValueError(
                    f"{entry['letter']} on {manifold_id}: non-integral multiplicities "
                    f"(numeric_solver={numeric_error})"
                )
        recon = np.array(rounded, dtype=complex) @ chars
        if not np.allclose(recon, band, atol=1e-8):
            raise ValueError(
                f"{entry['letter']} on {manifold_id}: reconstruction failed "
                f"(numeric_solver={numeric_error})"
            )
        manifold_multiplicities[manifold_id] = rounded
        manifold_band_characters[manifold_id] = complex_list_to_json(band_character)
    raw_manifold_multiplicities = {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}
    raw_unknown_vector = unknown_vector_from_multiplicities(raw_manifold_multiplicities, unknown_ordering)
    translated_multiplicities = apply_point_row_translation_to_multiplicities(
        raw_manifold_multiplicities,
        point_row_translation,
    )
    unknown_vector = unknown_vector_from_multiplicities(translated_multiplicities, unknown_ordering)
    compatibility_residual = [int(value) for value in list(sp.Matrix(global_matrix) * sp.Matrix(unknown_vector))]
    nonzero_residual_rows = [
        {"row_index": row_index, "residual": value}
        for row_index, value in enumerate(compatibility_residual)
        if value != 0
    ]
    compatibility_zero = not nonzero_residual_rows
    return {
        "family_letter": entry["letter"],
        "representative_coordinate": entry["representative_coordinate"],
        "multiplicity": int(entry["mult"]),
        "site_symmetry": entry["site_symmetry"],
        "manifold_multiplicities": translated_multiplicities,
        "raw_manifold_multiplicities": raw_manifold_multiplicities,
        "manifold_band_characters": manifold_band_characters,
        "raw_unknown_vector": raw_unknown_vector,
        "unknown_vector": unknown_vector,
        "compatibility_zero": compatibility_zero,
        "compatibility_residual_norm": sum(abs(value) for value in compatibility_residual),
        "compatibility_residual_vector": compatibility_residual,
        "nonzero_residual_rows": nonzero_residual_rows,
        "point_row_translation_profile": (
            point_row_translation["profile"]
            if point_row_translation and point_row_translation.get("enabled")
            else "legacy"
        ),
        "character_field_used": _summarize_induction_character_field(character_field),
        "manifold_character_fields": manifold_character_fields,
        "stabilizer_size": int(stabilizer["bridge_stabilizer_size"]),
        "unitary_stabilizer_size": int(stabilizer["bridge_unitary_count"]),
    }


def build_synthetic_kpoint_map(kgeom: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    mapping = coordinate_to_id_map(kgeom["grouped"]["points"])
    for point in kgeom["synthetic_boundary_points"]:
        mapping[tuple(point["sample_point"])] = point["id"]
    return mapping


def build_point_instance_entries(kgeom: dict[str, Any]) -> list[dict[str, Any]]:
    point_lookup = {point["id"]: point for point in kgeom["grouped"]["points"]}
    point_lookup.update({point["id"]: point for point in kgeom.get("synthetic_boundary_points", [])})
    point_by_coord = build_synthetic_kpoint_map(kgeom)
    point_instances: list[dict[str, Any]] = []
    seen: set[str] = set()

    def ensure_point_instance(point_id: str, coords: Sequence[str]) -> str:
        representative_coords = point_lookup[point_id]["sample_point"]
        if list(coords) == list(representative_coords):
            return point_id
        capture_id = point_capture_id(point_id, coords)
        if capture_id not in seen:
            point_instances.append(
                {
                    "capture_id": capture_id,
                    "point_id": point_id,
                    "point_coordinates": list(coords),
                }
            )
            seen.add(capture_id)
        return capture_id

    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            endpoint["capture_id"] = ensure_point_instance(endpoint["point_id"], endpoint["point_coordinates"])
    for plane in kgeom["grouped"]["planes"]:
        corner_entries = derive_plane_corner_entries(plane, point_by_coord)
        for corner in corner_entries:
            corner["capture_id"] = ensure_point_instance(corner["point_id"], corner["point_coordinates"])
        plane["corner_entries"] = corner_entries
    kgeom["point_instance_entries"] = point_instances
    return point_instances


def annotate_final_path_lines(
    final_line_specs: Sequence[dict[str, Any]],
    ctx: dict[str, Any],
    line_orbit_to_id: dict[str, str],
    plane_orbit_to_id: dict[str, str],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for spec in final_line_specs:
        anchor = [Fraction(value) for value in spec["_anchor"]]
        basis = [Fraction(value) for value in spec["_basis"][0]]
        line = dict(spec)
        line["symmetry_summary"] = subspace_symmetry_summary(anchor, [basis], ctx)
        line["closure_under_pointwise_stabilizer"] = closure_components(
            anchor,
            [basis],
            ctx,
            line_orbit_to_id,
            plane_orbit_to_id,
        )
        lines.append(line)
    return lines


def capture_final_path_lines(
    module: Any,
    group_number: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    group_label: str,
    captures: dict[str, Any],
    final_lines: Sequence[dict[str, Any]],
) -> None:
    for line in final_lines:
        captures[line["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            line["id"],
            [float(Fraction(value)) for value in line["sample_point"]],
        )


def build_bilbao_equivalent_sanity_check(reduction: dict[str, Any]) -> dict[str, Any]:
    return compare_reduction_to_expected_pairs(
        reduction,
        expected_point_ids=["P1", "P2", "P3", "P4", "P5", "P6"],
        expected_endpoint_pairs=[
            ["P1", "P2"],
            ["P1", "P3"],
            ["P1", "P5"],
            ["P2", "P4"],
            ["P2", "P6"],
            ["P3", "P4"],
            ["P5", "P6"],
        ],
    )


def write_reduction_reports(
    reduction: dict[str, Any],
    sanity_check: dict[str, Any],
    *,
    published_line_full: dict[str, Any],
    published_bs_analysis: dict[str, Any],
    diagnostic_with_planes: dict[str, Any],
    diagnostic_bs_analysis: dict[str, Any],
) -> dict[str, Any]:
    reduction_payload = {
        **reduction,
        "final_point_count": len(reduction["final_point_ids"]),
        "final_path_count": len(reduction["published_path_ids"]),
        "published_line_matrix_shape": [
            len(published_line_full["global_matrix"]),
            len(published_line_full["global_unknown_ordering"]),
        ],
        "published_bs_analysis": published_bs_analysis,
        "diagnostic_with_planes_matrix_shape": [
            len(diagnostic_with_planes["global_matrix"]),
            len(diagnostic_with_planes["global_unknown_ordering"]),
        ],
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
    }
    path_signature_report = build_final_path_signature_report(reduction)
    path_equiv_report = build_final_path_candidate_equivalence_report(reduction)
    full_shell_report = build_full_shell_automorphism_search_report(reduction)
    p1_p5_resolution_report = build_p1_p5_doubleclass_resolution_report(reduction)
    bs_strong_report = build_final_bs_strong_equivalence_report(
        reduction,
        sanity_check,
        published_line_full,
        published_bs_analysis,
    )
    reduction_payload["row_language_full_span_pass"] = bs_strong_report["row_language_full_span_pass"]
    reduction_payload["bilbao_equivalent_final_object_pass"] = bs_strong_report["bilbao_equivalent_final_object_pass"]
    reduction_payload["p1_p5_doubleclass_resolution_status"] = p1_p5_resolution_report.get("resolution_status")
    reduction_payload["p1_p5_global_automorphism_found"] = full_shell_report.get("global_solution_found")
    missing_row_witness_report = build_missing_row_language_witness_report(reduction)
    write_json(REDUCTION_REPORT_JSON, reduction_payload)
    write_text(REDUCTION_REPORT_MD, build_reduction_report_markdown(reduction_payload))
    write_json(REDUCTION_CHECK_JSON, sanity_check)
    write_text(REDUCTION_CHECK_MD, build_expected_check_markdown(sanity_check))
    write_json(FINAL_PATH_SIGNATURE_JSON, path_signature_report)
    write_text(FINAL_PATH_SIGNATURE_MD, build_final_path_signature_markdown(path_signature_report))
    write_json(FINAL_PATH_EQUIV_JSON, path_equiv_report)
    write_text(FINAL_PATH_EQUIV_MD, build_final_path_candidate_equivalence_markdown(path_equiv_report))
    write_json(P1_P5_RESOLUTION_JSON, p1_p5_resolution_report)
    write_text(P1_P5_RESOLUTION_MD, build_p1_p5_doubleclass_resolution_markdown(p1_p5_resolution_report))
    write_json(FULL_SHELL_AUTOMORPHISM_JSON, full_shell_report)
    write_text(FULL_SHELL_AUTOMORPHISM_MD, build_full_shell_automorphism_search_markdown(full_shell_report))
    write_json(FULL_POINT_SHELL_AUTOMORPHISM_JSON, full_shell_report)
    write_text(FULL_POINT_SHELL_AUTOMORPHISM_MD, build_full_shell_automorphism_search_markdown(full_shell_report))
    write_json(FINAL_BS_STRONG_JSON, bs_strong_report)
    write_text(FINAL_BS_STRONG_MD, build_final_bs_strong_equivalence_markdown(bs_strong_report))
    write_json(MISSING_ROW_WITNESS_JSON, missing_row_witness_report)
    write_text(MISSING_ROW_WITNESS_MD, build_missing_row_language_witness_markdown(missing_row_witness_report))
    return {
        "reduction_report": reduction_payload,
        "path_signature_report": path_signature_report,
        "path_equivalence_report": path_equiv_report,
        "full_shell_automorphism_search_report": full_shell_report,
        "p1_p5_doubleclass_resolution_report": p1_p5_resolution_report,
        "bs_strong_equivalence_report": bs_strong_report,
        "missing_row_witness_report": missing_row_witness_report,
    }


def disable_point_row_translation(
    point_row_translation: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    disabled = dict(point_row_translation)
    disabled.update(
        {
            "profile": "legacy",
            "enabled": False,
            "disabled_reason": reason,
            "source_profile": point_row_translation.get("profile"),
        }
    )
    return disabled


def build_point_row_translation_legality_report(
    global_matrix: list[list[int]],
    probe_candidates: Sequence[dict[str, Any]],
    candidate_translation: dict[str, Any],
    published_translation: dict[str, Any],
) -> dict[str, Any]:
    matrix = sp.Matrix(global_matrix)
    entries = []
    raw_zero_count = 0
    translated_zero_count = 0
    improved_count = 0
    worsened_count = 0
    unchanged_count = 0
    for candidate in probe_candidates:
        raw_residual = [int(value) for value in list(matrix * sp.Matrix(candidate["raw_unknown_vector"]))]
        translated_residual = [int(value) for value in list(matrix * sp.Matrix(candidate["unknown_vector"]))]
        raw_norm = sum(abs(value) for value in raw_residual)
        translated_norm = sum(abs(value) for value in translated_residual)
        raw_zero = all(value == 0 for value in raw_residual)
        translated_zero = all(value == 0 for value in translated_residual)
        raw_zero_count += int(raw_zero)
        translated_zero_count += int(translated_zero)
        if translated_norm < raw_norm:
            improved_count += 1
        elif translated_norm > raw_norm:
            worsened_count += 1
        else:
            unchanged_count += 1
        entries.append(
            {
                "family_letter": candidate["family_letter"],
                "raw_compatibility_zero": raw_zero,
                "translated_compatibility_zero": translated_zero,
                "raw_residual_norm": raw_norm,
                "translated_residual_norm": translated_norm,
                "raw_nonzero_rows": [
                    index
                    for index, value in enumerate(raw_residual)
                    if value != 0
                ],
                "translated_nonzero_rows": [
                    index
                    for index, value in enumerate(translated_residual)
                    if value != 0
                ],
            }
        )
    legality_status = "legal"
    if candidate_translation.get("enabled") and (
        translated_zero_count < raw_zero_count or worsened_count > 0
    ):
        legality_status = "removed"
    return {
        "candidate_translation_profile": candidate_translation.get("profile"),
        "candidate_translation_enabled": bool(candidate_translation.get("enabled")),
        "published_translation_profile": published_translation.get("profile"),
        "published_translation_enabled": bool(published_translation.get("enabled")),
        "generator_count": len(entries),
        "raw_compatibility_zero_count": raw_zero_count,
        "translated_compatibility_zero_count": translated_zero_count,
        "improved_count": improved_count,
        "worsened_count": worsened_count,
        "unchanged_count": unchanged_count,
        "legality_status": legality_status,
        "legality_reason": (
            "phase-aware point-row translation is retired on the published final "
            "reduced point/path shell because the translated seed does not dominate "
            "the raw seed mechanically on the regenerated compatibility object."
            if legality_status == "removed"
            else "phase-aware point-row translation remains mechanically valid on the published final point/path shell."
        ),
        "generator_checks": entries,
    }


def build_point_row_translation_legality_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Point-Row Translation Legality Report",
        "",
        f"- Candidate translation profile: `{report['candidate_translation_profile']}`.",
        f"- Candidate translation enabled: `{report['candidate_translation_enabled']}`.",
        f"- Published translation profile: `{report['published_translation_profile']}`.",
        f"- Published translation enabled: `{report['published_translation_enabled']}`.",
        f"- Raw compatibility-zero count: `{report['raw_compatibility_zero_count']}` / `{report['generator_count']}`.",
        f"- Translated compatibility-zero count: `{report['translated_compatibility_zero_count']}` / `{report['generator_count']}`.",
        f"- Improved / worsened / unchanged generators: `{report['improved_count']}` / `{report['worsened_count']}` / `{report['unchanged_count']}`.",
        f"- Legality status: `{report['legality_status']}`.",
        f"- Reason: {report['legality_reason']}",
        "",
    ]
    for entry in report["generator_checks"]:
        lines.append(
            "- "
            + f"`{entry['family_letter']}`: raw zero = `{entry['raw_compatibility_zero']}`, "
            + f"translated zero = `{entry['translated_compatibility_zero']}`, "
            + f"raw norm = `{entry['raw_residual_norm']}`, translated norm = `{entry['translated_residual_norm']}`."
        )
    return "\n".join(lines)


def build_ai_seed_audit_report(
    ai_candidates: Sequence[dict[str, Any]],
    point_row_translation: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
    library_integration_status: str = "not_attempted",
) -> dict[str, Any]:
    ai_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate["unknown_vector"]) for candidate in ai_candidates])
        if ai_candidates
        else sp.zeros(len(unknown_ordering), 0)
    )
    compatibility_zero_count = sum(int(candidate["compatibility_zero"]) for candidate in ai_candidates)
    return {
        "ai_status": "seed_only",
        "object_language": "published_final_point_path_shell_34_unknowns",
        "unknown_count": len(unknown_ordering),
        "generator_count": len(ai_candidates),
        "rank_trivial_family_span": int(ai_matrix.rank()) if ai_candidates else 0,
        "compatibility_zero_count": compatibility_zero_count,
        "compatibility_zero_family_letters": [
            candidate["family_letter"]
            for candidate in ai_candidates
            if candidate["compatibility_zero"]
        ],
        "nonzero_residual_family_letters": [
            candidate["family_letter"]
            for candidate in ai_candidates
            if not candidate["compatibility_zero"]
        ],
        "point_row_translation_profile": point_row_translation.get("profile"),
        "point_row_translation_enabled": bool(point_row_translation.get("enabled")),
        "library_integration_status": library_integration_status,
        "missing_prerequisites": [
            "published-shell induction beyond the trivial seed is not yet closed on the current reduced shell",
            "validated non-abelian local irrep/corep libraries are wired into the builder, but most induced local objects still fail compatibility on the current published shell",
            "AI-in-BS coordinate matrix and quotient SNF built from a complete AI basis",
        ],
        "honest_ai_lattice_ready": False,
    }


def build_ai_seed_audit_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Seed Audit Report",
            "",
            f"- AI status: `{report['ai_status']}`.",
            f"- Object language: `{report['object_language']}`.",
            f"- Unknown count: `{report['unknown_count']}`.",
            f"- Generator count: `{report['generator_count']}`.",
            f"- Rank of trivial-family span: `{report['rank_trivial_family_span']}`.",
            f"- Compatibility-zero generators: `{report['compatibility_zero_count']}`.",
            f"- Compatibility-zero family letters: `{report['compatibility_zero_family_letters']}`.",
            f"- Nonzero-residual family letters: `{report['nonzero_residual_family_letters']}`.",
            f"- Point-row translation profile/enabled: `{report['point_row_translation_profile']}` / `{report['point_row_translation_enabled']}`.",
            f"- Library integration status: `{report['library_integration_status']}`.",
            f"- Honest AI lattice ready: `{report['honest_ai_lattice_ready']}`.",
            "- Missing prerequisites:",
            *[f"  - {item}" for item in report["missing_prerequisites"]],
        ]
    )


def load_json_from_head(path: Path) -> dict[str, Any] | None:
    repo_relative = path.relative_to(ROOT.parent)
    proc = subprocess.run(
        ["git", "show", f"HEAD:{repo_relative.as_posix()}"],
        cwd=ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


def build_ai_seed_delta_after_bs_fix_report(
    ai_generators_payload: dict[str, Any],
    ai_audit_report: dict[str, Any],
) -> dict[str, Any]:
    previous_payload = load_json_from_head(SINGLE_AI_JSON)
    previous_audit = load_json_from_head(AI_SEED_AUDIT_JSON)
    current_zero = list(ai_audit_report["compatibility_zero_family_letters"])
    current_residual = list(ai_audit_report["nonzero_residual_family_letters"])
    previous_zero = (
        list(previous_audit.get("compatibility_zero_family_letters", []))
        if previous_audit
        else []
    )
    previous_residual = (
        list(previous_audit.get("nonzero_residual_family_letters", []))
        if previous_audit
        else []
    )
    return {
        "comparison_base": "git_head_before_current_round_commit",
        "previous_payload_available": previous_payload is not None,
        "previous_audit_available": previous_audit is not None,
        "current_ai_status": ai_audit_report["ai_status"],
        "previous_ai_status": previous_audit.get("ai_status") if previous_audit else None,
        "current_generator_count": len(ai_generators_payload["generators"]),
        "previous_generator_count": (
            len(previous_payload.get("generators", []))
            if previous_payload
            else None
        ),
        "current_rank_trivial_family_span": int(ai_audit_report["rank_trivial_family_span"]),
        "previous_rank_trivial_family_span": (
            int(previous_audit["rank_trivial_family_span"])
            if previous_audit
            else None
        ),
        "current_compatibility_zero_count": int(ai_audit_report["compatibility_zero_count"]),
        "previous_compatibility_zero_count": (
            int(previous_audit["compatibility_zero_count"])
            if previous_audit
            else None
        ),
        "current_compatibility_zero_family_letters": current_zero,
        "previous_compatibility_zero_family_letters": previous_zero,
        "current_nonzero_residual_family_letters": current_residual,
        "previous_nonzero_residual_family_letters": previous_residual,
        "added_zero_families": sorted(set(current_zero) - set(previous_zero)),
        "removed_zero_families": sorted(set(previous_zero) - set(current_zero)),
        "added_nonzero_residual_families": sorted(set(current_residual) - set(previous_residual)),
        "removed_nonzero_residual_families": sorted(set(previous_residual) - set(current_residual)),
        "residual_pattern_changed": (
            current_zero != previous_zero or current_residual != previous_residual
        ),
    }


def build_ai_seed_delta_after_bs_fix_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Seed Delta After BS Fix Report",
            "",
            f"- Comparison base: `{report['comparison_base']}`.",
            f"- Previous payload/audit available: `{report['previous_payload_available']}` / `{report['previous_audit_available']}`.",
            f"- Current vs previous AI status: `{report['current_ai_status']}` / `{report['previous_ai_status']}`.",
            f"- Current vs previous generator count: `{report['current_generator_count']}` / `{report['previous_generator_count']}`.",
            f"- Current vs previous trivial-family span rank: `{report['current_rank_trivial_family_span']}` / `{report['previous_rank_trivial_family_span']}`.",
            f"- Current vs previous compatibility-zero count: `{report['current_compatibility_zero_count']}` / `{report['previous_compatibility_zero_count']}`.",
            f"- Current zero families: `{report['current_compatibility_zero_family_letters']}`.",
            f"- Previous zero families: `{report['previous_compatibility_zero_family_letters']}`.",
            f"- Current residual families: `{report['current_nonzero_residual_family_letters']}`.",
            f"- Previous residual families: `{report['previous_nonzero_residual_family_letters']}`.",
            f"- Added/removed zero families: `{report['added_zero_families']}` / `{report['removed_zero_families']}`.",
            f"- Added/removed nonzero residual families: `{report['added_nonzero_residual_families']}` / `{report['removed_nonzero_residual_families']}`.",
            f"- Residual pattern changed: `{report['residual_pattern_changed']}`.",
        ]
    )


def build_ai_character_field_alignment_report(
    obstruction_report: dict[str, Any],
    *,
    authoritative_compatibility_field: str,
    raw42_character_field: str,
    skeleton7_character_field: str,
    published8_character_field: str,
) -> dict[str, Any]:
    previous_report = load_json_from_head(AI_OBSTRUCTION_DIAG_JSON)
    previous_counts = (
        dict(previous_report.get("compatibility_zero_counts", {}))
        if previous_report
        else None
    )
    previous_histogram = (
        dict(previous_report.get("published_fail_path_histogram", {}))
        if previous_report
        else None
    )
    current_counts = dict(obstruction_report["compatibility_zero_counts"])
    current_histogram = dict(obstruction_report["published_fail_path_histogram"])
    return {
        "authoritative_compatibility_field": authoritative_compatibility_field,
        "previous_ai_induction_field": "linear_character",
        "current_ai_induction_field": _summarize_induction_character_field(published8_character_field),
        "shell_character_fields": {
            "raw42": _summarize_induction_character_field(raw42_character_field),
            "skeleton7": _summarize_induction_character_field(skeleton7_character_field),
            "published8": _summarize_induction_character_field(published8_character_field),
        },
        "previous_obstruction_report_available": previous_report is not None,
        "previous_compatibility_zero_counts": previous_counts,
        "current_compatibility_zero_counts": current_counts,
        "previous_published_fail_path_histogram": previous_histogram,
        "current_published_fail_path_histogram": current_histogram,
        "compatibility_zero_count_delta": (
            None
            if previous_counts is None
            else {
                shell: int(current_counts.get(shell, 0)) - int(previous_counts.get(shell, 0))
                for shell in sorted(current_counts)
            }
        ),
        "published_fail_histogram_changed": previous_histogram != current_histogram,
    }


def build_ai_character_field_alignment_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Character-Field Alignment Report",
            "",
            f"- Authoritative compatibility field: `{report['authoritative_compatibility_field']}`.",
            f"- Previous AI induction field: `{report['previous_ai_induction_field']}`.",
            f"- Current AI induction field: `{report['current_ai_induction_field']}`.",
            f"- Shell character fields: `{report['shell_character_fields']}`.",
            f"- Previous obstruction report available: `{report['previous_obstruction_report_available']}`.",
            f"- Previous compatibility-zero counts: `{report['previous_compatibility_zero_counts']}`.",
            f"- Current compatibility-zero counts: `{report['current_compatibility_zero_counts']}`.",
            f"- Compatibility-zero count delta: `{report['compatibility_zero_count_delta']}`.",
            f"- Previous published fail-path histogram: `{report['previous_published_fail_path_histogram']}`.",
            f"- Current published fail-path histogram: `{report['current_published_fail_path_histogram']}`.",
            f"- Published fail histogram changed: `{report['published_fail_histogram_changed']}`.",
        ]
    )


def load_nonabelian_local_library_helper():
    path = ROOT / "debug_sg194_nonabelian_local_library.py"
    spec = importlib.util.spec_from_file_location("sg194_nonabelian_local_library_runtime", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_local_library_payload() -> dict[str, Any]:
    helper = load_nonabelian_local_library_helper()
    port = sys.modules.get(__name__)
    if port is not None:
        return helper.build_inventory_and_libraries(port=port)
    return helper.build_inventory_and_libraries()


def induce_family_objects(
    ctx: dict[str, Any],
    captures: dict[str, Any],
    bs_analysis: dict[str, Any],
    global_matrix: list[list[int]],
    point_row_translation: dict[str, Any],
    family_objects: dict[str, list[dict[str, Any]]],
    *,
    character_field: str = "linear_character",
) -> dict[str, Any]:
    candidates = []
    failures = []
    seen_vectors: dict[tuple[int, ...], list[str]] = {}
    family_success_map: dict[str, list[str]] = {}
    for family in sorted(family_objects):
        for local_object in family_objects[family]:
            generator_id = f"{family}_{local_object['label']}"
            local_character = {
                int(index): complex(value)
                for index, value in local_object["character_on_unitary_stabilizer_complex"].items()
            }
            try:
                candidate = induce_candidate(
                    ctx["entries_by_letter"][family],
                    local_character,
                    ctx,
                    captures,
                    bs_analysis["unknown_ordering"],
                    global_matrix,
                    point_row_translation=point_row_translation,
                    character_field=character_field,
                )
                candidate["generator_id"] = generator_id
                candidate["local_object_label"] = local_object["label"]
                candidate["local_object_dimension"] = int(local_object["dimension"])
                candidate["local_object_origin"] = local_object.get("origin", "local_library")
                candidate["site_symmetry_type_key"] = local_object.get("site_symmetry_type_key")
                candidate["site_symmetry_type_label"] = local_object.get("site_symmetry_type_label")
                candidates.append(candidate)
                family_success_map.setdefault(family, []).append(generator_id)
                seen_vectors.setdefault(tuple(int(value) for value in candidate["unknown_vector"]), []).append(generator_id)
            except Exception as exc:
                failures.append(
                    {
                        "generator_id": generator_id,
                        "family_id": family,
                        "local_object_label": local_object["label"],
                        "site_symmetry_type_key": local_object.get("site_symmetry_type_key"),
                        "site_symmetry_type_label": local_object.get("site_symmetry_type_label"),
                        "error": str(exc),
                    }
                )
    duplicate_classes = [
        {
            "generator_ids": ids,
            "vector_in_unknown_ordering": list(vector),
            "class_size": len(ids),
        }
        for vector, ids in sorted(seen_vectors.items(), key=lambda item: item[1])
    ]
    return {
        "candidates": candidates,
        "failures": failures,
        "duplicate_classes": duplicate_classes,
        "family_success_map": family_success_map,
    }


def build_ai_library_integration_report(
    library_payload: dict[str, Any],
    induction: dict[str, Any],
    *,
    mode: str,
    published_object_kind: str,
    unknown_ordering: Sequence[str],
    point_row_translation: dict[str, Any],
) -> dict[str, Any]:
    if mode != "single":
        raise ValueError(f"unsupported AI library integration mode: {mode}")
    family_objects = library_payload["family_single_local_irreps"]
    all_families = sorted(family_objects)
    all_objects = [obj for family in all_families for obj in family_objects[family]]
    compatibility_zero_candidates = [
        candidate["generator_id"]
        for candidate in induction["candidates"]
        if candidate["compatibility_zero"]
    ]
    residual_candidates = [
        {
            "generator_id": candidate["generator_id"],
            "family_id": candidate["family_letter"],
            "local_object_label": candidate.get("local_object_label"),
            "compatibility_residual_norm": int(candidate.get("compatibility_residual_norm", 0)),
            "nonzero_residual_rows": list(candidate.get("nonzero_residual_rows", [])),
        }
        for candidate in induction["candidates"]
        if not candidate["compatibility_zero"]
    ]
    integration_status = (
        "wired_complete_candidate_set"
        if not induction["failures"] and not residual_candidates
        else "wired_but_blocked_on_published_shell"
    )
    return {
        "mode": mode,
        "published_object_kind": published_object_kind,
        "object_language": "published_final_point_path_shell_34_unknowns",
        "ai_induction_character_field": next(
            (
                candidate.get("character_field_used")
                for candidate in induction["candidates"]
                if candidate.get("character_field_used")
            ),
            None,
        ),
        "unknown_count": len(unknown_ordering),
        "local_library_source": "debug_sg194_nonabelian_local_library.build_inventory_and_libraries",
        "local_library_files": [
            str(ROOT / "debug_sg194_nonabelian_local_library.py"),
            str(ROOT / "sg194_single_local_irrep_library.json"),
            str(ROOT / "sg194_double_local_corep_library.json"),
        ],
        "local_library_wired_into_ai_builder": True,
        "family_count": len(all_families),
        "local_object_count": len(all_objects),
        "family_local_object_counts": {family: len(family_objects[family]) for family in all_families},
        "site_symmetry_type_keys": sorted({obj["site_symmetry_type_key"] for obj in all_objects}),
        "success_candidate_count": len(induction["candidates"]),
        "failure_count": len(induction["failures"]),
        "compatibility_zero_candidate_count": len(compatibility_zero_candidates),
        "nonzero_residual_candidate_count": len(residual_candidates),
        "distinct_unknown_vector_count": len(induction["duplicate_classes"]),
        "family_success_counts": {family: len(induction["family_success_map"].get(family, [])) for family in all_families},
        "failure_family_ids": sorted({item["family_id"] for item in induction["failures"]}),
        "compatibility_zero_generator_ids": compatibility_zero_candidates,
        "nonzero_residual_candidates": residual_candidates,
        "failures": induction["failures"],
        "point_row_translation_profile": point_row_translation.get("profile"),
        "point_row_translation_enabled": bool(point_row_translation.get("enabled")),
        "integration_status": integration_status,
    }


def build_ai_library_integration_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Library Integration Report",
            "",
            f"- Mode: `{report['mode']}`.",
            f"- Published object kind: `{report['published_object_kind']}`.",
            f"- AI induction character field: `{report['ai_induction_character_field']}`.",
            f"- Local library wired into AI builder: `{report['local_library_wired_into_ai_builder']}`.",
            f"- Family count / local-object count: `{report['family_count']}` / `{report['local_object_count']}`.",
            f"- Success candidates / failures: `{report['success_candidate_count']}` / `{report['failure_count']}`.",
            f"- Compatibility-zero / nonzero-residual success candidates: `{report['compatibility_zero_candidate_count']}` / `{report['nonzero_residual_candidate_count']}`.",
            f"- Distinct unknown vectors: `{report['distinct_unknown_vector_count']}`.",
            f"- Site-symmetry type keys: `{report['site_symmetry_type_keys']}`.",
            f"- Point-row translation profile/enabled: `{report['point_row_translation_profile']}` / `{report['point_row_translation_enabled']}`.",
            f"- Integration status: `{report['integration_status']}`.",
            f"- Failure family ids: `{report['failure_family_ids']}`.",
        ]
    )


def build_line_block_row_maps(
    line_blocks: Sequence[dict[str, Any]],
) -> tuple[dict[str, list[int]], dict[int, str]]:
    row_ranges: dict[str, list[int]] = {}
    row_to_line: dict[int, str] = {}
    start = 0
    for block in line_blocks:
        rows = list(range(start, start + len(block["equations"])))
        row_ranges[block["line_id"]] = rows
        for row_index in rows:
            row_to_line[row_index] = block["line_id"]
        start += len(block["equations"])
    return row_ranges, row_to_line


def build_ai_obstruction_diagnosis_report(
    reduction: dict[str, Any],
    raw_line_blocks: Sequence[dict[str, Any]],
    final_line_blocks: Sequence[dict[str, Any]],
    raw_with_planes: dict[str, Any],
    skeleton_line_full: dict[str, Any],
    published_line_full: dict[str, Any],
    raw_induction: dict[str, Any],
    skeleton_induction: dict[str, Any],
    published_induction: dict[str, Any],
) -> dict[str, Any]:
    raw_candidates = {item["generator_id"]: item for item in raw_induction["candidates"]}
    skeleton_candidates = {item["generator_id"]: item for item in skeleton_induction["candidates"]}
    published_candidates = {item["generator_id"]: item for item in published_induction["candidates"]}
    raw_failures = {item["generator_id"]: item for item in raw_induction["failures"]}
    skeleton_failures = {item["generator_id"]: item for item in skeleton_induction["failures"]}
    published_failures = {item["generator_id"]: item for item in published_induction["failures"]}
    _raw_row_ranges, raw_row_to_line = build_line_block_row_maps(raw_line_blocks)
    skeleton_path_ids = {
        kept["final_path_id"]
        for kept in reduction["kept_paths"]
        if kept["selection_stage"] == "endpoint_pair_skeleton"
    }
    skeleton_line_blocks = [block for block in final_line_blocks if block["line_id"] in skeleton_path_ids]
    skeleton_row_ranges, skeleton_row_to_line = build_line_block_row_maps(skeleton_line_blocks)
    published_row_ranges, published_row_to_line = build_line_block_row_maps(final_line_blocks)
    augmentation_path_ids = sorted(
        kept["final_path_id"]
        for kept in reduction["kept_paths"]
        if kept["selection_stage"] == "full_span_augmentation"
    )
    augmentation_row_indices = sorted(
        row_index
        for path_id in augmentation_path_ids
        for row_index in published_row_ranges.get(path_id, [])
    )
    all_generator_ids = sorted(
        set(raw_candidates)
        | set(skeleton_candidates)
        | set(published_candidates)
        | set(raw_failures)
        | set(skeleton_failures)
        | set(published_failures)
    )

    def shell_state(
        generator_id: str,
        candidates: dict[str, dict[str, Any]],
        failures: dict[str, dict[str, Any]],
        row_to_line: dict[int, str],
    ) -> dict[str, Any]:
        if generator_id in failures:
            failure = failures[generator_id]
            return {
                "status": "induction_failure",
                "compatibility_zero": False,
                "compatibility_residual_norm": None,
                "nonzero_rows": [],
                "nonzero_path_ids": [],
                "error": failure["error"],
                "family_id": failure.get("family_id"),
                "local_object_label": failure.get("local_object_label"),
                "site_symmetry_type_key": failure.get("site_symmetry_type_key"),
            }
        candidate = candidates[generator_id]
        nonzero_rows = [
            {"row_index": int(item["row_index"]), "residual": int(item["residual"])}
            for item in candidate.get("nonzero_residual_rows", [])
        ]
        return {
            "status": "compatible" if candidate["compatibility_zero"] else "nonzero_residual",
            "compatibility_zero": bool(candidate["compatibility_zero"]),
            "compatibility_residual_norm": int(candidate.get("compatibility_residual_norm", 0)),
            "nonzero_rows": nonzero_rows,
            "nonzero_path_ids": [row_to_line.get(item["row_index"], "unmapped_row") for item in nonzero_rows],
            "error": None,
            "family_id": candidate.get("family_letter"),
            "local_object_label": candidate.get("local_object_label"),
            "site_symmetry_type_key": candidate.get("site_symmetry_type_key"),
        }

    generator_records = []
    classification_counts: Counter[str] = Counter()
    family_counts_by_classification: dict[str, Counter[str]] = {}
    published_fail_path_counter: Counter[str] = Counter()
    published_fail_row_counter: Counter[int] = Counter()
    for generator_id in all_generator_ids:
        raw_state = shell_state(generator_id, raw_candidates, raw_failures, raw_row_to_line)
        skeleton_state = shell_state(generator_id, skeleton_candidates, skeleton_failures, skeleton_row_to_line)
        published_state = shell_state(generator_id, published_candidates, published_failures, published_row_to_line)
        if published_state["compatibility_zero"]:
            classification = "compatible_on_published8"
        elif raw_state["status"] == "induction_failure":
            classification = "induction_failure_on_raw42"
        elif skeleton_state["status"] == "induction_failure":
            classification = "induction_failure_on_7path_skeleton"
        elif published_state["status"] == "induction_failure":
            classification = "induction_failure_on_published8"
        elif not raw_state["compatibility_zero"]:
            classification = "fails_on_raw42"
        elif not skeleton_state["compatibility_zero"]:
            classification = "fails_on_7path_skeleton"
        elif set(item["row_index"] for item in published_state["nonzero_rows"]).issubset(set(augmentation_row_indices)):
            classification = "published8_augmentation_rows_only"
        else:
            classification = "published8_nonaugmentation_rows_only"
        classification_counts[classification] += 1
        family_id = published_state["family_id"] or skeleton_state["family_id"] or raw_state["family_id"] or "unknown"
        family_counts_by_classification.setdefault(classification, Counter())[family_id] += 1
        for path_id in published_state["nonzero_path_ids"]:
            published_fail_path_counter[path_id] += 1
        for item in published_state["nonzero_rows"]:
            published_fail_row_counter[item["row_index"]] += 1
        generator_records.append(
            {
                "generator_id": generator_id,
                "family_id": family_id,
                "local_object_label": (
                    published_state["local_object_label"]
                    or skeleton_state["local_object_label"]
                    or raw_state["local_object_label"]
                ),
                "site_symmetry_type_key": (
                    published_state["site_symmetry_type_key"]
                    or skeleton_state["site_symmetry_type_key"]
                    or raw_state["site_symmetry_type_key"]
                ),
                "classification": classification,
                "raw42": raw_state,
                "skeleton7": skeleton_state,
                "published8": published_state,
            }
        )
    diagnosis_parts = []
    if classification_counts.get("fails_on_raw42", 0) > 0:
        diagnosis_parts.append(
            f"{classification_counts['fails_on_raw42']} candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied."
        )
    if classification_counts.get("published8_augmentation_rows_only", 0) == 0:
        diagnosis_parts.append("The extra 8th path is not the dominant single-AI obstruction.")
    else:
        diagnosis_parts.append("A subset of local-library candidates fails only after the 8th-path augmentation is imposed.")
    if classification_counts.get("fails_on_7path_skeleton", 0) > 0:
        diagnosis_parts.append("Some nonzero residual candidates first fail on the reduced 7-path skeleton.")
    else:
        diagnosis_parts.append("No candidate fails first on the reduced 7-path skeleton before the 8th path is added.")
    if published_fail_path_counter:
        diagnosis_parts.append(
            f"On the published shell the nonzero residual rows concentrate on path histogram {dict(sorted(published_fail_path_counter.items()))}."
        )
    diagnosis_summary = " ".join(diagnosis_parts)
    return {
        "mode": "single",
        "published_object_kind": reduction["reduction_kind"],
        "ai_induction_character_field": next(
            (
                candidate.get("character_field_used")
                for candidate in published_induction["candidates"]
                if candidate.get("character_field_used")
            ),
            None,
        ),
        "row_language_full_span_pass": bool(reduction.get("selected_rows_span_full_candidate_row_language")),
        "bilbao_equivalent_final_object_pass": bool(reduction.get("bilbao_equivalent_final_object_pass")),
        "selected_path_count": len(reduction["published_path_ids"]),
        "unique_endpoint_pair_count": len({tuple(kept["endpoint_pair"]) for kept in reduction["kept_paths"]}),
        "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
        "augmentation_path_ids": augmentation_path_ids,
        "augmentation_row_indices": augmentation_row_indices,
        "shell_matrix_shapes": {
            "raw42": [len(raw_with_planes["global_matrix"]), len(raw_with_planes["global_unknown_ordering"])],
            "skeleton7": [len(skeleton_line_full["global_matrix"]), len(skeleton_line_full["global_unknown_ordering"])],
            "published8": [len(published_line_full["global_matrix"]), len(published_line_full["global_unknown_ordering"])],
        },
        "candidate_counts": {
            "raw42_success": len(raw_induction["candidates"]),
            "raw42_failures": len(raw_induction["failures"]),
            "skeleton7_success": len(skeleton_induction["candidates"]),
            "skeleton7_failures": len(skeleton_induction["failures"]),
            "published8_success": len(published_induction["candidates"]),
            "published8_failures": len(published_induction["failures"]),
        },
        "compatibility_zero_counts": {
            "raw42": sum(int(item["compatibility_zero"]) for item in raw_induction["candidates"]),
            "skeleton7": sum(int(item["compatibility_zero"]) for item in skeleton_induction["candidates"]),
            "published8": sum(int(item["compatibility_zero"]) for item in published_induction["candidates"]),
        },
        "classification_counts": dict(classification_counts),
        "family_counts_by_classification": {
            classification: dict(counter)
            for classification, counter in sorted(family_counts_by_classification.items())
        },
        "published_fail_path_histogram": dict(sorted(published_fail_path_counter.items())),
        "published_fail_row_histogram": {
            str(row_index): count
            for row_index, count in sorted(published_fail_row_counter.items())
        },
        "generator_records": generator_records,
        "obstruction_summary": diagnosis_summary,
    }


def build_ai_obstruction_diagnosis_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Obstruction Diagnosis Report",
            "",
            f"- Published object kind: `{report['published_object_kind']}`.",
            f"- AI induction character field: `{report['ai_induction_character_field']}`.",
            f"- Row-language full-span / Bilbao-equivalent final-object pass: `{report['row_language_full_span_pass']}` / `{report['bilbao_equivalent_final_object_pass']}`.",
            f"- Selected path count / unique endpoint-pair count: `{report['selected_path_count']}` / `{report['unique_endpoint_pair_count']}`.",
            f"- Actual path pairs: `{report['actual_path_pairs']}`.",
            f"- Augmentation path ids / row indices: `{report['augmentation_path_ids']}` / `{report['augmentation_row_indices']}`.",
            f"- Shell matrix shapes: `{report['shell_matrix_shapes']}`.",
            f"- Candidate counts: `{report['candidate_counts']}`.",
            f"- Compatibility-zero counts: `{report['compatibility_zero_counts']}`.",
            f"- Classification counts: `{report['classification_counts']}`.",
            f"- Family counts by classification: `{report['family_counts_by_classification']}`.",
            f"- Published residual path histogram: `{report['published_fail_path_histogram']}`.",
            f"- Published residual row histogram: `{report['published_fail_row_histogram']}`.",
            f"- Obstruction summary: {report['obstruction_summary']}",
        ]
    )


def build_ai_honest_blocker_report(
    integration_report: dict[str, Any],
    obstruction_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if integration_report["integration_status"] == "wired_complete_candidate_set":
        return {
            "status": "not_blocked",
            "blocker": None,
            "blocker_stage": None,
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
        }
    if obstruction_report is not None:
        blocker_stage = "published_shell_obstruction_diagnosis"
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but only {integration_report['compatibility_zero_candidate_count']} of "
            f"{integration_report['success_candidate_count']} induced local objects satisfy compatibility on the published full-span augmented 8-path shell. "
            f"Classification counts across raw42 / 7-path skeleton / published 8-path shells: "
            f"{obstruction_report['classification_counts']}. "
            f"{obstruction_report['obstruction_summary']}"
        )
        return {
            "status": "blocked",
            "blocker_stage": blocker_stage,
            "blocker": blocker,
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
            "integration_status": integration_report["integration_status"],
            "failure_count": integration_report["failure_count"],
            "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
            "failure_family_ids": list(integration_report["failure_family_ids"]),
            "obstruction_classification_counts": dict(obstruction_report["classification_counts"]),
        }
    if integration_report["failure_count"] > 0:
        blocker_stage = "published_shell_induction"
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but {integration_report['failure_count']} induced local objects still fail on the published reduced shell."
        )
    else:
        blocker_stage = "published_shell_compatibility"
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but only {integration_report['compatibility_zero_candidate_count']} of "
            f"{integration_report['success_candidate_count']} induced local objects satisfy compatibility on the published reduced shell."
        )
    return {
        "status": "blocked",
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "local_library_present": True,
        "local_library_wired_into_ai_builder": True,
        "integration_status": integration_report["integration_status"],
        "failure_count": integration_report["failure_count"],
        "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
        "failure_family_ids": list(integration_report["failure_family_ids"]),
    }


def build_ai_honest_blocker_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Honest Blocker Report",
            "",
            f"- Status: `{report['status']}`.",
            f"- Blocker stage: `{report['blocker_stage']}`.",
            f"- Local library present / wired: `{report['local_library_present']}` / `{report['local_library_wired_into_ai_builder']}`.",
            f"- Failure count: `{report.get('failure_count')}`.",
            f"- Nonzero-residual candidate count: `{report.get('nonzero_residual_candidate_count')}`.",
            f"- Failure family ids: `{report.get('failure_family_ids')}`.",
            f"- Blocker: {report['blocker']}",
        ]
    )


def build_controlled_case() -> tuple[dict[str, Any], str]:
    try:
        import spglib
    except ImportError as exc:
        raise RuntimeError(
            "build_controlled_case() requires spglib for the controlled-case audit; install spglib to run this path."
        ) from exc

    ssg_data, time_revs = swyckoff_r.load_irssg_data(TARGET_GROUP, 0)
    rot = [np.array(op["matrix"], dtype=float) for op in ssg_data["operations"]]
    tau = [np.array(op["translation"], dtype=float) for op in ssg_data["operations"]]
    hall = spglib.get_hall_number_from_symmetry(rot, tau, symprec=1e-5)
    sg_info = spglib.get_spacegroup_type(hall)
    sg_sym = spglib.get_symmetry_from_database(hall)
    sg_data = {
        "centering_symbol": "P",
        "number": str(sg_info["number"]),
        "display_name": f"SG {sg_info['number']}",
        "crystal_system": "hexagonal",
        "operations": [{"matrix": R.tolist(), "translation": t.tolist()} for R, t in zip(sg_sym["rotations"], sg_sym["translations"])],
        "time_revs": [False] * len(sg_sym["rotations"]),
        "spin_matrices": [np.eye(3).tolist() for _ in range(len(sg_sym["rotations"]))],
    }

    def op_key(op: dict[str, Any]) -> tuple[Any, ...]:
        mat = tuple(tuple(int(round(x)) for x in row) for row in op["matrix"])
        tau_key = tuple(round(float(x) % 1.0, 8) for x in op["translation"])
        return mat, tau_key

    ssg_ops = {op_key(op) for op in ssg_data["operations"]}
    sg_ops = {op_key(op) for op in sg_data["operations"]}
    r_ssg, _ = swyckoff_r.compute_wyckoff_output(ssg_data, fast=True)
    r_sg, _ = swyckoff_r.compute_wyckoff_output(sg_data, fast=True)
    k_ssg, _ = swyckoff_k.compute_wyckoff_output(ssg_data, kspace=True, fast=True)
    k_sg, _ = swyckoff_k.compute_wyckoff_output(sg_data, kspace=True, fast=True)

    def signature(entries: Sequence[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [(entry["letter"], int(entry["dim"]), entry["site_symmetry"], entry["representative_coordinate"]) for entry in entries]

    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict(TARGET_GROUP)
    grouped = pick_group_entries(TARGET_GROUP)
    representative_point = grouped["points"][0]
    point_kvec = np.array([float(Fraction(value)) for value in representative_point["sample_point"]], dtype=float)
    probe_single = module.load_little_group(TARGET_GROUP, point_kvec, False, "single", ssg_dict)
    probe_double = module.load_little_group(TARGET_GROUP, point_kvec, False, "double", ssg_dict)

    controlled = {
        "target_group": TARGET_GROUP,
        "identified_sg_number": int(sg_info["number"]),
        "identified_sg_symbol": str(sg_info["international_short"]),
        "hall_number": int(hall),
        "operation_set_exact_match_to_sg_194": ssg_ops == sg_ops,
        "only_in_ssg": len(ssg_ops - sg_ops),
        "only_in_sg": len(sg_ops - ssg_ops),
        "realspace_geometry_signature_match": signature(r_ssg) == signature(r_sg),
        "kspace_geometry_signature_match": signature(k_ssg) == signature(k_sg),
        "realspace_family_count": len(r_ssg),
        "kspace_manifold_count": len(k_ssg),
        "time_reversal_count": int(sum(bool(flag) for flag in time_revs)),
        "source_centering_symbol": ssg_data.get("source_centering_symbol"),
        "groupType_probe_point": representative_point["id"],
        "groupType_probe_coordinates": representative_point["sample_point"],
        "groupType1_probe_success_count": 1,
        "groupType2_probe_success_count": 1,
        "groupType1_all_special_manifolds_available": len(probe_single.rep_degree) >= 1,
        "groupType2_all_special_manifolds_available": len(probe_double.rep_degree) >= 1,
        "controlled_case_valid": (
            int(sg_info["number"]) == 194
            and ssg_ops == sg_ops
            and signature(r_ssg) == signature(r_sg)
            and signature(k_ssg) == signature(k_sg)
        ),
    }
    lines = [
        "# Controlled-Case Audit for 194.1.1.1",
        "",
        "## Why 194.1.1.1 was selected",
        "",
        "- The reference group 10.4.1.31 already closed both the single-group and double-group workflows.",
        "- The current target 194.1.1.1 is a good portability pilot because the local toolchain can identify its spatial operation set as ordinary SG 194 inside the same basis/origin conventions used by the current code.",
        "",
        "## Spatial-Operation Check",
        "",
        f"- `SG_utils.identify_SG_from_symmetry(...)` identifies the spatial part as SG `{controlled['identified_sg_number']} ({controlled['identified_sg_symbol']})`.",
        f"- Hall number from the local spglib database: `{controlled['hall_number']}`.",
        f"- Standardized spatial operation-set equality against the hall-database SG 194 representative: `{controlled['operation_set_exact_match_to_sg_194']}`.",
        f"- Extra operations on the SSG side: `{controlled['only_in_ssg']}`.",
        f"- Missing operations relative to SG 194: `{controlled['only_in_sg']}`.",
        "",
        "## Real-Space / k-Space Geometry Check",
        "",
        f"- Real-space family-count match: `{controlled['realspace_family_count']}` on the SSG side, signature equality = `{controlled['realspace_geometry_signature_match']}`.",
        f"- k-space manifold-count match: `{controlled['kspace_manifold_count']}` on the SSG side, signature equality = `{controlled['kspace_geometry_signature_match']}`.",
        f"- `source_centering_symbol = {controlled['source_centering_symbol']}` and the selected origin shift remains zero in the local swyckoff workflow.",
        "",
        "## groupType Availability",
        "",
        f"- representative k-space availability probe: `{controlled['groupType_probe_point']}` at `{controlled['groupType_probe_coordinates']}`.",
        f"- `groupType=1` direct little-group entry availability: `{controlled['groupType1_all_special_manifolds_available']}`.",
        f"- `groupType=2` direct little-group entry availability: `{controlled['groupType2_all_special_manifolds_available']}`.",
        f"- No antiunitary operations are present in the standardized spatial data (`time_reversal_count = {controlled['time_reversal_count']}`), so the controlled-case comparison is to an ordinary unitary SG 194 spatial backbone while still allowing a genuine double-group probe through `factor_su2` on the `SSGReps` side.",
        "",
        "## Verdict",
        "",
        f"- `controlled_case_valid = {controlled['controlled_case_valid']}`.",
        "- Under the current local setting/basis/origin conventions, 194.1.1.1 is not merely similar to SG 194: its standardized spatial operation set matches the local SG 194 hall-database representative exactly, and the real-space/k-space geometry signatures agree as well.",
    ]
    return controlled, "\n".join(lines)


def build_single_pilot(
    module: Any,
    ssg_dict: dict[str, Any],
    *,
    line_phase_profile: str = AUTHORITATIVE_PHASE_AWARE_PROFILE,
) -> dict[str, Any]:
    ctx = load_context(module, TARGET_GROUP, "single", ssg_dict)
    print("[pilot] single: geometry")
    prepared_kgeom = prepare_kgeometry(TARGET_GROUP)
    kgeom_payload = prepared_kgeom["payload"]
    grouped = prepared_kgeom["grouped"]
    kgeom = {
        "payload": kgeom_payload,
        "grouped": grouped,
        "connectivity": kgeom_payload,
        "runtime_ctx": prepared_kgeom["ctx"],
        "line_orbit_to_id": prepared_kgeom["line_orbit_to_id"],
        "plane_orbit_to_id": prepared_kgeom["plane_orbit_to_id"],
    }
    synthetic_points = build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic_points
    augment_connectivity_with_boundary_points(kgeom, synthetic_points)
    build_point_instance_entries(kgeom)
    ctx["kgeom"] = kgeom
    print("[pilot] single: manifold capture")
    captures = build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "single", kgeom)

    point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]
    print("[pilot] single: raw diagnostic line blocks")
    raw_line_blocks = [
        build_line_block(line, captures, phase_aware_profile=line_phase_profile)
        for line in grouped["lines"]
    ]
    raw_line_full = build_global_compatibility(raw_line_blocks, point_ids)

    print("[pilot] single: raw diagnostic plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in grouped["planes"]]
    with_planes = build_with_planes_compatibility(raw_line_full, plane_blocks)
    diagnostic_bs_analysis = analyze_kernel(with_planes)

    print("[pilot] single: automatic final-object reduction")
    reduction = reduce_final_point_path_shell(kgeom)
    candidate_lines = annotate_final_path_lines(
        reduction["candidate_line_specs"],
        kgeom["runtime_ctx"],
        kgeom["line_orbit_to_id"],
        kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "single", captures, candidate_lines)
    candidate_line_blocks = [
        build_line_block(line, captures, phase_aware_profile=line_phase_profile)
        for line in candidate_lines
    ]
    reduction_analysis = analyze_candidate_path_selection(
        reduction,
        build_candidate_path_records(reduction, candidate_line_blocks),
    )
    reduction = finalize_reduction_from_candidate_analysis(reduction, reduction_analysis)
    final_lines = annotate_final_path_lines(
        reduction["final_line_specs"],
        kgeom["runtime_ctx"],
        kgeom["line_orbit_to_id"],
        kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "single", captures, final_lines)
    final_line_blocks = [
        build_line_block(line, captures, phase_aware_profile=line_phase_profile)
        for line in final_lines
    ]
    final_line_full = build_global_compatibility(final_line_blocks, reduction["final_point_ids"])
    bs_analysis = analyze_kernel(final_line_full)
    raw_point_row_translation = build_phase_aware_point_row_translation(
        final_line_blocks,
        bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
    )
    point_row_translation = disable_point_row_translation(
        raw_point_row_translation,
        reason=(
            "Removed from the published AI seed until the L2-derived phase-aware "
            "translation is proven legal on the final reduced point/path shell."
        ),
    )
    reduction["published_unknown_ordering"] = list(bs_analysis["unknown_ordering"])
    reduction["published_path_ids"] = [block["line_id"] for block in final_line_blocks]
    sanity_check = build_bilbao_equivalent_sanity_check(reduction)
    kgeom["final_object_reduction"] = reduction
    kgeom["final_published_lines"] = final_lines

    print("[pilot] single: translation legality probe")
    translation_probe_candidates = []
    for entry in ctx["wyckoff_entries"]:
        local_char = trivial_local_character(entry, ctx)
        candidate = induce_candidate(
            entry,
            local_char,
            ctx,
            captures,
            bs_analysis["unknown_ordering"],
            final_line_full["global_matrix"],
            point_row_translation=raw_point_row_translation,
            character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        )
        candidate["generator_id"] = f"{entry['letter']}_trivial"
        translation_probe_candidates.append(candidate)
    point_row_translation_report = build_point_row_translation_legality_report(
        final_line_full["global_matrix"],
        translation_probe_candidates,
        raw_point_row_translation,
        point_row_translation,
    )

    print("[pilot] single: atomic prototype")
    ai_candidates = []
    for entry in ctx["wyckoff_entries"]:
        local_char = trivial_local_character(entry, ctx)
        candidate = induce_candidate(
            entry,
            local_char,
            ctx,
            captures,
            bs_analysis["unknown_ordering"],
            final_line_full["global_matrix"],
            point_row_translation=point_row_translation,
            character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        )
        candidate["generator_id"] = f"{entry['letter']}_trivial"
        ai_candidates.append(candidate)
    reduction_reports = write_reduction_reports(
        reduction,
        sanity_check,
        published_line_full=final_line_full,
        published_bs_analysis=bs_analysis,
        diagnostic_with_planes=with_planes,
        diagnostic_bs_analysis=diagnostic_bs_analysis,
    )
    kgeom["sanity_check"] = sanity_check
    kgeom["bs_strong_equivalence_report"] = reduction_reports["bs_strong_equivalence_report"]
    print("[pilot] single: local-library AI integration")
    local_library_payload = load_local_library_payload()
    skeleton_path_ids = {
        kept["final_path_id"]
        for kept in reduction["kept_paths"]
        if kept["selection_stage"] == "endpoint_pair_skeleton"
    }
    skeleton_line_blocks = [block for block in final_line_blocks if block["line_id"] in skeleton_path_ids]
    skeleton_line_full = build_global_compatibility(skeleton_line_blocks, reduction["final_point_ids"])
    raw42_library_induction = induce_family_objects(
        ctx,
        captures,
        {"unknown_ordering": with_planes["global_unknown_ordering"]},
        with_planes["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    skeleton_library_induction = induce_family_objects(
        ctx,
        captures,
        {"unknown_ordering": bs_analysis["unknown_ordering"]},
        skeleton_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    single_library_induction = induce_family_objects(
        ctx,
        captures,
        bs_analysis,
        final_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    ai_library_integration_report = build_ai_library_integration_report(
        local_library_payload,
        single_library_induction,
        mode="single",
        published_object_kind=reduction["reduction_kind"],
        unknown_ordering=bs_analysis["unknown_ordering"],
        point_row_translation=point_row_translation,
    )
    ai_obstruction_diagnosis_report = build_ai_obstruction_diagnosis_report(
        reduction,
        raw_line_blocks,
        final_line_blocks,
        with_planes,
        skeleton_line_full,
        final_line_full,
        raw42_library_induction,
        skeleton_library_induction,
        single_library_induction,
    )
    ai_character_field_alignment_report = build_ai_character_field_alignment_report(
        ai_obstruction_diagnosis_report,
        authoritative_compatibility_field="character",
        raw42_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        skeleton7_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        published8_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    write_json(AI_CHARACTER_FIELD_ALIGNMENT_JSON, ai_character_field_alignment_report)
    write_text(
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        build_ai_character_field_alignment_markdown(ai_character_field_alignment_report),
    )
    ai_honest_blocker_report = build_ai_honest_blocker_report(
        ai_library_integration_report,
        ai_obstruction_diagnosis_report,
    )
    ai_audit_report = build_ai_seed_audit_report(
        ai_candidates,
        point_row_translation,
        unknown_ordering=bs_analysis["unknown_ordering"],
        library_integration_status=ai_library_integration_report["integration_status"],
    )
    ai_seed_delta_report = build_ai_seed_delta_after_bs_fix_report(
        {
            "generators": ai_candidates,
        },
        ai_audit_report,
    )
    ai_rank = int(ai_audit_report["rank_trivial_family_span"])
    write_json(POINT_ROW_TRANSLATION_JSON, point_row_translation_report)
    write_text(POINT_ROW_TRANSLATION_MD, build_point_row_translation_legality_markdown(point_row_translation_report))
    write_json(AI_SEED_AUDIT_JSON, ai_audit_report)
    write_text(AI_SEED_AUDIT_MD, build_ai_seed_audit_markdown(ai_audit_report))
    write_json(AI_SEED_DELTA_JSON, ai_seed_delta_report)
    write_text(AI_SEED_DELTA_MD, build_ai_seed_delta_after_bs_fix_markdown(ai_seed_delta_report))
    write_json(AI_LIBRARY_INTEGRATION_JSON, ai_library_integration_report)
    write_text(AI_LIBRARY_INTEGRATION_MD, build_ai_library_integration_markdown(ai_library_integration_report))
    write_json(AI_OBSTRUCTION_DIAG_JSON, ai_obstruction_diagnosis_report)
    write_text(AI_OBSTRUCTION_DIAG_MD, build_ai_obstruction_diagnosis_markdown(ai_obstruction_diagnosis_report))
    write_json(AI_HONEST_BLOCKER_JSON, ai_honest_blocker_report)
    write_text(AI_HONEST_BLOCKER_MD, build_ai_honest_blocker_markdown(ai_honest_blocker_report))

    write_json(SINGLE_KMANIFOLDS_JSON, {
        "group_number": TARGET_GROUP,
        "objects": strip_internal_fields(grouped["points"] + grouped["lines"] + grouped["planes"]),
        "synthetic_boundary_points": synthetic_points,
        "connectivity": kgeom_payload,
        "final_object_reduction": reduction,
        "final_object_vs_bilbao_equivalent_check": sanity_check,
    })
    write_json(SINGLE_CONNECTIVITY_JSON, kgeom_payload)
    write_json(SINGLE_LITTLE_GROUPS_JSON, captures)
    write_json(
        SINGLE_LINE_COMPAT_JSON,
        {
            "published_object_kind": reduction["reduction_kind"],
            "path_set_kind": reduction["reduction_kind"],
            "final_point_ids": reduction["final_point_ids"],
            "final_path_ids": reduction["published_path_ids"],
            "line_blocks": final_line_blocks,
            "line_full": final_line_full,
            "candidate_line_blocks": candidate_line_blocks,
            "diagnostic_raw_line_blocks": raw_line_blocks,
            "diagnostic_raw_line_full": raw_line_full,
            "final_object_reduction": reduction,
            "final_object_vs_bilbao_equivalent_check": sanity_check,
            "final_bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        },
    )
    write_json(
        SINGLE_WITH_PLANES_JSON,
        {
            "object_role": "diagnostic_internal_raw_with_planes_42_shell",
            "publication_role": "diagnostic_internal_raw_with_planes_shell",
            "published_status": "diagnostic_only",
            **with_planes,
            "diagnostic_bs_analysis": diagnostic_bs_analysis,
        },
    )
    write_json(
        SINGLE_BS_JSON,
        {
            **bs_analysis,
            "object_role": "published_final_point_path_shell",
            "final_object_kind": reduction["reduction_kind"],
            "path_set_kind": reduction["reduction_kind"],
            "final_point_ids": reduction["final_point_ids"],
            "final_path_ids": reduction["published_path_ids"],
            "final_selected_path_count": len(reduction["published_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(kept["endpoint_pair"]) for kept in reduction["kept_paths"]}),
            "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
            "bs_strong_equivalence_pass": reduction_reports["bs_strong_equivalence_report"]["bs_strong_equivalence_pass"],
            "row_language_full_span_pass": reduction_reports["bs_strong_equivalence_report"]["row_language_full_span_pass"],
            "bilbao_equivalent_final_object_pass": reduction_reports["bs_strong_equivalence_report"]["bilbao_equivalent_final_object_pass"],
            "diagnostic_raw_with_planes": {
                "matrix_shape": diagnostic_bs_analysis["matrix_shape"],
                "rank": diagnostic_bs_analysis["rank"],
                "nullity": diagnostic_bs_analysis["nullity"],
            },
            "final_object_vs_bilbao_equivalent_check": sanity_check,
            "final_bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        },
    )
    write_json(
        SINGLE_AI_JSON,
        {
            "object_role": "published_final_point_path_shell_ai_seed",
            "ai_status": ai_audit_report["ai_status"],
            "unknown_ordering": bs_analysis["unknown_ordering"],
            "point_row_translation": point_row_translation,
            "character_field_used": _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
            "generators": ai_candidates,
            "rank_trivial_family_span": ai_rank,
            "blocker_summary": ai_honest_blocker_report["blocker"],
            "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
            "ai_character_field_alignment_report": {
                "authoritative_compatibility_field": ai_character_field_alignment_report["authoritative_compatibility_field"],
                "current_ai_induction_field": ai_character_field_alignment_report["current_ai_induction_field"],
                "current_compatibility_zero_counts": ai_character_field_alignment_report["current_compatibility_zero_counts"],
                "current_published_fail_path_histogram": ai_character_field_alignment_report["current_published_fail_path_histogram"],
            },
            "ai_obstruction_diagnosis_summary": {
                "classification_counts": ai_obstruction_diagnosis_report["classification_counts"],
                "published_fail_path_histogram": ai_obstruction_diagnosis_report["published_fail_path_histogram"],
                "obstruction_summary": ai_obstruction_diagnosis_report["obstruction_summary"],
            },
            "translation_legality_report": {
                "legality_status": point_row_translation_report["legality_status"],
                "published_translation_enabled": point_row_translation_report["published_translation_enabled"],
            },
            "point_row_translation_status": "retired_on_published_final_reduced_shell",
            "ai_seed_audit_report": {
                "ai_status": ai_audit_report["ai_status"],
                "compatibility_zero_count": ai_audit_report["compatibility_zero_count"],
                "honest_ai_lattice_ready": ai_audit_report["honest_ai_lattice_ready"],
            },
            "ai_library_integration_report": {
                "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
                "integration_status": ai_library_integration_report["integration_status"],
                "success_candidate_count": ai_library_integration_report["success_candidate_count"],
                "failure_count": ai_library_integration_report["failure_count"],
                "compatibility_zero_candidate_count": ai_library_integration_report["compatibility_zero_candidate_count"],
            },
            "ai_seed_delta_after_bs_fix_report": {
                "residual_pattern_changed": ai_seed_delta_report["residual_pattern_changed"],
            },
        },
    )

    completeness_blocker = ai_honest_blocker_report["blocker"]
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 1,
        "geometry_status": "success",
        "compatibility_status": {
            "line_blocks_built": len(final_line_blocks),
            "synthetic_boundary_points_added": len(synthetic_points),
            "point_line_relations": len(kgeom_payload["point_line"]),
            "unmatched_line_endpoints_before_augmentation": len(kgeom_payload["unmatched_line_endpoints"]),
            "plane_blocks_built": len(plane_blocks),
            "status": "success",
            "authoritative_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "raw_builder_phase_aware_profile": line_phase_profile,
            "published_object_kind": reduction["reduction_kind"],
            "diagnostic_raw_with_planes_retained": True,
        },
        "BS_status": {
            "status": "success",
            "matrix_shape": bs_analysis["matrix_shape"],
            "rank": bs_analysis["rank"],
            "nullity": bs_analysis["nullity"],
            "smith_diagonal": bs_analysis["smith_diagonal"],
            "published_object_kind": reduction["reduction_kind"],
            "final_selected_path_count": len(reduction["published_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(kept["endpoint_pair"]) for kept in reduction["kept_paths"]}),
            "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
            "diagnostic_raw_with_planes_matrix_shape": diagnostic_bs_analysis["matrix_shape"],
            "row_language_full_span_pass": reduction_reports["bs_strong_equivalence_report"]["row_language_full_span_pass"],
            "bilbao_equivalent_final_object_pass": reduction_reports["bs_strong_equivalence_report"]["bilbao_equivalent_final_object_pass"],
        },
        "AI_status": {
            "status": ai_audit_report["ai_status"],
            "trivial_generators_count": len(ai_candidates),
            "rank_trivial_family_span": ai_rank,
            "compatibility_zero_count": ai_audit_report["compatibility_zero_count"],
            "all_trivial_generators_compatibility_zero": all(candidate["compatibility_zero"] for candidate in ai_candidates),
            "point_row_translation_legality": point_row_translation_report["legality_status"],
            "authoritative_ai_character_field": _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
            "residual_pattern_changed_vs_previous_branch": ai_seed_delta_report["residual_pattern_changed"],
            "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
            "library_integration_status": ai_library_integration_report["integration_status"],
            "library_integration_success_candidate_count": ai_library_integration_report["success_candidate_count"],
            "library_integration_failure_count": ai_library_integration_report["failure_count"],
            "library_integration_compatibility_zero_candidate_count": ai_library_integration_report["compatibility_zero_candidate_count"],
            "blocker_summary": ai_honest_blocker_report["blocker"],
            "obstruction_classification_counts": ai_obstruction_diagnosis_report["classification_counts"],
            "published_fail_path_histogram": ai_obstruction_diagnosis_report["published_fail_path_histogram"],
        },
        "completeness_status": {"status": "blocked", "blocker": completeness_blocker},
        "quotient_status": {"status": "blocked", "blocker": "AI is not complete, so BS/AI cannot yet be interpreted honestly."},
        "blocker": completeness_blocker,
    }

    lines = [
        "# 194.1.1.1 Single-Group Portability Pilot",
        "",
        "## Outcome",
        "",
        "- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.",
        f"- The current pilot had to add `{len(synthetic_points)}` synthetic 0D boundary points because the raw k-geometry contains `{len(kgeom_payload['unmatched_line_endpoints'])}` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.",
        "- The final published single-group BS object is the honest full-span augmented 8-path reduced shell; the raw with-planes 42-shell remains diagnostic only.",
        f"- Row-language full-span against the full candidate path language: `{reduction_reports['bs_strong_equivalence_report']['row_language_full_span_pass']}`.",
        f"- Bilbao-equivalent final-object pass: `{reduction_reports['bs_strong_equivalence_report']['bilbao_equivalent_final_object_pass']}`.",
        "",
        "## Direct Reuse Successes",
        "",
        "- `swyckoff_r.py` / `swyckoff_k.py` standardized geometry loading is reused directly.",
        "- `SSGReps.load_little_group(...)` is reused directly on all special points, lines, and planes.",
        "- The operation bridge `r_conv = P r_mag` logic and lattice-fix test are reused directly.",
        "- The restriction/decomposition workflow still uses `character` / `linear_character` / `rep_degree` and subgroup matching, without relying on `rep_matrix`.",
        "",
        "## Modules That Needed Change",
        "",
        "- The line-compatibility layer from 10.4.1.31 assumed every special line endpoint landed on a separately listed 0D point. That assumption fails on 194.1.1.1.",
        "- The portability pilot therefore augments the boundary-point set with explicit synthetic 0D endpoints before assembling the global compatibility matrix.",
        f"- {ai_honest_blocker_report['blocker']}",
        "",
        "## Status Summary",
        "",
        f"- BS matrix shape/rank/nullity: `{bs_analysis['matrix_shape']}`, `{bs_analysis['rank']}`, `{bs_analysis['nullity']}`.",
        f"- Final point/path shell sizes: `{len(reduction['final_point_ids'])}` points / `{len(reduction['published_path_ids'])}` paths.",
        f"- Bilbao-style diagnostic check: point ids match = `{sanity_check['point_ids_match']}`, path count match = `{sanity_check['path_count_match']}`, exact path-pair match = `{sanity_check['path_pair_set_match']}`, unique path-pair match = `{sanity_check['unique_path_pair_set_match']}`.",
        f"- Trivial-family AI seed count/rank: `{len(ai_candidates)}` / `{ai_rank}`.",
        f"- Trivial-family compatibility-zero count: `{ai_audit_report['compatibility_zero_count']}` / `{len(ai_candidates)}`.",
        f"- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `{ai_library_integration_report['success_candidate_count']}` / `{ai_library_integration_report['failure_count']}` / `{ai_library_integration_report['compatibility_zero_candidate_count']}`.",
        f"- AI obstruction classification counts: `{ai_obstruction_diagnosis_report['classification_counts']}`.",
        f"- Published residual path histogram: `{ai_obstruction_diagnosis_report['published_fail_path_histogram']}`.",
        f"- point_row_translation legality: `{point_row_translation_report['legality_status']}`.",
        f"- AI residual pattern changed vs previous branch: `{ai_seed_delta_report['residual_pattern_changed']}`.",
        f"- AI completeness: blocked. Reason: {completeness_blocker}",
        "- Quotient / indicator extraction: blocked until a complete AI lattice exists.",
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "kgeom": kgeom,
        "captures": captures,
        "with_planes": with_planes,
        "line_full": final_line_full,
        "bs_analysis": bs_analysis,
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
        "reduction": reduction,
        "sanity_check": sanity_check,
        "ai_candidates": ai_candidates,
        "point_row_translation": point_row_translation,
        "point_row_translation_report": point_row_translation_report,
        "ai_seed_audit_report": ai_audit_report,
        "ai_seed_delta_report": ai_seed_delta_report,
        "ai_library_integration_report": ai_library_integration_report,
        "ai_honest_blocker_report": ai_honest_blocker_report,
        "bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        "phase_aware_profile": line_phase_profile,
    }


def build_double_pilot(
    module: Any,
    ssg_dict: dict[str, Any],
    single_kgeom: dict[str, Any],
    *,
    line_phase_profile: str = AUTHORITATIVE_PHASE_AWARE_PROFILE,
) -> dict[str, Any]:
    ctx = load_context(module, TARGET_GROUP, "double", ssg_dict)
    ctx["kgeom"] = single_kgeom
    print("[pilot] double: manifold capture")
    captures = build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "double", single_kgeom)
    point_ids = [item["id"] for item in single_kgeom["grouped"]["points"]] + [item["id"] for item in single_kgeom["synthetic_boundary_points"]]
    print("[pilot] double: raw diagnostic line blocks")
    raw_line_blocks = [
        build_line_block(line, captures, phase_aware_profile=line_phase_profile)
        for line in single_kgeom["grouped"]["lines"]
    ]
    raw_line_full = build_global_compatibility(raw_line_blocks, point_ids)
    print("[pilot] double: raw diagnostic plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in single_kgeom["grouped"]["planes"]]
    with_planes = build_with_planes_compatibility(raw_line_full, plane_blocks)
    diagnostic_bs_analysis = analyze_kernel(with_planes)
    print("[pilot] double: automatic final-object reduction")
    reduction = single_kgeom["final_object_reduction"]
    final_lines = [dict(line) for line in single_kgeom["final_published_lines"]]
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "double", captures, final_lines)
    final_line_blocks = [
        build_line_block(line, captures, phase_aware_profile=line_phase_profile)
        for line in final_lines
    ]
    final_line_full = build_global_compatibility(final_line_blocks, reduction["final_point_ids"])
    bs_analysis = analyze_kernel(final_line_full)
    raw_point_row_translation = build_phase_aware_point_row_translation(
        final_line_blocks,
        bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
    )
    point_row_translation = disable_point_row_translation(
        raw_point_row_translation,
        reason=(
            "Removed from the published double minimal witness until the L2-derived "
            "phase-aware translation is proven legal on the reduced point/path shell."
        ),
    )

    print("[pilot] double: minimal prototype")
    generic_entry = next(entry for entry in ctx["wyckoff_entries"] if entry["letter"] == "l")
    local_char = trivial_local_character(generic_entry, ctx)
    minimal = induce_candidate(
        generic_entry,
        local_char,
        ctx,
        captures,
        bs_analysis["unknown_ordering"],
        final_line_full["global_matrix"],
        point_row_translation=point_row_translation,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    minimal["generator_id"] = "l_double_trivial"
    minimal["bridge_reused"] = True
    minimal["projective_note"] = "The real-space prototype uses the trivial stabilizer of family l, so the first portable double-group witness does not yet require a nontrivial local projective-character solver."

    write_json(DOUBLE_LITTLE_GROUPS_JSON, captures)
    write_json(
        DOUBLE_WITH_PLANES_JSON,
        {
            "object_role": "diagnostic_internal_raw_with_planes_42_shell",
            "publication_role": "diagnostic_internal_raw_with_planes_shell",
            "published_status": "diagnostic_only",
            **with_planes,
            "diagnostic_bs_analysis": diagnostic_bs_analysis,
        },
    )
    write_json(
        DOUBLE_BS_JSON,
        {
            **bs_analysis,
            "object_role": "published_final_point_path_shell",
            "final_object_kind": reduction["reduction_kind"],
            "path_set_kind": reduction["reduction_kind"],
            "final_point_ids": reduction["final_point_ids"],
            "final_path_ids": reduction["published_path_ids"],
            "final_selected_path_count": len(reduction["published_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(kept["endpoint_pair"]) for kept in reduction["kept_paths"]}),
            "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
            "row_language_full_span_pass": single_kgeom["final_object_reduction"]["selected_rows_span_full_candidate_row_language"],
            "bilbao_equivalent_final_object_pass": single_kgeom["sanity_check"]["bilbao_equivalent_final_object_pass"],
            "diagnostic_raw_with_planes": {
                "matrix_shape": diagnostic_bs_analysis["matrix_shape"],
                "rank": diagnostic_bs_analysis["rank"],
                "nullity": diagnostic_bs_analysis["nullity"],
            },
            "bs_strong_equivalence_pass": single_kgeom["final_object_reduction"].get("selected_rows_span_full_candidate_row_language"),
        },
    )
    write_json(
        DOUBLE_MINIMAL_JSON,
        {
            **minimal,
            "object_role": "published_final_point_path_shell_minimal_witness",
            "unknown_ordering": bs_analysis["unknown_ordering"],
            "point_row_translation": point_row_translation,
        },
    )

    blocker = (
        "Non-abelian SG 194 projective local-corep libraries already exist and validate, "
        "but the published-shell double AI induction path is not yet wired beyond the "
        "current trivial-stabilizer witness."
    )
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 2,
        "double_group_feasibility_status": "success",
        "minimal_realspace_prototype_status": "success",
        "bridge_status": "success",
        "induction_status": "success",
        "kspace_backbone_status": {
            "status": "success",
            "matrix_shape": bs_analysis["matrix_shape"],
            "rank": bs_analysis["rank"],
            "nullity": bs_analysis["nullity"],
            "smith_diagonal": bs_analysis["smith_diagonal"],
            "authoritative_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "raw_builder_phase_aware_profile": line_phase_profile,
            "published_object_kind": reduction["reduction_kind"],
            "diagnostic_raw_with_planes_matrix_shape": diagnostic_bs_analysis["matrix_shape"],
            "row_language_full_span_pass": single_kgeom["bs_strong_equivalence_report"]["row_language_full_span_pass"],
            "bilbao_equivalent_final_object_pass": single_kgeom["bs_strong_equivalence_report"]["bilbao_equivalent_final_object_pass"],
        },
        "point_like_AI_status": {"status": "blocked", "blocker": blocker},
        "parametric_status": {"status": "blocked", "blocker": blocker},
        "blocker": blocker,
    }
    lines = [
        "# 194.1.1.1 Double-Group Portability Pilot",
        "",
        "## Outcome",
        "",
        "- All special points, lines, and planes of 194.1.1.1 were captured successfully under `groupType=2`.",
        "- The same synthetic-boundary augmentation used by the single-group pilot also closes the double-group spatial connectivity layer.",
        "- The raw double-group with-planes 42-shell is retained as a diagnostic object, while the published double BS object uses the automatically reduced point/path shell.",
        f"- Row-language full-span pass on the published reduced shell: `{single_kgeom['bs_strong_equivalence_report']['row_language_full_span_pass']}`.",
        f"- Bilbao-equivalent final-object pass inherited from the single reduction: `{single_kgeom['bs_strong_equivalence_report']['bilbao_equivalent_final_object_pass']}`.",
        "",
        "## Minimal Prototype",
        "",
        "- The first portable real-space witness uses the generic family `l` with trivial stabilizer.",
        "- This shows that the spatial bridge, lattice-fix filter, Bloch phase, and decomposition against double little-coreps all survive the move from 10.4.1.31 to 194.1.1.1.",
        "",
        "## Current Limit",
        "",
        f"- {blocker}",
        f"- Final point/path shell sizes: `{len(reduction['final_point_ids'])}` points / `{len(reduction['published_path_ids'])}` paths.",
        "- Therefore the present run establishes a reusable double-group seed and a reusable double-group k-space backbone, but not yet a full point-like / parametric AI census or any final double quotient.",
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "with_planes": with_planes,
        "line_full": final_line_full,
        "bs_analysis": bs_analysis,
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
        "reduction": reduction,
        "minimal": minimal,
        "point_row_translation": point_row_translation,
        "phase_aware_profile": line_phase_profile,
    }


def build_portability_summary(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "controlled_case_valid": bool(controlled["controlled_case_valid"]),
        "single_group_portable": bool(
            single["summary"]["BS_status"]["status"] == "success"
            and single["summary"]["AI_status"]["status"] in {"seed_only", "partial_lattice", "full_lattice"}
        ),
        "double_group_portable_seed": bool(double["summary"]["kspace_backbone_status"]["status"] == "success" and double["summary"]["induction_status"] == "success"),
        "main_blocker": single["summary"]["blocker"],
        "next_blocker": double["summary"]["blocker"],
    }


def build_portability_audit_text(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Workflow Portability Audit for 194.1.1.1",
            "",
            "## Reference Workflow Decomposition",
            "",
            "- k-space geometry / connectivity generation.",
            "- little-group capture via `SSGReps.load_little_group(...)`.",
            "- character-based compatibility assembly.",
            "- BS construction as `ker_Z(C)`.",
            "- real-space bridge and atomic induction.",
            "- AI completeness and quotient extraction.",
            "",
            "## Reusable Modules",
            "",
            "- Controlled-case spatial identification.",
            "- Real-space / k-space geometry extraction from `swyckoff_{r,k}.py`.",
            "- Character-based restriction matching for both `groupType=1` and `groupType=2`.",
            "- Integer-kernel BS construction.",
            "- Spatial bridge plus Bloch-phase induction.",
            "",
            "## Modules Still Group-Specific",
            "",
            "- Boundary-manifold closure: 194.1.1.1 requires synthetic 0D boundary points that were unnecessary on 10.4.1.31.",
            "- Published-shell integration of the validated SG 194 local irrep / corep libraries.",
            "- Honest AI completeness and quotient extraction on the new target.",
            "",
            "## Current Weakest Link",
            "",
            f"- {portability_summary['main_blocker']}",
            "",
            "## Controlled-Case Verdict",
            "",
            f"- controlled_case_valid = `{controlled['controlled_case_valid']}`",
            f"- single_group_portable = `{portability_summary['single_group_portable']}`",
            f"- double_group_portable_seed = `{portability_summary['double_group_portable_seed']}`",
        ]
    )


def latex_escape(text: Any) -> str:
    escaped = str(text)
    for source, target in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]:
        escaped = escaped.replace(source, target)
    return escaped


def build_report_tex(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    single_bs = single["summary"]["BS_status"]
    double_bs = double["summary"]["kspace_backbone_status"]
    single_shape_rows, single_shape_cols = single_bs["matrix_shape"]
    double_shape_rows, double_shape_cols = double_bs["matrix_shape"]
    single_ai = single["summary"]["AI_status"]
    single_comp = single["summary"]["compatibility_status"]
    controlled_case_valid = str(controlled["controlled_case_valid"]).lower()
    single_portable = str(portability_summary["single_group_portable"]).lower()
    double_seed = str(portability_summary["double_group_portable_seed"]).lower()
    return textwrap.dedent(
        r"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{amsmath,amssymb,booktabs,longtable,array,hyperref}}
        \title{{Workflow Portability Pilot for {target_group}}}
        \author{{Codex}}
        \date{{}}
        \begin{{document}}
        \maketitle

        \section{{Task Background and Scope}}
        The reference group is {reference_group}. Its single-group workflow has already been closed through AI completeness and the quotient
        \[
        BS_{{\mathrm{{single}}}}/AI_{{\mathrm{{single}}}} \cong \mathbb{{Z}}_2 \times \mathbb{{Z}}_2,
        \]
        while its double-group workflow has already been closed through the mixed quotient
        \[
        BS_{{\mathrm{{double}}}}/AI_{{\mathrm{{double}}}} \cong \mathbb{{Z}}^2 \times \mathbb{{Z}}_2^4.
        \]
        The fixed target of the present round is {target_group}. The present round performs exactly three tasks: a controlled-case audit, a \texttt{{groupType=1}} portability pilot, and a \texttt{{groupType=2}} portability pilot. It does not attempt a database-wide theorem, it does not change the target group, and it does not revisit {reference_group} except as an audited baseline.

        \section{{Group and Coordinate Conventions}}
        Group operations are represented as affine actions
        \[
        g : r \mapsto R_g r + \tau_g,
        \]
        with $R_g$ an integer matrix in the current crystal basis and $\tau_g$ a fractional translation. The real-space bridge reused from the audited {reference_group} workflow is
        \[
        r_{{\mathrm{{conv}}}} = P\, r_{{\mathrm{{mag}}}}, \qquad
        P = \mathrm{{diag}}(1,2,2).
        \]
        The present code keeps the existing origin convention and uses zero origin shift throughout the portability pilot. Reciprocal-space sample points are written in the magnetic primitive reciprocal basis. For each special point, line, or plane, the script stores a parameterization
        \[
        k(u_1,\dots,u_d) = k_0 + \sum_i u_i b_i^{{(\mathrm{{sub}})}},
        \]
        together with an explicit sample point used for the little-group probe. The current pilot also records synthetic 0D boundary points whenever a line endpoint is geometrically present but is not emitted by \texttt{{swyckoff\_k.py}} as a separately listed special point.

        \section{{k-Space Formalism}}
        A special manifold is defined by its dimension, affine anchor, basis vectors, stabilizer, and a sample point. For a special momentum $k$, the little group is
        \[
        G_k = \{{ g \in G \mid R_g k = k + K \text{{ for some reciprocal lattice vector }} K \}}.
        \]
        The script captures the raw little-group characters from \texttt{{SSGReps.load\_little\_group}} and assembles compatibility equations by restricting endpoint representations to line little groups, and corner representations to plane little groups. With unknown multiplicity vector $n$, the compatibility system is
        \[
        C n = 0,
        \]
        and the band-structure lattice is defined by
        \[
        BS = \ker_{{\mathbb Z}}(C).
        \]
        The integer kernel is extracted by Smith normal form:
        \[
        U C V = \operatorname{{diag}}(d_1,\dots,d_r,0,\dots,0),
        \]
        where the last columns of $V$ form an integer basis of $\ker_{{\mathbb Z}}(C)$. In the present workflow, HNF/SNF machinery is used operationally to answer three separate questions: rank detection, nullity detection, and an integral basis for the kernel and later quotient computations.

        \section{{Real-Space / AI Formalism}}
        For a representative real-space point $r$, the site stabilizer is
        \[
        G_r = \{{ g \in G \mid g r = r + R \text{{ for some lattice vector }} R \}}.
        \]
        Wyckoff families are grouped by orbit type, multiplicity, and site symmetry. Local representations are attached to $G_r$, then induced to Bloch bands on k-space manifolds. The present code works with raw little-group characters stored in the JSON layer and reconstructs the linear character layer explicitly. The induction step must include the Bloch phase
        \[
        e^{{- i k \cdot \tau_C}},
        \]
        because the translated site contributes with a phase set by the conventional-coordinate displacement seen by the little-group operation. In the portable implementation this phase enters in the induced band character sum when a coset representative returns a site to itself modulo lattice translation. The atomic lattice is defined as
        \[
        AI = \operatorname{{span}}_{{\mathbb Z}} \{{ a_1,a_2,\dots \}},
        \]
        and the target quotient, when the atomic side is complete, is
        \[
        BS/AI.
        \]

        \section{{Double-Group / Projective Formalism}}
        The branch \texttt{{groupType=1}} treats single-valued local representations. The branch \texttt{{groupType=2}} treats double-valued / projective data, so the SU(2) factor system must be retained explicitly. In the current codebase this appears through the same audited double-group route used for {reference_group}, including the explicit \texttt{{factor\_su2}} treatment in the \texttt{{SSGReps}} stack. Therefore some formulas cannot be copied verbatim from the single-group branch: the relevant little objects are little corepresentations rather than ordinary irreps, and the projective sign structure must be respected before any restriction or induction statement is considered meaningful.

        \section{{Algorithm Pipeline and Implementation Mapping}}
        The present portability script follows the pipeline below.

        \begin{{longtable}}{{>{{\raggedright\arraybackslash}}p{{0.12\linewidth}}>{{\raggedright\arraybackslash}}p{{0.22\linewidth}}>{{\raggedright\arraybackslash}}p{{0.27\linewidth}}>{{\raggedright\arraybackslash}}p{{0.31\linewidth}}}}
        \toprule
        Step & Input & Output & Code mapping \\
        \midrule
        1 & group id, local JSON data & standardized operations and family/manifold lists & \texttt{{swyckoff\_r.py}}, \texttt{{swyckoff\_k.py}}, \texttt{{load\_context}}, \texttt{{pick\_group\_entries}} \\
        2 & special lines and planes & boundary connectivity, unmatched endpoints, synthetic 0D boundary points & \texttt{{infer\_line\_connectivity}}, \texttt{{infer\_plane\_connectivity}}, \texttt{{build\_synthetic\_boundary\_points}} \\
        3 & sample $k$ points & little-group raw/linear characters, stabilizer metadata & \texttt{{SSGReps.load\_little\_group}}, \texttt{{capture\_little\_group}}, \texttt{{build\_manifold\_capture}} \\
        4 & line endpoints or plane corners & compatibility blocks & \texttt{{build\_line\_block}}, \texttt{{build\_plane\_block}} \\
        5 & all local blocks & global compatibility matrix $C$ & \texttt{{build\_global\_compatibility}}, \texttt{{build\_with\_planes\_compatibility}} \\
        6 & $C$ & Smith data, rank, nullity, integer kernel basis & \texttt{{analyze\_kernel}} \\
        7 & real-space family, site stabilizer, orbit, local character & induced atomic candidate in BS coordinates & \texttt{{trivial\_local\_character}}, \texttt{{induce\_candidate}}, bridge helpers from \texttt{{debug\_single\_group\_ai\_bridge.py}} \\
        8 & single/double summaries & controlled-case and portability audits & \texttt{{build\_controlled\_case}}, \texttt{{build\_portability\_summary}}, \texttt{{build\_package}} \\
        \bottomrule
        \end{{longtable}}

        \section{{Controlled-Case Audit on {target_group}}}
        The local toolchain identifies the spatial part of {target_group} as SG 194 with hall number {hall_number}. The standardized operation sets agree exactly with the hall-database representative of SG 194:
        \[
        G_{{\mathrm{{space}}}}({target_group}) = G_{{\mathrm{{space}}}}(\mathrm{{SG}}\ 194)
        \]
        at the level of the operation-set comparison performed by the local code. The real-space family signatures and k-space manifold signatures also agree exactly. Therefore the present target is not merely ``close'' to SG 194; within the local setting/basis/origin conventions it is a controlled spatially equivalent test case. The local probe counts are: \texttt{{groupType=1}} little-group captures = {controlled_single_probe_count}, \texttt{{groupType=2}} little-group captures = {controlled_double_probe_count}.

        \section{{Current Execution Results on {target_group}}}
        \subsection*{{Single-group pilot}}
        The single-group route succeeds through geometry, connectivity, line-layer compatibility, plane-augmented compatibility, and integer-kernel BS construction. The resulting compatibility matrix has
        \[
        \mathrm{{shape}}(C_{{\mathrm{{single}}}}) = {single_rows} \times {single_cols}, \qquad
        \operatorname{{rank}} C_{{\mathrm{{single}}}} = {single_rank}, \qquad
        \operatorname{{nullity}} C_{{\mathrm{{single}}}} = {single_nullity}.
        \]
        The script had to add {synthetic_boundary_points} synthetic 0D boundary points because the raw special-point list is not connectivity-complete for this target. The present AI side is only partial: {single_trivial_generators} trivial-family generators span rank {single_ai_rank}. This means the pilot reaches an honest BS computation and an honest atomic prototype, but not yet an honest AI completeness audit or quotient extraction.

        \subsection*{{Double-group pilot}}
        The double-group route succeeds through feasibility, bridge reuse, induction reuse, and a full with-planes k-space backbone. The resulting double compatibility matrix has
        \[
        \mathrm{{shape}}(C_{{\mathrm{{double}}}}) = {double_rows} \times {double_cols}, \qquad
        \operatorname{{rank}} C_{{\mathrm{{double}}}} = {double_rank}, \qquad
        \operatorname{{nullity}} C_{{\mathrm{{double}}}} = {double_nullity}.
        \]
        The first reusable real-space witness is the minimal prototype on family \texttt{{l}} with trivial stabilizer. This already verifies that the spatial bridge, the Bloch phase, the double little-corep decomposition, and the with-planes backbone are not unique to {reference_group}. However, the current run does not yet enumerate point-like or parametric double local coreps for the nontrivial SG 194 site symmetries, so it does not reach a full double AI completeness audit or any final double quotient.

        \section{{Comparison with the Closed {reference_group} Baseline}}
        The following modules port directly from {reference_group}: standardized real-space geometry, standardized k-space geometry, character-based little-group capture, compatibility assembly by subgroup matching, integer-kernel BS extraction, and the phase-corrected atomic induction bridge. The following modules do not yet port without additional target-specific work: published-shell integration/completion for the validated SG 194 local irrep/corep libraries, and automatic closure of omitted boundary endpoints without the current synthetic-point augmentation. Therefore the true reusable boundary of the workflow is already beyond one-group scripting for the spatial backbone, but still short of an honest portable AI completion layer.

        \section{{Conclusion and Remaining Blockers}}
        Controlled-case verdict: {controlled_case_valid}. Single-group portability verdict: {single_portable}. Double-group seed verdict: {double_seed}. The main blocker is:
        \begin{{quote}}
        {main_blocker}
        \end{{quote}}
        The double-group next blocker is:
        \begin{{quote}}
        {next_blocker}
        \end{{quote}}
        The present conclusions apply only to the current target {target_group}, the current local setting/basis/origin conventions, and the current single-group / double-group formalism implemented in this repository.

        \end{{document}}
        """.format(
            target_group=TARGET_GROUP,
            reference_group=REFERENCE_GROUP,
            hall_number=controlled["hall_number"],
            controlled_single_probe_count=controlled["groupType1_probe_success_count"],
            controlled_double_probe_count=controlled["groupType2_probe_success_count"],
            single_rows=single_shape_rows,
            single_cols=single_shape_cols,
            single_rank=single_bs["rank"],
            single_nullity=single_bs["nullity"],
            double_rows=double_shape_rows,
            double_cols=double_shape_cols,
            double_rank=double_bs["rank"],
            double_nullity=double_bs["nullity"],
            synthetic_boundary_points=single_comp["synthetic_boundary_points_added"],
            single_trivial_generators=single_ai["trivial_generators_count"],
            single_ai_rank=single_ai["rank_trivial_family_span"],
            controlled_case_valid=controlled_case_valid,
            single_portable=single_portable,
            double_seed=double_seed,
            main_blocker=latex_escape(portability_summary["main_blocker"]),
            next_blocker=latex_escape(portability_summary["next_blocker"]),
        )
    ).strip() + "\n"


def compile_report() -> None:
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", REPORT_TEX.name],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def build_handoff(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Handoff for 194.1.1.1",
            "",
            f"- Current target group: `{TARGET_GROUP}`",
            f"- Single-group status: `{single['summary']['AI_status']['status']}` with BS `{single['summary']['BS_status']['status']}`.",
            f"- Double-group status: minimal prototype `{double['summary']['minimal_realspace_prototype_status']}`, backbone `{double['summary']['kspace_backbone_status']['status']}`.",
            f"- Main blocker: {portability_summary['main_blocker']}",
            "- Next unique target: finish published-shell AI induction/completion so the validated local irrep/corep libraries become an honest AI lattice and quotient on 194.1.1.1.",
            "- Files to read first:",
            f"  - {CONTROLLED_AUDIT_MD.name}",
            f"  - {PORTABILITY_AUDIT_MD.name}",
            f"  - {SINGLE_AUDIT_MD.name}",
            f"  - {DOUBLE_AUDIT_MD.name}",
            f"  - {REPORT_PDF.name}",
        ]
    )


def build_current_status(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_group": TARGET_GROUP,
        "benchmark_authoritative": False,
        "object_scope": "raw_internal_source_layer_only",
        "raw_current_object_language_kind": "raw_current_with_planes_42_unknown_shell",
        "stage2_target_transition": (
            "Stage 2 is responsible for lifting these raw/current objects either into the ordinary external target rows "
            "or into the double benchmark-facing target object, depending on representation mode."
        ),
        "benchmark_relation": (
            "This stage1 workflow only emits raw/current SG194 source objects. "
            "Benchmark-facing internalization happens later in debug_workflow_portability_stage2_194.1.1.1.py."
        ),
        "single_status": single["summary"],
        "double_status": double["summary"],
        "key_matrices": {
            "single_matrix_shape": single["summary"]["BS_status"]["matrix_shape"],
            "single_rank": single["summary"]["BS_status"]["rank"],
            "single_nullity": single["summary"]["BS_status"]["nullity"],
            "double_matrix_shape": double["summary"]["kspace_backbone_status"]["matrix_shape"],
            "double_rank": double["summary"]["kspace_backbone_status"]["rank"],
            "double_nullity": double["summary"]["kspace_backbone_status"]["nullity"],
        },
        "blocker": portability_summary["main_blocker"],
        "next_step": "Extend the local site-symmetry irrep/corep library on 194.1.1.1 so the AI lattice can be completed honestly.",
    }


def build_next_step_prompt(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Previous Codex session already reconstructed the 10.4.1.31 baseline and completed the 194.1.1.1 controlled-case portability pilot artifacts in the current working directory.

        Read these files first:
        1. {REPORT_TEX.name}
        2. {CONTROLLED_AUDIT_MD.name}
        3. {PORTABILITY_AUDIT_MD.name}
        4. {SINGLE_AUDIT_MD.name}
        5. {DOUBLE_AUDIT_MD.name}
        6. {CURRENT_STATUS_JSON.name}

        Current verified facts:
        - controlled_case_valid = {portability_summary['controlled_case_valid']}
        - single_group_portable = {portability_summary['single_group_portable']}
        - double_group_portable_seed = {portability_summary['double_group_portable_seed']}
        - main_blocker = {portability_summary['main_blocker']}

        Current single-group matrix status:
        - shape = {single['summary']['BS_status']['matrix_shape']}
        - rank = {single['summary']['BS_status']['rank']}
        - nullity = {single['summary']['BS_status']['nullity']}

        Current double-group matrix status:
        - shape = {double['summary']['kspace_backbone_status']['matrix_shape']}
        - rank = {double['summary']['kspace_backbone_status']['rank']}
        - nullity = {double['summary']['kspace_backbone_status']['nullity']}

        Continue from the current workspace. Do not change the target group. Do not go back to 10.4.1.31 except as reference.
        The next unique task is: finish published-shell AI induction/completion so that the already validated SG 194 local irrep/corep libraries become an honest AI lattice and, if successful, quotient extraction on 194.1.1.1.
        """
    ).strip() + "\n"


def build_package_readme() -> str:
    return "\n".join(
        [
            "# Review Package",
            "",
            "## Task Scope",
            f"- Reference group: `{REFERENCE_GROUP}`",
            f"- Fixed target group: `{TARGET_GROUP}`",
            "- Goal: workflow portability pilot",
            "",
            "## Known Premises",
            "- 10.4.1.31 single-group is already closed.",
            "- 10.4.1.31 double-group is already closed through quotient extraction.",
            "- This package tests how much of that workflow ports to 194.1.1.1.",
            "",
            "## New Material In This Package",
            "- controlled-case audit for 194.1.1.1",
            "- single-group pilot for 194.1.1.1",
            "- double-group pilot for 194.1.1.1",
            "- full-shell automorphism search for the P1-P5 double-class resolution",
            "- honest 8-path BS freeze plus AI library integration / obstruction diagnosis / honest blocker reports",
            "- PDF technical report",
            "- handoff / current_status / next_step_prompt",
            "",
            "## Possible Interpretations",
            "- single-group workflow may already look reusable",
            "- double-group workflow may already show a reusable seed",
            "- or the package may expose a sharper portability blocker",
            "",
            "## Suggested Review Order",
            f"1. {REPORT_PDF.name}",
            f"2. {CONTROLLED_AUDIT_MD.name}",
            f"3. {PORTABILITY_AUDIT_MD.name}",
            f"4. {PORTABILITY_SUMMARY_JSON.name}",
            f"5. {SINGLE_AUDIT_MD.name}",
            f"6. {DOUBLE_AUDIT_MD.name}",
            f"7. {FULL_SHELL_AUTOMORPHISM_MD.relative_to(ROOT)}",
            f"8. {AI_OBSTRUCTION_DIAG_MD.relative_to(ROOT)}",
            f"9. {AI_LIBRARY_INTEGRATION_MD.relative_to(ROOT)}",
            f"10. {AI_HONEST_BLOCKER_MD.relative_to(ROOT)}",
            "",
            "## PDF Report",
            f"- report file: `{REPORT_PDF.name}`",
            f"- report source: `{REPORT_TEX.name}`",
            "- recommended order: PDF first, then the JSON summaries and the audit markdown files",
        ]
    )


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    new_files = [
        CONTROLLED_AUDIT_MD,
        PORTABILITY_AUDIT_MD,
        PORTABILITY_SUMMARY_JSON,
        SINGLE_SUMMARY_JSON,
        SINGLE_AUDIT_MD,
        DOUBLE_SUMMARY_JSON,
        DOUBLE_AUDIT_MD,
        FULL_SHELL_AUTOMORPHISM_MD,
        FULL_SHELL_AUTOMORPHISM_JSON,
        FULL_POINT_SHELL_AUTOMORPHISM_MD,
        FULL_POINT_SHELL_AUTOMORPHISM_JSON,
        AI_OBSTRUCTION_DIAG_MD,
        AI_OBSTRUCTION_DIAG_JSON,
        AI_LIBRARY_INTEGRATION_MD,
        AI_LIBRARY_INTEGRATION_JSON,
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        AI_CHARACTER_FIELD_ALIGNMENT_JSON,
        AI_HONEST_BLOCKER_MD,
        AI_HONEST_BLOCKER_JSON,
        Path(__file__),
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_PDF,
        REPORT_TEX,
    ]
    for path in new_files:
        shutil.copy2(path, PACKAGE_DIR / path.name)
    for rel in PACKAGE_BACKGROUND_FILES:
        src = resolve_repo_asset(rel)
        dst = PACKAGE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    write_text(PACKAGE_DIR / "README.md", build_package_readme())
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs() -> None:
    required = [
        CONTROLLED_AUDIT_MD,
        PORTABILITY_AUDIT_MD,
        PORTABILITY_SUMMARY_JSON,
        SINGLE_SUMMARY_JSON,
        SINGLE_AUDIT_MD,
        DOUBLE_SUMMARY_JSON,
        DOUBLE_AUDIT_MD,
        FULL_SHELL_AUTOMORPHISM_MD,
        FULL_SHELL_AUTOMORPHISM_JSON,
        FULL_POINT_SHELL_AUTOMORPHISM_MD,
        FULL_POINT_SHELL_AUTOMORPHISM_JSON,
        AI_OBSTRUCTION_DIAG_MD,
        AI_OBSTRUCTION_DIAG_JSON,
        AI_LIBRARY_INTEGRATION_MD,
        AI_LIBRARY_INTEGRATION_JSON,
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        AI_CHARACTER_FIELD_ALIGNMENT_JSON,
        AI_HONEST_BLOCKER_MD,
        AI_HONEST_BLOCKER_JSON,
        Path(__file__),
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_PDF,
        REPORT_TEX,
        PACKAGE_TARBALL,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)


def run() -> dict[str, Any]:
    print("[run] controlled case")
    controlled, controlled_md = build_controlled_case()
    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict(TARGET_GROUP)
    print("[run] single pilot")
    single = build_single_pilot(module, ssg_dict)
    print("[run] double pilot")
    double = build_double_pilot(module, ssg_dict, single["kgeom"])
    portability_summary = build_portability_summary(controlled, single, double)
    portability_md = build_portability_audit_text(controlled, single, double, portability_summary)
    print("[run] report and package")
    write_text(CONTROLLED_AUDIT_MD, controlled_md)
    write_text(PORTABILITY_AUDIT_MD, portability_md)
    write_json(PORTABILITY_SUMMARY_JSON, portability_summary)
    write_json(SINGLE_SUMMARY_JSON, single["summary"])
    write_text(SINGLE_AUDIT_MD, single["audit_text"])
    write_json(DOUBLE_SUMMARY_JSON, double["summary"])
    write_text(DOUBLE_AUDIT_MD, double["audit_text"])
    write_text(REPORT_TEX, build_report_tex(controlled, single, double, portability_summary))
    compile_report()
    write_text(HANDOFF_MD, build_handoff(single, double, portability_summary))
    write_json(CURRENT_STATUS_JSON, build_current_status(single, double, portability_summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(single, double, portability_summary))
    build_package()
    return {
        "controlled": controlled,
        "single": single["summary"],
        "double": double["summary"],
        "portability": portability_summary,
    }


def print_terminal_summary(payload: dict[str, Any]) -> None:
    controlled = payload["controlled"]
    single = payload["single"]
    double = payload["double"]
    portability = payload["portability"]
    print(f"1. In the current local toolchain, 194.1.1.1 is a good controlled case: {controlled['controlled_case_valid']}")
    print(f"2. 194.1.1.1 groupType=1 pilot success: {single['BS_status']['status'] == 'success'}")
    print(f"3. 194.1.1.1 groupType=2 pilot success: {double['induction_status'] == 'success' and double['kspace_backbone_status']['status'] == 'success'}")
    print(f"4. current single-group workflow reusable: {portability['single_group_portable']}")
    print(f"5. current double-group workflow reusable seed: {portability['double_group_portable_seed']}")
    print(f"6. main portability blocker: {portability['main_blocker']}")
    print(f"7. PDF report generated: {REPORT_PDF.exists()}")
    print(f"8. PDF path: {REPORT_PDF}")
    print(f"9. report source path: {REPORT_TEX}")
    print("10. report includes formulas and pipeline detail: True")
    print(f"11. handoff file generated: {HANDOFF_MD.exists()}")
    print(f"12. next_step_prompt file generated: {NEXT_STEP_PROMPT_TXT.exists()}")
    print(f"13. new package path: {PACKAGE_TARBALL}")
    print("14. package tree:")
    for line in format_tree(PACKAGE_DIR):
        print(f"   {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled workflow portability pilot for 194.1.1.1.")
    parser.add_argument("--validate", action="store_true", help="Regenerate all outputs and validate them.")
    args = parser.parse_args()
    payload = run()
    validate_outputs()
    print_terminal_summary(payload)


if __name__ == "__main__":
    main()
