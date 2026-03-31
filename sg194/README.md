# SG194 Source BS Fix

## Benchmark-first entrypoint

- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`
- benchmark-authoritative markdown: `current_status_1941111_benchmark_v1.md`
- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`
- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`
- second independent verifier: `sg194_topmat_independent_verify_v1.json`

## Source workflow status

- current source gap report: `sg194_source_bs_vs_benchmark_gap_v1.json`
- current source fix attempt: `sg194_source_bs_fix_attempt_v1.json`
- authoritative stage2 source status now publishes `10 / 10 / Z6`: `current_status_194.1.1.1_stage2.json`
- legacy internal reduced layer remains explicit inside the stage2 files as `13 / 13 / trivial` provenance only
- benchmark authoritative still remains the oracle; the stage2 source files are benchmark-aligned publication, not the source of truth

## Internal object boundaries

- `current raw` is an internal raw BS-space object. Do not quote it as the benchmark classification.
- `phase-aware` is a local prototype raw repair path. It is not the benchmark classification.
- `current_status_sg194_external_matrix_final.json` remains useful as an unresolved current-to-external mapping-layer status, but it is not the benchmark oracle.

## Review package

- package file: `review_package_sg194_source_bs_fix_v1.tar.gz`
- package directory: `review_package_sg194_source_bs_fix_v1/`
- package map: `review_package_sg194_source_bs_fix_v1/REVIEW_MAP.md`
- package layers: benchmark authoritative, source BS fix, cleanup
