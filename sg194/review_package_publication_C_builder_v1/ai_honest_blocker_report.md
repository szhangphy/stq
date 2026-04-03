# AI Honest Blocker Report

- Status: `blocked`.
- Blocker stage: `published_shell_obstruction_diagnosis`.
- Local library present / wired: `True` / `True`.
- Failure count: `12`.
- Nonzero-residual candidate count: `22`.
- Failure family ids: `['c', 'd']`.
- Blocker: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 33 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 22, 'compatible_on_publication_shell': 11, 'induction_failure_on_raw42': 12}. 22 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 48}.
