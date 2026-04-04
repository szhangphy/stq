# Double Benchmark Oracle SNF Check

- Benchmark oracle file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`.
- Classification reference source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json::source_breakdown.copied_experimental_compute`.
- Input shape metadata / interpreted orientation: `[10, 33]` / `generator_rows_in_bs_coordinates`.
- Interpreted generator matrix shape: `[10, 33]`.
- Authoritative AI rank / published BS rank: `10` / `10`.
- Quotient group / invariants / SNF diagonal: `Z6` / `[6]` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`.
- Expected quotient group / expected SNF diagonal: `Z6` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`.
- Matches benchmark reference: `True`.
- Summary: The benchmark oracle stores 33 explicit double AI generators in BS coordinates. After interpreting the stored rows as generator coordinates in the 10-dimensional BS basis, their Smith form reproduces the benchmark Z6 quotient.
