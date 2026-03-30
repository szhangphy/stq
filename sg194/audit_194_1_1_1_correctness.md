# Correctness Audit for 194.1.1.1

## single-group

- `BS_likely_correct = uncertain`
- `AI_likely_complete = uncertain`
- `quotient_interpretation_likely_correct = false`
- raw quotient: `Z^16`
- suspicion ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `high`
- main issue: The raw quotient Z^16 is free-only and therefore cannot be presented as a standard finite topological indicator group.

### BS layer evidence

- single and double BS backgrounds can be rebuilt from the stage-1/stage-2 scripts in the current workspace
- the recomputed single and double matrices both have shape [58, 62] and nullity 29
- the BS layer on 194.1.1.1 depends on synthetic boundary-point augmentation because swyckoff_k.py does not emit every needed 0D endpoint directly
- that augmentation is internally consistent, but it is still the main reason this BS layer is less settled than the closed 10.4.1.31 case

### AI / completeness evidence

- the SG194 single local-irrep library covers the non-abelian types C3v, D3d-like, and D3h-like with orthogonality and dimension-squared checks
- the recomputed single AI rank is 13 inside BS rank 29
- the recomputed raw quotient is Z^16
- however, the completeness statement is still library-backed rather than independently checked against an external BR/EBR source

### Quotient interpretation evidence

- the quotient summary itself already records free_rank = 16 and finite_part = []
- there is no finite torsion left after the raw Smith decomposition
- therefore Z^16 is a raw free-dominated quotient, not a standard finite symmetry-indicator group

### Evidence files

- `group_194_1_1_1_single_bs_analysis.json`
- `group_194_1_1_1_single_full_compatibility_with_planes.json`
- `group_194_1_1_1_single_pilot_summary.json`
- `group_194_1_1_1_single_pilot_audit.md`
- `group_194_1_1_1_single_ai_completion_summary.json`
- `group_194_1_1_1_single_indicator_group_summary.json`
- `group_194_1_1_1_single_indicator_generators.json`
- `workflow_portability_report_194.1.1.1.tex`
- `workflow_portability_report_stage2_194.1.1.1.tex`
- `debug_workflow_portability_stage2_194.1.1.1.py`
- `debug_sg194_nonabelian_local_library.py`

- recommended next step: Keep the raw quotient as an algebraic result, but separately identify which free directions are genuine topological invariants and whether any finite symmetry-indicator sector remains after the physically appropriate reduction.

## double-group

- `BS_likely_correct = uncertain`
- `AI_likely_complete = uncertain`
- `quotient_interpretation_likely_correct = false`
- raw quotient: `Z^16`
- suspicion ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `medium`
- main issue: The double-group result is again a free-only raw quotient Z^16, while the AI completeness claim still depends on the current projective local library.

### BS layer evidence

- single and double BS backgrounds can be rebuilt from the stage-1/stage-2 scripts in the current workspace
- the recomputed single and double matrices both have shape [58, 62] and nullity 29
- the BS layer on 194.1.1.1 depends on synthetic boundary-point augmentation because swyckoff_k.py does not emit every needed 0D endpoint directly
- that augmentation is internally consistent, but it is still the main reason this BS layer is less settled than the closed 10.4.1.31 case

### AI / completeness evidence

- the SG194 double local library uses projective twisted-regular decomposition with factor_su2 validation
- the recomputed double AI rank is 13 inside BS rank 29
- the recomputed raw quotient is Z^16
- this is a newer and more delicate library than the single-group one, so the completeness verdict is still best treated as conditional on the current projective builder

### Quotient interpretation evidence

- the double quotient summary also records free_rank = 16 and finite_part = []
- this matches the recomputed projective-library-based quotient exactly
- again, the problem is interpretation: a free-only raw quotient cannot be read as a final finite indicator group

### Evidence files

- `group_194_1_1_1_double_bs_analysis.json`
- `group_194_1_1_1_double_full_compatibility_with_planes.json`
- `group_194_1_1_1_double_pilot_summary.json`
- `group_194_1_1_1_double_pilot_audit.md`
- `group_194_1_1_1_double_ai_completion_summary.json`
- `group_194_1_1_1_double_indicator_group_summary.json`
- `group_194_1_1_1_double_indicator_generators.json`
- `workflow_portability_report_194.1.1.1.tex`
- `workflow_portability_report_stage2_194.1.1.1.tex`
- `debug_workflow_portability_stage2_194.1.1.1.py`
- `debug_sg194_nonabelian_local_library.py`

- recommended next step: Do not call Z^16 a final double-group indicator group; first separate the free sector, then cross-check the projective local library with an independent derivation or benchmark.
