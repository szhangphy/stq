# SG194 Double AI Patch Before/After

## Global 33-Column Comparison

- old current rank / external rank: `12 / 10`
- new current rank / external rank: `12 / 10`
- old global union / intersection: `21 / 1`
- new global union / intersection: `21 / 1`

## Trusted Problem-Sector Comparison

- old problem-sector current / external / union / intersection:
  `6 / 6 / 8 / 4`
- new problem-sector current / external / union / intersection:
  `6 / 6 / 6 / 6`

## Delta Status

- `delta_c1_minus_b1` disappeared: `True`
- `delta_d1_minus_b1` disappeared: `True`

## Interpretation

- The patched source-level builder kills the explicit trusted `2b/2c/2d/6h` problem-sector mismatch exactly: union rank drops from `8` to `6`.
- The patched current rank in the full current-HSP `33`-column comparison remains `12`, so the hoped-for direct `12 -> 10` drop is **not** achieved at this stage.
- Therefore the true outcome is: the localized SG194 double AI bug source has been patched at the generator-construction layer, but the broader all-sector current/external row-language gap is not yet fully collapsed.
