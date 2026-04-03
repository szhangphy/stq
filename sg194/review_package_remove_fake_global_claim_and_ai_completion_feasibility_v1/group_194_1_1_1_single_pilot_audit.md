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
- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects are currently explicit compatibility-zero generators on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are removed in the current SG194/P-lattice setting by a conversion numerically consistent with the present capture conventions. Claim scope: For SG194 in the current P-lattice setting, the earlier P4 mismatch is removed by a conversion numerically consistent with the present capture conventions. This is not promoted to a basis-independent global theorem.. Current P4 verdict: setting_specific_fix_confirmed. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24]. The residual sector contributes quotient rank 5 after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank 5. Integer recombinations of the residual sector already lift the missing rank-5 directions to actual compatibility-zero vectors, but those recombined directions are not yet promoted into the authoritative publication-shell AI generator set.

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
- PPATH06 row semantics: `Publication rows 22/23/24 are the three phase-aware endpoint-class balance constraints on PPATH06. Each row is a pure pair-difference relation on P3 multiplicities, inherited directly from raw L2 through the internal FPATH07 shell without any new publication-only deformation.`.
- P4 current verdict: `setting_specific_fix_confirmed`.
- P4 theorem status: `not_global_not_basis_independent`.
- P4 setting-specific conversion validation scope / pass: `SG194_current_setting_only` / `True`.
- SG194-setting-specific linear->character consistency pass / theorem promoted: `True` / `False`.
- Residual-sector quotient-rank contribution / missing-rank-5 pivot ids: `5` / `['a_A1u', "b_A1''", "c_A1'", "d_A1'", 'g_Ag']`.
- Residual completion feasible / liftable direction ids: `True` / `['a_A1g', "b_A1'", "b_E'", "b_E'", 'a_A1g']`.
- point_row_translation legality: `removed`.
- AI residual pattern changed vs previous branch: `False`.
- AI completeness: blocked. Reason: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects are currently explicit compatibility-zero generators on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are removed in the current SG194/P-lattice setting by a conversion numerically consistent with the present capture conventions. Claim scope: For SG194 in the current P-lattice setting, the earlier P4 mismatch is removed by a conversion numerically consistent with the present capture conventions. This is not promoted to a basis-independent global theorem.. Current P4 verdict: setting_specific_fix_confirmed. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24]. The residual sector contributes quotient rank 5 after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank 5. Integer recombinations of the residual sector already lift the missing rank-5 directions to actual compatibility-zero vectors, but those recombined directions are not yet promoted into the authoritative publication-shell AI generator set.
- Quotient / indicator extraction: blocked until a complete AI lattice exists.
