# AI Obstruction Diagnosis Report

- Published object kind: `publication_level_point_path_shell_v1`.
- AI induction character field: `point=character, line=character, plane=character, default=character`.
- Row-language full-span / Bilbao-equivalent final-object pass: `True` / `True`.
- Internal vs publication selected path counts: `8` / `7`.
- Internal vs publication path pairs: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]` / `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.
- Shell matrix shapes: `{'raw42': [61, 42], 'internal_shell': [33, 34], 'publication_shell': [29, 34]}`.
- Candidate counts: `{'raw42_success': 33, 'raw42_failures': 12, 'internal_shell_success': 33, 'internal_shell_failures': 12, 'publication_shell_success': 33, 'publication_shell_failures': 12}`.
- Compatibility-zero counts: `{'raw42': 11, 'internal_shell': 11, 'publication_shell': 11}`.
- Classification counts: `{'fails_on_raw42': 22, 'compatible_on_publication_shell': 11, 'induction_failure_on_raw42': 12}`.
- Family counts by classification: `{'compatible_on_publication_shell': {'a': 2, 'e': 3, 'f': 3, 'j': 2, 'l': 1}, 'fails_on_raw42': {'a': 4, 'b': 6, 'g': 4, 'h': 4, 'i': 2, 'k': 2}, 'induction_failure_on_raw42': {'c': 6, 'd': 6}}`.
- Publication residual path histogram: `{'PPATH06': 48}`.
- Publication residual row histogram: `{'22': 20, '23': 20, '24': 8}`.
- Obstruction summary: 22 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 48}.
