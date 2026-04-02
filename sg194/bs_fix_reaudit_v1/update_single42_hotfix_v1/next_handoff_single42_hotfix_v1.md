# Next Handoff: single42 hotfix v1

This branch is still `not final`. The active object is the raw current with-planes 42-unknown shell for SSG `194.1.1.1`.

What is already safe to assume:

- The single authoritative hotfix path materializes with matrix shape `[61, 42]`, rank `29`, nullity `13`.
- `S1_R1..S4_R2` remain in the active unknown ordering.
- The active authoritative line/plane builders use `character`, not `linear_character`.
- The external review package now snapshots current outputs after rebuilding them, so the package is aligned with the current worktree for the key single authoritative files.
- Generic/public semantics keep raw-shell availability separate from target-pending blockage.

What the next session should read first:

1. `sg194/bs_fix_reaudit_v1/update_single42_hotfix_v1/update_status_single42_hotfix_v1.md`
2. `sg194/bs_fix_reaudit_v1/update_single42_hotfix_v1/consistency_check_single42_hotfix_v1.md`
3. `sg194/bs_fix_reaudit_v1/external_review_package_ssg194_bs_fix_v1/README.md`
4. `sg194/bs_fix_reaudit_v1/external_review_package_ssg194_bs_fix_v1/bugs/top_5_bugs.md`
5. `sg194/debug_workflow_portability_194.1.1.1.py`
6. `sg194/pipeline_v2/runtime_backend_free.py`
7. `sg194/pipeline_v2/generic_builders.py`

What not to do next:

- Do not switch the task to Bilbao, magnetic groups, benchmark/internalization, or stage2 closeout.
- Do not claim double mode is repaired.
- Do not claim BS/AI is finalized.

What a legitimate next step would be:

- If another session continues code work, it should stay on the same single authoritative object and either harden the consistency checks further or start a separate, explicitly scoped patch for the remaining generic target-builder / AI completeness blockers.
