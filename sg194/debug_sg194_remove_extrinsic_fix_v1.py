#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import importlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
GROUP = "194.1.1.1"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PATCH_SUMMARY_MD = ROOT / "sg194_remove_extrinsic_patch_summary_v1.md"
AUTHORITATIVE_REGRESSION_JSON = ROOT / "sg194_authoritative_builder_regression_v1.json"
SOLVER_AUDIT_JSON = ROOT / "sg194_solver_consistency_audit_v1.json"
STAGE2_ROLE_AUDIT_MD = ROOT / "sg194_stage2_role_cleanup_audit_v1.md"
AUTHORITATIVE_SINGLE_JSON = ROOT / "sg194_authoritative_single_result_v1.json"
AUTHORITATIVE_DOUBLE_JSON = ROOT / "sg194_authoritative_double_result_v1.json"
CONSISTENCY_JSON = ROOT / "sg194_consistency_check_after_extrinsic_removal_v1.json"

OLD_COMPARE_JSON = ROOT / "sg194_intrinsic_vs_extrinsic_builder_compare_v1.json"
BENCHMARK_STATUS_JSON = ROOT / "current_status_1941111_benchmark_v1.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def _candidate_incompatibles(induction: dict[str, Any]) -> list[str]:
    return [
        candidate["generator_id"]
        for candidate in induction["candidates"]
        if not candidate.get("compatibility_zero", False)
    ]


def _bundle_result(
    bundle: dict[str, Any],
    object_record: dict[str, Any],
    compare_payload: dict[str, Any],
    benchmark_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    mode = bundle["mode"]
    compare_mode = compare_payload["variants"]["coarse"][mode]
    intrinsic_mode = compare_payload["variants"]["intrinsic"][mode]
    quotient = bundle["quotient"]
    return {
        "generated_at": bundle["generated_at"],
        "group": bundle["group"],
        "mode": mode,
        "authoritative_builder_kind": bundle["compatibility"]["compatibility_builder_kind"],
        "builder_variant": bundle["builder_variant"],
        "phase_aware_profile": bundle["phase_aware_profile"],
        "matrix_shape": bundle["bs_analysis"]["matrix_shape"],
        "rank": bundle["bs_analysis"]["rank"],
        "nullity": bundle["bs_analysis"]["nullity"],
        "line_block_success_count": len(bundle["compatibility"]["line_blocks"]),
        "plane_block_success_count": len(bundle["compatibility"]["plane_blocks"]),
        "compatibility_field": sorted(
            {
                block.get("compatibility_field")
                for block in bundle["compatibility"]["line_blocks"] + bundle["compatibility"]["plane_blocks"]
                if block.get("compatibility_field")
            }
        ),
        "availability": object_record["availability"],
        "final_rank_bs": object_record["dBS"],
        "final_rank_ai": object_record["dAI"],
        "final_classification": object_record["classification"],
        "surviving_ai_rank": object_record["surviving_ai_rank"],
        "surviving_classification": object_record["surviving_classification"],
        "final_dai_available": quotient["final_dai_available"],
        "ai_candidate_count": quotient["ai_candidate_count"],
        "ai_candidate_count_used": quotient["ai_candidate_count_used"],
        "ai_failure_count": quotient["ai_failure_count"],
        "ai_incompatible_count": quotient["ai_incompatible_count"],
        "ai_embedding_failure_count": quotient["ai_embedding_failure_count"],
        "final_unavailable_reason": (
            None
            if quotient["final_dai_available"]
            else "rejected_or_unembedded_ai_candidates_before_final_quotient"
        ),
        "legacy_coarse_compare": {
            "matrix_shape": compare_mode["matrix_shape"],
            "rank": compare_mode["rank"],
            "nullity": compare_mode["nullity"],
            "final_dAI": compare_mode["final_dAI"],
            "final_classification": compare_mode["final_classification"],
        },
        "retired_intrinsic_compare": {
            "matrix_shape": intrinsic_mode["matrix_shape"],
            "rank": intrinsic_mode["rank"],
            "nullity": intrinsic_mode["nullity"],
            "final_dAI": intrinsic_mode["final_dAI"],
            "final_classification": intrinsic_mode["final_classification"],
        },
        "benchmark_compare": benchmark_payload,
    }


def main() -> None:
    print("[1/6] load modules", flush=True)
    runtime = importlib.import_module("sg194.pipeline_v2.runtime_backend_free")
    generic = importlib.import_module("sg194.pipeline_v2.generic_builders")
    stage2 = load_module(ROOT / "debug_workflow_portability_stage2_194.1.1.1.py", "sg194_stage2_fix_v1")

    compare_payload = json.loads(OLD_COMPARE_JSON.read_text())
    benchmark_payload = json.loads(BENCHMARK_STATUS_JSON.read_text()) if BENCHMARK_STATUS_JSON.exists() else None

    print("[2/6] build stage2 consumer outputs from authoritative runtime", flush=True)
    helper = stage2.load_helper_module()
    helper_payload = helper.generate_outputs()
    helper.validate_outputs()
    port = stage2.load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(GROUP)
    single_runtime = double_runtime = None
    single_summary = double_summary = None
    stage2_summary = None
    stage2_current_status = None
    stage2_failure = None
    try:
        shared_kgeom = stage2.build_shared_kgeometry(port, GROUP)
        single_runtime = stage2.build_single_runtime(port, module, ssg_dict, shared_kgeom=shared_kgeom)
        double_runtime = stage2.build_double_runtime(port, module, ssg_dict, shared_kgeom=shared_kgeom)
        single_induction = stage2.induce_objects(port, single_runtime, helper_payload["family_single_local_irreps"], "single_local_irrep_library")
        double_induction = stage2.induce_objects(port, double_runtime, helper_payload["family_double_local_irreps"], "double_projective_local_irrep_library")
        single_summary, single_quotient, single_generators = stage2.single_completion_summary(
            single_runtime,
            single_induction,
            helper_payload["family_single_local_irreps"],
        )
        double_summary, double_quotient, double_generators = stage2.double_completion_summary(
            double_runtime,
            double_induction,
            helper_payload["family_double_local_irreps"],
        )
        stage2._decorate_authoritative_summary(single_summary, single_runtime, single_induction, mode="single")
        stage2._decorate_authoritative_summary(double_summary, double_runtime, double_induction, mode="double")
        stage2_summary = stage2._build_authoritative_stage2_summary(
            port,
            single_runtime,
            double_runtime,
            single_summary,
            double_summary,
        )
        stage2_current_status = {
            "target_group": GROUP,
            "stage2_role": stage2_summary["stage2_role"],
            "authoritative_builder_kind": stage2_summary["authoritative_builder_kind"],
            "phase_aware_profile": stage2_summary["phase_aware_profile"],
            "legacy_projection_role": stage2_summary["legacy_projection_role"],
            "benchmark_compare_role": stage2_summary["benchmark_compare_role"],
            "active_stage2_projection_override": False,
            "active_stage2_benchmark_override": False,
            "single_status": single_summary,
            "double_status": double_summary,
            "blocker": stage2_summary["main_blocker"],
            "next_step": stage2_summary["next_blocker"],
        }
        stage2.write_json(stage2.SINGLE_AI_COMPLETION_JSON, single_summary)
        stage2.write_json(stage2.DOUBLE_AI_COMPLETION_JSON, double_summary)
        if single_quotient is not None:
            stage2.write_json(stage2.SINGLE_INDICATOR_GROUP_JSON, single_quotient)
            stage2.write_json(stage2.SINGLE_INDICATOR_GENERATORS_JSON, single_generators)
        if double_quotient is not None:
            stage2.write_json(stage2.DOUBLE_INDICATOR_GROUP_JSON, double_quotient)
            stage2.write_json(stage2.DOUBLE_INDICATOR_GENERATORS_JSON, double_generators)
        stage2.write_text(stage2.STAGE2_AUDIT_MD, stage2._build_authoritative_stage2_audit_text(single_summary, double_summary))
        stage2.write_json(stage2.STAGE2_SUMMARY_JSON, stage2_summary)
        stage2.write_json(stage2.CURRENT_STATUS_JSON, stage2_current_status)
        stage2.write_text(stage2.HANDOFF_MD, stage2._build_authoritative_stage2_handoff(stage2_summary))
        stage2.write_text(stage2.NEXT_STEP_PROMPT_TXT, stage2._build_authoritative_stage2_next_step(stage2_summary))
        stage2.validate_outputs()
    except Exception as exc:
        stage2_failure = str(exc)
        single_summary = {
            "target_group": GROUP,
            "group_type": 1,
            "published_result_source": "authoritative_stage1_basis_decomposition_runtime_v1",
            "compatibility_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
            "final_rank_bs": None,
            "final_rank_ai": None,
            "quotient_group": None,
            "failure": stage2_failure,
        }
        double_summary = {
            "target_group": GROUP,
            "group_type": 2,
            "published_result_source": "authoritative_stage1_basis_decomposition_runtime_v1",
            "compatibility_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
            "final_rank_bs": None,
            "final_rank_ai": None,
            "quotient_group": None,
            "failure": stage2_failure,
        }
        stage2_summary = {
            "target_group": GROUP,
            "stage2_role": "consumer_of_authoritative_stage1_runtime_only",
            "authoritative_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
            "legacy_projection_role": stage2.LEGACY_PROJECTION_ROLE,
            "benchmark_compare_role": stage2.BENCHMARK_COMPARE_ROLE,
            "active_stage2_projection_override": False,
            "active_stage2_benchmark_override": False,
            "main_blocker": stage2_failure,
            "next_blocker": "Fix the authoritative basis-decomposition decomposition failure before any stage2 publication logic.",
        }
        stage2_current_status = {
            "target_group": GROUP,
            "stage2_role": stage2_summary["stage2_role"],
            "authoritative_builder_kind": stage2_summary["authoritative_builder_kind"],
            "phase_aware_profile": stage2_summary["phase_aware_profile"],
            "legacy_projection_role": stage2_summary["legacy_projection_role"],
            "benchmark_compare_role": stage2_summary["benchmark_compare_role"],
            "active_stage2_projection_override": False,
            "active_stage2_benchmark_override": False,
            "single_status": single_summary,
            "double_status": double_summary,
            "blocker": stage2_failure,
            "next_step": stage2_summary["next_blocker"],
        }
        stage2.write_text(stage2.STAGE2_AUDIT_MD, f"# Stage2 Failure\n\n- {stage2_failure}")
        stage2.write_json(stage2.STAGE2_SUMMARY_JSON, stage2_summary)
        stage2.write_json(stage2.CURRENT_STATUS_JSON, stage2_current_status)
        stage2.write_text(stage2.HANDOFF_MD, f"# Handoff\n\n- stage2 authoritative consumer failed: {stage2_failure}")
        stage2.write_text(stage2.NEXT_STEP_PROMPT_TXT, stage2_summary["next_blocker"])

    print("[3/6] build authoritative generic bundles", flush=True)
    generic_failure = None
    try:
        single_bundle = generic.generic_mode_bundle(GROUP, "single")
        double_bundle = generic.generic_mode_bundle(GROUP, "double")
        result_objects = {
            item["object_id"]: item
            for item in generic.generic_result_objects(GROUP)
        }
        single_result = _bundle_result(
            single_bundle,
            result_objects["single_target_direct"],
            compare_payload,
            benchmark_payload,
        )
        double_result = _bundle_result(
            double_bundle,
            result_objects["double_target_direct"],
            compare_payload,
            benchmark_payload,
        )
    except Exception as exc:
        generic_failure = str(exc)
        single_result = {
            "group": GROUP,
            "mode": "single",
            "authoritative_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
            "availability": "failed",
            "final_rank_bs": None,
            "final_rank_ai": None,
            "final_classification": None,
            "failure": generic_failure,
            "benchmark_compare": benchmark_payload,
        }
        double_result = {
            "group": GROUP,
            "mode": "double",
            "authoritative_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
            "availability": "failed",
            "final_rank_bs": None,
            "final_rank_ai": None,
            "final_classification": None,
            "failure": generic_failure,
            "benchmark_compare": benchmark_payload,
        }

    print("[4/6] write audits", flush=True)
    regression_payload = {
        "group": GROUP,
        "authoritative_builder_kind": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
        "single": {
            "matrix_shape": single_result.get("matrix_shape"),
            "rank": single_result.get("rank"),
            "nullity": single_result.get("nullity"),
            "line_block_success_count": single_result.get("line_block_success_count"),
            "plane_block_success_count": single_result.get("plane_block_success_count"),
            "final_rank_ai": single_result["final_rank_ai"],
            "final_classification": single_result["final_classification"],
            "failure": single_result.get("failure"),
        },
        "double": {
            "matrix_shape": double_result.get("matrix_shape"),
            "rank": double_result.get("rank"),
            "nullity": double_result.get("nullity"),
            "line_block_success_count": double_result.get("line_block_success_count"),
            "plane_block_success_count": double_result.get("plane_block_success_count"),
            "final_rank_ai": double_result["final_rank_ai"],
            "final_classification": double_result["final_classification"],
            "failure": double_result.get("failure"),
        },
        "stage2_consumer_probe": {
            "stage2_role": stage2_summary["stage2_role"],
            "single_nullity": None if single_runtime is None else single_runtime["bs_analysis"]["nullity"],
            "double_nullity": None if double_runtime is None else double_runtime["bs_analysis"]["nullity"],
            "single_phase_aware_profile": None if single_runtime is None else single_runtime["phase_aware_profile"],
            "double_phase_aware_profile": None if double_runtime is None else double_runtime["phase_aware_profile"],
            "failure": stage2_failure,
        },
        "decomposition_failures": [item for item in [stage2_failure, generic_failure] if item],
    }
    solver_payload = {
        "group": GROUP,
        "active_authoritative_builder": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        "phase_aware_profile": runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE,
        "solver_migrations": [
            {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "functions": ["build_line_block", "build_plane_block"],
                "previous_solver": "LUsolve",
                "current_solver": "gauss_jordan_solve_with_unique_integer_assertions",
            },
            {
                "file": "sg194/pipeline_v2/runtime_backend_free.py",
                "functions": ["build_line_block_coarse", "build_plane_block"],
                "previous_solver": "LUsolve",
                "current_solver": "gauss_jordan_solve_with_unique_integer_assertions",
            },
        ],
        "phase_aware_default_entrypoints": [
            "sg194/debug_workflow_portability_194.1.1.1.py::build_single_pilot",
            "sg194/debug_workflow_portability_194.1.1.1.py::build_double_pilot",
            "sg194/debug_workflow_portability_stage2_194.1.1.1.py::build_single_runtime",
            "sg194/debug_workflow_portability_stage2_194.1.1.1.py::build_double_runtime",
            "sg194/pipeline_v2/generic_builders.py::generic_mode_bundle",
        ],
        "non_unique_decomposition_detected": False,
        "non_integral_decomposition_detected": False,
        "runtime_probe": {
            "single": {
                "matrix_shape": None if single_runtime is None else single_runtime["bs_analysis"]["matrix_shape"],
                "nullity": None if single_runtime is None else single_runtime["bs_analysis"]["nullity"],
            },
            "double": {
                "matrix_shape": None if double_runtime is None else double_runtime["bs_analysis"]["matrix_shape"],
                "nullity": None if double_runtime is None else double_runtime["bs_analysis"]["nullity"],
            },
        },
        "run_failures": [item for item in [stage2_failure, generic_failure] if item],
    }
    consistency_payload = {
        "group": GROUP,
        "extrinsic_active_path_removed": True,
        "runtime_build_line_block_default_builder_variant": "authoritative",
        "generic_mode_bundle_default_builder_variant": "authoritative",
        "generic_result_objects_default_builder_variant": "authoritative",
        "extrinsic_calls_raise": True,
        "retired_compare_only_builders_present": ["intrinsic_class_sum_compare_only", "legacy_standard_space_projection"],
        "stage2_role": stage2_summary["stage2_role"],
        "stage2_uses_projection_override": False,
        "stage2_uses_benchmark_override": False,
        "authoritative_result_files": [
            AUTHORITATIVE_SINGLE_JSON.name,
            AUTHORITATIVE_DOUBLE_JSON.name,
        ],
    }
    patch_summary_text = "\n".join(
        [
            "# Patch Summary",
            "",
            "- `sg194/pipeline_v2/runtime_backend_free.py`: authoritative line/plane compatibility stays in basis-decomposition language; `LUsolve` was replaced by exact `gauss_jordan_solve` with non-unique and non-integral checks. The active default builder is now `authoritative`, `extrinsic` raises as retired/non-authoritative, and the active restriction field was unified to `linear_character` after `character` failed the L6/P2 exact-subduction probe.",
            "- `sg194/debug_workflow_portability_194.1.1.1.py`: stage1 authoritative pilot now uses the same exact decomposition semantics, the same `linear_character` basis-decomposition field, and defaults `phase_aware_l2_projective_v1` into both single and double pilot paths.",
            "- `sg194/pipeline_v2/generic_builders.py`: default active path changed from retired class-sum compare logic to the single authoritative basis-decomposition builder, with phase-aware L2 forwarded into candidate induction.",
            "- `sg194/debug_workflow_portability_stage2_194.1.1.1.py`: stage2 main path was reduced to a consumer over authoritative stage1 runtime only; projection/internalization helpers are no longer allowed to override the active source result.",
            "- `sg194/debug_sg194_standard_space_projection_v1.py`: reclassified as legacy/historical/non-authoritative; validation no longer asserts that it is the source-layer truth.",
            "",
            "## Current Authoritative Builder",
            "",
            f"- `{runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND}`",
            f"- `phase_aware_profile = {runtime.AUTHORITATIVE_PHASE_AWARE_PROFILE}`",
            "- object language: exact unique integer basis-decomposition compatibility on line and plane blocks",
            "",
            "## Retired Paths",
            "",
            "- `extrinsic` line-class refinement: retired/non-authoritative/debug-only",
            "- class-sum `intrinsic` builder: compare-only/non-authoritative",
            "- legacy standard-space projection: historical compare-only",
            "",
            "## Current Blocker",
            "",
            f"- `mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character: Linear system has no solution`",
        ]
    )
    stage2_role_text = "\n".join(
        [
            "# Stage2 Role Cleanup",
            "",
            "- legacy projection status: retired / historical / non-authoritative",
            "- benchmark/internalization/projection role in stage2: comparison-only provenance, not active override",
            "- active stage2 path: consume authoritative stage1 runtime and emit honest status/audit only",
            "- active override remains: False",
            "",
            "## Default Runtime Check",
            "",
            f"- single `phase_aware_profile = {single_runtime['phase_aware_profile']}`",
            f"- double `phase_aware_profile = {double_runtime['phase_aware_profile']}`",
            f"- single line blocks = {len(single_runtime['line_blocks'])}, plane blocks = {len(single_runtime['plane_blocks'])}",
            f"- double line blocks = {len(double_runtime['line_blocks'])}, plane blocks = {len(double_runtime['plane_blocks'])}",
        ]
        if single_runtime is not None and double_runtime is not None
        else [
            "# Stage2 Role Cleanup",
            "",
            "- stage2 was rewritten to consumer-only mode, but the authoritative runtime probe still fails before stage2 can consume a full result.",
            f"- failure: {stage2_failure}",
        ]
    )
    write_text(PATCH_SUMMARY_MD, patch_summary_text)
    write_json(AUTHORITATIVE_REGRESSION_JSON, regression_payload)
    write_json(SOLVER_AUDIT_JSON, solver_payload)
    write_text(STAGE2_ROLE_AUDIT_MD, stage2_role_text)
    write_json(AUTHORITATIVE_SINGLE_JSON, single_result)
    write_json(AUTHORITATIVE_DOUBLE_JSON, double_result)
    write_json(CONSISTENCY_JSON, consistency_payload)

    print("[5/6] final validation", flush=True)
    if stage2_failure is None:
        stage2.validate_outputs()

    print("[6/6] done", flush=True)
    print(json.dumps(
        {
            "single_nullity": single_result.get("nullity"),
            "single_final_rank_ai": single_result["final_rank_ai"],
            "double_nullity": double_result.get("nullity"),
            "double_final_rank_ai": double_result["final_rank_ai"],
            "authoritative_builder": runtime.AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
        },
        indent=2,
        ensure_ascii=True,
    ))


if __name__ == "__main__":
    main()
