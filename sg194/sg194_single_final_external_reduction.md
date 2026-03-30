# SG194 Single Final External Reduction

- Raw quotient: `Z^16`
- V2 HSP point-space quotient: `Z^5`
- Full external ordinary quotient: `blocked`
- Current full raw AI rowspace rank: `13`
- Current HSP AI rowspace rank: `13`
- External ordinary AI rowspace rank: `13`
- Full raw / external union rowspace rank: `14`
- HSP / external union rowspace rank: `14`
- Exact full-raw row map exists: `False`
- Exact HSP row map exists: `False`

Why the final reduction is blocked:
- The missing blocker is no longer “matrix not cached”; the full external ordinary matrix is now cached locally.
- The stronger blocker is a genuine row-space mismatch: current and external ordinary AI images are both rank-13, but they intersect in rank 12 only.
- Therefore no exact current raw / HSP -> external ordinary row-space lift consistent with all 45 standard generators exists at present.

One external-only generator-domain basis vector:
- `[{'label': 'a_A2g', 'coeff': 1}, {'label': "b_A2'", 'coeff': 1}, {'label': "c_A2'", 'coeff': 1}, {'label': "d_A2'", 'coeff': 1}, {'label': 'e_A2', 'coeff': 1}, {'label': 'f_A2', 'coeff': 1}, {'label': 'g_Bg', 'coeff': 1}, {'label': 'h_B1', 'coeff': 1}, {'label': 'i_B', 'coeff': 1}, {'label': "j_A'", 'coeff': 1}, {'label': "k_A''", 'coeff': 1}, {'label': 'l_A', 'coeff': 1}]`

One current-only generator-domain basis vector:
- `[{'label': 'a_A1g', 'coeff': 1}, {'label': "b_A2''", 'coeff': 1}, {'label': "c_A2''", 'coeff': 1}, {'label': "d_A2''", 'coeff': 1}, {'label': 'e_A1', 'coeff': 1}, {'label': 'f_A1', 'coeff': 1}, {'label': 'g_Ag', 'coeff': 1}, {'label': 'h_B2', 'coeff': 1}, {'label': 'i_A', 'coeff': 1}, {'label': "j_A'", 'coeff': 1}, {'label': "k_A''", 'coeff': 1}, {'label': 'l_A', 'coeff': 1}]`

Correction relative to older conclusions:
- v1 `trivial` must be discarded.
- v2 `Z^5` remains a stricter intermediate point-space diagnostic, not the final external ordinary quotient.
