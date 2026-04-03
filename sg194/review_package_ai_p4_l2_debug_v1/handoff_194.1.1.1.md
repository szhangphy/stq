# Handoff for 194.1.1.1

- Current target group: `194.1.1.1`
- Single-group status: `partial_ai_lattice` with BS `success`.
- Double-group status: minimal prototype `success`, backbone `success`.
- Main blocker: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 33 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 22, 'compatible_on_publication_shell': 11, 'induction_failure_on_raw42': 12}. 22 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 48}. The remaining induction failures are concentrated on manifold P4 across families ['c', 'd'] (count=12). Nonzero residuals on the publication shell are concentrated on PPATH06 rows [19, 20, 21, 22, 23, 24].
- Next unique target: finish published-shell AI induction/completion so the validated local irrep/corep libraries become an honest AI lattice and quotient on 194.1.1.1.
- Files to read first:
  - controlled_case_audit_194.1.1.1.md
  - workflow_portability_audit_194.1.1.1.md
  - group_194_1_1_1_single_pilot_audit.md
  - group_194_1_1_1_double_pilot_audit.md
  - workflow_portability_report_194.1.1.1.pdf
