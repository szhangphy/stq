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

- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 33 induced local objects satisfy compatibility on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 22, 'compatible_on_publication_shell': 11, 'induction_failure_on_raw42': 12}. 22 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 48}. The remaining induction failures are concentrated on manifold P4 across families ['c', 'd'] (count=12). Nonzero residuals on the publication shell are concentrated on PPATH06 rows [19, 20, 21, 22, 23, 24].

## Controlled-Case Verdict

- controlled_case_valid = `True`
- single_group_portable = `True`
- double_group_portable_seed = `True`
