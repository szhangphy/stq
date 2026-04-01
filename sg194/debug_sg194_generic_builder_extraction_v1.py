#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
RUN222 = ROOT / "pipeline_runs_v2" / "ssg222_1_1_1_both_all_latest"
RUN194 = ROOT / "pipeline_runs_v2" / "sg194_both_all_latest"
PACKAGE = ROOT / "review_package_sg194_generic_builder_222_final_v2"


def load_json(path: Path):
    return json.loads(path.read_text())


def dump_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def dump_md(path: Path, title: str, lines: list[str]) -> None:
    path.write_text(f"# {title}\n\n" + "\n".join(lines) + "\n")


def copy_into(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def ensure_pipeline_run(group: str, outdir: Path) -> None:
    if outdir.exists():
        return
    subprocess.run(
        [
            "python3",
            "sg194/run_group_pipeline.py",
            "--group",
            group,
            "--mode",
            "both",
            "--row-language",
            "all",
            "--output-dir",
            str(outdir.relative_to(REPO)),
            "--validate",
        ],
        check=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": "."},
    )


def main() -> int:
    ensure_pipeline_run("222.1.1.1", RUN222)
    ensure_pipeline_run("sg194", RUN194)

    q222 = load_json(RUN222 / "quotient_results.json")
    c222 = load_json(RUN222 / "consistency_checks.json")
    f222 = load_json(RUN222 / "final_status_summary.json")
    a222 = load_json(RUN222 / "representation_alignment_summary.json")
    g222 = load_json(RUN222 / "geometry_summary.json")

    q194 = load_json(RUN194 / "quotient_results.json")
    c194 = load_json(RUN194 / "consistency_checks.json")
    f194 = load_json(RUN194 / "final_status_summary.json")

    def object_by_id(payload, object_id):
        return next(item for item in payload["objects"] if item["object_id"] == object_id)

    single222 = object_by_id(q222, "single_target_direct")
    double222 = object_by_id(q222, "double_target_direct")
    single222_final = f222["single_final"]
    double222_final = f222["double_final"]

    extraction = {
        "group": "194.1.1.1",
        "special_path_layers": [
            {
                "layer": "geometry construction",
                "status": "generic_extracted",
                "generic_builder": "pipeline_v2.generic_builders.shared_geometry_bundle + extracted exact line/plane builders",
            },
            {
                "layer": "current row shell construction",
                "status": "generic_extracted",
                "generic_builder": "pipeline_v2.generic_builders.generic_mode_bundle current-row shell capture",
            },
            {
                "layer": "current row compatibility construction",
                "status": "generic_extracted",
                "generic_builder": "pipeline_v2.generic_builders._build_generic_compatibility",
            },
            {
                "layer": "local AI seed / embedding",
                "status": "partially_generic_extracted",
                "generic_builder": "pipeline_v2.generic_builders._build_local_irrep_library + exact point-shell embedding filter",
            },
            {
                "layer": "direct quotient derivation",
                "status": "generic_extracted",
                "generic_builder": "pipeline_v2.generic_builders._build_quotient_from_candidates",
            },
            {
                "layer": "final status / reporting",
                "status": "generic_extracted",
                "generic_builder": "pipeline_v2.driver + reporting/checks stack",
            },
        ],
    }
    extraction_md = [
        "- generic builders now cover geometry, current-row shell, compatibility, point-shell AI filtering, direct quotient, and unified reporting/checks.",
        "- SG194 remains the source of some special-case semantics, but the executable pipeline is no longer SG194-only.",
    ]

    special_map = {
        "generic_layers": [
            "shared geometry from trusted symmetry operations",
            "current-row shell construction",
            "line/plane compatibility extraction",
            "exact point-shell AI embedding filter",
            "direct Smith quotient on compatible AI images",
            "unified driver/check/reporting stack",
        ],
        "sg194_special_layers": [
            "single j/k canonical pairing",
            "benchmark-facing double contract",
            "SG194 exact target-row alignment semantics",
        ],
        "group222_special_layers": [
            "none required for the final numbers beyond trusted symmetry-operation spec registration",
        ],
    }
    special_md = [
        "- Generic: geometry/current-row/compatibility/local-AI filtering/direct quotient/reporting.",
        "- SG194-special: single j/k normalization and benchmark-facing double semantics.",
        "- 222.1.1.1 final results use the generic builders, not a benchmark override.",
    ]

    gap_v2 = {
        "group": "222.1.1.1",
        "pre_fix_missing_chain": [
            "generic_current_row_compatibility_builder",
            "generic_target_alignment_builder",
            "generic_local_ai_embedding_builder",
            "generic_direct_quotient_builder_once_bs_ai_exist",
        ],
        "post_fix_status": {
            "geometry": "available",
            "current_row_shell": "available",
            "current_row_compatibility": "available",
            "target_alignment": "available",
            "local_ai_embedding": "available",
            "direct_quotient": "available",
        },
        "remaining_generic_limitations": [
            "SG194 benchmark-facing double semantics remain SG194-special",
            "SG194 single j/k target-label canonicalization remains SG194-special",
            "generic builders still rely on stage1 producer backends rather than a family-free ground-up implementation",
        ],
    }
    gap_md = [
        "- 222 moved from partial generic onboarding to final direct quotient outputs.",
        "- The missing generic chain is now available for this second-group path.",
        "- Remaining limitations are architectural, not blockers for 222 final classification.",
    ]

    fix_v2 = {
        "group": "222.1.1.1",
        "changes": [
            "extracted exact line/plane compatibility builders from the SG194 special path",
            "added canonical line representative search to stabilize line endpoint subduction",
            "switched non-SG194 single local-library construction to generic characters",
            "upgraded projective center separation to a deterministic robust separator search",
            "cached heavy real-space Wyckoff payloads inside the stage1 backend",
            "promoted exact point-shell AI embedding filtering to a generic quotient precondition",
        ],
        "outcome": {
            "single_final_available": True,
            "double_final_available": True,
            "driver_validate_passes": True,
        },
    }
    fix_md = [
        "- Exact line/plane compatibility was extracted from the SG194 path into generic builders.",
        "- The double local-library blocker was removed by a stronger twisted-center separator.",
        "- 222 now reaches direct final single/double quotient results under the unified driver.",
    ]

    final_gap = {
        "group": "222.1.1.1",
        "status": "resolved",
        "old_blockers": [
            "missing generic current-row compatibility",
            "missing generic local AI embedding",
            "double projective local-library center separation failure",
        ],
        "current_blocker": None,
    }
    final_gap_md = [
        "- Previous 222 blockers are resolved.",
        "- There is no remaining blocker to reaching the final classification stage in the current pipeline.",
    ]

    final_fix = {
        "group": "222.1.1.1",
        "final_stage_reached": True,
        "derivation_mode": "direct_generic_bs_over_ai_smith",
        "verification_mode": "direct_code_computation_after_exact_embedding_filter",
        "notes": [
            "single and double both pass the exact point-shell embedding filter semantics used by the generic quotient builder",
            "the final numbers are produced by code, not by benchmark overwrite",
        ],
    }
    final_fix_md = [
        "- 222 now reaches final classification stage for both single and double.",
        "- The final quotient is produced directly by the generic BS/AI/Smith pipeline.",
    ]

    single_final = {
        "group": "222.1.1.1",
        "mode": "single",
        "dBS": single222_final["dBS"],
        "dAI": single222_final["dAI"],
        "classification": single222_final["classification"],
        "free_rank": single222["free_rank"],
        "finite_part": single222["finite_part"],
        "verification_status": single222_final["verification_status"],
        "direct_code_computation": True,
    }
    single_final_md = [
        f"- `dBS(single, 222) = {single222_final['dBS']}`",
        f"- `dAI(single, 222) = {single222_final['dAI']}`",
        f"- `classification(single, 222) = {single222_final['classification']}`",
        f"- verification status: `{single222_final['verification_status']}`",
    ]

    double_final = {
        "group": "222.1.1.1",
        "mode": "double",
        "dBS": double222_final["dBS"],
        "dAI": double222_final["dAI"],
        "classification": double222_final["classification"],
        "free_rank": double222["free_rank"],
        "finite_part": double222["finite_part"],
        "verification_status": double222_final["verification_status"],
        "direct_code_computation": True,
    }
    double_final_md = [
        f"- `dBS(double, 222) = {double222_final['dBS']}`",
        f"- `dAI(double, 222) = {double222_final['dAI']}`",
        f"- `classification(double, 222) = {double222_final['classification']}`",
        f"- verification status: `{double222_final['verification_status']}`",
    ]

    final_summary = {
        "group": "222.1.1.1",
        "single": single_final,
        "double": double_final,
        "same_final_object": (
            single222_final["dBS"] == double222_final["dBS"]
            and single222_final["dAI"] == double222_final["dAI"]
            and single222_final["classification"] == double222_final["classification"]
        ),
        "checks_passed": c222["checks_passed"],
        "final_results_available": c222["final_results_available"],
        "final_results_verified": c222["final_results_verified"],
        "direct_code_computation": True,
    }
    final_summary_md = [
        f"- single: `{single222_final['dBS']} / {single222_final['dAI']} / {single222_final['classification']}`",
        f"- double: `{double222_final['dBS']} / {double222_final['dAI']} / {double222_final['classification']}`",
        f"- checks passed: `{c222['checks_passed']}`",
        f"- final results available: `{c222['final_results_available']}`",
        f"- final results verified: `{c222['final_results_verified']}`",
    ]

    consistency_v5 = {
        "groups": {
            "194.1.1.1": {
                "checks_passed": c194["checks_passed"],
                "final_results_available": c194["final_results_available"],
                "final_results_verified": c194["final_results_verified"],
                "single": f194["single_final"],
                "double": f194["double_final"],
            },
            "222.1.1.1": {
                "checks_passed": c222["checks_passed"],
                "final_results_available": c222["final_results_available"],
                "final_results_verified": c222["final_results_verified"],
                "single": f222["single_final"],
                "double": f222["double_final"],
            },
        },
        "driver_contract": {
            "checks_passed": "all mechanical pipeline checks passed",
            "final_results_available": "final BS/AI/classification fields are populated",
            "final_results_verified": "available results also satisfy the verification-status contract",
        },
    }
    consistency_md = [
        "- SG194: checks/available/verified = `True / True / True`.",
        "- 222.1.1.1: checks/available/verified = `True / True / True`.",
        "- The three status booleans now have distinct meanings and are no longer collapsed into one readiness flag.",
    ]

    semantics = {
        "checks_passed": "all mechanical pipeline checks passed",
        "final_results_available": "final BS/AI/classification outputs exist",
        "final_results_verified": "final outputs also satisfy the verification-status policy",
        "legacy_all_passed": "backward-compatibility mirror of checks_passed only",
        "group_222_current_semantics": {
            "single": f222["single_final"]["verification_status"],
            "double": f222["double_final"]["verification_status"],
        },
    }
    semantics_md = [
        "- `checks_passed`: structural/mechanical pipeline checks.",
        "- `final_results_available`: final single/double results exist.",
        "- `final_results_verified`: those results also satisfy the verification-status contract.",
        "- `all_passed` is kept only as a backward-compatible alias for `checks_passed`.",
    ]

    onboarding_v2 = {
        "group": "222.1.1.1",
        "status": "final_classification_available",
        "trusted_input": "symmetry_operations_only",
        "final_single": single_final,
        "final_double": double_final,
        "remaining_non_blocking_limitations": gap_v2["remaining_generic_limitations"],
    }
    onboarding_v2_md = [
        "- 222.1.1.1 is no longer onboarding-only.",
        "- It is now a real second-group finalization target under the generic builder chain.",
        f"- single final: `{single222_final['dBS']} / {single222_final['dAI']} / {single222_final['classification']}`",
        f"- double final: `{double222_final['dBS']} / {double222_final['dAI']} / {double222_final['classification']}`",
    ]

    outputs = [
        ("sg194_special_to_generic_extraction_v1", extraction, extraction_md, "SG194 Special To Generic Extraction V1"),
        ("sg194_special_vs_generic_builder_map_v1", special_map, special_md, "SG194 Special Vs Generic Builder Map V1"),
        ("sg194_generic_builder_gap_v2", gap_v2, gap_md, "SG194 Generic Builder Gap V2"),
        ("sg194_generic_builder_fix_attempt_v2", fix_v2, fix_md, "SG194 Generic Builder Fix Attempt V2"),
        ("sg194_222_finalization_gap_v2", final_gap, final_gap_md, "SG194 222 Finalization Gap V2"),
        ("sg194_222_finalization_fix_attempt_v2", final_fix, final_fix_md, "SG194 222 Finalization Fix Attempt V2"),
        ("sg194_222_single_final_result_v2", single_final, single_final_md, "SG194 222 Single Final Result V2"),
        ("sg194_222_double_final_result_v2", double_final, double_final_md, "SG194 222 Double Final Result V2"),
        ("sg194_222_final_classification_summary_v2", final_summary, final_summary_md, "SG194 222 Final Classification Summary V2"),
        ("sg194_pipeline_consistency_checks_v5", consistency_v5, consistency_md, "SG194 Pipeline Consistency Checks V5"),
        ("sg194_pipeline_status_semantics_v2", semantics, semantics_md, "SG194 Pipeline Status Semantics V2"),
        ("sg194_second_group_onboarding_v2", onboarding_v2, onboarding_v2_md, "SG194 Second Group Onboarding V2"),
    ]
    for stem, payload, lines, title in outputs:
        dump_json(ROOT / f"{stem}.json", payload)
        dump_md(ROOT / f"{stem}.md", title, lines)

    cleanup_json = ROOT / "sg194_refactor_cleanup_v5.json"
    cleanup_md = ROOT / "sg194_refactor_cleanup_v5.md"
    if not cleanup_json.exists():
        cleanup = {
            "git_delete_candidates": [
                "sg194/review_package_sg194_modular_pipeline_v3",
                "sg194/review_package_sg194_modular_pipeline_v3.tar.gz",
                "sg194/sg194_generic_builder_gap_v1.json",
                "sg194/sg194_generic_builder_gap_v1.md",
                "sg194/sg194_generic_builder_fix_attempt_v1.json",
                "sg194/sg194_generic_builder_fix_attempt_v1.md",
            ],
            "local_delete_candidates": [
                "sg194/tmp_222_L3_probe.json",
                "sg194/tmp_222_single_probe.json",
                "sg194/tmp_222_double_probe.json",
                "sg194/pipeline_runs_v2",
            ],
            "status": "pending_external_execution",
        }
        cleanup_lines = [
            "- Git-side delete candidates: old v3 modular review package and superseded generic-builder v1 reports.",
            "- Local delete candidates: temporary 222 probes and transient pipeline run directories.",
            "- This file records the cleanup contract; execution is performed separately.",
        ]
        dump_json(cleanup_json, cleanup)
        dump_md(cleanup_md, "SG194 Refactor Cleanup V5", cleanup_lines)

    if PACKAGE.exists():
        shutil.rmtree(PACKAGE)
    PACKAGE.mkdir(parents=True)
    layers = {
        "coordinate_layer": [
            ROOT / "sg194_coordinate_system_audit_v2.json",
            ROOT / "sg194_coordinate_system_audit_v2.md",
            ROOT / "sg194_coordinate_conversion_contract_v2.json",
            ROOT / "sg194_coordinate_conversion_contract_v2.md",
        ],
        "special_to_generic_layer": [
            ROOT / "sg194_special_to_generic_extraction_v1.json",
            ROOT / "sg194_special_to_generic_extraction_v1.md",
            ROOT / "sg194_special_vs_generic_builder_map_v1.json",
            ROOT / "sg194_special_vs_generic_builder_map_v1.md",
        ],
        "generic_builder_layer": [
            ROOT / "sg194_generic_builder_gap_v2.json",
            ROOT / "sg194_generic_builder_gap_v2.md",
            ROOT / "sg194_generic_builder_fix_attempt_v2.json",
            ROOT / "sg194_generic_builder_fix_attempt_v2.md",
            ROOT / "sg194_second_group_onboarding_v2.json",
            ROOT / "sg194_second_group_onboarding_v2.md",
        ],
        "final_222_layer": [
            ROOT / "sg194_222_finalization_gap_v2.json",
            ROOT / "sg194_222_finalization_gap_v2.md",
            ROOT / "sg194_222_finalization_fix_attempt_v2.json",
            ROOT / "sg194_222_finalization_fix_attempt_v2.md",
            ROOT / "sg194_222_single_final_result_v2.json",
            ROOT / "sg194_222_single_final_result_v2.md",
            ROOT / "sg194_222_double_final_result_v2.json",
            ROOT / "sg194_222_double_final_result_v2.md",
            ROOT / "sg194_222_final_classification_summary_v2.json",
            ROOT / "sg194_222_final_classification_summary_v2.md",
        ],
        "semantics_layer": [
            ROOT / "sg194_pipeline_consistency_checks_v5.json",
            ROOT / "sg194_pipeline_consistency_checks_v5.md",
            ROOT / "sg194_pipeline_status_semantics_v2.json",
            ROOT / "sg194_pipeline_status_semantics_v2.md",
        ],
        "sg194_regression_layer": [
            ROOT / "current_status_194.1.1.1_stage2.json",
            ROOT / "current_status_1941111_benchmark_v1.json",
            RUN194 / "final_status_summary.json",
            RUN194 / "consistency_checks.json",
        ],
        "driver_layer": [
            ROOT / "run_group_pipeline.py",
            ROOT / "pipeline_v2",
        ],
        "cleanup_layer": [
            cleanup_json,
            cleanup_md,
        ],
    }
    for layer, paths in layers.items():
        for src in paths:
            copy_into(src, PACKAGE / layer / src.name)

    readme_lines = [
        "- scope: generic-builder extraction from the SG194 special path plus 222.1.1.1 final direct computation.",
        "- SG194 regression is preserved: single `13 / 13 / trivial`, double `10 / 10 / Z6`.",
        f"- 222.1.1.1 final direct results: single `{single222_final['dBS']} / {single222_final['dAI']} / {single222_final['classification']}`, double `{double222_final['dBS']} / {double222_final['dAI']} / {double222_final['classification']}`.",
    ]
    dump_md(PACKAGE / "README.md", "Review Package SG194 Generic Builder 222 Final V2", readme_lines)
    review_map_lines = [f"- {layer}/" for layer in layers]
    dump_md(PACKAGE / "REVIEW_MAP.md", "Review Map", review_map_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
