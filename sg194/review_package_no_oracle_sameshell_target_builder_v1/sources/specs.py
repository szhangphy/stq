from __future__ import annotations

from .models import GroupSpec, ProducerCommand
from .coordinates import coordinate_contract


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
        "current_status": "sg194/current_status_194.1.1.1.json",
        "single_summary": "sg194/group_194_1_1_1_single_pilot_summary.json",
        "double_summary": "sg194/group_194_1_1_1_double_pilot_summary.json",
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
    builder_backend="adapter_artifacts",
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
        "single_target_exact": {"dBS": 10, "dAI": 10, "classification": "trivial"},
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
    coordinate_policy=coordinate_contract(),
    trust_level="accepted_group_specific_final_objects",
)


GROUP222_SPEC = GroupSpec(
    key="ssg222_1_1_1",
    group_id="222.1.1.1",
    title="222.1.1.1 / 222.1.1601 (OG) backend-free generic pipeline",
    description=(
        "Backend-free generic path under a strict trust policy: only symmetry-operation evidence "
        "is allowed on the native compute path. Copied topmat data for the equivalent OG object "
        "222.1.1601 are retained strictly as external compare/sanity-check artifacts."
    ),
    home_subdir="sg194",
    adapter_key="ssg222_generic_probe",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={
        "identity_map": "sg194/sg194_222_og1601_identity_map_v1.json",
        "generality_verdict": "sg194/sg194_generality_verdict_v3.json",
        "case_by_case_map": "sg194/sg194_case_by_case_map_v3.json",
        "ai_filter_bug_audit": "sg194/sg194_ai_filter_bug_fix_v2.json",
        "dropped_ai_candidates": "sg194/sg194_dropped_ai_candidates_v3.json",
        "topmat_oracle": "sg194/sg194_topmat_oracle_from_copy_v1.json",
        "oracle_compare_v1": "sg194/sg194_222_generic_vs_topmat_oracle_v1.json",
        "status_semantics_v5": "sg194/sg194_pipeline_status_semantics_v5.json",
    },
    producer_commands=(
        ProducerCommand(
            label="generic_path_purity_audit",
            script_relpath="sg194/debug_sg194_generic_path_purity_audit_v1.py",
        ),
        ProducerCommand(
            label="backend_free_generic_probe",
            script_relpath="sg194/debug_sg194_222_generic_probe_v1.py",
        ),
        ProducerCommand(
            label="generic_194_regression",
            script_relpath="sg194/debug_sg194_194_generic_regression_v1.py",
        ),
        ProducerCommand(
            label="topmat_oracle_compare",
            script_relpath="sg194/debug_sg194_topmat_oracle_compare_v1.py",
        ),
    ),
    builder_backend="generic_symmetry_ops",
    special_rules={
        "trust_policy": "symmetry_operations_only",
        "trusted_source": "irssg symmetry operations via common/swyckoff.py",
        "equivalent_og_object": "222.1.1601",
        "equivalent_topmat_msg_key": "222.98",
        "current_row_language_kind": "generic_canonical_point_row_language_from_symmetry_ops",
        "target_object_kind": "generic_direct_point_row_language_object",
        "generic_path_status": "backend_free_native_path",
        "oracle_policy": "copied_topmat_src_only_no_edits_to_original_tree",
    },
    final_object_ids={
        "single": "single_target_direct",
        "double": "double_target_direct",
    },
    capabilities={
        "full_geometry": True,
        "target_alignment": True,
        "final_results": True,
        "trusted_symmetry_probe": True,
        "generic_current_row_shell": True,
        "generic_local_ai_seed": True,
        "generic_current_row_compatibility": True,
        "generic_local_ai_embedding": True,
        "generic_direct_quotient": True,
        "oracle_compare_only": True,
    },
    coordinate_policy=coordinate_contract(),
    trust_level="backend_free_generic_symmetry_ops_with_external_oracle_compare",
    readiness_note=(
        "This spec is real and runnable. Native final slots come only from the backend-free generic "
        "path, while copied topmat results for the equivalent OG object 222.1.1601 remain compare-only."
    ),
)


GROUP99_SPEC = GroupSpec(
    key="ssg99_1_1_1",
    group_id="99.1.1.1",
    title="99.1.1.1 generic no-oracle same-shell target path",
    description=(
        "Oracle-free control target for the group-driven engine. The generic symmetry-ops path "
        "must build its own same-shell published target object when possible instead of relying on "
        "an external oracle. Only genuinely blocked no-oracle groups may remain diagnostic-only."
    ),
    home_subdir="sg194",
    adapter_key="generic_diagnostic",
    modes=("single", "double", "both"),
    row_languages=("raw", "target", "all"),
    artifacts={},
    builder_backend="generic_symmetry_ops",
    special_rules={
        "trust_policy": "symmetry_operations_only",
        "oracle_policy": "no_registered_benchmark_oracle_same_shell_builder_required",
        "current_row_language_kind": "generic_canonical_point_row_language_from_symmetry_ops",
        "target_object_kind": "generic_same_shell_target_object",
    },
    final_object_ids={},
    capabilities={
        "full_geometry": True,
        "target_alignment": True,
        "final_results": True,
        "trusted_symmetry_probe": True,
        "generic_current_row_shell": True,
        "generic_local_ai_seed": True,
        "generic_current_row_compatibility": True,
        "generic_local_ai_embedding": True,
        "generic_same_shell_target_builder": True,
        "generic_direct_quotient": True,
    },
    coordinate_policy=coordinate_contract(),
    trust_level="generic_symmetry_ops_same_shell_target_without_benchmark_oracle",
    readiness_note=(
        "99.1.1.1 is intentionally used as an oracle-free control group. It may become "
        "generic_final only if the same-shell published target builder succeeds on group data "
        "alone; projected point-shell diagnostics remain compare-only evidence."
    ),
)


GROUP_SPECS = {
    SG194_SPEC.key: SG194_SPEC,
    SG194_SPEC.group_id: SG194_SPEC,
    GROUP222_SPEC.key: GROUP222_SPEC,
    GROUP222_SPEC.group_id: GROUP222_SPEC,
    "222.1.1601": GROUP222_SPEC,
    GROUP99_SPEC.key: GROUP99_SPEC,
    GROUP99_SPEC.group_id: GROUP99_SPEC,
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
