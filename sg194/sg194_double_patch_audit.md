# SG194 Double Patch Audit

## Real Bug Source

- real patched source file: `debug_workflow_portability_stage2_194.1.1.1.py`
- raw artifact writer only: `debug_raw_matrix_audit.py`
- audit/alignment consumers only: `debug_sg194_standard_alignment.py`, `debug_sg194_standard_alignment_v2.py`, `debug_sg194_bs_ai_separation.py`, `debug_sg194_mismatch_localization.py`

## What Was Actually Patched

- The stage-2 double path now constructs SG194 spinorial current generators directly.
- The new patched profile is `sg194_double_anchor_patch_v1`.
- This patch is source-level, not an audit-only post-hoc override.

## Exact Outcome

- problem-sector union rank: `8 -> 6`
- problem-sector intersection rank: `4 -> 6`
- `delta_c1_minus_b1` disappeared: `False`
- `delta_d1_minus_b1` disappeared: `False`
- full current rank in the 33-column comparison: `12 -> 12`

## Diagnosis

- The exact trusted SG194 double mismatch in `2b/2c/2d/6h` is removed by the patched stage-2 builder.
- The hoped-for global `12 -> 10` collapse is not reached yet, so a BS-only rerun is still premature.
- The next blocker is no longer “find the bug source”; it is “finish the all-sector current-to-external spinorial row-language canonicalization after the patched problem sector has been fixed”.
