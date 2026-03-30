# SG194 Single External Row-Space Projection

        ## Old vs New

        - Old method: `AI-anchored projection using [M | C]^{-1} and explicit complement killing`
        - New method: `External-standard-point-determined restriction to the 34 HSP coordinates GM/A/K/H/M/L, with no AI-preserving complement-killing step`
        - Old trivial claim: `trivial`

        ## New Projection

        - Domain: current raw unknown ordering of size `62`
        - Target: the `34` standard HSP coordinates selected by the external ordinary SG 194 point list `GM/A/K/H/M/L`
        - Block map: `[{'current_block': 'P1', 'external_block': 'GM'}, {'current_block': 'P2', 'external_block': 'A'}, {'current_block': 'P3', 'external_block': 'K'}, {'current_block': 'B1', 'external_block': 'H'}, {'current_block': 'P5', 'external_block': 'M'}, {'current_block': 'P6', 'external_block': 'L'}]`

        This map is the literal coordinate restriction from the raw unknown ordering to the current HSP block set. It does not preserve the current AI by construction and does not kill any complement by hand.

        ## Rank Outcome

        - Current HSP-space BS rank: `18`
        - Current HSP-space AI rank: `13`
        - Current HSP-space quotient: `Z^5`

        ## Extra Directions Beyond AI

        - `194_1_1_1_single_bs_raw_basis_04`: [{'label': 'P1_R2', 'coeff': 2}, {'label': 'P1_R3', 'coeff': -1}, {'label': 'P1_R6', 'coeff': 1}, {'label': 'P2_R1', 'coeff': 1}, {'label': 'P5_R2', 'coeff': 2}, {'label': 'P5_R3', 'coeff': -1}, {'label': 'P5_R6', 'coeff': 1}, {'label': 'P6_R1', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_06`: [{'label': 'P1_R2', 'coeff': -1}, {'label': 'P1_R3', 'coeff': 1}, {'label': 'P1_R6', 'coeff': -1}, {'label': 'P1_R7', 'coeff': 1}, {'label': 'P5_R2', 'coeff': -1}, {'label': 'P5_R3', 'coeff': 1}, {'label': 'P5_R6', 'coeff': -1}, {'label': 'P5_R7', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_07`: [{'label': 'P1_R2', 'coeff': -1}, {'label': 'P1_R3', 'coeff': 1}, {'label': 'P5_R2', 'coeff': -1}, {'label': 'P5_R3', 'coeff': 1}]
- `194_1_1_1_single_bs_raw_basis_13`: [{'label': 'P1_R1', 'coeff': -1}, {'label': 'P1_R4', 'coeff': 1}, {'label': 'P1_R6', 'coeff': 1}, {'label': 'P1_R7', 'coeff': -1}]
- `194_1_1_1_single_bs_raw_basis_14`: [{'label': 'P1_R1', 'coeff': -2}, {'label': 'P1_R2', 'coeff': 1}, {'label': 'P1_R4', 'coeff': 1}, {'label': 'P1_R5', 'coeff': -1}, {'label': 'P1_R6', 'coeff': 2}, {'label': 'P1_R7', 'coeff': -1}, {'label': 'P2_R1', 'coeff': 1}, {'label': 'P2_R2', 'coeff': -1}]

        ## Conclusion

        The stricter v2 method does not reproduce the v1 `trivial` quotient. It leaves a rank-`5` free gap inside the selected HSP point space. To reduce that rank-`18` current image to the external ordinary SG 194 standard rank `13`, one still needs the full external ordinary generator matrix or an equivalent cached point-irrep basis transform.
