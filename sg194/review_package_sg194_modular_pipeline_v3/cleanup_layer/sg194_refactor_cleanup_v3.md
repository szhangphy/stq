# Refactor Cleanup V3

## Scope

This round removes the old v2 / `10.4.1.31`-primary path and records the final local cleanup for the new `pipeline_v2` generic-builder refactor centered on `222.1.1.1`.

## Git Deleted Or Deauthorized

- `sg194/pipeline_v2/adapters/ssg10_4_1_31.py`
- `sg194/debug_sg194_second_group_smoke_test_v1.py`
- `sg194/debug_sg194_extensibility_audit_v2.py`
- `sg194/debug_sg194_pipeline_consistency_v2.py`
- `sg194/sg194_second_group_onboarding_v1.json`
- `sg194/sg194_second_group_onboarding_v1.md`
- `sg194/sg194_extensibility_audit_v2.json`
- `sg194/sg194_extensibility_audit_v2.md`
- `sg194/sg194_hardcoded_vs_generic_map_v2.json`
- `sg194/sg194_hardcoded_vs_generic_map_v2.md`
- `sg194/sg194_modularization_plan_v2.json`
- `sg194/sg194_modularization_plan_v2.md`
- `sg194/sg194_module_dependency_graph_v2.json`
- `sg194/sg194_module_dependency_graph_v2.md`
- `sg194/sg194_group_spec_contract_v1.json`
- `sg194/sg194_group_spec_contract_v1.md`
- `sg194/sg194_pipeline_consistency_checks_v2.json`
- `sg194/sg194_pipeline_consistency_checks_v2.md`
- `sg194/sg194_pipeline_driver_spec_v2.json`
- `sg194/sg194_pipeline_driver_spec_v2.md`
- `sg194/review_package_sg194_modular_pipeline_v2/`
- `sg194/review_package_sg194_modular_pipeline_v2.tar.gz`

## Local Deleted

- `sg194/pipeline_runs_v2_tmp/`
- `sg194/pipeline_runs_v2_final/`
- `stq_repo_export/repo/autoresearch-state.prev.json`
- `stq_repo_export/repo/research-results.prev.tsv`

## Main Path Switch

- removed primary second-group probe: `10.4.1.31`
- new primary second-group probe: `222.1.1.1`

## Validation

- validation run directories were deleted after the checks finished
- the obsolete v2 review package was deleted
- the obsolete `10.4.1.31` primary adapter was deleted
