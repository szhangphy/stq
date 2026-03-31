# Reproducibility Manifest

## Recommended Verification Order

1. `sg194_standard_space_projection_summary_v1.json`
2. `sg194_current_to_standard_row_translation_v1.json`
3. `workflow_portability_stage2_summary_194.1.1.1.json`
4. `current_status_194.1.1.1_stage2.json`
5. `workflow_portability_report_stage2_194.1.1.1.pdf`
6. `REPRODUCIBILITY_MANIFEST.md`
7. `group_194_1_1_1_single_ai_completion_summary.json`
8. `group_194_1_1_1_double_ai_completion_summary.json`
9. `debug_sg194_standard_space_projection_v1.py`
10. `debug_workflow_portability_stage2_194.1.1.1.py`

## Minimal Smoke Tests

- `python3 debug_sg194_standard_space_projection_v1.py --validate`
- `python3 debug_workflow_portability_stage2_194.1.1.1.py --validate`

## Read-Only Boundary

- Supported and smoke-tested: the two `--validate` commands above plus direct inspection of the package-local JSON/MD/PDF outputs.
- These commands do not depend on the original repo absolute paths and do not need the package tarball beside them.

## Rerun Boundary

- Full reruns may be launched from the extracted package directory with `python3 debug_sg194_standard_space_projection_v1.py` and `python3 debug_workflow_portability_stage2_194.1.1.1.py`.
- Full reruns overwrite package-local outputs only and require local `pdflatex` for the stage-2 PDF build.
- Direct runtime dependencies for those reruns are listed in `reproducibility_manifest_v1.json` and in the dependency audit.

## Included Executable Scripts

### `debug_sg194_standard_space_projection_v1.py`
- role: `projection_and_final_closeout`
- smoke-test command: `python3 debug_sg194_standard_space_projection_v1.py --validate`
- direct dependencies:
  - `debug_sg194_standard_space_projection_v1.py`
  - `debug_workflow_portability_stage2_194.1.1.1.py`
  - `debug_workflow_portability_194.1.1.1.py`
  - `debug_sg194_nonabelian_local_library.py`
  - `sg194_external_ordinary_generator_matrix.json`
  - `group_194_1_1_1_single_indicator_generators.json`
  - `group_194_1_1_1_double_indicator_generators.json`
  - `group_194_1_1_1_single_bs_analysis.json`
  - `group_194_1_1_1_double_bs_analysis.json`
  - `debug_sg194_stage2_package_dependency_audit_v1.py`

### `debug_workflow_portability_stage2_194.1.1.1.py`
- role: `authoritative_stage2_closeout`
- smoke-test command: `python3 debug_workflow_portability_stage2_194.1.1.1.py --validate`
- direct dependencies:
  - `debug_workflow_portability_stage2_194.1.1.1.py`
  - `debug_sg194_standard_space_projection_v1.py`
  - `debug_sg194_nonabelian_local_library.py`
  - `debug_workflow_portability_194.1.1.1.py`
  - `workflow_portability_summary_194.1.1.1.json`
  - `group_194_1_1_1_single_pilot_summary.json`
  - `group_194_1_1_1_single_pilot_audit.md`
  - `group_194_1_1_1_double_pilot_summary.json`
  - `group_194_1_1_1_double_pilot_audit.md`
  - `controlled_case_audit_194.1.1.1.md`
  - `current_status_194.1.1.1.json`
  - `handoff_194.1.1.1.md`
  - `next_step_prompt_194.1.1.1.txt`
  - `double_group_ai_completeness_audit_10.4.1.31.md`
  - `double_group_ai_completeness_summary_10.4.1.31.json`
  - `double_group_indicator_group_summary_10.4.1.31.json`
  - `double_group_indicator_generators_10.4.1.31.json`
  - `double_group_bs_mod_ai_summary_10.4.1.31.json`
  - `double_group_bs_summary_10.4.1.31.json`
  - `double_group_bs_basis_raw_10.4.1.31.json`
  - `double_group_bs_basis_pretty_10.4.1.31.json`
  - `double_group_full_compatibility_with_planes_10.4.1.31.json`
  - `single_group_ai_completeness_audit.md`
  - `single_group_ai_completeness_summary.json`
  - `single_group_indicator_group_summary.json`
  - `single_group_indicator_generators.json`
  - `single_group_bs_mod_ai_single_summary.json`
  - `sg194_external_ordinary_generator_matrix.json`
  - `group_194_1_1_1_single_indicator_generators.json`
  - `group_194_1_1_1_double_indicator_generators.json`
  - `debug_sg194_stage2_package_dependency_audit_v1.py`
  - `common/debug_single_group_ai_bridge.py`
  - `common/debug_single_group_ai_expanded.py`
  - `swyckoff_r.py`
  - `swyckoff_k.py`
  - `common/SSGReps/SSGReps/SSGReps.py`
  - `common/SSGReps/SSGReps/SG_utils.py`
  - `common/SSGReps/SSGReps/rep_utils.py`
  - `common/SSGReps/ssg_data/identify.pkl.tar.gz`

### `debug_sg194_nonabelian_local_library.py`
- role: `helper_nonabelian_local_library_builder`
- smoke-test command: `not part of the minimal extracted-package smoke test`
- direct dependencies:
  - `debug_sg194_nonabelian_local_library.py`
  - `debug_workflow_portability_194.1.1.1.py`
  - `workflow_portability_summary_194.1.1.1.json`
  - `group_194_1_1_1_single_pilot_summary.json`
  - `group_194_1_1_1_single_pilot_audit.md`
  - `group_194_1_1_1_double_pilot_summary.json`
  - `group_194_1_1_1_double_pilot_audit.md`
  - `controlled_case_audit_194.1.1.1.md`
  - `current_status_194.1.1.1.json`
  - `handoff_194.1.1.1.md`
  - `next_step_prompt_194.1.1.1.txt`
  - `swyckoff_r.py`
  - `swyckoff_k.py`
  - `common/debug_single_group_ai_bridge.py`
  - `common/debug_single_group_ai_expanded.py`
  - `common/SSGReps/SSGReps/SSGReps.py`
  - `common/SSGReps/SSGReps/SG_utils.py`
  - `common/SSGReps/SSGReps/rep_utils.py`
  - `common/SSGReps/ssg_data/identify.pkl.tar.gz`

### `debug_workflow_portability_194.1.1.1.py`
- role: `upstream_stage1_portability_pilot`
- smoke-test command: `not part of the minimal extracted-package smoke test`
- direct dependencies:
  - `debug_workflow_portability_194.1.1.1.py`
  - `workflow_portability_summary_194.1.1.1.json`
  - `group_194_1_1_1_single_pilot_summary.json`
  - `group_194_1_1_1_single_pilot_audit.md`
  - `group_194_1_1_1_double_pilot_summary.json`
  - `group_194_1_1_1_double_pilot_audit.md`
  - `controlled_case_audit_194.1.1.1.md`
  - `current_status_194.1.1.1.json`
  - `handoff_194.1.1.1.md`
  - `next_step_prompt_194.1.1.1.txt`
  - `double_group_ai_completeness_audit_10.4.1.31.md`
  - `double_group_ai_completeness_summary_10.4.1.31.json`
  - `double_group_indicator_group_summary_10.4.1.31.json`
  - `double_group_indicator_generators_10.4.1.31.json`
  - `double_group_bs_mod_ai_summary_10.4.1.31.json`
  - `double_group_bs_summary_10.4.1.31.json`
  - `double_group_bs_basis_raw_10.4.1.31.json`
  - `double_group_bs_basis_pretty_10.4.1.31.json`
  - `double_group_full_compatibility_with_planes_10.4.1.31.json`
  - `single_group_ai_completeness_audit.md`
  - `single_group_ai_completeness_summary.json`
  - `single_group_indicator_group_summary.json`
  - `single_group_indicator_generators.json`
  - `single_group_bs_mod_ai_single_summary.json`
  - `swyckoff_r.py`
  - `swyckoff_k.py`
  - `common/debug_single_group_ai_bridge.py`
  - `common/debug_single_group_ai_expanded.py`
  - `common/SSGReps/SSGReps/SSGReps.py`
  - `common/SSGReps/SSGReps/SG_utils.py`
  - `common/SSGReps/SSGReps/rep_utils.py`
  - `common/SSGReps/ssg_data/identify.pkl.tar.gz`

### `debug_sg194_stage2_package_dependency_audit_v1.py`
- role: `package_dependency_audit_and_manifest_builder`
- smoke-test command: `not part of the minimal extracted-package smoke test`
- direct dependencies:
  - `debug_sg194_stage2_package_dependency_audit_v1.py`
  - `debug_sg194_standard_space_projection_v1.py`
  - `debug_workflow_portability_stage2_194.1.1.1.py`
  - `REPRODUCIBILITY_MANIFEST.md`
  - `reproducibility_manifest_v1.json`

### `common/debug_single_group_ai_bridge.py`
- role: `reference_single_group_bridge_helper`
- smoke-test command: `not part of the minimal extracted-package smoke test`
- direct dependencies:
  - `common/debug_single_group_ai_bridge.py`
  - `swyckoff_r.py`
  - `common/SSGReps/SSGReps/SSGReps.py`
  - `common/SSGReps/ssg_data/identify.pkl.tar.gz`

### `common/debug_single_group_ai_expanded.py`
- role: `reference_single_group_expanded_ai_helper`
- smoke-test command: `not part of the minimal extracted-package smoke test`
- direct dependencies:
  - `common/debug_single_group_ai_expanded.py`
  - `common/debug_single_group_ai_bridge.py`
  - `swyckoff_r.py`
  - `common/SSGReps/SSGReps/SSGReps.py`
  - `common/SSGReps/ssg_data/identify.pkl.tar.gz`
