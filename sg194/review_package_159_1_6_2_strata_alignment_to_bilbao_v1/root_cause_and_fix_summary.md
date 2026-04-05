# Root Cause And Fix Summary

## Root cause

Before this patch, `159.1.6.2` had already recovered the eight real maximal points, but the grouped geometry still only materialized three vertical lines:

- `(0,0,w)`
- `(1/3,1/3,w)`
- `(2/3,2/3,w)`

The missing piece was not additional points, but family special strata hidden as plane boundaries. In particular, the single internal plane family carried unmatched boundary lines whose endpoints were already real recovered points, but those 1D strata were never promoted into grouped geometry.

## Fix

The new helper `_recover_family_special_lines_from_planes(...)` scans unmatched plane boundaries, keeps only closures that remain within separately listed plane families, and materializes a new grouped line if both boundary endpoints are real distinct points.

For `159.1.6.2`, this recovers:

- `L4 = (v,-2v,0)`
- `L5 = (v,-2v,1/2)`
- `L6 = (1/2,-1,w)`

This is enough to lift grouped geometry from the previous “8 points + 3 vertical lines” layer to the intended Bilbao semantic layer containing `Lambda / Q / U / C`.

## What this round does not do

This patch does not change quotient logic. The remaining blocker is downstream: the published target universe is now populated, but the solver still returns `dBS=9` and `dAI=4`.
