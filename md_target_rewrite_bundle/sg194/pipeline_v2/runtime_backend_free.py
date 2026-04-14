"""Backend-free generic runtime extracted into pipeline_v2.

This module is the reusable runtime implementation used by the generic path.
It intentionally lives inside ``sg194/pipeline_v2`` so the core builders no
longer import or call the older SG194-special debug backends.
"""
from __future__ import annotations
import contextlib
import importlib.util
import io
import pickle
import sys
import tarfile as tarfile_module
from fractions import Fraction
from math import gcd
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
COMMON_ROOT = REPO_ROOT / "common"
COMMON_SSGREPS_ROOT = COMMON_ROOT / "SSGReps"
COMMON_SSG_DATA_ROOT = COMMON_SSGREPS_ROOT / "ssg_data"
IDENTIFY_PKL = COMMON_SSG_DATA_ROOT / "identify.pkl"
IDENTIFY_TAR = COMMON_SSG_DATA_ROOT / "identify.pkl.tar.gz"
REPO_LOCAL_MSG_PKL = COMMON_SSG_DATA_ROOT / "msg.pkl"
EXTERNAL_MSG_PKL = Path("/data/work/szhang/ssg/msgid/msg.pkl")
import numpy as np
import sympy as sp
from common import swyckoff_k, swyckoff_r
def complex_to_json(value: complex) -> dict[str, float]:
    return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}
def complex_list_to_json(values: Sequence[complex]) -> list[dict[str, float]]:
    return [complex_to_json(complex(value)) for value in values]
def complex_matrix_to_json(matrix: Sequence[Sequence[complex]]) -> list[list[dict[str, float]]]:
    return [complex_list_to_json(row) for row in matrix]
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
def evaluate_exprs(exprs: Sequence[sp.Expr], assignment: Dict[str, Fraction]) -> list[Fraction]:
    out: list[Fraction] = []
    for expr in exprs:
        value = expr
        for symbol_name, frac in assignment.items():
            value = value.subs(sp.Symbol(symbol_name), sp.Rational(frac.numerator, frac.denominator))
        out.append(Fraction(str(sp.simplify(value))))
    return out
def sample_assignment(parameters: Sequence[str]) -> Dict[str, Fraction]:
    pool = [
        Fraction(173, 1000),
        Fraction(417, 1000),
        Fraction(619, 1000),
        Fraction(842, 1000),
    ]
    return {name: pool[index] for index, name in enumerate(parameters)}
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
    # if IDENTIFY_PKL.exists():
    #     return IDENTIFY_PKL
    if REPO_LOCAL_MSG_PKL.exists():
        return REPO_LOCAL_MSG_PKL
    if EXTERNAL_MSG_PKL.exists():
        return EXTERNAL_MSG_PKL
    if IDENTIFY_PKL.exists():
        return IDENTIFY_PKL
    # if not IDENTIFY_TAR.exists():
    #     raise FileNotFoundError(f"missing {IDENTIFY_PKL} and {IDENTIFY_TAR}")
    if not IDENTIFY_TAR.exists():
        raise FileNotFoundError(
            f"missing {REPO_LOCAL_MSG_PKL}, {EXTERNAL_MSG_PKL}, {IDENTIFY_PKL} and {IDENTIFY_TAR}"
        )
    with tarfile_module.open(IDENTIFY_TAR, "r:gz") as tar:
        tar.extract("identify.pkl", path=COMMON_SSG_DATA_ROOT)
    return IDENTIFY_PKL
def _load_identify_ssg_list() -> list[dict[str, Any]]:
    identify_pkl = ensure_identify_pkl()
    with identify_pkl.open("rb") as fh:
        return pickle.load(fh)
def resolve_group_number(group_number: str) -> str:
    normalized = str(group_number).strip()
    if "." in normalized:
        return normalized
    matches = sorted(
        {
            str(item["ssgNum"])
            for item in _load_identify_ssg_list()
            if str(item.get("ssgNum", "")).split(".")[0] == normalized
        }
    )
    if not matches:
        raise ValueError(f"Cannot resolve SG shorthand {group_number!r} to a unique SSG number")
    if len(matches) != 1:
        raise ValueError(
            f"SG shorthand {group_number!r} is ambiguous across SSG numbers: {matches}"
        )
    return matches[0]
def load_ssg_dict(group_number: str) -> dict[str, Any]:
    resolved_group_number = resolve_group_number(group_number)
    return next(
        item
        for item in _load_identify_ssg_list()
        if item["ssgNum"] == resolved_group_number
    )
def _load_realspace_context_payload(group_number: str) -> dict[str, Any]:
    resolved_group_number = resolve_group_number(group_number)
    full_data, _ = swyckoff_r.load_irssg_data(resolved_group_number, 0)
    wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(resolved_group_number, fast=True)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]
    return {
        "full_data": full_data,
        "wyckoff_entries": wyckoff_entries,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
    }
def load_context(module: Any, group_number: str, group_label: str, ssg_dict: dict[str, Any]) -> dict[str, Any]:
    resolved_group_number = resolve_group_number(group_number)
    ssg = module.loadSsgGroup(resolved_group_number, np.array([0.0, 0.0, 0.0]), group_label, ssg_dict)
    realspace = _load_realspace_context_payload(resolved_group_number)
    ctx = {
        "group_number": resolved_group_number,
        "requested_group_number": str(group_number),
        "group_label": group_label,
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "translation_basis": np.column_stack([np.array(vector, dtype=float) for vector in ssg.pure_T]),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": realspace["full_data"],
        "full_ops": realspace["full_ops"],
        "full_time_revs": realspace["full_time_revs"],
        "wyckoff_entries": realspace["wyckoff_entries"],
    }
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in realspace["wyckoff_entries"]}
    return ctx
def load_reciprocal_context(group_number: str) -> dict[str, Any]:
    resolved_group_number = resolve_group_number(group_number)
    data, _time_revs = swyckoff_k.load_irssg_data(resolved_group_number, 0)
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
        "operation_source_kind": "swyckoff_k.load_irssg_data_via_construct_std_ssg_operations",
        "coordinate_basis_kind": "post_supercell_primitive_reciprocal_basis",
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
    resolved_group_number = resolve_group_number(group_number)
    # The md path prioritizes the canonical representative shell over speed, so
    # do not use the `fast=True` shortcut here.
    wyckoff, coord_key = swyckoff_k.compute_wyckoff_output(
        resolved_group_number,
        kspace=True,
        basis="primitive",
        fast=False,
    )
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
    for point in points:
        point.setdefault("manifold_role", "listed_special_point_manifold")
        point.setdefault("point_role", "physical_special_point")
        point.setdefault("point_origin_kind", "listed_fixed_subspace_point")
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
def annotate_special_manifolds(lines: Sequence[dict], planes: Sequence[dict], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> None:
    for line in lines:
        line["manifold_role"] = "separately_listed_special_line_manifold"
        line["symmetry_summary"] = subspace_symmetry_summary(line["_anchor"], line["_basis"], ctx)
        line["closure_under_pointwise_stabilizer"] = closure_components(line["_anchor"], line["_basis"], ctx, line_orbit_to_id, plane_orbit_to_id)
    for plane in planes:
        plane["manifold_role"] = "separately_listed_special_plane_manifold"
        plane["symmetry_summary"] = subspace_symmetry_summary(plane["_anchor"], plane["_basis"], ctx)
def build_generic_representative_points(
    grouped: dict[str, Any],
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Choose one representative sample point for each inequivalent generic k-star."""
    representatives: list[dict[str, Any]] = []
    for index, generic in enumerate(grouped.get("generic", []), start=1):
        sample_point = [frac_str(to_fraction(value)) for value in generic.get("sample_point", [])]
        anchor = [to_fraction(value) for value in sample_point]
        representatives.append(
            {
                "id": f"G{index}",
                "label": generic.get("label"),
                "type": "generic_point_representative",
                "dimension": 0,
                "sample_point": list(sample_point),
                "coordinate_expressions": list(sample_point),
                "parameters": [],
                "constraints": [],
                "constraint_summary": "representative generic k-star sample",
                "metadata": {
                    "source_letter": "generic_kstar_representative",
                    "source_generic_label": generic.get("label"),
                    "source_generic_parametrization": generic.get("parametrization"),
                    "source_orbit": [", ".join(sample_point)],
                },
                "symmetry_summary": subspace_symmetry_summary(generic["_anchor"], generic["_basis"], ctx),
                "manifold_role": "generic_kstar_representative",
                "point_role": "generic_kstar_representative",
                "point_origin_kind": "generic_kstar_representative",
                "_anchor": anchor,
                "_basis": [],
            }
        )
    return representatives
def operation_key_from_capture(capture: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(round(float(entry))) for entry in row) for row in capture["rotC"][op_index])
    tau = tuple(round(float(entry) % 1.0, 8) for entry in capture["tauC"][op_index])
    spin = tuple(tuple(round(float(entry), 8) for entry in row) for row in capture["spin"][op_index])
    return rot, tau, spin, int(capture["timeReversal"][op_index])
def capture_little_group(module: Any, group_number: str, ssg_dict: dict[str, Any], ctx: dict[str, Any], group_label: str, manifold_id: str, kvec: list[float]) -> dict[str, Any]:
    resolved_group_number = resolve_group_number(group_number)
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        lg = module.load_little_group(resolved_group_number, np.array(kvec, dtype=float), False, group_label, ssg_dict)
    unitary_rotations: list[np.ndarray] = []
    unitary_translations: list[np.ndarray] = []
    unitary_capture_indices: list[int] = []
    for raw_index, (rotation, translation, tr) in enumerate(zip(lg.rotC, lg.tauC, lg.time_reversal)):
        if int(tr) < 0:
            continue
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        unitary_rotations.append(rot)
        unitary_translations.append(tau)
        unitary_capture_indices.append(raw_index)
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
        "unitary_operation_count": len(unitary_capture_indices),
        "unitary_raw_indices": list(unitary_capture_indices),
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
    for point in kgeom.get("generic_representatives", []):
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
    if isinstance(value, sp.Basic):
        value = complex(value.evalf())
    real = 0.0 if abs(value.real) < 1e-8 else float(value.real)
    imag = 0.0 if abs(value.imag) < 1e-8 else float(value.imag)
    if abs(real - round(real)) < 1e-8:
        real_expr = sp.Integer(int(round(real)))
    else:
        real_expr = sp.nsimplify(real)
    if abs(imag - round(imag)) < 1e-8:
        imag_expr = sp.Integer(int(round(imag)))
    else:
        imag_expr = sp.nsimplify(imag)
    if imag == 0.0:
        return real_expr
    if real == 0.0:
        return sp.I * imag_expr
    return real_expr + sp.I * imag_expr
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
            f"{context}: numeric_attempt_error={numeric_error}; exact_solver={exc}"
        ) from exc
    if params.rows * params.cols:
        raise ValueError(
            f"{context}: numeric_attempt_error={numeric_error}; exact_solver=non-unique decomposition"
        )
    residual = basis_matrix * solution - restricted
    if any(sp.simplify(entry) != 0 for entry in residual):
        raise ValueError(
            f"{context}: numeric_attempt_error={numeric_error}; exact_solver=exact reconstruction failed"
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
def _primitive_integer_row_exact(row: Sequence[Any]) -> list[int]:
    exact_row = [sp.nsimplify(value) for value in row]
    denominator_lcm = 1
    for value in exact_row:
        if isinstance(value, sp.Rational):
            denominator_lcm = sp.ilcm(denominator_lcm, int(value.q))
    integer_row = [int(sp.nsimplify(value * denominator_lcm)) for value in exact_row]
    common_divisor = 0
    for value in integer_row:
        common_divisor = gcd(common_divisor, abs(int(value)))
    if common_divisor > 1:
        integer_row = [int(value // common_divisor) for value in integer_row]
    for value in integer_row:
        if value == 0:
            continue
        if value < 0:
            integer_row = [-item for item in integer_row]
        break
    return integer_row
def _row_rank_exact(rows: Sequence[Sequence[int]]) -> int:
    if not rows:
        return 0
    return int(sp.Matrix(rows).rank())
def exact_project_keep_unknowns(
    matrix_payload: dict[str, Any],
    *,
    keep_unknowns: Sequence[str],
    source_type: str = "exact_elimination",
) -> dict[str, Any]:
    """Project a full compatibility matrix onto a kept unknown subset exactly.

    Let the column ordering be split as `[keep | aux]`.  We compute row
    combinations lying in the left nullspace of `aux^T`; each such combination
    cancels every auxiliary variable exactly and yields a constraint involving
    only the kept columns.  Rank-gaining primitive integer rows are retained.
    """
    unknown_ordering = [str(unknown) for unknown in matrix_payload["global_unknown_ordering"]]
    keep_unknown_set = {str(unknown) for unknown in keep_unknowns}
    keep_indices = [
        index for index, unknown in enumerate(unknown_ordering)
        if unknown in keep_unknown_set
    ]
    aux_indices = [
        index for index, unknown in enumerate(unknown_ordering)
        if unknown not in keep_unknown_set
    ]
    if not keep_indices:
        raise ValueError("exact_project_keep_unknowns requires at least one kept unknown")

    matrix = sp.Matrix(matrix_payload["global_matrix"])
    if matrix.rows == 0:
        return {
            "global_unknown_ordering": [unknown_ordering[index] for index in keep_indices],
            "global_matrix_rows": [],
            "global_matrix": [],
            "elimination_semantics": "exact_left_nullspace_projection_of_full_compatibility",
            "eliminated_unknowns": [unknown_ordering[index] for index in aux_indices],
        }

    candidate_rows: list[dict[str, Any]] = []
    if aux_indices:
        aux_block = matrix[:, aux_indices]
        left_nullspace = aux_block.T.nullspace()
        for relation_index, coefficients in enumerate(left_nullspace, start=1):
            combined = coefficients.T * matrix
            projected_row = [combined[0, column_index] for column_index in keep_indices]
            primitive = _primitive_integer_row_exact(projected_row)
            if not any(primitive):
                continue
            support_rows = [
                int(row_index)
                for row_index, value in enumerate(coefficients)
                if sp.nsimplify(value) != 0
            ]
            candidate_rows.append(
                {
                    "basis_id": f"{source_type.upper()}_{relation_index:04d}",
                    "row_kind": "exact_auxiliary_elimination",
                    "matrix_row": primitive,
                    "support_row_indices": support_rows,
                }
            )
    else:
        for relation_index, row in enumerate(matrix.rowspace(), start=1):
            primitive = _primitive_integer_row_exact(row)
            if not any(primitive):
                continue
            candidate_rows.append(
                {
                    "basis_id": f"{source_type.upper()}_{relation_index:04d}",
                    "row_kind": "rowspace_basis_without_auxiliary_unknowns",
                    "matrix_row": primitive,
                    "support_row_indices": [relation_index - 1],
                }
            )

    candidate_rows.sort(key=lambda item: (tuple(item["matrix_row"]), item["basis_id"]))
    selected_rows: list[dict[str, Any]] = []
    running_rows: list[list[int]] = []
    running_rank = 0
    for row_record in candidate_rows:
        candidate_row = list(row_record["matrix_row"])
        candidate_rank = _row_rank_exact(running_rows + [candidate_row])
        if candidate_rank <= running_rank:
            continue
        selected_rows.append(row_record)
        running_rows.append(candidate_row)
        running_rank = candidate_rank

    reduced_unknown_ordering = [unknown_ordering[index] for index in keep_indices]
    reduced_matrix_rows = [
        {
            "source_type": source_type,
            "basis_id": row_record["basis_id"],
            "row_index_within_source": row_index,
            "equation_metadata": {
                key: value
                for key, value in row_record.items()
                if key != "matrix_row"
            },
            **{
                key: value
                for key, value in row_record.items()
                if key != "matrix_row"
            },
            "matrix_row": list(row_record["matrix_row"]),
        }
        for row_index, row_record in enumerate(selected_rows)
    ]
    return {
        "global_unknown_ordering": reduced_unknown_ordering,
        "global_matrix_rows": reduced_matrix_rows,
        "global_matrix": [list(row["matrix_row"]) for row in reduced_matrix_rows],
        "elimination_semantics": "exact_left_nullspace_projection_of_full_compatibility",
        "eliminated_unknowns": [unknown_ordering[index] for index in aux_indices],
    }
def smith_diagonal_entries(D: sp.Matrix) -> list[int]:
    diag = []
    for index in range(min(D.rows, D.cols)):
        value = int(abs(D[index, index]))
        if value:
            diag.append(value)
    return diag
def analyze_kernel(matrix_payload: dict[str, Any]) -> dict[str, Any]:
    unknown_ordering = list(matrix_payload["global_unknown_ordering"])
    unknown_count = len(unknown_ordering)
    if not matrix_payload["global_matrix"]:
        return {
            "unknown_ordering": unknown_ordering,
            "matrix_shape": [0, unknown_count],
            "rank": 0,
            "nullity": unknown_count,
            "smith_diagonal": [],
            "basis_vectors": [
                {
                    "id": f"basis_{basis_index + 1:02d}",
                    "vector": [1 if column_index == basis_index else 0 for column_index in range(unknown_count)],
                }
                for basis_index in range(unknown_count)
            ],
        }

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
        "unknown_ordering": unknown_ordering,
        "matrix_shape": [C.rows, C.cols],
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "basis_vectors": basis_vectors,
    }
