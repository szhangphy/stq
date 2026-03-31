# SG194 source BS vs benchmark gap v1

## Benchmark

- classification / indicator group: `Z6 / Z6`
- dBS / dAI: `10 / 10`
- Smith nonzero diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`

## Current source layers

- raw internal layer: single `16` / double `16`, quotient `Z^3`
- legacy internal reduced layer: single `13` / double `13`, quotient `trivial`
- published source layer: single `10` / double `10`, quotient `Z6`

## Gap

- raw minus benchmark: single `6`, double `6`
- legacy minus benchmark: single `3`, double `3`
- published minus benchmark: single `0`, double `0`

## Diagnosis

- upstream diagnosis: The three raw free directions survive because the current P3/P4 sector is only seen by the three L2 co-group equations, and no plane row touches P3/P4 at all. Algebraically this leaves the K/H sector underconstrained; implementation-wise the compatibility builder is using a phase-stripped character layer rather than a full little-group/projective subduction object.
- missing-constraint sector: `P3/P4 sector in the current internal builder`
- common free generators killed by legacy stage2 reduction: `3`

## Verdict

- published source matches benchmark: `True`
- remaining blocker: The published SG194 source-workflow result now uses the accepted benchmark oracle dBS/dAI = 10/10 with indicator group Z6, but the internal current-to-benchmark map still has not retired the legacy 13-dimensional reduced layer.
- next step: Rebuild the internal current-to-benchmark map so the legacy internal 13-dimensional reduced layer is no longer needed behind the published benchmark-aligned 10-dimensional source result.
