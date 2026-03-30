# SG194 External Matrix Final Report

## 1. Problem Background And Historical Error Chain

Previous SG194 stages stopped at a point where the local repository did not cache the full external Bilbao ordinary and spinorial generator matrices. That made the final standard reduction underdetermined. This stage closes that specific blocker by caching:

- ordinary external matrix: `34 x 45`
- spinorial external matrix: `56 x 33`

but it also shows that the remaining obstruction is **not** missing external data anymore.

## 2. External Matrix Acquisition

Ordinary route:
- landing page: `https://cryst.ehu.es/rep/sitesym.html`
- CGI: `https://cryst.ehu.es/cgi-bin/rep/programs/sitesym/sitesym_cgi.py`
- workflow: showwp -> showorbit -> calcsim

Spinorial route:
- CGI: `https://cryst.ehu.es/cgi-bin/cryst/programs/bandrep.pl`
- workflow: Wyckoff table fetch -> mixed 56x78 parse -> spinorial 56x33 extraction

Raw HTML fetches are cached under `sg194_external_matrix_cache/ordinary` and `sg194_external_matrix_cache/spinorial`.

## 3. Single Final Ordinary Reduction

Let
\[
E_{\mathrm{ord}} \in \mathbb{Z}^{34 \times 45}
\]
be the cached Bilbao ordinary generator matrix, with rows indexed by ordinary high-symmetry irreps at `GM, A, K, H, M, L`.

Let
\[
C_{\mathrm{cur}}^{\mathrm{full}} \in \mathbb{Z}^{62 \times 45}, \qquad
C_{\mathrm{cur}}^{\mathrm{HSP}} \in \mathbb{Z}^{34 \times 45}
\]
be the current internal generator matrices in the full raw unknown basis and in the selected HSP restriction, respectively.

After exact column reordering by generator id, one finds:

- `rank Row(C_cur^full) = 13`
- `rank Row(E_ord) = 13`
- `rank(Row(C_cur^full) + Row(E_ord)) = 14`

The same union rank `14` is obtained for the HSP-restricted current matrix. Therefore no exact row map
\[
P_{\mathrm{single}} C_{\mathrm{cur}} = E_{\mathrm{ord}}
\]
exists, neither from the full raw current matrix nor from the HSP restriction.

The single line is therefore still blocked. The old v1 `trivial` conclusion must be discarded, and the v2 `Z^5` should only be kept as an intermediate HSP-space diagnostic.

## 4. Double Final Spinorial Reduction

Let
\[
E_{\mathrm{spin}} \in \mathbb{Z}^{56 \times 33}
\]
be the cached Bilbao physically irreducible spinorial generator matrix.

The unambiguous problematic sector consists of the ten channels
`2b:E1,E2,E3`, `2c:E1,E2,E3`, `2d:E1,E2,E3`, `6h:E`.
After merging the current internal labels as in the v2 representation-content stage, the current and external problem-sector matrices satisfy:

- `rank Row(C_prob) = 6`
- `rank Row(E_prob) = 6`
- `rank(Row(C_prob) + Row(E_prob)) = 8`

Thus the residual mismatch survives even after the full external spinorial matrix is cached. The current-only and external-only problem-sector difference spaces are both two-dimensional.

This proves that `delta_c1_minus_b1` and `delta_d1_minus_b1` are not just missing lifts caused by unavailable external data; they remain current-only excess directions relative to the external spinorial problem-sector row space.

## 5. Updated Final Conclusions

- Single is **not** finalized.
- Double is **not** finalized.
- SG194 is **not yet** aligned to the final external standard language.

What is now final is the diagnosis:

- single blocker = genuine ordinary row-space mismatch
- double blocker = genuine rank-2 spinorial mismatch in the `2b/2c/2d/6h` sector

## 6. Implementation Mapping

- ordinary matrix cache: `sg194_external_ordinary_generator_matrix.json`
- spinorial matrix cache: `sg194_external_spinorial_generator_matrix.json`
- acquisition audit: `sg194_external_matrix_acquisition.md`
- single final reduction: `sg194_single_final_external_reduction.json`
- double final reduction: `sg194_double_final_external_reduction.json`
- final stage summary: `sg194_external_matrix_final_summary.json`

## 7. Confidence

- ordinary matrix cached: `True`
- spinorial matrix cached: `True`
- single finalized: `False`
- double finalized: `False`
