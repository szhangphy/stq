# Geometry Audit

## swyckoff_k.py real input

- CLI: `python swyckoff_k.py --irssg-ssgnum 10.4.1.31 --kspace --fast`
- Module entry: `swyckoff_k.compute_wyckoff_output('10.4.1.31', kspace=True, fast=True)`
- The required group identifier is the full `irssg` `ssgNum` string such as `10.4.1.31`; short forms like `10` are not accepted.

## swyckoff_k.py real output

- `compute_wyckoff_output(...)` returns `(wyckoff, coord_key)`.
- `wyckoff` is a list of dict entries containing at least `letter`, `mult`, `dim`, `rep`, `basis_vecs`, `x0`, `representative_coordinate`, and `orbit`.
- The raw entries also carry spin/moment/site-symmetry display fields. Those are not needed for this pure-geometry task.
- Parameter ranges are **not** emitted by `swyckoff_k.py`; this wrapper infers a half-interval fundamental domain from the explicit `k -> -k` orbit pairing in the chosen demo group.

## Demo group

- Selected group: `10.4.1.31`.
- Reason: Smallest inspected k-space group with points, lines, and planes whose affine data stays clean.
- This group currently returns `8` points, `4` lines, `2` planes, and one ignored generic 3D manifold.

## Removed as unnecessary for pure geometry

- Added `compact_geometry_entries(...)` and `build_geometry_json_payload(...)` to `swyckoff_k.py`.
- The geometry wrapper drops `moment_*`, `orbit_with_moments`, `site_symmetry*`, `spin_matrix`, `time_reversal`, and related magnetic-display fields.
- The enumeration core is intentionally unchanged; only a geometry-only projection helper was added.

## Wrapper layer

- `kgeometry_single.py` calls `compute_wyckoff_output(...)`, keeps only dimensions `0/1/2`, normalizes them, infers half-interval parameter ranges, derives line endpoints and plane boundary candidates, then exports JSON/Markdown.
- `demo_single_group.py` runs the wrapper for one group and prints the requested summary.

## Boundary interpretation

- The listed line objects are treated as `separately listed special 1D manifold` entries because they are present in `swyckoff_k.py` output as dimension-1 items.
- The plane boundary candidates are treated as `geometric boundary line` objects first. They are only promoted to `line_plane` edges when their full 1D orbit matches an existing listed line manifold.
- For `10.4.1.31`, the eight plane boundary candidates do **not** match any listed line orbit. Recomputed stabilizers alone do not separate them from the listed lines, but `closure_under_stabilizer` does: each boundary candidate closes back to the two listed plane manifolds `S1` and `S2`, not to an independent 1D orbit.
- Therefore `line_plane` being empty for this group is expected and is not treated as a bug.

## 20+ group comparison

- Compared `build_wyckoff_table_string(..., kspace=True, fast=True)` and `build_compact_json_payload(..., kspace=True, fast=True)` before/after the helper addition.
- Tested 22 representative groups: `1.8.1.3`, `2.6.2.1`, `3.6.1.7`, `4.9.1.1`, `5.8.2.1`, `6.6.1.7`, `7.6.1.4`, `8.6.2.19`, `9.10.2.3`, `10.4.1.31`, `11.5.4.7`, `12.4.1.17`, `13.4.1.1`, `14.6.4.13`, `15.6.2.11`, `16.4.2.77`, `17.4.4.21`, `18.6.4.1`, `19.5.2.1`, `20.6.4.13`, `21.4.2.14`, `22.8.2.13`.
- Result: all 22 groups matched byte-for-byte on both outputs.
