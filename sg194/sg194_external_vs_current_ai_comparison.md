# SG 194 External vs Current AI Comparison

## Single
- External standard AI rank: `13`
- Current raw AI rank: `13`
- External candidate count: `45`
- Current candidate count: `45`
- Exact inventory match: `True`
- Missing generators: `[]`
- Extra generators: `[]`
- Main issue: Current single AI is externally aligned; the unresolved inflation is at the BS/quotient layer rather than at the atomic-generator inventory layer.

## Double
- External mixed BANDREP rank: `23`
- External spinorial candidate rank: `10`
- Current raw AI rank: `13`
- Current candidate count: `45`
- External spinorial candidate count: `33`
- External mixed candidate count: `78`
- Current vs external spinorial counts by Wyckoff:
  - `2a`: current `6` vs Bilbao spinorial `6`
  - `2b`: current `6` vs Bilbao spinorial `3`
  - `2c`: current `6` vs Bilbao spinorial `3`
  - `2d`: current `6` vs Bilbao spinorial `3`
  - `4e`: current `3` vs Bilbao spinorial `3`
  - `4f`: current `3` vs Bilbao spinorial `3`
  - `6g`: current `4` vs Bilbao spinorial `4`
  - `6h`: current `4` vs Bilbao spinorial `1`
  - `12i`: current `2` vs Bilbao spinorial `2`
  - `12j`: current `2` vs Bilbao spinorial `2`
  - `12k`: current `2` vs Bilbao spinorial `2`
  - `24l`: current `1` vs Bilbao spinorial `1`
- Overexpanded sites: {'2b': 3, '2c': 3, '2d': 3, '6h': 3}
- Redundancy / mismatch notes:
  - Bilbao physically irreducible spinorial generators count 3 at each of 2b/2c/2d, whereas the current library carries 6 labels at each site.
  - Bilbao treats 6h through one spinorial E channel, whereas the current library carries 4 projective labels there.
- Main issue: The current double AI is not aligned to Bilbao's physically irreducible spinorial generator convention; the quotient layer is also non-standard because the current BS lives in a larger raw space.
