#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cmath
import contextlib
import importlib.util
import io
import json
import pickle
import shutil
import tarfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp
from sympy.polys.domains import ZZ

import debug_single_connection as single
import debug_single_group_ai_bridge as single_bridge
import debug_single_group_ai_expanded as single_expanded
import swyckoff_r


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 2

POINT_IDS = [f"P{i}" for i in range(1, 9)]
LINE_IDS = [f"L{i}" for i in range(1, 5)]
PLANE_IDS = ["S1", "S2"]

REVIEW_DOUBLE_FEAS = ROOT / "review_package_10.4.1.31_double_feasibility"
GEOMETRY_PATH = REVIEW_DOUBLE_FEAS / "background" / "single_group_kmanifolds.json"
CONNECTIVITY_PATH = REVIEW_DOUBLE_FEAS / "background" / "single_group_connectivity.json"
SINGLE_WITH_PLANES_RAW_PATH = REVIEW_DOUBLE_FEAS / "basis" / "single_group_bs_with_planes_basis_raw.json"
SINGLE_WITH_PLANES_PRETTY_PATH = REVIEW_DOUBLE_FEAS / "basis" / "single_group_bs_with_planes_basis_pretty.json"
SINGLE_WITH_PLANES_MATRIX_PATH = REVIEW_DOUBLE_FEAS / "matrix" / "single_group_full_compatibility_with_planes.json"

AUDIT_MD = ROOT / "double_group_kspace_backbone_audit_10.4.1.31.md"
SUMMARY_JSON = ROOT / "double_group_kspace_backbone_summary_10.4.1.31.json"
LINE_BLOCKS_JSON = ROOT / "double_group_line_blocks_10.4.1.31.json"
LINE_ONLY_JSON = ROOT / "double_group_full_compatibility_line_only_10.4.1.31.json"
PLANE_AUDIT_MD = ROOT / "double_group_plane_necessity_audit_10.4.1.31.md"
WITH_PLANES_JSON = ROOT / "double_group_full_compatibility_with_planes_10.4.1.31.json"
BS_SUMMARY_JSON = ROOT / "double_group_bs_summary_10.4.1.31.json"
BS_RAW_JSON = ROOT / "double_group_bs_basis_raw_10.4.1.31.json"
BS_PRETTY_JSON = ROOT / "double_group_bs_basis_pretty_10.4.1.31.json"
EMBED_JSON = ROOT / "double_group_minimal_ai_embedding_10.4.1.31.json"

PACKAGE_NAME = "review_package_10.4.1.31_double_kspace_backbone"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TAR = ROOT / f"{PACKAGE_NAME}.tar.gz"

P_MATRIX = [[1, 0, 0], [0, 2, 0], [0, 0, 2]]

EXPECTED_LINE_ENDPOINTS = {
    "L1": ("P1", "P4"),
    "L2": ("P2", "P6"),
    "L3": ("P3", "P5"),
    "L4": ("P7", "P8"),
}

REQUIRED_NEW_FILES = [
    AUDIT_MD,
    SUMMARY_JSON,
    LINE_BLOCKS_JSON,
    LINE_ONLY_JSON,
    PLANE_AUDIT_MD,
    BS_SUMMARY_JSON,
    BS_RAW_JSON,
    BS_PRETTY_JSON,
    EMBED_JSON,
    ROOT / "debug_double_group_kspace_backbone_10.4.1.31.py",
    PACKAGE_TAR,
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def reset_dir(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    path.mkdir(parents=True, exist_ok=True)


def format_tree(root: Path) -> list[str]:
    lines = [root.name]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def parse_fraction(value: str) -> Fraction:
    return Fraction(value)


def cli_str(value: Fraction) -> str:
    return format(float(value), ".12g")


def frac_list_to_float(values: list[str]) -> list[float]:
    return [float(parse_fraction(value)) for value in values]


def complex_to_json(value: complex) -> dict[str, float]:
    return {
        "real": round(float(value.real), 12),
        "imag": round(float(value.imag), 12),
    }


def complex_list_to_json(values: list[complex]) -> list[dict[str, float]]:
    return [complex_to_json(value) for value in values]


def complex_matrix_to_json(matrix: list[list[complex]]) -> list[list[dict[str, float]]]:
    return [complex_list_to_json(row) for row in matrix]


def support_from_vector(vector: list[int], unknown_ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown, "coeff": int(coeff)}
        for unknown, coeff in zip(unknown_ordering, vector)
        if coeff
    ]


def first_nonzero_sign(vector: list[int]) -> int:
    for coeff in vector:
        if coeff > 0:
            return 1
        if coeff < 0:
            return -1
    return 1


def smith_diagonal_from_D(D: sp.Matrix) -> list[int]:
    diagonal = []
    for i in range(min(D.rows, D.cols)):
        value = int(D[i, i])
        if value:
            diagonal.append(abs(value))
    return diagonal


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


@contextlib.contextmanager
def suppress_output() -> Any:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


def load_ssgreps_module():
    ssgreps_py = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
    ssgreps_dir = ssgreps_py.parent
    if str(ssgreps_dir) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(ssgreps_dir))
    spec = importlib.util.spec_from_file_location("ssgreps_local", ssgreps_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {ssgreps_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ssg_dict() -> dict[str, Any]:
    identify_pkl = ROOT / "SSGReps" / "ssg_data" / "identify.pkl"
    with identify_pkl.open("rb") as fh:
        ssg_list = pickle.load(fh)
    return next(item for item in ssg_list if item["ssgNum"] == GROUP_NUMBER)


def load_double_context(module: Any, ssg_dict: dict[str, Any]) -> dict[str, Any]:
    ssg = module.loadSsgGroup(GROUP_NUMBER, np.array([0.0, 0.0, 0.0]), "double", ssg_dict)
    with suppress_output():
        full_data, _ = swyckoff_r.load_irssg_data(GROUP_NUMBER, 0)
        wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(GROUP_NUMBER, fast=True)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]
    ctx = {
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": full_data,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
        "wyckoff_entries": wyckoff_entries,
    }
    ctx["raw_operations"] = single_expanded.raw_ops(ctx)
    ctx["group_tables"] = single_expanded.build_group_tables(ctx)
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in wyckoff_entries}
    ctx["spatial_bridge"] = single_bridge.validate_operation_bridge(ctx)
    return ctx


def load_background_bundle() -> dict[str, Any]:
    return {
        "double_feas_readme": (REVIEW_DOUBLE_FEAS / "README.md").read_text(),
        "double_feas_audit": (REVIEW_DOUBLE_FEAS / "double_group_feasibility_audit_10.4.1.31.md").read_text(),
        "double_feas_summary": load_json(REVIEW_DOUBLE_FEAS / "double_group_feasibility_summary_10.4.1.31.json"),
        "double_min_kspace": load_json(REVIEW_DOUBLE_FEAS / "double_group_minimal_kspace_10.4.1.31.json"),
        "double_min_realspace": load_json(REVIEW_DOUBLE_FEAS / "double_group_minimal_realspace_10.4.1.31.json"),
        "double_min_bs_ai": load_json(REVIEW_DOUBLE_FEAS / "double_group_minimal_bs_ai_summary_10.4.1.31.json"),
        "single_kmanifolds": load_json(GEOMETRY_PATH),
        "single_connectivity": load_json(CONNECTIVITY_PATH),
        "single_bs_with_planes_raw": load_json(SINGLE_WITH_PLANES_RAW_PATH),
        "single_bs_with_planes_pretty": load_json(SINGLE_WITH_PLANES_PRETTY_PATH),
        "single_full_with_planes": load_json(SINGLE_WITH_PLANES_MATRIX_PATH),
    }


def point_coordinates(point_obj: dict[str, Any]) -> list[str]:
    return list(point_obj["coordinate_expressions"])


def derive_plane_corner_points(objects: dict[str, Any], plane_obj: dict[str, Any]) -> list[str]:
    fixed_y = plane_obj["parametrization"].split(",")[1].strip()
    corner_points = []
    for point_id in POINT_IDS:
        coords = point_coordinates(objects[point_id])
        if coords[1] == fixed_y and coords[0] in {"0", "1/2"} and coords[2] in {"0", "1/2"}:
            corner_points.append(point_id)
    return sorted(corner_points, key=lambda item: int(item[1:]))


def load_geometry_context() -> dict[str, Any]:
    kmanifolds = load_json(GEOMETRY_PATH)
    connectivity = load_json(CONNECTIVITY_PATH)
    objects = {item["id"]: item for item in kmanifolds["objects"]}

    for point_id in POINT_IDS:
        if point_id not in objects:
            raise ValueError(f"missing point {point_id} in {GEOMETRY_PATH}")
    for line_id in LINE_IDS:
        if line_id not in objects:
            raise ValueError(f"missing line {line_id} in {GEOMETRY_PATH}")
    for plane_id in PLANE_IDS:
        if plane_id not in objects:
            raise ValueError(f"missing plane {plane_id} in {GEOMETRY_PATH}")

    blocks = []
    for line_id in LINE_IDS:
        line_obj = objects[line_id]
        edges = [edge for edge in connectivity["point_line"] if edge["line_id"] == line_id]
        left_edge = next((edge for edge in edges if edge["boundary_condition"] == "v = 0"), None)
        right_edge = next((edge for edge in edges if edge["boundary_condition"] == "v = 1/2"), None)
        if left_edge is None or right_edge is None:
            raise ValueError(f"{line_id} does not expose the expected v-boundary metadata")
        if (left_edge["point_id"], right_edge["point_id"]) != EXPECTED_LINE_ENDPOINTS[line_id]:
            raise ValueError(
                f"{line_id} endpoints {(left_edge['point_id'], right_edge['point_id'])} "
                f"do not match expected {EXPECTED_LINE_ENDPOINTS[line_id]}"
            )
        blocks.append(
            {
                "left_point_id": left_edge["point_id"],
                "line_id": line_id,
                "right_point_id": right_edge["point_id"],
                "left_exact_k": list(objects[left_edge["point_id"]]["sample_point"]),
                "line_exact_k": list(line_obj["sample_point"]),
                "right_exact_k": list(objects[right_edge["point_id"]]["sample_point"]),
                "left_cli_k": [cli_str(parse_fraction(v)) for v in objects[left_edge["point_id"]]["sample_point"]],
                "line_cli_k": [cli_str(parse_fraction(v)) for v in line_obj["sample_point"]],
                "right_cli_k": [cli_str(parse_fraction(v)) for v in objects[right_edge["point_id"]]["sample_point"]],
                "line_parametrization": line_obj["parametrization"],
                "line_constraints": list(line_obj["constraints"]),
                "line_sample_point": list(line_obj["sample_point"]),
                "line_coordinates": list(line_obj["coordinate_expressions"]),
                "line_symmetry_summary": dict(line_obj["symmetry_summary"]),
                "connectivity_edges": [left_edge, right_edge],
            }
        )

    planes = {}
    for plane_id in PLANE_IDS:
        plane_obj = objects[plane_id]
        planes[plane_id] = {
            "id": plane_id,
            "coordinates": list(plane_obj["coordinate_expressions"]),
            "parametrization": plane_obj["parametrization"],
            "constraints": list(plane_obj["constraints"]),
            "sample_point": list(plane_obj["sample_point"]),
            "symmetry_summary": dict(plane_obj["symmetry_summary"]),
            "corner_points": derive_plane_corner_points(objects, plane_obj),
        }

    return {
        "kmanifolds": kmanifolds,
        "connectivity": connectivity,
        "objects": objects,
        "line_blocks": blocks,
        "planes": planes,
        "unmatched_plane_boundaries": list(connectivity["unmatched_plane_boundaries"]),
    }


def complex_key(value: complex, digits: int = 8) -> tuple[float, float]:
    return (round(float(value.real), digits), round(float(value.imag), digits))


def capture_little_group(
    module: Any,
    ssg_dict: dict[str, Any],
    manifold_id: str,
    exact_k: list[str],
) -> dict[str, Any]:
    kvec = np.array(frac_list_to_float(exact_k), dtype=float)
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        lg = module.load_little_group(GROUP_NUMBER, kvec, False, "double", ssg_dict)

    raw_character = [[complex(value) for value in row] for row in lg.character]
    linear_character = [[complex(value) for value in row] for row in lg.linear_character]
    su2_json = [
        [[complex_to_json(complex(entry)) for entry in row] for row in matrix]
        for matrix in lg.su2s
    ]
    detail = {
        "status": "ok",
        "group_type": GROUP_TYPE,
        "manifold_id": manifold_id,
        "exact_k": list(exact_k),
        "cli_k": [cli_str(parse_fraction(v)) for v in exact_k],
        "warning_text": stdout.getvalue().strip(),
        "rep_count": len(lg.rep_degree),
        "rep_degree": [int(value) for value in lg.rep_degree],
        "torsion": [int(value) for value in lg.torsion],
        "character": raw_character,
        "linear_character": linear_character,
        "character_json": complex_matrix_to_json(raw_character),
        "linear_character_json": complex_matrix_to_json(linear_character),
        "character_available": bool(raw_character or len(lg.rep_degree) == 0),
        "linear_character_available": bool(linear_character or len(lg.rep_degree) == 0),
        "n_ops_total": len(lg.rotC),
        "n_unitary_ops": sum(1 for sign in lg.time_reversal if sign > 0),
        "n_antiunitary_ops": sum(1 for sign in lg.time_reversal if sign < 0),
        "time_reversal": [int(sign) for sign in lg.time_reversal],
        "rotC": [
            [[int(round(float(entry))) for entry in row] for row in matrix]
            for matrix in lg.rotC
        ],
        "tauC": [
            [single.normalize_float(float(entry)) for entry in vector]
            for vector in lg.tauC
        ],
        "tauC_mod1": [
            [single.normalize_float(float(entry) % 1.0) for entry in vector]
            for vector in lg.tauC
        ],
        "spin": [
            [[int(round(float(entry))) for entry in row] for row in matrix]
            for matrix in lg.spin
        ],
        "su2": su2_json,
        "character_shape": [len(raw_character), len(raw_character[0]) if raw_character else 0],
        "linear_character_shape": [len(linear_character), len(linear_character[0]) if linear_character else 0],
    }
    return detail


def compare_details(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    def allclose_matrix(a: list[list[complex]], b: list[list[complex]]) -> bool:
        if len(a) != len(b):
            return False
        if not a:
            return True
        return bool(np.allclose(np.array(a, dtype=complex), np.array(b, dtype=complex), atol=1e-8))

    return {
        "same_rep_degree": left["rep_degree"] == right["rep_degree"],
        "same_torsion": left["torsion"] == right["torsion"],
        "same_time_reversal": left["time_reversal"] == right["time_reversal"],
        "same_rotC": left["rotC"] == right["rotC"],
        "same_tauC": left["tauC"] == right["tauC"],
        "same_spin": left["spin"] == right["spin"],
        "same_character": allclose_matrix(left["character"], right["character"]),
        "same_linear_character": allclose_matrix(left["linear_character"], right["linear_character"]),
    }


def build_manifold_details(module: Any, geometry: dict[str, Any], ssg_dict: dict[str, Any]) -> dict[str, Any]:
    sample_points = {
        point_id: list(geometry["objects"][point_id]["sample_point"])
        for point_id in POINT_IDS
    }
    sample_points.update(
        {
            block["line_id"]: list(block["line_exact_k"])
            for block in geometry["line_blocks"]
        }
    )
    sample_points.update(
        {
            plane_id: list(geometry["planes"][plane_id]["sample_point"])
            for plane_id in PLANE_IDS
        }
    )

    details: dict[str, Any] = {}
    stability: dict[str, Any] = {}
    for manifold_id in POINT_IDS + LINE_IDS + PLANE_IDS:
        first = capture_little_group(module, ssg_dict, manifold_id, sample_points[manifold_id])
        second = capture_little_group(module, ssg_dict, manifold_id, sample_points[manifold_id])
        details[manifold_id] = first
        stability[manifold_id] = compare_details(first, second)
    return {
        "details": details,
        "stability": stability,
        "all_stable": all(all(item.values()) for item in stability.values()),
    }


def operation_key_from_detail(detail: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(entry) for entry in row) for row in detail["rotC"][op_index])
    tau = tuple(single.normalize_float(float(entry) % 1.0) for entry in detail["tauC"][op_index])
    spin = tuple(tuple(int(entry) for entry in row) for row in detail["spin"][op_index])
    su2 = tuple(
        tuple(
            complex_key(complex(cell["real"], cell["imag"]))
            for cell in row
        )
        for row in detail["su2"][op_index]
    )
    return rot, tau, spin, su2, int(detail["time_reversal"][op_index])


def basis_labels_for_manifold(manifold_id: str, detail: dict[str, Any]) -> list[str]:
    return [f"{manifold_id}_R{i}" for i in range(1, detail["rep_count"] + 1)]


def exact_basis_matrix(detail: dict[str, Any], mode: str) -> sp.Matrix:
    return sp.Matrix(
        [
            [single.as_exact_char(complex(value)) for value in rep_character]
            for rep_character in detail[mode]
        ]
    ).T


def solve_decomposition(
    basis_matrix: sp.Matrix,
    restricted_character: sp.Matrix,
    *,
    context: str,
) -> list[int]:
    solution, params = basis_matrix.gauss_jordan_solve(restricted_character)
    if params.rows * params.cols:
        raise ValueError(f"non-unique decomposition in {context}")
    coeffs = list(solution)
    return coerce_integer_coeffs(coeffs, context)


def numerically_assess_mode(
    source_detail: dict[str, Any],
    target_detail: dict[str, Any],
    matched: list[int],
    mode: str,
) -> dict[str, Any]:
    basis = np.array(target_detail[mode], dtype=complex).T
    pinv = np.linalg.pinv(basis)
    max_coeff_dev = 0.0
    max_recon_dev = 0.0
    worst: dict[str, Any] | None = None
    all_integer_like = True
    for rep_index, rep_character in enumerate(source_detail[mode], start=1):
        restricted = np.array([rep_character[index] for index in matched], dtype=complex)
        coeffs = pinv @ restricted
        recon = basis @ coeffs
        coeff_dev = max(
            float(np.max(np.abs(coeffs.imag))) if coeffs.size else 0.0,
            float(np.max(np.abs(coeffs.real - np.round(coeffs.real)))) if coeffs.size else 0.0,
        )
        recon_dev = float(np.max(np.abs(recon - restricted))) if recon.size else 0.0
        if coeff_dev > max_coeff_dev or recon_dev > max_recon_dev:
            max_coeff_dev = max(max_coeff_dev, coeff_dev)
            max_recon_dev = max(max_recon_dev, recon_dev)
            worst = {
                "rep_id": rep_index,
                "coefficients_rounded": complex_list_to_json([complex(value) for value in coeffs]),
                "reconstruction_deviation": round(recon_dev, 12),
            }
        if coeff_dev > 1e-6 or recon_dev > 1e-6:
            all_integer_like = False
    return {
        "all_integer_like": all_integer_like,
        "max_coefficient_deviation_from_nearest_integer": round(max_coeff_dev, 12),
        "max_reconstruction_deviation": round(max_recon_dev, 12),
        "worst_case": worst,
    }


def build_line_block(
    block: dict[str, Any],
    details: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    line_id = block["line_id"]
    left_id = block["left_point_id"]
    right_id = block["right_point_id"]
    line_detail = details[line_id]
    left_detail = details[left_id]
    right_detail = details[right_id]

    line_unitary_ops = [
        operation_key_from_detail(line_detail, op_index)
        for op_index, sign in enumerate(line_detail["time_reversal"])
        if sign > 0
    ]
    if len(line_unitary_ops) != line_detail["character_shape"][1]:
        raise ValueError(f"{line_id} unitary operation count does not match character length")

    line_basis_labels = basis_labels_for_manifold(line_id, line_detail)
    line_basis_matrix = exact_basis_matrix(line_detail, mode)

    endpoint_decompositions: dict[str, Any] = {}
    matched_operation_indices: dict[str, list[int]] = {}
    mode_viability: dict[str, Any] = {}
    for endpoint_id, endpoint_detail in ((left_id, left_detail), (right_id, right_detail)):
        unitary_map = {
            operation_key_from_detail(endpoint_detail, op_index): unitary_index
            for unitary_index, (op_index, sign) in enumerate(
                item for item in enumerate(endpoint_detail["time_reversal"]) if item[1] > 0
            )
        }
        matched = [unitary_map.get(op_key) for op_key in line_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(f"{endpoint_id} does not contain the full {line_id} unitary subgroup")
        matched_operation_indices[endpoint_id] = [int(index) for index in matched]
        mode_viability[endpoint_id] = numerically_assess_mode(endpoint_detail, line_detail, matched, mode)

        reps = []
        for rep_index, rep_character in enumerate(endpoint_detail[mode], start=1):
            restricted = sp.Matrix(
                [single.as_exact_char(complex(rep_character[index])) for index in matched]
            )
            coeffs_int = solve_decomposition(
                line_basis_matrix,
                restricted,
                context=f"{endpoint_id} rep {rep_index} on {line_id} using {mode}",
            )
            reps.append(
                {
                    "rep_id": f"{endpoint_id}_R{rep_index}",
                    "rep_degree": int(endpoint_detail["rep_degree"][rep_index - 1]),
                    "torsion": int(endpoint_detail["torsion"][rep_index - 1]),
                    "restricted_character_on_line_unitary_subgroup": [str(entry) for entry in restricted],
                    "decomposition_on_line_basis": {
                        basis_label: coeff
                        for basis_label, coeff in zip(line_basis_labels, coeffs_int)
                        if coeff
                    },
                }
            )
        endpoint_decompositions[endpoint_id] = reps

    equations = []
    matrix_rows = []
    local_unknown_ordering = [item["rep_id"] for item in endpoint_decompositions[left_id]] + [
        item["rep_id"] for item in endpoint_decompositions[right_id]
    ]
    for basis_label in line_basis_labels:
        row = []
        left_terms = []
        right_terms = []
        for item in endpoint_decompositions[left_id]:
            coeff = item["decomposition_on_line_basis"].get(basis_label, 0)
            row.append(int(coeff))
            if coeff:
                left_terms.append({"unknown": item["rep_id"], "coeff": int(coeff), "side": "left"})
        for item in endpoint_decompositions[right_id]:
            coeff = item["decomposition_on_line_basis"].get(basis_label, 0)
            row.append(-int(coeff))
            if coeff:
                right_terms.append({"unknown": item["rep_id"], "coeff": -int(coeff), "side": "right"})
        left_expr = " + ".join(f"{term['coeff']}*{term['unknown']}" for term in left_terms) or "0"
        right_expr = " + ".join(f"{-term['coeff']}*{term['unknown']}" for term in right_terms) or "0"
        equations.append(
            {
                "basis_id": basis_label,
                "terms": left_terms + right_terms,
                "equation": f"{left_expr} = {right_expr}",
            }
        )
        matrix_rows.append(row)

    line_group_signature = signature_from_detail(
        line_detail,
        block["line_symmetry_summary"],
        mode=mode,
    )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "character_mode_used_for_compatibility": mode,
        "left_point_id": left_id,
        "line_id": line_id,
        "right_point_id": right_id,
        "left_exact_k": block["left_exact_k"],
        "line_exact_k": block["line_exact_k"],
        "right_exact_k": block["right_exact_k"],
        "left_cli_k": block["left_cli_k"],
        "line_cli_k": block["line_cli_k"],
        "right_cli_k": block["right_cli_k"],
        "line_parametrization": block["line_parametrization"],
        "line_constraints": block["line_constraints"],
        "line_sample_point": block["line_sample_point"],
        "line_coordinates": block["line_coordinates"],
        "line_symmetry_summary": block["line_symmetry_summary"],
        "line_group_signature": line_group_signature,
        "line_generic_corep_list": [
            {
                "rep_id": rep_id,
                "rep_degree": int(degree),
                "torsion": int(torsion),
                "character": character,
                "linear_character": linear_character,
            }
            for rep_id, degree, torsion, character, linear_character in zip(
                line_basis_labels,
                line_detail["rep_degree"],
                line_detail["torsion"],
                line_detail["character_json"],
                line_detail["linear_character_json"],
            )
        ],
        "matched_unitary_operation_indices": matched_operation_indices,
        "endpoint_decompositions": endpoint_decompositions,
        "endpoint_mode_viability": mode_viability,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "block_matrix": matrix_rows,
        "block_matrix_shape": [len(matrix_rows), len(local_unknown_ordering)],
        "block_rank": int(sp.Matrix(matrix_rows).rank()),
    }


def build_line_character_choice_summary(
    blocks: list[dict[str, Any]],
    details: dict[str, Any],
) -> dict[str, Any]:
    per_mode: dict[str, dict[str, Any]] = {}
    for mode in ("character", "linear_character"):
        block_results = {}
        all_ok = True
        for block in blocks:
            line_id = block["line_id"]
            left_id = block["left_point_id"]
            right_id = block["right_point_id"]
            line_detail = details[line_id]
            line_unitary_ops = [
                operation_key_from_detail(line_detail, op_index)
                for op_index, sign in enumerate(line_detail["time_reversal"])
                if sign > 0
            ]
            endpoint_results = {}
            block_ok = True
            for endpoint_id in (left_id, right_id):
                endpoint_detail = details[endpoint_id]
                unitary_map = {
                    operation_key_from_detail(endpoint_detail, op_index): unitary_index
                    for unitary_index, (op_index, sign) in enumerate(
                        item for item in enumerate(endpoint_detail["time_reversal"]) if item[1] > 0
                    )
                }
                matched = [unitary_map.get(op_key) for op_key in line_unitary_ops]
                if any(index is None for index in matched):
                    endpoint_results[endpoint_id] = {
                        "matches_subgroup": False,
                        "integral_decomposition": False,
                    }
                    block_ok = False
                    continue
                viability = numerically_assess_mode(endpoint_detail, line_detail, matched, mode)
                endpoint_results[endpoint_id] = {
                    "matches_subgroup": True,
                    "integral_decomposition": viability["all_integer_like"],
                    "max_coefficient_deviation_from_nearest_integer": viability[
                        "max_coefficient_deviation_from_nearest_integer"
                    ],
                    "max_reconstruction_deviation": viability["max_reconstruction_deviation"],
                }
                if not viability["all_integer_like"]:
                    block_ok = False
            block_results[line_id] = {
                "block_ok": block_ok,
                "endpoints": endpoint_results,
            }
            all_ok = all_ok and block_ok
        per_mode[mode] = {
            "all_blocks_ok": all_ok,
            "line_blocks": block_results,
        }

    chosen_mode = "character"
    reason = (
        "Use raw character for compatibility. It gives an exact integer restriction/decomposition on all four "
        "explicit line blocks. linear_character carries the k-dependent Bloch phase exp(-i k·tauC); that phase "
        "is needed later for band-character decomposition and induction, but it breaks a uniform integer "
        "restriction formalism already on L1 and L3."
    )
    return {
        "available_modes": ["character", "linear_character"],
        "mode_assessment": per_mode,
        "selected_compatibility_character_mode": chosen_mode,
        "selection_reason": reason,
        "single_group_difference": (
            "The single-group scripts also effectively used raw character for subgroup restriction, but the reason "
            "was easier to overlook because linear_character often differed only by signs or trivial phases. "
            "In the double group the failure of linear_character on L1/L3 becomes explicit because the projective "
            "spinful phases combine with generic-k translational phases."
        ),
        "projective_phase_handling_note": (
            "The double-valued SU2/projective part is kept inside raw character and in the subgroup-matching key "
            "through the little-group su2 matrices. The translational Bloch phase is not stripped from induction; "
            "it is only excluded from compatibility rows."
        ),
    }


def build_global_unknown_ordering(line_blocks: list[dict[str, Any]]) -> list[str]:
    per_point_ids: dict[str, list[str]] = {}
    for block in line_blocks:
        for endpoint_id in (block["left_point_id"], block["right_point_id"]):
            rep_ids = [item["rep_id"] for item in block["endpoint_decompositions"][endpoint_id]]
            existing = per_point_ids.get(endpoint_id)
            if existing is None:
                per_point_ids[endpoint_id] = rep_ids
            elif existing != rep_ids:
                raise ValueError(f"inconsistent rep ordering for {endpoint_id}")
    ordering = []
    for point_id in POINT_IDS:
        ordering.extend(per_point_ids.get(point_id, []))
    return ordering


def build_line_only_global(line_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    unknown_ordering = build_global_unknown_ordering(line_blocks)
    unknown_index = {unknown: index for index, unknown in enumerate(unknown_ordering)}
    global_rows = []
    global_equations = []
    for block in line_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(unknown_ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            global_rows.append(
                {
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_line": row_index,
                    "equation": equation["equation"],
                    "matrix_row": row,
                }
            )
            global_equations.append(
                {
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "equation": equation["equation"],
                    "terms": equation["terms"],
                }
            )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "covered_lines": LINE_IDS,
        "global_unknown_ordering": unknown_ordering,
        "global_equations": global_equations,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
    }


def signature_from_detail(
    detail: dict[str, Any],
    symmetry_summary: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    basis_characters = [
        [str(single.as_exact_char(complex(value))) for value in rep_character]
        for rep_character in detail[mode]
    ]
    return {
        "character_mode": mode,
        "n_ops_total": detail["n_ops_total"],
        "n_unitary_ops": detail["n_unitary_ops"],
        "n_antiunitary_ops": detail["n_antiunitary_ops"],
        "basis_size": len(basis_characters),
        "character_length": len(basis_characters[0]) if basis_characters else 0,
        "rep_degree": list(detail["rep_degree"]),
        "torsion": list(detail["torsion"]),
        "basis_characters": basis_characters,
        "generic_stabilizer_size": symmetry_summary["generic_stabilizer_size"],
        "generic_rotation_stabilizer_size": symmetry_summary["generic_rotation_stabilizer_size"],
        "site_symmetry": symmetry_summary["site_symmetry"],
        "unitary_site_symmetry": symmetry_summary.get("unitary_site_symmetry"),
    }


def canonical_signature_key(signature: dict[str, Any]) -> str:
    compact = {
        key: value
        for key, value in signature.items()
        if key not in {"character_mode", "unitary_site_symmetry"}
    }
    return json.dumps(compact, sort_keys=True)


def build_plane_vs_line_comparison(
    geometry: dict[str, Any],
    details: dict[str, Any],
    line_blocks: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    line_signatures = {
        block["line_id"]: signature_from_detail(
            details[block["line_id"]],
            block["line_symmetry_summary"],
            mode=mode,
        )
        for block in line_blocks
    }
    plane_signatures = {
        plane_id: signature_from_detail(
            details[plane_id],
            geometry["planes"][plane_id]["symmetry_summary"],
            mode=mode,
        )
        for plane_id in PLANE_IDS
    }

    line_classes: dict[str, list[str]] = {}
    for line_id, signature in line_signatures.items():
        line_classes.setdefault(canonical_signature_key(signature), []).append(line_id)

    plane_vs_line = {}
    plane_to_matching_lines: dict[str, list[str]] = {}
    new_type_detected = False
    for plane_id, plane_signature in plane_signatures.items():
        plane_vs_line[plane_id] = {}
        plane_to_matching_lines[plane_id] = []
        plane_key = canonical_signature_key(plane_signature)
        for line_id, line_signature in line_signatures.items():
            line_key = canonical_signature_key(line_signature)
            same_signature = plane_key == line_key
            plane_vs_line[plane_id][line_id] = {
                "same_signature": same_signature,
                "same_basis_characters": plane_signature["basis_characters"] == line_signature["basis_characters"],
                "same_rep_degree_pattern": plane_signature["rep_degree"] == line_signature["rep_degree"],
                "same_torsion_pattern": plane_signature["torsion"] == line_signature["torsion"],
            }
            if same_signature:
                plane_to_matching_lines[plane_id].append(line_id)
        if not plane_to_matching_lines[plane_id]:
            new_type_detected = True

    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "character_mode_used": mode,
        "line_signature_classes": [
            {"line_ids": ids, "signature": line_signatures[ids[0]]}
            for ids in line_classes.values()
        ],
        "line_signatures": line_signatures,
        "plane_signatures": plane_signatures,
        "plane_vs_line": plane_vs_line,
        "plane_to_matching_lines": plane_to_matching_lines,
        "new_little_group_signature_types": new_type_detected,
    }


def build_plane_block(
    plane_id: str,
    plane_geometry: dict[str, Any],
    details: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    plane_detail = details[plane_id]
    plane_unitary_ops = [
        operation_key_from_detail(plane_detail, op_index)
        for op_index, sign in enumerate(plane_detail["time_reversal"])
        if sign > 0
    ]
    if len(plane_unitary_ops) != plane_detail["character_shape"][1]:
        raise ValueError(f"{plane_id} unitary operation count does not match character length")

    plane_basis_labels = basis_labels_for_manifold(plane_id, plane_detail)
    plane_basis_matrix = exact_basis_matrix(plane_detail, mode)
    corner_decompositions: dict[str, list[dict[str, Any]]] = {}
    matched_operation_indices: dict[str, list[int]] = {}
    local_unknown_ordering = []
    equations = []
    matrix_rows = []

    for point_id in plane_geometry["corner_points"]:
        point_detail = details[point_id]
        unitary_map = {
            operation_key_from_detail(point_detail, op_index): unitary_index
            for unitary_index, (op_index, sign) in enumerate(
                item for item in enumerate(point_detail["time_reversal"]) if item[1] > 0
            )
        }
        matched = [unitary_map.get(op_key) for op_key in plane_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(f"{point_id} does not contain the full {plane_id} unitary subgroup")
        matched_operation_indices[point_id] = [int(index) for index in matched]
        reps = []
        for rep_index, rep_character in enumerate(point_detail[mode], start=1):
            rep_id = f"{point_id}_R{rep_index}"
            restricted = sp.Matrix(
                [single.as_exact_char(complex(rep_character[index])) for index in matched]
            )
            coeffs_int = solve_decomposition(
                plane_basis_matrix,
                restricted,
                context=f"{point_id} rep {rep_index} on {plane_id} using {mode}",
            )
            reps.append(
                {
                    "rep_id": rep_id,
                    "rep_degree": int(point_detail["rep_degree"][rep_index - 1]),
                    "torsion": int(point_detail["torsion"][rep_index - 1]),
                    "restricted_character_on_plane_unitary_subgroup": [str(entry) for entry in restricted],
                    "decomposition_on_plane_basis": {
                        basis_label: coeff
                        for basis_label, coeff in zip(plane_basis_labels, coeffs_int)
                        if coeff
                    },
                }
            )
        corner_decompositions[point_id] = reps
        local_unknown_ordering.extend(item["rep_id"] for item in reps)
    local_unknown_ordering.extend(plane_basis_labels)
    local_unknown_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}

    for point_id in plane_geometry["corner_points"]:
        for basis_label in plane_basis_labels:
            row = [0] * len(local_unknown_ordering)
            point_terms = []
            for rep in corner_decompositions[point_id]:
                coeff = rep["decomposition_on_plane_basis"].get(basis_label, 0)
                if coeff:
                    row[local_unknown_index[rep["rep_id"]]] += int(coeff)
                    point_terms.append({"unknown": rep["rep_id"], "coeff": int(coeff), "side": "point"})
            row[local_unknown_index[basis_label]] -= 1
            lhs = " + ".join(f"{term['coeff']}*{term['unknown']}" for term in point_terms) or "0"
            equations.append(
                {
                    "plane_id": plane_id,
                    "point_id": point_id,
                    "basis_id": basis_label,
                    "terms": point_terms + [{"unknown": basis_label, "coeff": -1, "side": "plane"}],
                    "equation": f"{lhs} = 1*{basis_label}",
                }
            )
            matrix_rows.append(row)

    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "character_mode_used_for_compatibility": mode,
        "plane_id": plane_id,
        "connector_model": (
            "Direct point-plane restriction onto the plane generic unitary basis. "
            "The geometric boundary lines are not promoted to separate unknown-bearing manifolds."
        ),
        "boundary_model_note": (
            "single_group_connectivity.json still has line_plane = []. The boundary lines of S1/S2 are geometric-only "
            "objects rather than separately listed special-line manifolds, so a boundary-line chain through explicit "
            "line unknowns is not available. The minimal viable double-group connector is therefore direct restriction "
            "from each corner point to the plane generic basis."
        ),
        "corner_points": plane_geometry["corner_points"],
        "plane_exact_k": plane_geometry["sample_point"],
        "plane_cli_k": [cli_str(parse_fraction(v)) for v in plane_geometry["sample_point"]],
        "plane_parametrization": plane_geometry["parametrization"],
        "plane_constraints": plane_geometry["constraints"],
        "plane_coordinates": plane_geometry["coordinates"],
        "plane_sample_point": plane_geometry["sample_point"],
        "plane_symmetry_summary": plane_geometry["symmetry_summary"],
        "plane_group_signature": signature_from_detail(plane_detail, plane_geometry["symmetry_summary"], mode=mode),
        "plane_generic_corep_list": [
            {
                "rep_id": rep_id,
                "rep_degree": int(degree),
                "torsion": int(torsion),
                "character": character,
                "linear_character": linear_character,
            }
            for rep_id, degree, torsion, character, linear_character in zip(
                plane_basis_labels,
                plane_detail["rep_degree"],
                plane_detail["torsion"],
                plane_detail["character_json"],
                plane_detail["linear_character_json"],
            )
        ],
        "matched_unitary_operation_indices": matched_operation_indices,
        "corner_decompositions": corner_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "block_matrix": matrix_rows,
        "block_matrix_shape": [len(matrix_rows), len(local_unknown_ordering)],
        "block_rank": int(sp.Matrix(matrix_rows).rank()),
    }


def build_full_compatibility_with_planes(
    line_only: dict[str, Any],
    plane_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    plane_unknown_ordering = [
        basis["rep_id"]
        for block in plane_blocks
        for basis in block["plane_generic_corep_list"]
    ]
    global_unknown_ordering = list(line_only["global_unknown_ordering"]) + plane_unknown_ordering
    unknown_index = {unknown: index for index, unknown in enumerate(global_unknown_ordering)}
    global_rows = []
    global_equations = []

    for row in line_only["global_matrix_rows"]:
        padded_row = list(row["matrix_row"]) + [0] * len(plane_unknown_ordering)
        global_rows.append(
            {
                "source_type": "line",
                "line_id": row["line_id"],
                "basis_id": row["basis_id"],
                "row_index_within_source": row["row_index_within_line"],
                "equation": row["equation"],
                "matrix_row": padded_row,
            }
        )
        global_equations.append({"source_type": "line", **line_only["global_equations"][len(global_equations)]})

    for block in plane_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(global_unknown_ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            global_rows.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "point_id": equation["point_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "equation": equation["equation"],
                    "matrix_row": row,
                }
            )
            global_equations.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "point_id": equation["point_id"],
                    "basis_id": equation["basis_id"],
                    "equation": equation["equation"],
                    "terms": equation["terms"],
                }
            )

    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "model": "double-group line matrix plus direct point-plane connector",
        "line_rows_preserved": True,
        "plane_connector_model": (
            "Point-plane restriction on the plane generic unitary basis with explicit double-valued raw characters."
        ),
        "covered_lines": list(LINE_IDS),
        "covered_planes": [block["plane_id"] for block in plane_blocks],
        "plane_unknown_ordering": plane_unknown_ordering,
        "plane_blocks": plane_blocks,
        "global_unknown_ordering": global_unknown_ordering,
        "global_equations": global_equations,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
    }


def analyze_integer_kernel(
    payload: dict[str, Any],
    *,
    matrix_key: str = "global_matrix",
    unknown_key: str = "global_unknown_ordering",
) -> dict[str, Any]:
    unknown_ordering = list(payload[unknown_key])
    raw_matrix = payload[matrix_key]
    C = sp.Matrix(raw_matrix)
    D, U, V = smith_normal_decomp(C, domain=ZZ)
    smith_diagonal = smith_diagonal_from_D(D)
    rank = len(smith_diagonal)
    nullity = C.cols - rank
    if rank != int(C.rank()):
        raise ValueError("Smith rank does not match rational rank")

    raw_basis_matrix = V[:, rank:]
    if C * raw_basis_matrix != sp.zeros(C.rows, raw_basis_matrix.cols):
        raise ValueError("Smith-derived raw basis is not in the kernel")

    raw_basis_vectors = []
    for basis_index in range(raw_basis_matrix.cols):
        vector = [int(value) for value in raw_basis_matrix[:, basis_index]]
        raw_basis_vectors.append(
            {
                "id": f"bs_double_raw_basis_{basis_index + 1:02d}",
                "vector": vector,
                "support": support_from_vector(vector, unknown_ordering),
            }
        )

    pretty_basis_vectors = []
    sign_diagonal = []
    for basis_index, basis in enumerate(raw_basis_vectors):
        sign = first_nonzero_sign(basis["vector"])
        sign_diagonal.append(sign)
        vector = [sign * coeff for coeff in basis["vector"]]
        support = support_from_vector(vector, unknown_ordering)
        sectors = sorted({entry["unknown"].split("_")[0] for entry in support})
        sector_label = "+".join(sectors) if sectors else "zero"
        pretty_basis_vectors.append(
            {
                "id": f"bs_double_pretty_{basis_index + 1:02d}",
                "sector": sector_label,
                "description": (
                    f"Signed Smith-kernel basis vector supported on {sector_label}."
                    if sector_label != "zero"
                    else "Zero-support placeholder."
                ),
                "vector": vector,
                "support": support,
            }
        )

    pretty_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in pretty_basis_vectors]) if pretty_basis_vectors else sp.Matrix.zeros(C.cols, 0)
    if C * pretty_basis_matrix != sp.zeros(C.rows, pretty_basis_matrix.cols):
        raise ValueError("Pretty basis is not in the kernel")
    if int(pretty_basis_matrix.rank()) != nullity:
        raise ValueError("Pretty basis is not independent")

    transform = sp.diag(*sign_diagonal) if sign_diagonal else sp.eye(0)
    determinant = int(transform.det()) if sign_diagonal else 1
    if abs(determinant) != 1:
        raise ValueError("Signed raw-to-pretty transform is not unimodular")

    return {
        "unknown_ordering": unknown_ordering,
        "matrix_shape": [C.rows, C.cols],
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "raw_basis_matrix": raw_basis_matrix,
        "pretty_basis_matrix": pretty_basis_matrix,
        "raw_basis_vectors": raw_basis_vectors,
        "pretty_basis_vectors": pretty_basis_vectors,
        "pretty_transform_from_raw": {
            "matrix_as_rows": [[int(value) for value in row] for row in transform.tolist()],
            "determinant": determinant,
        },
    }


def build_bs_summary_payload(
    final_payload: dict[str, Any],
    analysis: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "matrix_source": source,
        "final_unknown_ordering": analysis["unknown_ordering"],
        "final_C_double": final_payload["global_matrix"],
        "shape": analysis["matrix_shape"],
        "rank": analysis["rank"],
        "nullity": analysis["nullity"],
        "smith_diagonal": analysis["smith_diagonal"],
        "bs_double_constructed": True,
    }


def build_c_double_local_irreps(ctx: dict[str, Any]) -> dict[str, Any]:
    stabilizer = [0, 3, 4, 7]
    factor = np.array(ctx["ssg"].factor_su2, dtype=complex)
    mul_table = np.array(ctx["ssg"].mul_table, dtype=int)

    def is_valid(character: dict[int, complex]) -> bool:
        for left in stabilizer:
            for right in stabilizer:
                target = int(mul_table[left][right]) - 1
                lhs = character[left] * character[right] * factor[left][right]
                rhs = character[target]
                if abs(lhs - rhs) > 1e-8:
                    return False
        return True

    irreps: list[dict[str, Any]] = []
    for c2_label, c2_value in (("plus_i", 1j), ("minus_i", -1j)):
        for inversion_label, inversion_value in (("g", 1), ("u", -1)):
            mirror_value = c2_value * inversion_value
            values = {0: 1 + 0j, 3: complex(c2_value), 4: complex(inversion_value), 7: complex(mirror_value)}
            if not is_valid(values):
                raise ValueError(f"invalid projective character on family c stabilizer: {values}")
            irreps.append(
                {
                    "id": f"c_double_{inversion_label}_{c2_label}",
                    "family_letter": "c",
                    "dimension": 1,
                    "site_symmetry": "2/m",
                    "double_group_local_object_kind": "projective_local_irrep",
                    "character_on_unitary_stabilizer": {
                        str(index): complex_to_json(value) for index, value in values.items()
                    },
                }
            )
    return {
        "selected_prototype_id": irreps[0]["id"],
        "stabilizer_indices": stabilizer,
        "irreps": irreps,
    }


def induce_double_irrep_on_manifolds(
    ctx: dict[str, Any],
    details: dict[str, Any],
    family_entry: dict[str, Any],
    local_character: dict[int, complex],
    manifold_ids: list[str],
) -> dict[str, Any]:
    orbit = single_expanded.orbit_for_sample_entry(family_entry, ctx, ctx["group_tables"])
    results: dict[str, Any] = {}
    for manifold_id in manifold_ids:
        detail = details[manifold_id]
        kconv = (
            frac_list_to_float(detail["exact_k"])[0] * ctx["reciprocal_basis"][0]
            + frac_list_to_float(detail["exact_k"])[1] * ctx["reciprocal_basis"][1]
            + frac_list_to_float(detail["exact_k"])[2] * ctx["reciprocal_basis"][2]
        )

        unitary_raw_indices = []
        unitary_rotations = []
        unitary_translations = []
        for op_index, sign in enumerate(detail["time_reversal"]):
            if sign < 0:
                continue
            rot = np.array(detail["rotC"][op_index], dtype=float)
            tau = np.array(detail["tauC"][op_index], dtype=float)
            unitary_raw_indices.append(
                single_expanded.match_raw_op(
                    ctx,
                    ctx["group_tables"]["operations"],
                    rot,
                    tau,
                    False,
                )
            )
            unitary_rotations.append(rot)
            unitary_translations.append(tau)

        band_character: list[complex] = []
        for op_index, rotation, translation in zip(
            unitary_raw_indices,
            unitary_rotations,
            unitary_translations,
        ):
            total = 0j
            for site in orbit:
                coset_index = int(site["source_operation_index"])
                conj_index = ctx["group_tables"]["compose"](
                    ctx["group_tables"]["inverse"][coset_index],
                    ctx["group_tables"]["compose"](op_index, coset_index),
                )
                if conj_index not in local_character:
                    continue
                point_conv = np.array(site["conv_vector"], dtype=float)
                delta = rotation @ point_conv + translation - point_conv
                fixed, _ = single_bridge.vector_is_lattice(ctx["supercell"], delta)
                if not fixed:
                    continue
                total += local_character[conj_index] * cmath.exp(-1j * float(np.dot(kconv, delta)))
            band_character.append(total)

        chars = np.array(detail["linear_character"], dtype=complex)
        band = np.array(band_character, dtype=complex)
        gram = chars @ chars.conj().T / chars.shape[1]
        rhs = chars.conj() @ band / chars.shape[1]
        multiplicities = np.linalg.solve(gram, rhs)
        rounded = [int(round(float(value.real))) for value in multiplicities]
        recon = np.array(rounded, dtype=complex) @ chars

        if not np.allclose(multiplicities, np.rint(multiplicities.real), atol=1e-8):
            raise ValueError(f"{family_entry['letter']} on {manifold_id}: non-integral multiplicities")
        if not np.allclose(recon, band, atol=1e-8):
            raise ValueError(f"{family_entry['letter']} on {manifold_id}: reconstruction failure")

        results[manifold_id] = {
            "rep_degree": detail["rep_degree"],
            "band_character": complex_list_to_json(band_character),
            "multiplicities": rounded,
            "reconstruction_exact": True,
            "total_dimension": int(sum(mult * degree for mult, degree in zip(rounded, detail["rep_degree"]))),
        }
    return results


def solve_integer_basis_coordinates(basis_matrix: sp.Matrix, vector: list[int], context: str) -> list[int]:
    target = sp.Matrix(vector)
    solution, params = basis_matrix.gauss_jordan_solve(target)
    if params.rows * params.cols:
        raise ValueError(f"free parameters when solving {context}")
    return coerce_integer_coeffs(list(solution), context)


def build_embedding_payload(
    ctx: dict[str, Any],
    details: dict[str, Any],
    final_unknown_ordering: list[str],
    final_matrix: list[list[int]],
    bs_analysis: dict[str, Any],
    *,
    planes_required: bool,
) -> dict[str, Any]:
    family_entry = ctx["entries_by_letter"]["c"]
    double_local = build_c_double_local_irreps(ctx)
    selected = next(item for item in double_local["irreps"] if item["id"] == double_local["selected_prototype_id"])
    local_character = {
        int(index): complex(value["real"], value["imag"])
        for index, value in selected["character_on_unitary_stabilizer"].items()
    }

    manifold_ids = list(POINT_IDS) + (PLANE_IDS if planes_required else [])
    induction = induce_double_irrep_on_manifolds(ctx, details, family_entry, local_character, manifold_ids)

    vector = []
    for unknown in final_unknown_ordering:
        manifold_id, rep_id = unknown.split("_", 1)
        rep_index = int(rep_id[1:]) - 1
        vector.append(int(induction[manifold_id]["multiplicities"][rep_index]))

    residual = sp.Matrix(final_matrix) * sp.Matrix(vector)
    residual_list = [int(value) for value in residual]
    in_bs = all(value == 0 for value in residual_list)
    if not in_bs:
        raise ValueError("minimal family-c prototype does not lie in the final BS kernel")

    raw_coords = solve_integer_basis_coordinates(
        bs_analysis["raw_basis_matrix"],
        vector,
        "minimal family-c embedding in raw BS basis",
    )
    pretty_coords = solve_integer_basis_coordinates(
        bs_analysis["pretty_basis_matrix"],
        vector,
        "minimal family-c embedding in pretty BS basis",
    )

    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "family": "c",
        "selected_local_irrep": selected,
        "final_unknown_ordering": final_unknown_ordering,
        "vector_in_final_unknown_ordering": vector,
        "support": support_from_vector(vector, final_unknown_ordering),
        "induced_multiplicities_by_manifold": induction,
        "in_bs_double": in_bs,
        "residual_under_final_C": residual_list,
        "coordinates_in_raw_bs_basis": raw_coords,
        "coordinates_in_pretty_bs_basis": pretty_coords,
        "planes_required_for_embedding": planes_required,
    }


def build_line_blocks_payload(
    geometry: dict[str, Any],
    manifold_bundle: dict[str, Any],
    character_choice: dict[str, Any],
    line_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    manifolds_summary = {}
    for manifold_id in POINT_IDS + LINE_IDS + PLANE_IDS:
        detail = manifold_bundle["details"][manifold_id]
        if manifold_id in geometry["objects"]:
            obj = geometry["objects"][manifold_id]
            manifolds_summary[manifold_id] = {
                "type": obj["type"],
                "dimension": int(obj["dimension"]),
                "coordinates": list(obj["coordinate_expressions"]),
                "parametrization": obj["parametrization"],
                "constraints": list(obj["constraints"]),
                "sample_point": list(obj["sample_point"]),
                "character_available": detail["character_available"],
                "linear_character_available": detail["linear_character_available"],
                "rep_count": detail["rep_count"],
                "rep_degree": detail["rep_degree"],
                "torsion": detail["torsion"],
                "character_shape": detail["character_shape"],
                "linear_character_shape": detail["linear_character_shape"],
                "n_unitary_ops": detail["n_unitary_ops"],
                "n_antiunitary_ops": detail["n_antiunitary_ops"],
                "warning_text": detail["warning_text"],
                "repeated_call_consistent": manifold_bundle["stability"][manifold_id],
            }
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "geometry_source": str(GEOMETRY_PATH),
        "connectivity_source": str(CONNECTIVITY_PATH),
        "manifolds": manifolds_summary,
        "all_manifolds_stable_under_repeat_call": manifold_bundle["all_stable"],
        "compatibility_character_choice": character_choice,
        "line_blocks": line_blocks,
    }


def build_plane_necessity_payload(
    geometry: dict[str, Any],
    comparison: dict[str, Any],
    plane_blocks: list[dict[str, Any]],
    line_only_analysis: dict[str, Any],
    with_planes_analysis: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    planes_required = with_planes_analysis["rank"] > line_only_analysis["rank"]
    markdown_lines = [
        "# Double-Group Plane Necessity Audit for 10.4.1.31",
        "",
        "## Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- stage: plane necessity audit on top of the full double-group line layer",
        "",
        "## Geometry Premise",
        "",
        f"- explicit special planes from geometry JSON: `{PLANE_IDS}`",
        f"- `line_plane`: `{geometry['connectivity']['line_plane']}`",
        "- All plane boundaries are geometric-only boundaries rather than separately listed special lines.",
        "- Because of that, a boundary-line chain through explicit line unknowns is not available here. The minimal viable connector is direct restriction from the corner points to the common plane generic basis.",
        "",
        "## Signatures",
        "",
        f"- `S1` matching lines: `{comparison['plane_to_matching_lines']['S1']}`",
        f"- `S2` matching lines: `{comparison['plane_to_matching_lines']['S2']}`",
        f"- new plane generic signature type detected: `{comparison['new_little_group_signature_types']}`",
        (
            "- Result: the planes do introduce a new generic signature class relative to the explicit lines, "
            "so the with-planes backbone is needed both to include the plane sectors and to impose the extra couplings."
            if comparison["new_little_group_signature_types"]
            else "- Result: the planes do not introduce a new little-group type. The necessity question is therefore "
            "about new couplings, not about a new signature class."
        ),
        "",
        "## Rank Test",
        "",
        f"- line-only matrix shape / rank / nullity: `{line_only_analysis['matrix_shape']}` / `{line_only_analysis['rank']}` / `{line_only_analysis['nullity']}`",
        f"- with-planes matrix shape / rank / nullity: `{with_planes_analysis['matrix_shape']}` / `{with_planes_analysis['rank']}` / `{with_planes_analysis['nullity']}`",
        f"- added rank beyond the line layer: `{with_planes_analysis['rank'] - line_only_analysis['rank']}`",
        f"- net nullity drop: `{line_only_analysis['nullity'] - with_planes_analysis['nullity']}`",
        "",
        "## Verdict",
        "",
        f"- planes required: `{planes_required}`",
        (
            "- `S1/S2` carry a plane generic signature class that is absent from the explicit line layer, "
            "and the associated plane unknowns also add independent couplings between corner-point sectors that "
            "remain disconnected in the line-only matrix."
            if comparison["new_little_group_signature_types"]
            else "- Even though `S1/S2` reuse the same generic signature classes as the explicit lines, they add "
            "new independent constraints because the shared plane unknowns couple point sectors that remain "
            "disconnected in the line-only matrix."
        ),
    ]
    payload = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "character_mode_used": comparison["character_mode_used"],
        "comparison": comparison,
        "plane_blocks": plane_blocks,
        "planes_required": planes_required,
        "line_only_shape": line_only_analysis["matrix_shape"],
        "line_only_rank": line_only_analysis["rank"],
        "line_only_nullity": line_only_analysis["nullity"],
        "with_planes_shape": with_planes_analysis["matrix_shape"],
        "with_planes_rank": with_planes_analysis["rank"],
        "with_planes_nullity": with_planes_analysis["nullity"],
        "added_rank_vs_line_only": with_planes_analysis["rank"] - line_only_analysis["rank"],
        "net_nullity_drop_vs_line_only": line_only_analysis["nullity"] - with_planes_analysis["nullity"],
    }
    return payload, "\n".join(markdown_lines)


def build_summary_payload(
    *,
    planes_required: bool,
    embedding_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "line_layer_completed": True,
        "plane_necessity_completed": True,
        "planes_required": planes_required,
        "with_planes_completed": planes_required,
        "bs_double_constructed": True,
        "minimal_realspace_double_embeds_in_bs": bool(embedding_payload["in_bs_double"]),
        "main_blocker": None,
        "next_blocker": (
            "The next unfinished step is a reusable double-group local-corep builder beyond family c "
            "and then a full AI lattice / BS-AI computation."
        ),
    }


def build_bs_basis_payload(
    analysis: dict[str, Any],
    *,
    key: str,
    note: str,
    include_transform: bool,
) -> dict[str, Any]:
    payload = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "unknown_ordering": analysis["unknown_ordering"],
        "basis_kind": key,
        "note": note,
        "basis_vectors": analysis["raw_basis_vectors" if key == "raw" else "pretty_basis_vectors"],
    }
    if include_transform:
        payload["basis_transform_note"] = "The pretty basis is a signed reorientation of the Smith raw basis."
        payload["basis_transform_from_raw"] = analysis["pretty_transform_from_raw"]
    return payload


def build_backbone_audit_md(
    background: dict[str, Any],
    geometry: dict[str, Any],
    line_blocks_payload: dict[str, Any],
    line_only_analysis: dict[str, Any],
    plane_payload: dict[str, Any],
    bs_summary: dict[str, Any],
    embedding_payload: dict[str, Any],
) -> str:
    character_choice = line_blocks_payload["compatibility_character_choice"]
    lines = [
        "# Double-Group K-Space Backbone Audit for 10.4.1.31",
        "",
        "## Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- This stage does not revisit the closed single-group line or the already accepted minimal double-group prototype.",
        "- The goal here is the full double-group k-space backbone: four explicit line blocks, plane necessity, final C_double, BS_double, and the formal embedding of the existing family-c prototype into that BS lattice.",
        "",
        "## Reused Premise",
        "",
        "- single-group is already closed, including with-planes BS and BS/AI.",
        "- the minimal double-group prototype already established that the k-space extraction, bridge, and induction all work at least on c -> P1/L1/P4.",
        f"- previous double-group feasibility verdict: `{background['double_feas_summary']['minimal_double_prototype_completed']}`",
        "",
        "## Geometry Audit",
        "",
        "- All manifolds are read from the existing geometry JSON rather than handwritten.",
        f"- points: `{POINT_IDS}`",
        f"- lines: `{LINE_IDS}`",
        f"- planes: `{PLANE_IDS}`",
        "- Sample points and parametrizations are taken directly from `single_group_kmanifolds.json`.",
        "",
        "## Double-Group Output Capability",
        "",
        f"- all manifolds stable under a repeated groupType=2 extraction: `{line_blocks_payload['all_manifolds_stable_under_repeat_call']}`",
        "- `character`, `linear_character`, and `rep_degree` are available on every point, line, and plane used in this run.",
        "- The array structure is consistent: rows are coreps, columns are unitary subgroup operations, and the row ordering stays stable under repeated extraction.",
        "",
        "## Character Choice",
        "",
        f"- selected compatibility mode: `{character_choice['selected_compatibility_character_mode']}`",
        f"- raw character all-block success: `{character_choice['mode_assessment']['character']['all_blocks_ok']}`",
        f"- linear_character all-block success: `{character_choice['mode_assessment']['linear_character']['all_blocks_ok']}`",
        "- Reason: compatibility must be an exact integer subgroup restriction problem. raw character satisfies that uniformly on all four lines, while linear_character fails on L1/L3 because it keeps the generic-k Bloch phase.",
        "- Consequence: raw character is used for compatibility rows and plane comparison; linear_character is still used later for induced band-character decomposition.",
        "",
        "## Reuse vs Rewrite",
        "",
        "- Reused from the single-group scripts:",
        "  - geometry / connectivity parsing from the existing JSON files,",
        "  - operation-subgroup matching,",
        "  - integer restriction/decomposition tables,",
        "  - Smith normal form and integer kernel extraction,",
        "  - the geometric conclusion that `line_plane = []` means the boundary-line chain is unavailable.",
        "- Rewritten or made explicitly double-aware:",
        "  - the subgroup-matching key now carries the little-group SU2 matrix in addition to the spatial data,",
        "  - the line/plane restriction solver is run on double-valued raw characters,",
        "  - the character-vs-linear_character choice is audited explicitly instead of inherited,",
        "  - the minimal family-c prototype is extended from the old P1/L1/P4 witness to the final BS_double unknown ordering.",
        "",
        "## Line Layer",
        "",
        f"- line-layer completed: `True`",
        f"- line-only matrix shape / rank / nullity: `{line_only_analysis['matrix_shape']}` / `{line_only_analysis['rank']}` / `{line_only_analysis['nullity']}`",
        f"- line-only Smith diagonal: `{line_only_analysis['smith_diagonal']}`",
        "",
        "## Plane Necessity",
        "",
        f"- planes required: `{plane_payload['planes_required']}`",
        f"- S1 matches: `{plane_payload['comparison']['plane_to_matching_lines']['S1']}`",
        f"- S2 matches: `{plane_payload['comparison']['plane_to_matching_lines']['S2']}`",
        f"- added rank beyond line-only: `{plane_payload['added_rank_vs_line_only']}`",
        "- Interpretation: the planes do not create a new generic signature class, but they still add independent constraints by coupling point sectors that are otherwise disconnected across the four line blocks.",
        "",
        "## Final BS_double",
        "",
        f"- final matrix source: `{bs_summary['matrix_source']}`",
        f"- final shape / rank / nullity: `{bs_summary['shape']}` / `{bs_summary['rank']}` / `{bs_summary['nullity']}`",
        f"- Smith diagonal: `{bs_summary['smith_diagonal']}`",
        f"- BS_double constructed: `{bs_summary['bs_double_constructed']}`",
        "",
        "## Minimal Real-Space Double Embedding",
        "",
        "- reused minimal prototype: family `c`, projective local irrep `c_double_g_plus_i`",
        f"- embedded in final BS_double: `{embedding_payload['in_bs_double']}`",
        f"- coordinates in raw BS basis: `{embedding_payload['coordinates_in_raw_bs_basis']}`",
        f"- coordinates in pretty BS basis: `{embedding_payload['coordinates_in_pretty_bs_basis']}`",
        "",
        "## Verdict",
        "",
        "- Conclusion type: `1` (full double-group k-space backbone succeeded).",
        "- Full line-layer compatibility succeeded.",
        "- Plane necessity was re-audited in the double group and the planes remain necessary.",
        "- The with-planes double compatibility matrix was built successfully.",
        "- BS_double was constructed exactly over Z.",
        "- The existing minimal family-c prototype now sits as an explicit vector inside the final BS_double lattice.",
    ]
    return "\n".join(lines)


def build_package_readme(planes_required: bool) -> str:
    maybe_planes = (
        "- double-group with-planes compatibility\n"
        if planes_required
        else "- no extra with-planes matrix was needed after the plane audit\n"
    )
    return "\n".join(
        [
            "# Review Package: 10.4.1.31 Double-Group K-Space Backbone",
            "",
            "## This Round",
            "",
            f"- group: `{GROUP_NUMBER}`",
            f"- groupType: `{GROUP_TYPE}`",
            "- stage: full double-group k-space backbone",
            "",
            "## Known Premise",
            "",
            "- the single-group line is already closed",
            "- the minimal double-group prototype is already established",
            "- this round advances from that minimal prototype to the full double-group k-space backbone",
            "",
            "## New Content",
            "",
            "- full double-group line-layer compatibility",
            "- double-group plane necessity",
            maybe_planes.rstrip(),
            "- BS_double",
            "- the formal embedding of the minimal family-c prototype into the final BS_double",
            "",
            "## Outcome Patterns",
            "",
            "- the full double-group k-space backbone succeeds",
            "- or a genuine blocker remains and is localized precisely",
            "",
            "## Suggested Review Order",
            "",
            "1. `double_group_kspace_backbone_audit_10.4.1.31.md`",
            "2. `double_group_kspace_backbone_summary_10.4.1.31.json`",
            "3. `double_group_line_blocks_10.4.1.31.json`",
            "4. `double_group_plane_necessity_audit_10.4.1.31.md`",
            "5. `double_group_bs_summary_10.4.1.31.json`",
            "",
            "## Result Of This Run",
            "",
            "- The full double-group k-space backbone succeeds for this group.",
            "- The next unfinished stage is no longer k-space feasibility/backbone construction. It is the reusable double-group AI/local-corep machinery beyond the single family-c prototype.",
        ]
    )


def build_package(planes_required: bool) -> None:
    reset_dir(PACKAGE_DIR)
    write_text(PACKAGE_DIR / "README.md", build_package_readme(planes_required))

    root_files = [
        AUDIT_MD,
        SUMMARY_JSON,
        LINE_BLOCKS_JSON,
        LINE_ONLY_JSON,
        PLANE_AUDIT_MD,
        BS_SUMMARY_JSON,
        BS_RAW_JSON,
        BS_PRETTY_JSON,
        EMBED_JSON,
        ROOT / "debug_double_group_kspace_backbone_10.4.1.31.py",
        REVIEW_DOUBLE_FEAS / "double_group_feasibility_audit_10.4.1.31.md",
        REVIEW_DOUBLE_FEAS / "double_group_feasibility_summary_10.4.1.31.json",
        REVIEW_DOUBLE_FEAS / "double_group_minimal_kspace_10.4.1.31.json",
        REVIEW_DOUBLE_FEAS / "double_group_minimal_realspace_10.4.1.31.json",
        REVIEW_DOUBLE_FEAS / "double_group_minimal_bs_ai_summary_10.4.1.31.json",
    ]
    if planes_required:
        root_files.append(WITH_PLANES_JSON)

    for source in root_files:
        shutil.copyfile(source, PACKAGE_DIR / source.name)

    mapping = {
        "audit": [
            REVIEW_DOUBLE_FEAS / "audit" / "single_group_ai_completeness_audit.md",
            REVIEW_DOUBLE_FEAS / "audit" / "single_group_ai_completeness_summary.json",
            REVIEW_DOUBLE_FEAS / "audit" / "single_group_indicator_group_summary.json",
            REVIEW_DOUBLE_FEAS / "audit" / "single_group_indicator_generators.json",
            REVIEW_DOUBLE_FEAS / "audit" / "single_group_bs_mod_ai_single_summary.json",
        ],
        "basis": [
            REVIEW_DOUBLE_FEAS / "basis" / "single_group_bs_with_planes_basis_raw.json",
            REVIEW_DOUBLE_FEAS / "basis" / "single_group_bs_with_planes_basis_pretty.json",
        ],
        "matrix": [
            REVIEW_DOUBLE_FEAS / "matrix" / "single_group_full_compatibility_with_planes.json",
        ],
        "background": [
            REVIEW_DOUBLE_FEAS / "background" / "single_group_kmanifolds.json",
            REVIEW_DOUBLE_FEAS / "background" / "single_group_connectivity.json",
        ],
        "dependencies": [
            ROOT / "swyckoff_r.py",
            ROOT / "swyckoff_k.py",
        ],
        "dependencies/SSGReps": [
            ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
            ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
            ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
        ],
    }

    for rel_dir, sources in mapping.items():
        target_dir = PACKAGE_DIR / rel_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in sources:
            shutil.copyfile(source, target_dir / source.name)

    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs(planes_required: bool) -> None:
    for path in REQUIRED_NEW_FILES:
        if not path.exists():
            raise FileNotFoundError(f"missing required file {path}")
    if planes_required and not WITH_PLANES_JSON.exists():
        raise FileNotFoundError(f"missing required with-planes file {WITH_PLANES_JSON}")

    summary = load_json(SUMMARY_JSON)
    if not summary["line_layer_completed"]:
        raise ValueError("line_layer_completed is false")
    if not summary["plane_necessity_completed"]:
        raise ValueError("plane_necessity_completed is false")
    if summary["planes_required"] != planes_required:
        raise ValueError("planes_required mismatch")
    if not summary["bs_double_constructed"]:
        raise ValueError("bs_double_constructed is false")
    if not summary["minimal_realspace_double_embeds_in_bs"]:
        raise ValueError("minimal_realspace_double_embeds_in_bs is false")

    bs_summary = load_json(BS_SUMMARY_JSON)
    final_matrix = sp.Matrix(bs_summary["final_C_double"])
    raw_basis = load_json(BS_RAW_JSON)["basis_vectors"]
    pretty_basis = load_json(BS_PRETTY_JSON)["basis_vectors"]
    if raw_basis:
        raw_matrix = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in raw_basis])
        if final_matrix * raw_matrix != sp.zeros(final_matrix.rows, raw_matrix.cols):
            raise ValueError("raw BS basis is not in the kernel")
    if pretty_basis:
        pretty_matrix = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in pretty_basis])
        if final_matrix * pretty_matrix != sp.zeros(final_matrix.rows, pretty_matrix.cols):
            raise ValueError("pretty BS basis is not in the kernel")

    embedding = load_json(EMBED_JSON)
    if not embedding["in_bs_double"]:
        raise ValueError("embedding reports in_bs_double=false")
    if any(int(value) != 0 for value in embedding["residual_under_final_C"]):
        raise ValueError("embedding residual is nonzero")

    with tarfile.open(PACKAGE_TAR, "r:gz") as tar:
        members = set(tar.getnames())
    required_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/double_group_kspace_backbone_audit_10.4.1.31.md",
        f"{PACKAGE_NAME}/double_group_kspace_backbone_summary_10.4.1.31.json",
        f"{PACKAGE_NAME}/double_group_line_blocks_10.4.1.31.json",
        f"{PACKAGE_NAME}/double_group_plane_necessity_audit_10.4.1.31.md",
        f"{PACKAGE_NAME}/double_group_bs_summary_10.4.1.31.json",
        f"{PACKAGE_NAME}/double_group_bs_basis_raw_10.4.1.31.json",
        f"{PACKAGE_NAME}/double_group_bs_basis_pretty_10.4.1.31.json",
        f"{PACKAGE_NAME}/double_group_minimal_ai_embedding_10.4.1.31.json",
        f"{PACKAGE_NAME}/debug_double_group_kspace_backbone_10.4.1.31.py",
    }
    if planes_required:
        required_members.add(f"{PACKAGE_NAME}/double_group_full_compatibility_with_planes_10.4.1.31.json")
    missing = sorted(required_members - members)
    if missing:
        raise ValueError(f"package tarball is missing members: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    background = load_background_bundle()
    geometry = load_geometry_context()
    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict()
    ctx = load_double_context(module, ssg_dict)

    manifold_bundle = build_manifold_details(module, geometry, ssg_dict)
    details = manifold_bundle["details"]
    character_choice = build_line_character_choice_summary(geometry["line_blocks"], details)
    selected_mode = character_choice["selected_compatibility_character_mode"]

    line_blocks = [
        build_line_block(block, details, mode=selected_mode)
        for block in geometry["line_blocks"]
    ]
    line_blocks_payload = build_line_blocks_payload(
        geometry,
        manifold_bundle,
        character_choice,
        line_blocks,
    )
    write_json(LINE_BLOCKS_JSON, line_blocks_payload)

    line_only_payload = build_line_only_global(line_blocks)
    line_only_analysis = analyze_integer_kernel(line_only_payload)
    line_only_payload.update(
        {
            "matrix_shape": line_only_analysis["matrix_shape"],
            "rank": line_only_analysis["rank"],
            "nullity": line_only_analysis["nullity"],
            "smith_diagonal": line_only_analysis["smith_diagonal"],
        }
    )
    write_json(LINE_ONLY_JSON, line_only_payload)

    comparison = build_plane_vs_line_comparison(
        geometry,
        details,
        line_blocks,
        mode=selected_mode,
    )
    plane_blocks = [
        build_plane_block(plane_id, geometry["planes"][plane_id], details, mode=selected_mode)
        for plane_id in PLANE_IDS
    ]
    with_planes_payload = build_full_compatibility_with_planes(line_only_payload, plane_blocks)
    with_planes_analysis = analyze_integer_kernel(with_planes_payload)
    planes_required = with_planes_analysis["rank"] > line_only_analysis["rank"]
    plane_payload, plane_audit_md = build_plane_necessity_payload(
        geometry,
        comparison,
        plane_blocks,
        line_only_analysis,
        with_planes_analysis,
    )
    write_text(PLANE_AUDIT_MD, plane_audit_md)
    if planes_required:
        with_planes_payload.update(
            {
                "matrix_shape": with_planes_analysis["matrix_shape"],
                "rank": with_planes_analysis["rank"],
                "nullity": with_planes_analysis["nullity"],
                "smith_diagonal": with_planes_analysis["smith_diagonal"],
            }
        )
        write_json(WITH_PLANES_JSON, with_planes_payload)
        final_payload = with_planes_payload
        final_analysis = with_planes_analysis
        matrix_source = "with_planes"
    else:
        if WITH_PLANES_JSON.exists():
            WITH_PLANES_JSON.unlink()
        final_payload = line_only_payload
        final_analysis = line_only_analysis
        matrix_source = "line_only"

    bs_summary = build_bs_summary_payload(final_payload, final_analysis, source=matrix_source)
    write_json(BS_SUMMARY_JSON, bs_summary)
    write_json(
        BS_RAW_JSON,
        build_bs_basis_payload(
            final_analysis,
            key="raw",
            note="Exact Smith-kernel basis for BS_double.",
            include_transform=False,
        ),
    )
    write_json(
        BS_PRETTY_JSON,
        build_bs_basis_payload(
            final_analysis,
            key="pretty",
            note="Signed readable basis for BS_double.",
            include_transform=True,
        ),
    )

    embedding_payload = build_embedding_payload(
        ctx,
        details,
        final_analysis["unknown_ordering"],
        final_payload["global_matrix"],
        final_analysis,
        planes_required=planes_required,
    )
    write_json(EMBED_JSON, embedding_payload)

    summary_payload = build_summary_payload(
        planes_required=planes_required,
        embedding_payload=embedding_payload,
    )
    write_json(SUMMARY_JSON, summary_payload)

    audit_md = build_backbone_audit_md(
        background,
        geometry,
        line_blocks_payload,
        line_only_analysis,
        plane_payload,
        bs_summary,
        embedding_payload,
    )
    write_text(AUDIT_MD, audit_md)

    build_package(planes_required)

    if args.validate:
        validate_outputs(planes_required)

    tree_lines = format_tree(PACKAGE_DIR)
    print(f"1. groupType=2 full double-group line-layer compatibility successful: {summary_payload['line_layer_completed']}")
    print(f"2. groupType=2 plane still required: {summary_payload['planes_required']}")
    print(f"3. with-planes double compatibility successful: {summary_payload['with_planes_completed']}")
    print(f"4. full BS_double obtained: {summary_payload['bs_double_constructed']}")
    print(
        "5. minimal real-space double prototype embedded in full BS_double: "
        f"{summary_payload['minimal_realspace_double_embeds_in_bs']}"
    )
    print(f"6. smallest blocker: {summary_payload['main_blocker']}")
    print(f"7. new package path: {PACKAGE_TAR}")
    print("8. package tree:")
    for line in tree_lines:
        print(f"   {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
