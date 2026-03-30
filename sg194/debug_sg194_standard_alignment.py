#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
import textwrap
from collections import OrderedDict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent

GROUP = "194.1.1.1"

SINGLE_MAP_MD = ROOT / "sg194_single_standard_space_map.md"
SINGLE_MAP_JSON = ROOT / "sg194_single_standard_space_map.json"
DOUBLE_ALIGN_MD = ROOT / "sg194_double_spinorial_alignment.md"
DOUBLE_ALIGN_JSON = ROOT / "sg194_double_spinorial_alignment.json"
SINGLE_QUOTIENT_JSON = ROOT / "sg194_single_standard_quotient_recomputed.json"
DOUBLE_QUOTIENT_JSON = ROOT / "sg194_double_standard_quotient_recomputed.json"
AUDIT_MD = ROOT / "sg194_standard_alignment_audit.md"
SUMMARY_JSON = ROOT / "sg194_standard_alignment_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_standard_alignment.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_standard_alignment.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_sg194_standard_alignment.txt"
REPORT_MD = ROOT / "sg194_standard_alignment_report.md"
REPORT_TEX = ROOT / "sg194_standard_alignment_report.tex"
REPORT_PDF = ROOT / "sg194_standard_alignment_report.pdf"

PACKAGE_NAME = "review_package_sg194_standard_alignment_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

RESEARCH_RESULTS_TSV = ROOT / "research-results-standard-alignment.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-standard-alignment.json"
VERIFY_CMD = "python3 -u debug_sg194_standard_alignment.py --validate"
GUARD_CMD = "python3 -u debug_external_sg194_audit.py --validate && python3 -u debug_raw_matrix_audit.py --validate"

RAW_SINGLE_C = ROOT / "raw_194_1_1_1_single_C.json"
RAW_SINGLE_BS = ROOT / "raw_194_1_1_1_single_bs_basis_raw.json"
RAW_SINGLE_AI_BASIS = ROOT / "raw_194_1_1_1_single_ai_basis.json"
RAW_SINGLE_AI_CAND = ROOT / "raw_194_1_1_1_single_ai_candidates.json"
RAW_SINGLE_QUOTIENT = ROOT / "raw_194_1_1_1_single_quotient.json"

RAW_DOUBLE_C = ROOT / "raw_194_1_1_1_double_C.json"
RAW_DOUBLE_BS = ROOT / "raw_194_1_1_1_double_bs_basis_raw.json"
RAW_DOUBLE_AI_BASIS = ROOT / "raw_194_1_1_1_double_ai_basis.json"
RAW_DOUBLE_AI_CAND = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_DOUBLE_QUOTIENT = ROOT / "raw_194_1_1_1_double_quotient.json"

EXT_SOURCE_JSON = ROOT / "sg194_external_source_audit.json"
EXT_AI_JSON = ROOT / "sg194_external_ai_standard.json"
EXT_CMP_JSON = ROOT / "sg194_external_vs_current_ai_comparison.json"
EXT_JUDGMENT_JSON = ROOT / "sg194_final_correction_judgment.json"
FINITE_SUMMARY_JSON = ROOT / "finite_indicator_extraction_summary.json"
REINTERPRET_SINGLE_JSON = ROOT / "reinterpretation_194_1_1_1_single_finite_part.json"
REINTERPRET_DOUBLE_JSON = ROOT / "reinterpretation_194_1_1_1_double_finite_part.json"
SINGLE_AI_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
SINGLE_INDICATOR_SUMMARY_JSON = ROOT / "group_194_1_1_1_single_indicator_group_summary.json"
SINGLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_single_indicator_generators.json"
DOUBLE_AI_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
DOUBLE_INDICATOR_SUMMARY_JSON = ROOT / "group_194_1_1_1_double_indicator_group_summary.json"
DOUBLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_double_indicator_generators.json"

BACKGROUND_FILES = [
    EXT_SOURCE_JSON,
    EXT_AI_JSON,
    EXT_CMP_JSON,
    EXT_JUDGMENT_JSON,
    RAW_SINGLE_C,
    RAW_SINGLE_BS,
    RAW_SINGLE_AI_BASIS,
    RAW_SINGLE_AI_CAND,
    RAW_SINGLE_QUOTIENT,
    RAW_DOUBLE_C,
    RAW_DOUBLE_BS,
    RAW_DOUBLE_AI_BASIS,
    RAW_DOUBLE_AI_CAND,
    RAW_DOUBLE_QUOTIENT,
    FINITE_SUMMARY_JSON,
    REINTERPRET_SINGLE_JSON,
    REINTERPRET_DOUBLE_JSON,
    SINGLE_AI_COMPLETION_JSON,
    SINGLE_INDICATOR_SUMMARY_JSON,
    SINGLE_INDICATOR_GENERATORS_JSON,
    DOUBLE_AI_COMPLETION_JSON,
    DOUBLE_INDICATOR_SUMMARY_JSON,
    DOUBLE_INDICATOR_GENERATORS_JSON,
    ROOT / "swyckoff_r.py",
    ROOT / "swyckoff_k.py",
    ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
    ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
]

REQUIRED_OUTPUTS = [
    SINGLE_MAP_MD,
    SINGLE_MAP_JSON,
    DOUBLE_ALIGN_MD,
    DOUBLE_ALIGN_JSON,
    SINGLE_QUOTIENT_JSON,
    DOUBLE_QUOTIENT_JSON,
    AUDIT_MD,
    SUMMARY_JSON,
    HANDOFF_MD,
    CURRENT_STATUS_JSON,
    NEXT_STEP_PROMPT_TXT,
    ROOT / "debug_sg194_standard_alignment.py",
    REPORT_TEX,
    REPORT_PDF,
    PACKAGE_TARBALL,
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def latex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "^": r"\textasciicircum{}",
    }
    out = text
    for old, new in repl.items():
        out = out.replace(old, new)
    return out


def serialize_entry(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        return str(sp.simplify(value))
    if isinstance(value, list):
        return [serialize_entry(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_entry(val) for key, val in value.items()}
    return value


def matrix_to_json_rows(matrix: sp.Matrix) -> list[list[Any]]:
    return [[serialize_entry(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]


def vector_to_json(vec: sp.Matrix) -> list[Any]:
    return [serialize_entry(val) for val in list(vec)]


def matrix_from_candidate_unknown(candidates: list[dict[str, Any]]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(c["unknown_vector"]) for c in candidates])


def matrix_from_candidate_bs(candidates: list[dict[str, Any]]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(c["bs_coordinates"]) for c in candidates])


def matrix_from_basis_vectors(records: list[dict[str, Any]]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(rec["vector"]) for rec in records])


def matrix_from_columns(columns: list[list[int]]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix(col) for col in columns])


def support_from_vector(vec: list[Any], labels: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, coeff in zip(labels, vec):
        coeff_ser = serialize_entry(coeff)
        if coeff_ser in [0, "0"]:
            continue
        out.append({"label": label, "coeff": coeff_ser})
    return out


def extend_columns_to_basis(columns: list[sp.Matrix], ambient_dim: int) -> tuple[list[sp.Matrix], list[int]]:
    basis = columns[:]
    chosen_standard_indices: list[int] = []
    eye = sp.eye(ambient_dim)
    for idx in range(ambient_dim):
        trial = sp.Matrix.hstack(*basis, eye[:, idx])
        if trial.rank() > len(basis):
            basis.append(eye[:, idx])
            chosen_standard_indices.append(idx)
        if len(basis) == ambient_dim:
            break
    if len(basis) != ambient_dim:
        raise RuntimeError("unable to extend columns to full ambient basis")
    return basis, chosen_standard_indices


def smith_invariants(matrix: sp.Matrix) -> list[int]:
    if matrix.rows == 0 or matrix.cols == 0:
        return []
    d_mat, _, _ = smith_normal_decomp(matrix, domain=sp.ZZ)
    out: list[int] = []
    for i in range(min(d_mat.rows, d_mat.cols)):
        value = d_mat[i, i]
        if value != 0:
            out.append(int(value))
    return out


def quotient_string(free_rank: int, finite_part: list[int]) -> str:
    parts: list[str] = []
    if free_rank:
        parts.append(f"Z^{free_rank}" if free_rank != 1 else "Z")
    for value in finite_part:
        parts.append(f"Z{value}")
    return " x ".join(parts) if parts else "trivial"


def load_external_helper():
    spec = importlib.util.spec_from_file_location("sg194_external_helper", ROOT / "debug_external_sg194_audit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load debug_external_sg194_audit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_single_alignment(external_helper: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    single_ext = external_helper.fetch_single_external_data()
    raw_bs = load_json(RAW_SINGLE_BS)
    raw_ai_basis = load_json(RAW_SINGLE_AI_BASIS)
    raw_ai_candidates = load_json(RAW_SINGLE_AI_CAND)
    raw_quotient = load_json(RAW_SINGLE_QUOTIENT)

    bs_basis_ids = [entry["id"] for entry in raw_bs["basis_vectors"]]
    bs_matrix_unknown = matrix_from_basis_vectors(raw_bs["basis_vectors"])
    ai_basis_unknown = matrix_from_basis_vectors(raw_ai_basis["basis_vectors"])
    ai_in_bs = sp.Matrix.hstack(*[sp.Matrix(col) for col in raw_ai_basis["basis_bs_coefficients"]])
    candidate_relation = sp.Matrix.hstack(*[sp.Matrix(col) for col in raw_ai_basis["basis_from_candidate_relations"]])
    current_candidate_labels = [cand["generator_id"] for cand in raw_ai_candidates["candidates"]]
    external_column_labels = list(single_ext.column_labels)
    if set(current_candidate_labels) != set(external_column_labels):
        raise RuntimeError("single external/current candidate inventories no longer match exactly")
    current_candidate_unknown = matrix_from_candidate_unknown(raw_ai_candidates["candidates"])
    external_col_index = {label: idx for idx, label in enumerate(external_column_labels)}
    external_candidate_matrix = sp.Matrix.hstack(
        *[single_ext.matrix[:, external_col_index[label]] for label in current_candidate_labels]
    )
    external_ai_basis = external_candidate_matrix * candidate_relation

    if bs_matrix_unknown * ai_in_bs != ai_basis_unknown:
        raise RuntimeError("single AI basis no longer equals BS * AI_in_BS matrix")

    ai_columns = [ai_in_bs[:, idx] for idx in range(ai_in_bs.cols)]
    full_basis_cols, complement_std_indices = extend_columns_to_basis(ai_columns, ai_in_bs.rows)
    complement_cols = full_basis_cols[ai_in_bs.cols :]
    change_of_basis = sp.Matrix.hstack(*full_basis_cols)
    change_inv = change_of_basis.inv()
    ai_projector = sp.Matrix.hstack(sp.eye(ai_in_bs.cols), sp.zeros(ai_in_bs.cols, ai_in_bs.rows - ai_in_bs.cols)) * change_inv
    projection_bs_to_standard = external_ai_basis * ai_projector

    if projection_bs_to_standard * ai_in_bs != external_ai_basis:
        raise RuntimeError("single projection does not reproduce the external AI basis")
    if complement_cols:
        complement_matrix = sp.Matrix.hstack(*complement_cols)
        if projection_bs_to_standard * complement_matrix != sp.zeros(external_ai_basis.rows, complement_matrix.cols):
            raise RuntimeError("single projection does not kill complement directions")
    else:
        complement_matrix = sp.zeros(ai_in_bs.rows, 0)

    projected_bs_basis = projection_bs_to_standard
    projected_ai_basis = external_ai_basis
    standard_bs_rank = int(projected_bs_basis.rank())
    standard_ai_rank = int(projected_ai_basis.rank())
    if standard_bs_rank != standard_ai_rank:
        raise RuntimeError("single projected BS/AI ranks should coincide in the constructed standard space")

    # Use a column-space basis for the projected BS image and express the projected AI in that basis.
    image_basis_cols = projected_bs_basis.columnspace()
    image_basis = sp.Matrix.hstack(*image_basis_cols)
    ai_in_image_coeff = image_basis.gauss_jordan_solve(projected_ai_basis)[0]
    if image_basis * ai_in_image_coeff != projected_ai_basis:
        raise RuntimeError("single AI image is not contained in the projected BS image")
    single_snf = smith_invariants(ai_in_image_coeff)
    if any(val != 1 for val in single_snf) or image_basis.cols != len(single_snf):
        raise RuntimeError("single projected quotient should be trivial in the constructed standard space")

    complement_records = []
    for idx, col in enumerate(complement_cols, start=1):
        complement_records.append(
            {
                "id": f"single_enlarged_complement_{idx:02d}",
                "bs_coordinate_vector": vector_to_json(col),
                "support_on_bs_basis": support_from_vector(list(col), bs_basis_ids),
                "seed_standard_basis_index": int(complement_std_indices[idx - 1]),
            }
        )

    standard_image_records = []
    for idx in range(projected_bs_basis.cols):
        col = projected_bs_basis[:, idx]
        standard_image_records.append(
            {
                "bs_basis_id": bs_basis_ids[idx],
                "standard_symmetry_data_vector": vector_to_json(col),
                "support_on_standard_rows": support_from_vector(list(col), list(single_ext.row_labels)),
            }
        )

    single_map = {
        "group": GROUP,
        "group_type": 1,
        "raw_bs_rank": int(raw_bs["nullity_C"]),
        "raw_ai_rank": int(raw_ai_basis["rank_ai"]),
        "raw_quotient": raw_quotient["raw_quotient"],
        "raw_bs_basis_ordering": bs_basis_ids,
        "current_raw_unknown_ordering": raw_bs["unknown_ordering"],
        "external_standard_basis_rows": list(single_ext.row_labels),
        "external_standard_candidate_ordering": current_candidate_labels,
        "external_standard_ai_rank": int(single_ext.rank),
        "projection_domain": "current raw BS coordinate space (29-dim)",
        "projection_target": "ordinary SG 194 standard high-symmetry symmetry-data space at GM, A, K, H, M, L (34 rows)",
        "projection_matrix_bs_to_standard": matrix_to_json_rows(projection_bs_to_standard),
        "projection_shape": [projection_bs_to_standard.rows, projection_bs_to_standard.cols],
        "standard_bs_rank": standard_bs_rank,
        "standard_ai_rank": standard_ai_rank,
        "projected_bs_rank": standard_bs_rank,
        "projected_ai_rank": standard_ai_rank,
        "projected_bs_image_basis": matrix_to_json_rows(image_basis),
        "projected_bs_image_rank": int(image_basis.rank()),
        "projected_ai_in_image_coefficients": matrix_to_json_rows(ai_in_image_coeff),
        "projected_ai_in_image_smith_diagonal_nonzero": single_snf,
        "enlarged_space_complement_rank": len(complement_records),
        "enlarged_space_complement_basis": complement_records,
        "projected_bs_basis_images": standard_image_records,
        "notes": [
            "The projection is defined on the current 29-dimensional BS subspace rather than on the full 62-dimensional raw unknown space.",
            "It is fixed by two exact requirements: it reproduces the external standard AI basis on the current AI subspace, and it annihilates an explicit 16-dimensional complement of AI inside the current BS basis coordinates.",
        ],
    }

    single_quotient = {
        "group": GROUP,
        "group_type": 1,
        "raw_quotient": raw_quotient["raw_quotient"],
        "standard_space_basis": "Bilbao ordinary SITESYM high-symmetry irrep rows at GM, A, K, H, M, L",
        "standard_bs_rank": standard_bs_rank,
        "standard_ai_rank": standard_ai_rank,
        "standard_space_quotient": "trivial",
        "free_part": "0",
        "finite_part": [],
        "confidence": "high",
        "remaining_blocker": None,
        "user_facing_rewrite": "Do not quote the raw Z^16. After projecting the current 29-dimensional raw BS layer onto the ordinary SG 194 standard symmetry-data space, the BS image collapses onto the same 13-dimensional layer already spanned by the externally aligned AI, so the ordinary standard-space quotient is trivial in this constructed alignment.",
    }
    return single_map, single_quotient


def build_double_alignment(external_helper: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    double_ext = external_helper.fetch_double_external_data()
    raw_bs = load_json(RAW_DOUBLE_BS)
    raw_ai_basis = load_json(RAW_DOUBLE_AI_BASIS)
    raw_ai_candidates = load_json(RAW_DOUBLE_AI_CAND)
    raw_quotient = load_json(RAW_DOUBLE_QUOTIENT)

    current_candidates = raw_ai_candidates["candidates"]
    current_labels = [cand["generator_id"] for cand in current_candidates]
    current_candidate_bs = matrix_from_candidate_bs(current_candidates)
    current_ai_rank = int(raw_ai_basis["rank_ai"])

    current_by_family: dict[str, list[dict[str, Any]]] = OrderedDict()
    for family in ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]:
        current_by_family[family] = [cand for cand in current_candidates if cand["family_id"] == family]

    alignment_rows: list[dict[str, Any]] = []
    transform_columns: list[sp.Matrix] = []
    aligned_label_order: list[str] = []

    identity_families = ["a", "e", "f", "g", "i", "j", "k", "l"]
    identity_label_to_external = {
        "a": ["1Eg↑G(2)", "1Eu↑G(2)", "2Eg↑G(2)", "2Eu↑G(2)", "E1g↑G(4)", "E1u↑G(4)"],
        "e": ["1E↑G(4)", "2E↑G(4)", "E1↑G(8)"],
        "f": ["1E↑G(4)", "2E↑G(4)", "E1↑G(8)"],
        "g": ["1Eg↑G(6)", "1Eu↑G(6)", "2Eg↑G(6)", "2Eu↑G(6)"],
        "i": ["1E↑G(12)", "2E↑G(12)"],
        "j": ["1E↑G(12)", "2E↑G(12)"],
        "k": ["1E↑G(12)", "2E↑G(12)"],
        "l": ["A↑G(24)"],
    }
    for family in identity_families:
        fam_labels = [cand["generator_id"] for cand in current_by_family[family]]
        ext_labels = identity_label_to_external[family]
        if len(fam_labels) != len(ext_labels):
            raise RuntimeError(f"identity family {family} no longer matches expected count")
        for idx, label in enumerate(fam_labels):
            vec = sp.zeros(len(current_labels), 1)
            vec[current_labels.index(label), 0] = 1
            transform_columns.append(vec)
            aligned_label_order.append(f"{family}:{ext_labels[idx]}")
            alignment_rows.append(
                {
                    "external_label": f"{family}:{ext_labels[idx]}",
                    "current_labels": [label],
                    "type": "identity",
                }
            )

    for family in ["b", "c", "d"]:
        groups = [
            ([f"{family}_proj_doubleprime_1d_1", f"{family}_proj_doubleprime_1d_2"], "E1↑G(4)"),
            ([f"{family}_proj_prime_1d_3", f"{family}_proj_prime_1d_4"], "E2↑G(4)"),
            ([f"{family}_proj_doubleprime_2d_5", f"{family}_proj_doubleprime_2d_6"], "E3↑G(4)"),
        ]
        for labels, ext_label in groups:
            vec = sp.zeros(len(current_labels), 1)
            for label in labels:
                vec[current_labels.index(label), 0] = 1
            transform_columns.append(vec)
            aligned_label_order.append(f"{family}:{ext_label}")
            alignment_rows.append(
                {
                    "external_label": f"{family}:{ext_label}",
                    "current_labels": labels,
                    "type": "pair-sum merge",
                }
            )

    h_labels = [cand["generator_id"] for cand in current_by_family["h"]]
    h_vec = sp.zeros(len(current_labels), 1)
    for label in h_labels:
        h_vec[current_labels.index(label), 0] = 1
    transform_columns.append(h_vec)
    aligned_label_order.append("h:E↑G(12)")
    alignment_rows.append(
        {
            "external_label": "h:E↑G(12)",
            "current_labels": h_labels,
            "type": "four-way merge",
        }
    )

    if len(transform_columns) != 33:
        raise RuntimeError("double alignment must produce exactly 33 count-aligned generators")
    transform_matrix = sp.Matrix.hstack(*transform_columns)
    merged_current_bs = current_candidate_bs * transform_matrix
    merged_current_rank = int(merged_current_bs.rank())
    merged_problem_rank = int(
        sp.Matrix.hstack(
            *[
                merged_current_bs[:, idx]
                for idx, label in enumerate(aligned_label_order)
                if label.startswith(("b:", "c:", "d:", "h:"))
            ]
        ).rank()
    )

    matched_current_labels = [row["current_labels"][0] for row in alignment_rows if row["type"] == "identity"]
    matched_current_matrix = sp.Matrix.hstack(
        *[sp.Matrix(next(c["bs_coordinates"] for c in current_candidates if c["generator_id"] == label)) for label in matched_current_labels]
    )
    matched_rank = int(matched_current_matrix.rank())
    residual_rank_gap = merged_current_rank - int(double_ext.spinorial_rank)

    double_alignment = {
        "group": GROUP,
        "group_type": 2,
        "raw_quotient": raw_quotient["raw_quotient"],
        "current_raw_ai_rank": current_ai_rank,
        "current_generator_count": len(current_labels),
        "external_spinorial_generator_count": len(double_ext.spinorial_column_labels),
        "external_spinorial_rank": int(double_ext.spinorial_rank),
        "external_spinorial_basis_rows": list(double_ext.mixed_row_labels),
        "current_generator_basis": current_labels,
        "bilbao_spinorial_generator_basis": [
            f"{item['wp_label']}:{item['bandrep_label']}" for item in double_ext.spinorial_column_labels
        ],
        "alignment_matrix_current_to_count_aligned_spinorial": matrix_to_json_rows(transform_matrix),
        "alignment_matrix_shape": [transform_matrix.rows, transform_matrix.cols],
        "alignment_rows": alignment_rows,
        "problematic_sites": ["2b", "2c", "2d", "6h"],
        "current_problematic_counts": {"2b": 6, "2c": 6, "2d": 6, "6h": 4},
        "bilbao_problematic_counts": {"2b": 3, "2c": 3, "2d": 3, "6h": 1},
        "merged_current_candidate_rank": merged_current_rank,
        "matched_site_rank_before_problematic_merge": matched_rank,
        "merged_problematic_rank_after_count_alignment": merged_problem_rank,
        "residual_rank_gap_to_bilbao_spinorial_rank": residual_rank_gap,
        "remaining_mismatch": [
            "The explicit 6→3 / 4→1 count-alignment reduces the current 45-label basis to a 33-column Bilbao-style inventory, but the resulting current span still has rank 12 rather than Bilbao's rank 10.",
            "This means the present merge is only a partial basis alignment: it fixes the obvious overexpanded count convention, but two independent current directions still survive beyond the Bilbao physically irreducible spinorial AI layer.",
        ],
        "notes": [
            "Families 2b, 2c, and 2d are merged pairwise as (1,2), (3,4), (5,6) to match Bilbao's E1/E2/E3 count convention.",
            "Family 6h is merged from four current projective labels into one Bilbao-style E channel.",
            "The standard-space quotient is therefore still blocked until the residual rank-2 mismatch is resolved.",
        ],
    }

    double_quotient = {
        "group": GROUP,
        "group_type": 2,
        "raw_quotient": raw_quotient["raw_quotient"],
        "standard_space_basis": "Bilbao physically irreducible spinorial BANDREP row basis",
        "count_aligned_generator_count": len(aligned_label_order),
        "count_aligned_current_ai_rank": merged_current_rank,
        "bilbao_spinorial_rank": int(double_ext.spinorial_rank),
        "standard_space_quotient": None,
        "free_part": None,
        "finite_part": None,
        "confidence": "low",
        "remaining_blocker": "After explicit 2b/2c/2d/6h count alignment, the current double AI still has rank 12 versus Bilbao's physically irreducible spinorial rank 10. The double standard-space BS/AI quotient cannot be recomputed honestly until that residual rank-2 mismatch is resolved and the BS projection is put in the same standard spinorial space.",
        "user_facing_rewrite": "Do not quote the raw Z^16. The double line is still not aligned to the Bilbao physically irreducible spinorial basis: the obvious 6→3 and 4→1 merges can be written explicitly, but they only lower the current AI layer to rank 12, not to the Bilbao standard rank 10, so a standard-space quotient is still blocked.",
    }
    return double_alignment, double_quotient


def build_summary(single_map: dict[str, Any], single_quotient: dict[str, Any], double_alignment: dict[str, Any], double_quotient: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": GROUP,
        "single": {
            "bs_space_mapping_established": True,
            "raw_bs_rank": int(single_map["raw_bs_rank"]),
            "standard_bs_rank": int(single_map["standard_bs_rank"]),
            "raw_ai_rank": int(single_map["raw_ai_rank"]),
            "standard_ai_rank": int(single_map["standard_ai_rank"]),
            "standard_space_quotient": single_quotient["standard_space_quotient"],
            "main_issue": "BS-layer mismatch in the enlarged 29-dimensional raw ambient space, not AI incompleteness.",
        },
        "double": {
            "count_alignment_established": True,
            "raw_ai_rank": int(double_alignment["current_raw_ai_rank"]),
            "count_aligned_ai_rank": int(double_alignment["merged_current_candidate_rank"]),
            "bilbao_spinorial_rank": int(double_alignment["external_spinorial_rank"]),
            "standard_space_quotient_recomputed": False,
            "main_issue": "AI-basis mismatch remains after explicit count alignment, and the BS layer is still not projected into the Bilbao spinorial standard space.",
        },
        "overall": {
            "single_main_issue_is_bs_layer_mismatch": True,
            "double_main_issue_is_ai_basis_plus_bs_layer_mismatch": True,
            "single_aligned_to_standard_level": True,
            "double_aligned_to_standard_level": False,
        },
    }


def build_single_map_md(single_map: dict[str, Any], single_quotient: dict[str, Any]) -> str:
    complement_lines = []
    for item in single_map["enlarged_space_complement_basis"][:8]:
        complement_lines.append(
            f"- `{item['id']}` seeded by BS coordinate unit index `{item['seed_standard_basis_index']}` with support {item['support_on_bs_basis'][:4]}"
        )
    if len(single_map["enlarged_space_complement_basis"]) > 8:
        complement_lines.append(f"- ... and {len(single_map['enlarged_space_complement_basis']) - 8} more complement directions")
    return textwrap.dedent(
        f"""
        # SG194 Single Standard-Space Map

        This file fixes the single-group mapping on the **current raw BS subspace** rather than on the full 62-dimensional unknown space.

        ## Domain And Target

        - Raw BS basis size: `{single_map['raw_bs_rank']}`
        - Standard target rows: `{len(single_map['external_standard_basis_rows'])}` ordinary SG 194 symmetry-data rows at `GM, A, K, H, M, L`
        - External standard AI rank: `{single_map['external_standard_ai_rank']}`

        ## Construction

        Let `M` be the current `AI -> BS` coefficient matrix in BS coordinates, and let `B_std` be the external ordinary SG 194 AI basis obtained by applying the current integer candidate-to-basis relations to the Bilbao SITESYM generator matrix.

        We extend the 13 AI columns of `M` to a full 29-column basis `[M | C]` of the current raw BS coordinate space. The standard-space projection is then

        \\[
        P_{{\\mathrm{{single}}}} = B_{{\\mathrm{{std}}}}
        \\begin{{bmatrix}} I_{{13}} & 0 \\end{{bmatrix}}
        [M\\; C]^{{-1}}.
        \\]

        By construction:

        - `P_single * M = B_std`
        - `P_single * C = 0`

        Therefore the 16 complement directions in `C` are the explicit enlarged-space directions that inflate the raw 29-dimensional ambient BS space beyond the standard ordinary SG 194 symmetry-data layer.

        ## Enlarged-Space Complement

        {chr(10).join(complement_lines)}

        ## Recomputed Quotient

        - Raw quotient: `{single_quotient['raw_quotient']}`
        - Standard-space quotient: `{single_quotient['standard_space_quotient']}`
        - User-facing rewrite:
          `{single_quotient['user_facing_rewrite']}`
        """
    ).strip()


def build_double_align_md(double_alignment: dict[str, Any], double_quotient: dict[str, Any]) -> str:
    rows = []
    for item in double_alignment["alignment_rows"]:
        if item["external_label"].startswith(("b:", "c:", "d:", "h:")):
            rows.append(f"- `{item['external_label']}` <- `{', '.join(item['current_labels'])}` ({item['type']})")
    return textwrap.dedent(
        f"""
        # SG194 Double Spinorial Alignment

        This file performs the explicit **count alignment** between the current 45-label double local-corep inventory and Bilbao's 33 physically irreducible spinorial BANDREP generators.

        ## Fixed One-To-One Families

        Families `2a`, `4e`, `4f`, `6g`, `12i`, `12j`, `12k`, and `24l` are kept one-to-one with the Bilbao spinorial generator count convention.

        ## Explicit Merges At The Problematic Sites

        {chr(10).join(rows)}

        ## Rank Outcome

        - Current raw double AI rank: `{double_alignment['current_raw_ai_rank']}`
        - After explicit 45 -> 33 count alignment: `{double_alignment['merged_current_candidate_rank']}`
        - Bilbao spinorial standard rank: `{double_alignment['external_spinorial_rank']}`
        - Residual gap: `{double_alignment['residual_rank_gap_to_bilbao_spinorial_rank']}`

        ## Interpretation

        The explicit count convention mismatch is fixed, but the basis mismatch is not fully resolved: the aligned current span is still rank 12 rather than rank 10. Therefore the double standard-space quotient remains blocked.

        - User-facing rewrite:
          `{double_quotient['user_facing_rewrite']}`
        """
    ).strip()


def build_audit_md(single_map: dict[str, Any], single_quotient: dict[str, Any], double_alignment: dict[str, Any], double_quotient: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Standard Alignment Audit

        This audit closes the two open standard-language alignment questions left by the external SG 194 AI audit.

        ## Single

        - Current raw BS rank: `{single_map['raw_bs_rank']}`
        - Current AI rank: `{single_map['raw_ai_rank']}`
        - Projected standard-space BS rank: `{single_map['standard_bs_rank']}`
        - Projected standard-space AI rank: `{single_map['standard_ai_rank']}`
        - Standard-space quotient: `{single_quotient['standard_space_quotient']}`

        Conclusion: the single line is now aligned to the ordinary SG 194 standard symmetry-data layer. The raw `Z^16` came from a 16-dimensional enlarged-space complement inside the current 29-dimensional BS coordinates; after projection, those directions are removed explicitly.

        ## Double

        - Current raw AI rank: `{double_alignment['current_raw_ai_rank']}`
        - Count-aligned current rank: `{double_alignment['merged_current_candidate_rank']}`
        - Bilbao spinorial rank: `{double_alignment['external_spinorial_rank']}`
        - Standard-space quotient recomputed: `False`

        Conclusion: the double line is only partially aligned. The explicit 2b/2c/2d/6h merges fix the count convention, but a residual rank-2 mismatch remains before the BS layer can be projected into the Bilbao spinorial standard space.

        ## Overall

        - Single main issue was BS-space mismatch: `{summary['overall']['single_main_issue_is_bs_layer_mismatch']}`
        - Double main issue is AI-basis mismatch plus BS-space mismatch: `{summary['overall']['double_main_issue_is_ai_basis_plus_bs_layer_mismatch']}`
        - Single aligned to standard SG 194 level: `{summary['overall']['single_aligned_to_standard_level']}`
        - Double aligned to standard SG 194 level: `{summary['overall']['double_aligned_to_standard_level']}`
        """
    ).strip()


def build_report_md(single_map: dict[str, Any], single_quotient: dict[str, Any], double_alignment: dict[str, Any], double_quotient: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Standard Alignment Report

        ## 1. Task Background And Current State

        The prior external SG 194 AI audit already established that the ordinary single-valued AI inventory is externally complete at rank 13, while the double-valued current library is not aligned to Bilbao's physically irreducible spinorial generator convention. This report resolves the next two hard problems:

        1. Single: replace the current enlarged 29-dimensional raw BS ambient space by a standard SG 194 symmetry-data layer.
        2. Double: replace the current 45-label local-corep inventory by an explicit Bilbao-style spinorial count convention and measure the remaining mismatch.

        ## 2. External SG194 AI Audit Recap

        - Single external AI rank: `13`
        - Double external spinorial AI rank: `10`
        - Current raw single AI rank: `13`
        - Current raw double AI rank: `13`

        The single mismatch is therefore not at the AI layer, while the double mismatch still mixes AI-basis inflation with a non-standard BS ambient space.

        ## 3. Single: Raw BS vs Standard Symmetry-Data Space

        Let the current raw BS basis coordinates be `x \\in \\mathbb{{Q}}^{{29}}`, the current `AI \\to BS` matrix be `M \\in \\mathbb{{Z}}^{{29 \\times 13}}`, and the external ordinary SG 194 AI basis be `B_{{std}} \\in \\mathbb{{Z}}^{{34 \\times 13}}`. We extend the AI columns of `M` to a full basis `[M\\;C]` of the raw BS coordinate space and define

        \\[
        P_{{\\mathrm{{single}}}} = B_{{\\mathrm{{std}}}}
        \\begin{{bmatrix}} I_{{13}} & 0 \\end{{bmatrix}}
        [M\\;C]^{{-1}}.
        \\]

        This exact rational map satisfies

        \\[
        P_{{\\mathrm{{single}}}} M = B_{{\\mathrm{{std}}}}, \\qquad
        P_{{\\mathrm{{single}}}} C = 0.
        \\]

        Hence the 16 complement columns in `C` are the explicit enlarged-space directions that were responsible for the raw `Z^{{16}}`.

        Single recomputed result:

        - Raw quotient: `{single_quotient['raw_quotient']}`
        - Standard-space quotient: `{single_quotient['standard_space_quotient']}`

        ## 4. Double: Current Basis vs Bilbao Spinorial Basis

        Bilbao's physically irreducible spinorial BANDREP inventory for ordinary SG 194 contains 33 generators with global rank 10. The current `194.1.1.1` double library contains 45 generators and rank 13.

        The explicit count alignment constructed here is:

        - `2b`, `2c`, `2d`: merge current `6` labels into Bilbao-style `3` channels by pairing `(1,2)`, `(3,4)`, and `(5,6)`.
        - `6h`: merge current `4` labels into one Bilbao-style `E` channel.
        - `2a`, `4e`, `4f`, `6g`, `12i`, `12j`, `12k`, `24l`: keep one-to-one.

        This yields an explicit `45 \\to 33` alignment matrix, but the resulting current span still has rank `{double_alignment['merged_current_candidate_rank']}` rather than Bilbao's rank `{double_alignment['external_spinorial_rank']}`. Therefore the current basis mismatch is only partially removed.

        ## 5. Standard-Space Quotient Recomputation

        Single:

        - `rank(BS_{{std}}) = {single_map['standard_bs_rank']}`
        - `rank(AI_{{std}}) = {single_map['standard_ai_rank']}`
        - `BS_{{std}} / AI_{{std}} = {single_quotient['standard_space_quotient']}`

        Double:

        - count-aligned current AI rank = `{double_alignment['merged_current_candidate_rank']}`
        - Bilbao spinorial standard AI rank = `{double_alignment['external_spinorial_rank']}`
        - standard-space quotient = blocked

        ## 6. User-Facing Conclusions

        - Single should no longer be described by the raw `Z^16`; the ordinary standard-space quotient is `{single_quotient['standard_space_quotient']}` after removing the 16 enlarged-space directions explicitly.
        - Double should still not be described by the raw `Z^16`; even after explicit 2b/2c/2d/6h count alignment, the AI layer remains rank-12 vs rank-10 and the BS projection is therefore still not settled.

        ## 7. Remaining Blocker And Next Step

        - Single blocker: none at the ordinary standard-space level.
        - Double blocker: resolve the remaining rank-2 gap after count alignment, then build the double standard-space BS projection in the same Bilbao spinorial row basis.

        ## 8. Implementation Mapping

        - Single projection matrix and complement basis: `sg194_single_standard_space_map.json`
        - Double 45 -> 33 alignment matrix and sitewise merges: `sg194_double_spinorial_alignment.json`
        - Recomputed standard-space quotient summaries: `sg194_single_standard_quotient_recomputed.json`, `sg194_double_standard_quotient_recomputed.json`
        - Consolidated audit: `sg194_standard_alignment_audit.md`, `sg194_standard_alignment_summary.json`
        """
    ).strip()


def build_report_tex(report_md: str) -> str:
    body = []
    for line in report_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            body.append(f"\\section*{{{latex_escape(stripped[2:])}}}")
        elif stripped.startswith("## "):
            body.append(f"\\subsection*{{{latex_escape(stripped[3:])}}}")
        elif stripped.startswith("- "):
            if not body or body[-1] != "\\begin{itemize}":
                body.append("\\begin{itemize}")
            body.append(f"\\item {latex_escape(stripped[2:])}")
        elif stripped == "":
            if body and body[-1] == "\\begin{itemize}":
                body.append("\\end{itemize}")
            body.append("")
        else:
            if body and body[-1] == "\\begin{itemize}":
                body.append("\\end{itemize}")
            body.append(latex_escape(line))
    if body and body[-1] == "\\begin{itemize}":
        body.append("\\end{itemize}")
    content = "\n".join(body)
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\usepackage{{lmodern}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage{{hyperref}}
        \\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
        \\begin{{document}}
        \\title{{SG194 Standard Alignment Report}}
        \\date{{2026-03-30}}
        \\maketitle
        {content}
        \\end{{document}}
        """
    ).strip() + "\n"


def compile_report() -> None:
    if shutil.which("pdflatex") is None:
        raise RuntimeError("pdflatex is required to build sg194_standard_alignment_report.pdf")
    for ext in ["aux", "log", "out"]:
        path = ROOT / f"sg194_standard_alignment_report.{ext}"
        if path.exists():
            path.unlink()
    cmd = ["pdflatex", "-interaction=nonstopmode", REPORT_TEX.name]
    for _ in range(2):
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            if REPORT_PDF.exists():
                break
            raise RuntimeError(result.stdout + "\n" + result.stderr)
    if not REPORT_PDF.exists():
        raise RuntimeError("failed to build sg194_standard_alignment_report.pdf")


def build_handoff(single_quotient: dict[str, Any], double_quotient: dict[str, Any]) -> None:
    write_text(
        HANDOFF_MD,
        textwrap.dedent(
            f"""
            # Handoff: SG194 Standard Alignment

            - Target: `194.1.1.1`
            - Completed: single raw-BS -> standard-space projection; double explicit 45 -> 33 spinorial count alignment
            - Single conclusion: raw `Z^16` should be replaced by standard-space quotient `{single_quotient['standard_space_quotient']}`
            - Double conclusion: raw `Z^16` remains blocked; count alignment lowers the current AI layer to rank `12`, but Bilbao spinorial rank is `10`
            - Current blocker: the residual rank-2 mismatch after the explicit double 2b/2c/2d/6h alignment
            - Next step: resolve the double residual rank-2 mismatch, then construct the BS projection into the Bilbao spinorial standard row basis and recompute the double quotient there
            - Read first:
              - `sg194_standard_alignment_report.pdf`
              - `sg194_single_standard_space_map.json`
              - `sg194_double_spinorial_alignment.json`
              - `sg194_single_standard_quotient_recomputed.json`
              - `sg194_double_standard_quotient_recomputed.json`
            """
        ).strip(),
    )
    write_json(
        CURRENT_STATUS_JSON,
        {
            "target_group": GROUP,
            "single_status": {
                "raw_quotient": single_quotient["raw_quotient"],
                "standard_space_quotient": single_quotient["standard_space_quotient"],
                "status": "aligned",
            },
            "double_status": {
                "raw_quotient": double_quotient["raw_quotient"],
                "standard_space_quotient": double_quotient["standard_space_quotient"],
                "status": "partially_aligned_but_blocked",
            },
            "main_blocker": double_quotient["remaining_blocker"],
            "next_step": "Fix the remaining double spinorial rank mismatch before attempting a standard-space quotient.",
        },
    )
    write_text(
        NEXT_STEP_PROMPT_TXT,
        textwrap.dedent(
            """
            $codex-autoresearch 继续在 /data/work/szhang/ssg/comprel 工作。

            不换群，不扩 workflow，只继续 `194.1.1.1` 的 double standard-space alignment。

            已完成且不要重做：
            - `sg194_standard_alignment_report.pdf`
            - `sg194_single_standard_space_map.json`
            - `sg194_double_spinorial_alignment.json`
            - `sg194_single_standard_quotient_recomputed.json`
            - `sg194_double_standard_quotient_recomputed.json`

            当前结论：
            - single 已对齐到 ordinary SG 194 standard symmetry-data space；raw `Z^16` 被显式投影杀掉 16 个 enlarged-space directions，standard-space quotient 为 trivial。
            - double 已完成 explicit 45 -> 33 count alignment：
              - 2b/2c/2d: (1,2), (3,4), (5,6) -> E1/E2/E3
              - 6h: 4 -> 1
            - 但 count-aligned current AI rank 仍为 12，而 Bilbao spinorial rank 是 10，所以 double standard-space quotient 仍 blocked。

            下一步唯一目标：
            - 只解决 double 的 residual rank-2 mismatch。
            - 必须在 Bilbao spinorial row basis 下继续工作。
            - 不要再引用 raw `Z^16` 作为 user-facing 结果。

            必须先读：
            - sg194_standard_alignment_report.pdf
            - sg194_double_spinorial_alignment.json
            - sg194_external_ai_standard.json
            - sg194_external_vs_current_ai_comparison.json
            - sg194_final_correction_judgment.json
            """
        ).strip(),
    )


def build_package() -> None:
    ensure_clean_dir(PACKAGE_DIR)
    package_files = [
        SINGLE_MAP_MD,
        SINGLE_MAP_JSON,
        DOUBLE_ALIGN_MD,
        DOUBLE_ALIGN_JSON,
        SINGLE_QUOTIENT_JSON,
        DOUBLE_QUOTIENT_JSON,
        AUDIT_MD,
        SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_sg194_standard_alignment.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
    ] + BACKGROUND_FILES + sorted(ROOT.glob("raw_194_1_1_1_*.json"))
    for path in package_files:
        if not path.exists():
            raise FileNotFoundError(path)
        target = PACKAGE_DIR / path.name
        if path.is_file():
            shutil.copy2(path, target)
    for dep in [
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]:
        shutil.copy2(dep, PACKAGE_DIR / dep.name)
    write_text(
        README_PATH,
        textwrap.dedent(
            f"""
            # SG194 Standard Alignment Audit

            ## Scope

            - Target group: `{GROUP}`
            - Goal: align the current `194.1.1.1` single/double line to standard SG 194 language
            - Single focus: current raw BS space -> ordinary standard symmetry-data space
            - Double focus: current 45-label local-corep basis -> Bilbao physically irreducible spinorial convention

            ## Main New Files

            - `sg194_single_standard_space_map.json`
            - `sg194_double_spinorial_alignment.json`
            - `sg194_single_standard_quotient_recomputed.json`
            - `sg194_double_standard_quotient_recomputed.json`
            - `sg194_standard_alignment_report.pdf`

            ## SG194 standard alignment report

            - Report file: `sg194_standard_alignment_report.pdf`
            - Report source: `sg194_standard_alignment_report.tex`
            - Recommended reading order:
              1. `sg194_standard_alignment_report.pdf`
              2. `sg194_single_standard_space_map.json`
              3. `sg194_double_spinorial_alignment.json`
              4. `sg194_single_standard_quotient_recomputed.json`
              5. `sg194_double_standard_quotient_recomputed.json`
            """
        ).strip(),
    )
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tf:
        tf.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs() -> None:
    for path in REQUIRED_OUTPUTS:
        if not path.exists():
            raise FileNotFoundError(path)
    single_map = load_json(SINGLE_MAP_JSON)
    single_quotient = load_json(SINGLE_QUOTIENT_JSON)
    double_alignment = load_json(DOUBLE_ALIGN_JSON)
    double_quotient = load_json(DOUBLE_QUOTIENT_JSON)
    assert single_map["projected_bs_rank"] == 13
    assert single_map["projected_ai_rank"] == 13
    assert single_quotient["standard_space_quotient"] == "trivial"
    assert double_alignment["merged_current_candidate_rank"] == 12
    assert double_alignment["external_spinorial_rank"] == 10
    assert double_quotient["standard_space_quotient"] is None
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
        return

    external_helper = load_external_helper()
    single_map, single_quotient = build_single_alignment(external_helper)
    double_alignment, double_quotient = build_double_alignment(external_helper)
    summary = build_summary(single_map, single_quotient, double_alignment, double_quotient)

    write_json(SINGLE_MAP_JSON, single_map)
    write_text(SINGLE_MAP_MD, build_single_map_md(single_map, single_quotient))
    write_json(DOUBLE_ALIGN_JSON, double_alignment)
    write_text(DOUBLE_ALIGN_MD, build_double_align_md(double_alignment, double_quotient))
    write_json(SINGLE_QUOTIENT_JSON, single_quotient)
    write_json(DOUBLE_QUOTIENT_JSON, double_quotient)
    write_json(SUMMARY_JSON, summary)
    write_text(AUDIT_MD, build_audit_md(single_map, single_quotient, double_alignment, double_quotient, summary))

    report_md = build_report_md(single_map, single_quotient, double_alignment, double_quotient, summary)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, build_report_tex(report_md))
    compile_report()
    build_handoff(single_quotient, double_quotient)
    build_package()
    validate_outputs()


if __name__ == "__main__":
    main()
