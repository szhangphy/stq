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

- Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects are currently explicit compatibility-zero generators on the publication-level shell. Classification counts across raw42 / internal honest shell / publication shell: {'fails_on_raw42': 34, 'compatible_on_publication_shell': 11}. 34 candidates already fail on the diagnostic raw42 shell before any internal/publication reduction is applied. No candidate first fails on the internal full-span 8-path shell before publication reduction. No candidate first fails on the publication shell after passing the internal shell. On the publication shell the nonzero residual rows concentrate on path histogram {'PPATH06': 68}. The earlier P4 induction failures are removed in the current SG194/P-lattice setting by a conversion numerically consistent with the present capture conventions. Claim scope: For SG194 in the current P-lattice setting, the earlier P4 mismatch is removed by a conversion numerically consistent with the present capture conventions. This is not promoted to a basis-independent global theorem.. Current P4 verdict: setting_specific_fix_confirmed. Nonzero residuals on the publication shell are concentrated on PPATH06 rows [22, 23, 24]. The residual sector contributes quotient rank 5 after quotienting the three PPATH06 support-row obstruction directions, matching the current missing AI rank 5. Integer recombinations of the residual sector already lift the missing rank-5 directions to actual compatibility-zero vectors, but those recombined directions are not yet promoted into the authoritative publication-shell AI generator set.

## Controlled-Case Verdict

- controlled_case_valid = `True`
- single_group_portable = `True`
- double_group_portable_seed = `True`
