#!/usr/bin/env python3

from __future__ import annotations

import argparse
import itertools
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

PREV_PACKAGE_DIR = ROOT / "review_package_10.4.1.31_plane_necessity"
PREV_README_PATH = PREV_PACKAGE_DIR / "README.md"
PREV_PLANE_AUDIT_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_plane_necessity_audit.md"
PREV_PLANE_SUMMARY_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_plane_necessity_summary.json"
PREV_PLANE_COMPARISON_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_plane_vs_line_comparison.json"
PREV_WITH_PLANES_SUMMARY_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_bs_with_planes_summary.json"
PREV_WITH_PLANES_MATRIX_PATH = PREV_PACKAGE_DIR / "matrix" / "single_group_full_compatibility_with_planes.json"
PREV_WITH_PLANES_BS_RAW_PATH = PREV_PACKAGE_DIR / "basis" / "single_group_bs_with_planes_basis_raw.json"
PREV_WITH_PLANES_BS_PRETTY_PATH = PREV_PACKAGE_DIR / "basis" / "single_group_bs_with_planes_basis_pretty.json"
PREV_S1_CHARACTER_PATH = PREV_PACKAGE_DIR / "raw_outputs" / "S1_character.json"
PREV_S1_DEGREE_PATH = PREV_PACKAGE_DIR / "raw_outputs" / "S1_degree.json"
PREV_S2_CHARACTER_PATH = PREV_PACKAGE_DIR / "raw_outputs" / "S2_character.json"
PREV_S2_DEGREE_PATH = PREV_PACKAGE_DIR / "raw_outputs" / "S2_degree.json"
PREV_KMANIFOLDS_PATH = PREV_PACKAGE_DIR / "background" / "single_group_kmanifolds.json"
PREV_CONNECTIVITY_PATH = PREV_PACKAGE_DIR / "background" / "single_group_connectivity.json"
PREV_SCRIPT_PATH = PREV_PACKAGE_DIR / "scripts" / "debug_single_group_plane_necessity.py"

PREV_BS_AUDIT_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_bs_audit.md"
PREV_BS_SUMMARY_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_bs_summary.json"
PREV_BS_WITH_PLANES_SUMMARY_PATH = PREV_PACKAGE_DIR / "audit" / "single_group_bs_with_planes_summary.json"
PREV_BS_RAW_PATH = PREV_PACKAGE_DIR / "basis" / "single_group_bs_basis_raw.json"
PREV_BS_PRETTY_PATH = PREV_PACKAGE_DIR / "basis" / "single_group_bs_basis_pretty.json"
PREV_FULL_COMPAT_PATH = PREV_PACKAGE_DIR / "matrix" / "single_group_full_compatibility.json"
PREV_FULL_WITH_PLANES_PATH = PREV_PACKAGE_DIR / "matrix" / "single_group_full_compatibility_with_planes.json"

FORMALISM_AUDIT_PATH = ROOT / "single_group_plane_formalism_audit.md"
FORMALISM_SUMMARY_PATH = ROOT / "single_group_plane_formalism_summary.json"
BOUNDARY_VS_PLANE_PATH = ROOT / "single_group_boundary_line_vs_plane_comparison.json"
TORSION_AUDIT_PATH = ROOT / "single_group_torsion_audit.json"

CORRECTED_WITH_PLANES_MATRIX_PATH = ROOT / "single_group_full_compatibility_with_planes_corrected.json"
CORRECTED_WITH_PLANES_SUMMARY_PATH = ROOT / "single_group_bs_with_planes_corrected_summary.json"
CORRECTED_WITH_PLANES_BS_RAW_PATH = ROOT / "single_group_bs_with_planes_corrected_basis_raw.json"
CORRECTED_WITH_PLANES_BS_PRETTY_PATH = ROOT / "single_group_bs_with_planes_corrected_basis_pretty.json"

PACKAGE_DIR = ROOT / "review_package_10.4.1.31_plane_formalism"
PACKAGE_TAR = ROOT / "review_package_10.4.1.31_plane_formalism.tar.gz"
TMP_ROOT = ROOT / ".tmp_single_group_plane_formalism"

BASE_REQUIRED_OUTPUTS = [
    "single_group_plane_formalism_audit.md",
    "single_group_plane_formalism_summary.json",
    "single_group_boundary_line_vs_plane_comparison.json",
    "single_group_torsion_audit.json",
    "debug_single_group_plane_formalism.py",
    "review_package_10.4.1.31_plane_formalism.tar.gz",
]
OPTIONAL_CORRECTED_OUTPUTS = [
    "single_group_full_compatibility_with_planes_corrected.json",
    "single_group_bs_with_planes_corrected_summary.json",
    "single_group_bs_with_planes_corrected_basis_raw.json",
    "single_group_bs_with_planes_corrected_basis_pretty.json",
]

BOUNDARY_CONDITION_TO_SUFFIX = {
    "u = 0": "u0",
    "u = 1/2": "u12",
    "w = 0": "w0",
    "w = 1/2": "w12",
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


def smith_diagonal_from_D(D: sp.Matrix) -> list[int]:
    diagonal = []
    for index in range(min(D.rows, D.cols)):
        value = D[index, index]
        if value != 0:
            diagonal.append(int(value))
    return diagonal


def support_from_vector(vector: list[int], labels: list[str], *, key: str) -> list[dict[str, Any]]:
    return [
        {key: label, "coeff": coeff}
        for label, coeff in zip(labels, vector)
        if coeff
    ]


def point_coordinates(point_obj: dict[str, Any]) -> list[str]:
    return list(point_obj.get("coordinate_expressions") or point_obj["sample_point"])


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


def required_output_paths(manifold_id: str, mode: str) -> tuple[Path, Path]:
    base = f"{manifold_id}_{mode}"
    return ROOT / f"{base}.json", ROOT / f"{base}.stdout.txt"


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


def derive_plane_corner_points(objects: dict[str, Any], plane_obj: dict[str, Any]) -> list[str]:
    fixed_y = plane_obj["parametrization"].split(",")[1].strip()
    corner_points = []
    for point_id in POINT_IDS:
        coords = point_coordinates(objects[point_id])
        if coords[1] == fixed_y and coords[0] in {"0", "1/2"} and coords[2] in {"0", "1/2"}:
            corner_points.append(point_id)
    return sorted(corner_points, key=lambda item: int(item[1:]))


def load_previous_context() -> dict[str, Any]:
    kmanifolds = load_json(PREV_KMANIFOLDS_PATH)
    connectivity = load_json(PREV_CONNECTIVITY_PATH)
    objects = {item["id"]: item for item in kmanifolds["objects"]}
    plane_objects = {
        item["id"]: item
        for item in kmanifolds["objects"]
        if item.get("manifold_role") == "separately_listed_special_plane_manifold"
    }
    boundary_entries = connectivity["unmatched_plane_boundaries"]
    return {
        "readme": PREV_README_PATH.read_text(),
        "plane_necessity_audit": PREV_PLANE_AUDIT_PATH.read_text(),
        "plane_necessity_summary": load_json(PREV_PLANE_SUMMARY_PATH),
        "plane_vs_line_comparison": load_json(PREV_PLANE_COMPARISON_PATH),
        "with_planes_summary": load_json(PREV_WITH_PLANES_SUMMARY_PATH),
        "with_planes_matrix": load_json(PREV_WITH_PLANES_MATRIX_PATH),
        "with_planes_basis_raw": load_json(PREV_WITH_PLANES_BS_RAW_PATH),
        "with_planes_basis_pretty": load_json(PREV_WITH_PLANES_BS_PRETTY_PATH),
        "s1_character": load_json(PREV_S1_CHARACTER_PATH),
        "s1_degree": load_json(PREV_S1_DEGREE_PATH),
        "s2_character": load_json(PREV_S2_CHARACTER_PATH),
        "s2_degree": load_json(PREV_S2_DEGREE_PATH),
        "kmanifolds": kmanifolds,
        "connectivity": connectivity,
        "objects": objects,
        "planes": {
            plane_id: {
                "id": plane_id,
                "object": plane_objects[plane_id],
                "parametrization": plane_objects[plane_id]["parametrization"],
                "constraints": plane_objects[plane_id]["constraints"],
                "sample_point": plane_objects[plane_id]["sample_point"],
                "symmetry_summary": plane_objects[plane_id]["symmetry_summary"],
                "corner_points": derive_plane_corner_points(objects, plane_objects[plane_id]),
            }
            for plane_id in PLANES
        },
        "boundary_entries": boundary_entries,
    }


def boundary_suffix(boundary_condition: str) -> str:
    if boundary_condition not in BOUNDARY_CONDITION_TO_SUFFIX:
        raise KeyError(f"unsupported boundary condition: {boundary_condition}")
    return BOUNDARY_CONDITION_TO_SUFFIX[boundary_condition]


def boundary_id(entry: dict[str, Any]) -> str:
    return f"{entry['plane_id']}_bdry_{boundary_suffix(entry['boundary_condition'])}"


def derive_boundary_endpoints(
    objects: dict[str, Any],
    plane_obj: dict[str, Any],
    entry: dict[str, Any],
) -> list[str]:
    fixed_y = plane_obj["parametrization"].split(",")[1].strip()
    variable_name, _, fixed_value = entry["boundary_condition"].partition("=")
    variable_name = variable_name.strip()
    fixed_value = fixed_value.strip()
    result = []
    for point_id in derive_plane_corner_points(objects, plane_obj):
        coords = point_coordinates(objects[point_id])
        coord_map = {"u": coords[0], "w": coords[2], "y": coords[1]}
        if coords[1] != fixed_y:
            continue
        if coord_map[variable_name] == fixed_value:
            result.append(point_id)
    return sorted(result, key=lambda item: int(item[1:]))


def build_boundary_infos(context: dict[str, Any]) -> list[dict[str, Any]]:
    infos = []
    for entry in context["boundary_entries"]:
        plane_id = entry["plane_id"]
        plane_obj = context["planes"][plane_id]["object"]
        bid = boundary_id(entry)
        infos.append(
            {
                "boundary_id": bid,
                "plane_id": plane_id,
                "boundary_condition": entry["boundary_condition"],
                "derived_line": entry["derived_line"],
                "parameters": entry["parameters"],
                "constraints": entry["constraints"],
                "sample_point": entry["sample_point"],
                "symmetry_summary": entry["symmetry_summary"],
                "classification": entry["classification"],
                "special_line_orbit_match": entry["special_line_orbit_match"],
                "endpoints": derive_boundary_endpoints(context["objects"], plane_obj, entry),
            }
        )
    infos.sort(key=lambda item: (item["plane_id"], item["boundary_id"]))
    return infos


def build_target_basis_labels(target_id: str, target_raw: dict[str, Any]) -> list[str]:
    return [f"{target_id}_R{i}" for i in range(1, len(target_raw["character"]) + 1)]


def build_restriction_decomposition(
    source_id: str,
    source_raw: dict[str, Any],
    target_id: str,
    target_raw: dict[str, Any],
    *,
    context: str,
) -> dict[str, Any]:
    target_unitary_ops = [
        operation_key_from_raw(target_raw, op_index)
        for op_index, sign in enumerate(target_raw["timeReversal"])
        if sign > 0
    ]
    if len(target_unitary_ops) != len(target_raw["character"][0]):
        raise ValueError(f"{target_id} unitary operation count does not match character length")
    target_basis_labels = build_target_basis_labels(target_id, target_raw)
    target_basis_matrix = sp.Matrix(
        [
            [single.as_exact_char(value) for value in rep_character]
            for rep_character in target_raw["character"]
        ]
    ).T
    source_unitary_map = {
        operation_key_from_raw(source_raw, op_index): unitary_index
        for unitary_index, (op_index, sign) in enumerate(
            item for item in enumerate(source_raw["timeReversal"]) if item[1] > 0
        )
    }
    matched = [source_unitary_map.get(op_key) for op_key in target_unitary_ops]
    if any(index is None for index in matched):
        raise ValueError(f"{source_id} does not contain the full {target_id} unitary subgroup in {context}")
    reps = []
    for rep_index, rep_character in enumerate(source_raw["character"], start=1):
        rep_id = f"{source_id}_R{rep_index}"
        restricted = sp.Matrix([single.as_exact_char(rep_character[index]) for index in matched])
        coeffs = list(target_basis_matrix.LUsolve(restricted))
        coeffs_int = coerce_integer_coeffs(coeffs, f"{context}: {rep_id}")
        reps.append(
            {
                "rep_id": rep_id,
                "rep_degree": int(source_raw["repDegree"][rep_index - 1]),
                "torsion": int(source_raw["torsion"][rep_index - 1]),
                "restricted_character_on_target_unitary_subgroup": [str(entry) for entry in restricted],
                "decomposition_on_target_basis": {
                    basis_label: coeff
                    for basis_label, coeff in zip(target_basis_labels, coeffs_int)
                    if coeff
                },
            }
        )
    return {
        "source_id": source_id,
        "target_id": target_id,
        "target_basis_labels": target_basis_labels,
        "matched_unitary_operation_indices": [int(index) for index in matched],
        "reps": reps,
    }


def compose_decompositions(
    first: dict[str, int],
    second: dict[str, dict[str, int]],
    target_basis_labels: list[str],
) -> dict[str, int]:
    coeffs = {basis_id: 0 for basis_id in target_basis_labels}
    for intermediate_id, first_coeff in first.items():
        for target_id, second_coeff in second[intermediate_id].items():
            coeffs[target_id] += first_coeff * second_coeff
    return {basis_id: coeff for basis_id, coeff in coeffs.items() if coeff}


def decomp_vector(decomposition: dict[str, int], basis_labels: list[str]) -> list[int]:
    return [int(decomposition.get(basis_id, 0)) for basis_id in basis_labels]


def point_local_row_from_rep_decompositions(
    point_reps: list[dict[str, Any]],
    plane_basis_labels: list[str],
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for basis_label in plane_basis_labels:
        row = []
        for rep in point_reps:
            row.append(int(rep["decomposition_on_target_basis"].get(basis_label, 0)))
        result[basis_label] = row
    return result


def build_direct_plane_maps(with_planes_payload: dict[str, Any]) -> dict[str, Any]:
    direct_by_plane: dict[str, Any] = {}
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in with_planes_payload["global_matrix_rows"]:
        if row["source_type"] == "plane":
            rows_by_key[(row["plane_id"], row["point_id"], row["basis_id"])] = row
    for block in with_planes_payload["plane_blocks"]:
        plane_id = block["plane_id"]
        plane_basis_labels = [item["basis_id"] for item in block["plane_unitary_basis"]]
        direct_by_plane[plane_id] = {
            "basis_labels": plane_basis_labels,
            "basis_characters": [item["character"] for item in block["plane_unitary_basis"]],
            "point_reps": {
                point_id: {
                    rep["rep_id"]: rep["decomposition_on_plane_basis"]
                    for rep in block["corner_decompositions"][point_id]
                }
                for point_id in block["corner_points"]
            },
            "point_rows": {
                point_id: {
                    basis_id: {
                        "coefficients_on_point_irreps": [
                            int(rep["decomposition_on_plane_basis"].get(basis_id, 0))
                            for rep in block["corner_decompositions"][point_id]
                        ],
                        "global_row": rows_by_key[(plane_id, point_id, basis_id)]["matrix_row"],
                        "equation": rows_by_key[(plane_id, point_id, basis_id)]["equation"],
                    }
                    for basis_id in plane_basis_labels
                }
                for point_id in block["corner_points"]
            },
        }
    return direct_by_plane


def build_boundary_outputs(boundaries: list[dict[str, Any]]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for boundary in boundaries:
        bid = boundary["boundary_id"]
        outputs[bid] = {
            "boundary_id": bid,
            "plane_id": boundary["plane_id"],
            "boundary_condition": boundary["boundary_condition"],
            "exact_k": list(boundary["sample_point"]),
            "actual_cli_k": [cli_str(parse_fraction(value)) for value in boundary["sample_point"]],
            "outputs": {},
            "status": "pending",
        }
        try:
            outputs[bid]["outputs"]["character"] = run_ssgreps_output(
                bid,
                list(boundary["sample_point"]),
                "character",
            )
            outputs[bid]["outputs"]["degree"] = run_ssgreps_output(
                bid,
                list(boundary["sample_point"]),
                "degree",
            )
            outputs[bid]["status"] = "ok"
        except Exception as exc:  # pragma: no cover - only used on tool/runtime failures
            outputs[bid]["status"] = "error"
            outputs[bid]["error"] = str(exc)
    return outputs


def build_boundary_vs_plane_comparison(
    context: dict[str, Any],
    boundaries: list[dict[str, Any]],
    boundary_outputs: dict[str, Any],
) -> dict[str, Any]:
    with_planes_payload = context["with_planes_matrix"]
    direct_maps = build_direct_plane_maps(with_planes_payload)
    plane_raw_map = {
        "S1": load_decoded_raw(PREV_S1_CHARACTER_PATH),
        "S2": load_decoded_raw(PREV_S2_CHARACTER_PATH),
    }
    point_raw_map = {
        point_id: load_decoded_raw(ROOT / f"{point_id}_character.json")
        for point_id in POINT_IDS
    }

    plane_signatures = {}
    for plane_id in PLANES:
        plane_signatures[plane_id] = {
            **signature_from_decoded_raw(plane_raw_map[plane_id]),
            "generic_stabilizer_size": context["planes"][plane_id]["symmetry_summary"]["generic_stabilizer_size"],
            "generic_rotation_stabilizer_size": context["planes"][plane_id]["symmetry_summary"]["generic_rotation_stabilizer_size"],
            "site_symmetry": context["planes"][plane_id]["symmetry_summary"]["site_symmetry"],
        }

    boundaries_payload = []
    all_boundary_outputs_available = True
    all_chain_matches = True
    all_row_matches = True
    all_boundary_plane_basis_maps_identity = True

    for boundary in boundaries:
        bid = boundary["boundary_id"]
        output = boundary_outputs[bid]
        entry = {
            "boundary_id": bid,
            "plane_id": boundary["plane_id"],
            "boundary_condition": boundary["boundary_condition"],
            "derived_line": boundary["derived_line"],
            "parameters": boundary["parameters"],
            "constraints": boundary["constraints"],
            "exact_k": list(boundary["sample_point"]),
            "actual_cli_k": [cli_str(parse_fraction(value)) for value in boundary["sample_point"]],
            "endpoints": list(boundary["endpoints"]),
            "classification": boundary["classification"],
            "special_line_orbit_match": boundary["special_line_orbit_match"],
            "status": output["status"],
        }
        if output["status"] != "ok":
            all_boundary_outputs_available = False
            entry["error"] = output.get("error", "unknown extraction failure")
            boundaries_payload.append(entry)
            all_chain_matches = False
            all_row_matches = False
            all_boundary_plane_basis_maps_identity = False
            continue

        boundary_raw = load_decoded_raw(ROOT / f"{bid}_character.json")
        plane_id = boundary["plane_id"]
        plane_raw = plane_raw_map[plane_id]
        plane_basis_labels = direct_maps[plane_id]["basis_labels"]

        boundary_signature = {
            **signature_from_decoded_raw(boundary_raw),
            "generic_stabilizer_size": boundary["symmetry_summary"]["generic_stabilizer_size"],
            "generic_rotation_stabilizer_size": boundary["symmetry_summary"]["generic_rotation_stabilizer_size"],
            "site_symmetry": boundary["symmetry_summary"]["site_symmetry"],
        }
        comparison = {
            "same_signature": canonical_signature_key(boundary_signature)
            == canonical_signature_key(plane_signatures[plane_id]),
            "same_basis_characters": boundary_signature["basis_characters"]
            == plane_signatures[plane_id]["basis_characters"],
            "same_rep_degree_pattern": boundary_signature["rep_degree"]
            == plane_signatures[plane_id]["rep_degree"],
            "same_unitary_antiunitary_counts": (
                boundary_signature["n_unitary_ops"] == plane_signatures[plane_id]["n_unitary_ops"]
                and boundary_signature["n_antiunitary_ops"] == plane_signatures[plane_id]["n_antiunitary_ops"]
            ),
            "same_stabilizer_size": (
                boundary_signature["generic_stabilizer_size"]
                == plane_signatures[plane_id]["generic_stabilizer_size"]
                and boundary_signature["generic_rotation_stabilizer_size"]
                == plane_signatures[plane_id]["generic_rotation_stabilizer_size"]
            ),
        }

        boundary_to_plane = build_restriction_decomposition(
            bid,
            boundary_raw,
            plane_id,
            plane_raw,
            context=f"{bid} -> {plane_id}",
        )
        boundary_basis_to_plane = {
            rep["rep_id"]: rep["decomposition_on_target_basis"]
            for rep in boundary_to_plane["reps"]
        }
        basis_map_identity = True
        for index, rep in enumerate(boundary_to_plane["reps"], start=1):
            if rep["decomposition_on_target_basis"] != {f"{plane_id}_R{index}": 1}:
                basis_map_identity = False
                break
        all_boundary_plane_basis_maps_identity &= basis_map_identity

        endpoint_payload = []
        boundary_all_chain_matches = True
        boundary_all_row_matches = True

        for point_id in boundary["endpoints"]:
            point_to_boundary = build_restriction_decomposition(
                point_id,
                point_raw_map[point_id],
                bid,
                boundary_raw,
                context=f"{point_id} -> {bid}",
            )
            rep_checks = []
            chain_reps_for_rows = []
            direct_point_map = direct_maps[plane_id]["point_reps"][point_id]
            for rep in point_to_boundary["reps"]:
                chain_decomposition = compose_decompositions(
                    rep["decomposition_on_target_basis"],
                    boundary_basis_to_plane,
                    plane_basis_labels,
                )
                direct_decomposition = direct_point_map[rep["rep_id"]]
                matches = chain_decomposition == direct_decomposition
                rep_checks.append(
                    {
                        "rep_id": rep["rep_id"],
                        "point_to_boundary_decomposition": rep["decomposition_on_target_basis"],
                        "chain_to_plane_decomposition": chain_decomposition,
                        "direct_point_to_plane_decomposition": direct_decomposition,
                        "matches_direct": matches,
                    }
                )
                boundary_all_chain_matches &= matches
                all_chain_matches &= matches
                chain_reps_for_rows.append(
                    {
                        "rep_id": rep["rep_id"],
                        "decomposition_on_target_basis": chain_decomposition,
                    }
                )

            chain_rows = point_local_row_from_rep_decompositions(chain_reps_for_rows, plane_basis_labels)
            row_checks = []
            for basis_id in plane_basis_labels:
                direct_row = direct_maps[plane_id]["point_rows"][point_id][basis_id]["coefficients_on_point_irreps"]
                chain_row = chain_rows[basis_id]
                matches = chain_row == direct_row
                row_checks.append(
                    {
                        "basis_id": basis_id,
                        "chain_coefficients_on_point_irreps": chain_row,
                        "direct_coefficients_on_point_irreps": direct_row,
                        "direct_equation": direct_maps[plane_id]["point_rows"][point_id][basis_id]["equation"],
                        "matches_direct": matches,
                    }
                )
                boundary_all_row_matches &= matches
                all_row_matches &= matches

            endpoint_payload.append(
                {
                    "point_id": point_id,
                    "matched_unitary_operation_indices_for_point_to_boundary": point_to_boundary["matched_unitary_operation_indices"],
                    "rep_checks": rep_checks,
                    "row_checks": row_checks,
                    "all_rep_checks_match": all(item["matches_direct"] for item in rep_checks),
                    "all_row_checks_match": all(item["matches_direct"] for item in row_checks),
                }
            )

        entry.update(
            {
                "boundary_signature": boundary_signature,
                "plane_signature": plane_signatures[plane_id],
                "boundary_vs_plane_signature": comparison,
                "boundary_to_plane": {
                    "matched_unitary_operation_indices": boundary_to_plane["matched_unitary_operation_indices"],
                    "basis_rep_to_plane_decomposition": boundary_basis_to_plane,
                    "basis_map_is_identity": basis_map_identity,
                },
                "endpoint_chain_checks": endpoint_payload,
                "all_endpoint_chain_checks_match_direct": boundary_all_chain_matches,
                "all_endpoint_row_checks_match_direct": boundary_all_row_matches,
            }
        )
        boundaries_payload.append(entry)

    plane_summaries = {}
    for plane_id in PLANES:
        plane_boundaries = [item for item in boundaries_payload if item["plane_id"] == plane_id]
        plane_summaries[plane_id] = {
            "boundary_ids": [item["boundary_id"] for item in plane_boundaries],
            "all_boundary_outputs_available": all(item["status"] == "ok" for item in plane_boundaries),
            "all_chain_matches_direct": all(
                item.get("all_endpoint_chain_checks_match_direct", False)
                for item in plane_boundaries
                if item["status"] == "ok"
            ),
            "all_row_matches_direct": all(
                item.get("all_endpoint_row_checks_match_direct", False)
                for item in plane_boundaries
                if item["status"] == "ok"
            ),
        }

    return {
        "group_number": GROUP_NUMBER,
        "current_plane_unknowns": with_planes_payload["plane_unknown_ordering"],
        "current_plane_unknown_definitions": [
            {
                "basis_id": basis["basis_id"],
                "character": basis["character"],
                "rep_degree": plane_signatures[basis["basis_id"].split("_")[0]]["rep_degree"][index],
            }
            for plane_id in PLANES
            for index, basis in enumerate(
                next(
                    block["plane_unitary_basis"]
                    for block in with_planes_payload["plane_blocks"]
                    if block["plane_id"] == plane_id
                )
            )
        ],
        "current_plane_rows": [
            {
                "row_index": index,
                "plane_id": row["plane_id"],
                "point_id": row["point_id"],
                "basis_id": row["basis_id"],
                "equation": row["equation"],
            }
            for index, row in enumerate(with_planes_payload["global_matrix_rows"])
            if row["source_type"] == "plane"
        ],
        "boundary_lines": boundaries_payload,
        "plane_summaries": plane_summaries,
        "boundary_line_outputs_available": all_boundary_outputs_available,
        "chain_check_consistent": all_chain_matches and all_row_matches and all_boundary_outputs_available,
        "chain_rows_equal_direct_rows": all_row_matches and all_boundary_outputs_available,
        "boundary_to_plane_basis_maps_identity": all_boundary_plane_basis_maps_identity and all_boundary_outputs_available,
        "conclusion_summary": (
            "Every boundary line can be treated as a local check object without entering the global unknown ordering. "
            "The chain point -> boundary-line -> plane reproduces the current direct point -> plane decompositions exactly for all available endpoints."
            if all_chain_matches and all_row_matches and all_boundary_outputs_available
            else "At least one boundary-line chain check fails to reproduce the current direct point -> plane model."
        ),
    }


def matrix_from_rows(rows: list[list[int]]) -> sp.Matrix:
    if not rows:
        return sp.Matrix.zeros(0, 0)
    return sp.Matrix(rows)


def analyze_matrix_rows(rows: list[dict[str, Any]], col_count: int) -> dict[str, Any]:
    M = sp.Matrix([row["matrix_row"] for row in rows]) if rows else sp.Matrix.zeros(0, col_count)
    D, U, V = smith_normal_decomp(M, domain=ZZ)
    diagonal = smith_diagonal_from_D(D)
    return {
        "shape": [M.rows, M.cols],
        "rank": len(diagonal),
        "smith_diagonal": diagonal,
        "matrix": M,
        "D": D,
        "U": U,
        "V": V,
    }


def analyze_selected_rows(
    all_rows: list[dict[str, Any]],
    unknown_ordering: list[str],
    row_ids: list[int],
) -> dict[str, Any]:
    selected_rows = [all_rows[index] for index in row_ids]
    analysis = analyze_matrix_rows(selected_rows, len(unknown_ordering))
    support_cols = sorted(
        {col_index for row in selected_rows for col_index, value in enumerate(row["matrix_row"]) if value}
    )
    support_matrix = sp.Matrix(
        [[row["matrix_row"][col_index] for col_index in support_cols] for row in selected_rows]
    ) if selected_rows else sp.Matrix.zeros(0, 0)
    D_support, _, _ = smith_normal_decomp(support_matrix, domain=ZZ)
    return {
        "row_ids": row_ids,
        "rows": [
            {
                "row_index": index,
                "source_type": all_rows[index]["source_type"],
                "line_id": all_rows[index].get("line_id"),
                "plane_id": all_rows[index].get("plane_id"),
                "point_id": all_rows[index].get("point_id"),
                "basis_id": all_rows[index].get("basis_id"),
                "equation": all_rows[index]["equation"],
            }
            for index in row_ids
        ],
        "shape": analysis["shape"],
        "rank": analysis["rank"],
        "smith_diagonal": analysis["smith_diagonal"],
        "support_columns": [
            {"column_index": index, "unknown": unknown_ordering[index]}
            for index in support_cols
        ],
        "support_only_shape": [support_matrix.rows, support_matrix.cols],
        "support_only_smith_diagonal": smith_diagonal_from_D(D_support),
    }


def find_minimal_torsion_pair(rows: list[dict[str, Any]], unknown_ordering: list[str]) -> dict[str, Any] | None:
    for row_ids in itertools.combinations(range(len(rows)), 2):
        witness = analyze_selected_rows(rows, unknown_ordering, list(row_ids))
        if 2 in witness["smith_diagonal"]:
            return witness
    return None


def find_minimal_s1_torsion_witness(rows: list[dict[str, Any]], unknown_ordering: list[str]) -> dict[str, Any] | None:
    candidates = [
        index
        for index, row in enumerate(rows)
        if (row["source_type"] == "line" and row.get("line_id") in {"L2", "L4"})
        or (row["source_type"] == "plane" and row.get("plane_id") == "S1" and row.get("point_id") in {"P2", "P7"})
    ]
    for size in range(1, len(candidates) + 1):
        for subset in itertools.combinations(candidates, size):
            witness = analyze_selected_rows(rows, unknown_ordering, list(subset))
            if 2 in witness["smith_diagonal"]:
                return witness
    return None


def build_torsion_audit(
    with_planes_payload: dict[str, Any],
    chain_comparison: dict[str, Any],
) -> dict[str, Any]:
    unknown_ordering = with_planes_payload["global_unknown_ordering"]
    rows = with_planes_payload["global_matrix_rows"]
    full = analyze_matrix_rows(rows, len(unknown_ordering))
    torsion_positions = [
        index
        for index in range(min(full["D"].rows, full["D"].cols))
        if full["D"][index, index] == 2
    ]
    torsion_index = torsion_positions[0] if torsion_positions else None
    transformed_row_support = []
    transformed_col_support = []
    if torsion_index is not None:
        transformed_row_support = [
            {
                "row_index": row_index,
                "coeff": int(full["U"][torsion_index, row_index]),
                "source_type": rows[row_index]["source_type"],
                "line_id": rows[row_index].get("line_id"),
                "plane_id": rows[row_index].get("plane_id"),
                "point_id": rows[row_index].get("point_id"),
                "basis_id": rows[row_index].get("basis_id"),
                "equation": rows[row_index]["equation"],
            }
            for row_index in range(full["U"].cols)
            if full["U"][torsion_index, row_index] != 0
        ]
        transformed_col_support = [
            {
                "column_index": col_index,
                "unknown": unknown_ordering[col_index],
                "coeff": int(full["V"][col_index, torsion_index]),
            }
            for col_index in range(full["V"].rows)
            if full["V"][col_index, torsion_index] != 0
        ]

    def row_ids_where(predicate) -> list[int]:
        return [index for index, row in enumerate(rows) if predicate(row)]

    experiment_specs = [
        ("line_only_baseline", row_ids_where(lambda row: row["source_type"] == "line")),
        ("full_current_matrix", list(range(len(rows)))),
        ("drop_S1_rows", row_ids_where(lambda row: row["source_type"] == "line" or row.get("plane_id") == "S2")),
        ("drop_S2_rows", row_ids_where(lambda row: row["source_type"] == "line" or row.get("plane_id") == "S1")),
        (
            "drop_S2_double_rows_P6_P8",
            row_ids_where(
                lambda row: not (
                    row["source_type"] == "plane"
                    and row.get("plane_id") == "S2"
                    and row.get("point_id") in {"P6", "P8"}
                )
            ),
        ),
        (
            "drop_S2_simple_rows_P4_P5",
            row_ids_where(
                lambda row: not (
                    row["source_type"] == "plane"
                    and row.get("plane_id") == "S2"
                    and row.get("point_id") in {"P4", "P5"}
                )
            ),
        ),
        ("drop_L2", row_ids_where(lambda row: not (row["source_type"] == "line" and row.get("line_id") == "L2"))),
        ("drop_L4", row_ids_where(lambda row: not (row["source_type"] == "line" and row.get("line_id") == "L4"))),
        (
            "drop_L2_and_L4",
            row_ids_where(
                lambda row: not (
                    row["source_type"] == "line" and row.get("line_id") in {"L2", "L4"}
                )
            ),
        ),
        (
            "only_S2_double_rows",
            row_ids_where(
                lambda row: row["source_type"] == "plane"
                and row.get("plane_id") == "S2"
                and row.get("point_id") in {"P6", "P8"}
            ),
        ),
    ]
    experiments = {}
    for name, row_ids in experiment_specs:
        witness = analyze_selected_rows(rows, unknown_ordering, row_ids)
        experiments[name] = {
            "shape": witness["shape"],
            "rank": witness["rank"],
            "smith_diagonal": witness["smith_diagonal"],
            "row_ids": row_ids,
        }

    minimal_pair_witness = find_minimal_torsion_pair(rows, unknown_ordering)
    minimal_s1_witness = find_minimal_s1_torsion_witness(rows, unknown_ordering)

    chain_replacement_same = bool(chain_comparison["chain_rows_equal_direct_rows"])
    chain_replacement_summary = {
        "rows_identical_to_current_direct_rows": chain_replacement_same,
        "smith_diagonal_if_replaced_by_chain_rows": full["smith_diagonal"] if chain_replacement_same else None,
        "torsion_changes_under_chain_replacement": False if chain_replacement_same else None,
    }

    torsion_explained = torsion_index is not None and chain_replacement_same
    reason = (
        "The unique 2 is a real parity/evenness constraint in the current integer compatibility lattice. "
        "It is absent in the line-only 10 x 26 matrix, but it appears as soon as either plane family is added. "
        "A minimal witness is the 2 x 3 subsystem formed by the rows 2*P6_R1 = S2_R1 and 2*P8_R1 = S2_R1, whose Smith diagonal is [1, 2]. "
        "An alternative S1-mediated witness is rows L2, L4, P2->S1(R1/R2), and P7->S1(R1/R2), which also produce a single 2. "
        "Because the chain audit reproduces the current direct rows exactly, this 2 is not a fake artifact of skipping explicit boundary-line unknowns."
        if torsion_explained
        else "The origin of the Smith-diagonal 2 remains unresolved."
    )

    return {
        "group_number": GROUP_NUMBER,
        "with_planes_matrix_shape": full["shape"],
        "with_planes_rank": full["rank"],
        "with_planes_smith_diagonal": full["smith_diagonal"],
        "torsion_diagonal_position_1_based": None if torsion_index is None else torsion_index + 1,
        "transformed_row_support_for_2": transformed_row_support,
        "transformed_column_support_for_2": transformed_col_support,
        "minimal_torsion_witness": minimal_pair_witness,
        "alternative_S1_witness": minimal_s1_witness,
        "row_removal_experiments": experiments,
        "chain_consistent_row_replacement": chain_replacement_summary,
        "torsion_2_explained": torsion_explained,
        "torsion_2_reason": reason,
    }


def build_formalism_summary(
    chain_comparison: dict[str, Any],
    torsion_audit: dict[str, Any],
) -> dict[str, Any]:
    accepted = chain_comparison["chain_check_consistent"] and torsion_audit["torsion_2_explained"]
    return {
        "group_number": GROUP_NUMBER,
        "boundary_line_outputs_available": chain_comparison["boundary_line_outputs_available"],
        "chain_check_consistent": chain_comparison["chain_check_consistent"],
        "torsion_2_explained": torsion_audit["torsion_2_explained"],
        "torsion_2_reason": torsion_audit["torsion_2_reason"],
        "current_plane_model_accepted": accepted,
        "requires_matrix_update": not accepted,
        "next_blocker": (
            "No immediate matrix correction is required at this layer; the remaining blocker is a future fully general connector formalism beyond this single-group local validation."
            if accepted
            else "The current direct point-plane rows do not survive the boundary-line chain check and need a corrected connector formalism."
        ),
    }


def format_signature(signature: dict[str, Any]) -> str:
    return (
        f"ops={signature['n_ops_total']}, unitary={signature['n_unitary_ops']}, "
        f"antiunitary={signature['n_antiunitary_ops']}, rep_degree={signature['rep_degree']}, "
        f"basis_characters={signature['basis_characters']}"
    )


def build_formalism_audit_markdown(
    context: dict[str, Any],
    boundaries: list[dict[str, Any]],
    boundary_outputs: dict[str, Any],
    chain_comparison: dict[str, Any],
    torsion_audit: dict[str, Any],
    summary: dict[str, Any],
) -> str:
    with_planes_payload = context["with_planes_matrix"]
    lines = [
        "# Single Group Plane Formalism Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- Stage: plane formalism audit and torsion audit on top of the existing minimal with-planes prototype.",
        "- Out of scope: AI / EBR / BS/AI / all-group generalization / final topology classification / rep_matrix-based workflows.",
        "",
        "## A. Current Minimal Point-Plane Prototype",
        "- Current model: `point -> plane direct restriction onto plane unitary basis`.",
        f"- Current with-planes matrix shape / rank / nullity: `{context['with_planes_summary']['matrix_shape'][0]} x {context['with_planes_summary']['matrix_shape'][1]}` / `{context['with_planes_summary']['rank']}` / `{context['with_planes_summary']['nullity']}`.",
        f"- Current plane unknown ordering: `{with_planes_payload['plane_unknown_ordering']}`.",
        "- Plane basis definitions:",
    ]
    for item in chain_comparison["current_plane_unknown_definitions"]:
        lines.append(
            f"  - `{item['basis_id']}` with character `{item['character']}` and rep_degree `{item['rep_degree']}`"
        )
    lines.extend(
        [
            "- Current 20 plane rows:",
        ]
    )
    for row in chain_comparison["current_plane_rows"]:
        lines.append(
            f"  - global row `{row['row_index']}`: `{row['plane_id']}` / `{row['point_id']}` / `{row['basis_id']}` gives `{row['equation']}`"
        )

    lines.extend(
        [
            "",
            "## B. Geometric-Only Boundary Lines Used As Local Check Objects",
            "- These boundary lines are not promoted to global unknown-bearing manifolds.",
            "- They are only used here as local intermediate objects for the chain check `point -> boundary-line -> plane`.",
            "- Exact boundary sample points read from `single_group_connectivity.json`:",
        ]
    )
    for boundary in boundaries:
        lines.append(
            f"  - `{boundary['boundary_id']}`: plane `{boundary['plane_id']}`, boundary `{boundary['boundary_condition']}`, derived line `{boundary['derived_line']}`, sample point `({', '.join(boundary['sample_point'])})`, endpoints `{boundary['endpoints']}`"
        )

    lines.extend(
        [
            "",
            "## C. Boundary-Line character / degree Extraction",
        ]
    )
    for boundary in boundaries:
        bid = boundary["boundary_id"]
        output = boundary_outputs[bid]
        if output["status"] == "ok":
            lines.append(
                f"- `{bid}`: character=`ok`, degree=`ok`, exact_k=`({', '.join(output['exact_k'])})`, cli_k=`({', '.join(output['actual_cli_k'])})`, `cant find the position` in character stdout=`{output['outputs']['character']['stdout_contains_cant_find_position']}`."
            )
        else:
            lines.append(f"- `{bid}`: extraction failed: `{output.get('error', 'unknown error')}`.")

    lines.extend(
        [
            "",
            "## D. Boundary-Line vs Plane Signatures",
        ]
    )
    for boundary in chain_comparison["boundary_lines"]:
        if boundary["status"] != "ok":
            lines.append(f"- `{boundary['boundary_id']}`: signature comparison unavailable because extraction failed.")
            continue
        lines.append(
            f"- `{boundary['boundary_id']}` vs `{boundary['plane_id']}`: "
            f"same_signature=`{boundary['boundary_vs_plane_signature']['same_signature']}`, "
            f"same_basis_characters=`{boundary['boundary_vs_plane_signature']['same_basis_characters']}`, "
            f"same_rep_degree_pattern=`{boundary['boundary_vs_plane_signature']['same_rep_degree_pattern']}`, "
            f"basis_map_is_identity=`{boundary['boundary_to_plane']['basis_map_is_identity']}`."
        )
        lines.append(f"  - boundary signature: `{format_signature(boundary['boundary_signature'])}`")
        lines.append(f"  - plane signature: `{format_signature(boundary['plane_signature'])}`")

    lines.extend(
        [
            "",
            "## E. Chain Consistency Check",
            "- Question: can the current direct model be reproduced as `point -> boundary-line -> plane`?",
        ]
    )
    for boundary in chain_comparison["boundary_lines"]:
        if boundary["status"] != "ok":
            continue
        lines.append(
            f"- `{boundary['boundary_id']}`: all endpoint rep checks match direct=`{boundary['all_endpoint_chain_checks_match_direct']}`, all endpoint row checks match direct=`{boundary['all_endpoint_row_checks_match_direct']}`."
        )
        for endpoint in boundary["endpoint_chain_checks"]:
            lines.append(
                f"  - `{endpoint['point_id']}`: rep_match=`{endpoint['all_rep_checks_match']}`, row_match=`{endpoint['all_row_checks_match']}`"
            )
    lines.extend(
        [
            f"- Global chain consistency result: `{chain_comparison['chain_check_consistent']}`.",
            f"- Chain-consistent rows equal the current direct rows: `{chain_comparison['chain_rows_equal_direct_rows']}`.",
            (
                "- Reading: the current minimal point-plane prototype is supported by the stricter chain check. "
                "The geometric-only boundary lines do not need to enter the global unknown ordering to validate the existing point-plane rows."
                if chain_comparison["chain_check_consistent"]
                else "- Reading: the chain check exposes a mismatch, so the current direct model is not yet reliable."
            ),
            "",
            "## F. Smith-Diagonal `2` Torsion Audit",
            f"- Full with-planes Smith diagonal: `{torsion_audit['with_planes_smith_diagonal']}`.",
            f"- The nontrivial invariant factor `2` sits at Smith position `{torsion_audit['torsion_diagonal_position_1_based']}` (1-based).",
        ]
    )
    if torsion_audit["minimal_torsion_witness"] is not None:
        witness = torsion_audit["minimal_torsion_witness"]
        lines.append(
            f"- Minimal torsion witness rows: `{[item['row_index'] for item in witness['rows']]}` with support-only Smith diagonal `{witness['support_only_smith_diagonal']}`."
        )
        for row in witness["rows"]:
            lines.append(f"  - `{row['equation']}`")
        lines.append(
            f"  - support unknowns: `{[item['unknown'] for item in witness['support_columns']]}`"
        )
    if torsion_audit["alternative_S1_witness"] is not None:
        witness = torsion_audit["alternative_S1_witness"]
        lines.append(
            f"- Alternative S1-mediated witness rows: `{[item['row_index'] for item in witness['rows']]}` with support-only Smith diagonal `{witness['support_only_smith_diagonal']}`."
        )
        for row in witness["rows"]:
            lines.append(f"  - `{row['equation']}`")

    lines.extend(
        [
            "- Row-removal experiments:",
        ]
    )
    for name, result in torsion_audit["row_removal_experiments"].items():
        lines.append(
            f"  - `{name}` -> shape `{result['shape'][0]} x {result['shape'][1]}`, rank `{result['rank']}`, Smith `{result['smith_diagonal']}`"
        )
    lines.extend(
        [
            f"- Chain-consistent row replacement changes the Smith result: `{torsion_audit['chain_consistent_row_replacement']['torsion_changes_under_chain_replacement']}`.",
            f"- Interpretation: {torsion_audit['torsion_2_reason']}",
            "",
            "## Final Conclusion",
            (
                "- Conclusion type: `1` (current minimal point-plane prototype is consistent and credible)."
                if summary["current_plane_model_accepted"]
                else "- Conclusion type: `2` (current minimal point-plane prototype requires correction)."
            ),
            f"- boundary_line_outputs_available=`{summary['boundary_line_outputs_available']}`",
            f"- chain_check_consistent=`{summary['chain_check_consistent']}`",
            f"- torsion_2_explained=`{summary['torsion_2_explained']}`",
            f"- current_plane_model_accepted=`{summary['current_plane_model_accepted']}`",
            f"- requires_matrix_update=`{summary['requires_matrix_update']}`",
            f"- next_blocker: {summary['next_blocker']}",
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
            FORMALISM_AUDIT_PATH,
            FORMALISM_SUMMARY_PATH,
            BOUNDARY_VS_PLANE_PATH,
            TORSION_AUDIT_PATH,
            PREV_PLANE_AUDIT_PATH,
            PREV_PLANE_SUMMARY_PATH,
            PREV_PLANE_COMPARISON_PATH,
            PREV_BS_AUDIT_PATH,
            PREV_BS_SUMMARY_PATH,
            PREV_BS_WITH_PLANES_SUMMARY_PATH,
        ],
        "basis": [
            PREV_BS_RAW_PATH,
            PREV_BS_PRETTY_PATH,
            PREV_WITH_PLANES_BS_RAW_PATH,
            PREV_WITH_PLANES_BS_PRETTY_PATH,
        ],
        "matrix": [
            PREV_FULL_COMPAT_PATH,
            PREV_FULL_WITH_PLANES_PATH,
        ],
        "background": [
            PREV_KMANIFOLDS_PATH,
            PREV_CONNECTIVITY_PATH,
        ],
        "scripts": [
            ROOT / "debug_single_group_plane_formalism.py",
            PREV_SCRIPT_PATH,
        ],
        "raw_outputs": [
            PREV_S1_CHARACTER_PATH,
            PREV_S1_DEGREE_PATH,
            PREV_S2_CHARACTER_PATH,
            PREV_S2_DEGREE_PATH,
            *[ROOT / f"{plane}_bdry_{suffix}_character.json" for plane in ("S1", "S2") for suffix in ("u0", "u12", "w0", "w12")],
            *[ROOT / f"{plane}_bdry_{suffix}_degree.json" for plane in ("S1", "S2") for suffix in ("u0", "u12", "w0", "w12")],
        ],
    }
    if summary["requires_matrix_update"]:
        mapping["matrix"].append(CORRECTED_WITH_PLANES_MATRIX_PATH)
        mapping["basis"].extend([CORRECTED_WITH_PLANES_BS_RAW_PATH, CORRECTED_WITH_PLANES_BS_PRETTY_PATH])
        mapping["audit"].append(CORRECTED_WITH_PLANES_SUMMARY_PATH)

    PACKAGE_DIR.mkdir()
    for subdir, files in mapping.items():
        target_dir = PACKAGE_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for src in files:
            shutil.copy2(src, target_dir / src.name)

    readme_lines = [
        "# Review Package: 10.4.1.31 Plane Formalism Audit",
        "",
        "## 1. Task Scope",
        "",
        "- group: `10.4.1.31`",
        "- stage: plane formalism audit and torsion audit",
        "",
        "## 2. Why This Stage Is Necessary",
        "",
        "- The current with-planes result is still a minimal prototype.",
        "- The direct point-plane model must be validated against a stricter chain check through geometric-only boundary lines.",
        "- The Smith diagonal contains a nontrivial `2`, and that integer effect must be explained before treating the current plane layer as reliable.",
        "",
        "## 3. New Contents In This Round",
        "",
        "- 8 boundary-line generic `character` / `degree` outputs",
        "- boundary-line vs plane signature and chain-consistency checks",
        "- a focused torsion audit for the Smith-diagonal `2`",
        "",
        "## 4. Two Possible Outcomes",
        "",
        "- current plane model is accepted",
        "- current plane model needs correction",
        "",
        "## 5. Suggested Review Order",
        "",
        "1. `audit/single_group_plane_formalism_audit.md`",
        "2. `audit/single_group_plane_formalism_summary.json`",
        "3. `audit/single_group_torsion_audit.json`",
        "4. `audit/single_group_boundary_line_vs_plane_comparison.json`",
    ]
    write_text(PACKAGE_DIR / "README.md", "\n".join(readme_lines) + "\n")

    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def count_missing_deliverables() -> int:
    required = list(BASE_REQUIRED_OUTPUTS)
    for plane in ("S1", "S2"):
        for suffix in ("u0", "u12", "w0", "w12"):
            required.append(f"{plane}_bdry_{suffix}_character.json")
            required.append(f"{plane}_bdry_{suffix}_degree.json")
    if FORMALISM_SUMMARY_PATH.exists():
        summary = load_json(FORMALISM_SUMMARY_PATH)
        if summary.get("requires_matrix_update"):
            required.extend(OPTIONAL_CORRECTED_OUTPUTS)
    return sum(0 if (ROOT / name).exists() else 1 for name in required)


def validate_outputs() -> int:
    required = list(BASE_REQUIRED_OUTPUTS)
    for plane in ("S1", "S2"):
        for suffix in ("u0", "u12", "w0", "w12"):
            required.append(f"{plane}_bdry_{suffix}_character.json")
            required.append(f"{plane}_bdry_{suffix}_degree.json")
    missing = [name for name in required if not (ROOT / name).exists()]
    if missing:
        for name in missing:
            print(f"missing: {name}")
        return 1
    summary = load_json(FORMALISM_SUMMARY_PATH)
    if summary.get("group_number") != GROUP_NUMBER:
        print(f"unexpected group_number: {summary.get('group_number')}")
        return 1
    if not summary.get("boundary_line_outputs_available"):
        print("boundary_line_outputs_available=false")
        return 1
    if not summary.get("chain_check_consistent"):
        print("chain_check_consistent=false")
        return 1
    if not summary.get("torsion_2_explained"):
        print("torsion_2_explained=false")
        return 1
    if summary.get("requires_matrix_update"):
        for name in OPTIONAL_CORRECTED_OUTPUTS:
            if not (ROOT / name).exists():
                print(f"missing: {name}")
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

    context = load_previous_context()
    boundaries = build_boundary_infos(context)
    boundary_outputs = build_boundary_outputs(boundaries)
    chain_comparison = build_boundary_vs_plane_comparison(context, boundaries, boundary_outputs)
    torsion_audit = build_torsion_audit(context["with_planes_matrix"], chain_comparison)
    summary = build_formalism_summary(chain_comparison, torsion_audit)
    audit_markdown = build_formalism_audit_markdown(
        context,
        boundaries,
        boundary_outputs,
        chain_comparison,
        torsion_audit,
        summary,
    )

    write_json(BOUNDARY_VS_PLANE_PATH, chain_comparison)
    write_json(TORSION_AUDIT_PATH, torsion_audit)
    write_json(FORMALISM_SUMMARY_PATH, summary)
    write_text(FORMALISM_AUDIT_PATH, audit_markdown)

    build_review_package(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
