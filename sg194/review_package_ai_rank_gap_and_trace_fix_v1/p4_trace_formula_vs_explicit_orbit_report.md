# P4 Trace Formula vs Explicit Orbit Report

- Manifold id: `P4`.
- Compared generators: `["b_A1'", "c_A1'", "d_A1'"]`.
- First failure mismatch: `None`.
- Resolved by character-field conversion: `True`.
- Bug localized to stage: `manifold_character_field_conversion: convert the assembled linear band trace to the selected character field by dividing by exp(-i k·tauC(op)) on each unitary operation`.
- Summary: Legacy formula trace and explicit orbit-action trace agree on the audited P4 objects after canonical orbit reduction, so the earlier c/d induction failure is not caused by target-site matching or explicit-orbit trace assembly. The repaired bug sits one stage later, when the assembled linear band trace must be converted into the selected `character` field using the operation translation phase.

- `b_A1'` differing ops: `[]`.
- `c_A1'` differing ops: `[]`.
- `d_A1'` differing ops: `[]`.
