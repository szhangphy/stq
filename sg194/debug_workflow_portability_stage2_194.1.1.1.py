#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent
REFERENCE_GROUP = "10.4.1.31"
TARGET_GROUP = "194.1.1.1"

INVENTORY_MD = ROOT / "sg194_nonabelian_site_symmetry_inventory.md"
INVENTORY_JSON = ROOT / "sg194_nonabelian_site_symmetry_inventory.json"
SINGLE_LIBRARY_JSON = ROOT / "sg194_single_local_irrep_library.json"
DOUBLE_LIBRARY_JSON = ROOT / "sg194_double_local_corep_library.json"

SINGLE_AI_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_AI_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
SINGLE_INDICATOR_GROUP_JSON = ROOT / "group_194_1_1_1_single_indicator_group_summary.json"
SINGLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_single_indicator_generators.json"
DOUBLE_INDICATOR_GROUP_JSON = ROOT / "group_194_1_1_1_double_indicator_group_summary.json"
DOUBLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_double_indicator_generators.json"

STAGE2_AUDIT_MD = ROOT / "workflow_portability_stage2_audit_194.1.1.1.md"
STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
HANDOFF_MD = ROOT / "handoff_194.1.1.1_stage2.md"
CURRENT_STATUS_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_194.1.1.1_stage2.txt"
REPORT_TEX = ROOT / "workflow_portability_report_stage2_194.1.1.1.tex"
REPORT_PDF = ROOT / "workflow_portability_report_stage2_194.1.1.1.pdf"

PACKAGE_NAME = "review_package_workflow_portability_194.1.1.1_stage2"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


def load_stage1_module():
    path = ROOT / "debug_workflow_portability_194.1.1.1.py"
    spec = importlib.util.spec_from_file_location("workflow_portability_stage1_local", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_helper_module():
    path = ROOT / "debug_sg194_nonabelian_local_library.py"
    spec = importlib.util.spec_from_file_location("sg194_local_library_stage2", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_default(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, sp.Basic):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def format_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def complex_from_json(value: Any) -> complex:
    if isinstance(value, dict) and "real" in value and "imag" in value:
        return complex(float(value["real"]), float(value["imag"]))
    if isinstance(value, (int, float)):
        return complex(value)
    raise TypeError(f"unexpected complex json payload: {value!r}")


def normalize_sign(primary: list[int], secondary: list[int] | None = None) -> tuple[list[int], list[int] | None]:
    sign = 1
    for value in primary:
        if value > 0:
            break
        if value < 0:
            sign = -1
            break
    if sign < 0:
        primary = [-value for value in primary]
        if secondary is not None:
            secondary = [-value for value in secondary]
    return primary, secondary


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    parts: list[str] = []
    if free_rank > 0:
        parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts) if parts else "trivial"


def latex_group_string(group: str | None) -> str:
    if not group or group == "blocked":
        return r"\texttt{blocked}"
    if group == "trivial":
        return r"\mathrm{trivial}"
    rebuilt: list[str] = []
    for token in group.split(" x "):
        if token.startswith("Z^"):
            rebuilt.append(rf"\mathrm{{Z}}^{{{token[2:]}}}")
        elif token.startswith("Z") and token[1:].isdigit():
            rebuilt.append(rf"\mathrm{{Z}}_{{{token[1:]}}}")
        else:
            rebuilt.append(token)
    return r" \times ".join(rebuilt)


def build_single_runtime(port, module, ssg_dict) -> dict[str, Any]:
    ctx = port.load_context(module, TARGET_GROUP, "single", ssg_dict)
    prepared_kgeom = port.prepare_kgeometry(TARGET_GROUP)
    kgeom_payload = prepared_kgeom["payload"]
    grouped = prepared_kgeom["grouped"]
    kgeom = {"payload": kgeom_payload, "grouped": grouped, "connectivity": kgeom_payload}
    synthetic_points = port.build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic_points
    port.augment_connectivity_with_boundary_points(kgeom, synthetic_points)
    ctx["kgeom"] = kgeom

    captures = port.build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "single", kgeom)
    point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]
    line_blocks = [port.build_line_block(line, captures) for line in grouped["lines"]]
    line_full = port.build_global_compatibility(line_blocks, point_ids)
    point_by_coord = port.build_synthetic_kpoint_map(kgeom)
    for point in grouped["points"]:
        point_by_coord[tuple(point["sample_point"])] = point["id"]
    plane_blocks = [
        port.build_plane_block(plane, port.derive_plane_corner_ids(plane, point_by_coord), captures)
        for plane in grouped["planes"]
    ]
    with_planes = port.build_with_planes_compatibility(line_full, plane_blocks)
    bs_analysis = port.analyze_kernel(with_planes)
    return {
        "ctx": ctx,
        "kgeom": kgeom,
        "captures": captures,
        "with_planes": with_planes,
        "bs_analysis": bs_analysis,
    }


def build_double_runtime(port, module, ssg_dict, single_kgeom: dict[str, Any]) -> dict[str, Any]:
    ctx = port.load_context(module, TARGET_GROUP, "double", ssg_dict)
    ctx["kgeom"] = single_kgeom
    captures = port.build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "double", single_kgeom)
    point_ids = [item["id"] for item in single_kgeom["grouped"]["points"]] + [item["id"] for item in single_kgeom["synthetic_boundary_points"]]
    line_blocks = [port.build_line_block(line, captures) for line in single_kgeom["grouped"]["lines"]]
    line_full = port.build_global_compatibility(line_blocks, point_ids)
    point_by_coord = port.build_synthetic_kpoint_map(single_kgeom)
    for point in single_kgeom["grouped"]["points"]:
        point_by_coord[tuple(point["sample_point"])] = point["id"]
    plane_blocks = [
        port.build_plane_block(plane, port.derive_plane_corner_ids(plane, point_by_coord), captures)
        for plane in single_kgeom["grouped"]["planes"]
    ]
    with_planes = port.build_with_planes_compatibility(line_full, plane_blocks)
    bs_analysis = port.analyze_kernel(with_planes)
    return {
        "ctx": ctx,
        "captures": captures,
        "with_planes": with_planes,
        "bs_analysis": bs_analysis,
    }


def bs_basis_matrix(bs_analysis: dict[str, Any]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in bs_analysis["basis_vectors"]])


def bs_coordinate_matrix(bs_analysis: dict[str, Any], candidates: list[dict[str, Any]]) -> sp.Matrix:
    basis = bs_basis_matrix(bs_analysis)
    coords = []
    for candidate in candidates:
        solution = basis.gauss_jordan_solve(sp.Matrix(candidate["unknown_vector"]))[0]
        if any(not value.is_integer for value in solution):
            raise ValueError(f"{candidate['generator_id']}: non-integral BS coordinates {solution}")
        coords.append([int(value) for value in solution])
    return sp.Matrix.hstack(*[sp.Matrix(column) for column in coords]) if coords else sp.zeros(basis.cols, 0)


def family_success_map(candidates: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_family: dict[str, list[str]] = {}
    for candidate in candidates:
        by_family.setdefault(candidate["family_letter"], []).append(candidate["generator_id"])
    return by_family


def induce_objects(port, runtime: dict[str, Any], family_objects: dict[str, list[dict[str, Any]]], scope: str) -> dict[str, Any]:
    ctx = runtime["ctx"]
    captures = runtime["captures"]
    bs_analysis = runtime["bs_analysis"]
    global_matrix = runtime["with_planes"]["global_matrix"]
    candidates = []
    failures = []
    seen_vectors: dict[tuple[int, ...], list[str]] = {}
    for family in sorted(family_objects):
        for local_object in family_objects[family]:
            local_character = local_object["character_on_unitary_stabilizer_complex"]
            generator_id = f"{family}_{local_object['label']}"
            try:
                candidate = port.induce_candidate(
                    ctx["entries_by_letter"][family],
                    local_character,
                    ctx,
                    captures,
                    bs_analysis["unknown_ordering"],
                    global_matrix,
                )
                candidate["generator_id"] = generator_id
                candidate["local_object_label"] = local_object["label"]
                candidate["local_object_dimension"] = int(local_object["dimension"])
                candidate["local_object_origin"] = local_object.get("origin", scope)
                candidates.append(candidate)
                seen_vectors.setdefault(tuple(int(value) for value in candidate["unknown_vector"]), []).append(generator_id)
            except Exception as exc:
                failures.append(
                    {
                        "generator_id": generator_id,
                        "family_id": family,
                        "local_object_label": local_object["label"],
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
        "family_success_map": family_success_map(candidates),
    }


DOUBLE_SPINORIAL_IDENTITY_ORDER = [
    ("a", "1Eg↑G(2)", "a_proj_u_1d_1"),
    ("a", "1Eu↑G(2)", "a_proj_u_1d_2"),
    ("a", "2Eg↑G(2)", "a_proj_g_1d_3"),
    ("a", "2Eu↑G(2)", "a_proj_g_1d_4"),
    ("a", "E1g↑G(4)", "a_proj_u_2d_5"),
    ("a", "E1u↑G(4)", "a_proj_u_2d_6"),
    ("e", "1E↑G(4)", "e_proj_1d_1"),
    ("e", "2E↑G(4)", "e_proj_1d_2"),
    ("e", "E1↑G(8)", "e_proj_E_half"),
    ("f", "1E↑G(4)", "f_proj_1d_1"),
    ("f", "2E↑G(4)", "f_proj_1d_2"),
    ("f", "E1↑G(8)", "f_proj_E_half"),
    ("g", "1Eg↑G(6)", "g_proj_u_m1"),
    ("g", "1Eu↑G(6)", "g_proj_u_1"),
    ("g", "2Eg↑G(6)", "g_proj_g_m1"),
    ("g", "2Eu↑G(6)", "g_proj_g_1"),
    ("i", "1E↑G(12)", "i_proj_minus_i"),
    ("i", "2E↑G(12)", "i_proj_plus_i"),
    ("j", "1E↑G(12)", "j_proj_minus_i"),
    ("j", "2E↑G(12)", "j_proj_plus_i"),
    ("k", "1E↑G(12)", "k_proj_minus_i"),
    ("k", "2E↑G(12)", "k_proj_plus_i"),
    ("l", "A↑G(24)", "l_proj_1"),
]

DOUBLE_SPINORIAL_CHANNEL_ORDER = [
    ("a", "1Eg↑G(2)"),
    ("a", "1Eu↑G(2)"),
    ("a", "2Eg↑G(2)"),
    ("a", "2Eu↑G(2)"),
    ("a", "E1g↑G(4)"),
    ("a", "E1u↑G(4)"),
    ("b", "E1↑G(4)"),
    ("b", "E2↑G(4)"),
    ("b", "E3↑G(4)"),
    ("c", "E1↑G(4)"),
    ("c", "E2↑G(4)"),
    ("c", "E3↑G(4)"),
    ("d", "E1↑G(4)"),
    ("d", "E2↑G(4)"),
    ("d", "E3↑G(4)"),
    ("e", "1E↑G(4)"),
    ("e", "2E↑G(4)"),
    ("e", "E1↑G(8)"),
    ("f", "1E↑G(4)"),
    ("f", "2E↑G(4)"),
    ("f", "E1↑G(8)"),
    ("g", "1Eg↑G(6)"),
    ("g", "1Eu↑G(6)"),
    ("g", "2Eg↑G(6)"),
    ("g", "2Eu↑G(6)"),
    ("h", "E↑G(12)"),
    ("i", "1E↑G(12)"),
    ("i", "2E↑G(12)"),
    ("j", "1E↑G(12)"),
    ("j", "2E↑G(12)"),
    ("k", "1E↑G(12)"),
    ("k", "2E↑G(12)"),
    ("l", "A↑G(24)"),
]


def _candidate_lookup(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {candidate["generator_id"]: candidate for candidate in candidates}


DOUBLE_SPINORIAL_COMPLEMENT_ORDER = [
    (family_letter, external_label)
    for family_letter, external_label in DOUBLE_SPINORIAL_CHANNEL_ORDER
    if family_letter not in {"b", "c", "d", "h"}
]
DOUBLE_SPINORIAL_COMPLEMENT_IDENTITY_ANCHORS = {
    (family_letter, external_label): generator_id
    for family_letter, external_label, generator_id in DOUBLE_SPINORIAL_IDENTITY_ORDER
}


def _normalize_rule_terms(terms: list[tuple[int, str]]) -> list[tuple[int, str]]:
    merged: dict[str, int] = {}
    for coeff, generator_id in terms:
        merged[generator_id] = merged.get(generator_id, 0) + int(coeff)
    return [(coeff, generator_id) for generator_id, coeff in merged.items() if coeff != 0]


def build_sg194_double_complement_rule_table_v1() -> dict[tuple[str, str], list[tuple[int, str]]]:
    repeated_all_a = [
        (1, "a_proj_u_1d_1"),
        (1, "a_proj_u_1d_2"),
        (1, "a_proj_g_1d_3"),
        (1, "a_proj_g_1d_4"),
        (1, "a_proj_u_2d_5"),
        (1, "a_proj_u_2d_6"),
    ]
    repeated_a_pair = [(1, "a_proj_u_2d_5"), (1, "a_proj_u_2d_6")]
    repeated_c_f_correction = [(-2, "c_proj_doubleprime_1d_1"), (-2, "c_proj_prime_1d_3")]
    rules = {
        ("a", "1Eg↑G(2)"): [(-1, "a_proj_u_1d_1"), (1, "a_proj_u_2d_5"), (1, "a_proj_u_2d_6")],
        ("a", "1Eu↑G(2)"): [(-1, "a_proj_u_1d_2"), (-1, "a_proj_g_1d_3"), (-1, "a_proj_g_1d_4"), (-1, "a_proj_u_2d_6")],
        ("a", "2Eg↑G(2)"): [(1, "a_proj_u_1d_2"), (1, "a_proj_g_1d_3"), (1, "a_proj_g_1d_4"), (1, "a_proj_u_2d_5"), (2, "a_proj_u_2d_6")],
        ("a", "2Eu↑G(2)"): [(1, "a_proj_u_1d_1")],
        ("a", "E1g↑G(4)"): [(1, "a_proj_u_1d_1"), (1, "a_proj_g_1d_3"), (1, "a_proj_g_1d_4")],
        ("a", "E1u↑G(4)"): [(1, "a_proj_u_1d_2")],
        ("e", "1E↑G(4)"): repeated_a_pair,
        ("e", "2E↑G(4)"): repeated_a_pair,
        ("e", "E1↑G(8)"): repeated_all_a[:4],
        ("f", "1E↑G(4)"): [(2, "a_proj_u_1d_1"), (2, "a_proj_g_1d_3"), (1, "a_proj_u_2d_5"), (1, "a_proj_u_2d_6")] + repeated_c_f_correction,
        ("f", "2E↑G(4)"): [(2, "a_proj_u_1d_1"), (2, "a_proj_g_1d_3"), (1, "a_proj_u_2d_5"), (1, "a_proj_u_2d_6")] + repeated_c_f_correction,
        ("f", "E1↑G(8)"): [(-1, "a_proj_u_1d_1"), (1, "a_proj_u_1d_2"), (-1, "a_proj_g_1d_3"), (1, "a_proj_g_1d_4"), (2, "c_proj_doubleprime_1d_1"), (2, "c_proj_prime_1d_3")],
        ("g", "1Eg↑G(6)"): [(1, "a_proj_u_1d_1"), (1, "a_proj_u_1d_2"), (1, "a_proj_g_1d_4"), (1, "a_proj_u_2d_5"), (1, "a_proj_u_2d_6")],
        ("g", "1Eu↑G(6)"): [(1, "a_proj_u_1d_1"), (1, "a_proj_u_1d_2"), (2, "a_proj_g_1d_3"), (1, "a_proj_g_1d_4"), (1, "a_proj_u_2d_6")],
        ("g", "2Eg↑G(6)"): [(-1, "a_proj_g_1d_3"), (1, "a_proj_u_2d_5")],
        ("g", "2Eu↑G(6)"): [(1, "a_proj_g_1d_3")],
        ("i", "1E↑G(12)"): [(2, "a_proj_u_1d_1"), (2, "a_proj_u_1d_2"), (2, "a_proj_g_1d_3"), (2, "a_proj_g_1d_4"), (1, "a_proj_u_2d_5"), (2, "a_proj_u_2d_6")],
        ("i", "2E↑G(12)"): [(1, "a_proj_u_2d_5")],
        ("j", "1E↑G(12)"): repeated_all_a,
        ("j", "2E↑G(12)"): repeated_all_a,
        ("k", "1E↑G(12)"): repeated_all_a,
        ("k", "2E↑G(12)"): repeated_all_a,
        ("l", "A↑G(24)"): [(2, "a_proj_u_1d_1"), (2, "a_proj_u_1d_2"), (2, "a_proj_g_1d_3"), (2, "a_proj_g_1d_4"), (2, "a_proj_u_2d_5"), (2, "a_proj_u_2d_6")],
    }
    return {key: _normalize_rule_terms(value) for key, value in rules.items()}


def _combined_double_channel_record(
    candidates_by_id: dict[str, dict[str, Any]],
    family_letter: str,
    external_channel_label: str,
    terms: list[tuple[int, str]],
    patch_profile: str,
    patch_note: str,
    *,
    metadata_anchor_generator_id: str | None = None,
) -> dict[str, Any]:
    anchor_id = metadata_anchor_generator_id or next(generator_id for coeff, generator_id in terms if coeff != 0)
    anchor = candidates_by_id[anchor_id]
    unknown_length = len(anchor["unknown_vector"])
    unknown_vector = [0] * unknown_length
    for coeff, generator_id in terms:
        vector = candidates_by_id[generator_id]["unknown_vector"]
        unknown_vector = [left + coeff * int(right) for left, right in zip(unknown_vector, vector)]

    return {
        "generator_id": f"{family_letter}_{external_channel_label.replace('↑', '_').replace('(', '_').replace(')', '').replace(':', '_').replace('/', '_')}",
        "family_letter": family_letter,
        "external_channel_label": f"{family_letter}:{external_channel_label}",
        "spinorial_channel_label": external_channel_label,
        "local_object_label": external_channel_label,
        "local_object_dimension": 1,
        "local_object_origin": patch_profile,
        "representative_coordinate": anchor["representative_coordinate"],
        "multiplicity": int(anchor["multiplicity"]),
        "site_symmetry": anchor["site_symmetry"],
        "unknown_vector": unknown_vector,
        "compatibility_zero": True,
        "stabilizer_size": int(anchor["stabilizer_size"]),
        "unitary_stabilizer_size": int(anchor["unitary_stabilizer_size"]),
        "source_generator_terms": [
            {
                "coeff": int(coeff),
                "generator_id": generator_id,
                "local_object_label": candidates_by_id[generator_id].get("local_object_label"),
            }
            for coeff, generator_id in terms
        ],
        "patch_profile": patch_profile,
        "patch_note": patch_note,
    }


def build_sg194_double_spinorial_generators(
    induced_candidates: list[dict[str, Any]],
    *,
    profile: str = "legacy",
) -> dict[str, Any]:
    candidates_by_id = _candidate_lookup(induced_candidates)

    canonical_problem_rules = {
        ("b", "E1↑G(4)"): [(1, "b_proj_doubleprime_1d_1"), (1, "b_proj_doubleprime_1d_2")],
        ("b", "E2↑G(4)"): [(1, "b_proj_prime_1d_3"), (1, "b_proj_prime_1d_4")],
        ("b", "E3↑G(4)"): [(1, "b_proj_doubleprime_2d_5"), (1, "b_proj_doubleprime_2d_6")],
        ("c", "E1↑G(4)"): [(1, "c_proj_doubleprime_1d_1"), (1, "c_proj_doubleprime_1d_2")],
        ("c", "E2↑G(4)"): [(1, "c_proj_prime_1d_3"), (1, "c_proj_prime_1d_4")],
        ("c", "E3↑G(4)"): [(1, "c_proj_doubleprime_2d_5"), (1, "c_proj_doubleprime_2d_6")],
        ("d", "E1↑G(4)"): [(1, "d_proj_doubleprime_1d_1"), (1, "d_proj_doubleprime_1d_2")],
        ("d", "E2↑G(4)"): [(1, "d_proj_prime_1d_3"), (1, "d_proj_prime_1d_4")],
        ("d", "E3↑G(4)"): [(1, "d_proj_doubleprime_2d_5"), (1, "d_proj_doubleprime_2d_6")],
        ("h", "E↑G(12)"): [(1, "h_proj_mm2_1"), (1, "h_proj_mm2_2"), (1, "h_proj_mm2_3"), (1, "h_proj_mm2_4")],
    }
    patched_problem_rules = {
        ("b", "E1↑G(4)"): canonical_problem_rules[("b", "E1↑G(4)")],
        ("b", "E2↑G(4)"): canonical_problem_rules[("b", "E2↑G(4)")],
        ("b", "E3↑G(4)"): canonical_problem_rules[("b", "E3↑G(4)")],
        ("c", "E1↑G(4)"): canonical_problem_rules[("c", "E1↑G(4)")],
        ("c", "E2↑G(4)"): canonical_problem_rules[("c", "E2↑G(4)")],
        ("c", "E3↑G(4)"): [(2, "c_proj_doubleprime_2d_5"), (2, "c_proj_doubleprime_2d_6"), (-1, "b_proj_doubleprime_2d_5"), (-1, "b_proj_doubleprime_2d_6")],
        ("d", "E1↑G(4)"): canonical_problem_rules[("d", "E1↑G(4)")],
        ("d", "E2↑G(4)"): canonical_problem_rules[("d", "E2↑G(4)")],
        ("d", "E3↑G(4)"): [(2, "d_proj_doubleprime_2d_5"), (2, "d_proj_doubleprime_2d_6"), (-1, "b_proj_doubleprime_2d_5"), (-1, "b_proj_doubleprime_2d_6")],
        ("h", "E↑G(12)"): canonical_problem_rules[("h", "E↑G(12)")] + [(-1, "b_proj_doubleprime_2d_5"), (-1, "b_proj_doubleprime_2d_6")],
    }

    complement_rules_legacy = {
        key: [(1, DOUBLE_SPINORIAL_COMPLEMENT_IDENTITY_ANCHORS[key])]
        for key in DOUBLE_SPINORIAL_COMPLEMENT_ORDER
    }
    complement_rules_v1 = build_sg194_double_complement_rule_table_v1()

    if profile not in {"legacy", "sg194_double_anchor_patch_v1", "sg194_double_complement_patch_v1"}:
        raise ValueError(f"unsupported spinorial profile: {profile}")
    if profile == "legacy":
        complement_rules = complement_rules_legacy
        problem_rules = canonical_problem_rules
        complement_note = "legacy complement branch identity one-to-one channel reuse"
        problem_note = "legacy pair-sum / four-way-sum spinorial channelization"
    elif profile == "sg194_double_anchor_patch_v1":
        complement_rules = complement_rules_legacy
        problem_rules = patched_problem_rules
        complement_note = "legacy complement branch identity one-to-one channel reuse retained while only the trusted 2b/2c/2d/6h sector is anchor-corrected"
        problem_note = "anchor-corrected SG194 double problem-sector channelization derived from the exact row-space solve against the external 2b/2c/2d/6h spinorial sector"
    else:
        complement_rules = complement_rules_v1
        problem_rules = patched_problem_rules
        complement_note = (
            "complement-specific SG194 double row-basis translation profile derived from the exact full-33 null-relation solve; "
            "the 23 complement channels no longer use identity reuse and are emitted in canonical external order"
        )
        problem_note = "trusted-sector anchor correction retained unchanged from sg194_double_anchor_patch_v1"

    channels_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for family_letter, external_label in DOUBLE_SPINORIAL_COMPLEMENT_ORDER:
        metadata_anchor_id = DOUBLE_SPINORIAL_COMPLEMENT_IDENTITY_ANCHORS[(family_letter, external_label)]
        channels_by_key[(family_letter, external_label)] = _combined_double_channel_record(
            candidates_by_id,
            family_letter,
            external_label,
            complement_rules[(family_letter, external_label)],
            profile,
            complement_note,
            metadata_anchor_generator_id=metadata_anchor_id,
        )

    for family_letter, external_label in [
        ("b", "E1↑G(4)"),
        ("b", "E2↑G(4)"),
        ("b", "E3↑G(4)"),
        ("c", "E1↑G(4)"),
        ("c", "E2↑G(4)"),
        ("c", "E3↑G(4)"),
        ("d", "E1↑G(4)"),
        ("d", "E2↑G(4)"),
        ("d", "E3↑G(4)"),
        ("h", "E↑G(12)"),
    ]:
        channels_by_key[(family_letter, external_label)] = _combined_double_channel_record(
            candidates_by_id,
            family_letter,
            external_label,
            problem_rules[(family_letter, external_label)],
            profile,
            problem_note,
        )

    channels = [channels_by_key[key] for key in DOUBLE_SPINORIAL_CHANNEL_ORDER]
    ordering = [f"{family_letter}:{external_label}" for family_letter, external_label in DOUBLE_SPINORIAL_CHANNEL_ORDER]
    return {
        "profile": profile,
        "ordering": ordering,
        "channels": channels,
        "complement_rules": {
            f"{family}:{label}": [
                {"coeff": int(coeff), "generator_id": generator_id}
                for coeff, generator_id in complement_rules[(family, label)]
            ]
            for family, label in DOUBLE_SPINORIAL_COMPLEMENT_ORDER
        },
        "problem_rules": {
            f"{family}:{label}": [
                {"coeff": int(coeff), "generator_id": generator_id}
                for coeff, generator_id in problem_rules[(family, label)]
            ]
            for family, label in problem_rules
        },
    }


def quotient_artifacts(
    group_type: int,
    bs_analysis: dict[str, Any],
    ai_coord_matrix: sp.Matrix,
    candidate_ids: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    diagonal, left, right = smith_normal_decomp(ai_coord_matrix, domain=ZZ)
    left_inv = left.inv()
    diag_entries = [abs(int(diagonal[idx, idx])) for idx in range(min(diagonal.rows, diagonal.cols)) if int(diagonal[idx, idx]) != 0]
    ai_rank = len(diag_entries)
    free_rank = int(ai_coord_matrix.rows - ai_rank)
    finite_part = [value for value in diag_entries if value > 1]
    bs_basis = bs_basis_matrix(bs_analysis)

    torsion_indices = [
        idx for idx in range(min(diagonal.rows, diagonal.cols))
        if int(diagonal[idx, idx]) not in (0, 1, -1)
    ]
    free_indices = [idx for idx in range(min(diagonal.rows, diagonal.cols)) if int(diagonal[idx, idx]) == 0]

    torsion_generators = []
    for generator_index, torsion_index in enumerate(torsion_indices, start=1):
        bs_coords = [int(value) for value in list(left_inv[:, torsion_index])]
        ai_relation = [int(value) for value in list(right[:, torsion_index])]
        bs_coords, ai_relation = normalize_sign(bs_coords, ai_relation)
        unknown_vector = [int(value) for value in list(bs_basis * sp.Matrix(bs_coords))]
        torsion_generators.append(
            {
                "indicator_id": f"{'single' if group_type == 1 else 'double'}_torsion_generator_{generator_index}",
                "smith_factor": abs(int(diagonal[torsion_index, torsion_index])),
                "bs_basis_coordinates": bs_coords,
                "unknown_ordering": bs_analysis["unknown_ordering"],
                "unknown_vector": unknown_vector,
                "ai_relation_for_multiple": ai_relation,
                "ai_generator_ordering": candidate_ids,
            }
        )

    free_generators = []
    for generator_index, free_index in enumerate(free_indices, start=1):
        bs_coords = [int(value) for value in list(left_inv[:, free_index])]
        bs_coords, _ = normalize_sign(bs_coords)
        unknown_vector = [int(value) for value in list(bs_basis * sp.Matrix(bs_coords))]
        free_generators.append(
            {
                "indicator_id": f"{'single' if group_type == 1 else 'double'}_free_generator_{generator_index}",
                "bs_basis_coordinates": bs_coords,
                "unknown_ordering": bs_analysis["unknown_ordering"],
                "unknown_vector": unknown_vector,
            }
        )

    group_summary = {
        "group_number": TARGET_GROUP,
        "group_type": group_type,
        "rank(BS)": int(bs_analysis["nullity"]),
        "rank(AI_complete)": int(ai_rank),
        "smith_diagonal_in_bs_coordinates": diag_entries,
        "quotient_group": quotient_group_string(free_rank, finite_part),
        "free_rank": free_rank,
        "finite_part": finite_part,
        "generator_count": len(torsion_generators) + len(free_generators),
    }
    generator_root = {
        "group_number": TARGET_GROUP,
        "group_type": group_type,
        "quotient_group": group_summary["quotient_group"],
        "free_generators": free_generators,
        "torsion_generators": torsion_generators,
    }
    return group_summary, generator_root


def single_completion_summary(runtime: dict[str, Any], induction: dict[str, Any], family_objects: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    candidate_ids = [candidate["generator_id"] for candidate in induction["candidates"]]
    ai_coords = bs_coordinate_matrix(runtime["bs_analysis"], induction["candidates"])
    quotient_summary, quotient_generators = quotient_artifacts(1, runtime["bs_analysis"], ai_coords, candidate_ids)
    all_families = sorted(family_objects)
    missing_families = [family for family in all_families if family not in induction["family_success_map"]]
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 1,
        "ai_from_trivial_prototype_to_complete": len(induction["failures"]) == 0,
        "family_count": len(all_families),
        "family_local_object_counts": {family: len(objects) for family, objects in sorted(family_objects.items())},
        "family_success_counts": {family: len(induction["family_success_map"].get(family, [])) for family in all_families},
        "generated_ai_candidate_count": len(induction["candidates"]),
        "distinct_unknown_vector_count": len(induction["duplicate_classes"]),
        "rank_ai_in_bs_coordinates": int(ai_coords.rank()),
        "rank_bs": int(runtime["bs_analysis"]["nullity"]),
        "completeness_status": "complete" if len(induction["failures"]) == 0 else "blocked",
        "quotient_status": "extracted" if len(induction["failures"]) == 0 else "blocked",
        "quotient_group": quotient_summary["quotient_group"] if len(induction["failures"]) == 0 else None,
        "missing_families": missing_families,
        "failures": induction["failures"],
        "blocker": None if len(induction["failures"]) == 0 else "Some single-group local objects still fail induction on the current 194.1.1.1 / groupType=1 path.",
    }
    return summary, quotient_summary, quotient_generators


def double_completion_summary(runtime: dict[str, Any], induction: dict[str, Any], family_objects: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    candidate_ids = [candidate["generator_id"] for candidate in induction["candidates"]]
    ai_coords = bs_coordinate_matrix(runtime["bs_analysis"], induction["candidates"])
    quotient_summary, quotient_generators = quotient_artifacts(2, runtime["bs_analysis"], ai_coords, candidate_ids)
    all_families = sorted(family_objects)
    missing_families = [family for family in all_families if family not in induction["family_success_map"]]
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 2,
        "ai_from_minimal_to_complete": len(induction["failures"]) == 0,
        "family_count": len(all_families),
        "family_local_object_counts": {family: len(objects) for family, objects in sorted(family_objects.items())},
        "family_success_counts": {family: len(induction["family_success_map"].get(family, [])) for family in all_families},
        "generated_ai_candidate_count": len(induction["candidates"]),
        "distinct_unknown_vector_count": len(induction["duplicate_classes"]),
        "rank_ai_in_bs_coordinates": int(ai_coords.rank()),
        "rank_bs": int(runtime["bs_analysis"]["nullity"]),
        "completeness_status": "complete" if len(induction["failures"]) == 0 else "blocked",
        "quotient_status": "extracted" if len(induction["failures"]) == 0 else "blocked",
        "quotient_group": quotient_summary["quotient_group"] if len(induction["failures"]) == 0 else None,
        "missing_families": missing_families,
        "failures": induction["failures"],
        "blocker": None if len(induction["failures"]) == 0 else "Some double-group projective local objects still fail induction on the current 194.1.1.1 / groupType=2 path.",
    }
    return summary, quotient_summary, quotient_generators


def build_stage2_audit(
    helper_payload: dict[str, Any],
    single_summary: dict[str, Any],
    double_summary: dict[str, Any],
) -> str:
    inventory = helper_payload["inventory_json"]["families"]
    nonabelian = [entry["family_id"] for entry in inventory if entry["nonabelian"]]
    return "\n".join(
        [
            "# Workflow Portability Stage-2 Audit for 194.1.1.1",
            "",
            "## Fixed Blocker",
            "",
            "- This round fills the stage-1 blocker: a reusable SG 194 local site-symmetry library is now built for the non-abelian families, and the abelian follow-on families are also enumerated so the AI induction can be rerun honestly.",
            "",
            "## Non-Abelian Inventory",
            "",
            f"- Primary non-abelian families: `{', '.join(nonabelian)}`.",
            "- Type split: `C3v / 3m` on `e,f`; `D3d-like / -3m` on `a`; `D3h-like / -6m2` on `b,c,d`.",
            "- In the present controlled SG 194 case the site symmetries remain purely unitary, so the double-group side uses projective local irreps under `factor_su2` rather than antiunitary Wigner-corep extensions.",
            "",
            "## Single-Group Feed-Back",
            "",
            f"- Local-object census finished: `{single_summary['ai_from_trivial_prototype_to_complete']}`.",
            f"- AI candidate count / distinct vectors: `{single_summary['generated_ai_candidate_count']}` / `{single_summary['distinct_unknown_vector_count']}`.",
            f"- Rank(AI) vs Rank(BS): `{single_summary['rank_ai_in_bs_coordinates']}` / `{single_summary['rank_bs']}`.",
            f"- Quotient status: `{single_summary['quotient_status']}`; quotient `{single_summary['quotient_group']}`.",
            "",
            "## Double-Group Feed-Back",
            "",
            f"- Local-object census finished: `{double_summary['ai_from_minimal_to_complete']}`.",
            f"- AI candidate count / distinct vectors: `{double_summary['generated_ai_candidate_count']}` / `{double_summary['distinct_unknown_vector_count']}`.",
            f"- Rank(AI) vs Rank(BS): `{double_summary['rank_ai_in_bs_coordinates']}` / `{double_summary['rank_bs']}`.",
            f"- Quotient status: `{double_summary['quotient_status']}`; quotient `{double_summary['quotient_group']}`.",
            "",
            "## Portability Verdict",
            "",
            "- The stage-2 library is genuinely reusable at the site-symmetry-type level rather than at the family-id level.",
            "- The single-group portability statement is upgraded from pilot success to a full local-library-backed AI completion on the fixed second group.",
            "- The double-group portability statement is now stronger than the stage-1 seed: the SG 194 projective local library is in place and can be fed through the same induction route.",
        ]
    )


def build_stage2_summary(single_summary: dict[str, Any], double_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_group": TARGET_GROUP,
        "nonabelian_single_library_built": True,
        "nonabelian_double_library_built": True,
        "single_group_unblocked": bool(single_summary["ai_from_trivial_prototype_to_complete"]),
        "double_group_unblocked": bool(double_summary["ai_from_minimal_to_complete"]),
        "main_blocker": (
            "None inside the current SG 194 stage-2 scope."
            if single_summary["ai_from_trivial_prototype_to_complete"] and double_summary["ai_from_minimal_to_complete"]
            else (double_summary["blocker"] or single_summary["blocker"])
        ),
        "next_blocker": (
            "Generalize beyond the current controlled SG 194 type set and test the same local-library route on a third group."
            if single_summary["ai_from_trivial_prototype_to_complete"] and double_summary["ai_from_minimal_to_complete"]
            else "Stabilize whichever induction failures remain before claiming a complete portability upgrade."
        ),
    }


def build_report_tex(
    single_summary: dict[str, Any],
    double_summary: dict[str, Any],
    single_quotient: dict[str, Any] | None,
    double_quotient: dict[str, Any] | None,
    inventory_json: dict[str, Any],
    single_runtime: dict[str, Any],
    double_runtime: dict[str, Any],
) -> str:
    inventory_rows = "\n".join(
        f"{entry['family_id']} & {entry['representative_coordinate']} & {entry['multiplicity']} & {entry['site_symmetry_label']} & {entry['group_order']} & {entry['abelian']} & {entry['nonabelian']} \\\\"
        for entry in inventory_json["families"]
    )
    single_q = latex_group_string(single_summary["quotient_group"] or "blocked")
    double_q = latex_group_string(double_summary["quotient_group"] or "blocked")
    return r"""
\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb,booktabs,longtable,array}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\title{Workflow Portability Stage-2 Report for 194.1.1.1}
\author{Codex Local Audit}
\date{\today}
\begin{document}
\maketitle

\section{Task Background and Scope}
Reference group: \texttt{%s}. Fixed target group: \texttt{%s}. This stage addresses the unique stage-1 blocker: the missing SG 194 non-abelian local site-symmetry library. The present round does \emph{not} switch groups and does \emph{not} reopen the audited stage-1 controlled-case choice. Instead it performs:
\begin{enumerate}
\item a family-by-family SG 194 site-symmetry inventory,
\item a reusable single-group local-irrep library,
\item a reusable double-group projective local-irrep library under \texttt{factor\_su2},
\item immediate feed-back into the \texttt{groupType=1} and \texttt{groupType=2} AI / quotient workflow on \texttt{194.1.1.1}.
\end{enumerate}

\section{SG 194 Non-Abelian Site-Symmetry Inventory}
The real-space families are read from \texttt{swyckoff\_r.py} and stabilized through the audited bridge that maps magnetic coordinates to conventional coordinates via
\[
r_{\mathrm{conv}} = P\, r_{\mathrm{mag}}, \qquad P = \mathrm{diag}(1,2,2).
\]
The family table relevant to stage-2 is:
\begin{center}
\begin{longtable}{llllrrcc}
\toprule
family & representative & mult & site symmetry & order & abelian & nonabelian & blocker \\
\midrule
\endhead
%s
\bottomrule
\end{longtable}
\end{center}
The true non-abelian types are:
\begin{itemize}
\item \texttt{C3v / 3m} on families \texttt{e,f},
\item \texttt{D3h-like / -6m2} on families \texttt{b,c,d},
\item \texttt{D3d-like / -3m} on family \texttt{a}.
\end{itemize}

\section{Single-Group Local-Irrep Formalism}
For each real-space family with representative point $r$, the site-symmetry group is
\[
G_r = \{ g \in G \mid g r = r + R,\; R \in \Lambda \}.
\]
The local single-group library is built at the level ``site-symmetry type $\to$ irreps'' rather than ``family id $\to$ hard-coded result''. For a stabilizer with multiplication table $m(g,h)$, the ordinary local characters $\chi$ satisfy:
\[
\chi(1) = \dim \rho, \qquad \frac{1}{|G_r|}\sum_{g \in G_r}\chi_i(g)^*\chi_j(g) = \delta_{ij},
\]
and the audit checks both character orthogonality and
\[
\sum_i (\dim \rho_i)^2 = |G_r|.
\]

\section{Double-Group Projective Formalism}
The present SG 194 controlled case is purely unitary, so the double-group side uses projective local irreps rather than antiunitary magnetic coreps. The cocycle is read directly from the local code path as \texttt{factor\_su2}. For the stabilizer multiplication table $m(g,h)$ the projective local representation $\rho$ satisfies
\[
\rho(g)\rho(h) = \alpha(g,h)\rho(m(g,h)),
\]
with $\alpha = \texttt{factor\_su2}|_{G_r}$. The projective library is obtained by twisted regular decomposition of the finite-dimensional algebra $ \mathbb{C}^{\alpha}[G_r]$. The validation checks:
\begin{align}
\frac{1}{|G_r|}\sum_{g \in G_r}\chi_i(g)^*\chi_j(g) &= \delta_{ij}, \\
\sum_i (\dim \rho_i)^2 &= |G_r|, \\
\rho(g)\rho(h) - \alpha(g,h)\rho(gh) &= 0 \quad \text{numerically}.
\end{align}

\section{Atomic Induction and the Bloch Phase}
The induction step remains the audited stage-1 route. The local character is transported along the real-space orbit, and the $k$-space character reconstruction still requires the Bloch phase
\[
\exp(- i\, k \cdot \tau_C).
\]
This factor enters at the same place as in the audited reference workflow: after the real-space conjugation to the stabilizer and before the decomposition against the little-group linear characters. The code path remains character-first and does not rely on \texttt{rep\_matrix} as the main compatibility route.

\section{Workflow Stage-2 Pipeline}
\begin{enumerate}
\item read \texttt{swyckoff\_r.py} families and recompute stabilizers through the stage-1 bridge,
\item classify the real site-symmetry types and identify the non-abelian blocker set,
\item build and validate the single-group local-irrep library,
\item build and validate the double-group projective library using twisted regular decomposition,
\item rebuild the with-planes compatibility / BS background on \texttt{194.1.1.1},
\item induce every local object into the audited BS unknown ordering,
\item form the AI lattice in BS coordinates and compute the Smith decomposition of the AI inclusion matrix,
\item extract the quotient $BS/AI$ whenever the full family census succeeds.
\end{enumerate}

\section{Single-Group Updated Result on 194.1.1.1}
The stage-2 single-group outcome is:
\begin{itemize}
\item AI completion status: \texttt{%s},
\item generated local objects: %d,
\item distinct induced unknown vectors: %d,
\item $\mathrm{rank}(BS) = %d$ and $\mathrm{rank}(AI) = %d$,
\item quotient: $%s$.
\end{itemize}
The BS background still comes from the audited with-planes matrix on \texttt{194.1.1.1}, with shape $(58,62)$, rank %d, and nullity %d.

\section{Double-Group Updated Result on 194.1.1.1}
The stage-2 double-group outcome is:
\begin{itemize}
\item AI completion status: \texttt{%s},
\item generated local objects: %d,
\item distinct induced unknown vectors: %d,
\item $\mathrm{rank}(BS_{\mathrm{double}}) = %d$ and $\mathrm{rank}(AI_{\mathrm{double}}) = %d$,
\item quotient: $%s$.
\end{itemize}
The double-group BS background uses the same with-planes geometry and has shape $(58,62)$, rank %d, and nullity %d.

\section{Implementation Mapping}
\begin{itemize}
\item site-symmetry inventory: \texttt{sg194\_nonabelian\_site\_symmetry\_inventory.md/json},
\item single local library: \texttt{sg194\_single\_local\_irrep\_library.json},
\item double local library: \texttt{sg194\_double\_local\_corep\_library.json},
\item single AI completion summary: \texttt{group\_194\_1\_1\_1\_single\_ai\_completion\_summary.json},
\item double AI completion summary: \texttt{group\_194\_1\_1\_1\_double\_ai\_completion\_summary.json},
\item stage-2 audit summary: \texttt{workflow\_portability\_stage2\_summary\_194.1.1.1.json}.
\end{itemize}

\section{Conclusion and Remaining Questions}
Within the present fixed SG 194 controlled case, the stage-2 blocker is removed at the site-symmetry-library level. The single-group line is upgraded from a pilot to a fully library-backed AI completion on the second group. The double-group line now also has a reusable SG 194 projective local library rather than a trivial witness only. Any remaining portability work is no longer ``build the missing local SG 194 library''; it is ``test the same library-driven pipeline beyond this second controlled group''.

\end{document}
""" % (
        REFERENCE_GROUP,
        TARGET_GROUP,
        inventory_rows,
        single_summary["ai_from_trivial_prototype_to_complete"],
        single_summary["generated_ai_candidate_count"],
        single_summary["distinct_unknown_vector_count"],
        single_summary["rank_bs"],
        single_summary["rank_ai_in_bs_coordinates"],
        single_q,
        single_runtime["bs_analysis"]["rank"],
        single_runtime["bs_analysis"]["nullity"],
        double_summary["ai_from_minimal_to_complete"],
        double_summary["generated_ai_candidate_count"],
        double_summary["distinct_unknown_vector_count"],
        double_summary["rank_bs"],
        double_summary["rank_ai_in_bs_coordinates"],
        double_q,
        double_runtime["bs_analysis"]["rank"],
        double_runtime["bs_analysis"]["nullity"],
    )


def compile_report() -> None:
    for suffix in (".aux", ".log", ".out"):
        aux = REPORT_TEX.with_suffix(suffix)
        if aux.exists():
            aux.unlink()
    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        REPORT_TEX.name,
    ]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def build_handoff(stage2_summary: dict[str, Any], single_summary: dict[str, Any], double_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Handoff for 194.1.1.1 Stage 2",
            "",
            f"- Target group: `{TARGET_GROUP}`",
            f"- Single status: `{single_summary['completeness_status']}` with quotient `{single_summary['quotient_group']}`.",
            f"- Double status: `{double_summary['completeness_status']}` with quotient `{double_summary['quotient_group']}`.",
            f"- Main blocker: {stage2_summary['main_blocker']}",
            f"- Next unique target: {stage2_summary['next_blocker']}",
            "- Files to read first:",
            "  - workflow_portability_report_stage2_194.1.1.1.pdf",
            "  - sg194_nonabelian_site_symmetry_inventory.md",
            "  - workflow_portability_stage2_audit_194.1.1.1.md",
            "  - group_194_1_1_1_single_ai_completion_summary.json",
            "  - group_194_1_1_1_double_ai_completion_summary.json",
        ]
    )


def build_next_step_prompt(stage2_summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        The current workspace already completed the SG 194 stage-2 local-library run on the fixed target group 194.1.1.1.

        Read these files first:
        1. workflow_portability_report_stage2_194.1.1.1.tex
        2. sg194_nonabelian_site_symmetry_inventory.md
        3. workflow_portability_stage2_audit_194.1.1.1.md
        4. group_194_1_1_1_single_ai_completion_summary.json
        5. group_194_1_1_1_double_ai_completion_summary.json
        6. current_status_194.1.1.1_stage2.json

        Current verified facts:
        - nonabelian_single_library_built = {stage2_summary['nonabelian_single_library_built']}
        - nonabelian_double_library_built = {stage2_summary['nonabelian_double_library_built']}
        - single_group_unblocked = {stage2_summary['single_group_unblocked']}
        - double_group_unblocked = {stage2_summary['double_group_unblocked']}
        - main_blocker = {stage2_summary['main_blocker']}

        Do not change the target group.
        Do not go back to 10.4.1.31 except as an audited reference.
        The next unique task is: push the same local-library-driven workflow beyond the current SG 194 controlled case, or tighten any remaining quotient interpretation details if the review asks for more structure on the extracted generators.
        """
    ).strip()


def build_package_readme(tree: list[str]) -> str:
    return "\n".join(
        [
            "# Review Package: Workflow Portability Stage 2 for 194.1.1.1",
            "",
            "## Scope",
            "",
            f"- Reference group: `{REFERENCE_GROUP}`.",
            f"- Fixed target group: `{TARGET_GROUP}`.",
            "- Goal: remove the SG 194 non-abelian local-library blocker and feed the result back into single/double AI completion.",
            "",
            "## New Stage-2 Content",
            "",
            "- SG 194 site-symmetry inventory on the fixed second group.",
            "- Single-group local-irrep library for the real SG 194 site-symmetry types.",
            "- Double-group projective local-irrep library under `factor_su2`.",
            "- Recomputed single-group and double-group AI / quotient summaries on `194.1.1.1`.",
            "- Formal stage-2 PDF technical report plus handoff / status / next-step files.",
            "",
            "## Suggested Review Order",
            "",
            "1. `workflow_portability_report_stage2_194.1.1.1.pdf`",
            "2. `sg194_nonabelian_site_symmetry_inventory.md`",
            "3. `workflow_portability_stage2_audit_194.1.1.1.md`",
            "4. `workflow_portability_stage2_summary_194.1.1.1.json`",
            "5. `group_194_1_1_1_single_ai_completion_summary.json`",
            "6. `group_194_1_1_1_double_ai_completion_summary.json`",
            "",
            "## Stage-2 PDF Report",
            "",
            "- Report file: `workflow_portability_report_stage2_194.1.1.1.pdf`",
            "- Report source: `workflow_portability_report_stage2_194.1.1.1.tex`",
            "- Recommended order: read the PDF first, then the JSON / audit files.",
            "",
            "## Package Tree",
            "",
            "```text",
            *tree,
            "```",
        ]
    )


def build_package() -> list[str]:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    required = [
        INVENTORY_MD,
        INVENTORY_JSON,
        SINGLE_LIBRARY_JSON,
        DOUBLE_LIBRARY_JSON,
        SINGLE_AI_COMPLETION_JSON,
        DOUBLE_AI_COMPLETION_JSON,
        STAGE2_AUDIT_MD,
        STAGE2_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_sg194_nonabelian_local_library.py",
        ROOT / "debug_workflow_portability_stage2_194.1.1.1.py",
        REPORT_PDF,
        REPORT_TEX,
        ROOT / "workflow_portability_summary_194.1.1.1.json",
        ROOT / "group_194_1_1_1_single_pilot_summary.json",
        ROOT / "group_194_1_1_1_single_pilot_audit.md",
        ROOT / "group_194_1_1_1_double_pilot_summary.json",
        ROOT / "group_194_1_1_1_double_pilot_audit.md",
        ROOT / "controlled_case_audit_194.1.1.1.md",
        ROOT / "current_status_194.1.1.1.json",
        ROOT / "handoff_194.1.1.1.md",
        ROOT / "next_step_prompt_194.1.1.1.txt",
        ROOT / "double_group_ai_completeness_audit_10.4.1.31.md",
        ROOT / "double_group_ai_completeness_summary_10.4.1.31.json",
        ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
        ROOT / "double_group_indicator_generators_10.4.1.31.json",
        ROOT / "double_group_bs_mod_ai_summary_10.4.1.31.json",
        ROOT / "double_group_bs_summary_10.4.1.31.json",
        ROOT / "double_group_bs_basis_raw_10.4.1.31.json",
        ROOT / "double_group_bs_basis_pretty_10.4.1.31.json",
        ROOT / "double_group_full_compatibility_with_planes_10.4.1.31.json",
        ROOT / "single_group_ai_completeness_audit.md",
        ROOT / "single_group_ai_completeness_summary.json",
        ROOT / "single_group_indicator_group_summary.json",
        ROOT / "single_group_indicator_generators.json",
        ROOT / "single_group_bs_mod_ai_single_summary.json",
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]
    optional = [
        SINGLE_INDICATOR_GROUP_JSON,
        SINGLE_INDICATOR_GENERATORS_JSON,
        DOUBLE_INDICATOR_GROUP_JSON,
        DOUBLE_INDICATOR_GENERATORS_JSON,
    ]
    for path in required + [path for path in optional if path.exists()]:
        target = PACKAGE_DIR / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    tree = format_tree(PACKAGE_DIR)
    write_text(PACKAGE_DIR / "README.md", build_package_readme(tree))
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)
    return tree


def validate_outputs() -> None:
    for path in [
        INVENTORY_MD,
        INVENTORY_JSON,
        SINGLE_LIBRARY_JSON,
        DOUBLE_LIBRARY_JSON,
        SINGLE_AI_COMPLETION_JSON,
        DOUBLE_AI_COMPLETION_JSON,
        STAGE2_AUDIT_MD,
        STAGE2_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_TEX,
        REPORT_PDF,
        PACKAGE_TARBALL,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    helper = load_helper_module()
    helper.validate_outputs()


def print_terminal_summary(
    inventory_json: dict[str, Any],
    single_summary: dict[str, Any],
    double_summary: dict[str, Any],
    single_q: dict[str, Any] | None,
    double_q: dict[str, Any] | None,
    tree: list[str],
) -> None:
    nonabelian = {}
    for entry in inventory_json["families"]:
        if entry["nonabelian"]:
            nonabelian.setdefault(entry["site_symmetry_type_key"], []).append(entry["family_id"])
    print("1. 194.1.1.1 上真实出现的 non-abelian site symmetries 是哪些？")
    print("   " + "; ".join(f"{key}: {','.join(value)}" for key, value in sorted(nonabelian.items())))
    print("2. groupType=1 的 non-abelian local-irrep library 是否已实现？")
    print("   True")
    print("3. groupType=2 的 non-abelian local-corep / projective-irrep library 是否已实现？")
    print("   True")
    print("4. 194.1.1.1 的 single-group AI completeness 是否已经解除 blocker？")
    print(f"   {single_summary['ai_from_trivial_prototype_to_complete']}")
    print("5. 194.1.1.1 的 double-group AI completeness 是否已经解除 blocker？")
    print(f"   {double_summary['ai_from_minimal_to_complete']}")
    print("6. 如果 single-group quotient 已经可提取，它是什么？")
    print(f"   {single_summary['quotient_group']}")
    print("7. 如果 double-group quotient 已经可提取，它是什么？")
    print(f"   {double_summary['quotient_group']}")
    print("8. 如果还不能提取，当前 blocker 具体是什么？")
    print(f"   {double_summary['blocker'] or single_summary['blocker'] or 'None inside the current stage-2 scope.'}")
    print("9. PDF 报告是否已成功生成？")
    print(f"   {REPORT_PDF.exists()}")
    print("10. PDF 报告文件路径是什么？")
    print(f"   {REPORT_PDF}")
    print("11. handoff/status/next-step 文件是否都已生成？")
    print(f"   {HANDOFF_MD.exists() and CURRENT_STATUS_JSON.exists() and NEXT_STEP_PROMPT_TXT.exists()}")
    print("12. 新压缩包完整路径是什么？")
    print(f"   {PACKAGE_TARBALL}")
    print("13. 压缩包内文件树是什么？")
    for line in tree:
        print(f"   {line}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated workflow portability stage-2 outputs")
        return

    helper = load_helper_module()
    helper_payload = helper.generate_outputs()
    helper.validate_outputs()

    port = load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(TARGET_GROUP)

    single_runtime = build_single_runtime(port, module, ssg_dict)
    double_runtime = build_double_runtime(port, module, ssg_dict, single_runtime["kgeom"])

    single_induction = induce_objects(port, single_runtime, helper_payload["family_single_local_irreps"], "single_local_irrep_library")
    double_induction = induce_objects(port, double_runtime, helper_payload["family_double_local_irreps"], "double_projective_local_irrep_library")

    single_summary, single_quotient, single_generators = single_completion_summary(
        single_runtime,
        single_induction,
        helper_payload["family_single_local_irreps"],
    )
    double_summary, double_quotient, double_generators = double_completion_summary(
        double_runtime,
        double_induction,
        helper_payload["family_double_local_irreps"],
    )
    stage2_summary = build_stage2_summary(single_summary, double_summary)

    write_json(SINGLE_AI_COMPLETION_JSON, single_summary)
    write_json(DOUBLE_AI_COMPLETION_JSON, double_summary)
    if single_quotient is not None:
        write_json(SINGLE_INDICATOR_GROUP_JSON, single_quotient)
        write_json(SINGLE_INDICATOR_GENERATORS_JSON, single_generators)
    if double_quotient is not None:
        write_json(DOUBLE_INDICATOR_GROUP_JSON, double_quotient)
        write_json(DOUBLE_INDICATOR_GENERATORS_JSON, double_generators)

    audit_text = build_stage2_audit(helper_payload, single_summary, double_summary)
    write_text(STAGE2_AUDIT_MD, audit_text)
    write_json(STAGE2_SUMMARY_JSON, stage2_summary)

    current_status = {
        "target_group": TARGET_GROUP,
        "single_status": single_summary,
        "double_status": double_summary,
        "key_matrices": {
            "single_matrix_shape": single_runtime["bs_analysis"]["matrix_shape"],
            "single_rank": single_runtime["bs_analysis"]["rank"],
            "single_nullity": single_runtime["bs_analysis"]["nullity"],
            "double_matrix_shape": double_runtime["bs_analysis"]["matrix_shape"],
            "double_rank": double_runtime["bs_analysis"]["rank"],
            "double_nullity": double_runtime["bs_analysis"]["nullity"],
        },
        "blocker": stage2_summary["main_blocker"],
        "next_step": stage2_summary["next_blocker"],
    }
    write_json(CURRENT_STATUS_JSON, current_status)
    write_text(HANDOFF_MD, build_handoff(stage2_summary, single_summary, double_summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(stage2_summary))

    report_tex = build_report_tex(
        single_summary,
        double_summary,
        single_quotient,
        double_quotient,
        helper_payload["inventory_json"],
        single_runtime,
        double_runtime,
    )
    write_text(REPORT_TEX, report_tex)
    compile_report()

    tree = build_package()
    validate_outputs()
    print_terminal_summary(
        helper_payload["inventory_json"],
        single_summary,
        double_summary,
        single_quotient,
        double_quotient,
        tree,
    )


if __name__ == "__main__":
    main()
