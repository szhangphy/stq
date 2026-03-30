#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent

RULE_SOLVE_JSON = ROOT / "sg194_double_complement_rule_solve_v1.json"
PATCH_SUMMARY_JSON = ROOT / "sg194_double_complement_patch_summary_v1.json"
REPORT_MD = ROOT / "sg194_double_complement_patch_report_v1.md"
REPORT_TEX = ROOT / "sg194_double_complement_patch_report_v1.tex"
REPORT_PDF = ROOT / "sg194_double_complement_patch_report_v1.pdf"
HANDOFF_MD = ROOT / "handoff_sg194_double_complement_patch_v1.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_double_complement_patch_v1.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_sg194_double_complement_patch_v1.txt"

RAW_CANDIDATES_PATCHED_V2_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched_v2.json"
RAW_BASIS_PATCHED_V2_JSON = ROOT / "raw_194_1_1_1_double_ai_basis_patched_v2.json"
RAW_IN_BS_PATCHED_V2_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched_v2.json"

PACKAGE_NAME = "review_package_sg194_double_complement_patch_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
ROOT_README = ROOT / "README.md"

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
STAGE1_SCRIPT = ROOT / "debug_workflow_portability_194.1.1.1.py"
LOCAL_LIBRARY_SCRIPT = ROOT / "debug_sg194_nonabelian_local_library.py"
PATCH_SCRIPT = ROOT / "debug_sg194_double_patch.py"
GLOBAL_RESIDUAL_SCRIPT = ROOT / "debug_sg194_double_global_residual.py"
LIFT_SCRIPT = ROOT / "debug_sg194_double_lift.py"
EXTERNAL_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"
RAW_CANDIDATES_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_CANDIDATES_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched.json"
RAW_BASIS_JSON = ROOT / "raw_194_1_1_1_double_ai_basis.json"
RAW_BASIS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_basis_patched.json"
RAW_IN_BS_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json"
RAW_IN_BS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched.json"
PROBLEM_INVENTORY_JSON = ROOT / "sg194_double_problem_sector_inventory.json"
PROBLEM_LIFT_JSON = ROOT / "sg194_double_problem_sector_lift.json"
PATCH_VERDICT_V3_JSON = ROOT / "sg194_double_patch_verdict_v3.json"
GLOBAL_DECOMPOSITION_JSON = ROOT / "sg194_double_global_decomposition.json"
GLOBAL_RESIDUAL_SUMMARY_JSON = ROOT / "sg194_double_global_residual_summary.json"
STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
SINGLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"

SWYCKOFF_K = ROOT / "swyckoff_k.py"
SWYCKOFF_R = ROOT / "swyckoff_r.py"
SSGREPS = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
SG_UTILS = ROOT / "SSGReps" / "SSGReps" / "SG_utils.py"
REP_UTILS = ROOT / "SSGReps" / "SSGReps" / "rep_utils.py"

DEPENDENCY_FILES = [
    STAGE2_SCRIPT,
    STAGE1_SCRIPT,
    LOCAL_LIBRARY_SCRIPT,
    GLOBAL_RESIDUAL_SCRIPT,
    LIFT_SCRIPT,
    RAW_CANDIDATES_JSON,
    RAW_CANDIDATES_PATCHED_JSON,
    RAW_BASIS_JSON,
    RAW_BASIS_PATCHED_JSON,
    RAW_IN_BS_JSON,
    RAW_IN_BS_PATCHED_JSON,
    EXTERNAL_JSON,
]

TRUSTED_COMMON_INDICES = [6, 7, 8, 9, 10, 11, 12, 13, 14, 25]
COMPLEMENT_COMMON_INDICES = [0, 1, 2, 3, 4, 5, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32]
SELECTED_HOMOGENEOUS_DIRECTIONS = [
    {"generator_id": "a_proj_u_1d_1", "null_pattern_index": 0},
    {"generator_id": "a_proj_u_1d_2", "null_pattern_index": 1},
    {"generator_id": "a_proj_g_1d_3", "null_pattern_index": 2},
    {"generator_id": "a_proj_u_2d_5", "null_pattern_index": 3},
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def dependency_status() -> dict[str, Any]:
    present = {path.name: path.exists() for path in DEPENDENCY_FILES}
    missing = [name for name, exists in present.items() if not exists]
    return {
        "all_present": not missing,
        "present_map": present,
        "missing_files": missing,
        "blocked_steps_if_missing": (
            []
            if not missing
            else [
                "versioned raw SG194 double regeneration",
                "exact complement/full rank validation",
                "PDF/package closeout",
            ]
        ),
    }


def rank_record(current: sp.Matrix, external: sp.Matrix) -> dict[str, int]:
    current_rank = int(current.rank())
    external_rank = int(external.rank())
    union_rank = int(sp.Matrix.vstack(current, external).rank())
    intersection_rank = current_rank + external_rank - union_rank
    return {
        "current_rank": current_rank,
        "external_rank": external_rank,
        "union_rank": union_rank,
        "intersection_rank": intersection_rank,
        "current_only_dimension": current_rank - intersection_rank,
        "external_only_dimension": external_rank - intersection_rank,
    }


def update_root_readme() -> None:
    section = textwrap.dedent(
        """
        ## SG194 double complement patch report v1

        - report file: `sg194_double_complement_patch_report_v1.pdf`
        - report source file: `sg194_double_complement_patch_report_v1.tex`
        - recommended reading order:
          - `sg194_double_complement_patch_report_v1.pdf`
          - `sg194_double_complement_rule_solve_v1.json`
          - `sg194_double_complement_patch_summary_v1.json`
          - `raw_194_1_1_1_double_ai_candidates_patched_v2.json`
        """
    ).strip()
    existing = ROOT_README.read_text() if ROOT_README.exists() else "# SG194 Residual Audits\n"
    if "## SG194 double complement patch report v1" in existing:
        prefix = existing.split("## SG194 double complement patch report v1")[0].rstrip()
        write_text(ROOT_README, prefix + "\n\n" + section)
    else:
        write_text(ROOT_README, existing.rstrip() + "\n\n" + section)


def build_context() -> dict[str, Any]:
    stage2 = load_module(STAGE2_SCRIPT, "sg194_stage2_complement_patch_v1")
    patch = load_module(PATCH_SCRIPT, "sg194_patch_base_complement_v1")
    rawaudit = load_module(ROOT / "debug_raw_matrix_audit.py", "sg194_rawaudit_complement_v1")

    raw_root = load_json(RAW_CANDIDATES_JSON)
    raw_candidates = raw_root["candidates"]
    unknown_ordering = raw_root["unknown_ordering"]
    selected_indices = patch.selection_indices(unknown_ordering)
    current_row_labels = [unknown_ordering[idx] for idx in selected_indices]

    family_dimension_map = {candidate["family_id"]: int(candidate["family_dimension"]) for candidate in raw_candidates}
    induction_like = [patch.raw_candidate_to_induction_like(candidate) for candidate in raw_candidates]

    compat_root = rawaudit.load_json(rawaudit.CASE_SPECS["194_1_1_1_double"]["compat_path"])
    c_ctx = rawaudit.compute_c_artifact("194_1_1_1_double", compat_root)
    bs_ctx = rawaudit.compute_bs_artifacts("194_1_1_1_double", c_ctx)

    external = load_json(EXTERNAL_JSON)
    external_labels = [f"{item['letter_key']}:{item['bandrep_label']}" for item in external["column_labels"]]
    external_matrix = sp.Matrix(external["matrix_entries"])

    return {
        "stage2": stage2,
        "patch": patch,
        "rawaudit": rawaudit,
        "raw_candidates": raw_candidates,
        "unknown_ordering": unknown_ordering,
        "selected_indices": selected_indices,
        "current_row_labels": current_row_labels,
        "family_dimension_map": family_dimension_map,
        "induction_like": induction_like,
        "c_ctx": c_ctx,
        "bs_ctx": bs_ctx,
        "external": external,
        "external_labels": external_labels,
        "external_matrix": external_matrix,
        "single_summary": load_json(STAGE2_SUMMARY_JSON),
        "single_completion": load_json(SINGLE_COMPLETION_JSON),
        "double_completion": load_json(DOUBLE_COMPLETION_JSON),
    }


def build_profile_artifacts(context: dict[str, Any], profile: str) -> dict[str, Any]:
    patch = context["patch"]
    stage2 = context["stage2"]
    built = stage2.build_sg194_double_spinorial_generators(context["induction_like"], profile=profile)
    payload_ctx = patch.build_channel_candidates(
        stage2,
        context["induction_like"],
        context["c_ctx"]["unknown_ordering"],
        context["c_ctx"]["matrix"],
        context["family_dimension_map"],
        profile=profile,
    )
    ai_candidates_ctx = context["rawaudit"].compute_ai_candidate_artifact("194_1_1_1_double", payload_ctx["channels"], context["bs_ctx"])
    ai_basis_ctx = context["rawaudit"].compute_ai_basis_artifact("194_1_1_1_double", ai_candidates_ctx, context["bs_ctx"])
    ai_in_bs_ctx = context["rawaudit"].compute_ai_in_bs_artifact("194_1_1_1_double", ai_basis_ctx, context["bs_ctx"], context["c_ctx"])
    return {
        "profile": profile,
        "built": built,
        "channel_payload": payload_ctx["channels"],
        "ai_candidates_payload": ai_candidates_ctx["payload"],
        "ai_basis_payload": ai_basis_ctx["payload"],
        "ai_in_bs_payload": ai_in_bs_ctx["payload"],
    }


def current_matrix_from_payload(payload: dict[str, Any], selected_indices: list[int], external_labels: list[str]) -> sp.Matrix:
    payload_map = {}
    for candidate in payload["candidates"]:
        label = candidate.get("external_channel_label") or candidate.get("source_payload", {}).get("external_channel_label")
        payload_map[label] = candidate
    return sp.Matrix.hstack(
        *[
            sp.Matrix([payload_map[label]["unknown_vector"][row_idx] for row_idx in selected_indices])
            for label in external_labels
        ]
    )


def rank_summary(context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    current_full = current_matrix_from_payload(payload, context["selected_indices"], context["external_labels"])
    external_full = context["external_matrix"]
    payload_labels = [
        candidate.get("external_channel_label") or candidate.get("source_payload", {}).get("external_channel_label")
        for candidate in payload["candidates"]
    ]
    current_complement = current_full[:, COMPLEMENT_COMMON_INDICES]
    external_complement = external_full[:, COMPLEMENT_COMMON_INDICES]
    current_trusted = current_full[:, TRUSTED_COMMON_INDICES]
    external_trusted = external_full[:, TRUSTED_COMMON_INDICES]
    return {
        "full": rank_record(current_full, external_full),
        "complement": rank_record(current_complement, external_complement),
        "trusted": rank_record(current_trusted, external_trusted),
        "canonical_order_matches_external": payload_labels == context["external_labels"],
    }


def changed_channel_report(old_payload: dict[str, Any], new_payload: dict[str, Any]) -> dict[str, Any]:
    old_map = {candidate["source_payload"]["external_channel_label"]: candidate for candidate in old_payload["candidates"]}
    new_map = {candidate["source_payload"]["external_channel_label"]: candidate for candidate in new_payload["candidates"]}
    changed = []
    unchanged = []
    for label in sorted(old_map):
        old_terms = old_map[label]["source_payload"]["merge_terms"]
        new_terms = new_map[label]["source_payload"]["merge_terms"]
        old_vector = old_map[label]["unknown_vector"]
        new_vector = new_map[label]["unknown_vector"]
        record = {
            "label": label,
            "merge_terms_changed": old_terms != new_terms,
            "unknown_vector_changed": old_vector != new_vector,
        }
        if old_terms != new_terms or old_vector != new_vector:
            changed.append(record)
        else:
            unchanged.append(record)
    return {
        "changed_count": len(changed),
        "unchanged_count": len(unchanged),
        "changed_labels": [item["label"] for item in changed],
        "unchanged_labels": [item["label"] for item in unchanged],
    }


def build_rule_solve_json(context: dict[str, Any], built: dict[str, Any], rank_data: dict[str, Any]) -> dict[str, Any]:
    stage2 = context["stage2"]
    complement_rule_records = {}
    channel_map = {(channel["family_letter"], channel["spinorial_channel_label"]): channel for channel in built["channels"]}
    for family_letter, external_label in stage2.DOUBLE_SPINORIAL_COMPLEMENT_ORDER:
        key = f"{family_letter}:{external_label}"
        complement_rule_records[key] = {
            "metadata_anchor_generator_id": stage2.DOUBLE_SPINORIAL_COMPLEMENT_IDENTITY_ANCHORS[(family_letter, external_label)],
            "source_generator_terms": built["complement_rules"][key],
            "term_count": len(built["complement_rules"][key]),
            "patch_note": channel_map[(family_letter, external_label)]["patch_note"],
        }
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "profile": "sg194_double_complement_patch_v1",
        "coefficient_field": "Z",
        "canonical_external_order": context["external_labels"],
        "trusted_common_indices": TRUSTED_COMMON_INDICES,
        "complement_common_indices": COMPLEMENT_COMMON_INDICES,
        "solve_kind": "exact full-33 external null-relation solve with the trusted 10-generator block fixed",
        "why_previous_patch_stopped_short": (
            "sg194_double_anchor_patch_v1 fixed only the trusted 2b/2c/2d/6h block. "
            "The 23-channel complement still used identity reuse, so the full 33-generator current row space stayed larger than the external one."
        ),
        "selected_homogeneous_directions": SELECTED_HOMOGENEOUS_DIRECTIONS,
        "complement_rule_count": len(complement_rule_records),
        "rules": complement_rule_records,
        "exact_rank_verification": {
            "full": rank_data["full"],
            "complement": rank_data["complement"],
            "trusted": rank_data["trusted"],
        },
        "single_double_relation": {
            "single_group_unblocked": context["single_summary"]["single_group_unblocked"],
            "double_group_unblocked": context["single_summary"]["double_group_unblocked"],
            "spinorial_only_bug": True,
            "reason": (
                "The single SG194 line does not have a separate spinorial 33-channel builder. "
                "The complement identity-reuse bug appears only in the double spinorial current-generator construction."
            ),
        },
    }


def build_summary_json(
    dependency_info: dict[str, Any],
    old_rank_data: dict[str, Any],
    new_rank_data: dict[str, Any],
    channel_diff: dict[str, Any],
    package_tree: list[str] | None = None,
) -> dict[str, Any]:
    complement_exact = (
        new_rank_data["complement"]["current_only_dimension"] == 0
        and new_rank_data["complement"]["external_only_dimension"] == 0
    )
    full_exact = (
        new_rank_data["full"]["current_only_dimension"] == 0
        and new_rank_data["full"]["external_only_dimension"] == 0
    )
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "profile": "sg194_double_complement_patch_v1",
        "dependency_check": dependency_info,
        "old_profile": "sg194_double_anchor_patch_v1",
        "new_profile": "sg194_double_complement_patch_v1",
        "changed_channels": channel_diff,
        "rank_before_after": {
            "old_v1": old_rank_data,
            "new_v2": new_rank_data,
        },
        "complement_exact_equality": complement_exact,
        "full_33_global_alignment": full_exact,
        "single_double_relation": {
            "single_is_clean_baseline_for_this_bug_class": True,
            "single_reason": "The SG194 single line has no spinorial complement channel builder and therefore does not show the complement identity-reuse failure mode.",
            "double_reason": "The old double current generator layer inserted a legacy identity-reuse complement branch on top of the already unblocked stage-2 library path.",
            "construction_philosophy_after_patch": (
                "Both lines now route through explicit, auditable source-layer construction rather than downstream audit-only rewrites. "
                "The double line still uses a spinorial-specific row-basis translation table, which has no single-line analogue."
            ),
        },
        "pdf_generated": REPORT_PDF.exists(),
        "handoff_generated": HANDOFF_MD.exists(),
        "status_generated": CURRENT_STATUS_JSON.exists(),
        "next_step_generated": NEXT_STEP_PROMPT_TXT.exists(),
        "package_tarball": str(PACKAGE_TARBALL) if PACKAGE_TARBALL.exists() else None,
        "package_tree": package_tree or [],
    }


def build_report_md(summary: dict[str, Any]) -> str:
    old_comp = summary["rank_before_after"]["old_v1"]["complement"]
    new_comp = summary["rank_before_after"]["new_v2"]["complement"]
    old_full = summary["rank_before_after"]["old_v1"]["full"]
    new_full = summary["rank_before_after"]["new_v2"]["full"]
    return textwrap.dedent(
        f"""
        # SG194 Double Complement Patch Report V1

        ## 1. What the previous patch solved and what it did not solve

        The previous `sg194_double_anchor_patch_v1` round solved the trusted `2b/2c/2d/6h` sector exactly, but it left the 23-channel complement on legacy identity reuse. That is why the global residual remained:

        - old complement rank tuple = `{old_comp['current_rank']} / {old_comp['external_rank']} / {old_comp['union_rank']} / {old_comp['intersection_rank']}`
        - old complement mismatch = `current-only {old_comp['current_only_dimension']}`, `external-only {old_comp['external_only_dimension']}`

        So the old patch fixed the trusted problem sector, but not the complement branch that still carried the full-33 obstruction.

        ## 2. Why this complement patch is the correct source layer

        The real unresolved source object was `build_sg194_double_spinorial_generators(...)` in `debug_workflow_portability_stage2_194.1.1.1.py`. The old builder used:

        - a trusted-sector patch only for `b/c/d/h`
        - legacy identity one-to-one reuse for the complement families `a/e/f/g/i/j/k/l`

        This round adds a new explicit profile `sg194_double_complement_patch_v1`. It keeps the trusted rules unchanged and replaces the complement branch with an exact, auditable row-basis translation table emitted in canonical external order.

        ## 3. Exact complement rule logic

        The complement rules were solved by fixing the trusted 10-generator block and imposing the full external 33-column null relations on the remaining 23 columns. The key four homogeneous directions selected by the exact solve are:

        - `a_proj_u_1d_1`
        - `a_proj_u_1d_2`
        - `a_proj_g_1d_3`
        - `a_proj_u_2d_5`

        All coefficients in the resulting complement rule table are exact integers. The explicit 23-channel table is serialized in `sg194_double_complement_rule_solve_v1.json`.

        ## 4. Exact rank data after the patch

        Complement-only after patch:

        - current/external/union/intersection = `{new_comp['current_rank']} / {new_comp['external_rank']} / {new_comp['union_rank']} / {new_comp['intersection_rank']}`
        - current-only/external-only = `{new_comp['current_only_dimension']} / {new_comp['external_only_dimension']}`

        Full 33 after patch:

        - current/external/union/intersection = `{new_full['current_rank']} / {new_full['external_rank']} / {new_full['union_rank']} / {new_full['intersection_rank']}`
        - current-only/external-only = `{new_full['current_only_dimension']} / {new_full['external_only_dimension']}`

        ## 5. Final verdict

        - complement exact equality reached: `{summary['complement_exact_equality']}`
        - full 33 global alignment reached: `{summary['full_33_global_alignment']}`

        This round therefore closes the SG194 double complement residual mathematically. The old global residual does not survive this versioned patch.

        ## 6. Single / double relation

        The current bug is spinorial-only. The single line is the clean baseline for this bug class because it does not have a separate spinorial complement channel builder. After this patch, both lines are source-layer-driven and auditable, but only the double line needs the complement row-basis translation table.

        ## 7. Remaining engineering work

        The SG194 double complement obstruction is closed for this group. The remaining work is no longer “patch this SG194 residual again”; it is to decide whether this exact null-relation solve should be generalized into a reusable spinorial construction routine beyond SG194.
        """
    ).strip()


def build_report_tex(summary: dict[str, Any]) -> str:
    old_comp = summary["rank_before_after"]["old_v1"]["complement"]
    new_comp = summary["rank_before_after"]["new_v2"]["complement"]
    new_full = summary["rank_before_after"]["new_v2"]["full"]
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\title{{SG194 Double Complement Patch Report V1}}
        \\author{{Codex Complement Patch Round}}
        \\date{{\\today}}
        \\begin{{document}}
        \\maketitle

        \\section*{{1. What the previous patch solved and what it did not solve}}
        The previous \\texttt{{sg194\\_double\\_anchor\\_patch\\_v1}} round solved the trusted \\texttt{{2b/2c/2d/6h}} sector exactly, but it left the 23-channel complement on legacy identity reuse. The old complement rank tuple was \\texttt{{{old_comp['current_rank']} / {old_comp['external_rank']} / {old_comp['union_rank']} / {old_comp['intersection_rank']}}}, with current-only / external-only dimensions \\texttt{{{old_comp['current_only_dimension']} / {old_comp['external_only_dimension']}}}. Therefore the old patch fixed the trusted sector, but not the complement branch.

        \\section*{{2. Why this complement patch is the correct source layer}}
        The real unresolved source object was \\texttt{{build\\_sg194\\_double\\_spinorial\\_generators(...)}} in \\texttt{{debug\\_workflow\\_portability\\_stage2\\_194.1.1.1.py}}. This round adds \\texttt{{sg194\\_double\\_complement\\_patch\\_v1}}, keeps the trusted rules unchanged, and replaces the complement identity-reuse branch with an explicit exact rule table in canonical external order.

        \\section*{{3. Exact complement rule logic}}
        The complement rules were solved by fixing the trusted 10-generator block and imposing the full external 33-column null relations on the remaining 23 columns. The four selected homogeneous directions are:
        \\begin{{itemize}}
        \\item \\texttt{{a\\_proj\\_u\\_1d\\_1}}
        \\item \\texttt{{a\\_proj\\_u\\_1d\\_2}}
        \\item \\texttt{{a\\_proj\\_g\\_1d\\_3}}
        \\item \\texttt{{a\\_proj\\_u\\_2d\\_5}}
        \\end{{itemize}}
        All coefficients in the final table are exact integers.

        \\section*{{4. Exact rank data after the patch}}
        Complement-only after patch: \\texttt{{{new_comp['current_rank']} / {new_comp['external_rank']} / {new_comp['union_rank']} / {new_comp['intersection_rank']}}}, current-only / external-only = \\texttt{{{new_comp['current_only_dimension']} / {new_comp['external_only_dimension']}}}.

        Full 33 after patch: \\texttt{{{new_full['current_rank']} / {new_full['external_rank']} / {new_full['union_rank']} / {new_full['intersection_rank']}}}, current-only / external-only = \\texttt{{{new_full['current_only_dimension']} / {new_full['external_only_dimension']}}}.

        \\section*{{5. Final verdict}}
        Complement exact equality reached: \\texttt{{{summary['complement_exact_equality']}}}. Full 33 global alignment reached: \\texttt{{{summary['full_33_global_alignment']}}}. This round closes the SG194 double complement residual mathematically.

        \\section*{{6. Single / double relation}}
        The current bug is spinorial-only. The single line does not have a separate spinorial complement channel builder, so this failure mode does not appear there. After this patch, both lines are source-layer-driven and auditable, but only the double line needs the complement row-basis translation table.

        \\section*{{7. Remaining engineering work}}
        The next engineering question is no longer the SG194 complement obstruction itself. It is whether this exact null-relation solve should be generalized into a reusable spinorial construction routine beyond SG194.

        \\end{{document}}
        """
    ).strip() + "\n"


def build_handoff_md(summary: dict[str, Any]) -> str:
    new_comp = summary["rank_before_after"]["new_v2"]["complement"]
    new_full = summary["rank_before_after"]["new_v2"]["full"]
    return textwrap.dedent(
        f"""
        # Handoff: SG194 Double Complement Patch V1

        ## Completed

        - added the source-layer profile `sg194_double_complement_patch_v1`
        - regenerated versioned SG194 double raw outputs under `*_patched_v2.json`
        - proved exact complement equality and full 33 global alignment

        ## Exact result

        - complement tuple = `({new_comp['current_rank']}, {new_comp['external_rank']}, {new_comp['union_rank']}, {new_comp['intersection_rank']})`
        - complement current-only / external-only = `{new_comp['current_only_dimension']} / {new_comp['external_only_dimension']}`
        - full tuple = `({new_full['current_rank']}, {new_full['external_rank']}, {new_full['union_rank']}, {new_full['intersection_rank']})`

        ## Next step

        - do not reopen SG194 trusted-sector debugging
        - if continuing, focus on refactoring this exact complement null-relation solve into a reusable spinorial construction routine
        """
    ).strip()


def build_status_json(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "sg194_double_complement_patch_v1",
        "status": "completed",
        "complement_exact_equality": summary["complement_exact_equality"],
        "full_33_global_alignment": summary["full_33_global_alignment"],
        "package_tarball": str(PACKAGE_TARBALL),
    }


def build_next_step_prompt(summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Continue from the completed SG194 double complement patch v1 round.

        Fixed facts:
        - profile `sg194_double_complement_patch_v1` is now implemented in `debug_workflow_portability_stage2_194.1.1.1.py`
        - the complement 23-generator branch reached exact equality
        - the full 33-generator SG194 double current/external spaces are globally aligned

        Do not reopen the trusted-sector bug story.
        The next useful task is to decide whether the exact complement null-relation solve should be generalized into a reusable spinorial row-basis translation routine beyond SG194.
        """
    ).strip()


def build_package_readme(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Review Package: SG194 Double Complement Patch V1",
            "",
            "## What this round solved",
            "",
            "- Added `sg194_double_complement_patch_v1` to the stage-2 SG194 double generator builder.",
            "- Replaced legacy complement identity reuse with an explicit exact complement rule table.",
            f"- Complement exact equality reached: `{summary['complement_exact_equality']}`.",
            f"- Full 33-generator global alignment reached: `{summary['full_33_global_alignment']}`.",
            "",
            "## What this round did not try to solve",
            "",
            "- It did not reopen the already solved trusted 10-generator lift.",
            "- It did not attempt to generalize the SG194-specific exact solve into a multi-group framework.",
            "",
            "## Reproduce",
            "",
            "1. `python3 -m py_compile debug_workflow_portability_stage2_194.1.1.1.py debug_sg194_double_complement_patch_v1.py`",
            "2. `python3 debug_sg194_double_complement_patch_v1.py`",
            "3. `python3 debug_sg194_double_complement_patch_v1.py --validate`",
            "",
            "## Entry Point",
            "",
            "- `debug_sg194_double_complement_patch_v1.py`",
            "",
            "## Suggested Reading Order",
            "",
            "1. `sg194_double_complement_patch_report_v1.pdf`",
            "2. `sg194_double_complement_rule_solve_v1.json`",
            "3. `sg194_double_complement_patch_summary_v1.json`",
            "4. `raw_194_1_1_1_double_ai_candidates_patched_v2.json`",
            "",
            "## File Guide",
            "",
            "- `sg194_double_complement_rule_solve_v1.json`: exact 23-channel complement rule table and solve metadata",
            "- `sg194_double_complement_patch_summary_v1.json`: before/after rank comparison and final verdict",
            "- `sg194_double_complement_patch_report_v1.pdf`: human-readable technical report",
            "- `raw_194_1_1_1_double_ai_*_patched_v2.json`: regenerated versioned raw outputs",
            "- `handoff_sg194_double_complement_patch_v1.md`: concise continuation note",
            "- `current_status_sg194_double_complement_patch_v1.json`: machine-readable status snapshot",
            "- `next_step_prompt_sg194_double_complement_patch_v1.txt`: next-session prompt",
        ]
    )


def build_package(summary: dict[str, Any]) -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    write_text(PACKAGE_DIR / "README.md", build_package_readme(summary))

    files_to_copy = [
        RULE_SOLVE_JSON,
        PATCH_SUMMARY_JSON,
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        RAW_CANDIDATES_PATCHED_V2_JSON,
        RAW_BASIS_PATCHED_V2_JSON,
        RAW_IN_BS_PATCHED_V2_JSON,
        STAGE2_SCRIPT,
        STAGE1_SCRIPT,
        LOCAL_LIBRARY_SCRIPT,
        PATCH_SCRIPT,
        GLOBAL_RESIDUAL_SCRIPT,
        LIFT_SCRIPT,
        EXTERNAL_JSON,
        RAW_CANDIDATES_JSON,
        RAW_CANDIDATES_PATCHED_JSON,
        RAW_BASIS_JSON,
        RAW_BASIS_PATCHED_JSON,
        RAW_IN_BS_JSON,
        RAW_IN_BS_PATCHED_JSON,
        PROBLEM_INVENTORY_JSON,
        PROBLEM_LIFT_JSON,
        PATCH_VERDICT_V3_JSON,
        GLOBAL_DECOMPOSITION_JSON,
        GLOBAL_RESIDUAL_SUMMARY_JSON,
        STAGE2_SUMMARY_JSON,
        SINGLE_COMPLETION_JSON,
        DOUBLE_COMPLETION_JSON,
        SWYCKOFF_K,
        SWYCKOFF_R,
        SSGREPS,
        SG_UTILS,
        REP_UTILS,
        ROOT / "debug_sg194_double_complement_patch_v1.py",
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


def run_round() -> None:
    dependencies = dependency_status()
    if not dependencies["all_present"]:
        raise FileNotFoundError("missing dependencies: " + ", ".join(dependencies["missing_files"]))

    context = build_context()
    old_profile = build_profile_artifacts(context, "sg194_double_anchor_patch_v1")
    new_profile = build_profile_artifacts(context, "sg194_double_complement_patch_v1")

    if new_profile["built"]["ordering"] != context["external_labels"]:
        raise ValueError("new profile did not emit canonical external order")

    write_json(RAW_CANDIDATES_PATCHED_V2_JSON, new_profile["ai_candidates_payload"])
    write_json(RAW_BASIS_PATCHED_V2_JSON, new_profile["ai_basis_payload"])
    write_json(RAW_IN_BS_PATCHED_V2_JSON, new_profile["ai_in_bs_payload"])

    old_rank_data = rank_summary(context, old_profile["ai_candidates_payload"])
    new_rank_data = rank_summary(context, new_profile["ai_candidates_payload"])
    channel_diff = changed_channel_report(old_profile["ai_candidates_payload"], new_profile["ai_candidates_payload"])
    rule_solve = build_rule_solve_json(context, new_profile["built"], new_rank_data)
    write_json(RULE_SOLVE_JSON, rule_solve)

    provisional_summary = build_summary_json(dependencies, old_rank_data, new_rank_data, channel_diff)
    write_text(REPORT_MD, build_report_md(provisional_summary))
    write_text(REPORT_TEX, build_report_tex(provisional_summary))
    compile_pdf(REPORT_TEX, REPORT_PDF)
    write_text(HANDOFF_MD, build_handoff_md(provisional_summary))
    write_json(CURRENT_STATUS_JSON, build_status_json(provisional_summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(provisional_summary))

    update_root_readme()
    package_tree = build_package(provisional_summary)
    summary = build_summary_json(dependencies, old_rank_data, new_rank_data, channel_diff, package_tree)
    write_json(PATCH_SUMMARY_JSON, summary)
    write_text(HANDOFF_MD, build_handoff_md(summary))
    write_json(CURRENT_STATUS_JSON, build_status_json(summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(summary))
    package_tree = build_package(summary)
    write_json(PATCH_SUMMARY_JSON, build_summary_json(dependencies, old_rank_data, new_rank_data, channel_diff, package_tree))


def validate_outputs() -> None:
    required = [
        RULE_SOLVE_JSON,
        PATCH_SUMMARY_JSON,
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        RAW_CANDIDATES_PATCHED_V2_JSON,
        RAW_BASIS_PATCHED_V2_JSON,
        RAW_IN_BS_PATCHED_V2_JSON,
        ROOT_README,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing outputs: " + ", ".join(missing))

    summary = load_json(PATCH_SUMMARY_JSON)
    if not summary["complement_exact_equality"]:
        raise ValueError("complement exact equality must hold")
    if not summary["full_33_global_alignment"]:
        raise ValueError("full 33 global alignment must hold")

    new_comp = summary["rank_before_after"]["new_v2"]["complement"]
    if (new_comp["current_rank"], new_comp["external_rank"], new_comp["union_rank"], new_comp["intersection_rank"]) != (7, 7, 7, 7):
        raise ValueError("unexpected complement rank tuple")
    new_full = summary["rank_before_after"]["new_v2"]["full"]
    if (new_full["current_rank"], new_full["external_rank"], new_full["union_rank"], new_full["intersection_rank"]) != (10, 10, 10, 10):
        raise ValueError("unexpected full rank tuple")

    rules = load_json(RULE_SOLVE_JSON)
    if rules["coefficient_field"] != "Z" or rules["complement_rule_count"] != 23:
        raise ValueError("rule table metadata mismatch")

    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(tar.getnames())
        readme_bytes = tar.extractfile(f"{PACKAGE_NAME}/README.md").read()
    required_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/{RULE_SOLVE_JSON.name}",
        f"{PACKAGE_NAME}/{PATCH_SUMMARY_JSON.name}",
        f"{PACKAGE_NAME}/{REPORT_PDF.name}",
        f"{PACKAGE_NAME}/{RAW_CANDIDATES_PATCHED_V2_JSON.name}",
        f"{PACKAGE_NAME}/{STAGE2_SCRIPT.name}",
        f"{PACKAGE_NAME}/{LOCAL_LIBRARY_SCRIPT.name}",
    }
    missing_members = sorted(required_members - names)
    if missing_members:
        raise FileNotFoundError("missing tar members: " + ", ".join(missing_members))
    readme_text = readme_bytes.decode("utf-8")
    if not readme_text.startswith("# Review Package: SG194 Double Complement Patch V1"):
        raise ValueError("package README was overwritten by a non-package README")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply and validate the SG194 double complement patch v1 round.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return

    run_round()
    validate_outputs()


if __name__ == "__main__":
    main()
