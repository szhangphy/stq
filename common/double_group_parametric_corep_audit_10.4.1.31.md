# Double-Group Parametric Local-Corep Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Group type only: `2`.
- This round does not revisit the settled single-group line, the double-group backbone, or the finished point-like double AI stage.
- This round only handles the parametric families `o,m,k,l,n,i,j`.

## Known Premise

- The single-group line for the same group is already closed.
- The full double-group k-space backbone is already established, with `rank(BS_double)=8`.
- The point-like double AI prototype already exists and spans rank 6.
- The bridge `r_conv = P r_mag`, `P = diag(1,2,2)` is already trusted and reused here.

## Processing Order

- Actual processing order: `o, m, k, l, i, j, n`.
- Stage 1 is pure-unitary parametric families `o,m,k,l`.
- Stage 2 is antiunitary parametric families `i,j,n`.
- Reason: start from the generic identity-stabilizer family `o`, then add the two pure-unitary order-2 stabilizer types, and only then switch to the antiunitary case-a builder with the simplest one-parameter `2'` families before the two-parameter `m'` family.

## Method Summary

- Parametric families do not reuse the point-like x0-orbit logic. Every induction is forced to start from the generic sample point orbit.
- `o,m,k,l` use a pure-unitary double local builder: either the unique trivial projective irrep (`o`) or the two `+i/-i` projective irreps on an audited order-2 stabilizer (`m,k,l`).
- `n,i,j` use a magnetic local-corep builder with trivial unitary subgroup: the antiunitary generator squares to the identity with double-group factor `+1`, so the local objects are the Wigner-case-a eta pair.
- Atomic induction still uses the audited route: local double/projective character first, then the Bloch factor through the existing double-group induction routine.

## Family-By-Family Census

### Family `o`

- Representative parametric form: `x, y, z`.
- Dimension: `3`.
- Generic sample point (magnetic): `['1/5', '2/7', '3/11']`.
- Multiplicity: `16`.
- Site symmetry: `1`.
- Stabilizer size / unitary / antiunitary: `1` / `1` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `16` / `16`.
- Processing reason: Start from the fully generic family because its stabilizer is just the identity; this is the cleanest way to test the sample-point orbit branch before any nontrivial projective relation is introduced.
- Unitary subgroup summary: `1`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `o_double_A`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `False`. Source: Unique one-dimensional projective irrep of the trivial unitary stabilizer.

### Family `m`

- Representative parametric form: `x, 0, z`.
- Dimension: `2`.
- Generic sample point (magnetic): `['1/5', '0', '2/7']`.
- Multiplicity: `8`.
- Site symmetry: `m`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: Second because it is still pure unitary, but now the order-2 mirror generator forces a real projective check through `factor_su2(7,7)=-1`.
- Unitary subgroup summary: `projective m`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `m_double_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.
  - `m_double_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.

### Family `k`

- Representative parametric form: `0, y, 1/4`.
- Dimension: `1`.
- Generic sample point (magnetic): `['0', '1/5', '1/4']`.
- Multiplicity: `8`.
- Site symmetry: `2`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: Then move to the one-parameter pure-unitary `2` family, which uses the same order-2 projective logic as `m` but on a different generator and orbit geometry.
- Unitary subgroup summary: `projective 2`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `k_double_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.
  - `k_double_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.

### Family `l`

- Representative parametric form: `1/2, y, 1/4`.
- Dimension: `1`.
- Generic sample point (magnetic): `['1/2', '1/5', '1/4']`.
- Multiplicity: `8`.
- Site symmetry: `2`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: Processed immediately after `k` because it is its translated partner with the same projective order-2 stabilizer.
- Unitary subgroup summary: `projective 2`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `l_double_plus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.
  - `l_double_minus_i`: dim `1`, type `projective_local_irrep`, Wigner case `None`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Double-valued one-dimensional projective irrep on the order-2 pure-unitary stabilizer.

### Family `i`

- Representative parametric form: `0, y, 0`.
- Dimension: `1`.
- Generic sample point (magnetic): `['0', '1/5', '0']`.
- Multiplicity: `8`.
- Site symmetry: `2'`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: The antiunitary stage starts with the simplest one-parameter `2'` family, whose unitary subgroup is trivial and therefore gives the cleanest double case-a extension test.
- Unitary subgroup summary: `1`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `i_double_A_eta_plus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.
  - `i_double_A_eta_minus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.

### Family `j`

- Representative parametric form: `1/2, y, 0`.
- Dimension: `1`.
- Generic sample point (magnetic): `['1/2', '1/5', '0']`.
- Multiplicity: `8`.
- Site symmetry: `2'`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: Processed next because it is the translated partner of `i` and should reuse the exact same case-a builder if the sample-point orbit logic is correct.
- Unitary subgroup summary: `1`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `j_double_A_eta_plus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.
  - `j_double_A_eta_minus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.

### Family `n`

- Representative parametric form: `x, 1/4, z`.
- Dimension: `2`.
- Generic sample point (magnetic): `['1/5', '1/4', '2/7']`.
- Multiplicity: `8`.
- Site symmetry: `m'`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- `swyckoff_r.py` `stab` field matches direct recomputation: `True`.
- Usable as double local-corep input: `True`.
- Sample-point orbit required: `True`.
- x0 orbit size / sample-point orbit size / multiplicity: `4` / `8` / `8`.
- Processing reason: Kept last because it is the two-parameter antiunitary `m'` family; the corep classification is still case a, but its generic sample-point orbit is the largest antiunitary parametric test in scope.
- Unitary subgroup summary: `1`.
- Full local-object set built: `True`.
- Constructed local objects:
  - `n_double_A_eta_plus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.
  - `n_double_A_eta_minus`: dim `1`, type `magnetic_local_corep`, Wigner case `a`, truly antiunitary `False`, depends on `factor_su2` `True`. Source: Wigner-case-a direct extension of the unique trivial-unitary-subgroup irrep.

## AI Outcome

- Successful families: `o, m, k, l, i, j, n`.
- Failed families: `none`.
- Successful local object count: `13`.
- New parametric raw candidate count: `13`.
- Distinct new induced 31-dimensional vectors: `8`.
- `rank_Z(AI_double_v2) = 6` while `rank_Z(BS_double) = 8`.
- Rank increase over point-like v1: `0`.
- Same lattice as old point-like v1: `True`.
- The antiunitary parametric eta pairs do not produce new unitary-k-space vectors: all six `n/i/j` eta extensions collapse to the same BS-coordinate direction already seen in the point-like antiunitary sector.
- The pure-unitary parametric families do add new raw generators, but those generators are still integer combinations of the old point-like AI basis, so the total rank remains 6.
- Therefore this stage succeeds as a builder / induction audit, but it does not close the BS gap. The residual rank-2 gap is now an explicit witness, not a vague missing-family statement.
