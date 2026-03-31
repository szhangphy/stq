# SG194 Upstream Raw BS Gap Audit v1

## Summary

- raw single rank(BS) = `16`
- raw double rank(BS) = `16`
- raw single/double quotient = `Z^3` / `Z^3`
- common free-generator count = `3`

## The Three Common Free Directions

- `common_free_generator_1`
  - support = `[{'label': 'P3_R5', 'coeff': -1}, {'label': 'P3_R6', 'coeff': 1}]`
  - support blocks = `{'P3': ['P3_R5', 'P3_R6']}`
  - BS coordinates = `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]`
- `common_free_generator_2`
  - support = `[{'label': 'P3_R5', 'coeff': 1}, {'label': 'P4_R1', 'coeff': 1}]`
  - support blocks = `{'P3': ['P3_R5'], 'P4': ['P4_R1']}`
  - BS coordinates = `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]`
- `common_free_generator_3`
  - support = `[{'label': 'P3_R1', 'coeff': 1}, {'label': 'P3_R2', 'coeff': 1}, {'label': 'P4_R3', 'coeff': 1}]`
  - support blocks = `{'P3': ['P3_R1', 'P3_R2'], 'P4': ['P4_R3']}`
  - BS coordinates = `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]`

## P3/P4 Constraint Exposure

- sector rows = `['P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P3_R5', 'P3_R6', 'P4_R1', 'P4_R2', 'P4_R3']`
- touching line ids = `['L2']`
- touching plane ids = `[]`
- restricted matrix shape/rank/nullity = `[3, 9]` / `3` / `6`
- touching source counts = `{'L2': 3}`

The current full compatibility matrix only sees the P3/P4 sector through the three `L2` rows below:

- `L2_R1`: `[{'label': 'P3_R2', 'coeff': 1}, {'label': 'P3_R3', 'coeff': 1}, {'label': 'P4_R3', 'coeff': -1}]`
- `L2_R2`: `[{'label': 'P3_R1', 'coeff': 1}, {'label': 'P3_R4', 'coeff': 1}, {'label': 'P4_R3', 'coeff': -1}]`
- `L2_R3`: `[{'label': 'P3_R5', 'coeff': 1}, {'label': 'P3_R6', 'coeff': 1}, {'label': 'P4_R1', 'coeff': -1}, {'label': 'P4_R2', 'coeff': -1}]`

## Residual Check

Every common free generator has zero residual against the full single and double with-planes matrix, but each one is only touched by `L2` rows.

- single residuals = `[{'generator_id': 'common_free_generator_1', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 8, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R3', 'row_support': ['P3_R5', 'P3_R6'], 'residual': 0}]}, {'generator_id': 'common_free_generator_2', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 8, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R3', 'row_support': ['P3_R5', 'P4_R1'], 'residual': 0}]}, {'generator_id': 'common_free_generator_3', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 6, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R1', 'row_support': ['P3_R2', 'P4_R3'], 'residual': 0}, {'row_index': 7, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R2', 'row_support': ['P3_R1', 'P4_R3'], 'residual': 0}]}]`
- double residuals = `[{'generator_id': 'common_free_generator_1', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 8, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R3', 'row_support': ['P3_R5', 'P3_R6'], 'residual': 0}]}, {'generator_id': 'common_free_generator_2', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 8, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R3', 'row_support': ['P3_R5', 'P4_R1'], 'residual': 0}]}, {'generator_id': 'common_free_generator_3', 'nonzero_residual_rows': [], 'touched_rows': [{'row_index': 6, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R1', 'row_support': ['P3_R2', 'P4_R3'], 'residual': 0}, {'row_index': 7, 'source_type': 'line', 'source_id': 'L2', 'basis_id': 'L2_R2', 'row_support': ['P3_R1', 'P4_R3'], 'residual': 0}]}]`

## Classification

- primary = `missing_effective_constraints_in_P3_P4_sector`
- secondary = `['wrong_use_of_little_co_group_vs_full_little_group_representation', 'wrong_handling_of_translational_Bloch_phase_e_minus_ik_t_in_compatibility_subduction']`
- ruled out = `['wrong_endpoint_restriction_geometry', 'wrong_plane_gluing_on_existing_P3_P4_planes', 'wrong_little_group_representation_construction_in_induction']`
- verdict: The three raw free directions survive because the current P3/P4 sector is only seen by the three L2 co-group equations, and no plane row touches P3/P4 at all. Algebraically this leaves the K/H sector underconstrained; implementation-wise the compatibility builder is using a phase-stripped character layer rather than a full little-group/projective subduction object.
