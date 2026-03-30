# Handoff: SG194 mismatch localization

## Done
- Localized the 1D single AI mismatch to explicit generator-domain and row-witness representatives.
- Decomposed the single BS mismatch into 9 AI-induced dimensions plus 4 independent residual BS directions.
- Localized `delta_c1_minus_b1` and `delta_d1_minus_b1` to explicit 2b/2c/2d E1 merged-channel differences.
- Wrote a minimal double correction plan focused on merge/typing rules rather than BS code.

## Current diagnosis
- single main issue: both
- single independent BS residual dimension: 4
- double main issue: AI

## Current blocker
- No new blocker for localization. The next blocker is implementation: patch the double merge/typing logic and then rerun the limited AI-only alignment checks.

## Next unique goal
- Implement the minimal correction plan at the 2b/2c/2d/6h double AI merge layer and test whether the problem-sector rank drops from 12 to 10.

## Read first
- `sg194_single_ai_mismatch_localization.json`
- `sg194_single_bs_mismatch_localization.json`
- `sg194_double_delta_localization.json`
- `sg194_double_minimal_correction_plan.json`
