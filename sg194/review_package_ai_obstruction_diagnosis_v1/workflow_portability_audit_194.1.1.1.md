# Workflow Portability Audit for 194.1.1.1

## Reference Workflow Decomposition

- k-space geometry / connectivity generation.
- little-group capture via `SSGReps.load_little_group(...)`.
- character-based compatibility assembly.
- BS construction as `ker_Z(C)`.
- real-space bridge and atomic induction.
- AI completeness and quotient extraction.

## Reusable Modules

- Controlled-case spatial identification.
- Real-space / k-space geometry extraction from `swyckoff_{r,k}.py`.
- Character-based restriction matching for both `groupType=1` and `groupType=2`.
- Integer-kernel BS construction.
- Spatial bridge plus Bloch-phase induction.

## Modules Still Group-Specific

- Boundary-manifold closure: 194.1.1.1 requires synthetic 0D boundary points that were unnecessary on 10.4.1.31.
- Published-shell integration of the validated SG 194 local irrep / corep libraries.
- Honest AI completeness and quotient extraction on the new target.

## Current Weakest Link

- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published full-span augmented 8-path shell. Classification counts across raw42 / 7-path skeleton / published 8-path shells: {'fails_on_raw42': 34, 'compatible_on_published8': 11}. 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.

## Controlled-Case Verdict

- controlled_case_valid = `True`
- single_group_portable = `True`
- double_group_portable_seed = `True`
