# Handoff for 194.1.1.1

- Current target group: `194.1.1.1`
- Single-group status: `seed_only` with BS `success`.
- Double-group status: minimal prototype `success`, backbone `success`.
- Main blocker: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published full-span augmented 8-path shell. Classification counts across raw42 / 7-path skeleton / published 8-path shells: {'fails_on_raw42': 34, 'compatible_on_published8': 11}. 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.
- Next unique target: finish published-shell AI induction/completion so the validated local irrep/corep libraries become an honest AI lattice and quotient on 194.1.1.1.
- Files to read first:
  - controlled_case_audit_194.1.1.1.md
  - workflow_portability_audit_194.1.1.1.md
  - group_194_1_1_1_single_pilot_audit.md
  - group_194_1_1_1_double_pilot_audit.md
  - workflow_portability_report_194.1.1.1.pdf
