# SG194 topmat independent verify v1

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Result

- classification / indicator group: `Z6`
- dBS: `10`
- dAI: `10`
- Smith nonzero diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`
- finite part: `[6]`
- free rank: `0`

## Independent method

- summary: Independent verifier that parses the copied topmat reference data, selects a full-rank 10x10 basis row minor from basis_194.263.txt, solves each MsgAI column through that row minor, verifies full-row reconstruction, and then performs Smith decomposition on the resulting AI-in-BS integer matrix.
- basis row minor indices (0-based): `[0, 1, 2, 3, 4, 5, 9, 11, 16, 20]`
- basis row minor determinant: `1`

## Cross-checks

- Lindex indicator factors: `[6]`
- basis invariants: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`
- basis invariants match Smith diagonal: `true`
- Lindex finite factors match quotient: `true`

## Input files

- Lindex: `sg194/topmat_reference_v3/data/output/Lindex_194.263.txt`
- basis: `sg194/topmat_reference_v3/data/output/basis_194.263.txt`
- MsgAI: `sg194/topmat_reference_v3/data/output/MsgAI_194.263.txt`
