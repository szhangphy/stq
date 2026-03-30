# Single-Group Local-Rep Census Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Stage: expand the atomic-side work from the earlier minimal prototype to a larger single-group AI candidate lattice.
- This audit keeps the earlier bridge result fixed and only pushes the real-space/local-rep side forward.

## Code Paths Actually Used

- `swyckoff_r.py`: real-space families, representative coordinates, sample-point generation, and the audited site-symmetry labels.
- `swyckoff_k.py`: background source of the same standardized operation convention and with-planes unknown ordering context.
- `SSGReps/SSGReps/SSGReps.py`: raw little-group operations plus `character`/`rep_degree`; the `exp(-i k·tauC)` correction remains mandatory.
- `swyckoff.py`: not present in this repository, so it is not part of the actual real-space path for this group.

## Trusted Families

- All previously double-checked families remain trusted at the geometric/site-symmetry level: `o, n, m, l, k, j, i, h, g, f, e, d, c, b, a`.
- The bridge `r_conv = P r_mag` with `P = diag(1,2,2)` is reused without modification.

## Tiering

- Tier 1: `o, m, k, l, c, f`.
  These six families have purely unitary site symmetry, so their local irreps are fully reconstructable as honest one-dimensional characters of the audited stabilizer.
- Tier 2: `h, g, e, d, b, a`.
  These are point-like and geometrically stable, but the site symmetry contains antiunitary elements; a magnetic-corep audit is still missing.
- Tier 3: `n, j, i`.
  These families combine antiunitary site symmetry with free real-space parameters, so they were left out of this round.

## Included Local Reps

- `o`: `o_A`.
- `m`: `m_A_prime`, `m_A_double_prime`.
- `k`: `k_A`, `k_B`.
- `l`: `l_A`, `l_B`.
- `c`: `c_Ag`, `c_Bg`, `c_Au`, `c_Bu`.
- `f`: `f_Ag`, `f_Bg`, `f_Au`, `f_Bu`.

## Important Sample-Point Detail

- For parameter families such as `o/m/k/l`, the orbit must be generated from a generic sample point inside the family, not directly from the symbolic `x0` anchor.
- Reusing the old `x0`-based orbit logic would incorrectly collapse these families to more special positions.
- This round therefore uses the same sample-parameter convention as the bridge helper when the family dimension is nonzero.

## Current Inclusion Boundary

- Expanded candidate generation is intentionally restricted to the Tier-1 families above.
- The current script does not attempt magnetic Wigner coreps for antiunitary site symmetries, so `a,b,d,e,g,h,n,i,j` stay outside the candidate matrix.
- This means the present `AI_expanded` is larger than the earlier 2-generator prototype, but it is still not the full single-group AI lattice.

## BS Target Space

- The target space remains the audited 31-dimensional with-planes unknown ordering from `single_group_bs_with_planes_basis_raw.json` and `single_group_full_compatibility_with_planes.json`.
- `rank(BS_with_planes) = 8` at the basis level used here.
