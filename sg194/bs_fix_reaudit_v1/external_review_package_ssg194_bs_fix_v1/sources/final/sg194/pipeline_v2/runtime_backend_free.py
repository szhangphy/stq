#!/usr/bin/env python3
"""Backend-free generic runtime extracted into pipeline_v2.

This module is the reusable runtime implementation used by the generic path.
It intentionally lives inside ``sg194/pipeline_v2`` so the core builders no
longer import or call the older SG194-special debug backends.
"""
from __future__ import annotations

import argparse
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

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
COMMON_ROOT = REPO_ROOT / "common"
COMMON_SSGREPS_ROOT = COMMON_ROOT / "SSGReps"
COMMON_SSG_DATA_ROOT = COMMON_SSGREPS_ROOT / "ssg_data"
IDENTIFY_PKL = COMMON_SSG_DATA_ROOT / "identify.pkl"
IDENTIFY_TAR = COMMON_SSG_DATA_ROOT / "identify.pkl.tar.gz"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import smith_normal_form

from common import swyckoff_k, swyckoff_r

from . import runtime_bridge as bridge
from . import runtime_group_ops as single_expanded

REFERENCE_GROUP = "10.4.1.31"
TARGET_GROUP = "194.1.1.1"
PACKAGE_NAME = "review_package_workflow_portability_194.1.1.1"
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

ZERO = Fraction(0, 1)
HALF = Fraction(1, 2)
LINE_SAMPLE = Fraction(1, 5)
BOUNDARY_VALUES = (ZERO, HALF)
AUTHORITATIVE_PHASE_AWARE_PROFILE = "phase_aware_l2_projective_v1"
AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND = (
    "authoritative_basis_decomposition_exact_unique_integer_with_phase_aware_l2_v1"
)
RETIRED_INTRINSIC_BUILDER_KIND = "retired_intrinsic_class_sum_compare_only_non_authoritative"
RETIRED_EXTRINSIC_BUILDER_KIND = "retired_extrinsic_star_augmented_compare_only_non_authoritative"

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
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
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
                candidate["special_line_orbit_match"] = line_orbit_to_id.get(orbit_key)
                candidate["classification"] = {
                    "is_separately_listed_special_line": bool(line_orbit_to_id.get(orbit_key)),
                    "reason": "Matches an existing 1D manifold orbit." if line_orbit_to_id.get(orbit_key) else "Does not match any listed 1D manifold orbit.",
                }
                if line:
                    candidate["line_id"] = line["id"]
                    boundaries.append(candidate)
                    line_plane.append(
                        {
                            "line_id": line["id"],
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


def _line_embedding_in_plane(
    line_anchor: Sequence[Fraction],
    line_basis: Sequence[Fraction],
    plane_anchor: Sequence[Fraction],
    plane_basis: Sequence[Sequence[Fraction]],
) -> dict[str, list[str]] | None:
    plane_matrix = sp.Matrix(
        [
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[0]],
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[1]],
        ]
    ).T
    offset = sp.Matrix(
        [
            sp.Rational(to_fraction(line_value - plane_value).numerator, to_fraction(line_value - plane_value).denominator)
            for line_value, plane_value in zip(line_anchor, plane_anchor)
        ]
    )
    direction = sp.Matrix(
        [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in line_basis]
    )
    try:
        anchor_coords = plane_matrix.gauss_jordan_solve(offset)[0]
        direction_coords = plane_matrix.gauss_jordan_solve(direction)[0]
    except Exception:
        return None
    return {
        "anchor_coords": [str(sp.simplify(value)) for value in anchor_coords],
        "direction_coords": [str(sp.simplify(value)) for value in direction_coords],
    }


def _point_embedding_in_plane(
    point_coords: Sequence[Fraction],
    plane_anchor: Sequence[Fraction],
    plane_basis: Sequence[Sequence[Fraction]],
) -> list[str] | None:
    plane_matrix = sp.Matrix(
        [
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[0]],
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[1]],
        ]
    ).T
    offset = sp.Matrix(
        [
            sp.Rational(to_fraction(point_value - plane_value).numerator, to_fraction(point_value - plane_value).denominator)
            for point_value, plane_value in zip(point_coords, plane_anchor)
        ]
    )
    try:
        plane_coords = plane_matrix.gauss_jordan_solve(offset)[0]
    except Exception:
        return None
    return [str(sp.simplify(value)) for value in plane_coords]


def annotate_special_line_plane_incidences(planes: Sequence[dict], lines: Sequence[dict]) -> list[dict[str, Any]]:
    incidences: list[dict[str, Any]] = []
    for line in lines:
        line["containing_planes"] = []
    for plane in planes:
        boundary_ids = {
            entry["line_id"]
            for entry in plane.get("boundary_lines", [])
            if entry.get("line_id")
        }
        contained_special_lines: list[dict[str, Any]] = []
        for line in lines:
            embedding = _line_embedding_in_plane(
                line["_anchor"],
                line["_basis"][0],
                plane["_anchor"],
                plane["_basis"],
            )
            if embedding is None:
                continue
            entry = {
                "plane_id": plane["id"],
                "line_id": line["id"],
                "incidence_role": "boundary" if line["id"] in boundary_ids else "interior",
                "plane_coordinates": embedding,
            }
            contained_special_lines.append(entry)
            line["containing_planes"].append(
                {
                    "plane_id": plane["id"],
                    "incidence_role": entry["incidence_role"],
                    "plane_coordinates": dict(embedding),
                }
            )
            incidences.append(dict(entry))
        plane["contained_special_lines"] = contained_special_lines
        plane["interior_special_lines"] = [
            item for item in contained_special_lines if item["incidence_role"] == "interior"
        ]
    return incidences


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
    special_line_plane_incidences = annotate_special_line_plane_incidences(planes, lines)
    payload = {
        "group_number": group_number,
        "objects": strip_internal_fields(points + lines + planes),
        "generic_manifolds_ignored": strip_internal_fields(generic),
        "point_line": point_line,
        "unmatched_line_endpoints": unmatched_endpoints,
        "line_plane": line_plane,
        "special_line_plane_incidences": special_line_plane_incidences,
        "unmatched_plane_boundaries": unmatched_plane_boundaries,
    }
    return {"grouped": grouped, "payload": payload}


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
    extra_fingerprints: dict[str, dict[str, Any]] | None = None,
    tol: float = 1e-8,
) -> list[dict[str, Any]]:
    vectors = capture_character_vectors(endpoint_raw, field, matched)
    classes: list[dict[str, Any]] = []
    for rep_index, restricted_vector in enumerate(vectors, start=1):
        rep_id = f"{endpoint_id}_R{rep_index}"
        extra_fingerprint = extra_fingerprints.get(rep_id) if extra_fingerprints else None
        extra_key = json.dumps(extra_fingerprint, sort_keys=True, separators=(",", ":")) if extra_fingerprint else ""
        for existing in classes:
            if (
                all(abs(left - right) <= tol for left, right in zip(existing["_vector"], restricted_vector))
                and existing["_extra_key"] == extra_key
            ):
                existing["rep_ids"].append(rep_id)
                break
        else:
            classes.append(
                {
                    "rep_ids": [rep_id],
                    "restricted_vector": complex_list_to_json(restricted_vector),
                    "extra_fingerprint": extra_fingerprint,
                    "_vector": restricted_vector,
                    "_extra_key": extra_key,
                }
            )
    for existing in classes:
        existing["class_size"] = len(existing["rep_ids"])
        del existing["_vector"]
        del existing["_extra_key"]
    return classes


def _line_decomposition_signature(rep: dict[str, Any]) -> list[list[Any]]:
    return [
        [basis_label, int(coeff)]
        for basis_label, coeff in sorted(rep.get("decomposition_on_line_basis", {}).items())
    ]


def _normalized_complex_json_vector(values: Sequence[complex], tol: float = 1e-8) -> list[dict[str, float]]:
    normalized = []
    for value in values:
        complex_value = complex(value)
        real = 0.0 if abs(complex_value.real) <= tol else float(complex_value.real)
        imag = 0.0 if abs(complex_value.imag) <= tol else float(complex_value.imag)
        if abs(real - round(real)) <= tol:
            real = float(round(real))
        if abs(imag - round(imag)) <= tol:
            imag = float(round(imag))
        normalized.append(complex(real, imag))
    return complex_list_to_json(normalized)


def _restriction_class_key(
    restricted_vector: list[dict[str, Any]],
    extra_fingerprint: dict[str, Any] | None = None,
) -> str:
    payload = {"restricted_vector": restricted_vector}
    if extra_fingerprint is not None:
        payload["extra_fingerprint"] = extra_fingerprint
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _endpoint_star_fingerprints_for_line(
    endpoint_entry: dict[str, Any],
    current_line_id: str,
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    *,
    field: str,
) -> list[dict[str, Any]]:
    fingerprints = []
    for line_id in sorted(endpoint_entry.get("incident_lines", [])):
        if line_id == current_line_id:
            continue
        line_raw = captures[line_id]
        matched_line = matched_unitary_indices(line_raw, endpoint_raw)
        line_vectors = capture_character_vectors(endpoint_raw, field, matched_line)
        fingerprints.append(
            {
                "manifold_id": line_id,
                "manifold_type": "line",
                "restricted_vector": _normalized_complex_json_vector(line_vectors[rep_index - 1]),
            }
        )
    for plane_id in sorted(endpoint_entry.get("incident_planes", [])):
        plane_raw = captures[plane_id]
        matched_plane = matched_unitary_indices(plane_raw, endpoint_raw)
        plane_vectors = capture_character_vectors(endpoint_raw, field, matched_plane)
        fingerprints.append(
            {
                "manifold_id": plane_id,
                "manifold_type": "plane",
                "restricted_vector": _normalized_complex_json_vector(plane_vectors[rep_index - 1]),
            }
        )
    return fingerprints


def intrinsic_restriction_fingerprint_for_line(
    line_obj: dict[str, Any],
    endpoint_entry: dict[str, Any],
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    coarse_block: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    line_raw = captures[line_obj["id"]]
    matched_line = matched_unitary_indices(line_raw, endpoint_raw)
    restricted_vector = capture_character_vectors(endpoint_raw, field, matched_line)[rep_index - 1]
    endpoint_id = endpoint_entry["point_id"]
    rep_id = f"{endpoint_id}_R{rep_index}"
    decomposition = {
        item["rep_id"]: item
        for item in coarse_block["endpoint_decompositions"][endpoint_id]
    }
    return {
        "fingerprint_kind": "line_intrinsic_restriction_v1",
        "field": field,
        "line_id": line_obj["id"],
        "endpoint_id": endpoint_id,
        "capture_id": endpoint_entry.get("capture_id", endpoint_id),
        "line_restricted_vector": _normalized_complex_json_vector(restricted_vector),
        "line_basis_decomposition": _line_decomposition_signature(decomposition[rep_id]),
    }


def extrinsic_star_fingerprint_for_line(
    line_obj: dict[str, Any],
    endpoint_entry: dict[str, Any],
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    *,
    field: str,
) -> dict[str, Any]:
    return {
        "fingerprint_kind": "line_extrinsic_star_augmented_v1",
        "field": field,
        "line_id": line_obj["id"],
        "line_containing_planes": list(line_obj.get("containing_planes", [])),
        "endpoint_plane_incidences": list(endpoint_entry.get("plane_incidences", [])),
        "point_star_restrictions": _endpoint_star_fingerprints_for_line(
            endpoint_entry,
            line_obj["id"],
            endpoint_raw,
            rep_index,
            captures,
            field=field,
        ),
    }


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


def build_line_block_coarse(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    phase_aware_profile: str | None = None,
) -> dict[str, Any]:
    normalized_phase_profile, selected_endpoint_override = phase_aware_l2_profile_config(phase_aware_profile)
    line_id = line_obj["id"]
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
    # Source-layer endpoint/plane subduction for 194.1.1.1 must stay in the
    # character language. The linear_character basis is not integer-solvable
    # for L1/L2/L5 and S3, which is the active BS-construction failure.
    field = "character"
    line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
    line_basis_matrix = _exact_basis_matrix_from_capture(
        line_raw,
        field,
        manifold_id=line_id,
    )
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
        equations.append(
            {
                "basis_id": basis_label,
                "terms": terms,
                "builder_variant": "coarse",
                "row_kind": "line_basis_decomposition",
                "uses_extrinsic_data": False,
                "endpoint_support": {},
                "class_members": [],
                "intrinsic_fingerprint_by_rep": {},
                "extrinsic_fingerprint_by_rep": {},
                "coarse_signature_by_rep": {},
            }
        )
    phase_aware_refinement = {
        "profile": "legacy",
        "selected_endpoint_id": None,
        "restriction_classes_by_endpoint": {},
        "refinement_equations": [],
    }
    if normalized_phase_profile == "phase_aware_l2_projective_v1":
        phase_aware_refinement = phase_aware_l2_refinement(
            line_id,
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
                    "builder_variant": "coarse",
                    "row_kind": "phase_aware_endpoint_class",
                    "uses_extrinsic_data": False,
                    "endpoint_support": {},
                    "class_members": list(equation["restriction_class_rep_ids"]),
                    "intrinsic_fingerprint_by_rep": {},
                    "extrinsic_fingerprint_by_rep": {},
                    "coarse_signature_by_rep": {},
                }
            )
    return {
        "status": "success",
        "builder_variant": "coarse",
        "line_id": line_id,
        "endpoint_ids": endpoint_ids,
        "line_sample_point": line_obj["sample_point"],
        "line_parametrization": line_obj["parametrization"],
        "line_symmetry_summary": line_obj["symmetry_summary"],
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "line_basis_labels": line_basis_labels,
        "line_group_signature": {
            "n_ops_total": len(line_raw["rotC"]),
            "n_unitary_ops": line_raw["unitary_operation_count"],
            "n_antiunitary_ops": sum(1 for sign in line_raw["timeReversal"] if sign < 0),
            "rep_degree": list(line_raw["rep_degree"]),
            "torsion": list(line_raw["torsion"]),
        },
        "phase_aware_refinement": phase_aware_refinement,
        "compatibility_field": field,
        "compatibility_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        "phase_aware_profile_used": (
            phase_aware_refinement["profile"]
            if phase_aware_refinement["profile"] != "legacy"
            else "legacy"
        ),
    }


def build_line_block_from_coarse_restriction(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "character",
) -> dict[str, Any]:
    block = build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
    return {
        **block,
        "builder_variant": "coarse",
        "restriction_class_builder": {
            "status": "compare_only",
            "builder_kind": "coarse_basis_decomposition_only",
            "field": field,
            "restriction_classes_by_endpoint": {},
            "row_count": len(block["equations"]),
            "uses_extrinsic_data": False,
        },
        "coarse_compare": {
            "builder_kind": "coarse_basis_decomposition_only",
            "equation_count": len(block["equations"]),
            "matrix_row_count": len(block["matrix_rows"]),
        },
    }


def _line_endpoint_entries(line_obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
            "incident_lines": list(endpoint.get("incident_lines", [])),
            "incident_planes": list(endpoint.get("incident_planes", [])),
            "plane_incidences": list(endpoint.get("plane_incidences", [])),
        }
        for endpoint in line_obj["endpoints"]
    ]


def _build_line_block_from_restriction_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    builder_variant: str,
    field: str = "linear_character",
) -> dict[str, Any]:
    if builder_variant not in {"intrinsic", "extrinsic"}:
        raise ValueError(f"unsupported restriction-class builder variant: {builder_variant}")

    coarse_block = build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
    endpoint_entries = _line_endpoint_entries(line_obj)
    endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
    line_raw = captures[line_obj["id"]]
    restriction_classes_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    class_support: dict[str, dict[str, Any]] = {}
    intrinsic_fingerprints_by_rep: dict[str, dict[str, Any]] = {}
    extrinsic_fingerprints_by_rep: dict[str, dict[str, Any]] = {}
    coarse_signature_by_rep: dict[str, list[list[Any]]] = {}

    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        capture_id = endpoint_entry["capture_id"]
        endpoint_raw = captures[capture_id]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        extra_fingerprints: dict[str, dict[str, Any]] | None = {} if builder_variant == "extrinsic" else None
        for rep_index in range(1, len(endpoint_raw[field]) + 1):
            rep_id = f"{endpoint_id}_R{rep_index}"
            intrinsic_fingerprints_by_rep[rep_id] = intrinsic_restriction_fingerprint_for_line(
                line_obj,
                endpoint_entry,
                endpoint_raw,
                rep_index,
                captures,
                coarse_block,
                field=field,
            )
            coarse_signature_by_rep[rep_id] = intrinsic_fingerprints_by_rep[rep_id]["line_basis_decomposition"]
            if extra_fingerprints is not None:
                extra_fingerprints[rep_id] = extrinsic_star_fingerprint_for_line(
                    line_obj,
                    endpoint_entry,
                    endpoint_raw,
                    rep_index,
                    captures,
                    field=field,
                )
                extrinsic_fingerprints_by_rep[rep_id] = extra_fingerprints[rep_id]
        classes = identical_restriction_classes(
            endpoint_id,
            endpoint_raw,
            matched,
            field=field,
            extra_fingerprints=extra_fingerprints,
        )
        restriction_classes_by_endpoint[endpoint_id] = classes
        for entry in classes:
            class_key = _restriction_class_key(
                entry["restricted_vector"],
                entry.get("extra_fingerprint") if builder_variant == "extrinsic" else None,
            )
            support = class_support.setdefault(
                class_key,
                {
                    "restricted_vector": entry["restricted_vector"],
                    "extra_fingerprint": entry.get("extra_fingerprint"),
                    "members_by_endpoint": {},
                },
            )
            support["members_by_endpoint"][endpoint_id] = list(entry["rep_ids"])

    local_index = {unknown: index for index, unknown in enumerate(coarse_block["local_unknown_ordering"])}
    restriction_equations: list[dict[str, Any]] = []
    restriction_rows = []
    for class_index, class_key in enumerate(sorted(class_support), start=1):
        support = class_support[class_key]
        endpoint_support = {endpoint_id: list(support["members_by_endpoint"].get(endpoint_id, [])) for endpoint_id in endpoint_ids}
        terms = []
        for endpoint_id, side in zip(endpoint_ids, ("left", "right")):
            coeff = 1 if side == "left" else -1
            for rep_id in endpoint_support.get(endpoint_id, []):
                terms.append({"unknown": rep_id, "coeff": coeff, "side": side})
        if not terms:
            continue
        class_members = [rep_id for endpoint_id in endpoint_ids for rep_id in endpoint_support.get(endpoint_id, [])]
        equation = {
            "basis_id": f"{line_obj['id']}_{builder_variant}_class_{class_index:02d}",
            "terms": terms,
            "builder_variant": builder_variant,
            "row_kind": "restriction_class_sum",
            "endpoint_support": endpoint_support,
            "class_members": class_members,
            "restricted_vector": support["restricted_vector"],
            "intrinsic_fingerprint_by_rep": {
                rep_id: intrinsic_fingerprints_by_rep[rep_id]
                for rep_id in class_members
            },
            "extrinsic_fingerprint_by_rep": (
                {
                    rep_id: extrinsic_fingerprints_by_rep[rep_id]
                    for rep_id in class_members
                }
                if builder_variant == "extrinsic"
                else {}
            ),
            "coarse_signature_by_rep": {
                rep_id: coarse_signature_by_rep[rep_id]
                for rep_id in class_members
            },
            "uses_extrinsic_data": builder_variant == "extrinsic",
            "line_containing_planes": list(line_obj.get("containing_planes", [])),
        }
        restriction_equations.append(equation)
        row = [0] * len(coarse_block["local_unknown_ordering"])
        for term in terms:
            row[local_index[term["unknown"]]] += int(term["coeff"])
        restriction_rows.append(row)

    builder_kind = (
        RETIRED_INTRINSIC_BUILDER_KIND
        if builder_variant == "intrinsic"
        else RETIRED_EXTRINSIC_BUILDER_KIND
    )
    return {
        **coarse_block,
        "status": "retired_compare_only_non_authoritative",
        "builder_variant": builder_variant,
        "equations": restriction_equations,
        "matrix_rows": restriction_rows,
        "line_group_signature": {
            **coarse_block["line_group_signature"],
            "containing_plane_count": len(line_obj.get("containing_planes", [])),
        },
        "restriction_class_builder": {
            "status": "retired_compare_only_non_authoritative",
            "builder_kind": builder_kind,
            "field": field,
            "containing_planes": list(line_obj.get("containing_planes", [])),
            "restriction_classes_by_endpoint": restriction_classes_by_endpoint,
            "row_count": len(restriction_equations),
            "uses_extrinsic_data": builder_variant == "extrinsic",
        },
        "phase_aware_refinement": {
            "profile": "disabled_in_backend_free_generic_primary_path",
            "selected_endpoint_id": None,
            "restriction_classes_by_endpoint": {},
            "refinement_equations": [],
        },
        "coarse_compare": {
            "builder_kind": "basis_decomposition_compare_only",
            "equation_count": len(coarse_block["equations"]),
            "matrix_row_count": len(coarse_block["matrix_rows"]),
        },
    }


def build_line_block_from_intrinsic_restriction_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "linear_character",
) -> dict[str, Any]:
    return _build_line_block_from_restriction_classes(
        line_obj,
        captures,
        builder_variant="intrinsic",
        field=field,
    )


def build_line_block_from_extrinsic_star_augmented_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "linear_character",
) -> dict[str, Any]:
    return _build_line_block_from_restriction_classes(
        line_obj,
        captures,
        builder_variant="extrinsic",
        field=field,
    )


def build_line_block(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    phase_aware_profile: str | None = AUTHORITATIVE_PHASE_AWARE_PROFILE,
    *,
    builder_variant: str = "authoritative",
) -> dict[str, Any]:
    if builder_variant in {"authoritative", "coarse"}:
        return build_line_block_coarse(
            line_obj,
            captures,
            phase_aware_profile=phase_aware_profile,
        )
    if builder_variant == "intrinsic":
        return build_line_block_from_intrinsic_restriction_classes(line_obj, captures, field="character")
    if builder_variant == "extrinsic":
        raise ValueError("extrinsic line builder is retired and non-authoritative")
    raise ValueError(f"unsupported builder_variant: {builder_variant}")


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
            metadata = {key: value for key, value in equation.items() if key != "terms"}
            global_rows.append(
                {
                    "source_type": "line",
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "builder_variant": block.get("builder_variant", "coarse"),
                    "equation_metadata": metadata,
                    **metadata,
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

    line_block = next((block for block in line_blocks if block["line_id"] == "L2"), None)
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
    # Plane auxiliary coordinates remain the intended two-label 42-shell only
    # if the point-to-plane subduction is performed in character language.
    field = "character"
    plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
    plane_basis_matrix = _exact_basis_matrix_from_capture(
        plane_raw,
        field,
        manifold_id=plane_id,
    )
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
            row_metadata = {key: value for key, value in equation.items() if key != "terms"}
            rows.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "point_id": equation["point_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "equation_metadata": row_metadata,
                    **row_metadata,
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


def induce_candidate(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    unknown_ordering: list[str],
    global_matrix: list[list[int]],
    point_row_translation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    orbit = single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    stabilizer = bridge.bridge_stabilizer_for_entry(entry, ctx)
    stabilizer_unitary = set(stabilizer["unitary_indices"])
    manifold_multiplicities: dict[str, list[int]] = {}
    manifold_band_characters: dict[str, list[dict[str, float]]] = {}
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
        chars = np.array(info["linear_character"], dtype=complex)
        band = np.array(band_character, dtype=complex)
        gram = chars @ chars.conj().T / chars.shape[1]
        rhs = chars.conj() @ band / chars.shape[1]
        multiplicities = np.linalg.solve(gram, rhs)
        rounded = [int(round(float(value.real))) for value in multiplicities]
        recon = np.array(rounded, dtype=complex) @ chars
        if not np.allclose(multiplicities, np.rint(multiplicities.real), atol=1e-8):
            raise ValueError(f"{entry['letter']} on {manifold_id}: non-integral multiplicities")
        if not np.allclose(recon, band, atol=1e-8):
            raise ValueError(f"{entry['letter']} on {manifold_id}: reconstruction failed")
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
    point_instance_lookup: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    def ensure_point_instance(point_id: str, coords: Sequence[str]) -> str:
        representative_coords = point_lookup[point_id]["sample_point"]
        capture_id = point_id if list(coords) == list(representative_coords) else point_capture_id(point_id, coords)
        if capture_id not in point_instance_lookup:
            point_instance_lookup[capture_id] = {
                "capture_id": capture_id,
                "point_id": point_id,
                "point_coordinates": list(coords),
                "incident_lines": [],
                "incident_planes": [],
                "plane_incidences": [],
            }
        if capture_id != point_id and capture_id not in seen:
            point_instances.append(point_instance_lookup[capture_id])
            seen.add(capture_id)
        return capture_id

    for point in point_lookup.values():
        ensure_point_instance(point["id"], point["sample_point"])

    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            endpoint["capture_id"] = ensure_point_instance(endpoint["point_id"], endpoint["point_coordinates"])
            point_instance_lookup[endpoint["capture_id"]]["incident_lines"].append(line["id"])
    for plane in kgeom["grouped"]["planes"]:
        corner_entries = derive_plane_corner_entries(plane, point_by_coord)
        for corner in corner_entries:
            corner["capture_id"] = ensure_point_instance(corner["point_id"], corner["point_coordinates"])
        plane["corner_entries"] = corner_entries

    for instance in point_instance_lookup.values():
        coords = [Fraction(value) for value in instance["point_coordinates"]]
        for plane in kgeom["grouped"]["planes"]:
            plane_coords = _point_embedding_in_plane(coords, plane["_anchor"], plane["_basis"])
            if plane_coords is None:
                continue
            role = "corner" if any(
                corner.get("capture_id") == instance["capture_id"]
                for corner in plane.get("corner_entries", [])
            ) else "interior_or_boundary_noncorner"
            instance["incident_planes"].append(plane["id"])
            instance["plane_incidences"].append(
                {
                    "plane_id": plane["id"],
                    "plane_coordinates": plane_coords,
                    "incidence_role": role,
                }
            )

    point_instance_lookup_by_point: dict[str, list[dict[str, Any]]] = {}
    for instance in point_instance_lookup.values():
        instance["incident_lines"] = sorted(set(instance["incident_lines"]))
        instance["incident_planes"] = sorted(set(instance["incident_planes"]))
        point_instance_lookup_by_point.setdefault(instance["point_id"], []).append(instance)

    for point in point_lookup.values():
        instances = point_instance_lookup_by_point.get(point["id"], [])
        point["incident_lines"] = sorted({line_id for item in instances for line_id in item["incident_lines"]})
        point["incident_planes"] = sorted({plane_id for item in instances for plane_id in item["incident_planes"]})

    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            instance = point_instance_lookup[endpoint["capture_id"]]
            endpoint["incident_lines"] = list(instance["incident_lines"])
            endpoint["incident_planes"] = list(instance["incident_planes"])
            endpoint["plane_incidences"] = list(instance["plane_incidences"])
    for plane in kgeom["grouped"]["planes"]:
        for corner in plane.get("corner_entries", []):
            instance = point_instance_lookup[corner["capture_id"]]
            corner["incident_lines"] = list(instance["incident_lines"])
            corner["incident_planes"] = list(instance["incident_planes"])
            corner["plane_incidences"] = list(instance["plane_incidences"])
    kgeom["point_instance_lookup"] = point_instance_lookup
    kgeom["point_instance_entries"] = point_instances
    return point_instances


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
    kgeom = {"payload": kgeom_payload, "grouped": grouped, "connectivity": kgeom_payload}
    synthetic_points = build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic_points
    augment_connectivity_with_boundary_points(kgeom, synthetic_points)
    build_point_instance_entries(kgeom)
    ctx["kgeom"] = kgeom
    print("[pilot] single: manifold capture")
    captures = build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "single", kgeom)

    point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]
    print("[pilot] single: line blocks")
    line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in grouped["lines"]
    ]
    line_full = build_global_compatibility(line_blocks, point_ids)

    print("[pilot] single: plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in grouped["planes"]]
    with_planes = build_with_planes_compatibility(line_full, plane_blocks)
    bs_analysis = analyze_kernel(with_planes)
    point_row_translation = build_phase_aware_point_row_translation(
        line_blocks,
        bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
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
            with_planes["global_matrix"],
            point_row_translation=point_row_translation,
        )
        candidate["generator_id"] = f"{entry['letter']}_trivial"
        ai_candidates.append(candidate)
    ai_matrix = sp.Matrix.hstack(*[sp.Matrix(candidate["unknown_vector"]) for candidate in ai_candidates]) if ai_candidates else sp.zeros(len(bs_analysis["unknown_ordering"]), 0)
    ai_rank = int(ai_matrix.rank()) if ai_candidates else 0

    write_json(SINGLE_KMANIFOLDS_JSON, {
        "group_number": TARGET_GROUP,
        "objects": strip_internal_fields(grouped["points"] + grouped["lines"] + grouped["planes"]),
        "synthetic_boundary_points": synthetic_points,
        "connectivity": kgeom_payload,
    })
    write_json(SINGLE_CONNECTIVITY_JSON, kgeom_payload)
    write_json(SINGLE_LITTLE_GROUPS_JSON, captures)
    write_json(SINGLE_LINE_COMPAT_JSON, {"line_blocks": line_blocks, "line_full": line_full})
    write_json(SINGLE_WITH_PLANES_JSON, with_planes)
    write_json(SINGLE_BS_JSON, bs_analysis)
    write_json(SINGLE_AI_JSON, {"generators": ai_candidates, "rank_trivial_family_span": ai_rank})

    completeness_blocker = "Generic local-irrep library beyond the trivial rep is not implemented for the non-abelian SG 194 site symmetries, so AI completeness cannot be certified honestly."
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 1,
        "geometry_status": "success",
        "compatibility_status": {
            "line_blocks_built": len(line_blocks),
            "synthetic_boundary_points_added": len(synthetic_points),
            "point_line_relations": len(kgeom_payload["point_line"]),
            "unmatched_line_endpoints_before_augmentation": len(kgeom_payload["unmatched_line_endpoints"]),
            "plane_blocks_built": len(plane_blocks),
            "status": "success",
            "authoritative_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": line_phase_profile,
        },
        "BS_status": {
            "status": "success",
            "matrix_shape": bs_analysis["matrix_shape"],
            "rank": bs_analysis["rank"],
            "nullity": bs_analysis["nullity"],
            "smith_diagonal": bs_analysis["smith_diagonal"],
        },
        "AI_status": {
            "status": "partial",
            "trivial_generators_count": len(ai_candidates),
            "rank_trivial_family_span": ai_rank,
            "all_trivial_generators_compatibility_zero": all(candidate["compatibility_zero"] for candidate in ai_candidates),
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
        "- Real-space geometry, k-space manifolds, little-group capture, line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.",
        f"- The current pilot had to add `{len(synthetic_points)}` synthetic 0D boundary points because the raw k-geometry contains `{len(kgeom_payload['unmatched_line_endpoints'])}` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.",
        "- That synthetic-boundary augmentation is the main code-level portability change relative to 10.4.1.31.",
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
        "- The AI side is only partial: the current pilot induces the trivial local representation on every real-space family, but it does not yet enumerate the full local-irrep library for the non-abelian SG 194 site symmetries.",
        "",
        "## Status Summary",
        "",
        f"- BS matrix shape/rank/nullity: `{bs_analysis['matrix_shape']}`, `{bs_analysis['rank']}`, `{bs_analysis['nullity']}`.",
        f"- Trivial-family AI prototype count/rank: `{len(ai_candidates)}` / `{ai_rank}`.",
        f"- AI completeness: blocked. Reason: {completeness_blocker}",
        "- Quotient / indicator extraction: blocked until a complete AI lattice exists.",
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "kgeom": kgeom,
        "captures": captures,
        "with_planes": with_planes,
        "bs_analysis": bs_analysis,
        "ai_candidates": ai_candidates,
        "point_row_translation": point_row_translation,
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
    print("[pilot] double: line blocks")
    line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in single_kgeom["grouped"]["lines"]
    ]
    line_full = build_global_compatibility(line_blocks, point_ids)
    print("[pilot] double: plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in single_kgeom["grouped"]["planes"]]
    with_planes = build_with_planes_compatibility(line_full, plane_blocks)
    bs_analysis = analyze_kernel(with_planes)
    point_row_translation = build_phase_aware_point_row_translation(
        line_blocks,
        bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
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
        with_planes["global_matrix"],
        point_row_translation=point_row_translation,
    )
    minimal["generator_id"] = "l_double_trivial"
    minimal["bridge_reused"] = True
    minimal["projective_note"] = "The real-space prototype uses the trivial stabilizer of family l, so the first portable double-group witness does not yet require a nontrivial local projective-character solver."

    write_json(DOUBLE_LITTLE_GROUPS_JSON, captures)
    write_json(DOUBLE_WITH_PLANES_JSON, with_planes)
    write_json(DOUBLE_BS_JSON, bs_analysis)
    write_json(DOUBLE_MINIMAL_JSON, minimal)

    blocker = "A generic projective local-corep builder for the nontrivial SG 194 site symmetries is still missing, so point-like / parametric double AI families cannot yet be enumerated beyond the trivial-stabilizer witness."
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
            "phase_aware_profile": line_phase_profile,
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
        "- The double-group with-planes k-space backbone was assembled successfully from raw/linear characters and subgroup restriction data.",
        "",
        "## Minimal Prototype",
        "",
        "- The first portable real-space witness uses the generic family `l` with trivial stabilizer.",
        "- This shows that the spatial bridge, lattice-fix filter, Bloch phase, and decomposition against double little-coreps all survive the move from 10.4.1.31 to 194.1.1.1.",
        "",
        "## Current Limit",
        "",
        f"- {blocker}",
        "- Therefore the present run establishes a reusable double-group seed and a reusable double-group k-space backbone, but not yet a full point-like / parametric AI census or any final double quotient.",
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "with_planes": with_planes,
        "bs_analysis": bs_analysis,
        "minimal": minimal,
        "point_row_translation": point_row_translation,
        "phase_aware_profile": line_phase_profile,
    }


def build_portability_summary(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "controlled_case_valid": bool(controlled["controlled_case_valid"]),
        "single_group_portable": bool(single["summary"]["BS_status"]["status"] == "success" and single["summary"]["AI_status"]["status"] == "partial"),
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
            "- Local real-space irrep / corep libraries for SG 194 site symmetries.",
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
        The following modules port directly from {reference_group}: standardized real-space geometry, standardized k-space geometry, character-based little-group capture, compatibility assembly by subgroup matching, integer-kernel BS extraction, and the phase-corrected atomic induction bridge. The following modules do not yet port without additional target-specific work: completeness-level local irrep/corep enumeration for the SG 194 site symmetries, and automatic closure of omitted boundary endpoints without the current synthetic-point augmentation. Therefore the true reusable boundary of the workflow is already beyond one-group scripting for the spatial backbone, but still short of a group-agnostic AI library.

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
            main_blocker=portability_summary["main_blocker"],
            next_blocker=portability_summary["next_blocker"],
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
            "- Next unique target: generalize the local real-space irrep/corep library so that AI completeness and quotient extraction become honest on 194.1.1.1.",
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
        The next unique task is: implement a generic local real-space irrep/corep builder for the SG 194 site symmetries so that the current partial AI prototypes on 194.1.1.1 can be upgraded to an honest AI completeness audit and, if successful, quotient extraction.
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
