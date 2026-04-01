# SG194 Refactor Cleanup V6

- Target object: `222.1.1.1`
- Equivalent OG object: `222.1.1601`

## Git deletions

- `sg194/debug_sg194_222_consistency_probe_v2.py`
- `sg194/debug_sg194_222_finalization_probe_v2.py`
- `sg194/sg194_222_finalization_gap_v2.json`
- `sg194/sg194_222_finalization_gap_v2.md`
- `sg194/sg194_222_finalization_fix_attempt_v2.json`
- `sg194/sg194_222_finalization_fix_attempt_v2.md`
- `sg194/sg194_222_single_final_result_v2.json`
- `sg194/sg194_222_single_final_result_v2.md`
- `sg194/sg194_222_double_final_result_v2.json`
- `sg194/sg194_222_double_final_result_v2.md`
- `sg194/sg194_222_final_classification_summary_v2.json`
- `sg194/sg194_222_final_classification_summary_v2.md`
- `sg194/sg194_second_group_onboarding_v2.json`
- `sg194/sg194_second_group_onboarding_v2.md`
- `sg194/review_package_sg194_generic_builder_222_final_v2`
- `sg194/review_package_sg194_generic_builder_222_final_v2.tar.gz`

## Local deletions

- `sg194/pipeline_runs_v2`
- `sg194/pipeline_runs_v2_tmp`
- `sg194/pipeline_runs_v2_final`
- `sg194/tmp_222_L3_probe.json`
- `sg194/tmp_222_single_probe.json`
- `sg194/tmp_222_double_probe.json`

## Replacement set

- `sg194/sg194_222_og1601_identity_map_v1.json`
- `sg194/sg194_222_finalization_gap_v3.json`
- `sg194/sg194_222_finalization_fix_attempt_v3.json`
- `sg194/sg194_222_single_final_result_v3.json`
- `sg194/sg194_222_double_final_result_v3.json`
- `sg194/sg194_222_final_classification_summary_v3.json`
- `sg194/sg194_pipeline_consistency_checks_v6.json`
- `sg194/sg194_pipeline_status_semantics_v3.json`

## Rationale

- The removed `v2` files were superseded and misleading because they exposed bugged generic-path provisional outputs as if they were final `222.1.1.1` results.
- The `v3` replacement files keep the bug audit visible, preserve the `222.1.1.1 <-> 222.1.1601` identity map, and separate provisional generic-path output from copied-topmat oracle-backed unified OG-object reporting.
