# SG194 194.1.1.1 Source BS Fix Live Checkpoint

        - Current time: 2026-04-01 05:25:45 +0800
        - Branch: `sg194-special`
        - Current HEAD: `4720edc`
        - Repo root (relative): `.`
        - Remote: `git@github.com:szhangphy/stq.git`
        - Current subtask: keep the published source BS aligned to the accepted benchmark while rebuilding the internal current-to-benchmark map

        ## Accepted hard facts

        1. The published source workflow now reports `rank(BS)=10`, `rank(AI)=10`, final quotient `Z6` for both single and double.
        2. The legacy internal reduced layer is still `13/13/trivial` and is retained only as provenance.
        3. The implementation is an externally anchored current-to-standard elimination contract, not an internal ambient row-space identity proof.
        4. Both single and double have external-union rank `17` inside current point rows, so the external ordinary standard layer must remain externally anchored.
        5. The source-BS review package carries dependency audit and reproducibility manifest files, plus extracted-package smoke-test evidence.

        ## Read First

        1. `sg194/sg194_standard_space_projection_summary_v1.json`
2. `sg194/current_status_194.1.1.1_stage2.json`
3. `sg194/workflow_portability_stage2_summary_194.1.1.1.json`
4. `sg194/workflow_portability_report_stage2_194.1.1.1.pdf`
5. `sg194/review_package_sg194_source_bs_fix_v1/REPRODUCIBILITY_MANIFEST.md`
6. `sg194/sg194_stage2_package_dependency_audit_v1.md`
7. `sg194/sg194_package_smoke_test_v1.md`

        ## Immediate Next Step

        1. Review the git diff for in-scope source-BS benchmark-adoption changes only.
2. Commit on sg194-special.
3. Push origin/sg194-special.
