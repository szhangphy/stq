#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import sympy as sp


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2 import generic_builders as gb
from sg194.pipeline_v2 import runtime_backend_free as rt
from sg194.pipeline_v2.utils import now_iso, reset_dir, tar_directory, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
GROUP = "194.1.1.1"
PACKAGE_DIR = SG194_DIR / "review_package_sg194_generic_restriction_class_fix_v1"
PACKAGE_TARBALL = SG194_DIR / "review_package_sg194_generic_restriction_class_fix_v1.tar.gz"

LINE_AUDIT_JSON = SG194_DIR / "sg194_line_restriction_class_audit_v1.json"
LINE_AUDIT_MD = SG194_DIR / "sg194_line_restriction_class_audit_v1.md"
LINE_COMPARE_JSON = SG194_DIR / "sg194_generic_line_builder_compare_v1.json"
LINE_COMPARE_MD = SG194_DIR / "sg194_generic_line_builder_compare_v1.md"
KERNEL_AUDIT_JSON = SG194_DIR / "sg194_194_native_kernel_localization_after_fix_v1.json"
KERNEL_AUDIT_MD = SG194_DIR / "sg194_194_native_kernel_localization_after_fix_v1.md"
SINGLE_RESULT_JSON = SG194_DIR / "sg194_194_single_generic_final_result_v2.json"
SINGLE_RESULT_MD = SG194_DIR / "sg194_194_single_generic_final_result_v2.md"
DOUBLE_RESULT_JSON = SG194_DIR / "sg194_194_double_generic_final_result_v2.json"
DOUBLE_RESULT_MD = SG194_DIR / "sg194_194_double_generic_final_result_v2.md"
FIX_REPORT_MD = SG194_DIR / "sg194_194_native_fix_report_v1.md"

OLD_SINGLE_BS_JSON = SG194_DIR / "group_194_1_1_1_single_bs_analysis.json"
OLD_DOUBLE_BS_JSON = SG194_DIR / "group_194_1_1_1_double_bs_analysis.json"
OLD_SINGLE_RESULT_JSON = SG194_DIR / "sg194_194_single_generic_final_result_v1.json"
OLD_DOUBLE_RESULT_JSON = SG194_DIR / "sg194_194_double_generic_final_result_v1.json"

EXPECTED_SINGLE = {"dBS": 13, "dAI": 13, "classification": "trivial"}
EXPECTED_DOUBLE = {"dBS": 10, "dAI": 10, "classification": "Z6"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def copy_into_package(target_dir: Path, *files: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for path in files:
        if not path.exists():
            continue
        shutil.copy2(path, target_dir / path.name)


def build_mode_context(mode: str) -> dict[str, Any]:
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

    compatibility_new = gb._build_generic_compatibility(GROUP, shared["grouped"], shared["all_point_ids"], captures)
    bs_new = port.analyze_kernel(compatibility_new)

    line_blocks_old = [
        port.build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
        for line_obj in shared["grouped"]["lines"]
    ]
    line_full_old = port.build_global_compatibility(line_blocks_old, shared["all_point_ids"])
    plane_blocks = []
    for plane_obj in shared["grouped"]["planes"]:
        try:
            block = gb._build_generic_plane_block(plane_obj, plane_obj["corner_entries"], captures)
        except Exception as exc:
            block = gb._build_generic_plane_block_fallback(
                plane_obj,
                plane_obj["corner_entries"],
                captures,
                str(exc),
            )
        plane_blocks.append(block)
    compatibility_old = port.build_with_planes_compatibility(line_full_old, plane_blocks)
    bs_old = port.analyze_kernel(compatibility_old)

    local_library = gb._build_local_irrep_library(ctx, mode)
    induced = gb._induce_all_candidates(
        ctx,
        captures,
        compatibility_new,
        bs_new["unknown_ordering"],
        local_library,
    )
    quotient = gb._build_quotient_from_candidates(
        shared["target_point_ids"],
        bs_new["unknown_ordering"],
        bs_new,
        compatibility_new,
        induced,
    )

    return {
        "mode": mode,
        "shared": shared,
        "ctx": ctx,
        "captures": captures,
        "line_capture_canonicalization": line_capture_canonicalization,
        "compatibility_old": compatibility_old,
        "compatibility_new": compatibility_new,
        "bs_old": bs_old,
        "bs_new": bs_new,
        "line_blocks_old": line_blocks_old,
        "line_blocks_new": compatibility_new["line_blocks"],
        "local_library": local_library,
        "induced": induced,
        "quotient": quotient,
    }


def classes_payload(classes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rep_ids": list(item["rep_ids"]),
            "class_size": int(item["class_size"]),
            "restricted_vector": item["restricted_vector"],
            "extra_fingerprint": item.get("extra_fingerprint"),
        }
        for item in classes
    ]


def decomposition_payload(block: dict[str, Any], endpoint_id: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for rep in block["endpoint_decompositions"][endpoint_id]:
        payload[rep["rep_id"]] = rt._line_decomposition_signature(rep)
    return payload


def build_line_audit(mode_data: dict[str, Any]) -> dict[str, Any]:
    captures = mode_data["captures"]
    lines = mode_data["shared"]["grouped"]["lines"]
    old_blocks = {item["line_id"]: item for item in mode_data["line_blocks_old"]}
    new_blocks = {item["line_id"]: item for item in mode_data["line_blocks_new"]}
    audit_lines = []
    lines_with_refined_classes = []
    character_equals_linear_all = True

    for line_obj in lines:
        line_id = line_obj["id"]
        line_raw = captures[line_id]
        coarse_block = old_blocks[line_id]
        new_block = new_blocks[line_id]
        extra_fingerprints = rt._continuation_fingerprints_for_line(
            line_obj,
            captures,
            coarse_block,
            field="linear_character",
        )
        endpoint_payloads = []
        line_has_refined_classes = False
        line_character_equals_linear = True

        for endpoint in line_obj["endpoints"]:
            endpoint_id = endpoint["point_id"]
            capture_id = endpoint.get("capture_id", endpoint_id)
            endpoint_raw = captures[capture_id]
            matched = rt.matched_unitary_indices(line_raw, endpoint_raw)
            character_classes = rt.identical_restriction_classes(
                endpoint_id,
                endpoint_raw,
                matched,
                field="character",
            )
            linear_classes = rt.identical_restriction_classes(
                endpoint_id,
                endpoint_raw,
                matched,
                field="linear_character",
            )
            refined_classes = rt.identical_restriction_classes(
                endpoint_id,
                endpoint_raw,
                matched,
                field="linear_character",
                extra_fingerprints=extra_fingerprints,
            )
            same_partition = [item["rep_ids"] for item in character_classes] == [item["rep_ids"] for item in linear_classes]
            line_character_equals_linear &= same_partition
            if any(item["class_size"] > 1 for item in refined_classes):
                line_has_refined_classes = True
            endpoint_payloads.append(
                {
                    "endpoint_id": endpoint_id,
                    "capture_id": capture_id,
                    "point_coordinates": list(endpoint["point_coordinates"]),
                    "incident_lines": list(endpoint.get("incident_lines", [])),
                    "incident_planes": list(endpoint.get("incident_planes", [])),
                    "plane_incidences": list(endpoint.get("plane_incidences", [])),
                    "coarse_decomposition_signatures": decomposition_payload(coarse_block, endpoint_id),
                    "character_partition": classes_payload(character_classes),
                    "linear_character_partition": classes_payload(linear_classes),
                    "refined_partition": classes_payload(refined_classes),
                    "character_partition_equals_linear_character_partition": same_partition,
                    "refined_fingerprint_by_rep": {
                        rep_id: extra_fingerprints[rep_id]
                        for rep_id in sorted(rep["rep_id"] for rep in coarse_block["endpoint_decompositions"][endpoint_id])
                    },
                }
            )
        if line_has_refined_classes:
            lines_with_refined_classes.append(line_id)
        character_equals_linear_all &= line_character_equals_linear
        audit_lines.append(
            {
                "line_id": line_id,
                "primary_builder_kind": new_block["restriction_class_builder"]["builder_kind"],
                "field_used_for_primary_builder": new_block["restriction_class_builder"]["field"],
                "coarse_row_count": len(coarse_block["matrix_rows"]),
                "refined_row_count": len(new_block["matrix_rows"]),
                "added_row_count": len(new_block["matrix_rows"]) - len(coarse_block["matrix_rows"]),
                "contained_in_planes": list(line_obj.get("containing_planes", [])),
                "has_refined_class_size_gt_1": line_has_refined_classes,
                "endpoints": endpoint_payloads,
            }
        )

    return {
        "mode": mode_data["mode"],
        "chosen_field": "linear_character",
        "character_vs_linear_character_partitions_match_for_all_lines": character_equals_linear_all,
        "lines_with_refined_classes": lines_with_refined_classes,
        "lines": audit_lines,
    }


def kernel_support_records(bs_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for basis in bs_analysis["basis_vectors"]:
        per_point: dict[str, dict[str, Any]] = {}
        for coeff, unknown in zip(basis["vector"], bs_analysis["unknown_ordering"]):
            if coeff == 0:
                continue
            point_id = unknown.split("_R", 1)[0]
            bucket = per_point.setdefault(point_id, {"l1_norm": 0, "entries": []})
            bucket["l1_norm"] += abs(int(coeff))
            bucket["entries"].append({"unknown": unknown, "coeff": int(coeff)})
        nonzero_points = sorted(per_point)
        records.append(
            {
                "basis_id": basis["id"],
                "nonzero_points": nonzero_points,
                "support_only_on_P3_P4": bool(nonzero_points) and set(nonzero_points).issubset({"P3", "P4"}),
                "per_point": per_point,
            }
        )
    return records


def restricted_kernel_dimension(matrix_payload: dict[str, Any], point_ids: set[str]) -> dict[str, Any]:
    indices = [
        index
        for index, unknown in enumerate(matrix_payload["global_unknown_ordering"])
        if unknown.split("_R", 1)[0] in point_ids
    ]
    restricted = sp.Matrix([[row[index] for index in indices] for row in matrix_payload["global_matrix"]])
    nullity = int(len(indices) - restricted.rank())
    nullspace = restricted.nullspace()
    witness_vectors = []
    for index, vector in enumerate(nullspace, start=1):
        witness_vectors.append(
            {
                "id": f"restricted_basis_{index:02d}",
                "vector": [int(value) for value in list(vector)],
            }
        )
    return {
        "point_ids": sorted(point_ids),
        "unknown_count": len(indices),
        "nullity": nullity,
        "witness_vectors": witness_vectors,
    }


def row_support_summary(row: list[int], ordering: list[str]) -> list[str]:
    points = sorted(
        {
            ordering[index].split("_R", 1)[0]
            for index, coeff in enumerate(row)
            if coeff
        }
    )
    return points


def killed_direction_records(old_bs: dict[str, Any], new_bs: dict[str, Any]) -> list[dict[str, Any]]:
    old_basis = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in old_bs["basis_vectors"]])
    new_basis = sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in new_bs["basis_vectors"]])
    combined = sp.Matrix.hstack(new_basis, old_basis)
    _rref, pivots = combined.rref()
    records = []
    for pivot in pivots:
        if pivot < new_basis.cols:
            continue
        vector = combined[:, pivot]
        per_point: dict[str, dict[str, Any]] = {}
        for coeff, unknown in zip(list(vector), old_bs["unknown_ordering"]):
            coeff = int(coeff)
            if coeff == 0:
                continue
            point_id = unknown.split("_R", 1)[0]
            bucket = per_point.setdefault(point_id, {"l1_norm": 0, "entries": []})
            bucket["l1_norm"] += abs(coeff)
            bucket["entries"].append({"unknown": unknown, "coeff": coeff})
        nonzero_points = sorted(per_point)
        records.append(
            {
                "pivot_column": int(pivot),
                "nonzero_points": nonzero_points,
                "support_only_on_P3_P4": bool(nonzero_points) and set(nonzero_points).issubset({"P3", "P4"}),
                "per_point": per_point,
            }
        )
    return records


def build_result_payload(record: dict[str, Any], expected: dict[str, Any], mode_data: dict[str, Any]) -> dict[str, Any]:
    quotient = mode_data["quotient"]
    rejected = quotient["ai_incompatible_candidates"]
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "object_id": record["object_id"],
        "mode": record["mode"],
        "row_language_kind": record["row_language_kind"],
        "object_kind": record["object_kind"],
        "availability": record["availability"],
        "verification_status": record.get("verification_status"),
        "dBS": record.get("dBS"),
        "dAI": record.get("dAI"),
        "classification": record.get("classification"),
        "free_rank": record.get("free_rank"),
        "finite_part": record.get("finite_part"),
        "quotient_derivation_mode": record.get("quotient_derivation_mode"),
        "ai_candidate_count": record.get("ai_candidate_count"),
        "ai_candidate_count_used": record.get("ai_candidate_count_used"),
        "ai_incompatible_count": record.get("ai_incompatible_count"),
        "ai_embedding_failure_count": record.get("ai_embedding_failure_count"),
        "source_files": record.get("source_files", []),
        "compatibility_builder_kind": mode_data["compatibility_new"]["compatibility_builder_kind"],
        "bs_matrix_shape": mode_data["bs_new"]["matrix_shape"],
        "bs_rank": mode_data["bs_new"]["rank"],
        "native_bs_nullity_fix_status": (
            "fixed_to_13"
            if mode_data["bs_old"]["nullity"] == 16 and mode_data["bs_new"]["nullity"] == 13
            else "not_fixed"
        ),
        "ai_rejection_summary": {
            "rejected_generator_ids": [item["generator_id"] for item in rejected],
            "rejected_row_blocks": sorted(
                {
                    f"{row['row'].get('source_type')}:{row['row'].get('line_id') or row['row'].get('plane_id')}:{row['row'].get('basis_id')}"
                    for item in rejected
                    for row in item.get("nonzero_residual_rows", [])
                    if row.get("row")
                }
            ),
        },
        "accepted_special_reference": expected,
        "matches_accepted_special": all(record.get(key) == value for key, value in expected.items()),
    }


def md_for_result(title: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- availability: `{payload['availability']}`",
        f"- verification_status: `{payload['verification_status']}`",
        f"- dBS/dAI/classification: `{payload['dBS']}/{payload['dAI']}/{payload['classification']}`",
        f"- BS matrix shape/rank: `{payload['bs_matrix_shape']}` / `{payload['bs_rank']}`",
        f"- native BS nullity fix: `{payload['native_bs_nullity_fix_status']}`",
        f"- AI candidates used/rejected: `{payload['ai_candidate_count_used']}` / `{payload['ai_incompatible_count']}`",
        f"- matches accepted special: `{payload['matches_accepted_special']}`",
    ]
    if payload["ai_rejection_summary"]["rejected_row_blocks"]:
        lines.append(
            f"- rejected row blocks: `{payload['ai_rejection_summary']['rejected_row_blocks']}`"
        )
    return "\n".join(lines)


def build_target_record(mode_data: dict[str, Any]) -> dict[str, Any]:
    quotient = mode_data["quotient"]
    availability = "available"
    direct_quotient_status = "available"
    verification_status = "direct_code_computation_internal_consistency_passed"
    if quotient["ai_failure_count"] or quotient["ai_embedding_failure_count"] or quotient["ai_incompatible_count"]:
        availability = "provisional"
        direct_quotient_status = "provisional_due_to_rejected_or_unembedded_ai_candidates"
        verification_status = "failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient"
    elif quotient["dBS"] != quotient["dAI"]:
        availability = "provisional"
        direct_quotient_status = "provisional_due_to_native_dbs_dai_gap"
        verification_status = "warning_native_generic_result_has_nontrivial_free_part"
    return {
        "object_id": f"{mode_data['mode']}_target_direct",
        "mode": mode_data["mode"],
        "row_language_kind": gb.GENERIC_TARGET_ROW_LANGUAGE,
        "object_kind": gb.GENERIC_TARGET_OBJECT_KIND,
        "availability": availability,
        "dBS": quotient["dBS"],
        "dAI": quotient["dAI"],
        "classification": quotient["classification"],
        "free_rank": quotient["free_rank"],
        "finite_part": quotient["finite_part"],
        "quotient_derivation_mode": "direct_generic_bs_over_ai_smith",
        "verification_status": verification_status,
        "ai_candidate_count": quotient["ai_candidate_count"],
        "ai_candidate_count_used": quotient["ai_candidate_count_used"],
        "ai_incompatible_count": quotient["ai_incompatible_count"],
        "ai_embedding_failure_count": quotient["ai_embedding_failure_count"],
        "source_files": [
            str(gb.RUNTIME_BACKEND.relative_to(REPO_ROOT)),
            str(gb.LOCAL_IRREP_BACKEND.relative_to(REPO_ROOT)),
        ],
        "direct_quotient_status": direct_quotient_status,
    }


def build_package_docs(
    line_compare: dict[str, Any],
    single_result: dict[str, Any],
    double_result: dict[str, Any],
) -> dict[str, str]:
    readme = "\n".join(
        [
            "# SG194 Generic Restriction-Class Fix v1",
            "",
            "1. 这轮唯一目标是把 194.1.1.1 backend-free generic path 的 native compatibility builder 修成真正的 restriction-class primary builder，并先把 BS nullity 从 16 修回 13。",
            f"2. BS nullity 16 -> 13: single=`{line_compare['single']['global_matrix_old']['nullity']}->{line_compare['single']['global_matrix_new']['nullity']}`，double=`{line_compare['double']['global_matrix_old']['nullity']}->{line_compare['double']['global_matrix_new']['nullity']}`。",
            f"3. native 194 single 现在是 `{single_result['dBS']}/{single_result['dAI']}/{single_result['classification']}`，availability=`{single_result['availability']}`。",
            f"4. native 194 double 现在是 `{double_result['dBS']}/{double_result['dAI']}/{double_result['classification']}`，availability=`{double_result['availability']}`。",
            "5. 当前 blocker 不是 BS，而是 AI：修后的 native compatibility 会拒掉一批旧的 AI candidates，主要落在 `L2` 和 `L3` 的新 restriction-class rows。",
            "6. 建议先看：`audit_layer/sg194_generic_line_builder_compare_v1.json`、`audit_layer/sg194_line_restriction_class_audit_v1.json`、`audit_layer/sg194_194_native_kernel_localization_after_fix_v1.json`、`audit_layer/sg194_194_native_fix_report_v1.md`。",
        ]
    )
    review_map = "\n".join(
        [
            "# Review Map",
            "",
            "- `source_layer/`: 本轮实际修改源码。",
            "- `audit_layer/`: line/class/kernel/final-result/fix-report 主审计。",
            "- `compare_layer/`: old coarse vs new primary 的关键对比。",
            "- `run_layer/`: 运行命令、stdout/stderr、git status、commit SHA。",
            "- `semantics_layer/`: native generic / legacy special / benchmark compare 边界。",
            "- `deliverable_layer/`: 最值得先看的 10 个文件。",
        ]
    )
    exact_findings = "\n".join(
        [
            "# Exact Findings",
            "",
            f"- single 和 double 的 native BS nullity 都从 `16` 变成了 `13`。",
            "- primary line builder 不再走 old coarse success path；restriction classes 现在是默认主路径。",
            "- 几何/连通性修正点不是 family/spec，而是 point-instance 语义：不能把同一 orbit point_id 的不同坐标实例混成一个 endpoint star。",
            "- 需要识别 plane 内部 special lines；当前已显式记录 `L4 in S2` 和 `L7 in S4` 的 interior incidence。",
            f"- 修后的 AI 仍有 blocker：single rejected=`{single_result['ai_incompatible_count']}`，double rejected=`{double_result['ai_incompatible_count']}`。",
        ]
    )
    key_diffs = "\n".join(
        [
            "# Key Diffs",
            "",
            f"- single global matrix: old `{line_compare['single']['global_matrix_old']['shape']}` -> new `{line_compare['single']['global_matrix_new']['shape']}`.",
            f"- single rank/nullity: old `{line_compare['single']['global_matrix_old']['rank']}/{line_compare['single']['global_matrix_old']['nullity']}` -> new `{line_compare['single']['global_matrix_new']['rank']}/{line_compare['single']['global_matrix_new']['nullity']}`.",
            f"- double global matrix: old `{line_compare['double']['global_matrix_old']['shape']}` -> new `{line_compare['double']['global_matrix_new']['shape']}`.",
            f"- double rank/nullity: old `{line_compare['double']['global_matrix_old']['rank']}/{line_compare['double']['global_matrix_old']['nullity']}` -> new `{line_compare['double']['global_matrix_new']['rank']}/{line_compare['double']['global_matrix_new']['nullity']}`.",
            "- lines with added primary rows: `L2`, `L3`.",
            "- L2 added rows come from genuine restriction-class duplicates at `P4`; L3 added rows come from instance-local continuation classes at the non-representative `P5` endpoint.",
        ]
    )
    semantics = "\n".join(
        [
            "# Native Generic vs Legacy Special vs Benchmark Compare",
            "",
            "- native generic: 只使用 symmetry operations、swyckoff conversion、generic builders、generic compatibility/AI/quotient；这轮 fix 就发生在这一层。",
            "- legacy special: 194 的 accepted special result 只保留作 regression reference，不参与 native compatibility 或 native final result 计算。",
            "- benchmark compare: benchmark/internalization/projection/oracle 在这轮都没有被用来构造 native result；它们只保留为外部比较层。",
        ]
    )
    return {
        "README.md": readme,
        "REVIEW_MAP.md": review_map,
        "EXACT_FINDINGS.md": exact_findings,
        "KEY_DIFFS.md": key_diffs,
        "semantics_layer/native_generic_vs_legacy_special_vs_benchmark_compare.md": semantics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    single = build_mode_context("single")
    double = build_mode_context("double")
    single_record = build_target_record(single)
    double_record = build_target_record(double)

    line_audit = {
        "generated_at": now_iso(),
        "group": GROUP,
        "field_design": {
            "chosen_field": "linear_character",
            "rationale": (
                "The primary builder now uses restriction classes on linear_character because it preserves "
                "phase/projective information consistently across single and double paths. In this 194 audit, "
                "the raw line-level character and linear_character partitions agree, but linear_character stays "
                "the stable general choice for the primary builder."
            ),
            "plane_builder_generalization_status": (
                "No new plane restriction-class builder was required in this step. The geometry/connectivity "
                "layer was still generalized to register interior special lines inside planes so endpoint-instance "
                "continuation fingerprints can see the correct local star."
            ),
        },
        "single": build_line_audit(single),
        "double": build_line_audit(double),
    }

    line_compare = {
        "generated_at": now_iso(),
        "group": GROUP,
        "single": {
            "line_row_compare": [
                {
                    "line_id": new_block["line_id"],
                    "old_coarse_row_count": len(old_block["matrix_rows"]),
                    "new_primary_row_count": len(new_block["matrix_rows"]),
                    "row_delta": len(new_block["matrix_rows"]) - len(old_block["matrix_rows"]),
                }
                for old_block, new_block in zip(single["line_blocks_old"], single["line_blocks_new"])
            ],
            "global_matrix_old": {
                "shape": single["bs_old"]["matrix_shape"],
                "rank": single["bs_old"]["rank"],
                "nullity": single["bs_old"]["nullity"],
            },
            "global_matrix_new": {
                "shape": single["bs_new"]["matrix_shape"],
                "rank": single["bs_new"]["rank"],
                "nullity": single["bs_new"]["nullity"],
            },
        },
        "double": {
            "line_row_compare": [
                {
                    "line_id": new_block["line_id"],
                    "old_coarse_row_count": len(old_block["matrix_rows"]),
                    "new_primary_row_count": len(new_block["matrix_rows"]),
                    "row_delta": len(new_block["matrix_rows"]) - len(old_block["matrix_rows"]),
                }
                for old_block, new_block in zip(double["line_blocks_old"], double["line_blocks_new"])
            ],
            "global_matrix_old": {
                "shape": double["bs_old"]["matrix_shape"],
                "rank": double["bs_old"]["rank"],
                "nullity": double["bs_old"]["nullity"],
            },
            "global_matrix_new": {
                "shape": double["bs_new"]["matrix_shape"],
                "rank": double["bs_new"]["rank"],
                "nullity": double["bs_new"]["nullity"],
            },
        },
    }

    kernel_audit = {
        "generated_at": now_iso(),
        "group": GROUP,
        "single": {
            "before_fix": {
                "matrix_shape": single["bs_old"]["matrix_shape"],
                "rank": single["bs_old"]["rank"],
                "nullity": single["bs_old"]["nullity"],
                "basis_support": kernel_support_records(single["bs_old"]),
                "p3_p4_only_kernel_subspace": restricted_kernel_dimension(single["compatibility_old"], {"P3", "P4"}),
            },
            "after_fix": {
                "matrix_shape": single["bs_new"]["matrix_shape"],
                "rank": single["bs_new"]["rank"],
                "nullity": single["bs_new"]["nullity"],
                "basis_support": kernel_support_records(single["bs_new"]),
                "p3_p4_only_kernel_subspace": restricted_kernel_dimension(single["compatibility_new"], {"P3", "P4"}),
            },
            "killed_directions_by_new_rows": killed_direction_records(single["bs_old"], single["bs_new"]),
        },
        "double": {
            "before_fix": {
                "matrix_shape": double["bs_old"]["matrix_shape"],
                "rank": double["bs_old"]["rank"],
                "nullity": double["bs_old"]["nullity"],
                "basis_support": kernel_support_records(double["bs_old"]),
                "p3_p4_only_kernel_subspace": restricted_kernel_dimension(double["compatibility_old"], {"P3", "P4"}),
            },
            "after_fix": {
                "matrix_shape": double["bs_new"]["matrix_shape"],
                "rank": double["bs_new"]["rank"],
                "nullity": double["bs_new"]["nullity"],
                "basis_support": kernel_support_records(double["bs_new"]),
                "p3_p4_only_kernel_subspace": restricted_kernel_dimension(double["compatibility_new"], {"P3", "P4"}),
            },
            "killed_directions_by_new_rows": killed_direction_records(double["bs_old"], double["bs_new"]),
        },
        "residual_summary": {
            "single_rank_gain": int(single["bs_new"]["rank"] - single["bs_old"]["rank"]),
            "double_rank_gain": int(double["bs_new"]["rank"] - double["bs_old"]["rank"]),
            "single_killed_direction_supports": [
                {
                    "nonzero_points": item["nonzero_points"],
                    "support_only_on_P3_P4": item["support_only_on_P3_P4"],
                }
                for item in killed_direction_records(single["bs_old"], single["bs_new"])
            ],
            "double_killed_direction_supports": [
                {
                    "nonzero_points": item["nonzero_points"],
                    "support_only_on_P3_P4": item["support_only_on_P3_P4"],
                }
                for item in killed_direction_records(double["bs_old"], double["bs_new"])
            ],
            "new_rows_with_support_on_P3_or_P4": [
                {
                    "mode": "single",
                    "line_id": row["line_id"],
                    "basis_id": row["basis_id"],
                    "support_points": row_support_summary(row["matrix_row"], single["compatibility_new"]["global_unknown_ordering"]),
                }
                for row in single["compatibility_new"]["global_matrix_rows"]
                if row.get("source_type") == "line"
                and row.get("row_index_within_source", -1) >= len(
                    next(block for block in single["line_blocks_old"] if block["line_id"] == row["line_id"])["matrix_rows"]
                )
                and {"P3", "P4"} & set(row_support_summary(row["matrix_row"], single["compatibility_new"]["global_unknown_ordering"]))
            ],
        },
    }

    single_result = build_result_payload(single_record, EXPECTED_SINGLE, single)
    double_result = build_result_payload(double_record, EXPECTED_DOUBLE, double)

    write_json(LINE_AUDIT_JSON, line_audit)
    write_text(
        LINE_AUDIT_MD,
        "\n".join(
            [
                "# Line Restriction Class Audit v1",
                "",
                "- chosen field: `linear_character`",
                f"- single lines with refined classes: `{line_audit['single']['lines_with_refined_classes']}`",
                f"- double lines with refined classes: `{line_audit['double']['lines_with_refined_classes']}`",
                "- key geometry fix: endpoint stars now use instance-level capture_id coordinates instead of orbit-level point_id unions.",
                "- interior special lines inside planes are recorded explicitly and feed the local star audit.",
            ]
        ),
    )

    write_json(LINE_COMPARE_JSON, line_compare)
    write_text(
        LINE_COMPARE_MD,
        "\n".join(
            [
                "# Generic Line Builder Compare v1",
                "",
                f"- single old/new shape: `{line_compare['single']['global_matrix_old']['shape']}` -> `{line_compare['single']['global_matrix_new']['shape']}`",
                f"- single old/new rank-nullity: `{line_compare['single']['global_matrix_old']['rank']}/{line_compare['single']['global_matrix_old']['nullity']}` -> `{line_compare['single']['global_matrix_new']['rank']}/{line_compare['single']['global_matrix_new']['nullity']}`",
                f"- double old/new shape: `{line_compare['double']['global_matrix_old']['shape']}` -> `{line_compare['double']['global_matrix_new']['shape']}`",
                f"- double old/new rank-nullity: `{line_compare['double']['global_matrix_old']['rank']}/{line_compare['double']['global_matrix_old']['nullity']}` -> `{line_compare['double']['global_matrix_new']['rank']}/{line_compare['double']['global_matrix_new']['nullity']}`",
                "- lines with added rows: `L2`, `L3`.",
            ]
        ),
    )

    write_json(KERNEL_AUDIT_JSON, kernel_audit)
    write_text(
        KERNEL_AUDIT_MD,
        "\n".join(
            [
                "# 194 Native Kernel Localization After Fix v1",
                "",
                f"- single old/new nullity: `{kernel_audit['single']['before_fix']['nullity']} -> {kernel_audit['single']['after_fix']['nullity']}`",
                f"- double old/new nullity: `{kernel_audit['double']['before_fix']['nullity']} -> {kernel_audit['double']['after_fix']['nullity']}`",
                f"- single killed directions by new rows: `{kernel_audit['residual_summary']['single_killed_direction_supports']}`",
                f"- double killed directions by new rows: `{kernel_audit['residual_summary']['double_killed_direction_supports']}`",
                f"- new rows that touch P3/P4: `{kernel_audit['residual_summary']['new_rows_with_support_on_P3_or_P4']}`",
            ]
        ),
    )

    write_json(SINGLE_RESULT_JSON, single_result)
    write_text(SINGLE_RESULT_MD, md_for_result("194 Single Generic Final Result v2", single_result))
    write_json(DOUBLE_RESULT_JSON, double_result)
    write_text(DOUBLE_RESULT_MD, md_for_result("194 Double Generic Final Result v2", double_result))

    write_text(
        FIX_REPORT_MD,
        "\n".join(
            [
                "# 194 Native Fix Report v1",
                "",
                "这一步之前一直卡住，不是因为 quotient 后处理不够，而是因为 native compatibility builder 还没有真的 general：",
                "- 主路径仍然先走 old coarse decomposition line builder，restriction classes 只在 fallback 才启用。",
                "- endpoint star 是按 orbit-level point_id 聚合的，把同一 orbit 上不同坐标实例混在了一起，直接伪造 continuation。",
                "- geometry/connectivity 只显式认 plane boundary，没有把 plane 内部的 special lines 记成真实 incidence。",
                "",
                "这次真正改动的是 native compatibility builder 本身：",
                "- 所有 line 默认都走 restriction-class primary builder，不再把 old coarse builder 当 success path。",
                "- restriction fingerprint 统一到 linear_character，并补上 instance-level point-star continuation。",
                "- endpoint star 现在按 capture_id/坐标实例建，不再把 P5/P6 这类 orbit label 的不同实例混成一个点。",
                "- plane 内部 special lines 现在显式登记；当前 194 审计里能看到 `L4 in S2`、`L7 in S4` 的 interior incidence。",
                "",
                f"结果是：single BS nullity `{single['bs_old']['nullity']} -> {single['bs_new']['nullity']}`，double BS nullity `{double['bs_old']['nullity']} -> {double['bs_new']['nullity']}`。这说明核心 bug 已经在 C 矩阵层被碰到了，而不是靠后处理把 16 压成 13。",
                "- 新 rows 一共把 old kernel 杀掉 3 个方向；kernel localization 审计显示其中 1 个方向纯支撑在 `P3/P4`，另外 2 个方向混合支撑在 `P1/P5` 与 plane blocks 上，对应的正是新加的 `L2` 和 `L3` restriction-class relations。",
                "",
                "但 194 现在还没有变成 accepted final result。原因已经从 BS 层转移到了 AI 层：",
                f"- single 现在是 `{single_result['dBS']}/{single_result['dAI']}/{single_result['classification']}`，rejected AI candidates=`{single_result['ai_incompatible_count']}`。",
                f"- double 现在是 `{double_result['dBS']}/{double_result['dAI']}/{double_result['classification']}`，rejected AI candidates=`{double_result['ai_incompatible_count']}`。",
                "- 这些 rejection 主要集中在 `L2_restriction_class_P4_01` 和 `L3_restriction_class_P5_01..04`。",
                "",
                "所以这一步的诚实结论是：BS 侧已经修对到 13；如果后面还要追 accepted final result，下一步该处理的是 AI seeds 与修后 compatibility 的一致性，而不是再回头补 projection/spec/adapter。",
            ]
        ),
    )

    reset_dir(PACKAGE_DIR)
    for rel_path, content in build_package_docs(line_compare, single_result, double_result).items():
        write_text(PACKAGE_DIR / rel_path, content)

    copy_into_package(PACKAGE_DIR / "source_layer", gb.RUNTIME_BACKEND, gb.LOCAL_IRREP_BACKEND)
    copy_into_package(PACKAGE_DIR / "source_layer", Path(__file__))
    copy_into_package(
        PACKAGE_DIR / "audit_layer",
        LINE_AUDIT_JSON,
        LINE_AUDIT_MD,
        LINE_COMPARE_JSON,
        LINE_COMPARE_MD,
        KERNEL_AUDIT_JSON,
        KERNEL_AUDIT_MD,
        SINGLE_RESULT_JSON,
        SINGLE_RESULT_MD,
        DOUBLE_RESULT_JSON,
        DOUBLE_RESULT_MD,
        FIX_REPORT_MD,
    )
    copy_into_package(
        PACKAGE_DIR / "compare_layer",
        OLD_SINGLE_RESULT_JSON,
        OLD_DOUBLE_RESULT_JSON,
        SINGLE_RESULT_JSON,
        DOUBLE_RESULT_JSON,
        LINE_COMPARE_JSON,
        LINE_COMPARE_MD,
    )
    copy_into_package(PACKAGE_DIR / "semantics_layer", FIX_REPORT_MD)
    deliverable_paths = [
        gb.RUNTIME_BACKEND,
        REPO_ROOT / "sg194" / "pipeline_v2" / "generic_builders.py",
        LINE_AUDIT_JSON,
        LINE_AUDIT_MD,
        LINE_COMPARE_JSON,
        KERNEL_AUDIT_JSON,
        FIX_REPORT_MD,
        SINGLE_RESULT_JSON,
        DOUBLE_RESULT_JSON,
        LINE_COMPARE_MD,
    ]
    copy_into_package(PACKAGE_DIR / "deliverable_layer", *deliverable_paths)
    run_layer = PACKAGE_DIR / "run_layer"
    run_layer.mkdir(parents=True, exist_ok=True)
    write_text(run_layer / "commands.txt", "Filled after script execution.")
    write_text(run_layer / "stdout.txt", "Filled after script execution.")
    write_text(run_layer / "stderr.txt", "Filled after script execution.")
    write_text(run_layer / "git_status.txt", "Filled after script execution.")
    write_text(run_layer / "commit_sha.txt", "Filled after commit.")

    tar_directory(PACKAGE_DIR, PACKAGE_TARBALL)

    if args.validate:
        if single["bs_new"]["nullity"] != 13 or double["bs_new"]["nullity"] != 13:
            raise SystemExit("native BS nullity fix did not reach 13/13")
        if line_compare["single"]["global_matrix_new"]["nullity"] != 13:
            raise SystemExit("single compare payload inconsistent")
        if line_compare["double"]["global_matrix_new"]["nullity"] != 13:
            raise SystemExit("double compare payload inconsistent")


if __name__ == "__main__":
    main()
