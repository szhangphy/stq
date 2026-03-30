#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent
GROUP = "194.1.1.1"

RAW_SINGLE_AI_CAND = ROOT / "raw_194_1_1_1_single_ai_candidates.json"
RAW_SINGLE_AI_BASIS = ROOT / "raw_194_1_1_1_single_ai_basis.json"
RAW_SINGLE_BS = ROOT / "raw_194_1_1_1_single_bs_basis_raw.json"
RAW_SINGLE_C = ROOT / "raw_194_1_1_1_single_C.json"
RAW_DOUBLE_AI_CAND = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_DOUBLE_AI_BASIS = ROOT / "raw_194_1_1_1_double_ai_basis.json"
RAW_DOUBLE_BS = ROOT / "raw_194_1_1_1_double_bs_basis_raw.json"
RAW_DOUBLE_C = ROOT / "raw_194_1_1_1_double_C.json"

EXT_ORD_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"
EXT_SPIN_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"
OLD_SINGLE_FINAL_JSON = ROOT / "sg194_single_final_external_reduction.json"
OLD_DOUBLE_FINAL_JSON = ROOT / "sg194_double_final_external_reduction.json"
OLD_FINAL_SUMMARY_JSON = ROOT / "sg194_external_matrix_final_summary.json"
OLD_SINGLE_V2_JSON = ROOT / "sg194_single_standard_quotient_recomputed_v2.json"
OLD_SINGLE_MAP_JSON = ROOT / "sg194_single_external_rowspace_projection.json"
OLD_DOUBLE_V2_JSON = ROOT / "sg194_double_standard_quotient_recomputed_v2.json"
OLD_DOUBLE_ALIGN_JSON = ROOT / "sg194_double_repcontent_alignment.json"

SINGLE_AI_JSON = ROOT / "sg194_single_ai_vs_external.json"
SINGLE_BS_JSON = ROOT / "sg194_single_bs_vs_external.json"
SINGLE_AUDIT_MD = ROOT / "sg194_single_separated_audit.md"
DOUBLE_AI_JSON = ROOT / "sg194_double_ai_vs_external.json"
DOUBLE_BS_JSON = ROOT / "sg194_double_bs_vs_external.json"
DOUBLE_AUDIT_MD = ROOT / "sg194_double_separated_audit.md"
AUDIT_MD = ROOT / "sg194_bs_ai_separation_audit.md"
SUMMARY_JSON = ROOT / "sg194_bs_ai_separation_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_bs_ai_separation.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_bs_ai_separation.json"
NEXT_STEP_TXT = ROOT / "next_step_prompt_sg194_bs_ai_separation.txt"
REPORT_MD = ROOT / "sg194_bs_ai_separation_report.md"
REPORT_TEX = ROOT / "sg194_bs_ai_separation_report.tex"
REPORT_PDF = ROOT / "sg194_bs_ai_separation_report.pdf"

PACKAGE_NAME = "review_package_sg194_bs_ai_separation_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

VERIFY_CMD = "python3 -u debug_sg194_bs_ai_separation.py --validate"
GUARD_CMD = "python3 -u debug_sg194_external_matrix_final.py --validate && python3 -u debug_sg194_standard_alignment_v2.py --validate"

RESEARCH_RESULTS_TSV = ROOT / "research-results-bs-ai-separation.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-bs-ai-separation.json"

POINT_BLOCKS = [("P1", "GM"), ("P2", "A"), ("P3", "K"), ("P5", "M"), ("P6", "L"), ("B1", "H")]

BACKGROUND_FILES = [
    EXT_ORD_JSON,
    EXT_SPIN_JSON,
    OLD_SINGLE_FINAL_JSON,
    OLD_DOUBLE_FINAL_JSON,
    OLD_FINAL_SUMMARY_JSON,
    RAW_SINGLE_AI_CAND,
    RAW_SINGLE_AI_BASIS,
    RAW_SINGLE_BS,
    RAW_SINGLE_C,
    RAW_DOUBLE_AI_CAND,
    RAW_DOUBLE_AI_BASIS,
    RAW_DOUBLE_BS,
    RAW_DOUBLE_C,
    ROOT / "raw_194_1_1_1_single_bs_basis_pretty.json",
    ROOT / "raw_194_1_1_1_double_bs_basis_pretty.json",
    ROOT / "swyckoff_r.py",
    ROOT / "swyckoff_k.py",
    ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
    ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
]

REQUIRED_OUTPUTS = [
    SINGLE_AI_JSON,
    SINGLE_BS_JSON,
    SINGLE_AUDIT_MD,
    DOUBLE_AI_JSON,
    DOUBLE_BS_JSON,
    DOUBLE_AUDIT_MD,
    AUDIT_MD,
    SUMMARY_JSON,
    HANDOFF_MD,
    CURRENT_STATUS_JSON,
    NEXT_STEP_TXT,
    ROOT / "debug_sg194_bs_ai_separation.py",
    REPORT_PDF,
    REPORT_TEX,
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


def serialize_entry(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return str(value)
        return str(sp.simplify(value))
    if isinstance(value, list):
        return [serialize_entry(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_entry(val) for key, val in value.items()}
    return value


def matrix_to_rows(matrix: sp.Matrix) -> list[list[Any]]:
    return [[serialize_entry(matrix[i, j]) for j in range(matrix.cols)] for i in range(matrix.rows)]


def support_from_dense(vec: list[Any], labels: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, coeff in zip(labels, vec):
        coeff_s = serialize_entry(coeff)
        if coeff_s in [0, "0"]:
            continue
        out.append({"label": label, "coeff": coeff_s})
    return out


def selection_indices(unknown_ordering: list[str], block_ids: list[str]) -> list[int]:
    return [idx for idx, label in enumerate(unknown_ordering) if any(label.startswith(f"{block}_") for block in block_ids)]


def selection_matrix(total_dim: int, chosen: list[int]) -> sp.Matrix:
    rows = []
    for idx in chosen:
        row = [0] * total_dim
        row[idx] = 1
        rows.append(row)
    return sp.Matrix(rows)


def matrix_from_records(records: list[dict[str, Any]], key: str, chosen_idx: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([record[key][i] for i in chosen_idx]) for record in records])


def rowspace_basis_matrix(matrix: sp.Matrix) -> sp.Matrix:
    basis = matrix.rowspace()
    return sp.Matrix.vstack(*basis) if basis else sp.zeros(0, matrix.cols)


def columnspace_basis_matrix(matrix: sp.Matrix) -> sp.Matrix:
    basis = matrix.columnspace()
    return sp.Matrix.hstack(*basis) if basis else sp.zeros(matrix.rows, 0)


def subset_in_rowspace(test: sp.Matrix, container: sp.Matrix) -> bool:
    return sp.Matrix.vstack(container, test).rank() == container.rank()


def subset_in_colspace(test: sp.Matrix, container: sp.Matrix) -> bool:
    return sp.Matrix.hstack(container, test).rank() == container.rank()


def rowspace_difference_basis(current: sp.Matrix, external: sp.Matrix, column_labels: list[str]) -> list[dict[str, Any]]:
    ext_basis = rowspace_basis_matrix(external)
    cur_basis = rowspace_basis_matrix(current)
    span = ext_basis
    extra: list[dict[str, Any]] = []
    for idx in range(cur_basis.rows):
        row = cur_basis[idx, :]
        trial = sp.Matrix.vstack(span, row) if span.rows else sp.Matrix([list(row)])
        if trial.rank() > span.rank():
            extra.append(
                {
                    "id": f"current_row_extra_{len(extra)+1:02d}",
                    "vector_on_generator_domain": [serialize_entry(val) for val in list(row)],
                    "support_on_generator_labels": support_from_dense(list(row), column_labels),
                }
            )
            span = trial
    return extra


def colspace_difference_basis(
    current: sp.Matrix,
    external: sp.Matrix,
    current_row_labels: list[str],
    external_row_labels: list[str],
) -> list[dict[str, Any]]:
    ext_basis = columnspace_basis_matrix(external)
    cur_basis = columnspace_basis_matrix(current)
    span = ext_basis
    extra: list[dict[str, Any]] = []
    for idx in range(cur_basis.cols):
        col = cur_basis[:, idx]
        trial = span.row_join(col) if span.cols else sp.Matrix(col)
        if trial.rank() > span.rank():
            dense = list(col)
            extra.append(
                {
                    "id": f"current_col_extra_{len(extra)+1:02d}",
                    "vector_on_34_point_space": [serialize_entry(val) for val in dense],
                    "support_on_current_hsp_labels": support_from_dense(dense, current_row_labels),
                    "support_on_external_row_labels_by_position": support_from_dense(dense, external_row_labels),
                }
            )
            span = trial
    return extra


def row_position_matching(current_labels: list[str], external_labels: list[str]) -> list[dict[str, Any]]:
    return [{"position": idx, "current_hsp_label": cur, "external_row_label": ext} for idx, (cur, ext) in enumerate(zip(current_labels, external_labels))]


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


def compile_pdf() -> None:
    if shutil.which("pdflatex") is None:
        raise RuntimeError("pdflatex is required to build sg194_bs_ai_separation_report.pdf")
    cmd = ["pdflatex", "-interaction=nonstopmode", REPORT_TEX.name]
    for _ in range(2):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if not REPORT_PDF.exists():
        raise RuntimeError("pdflatex did not produce sg194_bs_ai_separation_report.pdf")
    for suffix in [".aux", ".log", ".out"]:
        aux = REPORT_TEX.with_suffix(suffix)
        if aux.exists():
            aux.unlink()


def build_single_ai_vs_external() -> dict[str, Any]:
    raw_c = load_json(RAW_SINGLE_C)
    raw_ai_cand = load_json(RAW_SINGLE_AI_CAND)
    raw_ai_basis = load_json(RAW_SINGLE_AI_BASIS)
    external = load_json(EXT_ORD_JSON)

    idx = selection_indices(raw_c["unknown_ordering"], [item[0] for item in POINT_BLOCKS])
    current_hsp_labels = [raw_c["unknown_ordering"][i] for i in idx]
    sel = selection_matrix(len(raw_c["unknown_ordering"]), idx)

    current_labels = [cand["generator_id"] for cand in raw_ai_cand["candidates"]]
    ext_labels = external["column_labels"]
    perm = [ext_labels.index(label) for label in current_labels]
    ext_matrix = sp.Matrix(external["matrix_entries"])[:, perm]

    ai_candidate_hsp = sel * matrix_from_records(raw_ai_cand["candidates"], "unknown_vector", list(range(len(raw_c["unknown_ordering"]))))
    ai_basis_hsp = sel * matrix_from_records(raw_ai_basis["basis_vectors"], "vector", list(range(len(raw_c["unknown_ordering"]))))

    current_rank = int(ai_candidate_hsp.rank())
    ext_rank = int(ext_matrix.rank())
    union_rank = int(sp.Matrix.vstack(ai_candidate_hsp, ext_matrix).rank())
    intersection_rank = current_rank + ext_rank - union_rank

    payload = {
        "group": GROUP,
        "group_type": 1,
        "comparison_kind": "AI-only",
        "compared_objects": {
            "current": "current single AI candidate image restricted to the 34-row HSP point space",
            "external": "external ordinary 34x45 generator matrix from Bilbao SITESYM, columns reordered by exact generator ids",
        },
        "ambient_domain": "45-generator domain after exact generator-id reordering",
        "current_unknown_ordering": raw_c["unknown_ordering"],
        "current_hsp_labels": current_hsp_labels,
        "external_row_labels": external["row_labels"],
        "generator_ordering": current_labels,
        "current_hsp_ai_candidate_matrix_shape": [int(ai_candidate_hsp.rows), int(ai_candidate_hsp.cols)],
        "current_hsp_ai_basis_matrix_shape": [int(ai_basis_hsp.rows), int(ai_basis_hsp.cols)],
        "current_ai_candidate_rank": current_rank,
        "current_ai_basis_rank": int(ai_basis_hsp.rank()),
        "external_generator_matrix_shape": external["shape"],
        "external_generator_rank": ext_rank,
        "rowspace_union_rank": union_rank,
        "rowspace_intersection_rank": intersection_rank,
        "exact_rowspace_identification_exists": union_rank == current_rank == ext_rank,
        "current_rowspace_subset_of_external": subset_in_rowspace(ai_candidate_hsp, ext_matrix),
        "external_rowspace_subset_of_current": subset_in_rowspace(ext_matrix, ai_candidate_hsp),
        "mismatch_is_one_dimensional": union_rank - max(current_rank, ext_rank) == 1,
        "current_only_rowspace_basis": rowspace_difference_basis(ai_candidate_hsp, ext_matrix, current_labels),
        "external_only_rowspace_basis": rowspace_difference_basis(ext_matrix, ai_candidate_hsp, current_labels),
        "diagnosis": (
            "Current single AI is not identical to the external ordinary AI generator image. Both spaces have rank 13, "
            "but their union has rank 14 and intersection rank 12, so the mismatch is exactly one-dimensional in the 45-generator domain."
        ),
    }
    return payload


def build_single_bs_vs_external() -> dict[str, Any]:
    raw_c = load_json(RAW_SINGLE_C)
    raw_bs = load_json(RAW_SINGLE_BS)
    raw_ai_basis = load_json(RAW_SINGLE_AI_BASIS)
    external = load_json(EXT_ORD_JSON)
    single_map = load_json(OLD_SINGLE_MAP_JSON)
    single_v2 = load_json(OLD_SINGLE_V2_JSON)

    idx = selection_indices(raw_c["unknown_ordering"], [item[0] for item in POINT_BLOCKS])
    current_hsp_labels = [raw_c["unknown_ordering"][i] for i in idx]
    external_rows = external["row_labels"]
    assert len(current_hsp_labels) == len(external_rows)

    bs_hsp = matrix_from_records(raw_bs["basis_vectors"], "vector", idx)
    ai_hsp = matrix_from_records(raw_ai_basis["basis_vectors"], "vector", idx)
    ext_matrix = sp.Matrix(external["matrix_entries"])

    current_rank = int(bs_hsp.rank())
    external_rank = int(ext_matrix.rank())
    union_rank = int(sp.Matrix.hstack(bs_hsp, ext_matrix).rank())
    intersection_rank = current_rank + external_rank - union_rank

    payload = {
        "group": GROUP,
        "group_type": 1,
        "comparison_kind": "BS-only",
        "compared_objects": {
            "current": "current single BS basis projected to the 34-row HSP point space",
            "external": "external ordinary standard symmetry-data span, represented by the 34x45 Bilbao ordinary generator matrix",
        },
        "ambient_domain": "34-row point-space after the non-AI-anchored HSP restriction from v2",
        "current_hsp_labels": current_hsp_labels,
        "external_row_labels": external_rows,
        "row_position_matching": row_position_matching(current_hsp_labels, external_rows),
        "projection_notes": single_map["notes"],
        "current_bs_image_shape": [int(bs_hsp.rows), int(bs_hsp.cols)],
        "current_bs_image_rank": current_rank,
        "current_ai_image_rank_in_same_point_space": int(ai_hsp.rank()),
        "external_span_shape": external["shape"],
        "external_span_rank": external_rank,
        "columnspace_union_rank": union_rank,
        "columnspace_intersection_rank": intersection_rank,
        "exact_space_identification_exists": union_rank == current_rank == external_rank,
        "current_space_subset_of_external": subset_in_colspace(bs_hsp, ext_matrix),
        "external_space_subset_of_current": subset_in_colspace(ext_matrix, bs_hsp),
        "current_only_dimension_over_external": current_rank - intersection_rank,
        "external_only_dimension_over_current": external_rank - intersection_rank,
        "current_only_bs_directions": colspace_difference_basis(bs_hsp, ext_matrix, current_hsp_labels, external_rows),
        "external_only_standard_directions": colspace_difference_basis(ext_matrix, bs_hsp, external_rows, external_rows),
        "relation_to_v2_internal_point_space_gap": {
            "v2_point_space_quotient": single_v2["current_hsp_point_space_quotient"],
            "v2_current_hsp_point_space_bs_rank": single_v2["current_hsp_point_space_bs_rank"],
            "v2_current_hsp_point_space_ai_rank": single_v2["current_hsp_point_space_ai_rank"],
            "meaning": "The old Z^5 is only the current internal BS/AI gap inside the 34-row point space. The new BS-vs-external comparison shows a much larger mismatch against the external ordinary standard span.",
        },
        "diagnosis": (
            "Current single BS is not aligned with the external ordinary standard symmetry-data span. In the same 34-row point-space ambient, "
            "the current BS image has rank 18 while the external span has rank 13; their union rank is 26 and intersection rank is only 5."
        ),
    }
    return payload


def build_double_ai_vs_external() -> dict[str, Any]:
    raw_c = load_json(RAW_DOUBLE_C)
    raw_ai_cand = load_json(RAW_DOUBLE_AI_CAND)["candidates"]
    raw_ai_basis = load_json(RAW_DOUBLE_AI_BASIS)
    ext_spin = load_json(EXT_SPIN_JSON)
    align = load_json(OLD_DOUBLE_ALIGN_JSON)
    old_final = load_json(OLD_DOUBLE_FINAL_JSON)

    idx = selection_indices(raw_c["unknown_ordering"], [item[0] for item in POINT_BLOCKS])
    current_hsp_labels = [raw_c["unknown_ordering"][i] for i in idx]

    current_ai_basis_hsp = matrix_from_records(raw_ai_basis["basis_vectors"], "vector", idx)
    by_id = {cand["generator_id"]: cand for cand in raw_ai_cand}

    merged_labels: list[str] = []
    merged_cols: list[sp.Matrix] = []
    for channel in align["merged_channels"]:
        label = channel["external_channel_label"]
        vec = sp.zeros(len(idx), 1)
        for gid in channel["current_generators"]:
            cand = by_id[gid]
            vec += sp.Matrix([cand["unknown_vector"][i] for i in idx])
        merged_labels.append(label)
        merged_cols.append(vec)
    merged_matrix = sp.Matrix.hstack(*merged_cols)

    ext_problem_indices = [
        i
        for i, item in enumerate(ext_spin["column_labels"])
        if item["wp_label"] in {"2b", "2c", "2d", "6h"}
    ]
    ext_problem = sp.Matrix(ext_spin["matrix_entries"])[:, ext_problem_indices]
    problem_labels = [merged_labels[i] for i, label in enumerate(merged_labels) if label.startswith(("b:", "c:", "d:")) or label == "h:E"]
    current_problem_indices = [merged_labels.index(label) for label in problem_labels]
    current_problem = merged_matrix[:, current_problem_indices]
    union_rank = int(sp.Matrix.vstack(current_problem, ext_problem).rank())
    intersection_rank = int(current_problem.rank() + ext_problem.rank() - union_rank)

    payload = {
        "group": GROUP,
        "group_type": 2,
        "comparison_kind": "AI-only",
        "compared_objects": {
            "current": "current double AI after v2 representation-content merging on the 34-row current HSP point space",
            "external": "external Bilbao physically irreducible spinorial 56x33 generator matrix",
        },
        "current_hsp_row_labels": current_hsp_labels,
        "external_spinorial_row_labels": ext_spin["row_labels"],
        "current_raw_ai_basis_rank": int(current_ai_basis_hsp.rank()),
        "current_raw_candidate_rank_in_hsp_space": int(matrix_from_records(raw_ai_cand, "unknown_vector", idx).rank()),
        "current_45_to_33_alignment_status": {
            "status": "partial",
            "completed_exactly_for": "problematic 2b/2c/2d/6h sector via representation-content merging",
            "not_canonical_yet_for": "identity sectors with matched counts but no fixed per-label Bilbao naming map",
            "count_aligned_rank": int(merged_matrix.rank()),
        },
        "external_spinorial_generator_rank": int(sp.Matrix(ext_spin["matrix_entries"]).rank()),
        "global_union_rank": None,
        "global_intersection_rank": None,
        "global_exact_identification_exists": False,
        "global_reason": "A full canonical 33-column current-to-Bilbao label identification outside the explicit problem sector is still not fixed.",
        "problem_sector_labels": problem_labels,
        "problem_sector_current_rank": int(current_problem.rank()),
        "problem_sector_external_rank": int(ext_problem.rank()),
        "problem_sector_union_rank": union_rank,
        "problem_sector_intersection_rank": intersection_rank,
        "delta_c1_minus_b1_classification": "current-only AI excess direction inside the problem-sector generator image",
        "delta_d1_minus_b1_classification": "current-only AI excess direction inside the problem-sector generator image",
        "delta_basis_from_v2": align["residual_rank_gap_basis"],
        "problem_sector_current_only_basis": old_final["current_only_problem_sector_basis"],
        "problem_sector_external_only_basis": old_final["external_only_problem_sector_basis"],
        "diagnosis": (
            "Double AI is genuinely misaligned with the external spinorial generator language in the explicit 2b/2c/2d/6h problem sector. "
            "Both current merged and external problem-sector row spaces have rank 6, but their union has rank 8 and intersection rank 4."
        ),
    }
    return payload


def build_double_bs_vs_external() -> dict[str, Any]:
    raw_c = load_json(RAW_DOUBLE_C)
    raw_bs = load_json(RAW_DOUBLE_BS)
    raw_ai_basis = load_json(RAW_DOUBLE_AI_BASIS)
    ext_spin = load_json(EXT_SPIN_JSON)
    align = load_json(OLD_DOUBLE_ALIGN_JSON)

    idx = selection_indices(raw_c["unknown_ordering"], [item[0] for item in POINT_BLOCKS])
    current_hsp_labels = [raw_c["unknown_ordering"][i] for i in idx]
    bs_hsp = matrix_from_records(raw_bs["basis_vectors"], "vector", idx)
    ai_hsp = matrix_from_records(raw_ai_basis["basis_vectors"], "vector", idx)

    current_extra_over_ai = load_json(OLD_SINGLE_MAP_JSON)["current_hsp_extra_directions_over_ai"]

    payload = {
        "group": GROUP,
        "group_type": 2,
        "comparison_kind": "BS-only",
        "compared_objects": {
            "current": "current double BS basis projected to the 34-row current HSP point space",
            "external": "external spinorial standard row-space language",
        },
        "current_hsp_labels": current_hsp_labels,
        "external_spinorial_row_labels": ext_spin["row_labels"],
        "current_bs_image_shape": [int(bs_hsp.rows), int(bs_hsp.cols)],
        "current_bs_image_rank_in_current_hsp_space": int(bs_hsp.rank()),
        "current_ai_image_rank_in_same_hsp_space": int(ai_hsp.rank()),
        "external_spinorial_generator_matrix_shape": ext_spin["shape"],
        "external_spinorial_generator_rank": int(sp.Matrix(ext_spin["matrix_entries"]).rank()),
        "union_rank": None,
        "intersection_rank": None,
        "exact_lift_to_external_spinorial_row_space_exists": False,
        "bs_only_comparison_status": "blocked",
        "blocker": (
            "A BS-only external comparison cannot yet be completed. The cached external spinorial object is a generator matrix in a 56-row Bilbao basis, "
            "whereas the current BS basis lives in a 34-row current point-space after restriction. No BS-only lift from the current 34-row point coordinates "
            "to the 56-row Bilbao spinorial basis is available without reusing AI/generator alignment machinery."
        ),
        "what_is_still_known_locally": {
            "current_hsp_extra_bs_over_current_ai_rank": int(bs_hsp.rank() - ai_hsp.rank()),
            "current_hsp_extra_bs_over_current_ai_basis": current_extra_over_ai,
            "relation_to_problem_sector_ai_blocker": align["residual_rank_gap_basis"],
        },
        "diagnosis": (
            "Previous external_matrix_final did not establish a BS-space mismatch for double. After separating objects correctly, the BS-only external comparison is still blocked; "
            "the currently proven issue is at the AI/generator alignment layer."
        ),
    }
    return payload


def build_single_audit_md(ai_payload: dict[str, Any], bs_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 Single Separated Audit",
            "",
            "## Previous Mis-attribution",
            "- The previous `external_matrix_final` single line compared current AI candidates with the external ordinary generator matrix.",
            "- That comparison could certify an AI-image mismatch, but it could not by itself certify a BS-space mismatch.",
            "",
            "## AI-only Result",
            f"- Current AI candidate rank: `{ai_payload['current_ai_candidate_rank']}`",
            f"- External ordinary generator rank: `{ai_payload['external_generator_rank']}`",
            f"- Union rank in the 45-generator domain: `{ai_payload['rowspace_union_rank']}`",
            f"- Intersection rank: `{ai_payload['rowspace_intersection_rank']}`",
            f"- Exact identification exists: `{ai_payload['exact_rowspace_identification_exists']}`",
            "",
            "## BS-only Result",
            f"- Current projected BS rank: `{bs_payload['current_bs_image_rank']}`",
            f"- External ordinary span rank: `{bs_payload['external_span_rank']}`",
            f"- Union rank in the 34-row point space: `{bs_payload['columnspace_union_rank']}`",
            f"- Intersection rank: `{bs_payload['columnspace_intersection_rank']}`",
            f"- Exact space identification exists: `{bs_payload['exact_space_identification_exists']}`",
            "",
            "## Final Diagnosis",
            "- Single has both an AI mismatch and a BS mismatch.",
            "- The AI mismatch is one-dimensional in the 45-generator domain.",
            "- The BS mismatch is much stronger: the current projected BS image and the external ordinary span intersect in only rank 5 inside the 34-row point-space ambient.",
            "- The old `trivial` conclusion must stay retired.",
            "- The old `Z^5` is only an internal point-space BS/AI diagnostic, not a final external quotient.",
            "- The old raw `Z^16` remains a raw quotient and is not a standard-space result.",
        ]
    )


def build_double_audit_md(ai_payload: dict[str, Any], bs_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 Double Separated Audit",
            "",
            "## Previous Mis-attribution",
            "- The previous `external_matrix_final` double line compared current merged AI/generator content with the external spinorial generator matrix, mainly in the 2b/2c/2d/6h problem sector.",
            "- That comparison could certify an AI/generator mismatch, but it could not by itself certify a BS-space mismatch.",
            "",
            "## AI-only Result",
            f"- Current raw AI rank in current HSP space: `{ai_payload['current_raw_ai_basis_rank']}`",
            f"- Current merged 45->33 aligned rank: `{ai_payload['current_45_to_33_alignment_status']['count_aligned_rank']}`",
            f"- External spinorial generator rank: `{ai_payload['external_spinorial_generator_rank']}`",
            f"- Problem-sector union rank: `{ai_payload['problem_sector_union_rank']}`",
            f"- Problem-sector intersection rank: `{ai_payload['problem_sector_intersection_rank']}`",
            "",
            "## BS-only Result",
            f"- Current projected BS rank in current HSP space: `{bs_payload['current_bs_image_rank_in_current_hsp_space']}`",
            f"- Current projected AI rank in the same space: `{bs_payload['current_ai_image_rank_in_same_hsp_space']}`",
            f"- Exact lift to external spinorial BS space exists: `{bs_payload['exact_lift_to_external_spinorial_row_space_exists']}`",
            "- A BS-only external comparison is still blocked because the cached external spinorial object is an AI generator matrix in a 56-row Bilbao basis, not a BS basis/span, and no BS-only lift from the current 34-row point coordinates has been fixed.",
            "",
            "## Final Diagnosis",
            "- Double has a proven AI mismatch.",
            "- `delta_c1_minus_b1` and `delta_d1_minus_b1` are AI excess directions in the explicit problem-sector generator image.",
            "- A separate BS mismatch has not yet been honestly established by the cached data alone.",
            "- Therefore the previous external_matrix_final wording over-attributed a BS conclusion.",
        ]
    )


def build_summary_json(single_ai: dict[str, Any], single_bs: dict[str, Any], double_ai: dict[str, Any], double_bs: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_group": GROUP,
        "previous_external_matrix_final_error": "previous external_matrix_final mixed up AI-image comparison with BS-space comparison",
        "single_main_issue": "both",
        "double_main_issue": "AI",
        "single_confidence": "high",
        "double_confidence": "medium",
        "old_conclusions_to_retire": [
            "previous external_matrix_final single BS mismatch wording",
            "previous external_matrix_final double BS mismatch wording",
            "single v1 standard-space quotient = trivial",
        ],
        "updated_conclusions": {
            "single": (
                "AI-only mismatch is one-dimensional in the 45-generator domain, and BS-only mismatch is stronger in the 34-row point-space ambient "
                "(current rank 18 vs external rank 13, intersection rank 5)."
            ),
            "double": (
                "AI-only mismatch is proven in the explicit 2b/2c/2d/6h problem sector; BS-only external comparison remains blocked because no BS-only lift "
                "to the 56-row Bilbao spinorial basis has been fixed."
            ),
        },
        "single": {
            "ai_rank_current": single_ai["current_ai_candidate_rank"],
            "ai_rank_external": single_ai["external_generator_rank"],
            "ai_union_rank": single_ai["rowspace_union_rank"],
            "bs_rank_current": single_bs["current_bs_image_rank"],
            "bs_rank_external": single_bs["external_span_rank"],
            "bs_union_rank": single_bs["columnspace_union_rank"],
        },
        "double": {
            "ai_rank_current_raw": double_ai["current_raw_ai_basis_rank"],
            "ai_rank_current_merged": double_ai["current_45_to_33_alignment_status"]["count_aligned_rank"],
            "ai_rank_external": double_ai["external_spinorial_generator_rank"],
            "ai_problem_sector_union_rank": double_ai["problem_sector_union_rank"],
            "bs_comparison_status": double_bs["bs_only_comparison_status"],
        },
    }


def build_audit_md(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 BS-vs-AI Separation Audit",
            "",
            "## Previous Mis-attribution",
            "- previous external_matrix_final mixed up AI-image comparison with BS-space comparison.",
            "",
            "## Single",
            f"- Main issue: `{summary['single_main_issue']}`",
            f"- AI ranks / union: `{summary['single']['ai_rank_current']}`, `{summary['single']['ai_rank_external']}`, `{summary['single']['ai_union_rank']}`",
            f"- BS ranks / union: `{summary['single']['bs_rank_current']}`, `{summary['single']['bs_rank_external']}`, `{summary['single']['bs_union_rank']}`",
            "",
            "## Double",
            f"- Main issue: `{summary['double_main_issue']}`",
            f"- AI ranks: raw `{summary['double']['ai_rank_current_raw']}`, merged `{summary['double']['ai_rank_current_merged']}`, external `{summary['double']['ai_rank_external']}`",
            f"- AI problem-sector union rank: `{summary['double']['ai_problem_sector_union_rank']}`",
            f"- BS comparison status: `{summary['double']['bs_comparison_status']}`",
            "",
            "## Updated Conclusions",
            f"- Single: {summary['updated_conclusions']['single']}",
            f"- Double: {summary['updated_conclusions']['double']}",
        ]
    )


def build_handoff(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Handoff: SG194 BS-vs-AI Separation",
            "",
            "- Target: `194.1.1.1`",
            "- Completed: separated single/double AI-only and BS-only external comparisons",
            f"- Single diagnosis: `{summary['single_main_issue']}`",
            f"- Double diagnosis: `{summary['double_main_issue']}`",
            "- Important correction: previous external_matrix_final over-attributed BS mismatch from AI-image evidence.",
            "- Read first:",
            "  - `sg194_bs_ai_separation_report.pdf`",
            "  - `sg194_single_ai_vs_external.json`",
            "  - `sg194_single_bs_vs_external.json`",
            "  - `sg194_double_ai_vs_external.json`",
            "  - `sg194_double_bs_vs_external.json`",
            "- Next step if continuing: either build an external BS object for double, or construct a BS-only lift from the current 34-row point coordinates to the 56-row Bilbao spinorial basis without reusing AI anchoring.",
        ]
    )


def build_next_step_prompt(summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""\
        $codex-autoresearch 继续在 /data/work/szhang/ssg/comprel 工作。

        不换群，不扩 workflow。只继续 `194.1.1.1` 的 BS-vs-AI separation 之后的剩余 blocker。

        已完成且不要重做：
        - `sg194_single_ai_vs_external.json`
        - `sg194_single_bs_vs_external.json`
        - `sg194_double_ai_vs_external.json`
        - `sg194_double_bs_vs_external.json`
        - `sg194_bs_ai_separation_report.pdf`

        当前已钉死的结论：
        - previous external_matrix_final mixed up AI-image comparison with BS-space comparison.
        - single: `both`
          - AI-only mismatch: rank 13 vs 13, union rank 14, intersection 12
          - BS-only mismatch: current rank 18 vs external rank 13, union rank 26, intersection 5
        - double: `AI`
          - AI-only mismatch proven in the 2b/2c/2d/6h problem sector: rank 6 vs 6, union rank 8, intersection 4
          - BS-only external comparison still blocked; no BS-only lift to the 56-row Bilbao spinorial basis is fixed yet
        - `delta_c1_minus_b1` / `delta_d1_minus_b1` are AI excess directions, not separately proven BS excess directions.

        下一步唯一目标：
        - 如果还要推进 double 的 BS line，只能去构造一个不依赖 AI anchoring 的 BS-only current->Bilbao spinorial row-basis lift，或者拿到独立 external BS object。
        """
    ).strip()


def build_report_md(summary: dict[str, Any], single_ai: dict[str, Any], single_bs: dict[str, Any], double_ai: dict[str, Any], double_bs: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""\
        # SG194 BS-vs-AI Separation Report

        ## 1. Problem Background And Previous Mis-attribution

        The previous `external_matrix_final` stage compared internal AI/generator images against cached external matrices and then described the result as a BS-space mismatch. That attribution was too strong. An AI-image mismatch can imply that the current atomic-generator layer is not externally aligned, but it cannot by itself prove that the BS layer is misaligned.

        This stage corrects that object confusion by separating:

        - AI-only external comparison
        - BS-only external comparison

        for both single and double.

        ## 2. Single: AI-only External Comparison

        Current single AI is represented by the `45` raw AI candidates restricted to the `34` selected HSP rows. The external comparison object is the cached Bilbao ordinary `34 x 45` generator matrix.

        These two matrices live in different row bases but in the same `45`-generator domain after exact generator-id reordering. Therefore the correct invariant is their row-space comparison in
        \\[
        \mathbb{{Z}}^{{45}}.
        \\]

        The result is:
        - current rank = `{single_ai['current_ai_candidate_rank']}`
        - external rank = `{single_ai['external_generator_rank']}`
        - union rank = `{single_ai['rowspace_union_rank']}`
        - intersection rank = `{single_ai['rowspace_intersection_rank']}`

        So the single AI mismatch is exactly one-dimensional.

        ## 3. Single: BS-only External Comparison

        Current single BS is represented by the projected current BS basis in the non-AI-anchored `34`-row point-space used in the v2 stage. The external comparison object is the ordinary SG194 standard symmetry-data span represented by the same cached Bilbao `34 x 45` ordinary generator matrix.

        In this ambient `34`-row point-space, one compares column spaces:
        \\[
        \mathrm{{Col}}(B_{{\mathrm{{cur}}}}^{{\mathrm{{single,HSP}}}}) \subset \mathbb{{Z}}^{{34}},
        \qquad
        \mathrm{{Col}}(E_{{\mathrm{{ord}}}}) \subset \mathbb{{Z}}^{{34}}.
        \\]

        The result is:
        - current rank = `{single_bs['current_bs_image_rank']}`
        - external rank = `{single_bs['external_span_rank']}`
        - union rank = `{single_bs['columnspace_union_rank']}`
        - intersection rank = `{single_bs['columnspace_intersection_rank']}`

        This is a strong BS-space mismatch, not just an AI mismatch. The old v1 `trivial` must stay retired; the old `Z^5` is only an internal current-point-space BS/AI gap.

        ## 4. Double: AI-only External Comparison

        For double, the exact external object available locally is the cached Bilbao physically irreducible spinorial `56 x 33` generator matrix. The current side can be aligned honestly only in the explicit `2b/2c/2d/6h` problem sector, where the v2 stage already fixed representation-content merges.

        In that explicit problem sector:
        - current merged rank = `{double_ai['problem_sector_current_rank']}`
        - external rank = `{double_ai['problem_sector_external_rank']}`
        - union rank = `{double_ai['problem_sector_union_rank']}`
        - intersection rank = `{double_ai['problem_sector_intersection_rank']}`

        Therefore `delta_c1_minus_b1` and `delta_d1_minus_b1` are AI excess directions in the current problem-sector generator image.

        ## 5. Double: BS-only External Comparison

        The BS-only comparison for double is still blocked. The current double BS basis is only available after restriction to the `34` current point coordinates, whereas the cached external spinorial object is an AI generator matrix in a `56`-row Bilbao basis. No BS-only lift
        \\[
        \mathbb{{Z}}^{{34}} \to \mathbb{{Z}}^{{56}}
        \\]
        has been fixed without reusing AI anchoring, and there is no independently cached external double BS basis/span.

        So the correct conclusion is not “double BS mismatch proven”, but rather:
        - double AI mismatch is proven,
        - double BS mismatch is not yet separately established.

        ## 6. Final Diagnosis

        - single main issue: `{summary['single_main_issue']}`
        - double main issue: `{summary['double_main_issue']}`

        Updated interpretation:
        - single: both AI and BS are externally misaligned, with the BS mismatch stronger
        - double: AI mismatch is proven; BS comparison remains blocked/unresolved

        ## 7. Implementation Mapping

        - single AI-only output: `sg194_single_ai_vs_external.json`
        - single BS-only output: `sg194_single_bs_vs_external.json`
        - double AI-only output: `sg194_double_ai_vs_external.json`
        - double BS-only output: `sg194_double_bs_vs_external.json`
        - summary: `sg194_bs_ai_separation_summary.json`
        """
    ).strip()


def build_report_tex(md: str) -> str:
    sections = md.split("\n## ")
    title = sections[0].splitlines()[0].replace("# ", "")
    rendered_sections = []
    for sec in sections[1:]:
        lines = sec.splitlines()
        sec_title = lines[0].strip()
        rendered = [rf"\section*{{{latex_escape(sec_title)}}}"]
        for line in lines[1:]:
            if not line.strip():
                rendered.append("")
            else:
                rendered.append(latex_escape(line) + r"\\")
        rendered_sections.append("\n".join(rendered))
    return textwrap.dedent(
        rf"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{hyperref}}
        \usepackage{{amsmath,amssymb}}
        \setlength{{\parindent}}{{0pt}}
        \setlength{{\parskip}}{{0.6em}}
        \begin{{document}}
        \begin{{center}}
        {{\LARGE {latex_escape(title)}}}
        \end{{center}}
        {'\n\n'.join(rendered_sections)}
        \end{{document}}
        """
    ).strip() + "\n"


def create_package() -> None:
    ensure_clean_dir(PACKAGE_DIR)
    package_files = [path for path in REQUIRED_OUTPUTS if path != PACKAGE_TARBALL] + [REPORT_MD] + BACKGROUND_FILES
    for src in package_files:
        shutil.copy2(src, PACKAGE_DIR / src.name)
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "SSGReps.py", PACKAGE_DIR / "SSGReps.py")
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "SG_utils.py", PACKAGE_DIR / "SG_utils.py")
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "rep_utils.py", PACKAGE_DIR / "rep_utils.py")

    readme = textwrap.dedent(
        f"""\
        # SG194 BS-vs-AI Separation Audit

        This package contains the separated SG194 audit for `194.1.1.1`, explicitly correcting the previous `external_matrix_final` object confusion.

        ## Scope
        - target group: `194.1.1.1`
        - task: separate `AI-vs-external` from `BS-vs-external`

        ## Main outputs
        - `sg194_single_ai_vs_external.json`
        - `sg194_single_bs_vs_external.json`
        - `sg194_double_ai_vs_external.json`
        - `sg194_double_bs_vs_external.json`
        - `sg194_bs_ai_separation_summary.json`

        ## SG194 BS-vs-AI separation report
        - report file: `sg194_bs_ai_separation_report.pdf`
        - report source: `sg194_bs_ai_separation_report.tex`
        - suggested reading order:
          1. PDF report
          2. single AI vs external
          3. single BS vs external
          4. double AI vs external
          5. double BS vs external
        """
    ).strip()
    write_text(README_PATH, readme)

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate() -> None:
    for path in REQUIRED_OUTPUTS:
        if not path.exists():
            raise SystemExit(f"missing required output: {path.name}")
    summary = load_json(SUMMARY_JSON)
    single_ai = load_json(SINGLE_AI_JSON)
    single_bs = load_json(SINGLE_BS_JSON)
    double_ai = load_json(DOUBLE_AI_JSON)
    double_bs = load_json(DOUBLE_BS_JSON)
    assert summary["single_main_issue"] == "both"
    assert summary["double_main_issue"] == "AI"
    assert single_ai["rowspace_union_rank"] == 14
    assert single_ai["rowspace_intersection_rank"] == 12
    assert single_bs["current_bs_image_rank"] == 18
    assert single_bs["external_span_rank"] == 13
    assert single_bs["columnspace_union_rank"] == 26
    assert single_bs["columnspace_intersection_rank"] == 5
    assert double_ai["problem_sector_union_rank"] == 8
    assert double_ai["problem_sector_intersection_rank"] == 4
    assert double_bs["bs_only_comparison_status"] == "blocked"
    assert REPORT_PDF.exists()
    assert PACKAGE_TARBALL.exists()
    print("validation_ok")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate()
        return

    single_ai = build_single_ai_vs_external()
    single_bs = build_single_bs_vs_external()
    double_ai = build_double_ai_vs_external()
    double_bs = build_double_bs_vs_external()
    summary = build_summary_json(single_ai, single_bs, double_ai, double_bs)

    write_json(SINGLE_AI_JSON, single_ai)
    write_json(SINGLE_BS_JSON, single_bs)
    write_text(SINGLE_AUDIT_MD, build_single_audit_md(single_ai, single_bs))
    write_json(DOUBLE_AI_JSON, double_ai)
    write_json(DOUBLE_BS_JSON, double_bs)
    write_text(DOUBLE_AUDIT_MD, build_double_audit_md(double_ai, double_bs))
    write_json(SUMMARY_JSON, summary)
    write_text(AUDIT_MD, build_audit_md(summary))
    write_text(HANDOFF_MD, build_handoff(summary))
    write_json(
        CURRENT_STATUS_JSON,
        {
            "target_group": GROUP,
            "single_main_issue": summary["single_main_issue"],
            "double_main_issue": summary["double_main_issue"],
            "single_ai_union_rank": single_ai["rowspace_union_rank"],
            "single_bs_union_rank": single_bs["columnspace_union_rank"],
            "double_ai_problem_sector_union_rank": double_ai["problem_sector_union_rank"],
            "double_bs_status": double_bs["bs_only_comparison_status"],
            "blocker": "double BS-only comparison still lacks a BS-only lift to the external 56-row spinorial basis",
            "next_step": "Either construct a BS-only current->Bilbao spinorial lift or obtain an independent external double BS object.",
        },
    )
    write_text(NEXT_STEP_TXT, build_next_step_prompt(summary))
    report_md = build_report_md(summary, single_ai, single_bs, double_ai, double_bs)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, build_report_tex(report_md))
    compile_pdf()
    create_package()


if __name__ == "__main__":
    main()
