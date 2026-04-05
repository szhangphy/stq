# BS vs Bilbao Family Diff for 159.1.6.2

## 1. Missing exact line families relative to Bilbao target semantics
Ordinary line families `DT / P / PC / Λ / Q / U` are no longer missing. All six are now materialized as exact restriction-class rows.

## 2. Rows that are still coarse but semantically should be exact
None in the actual target BS row language after this patch.

## 3. Monodromy families that are still metadata-only / zero-equation
All current monodromy blocks for `L1..L6` remain zero-equation blocks. They are no longer coarse-builder blocks, but they still do not contribute actual exact equations.

## 4. Source-dependent split check
The old split `recovered -> exact` vs `ordinary -> coarse` has been removed.
- `L1/L2/L3` were previously coarse only.
- `L4/L5/L6` were previously exact only because they were recovered.
- After this patch, `L1..L6` all dispatch through the same semantic rule: line family with `source_dimension=1` and `source_mult=1` -> exact.

## 5. Remaining semantic gap
The remaining gap is not coarse ordinary families. It is the absence of nonzero exact monodromy equations for the six target line families. Therefore the BS path is still not final.
