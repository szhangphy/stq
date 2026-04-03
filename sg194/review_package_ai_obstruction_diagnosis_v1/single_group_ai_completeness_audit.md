# Single-Group AI Completeness Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Group type only: `1` (single group).
- This audit does not revisit the trusted k-space formalism, bridge, or family-level induction mechanics.
- The only task here is to decide whether `AI_expanded_v3` is already the complete single-group AI lattice and, if so, whether the residual Smith factors can be promoted to the honest single-group quotient `BS/AI`.

## Inputs Actually Used

- `single_group_local_rep_census_audit.md` and `single_group_local_rep_census_summary.json` for the unitary family census.
- `single_group_magnetic_local_corep_audit.md` and `single_group_pointlike_magnetic_coreps.json` for `a,b,d,e,g,h`.
- `single_group_parametric_magnetic_corep_audit.md` and `single_group_parametric_magnetic_coreps.json` for `n,i,j`.
- `single_group_ai_expanded_v3_candidates.json`, `single_group_ai_expanded_v3_basis.json`, and `single_group_saturation_summary.json` for the complete single-group AI lattice candidate and the current finite-index state.
- `single_group_site_symmetry_check.json` for the geometry / stabilizer consistency checks on all fifteen families.

## Family Coverage Table

| family | dim | mult | site symmetry | included local generators | complete? |
| --- | --- | --- | --- | --- | --- |
| `a` | `0` | `4` | `2'/m` | `a_Ap_eta_plus, a_Ap_eta_minus, a_App_eta_plus, a_App_eta_minus` | `yes` |
| `b` | `0` | `4` | `2'/m` | `b_Ap_eta_plus, b_Ap_eta_minus, b_App_eta_plus, b_App_eta_minus` | `yes` |
| `c` | `0` | `4` | `2/m` | `c_Ag, c_Bg, c_Au, c_Bu` | `yes` |
| `d` | `0` | `4` | `2'/m'` | `d_g_eta_plus, d_g_eta_minus, d_u_eta_plus, d_u_eta_minus` | `yes` |
| `e` | `0` | `4` | `2'/m'` | `e_g_eta_plus, e_g_eta_minus, e_u_eta_plus, e_u_eta_minus` | `yes` |
| `f` | `0` | `4` | `2/m` | `f_Ag, f_Bg, f_Au, f_Bu` | `yes` |
| `g` | `0` | `4` | `2/m'` | `g_A_eta_plus, g_A_eta_minus, g_B_eta_plus, g_B_eta_minus` | `yes` |
| `h` | `0` | `4` | `2/m'` | `h_A_eta_plus, h_A_eta_minus, h_B_eta_plus, h_B_eta_minus` | `yes` |
| `i` | `1` | `8` | `2'` | `i_A_eta_plus, i_A_eta_minus` | `yes` |
| `j` | `1` | `8` | `2'` | `j_A_eta_plus, j_A_eta_minus` | `yes` |
| `k` | `1` | `8` | `2` | `k_A, k_B` | `yes` |
| `l` | `1` | `8` | `2` | `l_A, l_B` | `yes` |
| `m` | `2` | `8` | `m` | `m_A_prime, m_A_double_prime` | `yes` |
| `n` | `2` | `8` | `m'` | `n_A_eta_plus, n_A_eta_minus` | `yes` |
| `o` | `3` | `16` | `1` | `o_A` | `yes` |

## Antiunitary-Family Completeness Basis

- All antiunitary families in this single-group audit have order-1 or order-2 unitary subgroups whose irreps are real and one-dimensional.
- The audited antiunitary generators square to the identity and either fix the unitary subgroup generator or act trivially because the unitary subgroup is the identity alone.
- Therefore only Wigner case-a occurs on these families, each source unitary irrep has exactly two eta=+/- direct extensions, and there is no room for missing higher-dimensional single-group magnetic coreps.

- `a`: The unitary subgroup is Cs with real one-dimensional irreps A', A''. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `b`: The unitary subgroup is Cs with real one-dimensional irreps A', A''. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `d`: The unitary subgroup is Ci with real one-dimensional irreps g, u. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `e`: The unitary subgroup is Ci with real one-dimensional irreps g, u. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `g`: The unitary subgroup is C2 with real one-dimensional irreps A, B. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `h`: The unitary subgroup is C2 with real one-dimensional irreps A, B. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `i`: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `j`: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- `n`: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.

## Family-Level Verdicts

### Family `a`

- Site symmetry summary: `2'/m` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `a_Ap_eta_plus, a_Ap_eta_minus, a_App_eta_plus, a_App_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is Cs with real one-dimensional irreps A', A''. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `b`

- Site symmetry summary: `2'/m` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `b_Ap_eta_plus, b_Ap_eta_minus, b_App_eta_plus, b_App_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is Cs with real one-dimensional irreps A', A''. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `c`

- Site symmetry summary: `2/m` / `2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `4` / `0`.
- Included local reps/coreps: `c_Ag, c_Bg, c_Au, c_Bu`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary site symmetry is the abelian order-4 group C2h, so the full single-group local-irrep census is the four one-dimensional characters Ag/Bg/Au/Bu.
- Notes: Complete: the enumerated local irreps exactly match the expected C2h single-group character list.

### Family `d`

- Site symmetry summary: `2'/m'` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `d_g_eta_plus, d_g_eta_minus, d_u_eta_plus, d_u_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is Ci with real one-dimensional irreps g, u. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `e`

- Site symmetry summary: `2'/m'` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `e_g_eta_plus, e_g_eta_minus, e_u_eta_plus, e_u_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is Ci with real one-dimensional irreps g, u. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `f`

- Site symmetry summary: `2/m` / `2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `4` / `0`.
- Included local reps/coreps: `f_Ag, f_Bg, f_Au, f_Bu`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary site symmetry is the abelian order-4 group C2h, so the full single-group local-irrep census is the four one-dimensional characters Ag/Bg/Au/Bu.
- Notes: Complete: the enumerated local irreps exactly match the expected C2h single-group character list.

### Family `g`

- Site symmetry summary: `2/m'` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `g_A_eta_plus, g_A_eta_minus, g_B_eta_plus, g_B_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is C2 with real one-dimensional irreps A, B. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `h`

- Site symmetry summary: `2/m'` / `m'[x] * m'[y] * 2[z]`.
- Stabilizer size / unitary / antiunitary: `4` / `2` / `2`.
- Included local reps/coreps: `h_A_eta_plus, h_A_eta_minus, h_B_eta_plus, h_B_eta_minus`.
- Sum of squared local dimensions: `4`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is C2 with real one-dimensional irreps A, B. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `i`

- Site symmetry summary: `2'` / `m'[x]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Included local reps/coreps: `i_A_eta_plus, i_A_eta_minus`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `j`

- Site symmetry summary: `2'` / `m'[x]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Included local reps/coreps: `j_A_eta_plus, j_A_eta_minus`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `k`

- Site symmetry summary: `2` / `2[z]`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- Included local reps/coreps: `k_A, k_B`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary site symmetry is order-2 rotation symmetry, hence abelian with exactly two one-dimensional single-group irreps.
- Notes: Complete: the enumerated local irreps exactly match the expected C2 single-group character list.

### Family `l`

- Site symmetry summary: `2` / `2[z]`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- Included local reps/coreps: `l_A, l_B`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary site symmetry is order-2 rotation symmetry, hence abelian with exactly two one-dimensional single-group irreps.
- Notes: Complete: the enumerated local irreps exactly match the expected C2 single-group character list.

### Family `m`

- Site symmetry summary: `m` / `2[z]`.
- Stabilizer size / unitary / antiunitary: `2` / `2` / `0`.
- Included local reps/coreps: `m_A_prime, m_A_double_prime`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary site symmetry is order-2 mirror symmetry, hence abelian with exactly two one-dimensional single-group irreps.
- Notes: Complete: the enumerated local irreps exactly match the expected Cs single-group character list.

### Family `n`

- Site symmetry summary: `m'` / `m'[y]`.
- Stabilizer size / unitary / antiunitary: `2` / `1` / `1`.
- Included local reps/coreps: `n_A_eta_plus, n_A_eta_minus`.
- Sum of squared local dimensions: `2`.
- Complete for single group: `True`.
- Basis: The unitary subgroup is C1 with real one-dimensional irreps A. The audited antiunitary action fixes those irreps and the Wigner analysis is case-a, so each unitary irrep has exactly two eta=+/- direct extensions and no higher-dimensional single-group magnetic coreps are expected.
- Notes: Complete: the family's magnetic local-corep census closes under the audited case-a extension logic.

### Family `o`

- Site symmetry summary: `1` / `1`.
- Stabilizer size / unitary / antiunitary: `1` / `1` / `0`.
- Included local reps/coreps: `o_A`.
- Sum of squared local dimensions: `1`.
- Complete for single group: `True`.
- Basis: The generic family has trivial single-group site symmetry, so there is exactly one one-dimensional local irrep.
- Notes: Complete: the enumerated local irreps exactly match the expected C1 single-group character list.

## Completeness Verdict

- All families audited: `True`.
- Complete families: `a, b, c, d, e, f, g, h, i, j, k, l, m, n, o`.
- Incomplete families: `none`.
- `AI_expanded_v3` can be promoted to the complete single-group AI lattice: `True`.
- Next blocker: None inside the present single-group completeness stage; the quotient extraction is now meaningful and is generated alongside this audit.

## Single-Group Quotient Extraction

- `rank(BS_with_planes) = 8`.
- `rank(AI_complete_single) = 8`.
- Smith diagonal in BS coordinates: `[1, 1, 1, 1, 1, 1, 2, 2]`.
- Quotient group: `Z2 x Z2`.
- Number of independent finite indicators: `2`.
- The two indicator generators below are independent by Smith construction and therefore span the entire finite quotient.

### `indicator_generator_1`

- BS basis coordinates: `[0, 0, 0, 0, 0, 1, 0, 0]`.
- Smallest multiplier into AI: `2`.
- Unknown support: `[{'unknown': 'P1_R1', 'coeff': -1}, {'unknown': 'P1_R2', 'coeff': 1}, {'unknown': 'P1_R3', 'coeff': -1}, {'unknown': 'P1_R4', 'coeff': 1}]`.
- Relation to previous witness: `bs_basis_direction_06`.

### `indicator_generator_2`

- BS basis coordinates: `[0, 0, 0, 0, 0, 0, 0, 1]`.
- Smallest multiplier into AI: `2`.
- Unknown support: `[{'unknown': 'P1_R2', 'coeff': 1}, {'unknown': 'P1_R3', 'coeff': -1}, {'unknown': 'P1_R6', 'coeff': -1}, {'unknown': 'P1_R7', 'coeff': 1}, {'unknown': 'P4_R1', 'coeff': -1}, {'unknown': 'P4_R2', 'coeff': 1}]`.
- Relation to previous witness: `bs_basis_direction_08`.

## Scope Limits

- This result applies only to the current single-group (`groupType=1`) treatment of `10.4.1.31` in the present with-planes basis and unknown ordering.
- It does not apply to double groups, other SSGs, or any different formalism/basis choice that has not been matched to the same audited setup.
