# SG194 Residual Audits

## SG194 stage2 closeout followup v2

- package file: `review_package_sg194_stage2_closeout_followup_v2.tar.gz`
- package directory: `review_package_sg194_stage2_closeout_followup_v2/`
- current contract:
  - the stage2 quotient fields are raw internal BS-space quotients
  - final SG194 standard quotient is still missing and must remain reported as missing
  - current local stage2 completion summaries use `rank_bs = 16`, `raw_internal_quotient_group = Z^3`, and `quotient_group = null`
- recommended reading order:
  - `workflow_portability_report_stage2_194.1.1.1.pdf`
  - `workflow_portability_stage2_summary_194.1.1.1.json`
  - `group_194_1_1_1_single_ai_completion_summary.json`
  - `group_194_1_1_1_double_ai_completion_summary.json`
  - `handoff_sg194_1941111_bs_ai_bug_audit_v1.md`
  - `current_status_sg194_1941111_bs_ai_bug_audit_v1.json`

## SG194 BS-vs-AI separation legacy reference

- status: `legacy_stale_reference`
- this audit must not be cited as current-snapshot SG194 evidence
- reason:
  - current repo point blocks are `P1..P6`
  - the retained legacy audit still uses `P1/P2/P3/P5/P6/B1`
  - it remains useful only for the historical AI-vs-BS object-separation diagnosis
- if someone wants to reuse it honestly, they must rebuild it on the current point-space rather than reusing the legacy outputs

## SG194 double lift report

- report file: `sg194_double_lift_report.pdf`
- report source file: `sg194_double_lift_report.tex`
- recommended reading order:
  - `sg194_double_lift_report.pdf`
  - `sg194_double_problem_sector_inventory.json`
  - `sg194_double_problem_sector_lift.json`
  - `sg194_double_delta_external_verdict.json`
  - `sg194_double_patch_verdict_v3.json`

## SG194 double global residual report

- report file: `sg194_double_global_residual_report.pdf`
- report source file: `sg194_double_global_residual_report.tex`
- recommended reading order:
  - `sg194_double_global_residual_report.pdf`
  - `sg194_double_global_decomposition.json`
  - `sg194_double_complement_lift.json`
  - `sg194_double_complement_mismatch_localization.json`
  - `sg194_double_next_patch_target.json`

## SG194 double complement patch report v1

- report file: `sg194_double_complement_patch_report_v1.pdf`
- report source file: `sg194_double_complement_patch_report_v1.tex`
- recommended reading order:
  - `sg194_double_complement_patch_report_v1.pdf`
  - `sg194_double_complement_rule_solve_v1.json`
  - `sg194_double_complement_patch_summary_v1.json`
  - `raw_194_1_1_1_double_ai_candidates_patched_v2.json`
