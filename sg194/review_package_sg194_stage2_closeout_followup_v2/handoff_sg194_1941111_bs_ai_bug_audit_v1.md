# SG194 194.1.1.1 Repo Consistency Closeout Handoff v1

- Current time: 2026-03-31 18:14:31 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Current branch: `sg194-special`
- Current HEAD: `a53a9af`
- Latest synced `origin/sg194-special`: `a53a9af`
- Latest synced `origin/main`: `a7b4e4d`
- Current subtask: final staged-scope review, git commit, and git push.

## Accepted hard facts

1. The double complement followup is already accepted as complete for this phase:
   - patched-v2 raw internal quotient `Z^6 x Z2 x Z2 x Z2`
   - patched-v2 matrix shape `[16, 10]`
   - `full_33_global_alignment = true`
   - `complement_exact_equality = true`
2. This phase is repo consistency closeout only. Do not reopen trusted-sector work, 42-vs-62 mismatch analysis, or the complement proof layer.

## Final verified findings for this phase

1. `autoresearch_resume_check.py` returned `full_resume`; the existing run state matches `research-results.tsv`.
2. No active long-running `stage2` / `double_patch` / `double_complement` process was left running from the previous round.
3. Local stage2 completion JSONs now consistently report:
   - `rank_bs = 16`
   - `raw_internal_quotient_group = Z^3`
   - `quotient_group = null`
   - `standard_space_projection_status = missing`
4. Local `current_status_194.1.1.1_stage2.json` and `workflow_portability_stage2_summary_194.1.1.1.json` correctly separate the raw internal quotient from the missing standard-space projection, with key matrix shape `[58, 42]`, rank `26`, nullity `16`.
5. `debug_sg194_bs_ai_separation.py` is now unambiguously `legacy_stale_reference`, and its generated summary/status/package explicitly point to the stage2 closeout outputs as the current authoritative SG194 evidence path.
6. Repo-top `common/SG_utils.py`, `common/SSGReps.py`, and `common/rep_utils.py` are on the lazy-import path.
7. The real runtime import path under `common/SSGReps/SSGReps/` is now patched onto the same lazy-import contract; under active `spglib` / `pymatgen` import blocking, both repo-top and vendored `SG_utils`, `rep_utils`, and `SSGReps` import successfully.
8. `review_package_sg194_stage2_closeout_followup_v2/` has been regenerated and now contains:
   - generated `README.md`
   - refreshed `SG_utils.py`, `SSGReps.py`, `rep_utils.py`
   - refreshed bs\_ai legacy-status files
   - rolling closeout checkpoint files
9. The final rolling checkpoint files are already synced into both `review_package_sg194_stage2_closeout_followup_v2/` and `handoff_bundle_sg194_repo_consistency_closeout_v1/`, and both tarballs are present on disk.
10. `review_package_sg194_bs_ai_separation_audit/` has been regenerated and now carries the current-authoritative-path warning instead of a half-current legacy status.
11. Required regression reruns completed successfully:
   - `python3 sg194/debug_sg194_bs_ai_separation.py`
   - `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
   - `python3 sg194/debug_sg194_double_patch.py`
   - `python3 sg194/debug_sg194_double_complement_patch_v1.py`

## Source edits applied in this phase

1. `common/SG_utils.py`
   - top-level `spglib` import removed
   - `_require_spglib(...)` helper added
2. `common/SSGReps.py`
   - top-level `from spglib import *` removed
3. `common/rep_utils.py`
   - top-level `from spglib import *` removed
4. `common/SSGReps/SSGReps/SG_utils.py`
   - vendored runtime path now uses `_require_spglib(...)` lazy import
5. `common/SSGReps/SSGReps/SSGReps.py`
   - vendored runtime path no longer top-level imports `spglib` or `PointGroupAnalyzer`
6. `common/SSGReps/SSGReps/rep_utils.py`
   - vendored runtime path no longer top-level imports `spglib` or `PointGroupAnalyzer`
7. `sg194/debug_workflow_portability_stage2_194.1.1.1.py`
   - stage2 closeout-v2 package contract refreshed
   - package copy logic now resolves missing baseline files through `resolve_repo_asset(...)`
8. `sg194/debug_sg194_bs_ai_separation.py`
   - adds explicit `current_authoritative_reference_outputs`
   - legacy outputs/package now point reviewers to the stage2 closeout path
9. `sg194/README.md`
   - stage2 closeout-v2 and bs\_ai legacy-reference sections retained as the top-level entrypoint

## Commands run in this phase

1. `git status --short --branch`
2. `git branch -a`
3. `git remote -v`
4. `python3 /data/home/szhang/.codex/skills/codex-autoresearch/scripts/autoresearch_resume_check.py --repo /data/work/szhang/ssg/comprel/stq_repo_export/repo`
5. `ps -eo pid,etimes,cmd | rg 'debug_workflow_portability_stage2_194\.1\.1\.1|debug_sg194_double_patch|debug_sg194_double_complement_patch_v1|double_complement|double_patch|stage2'`
6. `python3 -m py_compile common/*.py`
7. `python3 -m py_compile sg194/*.py`
8. blocked-import verification for repo-top and vendored `SG_utils` / `rep_utils` / `SSGReps`
9. `python3 sg194/debug_sg194_bs_ai_separation.py`
10. `python3 sg194/debug_sg194_bs_ai_separation.py --validate`
11. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
12. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`
13. tar-member spot checks for the stage2 and bs\_ai review packages
14. `python3 sg194/debug_sg194_double_patch.py`
15. `python3 sg194/debug_sg194_double_complement_patch_v1.py`

## Immediate next step

1. Review the staged diff and remove any out-of-scope old review-package files before commit.
2. Commit the in-scope source/artifact/package/checkpoint outputs on `sg194-special`.
3. Push to `origin/sg194-special`.
