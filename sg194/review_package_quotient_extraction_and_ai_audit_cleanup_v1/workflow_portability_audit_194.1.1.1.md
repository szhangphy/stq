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
- Published-shell double-group integration of the validated SG 194 local irrep / corep libraries.
- Honest double-group AI completeness and quotient extraction on the new target remain unresolved.

## Current Weakest Link

- Non-abelian SG 194 projective local-corep libraries already exist and validate, but the published-shell double AI induction path is not yet wired beyond the current trivial-stabilizer witness.

## Controlled-Case Verdict

- controlled_case_valid = `True`
- single_group_portable = `True`
- double_group_portable_seed = `True`
