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
- First local solution: `{'endpoint_relabel': {'P1': {'P1_R1': 'P1_R3', 'P1_R2': 'P1_R4', 'P1_R3': 'P1_R1', 'P1_R4': 'P1_R2'}, 'P5': {'P5_R1': 'P5_R3', 'P5_R2': 'P5_R4', 'P5_R3': 'P5_R1', 'P5_R4': 'P5_R2'}}, 'broken_selected_path_ids': ['FPATH01', 'FPATH02', 'FPATH03', 'FPATH08'], 'preserves_other_selected_shell': False}`.
- First shell-preserving solution: `None`.
- Selected-shell preservation was checked against: `['FPATH01', 'FPATH02', 'FPATH03', 'FPATH05', 'FPATH06', 'FPATH07', 'FPATH08']`.
- Resolution status: `both_retained_honest_8_path`.
- Resolution reason: A local P1/P5 endpoint relabel can map the augmentation class into the skeleton class, but every such relabel breaks the row language of other selected paths. The class split is therefore not globally collapsible on the published shell.
