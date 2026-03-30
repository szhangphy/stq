# Double-Group Point-Like Local-Corep Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Group type only: `2`.
- This round does not revisit the settled single-group line or the already-completed double-group k-space backbone.
- This round only builds the point-like double local-corep builder on families `a, b, c, d, e, f, g, h` and the first point-like double AI prototype that those families generate.

## Known Premise

- The single-group line is already closed for the same group.
- The minimal double-group prototype is already established.
- The full double-group k-space backbone is already established, including `BS_double` with rank 8.
- The bridge `r_conv = P r_mag`, `P = diag(1,2,2)` is already trusted and reused here.

## Processing Order

- Actual processing order: `c, f, d, e, g, h, b, a`.
- Reason: start from the already-validated minimal family `c`, extend immediately to its pure-unitary partner `f`, then handle the antiunitary families in same-site-symmetry pairs so the case-c builder is debugged once per stabilizer type.

## Method Summary

- Pure-unitary point families `c,f` are handled by explicit projective character enumeration on the unitary `2/m` stabilizer using `factor_su2`.
- Antiunitary point families `a,b,d,e,g,h` are handled by an explicit magnetic-corep builder: first enumerate the paired projective unitary irreps with generator values `+i` and `-i`, then combine them into one 2D Wigner-case-c corep.
- Atomic induction reuses the audited bridge and the existing full `BS_double` unknown ordering.
- The induction route still starts from the local double/projective character, then applies the Bloch phase through the audited `linear_character` reconstruction on the k-space side.

## Family-By-Family Census

### Family `c`

- Representative coordinate: `0, 0, 1/4`.
- Multiplicity: `4`.
- Site symmetry: `2/m`.
- Stabilizer size / unitary / antiunitary: `4` / `4` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Already validated as the minimal double-group seed family; pure unitary `2/m` and the safest place to anchor the reusable point-like builder.
- Unitary subgroup summary: `2/m`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `c_double_g_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `c_double_u_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `c_double_g_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `c_double_u_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.

### Family `f`

- Representative coordinate: `1/2, 0, 1/4`.
- Multiplicity: `4`.
- Site symmetry: `2/m`.
- Stabilizer size / unitary / antiunitary: `4` / `4` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Same pure-unitary `2/m` site symmetry as `c`, so it is the cleanest first extension once the seed builder is stable.
- Unitary subgroup summary: `2/m`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `f_double_g_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `f_double_u_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `f_double_g_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.
  - `f_double_u_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the unitary `2/m` stabilizer.

### Family `d`

- Representative coordinate: `0, 1/4, 0`.
- Multiplicity: `4`.
- Site symmetry: `2'/m'`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: First antiunitary pair after `c,f`; it shares the same `2'/m'` site symmetry as `e`, so the case-c builder can be debugged on one stabilizer type before cloning it to its partner.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `d_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

### Family `e`

- Representative coordinate: `1/2, 1/4, 0`.
- Multiplicity: `4`.
- Site symmetry: `2'/m'`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Same antiunitary site-symmetry type as `d`; processed immediately after it to reuse the exact same case-c construction.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `e_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

### Family `g`

- Representative coordinate: `0, 1/4, 1/4`.
- Multiplicity: `4`.
- Site symmetry: `2/m'`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Second antiunitary pair; shares the same `2/m'` site symmetry as `h`, so it is handled as the next reusable case-c block.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `g_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

### Family `h`

- Representative coordinate: `1/2, 1/4, 1/4`.
- Multiplicity: `4`.
- Site symmetry: `2/m'`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Same antiunitary site-symmetry type as `g`; kept adjacent to avoid switching stabilizer logic mid-stream.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `h_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

### Family `b`

- Representative coordinate: `1/2, 0, 0`.
- Multiplicity: `4`.
- Site symmetry: `2'/m`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Final antiunitary pair; shares the same `2'/m` site symmetry as `a` and is handled only after the two earlier case-c patterns are stable.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `b_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

### Family `a`

- Representative coordinate: `0, 0, 0`.
- Multiplicity: `4`.
- Site symmetry: `2'/m`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Processing reason: Same antiunitary site-symmetry type as `b`; kept last only because the builder is already trusted by then, not because the family is intrinsically harder.
- Unitary subgroup summary: `projective order-2 unitary subgroup`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `a_double_case_c_pair`: dim `2`, type `magnetic_local_corep`, Wigner case `c`, truly antiunitary `True`, depends on `factor_su2` `True`. Source: Wigner case-c pairing of the two complex-conjugate projective unitary irreps on the order-2 unitary subgroup.

## Outcome

- Successful families: `c, f, d, e, g, h, b, a`.
- Failed families: `none`.
- Successful local object count: `14`.
- Raw point-like candidate count: `14`.
- Distinct induced 31-dimensional vectors: `9`.
- `rank_Z(AI_double_pointlike_v1) = 6` while `rank_Z(BS_double) = 8`.
- Rank-growing example generators: `c_double_g_plus_i, c_double_u_plus_i, c_double_g_minus_i, c_double_u_minus_i, f_double_g_plus_i, f_double_u_plus_i`.
- All six antiunitary point-like families fall into Wigner case c in the double group, not the single-group case-a pattern.
- The point-like builder is therefore now stable, but it only covers 6 of the 8 BS directions. The residual gap is no longer in the point-like sector.
