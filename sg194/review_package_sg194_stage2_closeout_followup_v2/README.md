# Review Package: SG194 Stage-2 Closeout Followup v2

## Scope

- Reference group: `10.4.1.31`.
- Fixed target group: `194.1.1.1`.
- Goal: keep the current stage-2 outputs, checkpoints, README, and review package aligned on the raw-vs-standard quotient boundary.

## Closeout Content

- SG 194 site-symmetry inventory on the fixed second group.
- Single-group local-irrep library for the real SG 194 site-symmetry types.
- Double-group projective local-irrep library under `factor_su2`.
- Recomputed single-group and double-group AI / raw-internal quotient summaries on `194.1.1.1`.
- Formal stage-2 PDF technical report plus handoff / status / next-step files.
- Rolling closeout checkpoints for the SG194 repo-consistency followup.
- Legacy/stale status files for the separate BS-vs-AI audit, so reviewers do not mistake it for current-snapshot evidence.

## Interpretation Boundary

- The extracted quotient files are raw internal BS-space quotients.
- The raw internal quotient is still preserved as provenance.
- The final SG194 ordinary standard quotient is now implemented through the explicit current-to-standard elimination contract.
- Any legacy BS-vs-AI separation material in this package is included as historical reference only, not as active current evidence.

## Suggested Review Order

1. `workflow_portability_report_stage2_194.1.1.1.pdf`
2. `sg194_standard_space_projection_summary_v1.json`
3. `sg194_current_to_standard_row_translation_v1.json`
4. `sg194_nonabelian_site_symmetry_inventory.md`
5. `workflow_portability_stage2_audit_194.1.1.1.md`
6. `workflow_portability_stage2_summary_194.1.1.1.json`
7. `group_194_1_1_1_single_ai_completion_summary.json`
8. `group_194_1_1_1_double_ai_completion_summary.json`
9. `handoff_sg194_1941111_bs_ai_bug_audit_v1.md`
10. `current_status_sg194_1941111_bs_ai_bug_audit_v1.json`

## Stage-2 PDF Report

- Report file: `workflow_portability_report_stage2_194.1.1.1.pdf`
- Report source: `workflow_portability_report_stage2_194.1.1.1.tex`
- Recommended order: read the PDF first, then the JSON / audit files.

## Package Tree

```text
review_package_sg194_stage2_closeout_followup_v2/
  - README.md
  - SG_utils.py
  - SSGReps.py
  - controlled_case_audit_194.1.1.1.md
  - current_status_194.1.1.1.json
  - current_status_194.1.1.1_stage2.json
  - current_status_sg194_1941111_bs_ai_bug_audit_v1.json
  - current_status_sg194_bs_ai_separation.json
  - debug_sg194_nonabelian_local_library.py
  - debug_sg194_standard_space_projection_v1.py
  - debug_workflow_portability_stage2_194.1.1.1.py
  - double_group_ai_completeness_audit_10.4.1.31.md
  - double_group_ai_completeness_summary_10.4.1.31.json
  - double_group_bs_basis_pretty_10.4.1.31.json
  - double_group_bs_basis_raw_10.4.1.31.json
  - double_group_bs_mod_ai_summary_10.4.1.31.json
  - double_group_bs_summary_10.4.1.31.json
  - double_group_full_compatibility_with_planes_10.4.1.31.json
  - double_group_indicator_generators_10.4.1.31.json
  - double_group_indicator_group_summary_10.4.1.31.json
  - group_194_1_1_1_double_ai_completion_summary.json
  - group_194_1_1_1_double_indicator_generators.json
  - group_194_1_1_1_double_indicator_group_summary.json
  - group_194_1_1_1_double_pilot_audit.md
  - group_194_1_1_1_double_pilot_summary.json
  - group_194_1_1_1_single_ai_completion_summary.json
  - group_194_1_1_1_single_indicator_generators.json
  - group_194_1_1_1_single_indicator_group_summary.json
  - group_194_1_1_1_single_pilot_audit.md
  - group_194_1_1_1_single_pilot_summary.json
  - handoff_194.1.1.1.md
  - handoff_194.1.1.1_stage2.md
  - handoff_sg194_1941111_bs_ai_bug_audit_v1.md
  - handoff_sg194_bs_ai_separation.md
  - live_checkpoint_sg194_1941111.json
  - live_checkpoint_sg194_1941111.md
  - next_step_prompt_194.1.1.1.txt
  - next_step_prompt_194.1.1.1_stage2.txt
  - next_step_prompt_sg194_1941111_bs_ai_bug_audit_v1.txt
  - next_step_prompt_sg194_bs_ai_separation.txt
  - rep_utils.py
  - sg194_1941111_bs_ai_bug_audit_report_v1.md
  - sg194_1941111_bs_ai_bug_audit_summary_v1.json
  - sg194_bs_ai_separation_report.md
  - sg194_bs_ai_separation_summary.json
  - sg194_current_point_space_snapshot_v1.json
  - sg194_current_to_standard_row_translation_v1.json
  - sg194_double_local_corep_library.json
  - sg194_final_bs_ai_closeout_next_step_prompt_v1.txt
  - sg194_final_bs_ai_closeout_report_v1.md
  - sg194_final_bs_ai_closeout_status_v1.json
  - sg194_nonabelian_site_symmetry_inventory.json
  - sg194_nonabelian_site_symmetry_inventory.md
  - sg194_single_local_irrep_library.json
  - sg194_standard_space_projection_summary_v1.json
  - single_group_ai_completeness_audit.md
  - single_group_ai_completeness_summary.json
  - single_group_bs_mod_ai_single_summary.json
  - single_group_indicator_generators.json
  - single_group_indicator_group_summary.json
  - swyckoff_k.py
  - swyckoff_r.py
  - workflow_portability_report_stage2_194.1.1.1.pdf
  - workflow_portability_report_stage2_194.1.1.1.tex
  - workflow_portability_stage2_audit_194.1.1.1.md
  - workflow_portability_stage2_summary_194.1.1.1.json
  - workflow_portability_summary_194.1.1.1.json
```
