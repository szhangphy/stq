# SG194 external benchmark from topmat v3

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## topmat reference verdict

- classification / indicator group: `Z6`
- dBS: `10`
- dAI: `10`
- Smith nonzero diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`
- finite part: `[6]`
- free rank: `0`

## What topmat_src gives directly

- read-only CLI run succeeded: `true`
- sample direct indicator value: `Z6=0,`
- classification from `Lindex_194.263.txt`: `Z6`

## What required copied experimental computation

- `dBS` and `dAI` were not emitted as direct CLI scalars.
- They were computed locally from the copied `basis_194.263.txt` and `MsgAI_194.263.txt` using rank and Smith decomposition.

## External cross-check scope

- Bilbao magnetic-group table for radical 194: https://cryst.ehu.es/cryst/magnext.php?from=&magtr=3&radical=194&radical_label=P6%3Csub%3E3%3C%2Fsub%3E%2Fmmc
- Bilbao group page for 194.263: https://www.cryst.ehu.es/cryst/magnext.php?label=P6_3%2Fmmc&label_og=P6_3%2Fmmc&radical_label=P6_3%2Fmmc&radical_og=194&radical_sub=194.263&radical_sub_subsub=&sub_og=1&subsub_og=1494&type=1
- Bilbao MSG overview for radical 194: https://www.cryst.ehu.es/cryst/msg_all.php?radical=194
- PRX 2024 supplementary SSG table: https://journals.aps.org/prx/supplemental/10.1103/PhysRevX.14.031039/sm.pdf

## Z6 hypothesis

- status: `supported`
- basis: `Lindex` group factor 6, `basis` invariant factor 6, and copied Smith quotient finite part [6].
