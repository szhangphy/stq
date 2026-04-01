# Review Package: SG194 Generality And 222 Fix V2

This package captures three distinct facts:

- the current codebase is **not** truly general yet;
- the previous `222.1.1.1` generic-path result had a real `dBS != dAI` bug caused by silent AI-candidate dropping;
- the copied `topmat_src` oracle provides a unified OG-object result for `222.1.1.1 <-> 222.1.1601`.

## Key points

- `generality_layer/` shows where the pipeline is still case-by-case or fake-generic.
- `bug_layer/` shows the dropped AI candidates and why `11 / 10 / Z x Z4` was not trustworthy.
- `identity_222_layer/` records the object identity map and the v3 finalization files.
- `oracle_layer/` records the copied oracle inputs and the modifications log.
- `semantics_layer/` separates `checks_passed`, `final_results_available`, and `final_results_verified`.
- `sg194_regression_layer/` keeps the accepted SG194 reference state for non-regression.
- `cleanup_layer/` records deletion of superseded `222 v2` partial/onboarding artifacts.

## Scope note

- The copied topmat oracle is unified at the OG-object level. It does not expose an independent single/double split.
- The package therefore records the same oracle-backed `8 / 8 / Z2` result in both mode slots with explicit unified-OG scope notes.
