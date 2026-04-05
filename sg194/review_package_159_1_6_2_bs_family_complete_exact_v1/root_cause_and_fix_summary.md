# Root Cause And Fix Summary

## Root cause in previous branch
The previous exact-compatibility patch still gated exact rows by provenance (`source_letter == recovered_family_special_line`). That split one Bilbao target semantics layer into two languages:
- recovered families exact
- ordinary families coarse

## This round's fix
The exact/coarse decision was moved from provenance-based gating to semantic family gating in `generic_builders.py`.

## Current quantitative result
- 159 single target row-language rank: 3
- 159 double target row-language rank: 4
- 159 single published dBS: 3
- 159 double published dBS: 2
- 159 single dAI: 0
- 159 double dAI: 0

## Remaining blocker
Ordinary line families are now family-complete exact, but monodromy blocks still contribute zero actual equations. Therefore the BS target semantics is improved and no longer mixed by source, but it is still not final.
