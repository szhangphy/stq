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


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 2

FAMILY_ORDER = list("abcdefghijklmno")
POINTLIKE_FAMILIES = list("abcdefgh")
PARAMETRIC_FAMILIES = ["i", "j", "k", "l", "m", "n", "o"]

REVIEW_PARAMETRIC = ROOT / "review_package_10.4.1.31_double_parametric_ai"
REVIEW_SINGLE = ROOT / "review_package_10.4.1.31_single_indicator"

AI_COMPLETENESS_AUDIT_MD = ROOT / "double_group_ai_completeness_audit_10.4.1.31.md"
AI_COMPLETENESS_SUMMARY_JSON = ROOT / "double_group_ai_completeness_summary_10.4.1.31.json"
FAMILY_COMPLETENESS_JSON = ROOT / "double_group_family_completeness_table_10.4.1.31.json"
INDICATOR_GROUP_SUMMARY_JSON = ROOT / "double_group_indicator_group_summary_10.4.1.31.json"
INDICATOR_GENERATORS_JSON = ROOT / "double_group_indicator_generators_10.4.1.31.json"
BS_MOD_AI_SUMMARY_JSON = ROOT / "double_group_bs_mod_ai_summary_10.4.1.31.json"
MISSING_GENERATORS_JSON = ROOT / "double_group_ai_missing_generators_report_10.4.1.31.json"

PACKAGE_NAME = "review_package_10.4.1.31_double_indicator"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TAR = ROOT / f"{PACKAGE_NAME}.tar.gz"

REQUIRED_NEW_FILES = [
    AI_COMPLETENESS_AUDIT_MD,
    AI_COMPLETENESS_SUMMARY_JSON,
    FAMILY_COMPLETENESS_JSON,
    ROOT / "debug_double_group_ai_completeness_10.4.1.31.py",
    PACKAGE_TAR,
]

COMPLETE_MODELS: dict[str, dict[str, Any]] = {
    "c": {
        "family_class": "point-like",
        "expected_count": 4,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "2/m",
        "basis": [
            "Pure-unitary family with full unitary stabilizer `2/m`.",
            "The projective character is fixed by two choices: C2 eigenvalue `+i/-i` and inversion parity `g/u`.",
            "Those two binary choices give exactly four one-dimensional double-valued projective irreps and the current census contains all four.",
        ],
    },
    "f": {
        "family_class": "point-like",
        "expected_count": 4,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "2/m",
        "basis": [
            "Same pure-unitary `2/m` site symmetry as family `c`.",
            "Projective completeness is fixed by the same `C2=+i/-i` and inversion `g/u` choices.",
            "Hence the complete local set has exactly four one-dimensional projective irreps, all present in the census.",
        ],
    },
    "a": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'/m",
        "expected_wigner_case": "c",
        "basis": [
            "The unitary subgroup is projective order-2 with exactly two conjugate unitary irreps `+i/-i`.",
            "The antiunitary generator fixes the unitary generator and squares to the identity, so Wigner extension pairs those conjugate unitary irreps into one irreducible case-c magnetic corep.",
            "No additional case-a or higher-dimensional magnetic corep exists because there is no extra unitary irrep left to extend.",
        ],
    },
    "b": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'/m",
        "expected_wigner_case": "c",
        "basis": [
            "Same `2'/m` antiunitary stabilizer as family `a`.",
            "The only unitary projective irreps are the conjugate pair `+i/-i`.",
            "Therefore the complete double local set is a single Wigner-case-c pair, already present in the census.",
        ],
    },
    "d": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'/m'",
        "expected_wigner_case": "c",
        "basis": [
            "The unitary subgroup is projective order-2 with generator square factor `-1`, so its only one-dimensional projective irreps are `+i/-i`.",
            "The antiunitary action fixes that unitary generator, so the conjugate pair must combine into one irreducible case-c magnetic corep.",
            "That single case-c pair is therefore the full local-object set.",
        ],
    },
    "e": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'/m'",
        "expected_wigner_case": "c",
        "basis": [
            "Same `2'/m'` antiunitary stabilizer as family `d`.",
            "The projective unitary subgroup again has only the conjugate pair `+i/-i`.",
            "Hence the census is complete once the single case-c magnetic corep is present, which it is.",
        ],
    },
    "g": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2/m'",
        "expected_wigner_case": "c",
        "basis": [
            "The unitary subgroup is projective order-2 with only the conjugate `+i/-i` pair.",
            "The antiunitary generator fixes the unitary generator, so Wigner completeness again produces a single irreducible case-c corep.",
            "No further double local object is available beyond that pair.",
        ],
    },
    "h": {
        "family_class": "point-like",
        "expected_count": 1,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2/m'",
        "expected_wigner_case": "c",
        "basis": [
            "Same `2/m'` antiunitary stabilizer as family `g`.",
            "The only unitary projective irreps are the conjugate pair `+i/-i`.",
            "That pair gives exactly one case-c magnetic corep, which is already present.",
        ],
    },
    "o": {
        "family_class": "parametric",
        "expected_count": 1,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "1",
        "basis": [
            "The site stabilizer is trivial.",
            "A trivial stabilizer has exactly one one-dimensional projective local irrep.",
            "The current singleton census is therefore complete.",
        ],
    },
    "m": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "m",
        "basis": [
            "The pure-unitary stabilizer is order 2 with double-group square factor `-1` on its generator.",
            "A one-dimensional projective character must satisfy `chi(g)^2 = -1`, so the only possibilities are `+i` and `-i`.",
            "Those two characters exhaust the projective local-irrep set.",
        ],
    },
    "k": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "2",
        "basis": [
            "The pure-unitary stabilizer is order 2 with generator square factor `-1`.",
            "Hence the complete one-dimensional projective spectrum is just the two generator eigenvalues `+i/-i`.",
            "Both are present in the current census, so the family is complete.",
        ],
    },
    "l": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "projective_local_irrep",
        "site_symmetry": "2",
        "basis": [
            "Same order-2 pure-unitary stabilizer as family `k`.",
            "The only projective one-dimensional possibilities are again `+i/-i`.",
            "Both are included, so the family-level local-object census is complete.",
        ],
    },
    "i": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'",
        "expected_wigner_case": "a",
        "basis": [
            "The unitary subgroup is trivial, so there is only one unitary irrep to extend.",
            "The antiunitary generator squares to the identity with double-group factor `+1`, so Wigner completeness gives the eta=`+/-` case-a pair.",
            "There is no room for an additional higher-dimensional or projective magnetic corep in this stabilizer.",
        ],
    },
    "j": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "2'",
        "expected_wigner_case": "a",
        "basis": [
            "Same `2'` antiunitary stabilizer as family `i`.",
            "With trivial unitary subgroup and antiunitary square `+1`, the full local set is exactly the eta=`+/-` case-a pair.",
            "The census already contains that full pair.",
        ],
    },
    "n": {
        "family_class": "parametric",
        "expected_count": 2,
        "expected_kind": "magnetic_local_corep",
        "site_symmetry": "m'",
        "expected_wigner_case": "a",
        "basis": [
            "The unitary subgroup is again trivial.",
            "The antiunitary generator squares to the identity with double-group factor `+1`, so the complete magnetic extension is the eta=`+/-` case-a pair.",
            "No missing higher-dimensional local corep remains after that pair is included.",
        ],
    },
}


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


def basis_matrix_from_json(basis_json: dict[str, Any]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in basis_json["basis_vectors"]])


def support_from_vector(vector: list[int], unknown_ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown, "coeff": int(coeff)}
        for unknown, coeff in zip(unknown_ordering, vector)
        if coeff
    ]


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    pieces: list[str] = []
    if free_rank == 1:
        pieces.append("Z")
    elif free_rank > 1:
        pieces.append(f"Z^{free_rank}")
    for value in finite_part:
        pieces.append(f"Z{value}")
    return " x ".join(pieces) if pieces else "0"


def family_kind(letter: str) -> str:
    if letter in POINTLIKE_FAMILIES:
        return "point-like"
    if letter in PARAMETRIC_FAMILIES:
        return "parametric"
    raise KeyError(letter)


def build_context() -> dict[str, Any]:
    pointlike_coreps = load_json(REVIEW_PARAMETRIC / "double_group_pointlike_coreps_10.4.1.31.json")
    parametric_coreps = load_json(REVIEW_PARAMETRIC / "double_group_parametric_coreps_10.4.1.31.json")
    ai_v2_candidates = load_json(REVIEW_PARAMETRIC / "double_group_ai_v2_candidates_10.4.1.31.json")
    ai_v2_basis = load_json(REVIEW_PARAMETRIC / "double_group_ai_v2_basis_10.4.1.31.json")
    bs_vs_ai_v2 = load_json(REVIEW_PARAMETRIC / "double_group_bs_vs_ai_v2_summary_10.4.1.31.json")
    bs_summary = load_json(REVIEW_PARAMETRIC / "double_group_bs_summary_10.4.1.31.json")
    bs_raw = load_json(REVIEW_PARAMETRIC / "double_group_bs_basis_raw_10.4.1.31.json")
    bs_pretty = load_json(REVIEW_PARAMETRIC / "double_group_bs_basis_pretty_10.4.1.31.json")

    pointlike_map = {record["letter"]: record for record in pointlike_coreps["families"]}
    parametric_map = {record["letter"]: record for record in parametric_coreps["families"]}
    family_records: dict[str, dict[str, Any]] = {}
    for letter in FAMILY_ORDER:
        if letter in pointlike_map:
            family_records[letter] = pointlike_map[letter]
        elif letter in parametric_map:
            family_records[letter] = parametric_map[letter]
        else:
            raise ValueError(f"missing family {letter} from the audited double-group census")

    ai_v2_matrix = sp.Matrix.hstack(*[sp.Matrix(column) for column in ai_v2_basis["basis_bs_coefficients"]])
    bs_raw_basis = basis_matrix_from_json(bs_raw)

    return {
        "pointlike_coreps": pointlike_coreps,
        "parametric_coreps": parametric_coreps,
        "family_records": family_records,
        "ai_v2_candidates": ai_v2_candidates,
        "ai_v2_basis": ai_v2_basis,
        "bs_vs_ai_v2": bs_vs_ai_v2,
        "bs_summary": bs_summary,
        "bs_raw": bs_raw,
        "bs_pretty": bs_pretty,
        "ai_v2_basis_matrix": ai_v2_matrix,
        "bs_raw_basis_matrix": bs_raw_basis,
        "unknown_ordering": bs_summary["final_unknown_ordering"],
    }


def build_family_completeness_entry(letter: str, record: dict[str, Any]) -> dict[str, Any]:
    model = COMPLETE_MODELS[letter]
    local_objects = list(record["local_objects"])
    actual_count = len(local_objects)
    expected_count = int(model["expected_count"])
    expected_kind = model["expected_kind"]
    kinds_ok = all(obj["double_group_local_object_kind"] == expected_kind for obj in local_objects)
    feasibility_ok = bool(record["double_group_local_corep_feasibility"]["can_build_full_local_object_set"])
    set_built_ok = bool(record["full_local_object_set_built"])
    wigner_ok = True
    expected_wigner_case = model.get("expected_wigner_case")
    if expected_wigner_case is not None:
        wigner_ok = all(obj.get("wigner_case") == expected_wigner_case for obj in local_objects)

    complete = (
        actual_count == expected_count
        and kinds_ok
        and feasibility_ok
        and set_built_ok
        and wigner_ok
    )

    current_objects = [
        {
            "id": obj["id"],
            "dimension": int(obj["dimension"]),
            "kind": obj["double_group_local_object_kind"],
            "wigner_case": obj.get("wigner_case"),
            "truly_antiunitary": bool(obj["truly_antiunitary"]),
        }
        for obj in local_objects
    ]

    notes = []
    if actual_count != expected_count:
        notes.append(f"expected {expected_count} local objects but found {actual_count}")
    if not kinds_ok:
        notes.append(f"not all objects have expected kind `{expected_kind}`")
    if not feasibility_ok:
        notes.append("the family-level feasibility flag is still false")
    if not set_built_ok:
        notes.append("the family record does not mark the full local set as built")
    if expected_wigner_case is not None and not wigner_ok:
        notes.append(f"the Wigner-case labels do not match the expected `{expected_wigner_case}` classification")
    if not notes:
        notes.append("Current local-object census matches the mathematically expected double-group object set for this family.")

    return {
        "family_id": letter,
        "family_class": model["family_class"],
        "multiplicity": int(record["multiplicity"]),
        "site_symmetry_summary": {
            "site_symmetry": record["site_symmetry_summary"]["site_symmetry"],
            "unitary_subgroup_summary": record["unitary_subgroup_summary"],
        },
        "current_included_double_local_objects": current_objects,
        "expected_local_object_count": expected_count,
        "expected_kind": expected_kind,
        "completeness_status": "complete" if complete else "incomplete",
        "complete": complete,
        "missing_objects": [] if complete else ["undetermined missing double local object(s) within this family"],
        "completeness_basis": model["basis"],
        "notes": notes,
    }


def build_family_table(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        build_family_completeness_entry(letter, ctx["family_records"][letter])
        for letter in FAMILY_ORDER
    ]


def build_completeness_summary(table: list[dict[str, Any]]) -> dict[str, Any]:
    complete_families = [entry["family_id"] for entry in table if entry["complete"]]
    incomplete_families = [entry["family_id"] for entry in table if not entry["complete"]]
    ai_complete = len(incomplete_families) == 0 and len(complete_families) == len(FAMILY_ORDER)
    next_blocker = (
        "No remaining family-level AI blocker inside the current 10.4.1.31 / groupType=2 scope. The next task is purely quotient interpretation."
        if ai_complete
        else "At least one family-level double local-object census is still incomplete, so quotient extraction must stop until those missing generators are resolved."
    )
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "all_families_audited": len(table) == len(FAMILY_ORDER),
        "complete_families": complete_families,
        "incomplete_families": incomplete_families,
        "ai_v2_complete_for_double_group": ai_complete,
        "next_blocker": next_blocker,
    }


def compute_indicator_data(ctx: dict[str, Any]) -> dict[str, Any]:
    A = ctx["ai_v2_basis_matrix"]
    B = ctx["bs_raw_basis_matrix"]
    D, S, T = smith_normal_decomp(A, domain=ZZ)
    if S * A * T != D:
        raise ValueError("Smith decomposition consistency check failed")
    if int(ctx["bs_summary"]["nullity"]) != int(B.cols):
        raise ValueError("BS summary nullity does not match the explicit BS basis size")

    Sinv = S.inv()
    rank = int(A.rank())
    invariant_factors = [int(D[i, i]) for i in range(rank)]
    free_rank = int(B.cols - rank)
    finite_part = [value for value in invariant_factors if value > 1]

    quotient_generators = []
    for slot in range(B.cols):
        invariant = int(D[slot, slot]) if slot < rank else 0
        if slot < rank and invariant == 1:
            continue
        kind = "finite" if slot < rank else "free"
        bs_coords = [int(Sinv[row, slot]) for row in range(Sinv.rows)]
        unknown_vector = [int(value) for value in list(B * sp.Matrix(bs_coords))]
        generator = {
            "id": (
                f"double_indicator_generator_finite_{len([g for g in quotient_generators if g.get('kind') == 'finite']) + 1:02d}"
                if kind == "finite"
                else f"double_indicator_generator_free_{len([g for g in quotient_generators if g.get('kind') == 'free']) + 1:02d}"
            ),
            "kind": kind,
            "snf_slot": slot + 1,
            "order": invariant if kind == "finite" else None,
            "bs_double_basis_coordinates": bs_coords,
            "vector_in_unknown_ordering": unknown_vector,
            "support": support_from_vector(unknown_vector, ctx["unknown_ordering"]),
            "why_not_in_ai": "Its Smith slot is nontrivial in the quotient, so this vector is not in the AI lattice.",
        }
        if kind == "finite":
            ai_relation = [int(T[row, slot]) for row in range(T.rows)]
            lhs = A * sp.Matrix(ai_relation)
            rhs = invariant * sp.Matrix(bs_coords)
            if lhs != rhs:
                raise ValueError(f"finite quotient relation failed in slot {slot + 1}")
            generator["minimal_multiple_in_ai"] = invariant
            generator["ai_v2_basis_relation_for_minimal_multiple"] = ai_relation
            generator["minimal_multiple_relation_note"] = (
                f"{invariant} times this generator lies in AI_double and its AI_v2-basis coordinates are recorded here."
            )
        else:
            generator["minimal_multiple_in_ai"] = None
            generator["ai_v2_basis_relation_for_minimal_multiple"] = None
            generator["minimal_multiple_relation_note"] = "No nonzero finite multiple is forced into AI_double; this is a free quotient direction."
        quotient_generators.append(generator)

    gap_witnesses = []
    for witness in ctx["bs_vs_ai_v2"]["gap_witnesses"]:
        basis_index = int(witness["bs_basis_index"]) - 1
        full_coords = [int(S[row, basis_index]) for row in range(S.rows)]
        reduced_finite = []
        for slot, value in enumerate(full_coords[:rank]):
            invariant = int(D[slot, slot])
            if invariant > 1:
                reduced_finite.append(value % invariant)
        reduced_free = [int(value) for value in full_coords[rank:]]
        gap_witnesses.append(
            {
                "gap_witness_id": witness["bs_basis_id"],
                "basis_index": witness["bs_basis_index"],
                "coordinates_in_full_snf_basis": full_coords,
                "reduced_coordinates_in_selected_quotient_generators": reduced_finite + reduced_free,
                "finite_part_coordinates_mod_invariants": reduced_finite,
                "free_part_coordinates": reduced_free,
            }
        )

    quotient_group = quotient_group_string(free_rank, finite_part)
    return {
        "rank_BS_double": int(B.cols),
        "rank_AI_double_complete": rank,
        "smith_diagonal_in_bs_coordinates": invariant_factors,
        "quotient_group": quotient_group,
        "free_rank": free_rank,
        "finite_part": finite_part,
        "indicator_generators": quotient_generators,
        "indicator_generators_count": len(quotient_generators),
        "gap_witness_coordinates_in_quotient": gap_witnesses,
    }


def build_indicator_group_summary(indicator: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "rank(BS_double)": indicator["rank_BS_double"],
        "rank(AI_double_complete)": indicator["rank_AI_double_complete"],
        "smith_diagonal_in_bs_coordinates": indicator["smith_diagonal_in_bs_coordinates"],
        "quotient_group": indicator["quotient_group"],
        "free_rank": indicator["free_rank"],
        "finite_part": indicator["finite_part"],
        "indicator_generators_count": indicator["indicator_generators_count"],
    }


def build_indicator_generators_json(indicator: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "unknown_ordering": ctx["unknown_ordering"],
        "bs_basis_ids": [item["id"] for item in ctx["bs_raw"]["basis_vectors"]],
        "quotient_group": indicator["quotient_group"],
        "quotient_generators": indicator["indicator_generators"],
        "gap_witness_coordinates_in_quotient": indicator["gap_witness_coordinates_in_quotient"],
    }


def build_bs_mod_ai_summary(indicator: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "ai_double_complete": True,
        "bs_mod_ai_extracted": True,
        "quotient_group": indicator["quotient_group"],
        "free_part_present": indicator["free_rank"] > 0,
        "free_rank": indicator["free_rank"],
        "finite_part": indicator["finite_part"],
        "scope_statement": "This result applies only to group 10.4.1.31 at groupType=2, within the current with-planes double-group formalism, the current BS basis, and the current 31-dimensional unknown ordering.",
        "not_yet_general_statement": "This is not a whole-database result, not a reusable universal double-group builder proof, and not a statement about other groups.",
        "interpretation_note": "Because the quotient contains a free part, the current BS_double/AI_double is not a purely finite indicator group. The honest algebraic result is the full mixed quotient reported here.",
    }


def build_missing_report(summary: dict[str, Any], table: list[dict[str, Any]]) -> dict[str, Any]:
    missing_entries = [entry for entry in table if not entry["complete"]]
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "missing_families": [entry["family_id"] for entry in missing_entries],
        "missing_family_details": missing_entries,
        "why_this_blocks_quotient": "AI_double_v2 cannot be treated as complete AI_double while any family-level local-object census is incomplete, so BS_double / AI_double would still be contaminated by missing atomic generators.",
        "next_blocker": summary["next_blocker"],
    }


def build_audit_md(summary: dict[str, Any], table: list[dict[str, Any]], indicator: dict[str, Any] | None) -> str:
    lines = [
        f"# Double-Group AI Completeness Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        f"- Group type only: `{GROUP_TYPE}`.",
        "- The settled single-group line is not revisited here.",
        "- The settled double-group k-space backbone, point-like census, and parametric census are treated as trusted background.",
        "- This round only asks whether the current `AI_double_v2` is already the complete `AI_double`, and only if yes does it extract `BS_double / AI_double`.",
        "",
        "## Known Premise",
        "",
        "- The single-group line for the same group is already closed.",
        "- The full double-group k-space backbone is already established.",
        "- Point-like and parametric families together already cover all 15 families `a..o`.",
        "- The current problem is therefore no longer missing-family discovery, but completeness and quotient interpretation.",
        "",
        "## Family-Level Completeness",
        "",
    ]

    for entry in table:
        lines.extend(
            [
                f"### Family `{entry['family_id']}`",
                "",
                f"- Class: `{entry['family_class']}`.",
                f"- Multiplicity: `{entry['multiplicity']}`.",
                f"- Site symmetry: `{entry['site_symmetry_summary']['site_symmetry']}`.",
                f"- Included double local objects: `{', '.join(obj['id'] for obj in entry['current_included_double_local_objects'])}`.",
                f"- Completeness status: `{entry['completeness_status']}`.",
                "- Completeness basis:",
            ]
        )
        for item in entry["completeness_basis"]:
            lines.append(f"  - {item}")
        lines.append(f"- Notes: {' '.join(entry['notes'])}")
        lines.append("")

    anti_point = ["a", "b", "d", "e", "g", "h"]
    anti_param = ["n", "i", "j"]
    pure_param = ["o", "m", "k", "l"]
    lines.extend(
        [
            "## Completeness Arguments By Family Type",
            "",
            f"- Antiunitary point-like families `{', '.join(anti_point)}` are complete because each has exactly one conjugate pair of unitary projective irreps `+i/-i`, and Wigner extension forces that pair into one irreducible case-c magnetic corep.",
            f"- Antiunitary parametric families `{', '.join(anti_param)}` are complete because their unitary subgroup is trivial and the antiunitary generator squares to `+1`, leaving only the eta=`+/-` case-a pair.",
            f"- Pure-unitary parametric families `{', '.join(pure_param)}` are complete because the trivial stabilizer gives one projective irrep (`o`) and the order-2 stabilizers give only the two projective eigenvalues `+i/-i` (`m,k,l`).",
            "- Pure-unitary point-like families `c,f` are complete because the `2/m` projective character is fully determined by the binary choices `C2=+i/-i` and inversion parity `g/u`, giving exactly four local projective irreps.",
            "",
            "## AI Completeness Conclusion",
            "",
            f"- All families audited: `{summary['all_families_audited']}`.",
            f"- Complete families: `{', '.join(summary['complete_families'])}`.",
            f"- Incomplete families: `{', '.join(summary['incomplete_families']) if summary['incomplete_families'] else 'none'}`.",
            f"- `AI_double_v2` can be treated as complete `AI_double`: `{summary['ai_v2_complete_for_double_group']}`.",
            "",
            "## Scope Boundary",
            "",
            "- This conclusion is only for group `10.4.1.31`, `groupType=2`, the current with-planes formalism, and the current BS basis / unknown ordering.",
            "- It is not a statement about other groups, not a reusable database-wide builder proof, and not the end of the overall project.",
            "",
        ]
    )

    if indicator is not None:
        lines.extend(
            [
                "## Quotient Outcome",
                "",
                f"- `rank(BS_double) = {indicator['rank_BS_double']}`.",
                f"- `rank(AI_double) = {indicator['rank_AI_double_complete']}`.",
                f"- Smith diagonal of `AI_double` inside the current `BS_double` basis: `{indicator['smith_diagonal_in_bs_coordinates']}`.",
                f"- Therefore `BS_double / AI_double = {indicator['quotient_group']}`.",
                "- This quotient contains both a free part and a finite torsion part, so it is not a purely finite indicator group.",
                f"- Explicit quotient generators are written to `double_group_indicator_generators_10.4.1.31.json`.",
            ]
        )
    else:
        lines.extend(
            [
                "## Missing-Generator Outcome",
                "",
                "- Completeness did not close, so quotient extraction is intentionally not attempted in this round.",
            ]
        )
    return "\n".join(lines)


def build_package_readme(ai_complete: bool) -> str:
    lines = [
        f"# Review Package: {GROUP_NUMBER} Double-Group AI Completeness",
        "",
        "## Task Scope",
        "",
        f"- group: `{GROUP_NUMBER}`",
        f"- groupType: `{GROUP_TYPE}`",
        "- stage: AI completeness audit + quotient feasibility",
        "",
        "## Current Premise",
        "",
        "- The single-group line for the same group is already closed.",
        "- The full double-group k-space backbone is already established.",
        "- Point-like and parametric family census stages are already finished.",
        "- The current question is no longer missing families, but AI completeness and quotient interpretation.",
        "",
        "## New Content In This Round",
        "",
        "- Double-group family-level completeness audit on all families `a..o`.",
    ]
    if ai_complete:
        lines.append("- Formal quotient extraction for the current `BS_double / AI_double`.")
    else:
        lines.append("- Missing-generator report instead of quotient extraction because completeness did not close.")
    lines.extend(
        [
            "",
            "## Possible Result Pattern",
            "",
            "- `AI_double_v2` may already be complete, in which case the quotient can be extracted.",
            "- Or the family-level completeness audit may still expose missing local objects, in which case quotient extraction must stop.",
            "",
            "## Suggested Review Order",
            "",
            "1. `double_group_ai_completeness_audit_10.4.1.31.md`",
            "2. `double_group_ai_completeness_summary_10.4.1.31.json`",
            "3. `double_group_family_completeness_table_10.4.1.31.json`",
        ]
    )
    if ai_complete:
        lines.extend(
            [
                "4. `double_group_indicator_group_summary_10.4.1.31.json`",
                "5. `double_group_indicator_generators_10.4.1.31.json`",
            ]
        )
    else:
        lines.append("4. `double_group_ai_missing_generators_report_10.4.1.31.json`")
    return "\n".join(lines)


def build_package(ai_complete: bool) -> None:
    reset_dir(PACKAGE_DIR)
    mapping = {
        "double_group_ai_completeness_audit_10.4.1.31.md": AI_COMPLETENESS_AUDIT_MD,
        "double_group_ai_completeness_summary_10.4.1.31.json": AI_COMPLETENESS_SUMMARY_JSON,
        "double_group_family_completeness_table_10.4.1.31.json": FAMILY_COMPLETENESS_JSON,
        "debug_double_group_ai_completeness_10.4.1.31.py": ROOT / "debug_double_group_ai_completeness_10.4.1.31.py",
        "double_group_parametric_corep_audit_10.4.1.31.md": REVIEW_PARAMETRIC / "double_group_parametric_corep_audit_10.4.1.31.md",
        "double_group_parametric_corep_summary_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_parametric_corep_summary_10.4.1.31.json",
        "double_group_parametric_coreps_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_parametric_coreps_10.4.1.31.json",
        "double_group_pointlike_corep_audit_10.4.1.31.md": REVIEW_PARAMETRIC / "double_group_pointlike_corep_audit_10.4.1.31.md",
        "double_group_pointlike_corep_summary_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_pointlike_corep_summary_10.4.1.31.json",
        "double_group_pointlike_coreps_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_pointlike_coreps_10.4.1.31.json",
        "double_group_ai_v2_candidates_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_ai_v2_candidates_10.4.1.31.json",
        "double_group_ai_v2_basis_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_ai_v2_basis_10.4.1.31.json",
        "double_group_bs_vs_ai_v2_summary_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_bs_vs_ai_v2_summary_10.4.1.31.json",
        "double_group_bs_summary_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_bs_summary_10.4.1.31.json",
        "double_group_bs_basis_raw_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_bs_basis_raw_10.4.1.31.json",
        "double_group_bs_basis_pretty_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_bs_basis_pretty_10.4.1.31.json",
        "double_group_full_compatibility_with_planes_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_full_compatibility_with_planes_10.4.1.31.json",
        "double_group_kspace_backbone_audit_10.4.1.31.md": REVIEW_PARAMETRIC / "double_group_kspace_backbone_audit_10.4.1.31.md",
        "double_group_kspace_backbone_summary_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_kspace_backbone_summary_10.4.1.31.json",
        "double_group_line_blocks_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_line_blocks_10.4.1.31.json",
        "double_group_minimal_realspace_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_minimal_realspace_10.4.1.31.json",
        "double_group_minimal_ai_embedding_10.4.1.31.json": REVIEW_PARAMETRIC / "double_group_minimal_ai_embedding_10.4.1.31.json",
        "audit/single_group_indicator_group_summary.json": REVIEW_SINGLE / "audit" / "single_group_indicator_group_summary.json",
        "audit/single_group_indicator_generators.json": REVIEW_SINGLE / "audit" / "single_group_indicator_generators.json",
        "audit/single_group_bs_mod_ai_single_summary.json": REVIEW_SINGLE / "audit" / "single_group_bs_mod_ai_single_summary.json",
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    }
    if ai_complete:
        mapping["double_group_indicator_group_summary_10.4.1.31.json"] = INDICATOR_GROUP_SUMMARY_JSON
        mapping["double_group_indicator_generators_10.4.1.31.json"] = INDICATOR_GENERATORS_JSON
        mapping["double_group_bs_mod_ai_summary_10.4.1.31.json"] = BS_MOD_AI_SUMMARY_JSON
    else:
        mapping["double_group_ai_missing_generators_report_10.4.1.31.json"] = MISSING_GENERATORS_JSON

    for relative, source in mapping.items():
        destination = PACKAGE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    write_text(PACKAGE_DIR / "README.md", build_package_readme(ai_complete))
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = build_context()
    table = build_family_table(ctx)
    summary = build_completeness_summary(table)

    write_json(FAMILY_COMPLETENESS_JSON, {"group_number": GROUP_NUMBER, "group_type": GROUP_TYPE, "families": table})
    write_json(AI_COMPLETENESS_SUMMARY_JSON, summary)

    if summary["ai_v2_complete_for_double_group"]:
        indicator = compute_indicator_data(ctx)
        indicator_group_summary = build_indicator_group_summary(indicator)
        indicator_generators = build_indicator_generators_json(indicator, ctx)
        bs_mod_ai = build_bs_mod_ai_summary(indicator)
        write_json(INDICATOR_GROUP_SUMMARY_JSON, indicator_group_summary)
        write_json(INDICATOR_GENERATORS_JSON, indicator_generators)
        write_json(BS_MOD_AI_SUMMARY_JSON, bs_mod_ai)
        if MISSING_GENERATORS_JSON.exists():
            MISSING_GENERATORS_JSON.unlink()
    else:
        indicator = None
        missing_report = build_missing_report(summary, table)
        write_json(MISSING_GENERATORS_JSON, missing_report)
        for path in (INDICATOR_GROUP_SUMMARY_JSON, INDICATOR_GENERATORS_JSON, BS_MOD_AI_SUMMARY_JSON):
            if path.exists():
                path.unlink()

    audit_md = build_audit_md(summary, table, indicator)
    write_text(AI_COMPLETENESS_AUDIT_MD, audit_md)
    build_package(bool(summary["ai_v2_complete_for_double_group"]))

    return {
        "ctx": ctx,
        "table": table,
        "summary": summary,
        "indicator": indicator,
        "package_tree": format_tree(PACKAGE_DIR),
    }


def validate_outputs() -> dict[str, Any]:
    state = generate_outputs()
    for path in REQUIRED_NEW_FILES:
        if not path.exists():
            raise FileNotFoundError(f"missing required output: {path}")

    summary = load_json(AI_COMPLETENESS_SUMMARY_JSON)
    family_table = load_json(FAMILY_COMPLETENESS_JSON)
    if summary["group_number"] != GROUP_NUMBER or int(summary["group_type"]) != GROUP_TYPE:
        raise ValueError("summary group metadata mismatch")
    if not bool(summary["all_families_audited"]):
        raise ValueError("all families should have been audited")
    if summary["complete_families"] != FAMILY_ORDER:
        raise ValueError("all families should be complete in this phase")
    if summary["incomplete_families"]:
        raise ValueError("unexpected incomplete families in completeness summary")
    if not bool(summary["ai_v2_complete_for_double_group"]):
        raise ValueError("AI_double_v2 should be complete in this phase")

    if len(family_table["families"]) != len(FAMILY_ORDER):
        raise ValueError("family completeness table length mismatch")
    if any(entry["completeness_status"] != "complete" for entry in family_table["families"]):
        raise ValueError("all families should be marked complete")

    indicator_summary = load_json(INDICATOR_GROUP_SUMMARY_JSON)
    indicator_generators = load_json(INDICATOR_GENERATORS_JSON)
    bs_mod_ai = load_json(BS_MOD_AI_SUMMARY_JSON)
    if indicator_summary["quotient_group"] != "Z^2 x Z2 x Z2 x Z2 x Z2":
        raise ValueError("unexpected quotient group")
    if int(indicator_summary["free_rank"]) != 2:
        raise ValueError("unexpected quotient free rank")
    if list(indicator_summary["finite_part"]) != [2, 2, 2, 2]:
        raise ValueError("unexpected quotient finite part")
    if int(indicator_summary["indicator_generators_count"]) != 6:
        raise ValueError("unexpected indicator generator count")
    if len(indicator_generators["quotient_generators"]) != 6:
        raise ValueError("indicator generator file length mismatch")
    if not bool(bs_mod_ai["bs_mod_ai_extracted"]):
        raise ValueError("BS/AI summary should mark quotient extracted")
    if MISSING_GENERATORS_JSON.exists():
        raise ValueError("missing-generator report should not exist when completeness closes")

    if not PACKAGE_DIR.exists() or not PACKAGE_TAR.exists():
        raise FileNotFoundError("package build missing")

    return state


def print_terminal_summary(state: dict[str, Any]) -> None:
    summary = state["summary"]
    indicator = state["indicator"]
    print("1. 所有 families `a..o` 的 double-group completeness audit 是否完成？")
    print(f"   {'是' if summary['all_families_audited'] else '否'}。")
    print("2. `AI_double_v2` 是否已经可以视为完整的 `AI_double`？")
    print(f"   {'是' if summary['ai_v2_complete_for_double_group'] else '否'}。")
    print("3. 如果可以，当前 `BS_double / AI_double` 的 quotient group 是什么？")
    if indicator is None:
        print("   不适用。")
    else:
        print(f"   {indicator['quotient_group']}。")
    print("4. 是否已经给出了显式 double-group quotient generators？")
    if indicator is None:
        print("   否。")
    else:
        print(f"   是，给出了 {indicator['indicator_generators_count']} 个显式 generators。")
    print("5. 如果不可以，缺失的 family / local objects 是什么？")
    if summary["ai_v2_complete_for_double_group"]:
        print("   无。")
    else:
        print(f"   {', '.join(summary['incomplete_families'])}。")
    print("6. 新压缩包完整路径是什么？")
    print(f"   {PACKAGE_TAR}")
    print("7. 压缩包内文件树是什么？")
    for line in state["package_tree"]:
        print(f"   {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Regenerate outputs and validate the double-group completeness / quotient bundle.",
    )
    args = parser.parse_args()

    state = validate_outputs() if args.validate else generate_outputs()
    print_terminal_summary(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
