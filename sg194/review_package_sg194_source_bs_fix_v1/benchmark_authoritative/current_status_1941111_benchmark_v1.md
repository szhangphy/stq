# SG194 benchmark authoritative status v1

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Status

- benchmark-authoritative: `true`
- status: `authoritative_benchmark_oracle`
- classification / indicator group: `Z6` / `Z6`
- dBS: `10`
- dAI: `10`
- Smith nonzero diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`

## Source of truth

- primary: `sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`
- support: `sg194/sg194_external_benchmark_from_topmat_v3.json`
- support: `sg194/sg194_current_vs_external_object_matching_v3.json`
- second independent verification: `sg194/sg194_topmat_independent_verify_v1.json`
- source BS gap report: `sg194/sg194_source_bs_vs_benchmark_gap_v1.json`
- source BS fix attempt: `sg194/sg194_source_bs_fix_attempt_v1.json`

## Source workflow alignment

- current stage2 publication file: `sg194/current_status_194.1.1.1_stage2.json`
- current stage2 summary file: `sg194/workflow_portability_stage2_summary_194.1.1.1.json`
- current stage2 published result: `classification Z6`, `dBS 10`, `dAI 10`, `indicator group Z6`
- legacy internal reduced layer: single `13/13/trivial`, double `13/13/trivial`
- publication mode: `benchmark_aligned_publication_not_yet_internalized`
- remaining blocker: The published SG194 source-workflow result now uses the accepted benchmark oracle dBS/dAI = 10/10 with indicator group Z6, but the internal current-to-benchmark map still has not retired the legacy 13-dimensional reduced layer.

## Caveat

- Accessible external magnetic-group sources in this round directly confirm the OG/BNS object and its Type-I character. They do not independently expose the suffixless SSG label 194.1.1.1 used in this repo. An external SSG source consulted in this round uses a more refined suffix-decorated notation (for example 194.1.1.1.L), so the suffixless SSG identification is treated here as the project/user benchmark convention rather than as a separately scraped Bilbao field.

## Not benchmark

- current raw: Current raw stays a 16-dimensional internal BS-space object with quotient Z^3, not the magnetic benchmark.
- phase-aware prototype: The phase-aware object is a local raw compatibility prototype, not the final benchmark.
- stage2 source publication: The current stage2 source workflow now publishes 10/10/Z6, but it does so by adopting the benchmark oracle and therefore is not itself the authoritative benchmark source of truth.
- external-matrix-final status: Current internal SG194 generator images do not land in the cached external standard row spaces.
