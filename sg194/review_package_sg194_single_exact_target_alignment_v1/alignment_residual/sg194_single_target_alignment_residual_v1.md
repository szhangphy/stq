# SG194 Single Target Alignment Residual v1

- pre-fix raw-label residual rank = `1`
- post-fix exact-label residual rank = `0`
- problem columns before fix = `["j_A'", "j_A''", "k_A'", "k_A''"]`
- verdict: The old residual lived entirely on the j/k A'/A'' columns under raw label pairing. After applying the canonical single ordinary target-label map, the residual vanishes exactly.
