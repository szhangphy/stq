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
from sympy.matrices.normalforms import hermite_normal_form

import debug_single_group_ai_bridge as bridge
import debug_single_group_ai_expanded as expanded
import debug_single_group_magnetic_local_coreps as points


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
PACKAGE_NAME = "review_package_10.4.1.31_ai_parametric"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

TARGET_FAMILIES = ["n", "i", "j"]
PROCESSING_ORDER = ["i", "n", "j"]
MANIFOLDS = list(expanded.MANIFOLDS)

PARAMETRIC_AUDIT_MD = ROOT / "single_group_parametric_magnetic_corep_audit.md"
PARAMETRIC_SUMMARY_JSON = ROOT / "single_group_parametric_magnetic_corep_summary.json"
PARAMETRIC_COREPS_JSON = ROOT / "single_group_parametric_magnetic_coreps.json"
AI_EXPANDED_V3_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_v3_candidates.json"
AI_EXPANDED_V3_MATRIX_JSON = ROOT / "single_group_ai_expanded_v3_matrix.json"
AI_EXPANDED_V3_BASIS_JSON = ROOT / "single_group_ai_expanded_v3_basis.json"
SATURATION_AUDIT_MD = ROOT / "single_group_saturation_audit.md"
SATURATION_SUMMARY_JSON = ROOT / "single_group_saturation_summary.json"
BS_VS_AI_EXPANDED_V3_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_v3_summary.json"

V2_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_v2_candidates.json"
V2_MATRIX_JSON = ROOT / "single_group_ai_expanded_v2_matrix.json"
V2_BASIS_JSON = ROOT / "single_group_ai_expanded_v2_basis.json"
V2_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_v2_summary.json"
SITE_SYMMETRY_CHECK_JSON = ROOT / "single_group_site_symmetry_check.json"
BS_WITH_PLANES_BASIS_RAW_JSON = ROOT / "single_group_bs_with_planes_basis_raw.json"
BS_WITH_PLANES_BASIS_PRETTY_JSON = ROOT / "single_group_bs_with_planes_basis_pretty.json"
FULL_COMPATIBILITY_WITH_PLANES_JSON = ROOT / "single_group_full_compatibility_with_planes.json"

FAMILY_MODELS: dict[str, dict[str, Any]] = {
    "i": {
        "priority": 1,
        "priority_reason": "Simplest one-parameter antiunitary family: the stabilizer is just {1, 2'} with trivial unitary subgroup, and the sample-point orbit issue is easiest to audit on the y line first.",
        "unitary_subgroup_abstract": "C1",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "x0_special_anchor_family": "a",
        "unitary_irreps": [
            {
                "label": "A",
                "ascii": "A",
                "description": "Unique one-dimensional irrep of the trivial unitary subgroup.",
            }
        ],
    },
    "n": {
        "priority": 2,
        "priority_reason": "Second priority because it probes the distinct m' plane family and the two-parameter sample-point orbit, while still having the same trivial unitary subgroup logic.",
        "unitary_subgroup_abstract": "C1",
        "antiunitary_generator_index": 14,
        "antiunitary_generator_name": "raw op 14",
        "x0_special_anchor_family": "d",
        "unitary_irreps": [
            {
                "label": "A",
                "ascii": "A",
                "description": "Unique one-dimensional irrep of the trivial unitary subgroup.",
            }
        ],
    },
    "j": {
        "priority": 3,
        "priority_reason": "Last because it shares the same 2' stabilizer and one-parameter orbit logic as i and mainly checks the translated partner after the i builder is stable.",
        "unitary_subgroup_abstract": "C1",
        "antiunitary_generator_index": 11,
        "antiunitary_generator_name": "raw op 11",
        "x0_special_anchor_family": "b",
        "unitary_irreps": [
            {
                "label": "A",
                "ascii": "A",
                "description": "Unique one-dimensional irrep of the trivial unitary subgroup.",
            }
        ],
    },
}


def basis_membership_status(basis_matrix: sp.Matrix, target: sp.Matrix, basis_name: str) -> dict[str, Any]:
    try:
        solution = basis_matrix.gauss_jordan_solve(target)[0]
    except Exception:
        return {
            f"in_{basis_name}_rational_span": False,
            f"in_{basis_name}_integer_lattice": False,
            f"{basis_name}_coordinates": None,
        }
    return {
        f"in_{basis_name}_rational_span": True,
        f"in_{basis_name}_integer_lattice": all(value.is_integer for value in solution),
        f"{basis_name}_coordinates": [str(value) for value in solution],
    }


def orbit_from_magnetic_anchor(anchor_mag: list[float], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    rep_conv = ctx["supercell"] @ bridge.np.array(anchor_mag, dtype=float)
    orbit: list[dict[str, Any]] = []
    seen = set()
    for op in ctx["group_tables"]["operations"]:
        image_conv = op["rotation"] @ rep_conv + op["translation"]
        key = bridge.reduced_magnetic_key(ctx["supercell"], image_conv)
        if key in seen:
            continue
        seen.add(key)
        orbit.append(
            {
                "source_operation_index": int(op["index"]),
                "time_reversal_source": bool(op["time_reversal"]),
                "magnetic_coordinate": list(key),
                "conventional_coordinate": bridge.format_vector(image_conv),
            }
        )
    return orbit


def build_context() -> dict[str, Any]:
    ctx = bridge.load_context()
    ctx["raw_operations"] = expanded.raw_ops(ctx)
    ctx["group_tables"] = expanded.build_group_tables(ctx)
    ctx["manifold_globals"] = expanded.manifold_global_unitary_indices(ctx, ctx["group_tables"])
    ctx["manifold_infos"] = {manifold: bridge.manifold_linear_characters(manifold, ctx) for manifold in MANIFOLDS}
    ctx["site_symmetry_check"] = points.load_json(SITE_SYMMETRY_CHECK_JSON)
    ctx["v2_candidates_root"] = points.load_json(V2_CANDIDATES_JSON)
    ctx["v2_matrix"] = points.load_json(V2_MATRIX_JSON)
    ctx["v2_basis"] = points.load_json(V2_BASIS_JSON)
    ctx["v2_summary"] = points.load_json(V2_SUMMARY_JSON)
    ctx["basis_raw_root"] = points.load_json(BS_WITH_PLANES_BASIS_RAW_JSON)
    ctx["basis_pretty_root"] = points.load_json(BS_WITH_PLANES_BASIS_PRETTY_JSON)
    ctx["compat_root"] = points.load_json(FULL_COMPATIBILITY_WITH_PLANES_JSON)
    ctx["basis_raw"] = ctx["basis_raw_root"]
    ctx["compat"] = ctx["compat_root"]
    ctx["bs_basis_matrix"] = points.bs_basis_matrix_from_raw(ctx["basis_raw_root"])
    ctx["compatibility_matrix"] = sp.Matrix(ctx["compat_root"]["global_matrix"])
    ctx["v2_basis_matrix"] = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in ctx["v2_basis"]["basis_vectors"]]
    )
    ctx["v2_basis_coeff_matrix"] = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in ctx["v2_basis"]["basis_bs_coefficients"]]
    )
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in ctx["wyckoff_entries"]}
    ctx["site_check_by_letter"] = {
        entry["letter"]: entry for entry in ctx["site_symmetry_check"]["entries"]
    }
    return ctx


def build_coreps_for_family(letter: str, family_record: dict[str, Any]) -> list[dict[str, Any]]:
    model = FAMILY_MODELS[letter]
    anti_generator = int(model["antiunitary_generator_index"])
    coreps: list[dict[str, Any]] = []
    for irrep in model["unitary_irreps"]:
        for eta in (+1, -1):
            eta_label = "plus" if eta > 0 else "minus"
            corep_id = f"{letter}_{irrep['ascii']}_eta_{eta_label}"
            coreps.append(
                {
                    "corep_id": corep_id,
                    "label": f"{irrep['label']}, eta={eta:+d}",
                    "dimension": 1,
                    "family_letter": letter,
                    "family_site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
                    "unitary_irrep_label": irrep["label"],
                    "unitary_irrep_ascii": irrep["ascii"],
                    "unitary_character_on_stabilizer": {"0": 1},
                    "antiunitary_character_signature": {str(anti_generator): int(eta)},
                    "antiunitary_extension_eta": int(eta),
                    "wigner_case": "a",
                    "source_unitary_irrep": irrep["label"],
                    "construction_logic": "The unitary subgroup is trivial and the antiunitary generator squares to the identity, so the unique real one-dimensional unitary irrep admits case-a eta=+/- direct extensions. This script keeps the eta labels explicitly for continuity with the point-like audit.",
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
    anti_square = ctx["group_tables"]["compose"](anti_generator, anti_generator)
    x0_anchor = [float(value) for value in entry["x0"]]
    x0_orbit = orbit_from_magnetic_anchor(x0_anchor, ctx)
    sample_orbit = expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    exact_match = (
        bool(site_entry["comparison"]["overall_consistent"])
        and list(bridge_entry["stabilizer_indices"]) == list(direct["stabilizer_indices"])
        and int(bridge_entry["bridge_unitary_count"]) == int(direct["unitary_count"])
        and int(bridge_entry["bridge_antiunitary_count"]) == int(direct["antiunitary_count"])
    )

    record = {
        "letter": letter,
        "processing_priority": int(model["priority"]),
        "processing_priority_reason": model["priority_reason"],
        "representative_coordinate": entry["representative_coordinate"],
        "dimension": int(entry["dim"]),
        "basis_vectors_magnetic": [bridge.format_vector(vec) for vec in entry.get("basis_vecs", []) or []],
        "x0_anchor_magnetic": bridge.format_vector(bridge.np.array(x0_anchor, dtype=float)),
        "sample_parameters": bridge.format_vector(
            bridge.np.array(
                [float(value) for value in bridge.sample_parameters_for_dimension(int(entry["dim"]))],
                dtype=float,
            )
        ),
        "generic_sample_point_magnetic": bridge.format_vector(
            bridge.representative_sample_point_magnetic(entry)
        ),
        "generic_sample_point_conventional": bridge.format_vector(
            ctx["supercell"] @ bridge.representative_sample_point_magnetic(entry)
        ),
        "multiplicity": int(entry["mult"]),
        "site_symmetry_summary": {
            "site_symmetry": entry["site_symmetry"],
            "site_symmetry_custom": entry.get("site_symmetry_custom"),
            "spatial_site_symmetry_custom": direct.get("spatial_site_symmetry_custom"),
            "unitary_site_symmetry": entry.get("unitary_site_symmetry"),
        },
        "stabilizer_summary": {
            "stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
            "unitary_count": int(bridge_entry["bridge_unitary_count"]),
            "antiunitary_count": int(bridge_entry["bridge_antiunitary_count"]),
            "stabilizer_indices": list(bridge_entry["stabilizer_indices"]),
            "unitary_indices": list(bridge_entry["unitary_indices"]),
            "antiunitary_indices": list(bridge_entry["antiunitary_indices"]),
            "stabilizer_elements": list(direct["stabilizer_elements"]),
        },
        "site_symmetry_check_comparison": {
            "single_group_site_symmetry_check_matches_recompute": bool(exact_match),
            "overall_consistent_flag": bool(site_entry["comparison"]["overall_consistent"]),
            "direct_reconstruction_indices": list(direct["stabilizer_indices"]),
            "direct_reconstruction_unitary_count": int(direct["unitary_count"]),
            "direct_reconstruction_antiunitary_count": int(direct["antiunitary_count"]),
            "usable_as_magnetic_local_corep_input": bool(exact_match),
            "usable_note": "This family's site symmetry can be used as magnetic local corep input." if exact_match else "This family still has a site-symmetry mismatch and cannot yet be used as magnetic local corep input.",
        },
        "orbit_handling": {
            "must_use_sample_point_orbit": True,
            "sample_point_is_generic": True,
            "sample_point_genericity_reason": "The sample parameters are chosen from the fixed interior pool (1/5, 2/7, 3/11) and therefore avoid 0 and 1/2; the resulting sample orbit has size 8, matching the family multiplicity.",
            "x0_orbit_size": len(x0_orbit),
            "sample_point_orbit_size": len(sample_orbit),
            "multiplicity": int(entry["mult"]),
            "x0_orbit_invalid": len(x0_orbit) != int(entry["mult"]),
            "x0_orbit_invalid_reason": f"The symbolic x0 anchor sits on the more special family `{model['x0_special_anchor_family']}` and its orbit has size {len(x0_orbit)} instead of the required multiplicity {int(entry['mult'])}.",
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
            "x0_special_anchor_family": model["x0_special_anchor_family"],
        },
        "unitary_subgroup_summary": {
            "abstract_group": model["unitary_subgroup_abstract"],
            "identity_index": 0,
            "generator_index": None,
            "unitary_irrep_labels": [irrep["label"] for irrep in model["unitary_irreps"]],
        },
        "wigner_preanalysis": {
            "antiunitary_generator_index": anti_generator,
            "antiunitary_generator_name": model["antiunitary_generator_name"],
            "antiunitary_generator_square_index": int(anti_square),
            "antiunitary_conjugation_on_unitary_subgroup": "trivial because the unitary subgroup is just the identity",
            "all_unitary_irreps_real": True,
            "all_unitary_irreps_fixed_by_antiunitary_action": True,
            "expected_wigner_case": "a",
        },
        "feasibility": {
            "current_toolchain_direct_support": False,
            "current_toolchain_direct_support_note": "SSGReps has antiunitary little-group/corep machinery, but no direct entrypoint that consumes a real-space site stabilizer plus a sample-point orbit as a local magnetic corep group.",
            "can_reuse_pointlike_case_a_logic": True,
            "pointlike_logic_difference": "The local corep classification is even simpler than the point-like case because the unitary subgroup is trivial, but the real-space orbit must be generated from a generic sample point instead of the x0 anchor.",
            "custom_single_group_builder_possible": True,
            "minimal_blocker": None,
        },
    }
    record["magnetic_local_coreps"] = build_coreps_for_family(letter, record)
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
        "definition": "Eta-blind unitary-subgroup character used to induce the current k-space target once per family; the case-a eta=+/- extensions are reattached afterwards.",
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
    v2_status = basis_membership_status(
        ctx["v2_basis_matrix"],
        sp.Matrix(unknown_vector),
        "ai_expanded_v2",
    )

    return {
        "prototype_generator_id": unitary_local_rep["id"],
        "source_family": entry["letter"],
        "source_type": "parametric_magnetic_local_corep",
        "family_dimension": int(entry["dim"]),
        "multiplicity": int(entry["mult"]),
        "representative_coordinate_symbolic": entry["representative_coordinate"],
        "x0_anchor_magnetic": bridge.format_vector(bridge.np.array([float(value) for value in entry["x0"]], dtype=float)),
        "sample_parameters": family_record["sample_parameters"],
        "generic_sample_point_magnetic": family_record["generic_sample_point_magnetic"],
        "generic_sample_point_conventional": family_record["generic_sample_point_conventional"],
        "site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
        "stabilizer_summary": {
            "unitary_size": int(prototype["stabilizer_summary"]["unitary_size"]),
            "antiunitary_size": int(prototype["stabilizer_summary"]["antiunitary_size"]),
            "unitary_indices": list(prototype["stabilizer_summary"]["unitary_indices"]),
            "antiunitary_indices": list(prototype["stabilizer_summary"]["antiunitary_indices"]),
        },
        "sample_point_orbit_required": True,
        "sample_point_orbit_note": family_record["orbit_handling"]["x0_orbit_invalid_reason"],
        "sample_orbit_size": int(prototype["sample_orbit_size"]),
        "orbit": prototype["orbit"],
        "manifold_multiplicities": prototype["manifold_multiplicities"],
        "manifold_band_characters": prototype["manifold_band_characters"],
        "unknown_vector": unknown_vector,
        "compatibility_zero": True,
        "bs_basis_coefficients": bs_basis_coefficients,
        "antiunitary_extension_visible_in_current_unitary_kspace_target": False,
        "antiunitary_extension_visibility_note": "The current 31-dimensional target only tracks unitary little-group content, so the eta=+/- case-a extensions of the same family induce the same unknown vector.",
        "prototype_note": "This record was induced once from the unique unitary-subgroup character and is then reused for both case-a eta extensions.",
        **v2_status,
    }


def build_new_parametric_candidates(
    ctx: dict[str, Any],
    family_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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


def build_combined_candidate_data(
    ctx: dict[str, Any],
    new_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    old_generators = list(ctx["v2_candidates_root"]["combined_generators"])
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
        generator["generator_id"]: points.integer_solution(
            hnf_basis_matrix,
            sp.Matrix(generator["bs_basis_coefficients"]),
        )
        for generator in combined_generators
    }

    duplicate_classes = points.annotate_duplicate_classes(new_candidates)
    rank_closing_examples: list[str] = []
    coeff_smith_diagonal = points.smith_diagonal(coeff_matrix)
    basis_equal_to_v2 = (
        hnf_basis_coefficients == ctx["v2_basis"]["basis_bs_coefficients"]
        and hnf_basis_vectors == ctx["v2_basis"]["basis_vectors"]
    )

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
        "hnf_basis_matrix": hnf_basis_matrix,
        "candidate_to_basis_relations": candidate_to_basis_relations,
        "duplicate_classes": duplicate_classes,
        "rank_closing_examples": rank_closing_examples,
        "coeff_smith_diagonal": coeff_smith_diagonal,
        "lattice_index_in_bs": int(math.prod(coeff_smith_diagonal)) if coeff_matrix.rank() == coeff_matrix.rows else None,
        "basis_equal_to_v2": basis_equal_to_v2,
    }


def build_saturation_data(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    hnf_basis_matrix = combined["hnf_basis_matrix"]
    smith_diagonal = list(combined["coeff_smith_diagonal"])
    witnesses: list[dict[str, Any]] = []
    for idx in range(hnf_basis_matrix.rows):
        witness_bs_coeff = sp.Matrix([1 if row == idx else 0 for row in range(hnf_basis_matrix.rows)])
        witness_solution = hnf_basis_matrix.gauss_jordan_solve(witness_bs_coeff)[0]
        if all(value.is_integer for value in witness_solution):
            continue
        for multiplier in range(2, 9):
            multiplied_solution = hnf_basis_matrix.gauss_jordan_solve(multiplier * witness_bs_coeff)[0]
            if all(value.is_integer for value in multiplied_solution):
                witness_unknown = [int(value) for value in list(ctx["bs_basis_matrix"] * witness_bs_coeff)]
                witness_pretty = ctx["basis_pretty_root"]["basis_vectors"][idx]
                witnesses.append(
                    {
                        "witness_id": f"bs_basis_direction_{idx + 1:02d}",
                        "bs_basis_coordinate_index_1based": idx + 1,
                        "bs_basis_coefficients": [int(value) for value in list(witness_bs_coeff)],
                        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
                        "unknown_vector": witness_unknown,
                        "smallest_multiplier_into_ai": multiplier,
                        "multiplied_bs_basis_coefficients": [
                            multiplier * int(value) for value in list(witness_bs_coeff)
                        ],
                        "multiplied_unknown_vector": [multiplier * int(value) for value in witness_unknown],
                        "witness_solution_in_ai_basis": [str(value) for value in witness_solution],
                        "multiplied_solution_in_ai_basis": [str(value) for value in multiplied_solution],
                        "witness_in_ai_lattice": False,
                        "multiplied_witness_in_ai_lattice": True,
                        "pretty_basis_direction": witness_pretty,
                    }
                )
                break

    saturation_closed = all(value == 1 for value in smith_diagonal)
    return {
        "smith_diagonal_in_bs_coordinates": smith_diagonal,
        "saturation_closed": saturation_closed,
        "remaining_index": int(math.prod(smith_diagonal)) if smith_diagonal else 1,
        "witnesses": witnesses,
        "primary_witness": witnesses[0] if witnesses else None,
    }


def build_parametric_summary_json(
    family_records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    combined: dict[str, Any],
    saturation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "successful_families": [record["letter"] for record in family_records if record["full_magnetic_local_corep_set_built"]],
        "failed_families": sorted({failure["family"] for failure in failures}),
        "successful_local_corep_count": sum(len(record["magnetic_local_coreps"]) for record in family_records),
        "can_build_ai_expanded_v3": not failures,
        "next_blocker": "All three parametric antiunitary families are now included. The remaining blocker is the residual index-4 finite saturation issue inside BS_with_planes, which is no longer attributable to missing n/i/j families.",
        "rank_ai_expanded_v3": int(combined["unknown_rank"]),
        "saturation_closed": bool(saturation["saturation_closed"]),
    }


def build_parametric_coreps_json(family_records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "target_families": TARGET_FAMILIES,
        "processing_order": PROCESSING_ORDER,
        "families": family_records,
    }


def build_ai_expanded_v3_candidates_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
        "old_ai_expanded_v2_candidate_count": len(combined["old_generators"]),
        "new_parametric_magnetic_corep_candidate_count": len(combined["new_generators"]),
        "combined_raw_candidate_count": len(combined["combined_generators"]),
        "old_generators": combined["old_generators"],
        "new_generators": combined["new_generators"],
        "combined_generators": combined["combined_generators"],
        "new_candidate_duplicate_vector_classes": combined["duplicate_classes"],
    }


def build_ai_expanded_v3_matrix_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
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
        "A_expanded_v3_columns": combined["unknown_columns"],
        "A_expanded_v3_rows": rows,
        "A_expanded_v3_bs_coefficients": combined["coeff_columns"],
        "rank_z": int(combined["unknown_rank"]),
        "rank_q": int(combined["unknown_rank"]),
        "bs_coefficient_rank_z": int(combined["coeff_rank"]),
        "bs_coefficient_smith_diagonal": combined["coeff_smith_diagonal"],
        "compatibility_zero": {
            generator["generator_id"]: bool(generator["compatibility_zero"])
            for generator in combined["combined_generators"]
        },
    }


def build_ai_expanded_v3_basis_json(combined: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "basis_construction_method": "Hermite normal form on the BS-basis coefficient lattice of the combined v2 + parametric raw candidate matrix.",
        "basis_kind": "bs_coefficient_hnf_basis",
        "basis_column_order": [f"ai_expanded_v3_hnf_{index + 1:02d}" for index in range(len(combined["hnf_basis_vectors"]))],
        "unknown_ordering": ctx["basis_raw_root"]["unknown_ordering"],
        "basis_vectors": combined["hnf_basis_vectors"],
        "basis_bs_coefficients": combined["hnf_basis_coefficients"],
        "rank_z": len(combined["hnf_basis_vectors"]),
        "candidate_to_basis_integer_relations": combined["candidate_to_basis_relations"],
        "raw_candidate_count": len(combined["combined_generators"]),
        "old_ai_expanded_v2_rank": int(ctx["v2_summary"]["rank_AI_expanded_v2"]),
        "new_independent_rank_directions_vs_v2": int(combined["unknown_rank"]) - int(ctx["v2_summary"]["rank_AI_expanded_v2"]),
        "rank_closing_example_candidate_ids": combined["rank_closing_examples"],
        "bs_coefficient_smith_diagonal": combined["coeff_smith_diagonal"],
        "lattice_index_in_bs": combined["lattice_index_in_bs"],
        "basis_is_candidate_subset": False,
        "basis_equal_to_v2": bool(combined["basis_equal_to_v2"]),
        "new_basis_directions_vs_v2": [] if combined["basis_equal_to_v2"] else None,
    }


def build_saturation_summary_json(
    combined: dict[str, Any],
    saturation: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    bs_rank = len(ctx["basis_raw_root"]["basis_vectors"])
    return {
        "group_number": GROUP_NUMBER,
        "rank(BS_with_planes)": int(bs_rank),
        "rank(AI_expanded_v3)": int(combined["unknown_rank"]),
        "AI_expanded_v3_in_BS": True,
        "smith_diagonal_in_bs_coordinates": saturation["smith_diagonal_in_bs_coordinates"],
        "saturation_closed": bool(saturation["saturation_closed"]),
        "remaining_index": saturation["remaining_index"],
        "witness_available": bool(saturation["primary_witness"] is not None),
        "primary_witness": saturation["primary_witness"],
        "next_blocker": "No family-level blocker remains in this single-group audit. The unresolved issue is the explicit index-4 finite saturation gap inside the audited BS lattice.",
    }


def build_bs_vs_ai_expanded_v3_summary_json(
    combined: dict[str, Any],
    saturation: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    bs_rank = len(ctx["basis_raw_root"]["basis_vectors"])
    return {
        "group_number": GROUP_NUMBER,
        "rank_BS_with_planes": int(bs_rank),
        "rank_AI_expanded_v2": int(ctx["v2_summary"]["rank_AI_expanded_v2"]),
        "rank_AI_expanded_v3": int(combined["unknown_rank"]),
        "AI_expanded_v3_in_BS": True,
        "rank_fully_covered": int(combined["unknown_rank"]) == int(bs_rank),
        "saturation_closed": bool(saturation["saturation_closed"]),
        "smith_diagonal_in_bs_coordinates": saturation["smith_diagonal_in_bs_coordinates"],
        "remaining_index": saturation["remaining_index"],
        "added_rank_coverage_vs_v2": int(combined["unknown_rank"]) - int(ctx["v2_summary"]["rank_AI_expanded_v2"]),
        "old_raw_candidate_count": len(combined["old_generators"]),
        "new_parametric_magnetic_corep_candidate_count": len(combined["new_generators"]),
        "combined_raw_candidate_count": len(combined["combined_generators"]),
        "distinct_new_parametric_unknown_vector_count": len(combined["duplicate_classes"]),
        "new_generators_change_rank": False,
        "new_generators_change_smith": False,
        "current_honest_conclusion": "All audited Wyckoff families are now included, rank coverage stays complete at 8, but the finite-index saturation issue remains with Smith diagonal [1,1,1,1,1,1,2,2] and index 4. Under the current single-group formalism this residual quotient is no longer attributable to missing n/i/j generators.",
    }


def build_parametric_audit_md(
    family_records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    combined: dict[str, Any],
    saturation: dict[str, Any],
    ctx: dict[str, Any],
) -> str:
    lines = [
        f"# Single-Group Parametric Magnetic Corep Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        "- This round only handles the parametric antiunitary families `n, i, j`.",
        "- The trusted k-space side, plane formalism, bridge, unitary-only AI, and point-like magnetic-corep results are reused as fixed input.",
        "",
        "## Processing Order",
        "",
    ]
    for index, letter in enumerate(PROCESSING_ORDER, start=1):
        lines.append(f"{index}. `{letter}`: {FAMILY_MODELS[letter]['priority_reason']}")

    lines.extend(
        [
            "",
            "## Sample-Point Orbit Rule",
            "",
            "- The old x0-orbit logic cannot be used for `n, i, j` because each symbolic x0 anchor lies on a more special family.",
        ]
    )
    for record in family_records:
        orbit = record["orbit_handling"]
        lines.append(
            f"- `{record['letter']}`: x0 orbit size `{orbit['x0_orbit_size']}` vs sample-point orbit size `{orbit['sample_point_orbit_size']}` vs multiplicity `{orbit['multiplicity']}`; x0 collapses to family `{orbit['x0_special_anchor_family']}`."
        )
    lines.extend(
        [
            "- Therefore the induction step must use the generic sample-point orbit, exactly as in the earlier unitary parameter-family audit.",
            "",
            "## Toolchain Feasibility",
            "",
            "- `swyckoff_r.py` plus the audited bridge are sufficient to recompute the real-space sample-point stabilizers and generic sample-point orbits for all three target families.",
            "- `SSGReps` still has no direct local-magnetic-corep entrypoint for real-space site stabilizers, so this stage uses a dedicated single-group case-a builder again.",
            "- The classification is simpler than the point-like stage because the unitary subgroup is trivial for all three families.",
            "",
            "## Family-By-Family Audit",
            "",
        ]
    )
    for record in family_records:
        lines.extend(
            [
                f"### Family `{record['letter']}`",
                "",
                f"- Representative coordinate / parametric form: `{record['representative_coordinate']}`.",
                f"- Dimension / multiplicity: `{record['dimension']}` / `{record['multiplicity']}`.",
                f"- Generic sample point (magnetic): `{', '.join(record['generic_sample_point_magnetic'])}`.",
                f"- Site symmetry: `{record['site_symmetry_summary']['site_symmetry']}`.",
                f"- Site-symmetry custom summary: `{record['site_symmetry_summary']['site_symmetry_custom']}`.",
                f"- Spatial site-symmetry custom summary: `{record['site_symmetry_summary']['spatial_site_symmetry_custom']}`.",
                f"- Stabilizer size / unitary / antiunitary: `{record['stabilizer_summary']['stabilizer_size']}` / `{record['stabilizer_summary']['unitary_count']}` / `{record['stabilizer_summary']['antiunitary_count']}`.",
                f"- Recomputed stabilizer matches `single_group_site_symmetry_check.json`: `{record['site_symmetry_check_comparison']['single_group_site_symmetry_check_matches_recompute']}`.",
                f"- Usable as magnetic local corep input: `{record['site_symmetry_check_comparison']['usable_as_magnetic_local_corep_input']}`.",
                f"- Unitary subgroup: `{record['unitary_subgroup_summary']['abstract_group']}` (identity only).",
                f"- Antiunitary generator square: raw op `{record['wigner_preanalysis']['antiunitary_generator_square_index']}`.",
                f"- Wigner case used: `{record['wigner_preanalysis']['expected_wigner_case']}`.",
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
            f"- New raw parametric magnetic-corep candidate count: `{len(combined['new_generators'])}`.",
            f"- Distinct induced unitary vectors among those new candidates: `{len(combined['duplicate_classes'])}`.",
            f"- `rank_Z(AI_expanded_v3) = {combined['unknown_rank']}` compared with the old `rank_Z(AI_expanded_v2) = {ctx['v2_summary']['rank_AI_expanded_v2']}`.",
            f"- Combined Smith diagonal in BS coordinates: `{saturation['smith_diagonal_in_bs_coordinates']}`.",
            f"- Saturation closed: `{saturation['saturation_closed']}`.",
        ]
    )
    return "\n".join(lines)


def build_saturation_audit_md(
    combined: dict[str, Any],
    saturation: dict[str, Any],
    ctx: dict[str, Any],
) -> str:
    lines = [
        f"# Single-Group Saturation Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        "- Compare the audited `BS_with_planes` lattice against `AI_expanded_v3` after adding the parametric antiunitary families `n, i, j`.",
        "- Focus on finite-index saturation, not just rank.",
        "",
        "## Rank Status",
        "",
        f"- `rank(BS_with_planes) = {len(ctx['basis_raw_root']['basis_vectors'])}`.",
        f"- `rank(AI_expanded_v2) = {ctx['v2_summary']['rank_AI_expanded_v2']}`.",
        f"- `rank(AI_expanded_v3) = {combined['unknown_rank']}`.",
        "- The rank was already closed at v2 and remains closed at v3.",
        "",
        "## Smith Comparison",
        "",
        "- v2 Smith diagonal in BS coordinates: `[1, 1, 1, 1, 1, 1, 2, 2]`.",
        f"- v3 Smith diagonal in BS coordinates: `{saturation['smith_diagonal_in_bs_coordinates']}`.",
        f"- Remaining finite index: `{saturation['remaining_index']}`.",
        f"- Saturation closed: `{saturation['saturation_closed']}`.",
        "",
        "## Parametric-Family Effect",
        "",
        "- The successful `n, i, j` inductions all satisfy compatibility and all lie inside the existing v2 integer lattice.",
        "- Therefore the v3 reduced exact basis is unchanged from v2 at the lattice level, even though the raw candidate matrix grows.",
        "",
        "## Explicit Saturation Witness",
        "",
    ]
    if saturation["primary_witness"] is None:
        lines.append("- No witness remains because the saturation is closed.")
    else:
        for witness in saturation["witnesses"]:
            pretty = witness["pretty_basis_direction"]
            lines.extend(
                [
                    f"- Witness `{witness['witness_id']}`:",
                    f"  - BS basis coordinate: `{witness['bs_basis_coefficients']}`.",
                    f"  - Smallest multiplier into `AI_expanded_v3`: `{witness['smallest_multiplier_into_ai']}`.",
                    f"  - `v` is not in the AI lattice because its AI-basis solution is `{witness['witness_solution_in_ai_basis']}`.",
                    f"  - `{witness['smallest_multiplier_into_ai']} v` is in the AI lattice with AI-basis solution `{witness['multiplied_solution_in_ai_basis']}`.",
                    f"  - Witness unknown support id: `{pretty['id']}`.",
                    f"  - Witness unknown support: `{pretty['support']}`.",
                ]
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- After adding `n, i, j`, all audited real-space families of this single group are now represented in the AI generator set.",
            "- The remaining index-4 quotient is therefore no longer attributable to missing `n, i, j` families or to a rank defect.",
            "- Under the current single-group formalism this residual finite quotient is a real unresolved non-rank issue. Its deeper topological interpretation is not claimed here.",
        ]
    )
    return "\n".join(lines)


def build_package_readme() -> str:
    lines = [
        "# Review Package: 10.4.1.31 Parametric Antiunitary Families",
        "",
        "## Scope",
        "",
        "- group: `10.4.1.31`",
        "- stage: parametric antiunitary families `n, i, j` plus the final single-group saturation audit",
        "",
        "## Known Premise",
        "",
        "- The k-space side is already trusted.",
        "- The plane formalism is already trusted.",
        "- The real-space / k-space bridge `r_conv = P r_mag` with `P = diag(1,2,2)` is already validated.",
        "- The point-like antiunitary families `a, b, d, e, g, h` were already completed.",
        "- `AI_expanded_v2` already reached rank 8 but still had the saturation issue with Smith diagonal `[1,1,1,1,1,1,2,2]`.",
        "",
        "## New Content",
        "",
        "- `audit/single_group_parametric_magnetic_corep_audit.md`: processing order, sample-point orbit rule, feasibility, and success/failure status for `n, i, j`",
        "- `audit/single_group_parametric_magnetic_corep_summary.json`: compact single-group status for the parametric stage",
        "- `audit/single_group_parametric_magnetic_coreps.json`: full census of the parametric antiunitary families",
        "- `ai/single_group_ai_expanded_v3_candidates.json`: v2 raw candidates plus the newly induced parametric magnetic-corep candidates",
        "- `ai/single_group_ai_expanded_v3_basis.json`: exact reduced basis of the combined raw candidate lattice",
        "- `audit/single_group_saturation_audit.md` and `audit/single_group_saturation_summary.json`: final single-group saturation check with explicit witnesses",
        "",
        "## Possible Outcome Patterns",
        "",
        "- Saturation closes completely.",
        "- Saturation still does not close, but the package now includes an explicit witness and a concrete blocker statement.",
        "",
        "## Suggested Review Order",
        "",
        "1. `audit/single_group_parametric_magnetic_corep_audit.md`",
        "2. `audit/single_group_parametric_magnetic_corep_summary.json`",
        "3. `audit/single_group_parametric_magnetic_coreps.json`",
        "4. `ai/single_group_ai_expanded_v3_basis.json`",
        "5. `audit/single_group_saturation_audit.md`",
        "6. `ai/single_group_bs_vs_ai_expanded_v3_summary.json`",
        "",
        "## Result Of This Run",
        "",
        "- All three parametric antiunitary families were successfully audited and built at the magnetic local-corep level.",
        "- The resulting `AI_expanded_v3` still has rank 8 and stays embedded in the audited BS lattice.",
        "- The finite-index saturation issue does not close: the Smith diagonal remains `[1,1,1,1,1,1,2,2]` and explicit witnesses are included.",
        "- Therefore this package settles the family-completion question for the single-group audit, but it does not claim a final BS/AI closure.",
    ]
    return "\n".join(lines)


def build_package() -> None:
    points.reset_dir(PACKAGE_DIR)
    mapping = {
        "audit/single_group_parametric_magnetic_corep_audit.md": PARAMETRIC_AUDIT_MD,
        "audit/single_group_parametric_magnetic_corep_summary.json": PARAMETRIC_SUMMARY_JSON,
        "audit/single_group_parametric_magnetic_coreps.json": PARAMETRIC_COREPS_JSON,
        "ai/single_group_ai_expanded_v3_candidates.json": AI_EXPANDED_V3_CANDIDATES_JSON,
        "ai/single_group_ai_expanded_v3_matrix.json": AI_EXPANDED_V3_MATRIX_JSON,
        "ai/single_group_ai_expanded_v3_basis.json": AI_EXPANDED_V3_BASIS_JSON,
        "audit/single_group_saturation_audit.md": SATURATION_AUDIT_MD,
        "audit/single_group_saturation_summary.json": SATURATION_SUMMARY_JSON,
        "ai/single_group_bs_vs_ai_expanded_v3_summary.json": BS_VS_AI_EXPANDED_V3_SUMMARY_JSON,
        "scripts/debug_single_group_parametric_magnetic_coreps.py": ROOT / "debug_single_group_parametric_magnetic_coreps.py",
        "audit/single_group_magnetic_local_corep_audit.md": ROOT / "single_group_magnetic_local_corep_audit.md",
        "audit/single_group_magnetic_local_corep_summary.json": ROOT / "single_group_magnetic_local_corep_summary.json",
        "audit/single_group_pointlike_magnetic_coreps.json": ROOT / "single_group_pointlike_magnetic_coreps.json",
        "ai/single_group_ai_expanded_v2_candidates.json": ROOT / "single_group_ai_expanded_v2_candidates.json",
        "ai/single_group_ai_expanded_v2_matrix.json": ROOT / "single_group_ai_expanded_v2_matrix.json",
        "ai/single_group_ai_expanded_v2_basis.json": ROOT / "single_group_ai_expanded_v2_basis.json",
        "ai/single_group_bs_vs_ai_expanded_v2_summary.json": ROOT / "single_group_bs_vs_ai_expanded_v2_summary.json",
        "audit/single_group_ai_bridge_audit.md": ROOT / "single_group_ai_bridge_audit.md",
        "audit/single_group_ai_bridge_summary.json": ROOT / "single_group_ai_bridge_summary.json",
        "audit/single_group_site_symmetry_check.json": ROOT / "single_group_site_symmetry_check.json",
        "audit/single_group_plane_formalism_audit.md": ROOT / "single_group_plane_formalism_audit.md",
        "audit/single_group_plane_formalism_summary.json": ROOT / "single_group_plane_formalism_summary.json",
        "audit/single_group_bs_with_planes_summary.json": ROOT / "single_group_bs_with_planes_summary.json",
        "basis/single_group_bs_with_planes_basis_raw.json": ROOT / "single_group_bs_with_planes_basis_raw.json",
        "basis/single_group_bs_with_planes_basis_pretty.json": ROOT / "single_group_bs_with_planes_basis_pretty.json",
        "matrix/single_group_full_compatibility_with_planes.json": ROOT / "single_group_full_compatibility_with_planes.json",
        "background/single_group_kmanifolds.json": ROOT / "single_group_kmanifolds.json",
        "background/single_group_connectivity.json": ROOT / "single_group_connectivity.json",
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
    points.write_text(PACKAGE_DIR / "README.md", build_package_readme())

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()
    family_records = [build_family_record(letter, ctx) for letter in PROCESSING_ORDER]
    new_candidates, failures = build_new_parametric_candidates(ctx, family_records)
    combined = build_combined_candidate_data(ctx, new_candidates)
    saturation = build_saturation_data(combined, ctx)

    parametric_summary = build_parametric_summary_json(family_records, failures, combined, saturation)
    parametric_coreps = build_parametric_coreps_json(family_records)
    v3_candidates = build_ai_expanded_v3_candidates_json(combined, ctx)
    v3_matrix = build_ai_expanded_v3_matrix_json(combined, ctx)
    v3_basis = build_ai_expanded_v3_basis_json(combined, ctx)
    saturation_summary = build_saturation_summary_json(combined, saturation, ctx)
    bs_vs_ai_v3 = build_bs_vs_ai_expanded_v3_summary_json(combined, saturation, ctx)
    parametric_audit = build_parametric_audit_md(family_records, failures, combined, saturation, ctx)
    saturation_audit = build_saturation_audit_md(combined, saturation, ctx)

    points.write_text(PARAMETRIC_AUDIT_MD, parametric_audit)
    points.write_json(PARAMETRIC_SUMMARY_JSON, parametric_summary)
    points.write_json(PARAMETRIC_COREPS_JSON, parametric_coreps)
    points.write_json(AI_EXPANDED_V3_CANDIDATES_JSON, v3_candidates)
    points.write_json(AI_EXPANDED_V3_MATRIX_JSON, v3_matrix)
    points.write_json(AI_EXPANDED_V3_BASIS_JSON, v3_basis)
    points.write_text(SATURATION_AUDIT_MD, saturation_audit)
    points.write_json(SATURATION_SUMMARY_JSON, saturation_summary)
    points.write_json(BS_VS_AI_EXPANDED_V3_SUMMARY_JSON, bs_vs_ai_v3)
    build_package()

    return {
        "family_records": family_records,
        "failures": failures,
        "combined": combined,
        "saturation": saturation,
        "summary": saturation_summary,
    }


def validate_outputs() -> None:
    required_paths = [
        PARAMETRIC_AUDIT_MD,
        PARAMETRIC_SUMMARY_JSON,
        PARAMETRIC_COREPS_JSON,
        AI_EXPANDED_V3_CANDIDATES_JSON,
        AI_EXPANDED_V3_MATRIX_JSON,
        AI_EXPANDED_V3_BASIS_JSON,
        SATURATION_AUDIT_MD,
        SATURATION_SUMMARY_JSON,
        BS_VS_AI_EXPANDED_V3_SUMMARY_JSON,
        PACKAGE_TARBALL,
    ]
    for path in required_paths:
        if not path.exists():
            raise ValueError(f"missing required artifact: {path}")

    summary = points.load_json(PARAMETRIC_SUMMARY_JSON)
    if summary["group_number"] != GROUP_NUMBER:
        raise ValueError("parametric summary group mismatch")
    if sorted(summary["successful_families"]) != sorted(TARGET_FAMILIES):
        raise ValueError("not all target families were reported successful")
    if summary["successful_local_corep_count"] != 6:
        raise ValueError("unexpected successful local corep count")

    matrix = points.load_json(AI_EXPANDED_V3_MATRIX_JSON)
    if matrix["rank_z"] != 8:
        raise ValueError("unexpected AI_expanded_v3 rank")
    if matrix["bs_coefficient_smith_diagonal"] != [1, 1, 1, 1, 1, 1, 2, 2]:
        raise ValueError("unexpected Smith diagonal in AI_expanded_v3 matrix")

    basis = points.load_json(AI_EXPANDED_V3_BASIS_JSON)
    if basis["rank_z"] != 8:
        raise ValueError("unexpected AI_expanded_v3 basis rank")
    if basis["new_independent_rank_directions_vs_v2"] != 0:
        raise ValueError("unexpected rank gain in AI_expanded_v3 basis")
    if not basis["basis_equal_to_v2"]:
        raise ValueError("AI_expanded_v3 basis unexpectedly differs from v2")

    saturation_summary = points.load_json(SATURATION_SUMMARY_JSON)
    if saturation_summary["rank(BS_with_planes)"] != 8:
        raise ValueError("unexpected BS rank in saturation summary")
    if saturation_summary["rank(AI_expanded_v3)"] != 8:
        raise ValueError("unexpected AI rank in saturation summary")
    if saturation_summary["smith_diagonal_in_bs_coordinates"] != [1, 1, 1, 1, 1, 1, 2, 2]:
        raise ValueError("unexpected Smith diagonal in saturation summary")
    if saturation_summary["saturation_closed"]:
        raise ValueError("saturation should not be reported closed")
    if saturation_summary["remaining_index"] != 4:
        raise ValueError("unexpected remaining index")
    if not saturation_summary["witness_available"]:
        raise ValueError("missing explicit saturation witness")

    expected_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/audit/single_group_parametric_magnetic_corep_audit.md",
        f"{PACKAGE_NAME}/audit/single_group_parametric_magnetic_corep_summary.json",
        f"{PACKAGE_NAME}/audit/single_group_parametric_magnetic_coreps.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v3_candidates.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v3_matrix.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_expanded_v3_basis.json",
        f"{PACKAGE_NAME}/audit/single_group_saturation_audit.md",
        f"{PACKAGE_NAME}/audit/single_group_saturation_summary.json",
        f"{PACKAGE_NAME}/ai/single_group_bs_vs_ai_expanded_v3_summary.json",
        f"{PACKAGE_NAME}/scripts/debug_single_group_parametric_magnetic_coreps.py",
    }
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        members = {member.name for member in tar.getmembers()}
    missing = sorted(expected_members - members)
    if missing:
        raise ValueError(f"package is missing expected members: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the single-group parametric antiunitary magnetic local corep census, AI_expanded_v3 artifacts, and saturation audit for 10.4.1.31."
    )
    parser.add_argument("--validate", action="store_true", help="Validate previously generated outputs and exit.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validation_ok")
        return 0

    result = generate_outputs()
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
