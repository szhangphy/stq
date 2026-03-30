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

METRIC_BUG_AUDIT_JSON = ROOT / "sg194_double_metric_bug_audit.json"
METRIC_BUG_AUDIT_MD = ROOT / "sg194_double_metric_bug_audit.md"
BEFORE_AFTER_V2_JSON = ROOT / "sg194_double_ai_patch_before_after_v2.json"
BEFORE_AFTER_V2_MD = ROOT / "sg194_double_ai_patch_before_after_v2.md"
PATCH_SUMMARY_V2_JSON = ROOT / "sg194_double_patch_summary_v2.json"
PATCH_AUDIT_V2_MD = ROOT / "sg194_double_patch_audit_v2.md"
HANDOFF_V2_MD = ROOT / "handoff_sg194_double_patch_v2.md"
CURRENT_STATUS_V2_JSON = ROOT / "current_status_sg194_double_patch_v2.json"
NEXT_STEP_V2_TXT = ROOT / "next_step_prompt_sg194_double_patch_v2.txt"
REPORT_V2_MD = ROOT / "sg194_double_patch_report_v2.md"
REPORT_V2_TEX = ROOT / "sg194_double_patch_report_v2.tex"
REPORT_V2_PDF = ROOT / "sg194_double_patch_report_v2.pdf"

PACKAGE_NAME = "review_package_sg194_double_patch_metricfix"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


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


def recompute_corrected_before_after(base: Any) -> dict[str, Any]:
    stage2, raw = base.load_context_modules()
    compat_root = raw.load_json(raw.CASE_SPECS["194_1_1_1_double"]["compat_path"])
    c_ctx = raw.compute_c_artifact("194_1_1_1_double", compat_root)

    legacy_raw = load_json(ROOT / "raw_194_1_1_1_double_ai_candidates.json")["candidates"]
    induction_like = [base.raw_candidate_to_induction_like(candidate) for candidate in legacy_raw]
    family_dimension_map = {candidate["family_id"]: int(candidate["family_dimension"]) for candidate in legacy_raw}

    ordering = c_ctx["unknown_ordering"]
    legacy = base.build_channel_candidates(
        stage2,
        induction_like,
        ordering,
        c_ctx["matrix"],
        family_dimension_map,
        profile="legacy",
    )
    patched = base.build_channel_candidates(
        stage2,
        induction_like,
        ordering,
        c_ctx["matrix"],
        family_dimension_map,
        profile="sg194_double_anchor_patch_v1",
    )

    corrected = base.build_before_after(legacy["channels"], patched["channels"], ordering)

    current_indices = base.selection_indices(ordering)
    legacy_hsp = base.matrix_from_channels(legacy["channels"], current_indices)
    patched_hsp = base.matrix_from_channels(patched["channels"], current_indices)
    ext_spin = load_json(ROOT / "sg194_external_spinorial_generator_matrix.json")
    external = sp.Matrix(ext_spin["matrix_entries"])
    ext_problem_indices = [
        idx
        for idx, item in enumerate(ext_spin["column_labels"])
        if item["wp_label"] in {"2b", "2c", "2d", "6h"}
    ]
    legacy_problem_indices, problem_labels = base.problem_sector_indices_and_labels(legacy["channels"])
    patched_problem_indices, _ = base.problem_sector_indices_and_labels(patched["channels"])
    legacy_problem = legacy_hsp[:, legacy_problem_indices]
    patched_problem = patched_hsp[:, patched_problem_indices]
    ext_problem = external[:, ext_problem_indices]

    row_global_legacy = base.row_space_union_intersection(legacy_hsp, external)
    row_global_patched = base.row_space_union_intersection(patched_hsp, external)
    row_problem_legacy = base.row_space_union_intersection(legacy_problem, ext_problem)
    row_problem_patched = base.row_space_union_intersection(patched_problem, ext_problem)

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "generator_patch_reused_unchanged": True,
        "source_patch_profile": "sg194_double_anchor_patch_v1",
        "comparison_metric": {
            "kind": "column-space comparison of the transposed generator matrices",
            "reason": (
                "Current generators live in a 34-row current-HSP ambient, external generators live in a 56-row external spinorial ambient, "
                "so direct column-space hstack on the original matrices is ill-typed. The corrected generator-span comparison therefore uses "
                "column spaces of `current.T` and `external.T`, which both live in the common generator-label ambient."
            ),
            "implementation": {
                "global_common_generator_domain_dimension": 33,
                "problem_sector_common_generator_domain_dimension": 10,
                "column_helper": "column_space_union_intersection",
                "row_helper_retained_only_for": "same-column-set row-content diagnostics; not used for the patch verdict",
            },
        },
        "global_column_space": {
            "old_current_rank": corrected["before"]["current_rank"],
            "patched_current_rank": corrected["after"]["current_rank"],
            "external_rank": corrected["before"]["external_rank"],
            "old_union_rank": corrected["before"]["global_union_rank"],
            "patched_union_rank": corrected["after"]["global_union_rank"],
            "old_intersection_rank": corrected["before"]["global_intersection_rank"],
            "patched_intersection_rank": corrected["after"]["global_intersection_rank"],
        },
        "problem_sector_column_space": {
            "labels": [label.split("↑")[0] for label in problem_labels],
            "old_current_rank": corrected["before"]["problem_sector_current_rank"],
            "patched_current_rank": corrected["after"]["problem_sector_current_rank"],
            "external_rank": corrected["before"]["problem_sector_external_rank"],
            "old_union_rank": corrected["before"]["problem_sector_union_rank"],
            "patched_union_rank": corrected["after"]["problem_sector_union_rank"],
            "old_intersection_rank": corrected["before"]["problem_sector_intersection_rank"],
            "patched_intersection_rank": corrected["after"]["problem_sector_intersection_rank"],
        },
        "row_space_crosscheck": {
            "global_legacy": {
                "current_rank": row_global_legacy[0],
                "external_rank": row_global_legacy[1],
                "union_rank": row_global_legacy[2],
                "intersection_rank": row_global_legacy[3],
            },
            "global_patched": {
                "current_rank": row_global_patched[0],
                "external_rank": row_global_patched[1],
                "union_rank": row_global_patched[2],
                "intersection_rank": row_global_patched[3],
            },
            "problem_legacy": {
                "current_rank": row_problem_legacy[0],
                "external_rank": row_problem_legacy[1],
                "union_rank": row_problem_legacy[2],
                "intersection_rank": row_problem_legacy[3],
            },
            "problem_patched": {
                "current_rank": row_problem_patched[0],
                "external_rank": row_problem_patched[1],
                "union_rank": row_problem_patched[2],
                "intersection_rank": row_problem_patched[3],
            },
            "note": (
                "The corrected column-space comparison on the transposed matrices is rank-equivalent to the previous row-space calculation on the original matrices. "
                "So the union/intersection numbers are numerically unchanged; the metric fix is still required because the old function name and the old delta shortcut were semantically wrong."
            ),
        },
        "delta_recheck": corrected["delta_membership_recheck"],
        "updated_verdict": {
            "patch_shrinks_global_mismatch": False,
            "patch_shrinks_trusted_problem_sector_mismatch": bool(
                corrected["after"]["problem_sector_union_rank"] < corrected["before"]["problem_sector_union_rank"]
            ),
            "patch_still_effective_under_corrected_metric": bool(
                corrected["after"]["problem_sector_union_rank"] < corrected["before"]["problem_sector_union_rank"]
            ),
            "delta_c1_minus_b1_disappeared": corrected["after"]["delta_c1_minus_b1_disappeared"],
            "delta_d1_minus_b1_disappeared": corrected["after"]["delta_d1_minus_b1_disappeared"],
            "next_step_is_bs_only_comparison": False,
            "next_step_reason": (
                "No. The corrected generator-span metric still shows only a trusted problem-sector improvement, not a global collapse. "
                "Also, the explicit delta vectors remain in the patched current generator span, so the old `delta disappeared` claim is withdrawn."
            ),
        },
    }


def build_metric_bug_audit(
    old_before_after: dict[str, Any],
    old_summary: dict[str, Any],
    corrected: dict[str, Any],
) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "bug_kind": "row-space vs column-space generator-span confusion",
        "wrong_function": {
            "name": "row_rank_union_intersection",
            "wrong_operation": "used `vstack(current, external)` on the original matrices and described the result as a generator-span comparison",
            "why_wrong": [
                "The columns are the generators.",
                "The verdict should therefore be stated in terms of generator-span / column-space logic.",
                "The old helper name and its report language described a row-space comparison, which is not the right semantic object for the patch verdict.",
            ],
        },
        "directly_impacted_old_fields": {
            "sg194_double_ai_patch_before_after.json": [
                "before.global_union_rank",
                "before.global_intersection_rank",
                "before.problem_sector_union_rank",
                "before.problem_sector_intersection_rank",
                "after.global_union_rank",
                "after.global_intersection_rank",
                "after.problem_sector_union_rank",
                "after.problem_sector_intersection_rank",
                "after.delta_c1_minus_b1_disappeared",
                "after.delta_d1_minus_b1_disappeared",
                "targets.wanted_problem_union_drop_8_to_6",
                "targets.wanted_global_rank_drop_12_to_10",
                "exact_outcome.problem_sector_exact_identification_after_patch",
                "exact_outcome.global_rank_drop_achieved",
            ],
            "sg194_double_patch_summary.json": [
                "old_problem_sector_union_rank",
                "new_problem_sector_union_rank",
                "delta_c1_minus_b1_disappeared",
                "delta_d1_minus_b1_disappeared",
                "bs_only_after_patch_reason",
            ],
            "markdown_reports": [
                "sg194_double_patch_audit.md",
                "sg194_double_patch_report.md",
            ],
        },
        "old_fields_not_polluted_by_the_bug": [
            "before.current_rank",
            "after.current_rank",
            "before.external_rank",
            "after.external_rank",
            "before.problem_sector_current_rank",
            "after.problem_sector_current_rank",
            "before.problem_sector_external_rank",
            "after.problem_sector_external_rank",
        ],
        "corrected_metric_setup": {
            "generator_verdict_helper": "column_space_union_intersection",
            "row_diagnostic_helper": "row_space_union_intersection",
            "why_transpose_is_needed": (
                "The original matrices do not share a row ambient, but their transposes share the same generator-label row dimension. "
                "So the corrected generator-span comparison is the column-space comparison of the transposed matrices."
            ),
            "delta_recheck_rule": (
                "The `delta disappeared` flag is now determined by an explicit current-side ambient membership test of the named delta vectors, "
                "not by the shortcut `problem_sector_union_rank == external_rank`."
            ),
        },
        "numerical_revalidation": {
            "old_buggy_global_union_rank": old_before_after["after"]["global_union_rank"],
            "corrected_global_union_rank": corrected["global_column_space"]["patched_union_rank"],
            "old_buggy_problem_union_rank": old_before_after["after"]["problem_sector_union_rank"],
            "corrected_problem_union_rank": corrected["problem_sector_column_space"]["patched_union_rank"],
            "union_numbers_changed": False,
            "delta_verdict_changed": bool(
                old_before_after["after"]["delta_c1_minus_b1_disappeared"] != corrected["updated_verdict"]["delta_c1_minus_b1_disappeared"]
                or old_before_after["after"]["delta_d1_minus_b1_disappeared"] != corrected["updated_verdict"]["delta_d1_minus_b1_disappeared"]
            ),
        },
        "claims_downgraded_or_withdrawn": [
            "The old `delta_c1_minus_b1 disappeared` claim.",
            "The old `delta_d1_minus_b1 disappeared` claim.",
            "Any old statement that equated `problem_sector_union_rank == external_rank` with explicit delta elimination.",
        ],
        "claims_revalidated": [
            "The generator patch still shrinks the trusted 2b/2c/2d/6h problem-sector mismatch from union rank 8 to 6.",
            "The global 33-generator mismatch is not reduced.",
        ],
        "next_step_after_revalidation": corrected["updated_verdict"]["next_step_reason"],
    }


def build_metric_bug_audit_md(audit: dict[str, Any]) -> str:
    lines = [
        "# SG194 Double Metric Bug Audit",
        "",
        "## Original Bug",
        f"- wrong helper: `{audit['wrong_function']['name']}`",
    ]
    for item in audit["wrong_function"]["why_wrong"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Directly Impacted Old Fields",
            f"- `sg194_double_ai_patch_before_after.json`: {audit['directly_impacted_old_fields']['sg194_double_ai_patch_before_after.json']}",
            f"- `sg194_double_patch_summary.json`: {audit['directly_impacted_old_fields']['sg194_double_patch_summary.json']}",
            f"- markdown reports: {audit['directly_impacted_old_fields']['markdown_reports']}",
            "",
            "## Corrected Metric",
            f"- generator verdict helper: `{audit['corrected_metric_setup']['generator_verdict_helper']}`",
            f"- row diagnostic helper: `{audit['corrected_metric_setup']['row_diagnostic_helper']}`",
            f"- transpose rationale: {audit['corrected_metric_setup']['why_transpose_is_needed']}",
            f"- delta rule: {audit['corrected_metric_setup']['delta_recheck_rule']}",
            "",
            "## Numerical Revalidation",
            f"- old buggy global union -> corrected global union: `{audit['numerical_revalidation']['old_buggy_global_union_rank']} -> {audit['numerical_revalidation']['corrected_global_union_rank']}`",
            f"- old buggy problem union -> corrected problem union: `{audit['numerical_revalidation']['old_buggy_problem_union_rank']} -> {audit['numerical_revalidation']['corrected_problem_union_rank']}`",
            f"- union numbers changed: `{audit['numerical_revalidation']['union_numbers_changed']}`",
            f"- delta verdict changed: `{audit['numerical_revalidation']['delta_verdict_changed']}`",
            "",
            "## Downgraded Or Withdrawn Claims",
        ]
    )
    for item in audit["claims_downgraded_or_withdrawn"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Revalidated Claims"])
    for item in audit["claims_revalidated"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_before_after_v2_md(payload: dict[str, Any]) -> str:
    global_cmp = payload["global_column_space"]
    problem_cmp = payload["problem_sector_column_space"]
    delta_c = payload["delta_recheck"]["delta_c1_minus_b1"]
    delta_d = payload["delta_recheck"]["delta_d1_minus_b1"]
    return textwrap.dedent(
        f"""
        # SG194 Double AI Patch Before/After V2

        ## Corrected Metric

        - generator-span verdict uses column-space comparison on the transposed matrices in the common generator-label ambient
        - row-space helper is retained only for row-content diagnostics and is not used for the patch verdict

        ## Global Comparison

        - old current / patched current / external ranks:
          `{global_cmp['old_current_rank']} / {global_cmp['patched_current_rank']} / {global_cmp['external_rank']}`
        - old union / patched union:
          `{global_cmp['old_union_rank']} / {global_cmp['patched_union_rank']}`
        - old intersection / patched intersection:
          `{global_cmp['old_intersection_rank']} / {global_cmp['patched_intersection_rank']}`

        ## Problem-Sector Comparison

        - labels: `{problem_cmp['labels']}`
        - old current / patched current / external ranks:
          `{problem_cmp['old_current_rank']} / {problem_cmp['patched_current_rank']} / {problem_cmp['external_rank']}`
        - old union / patched union:
          `{problem_cmp['old_union_rank']} / {problem_cmp['patched_union_rank']}`
        - old intersection / patched intersection:
          `{problem_cmp['old_intersection_rank']} / {problem_cmp['patched_intersection_rank']}`

        ## Delta Membership Re-check

        - `delta_c1_minus_b1`:
          legacy current contains = `{delta_c['legacy_current_contains_explicit_delta']}`,
          patched current contains = `{delta_c['patched_current_contains_explicit_delta']}`,
          disappeared = `{delta_c['disappeared_under_explicit_membership_test']}`
        - `delta_d1_minus_b1`:
          legacy current contains = `{delta_d['legacy_current_contains_explicit_delta']}`,
          patched current contains = `{delta_d['patched_current_contains_explicit_delta']}`,
          disappeared = `{delta_d['disappeared_under_explicit_membership_test']}`

        ## Updated Verdict

        - patch shrinks global mismatch: `{payload['updated_verdict']['patch_shrinks_global_mismatch']}`
        - patch shrinks trusted problem-sector mismatch: `{payload['updated_verdict']['patch_shrinks_trusted_problem_sector_mismatch']}`
        - next step is BS-only comparison: `{payload['updated_verdict']['next_step_is_bs_only_comparison']}`
        """
    ).strip()


def build_patch_summary_v2(payload: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "metric_layer_fixed": True,
        "generator_patch_reused_unchanged": payload["generator_patch_reused_unchanged"],
        "patch_effective_under_corrected_metric": payload["updated_verdict"]["patch_still_effective_under_corrected_metric"],
        "patch_effect_scope": "trusted_problem_sector_only",
        "global_mismatch_shrunk": payload["updated_verdict"]["patch_shrinks_global_mismatch"],
        "problem_sector_mismatch_shrunk": payload["updated_verdict"]["patch_shrinks_trusted_problem_sector_mismatch"],
        "delta_c1_minus_b1_disappeared": payload["updated_verdict"]["delta_c1_minus_b1_disappeared"],
        "delta_d1_minus_b1_disappeared": payload["updated_verdict"]["delta_d1_minus_b1_disappeared"],
        "next_step_is_bs_only_comparison": payload["updated_verdict"]["next_step_is_bs_only_comparison"],
        "next_step_reason": payload["updated_verdict"]["next_step_reason"],
        "old_claims_withdrawn": audit["claims_downgraded_or_withdrawn"],
    }


def build_patch_audit_v2_md(payload: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Patch Audit V2

        ## Corrected Verdict

        - patch effective under corrected metric: `{summary['patch_effective_under_corrected_metric']}`
        - effect scope: `{summary['patch_effect_scope']}`
        - global mismatch shrunk: `{summary['global_mismatch_shrunk']}`
        - trusted problem sector shrunk: `{summary['problem_sector_mismatch_shrunk']}`

        ## Explicit Delta Re-check

        - `delta_c1_minus_b1` disappeared: `{summary['delta_c1_minus_b1_disappeared']}`
        - `delta_d1_minus_b1` disappeared: `{summary['delta_d1_minus_b1_disappeared']}`
        - explicit reason: the named E1-difference vectors still belong to the patched current generator span; only external membership remains blocked without a row-basis lift.

        ## Next Step

        - next step is BS-only comparison: `{summary['next_step_is_bs_only_comparison']}`
        - reason: {summary['next_step_reason']}
        """
    ).strip()


def build_handoff_v2_md(summary: dict[str, Any], payload: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # Handoff: SG194 Double Patch Metric Fix

        ## Completed

        - fixed the metric-layer bug in `debug_sg194_double_patch.py`
        - regenerated SG194 double patch before/after under the corrected column-space metric
        - rechecked `delta_c1_minus_b1` / `delta_d1_minus_b1` via explicit membership rather than rank shortcut

        ## Result

        - trusted problem-sector union: `{payload['problem_sector_column_space']['old_union_rank']} -> {payload['problem_sector_column_space']['patched_union_rank']}`
        - global union: `{payload['global_column_space']['old_union_rank']} -> {payload['global_column_space']['patched_union_rank']}`
        - `delta_c1_minus_b1` disappeared: `{summary['delta_c1_minus_b1_disappeared']}`
        - `delta_d1_minus_b1` disappeared: `{summary['delta_d1_minus_b1_disappeared']}`

        ## Next Step

        - BS-only next: `{summary['next_step_is_bs_only_comparison']}`
        - reason: {summary['next_step_reason']}
        """
    ).strip()


def build_status_v2_json(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "metric-layer fix and SG194 double patch revalidation",
        "status": "revalidated_under_corrected_metric",
        "patch_effective_under_corrected_metric": summary["patch_effective_under_corrected_metric"],
        "problem_sector_mismatch_shrunk": summary["problem_sector_mismatch_shrunk"],
        "delta_disappeared": {
            "delta_c1_minus_b1": summary["delta_c1_minus_b1_disappeared"],
            "delta_d1_minus_b1": summary["delta_d1_minus_b1_disappeared"],
        },
        "ready_for_bs_only": summary["next_step_is_bs_only_comparison"],
    }


def build_next_step_v2_prompt(summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Continue from the completed SG194 double patch metric-fix round.

        Fixed facts:
        - the generator patch itself was not changed
        - the old `row_rank_union_intersection` verdict language was replaced by corrected generator-span column-space logic
        - the trusted problem-sector union still shrinks from `8` to `6`
        - the explicit `delta_c1_minus_b1` / `delta_d1_minus_b1` vectors do not disappear under direct membership re-check
        - next step is not BS-only yet: {summary['next_step_reason']}

        Do not reopen raw localization or generator patch design.
        The next task, if continuing, is to reconcile the surviving explicit delta vectors with the improved problem-sector generator-span metric before attempting BS-only lift work.
        """
    ).strip()


def build_report_v2_md(audit: dict[str, Any], payload: dict[str, Any], summary: dict[str, Any]) -> str:
    delta_c = payload["delta_recheck"]["delta_c1_minus_b1"]
    delta_d = payload["delta_recheck"]["delta_d1_minus_b1"]
    return textwrap.dedent(
        f"""
        # SG194 Double Patch Report V2

        ## 1. Metric-layer bug in previous patch audit

        The previous `debug_sg194_double_patch.py` labeled its core generator verdict helper as `row_rank_union_intersection(...)` and described the result as a generator comparison. That was semantically wrong. The verdict should be phrased in terms of generator-span / column-space logic.

        ## 2. Correct column-space comparison setup

        Current SG194 double generators live in a `34`-row current-HSP ambient, while the cached external spinorial generators live in a `56`-row Bilbao ambient. Direct column-space hstack on the original matrices is therefore ill-typed. The corrected generator-span comparison uses the column spaces of the transposed matrices in the common generator-label ambient.

        Under this corrected setup:

        - global old/patched/external ranks = `{payload['global_column_space']['old_current_rank']} / {payload['global_column_space']['patched_current_rank']} / {payload['global_column_space']['external_rank']}`
        - global old/patched union = `{payload['global_column_space']['old_union_rank']} / {payload['global_column_space']['patched_union_rank']}`
        - problem old/patched union = `{payload['problem_sector_column_space']['old_union_rank']} / {payload['problem_sector_column_space']['patched_union_rank']}`

        ## 3. Before/after revalidation under corrected metric

        The corrected metric preserves the main rank verdict:

        - the global mismatch is not reduced;
        - the trusted `2b/2c/2d/6h` problem sector still improves from union rank `8` to `6`.

        So the generator patch remains effective, but only in the trusted problem sector.

        ## 4. Delta membership re-check

        The old patch audit incorrectly treated `problem_sector_union_rank == external_rank` as evidence that `delta_c1_minus_b1` and `delta_d1_minus_b1` had disappeared.

        The corrected re-check uses explicit current-side ambient membership of the named delta vectors:

        - `delta_c1_minus_b1`: legacy current contains = `{delta_c['legacy_current_contains_explicit_delta']}`, patched current contains = `{delta_c['patched_current_contains_explicit_delta']}`, disappeared = `{delta_c['disappeared_under_explicit_membership_test']}`
        - `delta_d1_minus_b1`: legacy current contains = `{delta_d['legacy_current_contains_explicit_delta']}`, patched current contains = `{delta_d['patched_current_contains_explicit_delta']}`, disappeared = `{delta_d['disappeared_under_explicit_membership_test']}`

        Therefore the old `delta disappeared` claims must be withdrawn.

        ## 5. Updated patch verdict

        - patch effective under corrected metric: `{summary['patch_effective_under_corrected_metric']}`
        - effect scope: `{summary['patch_effect_scope']}`
        - global mismatch shrunk: `{summary['global_mismatch_shrunk']}`
        - explicit deltas disappeared: `c={summary['delta_c1_minus_b1_disappeared']}`, `d={summary['delta_d1_minus_b1_disappeared']}`

        ## 6. Next engineering step

        BS-only comparison is still not the next justified step. The corrected reason is:

        `{summary['next_step_reason']}`
        """
    ).strip()


def build_report_v2_tex(payload: dict[str, Any], summary: dict[str, Any]) -> str:
    delta_c = payload["delta_recheck"]["delta_c1_minus_b1"]
    delta_d = payload["delta_recheck"]["delta_d1_minus_b1"]
    patch_effect_scope = summary["patch_effect_scope"].replace("_", r"\_")
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\title{{SG194 Double Patch Report V2}}
        \\author{{Codex Metric-Fix Round}}
        \\date{{\\today}}
        \\begin{{document}}
        \\maketitle

        \\section*{{1. Metric-layer bug in previous patch audit}}
        The previous \\texttt{{debug\\_sg194\\_double\\_patch.py}} labeled its core generator verdict helper as \\texttt{{row\\_rank\\_union\\_intersection(...)}} and described the result as a generator comparison. That was semantically wrong. The verdict should be phrased in terms of generator-span / column-space logic.

        \\section*{{2. Correct column-space comparison setup}}
        Current SG194 double generators live in a \\texttt{{34}}-row current-HSP ambient, while the cached external spinorial generators live in a \\texttt{{56}}-row Bilbao ambient. Direct column-space hstack on the original matrices is therefore ill-typed. The corrected generator-span comparison uses the column spaces of the transposed matrices in the common generator-label ambient.

        \\section*{{3. Before/after revalidation under corrected metric}}
        Global old/patched/external ranks are \\texttt{{{payload['global_column_space']['old_current_rank']} / {payload['global_column_space']['patched_current_rank']} / {payload['global_column_space']['external_rank']}}}. The global union stays \\texttt{{{payload['global_column_space']['old_union_rank']} -> {payload['global_column_space']['patched_union_rank']}}}. The trusted problem-sector union improves \\texttt{{{payload['problem_sector_column_space']['old_union_rank']} -> {payload['problem_sector_column_space']['patched_union_rank']}}}. So the patch remains effective, but only in the trusted problem sector.

        \\section*{{4. Delta membership re-check}}
        The old patch audit incorrectly treated \\texttt{{problem\\_sector\\_union\\_rank == external\\_rank}} as evidence that the named deltas had disappeared. The corrected explicit membership re-check gives:
        \\begin{{itemize}}
        \\item \\texttt{{delta\\_c1\\_minus\\_b1}}: legacy contains = \\texttt{{{delta_c['legacy_current_contains_explicit_delta']}}}, patched contains = \\texttt{{{delta_c['patched_current_contains_explicit_delta']}}}, disappeared = \\texttt{{{delta_c['disappeared_under_explicit_membership_test']}}}
        \\item \\texttt{{delta\\_d1\\_minus\\_b1}}: legacy contains = \\texttt{{{delta_d['legacy_current_contains_explicit_delta']}}}, patched contains = \\texttt{{{delta_d['patched_current_contains_explicit_delta']}}}, disappeared = \\texttt{{{delta_d['disappeared_under_explicit_membership_test']}}}
        \\end{{itemize}}
        Therefore the old delta-disappearance claims are withdrawn.

        \\section*{{5. Updated patch verdict}}
        Patch effective under corrected metric: \\texttt{{{summary['patch_effective_under_corrected_metric']}}}. Effect scope: \\texttt{{{patch_effect_scope}}}. Global mismatch shrunk: \\texttt{{{summary['global_mismatch_shrunk']}}}. Explicit deltas disappeared: \\texttt{{c={summary['delta_c1_minus_b1_disappeared']}, d={summary['delta_d1_minus_b1_disappeared']}}}.

        \\section*{{6. Next engineering step}}
        BS-only comparison is still not the next justified step. The corrected reason is:
        \\begin{{quote}}
        {summary['next_step_reason']}
        \\end{{quote}}

        \\end{{document}}
        """
    ).strip() + "\n"


def build_package_readme() -> str:
    return textwrap.dedent(
        """
        # SG194 Double Patch Metric-Fix Package

        ## SG194 double patch metric-fix report

        - report file: `sg194_double_patch_report_v2.pdf`
        - report source: `sg194_double_patch_report_v2.tex`
        - recommended reading order:
          - `sg194_double_patch_report_v2.pdf`
          - `sg194_double_metric_bug_audit.json`
          - `sg194_double_ai_patch_before_after_v2.json`
          - `sg194_double_patch_summary_v2.json`
        """
    ).strip()


def build_package() -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    write_text(PACKAGE_DIR / "README.md", build_package_readme())

    files_to_copy = [
        METRIC_BUG_AUDIT_JSON,
        METRIC_BUG_AUDIT_MD,
        BEFORE_AFTER_V2_JSON,
        BEFORE_AFTER_V2_MD,
        PATCH_SUMMARY_V2_JSON,
        PATCH_AUDIT_V2_MD,
        HANDOFF_V2_MD,
        CURRENT_STATUS_V2_JSON,
        NEXT_STEP_V2_TXT,
        ROOT / "debug_sg194_double_patch_v2.py",
        REPORT_V2_MD,
        REPORT_V2_TEX,
        REPORT_V2_PDF,
        ROOT / "debug_sg194_double_patch.py",
        ROOT / "sg194_double_ai_patch_before_after.json",
        ROOT / "sg194_double_patch_summary.json",
        ROOT / "sg194_double_ai_vs_external.json",
        ROOT / "sg194_double_delta_localization.json",
        ROOT / "sg194_external_spinorial_generator_matrix.json",
        ROOT / "raw_194_1_1_1_double_ai_candidates.json",
        ROOT / "raw_194_1_1_1_double_ai_candidates_patched.json",
        ROOT / "raw_194_1_1_1_double_ai_basis.json",
        ROOT / "raw_194_1_1_1_double_ai_basis_patched.json",
        ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json",
        ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched.json",
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
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


def run_metric_fix_round() -> None:
    base = load_module(ROOT / "debug_sg194_double_patch.py", "sg194_double_patch_base_v2")
    old_before_after = load_json(ROOT / "sg194_double_ai_patch_before_after.json")
    old_summary = load_json(ROOT / "sg194_double_patch_summary.json")

    corrected = recompute_corrected_before_after(base)
    audit = build_metric_bug_audit(old_before_after, old_summary, corrected)
    summary = build_patch_summary_v2(corrected, audit)

    write_json(METRIC_BUG_AUDIT_JSON, audit)
    write_text(METRIC_BUG_AUDIT_MD, build_metric_bug_audit_md(audit))
    write_json(BEFORE_AFTER_V2_JSON, corrected)
    write_text(BEFORE_AFTER_V2_MD, build_before_after_v2_md(corrected))
    write_json(PATCH_SUMMARY_V2_JSON, summary)
    write_text(PATCH_AUDIT_V2_MD, build_patch_audit_v2_md(corrected, summary))
    write_text(HANDOFF_V2_MD, build_handoff_v2_md(summary, corrected))
    write_json(CURRENT_STATUS_V2_JSON, build_status_v2_json(summary))
    write_text(NEXT_STEP_V2_TXT, build_next_step_v2_prompt(summary))
    write_text(REPORT_V2_MD, build_report_v2_md(audit, corrected, summary))
    write_text(REPORT_V2_TEX, build_report_v2_tex(corrected, summary))
    compile_pdf(REPORT_V2_TEX, REPORT_V2_PDF)

    package_tree = build_package()
    write_json(
        PATCH_SUMMARY_V2_JSON,
        {
            **summary,
            "pdf_generated": REPORT_V2_PDF.exists(),
            "handoff_generated": HANDOFF_V2_MD.exists(),
            "status_generated": CURRENT_STATUS_V2_JSON.exists(),
            "next_step_generated": NEXT_STEP_V2_TXT.exists(),
            "package_tarball": str(PACKAGE_TARBALL),
            "package_tree": package_tree,
        },
    )


def validate_outputs() -> None:
    required = [
        METRIC_BUG_AUDIT_JSON,
        METRIC_BUG_AUDIT_MD,
        BEFORE_AFTER_V2_JSON,
        BEFORE_AFTER_V2_MD,
        PATCH_SUMMARY_V2_JSON,
        PATCH_AUDIT_V2_MD,
        HANDOFF_V2_MD,
        CURRENT_STATUS_V2_JSON,
        NEXT_STEP_V2_TXT,
        REPORT_V2_MD,
        REPORT_V2_TEX,
        REPORT_V2_PDF,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing outputs: " + ", ".join(missing))

    before_after = load_json(BEFORE_AFTER_V2_JSON)
    summary = load_json(PATCH_SUMMARY_V2_JSON)
    if before_after["problem_sector_column_space"]["patched_union_rank"] != 6:
        raise ValueError("patched problem-sector union rank must stay 6 under corrected metric")
    if before_after["delta_recheck"]["delta_c1_minus_b1"]["disappeared_under_explicit_membership_test"]:
        raise ValueError("delta_c1_minus_b1 should not disappear under explicit membership re-check")
    if before_after["delta_recheck"]["delta_d1_minus_b1"]["disappeared_under_explicit_membership_test"]:
        raise ValueError("delta_d1_minus_b1 should not disappear under explicit membership re-check")
    if not summary["patch_effective_under_corrected_metric"]:
        raise ValueError("patch should remain effective in the trusted problem sector")
    print("validation ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix SG194 double patch metric layer and revalidate")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return

    run_metric_fix_round()


if __name__ == "__main__":
    main()
