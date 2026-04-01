# SG194 Modular Pipeline Live Checkpoint

- Current time: 2026-04-01 15:05:51 +0800
- Branch: `sg194-special`
- Current HEAD: `8cb81be`
- Current subtask: modularize SG194 into a reusable pipeline with one unified entrypoint

## Accepted hard facts

1. Single exact target remains `13 / 13 / trivial`.
2. Double benchmark-facing target remains `10 / 10 / Z6`.
3. Single and double share geometry but not the same final target object.
4. The unified entrypoint is now `sg194/run_group_pipeline.py`.
5. The old single j/k proof package is retired; the new review package is `review_package_sg194_modular_pipeline_v1`.

## Read First

1. `sg194/sg194_extensibility_audit_v1.json`
2. `sg194/sg194_pipeline_driver_spec_v1.json`
3. `sg194/sg194_pipeline_consistency_checks_v1.json`
4. `sg194/current_status_194.1.1.1_stage2.json`
5. `sg194/current_status_1941111_benchmark_v1.json`
6. `sg194/review_package_sg194_modular_pipeline_v1/README.md`
7. `sg194/review_package_sg194_modular_pipeline_v1/REVIEW_MAP.md`

## Immediate Next Step

1. Review the modular pipeline diff and cleanup diff together.
2. Commit on `sg194-special`.
3. Push `origin/sg194-special`.
