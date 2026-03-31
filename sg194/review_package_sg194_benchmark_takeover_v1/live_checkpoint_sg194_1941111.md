# SG194 194.1.1.1 Live Checkpoint

- Current time: 2026-04-01 04:24:44 +0800
- Branch: `sg194-special`
- HEAD before this checkpoint update: `82df8fc`
- Task scope: SG194 benchmark takeover / benchmark reconciliation. The repo now treats the copied topmat magnetic benchmark as the only benchmark-authoritative SG194 conclusion and de-authorizes internal stage2 `13 / trivial` claims for benchmark use.

## Rolling Stages

1. Authoritative-looking file inventory completed.
   Audited benchmark-oracle, current raw, phase-aware, stage2, unresolved external-matrix, README, handoff, live checkpoint, and historical stage2 package entrypoints as authoritative-looking SG194 files.
2. Benchmark-authoritative status written.
   `current_status_1941111_benchmark_v1.json` and `.md` now state the benchmark-authoritative SG194 result: `classification = Z6`, `dBS = 10`, `dAI = 10`.
3. Object ladder completed.
   `sg194_object_ladder_and_benchmark_map_v1.json` and `.md` now distinguish benchmark oracle, current raw, phase-aware prototype, anchored stage2 claim, and unresolved external-matrix status.
4. Old stage2 files de-authorized.
   `current_status_194.1.1.1_stage2.json`, `workflow_portability_stage2_summary_194.1.1.1.json`, and the single/double AI completion summaries are now explicitly marked superseded for benchmark use.
5. README / handoff / checkpoint unified.
   `sg194/README.md` is benchmark-first, `handoff_194.1.1.1_stage2.md` is now explicitly internal-only, and this live checkpoint is centered on benchmark takeover rather than the old `trivial` claim.
6. Review package rebuilt.
   `review_package_sg194_benchmark_takeover_v1/` and `review_package_sg194_benchmark_takeover_v1.tar.gz` now collect the benchmark authoritative status, object ladder, inventory, benchmark verdict, reconciliation files, updated README, updated checkpoint, and downgraded stage2 summaries.
7. Pre-commit state reached.
   Mechanical validation passed for `py_compile`, benchmark takeover consistency, and review package contents. The branch is now ready for commit/push.

## Confirmed Findings

1. The only benchmark-authoritative SG194 result in this round is `classification = Z6`, `dBS = 10`, `dAI = 10`.
2. `SSG 194.1.1.1` is treated in this round as the same benchmark target as its no-time-reversal magnetic counterpart `OG 194.1.1494 / BNS 194.263`.
3. This SSG/BNS unification remains a project benchmark convention plus magnetic-counterpart mapping layer, not a separately scraped suffixless external field.
4. `current raw` is an internal raw object, not the benchmark.
5. `phase-aware` is a local prototype raw repair path, not the benchmark.
6. The old stage2 `13 / 13 / trivial` claim is retained only as an internally anchored reduced quotient claim and is superseded for benchmark use.
7. `current_status_sg194_external_matrix_final.json` remains useful only as an unresolved current-to-external mapping-layer status.

## Commands Run

1. `python3 /data/home/szhang/.codex/skills/codex-autoresearch/scripts/autoresearch_resume_check.py --repo /data/work/szhang/ssg/comprel`
2. `python3 sg194/debug_sg194_benchmark_takeover_v1.py --write`
3. `python3 -m py_compile sg194/*.py`
4. `python3 sg194/debug_sg194_benchmark_takeover_v1.py --validate`

## Files Added In Scope

1. `sg194/current_status_1941111_benchmark_v1.json`
2. `sg194/current_status_1941111_benchmark_v1.md`
3. `sg194/sg194_object_ladder_and_benchmark_map_v1.json`
4. `sg194/sg194_object_ladder_and_benchmark_map_v1.md`
5. `sg194/sg194_authoritative_file_inventory_v1.json`
6. `sg194/sg194_authoritative_file_inventory_v1.md`
7. `sg194/sg194_benchmark_takeover_report_v1.md`
8. `sg194/debug_sg194_benchmark_takeover_v1.py`
9. `sg194/review_package_sg194_benchmark_takeover_v1/`
10. `sg194/review_package_sg194_benchmark_takeover_v1.tar.gz`

## Files Updated In Scope

1. `sg194/current_status_194.1.1.1_stage2.json`
2. `sg194/workflow_portability_stage2_summary_194.1.1.1.json`
3. `sg194/group_194_1_1_1_single_ai_completion_summary.json`
4. `sg194/group_194_1_1_1_double_ai_completion_summary.json`
5. `sg194/current_status_sg194_external_matrix_final.json`
6. `sg194/README.md`
7. `sg194/handoff_194.1.1.1_stage2.md`
8. `sg194/live_checkpoint_sg194_1941111.json`
9. `sg194/live_checkpoint_sg194_1941111.md`

## Active Blocker

1. Accessible external magnetic-group sources confirm `OG 194.1.1494 / BNS 194.263` and `Type-I`, but do not separately expose the suffixless `SSG 194.1.1.1` label as an external field.
