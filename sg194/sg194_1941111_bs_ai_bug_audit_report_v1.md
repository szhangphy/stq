# SG194 194.1.1.1 BS/AI Bug Audit Report v1

- Current time: 2026-03-31 15:03:02 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Branch: `sg194-special`
- Latest synced audit-fix commit: `a48469a`
- Audit phase: closeout after final complement-patch verification and GitHub sync

## Scope

This audit tracked the current SG194 `194.1.1.1` workflow state in the live repo, not stale review-package summaries. The concrete goals were:

1. identify real current failures,
2. separate stale context from current code behavior,
3. repair the SG194 double-patch and complement-patch path,
4. preserve rolling state in checkpoint files so the task survives compaction or interruption, and
5. sync the relevant fixes to `origin/sg194-special`.

## Final hard conclusions

1. The active working repo is the nested git repo at `/data/work/szhang/ssg/comprel/stq_repo_export/repo`.
2. Stage1 portability and stage2 portability both pass in the current repo state.
3. The current single-group line compatibility state is `34` unknowns with point blocks `P1` through `P6`; older `31`-dimensional claims are stale for this branch snapshot.
4. The original SG194 double-patch failure was a real stale-input bug:
   - the current compatibility matrix was built in a `42`-dimensional space,
   - but the patch scripts were reading a stale serialized `62`-entry raw candidate file.
5. The live rebuild path itself was already consistent in `42` dimensions, so the fix was to stop trusting the stale on-disk raw candidate payload.
6. `sg194/debug_sg194_double_patch.py` and `sg194/debug_sg194_double_complement_patch_v1.py` were patched to load rebuilt/current candidates through `debug_raw_matrix_audit`.
7. After that fix, the remaining trusted/full mismatch was traced to a stale selected current surface: `selection_indices()` excluded `P4` and compressed the current space to legacy `P1/P2/P3/P5/P6`.
8. `selection_indices()` now includes `P4`, which restores exact patched-v2 row-space agreement.
9. After the selected-surface fix, the remaining complement-script failure was not geometric or algebraic. It was a stale validator constant: the regenerated raw quotient is `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`, not the older `Z^19 x Z2 x Z2 x Z2` / `[29, 10]` expectation.
10. `validate_outputs()` now checks the regenerated quotient constants.
11. Final mechanical verification passed:
    - `debug_sg194_double_patch.py` exits `0`
    - `debug_sg194_double_complement_patch_v1.py` exits `0`
    - `full_33_global_alignment = true`
    - `complement_exact_equality = true`
    - patched-v2 raw quotient = `Z^6 x Z2 x Z2 x Z2`
    - patched-v2 matrix shape = `[16, 10]`
    - patched-v2 Smith diagonal nonzero = `[1,1,1,1,1,1,1,2,2,2]`
12. `common/SG_utils.py` and `common/SSGReps.py` still hard-import `spglib` at top level. That is still worth cleaning up for portability, but it is not the bug that was breaking the SG194 double-patch path.

## Key evidence

1. `python3 sg194/debug_workflow_portability_194.1.1.1.py`
   Result: passed.
2. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
   Result: passed; stage2 reports both local libraries built and raw internal quotient `Z^3`.
3. `jq '.line_full.global_unknown_ordering | length' sg194/group_194_1_1_1_single_line_compatibility.json`
   Result: `34`.
4. `timeout 600 python3 sg194/debug_sg194_double_patch.py`
   Result: final rerun passed.
5. `timeout 600 python3 sg194/debug_sg194_double_complement_patch_v1.py`
   Result: final rerun passed.
6. `jq '{full_33_global_alignment, complement_exact_equality, double_patched_v2_raw_internal_quotient, patched_v2_matrix_shape, patched_v2_smith_diagonal_nonzero}' sg194/sg194_double_complement_patch_summary_v1.json`
   Result: `true`, `true`, `Z^6 x Z2 x Z2 x Z2`, `[16,10]`, `[1,1,1,1,1,1,1,2,2,2]`.
7. `git push origin sg194-special`
   Result: pushed `e5701c3..a48469a`.

## Ruled out

1. The current repo is not still stuck at five point blocks / `31` point-space unknowns.
2. The current stage2 failure mode is not missing local libraries.
3. The last complement-script failure was not a surviving row-space construction mismatch.

## Remaining follow-up work

1. Separate raw internal quotient reporting from final SG194 standard quotient reporting in downstream summaries.
2. Lazy-import `spglib` inside `common/SG_utils.py` and `common/SSGReps.py` for portability if that cleanup is requested later.

## Resume rule

If this task resumes in a later session, start from the checkpoint files written in this run rather than any older review-package snapshot.
