# SG194 topmat experimental compute v2

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Input objects

- copied basis file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/basis_194.263.txt`
- copied magnetic AI file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/MsgAI_194.263.txt`
- copied Lindex file: `/data/work/szhang/ssg/comprel/stq_repo_export/repo/sg194/topmat_reference_v3/data/output/Lindex_194.263.txt`

## Algorithms

- compatibility / benchmark lattice object: magnetic BS basis from `basis_194.263.txt`
- BS dimension: rank of the copied magnetic BS basis matrix
- AI dimension: rank of magnetic AI generators after exact integer lift into the BS basis
- quotient: Smith normal form of the AI-in-BS integer generator matrix

## Output object

- complete classification: `Z6`
- dBS: `10`
- dAI: `10`
- AI-in-BS shape: `[10, 33]`
- Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`

## Direct run confirmation

- read-only topmat run success: `true`
- sample `indout`: `Z6=0,`
