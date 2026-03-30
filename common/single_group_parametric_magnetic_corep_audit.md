# Single-Group Parametric Magnetic Corep Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- This round only handles the parametric antiunitary families `n, i, j`.
- The trusted k-space side, plane formalism, bridge, unitary-only AI, and point-like magnetic-corep results are reused as fixed input.

## Processing Order

1. `i`: Simplest one-parameter antiunitary family: the stabilizer is just {1, 2'} with trivial unitary subgroup, and the sample-point orbit issue is easiest to audit on the y line first.
2. `n`: Second priority because it probes the distinct m' plane family and the two-parameter sample-point orbit, while still having the same trivial unitary subgroup logic.
3. `j`: Last because it shares the same 2' stabilizer and one-parameter orbit logic as i and mainly checks the translated partner after the i builder is stable.

## Sample-Point Orbit Rule

- The old x0-orbit logic cannot be used for `n, i, j` because each symbolic x0 anchor lies on a more special family.
- `i`: x0 orbit size `4` vs sample-point orbit size `8` vs multiplicity `8`; x0 collapses to family `a`.
- `n`: x0 orbit size `4` vs sample-point orbit size `8` vs multiplicity `8`; x0 collapses to family `d`.
- `j`: x0 orbit size `4` vs sample-point orbit size `8` vs multiplicity `8`; x0 collapses to family `b`.
- Therefore the induction step must use the generic sample-point orbit, exactly as in the earlier unitary parameter-family audit.

## Toolchain Feasibility

- `swyckoff_r.py` plus the audited bridge are sufficient to recompute the real-space sample-point stabilizers and generic sample-point orbits for all three target families.
- `SSGReps` still has no direct local-magnetic-corep entrypoint for real-space site stabilizers, so this stage uses a dedicated single-group case-a builder again.
- The classification is simpler than the point-like stage because the unitary subgroup is trivial for all three families.

## Family-By-Family Audit

### Family `i`

- Representative coordinate / parametric form: `0, y, 0`.
- Dimension / multiplicity: `1` / `8`.
- Generic sample point (magnetic): `0, 1/5, 0`.
- Site symmetry: `2'`.
- Site-symmetry custom summary: `m'[x]`.
- Spatial site-symmetry custom summary: `2'[y]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Recomputed stabilizer matches `single_group_site_symmetry_check.json`: `True`.
- Usable as magnetic local corep input: `True`.
- Unitary subgroup: `C1` (identity only).
- Antiunitary generator square: raw op `0`.
- Wigner case used: `a`.
- Dedicated single-group builder sufficient: `True`.
- Full magnetic local corep set successfully built: `True`.
- Constructed magnetic local coreps:
  - `i_A_eta_plus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `+1`, truly antiunitary `False`.
  - `i_A_eta_minus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `-1`, truly antiunitary `False`.

### Family `n`

- Representative coordinate / parametric form: `x, 1/4, z`.
- Dimension / multiplicity: `2` / `8`.
- Generic sample point (magnetic): `1/5, 1/4, 2/7`.
- Site symmetry: `m'`.
- Site-symmetry custom summary: `m'[y]`.
- Spatial site-symmetry custom summary: `m'[y]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Recomputed stabilizer matches `single_group_site_symmetry_check.json`: `True`.
- Usable as magnetic local corep input: `True`.
- Unitary subgroup: `C1` (identity only).
- Antiunitary generator square: raw op `0`.
- Wigner case used: `a`.
- Dedicated single-group builder sufficient: `True`.
- Full magnetic local corep set successfully built: `True`.
- Constructed magnetic local coreps:
  - `n_A_eta_plus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `+1`, truly antiunitary `False`.
  - `n_A_eta_minus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `-1`, truly antiunitary `False`.

### Family `j`

- Representative coordinate / parametric form: `1/2, y, 0`.
- Dimension / multiplicity: `1` / `8`.
- Generic sample point (magnetic): `1/2, 1/5, 0`.
- Site symmetry: `2'`.
- Site-symmetry custom summary: `m'[x]`.
- Spatial site-symmetry custom summary: `2'[y]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Recomputed stabilizer matches `single_group_site_symmetry_check.json`: `True`.
- Usable as magnetic local corep input: `True`.
- Unitary subgroup: `C1` (identity only).
- Antiunitary generator square: raw op `0`.
- Wigner case used: `a`.
- Dedicated single-group builder sufficient: `True`.
- Full magnetic local corep set successfully built: `True`.
- Constructed magnetic local coreps:
  - `j_A_eta_plus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `+1`, truly antiunitary `False`.
  - `j_A_eta_minus`: dim `1`, source unitary irrep `A`, Wigner case `a`, eta `-1`, truly antiunitary `False`.

## Outcome

- Successful families: `i, n, j`.
- Failed families: `none`.
- Successful local corep count: `6`.
- New raw parametric magnetic-corep candidate count: `6`.
- Distinct induced unitary vectors among those new candidates: `1`.
- `rank_Z(AI_expanded_v3) = 8` compared with the old `rank_Z(AI_expanded_v2) = 8`.
- Combined Smith diagonal in BS coordinates: `[1, 1, 1, 1, 1, 1, 2, 2]`.
- Saturation closed: `False`.
