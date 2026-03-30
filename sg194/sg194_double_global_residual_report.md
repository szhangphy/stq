# SG194 Double Global Residual Report

## 1. What is already solved: trusted 10-generator sector

The trusted `2b/2c/2d/6h` sector has already been removed from the unresolved problem. Its explicit rational lift is accepted and is not revisited here.

## 2. Full 33-generator decomposition

The full aligned generator domain is split into:

- trusted sector common indices `[6, 7, 8, 9, 10, 11, 12, 13, 14, 25]`
- complement common indices `[0, 1, 2, 3, 4, 5, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32]`

The unresolved object is therefore only the 23-generator complement.

## 3. Complement-only comparison

Exact complement ranks are:

- current rank = `9`
- external rank = `7`
- union rank = `12`
- intersection rank = `4`

So the complement carries `5` current-only dimensions and `3` external-only dimensions.

## 4. Complement lift or obstruction

No complement lift exists, even over `Q`. The exact obstruction is row-space containment failure: the external complement has a 3-dimensional basis outside the current complement row span.

## 5. Residual mismatch localization

The important engineering fact is that every individual family block embeds locally, but the full complement still mismatches globally. Therefore the residual is cross-family rather than family-local. The obstruction witnesses use current rows in block `['P1']` and external rows in blocks `['A', 'Γ']`.

## 6. Next source-level patch target

The next patch target is `debug_workflow_portability_stage2_194.1.1.1.py`, function `build_sg194_double_spinorial_generators`. The b/c/d/h trusted-sector rules are not the issue anymore. The unresolved source assumption is the unchanged identity one-to-one reuse of the complement families `a/e/f/g/i/j/k/l`.
