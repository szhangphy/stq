# SG194 benchmark authoritative status v1

SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.

## Status

- benchmark-authoritative: `true`
- status: `authoritative_benchmark_oracle`
- classification / indicator group: `Z6`
- dBS: `10`
- dAI: `10`
- Smith nonzero diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 6]`

## Source of truth

- primary: `sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`
- support: `sg194/sg194_external_benchmark_from_topmat_v3.json`
- support: `sg194/sg194_current_vs_external_object_matching_v3.json`
- direct topmat classification available: `true`
- direct topmat dBS available: `false`
- direct topmat dAI available: `false`

## Caveat

- Accessible external magnetic-group sources in this round directly confirm the OG/BNS object and its Type-I character. They do not independently expose the suffixless SSG label 194.1.1.1 used in this repo. An external SSG source consulted in this round uses a more refined suffix-decorated notation (for example 194.1.1.1.L), so the suffixless SSG identification is treated here as the project/user benchmark convention rather than as a separately scraped Bilbao field.

## Not benchmark

- current raw: Current raw stays a 16-dimensional internal BS-space object with quotient Z^3, not the magnetic benchmark.
- phase-aware prototype: The phase-aware object is a local raw compatibility prototype, not the final benchmark.
- anchored stage2 final claim: The older stage2 anchored object was a reduced externally anchored quotient claim, but the later authoritative status re-opened it to unresolved/null.
- external-matrix-final status: Current internal SG194 generator images do not land in the cached external standard row spaces.

## Takeover verdict

- phase-aware verdict: still potentially needed, but only after object mapping to benchmark is clarified
- phase-aware detail: Necessary as a raw-layer repair if the internal SG194 builder is being fixed, but directionally wrong if interpreted as the benchmark answer itself.
- stage2 13/trivial verdict: The older 13/13/trivial stage2 claim is retained only as an internally anchored reduced quotient claim and is superseded for benchmark use.
