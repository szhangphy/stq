from __future__ import annotations

from .models import GroupSpec, ProducerCommand


SG194_SINGLE_JK_CANONICALIZATION = {
    "j_A'": "k_A'",
    "j_A''": "k_A''",
    "k_A'": "j_A'",
    "k_A''": "j_A''",
}


SG194_SPEC = GroupSpec(
    key="sg194",
    group_id="194.1.1.1",
    title="SG194 exact single / benchmark-facing double pipeline",
    description=(
        "Accepted SG194 split: ordinary single exact target-row-language object and "
        "benchmark-facing spinorial double target object."
    ),
    home_subdir="sg194",
    adapter_key="sg194",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={
        "stage2_status": "sg194/current_status_194.1.1.1_stage2.json",
        "stage2_summary": "sg194/workflow_portability_stage2_summary_194.1.1.1.json",
        "single_kmanifolds": "sg194/group_194_1_1_1_single_kmanifolds.json",
        "single_connectivity": "sg194/group_194_1_1_1_single_connectivity.json",
        "single_full_compatibility": "sg194/group_194_1_1_1_single_full_compatibility_with_planes.json",
        "benchmark_status": "sg194/current_status_1941111_benchmark_v1.json",
        "projection_summary": "sg194/sg194_standard_space_projection_summary_v1.json",
    },
    producer_commands=(
        ProducerCommand(
            label="projection_summary",
            script_relpath="sg194/debug_sg194_standard_space_projection_v1.py",
        ),
        ProducerCommand(
            label="stage2_status",
            script_relpath="sg194/debug_workflow_portability_stage2_194.1.1.1.py",
        ),
        ProducerCommand(
            label="single_exact_alignment",
            script_relpath="sg194/debug_sg194_single_exact_target_alignment_v1.py",
        ),
        ProducerCommand(
            label="single_alignment_regression",
            script_relpath="sg194/debug_sg194_single_exact_alignment_regression_v1.py",
        ),
    ),
    special_rules={
        "single_target_label_normalization": {
            "kind": "external_ordinary_target_label_lookup_normalization",
            "mapping": dict(SG194_SINGLE_JK_CANONICALIZATION),
            "scope": "single-valued ordinary target-row-language cache lookup only",
        },
        "raw_row_language_kind": "raw_current_with_planes_42_unknown_shell",
        "target_row_language_kind": "ordinary_sg194_external_row_language",
        "single_target_object_kind": "ordinary_single_exact_target_row_language_object",
        "double_target_object_kind": "benchmark_facing_double_internalized_target_object",
    },
    expected_results={
        "single_target_exact": {"dBS": 13, "dAI": 13, "classification": "trivial"},
        "double_target_benchmark_facing": {"dBS": 10, "dAI": 10, "classification": "Z6"},
    },
    benchmark={
        "indicator_group": "Z6",
        "dBS": 10,
        "dAI": 10,
        "scope": "benchmark-facing magnetic/spinorial target only",
    },
    final_object_ids={
        "single": "single_target_exact",
        "double": "double_target_benchmark_facing",
    },
    capabilities={
        "full_geometry": True,
        "target_alignment": True,
        "final_results": True,
    },
    trust_level="accepted_group_specific_final_objects",
)


GROUP10_SPEC = GroupSpec(
    key="ssg10_4_1_31",
    group_id="10.4.1.31",
    title="10.4.1.31 symmetry-ops-only onboarding probe",
    description=(
        "Real second-group spec under a strict trust policy: only symmetry-operation evidence "
        "is consumed, so the pipeline reports onboarding readiness and explicit blockers rather "
        "than BS/AI/quotient conclusions."
    ),
    home_subdir="common",
    adapter_key="ssg10_ops_only",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={
        "ops_onboarding": "sg194/sg194_second_group_onboarding_v1.json",
    },
    producer_commands=(
        ProducerCommand(
            label="second_group_smoke_test",
            script_relpath="sg194/debug_sg194_second_group_smoke_test_v1.py",
        ),
    ),
    special_rules={
        "trust_policy": "symmetry_operations_only",
        "trusted_source_files": [
            "common/P1_character.json",
            "common/L1_character.json",
            "common/P4_character.json",
        ],
        "known_missing_builders": [
            "generic_k_geometry_builder_from_symmetry_ops",
            "generic_current_row_compatibility_builder",
            "generic_local_ai_builder_from_site_symmetry_data",
            "generic_direct_quotient_builder_once_bs_ai_exist",
        ],
    },
    capabilities={
        "full_geometry": False,
        "target_alignment": False,
        "final_results": False,
        "trusted_symmetry_probe": True,
    },
    trust_level="symmetry_operations_only",
    readiness_note=(
        "This spec is real and runnable, but it is intentionally limited to symmetry-ops-backed "
        "readiness. No BS/AI/quotient conclusion is emitted until generic builders from symmetry "
        "operations exist."
    ),
)


GROUP_SPECS = {
    SG194_SPEC.key: SG194_SPEC,
    SG194_SPEC.group_id: SG194_SPEC,
    GROUP10_SPEC.key: GROUP10_SPEC,
    GROUP10_SPEC.group_id: GROUP10_SPEC,
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
            "trust_level": spec.trust_level,
            "readiness_note": spec.readiness_note,
        }
        for spec in unique_specs.values()
    ]
