# SG194 Double Metric Bug Audit

## Original Bug
- wrong helper: `row_rank_union_intersection`
- The columns are the generators.
- The verdict should therefore be stated in terms of generator-span / column-space logic.
- The old helper name and its report language described a row-space comparison, which is not the right semantic object for the patch verdict.

## Directly Impacted Old Fields
- `sg194_double_ai_patch_before_after.json`: ['before.global_union_rank', 'before.global_intersection_rank', 'before.problem_sector_union_rank', 'before.problem_sector_intersection_rank', 'after.global_union_rank', 'after.global_intersection_rank', 'after.problem_sector_union_rank', 'after.problem_sector_intersection_rank', 'after.delta_c1_minus_b1_disappeared', 'after.delta_d1_minus_b1_disappeared', 'targets.wanted_problem_union_drop_8_to_6', 'targets.wanted_global_rank_drop_12_to_10', 'exact_outcome.problem_sector_exact_identification_after_patch', 'exact_outcome.global_rank_drop_achieved']
- `sg194_double_patch_summary.json`: ['old_problem_sector_union_rank', 'new_problem_sector_union_rank', 'delta_c1_minus_b1_disappeared', 'delta_d1_minus_b1_disappeared', 'bs_only_after_patch_reason']
- markdown reports: ['sg194_double_patch_audit.md', 'sg194_double_patch_report.md']

## Corrected Metric
- generator verdict helper: `column_space_union_intersection`
- row diagnostic helper: `row_space_union_intersection`
- transpose rationale: The original matrices do not share a row ambient, but their transposes share the same generator-label row dimension. So the corrected generator-span comparison is the column-space comparison of the transposed matrices.
- delta rule: The `delta disappeared` flag is now determined by an explicit current-side ambient membership test of the named delta vectors, not by the shortcut `problem_sector_union_rank == external_rank`.

## Numerical Revalidation
- old buggy global union -> corrected global union: `21 -> 21`
- old buggy problem union -> corrected problem union: `6 -> 6`
- union numbers changed: `False`
- delta verdict changed: `True`

## Downgraded Or Withdrawn Claims
- The old `delta_c1_minus_b1 disappeared` claim.
- The old `delta_d1_minus_b1 disappeared` claim.
- Any old statement that equated `problem_sector_union_rank == external_rank` with explicit delta elimination.

## Revalidated Claims
- The generator patch still shrinks the trusted 2b/2c/2d/6h problem-sector mismatch from union rank 8 to 6.
- The global 33-generator mismatch is not reduced.
