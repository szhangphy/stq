#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import sympy as sp

import swyckoff_k


GROUP_NUMBER = "10.4.1.31"
GROUP_REASON = "Smallest inspected k-space group with points, lines, and planes whose affine data stays clean."
COMPARISON_SUMMARY = "\n".join(
    [
        "- Compared `build_wyckoff_table_string(..., kspace=True, fast=True)` and `build_compact_json_payload(..., kspace=True, fast=True)` before/after the helper addition.",
        "- Tested 22 representative groups: `1.8.1.3`, `2.6.2.1`, `3.6.1.7`, `4.9.1.1`, `5.8.2.1`, `6.6.1.7`, `7.6.1.4`, `8.6.2.19`, `9.10.2.3`, `10.4.1.31`, `11.5.4.7`, `12.4.1.17`, `13.4.1.1`, `14.6.4.13`, `15.6.2.11`, `16.4.2.77`, `17.4.4.21`, `18.6.4.1`, `19.5.2.1`, `20.6.4.13`, `21.4.2.14`, `22.8.2.13`.",
        "- Result: all 22 groups matched byte-for-byte on both outputs.",
    ]
)
OUTPUT_FILES = {
    "audit": "geometry_audit.md",
    "manifolds": "single_group_kmanifolds.json",
    "connectivity": "single_group_connectivity.json",
}
ZERO = Fraction(0, 1)
HALF = Fraction(1, 2)
LINE_SAMPLE = Fraction(1, 5)
PLANE_SAMPLES = (Fraction(1, 5), Fraction(2, 5))
GENERIC_SAMPLES = (Fraction(1, 5), Fraction(2, 5), Fraction(3, 10))
BOUNDARY_VALUES = (ZERO, HALF)


def to_fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(value)


def frac_str(value: Fraction) -> str:
    value = to_fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def mod1_fraction(value: Fraction) -> Fraction:
    value = to_fraction(value) % 1
    return value + 1 if value < 0 else value


def vector_add_scaled(anchor: Sequence[Fraction], basis: Sequence[Fraction], scale: Fraction) -> List[Fraction]:
    return [to_fraction(a) + to_fraction(scale) * to_fraction(b) for a, b in zip(anchor, basis)]


def vector_key(vector: Sequence[Fraction]) -> Tuple[str, str, str]:
    return tuple(frac_str(mod1_fraction(value)) for value in vector)


def basis_key(vector: Sequence[Fraction]) -> Tuple[str, str, str]:
    return tuple(frac_str(to_fraction(value)) for value in vector)


def ordered_parameters(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> List[str]:
    ordered: List[str] = []
    for _const, coeffs in rep:
        for name in coeffs:
            if name not in ordered:
                ordered.append(name)
    return ordered


def rep_to_sympy(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> List[sp.Expr]:
    exprs: List[sp.Expr] = []
    for const, coeffs in rep:
        expr = sp.Rational(const.numerator, const.denominator)
        for name, coeff in coeffs.items():
            frac = to_fraction(coeff)
            expr += sp.Rational(frac.numerator, frac.denominator) * sp.Symbol(name)
        exprs.append(sp.simplify(expr))
    return exprs


def expr_str(expr: sp.Expr) -> str:
    return str(sp.simplify(expr))


def expr_vector_str(exprs: Sequence[sp.Expr]) -> str:
    return "(" + ", ".join(expr_str(expr) for expr in exprs) + ")"


def format_constraint_string(parameters: Sequence[str]) -> str:
    parts = [f"0 < {name} < 1/2" for name in parameters]
    return ", ".join(parts)


def sample_assignment(parameters: Sequence[str]) -> Dict[str, Fraction]:
    if not parameters:
        return {}
    if len(parameters) == 1:
        return {parameters[0]: LINE_SAMPLE}
    if len(parameters) == 2:
        return {parameters[0]: PLANE_SAMPLES[0], parameters[1]: PLANE_SAMPLES[1]}
    if len(parameters) == 3:
        return {
            parameters[0]: GENERIC_SAMPLES[0],
            parameters[1]: GENERIC_SAMPLES[1],
            parameters[2]: GENERIC_SAMPLES[2],
        }
    raise ValueError(f"Unsupported parameter count: {parameters}")


def evaluate_exprs(exprs: Sequence[sp.Expr], assignment: Dict[str, Fraction]) -> List[Fraction]:
    subs = {
        sp.Symbol(name): sp.Rational(value.numerator, value.denominator)
        for name, value in assignment.items()
    }
    evaluated: List[Fraction] = []
    for expr in exprs:
        value = sp.simplify(expr.subs(subs))
        evaluated.append(Fraction(int(value.p), int(value.q)))
    return evaluated


def line_signature(anchor: Sequence[Fraction], basis: Sequence[Fraction]) -> Tuple[Tuple[str, str, str], Tuple[str, str, str]]:
    return vector_key(anchor), basis_key(basis)


def boundary_line_expressions(
    anchor: Sequence[Fraction],
    basis: Sequence[Fraction],
    parameter: str,
) -> List[sp.Expr]:
    symbol = sp.Symbol(parameter)
    exprs: List[sp.Expr] = []
    for coord, step in zip(anchor, basis):
        expr = sp.Rational(coord.numerator, coord.denominator)
        if step:
            expr += sp.Rational(step.numerator, step.denominator) * symbol
        exprs.append(sp.simplify(expr))
    return exprs


def geometry_type(dimension: int) -> str:
    return {0: "point", 1: "line", 2: "plane", 3: "generic"}[dimension]


def assign_ids(entries: Sequence[dict], prefix: str) -> None:
    for index, entry in enumerate(entries, start=1):
        entry["id"] = f"{prefix}{index}"


def load_reciprocal_context() -> dict:
    data, _time_revs = swyckoff_k.load_irssg_data(GROUP_NUMBER, 0)
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
    ops = ctx["ops"]
    mag_ops_real = ctx["mag_ops_real"]
    spin_ops_symbolic = ctx["spin_ops_symbolic"]
    mag_stab_ops = [mag_ops_real[i] for i in indices]
    spin_stab_ops_symbolic = [spin_ops_symbolic[i] for i in indices]
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
    if basis:
        generic_point = swyckoff_k.generic_point_on_subspace(anchor, basis)
    else:
        generic_point = list(anchor)
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
        line["closure_under_pointwise_stabilizer"] = closure_components(
            line["_anchor"],
            line["_basis"],
            ctx,
            line_orbit_to_id,
            plane_orbit_to_id,
        )
    for plane in planes:
        plane["manifold_role"] = "separately_listed_special_plane_manifold"
        plane["symmetry_summary"] = subspace_symmetry_summary(plane["_anchor"], plane["_basis"], ctx)


def normalize_entry(entry: dict) -> dict:
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
        "parameter_range_note": "Half-interval fundamental domain inferred from the explicit k -> -k orbit pairing.",
    }

    return {
        "label": entry["letter"],
        "type": geometry_type(dimension),
        "dimension": dimension,
        "parametrization": expr_vector_str(exprs),
        "coordinate_expressions": [expr_str(expr) for expr in exprs],
        "parameters": params,
        "constraints": constraints,
        "constraint_summary": format_constraint_string(params),
        "sample_point": [frac_str(mod1_fraction(value)) for value in sample],
        "metadata": metadata,
        "_anchor": anchor,
        "_basis": basis,
        "_exprs": exprs,
        "_params": params,
    }


def pick_group_entries() -> Dict[str, List[dict]]:
    wyckoff, coord_key = swyckoff_k.compute_wyckoff_output(GROUP_NUMBER, kspace=True, fast=True)
    if coord_key != "orbit":
        raise ValueError(f"Unexpected coordinate key: {coord_key}")

    points: List[dict] = []
    lines: List[dict] = []
    planes: List[dict] = []
    generic: List[dict] = []
    for entry in wyckoff:
        normalized = normalize_entry(entry)
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

    return {
        "points": points,
        "lines": lines,
        "planes": planes,
        "generic": generic,
    }


def infer_line_connectivity(points: Sequence[dict], lines: Sequence[dict]) -> Tuple[List[dict], List[dict]]:
    point_map = {vector_key(point["_anchor"]): point for point in points}
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


def infer_plane_connectivity(
    planes: Sequence[dict],
    lines: Sequence[dict],
    ctx: dict,
    line_orbit_to_id: dict,
    plane_orbit_to_id: dict,
) -> Tuple[List[dict], List[dict]]:
    line_map = {
        line_signature(line["_anchor"], line["_basis"][0]): line
        for line in lines
    }
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
                    "sample_point": [
                        frac_str(mod1_fraction(value))
                        for value in vector_add_scaled(anchor, free_basis, LINE_SAMPLE)
                    ],
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
                    "reason": (
                        "Matches an existing 1D manifold orbit."
                        if line_orbit_to_id.get(orbit_key)
                        else "Does not match any listed 1D manifold orbit."
                    ),
                }
                if line:
                    candidate["line_id"] = line["id"]
                    candidate["classification"]["reason"] = "Geometric boundary coincides with a separately listed special line."
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


def strip_internal_fields(entries: Sequence[dict]) -> List[dict]:
    cleaned: List[dict] = []
    for entry in entries:
        cleaned.append(
            {
                key: value
                for key, value in entry.items()
                if not key.startswith("_")
            }
        )
    return cleaned


def json_ready(value):
    if isinstance(value, Fraction):
        return frac_str(value)
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    return value


def build_payloads() -> Tuple[dict, dict]:
    grouped = pick_group_entries()
    points = grouped["points"]
    lines = grouped["lines"]
    planes = grouped["planes"]
    generic = grouped["generic"]
    ctx = load_reciprocal_context()
    line_orbit_to_id, plane_orbit_to_id = subspace_orbit_id_maps(lines, planes, ctx)
    annotate_special_manifolds(lines, planes, ctx, line_orbit_to_id, plane_orbit_to_id)

    point_line, unmatched_endpoints = infer_line_connectivity(points, lines)
    line_plane, unmatched_plane_boundaries = infer_plane_connectivity(
        planes,
        lines,
        ctx,
        line_orbit_to_id,
        plane_orbit_to_id,
    )

    manifolds = {
        "group_number": GROUP_NUMBER,
        "source": {
            "module": "swyckoff_k.py",
            "function": "compute_wyckoff_output",
            "arguments": {"ssgnum": GROUP_NUMBER, "kspace": True, "fast": True},
        },
        "interpretation": {
            "listed_line_objects": "Separately listed special 1D manifold types emitted by swyckoff_k.py.",
            "plane_boundary_candidates": "Geometric boundary lines derived from plane parameter domains; they are not required to match the separately listed line list.",
        },
        "objects": strip_internal_fields(points + lines + planes),
        "generic_manifolds_ignored": strip_internal_fields(generic),
    }
    connectivity = {
        "group_number": GROUP_NUMBER,
        "interpretation": {
            "point_line": "A point-line edge is recorded only when a line endpoint exactly matches an existing listed point.",
            "line_plane": "A line-plane edge is recorded only when a geometric plane boundary exactly matches an existing separately listed line manifold.",
            "unmatched_plane_boundaries": "These are still valid geometric boundaries; unmatched means only that swyckoff_k.py did not list the same 1D orbit as an independent special line manifold.",
        },
        "point_line": point_line,
        "line_plane": line_plane,
        "unmatched_line_endpoints": unmatched_endpoints,
        "unmatched_plane_boundaries": unmatched_plane_boundaries,
    }
    return manifolds, connectivity


def build_audit_markdown(comparison_summary: str | None = None) -> str:
    summary = comparison_summary if comparison_summary is not None else COMPARISON_SUMMARY
    lines = [
        "# Geometry Audit",
        "",
        "## swyckoff_k.py real input",
        "",
        "- CLI: `python swyckoff_k.py --irssg-ssgnum 10.4.1.31 --kspace --fast`",
        "- Module entry: `swyckoff_k.compute_wyckoff_output('10.4.1.31', kspace=True, fast=True)`",
        "- The required group identifier is the full `irssg` `ssgNum` string such as `10.4.1.31`; short forms like `10` are not accepted.",
        "",
        "## swyckoff_k.py real output",
        "",
        "- `compute_wyckoff_output(...)` returns `(wyckoff, coord_key)`.",
        "- `wyckoff` is a list of dict entries containing at least `letter`, `mult`, `dim`, `rep`, `basis_vecs`, `x0`, `representative_coordinate`, and `orbit`.",
        "- The raw entries also carry spin/moment/site-symmetry display fields. Those are not needed for this pure-geometry task.",
        "- Parameter ranges are **not** emitted by `swyckoff_k.py`; this wrapper infers a half-interval fundamental domain from the explicit `k -> -k` orbit pairing in the chosen demo group.",
        "",
        "## Demo group",
        "",
        f"- Selected group: `{GROUP_NUMBER}`.",
        f"- Reason: {GROUP_REASON}",
        "- This group currently returns `8` points, `4` lines, `2` planes, and one ignored generic 3D manifold.",
        "",
        "## Removed as unnecessary for pure geometry",
        "",
        "- Added `compact_geometry_entries(...)` and `build_geometry_json_payload(...)` to `swyckoff_k.py`.",
        "- The geometry wrapper drops `moment_*`, `orbit_with_moments`, `site_symmetry*`, `spin_matrix`, `time_reversal`, and related magnetic-display fields.",
        "- The enumeration core is intentionally unchanged; only a geometry-only projection helper was added.",
        "",
        "## Wrapper layer",
        "",
        "- `kgeometry_single.py` calls `compute_wyckoff_output(...)`, keeps only dimensions `0/1/2`, normalizes them, infers half-interval parameter ranges, derives line endpoints and plane boundary candidates, then exports JSON/Markdown.",
        "- `demo_single_group.py` runs the wrapper for one group and prints the requested summary.",
        "",
        "## Boundary interpretation",
        "",
        "- The listed line objects are treated as `separately listed special 1D manifold` entries because they are present in `swyckoff_k.py` output as dimension-1 items.",
        "- The plane boundary candidates are treated as `geometric boundary line` objects first. They are only promoted to `line_plane` edges when their full 1D orbit matches an existing listed line manifold.",
        "- For `10.4.1.31`, the eight plane boundary candidates do **not** match any listed line orbit. Recomputed stabilizers alone do not separate them from the listed lines, but `closure_under_stabilizer` does: each boundary candidate closes back to the two listed plane manifolds `S1` and `S2`, not to an independent 1D orbit.",
        "- Therefore `line_plane` being empty for this group is expected and is not treated as a bug.",
    ]
    if summary:
        lines.extend(["", "## 20+ group comparison", "", summary])
    return "\n".join(lines) + "\n"


def write_outputs(output_dir: Path, comparison_summary: str | None = None) -> Tuple[dict, dict]:
    manifolds, connectivity = build_payloads()
    output_dir.joinpath(OUTPUT_FILES["manifolds"]).write_text(
        json.dumps(json_ready(manifolds), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath(OUTPUT_FILES["connectivity"]).write_text(
        json.dumps(json_ready(connectivity), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_dir.joinpath(OUTPUT_FILES["audit"]).write_text(
        build_audit_markdown(comparison_summary=comparison_summary),
        encoding="utf-8",
    )
    return manifolds, connectivity


def build_demo_text(manifolds: dict, connectivity: dict) -> str:
    objects = manifolds["objects"]
    points = [obj for obj in objects if obj["type"] == "point"]
    lines = [obj for obj in objects if obj["type"] == "line"]
    planes = [obj for obj in objects if obj["type"] == "plane"]

    out: List[str] = [
        f"- group: {GROUP_NUMBER}",
        f"- points: {len(points)}",
        f"- lines: {len(lines)}",
        f"- planes: {len(planes)}",
        "",
    ]

    for line in lines:
        out.append(f"Line {line['id']}: k={line['parametrization']}, {line['constraint_summary']}")
        out.append("  endpoints:")
        for endpoint in line.get("endpoints", []):
            if endpoint["point_id"]:
                out.append(
                    f"    {endpoint['point_id']} = ({', '.join(endpoint['point_coordinates'])})"
                    f"  [{endpoint['boundary_condition']}]"
                )
            else:
                out.append(
                    f"    unmatched = ({', '.join(endpoint['point_coordinates'])})"
                    f"  [{endpoint['boundary_condition']}]"
                )
        out.append("")

    for plane in planes:
        out.append(f"Plane {plane['id']}: k={plane['parametrization']}, {plane['constraint_summary']}")
        out.append("  boundary lines:")
        for boundary in plane.get("boundary_lines", []):
            if boundary["line_id"]:
                out.append(
                    f"    {boundary['line_id']}: {boundary['parametrization']}"
                    f"  [{boundary['boundary_condition']}]"
                )
            else:
                closure_planes = [
                    component["plane_id"]
                    for component in boundary.get("closure_under_pointwise_stabilizer", [])
                    if component.get("plane_id")
                ]
                closure_note = ""
                if closure_planes:
                    closure_note = f"; closure -> {', '.join(closure_planes)}"
                out.append(
                    f"    geometric only: {boundary['parametrization']}"
                    f"  [{boundary['boundary_condition']}{closure_note}]"
                )
        out.append("")

    out.append("Connectivity summary:")
    for relation in connectivity["point_line"]:
        out.append(
            f"- {relation['point_id']} <-> {relation['line_id']} via {relation['boundary_condition']}"
        )
    if connectivity["line_plane"]:
        for relation in connectivity["line_plane"]:
            out.append(
                f"- {relation['line_id']} <-> {relation['plane_id']} via {relation['boundary_condition']}"
            )
    else:
        out.append("- no matched line-plane boundaries; every derived plane boundary is geometric-only in this group")
    if connectivity["unmatched_plane_boundaries"]:
        out.append("- unmatched plane boundaries:")
        for relation in connectivity["unmatched_plane_boundaries"]:
            out.append(
                f"  {relation['plane_id']} -> {relation['derived_line']} via {relation['boundary_condition']}"
            )
    return "\n".join(out) + "\n"


def validate_payloads(manifolds: dict, connectivity: dict, output_dir: Path) -> List[str]:
    issues: List[str] = []
    if manifolds.get("group_number") != GROUP_NUMBER:
        issues.append("wrong group number in single_group_kmanifolds.json")

    objects = manifolds.get("objects", [])
    points = [obj for obj in objects if obj.get("type") == "point"]
    lines = [obj for obj in objects if obj.get("type") == "line"]
    planes = [obj for obj in objects if obj.get("type") == "plane"]
    if len(points) != 8:
        issues.append(f"expected 8 points, found {len(points)}")
    if len(lines) != 4:
        issues.append(f"expected 4 lines, found {len(lines)}")
    if len(planes) != 2:
        issues.append(f"expected 2 planes, found {len(planes)}")

    if len(connectivity.get("point_line", [])) != 8:
        issues.append("expected 8 point-line boundary relations")
    if connectivity.get("unmatched_line_endpoints"):
        issues.append("line endpoint matching is incomplete")
    if not connectivity.get("line_plane") and not connectivity.get("unmatched_plane_boundaries"):
        issues.append("plane boundary inference produced no output")

    required = [
        OUTPUT_FILES["audit"],
        OUTPUT_FILES["manifolds"],
        OUTPUT_FILES["connectivity"],
        "demo_single_group.py",
    ]
    for name in required:
        if not output_dir.joinpath(name).exists():
            issues.append(f"missing required file: {name}")

    demo = subprocess.run(
        [sys.executable, "demo_single_group.py"],
        cwd=output_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if demo.returncode != 0:
        issues.append("demo_single_group.py failed")
    else:
        stdout = demo.stdout
        required_snippets = [GROUP_NUMBER, "Line L1:", "Plane S1:", "Connectivity summary:"]
        for snippet in required_snippets:
            if snippet not in stdout:
                issues.append(f"demo output missing snippet: {snippet}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one pure-geometric single-group k-manifold demo.")
    parser.add_argument("--output-dir", default=".")
    parser.add_argument("--comparison-summary")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    manifolds, connectivity = write_outputs(output_dir, comparison_summary=args.comparison_summary)
    if args.validate:
        issues = validate_payloads(manifolds, connectivity, output_dir)
        for issue in issues:
            print(issue, file=sys.stderr)
        print(len(issues))
        return 0 if not issues else 1

    print(build_demo_text(manifolds, connectivity), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
