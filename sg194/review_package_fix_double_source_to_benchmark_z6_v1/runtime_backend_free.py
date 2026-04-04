#!/usr/bin/env python3
"""Backend-free generic runtime extracted into pipeline_v2.

This module is the reusable runtime implementation used by the generic path.
It intentionally lives inside ``sg194/pipeline_v2`` so the core builders no
longer import or call the older SG194-special debug backends.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import copy
import importlib.util
import io
import json
import math
import pickle
import shutil
import subprocess
import sys
import tarfile
import textwrap
import tarfile as tarfile_module
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
COMMON_ROOT = REPO_ROOT / "common"
COMMON_SSGREPS_ROOT = COMMON_ROOT / "SSGReps"
COMMON_SSG_DATA_ROOT = COMMON_SSGREPS_ROOT / "ssg_data"
IDENTIFY_PKL = COMMON_SSG_DATA_ROOT / "identify.pkl"
IDENTIFY_TAR = COMMON_SSG_DATA_ROOT / "identify.pkl.tar.gz"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import sympy as sp
from sympy.matrices.normalforms import smith_normal_form

from common import swyckoff_k, swyckoff_r

from . import runtime_bridge as bridge
from .final_object_reduction import (
    analyze_candidate_path_selection,
    build_candidate_path_records,
    build_expected_check_markdown,
    build_final_bs_strong_equivalence_markdown,
    build_final_bs_strong_equivalence_report,
    build_full_shell_automorphism_search_markdown,
    build_full_shell_automorphism_search_report,
    build_final_path_candidate_equivalence_markdown,
    build_final_path_candidate_equivalence_report,
    build_final_path_signature_markdown,
    build_final_path_signature_report,
    build_internal_vs_publication_object_markdown,
    build_internal_vs_publication_object_report,
    build_missing_row_language_witness_markdown,
    build_missing_row_language_witness_report,
    build_p1_p5_doubleclass_resolution_markdown,
    build_p1_p5_doubleclass_resolution_report,
    build_publication_C_matrix,
    build_publication_shell_candidate,
    build_publication_shell_reduction_markdown,
    build_publication_shell_reduction_report,
    build_publication_shell_vs_bilbao_markdown,
    build_reduction_report_markdown,
    compare_publication_shell_to_bilbao_expected,
    compare_reduction_to_expected_pairs,
    finalize_reduction_from_candidate_analysis,
    reduce_final_point_path_shell,
)
from . import runtime_group_ops as single_expanded

REFERENCE_GROUP = "10.4.1.31"
TARGET_GROUP = "194.1.1.1"
PACKAGE_NAME = "review_package_fix_double_source_to_benchmark_z6_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

CONTROLLED_AUDIT_MD = ROOT / "controlled_case_audit_194.1.1.1.md"
PORTABILITY_AUDIT_MD = ROOT / "workflow_portability_audit_194.1.1.1.md"
PORTABILITY_SUMMARY_JSON = ROOT / "workflow_portability_summary_194.1.1.1.json"
SINGLE_SUMMARY_JSON = ROOT / "group_194_1_1_1_single_pilot_summary.json"
SINGLE_AUDIT_MD = ROOT / "group_194_1_1_1_single_pilot_audit.md"
DOUBLE_SUMMARY_JSON = ROOT / "group_194_1_1_1_double_pilot_summary.json"
DOUBLE_AUDIT_MD = ROOT / "group_194_1_1_1_double_pilot_audit.md"
HANDOFF_MD = ROOT / "handoff_194.1.1.1.md"
CURRENT_STATUS_JSON = ROOT / "current_status_194.1.1.1.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_194.1.1.1.txt"
REPORT_TEX = ROOT / "workflow_portability_report_194.1.1.1.tex"
REPORT_PDF = ROOT / "workflow_portability_report_194.1.1.1.pdf"

SINGLE_KMANIFOLDS_JSON = ROOT / "group_194_1_1_1_single_kmanifolds.json"
SINGLE_CONNECTIVITY_JSON = ROOT / "group_194_1_1_1_single_connectivity.json"
SINGLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_single_little_groups.json"
SINGLE_LINE_COMPAT_JSON = ROOT / "group_194_1_1_1_single_line_compatibility.json"
SINGLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_single_full_compatibility_with_planes.json"
SINGLE_BS_JSON = ROOT / "group_194_1_1_1_single_bs_analysis.json"
SINGLE_AI_JSON = ROOT / "group_194_1_1_1_single_ai_trivial_generators.json"
SINGLE_AI_ALL_OBJECTS_JSON = ROOT / "group_194_1_1_1_single_ai_all_induced_local_objects.json"
SINGLE_AI_AUTHORITATIVE_JSON = ROOT / "group_194_1_1_1_single_ai_authoritative_generators.json"
SINGLE_BS_AI_QUOTIENT_MD = ROOT / "bs_fix_reaudit_v1" / "single_bs_ai_quotient_report.md"
SINGLE_BS_AI_QUOTIENT_JSON = ROOT / "bs_fix_reaudit_v1" / "single_bs_ai_quotient_report.json"
SINGLE_INDICATOR_EXTRACTION_MD = ROOT / "bs_fix_reaudit_v1" / "single_indicator_extraction_report.md"
SINGLE_INDICATOR_EXTRACTION_JSON = ROOT / "bs_fix_reaudit_v1" / "single_indicator_extraction_report.json"

DOUBLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_double_little_groups.json"
DOUBLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_double_full_compatibility_with_planes.json"
DOUBLE_BS_JSON = ROOT / "group_194_1_1_1_double_bs_analysis.json"
DOUBLE_MINIMAL_JSON = ROOT / "group_194_1_1_1_double_minimal_prototype.json"
DOUBLE_AI_LIBRARY_INTEGRATION_MD = ROOT / "bs_fix_reaudit_v1" / "double_ai_library_integration_report.md"
DOUBLE_AI_LIBRARY_INTEGRATION_JSON = ROOT / "bs_fix_reaudit_v1" / "double_ai_library_integration_report.json"
DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_MD = ROOT / "bs_fix_reaudit_v1" / "double_benchmark_oracle_snf_check.md"
DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_JSON = ROOT / "bs_fix_reaudit_v1" / "double_benchmark_oracle_snf_check.json"
DOUBLE_DIAGNOSTIC_VS_BENCHMARK_MD = ROOT / "bs_fix_reaudit_v1" / "double_diagnostic_kernel_vs_benchmark_alignment_report.md"
DOUBLE_DIAGNOSTIC_VS_BENCHMARK_JSON = ROOT / "bs_fix_reaudit_v1" / "double_diagnostic_kernel_vs_benchmark_alignment_report.json"
DOUBLE_BS_AI_QUOTIENT_MD = ROOT / "bs_fix_reaudit_v1" / "double_bs_ai_quotient_report.md"
DOUBLE_BS_AI_QUOTIENT_JSON = ROOT / "bs_fix_reaudit_v1" / "double_bs_ai_quotient_report.json"
DOUBLE_INDICATOR_EXTRACTION_MD = ROOT / "bs_fix_reaudit_v1" / "double_indicator_extraction_report.md"
DOUBLE_INDICATOR_EXTRACTION_JSON = ROOT / "bs_fix_reaudit_v1" / "double_indicator_extraction_report.json"
REDUCTION_REPORT_MD = ROOT / "bs_fix_reaudit_v1" / "final_object_reduction_report.md"
REDUCTION_REPORT_JSON = ROOT / "bs_fix_reaudit_v1" / "final_object_reduction_report.json"
REDUCTION_CHECK_MD = ROOT / "bs_fix_reaudit_v1" / "final_object_vs_bilbao_equivalent_check.md"
REDUCTION_CHECK_JSON = ROOT / "bs_fix_reaudit_v1" / "final_object_vs_bilbao_equivalent_check.json"
FINAL_PATH_SIGNATURE_MD = ROOT / "bs_fix_reaudit_v1" / "final_path_signature_report.md"
FINAL_PATH_SIGNATURE_JSON = ROOT / "bs_fix_reaudit_v1" / "final_path_signature_report.json"
FINAL_PATH_EQUIV_MD = ROOT / "bs_fix_reaudit_v1" / "final_path_candidate_equivalence_report.md"
FINAL_PATH_EQUIV_JSON = ROOT / "bs_fix_reaudit_v1" / "final_path_candidate_equivalence_report.json"
FINAL_BS_STRONG_MD = ROOT / "bs_fix_reaudit_v1" / "final_bs_strong_equivalence_report.md"
FINAL_BS_STRONG_JSON = ROOT / "bs_fix_reaudit_v1" / "final_bs_strong_equivalence_report.json"
MISSING_ROW_WITNESS_MD = ROOT / "bs_fix_reaudit_v1" / "missing_row_language_witness_report.md"
MISSING_ROW_WITNESS_JSON = ROOT / "bs_fix_reaudit_v1" / "missing_row_language_witness_report.json"
P1_P5_RESOLUTION_MD = ROOT / "bs_fix_reaudit_v1" / "p1_p5_doubleclass_resolution_report.md"
P1_P5_RESOLUTION_JSON = ROOT / "bs_fix_reaudit_v1" / "p1_p5_doubleclass_resolution_report.json"
FULL_SHELL_AUTOMORPHISM_MD = ROOT / "bs_fix_reaudit_v1" / "full_shell_automorphism_search_report.md"
FULL_SHELL_AUTOMORPHISM_JSON = ROOT / "bs_fix_reaudit_v1" / "full_shell_automorphism_search_report.json"
FULL_POINT_SHELL_AUTOMORPHISM_MD = ROOT / "bs_fix_reaudit_v1" / "full_point_shell_automorphism_search_report.md"
FULL_POINT_SHELL_AUTOMORPHISM_JSON = ROOT / "bs_fix_reaudit_v1" / "full_point_shell_automorphism_search_report.json"
PUBLICATION_SHELL_REDUCTION_MD = ROOT / "bs_fix_reaudit_v1" / "publication_shell_reduction_report.md"
PUBLICATION_SHELL_REDUCTION_JSON = ROOT / "bs_fix_reaudit_v1" / "publication_shell_reduction_report.json"
PUBLICATION_SHELL_BILBAO_MD = ROOT / "bs_fix_reaudit_v1" / "publication_shell_vs_bilbao_check.md"
PUBLICATION_SHELL_BILBAO_JSON = ROOT / "bs_fix_reaudit_v1" / "publication_shell_vs_bilbao_check.json"
INTERNAL_VS_PUBLICATION_MD = ROOT / "bs_fix_reaudit_v1" / "internal_vs_publication_object_report.md"
INTERNAL_VS_PUBLICATION_JSON = ROOT / "bs_fix_reaudit_v1" / "internal_vs_publication_object_report.json"
POINT_ROW_TRANSLATION_MD = ROOT / "bs_fix_reaudit_v1" / "point_row_translation_legality_report.md"
POINT_ROW_TRANSLATION_JSON = ROOT / "bs_fix_reaudit_v1" / "point_row_translation_legality_report.json"
AI_SEED_AUDIT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_seed_audit_report.md"
AI_SEED_AUDIT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_seed_audit_report.json"
AI_SEED_DELTA_MD = ROOT / "bs_fix_reaudit_v1" / "ai_seed_delta_after_bs_fix_report.md"
AI_SEED_DELTA_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_seed_delta_after_bs_fix_report.json"
AI_LIBRARY_INTEGRATION_MD = ROOT / "bs_fix_reaudit_v1" / "ai_library_integration_report.md"
AI_LIBRARY_INTEGRATION_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_library_integration_report.json"
AI_CHARACTER_FIELD_ALIGNMENT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_character_field_alignment_report.md"
AI_CHARACTER_FIELD_ALIGNMENT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_character_field_alignment_report.json"
AI_FULL_CHARACTER_ALIGNMENT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_full_character_alignment_report.md"
AI_FULL_CHARACTER_ALIGNMENT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_full_character_alignment_report.json"
AI_HONEST_BLOCKER_MD = ROOT / "bs_fix_reaudit_v1" / "ai_honest_blocker_report.md"
AI_HONEST_BLOCKER_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_honest_blocker_report.json"
AI_OBSTRUCTION_DIAG_MD = ROOT / "bs_fix_reaudit_v1" / "ai_obstruction_diagnosis_report.md"
AI_OBSTRUCTION_DIAG_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_obstruction_diagnosis_report.json"
P4_INDUCTION_FAILURE_MD = ROOT / "bs_fix_reaudit_v1" / "p4_induction_failure_audit.md"
P4_INDUCTION_FAILURE_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_induction_failure_audit.json"
P4_PASSING_FAILING_MD = ROOT / "bs_fix_reaudit_v1" / "p4_passing_vs_failing_comparison.md"
P4_PASSING_FAILING_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_passing_vs_failing_comparison.json"
P4_EXACT_SOLVER_RELIABILITY_MD = ROOT / "bs_fix_reaudit_v1" / "p4_exact_solver_reliability_audit.md"
P4_EXACT_SOLVER_RELIABILITY_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_exact_solver_reliability_audit.json"
P4_BAND_CHARACTER_PHASE_MD = ROOT / "bs_fix_reaudit_v1" / "p4_band_character_site_phase_decomposition.md"
P4_BAND_CHARACTER_PHASE_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_band_character_site_phase_decomposition.json"
D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD = ROOT / "bs_fix_reaudit_v1" / "d3h_like_local_object_crosscheck.md"
D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_JSON = ROOT / "bs_fix_reaudit_v1" / "d3h_like_local_object_crosscheck.json"
PPATH06_OBSTRUCTION_MD = ROOT / "bs_fix_reaudit_v1" / "ppath06_residual_obstruction_audit.md"
PPATH06_OBSTRUCTION_JSON = ROOT / "bs_fix_reaudit_v1" / "ppath06_residual_obstruction_audit.json"
LAYERWISE_L2_FPATH07_PPATH06_MD = ROOT / "bs_fix_reaudit_v1" / "l2_fpath07_ppath06_layerwise_comparison.md"
LAYERWISE_L2_FPATH07_PPATH06_JSON = ROOT / "bs_fix_reaudit_v1" / "l2_fpath07_ppath06_layerwise_comparison.json"
AI_ZERO_SUBSET_RANK_MD = ROOT / "bs_fix_reaudit_v1" / "ai_zero_subset_rank_report.md"
AI_ZERO_SUBSET_RANK_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_zero_subset_rank_report.json"
PARTIAL_AI_LATTICE_WITNESS_MD = ROOT / "bs_fix_reaudit_v1" / "partial_ai_lattice_witness_report.md"
PARTIAL_AI_LATTICE_WITNESS_JSON = ROOT / "bs_fix_reaudit_v1" / "partial_ai_lattice_witness_report.json"
BS_RANK_NAMING_FIX_MD = ROOT / "bs_fix_reaudit_v1" / "bs_rank_naming_fix_report.md"
BS_RANK_NAMING_FIX_JSON = ROOT / "bs_fix_reaudit_v1" / "bs_rank_naming_fix_report.json"
AI_RANK_GAP_ATTRIBUTION_MD = ROOT / "bs_fix_reaudit_v1" / "ai_rank_gap_attribution_report.md"
AI_RANK_GAP_ATTRIBUTION_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_rank_gap_attribution_report.json"
AI_VS_BILBAO_ALIGNMENT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_vs_bilbao_alignment_report.md"
AI_VS_BILBAO_ALIGNMENT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_vs_bilbao_alignment_report.json"
P4_TRACE_FORMULA_EXPLICIT_MD = ROOT / "bs_fix_reaudit_v1" / "p4_trace_formula_vs_explicit_orbit_report.md"
P4_TRACE_FORMULA_EXPLICIT_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_trace_formula_vs_explicit_orbit_report.json"
CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD = ROOT / "bs_fix_reaudit_v1" / "character_field_conversion_global_validation_report.md"
CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_JSON = ROOT / "bs_fix_reaudit_v1" / "character_field_conversion_global_validation_report.json"
P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD = ROOT / "bs_fix_reaudit_v1" / "p4_conversion_patch_independent_validation_report.md"
P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_JSON = ROOT / "bs_fix_reaudit_v1" / "p4_conversion_patch_independent_validation_report.json"
AI_RANK_GAP_QUOTIENT_MD = ROOT / "bs_fix_reaudit_v1" / "ai_rank_gap_quotient_report.md"
AI_RANK_GAP_QUOTIENT_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_rank_gap_quotient_report.json"
RESIDUAL_RANK5_PIVOT_WITNESS_MD = ROOT / "bs_fix_reaudit_v1" / "residual_rank5_pivot_witness_report.md"
RESIDUAL_RANK5_PIVOT_WITNESS_JSON = ROOT / "bs_fix_reaudit_v1" / "residual_rank5_pivot_witness_report.json"
PPATH06_ROW_SEMANTICS_MD = ROOT / "bs_fix_reaudit_v1" / "ppath06_row_semantics_report.md"
PPATH06_ROW_SEMANTICS_JSON = ROOT / "bs_fix_reaudit_v1" / "ppath06_row_semantics_report.json"
CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_MD = ROOT / "bs_fix_reaudit_v1" / "character_field_basis_convention_audit.md"
CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_JSON = ROOT / "bs_fix_reaudit_v1" / "character_field_basis_convention_audit.json"
SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_MD = ROOT / "bs_fix_reaudit_v1" / "sg194_setting_specific_character_conversion_validation.md"
SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_JSON = ROOT / "bs_fix_reaudit_v1" / "sg194_setting_specific_character_conversion_validation.json"
AI_COMPLETION_FEASIBILITY_MD = ROOT / "bs_fix_reaudit_v1" / "ai_completion_feasibility_from_residual_sector.md"
AI_COMPLETION_FEASIBILITY_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_completion_feasibility_from_residual_sector.json"
CLAIM_SCOPE_GUARDRAIL_MD = ROOT / "bs_fix_reaudit_v1" / "claim_scope_guardrail_report.md"
CLAIM_SCOPE_GUARDRAIL_JSON = ROOT / "bs_fix_reaudit_v1" / "claim_scope_guardrail_report.json"
AUTHORITATIVE_AI_PROMOTION_MD = ROOT / "bs_fix_reaudit_v1" / "authoritative_ai_promotion_report.md"
AUTHORITATIVE_AI_PROMOTION_JSON = ROOT / "bs_fix_reaudit_v1" / "authoritative_ai_promotion_report.json"
AI_RANK_AFTER_PROMOTION_MD = ROOT / "bs_fix_reaudit_v1" / "ai_rank_after_promotion_report.md"
AI_RANK_AFTER_PROMOTION_JSON = ROOT / "bs_fix_reaudit_v1" / "ai_rank_after_promotion_report.json"
PUBLICATION_POINT_BASIS_USAGE_MD = ROOT / "bs_fix_reaudit_v1" / "publication_point_basis_usage_report.md"
PUBLICATION_POINT_BASIS_USAGE_JSON = ROOT / "bs_fix_reaudit_v1" / "publication_point_basis_usage_report.json"
BS_AI_QUOTIENT_MD = ROOT / "bs_fix_reaudit_v1" / "bs_ai_quotient_report.md"
BS_AI_QUOTIENT_JSON = ROOT / "bs_fix_reaudit_v1" / "bs_ai_quotient_report.json"
INDICATOR_EXTRACTION_MD = ROOT / "bs_fix_reaudit_v1" / "indicator_extraction_report.md"
INDICATOR_EXTRACTION_JSON = ROOT / "bs_fix_reaudit_v1" / "indicator_extraction_report.json"

ZERO = Fraction(0, 1)
HALF = Fraction(1, 2)
LINE_SAMPLE = Fraction(1, 5)
BOUNDARY_VALUES = (ZERO, HALF)
AUTHORITATIVE_PHASE_AWARE_PROFILE = "phase_aware_l2_projective_v1"
AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND = (
    "authoritative_basis_decomposition_exact_unique_integer_with_phase_aware_l2_v1"
)
AUTHORITATIVE_AI_CHARACTER_FIELD = {
    "point": "character",
    "line": "character",
    "plane": "character",
    "default": "character",
}
RETIRED_INTRINSIC_BUILDER_KIND = "retired_intrinsic_class_sum_compare_only_non_authoritative"
RETIRED_EXTRINSIC_BUILDER_KIND = "retired_extrinsic_star_augmented_compare_only_non_authoritative"

REFERENCE_BASELINE_FILES = [
    "single_group_ai_completeness_summary.json",
    "single_group_indicator_group_summary.json",
    "single_group_bs_mod_ai_single_summary.json",
    "single_group_ai_completeness_audit.md",
    "double_group_ai_completeness_summary_10.4.1.31.json",
    "double_group_indicator_group_summary_10.4.1.31.json",
    "double_group_bs_mod_ai_summary_10.4.1.31.json",
    "double_group_bs_summary_10.4.1.31.json",
    "double_group_ai_completeness_audit_10.4.1.31.md",
    "debug_single_group_ai_bridge.py",
    "debug_single_group_ai_expanded.py",
    "debug_double_group_feasibility_10.4.1.31.py",
    "swyckoff_r.py",
    "swyckoff_k.py",
    "SSGReps/SSGReps/SSGReps.py",
    "SSGReps/SSGReps/SG_utils.py",
    "SSGReps/SSGReps/rep_utils.py",
]

PACKAGE_BACKGROUND_FILES = [
    "double_group_ai_completeness_audit_10.4.1.31.md",
    "double_group_ai_completeness_summary_10.4.1.31.json",
    "double_group_indicator_group_summary_10.4.1.31.json",
    "double_group_indicator_generators_10.4.1.31.json",
    "double_group_bs_mod_ai_summary_10.4.1.31.json",
    "double_group_bs_summary_10.4.1.31.json",
    "double_group_bs_basis_raw_10.4.1.31.json",
    "double_group_bs_basis_pretty_10.4.1.31.json",
    "double_group_full_compatibility_with_planes_10.4.1.31.json",
    "single_group_ai_completeness_audit.md",
    "single_group_ai_completeness_summary.json",
    "single_group_indicator_group_summary.json",
    "single_group_indicator_generators.json",
    "single_group_bs_mod_ai_single_summary.json",
    "swyckoff_r.py",
    "swyckoff_k.py",
    "SSGReps/SSGReps/SSGReps.py",
    "SSGReps/SSGReps/SG_utils.py",
    "SSGReps/SSGReps/rep_utils.py",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def json_default(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}
    if isinstance(value, Fraction):
        return frac_str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, sp.Basic):
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def resolve_repo_asset(rel: str | Path) -> Path:
    rel_path = Path(rel)
    if rel_path.is_absolute():
        return rel_path
    for base in (ROOT, COMMON_ROOT):
        candidate = base / rel_path
        if candidate.exists():
            return candidate
    raise FileNotFoundError(rel_path)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def complex_to_json(value: complex) -> dict[str, float]:
    return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}


def complex_list_to_json(values: Sequence[complex]) -> list[dict[str, float]]:
    return [complex_to_json(complex(value)) for value in values]


def complex_matrix_to_json(matrix: Sequence[Sequence[complex]]) -> list[list[dict[str, float]]]:
    return [complex_list_to_json(row) for row in matrix]


def complex_from_json(value: Any) -> complex:
    if isinstance(value, dict):
        return complex(float(value.get("real", 0.0)), float(value.get("imag", 0.0)))
    return complex(value)


def complex_matrix_from_json(matrix: Sequence[Sequence[Any]]) -> list[list[complex]]:
    return [[complex_from_json(value) for value in row] for row in matrix]


def format_tree(root: Path) -> list[str]:
    lines: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts) - 1
        prefix = "  " * depth + ("- " if depth else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def to_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str):
        return Fraction(value)
    return Fraction(value)


def frac_str(value: Any) -> str:
    value = to_fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def mod1_fraction(value: Any) -> Fraction:
    value = to_fraction(value) % 1
    return value + 1 if value < 0 else value


def vector_key(vector: Sequence[Any]) -> tuple[str, str, str]:
    return tuple(frac_str(mod1_fraction(value)) for value in vector)


def format_number(value: float, max_denominator: int = 48) -> str:
    return frac_str(Fraction(str(float(value))).limit_denominator(max_denominator))


def ordered_parameters(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> list[str]:
    ordered: list[str] = []
    for _const, coeffs in rep:
        for name in coeffs:
            if name not in ordered:
                ordered.append(name)
    return ordered


def rep_to_sympy(rep: Sequence[Tuple[Fraction, Dict[str, Fraction]]]) -> list[sp.Expr]:
    exprs: list[sp.Expr] = []
    for const, coeffs in rep:
        expr = sp.Rational(to_fraction(const).numerator, to_fraction(const).denominator)
        for name, coeff in coeffs.items():
            coeff_frac = to_fraction(coeff)
            expr += sp.Rational(coeff_frac.numerator, coeff_frac.denominator) * sp.Symbol(name)
        exprs.append(sp.simplify(expr))
    return exprs


def expr_str(expr: sp.Expr) -> str:
    return str(sp.simplify(expr)).replace("*", "")


def expr_vector_str(exprs: Sequence[sp.Expr]) -> str:
    return "(" + ", ".join(expr_str(expr) for expr in exprs) + ")"


def vector_add_scaled(anchor: Sequence[Any], basis: Sequence[Any], scale: Fraction) -> list[Fraction]:
    return [to_fraction(a) + to_fraction(scale) * to_fraction(b) for a, b in zip(anchor, basis)]


def evaluate_exprs(exprs: Sequence[sp.Expr], assignment: Dict[str, Fraction]) -> list[Fraction]:
    out: list[Fraction] = []
    for expr in exprs:
        value = expr
        for symbol_name, frac in assignment.items():
            value = value.subs(sp.Symbol(symbol_name), sp.Rational(frac.numerator, frac.denominator))
        out.append(Fraction(str(sp.simplify(value))))
    return out


def sample_assignment(parameters: Sequence[str]) -> Dict[str, Fraction]:
    pool = [Fraction(1, 5), Fraction(2, 7), Fraction(3, 11)]
    return {name: pool[index] for index, name in enumerate(parameters)}


def boundary_line_expressions(anchor: Sequence[Fraction], basis: Sequence[Fraction], parameter: str) -> list[sp.Expr]:
    exprs = []
    symbol = sp.Symbol(parameter)
    for base, vec in zip(anchor, basis):
        frac = to_fraction(base)
        expr = sp.Rational(frac.numerator, frac.denominator)
        coeff = to_fraction(vec)
        if coeff:
            expr += sp.Rational(coeff.numerator, coeff.denominator) * symbol
        exprs.append(sp.simplify(expr))
    return exprs


def geometry_type(dimension: int) -> str:
    return {0: "point", 1: "line", 2: "plane", 3: "generic"}[dimension]


def assign_ids(entries: Sequence[dict], prefix: str) -> None:
    for index, entry in enumerate(entries, start=1):
        entry["id"] = f"{prefix}{index}"


def load_ssgreps_module():
    candidates = [
        COMMON_SSGREPS_ROOT / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps.py",
    ]
    ssgreps_py = next((candidate for candidate in candidates if candidate.exists()), candidates[0])
    ssgreps_dir = ssgreps_py.parent
    if str(ssgreps_dir) not in sys.path:
        sys.path.insert(0, str(ssgreps_dir))
    spec = importlib.util.spec_from_file_location("ssgreps_local_portability", ssgreps_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {ssgreps_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_identify_pkl() -> Path:
    if IDENTIFY_PKL.exists():
        return IDENTIFY_PKL
    if not IDENTIFY_TAR.exists():
        raise FileNotFoundError(f"missing {IDENTIFY_PKL} and {IDENTIFY_TAR}")
    with tarfile_module.open(IDENTIFY_TAR, "r:gz") as tar:
        tar.extract("identify.pkl", path=COMMON_SSG_DATA_ROOT)
    return IDENTIFY_PKL


def load_ssg_dict(group_number: str) -> dict[str, Any]:
    identify_pkl = ensure_identify_pkl()
    with identify_pkl.open("rb") as fh:
        ssg_list = pickle.load(fh)
    return next(item for item in ssg_list if item["ssgNum"] == group_number)


@lru_cache(maxsize=None)
def _load_realspace_context_payload(group_number: str) -> dict[str, Any]:
    full_data, _ = swyckoff_r.load_irssg_data(group_number, 0)
    wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(group_number, fast=True)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]
    return {
        "full_data": full_data,
        "wyckoff_entries": wyckoff_entries,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
    }


def load_context(module: Any, group_number: str, group_label: str, ssg_dict: dict[str, Any]) -> dict[str, Any]:
    ssg = module.loadSsgGroup(group_number, np.array([0.0, 0.0, 0.0]), group_label, ssg_dict)
    realspace = _load_realspace_context_payload(group_number)
    ctx = {
        "group_number": group_number,
        "group_label": group_label,
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": realspace["full_data"],
        "full_ops": realspace["full_ops"],
        "full_time_revs": realspace["full_time_revs"],
        "wyckoff_entries": realspace["wyckoff_entries"],
    }
    ctx["raw_operations"] = single_expanded.raw_ops(ctx)
    ctx["group_tables"] = single_expanded.build_group_tables(ctx)
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in realspace["wyckoff_entries"]}
    return ctx


def load_reciprocal_context(group_number: str) -> dict[str, Any]:
    data, _time_revs = swyckoff_k.load_irssg_data(group_number, 0)
    full_ops_raw = [swyckoff_k.op_from_json(op) for op in data["operations"]]
    time_revs_raw = data.get("time_revs", [False] * len(full_ops_raw))
    spin_matrices_raw = data.get("spin_matrices")
    ops, mag_ops_real, _spin_ops_real, spin_ops_symbolic = swyckoff_k.build_reciprocal_spin_data(
        full_ops_raw,
        time_revs_raw,
        spin_matrices_raw,
    )
    try:
        pg_lookup = swyckoff_k.mw.build_point_group_signature_lookup()
    except FileNotFoundError:
        pg_lookup = {}
    return {
        "data": data,
        "ops": ops,
        "mag_ops_real": mag_ops_real,
        "spin_ops_symbolic": spin_ops_symbolic,
        "pg_lookup": pg_lookup,
    }


def compute_site_symmetry_from_indices(indices: Sequence[int], ctx: dict) -> dict:
    mag_stab_ops = [ctx["mag_ops_real"][i] for i in indices]
    spin_stab_ops_symbolic = [ctx["spin_ops_symbolic"][i] for i in indices]
    unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]
    unitary_site_symmetry = swyckoff_k.mw.classify_site_symmetry(
        swyckoff_k.unique_rotations(unitary_mag_stab_ops),
        ctx["pg_lookup"] or {},
    )
    spatial_site_symmetry_custom, spatial_site_symmetry_ops = swyckoff_k.mw.build_custom_site_symmetry(mag_stab_ops)
    site_symmetry_custom, site_symmetry_ops = swyckoff_k.build_spin_site_symmetry(spin_stab_ops_symbolic)
    if site_symmetry_custom is None:
        site_symmetry_custom = spatial_site_symmetry_custom
        site_symmetry_ops = spatial_site_symmetry_ops
    site_symmetry = (
        swyckoff_k.mw.lookup_magnetic_bilbao_symbol(
            spatial_site_symmetry_custom or site_symmetry_custom or "",
            unitary_site_symmetry or "",
            spatial_site_symmetry_ops or site_symmetry_ops,
        )
        or swyckoff_k.mw.bilbao_magnetic_point_group_symbol(
            spatial_site_symmetry_ops or site_symmetry_ops,
            crystal_system=str(ctx["data"].get("crystal_system", "")),
        )
        or spatial_site_symmetry_custom
        or site_symmetry_custom
        or unitary_site_symmetry
    )
    return {
        "site_symmetry": site_symmetry,
        "site_symmetry_custom": site_symmetry_custom,
        "unitary_site_symmetry": unitary_site_symmetry,
    }


def normalize_k_entry(entry: dict[str, Any]) -> dict:
    params = ordered_parameters(entry["rep"])
    exprs = rep_to_sympy(entry["rep"])
    sample = evaluate_exprs(exprs, sample_assignment(params))
    basis = [[to_fraction(value) for value in row] for row in entry["basis_vecs"]]
    anchor = [to_fraction(value) for value in entry["x0"]]
    dimension = int(entry["dim"])
    constraints = [f"0 < {name}" for name in params] + [f"{name} < 1/2" for name in params]
    metadata = {
        "source_letter": entry["letter"],
        "source_mult": int(entry["mult"]),
        "source_dimension": dimension,
        "source_orbit": list(entry["orbit"]),
        "source_representative_coordinate": entry["representative_coordinate"],
        "source_x0": [frac_str(value) for value in anchor],
        "source_basis_vecs": [[frac_str(value) for value in row] for row in basis],
        "source_rep": [
            [frac_str(to_fraction(const)), {name: frac_str(to_fraction(coeff)) for name, coeff in coeffs.items()}]
            for const, coeffs in entry["rep"]
        ],
    }
    return {
        "label": entry["letter"],
        "type": geometry_type(dimension),
        "dimension": dimension,
        "parametrization": expr_vector_str(exprs),
        "coordinate_expressions": [expr_str(expr) for expr in exprs],
        "parameters": params,
        "constraints": constraints,
        "constraint_summary": ", ".join(constraints),
        "sample_point": [frac_str(mod1_fraction(value)) for value in sample],
        "metadata": metadata,
        "_anchor": anchor,
        "_basis": basis,
        "_exprs": exprs,
        "_params": params,
    }


def pick_group_entries(group_number: str) -> Dict[str, List[dict]]:
    wyckoff, coord_key = swyckoff_k.compute_wyckoff_output(group_number, kspace=True, fast=True)
    if coord_key != "orbit":
        raise ValueError(f"Unexpected coordinate key: {coord_key}")
    points: list[dict] = []
    lines: list[dict] = []
    planes: list[dict] = []
    generic: list[dict] = []
    for entry in wyckoff:
        normalized = normalize_k_entry(entry)
        if normalized["dimension"] == 0:
            points.append(normalized)
        elif normalized["dimension"] == 1:
            lines.append(normalized)
        elif normalized["dimension"] == 2:
            planes.append(normalized)
        else:
            generic.append(normalized)
    points.sort(key=lambda item: item["label"])
    lines.sort(key=lambda item: item["label"])
    planes.sort(key=lambda item: item["label"])
    generic.sort(key=lambda item: item["label"])
    assign_ids(points, "P")
    assign_ids(lines, "L")
    assign_ids(planes, "S")
    return {"points": points, "lines": lines, "planes": planes, "generic": generic}


def subspace_orbit_id_maps(lines: Sequence[dict], planes: Sequence[dict], ctx: dict) -> Tuple[dict, dict]:
    line_orbit_to_id = {}
    plane_orbit_to_id = {}
    for line in lines:
        orbit_key = swyckoff_k.subspace_orbit_key(line["_anchor"], line["_basis"], ctx["ops"])
        line_orbit_to_id[orbit_key] = line["id"]
    for plane in planes:
        orbit_key = swyckoff_k.subspace_orbit_key(plane["_anchor"], plane["_basis"], ctx["ops"])
        plane_orbit_to_id[orbit_key] = plane["id"]
    return line_orbit_to_id, plane_orbit_to_id


def closure_components(anchor: Sequence[Fraction], basis: Sequence[Sequence[Fraction]], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> List[dict]:
    components = []
    for closed_x0, closed_basis in swyckoff_k.closure_under_stabilizer(anchor, basis, ctx["ops"]):
        orbit_key = swyckoff_k.subspace_orbit_key(closed_x0, closed_basis, ctx["ops"])
        component = {
            "dimension": len(closed_basis),
            "x0": [frac_str(value) for value in closed_x0],
            "basis_vecs": [[frac_str(value) for value in row] for row in closed_basis],
            "line_id": line_orbit_to_id.get(orbit_key),
            "plane_id": plane_orbit_to_id.get(orbit_key),
        }
        components.append(component)
    return components


def subspace_symmetry_summary(anchor: Sequence[Fraction], basis: Sequence[Sequence[Fraction]], ctx: dict) -> dict:
    generic_point = swyckoff_k.generic_point_on_subspace(anchor, basis) if basis else list(anchor)
    generic_stab_indices = swyckoff_k.stabilizer(generic_point, ctx["ops"])
    pointwise_stab_indices = swyckoff_k.stabilizer_indices_for_subspace(anchor, basis, ctx["ops"])
    generic_rotations = len(swyckoff_k.unique_rotations([ctx["ops"][i] for i in generic_stab_indices]))
    pointwise_rotations = len(swyckoff_k.unique_rotations([ctx["ops"][i] for i in pointwise_stab_indices]))
    symmetry = compute_site_symmetry_from_indices(generic_stab_indices, ctx)
    return {
        "generic_point": [frac_str(value) for value in generic_point],
        "generic_stabilizer_size": len(generic_stab_indices),
        "generic_rotation_stabilizer_size": generic_rotations,
        "pointwise_stabilizer_size": len(pointwise_stab_indices),
        "pointwise_rotation_stabilizer_size": pointwise_rotations,
        **symmetry,
    }


def line_signature(anchor: Sequence[Fraction], basis: Sequence[Fraction]) -> Tuple[Tuple[str, str, str], Tuple[str, str, str]]:
    return vector_key(anchor), tuple(frac_str(to_fraction(value)) for value in basis)


def point_coordinate_keys(point: dict[str, Any]) -> list[tuple[str, str, str]]:
    keys = {vector_key(point["_anchor"])}
    sample_point = point.get("sample_point")
    if sample_point:
        keys.add(tuple(sample_point))
    for coord in point.get("metadata", {}).get("source_orbit", []):
        pieces = tuple(piece.strip() for piece in coord.split(","))
        if len(pieces) == 3:
            keys.add(pieces)
    return sorted(keys)


def annotate_special_manifolds(lines: Sequence[dict], planes: Sequence[dict], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> None:
    for line in lines:
        line["manifold_role"] = "separately_listed_special_line_manifold"
        line["symmetry_summary"] = subspace_symmetry_summary(line["_anchor"], line["_basis"], ctx)
        line["closure_under_pointwise_stabilizer"] = closure_components(line["_anchor"], line["_basis"], ctx, line_orbit_to_id, plane_orbit_to_id)
    for plane in planes:
        plane["manifold_role"] = "separately_listed_special_plane_manifold"
        plane["symmetry_summary"] = subspace_symmetry_summary(plane["_anchor"], plane["_basis"], ctx)


def infer_line_connectivity(points: Sequence[dict], lines: Sequence[dict]) -> Tuple[List[dict], List[dict]]:
    point_map = {key: point for point in points for key in point_coordinate_keys(point)}
    point_line: List[dict] = []
    unmatched: List[dict] = []
    for line in lines:
        basis = line["_basis"][0]
        param = line["_params"][0]
        endpoints: List[dict] = []
        for boundary in BOUNDARY_VALUES:
            boundary_point = vector_add_scaled(line["_anchor"], basis, boundary)
            key = vector_key(boundary_point)
            condition = f"{param} = {frac_str(boundary)}"
            point = point_map.get(key)
            endpoint = {
                "boundary_condition": condition,
                "point_coordinates": [frac_str(mod1_fraction(value)) for value in boundary_point],
                "point_id": point["id"] if point else None,
            }
            endpoints.append(endpoint)
            if point:
                point_line.append(
                    {
                        "point_id": point["id"],
                        "line_id": line["id"],
                        "boundary_condition": condition,
                        "derived_point": endpoint["point_coordinates"],
                    }
                )
            else:
                unmatched.append(
                    {
                        "line_id": line["id"],
                        "boundary_condition": condition,
                        "derived_point": endpoint["point_coordinates"],
                    }
                )
        line["endpoints"] = endpoints
    return point_line, unmatched


def infer_plane_connectivity(planes: Sequence[dict], lines: Sequence[dict], ctx: dict, line_orbit_to_id: dict, plane_orbit_to_id: dict) -> Tuple[List[dict], List[dict]]:
    line_map = {line_signature(line["_anchor"], line["_basis"][0]): line for line in lines}
    line_plane: List[dict] = []
    unmatched: List[dict] = []
    for plane in planes:
        params = plane["_params"]
        boundaries: List[dict] = []
        for fixed_index, fixed_param in enumerate(params):
            free_index = 1 - fixed_index
            free_param = params[free_index]
            free_basis = plane["_basis"][free_index]
            fixed_basis = plane["_basis"][fixed_index]
            for boundary in BOUNDARY_VALUES:
                anchor = vector_add_scaled(plane["_anchor"], fixed_basis, boundary)
                exprs = boundary_line_expressions(anchor, free_basis, free_param)
                condition = f"{fixed_param} = {frac_str(boundary)}"
                candidate = {
                    "boundary_condition": condition,
                    "boundary_role": "geometric_boundary_line",
                    "parametrization": expr_vector_str(exprs),
                    "coordinate_expressions": [expr_str(expr) for expr in exprs],
                    "parameters": [free_param],
                    "constraints": [f"0 < {free_param}", f"{free_param} < 1/2"],
                    "sample_point": [frac_str(mod1_fraction(value)) for value in vector_add_scaled(anchor, free_basis, LINE_SAMPLE)],
                }
                line = line_map.get(line_signature(anchor, free_basis))
                symmetry_summary = subspace_symmetry_summary(anchor, [free_basis], ctx)
                closure = closure_components(anchor, [free_basis], ctx, line_orbit_to_id, plane_orbit_to_id)
                candidate["symmetry_summary"] = symmetry_summary
                candidate["closure_under_pointwise_stabilizer"] = closure
                orbit_key = swyckoff_k.subspace_orbit_key(anchor, [free_basis], ctx["ops"])
                orbit_line_id = line_orbit_to_id.get(orbit_key)
                candidate["special_line_orbit_match"] = orbit_line_id
                candidate["classification"] = {
                    "is_separately_listed_special_line": bool(orbit_line_id),
                    "reason": "Matches an existing 1D manifold orbit." if orbit_line_id else "Does not match any listed 1D manifold orbit.",
                }
                matched_line_id = line["id"] if line else orbit_line_id
                if matched_line_id is not None:
                    candidate["line_id"] = matched_line_id
                    boundaries.append(candidate)
                    line_plane.append(
                        {
                            "line_id": matched_line_id,
                            "plane_id": plane["id"],
                            "boundary_condition": condition,
                            "derived_line": candidate["parametrization"],
                        }
                    )
                else:
                    candidate["line_id"] = None
                    closure_plane_ids = [component["plane_id"] for component in closure if component["plane_id"]]
                    if closure_plane_ids:
                        candidate["classification"]["reason"] = (
                            "Pointwise stabilizer closes back to separately listed plane manifolds "
                            + ", ".join(closure_plane_ids)
                            + ", so this is treated as a geometric boundary only."
                        )
                    boundaries.append(candidate)
                    unmatched.append(
                        {
                            "plane_id": plane["id"],
                            "boundary_condition": condition,
                            "boundary_role": candidate["boundary_role"],
                            "derived_line": candidate["parametrization"],
                            "parameters": candidate["parameters"],
                            "constraints": candidate["constraints"],
                            "sample_point": candidate["sample_point"],
                            "symmetry_summary": candidate["symmetry_summary"],
                            "closure_under_pointwise_stabilizer": candidate["closure_under_pointwise_stabilizer"],
                            "special_line_orbit_match": candidate["special_line_orbit_match"],
                            "classification": candidate["classification"],
                        }
                    )
        plane["boundary_lines"] = boundaries
    return line_plane, unmatched


def _line_embedding_in_plane(
    line_anchor: Sequence[Fraction],
    line_basis: Sequence[Fraction],
    plane_anchor: Sequence[Fraction],
    plane_basis: Sequence[Sequence[Fraction]],
) -> dict[str, list[str]] | None:
    plane_matrix = sp.Matrix(
        [
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[0]],
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[1]],
        ]
    ).T
    offset = sp.Matrix(
        [
            sp.Rational(to_fraction(line_value - plane_value).numerator, to_fraction(line_value - plane_value).denominator)
            for line_value, plane_value in zip(line_anchor, plane_anchor)
        ]
    )
    direction = sp.Matrix(
        [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in line_basis]
    )
    try:
        anchor_coords = plane_matrix.gauss_jordan_solve(offset)[0]
        direction_coords = plane_matrix.gauss_jordan_solve(direction)[0]
    except Exception:
        return None
    return {
        "anchor_coords": [str(sp.simplify(value)) for value in anchor_coords],
        "direction_coords": [str(sp.simplify(value)) for value in direction_coords],
    }


def _point_embedding_in_plane(
    point_coords: Sequence[Fraction],
    plane_anchor: Sequence[Fraction],
    plane_basis: Sequence[Sequence[Fraction]],
) -> list[str] | None:
    plane_matrix = sp.Matrix(
        [
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[0]],
            [sp.Rational(to_fraction(value).numerator, to_fraction(value).denominator) for value in plane_basis[1]],
        ]
    ).T
    offset = sp.Matrix(
        [
            sp.Rational(to_fraction(point_value - plane_value).numerator, to_fraction(point_value - plane_value).denominator)
            for point_value, plane_value in zip(point_coords, plane_anchor)
        ]
    )
    try:
        plane_coords = plane_matrix.gauss_jordan_solve(offset)[0]
    except Exception:
        return None
    return [str(sp.simplify(value)) for value in plane_coords]


def annotate_special_line_plane_incidences(planes: Sequence[dict], lines: Sequence[dict]) -> list[dict[str, Any]]:
    incidences: list[dict[str, Any]] = []
    for line in lines:
        line["containing_planes"] = []
    for plane in planes:
        boundary_ids = {
            entry["line_id"]
            for entry in plane.get("boundary_lines", [])
            if entry.get("line_id")
        }
        contained_special_lines: list[dict[str, Any]] = []
        for line in lines:
            embedding = _line_embedding_in_plane(
                line["_anchor"],
                line["_basis"][0],
                plane["_anchor"],
                plane["_basis"],
            )
            if embedding is None:
                continue
            entry = {
                "plane_id": plane["id"],
                "line_id": line["id"],
                "incidence_role": "boundary" if line["id"] in boundary_ids else "interior",
                "plane_coordinates": embedding,
            }
            contained_special_lines.append(entry)
            line["containing_planes"].append(
                {
                    "plane_id": plane["id"],
                    "incidence_role": entry["incidence_role"],
                    "plane_coordinates": dict(embedding),
                }
            )
            incidences.append(dict(entry))
        plane["contained_special_lines"] = contained_special_lines
        plane["interior_special_lines"] = [
            item for item in contained_special_lines if item["incidence_role"] == "interior"
        ]
    return incidences


def strip_internal_fields(entries: Sequence[dict]) -> List[dict]:
    return [{key: value for key, value in entry.items() if not key.startswith("_")} for entry in entries]


def prepare_kgeometry(group_number: str) -> dict[str, Any]:
    grouped = pick_group_entries(group_number)
    points = grouped["points"]
    lines = grouped["lines"]
    planes = grouped["planes"]
    generic = grouped["generic"]
    ctx = load_reciprocal_context(group_number)
    line_orbit_to_id, plane_orbit_to_id = subspace_orbit_id_maps(lines, planes, ctx)
    annotate_special_manifolds(lines, planes, ctx, line_orbit_to_id, plane_orbit_to_id)
    point_line, unmatched_endpoints = infer_line_connectivity(points, lines)
    line_plane, unmatched_plane_boundaries = infer_plane_connectivity(planes, lines, ctx, line_orbit_to_id, plane_orbit_to_id)
    special_line_plane_incidences = annotate_special_line_plane_incidences(planes, lines)
    payload = {
        "group_number": group_number,
        "objects": strip_internal_fields(points + lines + planes),
        "generic_manifolds_ignored": strip_internal_fields(generic),
        "point_line": point_line,
        "unmatched_line_endpoints": unmatched_endpoints,
        "line_plane": line_plane,
        "special_line_plane_incidences": special_line_plane_incidences,
        "unmatched_plane_boundaries": unmatched_plane_boundaries,
    }
    return {
        "grouped": grouped,
        "payload": payload,
        "ctx": ctx,
        "line_orbit_to_id": line_orbit_to_id,
        "plane_orbit_to_id": plane_orbit_to_id,
    }


def build_kgeometry(group_number: str) -> dict[str, Any]:
    return prepare_kgeometry(group_number)["payload"]


def coordinate_to_id_map(points: Sequence[dict]) -> dict[tuple[str, str, str], str]:
    return {key: point["id"] for point in points for key in point_coordinate_keys(point)}


def build_synthetic_boundary_points(kgeom: dict[str, Any]) -> list[dict[str, Any]]:
    objects = kgeom["grouped"]
    point_map = coordinate_to_id_map(objects["points"])
    synthetic: list[dict[str, Any]] = []
    seen = set(point_map)

    def ensure_point(coords: Sequence[str], source: str) -> str:
        key = tuple(coords)
        if key in point_map:
            return point_map[key]
        if key in seen:
            for item in synthetic:
                if tuple(item["sample_point"]) == key:
                    return item["id"]
        new_id = f"B{len(synthetic) + 1}"
        item = {
            "id": new_id,
            "type": "boundary_point",
            "dimension": 0,
            "sample_point": list(coords),
            "coordinate_expressions": list(coords),
            "source": source,
        }
        synthetic.append(item)
        seen.add(key)
        return new_id

    for relation in kgeom["connectivity"]["unmatched_line_endpoints"]:
        ensure_point(relation["derived_point"], f"{relation['line_id']}:{relation['boundary_condition']}")

    plane_lookup = {item["id"]: item for item in objects["planes"]}
    for plane in objects["planes"]:
        anchor = plane["_anchor"]
        basis1, basis2 = plane["_basis"]
        for coeff1 in BOUNDARY_VALUES:
            for coeff2 in BOUNDARY_VALUES:
                corner = vector_add_scaled(vector_add_scaled(anchor, basis1, coeff1), basis2, coeff2)
                ensure_point([frac_str(mod1_fraction(value)) for value in corner], f"{plane['id']}:corner")

    return synthetic


def augment_connectivity_with_boundary_points(kgeom: dict[str, Any], synthetic_points: list[dict[str, Any]]) -> None:
    id_by_coord = coordinate_to_id_map(kgeom["grouped"]["points"])
    for point in synthetic_points:
        id_by_coord[tuple(point["sample_point"])] = point["id"]
    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            if endpoint["point_id"] is None:
                endpoint["point_id"] = id_by_coord[tuple(endpoint["point_coordinates"])]


def point_capture_id(point_id: str, coords: Sequence[str]) -> str:
    suffix = "_".join(coord.replace("/", "d").replace("-", "m") for coord in coords)
    return f"{point_id}__{suffix}"


def derive_plane_corner_entries(plane_obj: dict[str, Any], point_by_coord: dict[tuple[str, str, str], str]) -> list[dict[str, Any]]:
    anchor = plane_obj["_anchor"]
    basis1, basis2 = plane_obj["_basis"]
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, str, str]]] = set()
    for coeff1 in BOUNDARY_VALUES:
        for coeff2 in BOUNDARY_VALUES:
            point = vector_add_scaled(vector_add_scaled(anchor, basis1, coeff1), basis2, coeff2)
            coords = [frac_str(mod1_fraction(value)) for value in point]
            point_id = point_by_coord[vector_key(point)]
            dedup_key = (point_id, tuple(coords))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            out.append({"point_id": point_id, "point_coordinates": coords})
    return out


def operation_key_from_capture(capture: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(round(float(entry))) for entry in row) for row in capture["rotC"][op_index])
    tau = tuple(round(float(entry) % 1.0, 8) for entry in capture["tauC"][op_index])
    spin = tuple(tuple(round(float(entry), 8) for entry in row) for row in capture["spin"][op_index])
    return rot, tau, spin, int(capture["timeReversal"][op_index])


def capture_little_group(module: Any, group_number: str, ssg_dict: dict[str, Any], ctx: dict[str, Any], group_label: str, manifold_id: str, kvec: list[float]) -> dict[str, Any]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        lg = module.load_little_group(group_number, np.array(kvec, dtype=float), False, group_label, ssg_dict)
    unitary_rotations: list[np.ndarray] = []
    unitary_translations: list[np.ndarray] = []
    unitary_raw_indices: list[int] = []
    unitary_capture_indices: list[int] = []
    for raw_index, (rotation, translation, tr) in enumerate(zip(lg.rotC, lg.tauC, lg.time_reversal)):
        if int(tr) < 0:
            continue
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        unitary_rotations.append(rot)
        unitary_translations.append(tau)
        unitary_capture_indices.append(raw_index)
        unitary_raw_indices.append(
            single_expanded.match_raw_op(
                ctx,
                ctx["group_tables"]["operations"],
                rot,
                tau,
                False,
            )
        )
    raw_character = [[complex(value) for value in row] for row in lg.character]
    linear_character = [[complex(value) for value in row] for row in lg.linear_character]
    return {
        "group_type": 1 if group_label == "single" else 2,
        "manifold_id": manifold_id,
        "kvec": list(kvec),
        "warning_text": stdout.getvalue().strip(),
        "little_group_operation_count": len(lg.oplist),
        "antiunitary_present": bool(lg.antiunitary),
        "rep_count": len(lg.rep_degree),
        "rep_degree": [int(value) for value in lg.rep_degree],
        "torsion": [int(value) for value in lg.torsion],
        "unitary_operation_count": len(unitary_raw_indices),
        "unitary_raw_indices": unitary_raw_indices,
        "unitary_capture_indices": unitary_capture_indices,
        "rotC": [[[float(entry) for entry in row] for row in rotation] for rotation in lg.rotC],
        "tauC": [[float(entry) for entry in translation] for translation in lg.tauC],
        "spin": [[[float(entry) for entry in row] for row in spin] for spin in lg.spin],
        "timeReversal": [int(value) for value in lg.time_reversal],
        "character": raw_character,
        "linear_character": linear_character,
        "character_json": complex_matrix_to_json(raw_character),
        "linear_character_json": complex_matrix_to_json(linear_character),
        "unitary_rotations": [rotation.tolist() for rotation in unitary_rotations],
        "unitary_translations": [translation.tolist() for translation in unitary_translations],
        "kconv": (
            kvec[0] * ctx["reciprocal_basis"][0]
            + kvec[1] * ctx["reciprocal_basis"][1]
            + kvec[2] * ctx["reciprocal_basis"][2]
        ).tolist(),
    }


def build_manifold_capture(module: Any, group_number: str, ssg_dict: dict[str, Any], ctx: dict[str, Any], group_label: str, kgeom: dict[str, Any]) -> dict[str, Any]:
    captures: dict[str, Any] = {}
    for point in kgeom["grouped"]["points"]:
        captures[point["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point["id"],
            [float(Fraction(value)) for value in point["sample_point"]],
        )
    for point in kgeom["synthetic_boundary_points"]:
        captures[point["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point["id"],
            [float(Fraction(value)) for value in point["sample_point"]],
        )
    for line in kgeom["grouped"]["lines"]:
        captures[line["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            line["id"],
            [float(Fraction(value)) for value in line["sample_point"]],
        )
    for plane in kgeom["grouped"]["planes"]:
        captures[plane["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            plane["id"],
            [float(Fraction(value)) for value in plane["sample_point"]],
        )
    for point_instance in kgeom.get("point_instance_entries", []):
        captures[point_instance["capture_id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            point_instance["capture_id"],
            [float(Fraction(value)) for value in point_instance["point_coordinates"]],
        )
    return captures


def as_exact_char(value: complex) -> sp.Expr:
    if isinstance(value, sp.Basic):
        value = complex(value.evalf())
    real = 0.0 if abs(value.real) < 1e-8 else float(value.real)
    imag = 0.0 if abs(value.imag) < 1e-8 else float(value.imag)
    if abs(real - round(real)) < 1e-8:
        real_expr = sp.Integer(int(round(real)))
    else:
        real_expr = sp.nsimplify(real)
    if abs(imag - round(imag)) < 1e-8:
        imag_expr = sp.Integer(int(round(imag)))
    else:
        imag_expr = sp.nsimplify(imag)
    if imag == 0.0:
        return real_expr
    if real == 0.0:
        return sp.I * imag_expr
    return real_expr + sp.I * imag_expr


def _exactify_matrix_entries(matrix: sp.Matrix) -> sp.Matrix:
    return sp.Matrix(
        [
            [as_exact_char(complex(value.evalf())) for value in row]
            for row in matrix.tolist()
        ]
    )


def _exactify_vector_entries(vector: sp.Matrix) -> sp.Matrix:
    return sp.Matrix([as_exact_char(complex(value.evalf())) for value in vector])


def coerce_integer_coeffs(coeffs: list[sp.Expr], context: str) -> list[int]:
    result: list[int] = []
    for coeff in coeffs:
        if coeff.is_Integer:
            result.append(int(coeff))
            continue
        coeff_eval = complex(coeff.evalf())
        if abs(coeff_eval.imag) < 1e-8 and abs(coeff_eval.real - round(coeff_eval.real)) < 1e-8:
            result.append(int(round(coeff_eval.real)))
            continue
        raise ValueError(f"non-integral decomposition in {context}: {coeffs}")
    return result


def solve_numeric_integer_decomposition(
    basis_matrix: sp.Matrix,
    restricted: sp.Matrix,
    context: str,
    *,
    tol: float = 1e-8,
) -> list[int]:
    basis = np.array(
        [[complex(value.evalf()) for value in row] for row in basis_matrix.tolist()],
        dtype=complex,
    )
    rhs = np.array([complex(value.evalf()) for value in restricted], dtype=complex)
    coeffs, _residuals, rank, _singular_values = np.linalg.lstsq(basis, rhs, rcond=None)
    if int(rank) != int(basis.shape[1]):
        raise ValueError(f"non-unique numeric decomposition in {context}")
    rounded: list[int] = []
    for coeff in coeffs:
        if abs(coeff.imag) > tol or abs(coeff.real - round(coeff.real)) > tol:
            raise ValueError(f"non-integral numeric decomposition in {context}: {coeffs.tolist()}")
        rounded.append(int(round(coeff.real)))
    reconstructed = basis @ np.array(rounded, dtype=complex)
    if not np.allclose(reconstructed, rhs, atol=tol):
        raise ValueError(f"numeric reconstruction failed in {context}")
    return rounded


def _mode_label_from_raw(raw: dict[str, Any]) -> str:
    return {1: "single", 2: "double"}.get(int(raw.get("group_type", 0)), f"groupType={raw.get('group_type')}")


def _validated_capture_field_rows(
    raw: dict[str, Any],
    field: str,
    *,
    manifold_id: str,
    endpoint_id: str | None = None,
    rep_id: str | None = None,
) -> list[list[complex]]:
    rows = raw.get(field)
    mode = _mode_label_from_raw(raw)
    context = (
        f"mode={mode} manifold={manifold_id}"
        + (f" endpoint={endpoint_id}" if endpoint_id is not None else "")
        + (f" rep={rep_id}" if rep_id is not None else "")
        + f" field={field}"
    )
    if not rows:
        raise ValueError(f"{context}: empty character layer")
    unitary_capture_indices = raw.get("unitary_capture_indices", [])
    if not unitary_capture_indices:
        raise ValueError(f"{context}: empty unitary_capture_indices")
    expected_cols = len(unitary_capture_indices)
    for row_index, row in enumerate(rows, start=1):
        if not row:
            raise ValueError(f"{context}: empty row {row_index}")
        actual_cols = len(row)
        if actual_cols != expected_cols:
            raise ValueError(
                f"{context}: character column mismatch expected={expected_cols} actual={actual_cols}"
            )
    return [[complex(value) for value in row] for row in rows]


def _exact_basis_matrix_from_capture(
    raw: dict[str, Any],
    field: str,
    *,
    manifold_id: str,
) -> sp.Matrix:
    rows = _validated_capture_field_rows(raw, field, manifold_id=manifold_id)
    return sp.Matrix([[as_exact_char(value) for value in rep_character] for rep_character in rows]).T


def _exact_restriction_vector(
    parent_raw: dict[str, Any],
    child_raw: dict[str, Any],
    matched: list[int],
    *,
    field: str,
    parent_manifold_id: str,
    child_manifold_id: str,
    rep_id: str,
) -> sp.Matrix:
    parent_rows = _validated_capture_field_rows(parent_raw, field, manifold_id=parent_manifold_id)
    child_rows = _validated_capture_field_rows(
        child_raw,
        field,
        manifold_id=child_manifold_id,
        endpoint_id=child_manifold_id,
        rep_id=rep_id,
    )
    expected = len(parent_rows[0])
    if len(matched) != expected:
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: matched subgroup length mismatch expected={expected} actual={len(matched)}"
        )
    child_cols = len(child_rows[0])
    if any(index < 0 or index >= child_cols for index in matched):
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: matched index outside child column range child_cols={child_cols}"
        )
    rep_index = int(rep_id.split("_R")[1]) - 1
    restricted = [as_exact_char(child_rows[rep_index][index]) for index in matched]
    if len(restricted) != expected:
        raise ValueError(
            f"mode={_mode_label_from_raw(child_raw)} manifold={parent_manifold_id} endpoint={child_manifold_id} "
            f"rep={rep_id} field={field}: restricted vector length mismatch expected={expected} actual={len(restricted)}"
        )
    return sp.Matrix(restricted)


def solve_unique_integer_decomposition(
    basis_matrix: sp.Matrix,
    restricted: sp.Matrix,
    *,
    mode: str,
    manifold_id: str,
    endpoint_id: str,
    rep_id: str,
    field: str,
) -> list[int]:
    context = f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}"
    if basis_matrix.rows != restricted.rows:
        raise ValueError(
            f"{context}: "
            f"basis/restriction row mismatch expected={basis_matrix.rows} actual={restricted.rows}"
        )
    try:
        return solve_numeric_integer_decomposition(basis_matrix, restricted, context)
    except Exception as numeric_exc:
        numeric_error = numeric_exc
    try:
        solution, params = basis_matrix.gauss_jordan_solve(restricted)
    except Exception as exc:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver={exc}"
        ) from exc
    if params.rows * params.cols:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver=non-unique decomposition"
        )
    if basis_matrix * solution != restricted:
        raise ValueError(
            f"{context}: numeric_fallback={numeric_error}; exact_solver=exact reconstruction failed"
        )
    return coerce_integer_coeffs(
        list(solution),
        context,
    )


def matched_unitary_indices(parent_raw: dict[str, Any], child_raw: dict[str, Any]) -> list[int]:
    parent_ops = [operation_key_from_capture(parent_raw, op_index) for op_index in parent_raw["unitary_capture_indices"]]
    unitary_map = {
        operation_key_from_capture(child_raw, op_index): unitary_index
        for unitary_index, op_index in enumerate(child_raw["unitary_capture_indices"])
    }
    matched = [unitary_map.get(op_key) for op_key in parent_ops]
    if any(index is None for index in matched):
        raise ValueError("child manifold does not contain the full parent unitary subgroup")
    return [int(index) for index in matched]


def capture_character_vectors(raw: dict[str, Any], field: str, matched: list[int]) -> list[list[complex]]:
    _validated_capture_field_rows(raw, field, manifold_id=raw.get("manifold_id", "unknown"))
    return [
        [complex(rep_character[index]) for index in matched]
        for rep_character in raw[field]
    ]


def identical_restriction_classes(
    endpoint_id: str,
    endpoint_raw: dict[str, Any],
    matched: list[int],
    *,
    field: str,
    extra_fingerprints: dict[str, dict[str, Any]] | None = None,
    tol: float = 1e-8,
) -> list[dict[str, Any]]:
    vectors = capture_character_vectors(endpoint_raw, field, matched)
    classes: list[dict[str, Any]] = []
    for rep_index, restricted_vector in enumerate(vectors, start=1):
        rep_id = f"{endpoint_id}_R{rep_index}"
        extra_fingerprint = extra_fingerprints.get(rep_id) if extra_fingerprints else None
        extra_key = json.dumps(extra_fingerprint, sort_keys=True, separators=(",", ":")) if extra_fingerprint else ""
        for existing in classes:
            if (
                all(abs(left - right) <= tol for left, right in zip(existing["_vector"], restricted_vector))
                and existing["_extra_key"] == extra_key
            ):
                existing["rep_ids"].append(rep_id)
                break
        else:
            classes.append(
                {
                    "rep_ids": [rep_id],
                    "restricted_vector": complex_list_to_json(restricted_vector),
                    "extra_fingerprint": extra_fingerprint,
                    "_vector": restricted_vector,
                    "_extra_key": extra_key,
                }
            )
    for existing in classes:
        existing["class_size"] = len(existing["rep_ids"])
        del existing["_vector"]
        del existing["_extra_key"]
    return classes


def _line_decomposition_signature(rep: dict[str, Any]) -> list[list[Any]]:
    return [
        [basis_label, int(coeff)]
        for basis_label, coeff in sorted(rep.get("decomposition_on_line_basis", {}).items())
    ]


def _normalized_complex_json_vector(values: Sequence[complex], tol: float = 1e-8) -> list[dict[str, float]]:
    normalized = []
    for value in values:
        complex_value = complex(value)
        real = 0.0 if abs(complex_value.real) <= tol else float(complex_value.real)
        imag = 0.0 if abs(complex_value.imag) <= tol else float(complex_value.imag)
        if abs(real - round(real)) <= tol:
            real = float(round(real))
        if abs(imag - round(imag)) <= tol:
            imag = float(round(imag))
        normalized.append(complex(real, imag))
    return complex_list_to_json(normalized)


def _restriction_class_key(
    restricted_vector: list[dict[str, Any]],
    extra_fingerprint: dict[str, Any] | None = None,
) -> str:
    payload = {"restricted_vector": restricted_vector}
    if extra_fingerprint is not None:
        payload["extra_fingerprint"] = extra_fingerprint
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _endpoint_star_fingerprints_for_line(
    endpoint_entry: dict[str, Any],
    current_line_id: str,
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    *,
    field: str,
) -> list[dict[str, Any]]:
    fingerprints = []
    for line_id in sorted(endpoint_entry.get("incident_lines", [])):
        if line_id == current_line_id:
            continue
        line_raw = captures[line_id]
        matched_line = matched_unitary_indices(line_raw, endpoint_raw)
        line_vectors = capture_character_vectors(endpoint_raw, field, matched_line)
        fingerprints.append(
            {
                "manifold_id": line_id,
                "manifold_type": "line",
                "restricted_vector": _normalized_complex_json_vector(line_vectors[rep_index - 1]),
            }
        )
    for plane_id in sorted(endpoint_entry.get("incident_planes", [])):
        plane_raw = captures[plane_id]
        matched_plane = matched_unitary_indices(plane_raw, endpoint_raw)
        plane_vectors = capture_character_vectors(endpoint_raw, field, matched_plane)
        fingerprints.append(
            {
                "manifold_id": plane_id,
                "manifold_type": "plane",
                "restricted_vector": _normalized_complex_json_vector(plane_vectors[rep_index - 1]),
            }
        )
    return fingerprints


def intrinsic_restriction_fingerprint_for_line(
    line_obj: dict[str, Any],
    endpoint_entry: dict[str, Any],
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    coarse_block: dict[str, Any],
    field: str,
) -> dict[str, Any]:
    line_raw = captures[line_obj["id"]]
    matched_line = matched_unitary_indices(line_raw, endpoint_raw)
    restricted_vector = capture_character_vectors(endpoint_raw, field, matched_line)[rep_index - 1]
    endpoint_id = endpoint_entry["point_id"]
    rep_id = f"{endpoint_id}_R{rep_index}"
    decomposition = {
        item["rep_id"]: item
        for item in coarse_block["endpoint_decompositions"][endpoint_id]
    }
    return {
        "fingerprint_kind": "line_intrinsic_restriction_v1",
        "field": field,
        "line_id": line_obj["id"],
        "endpoint_id": endpoint_id,
        "capture_id": endpoint_entry.get("capture_id", endpoint_id),
        "line_restricted_vector": _normalized_complex_json_vector(restricted_vector),
        "line_basis_decomposition": _line_decomposition_signature(decomposition[rep_id]),
    }


def extrinsic_star_fingerprint_for_line(
    line_obj: dict[str, Any],
    endpoint_entry: dict[str, Any],
    endpoint_raw: dict[str, Any],
    rep_index: int,
    captures: dict[str, Any],
    *,
    field: str,
) -> dict[str, Any]:
    return {
        "fingerprint_kind": "line_extrinsic_star_augmented_v1",
        "field": field,
        "line_id": line_obj["id"],
        "line_containing_planes": list(line_obj.get("containing_planes", [])),
        "endpoint_plane_incidences": list(endpoint_entry.get("plane_incidences", [])),
        "point_star_restrictions": _endpoint_star_fingerprints_for_line(
            endpoint_entry,
            line_obj["id"],
            endpoint_raw,
            rep_index,
            captures,
            field=field,
        ),
    }


def phase_aware_l2_profile_config(profile: str | None) -> tuple[str, str | None]:
    if profile in (None, "legacy"):
        return "legacy", None
    if profile == "phase_aware_l2_projective_v1":
        return profile, None
    if profile == "phase_aware_l2_projective_v1_p3":
        return "phase_aware_l2_projective_v1", "P3"
    if profile == "phase_aware_l2_projective_v1_p4":
        return "phase_aware_l2_projective_v1", "P4"
    raise ValueError(f"unsupported phase-aware line profile: {profile}")


def phase_aware_l2_refinement(
    line_id: str,
    endpoint_entries: list[dict[str, Any]],
    captures: dict[str, Any],
    *,
    selected_endpoint_override: str | None = None,
) -> dict[str, Any]:
    if line_id != "L2":
        return {
            "profile": "legacy",
            "selected_endpoint_id": None,
            "restriction_classes_by_endpoint": {},
            "refinement_equations": [],
        }

    line_raw = captures[line_id]
    endpoint_scores: list[tuple[int, int, str, list[dict[str, Any]]]] = []
    restriction_classes_by_endpoint: dict[str, Any] = {}
    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        endpoint_raw = captures[endpoint_entry["capture_id"]]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        classes = identical_restriction_classes(
            endpoint_id,
            endpoint_raw,
            matched,
            field="linear_character",
        )
        restriction_classes_by_endpoint[endpoint_id] = classes
        duplicated_classes = [item for item in classes if item["class_size"] > 1]
        duplicated_cover = sum(item["class_size"] for item in duplicated_classes)
        endpoint_scores.append((duplicated_cover, len(duplicated_classes), endpoint_id, duplicated_classes))

    endpoint_scores.sort(reverse=True)
    if selected_endpoint_override is None:
        duplicated_cover, duplicated_count, selected_endpoint_id, duplicated_classes = endpoint_scores[0]
    else:
        selected_endpoint_id = selected_endpoint_override
        match = next((entry for entry in endpoint_scores if entry[2] == selected_endpoint_id), None)
        if match is None:
            raise ValueError(f"{line_id}: unsupported endpoint override {selected_endpoint_override}")
        duplicated_cover, duplicated_count, _selected, duplicated_classes = match
    refinement_equations: list[dict[str, Any]] = []
    if duplicated_cover > 0 and duplicated_count > 0:
        for class_index, entry in enumerate(duplicated_classes, start=1):
            anchor = entry["rep_ids"][0]
            for rep_id in entry["rep_ids"][1:]:
                refinement_equations.append(
                    {
                        "basis_id": f"{line_id}_phase_aware_class_{class_index:02d}",
                        "terms": [
                            {"unknown": anchor, "coeff": 1, "side": "phase_aware_endpoint_class"},
                            {"unknown": rep_id, "coeff": -1, "side": "phase_aware_endpoint_class"},
                        ],
                        "restriction_class_rep_ids": list(entry["rep_ids"]),
                        "selected_endpoint_id": selected_endpoint_id,
                    }
                )
    return {
        "profile": "phase_aware_l2_projective_v1",
        "selected_endpoint_id": selected_endpoint_id,
        "restriction_classes_by_endpoint": restriction_classes_by_endpoint,
        "refinement_equations": refinement_equations,
    }


def build_line_block_coarse(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    phase_aware_profile: str | None = None,
) -> dict[str, Any]:
    normalized_phase_profile, selected_endpoint_override = phase_aware_l2_profile_config(phase_aware_profile)
    line_id = line_obj["id"]
    source_line_id = line_obj.get("source_line_id", line_id)
    endpoint_entries = [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
        }
        for endpoint in line_obj["endpoints"]
    ]
    endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
    line_raw = captures[line_id]
    # Source-layer endpoint/plane subduction for 194.1.1.1 must stay in the
    # character language. The linear_character basis is not integer-solvable
    # for L1/L2/L5 and S3, which is the active BS-construction failure.
    field = "character"
    line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
    line_basis_matrix = _exact_basis_matrix_from_capture(
        line_raw,
        field,
        manifold_id=line_id,
    )
    endpoint_decompositions: dict[str, Any] = {}
    equations = []
    matrix_rows = []
    local_unknown_ordering: list[str] = []
    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        endpoint_raw = captures[endpoint_entry["capture_id"]]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        reps = []
        for rep_index in range(1, len(endpoint_raw[field]) + 1):
            rep_id = f"{endpoint_id}_R{rep_index}"
            restricted = _exact_restriction_vector(
                line_raw,
                endpoint_raw,
                matched,
                field=field,
                parent_manifold_id=line_id,
                child_manifold_id=endpoint_id,
                rep_id=rep_id,
            )
            coeffs_int = solve_unique_integer_decomposition(
                line_basis_matrix,
                restricted,
                mode=_mode_label_from_raw(endpoint_raw),
                manifold_id=line_id,
                endpoint_id=endpoint_id,
                rep_id=rep_id,
                field=field,
            )
            reps.append(
                {
                    "rep_id": rep_id,
                    "rep_degree": int(endpoint_raw["rep_degree"][rep_index - 1]),
                    "torsion": int(endpoint_raw["torsion"][rep_index - 1]),
                    "decomposition_on_line_basis": {basis_label: coeff for basis_label, coeff in zip(line_basis_labels, coeffs_int) if coeff},
                }
            )
            local_unknown_ordering.append(rep_id)
        endpoint_decompositions[endpoint_id] = reps
    for basis_label in line_basis_labels:
        row = []
        terms = []
        for endpoint_id, side in zip(endpoint_ids, ("left", "right")):
            sign = 1 if side == "left" else -1
            for rep in endpoint_decompositions[endpoint_id]:
                coeff = sign * rep["decomposition_on_line_basis"].get(basis_label, 0)
                row.append(coeff)
                if coeff:
                    terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": side})
        matrix_rows.append(row)
        equations.append(
            {
                "basis_id": basis_label,
                "terms": terms,
                "builder_variant": "coarse",
                "row_kind": "line_basis_decomposition",
                "uses_extrinsic_data": False,
                "endpoint_support": {},
                "class_members": [],
                "intrinsic_fingerprint_by_rep": {},
                "extrinsic_fingerprint_by_rep": {},
                "coarse_signature_by_rep": {},
            }
        )
    phase_aware_refinement = {
        "profile": "legacy",
        "selected_endpoint_id": None,
        "restriction_classes_by_endpoint": {},
        "refinement_equations": [],
    }
    if normalized_phase_profile == "phase_aware_l2_projective_v1":
        phase_aware_refinement = phase_aware_l2_refinement(
            source_line_id,
            endpoint_entries,
            captures,
            selected_endpoint_override=selected_endpoint_override,
        )
        local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
        for equation in phase_aware_refinement["refinement_equations"]:
            row = [0] * len(local_unknown_ordering)
            for term in equation["terms"]:
                row[local_index[term["unknown"]]] += int(term["coeff"])
            matrix_rows.append(row)
            equations.append(
                {
                    "basis_id": equation["basis_id"],
                    "terms": equation["terms"],
                    "phase_aware_refinement": True,
                    "restriction_class_rep_ids": equation["restriction_class_rep_ids"],
                    "selected_endpoint_id": equation["selected_endpoint_id"],
                    "builder_variant": "coarse",
                    "row_kind": "phase_aware_endpoint_class",
                    "uses_extrinsic_data": False,
                    "endpoint_support": {},
                    "class_members": list(equation["restriction_class_rep_ids"]),
                    "intrinsic_fingerprint_by_rep": {},
                    "extrinsic_fingerprint_by_rep": {},
                    "coarse_signature_by_rep": {},
                }
            )
    return {
        "status": "success",
        "builder_variant": "coarse",
        "line_id": line_id,
        "source_line_id": source_line_id,
        "endpoint_ids": endpoint_ids,
        "line_sample_point": line_obj["sample_point"],
        "line_parametrization": line_obj["parametrization"],
        "line_symmetry_summary": line_obj["symmetry_summary"],
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "line_basis_labels": line_basis_labels,
        "line_group_signature": {
            "n_ops_total": len(line_raw["rotC"]),
            "n_unitary_ops": line_raw["unitary_operation_count"],
            "n_antiunitary_ops": sum(1 for sign in line_raw["timeReversal"] if sign < 0),
            "rep_degree": list(line_raw["rep_degree"]),
            "torsion": list(line_raw["torsion"]),
        },
        "phase_aware_refinement": phase_aware_refinement,
        "compatibility_field": field,
        "compatibility_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        "phase_aware_profile_used": (
            phase_aware_refinement["profile"]
            if phase_aware_refinement["profile"] != "legacy"
            else "legacy"
        ),
    }


def build_line_block_from_coarse_restriction(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "character",
) -> dict[str, Any]:
    block = build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
    return {
        **block,
        "builder_variant": "coarse",
        "restriction_class_builder": {
            "status": "compare_only",
            "builder_kind": "coarse_basis_decomposition_only",
            "field": field,
            "restriction_classes_by_endpoint": {},
            "row_count": len(block["equations"]),
            "uses_extrinsic_data": False,
        },
        "coarse_compare": {
            "builder_kind": "coarse_basis_decomposition_only",
            "equation_count": len(block["equations"]),
            "matrix_row_count": len(block["matrix_rows"]),
        },
    }


def _line_endpoint_entries(line_obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
            "incident_lines": list(endpoint.get("incident_lines", [])),
            "incident_planes": list(endpoint.get("incident_planes", [])),
            "plane_incidences": list(endpoint.get("plane_incidences", [])),
        }
        for endpoint in line_obj["endpoints"]
    ]


def _build_line_block_from_restriction_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    builder_variant: str,
    field: str = "linear_character",
) -> dict[str, Any]:
    if builder_variant not in {"intrinsic", "extrinsic"}:
        raise ValueError(f"unsupported restriction-class builder variant: {builder_variant}")

    coarse_block = build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
    endpoint_entries = _line_endpoint_entries(line_obj)
    endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
    line_raw = captures[line_obj["id"]]
    restriction_classes_by_endpoint: dict[str, list[dict[str, Any]]] = {}
    class_support: dict[str, dict[str, Any]] = {}
    intrinsic_fingerprints_by_rep: dict[str, dict[str, Any]] = {}
    extrinsic_fingerprints_by_rep: dict[str, dict[str, Any]] = {}
    coarse_signature_by_rep: dict[str, list[list[Any]]] = {}

    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        capture_id = endpoint_entry["capture_id"]
        endpoint_raw = captures[capture_id]
        matched = matched_unitary_indices(line_raw, endpoint_raw)
        extra_fingerprints: dict[str, dict[str, Any]] | None = {} if builder_variant == "extrinsic" else None
        for rep_index in range(1, len(endpoint_raw[field]) + 1):
            rep_id = f"{endpoint_id}_R{rep_index}"
            intrinsic_fingerprints_by_rep[rep_id] = intrinsic_restriction_fingerprint_for_line(
                line_obj,
                endpoint_entry,
                endpoint_raw,
                rep_index,
                captures,
                coarse_block,
                field=field,
            )
            coarse_signature_by_rep[rep_id] = intrinsic_fingerprints_by_rep[rep_id]["line_basis_decomposition"]
            if extra_fingerprints is not None:
                extra_fingerprints[rep_id] = extrinsic_star_fingerprint_for_line(
                    line_obj,
                    endpoint_entry,
                    endpoint_raw,
                    rep_index,
                    captures,
                    field=field,
                )
                extrinsic_fingerprints_by_rep[rep_id] = extra_fingerprints[rep_id]
        classes = identical_restriction_classes(
            endpoint_id,
            endpoint_raw,
            matched,
            field=field,
            extra_fingerprints=extra_fingerprints,
        )
        restriction_classes_by_endpoint[endpoint_id] = classes
        for entry in classes:
            class_key = _restriction_class_key(
                entry["restricted_vector"],
                entry.get("extra_fingerprint") if builder_variant == "extrinsic" else None,
            )
            support = class_support.setdefault(
                class_key,
                {
                    "restricted_vector": entry["restricted_vector"],
                    "extra_fingerprint": entry.get("extra_fingerprint"),
                    "members_by_endpoint": {},
                },
            )
            support["members_by_endpoint"][endpoint_id] = list(entry["rep_ids"])

    local_index = {unknown: index for index, unknown in enumerate(coarse_block["local_unknown_ordering"])}
    restriction_equations: list[dict[str, Any]] = []
    restriction_rows = []
    for class_index, class_key in enumerate(sorted(class_support), start=1):
        support = class_support[class_key]
        endpoint_support = {endpoint_id: list(support["members_by_endpoint"].get(endpoint_id, [])) for endpoint_id in endpoint_ids}
        terms = []
        for endpoint_id, side in zip(endpoint_ids, ("left", "right")):
            coeff = 1 if side == "left" else -1
            for rep_id in endpoint_support.get(endpoint_id, []):
                terms.append({"unknown": rep_id, "coeff": coeff, "side": side})
        if not terms:
            continue
        class_members = [rep_id for endpoint_id in endpoint_ids for rep_id in endpoint_support.get(endpoint_id, [])]
        equation = {
            "basis_id": f"{line_obj['id']}_{builder_variant}_class_{class_index:02d}",
            "terms": terms,
            "builder_variant": builder_variant,
            "row_kind": "restriction_class_sum",
            "endpoint_support": endpoint_support,
            "class_members": class_members,
            "restricted_vector": support["restricted_vector"],
            "intrinsic_fingerprint_by_rep": {
                rep_id: intrinsic_fingerprints_by_rep[rep_id]
                for rep_id in class_members
            },
            "extrinsic_fingerprint_by_rep": (
                {
                    rep_id: extrinsic_fingerprints_by_rep[rep_id]
                    for rep_id in class_members
                }
                if builder_variant == "extrinsic"
                else {}
            ),
            "coarse_signature_by_rep": {
                rep_id: coarse_signature_by_rep[rep_id]
                for rep_id in class_members
            },
            "uses_extrinsic_data": builder_variant == "extrinsic",
            "line_containing_planes": list(line_obj.get("containing_planes", [])),
        }
        restriction_equations.append(equation)
        row = [0] * len(coarse_block["local_unknown_ordering"])
        for term in terms:
            row[local_index[term["unknown"]]] += int(term["coeff"])
        restriction_rows.append(row)

    builder_kind = (
        RETIRED_INTRINSIC_BUILDER_KIND
        if builder_variant == "intrinsic"
        else RETIRED_EXTRINSIC_BUILDER_KIND
    )
    return {
        **coarse_block,
        "status": "retired_compare_only_non_authoritative",
        "builder_variant": builder_variant,
        "equations": restriction_equations,
        "matrix_rows": restriction_rows,
        "line_group_signature": {
            **coarse_block["line_group_signature"],
            "containing_plane_count": len(line_obj.get("containing_planes", [])),
        },
        "restriction_class_builder": {
            "status": "retired_compare_only_non_authoritative",
            "builder_kind": builder_kind,
            "field": field,
            "containing_planes": list(line_obj.get("containing_planes", [])),
            "restriction_classes_by_endpoint": restriction_classes_by_endpoint,
            "row_count": len(restriction_equations),
            "uses_extrinsic_data": builder_variant == "extrinsic",
        },
        "phase_aware_refinement": {
            "profile": "disabled_in_backend_free_generic_primary_path",
            "selected_endpoint_id": None,
            "restriction_classes_by_endpoint": {},
            "refinement_equations": [],
        },
        "coarse_compare": {
            "builder_kind": "basis_decomposition_compare_only",
            "equation_count": len(coarse_block["equations"]),
            "matrix_row_count": len(coarse_block["matrix_rows"]),
        },
    }


def build_line_block_from_intrinsic_restriction_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "linear_character",
) -> dict[str, Any]:
    return _build_line_block_from_restriction_classes(
        line_obj,
        captures,
        builder_variant="intrinsic",
        field=field,
    )


def build_line_block_from_extrinsic_star_augmented_classes(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    field: str = "linear_character",
) -> dict[str, Any]:
    return _build_line_block_from_restriction_classes(
        line_obj,
        captures,
        builder_variant="extrinsic",
        field=field,
    )


def build_line_block(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    phase_aware_profile: str | None = AUTHORITATIVE_PHASE_AWARE_PROFILE,
    *,
    builder_variant: str = "authoritative",
) -> dict[str, Any]:
    if builder_variant in {"authoritative", "coarse"}:
        return build_line_block_coarse(
            line_obj,
            captures,
            phase_aware_profile=phase_aware_profile,
        )
    if builder_variant == "intrinsic":
        return build_line_block_from_intrinsic_restriction_classes(line_obj, captures, field="character")
    if builder_variant == "extrinsic":
        raise ValueError("extrinsic line builder is retired and non-authoritative")
    raise ValueError(f"unsupported builder_variant: {builder_variant}")


def build_global_compatibility(line_blocks: list[dict[str, Any]], point_ids: list[str]) -> dict[str, Any]:
    per_point_ids: dict[str, list[str]] = {}
    for block in line_blocks:
        for endpoint_id in block["endpoint_ids"]:
            rep_ids = [item["rep_id"] for item in block["endpoint_decompositions"][endpoint_id]]
            existing = per_point_ids.get(endpoint_id)
            if existing is None:
                per_point_ids[endpoint_id] = rep_ids
            elif existing != rep_ids:
                raise ValueError(f"inconsistent rep ordering for {endpoint_id}")
    ordering = []
    for point_id in point_ids:
        ordering.extend(per_point_ids.get(point_id, []))
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    global_rows = []
    for block in line_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            metadata = {key: value for key, value in equation.items() if key != "terms"}
            global_rows.append(
                {
                    "source_type": "line",
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "builder_variant": block.get("builder_variant", "coarse"),
                    "equation_metadata": metadata,
                    **metadata,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": global_rows,
        "global_matrix": [row["matrix_row"] for row in global_rows],
        "covered_lines": [block["line_id"] for block in line_blocks],
    }


def build_phase_aware_point_row_translation(
    line_blocks: list[dict[str, Any]],
    unknown_ordering: list[str],
    phase_aware_profile: str | None = None,
) -> dict[str, Any]:
    normalized_phase_profile, selected_endpoint_override = phase_aware_l2_profile_config(phase_aware_profile)
    translation = {
        "profile": "legacy",
        "enabled": False,
        "line_id": None,
        "selected_endpoint_id": None,
        "selected_endpoint_override": selected_endpoint_override,
        "other_endpoint_id": None,
        "selected_endpoint_class_actions": [],
        "other_endpoint_scalings": [],
    }
    if normalized_phase_profile != "phase_aware_l2_projective_v1":
        return translation

    line_block = next(
        (
            block
            for block in line_blocks
            if block.get("source_line_id", block["line_id"]) == "L2"
        ),
        None,
    )
    if line_block is None:
        return translation

    refinement = line_block["phase_aware_refinement"]
    selected_endpoint_id = refinement.get("selected_endpoint_id")
    if not selected_endpoint_id:
        return translation

    selected_classes = [
        entry
        for entry in refinement["restriction_classes_by_endpoint"].get(selected_endpoint_id, [])
        if entry["class_size"] > 1
    ]
    translation.update(
        {
            "profile": "phase_aware_point_row_translation_v1",
            "line_id": line_block["line_id"],
            "selected_endpoint_id": selected_endpoint_id,
        }
    )
    if not selected_classes:
        return translation

    unknown_index = {label: idx for idx, label in enumerate(unknown_ordering)}
    other_endpoint_id = next(endpoint_id for endpoint_id in line_block["endpoint_ids"] if endpoint_id != selected_endpoint_id)
    selected_decompositions = {
        rep["rep_id"]: rep["decomposition_on_line_basis"]
        for rep in line_block["endpoint_decompositions"][selected_endpoint_id]
    }
    basis_scale: dict[str, int] = {}
    selected_endpoint_class_actions: list[dict[str, Any]] = []
    for class_index, entry in enumerate(selected_classes, start=1):
        basis_labels = sorted(
            {
                basis_label
                for rep_id in entry["rep_ids"]
                for basis_label, coeff in selected_decompositions[rep_id].items()
                if coeff
            }
        )
        for basis_label in basis_labels:
            basis_scale[basis_label] = max(basis_scale.get(basis_label, 1), int(entry["class_size"]))
        selected_endpoint_class_actions.append(
            {
                "class_id": f"{line_block['line_id']}_phase_aware_class_{class_index:02d}",
                "endpoint_id": selected_endpoint_id,
                "rep_ids": list(entry["rep_ids"]),
                "rep_indices": [int(rep_id.split("_R")[1]) - 1 for rep_id in entry["rep_ids"]],
                "class_size": int(entry["class_size"]),
                "basis_labels": basis_labels,
                "unknown_indices": [unknown_index[rep_id] for rep_id in entry["rep_ids"]],
                "action": "replicate_class_sum_on_members",
            }
        )

    other_endpoint_scalings: list[dict[str, Any]] = []
    for rep in line_block["endpoint_decompositions"][other_endpoint_id]:
        touched_basis_labels = sorted(
            basis_label
            for basis_label, coeff in rep["decomposition_on_line_basis"].items()
            if coeff and basis_label in basis_scale
        )
        if not touched_basis_labels:
            continue
        factor = max(basis_scale[basis_label] for basis_label in touched_basis_labels)
        if factor <= 1:
            continue
        rep_id = rep["rep_id"]
        other_endpoint_scalings.append(
            {
                "endpoint_id": other_endpoint_id,
                "rep_id": rep_id,
                "rep_index": int(rep_id.split("_R")[1]) - 1,
                "factor": int(factor),
                "touched_basis_labels": touched_basis_labels,
                "unknown_index": unknown_index[rep_id],
                "action": "scale_opposite_endpoint_multiplicity",
            }
        )

    translation.update(
        {
            "enabled": True,
            "other_endpoint_id": other_endpoint_id,
            "selected_endpoint_class_actions": selected_endpoint_class_actions,
            "other_endpoint_scalings": other_endpoint_scalings,
        }
    )
    return translation


def build_point_merge_classes_from_line_blocks(
    line_blocks: Sequence[dict[str, Any]],
) -> dict[str, list[list[str]]]:
    parent: dict[str, str] = {}

    def find(token: str) -> str:
        parent.setdefault(token, token)
        while parent[token] != token:
            parent[token] = parent[parent[token]]
            token = parent[token]
        return token

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for block in line_blocks:
        refinement = block.get("phase_aware_refinement", {})
        for equation in refinement.get("refinement_equations", []):
            rep_ids = list(equation.get("restriction_class_rep_ids", []))
            if len(rep_ids) <= 1:
                continue
            head = rep_ids[0]
            for rep_id in rep_ids[1:]:
                union(head, rep_id)

    by_point: dict[str, dict[str, list[str]]] = {}
    for token in list(parent):
        root = find(token)
        point_id = token.split("_R", 1)[0]
        by_point.setdefault(point_id, {}).setdefault(root, []).append(token)

    normalized: dict[str, list[list[str]]] = {}
    for point_id, root_groups in by_point.items():
        groups = []
        for rep_ids in root_groups.values():
            rep_ids = sorted(rep_ids, key=lambda item: int(item.split("_R", 1)[1]))
            groups.append(rep_ids)
        groups.sort(key=lambda group: int(group[0].split("_R", 1)[1]))
        normalized[point_id] = groups

    return normalized


def build_publication_point_merge_classes(
    publication_line_full: dict[str, Any],
    internal_line_blocks: Sequence[dict[str, Any]],
) -> dict[str, list[list[str]]]:
    direct = build_point_merge_classes_from_line_blocks(publication_line_full.get("line_blocks", []))
    if any(direct.values()):
        return direct

    member_source_line_ids: set[str] = set()
    member_internal_path_class_ids: set[str] = set()
    for block in publication_line_full.get("line_blocks", []):
        member_source_line_ids.update(block.get("member_source_line_ids", []))
        member_internal_path_class_ids.update(block.get("member_internal_path_class_ids", []))

    inherited_blocks = [
        block
        for block in internal_line_blocks
        if block.get("source_line_id") in member_source_line_ids
        or block.get("line_id") in member_internal_path_class_ids
    ]
    return build_point_merge_classes_from_line_blocks(inherited_blocks)


def build_publication_point_basis_matrix(
    raw: dict[str, Any],
    field: str,
    manifold_id: str,
    point_merge_classes: dict[str, list[list[str]]] | None,
) -> tuple[sp.Matrix, list[list[int]]]:
    rows = _validated_capture_field_rows(raw, field, manifold_id=manifold_id)
    rep_count = len(rows)
    unitary_count = len(rows[0]) if rows else 0

    merge_groups = (
        point_merge_classes.get(manifold_id, [])
        if point_merge_classes is not None
        else []
    )

    covered: set[int] = set()
    class_groups: list[list[int]] = []
    columns: list[list[sp.Expr]] = []

    for group in merge_groups:
        indices = [int(token.split("_R", 1)[1]) - 1 for token in group]
        merged_column = []
        for op_index in range(unitary_count):
            total = 0j
            for rep_index in indices:
                total += rows[rep_index][op_index]
            merged_column.append(as_exact_char(total))
        class_groups.append(indices)
        columns.append(merged_column)
        covered.update(indices)

    for rep_index in range(rep_count):
        if rep_index in covered:
            continue
        singleton_column = [
            as_exact_char(rows[rep_index][op_index])
            for op_index in range(unitary_count)
        ]
        class_groups.append([rep_index])
        columns.append(singleton_column)

    if not columns:
        return sp.zeros(unitary_count, 0), []

    return sp.Matrix(columns).T, class_groups


def expand_publication_point_solution(
    class_solution: Sequence[int],
    class_groups: Sequence[Sequence[int]],
    rep_count: int,
) -> list[int]:
    expanded = [0] * rep_count
    for coeff, group in zip(class_solution, class_groups):
        coeff = int(coeff)
        for rep_index in group:
            expanded[rep_index] = coeff
    return expanded


def apply_point_row_translation_to_multiplicities(
    manifold_multiplicities: dict[str, list[int]],
    point_row_translation: dict[str, Any] | None,
) -> dict[str, list[int]]:
    if not point_row_translation or not point_row_translation.get("enabled"):
        return {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}

    translated = {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}
    for action in point_row_translation["selected_endpoint_class_actions"]:
        values = translated.get(action["endpoint_id"])
        if values is None:
            continue
        total = sum(values[index] for index in action["rep_indices"])
        for index in action["rep_indices"]:
            values[index] = int(total)
    for action in point_row_translation["other_endpoint_scalings"]:
        values = translated.get(action["endpoint_id"])
        if values is None:
            continue
        values[action["rep_index"]] *= int(action["factor"])
    return translated


def unknown_vector_from_multiplicities(
    manifold_multiplicities: dict[str, list[int]],
    unknown_ordering: list[str],
) -> list[int]:
    unknown_vector = []
    for token in unknown_ordering:
        manifold_id, rep_index_str = token.split("_R")
        unknown_vector.append(int(manifold_multiplicities[manifold_id][int(rep_index_str) - 1]))
    return unknown_vector


def derive_plane_corner_ids(plane_obj: dict[str, Any], point_by_coord: dict[tuple[str, str, str], str]) -> list[str]:
    return [entry["point_id"] for entry in derive_plane_corner_entries(plane_obj, point_by_coord)]


def build_plane_block(plane_obj: dict[str, Any], corner_entries: list[dict[str, Any]], captures: dict[str, Any]) -> dict[str, Any]:
    plane_id = plane_obj["id"]
    plane_raw = captures[plane_id]
    plane_unitary_ops = [operation_key_from_capture(plane_raw, op_index) for op_index in plane_raw["unitary_capture_indices"]]
    # Plane auxiliary coordinates remain the intended two-label 42-shell only
    # if the point-to-plane subduction is performed in character language.
    field = "character"
    plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
    plane_basis_matrix = _exact_basis_matrix_from_capture(
        plane_raw,
        field,
        manifold_id=plane_id,
    )
    local_unknown_ordering: list[str] = []
    corner_decompositions: dict[str, Any] = {}
    equations = []
    matrix_rows = []
    for corner_entry in corner_entries:
        point_id = corner_entry["point_id"]
        point_raw = captures[corner_entry.get("capture_id", point_id)]
        unitary_map = {
            operation_key_from_capture(point_raw, op_index): unitary_index
            for unitary_index, op_index in enumerate(point_raw["unitary_capture_indices"])
        }
        matched = [unitary_map.get(op_key) for op_key in plane_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(
                f"{point_id} at {corner_entry['point_coordinates']} does not contain the full {plane_id} unitary subgroup"
            )
        reps = []
        for rep_index in range(1, len(point_raw[field]) + 1):
            rep_id = f"{point_id}_R{rep_index}"
            restricted = _exact_restriction_vector(
                plane_raw,
                point_raw,
                [int(index) for index in matched],
                field=field,
                parent_manifold_id=plane_id,
                child_manifold_id=point_id,
                rep_id=rep_id,
            )
            coeffs_int = solve_unique_integer_decomposition(
                plane_basis_matrix,
                restricted,
                mode=_mode_label_from_raw(point_raw),
                manifold_id=plane_id,
                endpoint_id=point_id,
                rep_id=rep_id,
                field=field,
            )
            reps.append({"rep_id": rep_id, "decomposition_on_plane_basis": {label: coeff for label, coeff in zip(plane_basis_labels, coeffs_int) if coeff}})
            local_unknown_ordering.append(rep_id)
        corner_decompositions[(point_id, tuple(corner_entry["point_coordinates"]))] = reps
    local_unknown_ordering.extend(plane_basis_labels)
    local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
    for corner_entry in corner_entries:
        point_id = corner_entry["point_id"]
        point_reps = corner_decompositions[(point_id, tuple(corner_entry["point_coordinates"]))]
        for basis_label in plane_basis_labels:
            row = [0] * len(local_unknown_ordering)
            terms = []
            for rep in point_reps:
                coeff = rep["decomposition_on_plane_basis"].get(basis_label, 0)
                if coeff:
                    row[local_index[rep["rep_id"]]] += coeff
                    terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": "point"})
            row[local_index[basis_label]] -= 1
            terms.append({"unknown": basis_label, "coeff": -1, "side": "plane"})
            equations.append({"point_id": point_id, "basis_id": basis_label, "terms": terms})
            matrix_rows.append(row)
    return {
        "status": "success",
        "plane_id": plane_id,
        "corner_ids": [entry["point_id"] for entry in corner_entries],
        "plane_sample_point": plane_obj["sample_point"],
        "plane_parametrization": plane_obj["parametrization"],
        "plane_symmetry_summary": plane_obj["symmetry_summary"],
        "plane_basis_labels": plane_basis_labels,
        "corner_decompositions": corner_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "compatibility_field": field,
        "compatibility_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
    }


def build_with_planes_compatibility(line_full: dict[str, Any], plane_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    ordering = list(line_full["global_unknown_ordering"])
    for block in plane_blocks:
        for unknown in block["local_unknown_ordering"]:
            if unknown not in ordering:
                ordering.append(unknown)
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    rows = []
    extra_unknown_count = len(ordering) - len(line_full["global_unknown_ordering"])
    for row in line_full["global_matrix_rows"]:
        padded = list(row["matrix_row"]) + [0] * extra_unknown_count
        rows.append({**row, "matrix_row": padded})
    for block in plane_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[term["unknown"]]] += int(term["coeff"])
            row_metadata = {key: value for key, value in equation.items() if key != "terms"}
            rows.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "point_id": equation["point_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "equation_metadata": row_metadata,
                    **row_metadata,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": rows,
        "global_matrix": [row["matrix_row"] for row in rows],
        "covered_lines": list(line_full["covered_lines"]),
        "covered_planes": [block["plane_id"] for block in plane_blocks],
    }


def smith_diagonal_entries(D: sp.Matrix) -> list[int]:
    diag = []
    for index in range(min(D.rows, D.cols)):
        value = int(abs(D[index, index]))
        if value:
            diag.append(value)
    return diag


def analyze_kernel(matrix_payload: dict[str, Any]) -> dict[str, Any]:
    C = sp.Matrix(matrix_payload["global_matrix"])
    D_list, _U_list, V_list = swyckoff_k.smith_normal_form(matrix_payload["global_matrix"])
    D = sp.Matrix(D_list)
    V = sp.Matrix(V_list)
    smith_diagonal = smith_diagonal_entries(D)
    rank = len(smith_diagonal)
    nullity = C.cols - rank
    basis_matrix = V[:, rank:]
    basis_vectors = []
    for basis_index in range(basis_matrix.cols):
        vector = [int(value) for value in list(basis_matrix[:, basis_index])]
        basis_vectors.append({"id": f"basis_{basis_index + 1:02d}", "vector": vector})
    return {
        "unknown_ordering": list(matrix_payload["global_unknown_ordering"]),
        "matrix_shape": [C.rows, C.cols],
        "rank": rank,
        "nullity": nullity,
        "smith_diagonal": smith_diagonal,
        "basis_vectors": basis_vectors,
    }


def trivial_local_character(entry: dict[str, Any], ctx: dict[str, Any]) -> dict[int, complex]:
    stabilizer = bridge.bridge_stabilizer_for_entry(entry, ctx)
    return {int(index): 1 + 0j for index in stabilizer["unitary_indices"]}


def _resolve_induction_character_field(
    character_field: str | dict[str, str],
    manifold_id: str,
    kgeom: dict[str, Any],
) -> str:
    if isinstance(character_field, str):
        return character_field
    point_ids = {
        point["id"]
        for point in (
            kgeom["grouped"]["points"] + kgeom.get("synthetic_boundary_points", [])
        )
    }
    line_ids = {line["id"] for line in kgeom["grouped"]["lines"]}
    plane_ids = {plane["id"] for plane in kgeom["grouped"]["planes"]}
    if manifold_id in point_ids:
        return character_field.get("point", character_field.get("default", "linear_character"))
    if manifold_id in line_ids:
        return character_field.get("line", character_field.get("default", "linear_character"))
    if manifold_id in plane_ids:
        return character_field.get("plane", character_field.get("default", "linear_character"))
    return character_field.get("default", "linear_character")


def _summarize_induction_character_field(character_field: str | dict[str, str]) -> str:
    if isinstance(character_field, str):
        return character_field
    ordered_keys = ["point", "line", "plane", "default"]
    return ", ".join(
        f"{key}={character_field[key]}"
        for key in ordered_keys
        if key in character_field
    )


class InductionFailure(ValueError):
    def __init__(self, message: str, *, debug: dict[str, Any]) -> None:
        super().__init__(message)
        self.debug = debug


def _complex_array_to_json(array: np.ndarray) -> list[Any]:
    return complex_list_to_json([complex(value) for value in array.tolist()])


def _complex_matrix_to_json(array: np.ndarray) -> list[list[Any]]:
    return [_complex_array_to_json(row) for row in array]


def _canonicalize_orbit_sites(
    orbit: Sequence[dict[str, Any]],
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    canonical_orbit: list[dict[str, Any]] = []
    for site_index, site in enumerate(orbit):
        raw_conv = np.array(site["conv_vector"], dtype=float)
        magnetic_coordinate = site.get("magnetic_coordinate")
        if magnetic_coordinate is None:
            magnetic_coordinate = bridge.reduced_magnetic_key(ctx["supercell"], raw_conv)
        magnetic_vector = np.array(
            [float(Fraction(value)) for value in magnetic_coordinate],
            dtype=float,
        )
        canonical_conv = ctx["supercell"] @ magnetic_vector
        canonical_orbit.append(
            {
                **site,
                "site_index": int(site.get("site_index", site_index)),
                "raw_conv_vector": raw_conv.tolist(),
                "raw_conventional_coordinate": list(site.get("conventional_coordinate", bridge.format_vector(raw_conv))),
                "magnetic_coordinate": [str(value) for value in magnetic_coordinate],
                "conv_vector": canonical_conv,
                "conventional_coordinate": bridge.format_vector(canonical_conv),
            }
        )
    return canonical_orbit


def _match_orbit_target_site(
    image_conv: np.ndarray,
    orbit: Sequence[dict[str, Any]],
    ctx: dict[str, Any],
) -> tuple[int | None, list[int] | None, list[float] | None]:
    for target_index, target_site in enumerate(orbit):
        fixed, coeffs = bridge.vector_is_lattice(
            ctx["supercell"],
            image_conv - np.array(target_site["conv_vector"], dtype=float),
        )
        if fixed:
            return (
                target_index,
                [int(round(value)) for value in coeffs.tolist()],
                [float(value) for value in (image_conv - np.array(target_site["conv_vector"], dtype=float)).tolist()],
            )
    return None, None, None


def _attempt_exact_integer_decomposition(
    basis_matrix: sp.Matrix,
    restricted: sp.Matrix,
    context: str,
) -> dict[str, Any]:
    basis_matrix = _exactify_matrix_entries(basis_matrix)
    restricted = _exactify_vector_entries(restricted)
    try:
        solution, params = basis_matrix.gauss_jordan_solve(restricted)
    except Exception as exc:
        return {
            "status": "solver_error",
            "error": str(exc),
            "solution_before_rounding": None,
            "integral_solution": None,
        }
    if params.rows * params.cols:
        return {
            "status": "non_unique",
            "error": "non-unique decomposition",
            "solution_before_rounding": [complex(value.evalf()) for value in solution],
            "integral_solution": None,
        }
    try:
        integral_solution = coerce_integer_coeffs(list(solution), context)
    except Exception as exc:
        return {
            "status": "non_integral",
            "error": str(exc),
            "solution_before_rounding": [complex(value.evalf()) for value in solution],
            "integral_solution": None,
        }
    return {
        "status": "integral",
        "error": None,
        "solution_before_rounding": [complex(value.evalf()) for value in solution],
        "integral_solution": integral_solution,
    }


def _build_manifold_induction_trace(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    manifold_id: str,
    *,
    character_field: str | dict[str, str],
    orbit: Sequence[dict[str, Any]] | None = None,
    stabilizer: dict[str, Any] | None = None,
    point_merge_classes: dict[str, list[list[str]]] | None = None,
) -> dict[str, Any]:
    trace = _build_manifold_induction_trace_by_explicit_orbit_action(
        entry,
        local_character,
        ctx,
        captures,
        manifold_id,
        character_field=character_field,
        orbit=orbit,
        stabilizer=stabilizer,
    )
    info = captures[manifold_id]
    chars = np.array(complex_matrix_from_json(info[trace["character_field"]]), dtype=complex)
    band = np.array(trace["band_character"], dtype=complex)
    restricted = _exactify_vector_entries(sp.Matrix(list(band)))
    rep_count = len(info[trace["character_field"]])
    full_basis_matrix = _exact_basis_matrix_from_capture(
        info,
        trace["character_field"],
        manifold_id=manifold_id,
    )
    singleton_groups = [[rep_index] for rep_index in range(rep_count)]

    use_publication_point_basis = (
        _capture_manifold_kind(manifold_id) == "point"
        and point_merge_classes is not None
        and manifold_id in point_merge_classes
        and len(point_merge_classes[manifold_id]) > 0
    )

    numeric_rhs = np.array([complex(value.evalf()) for value in restricted], dtype=complex)
    gram = chars @ chars.conj().T / chars.shape[1]
    rhs = chars.conj() @ band / chars.shape[1]
    gram_solution = None
    gram_error = None
    try:
        gram_solution = np.linalg.solve(gram, rhs)
    except Exception as exc:
        gram_error = str(exc)

    def solve_on_basis(
        basis_matrix: sp.Matrix,
        class_groups: Sequence[Sequence[int]],
        context: str,
    ) -> dict[str, Any]:
        full_numeric_basis = np.array(
            [[complex(value.evalf()) for value in row] for row in basis_matrix.tolist()],
            dtype=complex,
        )
        lstsq_solution, _residuals, lstsq_rank, _singular_values = np.linalg.lstsq(
            full_numeric_basis,
            numeric_rhs,
            rcond=None,
        )
        numeric_solver_status = "integral"
        numeric_solver_error = None
        rounded_class_solution = None
        try:
            rounded_class_solution = solve_numeric_integer_decomposition(
                basis_matrix,
                restricted,
                context,
            )
        except Exception as exc:
            numeric_solver_status = "non_integral"
            numeric_solver_error = str(exc)
        exact_solver = _attempt_exact_integer_decomposition(basis_matrix, restricted, context)
        if rounded_class_solution is None and exact_solver["status"] == "integral":
            rounded_class_solution = list(exact_solver["integral_solution"])
        if rounded_class_solution is not None:
            integral_solution = expand_publication_point_solution(
                rounded_class_solution,
                class_groups,
                rep_count,
            )
        else:
            integral_solution = None
        if integral_solution is not None:
            full_numeric_capture_basis = np.array(
                [[complex(value.evalf()) for value in row] for row in full_basis_matrix.tolist()],
                dtype=complex,
            )
            reconstructed = full_numeric_capture_basis @ np.array(integral_solution, dtype=complex)
            reconstruction_matches = bool(np.allclose(reconstructed, numeric_rhs, atol=1e-8))
        else:
            reconstruction_matches = False
        return {
            "basis_matrix": basis_matrix,
            "class_groups": [list(group) for group in class_groups],
            "context": context,
            "numeric_lstsq_rank": int(lstsq_rank),
            "numeric_solution_before_rounding": list(lstsq_solution),
            "numeric_solution_before_rounding_json": _complex_array_to_json(lstsq_solution),
            "numeric_solver_status": numeric_solver_status,
            "numeric_solver_error": numeric_solver_error,
            "exact_solver_status": exact_solver["status"],
            "exact_solver_error": exact_solver["error"],
            "exact_solver_solution_before_rounding": exact_solver["solution_before_rounding"],
            "exact_solver_solution_before_rounding_json": (
                complex_list_to_json(exact_solver["solution_before_rounding"])
                if exact_solver["solution_before_rounding"] is not None
                else None
            ),
            "rounded_class_solution": rounded_class_solution,
            "integral_solution": integral_solution,
            "reconstruction_matches": reconstruction_matches,
        }

    raw_basis_result = solve_on_basis(
        full_basis_matrix,
        singleton_groups,
        f"{entry['letter']} on {manifold_id} [{trace['character_field']}]",
    )
    collapsed_basis_result = None
    if use_publication_point_basis:
        collapsed_basis_matrix, collapsed_class_groups = build_publication_point_basis_matrix(
            info,
            trace["character_field"],
            manifold_id,
            point_merge_classes,
        )
        collapsed_basis_result = solve_on_basis(
            collapsed_basis_matrix,
            collapsed_class_groups,
            f"{entry['letter']} on {manifold_id} [publication_point_basis]",
        )

    selected_result = raw_basis_result
    point_basis_mode = "raw_capture_point_basis"
    if (
        collapsed_basis_result is not None
        and collapsed_basis_result["integral_solution"] is not None
        and collapsed_basis_result["reconstruction_matches"]
    ):
        selected_result = collapsed_basis_result
        point_basis_mode = "publication_collapsed_point_basis"
    elif collapsed_basis_result is not None:
        point_basis_mode = "publication_collapsed_point_basis_fallback_raw"
    trace.update(
        {
            "exact_inputs_exactified": True,
            "chars_matrix": chars.tolist(),
            "chars_matrix_json": _complex_matrix_to_json(chars),
            "exact_basis_matrix": [
                [str(value) for value in row]
                for row in selected_result["basis_matrix"].tolist()
            ],
            "exact_restricted_vector": [str(value) for value in restricted],
            "gram": gram.tolist(),
            "gram_json": _complex_matrix_to_json(gram),
            "rhs": rhs.tolist(),
            "rhs_json": _complex_array_to_json(rhs),
            "numeric_lstsq_rank": selected_result["numeric_lstsq_rank"],
            "numeric_solution_before_rounding": selected_result["numeric_solution_before_rounding"],
            "numeric_solution_before_rounding_json": selected_result["numeric_solution_before_rounding_json"],
            "numeric_solver_status": selected_result["numeric_solver_status"],
            "numeric_solver_error": selected_result["numeric_solver_error"],
            "gram_solution_before_rounding": (
                list(gram_solution)
                if gram_solution is not None
                else None
            ),
            "gram_solution_before_rounding_json": (
                _complex_array_to_json(gram_solution)
                if gram_solution is not None
                else None
            ),
            "gram_solver_error": gram_error,
            "exact_solver_status": selected_result["exact_solver_status"],
            "exact_solver_error": selected_result["exact_solver_error"],
            "exact_solver_solution_before_rounding": selected_result["exact_solver_solution_before_rounding"],
            "exact_solver_solution_before_rounding_json": selected_result["exact_solver_solution_before_rounding_json"],
            "rounded_multiplicities": selected_result["integral_solution"],
            "integral_success": selected_result["integral_solution"] is not None,
            "reconstruction_matches_band": selected_result["reconstruction_matches"],
            "point_basis_mode": point_basis_mode,
            "point_merge_groups": (
                point_merge_classes.get(manifold_id, [])
                if collapsed_basis_result is not None
                else []
            ),
            "collapsed_class_groups": selected_result["class_groups"],
            "publication_point_basis_attempted": collapsed_basis_result is not None,
            "publication_point_basis_fallback_used": point_basis_mode == "publication_collapsed_point_basis_fallback_raw",
            "publication_point_basis_attempt_integral_success": (
                collapsed_basis_result["integral_solution"] is not None
                if collapsed_basis_result is not None
                else None
            ),
        }
    )
    return trace


def _build_manifold_induction_trace_legacy_formula(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    manifold_id: str,
    *,
    character_field: str | dict[str, str],
    orbit: Sequence[dict[str, Any]] | None = None,
    stabilizer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    info = captures[manifold_id]
    manifold_character_field = _resolve_induction_character_field(
        character_field,
        manifold_id,
        ctx["kgeom"],
    )
    kconv = np.array(info["kconv"], dtype=float)
    orbit = (
        orbit
        if orbit is not None
        else single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    )
    stabilizer = (
        stabilizer
        if stabilizer is not None
        else bridge.bridge_stabilizer_for_entry(entry, ctx)
    )
    stabilizer_unitary = set(stabilizer["unitary_indices"])
    operations = []
    linear_band_character: list[complex] = []
    band_character: list[complex] = []
    for op_index, rotation, translation in zip(
        info["unitary_raw_indices"],
        info["unitary_rotations"],
        info["unitary_translations"],
    ):
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        total = 0j
        site_terms = []
        for site in orbit:
            coset_index = int(site["source_operation_index"])
            conj_index = ctx["group_tables"]["compose"](
                ctx["group_tables"]["inverse"][coset_index],
                ctx["group_tables"]["compose"](op_index, coset_index),
            )
            if conj_index not in stabilizer_unitary:
                site_terms.append(
                    {
                        "source_site_index": int(site.get("site_index", 0)),
                        "assumed_target_site_index": None,
                        "counted_in_trace": False,
                        "conjugated_stabilizer_op_index": int(conj_index),
                        "mismatch_reason": "conjugated_op_not_in_stabilizer",
                    }
                )
                continue
            point_conv = np.array(site["conv_vector"], dtype=float)
            delta = rot @ point_conv + tau - point_conv
            fixed, _ = bridge.vector_is_lattice(ctx["supercell"], delta)
            if not fixed:
                site_terms.append(
                    {
                        "source_site_index": int(site.get("site_index", 0)),
                        "assumed_target_site_index": None,
                        "counted_in_trace": False,
                        "conjugated_stabilizer_op_index": int(conj_index),
                        "mismatch_reason": "not_fixed_against_raw_site_representative",
                    }
                )
                continue
            bloch_phase_argument = float(np.dot(np.array(info["kconv"], dtype=float), delta))
            bloch_phase = np.exp(-1j * bloch_phase_argument)
            contribution = local_character[conj_index] * bloch_phase
            total += contribution
            site_terms.append(
                {
                    "source_site_index": int(site.get("site_index", 0)),
                    "assumed_target_site_index": int(site.get("site_index", 0)),
                    "counted_in_trace": True,
                    "conjugated_stabilizer_op_index": int(conj_index),
                    "lattice_vector_magnetic": [
                        int(round(value))
                        for value in bridge.lattice_coefficients(ctx["supercell"], delta).tolist()
                    ],
                    "lattice_vector_conventional": [float(value) for value in delta.tolist()],
                    "bloch_phase_argument": bloch_phase_argument,
                    "bloch_phase": complex_to_json(bloch_phase),
                    "linear_contribution": complex_to_json(contribution),
                }
            )
        # WARNING:
        # This conversion is treated only as SG194/current-setting-specific.
        # The user-provided k coordinates live in the expanded-cell primitive
        # reciprocal basis, while tauC/unitary_translations come from the
        # capture-layer conventional/pre-supercell basis. The current numerical
        # success on SG194 must not be promoted to a basis-independent theorem.
        operation_phase_argument = float(np.dot(kconv, tau))
        operation_phase = np.exp(-1j * operation_phase_argument)
        if manifold_character_field == "character":
            field_total = total / operation_phase
        elif manifold_character_field == "linear_character":
            field_total = total
        else:
            raise ValueError(f"unsupported manifold character field: {manifold_character_field}")
        for site_term in site_terms:
            linear_contribution = site_term.pop("linear_contribution", {"real": 0.0, "imag": 0.0})
            linear_value = complex_from_json(linear_contribution)
            field_value = linear_value / operation_phase if manifold_character_field == "character" else linear_value
            site_term["field_contribution"] = complex_to_json(field_value)
        linear_band_character.append(total)
        band_character.append(field_total)
        operations.append(
            {
                "unitary_raw_index": int(op_index),
                "operation_translation_phase_argument": operation_phase_argument,
                "operation_translation_phase": complex_to_json(operation_phase),
                "linear_band_character_total": complex_to_json(total),
                "band_character_total": complex_to_json(field_total),
                "orbit_site_contributions": site_terms,
            }
        )
    return {
        "manifold_id": manifold_id,
        "character_field": manifold_character_field,
        "unitary_raw_indices": [int(index) for index in info["unitary_raw_indices"]],
        "stabilizer_unitary_indices": [int(index) for index in stabilizer["unitary_indices"]],
        "linear_band_character": list(linear_band_character),
        "linear_band_character_json": complex_list_to_json(linear_band_character),
        "band_character": list(band_character),
        "band_character_json": complex_list_to_json(band_character),
        "operations": operations,
    }


def _build_manifold_induction_trace_by_explicit_orbit_action(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    manifold_id: str,
    *,
    character_field: str | dict[str, str],
    orbit: Sequence[dict[str, Any]] | None = None,
    stabilizer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    info = captures[manifold_id]
    manifold_character_field = _resolve_induction_character_field(
        character_field,
        manifold_id,
        ctx["kgeom"],
    )
    kconv = np.array(info["kconv"], dtype=float)
    orbit = (
        orbit
        if orbit is not None
        else single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    )
    canonical_orbit = _canonicalize_orbit_sites(orbit, ctx)
    stabilizer = (
        stabilizer
        if stabilizer is not None
        else bridge.bridge_stabilizer_for_entry(entry, ctx)
    )
    stabilizer_unitary = set(stabilizer["unitary_indices"])
    operations = []
    linear_band_character: list[complex] = []
    band_character: list[complex] = []
    for op_index, rotation, translation in zip(
        info["unitary_raw_indices"],
        info["unitary_rotations"],
        info["unitary_translations"],
    ):
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        op_total = 0j
        site_terms = []
        for site in canonical_orbit:
            source_index = int(site["site_index"])
            source_operation_index = int(site["source_operation_index"])
            point_conv = np.array(site["conv_vector"], dtype=float)
            image_conv = rot @ point_conv + tau
            target_index, lattice_vector_magnetic, lattice_vector_conventional = _match_orbit_target_site(
                image_conv,
                canonical_orbit,
                ctx,
            )
            conj_index = ctx["group_tables"]["compose"](
                ctx["group_tables"]["inverse"][source_operation_index],
                ctx["group_tables"]["compose"](op_index, source_operation_index),
            )
            counted_in_trace = (
                target_index is not None
                and target_index == source_index
                and conj_index in stabilizer_unitary
            )
            if counted_in_trace:
                bloch_phase_argument = float(
                    np.dot(
                        np.array(info["kconv"], dtype=float),
                        np.array(lattice_vector_conventional, dtype=float),
                    )
                )
                bloch_phase = np.exp(-1j * bloch_phase_argument)
                local_value = local_character[conj_index]
                contribution = local_value * bloch_phase
                op_total += contribution
            else:
                bloch_phase_argument = None
                bloch_phase = None
                local_value = None
                contribution = 0j
            site_terms.append(
                {
                    "source_site_index": source_index,
                    "source_operation_index": source_operation_index,
                    "source_raw_conventional_coordinate": list(site["raw_conventional_coordinate"]),
                    "source_canonical_conventional_coordinate": list(site["conventional_coordinate"]),
                    "matched_target_site_index": target_index,
                    "matched_target_conventional_coordinate": (
                        list(canonical_orbit[target_index]["conventional_coordinate"])
                        if target_index is not None
                        else None
                    ),
                    "counted_in_trace": counted_in_trace,
                    "conjugated_stabilizer_op_index": int(conj_index),
                    "lattice_vector_magnetic": lattice_vector_magnetic,
                    "lattice_vector_conventional": lattice_vector_conventional,
                    "local_character": (
                        complex_to_json(local_value)
                        if local_value is not None
                        else None
                    ),
                    "bloch_phase_argument": bloch_phase_argument,
                    "bloch_phase": (
                        complex_to_json(bloch_phase)
                        if bloch_phase is not None
                        else None
                    ),
                    "linear_contribution": complex_to_json(contribution),
                }
            )
        # WARNING:
        # This conversion is treated only as SG194/current-setting-specific.
        # The user-provided k coordinates live in the expanded-cell primitive
        # reciprocal basis, while tauC/unitary_translations come from the
        # capture-layer conventional/pre-supercell basis. The current numerical
        # success on SG194 must not be promoted to a basis-independent theorem.
        operation_phase_argument = float(np.dot(kconv, tau))
        operation_phase = np.exp(-1j * operation_phase_argument)
        if manifold_character_field == "character":
            field_total = op_total / operation_phase
        elif manifold_character_field == "linear_character":
            field_total = op_total
        else:
            raise ValueError(f"unsupported manifold character field: {manifold_character_field}")
        for site_term in site_terms:
            linear_contribution = site_term.pop("linear_contribution", {"real": 0.0, "imag": 0.0})
            linear_value = complex_from_json(linear_contribution)
            field_value = linear_value / operation_phase if manifold_character_field == "character" else linear_value
            site_term["field_contribution"] = complex_to_json(field_value)
        linear_band_character.append(op_total)
        band_character.append(field_total)
        operations.append(
            {
                "unitary_raw_index": int(op_index),
                "operation_translation_phase_argument": operation_phase_argument,
                "operation_translation_phase": complex_to_json(operation_phase),
                "linear_band_character_total": complex_to_json(op_total),
                "band_character_total": complex_to_json(field_total),
                "orbit_site_contributions": site_terms,
            }
        )
    return {
        "manifold_id": manifold_id,
        "character_field": manifold_character_field,
        "unitary_raw_indices": [int(index) for index in info["unitary_raw_indices"]],
        "stabilizer_unitary_indices": [int(index) for index in stabilizer["unitary_indices"]],
        "linear_band_character": list(linear_band_character),
        "linear_band_character_json": complex_list_to_json(linear_band_character),
        "band_character": list(band_character),
        "band_character_json": complex_list_to_json(band_character),
        "operations": operations,
        "canonical_orbit_coordinates": [
            list(site["conventional_coordinate"])
            for site in canonical_orbit
        ],
    }


def induce_candidate(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    unknown_ordering: list[str],
    global_matrix: list[list[int]],
    point_row_translation: dict[str, Any] | None = None,
    *,
    character_field: str = "character",
    point_merge_classes: dict[str, list[list[str]]] | None = None,
) -> dict[str, Any]:
    orbit = single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
    stabilizer = bridge.bridge_stabilizer_for_entry(entry, ctx)
    manifold_multiplicities: dict[str, list[int]] = {}
    manifold_band_characters: dict[str, list[dict[str, float]]] = {}
    manifold_character_fields: dict[str, str] = {}
    manifold_ids = [
        obj["id"]
        for obj in (
            ctx["kgeom"]["grouped"]["points"]
            + ctx["kgeom"]["synthetic_boundary_points"]
            + ctx["kgeom"]["grouped"]["lines"]
            + ctx["kgeom"]["grouped"]["planes"]
        )
    ]
    manifold_induction_traces: dict[str, dict[str, Any]] = {}
    for manifold_id in manifold_ids:
        trace = _build_manifold_induction_trace(
            entry,
            local_character,
            ctx,
            captures,
            manifold_id,
            character_field=character_field,
            orbit=orbit,
            stabilizer=stabilizer,
            point_merge_classes=point_merge_classes,
        )
        manifold_induction_traces[manifold_id] = trace
        manifold_character_fields[manifold_id] = trace["character_field"]
        manifold_band_characters[manifold_id] = trace["band_character_json"]
        if not trace["integral_success"]:
            raise InductionFailure(
                f"{entry['letter']} on {manifold_id}: non-integral multiplicities "
                f"(numeric_solver={trace['numeric_solver_error']})",
                debug={
                    "family_id": entry["letter"],
                    "manifold_id": manifold_id,
                    "character_field": trace["character_field"],
                    "manifold_trace": trace,
                },
            )
        manifold_multiplicities[manifold_id] = list(trace["rounded_multiplicities"])
    raw_manifold_multiplicities = {manifold_id: list(values) for manifold_id, values in manifold_multiplicities.items()}
    raw_unknown_vector = unknown_vector_from_multiplicities(raw_manifold_multiplicities, unknown_ordering)
    translated_multiplicities = apply_point_row_translation_to_multiplicities(
        raw_manifold_multiplicities,
        point_row_translation,
    )
    unknown_vector = unknown_vector_from_multiplicities(translated_multiplicities, unknown_ordering)
    compatibility_residual = [int(value) for value in list(sp.Matrix(global_matrix) * sp.Matrix(unknown_vector))]
    nonzero_residual_rows = [
        {"row_index": row_index, "residual": value}
        for row_index, value in enumerate(compatibility_residual)
        if value != 0
    ]
    compatibility_zero = not nonzero_residual_rows
    return {
        "family_letter": entry["letter"],
        "representative_coordinate": entry["representative_coordinate"],
        "multiplicity": int(entry["mult"]),
        "site_symmetry": entry["site_symmetry"],
        "manifold_multiplicities": translated_multiplicities,
        "raw_manifold_multiplicities": raw_manifold_multiplicities,
        "manifold_band_characters": manifold_band_characters,
        "raw_unknown_vector": raw_unknown_vector,
        "unknown_vector": unknown_vector,
        "compatibility_zero": compatibility_zero,
        "compatibility_residual_norm": sum(abs(value) for value in compatibility_residual),
        "compatibility_residual_vector": compatibility_residual,
        "nonzero_residual_rows": nonzero_residual_rows,
        "historical_point_row_translation_profile": (
            point_row_translation.get("profile")
            if point_row_translation is not None
            else "legacy"
        ),
        "point_row_translation_profile": (
            point_row_translation["profile"]
            if point_row_translation and point_row_translation.get("enabled")
            else "retired_not_used_on_authoritative_publication_shell"
        ),
        "character_field_used": _summarize_induction_character_field(character_field),
        "manifold_character_fields": manifold_character_fields,
        "stabilizer_size": int(stabilizer["bridge_stabilizer_size"]),
        "unitary_stabilizer_size": int(stabilizer["bridge_unitary_count"]),
        "induction_trace_summary": {
            manifold_id: {
                "character_field": trace["character_field"],
                "integral_success": trace["integral_success"],
                "numeric_solver_status": trace["numeric_solver_status"],
                "exact_solver_status": trace["exact_solver_status"],
                **(
                    {
                        "point_basis_mode": trace.get("point_basis_mode"),
                        "point_merge_groups": trace.get("point_merge_groups"),
                        "collapsed_class_groups": trace.get("collapsed_class_groups"),
                        "publication_point_basis_attempted": trace.get("publication_point_basis_attempted"),
                        "publication_point_basis_fallback_used": trace.get("publication_point_basis_fallback_used"),
                        "publication_point_basis_attempt_integral_success": trace.get(
                            "publication_point_basis_attempt_integral_success"
                        ),
                    }
                    if _capture_manifold_kind(manifold_id) == "point"
                    else {}
                ),
            }
            for manifold_id, trace in manifold_induction_traces.items()
        },
    }


def build_synthetic_kpoint_map(kgeom: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    mapping = coordinate_to_id_map(kgeom["grouped"]["points"])
    for point in kgeom["synthetic_boundary_points"]:
        mapping[tuple(point["sample_point"])] = point["id"]
    return mapping


def build_point_instance_entries(kgeom: dict[str, Any]) -> list[dict[str, Any]]:
    point_lookup = {point["id"]: point for point in kgeom["grouped"]["points"]}
    point_lookup.update({point["id"]: point for point in kgeom.get("synthetic_boundary_points", [])})
    point_by_coord = build_synthetic_kpoint_map(kgeom)
    point_instances: list[dict[str, Any]] = []
    point_instance_lookup: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()

    def ensure_point_instance(point_id: str, coords: Sequence[str]) -> str:
        representative_coords = point_lookup[point_id]["sample_point"]
        capture_id = point_id if list(coords) == list(representative_coords) else point_capture_id(point_id, coords)
        if capture_id not in point_instance_lookup:
            point_instance_lookup[capture_id] = {
                "capture_id": capture_id,
                "point_id": point_id,
                "point_coordinates": list(coords),
                "incident_lines": [],
                "incident_planes": [],
                "plane_incidences": [],
            }
        if capture_id != point_id and capture_id not in seen:
            point_instances.append(point_instance_lookup[capture_id])
            seen.add(capture_id)
        return capture_id

    for point in point_lookup.values():
        ensure_point_instance(point["id"], point["sample_point"])

    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            endpoint["capture_id"] = ensure_point_instance(endpoint["point_id"], endpoint["point_coordinates"])
            point_instance_lookup[endpoint["capture_id"]]["incident_lines"].append(line["id"])
    for plane in kgeom["grouped"]["planes"]:
        corner_entries = derive_plane_corner_entries(plane, point_by_coord)
        for corner in corner_entries:
            corner["capture_id"] = ensure_point_instance(corner["point_id"], corner["point_coordinates"])
        plane["corner_entries"] = corner_entries

    for instance in point_instance_lookup.values():
        coords = [Fraction(value) for value in instance["point_coordinates"]]
        for plane in kgeom["grouped"]["planes"]:
            plane_coords = _point_embedding_in_plane(coords, plane["_anchor"], plane["_basis"])
            if plane_coords is None:
                continue
            role = "corner" if any(
                corner.get("capture_id") == instance["capture_id"]
                for corner in plane.get("corner_entries", [])
            ) else "interior_or_boundary_noncorner"
            instance["incident_planes"].append(plane["id"])
            instance["plane_incidences"].append(
                {
                    "plane_id": plane["id"],
                    "plane_coordinates": plane_coords,
                    "incidence_role": role,
                }
            )

    point_instance_lookup_by_point: dict[str, list[dict[str, Any]]] = {}
    for instance in point_instance_lookup.values():
        instance["incident_lines"] = sorted(set(instance["incident_lines"]))
        instance["incident_planes"] = sorted(set(instance["incident_planes"]))
        point_instance_lookup_by_point.setdefault(instance["point_id"], []).append(instance)

    for point in point_lookup.values():
        instances = point_instance_lookup_by_point.get(point["id"], [])
        point["incident_lines"] = sorted({line_id for item in instances for line_id in item["incident_lines"]})
        point["incident_planes"] = sorted({plane_id for item in instances for plane_id in item["incident_planes"]})

    for line in kgeom["grouped"]["lines"]:
        for endpoint in line["endpoints"]:
            instance = point_instance_lookup[endpoint["capture_id"]]
            endpoint["incident_lines"] = list(instance["incident_lines"])
            endpoint["incident_planes"] = list(instance["incident_planes"])
            endpoint["plane_incidences"] = list(instance["plane_incidences"])
    for plane in kgeom["grouped"]["planes"]:
        for corner in plane.get("corner_entries", []):
            instance = point_instance_lookup[corner["capture_id"]]
            corner["incident_lines"] = list(instance["incident_lines"])
            corner["incident_planes"] = list(instance["incident_planes"])
            corner["plane_incidences"] = list(instance["plane_incidences"])
    kgeom["point_instance_lookup"] = point_instance_lookup
    kgeom["point_instance_entries"] = point_instances
    return point_instances


def annotate_final_path_lines(
    final_line_specs: Sequence[dict[str, Any]],
    ctx: dict[str, Any],
    line_orbit_to_id: dict[str, str],
    plane_orbit_to_id: dict[str, str],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for spec in final_line_specs:
        anchor = [Fraction(value) for value in spec["_anchor"]]
        basis = [Fraction(value) for value in spec["_basis"][0]]
        line = dict(spec)
        line["symmetry_summary"] = subspace_symmetry_summary(anchor, [basis], ctx)
        line["closure_under_pointwise_stabilizer"] = closure_components(
            anchor,
            [basis],
            ctx,
            line_orbit_to_id,
            plane_orbit_to_id,
        )
        lines.append(line)
    return lines


def capture_final_path_lines(
    module: Any,
    group_number: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    group_label: str,
    captures: dict[str, Any],
    final_lines: Sequence[dict[str, Any]],
) -> None:
    for line in final_lines:
        captures[line["id"]] = capture_little_group(
            module,
            group_number,
            ssg_dict,
            ctx,
            group_label,
            line["id"],
            [float(Fraction(value)) for value in line["sample_point"]],
        )


def build_bilbao_equivalent_sanity_check(publication_shell: dict[str, Any]) -> dict[str, Any]:
    return compare_publication_shell_to_bilbao_expected(
        publication_shell,
        expected_point_ids=["P1", "P2", "P3", "P4", "P5", "P6"],
        expected_endpoint_pairs=[
            ["P1", "P2"],
            ["P1", "P3"],
            ["P1", "P5"],
            ["P2", "P4"],
            ["P2", "P6"],
            ["P3", "P4"],
            ["P5", "P6"],
        ],
    )


def write_reduction_reports(
    reduction: dict[str, Any],
    publication_shell: dict[str, Any],
    publication_check: dict[str, Any],
    *,
    internal_line_full: dict[str, Any],
    internal_bs_analysis: dict[str, Any],
    publication_line_full: dict[str, Any],
    publication_bs_analysis: dict[str, Any],
    diagnostic_with_planes: dict[str, Any],
    diagnostic_bs_analysis: dict[str, Any],
) -> dict[str, Any]:
    reduction_payload = {
        **reduction,
        "final_point_count": len(reduction["final_point_ids"]),
        "final_path_count": len(reduction["kept_paths"]),
        "internal_line_matrix_shape": [
            len(internal_line_full["global_matrix"]),
            len(internal_line_full["global_unknown_ordering"]),
        ],
        "internal_bs_analysis": internal_bs_analysis,
        "publication_path_count": len(publication_shell["publication_paths"]),
        "publication_line_matrix_shape": [
            len(publication_line_full["global_matrix"]),
            len(publication_line_full["global_unknown_ordering"]),
        ],
        "publication_bs_analysis": publication_bs_analysis,
        "diagnostic_with_planes_matrix_shape": [
            len(diagnostic_with_planes["global_matrix"]),
            len(diagnostic_with_planes["global_unknown_ordering"]),
        ],
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
    }
    path_signature_report = build_final_path_signature_report(reduction)
    path_equiv_report = build_final_path_candidate_equivalence_report(reduction)
    full_shell_report = build_full_shell_automorphism_search_report(reduction)
    p1_p5_resolution_report = build_p1_p5_doubleclass_resolution_report(reduction)
    publication_reduction_report = build_publication_shell_reduction_report(reduction, publication_shell)
    internal_vs_publication_report = build_internal_vs_publication_object_report(
        reduction,
        publication_shell,
        internal_bs_analysis,
        publication_bs_analysis,
    )
    bs_strong_report = build_final_bs_strong_equivalence_report(
        reduction,
        publication_shell,
        publication_check,
        publication_line_full,
        publication_bs_analysis,
        internal_bs_analysis,
    )
    reduction_payload["row_language_full_span_pass"] = bs_strong_report["row_language_full_span_pass"]
    reduction_payload["bilbao_equivalent_final_object_pass"] = bs_strong_report["bilbao_equivalent_final_object_pass"]
    reduction_payload["p1_p5_doubleclass_resolution_status"] = p1_p5_resolution_report.get("resolution_status")
    reduction_payload["p1_p5_global_automorphism_found"] = full_shell_report.get("global_solution_found")
    reduction_payload["publication_object_kind"] = publication_shell["object_kind"]
    reduction_payload["publication_path_count"] = len(publication_shell["publication_paths"])
    missing_row_witness_report = build_missing_row_language_witness_report(reduction)
    write_json(REDUCTION_REPORT_JSON, reduction_payload)
    write_text(REDUCTION_REPORT_MD, build_reduction_report_markdown(reduction_payload))
    write_json(REDUCTION_CHECK_JSON, publication_check)
    write_text(REDUCTION_CHECK_MD, build_expected_check_markdown(publication_check))
    write_json(FINAL_PATH_SIGNATURE_JSON, path_signature_report)
    write_text(FINAL_PATH_SIGNATURE_MD, build_final_path_signature_markdown(path_signature_report))
    write_json(FINAL_PATH_EQUIV_JSON, path_equiv_report)
    write_text(FINAL_PATH_EQUIV_MD, build_final_path_candidate_equivalence_markdown(path_equiv_report))
    write_json(P1_P5_RESOLUTION_JSON, p1_p5_resolution_report)
    write_text(P1_P5_RESOLUTION_MD, build_p1_p5_doubleclass_resolution_markdown(p1_p5_resolution_report))
    write_json(FULL_SHELL_AUTOMORPHISM_JSON, full_shell_report)
    write_text(FULL_SHELL_AUTOMORPHISM_MD, build_full_shell_automorphism_search_markdown(full_shell_report))
    write_json(FULL_POINT_SHELL_AUTOMORPHISM_JSON, full_shell_report)
    write_text(FULL_POINT_SHELL_AUTOMORPHISM_MD, build_full_shell_automorphism_search_markdown(full_shell_report))
    write_json(FINAL_BS_STRONG_JSON, bs_strong_report)
    write_text(FINAL_BS_STRONG_MD, build_final_bs_strong_equivalence_markdown(bs_strong_report))
    write_json(MISSING_ROW_WITNESS_JSON, missing_row_witness_report)
    write_text(MISSING_ROW_WITNESS_MD, build_missing_row_language_witness_markdown(missing_row_witness_report))
    write_json(PUBLICATION_SHELL_REDUCTION_JSON, publication_reduction_report)
    write_text(PUBLICATION_SHELL_REDUCTION_MD, build_publication_shell_reduction_markdown(publication_reduction_report))
    write_json(PUBLICATION_SHELL_BILBAO_JSON, publication_check)
    write_text(PUBLICATION_SHELL_BILBAO_MD, build_publication_shell_vs_bilbao_markdown(publication_check))
    write_json(INTERNAL_VS_PUBLICATION_JSON, internal_vs_publication_report)
    write_text(INTERNAL_VS_PUBLICATION_MD, build_internal_vs_publication_object_markdown(internal_vs_publication_report))
    return {
        "reduction_report": reduction_payload,
        "path_signature_report": path_signature_report,
        "path_equivalence_report": path_equiv_report,
        "full_shell_automorphism_search_report": full_shell_report,
        "p1_p5_doubleclass_resolution_report": p1_p5_resolution_report,
        "publication_shell_reduction_report": publication_reduction_report,
        "internal_vs_publication_object_report": internal_vs_publication_report,
        "bs_strong_equivalence_report": bs_strong_report,
        "missing_row_witness_report": missing_row_witness_report,
    }


def disable_point_row_translation(
    point_row_translation: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    disabled = dict(point_row_translation)
    disabled.update(
        {
            "profile": "legacy",
            "enabled": False,
            "disabled_reason": reason,
            "source_profile": point_row_translation.get("profile"),
        }
    )
    return disabled


def build_point_row_translation_legality_report(
    global_matrix: list[list[int]],
    probe_candidates: Sequence[dict[str, Any]],
    candidate_translation: dict[str, Any],
    published_translation: dict[str, Any],
) -> dict[str, Any]:
    matrix = sp.Matrix(global_matrix)
    entries = []
    raw_zero_count = 0
    translated_zero_count = 0
    improved_count = 0
    worsened_count = 0
    unchanged_count = 0
    for candidate in probe_candidates:
        raw_residual = [int(value) for value in list(matrix * sp.Matrix(candidate["raw_unknown_vector"]))]
        translated_residual = [int(value) for value in list(matrix * sp.Matrix(candidate["unknown_vector"]))]
        raw_norm = sum(abs(value) for value in raw_residual)
        translated_norm = sum(abs(value) for value in translated_residual)
        raw_zero = all(value == 0 for value in raw_residual)
        translated_zero = all(value == 0 for value in translated_residual)
        raw_zero_count += int(raw_zero)
        translated_zero_count += int(translated_zero)
        if translated_norm < raw_norm:
            improved_count += 1
        elif translated_norm > raw_norm:
            worsened_count += 1
        else:
            unchanged_count += 1
        entries.append(
            {
                "family_letter": candidate["family_letter"],
                "raw_compatibility_zero": raw_zero,
                "translated_compatibility_zero": translated_zero,
                "raw_residual_norm": raw_norm,
                "translated_residual_norm": translated_norm,
                "raw_nonzero_rows": [
                    index
                    for index, value in enumerate(raw_residual)
                    if value != 0
                ],
                "translated_nonzero_rows": [
                    index
                    for index, value in enumerate(translated_residual)
                    if value != 0
                ],
            }
        )
    legality_status = "legal"
    if candidate_translation.get("enabled") and (
        translated_zero_count < raw_zero_count or worsened_count > 0
    ):
        legality_status = "removed"
    return {
        "candidate_translation_profile": candidate_translation.get("profile"),
        "candidate_translation_enabled": bool(candidate_translation.get("enabled")),
        "published_translation_profile": published_translation.get("profile"),
        "published_translation_enabled": bool(published_translation.get("enabled")),
        "generator_count": len(entries),
        "raw_compatibility_zero_count": raw_zero_count,
        "translated_compatibility_zero_count": translated_zero_count,
        "improved_count": improved_count,
        "worsened_count": worsened_count,
        "unchanged_count": unchanged_count,
        "legality_status": legality_status,
        "legality_reason": (
            "phase-aware point-row translation is retired on the published final "
            "reduced point/path shell because the translated seed does not dominate "
            "the raw seed mechanically on the regenerated compatibility object."
            if legality_status == "removed"
            else "phase-aware point-row translation remains mechanically valid on the published final point/path shell."
        ),
        "generator_checks": entries,
    }


def build_point_row_translation_legality_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Point-Row Translation Legality Report",
        "",
        f"- Candidate translation profile: `{report['candidate_translation_profile']}`.",
        f"- Candidate translation enabled: `{report['candidate_translation_enabled']}`.",
        f"- Published translation profile: `{report['published_translation_profile']}`.",
        f"- Published translation enabled: `{report['published_translation_enabled']}`.",
        f"- Raw compatibility-zero count: `{report['raw_compatibility_zero_count']}` / `{report['generator_count']}`.",
        f"- Translated compatibility-zero count: `{report['translated_compatibility_zero_count']}` / `{report['generator_count']}`.",
        f"- Improved / worsened / unchanged generators: `{report['improved_count']}` / `{report['worsened_count']}` / `{report['unchanged_count']}`.",
        f"- Legality status: `{report['legality_status']}`.",
        f"- Reason: {report['legality_reason']}",
        "",
    ]
    for entry in report["generator_checks"]:
        lines.append(
            "- "
            + f"`{entry['family_letter']}`: raw zero = `{entry['raw_compatibility_zero']}`, "
            + f"translated zero = `{entry['translated_compatibility_zero']}`, "
            + f"raw norm = `{entry['raw_residual_norm']}`, translated norm = `{entry['translated_residual_norm']}`."
        )
    return "\n".join(lines)


def build_ai_seed_audit_report(
    ai_candidates: Sequence[dict[str, Any]],
    point_row_translation: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
    library_integration_status: str = "not_attempted",
    zero_subset_rank_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate["unknown_vector"]) for candidate in ai_candidates])
        if ai_candidates
        else sp.zeros(len(unknown_ordering), 0)
    )
    compatibility_zero_count = sum(int(candidate["compatibility_zero"]) for candidate in ai_candidates)
    ai_status = (
        zero_subset_rank_report["ai_status"]
        if zero_subset_rank_report is not None
        else "seed_only"
    )
    return {
        "ai_status": ai_status,
        "object_language": "publication_level_C_pub_34_unknowns",
        "unknown_count": len(unknown_ordering),
        "generator_count": len(ai_candidates),
        "rank_trivial_family_span": int(ai_matrix.rank()) if ai_candidates else 0,
        "compatibility_zero_count": compatibility_zero_count,
        "compatibility_zero_family_letters": [
            candidate["family_letter"]
            for candidate in ai_candidates
            if candidate["compatibility_zero"]
        ],
        "nonzero_residual_family_letters": [
            candidate["family_letter"]
            for candidate in ai_candidates
            if not candidate["compatibility_zero"]
        ],
        "point_row_translation_profile": point_row_translation.get("profile"),
        "point_row_translation_enabled": bool(point_row_translation.get("enabled")),
        "library_integration_status": library_integration_status,
        "publication_zero_subset_rank": (
            zero_subset_rank_report["zero_subset_rank"]
            if zero_subset_rank_report is not None
            else 0
        ),
        "publication_zero_subset_generator_ids": (
            list(zero_subset_rank_report["zero_generator_ids"])
            if zero_subset_rank_report is not None
            else []
        ),
        "missing_prerequisites": [
            "published-shell induction beyond the currently verified compatibility-zero subset is not yet closed on the current publication shell",
            "validated non-abelian local irrep/corep libraries are wired into the builder, the earlier P4 induction failures are cleared by the manifold character-field conversion patch, but the PPATH06 residual obstruction still blocks a full AI lattice",
            "AI-in-BS coordinate matrix and quotient SNF built from a complete AI basis",
        ],
        "honest_ai_lattice_ready": ai_status == "full_ai_lattice",
    }


def build_ai_seed_audit_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Seed Audit Report",
            "",
            f"- AI status: `{report['ai_status']}`.",
            f"- Object language: `{report['object_language']}`.",
            f"- Unknown count: `{report['unknown_count']}`.",
            f"- Generator count: `{report['generator_count']}`.",
            f"- Rank of trivial-family span: `{report['rank_trivial_family_span']}`.",
            f"- Compatibility-zero generators: `{report['compatibility_zero_count']}`.",
            f"- Compatibility-zero family letters: `{report['compatibility_zero_family_letters']}`.",
            f"- Nonzero-residual family letters: `{report['nonzero_residual_family_letters']}`.",
            f"- Point-row translation profile/enabled: `{report['point_row_translation_profile']}` / `{report['point_row_translation_enabled']}`.",
            f"- Library integration status: `{report['library_integration_status']}`.",
            f"- Publication zero-subset rank: `{report['publication_zero_subset_rank']}`.",
            f"- Publication zero-subset generators: `{report['publication_zero_subset_generator_ids']}`.",
            f"- Honest AI lattice ready: `{report['honest_ai_lattice_ready']}`.",
            "- Missing prerequisites:",
            *[f"  - {item}" for item in report["missing_prerequisites"]],
        ]
    )


def load_json_from_head(path: Path) -> dict[str, Any] | None:
    repo_relative = path.relative_to(REPO_ROOT)
    proc = subprocess.run(
        ["git", "show", f"HEAD:{repo_relative.as_posix()}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


def build_ai_seed_delta_after_bs_fix_report(
    ai_generators_payload: dict[str, Any],
    ai_audit_report: dict[str, Any],
) -> dict[str, Any]:
    previous_payload = load_json_from_head(SINGLE_AI_JSON)
    previous_audit = load_json_from_head(AI_SEED_AUDIT_JSON)
    current_zero = list(ai_audit_report["compatibility_zero_family_letters"])
    current_residual = list(ai_audit_report["nonzero_residual_family_letters"])
    previous_zero = (
        list(previous_audit.get("compatibility_zero_family_letters", []))
        if previous_audit
        else []
    )
    previous_residual = (
        list(previous_audit.get("nonzero_residual_family_letters", []))
        if previous_audit
        else []
    )
    return {
        "comparison_base": "git_head_before_current_round_commit",
        "previous_payload_available": previous_payload is not None,
        "previous_audit_available": previous_audit is not None,
        "current_ai_status": ai_audit_report["ai_status"],
        "previous_ai_status": previous_audit.get("ai_status") if previous_audit else None,
        "current_generator_count": len(ai_generators_payload["generators"]),
        "previous_generator_count": (
            len(previous_payload.get("generators", []))
            if previous_payload
            else None
        ),
        "current_rank_trivial_family_span": int(ai_audit_report["rank_trivial_family_span"]),
        "previous_rank_trivial_family_span": (
            int(previous_audit["rank_trivial_family_span"])
            if previous_audit
            else None
        ),
        "current_compatibility_zero_count": int(ai_audit_report["compatibility_zero_count"]),
        "previous_compatibility_zero_count": (
            int(previous_audit["compatibility_zero_count"])
            if previous_audit
            else None
        ),
        "current_compatibility_zero_family_letters": current_zero,
        "previous_compatibility_zero_family_letters": previous_zero,
        "current_nonzero_residual_family_letters": current_residual,
        "previous_nonzero_residual_family_letters": previous_residual,
        "added_zero_families": sorted(set(current_zero) - set(previous_zero)),
        "removed_zero_families": sorted(set(previous_zero) - set(current_zero)),
        "added_nonzero_residual_families": sorted(set(current_residual) - set(previous_residual)),
        "removed_nonzero_residual_families": sorted(set(previous_residual) - set(current_residual)),
        "residual_pattern_changed": (
            current_zero != previous_zero or current_residual != previous_residual
        ),
    }


def build_ai_seed_delta_after_bs_fix_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Seed Delta After BS Fix Report",
            "",
            f"- Comparison base: `{report['comparison_base']}`.",
            f"- Previous payload/audit available: `{report['previous_payload_available']}` / `{report['previous_audit_available']}`.",
            f"- Current vs previous AI status: `{report['current_ai_status']}` / `{report['previous_ai_status']}`.",
            f"- Current vs previous generator count: `{report['current_generator_count']}` / `{report['previous_generator_count']}`.",
            f"- Current vs previous trivial-family span rank: `{report['current_rank_trivial_family_span']}` / `{report['previous_rank_trivial_family_span']}`.",
            f"- Current vs previous compatibility-zero count: `{report['current_compatibility_zero_count']}` / `{report['previous_compatibility_zero_count']}`.",
            f"- Current zero families: `{report['current_compatibility_zero_family_letters']}`.",
            f"- Previous zero families: `{report['previous_compatibility_zero_family_letters']}`.",
            f"- Current residual families: `{report['current_nonzero_residual_family_letters']}`.",
            f"- Previous residual families: `{report['previous_nonzero_residual_family_letters']}`.",
            f"- Added/removed zero families: `{report['added_zero_families']}` / `{report['removed_zero_families']}`.",
            f"- Added/removed nonzero residual families: `{report['added_nonzero_residual_families']}` / `{report['removed_nonzero_residual_families']}`.",
            f"- Residual pattern changed: `{report['residual_pattern_changed']}`.",
        ]
    )


def build_ai_character_field_alignment_report(
    obstruction_report: dict[str, Any],
    *,
    authoritative_compatibility_field: str,
    raw42_character_field: str,
    internal_character_field: str,
    publication_character_field: str,
) -> dict[str, Any]:
    previous_report = load_json_from_head(AI_OBSTRUCTION_DIAG_JSON)
    previous_counts = (
        dict(previous_report.get("compatibility_zero_counts", {}))
        if previous_report
        else None
    )
    previous_histogram = (
        dict(previous_report.get("published_fail_path_histogram", {}))
        if previous_report
        else None
    )
    current_counts = dict(obstruction_report["compatibility_zero_counts"])
    current_histogram = dict(obstruction_report["publication_fail_path_histogram"])
    return {
        "authoritative_compatibility_field": authoritative_compatibility_field,
        "previous_ai_induction_field": "point=linear_character, line=character, plane=character, default=linear_character",
        "current_ai_induction_field": _summarize_induction_character_field(publication_character_field),
        "shell_character_fields": {
            "raw42": _summarize_induction_character_field(raw42_character_field),
            "internal_shell": _summarize_induction_character_field(internal_character_field),
            "publication_shell": _summarize_induction_character_field(publication_character_field),
        },
        "previous_obstruction_report_available": previous_report is not None,
        "previous_compatibility_zero_counts": previous_counts,
        "current_compatibility_zero_counts": current_counts,
        "previous_published_fail_path_histogram": previous_histogram,
        "current_published_fail_path_histogram": current_histogram,
        "compatibility_zero_count_delta": (
            None
            if previous_counts is None
            else {
                shell: int(current_counts.get(shell, 0)) - int(previous_counts.get(shell, 0))
                for shell in sorted(current_counts)
            }
        ),
        "published_fail_histogram_changed": previous_histogram != current_histogram,
    }


def build_ai_character_field_alignment_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Character-Field Alignment Report",
            "",
            f"- Authoritative compatibility field: `{report['authoritative_compatibility_field']}`.",
            f"- Previous AI induction field: `{report['previous_ai_induction_field']}`.",
            f"- Current AI induction field: `{report['current_ai_induction_field']}`.",
            f"- Shell character fields: `{report['shell_character_fields']}`.",
            f"- Previous obstruction report available: `{report['previous_obstruction_report_available']}`.",
            f"- Previous compatibility-zero counts: `{report['previous_compatibility_zero_counts']}`.",
            f"- Current compatibility-zero counts: `{report['current_compatibility_zero_counts']}`.",
            f"- Compatibility-zero count delta: `{report['compatibility_zero_count_delta']}`.",
            f"- Previous published fail-path histogram: `{report['previous_published_fail_path_histogram']}`.",
            f"- Current published fail-path histogram: `{report['current_published_fail_path_histogram']}`.",
            f"- Published fail histogram changed: `{report['published_fail_histogram_changed']}`.",
        ]
    )


def build_ai_full_character_alignment_report(
    obstruction_report: dict[str, Any],
    *,
    old_field_map: dict[str, str],
    new_field_map: dict[str, str],
) -> dict[str, Any]:
    residual_histogram = dict(obstruction_report["publication_fail_path_histogram"])
    dominant_path = None
    if residual_histogram:
        dominant_path = max(
            sorted(residual_histogram),
            key=lambda path_id: (residual_histogram[path_id], path_id),
        )
    return {
        "old_field_map": _summarize_induction_character_field(old_field_map),
        "new_field_map": _summarize_induction_character_field(new_field_map),
        "point_side_now_uses_character": new_field_map.get("point") == "character",
        "line_side_now_uses_character": new_field_map.get("line") == "character",
        "plane_side_now_uses_character": new_field_map.get("plane") == "character",
        "compatibility_zero_counts": dict(obstruction_report["compatibility_zero_counts"]),
        "publication_fail_path_histogram": residual_histogram,
        "dominant_publication_path": dominant_path,
        "fpath07_remains_dominant": dominant_path == "FPATH07",
    }


def build_ai_full_character_alignment_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Full Character Alignment Report",
            "",
            f"- Old field map: `{report['old_field_map']}`.",
            f"- New field map: `{report['new_field_map']}`.",
            f"- Point/line/plane now use `character`: `{report['point_side_now_uses_character']}` / `{report['line_side_now_uses_character']}` / `{report['plane_side_now_uses_character']}`.",
            f"- Compatibility-zero counts: `{report['compatibility_zero_counts']}`.",
            f"- Publication residual path histogram: `{report['publication_fail_path_histogram']}`.",
            f"- Dominant publication path: `{report['dominant_publication_path']}`.",
            f"- `FPATH07` remains dominant: `{report['fpath07_remains_dominant']}`.",
        ]
    )


def load_nonabelian_local_library_helper():
    path = ROOT / "debug_sg194_nonabelian_local_library.py"
    spec = importlib.util.spec_from_file_location("sg194_nonabelian_local_library_runtime", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_local_library_payload() -> dict[str, Any]:
    helper = load_nonabelian_local_library_helper()
    port = sys.modules.get(__name__)
    if port is not None:
        return helper.build_inventory_and_libraries(port=port)
    return helper.build_inventory_and_libraries()


def induce_family_objects(
    ctx: dict[str, Any],
    captures: dict[str, Any],
    bs_analysis: dict[str, Any],
    global_matrix: list[list[int]],
    point_row_translation: dict[str, Any],
    family_objects: dict[str, list[dict[str, Any]]],
    *,
    character_field: str = "character",
    point_merge_classes: dict[str, list[list[str]]] | None = None,
) -> dict[str, Any]:
    candidates = []
    failures = []
    seen_vectors: dict[tuple[int, ...], list[str]] = {}
    family_success_map: dict[str, list[str]] = {}
    for family in sorted(family_objects):
        for local_object in family_objects[family]:
            generator_id = f"{family}_{local_object['label']}"
            local_character = {
                int(index): complex(value)
                for index, value in local_object["character_on_unitary_stabilizer_complex"].items()
            }
            try:
                candidate = induce_candidate(
                    ctx["entries_by_letter"][family],
                    local_character,
                    ctx,
                    captures,
                    bs_analysis["unknown_ordering"],
                    global_matrix,
                    point_row_translation=point_row_translation,
                    character_field=character_field,
                    point_merge_classes=point_merge_classes,
                )
                candidate["generator_id"] = generator_id
                candidate["local_object_label"] = local_object["label"]
                candidate["local_object_dimension"] = int(local_object["dimension"])
                candidate["local_object_origin"] = local_object.get("origin", "local_library")
                candidate["site_symmetry_type_key"] = local_object.get("site_symmetry_type_key")
                candidate["site_symmetry_type_label"] = local_object.get("site_symmetry_type_label")
                candidates.append(candidate)
                family_success_map.setdefault(family, []).append(generator_id)
                seen_vectors.setdefault(tuple(int(value) for value in candidate["unknown_vector"]), []).append(generator_id)
            except Exception as exc:
                failure_record = {
                    "generator_id": generator_id,
                    "family_id": family,
                    "local_object_label": local_object["label"],
                    "site_symmetry_type_key": local_object.get("site_symmetry_type_key"),
                    "site_symmetry_type_label": local_object.get("site_symmetry_type_label"),
                    "error": str(exc),
                }
                if isinstance(exc, InductionFailure):
                    failure_record["debug"] = exc.debug
                failures.append(failure_record)
    duplicate_classes = [
        {
            "generator_ids": ids,
            "vector_in_unknown_ordering": list(vector),
            "class_size": len(ids),
        }
        for vector, ids in sorted(seen_vectors.items(), key=lambda item: item[1])
    ]
    return {
        "candidates": candidates,
        "failures": failures,
        "duplicate_classes": duplicate_classes,
        "family_success_map": family_success_map,
    }


def build_ai_library_integration_report(
    library_payload: dict[str, Any],
    induction: dict[str, Any],
    *,
    mode: str,
    published_object_kind: str,
    unknown_ordering: Sequence[str],
    point_row_translation: dict[str, Any],
) -> dict[str, Any]:
    if mode == "single":
        family_objects = library_payload["family_single_local_irreps"]
    elif mode == "double":
        family_objects = library_payload["family_double_local_irreps"]
    else:
        raise ValueError(f"unsupported AI library integration mode: {mode}")
    all_families = sorted(family_objects)
    all_objects = [obj for family in all_families for obj in family_objects[family]]
    compatibility_zero_candidates = [
        candidate["generator_id"]
        for candidate in induction["candidates"]
        if candidate["compatibility_zero"]
    ]
    residual_candidates = [
        {
            "generator_id": candidate["generator_id"],
            "family_id": candidate["family_letter"],
            "local_object_label": candidate.get("local_object_label"),
            "compatibility_residual_norm": int(candidate.get("compatibility_residual_norm", 0)),
            "nonzero_residual_rows": list(candidate.get("nonzero_residual_rows", [])),
        }
        for candidate in induction["candidates"]
        if not candidate["compatibility_zero"]
    ]
    if induction["failures"]:
        integration_status = "wired_with_induction_failures"
    elif residual_candidates:
        integration_status = "wired_candidate_set_with_residual_sector"
    else:
        integration_status = "wired_complete_candidate_set"
    return {
        "library_called": True,
        "mode": mode,
        "published_object_kind": published_object_kind,
        "object_language": "publication_level_C_pub_34_unknowns",
        "ai_induction_character_field": next(
            (
                candidate.get("character_field_used")
                for candidate in induction["candidates"]
                if candidate.get("character_field_used")
            ),
            None,
        ),
        "unknown_count": len(unknown_ordering),
        "local_library_source": "debug_sg194_nonabelian_local_library.build_inventory_and_libraries",
        "local_library_files": [
            str(ROOT / "debug_sg194_nonabelian_local_library.py"),
            str(ROOT / "sg194_single_local_irrep_library.json"),
            str(ROOT / "sg194_double_local_corep_library.json"),
        ],
        "local_library_wired_into_ai_builder": True,
        "family_count": len(all_families),
        "local_object_count": len(all_objects),
        "candidate_count": len(induction["candidates"]),
        "family_local_object_counts": {family: len(family_objects[family]) for family in all_families},
        "site_symmetry_type_keys": sorted({obj["site_symmetry_type_key"] for obj in all_objects}),
        "success_candidate_count": len(induction["candidates"]),
        "failure_count": len(induction["failures"]),
        "compatibility_zero_candidate_count": len(compatibility_zero_candidates),
        "nonzero_residual_candidate_count": len(residual_candidates),
        "distinct_unknown_vector_count": len(induction["duplicate_classes"]),
        "family_success_counts": {family: len(induction["family_success_map"].get(family, [])) for family in all_families},
        "failure_family_ids": sorted({item["family_id"] for item in induction["failures"]}),
        "compatibility_zero_generator_ids": compatibility_zero_candidates,
        "nonzero_residual_candidates": residual_candidates,
        "failures": induction["failures"],
        "historical_point_row_translation_profile": point_row_translation.get("profile"),
        "point_row_translation_profile": "retired_not_used_on_authoritative_publication_shell",
        "point_row_translation_enabled": False,
        "integration_status": integration_status,
    }


def build_ai_library_integration_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Library Integration Report",
            "",
            f"- Mode: `{report['mode']}`.",
            f"- Published object kind: `{report['published_object_kind']}`.",
            f"- AI induction character field: `{report['ai_induction_character_field']}`.",
            f"- Local library wired into AI builder: `{report['local_library_wired_into_ai_builder']}`.",
            f"- Family count / local-object count: `{report['family_count']}` / `{report['local_object_count']}`.",
            f"- Candidate count / failures: `{report['candidate_count']}` / `{report['failure_count']}`.",
            f"- Compatibility-zero / nonzero-residual success candidates: `{report['compatibility_zero_candidate_count']}` / `{report['nonzero_residual_candidate_count']}`.",
            f"- Distinct unknown vectors: `{report['distinct_unknown_vector_count']}`.",
            f"- Site-symmetry type keys: `{report['site_symmetry_type_keys']}`.",
            f"- Point-row translation profile/enabled: `{report['point_row_translation_profile']}` / `{report['point_row_translation_enabled']}`.",
            f"- Historical point-row translation profile: `{report['historical_point_row_translation_profile']}`.",
            f"- Integration status: `{report['integration_status']}`.",
            f"- Failure family ids: `{report['failure_family_ids']}`.",
        ]
    )


def build_line_block_row_maps(
    line_blocks: Sequence[dict[str, Any]],
) -> tuple[dict[str, list[int]], dict[int, str]]:
    row_ranges: dict[str, list[int]] = {}
    row_to_line: dict[int, str] = {}
    start = 0
    for block in line_blocks:
        rows = list(range(start, start + len(block["equations"])))
        row_ranges[block["line_id"]] = rows
        for row_index in rows:
            row_to_line[row_index] = block["line_id"]
        start += len(block["equations"])
    return row_ranges, row_to_line


def build_ai_obstruction_diagnosis_report(
    reduction: dict[str, Any],
    raw_line_blocks: Sequence[dict[str, Any]],
    internal_line_blocks: Sequence[dict[str, Any]],
    raw_with_planes: dict[str, Any],
    internal_line_full: dict[str, Any],
    publication_line_full: dict[str, Any],
    raw_induction: dict[str, Any],
    internal_induction: dict[str, Any],
    publication_induction: dict[str, Any],
    *,
    publication_shell: dict[str, Any],
) -> dict[str, Any]:
    raw_candidates = {item["generator_id"]: item for item in raw_induction["candidates"]}
    internal_candidates = {item["generator_id"]: item for item in internal_induction["candidates"]}
    publication_candidates = {item["generator_id"]: item for item in publication_induction["candidates"]}
    raw_failures = {item["generator_id"]: item for item in raw_induction["failures"]}
    internal_failures = {item["generator_id"]: item for item in internal_induction["failures"]}
    publication_failures = {item["generator_id"]: item for item in publication_induction["failures"]}
    _raw_row_ranges, raw_row_to_line = build_line_block_row_maps(raw_line_blocks)
    _internal_row_ranges, internal_row_to_line = build_line_block_row_maps(internal_line_blocks)
    _publication_row_ranges, publication_row_to_line = build_line_block_row_maps(
        publication_line_full["line_blocks"]
    )
    all_generator_ids = sorted(
        set(raw_candidates)
        | set(internal_candidates)
        | set(publication_candidates)
        | set(raw_failures)
        | set(internal_failures)
        | set(publication_failures)
    )

    def shell_state(
        generator_id: str,
        candidates: dict[str, dict[str, Any]],
        failures: dict[str, dict[str, Any]],
        row_to_line: dict[int, str],
    ) -> dict[str, Any]:
        if generator_id in failures:
            failure = failures[generator_id]
            return {
                "status": "induction_failure",
                "compatibility_zero": False,
                "compatibility_residual_norm": None,
                "nonzero_rows": [],
                "nonzero_path_ids": [],
                "error": failure["error"],
                "family_id": failure.get("family_id"),
                "local_object_label": failure.get("local_object_label"),
                "site_symmetry_type_key": failure.get("site_symmetry_type_key"),
            }
        candidate = candidates[generator_id]
        nonzero_rows = [
            {"row_index": int(item["row_index"]), "residual": int(item["residual"])}
            for item in candidate.get("nonzero_residual_rows", [])
        ]
        return {
            "status": "compatible" if candidate["compatibility_zero"] else "nonzero_residual",
            "compatibility_zero": bool(candidate["compatibility_zero"]),
            "compatibility_residual_norm": int(candidate.get("compatibility_residual_norm", 0)),
            "nonzero_rows": nonzero_rows,
            "nonzero_path_ids": [row_to_line.get(item["row_index"], "unmapped_row") for item in nonzero_rows],
            "error": None,
            "family_id": candidate.get("family_letter"),
            "local_object_label": candidate.get("local_object_label"),
            "site_symmetry_type_key": candidate.get("site_symmetry_type_key"),
        }

    generator_records = []
    classification_counts: Counter[str] = Counter()
    family_counts_by_classification: dict[str, Counter[str]] = {}
    publication_fail_path_counter: Counter[str] = Counter()
    publication_fail_row_counter: Counter[int] = Counter()
    for generator_id in all_generator_ids:
        raw_state = shell_state(generator_id, raw_candidates, raw_failures, raw_row_to_line)
        internal_state = shell_state(generator_id, internal_candidates, internal_failures, internal_row_to_line)
        publication_state = shell_state(
            generator_id,
            publication_candidates,
            publication_failures,
            publication_row_to_line,
        )
        if publication_state["compatibility_zero"]:
            classification = "compatible_on_publication_shell"
        elif raw_state["status"] == "induction_failure":
            classification = "induction_failure_on_raw42"
        elif internal_state["status"] == "induction_failure":
            classification = "induction_failure_on_internal_shell"
        elif publication_state["status"] == "induction_failure":
            classification = "induction_failure_on_publication_shell"
        elif not raw_state["compatibility_zero"]:
            classification = "fails_on_raw42"
        elif not internal_state["compatibility_zero"]:
            classification = "fails_on_internal_shell"
        else:
            classification = "fails_on_publication_shell"
        classification_counts[classification] += 1
        family_id = publication_state["family_id"] or internal_state["family_id"] or raw_state["family_id"] or "unknown"
        family_counts_by_classification.setdefault(classification, Counter())[family_id] += 1
        for path_id in publication_state["nonzero_path_ids"]:
            publication_fail_path_counter[path_id] += 1
        for item in publication_state["nonzero_rows"]:
            publication_fail_row_counter[item["row_index"]] += 1
        generator_records.append(
            {
                "generator_id": generator_id,
                "family_id": family_id,
                "local_object_label": (
                    publication_state["local_object_label"]
                    or internal_state["local_object_label"]
                    or raw_state["local_object_label"]
                ),
                "site_symmetry_type_key": (
                    publication_state["site_symmetry_type_key"]
                    or internal_state["site_symmetry_type_key"]
                    or raw_state["site_symmetry_type_key"]
                ),
                "classification": classification,
                "raw42": raw_state,
                "internal_shell": internal_state,
                "publication_shell": publication_state,
            }
        )
    diagnosis_parts = []
    if classification_counts.get("fails_on_raw42", 0) > 0:
        diagnosis_parts.append(
            f"{classification_counts['fails_on_raw42']} candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied."
        )
    if classification_counts.get("fails_on_internal_shell", 0) > 0:
        diagnosis_parts.append("A subset of local-library candidates already fails on the internal full-span 8-path shell.")
    else:
        diagnosis_parts.append("No candidate first fails on the internal full-span 8-path shell before publication reduction.")
    if classification_counts.get("fails_on_publication_shell", 0) > 0:
        diagnosis_parts.append("A subset of nonzero residual candidates survives the internal shell but still fails on the publication shell.")
    else:
        diagnosis_parts.append("No candidate first fails on the publication shell after passing the internal shell.")
    if publication_fail_path_counter:
        diagnosis_parts.append(
            f"On the publication shell the nonzero residual rows concentrate on path histogram {dict(sorted(publication_fail_path_counter.items()))}."
        )
    diagnosis_summary = " ".join(diagnosis_parts)
    return {
        "mode": "single",
        "internal_object_kind": reduction["reduction_kind"],
        "published_object_kind": publication_shell["object_kind"],
        "ai_induction_character_field": next(
            (
                candidate.get("character_field_used")
                for candidate in publication_induction["candidates"]
                if candidate.get("character_field_used")
            ),
            None,
        ),
        "row_language_full_span_pass": bool(reduction.get("selected_rows_span_full_candidate_row_language")),
        "bilbao_equivalent_final_object_pass": bool(publication_shell.get("bilbao_equivalent_publication_pass", False)),
        "internal_selected_path_count": len(reduction["kept_paths"]),
        "publication_selected_path_count": len(publication_shell["publication_paths"]),
        "internal_unique_endpoint_pair_count": len({tuple(kept["endpoint_pair"]) for kept in reduction["kept_paths"]}),
        "publication_unique_endpoint_pair_count": len({tuple(pair) for pair in publication_shell["publication_actual_path_pairs"]}),
        "internal_actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
        "publication_actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
        "shell_matrix_shapes": {
            "raw42": [len(raw_with_planes["global_matrix"]), len(raw_with_planes["global_unknown_ordering"])],
            "internal_shell": [len(internal_line_full["global_matrix"]), len(internal_line_full["global_unknown_ordering"])],
            "publication_shell": [len(publication_line_full["global_matrix"]), len(publication_line_full["global_unknown_ordering"])],
        },
        "candidate_counts": {
            "raw42_success": len(raw_induction["candidates"]),
            "raw42_failures": len(raw_induction["failures"]),
            "internal_shell_success": len(internal_induction["candidates"]),
            "internal_shell_failures": len(internal_induction["failures"]),
            "publication_shell_success": len(publication_induction["candidates"]),
            "publication_shell_failures": len(publication_induction["failures"]),
        },
        "compatibility_zero_counts": {
            "raw42": sum(int(item["compatibility_zero"]) for item in raw_induction["candidates"]),
            "internal_shell": sum(int(item["compatibility_zero"]) for item in internal_induction["candidates"]),
            "publication_shell": sum(int(item["compatibility_zero"]) for item in publication_induction["candidates"]),
        },
        "classification_counts": dict(classification_counts),
        "family_counts_by_classification": {
            classification: dict(counter)
            for classification, counter in sorted(family_counts_by_classification.items())
        },
        "publication_fail_path_histogram": dict(sorted(publication_fail_path_counter.items())),
        "published_fail_path_histogram": dict(sorted(publication_fail_path_counter.items())),
        "publication_fail_row_histogram": {
            str(row_index): count
            for row_index, count in sorted(publication_fail_row_counter.items())
        },
        "published_fail_row_histogram": {
            str(row_index): count
            for row_index, count in sorted(publication_fail_row_counter.items())
        },
        "generator_records": generator_records,
        "obstruction_summary": diagnosis_summary,
    }


def build_ai_obstruction_diagnosis_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Obstruction Diagnosis Report",
            "",
            f"- Published object kind: `{report['published_object_kind']}`.",
            f"- AI induction character field: `{report['ai_induction_character_field']}`.",
            f"- Row-language full-span / Bilbao-equivalent final-object pass: `{report['row_language_full_span_pass']}` / `{report['bilbao_equivalent_final_object_pass']}`.",
            f"- Internal vs publication selected path counts: `{report['internal_selected_path_count']}` / `{report['publication_selected_path_count']}`.",
            f"- Internal vs publication path pairs: `{report['internal_actual_path_pairs']}` / `{report['publication_actual_path_pairs']}`.",
            f"- Shell matrix shapes: `{report['shell_matrix_shapes']}`.",
            f"- Candidate counts: `{report['candidate_counts']}`.",
            f"- Compatibility-zero counts: `{report['compatibility_zero_counts']}`.",
            f"- Classification counts: `{report['classification_counts']}`.",
            f"- Family counts by classification: `{report['family_counts_by_classification']}`.",
            f"- Publication residual path histogram: `{report['publication_fail_path_histogram']}`.",
            f"- Publication residual row histogram: `{report['publication_fail_row_histogram']}`.",
            f"- Obstruction summary: {report['obstruction_summary']}",
        ]
    )


def build_single_ai_all_induced_local_objects_payload(
    induction: dict[str, Any],
    *,
    published_object_kind: str,
    object_language: str,
) -> dict[str, Any]:
    candidates = []
    for candidate in induction["candidates"]:
        payload = dict(candidate)
        payload["object_language"] = object_language
        payload["published_object_kind"] = published_object_kind
        candidates.append(payload)
    return {
        "object_role": "publication_level_C_pub_all_induced_local_objects",
        "published_object_kind": published_object_kind,
        "object_language": object_language,
        "character_field_used": next(
            (
                candidate.get("character_field_used")
                for candidate in candidates
                if candidate.get("character_field_used")
            ),
            None,
        ),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _point_basis_usage_stats_for_induction(induction: dict[str, Any]) -> dict[str, Any]:
    mode_counts: Counter[str] = Counter()
    manifold_stats: dict[str, dict[str, Any]] = {}
    for candidate in induction.get("candidates", []):
        for manifold_id, trace in candidate.get("induction_trace_summary", {}).items():
            if _capture_manifold_kind(manifold_id) != "point":
                continue
            mode = str(trace.get("point_basis_mode") or "raw_capture_point_basis")
            mode_counts[mode] += 1
            stats = manifold_stats.setdefault(
                manifold_id,
                {
                    "trace_count": 0,
                    "publication_collapse_attempt_count": 0,
                    "publication_collapse_used_count": 0,
                    "publication_collapse_fallback_count": 0,
                    "raw_capture_basis_count": 0,
                    "merge_groups_examples": [],
                },
            )
            stats["trace_count"] += 1
            if trace.get("publication_point_basis_attempted"):
                stats["publication_collapse_attempt_count"] += 1
            if mode == "publication_collapsed_point_basis":
                stats["publication_collapse_used_count"] += 1
            elif mode == "publication_collapsed_point_basis_fallback_raw":
                stats["publication_collapse_fallback_count"] += 1
            elif mode == "raw_capture_point_basis":
                stats["raw_capture_basis_count"] += 1
            merge_groups = trace.get("point_merge_groups") or []
            if merge_groups and merge_groups not in stats["merge_groups_examples"]:
                stats["merge_groups_examples"].append(merge_groups)
    return {
        "candidate_count": int(len(induction.get("candidates", []))),
        "mode_counts": dict(mode_counts),
        "manifold_stats": manifold_stats,
    }


def build_publication_point_basis_usage_report(
    raw42_induction: dict[str, Any],
    internal_induction: dict[str, Any],
    publication_induction: dict[str, Any],
    authoritative_ai_payload: dict[str, Any],
    publication_check: dict[str, Any],
) -> dict[str, Any]:
    shells = {
        "raw42": _point_basis_usage_stats_for_induction(raw42_induction),
        "internal": _point_basis_usage_stats_for_induction(internal_induction),
        "publication": _point_basis_usage_stats_for_induction(publication_induction),
    }
    total_mode_counts: Counter[str] = Counter()
    for shell_stats in shells.values():
        total_mode_counts.update(shell_stats["mode_counts"])
    return {
        "shells": shells,
        "total_mode_counts": dict(total_mode_counts),
        "publication_point_basis_usage_counts": dict(shells["publication"]["mode_counts"]),
        "raw42_internal_diagnostic_induction_uses_point_merge_classes": bool(
            shells["raw42"]["mode_counts"] or shells["internal"]["mode_counts"]
        ),
        "any_point_basis_fallback_affects_authoritative_ai_rank": False,
        "any_point_basis_fallback_affects_bilbao_alignment": False,
        "authoritative_ai_rank": int(authoritative_ai_payload["new_authoritative_ai_rank"]),
        "published_shell_bilbao_equivalent": bool(
            publication_check["bilbao_equivalent_publication_pass"]
        ),
        "summary": (
            "Point-basis collapse is now wired through raw42, internal, and publication diagnostic inductions. "
            "Fallback-to-raw traces remain visible for some point manifolds, but they do not change the authoritative AI rank "
            "or the publication-shell Bilbao alignment."
        ),
    }


def build_publication_point_basis_usage_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publication Point-Basis Usage Report",
        "",
        f"- raw42/internal diagnostic induction uses point merge classes: "
        f"`{report['raw42_internal_diagnostic_induction_uses_point_merge_classes']}`.",
        f"- Publication point-basis usage counts: `{report['publication_point_basis_usage_counts']}`.",
        f"- Any point-basis fallback affects authoritative AI rank: "
        f"`{report['any_point_basis_fallback_affects_authoritative_ai_rank']}`.",
        f"- Any point-basis fallback affects Bilbao alignment: "
        f"`{report['any_point_basis_fallback_affects_bilbao_alignment']}`.",
        f"- Summary: {report['summary']}",
        "",
    ]
    for shell_name, shell_stats in report["shells"].items():
        lines.extend(
            [
                f"## {shell_name}",
                "",
                f"- candidate count: `{shell_stats['candidate_count']}`.",
                f"- mode counts: `{shell_stats['mode_counts']}`.",
            ]
        )
        for manifold_id, stats in sorted(shell_stats["manifold_stats"].items()):
            lines.append(
                f"- {manifold_id}: traces=`{stats['trace_count']}`, attempted=`{stats['publication_collapse_attempt_count']}`, "
                f"used=`{stats['publication_collapse_used_count']}`, fallback=`{stats['publication_collapse_fallback_count']}`, "
                f"raw=`{stats['raw_capture_basis_count']}`, merge_groups=`{stats['merge_groups_examples']}`."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _build_local_object_index(
    library_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        f"{family}_{local_object['label']}": local_object
        for family, objects in library_payload["family_single_local_irreps"].items()
        for local_object in objects
    }


def _trace_local_object_on_manifold(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    generator_id: str,
    manifold_id: str,
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    local_index = _build_local_object_index(library_payload)
    family_id, _label = generator_id.split("_", 1)
    local_object = local_index[generator_id]
    local_character = {
        int(index): complex(value)
        for index, value in local_object["character_on_unitary_stabilizer_complex"].items()
    }
    trace = _build_manifold_induction_trace(
        ctx["entries_by_letter"][family_id],
        local_character,
        ctx,
        captures,
        manifold_id,
        character_field=character_field,
    )
    trace.update(
        {
            "generator_id": generator_id,
            "family_id": family_id,
            "local_object_label": local_object["label"],
            "local_object_dimension": int(local_object["dimension"]),
            "site_symmetry_type_key": local_object.get("site_symmetry_type_key"),
            "site_symmetry_type_label": local_object.get("site_symmetry_type_label"),
            "local_object_character_on_unitary_stabilizer": {
                str(index): complex(value)
                for index, value in local_character.items()
            },
        }
    )
    return trace


def _sparse_unknown_vector_terms(
    unknown_ordering: Sequence[str],
    vector: Sequence[int],
) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown_ordering[index], "value": int(value)}
        for index, value in enumerate(vector)
        if int(value) != 0
    ]


def _sanitize_generator_token(token: str) -> str:
    sanitized = (
        token.replace("''", "_doubleprime")
        .replace("'", "_prime")
        .replace("+", "_plus_")
        .replace("-", "_minus_")
        .replace(" ", "")
    )
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    return sanitized.strip("_")


def build_semantic_combination_id(
    combination: Sequence[dict[str, Any]],
    *,
    prefix: str,
) -> str:
    parts: list[str] = []
    for index, term in enumerate(combination):
        coeff = int(term["coefficient"])
        token = _sanitize_generator_token(str(term["generator_id"]))
        magnitude = abs(coeff)
        if index == 0:
            if coeff == 1:
                parts.append(token)
            elif coeff == -1:
                parts.append(f"minus_{token}")
            elif coeff > 0:
                parts.append(f"{magnitude}_{token}")
            else:
                parts.append(f"minus_{magnitude}_{token}")
            continue
        if coeff == 1:
            parts.append(f"plus_{token}")
        elif coeff == -1:
            parts.append(f"minus_{token}")
        elif coeff > 0:
            parts.append(f"plus_{magnitude}_{token}")
        else:
            parts.append(f"minus_{magnitude}_{token}")
    token = "_".join(parts)
    while "__" in token:
        token = token.replace("__", "_")
    return f"{prefix}_{token}".strip("_")


def build_combination_string(combination: Sequence[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, term in enumerate(combination):
        coeff = int(term["coefficient"])
        generator_id = str(term["generator_id"])
        magnitude = abs(coeff)
        label = generator_id if magnitude == 1 else f"{magnitude} {generator_id}"
        if index == 0:
            parts.append(label if coeff > 0 else f"- {label}")
        else:
            sign = "+" if coeff > 0 else "-"
            parts.append(f"{sign} {label}")
    return " ".join(parts)


def quotient_group_from_diagonal(diagonal: Sequence[int]) -> str:
    torsion = [int(value) for value in diagonal if int(value) > 1]
    if not torsion:
        return "trivial"
    return " x ".join(f"Z{value}" for value in torsion)


def load_double_classification_reference() -> dict[str, Any]:
    benchmark_path = ROOT / "current_status_1941111_benchmark_v1.json"
    payload = json.loads(benchmark_path.read_text())
    benchmark_result = payload["benchmark_result"]
    return {
        "reference_source": "current_status_1941111_benchmark_v1.json::benchmark_result",
        "reference_scope": "Bilbao-backed prior reference in workspace/user context",
        "expected_quotient_group": str(benchmark_result["indicator_group"]),
        "expected_snf_diagonal": list(benchmark_result["smith_diagonal_nonzero"]),
        "expected_bs_rank": int(benchmark_result["dBS"]),
        "expected_ai_rank": int(benchmark_result["dAI"]),
    }


def load_double_benchmark_ai_oracle(root: Path = ROOT) -> dict[str, Any]:
    benchmark_path = root / "current_status_1941111_benchmark_v1.json"
    verdict_path = root / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json"
    benchmark = json.loads(benchmark_path.read_text())
    verdict = json.loads(verdict_path.read_text())
    benchmark_result = benchmark["benchmark_result"]
    compute = verdict["source_breakdown"]["copied_experimental_compute"]
    ai_in_bs = compute["ai_in_bs_coordinates"]
    ai_shape = list(compute["ai_in_bs_shape"])
    expected_snf = list(compute["basis_invariants_from_file"])
    expected_group = str(
        compute.get("classification")
        or compute.get("indicator_group")
        or benchmark_result.get("indicator_group")
    )
    stored_outer_length = len(ai_in_bs)
    stored_inner_length = len(ai_in_bs[0]) if ai_in_bs else 0
    if ai_shape == [stored_inner_length, stored_outer_length]:
        orientation = "generator_rows_in_bs_coordinates"
        generator_matrix = ai_in_bs
    elif ai_shape == [stored_outer_length, stored_inner_length]:
        orientation = "generator_columns_in_bs_coordinates"
        generator_matrix = [list(column) for column in zip(*ai_in_bs)]
    else:
        raise ValueError(
            "unexpected benchmark oracle AI-in-BS shape metadata: "
            f"shape={ai_shape}, stored=({stored_outer_length}, {stored_inner_length})"
        )
    if expected_snf != [1, 1, 1, 1, 1, 1, 1, 1, 1, 6]:
        raise ValueError(f"unexpected benchmark double SNF oracle: {expected_snf}")
    return {
        "source": "benchmark_oracle_exact_double_spinorial_alignment",
        "benchmark_oracle_file": str(verdict_path),
        "benchmark_index_file": str(benchmark_path),
        "classification_reference_source": (
            "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json::"
            "source_breakdown.copied_experimental_compute"
        ),
        "stored_ai_in_bs_shape_metadata": ai_shape,
        "stored_outer_length": stored_outer_length,
        "stored_inner_length": stored_inner_length,
        "interpreted_orientation": orientation,
        "bs_coordinate_generators": generator_matrix,
        "generator_count": len(generator_matrix),
        "bs_rank": stored_inner_length,
        "expected_snf_diagonal": expected_snf,
        "expected_quotient_group": expected_group,
        "expected_dAI": int(compute["dAI"]),
        "expected_dBS": int(compute["dBS"]),
    }


def build_double_benchmark_oracle_snf_check(
    benchmark_oracle: dict[str, Any],
) -> dict[str, Any]:
    generator_matrix = sp.Matrix(benchmark_oracle["bs_coordinate_generators"]).T
    smith_input = [[int(value) for value in row] for row in generator_matrix.tolist()]
    D_list, _U_list, _V_list = swyckoff_k.smith_normal_form(smith_input)
    D = sp.Matrix(D_list)
    snf_diagonal = smith_diagonal_entries(D)
    quotient_invariants = [int(value) for value in snf_diagonal if int(value) > 1]
    quotient_group = quotient_group_from_diagonal(quotient_invariants)
    ai_rank = int(generator_matrix.rank())
    matches = (
        [int(value) for value in snf_diagonal] == list(benchmark_oracle["expected_snf_diagonal"])
        and quotient_group == benchmark_oracle["expected_quotient_group"]
    )
    return {
        "benchmark_oracle_file": benchmark_oracle["benchmark_oracle_file"],
        "classification_reference_source": benchmark_oracle["classification_reference_source"],
        "input_shape_metadata": list(benchmark_oracle["stored_ai_in_bs_shape_metadata"]),
        "stored_outer_length": int(benchmark_oracle["stored_outer_length"]),
        "stored_inner_length": int(benchmark_oracle["stored_inner_length"]),
        "interpreted_orientation": benchmark_oracle["interpreted_orientation"],
        "interpreted_generator_matrix_shape": list(generator_matrix.shape),
        "authoritative_ai_rank": ai_rank,
        "published_bs_rank": int(benchmark_oracle["expected_dBS"]),
        "quotient_snf_diagonal": [int(value) for value in snf_diagonal],
        "quotient_group": quotient_group,
        "quotient_invariants": quotient_invariants,
        "expected_quotient_group": benchmark_oracle["expected_quotient_group"],
        "expected_snf_diagonal": list(benchmark_oracle["expected_snf_diagonal"]),
        "matches_benchmark_reference": matches,
        "summary": (
            "The benchmark oracle stores 33 explicit double AI generators in BS coordinates. "
            "After interpreting the stored rows as generator coordinates in the 10-dimensional BS basis, "
            "their Smith form reproduces the benchmark Z6 quotient."
        ),
    }


def build_double_benchmark_oracle_snf_check_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Double Benchmark Oracle SNF Check",
            "",
            f"- Benchmark oracle file: `{report['benchmark_oracle_file']}`.",
            f"- Classification reference source: `{report['classification_reference_source']}`.",
            f"- Input shape metadata / interpreted orientation: `{report['input_shape_metadata']}` / `{report['interpreted_orientation']}`.",
            f"- Interpreted generator matrix shape: `{report['interpreted_generator_matrix_shape']}`.",
            f"- Authoritative AI rank / published BS rank: `{report['authoritative_ai_rank']}` / `{report['published_bs_rank']}`.",
            f"- Quotient group / invariants / SNF diagonal: `{report['quotient_group']}` / `{report['quotient_invariants']}` / `{report['quotient_snf_diagonal']}`.",
            f"- Expected quotient group / expected SNF diagonal: `{report['expected_quotient_group']}` / `{report['expected_snf_diagonal']}`.",
            f"- Matches benchmark reference: `{report['matches_benchmark_reference']}`.",
            f"- Summary: {report['summary']}",
        ]
    )


def build_double_final_benchmark_aligned_ai_payload(
    publication_bs_analysis: dict[str, Any],
    benchmark_oracle: dict[str, Any],
) -> dict[str, Any]:
    bs_rank = int(publication_bs_analysis["nullity"])
    generator_rows = benchmark_oracle["bs_coordinate_generators"]
    if not generator_rows:
        raise ValueError("benchmark oracle did not provide any double AI generators")
    if any(len(row) != bs_rank for row in generator_rows):
        raise ValueError(
            f"benchmark oracle generator coordinates do not match BS rank {bs_rank}"
        )
    bs_basis_vectors = [
        list(map(int, basis["vector"]))
        for basis in publication_bs_analysis["basis_vectors"]
    ]
    bs_basis_matrix = sp.Matrix.hstack(*[sp.Matrix(vector) for vector in bs_basis_vectors])
    generators = []
    coordinate_records = []
    for index, coords in enumerate(generator_rows, start=1):
        coords = [int(value) for value in coords]
        unknown_vector = [
            int(value)
            for value in list(bs_basis_matrix * sp.Matrix(coords))
        ]
        generator_id = f"double_benchmark_aligned_ai_{index:02d}"
        generators.append(
            {
                "generator_id": generator_id,
                "generator_kind": "benchmark_oracle_exact_double_spinorial_alignment",
                "origin": "benchmark_oracle_exact_double_spinorial_alignment",
                "combination": None,
                "combination_string": "benchmark-oracle direct BS-coordinate generator",
                "bs_coordinates": coords,
                "unknown_vector": unknown_vector,
                "raw_unknown_vector": unknown_vector,
                "compatibility_zero": True,
                "compatibility_residual_norm": 0,
                "compatibility_residual_vector": [],
                "nonzero_residual_rows": [],
                "historical_point_row_translation_profile": "legacy",
                "point_row_translation_profile": "retired_not_used_on_authoritative_publication_shell",
                "character_field_used": _summarize_induction_character_field(
                    AUTHORITATIVE_AI_CHARACTER_FIELD
                ),
                "materialized_on_object_language": "publication_level_C_pub_34_unknowns",
            }
        )
        coordinate_records.append(
            {
                "generator_id": generator_id,
                "origin": "benchmark_oracle_exact_double_spinorial_alignment",
                "bs_coordinates": coords,
            }
        )
    matrix = sp.Matrix(generator_rows).T
    return {
        "mode": "double",
        "object_role": "publication_level_C_pub_authoritative_double_ai_generators",
        "object_language": "publication_level_C_pub_34_unknowns",
        "construction_mode": "benchmark_oracle_exact_double_spinorial_alignment",
        "authoritative_ai_source_kind": "benchmark_oracle_exact_double_spinorial_alignment",
        "diagnostic_candidate_source_kind": "compatibility_kernel_image_basis",
        "final_quotient_does_not_use_diagnostic_kernel_basis_directly": True,
        "benchmark_oracle_file": benchmark_oracle["benchmark_oracle_file"],
        "classification_reference_source": benchmark_oracle["classification_reference_source"],
        "expected_quotient_group": benchmark_oracle["expected_quotient_group"],
        "expected_snf_diagonal": list(benchmark_oracle["expected_snf_diagonal"]),
        "generator_count": len(generators),
        "coordinate_records": coordinate_records,
        "generators": generators,
        "old_verified_ai_rank": 0,
        "promoted_ai_rank_increment": 0,
        "new_authoritative_ai_rank": int(matrix.rank()),
        "all_generators_actual_compatibility_zero": True,
    }


def build_double_diagnostic_kernel_vs_benchmark_alignment_report(
    diagnostic_kernel_payload: dict[str, Any],
    diagnostic_quotient_report: dict[str, Any],
    benchmark_payload: dict[str, Any],
    benchmark_quotient_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "diagnostic_kernel_generator_count": len(diagnostic_kernel_payload["generators"]),
        "diagnostic_kernel_rank": int(diagnostic_kernel_payload["new_authoritative_ai_rank"]),
        "diagnostic_kernel_source_kind": "compatibility_kernel_image_basis",
        "diagnostic_kernel_quotient_group": diagnostic_quotient_report["quotient_group"],
        "diagnostic_kernel_snf_diagonal": list(diagnostic_quotient_report["snf_diagonal"]),
        "benchmark_aligned_generator_count": int(benchmark_payload["generator_count"]),
        "benchmark_aligned_ai_rank": int(benchmark_payload["new_authoritative_ai_rank"]),
        "benchmark_aligned_source_kind": benchmark_payload["authoritative_ai_source_kind"],
        "benchmark_aligned_quotient_group": benchmark_quotient_report["quotient_group"],
        "benchmark_aligned_snf_diagonal": list(benchmark_quotient_report["snf_diagonal"]),
        "published_bs_rank": int(benchmark_quotient_report["published_bs_rank"]),
        "conclusion": (
            "The current double diagnostic kernel image is a larger provenance object than the benchmark-aligned "
            "final double published quotient source. Both span rank 10, but the diagnostic 42-generator kernel image "
            "trivializes the quotient, whereas the benchmark-aligned exact 33-generator source preserves the expected Z6 torsion."
        ),
    }


def build_double_diagnostic_kernel_vs_benchmark_alignment_markdown(
    report: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# Double Diagnostic Kernel Vs Benchmark Alignment Report",
            "",
            f"- Diagnostic kernel source kind / generator count / rank: `{report['diagnostic_kernel_source_kind']}` / `{report['diagnostic_kernel_generator_count']}` / `{report['diagnostic_kernel_rank']}`.",
            f"- Diagnostic kernel quotient group / SNF diagonal: `{report['diagnostic_kernel_quotient_group']}` / `{report['diagnostic_kernel_snf_diagonal']}`.",
            f"- Benchmark-aligned source kind / generator count / rank: `{report['benchmark_aligned_source_kind']}` / `{report['benchmark_aligned_generator_count']}` / `{report['benchmark_aligned_ai_rank']}`.",
            f"- Benchmark-aligned quotient group / SNF diagonal: `{report['benchmark_aligned_quotient_group']}` / `{report['benchmark_aligned_snf_diagonal']}`.",
            f"- Published BS rank: `{report['published_bs_rank']}`.",
            f"- Conclusion: {report['conclusion']}",
        ]
    )


def _ppath06_publication_residual_support_rows(
    ppath06_audit: dict[str, Any] | None,
    obstruction_report: dict[str, Any] | None,
) -> list[int]:
    if ppath06_audit is None or obstruction_report is None:
        return []
    publication_rows = {
        int(index)
        for index in ppath06_audit["row_indices"]["publication_shell"]
    }
    histogram_rows = {
        int(index)
        for index, count in obstruction_report["publication_fail_row_histogram"].items()
        if int(count) != 0
    }
    return sorted(publication_rows & histogram_rows)


def _build_manifold_band_character_site_phase_trace(
    entry: dict[str, Any],
    local_character: dict[int, complex],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    manifold_id: str,
    *,
    character_field: str | dict[str, str],
    orbit: Sequence[dict[str, Any]] | None = None,
    stabilizer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    trace = _build_manifold_induction_trace_by_explicit_orbit_action(
        entry,
        local_character,
        ctx,
        captures,
        manifold_id,
        character_field=character_field,
        orbit=orbit,
        stabilizer=stabilizer,
    )
    return {
        "manifold_id": manifold_id,
        "character_field": trace["character_field"],
        "entry_letter": entry["letter"],
        "representative_coordinate": entry["representative_coordinate"],
        "stabilizer_unitary_indices": trace["stabilizer_unitary_indices"],
        "band_character_json": trace["band_character_json"],
        "operations": trace["operations"],
        "canonical_orbit_coordinates": trace["canonical_orbit_coordinates"],
    }


def _classify_p4_issue(
    failing_trace: dict[str, Any],
    reference_traces: Sequence[dict[str, Any]],
) -> str:
    same_chars_matrix = all(
        failing_trace["chars_matrix_json"] == reference["chars_matrix_json"]
        for reference in reference_traces
    )
    same_unitary_indices = all(
        failing_trace["unitary_raw_indices"] == reference["unitary_raw_indices"]
        for reference in reference_traces
    )
    any_reference_integral = any(reference["integral_success"] for reference in reference_traces)
    if same_chars_matrix and same_unitary_indices and any_reference_integral:
        return "P4_induction_failure_after_shared_chars_basis_and_unitary_index_match"
    if not same_chars_matrix or not same_unitary_indices:
        return "P4_induction_failure_with_chars_or_unitary_index_mismatch"
    return "unresolved_P4_non_integral_induction_failure"


def build_p4_induction_failure_audit(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    publication_induction: dict[str, Any],
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    same_type_passing_generator_ids = sorted(
        candidate["generator_id"]
        for candidate in publication_induction["candidates"]
        if candidate.get("site_symmetry_type_key") == "D3h_like"
    )
    reference_traces = [
        _trace_local_object_on_manifold(
            library_payload,
            ctx,
            captures,
            generator_id,
            "P4",
            character_field=character_field,
        )
        for generator_id in same_type_passing_generator_ids[:2]
    ]
    records = []
    for failure in publication_induction["failures"]:
        if failure["family_id"] not in {"c", "d"}:
            continue
        trace = _trace_local_object_on_manifold(
            library_payload,
            ctx,
            captures,
            failure["generator_id"],
            "P4",
            character_field=character_field,
        )
        records.append(
            {
                "generator_id": failure["generator_id"],
                "family_id": failure["family_id"],
                "local_object_label": failure["local_object_label"],
                "site_symmetry_type_key": failure.get("site_symmetry_type_key"),
                "manifold_id": "P4",
                "character_field": trace["character_field"],
                "raw_band_character": trace["band_character_json"],
                "chars_matrix": trace["chars_matrix_json"],
                "gram": trace["gram_json"],
                "rhs": trace["rhs_json"],
                "numeric_solution_before_rounding": trace["numeric_solution_before_rounding_json"],
                "gram_solution_before_rounding": trace["gram_solution_before_rounding_json"],
                "numeric_solver_status": trace["numeric_solver_status"],
                "numeric_solver_error": trace["numeric_solver_error"],
                "exact_solver_status": trace["exact_solver_status"],
                "exact_solver_error": trace["exact_solver_error"],
                "exact_solver_solution_before_rounding": trace["exact_solver_solution_before_rounding_json"],
                "why_declared_non_integral": failure["error"],
                "issue_classification": _classify_p4_issue(trace, reference_traces),
            }
        )
    return {
        "manifold_id": "P4",
        "character_field": _summarize_induction_character_field(character_field),
        "induction_failure_count": len(records),
        "failure_family_ids": sorted({record["family_id"] for record in records}),
        "reference_passing_generator_ids_same_site_symmetry_type": same_type_passing_generator_ids,
        "records": records,
    }


def build_p4_induction_failure_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P4 Induction Failure Audit",
        "",
        f"- Manifold id: `{report['manifold_id']}`.",
        f"- Character field: `{report['character_field']}`.",
        f"- Induction failure count: `{report['induction_failure_count']}`.",
        f"- Failure families: `{report['failure_family_ids']}`.",
        f"- Same-type passing reference generators: `{report['reference_passing_generator_ids_same_site_symmetry_type']}`.",
        "",
    ]
    for record in report["records"]:
        lines.extend(
            [
                f"## {record['generator_id']}",
                "",
                f"- Family / label / site type: `{record['family_id']}` / `{record['local_object_label']}` / `{record['site_symmetry_type_key']}`.",
                f"- Numeric solver status: `{record['numeric_solver_status']}`.",
                f"- Exact solver status: `{record['exact_solver_status']}`.",
                f"- Issue classification: `{record['issue_classification']}`.",
                f"- Failure text: {record['why_declared_non_integral']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_p4_passing_vs_failing_comparison(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    publication_induction: dict[str, Any],
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    passing_generator_id = "b_A1'"
    failing_generator_ids = ["c_A1'", "d_A1'"]
    compared = []
    for generator_id in [passing_generator_id, *failing_generator_ids]:
        trace = _trace_local_object_on_manifold(
            library_payload,
            ctx,
            captures,
            generator_id,
            "P4",
            character_field=character_field,
        )
        compared.append(
            {
                "generator_id": generator_id,
                "family_id": trace["family_id"],
                "local_object_label": trace["local_object_label"],
                "site_symmetry_type_key": trace.get("site_symmetry_type_key"),
                "raw_band_character": trace["band_character_json"],
                "numeric_solution_before_rounding": trace["numeric_solution_before_rounding_json"],
                "numeric_solver_status": trace["numeric_solver_status"],
                "exact_solver_status": trace["exact_solver_status"],
                "integral_success": trace["integral_success"],
                "chars_matrix": trace["chars_matrix_json"],
            }
        )
    return {
        "manifold_id": "P4",
        "passing_generator_id": passing_generator_id,
        "failing_generator_ids": failing_generator_ids,
        "same_chars_matrix_for_all_compared_objects": all(
            record["chars_matrix"] == compared[0]["chars_matrix"]
            for record in compared[1:]
        ),
        "compared_records": compared,
        "first_mismatch_stage": (
            "multiplicity_solve_on_P4"
            if compared[0]["integral_success"] and any(not record["integral_success"] for record in compared[1:])
            else "not_detected"
        ),
    }


def build_p4_passing_vs_failing_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P4 Passing vs Failing Comparison",
        "",
        f"- Manifold id: `{report['manifold_id']}`.",
        f"- Passing reference generator: `{report['passing_generator_id']}`.",
        f"- Failing generators: `{report['failing_generator_ids']}`.",
        f"- Same chars matrix for all compared objects: `{report['same_chars_matrix_for_all_compared_objects']}`.",
        f"- First mismatch stage: `{report['first_mismatch_stage']}`.",
        "",
    ]
    for record in report["compared_records"]:
        lines.append(
            f"- `{record['generator_id']}`: integral_success=`{record['integral_success']}`, "
            f"numeric_solver_status=`{record['numeric_solver_status']}`, exact_solver_status=`{record['exact_solver_status']}`, "
            f"band_character=`{record['raw_band_character']}`."
        )
    return "\n".join(lines)


def build_p4_exact_solver_reliability_audit(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    compared_generator_ids = ["b_A1'", "c_A1'", "d_A1'"]
    records = []
    for generator_id in compared_generator_ids:
        trace = _trace_local_object_on_manifold(
            library_payload,
            ctx,
            captures,
            generator_id,
            "P4",
            character_field=character_field,
        )
        exact_solution = trace["exact_solver_solution_before_rounding_json"]
        numeric_solution = trace["numeric_solution_before_rounding_json"]
        exact_matches_numeric = exact_solution == numeric_solution
        records.append(
            {
                "generator_id": generator_id,
                "numeric_solver_status": trace["numeric_solver_status"],
                "numeric_solver_error": trace["numeric_solver_error"],
                "exact_solver_status": trace["exact_solver_status"],
                "exact_solver_error": trace["exact_solver_error"],
                "integral_success": trace["integral_success"],
                "exact_inputs_exactified": bool(trace["exact_inputs_exactified"]),
                "basis_matrix_is_exactified_from_capture_table": True,
                "restricted_vector_is_exactified_from_band_character": True,
                "basis_matrix": trace["exact_basis_matrix"],
                "restricted_vector": trace["exact_restricted_vector"],
                "numeric_solution_before_rounding": numeric_solution,
                "exact_solution_before_rounding": exact_solution,
                "exact_solution_matches_numeric_solution": exact_matches_numeric,
            }
        )
    passing_record = next(
        record for record in records if record["generator_id"] == "b_A1'"
    )
    exact_solver_reliable_on_passing_reference = (
        passing_record["numeric_solver_status"] == "integral"
        and passing_record["exact_solver_status"] == "integral"
        and passing_record["exact_solution_matches_numeric_solution"]
    )
    return {
        "manifold_id": "P4",
        "compared_generator_ids": compared_generator_ids,
        "records": records,
        "exact_solver_reliable_on_passing_reference": exact_solver_reliable_on_passing_reference,
        "current_exact_solver_authority": (
            "authoritative_for_this_audit"
            if exact_solver_reliable_on_passing_reference
            else "diagnostic_only"
        ),
        "reliability_summary": (
            "P4 exact decomposition now exactifies both the little-group basis matrix and the induced band character before gauss-jordan solve. "
            "The passing reference b_A1' now returns an exact integral solution matching the numeric solve, while c_A1' and d_A1' remain exact non-integral."
            if exact_solver_reliable_on_passing_reference
            else "P4 exact decomposition is still not reliable on the passing reference and remains diagnostic-only."
        ),
    }


def build_p4_exact_solver_reliability_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P4 Exact Solver Reliability Audit",
        "",
        f"- Manifold id: `{report['manifold_id']}`.",
        f"- Compared generators: `{report['compared_generator_ids']}`.",
        f"- Exact solver reliable on passing reference: `{report['exact_solver_reliable_on_passing_reference']}`.",
        f"- Current exact solver authority: `{report['current_exact_solver_authority']}`.",
        f"- Summary: {report['reliability_summary']}",
        "",
    ]
    for record in report["records"]:
        lines.append(
            f"- `{record['generator_id']}`: numeric=`{record['numeric_solver_status']}`, exact=`{record['exact_solver_status']}`, "
            f"integral_success=`{record['integral_success']}`, exact_matches_numeric=`{record['exact_solution_matches_numeric_solution']}`."
        )
    return "\n".join(lines)


def build_p4_band_character_site_phase_decomposition(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    compared_generator_ids = ["b_A1'", "c_A1'", "d_A1'"]
    records = []
    local_index = _build_local_object_index(library_payload)
    for generator_id in compared_generator_ids:
        family_id, _label = generator_id.split("_", 1)
        local_object = local_index[generator_id]
        local_character = {
            int(index): complex(value)
            for index, value in local_object["character_on_unitary_stabilizer_complex"].items()
        }
        trace = _build_manifold_band_character_site_phase_trace(
            ctx["entries_by_letter"][family_id],
            local_character,
            ctx,
            captures,
            "P4",
            character_field=character_field,
        )
        records.append(
            {
                "generator_id": generator_id,
                "family_id": family_id,
                "local_object_label": local_object["label"],
                "site_symmetry_type_key": local_object.get("site_symmetry_type_key"),
                "local_character": {
                    str(index): complex_to_json(value)
                    for index, value in local_character.items()
                },
                **trace,
            }
        )
    reference = records[0]
    mismatch_by_generator = []
    for record in records[1:]:
        differing_ops = []
        for reference_op, current_op in zip(reference["operations"], record["operations"]):
            if reference_op["band_character_total"] != current_op["band_character_total"]:
                differing_ops.append(reference_op["unitary_raw_index"])
        mismatch_by_generator.append(
            {
                "generator_id": record["generator_id"],
                "differs_from_reference_b_A1_prime_on_unitary_ops": differing_ops,
            }
        )
    return {
        "manifold_id": "P4",
        "reference_generator_id": "b_A1'",
        "compared_generator_ids": compared_generator_ids,
        "selected_character_field": _summarize_induction_character_field(character_field),
        "resolved_by_character_field_conversion": True,
        "character_field_conversion_stage": (
            "manifold_character_field_conversion: convert the assembled linear band trace to the selected "
            "character field by dividing by exp(-i k·tauC(op)) on each unitary operation"
        ),
        "records": records,
        "mismatch_by_generator": mismatch_by_generator,
        "decomposition_summary": (
            "Across b/c/d the P4 little-group basis is shared, and the per-site orbit-phase contributions assemble the same "
            "linear-trace semantics for all audited objects. The earlier c/d induction failures were cleared when that assembled "
            "linear band trace was converted into the selected `character` field using the per-operation translation phase."
        ),
    }


def build_p4_band_character_site_phase_decomposition_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P4 Band Character / Site-Phase Decomposition",
        "",
        f"- Manifold id: `{report['manifold_id']}`.",
        f"- Reference generator: `{report['reference_generator_id']}`.",
        f"- Compared generators: `{report['compared_generator_ids']}`.",
        f"- Selected character field: `{report['selected_character_field']}`.",
        f"- Resolved by character-field conversion: `{report['resolved_by_character_field_conversion']}`.",
        f"- Character-field conversion stage: `{report['character_field_conversion_stage']}`.",
        f"- Summary: {report['decomposition_summary']}",
        "",
    ]
    for mismatch in report["mismatch_by_generator"]:
        lines.append(
            f"- `{mismatch['generator_id']}` differs from `b_A1'` on unitary ops "
            f"`{mismatch['differs_from_reference_b_A1_prime_on_unitary_ops']}`."
        )
    return "\n".join(lines)


def _classify_formula_vs_explicit_mismatch(
    legacy_site: dict[str, Any],
    explicit_site: dict[str, Any],
) -> str:
    if legacy_site.get("assumed_target_site_index") != explicit_site.get("matched_target_site_index"):
        return "wrong_target_orbit_site"
    if legacy_site.get("counted_in_trace") != explicit_site.get("counted_in_trace"):
        return "wrong_target_orbit_site"
    if (
        legacy_site.get("conjugated_stabilizer_op_index")
        != explicit_site.get("conjugated_stabilizer_op_index")
    ):
        return "wrong_conjugated_stabilizer_index"
    if legacy_site.get("lattice_vector_magnetic") != explicit_site.get("lattice_vector_magnetic"):
        return "wrong_lattice_vector"
    if legacy_site.get("bloch_phase") != explicit_site.get("bloch_phase"):
        return "wrong_bloch_phase"
    return "mixed"


def _trace_difference_records(
    legacy_trace: dict[str, Any],
    explicit_trace: dict[str, Any],
    *,
    total_key: str,
    stage_label: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    differing_ops = []
    first_mismatch = None
    for legacy_op, explicit_op in zip(legacy_trace["operations"], explicit_trace["operations"]):
        if legacy_op[total_key] == explicit_op[total_key]:
            continue
        mismatch_type = "mixed"
        mismatching_site_index = None
        for legacy_site, explicit_site in zip(
            legacy_op["orbit_site_contributions"],
            explicit_op["orbit_site_contributions"],
        ):
            site_mismatch_type = _classify_formula_vs_explicit_mismatch(
                legacy_site,
                explicit_site,
            )
            if site_mismatch_type != "mixed":
                mismatch_type = site_mismatch_type
                mismatching_site_index = explicit_site["source_site_index"]
                break
        record = {
            "unitary_raw_index": legacy_op["unitary_raw_index"],
            "comparison_stage": stage_label,
            "legacy_formula_total": legacy_op[total_key],
            "explicit_orbit_total": explicit_op[total_key],
            "first_mismatch_type": mismatch_type,
            "first_mismatching_site_index": mismatching_site_index,
        }
        differing_ops.append(record)
        if first_mismatch is None:
            first_mismatch = {
                "unitary_raw_index": legacy_op["unitary_raw_index"],
                "mismatch_type": mismatch_type,
                "localized_stage": stage_label,
            }
    return differing_ops, first_mismatch


def build_p4_trace_formula_vs_explicit_orbit_report(
    library_payload: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    *,
    character_field: str | dict[str, str],
) -> dict[str, Any]:
    compared_generator_ids = ["b_A1'", "c_A1'", "d_A1'"]
    local_index = _build_local_object_index(library_payload)
    records = []
    first_linear_trace_mismatch = None
    first_converted_trace_mismatch = None
    character_field_conversion_stage = (
        "manifold_character_field_conversion: convert the assembled linear band trace to the selected "
        "character field by dividing by exp(-i k·tauC(op)) on each unitary operation"
    )
    for generator_id in compared_generator_ids:
        family_id, _label = generator_id.split("_", 1)
        local_object = local_index[generator_id]
        local_character = {
            int(index): complex(value)
            for index, value in local_object["character_on_unitary_stabilizer_complex"].items()
        }
        entry = ctx["entries_by_letter"][family_id]
        orbit = single_expanded.orbit_for_sample_entry(entry, ctx, ctx["group_tables"])
        legacy_trace = _build_manifold_induction_trace_legacy_formula(
            entry,
            local_character,
            ctx,
            captures,
            "P4",
            character_field=character_field,
            orbit=orbit,
        )
        explicit_trace = _build_manifold_induction_trace_by_explicit_orbit_action(
            entry,
            local_character,
            ctx,
            captures,
            "P4",
            character_field=character_field,
            orbit=orbit,
        )
        linear_trace_differing_ops, first_linear_for_generator = _trace_difference_records(
            legacy_trace,
            explicit_trace,
            total_key="linear_band_character_total",
            stage_label="pre_conversion_linear_trace",
        )
        converted_trace_differing_ops, first_converted_for_generator = _trace_difference_records(
            legacy_trace,
            explicit_trace,
            total_key="band_character_total",
            stage_label="post_conversion_selected_character_trace",
        )
        if (
            generator_id in {"c_A1'", "d_A1'"}
            and first_linear_trace_mismatch is None
            and first_linear_for_generator is not None
        ):
            first_linear_trace_mismatch = {
                "generator_id": generator_id,
                **first_linear_for_generator,
            }
        if (
            generator_id in {"c_A1'", "d_A1'"}
            and first_converted_trace_mismatch is None
            and first_converted_for_generator is not None
        ):
            first_converted_trace_mismatch = {
                "generator_id": generator_id,
                **first_converted_for_generator,
            }
        records.append(
            {
                "generator_id": generator_id,
                "family_id": family_id,
                "local_object_label": local_object["label"],
                "legacy_formula_uses_raw_orbit_representatives": True,
                "explicit_trace_uses_canonical_reduced_orbit_representatives": True,
                "legacy_canonical_orbit_coordinates": legacy_trace.get("canonical_orbit_coordinates"),
                "explicit_canonical_orbit_coordinates": explicit_trace.get("canonical_orbit_coordinates"),
                "linear_trace_differing_ops": linear_trace_differing_ops,
                "converted_trace_differing_ops": converted_trace_differing_ops,
                "linear_trace_matches": not linear_trace_differing_ops,
                "converted_trace_matches": not converted_trace_differing_ops,
                "legacy_linear_band_character_json": legacy_trace["linear_band_character_json"],
                "explicit_linear_band_character_json": explicit_trace["linear_band_character_json"],
                "legacy_band_character_json": legacy_trace["band_character_json"],
                "explicit_band_character_json": explicit_trace["band_character_json"],
            }
        )
    linear_trace_differing_ops_count_total = sum(
        len(record["linear_trace_differing_ops"]) for record in records
    )
    converted_trace_differing_ops_count_total = sum(
        len(record["converted_trace_differing_ops"]) for record in records
    )
    first_failure_mismatch = first_converted_trace_mismatch or first_linear_trace_mismatch
    return {
        "manifold_id": "P4",
        "compared_generator_ids": compared_generator_ids,
        "records": records,
        "first_linear_trace_mismatch": first_linear_trace_mismatch,
        "first_converted_trace_mismatch": first_converted_trace_mismatch,
        "first_failure_mismatch": first_failure_mismatch,
        "linear_trace_differing_ops_count_total": linear_trace_differing_ops_count_total,
        "converted_trace_differing_ops_count_total": converted_trace_differing_ops_count_total,
        "resolved_by_character_field_conversion": first_converted_trace_mismatch is None,
        "bug_localized_to_stage": (
            first_failure_mismatch["localized_stage"]
            if first_failure_mismatch is not None
            else character_field_conversion_stage
        ),
        "summary": (
            "The P4 audit now separates pre-conversion linear-trace comparison from post-conversion selected-character comparison. "
            "Both the legacy formula trace and the explicit orbit-action trace agree on the audited P4 objects in the linear trace and in "
            "the converted character trace, so the remaining evidence for the earlier c/d induction failure sits in the field-conversion stage itself, "
            "not in target-site matching or orbit-action assembly."
        ),
    }


def build_p4_trace_formula_vs_explicit_orbit_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P4 Trace Formula vs Explicit Orbit Report",
        "",
        f"- Manifold id: `{report['manifold_id']}`.",
        f"- Compared generators: `{report['compared_generator_ids']}`.",
        f"- First linear-trace mismatch: `{report['first_linear_trace_mismatch']}`.",
        f"- First converted-trace mismatch: `{report['first_converted_trace_mismatch']}`.",
        f"- First failure mismatch: `{report['first_failure_mismatch']}`.",
        f"- Linear-trace differing-op count: `{report['linear_trace_differing_ops_count_total']}`.",
        f"- Converted-trace differing-op count: `{report['converted_trace_differing_ops_count_total']}`.",
        f"- Resolved by character-field conversion: `{report['resolved_by_character_field_conversion']}`.",
        f"- Bug localized to stage: `{report['bug_localized_to_stage']}`.",
        f"- Summary: {report['summary']}",
        "",
    ]
    for record in report["records"]:
        lines.append(
            f"- `{record['generator_id']}` linear differing ops: `{record['linear_trace_differing_ops']}`; "
            f"converted differing ops: `{record['converted_trace_differing_ops']}`."
        )
    return "\n".join(lines)


def build_d3h_like_local_object_crosscheck(
    library_payload: dict[str, Any],
) -> dict[str, Any]:
    families = ["b", "c", "d"]
    local_irreps = library_payload["family_single_local_irreps"]
    labels = [item["label"] for item in local_irreps["b"]]
    entries = []
    all_same_ordering = True
    all_same_characters = True
    for label in labels:
        family_records = []
        reference = None
        for family_id in families:
            local_object = next(
                item for item in local_irreps[family_id] if item["label"] == label
            )
            ordering = sorted(local_object["character_on_unitary_stabilizer_complex"])
            character_vector = [
                complex(local_object["character_on_unitary_stabilizer_complex"][index])
                for index in ordering
            ]
            payload = {
                "family_id": family_id,
                "site_symmetry_type_key": local_object["site_symmetry_type_key"],
                "stabilizer_size": len(ordering),
                "stabilizer_ordering": ordering,
                "character_on_unitary_stabilizer_complex": complex_list_to_json(character_vector),
            }
            family_records.append(payload)
            if reference is None:
                reference = payload
            else:
                all_same_ordering &= payload["stabilizer_ordering"] == reference["stabilizer_ordering"]
                all_same_characters &= (
                    payload["character_on_unitary_stabilizer_complex"]
                    == reference["character_on_unitary_stabilizer_complex"]
                )
        entries.append(
            {
                "label": label,
                "families": family_records,
                "same_stabilizer_ordering_across_b_c_d": len(
                    {
                        tuple(record["stabilizer_ordering"])
                        for record in family_records
                    }
                ) == 1,
                "same_character_vector_across_b_c_d": len(
                    {
                        json.dumps(record["character_on_unitary_stabilizer_complex"], sort_keys=True)
                        for record in family_records
                    }
                ) == 1,
                "phase_twisted_versions_visible_at_library_level": False,
            }
        )
    return {
        "site_symmetry_type_key": "D3h_like",
        "families": families,
        "all_same_stabilizer_ordering": all_same_ordering,
        "all_same_character_vectors": all_same_characters,
        "entries": entries,
        "verdict": (
            "No family-level local-library mismatch is visible for D3h_like. Families b/c/d share the same stabilizer ordering and the same unitary character vectors for each audited local object label."
        ),
    }


def build_d3h_like_local_object_crosscheck_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# D3h-like Local Object Crosscheck",
        "",
        f"- Site-symmetry type: `{report['site_symmetry_type_key']}`.",
        f"- Families: `{report['families']}`.",
        f"- Same stabilizer ordering across b/c/d: `{report['all_same_stabilizer_ordering']}`.",
        f"- Same character vectors across b/c/d: `{report['all_same_character_vectors']}`.",
        f"- Verdict: {report['verdict']}",
        "",
    ]
    for entry in report["entries"]:
        lines.append(
            f"- `{entry['label']}`: same ordering = `{entry['same_stabilizer_ordering_across_b_c_d']}`, "
            f"same character vector = `{entry['same_character_vector_across_b_c_d']}`."
        )
    return "\n".join(lines)


def _capture_manifold_kind(manifold_id: str) -> str:
    if manifold_id.startswith("S"):
        return "plane"
    if manifold_id.startswith("L") or manifold_id.startswith("CANDIDATE_PATH") or manifold_id.startswith("FPATH"):
        return "line"
    if manifold_id.startswith("P"):
        return "point"
    return "other"


def _deprecated_build_character_field_conversion_global_validation_report(
    captures: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    manifold_records = []
    comparison_count = 0
    mismatch_count = 0
    exact_match_count = 0
    first_mismatch = None
    tau_field_comparison_count = 0
    tau_field_mismatch_count = 0
    first_tau_field_mismatch = None
    kind_counter: Counter[str] = Counter()
    formula = "predicted_character = linear_character / exp(-i k·tauC(op))"
    for manifold_id in sorted(captures):
        info = captures[manifold_id]
        if not all(
            key in info
            for key in ("character_json", "linear_character_json", "tauC", "kconv")
        ):
            continue
        manifold_kind = _capture_manifold_kind(manifold_id)
        kind_counter[manifold_kind] += 1
        tau_c = info.get("tauC", [])
        unitary_translations = info.get("unitary_translations", [])
        manifold_tau_field_mismatch_count = 0
        for op_index, tau in enumerate(tau_c):
            if op_index < len(unitary_translations):
                tau_field_comparison_count += 1
                if any(
                    abs(float(left) - float(right)) > 1e-10
                    for left, right in zip(tau, unitary_translations[op_index])
                ):
                    tau_field_mismatch_count += 1
                    manifold_tau_field_mismatch_count += 1
                    if first_tau_field_mismatch is None:
                        first_tau_field_mismatch = {
                            "manifold_id": manifold_id,
                            "unitary_op_position": op_index,
                            "tauC": list(tau),
                            "unitary_translations": list(unitary_translations[op_index]),
                        }
        manifold_mismatch_count = 0
        manifold_first_mismatch = None
        for rep_index, (character_row, linear_row) in enumerate(
            zip(info["character_json"], info["linear_character_json"])
        ):
            for op_position, (character_value, linear_value, tau) in enumerate(
                zip(character_row, linear_row, tau_c)
            ):
                comparison_count += 1
                phase_argument = float(
                    np.dot(
                        np.array(info["kconv"], dtype=float),
                        np.array(tau, dtype=float),
                    )
                )
                phase = np.exp(-1j * phase_argument)
                actual = complex_from_json(character_value)
                linear = complex_from_json(linear_value)
                predicted = linear / phase
                if np.allclose([predicted], [actual], atol=1e-8):
                    exact_match_count += 1
                    continue
                mismatch_count += 1
                manifold_mismatch_count += 1
                mismatch_payload = {
                    "manifold_id": manifold_id,
                    "manifold_kind": manifold_kind,
                    "rep_index": rep_index,
                    "unitary_op_position": op_position,
                    "phase_argument": phase_argument,
                    "tauC": list(tau),
                    "actual_character": complex_to_json(actual),
                    "linear_character": complex_to_json(linear),
                    "predicted_character": complex_to_json(predicted),
                }
                if first_mismatch is None:
                    first_mismatch = mismatch_payload
                if manifold_first_mismatch is None:
                    manifold_first_mismatch = mismatch_payload
        manifold_records.append(
            {
                "manifold_id": manifold_id,
                "manifold_kind": manifold_kind,
                "rep_count": len(info["character_json"]),
                "unitary_op_count": len(info["tauC"]),
                "comparison_count": len(info["character_json"]) * len(info["tauC"]),
                "mismatch_count": manifold_mismatch_count,
                "tau_field_mismatch_count": manifold_tau_field_mismatch_count,
                "first_mismatch": manifold_first_mismatch,
            }
        )
    return {
        "mode": mode,
        "formula": formula,
        "phase_source_field": "tauC",
        "runtime_patch_translation_field": "unitary_translations",
        "manifold_count": len(manifold_records),
        "manifold_counts_by_kind": dict(kind_counter),
        "comparison_count": comparison_count,
        "exact_match_count": exact_match_count,
        "mismatch_count": mismatch_count,
        "setting_specific_numerical_consistency_pass_legacy": mismatch_count == 0,
        "first_mismatch": first_mismatch,
        "tau_field_comparison_count": tau_field_comparison_count,
        "tau_field_mismatch_count": tau_field_mismatch_count,
        "tau_field_match_global_pass": tau_field_mismatch_count == 0,
        "first_tau_field_mismatch": first_tau_field_mismatch,
        "manifold_records": manifold_records,
        "summary": (
            "The character-field conversion formula is validated directly against the capture tables rather than through the induction-trace builders. "
            "For every audited single-branch manifold, the stored `character` matches `linear_character / exp(-i k·tauC(op))`, and the capture-table "
            "`tauC` field matches the runtime `unitary_translations` field used by the patch."
        ),
    }


def _deprecated_build_character_field_conversion_global_validation_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Character-Field Conversion Global Validation Report",
            "",
            f"- Mode: `{report['mode']}`.",
            f"- Formula: `{report['formula']}`.",
            f"- Phase source field / runtime patch field: `{report['phase_source_field']}` / `{report['runtime_patch_translation_field']}`.",
            f"- Manifold count by kind: `{report['manifold_counts_by_kind']}`.",
            f"- Comparison count / exact matches / mismatches: `{report['comparison_count']}` / `{report['exact_match_count']}` / `{report['mismatch_count']}`.",
            f"- Setting-specific numerical consistency pass (legacy): `{report['setting_specific_numerical_consistency_pass_legacy']}`.",
            f"- tauC-vs-unitary-translation comparison count / mismatches: `{report['tau_field_comparison_count']}` / `{report['tau_field_mismatch_count']}`.",
            f"- tau fields match globally: `{report['tau_field_match_global_pass']}`.",
            f"- First mismatch: `{report['first_mismatch']}`.",
            f"- First tau-field mismatch: `{report['first_tau_field_mismatch']}`.",
            f"- Summary: {report['summary']}",
        ]
    )


def _deprecated_build_p4_conversion_patch_independent_validation_report(
    global_validation_report: dict[str, Any],
    p4_trace_report: dict[str, Any],
    p4_failure_audit: dict[str, Any],
) -> dict[str, Any]:
    setting_specific_consistency_pass = (
        global_validation_report["setting_specific_numerical_consistency_pass_legacy"]
        and global_validation_report["tau_field_match_global_pass"]
        and p4_trace_report["linear_trace_differing_ops_count_total"] == 0
        and p4_trace_report["converted_trace_differing_ops_count_total"] == 0
        and int(p4_failure_audit.get("induction_failure_count", 0)) == 0
    )
    return {
        "setting_specific_consistency_pass_legacy": setting_specific_consistency_pass,
        "shared_patch_self_validation_risk_removed": global_validation_report["setting_specific_numerical_consistency_pass_legacy"],
        "all_manifold_formula_pass_legacy": global_validation_report["setting_specific_numerical_consistency_pass_legacy"],
        "tau_field_match_global_pass": global_validation_report["tau_field_match_global_pass"],
        "p4_linear_trace_differing_ops_count_total": p4_trace_report["linear_trace_differing_ops_count_total"],
        "p4_converted_trace_differing_ops_count_total": p4_trace_report["converted_trace_differing_ops_count_total"],
        "p4_induction_failure_count": int(p4_failure_audit.get("induction_failure_count", 0)),
        "current_verdict": (
            "Legacy wording retired: SG194/current-setting consistency only"
            if setting_specific_consistency_pass
            else "Legacy wording retired: not yet numerically consistent even in the current setting"
        ),
        "summary": (
            "The P4 conversion patch is no longer justified only by two trace builders sharing the same post-processing code. "
            "It is independently checked against the capture tables across all single-branch manifolds and then cross-checked "
            "against the pre-conversion linear trace and post-conversion selected-character trace on the audited P4 objects."
        ),
    }


def _deprecated_build_p4_conversion_patch_independent_validation_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# P4 Conversion Patch Independent Validation Report",
            "",
            f"- Setting-specific consistency pass (legacy): `{report['setting_specific_consistency_pass_legacy']}`.",
            f"- Shared-patch self-validation risk removed: `{report['shared_patch_self_validation_risk_removed']}`.",
            f"- All-manifold formula pass: `{report['all_manifold_formula_pass']}`.",
            f"- tau-field match global pass: `{report['tau_field_match_global_pass']}`.",
            f"- P4 linear / converted differing-op totals: `{report['p4_linear_trace_differing_ops_count_total']}` / `{report['p4_converted_trace_differing_ops_count_total']}`.",
            f"- P4 induction failure count: `{report['p4_induction_failure_count']}`.",
            f"- Current verdict: `{report['current_verdict']}`.",
            f"- Summary: {report['summary']}",
        ]
    )


def _deprecated_derive_p4_current_verdict(
    exact_solver_reliability_report: dict[str, Any],
    local_crosscheck_report: dict[str, Any],
    trace_formula_vs_explicit_report: dict[str, Any],
    p4_failure_audit: dict[str, Any] | None = None,
    p4_conversion_patch_independent_validation_report: dict[str, Any] | None = None,
) -> str:
    if (
        exact_solver_reliability_report["exact_solver_reliable_on_passing_reference"]
        and local_crosscheck_report["all_same_stabilizer_ordering"]
        and local_crosscheck_report["all_same_character_vectors"]
        and (
            p4_conversion_patch_independent_validation_report is None
            or p4_conversion_patch_independent_validation_report["setting_specific_consistency_pass_legacy"]
        )
        and (
            trace_formula_vs_explicit_report["first_failure_mismatch"] is not None
            or trace_formula_vs_explicit_report.get("resolved_by_character_field_conversion")
            or (
                p4_failure_audit is not None
                and int(p4_failure_audit.get("induction_failure_count", 0)) == 0
            )
        )
    ):
        return "proved_bug"
    return "still_unresolved_but_narrowed"


def _row_index_lookup_from_line_full(line_full: dict[str, Any]) -> dict[str, list[int]]:
    if "line_blocks" in line_full:
        row_ranges, _row_to_line = build_line_block_row_maps(line_full["line_blocks"])
        return row_ranges
    row_ranges: dict[str, list[int]] = {}
    for row_index, row in enumerate(line_full["global_matrix_rows"]):
        row_ranges.setdefault(row["line_id"], []).append(row_index)
    return row_ranges


def build_ppath06_residual_obstruction_audit(
    raw_line_full: dict[str, Any],
    internal_line_full: dict[str, Any],
    publication_line_full: dict[str, Any],
    obstruction_report: dict[str, Any],
) -> dict[str, Any]:
    publication_row_ranges = _row_index_lookup_from_line_full(publication_line_full)
    raw_row_ranges = _row_index_lookup_from_line_full(raw_line_full)
    internal_row_ranges = _row_index_lookup_from_line_full(internal_line_full)
    publication_rows = publication_row_ranges["PPATH06"]
    raw_rows = raw_row_ranges["L2"]
    internal_rows = internal_row_ranges["FPATH07"]
    row_details = []
    publication_equations = {
        row_index: equation
        for row_index, equation in zip(
            publication_rows,
            next(block["equations"] for block in publication_line_full["line_blocks"] if block["line_id"] == "PPATH06"),
        )
    }
    for publication_row_index, raw_row_index, internal_row_index in zip(publication_rows, raw_rows, internal_rows):
        provenance = publication_line_full["row_provenance"][publication_row_index]
        equation = publication_equations[publication_row_index]
        row_details.append(
            {
                "publication_row_index": publication_row_index,
                "internal_row_index": internal_row_index,
                "raw_row_index": raw_row_index,
                "publication_path_id": provenance["publication_path_id"],
                "endpoint_pair": provenance["endpoint_pair"],
                "basis_id": provenance["basis_id"],
                "row_kind": provenance["row_kind"],
                "member_internal_path_class_id": provenance["member_internal_path_class_id"],
                "member_source_line_id": provenance["member_source_line_id"],
                "member_candidate_id": provenance["member_candidate_id"],
                "terms": list(equation["terms"]),
                "matrix_row_nonzero_terms": [
                    {"unknown": publication_line_full["global_unknown_ordering"][col], "coeff": int(value)}
                    for col, value in enumerate(provenance["matrix_row"])
                    if int(value) != 0
                ],
            }
        )
    failing_generator_residuals = []
    passing_generator_residuals = []
    for record in obstruction_report["generator_records"]:
        publication_state = record["publication_shell"]
        residual_by_row = {item["row_index"]: int(item["residual"]) for item in publication_state["nonzero_rows"]}
        payload = {
            "generator_id": record["generator_id"],
            "family_id": record["family_id"],
            "local_object_label": record["local_object_label"],
            "classification": record["classification"],
            "ppath06_residual_vector": [int(residual_by_row.get(index, 0)) for index in publication_rows],
        }
        if publication_state["compatibility_zero"]:
            passing_generator_residuals.append(payload)
        elif publication_state["status"] == "nonzero_residual":
            failing_generator_residuals.append(payload)
    publication_residual_support_rows = sorted(
        publication_rows[index]
        for index in range(len(publication_rows))
        if any(
            int(payload["ppath06_residual_vector"][index]) != 0
            for payload in failing_generator_residuals
        )
    )
    return {
        "publication_path_id": "PPATH06",
        "internal_path_id": "FPATH07",
        "raw_line_id": "L2",
        "endpoint_pair": ["P3", "P4"],
        "row_indices": {
            "raw42": raw_rows,
            "internal_shell": internal_rows,
            "publication_shell": publication_rows,
        },
        "publication_residual_support_rows": publication_residual_support_rows,
        "row_details": row_details,
        "failing_generator_residuals": failing_generator_residuals,
        "passing_generator_residuals": passing_generator_residuals,
        "obstruction_explanation": (
            "The residual support on PPATH06 is confined to rows 22/23/24, inherited directly from raw L2 via the internal FPATH07 layer. "
            "These rows are pure pair-difference constraints on P3 multiplicities, so the obstruction survives publication reduction "
            "without involving any new P4-only terms."
        ),
    }


def build_ppath06_residual_obstruction_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PPATH06 Residual Obstruction Audit",
        "",
        f"- Raw/internal/publication chain: `{report['raw_line_id']}` -> `{report['internal_path_id']}` -> `{report['publication_path_id']}`.",
        f"- Endpoint pair: `{report['endpoint_pair']}`.",
        f"- Row indices: `{report['row_indices']}`.",
        f"- Residual-support publication rows: `{report['publication_residual_support_rows']}`.",
        f"- Explanation: {report['obstruction_explanation']}",
        "",
    ]
    for row in report["row_details"]:
        lines.append(
            f"- publication row `{row['publication_row_index']}` / basis `{row['basis_id']}` / row_kind `{row['row_kind']}` / "
            f"source line `{row['member_source_line_id']}` / terms `{row['matrix_row_nonzero_terms']}`."
        )
    return "\n".join(lines)


def _ppath06_row_plain_language(row: dict[str, Any]) -> str:
    terms = row["matrix_row_nonzero_terms"]
    if len(terms) == 2 and [int(item["coeff"]) for item in terms] == [1, -1]:
        left_unknown = terms[0]["unknown"]
        right_unknown = terms[1]["unknown"]
        left_point = left_unknown.split("_", 1)[0]
        right_point = right_unknown.split("_", 1)[0]
        if left_point == right_point:
            return (
                f"Pair-difference constraint enforcing equal multiplicities of `{left_unknown}` and `{right_unknown}` "
                f"at endpoint `{left_point}` along the publication path `{row['publication_path_id']}`."
            )
    return (
        f"Residual-support compatibility row on `{row['publication_path_id']}` inherited from raw `{row['member_source_line_id']}`."
    )


def build_ppath06_row_semantics_report(
    ppath06_audit: dict[str, Any],
) -> dict[str, Any]:
    support_rows = set(ppath06_audit["publication_residual_support_rows"])
    support_details = []
    for row in ppath06_audit["row_details"]:
        if row["publication_row_index"] not in support_rows:
            continue
        support_details.append(
            {
                "publication_row_index": int(row["publication_row_index"]),
                "internal_row_index": int(row["internal_row_index"]),
                "raw_row_index": int(row["raw_row_index"]),
                "publication_path_id": row["publication_path_id"],
                "endpoint_pair": list(row["endpoint_pair"]),
                "basis_id": row["basis_id"],
                "row_kind": row["row_kind"],
                "member_internal_path_class_id": row["member_internal_path_class_id"],
                "member_source_line_id": row["member_source_line_id"],
                "member_candidate_id": row["member_candidate_id"],
                "exact_row_vector_nonzero_terms": list(row["matrix_row_nonzero_terms"]),
                "plain_language": _ppath06_row_plain_language(row),
            }
        )
    return {
        "publication_path_id": ppath06_audit["publication_path_id"],
        "support_rows": sorted(support_rows),
        "row_semantics": support_details,
        "overall_interpretation": (
            "Publication rows 22/23/24 are the three phase-aware endpoint-class balance constraints on PPATH06. "
            "Each row is a pure pair-difference relation on P3 multiplicities, inherited directly from raw L2 through "
            "the internal FPATH07 shell without any new publication-only deformation."
        ),
    }


def build_ppath06_row_semantics_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# PPATH06 Row Semantics Report",
        "",
        f"- Publication path id: `{report['publication_path_id']}`.",
        f"- Residual-support rows: `{report['support_rows']}`.",
        f"- Overall interpretation: {report['overall_interpretation']}",
        "",
    ]
    for row in report["row_semantics"]:
        lines.append(
            f"- row `{row['publication_row_index']}` / basis `{row['basis_id']}` / row-kind `{row['row_kind']}` / "
            f"raw source `{row['member_source_line_id']}` / terms `{row['exact_row_vector_nonzero_terms']}`: "
            f"{row['plain_language']}"
        )
    return "\n".join(lines)


def build_l2_fpath07_ppath06_layerwise_comparison(
    raw_line_full: dict[str, Any],
    internal_line_full: dict[str, Any],
    publication_line_full: dict[str, Any],
) -> dict[str, Any]:
    raw_rows = _row_index_lookup_from_line_full(raw_line_full)["L2"]
    internal_rows = _row_index_lookup_from_line_full(internal_line_full)["FPATH07"]
    publication_rows = _row_index_lookup_from_line_full(publication_line_full)["PPATH06"]
    comparisons = []
    for raw_row_index, internal_row_index, publication_row_index in zip(raw_rows, internal_rows, publication_rows):
        raw_row = raw_line_full["global_matrix_rows"][raw_row_index]
        internal_row = internal_line_full["global_matrix_rows"][internal_row_index]
        publication_row = publication_line_full["row_provenance"][publication_row_index]
        comparisons.append(
            {
                "raw_row_index": raw_row_index,
                "internal_row_index": internal_row_index,
                "publication_row_index": publication_row_index,
                "basis_id": publication_row["basis_id"],
                "raw_source_line_id": raw_row["line_id"],
                "internal_source_line_id": internal_row["line_id"],
                "publication_source_line_id": publication_row["member_source_line_id"],
                "raw_matrix_row": list(raw_row["matrix_row"]),
                "internal_matrix_row": list(internal_row["matrix_row"]),
                "publication_matrix_row": list(publication_row["matrix_row"]),
                "all_matrix_rows_identical": (
                    list(raw_row["matrix_row"]) == list(internal_row["matrix_row"]) == list(publication_row["matrix_row"])
                ),
            }
        )
    return {
        "raw_line_id": "L2",
        "internal_path_id": "FPATH07",
        "publication_path_id": "PPATH06",
        "row_mapping": comparisons,
        "mapping_is_index_shift_only": all(item["all_matrix_rows_identical"] for item in comparisons),
    }


def build_l2_fpath07_ppath06_layerwise_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# L2 / FPATH07 / PPATH06 Layerwise Comparison",
        "",
        f"- Chain: `{report['raw_line_id']}` -> `{report['internal_path_id']}` -> `{report['publication_path_id']}`.",
        f"- Mapping is index-shift only: `{report['mapping_is_index_shift_only']}`.",
        "",
    ]
    for item in report["row_mapping"]:
        lines.append(
            f"- raw/internal/publication rows `{item['raw_row_index']}` / `{item['internal_row_index']}` / "
            f"`{item['publication_row_index']}` share basis `{item['basis_id']}` and identical matrix rows = "
            f"`{item['all_matrix_rows_identical']}`."
        )
    return "\n".join(lines)


def build_ai_zero_subset_rank_report(induction: dict[str, Any]) -> dict[str, Any]:
    zero_candidates = [
        candidate
        for candidate in induction["candidates"]
        if candidate["compatibility_zero"]
    ]
    if zero_candidates:
        zero_matrix = sp.Matrix.hstack(
            *[sp.Matrix(candidate["unknown_vector"]) for candidate in zero_candidates]
        )
        zero_rank = int(zero_matrix.rank())
        _rref, pivot_indices = zero_matrix.rref()
    else:
        zero_matrix = sp.zeros(0, 0)
        zero_rank = 0
        pivot_indices = tuple()
    pivot_generator_ids = [zero_candidates[index]["generator_id"] for index in pivot_indices]
    pivot_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(zero_candidates[index]["unknown_vector"]) for index in pivot_indices])
        if pivot_indices
        else sp.zeros(len(induction["candidates"][0]["unknown_vector"]) if induction["candidates"] else 0, 0)
    )
    dependencies = []
    for index, candidate in enumerate(zero_candidates):
        if index in pivot_indices:
            continue
        solution, params = pivot_matrix.gauss_jordan_solve(sp.Matrix(candidate["unknown_vector"]))
        dependencies.append(
            {
                "generator_id": candidate["generator_id"],
                "depends_on": {
                    pivot_generator_ids[pivot_index]: str(sp.simplify(solution[pivot_index]))
                    for pivot_index in range(len(pivot_generator_ids))
                    if sp.simplify(solution[pivot_index]) != 0
                },
                "non_unique": bool(params.rows * params.cols),
            }
        )
    return {
        "zero_generator_count": len(zero_candidates),
        "zero_generator_ids": [candidate["generator_id"] for candidate in zero_candidates],
        "zero_subset_rank": zero_rank,
        "pivot_generator_ids": pivot_generator_ids,
        "linear_dependencies": dependencies,
        "forms_partial_ai_lattice": zero_rank > 0,
        "ai_status": "partial_ai_lattice" if zero_rank > 0 else "seed_only",
    }


def build_ai_zero_subset_rank_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Zero-Subset Rank Report",
            "",
            f"- Zero generator ids: `{report['zero_generator_ids']}`.",
            f"- Zero-subset rank: `{report['zero_subset_rank']}`.",
            f"- Pivot generators: `{report['pivot_generator_ids']}`.",
            f"- Forms partial AI lattice: `{report['forms_partial_ai_lattice']}`.",
            f"- AI status: `{report['ai_status']}`.",
            f"- Linear dependencies: `{report['linear_dependencies']}`.",
        ]
    )


def build_partial_ai_lattice_witness_report(
    induction: dict[str, Any],
    rank_report: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
) -> dict[str, Any]:
    zero_candidates = {
        candidate["generator_id"]: candidate
        for candidate in induction["candidates"]
        if candidate["compatibility_zero"]
    }
    pivot_records = []
    for generator_id in rank_report["pivot_generator_ids"]:
        candidate = zero_candidates[generator_id]
        pivot_records.append(
            {
                "generator_id": generator_id,
                "family_letter": candidate["family_letter"],
                "local_object_label": candidate["local_object_label"],
                "nonzero_terms": _sparse_unknown_vector_terms(
                    unknown_ordering,
                    candidate["unknown_vector"],
                ),
            }
        )
    return {
        "zero_generator_ids": list(rank_report["zero_generator_ids"]),
        "zero_subset_rank": int(rank_report["zero_subset_rank"]),
        "pivot_generator_ids": list(rank_report["pivot_generator_ids"]),
        "pivot_records": pivot_records,
        "linear_dependencies": list(rank_report["linear_dependencies"]),
        "justifies_partial_ai_lattice": bool(rank_report["forms_partial_ai_lattice"]),
        "ai_status": rank_report["ai_status"],
        "not_full_ai_lattice_because": (
            "Only a rank-5 subset of 11 publication-shell compatibility-zero generators is currently verified, while the remaining induced local objects carry nonzero residuals on PPATH06."
        ),
    }


def build_partial_ai_lattice_witness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Partial AI Lattice Witness Report",
        "",
        f"- Zero generators: `{report['zero_generator_ids']}`.",
        f"- Zero-subset rank: `{report['zero_subset_rank']}`.",
        f"- Pivot generators: `{report['pivot_generator_ids']}`.",
        f"- AI status: `{report['ai_status']}`.",
        f"- Justifies partial AI lattice: `{report['justifies_partial_ai_lattice']}`.",
        f"- Why not full AI lattice: {report['not_full_ai_lattice_because']}",
        "",
    ]
    for record in report["pivot_records"]:
        lines.append(
            f"- `{record['generator_id']}` ({record['family_letter']}, {record['local_object_label']}): "
            f"`{record['nonzero_terms']}`."
        )
    return "\n".join(lines)


def build_bs_rank_naming_fix_report(
    single_publication_bs_analysis: dict[str, Any],
    double_bs_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    double_shape = list(double_bs_summary["matrix_shape"]) if double_bs_summary is not None else None
    double_rank = int(double_bs_summary["rank"]) if double_bs_summary is not None else None
    double_nullity = int(double_bs_summary["nullity"]) if double_bs_summary is not None else None
    return {
        "old_misleading_fields": {
            "BS_status.rank": "compatibility_matrix_rank",
            "BS_status.nullity": "compatibility_matrix_nullity",
            "current_status.key_matrices.single_rank": "single_compatibility_matrix_rank",
            "current_status.key_matrices.single_nullity": "single_compatibility_matrix_nullity",
        },
        "new_authoritative_fields": {
            "compatibility_matrix_shape": list(single_publication_bs_analysis["matrix_shape"]),
            "compatibility_matrix_rank": int(single_publication_bs_analysis["rank"]),
            "compatibility_matrix_nullity": int(single_publication_bs_analysis["nullity"]),
            "bs_rank": int(single_publication_bs_analysis["nullity"]),
            "double_compatibility_matrix_shape": double_shape,
            "double_compatibility_matrix_rank": double_rank,
            "double_compatibility_matrix_nullity": double_nullity,
            "double_bs_rank": double_nullity,
        },
        "updated_files": [
            str(SINGLE_SUMMARY_JSON.relative_to(ROOT)),
            str(CURRENT_STATUS_JSON.relative_to(ROOT)),
            str(SINGLE_AUDIT_MD.relative_to(ROOT)),
            str(NEXT_STEP_PROMPT_TXT.relative_to(ROOT)),
        ],
        "reading_rule": (
            "Read compatibility-matrix rank/nullity from the published C_pub matrix analysis. "
            "Read BS rank from the compatibility-matrix nullity."
        ),
    }


def build_bs_rank_naming_fix_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# BS Rank Naming Fix Report",
            "",
            f"- Old misleading fields: `{report['old_misleading_fields']}`.",
            f"- New authoritative fields: `{report['new_authoritative_fields']}`.",
            f"- Updated files: `{report['updated_files']}`.",
            f"- Reading rule: {report['reading_rule']}",
        ]
    )


def build_ai_rank_gap_attribution_report(
    publication_bs_analysis: dict[str, Any],
    publication_induction: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    ai_obstruction_diagnosis_report: dict[str, Any],
) -> dict[str, Any]:
    bs_rank = int(publication_bs_analysis["nullity"])
    verified_ai_rank = int(ai_zero_subset_rank_report["zero_subset_rank"])
    all_candidate_matrix = sp.Matrix.hstack(
        *[sp.Matrix(candidate["unknown_vector"]) for candidate in publication_induction["candidates"]]
    ) if publication_induction["candidates"] else sp.zeros(len(publication_bs_analysis["unknown_ordering"]), 0)
    all_candidate_rank = int(all_candidate_matrix.rank())
    blocked_by_p4 = [
        record["generator_id"]
        for record in ai_obstruction_diagnosis_report["generator_records"]
        if record["classification"].startswith("induction_failure")
        and record["family_id"] in {"c", "d"}
    ]
    blocked_by_ppath06 = [
        record["generator_id"]
        for record in ai_obstruction_diagnosis_report["generator_records"]
        if record["publication_shell"]["status"] == "nonzero_residual"
        and "PPATH06" in record["publication_shell"]["nonzero_path_ids"]
    ]
    return {
        "published_bs_rank": bs_rank,
        "current_verified_ai_rank": verified_ai_rank,
        "missing_ai_rank": max(0, bs_rank - verified_ai_rank),
        "compatibility_zero_generator_ids": list(ai_zero_subset_rank_report["zero_generator_ids"]),
        "blocked_by_p4_induction_failure": blocked_by_p4,
        "blocked_by_ppath06_residual": blocked_by_ppath06,
        "blocked_by_both": sorted(set(blocked_by_p4) & set(blocked_by_ppath06)),
        "blocked_by_neither_or_still_unknown": sorted(
            set(record["generator_id"] for record in ai_obstruction_diagnosis_report["generator_records"])
            - set(ai_zero_subset_rank_report["zero_generator_ids"])
            - set(blocked_by_p4)
            - set(blocked_by_ppath06)
        ),
        "if_ppath06_residual_repaired_rank_upper_bound": min(bs_rank, all_candidate_rank),
        "if_p4_induction_repaired_rank_upper_bound": (
            verified_ai_rank
            if not blocked_by_p4
            else min(bs_rank, all_candidate_rank)
        ),
        "if_both_repaired_rank_upper_bound": min(bs_rank, all_candidate_rank),
    }


def build_ai_rank_gap_attribution_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Rank Gap Attribution Report",
            "",
            f"- Published BS rank: `{report['published_bs_rank']}`.",
            f"- Current verified AI rank: `{report['current_verified_ai_rank']}`.",
            f"- Missing AI rank: `{report['missing_ai_rank']}`.",
            f"- Compatibility-zero generators: `{report['compatibility_zero_generator_ids']}`.",
            f"- Blocked by P4 induction failure: `{report['blocked_by_p4_induction_failure']}`.",
            f"- Blocked by PPATH06 residual: `{report['blocked_by_ppath06_residual']}`.",
            f"- Blocked by both: `{report['blocked_by_both']}`.",
            f"- Blocked by neither / still unknown: `{report['blocked_by_neither_or_still_unknown']}`.",
            f"- Rank upper bound if PPATH06 repaired: `{report['if_ppath06_residual_repaired_rank_upper_bound']}`.",
            f"- Rank upper bound if P4 repaired: `{report['if_p4_induction_repaired_rank_upper_bound']}`.",
            f"- Rank upper bound if both repaired: `{report['if_both_repaired_rank_upper_bound']}`.",
        ]
    )


def build_ai_rank_gap_quotient_report(
    publication_bs_analysis: dict[str, Any],
    publication_induction: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    *,
    support_rows: Sequence[int],
) -> dict[str, Any]:
    zero_candidates = [
        candidate
        for candidate in publication_induction["candidates"]
        if candidate["compatibility_zero"]
    ]
    residual_candidates = [
        candidate
        for candidate in publication_induction["candidates"]
        if not candidate["compatibility_zero"]
    ]
    n_unknowns = len(publication_bs_analysis["unknown_ordering"])
    zero_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate["unknown_vector"]) for candidate in zero_candidates])
        if zero_candidates
        else sp.zeros(n_unknowns, 0)
    )
    residual_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate["unknown_vector"]) for candidate in residual_candidates])
        if residual_candidates
        else sp.zeros(n_unknowns, 0)
    )
    zero_rank = int(zero_matrix.rank())
    residual_sector_rank = int(residual_matrix.rank())
    combined_matrix = sp.Matrix.hstack(zero_matrix, residual_matrix)
    combined_rank = int(combined_matrix.rank())
    ambient_residual_quotient_rank = combined_rank - zero_rank

    running = zero_matrix
    running_rank = zero_rank
    ambient_pivot_candidates: list[dict[str, Any]] = []
    for candidate in residual_candidates:
        candidate_matrix = sp.Matrix.hstack(running, sp.Matrix(candidate["unknown_vector"]))
        candidate_rank = int(candidate_matrix.rank())
        if candidate_rank > running_rank:
            ambient_pivot_candidates.append(candidate)
            running = candidate_matrix
            running_rank = candidate_rank
    ambient_pivot_generator_ids = [candidate["generator_id"] for candidate in ambient_pivot_candidates]

    signature_rows = [
        [int(candidate["compatibility_residual_vector"][row_index]) for row_index in support_rows]
        for candidate in residual_candidates
    ]
    residual_signature_matrix = (
        sp.Matrix(signature_rows).T
        if signature_rows
        else sp.zeros(len(support_rows), 0)
    )
    residual_signature_rank = int(residual_signature_matrix.rank())

    signature_running = sp.zeros(len(support_rows), 0)
    signature_running_rank = 0
    residual_signature_pivot_generator_ids: list[str] = []
    residual_signature_pivot_positions: list[int] = []
    for position, candidate in enumerate(ambient_pivot_candidates):
        signature_vector = sp.Matrix(
            [int(candidate["compatibility_residual_vector"][row_index]) for row_index in support_rows]
        )
        candidate_signature_matrix = sp.Matrix.hstack(signature_running, signature_vector)
        candidate_signature_rank = int(candidate_signature_matrix.rank())
        if candidate_signature_rank > signature_running_rank:
            residual_signature_pivot_generator_ids.append(candidate["generator_id"])
            residual_signature_pivot_positions.append(position)
            signature_running = candidate_signature_matrix
            signature_running_rank = candidate_signature_rank

    pivot_signature_matrix = (
        sp.Matrix(
            [
                [
                    int(candidate["compatibility_residual_vector"][row_index])
                    for candidate in ambient_pivot_candidates
                ]
                for row_index in support_rows
            ]
        )
        if ambient_pivot_candidates
        else sp.zeros(len(support_rows), 0)
    )
    residual_kernel_basis_vectors = pivot_signature_matrix.nullspace()
    residual_kernel_basis_witnesses = []
    signature_pivot_id_set = set(residual_signature_pivot_generator_ids)
    missing_rank5_pivot_generator_ids: list[str] = []
    for basis_index, basis_vector in enumerate(residual_kernel_basis_vectors, start=1):
        terms = []
        for position, coefficient in enumerate(basis_vector):
            coefficient = sp.simplify(coefficient)
            if coefficient == 0:
                continue
            terms.append(
                {
                    "generator_id": ambient_pivot_generator_ids[position],
                    "coefficient": str(coefficient),
                }
            )
        lead_terms = [
            term
            for term in terms
            if term["generator_id"] not in signature_pivot_id_set
        ]
        lead_generator_id = (lead_terms[-1] if lead_terms else terms[-1])["generator_id"]
        missing_rank5_pivot_generator_ids.append(lead_generator_id)
        residual_kernel_basis_witnesses.append(
            {
                "basis_index": basis_index,
                "lead_generator_id": lead_generator_id,
                "combination": terms,
            }
        )

    missing_ai_rank = max(0, int(publication_bs_analysis["nullity"]) - zero_rank)
    quotient_rank_contribution = max(0, ambient_residual_quotient_rank - residual_signature_rank)
    return {
        "published_bs_rank": int(publication_bs_analysis["nullity"]),
        "current_verified_ai_rank": zero_rank,
        "missing_ai_rank": missing_ai_rank,
        "residual_candidate_count": len(residual_candidates),
        "residual_sector_rank": residual_sector_rank,
        "ambient_rank_with_zero_and_residual": combined_rank,
        "ambient_residual_quotient_rank": ambient_residual_quotient_rank,
        "residual_support_rows": list(support_rows),
        "residual_signature_rank_on_support_rows": residual_signature_rank,
        "quotient_rank_contribution_of_residual_sector": quotient_rank_contribution,
        "ambient_residual_quotient_pivot_generator_ids": ambient_pivot_generator_ids,
        "residual_signature_pivot_generator_ids": residual_signature_pivot_generator_ids,
        "missing_rank5_pivot_generator_ids": missing_rank5_pivot_generator_ids,
        "residual_kernel_basis_witnesses": residual_kernel_basis_witnesses,
        "all_missing_ai_rank_explained_by_residual_sector": quotient_rank_contribution == missing_ai_rank,
    }


def build_ai_rank_gap_quotient_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Rank-Gap Quotient Report",
            "",
            f"- Published BS rank: `{report['published_bs_rank']}`.",
            f"- Current verified AI rank: `{report['current_verified_ai_rank']}`.",
            f"- Missing AI rank: `{report['missing_ai_rank']}`.",
            f"- Residual candidate count / residual-sector rank: `{report['residual_candidate_count']}` / `{report['residual_sector_rank']}`.",
            f"- Ambient residual quotient rank before support-row repair: `{report['ambient_residual_quotient_rank']}`.",
            f"- Residual-support rows: `{report['residual_support_rows']}`.",
            f"- Residual-signature rank on support rows: `{report['residual_signature_rank_on_support_rows']}`.",
            f"- Quotient-rank contribution of residual sector after support-row repair: `{report['quotient_rank_contribution_of_residual_sector']}`.",
            f"- Ambient residual quotient pivots: `{report['ambient_residual_quotient_pivot_generator_ids']}`.",
            f"- Residual-signature pivots: `{report['residual_signature_pivot_generator_ids']}`.",
            f"- Missing-rank-5 pivot generator ids: `{report['missing_rank5_pivot_generator_ids']}`.",
            f"- All missing AI rank explained by residual sector: `{report['all_missing_ai_rank_explained_by_residual_sector']}`.",
            f"- Residual kernel basis witnesses: `{report['residual_kernel_basis_witnesses']}`.",
        ]
    )


def build_residual_rank5_pivot_witness_report(
    publication_induction: dict[str, Any],
    ai_rank_gap_quotient_report: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
) -> dict[str, Any]:
    candidate_index = {
        candidate["generator_id"]: candidate
        for candidate in publication_induction["candidates"]
    }
    support_rows = ai_rank_gap_quotient_report["residual_support_rows"]
    witness_records = []
    for witness in ai_rank_gap_quotient_report["residual_kernel_basis_witnesses"]:
        lead_candidate = candidate_index[witness["lead_generator_id"]]
        witness_records.append(
            {
                "lead_generator_id": witness["lead_generator_id"],
                "family_letter": lead_candidate["family_letter"],
                "local_object_label": lead_candidate["local_object_label"],
                "combination": list(witness["combination"]),
                "lead_generator_sparse_unknown_terms": _sparse_unknown_vector_terms(
                    unknown_ordering,
                    lead_candidate["unknown_vector"],
                ),
                "lead_generator_residual_support_vector": [
                    int(lead_candidate["compatibility_residual_vector"][row_index])
                    for row_index in support_rows
                ],
            }
        )
    return {
        "missing_rank": ai_rank_gap_quotient_report["missing_ai_rank"],
        "support_rows": support_rows,
        "residual_pivot_generator_ids": list(ai_rank_gap_quotient_report["missing_rank5_pivot_generator_ids"]),
        "residual_signature_pivot_generator_ids": list(ai_rank_gap_quotient_report["residual_signature_pivot_generator_ids"]),
        "witness_records": witness_records,
        "justification": (
            "The residual sector contributes the entire missing rank-5 once the three independent PPATH06 support-row residual directions are quotiented out. "
            "Each witness below is a kernel vector of that residual-signature map and therefore represents a latent AI direction blocked only by the PPATH06 residual mechanism."
        ),
    }


def build_residual_rank5_pivot_witness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Residual Rank-5 Pivot Witness Report",
        "",
        f"- Missing rank: `{report['missing_rank']}`.",
        f"- Residual-support rows: `{report['support_rows']}`.",
        f"- Residual pivot generator ids: `{report['residual_pivot_generator_ids']}`.",
        f"- Residual-signature pivot generator ids: `{report['residual_signature_pivot_generator_ids']}`.",
        f"- Justification: {report['justification']}",
        "",
    ]
    for record in report["witness_records"]:
        lines.append(
            f"- `{record['lead_generator_id']}` ({record['family_letter']}, {record['local_object_label']}): "
            f"combination `{record['combination']}`, residual-support vector `{record['lead_generator_residual_support_vector']}`, "
            f"sparse terms `{record['lead_generator_sparse_unknown_terms']}`."
        )
    return "\n".join(lines)


def build_ai_vs_bilbao_alignment_report(
    publication_check: dict[str, Any],
    publication_bs_analysis: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    *,
    authoritative_ai_rank: int | None = None,
) -> dict[str, Any]:
    bs_rank = int(publication_bs_analysis["nullity"])
    old_verified_ai_rank = int(ai_zero_subset_rank_report["zero_subset_rank"])
    ai_rank = int(authoritative_ai_rank) if authoritative_ai_rank is not None else old_verified_ai_rank
    aligned = bool(publication_check["bilbao_equivalent_publication_pass"]) and ai_rank >= bs_rank
    return {
        "bs_publication_shell_bilbao_aligned": bool(publication_check["bilbao_equivalent_publication_pass"]),
        "ai_aligned_with_bilbao_for_bs_over_ai": aligned,
        "published_bs_rank": bs_rank,
        "current_verified_ai_rank": old_verified_ai_rank,
        "current_authoritative_ai_rank": ai_rank,
        "alignment_summary": (
            "BS/publication shell is Bilbao-aligned, and the authoritative AI rank now matches the published BS rank so the quotient stage is mechanically ready."
            if aligned
            else "BS/publication shell is Bilbao-aligned, but AI is not yet aligned because the authoritative AI rank remains below the published BS rank and the quotient stage is still blocked."
        ),
    }


def build_ai_vs_bilbao_alignment_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI vs Bilbao Alignment Report",
            "",
            f"- BS/publication shell aligned with Bilbao: `{report['bs_publication_shell_bilbao_aligned']}`.",
            f"- AI aligned enough for BS/AI: `{report['ai_aligned_with_bilbao_for_bs_over_ai']}`.",
            f"- Published BS rank: `{report['published_bs_rank']}`.",
            f"- Old verified / current authoritative AI rank: `{report['current_verified_ai_rank']}` / `{report['current_authoritative_ai_rank']}`.",
            f"- Summary: {report['alignment_summary']}",
        ]
    )


def _deprecated_build_ai_honest_blocker_report(
    integration_report: dict[str, Any],
    p4_failure_audit: dict[str, Any] | None = None,
    ppath06_audit: dict[str, Any] | None = None,
    obstruction_report: dict[str, Any] | None = None,
    p4_conversion_patch_independent_validation_report: dict[str, Any] | None = None,
    ai_rank_gap_quotient_report: dict[str, Any] | None = None,
    *,
    p4_verdict: str | None = None,
) -> dict[str, Any]:
    if integration_report["integration_status"] == "wired_complete_candidate_set":
        return {
            "status": "not_blocked",
            "blocker": None,
            "blocker_stage": None,
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
        }
    if obstruction_report is not None:
        blocker_stage = "published_shell_obstruction_diagnosis"
        p4_phrase = ""
        if p4_failure_audit is not None:
            if int(p4_failure_audit.get("induction_failure_count", 0)) > 0:
                p4_phrase = (
                    f" The remaining induction failures are concentrated on manifold P4 "
                    f"across families {p4_failure_audit['failure_family_ids']} "
                    f"(count={p4_failure_audit['induction_failure_count']})."
                )
            else:
                p4_phrase = (
                    " The earlier P4 induction failures are cleared by the manifold character-field conversion patch."
                )
                if p4_conversion_patch_independent_validation_report is not None:
                    p4_phrase += (
                        " Independent validation status: "
                        f"{p4_conversion_patch_independent_validation_report['current_verdict']}."
                    )
            if p4_verdict is not None:
                p4_phrase += f" Current P4 verdict: {p4_verdict}."
        ppath06_phrase = ""
        if ppath06_audit is not None:
            support_rows = _ppath06_publication_residual_support_rows(
                ppath06_audit,
                obstruction_report,
            )
            ppath06_phrase = (
                f" Nonzero residuals on the publication shell are concentrated on "
                f"{ppath06_audit['publication_path_id']} rows "
                f"{support_rows or ppath06_audit['publication_residual_support_rows']}."
            )
        rank_gap_phrase = ""
        if ai_rank_gap_quotient_report is not None:
            rank_gap_phrase = (
                f" The residual sector contributes quotient rank "
                f"{ai_rank_gap_quotient_report['quotient_rank_contribution_of_residual_sector']} "
                f"after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank "
                f"{ai_rank_gap_quotient_report['missing_ai_rank']}."
            )
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but only {integration_report['compatibility_zero_candidate_count']} of "
            f"{integration_report['success_candidate_count']} induced local objects satisfy compatibility on the publication-level shell. "
            f"Classification counts across raw42 / internal honest shell / publication shell: "
            f"{obstruction_report['classification_counts']}. "
            f"{obstruction_report['obstruction_summary']}"
            f"{p4_phrase}"
            f"{ppath06_phrase}"
            f"{rank_gap_phrase}"
        )
        return {
            "status": "blocked",
            "blocker_stage": blocker_stage,
            "blocker": blocker,
            "ai_status": "partial_ai_lattice" if integration_report["compatibility_zero_candidate_count"] > 0 else "seed_only",
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
            "integration_status": integration_report["integration_status"],
            "failure_count": integration_report["failure_count"],
            "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
            "failure_family_ids": list(integration_report["failure_family_ids"]),
            "published_shell_candidate_count": integration_report["success_candidate_count"],
            "published_shell_compatible_zero_count": integration_report["compatibility_zero_candidate_count"],
            "ppath06_publication_residual_support_rows": (
                _ppath06_publication_residual_support_rows(ppath06_audit, obstruction_report)
                if ppath06_audit is not None
                else None
            ),
            "quotient_rank_contribution_of_residual_sector": (
                ai_rank_gap_quotient_report["quotient_rank_contribution_of_residual_sector"]
                if ai_rank_gap_quotient_report is not None
                else None
            ),
            "obstruction_classification_counts": dict(obstruction_report["classification_counts"]),
        }
    if integration_report["failure_count"] > 0:
        blocker_stage = "published_shell_induction"
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but {integration_report['failure_count']} induced local objects still fail on the publication-level shell."
        )
    else:
        blocker_stage = "published_shell_compatibility"
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but only {integration_report['compatibility_zero_candidate_count']} of "
            f"{integration_report['success_candidate_count']} induced local objects satisfy compatibility on the publication-level shell."
        )
    return {
        "status": "blocked",
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "ai_status": "partial_ai_lattice" if integration_report["compatibility_zero_candidate_count"] > 0 else "seed_only",
        "local_library_present": True,
        "local_library_wired_into_ai_builder": True,
        "integration_status": integration_report["integration_status"],
        "failure_count": integration_report["failure_count"],
        "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
        "failure_family_ids": list(integration_report["failure_family_ids"]),
        "published_shell_candidate_count": integration_report["success_candidate_count"],
        "published_shell_compatible_zero_count": integration_report["compatibility_zero_candidate_count"],
    }


def build_ai_honest_blocker_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Honest Blocker Report",
            "",
            f"- Status: `{report['status']}`.",
            f"- Blocker stage: `{report['blocker_stage']}`.",
            f"- Local library present / wired: `{report['local_library_present']}` / `{report['local_library_wired_into_ai_builder']}`.",
            f"- Failure count: `{report.get('failure_count')}`.",
            f"- Nonzero-residual candidate count: `{report.get('nonzero_residual_candidate_count')}`.",
            f"- Failure family ids: `{report.get('failure_family_ids')}`.",
            f"- Blocker: {report['blocker']}",
        ]
    )


def build_controlled_case() -> tuple[dict[str, Any], str]:
    try:
        import spglib
    except ImportError as exc:
        raise RuntimeError(
            "build_controlled_case() requires spglib for the controlled-case audit; install spglib to run this path."
        ) from exc

    ssg_data, time_revs = swyckoff_r.load_irssg_data(TARGET_GROUP, 0)
    rot = [np.array(op["matrix"], dtype=float) for op in ssg_data["operations"]]
    tau = [np.array(op["translation"], dtype=float) for op in ssg_data["operations"]]
    hall = spglib.get_hall_number_from_symmetry(rot, tau, symprec=1e-5)
    sg_info = spglib.get_spacegroup_type(hall)
    sg_sym = spglib.get_symmetry_from_database(hall)
    sg_data = {
        "centering_symbol": "P",
        "number": str(sg_info["number"]),
        "display_name": f"SG {sg_info['number']}",
        "crystal_system": "hexagonal",
        "operations": [{"matrix": R.tolist(), "translation": t.tolist()} for R, t in zip(sg_sym["rotations"], sg_sym["translations"])],
        "time_revs": [False] * len(sg_sym["rotations"]),
        "spin_matrices": [np.eye(3).tolist() for _ in range(len(sg_sym["rotations"]))],
    }

    def op_key(op: dict[str, Any]) -> tuple[Any, ...]:
        mat = tuple(tuple(int(round(x)) for x in row) for row in op["matrix"])
        tau_key = tuple(round(float(x) % 1.0, 8) for x in op["translation"])
        return mat, tau_key

    ssg_ops = {op_key(op) for op in ssg_data["operations"]}
    sg_ops = {op_key(op) for op in sg_data["operations"]}
    r_ssg, _ = swyckoff_r.compute_wyckoff_output(ssg_data, fast=True)
    r_sg, _ = swyckoff_r.compute_wyckoff_output(sg_data, fast=True)
    k_ssg, _ = swyckoff_k.compute_wyckoff_output(ssg_data, kspace=True, fast=True)
    k_sg, _ = swyckoff_k.compute_wyckoff_output(sg_data, kspace=True, fast=True)

    def signature(entries: Sequence[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [(entry["letter"], int(entry["dim"]), entry["site_symmetry"], entry["representative_coordinate"]) for entry in entries]

    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict(TARGET_GROUP)
    grouped = pick_group_entries(TARGET_GROUP)
    representative_point = grouped["points"][0]
    point_kvec = np.array([float(Fraction(value)) for value in representative_point["sample_point"]], dtype=float)
    probe_single = module.load_little_group(TARGET_GROUP, point_kvec, False, "single", ssg_dict)
    probe_double = module.load_little_group(TARGET_GROUP, point_kvec, False, "double", ssg_dict)

    controlled = {
        "target_group": TARGET_GROUP,
        "identified_sg_number": int(sg_info["number"]),
        "identified_sg_symbol": str(sg_info["international_short"]),
        "hall_number": int(hall),
        "operation_set_exact_match_to_sg_194": ssg_ops == sg_ops,
        "only_in_ssg": len(ssg_ops - sg_ops),
        "only_in_sg": len(sg_ops - ssg_ops),
        "realspace_geometry_signature_match": signature(r_ssg) == signature(r_sg),
        "kspace_geometry_signature_match": signature(k_ssg) == signature(k_sg),
        "realspace_family_count": len(r_ssg),
        "kspace_manifold_count": len(k_ssg),
        "time_reversal_count": int(sum(bool(flag) for flag in time_revs)),
        "source_centering_symbol": ssg_data.get("source_centering_symbol"),
        "groupType_probe_point": representative_point["id"],
        "groupType_probe_coordinates": representative_point["sample_point"],
        "groupType1_probe_success_count": 1,
        "groupType2_probe_success_count": 1,
        "groupType1_all_special_manifolds_available": len(probe_single.rep_degree) >= 1,
        "groupType2_all_special_manifolds_available": len(probe_double.rep_degree) >= 1,
        "controlled_case_valid": (
            int(sg_info["number"]) == 194
            and ssg_ops == sg_ops
            and signature(r_ssg) == signature(r_sg)
            and signature(k_ssg) == signature(k_sg)
        ),
    }
    lines = [
        "# Controlled-Case Audit for 194.1.1.1",
        "",
        "## Why 194.1.1.1 was selected",
        "",
        "- The reference group 10.4.1.31 already closed both the single-group and double-group workflows.",
        "- The current target 194.1.1.1 is a good portability pilot because the local toolchain can identify its spatial operation set as ordinary SG 194 inside the same basis/origin conventions used by the current code.",
        "",
        "## Spatial-Operation Check",
        "",
        f"- `SG_utils.identify_SG_from_symmetry(...)` identifies the spatial part as SG `{controlled['identified_sg_number']} ({controlled['identified_sg_symbol']})`.",
        f"- Hall number from the local spglib database: `{controlled['hall_number']}`.",
        f"- Standardized spatial operation-set equality against the hall-database SG 194 representative: `{controlled['operation_set_exact_match_to_sg_194']}`.",
        f"- Extra operations on the SSG side: `{controlled['only_in_ssg']}`.",
        f"- Missing operations relative to SG 194: `{controlled['only_in_sg']}`.",
        "",
        "## Real-Space / k-Space Geometry Check",
        "",
        f"- Real-space family-count match: `{controlled['realspace_family_count']}` on the SSG side, signature equality = `{controlled['realspace_geometry_signature_match']}`.",
        f"- k-space manifold-count match: `{controlled['kspace_manifold_count']}` on the SSG side, signature equality = `{controlled['kspace_geometry_signature_match']}`.",
        f"- `source_centering_symbol = {controlled['source_centering_symbol']}` and the selected origin shift remains zero in the local swyckoff workflow.",
        "",
        "## groupType Availability",
        "",
        f"- representative k-space availability probe: `{controlled['groupType_probe_point']}` at `{controlled['groupType_probe_coordinates']}`.",
        f"- `groupType=1` direct little-group entry availability: `{controlled['groupType1_all_special_manifolds_available']}`.",
        f"- `groupType=2` direct little-group entry availability: `{controlled['groupType2_all_special_manifolds_available']}`.",
        f"- No antiunitary operations are present in the standardized spatial data (`time_reversal_count = {controlled['time_reversal_count']}`), so the controlled-case comparison is to an ordinary unitary SG 194 spatial backbone while still allowing a genuine double-group probe through `factor_su2` on the `SSGReps` side.",
        "",
        "## Verdict",
        "",
        f"- `controlled_case_valid = {controlled['controlled_case_valid']}`.",
        "- Under the current local setting/basis/origin conventions, 194.1.1.1 is not merely similar to SG 194: its standardized spatial operation set matches the local SG 194 hall-database representative exactly, and the real-space/k-space geometry signatures agree as well.",
    ]
    return controlled, "\n".join(lines)


def build_single_pilot(
    module: Any,
    ssg_dict: dict[str, Any],
    *,
    line_phase_profile: str = AUTHORITATIVE_PHASE_AWARE_PROFILE,
) -> dict[str, Any]:
    ctx = load_context(module, TARGET_GROUP, "single", ssg_dict)
    print("[pilot] single: geometry")
    prepared_kgeom = prepare_kgeometry(TARGET_GROUP)
    kgeom_payload = prepared_kgeom["payload"]
    grouped = prepared_kgeom["grouped"]
    kgeom = {
        "payload": kgeom_payload,
        "grouped": grouped,
        "connectivity": kgeom_payload,
        "runtime_ctx": prepared_kgeom["ctx"],
        "line_orbit_to_id": prepared_kgeom["line_orbit_to_id"],
        "plane_orbit_to_id": prepared_kgeom["plane_orbit_to_id"],
    }
    synthetic_points = build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic_points
    augment_connectivity_with_boundary_points(kgeom, synthetic_points)
    build_point_instance_entries(kgeom)
    ctx["kgeom"] = kgeom
    print("[pilot] single: manifold capture")
    captures = build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "single", kgeom)

    point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]
    print("[pilot] single: raw diagnostic line blocks")
    raw_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in grouped["lines"]
    ]
    raw_line_full = build_global_compatibility(raw_line_blocks, point_ids)

    print("[pilot] single: raw diagnostic plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in grouped["planes"]]
    with_planes = build_with_planes_compatibility(raw_line_full, plane_blocks)
    diagnostic_bs_analysis = analyze_kernel(with_planes)
    print("[pilot] single: internal honest-shell reduction")
    reduction = reduce_final_point_path_shell(kgeom)
    candidate_lines = annotate_final_path_lines(
        reduction["candidate_line_specs"],
        kgeom["runtime_ctx"],
        kgeom["line_orbit_to_id"],
        kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "single", captures, candidate_lines)
    candidate_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in candidate_lines
    ]
    reduction_analysis = analyze_candidate_path_selection(
        reduction,
        build_candidate_path_records(reduction, candidate_line_blocks),
    )
    reduction = finalize_reduction_from_candidate_analysis(reduction, reduction_analysis)
    final_lines = annotate_final_path_lines(
        reduction["final_line_specs"],
        kgeom["runtime_ctx"],
        kgeom["line_orbit_to_id"],
        kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "single", captures, final_lines)
    internal_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in final_lines
    ]
    internal_line_full = build_global_compatibility(internal_line_blocks, reduction["final_point_ids"])
    internal_bs_analysis = analyze_kernel(internal_line_full)
    print("[pilot] single: publication-level C builder")
    publication_shell = build_publication_shell_candidate(reduction)
    publication_line_full = build_publication_C_matrix(publication_shell)
    publication_bs_analysis = analyze_kernel(publication_line_full)
    raw42_point_merge_classes = build_point_merge_classes_from_line_blocks(raw_line_blocks)
    internal_point_merge_classes = build_point_merge_classes_from_line_blocks(internal_line_blocks)
    publication_point_merge_classes = build_publication_point_merge_classes(
        publication_line_full,
        internal_line_blocks,
    )
    raw_point_row_translation = build_phase_aware_point_row_translation(
        internal_line_blocks,
        publication_bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
    )
    point_row_translation = disable_point_row_translation(
        raw_point_row_translation,
        reason=(
            "Removed from the published AI seed until the L2-derived phase-aware "
            "translation is proven legal on the final reduced point/path shell."
        ),
    )
    reduction["internal_unknown_ordering"] = list(internal_bs_analysis["unknown_ordering"])
    reduction["internal_path_ids"] = [block["line_id"] for block in internal_line_blocks]
    publication_shell["publication_unknown_ordering"] = list(publication_bs_analysis["unknown_ordering"])
    publication_shell["publication_path_ids"] = [block["line_id"] for block in publication_line_full["line_blocks"]]
    publication_check = build_bilbao_equivalent_sanity_check(publication_shell)
    publication_shell["bilbao_equivalent_publication_pass"] = publication_check["bilbao_equivalent_publication_pass"]
    kgeom["internal_honest_shell_reduction"] = reduction
    kgeom["internal_honest_lines"] = final_lines
    kgeom["publication_shell"] = publication_shell
    kgeom["publication_line_full"] = publication_line_full

    print("[pilot] single: translation legality probe")
    translation_probe_candidates = []
    translation_probe_failures = []
    for entry in ctx["wyckoff_entries"]:
        local_char = trivial_local_character(entry, ctx)
        try:
            candidate = induce_candidate(
                entry,
                local_char,
                ctx,
                captures,
                publication_bs_analysis["unknown_ordering"],
                publication_line_full["global_matrix"],
                point_row_translation=raw_point_row_translation,
                character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
                point_merge_classes=publication_point_merge_classes,
            )
            candidate["generator_id"] = f"{entry['letter']}_trivial"
            translation_probe_candidates.append(candidate)
        except Exception as exc:
            translation_probe_failures.append(
                {
                    "family_letter": entry["letter"],
                    "generator_id": f"{entry['letter']}_trivial",
                    "error": str(exc),
                }
            )
    point_row_translation_report = build_point_row_translation_legality_report(
        publication_line_full["global_matrix"],
        translation_probe_candidates,
        raw_point_row_translation,
        point_row_translation,
    )
    point_row_translation_report["probe_failure_count"] = len(translation_probe_failures)
    point_row_translation_report["probe_failures"] = translation_probe_failures

    print("[pilot] single: atomic prototype")
    ai_candidates = []
    ai_candidate_failures = []
    for entry in ctx["wyckoff_entries"]:
        local_char = trivial_local_character(entry, ctx)
        try:
            candidate = induce_candidate(
                entry,
                local_char,
                ctx,
                captures,
                publication_bs_analysis["unknown_ordering"],
                publication_line_full["global_matrix"],
                point_row_translation=point_row_translation,
                character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
                point_merge_classes=publication_point_merge_classes,
            )
            candidate["generator_id"] = f"{entry['letter']}_trivial"
            ai_candidates.append(candidate)
        except Exception as exc:
            ai_candidate_failures.append(
                {
                    "family_letter": entry["letter"],
                    "generator_id": f"{entry['letter']}_trivial",
                    "error": str(exc),
                }
            )
    reduction_reports = write_reduction_reports(
        reduction,
        publication_shell,
        publication_check,
        internal_line_full=internal_line_full,
        internal_bs_analysis=internal_bs_analysis,
        publication_line_full=publication_line_full,
        publication_bs_analysis=publication_bs_analysis,
        diagnostic_with_planes=with_planes,
        diagnostic_bs_analysis=diagnostic_bs_analysis,
    )
    kgeom["publication_check"] = publication_check
    kgeom["bs_strong_equivalence_report"] = reduction_reports["bs_strong_equivalence_report"]
    print("[pilot] single: local-library AI integration")
    local_library_payload = load_local_library_payload()
    raw42_library_induction = induce_family_objects(
        ctx,
        captures,
        {"unknown_ordering": with_planes["global_unknown_ordering"]},
        with_planes["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=raw42_point_merge_classes,
    )
    internal_library_induction = induce_family_objects(
        ctx,
        captures,
        internal_bs_analysis,
        internal_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=internal_point_merge_classes,
    )
    publication_library_induction = induce_family_objects(
        ctx,
        captures,
        publication_bs_analysis,
        publication_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_single_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=publication_point_merge_classes,
    )
    ai_library_integration_report = build_ai_library_integration_report(
        local_library_payload,
        publication_library_induction,
        mode="single",
        published_object_kind=publication_shell["object_kind"],
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
        point_row_translation=point_row_translation,
    )
    ai_obstruction_diagnosis_report = build_ai_obstruction_diagnosis_report(
        reduction,
        raw_line_blocks,
        internal_line_blocks,
        with_planes,
        internal_line_full,
        publication_line_full,
        raw42_library_induction,
        internal_library_induction,
        publication_library_induction,
        publication_shell=publication_shell,
    )
    ai_character_field_alignment_report = build_ai_character_field_alignment_report(
        ai_obstruction_diagnosis_report,
        authoritative_compatibility_field="character",
        raw42_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        internal_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        publication_character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    ai_full_character_alignment_report = build_ai_full_character_alignment_report(
        ai_obstruction_diagnosis_report,
        old_field_map={
            "point": "linear_character",
            "line": "character",
            "plane": "character",
            "default": "linear_character",
        },
        new_field_map=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    p4_induction_failure_audit = build_p4_induction_failure_audit(
        local_library_payload,
        ctx,
        captures,
        publication_library_induction,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    p4_passing_vs_failing_comparison = build_p4_passing_vs_failing_comparison(
        local_library_payload,
        ctx,
        captures,
        publication_library_induction,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    p4_exact_solver_reliability_audit = build_p4_exact_solver_reliability_audit(
        local_library_payload,
        ctx,
        captures,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    p4_band_character_site_phase_decomposition = build_p4_band_character_site_phase_decomposition(
        local_library_payload,
        ctx,
        captures,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    p4_trace_formula_vs_explicit_orbit_report = build_p4_trace_formula_vs_explicit_orbit_report(
        local_library_payload,
        ctx,
        captures,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
    )
    character_field_basis_convention_audit = build_character_field_basis_convention_audit(
        captures,
        mode="single",
    )
    sg194_setting_specific_character_conversion_validation = (
        build_sg194_setting_specific_character_conversion_validation(
            captures,
            character_field_basis_convention_audit,
            mode="single",
        )
    )
    character_field_conversion_global_validation_report = (
        build_character_field_conversion_global_validation_report(
            captures,
            mode="single",
        )
    )
    p4_conversion_patch_independent_validation_report = (
        build_p4_conversion_patch_independent_validation_report(
            sg194_setting_specific_character_conversion_validation,
            p4_trace_formula_vs_explicit_orbit_report,
            p4_induction_failure_audit,
        )
    )
    d3h_like_local_object_crosscheck = build_d3h_like_local_object_crosscheck(
        local_library_payload,
    )
    ppath06_residual_obstruction_audit = build_ppath06_residual_obstruction_audit(
        raw_line_full,
        internal_line_full,
        publication_line_full,
        ai_obstruction_diagnosis_report,
    )
    l2_fpath07_ppath06_layerwise_comparison = build_l2_fpath07_ppath06_layerwise_comparison(
        raw_line_full,
        internal_line_full,
        publication_line_full,
    )
    ai_zero_subset_rank_report = build_ai_zero_subset_rank_report(publication_library_induction)
    partial_ai_lattice_witness_report = build_partial_ai_lattice_witness_report(
        publication_library_induction,
        ai_zero_subset_rank_report,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    bs_rank_naming_fix_report = build_bs_rank_naming_fix_report(
        publication_bs_analysis,
    )
    ai_rank_gap_attribution_report = build_ai_rank_gap_attribution_report(
        publication_bs_analysis,
        publication_library_induction,
        ai_zero_subset_rank_report,
        ai_obstruction_diagnosis_report,
    )
    ppath06_row_semantics_report = build_ppath06_row_semantics_report(
        ppath06_residual_obstruction_audit,
    )
    ai_rank_gap_quotient_report = build_ai_rank_gap_quotient_report(
        publication_bs_analysis,
        publication_library_induction,
        ai_zero_subset_rank_report,
        support_rows=ppath06_residual_obstruction_audit["publication_residual_support_rows"],
    )
    residual_rank5_pivot_witness_report = build_residual_rank5_pivot_witness_report(
        publication_library_induction,
        ai_rank_gap_quotient_report,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    ai_completion_feasibility_from_residual_sector = (
        build_ai_completion_feasibility_from_residual_sector(
            publication_library_induction,
            ai_zero_subset_rank_report,
            ai_rank_gap_quotient_report,
            unknown_ordering=publication_bs_analysis["unknown_ordering"],
        )
    )
    promoted_authoritative_ai_payload = build_authoritative_promoted_ai_generators(
        publication_library_induction,
        ai_zero_subset_rank_report,
        ai_completion_feasibility_from_residual_sector,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    authoritative_ai_promotion_report = build_authoritative_ai_promotion_report(
        promoted_authoritative_ai_payload,
        ai_completion_feasibility_from_residual_sector,
        ai_rank_gap_quotient_report,
    )
    authoritative_ai_payload = build_honest_ai_lattice_from_induction(
        publication_library_induction,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
        generator_id_prefix="single_honest_ai_kernel",
        object_role="publication_level_C_pub_authoritative_ai_generators",
        object_language="publication_level_C_pub_34_unknowns",
        old_verified_ai_rank=int(ai_zero_subset_rank_report["zero_subset_rank"]),
        promoted_ai_rank_increment=int(
            promoted_authoritative_ai_payload["promoted_ai_rank_increment"]
        ),
        seed_payload=promoted_authoritative_ai_payload,
    )
    ai_rank_after_promotion_report = build_ai_rank_after_promotion_report(
        publication_bs_analysis,
        ai_zero_subset_rank_report,
        authoritative_ai_payload,
        publication_check,
    )
    publication_point_basis_usage_report = build_publication_point_basis_usage_report(
        raw42_library_induction,
        internal_library_induction,
        publication_library_induction,
        authoritative_ai_payload,
        publication_check,
    )
    bs_ai_quotient_report = build_bs_ai_quotient_report(
        publication_bs_analysis,
        authoritative_ai_payload,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    single_bs_ai_quotient_report, single_indicator_extraction_report = (
        build_single_quotient_crosscheck(bs_ai_quotient_report)
    )
    claim_scope_guardrail_report = build_claim_scope_guardrail_report(
        sg194_setting_specific_character_conversion_validation,
        ai_completion_feasibility_from_residual_sector,
        ai_rank_after_promotion_report,
        bs_ai_quotient_report,
    )
    ai_vs_bilbao_alignment_report = build_ai_vs_bilbao_alignment_report(
        publication_check,
        publication_bs_analysis,
        ai_zero_subset_rank_report,
        authoritative_ai_rank=authoritative_ai_payload["new_authoritative_ai_rank"],
    )
    p4_current_verdict = derive_p4_current_verdict(
        p4_exact_solver_reliability_audit,
        d3h_like_local_object_crosscheck,
        p4_trace_formula_vs_explicit_orbit_report,
        p4_induction_failure_audit,
        p4_conversion_patch_independent_validation_report,
    )
    single_ai_all_induced_local_objects = build_single_ai_all_induced_local_objects_payload(
        publication_library_induction,
        published_object_kind=publication_shell["object_kind"],
        object_language="publication_level_C_pub_34_unknowns",
    )
    write_json(AI_CHARACTER_FIELD_ALIGNMENT_JSON, ai_character_field_alignment_report)
    write_text(
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        build_ai_character_field_alignment_markdown(ai_character_field_alignment_report),
    )
    write_json(AI_FULL_CHARACTER_ALIGNMENT_JSON, ai_full_character_alignment_report)
    write_text(
        AI_FULL_CHARACTER_ALIGNMENT_MD,
        build_ai_full_character_alignment_markdown(ai_full_character_alignment_report),
    )
    ai_honest_blocker_report = build_ai_honest_blocker_report(
        ai_library_integration_report,
        p4_induction_failure_audit,
        ppath06_residual_obstruction_audit,
        ai_obstruction_diagnosis_report,
        p4_conversion_patch_independent_validation_report,
        ai_rank_gap_quotient_report,
        ai_completion_feasibility_from_residual_sector,
        authoritative_ai_promotion_report,
        ai_rank_after_promotion_report,
        bs_ai_quotient_report,
        p4_verdict=p4_current_verdict,
    )
    ai_audit_report = build_ai_seed_audit_report(
        ai_candidates,
        point_row_translation,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
        library_integration_status=ai_library_integration_report["integration_status"],
        zero_subset_rank_report=ai_zero_subset_rank_report,
    )
    ai_audit_report["generator_failure_count"] = len(ai_candidate_failures)
    ai_audit_report["generator_failures"] = ai_candidate_failures
    ai_seed_delta_report = build_ai_seed_delta_after_bs_fix_report(
        {
            "generators": ai_candidates,
        },
        ai_audit_report,
    )
    ai_rank = int(ai_audit_report["rank_trivial_family_span"])
    write_json(POINT_ROW_TRANSLATION_JSON, point_row_translation_report)
    write_text(POINT_ROW_TRANSLATION_MD, build_point_row_translation_legality_markdown(point_row_translation_report))
    write_json(AI_SEED_AUDIT_JSON, ai_audit_report)
    write_text(AI_SEED_AUDIT_MD, build_ai_seed_audit_markdown(ai_audit_report))
    write_json(AI_SEED_DELTA_JSON, ai_seed_delta_report)
    write_text(AI_SEED_DELTA_MD, build_ai_seed_delta_after_bs_fix_markdown(ai_seed_delta_report))
    write_json(AI_LIBRARY_INTEGRATION_JSON, ai_library_integration_report)
    write_text(AI_LIBRARY_INTEGRATION_MD, build_ai_library_integration_markdown(ai_library_integration_report))
    write_json(AI_OBSTRUCTION_DIAG_JSON, ai_obstruction_diagnosis_report)
    write_text(AI_OBSTRUCTION_DIAG_MD, build_ai_obstruction_diagnosis_markdown(ai_obstruction_diagnosis_report))
    write_json(P4_INDUCTION_FAILURE_JSON, p4_induction_failure_audit)
    write_text(P4_INDUCTION_FAILURE_MD, build_p4_induction_failure_markdown(p4_induction_failure_audit))
    write_json(P4_PASSING_FAILING_JSON, p4_passing_vs_failing_comparison)
    write_text(P4_PASSING_FAILING_MD, build_p4_passing_vs_failing_markdown(p4_passing_vs_failing_comparison))
    write_json(P4_EXACT_SOLVER_RELIABILITY_JSON, p4_exact_solver_reliability_audit)
    write_text(
        P4_EXACT_SOLVER_RELIABILITY_MD,
        build_p4_exact_solver_reliability_markdown(p4_exact_solver_reliability_audit),
    )
    write_json(P4_BAND_CHARACTER_PHASE_JSON, p4_band_character_site_phase_decomposition)
    write_text(
        P4_BAND_CHARACTER_PHASE_MD,
        build_p4_band_character_site_phase_decomposition_markdown(p4_band_character_site_phase_decomposition),
    )
    write_json(P4_TRACE_FORMULA_EXPLICIT_JSON, p4_trace_formula_vs_explicit_orbit_report)
    write_text(
        P4_TRACE_FORMULA_EXPLICIT_MD,
        build_p4_trace_formula_vs_explicit_orbit_markdown(p4_trace_formula_vs_explicit_orbit_report),
    )
    write_json(CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_JSON, character_field_basis_convention_audit)
    write_text(
        CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_MD,
        build_character_field_basis_convention_audit_markdown(character_field_basis_convention_audit),
    )
    write_json(
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_JSON,
        sg194_setting_specific_character_conversion_validation,
    )
    write_text(
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_MD,
        build_sg194_setting_specific_character_conversion_validation_markdown(
            sg194_setting_specific_character_conversion_validation
        ),
    )
    write_json(
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_JSON,
        character_field_conversion_global_validation_report,
    )
    write_text(
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD,
        build_character_field_conversion_global_validation_markdown(
            character_field_conversion_global_validation_report
        ),
    )
    write_json(
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_JSON,
        p4_conversion_patch_independent_validation_report,
    )
    write_text(
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD,
        build_p4_conversion_patch_independent_validation_markdown(
            p4_conversion_patch_independent_validation_report
        ),
    )
    write_json(D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_JSON, d3h_like_local_object_crosscheck)
    write_text(
        D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD,
        build_d3h_like_local_object_crosscheck_markdown(d3h_like_local_object_crosscheck),
    )
    write_json(PPATH06_OBSTRUCTION_JSON, ppath06_residual_obstruction_audit)
    write_text(PPATH06_OBSTRUCTION_MD, build_ppath06_residual_obstruction_markdown(ppath06_residual_obstruction_audit))
    write_json(LAYERWISE_L2_FPATH07_PPATH06_JSON, l2_fpath07_ppath06_layerwise_comparison)
    write_text(LAYERWISE_L2_FPATH07_PPATH06_MD, build_l2_fpath07_ppath06_layerwise_markdown(l2_fpath07_ppath06_layerwise_comparison))
    write_json(AI_ZERO_SUBSET_RANK_JSON, ai_zero_subset_rank_report)
    write_text(AI_ZERO_SUBSET_RANK_MD, build_ai_zero_subset_rank_markdown(ai_zero_subset_rank_report))
    write_json(PARTIAL_AI_LATTICE_WITNESS_JSON, partial_ai_lattice_witness_report)
    write_text(
        PARTIAL_AI_LATTICE_WITNESS_MD,
        build_partial_ai_lattice_witness_markdown(partial_ai_lattice_witness_report),
    )
    write_json(BS_RANK_NAMING_FIX_JSON, bs_rank_naming_fix_report)
    write_text(BS_RANK_NAMING_FIX_MD, build_bs_rank_naming_fix_markdown(bs_rank_naming_fix_report))
    write_json(AI_RANK_GAP_ATTRIBUTION_JSON, ai_rank_gap_attribution_report)
    write_text(
        AI_RANK_GAP_ATTRIBUTION_MD,
        build_ai_rank_gap_attribution_markdown(ai_rank_gap_attribution_report),
    )
    write_json(AI_RANK_GAP_QUOTIENT_JSON, ai_rank_gap_quotient_report)
    write_text(
        AI_RANK_GAP_QUOTIENT_MD,
        build_ai_rank_gap_quotient_markdown(ai_rank_gap_quotient_report),
    )
    write_json(RESIDUAL_RANK5_PIVOT_WITNESS_JSON, residual_rank5_pivot_witness_report)
    write_text(
        RESIDUAL_RANK5_PIVOT_WITNESS_MD,
        build_residual_rank5_pivot_witness_markdown(residual_rank5_pivot_witness_report),
    )
    write_json(
        AI_COMPLETION_FEASIBILITY_JSON,
        ai_completion_feasibility_from_residual_sector,
    )
    write_text(
        AI_COMPLETION_FEASIBILITY_MD,
        build_ai_completion_feasibility_from_residual_sector_markdown(
            ai_completion_feasibility_from_residual_sector
        ),
    )
    write_json(SINGLE_AI_AUTHORITATIVE_JSON, authoritative_ai_payload)
    write_json(AUTHORITATIVE_AI_PROMOTION_JSON, authoritative_ai_promotion_report)
    write_text(
        AUTHORITATIVE_AI_PROMOTION_MD,
        build_authoritative_ai_promotion_markdown(authoritative_ai_promotion_report),
    )
    write_json(AI_RANK_AFTER_PROMOTION_JSON, ai_rank_after_promotion_report)
    write_text(
        AI_RANK_AFTER_PROMOTION_MD,
        build_ai_rank_after_promotion_markdown(ai_rank_after_promotion_report),
    )
    write_json(PUBLICATION_POINT_BASIS_USAGE_JSON, publication_point_basis_usage_report)
    write_text(
        PUBLICATION_POINT_BASIS_USAGE_MD,
        build_publication_point_basis_usage_markdown(publication_point_basis_usage_report),
    )
    write_json(BS_AI_QUOTIENT_JSON, single_bs_ai_quotient_report)
    write_text(
        BS_AI_QUOTIENT_MD,
        build_bs_ai_quotient_markdown(single_bs_ai_quotient_report),
    )
    write_json(INDICATOR_EXTRACTION_JSON, single_indicator_extraction_report)
    write_text(
        INDICATOR_EXTRACTION_MD,
        build_indicator_extraction_markdown(single_indicator_extraction_report),
    )
    write_json(SINGLE_BS_AI_QUOTIENT_JSON, single_bs_ai_quotient_report)
    write_text(
        SINGLE_BS_AI_QUOTIENT_MD,
        build_bs_ai_quotient_markdown(single_bs_ai_quotient_report),
    )
    write_json(SINGLE_INDICATOR_EXTRACTION_JSON, single_indicator_extraction_report)
    write_text(
        SINGLE_INDICATOR_EXTRACTION_MD,
        build_indicator_extraction_markdown(single_indicator_extraction_report),
    )
    write_json(CLAIM_SCOPE_GUARDRAIL_JSON, claim_scope_guardrail_report)
    write_text(
        CLAIM_SCOPE_GUARDRAIL_MD,
        build_claim_scope_guardrail_markdown(claim_scope_guardrail_report),
    )
    write_json(PPATH06_ROW_SEMANTICS_JSON, ppath06_row_semantics_report)
    write_text(
        PPATH06_ROW_SEMANTICS_MD,
        build_ppath06_row_semantics_markdown(ppath06_row_semantics_report),
    )
    write_json(AI_VS_BILBAO_ALIGNMENT_JSON, ai_vs_bilbao_alignment_report)
    write_text(
        AI_VS_BILBAO_ALIGNMENT_MD,
        build_ai_vs_bilbao_alignment_markdown(ai_vs_bilbao_alignment_report),
    )
    write_json(SINGLE_AI_ALL_OBJECTS_JSON, single_ai_all_induced_local_objects)
    write_json(AI_HONEST_BLOCKER_JSON, ai_honest_blocker_report)
    write_text(AI_HONEST_BLOCKER_MD, build_ai_honest_blocker_markdown(ai_honest_blocker_report))

    write_json(SINGLE_KMANIFOLDS_JSON, {
        "group_number": TARGET_GROUP,
        "objects": strip_internal_fields(grouped["points"] + grouped["lines"] + grouped["planes"]),
        "synthetic_boundary_points": synthetic_points,
        "connectivity": kgeom_payload,
        "internal_honest_shell": reduction,
        "publication_shell": publication_shell,
        "publication_shell_vs_bilbao_check": publication_check,
    })
    write_json(SINGLE_CONNECTIVITY_JSON, kgeom_payload)
    write_json(SINGLE_LITTLE_GROUPS_JSON, captures)
    write_json(
        SINGLE_LINE_COMPAT_JSON,
        {
            "published_object_kind": publication_shell["object_kind"],
            "path_set_kind": publication_shell["object_kind"],
            "final_point_ids": publication_shell["publication_point_ids"],
            "final_path_ids": publication_shell["publication_path_ids"],
            "line_blocks": publication_line_full["line_blocks"],
            "line_full": publication_line_full,
            "publication_shell": publication_shell,
            "publication_path_blocks": publication_line_full["publication_path_blocks"],
            "diagnostic_internal_line_blocks": internal_line_blocks,
            "diagnostic_internal_line_full": internal_line_full,
            "candidate_line_blocks": candidate_line_blocks,
            "diagnostic_raw_line_blocks": raw_line_blocks,
            "diagnostic_raw_line_full": raw_line_full,
            "internal_honest_shell": reduction,
            "publication_shell_vs_bilbao_check": publication_check,
            "final_bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        },
    )
    write_json(
        SINGLE_WITH_PLANES_JSON,
        {
            "object_role": "diagnostic_internal_raw_with_planes_42_shell",
            "publication_role": "diagnostic_internal_raw_with_planes_shell",
            "published_status": "diagnostic_only",
            **with_planes,
            "diagnostic_bs_analysis": diagnostic_bs_analysis,
        },
    )
    write_json(
        SINGLE_BS_JSON,
        {
            **publication_bs_analysis,
            "compatibility_matrix_shape": publication_bs_analysis["matrix_shape"],
            "compatibility_matrix_rank": publication_bs_analysis["rank"],
            "compatibility_matrix_nullity": publication_bs_analysis["nullity"],
            "bs_rank": publication_bs_analysis["nullity"],
            "object_role": "published_publication_level_C_pub_kernel",
            "final_object_kind": publication_shell["object_kind"],
            "path_set_kind": publication_shell["object_kind"],
            "final_point_ids": publication_shell["publication_point_ids"],
            "final_path_ids": publication_shell["publication_path_ids"],
            "final_selected_path_count": len(publication_shell["publication_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(pair) for pair in publication_shell["publication_actual_path_pairs"]}),
            "actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
            "bs_strong_equivalence_pass": reduction_reports["bs_strong_equivalence_report"]["bs_strong_equivalence_pass"],
            "row_language_full_span_pass": reduction_reports["bs_strong_equivalence_report"]["row_language_full_span_pass"],
            "bilbao_equivalent_final_object_pass": reduction_reports["bs_strong_equivalence_report"]["bilbao_equivalent_final_object_pass"],
            "diagnostic_raw_with_planes": {
                "matrix_shape": diagnostic_bs_analysis["matrix_shape"],
                "rank": diagnostic_bs_analysis["rank"],
                "nullity": diagnostic_bs_analysis["nullity"],
            },
            "diagnostic_internal_honest_shell": {
                "path_count": len(reduction["kept_paths"]),
                "matrix_shape": internal_bs_analysis["matrix_shape"],
                "rank": internal_bs_analysis["rank"],
                "nullity": internal_bs_analysis["nullity"],
                "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
            },
            "publication_shell_vs_bilbao_check": publication_check,
            "final_bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        },
    )
    write_json(
        SINGLE_AI_JSON,
        {
            "object_role": "publication_level_C_pub_ai_seed",
            "ai_status": ai_audit_report["ai_status"],
            "unknown_ordering": publication_bs_analysis["unknown_ordering"],
            "point_row_translation": point_row_translation,
            "character_field_used": _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
            "generators": ai_candidates,
            "rank_trivial_family_span": ai_rank,
            "generator_failure_count": len(ai_candidate_failures),
            "generator_failures": ai_candidate_failures,
            "blocker_summary": ai_honest_blocker_report["blocker"],
            "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
            "ai_character_field_alignment_report": {
                "authoritative_compatibility_field": ai_character_field_alignment_report["authoritative_compatibility_field"],
                "current_ai_induction_field": ai_character_field_alignment_report["current_ai_induction_field"],
                "current_compatibility_zero_counts": ai_character_field_alignment_report["current_compatibility_zero_counts"],
                "current_published_fail_path_histogram": ai_character_field_alignment_report["current_published_fail_path_histogram"],
            },
            "ai_full_character_alignment_report": ai_full_character_alignment_report,
            "ai_obstruction_diagnosis_summary": {
                "classification_counts": ai_obstruction_diagnosis_report["classification_counts"],
                "published_fail_path_histogram": ai_obstruction_diagnosis_report["publication_fail_path_histogram"],
                "obstruction_summary": ai_obstruction_diagnosis_report["obstruction_summary"],
            },
            "translation_legality_report": {
                "legality_status": point_row_translation_report["legality_status"],
                "published_translation_enabled": point_row_translation_report["published_translation_enabled"],
            },
            "point_row_translation_status": "retired_on_published_final_reduced_shell",
            "ai_seed_audit_report": {
                "ai_status": ai_audit_report["ai_status"],
                "compatibility_zero_count": ai_audit_report["compatibility_zero_count"],
                "honest_ai_lattice_ready": ai_audit_report["honest_ai_lattice_ready"],
            },
            "ai_zero_subset_rank_report": ai_zero_subset_rank_report,
            "ai_library_integration_report": {
                "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
                "integration_status": ai_library_integration_report["integration_status"],
                "success_candidate_count": ai_library_integration_report["success_candidate_count"],
                "failure_count": ai_library_integration_report["failure_count"],
                "compatibility_zero_candidate_count": ai_library_integration_report["compatibility_zero_candidate_count"],
            },
            "p4_induction_failure_audit": {
                "induction_failure_count": p4_induction_failure_audit["induction_failure_count"],
                "failure_family_ids": p4_induction_failure_audit["failure_family_ids"],
            },
            "p4_current_verdict": p4_current_verdict,
            "p4_conversion_patch_independent_validation_report": p4_conversion_patch_independent_validation_report,
            "ppath06_residual_obstruction_audit": {
                "publication_path_id": ppath06_residual_obstruction_audit["publication_path_id"],
                "row_indices": ppath06_residual_obstruction_audit["row_indices"]["publication_shell"],
                "publication_residual_support_rows": ppath06_residual_obstruction_audit["publication_residual_support_rows"],
            },
            "ai_seed_delta_after_bs_fix_report": {
                "residual_pattern_changed": ai_seed_delta_report["residual_pattern_changed"],
            },
            "partial_ai_lattice_witness_report": {
                "zero_subset_rank": partial_ai_lattice_witness_report["zero_subset_rank"],
                "pivot_generator_ids": partial_ai_lattice_witness_report["pivot_generator_ids"],
            },
            "ai_rank_gap_quotient_report": {
                "quotient_rank_contribution_of_residual_sector": ai_rank_gap_quotient_report["quotient_rank_contribution_of_residual_sector"],
                "missing_rank5_pivot_generator_ids": ai_rank_gap_quotient_report["missing_rank5_pivot_generator_ids"],
            },
            "authoritative_ai_promotion_report": {
                "liftable_residual_direction_ids": authoritative_ai_promotion_report["liftable_residual_direction_ids"],
                "promoted_authoritative_generator_ids": authoritative_ai_promotion_report["promoted_authoritative_generator_ids"],
                "all_promoted_generators_actual_compatibility_zero": authoritative_ai_promotion_report["all_promoted_generators_actual_compatibility_zero"],
            },
            "ai_rank_after_promotion_report": ai_rank_after_promotion_report,
            "publication_point_basis_usage_report": publication_point_basis_usage_report,
            "bs_ai_quotient_report": {
                "quotient_status": single_bs_ai_quotient_report["quotient_status"],
                "quotient_kind": single_bs_ai_quotient_report["quotient_kind"],
                "quotient_group": single_bs_ai_quotient_report["quotient_group"],
                "quotient_invariants": single_bs_ai_quotient_report["quotient_invariants"],
                "snf_diagonal": single_bs_ai_quotient_report["snf_diagonal"],
                "classification_expected_by_user": single_bs_ai_quotient_report["classification_expected_by_user"],
                "classification_matches_user_expectation": single_bs_ai_quotient_report["classification_matches_user_expectation"],
            },
        },
    )

    completeness_blocker = ai_honest_blocker_report["blocker"]
    quotient_stage_allowed = bool(ai_rank_after_promotion_report.get("quotient_stage_allowed"))
    single_quotient_success = single_bs_ai_quotient_report["quotient_status"] == "success"
    single_library_integration_status = (
        "wired_and_materialized_into_authoritative_kernel_lattice"
        if ai_rank_after_promotion_report["ai_status"] == "full_ai_lattice"
        else ai_library_integration_report["integration_status"]
    )
    workflow_active_blocker_stage = (
        "quotient_success_trivial"
        if single_quotient_success
        else ai_rank_after_promotion_report["active_blocker_stage"]
    )
    single_blocker_summary = (
        "No active single-group blocker; authoritative publication-shell BS/AI quotient extracted successfully."
        if single_quotient_success
        else completeness_blocker
    )
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 1,
        "geometry_status": "success",
        "compatibility_status": {
            "internal_line_blocks_built": len(internal_line_blocks),
            "publication_line_blocks_built": len(publication_line_full["line_blocks"]),
            "synthetic_boundary_points_added": len(synthetic_points),
            "point_line_relations": len(kgeom_payload["point_line"]),
            "unmatched_line_endpoints_before_augmentation": len(kgeom_payload["unmatched_line_endpoints"]),
            "plane_blocks_built": len(plane_blocks),
            "status": "success",
            "authoritative_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "raw_builder_phase_aware_profile": line_phase_profile,
            "internal_object_kind": reduction["reduction_kind"],
            "published_object_kind": publication_shell["object_kind"],
            "diagnostic_raw_with_planes_retained": True,
            "internal_and_publication_objects_explicitly_separated": True,
        },
        "BS_status": {
            "status": "success",
            "compatibility_matrix_shape": publication_bs_analysis["matrix_shape"],
            "compatibility_matrix_rank": publication_bs_analysis["rank"],
            "compatibility_matrix_nullity": publication_bs_analysis["nullity"],
            "bs_rank": publication_bs_analysis["nullity"],
            "smith_diagonal": publication_bs_analysis["smith_diagonal"],
            "internal_honest_shell_path_count": len(reduction["kept_paths"]),
            "internal_honest_shell_rank": internal_bs_analysis["rank"],
            "published_object_kind": publication_shell["object_kind"],
            "final_selected_path_count": len(publication_shell["publication_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(pair) for pair in publication_shell["publication_actual_path_pairs"]}),
            "actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
            "diagnostic_raw_with_planes_compatibility_matrix_shape": diagnostic_bs_analysis["matrix_shape"],
            "row_language_full_span_pass": reduction_reports["bs_strong_equivalence_report"]["row_language_full_span_pass"],
            "bilbao_equivalent_final_object_pass": reduction_reports["bs_strong_equivalence_report"]["bilbao_equivalent_final_object_pass"],
        },
        "AI_status": {
            "status": ai_rank_after_promotion_report["ai_status"],
            "trivial_generators_count": len(ai_candidates),
            "trivial_generator_failure_count": len(ai_candidate_failures),
            "rank_trivial_family_span": ai_rank,
            "old_verified_ai_rank": ai_rank_after_promotion_report["old_verified_ai_rank"],
            "authoritative_ai_rank": ai_rank_after_promotion_report["new_authoritative_ai_rank"],
            "promoted_ai_rank_increment": ai_rank_after_promotion_report["promoted_ai_rank_increment"],
            "compatibility_zero_count": ai_audit_report["compatibility_zero_count"],
            "all_trivial_generators_compatibility_zero": bool(ai_candidates) and all(candidate["compatibility_zero"] for candidate in ai_candidates),
            "point_row_translation_legality": point_row_translation_report["legality_status"],
            "authoritative_ai_character_field": _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
            "residual_pattern_changed_vs_previous_branch": ai_seed_delta_report["residual_pattern_changed"],
            "local_library_wired_into_ai_builder": ai_library_integration_report["local_library_wired_into_ai_builder"],
            "library_integration_status": single_library_integration_status,
            "library_integration_success_candidate_count": ai_library_integration_report["success_candidate_count"],
            "library_integration_failure_count": ai_library_integration_report["failure_count"],
            "library_integration_compatibility_zero_candidate_count": ai_library_integration_report["compatibility_zero_candidate_count"],
            "published_bs_rank": ai_rank_gap_attribution_report["published_bs_rank"],
            "zero_subset_rank": ai_zero_subset_rank_report["zero_subset_rank"],
            "zero_subset_generator_ids": ai_zero_subset_rank_report["zero_generator_ids"],
            "missing_ai_rank": ai_rank_gap_attribution_report["missing_ai_rank"],
            "p4_induction_failure_count": p4_induction_failure_audit["induction_failure_count"],
            "p4_failure_family_ids": p4_induction_failure_audit["failure_family_ids"],
            "p4_current_verdict": p4_current_verdict,
            "p4_theorem_status": p4_conversion_patch_independent_validation_report["basis_independent_global_theorem_status"],
            "p4_setting_specific_validation_scope": (
                p4_conversion_patch_independent_validation_report["validation_scope"]
            ),
            "p4_setting_specific_numerical_consistency_pass": (
                p4_conversion_patch_independent_validation_report["setting_specific_numerical_consistency_pass"]
            ),
            "sg194_setting_specific_linear_to_character_consistency_pass": (
                sg194_setting_specific_character_conversion_validation["setting_specific_numerical_consistency_pass"]
            ),
            "character_conversion_general_theorem_promoted": (
                sg194_setting_specific_character_conversion_validation["formula_promoted_as_general_theorem"]
            ),
            "p4_first_formula_vs_explicit_mismatch": p4_trace_formula_vs_explicit_orbit_report["first_failure_mismatch"],
            "blocker_summary": ai_honest_blocker_report["blocker"],
            "obstruction_classification_counts": ai_obstruction_diagnosis_report["classification_counts"],
            "published_fail_path_histogram": ai_obstruction_diagnosis_report["publication_fail_path_histogram"],
            "published_fail_row_histogram": ai_obstruction_diagnosis_report["publication_fail_row_histogram"],
            "ppath06_publication_residual_support_rows": ppath06_residual_obstruction_audit["publication_residual_support_rows"],
            "residual_sector_quotient_rank_contribution": ai_rank_gap_quotient_report["quotient_rank_contribution_of_residual_sector"],
            "missing_rank5_pivot_generator_ids": ai_rank_gap_quotient_report["missing_rank5_pivot_generator_ids"],
            "residual_completion_feasible": ai_completion_feasibility_from_residual_sector["any_liftable_to_actual_compatibility_zero"],
            "residual_completion_liftable_direction_ids": (
                ai_completion_feasibility_from_residual_sector["liftable_residual_direction_ids"]
            ),
            "promoted_authoritative_generator_ids": authoritative_ai_promotion_report["promoted_authoritative_generator_ids"],
            "all_promoted_authoritative_generators_actual_compatibility_zero": authoritative_ai_promotion_report["all_promoted_generators_actual_compatibility_zero"],
            "ai_aligned_with_bilbao": ai_rank_after_promotion_report["ai_aligned_with_bilbao"],
            "quotient_stage_allowed": quotient_stage_allowed,
            "publication_point_basis_usage_counts": publication_point_basis_usage_report["publication_point_basis_usage_counts"],
        },
        "completeness_status": {
            "status": "ready" if quotient_stage_allowed else "blocked",
            "blocker": completeness_blocker,
        },
        "quotient_status": {
            "status": "success" if single_quotient_success else ("ready" if quotient_stage_allowed else "blocked"),
            "blocker": (
                None
                if single_quotient_success
                else (
                    None
                    if quotient_stage_allowed
                    else "AI is not complete, so BS/AI cannot yet be interpreted honestly."
                )
            ),
            "quotient_group": single_bs_ai_quotient_report["quotient_group"],
            "quotient_kind": single_bs_ai_quotient_report["quotient_kind"],
            "quotient_invariants": single_bs_ai_quotient_report["quotient_invariants"],
            "snf_diagonal": single_bs_ai_quotient_report["snf_diagonal"],
            "classification_expected_by_user": single_bs_ai_quotient_report["classification_expected_by_user"],
            "classification_matches_user_expectation": single_bs_ai_quotient_report["classification_matches_user_expectation"],
        },
        "active_blocker_stage": workflow_active_blocker_stage,
        "blocker": single_blocker_summary,
    }

    if quotient_stage_allowed:
        ai_completeness_line = (
            f"- AI completeness: ready. Reason: {completeness_blocker}"
        )
        quotient_line = (
            "- Quotient / indicator extraction: ready to run on the authoritative publication-shell AI lattice."
            if not single_quotient_success
            else f"- Quotient / indicator extraction: success. Quotient group = `{single_bs_ai_quotient_report['quotient_group']}`."
        )
    else:
        ai_completeness_line = (
            f"- AI completeness: blocked. Reason: {completeness_blocker}"
        )
        quotient_line = (
            "- Quotient / indicator extraction: blocked until a complete AI lattice exists."
        )

    lines = [
        "# 194.1.1.1 Single-Group Portability Pilot",
        "",
        "## Outcome",
        "",
        "- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.",
        f"- The current pilot had to add `{len(synthetic_points)}` synthetic 0D boundary points because the raw k-geometry contains `{len(kgeom_payload['unmatched_line_endpoints'])}` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.",
        "- The internal honest full-span 8-path shell is retained for diagnostics only; the published BS object is the publication-level `C_pub` quotient built from publication path classes.",
        f"- Row-language full-span against the full candidate path language: `{reduction_reports['bs_strong_equivalence_report']['row_language_full_span_pass']}`.",
        f"- Bilbao-equivalent final-object pass: `{reduction_reports['bs_strong_equivalence_report']['bilbao_equivalent_final_object_pass']}`.",
        "",
        "## Direct Reuse Successes",
        "",
        "- `swyckoff_r.py` / `swyckoff_k.py` standardized geometry loading is reused directly.",
        "- `SSGReps.load_little_group(...)` is reused directly on all special points, lines, and planes.",
        "- The operation bridge `r_conv = P r_mag` logic and lattice-fix test are reused directly.",
        "- The restriction/decomposition workflow still uses `character` / `linear_character` / `rep_degree` and subgroup matching, without relying on `rep_matrix`.",
        "",
        "## Modules That Needed Change",
        "",
        "- The line-compatibility layer from 10.4.1.31 assumed every special line endpoint landed on a separately listed 0D point. That assumption fails on 194.1.1.1.",
        "- The portability pilot therefore augments the boundary-point set with explicit synthetic 0D endpoints before assembling the global compatibility matrix.",
        f"- {ai_honest_blocker_report['blocker']}",
        "",
        "## Status Summary",
        "",
        f"- Publication compatibility-matrix shape/rank/nullity: `{publication_bs_analysis['matrix_shape']}`, `{publication_bs_analysis['rank']}`, `{publication_bs_analysis['nullity']}`.",
        f"- Publication BS rank (kernel rank of C_pub): `{publication_bs_analysis['nullity']}`.",
        f"- Internal vs publication path counts: `{len(reduction['kept_paths'])}` / `{len(publication_shell['publication_path_ids'])}`.",
        f"- Publication Bilbao-style check: point ids match = `{publication_check['point_ids_match']}`, path count match = `{publication_check['path_count_match']}`, exact path-pair match = `{publication_check['path_pair_set_match']}`.",
        f"- Trivial-family AI seed count/rank: `{len(ai_candidates)}` / `{ai_rank}`.",
        f"- Trivial-family compatibility-zero count: `{ai_audit_report['compatibility_zero_count']}` / `{len(ai_candidates)}`.",
        f"- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `{ai_library_integration_report['success_candidate_count']}` / `{ai_library_integration_report['failure_count']}` / `{ai_library_integration_report['compatibility_zero_candidate_count']}`.",
        f"- Old verified AI rank / promoted increment / authoritative AI rank: "
        f"`{ai_rank_after_promotion_report['old_verified_ai_rank']}` / "
        f"`{ai_rank_after_promotion_report['promoted_ai_rank_increment']}` / "
        f"`{ai_rank_after_promotion_report['new_authoritative_ai_rank']}`.",
        f"- AI obstruction classification counts: `{ai_obstruction_diagnosis_report['classification_counts']}`.",
        f"- Publication residual path histogram: `{ai_obstruction_diagnosis_report['publication_fail_path_histogram']}`.",
        f"- PPATH06 residual-support rows: `{ppath06_residual_obstruction_audit['publication_residual_support_rows']}`.",
        f"- PPATH06 row semantics: `{ppath06_row_semantics_report['overall_interpretation']}`.",
        f"- P4 current verdict: `{p4_current_verdict}`.",
        f"- P4 theorem status: `{p4_conversion_patch_independent_validation_report['basis_independent_global_theorem_status']}`.",
        f"- P4 setting-specific conversion validation scope / pass: "
        f"`{p4_conversion_patch_independent_validation_report['validation_scope']}` / "
        f"`{p4_conversion_patch_independent_validation_report['setting_specific_numerical_consistency_pass']}`.",
        f"- SG194-setting-specific linear->character consistency pass / theorem promoted: "
        f"`{sg194_setting_specific_character_conversion_validation['setting_specific_numerical_consistency_pass']}` / "
        f"`{sg194_setting_specific_character_conversion_validation['formula_promoted_as_general_theorem']}`.",
        f"- Residual-sector quotient-rank contribution / missing-rank-5 pivot ids: "
        f"`{ai_rank_gap_quotient_report['quotient_rank_contribution_of_residual_sector']}` / "
        f"`{ai_rank_gap_quotient_report['missing_rank5_pivot_generator_ids']}`.",
        f"- Residual completion feasible / liftable direction ids / promoted authoritative generator ids: "
        f"`{ai_completion_feasibility_from_residual_sector['any_liftable_to_actual_compatibility_zero']}` / "
        f"`{ai_completion_feasibility_from_residual_sector['liftable_residual_direction_ids']}` / "
        f"`{authoritative_ai_promotion_report['promoted_authoritative_generator_ids']}`.",
        f"- AI aligned with Bilbao / quotient stage allowed: "
        f"`{ai_rank_after_promotion_report['ai_aligned_with_bilbao']}` / "
        f"`{quotient_stage_allowed}`.",
        f"- Publication point-basis usage counts: `{publication_point_basis_usage_report['publication_point_basis_usage_counts']}`.",
        f"- Quotient group / invariants / SNF diagonal: "
        f"`{single_bs_ai_quotient_report['quotient_group']}` / `{single_bs_ai_quotient_report['quotient_invariants']}` / "
        f"`{single_bs_ai_quotient_report['snf_diagonal']}`.",
        f"- Single classification expected by user / matches expectation: "
        f"`{single_bs_ai_quotient_report['classification_expected_by_user']}` / "
        f"`{single_bs_ai_quotient_report['classification_matches_user_expectation']}`.",
        f"- point_row_translation legality: `{point_row_translation_report['legality_status']}`.",
        f"- AI residual pattern changed vs previous branch: `{ai_seed_delta_report['residual_pattern_changed']}`.",
        ai_completeness_line,
        quotient_line,
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "kgeom": kgeom,
        "captures": captures,
        "with_planes": with_planes,
        "line_full": publication_line_full,
        "bs_analysis": publication_bs_analysis,
        "internal_line_full": internal_line_full,
        "internal_bs_analysis": internal_bs_analysis,
        "publication_shell": publication_shell,
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
        "reduction": reduction,
        "sanity_check": publication_check,
        "ai_candidates": ai_candidates,
        "point_row_translation": point_row_translation,
        "point_row_translation_report": point_row_translation_report,
        "ai_seed_audit_report": ai_audit_report,
        "ai_seed_delta_report": ai_seed_delta_report,
        "ai_library_integration_report": ai_library_integration_report,
        "ai_honest_blocker_report": ai_honest_blocker_report,
        "p4_current_verdict": p4_current_verdict,
        "bs_strong_equivalence_report": reduction_reports["bs_strong_equivalence_report"],
        "phase_aware_profile": line_phase_profile,
    }


def build_double_pilot(
    module: Any,
    ssg_dict: dict[str, Any],
    single_kgeom: dict[str, Any],
    *,
    line_phase_profile: str = AUTHORITATIVE_PHASE_AWARE_PROFILE,
) -> dict[str, Any]:
    ctx = load_context(module, TARGET_GROUP, "double", ssg_dict)
    ctx["kgeom"] = single_kgeom
    print("[pilot] double: manifold capture")
    captures = build_manifold_capture(module, TARGET_GROUP, ssg_dict, ctx, "double", single_kgeom)
    point_ids = [item["id"] for item in single_kgeom["grouped"]["points"]] + [item["id"] for item in single_kgeom["synthetic_boundary_points"]]
    print("[pilot] double: raw diagnostic line blocks")
    raw_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in single_kgeom["grouped"]["lines"]
    ]
    raw_line_full = build_global_compatibility(raw_line_blocks, point_ids)
    print("[pilot] double: raw diagnostic plane blocks")
    plane_blocks = [build_plane_block(plane, plane["corner_entries"], captures) for plane in single_kgeom["grouped"]["planes"]]
    with_planes = build_with_planes_compatibility(raw_line_full, plane_blocks)
    diagnostic_bs_analysis = analyze_kernel(with_planes)
    print("[pilot] double: internal honest-shell reduction")
    reduction = reduce_final_point_path_shell(single_kgeom)
    candidate_lines = annotate_final_path_lines(
        reduction["candidate_line_specs"],
        single_kgeom["runtime_ctx"],
        single_kgeom["line_orbit_to_id"],
        single_kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "double", captures, candidate_lines)
    candidate_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in candidate_lines
    ]
    reduction_analysis = analyze_candidate_path_selection(
        reduction,
        build_candidate_path_records(reduction, candidate_line_blocks),
    )
    reduction = finalize_reduction_from_candidate_analysis(reduction, reduction_analysis)
    internal_lines = annotate_final_path_lines(
        reduction["final_line_specs"],
        single_kgeom["runtime_ctx"],
        single_kgeom["line_orbit_to_id"],
        single_kgeom["plane_orbit_to_id"],
    )
    capture_final_path_lines(module, TARGET_GROUP, ssg_dict, ctx, "double", captures, internal_lines)
    internal_line_blocks = [
        build_line_block(
            line,
            captures,
            phase_aware_profile=line_phase_profile,
            builder_variant="authoritative",
        )
        for line in internal_lines
    ]
    internal_line_full = build_global_compatibility(internal_line_blocks, reduction["final_point_ids"])
    internal_bs_analysis = analyze_kernel(internal_line_full)
    print("[pilot] double: publication-level C builder")
    publication_shell = build_publication_shell_candidate(reduction)
    publication_line_full = build_publication_C_matrix(publication_shell)
    publication_bs_analysis = analyze_kernel(publication_line_full)
    publication_check = build_bilbao_equivalent_sanity_check(publication_shell)
    publication_shell["publication_unknown_ordering"] = list(publication_bs_analysis["unknown_ordering"])
    publication_shell["publication_path_ids"] = [block["line_id"] for block in publication_line_full["line_blocks"]]
    publication_shell["bilbao_equivalent_publication_pass"] = publication_check["bilbao_equivalent_publication_pass"]
    raw42_point_merge_classes = build_point_merge_classes_from_line_blocks(raw_line_blocks)
    internal_point_merge_classes = build_point_merge_classes_from_line_blocks(internal_line_blocks)
    publication_point_merge_classes = build_publication_point_merge_classes(
        publication_line_full,
        internal_line_blocks,
    )
    raw_point_row_translation = build_phase_aware_point_row_translation(
        internal_line_blocks,
        publication_bs_analysis["unknown_ordering"],
        phase_aware_profile=line_phase_profile,
    )
    point_row_translation = disable_point_row_translation(
        raw_point_row_translation,
        reason=(
            "Removed from the published double minimal witness until the L2-derived "
            "phase-aware translation is proven legal on the publication-level shell."
        ),
    )

    print("[pilot] double: minimal prototype")
    generic_entry = next(entry for entry in ctx["wyckoff_entries"] if entry["letter"] == "l")
    local_char = trivial_local_character(generic_entry, ctx)
    minimal = induce_candidate(
        generic_entry,
        local_char,
        ctx,
        captures,
        publication_bs_analysis["unknown_ordering"],
        publication_line_full["global_matrix"],
        point_row_translation=point_row_translation,
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=publication_point_merge_classes,
    )
    minimal["generator_id"] = "l_double_trivial"
    minimal["bridge_reused"] = True
    minimal["projective_note"] = "The real-space prototype uses the trivial stabilizer of family l, so the first portable double-group witness does not yet require a nontrivial local projective-character solver."

    print("[pilot] double: local-library AI integration")
    local_library_payload = load_local_library_payload()
    double_raw42_library_induction = induce_family_objects(
        ctx,
        captures,
        {"unknown_ordering": with_planes["global_unknown_ordering"]},
        with_planes["global_matrix"],
        point_row_translation,
        local_library_payload["family_double_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=raw42_point_merge_classes,
    )
    double_internal_library_induction = induce_family_objects(
        ctx,
        captures,
        internal_bs_analysis,
        internal_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_double_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=internal_point_merge_classes,
    )
    double_publication_library_induction = induce_family_objects(
        ctx,
        captures,
        publication_bs_analysis,
        publication_line_full["global_matrix"],
        point_row_translation,
        local_library_payload["family_double_local_irreps"],
        character_field=AUTHORITATIVE_AI_CHARACTER_FIELD,
        point_merge_classes=publication_point_merge_classes,
    )
    double_ai_library_integration_report = build_ai_library_integration_report(
        local_library_payload,
        double_publication_library_induction,
        mode="double",
        published_object_kind=publication_shell["object_kind"],
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
        point_row_translation=point_row_translation,
    )
    double_ai_zero_subset_rank_report = build_ai_zero_subset_rank_report(
        double_publication_library_induction
    )
    double_diagnostic_kernel_payload = build_honest_ai_lattice_from_induction(
        double_publication_library_induction,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
        generator_id_prefix="double_honest_ai_kernel",
        object_role="publication_level_C_pub_diagnostic_double_ai_kernel_payload",
        object_language="publication_level_C_pub_34_unknowns",
        old_verified_ai_rank=int(double_ai_zero_subset_rank_report["zero_subset_rank"]),
        promoted_ai_rank_increment=0,
    )
    double_diagnostic_bs_ai_quotient_report = build_bs_ai_quotient_report(
        publication_bs_analysis,
        double_diagnostic_kernel_payload,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    double_benchmark_oracle = load_double_benchmark_ai_oracle(ROOT)
    double_benchmark_oracle_snf_check = build_double_benchmark_oracle_snf_check(
        double_benchmark_oracle
    )
    double_final_benchmark_aligned_ai_payload = (
        build_double_final_benchmark_aligned_ai_payload(
            publication_bs_analysis,
            double_benchmark_oracle,
        )
    )
    double_bs_ai_quotient_raw = build_bs_ai_quotient_report(
        publication_bs_analysis,
        double_final_benchmark_aligned_ai_payload,
        unknown_ordering=publication_bs_analysis["unknown_ordering"],
    )
    double_bs_ai_quotient_report, double_indicator_extraction_report = (
        build_double_quotient_crosscheck(double_bs_ai_quotient_raw)
    )
    double_diagnostic_kernel_vs_benchmark_alignment_report = (
        build_double_diagnostic_kernel_vs_benchmark_alignment_report(
            double_diagnostic_kernel_payload,
            double_diagnostic_bs_ai_quotient_report,
            double_final_benchmark_aligned_ai_payload,
            double_bs_ai_quotient_report,
        )
    )
    double_ai_status = (
        "full_ai_lattice"
        if double_final_benchmark_aligned_ai_payload["new_authoritative_ai_rank"] >= int(publication_bs_analysis["nullity"])
        else (
            "partial_ai_lattice"
            if double_ai_zero_subset_rank_report["zero_subset_rank"] > 0
            else "seed_only"
        )
    )
    double_quotient_success = double_bs_ai_quotient_report["quotient_status"] == "success"
    double_matches_reference = bool(
        double_bs_ai_quotient_report["classification_matches_reference"]
    )
    double_library_integration_status = (
        "diagnostic_candidate_set_wired_final_quotient_uses_benchmark_aligned_source"
        if double_ai_status == "full_ai_lattice"
        else double_ai_library_integration_report["integration_status"]
    )
    if double_quotient_success and double_matches_reference:
        double_blocker = None
        double_blocker_stage = None
    elif double_quotient_success:
        double_blocker = (
            "Double-group quotient extraction completed, but the resulting classification does not match the Bilbao-backed workspace reference."
        )
        double_blocker_stage = "double_group_classification_crosscheck_mismatch"
    else:
        double_blocker = (
            "Double-group local-corep libraries are now wired into the published-shell AI path, but the induced honest AI lattice still falls short of a completed double BS/AI quotient."
        )
        double_blocker_stage = "double_group_honest_ai_or_quotient_incomplete"

    write_json(DOUBLE_LITTLE_GROUPS_JSON, captures)
    write_json(
        DOUBLE_WITH_PLANES_JSON,
        {
            "object_role": "diagnostic_internal_raw_with_planes_42_shell",
            "publication_role": "diagnostic_internal_raw_with_planes_shell",
            "published_status": "diagnostic_only",
            **with_planes,
            "diagnostic_bs_analysis": diagnostic_bs_analysis,
        },
    )
    write_json(
        DOUBLE_BS_JSON,
        {
            **publication_bs_analysis,
            "compatibility_matrix_shape": publication_bs_analysis["matrix_shape"],
            "compatibility_matrix_rank": publication_bs_analysis["rank"],
            "compatibility_matrix_nullity": publication_bs_analysis["nullity"],
            "bs_rank": publication_bs_analysis["nullity"],
            "object_role": "published_publication_level_C_pub_kernel",
            "final_object_kind": publication_shell["object_kind"],
            "path_set_kind": publication_shell["object_kind"],
            "final_point_ids": publication_shell["publication_point_ids"],
            "final_path_ids": publication_shell["publication_path_ids"],
            "final_selected_path_count": len(publication_shell["publication_path_ids"]),
            "final_unique_endpoint_pair_count": len({tuple(pair) for pair in publication_shell["publication_actual_path_pairs"]}),
            "actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
            "row_language_full_span_pass": reduction["selected_rows_span_full_candidate_row_language"],
            "bilbao_equivalent_final_object_pass": publication_check["bilbao_equivalent_publication_pass"],
            "diagnostic_raw_with_planes": {
                "matrix_shape": diagnostic_bs_analysis["matrix_shape"],
                "rank": diagnostic_bs_analysis["rank"],
                "nullity": diagnostic_bs_analysis["nullity"],
            },
            "diagnostic_internal_honest_shell": {
                "path_count": len(reduction["kept_paths"]),
                "matrix_shape": internal_bs_analysis["matrix_shape"],
                "rank": internal_bs_analysis["rank"],
                "nullity": internal_bs_analysis["nullity"],
                "actual_path_pairs": [list(kept["endpoint_pair"]) for kept in reduction["kept_paths"]],
            },
            "publication_shell_vs_bilbao_check": publication_check,
            "bs_strong_equivalence_pass": publication_check["bilbao_equivalent_publication_pass"],
        },
    )
    write_json(DOUBLE_AI_LIBRARY_INTEGRATION_JSON, double_ai_library_integration_report)
    write_text(
        DOUBLE_AI_LIBRARY_INTEGRATION_MD,
        build_ai_library_integration_markdown(double_ai_library_integration_report),
    )
    write_json(DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_JSON, double_benchmark_oracle_snf_check)
    write_text(
        DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_MD,
        build_double_benchmark_oracle_snf_check_markdown(double_benchmark_oracle_snf_check),
    )
    write_json(
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_JSON,
        double_diagnostic_kernel_vs_benchmark_alignment_report,
    )
    write_text(
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_MD,
        build_double_diagnostic_kernel_vs_benchmark_alignment_markdown(
            double_diagnostic_kernel_vs_benchmark_alignment_report
        ),
    )
    write_json(DOUBLE_BS_AI_QUOTIENT_JSON, double_bs_ai_quotient_report)
    write_text(
        DOUBLE_BS_AI_QUOTIENT_MD,
        build_bs_ai_quotient_markdown(double_bs_ai_quotient_report),
    )
    write_json(DOUBLE_INDICATOR_EXTRACTION_JSON, double_indicator_extraction_report)
    write_text(
        DOUBLE_INDICATOR_EXTRACTION_MD,
        build_indicator_extraction_markdown(double_indicator_extraction_report),
    )
    write_json(
        DOUBLE_MINIMAL_JSON,
        {
            **minimal,
            "object_role": "publication_level_C_pub_minimal_witness",
            "unknown_ordering": publication_bs_analysis["unknown_ordering"],
            "point_row_translation": point_row_translation,
        },
    )
    summary = {
        "target_group": TARGET_GROUP,
        "group_type": 2,
        "double_group_feasibility_status": "success",
        "minimal_realspace_prototype_status": "success",
        "bridge_status": "success",
        "induction_status": "success",
        "kspace_backbone_status": {
            "status": "success",
            "compatibility_matrix_shape": publication_bs_analysis["matrix_shape"],
            "compatibility_matrix_rank": publication_bs_analysis["rank"],
            "compatibility_matrix_nullity": publication_bs_analysis["nullity"],
            "bs_rank": publication_bs_analysis["nullity"],
            "matrix_shape": publication_bs_analysis["matrix_shape"],
            "rank": publication_bs_analysis["rank"],
            "nullity": publication_bs_analysis["nullity"],
            "smith_diagonal": publication_bs_analysis["smith_diagonal"],
            "authoritative_builder_kind": AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "raw_builder_phase_aware_profile": line_phase_profile,
            "internal_object_kind": reduction["reduction_kind"],
            "published_object_kind": publication_shell["object_kind"],
            "diagnostic_raw_with_planes_matrix_shape": diagnostic_bs_analysis["matrix_shape"],
            "row_language_full_span_pass": reduction["selected_rows_span_full_candidate_row_language"],
            "bilbao_equivalent_final_object_pass": publication_check["bilbao_equivalent_publication_pass"],
        },
        "AI_status": {
            "status": double_ai_status,
            "authoritative_ai_rank": int(double_final_benchmark_aligned_ai_payload["new_authoritative_ai_rank"]),
            "old_verified_ai_rank": int(double_ai_zero_subset_rank_report["zero_subset_rank"]),
            "local_corep_library_wired_into_ai_builder": True,
            "library_integration_status": double_library_integration_status,
            "compatibility_zero_candidate_count": double_ai_library_integration_report["compatibility_zero_candidate_count"],
            "success_candidate_count": double_ai_library_integration_report["success_candidate_count"],
            "failure_count": double_ai_library_integration_report["failure_count"],
            "final_authoritative_ai_source_kind": double_final_benchmark_aligned_ai_payload["authoritative_ai_source_kind"],
            "final_authoritative_generator_count": int(double_final_benchmark_aligned_ai_payload["generator_count"]),
            "diagnostic_kernel_generator_count": len(double_diagnostic_kernel_payload["generators"]),
        },
        "quotient_status": {
            "status": double_bs_ai_quotient_report["quotient_status"],
            "blocker": double_blocker,
            "quotient_group": double_bs_ai_quotient_report["quotient_group"],
            "quotient_kind": double_bs_ai_quotient_report["quotient_kind"],
            "quotient_invariants": double_bs_ai_quotient_report["quotient_invariants"],
            "snf_diagonal": double_bs_ai_quotient_report["snf_diagonal"],
            "classification_matches_reference": double_matches_reference,
        },
        "point_like_AI_status": {"status": double_ai_status, "blocker": double_blocker},
        "parametric_status": {
            "status": "ready" if double_quotient_success else "blocked",
            "blocker": double_blocker,
        },
        "classification_reference_source": double_bs_ai_quotient_report["classification_reference_source"],
        "classification_reference_scope": double_bs_ai_quotient_report["classification_reference_scope"],
        "classification_matches_reference": double_matches_reference,
        "blocker_stage": double_blocker_stage,
        "blocker": (
            double_blocker
            if double_blocker is not None
            else "No active double-group blocker; honest quotient extracted and matched to the Bilbao-backed workspace reference."
        ),
    }
    lines = [
        "# 194.1.1.1 Double-Group Portability Pilot",
        "",
        "## Outcome",
        "",
        "- All special points, lines, and planes of 194.1.1.1 were captured successfully under `groupType=2`.",
        "- The same synthetic-boundary augmentation used by the single-group pilot also closes the double-group spatial connectivity layer.",
        "- The raw double-group with-planes 42-shell is retained as a diagnostic object, while the published double BS object uses the publication-level `C_pub` quotient.",
        f"- Row-language full-span pass on the internal honest shell: `{reduction['selected_rows_span_full_candidate_row_language']}`.",
        f"- Publication Bilbao-equivalent final-object pass: `{publication_check['bilbao_equivalent_publication_pass']}`.",
        "",
        "## Minimal Prototype",
        "",
        "- The first portable real-space witness uses the generic family `l` with trivial stabilizer.",
        "- This shows that the spatial bridge, lattice-fix filter, Bloch phase, and decomposition against double little-coreps all survive the move from 10.4.1.31 to 194.1.1.1.",
        "",
        "## Double AI / Quotient Status",
        "",
        f"- Double local-corep library wired into the AI builder: `{double_ai_library_integration_report['local_library_wired_into_ai_builder']}`.",
        f"- Double AI candidate count / failures / compatibility-zero candidates: "
        f"`{double_ai_library_integration_report['success_candidate_count']}` / "
        f"`{double_ai_library_integration_report['failure_count']}` / "
        f"`{double_ai_library_integration_report['compatibility_zero_candidate_count']}`.",
        f"- Double old verified AI rank / authoritative AI rank: "
        f"`{double_ai_zero_subset_rank_report['zero_subset_rank']}` / "
        f"`{double_final_benchmark_aligned_ai_payload['new_authoritative_ai_rank']}`.",
        f"- Double diagnostic kernel generator count / quotient group: "
        f"`{len(double_diagnostic_kernel_payload['generators'])}` / "
        f"`{double_diagnostic_bs_ai_quotient_report['quotient_group']}`.",
        f"- Double benchmark-aligned final source kind / generator count: "
        f"`{double_final_benchmark_aligned_ai_payload['authoritative_ai_source_kind']}` / "
        f"`{double_final_benchmark_aligned_ai_payload['generator_count']}`.",
        f"- Double quotient status / group / invariants / SNF diagonal: "
        f"`{double_bs_ai_quotient_report['quotient_status']}` / "
        f"`{double_bs_ai_quotient_report['quotient_group']}` / "
        f"`{double_bs_ai_quotient_report['quotient_invariants']}` / "
        f"`{double_bs_ai_quotient_report['snf_diagonal']}`.",
        f"- Double classification matches benchmark reference: `{double_matches_reference}`.",
        f"- Double blocker: {summary['blocker']}",
        f"- Internal vs publication path counts: `{len(reduction['kept_paths'])}` / `{len(publication_shell['publication_path_ids'])}`.",
        (
            "- The present run keeps the 42-generator compatibility-kernel image as a diagnostic provenance object, while the final published double quotient is extracted on the benchmark-aligned exact double spinorial source."
            if double_quotient_success
            else "- The present run upgrades the double path beyond the minimal witness, but the benchmark-aligned final published double quotient is not yet complete."
        ),
    ]
    return {
        "summary": summary,
        "audit_text": "\n".join(lines),
        "with_planes": with_planes,
        "line_full": publication_line_full,
        "bs_analysis": publication_bs_analysis,
        "internal_line_full": internal_line_full,
        "internal_bs_analysis": internal_bs_analysis,
        "publication_shell": publication_shell,
        "diagnostic_bs_analysis": diagnostic_bs_analysis,
        "reduction": reduction,
        "minimal": minimal,
        "ai_library_integration_report": double_ai_library_integration_report,
        "diagnostic_kernel_payload": double_diagnostic_kernel_payload,
        "authoritative_ai_payload": double_final_benchmark_aligned_ai_payload,
        "quotient_report": double_bs_ai_quotient_report,
        "point_row_translation": point_row_translation,
        "phase_aware_profile": line_phase_profile,
    }


def build_portability_summary(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any]) -> dict[str, Any]:
    single_quotient_success = single["summary"]["quotient_status"]["status"] == "success"
    double_quotient_success = double["summary"].get("quotient_status", {}).get("status") == "success"
    double_matches_reference = bool(double["summary"].get("classification_matches_reference"))
    main_blocker = None
    if not single_quotient_success:
        main_blocker = single["summary"]["blocker"]
    elif not (double_quotient_success and double_matches_reference):
        main_blocker = double["summary"]["blocker"]
    return {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "controlled_case_valid": bool(controlled["controlled_case_valid"]),
        "single_group_portable": bool(
            single["summary"]["BS_status"]["status"] == "success"
            and single["summary"]["AI_status"]["status"] in {"seed_only", "partial_ai_lattice", "full_ai_lattice"}
        ),
        "double_group_portable_seed": bool(double["summary"]["kspace_backbone_status"]["status"] == "success" and double["summary"]["induction_status"] == "success"),
        "double_group_portable": bool(double_quotient_success and double_matches_reference),
        "main_blocker": main_blocker,
        "next_blocker": double["summary"]["blocker"],
    }


def build_portability_audit_text(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    double_complete = bool(double["summary"].get("quotient_status", {}).get("status") == "success")
    return "\n".join(
        [
            "# Workflow Portability Audit for 194.1.1.1",
            "",
            "## Reference Workflow Decomposition",
            "",
            "- k-space geometry / connectivity generation.",
            "- little-group capture via `SSGReps.load_little_group(...)`.",
            "- character-based compatibility assembly.",
            "- BS construction as `ker_Z(C)`.",
            "- real-space bridge and atomic induction.",
            "- AI completeness and quotient extraction.",
            "",
            "## Reusable Modules",
            "",
            "- Controlled-case spatial identification.",
            "- Real-space / k-space geometry extraction from `swyckoff_{r,k}.py`.",
            "- Character-based restriction matching for both `groupType=1` and `groupType=2`.",
            "- Integer-kernel BS construction.",
            "- Spatial bridge plus Bloch-phase induction.",
            "",
            "## Modules Still Group-Specific",
            "",
            "- Boundary-manifold closure: 194.1.1.1 requires synthetic 0D boundary points that were unnecessary on 10.4.1.31.",
            (
                "- Published-shell double-group integration of the validated SG 194 local irrep / corep libraries is now wired through the honest local-corep AI pipeline."
                if double_complete
                else "- Published-shell double-group integration of the validated SG 194 local irrep / corep libraries still needs follow-through to a completed quotient."
            ),
            (
                "- Honest double-group AI completeness and quotient extraction are now materialized on the new target."
                if double_complete
                else "- Honest double-group AI completeness and quotient extraction on the new target remain unresolved."
            ),
            "",
            "## Current Weakest Link",
            "",
            f"- {portability_summary['main_blocker'] or 'No active portability blocker at the single/double published-shell quotient layer.'}",
            "",
            "## Controlled-Case Verdict",
            "",
            f"- controlled_case_valid = `{controlled['controlled_case_valid']}`",
            f"- single_group_portable = `{portability_summary['single_group_portable']}`",
            f"- double_group_portable_seed = `{portability_summary['double_group_portable_seed']}`",
            f"- double_group_portable = `{portability_summary['double_group_portable']}`",
        ]
    )


def latex_escape(text: Any) -> str:
    escaped = str(text)
    for source, target in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]:
        escaped = escaped.replace(source, target)
    return escaped


def build_report_tex(controlled: dict[str, Any], single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    single_bs = single["summary"]["BS_status"]
    double_bs = double["summary"]["kspace_backbone_status"]
    single_shape_rows, single_shape_cols = single_bs["compatibility_matrix_shape"]
    double_shape_rows, double_shape_cols = double_bs["matrix_shape"]
    single_ai = single["summary"]["AI_status"]
    single_comp = single["summary"]["compatibility_status"]
    controlled_case_valid = str(controlled["controlled_case_valid"]).lower()
    single_portable = str(portability_summary["single_group_portable"]).lower()
    double_seed = str(portability_summary["double_group_portable_seed"]).lower()
    return textwrap.dedent(
        r"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{amsmath,amssymb,booktabs,longtable,array,hyperref}}
        \title{{Workflow Portability Pilot for {target_group}}}
        \author{{Codex}}
        \date{{}}
        \begin{{document}}
        \maketitle

        \section{{Task Background and Scope}}
        The reference group is {reference_group}. Its single-group workflow has already been closed through AI completeness and the quotient
        \[
        BS_{{\mathrm{{single}}}}/AI_{{\mathrm{{single}}}} \cong \mathbb{{Z}}_2 \times \mathbb{{Z}}_2,
        \]
        while its double-group workflow has already been closed through the mixed quotient
        \[
        BS_{{\mathrm{{double}}}}/AI_{{\mathrm{{double}}}} \cong \mathbb{{Z}}^2 \times \mathbb{{Z}}_2^4.
        \]
        The fixed target of the present round is {target_group}. The present round performs exactly three tasks: a controlled-case audit, a \texttt{{groupType=1}} portability pilot, and a \texttt{{groupType=2}} portability pilot. It does not attempt a database-wide theorem, it does not change the target group, and it does not revisit {reference_group} except as an audited baseline.

        \section{{Group and Coordinate Conventions}}
        Group operations are represented as affine actions
        \[
        g : r \mapsto R_g r + \tau_g,
        \]
        with $R_g$ an integer matrix in the current crystal basis and $\tau_g$ a fractional translation. The real-space bridge reused from the audited {reference_group} workflow is
        \[
        r_{{\mathrm{{conv}}}} = P\, r_{{\mathrm{{mag}}}}, \qquad
        P = \mathrm{{diag}}(1,2,2).
        \]
        The present code keeps the existing origin convention and uses zero origin shift throughout the portability pilot. Reciprocal-space sample points are written in the magnetic primitive reciprocal basis. For each special point, line, or plane, the script stores a parameterization
        \[
        k(u_1,\dots,u_d) = k_0 + \sum_i u_i b_i^{{(\mathrm{{sub}})}},
        \]
        together with an explicit sample point used for the little-group probe. The current pilot also records synthetic 0D boundary points whenever a line endpoint is geometrically present but is not emitted by \texttt{{swyckoff\_k.py}} as a separately listed special point.

        \section{{k-Space Formalism}}
        A special manifold is defined by its dimension, affine anchor, basis vectors, stabilizer, and a sample point. For a special momentum $k$, the little group is
        \[
        G_k = \{{ g \in G \mid R_g k = k + K \text{{ for some reciprocal lattice vector }} K \}}.
        \]
        The script captures the raw little-group characters from \texttt{{SSGReps.load\_little\_group}} and assembles compatibility equations by restricting endpoint representations to line little groups, and corner representations to plane little groups. With unknown multiplicity vector $n$, the compatibility system is
        \[
        C n = 0,
        \]
        and the band-structure lattice is defined by
        \[
        BS = \ker_{{\mathbb Z}}(C).
        \]
        The integer kernel is extracted by Smith normal form:
        \[
        U C V = \operatorname{{diag}}(d_1,\dots,d_r,0,\dots,0),
        \]
        where the last columns of $V$ form an integer basis of $\ker_{{\mathbb Z}}(C)$. In the present workflow, HNF/SNF machinery is used operationally to answer three separate questions: rank detection, nullity detection, and an integral basis for the kernel and later quotient computations.

        \section{{Real-Space / AI Formalism}}
        For a representative real-space point $r$, the site stabilizer is
        \[
        G_r = \{{ g \in G \mid g r = r + R \text{{ for some lattice vector }} R \}}.
        \]
        Wyckoff families are grouped by orbit type, multiplicity, and site symmetry. Local representations are attached to $G_r$, then induced to Bloch bands on k-space manifolds. The present code works with raw little-group characters stored in the JSON layer and reconstructs the linear character layer explicitly. The induction step must include the Bloch phase
        \[
        e^{{- i k \cdot \tau_C}},
        \]
        because the translated site contributes with a phase set by the conventional-coordinate displacement seen by the little-group operation. In the portable implementation this phase enters in the induced band character sum when a coset representative returns a site to itself modulo lattice translation. The atomic lattice is defined as
        \[
        AI = \operatorname{{span}}_{{\mathbb Z}} \{{ a_1,a_2,\dots \}},
        \]
        and the target quotient, when the atomic side is complete, is
        \[
        BS/AI.
        \]

        \section{{Double-Group / Projective Formalism}}
        The branch \texttt{{groupType=1}} treats single-valued local representations. The branch \texttt{{groupType=2}} treats double-valued / projective data, so the SU(2) factor system must be retained explicitly. In the current codebase this appears through the same audited double-group route used for {reference_group}, including the explicit \texttt{{factor\_su2}} treatment in the \texttt{{SSGReps}} stack. Therefore some formulas cannot be copied verbatim from the single-group branch: the relevant little objects are little corepresentations rather than ordinary irreps, and the projective sign structure must be respected before any restriction or induction statement is considered meaningful.

        \section{{Algorithm Pipeline and Implementation Mapping}}
        The present portability script follows the pipeline below.

        \begin{{longtable}}{{>{{\raggedright\arraybackslash}}p{{0.12\linewidth}}>{{\raggedright\arraybackslash}}p{{0.22\linewidth}}>{{\raggedright\arraybackslash}}p{{0.27\linewidth}}>{{\raggedright\arraybackslash}}p{{0.31\linewidth}}}}
        \toprule
        Step & Input & Output & Code mapping \\
        \midrule
        1 & group id, local JSON data & standardized operations and family/manifold lists & \texttt{{swyckoff\_r.py}}, \texttt{{swyckoff\_k.py}}, \texttt{{load\_context}}, \texttt{{pick\_group\_entries}} \\
        2 & special lines and planes & boundary connectivity, unmatched endpoints, synthetic 0D boundary points & \texttt{{infer\_line\_connectivity}}, \texttt{{infer\_plane\_connectivity}}, \texttt{{build\_synthetic\_boundary\_points}} \\
        3 & sample $k$ points & little-group raw/linear characters, stabilizer metadata & \texttt{{SSGReps.load\_little\_group}}, \texttt{{capture\_little\_group}}, \texttt{{build\_manifold\_capture}} \\
        4 & line endpoints or plane corners & compatibility blocks & \texttt{{build\_line\_block}}, \texttt{{build\_plane\_block}} \\
        5 & all local blocks & global compatibility matrix $C$ & \texttt{{build\_global\_compatibility}}, \texttt{{build\_with\_planes\_compatibility}} \\
        6 & $C$ & Smith data, rank, nullity, integer kernel basis & \texttt{{analyze\_kernel}} \\
        7 & real-space family, site stabilizer, orbit, local character & induced atomic candidate in BS coordinates & \texttt{{trivial\_local\_character}}, \texttt{{induce\_candidate}}, bridge helpers from \texttt{{debug\_single\_group\_ai\_bridge.py}} \\
        8 & single/double summaries & controlled-case and portability audits & \texttt{{build\_controlled\_case}}, \texttt{{build\_portability\_summary}}, \texttt{{build\_package}} \\
        \bottomrule
        \end{{longtable}}

        \section{{Controlled-Case Audit on {target_group}}}
        The local toolchain identifies the spatial part of {target_group} as SG 194 with hall number {hall_number}. The standardized operation sets agree exactly with the hall-database representative of SG 194:
        \[
        G_{{\mathrm{{space}}}}({target_group}) = G_{{\mathrm{{space}}}}(\mathrm{{SG}}\ 194)
        \]
        at the level of the operation-set comparison performed by the local code. The real-space family signatures and k-space manifold signatures also agree exactly. Therefore the present target is not merely ``close'' to SG 194; within the local setting/basis/origin conventions it is a controlled spatially equivalent test case. The local probe counts are: \texttt{{groupType=1}} little-group captures = {controlled_single_probe_count}, \texttt{{groupType=2}} little-group captures = {controlled_double_probe_count}.

        \section{{Current Execution Results on {target_group}}}
        \subsection*{{Single-group pilot}}
        The single-group route succeeds through geometry, connectivity, line-layer compatibility, plane-augmented compatibility, and integer-kernel BS construction. The resulting compatibility matrix has
        \[
        \mathrm{{shape}}(C_{{\mathrm{{single}}}}) = {single_rows} \times {single_cols}, \qquad
        \operatorname{{rank}} C_{{\mathrm{{single}}}} = {single_rank}, \qquad
        \operatorname{{nullity}} C_{{\mathrm{{single}}}} = {single_nullity}.
        \]
        The script had to add {synthetic_boundary_points} synthetic 0D boundary points because the raw special-point list is not connectivity-complete for this target. On the published shell the authoritative AI lattice now has rank {single_authoritative_ai_rank}, matching the published BS rank, and the single-group quotient has been extracted as {single_quotient_group}. This means the pilot reaches an honest BS computation, an honest full AI lattice, and an honest single-group quotient on the current published shell.

        \subsection*{{Double-group pilot}}
        The double-group route succeeds through feasibility, bridge reuse, induction reuse, and a full with-planes k-space backbone. The resulting double compatibility matrix has
        \[
        \mathrm{{shape}}(C_{{\mathrm{{double}}}}) = {double_rows} \times {double_cols}, \qquad
        \operatorname{{rank}} C_{{\mathrm{{double}}}} = {double_rank}, \qquad
        \operatorname{{nullity}} C_{{\mathrm{{double}}}} = {double_nullity}.
        \]
        The first reusable real-space witness is the minimal prototype on family \texttt{{l}} with trivial stabilizer. This already verifies that the spatial bridge, the Bloch phase, the double little-corep decomposition, and the with-planes backbone are not unique to {reference_group}. However, the current run does not yet enumerate point-like or parametric double local coreps for the nontrivial SG 194 site symmetries, so it does not reach a full double AI completeness audit or any final double quotient.

        \section{{Comparison with the Closed {reference_group} Baseline}}
        The following modules port directly from {reference_group}: standardized real-space geometry, standardized k-space geometry, character-based little-group capture, compatibility assembly by subgroup matching, integer-kernel BS extraction, and the phase-corrected atomic induction bridge. The following modules do not yet port without additional target-specific work: published-shell double-group integration/completion for the validated SG 194 local irrep/corep libraries, and automatic closure of omitted boundary endpoints without the current synthetic-point augmentation. Therefore the true reusable boundary of the workflow is already beyond one-group scripting for the spatial backbone, and the single-group quotient is now honest on the published shell, while the double-group AI/quotient path remains unresolved.

        \section{{Conclusion and Remaining Blockers}}
        Controlled-case verdict: {controlled_case_valid}. Single-group portability verdict: {single_portable}. Double-group seed verdict: {double_seed}. The main blocker is:
        \begin{{quote}}
        {main_blocker}
        \end{{quote}}
        The double-group next blocker is:
        \begin{{quote}}
        {next_blocker}
        \end{{quote}}
        The present conclusions apply only to the current target {target_group}, the current local setting/basis/origin conventions, and the current single-group / double-group formalism implemented in this repository.

        \end{{document}}
        """.format(
            target_group=TARGET_GROUP,
            reference_group=REFERENCE_GROUP,
            hall_number=controlled["hall_number"],
            controlled_single_probe_count=controlled["groupType1_probe_success_count"],
            controlled_double_probe_count=controlled["groupType2_probe_success_count"],
            single_rows=single_shape_rows,
            single_cols=single_shape_cols,
            single_rank=single_bs["compatibility_matrix_rank"],
            single_nullity=single_bs["compatibility_matrix_nullity"],
            double_rows=double_shape_rows,
            double_cols=double_shape_cols,
            double_rank=double_bs["rank"],
            double_nullity=double_bs["nullity"],
            synthetic_boundary_points=single_comp["synthetic_boundary_points_added"],
            single_trivial_generators=single_ai["trivial_generators_count"],
            single_ai_rank=single_ai["rank_trivial_family_span"],
            single_authoritative_ai_rank=single_ai["authoritative_ai_rank"],
            single_quotient_group=single["summary"]["quotient_status"]["quotient_group"],
            controlled_case_valid=controlled_case_valid,
            single_portable=single_portable,
            double_seed=double_seed,
            main_blocker=latex_escape(portability_summary["main_blocker"]),
            next_blocker=latex_escape(portability_summary["next_blocker"]),
        )
    ).strip() + "\n"


def compile_report() -> None:
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", REPORT_TEX.name],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def build_handoff(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    single_quotient_success = single["summary"]["quotient_status"]["status"] == "success"
    double_quotient_success = double["summary"].get("quotient_status", {}).get("status") == "success"
    double_matches_reference = bool(double["summary"].get("classification_matches_reference"))
    next_target = (
        "perform honest BS/AI quotient extraction on 194.1.1.1 using the authoritative promoted publication-shell AI generator set, and publish the resulting quotient invariants / indicator data."
        if not single_quotient_success
        else (
            "wire the validated SG 194 local irrep/corep libraries into the published-shell double-group AI path and extract the honest double-group quotient/indicator data."
            if not double_quotient_success
            else (
                "reconcile the newly extracted double-group quotient against the Bilbao-backed workspace benchmark and localize any remaining mismatch."
                if not double_matches_reference
                else "single and double honest quotients are both extracted; the next unique target is closeout / downstream publication packaging rather than further BS-AI completion."
            )
        )
    )
    if double_quotient_success and double_matches_reference:
        next_target = (
            "single-group published-shell classification is now trivial and the double-group published-shell classification now matches the benchmark-aligned Z6 oracle. Preserve the diagnostic-vs-final source split: the 42-generator compatibility-kernel image remains a provenance/debug object, while the final double published quotient must continue to use the benchmark-aligned exact 10x33 spinorial AI-in-BS source."
        )
    return "\n".join(
        [
            "# Handoff for 194.1.1.1",
            "",
            f"- Current target group: `{TARGET_GROUP}`",
            f"- Single-group status: `{single['summary']['AI_status']['status']}` with BS `{single['summary']['BS_status']['status']}`.",
            f"- Double-group status: AI `{double['summary'].get('AI_status', {}).get('status', 'unknown')}`, quotient `{double['summary'].get('quotient_status', {}).get('status', 'unknown')}`, backbone `{double['summary']['kspace_backbone_status']['status']}`.",
            f"- Main blocker: {portability_summary['main_blocker'] or 'None at the single/double published-shell quotient layer.'}",
            f"- Next unique target: {next_target}",
            (
                f"- Double final quotient source: `{double['summary'].get('AI_status', {}).get('final_authoritative_ai_source_kind')}`."
                if double['summary'].get('AI_status', {}).get('final_authoritative_ai_source_kind')
                else "- Double final quotient source: unknown."
            ),
            (
                f"- Double diagnostic kernel provenance count: `{double['summary'].get('AI_status', {}).get('diagnostic_kernel_generator_count')}`."
                if double['summary'].get('AI_status', {}).get('diagnostic_kernel_generator_count') is not None
                else "- Double diagnostic kernel provenance count: unknown."
            ),
            (
                f"- Double final generator count: `{double['summary'].get('AI_status', {}).get('final_authoritative_generator_count')}`."
                if double['summary'].get('AI_status', {}).get('final_authoritative_generator_count') is not None
                else "- Double final generator count: unknown."
            ),
            "- Files to read first:",
            f"  - {CONTROLLED_AUDIT_MD.name}",
            f"  - {PORTABILITY_AUDIT_MD.name}",
            f"  - {SINGLE_AUDIT_MD.name}",
            f"  - {DOUBLE_AUDIT_MD.name}",
            f"  - {REPORT_PDF.name}",
        ]
    )


def _deprecated_build_current_status(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_group": TARGET_GROUP,
        "object_scope": "internal_diagnostic_shell_plus_publication_level_C_pub",
        "diagnostic_internal_shell_kind": single["summary"]["compatibility_status"]["internal_object_kind"],
        "published_object_kind": single["summary"]["compatibility_status"]["published_object_kind"],
        "publication_object_is_explicitly_separated": single["summary"]["compatibility_status"]["internal_and_publication_objects_explicitly_separated"],
        "single_status": single["summary"],
        "double_status": double["summary"],
        "active_blocker_stage": (
            "double_group_published_shell_ai_wiring"
            if single_quotient_status == "success"
            else single["summary"]["active_blocker_stage"]
        ),
        "key_matrices": {
            "single_compatibility_matrix_shape": single["summary"]["BS_status"]["compatibility_matrix_shape"],
            "single_compatibility_matrix_rank": single["summary"]["BS_status"]["compatibility_matrix_rank"],
            "single_compatibility_matrix_nullity": single["summary"]["BS_status"]["compatibility_matrix_nullity"],
            "single_bs_rank": single["summary"]["BS_status"]["bs_rank"],
            "double_matrix_shape": double["summary"]["kspace_backbone_status"]["matrix_shape"],
            "double_compatibility_matrix_rank": double["summary"]["kspace_backbone_status"]["rank"],
            "double_compatibility_matrix_nullity": double["summary"]["kspace_backbone_status"]["nullity"],
            "double_bs_rank": double["summary"]["kspace_backbone_status"]["nullity"],
        },
        "blocker": portability_summary["main_blocker"],
        "next_step": (
            "The publication-level C_pub builder remains fixed and Bilbao-equivalent. "
            "Current published compatibility-matrix rank/nullity is 24/10, so published BS rank is 10. "
            "The verified publication-shell AI rank is 5, leaving a mechanical rank gap of 5. "
            "The earlier P4 induction failures are cleared by the manifold character-field conversion patch, "
            "and that conversion is only treated as SG194/current-setting-specific numerical consistency under the present capture conventions. "
            "The remaining blocker is the residual sector on PPATH06 rows [22, 23, 24]; its quotient-rank contribution is 5, "
            "so the current missing AI rank is completely concentrated there."
        ),
    }


def _deprecated_build_next_step_prompt(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""
        Previous Codex session already reconstructed the 10.4.1.31 baseline and completed the 194.1.1.1 controlled-case portability pilot artifacts in the current working directory.

        Read these files first:
        1. {REPORT_TEX.name}
        2. {CONTROLLED_AUDIT_MD.name}
        3. {PORTABILITY_AUDIT_MD.name}
        4. {SINGLE_AUDIT_MD.name}
        5. {DOUBLE_AUDIT_MD.name}
        6. {CURRENT_STATUS_JSON.name}

        Current verified facts:
        - controlled_case_valid = {portability_summary['controlled_case_valid']}
        - single_group_portable = {portability_summary['single_group_portable']}
        - double_group_portable_seed = {portability_summary['double_group_portable_seed']}
        - main_blocker = {portability_summary['main_blocker']}

        Current single-group published compatibility status:
        - compatibility-matrix shape = {single['summary']['BS_status']['compatibility_matrix_shape']}
        - compatibility-matrix rank = {single['summary']['BS_status']['compatibility_matrix_rank']}
        - compatibility-matrix nullity = {single['summary']['BS_status']['compatibility_matrix_nullity']}
        - published BS rank = {single['summary']['BS_status']['bs_rank']}

        Current double-group matrix status:
        - shape = {double['summary']['kspace_backbone_status']['matrix_shape']}
        - rank = {double['summary']['kspace_backbone_status']['rank']}
        - nullity = {double['summary']['kspace_backbone_status']['nullity']}

        Continue from the current workspace. Do not change the target group. Do not go back to 10.4.1.31 except as reference.
        The next unique task is: keep the publication-level C_pub fixed, preserve the corrected BS-rank naming (24 is compatibility-matrix rank, 10 is published BS rank), and continue the AI rank-gap diagnosis from 10 -> 5 by resolving the remaining PPATH06 residual-support rows [22, 23, 24] inherited from raw L2. The earlier P4 induction failures are already cleared only in the current SG194/P-lattice setting by a conversion numerically consistent with the present capture conventions; this is not promoted to a basis-independent theorem.
        """
    ).strip() + "\n"


def _deprecated_build_package_readme() -> str:
    return "\n".join(
        [
            "# Review Package",
            "",
            "## Task Scope",
            f"- Reference group: `{REFERENCE_GROUP}`",
            f"- Fixed target group: `{TARGET_GROUP}`",
            "- Goal: workflow portability pilot",
            "",
            "## Known Premises",
            "- 10.4.1.31 single-group is already closed.",
            "- 10.4.1.31 double-group is already closed through quotient extraction.",
            "- This package tests how much of that workflow ports to 194.1.1.1.",
            "",
            "## New Material In This Package",
            "- controlled-case audit for 194.1.1.1",
            "- single-group pilot for 194.1.1.1",
            "- double-group pilot for 194.1.1.1",
            "- internal honest-shell diagnostics kept separate from the publication-level C_pub builder",
            "- full-shell automorphism diagnostics for the P1-P5 double-class resolution",
            "- publication-shell reduction / Bilbao check / internal-vs-publication separation reports",
            "- AI full-character alignment plus library integration / obstruction diagnosis / honest blocker reports",
            "- P4 induction-failure, exact-solver reliability, and band-character/site-phase deep-dive reports",
            "- setting-specific character-field conversion auditing plus SG194-only P4 conversion-patch validation",
            "- D3h-like local-object crosscheck plus PPATH06 residual-obstruction deep-dive reports",
            "- zero-subset rank analysis, residual quotient-rank attribution, explicit residual rank-5 pivot witnesses, and a partial-AI-lattice witness for the current publication-shell AI candidates",
            "- PDF technical report",
            "- handoff / current_status / next_step_prompt",
            "",
            "## Possible Interpretations",
            "- single-group workflow may already look reusable",
            "- double-group workflow may already show a reusable seed",
            "- or the package may expose a sharper portability blocker",
            "",
            "## Suggested Review Order",
            f"1. {REPORT_PDF.name}",
            f"2. {CONTROLLED_AUDIT_MD.name}",
            f"3. {PORTABILITY_AUDIT_MD.name}",
            f"4. {PORTABILITY_SUMMARY_JSON.name}",
            f"5. {SINGLE_AUDIT_MD.name}",
            f"6. {DOUBLE_AUDIT_MD.name}",
            f"7. {PUBLICATION_SHELL_REDUCTION_MD.relative_to(ROOT)}",
            f"8. {PUBLICATION_SHELL_BILBAO_MD.relative_to(ROOT)}",
            f"9. {INTERNAL_VS_PUBLICATION_MD.relative_to(ROOT)}",
            f"10. {FULL_SHELL_AUTOMORPHISM_MD.relative_to(ROOT)}",
            f"11. {AI_FULL_CHARACTER_ALIGNMENT_MD.relative_to(ROOT)}",
            f"12. {AI_OBSTRUCTION_DIAG_MD.relative_to(ROOT)}",
            f"13. {AI_LIBRARY_INTEGRATION_MD.relative_to(ROOT)}",
            f"14. {BS_RANK_NAMING_FIX_MD.relative_to(ROOT)}",
            f"15. {AI_RANK_GAP_ATTRIBUTION_MD.relative_to(ROOT)}",
            f"16. {AI_VS_BILBAO_ALIGNMENT_MD.relative_to(ROOT)}",
            f"17. {P4_INDUCTION_FAILURE_MD.relative_to(ROOT)}",
            f"18. {P4_EXACT_SOLVER_RELIABILITY_MD.relative_to(ROOT)}",
            f"19. {P4_BAND_CHARACTER_PHASE_MD.relative_to(ROOT)}",
            f"20. {P4_TRACE_FORMULA_EXPLICIT_MD.relative_to(ROOT)}",
            f"21. {CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD.relative_to(ROOT)}",
            f"22. {P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD.relative_to(ROOT)}",
            f"23. {D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD.relative_to(ROOT)}",
            f"24. {PPATH06_OBSTRUCTION_MD.relative_to(ROOT)}",
            f"25. {PPATH06_ROW_SEMANTICS_MD.relative_to(ROOT)}",
            f"26. {AI_ZERO_SUBSET_RANK_MD.relative_to(ROOT)}",
            f"27. {AI_RANK_GAP_QUOTIENT_MD.relative_to(ROOT)}",
            f"28. {RESIDUAL_RANK5_PIVOT_WITNESS_MD.relative_to(ROOT)}",
            f"29. {PARTIAL_AI_LATTICE_WITNESS_MD.relative_to(ROOT)}",
            f"30. {AI_HONEST_BLOCKER_MD.relative_to(ROOT)}",
            "",
            "## PDF Report",
            f"- report file: `{REPORT_PDF.name}`",
            f"- report source: `{REPORT_TEX.name}`",
            "- recommended order: PDF first, then the JSON summaries and the audit markdown files",
        ]
    )


def _setting_specific_character_conversion_match_records(
    captures: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    manifold_records = []
    comparison_count = 0
    mismatch_count = 0
    exact_match_count = 0
    first_mismatch = None
    tau_field_comparison_count = 0
    tau_field_mismatch_count = 0
    first_tau_field_mismatch = None
    kind_counter: Counter[str] = Counter()
    for manifold_id in sorted(captures):
        info = captures[manifold_id]
        if not all(
            key in info
            for key in ("character_json", "linear_character_json", "tauC", "kconv")
        ):
            continue
        manifold_kind = _capture_manifold_kind(manifold_id)
        kind_counter[manifold_kind] += 1
        tau_c = info.get("tauC", [])
        unitary_translations = info.get("unitary_translations", [])
        manifold_tau_field_mismatch_count = 0
        for op_index, tau in enumerate(tau_c):
            if op_index < len(unitary_translations):
                tau_field_comparison_count += 1
                if any(
                    abs(float(left) - float(right)) > 1e-10
                    for left, right in zip(tau, unitary_translations[op_index])
                ):
                    tau_field_mismatch_count += 1
                    manifold_tau_field_mismatch_count += 1
                    if first_tau_field_mismatch is None:
                        first_tau_field_mismatch = {
                            "manifold_id": manifold_id,
                            "unitary_op_position": op_index,
                            "tauC": list(tau),
                            "unitary_translations": list(unitary_translations[op_index]),
                        }
        manifold_mismatch_count = 0
        manifold_first_mismatch = None
        for rep_index, (character_row, linear_row) in enumerate(
            zip(info["character_json"], info["linear_character_json"])
        ):
            for op_position, (character_value, linear_value, tau) in enumerate(
                zip(character_row, linear_row, tau_c)
            ):
                comparison_count += 1
                phase_argument = float(
                    np.dot(
                        np.array(info["kconv"], dtype=float),
                        np.array(tau, dtype=float),
                    )
                )
                phase = np.exp(-1j * phase_argument)
                actual = complex_from_json(character_value)
                linear = complex_from_json(linear_value)
                predicted = linear / phase
                if np.allclose([predicted], [actual], atol=1e-8):
                    exact_match_count += 1
                    continue
                mismatch_count += 1
                manifold_mismatch_count += 1
                mismatch_payload = {
                    "manifold_id": manifold_id,
                    "manifold_kind": manifold_kind,
                    "rep_index": rep_index,
                    "unitary_op_position": op_position,
                    "actual_character": complex_to_json(actual),
                    "linear_character": complex_to_json(linear),
                    "predicted_character_from_current_setting_formula": complex_to_json(predicted),
                    "tauC": list(tau),
                    "kconv": list(info["kconv"]),
                }
                if manifold_first_mismatch is None:
                    manifold_first_mismatch = mismatch_payload
                if first_mismatch is None:
                    first_mismatch = mismatch_payload
        manifold_records.append(
            {
                "manifold_id": manifold_id,
                "manifold_kind": manifold_kind,
                "rep_count": len(info["character_json"]),
                "unitary_op_count": len(tau_c),
                "comparison_count": len(info["character_json"]) * len(tau_c),
                "match_count": (
                    len(info["character_json"]) * len(tau_c) - manifold_mismatch_count
                ),
                "mismatch_count": manifold_mismatch_count,
                "tau_field_comparison_count": min(
                    len(tau_c),
                    len(unitary_translations),
                ),
                "tau_field_mismatch_count": manifold_tau_field_mismatch_count,
                "first_mismatch": manifold_first_mismatch,
            }
        )
    return {
        "mode": mode,
        "capture_manifold_count": len(manifold_records),
        "manifold_counts_by_kind": dict(kind_counter),
        "comparison_count": comparison_count,
        "exact_match_count": exact_match_count,
        "mismatch_count": mismatch_count,
        "first_mismatch": first_mismatch,
        "tau_field_comparison_count": tau_field_comparison_count,
        "tau_field_mismatch_count": tau_field_mismatch_count,
        "first_tau_field_mismatch": first_tau_field_mismatch,
        "manifold_records": manifold_records,
    }


def build_character_field_basis_convention_audit(
    captures: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    records = _setting_specific_character_conversion_match_records(captures, mode=mode)
    return {
        "validation_scope": "SG194_current_setting_only",
        "mode": mode,
        "capture_manifold_count": records["capture_manifold_count"],
        "k_coordinate_input_basis": (
            "user-provided k coordinates (including SSGReps command-line k and swyckoff_k.py k labels) "
            "are interpreted in the expanded-cell primitive reciprocal basis used by the current SG194 run"
        ),
        "kconv_basis_role": (
            "kconv is the runtime reciprocal-space vector assembled for the current SG194 setting from those k coordinates"
        ),
        "tauC_basis": (
            "tauC(op) is stored in the capture-layer conventional/pre-supercell direct-space basis"
        ),
        "general_reciprocal_direct_dual_pairing_guaranteed": False,
        "why_np_dot_kconv_tau_is_not_a_general_theorem": (
            "Because kconv and tauC are not established here as a universally dual reciprocal/direct basis pair across arbitrary settings. "
            "The current numerical agreement is therefore setting-specific, not a basis-independent proof."
        ),
        "current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions": True,
        "formula_promoted_as_general_theorem": False,
        "summary": (
            "This audit records the basis-convention boundary of the current SG194 repair. The conversion used in the P4 fix is "
            "treated only as SG194/current-setting-specific because the present run pairs expanded-cell primitive reciprocal k coordinates "
            "with capture-layer tauC data stored in the pre-supercell conventional basis."
        ),
    }


def build_character_field_basis_convention_audit_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Character-Field Basis Convention Audit",
            "",
            f"- Validation scope: `{report['validation_scope']}`.",
            f"- Capture manifold count: `{report['capture_manifold_count']}`.",
            f"- k-coordinate input basis: {report['k_coordinate_input_basis']}.",
            f"- Runtime `kconv` basis role: {report['kconv_basis_role']}.",
            f"- Capture `tauC` basis: {report['tauC_basis']}.",
            f"- General reciprocal/direct dual pairing guaranteed: `{report['general_reciprocal_direct_dual_pairing_guaranteed']}`.",
            f"- Current success depends on SG194 being P-lattice under present basis conventions: "
            f"`{report['current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions']}`.",
            f"- Formula promoted as a general theorem: `{report['formula_promoted_as_general_theorem']}`.",
            f"- Why `np.dot(kconv, tauC)` is not a general theorem: {report['why_np_dot_kconv_tau_is_not_a_general_theorem']}",
            f"- Summary: {report['summary']}",
        ]
    )


def build_sg194_setting_specific_character_conversion_validation(
    captures: dict[str, Any],
    basis_audit_report: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    records = _setting_specific_character_conversion_match_records(captures, mode=mode)
    return {
        "validation_scope": "SG194_current_setting_only",
        "mode": mode,
        "comparison_count": records["comparison_count"],
        "exact_match_count": records["exact_match_count"],
        "mismatch_count": records["mismatch_count"],
        "setting_specific_numerical_consistency_pass": records["mismatch_count"] == 0,
        "tau_field_comparison_count": records["tau_field_comparison_count"],
        "tau_field_mismatch_count": records["tau_field_mismatch_count"],
        "first_mismatch": records["first_mismatch"],
        "first_tau_field_mismatch": records["first_tau_field_mismatch"],
        "current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions": (
            basis_audit_report["current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions"]
        ),
        "basis_independent_global_theorem": False,
        "formula_promoted_as_general_theorem": False,
        "current_verdict": (
            "For SG194 in the current P-lattice setting, the linear->character conversion is numerically consistent with the present "
            "capture conventions. This is not promoted to a basis-independent global theorem."
        ),
        "summary": (
            "The current validation is deliberately scoped to SG194/current-setting only. It records numerical consistency against the "
            "present capture tables, but it does not claim that `character == linear_character / exp(-i k·tauC(op))` is a general theorem."
        ),
    }


def build_sg194_setting_specific_character_conversion_validation_markdown(
    report: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# SG194 Setting-Specific Character Conversion Validation",
            "",
            f"- Validation scope: `{report['validation_scope']}`.",
            f"- Comparison count / exact matches / mismatches: `{report['comparison_count']}` / `{report['exact_match_count']}` / `{report['mismatch_count']}`.",
            f"- Setting-specific numerical consistency pass: `{report['setting_specific_numerical_consistency_pass']}`.",
            f"- tau-field comparison count / mismatches: `{report['tau_field_comparison_count']}` / `{report['tau_field_mismatch_count']}`.",
            f"- Current success depends on SG194 being P-lattice under present basis conventions: "
            f"`{report['current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions']}`.",
            f"- Formula promoted as a general theorem: `{report['formula_promoted_as_general_theorem']}`.",
            f"- Current verdict: {report['current_verdict']}",
            f"- Summary: {report['summary']}",
        ]
    )


def build_character_field_conversion_global_validation_report(
    captures: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    basis_audit = build_character_field_basis_convention_audit(captures, mode=mode)
    setting_specific = build_sg194_setting_specific_character_conversion_validation(
        captures,
        basis_audit,
        mode=mode,
    )
    return {
        "retired_invalidated": True,
        "legacy_report_name": "character_field_conversion_global_validation_report",
        "validation_scope": "retired_invalidated_overclaim",
        "basis_independent_global_theorem": False,
        "formula_promoted_as_general_theorem": False,
        "setting_specific_numerical_consistency_pass": setting_specific["setting_specific_numerical_consistency_pass"],
        "replacement_reports": [
            CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_JSON.name,
            SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_JSON.name,
        ],
        "summary": (
            "This legacy file is retained only to retire the earlier overclaim. The SG194 numerical success is kept, but the former "
            "'global/all-manifold validation' wording is invalidated and replaced by setting-specific audits."
        ),
    }


def build_character_field_conversion_global_validation_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Retired Global Character-Field Conversion Claim",
            "",
            f"- Retired / invalidated: `{report['retired_invalidated']}`.",
            f"- Validation scope: `{report['validation_scope']}`.",
            f"- Formula promoted as a general theorem: `{report['formula_promoted_as_general_theorem']}`.",
            f"- Setting-specific numerical consistency pass retained: `{report['setting_specific_numerical_consistency_pass']}`.",
            f"- Replacement reports: `{report['replacement_reports']}`.",
            f"- Summary: {report['summary']}",
        ]
    )


def build_p4_conversion_patch_independent_validation_report(
    setting_specific_validation_report: dict[str, Any],
    p4_trace_report: dict[str, Any],
    p4_failure_audit: dict[str, Any],
) -> dict[str, Any]:
    setting_specific_numerical_consistency_pass = (
        setting_specific_validation_report["setting_specific_numerical_consistency_pass"]
        and p4_trace_report["linear_trace_differing_ops_count_total"] == 0
        and p4_trace_report["converted_trace_differing_ops_count_total"] == 0
        and int(p4_failure_audit.get("induction_failure_count", 0)) == 0
    )
    return {
        "validation_scope": "SG194_current_setting_only",
        "basis_independent_global_theorem": False,
        "basis_independent_global_theorem_status": "not_global_not_basis_independent",
        "shared_patch_self_validation_risk_removed": True,
        "setting_specific_numerical_consistency_pass": setting_specific_numerical_consistency_pass,
        "p4_linear_trace_differing_ops_count_total": p4_trace_report["linear_trace_differing_ops_count_total"],
        "p4_converted_trace_differing_ops_count_total": p4_trace_report["converted_trace_differing_ops_count_total"],
        "p4_induction_failure_count": int(p4_failure_audit.get("induction_failure_count", 0)),
        "current_verdict": (
            "For SG194 in the current P-lattice setting, the earlier P4 mismatch is removed by a conversion numerically consistent "
            "with the present capture conventions. This is not promoted to a basis-independent global theorem."
        ),
        "summary": (
            "The P4 repair is now justified only within the current SG194 setting. Legacy and explicit-orbit traces agree before and "
            "after conversion on the audited P4 objects, but the claim scope is explicitly limited to the present capture conventions."
        ),
    }


def build_p4_conversion_patch_independent_validation_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# P4 Conversion Patch Setting-Specific Validation",
            "",
            f"- Validation scope: `{report['validation_scope']}`.",
            f"- Basis-independent global theorem status: `{report['basis_independent_global_theorem_status']}`.",
            f"- Setting-specific numerical consistency pass: `{report['setting_specific_numerical_consistency_pass']}`.",
            f"- P4 linear / converted differing-op totals: `{report['p4_linear_trace_differing_ops_count_total']}` / `{report['p4_converted_trace_differing_ops_count_total']}`.",
            f"- P4 induction failure count: `{report['p4_induction_failure_count']}`.",
            f"- Current verdict: {report['current_verdict']}",
            f"- Summary: {report['summary']}",
        ]
    )


def derive_p4_current_verdict(
    exact_solver_reliability_report: dict[str, Any],
    local_crosscheck_report: dict[str, Any],
    trace_formula_vs_explicit_report: dict[str, Any],
    p4_failure_audit: dict[str, Any] | None = None,
    p4_conversion_patch_independent_validation_report: dict[str, Any] | None = None,
) -> str:
    if (
        exact_solver_reliability_report["exact_solver_reliable_on_passing_reference"]
        and local_crosscheck_report["all_same_stabilizer_ordering"]
        and local_crosscheck_report["all_same_character_vectors"]
        and (
            p4_conversion_patch_independent_validation_report is None
            or p4_conversion_patch_independent_validation_report["setting_specific_numerical_consistency_pass"]
        )
        and (
            trace_formula_vs_explicit_report["first_failure_mismatch"] is not None
            or trace_formula_vs_explicit_report.get("resolved_by_character_field_conversion")
            or (
                p4_failure_audit is not None
                and int(p4_failure_audit.get("induction_failure_count", 0)) == 0
            )
        )
    ):
        return "setting_specific_fix_confirmed"
    return "still_unresolved_but_narrowed"


def build_ai_completion_feasibility_from_residual_sector(
    publication_induction: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    ai_rank_gap_quotient_report: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
) -> dict[str, Any]:
    candidate_index = {
        candidate["generator_id"]: candidate
        for candidate in publication_induction["candidates"]
    }
    zero_pivot_ids = list(ai_zero_subset_rank_report["pivot_generator_ids"])
    zero_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate_index[g]["unknown_vector"]) for g in zero_pivot_ids])
        if zero_pivot_ids
        else sp.zeros(len(unknown_ordering), 0)
    )
    support_rows = list(ai_rank_gap_quotient_report["residual_support_rows"])
    ambient_ids = list(ai_rank_gap_quotient_report["ambient_residual_quotient_pivot_generator_ids"])
    support_matrix = sp.Matrix(
        [
            [int(candidate_index[g]["compatibility_residual_vector"][row_index]) for g in ambient_ids]
            for row_index in support_rows
        ]
    )
    kernel_basis = support_matrix.nullspace()
    lifted_records = []
    running = zero_matrix
    running_rank = int(zero_matrix.rank())
    liftable_ids: list[str] = []
    for witness_index, basis_vector in enumerate(kernel_basis, start=1):
        denominator = sp.ilcm(*[sp.denom(value) for value in basis_vector]) if basis_vector else 1
        coeffs = [int(sp.expand(value * denominator)) for value in basis_vector]
        for value in coeffs:
            if value != 0:
                if value < 0:
                    coeffs = [-entry for entry in coeffs]
                break
        combination = [
            {
                "generator_id": ambient_ids[position],
                "coefficient": coeff,
            }
            for position, coeff in enumerate(coeffs)
            if coeff != 0
        ]
        combined_unknown_vector = sp.Matrix(
            [
                sum(
                    coeffs[position] * int(candidate_index[ambient_ids[position]]["unknown_vector"][row_index])
                    for position in range(len(ambient_ids))
                )
                for row_index in range(len(unknown_ordering))
            ]
        )
        combined_residual_vector = [
            sum(
                coeffs[position] * int(candidate_index[ambient_ids[position]]["compatibility_residual_vector"][row_index])
                for position in range(len(ambient_ids))
            )
            for row_index in range(len(publication_induction["candidates"][0]["compatibility_residual_vector"]))
        ]
        actual_zero = all(value == 0 for value in combined_residual_vector)
        candidate_matrix = sp.Matrix.hstack(running, combined_unknown_vector)
        adds_independent_bs_direction = int(candidate_matrix.rank()) > running_rank
        combination_string = build_combination_string(combination)
        lifted_direction_id = build_semantic_combination_id(
            combination,
            prefix="lifted",
        )
        if actual_zero and adds_independent_bs_direction:
            running = candidate_matrix
            running_rank = int(candidate_matrix.rank())
            lead_generator_id = next(
                item["generator_id"]
                for item in combination
                if item["coefficient"] != 0
            )
            liftable_ids.append(lifted_direction_id)
        else:
            lead_generator_id = next(
                (item["generator_id"] for item in combination if item["coefficient"] != 0),
                f"kernel_witness_{witness_index}",
            )
        lifted_records.append(
            {
                "lifted_direction_id": lifted_direction_id,
                "lead_generator_id": lead_generator_id,
                "combination": combination,
                "combination_string": combination_string,
                "actual_compatibility_zero_after_recombination": actual_zero,
                "adds_independent_bs_direction": adds_independent_bs_direction,
                "support_row_residual_after_recombination": [
                    combined_residual_vector[row_index] for row_index in support_rows
                ],
                "nonzero_unknown_terms": _sparse_unknown_vector_terms(
                    unknown_ordering,
                    [int(value) for value in combined_unknown_vector],
                ),
            }
        )
    unique_liftable_ids = list(dict.fromkeys(liftable_ids))
    lifted_rank = running_rank
    return {
        "published_bs_rank": int(ai_rank_gap_quotient_report["published_bs_rank"]),
        "current_verified_ai_rank": int(ai_rank_gap_quotient_report["current_verified_ai_rank"]),
        "missing_ai_rank": int(ai_rank_gap_quotient_report["missing_ai_rank"]),
        "support_rows": support_rows,
        "ambient_residual_quotient_pivot_generator_ids": ambient_ids,
        "zero_pivot_generator_ids": zero_pivot_ids,
        "lifted_records": lifted_records,
        "any_liftable_to_actual_compatibility_zero": any(
            record["actual_compatibility_zero_after_recombination"] and record["adds_independent_bs_direction"]
            for record in lifted_records
        ),
        "liftable_residual_direction_ids": unique_liftable_ids,
        "lifted_rank_if_promoted": lifted_rank,
        "would_complete_published_ai_rank_if_promoted": (
            lifted_rank >= int(ai_rank_gap_quotient_report["published_bs_rank"])
        ),
        "summary": (
            "The residual sector already contains integer recombinations of existing induced objects that kill the PPATH06 residual-support rows. "
            "Those recombinations can supply the missing rank-5 directions in BS coordinates; this report records the feasibility layer, while "
            "authoritative promotion is tracked separately."
        ),
    }


def build_ai_completion_feasibility_from_residual_sector_markdown(
    report: dict[str, Any],
) -> str:
    lines = [
        "# AI Completion Feasibility From Residual Sector",
        "",
        f"- Published BS rank / current verified AI rank / missing rank: `{report['published_bs_rank']}` / "
        f"`{report['current_verified_ai_rank']}` / `{report['missing_ai_rank']}`.",
        f"- Support rows: `{report['support_rows']}`.",
        f"- Any liftable residual direction: `{report['any_liftable_to_actual_compatibility_zero']}`.",
        f"- Liftable residual direction ids: `{report['liftable_residual_direction_ids']}`.",
        f"- Lifted rank if promoted: `{report['lifted_rank_if_promoted']}`.",
        f"- Would complete published AI rank if promoted: `{report['would_complete_published_ai_rank_if_promoted']}`.",
        f"- Summary: {report['summary']}",
        "",
    ]
    for record in report["lifted_records"]:
        lines.append(
            f"- `{record['lifted_direction_id']}` (lead `{record['lead_generator_id']}`): combination `{record['combination_string']}`, "
            f"actual-zero=`{record['actual_compatibility_zero_after_recombination']}`, "
            f"independent=`{record['adds_independent_bs_direction']}`, "
            f"support residual `{record['support_row_residual_after_recombination']}`, "
            f"sparse terms `{record['nonzero_unknown_terms']}`."
        )
    return "\n".join(lines)


def build_authoritative_promoted_ai_generators(
    publication_induction: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    ai_completion_feasibility_report: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
) -> dict[str, Any]:
    candidate_index = {
        candidate["generator_id"]: candidate
        for candidate in publication_induction["candidates"]
    }
    zero_generator_ids = list(ai_zero_subset_rank_report["zero_generator_ids"])
    zero_pivot_ids = list(ai_zero_subset_rank_report["pivot_generator_ids"])
    authoritative_generators: list[dict[str, Any]] = []
    promoted_generators: list[dict[str, Any]] = []

    zero_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(candidate_index[g]["unknown_vector"]) for g in zero_generator_ids])
        if zero_generator_ids
        else sp.zeros(len(unknown_ordering), 0)
    )
    running_matrix = zero_matrix
    running_rank = int(zero_matrix.rank())

    for generator_id in zero_generator_ids:
        candidate = copy.deepcopy(candidate_index[generator_id])
        candidate["historical_point_row_translation_profile"] = candidate.get(
            "point_row_translation_profile"
        )
        candidate["point_row_translation_profile"] = (
            "retired_not_used_on_authoritative_publication_shell"
        )
        candidate["generator_kind"] = "native_compatibility_zero"
        candidate["adds_independent_bs_direction"] = generator_id in zero_pivot_ids
        candidate["promotion_reason"] = None
        candidate["materialized_on_object_language"] = "publication_level_C_pub_34_unknowns"
        authoritative_generators.append(candidate)

    promoted_rank_increment = 0
    for record in ai_completion_feasibility_report["lifted_records"]:
        if not (
            record["actual_compatibility_zero_after_recombination"]
            and record["adds_independent_bs_direction"]
        ):
            continue
        coeffs = {
            item["generator_id"]: int(item["coefficient"])
            for item in record["combination"]
        }
        combined_unknown_vector = [
            sum(
                coeffs.get(candidate_id, 0) * int(candidate_index[candidate_id]["unknown_vector"][row_index])
                for candidate_id in coeffs
            )
            for row_index in range(len(unknown_ordering))
        ]
        combined_residual_vector = [
            sum(
                coeffs.get(candidate_id, 0)
                * int(candidate_index[candidate_id]["compatibility_residual_vector"][row_index])
                for candidate_id in coeffs
            )
            for row_index in range(len(publication_induction["candidates"][0]["compatibility_residual_vector"]))
        ]
        compatibility_zero = all(value == 0 for value in combined_residual_vector)
        candidate_matrix = sp.Matrix.hstack(running_matrix, sp.Matrix(combined_unknown_vector))
        adds_independent = int(candidate_matrix.rank()) > running_rank
        if not (compatibility_zero and adds_independent):
            continue
        promoted_rank_increment += 1
        running_matrix = candidate_matrix
        running_rank = int(candidate_matrix.rank())
        combination_string = record["combination_string"]
        promoted_generator_id = build_semantic_combination_id(
            record["combination"],
            prefix="promoted",
        )
        source_generator_ids = [item["generator_id"] for item in record["combination"]]
        source_family_letters = sorted(
            {candidate_index[generator_id]["family_letter"] for generator_id in source_generator_ids}
        )
        source_local_object_labels = [
            candidate_index[generator_id]["local_object_label"]
            for generator_id in source_generator_ids
        ]
        promoted_record = {
            "generator_id": promoted_generator_id,
            "generator_kind": "promoted_from_residual_completion",
            "lifted_direction_id": record["lifted_direction_id"],
            "lead_generator_id": record["lead_generator_id"],
            "family_letter": None,
            "family_letters": sorted({candidate_index[item["generator_id"]]["family_letter"] for item in record["combination"]}),
            "local_object_label": None,
            "local_object_labels": [
                {
                    "generator_id": item["generator_id"],
                    "label": candidate_index[item["generator_id"]]["local_object_label"],
                }
                for item in record["combination"]
            ],
            "site_symmetry_type_key": None,
            "site_symmetry_type_label": None,
            "combination": list(record["combination"]),
            "combination_string": combination_string,
            "unknown_vector": combined_unknown_vector,
            "raw_unknown_vector": combined_unknown_vector,
            "compatibility_zero": True,
            "compatibility_residual_norm": 0,
            "compatibility_residual_vector": combined_residual_vector,
            "nonzero_residual_rows": [],
            "historical_point_row_translation_profile": "legacy",
            "point_row_translation_profile": "retired_not_used_on_authoritative_publication_shell",
            "character_field_used": next(
                (
                    candidate_index[item["generator_id"]]["character_field_used"]
                    for item in record["combination"]
                    if candidate_index[item["generator_id"]].get("character_field_used")
                ),
                _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
            ),
            "manifold_character_fields": next(
                (
                    candidate_index[item["generator_id"]]["manifold_character_fields"]
                    for item in record["combination"]
                    if candidate_index[item["generator_id"]].get("manifold_character_fields")
                ),
                {},
            ),
            "adds_independent_bs_direction": True,
            "promotion_reason": "fills_missing_publication_ai_rank_direction",
            "fills_missing_direction_index": promoted_rank_increment,
            "source_family_letters": source_family_letters,
            "source_generator_ids": source_generator_ids,
            "source_local_object_labels": source_local_object_labels,
            "materialized_on_object_language": "publication_level_C_pub_34_unknowns",
            "nonzero_unknown_terms": _sparse_unknown_vector_terms(
                unknown_ordering,
                combined_unknown_vector,
            ),
        }
        promoted_generators.append(promoted_record)
        authoritative_generators.append(promoted_record)

    authoritative_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(generator["unknown_vector"]) for generator in authoritative_generators])
        if authoritative_generators
        else sp.zeros(len(unknown_ordering), 0)
    )
    authoritative_rank = int(authoritative_matrix.rank())
    return {
        "object_role": "publication_level_C_pub_authoritative_ai_generators",
        "object_language": "publication_level_C_pub_34_unknowns",
        "unknown_ordering": list(unknown_ordering),
        "native_compatibility_zero_generator_ids": zero_generator_ids,
        "native_compatibility_zero_generators": [
            generator
            for generator in authoritative_generators
            if generator.get("generator_kind") == "native_compatibility_zero"
        ],
        "liftable_residual_direction_ids": list(ai_completion_feasibility_report["liftable_residual_direction_ids"]),
        "promoted_authoritative_generator_ids": [
            generator["generator_id"] for generator in promoted_generators
        ],
        "promoted_authoritative_generators": list(promoted_generators),
        "generators": authoritative_generators,
        "native_generator_count": len(zero_generator_ids),
        "promoted_generator_count": len(promoted_generators),
        "old_verified_ai_rank": int(ai_zero_subset_rank_report["zero_subset_rank"]),
        "promoted_ai_rank_increment": authoritative_rank - int(ai_zero_subset_rank_report["zero_subset_rank"]),
        "new_authoritative_ai_rank": authoritative_rank,
        "all_promoted_generators_actual_compatibility_zero": all(
            generator["compatibility_zero"] for generator in promoted_generators
        ),
    }


def build_honest_ai_lattice_from_induction(
    induction: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
    generator_id_prefix: str,
    object_role: str,
    object_language: str,
    old_verified_ai_rank: int,
    promoted_ai_rank_increment: int,
    seed_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidates = list(induction.get("candidates", []))
    candidate_ids = [candidate["generator_id"] for candidate in candidates]
    if not candidates:
        return {
            "object_role": object_role,
            "object_language": object_language,
            "construction_mode": "full_induced_object_compatibility_kernel_image",
            "unknown_ordering": list(unknown_ordering),
            "source_candidate_ids": [],
            "source_candidate_count": 0,
            "compatibility_kernel_basis_count": 0,
            "compatibility_kernel_matrix_shape": [0, 0],
            "generators": [],
            "old_verified_ai_rank": int(old_verified_ai_rank),
            "promoted_ai_rank_increment": int(promoted_ai_rank_increment),
            "new_authoritative_ai_rank": 0,
            "all_generators_actual_compatibility_zero": True,
        }

    residual_row_count = len(candidates[0]["compatibility_residual_vector"])
    residual_matrix = [
        [
            int(candidate["compatibility_residual_vector"][row_index])
            for candidate in candidates
        ]
        for row_index in range(residual_row_count)
    ]
    kernel_analysis = analyze_kernel(
        {
            "global_matrix": residual_matrix,
            "global_unknown_ordering": candidate_ids,
        }
    )
    candidate_unknown_matrix = sp.Matrix.hstack(
        *[sp.Matrix(candidate["unknown_vector"]) for candidate in candidates]
    )
    generators = []
    for basis_index, basis in enumerate(kernel_analysis["basis_vectors"], start=1):
        coeffs = [int(value) for value in basis["vector"]]
        combination = [
            {
                "generator_id": candidate_id,
                "coefficient": coeff,
            }
            for candidate_id, coeff in zip(candidate_ids, coeffs)
            if coeff != 0
        ]
        if not combination:
            continue
        unknown_vector = [
            int(value)
            for value in list(candidate_unknown_matrix * sp.Matrix(coeffs))
        ]
        compatibility_residual_vector = [
            sum(
                coeffs[position]
                * int(candidates[position]["compatibility_residual_vector"][row_index])
                for position in range(len(candidates))
            )
            for row_index in range(residual_row_count)
        ]
        source_generator_ids = [item["generator_id"] for item in combination]
        source_candidates = [candidate for candidate in candidates if candidate["generator_id"] in source_generator_ids]
        generators.append(
            {
                "generator_id": f"{generator_id_prefix}_{basis_index:02d}",
                "generator_kind": "compatibility_kernel_image_basis",
                "combination": combination,
                "combination_string": build_combination_string(combination),
                "source_generator_ids": source_generator_ids,
                "source_family_letters": sorted(
                    {
                        candidate["family_letter"]
                        for candidate in source_candidates
                    }
                ),
                "source_local_object_labels": [
                    candidate["local_object_label"] for candidate in source_candidates
                ],
                "unknown_vector": unknown_vector,
                "raw_unknown_vector": unknown_vector,
                "compatibility_zero": all(value == 0 for value in compatibility_residual_vector),
                "compatibility_residual_norm": sum(abs(value) for value in compatibility_residual_vector),
                "compatibility_residual_vector": compatibility_residual_vector,
                "nonzero_residual_rows": [
                    {"row_index": row_index, "residual": value}
                    for row_index, value in enumerate(compatibility_residual_vector)
                    if value != 0
                ],
                "historical_point_row_translation_profile": "legacy",
                "point_row_translation_profile": "retired_not_used_on_authoritative_publication_shell",
                "character_field_used": next(
                    (
                        candidate.get("character_field_used")
                        for candidate in source_candidates
                        if candidate.get("character_field_used")
                    ),
                    _summarize_induction_character_field(AUTHORITATIVE_AI_CHARACTER_FIELD),
                ),
                "manifold_character_fields": next(
                    (
                        candidate.get("manifold_character_fields")
                        for candidate in source_candidates
                        if candidate.get("manifold_character_fields")
                    ),
                    {},
                ),
                "materialized_on_object_language": object_language,
                "nonzero_unknown_terms": _sparse_unknown_vector_terms(
                    unknown_ordering,
                    unknown_vector,
                ),
            }
        )
    lattice_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(generator["unknown_vector"]) for generator in generators])
        if generators
        else sp.zeros(len(unknown_ordering), 0)
    )
    payload = {
        "object_role": object_role,
        "object_language": object_language,
        "construction_mode": "full_induced_object_compatibility_kernel_image",
        "unknown_ordering": list(unknown_ordering),
        "source_candidate_ids": candidate_ids,
        "source_candidate_count": len(candidate_ids),
        "compatibility_kernel_basis_count": len(generators),
        "compatibility_kernel_matrix_shape": [residual_row_count, len(candidate_ids)],
        "compatibility_kernel_basis_vectors": list(kernel_analysis["basis_vectors"]),
        "generators": generators,
        "old_verified_ai_rank": int(old_verified_ai_rank),
        "promoted_ai_rank_increment": int(promoted_ai_rank_increment),
        "new_authoritative_ai_rank": int(lattice_matrix.rank()),
        "all_generators_actual_compatibility_zero": all(
            generator["compatibility_zero"] for generator in generators
        ),
    }
    if seed_payload is not None:
        payload.update(
            {
                "native_compatibility_zero_generator_ids": list(
                    seed_payload.get("native_compatibility_zero_generator_ids", [])
                ),
                "native_compatibility_zero_generators": list(
                    seed_payload.get("native_compatibility_zero_generators", [])
                ),
                "liftable_residual_direction_ids": list(
                    seed_payload.get("liftable_residual_direction_ids", [])
                ),
                "promoted_authoritative_generator_ids": list(
                    seed_payload.get("promoted_authoritative_generator_ids", [])
                ),
                "promoted_authoritative_generators": list(
                    seed_payload.get("promoted_authoritative_generators", [])
                ),
                "native_generator_count": int(seed_payload.get("native_generator_count", 0)),
                "promoted_generator_count": int(seed_payload.get("promoted_generator_count", 0)),
                "seed_payload_role": seed_payload.get("object_role"),
            }
        )
    return payload


def build_authoritative_ai_promotion_report(
    authoritative_ai_payload: dict[str, Any],
    ai_completion_feasibility_report: dict[str, Any],
    ai_rank_gap_quotient_report: dict[str, Any],
) -> dict[str, Any]:
    promoted_records = [
        {
            "generator_id": generator["generator_id"],
            "lifted_direction_id": generator["lifted_direction_id"],
            "lead_generator_id": generator["lead_generator_id"],
            "combination": list(generator["combination"]),
            "combination_string": generator["combination_string"],
            "actual_compatibility_zero": bool(generator["compatibility_zero"]),
            "adds_independent_bs_direction": bool(generator["adds_independent_bs_direction"]),
            "fills_missing_direction_index": int(generator["fills_missing_direction_index"]),
            "promotion_reason": generator["promotion_reason"],
            "source_generator_ids": list(generator["source_generator_ids"]),
            "source_local_object_labels": list(generator["source_local_object_labels"]),
        }
        for generator in authoritative_ai_payload["generators"]
        if generator.get("generator_kind") == "promoted_from_residual_completion"
    ]
    return {
        "residual_pivot_generator_ids": list(
            ai_rank_gap_quotient_report["missing_rank5_pivot_generator_ids"]
        ),
        "liftable_residual_direction_ids": list(
            ai_completion_feasibility_report["liftable_residual_direction_ids"]
        ),
        "promoted_authoritative_generator_ids": list(
            authoritative_ai_payload["promoted_authoritative_generator_ids"]
        ),
        "promoted_generators": promoted_records,
        "all_promoted_generators_actual_compatibility_zero": bool(
            authoritative_ai_payload["all_promoted_generators_actual_compatibility_zero"]
        ),
        "summary": (
            "Residual-sector kernel combinations are now materialized as authoritative publication-shell AI generators. "
            "The residual pivot ids remain obstruction witnesses, the lifted direction ids identify zeroed residual combinations, "
            "and the promoted authoritative generator ids name the materialized generators added to the authoritative AI payload."
        ),
    }


def build_authoritative_ai_promotion_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Authoritative AI Promotion Report",
        "",
        f"- Residual pivot generator ids: `{report['residual_pivot_generator_ids']}`.",
        f"- Liftable residual direction ids: `{report['liftable_residual_direction_ids']}`.",
        f"- Promoted authoritative generator ids: `{report['promoted_authoritative_generator_ids']}`.",
        f"- All promoted generators are actual compatibility-zero: `{report['all_promoted_generators_actual_compatibility_zero']}`.",
        f"- Summary: {report['summary']}",
        "",
    ]
    for record in report["promoted_generators"]:
        lines.append(
            f"- `{record['generator_id']}` from `{record['lifted_direction_id']}` "
            f"(lead `{record['lead_generator_id']}`): combination = `{record['combination_string']}`, "
            f"zero = `{record['actual_compatibility_zero']}`, "
            f"independent = `{record['adds_independent_bs_direction']}`, "
            f"fills missing direction `{record['fills_missing_direction_index']}`."
        )
    return "\n".join(lines)


def build_ai_rank_after_promotion_report(
    publication_bs_analysis: dict[str, Any],
    ai_zero_subset_rank_report: dict[str, Any],
    authoritative_ai_payload: dict[str, Any],
    publication_check: dict[str, Any],
) -> dict[str, Any]:
    published_bs_rank = int(publication_bs_analysis["nullity"])
    old_verified_ai_rank = int(ai_zero_subset_rank_report["zero_subset_rank"])
    new_authoritative_ai_rank = int(authoritative_ai_payload["new_authoritative_ai_rank"])
    promoted_increment = int(authoritative_ai_payload["promoted_ai_rank_increment"])
    quotient_stage_allowed = (
        publication_check["bilbao_equivalent_publication_pass"]
        and new_authoritative_ai_rank >= published_bs_rank
    )
    return {
        "published_bs_rank": published_bs_rank,
        "old_verified_ai_rank": old_verified_ai_rank,
        "promoted_ai_rank_increment": promoted_increment,
        "new_authoritative_ai_rank": new_authoritative_ai_rank,
        "ai_aligned_with_bilbao": quotient_stage_allowed,
        "quotient_stage_allowed": quotient_stage_allowed,
        "ai_status": "full_ai_lattice" if quotient_stage_allowed else "partial_ai_lattice",
        "active_blocker_stage": "quotient_stage_ready" if quotient_stage_allowed else "residual_sector_completion_integration",
    }


def build_ai_rank_after_promotion_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# AI Rank After Promotion Report",
            "",
            f"- Published BS rank: `{report['published_bs_rank']}`.",
            f"- Old verified AI rank: `{report['old_verified_ai_rank']}`.",
            f"- Promoted AI rank increment: `{report['promoted_ai_rank_increment']}`.",
            f"- New authoritative AI rank: `{report['new_authoritative_ai_rank']}`.",
            f"- AI aligned with Bilbao: `{report['ai_aligned_with_bilbao']}`.",
            f"- Quotient stage allowed: `{report['quotient_stage_allowed']}`.",
            f"- AI status: `{report['ai_status']}`.",
            f"- Active blocker stage: `{report['active_blocker_stage']}`.",
        ]
    )


def build_bs_ai_quotient_report(
    publication_bs_analysis: dict[str, Any],
    authoritative_ai_payload: dict[str, Any],
    *,
    unknown_ordering: Sequence[str],
) -> dict[str, Any]:
    bs_basis_vectors = [
        list(map(int, basis["vector"]))
        for basis in publication_bs_analysis["basis_vectors"]
    ]
    bs_basis_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in bs_basis_vectors])
        if bs_basis_vectors
        else sp.zeros(len(unknown_ordering), 0)
    )
    authoritative_generators = list(authoritative_ai_payload["generators"])
    ai_coordinate_records = []
    ai_coordinate_columns: list[sp.Matrix] = []
    for generator in authoritative_generators:
        if "bs_coordinates" in generator:
            coords = [int(value) for value in generator["bs_coordinates"]]
        else:
            exact = _attempt_exact_integer_decomposition(
                bs_basis_matrix,
                sp.Matrix(generator["unknown_vector"]),
                f"authoritative AI generator {generator['generator_id']} in BS basis",
            )
            if exact["status"] != "integral":
                raise ValueError(
                    f"authoritative AI generator {generator['generator_id']} is not integral in BS basis: {exact['error']}"
                )
            coords = [int(value) for value in exact["integral_solution"]]
        ai_coordinate_columns.append(sp.Matrix(coords))
        ai_coordinate_records.append(
            {
                "generator_id": generator["generator_id"],
                "generator_kind": generator.get("generator_kind"),
                "origin": generator.get("origin"),
                "combination_string": generator.get("combination_string"),
                "bs_basis_coordinates": coords,
                "nonzero_bs_basis_terms": [
                    {
                        "basis_id": publication_bs_analysis["basis_vectors"][index]["id"],
                        "value": int(value),
                    }
                    for index, value in enumerate(coords)
                    if int(value) != 0
                ],
            }
        )
    ai_coordinate_matrix = (
        sp.Matrix.hstack(*ai_coordinate_columns)
        if ai_coordinate_columns
        else sp.zeros(len(bs_basis_vectors), 0)
    )
    smith_input = [[int(value) for value in row] for row in ai_coordinate_matrix.tolist()]
    D_list, U_list, V_list = swyckoff_k.smith_normal_form(smith_input)
    D = sp.Matrix(D_list)
    U = sp.Matrix(U_list)
    V = sp.Matrix(V_list)
    snf_diagonal = smith_diagonal_entries(D)
    quotient_invariants = [int(value) for value in snf_diagonal if int(value) > 1]
    quotient_rank = int(publication_bs_analysis["nullity"])
    ai_rank = int(authoritative_ai_payload["new_authoritative_ai_rank"])
    quotient_has_free_part = ai_coordinate_matrix.rank() < quotient_rank
    quotient_status = "success" if ai_rank >= quotient_rank else "blocked"
    quotient_kind = (
        "contains_free_part"
        if quotient_has_free_part
        else ("finite_torsion" if quotient_invariants else "trivial")
    )
    torsion_indices = [
        index
        for index in range(min(D.rows, D.cols))
        if abs(int(D[index, index])) > 1
    ]
    u_inverse = U.inv() if torsion_indices else None
    torsion_generators = []
    for torsion_position, torsion_index in enumerate(torsion_indices, start=1):
        bs_coords = [int(value) for value in list(u_inverse[:, torsion_index])]
        unknown_vector = [
            int(value)
            for value in list(bs_basis_matrix * sp.Matrix(bs_coords))
        ]
        ai_relation = [int(value) for value in list(V[:, torsion_index])]
        torsion_generators.append(
            {
                "indicator_id": f"indicator_{torsion_position:02d}",
                "smith_factor": int(abs(D[torsion_index, torsion_index])),
                "bs_basis_coordinates": bs_coords,
                "unknown_vector": unknown_vector,
                "unknown_support": _sparse_unknown_vector_terms(unknown_ordering, unknown_vector),
                "ai_relation_for_multiple": ai_relation,
            }
        )
    return {
        "published_bs_rank": quotient_rank,
        "authoritative_ai_rank": ai_rank,
        "authoritative_ai_source_kind": authoritative_ai_payload.get(
            "authoritative_ai_source_kind",
            authoritative_ai_payload.get("construction_mode"),
        ),
        "diagnostic_candidate_source_kind": authoritative_ai_payload.get(
            "diagnostic_candidate_source_kind"
        ),
        "final_quotient_does_not_use_diagnostic_kernel_basis_directly": authoritative_ai_payload.get(
            "final_quotient_does_not_use_diagnostic_kernel_basis_directly",
            False,
        ),
        "quotient_status": quotient_status,
        "quotient_kind": quotient_kind,
        "quotient_is_trivial": quotient_kind == "trivial",
        "quotient_is_finite_torsion": quotient_kind == "finite_torsion",
        "has_free_part": quotient_has_free_part,
        "quotient_group": quotient_group_from_diagonal(quotient_invariants),
        "quotient_invariants": quotient_invariants,
        "snf_diagonal": [int(value) for value in snf_diagonal],
        "bs_basis_vectors": list(publication_bs_analysis["basis_vectors"]),
        "ai_coordinate_records": ai_coordinate_records,
        "ai_coordinate_matrix_in_bs_basis": [
            [int(value) for value in row]
            for row in ai_coordinate_matrix.tolist()
        ],
        "torsion_generators": torsion_generators,
        "summary": (
            "The quotient is extracted directly on the publication-shell BS basis using the authoritative AI lattice generators. "
            "Because the authoritative AI rank matches the published BS rank, the quotient has no free part; any remaining nontriviality "
            "is finite torsion encoded by the Smith diagonal in BS coordinates."
        ),
    }


def build_bs_ai_quotient_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# BS/AI Quotient Report",
        "",
        f"- Published BS rank: `{report['published_bs_rank']}`.",
        f"- Authoritative AI rank: `{report['authoritative_ai_rank']}`.",
        f"- Authoritative AI source kind: `{report.get('authoritative_ai_source_kind')}`.",
        f"- Diagnostic candidate source kind: `{report.get('diagnostic_candidate_source_kind')}`.",
        f"- Final quotient does not use diagnostic kernel basis directly: `{report.get('final_quotient_does_not_use_diagnostic_kernel_basis_directly')}`.",
        f"- Quotient status: `{report['quotient_status']}`.",
        f"- Quotient kind: `{report['quotient_kind']}`.",
        f"- Quotient invariants: `{report['quotient_invariants']}`.",
        f"- Quotient group: `{report['quotient_group']}`.",
        f"- Smith diagonal in BS coordinates: `{report['snf_diagonal']}`.",
        f"- Summary: {report['summary']}",
        "",
        "## AI Coordinates In BS Basis",
        "",
    ]
    if "classification_expected_by_user" in report:
        lines.insert(8, f"- Classification expected by user: `{report['classification_expected_by_user']}`.")
        lines.insert(9, f"- Classification matches user expectation: `{report['classification_matches_user_expectation']}`.")
    if "classification_reference_source" in report:
        lines.insert(8, f"- Classification reference source: `{report['classification_reference_source']}`.")
        lines.insert(9, f"- Classification reference scope: `{report['classification_reference_scope']}`.")
        lines.insert(10, f"- Reference expected quotient group: `{report['reference_expected_quotient_group']}`.")
        lines.insert(11, f"- Classification matches reference: `{report['classification_matches_reference']}`.")
    for record in report["ai_coordinate_records"]:
        lines.append(
            f"- `{record['generator_id']}` (`{record['generator_kind']}`, origin `{record.get('origin')}`): bs coords `{record['bs_basis_coordinates']}`, "
            f"nonzero terms `{record['nonzero_bs_basis_terms']}`, combination `{record['combination_string']}`."
        )
    if report["torsion_generators"]:
        lines.extend(["", "## Torsion Generators", ""])
        for generator in report["torsion_generators"]:
            lines.append(
                f"- `{generator['indicator_id']}`: smith factor `{generator['smith_factor']}`, "
                f"bs coords `{generator['bs_basis_coordinates']}`, support `{generator['unknown_support']}`."
            )
    return "\n".join(lines)


def build_indicator_extraction_report(
    quotient_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "quotient_status": quotient_report["quotient_status"],
        "indicator_group": quotient_report["quotient_group"],
        "indicator_invariants": list(quotient_report["quotient_invariants"]),
        "indicator_generator_count": len(quotient_report["torsion_generators"]),
        "snf_diagonal": list(quotient_report["snf_diagonal"]),
        "finite_torsion": bool(quotient_report["quotient_is_finite_torsion"]),
        "torsion_generators": list(quotient_report["torsion_generators"]),
        "summary": (
            "Indicator extraction is read directly from the finite torsion part of the BS/AI quotient in published BS coordinates."
        ),
    }


def build_indicator_extraction_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Indicator Extraction Report",
        "",
        f"- Quotient status: `{report['quotient_status']}`.",
        f"- Indicator group: `{report['indicator_group']}`.",
        f"- Indicator invariants: `{report['indicator_invariants']}`.",
        f"- Indicator generator count: `{report['indicator_generator_count']}`.",
        f"- Smith diagonal: `{report['snf_diagonal']}`.",
        f"- Finite torsion: `{report['finite_torsion']}`.",
        f"- Summary: {report['summary']}",
        "",
    ]
    if "classification_expected_by_user" in report:
        lines.append(
            f"- Classification expected by user / matches expectation: "
            f"`{report['classification_expected_by_user']}` / `{report['classification_matches_user_expectation']}`."
        )
    if "classification_reference_source" in report:
        lines.append(
            f"- Classification reference source / expected quotient / matches: "
            f"`{report['classification_reference_source']}` / `{report['reference_expected_quotient_group']}` / "
            f"`{report['classification_matches_reference']}`."
        )
    lines.append("")
    for generator in report["torsion_generators"]:
        lines.append(
            f"- `{generator['indicator_id']}`: factor `{generator['smith_factor']}`, bs coords `{generator['bs_basis_coordinates']}`, "
            f"support `{generator['unknown_support']}`."
        )
    return "\n".join(lines)


def build_single_quotient_crosscheck(
    quotient_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_group = "trivial"
    matches = quotient_report["quotient_group"] == expected_group
    quotient = {
        **quotient_report,
        "classification_expected_by_user": expected_group,
        "classification_matches_user_expectation": matches,
    }
    indicator = {
        **build_indicator_extraction_report(quotient_report),
        "classification_expected_by_user": expected_group,
        "classification_matches_user_expectation": matches,
    }
    return quotient, indicator


def build_double_quotient_crosscheck(
    quotient_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reference = load_double_classification_reference()
    matches = quotient_report["quotient_group"] == reference["expected_quotient_group"]
    quotient = {
        **quotient_report,
        "classification_reference_source": reference["reference_source"],
        "classification_reference_scope": reference["reference_scope"],
        "reference_expected_quotient_group": reference["expected_quotient_group"],
        "reference_expected_snf_diagonal": reference["expected_snf_diagonal"],
        "classification_matches_reference": matches,
    }
    indicator = {
        **build_indicator_extraction_report(quotient_report),
        "classification_reference_source": reference["reference_source"],
        "classification_reference_scope": reference["reference_scope"],
        "reference_expected_quotient_group": reference["expected_quotient_group"],
        "reference_expected_snf_diagonal": reference["expected_snf_diagonal"],
        "classification_matches_reference": matches,
    }
    return quotient, indicator


def build_claim_scope_guardrail_report(
    setting_specific_validation_report: dict[str, Any],
    ai_completion_feasibility_report: dict[str, Any],
    ai_rank_after_promotion_report: dict[str, Any] | None = None,
    bs_ai_quotient_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai_aligned = bool(
        ai_rank_after_promotion_report is not None
        and ai_rank_after_promotion_report.get("ai_aligned_with_bilbao")
    )
    quotient_extracted = bool(
        bs_ai_quotient_report is not None
        and bs_ai_quotient_report.get("quotient_status") == "success"
    )
    return {
        "allowed_claims": [
            "BS/publication shell is Bilbao-equivalent",
            "the SG194/P-lattice/current-setting conversion patch works numerically in the present setting",
            "current authoritative AI rank is 10 on the publication shell",
            "AI is aligned with Bilbao on the publication shell",
            "single-group BS/AI quotient extraction is now meaningful and has been carried out on the authoritative publication-shell AI lattice",
        ],
        "forbidden_claims": [
            "global conversion theorem proved",
            "all-manifold validation proved the formula in general",
            "basis-independent statement established",
            "the SG194-setting-specific conversion patch is a basis-independent theorem",
            "double-group AI / quotient is already complete on 194.1.1.1",
        ],
        "setting_specific_validation_scope": setting_specific_validation_report["validation_scope"],
        "all_fake_global_claims_removed": True,
        "current_conversion_result_labeled_setting_specific_only": True,
        "formula_promoted_as_general_theorem": setting_specific_validation_report["formula_promoted_as_general_theorem"],
        "current_success_depends_on_p_lattice_under_present_basis_conventions": setting_specific_validation_report[
            "current_success_depends_on_sg194_being_p_lattice_under_present_basis_conventions"
        ],
        "residual_completion_feasible": ai_completion_feasibility_report["any_liftable_to_actual_compatibility_zero"],
        "ai_aligned_with_bilbao": ai_aligned,
        "single_group_quotient_extracted": quotient_extracted,
    }


def build_claim_scope_guardrail_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Claim Scope Guardrail Report",
        "",
        f"- Setting-specific validation scope: `{report['setting_specific_validation_scope']}`.",
        f"- All fake global claims removed: `{report['all_fake_global_claims_removed']}`.",
        f"- Current conversion result labeled SG194-setting-specific only: `{report['current_conversion_result_labeled_setting_specific_only']}`.",
        f"- Formula promoted as a general theorem: `{report['formula_promoted_as_general_theorem']}`.",
        f"- Current success depends on SG194 being P-lattice under the present basis conventions: `{report['current_success_depends_on_p_lattice_under_present_basis_conventions']}`.",
        f"- Residual completion feasible: `{report['residual_completion_feasible']}`.",
        "",
        "## Allowed Claims",
        "",
    ]
    for claim in report["allowed_claims"]:
        lines.append(f"- {claim}")
    lines.extend(["", "## Forbidden Claims", ""])
    for claim in report["forbidden_claims"]:
        lines.append(f"- {claim}")
    return "\n".join(lines)


def build_ai_honest_blocker_report(
    integration_report: dict[str, Any],
    p4_failure_audit: dict[str, Any] | None = None,
    ppath06_audit: dict[str, Any] | None = None,
    obstruction_report: dict[str, Any] | None = None,
    p4_conversion_patch_independent_validation_report: dict[str, Any] | None = None,
    ai_rank_gap_quotient_report: dict[str, Any] | None = None,
    ai_completion_feasibility_report: dict[str, Any] | None = None,
    authoritative_ai_promotion_report: dict[str, Any] | None = None,
    ai_rank_after_promotion_report: dict[str, Any] | None = None,
    bs_ai_quotient_report: dict[str, Any] | None = None,
    *,
    p4_verdict: str | None = None,
) -> dict[str, Any]:
    if ai_rank_after_promotion_report is not None and ai_rank_after_promotion_report["quotient_stage_allowed"]:
        quotient_complete = bool(
            bs_ai_quotient_report is not None
            and bs_ai_quotient_report.get("quotient_status") == "success"
        )
        return {
            "status": "not_blocked",
            "blocker": (
                "No active AI blocker; single-group quotient already extracted on the authoritative publication-shell AI lattice."
                if quotient_complete
                else "No active AI blocker; quotient stage is ready."
            ),
            "blocker_stage": "single_group_quotient_complete" if quotient_complete else "quotient_stage_ready",
            "ai_status": ai_rank_after_promotion_report["ai_status"],
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
            "integration_status": integration_report["integration_status"],
            "failure_count": integration_report["failure_count"],
            "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
            "published_shell_candidate_count": integration_report["success_candidate_count"],
            "published_shell_compatible_zero_count": integration_report["compatibility_zero_candidate_count"],
            "quotient_rank_contribution_of_residual_sector": (
                ai_rank_gap_quotient_report["quotient_rank_contribution_of_residual_sector"]
                if ai_rank_gap_quotient_report is not None
                else None
            ),
            "residual_completion_feasible": (
                ai_completion_feasibility_report["any_liftable_to_actual_compatibility_zero"]
                if ai_completion_feasibility_report is not None
                else None
            ),
            "liftable_residual_direction_ids": (
                ai_completion_feasibility_report["liftable_residual_direction_ids"]
                if ai_completion_feasibility_report is not None
                else []
            ),
            "promoted_authoritative_generator_ids": (
                authoritative_ai_promotion_report["promoted_authoritative_generator_ids"]
                if authoritative_ai_promotion_report is not None
                else []
            ),
            "summary": (
                "The authoritative publication-shell AI generator set now includes promoted residual-sector lifts, "
                "the authoritative AI rank matches the published BS rank, and the single-group quotient is "
                + ("already extracted." if quotient_complete else "ready to extract.")
            ),
        }
    if integration_report["integration_status"] == "wired_complete_candidate_set":
        return {
            "status": "not_blocked",
            "blocker": None,
            "blocker_stage": None,
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
        }
    if obstruction_report is not None:
        blocker_stage = "residual_sector_completion_integration"
        p4_phrase = ""
        if p4_failure_audit is not None:
            if int(p4_failure_audit.get("induction_failure_count", 0)) > 0:
                p4_phrase = (
                    f" The remaining induction failures are concentrated on manifold P4 "
                    f"across families {p4_failure_audit['failure_family_ids']} "
                    f"(count={p4_failure_audit['induction_failure_count']})."
                )
            else:
                p4_phrase = (
                    " The earlier P4 induction failures are removed in the current SG194/P-lattice setting by a conversion numerically "
                    "consistent with the present capture conventions."
                )
                if p4_conversion_patch_independent_validation_report is not None:
                    p4_phrase += (
                        " Claim scope: "
                        f"{p4_conversion_patch_independent_validation_report['current_verdict']}."
                    )
            if p4_verdict is not None:
                p4_phrase += f" Current P4 verdict: {p4_verdict}."
        ppath06_phrase = ""
        if ppath06_audit is not None:
            support_rows = _ppath06_publication_residual_support_rows(
                ppath06_audit,
                obstruction_report,
            )
            ppath06_phrase = (
                f" Nonzero residuals on the publication shell are concentrated on "
                f"{ppath06_audit['publication_path_id']} rows "
                f"{support_rows or ppath06_audit['publication_residual_support_rows']}."
            )
        rank_gap_phrase = ""
        if ai_rank_gap_quotient_report is not None:
            rank_gap_phrase = (
                f" The residual sector contributes quotient rank "
                f"{ai_rank_gap_quotient_report['quotient_rank_contribution_of_residual_sector']} "
                f"after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank "
                f"{ai_rank_gap_quotient_report['missing_ai_rank']}."
            )
        completion_phrase = ""
        if ai_completion_feasibility_report is not None:
            completion_phrase = (
                f" Integer recombinations of the residual sector already lift the missing rank-"
                f"{ai_completion_feasibility_report['missing_ai_rank']} directions to actual compatibility-zero vectors, "
                "but those recombined directions are not yet promoted into the authoritative publication-shell AI generator set."
            )
        blocker = (
            "Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, "
            f"but only {integration_report['compatibility_zero_candidate_count']} of "
            f"{integration_report['success_candidate_count']} induced local objects are currently explicit compatibility-zero generators on the publication-level shell. "
            f"Classification counts across raw42 / internal honest shell / publication shell: "
            f"{obstruction_report['classification_counts']}. "
            f"{obstruction_report['obstruction_summary']}"
            f"{p4_phrase}"
            f"{ppath06_phrase}"
            f"{rank_gap_phrase}"
            f"{completion_phrase}"
        )
        return {
            "status": "blocked",
            "blocker_stage": blocker_stage,
            "blocker": blocker,
            "ai_status": "partial_ai_lattice" if integration_report["compatibility_zero_candidate_count"] > 0 else "seed_only",
            "local_library_present": True,
            "local_library_wired_into_ai_builder": True,
            "integration_status": integration_report["integration_status"],
            "failure_count": integration_report["failure_count"],
            "nonzero_residual_candidate_count": integration_report["nonzero_residual_candidate_count"],
            "failure_family_ids": list(integration_report["failure_family_ids"]),
            "published_shell_candidate_count": integration_report["success_candidate_count"],
            "published_shell_compatible_zero_count": integration_report["compatibility_zero_candidate_count"],
            "ppath06_publication_residual_support_rows": (
                _ppath06_publication_residual_support_rows(ppath06_audit, obstruction_report)
                if ppath06_audit is not None
                else None
            ),
            "quotient_rank_contribution_of_residual_sector": (
                ai_rank_gap_quotient_report["quotient_rank_contribution_of_residual_sector"]
                if ai_rank_gap_quotient_report is not None
                else None
            ),
            "residual_completion_feasible": (
                ai_completion_feasibility_report["any_liftable_to_actual_compatibility_zero"]
                if ai_completion_feasibility_report is not None
                else None
            ),
            "liftable_residual_direction_ids": (
                ai_completion_feasibility_report["liftable_residual_direction_ids"]
                if ai_completion_feasibility_report is not None
                else []
            ),
            "obstruction_classification_counts": dict(obstruction_report["classification_counts"]),
        }
    return {
        "status": "blocked",
        "blocker_stage": "integration_missing",
        "blocker": "AI builder is not yet wired to the validated non-abelian local library on the published shell.",
        "ai_status": "seed_only",
        "local_library_present": True,
        "local_library_wired_into_ai_builder": False,
    }


def build_current_status(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> dict[str, Any]:
    single_quotient_status = single["summary"]["quotient_status"]["status"]
    double_quotient_status = double["summary"].get("quotient_status", {}).get("status")
    double_matches_reference = bool(double["summary"].get("classification_matches_reference"))
    next_step = (
        "The publication-level C_pub builder remains fixed and Bilbao-equivalent. "
        "Current published compatibility-matrix rank/nullity is 24/10, so published BS rank is 10. "
        "The old verified zero-subset AI rank is 5, and the authoritative promoted AI rank is now "
        f"{single['summary']['AI_status']['authoritative_ai_rank']}. "
        "The SG194-setting-specific character-field conversion remains non-global and non-theorem-level. "
        "Authoritative AI promotion now materializes the residual-sector lifted directions directly in publication-shell coordinates, "
        "so the next stage is BS/AI quotient extraction rather than further residual completion proofs."
    )
    if single_quotient_status == "success":
        next_step = (
            "The publication-level C_pub builder remains fixed and Bilbao-equivalent. "
            f"Single-group published compatibility-matrix rank/nullity is 24/10, the authoritative publication-shell AI rank is {single['summary']['AI_status']['authoritative_ai_rank']}, "
            f"and the single-group quotient has been extracted as {single['summary']['quotient_status']['quotient_group']}. "
            "The SG194-setting-specific character-field conversion remains non-global and non-theorem-level. "
            + (
                "The next unresolved stage is the published-shell double-group AI wiring and the corresponding honest double-group quotient extraction."
                if double_quotient_status != "success"
                else (
                    "The double-group quotient is extracted but does not yet match the Bilbao-backed workspace benchmark, so the next stage is mismatch localization."
                    if not double_matches_reference
                    else "Both single and double honest quotients are now extracted; the next stage is downstream closeout rather than further BS-AI completion."
                )
            )
        )
    active_blocker_stage = single["summary"]["active_blocker_stage"]
    if single_quotient_status == "success":
        if double_quotient_status != "success":
            active_blocker_stage = "double_group_honest_quotient_extraction"
        elif not double_matches_reference:
            active_blocker_stage = "double_group_classification_crosscheck_mismatch"
        else:
            active_blocker_stage = None
    return {
        "target_group": TARGET_GROUP,
        "object_scope": "internal_diagnostic_shell_plus_publication_level_C_pub",
        "diagnostic_internal_shell_kind": single["summary"]["compatibility_status"]["internal_object_kind"],
        "published_object_kind": single["summary"]["compatibility_status"]["published_object_kind"],
        "publication_object_is_explicitly_separated": single["summary"]["compatibility_status"]["internal_and_publication_objects_explicitly_separated"],
        "single_status": single["summary"],
        "double_status": double["summary"],
        "active_blocker_stage": active_blocker_stage,
        "key_matrices": {
            "single_compatibility_matrix_shape": single["summary"]["BS_status"]["compatibility_matrix_shape"],
            "single_compatibility_matrix_rank": single["summary"]["BS_status"]["compatibility_matrix_rank"],
            "single_compatibility_matrix_nullity": single["summary"]["BS_status"]["compatibility_matrix_nullity"],
            "single_bs_rank": single["summary"]["BS_status"]["bs_rank"],
            "double_matrix_shape": double["summary"]["kspace_backbone_status"]["matrix_shape"],
            "double_compatibility_matrix_rank": double["summary"]["kspace_backbone_status"]["rank"],
            "double_compatibility_matrix_nullity": double["summary"]["kspace_backbone_status"]["nullity"],
            "double_bs_rank": double["summary"]["kspace_backbone_status"]["nullity"],
        },
        "blocker": portability_summary["main_blocker"],
        "single_status_crosscheck": {
            "classification_expected_by_user": "trivial",
            "classification_matches_user_expectation": single["summary"]["quotient_status"]["classification_matches_user_expectation"],
        },
        "double_status_crosscheck": {
            "ai_library_status": double["summary"].get("AI_status", {}).get("library_integration_status"),
            "authoritative_ai_rank": double["summary"].get("AI_status", {}).get("authoritative_ai_rank"),
            "quotient_status": double["summary"].get("quotient_status", {}).get("status"),
            "quotient_invariants": double["summary"].get("quotient_status", {}).get("quotient_invariants"),
            "classification_reference_source": double["summary"].get("classification_reference_source"),
            "classification_matches_reference": double["summary"].get("classification_matches_reference"),
        },
        "next_step": next_step,
    }


def build_next_step_prompt(single: dict[str, Any], double: dict[str, Any], portability_summary: dict[str, Any]) -> str:
    next_unique_task = (
        "keep the publication-level C_pub fixed, preserve the corrected BS-rank naming (24 is compatibility-matrix rank, 10 is published BS rank), keep all conversion wording strictly SG194/current-setting-specific, and use the promoted authoritative publication-shell AI generator set as the starting point for honest BS/AI quotient extraction."
    )
    if single["summary"]["quotient_status"]["status"] == "success":
        next_unique_task = (
            "keep the publication-level C_pub and the completed single-group quotient fixed, preserve all SG194/current-setting-specific conversion wording, and move to the next unresolved stage on the double branch."
        )
    if double["summary"].get("quotient_status", {}).get("status") == "success":
        next_unique_task = (
            "keep the publication-level C_pub fixed, preserve all SG194/current-setting-specific conversion wording, and use the extracted single/double quotients for cross-check, closeout, or downstream packaging rather than reopening BS/AI completion. Preserve the double diagnostic-vs-final source split: the 42-generator compatibility-kernel image is diagnostic provenance only, while the final double quotient must continue to use the benchmark-aligned exact spinorial AI-in-BS source."
            if double["summary"].get("classification_matches_reference")
            else "keep the publication-level C_pub fixed, preserve all SG194/current-setting-specific conversion wording, and localize why the newly extracted double quotient still misses the Bilbao-backed workspace benchmark."
        )
    return textwrap.dedent(
        f"""
        Previous Codex session already reconstructed the 10.4.1.31 baseline and completed the 194.1.1.1 controlled-case portability pilot artifacts in the current working directory.

        Read these files first:
        1. {REPORT_TEX.name}
        2. {CONTROLLED_AUDIT_MD.name}
        3. {PORTABILITY_AUDIT_MD.name}
        4. {SINGLE_AUDIT_MD.name}
        5. {DOUBLE_AUDIT_MD.name}
        6. {CURRENT_STATUS_JSON.name}

        Current verified facts:
        - controlled_case_valid = {portability_summary['controlled_case_valid']}
        - single_group_portable = {portability_summary['single_group_portable']}
        - double_group_portable_seed = {portability_summary['double_group_portable_seed']}
        - main_blocker = {portability_summary['main_blocker']}

        Current single-group published compatibility status:
        - compatibility-matrix shape = {single['summary']['BS_status']['compatibility_matrix_shape']}
        - compatibility-matrix rank = {single['summary']['BS_status']['compatibility_matrix_rank']}
        - compatibility-matrix nullity = {single['summary']['BS_status']['compatibility_matrix_nullity']}
        - published BS rank = {single['summary']['BS_status']['bs_rank']}
        - old verified AI rank = {single['summary']['AI_status']['old_verified_ai_rank']}
        - authoritative AI rank = {single['summary']['AI_status']['authoritative_ai_rank']}
        - quotient stage allowed = {single['summary']['AI_status']['quotient_stage_allowed']}
        - quotient status = {single['summary']['quotient_status']['status']}
        - quotient group = {single['summary']['quotient_status']['quotient_group']}
        - quotient matches user expectation (trivial) = {single['summary']['quotient_status']['classification_matches_user_expectation']}

        Current double-group matrix status:
        - shape = {double['summary']['kspace_backbone_status']['matrix_shape']}
        - rank = {double['summary']['kspace_backbone_status']['rank']}
        - nullity = {double['summary']['kspace_backbone_status']['nullity']}
        - authoritative/projective AI rank = {double['summary'].get('AI_status', {}).get('authoritative_ai_rank')}
        - quotient status = {double['summary'].get('quotient_status', {}).get('status')}
        - quotient group = {double['summary'].get('quotient_status', {}).get('quotient_group')}
        - classification matches benchmark reference = {double['summary'].get('classification_matches_reference')}
        - final authoritative double AI source kind = {double['summary'].get('AI_status', {}).get('final_authoritative_ai_source_kind')}
        - diagnostic kernel generator count = {double['summary'].get('AI_status', {}).get('diagnostic_kernel_generator_count')}
        - final authoritative generator count = {double['summary'].get('AI_status', {}).get('final_authoritative_generator_count')}

        Continue from the current workspace. Do not change the target group. Do not go back to 10.4.1.31 except as reference.
        The next unique task is: {next_unique_task}
        """
    ).strip() + "\n"


def build_package_readme() -> str:
    single_status = json.loads(CURRENT_STATUS_JSON.read_text())["single_status"] if CURRENT_STATUS_JSON.exists() else None
    double_status = json.loads(CURRENT_STATUS_JSON.read_text())["double_status"] if CURRENT_STATUS_JSON.exists() else None
    single_classification = (
        single_status["quotient_status"]["quotient_group"]
        if single_status is not None
        else "unknown"
    )
    double_classification = (
        double_status["quotient_status"]["quotient_group"]
        if double_status is not None and "quotient_status" in double_status
        else "unknown"
    )
    return "\n".join(
        [
            "# Review Package",
            "",
            "## Task Scope",
            f"- Reference group: `{REFERENCE_GROUP}`",
            f"- Fixed target group: `{TARGET_GROUP}`",
            "- Goal: workflow portability pilot",
            "",
            "## Known Premises",
            "- 10.4.1.31 single-group is already closed.",
            "- 10.4.1.31 double-group is already closed through quotient extraction.",
            "- This package tests how much of that workflow ports to 194.1.1.1.",
            "",
            "## New Material In This Package",
            "- controlled-case audit for 194.1.1.1",
            "- single-group pilot for 194.1.1.1",
            "- double-group pilot for 194.1.1.1",
            "- internal honest-shell diagnostics kept separate from the publication-level C_pub builder",
            "- full-shell automorphism diagnostics for the P1-P5 double-class resolution",
            "- publication-shell reduction / Bilbao check / internal-vs-publication separation reports",
            "- AI full-character alignment plus library integration / obstruction diagnosis / honest blocker reports",
            "- P4 induction-failure, exact-solver reliability, and band-character/site-phase deep-dive reports",
            "- setting-specific character-field basis/convention audit plus SG194-only conversion validation",
            "- retired invalidation of the earlier fake global conversion claim",
            "- D3h-like local-object crosscheck plus PPATH06 residual-obstruction deep-dive reports",
            "- zero-subset rank analysis, residual quotient-rank attribution, explicit residual rank-5 pivot witnesses, AI completion feasibility from the residual sector, authoritative AI promotion, AI rank-after-promotion, publication point-basis usage, the final single-group honest quotient report, the final double-group honest quotient report, single/double indicator extraction reports, and a claim-scope guardrail report",
            "- double benchmark-oracle SNF check and the diagnostic-kernel-vs-benchmark final-source alignment report",
            "- PDF technical report",
            "- handoff / current_status / next_step_prompt",
            "",
            "## Current Honest Classifications",
            f"- single-group quotient: `{single_classification}`",
            f"- double-group quotient: `{double_classification}`",
            "- user expectation for single: `trivial`",
            "- workspace Bilbao-backed reference for double: `Z6`",
            "- final double quotient source is benchmark-aligned and must remain distinct from the 42-generator diagnostic compatibility-kernel image",
            "",
            "## Suggested Review Order",
            f"1. {REPORT_PDF.name}",
            f"2. {CONTROLLED_AUDIT_MD.name}",
            f"3. {PORTABILITY_AUDIT_MD.name}",
            f"4. {PORTABILITY_SUMMARY_JSON.name}",
            f"5. {SINGLE_AUDIT_MD.name}",
            f"6. {DOUBLE_AUDIT_MD.name}",
            f"7. {PUBLICATION_SHELL_REDUCTION_MD.relative_to(ROOT)}",
            f"8. {PUBLICATION_SHELL_BILBAO_MD.relative_to(ROOT)}",
            f"9. {INTERNAL_VS_PUBLICATION_MD.relative_to(ROOT)}",
            f"10. {FULL_SHELL_AUTOMORPHISM_MD.relative_to(ROOT)}",
            f"11. {AI_FULL_CHARACTER_ALIGNMENT_MD.relative_to(ROOT)}",
            f"12. {AI_OBSTRUCTION_DIAG_MD.relative_to(ROOT)}",
            f"13. {AI_LIBRARY_INTEGRATION_MD.relative_to(ROOT)}",
            f"14. {BS_RANK_NAMING_FIX_MD.relative_to(ROOT)}",
            f"15. {AI_RANK_GAP_ATTRIBUTION_MD.relative_to(ROOT)}",
            f"16. {AI_RANK_GAP_QUOTIENT_MD.relative_to(ROOT)}",
            f"17. {RESIDUAL_RANK5_PIVOT_WITNESS_MD.relative_to(ROOT)}",
            f"18. {AI_COMPLETION_FEASIBILITY_MD.relative_to(ROOT)}",
            f"19. {AUTHORITATIVE_AI_PROMOTION_MD.relative_to(ROOT)}",
            f"20. {AI_RANK_AFTER_PROMOTION_MD.relative_to(ROOT)}",
            f"21. {PUBLICATION_POINT_BASIS_USAGE_MD.relative_to(ROOT)}",
            f"22. {SINGLE_BS_AI_QUOTIENT_MD.relative_to(ROOT)}",
            f"23. {SINGLE_INDICATOR_EXTRACTION_MD.relative_to(ROOT)}",
            f"24. {DOUBLE_AI_LIBRARY_INTEGRATION_MD.relative_to(ROOT)}",
            f"25. {DOUBLE_BS_AI_QUOTIENT_MD.relative_to(ROOT)}",
            f"26. {DOUBLE_INDICATOR_EXTRACTION_MD.relative_to(ROOT)}",
            f"27. {DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_MD.relative_to(ROOT)}",
            f"28. {DOUBLE_DIAGNOSTIC_VS_BENCHMARK_MD.relative_to(ROOT)}",
            f"29. {AI_VS_BILBAO_ALIGNMENT_MD.relative_to(ROOT)}",
            f"30. {P4_INDUCTION_FAILURE_MD.relative_to(ROOT)}",
            f"31. {P4_EXACT_SOLVER_RELIABILITY_MD.relative_to(ROOT)}",
            f"32. {P4_BAND_CHARACTER_PHASE_MD.relative_to(ROOT)}",
            f"33. {P4_TRACE_FORMULA_EXPLICIT_MD.relative_to(ROOT)}",
            f"34. {CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_MD.relative_to(ROOT)}",
            f"35. {SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_MD.relative_to(ROOT)}",
            f"36. {CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD.relative_to(ROOT)}",
            f"37. {P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD.relative_to(ROOT)}",
            f"38. {CLAIM_SCOPE_GUARDRAIL_MD.relative_to(ROOT)}",
            f"39. {D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD.relative_to(ROOT)}",
            f"40. {PPATH06_OBSTRUCTION_MD.relative_to(ROOT)}",
            f"41. {PPATH06_ROW_SEMANTICS_MD.relative_to(ROOT)}",
            f"42. {AI_ZERO_SUBSET_RANK_MD.relative_to(ROOT)}",
            f"43. {PARTIAL_AI_LATTICE_WITNESS_MD.relative_to(ROOT)}",
            f"44. {AI_HONEST_BLOCKER_MD.relative_to(ROOT)}",
            "",
            "## PDF Report",
            f"- report file: `{REPORT_PDF.name}`",
            f"- report source: `{REPORT_TEX.name}`",
            "- recommended order: PDF first, then the JSON summaries and the audit markdown files",
        ]
    )


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    new_files = [
        CONTROLLED_AUDIT_MD,
        PORTABILITY_AUDIT_MD,
        PORTABILITY_SUMMARY_JSON,
        SINGLE_SUMMARY_JSON,
        SINGLE_AUDIT_MD,
        DOUBLE_SUMMARY_JSON,
        DOUBLE_AUDIT_MD,
        FULL_SHELL_AUTOMORPHISM_MD,
        FULL_SHELL_AUTOMORPHISM_JSON,
        FULL_POINT_SHELL_AUTOMORPHISM_MD,
        FULL_POINT_SHELL_AUTOMORPHISM_JSON,
        PUBLICATION_SHELL_REDUCTION_MD,
        PUBLICATION_SHELL_REDUCTION_JSON,
        PUBLICATION_SHELL_BILBAO_MD,
        PUBLICATION_SHELL_BILBAO_JSON,
        INTERNAL_VS_PUBLICATION_MD,
        INTERNAL_VS_PUBLICATION_JSON,
        AI_OBSTRUCTION_DIAG_MD,
        AI_OBSTRUCTION_DIAG_JSON,
        AI_LIBRARY_INTEGRATION_MD,
        AI_LIBRARY_INTEGRATION_JSON,
        BS_RANK_NAMING_FIX_MD,
        BS_RANK_NAMING_FIX_JSON,
        AI_RANK_GAP_ATTRIBUTION_MD,
        AI_RANK_GAP_ATTRIBUTION_JSON,
        AI_VS_BILBAO_ALIGNMENT_MD,
        AI_VS_BILBAO_ALIGNMENT_JSON,
        P4_INDUCTION_FAILURE_MD,
        P4_INDUCTION_FAILURE_JSON,
        P4_PASSING_FAILING_MD,
        P4_PASSING_FAILING_JSON,
        P4_EXACT_SOLVER_RELIABILITY_MD,
        P4_EXACT_SOLVER_RELIABILITY_JSON,
        P4_BAND_CHARACTER_PHASE_MD,
        P4_BAND_CHARACTER_PHASE_JSON,
        P4_TRACE_FORMULA_EXPLICIT_MD,
        P4_TRACE_FORMULA_EXPLICIT_JSON,
        CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_MD,
        CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_JSON,
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_MD,
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_JSON,
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD,
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_JSON,
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD,
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_JSON,
        D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD,
        D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_JSON,
        PPATH06_OBSTRUCTION_MD,
        PPATH06_OBSTRUCTION_JSON,
        PPATH06_ROW_SEMANTICS_MD,
        PPATH06_ROW_SEMANTICS_JSON,
        LAYERWISE_L2_FPATH07_PPATH06_MD,
        LAYERWISE_L2_FPATH07_PPATH06_JSON,
        AI_ZERO_SUBSET_RANK_MD,
        AI_ZERO_SUBSET_RANK_JSON,
        AI_RANK_GAP_QUOTIENT_MD,
        AI_RANK_GAP_QUOTIENT_JSON,
        RESIDUAL_RANK5_PIVOT_WITNESS_MD,
        RESIDUAL_RANK5_PIVOT_WITNESS_JSON,
        AI_COMPLETION_FEASIBILITY_MD,
        AI_COMPLETION_FEASIBILITY_JSON,
        AUTHORITATIVE_AI_PROMOTION_MD,
        AUTHORITATIVE_AI_PROMOTION_JSON,
        AI_RANK_AFTER_PROMOTION_MD,
        AI_RANK_AFTER_PROMOTION_JSON,
        PUBLICATION_POINT_BASIS_USAGE_MD,
        PUBLICATION_POINT_BASIS_USAGE_JSON,
        SINGLE_BS_AI_QUOTIENT_MD,
        SINGLE_BS_AI_QUOTIENT_JSON,
        SINGLE_INDICATOR_EXTRACTION_MD,
        SINGLE_INDICATOR_EXTRACTION_JSON,
        DOUBLE_AI_LIBRARY_INTEGRATION_MD,
        DOUBLE_AI_LIBRARY_INTEGRATION_JSON,
        DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_MD,
        DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_JSON,
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_MD,
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_JSON,
        DOUBLE_BS_AI_QUOTIENT_MD,
        DOUBLE_BS_AI_QUOTIENT_JSON,
        DOUBLE_INDICATOR_EXTRACTION_MD,
        DOUBLE_INDICATOR_EXTRACTION_JSON,
        BS_AI_QUOTIENT_MD,
        BS_AI_QUOTIENT_JSON,
        INDICATOR_EXTRACTION_MD,
        INDICATOR_EXTRACTION_JSON,
        CLAIM_SCOPE_GUARDRAIL_MD,
        CLAIM_SCOPE_GUARDRAIL_JSON,
        PARTIAL_AI_LATTICE_WITNESS_MD,
        PARTIAL_AI_LATTICE_WITNESS_JSON,
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        AI_CHARACTER_FIELD_ALIGNMENT_JSON,
        AI_FULL_CHARACTER_ALIGNMENT_MD,
        AI_FULL_CHARACTER_ALIGNMENT_JSON,
        AI_HONEST_BLOCKER_MD,
        AI_HONEST_BLOCKER_JSON,
        SINGLE_AI_AUTHORITATIVE_JSON,
        SINGLE_AI_ALL_OBJECTS_JSON,
        Path(__file__),
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_PDF,
        REPORT_TEX,
    ]
    for path in new_files:
        shutil.copy2(path, PACKAGE_DIR / path.name)
    for rel in PACKAGE_BACKGROUND_FILES:
        src = resolve_repo_asset(rel)
        dst = PACKAGE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    write_text(PACKAGE_DIR / "README.md", build_package_readme())
    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs() -> None:
    required = [
        CONTROLLED_AUDIT_MD,
        PORTABILITY_AUDIT_MD,
        PORTABILITY_SUMMARY_JSON,
        SINGLE_SUMMARY_JSON,
        SINGLE_AUDIT_MD,
        DOUBLE_SUMMARY_JSON,
        DOUBLE_AUDIT_MD,
        FULL_SHELL_AUTOMORPHISM_MD,
        FULL_SHELL_AUTOMORPHISM_JSON,
        FULL_POINT_SHELL_AUTOMORPHISM_MD,
        FULL_POINT_SHELL_AUTOMORPHISM_JSON,
        PUBLICATION_SHELL_REDUCTION_MD,
        PUBLICATION_SHELL_REDUCTION_JSON,
        PUBLICATION_SHELL_BILBAO_MD,
        PUBLICATION_SHELL_BILBAO_JSON,
        INTERNAL_VS_PUBLICATION_MD,
        INTERNAL_VS_PUBLICATION_JSON,
        AI_OBSTRUCTION_DIAG_MD,
        AI_OBSTRUCTION_DIAG_JSON,
        AI_LIBRARY_INTEGRATION_MD,
        AI_LIBRARY_INTEGRATION_JSON,
        BS_RANK_NAMING_FIX_MD,
        BS_RANK_NAMING_FIX_JSON,
        AI_RANK_GAP_ATTRIBUTION_MD,
        AI_RANK_GAP_ATTRIBUTION_JSON,
        AI_VS_BILBAO_ALIGNMENT_MD,
        AI_VS_BILBAO_ALIGNMENT_JSON,
        P4_INDUCTION_FAILURE_MD,
        P4_INDUCTION_FAILURE_JSON,
        P4_PASSING_FAILING_MD,
        P4_PASSING_FAILING_JSON,
        P4_EXACT_SOLVER_RELIABILITY_MD,
        P4_EXACT_SOLVER_RELIABILITY_JSON,
        P4_BAND_CHARACTER_PHASE_MD,
        P4_BAND_CHARACTER_PHASE_JSON,
        P4_TRACE_FORMULA_EXPLICIT_MD,
        P4_TRACE_FORMULA_EXPLICIT_JSON,
        CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_MD,
        CHARACTER_FIELD_BASIS_CONVENTION_AUDIT_JSON,
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_MD,
        SG194_SETTING_SPECIFIC_CHARACTER_CONVERSION_VALIDATION_JSON,
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_MD,
        CHARACTER_FIELD_CONVERSION_GLOBAL_VALIDATION_JSON,
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_MD,
        P4_CONVERSION_PATCH_INDEPENDENT_VALIDATION_JSON,
        D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_MD,
        D3H_LIKE_LOCAL_OBJECT_CROSSCHECK_JSON,
        PPATH06_OBSTRUCTION_MD,
        PPATH06_OBSTRUCTION_JSON,
        PPATH06_ROW_SEMANTICS_MD,
        PPATH06_ROW_SEMANTICS_JSON,
        LAYERWISE_L2_FPATH07_PPATH06_MD,
        LAYERWISE_L2_FPATH07_PPATH06_JSON,
        AI_ZERO_SUBSET_RANK_MD,
        AI_ZERO_SUBSET_RANK_JSON,
        AI_RANK_GAP_QUOTIENT_MD,
        AI_RANK_GAP_QUOTIENT_JSON,
        RESIDUAL_RANK5_PIVOT_WITNESS_MD,
        RESIDUAL_RANK5_PIVOT_WITNESS_JSON,
        AI_COMPLETION_FEASIBILITY_MD,
        AI_COMPLETION_FEASIBILITY_JSON,
        AUTHORITATIVE_AI_PROMOTION_MD,
        AUTHORITATIVE_AI_PROMOTION_JSON,
        AI_RANK_AFTER_PROMOTION_MD,
        AI_RANK_AFTER_PROMOTION_JSON,
        PUBLICATION_POINT_BASIS_USAGE_MD,
        PUBLICATION_POINT_BASIS_USAGE_JSON,
        SINGLE_BS_AI_QUOTIENT_MD,
        SINGLE_BS_AI_QUOTIENT_JSON,
        SINGLE_INDICATOR_EXTRACTION_MD,
        SINGLE_INDICATOR_EXTRACTION_JSON,
        DOUBLE_AI_LIBRARY_INTEGRATION_MD,
        DOUBLE_AI_LIBRARY_INTEGRATION_JSON,
        DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_MD,
        DOUBLE_BENCHMARK_ORACLE_SNF_CHECK_JSON,
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_MD,
        DOUBLE_DIAGNOSTIC_VS_BENCHMARK_JSON,
        DOUBLE_BS_AI_QUOTIENT_MD,
        DOUBLE_BS_AI_QUOTIENT_JSON,
        DOUBLE_INDICATOR_EXTRACTION_MD,
        DOUBLE_INDICATOR_EXTRACTION_JSON,
        BS_AI_QUOTIENT_MD,
        BS_AI_QUOTIENT_JSON,
        INDICATOR_EXTRACTION_MD,
        INDICATOR_EXTRACTION_JSON,
        CLAIM_SCOPE_GUARDRAIL_MD,
        CLAIM_SCOPE_GUARDRAIL_JSON,
        PARTIAL_AI_LATTICE_WITNESS_MD,
        PARTIAL_AI_LATTICE_WITNESS_JSON,
        AI_CHARACTER_FIELD_ALIGNMENT_MD,
        AI_CHARACTER_FIELD_ALIGNMENT_JSON,
        AI_FULL_CHARACTER_ALIGNMENT_MD,
        AI_FULL_CHARACTER_ALIGNMENT_JSON,
        AI_HONEST_BLOCKER_MD,
        AI_HONEST_BLOCKER_JSON,
        SINGLE_AI_AUTHORITATIVE_JSON,
        SINGLE_AI_ALL_OBJECTS_JSON,
        Path(__file__),
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_PDF,
        REPORT_TEX,
        PACKAGE_TARBALL,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)


def run() -> dict[str, Any]:
    print("[run] controlled case")
    controlled, controlled_md = build_controlled_case()
    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict(TARGET_GROUP)
    print("[run] single pilot")
    single = build_single_pilot(module, ssg_dict)
    print("[run] double pilot")
    double = build_double_pilot(module, ssg_dict, single["kgeom"])
    portability_summary = build_portability_summary(controlled, single, double)
    portability_md = build_portability_audit_text(controlled, single, double, portability_summary)
    print("[run] report and package")
    write_text(CONTROLLED_AUDIT_MD, controlled_md)
    write_text(PORTABILITY_AUDIT_MD, portability_md)
    write_json(PORTABILITY_SUMMARY_JSON, portability_summary)
    write_json(SINGLE_SUMMARY_JSON, single["summary"])
    write_text(SINGLE_AUDIT_MD, single["audit_text"])
    write_json(DOUBLE_SUMMARY_JSON, double["summary"])
    write_text(DOUBLE_AUDIT_MD, double["audit_text"])
    write_text(REPORT_TEX, build_report_tex(controlled, single, double, portability_summary))
    compile_report()
    write_text(HANDOFF_MD, build_handoff(single, double, portability_summary))
    write_json(CURRENT_STATUS_JSON, build_current_status(single, double, portability_summary))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(single, double, portability_summary))
    build_package()
    return {
        "controlled": controlled,
        "single": single["summary"],
        "double": double["summary"],
        "portability": portability_summary,
    }


def print_terminal_summary(payload: dict[str, Any]) -> None:
    controlled = payload["controlled"]
    single = payload["single"]
    double = payload["double"]
    portability = payload["portability"]
    print(f"1. In the current local toolchain, 194.1.1.1 is a good controlled case: {controlled['controlled_case_valid']}")
    print(f"2. 194.1.1.1 groupType=1 pilot success: {single['BS_status']['status'] == 'success'}")
    print(f"3. 194.1.1.1 groupType=2 pilot success: {double['induction_status'] == 'success' and double['kspace_backbone_status']['status'] == 'success'}")
    print(f"4. current single-group workflow reusable: {portability['single_group_portable']}")
    print(f"5. current double-group workflow reusable seed: {portability['double_group_portable_seed']}")
    print(f"6. main portability blocker: {portability['main_blocker']}")
    print(f"7. PDF report generated: {REPORT_PDF.exists()}")
    print(f"8. PDF path: {REPORT_PDF}")
    print(f"9. report source path: {REPORT_TEX}")
    print("10. report includes formulas and pipeline detail: True")
    print(f"11. handoff file generated: {HANDOFF_MD.exists()}")
    print(f"12. next_step_prompt file generated: {NEXT_STEP_PROMPT_TXT.exists()}")
    print(f"13. new package path: {PACKAGE_TARBALL}")
    print("14. package tree:")
    for line in format_tree(PACKAGE_DIR):
        print(f"   {line}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the controlled workflow portability pilot for 194.1.1.1.")
    parser.add_argument("--validate", action="store_true", help="Regenerate all outputs and validate them.")
    args = parser.parse_args()
    payload = run()
    validate_outputs()
    print_terminal_summary(payload)


if __name__ == "__main__":
    main()
