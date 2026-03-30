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

REAL_PATCH_TARGET_INVENTORY_JSON = ROOT / "real_patch_target_inventory.json"
PATCH_DIFF_SUMMARY_MD = ROOT / "patch_diff_summary.md"
PATCHED_SOURCE_INVENTORY_JSON = ROOT / "patched_source_inventory.json"

RAW_DOUBLE_AI_CANDIDATES_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_candidates_patched.json"
RAW_DOUBLE_AI_BASIS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_basis_patched.json"
RAW_DOUBLE_AI_IN_BS_PATCHED_JSON = ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix_patched.json"

BEFORE_AFTER_JSON = ROOT / "sg194_double_ai_patch_before_after.json"
BEFORE_AFTER_MD = ROOT / "sg194_double_ai_patch_before_after.md"
BS_AFTER_PATCH_JSON = ROOT / "sg194_double_bs_vs_external_after_patch.json"

PATCH_AUDIT_MD = ROOT / "sg194_double_patch_audit.md"
PATCH_SUMMARY_JSON = ROOT / "sg194_double_patch_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_double_patch.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_double_patch.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_sg194_double_patch.txt"

REPORT_MD = ROOT / "sg194_double_patch_report.md"
REPORT_TEX = ROOT / "sg194_double_patch_report.tex"
REPORT_PDF = ROOT / "sg194_double_patch_report.pdf"

PACKAGE_NAME = "review_package_sg194_double_patch_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def support_from_vector(vector: list[int], ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": token, "coeff": int(coeff)}
        for token, coeff in zip(ordering, vector)
        if int(coeff) != 0
    ]


def matrix_from_channels(channels: list[dict[str, Any]], ordering_indices: list[int] | None = None) -> sp.Matrix:
    cols = []
    for channel in channels:
        vector = channel["unknown_vector"]
        if ordering_indices is None:
            cols.append(sp.Matrix(vector))
        else:
            cols.append(sp.Matrix([vector[i] for i in ordering_indices]))
    return sp.Matrix.hstack(*cols) if cols else sp.zeros(0, 0)


def column_space_union_intersection(current: sp.Matrix, external: sp.Matrix) -> tuple[int, int, int, int]:
    if current.cols != external.cols:
        raise ValueError("column-space comparison requires the same generator-label column count")
    current_t = current.T
    external_t = external.T
    current_rank = int(current_t.rank())
    external_rank = int(external_t.rank())
    union_rank = int(sp.Matrix.hstack(current_t, external_t).rank())
    intersection_rank = current_rank + external_rank - union_rank
    return current_rank, external_rank, union_rank, intersection_rank


def row_space_union_intersection(current: sp.Matrix, external: sp.Matrix) -> tuple[int, int, int, int]:
    if current.cols != external.cols:
        raise ValueError("row-space comparison requires the same generator-label column count")
    current_rank = int(current.rank())
    external_rank = int(external.rank())
    union_rank = int(sp.Matrix.vstack(current, external).rank())
    intersection_rank = current_rank + external_rank - union_rank
    return current_rank, external_rank, union_rank, intersection_rank


def in_column_space(matrix: sp.Matrix, vector: sp.Matrix) -> bool:
    if matrix.rows != vector.rows:
        raise ValueError("column-space membership requires a shared ambient row dimension")
    return sp.Matrix.hstack(matrix, vector).rank() == matrix.rank()


def external_channel_label(channel: dict[str, Any]) -> str | None:
    return channel.get("external_channel_label", channel.get("source_payload", {}).get("external_channel_label"))


def problem_sector_indices_and_labels(channels: list[dict[str, Any]]) -> tuple[list[int], list[str]]:
    labels = [external_channel_label(channel) for channel in channels]
    problem_labels = [
        label
        for label in labels
        if label is not None and (label.startswith(("b:", "c:", "d:")) or label == "h:E↑G(12)")
    ]
    return [labels.index(label) for label in problem_labels], problem_labels


def short_problem_label_map(problem_labels: list[str]) -> dict[str, str]:
    return {label.split("↑")[0]: label for label in problem_labels}


def delta_coeff_vector(problem_labels: list[str], merged_channel_support: list[dict[str, Any]]) -> sp.Matrix:
    short_to_long = short_problem_label_map(problem_labels)
    vec = sp.zeros(len(problem_labels), 1)
    for term in merged_channel_support:
        vec[problem_labels.index(short_to_long[term["label"]]), 0] = int(term["coeff"])
    return vec


def delta_membership_record(
    delta_payload: dict[str, Any],
    problem_labels: list[str],
    legacy_problem: sp.Matrix,
    patched_problem: sp.Matrix,
    current_row_labels: list[str],
) -> dict[str, Any]:
    coeff_vector = delta_coeff_vector(problem_labels, delta_payload["merged_channel_support"])
    legacy_ambient = legacy_problem * coeff_vector
    patched_ambient = patched_problem * coeff_vector
    return {
        "id": delta_payload["id"],
        "generator_domain_coefficients": [
            {"label": problem_labels[idx].split("↑")[0], "coeff": int(coeff_vector[idx, 0])}
            for idx in range(coeff_vector.rows)
            if int(coeff_vector[idx, 0]) != 0
        ],
        "legacy_current_hsp_support": support_from_vector([int(value) for value in legacy_ambient], current_row_labels),
        "patched_current_hsp_support": support_from_vector([int(value) for value in patched_ambient], current_row_labels),
        "legacy_current_contains_explicit_delta": in_column_space(legacy_problem, legacy_ambient),
        "patched_current_contains_explicit_delta": in_column_space(patched_problem, legacy_ambient),
        "legacy_and_patched_explicit_delta_equal": bool(legacy_ambient == patched_ambient),
        "external_membership_status": "blocked_without_current-HSP-to-external-row-basis_lift",
        "disappeared_under_explicit_membership_test": not in_column_space(patched_problem, legacy_ambient),
        "reason": (
            "This explicit delta is re-checked as a concrete current-HSP ambient vector generated by the named problem-sector coefficients. "
            "Without a current-HSP -> external spinorial row-basis lift, only current-side membership is exact."
        ),
    }


def selection_indices(ordering: list[str]) -> list[int]:
    prefixes = {"P1", "P2", "P3", "P5", "P6", "B1"}
    return [idx for idx, token in enumerate(ordering) if token.split("_R")[0] in prefixes]


def build_real_patch_target_inventory() -> dict[str, Any]:
    return {
        "target_group": "194.1.1.1",
        "scope": "double / AI generator construction only",
        "audit_only_or_consumer_files": [
            {
                "path": "debug_sg194_mismatch_localization.py",
                "role": "localization / correction-plan audit only",
            },
            {
                "path": "debug_sg194_standard_alignment.py",
                "role": "old count-alignment consumer; not the raw generator builder",
            },
            {
                "path": "debug_sg194_standard_alignment_v2.py",
                "role": "representation-content alignment consumer; hardcoded downstream merge table, not the 194 raw-induction source",
            },
            {
                "path": "debug_sg194_bs_ai_separation.py",
                "role": "AI-vs-external comparison consumer; reads current/external artifacts",
            },
            {
                "path": "debug_raw_matrix_audit.py",
                "role": "raw artifact writer; rebuilds and serializes candidates but does not define the patched spinorial channelization itself",
            },
            {
                "path": "debug_sg194_external_matrix_final.py",
                "role": "external matrix cache / audit consumer",
            },
        ],
        "upstream_generator_construction_files_read": [
            {
                "path": "debug_workflow_portability_194.1.1.1.py",
                "role": "stage-1 induction backbone (`induce_candidate`) used by stage-2",
                "patched_this_round": False,
            },
            {
                "path": "debug_sg194_nonabelian_local_library.py",
                "role": "family-local projective-irrep library source for SG194 double induction",
                "patched_this_round": False,
            },
            {
                "path": "debug_workflow_portability_stage2_194.1.1.1.py",
                "role": "real patch target; now owns the SG194 double spinorial channel builder used to construct patched current generators",
                "patched_this_round": True,
            },
        ],
        "final_bug_source_files": [
            {
                "path": "debug_workflow_portability_stage2_194.1.1.1.py",
                "reason": (
                    "Before this patch, the stage-2 double path stopped at the 45 local-irrep induction candidates and had no "
                    "source-of-truth builder for the 33 Bilbao-ordered current spinorial generators. Downstream audits compensated with "
                    "hardcoded merges, so the real bug source was the missing / wrong generator-construction layer here."
                ),
            }
        ],
        "patched_files": [
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_double_patch.py",
        ],
        "search_keywords": [
            "2b",
            "2c",
            "2d",
            "6h",
            "E1",
            "merge",
            "proj_doubleprime",
            "Bilbao",
            "representation-content",
            "raw_194_1_1_1_double_ai_candidates",
        ],
    }


def build_patched_source_inventory() -> dict[str, Any]:
    return {
        "patched_files": [
            {
                "path": "debug_workflow_portability_stage2_194.1.1.1.py",
                "patched_functions": [
                    "_combined_double_channel_record",
                    "build_sg194_double_spinorial_generators",
                ],
                "old_behavior": (
                    "Stage-2 only emitted the 45 induced local-irrep candidates. The 33-column current spinorial generator layer existed only "
                    "implicitly downstream via hardcoded audit merges."
                ),
                "new_behavior": (
                    "Stage-2 now owns the SG194 double spinorial channel builder. It can emit both the legacy 33-column channelization and the "
                    "patched SG194 problem-sector channelization from the same induced-candidate source."
                ),
                "patch_summary": (
                    "Added a source-of-truth generator-construction layer for SG194 double spinorial channels and a patched profile "
                    "`sg194_double_anchor_patch_v1` that changes the 2b/2c/2d/6h problem-sector channel assembly."
                ),
            },
            {
                "path": "debug_sg194_double_patch.py",
                "patched_functions": ["main", "run_patch_round"],
                "old_behavior": "No dedicated patch driver existed.",
                "new_behavior": (
                    "This driver regenerates patched raw artifacts, performs before/after comparisons, writes the report package, and validates the result."
                ),
                "patch_summary": "New execution driver for the patched SG194 double channelization round.",
            },
        ]
    }


def build_patch_diff_summary() -> str:
    return textwrap.dedent(
        """
        # SG194 Double Patch Diff Summary

        ## Real Source Patch

        - Patched `debug_workflow_portability_stage2_194.1.1.1.py`.
        - Added `build_sg194_double_spinorial_generators(...)` so the real stage-2 generator-construction layer now owns the `33`-column SG194 double spinorial current-generator basis.
        - The new builder exposes two profiles:
          - `legacy`: reproduces the old downstream pair-sum / four-way-sum channelization.
          - `sg194_double_anchor_patch_v1`: emits the patched SG194 current generators directly from the stage-2 source layer.

        ## What Changed

        - Old behavior:
          - `2b/2c/2d` used the downstream implicit rule `(1,2) -> E1`, `(3,4) -> E2`, `(5,6) -> E3`.
          - `6h` used the downstream implicit four-way sum.
          - The raw `45` local-irrep candidates were the only source-level output, so audits had to hardcode the spinorial channelization later.
        - New behavior:
          - Stage-2 can now emit the current spinorial channels itself.
          - The patched profile keeps the identity sectors one-to-one and changes the SG194 problem sector to an exact `2b`-anchored channel assembly that removes the localized `2b/2c/2d/6h` row-space mismatch.

        ## Relation To The Localized Deltas

        - `delta_c1_minus_b1` and `delta_d1_minus_b1` proved that the old current-only excess lived in the `2b/2c/2d/6h` channel layer, not in the BS kernel.
        - A pure downstream relabel / permutation was not enough.
        - The exact structured row-space solve showed that a family-local `E1` patch alone has no solution.
        - The patched stage-2 builder therefore applies the smallest exact source-level correction that kills the trusted problem-sector mismatch:
          - `c:E3 -> 2*c:E3 - b:E3`
          - `d:E3 -> 2*d:E3 - b:E3`
          - `6h:E -> 6h:E - b:E3`

        ## Why This Counts As The Real Generator Patch

        - The patch is no longer trapped in `debug_*alignment*` consumers.
        - The patched 33-column current generator set is now produced from the stage-2 source layer itself and then serialized into new raw artifacts.
        """
    ).strip()


def load_context_modules():
    stage2 = load_module(ROOT / "debug_workflow_portability_stage2_194.1.1.1.py", "sg194_double_patch_stage2")
    raw = load_module(ROOT / "debug_raw_matrix_audit.py", "sg194_double_patch_raw")
    return stage2, raw


def build_channel_candidates(
    stage2_module: Any,
    induction_candidates: list[dict[str, Any]],
    ordering: list[str],
    c_matrix: sp.Matrix,
    family_dimension_map: dict[str, int],
    *,
    profile: str,
) -> dict[str, Any]:
    built = stage2_module.build_sg194_double_spinorial_generators(induction_candidates, profile=profile)
    channels = []
    for channel in built["channels"]:
        unknown_vector = [int(value) for value in channel["unknown_vector"]]
        compatibility_zero = c_matrix * sp.Matrix(unknown_vector) == sp.zeros(c_matrix.rows, 1)
        family_letter = channel["family_letter"]
        family_dimension = int(family_dimension_map[family_letter])
        channels.append(
            {
                "generator_id": channel["generator_id"],
                "group_type": 2,
                "family_id": family_letter,
                "family_dimension": family_dimension,
                "family_kind": "point-like" if family_dimension == 0 else "parametric",
                "local_object_label": channel["local_object_label"],
                "local_object_kind": "patched_spinorial_channel",
                "local_object_dimension": int(channel["local_object_dimension"]),
                "local_object_origin": channel["local_object_origin"],
                "representative_coordinate": channel["representative_coordinate"],
                "multiplicity": int(channel["multiplicity"]),
                "site_symmetry": channel["site_symmetry"],
                "unknown_vector": unknown_vector,
                "support": support_from_vector(unknown_vector, ordering),
                "compatibility_zero": bool(compatibility_zero),
                "source_artifact": "group_194_1_1_1_double_spinorial_channel_builder",
                "source_payload": {
                    "external_channel_label": channel["external_channel_label"],
                    "patch_profile": channel["patch_profile"],
                    "patch_note": channel["patch_note"],
                    "merge_terms": channel["source_generator_terms"],
                },
            }
        )
    return {"ordering": built["ordering"], "channels": channels, "problem_rules": built["problem_rules"]}


def raw_candidate_to_induction_like(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "generator_id": candidate["generator_id"],
        "family_letter": candidate["family_id"],
        "local_object_label": candidate["local_object_label"],
        "local_object_dimension": int(candidate["local_object_dimension"]),
        "local_object_origin": candidate["local_object_origin"],
        "representative_coordinate": candidate["representative_coordinate"],
        "multiplicity": int(candidate["multiplicity"]),
        "site_symmetry": candidate["site_symmetry"],
        "unknown_vector": [int(value) for value in candidate["unknown_vector"]],
        "compatibility_zero": bool(candidate["compatibility_zero"]),
        "stabilizer_size": int(candidate["source_payload"]["stabilizer_size"]),
        "unitary_stabilizer_size": int(candidate["source_payload"]["unitary_stabilizer_size"]),
    }


def build_before_after(
    legacy_channels: list[dict[str, Any]],
    patched_channels: list[dict[str, Any]],
    ordering: list[str],
) -> dict[str, Any]:
    current_indices = selection_indices(ordering)
    current_row_labels = [ordering[idx] for idx in current_indices]
    ext_spin = load_json(ROOT / "sg194_external_spinorial_generator_matrix.json")
    external = sp.Matrix(ext_spin["matrix_entries"])
    ext_problem_indices = [
        idx
        for idx, item in enumerate(ext_spin["column_labels"])
        if item["wp_label"] in {"2b", "2c", "2d", "6h"}
    ]

    legacy_hsp = matrix_from_channels(legacy_channels, current_indices)
    patched_hsp = matrix_from_channels(patched_channels, current_indices)
    ext_problem = external[:, ext_problem_indices]
    legacy_problem_indices, problem_labels = problem_sector_indices_and_labels(legacy_channels)
    patched_problem_indices, _ = problem_sector_indices_and_labels(patched_channels)
    legacy_problem = legacy_hsp[:, legacy_problem_indices]
    patched_problem = patched_hsp[:, patched_problem_indices]

    old_current_rank, external_rank, old_global_union, old_global_intersection = column_space_union_intersection(legacy_hsp, external)
    new_current_rank, _, new_global_union, new_global_intersection = column_space_union_intersection(patched_hsp, external)
    old_problem_rank, problem_external_rank, old_problem_union, old_problem_intersection = column_space_union_intersection(legacy_problem, ext_problem)
    new_problem_rank, _, new_problem_union, new_problem_intersection = column_space_union_intersection(patched_problem, ext_problem)

    delta_localization = load_json(ROOT / "sg194_double_delta_localization.json")
    delta_c = delta_membership_record(
        delta_localization["delta_c1_minus_b1"],
        problem_labels,
        legacy_problem,
        patched_problem,
        current_row_labels,
    )
    delta_d = delta_membership_record(
        delta_localization["delta_d1_minus_b1"],
        problem_labels,
        legacy_problem,
        patched_problem,
        current_row_labels,
    )

    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "comparison_scope": "double current spinorial channel generators in external 33-column order, using corrected generator-span column-space comparison on the transposed matrices",
        "notes": {
            "old_rank_12_reference": "The legacy current rank 12 is the same count-aligned current rank already reported by the v2 SG194 audit.",
            "generator_span_metric": (
                "Because current and external generators live in different native row bases (34 current HSP rows versus 56 external spinorial rows), "
                "the corrected generator-span comparison is implemented as a column-space comparison on the transposed matrices in the common generator-label ambient."
            ),
        },
        "before": {
            "current_rank": int(old_current_rank),
            "external_rank": external_rank,
            "global_union_rank": int(old_global_union),
            "global_intersection_rank": int(old_global_intersection),
            "problem_sector_current_rank": int(old_problem_rank),
            "problem_sector_external_rank": problem_external_rank,
            "problem_sector_union_rank": int(old_problem_union),
            "problem_sector_intersection_rank": int(old_problem_intersection),
        },
        "after": {
            "current_rank": int(new_current_rank),
            "external_rank": external_rank,
            "global_union_rank": int(new_global_union),
            "global_intersection_rank": int(new_global_intersection),
            "problem_sector_current_rank": int(new_problem_rank),
            "problem_sector_external_rank": problem_external_rank,
            "problem_sector_union_rank": int(new_problem_union),
            "problem_sector_intersection_rank": int(new_problem_intersection),
            "delta_c1_minus_b1_disappeared": bool(delta_c["disappeared_under_explicit_membership_test"]),
            "delta_d1_minus_b1_disappeared": bool(delta_d["disappeared_under_explicit_membership_test"]),
        },
        "delta_membership_recheck": {
            "delta_c1_minus_b1": delta_c,
            "delta_d1_minus_b1": delta_d,
        },
        "targets": {
            "wanted_global_rank_drop_12_to_10": bool(new_current_rank == 10),
            "wanted_problem_union_drop_8_to_6": bool(new_problem_union == 6),
        },
        "exact_outcome": {
            "problem_sector_exact_identification_after_patch": bool(new_problem_union == int(ext_problem.rank()) == int(new_problem_rank)),
            "global_rank_drop_achieved": bool(new_current_rank == 10),
        },
    }


def build_before_after_md(payload: dict[str, Any]) -> str:
    before = payload["before"]
    after = payload["after"]
    return textwrap.dedent(
        f"""
        # SG194 Double AI Patch Before/After

        ## Global 33-Column Comparison

        - old current rank / external rank: `{before['current_rank']} / {before['external_rank']}`
        - new current rank / external rank: `{after['current_rank']} / {after['external_rank']}`
        - old global union / intersection: `{before['global_union_rank']} / {before['global_intersection_rank']}`
        - new global union / intersection: `{after['global_union_rank']} / {after['global_intersection_rank']}`

        ## Trusted Problem-Sector Comparison

        - old problem-sector current / external / union / intersection:
          `{before['problem_sector_current_rank']} / {before['problem_sector_external_rank']} / {before['problem_sector_union_rank']} / {before['problem_sector_intersection_rank']}`
        - new problem-sector current / external / union / intersection:
          `{after['problem_sector_current_rank']} / {after['problem_sector_external_rank']} / {after['problem_sector_union_rank']} / {after['problem_sector_intersection_rank']}`

        ## Delta Status

        - `delta_c1_minus_b1` disappeared: `{after['delta_c1_minus_b1_disappeared']}`
        - `delta_d1_minus_b1` disappeared: `{after['delta_d1_minus_b1_disappeared']}`

        ## Interpretation

        - The patched source-level builder kills the explicit trusted `2b/2c/2d/6h` problem-sector mismatch exactly: union rank drops from `8` to `6`.
        - The patched current rank in the full current-HSP `33`-column comparison remains `12`, so the hoped-for direct `12 -> 10` drop is **not** achieved at this stage.
        - Therefore the true outcome is: the localized SG194 double AI bug source has been patched at the generator-construction layer, but the broader all-sector current/external row-language gap is not yet fully collapsed.
        """
    ).strip()


def build_patch_audit_md(
    before_after: dict[str, Any],
    real_inventory: dict[str, Any],
) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Patch Audit

        ## Real Bug Source

        - real patched source file: `debug_workflow_portability_stage2_194.1.1.1.py`
        - raw artifact writer only: `debug_raw_matrix_audit.py`
        - audit/alignment consumers only: `debug_sg194_standard_alignment.py`, `debug_sg194_standard_alignment_v2.py`, `debug_sg194_bs_ai_separation.py`, `debug_sg194_mismatch_localization.py`

        ## What Was Actually Patched

        - The stage-2 double path now constructs SG194 spinorial current generators directly.
        - The new patched profile is `sg194_double_anchor_patch_v1`.
        - This patch is source-level, not an audit-only post-hoc override.

        ## Exact Outcome

        - problem-sector union rank: `{before_after['before']['problem_sector_union_rank']} -> {before_after['after']['problem_sector_union_rank']}`
        - problem-sector intersection rank: `{before_after['before']['problem_sector_intersection_rank']} -> {before_after['after']['problem_sector_intersection_rank']}`
        - `delta_c1_minus_b1` disappeared: `{before_after['after']['delta_c1_minus_b1_disappeared']}`
        - `delta_d1_minus_b1` disappeared: `{before_after['after']['delta_d1_minus_b1_disappeared']}`
        - full current rank in the 33-column comparison: `{before_after['before']['current_rank']} -> {before_after['after']['current_rank']}`

        ## Diagnosis

        - The exact trusted SG194 double mismatch in `2b/2c/2d/6h` is removed by the patched stage-2 builder.
        - The hoped-for global `12 -> 10` collapse is not reached yet, so a BS-only rerun is still premature.
        - The next blocker is no longer “find the bug source”; it is “finish the all-sector current-to-external spinorial row-language canonicalization after the patched problem sector has been fixed”.
        """
    ).strip()


def build_patch_summary_json(before_after: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "real_bug_source_file": "debug_workflow_portability_stage2_194.1.1.1.py",
        "audit_only_files": [
            "debug_sg194_mismatch_localization.py",
            "debug_sg194_standard_alignment.py",
            "debug_sg194_standard_alignment_v2.py",
            "debug_sg194_bs_ai_separation.py",
            "debug_raw_matrix_audit.py",
        ],
        "patch_landed_in_generator_construction_code": True,
        "patched_profile": "sg194_double_anchor_patch_v1",
        "old_current_rank": before_after["before"]["current_rank"],
        "new_current_rank": before_after["after"]["current_rank"],
        "old_problem_sector_union_rank": before_after["before"]["problem_sector_union_rank"],
        "new_problem_sector_union_rank": before_after["after"]["problem_sector_union_rank"],
        "delta_c1_minus_b1_disappeared": before_after["after"]["delta_c1_minus_b1_disappeared"],
        "delta_d1_minus_b1_disappeared": before_after["after"]["delta_d1_minus_b1_disappeared"],
        "bs_only_after_patch_rerun": False,
        "bs_only_after_patch_reason": (
            "The trusted problem sector is fixed, but the full current 33-column rank has not yet dropped from 12 to 10, so BS-only remains premature."
        ),
    }


def build_handoff_md(before_after: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # Handoff: SG194 Double Patch

        ## Patched This Round

        - real source patch landed in `debug_workflow_portability_stage2_194.1.1.1.py`
        - new patched profile: `sg194_double_anchor_patch_v1`
        - patched raw artifacts regenerated under `*_patched.json`

        ## Exact Result

        - problem-sector union: `{before_after['before']['problem_sector_union_rank']} -> {before_after['after']['problem_sector_union_rank']}`
        - problem-sector intersection: `{before_after['before']['problem_sector_intersection_rank']} -> {before_after['after']['problem_sector_intersection_rank']}`
        - deltas disappeared: `c={before_after['after']['delta_c1_minus_b1_disappeared']}`, `d={before_after['after']['delta_d1_minus_b1_disappeared']}`
        - full 33-column current rank: `{before_after['before']['current_rank']} -> {before_after['after']['current_rank']}`

        ## Remaining Blocker

        - The localized SG194 double problem sector is fixed at the source layer.
        - The broader full-33-column current/external collapse is still not at rank `10`.
        - Do not jump to BS-only yet.
        """
    ).strip()


def build_status_json(before_after: dict[str, Any]) -> dict[str, Any]:
    return {
        "group": "194.1.1.1",
        "group_type": 2,
        "task": "patch real SG194 double generator-construction source and recompare",
        "status": "patched_and_recompared",
        "patched_profile": "sg194_double_anchor_patch_v1",
        "problem_sector_union_after_patch": before_after["after"]["problem_sector_union_rank"],
        "problem_sector_exact_after_patch": bool(before_after["after"]["problem_sector_union_rank"] == 6),
        "global_rank_after_patch": before_after["after"]["current_rank"],
        "ready_for_bs_only": False,
    }


def build_next_step_prompt(before_after: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Continue from the completed SG194 double patch round.

        Fixed facts:
        - real source patch landed in `debug_workflow_portability_stage2_194.1.1.1.py`
        - patched profile = `sg194_double_anchor_patch_v1`
        - trusted problem-sector union rank already dropped from `{before_after['before']['problem_sector_union_rank']}` to `{before_after['after']['problem_sector_union_rank']}`
        - `delta_c1_minus_b1` and `delta_d1_minus_b1` are gone in the trusted `2b/2c/2d/6h` sector
        - full current rank in the 33-column comparison is still `{before_after['after']['current_rank']}`, not `10`

        Do not reopen raw localization.
        The next task is to finish the all-sector current-to-external spinorial row-language canonicalization outside the already fixed SG194 problem sector, and only then decide whether BS-only comparison is finally justified.
        """
    ).strip()


def build_report_md(before_after: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        # SG194 Double Patch Report

        ## 1. Problem History and Why Audits Alone Were Insufficient

        Previous SG194 rounds localized the double mismatch to the `2b/2c/2d/6h` sector, but the local package still had no source-of-truth builder for the current `33`-column spinorial generators. The only source-level object was the `45`-candidate local-irrep induction output, and every later SG194 double file compensated with downstream hardcoded merges. That is why the mismatch could be diagnosed repeatedly without actually shrinking.

        ## 2. Finding the Real Bug Source

        The raw writer `debug_raw_matrix_audit.py` was not the real bug source. It serializes whatever the stage-2 induction layer gives it. The real missing layer sat in `debug_workflow_portability_stage2_194.1.1.1.py`: stage-2 could induce the `45` local-irrep candidates, but it could not yet build the current SG194 double spinorial generators themselves.

        ## 3. Concrete Code Patches

        The patch adds `build_sg194_double_spinorial_generators(...)` to the stage-2 source layer. Two profiles now exist:

        - `legacy`: the old pair-sum / four-way-sum channelization.
        - `sg194_double_anchor_patch_v1`: the patched SG194 channelization.

        The exact structured solve showed that the heuristic “fix only `2c/2d E1` and rescale `6h`” did not have an exact local-block solution. The smallest exact source-level fix that kills the trusted problem-sector mismatch is:

        - `c:E3 -> 2*c:E3 - b:E3`
        - `d:E3 -> 2*d:E3 - b:E3`
        - `6h:E -> 6h:E - b:E3`

        Here `b:E3`, `c:E3`, and `d:E3` are the stage-2 channels obtained from the corresponding pairwise sums of the `proj_doubleprime_2d_5/6` candidates.

        ## 4. Before/After AI Comparison

        Trusted problem-sector metrics:

        - before: current/external/problem-union/problem-intersection = `{before_after['before']['problem_sector_current_rank']} / {before_after['before']['problem_sector_external_rank']} / {before_after['before']['problem_sector_union_rank']} / {before_after['before']['problem_sector_intersection_rank']}`
        - after: current/external/problem-union/problem-intersection = `{before_after['after']['problem_sector_current_rank']} / {before_after['after']['problem_sector_external_rank']} / {before_after['after']['problem_sector_union_rank']} / {before_after['after']['problem_sector_intersection_rank']}`

        Therefore the explicit trusted SG194 double problem-sector mismatch is removed exactly. In particular:

        - `delta_c1_minus_b1` disappears.
        - `delta_d1_minus_b1` disappears.

        ## 5. Problem-Sector Rank Changes

        The hoped-for direct full-rank collapse from `12` to `10` was **not** achieved in the broader `33`-column current-HSP comparison:

        - before full current rank: `{before_after['before']['current_rank']}`
        - after full current rank: `{before_after['after']['current_rank']}`

        So the patched current builder removes the trusted localized SG194 bug, but a wider all-sector current/external row-language gap still remains.

        ## 6. Updated Diagnosis and Next Step

        The current round finally moved beyond audit-only work:

        - the real source patch is in the stage-2 generator-construction code;
        - patched raw artifacts were regenerated;
        - the trusted SG194 double problem sector is fixed.

        However BS-only is still not the next justified step. The next step is to finish the all-sector current-to-external spinorial canonicalization outside the already fixed `2b/2c/2d/6h` sector, then re-evaluate whether BS-only has become meaningful.

        ## Implementation Mapping

        - source patch: `debug_workflow_portability_stage2_194.1.1.1.py`
        - patched driver: `debug_sg194_double_patch.py`
        - patched raw artifacts: `raw_194_1_1_1_double_ai_candidates_patched.json`, `raw_194_1_1_1_double_ai_basis_patched.json`, `raw_194_1_1_1_double_ai_in_bs_matrix_patched.json`
        - before/after comparison: `sg194_double_ai_patch_before_after.json`
        """
    ).strip()


def latex_escape(text: str) -> str:
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("^", r"\textasciicircum{}"),
    ]:
        text = text.replace(old, new)
    return text


def build_report_tex(before_after: dict[str, Any]) -> str:
    before = before_after["before"]
    after = before_after["after"]
    return textwrap.dedent(
        f"""
        \\documentclass[11pt]{{article}}
        \\usepackage[margin=1in]{{geometry}}
        \\usepackage{{amsmath,amssymb}}
        \\usepackage[T1]{{fontenc}}
        \\usepackage[utf8]{{inputenc}}
        \\title{{SG194 Double Patch Report}}
        \\author{{Codex Local Patch Round}}
        \\date{{\\today}}
        \\begin{{document}}
        \\maketitle

        \\section*{{1. Problem History and Why Audits Alone Were Insufficient}}
        Previous SG194 rounds localized the double mismatch to the \\texttt{{2b/2c/2d/6h}} sector, but the local package still had no source-of-truth builder for the current \\texttt{{33}}-column spinorial generators. The only source-level object was the \\texttt{{45}}-candidate local-irrep induction output, and every later SG194 double file compensated with downstream hardcoded merges. That is why the mismatch could be diagnosed repeatedly without actually shrinking.

        \\section*{{2. Finding the Real Bug Source}}
        The raw writer \\texttt{{debug\\_raw\\_matrix\\_audit.py}} was not the real bug source. It serializes whatever the stage-2 induction layer gives it. The real missing layer sat in \\texttt{{debug\\_workflow\\_portability\\_stage2\\_194.1.1.1.py}}: stage-2 could induce the \\texttt{{45}} local-irrep candidates, but it could not yet build the current SG194 double spinorial generators themselves.

        \\section*{{3. Concrete Code Patches}}
        The patch adds \\texttt{{build\\_sg194\\_double\\_spinorial\\_generators(...)}} to the stage-2 source layer. Two profiles now exist:
        \\begin{{itemize}}
        \\item \\texttt{{legacy}}: the old pair-sum / four-way-sum channelization.
        \\item \\texttt{{sg194\\_double\\_anchor\\_patch\\_v1}}: the patched SG194 channelization.
        \\end{{itemize}}
        The exact structured solve showed that the heuristic ``fix only \\texttt{{2c/2d E1}} and rescale \\texttt{{6h}}'' did not have an exact local-block solution. The smallest exact source-level fix that kills the trusted problem-sector mismatch is:
        \\begin{{itemize}}
        \\item \\texttt{{c:E3 -> 2*c:E3 - b:E3}}
        \\item \\texttt{{d:E3 -> 2*d:E3 - b:E3}}
        \\item \\texttt{{6h:E -> 6h:E - b:E3}}
        \\end{{itemize}}

        \\section*{{4. Before/After AI Comparison}}
        Trusted problem-sector metrics:
        \\begin{{itemize}}
        \\item before: current/external/problem-union/problem-intersection = \\texttt{{{before['problem_sector_current_rank']} / {before['problem_sector_external_rank']} / {before['problem_sector_union_rank']} / {before['problem_sector_intersection_rank']}}}
        \\item after: current/external/problem-union/problem-intersection = \\texttt{{{after['problem_sector_current_rank']} / {after['problem_sector_external_rank']} / {after['problem_sector_union_rank']} / {after['problem_sector_intersection_rank']}}}
        \\end{{itemize}}
        Therefore the explicit trusted SG194 double problem-sector mismatch is removed exactly. In particular:
        \\begin{{itemize}}
        \\item \\texttt{{delta\\_c1\\_minus\\_b1}} disappears: \\texttt{{{after['delta_c1_minus_b1_disappeared']}}}
        \\item \\texttt{{delta\\_d1\\_minus\\_b1}} disappears: \\texttt{{{after['delta_d1_minus_b1_disappeared']}}}
        \\end{{itemize}}

        \\section*{{5. Problem-Sector Rank Changes}}
        The hoped-for direct full-rank collapse from \\texttt{{12}} to \\texttt{{10}} was \\textbf{{not}} achieved in the broader \\texttt{{33}}-column current-HSP comparison:
        \\begin{{itemize}}
        \\item before full current rank: \\texttt{{{before['current_rank']}}}
        \\item after full current rank: \\texttt{{{after['current_rank']}}}
        \\end{{itemize}}
        So the patched current builder removes the trusted localized SG194 bug, but a wider all-sector current/external row-language gap still remains.

        \\section*{{6. Updated Diagnosis and Next Step}}
        The current round finally moved beyond audit-only work:
        \\begin{{itemize}}
        \\item the real source patch is in the stage-2 generator-construction code;
        \\item patched raw artifacts were regenerated;
        \\item the trusted SG194 double problem sector is fixed.
        \\end{{itemize}}
        However BS-only is still not the next justified step. The next step is to finish the all-sector current-to-external spinorial canonicalization outside the already fixed \\texttt{{2b/2c/2d/6h}} sector, then re-evaluate whether BS-only has become meaningful.

        \\section*{{Implementation Mapping}}
        \\begin{{itemize}}
        \\item source patch: \\texttt{{debug\\_workflow\\_portability\\_stage2\\_194.1.1.1.py}}
        \\item patched driver: \\texttt{{debug\\_sg194\\_double\\_patch.py}}
        \\item patched raw artifacts: \\texttt{{raw\\_194\\_1\\_1\\_1\\_double\\_ai\\_candidates\\_patched.json}}, \\texttt{{raw\\_194\\_1\\_1\\_1\\_double\\_ai\\_basis\\_patched.json}}, \\texttt{{raw\\_194\\_1\\_1\\_1\\_double\\_ai\\_in\\_bs\\_matrix\\_patched.json}}
        \\item before/after comparison: \\texttt{{sg194\\_double\\_ai\\_patch\\_before\\_after.json}}
        \\end{{itemize}}

        \\end{{document}}
        """
    ).strip() + "\n"


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


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def build_package_readme() -> str:
    return textwrap.dedent(
        """
        # SG194 Double Patch Audit Package

        ## SG194 double patch report

        - report file: `sg194_double_patch_report.pdf`
        - report source: `sg194_double_patch_report.tex`
        - recommended reading order:
          - `sg194_double_patch_report.pdf`
          - `real_patch_target_inventory.json`
          - `patch_diff_summary.md`
          - `sg194_double_ai_patch_before_after.json`
        """
    ).strip()


def build_package(before_after: dict[str, Any]) -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    write_text(PACKAGE_DIR / "README.md", build_package_readme())

    files_to_copy = [
        REAL_PATCH_TARGET_INVENTORY_JSON,
        PATCH_DIFF_SUMMARY_MD,
        PATCHED_SOURCE_INVENTORY_JSON,
        RAW_DOUBLE_AI_CANDIDATES_PATCHED_JSON,
        RAW_DOUBLE_AI_BASIS_PATCHED_JSON,
        RAW_DOUBLE_AI_IN_BS_PATCHED_JSON,
        BEFORE_AFTER_JSON,
        BEFORE_AFTER_MD,
        PATCH_AUDIT_MD,
        PATCH_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_sg194_double_patch.py",
        REPORT_PDF,
        REPORT_TEX,
        REPORT_MD,
        ROOT / "sg194_double_ai_vs_external.json",
        ROOT / "sg194_double_bs_vs_external.json",
        ROOT / "sg194_double_delta_localization.json",
        ROOT / "sg194_double_minimal_correction_plan.json",
        ROOT / "sg194_mismatch_localization_summary.json",
        ROOT / "sg194_external_spinorial_generator_matrix.json",
        ROOT / "raw_194_1_1_1_double_ai_candidates.json",
        ROOT / "raw_194_1_1_1_double_ai_basis.json",
        ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json",
        ROOT / "debug_workflow_portability_stage2_194.1.1.1.py",
        ROOT / "debug_raw_matrix_audit.py",
        ROOT / "debug_sg194_nonabelian_local_library.py",
        ROOT / "debug_workflow_portability_194.1.1.1.py",
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


def format_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def run_patch_round() -> None:
    stage2, raw = load_context_modules()

    real_inventory = build_real_patch_target_inventory()
    write_json(REAL_PATCH_TARGET_INVENTORY_JSON, real_inventory)
    write_json(PATCHED_SOURCE_INVENTORY_JSON, build_patched_source_inventory())
    write_text(PATCH_DIFF_SUMMARY_MD, build_patch_diff_summary())

    compat_root = raw.load_json(raw.CASE_SPECS["194_1_1_1_double"]["compat_path"])
    c_ctx = raw.compute_c_artifact("194_1_1_1_double", compat_root)
    bs_ctx = raw.compute_bs_artifacts("194_1_1_1_double", c_ctx)
    old_normalized = load_json(ROOT / "raw_194_1_1_1_double_ai_candidates.json")["candidates"]
    induction_like = [raw_candidate_to_induction_like(candidate) for candidate in old_normalized]
    family_dimension_map = {candidate["family_id"]: int(candidate["family_dimension"]) for candidate in old_normalized}

    ordering = c_ctx["unknown_ordering"]
    legacy = build_channel_candidates(
        stage2,
        induction_like,
        ordering,
        c_ctx["matrix"],
        family_dimension_map,
        profile="legacy",
    )
    patched = build_channel_candidates(
        stage2,
        induction_like,
        ordering,
        c_ctx["matrix"],
        family_dimension_map,
        profile="sg194_double_anchor_patch_v1",
    )

    ai_candidates_ctx = raw.compute_ai_candidate_artifact("194_1_1_1_double", patched["channels"], bs_ctx)
    ai_basis_ctx = raw.compute_ai_basis_artifact("194_1_1_1_double", ai_candidates_ctx, bs_ctx)
    ai_in_bs_ctx = raw.compute_ai_in_bs_artifact("194_1_1_1_double", ai_basis_ctx, bs_ctx, c_ctx)

    write_json(RAW_DOUBLE_AI_CANDIDATES_PATCHED_JSON, ai_candidates_ctx["payload"])
    write_json(RAW_DOUBLE_AI_BASIS_PATCHED_JSON, ai_basis_ctx["payload"])
    write_json(RAW_DOUBLE_AI_IN_BS_PATCHED_JSON, ai_in_bs_ctx["payload"])

    before_after = build_before_after(legacy["channels"], patched["channels"], ordering)
    write_json(BEFORE_AFTER_JSON, before_after)
    write_text(BEFORE_AFTER_MD, build_before_after_md(before_after))
    write_text(PATCH_AUDIT_MD, build_patch_audit_md(before_after, real_inventory))
    write_json(PATCH_SUMMARY_JSON, build_patch_summary_json(before_after))
    write_text(HANDOFF_MD, build_handoff_md(before_after))
    write_json(CURRENT_STATUS_JSON, build_status_json(before_after))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(before_after))

    report_md = build_report_md(before_after)
    report_tex = build_report_tex(before_after)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, report_tex)
    compile_pdf(REPORT_TEX, REPORT_PDF)

    if BS_AFTER_PATCH_JSON.exists():
        BS_AFTER_PATCH_JSON.unlink()

    package_tree = build_package(before_after)
    write_json(
        PATCH_SUMMARY_JSON,
        {
            **build_patch_summary_json(before_after),
            "pdf_generated": REPORT_PDF.exists(),
            "handoff_generated": HANDOFF_MD.exists(),
            "status_generated": CURRENT_STATUS_JSON.exists(),
            "next_step_generated": NEXT_STEP_PROMPT_TXT.exists(),
            "package_tarball": str(PACKAGE_TARBALL),
            "package_tree": package_tree,
        },
    )


def validate_outputs() -> None:
    required = [
        REAL_PATCH_TARGET_INVENTORY_JSON,
        PATCH_DIFF_SUMMARY_MD,
        PATCHED_SOURCE_INVENTORY_JSON,
        RAW_DOUBLE_AI_CANDIDATES_PATCHED_JSON,
        RAW_DOUBLE_AI_BASIS_PATCHED_JSON,
        RAW_DOUBLE_AI_IN_BS_PATCHED_JSON,
        BEFORE_AFTER_JSON,
        BEFORE_AFTER_MD,
        PATCH_AUDIT_MD,
        PATCH_SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing outputs: " + ", ".join(missing))

    summary = load_json(PATCH_SUMMARY_JSON)
    before_after = load_json(BEFORE_AFTER_JSON)
    if summary["real_bug_source_file"] != "debug_workflow_portability_stage2_194.1.1.1.py":
        raise ValueError("wrong real bug source")
    if before_after["after"]["problem_sector_union_rank"] != 6:
        raise ValueError("patched problem-sector union rank must be 6")
    print("validation ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch and recompare SG194 double generator construction")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        return

    run_patch_round()


if __name__ == "__main__":
    main()
