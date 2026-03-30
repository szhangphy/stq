# Finite Indicator Extraction Audit

## Why Raw Quotients Are Not Final Indicator Groups

- The raw quotient is the exact integer cokernel `coker(AI -> BS)`.
- Standard symmetry-indicator language is reserved for the finite torsion sector, not for any free abelian crystalline directions that remain in the raw quotient.
- Therefore `Z^n` or `Z^m x finite torsion` cannot be reported to users as a final finite symmetry-indicator group without a clean free/torsion split.

## Four-Case Summary

| case | raw quotient | free part | finite indicator candidate | confidence |
| --- | --- | --- | --- | --- |
| `10.4.1.31` / `1` | `Z2 x Z2` | `trivial` | `Z2 x Z2` | `high` |
| `10.4.1.31` / `2` | `Z^2 x Z2 x Z2 x Z2 x Z2` | `Z^2` | `Z2 x Z2 x Z2 x Z2` | `high` |
| `194.1.1.1` / `1` | `Z^16` | `Z^16` | `trivial` | `medium` |
| `194.1.1.1` / `2` | `Z^16` | `Z^16` | `trivial` | `medium` |

## Case Notes

### 10.4.1.31 / groupType=1

- Raw quotient: `Z2 x Z2`.
- Free crystalline invariant part: `trivial`.
- Finite symmetry-indicator candidate: `Z2 x Z2`.
- Confidence: `high`.
- Still missing step: none within the current raw/SNF formalism
- User-facing interpretation: This case is already purely torsion at the raw quotient level, so the finite symmetry-indicator candidate is the same Z2 x Z2.
- Exact Smith diagonal (nonzero entries): `[1, 1, 1, 1, 1, 1, 2, 2]`.

### 10.4.1.31 / groupType=2

- Raw quotient: `Z^2 x Z2 x Z2 x Z2 x Z2`.
- Free crystalline invariant part: `Z^2`.
- Finite symmetry-indicator candidate: `Z2 x Z2 x Z2 x Z2`.
- Confidence: `high`.
- Still missing step: Only reporting-layer cleanup remains: reserve indicator language for the torsion subgroup and report Z^2 separately as free crystalline invariants.
- User-facing interpretation: Report the full raw quotient as Z^2 x Z2^4, but call only the exact torsion subgroup Z2^4 the finite symmetry-indicator candidate.
- Exact Smith diagonal (nonzero entries): `[1, 1, 2, 2, 2, 2]`.

### 194.1.1.1 / groupType=1

- Raw quotient: `Z^16`.
- Free crystalline invariant part: `Z^16`.
- Finite symmetry-indicator candidate: `trivial`.
- Confidence: `medium`.
- Still missing step: A physically justified quotient that mods out the free crystalline subgroup before comparison to standard finite symmetry-indicator tables.
- User-facing interpretation: The current result is a free-only raw quotient Z^16. In standard finite-indicator language no nontrivial finite torsion sector has been isolated.
- Exact Smith diagonal (nonzero entries): `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.

### 194.1.1.1 / groupType=2

- Raw quotient: `Z^16`.
- Free crystalline invariant part: `Z^16`.
- Finite symmetry-indicator candidate: `trivial`.
- Confidence: `medium`.
- Still missing step: A physically justified quotient that removes the 16 free crystalline directions before any comparison to a standard finite double-group indicator table.
- User-facing interpretation: The current result is again a free-only raw quotient Z^16. The finite symmetry-indicator candidate is trivial unless an additional physical quotient produces residual torsion.
- Exact Smith diagonal (nonzero entries): `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.

## Stabilized User-Facing Language

- `10.4.1.31 / single`: the raw quotient is already finite, so `Z2 x Z2` remains the finite symmetry-indicator candidate.
- `10.4.1.31 / double`: the raw quotient is `Z^2 x Z2^4`, but only `Z2^4` is the finite symmetry-indicator candidate; the `Z^2` sector must be reported separately as free crystalline invariants.
- `194.1.1.1 / single`: the raw quotient is `Z^16`; no finite torsion is present, so the current finite symmetry-indicator candidate is trivial unless a later physical quotient leaves residual torsion.
- `194.1.1.1 / double`: same correction as the single case; do not call `Z^16` a finite indicator group.
