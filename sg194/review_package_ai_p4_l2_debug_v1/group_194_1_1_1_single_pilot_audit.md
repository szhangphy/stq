# 194.1.1.1 Single-Group Portability Pilot

## Outcome

- The publication-level C_pub shell remains fixed and Bilbao-equivalent.
- Publication shell path count: `7`.
- Publication BS matrix shape/rank/nullity: `[29, 34]` / `24` / `10`.
- AI zero-subset rank: `5` with zero generators `['a_Eg', 'a_Eu', 'e_A1', 'e_A2', 'e_E', 'f_A1', 'f_A2', 'f_E', "j_A'", "j_A''", 'l_A']`.
- P4 induction failure count/families: `12` / `['c', 'd']`.
- Dominant publication residual path/rows: `PPATH06` / `[22, 23, 24]`.

## Current Blocker

- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 33 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 22, 'compatible_on_publication_shell': 11, 'induction_failure_on_raw42': 12}. 22 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 48}. The remaining induction failures are concentrated on manifold P4 across families ['c', 'd'] (count=12). Nonzero residuals on the publication shell are concentrated on PPATH06 rows [19, 20, 21, 22, 23, 24].
