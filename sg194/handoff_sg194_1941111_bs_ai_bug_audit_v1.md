# SG194 194.1.1.1 BS/AI Bug Audit Handoff v1

- Current time: 2026-03-31 15:03:02 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Current branch: `sg194-special`
- Latest synced audit-fix commit: `a48469a`
- Current subtask: closeout checkpoint refresh and GitHub sync are complete; the remaining items are optional follow-up cleanup, not a live runtime blocker.

## Confirmed hard conclusions

1. The active working repo for this task is the nested git repo at `/data/work/szhang/ssg/comprel/stq_repo_export/repo`.
2. The inherited SG194 worktree is still dirty with many generated outputs and unrelated edits; those files were intentionally left untouched.
3. `python3 -m py_compile common/*.py`, `python3 -m py_compile sg194/*.py`, `python3 sg194/debug_workflow_portability_194.1.1.1.py`, and `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py` all pass in the current repo state.
4. The current single-group line compatibility state is `34` unknowns with point blocks `P1` through `P6`; the older `31`-dimensional / five-block context is stale for this repo snapshot.
5. The original double-patch failure was a real 42-vs-62 ordering mismatch:
   - the compatibility matrix was built in the current `42`-dimensional space,
   - but `debug_sg194_double_patch.py` and `debug_sg194_double_complement_patch_v1.py` were reading stale on-disk `62`-entry raw candidates.
6. The current rebuild path is already internally consistent: `build_double_runtime(...)`, `induce_objects(...)`, and `debug_raw_matrix_audit.load_case_candidates('194_1_1_1_double', rebuilt)` all return `42`-entry double vectors.
7. Source fix applied:
   - `sg194/debug_sg194_double_patch.py` now loads rebuilt/current double candidates through `debug_raw_matrix_audit`.
   - `sg194/debug_sg194_double_complement_patch_v1.py` now uses the same rebuilt/current candidate source.
8. The second root cause was a stale selected current surface. `debug_sg194_double_patch.py:selection_indices()` had been compressing the current space to legacy `P1/P2/P3/P5/P6`, excluding `P4`, and that projection introduced the apparent trusted/full mismatch.
9. Source fix applied: `selection_indices()` now includes `P4`, which restores exact row-space agreement on the patched-v2 payload.
10. The third root cause was stale quotient validation constants. The mechanically regenerated patched-v2 quotient is `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`, not the older `Z^19 x Z2 x Z2 x Z2` / `[29, 10]` expectation.
11. Source fix applied: `debug_sg194_double_complement_patch_v1.py:validate_outputs()` now checks the regenerated quotient constants.
12. Final verification result:
    - `python3 sg194/debug_sg194_double_patch.py` exits `0`
    - `python3 sg194/debug_sg194_double_complement_patch_v1.py` exits `0`
    - `sg194/sg194_double_complement_patch_summary_v1.json` records `full_33_global_alignment = true`
    - `sg194/sg194_double_complement_patch_summary_v1.json` records `complement_exact_equality = true`
    - the patched-v2 raw quotient is `Z^6 x Z2 x Z2 x Z2`
    - the patched-v2 matrix shape is `[16, 10]`
    - the patched-v2 Smith diagonal nonzero entries are `[1,1,1,1,1,1,1,2,2,2]`
13. `common/SG_utils.py` and `common/SSGReps.py` still hard-import `spglib` at module import time. That remains a portability debt, but it is not the blocker that was breaking the SG194 double-patch closeout.
14. The audit-fix commit `a48469a` was pushed successfully to `origin/sg194-special` before this checkpoint refresh.

## Ruled-out pseudo-problems

1. The current mainline SG194 point-space is not still stuck at `31` unknowns with only five point blocks.
2. Stage2 is not currently blocked by missing non-abelian local libraries.
3. The surviving double-patch failure is not a top-level import problem.
4. The final complement failure was not a remaining row-space construction mismatch; it was a stale validator constant.

## Most recent commands and results

1. `timeout 600 python3 /data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/debug_sg194_double_complement_patch_v1.py`
   Result: exit code `0`.
2. `jq '{full_33_global_alignment, complement_exact_equality, double_patched_v2_raw_internal_quotient, patched_v2_matrix_shape, patched_v2_smith_diagonal_nonzero}' /data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/sg194_double_complement_patch_summary_v1.json`
   Result: `true`, `true`, `Z^6 x Z2 x Z2 x Z2`, `[16,10]`, `[1,1,1,1,1,1,1,2,2,2]`.
3. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo push origin sg194-special`
   Result: pushed `e5701c3..a48469a`.
4. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo rev-parse --short HEAD && git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo rev-parse --short origin/sg194-special`
   Result: both sides reported `a48469a` before this checkpoint refresh commit.

## Files modified during the run

1. `sg194/debug_sg194_double_patch.py`
2. `sg194/debug_sg194_double_complement_patch_v1.py`
3. `sg194/handoff_sg194_1941111_bs_ai_bug_audit_v1.md`
4. `sg194/current_status_sg194_1941111_bs_ai_bug_audit_v1.json`
5. `sg194/next_step_prompt_sg194_1941111_bs_ai_bug_audit_v1.txt`
6. `sg194/sg194_1941111_bs_ai_bug_audit_summary_v1.json`
7. `sg194/sg194_1941111_bs_ai_bug_audit_report_v1.md`
8. `sg194/live_checkpoint_sg194_1941111.md`
9. `sg194/live_checkpoint_sg194_1941111.json`

## Remaining open items

1. Downstream reporting still conflates the raw internal quotient with the final SG194 standard quotient in some inherited summaries. That interpretation split remains a follow-up task.
2. `spglib` is still hard-imported at top level in `common/`; that portability cleanup remains a follow-up task.

## Immediate next step if the task resumes

1. Read this handoff plus the paired JSON checkpoint files first.
2. Treat the repaired patch path as closed unless a new regression appears.
3. If further SG194 work continues, focus next on the raw-vs-standard quotient reporting split and the `spglib` portability cleanup.
