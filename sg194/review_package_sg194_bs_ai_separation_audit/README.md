# SG194 BS-vs-AI Separation Audit

This package contains the separated SG194 audit for `194.1.1.1`, explicitly correcting the previous `external_matrix_final` object confusion.
It is retained as a **legacy/stale reference** and must not be cited as the live current-snapshot SG194 point-space audit.

## Scope
- target group: `194.1.1.1`
- task: separate `AI-vs-external` from `BS-vs-external`
- analysis_status: `legacy_stale_reference`
- current repo point blocks: `P1, P2, P3, P4, P5, P6`
- legacy internal selection blocks used here: `P1, P2, P3, P5, P6, B1`

## Main outputs
- `sg194_single_ai_vs_external.json`
- `sg194_single_bs_vs_external.json`
- `sg194_double_ai_vs_external.json`
- `sg194_double_bs_vs_external.json`
- `sg194_bs_ai_separation_summary.json`

## Current-status warning
- this package is historical reference only
- if a reviewer needs current SG194 evidence, they must use the current stage2 closeout outputs instead
- current authoritative note: Current authoritative SG194 evidence now lives in the stage2 closeout outputs, not in this legacy/stale BS-vs-AI separation package.
- current authoritative outputs:
  - `workflow_portability_report_stage2_194.1.1.1.pdf`
  - `workflow_portability_stage2_summary_194.1.1.1.json`
  - `current_status_194.1.1.1_stage2.json`
  - `handoff_194.1.1.1_stage2.md`
  - `review_package_sg194_stage2_closeout_followup_v2.tar.gz`

## SG194 BS-vs-AI separation report
- report file: `sg194_bs_ai_separation_report.pdf`
- report source: `sg194_bs_ai_separation_report.tex`
- suggested reading order:
  1. PDF report
  2. single AI vs external
  3. single BS vs external
  4. double AI vs external
  5. double BS vs external
