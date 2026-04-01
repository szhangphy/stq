# SG194 Single Target Generator Diff v1

- problem generators = `["j_A'", "j_A''", "k_A'", "k_A''"]`
- signed permutation map = `{"j_A'": "k_A'", "j_A''": "k_A''", "k_A'": "j_A'", "k_A''": "j_A''"}`
- root cause: The single-valued ordinary 12j / 12k generator labels are swapped relative to the external ordinary cache.
