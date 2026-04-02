# 194.1.1.1 Single-Group Portability Pilot

## Outcome

- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.
- The current pilot had to add `0` synthetic 0D boundary points because the raw k-geometry contains `0` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.
- The final published single-group BS object is now the automatically reduced point/path shell; the raw with-planes 42-shell remains diagnostic only.
- Strong BS equivalence against the full candidate path language: `True`.

## Direct Reuse Successes

- `swyckoff_r.py` / `swyckoff_k.py` standardized geometry loading is reused directly.
- `SSGReps.load_little_group(...)` is reused directly on all special points, lines, and planes.
- The operation bridge `r_conv = P r_mag` logic and lattice-fix test are reused directly.
- The restriction/decomposition workflow still uses `character` / `linear_character` / `rep_degree` and subgroup matching, without relying on `rep_matrix`.

## Modules That Needed Change

- The line-compatibility layer from 10.4.1.31 assumed every special line endpoint landed on a separately listed 0D point. That assumption fails on 194.1.1.1.
- The portability pilot therefore augments the boundary-point set with explicit synthetic 0D endpoints before assembling the global compatibility matrix.
- The AI side is only partial: the current pilot induces the trivial local representation on every real-space family, but it does not yet enumerate the full local-irrep library for the non-abelian SG 194 site symmetries.

## Status Summary

- BS matrix shape/rank/nullity: `[29, 34]`, `23`, `11`.
- Final point/path shell sizes: `6` points / `7` paths.
- Bilbao-equivalent sanity check (diagnostic only): point ids match = `True`, path pair set match = `True`.
- Trivial-family AI seed count/rank: `12` / `12`.
- Trivial-family compatibility-zero count: `4` / `12`.
- point_row_translation legality: `removed`.
- AI completeness: blocked. Reason: Generic local-irrep library beyond the trivial rep is not implemented for the non-abelian SG 194 site symmetries, so AI completeness cannot be certified honestly.
- Quotient / indicator extraction: blocked until a complete AI lattice exists.
