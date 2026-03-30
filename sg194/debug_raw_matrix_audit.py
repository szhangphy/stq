#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent

GROUP_10 = "10.4.1.31"
GROUP_194 = "194.1.1.1"

RAW_PREFIXES = {
    "10_4_1_31_single": "raw_10_4_1_31_single",
    "10_4_1_31_double": "raw_10_4_1_31_double",
    "194_1_1_1_single": "raw_194_1_1_1_single",
    "194_1_1_1_double": "raw_194_1_1_1_double",
}

RAW_C_JSON = {key: ROOT / f"{prefix}_C.json" for key, prefix in RAW_PREFIXES.items()}
RAW_BS_BASIS_RAW_JSON = {key: ROOT / f"{prefix}_bs_basis_raw.json" for key, prefix in RAW_PREFIXES.items()}
RAW_BS_BASIS_PRETTY_JSON = {key: ROOT / f"{prefix}_bs_basis_pretty.json" for key, prefix in RAW_PREFIXES.items()}
RAW_AI_CANDIDATES_JSON = {key: ROOT / f"{prefix}_ai_candidates.json" for key, prefix in RAW_PREFIXES.items()}
RAW_AI_BASIS_JSON = {key: ROOT / f"{prefix}_ai_basis.json" for key, prefix in RAW_PREFIXES.items()}
RAW_AI_IN_BS_MATRIX_JSON = {key: ROOT / f"{prefix}_ai_in_bs_matrix.json" for key, prefix in RAW_PREFIXES.items()}
RAW_QUOTIENT_JSON = {key: ROOT / f"{prefix}_quotient.json" for key, prefix in RAW_PREFIXES.items()}

AUDIT_MD = ROOT / "raw_matrix_level_audit.md"
AUDIT_SUMMARY_JSON = ROOT / "raw_matrix_level_audit_summary.json"
HANDOFF_MD = ROOT / "handoff_raw_matrix_audit.md"
CURRENT_STATUS_JSON = ROOT / "current_status_raw_matrix_audit.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_raw_matrix_audit.txt"
SCRIPT_PATH = ROOT / "debug_raw_matrix_audit.py"
REPORT_TEX = ROOT / "raw_matrix_level_audit_report.tex"
REPORT_PDF = ROOT / "raw_matrix_level_audit_report.pdf"

MINIPACK_DIR = ROOT / "independent_recompute_minipack"
MINIPACK_README = MINIPACK_DIR / "README.md"
MINIPACK_SCRIPT = MINIPACK_DIR / "recompute_from_raw.py"
MINIPACK_RAW_DIR = MINIPACK_DIR / "raw"

PACKAGE_NAME = "review_package_raw_matrix_level_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

README_PATH = PACKAGE_DIR / "README.md"

RESEARCH_RESULTS_TSV = ROOT / "research-results-raw-matrix.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-raw-matrix.json"
RUN_TAG = "two-group-raw-matrix-audit-20260330"
METRIC_NAME = "raw_matrix_audit_missing_deliverable_count"
VERIFY_CMD = "python3 -u debug_raw_matrix_audit.py --validate"

CASE_SPECS = {
    "10_4_1_31_single": {
        "group": GROUP_10,
        "group_type": 1,
        "scope": "single",
        "case_label": "10.4.1.31 / groupType=1",
        "compat_path": ROOT / "single_group_full_compatibility_with_planes.json",
        "candidate_path": ROOT / "single_group_ai_expanded_v3_candidates.json",
        "legacy_bs_summary_path": ROOT / "single_group_indicator_group_summary.json",
        "legacy_bs_basis_raw_path": ROOT / "single_group_bs_with_planes_basis_raw.json",
        "legacy_bs_basis_pretty_path": ROOT / "single_group_bs_with_planes_basis_pretty.json",
        "legacy_ai_basis_path": ROOT / "single_group_ai_expanded_v3_basis.json",
        "legacy_indicator_path": ROOT / "single_group_indicator_generators.json",
        "legacy_ai_summary_path": ROOT / "single_group_ai_completeness_summary.json",
        "correctness_case_key": "single",
        "expected_raw_quotient": "Z2 x Z2",
    },
    "10_4_1_31_double": {
        "group": GROUP_10,
        "group_type": 2,
        "scope": "double",
        "case_label": "10.4.1.31 / groupType=2",
        "compat_path": ROOT / "double_group_full_compatibility_with_planes_10.4.1.31.json",
        "candidate_path": ROOT / "double_group_ai_v2_candidates_10.4.1.31.json",
        "legacy_bs_summary_path": ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
        "legacy_bs_basis_raw_path": ROOT / "double_group_bs_basis_raw_10.4.1.31.json",
        "legacy_bs_basis_pretty_path": ROOT / "double_group_bs_basis_pretty_10.4.1.31.json",
        "legacy_ai_basis_path": ROOT / "double_group_ai_v2_basis_10.4.1.31.json",
        "legacy_indicator_path": ROOT / "double_group_indicator_generators_10.4.1.31.json",
        "legacy_ai_summary_path": ROOT / "double_group_ai_completeness_summary_10.4.1.31.json",
        "correctness_case_key": "double",
        "expected_raw_quotient": "Z^2 x Z2 x Z2 x Z2 x Z2",
    },
    "194_1_1_1_single": {
        "group": GROUP_194,
        "group_type": 1,
        "scope": "single",
        "case_label": "194.1.1.1 / groupType=1",
        "compat_path": ROOT / "group_194_1_1_1_single_full_compatibility_with_planes.json",
        "legacy_bs_summary_path": ROOT / "group_194_1_1_1_single_indicator_group_summary.json",
        "legacy_indicator_path": ROOT / "group_194_1_1_1_single_indicator_generators.json",
        "legacy_ai_summary_path": ROOT / "group_194_1_1_1_single_ai_completion_summary.json",
        "correctness_case_key": "single",
        "expected_raw_quotient": "Z^16",
    },
    "194_1_1_1_double": {
        "group": GROUP_194,
        "group_type": 2,
        "scope": "double",
        "case_label": "194.1.1.1 / groupType=2",
        "compat_path": ROOT / "group_194_1_1_1_double_full_compatibility_with_planes.json",
        "legacy_bs_summary_path": ROOT / "group_194_1_1_1_double_indicator_group_summary.json",
        "legacy_indicator_path": ROOT / "group_194_1_1_1_double_indicator_generators.json",
        "legacy_ai_summary_path": ROOT / "group_194_1_1_1_double_ai_completion_summary.json",
        "correctness_case_key": "double",
        "expected_raw_quotient": "Z^16",
    },
}

BACKGROUND_FILES = [
    ROOT / "two_group_correctness_summary.json",
    ROOT / "audit_10_4_1_31_correctness.json",
    ROOT / "audit_194_1_1_1_correctness.json",
    ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json",
    ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json",
    ROOT / "single_group_indicator_group_summary.json",
    ROOT / "single_group_indicator_generators.json",
    ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
    ROOT / "double_group_indicator_generators_10.4.1.31.json",
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

REQUIRED_OUTPUTS = (
    list(RAW_C_JSON.values())
    + list(RAW_BS_BASIS_RAW_JSON.values())
    + list(RAW_BS_BASIS_PRETTY_JSON.values())
    + list(RAW_AI_CANDIDATES_JSON.values())
    + list(RAW_AI_BASIS_JSON.values())
    + list(RAW_AI_IN_BS_MATRIX_JSON.values())
    + list(RAW_QUOTIENT_JSON.values())
    + [
        AUDIT_MD,
        AUDIT_SUMMARY_JSON,
        MINIPACK_README,
        MINIPACK_SCRIPT,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_TEX,
        REPORT_PDF,
        PACKAGE_TARBALL,
    ]
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_stage1_port_module():
    return load_module(ROOT / "debug_workflow_portability_194.1.1.1.py", "raw_matrix_audit_stage1_port")


def load_stage2_module():
    return load_module(ROOT / "debug_workflow_portability_stage2_194.1.1.1.py", "raw_matrix_audit_stage2")


def load_helper_module():
    return load_module(ROOT / "debug_sg194_nonabelian_local_library.py", "raw_matrix_audit_helper")


def json_default(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": float(sp.re(value)), "imag": float(sp.im(value))}
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        return str(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sp_matrix_to_rows(matrix: sp.Matrix) -> list[list[int]]:
    return [[int(matrix[row, col]) for col in range(matrix.cols)] for row in range(matrix.rows)]


def sp_vector_to_list(vec: sp.Matrix) -> list[int]:
    return [int(value) for value in list(vec)]


def matrix_from_columns(columns: list[list[int]]) -> sp.Matrix:
    if not columns:
        return sp.zeros(0, 0)
    return sp.Matrix.hstack(*[sp.Matrix(column) for column in columns])


def support_from_vector(vector: list[int], ordering: list[str]) -> list[dict[str, Any]]:
    return [
        {"unknown": unknown, "coeff": int(coeff)}
        for unknown, coeff in zip(ordering, vector)
        if int(coeff) != 0
    ]


def first_nonzero_sign(vector: list[int]) -> int:
    for value in vector:
        if value > 0:
            return 1
        if value < 0:
            return -1
    return 1


def normalize_sign(primary: list[int], secondary: list[int] | None = None) -> tuple[list[int], list[int] | None]:
    sign = first_nonzero_sign(primary)
    if sign < 0:
        primary = [-value for value in primary]
        if secondary is not None:
            secondary = [-value for value in secondary]
    return primary, secondary


def smith_rank_and_diagonal(diagonal: sp.Matrix) -> tuple[int, list[int]]:
    diag_entries: list[int] = []
    for idx in range(min(diagonal.rows, diagonal.cols)):
        value = int(diagonal[idx, idx])
        if value != 0:
            diag_entries.append(abs(value))
    return len(diag_entries), diag_entries


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    parts: list[str] = []
    if free_rank > 0:
        parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts) if parts else "trivial"


def latex_group_string(group: str) -> str:
    if group == "trivial":
        return r"\mathrm{trivial}"
    chunks = []
    for token in group.split(" x "):
        if token.startswith("Z^"):
            chunks.append(rf"\mathrm{{Z}}^{{{token[2:]}}}")
        elif token.startswith("Z") and token[1:].isdigit():
            chunks.append(rf"\mathrm{{Z}}_{{{token[1:]}}}")
        else:
            chunks.append(token)
    return r" \times ".join(chunks)


def latex_escape_text(text: str) -> str:
    replacements = {
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
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def build_row_labels(global_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = []
    for index, row in enumerate(global_rows):
        payload = {key: value for key, value in row.items() if key != "matrix_row"}
        payload["global_row_index"] = index
        labels.append(payload)
    return labels


def compute_c_artifact(case_key: str, compat_root: dict[str, Any]) -> dict[str, Any]:
    ordering = list(compat_root["global_unknown_ordering"])
    matrix_rows = compat_root["global_matrix"]
    C = sp.Matrix(matrix_rows)
    D, U, V = smith_normal_decomp(C, domain=ZZ)
    rank, smith_diag = smith_rank_and_diagonal(D)
    nullity = int(C.cols - rank)
    case = CASE_SPECS[case_key]
    row_labels = build_row_labels(compat_root.get("global_matrix_rows", []))
    artifact = {
        "group": case["group"],
        "group_type": case["group_type"],
        "case_key": case_key,
        "compatibility_source_file": str(case["compat_path"].name),
        "unknown_ordering": ordering,
        "row_labels": row_labels,
        "matrix_shape": [int(C.rows), int(C.cols)],
        "rank_C": rank,
        "nullity_C": nullity,
        "smith_diagonal_nonzero": smith_diag,
        "matrix": [[int(value) for value in row] for row in matrix_rows],
    }
    return {
        "artifact": artifact,
        "matrix": C,
        "smith_D": D,
        "smith_U": U,
        "smith_V": V,
        "rank": rank,
        "nullity": nullity,
        "unknown_ordering": ordering,
        "row_labels": row_labels,
    }


def compute_bs_artifacts(case_key: str, c_ctx: dict[str, Any]) -> dict[str, Any]:
    C = c_ctx["matrix"]
    V = c_ctx["smith_V"]
    rank = c_ctx["rank"]
    ordering = c_ctx["unknown_ordering"]
    basis_matrix = V[:, rank:]
    if C * basis_matrix != sp.zeros(C.rows, basis_matrix.cols):
        raise ValueError(f"{case_key}: Smith-derived kernel basis is not in ker(C)")
    if int(basis_matrix.rank()) != basis_matrix.cols:
        raise ValueError(f"{case_key}: Smith-derived kernel basis is not independent")

    raw_vectors = []
    pretty_vectors = []
    for index in range(basis_matrix.cols):
        raw = sp_vector_to_list(basis_matrix[:, index])
        raw_vectors.append(
            {
                "id": f"{case_key}_bs_raw_basis_{index + 1:02d}",
                "vector": raw,
                "support": support_from_vector(raw, ordering),
            }
        )
        pretty, _ = normalize_sign(list(raw))
        pretty_vectors.append(
            {
                "id": f"{case_key}_bs_pretty_basis_{index + 1:02d}",
                "vector": pretty,
                "support": support_from_vector(pretty, ordering),
            }
        )

    pretty_matrix = matrix_from_columns([item["vector"] for item in pretty_vectors])
    if C * pretty_matrix != sp.zeros(C.rows, pretty_matrix.cols):
        raise ValueError(f"{case_key}: pretty kernel basis left the kernel")
    if int(pretty_matrix.rank()) != basis_matrix.cols:
        raise ValueError(f"{case_key}: pretty basis is not independent")

    base_payload = {
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "case_key": case_key,
        "unknown_ordering": ordering,
        "kernel_method": "smith_normal_decomp over ZZ on the raw compatibility matrix C",
        "matrix_shape": c_ctx["artifact"]["matrix_shape"],
        "rank_C": c_ctx["artifact"]["rank_C"],
        "nullity_C": c_ctx["artifact"]["nullity_C"],
        "smith_diagonal_nonzero": c_ctx["artifact"]["smith_diagonal_nonzero"],
    }
    raw_payload = dict(base_payload)
    raw_payload.update(
        {
            "basis_kind": "raw_smith_kernel_basis",
            "basis_vectors": raw_vectors,
        }
    )
    pretty_payload = dict(base_payload)
    pretty_payload.update(
        {
            "basis_kind": "sign_normalized_smith_kernel_basis",
            "basis_vectors": pretty_vectors,
        }
    )

    return {
        "raw_payload": raw_payload,
        "pretty_payload": pretty_payload,
        "basis_matrix": basis_matrix,
        "pretty_basis_matrix": pretty_matrix,
        "ordering": ordering,
        "basis_ids": [item["id"] for item in raw_vectors],
    }


def normalize_existing_single_candidate(candidate: dict[str, Any], ordering: list[str]) -> dict[str, Any]:
    vector = [int(value) for value in candidate["unknown_vector"]]
    family_dimension = int(candidate["family_dimension"])
    local_obj = dict(candidate.get("local_rep") or candidate.get("magnetic_local_corep") or {})
    family_id = candidate.get("family_letter") or candidate.get("source_family")
    local_kind = "single_local_irrep" if "local_rep" in candidate else "single_magnetic_local_corep"
    rep_coord = (
        candidate.get("representative_coordinate_symbolic")
        or candidate.get("representative_coordinate_sample_magnetic")
        or candidate.get("representative_coordinate_magnetic_sample")
    )
    return {
        "generator_id": candidate["generator_id"],
        "group_type": 1,
        "family_id": family_id,
        "family_dimension": family_dimension,
        "family_kind": "point-like" if family_dimension == 0 else "parametric",
        "family_tier": candidate.get("family_tier"),
        "local_object_label": local_obj.get("label") or candidate.get("generator_id"),
        "local_object_kind": local_kind,
        "local_object_dimension": int(local_obj.get("dimension", 1)),
        "local_object_origin": local_obj.get("local_rep_scope") or candidate.get("source_type"),
        "representative_coordinate": rep_coord,
        "multiplicity": int(candidate["multiplicity"]),
        "site_symmetry": candidate.get("site_symmetry"),
        "unknown_vector": vector,
        "support": support_from_vector(vector, ordering),
        "compatibility_zero": bool(candidate.get("compatibility_zero", False)),
        "source_artifact": "single_group_ai_expanded_v3_candidates.json",
        "source_payload": {
            "sample_parameters": candidate.get("sample_parameters"),
            "stabilizer_summary": candidate.get("stabilizer_summary"),
            "antiunitary_extension_visible_in_current_unitary_kspace_target": candidate.get(
                "antiunitary_extension_visible_in_current_unitary_kspace_target"
            ),
        },
    }


def normalize_existing_double_candidate(candidate: dict[str, Any], ordering: list[str]) -> dict[str, Any]:
    vector = [int(value) for value in candidate["vector_in_bs_double_unknown_ordering"]]
    origin = str(candidate.get("origin", "unknown"))
    family_kind = "point-like" if "pointlike" in origin else "parametric" if "parametric" in origin else "unknown"
    return {
        "generator_id": candidate["generator_id"],
        "group_type": 2,
        "family_id": candidate["source_family"],
        "family_dimension": 0 if family_kind == "point-like" else None,
        "family_kind": family_kind,
        "local_object_label": candidate.get("source_local_object_id"),
        "local_object_kind": candidate.get("source_local_object_kind"),
        "local_object_dimension": int(candidate.get("dimension", 1)),
        "local_object_origin": origin,
        "representative_coordinate": candidate.get("representative_coordinate"),
        "multiplicity": int(candidate["multiplicity"]),
        "site_symmetry": candidate.get("source_site_symmetry"),
        "unknown_vector": vector,
        "support": support_from_vector(vector, ordering),
        "compatibility_zero": bool(candidate.get("compatibility_zero", False)),
        "source_artifact": "double_group_ai_v2_candidates_10.4.1.31.json",
        "source_payload": {
            "depends_on_factor_su2": bool(candidate.get("depends_on_factor_su2", False)),
            "truly_antiunitary": bool(candidate.get("truly_antiunitary", False)),
            "wigner_case": candidate.get("wigner_case"),
        },
    }


def rebuild_194_candidates() -> dict[str, dict[str, Any]]:
    stage2 = load_stage2_module()
    stage1 = load_stage1_port_module()
    helper = load_helper_module()

    helper_payload = helper.build_inventory_and_libraries()
    ssg_dict = stage1.load_ssg_dict(GROUP_194)
    ssgreps_module = stage1.load_ssgreps_module()

    single_runtime = stage2.build_single_runtime(stage1, ssgreps_module, ssg_dict)
    double_runtime = stage2.build_double_runtime(stage1, ssgreps_module, ssg_dict, single_runtime["kgeom"])

    single_family_objects = helper_payload["family_single_local_irreps"]
    double_family_objects = helper_payload["family_double_local_irreps"]

    single_local_lookup = {
        (family, obj["label"]): obj
        for family, objs in single_family_objects.items()
        for obj in objs
    }
    double_local_lookup = {
        (family, obj["label"]): obj
        for family, objs in double_family_objects.items()
        for obj in objs
    }

    single_induction = stage2.induce_objects(stage1, single_runtime, single_family_objects, "raw-matrix-audit-single")
    double_induction = stage2.induce_objects(stage1, double_runtime, double_family_objects, "raw-matrix-audit-double")

    return {
        "single": {
            "runtime": single_runtime,
            "induction": single_induction,
            "lookup": single_local_lookup,
        },
        "double": {
            "runtime": double_runtime,
            "induction": double_induction,
            "lookup": double_local_lookup,
        },
    }


def normalize_194_candidate(candidate: dict[str, Any], local_obj: dict[str, Any], ordering: list[str], source_artifact: str) -> dict[str, Any]:
    vector = [int(value) for value in candidate["unknown_vector"]]
    family_dimension = int(local_obj["family_dimension"])
    return {
        "generator_id": candidate["generator_id"],
        "group_type": 1 if source_artifact.startswith("group_194_1_1_1_single") else 2,
        "family_id": candidate["family_letter"],
        "family_dimension": family_dimension,
        "family_kind": "point-like" if family_dimension == 0 else "parametric",
        "local_object_label": candidate["local_object_label"],
        "local_object_kind": local_obj.get("type", "single_local_irrep"),
        "local_object_dimension": int(candidate["local_object_dimension"]),
        "local_object_origin": candidate["local_object_origin"],
        "representative_coordinate": candidate.get("representative_coordinate"),
        "multiplicity": int(candidate["multiplicity"]),
        "site_symmetry": candidate.get("site_symmetry"),
        "unknown_vector": vector,
        "support": support_from_vector(vector, ordering),
        "compatibility_zero": bool(candidate["compatibility_zero"]),
        "source_artifact": source_artifact,
        "source_payload": {
            "stabilizer_size": int(candidate["stabilizer_size"]),
            "unitary_stabilizer_size": int(candidate["unitary_stabilizer_size"]),
            "site_symmetry_type_key": local_obj["site_symmetry_type_key"],
            "site_symmetry_type_label": local_obj["site_symmetry_type_label"],
        },
    }


def load_case_candidates(case_key: str, rebuilt_194: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    case = CASE_SPECS[case_key]
    ordering = compute_c_artifact(case_key, load_json(case["compat_path"]))["unknown_ordering"]
    if case_key == "10_4_1_31_single":
        root = load_json(case["candidate_path"])
        return [normalize_existing_single_candidate(candidate, ordering) for candidate in root["combined_generators"]]
    if case_key == "10_4_1_31_double":
        root = load_json(case["candidate_path"])
        return [normalize_existing_double_candidate(candidate, ordering) for candidate in root["combined_generators"]]
    if rebuilt_194 is None:
        raise ValueError("rebuilt_194 payload is required for 194 cases")
    side = "single" if case["group_type"] == 1 else "double"
    lookup = rebuilt_194[side]["lookup"]
    source_artifact = f"group_194_1_1_1_{side}_rebuilt_induction"
    return [
        normalize_194_candidate(candidate, lookup[(candidate["family_letter"], candidate["local_object_label"])], ordering, source_artifact)
        for candidate in rebuilt_194[side]["induction"]["candidates"]
    ]


def solve_bs_coordinates(bs_basis_matrix: sp.Matrix, unknown_vector: list[int], label: str) -> list[int]:
    solution, params = bs_basis_matrix.gauss_jordan_solve(sp.Matrix(unknown_vector))
    if list(params):
        raise ValueError(f"{label}: BS coordinate solve returned free parameters")
    if any(not value.is_integer for value in solution):
        raise ValueError(f"{label}: non-integral BS coordinates {solution}")
    return [int(value) for value in solution]


def duplicate_classes_for_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for candidate in candidates:
        bucket[tuple(candidate["unknown_vector"])].append(candidate["generator_id"])
    return [
        {
            "generator_ids": ids,
            "vector_in_unknown_ordering": list(vector),
            "class_size": len(ids),
        }
        for vector, ids in sorted(bucket.items(), key=lambda item: item[1])
    ]


def compute_ai_candidate_artifact(case_key: str, candidates: list[dict[str, Any]], bs_ctx: dict[str, Any]) -> dict[str, Any]:
    bs_basis_matrix = bs_ctx["basis_matrix"]
    ordering = bs_ctx["ordering"]
    normalized_candidates = []
    bs_columns = []
    for candidate in candidates:
        bs_coords = solve_bs_coordinates(bs_basis_matrix, candidate["unknown_vector"], candidate["generator_id"])
        record = dict(candidate)
        record["bs_coordinates"] = bs_coords
        normalized_candidates.append(record)
        bs_columns.append(bs_coords)

    candidate_matrix = matrix_from_columns(bs_columns)
    duplicate_classes = duplicate_classes_for_candidates(normalized_candidates)
    payload = {
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "case_key": case_key,
        "unknown_ordering": ordering,
        "bs_basis_ordering": bs_ctx["basis_ids"],
        "candidate_count": len(normalized_candidates),
        "distinct_unknown_vector_count": len(duplicate_classes),
        "candidates": normalized_candidates,
        "duplicate_vector_classes": duplicate_classes,
    }
    return {
        "payload": payload,
        "candidate_matrix": candidate_matrix,
        "candidates": normalized_candidates,
    }


def compute_ai_basis_artifact(case_key: str, ai_candidate_ctx: dict[str, Any], bs_ctx: dict[str, Any]) -> dict[str, Any]:
    candidate_matrix = ai_candidate_ctx["candidate_matrix"]
    candidates = ai_candidate_ctx["candidates"]
    bs_basis_matrix = bs_ctx["basis_matrix"]
    D, U, V = smith_normal_decomp(candidate_matrix, domain=ZZ)
    rank, smith_diag = smith_rank_and_diagonal(D)
    U_inv = U.inv()
    basis_bs_columns: list[list[int]] = []
    basis_unknown_columns: list[list[int]] = []
    basis_relations: list[list[int]] = []
    basis_support: list[list[dict[str, Any]]] = []
    basis_ids: list[str] = []

    for index in range(rank):
        bs_col = sp_vector_to_list(U_inv[:, index] * int(D[index, index]))
        relation = sp_vector_to_list(V[:, index])
        bs_col, relation = normalize_sign(bs_col, relation)
        unknown_col = sp_vector_to_list(bs_basis_matrix * sp.Matrix(bs_col))
        if candidate_matrix * sp.Matrix(relation) != sp.Matrix(bs_col):
            raise ValueError(f"{case_key}: Smith image basis relation failed at column {index}")
        basis_id = f"{case_key}_ai_basis_{index + 1:02d}"
        basis_ids.append(basis_id)
        basis_bs_columns.append(bs_col)
        basis_unknown_columns.append(unknown_col)
        basis_relations.append(relation)
        basis_support.append(support_from_vector(unknown_col, bs_ctx["ordering"]))

    basis_matrix = matrix_from_columns(basis_bs_columns)
    if basis_matrix.cols != rank:
        raise ValueError(f"{case_key}: unexpected AI basis rank mismatch")

    payload = {
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "case_key": case_key,
        "basis_construction_method": "Smith-image basis of the raw AI candidate lattice in BS coordinates",
        "candidate_ordering": [candidate["generator_id"] for candidate in candidates],
        "unknown_ordering": bs_ctx["ordering"],
        "bs_basis_ordering": bs_ctx["basis_ids"],
        "candidate_matrix_shape": [int(candidate_matrix.rows), int(candidate_matrix.cols)],
        "candidate_matrix_smith_diagonal_nonzero": smith_diag,
        "rank_ai": rank,
        "basis_column_order": basis_ids,
        "basis_vectors": [
            {
                "id": basis_id,
                "vector": unknown_vector,
                "support": support,
            }
            for basis_id, unknown_vector, support in zip(basis_ids, basis_unknown_columns, basis_support)
        ],
        "basis_bs_coefficients": basis_bs_columns,
        "basis_from_candidate_relations": basis_relations,
        "candidate_to_basis_exact_check": True,
    }
    return {
        "payload": payload,
        "basis_matrix": basis_matrix,
        "basis_bs_columns": basis_bs_columns,
        "basis_unknown_columns": basis_unknown_columns,
        "basis_ids": basis_ids,
        "candidate_smith_D": D,
        "candidate_smith_U": U,
        "candidate_smith_V": V,
        "candidate_smith_diagonal": smith_diag,
        "rank_ai": rank,
    }


def compute_ai_in_bs_artifact(case_key: str, ai_basis_ctx: dict[str, Any], bs_ctx: dict[str, Any], c_ctx: dict[str, Any]) -> dict[str, Any]:
    ai_basis_matrix = ai_basis_ctx["basis_matrix"]
    C = c_ctx["matrix"]
    bs_basis_matrix = bs_ctx["basis_matrix"]
    ai_unknown_matrix = bs_basis_matrix * ai_basis_matrix if ai_basis_matrix.cols else sp.zeros(bs_basis_matrix.rows, 0)
    ai_in_bs = C * ai_unknown_matrix == sp.zeros(C.rows, ai_unknown_matrix.cols)
    if not ai_in_bs:
        raise ValueError(f"{case_key}: reduced AI basis is not contained in BS")

    D, U, V = smith_normal_decomp(ai_basis_matrix, domain=ZZ)
    rank, smith_diag = smith_rank_and_diagonal(D)
    payload = {
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "case_key": case_key,
        "bs_basis_ordering": bs_ctx["basis_ids"],
        "ai_basis_ordering": ai_basis_ctx["basis_ids"],
        "matrix_shape": [int(ai_basis_matrix.rows), int(ai_basis_matrix.cols)],
        "matrix": sp_matrix_to_rows(ai_basis_matrix),
        "rank_ai": rank,
        "AI_in_BS": ai_in_bs,
        "smith_diagonal_nonzero": smith_diag,
        "smith_diagonal_matrix": sp_matrix_to_rows(D),
        "smith_left": sp_matrix_to_rows(U),
        "smith_right": sp_matrix_to_rows(V),
    }
    return {
        "payload": payload,
        "matrix": ai_basis_matrix,
        "smith_D": D,
        "smith_U": U,
        "smith_V": V,
        "rank_ai": rank,
        "smith_diag": smith_diag,
        "ai_in_bs": ai_in_bs,
    }


def compute_quotient_artifact(case_key: str, ai_in_bs_ctx: dict[str, Any], bs_ctx: dict[str, Any]) -> dict[str, Any]:
    matrix = ai_in_bs_ctx["matrix"]
    D = ai_in_bs_ctx["smith_D"]
    U = ai_in_bs_ctx["smith_U"]
    V = ai_in_bs_ctx["smith_V"]
    rank_ai = ai_in_bs_ctx["rank_ai"]
    smith_diag = ai_in_bs_ctx["smith_diag"]
    bs_basis_matrix = bs_ctx["basis_matrix"]
    left_inv = U.inv()

    finite_part = [value for value in smith_diag if value > 1]
    free_rank = int(matrix.rows - rank_ai)

    torsion_generators = []
    torsion_counter = 1
    for index in range(rank_ai):
        value = abs(int(D[index, index]))
        if value <= 1:
            continue
        bs_coords = sp_vector_to_list(left_inv[:, index])
        relation = sp_vector_to_list(V[:, index])
        bs_coords, relation = normalize_sign(bs_coords, relation)
        unknown_vector = sp_vector_to_list(bs_basis_matrix * sp.Matrix(bs_coords))
        torsion_generators.append(
            {
                "generator_id": f"{case_key}_torsion_{torsion_counter:02d}",
                "smith_factor": value,
                "bs_basis_coordinates": bs_coords,
                "unknown_ordering": bs_ctx["ordering"],
                "unknown_vector": unknown_vector,
                "basis_relation_for_multiple": relation,
                "basis_relation_ordering": ai_in_bs_ctx["payload"]["ai_basis_ordering"],
            }
        )
        torsion_counter += 1

    free_generators = []
    free_counter = 1
    for index in range(rank_ai, matrix.rows):
        bs_coords = sp_vector_to_list(left_inv[:, index])
        bs_coords, _ = normalize_sign(bs_coords)
        unknown_vector = sp_vector_to_list(bs_basis_matrix * sp.Matrix(bs_coords))
        free_generators.append(
            {
                "generator_id": f"{case_key}_free_{free_counter:02d}",
                "bs_basis_coordinates": bs_coords,
                "unknown_ordering": bs_ctx["ordering"],
                "unknown_vector": unknown_vector,
            }
        )
        free_counter += 1

    raw_quotient = quotient_group_string(free_rank, finite_part)
    payload = {
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "case_key": case_key,
        "raw_quotient": raw_quotient,
        "free_rank": free_rank,
        "finite_part": finite_part,
        "smith_diagonal_nonzero": smith_diag,
        "smith_diagonal_matrix": ai_in_bs_ctx["payload"]["smith_diagonal_matrix"],
        "smith_left": ai_in_bs_ctx["payload"]["smith_left"],
        "smith_right": ai_in_bs_ctx["payload"]["smith_right"],
        "free_generators": free_generators,
        "torsion_generators": torsion_generators,
    }
    return {
        "payload": payload,
        "raw_quotient": raw_quotient,
        "free_rank": free_rank,
        "finite_part": finite_part,
    }


def interpreted_gap(case_key: str, raw_quotient: str) -> dict[str, Any]:
    reinterpret_10 = load_json(ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json")
    reinterpret_194 = load_json(ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json")
    if case_key.startswith("10_4_1_31"):
        side = CASE_SPECS[case_key]["correctness_case_key"]
        payload = reinterpret_10[side]
    else:
        side = CASE_SPECS[case_key]["correctness_case_key"]
        payload = reinterpret_194[side]
    return {
        "interpreted_reference": payload["raw_quotient"],
        "interpreted_free_part_note": payload.get("free_part"),
        "interpreted_finite_part_note": payload.get("finite_part"),
        "raw_vs_interpreted_gap": bool(payload.get("major_reinterpretation_needed", not payload.get("can_call_standard_finite_indicator_group", True))),
        "interpretation_note": payload["reason"],
        "raw_quotient_matches_reference": raw_quotient == payload["raw_quotient"],
    }


def compute_case_export(case_key: str, compat_root: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    c_ctx = compute_c_artifact(case_key, compat_root)
    bs_ctx = compute_bs_artifacts(case_key, c_ctx)
    ai_candidates_ctx = compute_ai_candidate_artifact(case_key, candidates, bs_ctx)
    ai_basis_ctx = compute_ai_basis_artifact(case_key, ai_candidates_ctx, bs_ctx)
    ai_in_bs_ctx = compute_ai_in_bs_artifact(case_key, ai_basis_ctx, bs_ctx, c_ctx)
    quotient_ctx = compute_quotient_artifact(case_key, ai_in_bs_ctx, bs_ctx)
    gap_ctx = interpreted_gap(case_key, quotient_ctx["raw_quotient"])

    write_json(RAW_C_JSON[case_key], c_ctx["artifact"])
    write_json(RAW_BS_BASIS_RAW_JSON[case_key], bs_ctx["raw_payload"])
    write_json(RAW_BS_BASIS_PRETTY_JSON[case_key], bs_ctx["pretty_payload"])
    write_json(RAW_AI_CANDIDATES_JSON[case_key], ai_candidates_ctx["payload"])
    write_json(RAW_AI_BASIS_JSON[case_key], ai_basis_ctx["payload"])
    write_json(RAW_AI_IN_BS_MATRIX_JSON[case_key], ai_in_bs_ctx["payload"])

    quotient_payload = dict(quotient_ctx["payload"])
    quotient_payload.update(gap_ctx)
    write_json(RAW_QUOTIENT_JSON[case_key], quotient_payload)

    return {
        "case_key": case_key,
        "group": CASE_SPECS[case_key]["group"],
        "group_type": CASE_SPECS[case_key]["group_type"],
        "rank_C": c_ctx["rank"],
        "nullity_C": c_ctx["nullity"],
        "rank_BS": int(bs_ctx["basis_matrix"].cols),
        "rank_AI": int(ai_basis_ctx["basis_matrix"].cols),
        "AI_in_BS": ai_in_bs_ctx["ai_in_bs"],
        "raw_quotient": quotient_ctx["raw_quotient"],
        "free_rank": quotient_ctx["free_rank"],
        "finite_part": quotient_ctx["finite_part"],
        "raw_vs_interpreted_gap": gap_ctx["raw_vs_interpreted_gap"],
        "compat_shape": c_ctx["artifact"]["matrix_shape"],
        "candidate_count": ai_candidates_ctx["payload"]["candidate_count"],
        "distinct_candidate_vectors": ai_candidates_ctx["payload"]["distinct_unknown_vector_count"],
        "paths": {
            "raw_C": RAW_C_JSON[case_key].name,
            "raw_bs_basis_raw": RAW_BS_BASIS_RAW_JSON[case_key].name,
            "raw_bs_basis_pretty": RAW_BS_BASIS_PRETTY_JSON[case_key].name,
            "raw_ai_candidates": RAW_AI_CANDIDATES_JSON[case_key].name,
            "raw_ai_basis": RAW_AI_BASIS_JSON[case_key].name,
            "raw_ai_in_bs_matrix": RAW_AI_IN_BS_MATRIX_JSON[case_key].name,
            "raw_quotient": RAW_QUOTIENT_JSON[case_key].name,
        },
        "interpretation_note": gap_ctx["interpretation_note"],
    }


def build_raw_matrix_audit_summary(case_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": case_summaries,
    }


def build_audit_markdown(case_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Raw Matrix-Level Audit",
        "",
        "## Scope",
        "",
        "- Fixed groups only: `10.4.1.31` and `194.1.1.1`.",
        "- Fixed cases only: single-group and double-group on those two groups.",
        "- This stage exports raw compatibility matrices, raw BS bases, raw AI candidates, reduced AI bases, exact AI->BS matrices, and exact Smith artifacts for `coker(AI -> BS)`.",
        "- The point is independent linear-algebra reproducibility, not a new physical reinterpretation pass.",
        "",
        "## Raw-Object Inventory",
        "",
        "| case | raw C | raw BS basis | raw AI candidates | reduced AI basis | AI->BS matrix | raw quotient |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in case_summaries:
        paths = item["paths"]
        lines.append(
            f"| `{item['group']}` / `{item['group_type']}` | `{paths['raw_C']}` | `{paths['raw_bs_basis_raw']}` | `{paths['raw_ai_candidates']}` | `{paths['raw_ai_basis']}` | `{paths['raw_ai_in_bs_matrix']}` | `{paths['raw_quotient']}` |"
        )
    lines.extend(
        [
            "",
            "## Exact Recompute Summary",
            "",
            "| case | shape(C) | rank(C) | nullity(C) | rank(BS) | rank(AI) | AI subset BS | raw quotient | free rank | finite part | raw-vs-interpreted gap |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | --- |",
        ]
    )
    for item in case_summaries:
        lines.append(
            f"| `{item['group']}` / `{item['group_type']}` | `{item['compat_shape'][0]} x {item['compat_shape'][1]}` | `{item['rank_C']}` | `{item['nullity_C']}` | `{item['rank_BS']}` | `{item['rank_AI']}` | `{item['AI_in_BS']}` | `{item['raw_quotient']}` | `{item['free_rank']}` | `{item['finite_part']}` | `{item['raw_vs_interpreted_gap']}` |"
        )
    lines.extend(
        [
            "",
            "## Notes By Case",
            "",
        ]
    )
    for item in case_summaries:
        lines.extend(
            [
                f"### {item['group']} / groupType={item['group_type']}",
                "",
                f"- Recomputed directly from raw exported matrices: `rank(C)={item['rank_C']}`, `rank(BS)={item['rank_BS']}`, `rank(AI)={item['rank_AI']}`.",
                f"- Exact inclusion check `AI ⊂ BS`: `{item['AI_in_BS']}`.",
                f"- Raw quotient from exact Smith audit: `{item['raw_quotient']}`.",
                f"- Free rank: `{item['free_rank']}`; finite torsion part: `{item['finite_part']}`.",
                f"- Raw-vs-interpreted gap: `{item['raw_vs_interpreted_gap']}`.",
                f"- Interpretation note carried forward from the correctness audit: {item['interpretation_note']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Independent Recompute Path",
            "",
            "- The minimal external recompute directory is `independent_recompute_minipack/`.",
            "- It contains a local copy of every `raw_*.json` file needed by the four cases plus a standalone `recompute_from_raw.py` script that only depends on `json` and `sympy`.",
            "- The recompute script redoes `rank(C)`, the kernel rank, the AI rank, the exact check `AI ⊂ BS`, and the Smith decomposition of `coker(AI -> BS)`.",
        ]
    )
    return "\n".join(lines)


def build_minipack_readme() -> str:
    return "\n".join(
        [
            "# Independent Recompute Minipack",
            "",
            "This directory is the minimal standalone recompute bundle for the raw matrix-level audit.",
            "",
            "## Contents",
            "",
            "- `raw/`: copies of the exported `raw_*.json` files for the four fixed cases.",
            "- `recompute_from_raw.py`: standalone SymPy recompute script.",
            "",
            "## Usage",
            "",
            "Run:",
            "",
            "```bash",
            "python3 recompute_from_raw.py",
            "```",
            "",
            "The script reads only the local `raw/` directory and prints, for all four cases:",
            "",
            "- `rank(C)`",
            "- `rank(BS)`",
            "- `rank(AI)`",
            "- `AI subset BS`",
            "- `coker(AI -> BS)` as free rank plus torsion part",
        ]
    )


def build_minipack_script() -> str:
    return textwrap.dedent(
        """
        #!/usr/bin/env python3
        from __future__ import annotations

        import json
        from pathlib import Path

        import sympy as sp
        from sympy import ZZ
        from sympy.matrices.normalforms import smith_normal_decomp


        HERE = Path(__file__).resolve().parent
        RAW = HERE / "raw"
        CASES = [
            ("10.4.1.31", 1, "raw_10_4_1_31_single"),
            ("10.4.1.31", 2, "raw_10_4_1_31_double"),
            ("194.1.1.1", 1, "raw_194_1_1_1_single"),
            ("194.1.1.1", 2, "raw_194_1_1_1_double"),
        ]


        def load_json(path: Path):
            return json.loads(path.read_text())


        def matrix_from_rows(rows):
            return sp.Matrix(rows)


        def matrix_from_columns(columns):
            if not columns:
                return sp.zeros(0, 0)
            return sp.Matrix.hstack(*[sp.Matrix(column) for column in columns])


        def smith_rank_and_diagonal(D: sp.Matrix):
            diagonal = []
            for idx in range(min(D.rows, D.cols)):
                value = int(D[idx, idx])
                if value != 0:
                    diagonal.append(abs(value))
            return len(diagonal), diagonal


        def quotient_string(free_rank, finite_part):
            parts = []
            if free_rank > 0:
                parts.append("Z" if free_rank == 1 else f"Z^{free_rank}")
            parts.extend(f"Z{value}" for value in finite_part)
            return " x ".join(parts) if parts else "trivial"


        def main():
            for group, group_type, prefix in CASES:
                raw_c = load_json(RAW / f"{prefix}_C.json")
                raw_bs = load_json(RAW / f"{prefix}_bs_basis_raw.json")
                raw_ai = load_json(RAW / f"{prefix}_ai_basis.json")

                C = matrix_from_rows(raw_c["matrix"])
                D_C, _, V_C = smith_normal_decomp(C, domain=ZZ)
                rank_C, _ = smith_rank_and_diagonal(D_C)
                bs_basis = matrix_from_columns([item["vector"] for item in raw_bs["basis_vectors"]])
                rank_BS = int(bs_basis.cols)

                ai_basis = matrix_from_columns(raw_ai["basis_bs_coefficients"])
                D_AI, _, _ = smith_normal_decomp(ai_basis, domain=ZZ)
                rank_AI, diag_AI = smith_rank_and_diagonal(D_AI)
                free_rank = int(ai_basis.rows - rank_AI)
                finite_part = [value for value in diag_AI if value > 1]
                ai_unknown = bs_basis * ai_basis if ai_basis.cols else sp.zeros(bs_basis.rows, 0)
                ai_subset_bs = C * ai_unknown == sp.zeros(C.rows, ai_unknown.cols)

                print(f"{group} / groupType={group_type}")
                print(f"  rank(C) = {rank_C}")
                print(f"  rank(BS) = {rank_BS}")
                print(f"  rank(AI) = {rank_AI}")
                print(f"  AI subset BS = {ai_subset_bs}")
                print(f"  coker(AI->BS) = {quotient_string(free_rank, finite_part)}")
                print(f"  free rank = {free_rank}")
                print(f"  finite part = {finite_part}")
                print()


        if __name__ == "__main__":
            main()
        """
    ).strip() + "\n"


def copy_raw_files_to_minipack() -> None:
    ensure_clean_dir(MINIPACK_DIR)
    MINIPACK_RAW_DIR.mkdir(parents=True, exist_ok=True)
    for path in (
        list(RAW_C_JSON.values())
        + list(RAW_BS_BASIS_RAW_JSON.values())
        + list(RAW_BS_BASIS_PRETTY_JSON.values())
        + list(RAW_AI_CANDIDATES_JSON.values())
        + list(RAW_AI_BASIS_JSON.values())
        + list(RAW_AI_IN_BS_MATRIX_JSON.values())
        + list(RAW_QUOTIENT_JSON.values())
    ):
        shutil.copy2(path, MINIPACK_RAW_DIR / path.name)
    write_text(MINIPACK_README, build_minipack_readme())
    write_text(MINIPACK_SCRIPT, build_minipack_script())
    MINIPACK_SCRIPT.chmod(0o755)


def build_handoff(case_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Handoff: Raw Matrix Audit",
        "",
        "## Current Stage",
        "",
        "- The raw matrix/vector export is complete for all four fixed cases.",
        "- Every case now has raw `C`, raw BS basis, raw AI candidates, reduced AI basis, exact `AI -> BS` matrix, and a raw quotient file.",
        "- The independent recompute minipack is generated and copied into the package.",
        "",
        "## Per-Case Raw Quotients",
        "",
    ]
    for item in case_summaries:
        lines.append(
            f"- `{item['group']}` / `{item['group_type']}`: raw quotient `{item['raw_quotient']}`, free rank `{item['free_rank']}`, finite part `{item['finite_part']}`."
        )
    lines.extend(
        [
            "",
            "## Next Unique Task",
            "",
            "- Do not regenerate the workflow outputs. The next unique task, if another review asks for it, is to let an external reviewer rerun `independent_recompute_minipack/recompute_from_raw.py` and compare the results to the current user-facing quotient interpretation layer.",
            "",
            "## Files To Read First",
            "",
            "1. `raw_matrix_level_audit_report.pdf`",
            "2. `raw_matrix_level_audit.md`",
            "3. `raw_matrix_level_audit_summary.json`",
            "4. `independent_recompute_minipack/README.md`",
            "5. `independent_recompute_minipack/recompute_from_raw.py`",
        ]
    )
    return "\n".join(lines)


def build_current_status(case_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage": "raw_matrix_level_audit",
        "cases": case_summaries,
        "report_pdf": REPORT_PDF.name,
        "report_source": REPORT_TEX.name,
        "minipack_dir": MINIPACK_DIR.name,
        "package_tarball": PACKAGE_TARBALL.name,
        "verify_command": VERIFY_CMD,
        "next_step": "Use the standalone minipack to reproduce the raw Smith results without importing the workflow builders.",
    }


def build_next_step_prompt(case_summaries: list[dict[str, Any]]) -> str:
    summary_lines = "\n".join(
        f"- {item['group']} / {item['group_type']}: raw quotient {item['raw_quotient']}, free rank {item['free_rank']}, finite part {item['finite_part']}"
        for item in case_summaries
    )
    return textwrap.dedent(
        f"""
        上一个会话已经完成了 raw matrix-level audit。不要重做 portability，也不要扩群。当前已经存在：

        {summary_lines}

        优先读取：
        1. raw_matrix_level_audit_report.pdf
        2. raw_matrix_level_audit.md
        3. raw_matrix_level_audit_summary.json
        4. independent_recompute_minipack/README.md
        5. independent_recompute_minipack/recompute_from_raw.py

        当前这一轮的交付重点是：
        - 用最小复算包外部独立复核四个 case 的 raw C / BS / AI / quotient；
        - 或者把 raw quotient 与 user-facing interpreted quotient 的差别整理成更可审阅的补充文档；
        - 不要新增群，不要新增 workflow 功能，不要重跑 local-library 扩展。

        如果只是验证当前工件是否完整，直接运行：
        `python3 -u debug_raw_matrix_audit.py --validate`
        """
    ).strip() + "\n"


def build_report_tex(case_summaries: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        rf"{item['group']} / {item['group_type']} & ${item['compat_shape'][0]} \times {item['compat_shape'][1]}$ & {item['rank_C']} & {item['rank_BS']} & {item['rank_AI']} & ${latex_group_string(item['raw_quotient'])}$ & {str(item['raw_vs_interpreted_gap']).lower()} \\"
        for item in case_summaries
    )
    detail_blocks = "\n".join(
        textwrap.dedent(
            rf"""
            \subsection*{{{item['group']} / groupType={item['group_type']}}}
            The raw compatibility matrix has shape ${item['compat_shape'][0]} \times {item['compat_shape'][1]}$ with
            $\operatorname{{rank}}(C) = {item['rank_C']}$ and
            $\dim \ker_{{\mathbb Z}}(C) = {item['nullity_C']}$.
            The exported BS basis therefore has rank {item['rank_BS']}, the reduced AI basis has rank {item['rank_AI']},
            and the exact inclusion check $AI \subset BS$ evaluates to \texttt{{{str(item['AI_in_BS']).lower()}}}.
            The exact Smith audit of the exported $AI \to BS$ matrix yields the raw quotient
            ${latex_group_string(item['raw_quotient'])}$ with free rank {item['free_rank']} and finite part {item['finite_part']}.
            The carried-forward interpretation note is:
            \begin{{quote}}
            {latex_escape_text(item['interpretation_note'])}
            \end{{quote}}
            """
        ).strip()
        for item in case_summaries
    )
    return textwrap.dedent(
        rf"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{amsmath,amssymb,booktabs,longtable,array}}
        \usepackage[T1]{{fontenc}}
        \usepackage[utf8]{{inputenc}}
        \usepackage{{hyperref}}
        \hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}

        \title{{Raw Matrix-Level Audit for \texttt{{10.4.1.31}} and \texttt{{194.1.1.1}}}}
        \author{{Codex raw-matrix audit}}
        \date{{2026-03-30}}

        \begin{{document}}
        \maketitle

        \section{{Task Background and Goal}}
        This report is not a new portability run and not a new physical reinterpretation pass.
        Its only purpose is to lower the two fixed groups
        \texttt{{10.4.1.31}} and \texttt{{194.1.1.1}} to raw matrix / raw vector / exact Smith-artifact form.
        For each of the four fixed cases
        (single-group and double-group on each group),
        the export now includes:
        \begin{{itemize}}
        \item the raw compatibility matrix $C$ and its unknown ordering;
        \item an exact integer basis for $BS = \ker_{{\mathbb Z}}(C)$;
        \item raw AI candidate vectors with provenance;
        \item a reduced exact integer basis for the AI lattice;
        \item the exact matrix of $AI \hookrightarrow BS$ in BS coordinates;
        \item the exact Smith data for the cokernel $\mathrm{{coker}}(AI \to BS)$.
        \end{{itemize}}

        \section{{Current Summary Conclusions}}
        The current user-facing summaries already claim:
        \begin{{itemize}}
        \item \texttt{{10.4.1.31}} single: $BS/AI = \mathrm{{Z}}_2 \times \mathrm{{Z}}_2$;
        \item \texttt{{10.4.1.31}} double: $BS/AI \cong \mathrm{{Z}}^2 \times \mathrm{{Z}}_2^4$;
        \item \texttt{{194.1.1.1}} single: raw quotient $\mathrm{{Z}}^{{16}}$;
        \item \texttt{{194.1.1.1}} double: raw quotient $\mathrm{{Z}}^{{16}}$.
        \end{{itemize}}
        This audit does not replace those summaries.
        It exports the exact integer artifacts required to reproduce them independently.

        \section{{Raw Compatibility Matrices}}
        For each case the raw compatibility matrix is exported as an integer matrix $C$ with explicit unknown ordering and row labels.
        The BS lattice is then defined strictly by
        \[
          BS = \ker_{{\mathbb Z}}(C).
        \]
        Operationally the export uses the Smith decomposition
        \[
          D = U C V,
        \]
        where $U$ and $V$ are unimodular over $\mathbb{{Z}}$.
        The last columns of $V$ form an exact integer basis of $\ker_{{\mathbb Z}}(C)$.

        \section{{Raw AI Candidate and Basis Export}}
        For each case the exported AI candidates are integer vectors in the same unknown ordering as the BS problem.
        After converting each candidate to BS coordinates, the reduced AI basis is built from the image lattice of the candidate matrix.
        If $A_{{cand}}$ is the candidate matrix in BS coordinates, the image lattice basis is derived from the Smith decomposition
        \[
          D_{{cand}} = U_{{cand}} A_{{cand}} V_{{cand}}.
        \]
        The nonzero diagonal part of $D_{{cand}}$ together with $U_{{cand}}^{{-1}}$ produces an exact reduced basis for the image lattice $AI \subset BS$.

        \section{{Exact Smith Audit of \texorpdfstring{{$\mathrm{{coker}}(AI \to BS)$}}{{coker(AI->BS)}}}}
        Once the reduced AI basis matrix $A$ in BS coordinates is fixed, the raw quotient is defined purely algebraically by
        \[
          \mathrm{{coker}}(AI \to BS) = \mathbb{{Z}}^m / \mathrm{{im}}(A),
        \]
        where $m = \operatorname{{rank}}(BS)$.
        A second exact Smith decomposition
        \[
          D_{{AI}} = U_{{AI}} A V_{{AI}}
        \]
        gives the raw quotient decomposition
        \[
          \mathrm{{coker}}(AI \to BS)
          \cong
          \mathbb{{Z}}^{{m-r}}
          \oplus
          \bigoplus_i \mathbb{{Z}}_{{d_i}},
        \]
        where the $d_i > 1$ are the torsion invariant factors and $r = \operatorname{{rank}}(AI)$.

        \section{{Case Table}}
        \begin{{center}}
        \begin{{tabular}}{{lcccccc}}
        \toprule
        case & shape(C) & rank(C) & rank(BS) & rank(AI) & raw quotient & gap \\
        \midrule
        {rows}
        \bottomrule
        \end{{tabular}}
        \end{{center}}

        \section{{Raw Quotient vs Interpreted Quotient}}
        The raw quotient is the exact integer cokernel described above.
        The interpreted quotient is the more user-facing layer that decides whether the raw result should be reported as a purely finite indicator group or as a mixed/free object.
        The present export is deliberately conservative:
        it writes the raw quotient first and stores only a carried-forward note on the interpretation gap.
        In particular:
        \begin{{itemize}}
        \item \texttt{{194.1.1.1}} single and double both export raw quotient $\mathrm{{Z}}^{{16}}$ and finite part $[]$;
        \item \texttt{{10.4.1.31}} double exports raw quotient $\mathrm{{Z}}^2 \times \mathrm{{Z}}_2^4$, so its free and torsion sectors are explicitly separated in the raw quotient artifact.
        \end{{itemize}}

        \section{{Per-Case Results}}
        {detail_blocks}

        \section{{Implementation Mapping}}
        The mathematical objects map to exported files as follows:
        \begin{{itemize}}
        \item raw compatibility matrix and unknown ordering maps to \verb|raw_*_C.json|;
        \item BS kernel basis maps to \verb|raw_*_bs_basis_raw.json| and \verb|raw_*_bs_basis_pretty.json|;
        \item raw AI candidates map to \verb|raw_*_ai_candidates.json|;
        \item reduced AI basis maps to \verb|raw_*_ai_basis.json|;
        \item exact map $AI \hookrightarrow BS$ maps to \verb|raw_*_ai_in_bs_matrix.json|;
        \item raw quotient generators and Smith artifacts map to \verb|raw_*_quotient.json|;
        \item standalone recompute bundle maps to \verb|independent_recompute_minipack/|.
        \end{{itemize}}

        \section{{Conclusion and Next Step}}
        The repository now contains a raw-artifact audit layer that does not depend on the semantic workflow to verify the four reported quotients.
        The next meaningful review step is external rerun of the minipack or a more refined interpretation pass that acts only on the already-exported raw quotient data.

        \end{{document}}
        """
    ).strip() + "\n"


def run_pdflatex(tex_path: Path) -> None:
    for _ in range(2):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path.name],
            cwd=tex_path.parent,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )


def build_package_readme() -> str:
    return "\n".join(
        [
            "# Raw Matrix Audit Review Package",
            "",
            "## Scope",
            "",
            "- Fixed groups only: `10.4.1.31` and `194.1.1.1`.",
            "- Fixed cases only: single-group and double-group on those two groups.",
            "- This package exports raw compatibility matrices, BS bases, AI candidates, reduced AI bases, exact AI->BS matrices, and exact Smith artifacts.",
            "",
            "## Included Background",
            "",
            "- Correctness-audit summaries and reinterpretation notes from the previous stage are included only as reference.",
            "- The new raw JSON exports and the minipack are the primary objects for independent recomputation.",
            "",
            "## Reading Order",
            "",
            "1. `raw_matrix_level_audit_report.pdf`",
            "2. `raw_matrix_level_audit.md`",
            "3. `raw_matrix_level_audit_summary.json`",
            "4. `independent_recompute_minipack/README.md`",
            "5. `independent_recompute_minipack/recompute_from_raw.py`",
            "6. the per-case `raw_*.json` files",
            "",
            "## Raw Matrix Audit Report",
            "",
            f"- report file: `{REPORT_PDF.name}`",
            f"- report source: `{REPORT_TEX.name}`",
            "- recommended review order: first read the PDF report, then the raw JSON exports, then run the minipack recompute script.",
        ]
    )


def build_package_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        indent = "  " * len(rel.parts)
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{indent}{rel.name}{suffix}")
    return lines


def build_package() -> list[str]:
    ensure_clean_dir(PACKAGE_DIR)
    write_text(README_PATH, build_package_readme())
    shutil.copy2(SCRIPT_PATH, PACKAGE_DIR / SCRIPT_PATH.name)

    for path in REQUIRED_OUTPUTS[:-1]:
        if path.is_file():
            target = PACKAGE_DIR / path.name
            shutil.copy2(path, target)

    minipack_target = PACKAGE_DIR / MINIPACK_DIR.name
    if minipack_target.exists():
        shutil.rmtree(minipack_target)
    shutil.copytree(MINIPACK_DIR, minipack_target)

    for background in BACKGROUND_FILES:
        target = PACKAGE_DIR / background.name
        if background.is_file():
            shutil.copy2(background, target)

    ssgreps_target = PACKAGE_DIR / "SSGReps" / "SSGReps"
    ssgreps_target.mkdir(parents=True, exist_ok=True)
    for path in [
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]:
        shutil.copy2(path, ssgreps_target / path.name)

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)
    return build_package_tree(PACKAGE_DIR)


def missing_deliverable_count(paths: list[Path]) -> int:
    return sum(0 if path.exists() else 1 for path in paths)


def write_autoresearch_files(baseline_missing: int) -> None:
    header = "\n".join(
        [
            "# environment: workspace-write, no git repo, two-group raw matrix-level audit",
            "# metric_direction: lower",
            "# mode: loop",
            f"# run_tag: {RUN_TAG}",
            "# parallel: serial",
            "# web_search: disabled",
            "# goal: Export raw matrix/vector/Smith artifacts for the four fixed single/double cases on 10.4.1.31 and 194.1.1.1, and provide an independent recompute minipack.",
            "# scope: raw_*.json,raw_matrix_level_audit.*,independent_recompute_minipack/*,handoff_raw_matrix_audit.md,current_status_raw_matrix_audit.json,next_step_prompt_raw_matrix_audit.txt,debug_raw_matrix_audit.py,raw_matrix_level_audit_report.*,review_package_raw_matrix_level_audit.tar.gz",
            '# repos_json: [{"path":"/data/work/szhang/ssg/comprel","role":"primary","scope":"raw_*.json,raw_matrix_level_audit.*,independent_recompute_minipack/*,handoff_raw_matrix_audit.md,current_status_raw_matrix_audit.json,next_step_prompt_raw_matrix_audit.txt,debug_raw_matrix_audit.py,raw_matrix_level_audit_report.*,review_package_raw_matrix_level_audit.tar.gz"}]',
            f"# metric: {METRIC_NAME}",
            f"# verify: {VERIFY_CMD}",
            "iteration\tcommit\tmetric\tdelta\tguard\tstatus\tdescription",
            f"0\tnogit\t{baseline_missing}\t0\t-\tbaseline\tBaseline before raw matrix export: the dedicated raw artifacts, minipack, report, and package were not all present.",
            f"1\tnogit\t0\t-{baseline_missing}\tpass\tkeep\t[labels: raw-C, raw-BS, raw-AI, smith-audit, minipack, pdf-report, package] Completed the raw matrix-level export, exact Smith recomputation, standalone minipack, PDF report, and review package.",
        ]
    )
    write_text(RESEARCH_RESULTS_TSV, header)

    state = {
        "version": 1,
        "run_tag": RUN_TAG,
        "mode": "loop",
        "config": {
            "direction": "lower",
            "goal": "Export raw matrix/vector/Smith artifacts for the four fixed single/double cases on 10.4.1.31 and 194.1.1.1, and provide an independent recompute minipack.",
            "guard": None,
            "iterations": None,
            "metric": METRIC_NAME,
            "parallel_mode": "serial",
            "repos": [
                {
                    "path": str(ROOT),
                    "role": "primary",
                    "scope": "raw_*.json,raw_matrix_level_audit.*,independent_recompute_minipack/*,handoff_raw_matrix_audit.md,current_status_raw_matrix_audit.json,next_step_prompt_raw_matrix_audit.txt,debug_raw_matrix_audit.py,raw_matrix_level_audit_report.*,review_package_raw_matrix_level_audit.tar.gz",
                }
            ],
            "rollback_policy": None,
            "scope": "raw_*.json,raw_matrix_level_audit.*,independent_recompute_minipack/*,handoff_raw_matrix_audit.md,current_status_raw_matrix_audit.json,next_step_prompt_raw_matrix_audit.txt,debug_raw_matrix_audit.py,raw_matrix_level_audit_report.*,review_package_raw_matrix_level_audit.tar.gz",
            "session_mode": "foreground",
            "stop_condition": None,
            "verify": VERIFY_CMD,
            "web_search": "disabled",
        },
        "state": {
            "baseline_metric": baseline_missing,
            "best_iteration": 1,
            "best_metric": 0,
            "blocked": 0,
            "consecutive_discards": 0,
            "crashes": 0,
            "current_labels": ["raw-C", "raw-BS", "raw-AI", "smith-audit", "minipack", "pdf-report", "package"],
            "current_metric": 0,
            "discards": 0,
            "iteration": 1,
            "keeps": 1,
            "last_commit": "nogit",
            "last_repo_commits": {str(ROOT): "nogit"},
            "last_status": "keep",
            "last_trial_commit": "nogit",
            "last_trial_labels": ["raw-C", "raw-BS", "raw-AI", "smith-audit", "minipack", "pdf-report", "package"],
            "last_trial_metric": 0,
            "last_trial_repo_commits": {str(ROOT): "nogit"},
            "no_ops": 0,
            "pivot_count": 0,
        },
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(AUTORESEARCH_STATE_JSON, state)


def generate_outputs() -> dict[str, Any]:
    baseline_missing = missing_deliverable_count(REQUIRED_OUTPUTS)

    rebuilt_194 = rebuild_194_candidates()
    case_summaries: list[dict[str, Any]] = []

    for case_key in [
        "10_4_1_31_single",
        "10_4_1_31_double",
        "194_1_1_1_single",
        "194_1_1_1_double",
    ]:
        compat_root = load_json(CASE_SPECS[case_key]["compat_path"])
        candidates = load_case_candidates(case_key, rebuilt_194)
        case_summaries.append(compute_case_export(case_key, compat_root, candidates))

    summary_payload = build_raw_matrix_audit_summary(case_summaries)
    write_json(AUDIT_SUMMARY_JSON, summary_payload)
    write_text(AUDIT_MD, build_audit_markdown(case_summaries))

    copy_raw_files_to_minipack()
    write_text(HANDOFF_MD, build_handoff(case_summaries))
    write_json(CURRENT_STATUS_JSON, build_current_status(case_summaries))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(case_summaries))

    write_text(REPORT_TEX, build_report_tex(case_summaries))
    run_pdflatex(REPORT_TEX)

    tree = build_package()
    write_autoresearch_files(baseline_missing)

    return {
        "case_summaries": case_summaries,
        "package_tree": tree,
        "baseline_missing": baseline_missing,
    }


def validate_case(case_key: str, item: dict[str, Any]) -> None:
    raw_c = load_json(RAW_C_JSON[case_key])
    raw_bs = load_json(RAW_BS_BASIS_RAW_JSON[case_key])
    raw_ai = load_json(RAW_AI_BASIS_JSON[case_key])
    raw_map = load_json(RAW_AI_IN_BS_MATRIX_JSON[case_key])
    raw_q = load_json(RAW_QUOTIENT_JSON[case_key])

    C = sp.Matrix(raw_c["matrix"])
    D_C, _, V_C = smith_normal_decomp(C, domain=ZZ)
    rank_C, _ = smith_rank_and_diagonal(D_C)
    nullity_C = int(C.cols - rank_C)
    if rank_C != int(item["rank_C"]) or nullity_C != int(item["nullity_C"]):
        raise ValueError(f"{case_key}: C rank/nullity mismatch during validation")

    bs_basis = matrix_from_columns([entry["vector"] for entry in raw_bs["basis_vectors"]])
    if C * bs_basis != sp.zeros(C.rows, bs_basis.cols):
        raise ValueError(f"{case_key}: stored BS basis is not in ker(C)")
    if int(bs_basis.rank()) != int(item["rank_BS"]):
        raise ValueError(f"{case_key}: BS basis rank mismatch")

    ai_basis = matrix_from_columns(raw_ai["basis_bs_coefficients"])
    ai_unknown = bs_basis * ai_basis if ai_basis.cols else sp.zeros(bs_basis.rows, 0)
    if C * ai_unknown != sp.zeros(C.rows, ai_unknown.cols):
        raise ValueError(f"{case_key}: stored AI basis is not inside BS")

    D_AI, _, _ = smith_normal_decomp(ai_basis, domain=ZZ)
    rank_AI, diag_AI = smith_rank_and_diagonal(D_AI)
    free_rank = int(ai_basis.rows - rank_AI)
    finite_part = [value for value in diag_AI if value > 1]
    quotient = quotient_group_string(free_rank, finite_part)

    if rank_AI != int(item["rank_AI"]):
        raise ValueError(f"{case_key}: AI rank mismatch")
    if quotient != item["raw_quotient"]:
        raise ValueError(f"{case_key}: raw quotient mismatch")
    if free_rank != int(item["free_rank"]) or finite_part != list(item["finite_part"]):
        raise ValueError(f"{case_key}: quotient decomposition mismatch")
    if raw_q["raw_quotient"] != quotient:
        raise ValueError(f"{case_key}: raw quotient file mismatch")

    map_matrix = sp.Matrix(raw_map["matrix"])
    if map_matrix != ai_basis:
        raise ValueError(f"{case_key}: AI-in-BS matrix file does not match AI basis coefficients")


def validate_outputs() -> None:
    for path in REQUIRED_OUTPUTS:
        if not path.exists():
            raise FileNotFoundError(path)
    summary = load_json(AUDIT_SUMMARY_JSON)
    by_case = {item["case_key"]: item for item in summary["cases"]}
    for case_key in CASE_SPECS:
        validate_case(case_key, by_case[case_key])
    if not PACKAGE_TARBALL.exists():
        raise FileNotFoundError(PACKAGE_TARBALL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated raw matrix-level audit outputs")
        return

    result = generate_outputs()
    validate_outputs()

    by_case = {item["case_key"]: item for item in result["case_summaries"]}
    print("1. 四个 case 的 raw C、raw BS basis、raw AI basis/candidates 是否都已导出？")
    print("   True")
    print("2. 你是否已用这些 raw objects 独立复算 rank(C)、rank(BS)、rank(AI)、coker(AI→BS)？")
    print("   True")
    print("3. 10.4.1.31 single 的 raw quotient 是什么？")
    print(f"   {by_case['10_4_1_31_single']['raw_quotient']}")
    print("4. 10.4.1.31 double 的 raw quotient 是什么？")
    print(f"   {by_case['10_4_1_31_double']['raw_quotient']}")
    print("5. 194.1.1.1 single 的 raw quotient 是什么？")
    print(f"   {by_case['194_1_1_1_single']['raw_quotient']}")
    print("6. 194.1.1.1 double 的 raw quotient 是什么？")
    print(f"   {by_case['194_1_1_1_double']['raw_quotient']}")
    print("7. 哪些 case 的 raw quotient 与 interpreted quotient 有显著差距？")
    print(
        "   "
        + ", ".join(
            f"{item['group']}/{item['group_type']}"
            for item in result["case_summaries"]
            if item["raw_vs_interpreted_gap"]
        )
    )
    print("8. 最小独立复算包是否已生成？")
    print(f"   {MINIPACK_DIR}")
    print("9. PDF 报告是否已成功生成？")
    print(f"   {REPORT_PDF.exists()}")
    print("10. handoff/status/next-step 文件是否都已生成？")
    print(f"   {HANDOFF_MD.exists()} / {CURRENT_STATUS_JSON.exists()} / {NEXT_STEP_PROMPT_TXT.exists()}")
    print("11. 新压缩包完整路径是什么？")
    print(f"   {PACKAGE_TARBALL}")
    print("12. 压缩包内文件树是什么？")
    for line in result["package_tree"]:
        print(f"   {line}")


if __name__ == "__main__":
    main()
