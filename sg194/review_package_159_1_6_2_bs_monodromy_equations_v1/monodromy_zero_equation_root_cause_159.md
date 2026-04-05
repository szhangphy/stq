# Root Cause of Zero-Equation Monodromy Blocks for 159.1.6.2

1. `_collect_same_point_monodromy_pairs(...)`: checked. Not the root cause for `L1/L2/L3/L6`; the selected translated same-point pairs are the intended published-target pairs.
2. `_sample_branch_point_from_orbit_expr(...)`: checked. Changing the branch sample did not change the previous zero-equation verdict, so sample choice was not the main blocker.
3. `monodromy_field="character"`: checked. This was a real blocker. In the old builder, left/right decompositions in character language were identical, so every family collapsed to zero equations.
4. `solve_unique_integer_decomposition(...)` on a shared line basis: checked. This was also a real blocker. Even when continuation was nontrivial, the old algebra compared left/right inside the same line-basis frame and erased the permutation content.
5. capture canonicalization / matched indices: checked. These were not broken, but they kept both branches in the same decomposition frame, which is why the old delta stayed zero.
6. row filtering / sign rules: checked. Not the root cause; the rows were already empty before assembly.

Current post-fix state:
- `L1/L2/L3/L6`: actual monodromy equations now appear because the builder uses translated-capture rep matching and then emits point-level equations for nontrivial permutation cycles.
- `L4/L5`: still zero-equation, because the translated-capture rep matching is identity in the current semantics. These two families remain the concrete residual gap.