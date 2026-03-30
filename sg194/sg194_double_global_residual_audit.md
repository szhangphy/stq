# SG194 Double Global Residual Audit

## What remains after removing the trusted sector

- full 33-generator decomposition completed: `True`
- trusted sector common indices: `[6, 7, 8, 9, 10, 11, 12, 13, 14, 25]`
- complement common indices: `[0, 1, 2, 3, 4, 5, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32]`

## Complement-only exact comparison

- current rank: `9`
- external rank: `7`
- union rank: `12`
- intersection rank: `4`
- current-only dimension: `5`
- external-only dimension: `3`

## Complement lift

- complement lift exists: `False`
- rational lift exists: `False`
- obstruction kind: `row_space_containment_failure`

## Residual mismatch localization

- family-local residual families: `[]`
- current witness row blocks: `['P1']`
- external witness row blocks: `['A', 'Γ']`
- residual classification: `wrong_ambient_space_construction_or_missing_complement_row_basis_translation`

## Next patch target

- source file: `debug_workflow_portability_stage2_194.1.1.1.py`
- function: `build_sg194_double_spinorial_generators`
- patch type: `another_generator_construction_patch_with_complement_specific_row_basis_translation`
