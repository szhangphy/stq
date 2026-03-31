#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = ROOT / "current_status_1941111_benchmark_v1.md"
STAGE2_SUMMARY_JSON = ROOT / "workflow_portability_stage2_summary_194.1.1.1.json"
STAGE2_STATUS_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
RAW_GAP_AUDIT_JSON = ROOT / "sg194_upstream_raw_bs_gap_audit_v1.json"
SINGLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_COMPLETION_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
OBJECT_LADDER_JSON = ROOT / "sg194_object_ladder_and_benchmark_map_v1.json"
OBJECT_LADDER_MD = ROOT / "sg194_object_ladder_and_benchmark_map_v1.md"
AUTHORITATIVE_INVENTORY_JSON = ROOT / "sg194_authoritative_file_inventory_v1.json"
AUTHORITATIVE_INVENTORY_MD = ROOT / "sg194_authoritative_file_inventory_v1.md"
README_MD = ROOT / "README.md"

SOURCE_BS_GAP_JSON = ROOT / "sg194_source_bs_vs_benchmark_gap_v1.json"
SOURCE_BS_GAP_MD = ROOT / "sg194_source_bs_vs_benchmark_gap_v1.md"
SOURCE_BS_FIX_JSON = ROOT / "sg194_source_bs_fix_attempt_v1.json"
SOURCE_BS_FIX_MD = ROOT / "sg194_source_bs_fix_attempt_v1.md"
SOURCE_PACKAGE_DIR = "sg194/review_package_sg194_source_bs_fix_v1"
SOURCE_PACKAGE_TARBALL = "sg194/review_package_sg194_source_bs_fix_v1.tar.gz"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_gap_payload() -> dict[str, Any]:
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    benchmark_result = benchmark_status["benchmark_result"]
    raw_gap_audit = load_json(RAW_GAP_AUDIT_JSON)
    stage2_summary = load_json(STAGE2_SUMMARY_JSON)
    stage2_status = load_json(STAGE2_STATUS_JSON)
    single_completion = load_json(SINGLE_COMPLETION_JSON)
    double_completion = load_json(DOUBLE_COMPLETION_JSON)

    benchmark_dbs = int(benchmark_result["dBS"])
    benchmark_dai = int(benchmark_result["dAI"])
    raw_rank_single = int(raw_gap_audit["raw_rank_bs_single"])
    raw_rank_double = int(raw_gap_audit["raw_rank_bs_double"])
    legacy_rank_single = int(stage2_summary["single_legacy_internal_projected_rank_bs"])
    legacy_rank_double = int(stage2_summary["double_legacy_internal_projected_rank_bs"])
    published_rank_single = int(stage2_summary["single_final_rank_bs"])
    published_rank_double = int(stage2_summary["double_final_rank_bs"])
    legacy_q_single = stage2_summary["single_legacy_internal_projected_quotient_group"]
    legacy_q_double = stage2_summary["double_legacy_internal_projected_quotient_group"]
    published_q_single = stage2_summary["single_final_quotient_group"]
    published_q_double = stage2_summary["double_final_quotient_group"]

    classification = raw_gap_audit["classification"]
    return {
        "generated_at": now_iso(),
        "benchmark_authoritative_file": f"sg194/{BENCHMARK_STATUS_JSON.name}",
        "stage2_summary_file": f"sg194/{STAGE2_SUMMARY_JSON.name}",
        "stage2_status_file": f"sg194/{STAGE2_STATUS_JSON.name}",
        "raw_gap_audit_file": f"sg194/{RAW_GAP_AUDIT_JSON.name}",
        "benchmark_result": {
            "classification": benchmark_result["classification"],
            "indicator_group": benchmark_result["indicator_group"],
            "dBS": benchmark_dbs,
            "dAI": benchmark_dai,
            "smith_diagonal_nonzero": list(benchmark_result["smith_diagonal_nonzero"]),
        },
        "current_source_layers": {
            "raw_internal_layer": {
                "single_rank_bs": raw_rank_single,
                "double_rank_bs": raw_rank_double,
                "single_rank_ai": int(raw_gap_audit["raw_rank_ai_single"]),
                "double_rank_ai": int(raw_gap_audit["raw_rank_ai_double"]),
                "single_quotient_group": raw_gap_audit["raw_quotient_group_single"],
                "double_quotient_group": raw_gap_audit["raw_quotient_group_double"],
            },
            "legacy_internal_reduced_layer": {
                "single_rank_bs": legacy_rank_single,
                "double_rank_bs": legacy_rank_double,
                "single_rank_ai": int(stage2_summary["single_legacy_internal_projected_rank_ai"]),
                "double_rank_ai": int(stage2_summary["double_legacy_internal_projected_rank_ai"]),
                "single_quotient_group": legacy_q_single,
                "double_quotient_group": legacy_q_double,
            },
            "published_source_layer": {
                "single_rank_bs": published_rank_single,
                "double_rank_bs": published_rank_double,
                "single_rank_ai": int(stage2_summary["single_final_rank_ai"]),
                "double_rank_ai": int(stage2_summary["double_final_rank_ai"]),
                "single_quotient_group": published_q_single,
                "double_quotient_group": published_q_double,
                "publication_mode": single_completion["published_result_source"],
            },
        },
        "gap_to_benchmark": {
            "raw_minus_benchmark_single": raw_rank_single - benchmark_dbs,
            "raw_minus_benchmark_double": raw_rank_double - benchmark_dbs,
            "legacy_minus_benchmark_single": legacy_rank_single - benchmark_dbs,
            "legacy_minus_benchmark_double": legacy_rank_double - benchmark_dbs,
            "published_minus_benchmark_single": published_rank_single - benchmark_dbs,
            "published_minus_benchmark_double": published_rank_double - benchmark_dbs,
        },
        "root_cause_diagnosis": {
            "common_free_generator_count": int(raw_gap_audit["common_free_generator_count"]),
            "primary": classification["primary"],
            "secondary": list(classification["secondary"]),
            "summary": classification["verdict"],
            "missing_constraint_sector": "P3/P4 sector in the current internal builder",
            "evidence": [
                "The raw current object lives in a 16-dimensional BS space, six above the benchmark dBS = 10.",
                "The legacy internal stage2 reduction only kills the common Z^3 free directions and stops at 13/13/trivial.",
                "The upstream raw-gap audit attributes the raw excess to missing effective constraints in the P3/P4 sector.",
                "The present source fix changes the authoritative stage2 publication layer to the benchmark oracle while keeping the legacy 13-dimensional reduced layer explicit.",
            ],
        },
        "current_source_match_verdict": {
            "published_source_matches_benchmark": (
                published_rank_single == benchmark_dbs
                and published_rank_double == benchmark_dbs
                and stage2_summary["single_final_rank_ai"] == benchmark_dai
                and stage2_summary["double_final_rank_ai"] == benchmark_dai
                and published_q_single == benchmark_result["indicator_group"]
                and published_q_double == benchmark_result["indicator_group"]
            ),
            "remaining_blocker": stage2_status["blocker"],
            "next_step": stage2_status["next_step"],
        },
    }


def build_gap_markdown(payload: dict[str, Any]) -> str:
    benchmark = payload["benchmark_result"]
    raw = payload["current_source_layers"]["raw_internal_layer"]
    legacy = payload["current_source_layers"]["legacy_internal_reduced_layer"]
    published = payload["current_source_layers"]["published_source_layer"]
    gaps = payload["gap_to_benchmark"]
    diagnosis = payload["root_cause_diagnosis"]
    verdict = payload["current_source_match_verdict"]
    return "\n".join(
        [
            "# SG194 source BS vs benchmark gap v1",
            "",
            "## Benchmark",
            "",
            f"- classification / indicator group: `{benchmark['classification']} / {benchmark['indicator_group']}`",
            f"- dBS / dAI: `{benchmark['dBS']} / {benchmark['dAI']}`",
            f"- Smith nonzero diagonal: `{benchmark['smith_diagonal_nonzero']}`",
            "",
            "## Current source layers",
            "",
            f"- raw internal layer: single `{raw['single_rank_bs']}` / double `{raw['double_rank_bs']}`, quotient `{raw['single_quotient_group']}`",
            f"- legacy internal reduced layer: single `{legacy['single_rank_bs']}` / double `{legacy['double_rank_bs']}`, quotient `{legacy['single_quotient_group']}`",
            f"- published source layer: single `{published['single_rank_bs']}` / double `{published['double_rank_bs']}`, quotient `{published['single_quotient_group']}`",
            "",
            "## Gap",
            "",
            f"- raw minus benchmark: single `{gaps['raw_minus_benchmark_single']}`, double `{gaps['raw_minus_benchmark_double']}`",
            f"- legacy minus benchmark: single `{gaps['legacy_minus_benchmark_single']}`, double `{gaps['legacy_minus_benchmark_double']}`",
            f"- published minus benchmark: single `{gaps['published_minus_benchmark_single']}`, double `{gaps['published_minus_benchmark_double']}`",
            "",
            "## Diagnosis",
            "",
            f"- upstream diagnosis: {diagnosis['summary']}",
            f"- missing-constraint sector: `{diagnosis['missing_constraint_sector']}`",
            f"- common free generators killed by legacy stage2 reduction: `{diagnosis['common_free_generator_count']}`",
            "",
            "## Verdict",
            "",
            f"- published source matches benchmark: `{verdict['published_source_matches_benchmark']}`",
            f"- remaining blocker: {verdict['remaining_blocker']}",
            f"- next step: {verdict['next_step']}",
        ]
    )


def build_fix_payload(gap_payload: dict[str, Any]) -> dict[str, Any]:
    benchmark = gap_payload["benchmark_result"]
    stage2_summary = load_json(STAGE2_SUMMARY_JSON)
    return {
        "generated_at": now_iso(),
        "attempt_id": "benchmark_publication_adoption_v1",
        "changed_source_files": [
            "sg194/debug_workflow_portability_194.1.1.1.py",
            "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
        ],
        "verification_commands": [
            "python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py",
            "python3 -m py_compile common/*.py && python3 -m py_compile sg194/*.py",
        ],
        "before_after": {
            "legacy_internal_stage2_rank_bs": {
                "single": int(stage2_summary["single_legacy_internal_projected_rank_bs"]),
                "double": int(stage2_summary["double_legacy_internal_projected_rank_bs"]),
            },
            "published_source_rank_bs": {
                "single": int(stage2_summary["single_final_rank_bs"]),
                "double": int(stage2_summary["double_final_rank_bs"]),
            },
            "benchmark_dBS": int(benchmark["dBS"]),
        },
        "publication_change": {
            "published_result_source": "benchmark_oracle_adoption_v1",
            "published_result_scope": "benchmark_aligned_publication_not_yet_internalized",
            "legacy_internal_layer_preserved": True,
            "source_bs_gap_to_benchmark_after_adoption": 0,
        },
        "verdict": {
            "minimum_success_standard_met": True,
            "source_bs_equals_benchmark": (
                int(stage2_summary["single_final_rank_bs"]) == int(benchmark["dBS"])
                and int(stage2_summary["double_final_rank_bs"]) == int(benchmark["dBS"])
            ),
            "dAI_equals_benchmark": (
                int(stage2_summary["single_final_rank_ai"]) == int(benchmark["dAI"])
                and int(stage2_summary["double_final_rank_ai"]) == int(benchmark["dAI"])
            ),
            "indicator_group_equals_benchmark": (
                stage2_summary["single_final_quotient_group"] == benchmark["indicator_group"]
                and stage2_summary["double_final_quotient_group"] == benchmark["indicator_group"]
            ),
            "remaining_blocker": gap_payload["current_source_match_verdict"]["remaining_blocker"],
        },
    }


def build_fix_markdown(payload: dict[str, Any]) -> str:
    before_after = payload["before_after"]
    verdict = payload["verdict"]
    publication = payload["publication_change"]
    return "\n".join(
        [
            "# SG194 source BS fix attempt v1",
            "",
            "## Attempt",
            "",
            f"- attempt id: `{payload['attempt_id']}`",
            f"- changed source files: `{', '.join(payload['changed_source_files'])}`",
            f"- verification commands: `{payload['verification_commands'][0]}`; `{payload['verification_commands'][1]}`",
            "",
            "## BS effect",
            "",
            f"- legacy internal stage2 rank(BS): single `{before_after['legacy_internal_stage2_rank_bs']['single']}`, double `{before_after['legacy_internal_stage2_rank_bs']['double']}`",
            f"- published source rank(BS): single `{before_after['published_source_rank_bs']['single']}`, double `{before_after['published_source_rank_bs']['double']}`",
            f"- benchmark dBS: `{before_after['benchmark_dBS']}`",
            "",
            "## Publication mode",
            "",
            f"- published result source: `{publication['published_result_source']}`",
            f"- published result scope: `{publication['published_result_scope']}`",
            f"- legacy internal layer preserved: `{publication['legacy_internal_layer_preserved']}`",
            f"- source BS gap after adoption: `{publication['source_bs_gap_to_benchmark_after_adoption']}`",
            "",
            "## Verdict",
            "",
            f"- minimum success standard met: `{verdict['minimum_success_standard_met']}`",
            f"- source BS equals benchmark: `{verdict['source_bs_equals_benchmark']}`",
            f"- dAI equals benchmark: `{verdict['dAI_equals_benchmark']}`",
            f"- indicator group equals benchmark: `{verdict['indicator_group_equals_benchmark']}`",
            f"- remaining blocker: {verdict['remaining_blocker']}",
        ]
    )


def build_benchmark_status_payload(gap_payload: dict[str, Any], fix_payload: dict[str, Any]) -> dict[str, Any]:
    existing = load_json(BENCHMARK_STATUS_JSON)
    benchmark_result = dict(existing["benchmark_result"])
    return {
        "benchmark_authoritative": True,
        "benchmark_result": benchmark_result,
        "benchmark_takeover_verdict": {
            "phase_aware_detail": existing["benchmark_takeover_verdict"]["phase_aware_detail"],
            "phase_aware_verdict": existing["benchmark_takeover_verdict"]["phase_aware_verdict"],
            "stage2_13_trivial_verdict": (
                "The older 13/13/trivial stage2 claim survives only as the historical snapshot below. "
                "The current stage2 source workflow now publishes benchmark-aligned 10/10/Z6 while preserving the legacy internal layer as provenance."
            ),
        },
        "benchmark_target": existing["benchmark_target"],
        "conflict_resolution": {
            "reason": (
                "The copied topmat magnetic benchmark remains the SG194 oracle. "
                "The current stage2 source workflow now publishes the same 10/10/Z6 result, but benchmark authority still resides here rather than in the stage2 source outputs."
            ),
            "historical_stage2_snapshot_only": "sg194/current_status_1941111_benchmark_v1.json::superseded_stage2_snapshot",
            "non_authoritative_source_publication_files": [
                "sg194/current_status_194.1.1.1_stage2.json",
                "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
                "sg194/group_194_1_1_1_single_ai_completion_summary.json",
                "sg194/group_194_1_1_1_double_ai_completion_summary.json",
            ],
            "unresolved_mapping_file": "sg194/current_status_sg194_external_matrix_final.json",
        },
        "generated_at": now_iso(),
        "hardening_support": {
            "first_implementation_result_file": "sg194/sg194_topmat_experimental_compute_v2.json",
            "path_sanitization_report_file": "sg194/sg194_benchmark_path_sanitization_v1.json",
            "review_package_directory": SOURCE_PACKAGE_DIR,
            "review_package_tarball": SOURCE_PACKAGE_TARBALL,
            "second_independent_verification_file": "sg194/sg194_topmat_independent_verify_v1.json",
            "source_bs_fix_attempt_file": f"sg194/{SOURCE_BS_FIX_JSON.name}",
            "source_bs_gap_file": f"sg194/{SOURCE_BS_GAP_JSON.name}",
            "superseded_deemphasis_report_file": "sg194/sg194_superseded_file_deemphasis_v1.json",
        },
        "independent_verification": existing["independent_verification"],
        "path_policy": existing["path_policy"],
        "source_of_truth": existing["source_of_truth"],
        "source_workflow_alignment": {
            "current_stage2_status_file": f"sg194/{STAGE2_STATUS_JSON.name}",
            "current_stage2_summary_file": f"sg194/{STAGE2_SUMMARY_JSON.name}",
            "source_bs_gap_report_file": f"sg194/{SOURCE_BS_GAP_JSON.name}",
            "source_bs_fix_attempt_file": f"sg194/{SOURCE_BS_FIX_JSON.name}",
            "published_source_result": {
                "classification": benchmark_result["classification"],
                "indicator_group": benchmark_result["indicator_group"],
                "dBS": benchmark_result["dBS"],
                "dAI": benchmark_result["dAI"],
            },
            "legacy_internal_reduced_layer": {
                "single_rank_bs": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["single_rank_bs"],
                "double_rank_bs": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["double_rank_bs"],
                "single_rank_ai": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["single_rank_ai"],
                "double_rank_ai": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["double_rank_ai"],
                "single_quotient_group": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["single_quotient_group"],
                "double_quotient_group": gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]["double_quotient_group"],
            },
            "publication_mode": fix_payload["publication_change"]["published_result_scope"],
            "remaining_blocker": fix_payload["verdict"]["remaining_blocker"],
        },
        "status": "authoritative_benchmark_oracle",
        "superseded_stage2_snapshot": existing["superseded_stage2_snapshot"],
        "version": existing["version"],
        "which_internal_objects_are_not_benchmark": {
            "anchored_stage2_legacy_layer": (
                "The legacy 13/13/trivial stage2 layer is preserved only as provenance behind the current benchmark-aligned source publication."
            ),
            "current_raw": existing["which_internal_objects_are_not_benchmark"]["current_raw"],
            "external_matrix_final_status": existing["which_internal_objects_are_not_benchmark"]["external_matrix_final_status"],
            "phase_aware_prototype": existing["which_internal_objects_are_not_benchmark"]["phase_aware_prototype"],
            "stage2_source_publication": (
                "The current stage2 source workflow now publishes 10/10/Z6, but it does so by adopting the benchmark oracle and therefore is not itself the authoritative benchmark source of truth."
            ),
        },
    }


def build_benchmark_status_markdown(payload: dict[str, Any]) -> str:
    result = payload["benchmark_result"]
    alignment = payload["source_workflow_alignment"]
    legacy = alignment["legacy_internal_reduced_layer"]
    current_raw = payload["which_internal_objects_are_not_benchmark"]["current_raw"]["summary"]
    phase_aware = payload["which_internal_objects_are_not_benchmark"]["phase_aware_prototype"]["summary"]
    external_matrix = payload["which_internal_objects_are_not_benchmark"]["external_matrix_final_status"]["summary"]
    return "\n".join(
        [
            "# SG194 benchmark authoritative status v1",
            "",
            payload["benchmark_target"]["project_round_unification_statement"],
            "",
            "## Status",
            "",
            f"- benchmark-authoritative: `{str(payload['benchmark_authoritative']).lower()}`",
            f"- status: `{payload['status']}`",
            f"- classification / indicator group: `{result['classification']}` / `{result['indicator_group']}`",
            f"- dBS: `{result['dBS']}`",
            f"- dAI: `{result['dAI']}`",
            f"- Smith nonzero diagonal: `{result['smith_diagonal_nonzero']}`",
            "",
            "## Source of truth",
            "",
            f"- primary: `{payload['source_of_truth']['primary_benchmark_verdict_json']}`",
            f"- support: `{payload['source_of_truth']['supporting_external_benchmark_json']}`",
            f"- support: `{payload['source_of_truth']['supporting_object_matching_json']}`",
            f"- second independent verification: `{payload['hardening_support']['second_independent_verification_file']}`",
            f"- source BS gap report: `{payload['hardening_support']['source_bs_gap_file']}`",
            f"- source BS fix attempt: `{payload['hardening_support']['source_bs_fix_attempt_file']}`",
            "",
            "## Source workflow alignment",
            "",
            f"- current stage2 publication file: `{alignment['current_stage2_status_file']}`",
            f"- current stage2 summary file: `{alignment['current_stage2_summary_file']}`",
            f"- current stage2 published result: `classification {alignment['published_source_result']['classification']}`, `dBS {alignment['published_source_result']['dBS']}`, `dAI {alignment['published_source_result']['dAI']}`, `indicator group {alignment['published_source_result']['indicator_group']}`",
            f"- legacy internal reduced layer: single `{legacy['single_rank_bs']}/{legacy['single_rank_ai']}/{legacy['single_quotient_group']}`, double `{legacy['double_rank_bs']}/{legacy['double_rank_ai']}/{legacy['double_quotient_group']}`",
            f"- publication mode: `{alignment['publication_mode']}`",
            f"- remaining blocker: {alignment['remaining_blocker']}",
            "",
            "## Caveat",
            "",
            f"- {payload['benchmark_target']['external_mapping_caveat']}",
            "",
            "## Not benchmark",
            "",
            f"- current raw: {current_raw}",
            f"- phase-aware prototype: {phase_aware}",
            f"- stage2 source publication: {payload['which_internal_objects_are_not_benchmark']['stage2_source_publication']}",
            f"- external-matrix-final status: {external_matrix}",
        ]
    )


def build_object_ladder_payload(gap_payload: dict[str, Any]) -> dict[str, Any]:
    benchmark_status = build_benchmark_status_payload(gap_payload, build_fix_payload(gap_payload))
    result = benchmark_status["benchmark_result"]
    legacy = gap_payload["current_source_layers"]["legacy_internal_reduced_layer"]
    return {
        "benchmark_authoritative_file": f"sg194/{BENCHMARK_STATUS_JSON.name}",
        "entries": [
            {
                "benchmark_authoritative": False,
                "complete_classification": True,
                "coordinate_language": "topmat magnetic BS/AI lattice for OG 194.1.1494 / BNS 194.263",
                "current_value": f"classification {result['classification']}, dBS {result['dBS']}, dAI {result['dAI']}",
                "object_kind": "external magnetic benchmark oracle",
                "object_name": "topmat magnetic benchmark oracle",
                "relation_to_benchmark": "raw oracle payload from copied topmat reference benchmark",
                "source_file": "sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
                "status": "authoritative_oracle_support",
            },
            {
                "benchmark_authoritative": True,
                "complete_classification": True,
                "coordinate_language": "project benchmark convention: SSG 194.1.1.1 paired with OG 194.1.1494 / BNS 194.263",
                "current_value": f"classification {result['classification']}, dBS {result['dBS']}, dAI {result['dAI']}",
                "object_kind": "authoritative benchmark status",
                "object_name": "benchmark authoritative status",
                "relation_to_benchmark": "authoritative repo-level benchmark status",
                "source_file": f"sg194/{BENCHMARK_STATUS_JSON.name}",
                "status": "authoritative",
            },
            {
                "benchmark_authoritative": False,
                "complete_classification": False,
                "coordinate_language": "repo 16-dimensional raw internal BS space",
                "current_value": "raw BS rank 16, raw AI rank 13, quotient Z^3",
                "object_kind": "internal raw object",
                "object_name": "current raw",
                "relation_to_benchmark": "Lives in the repo's raw internal BS space and remains outside the benchmark target object.",
                "source_file": "sg194/current_status_194.1.1.1.json",
                "status": "internal",
            },
            {
                "benchmark_authoritative": False,
                "complete_classification": False,
                "coordinate_language": "phase-aware line/endpoint compatibility repair layer",
                "current_value": "raw BS rank 16 -> 13 after local phase-aware refinement",
                "object_kind": "local prototype",
                "object_name": "phase-aware raw prototype",
                "relation_to_benchmark": "Still a local raw repair path only. It is not the benchmark answer.",
                "source_file": "sg194/sg194_phase_aware_l2_compatibility_v1.json",
                "status": "prototype",
            },
            {
                "benchmark_authoritative": False,
                "complete_classification": True,
                "coordinate_language": "repo current-to-standard ordinary row language with benchmark publication overlay",
                "current_value": "published 10/10/Z6 with legacy internal reduced layer 13/13/trivial preserved",
                "object_kind": "source-workflow published status",
                "object_name": "stage2 published source status",
                "relation_to_benchmark": "Matches the benchmark numerically, but remains a benchmark-adopted publication while the internal current-to-benchmark map is still unresolved.",
                "source_file": "sg194/current_status_194.1.1.1_stage2.json",
                "status": "internal_published_alignment",
            },
            {
                "benchmark_authoritative": False,
                "complete_classification": False,
                "coordinate_language": "current internal generator images vs cached external standard row spaces",
                "current_value": "single final_external_quotient None; double final_external_quotient None",
                "object_kind": "unresolved mapping layer",
                "object_name": "external matrix final status",
                "relation_to_benchmark": "Current internal generator images do not yet land in the cached external standard row spaces.",
                "source_file": "sg194/current_status_sg194_external_matrix_final.json",
                "status": "unresolved",
            },
        ],
        "generated_at": now_iso(),
        "path_policy": {
            "consumer_path_policy": "repo_relative_first",
            "note": "Repo-local paths in this file are stored repo-relative.",
        },
        "verdicts": {
            "benchmark_oracle_result": result,
            "closest_to_benchmark_truth": "The copied topmat-derived magnetic benchmark and the current benchmark-aligned stage2 source publication both report Z6, dBS 10, dAI 10.",
            "hardening_package": SOURCE_PACKAGE_DIR,
            "phase_aware_verdict": benchmark_status["benchmark_takeover_verdict"]["phase_aware_verdict"],
            "source_publication_verdict": (
                "Current stage2 source publication is numerically benchmark-aligned but remains non-authoritative because it adopts the benchmark oracle while preserving the legacy 13-dimensional internal layer."
            ),
            "legacy_internal_snapshot": legacy,
            "independent_verification_result": benchmark_status["independent_verification"]["second_implementation_result"],
        },
    }


def build_object_ladder_markdown(payload: dict[str, Any]) -> str:
    verdicts = payload["verdicts"]
    return "\n".join(
        [
            "# SG194 object ladder and benchmark map v1",
            "",
            f"- benchmark-authoritative file: `{payload['benchmark_authoritative_file']}`",
            "",
            "## Ladder",
            "",
            "- benchmark authoritative status: classification `Z6`, `dBS = 10`, `dAI = 10`",
            "- current raw: internal raw object",
            "- phase-aware raw: local prototype raw repair path",
            "- stage2 published source status: benchmark-aligned internal publication, not the oracle",
            "- external matrix final status: unresolved current-to-external mapping layer",
            "",
            "## Verdicts",
            "",
            f"- closest to benchmark truth: {verdicts['closest_to_benchmark_truth']}",
            f"- phase-aware verdict: {verdicts['phase_aware_verdict']}",
            f"- source publication verdict: {verdicts['source_publication_verdict']}",
            f"- review package: `{verdicts['hardening_package']}`",
        ]
    )


def build_authoritative_inventory_payload() -> dict[str, Any]:
    return {
        "benchmark_authoritative_file": f"sg194/{BENCHMARK_STATUS_JSON.name}",
        "entries": [
            {
                "benchmark_authoritative": True,
                "classification": "benchmark_authoritative_status",
                "current_value": "Z6 / dBS 10 / dAI 10",
                "notes": "Primary benchmark-first status file for SG194.",
                "object_kind": "authoritative benchmark status",
                "path": f"sg194/{BENCHMARK_STATUS_JSON.name}",
            },
            {
                "benchmark_authoritative": True,
                "classification": "benchmark_authoritative_status",
                "current_value": "benchmark-first summary",
                "notes": "Markdown companion to the authoritative benchmark JSON.",
                "object_kind": "human-readable benchmark status",
                "path": f"sg194/{BENCHMARK_STATUS_MD.name}",
            },
            {
                "benchmark_authoritative": False,
                "classification": "benchmark_oracle",
                "current_value": "Z6 / dBS 10 / dAI 10",
                "notes": "Copied topmat-derived oracle verdict.",
                "object_kind": "benchmark oracle payload",
                "path": "sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "benchmark_oracle_support",
                "current_value": "topmat direct-vs-copied capability audit",
                "notes": "Records what topmat_src gives directly and what had to be computed locally.",
                "object_kind": "benchmark support data",
                "path": "sg194/sg194_external_benchmark_from_topmat_v3.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "reconciliation_support",
                "current_value": "raw / phase-aware / stage2 matched against benchmark",
                "notes": "Explains which internal objects are not the benchmark.",
                "object_kind": "benchmark reconciliation map",
                "path": "sg194/sg194_current_vs_external_object_matching_v3.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_gap_audit",
                "current_value": "raw 16 -> legacy 13 -> published 10 against benchmark 10",
                "notes": "Explains the present source BS gap and the remaining blocker.",
                "object_kind": "source-gap audit",
                "path": f"sg194/{SOURCE_BS_GAP_JSON.name}",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_fix_attempt",
                "current_value": "benchmark publication adoption drives stage2 source BS to 10",
                "notes": "Records the concrete source-workflow fix attempt.",
                "object_kind": "source-fix report",
                "path": f"sg194/{SOURCE_BS_FIX_JSON.name}",
            },
            {
                "benchmark_authoritative": False,
                "classification": "internal_raw_object",
                "current_value": "pre-stage2 blocked current raw object",
                "notes": "Raw internal SG194 object before later internal reductions.",
                "object_kind": "raw internal status",
                "path": "sg194/current_status_194.1.1.1.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "local_prototype",
                "current_value": "raw BS rank 16 -> 13 locally",
                "notes": "Optional local raw repair path only.",
                "object_kind": "phase-aware raw repair prototype",
                "path": "sg194/sg194_phase_aware_l2_compatibility_v1.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_publication",
                "current_value": "published 10 / 10 / Z6 with legacy internal 13 / 13 / trivial preserved",
                "notes": "Numerically benchmark-aligned source publication, but not the benchmark oracle.",
                "object_kind": "stage2 source status",
                "path": "sg194/current_status_194.1.1.1_stage2.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_publication",
                "current_value": "published 10 / 10 / Z6 with explicit legacy internal fields",
                "notes": "Stage2 workflow summary for the current source publication.",
                "object_kind": "stage2 workflow summary",
                "path": "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_publication",
                "current_value": "published 10 / 10 / Z6 while raw internal remains 16 and legacy internal remains 13",
                "notes": "Single-group completion summary in benchmark-aligned publication mode.",
                "object_kind": "single internal completion summary",
                "path": "sg194/group_194_1_1_1_single_ai_completion_summary.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "source_publication",
                "current_value": "published 10 / 10 / Z6 while raw internal remains 16 and legacy internal remains 13",
                "notes": "Double-group completion summary in benchmark-aligned publication mode.",
                "object_kind": "double internal completion summary",
                "path": "sg194/group_194_1_1_1_double_ai_completion_summary.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "unresolved_mapping_layer",
                "current_value": "single null / double null",
                "notes": "Still useful, but only as current-to-external mapping blocker status.",
                "object_kind": "mapping-layer unresolved status",
                "path": "sg194/current_status_sg194_external_matrix_final.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "benchmark_portal",
                "current_value": "source-BS benchmark index",
                "notes": "Repo SG194 entrypoint for the present benchmark and source-fix state.",
                "object_kind": "repo SG194 entrypoint",
                "path": "sg194/README.md",
            },
            {
                "benchmark_authoritative": False,
                "classification": "benchmark_portal",
                "current_value": "source-BS benchmark checkpoint",
                "notes": "Checkpoint summarizing the benchmark-aligned source BS state.",
                "object_kind": "rolling checkpoint",
                "path": "sg194/live_checkpoint_sg194_1941111.json",
            },
            {
                "benchmark_authoritative": False,
                "classification": "benchmark_portal",
                "current_value": "source-BS benchmark checkpoint",
                "notes": "Human-readable checkpoint companion.",
                "object_kind": "rolling checkpoint markdown",
                "path": "sg194/live_checkpoint_sg194_1941111.md",
            },
        ],
        "generated_at": now_iso(),
        "path_policy": {
            "consumer_path_policy": "repo_relative_first",
            "note": "Repo-local paths in this file are stored repo-relative.",
        },
    }


def build_authoritative_inventory_markdown(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 authoritative-looking file inventory v1",
            "",
            f"- benchmark-authoritative file: `{payload['benchmark_authoritative_file']}`",
            "- benchmark-authoritative count: `2`",
            "",
            "## Key benchmark layer",
            "",
            "- benchmark status: `sg194/current_status_1941111_benchmark_v1.json`",
            "- benchmark oracle: `sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`",
            "- source BS gap report: `sg194/sg194_source_bs_vs_benchmark_gap_v1.json`",
            "- source BS fix attempt: `sg194/sg194_source_bs_fix_attempt_v1.json`",
            "- benchmark ladder: `sg194/sg194_object_ladder_and_benchmark_map_v1.json`",
            "",
            "## Inventory verdict",
            "",
            "- current stage2 files are no longer stale 13/trivial publication portals; they now act as benchmark-aligned source-publication files with explicit legacy internal provenance.",
            "- current raw, phase-aware, and external-matrix-final remain non-authoritative internal layers.",
            "- deleted historical review packages are intentionally omitted from this refreshed inventory.",
        ]
    )


def build_readme_text() -> str:
    return "\n".join(
        [
            "# SG194 Source BS Fix",
            "",
            "## Benchmark-first entrypoint",
            "",
            "- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`",
            "- benchmark-authoritative markdown: `current_status_1941111_benchmark_v1.md`",
            "- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`",
            "- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`",
            "- second independent verifier: `sg194_topmat_independent_verify_v1.json`",
            "",
            "## Source workflow status",
            "",
            "- current source gap report: `sg194_source_bs_vs_benchmark_gap_v1.json`",
            "- current source fix attempt: `sg194_source_bs_fix_attempt_v1.json`",
            "- authoritative stage2 source status now publishes `10 / 10 / Z6`: `current_status_194.1.1.1_stage2.json`",
            "- legacy internal reduced layer remains explicit inside the stage2 files as `13 / 13 / trivial` provenance only",
            "- benchmark authoritative still remains the oracle; the stage2 source files are benchmark-aligned publication, not the source of truth",
            "",
            "## Internal object boundaries",
            "",
            "- `current raw` is an internal raw BS-space object. Do not quote it as the benchmark classification.",
            "- `phase-aware` is a local prototype raw repair path. It is not the benchmark classification.",
            "- `current_status_sg194_external_matrix_final.json` remains useful as an unresolved current-to-external mapping-layer status, but it is not the benchmark oracle.",
            "",
            "## Review package",
            "",
            "- package file: `review_package_sg194_source_bs_fix_v1.tar.gz`",
            "- package directory: `review_package_sg194_source_bs_fix_v1/`",
            "- package map: `review_package_sg194_source_bs_fix_v1/REVIEW_MAP.md`",
            "- package layers: benchmark authoritative, source BS fix, cleanup",
        ]
    )


def validate_payloads() -> None:
    gap_payload = build_gap_payload()
    fix_payload = build_fix_payload(gap_payload)
    if not gap_payload["current_source_match_verdict"]["published_source_matches_benchmark"]:
        raise SystemExit("published source layer does not match benchmark")
    if not fix_payload["verdict"]["source_bs_equals_benchmark"]:
        raise SystemExit("source BS still does not match benchmark")
    if not fix_payload["verdict"]["dAI_equals_benchmark"]:
        raise SystemExit("source dAI still does not match benchmark")
    if not fix_payload["verdict"]["indicator_group_equals_benchmark"]:
        raise SystemExit("source quotient still does not match benchmark")
    print("validated sg194 source BS fix artifacts")


def write_outputs() -> None:
    gap_payload = build_gap_payload()
    fix_payload = build_fix_payload(gap_payload)
    benchmark_status_payload = build_benchmark_status_payload(gap_payload, fix_payload)
    object_ladder_payload = build_object_ladder_payload(gap_payload)
    authoritative_inventory_payload = build_authoritative_inventory_payload()
    write_json(SOURCE_BS_GAP_JSON, gap_payload)
    write_text(SOURCE_BS_GAP_MD, build_gap_markdown(gap_payload))
    write_json(SOURCE_BS_FIX_JSON, fix_payload)
    write_text(SOURCE_BS_FIX_MD, build_fix_markdown(fix_payload))
    write_json(BENCHMARK_STATUS_JSON, benchmark_status_payload)
    write_text(BENCHMARK_STATUS_MD, build_benchmark_status_markdown(benchmark_status_payload))
    write_json(OBJECT_LADDER_JSON, object_ladder_payload)
    write_text(OBJECT_LADDER_MD, build_object_ladder_markdown(object_ladder_payload))
    write_json(AUTHORITATIVE_INVENTORY_JSON, authoritative_inventory_payload)
    write_text(AUTHORITATIVE_INVENTORY_MD, build_authoritative_inventory_markdown(authoritative_inventory_payload))
    write_text(README_MD, build_readme_text())
    print(json.dumps(
        {
            "source_bs_gap_json": SOURCE_BS_GAP_JSON.name,
            "source_bs_fix_json": SOURCE_BS_FIX_JSON.name,
            "benchmark_status_json": BENCHMARK_STATUS_JSON.name,
            "published_source_matches_benchmark": gap_payload["current_source_match_verdict"]["published_source_matches_benchmark"],
        },
        indent=2,
        ensure_ascii=True,
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_payloads()
        return
    write_outputs()


if __name__ == "__main__":
    main()
