# SG194 194.1.1.1 Internalization Fix Handoff v1

        - Current time: 2026-04-01 06:36:58 +0800
        - Branch: `sg194-special`
        - Current HEAD: `3538eca`
        - Repo root (relative): `.`
        - Remote: `git@github.com:szhangphy/stq.git`
        - Current subtask: keep the benchmark-facing SG194 result sourced by the internalized double spinorial path while cleaning historical adoption-era leftovers

        ## Accepted hard facts

        1. The active benchmark-facing SG194 result now reports `rank(BS)=10`, `rank(AI)=10`, final quotient `Z6`.
        2. The historical internal reduced layer is still `13/13/trivial`, but it is retained only as provenance.
        3. The implementation still keeps the externally anchored current-to-standard elimination contract for the historical ordinary-language projection; that contract is no longer the active benchmark layer.
        4. The active benchmark layer is now tied to the source-computed double spinorial 33-generator internalization path.
        5. The review package carries dependency audit and reproducibility manifest files, plus extracted-package smoke-test evidence.

        ## Read First

        1. `sg194/sg194_standard_space_projection_summary_v1.json`
2. `sg194/current_status_194.1.1.1_stage2.json`
3. `sg194/workflow_portability_stage2_summary_194.1.1.1.json`
4. `sg194/workflow_portability_report_stage2_194.1.1.1.pdf`
5. `sg194/review_package_sg194_internalization_fix_v1/REPRODUCIBILITY_MANIFEST.md`
6. `sg194/sg194_stage2_package_dependency_audit_v1.md`
7. `sg194/sg194_package_smoke_test_v1.md`

        ## Immediate Next Step

        1. Review the git diff for in-scope source internalization and cleanup changes only.
2. Commit on sg194-special.
3. Push origin/sg194-special.
