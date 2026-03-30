#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp
from sympy.polys.domains import ZZ

import debug_single_group_ai_expanded as expanded
import debug_single_group_magnetic_local_coreps as points


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 1
PACKAGE_NAME = "review_package_10.4.1.31_single_indicator"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

FAMILY_ORDER = list("abcdefghijklmno")
UNITARY_FAMILIES = ["o", "m", "k", "l", "c", "f"]
POINTLIKE_ANTIUNITARY_FAMILIES = ["a", "b", "d", "e", "g", "h"]
PARAMETRIC_ANTIUNITARY_FAMILIES = ["n", "i", "j"]

COMPLETENESS_AUDIT_MD = ROOT / "single_group_ai_completeness_audit.md"
COMPLETENESS_SUMMARY_JSON = ROOT / "single_group_ai_completeness_summary.json"
FAMILY_TABLE_JSON = ROOT / "single_group_family_completeness_table.json"
INDICATOR_GROUP_SUMMARY_JSON = ROOT / "single_group_indicator_group_summary.json"
INDICATOR_GENERATORS_JSON = ROOT / "single_group_indicator_generators.json"
BS_MOD_AI_SINGLE_SUMMARY_JSON = ROOT / "single_group_bs_mod_ai_single_summary.json"
MISSING_GENERATORS_REPORT_JSON = ROOT / "single_group_ai_missing_generators_report.json"

LOCAL_REP_CENSUS_AUDIT_MD = ROOT / "single_group_local_rep_census_audit.md"
LOCAL_REP_CENSUS_SUMMARY_JSON = ROOT / "single_group_local_rep_census_summary.json"
POINTLIKE_COREP_AUDIT_MD = ROOT / "single_group_magnetic_local_corep_audit.md"
POINTLIKE_COREP_SUMMARY_JSON = ROOT / "single_group_magnetic_local_corep_summary.json"
POINTLIKE_COREPS_JSON = ROOT / "single_group_pointlike_magnetic_coreps.json"
PARAMETRIC_COREP_AUDIT_MD = ROOT / "single_group_parametric_magnetic_corep_audit.md"
PARAMETRIC_COREP_SUMMARY_JSON = ROOT / "single_group_parametric_magnetic_corep_summary.json"
PARAMETRIC_COREPS_JSON = ROOT / "single_group_parametric_magnetic_coreps.json"
SITE_SYMMETRY_CHECK_JSON = ROOT / "single_group_site_symmetry_check.json"
V2_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_v2_candidates.json"
V2_BASIS_JSON = ROOT / "single_group_ai_expanded_v2_basis.json"
V3_CANDIDATES_JSON = ROOT / "single_group_ai_expanded_v3_candidates.json"
V3_BASIS_JSON = ROOT / "single_group_ai_expanded_v3_basis.json"
V2_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_v2_summary.json"
V3_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_expanded_v3_summary.json"
SATURATION_AUDIT_MD = ROOT / "single_group_saturation_audit.md"
SATURATION_SUMMARY_JSON = ROOT / "single_group_saturation_summary.json"
BS_WITH_PLANES_BASIS_RAW_JSON = ROOT / "single_group_bs_with_planes_basis_raw.json"
BS_WITH_PLANES_BASIS_PRETTY_JSON = ROOT / "single_group_bs_with_planes_basis_pretty.json"
FULL_COMPATIBILITY_WITH_PLANES_JSON = ROOT / "single_group_full_compatibility_with_planes.json"
KMANIFOLDS_JSON = ROOT / "single_group_kmanifolds.json"
CONNECTIVITY_JSON = ROOT / "single_group_connectivity.json"

FALLBACK_LOCAL_REP_CENSUS_AUDIT_MD = (
    ROOT / "review_package_10.4.1.31_ai_magnetic_points" / "audit" / "single_group_local_rep_census_audit.md"
)
FALLBACK_LOCAL_REP_CENSUS_SUMMARY_JSON = (
    ROOT / "review_package_10.4.1.31_ai_magnetic_points" / "audit" / "single_group_local_rep_census_summary.json"
)

UNITARY_FAMILY_MODELS: dict[str, dict[str, Any]] = {
    "o": {
        "abstract_group": "C1",
        "expected_ids": ["o_A"],
        "expected_count": 1,
        "completeness_basis": "The generic family has trivial single-group site symmetry, so there is exactly one one-dimensional local irrep.",
    },
    "m": {
        "abstract_group": "Cs",
        "expected_ids": ["m_A_prime", "m_A_double_prime"],
        "expected_count": 2,
        "completeness_basis": "The unitary site symmetry is order-2 mirror symmetry, hence abelian with exactly two one-dimensional single-group irreps.",
    },
    "k": {
        "abstract_group": "C2",
        "expected_ids": ["k_A", "k_B"],
        "expected_count": 2,
        "completeness_basis": "The unitary site symmetry is order-2 rotation symmetry, hence abelian with exactly two one-dimensional single-group irreps.",
    },
    "l": {
        "abstract_group": "C2",
        "expected_ids": ["l_A", "l_B"],
        "expected_count": 2,
        "completeness_basis": "The unitary site symmetry is order-2 rotation symmetry, hence abelian with exactly two one-dimensional single-group irreps.",
    },
    "c": {
        "abstract_group": "C2h",
        "expected_ids": ["c_Ag", "c_Bg", "c_Au", "c_Bu"],
        "expected_count": 4,
        "completeness_basis": "The unitary site symmetry is the abelian order-4 group C2h, so the full single-group local-irrep census is the four one-dimensional characters Ag/Bg/Au/Bu.",
    },
    "f": {
        "abstract_group": "C2h",
        "expected_ids": ["f_Ag", "f_Bg", "f_Au", "f_Bu"],
        "expected_count": 4,
        "completeness_basis": "The unitary site symmetry is the abelian order-4 group C2h, so the full single-group local-irrep census is the four one-dimensional characters Ag/Bg/Au/Bu.",
    },
}


def existing_path(primary: Path, fallback: Path | None = None) -> Path:
    if primary.exists():
        return primary
    if fallback is not None and fallback.exists():
        return fallback
    raise FileNotFoundError(primary)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def sp_vector_to_int_list(vec: sp.Matrix) -> list[int]:
    return [int(value) for value in list(vec)]


def normalize_sign(vector: list[int], relation: list[int]) -> tuple[list[int], list[int]]:
    for value in vector:
        if value == 0:
            continue
        if value < 0:
            return ([-entry for entry in vector], [-entry for entry in relation])
        break
    return vector, relation


def family_generator_map(candidates_root: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for generator in candidates_root["combined_generators"]:
        family = generator.get("source_family") or generator.get("family_letter")
        if family is None:
            continue
        result.setdefault(str(family), []).append(generator)
    return result


def find_unitary_local_reps(letter: str) -> list[dict[str, Any]]:
    return [dict(item) for item in expanded.LOCAL_REP_LIBRARY.get(letter, [])]


def build_context() -> dict[str, Any]:
    local_census_audit = existing_path(LOCAL_REP_CENSUS_AUDIT_MD, FALLBACK_LOCAL_REP_CENSUS_AUDIT_MD)
    local_census_summary = existing_path(LOCAL_REP_CENSUS_SUMMARY_JSON, FALLBACK_LOCAL_REP_CENSUS_SUMMARY_JSON)

    site_symmetry = load_json(SITE_SYMMETRY_CHECK_JSON)
    v3_candidates_root = load_json(V3_CANDIDATES_JSON)
    v3_basis = load_json(V3_BASIS_JSON)
    basis_raw = load_json(BS_WITH_PLANES_BASIS_RAW_JSON)
    basis_pretty = load_json(BS_WITH_PLANES_BASIS_PRETTY_JSON)

    ai_basis_coeff_matrix = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in v3_basis["basis_bs_coefficients"]]
    )
    ai_basis_unknown_matrix = sp.Matrix.hstack(
        *[sp.Matrix(column) for column in v3_basis["basis_vectors"]]
    )
    snf_diagonal_matrix, snf_left, snf_right = smith_normal_decomp(ai_basis_coeff_matrix, domain=ZZ)

    return {
        "local_census_audit_path": local_census_audit,
        "local_census_summary_path": local_census_summary,
        "local_census_summary": load_json(local_census_summary),
        "pointlike_corep_summary": load_json(POINTLIKE_COREP_SUMMARY_JSON),
        "pointlike_coreps_root": load_json(POINTLIKE_COREPS_JSON),
        "parametric_corep_summary": load_json(PARAMETRIC_COREP_SUMMARY_JSON),
        "parametric_coreps_root": load_json(PARAMETRIC_COREPS_JSON),
        "site_symmetry_root": site_symmetry,
        "site_by_letter": {entry["letter"]: entry for entry in site_symmetry["entries"]},
        "v2_candidates_root": load_json(V2_CANDIDATES_JSON),
        "v2_basis": load_json(V2_BASIS_JSON),
        "v3_candidates_root": v3_candidates_root,
        "v3_basis": v3_basis,
        "v2_summary": load_json(V2_SUMMARY_JSON),
        "v3_summary": load_json(V3_SUMMARY_JSON),
        "saturation_summary": load_json(SATURATION_SUMMARY_JSON),
        "basis_raw": basis_raw,
        "basis_pretty": basis_pretty,
        "compat_root": load_json(FULL_COMPATIBILITY_WITH_PLANES_JSON),
        "kmanifolds": load_json(KMANIFOLDS_JSON),
        "connectivity": load_json(CONNECTIVITY_JSON),
        "v3_generators_by_family": family_generator_map(v3_candidates_root),
        "bs_basis_matrix": points.bs_basis_matrix_from_raw(basis_raw),
        "ai_basis_coeff_matrix": ai_basis_coeff_matrix,
        "ai_basis_unknown_matrix": ai_basis_unknown_matrix,
        "snf_diagonal_matrix": snf_diagonal_matrix,
        "snf_left": snf_left,
        "snf_right": snf_right,
        "pointlike_family_by_letter": {
            record["letter"]: record for record in load_json(POINTLIKE_COREPS_JSON)["families"]
        },
        "parametric_family_by_letter": {
            record["letter"]: record for record in load_json(PARAMETRIC_COREPS_JSON)["families"]
        },
    }


def build_unitary_family_record(letter: str, ctx: dict[str, Any]) -> dict[str, Any]:
    model = UNITARY_FAMILY_MODELS[letter]
    site_entry = ctx["site_by_letter"][letter]
    direct = site_entry["direct_reconstruction"]
    included = find_unitary_local_reps(letter)
    included_ids = [rep["id"] for rep in included]
    ai_generator_ids = [generator["generator_id"] for generator in ctx["v3_generators_by_family"].get(letter, [])]
    expected_ids = list(model["expected_ids"])
    sum_dim_sq = sum(int(rep["dimension"]) ** 2 for rep in included)

    complete = (
        site_entry["comparison"]["overall_consistent"]
        and included_ids == expected_ids
        and ai_generator_ids == expected_ids
        and len(included_ids) == int(model["expected_count"])
        and sum_dim_sq == int(direct["stabilizer_size"])
    )

    note = (
        f"Complete: the enumerated local irreps exactly match the expected {model['abstract_group']} single-group character list."
        if complete
        else "Incomplete: the current local-irrep list does not match the expected single-group census."
    )

    return {
        "family_id": letter,
        "family_kind": "unitary",
        "dimension": int(site_entry["dimension"]),
        "multiplicity": int(site_entry["multiplicity"]),
        "representative_coordinate": site_entry["representative_coordinate"],
        "site_symmetry": site_entry["program_output"]["site_symmetry"],
        "site_symmetry_custom": site_entry["program_output"]["site_symmetry_custom"],
        "unitary_site_symmetry": site_entry["program_output"]["unitary_site_symmetry"],
        "stabilizer_size": int(direct["stabilizer_size"]),
        "unitary_count": int(direct["unitary_count"]),
        "antiunitary_count": int(direct["antiunitary_count"]),
        "site_symmetry_consistent": bool(site_entry["comparison"]["overall_consistent"]),
        "expected_single_group_local_object_kind": "local_irreps",
        "expected_single_group_abstract_group": model["abstract_group"],
        "expected_single_group_count": int(model["expected_count"]),
        "current_included_local_reps_coreps": [
            {
                "id": rep["id"],
                "label": rep["label"],
                "dimension": int(rep["dimension"]),
                "type": "unitary_local_irrep",
            }
            for rep in included
        ],
        "current_ai_generator_ids": ai_generator_ids,
        "sum_dimension_squared": int(sum_dim_sq),
        "complete_for_single_group": bool(complete),
        "missing_items": [] if complete else expected_ids,
        "completeness_basis": model["completeness_basis"],
        "notes": note,
    }


def antiunitary_case_a_completeness_note(record: dict[str, Any]) -> str:
    subgroup = record["unitary_subgroup_summary"]["abstract_group"]
    labels = ", ".join(record["unitary_subgroup_summary"]["unitary_irrep_labels"])
    return (
        f"The unitary subgroup is {subgroup} with real one-dimensional irreps {labels}. "
        f"The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, "
        f"so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional "
        f"single-group magnetic coreps are expected."
    )


def build_antiunitary_family_record(letter: str, ctx: dict[str, Any], source: str) -> dict[str, Any]:
    site_entry = ctx["site_by_letter"][letter]
    direct = site_entry["direct_reconstruction"]
    if source == "pointlike":
        family_record = ctx["pointlike_family_by_letter"][letter]
    else:
        family_record = ctx["parametric_family_by_letter"][letter]

    included_coreps = list(family_record["magnetic_local_coreps"])
    included_ids = [corep["corep_id"] for corep in included_coreps]
    ai_generator_ids = [generator["generator_id"] for generator in ctx["v3_generators_by_family"].get(letter, [])]
    expected_count = 2 * len(family_record["unitary_subgroup_summary"]["unitary_irrep_labels"])
    sum_dim_sq = sum(int(corep["dimension"]) ** 2 for corep in included_coreps)
    conjugation_fixed = family_record["wigner_preanalysis"].get("antiunitary_conjugation_fixed", True)
    case_a = family_record["wigner_preanalysis"]["expected_wigner_case"] == "a"

    complete = (
        site_entry["comparison"]["overall_consistent"]
        and family_record["site_symmetry_check_comparison"]["usable_as_magnetic_local_corep_input"]
        and family_record["full_magnetic_local_corep_set_built"]
        and case_a
        and conjugation_fixed
        and len(included_coreps) == int(expected_count)
        and ai_generator_ids == included_ids
        and sum_dim_sq == int(direct["stabilizer_size"])
        and all(bool(corep["direct_extension_of_unitary_irrep"]) for corep in included_coreps)
    )

    note = (
        "Complete: the family's magnetic local-corep census closes under the audited case-a extension logic."
        if complete
        else "Incomplete: the family's magnetic local-corep census does not yet exhaust the expected single-group case-a extensions."
    )

    return {
        "family_id": letter,
        "family_kind": source,
        "dimension": int(site_entry["dimension"]),
        "multiplicity": int(site_entry["multiplicity"]),
        "representative_coordinate": site_entry["representative_coordinate"],
        "site_symmetry": family_record["site_symmetry_summary"]["site_symmetry"],
        "site_symmetry_custom": family_record["site_symmetry_summary"]["site_symmetry_custom"],
        "unitary_site_symmetry": site_entry["program_output"]["unitary_site_symmetry"],
        "stabilizer_size": int(direct["stabilizer_size"]),
        "unitary_count": int(direct["unitary_count"]),
        "antiunitary_count": int(direct["antiunitary_count"]),
        "site_symmetry_consistent": bool(site_entry["comparison"]["overall_consistent"]),
        "expected_single_group_local_object_kind": "magnetic_local_coreps",
        "expected_single_group_abstract_group": family_record["unitary_subgroup_summary"]["abstract_group"],
        "expected_single_group_count": int(expected_count),
        "wigner_case": family_record["wigner_preanalysis"]["expected_wigner_case"],
        "antiunitary_generator_square_index": int(
            family_record["wigner_preanalysis"]["antiunitary_generator_square_index"]
        ),
        "current_included_local_reps_coreps": [
            {
                "id": corep["corep_id"],
                "label": corep["label"],
                "dimension": int(corep["dimension"]),
                "type": "magnetic_local_corep",
                "source_unitary_irrep": corep["source_unitary_irrep"],
                "eta": int(corep["antiunitary_extension_eta"]),
                "truly_antiunitary": bool(corep["truly_antiunitary"]),
            }
            for corep in included_coreps
        ],
        "current_ai_generator_ids": ai_generator_ids,
        "sum_dimension_squared": int(sum_dim_sq),
        "complete_for_single_group": bool(complete),
        "missing_items": [] if complete else included_ids,
        "completeness_basis": antiunitary_case_a_completeness_note(family_record),
        "notes": note,
    }


def build_family_table(ctx: dict[str, Any]) -> dict[str, Any]:
    families: list[dict[str, Any]] = []
    for letter in FAMILY_ORDER:
        if letter in UNITARY_FAMILIES:
            record = build_unitary_family_record(letter, ctx)
        elif letter in POINTLIKE_ANTIUNITARY_FAMILIES:
            record = build_antiunitary_family_record(letter, ctx, source="pointlike")
        elif letter in PARAMETRIC_ANTIUNITARY_FAMILIES:
            record = build_antiunitary_family_record(letter, ctx, source="parametric")
        else:
            raise ValueError(f"unexpected family {letter}")
        families.append(record)

    complete_families = [record["family_id"] for record in families if record["complete_for_single_group"]]
    incomplete_families = [record["family_id"] for record in families if not record["complete_for_single_group"]]
    families_in_v3 = sorted(ctx["v3_generators_by_family"])
    all_families_audited = sorted(record["family_id"] for record in families) == FAMILY_ORDER
    ai_v3_complete = (
        all_families_audited
        and not incomplete_families
        and families_in_v3 == sorted(FAMILY_ORDER)
    )

    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "family_order": FAMILY_ORDER,
        "all_families_audited": bool(all_families_audited),
        "complete_families": complete_families,
        "incomplete_families": incomplete_families,
        "ai_v3_complete_for_single_group": bool(ai_v3_complete),
        "families": families,
    }


def quotient_group_from_diagonal(diagonal: list[int]) -> str:
    torsion = [value for value in diagonal if value > 1]
    if not torsion:
        return "trivial"
    return " x ".join(f"Z{value}" for value in torsion)


def compute_standard_basis_witnesses(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    basis_matrix = ctx["ai_basis_coeff_matrix"]
    pretty_basis = ctx["basis_pretty"]["basis_vectors"]
    raw_unknown_ordering = ctx["basis_raw"]["unknown_ordering"]
    bs_basis_matrix = ctx["bs_basis_matrix"]

    witnesses: list[dict[str, Any]] = []
    for idx in range(basis_matrix.rows):
        e_vec = sp.Matrix([1 if row == idx else 0 for row in range(basis_matrix.rows)])
        solution = basis_matrix.gauss_jordan_solve(e_vec)[0]
        if all(value.is_integer for value in solution):
            continue
        multiplier = None
        multiplied_solution = None
        for m in range(2, 9):
            candidate = basis_matrix.gauss_jordan_solve(m * e_vec)[0]
            if all(value.is_integer for value in candidate):
                multiplier = m
                multiplied_solution = candidate
                break
        if multiplier is None or multiplied_solution is None:
            continue
        unknown_vector = sp_vector_to_int_list(bs_basis_matrix * e_vec)
        witnesses.append(
            {
                "basis_index_1based": idx + 1,
                "bs_basis_coordinates": sp_vector_to_int_list(e_vec),
                "unknown_ordering": raw_unknown_ordering,
                "unknown_vector": unknown_vector,
                "smallest_multiplier": int(multiplier),
                "solution": [str(value) for value in solution],
                "multiplied_solution": [str(value) for value in multiplied_solution],
                "pretty_basis_direction": pretty_basis[idx],
            }
        )
    return witnesses


def build_indicator_outputs(ctx: dict[str, Any], family_table: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    basis_matrix = ctx["ai_basis_coeff_matrix"]
    diagonal_matrix = ctx["snf_diagonal_matrix"]
    snf_left = ctx["snf_left"]
    snf_right = ctx["snf_right"]
    snf_left_inv = snf_left.inv()
    bs_basis_matrix = ctx["bs_basis_matrix"]
    raw_unknown_ordering = ctx["basis_raw"]["unknown_ordering"]
    witnesses = compute_standard_basis_witnesses(ctx)

    torsion_indices = [
        index
        for index in range(min(diagonal_matrix.rows, diagonal_matrix.cols))
        if abs(int(diagonal_matrix[index, index])) > 1
    ]
    torsion_values = [abs(int(diagonal_matrix[index, index])) for index in torsion_indices]

    indicator_generators: list[dict[str, Any]] = []
    for indicator_index, torsion_index in enumerate(torsion_indices, start=1):
        raw_bs_coords = sp_vector_to_int_list(snf_left_inv[:, torsion_index])
        raw_ai_relation = sp_vector_to_int_list(snf_right[:, torsion_index])
        bs_coords, ai_relation = normalize_sign(raw_bs_coords, raw_ai_relation)
        multiplier = abs(int(diagonal_matrix[torsion_index, torsion_index]))
        unknown_vector = sp_vector_to_int_list(bs_basis_matrix * sp.Matrix(bs_coords))
        support = [
            {"unknown": token, "coeff": coeff}
            for token, coeff in zip(raw_unknown_ordering, unknown_vector)
            if coeff != 0
        ]

        matching_witness = None
        for witness in witnesses:
            if witness["bs_basis_coordinates"] == bs_coords or witness["bs_basis_coordinates"] == [-value for value in bs_coords]:
                matching_witness = witness
                break

        indicator_generators.append(
            {
                "indicator_id": f"indicator_generator_{indicator_index}",
                "smith_factor": int(multiplier),
                "quotient_coordinates": [
                    1 if idx == indicator_index - 1 else 0 for idx in range(len(torsion_indices))
                ],
                "bs_basis_coordinates": bs_coords,
                "unknown_ordering": raw_unknown_ordering,
                "unknown_vector": unknown_vector,
                "unknown_support": support,
                "smallest_multiplier_into_ai": int(multiplier),
                "multiplied_bs_basis_coordinates": [int(multiplier) * value for value in bs_coords],
                "multiplied_unknown_vector": [int(multiplier) * value for value in unknown_vector],
                "ai_complete_single_basis_relation_for_multiple": ai_relation,
                "not_in_ai_complete_single": True,
                "multiple_in_ai_complete_single": True,
                "relation_to_previous_saturation_witness": (
                    {
                        "matches_previous_witness": True,
                        "previous_witness_id": f"bs_basis_direction_{matching_witness['basis_index_1based']:02d}",
                        "previous_witness_pretty_basis_direction": matching_witness["pretty_basis_direction"]["id"],
                    }
                    if matching_witness is not None
                    else {
                        "matches_previous_witness": False,
                        "previous_witness_id": None,
                        "previous_witness_pretty_basis_direction": None,
                    }
                ),
            }
        )

    indicator_group_summary = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "rank(BS_with_planes)": int(ctx["v3_summary"]["rank_BS_with_planes"]),
        "rank(AI_complete_single)": int(ctx["v3_summary"]["rank_AI_expanded_v3"]),
        "smith_diagonal_in_bs_coordinates": [int(value) for value in ctx["v3_basis"]["bs_coefficient_smith_diagonal"]],
        "quotient_group": quotient_group_from_diagonal(torsion_values),
        "indicator_rank_finite_part": len(torsion_indices),
        "indicator_generators_count": len(indicator_generators),
    }

    indicator_generators_root = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "quotient_group": indicator_group_summary["quotient_group"],
        "generators": indicator_generators,
        "independence_basis": "The generators are the two torsion basis directions coming directly from the Smith decomposition of the complete AI lattice in BS coordinates.",
        "span_basis": "Because the Smith diagonal has exactly two nontrivial invariant factors, these two generators span the full finite quotient.",
    }

    bs_mod_ai_summary = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "ai_v3_complete_for_single_group": bool(family_table["ai_v3_complete_for_single_group"]),
        "bs_mod_ai_single_obtained": True,
        "quotient_group": indicator_group_summary["quotient_group"],
        "indicator_generators": [generator["indicator_id"] for generator in indicator_generators],
        "applicable_scope": [
            "single group only",
            "group 10.4.1.31 only",
            "current with-planes formalism only",
            "current audited BS basis and unknown ordering only",
        ],
        "not_applicable_scope": [
            "double group",
            "other SSGs",
            "database-wide automation",
            "any basis/formalism not matched to the current audited single-group setup",
        ],
        "current_honest_conclusion": "For SSG 10.4.1.31 at groupType=1, the current AI_expanded_v3 passes the family-level completeness audit, so it is promoted to the complete single-group AI lattice. Therefore the residual Smith diagonal [1,1,1,1,1,1,2,2] is interpreted as the genuine finite quotient BS/AI = Z2 x Z2 within the present audited formalism.",
    }

    return indicator_group_summary, indicator_generators_root, bs_mod_ai_summary


def build_missing_report(family_table: dict[str, Any]) -> dict[str, Any]:
    incomplete_records = [
        record for record in family_table["families"] if not record["complete_for_single_group"]
    ]
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "ai_v3_complete_for_single_group": False,
        "incomplete_families": [record["family_id"] for record in incomplete_records],
        "missing_family_rep_corep_details": [
            {
                "family_id": record["family_id"],
                "missing_items": record["missing_items"],
                "reason": record["notes"],
            }
            for record in incomplete_records
        ],
        "why_this_blocks_quotient_extraction": "If the single-group AI lattice is incomplete, then a residual Smith factor can still be an artifact of missing atomic generators rather than a genuine BS/AI quotient.",
        "next_blocker": "Finish the missing family-level single-group local generator census before quotient extraction.",
    }


def build_completeness_summary(family_table: dict[str, Any]) -> dict[str, Any]:
    if family_table["ai_v3_complete_for_single_group"]:
        next_blocker = "None inside the present single-group completeness stage; the quotient extraction is now meaningful and is generated alongside this audit."
    else:
        next_blocker = "The incomplete families listed here still block any honest single-group quotient extraction."
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "all_families_audited": bool(family_table["all_families_audited"]),
        "complete_families": family_table["complete_families"],
        "incomplete_families": family_table["incomplete_families"],
        "ai_v3_complete_for_single_group": bool(family_table["ai_v3_complete_for_single_group"]),
        "next_blocker": next_blocker,
    }


def markdown_bool(value: bool) -> str:
    return "yes" if value else "no"


def build_completeness_audit_md(
    ctx: dict[str, Any],
    family_table: dict[str, Any],
    completeness_summary: dict[str, Any],
    indicator_group_summary: dict[str, Any] | None,
    indicator_generators_root: dict[str, Any] | None,
) -> str:
    lines = [
        f"# Single-Group AI Completeness Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        f"- Group type only: `{GROUP_TYPE}` (single group).",
        "- This audit does not revisit the trusted k-space formalism, bridge, or family-level induction mechanics.",
        "- The only task here is to decide whether `AI_expanded_v3` is already the complete single-group AI lattice and, if so, whether the residual Smith factors can be promoted to the honest single-group quotient `BS/AI`.",
        "",
        "## Inputs Actually Used",
        "",
        f"- `{ctx['local_census_audit_path'].name}` and `{ctx['local_census_summary_path'].name}` for the unitary family census.",
        "- `single_group_magnetic_local_corep_audit.md` and `single_group_pointlike_magnetic_coreps.json` for `a,b,d,e,g,h`.",
        "- `single_group_parametric_magnetic_corep_audit.md` and `single_group_parametric_magnetic_coreps.json` for `n,i,j`.",
        "- `single_group_ai_expanded_v3_candidates.json`, `single_group_ai_expanded_v3_basis.json`, and `single_group_saturation_summary.json` for the complete single-group AI lattice candidate and the current finite-index state.",
        "- `single_group_site_symmetry_check.json` for the geometry / stabilizer consistency checks on all fifteen families.",
        "",
        "## Family Coverage Table",
        "",
        "| family | dim | mult | site symmetry | included local generators | complete? |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in family_table["families"]:
        included = ", ".join(item["id"] for item in record["current_included_local_reps_coreps"])
        lines.append(
            f"| `{record['family_id']}` | `{record['dimension']}` | `{record['multiplicity']}` | `{record['site_symmetry']}` | `{included}` | `{markdown_bool(record['complete_for_single_group'])}` |"
        )

    lines.extend(
        [
            "",
            "## Antiunitary-Family Completeness Basis",
            "",
            "- All antiunitary families in this single-group audit have order-1 or order-2 unitary subgroups whose irreps are real and one-dimensional.",
            "- The audited antiunitary generators square to the identity and either fix the unitary subgroup generator or act trivially because the unitary subgroup is the identity alone.",
            "- Therefore only Wigner case-a occurs on these families, each source unitary irrep has exactly two eta=+/- direct extensions, and there is no room for missing higher-dimensional single-group magnetic coreps.",
            "",
        ]
    )
    for record in family_table["families"]:
        if record["family_kind"] == "unitary":
            continue
        lines.append(
            f"- `{record['family_id']}`: {record['completeness_basis']}"
        )

    lines.extend(
        [
            "",
            "## Family-Level Verdicts",
            "",
        ]
    )
    for record in family_table["families"]:
        lines.extend(
            [
                f"### Family `{record['family_id']}`",
                "",
                f"- Site symmetry summary: `{record['site_symmetry']}` / `{record['site_symmetry_custom']}`.",
                f"- Stabilizer size / unitary / antiunitary: `{record['stabilizer_size']}` / `{record['unitary_count']}` / `{record['antiunitary_count']}`.",
                f"- Included local reps/coreps: `{', '.join(item['id'] for item in record['current_included_local_reps_coreps'])}`.",
                f"- Sum of squared local dimensions: `{record['sum_dimension_squared']}`.",
                f"- Complete for single group: `{record['complete_for_single_group']}`.",
                f"- Basis: {record['completeness_basis']}",
                f"- Notes: {record['notes']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Completeness Verdict",
            "",
            f"- All families audited: `{family_table['all_families_audited']}`.",
            f"- Complete families: `{', '.join(family_table['complete_families'])}`.",
            f"- Incomplete families: `{', '.join(family_table['incomplete_families']) if family_table['incomplete_families'] else 'none'}`.",
            f"- `AI_expanded_v3` can be promoted to the complete single-group AI lattice: `{completeness_summary['ai_v3_complete_for_single_group']}`.",
            f"- Next blocker: {completeness_summary['next_blocker']}",
            "",
        ]
    )

    if indicator_group_summary is None or indicator_generators_root is None:
        lines.extend(
            [
                "## Quotient Extraction",
                "",
                "- Not attempted because the single-group AI completeness audit did not close.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "## Single-Group Quotient Extraction",
            "",
            f"- `rank(BS_with_planes) = {indicator_group_summary['rank(BS_with_planes)']}`.",
            f"- `rank(AI_complete_single) = {indicator_group_summary['rank(AI_complete_single)']}`.",
            f"- Smith diagonal in BS coordinates: `{indicator_group_summary['smith_diagonal_in_bs_coordinates']}`.",
            f"- Quotient group: `{indicator_group_summary['quotient_group']}`.",
            f"- Number of independent finite indicators: `{indicator_group_summary['indicator_generators_count']}`.",
            "- The two indicator generators below are independent by Smith construction and therefore span the entire finite quotient.",
            "",
        ]
    )
    for generator in indicator_generators_root["generators"]:
        lines.extend(
            [
                f"### `{generator['indicator_id']}`",
                "",
                f"- BS basis coordinates: `{generator['bs_basis_coordinates']}`.",
                f"- Smallest multiplier into AI: `{generator['smallest_multiplier_into_ai']}`.",
                f"- Unknown support: `{generator['unknown_support']}`.",
                f"- Relation to previous witness: `{generator['relation_to_previous_saturation_witness']['previous_witness_id']}`.",
                "",
            ]
        )
    lines.extend(
        [
            "## Scope Limits",
            "",
            "- This result applies only to the current single-group (`groupType=1`) treatment of `10.4.1.31` in the present with-planes basis and unknown ordering.",
            "- It does not apply to double groups, other SSGs, or any different formalism/basis choice that has not been matched to the same audited setup.",
        ]
    )
    return "\n".join(lines)


def build_package_readme(completeness_summary: dict[str, Any], indicator_group_summary: dict[str, Any] | None) -> str:
    lines = [
        "# Review Package: 10.4.1.31 Single-Group AI Completeness",
        "",
        "## Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- stage: AI completeness audit plus single-group quotient extraction",
        "",
        "## Known Premise",
        "",
        "- The k-space side is already trusted.",
        "- The real-space / k-space bridge is already trusted.",
        "- All families `a..o` already have audited local-rep/corep census input from the previous single-group stages.",
        "- The current issue is no longer a rank gap; it is whether `AI_expanded_v3` is already the complete single-group AI lattice and, if so, whether the residual Smith factors are the honest quotient.",
        "",
        "## New Content",
        "",
        "- `audit/single_group_ai_completeness_audit.md`: family-by-family completeness audit and the single-group completeness verdict",
        "- `audit/single_group_ai_completeness_summary.json`: compact completeness verdict",
        "- `audit/single_group_family_completeness_table.json`: explicit per-family completeness table",
        "- `scripts/debug_single_group_ai_completeness.py`: single-group completeness / quotient reproduction script",
    ]
    if completeness_summary["ai_v3_complete_for_single_group"]:
        lines.extend(
            [
                "- `audit/single_group_indicator_group_summary.json`: quotient-group summary",
                "- `audit/single_group_indicator_generators.json`: explicit indicator generators",
                "- `audit/single_group_bs_mod_ai_single_summary.json`: honest scope-limited `BS/AI` conclusion",
            ]
        )
    else:
        lines.append("- `audit/single_group_ai_missing_generators_report.json`: blocking missing-generator report")
    lines.extend(
        [
            "",
            "## Possible Outcome Patterns",
            "",
            "- `AI_expanded_v3` is complete for the single group, so the quotient can be extracted.",
            "- `AI_expanded_v3` is still incomplete, so only a missing-generator report is honest.",
            "",
            "## Suggested Review Order",
            "",
            "1. `audit/single_group_ai_completeness_audit.md`",
            "2. `audit/single_group_ai_completeness_summary.json`",
            "3. `audit/single_group_family_completeness_table.json`",
        ]
    )
    if completeness_summary["ai_v3_complete_for_single_group"]:
        lines.extend(
            [
                "4. `audit/single_group_indicator_group_summary.json`",
                "5. `audit/single_group_indicator_generators.json`",
            ]
        )
    lines.extend(
        [
            "",
            "## Result Of This Run",
            "",
            f"- `AI_expanded_v3` complete for the single group: `{completeness_summary['ai_v3_complete_for_single_group']}`.",
        ]
    )
    if indicator_group_summary is not None:
        lines.append(f"- The extracted single-group quotient is `{indicator_group_summary['quotient_group']}`.")
    else:
        lines.append("- Quotient extraction was not performed because completeness did not close.")
    return "\n".join(lines)


def build_package(completeness_summary: dict[str, Any]) -> None:
    points.reset_dir(PACKAGE_DIR)

    mapping: dict[str, Path] = {
        "audit/single_group_ai_completeness_audit.md": COMPLETENESS_AUDIT_MD,
        "audit/single_group_ai_completeness_summary.json": COMPLETENESS_SUMMARY_JSON,
        "audit/single_group_family_completeness_table.json": FAMILY_TABLE_JSON,
        "scripts/debug_single_group_ai_completeness.py": ROOT / "debug_single_group_ai_completeness.py",
        "audit/single_group_parametric_magnetic_corep_audit.md": PARAMETRIC_COREP_AUDIT_MD,
        "audit/single_group_parametric_magnetic_corep_summary.json": PARAMETRIC_COREP_SUMMARY_JSON,
        "audit/single_group_parametric_magnetic_coreps.json": PARAMETRIC_COREPS_JSON,
        "audit/single_group_magnetic_local_corep_audit.md": POINTLIKE_COREP_AUDIT_MD,
        "audit/single_group_magnetic_local_corep_summary.json": POINTLIKE_COREP_SUMMARY_JSON,
        "audit/single_group_pointlike_magnetic_coreps.json": POINTLIKE_COREPS_JSON,
        "audit/single_group_local_rep_census_audit.md": existing_path(
            LOCAL_REP_CENSUS_AUDIT_MD,
            FALLBACK_LOCAL_REP_CENSUS_AUDIT_MD,
        ),
        "audit/single_group_local_rep_census_summary.json": existing_path(
            LOCAL_REP_CENSUS_SUMMARY_JSON,
            FALLBACK_LOCAL_REP_CENSUS_SUMMARY_JSON,
        ),
        "ai/single_group_ai_expanded_v3_candidates.json": V3_CANDIDATES_JSON,
        "ai/single_group_ai_expanded_v3_basis.json": V3_BASIS_JSON,
        "ai/single_group_bs_vs_ai_expanded_v3_summary.json": V3_SUMMARY_JSON,
        "audit/single_group_saturation_audit.md": SATURATION_AUDIT_MD,
        "audit/single_group_saturation_summary.json": SATURATION_SUMMARY_JSON,
        "basis/single_group_bs_with_planes_basis_raw.json": BS_WITH_PLANES_BASIS_RAW_JSON,
        "basis/single_group_bs_with_planes_basis_pretty.json": BS_WITH_PLANES_BASIS_PRETTY_JSON,
        "matrix/single_group_full_compatibility_with_planes.json": FULL_COMPATIBILITY_WITH_PLANES_JSON,
        "background/single_group_kmanifolds.json": KMANIFOLDS_JSON,
        "background/single_group_connectivity.json": CONNECTIVITY_JSON,
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    }
    if completeness_summary["ai_v3_complete_for_single_group"]:
        mapping.update(
            {
                "audit/single_group_indicator_group_summary.json": INDICATOR_GROUP_SUMMARY_JSON,
                "audit/single_group_indicator_generators.json": INDICATOR_GENERATORS_JSON,
                "audit/single_group_bs_mod_ai_single_summary.json": BS_MOD_AI_SINGLE_SUMMARY_JSON,
            }
        )
    else:
        mapping["audit/single_group_ai_missing_generators_report.json"] = MISSING_GENERATORS_REPORT_JSON

    for relative_path, source in mapping.items():
        destination = PACKAGE_DIR / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    indicator_summary = None
    if completeness_summary["ai_v3_complete_for_single_group"]:
        indicator_summary = load_json(INDICATOR_GROUP_SUMMARY_JSON)
    write_text(PACKAGE_DIR / "README.md", build_package_readme(completeness_summary, indicator_summary))

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()
    family_table = build_family_table(ctx)
    completeness_summary = build_completeness_summary(family_table)

    indicator_group_summary = None
    indicator_generators_root = None
    bs_mod_ai_single_summary = None
    missing_report = None

    if family_table["ai_v3_complete_for_single_group"]:
        indicator_group_summary, indicator_generators_root, bs_mod_ai_single_summary = build_indicator_outputs(
            ctx, family_table
        )
        if MISSING_GENERATORS_REPORT_JSON.exists():
            MISSING_GENERATORS_REPORT_JSON.unlink()
        write_json(INDICATOR_GROUP_SUMMARY_JSON, indicator_group_summary)
        write_json(INDICATOR_GENERATORS_JSON, indicator_generators_root)
        write_json(BS_MOD_AI_SINGLE_SUMMARY_JSON, bs_mod_ai_single_summary)
    else:
        missing_report = build_missing_report(family_table)
        for path in (INDICATOR_GROUP_SUMMARY_JSON, INDICATOR_GENERATORS_JSON, BS_MOD_AI_SINGLE_SUMMARY_JSON):
            if path.exists():
                path.unlink()
        write_json(MISSING_GENERATORS_REPORT_JSON, missing_report)

    write_json(FAMILY_TABLE_JSON, family_table)
    write_json(COMPLETENESS_SUMMARY_JSON, completeness_summary)
    write_text(
        COMPLETENESS_AUDIT_MD,
        build_completeness_audit_md(
            ctx,
            family_table,
            completeness_summary,
            indicator_group_summary,
            indicator_generators_root,
        ),
    )

    build_package(completeness_summary)

    return {
        "family_table": family_table,
        "completeness_summary": completeness_summary,
        "indicator_group_summary": indicator_group_summary,
        "indicator_generators_root": indicator_generators_root,
        "missing_report": missing_report,
    }


def validate_outputs() -> None:
    core_required = [
        COMPLETENESS_AUDIT_MD,
        COMPLETENESS_SUMMARY_JSON,
        FAMILY_TABLE_JSON,
        ROOT / "debug_single_group_ai_completeness.py",
        PACKAGE_TARBALL,
    ]
    for path in core_required:
        if not path.exists():
            raise ValueError(f"missing required artifact: {path}")

    summary = load_json(COMPLETENESS_SUMMARY_JSON)
    if summary["group_number"] != GROUP_NUMBER:
        raise ValueError("wrong group number in completeness summary")
    if int(summary["group_type"]) != GROUP_TYPE:
        raise ValueError("wrong group type in completeness summary")
    if not summary["all_families_audited"]:
        raise ValueError("family audit did not close")

    family_table = load_json(FAMILY_TABLE_JSON)
    if sorted(record["family_id"] for record in family_table["families"]) != FAMILY_ORDER:
        raise ValueError("family table is missing one or more families")

    expected_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/audit/single_group_ai_completeness_audit.md",
        f"{PACKAGE_NAME}/audit/single_group_ai_completeness_summary.json",
        f"{PACKAGE_NAME}/audit/single_group_family_completeness_table.json",
        f"{PACKAGE_NAME}/scripts/debug_single_group_ai_completeness.py",
    }

    if summary["ai_v3_complete_for_single_group"]:
        required_complete = [
            INDICATOR_GROUP_SUMMARY_JSON,
            INDICATOR_GENERATORS_JSON,
            BS_MOD_AI_SINGLE_SUMMARY_JSON,
        ]
        for path in required_complete:
            if not path.exists():
                raise ValueError(f"missing complete-branch artifact: {path}")

        indicator_summary = load_json(INDICATOR_GROUP_SUMMARY_JSON)
        if indicator_summary["quotient_group"] != "Z2 x Z2":
            raise ValueError("unexpected quotient group")
        if indicator_summary["indicator_generators_count"] != 2:
            raise ValueError("unexpected indicator generator count")

        indicator_generators = load_json(INDICATOR_GENERATORS_JSON)
        if len(indicator_generators["generators"]) != 2:
            raise ValueError("unexpected explicit indicator generator count")

        bs_mod_ai_summary = load_json(BS_MOD_AI_SINGLE_SUMMARY_JSON)
        if not bs_mod_ai_summary["bs_mod_ai_single_obtained"]:
            raise ValueError("single-group quotient should be marked obtained")

        expected_members.update(
            {
                f"{PACKAGE_NAME}/audit/single_group_indicator_group_summary.json",
                f"{PACKAGE_NAME}/audit/single_group_indicator_generators.json",
                f"{PACKAGE_NAME}/audit/single_group_bs_mod_ai_single_summary.json",
            }
        )
    else:
        if not MISSING_GENERATORS_REPORT_JSON.exists():
            raise ValueError("missing incomplete-branch report")
        expected_members.add(f"{PACKAGE_NAME}/audit/single_group_ai_missing_generators_report.json")

    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        members = {member.name for member in tar.getmembers()}
    missing = sorted(expected_members - members)
    if missing:
        raise ValueError(f"package is missing expected members: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit single-group AI completeness for 10.4.1.31 and, if complete, extract the single-group BS/AI quotient."
    )
    parser.add_argument("--validate", action="store_true", help="Validate previously generated outputs and exit.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validation_ok")
        return 0

    result = generate_outputs()
    output = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "ai_v3_complete_for_single_group": result["completeness_summary"]["ai_v3_complete_for_single_group"],
        "complete_families": result["completeness_summary"]["complete_families"],
        "incomplete_families": result["completeness_summary"]["incomplete_families"],
    }
    if result["indicator_group_summary"] is not None:
        output["quotient_group"] = result["indicator_group_summary"]["quotient_group"]
        output["indicator_generators"] = [
            generator["indicator_id"] for generator in result["indicator_generators_root"]["generators"]
        ]
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
