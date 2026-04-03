# 194.1.1.1 Single-Group Portability Pilot

## Outcome

- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.
- The current pilot had to add `0` synthetic 0D boundary points because the raw k-geometry contains `0` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.
- The final published single-group BS object is the honest full-span augmented 8-path reduced shell; the raw with-planes 42-shell remains diagnostic only.
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
- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published full-span augmented 8-path shell. Classification counts across raw42 / 7-path skeleton / published 8-path shells: {'fails_on_raw42': 34, 'compatible_on_published8': 11}. 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.

## Status Summary

- BS matrix shape/rank/nullity: `[33, 34]`, `24`, `10`.
- Final point/path shell sizes: `6` points / `8` paths.
- Bilbao-style diagnostic check: point ids match = `True`, path count match = `False`, exact path-pair match = `False`, unique path-pair match = `True`.
- Trivial-family AI seed count/rank: `12` / `12`.
- Trivial-family compatibility-zero count: `4` / `12`.
- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `45` / `0` / `11`.
- AI obstruction classification counts: `{'fails_on_raw42': 34, 'compatible_on_published8': 11}`.
- Published residual path histogram: `{'FPATH07': 68}`.
- point_row_translation legality: `removed`.
- AI residual pattern changed vs previous branch: `False`.
- AI completeness: blocked. Reason: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published full-span augmented 8-path shell. Classification counts across raw42 / 7-path skeleton / published 8-path shells: {'fails_on_raw42': 34, 'compatible_on_published8': 11}. 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.
- Quotient / indicator extraction: blocked until a complete AI lattice exists.
