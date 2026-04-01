# SG194 Single Missing Target Layers v1

- Purpose: show which single layers were missing before the fix and which gap still remains after promotion to target rows.

```json
{
  "generated_at": "2026-04-01T13:15:42+08:00",
  "target_group": "194.1.1.1",
  "single_available_layers": [
    "shared_k_geometry",
    "active_current_row_language",
    "ordinary_external_target_rows",
    "projected_target_row_quotient_presentation"
  ],
  "single_missing_layers_before_fix": [
    "active_use_of_target_result_in_stage2_final_fields",
    "exact_single_current_external_generator_alignment"
  ],
  "blocking_function": {
    "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
    "source_function": "apply_single_direct_result_fields",
    "problem": "Overwrote the target-row-language 13/13/trivial payload with raw-current 16/13/Z^3 publication fields."
  },
  "blocking_matrices": {
    "current_single_ai_bs_matrix_shape": [
      16,
      45
    ],
    "target_projection_matrix_shape": [
      34,
      16
    ],
    "external_ordinary_generator_matrix_shape": [
      34,
      45
    ],
    "exact_linear_target_alignment_exists": false,
    "projected_current_matches_external_matrix_exactly": false,
    "mismatch_rank_after_projection": 1
  },
  "status_after_fix": {
    "single_target_result_is_active": true,
    "single_target_row_language_active": true,
    "single_target_row_language_internalized": false,
    "remaining_gap": "An exact single current/external target-generator alignment matrix does not exist for the present single BS-coordinate generator matrix against the cached external ordinary generator matrix."
  }
}
```
