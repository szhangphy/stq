# External Review Package: SSG 194.1.1.1 BS Fix v1

## Purpose

- Hand off the exact source-level BS/AI bug repair for SSG `194.1.1.1`.
- Provide original vs final source snapshots, unified diffs, first-failure evidence, key object dumps, and one-command repro scripts for line-by-line external code review.

## One-Command Repro

- Original first failure: `python3 /data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/bs_fix_reaudit_v1/external_review_package_ssg194_bs_fix_v1/repro/reproduce_original_first_failure.py`
- Current diagnostic experiment: `bash /data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/bs_fix_reaudit_v1/external_review_package_ssg194_bs_fix_v1/repro/run_current_diagnostic_experiment.sh`

## Review Order

- `bugs/top_5_bugs.md`
- `evidence/first_failure/`
- `dumps/l1_line_block_before_after.json`
- `dumps/s3_plane_block_before_after.json`
- `dumps/shape_rank_nullity_comparison.json`
- `patches/overall.patch`
- `sources/original/` and `sources/final/`

## Included

- Source snapshot count: `6`
- Output snapshot count: `5`
- Overall patch: `patches/overall.patch`
- First failure stderr: `evidence/first_failure/stderr.txt`
- First failure exit code: `1`

## Scope

- No Bilbao comparisons.
- No magnetic-group detour.
- No benchmark/internalization mainline.
- Focus is the repo-internal BS construction and generic/public shell semantics for `194.1.1.1`.
