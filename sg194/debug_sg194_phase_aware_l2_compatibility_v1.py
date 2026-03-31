#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent
TARGET_GROUP = "194.1.1.1"
PROFILE = "phase_aware_l2_projective_v1"

PHASE_AWARE_JSON = ROOT / "sg194_phase_aware_l2_compatibility_v1.json"
PHASE_AWARE_MD = ROOT / "sg194_phase_aware_l2_compatibility_v1.md"
FIX_ATTEMPT_JSON = ROOT / "sg194_upstream_raw_bs_fix_attempt_v1.json"
FIX_ATTEMPT_MD = ROOT / "sg194_upstream_raw_bs_fix_attempt_v1.md"
RAW_GAP_AUDIT_JSON = ROOT / "sg194_upstream_raw_bs_gap_audit_v1.json"
PHASE_AUDIT_JSON = ROOT / "sg194_phase_and_subduction_audit_v1.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def load_stage2_module():
    path = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
    spec = importlib.util.spec_from_file_location("sg194_stage2_phase_aware_fix", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def line_block(runtime: dict[str, Any], line_id: str) -> dict[str, Any]:
    return next(block for block in runtime["line_blocks"] if block["line_id"] == line_id)


def vector_from_support(ordering: list[str], support: list[dict[str, Any]]) -> list[int]:
    index = {label: idx for idx, label in enumerate(ordering)}
    vector = [0] * len(ordering)
    for item in support:
        vector[index[item["label"]]] = int(item["coeff"])
    return vector


def generator_residuals(
    ordering: list[str],
    matrix_rows: list[list[int]],
    generators: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matrix = sp.Matrix(matrix_rows)
    residuals = []
    for generator in generators:
        vector = sp.Matrix(vector_from_support(ordering, generator["support"]))
        residual = list(matrix * vector)
        nonzero = [
            {"row_index": idx, "residual": int(value)}
            for idx, value in enumerate(residual)
            if int(value) != 0
        ]
        residuals.append(
            {
                "generator_id": generator["generator_id"],
                "nonzero_residual_rows": nonzero,
                "survives_refined_kernel": len(nonzero) == 0,
            }
        )
    return residuals


def candidate_violation_summary(
    candidates: list[dict[str, Any]],
    matrix_rows: list[list[int]],
    row_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    matrix = sp.Matrix(matrix_rows)
    failing = []
    for candidate in candidates:
        residual = list(matrix * sp.Matrix(candidate["unknown_vector"]))
        nonzero = [
            {
                "row_index": idx,
                "residual": int(value),
                "basis_id": row_meta[idx].get("basis_id"),
                "source_type": row_meta[idx].get("source_type"),
                "line_id": row_meta[idx].get("line_id"),
            }
            for idx, value in enumerate(residual)
            if int(value) != 0
        ]
        if nonzero:
            failing.append(
                {
                    "generator_id": candidate["generator_id"],
                    "local_object_label": candidate.get("local_object_label"),
                    "failure_count": len(nonzero),
                    "nonzero_residual_rows": nonzero[:5],
                }
            )
    return {
        "all_candidates_compatibility_zero": len(failing) == 0,
        "failing_candidate_count": len(failing),
        "failing_candidate_examples": failing[:10],
    }


def build_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    stage2 = load_stage2_module()
    helper = stage2.load_helper_module()
    helper_payload = helper.generate_outputs()
    port = stage2.load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(TARGET_GROUP)

    current_single = stage2.build_single_runtime(port, module, ssg_dict)
    current_double = stage2.build_double_runtime(port, module, ssg_dict, current_single["kgeom"])
    refined_single = stage2.build_single_runtime(port, module, ssg_dict, line_phase_profile=PROFILE)
    refined_double = stage2.build_double_runtime(
        port,
        module,
        ssg_dict,
        current_single["kgeom"],
        line_phase_profile=PROFILE,
    )

    single_induction = stage2.induce_objects(
        port,
        current_single,
        helper_payload["family_single_local_irreps"],
        "single_local_irrep_library",
    )
    double_induction = stage2.induce_objects(
        port,
        current_double,
        helper_payload["family_double_local_irreps"],
        "double_projective_local_irrep_library",
    )

    raw_gap = load_json(RAW_GAP_AUDIT_JSON)
    phase_audit = load_json(PHASE_AUDIT_JSON)
    current_l2 = line_block(current_single, "L2")
    refined_l2 = line_block(refined_single, "L2")

    refined_single_residuals = generator_residuals(
        refined_single["with_planes"]["global_unknown_ordering"],
        refined_single["with_planes"]["global_matrix"],
        raw_gap["common_free_generators"],
    )
    refined_double_residuals = generator_residuals(
        refined_double["with_planes"]["global_unknown_ordering"],
        refined_double["with_planes"]["global_matrix"],
        raw_gap["common_free_generators"],
    )
    surviving_after = sum(1 for item in refined_single_residuals if item["survives_refined_kernel"])

    single_candidate_check = candidate_violation_summary(
        single_induction["candidates"],
        refined_single["with_planes"]["global_matrix"],
        refined_single["with_planes"]["global_matrix_rows"],
    )
    double_candidate_check = candidate_violation_summary(
        double_induction["candidates"],
        refined_double["with_planes"]["global_matrix"],
        refined_double["with_planes"]["global_matrix_rows"],
    )

    inconsistent_single = [
        report["rep_id"]
        for endpoint in phase_audit["subduction_tests"]["single_L2_using_linear_character"]["endpoint_reports"]
        for report in endpoint["rep_reports"]
        if report["status"] == "inconsistent"
    ]
    selected_endpoint = refined_l2["phase_aware_refinement"]["selected_endpoint_id"]
    selected_classes = refined_l2["phase_aware_refinement"]["restriction_classes_by_endpoint"].get(selected_endpoint, [])
    selected_class_maps = []
    decomposition_lookup = {
        rep["rep_id"]: rep["decomposition_on_line_basis"]
        for rep in current_l2["endpoint_decompositions"][selected_endpoint]
    }
    for entry in selected_classes:
        selected_class_maps.append(
            {
                "rep_ids": entry["rep_ids"],
                "class_size": entry["class_size"],
                "restricted_vector": entry["restricted_vector"],
                "representative_raw_decomposition_on_line_basis": decomposition_lookup[entry["rep_ids"][0]],
            }
        )

    phase_payload = {
        "target_group": TARGET_GROUP,
        "current_builder_object": {
            "line_id": current_l2["line_id"],
            "compatibility_input": "phase_stripped_character",
            "line_basis_labels": current_l2["line_basis_labels"],
            "equation_count": len(current_l2["line_basis_labels"]),
            "equations": current_l2["equations"],
        },
        "native_linear_character_inconsistency": {
            "current_individually_inconsistent_rep_ids": inconsistent_single,
            "note": (
                "The current direct linear-character solve is inconsistent on the duplicated P3 channels and on P4_R3. "
                "The v1 prototype therefore stops solving per raw irrep and first glues duplicated native restrictions into endpoint classes."
            ),
        },
        "phase_aware_l2_solver_object": {
            "profile": PROFILE,
            "selected_endpoint_id": selected_endpoint,
            "selected_endpoint_class_maps": selected_class_maps,
            "restriction_classes_by_endpoint": refined_l2["phase_aware_refinement"]["restriction_classes_by_endpoint"],
            "refinement_equation_count": len(refined_l2["phase_aware_refinement"]["refinement_equations"]),
            "refinement_equations": refined_l2["phase_aware_refinement"]["refinement_equations"],
            "solver_interpretation": (
                "Use native linear-character restrictions on L2, group identical duplicated endpoint channels into projective classes, "
                "and add equality rows inside the selected duplicated endpoint before the legacy line-basis matching is applied."
            ),
        },
        "local_validation": {
            "current_raw_rank_bs_single": current_single["bs_analysis"]["nullity"],
            "refined_raw_rank_bs_single": refined_single["bs_analysis"]["nullity"],
            "current_raw_rank_bs_double": current_double["bs_analysis"]["nullity"],
            "refined_raw_rank_bs_double": refined_double["bs_analysis"]["nullity"],
            "refined_single_common_free_generator_residuals": refined_single_residuals,
            "refined_double_common_free_generator_residuals": refined_double_residuals,
            "surviving_common_free_generators_after_refinement": surviving_after,
        },
    }

    fix_attempt = {
        "target_group": TARGET_GROUP,
        "profile": PROFILE,
        "current_raw_bs_rank_single": current_single["bs_analysis"]["nullity"],
        "current_raw_bs_rank_double": current_double["bs_analysis"]["nullity"],
        "refined_raw_bs_rank_single": refined_single["bs_analysis"]["nullity"],
        "refined_raw_bs_rank_double": refined_double["bs_analysis"]["nullity"],
        "current_raw_quotient_group_single": load_json(ROOT / "group_194_1_1_1_single_ai_completion_summary.json")["raw_internal_quotient_group"],
        "current_raw_quotient_group_double": load_json(ROOT / "group_194_1_1_1_double_ai_completion_summary.json")["raw_internal_quotient_group"],
        "surviving_common_free_generators_before": raw_gap["common_free_generator_count"],
        "surviving_common_free_generators_after": surviving_after,
        "single_current_ai_against_refined_kernel": single_candidate_check,
        "double_current_ai_against_refined_kernel": double_candidate_check,
        "raw_quotient_status_after_refined_l2": (
            "blocked_by_phase_aware_ai_mapping"
            if not single_candidate_check["all_candidates_compatibility_zero"] or not double_candidate_check["all_candidates_compatibility_zero"]
            else "ready_for_recompute"
        ),
        "blocker": (
            "The phase-aware L2 refinement kills the BS-side Z^3 and drops raw BS from 16 to 13, "
            "but the current AI induction still emits raw point-row multiplicities that violate the new P3 class-glue rows. "
            "A matching phase-aware point-row translation / unknown-vector builder is still missing."
        ),
        "next_missing_object": "phase_aware_point_row_translation_for_P3_duplicate_L2_classes",
    }
    return phase_payload, fix_attempt


def build_phase_md(payload: dict[str, Any]) -> str:
    solver = payload["phase_aware_l2_solver_object"]
    validation = payload["local_validation"]
    lines = [
        "# SG194 Phase-Aware L2 Compatibility v1",
        "",
        "## Current Builder Object",
        "",
        f"- line id: `{payload['current_builder_object']['line_id']}`",
        f"- compatibility input: `{payload['current_builder_object']['compatibility_input']}`",
        f"- line-basis equation count: `{payload['current_builder_object']['equation_count']}`",
        "",
        "## Native Linear-Character Problem",
        "",
        f"- individually inconsistent reps on direct linear-character subduction: `{payload['native_linear_character_inconsistency']['current_individually_inconsistent_rep_ids']}`",
        f"- note: {payload['native_linear_character_inconsistency']['note']}",
        "",
        "## Phase-Aware v1 Solver",
        "",
        f"- profile: `{solver['profile']}`",
        f"- selected duplicated endpoint: `{solver['selected_endpoint_id']}`",
        f"- refinement equation count: `{solver['refinement_equation_count']}`",
        f"- solver interpretation: {solver['solver_interpretation']}",
        "",
        "### Selected Endpoint Classes",
        "",
    ]
    for entry in solver["selected_endpoint_class_maps"]:
        lines.append(
            f"- `{entry['rep_ids']}` -> raw line decomposition `{entry['representative_raw_decomposition_on_line_basis']}`"
        )
    lines.extend(
        [
            "",
            "## Local Validation",
            "",
            f"- current single/double raw rank(BS): `{validation['current_raw_rank_bs_single']}` / `{validation['current_raw_rank_bs_double']}`",
            f"- refined single/double raw rank(BS): `{validation['refined_raw_rank_bs_single']}` / `{validation['refined_raw_rank_bs_double']}`",
            f"- surviving common free generators after refinement: `{validation['surviving_common_free_generators_after_refinement']}`",
        ]
    )
    return "\n".join(lines)


def build_fix_attempt_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Upstream Raw BS Fix Attempt v1",
        "",
        "## Result",
        "",
        f"- current raw single/double rank(BS): `{payload['current_raw_bs_rank_single']}` / `{payload['current_raw_bs_rank_double']}`",
        f"- refined raw single/double rank(BS): `{payload['refined_raw_bs_rank_single']}` / `{payload['refined_raw_bs_rank_double']}`",
        f"- surviving common free generators before/after: `{payload['surviving_common_free_generators_before']}` / `{payload['surviving_common_free_generators_after']}`",
        f"- raw quotient status after refined L2: `{payload['raw_quotient_status_after_refined_l2']}`",
        "",
        "## Why the Fix Is Not Yet End-to-End",
        "",
        f"- blocker: {payload['blocker']}",
        f"- next missing object: `{payload['next_missing_object']}`",
        "",
        "## Current AI Compatibility Against The Refined Kernel",
        "",
        f"- single all candidates compatibility zero: `{payload['single_current_ai_against_refined_kernel']['all_candidates_compatibility_zero']}`",
        f"- single failing candidate count: `{payload['single_current_ai_against_refined_kernel']['failing_candidate_count']}`",
        f"- double all candidates compatibility zero: `{payload['double_current_ai_against_refined_kernel']['all_candidates_compatibility_zero']}`",
        f"- double failing candidate count: `{payload['double_current_ai_against_refined_kernel']['failing_candidate_count']}`",
    ]
    return "\n".join(lines)


def validate_outputs() -> None:
    for path in [PHASE_AWARE_JSON, PHASE_AWARE_MD, FIX_ATTEMPT_JSON, FIX_ATTEMPT_MD]:
        if not path.exists():
            raise FileNotFoundError(path)
    phase_payload = load_json(PHASE_AWARE_JSON)
    fix_payload = load_json(FIX_ATTEMPT_JSON)
    if phase_payload["local_validation"]["refined_raw_rank_bs_single"] != 13:
        raise RuntimeError("refined single raw BS rank is not 13")
    if phase_payload["local_validation"]["refined_raw_rank_bs_double"] != 13:
        raise RuntimeError("refined double raw BS rank is not 13")
    if fix_payload["surviving_common_free_generators_after"] != 0:
        raise RuntimeError("common raw free generators still survive the refined L2 kernel")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated phase-aware L2 compatibility prototype outputs")
        return

    phase_payload, fix_attempt = build_payload()
    write_json(PHASE_AWARE_JSON, phase_payload)
    write_text(PHASE_AWARE_MD, build_phase_md(phase_payload))
    write_json(FIX_ATTEMPT_JSON, fix_attempt)
    write_text(FIX_ATTEMPT_MD, build_fix_attempt_md(fix_attempt))
    validate_outputs()
    print(
        f"generated {PROFILE}: refined raw BS {fix_attempt['refined_raw_bs_rank_single']}/"
        f"{fix_attempt['refined_raw_bs_rank_double']}, surviving free generators "
        f"{fix_attempt['surviving_common_free_generators_after']}"
    )


if __name__ == "__main__":
    main()
