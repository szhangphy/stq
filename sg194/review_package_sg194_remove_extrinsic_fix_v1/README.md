# review_package_sg194_remove_extrinsic_fix_v1

## This Round

This round had one goal only: remove `extrinsic` from the active SG194 path and collapse the code back to a single authoritative compatibility builder with exact basis-decomposition semantics.

## Verdict

- `extrinsic` is removed from the active path.
- The only authoritative builder is `authoritative_basis_decomposition_exact_unique_integer_with_phase_aware_l2_v1`.
- `phase_aware_profile = phase_aware_l2_projective_v1` is wired into the active stage1/stage2/generic entrypoints.
- The old coarse `13` is not supported by the repaired main path.
- The repaired main path does not yet reach an authoritative SG194 result: it currently fails at `mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character: Linear system has no solution`.

## Native 194 Status

- single: unavailable, blocked in the authoritative basis-decomposition restriction solve
- double: unavailable, blocked behind the same first authoritative single failure

## Main Blocker

- The solver and object language were cleaned up enough to expose the real representation-layer blocker.
- `character` was rejected as authoritative after the `L6/P2` exact-subduction probe failed there but succeeded under `linear_character`.
- After unifying the authoritative field to `linear_character`, the first remaining blocker moved to `L1/P1`.

## Read First

1. `audit_layer/sg194_remove_extrinsic_patch_summary_v1.md`
2. `audit_layer/sg194_authoritative_builder_regression_v1.json`
3. `audit_layer/sg194_authoritative_single_result_v1.json`
4. `audit_layer/sg194_authoritative_double_result_v1.json`
5. `audit_layer/sg194_solver_consistency_audit_v1.json`
6. `audit_layer/sg194_stage2_role_cleanup_audit_v1.md`
7. `compare_layer/sg194_intrinsic_vs_extrinsic_builder_compare_v1.json`
8. `compare_layer/l6_p2_field_probe.txt`
9. `source_layer/runtime_backend_free.py`
10. `source_layer/generic_builders.py`
