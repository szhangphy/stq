# Review Package: SG194 Source BS Fix v1

## Scope

- Benchmark oracle remains `Z6`, `dBS = 10`, `dAI = 10`.
- The current stage2 source workflow now publishes the same `10 / 10 / Z6` result while preserving the legacy internal `13 / 13 / trivial` layer as provenance.
- Old benchmark-takeover / benchmark-hardening / stage2-closeout packages were deleted from git in this round and replaced by this package.

## Layers

- `benchmark_authoritative/`: benchmark oracle, supporting benchmark evidence, object ladder, authoritative file inventory.
- `source_bs_fix/`: current source workflow outputs, source-gap audit, source-fix attempt, and the source scripts involved.
- `cleanup/`: deletion plan and deletion execution reports for obsolete packages and local clutter.
- `internal_context/`: retained non-authoritative context files that still matter for follow-up work.
