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

import debug_single_connection as single


ROOT = single.ROOT
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 1
LINE_IDS = ["L1", "L2", "L3", "L4"]
POINT_IDS = [f"P{i}" for i in range(1, 9)]
PACKAGE_DIR = ROOT / "review_package_10.4.1.31_full_compatibility"
PACKAGE_TAR = ROOT / "review_package_10.4.1.31_full_compatibility.tar.gz"
TMP_ROOT = ROOT / ".tmp_single_group_full_compatibility"

EXPECTED_BLOCK_ENDPOINTS = {
    "L1": ("P1", "P4"),
    "L2": ("P2", "P6"),
    "L3": ("P3", "P5"),
    "L4": ("P7", "P8"),
}

REQUIRED_OUTPUTS = [
    "single_group_full_compatibility_audit.md",
    "single_group_full_compatibility_summary.json",
    "single_group_full_compatibility.json",
    "single_group_raw_outputs_manifest.json",
    "L1_block.json",
    "L2_block.json",
    "L3_block.json",
    "L4_block.json",
    "debug_single_group_full_compatibility.py",
    "review_package_10.4.1.31_full_compatibility.tar.gz",
]


def parse_fraction(value: str) -> Fraction:
    return Fraction(value)


def frac_str(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def cli_str(value: Fraction) -> str:
    return format(float(value), ".12g")


def exact_k_from_object(obj: dict[str, Any]) -> list[str]:
    return list(obj["sample_point"])


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


def load_geometry_context() -> dict[str, Any]:
    manifolds = single.load_json(ROOT / "single_group_kmanifolds.json")
    connectivity = single.load_json(ROOT / "single_group_connectivity.json")
    objects = {item["id"]: item for item in manifolds["objects"]}
    point_line_edges = connectivity["point_line"]
    for point_id in POINT_IDS:
        if point_id not in objects:
            raise ValueError(f"missing point {point_id} in single_group_kmanifolds.json")
    blocks = []
    for line_id in LINE_IDS:
        if line_id not in objects:
            raise ValueError(f"missing line {line_id} in single_group_kmanifolds.json")
        line = objects[line_id]
        if line.get("manifold_role") != "separately_listed_special_line_manifold":
            raise ValueError(f"{line_id} is not marked as a separately listed special line manifold")
        edges = [edge for edge in point_line_edges if edge["line_id"] == line_id]
        if len(edges) != 2:
            raise ValueError(f"{line_id} should have exactly two point-line edges")
        left_edge = next((edge for edge in edges if edge["boundary_condition"] == "v = 0"), None)
        right_edge = next((edge for edge in edges if edge["boundary_condition"] == "v = 1/2"), None)
        if left_edge is None or right_edge is None:
            raise ValueError(f"{line_id} does not expose the expected endpoint boundary conditions")
        left_id = left_edge["point_id"]
        right_id = right_edge["point_id"]
        expected = EXPECTED_BLOCK_ENDPOINTS[line_id]
        if (left_id, right_id) != expected:
            raise ValueError(f"{line_id} endpoints {(left_id, right_id)} do not match expected {expected}")
        endpoint_map = {endpoint["boundary_condition"]: endpoint["point_id"] for endpoint in line["endpoints"]}
        if endpoint_map != {"v = 0": left_id, "v = 1/2": right_id}:
            raise ValueError(f"{line_id} endpoint metadata disagrees with point_line connectivity")
        left = objects[left_id]
        right = objects[right_id]
        block = {
            "left_point_id": left_id,
            "line_id": line_id,
            "right_point_id": right_id,
            "left_exact_k": exact_k_from_object(left),
            "line_exact_k": exact_k_from_object(line),
            "right_exact_k": exact_k_from_object(right),
            "left_cli_k": [cli_str(parse_fraction(value)) for value in exact_k_from_object(left)],
            "line_cli_k": [cli_str(parse_fraction(value)) for value in exact_k_from_object(line)],
            "right_cli_k": [cli_str(parse_fraction(value)) for value in exact_k_from_object(right)],
            "line_parametrization": line["parametrization"],
            "line_constraints": line["constraints"],
            "line_sample_point": line["sample_point"],
            "line_symmetry_summary": line["symmetry_summary"],
            "connectivity_edges": [left_edge, right_edge],
        }
        blocks.append(block)
    return {
        "objects": objects,
        "blocks": blocks,
        "point_line_edges": point_line_edges,
    }


def load_existing_or_generate_raw(manifold_id: str, exact_k: list[str], mode: str) -> dict[str, Any]:
    out_name = "character" if mode == "character" else "rep_degree"
    cmd, cli_k = build_command(exact_k, out_name)
    json_path, stdout_path = required_output_paths(manifold_id, mode)
    generated_this_run = False
    error = None
    if not json_path.exists():
        generated_this_run = True
        try:
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
                    raise RuntimeError(stdout_text.strip() or f"exit code {completed.returncode}")
                raw_output = tmp_path / "output.json"
                if not raw_output.exists():
                    raise FileNotFoundError(f"{raw_output} was not created")
                shutil.copyfile(raw_output, json_path)
        except Exception as exc:  # pragma: no cover - audit path
            error = str(exc)
    if error is None and json_path.exists():
        try:
            data = single.load_json(json_path)
            summary = single.summarize_raw_json(data)
        except Exception as exc:  # pragma: no cover - audit path
            error = f"failed to parse {json_path}: {exc}"
            summary = None
    else:
        summary = None
    result = {
        "manifold_id": manifold_id,
        "mode": mode,
        "command": " ".join(cmd),
        "json_path": str(json_path),
        "stdout_path": str(stdout_path),
        "exact_k": exact_k,
        "actual_cli_k": cli_k,
        "generated_this_run": generated_this_run,
        "success": error is None and summary is not None,
        "error": error,
    }
    if summary is not None:
        result.update(summary)
    return result


def collect_raw_outputs(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    unique_manifolds: dict[str, list[str]] = {}
    for block in blocks:
        unique_manifolds[block["left_point_id"]] = block["left_exact_k"]
        unique_manifolds[block["line_id"]] = block["line_exact_k"]
        unique_manifolds[block["right_point_id"]] = block["right_exact_k"]
    outputs: dict[str, Any] = {}
    for manifold_id, exact_k in unique_manifolds.items():
        outputs[manifold_id] = {}
        for mode in ("character", "degree"):
            outputs[manifold_id][mode] = load_existing_or_generate_raw(manifold_id, exact_k, mode)
    return outputs


def load_decoded_raw(manifold_id: str, mode: str) -> dict[str, Any]:
    raw = single.load_json(ROOT / f"{manifold_id}_{mode}.json")
    return single.decode_complex_json(raw)


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


def build_line_block(block: dict[str, Any], raw_manifest: dict[str, Any]) -> dict[str, Any]:
    line_id = block["line_id"]
    left_id = block["left_point_id"]
    right_id = block["right_point_id"]
    for manifold_id in (left_id, line_id, right_id):
        for mode in ("character", "degree"):
            if not raw_manifest[manifold_id][mode]["success"]:
                raise RuntimeError(f"{manifold_id} {mode} raw output is unavailable")

    line_raw = load_decoded_raw(line_id, "character")
    left_raw = load_decoded_raw(left_id, "character")
    right_raw = load_decoded_raw(right_id, "character")

    line_unitary_ops = [
        operation_key_from_raw(line_raw, op_index)
        for op_index, sign in enumerate(line_raw["timeReversal"])
        if sign > 0
    ]
    if len(line_unitary_ops) != len(line_raw["character"][0]):
        raise ValueError(f"{line_id} unitary operation count does not match character length")

    line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw["character"]) + 1)]
    line_basis_matrix = sp.Matrix(
        [
            [single.as_exact_char(value) for value in rep_character]
            for rep_character in line_raw["character"]
        ]
    ).T

    matched_operation_indices: dict[str, list[int]] = {}
    endpoint_decompositions: dict[str, Any] = {}
    endpoint_restrictions: dict[str, Any] = {}
    for endpoint_id, endpoint_raw in ((left_id, left_raw), (right_id, right_raw)):
        unitary_map = {
            operation_key_from_raw(endpoint_raw, op_index): unitary_index
            for unitary_index, (op_index, sign) in enumerate(
                item for item in enumerate(endpoint_raw["timeReversal"]) if item[1] > 0
            )
        }
        matched = [unitary_map.get(op_key) for op_key in line_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(f"{endpoint_id} does not contain the full {line_id} unitary subgroup")
        matched_operation_indices[endpoint_id] = [int(index) for index in matched]

        reps = []
        restrictions = []
        for rep_index, rep_character in enumerate(endpoint_raw["character"], start=1):
            restricted = sp.Matrix([single.as_exact_char(rep_character[index]) for index in matched])
            coeffs = list(line_basis_matrix.LUsolve(restricted))
            coeffs_int = coerce_integer_coeffs(coeffs, f"{endpoint_id} rep {rep_index} on {line_id}")
            restrictions.append([str(entry) for entry in restricted])
            reps.append(
                {
                    "rep_id": f"{endpoint_id}_R{rep_index}",
                    "rep_degree": int(endpoint_raw["repDegree"][rep_index - 1]),
                    "torsion": int(endpoint_raw["torsion"][rep_index - 1]),
                    "restricted_character_on_line_unitary_subgroup": [str(entry) for entry in restricted],
                    "decomposition_on_line_basis": {
                        basis_label: coeff
                        for basis_label, coeff in zip(line_basis_labels, coeffs_int)
                        if coeff
                    },
                }
            )
        endpoint_decompositions[endpoint_id] = reps
        endpoint_restrictions[endpoint_id] = restrictions

    local_unknown_ordering = [item["rep_id"] for item in endpoint_decompositions[left_id]] + [
        item["rep_id"] for item in endpoint_decompositions[right_id]
    ]
    equations = []
    matrix_rows = []
    for basis_label in line_basis_labels:
        row = []
        terms = []
        for item in endpoint_decompositions[left_id]:
            coeff = item["decomposition_on_line_basis"].get(basis_label, 0)
            row.append(coeff)
            if coeff:
                terms.append({"unknown": item["rep_id"], "coeff": coeff, "side": "left"})
        for item in endpoint_decompositions[right_id]:
            coeff = -item["decomposition_on_line_basis"].get(basis_label, 0)
            row.append(coeff)
            if coeff:
                terms.append({"unknown": item["rep_id"], "coeff": coeff, "side": "right"})
        left_expr = " + ".join(
            f"{term['coeff']}*{term['unknown']}" for term in terms if term["side"] == "left"
        )
        right_expr = " + ".join(
            f"{-term['coeff']}*{term['unknown']}" for term in terms if term["side"] == "right"
        )
        equation = f"{left_expr} = {right_expr}"
        equations.append(
            {
                "basis_id": basis_label,
                "terms": terms,
                "equation": equation,
            }
        )
        matrix_rows.append(row)

    line_group_signature = {
        "n_ops_total": len(line_raw["rotC"]),
        "n_unitary_ops": sum(1 for sign in line_raw["timeReversal"] if sign > 0),
        "n_antiunitary_ops": sum(1 for sign in line_raw["timeReversal"] if sign < 0),
        "rep_degree": [int(value) for value in line_raw["repDegree"]],
        "torsion": [int(value) for value in line_raw["torsion"]],
        "basis_characters": [
            [str(single.as_exact_char(value)) for value in rep_character]
            for rep_character in line_raw["character"]
        ],
    }

    return {
        "group_number": GROUP_NUMBER,
        "status": "success",
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
        "line_symmetry_summary": block["line_symmetry_summary"],
        "line_group_signature": line_group_signature,
        "line_unitary_basis": [
            {"basis_id": basis_id, "character": character}
            for basis_id, character in zip(line_basis_labels, line_group_signature["basis_characters"])
        ],
        "matched_unitary_operation_indices": matched_operation_indices,
        "endpoint_decompositions": endpoint_decompositions,
        "endpoint_restrictions": endpoint_restrictions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "raw_files": {
            manifold_id: {
                "character": raw_manifest[manifold_id]["character"]["json_path"],
                "degree": raw_manifest[manifold_id]["degree"]["json_path"],
            }
            for manifold_id in (left_id, line_id, right_id)
        },
    }


def build_failed_block(block: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "status": "failed",
        "left_point_id": block["left_point_id"],
        "line_id": block["line_id"],
        "right_point_id": block["right_point_id"],
        "left_exact_k": block["left_exact_k"],
        "line_exact_k": block["line_exact_k"],
        "right_exact_k": block["right_exact_k"],
        "line_parametrization": block["line_parametrization"],
        "line_constraints": block["line_constraints"],
        "line_sample_point": block["line_sample_point"],
        "error": error,
    }


def canonical_basis_set(block: dict[str, Any]) -> list[tuple[str, ...]]:
    return sorted(tuple(entry["character"]) for entry in block["line_unitary_basis"])


def canonical_local_matrix(block: dict[str, Any]) -> list[tuple[int, ...]]:
    return sorted(tuple(row) for row in block["matrix_rows"])


def canonical_endpoint_patterns(block: dict[str, Any]) -> dict[str, list[tuple[str, ...]]]:
    result: dict[str, list[tuple[str, ...]]] = {}
    for endpoint_id, reps in block["endpoint_decompositions"].items():
        patterns = []
        for rep in reps:
            items = tuple(sorted(f"{key}:{value}" for key, value in rep["decomposition_on_line_basis"].items()))
            patterns.append(items)
        result[endpoint_id] = sorted(patterns)
    return result


def build_consistency_report(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [block for block in blocks if block["status"] == "success"]
    report = {
        "all_blocks_successful": len(successful) == len(blocks),
        "successful_block_count": len(successful),
        "line_group_signatures": {
            block["line_id"]: block["line_group_signature"] for block in successful
        },
        "same_line_group_type": False,
        "same_basis_size": False,
        "same_canonical_matrix_pattern": False,
        "same_endpoint_decomposition_patterns": False,
        "notes": [],
    }
    if not successful:
        report["notes"].append("No successful line blocks were available for consistency checking.")
        return report
    basis_sets = [canonical_basis_set(block) for block in successful]
    basis_sizes = [len(block["line_unitary_basis"]) for block in successful]
    matrix_patterns = [canonical_local_matrix(block) for block in successful]
    endpoint_patterns = [
        {
            "left": canonical_endpoint_patterns(block)[block["left_point_id"]],
            "right": canonical_endpoint_patterns(block)[block["right_point_id"]],
        }
        for block in successful
    ]
    line_group_signatures = [json.dumps(block["line_group_signature"], sort_keys=True) for block in successful]
    report["same_line_group_type"] = len(set(line_group_signatures)) == 1
    report["same_basis_size"] = len(set(basis_sizes)) == 1
    report["same_canonical_matrix_pattern"] = len({tuple(pattern) for pattern in matrix_patterns}) == 1
    report["same_endpoint_decomposition_patterns"] = len(
        {json.dumps(pattern, sort_keys=True) for pattern in endpoint_patterns}
    ) == 1

    if report["same_line_group_type"]:
        report["notes"].append("All four explicit special lines have the same generic little-group type and basis character set.")
    else:
        report["notes"].append("At least one explicit special line has a different little-group signature.")
    if report["same_canonical_matrix_pattern"] and report["same_endpoint_decomposition_patterns"]:
        report["notes"].append("The four line blocks are symmetry-equivalent copies of the same local compatibility pattern.")
    else:
        report["notes"].append("At least one line block differs in local matrix/decomposition pattern and needs separate inspection.")
    return report


def build_global_unknown_ordering(blocks: list[dict[str, Any]]) -> list[str]:
    per_point_ids: dict[str, list[str]] = {}
    for block in blocks:
        if block["status"] != "success":
            continue
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


def build_global_compatibility(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [block for block in blocks if block["status"] == "success"]
    global_unknown_ordering = build_global_unknown_ordering(successful)
    unknown_index = {unknown: index for index, unknown in enumerate(global_unknown_ordering)}
    global_equations = []
    global_rows = []
    for block in successful:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(global_unknown_ordering)
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
        "global_unknown_ordering": global_unknown_ordering,
        "global_equations": global_equations,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
    }


def build_raw_outputs_manifest(blocks: list[dict[str, Any]], raw_manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "blocks": [
            {
                "line_id": block["line_id"],
                "left_point_id": block["left_point_id"],
                "right_point_id": block["right_point_id"],
                "raw_ids": [block["left_point_id"], block["line_id"], block["right_point_id"]],
            }
            for block in blocks
        ],
        "manifolds": raw_manifest,
    }


def build_summary(
    blocks: list[dict[str, Any]],
    consistency: dict[str, Any],
    global_compatibility: dict[str, Any] | None,
) -> dict[str, Any]:
    successful = [block for block in blocks if block["status"] == "success"]
    can_proceed = len(successful) == len(blocks) and global_compatibility is not None
    next_blocker = None
    if not can_proceed:
        failures = [f"{block['line_id']}: {block.get('error', 'unknown failure')}" for block in blocks if block["status"] != "success"]
        next_blocker = "; ".join(failures) or "global compatibility assembly failed"
    else:
        next_blocker = "Plane-level representation theory and any later AI/EBR steps are outside the current run."
    return {
        "group_number": GROUP_NUMBER,
        "covered_lines": LINE_IDS,
        "global_unknown_ordering": global_compatibility["global_unknown_ordering"] if global_compatibility else [],
        "line_blocks": [
            {
                "line_id": block["line_id"],
                "left_point_id": block["left_point_id"],
                "right_point_id": block["right_point_id"],
                "basis_size": len(block.get("line_unitary_basis", [])),
                "local_matrix_shape": [
                    len(block.get("matrix_rows", [])),
                    len(block.get("local_unknown_ordering", [])),
                ],
                "success": block["status"] == "success",
                "error": block.get("error"),
            }
            for block in blocks
        ],
        "consistency": consistency,
        "global_matrix_shape": [
            len(global_compatibility["global_matrix"]) if global_compatibility else 0,
            len(global_compatibility["global_unknown_ordering"]) if global_compatibility else 0,
        ],
        "can_proceed_to_next_stage": can_proceed,
        "next_blocker": next_blocker,
    }


def build_audit_markdown(
    geometry: dict[str, Any],
    raw_manifest: dict[str, Any],
    blocks: list[dict[str, Any]],
    consistency: dict[str, Any],
    global_compatibility: dict[str, Any] | None,
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Single Group Full Compatibility Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- This run only covers the explicit special-line compatibility layer.",
        f"- Covered lines: `{', '.join(LINE_IDS)}`",
        "- Not covered: plane representation theory, geometric boundary lines, all-group generalization, AI/EBR/BS classification.",
        "",
        "## Reuse From The Single-Connection Prototype",
        "- Reused directly:",
        "  - raw `SSGReps.py` CLI calling convention",
        "  - exact-k to CLI-float bookkeeping",
        "  - unitary-subgroup operation matching",
        "  - restriction/decomposition using the internal JSON `character` field",
        "- Previously hard-coded for `L1` and generalized only within this single group:",
        "  - one line block -> loop over `L1-L4`",
        "  - one endpoint pair -> geometry-driven endpoint lookup from `single_group_connectivity.json`",
        "  - one local block -> four local blocks plus one global matrix assembly",
        "- Still intentionally not generalized to high-throughput or all-group infrastructure.",
        "",
        "## Geometry Verification",
    ]
    for block in geometry["blocks"]:
        lines.append(
            f"- `{block['left_point_id']} -- {block['line_id']} -- {block['right_point_id']}`: "
            f"`{block['line_parametrization']}`, constraints `{', '.join(block['line_constraints'])}`, "
            f"sample point `({', '.join(block['line_sample_point'])})`"
        )
    lines.extend(
        [
            "",
            "## Raw Output Status",
        ]
    )
    for manifold_id in sorted(raw_manifest.keys(), key=lambda item: (item[0], int(item[1:]))):
        char_info = raw_manifest[manifold_id]["character"]
        deg_info = raw_manifest[manifold_id]["degree"]
        lines.append(
            f"- `{manifold_id}`: character=`{'ok' if char_info['success'] else 'fail'}`, "
            f"degree=`{'ok' if deg_info['success'] else 'fail'}`, exact_k=`({', '.join(char_info['exact_k'])})`, "
            f"cli_k=`({', '.join(char_info['actual_cli_k'])})`"
        )
    lines.extend(
        [
            "",
            "## Per-Line Block Status",
        ]
    )
    for block in blocks:
        if block["status"] == "success":
            lines.append(
                f"- `{block['line_id']}` succeeded: endpoints `{block['left_point_id']}` / `{block['right_point_id']}`, "
                f"basis size `{len(block['line_unitary_basis'])}`, local matrix shape "
                f"`{len(block['matrix_rows'])} x {len(block['local_unknown_ordering'])}`"
            )
        else:
            lines.append(f"- `{block['line_id']}` failed: `{block['error']}`")
    lines.extend(
        [
            "",
            "## Consistency Checks",
            f"- All blocks successful: `{consistency['all_blocks_successful']}`",
            f"- Same line-group type: `{consistency['same_line_group_type']}`",
            f"- Same basis size: `{consistency['same_basis_size']}`",
            f"- Same canonical matrix pattern: `{consistency['same_canonical_matrix_pattern']}`",
            f"- Same endpoint decomposition patterns: `{consistency['same_endpoint_decomposition_patterns']}`",
        ]
    )
    for note in consistency["notes"]:
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Coverage",
            "- Constructed here:",
            "  - four explicit special-line endpoint-line-endpoint blocks",
            "  - the single-group global compatibility matrix assembled from those four line blocks",
            "- Not constructed here:",
            "  - any plane-level compatibility",
            "  - any compatibility induced from geometric-only boundary lines",
            "  - any full BS / AI / EBR result",
            "",
            "## Outcome",
            f"- Current line-level matrix available: `{global_compatibility is not None}`",
            f"- Global matrix shape: `{summary['global_matrix_shape'][0]} x {summary['global_matrix_shape'][1]}`",
            f"- can_proceed_to_next_stage: `{summary['can_proceed_to_next_stage']}`",
            f"- next_blocker: `{summary['next_blocker']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_review_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()

    mapping = {
        "audit": [
            "single_group_full_compatibility_audit.md",
            "single_group_full_compatibility_summary.json",
            "single_connection_audit.md",
            "single_connection_summary.json",
            "single_connection_compatibility.json",
        ],
        "blocks": ["L1_block.json", "L2_block.json", "L3_block.json", "L4_block.json"],
        "global": [
            "single_group_full_compatibility.json",
            "single_group_raw_outputs_manifest.json",
        ],
        "geometry": [
            "single_group_kmanifolds.json",
            "single_group_connectivity.json",
        ],
        "scripts": [
            "debug_single_group_full_compatibility.py",
            "debug_single_connection.py",
            "kgeometry_single.py",
            "demo_single_group.py",
        ],
        "raw_outputs": [],
        "dependencies/SSGReps": [
            "SSGReps/SSGReps/SSGReps.py",
            "SSGReps/SSGReps/SG_utils.py",
            "SSGReps/SSGReps/rep_utils.py",
        ],
        "dependencies/geometry": ["swyckoff_k.py"],
    }
    for manifold_id in POINT_IDS + LINE_IDS:
        for mode in ("character", "degree"):
            filename = f"{manifold_id}_{mode}.json"
            if (ROOT / filename).exists():
                mapping["raw_outputs"].append(filename)

    PACKAGE_DIR.mkdir()
    for subdir, files in mapping.items():
        target_dir = PACKAGE_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for rel in files:
            src = ROOT / rel
            if src.exists():
                shutil.copy2(src, target_dir / src.name)

    readme = PACKAGE_DIR / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Review Package: 10.4.1.31 Full Explicit Special-Line Compatibility",
                "",
                "## Scope",
                "",
                "- Group: `10.4.1.31`",
                "- Layer: explicit special-line compatibility",
                "- Covered lines: `L1`, `L2`, `L3`, `L4`",
                "",
                "## Included Contents",
                "",
                "- Four single-line block files: `L1_block.json` to `L4_block.json`",
                "- One assembled single-group compatibility matrix: `single_group_full_compatibility.json`",
                "- One raw-output manifest: `single_group_raw_outputs_manifest.json`",
                "- The driving script: `debug_single_group_full_compatibility.py`",
                "- Background geometry and the earlier single-connection prototype artifacts",
                "",
                "## Not Included In Scope",
                "",
                "- Plane representation theory",
                "- Geometric-only boundary-line representation theory",
                "- AI / EBR / BS or topological classification",
                "- All-group or high-throughput generalization",
                "",
                "## Minimal Reading Order",
                "",
                "1. `audit/single_group_full_compatibility_audit.md`",
                "2. `audit/single_group_full_compatibility_summary.json`",
                "3. `global/single_group_full_compatibility.json`",
                "4. `blocks/L1_block.json` to `blocks/L4_block.json` if line-by-line detail is needed",
                "",
                "## Raw Outputs",
                "",
                "- `raw_outputs/` contains the point and line `character` / `degree` JSON payloads used by this run.",
                "- The package includes only JSON raw outputs, not terminal stdout logs.",
                "",
                "## External Dependency Note",
                "",
                "- `SSGReps/ssg_data/identify.pkl` is not bundled here.",
                "- The included scripts expect that database to exist in the local workspace when rerunning extraction.",
                "",
            ]
        )
        + "\n"
    )

    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def count_missing_deliverables() -> int:
    return sum(0 if (ROOT / name).exists() else 1 for name in REQUIRED_OUTPUTS)


def validate_outputs() -> int:
    missing = [name for name in REQUIRED_OUTPUTS if not (ROOT / name).exists()]
    if missing:
        for name in missing:
            print(f"missing: {name}")
        return 1
    summary = single.load_json(ROOT / "single_group_full_compatibility_summary.json")
    if not summary.get("can_proceed_to_next_stage"):
        print("summary indicates can_proceed_to_next_stage=false")
        return 1
    if summary.get("global_matrix_shape") != [10, 26]:
        print(f"unexpected global matrix shape: {summary.get('global_matrix_shape')}")
        return 1
    full = single.load_json(ROOT / "single_group_full_compatibility.json")
    if len(full.get("line_blocks", [])) != 4:
        print("single_group_full_compatibility.json does not contain four line blocks")
        return 1
    if len(full.get("global_matrix", [])) != 10:
        print("global matrix row count is not 10")
        return 1
    if len(full.get("global_unknown_ordering", [])) != 26:
        print("global unknown ordering length is not 26")
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

    geometry = load_geometry_context()
    raw_manifest = collect_raw_outputs(geometry["blocks"])

    blocks = []
    for block in geometry["blocks"]:
        try:
            built = build_line_block(block, raw_manifest)
        except Exception as exc:  # pragma: no cover - audit path
            built = build_failed_block(block, str(exc))
        blocks.append(built)

    consistency = build_consistency_report(blocks)
    global_compatibility = None
    if consistency["all_blocks_successful"]:
        global_payload = build_global_compatibility(blocks)
        global_compatibility = {
            "group_number": GROUP_NUMBER,
            "covered_lines": LINE_IDS,
            "line_blocks": blocks,
            **global_payload,
        }

    summary = build_summary(blocks, consistency, global_compatibility)
    raw_outputs_manifest = build_raw_outputs_manifest(geometry["blocks"], raw_manifest)
    audit_md = build_audit_markdown(
        geometry=geometry,
        raw_manifest=raw_manifest,
        blocks=blocks,
        consistency=consistency,
        global_compatibility=global_compatibility,
        summary=summary,
    )

    for block in blocks:
        (ROOT / f"{block['line_id']}_block.json").write_text(json.dumps(block, ensure_ascii=False, indent=2))
    (ROOT / "single_group_raw_outputs_manifest.json").write_text(
        json.dumps(raw_outputs_manifest, ensure_ascii=False, indent=2)
    )
    (ROOT / "single_group_full_compatibility_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    (ROOT / "single_group_full_compatibility_audit.md").write_text(audit_md)
    if global_compatibility is not None:
        (ROOT / "single_group_full_compatibility.json").write_text(
            json.dumps(global_compatibility, ensure_ascii=False, indent=2)
        )
    build_review_package()

    print(f"group_number: {GROUP_NUMBER}")
    print("line_block_status:")
    for block in blocks:
        print(f"  {block['line_id']}: {block['status']}")
    print(f"all_blocks_successful: {consistency['all_blocks_successful']}")
    print(f"same_line_group_type: {consistency['same_line_group_type']}")
    print(f"same_canonical_matrix_pattern: {consistency['same_canonical_matrix_pattern']}")
    if global_compatibility is not None:
        print(f"global_matrix_shape: {len(global_compatibility['global_matrix'])} x {len(global_compatibility['global_unknown_ordering'])}")
    else:
        print("global_matrix_shape: unavailable")
    print(f"review_package: {PACKAGE_TAR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
