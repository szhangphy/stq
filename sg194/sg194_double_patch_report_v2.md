# SG194 Double Patch Report V2

## 1. Metric-layer bug in previous patch audit

The previous `debug_sg194_double_patch.py` labeled its core generator verdict helper as `row_rank_union_intersection(...)` and described the result as a generator comparison. That was semantically wrong. The verdict should be phrased in terms of generator-span / column-space logic.

## 2. Correct column-space comparison setup

Current SG194 double generators live in a `34`-row current-HSP ambient, while the cached external spinorial generators live in a `56`-row Bilbao ambient. Direct column-space hstack on the original matrices is therefore ill-typed. The corrected generator-span comparison uses the column spaces of the transposed matrices in the common generator-label ambient.

Under this corrected setup:

- global old/patched/external ranks = `12 / 12 / 10`
- global old/patched union = `21 / 21`
- problem old/patched union = `8 / 6`

## 3. Before/after revalidation under corrected metric

The corrected metric preserves the main rank verdict:

- the global mismatch is not reduced;
- the trusted `2b/2c/2d/6h` problem sector still improves from union rank `8` to `6`.

So the generator patch remains effective, but only in the trusted problem sector.

## 4. Delta membership re-check

The old patch audit incorrectly treated `problem_sector_union_rank == external_rank` as evidence that `delta_c1_minus_b1` and `delta_d1_minus_b1` had disappeared.

The corrected re-check uses explicit current-side ambient membership of the named delta vectors:

- `delta_c1_minus_b1`: legacy current contains = `True`, patched current contains = `True`, disappeared = `False`
- `delta_d1_minus_b1`: legacy current contains = `True`, patched current contains = `True`, disappeared = `False`

Therefore the old `delta disappeared` claims must be withdrawn.

## 5. Updated patch verdict

- patch effective under corrected metric: `True`
- effect scope: `trusted_problem_sector_only`
- global mismatch shrunk: `False`
- explicit deltas disappeared: `c=False`, `d=False`

## 6. Next engineering step

BS-only comparison is still not the next justified step. The corrected reason is:

`No. The corrected generator-span metric still shows only a trusted problem-sector improvement, not a global collapse. Also, the explicit delta vectors remain in the patched current generator span, so the old `delta disappeared` claim is withdrawn.`
