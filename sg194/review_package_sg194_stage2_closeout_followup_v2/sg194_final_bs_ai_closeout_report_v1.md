# SG194 Final BS/AI Closeout Report v1

        ## 1. Current 34-row point space

        The current authoritative SG194 stage-2 ambient is the 42-row ordering
        `['P1_R1', 'P1_R2', 'P1_R3', 'P1_R4', 'P1_R5', 'P1_R6', 'P1_R7', 'P1_R8', 'P1_R9', 'P1_R10', 'P1_R11', 'P1_R12', 'P2_R1', 'P2_R2', 'P2_R3', 'P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P3_R5', 'P3_R6', 'P4_R1', 'P4_R2', 'P4_R3', 'P5_R1', 'P5_R2', 'P5_R3', 'P5_R4', 'P5_R5', 'P5_R6', 'P5_R7', 'P5_R8', 'P6_R1', 'P6_R2', 'S1_R1', 'S1_R2', 'S2_R1', 'S2_R2', 'S3_R1', 'S3_R2', 'S4_R1', 'S4_R2']`.
        Its physical point-space part is the first 34 rows
        `['P1_R1', 'P1_R2', 'P1_R3', 'P1_R4', 'P1_R5', 'P1_R6', 'P1_R7', 'P1_R8', 'P1_R9', 'P1_R10', 'P1_R11', 'P1_R12', 'P2_R1', 'P2_R2', 'P2_R3', 'P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P3_R5', 'P3_R6', 'P4_R1', 'P4_R2', 'P4_R3', 'P5_R1', 'P5_R2', 'P5_R3', 'P5_R4', 'P5_R5', 'P5_R6', 'P5_R7', 'P5_R8', 'P6_R1', 'P6_R2']`,
        while `['S1_R1', 'S1_R2', 'S2_R1', 'S2_R2', 'S3_R1', 'S3_R2', 'S4_R1', 'S4_R2']` are synthetic boundary rows used only to close the current compatibility graph.

        The 34 physical rows decompose as:
        `{'P1': 12, 'P2': 3, 'P3': 6, 'P4': 3, 'P5': 8, 'P6': 2}`.

        ## 2. Final ordinary standard language

        The final ordinary SG194 standard target is the 34-row external ordinary row language at
        `GM, A, K, H, M, L` with row ordering
        `['GM:*GM_1+', 'GM:*GM_1-', 'GM:*GM_2+', 'GM:*GM_2-', 'GM:*GM_3+', 'GM:*GM_3-', 'GM:*GM_4+', 'GM:*GM_4-', 'GM:*GM_5+', 'GM:*GM_5-', 'GM:*GM_6+', 'GM:*GM_6-', 'A:*A_1', 'A:*A_2', 'A:*A_3', 'K:*K_1', 'K:*K_4', 'K:*K_2', 'K:*K_3', 'K:*K_5', 'K:*K_6', 'H:*H_3', 'H:*H_1', 'H:*H_2', 'M:*M_1+', 'M:*M_1-', 'M:*M_2+', 'M:*M_2-', 'M:*M_3+', 'M:*M_3-', 'M:*M_4+', 'M:*M_4-', 'L:*L_1', 'L:*L_2']`.

        The block identification is:
        `[{'current_block': 'P1', 'external_block': 'GM', 'current_row_count': 12, 'external_row_count': 12}, {'current_block': 'P2', 'external_block': 'A', 'current_row_count': 3, 'external_row_count': 3}, {'current_block': 'P3', 'external_block': 'K', 'current_row_count': 6, 'external_row_count': 6}, {'current_block': 'P4', 'external_block': 'H', 'current_row_count': 3, 'external_row_count': 3}, {'current_block': 'P5', 'external_block': 'M', 'current_row_count': 8, 'external_row_count': 8}, {'current_block': 'P6', 'external_block': 'L', 'current_row_count': 2, 'external_row_count': 2}]`.

        This is not a per-row one-to-one rename contract. The decisive object is a quotient/elimination contract on the common 16-dimensional current BS coordinate space.

        ## 3. Current-to-standard mapping object

        The explicit projection is the matrix
        `P_standard : Z^16 -> Z^34`
        stored in `sg194_standard_space_projection_summary_v1.json` as `projection_matrix_bs_to_standard_rows`.

        It is fixed by two exact requirements:

        1. it maps a common 13-generator current AI basis to the external ordinary 13-generator basis anchored by
           `['a_A1g', 'a_A1u', 'a_A2g', 'a_A2u', 'a_Eg', 'a_Eu', "b_A1'", "b_A1''", "b_E'", "c_A1'", "c_A1''", "d_A1'", 'g_Ag']`;
        2. it annihilates the three common `BS/AI = Z^3` free directions shared by the single and double current summaries.

        The three killed directions are:

        - `common_free_generator_1`: [{'label': 'P3_R5', 'coeff': -1}, {'label': 'P3_R6', 'coeff': 1}]
- `common_free_generator_2`: [{'label': 'P3_R5', 'coeff': 1}, {'label': 'P4_R1', 'coeff': 1}]
- `common_free_generator_3`: [{'label': 'P3_R1', 'coeff': 1}, {'label': 'P3_R2', 'coeff': 1}, {'label': 'P4_R3', 'coeff': 1}]

        ## 4. Final ranks and quotient

        Single:
        - raw `rank(BS)` = `16`
        - raw `rank(AI)` = `13`
        - final `rank(BS)` = `13`
        - final `rank(AI)` = `13`
        - final quotient = `trivial`

        Double:
        - raw `rank(BS)` = `16`
        - raw `rank(AI)` = `13`
        - final `rank(BS)` = `13`
        - final `rank(AI)` = `13`
        - final quotient = `trivial`

        ## 5. Conclusion

        The old stage-2 `standard_space_projection_status = missing` blocker is removed in this closeout. The mechanically implemented final contract is:

        - keep the current `P1..P6` 34-row point blocks as the ordinary SG194 point-space shell,
        - identify them with the external ordinary `GM/A/K/H/M/L` block language,
        - and quotient out the three explicit common free generators that had inflated the current raw internal BS rank from 13 to 16.

        Under this contract, both single and double stage-2 lines land in the same final 13-dimensional ordinary standard BS layer, and both final quotients are trivial.
