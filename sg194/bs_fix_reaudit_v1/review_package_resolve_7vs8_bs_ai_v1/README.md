# Review Package: Resolve 7-vs-8 BS / AI Seed Audit

## Scope
- Target: `SSG 194.1.1.1`
- Round goal: resolve the false Bilbao-equivalence claim on the reduced published shell, then rerun the AI seed honestly.

## Honest Result
- `row_language_full_span_pass = true`
- `bilbao_equivalent_final_object_pass = false`
- Current published shell is an honest `8-path` full-span reduced shell, not a Bilbao-equivalent `7-path` final object.
- The extra retained path class is `PCLASS04` from `L4` on endpoint pair `P1-P5`.

## Key Evidence
- `final_bs_strong_equivalence_report.*`: separates row-language closure from Bilbao-equivalent final-object pass.
- `p1_p5_doubleclass_resolution_report.*`: proves `PCLASS03`/`PCLASS04` are only locally relabelable; the relabel breaks `FPATH01`, `FPATH02`, `FPATH03`, and `FPATH08`, so the two classes cannot be collapsed on the published shell.
- `ai_seed_delta_after_bs_fix_report.*`: AI seed remains `seed_only`, and its residual pattern is unchanged relative to the previous branch.

## Contents
- `reports/`: regenerated audit reports and witnesses.
- `outputs/`: current single/double BS and AI JSON outputs.
- `source/`: final source files edited this round.
