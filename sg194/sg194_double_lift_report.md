# SG194 Double Lift Report

## 1. Why previous metrics still did not close the problem

The v2 metric compared the column spaces of the transposed current and external problem-sector matrices. That was a legitimate row-space test in the common 10-generator domain, but it was still only a proxy. It did not exhibit a concrete map from the 34 current-HSP rows to the 56 external spinorial rows, so it could not deliver an honest external-language verdict for lifted current vectors.

## 2. Trusted problem-sector inventory

The trusted sector consists of 10 generators ordered as:

`['b:E1↑G(4)', 'b:E2↑G(4)', 'b:E3↑G(4)', 'c:E1↑G(4)', 'c:E2↑G(4)', 'c:E3↑G(4)', 'd:E1↑G(4)', 'd:E2↑G(4)', 'd:E3↑G(4)', 'h:E↑G(12)']`

Current rows come from the 34-row HSP ambient with blocks `['P1', 'P2', 'P3', 'P5', 'P6', 'B1']`. External rows come from the 56-row spinorial ambient, with actual support in blocks `['A', 'Γ', 'H', 'K', 'L', 'M']`.

## 3. Explicit row-basis lift construction

A rational lift exists and satisfies exact equality:

`L_problem * C_patched_problem = E_problem`

on the trusted sector. The lift uses the current row basis

`['P1_R1', 'P1_R2', 'P1_R9', 'P3_R1', 'P3_R2', 'B1_R1']`

and reaches the external basis

`['A:A5', 'A:A6', 'Γ:Γ8', 'H:H5', 'H:H7', 'K:K8']`.

The exact lift is rational, not integral. The Smith diagonal of `C_problem^T` is `[1, 1, 1, 2, 2, 2]`, so the last three coordinates impose parity conditions that some external rows violate.

## 4. External verdict for the two delta directions

- `delta_c1_minus_b1`: zero = `False`, status = `nonzero_external_span_direction_not_residual_mismatch`
- `delta_d1_minus_b1`: zero = `False`, status = `nonzero_external_span_direction_not_residual_mismatch`

So the deltas do not vanish; they are reinterpreted as honest external-span directions. They are no longer independent residual mismatches after the lift is applied.

## 5. Updated patch verdict

The patched SG194 double generators are truly aligned with the external trusted problem sector once we use the explicit rational row lift. The trusted-sector patch verdict is therefore positive. The remaining limitation is not generator mismatch in this sector; it is only the absence of a full-space explicit lift outside this round's scope.

## 6. Next engineering step

Trusted-sector BS-only comparison is now justified. Full 33-generator global BS-only is still not certified in this round, because the explicit lift was only built on the trusted sector.
