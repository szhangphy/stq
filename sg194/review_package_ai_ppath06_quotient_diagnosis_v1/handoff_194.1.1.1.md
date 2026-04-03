# Handoff for 194.1.1.1

- Current target group: `194.1.1.1`
- Single-group status: `partial_ai_lattice` with BS `success`.
- Double-group status: minimal prototype `success`, backbone `success`.
- Main blocker: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are cleared by the manifold character-field conversion patch. Independent validation status: P4 bug independently validated and repaired at the manifold_character_field_conversion stage. Current P4 verdict: proved_bug. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24]. The residual sector contributes quotient rank 5 after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank 5.
- Next unique target: finish published-shell AI induction/completion so the validated local irrep/corep libraries become an honest AI lattice and quotient on 194.1.1.1.
- Files to read first:
  - controlled_case_audit_194.1.1.1.md
  - workflow_portability_audit_194.1.1.1.md
  - group_194_1_1_1_single_pilot_audit.md
  - group_194_1_1_1_double_pilot_audit.md
  - workflow_portability_report_194.1.1.1.pdf
