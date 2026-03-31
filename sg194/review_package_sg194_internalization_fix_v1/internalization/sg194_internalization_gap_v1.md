# SG194 Internalization Gap v1

## Direct Answers

- current_internal_source_bs_true_to_10: `True`
- current_internal_source_ai_true_to_10: `True`
- current_internal_source_quotient_true_to_Z6: `True`
- quotient_direct_current_lattice_derivation: `False`
- single_path_directly_internalized: `False`

## Layer Table

### raw_internal_layer

- object kind: `direct_source_raw_internal`
- source file: `sg194/current_status_194.1.1.1_stage2.json`
- direct source computation: `True`
- current value: `BS=16, AI=13, quotient=Z^3`
- benchmark match: `False`
- gap: BS +6, AI +3, quotient mismatch due to the 16-dimensional raw internal BS ambient

### legacy_internal_reduced_13_layer

- object kind: `historical_internal_reduced_layer`
- source file: `sg194/current_status_194.1.1.1_stage2.json`
- direct source computation: `True`
- current value: `BS=13, AI=13, quotient=trivial`
- benchmark match: `False`
- gap: The historical current-to-standard projection stays at 13/13/trivial and is retained only as provenance

### active_double_internalized_layer

- object kind: `active_source_internalized_target_object`
- source file: `sg194/current_status_194.1.1.1_stage2.json`
- direct source computation: `True`
- current value: `BS=10, AI=10, quotient=Z6`
- benchmark match: `True`
- gap: None at BS/AI rank. Quotient is matched-target inference after exact generator-space identity rather than a direct raw-current Smith derivation.

### single_publication_layer

- object kind: `single_inherited_publication_layer`
- source file: `sg194/current_status_194.1.1.1_stage2.json`
- direct source computation: `False`
- current value: `BS=10, AI=10, quotient=Z6`
- benchmark match: `True`
- gap: The single ordinary line is still inherited from the double internalized target object rather than directly derived as a single benchmark-layer computation.

## Remaining Gaps

- The active double target object is internalized at BS/AI = 10/10, but the final Z6 quotient is still recorded as matched-target inference rather than as a standalone raw-current lattice derivation.
- The single ordinary publication still inherits the target result from the internalized double path instead of exposing a direct single benchmark-layer computation.
- The legacy 13-dimensional reduced layer is still preserved inside stage2 outputs as historical provenance.
