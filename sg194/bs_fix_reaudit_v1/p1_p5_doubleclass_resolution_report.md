# P1-P5 Double-Class Resolution Report

- Reference class/source: `PCLASS03` / `L3`.
- Candidate class/source: `PCLASS04` / `L4`.
- Line-group signatures equal: `True`.
- Local row-space signatures equal: `False`.
- Global row-space signatures equal: `False`.
- Endpoint decomposition signatures equal: `False`.
- Exhaustive local relabel search executed: `True`.
- Varying rep ids by endpoint: `{'P1': ['P1_R1', 'P1_R2', 'P1_R3', 'P1_R4'], 'P5': ['P5_R1', 'P5_R2', 'P5_R3', 'P5_R4']}`.
- Local solution count: `1`.
- Shell-preserving solution count: `0`.
- Full-shell automorphism search summary: `{'searched': True, 'reason': None, 'local_solution_count': 1, 'local_solution_search_space': 576, 'search_space_size': 8640, 'searched_candidate_count': 8640, 'compensation_points': ['P2', 'P3', 'P6'], 'point_permutation_sizes': {'P2': 6, 'P3': 720, 'P6': 2}, 'local_solution_searches': [{'local_solution_index': 1, 'search_enabled': True, 'reason': None, 'broken_path_ids': ['FPATH01', 'FPATH02', 'FPATH03', 'FPATH08'], 'varying_endpoints': ['P1', 'P5'], 'compensation_points': ['P2', 'P3', 'P6'], 'point_permutation_sizes': {'P2': 6, 'P3': 720, 'P6': 2}, 'search_space_size': 8640, 'searched_candidate_count': 8640, 'global_solution_count': 0, 'first_global_solution': None}], 'global_solution_count': 0, 'first_global_solution': None, 'all_global_solutions': []}`.
- First local solution: `{'endpoint_relabel': {'P1': {'P1_R1': 'P1_R3', 'P1_R2': 'P1_R4', 'P1_R3': 'P1_R1', 'P1_R4': 'P1_R2'}, 'P5': {'P5_R1': 'P5_R3', 'P5_R2': 'P5_R4', 'P5_R3': 'P5_R1', 'P5_R4': 'P5_R2'}}, 'broken_selected_path_ids': ['FPATH01', 'FPATH02', 'FPATH03', 'FPATH08'], 'preserves_other_selected_shell': False}`.
- First shell-preserving solution: `None`.
- First global shell solution: `None`.
- Selected-shell preservation was checked against: `['FPATH01', 'FPATH02', 'FPATH03', 'FPATH05', 'FPATH06', 'FPATH07', 'FPATH08']`.
- Resolution status: `both_retained_honest_8_path`.
- Resolution reason: A local P1/P5 endpoint relabel can map the augmentation class into the skeleton class, but no full-shell automorphism witness extends that relabel across the rest of the selected shell. The class split is therefore not globally collapsible on the published shell.
