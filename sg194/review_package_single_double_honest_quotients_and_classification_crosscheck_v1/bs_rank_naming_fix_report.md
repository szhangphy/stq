# BS Rank Naming Fix Report

- Old misleading fields: `{'BS_status.rank': 'compatibility_matrix_rank', 'BS_status.nullity': 'compatibility_matrix_nullity', 'current_status.key_matrices.single_rank': 'single_compatibility_matrix_rank', 'current_status.key_matrices.single_nullity': 'single_compatibility_matrix_nullity'}`.
- New authoritative fields: `{'compatibility_matrix_shape': [29, 34], 'compatibility_matrix_rank': 24, 'compatibility_matrix_nullity': 10, 'bs_rank': 10, 'double_compatibility_matrix_shape': None, 'double_compatibility_matrix_rank': None, 'double_compatibility_matrix_nullity': None, 'double_bs_rank': None}`.
- Updated files: `['group_194_1_1_1_single_pilot_summary.json', 'current_status_194.1.1.1.json', 'group_194_1_1_1_single_pilot_audit.md', 'next_step_prompt_194.1.1.1.txt']`.
- Reading rule: Read compatibility-matrix rank/nullity from the published C_pub matrix analysis. Read BS rank from the compatibility-matrix nullity.
