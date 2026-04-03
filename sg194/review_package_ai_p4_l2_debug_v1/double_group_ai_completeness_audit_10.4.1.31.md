# Double-Group AI Completeness Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Group type only: `2`.
- The settled single-group line is not revisited here.
- The settled double-group k-space backbone, point-like census, and parametric census are treated as trusted background.
- This round only asks whether the current `AI_double_v2` is already the complete `AI_double`, and only if yes does it extract `BS_double / AI_double`.

## Known Premise

- The single-group line for the same group is already closed.
- The full double-group k-space backbone is already established.
- Point-like and parametric families together already cover all 15 families `a..o`.
- The current problem is therefore no longer missing-family discovery, but completeness and quotient interpretation.

## Family-Level Completeness

### Family `a`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2'/m`.
- Included double local objects: `a_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - The unitary subgroup is projective order-2 with exactly two conjugate unitary irreps `+i/-i`.
  - The antiunitary generator fixes the unitary generator and squares to the identity, so Wigner extension pairs those conjugate unitary irreps into one irreducible case-c magnetic corep.
  - No additional case-a or higher-dimensional magnetic corep exists because there is no extra unitary irrep left to extend.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `b`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2'/m`.
- Included double local objects: `b_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - Same `2'/m` antiunitary stabilizer as family `a`.
  - The only unitary projective irreps are the conjugate pair `+i/-i`.
  - Therefore the complete double local set is a single Wigner-case-c pair, already present in the census.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `c`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2/m`.
- Included double local objects: `c_double_g_plus_i, c_double_u_plus_i, c_double_g_minus_i, c_double_u_minus_i`.
- Completeness status: `complete`.
- Completeness basis:
  - Pure-unitary family with full unitary stabilizer `2/m`.
  - The projective character is fixed by two choices: C2 eigenvalue `+i/-i` and inversion parity `g/u`.
  - Those two binary choices give exactly four one-dimensional double-valued projective irreps and the current census contains all four.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `d`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2'/m'`.
- Included double local objects: `d_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - The unitary subgroup is projective order-2 with generator square factor `-1`, so its only one-dimensional projective irreps are `+i/-i`.
  - The antiunitary action fixes that unitary generator, so the conjugate pair must combine into one irreducible case-c magnetic corep.
  - That single case-c pair is therefore the full local-object set.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `e`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2'/m'`.
- Included double local objects: `e_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - Same `2'/m'` antiunitary stabilizer as family `d`.
  - The projective unitary subgroup again has only the conjugate pair `+i/-i`.
  - Hence the census is complete once the single case-c magnetic corep is present, which it is.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `f`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2/m`.
- Included double local objects: `f_double_g_plus_i, f_double_u_plus_i, f_double_g_minus_i, f_double_u_minus_i`.
- Completeness status: `complete`.
- Completeness basis:
  - Same pure-unitary `2/m` site symmetry as family `c`.
  - Projective completeness is fixed by the same `C2=+i/-i` and inversion `g/u` choices.
  - Hence the complete local set has exactly four one-dimensional projective irreps, all present in the census.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `g`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2/m'`.
- Included double local objects: `g_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - The unitary subgroup is projective order-2 with only the conjugate `+i/-i` pair.
  - The antiunitary generator fixes the unitary generator, so Wigner completeness again produces a single irreducible case-c corep.
  - No further double local object is available beyond that pair.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `h`

- Class: `point-like`.
- Multiplicity: `4`.
- Site symmetry: `2/m'`.
- Included double local objects: `h_double_case_c_pair`.
- Completeness status: `complete`.
- Completeness basis:
  - Same `2/m'` antiunitary stabilizer as family `g`.
  - The only unitary projective irreps are the conjugate pair `+i/-i`.
  - That pair gives exactly one case-c magnetic corep, which is already present.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `i`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `2'`.
- Included double local objects: `i_double_A_eta_plus, i_double_A_eta_minus`.
- Completeness status: `complete`.
- Completeness basis:
  - The unitary subgroup is trivial, so there is only one unitary irrep to extend.
  - The antiunitary generator squares to the identity with double-group factor `+1`, so Wigner completeness gives the eta=`+/-` case-a pair.
  - There is no room for an additional higher-dimensional or projective magnetic corep in this stabilizer.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `j`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `2'`.
- Included double local objects: `j_double_A_eta_plus, j_double_A_eta_minus`.
- Completeness status: `complete`.
- Completeness basis:
  - Same `2'` antiunitary stabilizer as family `i`.
  - With trivial unitary subgroup and antiunitary square `+1`, the full local set is exactly the eta=`+/-` case-a pair.
  - The census already contains that full pair.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `k`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `2`.
- Included double local objects: `k_double_plus_i, k_double_minus_i`.
- Completeness status: `complete`.
- Completeness basis:
  - The pure-unitary stabilizer is order 2 with generator square factor `-1`.
  - Hence the complete one-dimensional projective spectrum is just the two generator eigenvalues `+i/-i`.
  - Both are present in the current census, so the family is complete.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `l`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `2`.
- Included double local objects: `l_double_plus_i, l_double_minus_i`.
- Completeness status: `complete`.
- Completeness basis:
  - Same order-2 pure-unitary stabilizer as family `k`.
  - The only projective one-dimensional possibilities are again `+i/-i`.
  - Both are included, so the family-level local-object census is complete.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `m`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `m`.
- Included double local objects: `m_double_plus_i, m_double_minus_i`.
- Completeness status: `complete`.
- Completeness basis:
  - The pure-unitary stabilizer is order 2 with double-group square factor `-1` on its generator.
  - A one-dimensional projective character must satisfy `chi(g)^2 = -1`, so the only possibilities are `+i` and `-i`.
  - Those two characters exhaust the projective local-irrep set.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `n`

- Class: `parametric`.
- Multiplicity: `8`.
- Site symmetry: `m'`.
- Included double local objects: `n_double_A_eta_plus, n_double_A_eta_minus`.
- Completeness status: `complete`.
- Completeness basis:
  - The unitary subgroup is again trivial.
  - The antiunitary generator squares to the identity with double-group factor `+1`, so the complete magnetic extension is the eta=`+/-` case-a pair.
  - No missing higher-dimensional local corep remains after that pair is included.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

### Family `o`

- Class: `parametric`.
- Multiplicity: `16`.
- Site symmetry: `1`.
- Included double local objects: `o_double_A`.
- Completeness status: `complete`.
- Completeness basis:
  - The site stabilizer is trivial.
  - A trivial stabilizer has exactly one one-dimensional projective local irrep.
  - The current singleton census is therefore complete.
- Notes: Current local-object census matches the mathematically expected double-group object set for this family.

## Completeness Arguments By Family Type

- Antiunitary point-like families `a, b, d, e, g, h` are complete because each has exactly one conjugate pair of unitary projective irreps `+i/-i`, and Wigner extension forces that pair into one irreducible case-c magnetic corep.
- Antiunitary parametric families `n, i, j` are complete because their unitary subgroup is trivial and the antiunitary generator squares to `+1`, leaving only the eta=`+/-` case-a pair.
- Pure-unitary parametric families `o, m, k, l` are complete because the trivial stabilizer gives one projective irrep (`o`) and the order-2 stabilizers give only the two projective eigenvalues `+i/-i` (`m,k,l`).
- Pure-unitary point-like families `c,f` are complete because the `2/m` projective character is fully determined by the binary choices `C2=+i/-i` and inversion parity `g/u`, giving exactly four local projective irreps.

## AI Completeness Conclusion

- All families audited: `True`.
- Complete families: `a, b, c, d, e, f, g, h, i, j, k, l, m, n, o`.
- Incomplete families: `none`.
- `AI_double_v2` can be treated as complete `AI_double`: `True`.

## Scope Boundary

- This conclusion is only for group `10.4.1.31`, `groupType=2`, the current with-planes formalism, and the current BS basis / unknown ordering.
- It is not a statement about other groups, not a reusable database-wide builder proof, and not the end of the overall project.

## Quotient Outcome

- `rank(BS_double) = 8`.
- `rank(AI_double) = 6`.
- Smith diagonal of `AI_double` inside the current `BS_double` basis: `[1, 1, 2, 2, 2, 2]`.
- Therefore `BS_double / AI_double = Z^2 x Z2 x Z2 x Z2 x Z2`.
- This quotient contains both a free part and a finite torsion part, so it is not a purely finite indicator group.
- Explicit quotient generators are written to `double_group_indicator_generators_10.4.1.31.json`.
