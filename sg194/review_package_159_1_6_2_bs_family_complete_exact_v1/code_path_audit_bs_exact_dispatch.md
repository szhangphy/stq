# Code Path Audit for BS Exact Dispatch

## Before this patch
Exact dispatch depended on provenance:
- `generic_builders._build_target_line_blocks_for_window(...)`
- `if line.metadata.source_letter == "recovered_family_special_line"`
- then `_build_target_restriction_line_block(...)` exact path
- otherwise fallback to `_build_generic_line_block(...)` -> coarse backend

That created a source-dependent split inside the same Bilbao target semantics.

## After this patch
Exact dispatch depends on family semantics:
- `_canonical_target_line_family_key(...)`
- `_target_line_family_requires_exact_rows(...)`
- semantic rule: 1D target family with `source_mult == 1` under authoritative/intrinsic build -> exact restriction rows
- `_build_target_line_blocks_for_window(...)` now routes all such families through `_build_target_restriction_line_block(...)`
- `_build_target_restriction_line_block(...)` marks exact rows with `builder_variant = intrinsic`
- `_build_target_monodromy_block_from_pair(...)` also emits intrinsic builder metadata for monodromy rows

## Effect on 159
- `L1/L2/L3` stop being coarse-only
- `L4/L5/L6` remain exact
- all six ordinary target families are now exact under one semantic dispatch rule

## Effect on 194 control
`194.1.12.16` grouped line families have `source_mult != 1`, so they do not enter the new exact dispatch. Control-group BS stays at single=13, double=10.
