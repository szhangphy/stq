# PPATH06 Residual Obstruction Audit

- Raw/internal/publication chain: `L2` -> `FPATH07` -> `PPATH06`.
- Endpoint pair: `['P3', 'P4']`.
- Row indices: `{'raw42': [6, 7, 8, 9, 10, 11], 'internal_shell': [23, 24, 25, 26, 27, 28], 'publication_shell': [19, 20, 21, 22, 23, 24]}`.
- Residual-support publication rows: `[22, 23, 24]`.
- Explanation: The residual support on PPATH06 is confined to rows 22/23/24, inherited directly from raw L2 via the internal FPATH07 layer. These rows are pure pair-difference constraints on P3 multiplicities, so the obstruction survives publication reduction without involving any new P4-only terms.

- publication row `19` / basis `CANDIDATE_PATH_003_R1` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R2', 'coeff': 1}, {'unknown': 'P3_R3', 'coeff': 1}, {'unknown': 'P4_R3', 'coeff': -1}]`.
- publication row `20` / basis `CANDIDATE_PATH_003_R2` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R1', 'coeff': 1}, {'unknown': 'P3_R4', 'coeff': 1}, {'unknown': 'P4_R3', 'coeff': -1}]`.
- publication row `21` / basis `CANDIDATE_PATH_003_R3` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R5', 'coeff': 1}, {'unknown': 'P3_R6', 'coeff': 1}, {'unknown': 'P4_R1', 'coeff': -1}, {'unknown': 'P4_R2', 'coeff': -1}]`.
- publication row `22` / basis `L2_phase_aware_class_01` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R1', 'coeff': 1}, {'unknown': 'P3_R4', 'coeff': -1}]`.
- publication row `23` / basis `L2_phase_aware_class_02` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R2', 'coeff': 1}, {'unknown': 'P3_R3', 'coeff': -1}]`.
- publication row `24` / basis `L2_phase_aware_class_03` / row_kind `line_basis_decomposition` / source line `L2` / terms `[{'unknown': 'P3_R5', 'coeff': 1}, {'unknown': 'P3_R6', 'coeff': -1}]`.
