# Single Group Full Compatibility Audit

## Scope
- Group: `10.4.1.31`
- This run only covers the explicit special-line compatibility layer.
- Covered lines: `L1, L2, L3, L4`
- Not covered: plane representation theory, geometric boundary lines, all-group generalization, AI/EBR/BS classification.

## Reuse From The Single-Connection Prototype
- Reused directly:
  - raw `SSGReps.py` CLI calling convention
  - exact-k to CLI-float bookkeeping
  - unitary-subgroup operation matching
  - restriction/decomposition using the internal JSON `character` field
- Previously hard-coded for `L1` and generalized only within this single group:
  - one line block -> loop over `L1-L4`
  - one endpoint pair -> geometry-driven endpoint lookup from `single_group_connectivity.json`
  - one local block -> four local blocks plus one global matrix assembly
- Still intentionally not generalized to high-throughput or all-group infrastructure.

## Geometry Verification
- `P1 -- L1 -- P4`: `(0, v, 0)`, constraints `0 < v, v < 1/2`, sample point `(0, 1/5, 0)`
- `P2 -- L2 -- P6`: `(0, v, 1/2)`, constraints `0 < v, v < 1/2`, sample point `(0, 1/5, 1/2)`
- `P3 -- L3 -- P5`: `(1/2, v, 0)`, constraints `0 < v, v < 1/2`, sample point `(1/2, 1/5, 0)`
- `P7 -- L4 -- P8`: `(1/2, v, 1/2)`, constraints `0 < v, v < 1/2`, sample point `(1/2, 1/5, 1/2)`

## Raw Output Status
- `L1`: character=`ok`, degree=`ok`, exact_k=`(0, 1/5, 0)`, cli_k=`(0, 0.2, 0)`
- `L2`: character=`ok`, degree=`ok`, exact_k=`(0, 1/5, 1/2)`, cli_k=`(0, 0.2, 0.5)`
- `L3`: character=`ok`, degree=`ok`, exact_k=`(1/2, 1/5, 0)`, cli_k=`(0.5, 0.2, 0)`
- `L4`: character=`ok`, degree=`ok`, exact_k=`(1/2, 1/5, 1/2)`, cli_k=`(0.5, 0.2, 0.5)`
- `P1`: character=`ok`, degree=`ok`, exact_k=`(0, 0, 0)`, cli_k=`(0, 0, 0)`
- `P2`: character=`ok`, degree=`ok`, exact_k=`(0, 0, 1/2)`, cli_k=`(0, 0, 0.5)`
- `P3`: character=`ok`, degree=`ok`, exact_k=`(1/2, 0, 0)`, cli_k=`(0.5, 0, 0)`
- `P4`: character=`ok`, degree=`ok`, exact_k=`(0, 1/2, 0)`, cli_k=`(0, 0.5, 0)`
- `P5`: character=`ok`, degree=`ok`, exact_k=`(1/2, 1/2, 0)`, cli_k=`(0.5, 0.5, 0)`
- `P6`: character=`ok`, degree=`ok`, exact_k=`(0, 1/2, 1/2)`, cli_k=`(0, 0.5, 0.5)`
- `P7`: character=`ok`, degree=`ok`, exact_k=`(1/2, 0, 1/2)`, cli_k=`(0.5, 0, 0.5)`
- `P8`: character=`ok`, degree=`ok`, exact_k=`(1/2, 1/2, 1/2)`, cli_k=`(0.5, 0.5, 0.5)`

## Per-Line Block Status
- `L1` succeeded: endpoints `P1` / `P4`, basis size `4`, local matrix shape `4 x 10`
- `L2` succeeded: endpoints `P2` / `P6`, basis size `1`, local matrix shape `1 x 3`
- `L3` succeeded: endpoints `P3` / `P5`, basis size `4`, local matrix shape `4 x 10`
- `L4` succeeded: endpoints `P7` / `P8`, basis size `1`, local matrix shape `1 x 3`

## Consistency Checks
- All blocks successful: `True`
- Same line-group type: `False`
- Same basis size: `False`
- Same canonical matrix pattern: `False`
- Same endpoint decomposition patterns: `False`
- At least one explicit special line has a different little-group signature.
- At least one line block differs in local matrix/decomposition pattern and needs separate inspection.

## Coverage
- Constructed here:
  - four explicit special-line endpoint-line-endpoint blocks
  - the single-group global compatibility matrix assembled from those four line blocks
- Not constructed here:
  - any plane-level compatibility
  - any compatibility induced from geometric-only boundary lines
  - any full BS / AI / EBR result

## Outcome
- Current line-level matrix available: `True`
- Global matrix shape: `10 x 26`
- can_proceed_to_next_stage: `True`
- next_blocker: `Plane-level representation theory and any later AI/EBR steps are outside the current run.`
