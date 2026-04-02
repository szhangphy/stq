#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import sympy as sp


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2 import generic_builders as gb
from sg194.pipeline_v2.utils import now_iso, reset_dir, tar_directory, write_json, write_text


GROUP = "194.1.1.1"
SG194_DIR = REPO_ROOT / "sg194"
VARIANTS = ("coarse", "intrinsic", "extrinsic")
MODES = ("single", "double")

COMPARE_JSON = SG194_DIR / "sg194_intrinsic_vs_extrinsic_builder_compare_v1.json"
ROW_PROVENANCE_JSON = SG194_DIR / "sg194_line_row_provenance_audit_v1.json"
L2_L3_AUDIT_MD = SG194_DIR / "sg194_l2_l3_focus_audit_v1.md"
AI_REJECTION_JSON = SG194_DIR / "sg194_ai_rejection_row_provenance_v1.json"
SINGLE_RESULT_JSON = SG194_DIR / "sg194_194_single_generic_final_result_v3.json"
DOUBLE_RESULT_JSON = SG194_DIR / "sg194_194_double_generic_final_result_v3.json"
CONSISTENCY_JSON = SG194_DIR / "sg194_consistency_check_v1.json"

LINE_AUDIT_V2_JSON = SG194_DIR / "sg194_line_restriction_class_audit_v2.json"
LINE_AUDIT_V2_MD = SG194_DIR / "sg194_line_restriction_class_audit_v2.md"
SINGLE_VARIANTS_JSON = SG194_DIR / "sg194_194_single_line_compatibility_variants_v1.json"
DOUBLE_VARIANTS_JSON = SG194_DIR / "sg194_194_double_line_compatibility_variants_v1.json"

RUN_STDOUT = SG194_DIR / "sg194_intrinsic_extrinsic_audit_v1.stdout"
RUN_STDERR = SG194_DIR / "sg194_intrinsic_extrinsic_audit_v1.stderr"
RUN_COMMANDS = SG194_DIR / "sg194_intrinsic_extrinsic_audit_v1.commands.txt"
RUN_GIT_STATUS = SG194_DIR / "sg194_intrinsic_extrinsic_audit_v1.git_status.txt"
RUN_COMMIT = SG194_DIR / "sg194_intrinsic_extrinsic_audit_v1.commit.txt"

PACKAGE_DIR = SG194_DIR / "review_package_sg194_intrinsic_extrinsic_audit_v1"
PACKAGE_TARBALL = SG194_DIR / "review_package_sg194_intrinsic_extrinsic_audit_v1.tar.gz"


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_context(mode: str) -> dict[str, Any]:
    port = gb.stage1_backend()
    module = gb.ssgreps_module()
    shared = gb.shared_geometry_bundle(GROUP)
    ssg_dict = port.load_ssg_dict(GROUP)
    ctx = port.load_context(module, GROUP, mode, ssg_dict)
    ctx["kgeom"] = shared["kgeom"]
    captures = port.build_manifold_capture(module, GROUP, ssg_dict, ctx, mode, shared["kgeom"])
    captures, line_capture_canonicalization = gb._canonicalize_line_captures(
        module,
        GROUP,
        ssg_dict,
        ctx,
        mode,
        shared["grouped"],
        captures,
    )
    local_library = gb._build_local_irrep_library(ctx, mode)
    return {
        "mode": mode,
        "port": port,
        "shared": shared,
        "ctx": ctx,
        "captures": captures,
        "local_library": local_library,
        "line_capture_canonicalization": line_capture_canonicalization,
    }


def build_variant_record(mode_ctx: dict[str, Any], variant: str) -> dict[str, Any]:
    port = mode_ctx["port"]
    shared = mode_ctx["shared"]
    compatibility = gb._build_generic_compatibility(
        GROUP,
        shared["grouped"],
        shared["all_point_ids"],
        mode_ctx["captures"],
        builder_variant=variant,
    )
    bs_analysis = port.analyze_kernel(compatibility)
    induced = gb._induce_all_candidates(
        mode_ctx["ctx"],
        mode_ctx["captures"],
        compatibility,
        bs_analysis["unknown_ordering"],
        mode_ctx["local_library"],
    )
    quotient = gb._build_quotient_from_candidates(
        shared["target_point_ids"],
        bs_analysis["unknown_ordering"],
        bs_analysis,
        compatibility,
        induced,
    )
    return {
        "mode": mode_ctx["mode"],
        "builder_variant": variant,
        "shared": shared,
        "compatibility": compatibility,
        "bs_analysis": bs_analysis,
        "induced": induced,
        "quotient": quotient,
        "line_capture_canonicalization": mode_ctx["line_capture_canonicalization"],
    }


def basis_matrix(bs_analysis: dict[str, Any]) -> sp.Matrix:
    vectors = [sp.Matrix(item["vector"]) for item in bs_analysis["basis_vectors"]]
    if not vectors:
        return sp.zeros(len(bs_analysis["unknown_ordering"]), 0)
    return sp.Matrix.hstack(*vectors)


def _independent_columns(columns: list[sp.Matrix], rows: int) -> sp.Matrix:
    if not columns:
        return sp.zeros(rows, 0)
    selected: list[sp.Matrix] = []
    for column in columns:
        candidate = sp.Matrix.hstack(*(selected + [column]))
        if not selected or candidate.rank() > sp.Matrix.hstack(*selected).rank():
            selected.append(column)
    if not selected:
        return sp.zeros(rows, 0)
    return sp.Matrix.hstack(*selected)


def intersection_basis(left: sp.Matrix, right: sp.Matrix) -> sp.Matrix:
    if left.cols == 0 or right.cols == 0:
        return sp.zeros(left.rows, 0)
    combined = left.row_join(-right)
    candidates: list[sp.Matrix] = []
    for nullvec in combined.nullspace():
        coeffs = nullvec[: left.cols, :]
        candidate = left * coeffs
        if any(value != 0 for value in candidate):
            candidates.append(candidate)
    return _independent_columns(candidates, left.rows)


def complement_basis(big: sp.Matrix, sub: sp.Matrix) -> sp.Matrix:
    rows = big.rows
    intersection = intersection_basis(big, sub)
    intersection_cols = [intersection[:, i] for i in range(intersection.cols)]
    selected = list(intersection_cols)
    extras: list[sp.Matrix] = []
    for index in range(big.cols):
        column = big[:, index]
        trial = selected + [column]
        rank_before = sp.Matrix.hstack(*selected).rank() if selected else 0
        rank_after = sp.Matrix.hstack(*trial).rank()
        if rank_after > rank_before:
            selected.append(column)
            if len(selected) > len(intersection_cols):
                extras.append(column)
    return _independent_columns(extras, rows)


def vector_support_summary(vector: sp.Matrix, unknown_ordering: list[str]) -> dict[str, Any]:
    nonzero = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for coeff, unknown in zip(list(vector), unknown_ordering):
        coeff_int = int(coeff)
        if coeff_int == 0:
            continue
        family = unknown.split("_R", 1)[0]
        grouped.setdefault(family, []).append({"unknown": unknown, "coeff": coeff_int})
        nonzero.append(family)
    return {
        "nonzero_points": sorted(set(nonzero)),
        "per_point": grouped,
    }


def complement_summary(
    label: str,
    big_record: dict[str, Any],
    sub_record: dict[str, Any],
) -> dict[str, Any]:
    big_basis = basis_matrix(big_record["bs_analysis"])
    sub_basis = basis_matrix(sub_record["bs_analysis"])
    complement = complement_basis(big_basis, sub_basis)
    support = [
        {
            "direction_id": f"{label}_{index + 1:02d}",
            **vector_support_summary(complement[:, index], big_record["bs_analysis"]["unknown_ordering"]),
        }
        for index in range(complement.cols)
    ]
    intersection = intersection_basis(big_basis, sub_basis)
    return {
        "label": label,
        "dimension": int(complement.cols),
        "big_nullity": int(big_basis.cols),
        "sub_nullity": int(sub_basis.cols),
        "subspace_containment": int(intersection.cols) == int(sub_basis.cols),
        "support": support,
    }


def line_row_counts(record: dict[str, Any]) -> dict[str, int]:
    return {block["line_id"]: len(block["matrix_rows"]) for block in record["compatibility"]["line_blocks"]}


def compatibility_variant_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "builder_variant": record["builder_variant"],
        "compatibility_builder_kind": record["compatibility"]["compatibility_builder_kind"],
        "matrix_shape": record["compatibility"]["matrix_shape"],
        "line_blocks": record["compatibility"]["line_blocks"],
        "plane_blocks": [
            {
                "plane_id": block["plane_id"],
                "row_count": len(block["matrix_rows"]),
                "equation_count": len(block["equations"]),
                "status": block["status"],
            }
            for block in record["compatibility"]["plane_blocks"]
        ],
        "line_builder_compare": record["compatibility"]["line_builder_compare"],
        "line_capture_canonicalization": record["line_capture_canonicalization"],
    }


def compare_payload(records: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": now_iso(),
        "group": GROUP,
        "variants": {},
    }
    for variant in VARIANTS:
        payload["variants"][variant] = {}
        for mode in MODES:
            record = records[mode][variant]
            q = record["quotient"]
            payload["variants"][variant][mode] = {
                "builder_variant": variant,
                "matrix_shape": record["compatibility"]["matrix_shape"],
                "rank": record["bs_analysis"]["rank"],
                "nullity": record["bs_analysis"]["nullity"],
                "line_row_count": line_row_counts(record),
                "global_row_count": len(record["compatibility"]["global_matrix_rows"]),
                "ai_candidate_count": q["ai_candidate_count"],
                "ai_candidate_count_used": q["ai_candidate_count_used"],
                "ai_incompatible_count": q["ai_incompatible_count"],
                "ai_embedding_failure_count": q["ai_embedding_failure_count"],
                "surviving_ai_rank": q["surviving_ai_rank"],
                "final_dAI": q["dAI"],
                "surviving_classification": q["surviving_classification"],
                "final_classification": q["classification"],
            }
    for mode in MODES:
        coarse = records[mode]["coarse"]
        intrinsic = records[mode]["intrinsic"]
        extrinsic = records[mode]["extrinsic"]
        payload[mode] = {
            "coarse_vs_intrinsic_kernel": complement_summary(f"{mode}_coarse_minus_intrinsic", coarse, intrinsic),
            "coarse_vs_extrinsic_kernel": complement_summary(f"{mode}_coarse_minus_extrinsic", coarse, extrinsic),
            "intrinsic_vs_extrinsic_kernel": complement_summary(f"{mode}_intrinsic_minus_extrinsic", intrinsic, extrinsic),
        }
    payload["answers"] = {
        "q1_intrinsic_gives_13": all(records[mode]["intrinsic"]["bs_analysis"]["nullity"] == 13 for mode in MODES),
        "q1_extrinsic_gives_13": all(records[mode]["extrinsic"]["bs_analysis"]["nullity"] == 13 for mode in MODES),
        "q1_coarse_gives_13": all(records[mode]["coarse"]["bs_analysis"]["nullity"] == 13 for mode in MODES),
    }
    return payload


def line_restriction_audit_payload(records: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": now_iso(),
        "group": GROUP,
    }
    for mode in MODES:
        payload[mode] = {}
        for variant in VARIANTS:
            record = records[mode][variant]
            payload[mode][variant] = {
                "builder_variant": variant,
                "compatibility_builder_kind": record["compatibility"]["compatibility_builder_kind"],
                "lines": [],
            }
            line_map = {line["id"]: line for line in record["shared"]["grouped"]["lines"]}
            for block in record["compatibility"]["line_blocks"]:
                line_obj = line_map[block["line_id"]]
                endpoints = []
                restriction_classes_by_endpoint = block.get("restriction_class_builder", {}).get("restriction_classes_by_endpoint", {})
                for endpoint in line_obj["endpoints"]:
                    endpoint_id = endpoint["point_id"]
                    endpoints.append(
                        {
                            "endpoint_id": endpoint_id,
                            "capture_id": endpoint.get("capture_id", endpoint_id),
                            "point_coordinates": list(endpoint["point_coordinates"]),
                            "incident_lines": list(endpoint.get("incident_lines", [])),
                            "incident_planes": list(endpoint.get("incident_planes", [])),
                            "plane_incidences": list(endpoint.get("plane_incidences", [])),
                            "partition": restriction_classes_by_endpoint.get(endpoint_id, []),
                        }
                    )
                payload[mode][variant]["lines"].append(
                    {
                        "line_id": block["line_id"],
                        "builder_variant": variant,
                        "row_count": len(block["matrix_rows"]),
                        "containing_planes": list(line_obj.get("containing_planes", [])),
                        "endpoints": endpoints,
                    }
                )
    return payload


def line_row_provenance_payload(records: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    records_out = []
    for mode in MODES:
        for variant in ("intrinsic", "extrinsic"):
            record = records[mode][variant]
            coarse_counts = line_row_counts(records[mode]["coarse"])
            for block in record["compatibility"]["line_blocks"]:
                line_id = block["line_id"]
                coarse_count = coarse_counts[line_id]
                for row_index, equation in enumerate(block["equations"]):
                    records_out.append(
                        {
                            "mode": mode,
                            "builder_variant": variant,
                            "line_id": line_id,
                            "row_id": equation["basis_id"],
                            "row_index_within_line": row_index,
                            "counts_as_additional_vs_coarse": row_index >= coarse_count,
                            "class_members": list(equation.get("class_members", [])),
                            "endpoint_support": dict(equation.get("endpoint_support", {})),
                            "coarse_signature_by_rep": dict(equation.get("coarse_signature_by_rep", {})),
                            "intrinsic_fingerprint_by_rep": dict(equation.get("intrinsic_fingerprint_by_rep", {})),
                            "extrinsic_fingerprint_by_rep": dict(equation.get("extrinsic_fingerprint_by_rep", {})),
                            "affected_unknowns": [term["unknown"] for term in equation["terms"]],
                            "uses_extrinsic_data": bool(equation.get("uses_extrinsic_data", False)),
                            "line_containing_planes": list(equation.get("line_containing_planes", [])),
                            "restricted_vector": equation.get("restricted_vector"),
                        }
                    )
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "rows": records_out,
    }


def ai_rejection_payload(records: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": now_iso(),
        "group": GROUP,
    }
    for mode in MODES:
        payload[mode] = {}
        rejection_sets: dict[str, set[str]] = {}
        for variant in VARIANTS:
            record = records[mode][variant]
            rejected = []
            for candidate in record["quotient"]["ai_incompatible_candidates"]:
                row_records = []
                for row in candidate.get("nonzero_residual_rows", []):
                    row_meta = row.get("row", {})
                    row_records.append(
                        {
                            "row_index": row["row_index"],
                            "residual": row["residual"],
                            "row_id": row_meta.get("basis_id"),
                            "line_id": row_meta.get("line_id"),
                            "source_type": row_meta.get("source_type"),
                            "row_kind": row_meta.get("row_kind"),
                            "uses_extrinsic_data": bool(row_meta.get("uses_extrinsic_data", False)),
                            "builder_variant": row_meta.get("builder_variant", variant),
                        }
                    )
                rejected.append(
                    {
                        "generator_id": candidate["generator_id"],
                        "family_letter": candidate["family_letter"],
                        "row_records": row_records,
                    }
                )
            rejection_sets[variant] = {item["generator_id"] for item in rejected}
            payload[mode][variant] = {
                "builder_variant": variant,
                "rejected_candidate_count": len(rejected),
                "rejected_candidates": rejected,
            }
        payload[mode]["compare"] = {
            "intrinsic_only_rejected": sorted(rejection_sets["intrinsic"] - rejection_sets["extrinsic"]),
            "extrinsic_only_rejected": sorted(rejection_sets["extrinsic"] - rejection_sets["intrinsic"]),
            "rejected_by_both": sorted(rejection_sets["intrinsic"] & rejection_sets["extrinsic"]),
        }
    return payload


def result_payload(record: dict[str, Any], mode: str, recommended_builder_variant: str) -> dict[str, Any]:
    quotient = record["quotient"]
    final_available = bool(quotient["final_dai_available"])
    verification_status = "direct_code_computation_internal_consistency_passed"
    availability = "available"
    if not final_available:
        availability = "provisional"
        verification_status = "failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient"
    elif quotient["dBS"] != quotient["dAI"]:
        availability = "provisional"
        verification_status = "warning_native_generic_result_has_nontrivial_free_part"
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "mode": mode,
        "builder_variant": record["builder_variant"],
        "recommended_interpretation_builder_variant": recommended_builder_variant,
        "row_language_kind": gb.GENERIC_TARGET_ROW_LANGUAGE,
        "object_kind": gb.GENERIC_TARGET_OBJECT_KIND,
        "availability": availability,
        "verification_status": verification_status,
        "dBS": quotient["dBS"],
        "dAI": quotient["dAI"],
        "final_dAI": quotient["dAI"],
        "classification": quotient["classification"],
        "surviving_ai_rank": quotient["surviving_ai_rank"],
        "surviving_classification": quotient["surviving_classification"],
        "surviving_free_rank": quotient["surviving_free_rank"],
        "surviving_finite_part": quotient["surviving_finite_part"],
        "ai_candidate_count": quotient["ai_candidate_count"],
        "ai_candidate_count_used": quotient["ai_candidate_count_used"],
        "ai_incompatible_count": quotient["ai_incompatible_count"],
        "ai_embedding_failure_count": quotient["ai_embedding_failure_count"],
        "compatibility_builder_kind": record["compatibility"]["compatibility_builder_kind"],
        "bs_matrix_shape": record["compatibility"]["matrix_shape"],
        "bs_rank": record["bs_analysis"]["rank"],
        "bs_nullity": record["bs_analysis"]["nullity"],
        "direct_quotient_status": (
            "available" if final_available else "provisional_due_to_rejected_or_unembedded_ai_candidates"
        ),
        "final_dai_available": final_available,
        "source_files": [
            repo_rel(REPO_ROOT / "sg194/pipeline_v2/runtime_backend_free.py"),
            repo_rel(REPO_ROOT / "sg194/pipeline_v2/generic_builders.py"),
            repo_rel(REPO_ROOT / "sg194/pipeline_v2/local_irreps.py"),
        ],
    }


def focus_audit_text(compare: dict[str, Any], row_provenance: dict[str, Any]) -> str:
    rows = row_provenance["rows"]
    def variant_rows(mode: str, variant: str, line_id: str) -> list[dict[str, Any]]:
        return [row for row in rows if row["mode"] == mode and row["builder_variant"] == variant and row["line_id"] == line_id]

    lines = [
        "# SG194 194.1.1.1 L2 / L3 Focus Audit",
        "",
        "## 目标",
        "",
        "- 比较 `coarse / intrinsic / extrinsic` 三套 builder 在 `L2` 和 `L3` 上到底加了什么。",
        "- 明确哪些行是纯当前 line intrinsic restriction 关系，哪些行只有 extrinsic star/plane augmentation 才会出现。",
        "",
    ]
    for mode in MODES:
        lines.extend(
            [
                f"## {mode}",
                "",
                f"- `L2` row counts: coarse `{compare['variants']['coarse'][mode]['line_row_count']['L2']}`, intrinsic `{compare['variants']['intrinsic'][mode]['line_row_count']['L2']}`, extrinsic `{compare['variants']['extrinsic'][mode]['line_row_count']['L2']}`.",
                f"- `L3` row counts: coarse `{compare['variants']['coarse'][mode]['line_row_count']['L3']}`, intrinsic `{compare['variants']['intrinsic'][mode]['line_row_count']['L3']}`, extrinsic `{compare['variants']['extrinsic'][mode]['line_row_count']['L3']}`.",
                "",
                "### L2",
                "",
            ]
        )
        for variant in ("intrinsic", "extrinsic"):
            lines.append(f"- `{variant}`:")
            for row in variant_rows(mode, variant, "L2"):
                lines.append(
                    "  ".join(
                        [
                            "",
                            f"`{row['row_id']}`",
                            f"class_members={row['class_members']}",
                            f"uses_extrinsic={row['uses_extrinsic_data']}",
                        ]
                    ).strip()
                )
        lines.extend(["", "### L3", ""])
        for variant in ("intrinsic", "extrinsic"):
            lines.append(f"- `{variant}`:")
            for row in variant_rows(mode, variant, "L3"):
                lines.append(
                    "  ".join(
                        [
                            "",
                            f"`{row['row_id']}`",
                            f"class_members={row['class_members']}",
                            f"uses_extrinsic={row['uses_extrinsic_data']}",
                        ]
                    ).strip()
                )
        lines.extend(
            [
                "",
                f"- `L2` 是否依赖 extrinsic star/plane 信息：`{any(row['uses_extrinsic_data'] for row in variant_rows(mode, 'extrinsic', 'L2'))}`。",
                f"- `L3` 是否依赖 extrinsic star/plane 信息：`{any(row['uses_extrinsic_data'] for row in variant_rows(mode, 'extrinsic', 'L3'))}`。",
                "",
            ]
        )
    return "\n".join(lines)


def consistency_payload(
    records: dict[str, dict[str, dict[str, Any]]],
    compare: dict[str, Any],
    line_audit: dict[str, Any],
    row_provenance: dict[str, Any],
    single_result: dict[str, Any],
    double_result: dict[str, Any],
) -> dict[str, Any]:
    coverage_expected = 0
    for mode in MODES:
        for variant in ("intrinsic", "extrinsic"):
            coverage_expected += sum(len(block["matrix_rows"]) for block in records[mode][variant]["compatibility"]["line_blocks"])
    coverage_actual = len(row_provenance["rows"])
    compare_matches_variants = True
    for mode in MODES:
        for variant in VARIANTS:
            actual = line_row_counts(records[mode][variant])
            if compare["variants"][variant][mode]["line_row_count"] != actual:
                compare_matches_variants = False
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "checks": {
            "compare_matches_variant_line_counts": compare_matches_variants,
            "provenance_covers_all_noncoarse_rows": coverage_actual == coverage_expected,
            "restriction_class_audit_nonempty": bool(line_audit["single"]["intrinsic"]["lines"] and line_audit["double"]["intrinsic"]["lines"]),
            "single_result_matrix_shape_matches_intrinsic_run": single_result["bs_matrix_shape"] == records["single"]["intrinsic"]["compatibility"]["matrix_shape"],
            "double_result_matrix_shape_matches_intrinsic_run": double_result["bs_matrix_shape"] == records["double"]["intrinsic"]["compatibility"]["matrix_shape"],
        },
        "counts": {
            "expected_noncoarse_row_records": coverage_expected,
            "actual_noncoarse_row_records": coverage_actual,
        },
    }


def write_variant_compatibility_files(records: dict[str, dict[str, dict[str, Any]]]) -> None:
    for mode, path in (("single", SINGLE_VARIANTS_JSON), ("double", DOUBLE_VARIANTS_JSON)):
        payload = {
            "generated_at": now_iso(),
            "group": GROUP,
            "mode": mode,
            "variants": {
                variant: compatibility_variant_payload(records[mode][variant])
                for variant in VARIANTS
            },
        }
        write_json(path, payload)


def package_exact_findings(compare: dict[str, Any], ai_rejection: dict[str, Any], single_result: dict[str, Any], double_result: dict[str, Any]) -> str:
    lines = [
        "# Exact Findings",
        "",
        f"1. Q1: `13` intrinsic 也能得到吗？single/double = `{compare['variants']['intrinsic']['single']['nullity']}` / `{compare['variants']['intrinsic']['double']['nullity']}`；extrinsic = `{compare['variants']['extrinsic']['single']['nullity']}` / `{compare['variants']['extrinsic']['double']['nullity']}`。",
        f"2. Q2: 去掉 extrinsic fingerprints 后，`L3` row counts = single `{compare['variants']['intrinsic']['single']['line_row_count']['L3']}`、double `{compare['variants']['intrinsic']['double']['line_row_count']['L3']}`；extrinsic 则是 single `{compare['variants']['extrinsic']['single']['line_row_count']['L3']}`、double `{compare['variants']['extrinsic']['double']['line_row_count']['L3']}`。",
        f"3. Q3: `L2` 在 intrinsic 下的 row counts = single `{compare['variants']['intrinsic']['single']['line_row_count']['L2']}`、double `{compare['variants']['intrinsic']['double']['line_row_count']['L2']}`。",
        f"4. Q4: 只被 extrinsic 杀掉的 kernel 方向维数 = single `{compare['single']['intrinsic_vs_extrinsic_kernel']['dimension']}`、double `{compare['double']['intrinsic_vs_extrinsic_kernel']['dimension']}`。",
        f"5. Q5: 只在 extrinsic 下被拒的 AI candidates = single `{ai_rejection['single']['compare']['extrinsic_only_rejected']}`、double `{ai_rejection['double']['compare']['extrinsic_only_rejected']}`。",
        f"6. intrinsic 推荐结果：single `dBS={single_result['dBS']}, final_dAI={single_result['final_dAI']}, surviving_ai_rank={single_result['surviving_ai_rank']}`；double `dBS={double_result['dBS']}, final_dAI={double_result['final_dAI']}, surviving_ai_rank={double_result['surviving_ai_rank']}`。",
    ]
    return "\n".join(lines)


def write_run_metadata() -> None:
    write_text(
        RUN_COMMANDS,
        "\n".join(
            [
                "python3 -u sg194/debug_sg194_intrinsic_extrinsic_audit_v1.py > sg194/sg194_intrinsic_extrinsic_audit_v1.stdout 2> sg194/sg194_intrinsic_extrinsic_audit_v1.stderr",
                "python3 -m py_compile sg194/*.py sg194/pipeline_v2/*.py sg194/pipeline_v2/adapters/*.py common/*.py",
            ]
        ),
    )
    git_status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--short", "--branch"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    write_text(RUN_GIT_STATUS, git_status)
    commit = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    write_text(RUN_COMMIT, commit)


def copy_files(target_dir: Path, files: list[Path]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        if not path.exists():
            continue
        shutil.copy2(path, target_dir / path.name)


def build_package(compare: dict[str, Any], single_result: dict[str, Any], double_result: dict[str, Any], ai_rejection: dict[str, Any]) -> None:
    reset_dir(PACKAGE_DIR)
    source_layer = PACKAGE_DIR / "source_layer"
    audit_layer = PACKAGE_DIR / "audit_layer"
    compare_layer = PACKAGE_DIR / "compare_layer"
    run_layer = PACKAGE_DIR / "run_layer"
    semantics_layer = PACKAGE_DIR / "semantics_layer"
    deliverable_layer = PACKAGE_DIR / "deliverable_layer"

    copy_files(
        source_layer,
        [
            REPO_ROOT / "sg194/pipeline_v2/runtime_backend_free.py",
            REPO_ROOT / "sg194/pipeline_v2/generic_builders.py",
            Path(__file__),
        ],
    )
    copy_files(
        audit_layer,
        [
            LINE_AUDIT_V2_JSON,
            LINE_AUDIT_V2_MD,
            ROW_PROVENANCE_JSON,
            AI_REJECTION_JSON,
            SINGLE_RESULT_JSON,
            DOUBLE_RESULT_JSON,
            L2_L3_AUDIT_MD,
            CONSISTENCY_JSON,
        ],
    )
    copy_files(
        compare_layer,
        [
            COMPARE_JSON,
            SINGLE_VARIANTS_JSON,
            DOUBLE_VARIANTS_JSON,
        ],
    )
    copy_files(
        run_layer,
        [
            RUN_COMMANDS,
            RUN_STDOUT,
            RUN_STDERR,
            RUN_GIT_STATUS,
            RUN_COMMIT,
        ],
    )
    write_text(
        semantics_layer / "BOUNDARIES.md",
        "\n".join(
            [
                "# Semantics",
                "",
                "- `coarse`: 旧 `decomposition_on_line_basis` 基线。",
                "- `intrinsic`: 只使用当前 line 的 intrinsic restriction classes，是本轮推荐的 native interpretation。",
                "- `extrinsic`: 把 point-star / plane-incidence 混进 class key，只作 compare，不作推荐 native final builder。",
                "- `legacy special`: 仅作 reference，不参与这轮 builder provenance 结论。",
            ]
        ),
    )
    deliverables = [
        COMPARE_JSON,
        L2_L3_AUDIT_MD,
        ROW_PROVENANCE_JSON,
        AI_REJECTION_JSON,
        SINGLE_RESULT_JSON,
        DOUBLE_RESULT_JSON,
        LINE_AUDIT_V2_JSON,
        CONSISTENCY_JSON,
        REPO_ROOT / "sg194/pipeline_v2/runtime_backend_free.py",
        REPO_ROOT / "sg194/pipeline_v2/generic_builders.py",
    ]
    copy_files(deliverable_layer, deliverables)
    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# SG194 Intrinsic / Extrinsic Audit",
                "",
                "1. 这轮唯一目标：把 194 的 line compatibility builder 拆成 `coarse / intrinsic / extrinsic` 三套，并证明 `13` 到底来自哪一套。",
                f"2. `13` 是否由 intrinsic 得到：single/double = `{compare['variants']['intrinsic']['single']['nullity']}` / `{compare['variants']['intrinsic']['double']['nullity']}`。",
                f"3. `13` 是否由 extrinsic 得到：single/double = `{compare['variants']['extrinsic']['single']['nullity']}` / `{compare['variants']['extrinsic']['double']['nullity']}`。",
                f"4. L2 新增：intrinsic/extrinsic row counts = `{compare['variants']['intrinsic']['single']['line_row_count']['L2']}` / `{compare['variants']['extrinsic']['single']['line_row_count']['L2']}`。",
                f"5. L3 新增：intrinsic/extrinsic row counts = `{compare['variants']['intrinsic']['single']['line_row_count']['L3']}` / `{compare['variants']['extrinsic']['single']['line_row_count']['L3']}`。",
                f"6. final dAI 仍 unavailable 吗：single `{single_result['final_dAI']}`, double `{double_result['final_dAI']}`。",
                "7. 先看哪 10 个文件：compare、L2/L3 focus、row provenance、AI rejection provenance、single/double v3 result、consistency、runtime_backend_free.py、generic_builders.py。",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "- `source_layer/`: 本轮实际修改的源码和运行脚本。",
                "- `audit_layer/`: provenance、AI rejection、v3 result、consistency。",
                "- `compare_layer/`: 三套 builder 的矩阵/row count 对比和 variant compatibility。",
                "- `run_layer/`: 命令、stdout/stderr、git status、HEAD。",
                "- `semantics_layer/`: native intrinsic / extrinsic compare / legacy special 边界。",
                "- `deliverable_layer/`: 最值得先看的 10 个文件。",
            ]
        ),
    )
    write_text(PACKAGE_DIR / "EXACT_FINDINGS.md", package_exact_findings(compare, ai_rejection, single_result, double_result))
    write_text(
        PACKAGE_DIR / "KEY_DIFFS.md",
        "\n".join(
            [
                "# Key Diffs",
                "",
                "- `runtime_backend_free.py`: line builder 显式拆成 `coarse / intrinsic / extrinsic`。",
                "- `generic_builders.py`: generic path 支持 `builder_variant`，结果语义区分 `surviving_ai_rank` 与 `final_dAI`。",
                "- 本轮新增 compare/provenance/result/consistency artifacts，并用统一脚本重建 package。",
            ]
        ),
    )
    tar_directory(PACKAGE_DIR, PACKAGE_TARBALL)


def markdown_line_audit(line_audit: dict[str, Any]) -> str:
    lines = [
        "# SG194 Line Restriction Audit v2",
        "",
    ]
    for mode in MODES:
        lines.append(f"## {mode}")
        lines.append("")
        for variant in VARIANTS:
            lines.append(f"### {variant}")
            lines.append("")
            for line in line_audit[mode][variant]["lines"]:
                lines.append(f"- `{line['line_id']}` rows = `{line['row_count']}`")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    print("[audit] loading contexts")
    contexts = {mode: load_context(mode) for mode in MODES}
    records = {mode: {} for mode in MODES}
    for mode in MODES:
        for variant in VARIANTS:
            print(f"[audit] {mode} {variant}")
            records[mode][variant] = build_variant_record(contexts[mode], variant)

    compare = compare_payload(records)
    line_audit = line_restriction_audit_payload(records)
    row_provenance = line_row_provenance_payload(records)
    ai_rejection = ai_rejection_payload(records)

    recommended_builder_variant = "intrinsic"
    single_result = result_payload(records["single"][recommended_builder_variant], "single", recommended_builder_variant)
    double_result = result_payload(records["double"][recommended_builder_variant], "double", recommended_builder_variant)
    consistency = consistency_payload(records, compare, line_audit, row_provenance, single_result, double_result)

    print("[audit] writing artifacts")
    write_json(COMPARE_JSON, compare)
    write_json(ROW_PROVENANCE_JSON, row_provenance)
    write_text(L2_L3_AUDIT_MD, focus_audit_text(compare, row_provenance))
    write_json(AI_REJECTION_JSON, ai_rejection)
    write_json(SINGLE_RESULT_JSON, single_result)
    write_json(DOUBLE_RESULT_JSON, double_result)
    write_json(CONSISTENCY_JSON, consistency)
    write_json(LINE_AUDIT_V2_JSON, line_audit)
    write_text(LINE_AUDIT_V2_MD, markdown_line_audit(line_audit))
    write_variant_compatibility_files(records)
    write_run_metadata()
    build_package(compare, single_result, double_result, ai_rejection)

    passed = all(consistency["checks"].values())
    print(f"[audit] consistency_passed={passed}")
    print(
        json.dumps(
            {
                "q1_intrinsic_gives_13": compare["answers"]["q1_intrinsic_gives_13"],
                "q1_extrinsic_gives_13": compare["answers"]["q1_extrinsic_gives_13"],
                "single_intrinsic_nullity": compare["variants"]["intrinsic"]["single"]["nullity"],
                "single_extrinsic_nullity": compare["variants"]["extrinsic"]["single"]["nullity"],
                "double_intrinsic_nullity": compare["variants"]["intrinsic"]["double"]["nullity"],
                "double_extrinsic_nullity": compare["variants"]["extrinsic"]["double"]["nullity"],
                "single_final_dAI": single_result["final_dAI"],
                "single_surviving_ai_rank": single_result["surviving_ai_rank"],
                "double_final_dAI": double_result["final_dAI"],
                "double_surviving_ai_rank": double_result["surviving_ai_rank"],
                "consistency_passed": passed,
                "package": str(PACKAGE_TARBALL),
            },
            indent=2,
        )
    )
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
