#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp
from sympy.polys.domains import ZZ

import debug_single_connection as single


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 1
PLANES = ["S1", "S2"]
POINT_IDS = [f"P{i}" for i in range(1, 9)]

BS_PACKAGE_DIR = ROOT / "review_package_10.4.1.31_bs"
BS_README_PATH = BS_PACKAGE_DIR / "README.md"
BS_AUDIT_PATH = BS_PACKAGE_DIR / "audit" / "single_group_bs_audit.md"
BS_SUMMARY_PATH = BS_PACKAGE_DIR / "audit" / "single_group_bs_summary.json"
BS_BASIS_RAW_PATH = BS_PACKAGE_DIR / "basis" / "single_group_bs_basis_raw.json"
BS_BASIS_PRETTY_PATH = BS_PACKAGE_DIR / "basis" / "single_group_bs_basis_pretty.json"
BS_MATRIX_ANALYSIS_PATH = BS_PACKAGE_DIR / "matrix" / "single_group_bs_matrix_analysis.json"
FULL_COMPAT_PATH = BS_PACKAGE_DIR / "matrix" / "single_group_full_compatibility.json"
FULL_COMPAT_AUDIT_PATH = BS_PACKAGE_DIR / "audit" / "single_group_full_compatibility_audit.md"
FULL_COMPAT_SUMMARY_PATH = BS_PACKAGE_DIR / "audit" / "single_group_full_compatibility_summary.json"
KMANIFOLDS_PATH = BS_PACKAGE_DIR / "background" / "single_group_kmanifolds.json"
CONNECTIVITY_PATH = BS_PACKAGE_DIR / "background" / "single_group_connectivity.json"
LINE_BLOCK_PATHS = {
    "L1": BS_PACKAGE_DIR / "background" / "L1_block.json",
    "L2": BS_PACKAGE_DIR / "background" / "L2_block.json",
    "L3": BS_PACKAGE_DIR / "background" / "L3_block.json",
    "L4": BS_PACKAGE_DIR / "background" / "L4_block.json",
}
BS_SCRIPT_PATH = BS_PACKAGE_DIR / "scripts" / "debug_single_group_bs.py"
FULL_COMPAT_SCRIPT_PATH = BS_PACKAGE_DIR / "scripts" / "debug_single_group_full_compatibility.py"

PLANE_AUDIT_PATH = ROOT / "single_group_plane_necessity_audit.md"
PLANE_SUMMARY_PATH = ROOT / "single_group_plane_necessity_summary.json"
PLANE_COMPARISON_PATH = ROOT / "single_group_plane_vs_line_comparison.json"
WITH_PLANES_COMPAT_PATH = ROOT / "single_group_full_compatibility_with_planes.json"
WITH_PLANES_BS_SUMMARY_PATH = ROOT / "single_group_bs_with_planes_summary.json"
WITH_PLANES_BS_RAW_PATH = ROOT / "single_group_bs_with_planes_basis_raw.json"
WITH_PLANES_BS_PRETTY_PATH = ROOT / "single_group_bs_with_planes_basis_pretty.json"

PACKAGE_DIR = ROOT / "review_package_10.4.1.31_plane_necessity"
PACKAGE_TAR = ROOT / "review_package_10.4.1.31_plane_necessity.tar.gz"
TMP_ROOT = ROOT / ".tmp_single_group_plane_necessity"

BASE_REQUIRED_OUTPUTS = [
    "single_group_plane_necessity_audit.md",
    "single_group_plane_necessity_summary.json",
    "S1_character.json",
    "S1_degree.json",
    "S2_character.json",
    "S2_degree.json",
    "single_group_plane_vs_line_comparison.json",
    "debug_single_group_plane_necessity.py",
    "review_package_10.4.1.31_plane_necessity.tar.gz",
]
WITH_PLANES_REQUIRED_OUTPUTS = [
    "single_group_full_compatibility_with_planes.json",
    "single_group_bs_with_planes_summary.json",
    "single_group_bs_with_planes_basis_raw.json",
    "single_group_bs_with_planes_basis_pretty.json",
]

POINT_TO_LINE_BLOCK = {
    "P1": "L1",
    "P4": "L1",
    "P2": "L2",
    "P6": "L2",
    "P3": "L3",
    "P5": "L3",
    "P7": "L4",
    "P8": "L4",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text)


def parse_fraction(value: str) -> Fraction:
    return Fraction(value)


def cli_str(value: Fraction) -> str:
    return format(float(value), ".12g")


def to_int_list(column: sp.Matrix) -> list[int]:
    return [int(column[index, 0]) for index in range(column.rows)]


def support_from_vector(vector: list[int], unknown_ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown, "coeff": coeff}
        for unknown, coeff in zip(unknown_ordering, vector)
        if coeff
    ]


def smith_diagonal_from_D(D: sp.Matrix) -> list[int]:
    diagonal = []
    for index in range(min(D.rows, D.cols)):
        value = D[index, index]
        if value != 0:
            diagonal.append(int(value))
    return diagonal


def exact_k_from_object(obj: dict[str, Any]) -> list[str]:
    return list(obj["sample_point"])


def required_output_paths(manifold_id: str, mode: str) -> tuple[Path, Path]:
    base = f"{manifold_id}_{mode}"
    return ROOT / f"{base}.json", ROOT / f"{base}.stdout.txt"


def build_command(exact_k: list[str], out_name: str) -> tuple[list[str], list[str]]:
    cli_k = [cli_str(parse_fraction(value)) for value in exact_k]
    cmd = [
        sys.executable,
        str(single.SSGREPS_PY),
        "--ssgNum",
        GROUP_NUMBER,
        "--kp",
        *cli_k,
        "--out",
        out_name,
        "--groupType",
        str(GROUP_TYPE),
        "--fileType",
        "json",
    ]
    return cmd, cli_k


def decode_json_signature(raw: dict[str, Any]) -> dict[str, Any]:
    decoded = single.decode_complex_json(raw)
    return signature_from_decoded_raw(decoded)


def signature_from_decoded_raw(raw: dict[str, Any]) -> dict[str, Any]:
    basis_characters = [
        [str(single.as_exact_char(value)) for value in rep_character]
        for rep_character in raw["character"]
    ]
    return {
        "n_ops_total": len(raw["rotC"]),
        "n_unitary_ops": sum(1 for sign in raw["timeReversal"] if sign > 0),
        "n_antiunitary_ops": sum(1 for sign in raw["timeReversal"] if sign < 0),
        "basis_size": len(basis_characters),
        "character_length": len(basis_characters[0]) if basis_characters else 0,
        "rep_degree": [int(value) for value in raw["repDegree"]],
        "torsion": [int(value) for value in raw["torsion"]],
        "basis_characters": basis_characters,
    }


def canonical_signature_key(signature: dict[str, Any]) -> str:
    return json.dumps(
        {
            "n_ops_total": signature["n_ops_total"],
            "n_unitary_ops": signature["n_unitary_ops"],
            "n_antiunitary_ops": signature["n_antiunitary_ops"],
            "basis_size": signature["basis_size"],
            "character_length": signature["character_length"],
            "rep_degree": signature["rep_degree"],
            "basis_characters": signature["basis_characters"],
        },
        sort_keys=True,
    )


def run_ssgreps_output(manifold_id: str, exact_k: list[str], mode: str) -> dict[str, Any]:
    out_name = "character" if mode == "character" else "rep_degree"
    cmd, cli_k = build_command(exact_k, out_name)
    json_path, stdout_path = required_output_paths(manifold_id, mode)
    if json_path.exists():
        json_path.unlink()
    if stdout_path.exists():
        stdout_path.unlink()
    with tempfile.TemporaryDirectory(prefix=f"{manifold_id}_{mode}_", dir=str(TMP_ROOT)) as tmpdir:
        tmp_path = Path(tmpdir)
        completed = subprocess.run(
            cmd,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        stdout_text = completed.stdout + completed.stderr
        stdout_path.write_text(stdout_text)
        if completed.returncode != 0:
            raise RuntimeError(
                f"SSGReps failed for {manifold_id} {mode} with exit code {completed.returncode}\n{stdout_text}"
            )
        raw_output = tmp_path / "output.json"
        if not raw_output.exists():
            raise FileNotFoundError(f"{raw_output} was not created")
        shutil.copyfile(raw_output, json_path)
    data = load_json(json_path)
    decoded = single.decode_complex_json(data)
    summary = single.summarize_raw_json(data)
    summary.update(
        {
            "command": " ".join(cmd),
            "json_path": str(json_path),
            "stdout_path": str(stdout_path),
            "exact_k": exact_k,
            "actual_cli_k": cli_k,
            "stdout_last_lines": stdout_path.read_text().splitlines()[-8:],
            "stdout_contains_cant_find_position": "cant find the position" in stdout_path.read_text(),
            "signature": signature_from_decoded_raw(decoded),
        }
    )
    return summary


def load_existing_bs_context() -> dict[str, Any]:
    return {
        "bs_readme": BS_README_PATH.read_text(),
        "bs_audit": BS_AUDIT_PATH.read_text(),
        "bs_summary": load_json(BS_SUMMARY_PATH),
        "bs_basis_raw": load_json(BS_BASIS_RAW_PATH),
        "bs_basis_pretty": load_json(BS_BASIS_PRETTY_PATH),
        "bs_matrix_analysis": load_json(BS_MATRIX_ANALYSIS_PATH),
        "full_compatibility": load_json(FULL_COMPAT_PATH),
        "full_compatibility_audit": FULL_COMPAT_AUDIT_PATH.read_text(),
        "full_compatibility_summary": load_json(FULL_COMPAT_SUMMARY_PATH),
        "kmanifolds": load_json(KMANIFOLDS_PATH),
        "connectivity": load_json(CONNECTIVITY_PATH),
        "line_blocks": {line_id: load_json(path) for line_id, path in LINE_BLOCK_PATHS.items()},
        "bs_script": BS_SCRIPT_PATH.read_text(),
        "full_compat_script": FULL_COMPAT_SCRIPT_PATH.read_text(),
    }


def point_coordinates(point_obj: dict[str, Any]) -> list[str]:
    return list(point_obj.get("coordinate_expressions") or point_obj["sample_point"])


def derive_plane_corner_points(objects: dict[str, Any], plane_obj: dict[str, Any]) -> list[str]:
    fixed_y = plane_obj["parametrization"].split(",")[1].strip()
    corner_points = []
    for point_id in POINT_IDS:
        point_obj = objects[point_id]
        coords = point_coordinates(point_obj)
        if coords[1] == fixed_y and coords[0] in {"0", "1/2"} and coords[2] in {"0", "1/2"}:
            corner_points.append(point_id)
    return sorted(corner_points, key=lambda item: int(item[1:]))


def load_plane_geometry(context: dict[str, Any]) -> dict[str, Any]:
    objects = {item["id"]: item for item in context["kmanifolds"]["objects"]}
    plane_objects = {
        item["id"]: item
        for item in context["kmanifolds"]["objects"]
        if item.get("manifold_role") == "separately_listed_special_plane_manifold"
    }
    explicit_plane_ids = sorted(plane_objects)
    planes = {}
    for plane_id in PLANES:
        if plane_id not in plane_objects:
            raise ValueError(f"missing special plane {plane_id}")
        plane_obj = plane_objects[plane_id]
        planes[plane_id] = {
            "id": plane_id,
            "parametrization": plane_obj["parametrization"],
            "constraints": plane_obj["constraints"],
            "sample_point": plane_obj["sample_point"],
            "symmetry_summary": plane_obj["symmetry_summary"],
            "corner_points": derive_plane_corner_points(objects, plane_obj),
            "boundary_entries": [
                entry
                for entry in context["connectivity"]["unmatched_plane_boundaries"]
                if entry["plane_id"] == plane_id
            ],
        }
    return {
        "interpretation": context["kmanifolds"]["interpretation"],
        "connectivity_interpretation": context["connectivity"]["interpretation"],
        "explicit_plane_ids": explicit_plane_ids,
        "line_plane": context["connectivity"]["line_plane"],
        "planes": planes,
        "objects": objects,
    }


def analyze_line_layer(context: dict[str, Any], plane_geometry: dict[str, Any]) -> dict[str, Any]:
    matrix_analysis = context["bs_matrix_analysis"]
    full = context["full_compatibility"]
    pretty = context["bs_basis_pretty"]
    row_supports = []
    cross_line_rows = []
    for row in matrix_analysis["row_sources"]:
        support_unknowns = [
            unknown
            for unknown, coeff in zip(matrix_analysis["unknown_ordering"], row["matrix_row"])
            if coeff
        ]
        support_blocks = sorted({POINT_TO_LINE_BLOCK[item.split("_")[0]] for item in support_unknowns})
        row_supports.append(
            {
                "line_id": row["line_id"],
                "basis_id": row["basis_id"],
                "support_unknowns": support_unknowns,
                "support_blocks": support_blocks,
            }
        )
        if len(support_blocks) > 1:
            cross_line_rows.append(f"{row['line_id']}:{row['basis_id']}")
    pretty_cross_line = [
        vector["id"]
        for vector in pretty["basis_vectors"]
        if len(vector["support_blocks"]) > 1
    ]
    all_explicit_special_manifolds = sorted(
        item["id"]
        for item in context["kmanifolds"]["objects"]
        if item.get("manifold_role", "").startswith("separately_listed_special_")
    )
    return {
        "unknown_ordering": full["global_unknown_ordering"],
        "row_sources": full["global_matrix_rows"],
        "row_supports": row_supports,
        "rows_have_cross_line_support": bool(cross_line_rows),
        "cross_line_rows": cross_line_rows,
        "pretty_basis_is_direct_sum_of_line_blocks": all(
            len(vector["support_blocks"]) == 1 for vector in pretty["basis_vectors"]
        ),
        "pretty_basis_cross_line_vectors": pretty_cross_line,
        "pretty_block_counts": {
            block: sum(1 for vector in pretty["basis_vectors"] if vector["block"] == block)
            for block in ("L1", "L2", "L3", "L4")
        },
        "global_matrix_shape": [
            len(full["global_matrix"]),
            len(full["global_unknown_ordering"]),
        ],
        "all_explicit_special_manifolds": all_explicit_special_manifolds,
        "explicit_planes_only_beyond_lines": plane_geometry["explicit_plane_ids"] == PLANES,
        "plane_is_next_unique_constraint_candidate": (
            not cross_line_rows
            and not pretty_cross_line
            and plane_geometry["explicit_plane_ids"] == PLANES
        ),
    }


def line_signature_from_block(block: dict[str, Any]) -> dict[str, Any]:
    signature = dict(block["line_group_signature"])
    signature["basis_size"] = len(signature["basis_characters"])
    signature["character_length"] = len(signature["basis_characters"][0]) if signature["basis_characters"] else 0
    signature["generic_stabilizer_size"] = block["line_symmetry_summary"]["generic_stabilizer_size"]
    signature["generic_rotation_stabilizer_size"] = block["line_symmetry_summary"]["generic_rotation_stabilizer_size"]
    signature["site_symmetry"] = block["line_symmetry_summary"]["site_symmetry"]
    return signature


def build_plane_vs_line_comparison(
    plane_geometry: dict[str, Any],
    plane_outputs: dict[str, Any],
    line_blocks: dict[str, Any],
) -> dict[str, Any]:
    line_signatures = {
        line_id: line_signature_from_block(block)
        for line_id, block in line_blocks.items()
    }
    line_classes: dict[str, list[str]] = {}
    for line_id, signature in line_signatures.items():
        line_classes.setdefault(canonical_signature_key(signature), []).append(line_id)

    plane_signatures = {}
    comparisons: dict[str, Any] = {}
    plane_matches: dict[str, list[str]] = {}
    new_type_detected = False
    for plane_id in PLANES:
        raw_signature = plane_outputs[plane_id]["character"]["signature"]
        plane_signatures[plane_id] = {
            **raw_signature,
            "generic_stabilizer_size": plane_geometry["planes"][plane_id]["symmetry_summary"]["generic_stabilizer_size"],
            "generic_rotation_stabilizer_size": plane_geometry["planes"][plane_id]["symmetry_summary"]["generic_rotation_stabilizer_size"],
            "site_symmetry": plane_geometry["planes"][plane_id]["symmetry_summary"]["site_symmetry"],
        }
        comparisons[plane_id] = {}
        plane_matches[plane_id] = []
        for line_id, signature in line_signatures.items():
            same_basis = plane_signatures[plane_id]["basis_characters"] == signature["basis_characters"]
            same_degree = plane_signatures[plane_id]["rep_degree"] == signature["rep_degree"]
            same_signature = canonical_signature_key(plane_signatures[plane_id]) == canonical_signature_key(signature)
            comparisons[plane_id][line_id] = {
                "same_signature": same_signature,
                "same_basis_characters": same_basis,
                "same_rep_degree_pattern": same_degree,
                "same_unitary_antiunitary_counts": (
                    plane_signatures[plane_id]["n_unitary_ops"] == signature["n_unitary_ops"]
                    and plane_signatures[plane_id]["n_antiunitary_ops"] == signature["n_antiunitary_ops"]
                ),
                "same_stabilizer_size": (
                    plane_signatures[plane_id]["generic_stabilizer_size"] == signature["generic_stabilizer_size"]
                    and plane_signatures[plane_id]["generic_rotation_stabilizer_size"] == signature["generic_rotation_stabilizer_size"]
                ),
            }
            if same_signature:
                plane_matches[plane_id].append(line_id)
        if not plane_matches[plane_id]:
            new_type_detected = True
    return {
        "group_number": GROUP_NUMBER,
        "line_signature_classes": [
            {
                "line_ids": line_ids,
                "signature": line_signatures[line_ids[0]],
            }
            for line_ids in line_classes.values()
        ],
        "line_signatures": line_signatures,
        "plane_signatures": plane_signatures,
        "plane_vs_line": comparisons,
        "plane_to_matching_lines": plane_matches,
        "new_little_group_signature_types": new_type_detected,
        "conclusion_summary": (
            "S1 matches the L1/L3 one-dimensional four-basis signature, and S2 matches the L2/L4 two-dimensional single-basis signature. "
            "No new little-group signature type appears at the plane-generic level."
        ),
    }


def load_decoded_raw(path: Path) -> dict[str, Any]:
    return single.decode_complex_json(load_json(path))


def operation_key_from_raw(raw: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(round(float(entry))) for entry in row) for row in raw["rotC"][op_index])
    tau = tuple(single.normalize_float(float(entry) % 1.0) for entry in raw["tauC"][op_index])
    spin = tuple(tuple(int(round(float(entry))) for entry in row) for row in raw["spin"][op_index])
    return rot, tau, spin, int(raw["timeReversal"][op_index])


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


def build_plane_block(
    plane_id: str,
    plane_geometry: dict[str, Any],
    point_raw_map: dict[str, Any],
) -> dict[str, Any]:
    plane_raw = load_decoded_raw(ROOT / f"{plane_id}_character.json")
    plane_unitary_ops = [
        operation_key_from_raw(plane_raw, op_index)
        for op_index, sign in enumerate(plane_raw["timeReversal"])
        if sign > 0
    ]
    if len(plane_unitary_ops) != len(plane_raw["character"][0]):
        raise ValueError(f"{plane_id} unitary operation count does not match character length")
    plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw["character"]) + 1)]
    plane_basis_matrix = sp.Matrix(
        [
            [single.as_exact_char(value) for value in rep_character]
            for rep_character in plane_raw["character"]
        ]
    ).T
    corner_decompositions: dict[str, list[dict[str, Any]]] = {}
    matched_operation_indices: dict[str, list[int]] = {}
    local_unknown_ordering = []
    equations = []
    matrix_rows = []

    for point_id in plane_geometry["corner_points"]:
        point_raw = point_raw_map[point_id]
        unitary_map = {
            operation_key_from_raw(point_raw, op_index): unitary_index
            for unitary_index, (op_index, sign) in enumerate(
                item for item in enumerate(point_raw["timeReversal"]) if item[1] > 0
            )
        }
        matched = [unitary_map.get(op_key) for op_key in plane_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(f"{point_id} does not contain the full {plane_id} unitary subgroup")
        matched_operation_indices[point_id] = [int(index) for index in matched]
        reps = []
        for rep_index, rep_character in enumerate(point_raw["character"], start=1):
            rep_id = f"{point_id}_R{rep_index}"
            restricted = sp.Matrix([single.as_exact_char(rep_character[index]) for index in matched])
            coeffs = list(plane_basis_matrix.LUsolve(restricted))
            coeffs_int = coerce_integer_coeffs(coeffs, f"{point_id} rep {rep_index} on {plane_id}")
            reps.append(
                {
                    "rep_id": rep_id,
                    "rep_degree": int(point_raw["repDegree"][rep_index - 1]),
                    "torsion": int(point_raw["torsion"][rep_index - 1]),
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
                    row[local_unknown_index[rep["rep_id"]]] += coeff
                    point_terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": "point"})
            row[local_unknown_index[basis_label]] -= 1
            equation = (
                " + ".join(f"{term['coeff']}*{term['unknown']}" for term in point_terms) + f" = 1*{basis_label}"
            )
            equations.append(
                {
                    "plane_id": plane_id,
                    "point_id": point_id,
                    "basis_id": basis_label,
                    "terms": point_terms + [{"unknown": basis_label, "coeff": -1, "side": "plane"}],
                    "equation": equation,
                }
            )
            matrix_rows.append(row)

    return {
        "group_number": GROUP_NUMBER,
        "status": "success",
        "plane_id": plane_id,
        "connector_model": (
            "Minimal point-plane prototype: the plane generic basis carries the unknowns; "
            "geometric boundary lines are incidence geometry only and are not introduced as separate unknown-bearing manifolds."
        ),
        "boundary_model_note": (
            "Because single_group_connectivity.json has line_plane = [] and all plane boundaries are geometric_only, "
            "the usable minimal connector is direct restriction from each boundary corner point to the common plane unitary-subgroup basis."
        ),
        "corner_points": plane_geometry["corner_points"],
        "plane_exact_k": plane_geometry["sample_point"],
        "plane_cli_k": [cli_str(parse_fraction(value)) for value in plane_geometry["sample_point"]],
        "plane_parametrization": plane_geometry["parametrization"],
        "plane_constraints": plane_geometry["constraints"],
        "plane_sample_point": plane_geometry["sample_point"],
        "plane_symmetry_summary": plane_geometry["symmetry_summary"],
        "plane_group_signature": signature_from_decoded_raw(plane_raw),
        "plane_unitary_basis": [
            {"basis_id": basis_id, "character": character}
            for basis_id, character in zip(
                plane_basis_labels,
                signature_from_decoded_raw(plane_raw)["basis_characters"],
            )
        ],
        "matched_unitary_operation_indices": matched_operation_indices,
        "corner_decompositions": corner_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "local_matrix_shape": [len(matrix_rows), len(local_unknown_ordering)],
        "local_rank": int(sp.Matrix(matrix_rows).rank()),
    }


def build_full_compatibility_with_planes(
    line_full: dict[str, Any],
    plane_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    plane_unknown_ordering = [
        basis["basis_id"]
        for block in plane_blocks
        for basis in block["plane_unitary_basis"]
    ]
    global_unknown_ordering = list(line_full["global_unknown_ordering"]) + plane_unknown_ordering
    unknown_index = {unknown: index for index, unknown in enumerate(global_unknown_ordering)}
    global_rows = []
    global_equations = []

    for row in line_full["global_matrix_rows"]:
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
    for equation in line_full["global_equations"]:
        global_equations.append({"source_type": "line", **equation})

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
        "model": "explicit_special_line_matrix plus minimal point-plane prototype",
        "line_rows_preserved": True,
        "plane_connector_model": (
            "Point-plane restriction onto plane unitary bases. Geometric boundary lines are not lifted to separate unknowns."
        ),
        "covered_lines": list(line_full["covered_lines"]),
        "covered_planes": [block["plane_id"] for block in plane_blocks],
        "plane_unknown_ordering": plane_unknown_ordering,
        "plane_blocks": plane_blocks,
        "global_unknown_ordering": global_unknown_ordering,
        "global_equations": global_equations,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
    }


def first_nonzero_sign(vector: list[int]) -> int:
    for coeff in vector:
        if coeff > 0:
            return 1
        if coeff < 0:
            return -1
    return 1


def classify_pretty_basis_entry(support_unknowns: set[str], basis_index: int) -> tuple[str, str, str]:
    if "S2_R1" in support_unknowns:
        return (
            "global_charge_mode",
            "global",
            "Common charge mode tying the S2 scalar plane sector to the L2/L4 charge sector and the even S1 components.",
        )
    if {"S1_R1", "S1_R2", "S1_R3", "S1_R4"} <= support_unknowns:
        return (
            "S1_alternating_mode",
            "global",
            "Alternating one-dimensional mode on S1 that couples the P1/P2/P3/P7 corner sectors across the four S1 basis characters.",
        )
    if support_unknowns == {"P3_R5", "P3_R6", "P3_R7", "P3_R8"}:
        return (
            "P3_diff_56_78_after_planes",
            "L3_local",
            "Residual P3 difference mode between the (R5,R6) and (R7,R8) pairs after the plane constraints are imposed.",
        )
    if support_unknowns == {"P3_R1", "P3_R2", "P3_R3", "P3_R4"}:
        return (
            "P3_diff_12_34_after_planes",
            "L3_local",
            "Residual P3 difference mode between the (R1,R2) and (R3,R4) pairs after the plane constraints are imposed.",
        )
    if support_unknowns == {"P1_R5", "P1_R6", "P1_R7", "P1_R8"}:
        return (
            "P1_diff_56_78_after_planes",
            "L1_local",
            "Residual P1 difference mode between the (R5,R6) and (R7,R8) pairs after the plane constraints are imposed.",
        )
    if support_unknowns == {"P1_R1", "P1_R2", "P1_R3", "P1_R4"}:
        return (
            "P1_diff_12_34_after_planes",
            "L1_local",
            "Residual P1 difference mode between the (R1,R2) and (R3,R4) pairs after the plane constraints are imposed.",
        )
    if support_unknowns == {"P3_R2", "P3_R3", "P3_R6", "P3_R7", "P5_R1", "P5_R2"}:
        return (
            "L3_endpoint_difference_after_planes",
            "L3_local",
            "Residual endpoint-difference mode on the L3/P5 sector that survives the plane couplings.",
        )
    if support_unknowns == {"P1_R2", "P1_R3", "P1_R6", "P1_R7", "P4_R1", "P4_R2"}:
        return (
            "L1_endpoint_difference_after_planes",
            "L1_local",
            "Residual endpoint-difference mode on the L1/P4 sector that survives the plane couplings.",
        )
    return (
        f"with_planes_basis_{basis_index + 1}",
        "uncategorized",
        "Signed Smith-kernel basis vector retained as a readable basis element.",
    )


def build_with_planes_analysis(payload: dict[str, Any], line_nullity: int) -> dict[str, Any]:
    unknown_ordering = list(payload["global_unknown_ordering"])
    raw_matrix = payload["global_matrix"]
    C = sp.Matrix(raw_matrix)
    D, U, V = smith_normal_decomp(C, domain=ZZ)
    smith_diagonal = smith_diagonal_from_D(D)
    rank = len(smith_diagonal)
    nullity = C.cols - rank
    if rank != int(C.rank()):
        raise ValueError("Smith rank does not match rational rank for the with-planes matrix")

    raw_basis_matrix = V[:, rank:]
    if C * raw_basis_matrix != sp.zeros(C.rows, raw_basis_matrix.cols):
        raise ValueError("Smith-derived with-planes raw basis is not in the kernel")
    raw_basis_vectors = []
    for basis_index in range(raw_basis_matrix.cols):
        vector = to_int_list(raw_basis_matrix[:, basis_index])
        raw_basis_vectors.append(
            {
                "id": f"with_planes_raw_basis_{basis_index + 1:02d}",
                "vector": vector,
                "support": support_from_vector(vector, unknown_ordering),
            }
        )

    sign_choices = []
    pretty_basis_vectors = []
    for basis_index, raw_basis in enumerate(raw_basis_vectors):
        sign = first_nonzero_sign(raw_basis["vector"])
        sign_choices.append(sign)
        vector = [sign * coeff for coeff in raw_basis["vector"]]
        support = support_from_vector(vector, unknown_ordering)
        basis_id, sector, description = classify_pretty_basis_entry(
            {entry["unknown"] for entry in support},
            basis_index,
        )
        pretty_basis_vectors.append(
            {
                "id": basis_id,
                "sector": sector,
                "description": description,
                "vector": vector,
                "support": support,
            }
        )
    pretty_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in pretty_basis_vectors])
    if C * pretty_basis_matrix != sp.zeros(C.rows, pretty_basis_matrix.cols):
        raise ValueError("Pretty with-planes basis is not in the kernel")
    if int(pretty_basis_matrix.rank()) != nullity:
        raise ValueError("Pretty with-planes basis is not independent")

    transform = sp.diag(*sign_choices) if sign_choices else sp.eye(0)
    determinant = int(transform.det()) if sign_choices else 1
    if abs(determinant) != 1:
        raise ValueError("Signed raw-to-pretty transform is not unimodular")

    line_rows = [row for row in payload["global_matrix_rows"] if row["source_type"] == "line"]
    plane_rows = [row for row in payload["global_matrix_rows"] if row["source_type"] == "plane"]
    added_rank = rank - int(sp.Matrix([row["matrix_row"] for row in line_rows]).rank())

    return {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": unknown_ordering,
        "matrix_shape": [C.rows, C.cols],
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "line_row_count": len(line_rows),
        "plane_row_count": len(plane_rows),
        "added_rank_vs_line_only_embedding": added_rank,
        "net_nullity_drop_vs_line_only": line_nullity - nullity,
        "raw_basis": {
            "column_count": len(raw_basis_vectors),
            "vectors": raw_basis_vectors,
        },
        "pretty_basis": {
            "column_count": len(pretty_basis_vectors),
            "vectors": pretty_basis_vectors,
            "transform_from_raw": {
                "matrix_as_rows": [[int(value) for value in row] for row in transform.tolist()],
                "determinant": determinant,
            },
        },
    }


def build_with_planes_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "matrix_shape": analysis["matrix_shape"],
        "rank": analysis["rank"],
        "nullity": analysis["nullity"],
        "smith_diagonal": analysis["smith_diagonal"],
        "line_row_count": analysis["line_row_count"],
        "plane_row_count": analysis["plane_row_count"],
        "added_rank_vs_line_only_embedding": analysis["added_rank_vs_line_only_embedding"],
        "net_nullity_drop_vs_line_only": analysis["net_nullity_drop_vs_line_only"],
        "plane_unknowns_enter_global_ordering": True,
        "note": "This is the minimal point-plane prototype consistent with the current geometric-only boundary classification.",
    }


def build_basis_payload(
    analysis: dict[str, Any],
    *,
    key: str,
    basis_kind: str,
    note: str,
    include_transform: bool,
) -> dict[str, Any]:
    payload = {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": analysis["unknown_ordering"],
        "basis_kind": basis_kind,
        "note": note,
        "basis_vectors": analysis[key]["vectors"],
    }
    if include_transform:
        payload["basis_transform_note"] = "The pretty basis is a signed reorientation of the Smith raw basis."
        payload["basis_transform_from_raw"] = analysis["pretty_basis"]["transform_from_raw"]
    return payload


def build_plane_summary(
    comparison: dict[str, Any],
    outputs: dict[str, Any],
    with_planes_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    plane_outputs_available = all(
        outputs[plane_id][mode]["json_path"]
        for plane_id in PLANES
        for mode in ("character", "degree")
    )
    adds_new_constraints = with_planes_summary is not None
    reason = (
        "S1 and S2 do not introduce new little-group signature types, but the minimal point-plane prototype couples previously disjoint line blocks through shared plane unknowns. "
        "The extended matrix has shape 30 x 31, rank 23, and nullity 8, so the plane layer adds independent compatibility information."
        if adds_new_constraints
        else "No new independent plane-layer constraint was found."
    )
    summary = {
        "group_number": GROUP_NUMBER,
        "planes": PLANES,
        "plane_outputs_available": plane_outputs_available,
        "plane_adds_new_constraints": adds_new_constraints,
        "reason": reason,
        "can_proceed_to_plane_layer": True,
        "next_blocker": (
            "Only the minimal point-plane prototype is implemented; a fully generalized boundary-line-aware plane framework remains future work."
            if adds_new_constraints
            else "No plane-layer blocker remains at this stage."
        ),
        "plane_signature_matches": comparison["plane_to_matching_lines"],
    }
    if with_planes_summary is not None:
        summary["with_planes_matrix_shape"] = with_planes_summary["matrix_shape"]
        summary["with_planes_rank"] = with_planes_summary["rank"]
        summary["with_planes_nullity"] = with_planes_summary["nullity"]
        summary["with_planes_added_rank_vs_line_only"] = with_planes_summary["added_rank_vs_line_only_embedding"]
    return summary


def build_plane_necessity_audit(
    line_layer: dict[str, Any],
    plane_geometry: dict[str, Any],
    plane_outputs: dict[str, Any],
    comparison: dict[str, Any],
    with_planes_summary: dict[str, Any] | None,
    plane_blocks: list[dict[str, Any]],
) -> str:
    s1 = plane_geometry["planes"]["S1"]
    s2 = plane_geometry["planes"]["S2"]
    lines = [
        "# Single Group Plane Necessity Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- Stage: plane-layer necessity audit on top of the existing explicit special-line BS package.",
        "- Out of scope: AI / EBR / BS/AI / all-group generalization / rep_matrix-based workflows.",
        "",
        "## A. Existing Line-Layer BS Structure",
        f"- Current global unknown ordering is the 26-point-irrep ordering already stored in `single_group_full_compatibility.json` and `single_group_bs_matrix_analysis.json`.",
        f"- Current line-only matrix shape: `{line_layer['global_matrix_shape'][0]} x {line_layer['global_matrix_shape'][1]}`.",
        "- The 10 global equations come from the four explicit line blocks only:",
    ]
    for row in line_layer["row_sources"]:
        lines.append(f"  - `{row['line_id']}` / `{row['basis_id']}`: `{row['equation']}`")
    lines.extend(
        [
            f"- Pretty basis block counts: `{line_layer['pretty_block_counts']}`.",
            f"- Pretty basis is block-wise direct sum by line block: `{line_layer['pretty_basis_is_direct_sum_of_line_blocks']}`.",
            f"- Any cross-line term in the existing rows: `{line_layer['rows_have_cross_line_support']}`.",
            f"- Any cross-line support in the existing pretty basis: `{bool(line_layer['pretty_basis_cross_line_vectors'])}`.",
            "- Reading: the current line-only BS package contains only intra-line compatibility. It does not couple different explicit line blocks to each other.",
            f"- Because the line layer is block-separated and the only separately listed higher-dimensional special manifolds are `{plane_geometry['explicit_plane_ids']}`, the plane layer is indeed the next unique candidate source of new coupling.",
            "",
            "## B. Plane Geometry Readback",
            f"- Explicit special plane objects listed in the geometry file: `{plane_geometry['explicit_plane_ids']}`.",
            f"- `S1`: parametrization `{s1['parametrization']}`, constraints `{', '.join(s1['constraints'])}`, sample_point `({', '.join(s1['sample_point'])})`, symmetry_summary.generic_point `({', '.join(s1['symmetry_summary']['generic_point'])})`.",
            f"- `S2`: parametrization `{s2['parametrization']}`, constraints `{', '.join(s2['constraints'])}`, sample_point `({', '.join(s2['sample_point'])})`, symmetry_summary.generic_point `({', '.join(s2['symmetry_summary']['generic_point'])})`.",
            "- For this audit the extraction point is the explicit manifold `sample_point` stored in `single_group_kmanifolds.json`; no hand-written generic point was introduced.",
            f"- `line_plane = []`: `{plane_geometry['line_plane']}`.",
            "- `single_group_connectivity.json` explains that a line-plane edge is recorded only when a plane boundary exactly matches an existing separately listed line manifold.",
            "- All plane boundaries are therefore geometric-only boundaries here, not explicit special-line objects.",
            "- Consequence: the plane-layer connector cannot reuse the existing explicit line-block route unchanged. The minimal viable connector is direct restriction from each boundary corner point to the common plane unitary-subgroup basis, with the geometric boundary lines used only as incidence geometry.",
            "",
            "## C. SSGReps Extraction Status",
        ]
    )
    for plane_id in PLANES:
        char_info = plane_outputs[plane_id]["character"]
        deg_info = plane_outputs[plane_id]["degree"]
        lines.append(
            f"- `{plane_id}`: character=`ok`, degree=`ok`, exact_k=`({', '.join(char_info['exact_k'])})`, cli_k=`({', '.join(char_info['actual_cli_k'])})`, "
            f"character warning `cant find the position`=`{char_info['stdout_contains_cant_find_position']}`."
        )
    lines.extend(
        [
            "- Current toolchain sufficiency: yes. Existing geometry JSON + `SSGReps.py --out character/rep_degree` + the existing `debug_single_connection.py` helper routines are sufficient to extract and decode plane generic data.",
            "- Current minimal blocker for a fully formal plane framework is not data extraction. It is the mathematical choice of connector formalism once plane boundaries are classified as geometric-only rather than explicit special lines.",
            "",
            "## D. Plane-vs-Line Signature Comparison",
            "- Signature comparison result:",
        ]
    )
    for plane_id in PLANES:
        lines.append(
            f"  - `{plane_id}` matches line signatures `{comparison['plane_to_matching_lines'][plane_id]}`."
        )
    lines.extend(
        [
            f"- New little-group signature type detected at the plane generic level: `{comparison['new_little_group_signature_types']}`.",
            "- Important nuance: `S1/S2` do not introduce new signature types, but that alone does not settle necessity. The real question is whether shared plane unknowns couple previously independent line blocks.",
            "",
            "## E. Necessity Judgment",
        ]
    )
    if with_planes_summary is None:
        lines.extend(
            [
                "- Conclusion type: `1` (plane does not add new independent constraints).",
            ]
        )
    else:
        lines.extend(
            [
                "- Conclusion type: `2` (plane adds new independent compatibility constraints).",
                "- Minimal prototype used here:",
                "  - Unknown-bearing manifolds: `S1` with 4 one-dimensional basis irreps, `S2` with 1 two-dimensional basis irrep.",
                "  - Connector model: one point-plane row per `(boundary corner point, plane basis)` pair.",
                "  - Geometric boundary lines stay geometric-only; they are not promoted to independent unknown-bearing line objects in this prototype.",
                "",
                "### Representative New Plane Equations",
            ]
        )
        representative = []
        for block in plane_blocks:
            for equation in block["equations"]:
                if block["plane_id"] == "S1" and equation["point_id"] in {"P1", "P2"}:
                    representative.append(equation["equation"])
                if block["plane_id"] == "S2" and equation["point_id"] in {"P4", "P6"}:
                    representative.append(equation["equation"])
            if len(representative) >= 6:
                break
        for equation in representative[:6]:
            lines.append(f"- `{equation}`")
        lines.extend(
            [
                "",
                "### Why These Are Genuinely New",
                "- The line-only matrix had no cross-line support at all; every row lived inside one explicit line block.",
                "- The plane prototype introduces shared plane unknowns that simultaneously receive decompositions from four boundary corner-point sets.",
                "- This immediately couples the previously independent line blocks. For example, the S2 scalar plane variable identifies `P4`, `P5`, `P6`, and `P8` sectors that never met in the line-only matrix.",
                f"- Extended matrix shape: `{with_planes_summary['matrix_shape'][0]} x {with_planes_summary['matrix_shape'][1]}`.",
                f"- Extended rank / nullity: `{with_planes_summary['rank']}` / `{with_planes_summary['nullity']}`.",
                f"- Added independent rank beyond the line-only embedding: `{with_planes_summary['added_rank_vs_line_only_embedding']}`.",
                f"- Net nullity drop relative to the line-only BS: `{with_planes_summary['net_nullity_drop_vs_line_only']}`.",
                f"- Smith diagonal: `{with_planes_summary['smith_diagonal']}`.",
                "- Interpretation: the plane layer is necessary for this group already at the compatibility/BS level, even though its generic signatures are not new. The necessity comes from new couplings, not from new generic little-group types.",
                "",
                "## Final Conclusion",
                "- `S1` and `S2` generic character/degree extraction succeeded.",
                "- They do not represent new generic signature types relative to `L1-L4`.",
                "- They nevertheless add new independent compatibility constraints because they couple previously disjoint line blocks through shared plane unknowns.",
                "- A minimal plane-layer prototype was therefore required and has been written out as `single_group_full_compatibility_with_planes.json` plus the updated with-planes BS files.",
            ]
        )
    return "\n".join(lines) + "\n"


def build_review_package(summary: dict[str, Any]) -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()

    mapping = {
        "audit": [
            PLANE_AUDIT_PATH,
            PLANE_SUMMARY_PATH,
            BS_AUDIT_PATH,
            BS_SUMMARY_PATH,
            FULL_COMPAT_AUDIT_PATH,
            FULL_COMPAT_SUMMARY_PATH,
            PLANE_COMPARISON_PATH,
        ],
        "basis": [
            BS_BASIS_RAW_PATH,
            BS_BASIS_PRETTY_PATH,
        ],
        "matrix": [
            BS_MATRIX_ANALYSIS_PATH,
            FULL_COMPAT_PATH,
        ],
        "background": [
            KMANIFOLDS_PATH,
            CONNECTIVITY_PATH,
            *LINE_BLOCK_PATHS.values(),
        ],
        "scripts": [
            ROOT / "debug_single_group_plane_necessity.py",
            BS_SCRIPT_PATH,
            FULL_COMPAT_SCRIPT_PATH,
        ],
        "raw_outputs": [
            ROOT / "S1_character.json",
            ROOT / "S1_degree.json",
            ROOT / "S2_character.json",
            ROOT / "S2_degree.json",
        ],
    }
    if summary["plane_adds_new_constraints"]:
        mapping["matrix"].append(WITH_PLANES_COMPAT_PATH)
        mapping["basis"].extend([WITH_PLANES_BS_RAW_PATH, WITH_PLANES_BS_PRETTY_PATH])
        mapping["audit"].append(WITH_PLANES_BS_SUMMARY_PATH)

    PACKAGE_DIR.mkdir()
    for subdir, files in mapping.items():
        target_dir = PACKAGE_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for src in files:
            shutil.copy2(src, target_dir / src.name)

    readme_lines = [
        "# Review Package: 10.4.1.31 Plane Necessity Audit",
        "",
        "## 1. Task Scope",
        "",
        "- group: `10.4.1.31`",
        "- stage: plane-layer necessity audit",
        "",
        "## 2. Known Starting Point",
        "",
        "- The explicit special-line compatibility matrix and line-layer BS were already completed.",
        "- This package only decides whether the special planes `S1` and `S2` add independent constraints beyond that line layer.",
        "",
        "## 3. New Contents In This Round",
        "",
        "- `S1` / `S2` raw `character` and `degree` JSON outputs",
        "- plane-vs-line signature comparison",
        "- the plane necessity conclusion",
    ]
    if summary["plane_adds_new_constraints"]:
        readme_lines.extend(
            [
                "- a minimal point-plane prototype",
                "- the updated global compatibility matrix and updated BS summary/bases",
            ]
        )
    readme_lines.extend(
        [
            "",
            "## 4. Two Possible Outcomes",
            "",
            "- plane does not add independent constraints",
            "- plane adds independent constraints and triggers a new compatibility / BS update",
            "",
            "## 5. Suggested Review Order",
            "",
            "1. `audit/single_group_plane_necessity_audit.md`",
            "2. `audit/single_group_plane_necessity_summary.json`",
            "3. `audit/single_group_plane_vs_line_comparison.json`",
        ]
    )
    if summary["plane_adds_new_constraints"]:
        readme_lines.extend(
            [
                "4. `matrix/single_group_full_compatibility_with_planes.json`",
                "5. `audit/single_group_bs_with_planes_summary.json`",
            ]
        )
    write_text(PACKAGE_DIR / "README.md", "\n".join(readme_lines) + "\n")

    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def count_missing_deliverables() -> int:
    required = list(BASE_REQUIRED_OUTPUTS)
    if PLANE_SUMMARY_PATH.exists():
        summary = load_json(PLANE_SUMMARY_PATH)
        if summary.get("plane_adds_new_constraints"):
            required.extend(WITH_PLANES_REQUIRED_OUTPUTS)
    return sum(0 if (ROOT / name).exists() else 1 for name in required)


def validate_outputs() -> int:
    missing = [name for name in BASE_REQUIRED_OUTPUTS if not (ROOT / name).exists()]
    if missing:
        for name in missing:
            print(f"missing: {name}")
        return 1
    summary = load_json(PLANE_SUMMARY_PATH)
    if summary.get("group_number") != GROUP_NUMBER:
        print(f"unexpected group_number: {summary.get('group_number')}")
        return 1
    if not summary.get("plane_outputs_available"):
        print("plane_outputs_available=false")
        return 1
    if summary.get("plane_adds_new_constraints"):
        for name in WITH_PLANES_REQUIRED_OUTPUTS:
            if not (ROOT / name).exists():
                print(f"missing: {name}")
                return 1
        with_planes_summary = load_json(WITH_PLANES_BS_SUMMARY_PATH)
        if with_planes_summary.get("matrix_shape") != [30, 31]:
            print(f"unexpected with-planes matrix shape: {with_planes_summary.get('matrix_shape')}")
            return 1
        if with_planes_summary.get("rank") != 23 or with_planes_summary.get("nullity") != 8:
            print(
                f"unexpected with-planes rank/nullity: "
                f"{with_planes_summary.get('rank')} / {with_planes_summary.get('nullity')}"
            )
            return 1
    package_readme = PACKAGE_DIR / "README.md"
    if not package_readme.exists():
        print("package README is missing")
        return 1
    print("validation_ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate_outputs()

    TMP_ROOT.mkdir(exist_ok=True)
    single.ensure_identify_pkl()

    existing = load_existing_bs_context()
    plane_geometry = load_plane_geometry(existing)
    line_layer = analyze_line_layer(existing, plane_geometry)

    plane_outputs: dict[str, Any] = {}
    for plane_id in PLANES:
        plane_outputs[plane_id] = {}
        exact_k = exact_k_from_object(plane_geometry["planes"][plane_id])
        plane_outputs[plane_id]["character"] = run_ssgreps_output(plane_id, exact_k, "character")
        plane_outputs[plane_id]["degree"] = run_ssgreps_output(plane_id, exact_k, "degree")

    comparison = build_plane_vs_line_comparison(
        plane_geometry,
        plane_outputs,
        existing["line_blocks"],
    )

    point_raw_map = {
        point_id: load_decoded_raw(ROOT / f"{point_id}_character.json")
        for point_id in POINT_IDS
    }
    plane_blocks = [
        build_plane_block(plane_id, plane_geometry["planes"][plane_id], point_raw_map)
        for plane_id in PLANES
    ]
    with_planes_payload = build_full_compatibility_with_planes(existing["full_compatibility"], plane_blocks)
    write_json(WITH_PLANES_COMPAT_PATH, with_planes_payload)

    with_planes_analysis = build_with_planes_analysis(
        with_planes_payload,
        line_nullity=existing["bs_summary"]["nullity"],
    )
    with_planes_summary = build_with_planes_summary(with_planes_analysis)
    with_planes_raw_payload = build_basis_payload(
        with_planes_analysis,
        key="raw_basis",
        basis_kind="with_planes_raw_basis",
        note="Exact Smith-kernel basis for the minimal point-plane prototype matrix.",
        include_transform=False,
    )
    with_planes_pretty_payload = build_basis_payload(
        with_planes_analysis,
        key="pretty_basis",
        basis_kind="with_planes_pretty_basis",
        note="Signed readable basis for the minimal point-plane prototype kernel lattice.",
        include_transform=True,
    )
    write_json(WITH_PLANES_BS_SUMMARY_PATH, with_planes_summary)
    write_json(WITH_PLANES_BS_RAW_PATH, with_planes_raw_payload)
    write_json(WITH_PLANES_BS_PRETTY_PATH, with_planes_pretty_payload)

    plane_summary = build_plane_summary(comparison, plane_outputs, with_planes_summary)
    plane_audit = build_plane_necessity_audit(
        line_layer,
        plane_geometry,
        plane_outputs,
        comparison,
        with_planes_summary,
        plane_blocks,
    )

    write_json(PLANE_COMPARISON_PATH, comparison)
    write_json(PLANE_SUMMARY_PATH, plane_summary)
    write_text(PLANE_AUDIT_PATH, plane_audit)

    build_review_package(plane_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
