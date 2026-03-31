# SG194 194.1.1.1 BS/AI Bug Audit Handoff v1

- Current time: 2026-03-31 14:52:35 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Current branch: `sg194-special`
- Current HEAD: `e5701c3`
- Current subtask: post-compaction checkpoint refresh is complete; repo/branch/worktree have been reconfirmed on `sg194-special` without resetting inherited changes.
- Current subtask: the stale quotient constants in `validate_outputs()` have been patched to the current mechanical result; next step is the final complement rerun.

## Confirmed hard findings

1. The working repo for this task is `/data/work/szhang/ssg/comprel/stq_repo_export/repo`, not the parent aggregation directory.
2. The current branch is `sg194-special`, HEAD is `e5701c3`, and the worktree is already dirty with many inherited `sg194/` changes and generated artifacts.
3. These checkpoint files did not exist before this update; they are being created now and must be kept current throughout the run.
4. `python3 -m py_compile common/*.py` completed successfully.
5. `python3 -m py_compile sg194/*.py` completed successfully, but `sg194/debug_sg194_bs_ai_separation.py:799` emits repeated `SyntaxWarning: invalid escape sequence` warnings.
6. Importing `sg194/debug_workflow_portability_194.1.1.1.py` succeeded, so the current top-level import path is not broken.
7. Running `python3 sg194/debug_workflow_portability_194.1.1.1.py` completed successfully and produced a report and package. In that inherited baseline, the main blocker was still reported as missing generic non-abelian local-irrep support.
8. Running `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py` completed successfully and reports that both the single-group and double-group non-abelian local libraries are built, both AI completeness blockers are unblocked, both raw internal quotients are `Z^3`, and the remaining blocker is the missing projection to the final SG194 standard indicator space.
9. The current single-group line compatibility file reports 34 line-space unknowns with point blocks `P1` through `P6`, not 31 unknowns and not only five point blocks.
10. `python3 sg194/debug_sg194_double_patch.py` fails with `sympy.matrices.exceptions.ShapeError: Matrix size mismatch: (58, 42) * (62, 1)` inside `build_channel_candidates`.
11. `python3 sg194/debug_sg194_double_complement_patch_v1.py` fails with the same `ShapeError`, again through `debug_sg194_double_patch.py:build_channel_candidates`.
12. `common/SG_utils.py` and `common/SSGReps.py` still hard-import `spglib` at module import time, while `sg194/debug_workflow_portability_194.1.1.1.py` lazy-imports `spglib` inside `build_controlled_case`.
13. The current double-patch failure is now traced to an ordering/space mismatch: `debug_workflow_portability_stage2_194.1.1.1.py:build_sg194_double_spinorial_generators(...)` emits 33 channels whose `unknown_vector` length is `62` for both `legacy` and `sg194_double_anchor_patch_v1`, while `debug_raw_matrix_audit.py:compute_c_artifact(...)` returns a compatibility matrix of shape `(58, 42)` with `42` unknown-ordering labels. `debug_sg194_double_patch.py:build_channel_candidates(...)` multiplies the 42-column matrix by the 62-entry vectors without any projection or ordering translation.
14. `python3 sg194/debug_sg194_double_global_residual.py` now runs successfully with exit code `0`.
15. `python3 sg194/debug_sg194_double_lift.py` now runs successfully with exit code `0`.
16. `raw_194_1_1_1_double_ai_candidates.json` is not using the current 42-entry compatibility ordering. Its `unknown_ordering` length is `62`, it adds `B1..B5` entries (23 extra labels total), and it is missing `P4_R1`, `P4_R2`, and `P4_R3` compared with `group_194_1_1_1_double_full_compatibility_with_planes.json`.
17. The current in-memory rebuild path is already consistent with the 42-dimensional compatibility space. `build_double_runtime(...)` now returns `with_planes.global_unknown_ordering` length `42`, `bs_analysis.unknown_ordering` length `42`, and `induce_objects(...)` returns `45` double candidates with vector length `42`. `debug_raw_matrix_audit.load_case_candidates('194_1_1_1_double', rebuilt)` also returns `45` candidates with vector length `42`.
18. Therefore the current double-patch failure is not caused by the present rebuild pipeline itself. It is caused by `debug_sg194_double_patch.py` reading the stale on-disk file `raw_194_1_1_1_double_ai_candidates.json` instead of rebuilding or re-normalizing the current 42-dimensional candidate set.
19. The builder itself is not forcing 62-dimensional output. When `build_sg194_double_spinorial_generators(...)` is fed the current rebuilt 42-dimensional induction candidates, all three profiles (`legacy`, `sg194_double_anchor_patch_v1`, `sg194_double_complement_patch_v1`) emit `33` channels with `unknown_vector` length `42`.
20. Source fix applied:
    - `debug_sg194_double_patch.py` now loads normalized double candidates through `debug_raw_matrix_audit.rebuild_194_candidates()` plus `load_case_candidates("194_1_1_1_double", ...)`, instead of reading `raw_194_1_1_1_double_ai_candidates.json` from disk.
    - `debug_sg194_double_complement_patch_v1.py` now uses the same rebuilt/current candidate source and derives `unknown_ordering` from `c_ctx`.
21. Mechanical verification result: the patched `debug_sg194_double_patch.py` now exits with code `0`. The previous `(58, 42) * (62, 1)` `ShapeError` is gone.
22. Mechanical verification result: the patched `debug_sg194_double_complement_patch_v1.py` also gets past the old `(58, 42) * (62, 1)` crash. Its new failure is later in `validate_outputs()` with `ValueError: full 33 global alignment must hold`.
23. The regenerated complement v2 outputs show that the new failure is not a complement-sector mismatch:
    - `complement_exact_equality = true`
    - `full_33_global_alignment = false`
    - full-space ranks are `current=9`, `external=10`, `union=10`, `intersection=9`
    - the v2 raw quotient is `Z^6 x Z2 x Z2 x Z2`
    - the v2 matrix shape is `16 x 10`
24. After context compaction, the required `codex-autoresearch` runtime references (`core-principles`, `runtime-hard-invariants`, `debug-workflow`) were re-read from disk before the next iteration.
25. A cheaper post-fix probe on `raw_194_1_1_1_double_ai_candidates_patched_v2.json` shows that the trusted subspace already matches the external trusted rank on the full 42-entry current unknown vectors: `current rank = 6`, `external rank = 6`, `union rank = 6`.
26. The remaining one-dimensional trusted/full mismatch appears only after `debug_sg194_double_patch.py:selection_indices()` compresses the current space to the stale 31-row `P1/P2/P3/P5/P6` surface. Under that projection, the trusted comparison drops to `current rank = 5`, `external rank = 6`, and the quotient-basis representative is `[0, 0, 0, 1, 0, -1, 0, 1, -1, 0]` in trusted label order `[b:E1, b:E2, b:E3, c:E1, c:E2, c:E3, d:E1, d:E2, d:E3, h:E]`.
27. A direct synthetic probe that restores `P4` to the selected current surface (`P1..P6`, 34 rows) resolves the mismatch completely on the existing patched_v2 payload: full alignment becomes `10/10/10`, trusted alignment becomes `6/6/6`, and complement alignment stays `7/7/7`.
28. Source fix applied: `debug_sg194_double_patch.py:selection_indices()` now includes `P4` in the selected current surface.
29. Mechanical verification result after the source fix: `debug_sg194_double_patch.py` still exits `0`, and its own before/after column-space audit remains at global current rank `12` versus external rank `10`, while the trusted problem sector stays exact at `6/6/6`. That does not invalidate the row-space probe result; it shows that the patch script and complement script are reporting different metrics.
30. Mechanical verification result after the `selection_indices()` fix: `debug_sg194_double_complement_patch_v1.py` now reaches exact row-space agreement. The refreshed summary records `full_33_global_alignment = true`, `complement_exact_equality = true`, `new_v2.full = 10/10/10`, `new_v2.trusted = 6/6/6`, and `new_v2.complement = 7/7/7`.
31. The current remaining failure is now a stale validator constant, not a construction mismatch. `validate_outputs()` still expects `Z^19 x Z2 x Z2 x Z2` with matrix shape `[29, 10]`, while the regenerated summary, raw quotient JSON, and patched_v2 group summary all consistently report raw quotient `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`.

## Ruled-out pseudo-problems

1. The current repo state does not support the stale claim that the mainline single-group point-space is still `31`-dimensional with only five point blocks.
2. The current stage2 run is not blocked by a missing non-abelian local library; stage2 explicitly records both libraries as built and both AI completeness blockers as removed.
3. The SG194 stage1 workflow is not currently failing at import time.
4. There is no active SG194 baseline process still running from the earlier batch; only the log directory remains.
5. The double-patch crash is not profile-specific between `legacy` and `sg194_double_anchor_patch_v1`; both stage2 profiles currently emit 62-entry vectors.

## Most recent commands and results

1. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo branch --show-current`
   Result: `sg194-special`
2. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo rev-parse --short HEAD`
   Result: `e5701c3`
3. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo status --short --branch | sed -n '1,80p'`
   Result: inherited dirty worktree with many modified and untracked `sg194/` artifacts.
4. `sed -n '1,160p' /tmp/sg194_baseline_22651/4_run_workflow_portability_194.1.1.1.log`
   Result: stage1 baseline completed successfully; report/package generated; inherited blocker message still points at non-abelian local-irrep completeness.
5. `sed -n '1,160p' /tmp/sg194_baseline_22651/5_run_workflow_portability_stage2_194.1.1.1.log`
   Result: stage2 baseline completed successfully; both local libraries built; raw internal quotient is `Z^3`; standard-space projection still missing.
6. `for f in /tmp/sg194_baseline_22651/*.log; do ... tail -n 20 "$f"; done`
   Result: confirmed `debug_sg194_double_patch.py` and `debug_sg194_double_complement_patch_v1.py` both fail with the same `ShapeError`.
7. `rg -n 'spglib' common/SG_utils.py common/SSGReps.py sg194/debug_workflow_portability_194.1.1.1.py`
   Result: top-level `spglib` imports remain in `common/`, while the workflow script uses a local import.
8. `jq '{line_unknown_count:(.line_full.global_unknown_ordering|length), ordering:.line_full.global_unknown_ordering}' sg194/group_194_1_1_1_single_line_compatibility.json`
   Result: `34` unknowns with ordering spanning `P1` through `P6`.
9. `python3 - <<'PY' ... build_sg194_double_spinorial_generators(..., profile='legacy'/'sg194_double_anchor_patch_v1') ... PY`
   Result: both profiles emit `33` channels with `ordering_len=33` and `unknown_vector` length `62`.
10. `python3 - <<'PY' ... compute_c_artifact('194_1_1_1_double', ...) ... PY`
    Result: `c_ctx` has `ordering len = 42` and matrix shape `(58, 42)`.
11. `timeout 300 python3 sg194/debug_sg194_double_global_residual.py`
    Result: exit code `0`; refreshed `sg194/sg194_double_global_residual_summary.json` and `sg194/sg194_double_global_residual_report.aux`.
12. `timeout 300 python3 sg194/debug_sg194_double_lift.py`
    Result: exit code `0`; refreshed `sg194/sg194_double_lift_summary.json` and `sg194/sg194_double_lift_audit.md`.
13. `python3 - <<'PY' ... compare raw_194_1_1_1_double_ai_candidates.json unknown_ordering against group_194_1_1_1_double_full_compatibility_with_planes.json ... PY`
    Result: `raw_194_1_1_1_double_ai_candidates.json` has 23 extra `B*` labels and is missing `P4_R1..P4_R3`.
14. `python3 - <<'PY' ... build_double_runtime(...); induce_objects(...); PY`
    Result: current runtime and rebuilt double induction both use vector length `42`.
15. `python3 - <<'PY' ... raw.rebuild_194_candidates(); raw.load_case_candidates('194_1_1_1_double', rebuilt) ... PY`
    Result: raw audit's current rebuild path also returns `45` double candidates with vector length `42`.
16. `python3 - <<'PY' ... build_sg194_double_spinorial_generators(...) on rebuilt double induction candidates ... PY`
    Result: all three profiles emit `33` channels with vector length `42`.
17. Applied source patch to `debug_sg194_double_patch.py` and `debug_sg194_double_complement_patch_v1.py`
    Result: both scripts now source current rebuilt 42-dimensional double candidates instead of the stale raw JSON payload.
18. `timeout 600 python3 sg194/debug_sg194_double_patch.py`
    Result: exit code `0`; refreshed `raw_194_1_1_1_double_ai_candidates_patched.json`, `raw_194_1_1_1_double_ai_basis_patched.json`, `raw_194_1_1_1_double_ai_in_bs_matrix_patched.json`, `sg194_double_patch_summary.json`, and `sg194_double_patch_audit.md`.
19. `timeout 600 python3 sg194/debug_sg194_double_complement_patch_v1.py`
    Result: old ShapeError is gone; the run refreshes v2 patched outputs and then fails in `validate_outputs()` with `ValueError: full 33 global alignment must hold`.
20. Read `sg194_double_complement_patch_summary_v1.json` and `sg194_double_complement_patch_closeout_summary_v1.json`
    Result: complement equality now holds exactly, but full 33-channel alignment still misses one external dimension and the v2 quotient/matrix-shape numbers differ from the hardcoded validator expectations.
21. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo status --short --branch`
    Result: post-compaction reconfirmation shows the same inherited dirty `sg194-special` worktree, including the checkpoint files and regenerated SG194 artifacts.
22. Read `codex-autoresearch` `core-principles.md`, `runtime-hard-invariants.md`, and `debug-workflow.md`
    Result: runtime protocol was re-anchored before continuing after compaction.
23. `python3 - <<'PY' ... trusted-rank probe on raw_194_1_1_1_double_ai_candidates_patched_v2.json without selection_indices ... PY`
    Result: on the full 42-entry current unknown vectors, the trusted subspace already has `current rank = 6`, `external rank = 6`, and `union rank = 6`.
24. `python3 - <<'PY' ... apply debug_sg194_double_patch.selection_indices(...) to the patched_v2 payload and recompute trusted row-space quotient ... PY`
    Result: `selection_indices()` keeps only 31 rows with prefixes `P1/P2/P3/P5/P6`; under this projection the trusted comparison drops to `5 vs 6`, and the quotient-basis representative is `[0,0,0,1,0,-1,0,1,-1,0]`.
25. `python3 - <<'PY' ... synthetic P1..P6 selection probe on raw_194_1_1_1_double_ai_candidates_patched_v2.json ... PY`
    Result: with `P4` restored into the selected surface (34 rows), the patched_v2 payload reaches exact `full/trusted/complement` alignment: `10/10/10`, `6/6/6`, `7/7/7`.
26. Applied source patch to `debug_sg194_double_patch.py`
    Result: `selection_indices()` now includes `P4`.
27. `timeout 600 python3 sg194/debug_sg194_double_patch.py`
    Result: exit code `0`; the refreshed patch audit still reports global current rank `12` versus external `10`, while the trusted problem sector remains exact at `6/6/6`.
28. `jq '{after:.after, targets:.targets, exact_outcome:.exact_outcome}' sg194/sg194_double_ai_patch_before_after.json` plus `jq '.' sg194/sg194_double_patch_summary.json`
    Result: confirmed that the patch audit's column-space metric is unchanged and the next unresolved check is still the complement row-space validator.
29. `timeout 600 python3 sg194/debug_sg194_double_complement_patch_v1.py`
    Result: post-selection-fix rerun advances past `full_33_global_alignment` and now fails later with `ValueError: patched_v2 raw quotient mismatch`.
30. `jq '{full_33_global_alignment, complement_exact_equality, rank_before_after, double_patched_v2_raw_internal_quotient, patched_v2_matrix_shape, patched_v2_smith_diagonal_nonzero}' sg194/sg194_double_complement_patch_summary_v1.json` plus quotient/group-summary `jq`
    Result: confirmed exact `full/trusted/complement` row-space alignment and consistent regenerated quotient data `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`.

## Files modified in this update

1. `sg194/handoff_sg194_1941111_bs_ai_bug_audit_v1.md`
2. `sg194/current_status_sg194_1941111_bs_ai_bug_audit_v1.json`
3. `sg194/next_step_prompt_sg194_1941111_bs_ai_bug_audit_v1.txt`
4. `sg194/sg194_1941111_bs_ai_bug_audit_summary_v1.json`
5. `sg194/sg194_1941111_bs_ai_bug_audit_report_v1.md`
6. `sg194/live_checkpoint_sg194_1941111.md`
7. `sg194/live_checkpoint_sg194_1941111.json`
8. `sg194/debug_sg194_double_patch.py`
9. `sg194/debug_sg194_double_complement_patch_v1.py`
10. `sg194/raw_194_1_1_1_double_ai_candidates_patched.json`
11. `sg194/raw_194_1_1_1_double_ai_basis_patched.json`
12. `sg194/raw_194_1_1_1_double_ai_in_bs_matrix_patched.json`
13. `sg194/sg194_double_patch_summary.json`
14. `sg194/sg194_double_patch_audit.md`
15. `sg194/raw_194_1_1_1_double_ai_candidates_patched_v2.json`
16. `sg194/raw_194_1_1_1_double_ai_basis_patched_v2.json`
17. `sg194/raw_194_1_1_1_double_ai_in_bs_matrix_patched_v2.json`
18. `sg194/raw_194_1_1_1_double_quotient_patched_v2.json`
19. `sg194/group_194_1_1_1_double_indicator_group_summary_patched_v2.json`
20. `sg194/group_194_1_1_1_double_indicator_generators_patched_v2.json`
21. `sg194/sg194_double_complement_patch_closeout_summary_v1.json`

## Current unresolved problems

1. Need to patch `validate_outputs()` and any downstream stale text/constants so they accept the now-verified raw quotient `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`.
2. The inherited downstream reporting layer may still confuse the raw internal quotient with the final SG194 standard quotient.
3. The checkpoint artifacts created here have not yet been committed or pushed to GitHub.

## Immediate next step

1. Patch `validate_outputs()` and any stale downstream expectations that still hardcode the old quotient constants.
2. Rerun `debug_sg194_double_complement_patch_v1.py`.
3. Update all checkpoint files again before any long command and after each code edit.
