# SG194 Modular Pipeline Live Checkpoint v2

- Current time: 2026-04-01 15:44:02 +0800
- Branch: `sg194-special`
- Current HEAD: `72485d6`
- Current subtask: promote the modular pipeline to an adapter-pluggable framework with a real second-group onboarding path

## Accepted hard facts

1. SG194 single exact target remains `13 / 13 / trivial`.
2. SG194 double benchmark-facing target remains `10 / 10 / Z6`.
3. `run_group_pipeline.py` now dispatches to `pipeline_v2`.
4. A real second-group spec (`10.4.1.31`) is registered, but only under `symmetry_operations_only` trust.
5. The new review package is `review_package_sg194_modular_pipeline_v2`.

## Read First

1. `sg194/sg194_extensibility_audit_v2.json`
2. `sg194/sg194_group_spec_contract_v1.json`
3. `sg194/sg194_pipeline_driver_spec_v2.json`
4. `sg194/sg194_pipeline_consistency_checks_v2.json`
5. `sg194/sg194_second_group_onboarding_v1.json`
6. `sg194/current_status_194.1.1.1_stage2.json`
7. `sg194/current_status_1941111_benchmark_v1.json`
8. `sg194/review_package_sg194_modular_pipeline_v2/README.md`
9. `sg194/review_package_sg194_modular_pipeline_v2/REVIEW_MAP.md`

## Immediate Next Step

1. Review the `pipeline_v2` adapter boundary and second-group blocker list.
2. Commit on `sg194-special`.
3. Push `origin/sg194-special`.
