# SG194 Modular Pipeline v2

## Unified Entrypoint

- entrypoint: `run_group_pipeline.py`
- driver spec: `sg194_pipeline_driver_spec_v2.json`
- extensibility audit: `sg194_extensibility_audit_v2.json`
- consistency summary: `sg194_pipeline_consistency_checks_v2.json`
- group spec contract: `sg194_group_spec_contract_v1.json`

## Accepted SG194 Results

- single exact target object: `13 / 13 / trivial`
- double benchmark-facing target object: `10 / 10 / Z6`
- single and double share geometry but do not share the same final target object

## Second-Group Readiness

- real second-group spec: `10.4.1.31`
- trust policy: `symmetry_operations_only`
- current status: ops-backed onboarding only, no trusted BS/AI/quotient result
- onboarding artifact: `sg194_second_group_onboarding_v1.json`

## Pipeline Layers

- generic runtime: `pipeline_v2/`
- SG194-special adapter: `pipeline_v2/adapters/sg194.py`
- second-group ops-only adapter: `pipeline_v2/adapters/ssg10_4_1_31.py`
- legacy SG194 debug scripts remain backend/forensic only and are no longer the main orchestration layer

## Review Package

- package file: `review_package_sg194_modular_pipeline_v2.tar.gz`
- package directory: `review_package_sg194_modular_pipeline_v2/`

## Cleanup

- cleanup report: `sg194_refactor_cleanup_v2.json`
- retired old package: `review_package_sg194_modular_pipeline_v1`
