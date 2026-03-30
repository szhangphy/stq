# SG194 Standard Alignment Report V2

        ## 1. Problem Background And V1 Limitation

        The v1 SG194 alignment settled the easy part of the language conversion but still relied on two constructions that were not hard enough:

        - Single: the quotient was made trivial by an AI-anchored projection with an explicitly killed complement.
        - Double: the basis mismatch was reduced only at the level of generator counts.

        This v2 report upgrades both sides to stricter definitions.

        ## 2. Single: AI-Anchored Projection vs External Row-Space Restriction

        Let the current raw unknown vector be
        \[
        n_{\mathrm{raw}} \in \mathbb{Z}^{62}.
        \]
        The new single map does not start from the current AI basis. Instead it applies the literal standard-point selection
        \[
        S_{\mathrm{HSP}} : \mathbb{Z}^{62} \to \mathbb{Z}^{34},
        \]
        where the 34 retained rows are the current `P1,P2,P3,B1,P5,P6` blocks, corresponding externally to ordinary SG 194 `GM,A,K,H,M,L`.

        On the current raw BS basis this gives:

        - restricted BS rank = `18`
        - restricted AI rank = `13`
        - restricted point-space quotient = `Z^5`

        Therefore the old v1 `trivial` conclusion is not reproduced by the stricter non-AI-anchored method.

        ## 3. Single: Five Explicit Extra Directions

        The five extra current directions beyond AI inside the selected HSP point space are:

        - `194_1_1_1_single_bs_raw_basis_04` with support [{'label': 'P1_R2', 'coeff': 2}, {'label': 'P1_R3', 'coeff': -1}, {'label': 'P1_R6', 'coeff': 1}, {'label': 'P2_R1', 'coeff': 1}, {'label': 'P5_R2', 'coeff': 2}, {'label': 'P5_R3', 'coeff': -1}, {'label': 'P5_R6', 'coeff': 1}, {'label': 'P6_R1', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_06` with support [{'label': 'P1_R2', 'coeff': -1}, {'label': 'P1_R3', 'coeff': 1}, {'label': 'P1_R6', 'coeff': -1}, {'label': 'P1_R7', 'coeff': 1}, {'label': 'P5_R2', 'coeff': -1}, {'label': 'P5_R3', 'coeff': 1}, {'label': 'P5_R6', 'coeff': -1}, {'label': 'P5_R7', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_07` with support [{'label': 'P1_R2', 'coeff': -1}, {'label': 'P1_R3', 'coeff': 1}, {'label': 'P5_R2', 'coeff': -1}, {'label': 'P5_R3', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_13` with support [{'label': 'P1_R1', 'coeff': -1}, {'label': 'P1_R4', 'coeff': 1}, {'label': 'P1_R6', 'coeff': 1}, {'label': 'P1_R7', 'coeff': -1}]
- `194_1_1_1_single_bs_raw_basis_14` with support [{'label': 'P1_R1', 'coeff': -2}, {'label': 'P1_R2', 'coeff': 1}, {'label': 'P1_R4', 'coeff': 1}, {'label': 'P1_R5', 'coeff': -1}, {'label': 'P1_R6', 'coeff': 2}, {'label': 'P1_R7', 'coeff': -1}, {'label': 'P2_R1', 'coeff': 1}, {'label': 'P2_R2', 'coeff': -1}]

        These five directions explain why the raw v1 ordinary quotient could be collapsed to `trivial` only after an additional constructed projection.

        ## 4. Double: Count Alignment vs Representation-Content Alignment

        The new double method works in the current HSP representation-content space rather than at the level of labels only.

        - current HSP-space rank = `13`
        - identity-sector rank = `9`
        - count-aligned rank = `12`
        - Bilbao spinorial rank = `10`

        Sitewise, the problematic sectors behave as follows:

        - `b` current rank `6` -> merged rank `3`
- `c` current rank `6` -> merged rank `3`
- `d` current rank `6` -> merged rank `3`
- `h` current rank `4` -> merged rank `1`

        ## 5. Double: Residual Rank-2 Mismatch

        After content-based merging, the problematic sector still contributes three independent directions over the identity families, whereas the Bilbao spinorial total rank implies that only one such direction should survive. The residual rank-2 blocker can be written explicitly as:

        - `delta_c1_minus_b1` with support [{'label': 'P3_R1', 'coeff': -2}, {'label': 'P3_R3', 'coeff': -2}, {'label': 'P3_R5', 'coeff': 2}, {'label': 'B1_R1', 'coeff': 2}, {'label': 'B1_R3', 'coeff': -2}]
- `delta_d1_minus_b1` with support [{'label': 'P3_R1', 'coeff': -2}, {'label': 'P3_R3', 'coeff': -2}, {'label': 'P3_R5', 'coeff': 2}, {'label': 'B1_R2', 'coeff': 2}, {'label': 'B1_R3', 'coeff': -2}]

        The mismatch is therefore no longer a heuristic count issue; it is a concrete representation-content excess in the `2b/2c/2d/6h` sector.

        ## 6. New Recomputed Results

        Single:

        - old result = `trivial`
        - new result = unresolved at the strict external-row-space level
        - current strict point-space quotient = `Z^5`

        Double:

        - old result = blocked after count alignment
        - new result = still blocked, but with an explicit rank-2 blocker basis

        ## 7. Updated User-Facing Conclusions

        - Single should no longer be summarized as “standard-space quotient = trivial” without qualification. The v2 method shows that the non-AI-anchored HSP restriction still leaves a free rank-5 gap; an external ordinary generator matrix or an equivalent cached point-irrep basis transform is still required before an honest final standard-space quotient can be stated.
        - Double should no longer be summarized as “45 -> 33 count merge done”. The v2 method shows exactly where the remaining rank-2 mismatch lives and why the standard-space quotient is still blocked.

        ## 8. Remaining Blockers And Next Step

        - Single blocker: obtain the full external ordinary SG194 34x45 generator matrix, or a cached equivalent, so that the current 18-dimensional HSP image can be reduced to the external 13-dimensional ordinary symmetry-data row space without AI anchoring.
        - Double blocker: obtain the full external 56x33 Bilbao spinorial generator matrix, or a cached equivalent, so that the current 34-row HSP content can be lifted into the external spinorial row basis and the explicit rank-2 blocker can be tested against the physically irreducible Bilbao convention.

        ## 9. Implementation Mapping

        - Single new restriction map and rank-5 blocker basis: `sg194_single_external_rowspace_projection.json`
        - Double new representation-content alignment and rank-2 blocker basis: `sg194_double_repcontent_alignment.json`
        - Updated v2 recomputed results: `sg194_single_standard_quotient_recomputed_v2.json`, `sg194_double_standard_quotient_recomputed_v2.json`
        - Consolidated v2 audit: `sg194_standard_alignment_audit_v2.md`, `sg194_standard_alignment_summary_v2.json`
