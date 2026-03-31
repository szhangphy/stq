# SG194 Benchmark Hardening

## Benchmark-first entrypoint

- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`
- benchmark-authoritative markdown: `current_status_1941111_benchmark_v1.md`
- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`
- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`
- second independent verifier: `sg194_topmat_independent_verify_v1.json`
- path sanitization report: `sg194_benchmark_path_sanitization_v1.json`
- superseded deemphasis report: `sg194_superseded_file_deemphasis_v1.json`
- object ladder / benchmark map: `sg194_object_ladder_and_benchmark_map_v1.json`
- authoritative-looking file inventory: `sg194_authoritative_file_inventory_v1.json`

## Benchmark target caveat

- SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.
- This remains a project benchmark convention plus magnetic-counterpart mapping layer.
- Accessible external magnetic-group sources in this round directly confirm the `OG/BNS` object and its `Type-I` character, but do not independently expose the suffixless repo label `SSG 194.1.1.1` as a separately scraped external field.

## Internal object boundaries

- `current raw` is an internal raw BS-space object. Do not quote it as the benchmark classification.
- `phase-aware` is a local prototype raw repair path. It is not the benchmark classification.
- `current_status_194.1.1.1_stage2.json` and the paired stage2 workflow/completion summaries are historical internal reduced-quotient references. They are superseded for benchmark use and now carry explicit do-not-use banners.
- `current_status_sg194_external_matrix_final.json` remains useful as an unresolved current-to-external mapping-layer status, but it is not the benchmark oracle.

## Review package

- package file: `review_package_sg194_benchmark_hardening_v1.tar.gz`
- package directory: `review_package_sg194_benchmark_hardening_v1/`
- package layer map: `review_package_sg194_benchmark_hardening_v1/REVIEW_MAP.md`
- benchmark layer and internal/superseded layer are split into separate subdirectories.
