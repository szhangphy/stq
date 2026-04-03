# 194.1.1.1 Single-Group Portability Pilot

## Outcome

- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.
- The current pilot had to add `0` synthetic 0D boundary points because the raw k-geometry contains `0` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.
- The final published single-group BS object is the automatically reduced point/path shell; the raw with-planes 42-shell remains diagnostic only.
- Row-language full-span against the full candidate path language: `True`.
- Bilbao-equivalent final-object pass: `False`.

## Direct Reuse Successes

- `swyckoff_r.py` / `swyckoff_k.py` standardized geometry loading is reused directly.
- `SSGReps.load_little_group(...)` is reused directly on all special points, lines, and planes.
- The operation bridge `r_conv = P r_mag` logic and lattice-fix test are reused directly.
- The restriction/decomposition workflow still uses `character` / `linear_character` / `rep_degree` and subgroup matching, without relying on `rep_matrix`.

## Modules That Needed Change

- The line-compatibility layer from 10.4.1.31 assumed every special line endpoint landed on a separately listed 0D point. That assumption fails on 194.1.1.1.
- The portability pilot therefore augments the boundary-point set with explicit synthetic 0D endpoints before assembling the global compatibility matrix.
- The non-abelian SG 194 local-irrep library now loads and is wired into the single-branch AI builder, but published-shell induction/completeness remains blocked beyond the trivial seed.

## Status Summary

- BS matrix shape/rank/nullity: `[33, 34]`, `24`, `10`.
- Final point/path shell sizes: `6` points / `8` paths.
- Bilbao-style diagnostic check: point ids match = `True`, path count match = `False`, exact path-pair match = `False`, unique path-pair match = `True`.
- Trivial-family AI seed count/rank: `12` / `12`.
- Trivial-family compatibility-zero count: `4` / `12`.
- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `45` / `0` / `11`.
- point_row_translation legality: `removed`.
- AI residual pattern changed vs previous branch: `False`.
- AI completeness: blocked. Reason: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published reduced shell.
- Quotient / indicator extraction: blocked until a complete AI lattice exists.
