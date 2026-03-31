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
- Raw internal quotient status: `standard_projected`; raw internal quotient `Z^3`.
- Standard-space projection status: `implemented` with final rank(BS/AI) `13` / `13` and quotient `trivial`.
- Interpretation warning: The raw internal quotient is retained as provenance, and the final SG194 ordinary standard quotient is now computed through the explicit current-to-standard elimination contract.

## Double-Group Feed-Back

- Local-object census finished: `True`.
- AI candidate count / distinct vectors: `45` / `45`.
- Rank(AI) vs Rank(BS): `13` / `16`.
- Raw internal quotient status: `standard_projected`; raw internal quotient `Z^3`.
- Standard-space projection status: `implemented` with final rank(BS/AI) `13` / `13` and quotient `trivial`.
- Interpretation warning: The raw internal quotient is retained as provenance, and the final SG194 ordinary standard quotient is now computed through the explicit current-to-standard elimination contract.

## Final Standard Projection

- Projection contract type: `common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators`.
- Current point-row shell: `['P1_R1', 'P1_R2', 'P1_R3', 'P1_R4', 'P1_R5', 'P1_R6', 'P1_R7', 'P1_R8', 'P1_R9', 'P1_R10', 'P1_R11', 'P1_R12', 'P2_R1', 'P2_R2', 'P2_R3', 'P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P3_R5', 'P3_R6', 'P4_R1', 'P4_R2', 'P4_R3', 'P5_R1', 'P5_R2', 'P5_R3', 'P5_R4', 'P5_R5', 'P5_R6', 'P5_R7', 'P5_R8', 'P6_R1', 'P6_R2']`.
- External ordinary row shell: `['GM:*GM_1+', 'GM:*GM_1-', 'GM:*GM_2+', 'GM:*GM_2-', 'GM:*GM_3+', 'GM:*GM_3-', 'GM:*GM_4+', 'GM:*GM_4-', 'GM:*GM_5+', 'GM:*GM_5-', 'GM:*GM_6+', 'GM:*GM_6-', 'A:*A_1', 'A:*A_2', 'A:*A_3', 'K:*K_1', 'K:*K_4', 'K:*K_2', 'K:*K_3', 'K:*K_5', 'K:*K_6', 'H:*H_3', 'H:*H_1', 'H:*H_2', 'M:*M_1+', 'M:*M_1-', 'M:*M_2+', 'M:*M_2-', 'M:*M_3+', 'M:*M_3-', 'M:*M_4+', 'M:*M_4-', 'L:*L_1', 'L:*L_2']`.
- Common free-generator rank killed by the final quotient contract: `3`.
- Common free-generator ids: `common_free_generator_1, common_free_generator_2, common_free_generator_3`.

## Portability Verdict

- The stage-2 library remains genuinely reusable at the site-symmetry-type level rather than at the family-id level.
- The missing standard-space projection is now implemented mechanically rather than left as a documentation boundary.
- Single and double now both land in the same final 13-dimensional ordinary SG194 standard BS layer with trivial final quotient.
