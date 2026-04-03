# AI Obstruction Diagnosis Report

- Published object kind: `automatic_reduced_final_point_path_shell_v3_fullspan_augmented`.
- AI induction character field: `point=linear_character, line=character, plane=character, default=linear_character`.
- Row-language full-span / Bilbao-equivalent final-object pass: `True` / `False`.
- Selected path count / unique endpoint-pair count: `8` / `7`.
- Actual path pairs: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.
- Augmentation path ids / row indices: `['FPATH04']` / `[14, 15, 16, 17]`.
- Shell matrix shapes: `{'raw42': [61, 42], 'skeleton7': [29, 34], 'published8': [33, 34]}`.
- Candidate counts: `{'raw42_success': 45, 'raw42_failures': 0, 'skeleton7_success': 45, 'skeleton7_failures': 0, 'published8_success': 45, 'published8_failures': 0}`.
- Compatibility-zero counts: `{'raw42': 11, 'skeleton7': 11, 'published8': 11}`.
- Classification counts: `{'fails_on_raw42': 34, 'compatible_on_published8': 11}`.
- Family counts by classification: `{'compatible_on_published8': {'a': 2, 'e': 3, 'f': 3, 'j': 2, 'l': 1}, 'fails_on_raw42': {'a': 4, 'b': 6, 'c': 6, 'd': 6, 'g': 4, 'h': 4, 'i': 2, 'k': 2}}`.
- Published residual path histogram: `{'FPATH07': 68}`.
- Published residual row histogram: `{'26': 24, '27': 24, '28': 20}`.
- Obstruction summary: 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.
