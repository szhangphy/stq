# 194.1.1.1 Single-Group Portability Pilot

## Outcome

- Real-space geometry, k-space manifolds, little-group capture, raw line compatibility, plane augmentation, and the BS kernel construction all run on 194.1.1.1.
- The current pilot had to add `0` synthetic 0D boundary points because the raw k-geometry contains `0` line endpoints that are not emitted by `swyckoff_k.py` as separately listed special points.
- The internal honest full-span 8-path shell is retained for diagnostics only; the published BS object is the publication-level `C_pub` quotient built from publication path classes.
- Row-language full-span against the full candidate path language: `True`.
- Bilbao-equivalent final-object pass: `True`.

## Direct Reuse Successes

- `swyckoff_r.py` / `swyckoff_k.py` standardized geometry loading is reused directly.
- `SSGReps.load_little_group(...)` is reused directly on all special points, lines, and planes.
- The operation bridge `r_conv = P r_mag` logic and lattice-fix test are reused directly.
- The restriction/decomposition workflow still uses `character` / `linear_character` / `rep_degree` and subgroup matching, without relying on `rep_matrix`.

## Modules That Needed Change

- The line-compatibility layer from 10.4.1.31 assumed every special line endpoint landed on a separately listed 0D point. That assumption fails on 194.1.1.1.
- The portability pilot therefore augments the boundary-point set with explicit synthetic 0D endpoints before assembling the global compatibility matrix.
- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are cleared by the manifold character-field conversion patch. Current P4 verdict: proved_bug. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24].

## Status Summary

- Publication compatibility-matrix shape/rank/nullity: `[29, 34]`, `24`, `10`.
- Publication BS rank (kernel rank of C_pub): `10`.
- Internal vs publication path counts: `8` / `7`.
- Publication Bilbao-style check: point ids match = `True`, path count match = `True`, exact path-pair match = `True`.
- Trivial-family AI seed count/rank: `12` / `12`.
- Trivial-family compatibility-zero count: `4` / `12`.
- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `45` / `0` / `11`.
- Verified AI rank / missing rank relative to published BS: `5` / `5`.
- AI obstruction classification counts: `{'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}`.
- Publication residual path histogram: `{'PPATH06': 68}`.
- PPATH06 residual-support rows: `[22, 23, 24]`.
- P4 current verdict: `proved_bug`.
- point_row_translation legality: `removed`.
- AI residual pattern changed vs previous branch: `True`.
- AI completeness: blocked. Reason: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are cleared by the manifold character-field conversion patch. Current P4 verdict: proved_bug. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24].
- Quotient / indicator extraction: blocked until a complete AI lattice exists.
