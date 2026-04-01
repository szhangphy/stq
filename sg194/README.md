# SG194 Modular Pipeline

## Unified Entrypoint

- entrypoint: `run_group_pipeline.py`
- driver spec: `sg194_pipeline_driver_spec_v1.json`
- extensibility audit: `sg194_extensibility_audit_v1.json`
- consistency summary: `sg194_pipeline_consistency_checks_v1.json`

## Accepted SG194 Results

- single exact target object: `13 / 13 / trivial`
- double benchmark-facing target object: `10 / 10 / Z6`
- single and double share geometry but do not share the same final target object

## SG194-Special Backends

- `debug_workflow_portability_194.1.1.1.py`
- `debug_workflow_portability_stage2_194.1.1.1.py`
- `debug_sg194_standard_space_projection_v1.py`
- `debug_sg194_single_exact_target_alignment_v1.py`
- `debug_sg194_single_jk_pairing_proof_v1.py`
- `debug_sg194_single_exact_alignment_regression_v1.py`

These remain SG194-specific forensic/backend scripts. Use the unified driver for normal runs.

## Review Package

- package file: `review_package_sg194_modular_pipeline_v1.tar.gz`
- package directory: `review_package_sg194_modular_pipeline_v1/`

## Cleanup

- cleanup report: `sg194_refactor_cleanup_v1.json`
- retired old package: `review_package_sg194_single_jk_pairing_proof_v1`
