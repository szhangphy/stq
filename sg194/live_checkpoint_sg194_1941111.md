# Live Checkpoint: SG194 194.1.1.1

- Last updated: 2026-03-31 14:52:35 +0800
- Branch: `sg194-special`
- HEAD: `e5701c3`
- Phase: post-compaction checkpoint refresh; inspecting the remaining complement full-space mismatch

## Latest state

1. Stage1 portability passed.
2. Stage2 portability passed and reports both nonabelian libraries built plus raw internal quotient `Z^3`.
3. Current blocker is no longer missing local libraries; it is the missing standard-space projection and the broken double-patch path.
4. Current single-group line compatibility has `34` unknowns with point blocks `P1` through `P6`.
5. `debug_sg194_double_patch.py` and `debug_sg194_double_complement_patch_v1.py` both fail with `ShapeError: Matrix size mismatch: (58, 42) * (62, 1)`.
6. The mismatch is now localized: stage2 emits `62`-entry raw vectors, while `compute_c_artifact(...)` returns a `42`-column compatibility matrix.
7. `debug_sg194_double_global_residual.py` and `debug_sg194_double_lift.py` both reran successfully.
8. The stale raw ordering adds `23` `B1..B5` labels and omits `P4_R1..P4_R3` relative to the current compatibility ordering.
9. The current rebuild path already emits `42`-entry double vectors, so the live bug is the patch script reading a stale on-disk raw JSON file.
10. The stage2 double spinorial builder also stays in `42` dimensions when fed rebuilt double induction candidates.
11. Source patch is in place for both double patch entrypoints.
12. Patched `debug_sg194_double_patch.py` now passes.
13. Patched `debug_sg194_double_complement_patch_v1.py` gets past the old ShapeError but now fails later with `full 33 global alignment must hold`.
14. Complement v2 already matches exactly on the 23 complement channels; the remaining gap is one missing external full-space dimension.
15. After compaction, the required autoresearch runtime docs were re-read and git status was reconfirmed before continuing.
16. On the full 42-entry current unknown vectors, the trusted subspace already matches the external trusted rank exactly: `6 vs 6`.
17. The remaining `5 vs 6` trusted mismatch appears only after `selection_indices()` compresses the current space to the legacy 31-row `P1/P2/P3/P5/P6` surface, excluding `P4`.
18. A synthetic `P1..P6` selection probe on the patched_v2 payload restores exact `full/trusted/complement` alignment: `10/10/10`, `6/6/6`, `7/7/7`.
19. Source patch applied: `selection_indices()` now includes `P4`.
20. After the selection fix, `debug_sg194_double_patch.py` still exits `0` and its own column-space audit remains at global `12 vs 10`, while the trusted problem sector stays exact at `6/6/6`.
21. After the selection fix, `debug_sg194_double_complement_patch_v1.py` now reports exact `full/trusted/complement` row-space alignment and only fails later on a stale raw-quotient validator constant.
22. The regenerated complement summary, raw quotient JSON, and patched_v2 group summary now consistently report raw quotient `Z^6 x Z2 x Z2 x Z2` with matrix shape `16 x 10`.
23. Source patch applied: `debug_sg194_double_complement_patch_v1.py:validate_outputs()` now checks the mechanically regenerated quotient constants.

## Latest commands

1. Read baseline logs under `/tmp/sg194_baseline_22651`.
2. Queried `spglib` import locations with `rg`.
3. Queried the single-line compatibility ordering with `jq`.
4. Probed stage2 builder output lengths for both double spinorial profiles.
5. Probed `compute_c_artifact('194_1_1_1_double', ...)` for ordering length and matrix shape.
6. Reran `debug_sg194_double_global_residual.py` and `debug_sg194_double_lift.py`.
7. Compared the raw double AI candidate ordering against the current double compatibility ordering.
8. Probed the current build_double_runtime / induce_objects / raw.rebuild_194_candidates paths.
9. Probed `build_sg194_double_spinorial_generators(...)` on rebuilt double induction candidates.
10. Patched `debug_sg194_double_patch.py` and `debug_sg194_double_complement_patch_v1.py`.
11. Reran `debug_sg194_double_patch.py` successfully.
12. Reran `debug_sg194_double_complement_patch_v1.py` and captured the later alignment failure.
13. Read the regenerated complement summary/closeout files.
14. Reconfirmed `git status --short --branch` after compaction.
15. Re-read `codex-autoresearch` `core-principles.md`, `runtime-hard-invariants.md`, and `debug-workflow.md`.
16. Measured the trusted rank directly on `raw_194_1_1_1_double_ai_candidates_patched_v2.json` without `selection_indices()`.
17. Measured the trusted rank again after applying `selection_indices()` to the same patched-v2 payload.
18. Ran a synthetic `P1..P6` selection probe on the patched_v2 payload.
19. Patched `debug_sg194_double_patch.py:selection_indices()` to include `P4`.
20. Reran `debug_sg194_double_patch.py` and read `sg194_double_ai_patch_before_after.json` / `sg194_double_patch_summary.json`.
21. Reran `debug_sg194_double_complement_patch_v1.py` after the selection fix.
22. Read `sg194_double_complement_patch_summary_v1.json`, `raw_194_1_1_1_double_quotient_patched_v2.json`, and `group_194_1_1_1_double_indicator_group_summary_patched_v2.json`.

## Next

1. Rerun `debug_sg194_double_complement_patch_v1.py`, then compare the new quotient/matrix-shape values against the validator expectations.
2. Refresh all checkpoint files before the next long command.
