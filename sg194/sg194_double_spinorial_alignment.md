# SG194 Double Spinorial Alignment

        This file performs the explicit **count alignment** between the current 45-label double local-corep inventory and Bilbao's 33 physically irreducible spinorial BANDREP generators.

        ## Fixed One-To-One Families

        Families `2a`, `4e`, `4f`, `6g`, `12i`, `12j`, `12k`, and `24l` are kept one-to-one with the Bilbao spinorial generator count convention.

        ## Explicit Merges At The Problematic Sites

        - `b:E1↑G(4)` <- `b_proj_doubleprime_1d_1, b_proj_doubleprime_1d_2` (pair-sum merge)
- `b:E2↑G(4)` <- `b_proj_prime_1d_3, b_proj_prime_1d_4` (pair-sum merge)
- `b:E3↑G(4)` <- `b_proj_doubleprime_2d_5, b_proj_doubleprime_2d_6` (pair-sum merge)
- `c:E1↑G(4)` <- `c_proj_doubleprime_1d_1, c_proj_doubleprime_1d_2` (pair-sum merge)
- `c:E2↑G(4)` <- `c_proj_prime_1d_3, c_proj_prime_1d_4` (pair-sum merge)
- `c:E3↑G(4)` <- `c_proj_doubleprime_2d_5, c_proj_doubleprime_2d_6` (pair-sum merge)
- `d:E1↑G(4)` <- `d_proj_doubleprime_1d_1, d_proj_doubleprime_1d_2` (pair-sum merge)
- `d:E2↑G(4)` <- `d_proj_prime_1d_3, d_proj_prime_1d_4` (pair-sum merge)
- `d:E3↑G(4)` <- `d_proj_doubleprime_2d_5, d_proj_doubleprime_2d_6` (pair-sum merge)
- `h:E↑G(12)` <- `h_proj_mm2_1, h_proj_mm2_2, h_proj_mm2_3, h_proj_mm2_4` (four-way merge)

        ## Rank Outcome

        - Current raw double AI rank: `13`
        - After explicit 45 -> 33 count alignment: `12`
        - Bilbao spinorial standard rank: `10`
        - Residual gap: `2`

        ## Interpretation

        The explicit count convention mismatch is fixed, but the basis mismatch is not fully resolved: the aligned current span is still rank 12 rather than rank 10. Therefore the double standard-space quotient remains blocked.

        - User-facing rewrite:
          `Do not quote the raw Z^16. The double line is still not aligned to the Bilbao physically irreducible spinorial basis: the obvious 6→3 and 4→1 merges can be written explicitly, but they only lower the current AI layer to rank 12, not to the Bilbao standard rank 10, so a standard-space quotient is still blocked.`
