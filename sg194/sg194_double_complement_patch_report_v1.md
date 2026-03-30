# SG194 Double Complement Patch Report V1

## 1. What the previous patch solved and what it did not solve

The previous `sg194_double_anchor_patch_v1` round solved the trusted `2b/2c/2d/6h` sector exactly, but it left the 23-channel complement on legacy identity reuse. That is why the global residual remained:

- old complement rank tuple = `9 / 7 / 12 / 4`
- old complement mismatch = `current-only 5`, `external-only 3`

So the old patch fixed the trusted problem sector, but not the complement branch that still carried the full-33 obstruction.

## 2. Why this complement patch is the correct source layer

The real unresolved source object was `build_sg194_double_spinorial_generators(...)` in `debug_workflow_portability_stage2_194.1.1.1.py`. The old builder used:

- a trusted-sector patch only for `b/c/d/h`
- legacy identity one-to-one reuse for the complement families `a/e/f/g/i/j/k/l`

This round adds a new explicit profile `sg194_double_complement_patch_v1`. It keeps the trusted rules unchanged and replaces the complement branch with an exact, auditable row-basis translation table emitted in canonical external order.

## 3. Exact complement rule logic

The complement rules were solved by fixing the trusted 10-generator block and imposing the full external 33-column null relations on the remaining 23 columns. The key four homogeneous directions selected by the exact solve are:

- `a_proj_u_1d_1`
- `a_proj_u_1d_2`
- `a_proj_g_1d_3`
- `a_proj_u_2d_5`

All coefficients in the resulting complement rule table are exact integers. The explicit 23-channel table is serialized in `sg194_double_complement_rule_solve_v1.json`.

## 4. Exact rank data after the patch

Complement-only after patch:

- current/external/union/intersection = `7 / 7 / 7 / 7`
- current-only/external-only = `0 / 0`

Full 33 after patch:

- current/external/union/intersection = `10 / 10 / 10 / 10`
- current-only/external-only = `0 / 0`

## 5. Final verdict

- complement exact equality reached: `True`
- full 33 global alignment reached: `True`

This round therefore closes the SG194 double complement residual mathematically. The old global residual does not survive this versioned patch.

## 6. Single / double relation

The current bug is spinorial-only. The single line is the clean baseline for this bug class because it does not have a separate spinorial complement channel builder. After this patch, both lines are source-layer-driven and auditable, but only the double line needs the complement row-basis translation table.

## 7. Remaining engineering work

The SG194 double complement obstruction is closed for this group. The remaining work is no longer “patch this SG194 residual again”; it is to decide whether this exact null-relation solve should be generalized into a reusable spinorial construction routine beyond SG194.
