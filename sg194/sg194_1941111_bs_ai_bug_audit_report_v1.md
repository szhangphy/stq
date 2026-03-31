# SG194 194.1.1.1 BS/AI Bug Audit Report v1

- Current time: 2026-03-31 14:52:35 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Branch: `sg194-special`
- HEAD: `e5701c3`
- Audit phase: selection-index root-cause isolation after post-fix verification

## Scope

This audit is tracking the current SG194 `194.1.1.1` BS/AI workflow state, not stale review-package snapshots. The immediate focus is:

1. confirm which inherited scripts currently pass or fail,
2. separate real current blockers from stale claims,
3. isolate the double-patch `ShapeError`, and
4. preserve rolling state in checkpoint files so the run can survive compaction or interruption.

## Current hard conclusions

1. The active working repo is the nested git repo at `/data/work/szhang/ssg/comprel/stq_repo_export/repo`.
2. The active branch is `sg194-special` and the worktree is already dirty with inherited SG194 edits and outputs.
3. Stage1 portability currently runs to completion.
4. Stage2 portability currently runs to completion and reports:
   - nonabelian single local library built,
   - nonabelian double local library built,
   - single AI completeness unblocked,
   - double AI completeness unblocked,
   - raw internal quotient `Z^3` for both single and double,
   - missing standard-space projection as the current remaining blocker.
5. The current single-group line compatibility state is `34` unknowns with point blocks `P1` through `P6`.
6. The current double-patch path is broken by a concrete matrix-shape bug:
   - compatibility matrix shape `(58, 42)`
   - unknown vector shape `(62, 1)`
7. The same shape bug propagates into `debug_sg194_double_complement_patch_v1.py`.
8. The shape bug is now localized more precisely:
   - `build_sg194_double_spinorial_generators(...)` emits `33` channels with `unknown_vector` length `62` for both the `legacy` and `sg194_double_anchor_patch_v1` profiles.
   - `compute_c_artifact('194_1_1_1_double', ...)` returns a compatibility matrix with `42` columns.
   - `debug_sg194_double_patch.py:build_channel_candidates(...)` currently multiplies those `62`-entry raw vectors by the `42`-column compatibility matrix without projection or ordering translation.
9. `debug_sg194_double_global_residual.py` and `debug_sg194_double_lift.py` both now pass on direct rerun.
10. The stale raw ordering mismatch is now specific enough to search for the serialization bug:
   - `raw_194_1_1_1_double_ai_candidates.json` has `62` labels.
   - relative to the current compatibility ordering, it contains `23` extra `B1..B5` labels.
   - it omits `P4_R1`, `P4_R2`, and `P4_R3`.
11. The current rebuild path is already corrected:
   - `build_double_runtime(...)` returns `42`-entry ordering.
   - `stage2.induce_objects(...)` currently emits `45` double candidates with vector length `42`.
   - `debug_raw_matrix_audit.load_case_candidates('194_1_1_1_double', rebuilt)` also yields `45` candidates with vector length `42`.
   - this isolates the live bug to `debug_sg194_double_patch.py` reading stale on-disk raw candidates instead of current rebuilt ones.
12. The stage2 spinorial builder itself is compatible with the current 42-dimensional path:
   - when fed rebuilt 42-entry induction candidates,
   - all three double profiles emit `33` channels with vector length `42`.
13. Source fix has been applied:
   - `debug_sg194_double_patch.py` now rebuilds/loads the current normalized double candidates through `debug_raw_matrix_audit`.
   - `debug_sg194_double_complement_patch_v1.py` now uses the same rebuilt/current candidate source and `c_ctx` ordering.
14. First post-fix verification succeeded:
   - `debug_sg194_double_patch.py` now exits `0`.
   - the previous 42-vs-62 `ShapeError` no longer appears.
15. Second post-fix verification also moved forward:
   - `debug_sg194_double_complement_patch_v1.py` no longer fails at the old 42-vs-62 multiplication.
   - it now fails later in `validate_outputs()` with `ValueError: full 33 global alignment must hold`.
16. The regenerated complement v2 outputs refine that failure:
    - `complement_exact_equality = true`
    - `full_33_global_alignment = false`
    - full-space ranks are `current=9`, `external=10`, `union=10`, `intersection=9`
    - the v2 raw quotient is `Z^6 x Z2 x Z2 x Z2`
    - the v2 matrix shape is `16 x 10`
17. After context compaction, the required `codex-autoresearch` runtime references were re-read from disk and the repo state was reconfirmed before continuing.
18. A direct trusted-rank probe on `raw_194_1_1_1_double_ai_candidates_patched_v2.json` shows that the trusted subspace already matches the external trusted rank on the full 42-entry current unknown vectors: `current rank = 6`, `external rank = 6`, `union rank = 6`.
19. The remaining one-dimensional trusted/full mismatch appears only after `debug_sg194_double_patch.py:selection_indices()` compresses the current space to the legacy 31-row `P1/P2/P3/P5/P6` surface, excluding `P4`. Under that projection, the trusted comparison drops to `current rank = 5`, `external rank = 6`, and the quotient representative is `[0,0,0,1,0,-1,0,1,-1,0]` in trusted label order `[b:E1, b:E2, b:E3, c:E1, c:E2, c:E3, d:E1, d:E2, d:E3, h:E]`.
20. A direct synthetic probe that restores `P4` to the selected current surface (`P1..P6`, 34 rows) resolves the mismatch completely on the existing patched_v2 payload: full alignment becomes `10/10/10`, trusted alignment becomes `6/6/6`, and complement alignment stays `7/7/7`.
21. Source patch applied: `debug_sg194_double_patch.py:selection_indices()` now includes `P4`.
22. After the selection fix, `debug_sg194_double_patch.py` still exits `0`, but its own before/after column-space audit remains at global current rank `12` versus external rank `10`, while the trusted problem sector stays exact at `6/6/6`. The next decisive check is therefore still the complement row-space validator.
23. After the selection fix, `debug_sg194_double_complement_patch_v1.py` now reports exact `full/trusted/complement` row-space alignment and only fails later on `ValueError: patched_v2 raw quotient mismatch`.
24. The regenerated complement summary, raw quotient JSON, and patched_v2 group summary now consistently report raw quotient `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`. This indicates the remaining failure is a stale validator/report constant, not a surviving construction mismatch.
25. Source patch applied: `debug_sg194_double_complement_patch_v1.py:validate_outputs()` now checks the regenerated quotient constants instead of the stale `Z^19` / `[29, 10]` expectations.

## Pseudo-problems already ruled out

1. "The current mainline still has only five point blocks and 31 point-space unknowns."
2. "Stage2 still fails because the nonabelian local libraries are missing."
3. "The current stage1 workflow fails on import before any real SG194 work happens."

## Recent mechanical evidence

1. `/tmp/sg194_baseline_22651/4_run_workflow_portability_194.1.1.1.log`
   Result: stage1 completed and generated the inherited report/package output.
2. `/tmp/sg194_baseline_22651/5_run_workflow_portability_stage2_194.1.1.1.log`
   Result: stage2 completed and records the current unblocked-library state.
3. `/tmp/sg194_baseline_22651/7_run_sg194_double_complement_patch_v1.log`
   Result: fails with `ShapeError: Matrix size mismatch: (58, 42) * (62, 1)`.
4. `/tmp/sg194_baseline_22651/8_run_sg194_double_patch.log`
   Result: fails with the same `ShapeError`.
5. `sg194/group_194_1_1_1_single_line_compatibility.json`
   Result: `.line_full.global_unknown_ordering | length == 34`.
6. `python3` probe on `build_sg194_double_spinorial_generators(...)`
   Result: both profiles currently emit `62`-entry vectors.
7. `python3` probe on `compute_c_artifact('194_1_1_1_double', ...)`
   Result: the compatibility matrix is `(58, 42)`.
8. Direct rerun of `python3 sg194/debug_sg194_double_global_residual.py`
   Result: exit code `0`.
9. Direct rerun of `python3 sg194/debug_sg194_double_lift.py`
   Result: exit code `0`.
10. Comparison of `raw_194_1_1_1_double_ai_candidates.json` against `group_194_1_1_1_double_full_compatibility_with_planes.json`
    Result: extra labels are `B1..B5` entries; missing labels are `P4_R1..P4_R3`.
11. Probe of `build_double_runtime(...)`, `induce_objects(...)`, and `raw.load_case_candidates('194_1_1_1_double', rebuilt)`
    Result: the current rebuild path yields `42`-entry double vectors, not `62`-entry vectors.
12. Probe of `build_sg194_double_spinorial_generators(...)` on rebuilt double induction candidates
    Result: all three profiles emit `42`-entry channel vectors.
13. Applied source patch to both double patch entrypoints
    Result: both now avoid the stale on-disk raw candidate file.
14. Rerun of `python3 sg194/debug_sg194_double_patch.py`
   Result: exit code `0`; patched raw AI artifacts and patch summary/audit refreshed.
15. Rerun of `python3 sg194/debug_sg194_double_complement_patch_v1.py`
   Result: old ShapeError is gone; v2 patched outputs refresh before a later `full 33 global alignment must hold` failure in `validate_outputs()`.
16. Read `sg194_double_complement_patch_summary_v1.json` and `sg194_double_complement_patch_closeout_summary_v1.json`
   Result: complement equality now holds, but full-space alignment still misses one external dimension and the regenerated quotient/matrix-shape values differ from the hardcoded validator expectations.

## Portability note

`common/SG_utils.py` and `common/SSGReps.py` still import `spglib` at module import time. The SG194 workflow script already uses a lazy import inside `build_controlled_case`. This is a real portability concern, but it is not the same as the current SG194 double-patch shape bug.

## Open issues

1. Implement the now-supported `selection_indices()` fix that restores `P4` into the selected current surface.
2. Decide whether the hardcoded validator expectations are stale or the complement v2 result is still wrong after that fix.
3. Audit downstream summaries so the raw internal quotient is never misreported as the final SG194 standard quotient.

## Next action

Rerun `debug_sg194_double_complement_patch_v1.py` after the validator-constant fix, inspect the downstream output/report path there, then update every checkpoint file again before and after the next verification run.
