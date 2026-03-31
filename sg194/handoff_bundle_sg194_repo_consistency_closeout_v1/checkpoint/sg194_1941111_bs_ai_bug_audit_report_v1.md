# SG194 194.1.1.1 Repo Consistency Closeout Report v1

- Current time: 2026-03-31 18:14:31 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Branch: `sg194-special`
- Latest synced `sg194-special`: `a53a9af`
- Latest synced `main`: `a7b4e4d`

## Scope

This phase accepts the repaired double complement followup as complete and only closes repo consistency:

1. stage2 raw-vs-standard quotient semantics,
2. bs\_ai\_separation legacy/current status,
3. `spglib` portability cleanup in `common/`, including the vendored `common/SSGReps/SSGReps/` runtime path,
4. package / README / checkpoint consistency.

## Current findings

1. Local stage2 completion JSONs use the corrected raw-internal quotient schema with `rank_bs = 16`, `raw_internal_quotient_group = Z^3`, and `quotient_group = null`.
2. Local stage2 summary/current-status JSON express the correct interpretation boundary and now report key matrix shape `(58,42)` instead of the stale old `(58,62)` wording.
3. The bs\_ai separation outputs are now explicitly `legacy_stale_reference` and name the stage2 closeout outputs as the current authoritative evidence path.
4. Both the repo-top and vendored `common/` import chains now pass blocked `spglib` / `pymatgen` import verification.
5. The stage2 closeout-v2 package and the bs\_ai legacy-reference package were both regenerated successfully.
6. The lightweight handoff bundle tarball plus `repo_consistency_closeout_bundle_manifest_v1.md` are already present on disk.
7. The required compile/import/regression commands all passed.

## Commands run

1. `python3 -m py_compile common/*.py`
2. `python3 -m py_compile sg194/*.py`
3. blocked-import verification for repo-top and vendored `SG_utils` / `rep_utils` / `SSGReps`
4. `python3 sg194/debug_sg194_bs_ai_separation.py`
5. `python3 sg194/debug_sg194_bs_ai_separation.py --validate`
6. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
7. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`
8. tar-member spot checks for the stage2 and bs\_ai review packages
9. `python3 sg194/debug_sg194_double_patch.py`
10. `python3 sg194/debug_sg194_double_complement_patch_v1.py`

## Next

1. Review the staged diff and remove any out-of-scope old review-package files before commit.
2. Commit the in-scope source/artifact/package/checkpoint outputs on `sg194-special`.
3. Push `origin/sg194-special`.
