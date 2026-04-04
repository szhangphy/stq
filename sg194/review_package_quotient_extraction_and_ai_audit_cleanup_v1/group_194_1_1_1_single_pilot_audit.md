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
- No active AI blocker; single-group quotient already extracted on the authoritative publication-shell AI lattice.

## Status Summary

- Publication compatibility-matrix shape/rank/nullity: `[29, 34]`, `24`, `10`.
- Publication BS rank (kernel rank of C_pub): `10`.
- Internal vs publication path counts: `8` / `7`.
- Publication Bilbao-style check: point ids match = `True`, path count match = `True`, exact path-pair match = `True`.
- Trivial-family AI seed count/rank: `12` / `12`.
- Trivial-family compatibility-zero count: `4` / `12`.
- Library-integrated single AI candidate count / failures / compatibility-zero candidates: `45` / `0` / `11`.
- Old verified AI rank / promoted increment / authoritative AI rank: `5` / `5` / `10`.
- AI obstruction classification counts: `{'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}`.
- Publication residual path histogram: `{'PPATH06': 68}`.
- PPATH06 residual-support rows: `[22, 23, 24]`.
- PPATH06 row semantics: `Publication rows 22/23/24 are the three phase-aware endpoint-class balance constraints on PPATH06. Each row is a pure pair-difference relation on P3 multiplicities, inherited directly from raw L2 through the internal FPATH07 shell without any new publication-only deformation.`.
- P4 current verdict: `setting_specific_fix_confirmed`.
- P4 theorem status: `not_global_not_basis_independent`.
- P4 setting-specific conversion validation scope / pass: `SG194_current_setting_only` / `True`.
- SG194-setting-specific linear->character consistency pass / theorem promoted: `True` / `False`.
- Residual-sector quotient-rank contribution / missing-rank-5 pivot ids: `5` / `['a_A1u', "b_A1''", "c_A1'", "d_A1'", 'g_Ag']`.
- Residual completion feasible / liftable direction ids / promoted authoritative generator ids: `True` / `['lifted_a_A1g_minus_a_A1u', 'lifted_b_A1_prime_plus_b_A1_doubleprime', 'lifted_b_E_prime_minus_2_c_A1_prime', 'lifted_b_E_prime_minus_2_d_A1_prime', 'lifted_a_A1g_minus_g_Ag']` / `['promoted_a_A1g_minus_a_A1u', 'promoted_b_A1_prime_plus_b_A1_doubleprime', 'promoted_b_E_prime_minus_2_c_A1_prime', 'promoted_b_E_prime_minus_2_d_A1_prime', 'promoted_a_A1g_minus_g_Ag']`.
- AI aligned with Bilbao / quotient stage allowed: `True` / `True`.
- Publication point-basis usage counts: `{'raw_capture_point_basis': 225, 'publication_collapsed_point_basis_fallback_raw': 34, 'publication_collapsed_point_basis': 11}`.
- Quotient group / invariants / SNF diagonal: `Z2` / `[2]` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`.
- point_row_translation legality: `removed`.
- AI residual pattern changed vs previous branch: `False`.
- AI completeness: ready. Reason: No active AI blocker; single-group quotient already extracted on the authoritative publication-shell AI lattice.
- Quotient / indicator extraction: success. Quotient group = `Z2`.
