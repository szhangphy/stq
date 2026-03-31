# SG194 Repo Consistency Closeout Verification v1

- Time: 2026-03-31 16:47:00 +0800
- Repo: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Branch: `sg194-special`

## Required verification results

1. `python3 -m py_compile common/*.py`
   - passed
2. `python3 -m py_compile sg194/*.py`
   - passed
   - non-fatal warning retained: `debug_sg194_bs_ai_separation.py` still emits the known invalid-escape `SyntaxWarning`
3. blocked-import verification for repo-top and vendored `SG_utils` / `rep_utils` / `SSGReps`
   - passed
   - verified under active `spglib` / `pymatgen` import blocking:
     - repo-top `SG_utils`, `rep_utils`, `SSGReps`
     - vendored `common/SSGReps/SSGReps/SG_utils`, `rep_utils`, `SSGReps`
4. `python3 sg194/debug_sg194_bs_ai_separation.py`
   - passed
5. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
   - passed
6. `python3 sg194/debug_sg194_double_patch.py`
   - passed
7. `python3 sg194/debug_sg194_double_complement_patch_v1.py`
   - passed

## Extra validation

1. `python3 sg194/debug_sg194_bs_ai_separation.py --validate`
   - passed: `validation_ok`
2. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`
   - passed: `validated workflow portability stage-2 outputs`
3. stage2 tar-member spot check
   - confirmed `README.md`, `SG_utils.py`, `SSGReps.py`, `rep_utils.py`, `current_status_sg194_bs_ai_separation.json`, and `workflow_portability_stage2_summary_194.1.1.1.json`
4. bs\_ai tar-member spot check
   - confirmed `README.md`, `SG_utils.py`, `SSGReps.py`, `rep_utils.py`, `current_status_sg194_bs_ai_separation.json`

## Semantic checkpoints

1. Stage2 authoritative outputs still report `raw_internal_quotient_group = Z^3`, `quotient_group = null`, and `standard_space_projection_status = missing`.
2. Stage2 key matrix shape is `[58, 42]`, rank `26`, nullity `16`.
3. bs\_ai separation is marked `legacy_stale_reference`.
4. bs\_ai summary/status/package now point to the stage2 closeout outputs as the current authoritative SG194 evidence path.
