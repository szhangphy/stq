# SG194 Double Complement Mismatch Localization

## Exact residual

- current-only dimension: `5`
- external-only dimension: `3`
- family-local residual families: `[]`

## Localization

- current witness row blocks: `['P1']`
- external witness row blocks: `['A', 'Γ']`
- families touched by the residual basis: `['a', 'e', 'f', 'g', 'i', 'j', 'k', 'l']`

## Engineering diagnosis

- best match: `wrong_ambient_space_construction_or_missing_complement_row_basis_translation`
- reason: The trusted sector is already solved, and no single complement family shows an isolated external-vs-current residual. The unresolved mismatch appears only after assembling all complement families together, which is the signature of a global ambient-row translation problem.
