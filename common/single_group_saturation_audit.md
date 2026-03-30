# Single-Group Saturation Audit for 10.4.1.31

## Scope

- Compare the audited `BS_with_planes` lattice against `AI_expanded_v3` after adding the parametric antiunitary families `n, i, j`.
- Focus on finite-index saturation, not just rank.

## Rank Status

- `rank(BS_with_planes) = 8`.
- `rank(AI_expanded_v2) = 8`.
- `rank(AI_expanded_v3) = 8`.
- The rank was already closed at v2 and remains closed at v3.

## Smith Comparison

- v2 Smith diagonal in BS coordinates: `[1, 1, 1, 1, 1, 1, 2, 2]`.
- v3 Smith diagonal in BS coordinates: `[1, 1, 1, 1, 1, 1, 2, 2]`.
- Remaining finite index: `4`.
- Saturation closed: `False`.

## Parametric-Family Effect

- The successful `n, i, j` inductions all satisfy compatibility and all lie inside the existing v2 integer lattice.
- Therefore the v3 reduced exact basis is unchanged from v2 at the lattice level, even though the raw candidate matrix grows.

## Explicit Saturation Witness

- Witness `bs_basis_direction_03`:
  - BS basis coordinate: `[0, 0, 1, 0, 0, 0, 0, 0]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '1/2', '0', '0', '0', '0', '0']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '1', '0', '0', '0', '0', '0']`.
  - Witness unknown support id: `P3_diff_56_78_after_planes`.
  - Witness unknown support: `[{'unknown': 'P3_R5', 'coeff': 1}, {'unknown': 'P3_R6', 'coeff': -1}, {'unknown': 'P3_R7', 'coeff': 1}, {'unknown': 'P3_R8', 'coeff': -1}]`.
- Witness `bs_basis_direction_04`:
  - BS basis coordinate: `[0, 0, 0, 1, 0, 0, 0, 0]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '-1/2', '1', '0', '0', '0', '0']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '-1', '2', '0', '0', '0', '0']`.
  - Witness unknown support id: `P3_diff_12_34_after_planes`.
  - Witness unknown support: `[{'unknown': 'P3_R1', 'coeff': 1}, {'unknown': 'P3_R2', 'coeff': -1}, {'unknown': 'P3_R3', 'coeff': 1}, {'unknown': 'P3_R4', 'coeff': -1}]`.
- Witness `bs_basis_direction_05`:
  - BS basis coordinate: `[0, 0, 0, 0, 1, 0, 0, 0]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '-1/2', '0', '1', '0', '0', '0']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '-1', '0', '2', '0', '0', '0']`.
  - Witness unknown support id: `P1_diff_56_78_after_planes`.
  - Witness unknown support: `[{'unknown': 'P1_R5', 'coeff': 1}, {'unknown': 'P1_R6', 'coeff': -1}, {'unknown': 'P1_R7', 'coeff': 1}, {'unknown': 'P1_R8', 'coeff': -1}]`.
- Witness `bs_basis_direction_06`:
  - BS basis coordinate: `[0, 0, 0, 0, 0, 1, 0, 0]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '-1/2', '0', '0', '1', '0', '0']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '-1', '0', '0', '2', '0', '0']`.
  - Witness unknown support id: `P1_diff_12_34_after_planes`.
  - Witness unknown support: `[{'unknown': 'P1_R1', 'coeff': 1}, {'unknown': 'P1_R2', 'coeff': -1}, {'unknown': 'P1_R3', 'coeff': 1}, {'unknown': 'P1_R4', 'coeff': -1}]`.
- Witness `bs_basis_direction_07`:
  - BS basis coordinate: `[0, 0, 0, 0, 0, 0, 1, 0]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '0', '0', '0', '0', '1/2', '0']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '0', '0', '0', '0', '1', '0']`.
  - Witness unknown support id: `L3_endpoint_difference_after_planes`.
  - Witness unknown support: `[{'unknown': 'P3_R2', 'coeff': 1}, {'unknown': 'P3_R3', 'coeff': -1}, {'unknown': 'P3_R6', 'coeff': -1}, {'unknown': 'P3_R7', 'coeff': 1}, {'unknown': 'P5_R1', 'coeff': -1}, {'unknown': 'P5_R2', 'coeff': 1}]`.
- Witness `bs_basis_direction_08`:
  - BS basis coordinate: `[0, 0, 0, 0, 0, 0, 0, 1]`.
  - Smallest multiplier into `AI_expanded_v3`: `2`.
  - `v` is not in the AI lattice because its AI-basis solution is `['0', '0', '0', '0', '0', '0', '-1/2', '1']`.
  - `2 v` is in the AI lattice with AI-basis solution `['0', '0', '0', '0', '0', '0', '-1', '2']`.
  - Witness unknown support id: `L1_endpoint_difference_after_planes`.
  - Witness unknown support: `[{'unknown': 'P1_R2', 'coeff': 1}, {'unknown': 'P1_R3', 'coeff': -1}, {'unknown': 'P1_R6', 'coeff': -1}, {'unknown': 'P1_R7', 'coeff': 1}, {'unknown': 'P4_R1', 'coeff': -1}, {'unknown': 'P4_R2', 'coeff': 1}]`.

## Interpretation

- After adding `n, i, j`, all audited real-space families of this single group are now represented in the AI generator set.
- The remaining index-4 quotient is therefore no longer attributable to missing `n, i, j` families or to a rank defect.
- Under the current single-group formalism this residual finite quotient is a real unresolved non-rank issue. Its deeper topological interpretation is not claimed here.
