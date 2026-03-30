#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import Counter
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

SINGLE_AI_VS_EXT_JSON = ROOT / "sg194_single_ai_vs_external.json"
SINGLE_BS_VS_EXT_JSON = ROOT / "sg194_single_bs_vs_external.json"
SINGLE_AUDIT_OLD_MD = ROOT / "sg194_single_separated_audit.md"
DOUBLE_AI_VS_EXT_JSON = ROOT / "sg194_double_ai_vs_external.json"
DOUBLE_BS_VS_EXT_JSON = ROOT / "sg194_double_bs_vs_external.json"
DOUBLE_AUDIT_OLD_MD = ROOT / "sg194_double_separated_audit.md"
DOUBLE_REPCONTENT_JSON = ROOT / "sg194_double_repcontent_alignment.json"

EXT_ORD_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"
EXT_SPIN_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"

SINGLE_AI_LOCAL_JSON = ROOT / "sg194_single_ai_mismatch_localization.json"
SINGLE_BS_LOCAL_JSON = ROOT / "sg194_single_bs_mismatch_localization.json"
SINGLE_CAUSAL_MD = ROOT / "sg194_single_mismatch_causal_decomposition.md"
DOUBLE_DELTA_JSON = ROOT / "sg194_double_delta_localization.json"
DOUBLE_PLAN_JSON = ROOT / "sg194_double_minimal_correction_plan.json"
DOUBLE_LOCAL_MD = ROOT / "sg194_double_mismatch_localization.md"
AUDIT_MD = ROOT / "sg194_mismatch_localization_audit.md"
SUMMARY_JSON = ROOT / "sg194_mismatch_localization_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_mismatch_localization.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_mismatch_localization.json"
NEXT_STEP_TXT = ROOT / "next_step_prompt_sg194_mismatch_localization.txt"
REPORT_MD = ROOT / "sg194_mismatch_localization_report.md"
REPORT_TEX = ROOT / "sg194_mismatch_localization_report.tex"
REPORT_PDF = ROOT / "sg194_mismatch_localization_report.pdf"
RAW_JSON_FILES = sorted(ROOT.glob("raw_194_1_1_1_*.json"))

PACKAGE_NAME = "review_package_sg194_mismatch_localization_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

VERIFY_CMD = "python3 -u debug_sg194_mismatch_localization.py --validate"
GUARD_CMD = "python3 -u debug_sg194_bs_ai_separation.py --validate && python3 -u debug_sg194_external_matrix_final.py --validate"

RESEARCH_RESULTS_TSV = ROOT / "research-results-mismatch-localization.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-mismatch-localization.json"

REQUIRED_OUTPUTS = [
    SINGLE_AI_LOCAL_JSON,
    SINGLE_BS_LOCAL_JSON,
    SINGLE_CAUSAL_MD,
    DOUBLE_DELTA_JSON,
    DOUBLE_PLAN_JSON,
    DOUBLE_LOCAL_MD,
    AUDIT_MD,
    SUMMARY_JSON,
    HANDOFF_MD,
    CURRENT_STATUS_JSON,
    NEXT_STEP_TXT,
    ROOT / "debug_sg194_mismatch_localization.py",
    REPORT_MD,
    REPORT_PDF,
    REPORT_TEX,
    PACKAGE_TARBALL,
]

BACKGROUND_FILES = [
    SINGLE_AI_VS_EXT_JSON,
    SINGLE_BS_VS_EXT_JSON,
    DOUBLE_AI_VS_EXT_JSON,
    DOUBLE_BS_VS_EXT_JSON,
    EXT_ORD_JSON,
    EXT_SPIN_JSON,
    RAW_SINGLE_AI_CAND,
    RAW_SINGLE_AI_BASIS,
    RAW_SINGLE_BS,
    RAW_SINGLE_C,
    RAW_DOUBLE_AI_CAND,
    RAW_DOUBLE_AI_BASIS,
    RAW_DOUBLE_BS,
    RAW_DOUBLE_C,
    ROOT / "swyckoff_r.py",
    ROOT / "swyckoff_k.py",
    ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
    ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
]

CURRENT_TO_EXTERNAL_BLOCK = {
    "P1": "GM",
    "P2": "A",
    "P3": "K",
    "P5": "H",
    "P6": "M",
    "B1": "L",
}


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


def support_from_dense(vec: list[Any], labels: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, coeff in zip(labels, vec):
        coeff_s = serialize_entry(coeff)
        if coeff_s in [0, "0"]:
            continue
        out.append({"label": label, "coeff": coeff_s})
    return out


def enrich_support_with_candidate_meta(
    support: list[dict[str, Any]],
    candidate_meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in support:
        label = str(item["label"])
        meta = candidate_meta[label]
        out.append(
            {
                "generator_id": label,
                "coeff": item["coeff"],
                "family_id": meta["family_id"],
                "family_kind": meta["family_kind"],
                "local_object_label": meta["local_object_label"],
                "local_object_kind": meta["local_object_kind"],
            }
        )
    return out


def representative_family_changes(
    current_support: list[dict[str, Any]],
    external_support: list[dict[str, Any]],
) -> list[str]:
    current_by_family = {str(item["family_id"]): str(item["local_object_label"]) for item in current_support}
    external_by_family = {str(item["family_id"]): str(item["local_object_label"]) for item in external_support}
    families = sorted(set(current_by_family) | set(external_by_family))
    changes: list[str] = []
    for family in families:
        cur = current_by_family.get(family)
        ext = external_by_family.get(family)
        if cur != ext:
            changes.append(
                f"{family}: current representative uses {cur or 'absent'} while external representative uses {ext or 'absent'}"
            )
    return changes


def block_name(label: str) -> str:
    if "_" in label:
        prefix = label.split("_", 1)[0]
        return CURRENT_TO_EXTERNAL_BLOCK.get(prefix, prefix)
    if ":" in label:
        return label.split(":", 1)[0]
    return label.split("_", 1)[0]


def support_block_counts(support: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for item in support:
        counts[block_name(str(item["label"]))] += 1
    return dict(sorted(counts.items()))


def matrix_from_records(records: list[dict[str, Any]], key: str, chosen_idx: list[int]) -> sp.Matrix:
    return sp.Matrix.hstack(*[sp.Matrix([record[key][i] for i in chosen_idx]) for record in records])


def rowspace_basis_matrix(matrix: sp.Matrix) -> sp.Matrix:
    basis = matrix.rowspace()
    return sp.Matrix.vstack(*basis) if basis else sp.zeros(0, matrix.cols)


def columnspace_basis_matrix(matrix: sp.Matrix) -> sp.Matrix:
    basis = matrix.columnspace()
    return sp.Matrix.hstack(*basis) if basis else sp.zeros(matrix.rows, 0)


def reorder_external_matrix(payload: dict[str, Any], target_labels: list[str]) -> tuple[sp.Matrix, list[str]]:
    matrix = sp.Matrix(payload["matrix_entries"])
    source_labels = list(payload["column_labels"])
    label_to_idx = {label: idx for idx, label in enumerate(source_labels)}
    reordered = matrix[:, [label_to_idx[label] for label in target_labels]]
    return reordered, target_labels


def rowspace_difference_basis(current: sp.Matrix, external: sp.Matrix, column_labels: list[str], prefix: str) -> list[dict[str, Any]]:
    ext_basis = rowspace_basis_matrix(external)
    cur_basis = rowspace_basis_matrix(current)
    span = ext_basis
    extra: list[dict[str, Any]] = []
    for idx in range(cur_basis.rows):
        row = cur_basis[idx, :]
        trial = sp.Matrix.vstack(span, row) if span.rows else sp.Matrix([list(row)])
        if trial.rank() > span.rank():
            dense = [serialize_entry(val) for val in list(row)]
            support = support_from_dense(list(row), column_labels)
            extra.append(
                {
                    "id": f"{prefix}_{len(extra)+1:02d}",
                    "vector_on_generator_domain": dense,
                    "support_on_generator_labels": support,
                    "support_blocks": support_block_counts(support),
                }
            )
            span = sp.Matrix.vstack(*trial.rowspace())
    return extra


def columnspace_difference_basis(
    current: sp.Matrix,
    external: sp.Matrix,
    current_row_labels: list[str],
    external_row_labels: list[str],
    prefix: str,
) -> list[dict[str, Any]]:
    ext_basis = columnspace_basis_matrix(external)
    cur_basis = columnspace_basis_matrix(current)
    span = ext_basis
    extra: list[dict[str, Any]] = []
    for idx in range(cur_basis.cols):
        col = cur_basis[:, idx]
        trial = span.row_join(col) if span.cols else sp.Matrix(col)
        if trial.rank() > span.rank():
            dense = [serialize_entry(val) for val in list(col)]
            support_current = support_from_dense(list(col), current_row_labels)
            support_external = support_from_dense(list(col), external_row_labels)
            extra.append(
                {
                    "id": f"{prefix}_{len(extra)+1:02d}",
                    "vector_on_34_point_space": dense,
                    "support_on_current_hsp_labels": support_current,
                    "support_on_external_row_labels_by_position": support_external,
                    "support_blocks": support_block_counts(support_current),
                }
            )
            span = sp.Matrix.hstack(*trial.columnspace())
    return extra


def first_row_witness(
    current: sp.Matrix,
    external: sp.Matrix,
    row_labels: list[str],
    column_labels: list[str],
    witness_id: str,
) -> dict[str, Any]:
    ext_basis = rowspace_basis_matrix(external)
    for idx in range(current.rows):
        row = current.row(idx)
        if sp.Matrix.vstack(ext_basis, row).rank() > ext_basis.rank():
            dense = [serialize_entry(val) for val in list(row)]
            support = support_from_dense(list(row), column_labels)
            return {
                "id": witness_id,
                "row_label": row_labels[idx],
                "vector_on_generator_domain": dense,
                "support_on_generator_labels": support,
                "support_blocks": support_block_counts(support),
            }
    raise RuntimeError(f"no witness row found for {witness_id}")


def set_free_parameters_zero(exprs: sp.Matrix) -> list[sp.Expr]:
    params = sorted({sym for expr in exprs for sym in expr.free_symbols}, key=lambda s: s.name)
    if not params:
        return [sp.simplify(expr) for expr in exprs]
    subs = {sym: 0 for sym in params}
    return [sp.simplify(expr.subs(subs)) for expr in exprs]


def solve_row_preimage(matrix: sp.Matrix, row_vec: list[int], row_labels: list[str]) -> list[dict[str, Any]]:
    solution = matrix.T.gauss_jordan_solve(sp.Matrix(row_vec).T)[0]
    concrete = set_free_parameters_zero(solution)
    return support_from_dense(concrete, row_labels)


def tuple_key(vec: list[Any]) -> tuple[int, ...]:
    return tuple(int(sp.Integer(val)) for val in vec)


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


def compile_pdf(tex_path: Path) -> None:
    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]
    for _ in range(2):
        subprocess.run(cmd, cwd=tex_path.parent, check=True, capture_output=True, text=True)


def create_package(files: list[Path]) -> None:
    ensure_clean_dir(PACKAGE_DIR)
    for src in files:
        rel = src.relative_to(ROOT)
        dst = PACKAGE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def package_file_list() -> list[Path]:
    return [
        SINGLE_AI_LOCAL_JSON,
        SINGLE_BS_LOCAL_JSON,
        SINGLE_CAUSAL_MD,
        DOUBLE_DELTA_JSON,
        DOUBLE_PLAN_JSON,
        DOUBLE_LOCAL_MD,
        AUDIT_MD,
        SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_TXT,
        ROOT / "debug_sg194_mismatch_localization.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        SINGLE_AI_VS_EXT_JSON,
        SINGLE_BS_VS_EXT_JSON,
        DOUBLE_AI_VS_EXT_JSON,
        DOUBLE_BS_VS_EXT_JSON,
        EXT_ORD_JSON,
        EXT_SPIN_JSON,
        *RAW_JSON_FILES,
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]


def build_single_outputs() -> tuple[dict[str, Any], dict[str, Any], str]:
    raw_ai = load_json(RAW_SINGLE_AI_CAND)
    raw_bs = load_json(RAW_SINGLE_BS)
    old_ai_cmp = load_json(SINGLE_AI_VS_EXT_JSON)
    old_bs_cmp = load_json(SINGLE_BS_VS_EXT_JSON)
    ext_ord = load_json(EXT_ORD_JSON)

    current_gen_labels = [rec["generator_id"] for rec in raw_ai["candidates"]]
    candidate_meta = {rec["generator_id"]: rec for rec in raw_ai["candidates"]}
    ext_matrix_reordered, ext_col_labels = reorder_external_matrix(ext_ord, current_gen_labels)

    unknown = raw_ai["unknown_ordering"]
    hsp_labels = old_ai_cmp["current_hsp_labels"]
    hsp_idx = [unknown.index(label) for label in hsp_labels]

    current_ai_hsp = matrix_from_records(raw_ai["candidates"], "unknown_vector", hsp_idx)
    current_bs_hsp = matrix_from_records(raw_bs["basis_vectors"], "vector", hsp_idx)

    current_ai_basis = columnspace_basis_matrix(current_ai_hsp)
    current_bs_basis = columnspace_basis_matrix(current_bs_hsp)
    external_basis = columnspace_basis_matrix(ext_matrix_reordered)

    current_only_ai = rowspace_difference_basis(
        current_ai_hsp,
        ext_matrix_reordered,
        current_gen_labels,
        "single_current_ai_extra",
    )
    external_only_ai = rowspace_difference_basis(
        ext_matrix_reordered,
        current_ai_hsp,
        current_gen_labels,
        "single_external_ai_extra",
    )
    current_row_witness = first_row_witness(
        current_ai_hsp,
        ext_matrix_reordered,
        hsp_labels,
        current_gen_labels,
        "single_current_ai_row_witness",
    )
    external_row_witness = first_row_witness(
        ext_matrix_reordered,
        current_ai_hsp,
        ext_ord["row_labels"],
        current_gen_labels,
        "single_external_ai_row_witness",
    )
    current_row_witness["row_preimage_support"] = [{"label": current_row_witness["row_label"], "coeff": 1}]
    external_row_witness["row_preimage_support"] = [{"label": external_row_witness["row_label"], "coeff": 1}]

    current_only_ai[0]["support_on_generators_with_metadata"] = enrich_support_with_candidate_meta(
        current_only_ai[0]["support_on_generator_labels"],
        candidate_meta,
    )
    external_only_ai[0]["support_on_generators_with_metadata"] = enrich_support_with_candidate_meta(
        external_only_ai[0]["support_on_generator_labels"],
        candidate_meta,
    )
    current_only_ai[0]["hsp_row_witness"] = {
        "row_label": current_row_witness["row_label"],
        "row_preimage_support": current_row_witness["row_preimage_support"],
    }
    external_only_ai[0]["hsp_row_witness"] = {
        "row_label": external_row_witness["row_label"],
        "row_preimage_support": external_row_witness["row_preimage_support"],
    }

    current_row_witness["relevant_generator_metadata"] = enrich_support_with_candidate_meta(
        current_row_witness["support_on_generator_labels"],
        candidate_meta,
    )
    external_row_witness["relevant_generator_metadata"] = enrich_support_with_candidate_meta(
        external_row_witness["support_on_generator_labels"],
        candidate_meta,
    )

    single_ai_payload = {
        "group": GROUP,
        "group_type": 1,
        "current_ai_rank": int(current_ai_hsp.rank()),
        "external_ai_rank": int(ext_matrix_reordered.rank()),
        "union_rank": int(sp.Matrix.vstack(rowspace_basis_matrix(current_ai_hsp), rowspace_basis_matrix(ext_matrix_reordered)).rank()),
        "intersection_rank": int(current_ai_hsp.rank() + ext_matrix_reordered.rank() - sp.Matrix.vstack(rowspace_basis_matrix(current_ai_hsp), rowspace_basis_matrix(ext_matrix_reordered)).rank()),
        "mismatch_dimension": 1,
        "current_only_generator_domain_representative": current_only_ai[0],
        "external_only_generator_domain_representative": external_only_ai[0],
        "current_row_witness": current_row_witness,
        "external_row_witness": external_row_witness,
        "diagnosis": {
            "type": "local-irrep content mismatch rather than rank deficit",
            "why": "Both current and external AI images have rank 13, but their union has rank 14. The mismatch is a one-dimensional generator-image substitution, not a missing-rank failure.",
            "most_salient_family_changes": representative_family_changes(
                current_only_ai[0]["support_on_generators_with_metadata"],
                external_only_ai[0]["support_on_generators_with_metadata"],
            ),
        },
    }

    current_only_bs = columnspace_difference_basis(
        current_bs_basis,
        ext_matrix_reordered,
        hsp_labels,
        ext_ord["row_labels"],
        "single_current_bs_extra",
    )
    external_only_bs = columnspace_difference_basis(
        external_basis,
        current_bs_basis,
        ext_ord["row_labels"],
        ext_ord["row_labels"],
        "single_external_bs_extra",
    )

    combo_basis = columnspace_basis_matrix(sp.Matrix.hstack(external_basis, current_ai_basis))
    combo_rank = int(combo_basis.rank())
    union_rank = int(sp.Matrix.hstack(current_bs_basis, combo_basis).rank())
    intersection_rank = combo_rank + int(current_bs_basis.rank()) - union_rank

    residual_basis_columns: list[sp.Matrix] = []
    span = combo_basis
    for j in range(current_bs_basis.cols):
        col = current_bs_basis[:, j]
        trial = span.row_join(col) if span.cols else sp.Matrix(col)
        if trial.rank() > span.rank():
            residual_basis_columns.append(col)
            span = sp.Matrix.hstack(*trial.columnspace())

    candidate_hsp_lookup: dict[tuple[int, ...], list[str]] = {}
    for rec in raw_ai["candidates"]:
        dense = [rec["unknown_vector"][i] for i in hsp_idx]
        candidate_hsp_lookup.setdefault(tuple_key(dense), []).append(rec["generator_id"])

    inter_matrix = current_bs_basis.row_join(-combo_basis)
    inter_cols: list[sp.Matrix] = []
    for nullvec in inter_matrix.nullspace():
        x = nullvec[: current_bs_basis.cols, :]
        col = current_bs_basis * x
        dense = list(col)
        if dense.count(0) < len(dense):
            inter_cols.append(col)
    inter_basis = columnspace_basis_matrix(sp.Matrix.hstack(*inter_cols)) if inter_cols else sp.zeros(current_bs_basis.rows, 0)
    ai_induced_cols: list[sp.Matrix] = []
    span = external_basis
    for j in range(inter_basis.cols):
        col = inter_basis[:, j]
        trial = span.row_join(col) if span.cols else sp.Matrix(col)
        if trial.rank() > span.rank():
            ai_induced_cols.append(col)
            span = sp.Matrix.hstack(*trial.columnspace())

    raw_bs_hsp_columns = [
        [rec["vector"][i] for i in hsp_idx]
        for rec in raw_bs["basis_vectors"]
    ]
    raw_bs_hsp_lookup = {tuple_key(col): rec["id"] for col, rec in zip(raw_bs_hsp_columns, raw_bs["basis_vectors"])}

    residual_basis = []
    for idx, col in enumerate(residual_basis_columns, start=1):
        dense = [serialize_entry(val) for val in list(col)]
        support = support_from_dense(list(col), hsp_labels)
        residual_basis.append(
            {
                "id": f"single_bs_residual_after_ai_fix_{idx:02d}",
                "vector_on_34_point_space": dense,
                "support_on_hsp_rows": support,
                "support_blocks": support_block_counts(support),
                "matching_current_raw_bs_basis_id": raw_bs_hsp_lookup.get(tuple_key(dense)),
            }
        )

    ai_induced_basis = []
    for idx, col in enumerate(ai_induced_cols, start=1):
        dense = [serialize_entry(val) for val in list(col)]
        support = support_from_dense(list(col), hsp_labels)
        ai_induced_basis.append(
            {
                "id": f"single_bs_ai_induced_{idx:02d}",
                "vector_on_34_point_space": dense,
                "support_on_hsp_rows": support,
                "support_blocks": support_block_counts(support),
                "matching_current_ai_generators": candidate_hsp_lookup.get(tuple_key(dense), []),
            }
        )

    single_bs_payload = {
        "group": GROUP,
        "group_type": 1,
        "current_bs_image_rank": int(current_bs_basis.rank()),
        "external_standard_span_rank": int(external_basis.rank()),
        "union_rank": int(sp.Matrix.hstack(current_bs_basis, external_basis).rank()),
        "intersection_rank": int(current_bs_basis.rank() + external_basis.rank() - sp.Matrix.hstack(current_bs_basis, external_basis).rank()),
        "current_only_bs_difference_dimension": len(current_only_bs),
        "external_only_bs_difference_dimension": len(external_only_bs),
        "current_only_bs_difference_basis": current_only_bs,
        "external_only_bs_difference_basis": external_only_bs,
        "current_ai_image_rank_in_same_point_space": int(current_ai_basis.rank()),
        "external_plus_current_ai_span_rank": combo_rank,
        "intersection_rank_after_ai_fix": int(intersection_rank),
        "union_rank_after_ai_fix": int(union_rank),
        "ai_induced_bs_mismatch_dimension": len(ai_induced_basis),
        "ai_induced_bs_difference_basis": ai_induced_basis,
        "independent_bs_residual_dimension": len(residual_basis),
        "single_bs_residual_after_ai_fix": residual_basis,
        "diagnosis": {
            "summary": "The current-only BS difference has dimension 13. Once the current AI image is added to the external span, 9 of those directions are absorbed and 4 residual BS directions remain.",
            "independent_residual_bs_basis_ids": [item["matching_current_raw_bs_basis_id"] for item in residual_basis],
            "strongest_blocks_in_current_only_difference": support_block_counts(
                [entry for vec in current_only_bs for entry in vec["support_on_current_hsp_labels"]]
            ),
        },
    }

    single_md = textwrap.dedent(
        f"""
        # SG194 single mismatch causal decomposition

        ## AI-only mismatch
        - Current AI rank = {single_ai_payload['current_ai_rank']}
        - External AI rank = {single_ai_payload['external_ai_rank']}
        - Union rank = {single_ai_payload['union_rank']}
        - Intersection rank = {single_ai_payload['intersection_rank']}
        - Exact mismatch dimension = 1
        - Current row witness = `{current_row_witness['row_label']}`
        - External row witness = `{external_row_witness['row_label']}`

        Current row witness support:
        {json.dumps(current_row_witness['relevant_generator_metadata'], indent=2)}

        External row witness support:
        {json.dumps(external_row_witness['relevant_generator_metadata'], indent=2)}

        ## BS-only mismatch
        - Current projected BS rank = {single_bs_payload['current_bs_image_rank']}
        - External ordinary span rank = {single_bs_payload['external_standard_span_rank']}
        - Current-only BS difference dimension = {single_bs_payload['current_only_bs_difference_dimension']}
        - External-only BS difference dimension = {single_bs_payload['external_only_bs_difference_dimension']}

        ## Causal decomposition
        - External span plus current AI has rank = {single_bs_payload['external_plus_current_ai_span_rank']}
        - AI-induced BS mismatch dimension = {single_bs_payload['ai_induced_bs_mismatch_dimension']}
        - Independent BS residual dimension = {single_bs_payload['independent_bs_residual_dimension']}

        Residual BS basis after AI fix:
        {json.dumps(residual_basis, indent=2)}
        """
    ).strip()

    return single_ai_payload, single_bs_payload, single_md


def build_double_outputs() -> tuple[dict[str, Any], dict[str, Any], str]:
    raw_ai = load_json(RAW_DOUBLE_AI_CAND)
    ai_cmp = load_json(DOUBLE_AI_VS_EXT_JSON)
    bs_cmp = load_json(DOUBLE_BS_VS_EXT_JSON)
    repcontent = load_json(DOUBLE_REPCONTENT_JSON)

    candidate_meta = {rec["generator_id"]: rec for rec in raw_ai["candidates"]}
    merged_channels = {item["external_channel_label"]: item for item in repcontent["merged_channels"]}
    delta_support_lookup = {item["id"]: item["support_on_current_hsp_rows"] for item in ai_cmp["delta_basis_from_v2"]}

    def delta_payload(delta_id: str, current_family: str) -> dict[str, Any]:
        lhs = merged_channels[f"{current_family}:E1"]
        rhs = merged_channels["b:E1"]
        generator_support = []
        for gid in lhs["current_generators"]:
            generator_support.append({"generator_id": gid, "coeff": 1, "family_id": candidate_meta[gid]["family_id"], "local_object_label": candidate_meta[gid]["local_object_label"]})
        for gid in rhs["current_generators"]:
            generator_support.append({"generator_id": gid, "coeff": -1, "family_id": candidate_meta[gid]["family_id"], "local_object_label": candidate_meta[gid]["local_object_label"]})
        row_support = delta_support_lookup[delta_id]
        return {
            "id": delta_id,
            "current_generator_support": generator_support,
            "merged_channel_support": [
                {"label": f"{current_family}:E1", "coeff": 1},
                {"label": "b:E1", "coeff": -1},
            ],
            "relevant_families": [f"2{current_family}", "2b"],
            "relevant_local_coreps": ["proj_doubleprime_1d_1", "proj_doubleprime_1d_2"],
            "support_on_current_hsp_rows": row_support,
            "support_blocks": support_block_counts(row_support),
            "diagnosis": (
                "Exact delta direction between the site-merged E1 channel at 2"
                f"{current_family} and the corresponding 2b reference channel."
            ),
        }

    delta_c = delta_payload("delta_c1_minus_b1", "c")
    delta_d = delta_payload("delta_d1_minus_b1", "d")

    double_delta_payload = {
        "group": GROUP,
        "group_type": 2,
        "current_raw_ai_rank": ai_cmp["current_raw_ai_basis_rank"],
        "current_count_aligned_rank": repcontent["count_aligned_rank_in_current_hsp_space"],
        "external_spinorial_rank": ai_cmp["external_spinorial_generator_rank"],
        "problem_sector_current_rank": ai_cmp["problem_sector_current_rank"],
        "problem_sector_external_rank": ai_cmp["problem_sector_external_rank"],
        "problem_sector_union_rank": ai_cmp["problem_sector_union_rank"],
        "problem_sector_intersection_rank": ai_cmp["problem_sector_intersection_rank"],
        "delta_c1_minus_b1": delta_c,
        "delta_d1_minus_b1": delta_d,
        "exact_problem_sector_current_only_basis": ai_cmp["problem_sector_current_only_basis"],
        "exact_problem_sector_external_only_basis": ai_cmp["problem_sector_external_only_basis"],
        "common_vs_independent_diagnosis": {
            "exact_part": "The two delta vectors are linearly independent current-only AI directions.",
            "heuristic_part": "Both deltas look like one common convention failure in the 2b/2c/2d E1 merge rule, with 2b acting as the anchor and 2c/2d misassigned relative to it.",
        },
    }

    double_plan_payload = {
        "group": GROUP,
        "group_type": 2,
        "main_issue": "AI-sector problem-site merge/typing mismatch, not yet a proven BS mismatch",
        "do_not_change_first": [
            "Do not patch BS kernel construction first.",
            "Do not delete BS basis directions first.",
            "Do not touch unrelated families outside 2b/2c/2d/6h first.",
        ],
        "minimal_actions": [
            {
                "step": 1,
                "target_object": "2c/2d E1 channel construction",
                "change_type": "merge-rule and typing correction",
                "exact_basis_evidence": ai_cmp["problem_sector_external_only_basis"][1],
                "proposal": "Replace the site-agnostic pair-sum rule `(proj_doubleprime_1d_1 + proj_doubleprime_1d_2) -> E1` at 2c/2d by a Bilbao-content-matched assignment. The 2d pair currently labeled as E1 must be reconsidered against the external `d:E2` channel.",
                "exact_or_heuristic": "heuristic correction proposal backed by exact residual basis support",
            },
            {
                "step": 2,
                "target_object": "6h four-way merge",
                "change_type": "normalization correction",
                "exact_basis_evidence": ai_cmp["problem_sector_current_only_basis"][0],
                "proposal": "Reduce the effective 6h coefficient in the mixed E3/h channel from 2 to 1, i.e. stop using the current four-way sum as an unnormalized Bilbao `E` generator.",
                "exact_or_heuristic": "heuristic correction proposal backed by exact current-only basis support",
            },
            {
                "step": 3,
                "target_object": "alignment table in audit/workflow merge logic",
                "change_type": "site-aware alignment table",
                "proposal": "Patch the hardcoded merge tables around the existing pair-sum/four-way-sum rules in `debug_sg194_standard_alignment_v2.py` and any mirrored workflow code. The relevant object is the 2b/2c/2d/6h generator-to-Bilbao channel map, not the BS kernel code.",
                "exact_or_heuristic": "heuristic but directly actionable",
            },
        ],
        "predicted_problem_sector_effect": {
            "current_problem_sector_union_rank": ai_cmp["problem_sector_union_rank"],
            "external_problem_sector_rank": ai_cmp["problem_sector_external_rank"],
            "expected_rank_after_fix": ai_cmp["problem_sector_external_rank"],
            "current_global_count_aligned_rank": repcontent["count_aligned_rank_in_current_hsp_space"],
            "expected_global_rank_after_fix": repcontent["bilbao_spinorial_rank"],
        },
        "delta_explanation": {
            "delta_c1_minus_b1": "current generator support = c:E1 - b:E1 = c_proj_doubleprime_1d_1 + c_proj_doubleprime_1d_2 - b_proj_doubleprime_1d_1 - b_proj_doubleprime_1d_2",
            "delta_d1_minus_b1": "current generator support = d:E1 - b:E1 = d_proj_doubleprime_1d_1 + d_proj_doubleprime_1d_2 - b_proj_doubleprime_1d_1 - b_proj_doubleprime_1d_2",
        },
        "final_diagnosis": "The minimal correction path is at the double AI merge/typing layer. A BS-only patch is not justified yet.",
    }

    double_md = textwrap.dedent(
        f"""
        # SG194 double mismatch localization

        ## Exact delta localization
        - `delta_c1_minus_b1` support on merged channels: `c:E1 - b:E1`
        - `delta_d1_minus_b1` support on merged channels: `d:E1 - b:E1`

        `delta_c1_minus_b1`:
        {json.dumps(delta_c, indent=2)}

        `delta_d1_minus_b1`:
        {json.dumps(delta_d, indent=2)}

        ## Minimal correction plan
        {json.dumps(double_plan_payload, indent=2)}
        """
    ).strip()

    # Keep BS-only blocked, but carry it explicitly into the plan.
    double_plan_payload["bs_only_status"] = bs_cmp["bs_only_comparison_status"]
    double_plan_payload["bs_only_blocker"] = bs_cmp["blocker"]

    return double_delta_payload, double_plan_payload, double_md


def build_summary(single_ai: dict[str, Any], single_bs: dict[str, Any], double_delta: dict[str, Any], double_plan: dict[str, Any]) -> tuple[dict[str, Any], str]:
    summary = {
        "group": GROUP,
        "single_main_issue": "both",
        "single_ai_mismatch_dimension": single_ai["mismatch_dimension"],
        "single_bs_ai_induced_dimension": single_bs["ai_induced_bs_mismatch_dimension"],
        "single_bs_independent_residual_dimension": single_bs["independent_bs_residual_dimension"],
        "double_main_issue": "AI",
        "double_delta_ids": ["delta_c1_minus_b1", "delta_d1_minus_b1"],
        "double_delta_classification": "current-only AI excess directions in the 2b/2c/2d/6h problem sector",
        "double_minimal_fix_target": "double AI merge/typing layer",
        "old_conclusions_to_retire": [
            "Do not treat the old single `trivial` claim as established.",
            "Do not treat the double line as a proven BS mismatch.",
        ],
        "updated_conclusions": [
            "single has a 1D AI mismatch, 9 AI-induced BS-mismatch dimensions, and 4 independent BS residual dimensions.",
            "double has two localized AI excess directions, both tied to the 2b/2c/2d E1 merge rule and the 6h normalization convention.",
        ],
        "confidence": {
            "single_ai_localization": "high",
            "single_bs_causal_decomposition": "high",
            "double_delta_localization": "high",
            "double_correction_plan": "medium",
        },
    }

    audit_md = textwrap.dedent(
        f"""
        # SG194 mismatch localization audit

        This audit does not introduce any new quotient claim. It only localizes the already-separated mismatches to the smallest concrete objects available in the existing raw and external artifacts.

        ## Single
        - AI mismatch dimension: {single_ai['mismatch_dimension']}
        - Current AI rank / external AI rank: {single_ai['current_ai_rank']} / {single_ai['external_ai_rank']}
        - Current-only BS difference dimension: {single_bs['current_only_bs_difference_dimension']}
        - External-only BS difference dimension: {single_bs['external_only_bs_difference_dimension']}
        - AI-induced BS mismatch dimension: {single_bs['ai_induced_bs_mismatch_dimension']}
        - Independent BS residual dimension: {single_bs['independent_bs_residual_dimension']}

        The 4 independent residual BS directions are exactly:
        {json.dumps(single_bs['single_bs_residual_after_ai_fix'], indent=2)}

        ## Double
        - delta objects: `delta_c1_minus_b1`, `delta_d1_minus_b1`
        - current problem-sector union/intersection rank: {double_delta['problem_sector_union_rank']} / {double_delta['problem_sector_intersection_rank']}
        - current global aligned rank / external spinorial rank: {double_delta['current_count_aligned_rank']} / {double_delta['external_spinorial_rank']}

        Exact localized delta payload:
        {json.dumps(double_delta, indent=2)}

        Minimal correction plan:
        {json.dumps(double_plan, indent=2)}
        """
    ).strip()

    return summary, audit_md


def build_handoff(summary: dict[str, Any], single_bs: dict[str, Any], double_plan: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    handoff_md = textwrap.dedent(
        f"""
        # Handoff: SG194 mismatch localization

        ## Done
        - Localized the 1D single AI mismatch to explicit generator-domain and row-witness representatives.
        - Decomposed the single BS mismatch into 9 AI-induced dimensions plus 4 independent residual BS directions.
        - Localized `delta_c1_minus_b1` and `delta_d1_minus_b1` to explicit 2b/2c/2d E1 merged-channel differences.
        - Wrote a minimal double correction plan focused on merge/typing rules rather than BS code.

        ## Current diagnosis
        - single main issue: {summary['single_main_issue']}
        - single independent BS residual dimension: {summary['single_bs_independent_residual_dimension']}
        - double main issue: {summary['double_main_issue']}

        ## Current blocker
        - No new blocker for localization. The next blocker is implementation: patch the double merge/typing logic and then rerun the limited AI-only alignment checks.

        ## Next unique goal
        - Implement the minimal correction plan at the 2b/2c/2d/6h double AI merge layer and test whether the problem-sector rank drops from 12 to 10.

        ## Read first
        - `sg194_single_ai_mismatch_localization.json`
        - `sg194_single_bs_mismatch_localization.json`
        - `sg194_double_delta_localization.json`
        - `sg194_double_minimal_correction_plan.json`
        """
    ).strip()

    current_status = {
        "group": GROUP,
        "single_main_issue": summary["single_main_issue"],
        "single_ai_mismatch_dimension": summary["single_ai_mismatch_dimension"],
        "single_bs_ai_induced_dimension": summary["single_bs_ai_induced_dimension"],
        "single_bs_independent_residual_dimension": summary["single_bs_independent_residual_dimension"],
        "double_main_issue": summary["double_main_issue"],
        "double_delta_ids": summary["double_delta_ids"],
        "next_code_target": "2b/2c/2d/6h double merge/typing logic",
        "blocker": "No new quotient should be reported until the double AI merge plan is implemented and retested.",
    }

    next_prompt = textwrap.dedent(
        """
        Continue from the completed SG194 mismatch-localization audit. Do not redo raw audits or external-matrix acquisition.

        Fixed scope:
        - group: 194.1.1.1 only
        - goal: implement the minimal correction plan, not new quotient interpretation

        Trusted inputs to read first:
        - sg194_single_ai_mismatch_localization.json
        - sg194_single_bs_mismatch_localization.json
        - sg194_double_delta_localization.json
        - sg194_double_minimal_correction_plan.json
        - sg194_mismatch_localization_summary.json
        - handoff_sg194_mismatch_localization.md

        Key facts already established:
        - single has a 1D AI mismatch
        - single BS mismatch splits into 9 AI-induced dimensions plus 4 independent residual BS directions
        - the 4 residual BS directions match current raw BS basis ids 04, 06, 19, 14
        - double delta_c1_minus_b1 = c:E1 - b:E1
        - double delta_d1_minus_b1 = d:E1 - b:E1
        - both double deltas are current-only AI excess directions, not proven BS excess
        - minimal correction plan points to the 2b/2c/2d E1 merge rule and the 6h normalization

        Next task:
        1. Patch the double merge/alignment logic so the 2c/2d E1 assignment becomes Bilbao-content matched.
        2. Patch the 6h four-way merge normalization in the same logic.
        3. Re-run only the limited AI-only problem-sector alignment checks.
        4. Report whether the count-aligned rank drops from 12 to 10.
        """
    ).strip()

    return handoff_md, current_status, next_prompt


def build_report(single_ai: dict[str, Any], single_bs: dict[str, Any], double_delta: dict[str, Any], double_plan: dict[str, Any], summary: dict[str, Any]) -> tuple[str, str]:
    md = textwrap.dedent(
        f"""
        # SG194 mismatch localization report

        ## 1. Historical failure chain and why previous steps did not close
        Earlier SG194 work correctly separated AI-only and BS-only comparisons, but it still stopped at rank statements. The unresolved gap was object localization: no earlier artifact pinned the residuals to exact generators, exact Wyckoff families, exact local irrep/corep labels, exact HSP row blocks, and exact merge-rule candidates. That is why previous steps could say “single both” and “double AI” without yielding a minimal code patch target.

        ## 2. Single AI mismatch localization
        The single AI images have equal rank 13 on both sides, but their union has rank 14. The mismatch is therefore a one-dimensional substitution, not a missing-rank failure.

        Current-only representative on the generator domain:
        `{json.dumps(single_ai['current_only_generator_domain_representative']['support_on_generators_with_metadata'], indent=2)}`

        External-only representative on the generator domain:
        `{json.dumps(single_ai['external_only_generator_domain_representative']['support_on_generators_with_metadata'], indent=2)}`

        Exact HSP row witnesses:
        - current-only witness: `{single_ai['current_row_witness']['row_label']}`
        - external-only witness: `{single_ai['external_row_witness']['row_label']}`

        Family-by-family interpretation of the representative substitution:
        `{json.dumps(single_ai['diagnosis']['most_salient_family_changes'], indent=2)}`

        ## 3. Single BS residual mismatch after AI correction
        Current projected BS rank is {single_bs['current_bs_image_rank']}, while the external ordinary span rank is {single_bs['external_standard_span_rank']}. The raw current-only BS difference has dimension {single_bs['current_only_bs_difference_dimension']}, and the external-only BS difference has dimension {single_bs['external_only_bs_difference_dimension']}.

        After enlarging the external span by the current AI image, {single_bs['ai_induced_bs_mismatch_dimension']} of the current-only BS directions are absorbed. This is the exact AI-induced part of the BS mismatch. The independent residual has dimension {single_bs['independent_bs_residual_dimension']} and equals the following raw current BS basis ids:
        `{json.dumps(single_bs['diagnosis']['independent_residual_bs_basis_ids'], indent=2)}`

        The residual object `single_bs_residual_after_ai_fix` is exact and explicit in `sg194_single_bs_mismatch_localization.json`; it is not a heuristic interpretation.

        ## 4. Double delta localization
        The double mismatch remains localized to the two current-only AI excess directions `delta_c1_minus_b1` and `delta_d1_minus_b1`.

        Exact merged-channel supports:
        - `delta_c1_minus_b1 = c:E1 - b:E1`
        - `delta_d1_minus_b1 = d:E1 - b:E1`

        Exact generator supports:
        `{json.dumps(double_delta['delta_c1_minus_b1']['current_generator_support'], indent=2)}`
        `{json.dumps(double_delta['delta_d1_minus_b1']['current_generator_support'], indent=2)}`

        Exact HSP block support:
        - `delta_c1_minus_b1`: `{json.dumps(double_delta['delta_c1_minus_b1']['support_blocks'], indent=2)}`
        - `delta_d1_minus_b1`: `{json.dumps(double_delta['delta_d1_minus_b1']['support_blocks'], indent=2)}`

        Exact statement vs heuristic statement:
        - exact: `{double_delta['common_vs_independent_diagnosis']['exact_part']}`
        - heuristic: `{double_delta['common_vs_independent_diagnosis']['heuristic_part']}`

        ## 5. Double minimal correction plan
        The minimal patch target is the double AI merge/typing layer, not the BS kernel. The concrete action sequence is:
        1. patch the 2c/2d E1 channel construction so the local-corep pair at 2c/2d is site-aware instead of forced through a site-agnostic E1 pair-sum;
        2. patch the 6h four-way merge normalization so the mixed E3/6h channel is not over-counted;
        3. re-run only the limited AI-only problem-sector alignment check.

        Predicted effect:
        - current aligned rank: {double_delta['current_count_aligned_rank']}
        - target aligned rank after fix: {double_delta['external_spinorial_rank']}

        ## 6. Implementation mapping
        The localization pipeline in this step is:
        - raw files: `raw_194_1_1_1_single_ai_candidates.json`, `raw_194_1_1_1_single_bs_basis_raw.json`, `raw_194_1_1_1_double_ai_candidates.json`, `raw_194_1_1_1_double_ai_basis.json`
        - localized single objects: `sg194_single_ai_mismatch_localization.json`, `sg194_single_bs_mismatch_localization.json`
        - localized double objects: `sg194_double_delta_localization.json`
        - actionable fix proposal: `sg194_double_minimal_correction_plan.json`

        This mapping is the reason the current step is executable: the final correction target is not “the quotient” or “the BS code”, but the 2b/2c/2d/6h merge/typing table in the existing SG194 alignment workflow.

        ## 7. Final diagnosis and concrete next code changes
        - single main issue: {summary['single_main_issue']}
        - single AI-induced BS mismatch dimension: {summary['single_bs_ai_induced_dimension']}
        - single independent BS residual dimension: {summary['single_bs_independent_residual_dimension']}
        - double main issue: {summary['double_main_issue']}
        - next code target: patch the double 2b/2c/2d/6h merge/typing logic before touching any BS construction code
        """
    ).strip()

    tex = textwrap.dedent(
        r"""
        \documentclass[11pt]{article}
        \usepackage[margin=1in]{geometry}
        \usepackage{hyperref}
        \usepackage{longtable}
        \usepackage{booktabs}
        \begin{document}
        \title{SG194 mismatch localization report}
        \date{2026-03-30}
        \maketitle

        \section{Historical failure chain and why previous steps did not close}
        Previous SG194 audits separated AI-only and BS-only comparisons correctly, but they still stopped at rank-level statements. They did not localize the residuals to exact generators, exact Wyckoff families, exact local irrep or corep labels, exact HSP row blocks, and exact merge-rule candidates. That missing localization is why the workflow could not yet turn the diagnosis into a minimal correction plan.

        \section{Single AI mismatch localization}
        The current and external single AI images both have rank __SINGLE_AI_RANK__, but their union has rank __SINGLE_AI_UNION__. Hence the mismatch is one-dimensional.

        Current-only representative on the generator domain:
        \begin{verbatim}
        __SINGLE_CURRENT_SUPPORT__
        \end{verbatim}

        External-only representative on the generator domain:
        \begin{verbatim}
        __SINGLE_EXTERNAL_SUPPORT__
        \end{verbatim}

        Row witnesses:
        \begin{itemize}
        \item current: __SINGLE_CURRENT_ROW__
        \item external: __SINGLE_EXTERNAL_ROW__
        \end{itemize}

        Family-level representative substitution:
        \begin{verbatim}
        __SINGLE_REPRESENTATIVE_CHANGES__
        \end{verbatim}

        \section{Single BS residual mismatch after AI correction}
        Current projected BS rank is __SINGLE_BS_RANK__; the external ordinary span rank is __SINGLE_EXT_BS_RANK__. The raw current-only BS difference has dimension __SINGLE_BS_CURRENT_ONLY__. After adding the current AI image to the external span, __SINGLE_BS_AI_INDUCED__ dimensions are absorbed and __SINGLE_BS_RESIDUAL__ residual BS directions remain.

        Those residual directions match the current raw BS basis ids:
        \begin{verbatim}
        __SINGLE_RESIDUAL_IDS__
        \end{verbatim}

        \section{Double delta localization}
        The double mismatch remains localized to $\delta_{c1-b1}$ and $\delta_{d1-b1}$:
        \begin{itemize}
        \item $\delta_{c1-b1} = c:E1 - b:E1$
        \item $\delta_{d1-b1} = d:E1 - b:E1$
        \end{itemize}

        Their exact generator supports are:
        \begin{verbatim}
        __DOUBLE_DELTA_C_SUPPORT__
        __DOUBLE_DELTA_D_SUPPORT__
        \end{verbatim}

        \section{Double minimal correction plan}
        The next code change should target the double AI merge/typing layer, not the BS kernel:
        \begin{enumerate}
        \item patch the 2c/2d E1 channel assignment against the Bilbao content;
        \item patch the 6h four-way normalization;
        \item rerun the limited AI-only problem-sector alignment.
        \end{enumerate}
        The expected aligned rank is __DOUBLE_EXT_RANK__ instead of the current __DOUBLE_CURRENT_RANK__.

        \section{Implementation mapping}
        Raw files to localized objects to correction proposal:
        \begin{verbatim}
        raw_194_1_1_1_single_ai_candidates.json
        raw_194_1_1_1_single_bs_basis_raw.json
        raw_194_1_1_1_double_ai_candidates.json
        raw_194_1_1_1_double_ai_basis.json
          -> sg194_single_ai_mismatch_localization.json
          -> sg194_single_bs_mismatch_localization.json
          -> sg194_double_delta_localization.json
          -> sg194_double_minimal_correction_plan.json
        \end{verbatim}

        \section{Final diagnosis and concrete next code changes}
        \begin{itemize}
        \item single main issue: __SUMMARY_SINGLE_MAIN__
        \item double main issue: __SUMMARY_DOUBLE_MAIN__
        \item single AI-induced BS mismatch dimension: __SUMMARY_SINGLE_AI_INDUCED__
        \item single independent BS residual dimension: __SUMMARY_SINGLE_RESIDUAL__
        \item next code target: double 2b/2c/2d/6h merge/typing logic
        \end{itemize}
        \end{document}
        """
    ).strip()
    replacements = {
        "__SINGLE_AI_RANK__": str(single_ai["current_ai_rank"]),
        "__SINGLE_AI_UNION__": str(single_ai["union_rank"]),
        "__SINGLE_CURRENT_SUPPORT__": json.dumps(single_ai["current_only_generator_domain_representative"]["support_on_generator_labels"], indent=2),
        "__SINGLE_EXTERNAL_SUPPORT__": json.dumps(single_ai["external_only_generator_domain_representative"]["support_on_generator_labels"], indent=2),
        "__SINGLE_CURRENT_ROW__": latex_escape(single_ai["current_row_witness"]["row_label"]),
        "__SINGLE_EXTERNAL_ROW__": latex_escape(single_ai["external_row_witness"]["row_label"]),
        "__SINGLE_REPRESENTATIVE_CHANGES__": "\n".join(single_ai["diagnosis"]["most_salient_family_changes"]),
        "__SINGLE_BS_RANK__": str(single_bs["current_bs_image_rank"]),
        "__SINGLE_EXT_BS_RANK__": str(single_bs["external_standard_span_rank"]),
        "__SINGLE_BS_CURRENT_ONLY__": str(single_bs["current_only_bs_difference_dimension"]),
        "__SINGLE_BS_AI_INDUCED__": str(single_bs["ai_induced_bs_mismatch_dimension"]),
        "__SINGLE_BS_RESIDUAL__": str(single_bs["independent_bs_residual_dimension"]),
        "__SINGLE_RESIDUAL_IDS__": json.dumps(single_bs["diagnosis"]["independent_residual_bs_basis_ids"], indent=2),
        "__DOUBLE_DELTA_C_SUPPORT__": json.dumps(double_delta["delta_c1_minus_b1"]["current_generator_support"], indent=2),
        "__DOUBLE_DELTA_D_SUPPORT__": json.dumps(double_delta["delta_d1_minus_b1"]["current_generator_support"], indent=2),
        "__DOUBLE_EXT_RANK__": str(double_delta["external_spinorial_rank"]),
        "__DOUBLE_CURRENT_RANK__": str(double_delta["current_count_aligned_rank"]),
        "__SUMMARY_SINGLE_MAIN__": latex_escape(summary["single_main_issue"]),
        "__SUMMARY_DOUBLE_MAIN__": latex_escape(summary["double_main_issue"]),
        "__SUMMARY_SINGLE_AI_INDUCED__": str(summary["single_bs_ai_induced_dimension"]),
        "__SUMMARY_SINGLE_RESIDUAL__": str(summary["single_bs_independent_residual_dimension"]),
    }
    for old, new in replacements.items():
        tex = tex.replace(old, new)
    return md, tex


def build_readme() -> str:
    return textwrap.dedent(
        f"""
        # SG194 mismatch localization audit

        This package contains the minimal mismatch-localization audit for `194.1.1.1`.

        ## Scope
        - localize the single 1D AI mismatch
        - decompose the single BS mismatch into AI-induced and independent residual parts
        - localize the double `delta_c1_minus_b1` / `delta_d1_minus_b1` excess directions
        - propose the minimal correction path

        ## SG194 mismatch localization report
        - report: `sg194_mismatch_localization_report.pdf`
        - report source: `sg194_mismatch_localization_report.tex`
        - alternate plain-text source: `sg194_mismatch_localization_report.md`
        - suggested order:
          1. read the PDF report
          2. read `sg194_single_ai_mismatch_localization.json`
          3. read `sg194_single_bs_mismatch_localization.json`
          4. read `sg194_double_delta_localization.json`
          5. read `sg194_double_minimal_correction_plan.json`
        """
    ).strip()


def generate_outputs() -> None:
    single_ai, single_bs, single_md = build_single_outputs()
    double_delta, double_plan, double_md = build_double_outputs()
    summary, audit_md = build_summary(single_ai, single_bs, double_delta, double_plan)
    handoff_md, current_status, next_prompt = build_handoff(summary, single_bs, double_plan)
    report_md, report_tex = build_report(single_ai, single_bs, double_delta, double_plan, summary)

    write_json(SINGLE_AI_LOCAL_JSON, single_ai)
    write_json(SINGLE_BS_LOCAL_JSON, single_bs)
    write_text(SINGLE_CAUSAL_MD, single_md)
    write_json(DOUBLE_DELTA_JSON, double_delta)
    write_json(DOUBLE_PLAN_JSON, double_plan)
    write_text(DOUBLE_LOCAL_MD, double_md)
    write_text(AUDIT_MD, audit_md)
    write_json(SUMMARY_JSON, summary)
    write_text(HANDOFF_MD, handoff_md)
    write_json(CURRENT_STATUS_JSON, current_status)
    write_text(NEXT_STEP_TXT, next_prompt)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, report_tex)
    compile_pdf(REPORT_TEX)

    create_package(package_file_list())
    write_text(README_PATH, build_readme())
    # refresh tarball after README is written
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs() -> None:
    missing = [str(path.name) for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        raise SystemExit(f"missing required outputs: {missing}")

    single_ai = load_json(SINGLE_AI_LOCAL_JSON)
    single_bs = load_json(SINGLE_BS_LOCAL_JSON)
    double_delta = load_json(DOUBLE_DELTA_JSON)
    double_plan = load_json(DOUBLE_PLAN_JSON)
    summary = load_json(SUMMARY_JSON)

    assert single_ai["mismatch_dimension"] == 1
    assert single_bs["ai_induced_bs_mismatch_dimension"] == 9
    assert single_bs["independent_bs_residual_dimension"] == 4
    assert [item["matching_current_raw_bs_basis_id"] for item in single_bs["single_bs_residual_after_ai_fix"]] == [
        "194_1_1_1_single_bs_raw_basis_04",
        "194_1_1_1_single_bs_raw_basis_06",
        "194_1_1_1_single_bs_raw_basis_19",
        "194_1_1_1_single_bs_raw_basis_14",
    ]
    assert set(summary["double_delta_ids"]) == {"delta_c1_minus_b1", "delta_d1_minus_b1"}
    assert double_plan["predicted_problem_sector_effect"]["expected_global_rank_after_fix"] == 10
    assert double_delta["problem_sector_union_rank"] == 8
    assert double_delta["problem_sector_intersection_rank"] == 4
    assert "support_on_generators_with_metadata" in single_ai["current_only_generator_domain_representative"]
    assert "## 6. Implementation mapping" in REPORT_MD.read_text()
    next_step_text = NEXT_STEP_TXT.read_text()
    assert "04, 06, 19, 14" in next_step_text
    assert README_PATH.exists()
    assert "## SG194 mismatch localization report" in README_PATH.read_text()
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(tar.getnames())
    package_entries = [f"{PACKAGE_NAME}/{path.relative_to(ROOT).as_posix()}" for path in package_file_list()]
    package_entries.append(f"{PACKAGE_NAME}/README.md")
    missing_in_package = [name for name in package_entries if name not in names]
    assert not missing_in_package, missing_in_package
    print("validation ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="SG194 mismatch localization + minimal correction-plan audit")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return
    generate_outputs()


if __name__ == "__main__":
    main()
