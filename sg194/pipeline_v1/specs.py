from __future__ import annotations

from .models import GroupSpec, LegacyScriptSet


SG194_SINGLE_JK_CANONICALIZATION = {
    "j_A'": "k_A'",
    "j_A''": "k_A''",
    "k_A'": "j_A'",
    "k_A''": "j_A''",
}


SG194_SPEC = GroupSpec(
    key="sg194",
    group_id="194.1.1.1",
    title="SG194 unified modular pipeline",
    description=(
        "SG194 portability, target-row-language alignment, benchmark-facing double pipeline, "
        "and exact ordinary single target pipeline."
    ),
    root_subdir="sg194",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={
        "legacy_status": "current_status_194.1.1.1.json",
        "legacy_summary": "workflow_portability_summary_194.1.1.1.json",
        "stage2_status": "current_status_194.1.1.1_stage2.json",
        "stage2_summary": "workflow_portability_stage2_summary_194.1.1.1.json",
        "single_kmanifolds": "group_194_1_1_1_single_kmanifolds.json",
        "single_connectivity": "group_194_1_1_1_single_connectivity.json",
        "single_full_compatibility": "group_194_1_1_1_single_full_compatibility_with_planes.json",
        "single_bs_analysis": "group_194_1_1_1_single_bs_analysis.json",
        "single_completion": "group_194_1_1_1_single_ai_completion_summary.json",
        "double_completion": "group_194_1_1_1_double_ai_completion_summary.json",
        "projection_summary": "sg194_standard_space_projection_summary_v1.json",
        "benchmark_status": "current_status_1941111_benchmark_v1.json",
        "pairing_proof": "sg194_single_jk_pairing_proof_v1.json",
        "pairing_uniqueness": "sg194_single_jk_pairing_uniqueness_v1.json",
        "single_regression": "sg194_single_exact_alignment_regression_v1.json",
        "single_exact_alignment": "sg194_single_exact_target_alignment_fix_attempt_v1.json",
        "double_target_stack": "sg194_double_target_object_stack_v1.json",
    },
    legacy_scripts=LegacyScriptSet(
        stage1_script="debug_workflow_portability_194.1.1.1.py",
        stage2_script="debug_workflow_portability_stage2_194.1.1.1.py",
        projection_script="debug_sg194_standard_space_projection_v1.py",
        exact_alignment_script="debug_sg194_single_exact_target_alignment_v1.py",
        pairing_proof_script="debug_sg194_single_jk_pairing_proof_v1.py",
        regression_script="debug_sg194_single_exact_alignment_regression_v1.py",
    ),
    special_rules={
        "single_target_label_normalization": {
            "kind": "external_ordinary_target_label_lookup_normalization",
            "mapping": dict(SG194_SINGLE_JK_CANONICALIZATION),
            "scope": "single-valued ordinary target-row-language cache lookup only",
            "proof_artifact": "sg194_single_jk_pairing_proof_v1.json",
        },
        "raw_row_language_kind": "raw_current_with_planes_42_unknown_shell",
        "target_row_language_kind": "ordinary_sg194_external_row_language",
        "double_target_object_kind": "benchmark_facing_double_internalized_target_object",
        "single_target_object_kind": "ordinary_single_exact_target_row_language_object",
    },
    expected_results={
        "single_target": {"dBS": 13, "dAI": 13, "classification": "trivial"},
        "double_target": {"dBS": 10, "dAI": 10, "classification": "Z6"},
        "single_raw": {"dBS": 16, "dAI": 13, "classification": "Z^3"},
        "double_raw": {"dBS": 16, "dAI": 13, "classification": "Z^3"},
    },
    benchmark={
        "indicator_group": "Z6",
        "dBS": 10,
        "dAI": 10,
        "scope": "benchmark-facing magnetic/spinorial target only",
    },
)


TEMPLATE_SPEC = GroupSpec(
    key="template-hex",
    group_id="template.0.0.0",
    title="Template future-group spec",
    description=(
        "Non-runnable placeholder spec proving the modular driver accepts a second group "
        "contract without SG194 hardcoding."
    ),
    root_subdir="sg194",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={},
    legacy_scripts=LegacyScriptSet(),
    special_rules={
        "status": "template_only",
        "expected_extension_points": [
            "group_spec",
            "geometry adapter",
            "representation adapter",
            "alignment normalizer",
            "result expectation contract",
        ],
    },
    runnable=False,
    readiness_note=(
        "Template only. The unified driver can validate the spec shape and emit placeholder "
        "outputs, but no group-specific legacy data or external caches are wired in yet."
    ),
)


GROUP_SPECS = {
    SG194_SPEC.key: SG194_SPEC,
    SG194_SPEC.group_id: SG194_SPEC,
    TEMPLATE_SPEC.key: TEMPLATE_SPEC,
    TEMPLATE_SPEC.group_id: TEMPLATE_SPEC,
}


def get_group_spec(key: str) -> GroupSpec:
    try:
        return GROUP_SPECS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported group spec: {key}") from exc


def list_group_specs() -> list[dict[str, object]]:
    unique_specs = {spec.key: spec for spec in GROUP_SPECS.values()}
    return [
        {
            "key": spec.key,
            "group_id": spec.group_id,
            "title": spec.title,
            "runnable": spec.runnable,
            "row_languages": list(spec.row_languages),
            "modes": list(spec.modes),
            "readiness_note": spec.readiness_note,
        }
        for spec in unique_specs.values()
    ]
