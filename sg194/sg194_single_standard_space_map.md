# SG194 Single Standard-Space Map

        This file fixes the single-group mapping on the **current raw BS subspace** rather than on the full 62-dimensional unknown space.

        ## Domain And Target

        - Raw BS basis size: `29`
        - Standard target rows: `34` ordinary SG 194 symmetry-data rows at `GM, A, K, H, M, L`
        - External standard AI rank: `13`

        ## Construction

        Let `M` be the current `AI -> BS` coefficient matrix in BS coordinates, and let `B_std` be the external ordinary SG 194 AI basis obtained by applying the current integer candidate-to-basis relations to the Bilbao SITESYM generator matrix.

        We extend the 13 AI columns of `M` to a full 29-column basis `[M | C]` of the current raw BS coordinate space. The standard-space projection is then

        \[
        P_{\mathrm{single}} = B_{\mathrm{std}}
        \begin{bmatrix} I_{13} & 0 \end{bmatrix}
        [M\; C]^{-1}.
        \]

        By construction:

        - `P_single * M = B_std`
        - `P_single * C = 0`

        Therefore the 16 complement directions in `C` are the explicit enlarged-space directions that inflate the raw 29-dimensional ambient BS space beyond the standard ordinary SG 194 symmetry-data layer.

        ## Enlarged-Space Complement

        - `single_enlarged_complement_01` seeded by BS coordinate unit index `0` with support [{'label': '194_1_1_1_single_bs_raw_basis_01', 'coeff': 1}]
- `single_enlarged_complement_02` seeded by BS coordinate unit index `1` with support [{'label': '194_1_1_1_single_bs_raw_basis_02', 'coeff': 1}]
- `single_enlarged_complement_03` seeded by BS coordinate unit index `2` with support [{'label': '194_1_1_1_single_bs_raw_basis_03', 'coeff': 1}]
- `single_enlarged_complement_04` seeded by BS coordinate unit index `3` with support [{'label': '194_1_1_1_single_bs_raw_basis_04', 'coeff': 1}]
- `single_enlarged_complement_05` seeded by BS coordinate unit index `4` with support [{'label': '194_1_1_1_single_bs_raw_basis_05', 'coeff': 1}]
- `single_enlarged_complement_06` seeded by BS coordinate unit index `5` with support [{'label': '194_1_1_1_single_bs_raw_basis_06', 'coeff': 1}]
- `single_enlarged_complement_07` seeded by BS coordinate unit index `6` with support [{'label': '194_1_1_1_single_bs_raw_basis_07', 'coeff': 1}]
- `single_enlarged_complement_08` seeded by BS coordinate unit index `7` with support [{'label': '194_1_1_1_single_bs_raw_basis_08', 'coeff': 1}]
- ... and 8 more complement directions

        ## Recomputed Quotient

        - Raw quotient: `Z^16`
        - Standard-space quotient: `trivial`
        - User-facing rewrite:
          `Do not quote the raw Z^16. After projecting the current 29-dimensional raw BS layer onto the ordinary SG 194 standard symmetry-data space, the BS image collapses onto the same 13-dimensional layer already spanned by the externally aligned AI, so the ordinary standard-space quotient is trivial in this constructed alignment.`
