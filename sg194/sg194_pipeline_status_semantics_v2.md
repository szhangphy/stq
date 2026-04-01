# SG194 Pipeline Status Semantics V2

- `checks_passed`: structural/mechanical pipeline checks.
- `final_results_available`: final single/double results exist.
- `final_results_verified`: those results also satisfy the verification-status contract.
- `all_passed` is kept only as a backward-compatible alias for `checks_passed`.
