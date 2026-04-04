# Double Benchmark Oracle Orientation Check

- Benchmark oracle file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`.
- Classification reference source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json::source_breakdown.copied_experimental_compute`.
- Raw matrix shape: `[33, 10]`.
- Interpreted generator orientation: `rows_are_generators_in_bs_basis_transposed_to_columns`.
- Interpreted generator count: `33`.
- Transpose applied: `True`.
- Interpreted generator matrix shape: `[10, 33]`.
- Authoritative AI rank / published BS rank: `10` / `10`.
- Orientation/report semantics consistent: `True`.
- Summary: Raw oracle matrix shape [33, 10] is interpreted as `rows_are_generators_in_bs_basis_transposed_to_columns`; transpose_applied=True yields a BS-basis generator matrix with shape [10, 33] and generator_count=33.
