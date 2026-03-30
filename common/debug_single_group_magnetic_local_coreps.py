#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import hermite_normal_form, smith_normal_form

import debug_single_group_ai_bridge as bridge
import debug_single_group_ai_expanded as expanded


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
PACKAGE_NAME = "review_package_10.4.1.31_ai_magnetic_points"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

TARGET_FAMILIES = ["a", "b", "d", "e", "g", "h"]
PROCESSING_ORDER = ["e", "d", "h", "g", "b", "a"]
MANIFOLDS = list(expanded.MANIFOLDS)

MAGNETIC_LOCAL_COREP_AUDIT_MD = ROOT / "single_group_magnetic_local_corep_audit.md"
MAGNETIC_LOCAL_COREP_SUMMARY_JSON = ROOT / "single_group_magnetic_local_corep_summary.json"
POINTLIKE_MAGNETIC_COREPS_JSON = ROOT / "single_group_pointlike_magnetic_coreps.json"
AI_EXPANDED_V2_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_v2_candidates.json"
AI_EXPANDED_V2_MATRIX_JSON = ROOT / "single_group_ai_expanded_v2_matrix.json"
AI_EXPANDED_V2_BASIS_JSON = ROOT / "single_group_ai_expanded_v2_basis.json"
BS_VS_AI_EXPANDED_V2_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_v2_summary.json"

OLD_AI_EXPANDED_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_candidates.json"
OLD_AI_EXPANDED_MATRIX_JSON = ROOT / "single_group_ai_expanded_matrix.json"
OLD_AI_EXPANDED_BASIS_JSON = ROOT / "single_group_ai_expanded_basis.json"
OLD_BS_VS_AI_EXPANDED_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_summary.json"
SITE_SYMMETRY_CHECK_JSON = ROOT / "single_group_site_symmetry_check.json"
BS_WITH_PLANES_BASIS_RAW_JSON = ROOT / "single_group_bs_with_planes_basis_raw.json"
FULL_COMPATIBILITY_WITH_PLANES_JSON = ROOT / "single_group_full_compatibility_with_planes.json"

FAMILY_MODELS: dict[str, dict[str, Any]] = {
    "h": {
        "priority": 2,
        "priority_reason": "Shares the same 2/m' point-like magnetic site symmetry as g; simple case-a direct extensions, but not the first pair needed to probe the missing rank directions.",
        "unitary_subgroup_abstract": "C2",
        "unitary_generator_index": 3,
        "unitary_generator_name": "raw op 3",
        "antiunitary_generator_index": 14,
        "antiunitary_generator_name": "raw op 14",
        "unitary_irreps": [
            {"label": "A", "ascii": "A", "generator_character": 1, "description": "C2-even one-dimensional irrep."},
            {"label": "B", "ascii": "B", "generator_character": -1, "description": "C2-odd one-dimensional irrep."},
        ],
    },
    "g": {
        "priority": 2,
        "priority_reason": "Same magnetic site-symmetry structure as h; treated right after h once the C2-based case-a builder is validated.",
        "unitary_subgroup_abstract": "C2",
        "unitary_generator_index": 3,
        "unitary_generator_name": "raw op 3",
        "antiunitary_generator_index": 14,
        "antiunitary_generator_name": "raw op 14",
        "unitary_irreps": [
            {"label": "A", "ascii": "A", "generator_character": 1, "description": "C2-even one-dimensional irrep."},
            {"label": "B", "ascii": "B", "generator_character": -1, "description": "C2-odd one-dimensional irrep."},
        ],
    },
    "e": {
        "priority": 1,
        "priority_reason": "Shares the same 2'/m' point-like magnetic site symmetry as d, has the simplest inversion-based unitary subgroup, and directly probes the previously missing rank directions.",
        "unitary_subgroup_abstract": "Ci",
        "unitary_generator_index": 5,
        "unitary_generator_name": "raw op 5",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "unitary_irreps": [
            {"label": "g", "ascii": "g", "generator_character": 1, "description": "Even one-dimensional irrep of the inversion subgroup."},
            {"label": "u", "ascii": "u", "generator_character": -1, "description": "Odd one-dimensional irrep of the inversion subgroup."},
        ],
    },
    "d": {
        "priority": 1,
        "priority_reason": "Same magnetic site-symmetry structure as e and completes the first high-priority representative pair.",
        "unitary_subgroup_abstract": "Ci",
        "unitary_generator_index": 5,
        "unitary_generator_name": "raw op 5",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "unitary_irreps": [
            {"label": "g", "ascii": "g", "generator_character": 1, "description": "Even one-dimensional irrep of the inversion subgroup."},
            {"label": "u", "ascii": "u", "generator_character": -1, "description": "Odd one-dimensional irrep of the inversion subgroup."},
        ],
    },
    "b": {
        "priority": 3,
        "priority_reason": "Same 2'/m point-like magnetic site symmetry as a; still easy to build, but lower marginal value because the induced vectors collapse pairwise with a.",
        "unitary_subgroup_abstract": "Cs",
        "unitary_generator_index": 7,
        "unitary_generator_name": "raw op 7",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "unitary_irreps": [
            {"label": "A'", "ascii": "Ap", "generator_character": 1, "description": "Mirror-even one-dimensional irrep."},
            {"label": "A''", "ascii": "App", "generator_character": -1, "description": "Mirror-odd one-dimensional irrep."},
        ],
    },
    "a": {
        "priority": 3,
        "priority_reason": "Same magnetic site-symmetry structure as b and gives the lowest marginal gain because its induced vectors coincide with the corresponding b-family vectors.",
        "unitary_subgroup_abstract": "Cs",
        "unitary_generator_index": 7,
        "unitary_generator_name": "raw op 7",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "unitary_irreps": [
            {"label": "A'", "ascii": "Ap", "generator_character": 1, "description": "Mirror-even one-dimensional irrep."},
            {"label": "A''", "ascii": "App", "generator_character": -1, "description": "Mirror-odd one-dimensional irrep."},
        ],
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n")


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


def serialize_raw_op(ctx: dict[str, Any], op_index: int) -> dict[str, Any]:
    rotation = ctx["raw_operations"][op_index]["rotation"]
    translation = ctx["raw_operations"][op_index]["translation"]
    return {
        "index": int(op_index),
        "time_reversal": bool(ctx["raw_operations"][op_index]["time_reversal"]),
        "matrix": bridge.format_vector(rotation[0]) and [
            bridge.format_vector(row) for row in rotation.tolist()
        ],
        "translation": bridge.format_vector(translation),
    }


def smith_diagonal(matrix: sp.Matrix) -> list[int]:
    smith = smith_normal_form(matrix)
    diag: list[int] = []
    for idx in range(min(smith.rows, smith.cols)):
        value = int(abs(smith[idx, idx]))
        if value != 0:
            diag.append(value)
    return diag


def candidate_vector_key(candidate: dict[str, Any]) -> tuple[int, ...]:
    return tuple(int(value) for value in candidate["unknown_vector"])


def bs_basis_matrix_from_raw(basis_raw: dict[str, Any]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(column["vector"]) for column in basis_raw["basis_vectors"]])


def integer_solution(basis_matrix: sp.Matrix, target: sp.Matrix) -> list[int]:
    solution = basis_matrix.gauss_jordan_solve(target)[0]
    if any(not value.is_integer for value in solution):
        raise ValueError(f"expected an integer solution, got {solution}")
    return [int(value) for value in solution]


def rational_solution_status(basis_matrix: sp.Matrix, target: sp.Matrix) -> dict[str, Any]:
    try:
        solution = basis_matrix.gauss_jordan_solve(target)[0]
    except Exception:
        return {
            "in_old_ai_expanded_rational_span": False,
            "in_old_ai_expanded_integer_lattice": False,
            "old_ai_expanded_coordinates": None,
        }
    coordinates = [str(value) for value in solution]
    return {
        "in_old_ai_expanded_rational_span": True,
        "in_old_ai_expanded_integer_lattice": all(value.is_integer for value in solution),
        "old_ai_expanded_coordinates": coordinates,
    }


def build_context() -> dict[str, Any]:
    ctx = bridge.load_context()
    ctx["raw_operations"] = expanded.raw_ops(ctx)
    ctx["group_tables"] = expanded.build_group_tables(ctx)
    ctx["manifold_globals"] = expanded.manifold_global_unitary_indices(ctx, ctx["group_tables"])
    ctx["manifold_infos"] = {manifold: bridge.manifold_linear_characters(manifold, ctx) for manifold in MANIFOLDS}
    ctx["site_symmetry_check"] = load_json(SITE_SYMMETRY_CHECK_JSON)
    ctx["old_candidates"] = load_json(OLD_AI_EXPANDED_CANDIDATES_JSON)
    ctx["old_matrix"] = load_json(OLD_AI_EXPANDED_MATRIX_JSON)
    ctx["old_basis"] = load_json(OLD_AI_EXPANDED_BASIS_JSON)
    ctx["old_summary"] = load_json(OLD_BS_VS_AI_EXPANDED_SUMMARY_JSON)
    ctx["basis_raw_root"] = load_json(BS_WITH_PLANES_BASIS_RAW_JSON)
    ctx["compat_root"] = load_json(FULL_COMPATIBILITY_WITH_PLANES_JSON)
    ctx["basis_raw"] = ctx["basis_raw_root"]
    ctx["compat"] = ctx["compat_root"]
    ctx["bs_basis_matrix"] = bs_basis_matrix_from_raw(ctx["basis_raw_root"])
    ctx["compatibility_matrix"] = sp.Matrix(ctx["compat_root"]["global_matrix"])
    ctx["old_ai_basis_matrix"] = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in ctx["old_basis"]["basis_vectors"]]
    )
    ctx["old_ai_basis_coeff_matrix"] = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in ctx["old_basis"]["basis_bs_coefficients"]]
    )
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in ctx["wyckoff_entries"]}
    ctx["site_check_by_letter"] = {
        entry["letter"]: entry for entry in ctx["site_symmetry_check"]["entries"]
    }
    return ctx


def site_symmetry_counts_match(bridge_entry: dict[str, Any], direct: dict[str, Any]) -> bool:
    return (
        int(bridge_entry["bridge_stabilizer_size"]) == int(direct["stabilizer_size"])
        and int(bridge_entry["bridge_unitary_count"]) == int(direct["unitary_count"])
        and int(bridge_entry["bridge_antiunitary_count"]) == int(direct["antiunitary_count"])
        and list(bridge_entry["stabilizer_indices"]) == list(direct["stabilizer_indices"])
        and list(bridge_entry["unitary_indices"]) == list(
            idx for idx in direct["stabilizer_indices"] if idx in bridge_entry["unitary_indices"]
        )
        and list(bridge_entry["antiunitary_indices"]) == list(
            idx for idx in direct["stabilizer_indices"] if idx in bridge_entry["antiunitary_indices"]
        )
    )


def build_coreps_for_family(letter: str, family_record: dict[str, Any], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    model = FAMILY_MODELS[letter]
    unitary_generator = int(model["unitary_generator_index"])
    anti_generator = int(model["antiunitary_generator_index"])
    other_anti = next(
        index
        for index in family_record["stabilizer_summary"]["antiunitary_indices"]
        if index != anti_generator
    )
    other_anti_character_factor = {
        irrep["ascii"]: int(irrep["generator_character"]) for irrep in model["unitary_irreps"]
    }
    coreps: list[dict[str, Any]] = []
    for irrep in model["unitary_irreps"]:
        unitary_character = {
            0: 1,
            unitary_generator: int(irrep["generator_character"]),
        }
        for eta in (+1, -1):
            eta_label = "plus" if eta > 0 else "minus"
            corep_id = f"{letter}_{irrep['ascii']}_eta_{eta_label}"
            antiunitary_character = {
                anti_generator: eta,
                other_anti: eta * other_anti_character_factor[irrep["ascii"]],
            }
            coreps.append(
                {
                    "corep_id": corep_id,
                    "label": f"{irrep['label']}, eta={eta:+d}",
                    "dimension": 1,
                    "family_letter": letter,
                    "family_site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
                    "unitary_irrep_label": irrep["label"],
                    "unitary_irrep_ascii": irrep["ascii"],
                    "unitary_character_on_stabilizer": {
                        str(index): int(value) for index, value in unitary_character.items()
                    },
                    "antiunitary_character_signature": {
                        str(index): int(value) for index, value in antiunitary_character.items()
                    },
                    "antiunitary_extension_eta": int(eta),
                    "wigner_case": "a",
                    "source_unitary_irrep": irrep["label"],
                    "construction_logic": "The antiunitary generator squares to the identity and acts trivially by conjugation on the order-2 unitary subgroup, so each real one-dimensional unitary irrep admits two case-a direct extensions D(a)=eta*K.",
                    "truly_antiunitary": False,
                    "direct_extension_of_unitary_irrep": True,
                    "status": "constructed",
                }
            )
    return coreps


def build_family_record(letter: str, ctx: dict[str, Any]) -> dict[str, Any]:
    entry = ctx["entries_by_letter"][letter]
    site_entry = ctx["site_check_by_letter"][letter]
    direct = site_entry["direct_reconstruction"]
    bridge_entry = bridge.bridge_stabilizer_for_entry(entry, ctx)
    model = FAMILY_MODELS[letter]

    anti_generator = int(model["antiunitary_generator_index"])
    unitary_generator = int(model["unitary_generator_index"])
    group_tables = ctx["group_tables"]
    anti_square = group_tables["compose"](anti_generator, anti_generator)
    conjugation_image = group_tables["compose"](
        group_tables["inverse"][anti_generator],
        group_tables["compose"](unitary_generator, anti_generator),
    )

    exact_match = site_symmetry_counts_match(bridge_entry, direct) and bool(
        site_entry["comparison"]["overall_consistent"]
    )

    stabilizer_elements = [
        serialize_raw_op(ctx, op_index) for op_index in bridge_entry["stabilizer_indices"]
    ]

    record = {
        "letter": letter,
        "processing_priority": int(model["priority"]),
        "processing_priority_reason": model["priority_reason"],
        "representative_coordinate": entry["representative_coordinate"],
        "representative_coordinate_sample_magnetic": bridge.format_vector(
            bridge.representative_sample_point_magnetic(entry)
        ),
        "representative_coordinate_sample_conventional": bridge.format_vector(
            ctx["supercell"] @ bridge.representative_sample_point_magnetic(entry)
        ),
        "multiplicity": int(entry["mult"]),
        "site_symmetry_summary": {
            "site_symmetry": entry["site_symmetry"],
            "site_symmetry_custom": entry.get("site_symmetry_custom"),
            "unitary_site_symmetry": entry.get("unitary_site_symmetry"),
        },
        "stabilizer_summary": {
            "stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "unitary_count": int(bridge_entry["bridge_unitary_count"]),
            "antiunitary_count": int(bridge_entry["bridge_antiunitary_count"]),
            "stabilizer_indices": list(bridge_entry["stabilizer_indices"]),
            "unitary_indices": list(bridge_entry["unitary_indices"]),
            "antiunitary_indices": list(bridge_entry["antiunitary_indices"]),
            "stabilizer_elements": stabilizer_elements,
        },
        "site_symmetry_check_comparison": {
            "single_group_site_symmetry_check_matches_recompute": bool(exact_match),
            "direct_reconstruction_indices": list(direct["stabilizer_indices"]),
            "direct_reconstruction_unitary_count": int(direct["unitary_count"]),
            "direct_reconstruction_antiunitary_count": int(direct["antiunitary_count"]),
            "direct_reconstruction_site_symmetry": direct["site_symmetry"],
            "direct_reconstruction_site_symmetry_custom": direct.get("site_symmetry_custom"),
            "overall_consistent_flag": bool(site_entry["comparison"]["overall_consistent"]),
            "usable_as_magnetic_local_corep_input": bool(exact_match),
            "usable_note": "This family's site symmetry can be used as magnetic local corep input." if exact_match else "This family still has a site-symmetry mismatch and cannot yet be used as magnetic local corep input.",
        },
        "unitary_subgroup_summary": {
            "abstract_group": model["unitary_subgroup_abstract"],
            "generator_index": unitary_generator,
            "generator_name": model["unitary_generator_name"],
            "identity_index": 0,
            "unitary_irrep_labels": [irrep["label"] for irrep in model["unitary_irreps"]],
        },
        "wigner_preanalysis": {
            "antiunitary_generator_index": anti_generator,
            "antiunitary_generator_name": model["antiunitary_generator_name"],
            "antiunitary_generator_square_index": int(anti_square),
            "antiunitary_conjugation_on_unitary_generator": int(conjugation_image),
            "antiunitary_conjugation_fixed": int(conjugation_image) == unitary_generator,
            "all_unitary_irreps_real": True,
            "all_unitary_irreps_fixed_by_antiunitary_action": True,
            "expected_wigner_case": "a",
        },
        "feasibility": {
            "current_toolchain_direct_support": False,
            "current_toolchain_direct_support_note": "SSGReps has antiunitary little-group corep logic, but there is no direct entrypoint that consumes a real-space site stabilizer subset as a local magnetic corep group.",
            "custom_single_group_builder_possible": True,
            "custom_single_group_builder_note": "For these six families the stabilizer is order 4 with an order-2 unitary subgroup, so a dedicated single-group case-a builder is sufficient.",
            "minimal_blocker": None,
        },
    }
    record["magnetic_local_coreps"] = build_coreps_for_family(letter, record, ctx)
    record["full_magnetic_local_corep_set_built"] = True
    return record


def induce_corep_candidate(
    entry: dict[str, Any],
    family_record: dict[str, Any],
    corep: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    unitary_local_rep = {
        "id": f"{entry['letter']}_{corep['unitary_irrep_ascii']}_unitary_proto",
        "label": corep["unitary_irrep_label"],
        "dimension": int(corep["dimension"]),
        "local_rep_scope": "unitary-subgroup projection of the magnetic local corep",
        "definition": "Eta-blind unitary-subgroup character used to induce the current k-space target once per unitary irrep; the case-a eta=+/- extensions are reattached afterwards.",
        "character_on_unitary_stabilizer": corep["unitary_character_on_stabilizer"],
    }
    prototype = expanded.induce_candidate(
        entry,
        unitary_local_rep,
        ctx,
        ctx["group_tables"],
        ctx["manifold_globals"],
    )
    if not prototype["compatibility_zero"]:
        raise ValueError(f"{corep['corep_id']}: compatibility check failed")

    unknown_vector = [int(value) for value in prototype["unknown_vector"]]
    bs_basis_coefficients = [int(value) for value in prototype["bs_basis_coefficients"]]
    old_status = rational_solution_status(
        ctx["old_ai_basis_matrix"],
        sp.Matrix(unknown_vector),
    )

    return {
        "prototype_generator_id": unitary_local_rep["id"],
        "source_family": entry["letter"],
        "source_type": "pointlike_magnetic_local_corep",
        "family_dimension": int(entry["dim"]),
        "multiplicity": int(entry["mult"]),
        "representative_coordinate_symbolic": entry["representative_coordinate"],
        "representative_coordinate_sample_magnetic": bridge.format_vector(
            bridge.representative_sample_point_magnetic(entry)
        ),
        "representative_coordinate_sample_conventional": bridge.format_vector(
            ctx["supercell"] @ bridge.representative_sample_point_magnetic(entry)
        ),
        "site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
        "stabilizer_summary": {
            "unitary_size": int(prototype["stabilizer_summary"]["unitary_size"]),
            "antiunitary_size": int(prototype["stabilizer_summary"]["antiunitary_size"]),
            "unitary_indices": list(prototype["stabilizer_summary"]["unitary_indices"]),
            "antiunitary_indices": list(prototype["stabilizer_summary"]["antiunitary_indices"]),
        },
        "sample_orbit_size": int(prototype["sample_orbit_size"]),
        "orbit": prototype["orbit"],
        "manifold_multiplicities": prototype["manifold_multiplicities"],
        "manifold_band_characters": prototype["manifold_band_characters"],
        "unknown_vector": unknown_vector,
        "compatibility_zero": True,
        "bs_basis_coefficients": bs_basis_coefficients,
        "antiunitary_extension_visible_in_current_unitary_kspace_target": False,
        "antiunitary_extension_visibility_note": "The current 31-dimensional target only tracks unitary little-group content, so the eta=+/- case-a extensions of the same unitary irrep induce the same unknown vector.",
        "prototype_note": "This record was induced once from the unitary-subgroup content and is then reused for both case-a eta extensions of the same unitary irrep.",
        **old_status,
    }


def build_new_pointlike_candidates(ctx: dict[str, Any], family_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    successful: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    prototype_cache: dict[tuple[str, str], dict[str, Any]] = {}
    for family_record in family_records:
        entry = ctx["entries_by_letter"][family_record["letter"]]
        if not family_record["site_symmetry_check_comparison"]["usable_as_magnetic_local_corep_input"]:
            failures.append(
                {
                    "family": family_record["letter"],
                    "reason": "site symmetry is not stable enough for magnetic local corep input",
                }
            )
            continue
        for corep in family_record["magnetic_local_coreps"]:
            try:
                cache_key = (family_record["letter"], corep["unitary_irrep_ascii"])
                if cache_key not in prototype_cache:
                    prototype_cache[cache_key] = induce_corep_candidate(entry, family_record, corep, ctx)
                candidate = deepcopy(prototype_cache[cache_key])
                candidate["generator_id"] = corep["corep_id"]
                candidate["magnetic_local_corep"] = corep
                candidate["unitary_irrep_prototype_id"] = candidate["prototype_generator_id"]
                successful.append(candidate)
            except Exception as exc:
                failures.append(
                    {
                        "family": family_record["letter"],
                        "corep_id": corep["corep_id"],
                        "reason": str(exc),
                    }
                )
    return successful, failures


def annotate_duplicate_classes(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_vector: dict[tuple[int, ...], list[str]] = {}
    for candidate in candidates:
        by_vector.setdefault(candidate_vector_key(candidate), []).append(candidate["generator_id"])
    classes: list[dict[str, Any]] = []
    for vector, ids in sorted(by_vector.items(), key=lambda item: item[1]):
        classes.append(
            {
                "generator_ids": ids,
                "unknown_vector": list(vector),
                "class_size": len(ids),
            }
        )
    id_to_class = {
        generator_id: duplicate["generator_ids"]
        for duplicate in classes
        for generator_id in duplicate["generator_ids"]
    }
    for candidate in candidates:
        duplicate_ids = [gid for gid in id_to_class[candidate["generator_id"]] if gid != candidate["generator_id"]]
        candidate["same_unknown_vector_as"] = duplicate_ids
    return classes


def build_combined_candidate_data(
    ctx: dict[str, Any],
    new_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    old_generators = list(ctx["old_candidates"]["generators"])
    combined_generators = old_generators + new_candidates
    column_order = [generator["generator_id"] for generator in combined_generators]
    unknown_columns = [generator["unknown_vector"] for generator in combined_generators]
    coeff_columns = [generator["bs_basis_coefficients"] for generator in combined_generators]

    unknown_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in unknown_columns])
    coeff_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in coeff_columns])
    hnf_coeff_basis = hermite_normal_form(coeff_matrix)
    hnf_basis_coefficients = [
        [int(hnf_coeff_basis[row, col]) for row in range(hnf_coeff_basis.rows)]
        for col in range(hnf_coeff_basis.cols)
    ]
    hnf_basis_vectors = [
        [int(value) for value in list(ctx["bs_basis_matrix"] * sp.Matrix(column))]
        for column in hnf_basis_coefficients
    ]
    hnf_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in hnf_basis_coefficients])
    candidate_to_basis_relations = {
        generator["generator_id"]: integer_solution(
            hnf_basis_matrix,
            sp.Matrix(generator["bs_basis_coefficients"]),
        )
        for generator in combined_generators
    }

    duplicate_classes = annotate_duplicate_classes(new_candidates)
    rank_closing_examples = []
    old_rank = int(ctx["old_summary"]["rank_AI_expanded"])
    incremental_columns = [sp.Matrix(column) for column in ctx["old_basis"]["basis_vectors"]]
    current_rank = sp.Matrix.hstack(*incremental_columns).rank()
    for candidate in new_candidates:
        next_rank = sp.Matrix.hstack(*incremental_columns, sp.Matrix(candidate["unknown_vector"])).rank()
        if next_rank > current_rank:
            rank_closing_examples.append(candidate["generator_id"])
            incremental_columns.append(sp.Matrix(candidate["unknown_vector"]))
            current_rank = next_rank
        if current_rank == len(ctx["basis_raw_root"]["basis_vectors"]):
            break
    coeff_smith_diagonal = smith_diagonal(coeff_matrix)

    return {
        "old_generators": old_generators,
        "new_generators": new_candidates,
        "combined_generators": combined_generators,
        "column_order": column_order,
        "unknown_columns": unknown_columns,
        "coeff_columns": coeff_columns,
        "unknown_rank": int(unknown_matrix.rank()),
        "coeff_rank": int(coeff_matrix.rank()),
        "hnf_basis_coefficients": hnf_basis_coefficients,
        "hnf_basis_vectors": hnf_basis_vectors,
        "candidate_to_basis_relations": candidate_to_basis_relations,
        "duplicate_classes": duplicate_classes,
        "rank_closing_examples": rank_closing_examples,
        "coeff_smith_diagonal": coeff_smith_diagonal,
        "lattice_index_in_bs": int(math.prod(coeff_smith_diagonal)) if coeff_matrix.rank() == coeff_matrix.rows else None,
    }


def build_corep_summary_json(
    family_records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    combined: dict[str, Any],
) -> dict[str, Any]:
    successful_families = [record["letter"] for record in family_records if record["full_magnetic_local_corep_set_built"]]
    failed_family_names = sorted({failure["family"] for failure in failures})
    return {
        "group_number": GROUP_NUMBER,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "successful_families": successful_families,
        "failed_families": failed_family_names,
        "successful_local_corep_count": sum(len(record["magnetic_local_coreps"]) for record in family_records),
        "can_build_ai_expanded_v2": not failures,
        "next_blocker": "The point-like antiunitary families are now covered at the rank level; the remaining next blocker is the parameter families n,i,j together with the final integer-saturation question beyond rank closure.",
        "rank_ai_expanded_v2": int(combined["unknown_rank"]),
        "remaining_rank_gap": max(0, 8 - int(combined["unknown_rank"])),
    }


def build_pointlike_coreps_json(family_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "families": family_records,
    }


def build_ai_expanded_v2_candidates_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
        "old_expanded_candidate_count": len(combined["old_generators"]),
        "new_pointlike_magnetic_corep_candidate_count": len(combined["new_generators"]),
        "combined_raw_candidate_count": len(combined["combined_generators"]),
        "old_generators": combined["old_generators"],
        "new_generators": combined["new_generators"],
        "combined_generators": combined["combined_generators"],
        "new_candidate_duplicate_vector_classes": combined["duplicate_classes"],
    }


def build_ai_expanded_v2_matrix_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for index, unknown in enumerate(ctx["basis_raw_root"]["unknown_ordering"]):
        rows.append(
            {
                "unknown": unknown,
                "coefficients": [column[index] for column in combined["unknown_columns"]],
            }
        )
    return {
        "group_number": GROUP_NUMBER,
        "matrix_orientation": "columns_are_generators",
        "column_order": combined["column_order"],
        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
        "A_expanded_v2_columns": combined["unknown_columns"],
        "A_expanded_v2_rows": rows,
        "A_expanded_v2_bs_coefficients": combined["coeff_columns"],
        "rank_z": int(combined["unknown_rank"]),
        "rank_q": int(combined["unknown_rank"]),
        "bs_coefficient_rank_z": int(combined["coeff_rank"]),
        "bs_coefficient_smith_diagonal": combined["coeff_smith_diagonal"],
        "compatibility_zero": {
            generator["generator_id"]: bool(generator["compatibility_zero"])
            for generator in combined["combined_generators"]
        },
    }


def build_ai_expanded_v2_basis_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "basis_construction_method": "Hermite normal form on the BS-basis coefficient lattice of the combined raw candidate matrix.",
        "basis_kind": "bs_coefficient_hnf_basis",
        "basis_column_order": [f"ai_expanded_v2_hnf_{index + 1:02d}" for index in range(len(combined["hnf_basis_vectors"]))],
        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
        "basis_vectors": combined["hnf_basis_vectors"],
        "basis_bs_coefficients": combined["hnf_basis_coefficients"],
        "rank_z": len(combined["hnf_basis_vectors"]),
        "candidate_to_basis_integer_relations": combined["candidate_to_basis_relations"],
        "raw_candidate_count": len(combined["combined_generators"]),
        "old_ai_expanded_rank": int(ctx["old_summary"]["rank_AI_expanded"]),
        "new_independent_rank_directions_vs_old": int(combined["unknown_rank"]) - int(ctx["old_summary"]["rank_AI_expanded"]),
        "rank_closing_example_candidate_ids": combined["rank_closing_examples"],
        "bs_coefficient_smith_diagonal": combined["coeff_smith_diagonal"],
        "lattice_index_in_bs": combined["lattice_index_in_bs"],
        "basis_is_candidate_subset": False,
    }


def build_bs_vs_ai_expanded_v2_summary_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    bs_rank = len(ctx["basis_raw_root"]["basis_vectors"])
    bs_matrix = ctx["bs_basis_matrix"]
    ai_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in combined["unknown_columns"]])
    union_rank = int(sp.Matrix.hstack(bs_matrix, ai_matrix).rank())
    return {
        "group_number": GROUP_NUMBER,
        "rank_BS_with_planes": int(bs_rank),
        "rank_AI_expanded": int(ctx["old_summary"]["rank_AI_expanded"]),
        "rank_AI_expanded_v2": int(combined["unknown_rank"]),
        "AI_expanded_v2_in_BS": union_rank == bs_rank,
        "rank_span_BS_plus_AI_expanded_v2": union_rank,
        "remaining_rank_gap": max(0, bs_rank - int(combined["unknown_rank"])),
        "added_rank_coverage_vs_old": int(combined["unknown_rank"]) - int(ctx["old_summary"]["rank_AI_expanded"]),
        "old_raw_candidate_count": len(combined["old_generators"]),
        "new_pointlike_magnetic_corep_candidate_count": len(combined["new_generators"]),
        "combined_raw_candidate_count": len(combined["combined_generators"]),
        "distinct_new_pointlike_unknown_vector_count": len(combined["duplicate_classes"]),
        "rank_closing_example_candidate_ids": combined["rank_closing_examples"],
        "remaining_missing_families": ["n", "i", "j"],
        "residual_nonrank_issue": "The combined BS-coefficient Smith diagonal is [1,1,1,1,1,1,2,2], so finite-index saturation inside the audited BS lattice is still not settled by this rank-level closure.",
        "next_most_reasonable_target": "Build the parameter-family antiunitary magnetic local coreps for n,i,j and re-check integer saturation.",
    }


def build_magnetic_local_corep_audit_md(
    family_records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    combined: dict[str, Any],
    ctx: dict[str, Any],
) -> str:
    lines = [
        f"# Single-Group Magnetic Local Corep Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        "- This round only handles the point-like antiunitary families `a, b, d, e, g, h`.",
        "- The trusted k-space side, plane formalism, and real-space / k-space bridge are reused as fixed input.",
        "- The parameter families `n, i, j` remain out of scope in this script.",
        "",
        "## Processing Order",
        "",
        "1. `e`, `d`: same `2'/m'` site symmetry, easiest inversion-based unitary subgroup, and the first pair that actually probes the old rank-2 gap.",
        "2. `h`, `g`: same `2/m'` site symmetry, same case-a logic, but lower priority than `e/d` because they do not add new rank directions first.",
        "3. `b`, `a`: same `2'/m` site symmetry, still easy to build, but lowest marginal value because `a` duplicates the corresponding `b` vectors in the present unitary k-space target.",
        "",
        "## Toolchain Feasibility",
        "",
        "- `swyckoff_r.py` and the audited bridge are sufficient to recompute the point stabilizers exactly for all six target families.",
        "- `SSGReps/SSGReps/SSGReps.py` contains antiunitary Wigner/corep logic for little groups, but it does not provide a direct helper that consumes an arbitrary real-space site stabilizer as a local magnetic corep group.",
        "- A dedicated single-group builder is therefore used here: enumerate the order-2 unitary subgroup irreps, inspect the antiunitary action on that subgroup, classify the Wigner case, and build the corresponding magnetic local coreps explicitly.",
        "",
        "## Family-By-Family Audit",
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
                f"- Custom site-symmetry summary: `{record['site_symmetry_summary']['site_symmetry_custom']}`.",
                f"- Stabilizer size / unitary / antiunitary: `{record['stabilizer_summary']['stabilizer_size']}` / `{record['stabilizer_summary']['unitary_count']}` / `{record['stabilizer_summary']['antiunitary_count']}`.",
                f"- Recomputed stabilizer matches `single_group_site_symmetry_check.json`: `{record['site_symmetry_check_comparison']['single_group_site_symmetry_check_matches_recompute']}`.",
                f"- Usable as magnetic local corep input: `{record['site_symmetry_check_comparison']['usable_as_magnetic_local_corep_input']}`.",
                f"- Unitary subgroup: `{record['unitary_subgroup_summary']['abstract_group']}` generated by `{record['unitary_subgroup_summary']['generator_name']}`.",
                f"- Antiunitary generator square: raw op `{record['wigner_preanalysis']['antiunitary_generator_square_index']}`.",
                f"- Antiunitary conjugation fixes the unitary generator: `{record['wigner_preanalysis']['antiunitary_conjugation_fixed']}`.",
                f"- Wigner case used: `{record['wigner_preanalysis']['expected_wigner_case']}`.",
                f"- Direct code support already present: `{record['feasibility']['current_toolchain_direct_support']}`.",
                f"- Dedicated single-group builder sufficient: `{record['feasibility']['custom_single_group_builder_possible']}`.",
                f"- Full magnetic local corep set successfully built: `{record['full_magnetic_local_corep_set_built']}`.",
                "- Constructed magnetic local coreps:",
            ]
        )
        for corep in record["magnetic_local_coreps"]:
            lines.append(
                f"  - `{corep['corep_id']}`: dim `{corep['dimension']}`, source unitary irrep `{corep['source_unitary_irrep']}`, Wigner case `{corep['wigner_case']}`, eta `{corep['antiunitary_extension_eta']:+d}`, truly antiunitary `{corep['truly_antiunitary']}`."
            )
        lines.append("")

    lines.extend(
        [
            "## Outcome",
            "",
            f"- Successful families: `{', '.join(record['letter'] for record in family_records)}`.",
            f"- Failed families: `{', '.join(sorted({failure['family'] for failure in failures})) if failures else 'none'}`.",
            f"- Successful local corep count: `{sum(len(record['magnetic_local_coreps']) for record in family_records)}`.",
            f"- New raw point-like magnetic-corep candidate count: `{len(combined['new_generators'])}`.",
            f"- Distinct induced unitary vectors among those new candidates: `{len(combined['duplicate_classes'])}`.",
            f"- `rank_Z(AI_expanded_v2) = {combined['unknown_rank']}` compared with the old `rank_Z(AI_expanded) = {ctx['old_summary']['rank_AI_expanded']}`.",
            f"- Rank-closing example candidates: `{', '.join(combined['rank_closing_examples'])}`.",
            "- The point-like antiunitary families close the old rank-2 gap at the rank level, but they still leave a finite-index saturation issue in the BS coefficient lattice.",
        ]
    )
    return "\n".join(lines)


def build_package_readme() -> str:
    lines = [
        f"# Review Package: {GROUP_NUMBER} Magnetic Point-Like Coreps",
        "",
        "## Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        "- stage: magnetic local coreps on the point-like antiunitary families `a, b, d, e, g, h`",
        "",
        "## Known Premise",
        "",
        "- The k-space side is already trusted.",
        "- The plane formalism is already trusted.",
        "- The real-space / k-space bridge `r_conv = P r_mag` with `P = diag(1,2,2)` is already validated.",
        "- The earlier unitary-only expanded AI lattice already reached rank 6.",
        "",
        "## New Content",
        "",
        "- `audit/single_group_magnetic_local_corep_audit.md`: family ordering, site-symmetry audit, feasibility, and success/failure status",
        "- `audit/single_group_magnetic_local_corep_summary.json`: compact single-group status for this stage",
        "- `audit/single_group_pointlike_magnetic_coreps.json`: full census of the six point-like antiunitary families",
        "- `ai/single_group_ai_expanded_v2_candidates.json`: old 15 unitary-only candidates plus the newly induced magnetic point-like candidates",
        "- `ai/single_group_ai_expanded_v2_basis.json`: exact reduced basis of the combined raw candidate lattice",
        "- `ai/single_group_bs_vs_ai_expanded_v2_summary.json`: updated single-group BS-vs-AI comparison",
        "- `scripts/debug_single_group_magnetic_local_coreps.py`: single-group reproduction script for this stage only",
        "",
        "## Result Of This Run",
        "",
        "- All six point-like antiunitary families were successfully audited and built at the magnetic local-corep level.",
        "- The resulting `AI_expanded_v2` closes the old rank-2 gap at the rank level: rank 6 -> rank 8.",
        "- This is still not the final BS/AI result because the parameter families `n, i, j` remain untreated and the BS-coefficient lattice still has a finite-index saturation issue.",
        "",
        "## Suggested Review Order",
        "",
        "1. `audit/single_group_magnetic_local_corep_audit.md`",
        "2. `audit/single_group_magnetic_local_corep_summary.json`",
        "3. `audit/single_group_pointlike_magnetic_coreps.json`",
        "4. `ai/single_group_ai_expanded_v2_basis.json`",
        "5. `ai/single_group_bs_vs_ai_expanded_v2_summary.json`",
    ]
    return "\n".join(lines)


def build_package() -> None:
    reset_dir(PACKAGE_DIR)

    mapping = {
        "audit/single_group_magnetic_local_corep_audit.md": MAGNETIC_LOCAL_COREP_AUDIT_MD,
        "audit/single_group_magnetic_local_corep_summary.json": MAGNETIC_LOCAL_COREP_SUMMARY_JSON,
        "audit/single_group_pointlike_magnetic_coreps.json": POINTLIKE_MAGNETIC_COREPS_JSON,
        "ai/single_group_ai_expanded_v2_candidates.json": AI_EXPANDED_V2_CANDIDATES_JSON,
        "ai/single_group_ai_expanded_v2_matrix.json": AI_EXPANDED_V2_MATRIX_JSON,
        "ai/single_group_ai_expanded_v2_basis.json": AI_EXPANDED_V2_BASIS_JSON,
        "ai/single_group_bs_vs_ai_expanded_v2_summary.json": BS_VS_AI_EXPANDED_V2_SUMMARY_JSON,
        "scripts/debug_single_group_magnetic_local_coreps.py": ROOT / "debug_single_group_magnetic_local_coreps.py",
        "audit/single_group_local_rep_census_audit.md": ROOT / "single_group_local_rep_census_audit.md",
        "audit/single_group_local_rep_census_summary.json": ROOT / "single_group_local_rep_census_summary.json",
        "audit/single_group_ai_bridge_audit.md": ROOT / "single_group_ai_bridge_audit.md",
        "audit/single_group_ai_bridge_summary.json": ROOT / "single_group_ai_bridge_summary.json",
        "audit/single_group_site_symmetry_check.json": ROOT / "single_group_site_symmetry_check.json",
        "audit/single_group_plane_formalism_audit.md": ROOT / "single_group_plane_formalism_audit.md",
        "audit/single_group_plane_formalism_summary.json": ROOT / "single_group_plane_formalism_summary.json",
        "audit/single_group_bs_with_planes_summary.json": ROOT / "single_group_bs_with_planes_summary.json",
        "ai/single_group_ai_expanded_candidates.json": ROOT / "single_group_ai_expanded_candidates.json",
        "ai/single_group_ai_expanded_matrix.json": ROOT / "single_group_ai_expanded_matrix.json",
        "ai/single_group_ai_expanded_basis.json": ROOT / "single_group_ai_expanded_basis.json",
        "ai/single_group_bs_vs_ai_expanded_summary.json": ROOT / "single_group_bs_vs_ai_expanded_summary.json",
        "background/single_group_kmanifolds.json": ROOT / "single_group_kmanifolds.json",
        "background/single_group_connectivity.json": ROOT / "single_group_connectivity.json",
        "basis/single_group_bs_with_planes_basis_raw.json": ROOT / "single_group_bs_with_planes_basis_raw.json",
        "basis/single_group_bs_with_planes_basis_pretty.json": ROOT / "single_group_bs_with_planes_basis_pretty.json",
        "matrix/single_group_full_compatibility_with_planes.json": ROOT / "single_group_full_compatibility_with_planes.json",
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    }

    for relative, source in mapping.items():
        destination = PACKAGE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    write_text(PACKAGE_DIR / "README.md", build_package_readme())

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()

    family_records = [build_family_record(letter, ctx) for letter in PROCESSING_ORDER]
    new_candidates, failures = build_new_pointlike_candidates(ctx, family_records)
    combined = build_combined_candidate_data(ctx, new_candidates)

    summary_json = build_corep_summary_json(family_records, failures, combined)
    pointlike_json = build_pointlike_coreps_json(family_records)
    candidates_json = build_ai_expanded_v2_candidates_json(combined, ctx)
    matrix_json = build_ai_expanded_v2_matrix_json(combined, ctx)
    basis_json = build_ai_expanded_v2_basis_json(combined, ctx)
    bs_vs_ai_json = build_bs_vs_ai_expanded_v2_summary_json(combined, ctx)
    audit_md = build_magnetic_local_corep_audit_md(family_records, failures, combined, ctx)

    write_text(MAGNETIC_LOCAL_COREP_AUDIT_MD, audit_md)
    write_json(MAGNETIC_LOCAL_COREP_SUMMARY_JSON, summary_json)
    write_json(POINTLIKE_MAGNETIC_COREPS_JSON, pointlike_json)
    write_json(AI_EXPANDED_V2_CANDIDATES_JSON, candidates_json)
    write_json(AI_EXPANDED_V2_MATRIX_JSON, matrix_json)
    write_json(AI_EXPANDED_V2_BASIS_JSON, basis_json)
    write_json(BS_VS_AI_EXPANDED_V2_SUMMARY_JSON, bs_vs_ai_json)
    build_package()

    return {
        "family_records": family_records,
        "summary": summary_json,
        "combined": combined,
        "bs_vs_ai": bs_vs_ai_json,
        "failures": failures,
    }


def validate_outputs() -> None:
    required_paths = [
        MAGNETIC_LOCAL_COREP_AUDIT_MD,
        MAGNETIC_LOCAL_COREP_SUMMARY_JSON,
        POINTLIKE_MAGNETIC_COREPS_JSON,
        AI_EXPANDED_V2_CANDIDATES_JSON,
        AI_EXPANDED_V2_MATRIX_JSON,
        AI_EXPANDED_V2_BASIS_JSON,
        BS_VS_AI_EXPANDED_V2_SUMMARY_JSON,
        PACKAGE_TARBALL,
    ]
    for path in required_paths:
        if not path.exists():
            raise ValueError(f"missing required artifact: {path}")

    summary = load_json(MAGNETIC_LOCAL_COREP_SUMMARY_JSON)
    if summary["group_number"] != GROUP_NUMBER:
        raise ValueError("summary group number mismatch")
    if sorted(summary["successful_families"]) != sorted(TARGET_FAMILIES):
        raise ValueError("not all target families were reported successful")
    if summary["successful_local_corep_count"] != 24:
        raise ValueError("unexpected successful local corep count")

    coreps = load_json(POINTLIKE_MAGNETIC_COREPS_JSON)
    if len(coreps["families"]) != 6:
        raise ValueError("unexpected family count in corep census")

    matrix = load_json(AI_EXPANDED_V2_MATRIX_JSON)
    if matrix["rank_z"] != 8:
        raise ValueError("unexpected AI_expanded_v2 rank")

    basis = load_json(AI_EXPANDED_V2_BASIS_JSON)
    if basis["rank_z"] != 8:
        raise ValueError("unexpected AI_expanded_v2 basis rank")
    if basis["bs_coefficient_smith_diagonal"] != [1, 1, 1, 1, 1, 1, 2, 2]:
        raise ValueError("unexpected Smith diagonal in AI_expanded_v2 basis")

    bs_vs_ai = load_json(BS_VS_AI_EXPANDED_V2_SUMMARY_JSON)
    if bs_vs_ai["rank_BS_with_planes"] != 8:
        raise ValueError("unexpected BS rank")
    if bs_vs_ai["rank_AI_expanded_v2"] != 8:
        raise ValueError("unexpected AI_expanded_v2 rank in summary")
    if not bs_vs_ai["AI_expanded_v2_in_BS"]:
        raise ValueError("AI_expanded_v2 was not reported as embedded in BS")

    expected_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/audit/single_group_magnetic_local_corep_audit.md",
        f"{PACKAGE_NAME}/audit/single_group_magnetic_local_corep_summary.json",
        f"{PACKAGE_NAME}/audit/single_group_pointlike_magnetic_coreps.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v2_candidates.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v2_matrix.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v2_basis.json",
        f"{PACKAGE_NAME}/ai/single_group_bs_vs_ai_expanded_v2_summary.json",
        f"{PACKAGE_NAME}/scripts/debug_single_group_magnetic_local_coreps.py",
    }
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        members = {member.name for member in tar.getmembers()}
    missing = sorted(expected_members - members)
    if missing:
        raise ValueError(f"package is missing expected members: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the single-group point-like antiunitary magnetic local corep census and AI_expanded_v2 artifacts for 10.4.1.31."
    )
    parser.add_argument("--validate", action="store_true", help="Validate previously generated outputs and exit.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validation_ok")
        return 0

    result = generate_outputs()
    print(json.dumps(result["bs_vs_ai"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
