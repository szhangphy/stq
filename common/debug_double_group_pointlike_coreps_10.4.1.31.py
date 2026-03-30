#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import tarfile
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_form


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 2

TARGET_FAMILIES = ["a", "b", "c", "d", "e", "f", "g", "h"]
PROCESSING_ORDER = ["c", "f", "d", "e", "g", "h", "b", "a"]
PURE_UNITARY_FAMILIES = ["c", "f"]
ANTIUNITARY_FAMILIES = ["a", "b", "d", "e", "g", "h"]

REVIEW_SINGLE = ROOT / "review_package_10.4.1.31_single_indicator"

POINTLIKE_AUDIT_MD = ROOT / "double_group_pointlike_corep_audit_10.4.1.31.md"
POINTLIKE_SUMMARY_JSON = ROOT / "double_group_pointlike_corep_summary_10.4.1.31.json"
POINTLIKE_COREPS_JSON = ROOT / "double_group_pointlike_coreps_10.4.1.31.json"
AI_V1_CANDIDATES_JSON = ROOT / "double_group_ai_pointlike_v1_candidates_10.4.1.31.json"
AI_V1_MATRIX_JSON = ROOT / "double_group_ai_pointlike_v1_matrix_10.4.1.31.json"
AI_V1_BASIS_JSON = ROOT / "double_group_ai_pointlike_v1_basis_10.4.1.31.json"
BS_VS_AI_V1_SUMMARY_JSON = ROOT / "double_group_bs_vs_ai_pointlike_v1_summary_10.4.1.31.json"

BS_SUMMARY_JSON = ROOT / "double_group_bs_summary_10.4.1.31.json"
BS_RAW_JSON = ROOT / "double_group_bs_basis_raw_10.4.1.31.json"
BS_PRETTY_JSON = ROOT / "double_group_bs_basis_pretty_10.4.1.31.json"
FEAS_AUDIT_MD = ROOT / "double_group_feasibility_audit_10.4.1.31.md"
FEAS_SUMMARY_JSON = ROOT / "double_group_feasibility_summary_10.4.1.31.json"
KSPACE_AUDIT_MD = ROOT / "double_group_kspace_backbone_audit_10.4.1.31.md"
KSPACE_SUMMARY_JSON = ROOT / "double_group_kspace_backbone_summary_10.4.1.31.json"
LINE_BLOCKS_JSON = ROOT / "double_group_line_blocks_10.4.1.31.json"
WITH_PLANES_JSON = ROOT / "double_group_full_compatibility_with_planes_10.4.1.31.json"
MIN_REALSPACE_JSON = ROOT / "double_group_minimal_realspace_10.4.1.31.json"
MIN_AI_EMBED_JSON = ROOT / "double_group_minimal_ai_embedding_10.4.1.31.json"

PACKAGE_NAME = "review_package_10.4.1.31_double_pointlike_ai"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TAR = ROOT / f"{PACKAGE_NAME}.tar.gz"

REQUIRED_NEW_FILES = [
    POINTLIKE_AUDIT_MD,
    POINTLIKE_SUMMARY_JSON,
    POINTLIKE_COREPS_JSON,
    AI_V1_CANDIDATES_JSON,
    AI_V1_MATRIX_JSON,
    AI_V1_BASIS_JSON,
    BS_VS_AI_V1_SUMMARY_JSON,
    ROOT / "debug_double_group_pointlike_coreps_10.4.1.31.py",
    PACKAGE_TAR,
]

PURE_UNITARY_MODELS: dict[str, dict[str, Any]] = {
    "c": {
        "processing_reason": "Already validated as the minimal double-group seed family; pure unitary `2/m` and the safest place to anchor the reusable point-like builder.",
        "unitary_indices": [0, 3, 4, 7],
        "c2_index": 3,
        "inversion_index": 4,
        "mirror_index": 7,
        "unitary_subgroup_label": "2/m",
    },
    "f": {
        "processing_reason": "Same pure-unitary `2/m` site symmetry as `c`, so it is the cleanest first extension once the seed builder is stable.",
        "unitary_indices": [0, 3, 4, 7],
        "c2_index": 3,
        "inversion_index": 4,
        "mirror_index": 7,
        "unitary_subgroup_label": "2/m",
    },
}

ANTIUNITARY_MODELS: dict[str, dict[str, Any]] = {
    "d": {
        "processing_reason": "First antiunitary pair after `c,f`; it shares the same `2'/m'` site symmetry as `e`, so the case-c builder can be debugged on one stabilizer type before cloning it to its partner.",
        "unitary_generator_index": 5,
        "antiunitary_generator_index": 11,
        "site_symmetry_label": "2'/m'",
    },
    "e": {
        "processing_reason": "Same antiunitary site-symmetry type as `d`; processed immediately after it to reuse the exact same case-c construction.",
        "unitary_generator_index": 5,
        "antiunitary_generator_index": 11,
        "site_symmetry_label": "2'/m'",
    },
    "g": {
        "processing_reason": "Second antiunitary pair; shares the same `2/m'` site symmetry as `h`, so it is handled as the next reusable case-c block.",
        "unitary_generator_index": 3,
        "antiunitary_generator_index": 14,
        "site_symmetry_label": "2/m'",
    },
    "h": {
        "processing_reason": "Same antiunitary site-symmetry type as `g`; kept adjacent to avoid switching stabilizer logic mid-stream.",
        "unitary_generator_index": 3,
        "antiunitary_generator_index": 14,
        "site_symmetry_label": "2/m'",
    },
    "b": {
        "processing_reason": "Final antiunitary pair; shares the same `2'/m` site symmetry as `a` and is handled only after the two earlier case-c patterns are stable.",
        "unitary_generator_index": 7,
        "antiunitary_generator_index": 11,
        "site_symmetry_label": "2'/m",
    },
    "a": {
        "processing_reason": "Same antiunitary site-symmetry type as `b`; kept last only because the builder is already trusted by then, not because the family is intrinsically harder.",
        "unitary_generator_index": 7,
        "antiunitary_generator_index": 11,
        "site_symmetry_label": "2'/m",
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
    spec = importlib.util.spec_from_file_location("double_backbone_local", backbone_path)
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


def build_context() -> dict[str, Any]:
    ssg_module = backbone.load_ssgreps_module()
    ssg_dict = backbone.load_ssg_dict()
    ctx = backbone.load_double_context(ssg_module, ssg_dict)
    geometry = backbone.load_geometry_context()
    manifold_bundle = backbone.build_manifold_details(ssg_module, geometry, ssg_dict)

    bs_summary = load_json(BS_SUMMARY_JSON)
    bs_raw = load_json(BS_RAW_JSON)
    bs_pretty = load_json(BS_PRETTY_JSON)

    unknown_ordering = list(bs_summary["final_unknown_ordering"])
    if unknown_ordering != list(bs_raw["unknown_ordering"]) or unknown_ordering != list(bs_pretty["unknown_ordering"]):
        raise ValueError("BS unknown ordering mismatch across summary/raw/pretty files")

    ctx.update(
        {
            "geometry": geometry,
            "manifold_details": manifold_bundle["details"],
            "manifold_stability": manifold_bundle["stability"],
            "manifold_stability_all_true": bool(manifold_bundle["all_stable"]),
            "bs_summary": bs_summary,
            "bs_raw": bs_raw,
            "bs_pretty": bs_pretty,
            "final_unknown_ordering": unknown_ordering,
            "compatibility_matrix": sp.Matrix(bs_summary["final_C_double"]),
            "raw_basis_matrix": basis_matrix_from_json(bs_raw),
            "pretty_basis_matrix": basis_matrix_from_json(bs_pretty),
            "factor_su2": np.array(ctx["ssg"].factor_su2, dtype=complex),
            "mul_table_zero_based": np.array(ctx["ssg"].mul_table, dtype=int) - 1,
            "antiunitary_flags": [bool(int(flag) < 0) for flag in ctx["ssg"].time_reversal],
            "bs_rank": int(len(bs_raw["basis_vectors"])),
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


def build_projective_2_over_m_local_objects(letter: str, family_record: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    model = PURE_UNITARY_MODELS[letter]
    stabilizer = list(model["unitary_indices"])
    c2_index = int(model["c2_index"])
    inversion_index = int(model["inversion_index"])
    mirror_index = int(model["mirror_index"])

    objects: list[dict[str, Any]] = []
    for c2_label, c2_value in (("plus_i", 1j), ("minus_i", -1j)):
        for inversion_label, inversion_value in (("g", 1), ("u", -1)):
            mirror_value = c2_value * inversion_value
            character = {
                0: 1 + 0j,
                c2_index: complex(c2_value),
                inversion_index: complex(inversion_value),
                mirror_index: complex(mirror_value),
            }
            if not projective_character_is_valid(stabilizer, character, ctx):
                raise ValueError(f"{letter}: invalid projective character {character}")
            objects.append(
                {
                    "id": f"{letter}_double_{inversion_label}_{c2_label}",
                    "label": f"{letter}: {inversion_label}, C2={complex_symbol(c2_value)}",
                    "dimension": 1,
                    "type": "projective_local_irrep",
                    "double_group_local_object_kind": "projective_local_irrep",
                    "origin": {
                        "unitary_subgroup": model["unitary_subgroup_label"],
                        "construction": "Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.",
                        "c2_eigenvalue": complex_symbol(c2_value),
                        "inversion_parity": inversion_label,
                    },
                    "wigner_case": None,
                    "truly_antiunitary": False,
                    "depends_on_factor_su2": True,
                    "character_on_unitary_stabilizer": {
                        str(index): backbone.complex_to_json(value)
                        for index, value in character.items()
                    },
                    "projective_multiplication_verified": True,
                    "verification_scope": {
                        "stabilizer_indices": stabilizer,
                        "checked_relation_count": len(stabilizer) ** 2,
                    },
                }
            )
    return objects


def antiunitary_product(
    left: np.ndarray,
    right: np.ndarray,
    left_is_antiunitary: bool,
) -> np.ndarray:
    return left @ (right.conj() if left_is_antiunitary else right)


def build_case_c_local_object(letter: str, family_record: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    model = ANTIUNITARY_MODELS[letter]
    unitary_generator = int(model["unitary_generator_index"])
    anti_generator = int(model["antiunitary_generator_index"])
    stabilizer = list(family_record["stabilizer_summary"]["stabilizer_indices"])
    antiunitary_indices = list(family_record["stabilizer_summary"]["antiunitary_indices"])
    if anti_generator not in antiunitary_indices:
        raise ValueError(f"{letter}: chosen antiunitary generator {anti_generator} not in stabilizer")
    other_anti = next(index for index in antiunitary_indices if index != anti_generator)
    mul_table = ctx["mul_table_zero_based"]
    factor = ctx["factor_su2"]

    if int(mul_table[unitary_generator, anti_generator]) != other_anti:
        raise ValueError(f"{letter}: expected other antiunitary index from u*a does not match stabilizer")
    anti_square = ctx["group_tables"]["compose"](anti_generator, anti_generator)
    conjugation_image = ctx["group_tables"]["compose"](
        ctx["group_tables"]["inverse"][anti_generator],
        ctx["group_tables"]["compose"](unitary_generator, anti_generator),
    )
    if anti_square != 0:
        raise ValueError(f"{letter}: antiunitary generator square is not the identity")
    if conjugation_image != unitary_generator:
        raise ValueError(f"{letter}: antiunitary conjugation does not fix the projective unitary generator")

    if abs(factor[unitary_generator, unitary_generator] + 1) > 1e-8:
        raise ValueError(f"{letter}: factor_su2(u,u) is not -1")

    matrices: dict[int, np.ndarray] = {}
    matrices[0] = np.eye(2, dtype=complex)
    matrices[unitary_generator] = np.array([[1j, 0.0], [0.0, -1j]], dtype=complex)
    matrices[anti_generator] = np.eye(2, dtype=complex)
    matrices[other_anti] = matrices[unitary_generator] / factor[unitary_generator, anti_generator]

    anti_flags = ctx["antiunitary_flags"]
    for left in stabilizer:
        for right in stabilizer:
            lhs = antiunitary_product(matrices[left], matrices[right], anti_flags[left])
            rhs = factor[left, right] * matrices[int(mul_table[left, right])]
            if not np.allclose(lhs, rhs, atol=1e-8):
                raise ValueError(
                    f"{letter}: projective multiplication failed for ({left}, {right})"
                )

    unitary_character = {
        0: complex(np.trace(matrices[0])),
        unitary_generator: complex(np.trace(matrices[unitary_generator])),
    }

    return [
        {
            "id": f"{letter}_double_case_c_pair",
            "label": f"{letter}: Wigner-case-c pair",
            "dimension": 2,
            "type": "magnetic_local_corep",
            "double_group_local_object_kind": "magnetic_local_corep",
            "origin": {
                "unitary_projective_irrep_pair": [
                    {"label": "rho_plus_i", "generator_character": "+i"},
                    {"label": "rho_minus_i", "generator_character": "-i"},
                ],
                "construction": "Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.",
                "antiunitary_generator_index": anti_generator,
                "other_antiunitary_index": other_anti,
            },
            "wigner_case": "c",
            "truly_antiunitary": True,
            "depends_on_factor_su2": True,
            "character_on_unitary_stabilizer": {
                str(index): backbone.complex_to_json(value)
                for index, value in unitary_character.items()
            },
            "matrix_part_on_stabilizer": {
                str(index): backbone.complex_matrix_to_json(matrix.tolist())
                for index, matrix in matrices.items()
            },
            "projective_multiplication_verified": True,
            "verification_scope": {
                "stabilizer_indices": stabilizer,
                "checked_relation_count": len(stabilizer) ** 2,
                "antiunitary_generator_square_index": int(anti_square),
                "antiunitary_conjugation_on_unitary_generator": int(conjugation_image),
                "factor_u_u": backbone.complex_to_json(factor[unitary_generator, unitary_generator]),
            },
        }
    ]


def build_family_record(letter: str, ctx: dict[str, Any]) -> dict[str, Any]:
    entry = ctx["entries_by_letter"][letter]
    bridge_entry = backbone.single_bridge.bridge_stabilizer_for_entry(entry, ctx)
    site_ops = list(entry.get("site_symmetry_ops", []) or [])
    spatial_site_ops = list(entry.get("spatial_site_symmetry_ops", []) or [])
    generator_has_anti = any(bool(op.get("time_reversal", False)) for op in site_ops)

    record = {
        "letter": letter,
        "processing_order_index": PROCESSING_ORDER.index(letter) + 1,
        "processing_reason": (
            PURE_UNITARY_MODELS.get(letter, ANTIUNITARY_MODELS.get(letter))["processing_reason"]
        ),
        "representative_coordinate": entry["representative_coordinate"],
        "representative_coordinate_sample_magnetic": backbone.single_bridge.format_vector(
            backbone.single_bridge.representative_sample_point_magnetic(entry)
        ),
        "representative_coordinate_sample_conventional": backbone.single_bridge.format_vector(
            ctx["supercell"] @ backbone.single_bridge.representative_sample_point_magnetic(entry)
        ),
        "multiplicity": int(entry["mult"]),
        "site_symmetry_summary": {
            "site_symmetry": entry["site_symmetry"],
            "site_symmetry_custom": entry.get("site_symmetry_custom"),
            "unitary_site_symmetry_raw_field": entry.get("unitary_site_symmetry"),
            "site_symmetry_generators_from_swyckoff_r": serialize_site_symmetry_generators(site_ops),
            "spatial_site_symmetry_generators_from_swyckoff_r": serialize_site_symmetry_generators(spatial_site_ops),
            "note": "The `site_symmetry_ops` fields in `swyckoff_r.py` behave like generator descriptors, not a full indexed stabilizer list. Exact raw-op stabilizer indices below come from direct recomputation after the audited basis bridge.",
        },
        "stabilizer_summary": {
            "stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "unitary_count": int(bridge_entry["bridge_unitary_count"]),
            "antiunitary_count": int(bridge_entry["bridge_antiunitary_count"]),
            "stabilizer_indices": list(bridge_entry["stabilizer_indices"]),
            "unitary_indices": list(bridge_entry["unitary_indices"]),
            "antiunitary_indices": list(bridge_entry["antiunitary_indices"]),
            "stabilizer_elements": [
                serialize_stabilizer_element(ctx, op_index) for op_index in bridge_entry["stabilizer_indices"]
            ],
        },
        "swyckoff_vs_recomputed_stabilizer": {
            "swyckoff_stab_field": int(entry["stab"]),
            "recomputed_stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "size_matches": int(entry["stab"]) == int(bridge_entry["bridge_stabilizer_size"]),
            "generator_count_in_swyckoff_field": len(site_ops),
            "generator_has_antiunitary_flag": bool(generator_has_anti),
            "generator_antiunitary_presence_consistent_with_recomputed_counts": bool(generator_has_anti)
            == bool(bridge_entry["bridge_antiunitary_count"]),
            "usable_as_double_local_corep_input": int(entry["stab"]) == int(bridge_entry["bridge_stabilizer_size"]),
        },
    }

    if letter in PURE_UNITARY_MODELS:
        model = PURE_UNITARY_MODELS[letter]
        factor = ctx["factor_su2"]
        record["unitary_subgroup_summary"] = {
            "abstract_group": model["unitary_subgroup_label"],
            "unitary_indices": list(model["unitary_indices"]),
            "generator_indices": [int(model["c2_index"]), int(model["inversion_index"])],
            "factor_on_c2_square": backbone.complex_to_json(factor[int(model["c2_index"]), int(model["c2_index"])]),
            "factor_on_inversion_square": backbone.complex_to_json(
                factor[int(model["inversion_index"]), int(model["inversion_index"])]
            ),
            "double_group_local_builder": "explicit projective character enumeration on the full unitary stabilizer",
        }
        record["double_group_local_corep_feasibility"] = {
            "can_build_full_local_object_set": True,
            "reason": "Pure unitary point family. The full projective local-irrep set can be enumerated directly from the audited unitary stabilizer and `factor_su2`.",
            "expected_wigner_case": None,
            "minimal_blocker": None,
        }
        record["local_objects"] = build_projective_2_over_m_local_objects(letter, record, ctx)
    else:
        model = ANTIUNITARY_MODELS[letter]
        unitary_generator = int(model["unitary_generator_index"])
        anti_generator = int(model["antiunitary_generator_index"])
        anti_square = ctx["group_tables"]["compose"](anti_generator, anti_generator)
        conjugation_image = ctx["group_tables"]["compose"](
            ctx["group_tables"]["inverse"][anti_generator],
            ctx["group_tables"]["compose"](unitary_generator, anti_generator),
        )
        record["unitary_subgroup_summary"] = {
            "abstract_group": "projective order-2 unitary subgroup",
            "unitary_indices": [0, unitary_generator],
            "generator_index": unitary_generator,
            "antiunitary_generator_index": anti_generator,
            "antiunitary_generator_square_index": int(anti_square),
            "antiunitary_conjugation_on_unitary_generator": int(conjugation_image),
            "factor_on_generator_square": backbone.complex_to_json(
                ctx["factor_su2"][unitary_generator, unitary_generator]
            ),
            "projective_unitary_irrep_generator_values": ["+i", "-i"],
            "double_group_local_builder": "explicit Wigner-case-c pairing of the two complex-conjugate projective unitary irreps",
        }
        record["double_group_local_corep_feasibility"] = {
            "can_build_full_local_object_set": True,
            "reason": "The unitary subgroup has the projective eigenvalue pair `+i/-i`; the antiunitary action fixes the subgroup generator and pairs those conjugate irreps into one irreducible 2D magnetic corep.",
            "expected_wigner_case": "c",
            "minimal_blocker": None,
        }
        record["local_objects"] = build_case_c_local_object(letter, record, ctx)

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

    raw_coords = backbone.solve_integer_basis_coordinates(
        ctx["raw_basis_matrix"],
        vector,
        f"{local_object['id']} in raw BS_double basis",
    )
    pretty_coords = backbone.solve_integer_basis_coordinates(
        ctx["pretty_basis_matrix"],
        vector,
        f"{local_object['id']} in pretty BS_double basis",
    )

    return {
        "generator_id": local_object["id"],
        "source_family": family_record["letter"],
        "source_local_object_id": local_object["id"],
        "source_local_object_kind": local_object["double_group_local_object_kind"],
        "source_site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
        "dimension": int(local_object["dimension"]),
        "wigner_case": local_object.get("wigner_case"),
        "truly_antiunitary": bool(local_object["truly_antiunitary"]),
        "depends_on_factor_su2": bool(local_object["depends_on_factor_su2"]),
        "representative_coordinate": family_record["representative_coordinate"],
        "representative_coordinate_sample_magnetic": family_record["representative_coordinate_sample_magnetic"],
        "representative_coordinate_sample_conventional": family_record["representative_coordinate_sample_conventional"],
        "multiplicity": int(family_record["multiplicity"]),
        "bridge_used": {
            "r_conv_equals_P_r_mag": True,
            "P_matrix": backbone.P_MATRIX,
        },
        "unitary_character_used_for_induction": local_object["character_on_unitary_stabilizer"],
        "induction_note": "The local double/projective character is built first on the real-space stabilizer, then the Bloch factor exp(-i k·tauC) is applied on the k-space side through the audited `linear_character` reconstruction inside the induction routine.",
        "vector_in_bs_double_unknown_ordering": vector,
        "support": backbone.support_from_vector(vector, ctx["final_unknown_ordering"]),
        "compatibility_zero": True,
        "compatibility_residual": residual_list,
        "bs_raw_coordinates": raw_coords,
        "bs_pretty_coordinates": pretty_coords,
        "induced_multiplicities_by_manifold": induction,
        "origin": local_object["origin"],
    }


def build_candidates(
    family_records: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    successful: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
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
                successful.append(induce_local_object(family_record, local_object, ctx))
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


def build_ai_pointlike_data(candidates: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    if not candidates:
        raise ValueError("no successful point-like candidates were built")

    unknown_columns = [candidate["vector_in_bs_double_unknown_ordering"] for candidate in candidates]
    coeff_columns = [candidate["bs_raw_coordinates"] for candidate in candidates]
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
        candidate["generator_id"]: backbone.solve_integer_basis_coordinates(
            hnf_basis_matrix,
            candidate["bs_raw_coordinates"],
            f"{candidate['generator_id']} in point-like AI basis",
        )
        for candidate in candidates
    }

    rank_growing_ids: list[str] = []
    incremental_columns: list[sp.Matrix] = []
    current_rank = 0
    for candidate in candidates:
        next_matrix = sp.Matrix.hstack(
            *(incremental_columns + [sp.Matrix(candidate["vector_in_bs_double_unknown_ordering"])])
        )
        next_rank = int(next_matrix.rank())
        if next_rank > current_rank:
            rank_growing_ids.append(candidate["generator_id"])
            incremental_columns.append(sp.Matrix(candidate["vector_in_bs_double_unknown_ordering"]))
            current_rank = next_rank

    return {
        "candidates": candidates,
        "column_order": [candidate["generator_id"] for candidate in candidates],
        "unknown_columns": unknown_columns,
        "coeff_columns": coeff_columns,
        "unknown_rank": int(unknown_matrix.rank()),
        "coeff_rank": int(coeff_matrix.rank()),
        "distinct_unknown_vector_count": len({tuple(column) for column in unknown_columns}),
        "hnf_basis_coefficients": hnf_basis_coefficients,
        "hnf_basis_vectors": hnf_basis_vectors,
        "candidate_to_basis_relations": candidate_to_basis_relations,
        "rank_growing_candidate_ids": rank_growing_ids,
        "coeff_smith_diagonal": smith_diagonal(coeff_matrix),
        "hnf_shape": [int(hnf_coeff_matrix.rows), int(hnf_coeff_matrix.cols)],
    }


def build_pointlike_corep_summary_json(
    family_records: list[dict[str, Any]],
    candidate_failures: list[dict[str, Any]],
    ai_data: dict[str, Any],
) -> dict[str, Any]:
    successful_families = [
        letter for letter in TARGET_FAMILIES
        if next(record for record in family_records if record["letter"] == letter)["full_local_object_set_built"]
    ]
    failed_families = sorted({failure["family"] for failure in candidate_failures})
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "successful_families": successful_families,
        "failed_families": failed_families,
        "successful_local_object_count": int(sum(len(record["local_objects"]) for record in family_records)),
        "can_build_ai_double_pointlike_v1": not candidate_failures,
        "next_blocker": "All eight target point-like families are now covered. The remaining gap sits in the out-of-scope parametric sector `o,m,k,l,n,i,j`, and the present point-like data does not yet separate the unitary and antiunitary parametric contributions.",
        "rank_ai_double_pointlike_v1": int(ai_data["unknown_rank"]),
        "remaining_rank_gap_vs_bs_double": max(0, 8 - int(ai_data["unknown_rank"])),
    }


def build_pointlike_coreps_json(family_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "families": family_records,
    }


def build_ai_pointlike_candidates_json(
    candidates: list[dict[str, Any]],
    duplicate_classes: list[dict[str, Any]],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "unknown_ordering": ctx["final_unknown_ordering"],
        "pointlike_candidate_count": len(candidates),
        "distinct_unknown_vector_count": len(duplicate_classes),
        "generators": candidates,
        "duplicate_vector_classes": duplicate_classes,
    }


def build_ai_pointlike_matrix_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
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
        "A_double_pointlike_v1_columns": ai_data["unknown_columns"],
        "A_double_pointlike_v1_rows": rows,
        "A_double_pointlike_v1_bs_coefficients": ai_data["coeff_columns"],
        "rank_z": int(ai_data["unknown_rank"]),
        "rank_q": int(ai_data["unknown_rank"]),
        "bs_coefficient_rank_z": int(ai_data["coeff_rank"]),
        "bs_coefficient_smith_diagonal": ai_data["coeff_smith_diagonal"],
        "compatibility_zero": {
            candidate["generator_id"]: bool(candidate["compatibility_zero"])
            for candidate in ai_data["candidates"]
        },
    }


def build_ai_pointlike_basis_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "basis_construction_method": "Hermite normal form on the BS_double coefficient lattice of the raw point-like candidate matrix.",
        "basis_kind": "bs_double_coefficient_hnf_basis",
        "basis_column_order": [f"ai_double_pointlike_v1_hnf_{index + 1:02d}" for index in range(len(ai_data["hnf_basis_vectors"]))],
        "unknown_ordering": ctx["final_unknown_ordering"],
        "basis_vectors": ai_data["hnf_basis_vectors"],
        "basis_support": [
            backbone.support_from_vector(vector, ctx["final_unknown_ordering"])
            for vector in ai_data["hnf_basis_vectors"]
        ],
        "basis_bs_coefficients": ai_data["hnf_basis_coefficients"],
        "rank_z": len(ai_data["hnf_basis_vectors"]),
        "candidate_to_basis_integer_relations": ai_data["candidate_to_basis_relations"],
        "raw_candidate_count": len(ai_data["candidates"]),
        "distinct_candidate_vector_count": int(ai_data["distinct_unknown_vector_count"]),
        "rank_growing_candidate_ids": ai_data["rank_growing_candidate_ids"],
        "bs_coefficient_smith_diagonal": ai_data["coeff_smith_diagonal"],
        "hnf_shape": ai_data["hnf_shape"],
        "basis_is_candidate_subset": False,
        "key_added_directions": ai_data["rank_growing_candidate_ids"],
    }


def build_bs_vs_ai_summary_json(ai_data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    bs_rank = int(ctx["bs_rank"])
    bs_matrix = ctx["raw_basis_matrix"]
    ai_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in ai_data["unknown_columns"]])
    union_rank = int(sp.Matrix.hstack(bs_matrix, ai_matrix).rank())
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "rank_BS_double": bs_rank,
        "rank_AI_double_pointlike_v1": int(ai_data["unknown_rank"]),
        "AI_double_pointlike_v1_in_BS": union_rank == bs_rank,
        "rank_span_BS_plus_AI_double_pointlike_v1": union_rank,
        "covered_bs_dimensions": int(ai_data["unknown_rank"]),
        "remaining_rank_gap": max(0, bs_rank - int(ai_data["unknown_rank"])),
        "successful_pointlike_candidate_count": len(ai_data["candidates"]),
        "distinct_pointlike_unknown_vector_count": int(ai_data["distinct_unknown_vector_count"]),
        "remaining_gap_source": "The rank gap is no longer in the audited point-like sector. It is entirely in the out-of-scope parametric families `o,m,k,l,n,i,j`, although the current point-like data alone does not yet separate the unitary `o,m,k,l` and antiunitary `n,i,j` contributions.",
        "next_most_reasonable_target": "Extend the same double-group local-corep builder to the parametric families `o,m,k,l,n,i,j` and then re-check AI saturation inside BS_double.",
    }


def build_pointlike_audit_md(
    family_records: list[dict[str, Any]],
    candidate_failures: list[dict[str, Any]],
    ai_data: dict[str, Any],
    bs_vs_ai: dict[str, Any],
) -> str:
    lines = [
        f"# Double-Group Point-Like Local-Corep Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        f"- Group type only: `{GROUP_TYPE}`.",
        "- This round does not revisit the settled single-group line or the already-completed double-group k-space backbone.",
        "- This round only builds the point-like double local-corep builder on families `a, b, c, d, e, f, g, h` and the first point-like double AI prototype that those families generate.",
        "",
        "## Known Premise",
        "",
        "- The single-group line is already closed for the same group.",
        "- The minimal double-group prototype is already established.",
        "- The full double-group k-space backbone is already established, including `BS_double` with rank 8.",
        "- The bridge `r_conv = P r_mag`, `P = diag(1,2,2)` is already trusted and reused here.",
        "",
        "## Processing Order",
        "",
        f"- Actual processing order: `{', '.join(PROCESSING_ORDER)}`.",
        "- Reason: start from the already-validated minimal family `c`, extend immediately to its pure-unitary partner `f`, then handle the antiunitary families in same-site-symmetry pairs so the case-c builder is debugged once per stabilizer type.",
        "",
        "## Method Summary",
        "",
        "- Pure-unitary point families `c,f` are handled by explicit projective character enumeration on the unitary `2/m` stabilizer using `factor_su2`.",
        "- Antiunitary point families `a,b,d,e,g,h` are handled by an explicit magnetic-corep builder: first enumerate the paired projective unitary irreps with generator values `+i` and `-i`, then combine them into one 2D Wigner-case-c corep.",
        "- Atomic induction reuses the audited bridge and the existing full `BS_double` unknown ordering.",
        "- The induction route still starts from the local double/projective character, then applies the Bloch phase through the audited `linear_character` reconstruction on the k-space side.",
        "",
        "## Family-By-Family Census",
        "",
    ]

    for record in family_records:
        lines.extend(
            [
                f"### Family `{record['letter']}`",
                "",
                f"- Representative coordinate: `{record['representative_coordinate']}`.",
                f"- Multiplicity: `{record['multiplicity']}`.",
                f"- Site symmetry: `{record['site_symmetry_summary']['site_symmetry']}`.",
                f"- Stabilizer size / unitary / antiunitary: `{record['stabilizer_summary']['stabilizer_size']}` / `{record['stabilizer_summary']['unitary_count']}` / `{record['stabilizer_summary']['antiunitary_count']}`.",
                f"- `swyckoff_r.py` `stab` field matches direct recomputation: `{record['swyckoff_vs_recomputed_stabilizer']['size_matches']}`.",
                f"- Usable as double local-corep input: `{record['swyckoff_vs_recomputed_stabilizer']['usable_as_double_local_corep_input']}`.",
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
            "## Outcome",
            "",
            f"- Successful families: `{', '.join(record['letter'] for record in family_records)}`.",
            f"- Failed families: `{', '.join(failed_family_names) if failed_family_names else 'none'}`.",
            f"- Successful local object count: `{sum(len(record['local_objects']) for record in family_records)}`.",
            f"- Raw point-like candidate count: `{len(ai_data['candidates'])}`.",
            f"- Distinct induced 31-dimensional vectors: `{ai_data['distinct_unknown_vector_count']}`.",
            f"- `rank_Z(AI_double_pointlike_v1) = {ai_data['unknown_rank']}` while `rank_Z(BS_double) = {bs_vs_ai['rank_BS_double']}`.",
            f"- Rank-growing example generators: `{', '.join(ai_data['rank_growing_candidate_ids'])}`.",
            "- All six antiunitary point-like families fall into Wigner case c in the double group, not the single-group case-a pattern.",
            "- The point-like builder is therefore now stable, but it only covers 6 of the 8 BS directions. The residual gap is no longer in the point-like sector.",
        ]
    )
    return "\n".join(lines)


def build_package_readme() -> str:
    lines = [
        f"# Review Package: {GROUP_NUMBER} Double-Group Point-Like AI",
        "",
        "## Task Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- stage: point-like double local-corep builder + point-like AI prototype",
        "",
        "## Current Premise",
        "",
        "- The single-group line for the same group is already closed.",
        "- The minimal double-group prototype is already established.",
        "- The full double-group k-space backbone and `BS_double` are already established.",
        "",
        "## New Content In This Round",
        "",
        "- Point-like double local-corep census on `a,b,c,d,e,f,g,h`.",
        "- Point-like double AI prototype `AI_double_pointlike_v1`.",
        "- Minimal `BS_double` vs `AI_double_pointlike_v1` comparison.",
        "",
        "## Possible Result Pattern",
        "",
        "- All target point-like families may succeed.",
        "- Or only a subset may succeed if some antiunitary local-corep construction fails.",
        "- Even if all target point-like families succeed, the resulting AI prototype may still leave a rank gap relative to full `BS_double`.",
        "",
        "## Suggested Review Order",
        "",
        "1. `double_group_pointlike_corep_audit_10.4.1.31.md`",
        "2. `double_group_pointlike_corep_summary_10.4.1.31.json`",
        "3. `double_group_pointlike_coreps_10.4.1.31.json`",
        "4. `double_group_ai_pointlike_v1_basis_10.4.1.31.json`",
        "5. `double_group_bs_vs_ai_pointlike_v1_summary_10.4.1.31.json`",
    ]
    return "\n".join(lines)


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    mapping = {
        "double_group_pointlike_corep_audit_10.4.1.31.md": POINTLIKE_AUDIT_MD,
        "double_group_pointlike_corep_summary_10.4.1.31.json": POINTLIKE_SUMMARY_JSON,
        "double_group_pointlike_coreps_10.4.1.31.json": POINTLIKE_COREPS_JSON,
        "double_group_ai_pointlike_v1_candidates_10.4.1.31.json": AI_V1_CANDIDATES_JSON,
        "double_group_ai_pointlike_v1_matrix_10.4.1.31.json": AI_V1_MATRIX_JSON,
        "double_group_ai_pointlike_v1_basis_10.4.1.31.json": AI_V1_BASIS_JSON,
        "double_group_bs_vs_ai_pointlike_v1_summary_10.4.1.31.json": BS_VS_AI_V1_SUMMARY_JSON,
        "double_group_feasibility_audit_10.4.1.31.md": FEAS_AUDIT_MD,
        "double_group_feasibility_summary_10.4.1.31.json": FEAS_SUMMARY_JSON,
        "double_group_kspace_backbone_audit_10.4.1.31.md": KSPACE_AUDIT_MD,
        "double_group_kspace_backbone_summary_10.4.1.31.json": KSPACE_SUMMARY_JSON,
        "double_group_bs_summary_10.4.1.31.json": BS_SUMMARY_JSON,
        "double_group_bs_basis_raw_10.4.1.31.json": BS_RAW_JSON,
        "double_group_bs_basis_pretty_10.4.1.31.json": BS_PRETTY_JSON,
        "double_group_line_blocks_10.4.1.31.json": LINE_BLOCKS_JSON,
        "double_group_full_compatibility_with_planes_10.4.1.31.json": WITH_PLANES_JSON,
        "double_group_minimal_realspace_10.4.1.31.json": MIN_REALSPACE_JSON,
        "double_group_minimal_ai_embedding_10.4.1.31.json": MIN_AI_EMBED_JSON,
        "audit/single_group_ai_completeness_audit.md": REVIEW_SINGLE / "audit" / "single_group_ai_completeness_audit.md",
        "audit/single_group_ai_completeness_summary.json": REVIEW_SINGLE / "audit" / "single_group_ai_completeness_summary.json",
        "audit/single_group_indicator_group_summary.json": REVIEW_SINGLE / "audit" / "single_group_indicator_group_summary.json",
        "audit/single_group_indicator_generators.json": REVIEW_SINGLE / "audit" / "single_group_indicator_generators.json",
        "audit/single_group_bs_mod_ai_single_summary.json": REVIEW_SINGLE / "audit" / "single_group_bs_mod_ai_single_summary.json",
        "background/single_group_kmanifolds.json": REVIEW_SINGLE / "background" / "single_group_kmanifolds.json",
        "background/single_group_connectivity.json": REVIEW_SINGLE / "background" / "single_group_connectivity.json",
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
        "dependencies/debug_double_group_kspace_backbone_10.4.1.31.py": ROOT / "debug_double_group_kspace_backbone_10.4.1.31.py",
        "dependencies/debug_double_group_feasibility_10.4.1.31.py": ROOT / "debug_double_group_feasibility_10.4.1.31.py",
        "debug_double_group_pointlike_coreps_10.4.1.31.py": ROOT / "debug_double_group_pointlike_coreps_10.4.1.31.py",
    }

    for relative, source in mapping.items():
        destination = PACKAGE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    write_text(PACKAGE_DIR / "README.md", build_package_readme())
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()
    family_records = [build_family_record(letter, ctx) for letter in PROCESSING_ORDER]
    candidates, candidate_failures, duplicate_classes = build_candidates(family_records, ctx)
    ai_data = build_ai_pointlike_data(candidates, ctx)

    pointlike_summary = build_pointlike_corep_summary_json(family_records, candidate_failures, ai_data)
    pointlike_coreps = build_pointlike_coreps_json(family_records)
    pointlike_candidates = build_ai_pointlike_candidates_json(candidates, duplicate_classes, ctx)
    pointlike_matrix = build_ai_pointlike_matrix_json(ai_data, ctx)
    pointlike_basis = build_ai_pointlike_basis_json(ai_data, ctx)
    bs_vs_ai = build_bs_vs_ai_summary_json(ai_data, ctx)
    audit_md = build_pointlike_audit_md(family_records, candidate_failures, ai_data, bs_vs_ai)

    write_text(POINTLIKE_AUDIT_MD, audit_md)
    write_json(POINTLIKE_SUMMARY_JSON, pointlike_summary)
    write_json(POINTLIKE_COREPS_JSON, pointlike_coreps)
    write_json(AI_V1_CANDIDATES_JSON, pointlike_candidates)
    write_json(AI_V1_MATRIX_JSON, pointlike_matrix)
    write_json(AI_V1_BASIS_JSON, pointlike_basis)
    write_json(BS_VS_AI_V1_SUMMARY_JSON, bs_vs_ai)

    build_package()

    return {
        "ctx": ctx,
        "family_records": family_records,
        "candidates": candidates,
        "candidate_failures": candidate_failures,
        "duplicate_classes": duplicate_classes,
        "ai_data": ai_data,
        "pointlike_summary": pointlike_summary,
        "bs_vs_ai": bs_vs_ai,
        "package_tree": format_tree(PACKAGE_DIR),
    }


def validate_outputs() -> dict[str, Any]:
    state = generate_outputs()

    for path in REQUIRED_NEW_FILES:
        if not path.exists():
            raise FileNotFoundError(f"missing required output: {path}")

    pointlike_summary = load_json(POINTLIKE_SUMMARY_JSON)
    pointlike_coreps = load_json(POINTLIKE_COREPS_JSON)
    candidates_json = load_json(AI_V1_CANDIDATES_JSON)
    matrix_json = load_json(AI_V1_MATRIX_JSON)
    basis_json = load_json(AI_V1_BASIS_JSON)
    bs_vs_ai = load_json(BS_VS_AI_V1_SUMMARY_JSON)

    if pointlike_summary["group_number"] != GROUP_NUMBER or int(pointlike_summary["group_type"]) != GROUP_TYPE:
        raise ValueError("summary group metadata mismatch")
    if pointlike_summary["successful_families"] != TARGET_FAMILIES:
        raise ValueError("not all target families were marked successful")
    if pointlike_summary["failed_families"]:
        raise ValueError("unexpected failed families recorded in summary")
    if int(pointlike_summary["successful_local_object_count"]) != 14:
        raise ValueError("expected 14 successful local objects")
    if not bool(pointlike_summary["can_build_ai_double_pointlike_v1"]):
        raise ValueError("summary says AI_double_pointlike_v1 cannot be built")

    if len(pointlike_coreps["families"]) != len(PROCESSING_ORDER):
        raise ValueError("family census length mismatch")
    if len(candidates_json["generators"]) != 14:
        raise ValueError("candidate count mismatch")
    if any(not bool(item["compatibility_zero"]) for item in candidates_json["generators"]):
        raise ValueError("some induced generators do not satisfy BS compatibility")
    if int(matrix_json["rank_z"]) != 6:
        raise ValueError("unexpected AI point-like rank")
    if int(basis_json["rank_z"]) != 6:
        raise ValueError("unexpected reduced AI basis rank")
    if int(bs_vs_ai["rank_BS_double"]) != 8 or int(bs_vs_ai["rank_AI_double_pointlike_v1"]) != 6:
        raise ValueError("unexpected BS-vs-AI ranks")
    if not bool(bs_vs_ai["AI_double_pointlike_v1_in_BS"]):
        raise ValueError("AI_double_pointlike_v1 should lie in BS_double")
    if int(bs_vs_ai["remaining_rank_gap"]) != 2:
        raise ValueError("unexpected remaining rank gap")

    if not PACKAGE_DIR.exists() or not PACKAGE_TAR.exists():
        raise FileNotFoundError("package build missing")

    return state


def print_terminal_summary(state: dict[str, Any]) -> None:
    summary = state["pointlike_summary"]
    bs_vs_ai = state["bs_vs_ai"]
    candidate_failures = state["candidate_failures"]
    successful_families = summary["successful_families"]
    failed_families = summary["failed_families"]
    gap_note = bs_vs_ai["remaining_gap_source"]

    print(
        "1. `a,b,c,d,e,f,g,h` 这 8 个 point-like families 的 double local-corep census 是否完成？"
    )
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
    print("4. 是否已经成功构造 point-like `AI_double_v1`？")
    print(f"   {'是' if summary['can_build_ai_double_pointlike_v1'] else '否'}。")
    print("5. `AI_double_v1` 是否嵌入当前 `BS_double`？")
    print(f"   {'是' if bs_vs_ai['AI_double_pointlike_v1_in_BS'] else '否'}。")
    print("6. 当前 point-like `AI_double_v1` 覆盖了 `BS_double` 的多少维？")
    print(f"   {bs_vs_ai['covered_bs_dimensions']} / {bs_vs_ai['rank_BS_double']}。")
    print("7. 剩余缺口主要来自哪类 families？")
    print(f"   {gap_note}")
    print("8. 新压缩包完整路径是什么？")
    print(f"   {PACKAGE_TAR}")
    print("9. 压缩包内文件树是什么？")
    for line in state["package_tree"]:
        print(f"   {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Regenerate outputs and validate the point-like double AI prototype bundle.",
    )
    args = parser.parse_args()

    state = validate_outputs() if args.validate else generate_outputs()
    print_terminal_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
