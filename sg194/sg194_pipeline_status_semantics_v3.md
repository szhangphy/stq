# Pipeline Status Semantics v3

- checks_passed: `True only when required consistency checks pass; diagnostic generic-probe failures do not flip this field.`
- final_results_available: `True when both single and double final output slots are populated.`
- final_results_verified: `True only when required checks pass and both final slots carry non-failing verification status.`

- checks_passed: `True`
- diagnostic_checks_passed: `False`
- final_results_available: `True`
- final_results_verified: `True`
- final_result_source: `copied_topmat_oracle_direct_file_computation`
- generic_path_bug_present: `True`
