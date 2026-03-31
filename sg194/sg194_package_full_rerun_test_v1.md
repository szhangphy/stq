# SG194 Package Full Rerun Test v1

## Package Under Test

- tarball = `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/review_package_sg194_stage2_closeout_followup_v3.tar.gz`
- extracted package root = `/tmp/sg194_pkg_full_rerun_v1_w8j6b1fl/review_package_sg194_stage2_closeout_followup_v3`
- all passed = `True`

## Commands

- `python3 debug_sg194_standard_space_projection_v1.py`
  - passed = `True`
  - returncode = `0`
  - duration_seconds = `197.731`
  - output = `generated standard-space projection for 194.1.1.1: single rank(BS/AI)=13/13, double rank(BS/AI)=13/13`
- `python3 debug_workflow_portability_stage2_194.1.1.1.py`
  - passed = `True`
  - returncode = `0`
  - duration_seconds = `188.157`
  - output = `- workflow_portability_stage2_summary_194.1.1.1.json`

## Output Checks

- `sg194_standard_space_projection_summary_v1.json` -> `True`
- `group_194_1_1_1_single_ai_completion_summary.json` -> `True`
- `group_194_1_1_1_double_ai_completion_summary.json` -> `True`
- `workflow_portability_stage2_summary_194.1.1.1.json` -> `True`
- `current_status_194.1.1.1_stage2.json` -> `True`
- `workflow_portability_report_stage2_194.1.1.1.tex` -> `True`
- `workflow_portability_report_stage2_194.1.1.1.pdf` -> `True`

## Result Checks

- summary = `{'single_raw_rank_bs': 16, 'single_raw_quotient_group': 'Z^3', 'single_final_rank_bs': 13, 'single_final_rank_ai': 13, 'single_final_quotient_group': 'trivial', 'double_raw_rank_bs': 16, 'double_raw_quotient_group': 'Z^3', 'double_final_rank_bs': 13, 'double_final_rank_ai': 13, 'double_final_quotient_group': 'trivial', 'projection_status': 'implemented', 'projection_contract_type': 'common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators', 'stage2_standard_projection_status': 'implemented'}`
