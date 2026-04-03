# Character-Field Conversion Global Validation Report

- Mode: `single`.
- Formula: `predicted_character = linear_character / exp(-i k·tauC(op))`.
- Phase source field / runtime patch field: `tauC` / `unitary_translations`.
- Manifold count by kind: `{'line': 77, 'point': 11, 'plane': 4}`.
- Comparison count / exact matches / mismatches: `2148` / `2148` / `0`.
- All manifolds pass: `True`.
- tauC-vs-unitary-translation comparison count / mismatches: `508` / `0`.
- tau fields match globally: `True`.
- First mismatch: `None`.
- First tau-field mismatch: `None`.
- Summary: The character-field conversion formula is validated directly against the capture tables rather than through the induction-trace builders. For every audited single-branch manifold, the stored `character` matches `linear_character / exp(-i k·tauC(op))`, and the capture-table `tauC` field matches the runtime `unitary_translations` field used by the patch.
