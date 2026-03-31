# SG194 194.1.1.1 Live Checkpoint

- Current time: 2026-04-01 04:39:00 +0800
- Branch: `sg194-special`
- HEAD before this checkpoint update: `70fdd3f`
- Task scope: SG194 unified benchmark audit for `SSG 194.1.1.1` treated together with `OG 194.1.1494 / BNS 194.263`, using read-only `topmat_src` plus copied-source local compute inside `sg194/`.

## Rolling Stages

1. Read-only `topmat_src` audit completed.
   Audited `topmat.py`, `work_ind.sh`, `dealfort.py`, `BilBaoData/msginfo`, `Lindex_194.263.txt`, `basis_194.263.txt`, `MsgAI_194.263.txt`, `OrigAI_194.263.txt`, `mwyck-mag/194.263.txt`, `pairfiles_msghspk/194.263.txt`, and `mkpoints/194.txt`.
2. Read-only object lookup confirmed.
   `msginfo` row 1493 maps OG `1494` to BNS `194.263` with Type-I / no time reversal.
3. Read-only direct run completed.
   `python3 /data/home/szhang/soft_sz/topmat_src/topmat.py -og 1494 -sg 194 -mode 2` was executed in a temporary directory with generated `tqc.data` and returned `indout = Z6=0,`.
4. Copied-source benchmark compute completed.
   The copied reference tree `sg194/topmat_reference_v3/` was used without modifying `/data/home/szhang/soft_sz/topmat_src`.
5. Benchmark values resolved.
   `basis_194.263.txt` gives BS rank `10`; `MsgAI_194.263.txt` lifted into the BS basis also has rank `10`; Smith nonzero diagonal is `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`, so the complete benchmark classification is `Z6`.
6. Current-vs-external object matching completed.
   Current raw objects are `Z^3` raw internal quotients, the phase-aware object is a local raw compatibility repair prototype, and the older anchored trivial claim is superseded by a later unresolved external-matrix status.
7. Commit/push closeout nearly complete.
   The benchmark artifacts are committed and pushed once; the remaining follow-up is to commit the copied `topmat_reference_v3/` snapshot together with this refreshed final checkpoint state.

## Confirmed Findings

1. `SSG 194.1.1.1` is treated in this round as the same benchmark target as its no-time-reversal magnetic counterpart `OG 194.1.1494 / BNS 194.263`.
2. `topmat_src` can directly evaluate an indicator value and exposes enough reference data to recover the benchmark classification, but it does not directly print scalar `dBS` or `dAI`.
3. The direct magnetic classification for the unified target is `Z6`.
4. The copied experimental compute gives `dBS = 10` and `dAI = 10`.
5. The user-priority `Z6` hypothesis is supported, not merely unresolved.
6. Bilbao-level external checks in this round confirm the magnetic object identity and Type-I character, but do not independently expose the `SSG 194.1.1.1` label.
7. The current repo's raw and phase-aware objects are not themselves the final external benchmark object.

## Commands Run

1. `python3 /data/home/szhang/.codex/skills/codex-autoresearch/scripts/autoresearch_resume_check.py --repo /data/work/szhang/ssg/comprel`
2. `python3 sg194/sg194_topmat_experimental_compute_v2.py`
3. `python3 /data/home/szhang/soft_sz/topmat_src/topmat.py -og 1494 -sg 194 -mode 2`
4. `python3 - <<'PY' ...` independent SymPy rank / Smith verification on `basis_194.263.txt` and `MsgAI_194.263.txt`

## Files Added In Scope

1. `sg194/sg194_topmat_readonly_audit_v3.json`
2. `sg194/sg194_topmat_readonly_audit_v3.md`
3. `sg194/sg194_external_benchmark_from_topmat_v3.json`
4. `sg194/sg194_external_benchmark_from_topmat_v3.md`
5. `sg194/sg194_topmat_experimental_compute_v2.py`
6. `sg194/sg194_topmat_experimental_compute_v2.json`
7. `sg194/sg194_topmat_experimental_compute_v2.md`
8. `sg194/sg194_current_vs_external_object_matching_v3.json`
9. `sg194/sg194_current_vs_external_object_matching_v3.md`
10. `sg194/sg194_topmat_copied_sources_manifest_v2.json`
11. `sg194/sg194_topmat_copied_sources_manifest_v2.md`
12. `sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`
13. `sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.md`
14. `sg194/topmat_reference_v3/` copied-source snapshot tree

## Active Blockers

1. Bilbao/accessible web sources directly confirm `OG 194.1.1494 / BNS 194.263`, but not the `SSG 194.1.1.1` label as a separately surfaced external field.
2. The outer working directory `/data/work/szhang/ssg/comprel` is not itself a git repository; commit/push must happen from `stq_repo_export/repo`.
3. The copied `sg194/topmat_reference_v3/` tree still needs its own follow-up commit so the manifest points only at tracked files.
