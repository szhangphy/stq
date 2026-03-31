# Review Package: SG194 Stage-2 Closeout Followup v3

## Scope

- Reference group: `10.4.1.31`.
- Fixed target group: `194.1.1.1`.
- Goal: make the final-standard-space closeout auditable, reproducible, self-contained, and packageable.

## Closeout Content

- SG 194 site-symmetry inventory on the fixed second group.
- Single-group local-irrep library for the real SG 194 site-symmetry types.
- Double-group projective local-irrep library under `factor_su2`.
- Recomputed single-group and double-group AI / raw-internal quotient summaries on `194.1.1.1`.
- Formal stage-2 PDF technical report plus handoff / status / next-step files.
- Direct runtime dependencies for the authoritative stage-2 scripts, including the stage1 portability driver and local common runtime subtree.
- Reproducibility manifest plus extracted-package smoke-test commands.

## Interpretation Boundary

- The extracted quotient files are raw internal BS-space quotients.
- The raw internal quotient is still preserved as provenance.
- The final SG194 ordinary standard quotient is now implemented through an externally anchored current-to-standard elimination contract.
- `single_vs_external_union_rank_in_current_point_rows = 17` and `double_vs_external_union_rank_in_current_point_rows = 17` mean the external ordinary span is not already the same ambient subspace as the current 34-row span; this package does not claim an internal row-space identity proof.
- Any legacy BS-vs-AI separation material in this package is included as historical reference only, not as active current evidence.

## Read-Only / Rerun Boundary

- Supported and smoke-tested inside the extracted package: `python3 debug_sg194_standard_space_projection_v1.py --validate` and `python3 debug_workflow_portability_stage2_194.1.1.1.py --validate`.
- Full reruns are package-local and may overwrite package-local outputs; see `REPRODUCIBILITY_MANIFEST.md` and `reproducibility_manifest_v1.json` for the direct dependency map and expected outputs.

## Suggested Review Order

1. `sg194_standard_space_projection_summary_v1.json`
2. `sg194_current_to_standard_row_translation_v1.json`
3. `workflow_portability_stage2_summary_194.1.1.1.json`
4. `current_status_194.1.1.1_stage2.json`
5. `workflow_portability_report_stage2_194.1.1.1.pdf`
6. `REPRODUCIBILITY_MANIFEST.md`
7. `group_194_1_1_1_single_ai_completion_summary.json`
8. `group_194_1_1_1_double_ai_completion_summary.json`
9. `debug_sg194_standard_space_projection_v1.py`
10. `debug_workflow_portability_stage2_194.1.1.1.py`

## Package Tree

```text
review_package_sg194_stage2_closeout_followup_v3/
  - README.md
  - REPRODUCIBILITY_MANIFEST.md
  - SG_utils.py
  - SSGReps.py
  common/
    SSGReps/
      SSGReps/
        - SG_utils.py
        - SSGReps.py
        - rep_utils.py
      ssg_data/
        - identify.pkl.tar.gz
    - debug_single_group_ai_bridge.py
    - debug_single_group_ai_expanded.py
  - controlled_case_audit_194.1.1.1.md
  - current_status_194.1.1.1.json
  - current_status_194.1.1.1_stage2.json
  - current_status_sg194_1941111_bs_ai_bug_audit_v1.json
  - current_status_sg194_bs_ai_separation.json
  - debug_sg194_nonabelian_local_library.py
  - debug_sg194_stage2_package_dependency_audit_v1.py
  - debug_sg194_standard_space_projection_v1.py
  - debug_workflow_portability_194.1.1.1.py
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
  - group_194_1_1_1_double_bs_analysis.json
  - group_194_1_1_1_double_indicator_generators.json
  - group_194_1_1_1_double_indicator_group_summary.json
  - group_194_1_1_1_double_pilot_audit.md
  - group_194_1_1_1_double_pilot_summary.json
  - group_194_1_1_1_single_ai_completion_summary.json
  - group_194_1_1_1_single_bs_analysis.json
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
  - reproducibility_manifest_v1.json
  - sg194_1941111_bs_ai_bug_audit_report_v1.md
  - sg194_1941111_bs_ai_bug_audit_summary_v1.json
  - sg194_bs_ai_separation_report.md
  - sg194_bs_ai_separation_summary.json
  - sg194_current_point_space_snapshot_v1.json
  - sg194_current_to_standard_row_translation_v1.json
  - sg194_double_local_corep_library.json
  - sg194_external_ordinary_generator_matrix.json
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
