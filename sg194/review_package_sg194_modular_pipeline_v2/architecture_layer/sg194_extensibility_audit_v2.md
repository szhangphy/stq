# Extensibility Audit v2

- state: `partially_generic_but_now_adapter_pluggable`
- can onboard other groups today: `partially`
- second group trust level: `symmetry_operations_only`

## Structural Obstacles

- Group adapters still own artifact interpretation and final-object semantics.
- No generic builder yet exists from symmetry operations all the way to BS/AI/quotient.

## Data / Adapter Obstacles

- Each new group still needs a producer or trusted artifact binding.
- Target-row-language builders remain group-dependent unless a generic translation layer is added.

## Semantic Obstacles

- SG194 double benchmark-facing semantics are still group-specific.
- SG194 single j/k canonicalization remains an isolated normalization hook.
- 10.4.1.31 is only admitted under symmetry-operations-only trust.
