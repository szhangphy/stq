# Workflow Portability Stage-2 Audit for 194.1.1.1

## Fixed Blocker

- This round fills the stage-1 blocker: a reusable SG 194 local site-symmetry library is now built for the non-abelian families, and the abelian follow-on families are also enumerated so the AI induction can be rerun honestly.

## Non-Abelian Inventory

- Primary non-abelian families: `f, e, d, c, b, a`.
- Type split: `C3v / 3m` on `e,f`; `D3d-like / -3m` on `a`; `D3h-like / -6m2` on `b,c,d`.
- In the present controlled SG 194 case the site symmetries remain purely unitary, so the double-group side uses projective local irreps under `factor_su2` rather than antiunitary Wigner-corep extensions.

## Single-Group Feed-Back

- Local-object census finished: `True`.
- AI candidate count / distinct vectors: `45` / `45`.
- Rank(AI) vs Rank(BS): `13` / `16`.
- Raw internal quotient status: `raw_internal_extracted`; raw internal quotient `Z^3`.
- Standard-space projection status: `missing`.
- Interpretation warning: This quotient is computed in the 16-dimensional raw internal BS space and must not yet be reported as the final SG194 standard indicator.

## Double-Group Feed-Back

- Local-object census finished: `True`.
- AI candidate count / distinct vectors: `45` / `45`.
- Rank(AI) vs Rank(BS): `13` / `16`.
- Raw internal quotient status: `raw_internal_extracted`; raw internal quotient `Z^3`.
- Standard-space projection status: `missing`.
- Interpretation warning: This quotient is computed in the 16-dimensional raw internal BS space and must not yet be reported as the final SG194 standard indicator.

## Portability Verdict

- The stage-2 library is genuinely reusable at the site-symmetry-type level rather than at the family-id level.
- The single-group portability statement is upgraded from pilot success to a full local-library-backed AI completion on the fixed second group.
- The double-group portability statement is now stronger than the stage-1 seed: the SG 194 projective local library is in place and can be fed through the same induction route.
- The remaining blocker is no longer local-library construction. It is the missing projection from the raw internal BS-space quotient to the final SG194 standard indicator layer.
