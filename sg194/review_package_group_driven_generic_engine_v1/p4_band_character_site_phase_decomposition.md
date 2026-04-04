# P4 Band Character / Site-Phase Decomposition

- Manifold id: `P4`.
- Reference generator: `b_A1'`.
- Compared generators: `["b_A1'", "c_A1'", "d_A1'"]`.
- Selected character field: `point=character, line=character, plane=character, default=character`.
- Resolved by character-field conversion: `True`.
- Character-field conversion stage: `manifold_character_field_conversion: convert the assembled linear band trace to the selected character field by dividing by exp(-i k·tauC(op)) on each unitary operation`.
- Summary: Across b/c/d the P4 little-group basis is shared, and the per-site orbit-phase contributions assemble the same linear-trace semantics for all audited objects. The earlier c/d induction failures were cleared when that assembled linear band trace was converted into the selected `character` field using the per-operation translation phase.

- `c_A1'` differs from `b_A1'` on unitary ops `[1, 2, 16, 17]`.
- `d_A1'` differs from `b_A1'` on unitary ops `[1, 2, 16, 17]`.
