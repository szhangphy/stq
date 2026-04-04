# Double Benchmark Oracle SNF Check

- Benchmark oracle file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`.
- Classification reference source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json::source_breakdown.copied_experimental_compute`.
- Raw matrix shape / interpreted orientation: `[33, 10]` / `rows_are_generators_in_bs_basis_transposed_to_columns`.
- Interpreted generator count / transpose applied: `33` / `True`.
- Interpreted generator matrix shape: `[10, 33]`.
- Authoritative AI rank / published BS rank: `10` / `10`.
- Quotient group / invariants / SNF diagonal: `Z6` / `[6]` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`.
- Expected quotient group / expected SNF diagonal: `Z6` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`.
- Matches benchmark reference: `True`.
- Summary: After interpreting the raw benchmark oracle matrix with a dimension check against the published BS rank, the resulting Smith form reproduces the benchmark Z6 quotient.
