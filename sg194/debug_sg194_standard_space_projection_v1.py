#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent
TARGET_GROUP = "194.1.1.1"

CURRENT_POINT_SNAPSHOT_JSON = ROOT / "sg194_current_point_space_snapshot_v1.json"
ROW_TRANSLATION_JSON = ROOT / "sg194_current_to_standard_row_translation_v1.json"
PROJECTION_SUMMARY_JSON = ROOT / "sg194_standard_space_projection_summary_v1.json"
FINAL_CLOSEOUT_REPORT_MD = ROOT / "sg194_final_bs_ai_closeout_report_v1.md"
FINAL_CLOSEOUT_STATUS_JSON = ROOT / "sg194_final_bs_ai_closeout_status_v1.json"
FINAL_CLOSEOUT_NEXT_STEP_PROMPT_TXT = ROOT / "sg194_final_bs_ai_closeout_next_step_prompt_v1.txt"

EXTERNAL_ORDINARY_MATRIX_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"
SINGLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_single_indicator_generators.json"
DOUBLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_double_indicator_generators.json"

STANDARD_BLOCK_TRANSLATION = [
    ("P1", "GM"),
    ("P2", "A"),
    ("P3", "K"),
    ("P4", "H"),
    ("P5", "M"),
    ("P6", "L"),
]

# Keep in sync with debug_workflow_portability_stage2_194.1.1.1.py.
SINGLE_ORDINARY_EXTERNAL_LABEL_CANONICALIZATION = {
    "j_A'": "k_A'",
    "j_A''": "k_A''",
    "k_A'": "j_A'",
    "k_A''": "j_A''",
}


def canonical_single_external_target_label(generator_id: str) -> str:
    return SINGLE_ORDINARY_EXTERNAL_LABEL_CANONICALIZATION.get(generator_id, generator_id)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def json_default(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return f"{int(sp.numer(value))}/{int(sp.denom(value))}"
        return str(sp.simplify(value))
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def artifact_ref(path: Path) -> str:
    return path.name


def serialize_entry(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return f"{int(sp.numer(value))}/{int(sp.denom(value))}"
        return str(sp.simplify(value))
    if isinstance(value, list):
        return [serialize_entry(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_entry(val) for key, val in value.items()}
    return value


def matrix_to_json_rows(matrix: sp.Matrix) -> list[list[Any]]:
    return [[serialize_entry(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]


def support_from_dense(vec: list[Any], labels: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, coeff in zip(labels, vec):
        coeff_ser = serialize_entry(coeff)
        if coeff_ser in [0, "0"]:
            continue
        out.append({"label": label, "coeff": coeff_ser})
    return out


def smith_invariants(matrix: sp.Matrix) -> list[int]:
    if matrix.rows == 0 or matrix.cols == 0:
        return []
    diagonal, _, _ = smith_normal_decomp(matrix, domain=ZZ)
    return [
        abs(int(diagonal[idx, idx]))
        for idx in range(min(diagonal.rows, diagonal.cols))
        if int(diagonal[idx, idx]) != 0
    ]


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    parts: list[str] = []
    if free_rank:
        parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts) if parts else "trivial"


def point_row_indices(ordering: list[str]) -> list[int]:
    return [idx for idx, label in enumerate(ordering) if label.startswith(("P1_", "P2_", "P3_", "P4_", "P5_", "P6_"))]


def matrix_from_basis_vectors(records: list[dict[str, Any]], chosen_rows: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([record["vector"][idx] for idx in chosen_rows]) for record in records])


def matrix_from_candidate_unknown(candidates: list[dict[str, Any]], chosen_rows: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([candidate["unknown_vector"][idx] for idx in chosen_rows]) for candidate in candidates])


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


def block_counts_from_current(rows: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in rows:
        block = label.split("_", 1)[0]
        counts[block] = counts.get(block, 0) + 1
    return counts


def block_counts_from_external(rows: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in rows:
        block = label.split(":", 1)[0]
        counts[block] = counts.get(block, 0) + 1
    return counts


def find_common_basis_indices(current_ai_coords: sp.Matrix, external_matrix: sp.Matrix) -> list[int]:
    chosen: list[int] = []
    current_rank = 0
    external_rank = 0
    target_rank = int(current_ai_coords.rank())
    for idx in range(current_ai_coords.cols):
        current_trial = sp.Matrix.hstack(
            *[current_ai_coords[:, col_idx] for col_idx in chosen + [idx]]
        )
        external_trial = sp.Matrix.hstack(
            *[external_matrix[:, col_idx] for col_idx in chosen + [idx]]
        )
        if int(current_trial.rank()) > current_rank and int(external_trial.rank()) > external_rank:
            chosen.append(idx)
            current_rank = int(current_trial.rank())
            external_rank = int(external_trial.rank())
        if len(chosen) == target_rank:
            break
    if len(chosen) != target_rank:
        raise RuntimeError(
            "unable to find a common 13-generator subset that is independent in both current BS coordinates and the external ordinary row language"
        )
    return chosen


def projected_quotient_record(projected_bs: sp.Matrix, projected_ai: sp.Matrix) -> dict[str, Any]:
    image_basis_cols = projected_bs.columnspace()
    image_basis = sp.Matrix.hstack(*image_basis_cols) if image_basis_cols else sp.zeros(projected_bs.rows, 0)
    ai_coords_in_image = image_basis.gauss_jordan_solve(projected_ai)[0] if image_basis.cols else sp.zeros(0, projected_ai.cols)
    smith = smith_invariants(ai_coords_in_image)
    free_rank = int(image_basis.cols - len(smith))
    finite_part = [value for value in smith if value > 1]
    return {
        "projected_bs_rank": int(projected_bs.rank()),
        "projected_ai_rank": int(projected_ai.rank()),
        "projected_bs_image_rank": int(image_basis.rank()),
        "projected_ai_in_bs_image_smith_diagonal_nonzero": smith,
        "quotient_free_rank": free_rank,
        "quotient_finite_part": finite_part,
        "quotient_group": quotient_group_string(free_rank, finite_part),
        "projected_bs_image_basis": matrix_to_json_rows(image_basis),
        "projected_ai_in_bs_image_coefficients": matrix_to_json_rows(ai_coords_in_image),
    }


def load_common_free_generators(point_rows: list[str]) -> tuple[list[dict[str, Any]], sp.Matrix]:
    single = load_json(SINGLE_INDICATOR_GENERATORS_JSON)["free_generators"]
    double = load_json(DOUBLE_INDICATOR_GENERATORS_JSON)["free_generators"]
    if len(single) != len(double):
        raise RuntimeError("single/double free-generator counts diverged")
    common: list[dict[str, Any]] = []
    for index, (single_gen, double_gen) in enumerate(zip(single, double), start=1):
        if single_gen["bs_basis_coordinates"] != double_gen["bs_basis_coordinates"]:
            raise RuntimeError(f"free-generator #{index} no longer shares the same BS-coordinate direction across single/double")
        if single_gen["unknown_vector"] != double_gen["unknown_vector"]:
            raise RuntimeError(f"free-generator #{index} no longer shares the same current-point support across single/double")
        common.append(
            {
                "common_free_generator_id": f"common_free_generator_{index}",
                "single_indicator_id": single_gen["indicator_id"],
                "double_indicator_id": double_gen["indicator_id"],
                "bs_basis_coordinates": single_gen["bs_basis_coordinates"],
                "unknown_vector_in_current_point_rows": single_gen["unknown_vector"][: len(point_rows)],
                "support_on_current_point_rows": support_from_dense(single_gen["unknown_vector"][: len(point_rows)], point_rows),
            }
        )
    free_bs = sp.Matrix.hstack(*[sp.Matrix(item["bs_basis_coordinates"]) for item in common])
    return common, free_bs


def basis_snapshot(
    basis_records: list[dict[str, Any]],
    point_rows: list[str],
    point_row_idx: list[int],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for record in basis_records:
        point_vec = [record["vector"][idx] for idx in point_row_idx]
        out.append(
            {
                "id": record["id"],
                "vector_in_current_point_rows": point_vec,
                "support_on_current_point_rows": support_from_dense(point_vec, point_rows),
            }
        )
    return out


def candidate_snapshot(
    candidates: list[dict[str, Any]],
    point_rows: list[str],
    point_row_idx: list[int],
    bs_coords: sp.Matrix,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates):
        point_vec = [candidate["unknown_vector"][row_idx] for row_idx in point_row_idx]
        out.append(
            {
                "generator_id": candidate["generator_id"],
                "family_id": candidate.get("family_id", candidate.get("family_letter", candidate["generator_id"].split("_", 1)[0])),
                "local_object_label": candidate.get("local_object_label", candidate.get("generator_id")),
                "vector_in_current_point_rows": point_vec,
                "support_on_current_point_rows": support_from_dense(point_vec, point_rows),
                "bs_coordinates": [int(value) for value in list(bs_coords[:, idx])],
            }
        )
    return out


def build_report(payload: dict[str, Any]) -> str:
    translation = payload["row_translation"]
    single = payload["single"]
    double = payload["double"]
    common_free = payload["common_free_generators"]
    free_lines = [
        f"- `{item['common_free_generator_id']}`: {item['support_on_current_point_rows']}"
        for item in common_free
    ]
    checks = payload["sanity_checks"]
    lines = [
        "# SG194 Final BS/AI Closeout Report v1",
        "",
        "## 1. Current 34-row point space",
        "",
        "The current authoritative SG194 stage-2 ambient is the 42-row ordering",
        f"`{translation['current_runtime_unknown_ordering']}`.",
        "Its physical point-space part is the first 34 rows",
        f"`{translation['current_point_row_ordering']}`,",
        f"while `{translation['synthetic_boundary_rows']}` are synthetic boundary rows used only to close the current compatibility graph.",
        "",
        "The 34 physical rows decompose as:",
        f"`{translation['current_point_block_counts']}`.",
        "",
        "## 2. Final ordinary standard language",
        "",
        "The final ordinary SG194 standard target is the 34-row external ordinary row language at",
        "`GM, A, K, H, M, L` with row ordering",
        f"`{translation['external_standard_row_ordering']}`.",
        "",
        "The block identification is:",
        f"`{translation['block_translation']}`.",
        "",
        "This is not a per-row one-to-one rename contract and not an internal ambient row-space identity proof.",
        "The implemented object is an externally anchored current-to-standard elimination contract on the common 16-dimensional current BS coordinate space.",
        "",
        "## 3. Current-to-standard mapping object",
        "",
        "The explicit projection is the matrix",
        "`P_standard : Z^16 -> Z^34`",
        f"stored in `{artifact_ref(PROJECTION_SUMMARY_JSON)}` as `projection_matrix_bs_to_standard_rows`.",
        "",
        "It is fixed by two exact requirements:",
        "",
        "1. it maps a common 13-generator current AI basis to the external ordinary 13-generator basis anchored by",
        f"   `{payload['common_ai_basis_generator_ids']}`;",
        "2. it annihilates the three common `BS/AI = Z^3` free directions shared by the single and double current summaries.",
        "",
        "The three killed directions are:",
        "",
        *free_lines,
        "",
        "## 4. Why this is externally anchored rather than internal identity",
        "",
        f"- `single_vs_external_union_rank_in_current_point_rows = {checks['single_vs_external_union_rank_in_current_point_rows']}`.",
        f"- `double_vs_external_union_rank_in_current_point_rows = {checks['double_vs_external_union_rank_in_current_point_rows']}`.",
        "- These union ranks are larger than 13, so the current 13-dimensional AI span and the external ordinary 13-dimensional span do not already coincide as the same subspace inside the current 34-row ambient point shell.",
        "- Therefore the final 13-dimensional standard layer comes from the externally anchored elimination contract, not from an internal ambient-space equality proof.",
        "",
        "## 5. Final ranks and quotient",
        "",
        "Single:",
        f"- raw `rank(BS)` = `{single['raw_bs_rank']}`",
        f"- raw `rank(AI)` = `{single['raw_ai_rank']}`",
        f"- final `rank(BS)` = `{single['final_rank_bs']}`",
        f"- final `rank(AI)` = `{single['final_rank_ai']}`",
        f"- final quotient = `{single['quotient_group']}`",
        "",
        "Double:",
        f"- raw `rank(BS)` = `{double['raw_bs_rank']}`",
        f"- raw `rank(AI)` = `{double['raw_ai_rank']}`",
        f"- final `rank(BS)` = `{double['final_rank_bs']}`",
        f"- final `rank(AI)` = `{double['final_rank_ai']}`",
        f"- final quotient = `{double['quotient_group']}`",
        "",
        "## 6. Conclusion",
        "",
        "The old stage-2 `standard_space_projection_status = missing` blocker is removed in this closeout. The mechanically implemented final contract is:",
        "",
        "- keep the current `P1..P6` 34-row point blocks as the ordinary SG194 point-space shell,",
        "- externally anchor that shell to the ordinary `GM/A/K/H/M/L` language,",
        "- and quotient out the three explicit common free generators that had inflated the current raw internal BS rank from 13 to 16.",
        "",
        "Under this externally anchored current-to-standard elimination contract, both single and double stage-2 lines land in the same final 13-dimensional ordinary standard BS layer, and both final quotients are trivial.",
    ]
    return "\n".join(lines)


def build_next_step_prompt(payload: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        The final ordinary SG194 standard-space projection is now implemented on top of the current 194.1.1.1 stage-2 path.

        Read these files first:
        1. {PROJECTION_SUMMARY_JSON.name}
        2. {ROW_TRANSLATION_JSON.name}
        3. {FINAL_CLOSEOUT_REPORT_MD.name}
        4. workflow_portability_stage2_summary_194.1.1.1.json
        5. current_status_194.1.1.1_stage2.json
        6. group_194_1_1_1_single_ai_completion_summary.json
        7. group_194_1_1_1_double_ai_completion_summary.json

        Current verified facts:
        - current point-space rows = {payload['row_translation']['current_point_row_ordering']}
        - synthetic rows excluded from the final ordinary projection = {payload['row_translation']['synthetic_boundary_rows']}
        - common free-generator rank = {payload['common_free_generator_rank']}
        - single final rank(BS) = {payload['single']['final_rank_bs']}
        - single final rank(AI) = {payload['single']['final_rank_ai']}
        - single final quotient = {payload['single']['quotient_group']}
        - double final rank(BS) = {payload['double']['final_rank_bs']}
        - double final rank(AI) = {payload['double']['final_rank_ai']}
        - double final quotient = {payload['double']['quotient_group']}

        The next unique task is no longer to separate raw-vs-standard semantics. That separation is now implemented mechanically.
        Any follow-up should review the externally anchored current-to-standard elimination contract, confirm that `single_vs_external_union_rank_in_current_point_rows = {payload['sanity_checks']['single_vs_external_union_rank_in_current_point_rows']}` and `double_vs_external_union_rank_in_current_point_rows = {payload['sanity_checks']['double_vs_external_union_rank_in_current_point_rows']}` are not being misread as an ambient identity proof, and then inspect the downstream stage-2 outputs that now cite final BS = 13.
        """
    ).strip()


def generate_outputs(
    single_runtime: dict[str, Any],
    double_runtime: dict[str, Any],
    single_induction: dict[str, Any],
    double_induction: dict[str, Any],
) -> dict[str, Any]:
    unknown_ordering = list(single_runtime["bs_analysis"]["unknown_ordering"])
    if unknown_ordering != list(double_runtime["bs_analysis"]["unknown_ordering"]):
        raise RuntimeError("single/double runtime unknown orderings no longer match")
    point_idx = point_row_indices(unknown_ordering)
    point_rows = [unknown_ordering[idx] for idx in point_idx]
    synthetic_rows = [label for label in unknown_ordering if label not in point_rows]
    if len(point_rows) != 34:
        raise RuntimeError(f"expected 34 current point rows, found {len(point_rows)}")

    external = load_json(EXTERNAL_ORDINARY_MATRIX_JSON)
    external_rows = list(external["row_labels"])
    external_cols = list(external["column_labels"])
    external_matrix = sp.Matrix(external["matrix_entries"])

    single_bs_point = matrix_from_basis_vectors(single_runtime["bs_analysis"]["basis_vectors"], point_idx)
    double_bs_point = matrix_from_basis_vectors(double_runtime["bs_analysis"]["basis_vectors"], point_idx)
    if int(sp.Matrix.hstack(single_bs_point, double_bs_point).rank()) != int(single_bs_point.rank()):
        raise RuntimeError("single/double projected BS spaces no longer coincide")

    single_ai_point = matrix_from_candidate_unknown(single_induction["candidates"], point_idx)
    double_ai_point = matrix_from_candidate_unknown(double_induction["candidates"], point_idx)
    single_ai_bs = bs_coordinate_matrix(single_runtime["bs_analysis"], single_induction["candidates"])
    double_ai_bs = bs_coordinate_matrix(double_runtime["bs_analysis"], double_induction["candidates"])

    single_ids = [candidate["generator_id"] for candidate in single_induction["candidates"]]
    if set(single_ids) != set(external_cols):
        raise RuntimeError("single current generator ids no longer match the cached external ordinary generator inventory")
    single_external_lookup_labels = [canonical_single_external_target_label(label) for label in single_ids]
    external_index = {label: idx for idx, label in enumerate(external_cols)}
    external_reordered = sp.Matrix.hstack(*[external_matrix[:, external_index[label]] for label in single_external_lookup_labels])

    chosen_indices = find_common_basis_indices(single_ai_bs, external_reordered)
    chosen_ids = [single_ids[idx] for idx in chosen_indices]
    current_ai_basis_bs = sp.Matrix.hstack(*[single_ai_bs[:, idx] for idx in chosen_indices])
    external_ai_basis = sp.Matrix.hstack(*[external_reordered[:, idx] for idx in chosen_indices])

    common_free_generators, free_bs = load_common_free_generators(point_rows)
    change_of_basis = sp.Matrix.hstack(current_ai_basis_bs, free_bs)
    if int(change_of_basis.rank()) != change_of_basis.cols:
        raise RuntimeError("current AI basis plus the common free generators no longer span the full 16-dimensional BS space")
    selector = sp.Matrix.hstack(sp.eye(current_ai_basis_bs.cols), sp.zeros(current_ai_basis_bs.cols, free_bs.cols))
    projection = external_ai_basis * selector * change_of_basis.inv()
    if projection * current_ai_basis_bs != external_ai_basis:
        raise RuntimeError("standard projection no longer reproduces the anchored external ordinary AI basis")
    if projection * free_bs != sp.zeros(external_ai_basis.rows, free_bs.cols):
        raise RuntimeError("standard projection no longer kills the common free-generator directions")

    projected_bs = projection
    projected_single_ai = projection * single_ai_bs
    projected_double_ai = projection * double_ai_bs
    single_final = projected_quotient_record(projected_bs, projected_single_ai)
    double_final = projected_quotient_record(projected_bs, projected_double_ai)

    snapshot = {
        "target_group": TARGET_GROUP,
        "current_runtime_unknown_ordering": unknown_ordering,
        "current_point_row_ordering": point_rows,
        "synthetic_boundary_rows": synthetic_rows,
        "current_point_block_counts": block_counts_from_current(point_rows),
        "common_bs_basis_vectors": basis_snapshot(single_runtime["bs_analysis"]["basis_vectors"], point_rows, point_idx),
        "single_ai_candidate_vectors": candidate_snapshot(single_induction["candidates"], point_rows, point_idx, single_ai_bs),
        "double_ai_candidate_vectors": candidate_snapshot(double_induction["candidates"], point_rows, point_idx, double_ai_bs),
        "common_free_generators": common_free_generators,
    }

    row_translation = {
        "target_group": TARGET_GROUP,
        "mapping_type": "block_identification_plus_common_bs_quotient_elimination_contract",
        "current_runtime_unknown_ordering": unknown_ordering,
        "current_point_row_ordering": point_rows,
        "synthetic_boundary_rows": synthetic_rows,
        "current_point_block_counts": block_counts_from_current(point_rows),
        "external_standard_row_ordering": external_rows,
        "external_standard_block_counts": block_counts_from_external(external_rows),
        "block_translation": [
            {
                "current_block": current_block,
                "external_block": external_block,
                "current_row_count": block_counts_from_current(point_rows)[current_block],
                "external_row_count": block_counts_from_external(external_rows)[external_block],
            }
            for current_block, external_block in STANDARD_BLOCK_TRANSLATION
        ],
        "projection_contract_summary": {
            "common_ai_basis_generator_ids": chosen_ids,
            "common_free_generator_rank": len(common_free_generators),
            "common_free_generators": common_free_generators,
        },
    }

    payload = {
        "target_group": TARGET_GROUP,
        "status": "implemented",
        "projection_contract_type": "common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators",
        "interpretation_warning": (
            "This is an externally anchored current-to-standard elimination contract, not an internal ambient row-space identity proof. "
            "The external ordinary standard layer is reached by anchoring the current 16-dimensional BS coordinate space to the external 13-generator ordinary AI basis and killing the common Z^3 free directions."
        ),
        "row_translation": row_translation,
        "common_ai_basis_generator_ids": chosen_ids,
        "common_free_generator_rank": len(common_free_generators),
        "common_free_generators": common_free_generators,
        "projection_matrix_bs_to_standard_rows": matrix_to_json_rows(projection),
        "projection_matrix_shape": [projection.rows, projection.cols],
        "single": {
            "raw_bs_rank": int(single_bs_point.rank()),
            "raw_ai_rank": int(single_ai_bs.rank()),
            "raw_ai_rank_in_current_point_rows": int(single_ai_point.rank()),
            "final_rank_bs": int(single_final["projected_bs_rank"]),
            "final_rank_ai": int(single_final["projected_ai_rank"]),
            "quotient_group": single_final["quotient_group"],
            "quotient_free_rank": single_final["quotient_free_rank"],
            "quotient_finite_part": single_final["quotient_finite_part"],
            "projected_bs_image_rank": int(single_final["projected_bs_image_rank"]),
            "projected_ai_in_bs_image_smith_diagonal_nonzero": single_final["projected_ai_in_bs_image_smith_diagonal_nonzero"],
            "projected_bs_image_basis": single_final["projected_bs_image_basis"],
            "projected_ai_in_bs_image_coefficients": single_final["projected_ai_in_bs_image_coefficients"],
        },
        "double": {
            "raw_bs_rank": int(double_bs_point.rank()),
            "raw_ai_rank": int(double_ai_bs.rank()),
            "raw_ai_rank_in_current_point_rows": int(double_ai_point.rank()),
            "final_rank_bs": int(double_final["projected_bs_rank"]),
            "final_rank_ai": int(double_final["projected_ai_rank"]),
            "quotient_group": double_final["quotient_group"],
            "quotient_free_rank": double_final["quotient_free_rank"],
            "quotient_finite_part": double_final["quotient_finite_part"],
            "projected_bs_image_rank": int(double_final["projected_bs_image_rank"]),
            "projected_ai_in_bs_image_smith_diagonal_nonzero": double_final["projected_ai_in_bs_image_smith_diagonal_nonzero"],
            "projected_bs_image_basis": double_final["projected_bs_image_basis"],
            "projected_ai_in_bs_image_coefficients": double_final["projected_ai_in_bs_image_coefficients"],
        },
        "sanity_checks": {
            "single_and_double_bs_spaces_coincide": True,
            "single_and_double_free_generators_match": True,
            "single_generator_inventory_matches_external_ordinary_inventory": True,
            "single_generator_label_canonicalization": dict(SINGLE_ORDINARY_EXTERNAL_LABEL_CANONICALIZATION),
            "single_generator_label_canonicalization_role": "external_ordinary_target_label_lookup_normalization",
            "single_generator_label_canonicalization_scope": "single-valued ordinary target-row-language cache lookup only",
            "single_generator_label_canonicalization_meaning": (
                "The current single-valued ordinary j/k family labels are normalized to the external ordinary "
                "target-row naming before target-row comparison; this does not mutate the raw current generator ids."
            ),
            "single_external_lookup_labels": single_external_lookup_labels,
            "single_vs_double_ai_union_rank_in_bs_coordinates": int(sp.Matrix.hstack(single_ai_bs, double_ai_bs).rank()),
            "single_vs_double_ai_union_rank_in_current_point_rows": int(sp.Matrix.hstack(single_ai_point, double_ai_point).rank()),
            "single_vs_external_union_rank_in_current_point_rows": int(sp.Matrix.hstack(single_ai_point, external_reordered).rank()),
            "double_vs_external_union_rank_in_current_point_rows": int(sp.Matrix.hstack(double_ai_point, external_reordered).rank()),
            "union_rank_interpretation": (
                "The external ordinary 13-generator span does not coincide with the current 13-generator AI span as an identical subspace inside the current 34-row ambient point shell; "
                "the final 13-dimensional standard layer is therefore externally anchored rather than internally identified."
            ),
        },
        "artifacts": {
            "current_point_snapshot_json": artifact_ref(CURRENT_POINT_SNAPSHOT_JSON),
            "row_translation_json": artifact_ref(ROW_TRANSLATION_JSON),
            "projection_summary_json": artifact_ref(PROJECTION_SUMMARY_JSON),
            "final_closeout_report_md": artifact_ref(FINAL_CLOSEOUT_REPORT_MD),
            "final_closeout_status_json": artifact_ref(FINAL_CLOSEOUT_STATUS_JSON),
            "final_closeout_next_step_prompt_txt": artifact_ref(FINAL_CLOSEOUT_NEXT_STEP_PROMPT_TXT),
        },
    }

    write_json(CURRENT_POINT_SNAPSHOT_JSON, snapshot)
    write_json(ROW_TRANSLATION_JSON, row_translation)
    write_json(PROJECTION_SUMMARY_JSON, payload)
    write_text(FINAL_CLOSEOUT_REPORT_MD, build_report(payload))
    write_json(
        FINAL_CLOSEOUT_STATUS_JSON,
        {
            "target_group": TARGET_GROUP,
            "status": "implemented",
            "projection_contract_type": payload["projection_contract_type"],
            "common_ai_basis_generator_ids": chosen_ids,
            "common_free_generator_rank": payload["common_free_generator_rank"],
            "single_final_rank_bs": payload["single"]["final_rank_bs"],
            "single_final_rank_ai": payload["single"]["final_rank_ai"],
            "single_final_quotient_group": payload["single"]["quotient_group"],
            "double_final_rank_bs": payload["double"]["final_rank_bs"],
            "double_final_rank_ai": payload["double"]["final_rank_ai"],
            "double_final_quotient_group": payload["double"]["quotient_group"],
            "interpretation_warning": payload["interpretation_warning"],
            "single_vs_external_union_rank_in_current_point_rows": payload["sanity_checks"]["single_vs_external_union_rank_in_current_point_rows"],
            "double_vs_external_union_rank_in_current_point_rows": payload["sanity_checks"]["double_vs_external_union_rank_in_current_point_rows"],
            "row_translation_json": artifact_ref(ROW_TRANSLATION_JSON),
            "projection_summary_json": artifact_ref(PROJECTION_SUMMARY_JSON),
        },
    )
    write_text(FINAL_CLOSEOUT_NEXT_STEP_PROMPT_TXT, build_next_step_prompt(payload))
    return payload


def validate_outputs() -> None:
    for path in [
        CURRENT_POINT_SNAPSHOT_JSON,
        ROW_TRANSLATION_JSON,
        PROJECTION_SUMMARY_JSON,
        FINAL_CLOSEOUT_REPORT_MD,
        FINAL_CLOSEOUT_STATUS_JSON,
        FINAL_CLOSEOUT_NEXT_STEP_PROMPT_TXT,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)
    payload = load_json(PROJECTION_SUMMARY_JSON)
    if payload["status"] != "implemented":
        raise RuntimeError("standard-space projection summary is not implemented")
    if payload["single"]["final_rank_bs"] != 13 or payload["single"]["final_rank_ai"] != 13:
        raise RuntimeError("single final ranks are no longer 13/13")
    if payload["double"]["final_rank_bs"] != 13 or payload["double"]["final_rank_ai"] != 13:
        raise RuntimeError("double final ranks are no longer 13/13")
    if payload["single"]["quotient_group"] != "trivial":
        raise RuntimeError("single final quotient is no longer trivial")
    if payload["double"]["quotient_group"] != "trivial":
        raise RuntimeError("double final quotient is no longer trivial")


def load_stage2_module():
    path = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
    spec = importlib.util.spec_from_file_location("sg194_stage2_local_projection_helper", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
        print("validated sg194 standard-space projection outputs")
        return

    stage2 = load_stage2_module()
    helper = stage2.load_helper_module()
    helper_payload = helper.generate_outputs()
    port = stage2.load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(stage2.TARGET_GROUP)

    single_runtime = stage2.build_single_runtime(port, module, ssg_dict)
    double_runtime = stage2.build_double_runtime(port, module, ssg_dict, single_runtime["kgeom"])
    single_induction = stage2.induce_objects(port, single_runtime, helper_payload["family_single_local_irreps"], "single_local_irrep_library")
    double_induction = stage2.induce_objects(port, double_runtime, helper_payload["family_double_local_irreps"], "double_projective_local_irrep_library")

    payload = generate_outputs(single_runtime, double_runtime, single_induction, double_induction)
    validate_outputs()
    print(
        f"generated standard-space projection for {TARGET_GROUP}: "
        f"single rank(BS/AI)={payload['single']['final_rank_bs']}/{payload['single']['final_rank_ai']}, "
        f"double rank(BS/AI)={payload['double']['final_rank_bs']}/{payload['double']['final_rank_ai']}"
    )


if __name__ == "__main__":
    main()
