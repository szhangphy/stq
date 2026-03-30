# Reinterpretation: 10.4.1.31 / groupType=2

- Raw quotient: `Z^2 x Z2 x Z2 x Z2 x Z2`.
- Free part: `Z^2`.
- Finite torsion extracted directly from exact Smith audit: `Z2 x Z2 x Z2 x Z2`.
- Finite symmetry-indicator candidate: `Z2 x Z2 x Z2 x Z2`.
- Confidence: `high`.
- Result after modding out the full free subgroup candidate: `Z2 x Z2 x Z2 x Z2`.

## Interpretation

The Smith decomposition canonically splits the raw quotient into free rank 2 and four order-2 torsion slots.

## User-Facing Language

Report the full raw quotient as Z^2 x Z2^4, but call only the exact torsion subgroup Z2^4 the finite symmetry-indicator candidate.

## Still Missing Step

Only reporting-layer cleanup remains: reserve indicator language for the torsion subgroup and report Z^2 separately as free crystalline invariants.
