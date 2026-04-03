# P4 Trace Formula vs Explicit Orbit Report

- Manifold id: `P4`.
- Compared generators: `["b_A1'", "c_A1'", "d_A1'"]`.
- First linear-trace mismatch: `None`.
- First converted-trace mismatch: `None`.
- First failure mismatch: `None`.
- Linear-trace differing-op count: `0`.
- Converted-trace differing-op count: `0`.
- Resolved by character-field conversion: `True`.
- Bug localized to stage: `manifold_character_field_conversion: convert the assembled linear band trace to the selected character field by dividing by exp(-i k·tauC(op)) on each unitary operation`.
- Summary: The P4 audit now separates pre-conversion linear-trace comparison from post-conversion selected-character comparison. Both the legacy formula trace and the explicit orbit-action trace agree on the audited P4 objects in the linear trace and in the converted character trace, so the remaining evidence for the earlier c/d induction failure sits in the field-conversion stage itself, not in target-site matching or orbit-action assembly.

- `b_A1'` linear differing ops: `[]`; converted differing ops: `[]`.
- `c_A1'` linear differing ops: `[]`; converted differing ops: `[]`.
- `d_A1'` linear differing ops: `[]`; converted differing ops: `[]`.
