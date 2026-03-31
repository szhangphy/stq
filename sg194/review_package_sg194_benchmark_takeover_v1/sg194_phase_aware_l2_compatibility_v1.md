# SG194 Phase-Aware L2 Compatibility v1

## Current Builder Object

- line id: `L2`
- compatibility input: `phase_stripped_character`
- line-basis equation count: `3`

## Native Linear-Character Problem

- individually inconsistent reps on direct linear-character subduction: `['P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P4_R3']`
- note: The current direct linear-character solve is inconsistent on the duplicated P3 channels and on P4_R3. The v1 prototype therefore stops solving per raw irrep and first glues duplicated native restrictions into endpoint classes.

## Phase-Aware v1 Solver

- profile: `phase_aware_l2_projective_v1`
- selected duplicated endpoint: `P3`
- refinement equation count: `3`
- solver interpretation: Use native linear-character restrictions on L2, group identical duplicated endpoint channels into projective classes, and add equality rows inside the selected duplicated endpoint before the legacy line-basis matching is applied.

### Selected Endpoint Classes

- `['P3_R1', 'P3_R4']` -> raw line decomposition `{'L2_R2': 1}`
- `['P3_R2', 'P3_R3']` -> raw line decomposition `{'L2_R1': 1}`
- `['P3_R5', 'P3_R6']` -> raw line decomposition `{'L2_R3': 1}`

## Local Validation

- current single/double raw rank(BS): `16` / `16`
- refined single/double raw rank(BS): `13` / `13`
- surviving common free generators after refinement: `0`
