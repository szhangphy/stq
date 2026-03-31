# SG194 Double Complement Patch Closeout Report V1

## Code Fixes

- `debug_workflow_portability_194.1.1.1.py` now lazy-loads `spglib` only inside `build_controlled_case()`.
- `debug_sg194_double_complement_patch_v1.py` now treats `debug_raw_matrix_audit.py` as a real dependency and packages it.
- `debug_workflow_portability_stage2_194.1.1.1.py` now reports raw internal quotients separately from the missing final SG194 standard quotient.

## Quotient Facts

- single current raw internal quotient = `Z^3`
- double old raw internal quotient = `Z^3`
- double patched_v2 raw internal quotient = `Z^6 x Z2 x Z2 x Z2`
- patched_v2 matrix shape = `16 x 10`
- patched_v2 smith diagonal nonzero = `[1, 1, 1, 1, 1, 1, 1, 2, 2, 2]`

## Interpretation Boundary

This quotient is computed in the 16-dimensional raw internal BS space and must not yet be reported as the final SG194 standard indicator.

## Package Contract

- dependency graph file = `sg194_double_complement_patch_dependency_graph_v1.json`
- closeout summary file = `sg194_double_complement_patch_closeout_summary_v1.json`
- new review tarball = `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/review_package_sg194_double_complement_patch_followup_v1.tar.gz`
