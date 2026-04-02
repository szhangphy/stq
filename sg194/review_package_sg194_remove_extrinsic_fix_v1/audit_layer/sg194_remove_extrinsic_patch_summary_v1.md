# Patch Summary

- `sg194/pipeline_v2/runtime_backend_free.py`: authoritative line/plane compatibility stays in basis-decomposition language; `LUsolve` was replaced by exact `gauss_jordan_solve` with non-unique and non-integral checks. The active default builder is now `authoritative`, `extrinsic` raises as retired/non-authoritative, and the active restriction field was unified to `linear_character` after `character` failed the L6/P2 exact-subduction probe.
- `sg194/debug_workflow_portability_194.1.1.1.py`: stage1 authoritative pilot now uses the same exact decomposition semantics, the same `linear_character` basis-decomposition field, and defaults `phase_aware_l2_projective_v1` into both single and double pilot paths.
- `sg194/pipeline_v2/generic_builders.py`: default active path changed from retired class-sum compare logic to the single authoritative basis-decomposition builder, with phase-aware L2 forwarded into candidate induction.
- `sg194/debug_workflow_portability_stage2_194.1.1.1.py`: stage2 main path was reduced to a consumer over authoritative stage1 runtime only; projection/internalization helpers are no longer allowed to override the active source result.
- `sg194/debug_sg194_standard_space_projection_v1.py`: reclassified as legacy/historical/non-authoritative; validation no longer asserts that it is the source-layer truth.

## Current Authoritative Builder

- `authoritative_basis_decomposition_exact_unique_integer_with_phase_aware_l2_v1`
- `phase_aware_profile = phase_aware_l2_projective_v1`
- object language: exact unique integer basis-decomposition compatibility on line and plane blocks

## Retired Paths

- `extrinsic` line-class refinement: retired/non-authoritative/debug-only
- class-sum `intrinsic` builder: compare-only/non-authoritative
- legacy standard-space projection: historical compare-only

## Current Blocker

- `mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character: Linear system has no solution`
