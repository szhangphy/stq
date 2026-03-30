# Single Group BS Audit

## Scope
- Group: `10.4.1.31`
- Input matrix: the already assembled explicit special-line compatibility matrix from `single_group_full_compatibility.json`.
- Covered layer: explicit special-line compatibility only.
- Not covered: plane representation theory, AI / EBR, BS/AI, or any all-group generalization.

## Input Matrix
- Matrix shape: `10 x 26`
- Number of unknowns: `26`
- Number of equations: `10`
- All entries were rechecked to be exact integers read directly from JSON.

### Global Unknown Ordering
1. `P1_R1`
2. `P1_R2`
3. `P1_R3`
4. `P1_R4`
5. `P1_R5`
6. `P1_R6`
7. `P1_R7`
8. `P1_R8`
9. `P2_R1`
10. `P2_R2`
11. `P3_R1`
12. `P3_R2`
13. `P3_R3`
14. `P3_R4`
15. `P3_R5`
16. `P3_R6`
17. `P3_R7`
18. `P3_R8`
19. `P4_R1`
20. `P4_R2`
21. `P5_R1`
22. `P5_R2`
23. `P6_R1`
24. `P7_R1`
25. `P7_R2`
26. `P8_R1`

### Global Rows And Sources
1. `L1` / `L1_R1`: `1*P1_R1 + 1*P1_R2 = 1*P4_R2`
2. `L1` / `L1_R2`: `1*P1_R3 + 1*P1_R4 = 1*P4_R1`
3. `L1` / `L1_R3`: `1*P1_R5 + 1*P1_R6 = 1*P4_R1`
4. `L1` / `L1_R4`: `1*P1_R7 + 1*P1_R8 = 1*P4_R2`
5. `L2` / `L2_R1`: `1*P2_R1 + 1*P2_R2 = 2*P6_R1`
6. `L3` / `L3_R1`: `1*P3_R1 + 1*P3_R2 = 1*P5_R2`
7. `L3` / `L3_R2`: `1*P3_R3 + 1*P3_R4 = 1*P5_R1`
8. `L3` / `L3_R3`: `1*P3_R5 + 1*P3_R6 = 1*P5_R1`
9. `L3` / `L3_R4`: `1*P3_R7 + 1*P3_R8 = 1*P5_R2`
10. `L4` / `L4_R1`: `1*P7_R1 + 1*P7_R2 = 2*P8_R1`

## Exact Integer Analysis
- Method: exact integer Smith normal decomposition `U * C * V = D` over `ZZ`, with the kernel taken from the last `nullity` columns of the right unimodular matrix `V`.
- Integer rank: `10`
- Nullity: `16`
- Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`
- All nonzero Smith diagonal entries are 1: `True`
- Interpretation: there is no hidden integer torsion in the cokernel data relevant to this layer; the kernel lattice is free abelian of rank 16.

## Raw Integer Basis
- Source: columns `rank+1` through `n_unknowns` of the right unimodular transform `V` from the Smith decomposition.
- Basis vector count: `16`

## Pretty Integer Basis
- Construction: a single-group, block-readable basis chosen inside the same integer kernel lattice.
- Layout: grouped by the four explicit special lines `L1`, `L2`, `L3`, `L4`.
- Same lattice as raw basis: `True`, verified by an integral change-of-basis matrix with determinant `-1`.

### Pretty Basis Overview
- `P1_diff_12` [L1]: Difference mode inside the P1 pair constrained by the first L1 equation. -> `1*P1_R1, -1*P1_R2`
- `P1_diff_34` [L1]: Difference mode inside the P1 pair constrained by the second L1 equation. -> `1*P1_R3, -1*P1_R4`
- `P1_diff_56` [L1]: Difference mode inside the P1 pair constrained by the third L1 equation. -> `1*P1_R5, -1*P1_R6`
- `P1_diff_78` [L1]: Difference mode inside the P1 pair constrained by the fourth L1 equation. -> `1*P1_R7, -1*P1_R8`
- `L1_sum_R1` [L1]: Common integral shift along the L1 branch feeding P4_R1. -> `1*P1_R3, 1*P1_R5, 1*P4_R1`
- `L1_sum_R2` [L1]: Common integral shift along the L1 branch feeding P4_R2. -> `1*P1_R1, 1*P1_R7, 1*P4_R2`
- `P2_diff_12` [L2]: Difference mode inside the left endpoint pair of L2. -> `1*P2_R1, -1*P2_R2`
- `L2_charge` [L2]: Primitive integral charge mode for the 2-to-1 L2 relation. -> `2*P2_R1, 1*P6_R1`
- `P3_diff_12` [L3]: Difference mode inside the P3 pair constrained by the first L3 equation. -> `1*P3_R1, -1*P3_R2`
- `P3_diff_34` [L3]: Difference mode inside the P3 pair constrained by the second L3 equation. -> `1*P3_R3, -1*P3_R4`
- `P3_diff_56` [L3]: Difference mode inside the P3 pair constrained by the third L3 equation. -> `1*P3_R5, -1*P3_R6`
- `P3_diff_78` [L3]: Difference mode inside the P3 pair constrained by the fourth L3 equation. -> `1*P3_R7, -1*P3_R8`
- `L3_sum_R1` [L3]: Common integral shift along the L3 branch feeding P5_R1. -> `1*P3_R3, 1*P3_R5, 1*P5_R1`
- `L3_sum_R2` [L3]: Common integral shift along the L3 branch feeding P5_R2. -> `1*P3_R1, 1*P3_R7, 1*P5_R2`
- `P7_diff_12` [L4]: Difference mode inside the left endpoint pair of L4. -> `1*P7_R1, -1*P7_R2`
- `L4_charge` [L4]: Primitive integral charge mode for the 2-to-1 L4 relation. -> `2*P7_R1, 1*P8_R1`

## Correctness Checks
- Every raw basis vector satisfies `C * v = 0` exactly.
- Every pretty basis vector satisfies `C * v = 0` exactly.
- Raw basis rank and pretty basis rank both equal the nullity 16.
- The raw-to-pretty change-of-basis matrix is integral and unimodular, so both bases span the same integer lattice.
- Each global row is essential: dropping any one row lowers the rank from 10 to 9.
- No duplicate global rows were found.

### Local Block Checks
- `L1` local kernel rank: `6`; all raw/pretty basis restrictions satisfy the local equations.
- `L2` local kernel rank: `2`; all raw/pretty basis restrictions satisfy the local equations.
- `L3` local kernel rank: `6`; all raw/pretty basis restrictions satisfy the local equations.
- `L4` local kernel rank: `2`; all raw/pretty basis restrictions satisfy the local equations.

## Structural Reading
- The current matrix only encodes explicit special-line compatibility. Nothing else was mixed in.
- The pretty basis exhibits a direct-sum decomposition by line block: `L1` contributes 6 generators, `L2` contributes 2, `L3` contributes 6, and `L4` contributes 2.

## Current Result
- This run establishes the integer band-structure lattice `BS = ker_Z(C)` for group `10.4.1.31` at the explicit special-line compatibility layer.
- This is not a final topological classification and does not include AI / EBR / BS/AI.
