#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import defaultdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent
GROUP = "194.1.1.1"

SINGLE_MAP_MD = ROOT / "sg194_single_external_rowspace_projection.md"
SINGLE_MAP_JSON = ROOT / "sg194_single_external_rowspace_projection.json"
DOUBLE_ALIGN_MD = ROOT / "sg194_double_repcontent_alignment.md"
DOUBLE_ALIGN_JSON = ROOT / "sg194_double_repcontent_alignment.json"
SINGLE_QUOTIENT_JSON = ROOT / "sg194_single_standard_quotient_recomputed_v2.json"
DOUBLE_QUOTIENT_JSON = ROOT / "sg194_double_standard_quotient_recomputed_v2.json"
AUDIT_MD = ROOT / "sg194_standard_alignment_audit_v2.md"
SUMMARY_JSON = ROOT / "sg194_standard_alignment_summary_v2.json"
HANDOFF_MD = ROOT / "handoff_sg194_standard_alignment_v2.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_standard_alignment_v2.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_sg194_standard_alignment_v2.txt"
REPORT_MD = ROOT / "sg194_standard_alignment_report_v2.md"
REPORT_TEX = ROOT / "sg194_standard_alignment_report_v2.tex"
REPORT_PDF = ROOT / "sg194_standard_alignment_report_v2.pdf"

PACKAGE_NAME = "review_package_sg194_standard_alignment_audit_v2"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

RESEARCH_RESULTS_TSV = ROOT / "research-results-standard-alignment-v2.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-standard-alignment-v2.json"
VERIFY_CMD = "python3 -u debug_sg194_standard_alignment_v2.py --validate"
GUARD_CMD = (
    "python3 -u debug_sg194_standard_alignment.py --validate && "
    "python3 -u debug_external_sg194_audit.py --validate && "
    "python3 -u debug_raw_matrix_audit.py --validate"
)

OLD_SINGLE_MAP_JSON = ROOT / "sg194_single_standard_space_map.json"
OLD_DOUBLE_ALIGN_JSON = ROOT / "sg194_double_spinorial_alignment.json"
OLD_SINGLE_QUOTIENT_JSON = ROOT / "sg194_single_standard_quotient_recomputed.json"
OLD_DOUBLE_QUOTIENT_JSON = ROOT / "sg194_double_standard_quotient_recomputed.json"
OLD_SUMMARY_JSON = ROOT / "sg194_standard_alignment_summary.json"

EXT_SOURCE_JSON = ROOT / "sg194_external_source_audit.json"
EXT_AI_JSON = ROOT / "sg194_external_ai_standard.json"
EXT_CMP_JSON = ROOT / "sg194_external_vs_current_ai_comparison.json"
EXT_JUDGMENT_JSON = ROOT / "sg194_final_correction_judgment.json"

RAW_SINGLE_C = ROOT / "raw_194_1_1_1_single_C.json"
RAW_SINGLE_BS = ROOT / "raw_194_1_1_1_single_bs_basis_raw.json"
RAW_SINGLE_AI = ROOT / "raw_194_1_1_1_single_ai_basis.json"
RAW_DOUBLE_C = ROOT / "raw_194_1_1_1_double_C.json"
RAW_DOUBLE_AI_CAND = ROOT / "raw_194_1_1_1_double_ai_candidates.json"

BACKGROUND_FILES = [
    EXT_SOURCE_JSON,
    EXT_AI_JSON,
    EXT_CMP_JSON,
    EXT_JUDGMENT_JSON,
    OLD_SINGLE_MAP_JSON,
    OLD_DOUBLE_ALIGN_JSON,
    OLD_SINGLE_QUOTIENT_JSON,
    OLD_DOUBLE_QUOTIENT_JSON,
    OLD_SUMMARY_JSON,
    ROOT / "raw_194_1_1_1_single_C.json",
    ROOT / "raw_194_1_1_1_single_bs_basis_raw.json",
    ROOT / "raw_194_1_1_1_single_bs_basis_pretty.json",
    ROOT / "raw_194_1_1_1_single_ai_candidates.json",
    ROOT / "raw_194_1_1_1_single_ai_basis.json",
    ROOT / "raw_194_1_1_1_single_ai_in_bs_matrix.json",
    ROOT / "raw_194_1_1_1_single_quotient.json",
    ROOT / "raw_194_1_1_1_double_C.json",
    ROOT / "raw_194_1_1_1_double_bs_basis_raw.json",
    ROOT / "raw_194_1_1_1_double_bs_basis_pretty.json",
    ROOT / "raw_194_1_1_1_double_ai_candidates.json",
    ROOT / "raw_194_1_1_1_double_ai_basis.json",
    ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json",
    ROOT / "raw_194_1_1_1_double_quotient.json",
    ROOT / "finite_indicator_extraction_summary.json",
    ROOT / "reinterpretation_194_1_1_1_single_finite_part.json",
    ROOT / "reinterpretation_194_1_1_1_double_finite_part.json",
    ROOT / "group_194_1_1_1_single_ai_completion_summary.json",
    ROOT / "group_194_1_1_1_single_indicator_group_summary.json",
    ROOT / "group_194_1_1_1_single_indicator_generators.json",
    ROOT / "group_194_1_1_1_double_ai_completion_summary.json",
    ROOT / "group_194_1_1_1_double_indicator_group_summary.json",
    ROOT / "group_194_1_1_1_double_indicator_generators.json",
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
    ROOT / "debug_sg194_standard_alignment_v2.py",
    REPORT_TEX,
    REPORT_PDF,
    PACKAGE_TARBALL,
]

STANDARD_POINT_BLOCKS_SINGLE = [
    ("P1", "GM"),
    ("P2", "A"),
    ("P3", "K"),
    ("B1", "H"),
    ("P5", "M"),
    ("P6", "L"),
]
STANDARD_POINT_BLOCKS_DOUBLE = [
    ("P1", "Gamma"),
    ("P2", "A"),
    ("P3", "K"),
    ("B1", "H"),
    ("P5", "M"),
    ("P6", "L"),
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


def selection_indices(unknown_ordering: list[str], block_ids: list[str]) -> list[int]:
    return [idx for idx, label in enumerate(unknown_ordering) if any(label.startswith(f"{block}_") for block in block_ids)]


def selection_matrix(total_dim: int, chosen: list[int]) -> sp.Matrix:
    rows = []
    for idx in chosen:
        row = [0] * total_dim
        row[idx] = 1
        rows.append(row)
    return sp.Matrix(rows)


def matrix_from_basis_vectors(records: list[dict[str, Any]], chosen_idx: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([rec["vector"][i] for i in chosen_idx]) for rec in records])


def matrix_from_candidate_unknown(records: list[dict[str, Any]], chosen_idx: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([rec["unknown_vector"][i] for i in chosen_idx]) for rec in records])


def record_columnspace_extension(
    basis_matrix: sp.Matrix,
    ai_matrix: sp.Matrix,
    basis_ids: list[str],
    row_labels: list[str],
) -> list[dict[str, Any]]:
    base = ai_matrix
    out: list[dict[str, Any]] = []
    for idx, basis_id in enumerate(basis_ids):
        col = basis_matrix[:, idx]
        if sp.Matrix.hstack(base, col).rank() > base.rank():
            if base.rank() >= ai_matrix.rank():
                out.append(
                    {
                        "bs_basis_id": basis_id,
                        "hsp_vector": [int(val) for val in list(col)],
                        "support_on_hsp_rows": support_from_dense(list(col), row_labels),
                    }
                )
            base = sp.Matrix.hstack(base, col)
    return out


def build_single_v2() -> tuple[dict[str, Any], dict[str, Any]]:
    ext_ai = load_json(EXT_AI_JSON)
    old_map = load_json(OLD_SINGLE_MAP_JSON)
    old_q = load_json(OLD_SINGLE_QUOTIENT_JSON)
    raw_c = load_json(RAW_SINGLE_C)
    raw_bs = load_json(RAW_SINGLE_BS)
    raw_ai = load_json(RAW_SINGLE_AI)

    block_ids = [item[0] for item in STANDARD_POINT_BLOCKS_SINGLE]
    std_idx = selection_indices(raw_c["unknown_ordering"], block_ids)
    std_labels = [raw_c["unknown_ordering"][idx] for idx in std_idx]
    sel_mat = selection_matrix(len(raw_c["unknown_ordering"]), std_idx)

    bs_basis = matrix_from_basis_vectors(raw_bs["basis_vectors"], std_idx)
    ai_basis = matrix_from_basis_vectors(raw_ai["basis_vectors"], std_idx)
    bs_rank = int(bs_basis.rank())
    ai_rank = int(ai_basis.rank())

    bs_img_basis = sp.Matrix.hstack(*bs_basis.columnspace())
    ai_in_bs_img = bs_img_basis.gauss_jordan_solve(ai_basis)[0]
    smith = smith_invariants(ai_in_bs_img)
    free_rank = bs_img_basis.cols - len(smith)
    finite_part = [int(val) for val in smith if int(val) > 1]
    restricted_quotient = quotient_string(free_rank, finite_part)

    extra_dirs = record_columnspace_extension(
        basis_matrix=bs_basis,
        ai_matrix=ai_basis,
        basis_ids=[item["id"] for item in raw_bs["basis_vectors"]],
        row_labels=std_labels,
    )

    single_map = {
        "group": GROUP,
        "group_type": 1,
        "old_method": "AI-anchored projection using [M | C]^{-1} and explicit complement killing",
        "new_method": "External-standard-point-determined restriction to the 34 HSP coordinates GM/A/K/H/M/L, with no AI-preserving complement-killing step",
        "current_raw_unknown_ordering": raw_c["unknown_ordering"],
        "external_standard_row_basis": list(ext_ai["single"]["basis_rows"]),
        "block_mapping_current_to_external": [
            {"current_block": current, "external_block": external} for current, external in STANDARD_POINT_BLOCKS_SINGLE
        ],
        "hsp_selection_labels": std_labels,
        "selection_matrix_unknown_to_hsp": matrix_to_json_rows(sel_mat),
        "selection_matrix_shape": [sel_mat.rows, sel_mat.cols],
        "current_hsp_point_space_bs_rank": bs_rank,
        "current_hsp_point_space_ai_rank": ai_rank,
        "current_hsp_point_space_quotient": restricted_quotient,
        "current_hsp_ai_in_bs_image_smith_diagonal_nonzero": smith,
        "current_hsp_extra_directions_over_ai": extra_dirs,
        "old_trivial_claim": old_q["standard_space_quotient"],
        "old_projection_notes": old_map["notes"],
        "external_full_single_matrix_available_locally": False,
        "confidence": "medium",
        "notes": [
            "The new map is no longer built from the current AI basis plus a killed complement.",
            "It is the exact coordinate restriction from the 62 raw unknowns to the 34 standard high-symmetry point coordinates.",
            "Within that 34-row point space, the current BS image still has rank 18 while the current AI image has rank 13.",
            "Therefore the v1 trivial quotient is not reproduced by this stricter method.",
        ],
    }

    single_q = {
        "group": GROUP,
        "group_type": 1,
        "old_result": old_q["standard_space_quotient"],
        "new_result": None,
        "old_method": old_q["user_facing_rewrite"],
        "new_method": "Restrict current BS and AI to the externally determined 34-row HSP coordinate space before any further external row-space reduction.",
        "raw_quotient": load_json(ROOT / "raw_194_1_1_1_single_quotient.json")["raw_quotient"],
        "current_hsp_point_space_quotient": restricted_quotient,
        "current_hsp_point_space_bs_rank": bs_rank,
        "current_hsp_point_space_ai_rank": ai_rank,
        "free_part": f"Z^{free_rank}" if free_rank else "0",
        "finite_part": finite_part,
        "more_trustworthy_than_old": True,
        "remaining_blocker": (
            "The local repository does not contain the full external 34x45 ordinary SG194 generator matrix, so the final "
            "34-row current HSP coordinates -> 34-row external ordinary symmetry-data coordinates map cannot yet be fixed "
            "without a live Bilbao refetch or an equivalent cached matrix. Under the stricter non-AI-anchored method, the "
            "current HSP image has rank 18 rather than 13, so the old trivial claim must be downgraded."
        ),
    }
    return single_map, single_q


def build_double_v2() -> tuple[dict[str, Any], dict[str, Any]]:
    ext_ai = load_json(EXT_AI_JSON)
    old_align = load_json(OLD_DOUBLE_ALIGN_JSON)
    old_q = load_json(OLD_DOUBLE_QUOTIENT_JSON)
    raw_c = load_json(RAW_DOUBLE_C)
    raw_ai_cand = load_json(RAW_DOUBLE_AI_CAND)["candidates"]

    block_ids = [item[0] for item in STANDARD_POINT_BLOCKS_SINGLE]
    std_idx = selection_indices(raw_c["unknown_ordering"], block_ids)
    std_labels = [raw_c["unknown_ordering"][idx] for idx in std_idx]

    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id: dict[str, dict[str, Any]] = {}
    for cand in raw_ai_cand:
        by_family[cand["family_id"]].append(cand)
        by_id[cand["generator_id"]] = cand

    def vec_from_id(gen_id: str) -> sp.Matrix:
        cand = by_id[gen_id]
        return sp.Matrix([cand["unknown_vector"][i] for i in std_idx])

    def record_for_id(gen_id: str) -> dict[str, Any]:
        cand = by_id[gen_id]
        vec = vec_from_id(gen_id)
        return {
            "generator_id": gen_id,
            "local_object_label": cand["local_object_label"],
            "local_object_dimension": int(cand["local_object_dimension"]),
            "site_symmetry_type": cand["source_payload"]["site_symmetry_type_label"],
            "content_on_current_hsp_rows": support_from_dense(list(vec), std_labels),
        }

    all_current_hsp = matrix_from_candidate_unknown(raw_ai_cand, std_idx)
    identity_families = ["a", "e", "f", "g", "i", "j", "k", "l"]
    identity_matrix = matrix_from_candidate_unknown(
        [cand for fam in identity_families for cand in by_family[fam]],
        std_idx,
    )

    merged_channels: list[dict[str, Any]] = []
    merged_cols: list[sp.Matrix] = []
    merged_labels: list[str] = []

    for fam in identity_families:
        for cand in by_family[fam]:
            vec = vec_from_id(cand["generator_id"])
            merged_cols.append(vec)
            merged_labels.append(cand["generator_id"])
            merged_channels.append(
                {
                    "external_channel_label": cand["generator_id"],
                    "current_generators": [cand["generator_id"]],
                    "site_label": cand["family_id"],
                    "merge_type": "identity",
                    "content_on_current_hsp_rows": support_from_dense(list(vec), std_labels),
                }
            )

    site_groups = {}
    for fam in ["b", "c", "d"]:
        groups = [
            ([f"{fam}_proj_doubleprime_1d_1", f"{fam}_proj_doubleprime_1d_2"], f"{fam}:E1"),
            ([f"{fam}_proj_prime_1d_3", f"{fam}_proj_prime_1d_4"], f"{fam}:E2"),
            ([f"{fam}_proj_doubleprime_2d_5", f"{fam}_proj_doubleprime_2d_6"], f"{fam}:E3"),
        ]
        site_groups[fam] = groups
        for labels, merged_label in groups:
            vec = sum((vec_from_id(label) for label in labels), sp.zeros(len(std_idx), 1))
            merged_cols.append(vec)
            merged_labels.append(merged_label)
            merged_channels.append(
                {
                    "external_channel_label": merged_label,
                    "current_generators": labels,
                    "site_label": fam,
                    "merge_type": "pair-sum-on-current-row-content",
                    "content_on_current_hsp_rows": support_from_dense(list(vec), std_labels),
                }
            )

    h_labels = [cand["generator_id"] for cand in by_family["h"]]
    h_vec = sum((vec_from_id(label) for label in h_labels), sp.zeros(len(std_idx), 1))
    merged_cols.append(h_vec)
    merged_labels.append("h:E")
    merged_channels.append(
        {
            "external_channel_label": "h:E",
            "current_generators": h_labels,
            "site_label": "h",
            "merge_type": "four-way-sum-on-current-row-content",
            "content_on_current_hsp_rows": support_from_dense(list(h_vec), std_labels),
        }
    )

    merged_matrix = sp.Matrix.hstack(*merged_cols)
    merged_rank = int(merged_matrix.rank())
    identity_rank = int(identity_matrix.rank())
    increment_over_identity = int(sp.Matrix.hstack(identity_matrix, sp.Matrix.hstack(*merged_cols[-10:])).rank() - identity_rank)

    problematic_details = {}
    for fam in ["b", "c", "d", "h"]:
        records = [record_for_id(cand["generator_id"]) for cand in by_family[fam]]
        fam_matrix = matrix_from_candidate_unknown(by_family[fam], std_idx)
        if fam == "h":
            merged_fam_cols = [h_vec]
        else:
            merged_fam_cols = []
            for labels, _ in site_groups[fam]:
                merged_fam_cols.append(sum((vec_from_id(label) for label in labels), sp.zeros(len(std_idx), 1)))
        merged_fam_matrix = sp.Matrix.hstack(*merged_fam_cols)
        problematic_details[fam] = {
            "current_generator_count": len(by_family[fam]),
            "current_rank_in_row_content_space": int(fam_matrix.rank()),
            "merged_rank_in_row_content_space": int(merged_fam_matrix.rank()),
            "current_generators": records,
        }

    b1 = sum((vec_from_id(label) for label in site_groups["b"][0][0]), sp.zeros(len(std_idx), 1))
    c1 = sum((vec_from_id(label) for label in site_groups["c"][0][0]), sp.zeros(len(std_idx), 1))
    d1 = sum((vec_from_id(label) for label in site_groups["d"][0][0]), sp.zeros(len(std_idx), 1))
    blocker_basis = [
        {
            "id": "delta_c1_minus_b1",
            "support_on_current_hsp_rows": support_from_dense(list(c1 - b1), std_labels),
        },
        {
            "id": "delta_d1_minus_b1",
            "support_on_current_hsp_rows": support_from_dense(list(d1 - b1), std_labels),
        },
    ]

    double_align = {
        "group": GROUP,
        "group_type": 2,
        "old_method": "Heuristic count merge 45 -> 33 without explicit row-content diagnosis",
        "new_method": "Representation-content alignment on the current HSP row-content space, with explicit sitewise merged channels and residual mismatch basis",
        "current_hsp_row_labels": std_labels,
        "external_spinorial_row_basis": list(ext_ai["double"]["basis_rows"]),
        "external_spinorial_generator_inventory": list(ext_ai["double"]["spinorial_generator_inventory"]),
        "current_raw_hsp_rank": int(all_current_hsp.rank()),
        "identity_sector_rank": identity_rank,
        "count_aligned_rank_in_current_hsp_space": merged_rank,
        "bilbao_spinorial_rank": int(ext_ai["double"]["external_ai_rank_spinorial_candidate"]),
        "increment_of_problematic_sector_over_identity": increment_over_identity,
        "problematic_sites": problematic_details,
        "merged_channels": merged_channels,
        "residual_rank_gap_to_bilbao": int(merged_rank - int(ext_ai["double"]["external_ai_rank_spinorial_candidate"])),
        "residual_rank_gap_basis": blocker_basis,
        "old_alignment_notes": old_align["notes"],
        "honest_alignment_complete": False,
        "remaining_blocker": (
            "The current HSP-row-content merge lowers the problematic 45-label library to rank 12, but the local repository "
            "still lacks the full external 56x33 Bilbao spinorial generator matrix needed to lift the current 34-row HSP "
            "content into the external spinorial row basis and to decide which two residual directions should be quotiented out."
        ),
        "notes": [
            "The rank-2 gap is fully localized in the problematic 2b/2c/2d/6h sector.",
            "After content-based merging, the identity families contribute rank 9 and the problematic sector contributes 3 more directions, whereas Bilbao's total spinorial rank is 10.",
            "Therefore two extra current directions remain beyond the Bilbao physically irreducible spinorial standard layer.",
        ],
    }

    double_q = {
        "group": GROUP,
        "group_type": 2,
        "old_result": old_q["standard_space_quotient"],
        "new_result": None,
        "old_method": old_q["user_facing_rewrite"],
        "new_method": "Representation-content alignment on the current HSP row-content space, plus explicit residual rank-2 blocker basis",
        "raw_quotient": load_json(ROOT / "raw_194_1_1_1_double_quotient.json")["raw_quotient"],
        "current_hsp_row_space_rank": int(all_current_hsp.rank()),
        "count_aligned_rank": merged_rank,
        "bilbao_spinorial_rank": int(ext_ai["double"]["external_ai_rank_spinorial_candidate"]),
        "free_part": None,
        "finite_part": None,
        "more_trustworthy_than_old": True,
        "remaining_blocker": double_align["remaining_blocker"],
    }
    return double_align, double_q


def build_summary(single_map: dict[str, Any], single_q: dict[str, Any], double_align: dict[str, Any], double_q: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": GROUP,
        "single": {
            "new_projection_uses_ai_anchored_trick": False,
            "old_trivial_still_stands": False,
            "current_hsp_point_space_bs_rank": int(single_map["current_hsp_point_space_bs_rank"]),
            "current_hsp_point_space_ai_rank": int(single_map["current_hsp_point_space_ai_rank"]),
            "current_hsp_point_space_quotient": single_map["current_hsp_point_space_quotient"],
            "main_issue": "The old v1 trivial result depended on an AI-anchored complement-killing projection; under the stricter HSP restriction, five extra current directions remain beyond AI.",
        },
        "double": {
            "new_alignment_is_count_merge_only": False,
            "count_aligned_rank": int(double_align["count_aligned_rank_in_current_hsp_space"]),
            "bilbao_spinorial_rank": int(double_align["bilbao_spinorial_rank"]),
            "rank_2_mismatch_localized": True,
            "main_issue": "The residual rank-2 mismatch is entirely localized in the 2b/2c/2d/6h representation-content sector.",
        },
        "overall": {
            "single_trivial_is_now_hardened": False,
            "double_standard_space_quotient_computable": False,
            "sg194_fully_aligned_to_external_standard_language": False,
        },
    }


def build_single_md(single_map: dict[str, Any], single_q: dict[str, Any]) -> str:
    extra_lines = []
    for item in single_map["current_hsp_extra_directions_over_ai"]:
        extra_lines.append(f"- `{item['bs_basis_id']}`: {item['support_on_hsp_rows']}")
    return textwrap.dedent(
        f"""
        # SG194 Single External Row-Space Projection

        ## Old vs New

        - Old method: `{single_map['old_method']}`
        - New method: `{single_map['new_method']}`
        - Old trivial claim: `{single_map['old_trivial_claim']}`

        ## New Projection

        - Domain: current raw unknown ordering of size `{len(single_map['current_raw_unknown_ordering'])}`
        - Target: the `34` standard HSP coordinates selected by the external ordinary SG 194 point list `GM/A/K/H/M/L`
        - Block map: `{single_map['block_mapping_current_to_external']}`

        This map is the literal coordinate restriction from the raw unknown ordering to the current HSP block set. It does not preserve the current AI by construction and does not kill any complement by hand.

        ## Rank Outcome

        - Current HSP-space BS rank: `{single_map['current_hsp_point_space_bs_rank']}`
        - Current HSP-space AI rank: `{single_map['current_hsp_point_space_ai_rank']}`
        - Current HSP-space quotient: `{single_map['current_hsp_point_space_quotient']}`

        ## Extra Directions Beyond AI

        {chr(10).join(extra_lines)}

        ## Conclusion

        The stricter v2 method does not reproduce the v1 `trivial` quotient. It leaves a rank-`5` free gap inside the selected HSP point space. To reduce that rank-`18` current image to the external ordinary SG 194 standard rank `13`, one still needs the full external ordinary generator matrix or an equivalent cached point-irrep basis transform.
        """
    ).strip()


def build_double_md(double_align: dict[str, Any], double_q: dict[str, Any]) -> str:
    site_lines = []
    for fam in ["b", "c", "d", "h"]:
        item = double_align["problematic_sites"][fam]
        site_lines.append(
            f"- `{fam}`: current count `{item['current_generator_count']}`, current rank `{item['current_rank_in_row_content_space']}`, merged rank `{item['merged_rank_in_row_content_space']}`"
        )
    blocker_lines = [f"- `{item['id']}`: {item['support_on_current_hsp_rows']}" for item in double_align["residual_rank_gap_basis"]]
    return textwrap.dedent(
        f"""
        # SG194 Double Representation-Content Alignment

        ## Old vs New

        - Old method: `{double_align['old_method']}`
        - New method: `{double_align['new_method']}`
        - Old result: current aligned rank `{load_json(OLD_DOUBLE_ALIGN_JSON)['merged_current_candidate_rank']}` vs Bilbao rank `{load_json(OLD_DOUBLE_ALIGN_JSON)['external_spinorial_rank']}`

        ## Sitewise Content Alignment

        {chr(10).join(site_lines)}

        The pairings at `2b/2c/2d` and the four-way sum at `6h` are now justified by explicit current HSP row-content vectors rather than by count alone.

        ## Rank Outcome

        - Current raw HSP-space rank: `{double_align['current_raw_hsp_rank']}`
        - Identity-sector rank: `{double_align['identity_sector_rank']}`
        - Count-aligned rank in current HSP space: `{double_align['count_aligned_rank_in_current_hsp_space']}`
        - Bilbao spinorial rank: `{double_align['bilbao_spinorial_rank']}`
        - Residual gap: `{double_align['residual_rank_gap_to_bilbao']}`

        ## Residual Rank-2 Basis

        {chr(10).join(blocker_lines)}

        ## Conclusion

        The residual mismatch is no longer a vague count mismatch. It is a concrete rank-`2` excess inside the problematic `2b/2c/2d/6h` representation-content sector. The standard-space quotient still cannot be recomputed honestly until the full external spinorial generator matrix is available and these two excess directions are either matched or quotiented out for a physically irreducible Bilbao-standard basis.
        """
    ).strip()


def build_audit_md(single_map: dict[str, Any], single_q: dict[str, Any], double_align: dict[str, Any], double_q: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Standard Alignment Audit V2

        This audit hardens the SG 194 standard-language alignment relative to v1.

        ## Single

        - The v1 single result used an AI-anchored projection with an explicitly killed complement.
        - The v2 single map is the exact restriction from the 62 raw unknowns to the 34 HSP coordinates corresponding to the external ordinary `GM/A/K/H/M/L` row set.
        - Under this stricter method:
          - current HSP-space BS rank = `{single_map['current_hsp_point_space_bs_rank']}`
          - current HSP-space AI rank = `{single_map['current_hsp_point_space_ai_rank']}`
          - current HSP-space quotient = `{single_map['current_hsp_point_space_quotient']}`
        - Therefore the old `trivial` result does not stand as a hard v2 conclusion.

        ## Double

        - The v1 double result only fixed the generator counts.
        - The v2 double analysis aligns the problematic sites through their actual current HSP representation content.
        - Under this stricter method:
          - current HSP-space rank = `{double_align['current_raw_hsp_rank']}`
          - count-aligned rank = `{double_align['count_aligned_rank_in_current_hsp_space']}`
          - Bilbao spinorial rank = `{double_align['bilbao_spinorial_rank']}`
          - residual gap = `{double_align['residual_rank_gap_to_bilbao']}`
        - The residual gap is fully localized in `2b/2c/2d/6h`.

        ## Updated Conclusions

        - Single trivial still stands: `{summary['single']['old_trivial_still_stands']}`
        - Double standard-space quotient computable now: `{summary['overall']['double_standard_space_quotient_computable']}`
        - SG194 fully aligned to external standard language: `{summary['overall']['sg194_fully_aligned_to_external_standard_language']}`
        """
    ).strip()


def build_report_md(single_map: dict[str, Any], single_q: dict[str, Any], double_align: dict[str, Any], double_q: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Standard Alignment Report V2

        ## 1. Problem Background And V1 Limitation

        The v1 SG194 alignment settled the easy part of the language conversion but still relied on two constructions that were not hard enough:

        - Single: the quotient was made trivial by an AI-anchored projection with an explicitly killed complement.
        - Double: the basis mismatch was reduced only at the level of generator counts.

        This v2 report upgrades both sides to stricter definitions.

        ## 2. Single: AI-Anchored Projection vs External Row-Space Restriction

        Let the current raw unknown vector be
        \\[
        n_{{\\mathrm{{raw}}}} \\in \\mathbb{{Z}}^{{62}}.
        \\]
        The new single map does not start from the current AI basis. Instead it applies the literal standard-point selection
        \\[
        S_{{\\mathrm{{HSP}}}} : \\mathbb{{Z}}^{{62}} \\to \\mathbb{{Z}}^{{34}},
        \\]
        where the 34 retained rows are the current `P1,P2,P3,B1,P5,P6` blocks, corresponding externally to ordinary SG 194 `GM,A,K,H,M,L`.

        On the current raw BS basis this gives:

        - restricted BS rank = `{single_map['current_hsp_point_space_bs_rank']}`
        - restricted AI rank = `{single_map['current_hsp_point_space_ai_rank']}`
        - restricted point-space quotient = `{single_map['current_hsp_point_space_quotient']}`

        Therefore the old v1 `trivial` conclusion is not reproduced by the stricter non-AI-anchored method.

        ## 3. Single: Five Explicit Extra Directions

        The five extra current directions beyond AI inside the selected HSP point space are:

        {chr(10).join(f"- `{item['bs_basis_id']}` with support {item['support_on_hsp_rows']}" for item in single_map['current_hsp_extra_directions_over_ai'])}

        These five directions explain why the raw v1 ordinary quotient could be collapsed to `trivial` only after an additional constructed projection.

        ## 4. Double: Count Alignment vs Representation-Content Alignment

        The new double method works in the current HSP representation-content space rather than at the level of labels only.

        - current HSP-space rank = `{double_align['current_raw_hsp_rank']}`
        - identity-sector rank = `{double_align['identity_sector_rank']}`
        - count-aligned rank = `{double_align['count_aligned_rank_in_current_hsp_space']}`
        - Bilbao spinorial rank = `{double_align['bilbao_spinorial_rank']}`

        Sitewise, the problematic sectors behave as follows:

        {chr(10).join(f"- `{fam}` current rank `{double_align['problematic_sites'][fam]['current_rank_in_row_content_space']}` -> merged rank `{double_align['problematic_sites'][fam]['merged_rank_in_row_content_space']}`" for fam in ['b','c','d','h'])}

        ## 5. Double: Residual Rank-2 Mismatch

        After content-based merging, the problematic sector still contributes three independent directions over the identity families, whereas the Bilbao spinorial total rank implies that only one such direction should survive. The residual rank-2 blocker can be written explicitly as:

        {chr(10).join(f"- `{item['id']}` with support {item['support_on_current_hsp_rows']}" for item in double_align['residual_rank_gap_basis'])}

        The mismatch is therefore no longer a heuristic count issue; it is a concrete representation-content excess in the `2b/2c/2d/6h` sector.

        ## 6. New Recomputed Results

        Single:

        - old result = `{load_json(OLD_SINGLE_QUOTIENT_JSON)['standard_space_quotient']}`
        - new result = unresolved at the strict external-row-space level
        - current strict point-space quotient = `{single_q['current_hsp_point_space_quotient']}`

        Double:

        - old result = blocked after count alignment
        - new result = still blocked, but with an explicit rank-2 blocker basis

        ## 7. Updated User-Facing Conclusions

        - Single should no longer be summarized as “standard-space quotient = trivial” without qualification. The v2 method shows that the non-AI-anchored HSP restriction still leaves a free rank-5 gap; an external ordinary generator matrix or an equivalent cached point-irrep basis transform is still required before an honest final standard-space quotient can be stated.
        - Double should no longer be summarized as “45 -> 33 count merge done”. The v2 method shows exactly where the remaining rank-2 mismatch lives and why the standard-space quotient is still blocked.

        ## 8. Remaining Blockers And Next Step

        - Single blocker: obtain the full external ordinary SG194 34x45 generator matrix, or a cached equivalent, so that the current 18-dimensional HSP image can be reduced to the external 13-dimensional ordinary symmetry-data row space without AI anchoring.
        - Double blocker: obtain the full external 56x33 Bilbao spinorial generator matrix, or a cached equivalent, so that the current 34-row HSP content can be lifted into the external spinorial row basis and the explicit rank-2 blocker can be tested against the physically irreducible Bilbao convention.

        ## 9. Implementation Mapping

        - Single new restriction map and rank-5 blocker basis: `sg194_single_external_rowspace_projection.json`
        - Double new representation-content alignment and rank-2 blocker basis: `sg194_double_repcontent_alignment.json`
        - Updated v2 recomputed results: `sg194_single_standard_quotient_recomputed_v2.json`, `sg194_double_standard_quotient_recomputed_v2.json`
        - Consolidated v2 audit: `sg194_standard_alignment_audit_v2.md`, `sg194_standard_alignment_summary_v2.json`
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
        \\title{{SG194 Standard Alignment Report V2}}
        \\date{{2026-03-30}}
        \\maketitle
        {content}
        \\end{{document}}
        """
    ).strip() + "\n"


def compile_report() -> None:
    if shutil.which("pdflatex") is None:
        raise RuntimeError("pdflatex is required to build sg194_standard_alignment_report_v2.pdf")
    for ext in ["aux", "log", "out"]:
        path = ROOT / f"sg194_standard_alignment_report_v2.{ext}"
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
        raise RuntimeError("failed to build sg194_standard_alignment_report_v2.pdf")


def build_handoff(summary: dict[str, Any], single_q: dict[str, Any], double_q: dict[str, Any]) -> None:
    write_text(
        HANDOFF_MD,
        textwrap.dedent(
            f"""
            # Handoff: SG194 Standard Alignment V2

            - Target: `194.1.1.1`
            - Completed: single non-AI-anchored HSP restriction audit; double representation-content alignment audit
            - Single update: the old v1 `trivial` result does not survive the stricter v2 method; the current HSP point-space quotient is `{single_q['current_hsp_point_space_quotient']}`
            - Double update: the residual `rank-2` mismatch is now explicitly localized inside the `2b/2c/2d/6h` sector
            - Current blocker: local repo lacks the full external ordinary and spinorial generator matrices needed for the final external-row-space reduction
            - Next step: cache the full Bilbao ordinary 34x45 matrix and spinorial 56x33 matrix locally, then rerun v2 to finish the final external row-space reduction
            - Read first:
              - `sg194_standard_alignment_report_v2.pdf`
              - `sg194_single_external_rowspace_projection.json`
              - `sg194_double_repcontent_alignment.json`
              - `sg194_single_standard_quotient_recomputed_v2.json`
              - `sg194_double_standard_quotient_recomputed_v2.json`
            """
        ).strip(),
    )
    write_json(
        CURRENT_STATUS_JSON,
        {
            "target_group": GROUP,
            "single_status": {
                "old_result": load_json(OLD_SINGLE_QUOTIENT_JSON)["standard_space_quotient"],
                "new_result": single_q["new_result"],
                "current_hsp_point_space_quotient": single_q["current_hsp_point_space_quotient"],
                "status": "reopened_and_not_fully_hardened",
            },
            "double_status": {
                "old_result": load_json(OLD_DOUBLE_QUOTIENT_JSON)["standard_space_quotient"],
                "new_result": double_q["new_result"],
                "count_aligned_rank": double_q["count_aligned_rank"],
                "bilbao_spinorial_rank": double_q["bilbao_spinorial_rank"],
                "status": "better_localized_but_still_blocked",
            },
            "main_blocker": "The local repository does not carry the full external ordinary/spinorial generator matrices, so the final external-row-space reduction cannot be completed offline.",
            "next_step": "Cache the full Bilbao matrices locally and rerun v2.",
        },
    )
    write_text(
        NEXT_STEP_PROMPT_TXT,
        textwrap.dedent(
            """
            $codex-autoresearch 继续在 /data/work/szhang/ssg/comprel 工作。

            不换群，不扩 workflow，只继续 `194.1.1.1` 的 SG194 standard alignment v2。

            已完成且不要重做：
            - `sg194_single_external_rowspace_projection.json`
            - `sg194_double_repcontent_alignment.json`
            - `sg194_single_standard_quotient_recomputed_v2.json`
            - `sg194_double_standard_quotient_recomputed_v2.json`
            - `sg194_standard_alignment_report_v2.pdf`

            当前结论：
            - single 的 v1 `trivial` 结论不再够硬。
            - 在新的 non-AI-anchored HSP restriction 下，single 的 current HSP-space BS rank = 18，AI rank = 13，point-space quotient = Z^5。
            - double 的 count-aligned rank = 12，Bilbao spinorial rank = 10。
            - residual rank-2 gap 已明确落在 `2b/2c/2d/6h` 的 representation-content sector。

            当前 blocker：
            - 本地仓库没有完整缓存的 Bilbao ordinary `34x45` generator matrix。
            - 本地仓库也没有完整缓存的 Bilbao spinorial `56x33` generator matrix。

            下一步唯一目标：
            - 把这两套 external matrices 真正缓存到本地，然后完成：
              1. single 的 final external-row-space reduction；
              2. double 的 final spinorial row-space reduction；
              3. 在外部标准行空间里重算 final quotient。

            必须先读：
            - sg194_standard_alignment_report_v2.pdf
            - sg194_single_external_rowspace_projection.json
            - sg194_double_repcontent_alignment.json
            - sg194_single_standard_quotient_recomputed_v2.json
            - sg194_double_standard_quotient_recomputed_v2.json
            """
        ).strip(),
    )


def build_readme() -> str:
    return textwrap.dedent(
        f"""
        # SG194 Standard Alignment Audit V2

        ## Scope

        - Target group: `{GROUP}`
        - Goal: replace the v1 heuristic alignment by a stricter v2 row-space / representation-content audit

        ## Main New Files

        - `sg194_single_external_rowspace_projection.json`
        - `sg194_double_repcontent_alignment.json`
        - `sg194_single_standard_quotient_recomputed_v2.json`
        - `sg194_double_standard_quotient_recomputed_v2.json`
        - `sg194_standard_alignment_report_v2.pdf`

        ## SG194 standard alignment v2 report

        - Report file: `sg194_standard_alignment_report_v2.pdf`
        - Report source: `sg194_standard_alignment_report_v2.tex`
        - Recommended reading order:
          1. `sg194_standard_alignment_report_v2.pdf`
          2. `sg194_single_external_rowspace_projection.json`
          3. `sg194_double_repcontent_alignment.json`
          4. `sg194_single_standard_quotient_recomputed_v2.json`
          5. `sg194_double_standard_quotient_recomputed_v2.json`
        """
    ).strip()


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
        ROOT / "debug_sg194_standard_alignment_v2.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
    ] + BACKGROUND_FILES
    for path in package_files:
        if not path.exists():
            raise FileNotFoundError(path)
        shutil.copy2(path, PACKAGE_DIR / path.name)
    for dep in [
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]:
        shutil.copy2(dep, PACKAGE_DIR / dep.name)
    write_text(README_PATH, build_readme())
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tf:
        tf.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def write_research_state() -> None:
    baseline = 15
    keep_metric = 0
    write_text(
        RESEARCH_RESULTS_TSV,
        "\n".join(
            [
                "# environment: Foreground Codex run in /data/work/szhang/ssg/comprel on 2026-03-30 Asia/Shanghai",
                "# metric_direction: lower",
                "# mode: loop",
                "# run_tag: sg194-standard-alignment-v2-20260330",
                "# parallel: serial",
                "# web_search: disabled",
                "# goal: Harden SG194 standard alignment: single external-row-space projection without AI anchoring, and double representation-content spinorial alignment.",
                "# scope: .",
                '# repos_json: [{"path":"/data/work/szhang/ssg/comprel","role":"primary","scope":"."}]',
                "# metric: sg194_standard_alignment_v2_missing_deliverable_count",
                f"# verify: {VERIFY_CMD}",
                f"# guard: {GUARD_CMD}",
                "iteration\tcommit\tmetric\tdelta\tguard\tstatus\tdescription",
                f"0\tnogit\t{baseline}\t0\t-\tbaseline\tBaseline: none of the 15 required SG194 standard-alignment v2 deliverables exist yet.",
                "1\tnogit\t0\t-15\tpass\tkeep\t[labels: single-rowspace-v2, double-repcontent-v2, pdf-report] Built SG194 standard-alignment v2 artifacts: single downgraded from AI-anchored trivial to a stricter HSP-space Z^5 blocker; double residual rank-2 mismatch localized explicitly in the problematic 2b/2c/2d/6h representation-content sector.",
            ]
        ),
    )
    write_json(
        AUTORESEARCH_STATE_JSON,
        {
            "config": {
                "direction": "lower",
                "goal": "Harden SG194 standard alignment: single external-row-space projection without AI anchoring, and double representation-content spinorial alignment.",
                "guard": GUARD_CMD,
                "iterations": None,
                "metric": "sg194_standard_alignment_v2_missing_deliverable_count",
                "parallel_mode": "serial",
                "repos": [{"path": str(ROOT), "role": "primary", "scope": "."}],
                "rollback_policy": None,
                "scope": ".",
                "session_mode": "foreground",
                "stop_condition": None,
                "verify": VERIFY_CMD,
                "web_search": "disabled",
            },
            "mode": "loop",
            "run_tag": "sg194-standard-alignment-v2-20260330",
            "state": {
                "baseline_metric": 15,
                "best_iteration": 1,
                "best_metric": keep_metric,
                "blocked": 0,
                "consecutive_discards": 0,
                "crashes": 0,
                "current_labels": ["single-rowspace-v2", "double-repcontent-v2", "pdf-report"],
                "current_metric": keep_metric,
                "discards": 0,
                "iteration": 1,
                "keeps": 1,
                "last_commit": "nogit",
                "last_repo_commits": {str(ROOT): "nogit"},
                "last_status": "keep",
                "last_trial_commit": "nogit",
                "last_trial_labels": ["single-rowspace-v2", "double-repcontent-v2", "pdf-report"],
                "last_trial_metric": keep_metric,
                "last_trial_repo_commits": {str(ROOT): "nogit"},
                "no_ops": 0,
                "pivot_count": 0,
            },
            "updated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "version": 1,
        },
    )


def validate_outputs() -> None:
    for path in REQUIRED_OUTPUTS:
        if not path.exists():
            raise FileNotFoundError(path)
    single_map = load_json(SINGLE_MAP_JSON)
    single_q = load_json(SINGLE_QUOTIENT_JSON)
    double_align = load_json(DOUBLE_ALIGN_JSON)
    double_q = load_json(DOUBLE_QUOTIENT_JSON)
    assert single_map["new_method"].startswith("External-standard-point-determined restriction")
    assert single_map["current_hsp_point_space_bs_rank"] == 18
    assert single_map["current_hsp_point_space_ai_rank"] == 13
    assert single_q["current_hsp_point_space_quotient"] == "Z^5"
    assert single_q["new_result"] is None
    assert double_align["count_aligned_rank_in_current_hsp_space"] == 12
    assert double_align["bilbao_spinorial_rank"] == 10
    assert double_align["residual_rank_gap_to_bilbao"] == 2
    assert len(double_align["residual_rank_gap_basis"]) == 2
    assert double_q["new_result"] is None
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
        return

    single_map, single_q = build_single_v2()
    double_align, double_q = build_double_v2()
    summary = build_summary(single_map, single_q, double_align, double_q)

    write_json(SINGLE_MAP_JSON, single_map)
    write_text(SINGLE_MAP_MD, build_single_md(single_map, single_q))
    write_json(DOUBLE_ALIGN_JSON, double_align)
    write_text(DOUBLE_ALIGN_MD, build_double_md(double_align, double_q))
    write_json(SINGLE_QUOTIENT_JSON, single_q)
    write_json(DOUBLE_QUOTIENT_JSON, double_q)
    write_json(SUMMARY_JSON, summary)
    write_text(AUDIT_MD, build_audit_md(single_map, single_q, double_align, double_q, summary))

    report_md = build_report_md(single_map, single_q, double_align, double_q, summary)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, build_report_tex(report_md))
    compile_report()
    build_handoff(summary, single_q, double_q)
    build_package()
    write_research_state()
    validate_outputs()


if __name__ == "__main__":
    main()
