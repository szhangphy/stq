# SG194 194.1.1.1 Live Checkpoint

- Current time: 2026-04-01 04:54:02 
- Branch: `sg194-special`
- HEAD before this checkpoint update: `13a01c2`
- Task scope: SG194 benchmark hardening / benchmark cleanup: second independent verification, path sanitization, superseded-file deemphasis, and layered review package delivery.

## Rolling Stages

1. independent_verify
   Ran sg194_topmat_experimental_compute_v2.py and the new sg194_topmat_independent_verify_v1.py; both returned classification Z6 with dBS = 10 and dAI = 10.
2. path_inventory
   Identified repo-local absolute path pollution in benchmark authoritative/supporting JSON files before cleanup.
3. path_sanitization
   Rewrote benchmark authoritative/supporting JSON files to repo-relative path semantics and recorded the cleanup in sg194_benchmark_path_sanitization_v1.json/.md.
4. superseded_deemphasis
   Added do-not-use banners and historical snapshots to the old 13/trivial stage2/workflow/completion files.
5. readme_checkpoint_refresh
   Refreshed README and this rolling checkpoint to reflect benchmark hardening rather than benchmark takeover only.
6. review_package
   Built review_package_sg194_benchmark_hardening_v1/ and .tar.gz with benchmark_authoritative and internal_superseded subdirectories plus REVIEW_MAP.md.
7. validation
   py_compile, independent verifier, and benchmark hardening validation all passed; repo is ready for commit/push.

## Confirmed Findings

1. The benchmark-authoritative SG194 result remains classification Z6 with dBS = 10 and dAI = 10.
2. SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round treats them as the same benchmark target for topological classification / dBS / dAI comparison.
3. The suffixless SSG label remains a project benchmark convention plus magnetic-counterpart mapping layer rather than a separately scraped external field.
4. Repo-local benchmark delivery paths are now relative-path-first in the benchmark authoritative/supporting JSON files targeted by this round.
5. The old 13/trivial stage2/workflow/completion files remain preserved only as internal/superseded historical snapshots.

## Active Blocker

1. Accessible external magnetic-group sources confirm `OG 194.1.1494 / BNS 194.263` and `Type-I`, but do not separately expose the suffixless `SSG 194.1.1.1` label as an external field.
