# Live Checkpoint: SG194 194.1.1.1

- Last updated: 2026-03-31 15:03:02 +0800
- Branch: `sg194-special`
- Latest synced audit-fix commit: `a48469a`
- Phase: closeout checkpoint after successful complement rerun and successful push

## Latest state

1. Stage1 portability passed.
2. Stage2 portability passed and reports both nonabelian libraries built.
3. Current single-group line compatibility has `34` unknowns with point blocks `P1` through `P6`.
4. The original double-patch failure was the stale `62`-entry raw double candidate file being used against the current `42`-column compatibility matrix.
5. Both double patch entrypoints now load rebuilt/current candidates through `debug_raw_matrix_audit`.
6. The later row-space mismatch came from `selection_indices()` excluding `P4`; `selection_indices()` now includes `P4`.
7. The last complement-script failure came from stale quotient validator constants; `validate_outputs()` now checks the regenerated raw quotient `Z^6 x Z2 x Z2 x Z2` with matrix shape `[16, 10]`.
8. `debug_sg194_double_patch.py` now passes.
9. `debug_sg194_double_complement_patch_v1.py` now passes.
10. Final summary fields are:
    - `full_33_global_alignment = true`
    - `complement_exact_equality = true`
    - `double_patched_v2_raw_internal_quotient = Z^6 x Z2 x Z2 x Z2`
    - `patched_v2_matrix_shape = [16, 10]`
    - `patched_v2_smith_diagonal_nonzero = [1,1,1,1,1,1,1,2,2,2]`
11. Audit-fix commit `a48469a` has already been pushed to `origin/sg194-special`.
12. Optional follow-up only:
    - downstream raw-vs-standard quotient wording still needs cleanup
    - `spglib` is still hard-imported at top level in `common/`

## Latest commands

1. `timeout 600 python3 sg194/debug_sg194_double_complement_patch_v1.py`
   Result: exit code `0`.
2. `jq '{full_33_global_alignment, complement_exact_equality, double_patched_v2_raw_internal_quotient, patched_v2_matrix_shape, patched_v2_smith_diagonal_nonzero}' sg194/sg194_double_complement_patch_summary_v1.json`
   Result: verified the final aligned summary values.
3. `git -C /data/work/szhang/ssg/comprel/stq_repo_export/repo push origin sg194-special`
   Result: pushed `e5701c3..a48469a`.

## Next

1. If more SG194 work is requested, start from the checkpoint files first.
2. Treat the repaired patch path as closed unless a new regression appears.
