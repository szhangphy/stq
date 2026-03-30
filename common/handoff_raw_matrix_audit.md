# Handoff: Raw Matrix Audit

## Current Stage

- The raw matrix/vector export is complete for all four fixed cases.
- Every case now has raw `C`, raw BS basis, raw AI candidates, reduced AI basis, exact `AI -> BS` matrix, and a raw quotient file.
- The independent recompute minipack is generated and copied into the package.

## Per-Case Raw Quotients

- `10.4.1.31` / `1`: raw quotient `Z2 x Z2`, free rank `0`, finite part `[2, 2]`.
- `10.4.1.31` / `2`: raw quotient `Z^2 x Z2 x Z2 x Z2 x Z2`, free rank `2`, finite part `[2, 2, 2, 2]`.
- `194.1.1.1` / `1`: raw quotient `Z^16`, free rank `16`, finite part `[]`.
- `194.1.1.1` / `2`: raw quotient `Z^16`, free rank `16`, finite part `[]`.

## Next Unique Task

- Do not regenerate the workflow outputs. The next unique task, if another review asks for it, is to let an external reviewer rerun `independent_recompute_minipack/recompute_from_raw.py` and compare the results to the current user-facing quotient interpretation layer.

## Files To Read First

1. `raw_matrix_level_audit_report.pdf`
2. `raw_matrix_level_audit.md`
3. `raw_matrix_level_audit_summary.json`
4. `independent_recompute_minipack/README.md`
5. `independent_recompute_minipack/recompute_from_raw.py`
