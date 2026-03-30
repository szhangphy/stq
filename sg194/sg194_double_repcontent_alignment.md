# SG194 Double Representation-Content Alignment

        ## Old vs New

        - Old method: `Heuristic count merge 45 -> 33 without explicit row-content diagnosis`
        - New method: `Representation-content alignment on the current HSP row-content space, with explicit sitewise merged channels and residual mismatch basis`
        - Old result: current aligned rank `12` vs Bilbao rank `10`

        ## Sitewise Content Alignment

        - `b`: current count `6`, current rank `6`, merged rank `3`
- `c`: current count `6`, current rank `6`, merged rank `3`
- `d`: current count `6`, current rank `6`, merged rank `3`
- `h`: current count `4`, current rank `4`, merged rank `1`

        The pairings at `2b/2c/2d` and the four-way sum at `6h` are now justified by explicit current HSP row-content vectors rather than by count alone.

        ## Rank Outcome

        - Current raw HSP-space rank: `13`
        - Identity-sector rank: `9`
        - Count-aligned rank in current HSP space: `12`
        - Bilbao spinorial rank: `10`
        - Residual gap: `2`

        ## Residual Rank-2 Basis

        - `delta_c1_minus_b1`: [{'label': 'P3_R1', 'coeff': -2}, {'label': 'P3_R3', 'coeff': -2}, {'label': 'P3_R5', 'coeff': 2}, {'label': 'B1_R1', 'coeff': 2}, {'label': 'B1_R3', 'coeff': -2}]
- `delta_d1_minus_b1`: [{'label': 'P3_R1', 'coeff': -2}, {'label': 'P3_R3', 'coeff': -2}, {'label': 'P3_R5', 'coeff': 2}, {'label': 'B1_R2', 'coeff': 2}, {'label': 'B1_R3', 'coeff': -2}]

        ## Conclusion

        The residual mismatch is no longer a vague count mismatch. It is a concrete rank-`2` excess inside the problematic `2b/2c/2d/6h` representation-content sector. The standard-space quotient still cannot be recomputed honestly until the full external spinorial generator matrix is available and these two excess directions are either matched or quotiented out for a physically irreducible Bilbao-standard basis.
