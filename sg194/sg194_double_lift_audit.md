# SG194 Double Lift Audit

## Why the transposed column-space proxy was still not enough

The v2 proxy proved that the patched current and external problem-sector matrices have the same row span in the common 10-generator domain. It did not produce an explicit map from the 34 current-HSP rows to the 56 external spinorial rows. Equal row spaces do not by themselves tell us how a concrete current ambient vector should be interpreted in the external row language.

## Trusted problem-sector inventory

- current generator indices: `[23, 24, 25, 26, 27, 28, 29, 30, 31, 32]`
- external generator indices: `[6, 7, 8, 9, 10, 11, 12, 13, 14, 25]`
- current row blocks used: `['P1', 'P2', 'P3', 'P5', 'P6', 'B1']`
- external row blocks used: `['A', 'Γ', 'H', 'K', 'L', 'M']`

## Explicit row-basis lift

- rational lift exists: `True`
- integer lift exists: `False`
- common denominator lcm: `2`
- exact equality `L * C = E`: `True`

## Integer obstruction

- Smith diagonal: `[1, 1, 1, 2, 2, 2]`
- obstruction basis rank mod 2: `3`
- meaning: the trusted-sector row-space match is exact over `Q`, but an all-integer ambient lift is blocked by three parity directions in the external rows.

## External verdict for the delta directions

- `delta_c1_minus_b1`: zero = `False`, status = `nonzero_external_span_direction_not_residual_mismatch`
- `delta_d1_minus_b1`: zero = `False`, status = `nonzero_external_span_direction_not_residual_mismatch`

Both deltas remain nonzero vectors, but after lifting they live exactly inside the external generator span, so they are not residual mismatches.

## Updated patch verdict

- trusted-sector patch success: `True`
- trusted-sector ready for BS-only: `True`
- full global BS-only certified in this round: `False`
