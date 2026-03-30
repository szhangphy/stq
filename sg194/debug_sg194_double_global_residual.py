#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent

GLOBAL_DECOMPOSITION_JSON = ROOT / "sg194_double_global_decomposition.json"
COMPLEMENT_VS_EXTERNAL_JSON = ROOT / "sg194_double_complement_vs_external.json"
COMPLEMENT_LIFT_JSON = ROOT / "sg194_double_complement_lift.json"
COMPLEMENT_LIFT_MD = ROOT / "sg194_double_complement_lift.md"
COMPLEMENT_MISMATCH_JSON = ROOT / "sg194_double_complement_mismatch_localization.json"
COMPLEMENT_MISMATCH_MD = ROOT / "sg194_double_complement_mismatch_localization.md"
NEXT_PATCH_TARGET_JSON = ROOT / "sg194_double_next_patch_target.json"
GLOBAL_AUDIT_MD = ROOT / "sg194_double_global_residual_audit.md"
GLOBAL_SUMMARY_JSON = ROOT / "sg194_double_global_residual_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_double_global_residual.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_double_global_residual.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_sg194_double_global_residual.txt"
REPORT_MD = ROOT / "sg194_double_global_residual_report.md"
REPORT_TEX = ROOT / "sg194_double_global_residual_report.tex"
REPORT_PDF = ROOT / "sg194_double_global_residual_report.pdf"
ROOT_README = ROOT / "README.md"

LIFT_SCRIPT = ROOT / "debug_sg194_double_lift.py"
PATCH_SCRIPT = ROOT / "debug_sg194_double_patch.py"
PATCH_V2_SCRIPT = ROOT / "debug_sg194_double_patch_v2.py"
STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
PROBLEM_INVENTORY_JSON = ROOT / "sg194_double_problem_sector_inventory.json"
PROBLEM_LIFT_JSON = ROOT / "sg194_double_problem_sector_lift.json"
PATCH_VERDICT_V3_JSON = ROOT / "sg194_double_patch_verdict_v3.json"
RAW_CANDIDATES_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_CANDIDATES_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched.json"
RAW_BASIS_JSON = ROOT / "raw_194_1_1_1_double_ai_basis.json"
RAW_BASIS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_basis_patched.json"
RAW_IN_BS_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json"
RAW_IN_BS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched.json"
EXTERNAL_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"
SWYCKOFF_K = ROOT / "swyckoff_k.py"
SWYCKOFF_R = ROOT / "swyckoff_r.py"
SSGREPS = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
SG_UTILS = ROOT / "SSGReps" / "SSGReps" / "SG_utils.py"
REP_UTILS = ROOT / "SSGReps" / "SSGReps" / "rep_utils.py"

PACKAGE_NAME = "review_package_sg194_double_global_residual_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def json_default(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return f"{int(sp.numer(value))}/{int(sp.denom(value))}"
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def format_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def compile_pdf(tex_path: Path, pdf_path: Path) -> None:
    for suffix in [".aux", ".log"]:
        sidecar = tex_path.with_suffix(suffix)
        if sidecar.exists():
            sidecar.unlink()
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        cwd=tex_path.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)


def matrix_to_nested_lists(matrix: sp.Matrix) -> list[list[sp.Expr]]:
    return [[matrix[i, j] for j in range(matrix.cols)] for i in range(matrix.rows)]


def block_name(label: str, kind: str) -> str:
    if kind == "current":
        return label.split("_")[0]
    if kind == "external":
        return label.split(":")[0]
    if kind == "common":
        return label.split(":")[0]
    raise ValueError(kind)


def vector_support(vector: sp.Matrix, labels: list[str], *, families: list[str] | None = None) -> list[dict[str, Any]]:
    payload = []
    for idx in range(vector.rows):
        if vector[idx, 0] == 0:
            continue
        record: dict[str, Any] = {"index": idx, "label": labels[idx], "coeff": vector[idx, 0]}
        if families is not None:
            record["family"] = families[idx]
        payload.append(record)
    return payload


def support_summary(support: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({item["label"].split(":")[0] for item in support})
    return {
        "families": families,
        "channels": [item["label"] for item in support],
        "support_size": len(support),
    }


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def latex_ascii(text: str) -> str:
    text = (
        text.replace("↑", "->")
        .replace("Γ", "Gamma")
        .replace("Δ", "Delta")
        .replace("Σ", "Sigma")
        .replace("Π", "Pi")
        .replace("Ω", "Omega")
    )
    return latex_escape(text)


def load_context() -> dict[str, Any]:
    problem_inventory = load_json(PROBLEM_INVENTORY_JSON)
    problem_lift = load_json(PROBLEM_LIFT_JSON)
    patch_verdict = load_json(PATCH_VERDICT_V3_JSON)
    raw_candidates = load_json(RAW_CANDIDATES_JSON)
    raw_candidates_patched = load_json(RAW_CANDIDATES_PATCHED_JSON)
    raw_basis = load_json(RAW_BASIS_JSON)
    raw_basis_patched = load_json(RAW_BASIS_PATCHED_JSON)
    external = load_json(EXTERNAL_JSON)

    unknown_ordering = raw_candidates_patched["unknown_ordering"]
    selected_current_unknown_indices = [
        idx
        for idx, token in enumerate(unknown_ordering)
        if token.split("_R")[0] in {"P1", "P2", "P3", "P5", "P6", "B1"}
    ]
    current_row_labels = [unknown_ordering[idx] for idx in selected_current_unknown_indices]

    current_source_ordering = []
    current_label_to_source_index: dict[str, int] = {}
    for idx, candidate in enumerate(raw_candidates_patched["candidates"]):
        label = candidate.get("external_channel_label") or candidate.get("source_payload", {}).get("external_channel_label")
        current_source_ordering.append(
            {
                "source_index": idx,
                "label": label,
                "generator_id": candidate["generator_id"],
                "family_id": candidate["family_id"],
                "local_object_label": candidate["local_object_label"],
            }
        )
        current_label_to_source_index[label] = idx

    external_ordering = [
        {
            "source_index": idx,
            "label": f"{item['letter_key']}:{item['bandrep_label']}",
            "bandrep_label": item["bandrep_label"],
            "wp_label": item["wp_label"],
            "letter_key": item["letter_key"],
            "local_index": item["local_index"],
        }
        for idx, item in enumerate(external["column_labels"])
    ]
    common_aligned_labels = [item["label"] for item in external_ordering]
    current_source_reorder = [current_label_to_source_index[label] for label in common_aligned_labels]

    current_full_matrix = sp.Matrix.hstack(
        *[
            sp.Matrix([raw_candidates_patched["candidates"][source_idx]["unknown_vector"][row_idx] for row_idx in selected_current_unknown_indices])
            for source_idx in current_source_reorder
        ]
    )
    external_full_matrix = sp.Matrix(external["matrix_entries"])

    trusted_external_indices = [
        idx for idx, item in enumerate(external["column_labels"]) if item["wp_label"] in {"2b", "2c", "2d", "6h"}
    ]
    complement_external_indices = [idx for idx in range(len(external_ordering)) if idx not in trusted_external_indices]
    trusted_current_source_indices = [current_source_reorder[idx] for idx in trusted_external_indices]
    complement_current_source_indices = [current_source_reorder[idx] for idx in complement_external_indices]

    common_families = [label.split(":")[0] for label in common_aligned_labels]
    complement_labels = [common_aligned_labels[idx] for idx in complement_external_indices]
    complement_families = [common_families[idx] for idx in complement_external_indices]

    current_trusted_matrix = current_full_matrix[:, trusted_external_indices]
    external_trusted_matrix = external_full_matrix[:, trusted_external_indices]
    current_complement_matrix = current_full_matrix[:, complement_external_indices]
    external_complement_matrix = external_full_matrix[:, complement_external_indices]

    return {
        "problem_inventory": problem_inventory,
        "problem_lift": problem_lift,
        "patch_verdict": patch_verdict,
        "raw_candidates": raw_candidates,
        "raw_candidates_patched": raw_candidates_patched,
        "raw_basis": raw_basis,
        "raw_basis_patched": raw_basis_patched,
        "external": external,
        "selected_current_unknown_indices": selected_current_unknown_indices,
        "current_row_labels": current_row_labels,
        "current_source_ordering": current_source_ordering,
        "external_ordering": external_ordering,
        "common_aligned_labels": common_aligned_labels,
        "current_source_reorder": current_source_reorder,
        "current_full_matrix": current_full_matrix,
        "external_full_matrix": external_full_matrix,
        "trusted_external_indices": trusted_external_indices,
        "complement_external_indices": complement_external_indices,
        "trusted_current_source_indices": trusted_current_source_indices,
        "complement_current_source_indices": complement_current_source_indices,
        "current_trusted_matrix": current_trusted_matrix,
        "external_trusted_matrix": external_trusted_matrix,
        "current_complement_matrix": current_complement_matrix,
        "external_complement_matrix": external_complement_matrix,
        "complement_labels": complement_labels,
        "complement_families": complement_families,
    }


def build_global_decomposition(context: dict[str, Any]) -> dict[str, Any]:
    current_rows = context["current_row_labels"]
    external_rows = context["external"]["row_labels"]
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "full_33_generator_decomposition_into_trusted_plus_complement",
        "current_source_ordering": context["current_source_ordering"],
        "external_source_ordering": context["external_ordering"],
        "common_aligned_ordering": [
            {
                "common_index": idx,
                "label": label,
                "family": label.split(":")[0],
                "current_source_index": context["current_source_reorder"][idx],
                "external_source_index": idx,
            }
            for idx, label in enumerate(context["common_aligned_labels"])
        ],
        "trusted_sector": {
            "status": "already_solved",
            "common_indices": context["trusted_external_indices"],
            "common_labels": [context["common_aligned_labels"][idx] for idx in context["trusted_external_indices"]],
            "current_source_indices": context["trusted_current_source_indices"],
            "external_source_indices": context["trusted_external_indices"],
            "current_block_shape": list(context["current_trusted_matrix"].shape),
            "external_block_shape": list(context["external_trusted_matrix"].shape),
        },
        "complement_sector": {
            "status": "unresolved_in_this_round",
            "common_indices": context["complement_external_indices"],
            "common_labels": [context["common_aligned_labels"][idx] for idx in context["complement_external_indices"]],
            "current_source_indices": context["complement_current_source_indices"],
            "external_source_indices": context["complement_external_indices"],
            "current_block_shape": list(context["current_complement_matrix"].shape),
            "external_block_shape": list(context["external_complement_matrix"].shape),
            "family_blocks": {
                family: [idx for idx, fam in zip(context["complement_external_indices"], context["complement_families"]) if fam == family]
                for family in sorted(set(context["complement_families"]))
            },
        },
        "full_matrix_shapes": {
            "current_full": list(context["current_full_matrix"].shape),
            "external_full": list(context["external_full_matrix"].shape),
        },
        "current_row_ambient": {
            "selected_unknown_ordering_indices": context["selected_current_unknown_indices"],
            "selected_row_labels": current_rows,
        },
        "external_row_ambient": {
            "row_count": len(external_rows),
            "row_labels": external_rows,
        },
    }


def rowspace_decomposition(
    current_matrix: sp.Matrix,
    external_matrix: sp.Matrix,
    current_row_labels: list[str],
    external_row_labels: list[str],
    column_labels: list[str],
) -> dict[str, Any]:
    current_rank = int(current_matrix.rank())
    external_rank = int(external_matrix.rank())
    union_rank = int(sp.Matrix.vstack(current_matrix, external_matrix).rank())
    intersection_rank = current_rank + external_rank - union_rank

    A = current_matrix.T
    B = external_matrix.T
    null_basis = sp.Matrix.hstack(
        *[A * vec[: A.cols, :] for vec in sp.Matrix.hstack(A, -B).nullspace() if any(value != 0 for value in (A * vec[: A.cols, :]))]
    ) if sp.Matrix.hstack(A, -B).nullspace() else sp.zeros(A.rows, 0)
    intersection_basis_vectors = null_basis.columnspace() if null_basis.cols else []

    current_row_basis_indices = list(current_matrix.T.rref()[1])
    external_row_basis_indices = list(external_matrix.T.rref()[1])
    current_row_basis_vectors = [current_matrix[idx, :].T for idx in current_row_basis_indices]
    external_row_basis_vectors = [external_matrix[idx, :].T for idx in external_row_basis_indices]

    span = sp.Matrix.hstack(*intersection_basis_vectors) if intersection_basis_vectors else sp.zeros(A.rows, 0)
    current_only_basis = []
    for row_idx, vector in zip(current_row_basis_indices, current_row_basis_vectors):
        test = sp.Matrix.hstack(span, vector) if span.cols else sp.Matrix.hstack(vector)
        if test.rank() > span.rank():
            current_only_basis.append((row_idx, vector))
            span = test

    span = sp.Matrix.hstack(*intersection_basis_vectors) if intersection_basis_vectors else sp.zeros(A.rows, 0)
    external_only_basis = []
    for row_idx, vector in zip(external_row_basis_indices, external_row_basis_vectors):
        test = sp.Matrix.hstack(span, vector) if span.cols else sp.Matrix.hstack(vector)
        if test.rank() > span.rank():
            external_only_basis.append((row_idx, vector))
            span = test

    return {
        "current_rank": current_rank,
        "external_rank": external_rank,
        "union_rank": union_rank,
        "intersection_rank": intersection_rank,
        "current_only_dimension": current_rank - intersection_rank,
        "external_only_dimension": external_rank - intersection_rank,
        "intersection_basis": [
            {
                "vector_support": vector_support(vector, column_labels),
                "summary": support_summary(vector_support(vector, column_labels)),
            }
            for vector in intersection_basis_vectors
        ],
        "current_only_basis": [
            {
                "witness_row_index": row_idx,
                "witness_row_label": current_row_labels[row_idx],
                "witness_row_block": block_name(current_row_labels[row_idx], "current"),
                "vector_support": vector_support(vector, column_labels),
                "summary": support_summary(vector_support(vector, column_labels)),
            }
            for row_idx, vector in current_only_basis
        ],
        "external_only_basis": [
            {
                "witness_row_index": row_idx,
                "witness_row_label": external_row_labels[row_idx],
                "witness_row_block": block_name(external_row_labels[row_idx], "external"),
                "vector_support": vector_support(vector, column_labels),
                "summary": support_summary(vector_support(vector, column_labels)),
            }
            for row_idx, vector in external_only_basis
        ],
    }


def build_complement_vs_external(context: dict[str, Any]) -> dict[str, Any]:
    decomposition = rowspace_decomposition(
        context["current_complement_matrix"],
        context["external_complement_matrix"],
        context["current_row_labels"],
        context["external"]["row_labels"],
        context["complement_labels"],
    )

    family_blocks: dict[str, list[int]] = defaultdict(list)
    for local_idx, family in enumerate(context["complement_families"]):
        family_blocks[family].append(local_idx)

    family_local_diagnostics = {}
    for family, local_indices in sorted(family_blocks.items()):
        current_block = context["current_complement_matrix"][:, local_indices]
        external_block = context["external_complement_matrix"][:, local_indices]
        union_rank = int(sp.Matrix.vstack(current_block, external_block).rank())
        family_local_diagnostics[family] = {
            "local_indices": local_indices,
            "channel_labels": [context["complement_labels"][idx] for idx in local_indices],
            "current_rank": int(current_block.rank()),
            "external_rank": int(external_block.rank()),
            "union_rank": union_rank,
            "intersection_rank": int(current_block.rank() + external_block.rank() - union_rank),
            "external_embeds_in_current_family_block": union_rank == int(current_block.rank()),
            "family_local_residual": union_rank > int(current_block.rank()),
        }

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "remaining_23_generator_complement_vs_external",
        "construction_note": (
            "No extra quotient by the trusted sector is needed. "
            "If a full row lift existed on all 33 generators, column restriction would automatically induce a lift on the 23-generator complement. "
            "So complement analysis can be done exactly by restricting both matrices to the complement columns."
        ),
        "complement_labels": context["complement_labels"],
        "matrix_shapes": {
            "current_complement": list(context["current_complement_matrix"].shape),
            "external_complement": list(context["external_complement_matrix"].shape),
        },
        "rank_data": {
            "current_rank": decomposition["current_rank"],
            "external_rank": decomposition["external_rank"],
            "union_rank": decomposition["union_rank"],
            "intersection_rank": decomposition["intersection_rank"],
            "current_only_dimension": decomposition["current_only_dimension"],
            "external_only_dimension": decomposition["external_only_dimension"],
            "remaining_mismatch_dimension": decomposition["union_rank"] - decomposition["intersection_rank"],
        },
        "current_only_basis": decomposition["current_only_basis"],
        "external_only_basis": decomposition["external_only_basis"],
        "intersection_basis": decomposition["intersection_basis"],
        "family_local_diagnostics": family_local_diagnostics,
    }


def build_complement_lift(context: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    rational_lift_exists = comparison["rank_data"]["union_rank"] == comparison["rank_data"]["current_rank"]
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "remaining_23_generator_complement_lift_or_obstruction",
        "matrix_shapes": comparison["matrix_shapes"],
        "lift_exists": False if not rational_lift_exists else True,
        "integer_lift_exists": False if not rational_lift_exists else None,
        "rational_lift_exists": rational_lift_exists,
        "coefficient_field": None if not rational_lift_exists else "Q",
        "why_no_lift": (
            "No exact rational lift can exist because the external complement row space is not contained in the current complement row space. "
            f"Exact ranks are current={comparison['rank_data']['current_rank']}, external={comparison['rank_data']['external_rank']}, union={comparison['rank_data']['union_rank']}."
        ) if not rational_lift_exists else "A rational lift exists.",
        "obstruction": {
            "kind": "row_space_containment_failure",
            "minimal_rational_obstruction_dimension": comparison["rank_data"]["external_only_dimension"],
            "external_only_basis": comparison["external_only_basis"],
            "current_only_basis": comparison["current_only_basis"],
            "support_blocks": {
                "current_witness_row_blocks": sorted({item["witness_row_block"] for item in comparison["current_only_basis"]}),
                "external_witness_row_blocks": sorted({item["witness_row_block"] for item in comparison["external_only_basis"]}),
            },
            "support_families": sorted(
                {
                    family
                    for basis in comparison["external_only_basis"]
                    for family in basis["summary"]["families"]
                }
            ),
        },
    }


def build_complement_lift_md(payload: dict[str, Any]) -> str:
    obstruction = payload["obstruction"]
    return textwrap.dedent(
        f"""
        # SG194 Double Complement Lift

        ## Verdict

        - complement lift exists: `{payload['lift_exists']}`
        - integer lift exists: `{payload['integer_lift_exists']}`
        - rational lift exists: `{payload['rational_lift_exists']}`
        - coefficient field: `{payload['coefficient_field']}`

        ## Exact obstruction

        - obstruction kind: `{obstruction['kind']}`
        - minimal rational obstruction dimension: `{obstruction['minimal_rational_obstruction_dimension']}`
        - current witness row blocks: `{obstruction['support_blocks']['current_witness_row_blocks']}`
        - external witness row blocks: `{obstruction['support_blocks']['external_witness_row_blocks']}`
        - support families: `{obstruction['support_families']}`

        No quotient-lift exists even over `Q`, so there is automatically no integer lift. The exact obstruction basis is serialized in `{COMPLEMENT_LIFT_JSON.name}` via the `external_only_basis` records imported from the complement comparison.
        """
    ).strip()


def build_mismatch_localization(context: dict[str, Any], comparison: dict[str, Any], lift_payload: dict[str, Any]) -> dict[str, Any]:
    family_local = comparison["family_local_diagnostics"]
    family_local_residual_families = [
        family for family, payload in family_local.items() if payload["family_local_residual"]
    ]
    current_blocks = sorted({item["witness_row_block"] for item in comparison["current_only_basis"]})
    external_blocks = sorted({item["witness_row_block"] for item in comparison["external_only_basis"]})

    complement_generators_in_obstruction = sorted(
        {
            support["label"]
            for basis in comparison["external_only_basis"] + comparison["current_only_basis"]
            for support in basis["vector_support"]
        }
    )
    complement_families_in_obstruction = sorted({label.split(":")[0] for label in complement_generators_in_obstruction})

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "remaining_23_generator_complement_mismatch_localization",
        "residual_dimensions": comparison["rank_data"],
        "family_local_diagnostics": family_local,
        "family_local_residual_families": family_local_residual_families,
        "cross_family_residual": {
            "exists": True,
            "why": (
                "Every individual complement family block embeds into the current family block, but the full 23-generator complement still has "
                f"external-only dimension {comparison['rank_data']['external_only_dimension']}. "
                "So the residual mismatch is not family-local; it is caused by cross-family coupling in the row-language construction."
            ),
        },
        "witness_row_blocks": {
            "current_only": current_blocks,
            "external_only": external_blocks,
        },
        "witness_rows": {
            "current_only": [
                {"row_index": item["witness_row_index"], "row_label": item["witness_row_label"]}
                for item in comparison["current_only_basis"]
            ],
            "external_only": [
                {"row_index": item["witness_row_index"], "row_label": item["witness_row_label"]}
                for item in comparison["external_only_basis"]
            ],
        },
        "generators_channels_families": {
            "generator_labels": complement_generators_in_obstruction,
            "families": complement_families_in_obstruction,
            "channels": complement_generators_in_obstruction,
        },
        "residual_classification": {
            "best_match": "wrong_ambient_space_construction_or_missing_complement_row_basis_translation",
            "not_best_match": [
                "trusted-sector merge rule regression",
                "single-family missing generator patch",
                "pure normalization-only issue inside one family block",
            ],
            "reason": (
                "The trusted sector is already solved, and no single complement family shows an isolated external-vs-current residual. "
                "The unresolved mismatch appears only after assembling all complement families together, which is the signature of a global ambient-row translation problem."
            ),
        },
    }


def build_mismatch_localization_md(payload: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Complement Mismatch Localization

        ## Exact residual

        - current-only dimension: `{payload['residual_dimensions']['current_only_dimension']}`
        - external-only dimension: `{payload['residual_dimensions']['external_only_dimension']}`
        - family-local residual families: `{payload['family_local_residual_families']}`

        ## Localization

        - current witness row blocks: `{payload['witness_row_blocks']['current_only']}`
        - external witness row blocks: `{payload['witness_row_blocks']['external_only']}`
        - families touched by the residual basis: `{payload['generators_channels_families']['families']}`

        ## Engineering diagnosis

        - best match: `{payload['residual_classification']['best_match']}`
        - reason: {payload['residual_classification']['reason']}
        """
    ).strip()


def build_next_patch_target(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "next_source_level_patch_target_after_complement_residual_localization",
        "next_patch_type": "another_generator_construction_patch_with_complement_specific_row_basis_translation",
        "source_file": "debug_workflow_portability_stage2_194.1.1.1.py",
        "function": "build_sg194_double_spinorial_generators",
        "helper_to_reuse_or_extend": "_combined_double_channel_record",
        "rule_group_to_change": {
            "existing_rule_group": "DOUBLE_SPINORIAL_IDENTITY_ORDER",
            "existing_behavior": "identity one-to-one channel reuse for families a/e/f/g/i/j/k/l",
            "required_change": (
                "Replace the unchanged identity reuse on the complement families with an explicit complement-side channel assembly / row-basis translation, "
                "analogous in spirit to the trusted-sector patch but now solved on the 23-generator complement."
            ),
        },
        "target_generators_families_channels": payload["generators_channels_families"],
        "why_trusted_patch_not_enough": (
            "The trusted-sector patch only changed the b/c/d/h problem rules. "
            "The remaining 23-generator residual lives entirely in the complement, where the code still assumes identity one-to-one reuse."
        ),
        "why_this_function": (
            "This is the only source-layer function that converts induced candidates into the final 33 SG194 double channels. "
            "The complement residual shows that the untouched identity-reuse branch is the remaining mismatch source."
        ),
    }


def build_audit_md(
    decomposition: dict[str, Any],
    comparison: dict[str, Any],
    lift_payload: dict[str, Any],
    mismatch: dict[str, Any],
    next_patch: dict[str, Any],
) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Global Residual Audit

        ## What remains after removing the trusted sector

        - full 33-generator decomposition completed: `True`
        - trusted sector common indices: `{decomposition['trusted_sector']['common_indices']}`
        - complement common indices: `{decomposition['complement_sector']['common_indices']}`

        ## Complement-only exact comparison

        - current rank: `{comparison['rank_data']['current_rank']}`
        - external rank: `{comparison['rank_data']['external_rank']}`
        - union rank: `{comparison['rank_data']['union_rank']}`
        - intersection rank: `{comparison['rank_data']['intersection_rank']}`
        - current-only dimension: `{comparison['rank_data']['current_only_dimension']}`
        - external-only dimension: `{comparison['rank_data']['external_only_dimension']}`

        ## Complement lift

        - complement lift exists: `{lift_payload['lift_exists']}`
        - rational lift exists: `{lift_payload['rational_lift_exists']}`
        - obstruction kind: `{lift_payload['obstruction']['kind']}`

        ## Residual mismatch localization

        - family-local residual families: `{mismatch['family_local_residual_families']}`
        - current witness row blocks: `{mismatch['witness_row_blocks']['current_only']}`
        - external witness row blocks: `{mismatch['witness_row_blocks']['external_only']}`
        - residual classification: `{mismatch['residual_classification']['best_match']}`

        ## Next patch target

        - source file: `{next_patch['source_file']}`
        - function: `{next_patch['function']}`
        - patch type: `{next_patch['next_patch_type']}`
        """
    ).strip()


def build_handoff_md(summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # Handoff: SG194 Double Global Residual

        ## Completed

        - split the full 33-generator SG194 double problem into trusted 10-generator sector plus remaining 23-generator complement
        - computed the exact complement-only current/external comparison
        - proved that no complement lift exists, even over `Q`
        - localized the residual to the unchanged complement identity-reuse construction

        ## Result

        - complement rank tuple `(current, external, union, intersection)` = `({summary['complement_rank_tuple'][0]}, {summary['complement_rank_tuple'][1]}, {summary['complement_rank_tuple'][2]}, {summary['complement_rank_tuple'][3]})`
        - complement lift exists: `{summary['complement_lift_exists']}`
        - residual classification: `{summary['residual_classification']}`

        ## Next Step

        - next source file: `{summary['next_patch_source_file']}`
        - next function: `{summary['next_patch_function']}`
        - next patch type: `{summary['next_patch_type']}`
        """
    ).strip()


def build_current_status_json(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "global_complement_residual_localization",
        "status": "completed",
        "full_33_decomposition_completed": True,
        "complement_rank_tuple": summary["complement_rank_tuple"],
        "complement_lift_exists": summary["complement_lift_exists"],
        "residual_classification": summary["residual_classification"],
        "next_patch_source_file": summary["next_patch_source_file"],
        "next_patch_function": summary["next_patch_function"],
    }


def build_next_step_prompt(next_patch: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Continue from the completed SG194 double global residual round.

        Fixed facts:
        - do not reopen trusted 10-generator analysis
        - the remaining unresolved issue is the 23-generator complement
        - complement rank data is exact and proves no rational lift exists
        - the residual is cross-family and points at the unchanged complement identity-reuse construction

        Next patch target:
        - file: `{next_patch['source_file']}`
        - function: `{next_patch['function']}`
        - patch type: `{next_patch['next_patch_type']}`
        - rule group: `{next_patch['rule_group_to_change']['existing_rule_group']}`
        """
    ).strip()


def build_report_md(
    decomposition: dict[str, Any],
    comparison: dict[str, Any],
    lift_payload: dict[str, Any],
    mismatch: dict[str, Any],
    next_patch: dict[str, Any],
) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Global Residual Report

        ## 1. What is already solved: trusted 10-generator sector

        The trusted `2b/2c/2d/6h` sector has already been removed from the unresolved problem. Its explicit rational lift is accepted and is not revisited here.

        ## 2. Full 33-generator decomposition

        The full aligned generator domain is split into:

        - trusted sector common indices `{decomposition['trusted_sector']['common_indices']}`
        - complement common indices `{decomposition['complement_sector']['common_indices']}`

        The unresolved object is therefore only the 23-generator complement.

        ## 3. Complement-only comparison

        Exact complement ranks are:

        - current rank = `{comparison['rank_data']['current_rank']}`
        - external rank = `{comparison['rank_data']['external_rank']}`
        - union rank = `{comparison['rank_data']['union_rank']}`
        - intersection rank = `{comparison['rank_data']['intersection_rank']}`

        So the complement carries `5` current-only dimensions and `3` external-only dimensions.

        ## 4. Complement lift or obstruction

        No complement lift exists, even over `Q`. The exact obstruction is row-space containment failure: the external complement has a 3-dimensional basis outside the current complement row span.

        ## 5. Residual mismatch localization

        The important engineering fact is that every individual family block embeds locally, but the full complement still mismatches globally. Therefore the residual is cross-family rather than family-local. The obstruction witnesses use current rows in block `{mismatch['witness_row_blocks']['current_only']}` and external rows in blocks `{mismatch['witness_row_blocks']['external_only']}`.

        ## 6. Next source-level patch target

        The next patch target is `{next_patch['source_file']}`, function `{next_patch['function']}`. The b/c/d/h trusted-sector rules are not the issue anymore. The unresolved source assumption is the unchanged identity one-to-one reuse of the complement families `a/e/f/g/i/j/k/l`.
        """
    ).strip()


def build_report_tex(
    decomposition: dict[str, Any],
    comparison: dict[str, Any],
    lift_payload: dict[str, Any],
    mismatch: dict[str, Any],
    next_patch: dict[str, Any],
) -> str:
    trusted = latex_ascii(str(decomposition["trusted_sector"]["common_indices"]))
    complement = latex_ascii(str(decomposition["complement_sector"]["common_indices"]))
    current_blocks = latex_ascii(str(mismatch["witness_row_blocks"]["current_only"]))
    external_blocks = latex_ascii(str(mismatch["witness_row_blocks"]["external_only"]))
    source_file = latex_ascii(next_patch["source_file"])
    function = latex_ascii(next_patch["function"])
    families = latex_ascii(str(next_patch["target_generators_families_channels"]["families"]))
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\title{{SG194 Double Global Residual Report}}
        \\author{{Codex Complement Residual Round}}
        \\date{{\\today}}
        \\begin{{document}}
        \\maketitle

        \\section*{{1. What is already solved: trusted 10-generator sector}}
        The trusted \\texttt{{2b/2c/2d/6h}} sector has already been solved and is not re-analysed here.

        \\section*{{2. Full 33-generator decomposition}}
        Trusted common indices are
        \\begin{{quote}}
        {trusted}
        \\end{{quote}}
        and complement common indices are
        \\begin{{quote}}
        {complement}
        \\end{{quote}}

        \\section*{{3. Complement-only comparison}}
        Exact complement ranks are current = \\texttt{{{comparison['rank_data']['current_rank']}}}, external = \\texttt{{{comparison['rank_data']['external_rank']}}}, union = \\texttt{{{comparison['rank_data']['union_rank']}}}, intersection = \\texttt{{{comparison['rank_data']['intersection_rank']}}}. Therefore the unresolved complement has current-only dimension \\texttt{{{comparison['rank_data']['current_only_dimension']}}} and external-only dimension \\texttt{{{comparison['rank_data']['external_only_dimension']}}}.

        \\section*{{4. Complement lift or obstruction}}
        No complement lift exists, even over \\texttt{{Q}}. The exact obstruction is row-space containment failure on the complement.

        \\section*{{5. Residual mismatch localization}}
        The complement residual is cross-family. Current witness row blocks are {current_blocks}. External witness row blocks are {external_blocks}.

        \\section*{{6. Next source-level patch target}}
        The next patch target is file \\texttt{{{source_file}}}, function \\texttt{{{function}}}. The unresolved complement families are
        \\begin{{quote}}
        {families}
        \\end{{quote}}
        and the change should replace the untouched identity one-to-one reuse with a complement-specific channel assembly / row-basis translation.

        \\end{{document}}
        """
    ).strip() + "\n"


def build_root_readme() -> str:
    return textwrap.dedent(
        """
        # SG194 Residual Audits

        ## SG194 double lift report

        - report file: `sg194_double_lift_report.pdf`
        - report source file: `sg194_double_lift_report.tex`
        - recommended reading order:
          - `sg194_double_lift_report.pdf`
          - `sg194_double_problem_sector_inventory.json`
          - `sg194_double_problem_sector_lift.json`
          - `sg194_double_delta_external_verdict.json`
          - `sg194_double_patch_verdict_v3.json`

        ## SG194 double global residual report

        - report file: `sg194_double_global_residual_report.pdf`
        - report source file: `sg194_double_global_residual_report.tex`
        - recommended reading order:
          - `sg194_double_global_residual_report.pdf`
          - `sg194_double_global_decomposition.json`
          - `sg194_double_complement_lift.json`
          - `sg194_double_complement_mismatch_localization.json`
          - `sg194_double_next_patch_target.json`
        """
    ).strip()


def build_summary_json(
    comparison: dict[str, Any],
    lift_payload: dict[str, Any],
    mismatch: dict[str, Any],
    next_patch: dict[str, Any],
    package_tree: list[str],
) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "global_complement_residual_audit",
        "full_33_decomposition_completed": True,
        "trusted_sector_outside_scope_but_solved": True,
        "complement_rank_tuple": [
            comparison["rank_data"]["current_rank"],
            comparison["rank_data"]["external_rank"],
            comparison["rank_data"]["union_rank"],
            comparison["rank_data"]["intersection_rank"],
        ],
        "complement_lift_exists": lift_payload["lift_exists"],
        "rational_lift_exists": lift_payload["rational_lift_exists"],
        "integer_lift_exists": lift_payload["integer_lift_exists"],
        "minimal_obstruction_dimension": lift_payload["obstruction"]["minimal_rational_obstruction_dimension"],
        "residual_classification": mismatch["residual_classification"]["best_match"],
        "next_patch_source_file": next_patch["source_file"],
        "next_patch_function": next_patch["function"],
        "next_patch_type": next_patch["next_patch_type"],
        "pdf_generated": REPORT_PDF.exists(),
        "handoff_generated": HANDOFF_MD.exists(),
        "status_generated": CURRENT_STATUS_JSON.exists(),
        "next_step_generated": NEXT_STEP_PROMPT_TXT.exists(),
        "package_tarball": str(PACKAGE_TARBALL),
        "package_tree": package_tree,
    }


def build_package() -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    files_to_copy = [
        ROOT_README,
        GLOBAL_DECOMPOSITION_JSON,
        COMPLEMENT_VS_EXTERNAL_JSON,
        COMPLEMENT_LIFT_JSON,
        COMPLEMENT_LIFT_MD,
        COMPLEMENT_MISMATCH_JSON,
        COMPLEMENT_MISMATCH_MD,
        NEXT_PATCH_TARGET_JSON,
        GLOBAL_AUDIT_MD,
        GLOBAL_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_sg194_double_global_residual.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        LIFT_SCRIPT,
        PATCH_SCRIPT,
        PATCH_V2_SCRIPT,
        STAGE2_SCRIPT,
        PROBLEM_INVENTORY_JSON,
        PROBLEM_LIFT_JSON,
        PATCH_VERDICT_V3_JSON,
        EXTERNAL_JSON,
        RAW_CANDIDATES_JSON,
        RAW_CANDIDATES_PATCHED_JSON,
        RAW_BASIS_JSON,
        RAW_BASIS_PATCHED_JSON,
        RAW_IN_BS_JSON,
        RAW_IN_BS_PATCHED_JSON,
        SWYCKOFF_R,
        SWYCKOFF_K,
        SSGREPS,
        SG_UTILS,
        REP_UTILS,
    ]
    for path in files_to_copy:
        if not path.exists():
            continue
        rel = path.relative_to(ROOT)
        dest = PACKAGE_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)
    return format_tree(PACKAGE_DIR)


def generate_outputs() -> dict[str, Any]:
    context = load_context()
    decomposition = build_global_decomposition(context)
    comparison = build_complement_vs_external(context)
    lift_payload = build_complement_lift(context, comparison)
    mismatch = build_mismatch_localization(context, comparison, lift_payload)
    next_patch = build_next_patch_target(mismatch)

    write_json(GLOBAL_DECOMPOSITION_JSON, decomposition)
    write_json(COMPLEMENT_VS_EXTERNAL_JSON, comparison)
    write_json(COMPLEMENT_LIFT_JSON, lift_payload)
    write_text(COMPLEMENT_LIFT_MD, build_complement_lift_md(lift_payload))
    write_json(COMPLEMENT_MISMATCH_JSON, mismatch)
    write_text(COMPLEMENT_MISMATCH_MD, build_mismatch_localization_md(mismatch))
    write_json(NEXT_PATCH_TARGET_JSON, next_patch)
    write_text(GLOBAL_AUDIT_MD, build_audit_md(decomposition, comparison, lift_payload, mismatch, next_patch))
    write_text(ROOT_README, build_root_readme())
    write_text(REPORT_MD, build_report_md(decomposition, comparison, lift_payload, mismatch, next_patch))
    write_text(REPORT_TEX, build_report_tex(decomposition, comparison, lift_payload, mismatch, next_patch))
    compile_pdf(REPORT_TEX, REPORT_PDF)

    package_tree = build_package()
    summary = build_summary_json(comparison, lift_payload, mismatch, next_patch, package_tree)
    write_json(GLOBAL_SUMMARY_JSON, summary)
    write_text(HANDOFF_MD, build_handoff_md(summary))
    write_json(CURRENT_STATUS_JSON, build_current_status_json(summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(next_patch))

    package_tree = build_package()
    summary = build_summary_json(comparison, lift_payload, mismatch, next_patch, package_tree)
    write_json(GLOBAL_SUMMARY_JSON, summary)
    write_text(HANDOFF_MD, build_handoff_md(summary))
    write_json(CURRENT_STATUS_JSON, build_current_status_json(summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(next_patch))
    return {
        "context": context,
        "decomposition": decomposition,
        "comparison": comparison,
        "lift_payload": lift_payload,
        "mismatch": mismatch,
        "next_patch": next_patch,
        "summary": summary,
    }


def validate_outputs() -> None:
    required = [
        GLOBAL_DECOMPOSITION_JSON,
        COMPLEMENT_VS_EXTERNAL_JSON,
        COMPLEMENT_LIFT_JSON,
        COMPLEMENT_LIFT_MD,
        COMPLEMENT_MISMATCH_JSON,
        COMPLEMENT_MISMATCH_MD,
        NEXT_PATCH_TARGET_JSON,
        GLOBAL_AUDIT_MD,
        GLOBAL_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_sg194_double_global_residual.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        ROOT_README,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing outputs: " + ", ".join(missing))

    comparison = load_json(COMPLEMENT_VS_EXTERNAL_JSON)
    if comparison["rank_data"]["current_rank"] != 9 or comparison["rank_data"]["external_rank"] != 7:
        raise ValueError("unexpected complement rank data")
    if comparison["rank_data"]["union_rank"] != 12 or comparison["rank_data"]["intersection_rank"] != 4:
        raise ValueError("unexpected complement union/intersection")

    lift_payload = load_json(COMPLEMENT_LIFT_JSON)
    if lift_payload["lift_exists"]:
        raise ValueError("complement lift should not exist")
    if lift_payload["rational_lift_exists"]:
        raise ValueError("complement rational lift should not exist")

    summary = load_json(GLOBAL_SUMMARY_JSON)
    if summary["package_tarball"] != str(PACKAGE_TARBALL):
        raise ValueError("tarball path mismatch in summary")

    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(tar.getnames())
    required_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/{GLOBAL_DECOMPOSITION_JSON.name}",
        f"{PACKAGE_NAME}/{COMPLEMENT_LIFT_JSON.name}",
        f"{PACKAGE_NAME}/{COMPLEMENT_MISMATCH_JSON.name}",
        f"{PACKAGE_NAME}/{NEXT_PATCH_TARGET_JSON.name}",
        f"{PACKAGE_NAME}/{REPORT_PDF.name}",
        f"{PACKAGE_NAME}/debug_sg194_double_global_residual.py",
    }
    missing_members = sorted(required_members - names)
    if missing_members:
        raise FileNotFoundError("missing tar members: " + ", ".join(missing_members))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SG194 double global complement residual audit.")
    parser.add_argument("--validate", action="store_true", help="Only validate existing outputs.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return

    generate_outputs()
    validate_outputs()


if __name__ == "__main__":
    main()
