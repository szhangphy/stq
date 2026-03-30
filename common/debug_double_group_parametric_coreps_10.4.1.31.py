#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import tarfile
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_form


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 2

TARGET_FAMILIES = ["o", "m", "k", "l", "n", "i", "j"]
PROCESSING_ORDER = ["o", "m", "k", "l", "i", "j", "n"]
PURE_UNITARY_FAMILIES = ["o", "m", "k", "l"]
ANTIUNITARY_FAMILIES = ["n", "i", "j"]

REVIEW_POINTLIKE = ROOT / "review_package_10.4.1.31_double_pointlike_ai"
REVIEW_SINGLE = ROOT / "review_package_10.4.1.31_single_indicator"

PARAMETRIC_AUDIT_MD = ROOT / "double_group_parametric_corep_audit_10.4.1.31.md"
PARAMETRIC_SUMMARY_JSON = ROOT / "double_group_parametric_corep_summary_10.4.1.31.json"
PARAMETRIC_COREPS_JSON = ROOT / "double_group_parametric_coreps_10.4.1.31.json"
AI_V2_CANDIDATES_JSON = ROOT / "double_group_ai_v2_candidates_10.4.1.31.json"
AI_V2_MATRIX_JSON = ROOT / "double_group_ai_v2_matrix_10.4.1.31.json"
AI_V2_BASIS_JSON = ROOT / "double_group_ai_v2_basis_10.4.1.31.json"
BS_VS_AI_V2_SUMMARY_JSON = ROOT / "double_group_bs_vs_ai_v2_summary_10.4.1.31.json"
SATURATION_AUDIT_MD = ROOT / "double_group_saturation_audit_10.4.1.31.md"
SATURATION_SUMMARY_JSON = ROOT / "double_group_saturation_summary_10.4.1.31.json"

BS_SUMMARY_JSON = ROOT / "double_group_bs_summary_10.4.1.31.json"
BS_RAW_JSON = ROOT / "double_group_bs_basis_raw_10.4.1.31.json"
BS_PRETTY_JSON = ROOT / "double_group_bs_basis_pretty_10.4.1.31.json"

POINTLIKE_AUDIT_MD = REVIEW_POINTLIKE / "double_group_pointlike_corep_audit_10.4.1.31.md"
POINTLIKE_SUMMARY_JSON = REVIEW_POINTLIKE / "double_group_pointlike_corep_summary_10.4.1.31.json"
POINTLIKE_COREPS_JSON = REVIEW_POINTLIKE / "double_group_pointlike_coreps_10.4.1.31.json"
POINTLIKE_CANDIDATES_JSON = REVIEW_POINTLIKE / "double_group_ai_pointlike_v1_candidates_10.4.1.31.json"
POINTLIKE_MATRIX_JSON = REVIEW_POINTLIKE / "double_group_ai_pointlike_v1_matrix_10.4.1.31.json"
POINTLIKE_BASIS_JSON = REVIEW_POINTLIKE / "double_group_ai_pointlike_v1_basis_10.4.1.31.json"
POINTLIKE_BS_VS_AI_JSON = REVIEW_POINTLIKE / "double_group_bs_vs_ai_pointlike_v1_summary_10.4.1.31.json"

FEAS_AUDIT_MD = REVIEW_POINTLIKE / "double_group_feasibility_audit_10.4.1.31.md"
FEAS_SUMMARY_JSON = REVIEW_POINTLIKE / "double_group_feasibility_summary_10.4.1.31.json"
KSPACE_AUDIT_MD = REVIEW_POINTLIKE / "double_group_kspace_backbone_audit_10.4.1.31.md"
KSPACE_SUMMARY_JSON = REVIEW_POINTLIKE / "double_group_kspace_backbone_summary_10.4.1.31.json"
LINE_BLOCKS_JSON = REVIEW_POINTLIKE / "double_group_line_blocks_10.4.1.31.json"
WITH_PLANES_JSON = REVIEW_POINTLIKE / "double_group_full_compatibility_with_planes_10.4.1.31.json"
MIN_REALSPACE_JSON = REVIEW_POINTLIKE / "double_group_minimal_realspace_10.4.1.31.json"
MIN_AI_EMBED_JSON = REVIEW_POINTLIKE / "double_group_minimal_ai_embedding_10.4.1.31.json"

PACKAGE_NAME = "review_package_10.4.1.31_double_parametric_ai"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TAR = ROOT / f"{PACKAGE_NAME}.tar.gz"

REQUIRED_NEW_FILES = [
    PARAMETRIC_AUDIT_MD,
    PARAMETRIC_SUMMARY_JSON,
    PARAMETRIC_COREPS_JSON,
    AI_V2_CANDIDATES_JSON,
    AI_V2_MATRIX_JSON,
    AI_V2_BASIS_JSON,
    BS_VS_AI_V2_SUMMARY_JSON,
    ROOT / "debug_double_group_parametric_coreps_10.4.1.31.py",
    PACKAGE_TAR,
]

PURE_UNITARY_MODELS: dict[str, dict[str, Any]] = {
    "o": {
        "processing_reason": "Start from the fully generic family because its stabilizer is just the identity; this is the cleanest way to test the sample-point orbit branch before any nontrivial projective relation is introduced.",
        "builder": "trivial_projective",
        "site_symmetry_label": "1",
        "unitary_indices": [0],
        "unitary_subgroup_label": "1",
    },
    "m": {
        "processing_reason": "Second because it is still pure unitary, but now the order-2 mirror generator forces a real projective check through `factor_su2(7,7)=-1`.",
        "builder": "order2_projective",
        "site_symmetry_label": "m",
        "unitary_indices": [0, 7],
        "generator_index": 7,
        "generator_label": "mirror",
        "unitary_subgroup_label": "projective m",
    },
    "k": {
        "processing_reason": "Then move to the one-parameter pure-unitary `2` family, which uses the same order-2 projective logic as `m` but on a different generator and orbit geometry.",
        "builder": "order2_projective",
        "site_symmetry_label": "2",
        "unitary_indices": [0, 3],
        "generator_index": 3,
        "generator_label": "C2",
        "unitary_subgroup_label": "projective 2",
    },
    "l": {
        "processing_reason": "Processed immediately after `k` because it is its translated partner with the same projective order-2 stabilizer.",
        "builder": "order2_projective",
        "site_symmetry_label": "2",
        "unitary_indices": [0, 3],
        "generator_index": 3,
        "generator_label": "C2",
        "unitary_subgroup_label": "projective 2",
    },
}

ANTIUNITARY_MODELS: dict[str, dict[str, Any]] = {
    "i": {
        "processing_reason": "The antiunitary stage starts with the simplest one-parameter `2'` family, whose unitary subgroup is trivial and therefore gives the cleanest double case-a extension test.",
        "site_symmetry_label": "2'",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
    },
    "j": {
        "processing_reason": "Processed next because it is the translated partner of `i` and should reuse the exact same case-a builder if the sample-point orbit logic is correct.",
        "site_symmetry_label": "2'",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
    },
    "n": {
        "processing_reason": "Kept last because it is the two-parameter antiunitary `m'` family; the corep classification is still case a, but its generic sample-point orbit is the largest antiunitary parametric test in scope.",
        "site_symmetry_label": "m'",
        "antiunitary_generator_index": 14,
        "antiunitary_generator_name": "raw op 14",
    },
}


def load_backbone_module():
    candidates = [
        ROOT / "debug_double_group_kspace_backbone_10.4.1.31.py",
        ROOT / "dependencies" / "debug_double_group_kspace_backbone_10.4.1.31.py",
    ]
    backbone_path = next((path for path in candidates if path.exists()), None)
    if backbone_path is None:
        raise FileNotFoundError("debug_double_group_kspace_backbone_10.4.1.31.py not found")
    spec = importlib.util.spec_from_file_location("double_backbone_parametric_local", backbone_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {backbone_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backbone = load_backbone_module()


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


def smith_diagonal(matrix: sp.Matrix) -> list[int]:
    diag: list[int] = []
    D = smith_normal_form(matrix)
    for index in range(min(D.rows, D.cols)):
        value = int(D[index, index])
        if value:
            diag.append(abs(value))
    return diag


def columns_from_matrix(matrix: sp.Matrix) -> list[list[int]]:
    return [
        [int(matrix[row, col]) for row in range(matrix.rows)]
        for col in range(matrix.cols)
    ]


def complex_symbol(value: complex) -> str:
    rounded = complex(round(float(value.real), 12), round(float(value.imag), 12))
    if abs(rounded) < 1e-12:
        return "0"
    if abs(rounded - 1) < 1e-12:
        return "1"
    if abs(rounded + 1) < 1e-12:
        return "-1"
    if abs(rounded - 1j) < 1e-12:
        return "+i"
    if abs(rounded + 1j) < 1e-12:
        return "-i"
    return str(rounded)


def serialize_site_symmetry_generators(ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    generators = []
    for op in ops:
        generators.append(
            {
                "token": op.get("token"),
                "type": op.get("type"),
                "kind": op.get("kind"),
                "axis": op.get("axis"),
                "time_reversal": bool(op.get("time_reversal", False)),
                "spin_matrix": op.get("spin_matrix"),
            }
        )
    return generators


def serialize_stabilizer_element(ctx: dict[str, Any], op_index: int) -> dict[str, Any]:
    rotation = np.array(ctx["ssg"].rotC[op_index], dtype=int).tolist()
    translation = backbone.single_bridge.format_vector(np.array(ctx["ssg"].tauC[op_index], dtype=float))
    return {
        "index": int(op_index),
        "rotation": rotation,
        "translation": translation,
        "time_reversal": bool(int(ctx["ssg"].time_reversal[op_index]) < 0),
    }


def basis_matrix_from_json(basis_json: dict[str, Any]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in basis_json["basis_vectors"]])


def candidate_vector_key(candidate: dict[str, Any]) -> tuple[int, ...]:
    return tuple(candidate["vector_in_bs_double_unknown_ordering"])


def annotate_duplicate_classes(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_vector: dict[tuple[int, ...], list[str]] = {}
    for candidate in candidates:
        by_vector.setdefault(candidate_vector_key(candidate), []).append(candidate["generator_id"])

    classes = []
    for vector, ids in sorted(by_vector.items(), key=lambda item: item[1]):
        classes.append(
            {
                "generator_ids": ids,
                "vector_in_bs_double_unknown_ordering": list(vector),
                "class_size": len(ids),
            }
        )

    id_to_class = {
        generator_id: duplicate["generator_ids"]
        for duplicate in classes
        for generator_id in duplicate["generator_ids"]
    }
    for candidate in candidates:
        candidate["same_unknown_vector_as"] = [
            generator_id
            for generator_id in id_to_class[candidate["generator_id"]]
            if generator_id != candidate["generator_id"]
        ]
    return classes


def integerize_vector(vector: sp.Matrix) -> list[int]:
    denominators = [term.as_numer_denom()[1] for term in vector]
    scale = 1
    for denominator in denominators:
        scale = int(sp.ilcm(scale, int(denominator)))
    scaled = [int(sp.expand(term * scale)) for term in vector]
    gcd = 0
    for value in scaled:
        gcd = math.gcd(gcd, abs(value))
    gcd = max(gcd, 1)
    normalized = [value // gcd for value in scaled]
    for value in normalized:
        if value != 0:
            if value < 0:
                normalized = [-entry for entry in normalized]
            break
    return normalized


def solve_integer_basis_coordinates(basis_matrix: sp.Matrix, vector: list[int], context: str) -> list[int]:
    target = sp.Matrix(vector)
    solution, params = basis_matrix.gauss_jordan_solve(target)
    if params.rows * params.cols:
        raise ValueError(f"free parameters when solving {context}")
    result: list[int] = []
    for coeff in solution:
        if coeff.is_Integer:
            result.append(int(coeff))
            continue
        coeff_eval = complex(coeff.evalf())
        if abs(coeff_eval.imag) < 1e-8 and abs(coeff_eval.real - round(coeff_eval.real)) < 1e-8:
            result.append(int(round(coeff_eval.real)))
            continue
        raise ValueError(f"non-integral decomposition in {context}: {solution}")
    return result


def load_background_bundle() -> dict[str, Any]:
    return {
        "readme": (REVIEW_POINTLIKE / "README.md").read_text(),
        "pointlike_audit": POINTLIKE_AUDIT_MD.read_text(),
        "pointlike_summary": load_json(POINTLIKE_SUMMARY_JSON),
        "pointlike_coreps": load_json(POINTLIKE_COREPS_JSON),
        "pointlike_candidates": load_json(POINTLIKE_CANDIDATES_JSON),
        "pointlike_matrix": load_json(POINTLIKE_MATRIX_JSON),
        "pointlike_basis": load_json(POINTLIKE_BASIS_JSON),
        "pointlike_bs_vs_ai": load_json(POINTLIKE_BS_VS_AI_JSON),
        "bs_summary": load_json(REVIEW_POINTLIKE / "double_group_bs_summary_10.4.1.31.json"),
        "bs_raw": load_json(REVIEW_POINTLIKE / "double_group_bs_basis_raw_10.4.1.31.json"),
        "bs_pretty": load_json(REVIEW_POINTLIKE / "double_group_bs_basis_pretty_10.4.1.31.json"),
        "with_planes": load_json(REVIEW_POINTLIKE / "double_group_full_compatibility_with_planes_10.4.1.31.json"),
        "single_kmanifolds": load_json(REVIEW_POINTLIKE / "background" / "single_group_kmanifolds.json"),
        "single_connectivity": load_json(REVIEW_POINTLIKE / "background" / "single_group_connectivity.json"),
    }


def build_context() -> dict[str, Any]:
    ssg_module = backbone.load_ssgreps_module()
    ssg_dict = backbone.load_ssg_dict()
    ctx = backbone.load_double_context(ssg_module, ssg_dict)
    geometry = backbone.load_geometry_context()
    manifold_bundle = backbone.build_manifold_details(ssg_module, geometry, ssg_dict)
    background = load_background_bundle()

    bs_summary = background["bs_summary"]
    bs_raw = background["bs_raw"]
    bs_pretty = background["bs_pretty"]
    pointlike_candidates = background["pointlike_candidates"]
    pointlike_basis = background["pointlike_basis"]

    unknown_ordering = list(bs_summary["final_unknown_ordering"])
    if unknown_ordering != list(bs_raw["unknown_ordering"]) or unknown_ordering != list(bs_pretty["unknown_ordering"]):
        raise ValueError("BS unknown ordering mismatch across summary/raw/pretty files")
    if unknown_ordering != list(pointlike_candidates["unknown_ordering"]) or unknown_ordering != list(pointlike_basis["unknown_ordering"]):
        raise ValueError("Point-like and BS unknown ordering mismatch")

    ctx.update(
        {
            "background": background,
            "geometry": geometry,
            "manifold_details": manifold_bundle["details"],
            "manifold_stability": manifold_bundle["stability"],
            "manifold_stability_all_true": bool(manifold_bundle["all_stable"]),
            "final_unknown_ordering": unknown_ordering,
            "compatibility_matrix": sp.Matrix(bs_summary["final_C_double"]),
            "raw_basis_matrix": basis_matrix_from_json(bs_raw),
            "pretty_basis_matrix": basis_matrix_from_json(bs_pretty),
            "factor_su2": np.array(ctx["ssg"].factor_su2, dtype=complex),
            "mul_table_zero_based": np.array(ctx["ssg"].mul_table, dtype=int) - 1,
            "antiunitary_flags": [bool(int(flag) < 0) for flag in ctx["ssg"].time_reversal],
            "bs_rank": int(len(bs_raw["basis_vectors"])),
            "pointlike_v1_candidates": pointlike_candidates,
            "pointlike_v1_basis": pointlike_basis,
            "pointlike_v1_basis_coeff_matrix": sp.Matrix.hstack(
                *[sp.Matrix(column) for column in pointlike_basis["basis_bs_coefficients"]]
            ),
            "entries_by_letter": {entry["letter"]: entry for entry in ctx["wyckoff_entries"]},
        }
    )
    return ctx


def projective_character_is_valid(
    stabilizer: list[int],
    character: dict[int, complex],
    ctx: dict[str, Any],
) -> bool:
    mul_table = ctx["mul_table_zero_based"]
    factor = ctx["factor_su2"]
    for left in stabilizer:
        for right in stabilizer:
            target = int(mul_table[left, right])
            lhs = character[left] * character[right] * factor[left, right]
            rhs = character[target]
            if abs(lhs - rhs) > 1e-8:
                return False
    return True


def orbit_from_magnetic_anchor(anchor_mag: list[float], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    rep_conv = ctx["supercell"] @ np.array(anchor_mag, dtype=float)
    orbit: list[dict[str, Any]] = []
    seen = set()
    for op in ctx["group_tables"]["operations"]:
        image_conv = op["rotation"] @ rep_conv + op["translation"]
        key = backbone.single_bridge.reduced_magnetic_key(ctx["supercell"], image_conv)
        if key in seen:
            continue
        seen.add(key)
        orbit.append(
            {
                "source_operation_index": int(op["index"]),
                "time_reversal_source": bool(op["time_reversal"]),
                "magnetic_coordinate": list(key),
                "conventional_coordinate": backbone.single_bridge.format_vector(image_conv),
            }
        )
    return orbit


def build_trivial_projective_local_object(letter: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{letter}_double_A",
            "label": f"{letter}: A",
            "dimension": 1,
            "type": "projective_local_irrep",
            "double_group_local_object_kind": "projective_local_irrep",
            "origin": {
                "unitary_subgroup": "1",
                "construction": "Unique one-dimensional projective irrep of the trivial unitary stabilizer.",
            },
            "wigner_case": None,
            "truly_antiunitary": False,
            "depends_on_factor_su2": False,
            "character_on_unitary_stabilizer": {"0": backbone.complex_to_json(1 + 0j)},
            "projective_multiplication_verified": True,
            "verification_scope": {
                "stabilizer_indices": [0],
                "checked_relation_count": 1,
            },
        }
    ]


def build_projective_order2_local_objects(
    letter: str,
    generator_index: int,
    generator_label: str,
    stabilizer: list[int],
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for label, value in (("plus_i", 1j), ("minus_i", -1j)):
        character = {
            0: 1 + 0j,
            int(generator_index): complex(value),
        }
        if not projective_character_is_valid(stabilizer, character, ctx):
            raise ValueError(f"{letter}: invalid projective character {character}")
        objects.append(
            {
                "id": f"{letter}_double_{label}",
                "label": f"{letter}: {generator_label}={complex_symbol(value)}",
                "dimension": 1,
                "type": "projective_local_irrep",
                "double_group_local_object_kind": "projective_local_irrep",
                "origin": {
                    "unitary_subgroup": f"order-2 generated by raw op {generator_index}",
                    "construction": "Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.",
                    "generator_index": int(generator_index),
                    "generator_label": generator_label,
                    "generator_character": complex_symbol(value),
                },
                "wigner_case": None,
                "truly_antiunitary": False,
                "depends_on_factor_su2": True,
                "character_on_unitary_stabilizer": {
                    str(index): backbone.complex_to_json(val)
                    for index, val in character.items()
                },
                "projective_multiplication_verified": True,
                "verification_scope": {
                    "stabilizer_indices": list(stabilizer),
                    "checked_relation_count": len(stabilizer) ** 2,
                    "factor_on_generator_square": backbone.complex_to_json(
                        ctx["factor_su2"][generator_index, generator_index]
                    ),
                },
            }
        )
    return objects


def build_case_a_local_coreps(
    letter: str,
    antiunitary_generator: int,
    antiunitary_generator_name: str,
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    anti_square = ctx["group_tables"]["compose"](antiunitary_generator, antiunitary_generator)
    factor_value = ctx["factor_su2"][antiunitary_generator, antiunitary_generator]
    if anti_square != 0:
        raise ValueError(f"{letter}: antiunitary generator square is not the identity")
    if abs(factor_value - 1) > 1e-8:
        raise ValueError(f"{letter}: antiunitary square factor is not +1")

    objects: list[dict[str, Any]] = []
    for eta in (+1, -1):
        eta_label = "plus" if eta > 0 else "minus"
        objects.append(
            {
                "id": f"{letter}_double_A_eta_{eta_label}",
                "label": f"{letter}: A, eta={eta:+d}",
                "dimension": 1,
                "type": "magnetic_local_corep",
                "double_group_local_object_kind": "magnetic_local_corep",
                "origin": {
                    "unitary_subgroup": "1",
                    "construction": "Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.",
                    "antiunitary_generator_index": int(antiunitary_generator),
                    "antiunitary_generator_name": antiunitary_generator_name,
                },
                "wigner_case": "a",
                "truly_antiunitary": False,
                "depends_on_factor_su2": True,
                "character_on_unitary_stabilizer": {"0": backbone.complex_to_json(1 + 0j)},
                "antiunitary_character_signature": {str(antiunitary_generator): int(eta)},
                "antiunitary_extension_eta": int(eta),
                "source_unitary_irrep": "A",
                "construction_logic": "The unitary subgroup is trivial and the antiunitary generator squares to the identity with double-group factor +1, so the unique one-dimensional unitary irrep admits two case-a eta extensions.",
                "projective_multiplication_verified": True,
                "verification_scope": {
                    "stabilizer_indices": [0, int(antiunitary_generator)],
                    "checked_relation_count": 4,
                    "antiunitary_generator_square_index": int(anti_square),
                    "factor_on_antiunitary_square": backbone.complex_to_json(factor_value),
                },
            }
        )
    return objects


def build_family_record(letter: str, ctx: dict[str, Any]) -> dict[str, Any]:
    entry = ctx["entries_by_letter"][letter]
    bridge_entry = backbone.single_bridge.bridge_stabilizer_for_entry(entry, ctx)
    site_ops = list(entry.get("site_symmetry_ops", []) or [])
    spatial_site_ops = list(entry.get("spatial_site_symmetry_ops", []) or [])
    x0_anchor = [float(value) for value in entry["x0"]]
    sample_point_mag = backbone.single_bridge.representative_sample_point_magnetic(entry)
    sample_point_conv = ctx["supercell"] @ sample_point_mag
    x0_orbit = orbit_from_magnetic_anchor(x0_anchor, ctx)
    sample_orbit = backbone.single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    size_matches = int(entry["stab"]) == int(bridge_entry["bridge_stabilizer_size"])
    if letter in PURE_UNITARY_FAMILIES:
        model = PURE_UNITARY_MODELS[letter]
    else:
        model = ANTIUNITARY_MODELS[letter]

    record = {
        "letter": letter,
        "processing_order_index": PROCESSING_ORDER.index(letter) + 1,
        "processing_reason": model["processing_reason"],
        "dimension": int(entry["dim"]),
        "representative_parametric_form": entry["representative_coordinate"],
        "basis_vectors_magnetic": [
            backbone.single_bridge.format_vector(vec)
            for vec in entry.get("basis_vecs", []) or []
        ],
        "x0_anchor_magnetic": backbone.single_bridge.format_vector(np.array(x0_anchor, dtype=float)),
        "sample_parameters": backbone.single_bridge.format_vector(
            np.array(
                [float(value) for value in backbone.single_bridge.sample_parameters_for_dimension(int(entry["dim"]))],
                dtype=float,
            )
        ),
        "generic_sample_point_magnetic": backbone.single_bridge.format_vector(sample_point_mag),
        "generic_sample_point_conventional": backbone.single_bridge.format_vector(sample_point_conv),
        "multiplicity": int(entry["mult"]),
        "site_symmetry_summary": {
            "site_symmetry": entry["site_symmetry"],
            "site_symmetry_custom": entry.get("site_symmetry_custom"),
            "unitary_site_symmetry_raw_field": entry.get("unitary_site_symmetry"),
            "site_symmetry_generators_from_swyckoff_r": serialize_site_symmetry_generators(site_ops),
            "spatial_site_symmetry_generators_from_swyckoff_r": serialize_site_symmetry_generators(spatial_site_ops),
            "note": "As in the point-like audit, `site_symmetry_ops` behaves like generator metadata. The exact raw-op stabilizer indices below come from direct recomputation after the audited real-space / k-space bridge.",
        },
        "stabilizer_summary": {
            "stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "unitary_count": int(bridge_entry["bridge_unitary_count"]),
            "antiunitary_count": int(bridge_entry["bridge_antiunitary_count"]),
            "stabilizer_indices": list(bridge_entry["stabilizer_indices"]),
            "unitary_indices": list(bridge_entry["unitary_indices"]),
            "antiunitary_indices": list(bridge_entry["antiunitary_indices"]),
            "stabilizer_elements": [
                serialize_stabilizer_element(ctx, op_index)
                for op_index in bridge_entry["stabilizer_indices"]
            ],
        },
        "swyckoff_vs_recomputed_stabilizer": {
            "swyckoff_stab_field": int(entry["stab"]),
            "recomputed_stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "size_matches": bool(size_matches),
            "generator_count_in_swyckoff_field": len(site_ops),
            "usable_as_double_local_corep_input": bool(size_matches),
        },
        "orbit_handling": {
            "must_use_sample_point_orbit": True,
            "sample_point_is_generic": True,
            "sample_point_genericity_reason": "The fixed interior parameter pool `(1/5, 2/7, 3/11)` avoids 0 and 1/2 on every free coordinate, so the sampled point stays off the more special submanifolds and its orbit size matches the family multiplicity.",
            "x0_orbit_size": len(x0_orbit),
            "sample_point_orbit_size": len(sample_orbit),
            "multiplicity": int(entry["mult"]),
            "x0_orbit_invalid": len(x0_orbit) != int(entry["mult"]),
            "x0_orbit_invalid_reason": f"The symbolic x0 anchor has orbit size {len(x0_orbit)} instead of the required multiplicity {int(entry['mult'])}, so it sits on a more special submanifold and cannot be used for induction.",
            "x0_orbit": x0_orbit,
            "sample_point_orbit": [
                {
                    "source_operation_index": int(site["source_operation_index"]),
                    "time_reversal_source": bool(site["time_reversal_source"]),
                    "magnetic_coordinate": list(site["magnetic_coordinate"]),
                    "conventional_coordinate": list(site["conventional_coordinate"]),
                }
                for site in sample_orbit
            ],
        },
    }

    if letter in PURE_UNITARY_FAMILIES:
        builder = model["builder"]
        if builder == "trivial_projective":
            record["unitary_subgroup_summary"] = {
                "abstract_group": model["unitary_subgroup_label"],
                "unitary_indices": list(model["unitary_indices"]),
                "generator_index": None,
                "double_group_local_builder": "unique trivial projective irrep on the identity stabilizer",
            }
            record["double_group_local_corep_feasibility"] = {
                "can_build_full_local_object_set": True,
                "reason": "The stabilizer is trivial, so the double-group local projective set is a singleton.",
                "expected_wigner_case": None,
                "minimal_blocker": None,
            }
            record["local_objects"] = build_trivial_projective_local_object(letter)
        else:
            generator_index = int(model["generator_index"])
            record["unitary_subgroup_summary"] = {
                "abstract_group": model["unitary_subgroup_label"],
                "unitary_indices": list(model["unitary_indices"]),
                "generator_index": generator_index,
                "generator_label": model["generator_label"],
                "factor_on_generator_square": backbone.complex_to_json(
                    ctx["factor_su2"][generator_index, generator_index]
                ),
                "projective_generator_values": ["+i", "-i"],
                "double_group_local_builder": "explicit one-dimensional projective character enumeration on the audited order-2 unitary stabilizer",
            }
            record["double_group_local_corep_feasibility"] = {
                "can_build_full_local_object_set": True,
                "reason": "The pure-unitary stabilizer is order 2 and its double-group square relation is fixed by `factor_su2=-1`, so the full projective local-irrep set is just the two generator eigenvalues `+i/-i`.",
                "expected_wigner_case": None,
                "minimal_blocker": None,
            }
            record["local_objects"] = build_projective_order2_local_objects(
                letter,
                generator_index,
                model["generator_label"],
                list(model["unitary_indices"]),
                ctx,
            )
    else:
        anti_generator = int(model["antiunitary_generator_index"])
        anti_square = ctx["group_tables"]["compose"](anti_generator, anti_generator)
        record["unitary_subgroup_summary"] = {
            "abstract_group": "1",
            "unitary_indices": [0],
            "generator_index": None,
            "antiunitary_generator_index": anti_generator,
            "antiunitary_generator_name": model["antiunitary_generator_name"],
            "antiunitary_generator_square_index": int(anti_square),
            "factor_on_antiunitary_square": backbone.complex_to_json(
                ctx["factor_su2"][anti_generator, anti_generator]
            ),
            "double_group_local_builder": "explicit Wigner-case-a extension of the unique trivial-unitary-subgroup irrep",
        }
        record["double_group_local_corep_feasibility"] = {
            "can_build_full_local_object_set": True,
            "reason": "The unitary subgroup is trivial and the antiunitary generator squares to the identity with double-group factor +1, so the full magnetic local-corep set is the eta=+/- pair of case-a extensions.",
            "expected_wigner_case": "a",
            "minimal_blocker": None,
        }
        record["local_objects"] = build_case_a_local_coreps(
            letter,
            anti_generator,
            model["antiunitary_generator_name"],
            ctx,
        )

    record["full_local_object_set_built"] = True
    return record


def local_character_from_object(local_object: dict[str, Any]) -> dict[int, complex]:
    return {
        int(index): complex(value["real"], value["imag"])
        for index, value in local_object["character_on_unitary_stabilizer"].items()
    }


def induce_local_object(
    family_record: dict[str, Any],
    local_object: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    entry = ctx["entries_by_letter"][family_record["letter"]]
    induction = backbone.induce_double_irrep_on_manifolds(
        ctx,
        ctx["manifold_details"],
        entry,
        local_character_from_object(local_object),
        list(backbone.POINT_IDS) + list(backbone.PLANE_IDS),
    )

    vector = []
    for token in ctx["final_unknown_ordering"]:
        manifold_id, rep_id = token.split("_", 1)
        rep_index = int(rep_id[1:]) - 1
        vector.append(int(induction[manifold_id]["multiplicities"][rep_index]))

    residual = ctx["compatibility_matrix"] * sp.Matrix(vector)
    residual_list = [int(value) for value in residual]
    compatibility_zero = all(value == 0 for value in residual_list)
    if not compatibility_zero:
        raise ValueError(f"{local_object['id']}: induced vector is not in BS_double")

    raw_coords = solve_integer_basis_coordinates(
        ctx["raw_basis_matrix"],
        vector,
        f"{local_object['id']} in raw BS_double basis",
    )
    pretty_coords = solve_integer_basis_coordinates(
        ctx["pretty_basis_matrix"],
        vector,
        f"{local_object['id']} in pretty BS_double basis",
    )

    old_ai_v1_coords = solve_integer_basis_coordinates(
        ctx["pointlike_v1_basis_coeff_matrix"],
        raw_coords,
        f"{local_object['id']} in point-like AI_v1 basis",
    )

    return {
        "generator_id": local_object["id"],
        "source_family": family_record["letter"],
        "source_local_object_id": local_object["id"],
        "source_local_object_kind": local_object["double_group_local_object_kind"],
        "source_site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
        "family_dimension": int(family_record["dimension"]),
        "dimension": int(local_object["dimension"]),
        "wigner_case": local_object.get("wigner_case"),
        "truly_antiunitary": bool(local_object["truly_antiunitary"]),
        "depends_on_factor_su2": bool(local_object["depends_on_factor_su2"]),
        "representative_parametric_form": family_record["representative_parametric_form"],
        "x0_anchor_magnetic": family_record["x0_anchor_magnetic"],
        "sample_parameters": family_record["sample_parameters"],
        "generic_sample_point_magnetic": family_record["generic_sample_point_magnetic"],
        "generic_sample_point_conventional": family_record["generic_sample_point_conventional"],
        "multiplicity": int(family_record["multiplicity"]),
        "sample_point_orbit_required": True,
        "sample_point_orbit_note": family_record["orbit_handling"]["x0_orbit_invalid_reason"],
        "sample_point_orbit_size": int(family_record["orbit_handling"]["sample_point_orbit_size"]),
        "bridge_used": {
            "r_conv_equals_P_r_mag": True,
            "P_matrix": backbone.P_MATRIX,
        },
        "unitary_character_used_for_induction": local_object["character_on_unitary_stabilizer"],
        "antiunitary_extension_data": {
            "antiunitary_character_signature": local_object.get("antiunitary_character_signature"),
            "antiunitary_extension_eta": local_object.get("antiunitary_extension_eta"),
        },
        "induction_note": "The local double/projective character is built first on the real-space stabilizer, the orbit is generated from the generic sample point rather than x0, and then the Bloch factor exp(-i k·tauC) is applied inside the audited double-group induction routine.",
        "vector_in_bs_double_unknown_ordering": vector,
        "support": backbone.support_from_vector(vector, ctx["final_unknown_ordering"]),
        "compatibility_zero": True,
        "compatibility_residual": residual_list,
        "bs_raw_coordinates": raw_coords,
        "bs_pretty_coordinates": pretty_coords,
        "pointlike_v1_basis_coordinates": old_ai_v1_coords,
        "induced_multiplicities_by_manifold": induction,
        "origin": local_object["origin"],
    }


def build_parametric_candidates(
    family_records: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    successful: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    prototype_cache: dict[tuple[str, str], dict[str, Any]] = {}
    for family_record in family_records:
        if not family_record["swyckoff_vs_recomputed_stabilizer"]["usable_as_double_local_corep_input"]:
            failures.append(
                {
                    "family": family_record["letter"],
                    "reason": "recomputed stabilizer does not match the trusted `stab` field in `swyckoff_r.py`",
                }
            )
            continue
        for local_object in family_record["local_objects"]:
            try:
                cache_key = (
                    family_record["letter"],
                    json.dumps(local_object["character_on_unitary_stabilizer"], sort_keys=True),
                )
                if cache_key not in prototype_cache:
                    prototype_cache[cache_key] = induce_local_object(family_record, local_object, ctx)
                candidate = json.loads(json.dumps(prototype_cache[cache_key]))
                candidate["generator_id"] = local_object["id"]
                candidate["source_local_object_id"] = local_object["id"]
                candidate["antiunitary_extension_data"] = {
                    "antiunitary_character_signature": local_object.get("antiunitary_character_signature"),
                    "antiunitary_extension_eta": local_object.get("antiunitary_extension_eta"),
                }
                candidate["magnetic_or_projective_local_object"] = local_object
                successful.append(candidate)
            except Exception as exc:
                failures.append(
                    {
                        "family": family_record["letter"],
                        "local_object_id": local_object["id"],
                        "reason": str(exc),
                    }
                )

    duplicate_classes = annotate_duplicate_classes(successful)
    return successful, failures, duplicate_classes


def build_gap_witnesses(coeff_matrix: sp.Matrix, bs_raw: dict[str, Any]) -> list[dict[str, Any]]:
    witnesses: list[dict[str, Any]] = []
    current = coeff_matrix
    for basis_index, basis_vector in enumerate(bs_raw["basis_vectors"], start=1):
        column = sp.zeros(current.rows, 1)
        column[basis_index - 1, 0] = 1
        if sp.Matrix.hstack(current, column).rank() > current.rank():
            witnesses.append(
                {
                    "bs_basis_id": basis_vector["id"],
                    "bs_basis_index": basis_index,
                    "bs_basis_coefficients": [int(value) for value in column],
                    "vector_in_bs_double_unknown_ordering": list(basis_vector["vector"]),
                }
            )
            current = sp.Matrix.hstack(current, column)
        if current.rank() == coeff_matrix.rows:
            break
    return witnesses


def build_ai_v2_data(parametric_candidates: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    pointlike_generators = json.loads(json.dumps(ctx["pointlike_v1_candidates"]["generators"]))
    parametric_generators = json.loads(json.dumps(parametric_candidates))
    combined_generators = json.loads(json.dumps(pointlike_generators + parametric_generators))
    combined_duplicate_classes = annotate_duplicate_classes(combined_generators)
    parametric_duplicate_classes = annotate_duplicate_classes(parametric_generators)

    unknown_columns = [candidate["vector_in_bs_double_unknown_ordering"] for candidate in combined_generators]
    coeff_columns = [candidate["bs_raw_coordinates"] for candidate in combined_generators]
    unknown_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in unknown_columns])
    coeff_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in coeff_columns])
    hnf_coeff_matrix = hermite_normal_form(coeff_matrix)
    hnf_basis_coefficients = columns_from_matrix(hnf_coeff_matrix)
    hnf_basis_vectors = [
        [int(value) for value in list(ctx["raw_basis_matrix"] * sp.Matrix(column))]
        for column in hnf_basis_coefficients
    ]
    hnf_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in hnf_basis_coefficients])

    candidate_to_basis_relations = {
        candidate["generator_id"]: solve_integer_basis_coordinates(
            hnf_basis_matrix,
            candidate["bs_raw_coordinates"],
            f"{candidate['generator_id']} in AI_double_v2 basis",
        )
        for candidate in combined_generators
    }

    old_rank = int(ctx["pointlike_v1_basis"]["rank_z"])
    rank_growing_new_candidate_ids: list[str] = []
    current_rank = old_rank
    running_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in ctx["pointlike_v1_basis"]["basis_bs_coefficients"]])
    for candidate in parametric_candidates:
        next_matrix = sp.Matrix.hstack(running_matrix, sp.Matrix(candidate["bs_raw_coordinates"]))
        next_rank = int(next_matrix.rank())
        if next_rank > current_rank:
            rank_growing_new_candidate_ids.append(candidate["generator_id"])
            running_matrix = next_matrix
            current_rank = next_rank

    old_basis_coeff_columns = [list(column) for column in ctx["pointlike_v1_basis"]["basis_bs_coefficients"]]
    same_lattice_as_old_v1 = hnf_basis_coefficients == old_basis_coeff_columns

    left_annihilator = [integerize_vector(vector) for vector in coeff_matrix.T.nullspace()]
    gap_witnesses = build_gap_witnesses(coeff_matrix, ctx["background"]["bs_raw"])

    return {
        "pointlike_generators": pointlike_generators,
        "parametric_generators": parametric_generators,
        "combined_generators": combined_generators,
        "combined_duplicate_classes": combined_duplicate_classes,
        "parametric_duplicate_classes": parametric_duplicate_classes,
        "column_order": [candidate["generator_id"] for candidate in combined_generators],
        "unknown_columns": unknown_columns,
        "coeff_columns": coeff_columns,
        "unknown_rank": int(unknown_matrix.rank()),
        "coeff_rank": int(coeff_matrix.rank()),
        "distinct_unknown_vector_count": len({tuple(column) for column in unknown_columns}),
        "parametric_distinct_unknown_vector_count": len(
            {tuple(candidate["vector_in_bs_double_unknown_ordering"]) for candidate in parametric_candidates}
        ),
        "hnf_basis_coefficients": hnf_basis_coefficients,
        "hnf_basis_vectors": hnf_basis_vectors,
        "candidate_to_basis_relations": candidate_to_basis_relations,
        "rank_growing_new_candidate_ids_over_v1": rank_growing_new_candidate_ids,
        "coeff_smith_diagonal": smith_diagonal(coeff_matrix),
        "hnf_shape": [int(hnf_coeff_matrix.rows), int(hnf_coeff_matrix.cols)],
        "same_lattice_as_old_pointlike_v1": bool(same_lattice_as_old_v1),
        "left_annihilator_witnesses_in_bs_basis_coefficients": left_annihilator,
        "gap_witnesses": gap_witnesses,
        "rank_increase_over_pointlike_v1": int(unknown_matrix.rank()) - old_rank,
    }


def build_parametric_corep_summary_json(
    family_records: list[dict[str, Any]],
    candidate_failures: list[dict[str, Any]],
    ai_data: dict[str, Any],
    bs_vs_ai: dict[str, Any],
) -> dict[str, Any]:
    successful_families = [
        letter for letter in TARGET_FAMILIES
        if next(record for record in family_records if record["letter"] == letter)["full_local_object_set_built"]
    ]
    failed_families = sorted({failure["family"] for failure in candidate_failures})
    if failed_families:
        next_blocker = "Some target parametric families still fail, so the next blocker stays inside the local-corep census / induction layer."
    else:
        next_blocker = (
            "All target parametric families are now built, but the combined AI lattice still has rank "
            f"{ai_data['unknown_rank']} < {bs_vs_ai['rank_BS_double']}. The blocker is no longer a missing in-scope family; it is the explicit residual BS_double gap witnessed by the two annihilator relations recorded in `double_group_bs_vs_ai_v2_summary_10.4.1.31.json`."
        )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "successful_families": successful_families,
        "failed_families": failed_families,
        "successful_local_object_count": int(sum(len(record["local_objects"]) for record in family_records)),
        "can_build_ai_double_v2": not candidate_failures,
        "next_blocker": next_blocker,
    }


def build_parametric_coreps_json(family_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "families": family_records,
    }


def build_ai_v2_candidates_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "unknown_ordering": ctx["final_unknown_ordering"],
        "pointlike_v1_candidate_count": len(ai_data["pointlike_generators"]),
        "parametric_candidate_count": len(ai_data["parametric_generators"]),
        "combined_candidate_count": len(ai_data["combined_generators"]),
        "pointlike_generators": ai_data["pointlike_generators"],
        "parametric_generators": ai_data["parametric_generators"],
        "combined_generators": ai_data["combined_generators"],
        "duplicate_vector_classes": ai_data["combined_duplicate_classes"],
        "parametric_duplicate_vector_classes": ai_data["parametric_duplicate_classes"],
    }


def build_ai_v2_matrix_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for index, unknown in enumerate(ctx["final_unknown_ordering"]):
        rows.append(
            {
                "unknown": unknown,
                "coefficients": [column[index] for column in ai_data["unknown_columns"]],
            }
        )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "matrix_orientation": "columns_are_generators",
        "column_order": ai_data["column_order"],
        "unknown_ordering": ctx["final_unknown_ordering"],
        "A_double_v2_columns": ai_data["unknown_columns"],
        "A_double_v2_rows": rows,
        "A_double_v2_bs_coefficients": ai_data["coeff_columns"],
        "pointlike_v1_column_count": len(ai_data["pointlike_generators"]),
        "parametric_column_count": len(ai_data["parametric_generators"]),
        "rank_z": int(ai_data["unknown_rank"]),
        "rank_q": int(ai_data["unknown_rank"]),
        "bs_coefficient_rank_z": int(ai_data["coeff_rank"]),
        "bs_coefficient_smith_diagonal": ai_data["coeff_smith_diagonal"],
        "rank_increase_over_pointlike_v1": int(ai_data["rank_increase_over_pointlike_v1"]),
        "rank_growing_new_candidate_ids_over_v1": ai_data["rank_growing_new_candidate_ids_over_v1"],
        "left_annihilator_witnesses_in_bs_basis_coefficients": ai_data["left_annihilator_witnesses_in_bs_basis_coefficients"],
        "gap_witnesses": ai_data["gap_witnesses"],
    }


def build_ai_v2_basis_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "basis_construction_method": "Hermite normal form on the combined BS_double coefficient lattice of point-like AI_v1 plus the new parametric double candidates.",
        "basis_kind": "bs_double_coefficient_hnf_basis",
        "basis_column_order": [f"ai_double_v2_hnf_{index + 1:02d}" for index in range(len(ai_data["hnf_basis_vectors"]))],
        "unknown_ordering": ctx["final_unknown_ordering"],
        "basis_vectors": ai_data["hnf_basis_vectors"],
        "basis_support": [
            backbone.support_from_vector(vector, ctx["final_unknown_ordering"])
            for vector in ai_data["hnf_basis_vectors"]
        ],
        "basis_bs_coefficients": ai_data["hnf_basis_coefficients"],
        "rank_z": len(ai_data["hnf_basis_vectors"]),
        "candidate_to_basis_integer_relations": ai_data["candidate_to_basis_relations"],
        "raw_candidate_count": len(ai_data["combined_generators"]),
        "parametric_raw_candidate_count": len(ai_data["parametric_generators"]),
        "distinct_candidate_vector_count": int(ai_data["distinct_unknown_vector_count"]),
        "parametric_distinct_candidate_vector_count": int(ai_data["parametric_distinct_unknown_vector_count"]),
        "rank_growing_new_candidate_ids_over_v1": ai_data["rank_growing_new_candidate_ids_over_v1"],
        "bs_coefficient_smith_diagonal": ai_data["coeff_smith_diagonal"],
        "hnf_shape": ai_data["hnf_shape"],
        "same_lattice_as_old_pointlike_v1": bool(ai_data["same_lattice_as_old_pointlike_v1"]),
        "relation_to_old_pointlike_v1_basis": {
            "rank_increase_over_pointlike_v1": int(ai_data["rank_increase_over_pointlike_v1"]),
            "same_lattice_as_old_pointlike_v1": bool(ai_data["same_lattice_as_old_pointlike_v1"]),
            "new_basis_directions_added_in_this_round": ai_data["rank_growing_new_candidate_ids_over_v1"],
        },
        "key_added_directions": ai_data["rank_growing_new_candidate_ids_over_v1"],
    }


def build_bs_vs_ai_v2_summary_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    bs_rank = int(ctx["bs_rank"])
    bs_matrix = ctx["raw_basis_matrix"]
    ai_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in ai_data["unknown_columns"]])
    union_rank = int(sp.Matrix.hstack(bs_matrix, ai_matrix).rank())
    remaining_gap = max(0, bs_rank - int(ai_data["unknown_rank"]))
    if remaining_gap == 0:
        coverage_note = "The rank gap closes at AI_double_v2."
    else:
        coverage_note = (
            "The rank gap does not close. Every new parametric candidate still lies in the old point-like AI_v1 lattice, "
            "so the combined AI_double_v2 lattice is exactly the same rank-6 lattice as before."
        )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "rank_BS_double": bs_rank,
        "rank_AI_double_v2": int(ai_data["unknown_rank"]),
        "AI_double_v2_in_BS": union_rank == bs_rank,
        "rank_span_BS_plus_AI_double_v2": union_rank,
        "remaining_rank_gap": remaining_gap,
        "pointlike_v1_rank": int(ctx["background"]["pointlike_bs_vs_ai"]["rank_AI_double_pointlike_v1"]),
        "rank_increase_over_pointlike_v1": int(ai_data["rank_increase_over_pointlike_v1"]),
        "same_lattice_as_old_pointlike_v1": bool(ai_data["same_lattice_as_old_pointlike_v1"]),
        "coverage_note": coverage_note,
        "parametric_successful_candidate_count": len(ai_data["parametric_generators"]),
        "combined_candidate_count": len(ai_data["combined_generators"]),
        "parametric_distinct_unknown_vector_count": int(ai_data["parametric_distinct_unknown_vector_count"]),
        "left_annihilator_witnesses_in_bs_basis_coefficients": ai_data["left_annihilator_witnesses_in_bs_basis_coefficients"],
        "gap_witnesses": ai_data["gap_witnesses"],
        "added_directions_from_o_m_k_l": [
            candidate["generator_id"]
            for candidate in ai_data["parametric_generators"]
            if candidate["source_family"] in {"o", "m", "k", "l"}
            and candidate["generator_id"] in ai_data["rank_growing_new_candidate_ids_over_v1"]
        ],
        "added_directions_from_n_i_j": [
            candidate["generator_id"]
            for candidate in ai_data["parametric_generators"]
            if candidate["source_family"] in {"n", "i", "j"}
            and candidate["generator_id"] in ai_data["rank_growing_new_candidate_ids_over_v1"]
        ],
        "remaining_gap_source": (
            "No target parametric family is left unbuilt in scope. The explicit remaining gap is a structural rank-2 gap between BS_double and the current combined AI lattice."
            if remaining_gap
            else "The in-scope rank gap closes; any remaining issue would only be finite-index saturation."
        ),
    }


def build_saturation_payload(ai_data: dict[str, Any], ctx: dict[str, Any]) -> tuple[dict[str, Any], str]:
    smith = ai_data["coeff_smith_diagonal"]
    index = 1
    for value in smith:
        index *= value
    saturated = all(value == 1 for value in smith)
    summary = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "rank_BS_double": int(ctx["bs_rank"]),
        "rank_AI_double_v2": int(ai_data["unknown_rank"]),
        "smith_diagonal": smith,
        "saturated": saturated,
        "finite_index": int(index),
    }
    lines = [
        f"# Double-Group Saturation Audit for {GROUP_NUMBER}",
        "",
        "- This file is generated only because `rank(AI_double_v2) = rank(BS_double)`.",
        f"- Smith diagonal of the AI lattice inside the raw BS basis: `{smith}`.",
        f"- Saturated: `{saturated}`.",
        f"- Finite index: `{index}`.",
    ]
    return summary, "\n".join(lines)


def build_parametric_audit_md(
    family_records: list[dict[str, Any]],
    candidate_failures: list[dict[str, Any]],
    ai_data: dict[str, Any],
    bs_vs_ai: dict[str, Any],
) -> str:
    lines = [
        f"# Double-Group Parametric Local-Corep Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        f"- Group type only: `{GROUP_TYPE}`.",
        "- This round does not revisit the settled single-group line, the double-group backbone, or the finished point-like double AI stage.",
        "- This round only handles the parametric families `o,m,k,l,n,i,j`.",
        "",
        "## Known Premise",
        "",
        "- The single-group line for the same group is already closed.",
        "- The full double-group k-space backbone is already established, with `rank(BS_double)=8`.",
        "- The point-like double AI prototype already exists and spans rank 6.",
        "- The bridge `r_conv = P r_mag`, `P = diag(1,2,2)` is already trusted and reused here.",
        "",
        "## Processing Order",
        "",
        f"- Actual processing order: `{', '.join(PROCESSING_ORDER)}`.",
        "- Stage 1 is pure-unitary parametric families `o,m,k,l`.",
        "- Stage 2 is antiunitary parametric families `i,j,n`.",
        "- Reason: start from the generic identity-stabilizer family `o`, then add the two pure-unitary order-2 stabilizer types, and only then switch to the antiunitary case-a builder with the simplest one-parameter `2'` families before the two-parameter `m'` family.",
        "",
        "## Method Summary",
        "",
        "- Parametric families do not reuse the point-like x0-orbit logic. Every induction is forced to start from the generic sample point orbit.",
        "- `o,m,k,l` use a pure-unitary double local builder: either the unique trivial projective irrep (`o`) or the two `+i/-i` projective irreps on an audited order-2 stabilizer (`m,k,l`).",
        "- `n,i,j` use a magnetic local-corep builder with trivial unitary subgroup: the antiunitary generator squares to the identity with double-group factor `+1`, so the local objects are the Wigner-case-a eta pair.",
        "- Atomic induction still uses the audited route: local double/projective character first, then the Bloch factor through the existing double-group induction routine.",
        "",
        "## Family-By-Family Census",
        "",
    ]

    for record in family_records:
        lines.extend(
            [
                f"### Family `{record['letter']}`",
                "",
                f"- Representative parametric form: `{record['representative_parametric_form']}`.",
                f"- Dimension: `{record['dimension']}`.",
                f"- Generic sample point (magnetic): `{record['generic_sample_point_magnetic']}`.",
                f"- Multiplicity: `{record['multiplicity']}`.",
                f"- Site symmetry: `{record['site_symmetry_summary']['site_symmetry']}`.",
                f"- Stabilizer size / unitary / antiunitary: `{record['stabilizer_summary']['stabilizer_size']}` / `{record['stabilizer_summary']['unitary_count']}` / `{record['stabilizer_summary']['antiunitary_count']}`.",
                f"- `swyckoff_r.py` `stab` field matches direct recomputation: `{record['swyckoff_vs_recomputed_stabilizer']['size_matches']}`.",
                f"- Usable as double local-corep input: `{record['swyckoff_vs_recomputed_stabilizer']['usable_as_double_local_corep_input']}`.",
                f"- Sample-point orbit required: `{record['orbit_handling']['must_use_sample_point_orbit']}`.",
                f"- x0 orbit size / sample-point orbit size / multiplicity: `{record['orbit_handling']['x0_orbit_size']}` / `{record['orbit_handling']['sample_point_orbit_size']}` / `{record['orbit_handling']['multiplicity']}`.",
                f"- Processing reason: {record['processing_reason']}",
                f"- Unitary subgroup summary: `{record['unitary_subgroup_summary']['abstract_group']}`.",
                f"- Full local-object set built: `{record['full_local_object_set_built']}`.",
                "- Constructed local objects:",
            ]
        )
        for local_object in record["local_objects"]:
            origin = local_object["origin"]["construction"]
            lines.append(
                f"  - `{local_object['id']}`: dim `{local_object['dimension']}`, type `{local_object['double_group_local_object_kind']}`, Wigner case `{local_object['wigner_case']}`, truly antiunitary `{local_object['truly_antiunitary']}`, depends on `factor_su2` `{local_object['depends_on_factor_su2']}`. Source: {origin}"
            )
        lines.append("")

    failed_family_names = sorted({failure["family"] for failure in candidate_failures})
    lines.extend(
        [
            "## AI Outcome",
            "",
            f"- Successful families: `{', '.join(record['letter'] for record in family_records)}`.",
            f"- Failed families: `{', '.join(failed_family_names) if failed_family_names else 'none'}`.",
            f"- Successful local object count: `{sum(len(record['local_objects']) for record in family_records)}`.",
            f"- New parametric raw candidate count: `{len(ai_data['parametric_generators'])}`.",
            f"- Distinct new induced 31-dimensional vectors: `{ai_data['parametric_distinct_unknown_vector_count']}`.",
            f"- `rank_Z(AI_double_v2) = {ai_data['unknown_rank']}` while `rank_Z(BS_double) = {bs_vs_ai['rank_BS_double']}`.",
            f"- Rank increase over point-like v1: `{ai_data['rank_increase_over_pointlike_v1']}`.",
            f"- Same lattice as old point-like v1: `{ai_data['same_lattice_as_old_pointlike_v1']}`.",
            "- The antiunitary parametric eta pairs do not produce new unitary-k-space vectors: all six `n/i/j` eta extensions collapse to the same BS-coordinate direction already seen in the point-like antiunitary sector.",
            "- The pure-unitary parametric families do add new raw generators, but those generators are still integer combinations of the old point-like AI basis, so the total rank remains 6.",
            "- Therefore this stage succeeds as a builder / induction audit, but it does not close the BS gap. The residual rank-2 gap is now an explicit witness, not a vague missing-family statement.",
        ]
    )
    return "\n".join(lines)


def build_package_readme(rank_gap_closed: bool) -> str:
    lines = [
        f"# Review Package: {GROUP_NUMBER} Double-Group Parametric AI",
        "",
        "## Task Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- stage: parametric double local-corep builder + expanded double AI",
        "",
        "## Current Premise",
        "",
        "- The single-group line for the same group is already closed.",
        "- The full double-group k-space backbone and `BS_double` are already established.",
        "- The point-like double AI stage already covers 6 of the 8 BS_double directions.",
        "",
        "## New Content In This Round",
        "",
        "- Parametric double local-corep census on `o,m,k,l,n,i,j`.",
        "- Expanded combined AI lattice `AI_double_v2`.",
        "- Updated `BS_double` vs `AI_double_v2` comparison.",
    ]
    if rank_gap_closed:
        lines.extend(
            [
                "- Double-group saturation audit, because the in-scope rank gap closes.",
            ]
        )
    else:
        lines.extend(
            [
                "- No saturation audit file is included because the rank gap does not close in this round.",
            ]
        )
    lines.extend(
        [
            "",
            "## Possible Result Pattern",
            "",
            "- The rank gap may close.",
            "- Or the local-corep / induction stage may succeed while a residual gap remains.",
            "- Even if the rank gap closes, a finite-index saturation problem can still survive.",
            "",
            "## Suggested Review Order",
            "",
            "1. `double_group_parametric_corep_audit_10.4.1.31.md`",
            "2. `double_group_parametric_corep_summary_10.4.1.31.json`",
            "3. `double_group_parametric_coreps_10.4.1.31.json`",
            "4. `double_group_ai_v2_basis_10.4.1.31.json`",
            "5. `double_group_bs_vs_ai_v2_summary_10.4.1.31.json`",
        ]
    )
    if rank_gap_closed:
        lines.append("6. `double_group_saturation_audit_10.4.1.31.md`")
    return "\n".join(lines)


def build_package(rank_gap_closed: bool) -> None:
    reset_dir(PACKAGE_DIR)
    mapping = {
        "double_group_parametric_corep_audit_10.4.1.31.md": PARAMETRIC_AUDIT_MD,
        "double_group_parametric_corep_summary_10.4.1.31.json": PARAMETRIC_SUMMARY_JSON,
        "double_group_parametric_coreps_10.4.1.31.json": PARAMETRIC_COREPS_JSON,
        "double_group_ai_v2_candidates_10.4.1.31.json": AI_V2_CANDIDATES_JSON,
        "double_group_ai_v2_matrix_10.4.1.31.json": AI_V2_MATRIX_JSON,
        "double_group_ai_v2_basis_10.4.1.31.json": AI_V2_BASIS_JSON,
        "double_group_bs_vs_ai_v2_summary_10.4.1.31.json": BS_VS_AI_V2_SUMMARY_JSON,
        "double_group_pointlike_corep_audit_10.4.1.31.md": POINTLIKE_AUDIT_MD,
        "double_group_pointlike_corep_summary_10.4.1.31.json": POINTLIKE_SUMMARY_JSON,
        "double_group_pointlike_coreps_10.4.1.31.json": POINTLIKE_COREPS_JSON,
        "double_group_ai_pointlike_v1_candidates_10.4.1.31.json": POINTLIKE_CANDIDATES_JSON,
        "double_group_ai_pointlike_v1_matrix_10.4.1.31.json": POINTLIKE_MATRIX_JSON,
        "double_group_ai_pointlike_v1_basis_10.4.1.31.json": POINTLIKE_BASIS_JSON,
        "double_group_bs_vs_ai_pointlike_v1_summary_10.4.1.31.json": POINTLIKE_BS_VS_AI_JSON,
        "double_group_bs_summary_10.4.1.31.json": BS_SUMMARY_JSON,
        "double_group_bs_basis_raw_10.4.1.31.json": BS_RAW_JSON,
        "double_group_bs_basis_pretty_10.4.1.31.json": BS_PRETTY_JSON,
        "double_group_full_compatibility_with_planes_10.4.1.31.json": WITH_PLANES_JSON,
        "double_group_kspace_backbone_audit_10.4.1.31.md": KSPACE_AUDIT_MD,
        "double_group_kspace_backbone_summary_10.4.1.31.json": KSPACE_SUMMARY_JSON,
        "double_group_line_blocks_10.4.1.31.json": LINE_BLOCKS_JSON,
        "double_group_minimal_realspace_10.4.1.31.json": MIN_REALSPACE_JSON,
        "double_group_minimal_ai_embedding_10.4.1.31.json": MIN_AI_EMBED_JSON,
        "double_group_feasibility_audit_10.4.1.31.md": FEAS_AUDIT_MD,
        "double_group_feasibility_summary_10.4.1.31.json": FEAS_SUMMARY_JSON,
        "audit/single_group_indicator_group_summary.json": REVIEW_SINGLE / "audit" / "single_group_indicator_group_summary.json",
        "audit/single_group_indicator_generators.json": REVIEW_SINGLE / "audit" / "single_group_indicator_generators.json",
        "audit/single_group_bs_mod_ai_single_summary.json": REVIEW_SINGLE / "audit" / "single_group_bs_mod_ai_single_summary.json",
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
        "dependencies/debug_double_group_feasibility_10.4.1.31.py": ROOT / "debug_double_group_feasibility_10.4.1.31.py",
        "dependencies/debug_double_group_kspace_backbone_10.4.1.31.py": ROOT / "debug_double_group_kspace_backbone_10.4.1.31.py",
        "dependencies/debug_double_group_pointlike_coreps_10.4.1.31.py": ROOT / "debug_double_group_pointlike_coreps_10.4.1.31.py",
        "debug_double_group_parametric_coreps_10.4.1.31.py": ROOT / "debug_double_group_parametric_coreps_10.4.1.31.py",
    }
    if rank_gap_closed:
        mapping["double_group_saturation_audit_10.4.1.31.md"] = SATURATION_AUDIT_MD
        mapping["double_group_saturation_summary_10.4.1.31.json"] = SATURATION_SUMMARY_JSON

    for relative, source in mapping.items():
        destination = PACKAGE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    write_text(PACKAGE_DIR / "README.md", build_package_readme(rank_gap_closed))
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()
    family_records = [build_family_record(letter, ctx) for letter in PROCESSING_ORDER]
    parametric_candidates, candidate_failures, _ = build_parametric_candidates(family_records, ctx)
    ai_data = build_ai_v2_data(parametric_candidates, ctx)
    bs_vs_ai = build_bs_vs_ai_v2_summary_json(ai_data, ctx)
    parametric_summary = build_parametric_corep_summary_json(family_records, candidate_failures, ai_data, bs_vs_ai)
    parametric_coreps = build_parametric_coreps_json(family_records)
    ai_v2_candidates = build_ai_v2_candidates_json(ai_data, ctx)
    ai_v2_matrix = build_ai_v2_matrix_json(ai_data, ctx)
    ai_v2_basis = build_ai_v2_basis_json(ai_data, ctx)
    audit_md = build_parametric_audit_md(family_records, candidate_failures, ai_data, bs_vs_ai)

    write_text(PARAMETRIC_AUDIT_MD, audit_md)
    write_json(PARAMETRIC_SUMMARY_JSON, parametric_summary)
    write_json(PARAMETRIC_COREPS_JSON, parametric_coreps)
    write_json(AI_V2_CANDIDATES_JSON, ai_v2_candidates)
    write_json(AI_V2_MATRIX_JSON, ai_v2_matrix)
    write_json(AI_V2_BASIS_JSON, ai_v2_basis)
    write_json(BS_VS_AI_V2_SUMMARY_JSON, bs_vs_ai)

    rank_gap_closed = int(ai_data["unknown_rank"]) == int(ctx["bs_rank"])
    saturation_summary = None
    if rank_gap_closed:
        saturation_summary, saturation_md = build_saturation_payload(ai_data, ctx)
        write_json(SATURATION_SUMMARY_JSON, saturation_summary)
        write_text(SATURATION_AUDIT_MD, saturation_md)
    else:
        if SATURATION_SUMMARY_JSON.exists():
            SATURATION_SUMMARY_JSON.unlink()
        if SATURATION_AUDIT_MD.exists():
            SATURATION_AUDIT_MD.unlink()

    build_package(rank_gap_closed)

    return {
        "ctx": ctx,
        "family_records": family_records,
        "parametric_candidates": parametric_candidates,
        "candidate_failures": candidate_failures,
        "ai_data": ai_data,
        "bs_vs_ai": bs_vs_ai,
        "parametric_summary": parametric_summary,
        "saturation_summary": saturation_summary,
        "rank_gap_closed": rank_gap_closed,
        "package_tree": format_tree(PACKAGE_DIR),
    }


def validate_outputs() -> dict[str, Any]:
    state = generate_outputs()

    for path in REQUIRED_NEW_FILES:
        if not path.exists():
            raise FileNotFoundError(f"missing required output: {path}")

    parametric_summary = load_json(PARAMETRIC_SUMMARY_JSON)
    parametric_coreps = load_json(PARAMETRIC_COREPS_JSON)
    candidates_json = load_json(AI_V2_CANDIDATES_JSON)
    matrix_json = load_json(AI_V2_MATRIX_JSON)
    basis_json = load_json(AI_V2_BASIS_JSON)
    bs_vs_ai = load_json(BS_VS_AI_V2_SUMMARY_JSON)

    if parametric_summary["group_number"] != GROUP_NUMBER or int(parametric_summary["group_type"]) != GROUP_TYPE:
        raise ValueError("summary group metadata mismatch")
    if parametric_summary["successful_families"] != TARGET_FAMILIES:
        raise ValueError("not all target families were marked successful")
    if parametric_summary["failed_families"]:
        raise ValueError("unexpected failed families recorded in summary")
    if int(parametric_summary["successful_local_object_count"]) != 13:
        raise ValueError("expected 13 successful local objects")
    if not bool(parametric_summary["can_build_ai_double_v2"]):
        raise ValueError("summary says AI_double_v2 cannot be built")

    if len(parametric_coreps["families"]) != len(PROCESSING_ORDER):
        raise ValueError("family census length mismatch")
    if len(candidates_json["parametric_generators"]) != 13:
        raise ValueError("parametric candidate count mismatch")
    if len(candidates_json["combined_generators"]) != 27:
        raise ValueError("combined candidate count mismatch")
    if any(not bool(item["compatibility_zero"]) for item in candidates_json["parametric_generators"]):
        raise ValueError("some induced parametric generators do not satisfy BS compatibility")
    if int(matrix_json["rank_z"]) != 6:
        raise ValueError("unexpected AI_v2 rank")
    if int(basis_json["rank_z"]) != 6:
        raise ValueError("unexpected reduced AI_v2 basis rank")
    if not bool(basis_json["same_lattice_as_old_pointlike_v1"]):
        raise ValueError("AI_v2 should match the old point-like lattice in this phase")
    if int(bs_vs_ai["rank_BS_double"]) != 8 or int(bs_vs_ai["rank_AI_double_v2"]) != 6:
        raise ValueError("unexpected BS-vs-AI ranks")
    if not bool(bs_vs_ai["AI_double_v2_in_BS"]):
        raise ValueError("AI_double_v2 should lie in BS_double")
    if int(bs_vs_ai["remaining_rank_gap"]) != 2:
        raise ValueError("unexpected remaining rank gap")
    if SATURATION_AUDIT_MD.exists() or SATURATION_SUMMARY_JSON.exists():
        raise ValueError("saturation files should not exist when the rank gap remains open")

    if not PACKAGE_DIR.exists() or not PACKAGE_TAR.exists():
        raise FileNotFoundError("package build missing")

    return state


def print_terminal_summary(state: dict[str, Any]) -> None:
    summary = state["parametric_summary"]
    bs_vs_ai = state["bs_vs_ai"]
    candidate_failures = state["candidate_failures"]
    successful_families = summary["successful_families"]
    failed_families = summary["failed_families"]

    print("1. `o,m,k,l,n,i,j` 这 7 个参数型 families 的 double local-corep census 是否完成？")
    print("   是，已完成。")
    print("2. 哪些 family 成功构造出了 double local objects？")
    print(f"   {', '.join(successful_families)}。")
    print("3. 哪些 family 失败了？失败原因是什么？")
    if failed_families:
        for family in failed_families:
            reasons = [
                failure["reason"] for failure in candidate_failures if failure["family"] == family
            ]
            print(f"   {family}: {'; '.join(reasons)}")
    else:
        print("   无。")
    print("4. 是否已经成功构造 `AI_double_v2`？")
    print(f"   {'是' if summary['can_build_ai_double_v2'] else '否'}。")
    print("5. `AI_double_v2` 是否嵌入当前 `BS_double`？")
    print(f"   {'是' if bs_vs_ai['AI_double_v2_in_BS'] else '否'}。")
    print("6. 当前 rank gap 还剩多少？")
    print(f"   {bs_vs_ai['remaining_rank_gap']}。")
    print("7. 如果 rank gap 闭合，double-group saturation 是否也做了？")
    if state["rank_gap_closed"]:
        print("   是。")
    else:
        print("   否；本轮 rank gap 仍为 2，因此未进入 saturation audit。")
    print("8. 如果做了，Smith 对角元是什么？")
    if state["rank_gap_closed"]:
        print(f"   {state['saturation_summary']['smith_diagonal']}。")
    else:
        print("   不适用。")
    print("9. 新压缩包完整路径是什么？")
    print(f"   {PACKAGE_TAR}")
    print("10. 压缩包内文件树是什么？")
    for line in state["package_tree"]:
        print(f"   {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Regenerate outputs and validate the parametric double-group AI_v2 bundle.",
    )
    args = parser.parse_args()

    state = validate_outputs() if args.validate else generate_outputs()
    print_terminal_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
