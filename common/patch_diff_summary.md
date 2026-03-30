# SG194 Double Patch Diff Summary

## Real Source Patch

- Patched `debug_workflow_portability_stage2_194.1.1.1.py`.
- Added `build_sg194_double_spinorial_generators(...)` so the real stage-2 generator-construction layer now owns the `33`-column SG194 double spinorial current-generator basis.
- The new builder exposes two profiles:
  - `legacy`: reproduces the old downstream pair-sum / four-way-sum channelization.
  - `sg194_double_anchor_patch_v1`: emits the patched SG194 current generators directly from the stage-2 source layer.

## What Changed

- Old behavior:
  - `2b/2c/2d` used the downstream implicit rule `(1,2) -> E1`, `(3,4) -> E2`, `(5,6) -> E3`.
  - `6h` used the downstream implicit four-way sum.
  - The raw `45` local-irrep candidates were the only source-level output, so audits had to hardcode the spinorial channelization later.
- New behavior:
  - Stage-2 can now emit the current spinorial channels itself.
  - The patched profile keeps the identity sectors one-to-one and changes the SG194 problem sector to an exact `2b`-anchored channel assembly that removes the localized `2b/2c/2d/6h` row-space mismatch.

## Relation To The Localized Deltas

- `delta_c1_minus_b1` and `delta_d1_minus_b1` proved that the old current-only excess lived in the `2b/2c/2d/6h` channel layer, not in the BS kernel.
- A pure downstream relabel / permutation was not enough.
- The exact structured row-space solve showed that a family-local `E1` patch alone has no solution.
- The patched stage-2 builder therefore applies the smallest exact source-level correction that kills the trusted problem-sector mismatch:
  - `c:E3 -> 2*c:E3 - b:E3`
  - `d:E3 -> 2*d:E3 - b:E3`
  - `6h:E -> 6h:E - b:E3`

## Why This Counts As The Real Generator Patch

- The patch is no longer trapped in `debug_*alignment*` consumers.
- The patched 33-column current generator set is now produced from the stage-2 source layer itself and then serialized into new raw artifacts.
