# SG194 Double AI Patch Before/After V2

## Corrected Metric

- generator-span verdict uses column-space comparison on the transposed matrices in the common generator-label ambient
- row-space helper is retained only for row-content diagnostics and is not used for the patch verdict

## Global Comparison

- old current / patched current / external ranks:
  `12 / 12 / 10`
- old union / patched union:
  `21 / 21`
- old intersection / patched intersection:
  `1 / 1`

## Problem-Sector Comparison

- labels: `['b:E1', 'b:E2', 'b:E3', 'c:E1', 'c:E2', 'c:E3', 'd:E1', 'd:E2', 'd:E3', 'h:E']`
- old current / patched current / external ranks:
  `6 / 6 / 6`
- old union / patched union:
  `8 / 6`
- old intersection / patched intersection:
  `4 / 6`

## Delta Membership Re-check

- `delta_c1_minus_b1`:
  legacy current contains = `True`,
  patched current contains = `True`,
  disappeared = `False`
- `delta_d1_minus_b1`:
  legacy current contains = `True`,
  patched current contains = `True`,
  disappeared = `False`

## Updated Verdict

- patch shrinks global mismatch: `False`
- patch shrinks trusted problem-sector mismatch: `True`
- next step is BS-only comparison: `False`
