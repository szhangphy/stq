# Root Cause and Fix Summary

- The previous gap was no longer coarse ordinary rows; it was monodromy families with semantic slots but zero equations.
- This patch changes the monodromy builder from same-index line-basis delta to translated-capture rep matching, then emits point-level equations only when continuation is single-valued at the published target point.
- That generic single-valued-continuation gate keeps `159` active while keeping `194.1.12.16` unchanged.
- Remaining blocker: `L4/L5` still yield identity continuation, so they remain zero-equation families and prevent a final BS claim.