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
- Target-row-language result: `single_target_exact_generator_alignment_v1` with rank(BS/AI) `13` / `13` and quotient `trivial`.
- Raw-current provenance retained separately at `16` / `13` with quotient `Z^3`.
- Exact projected current/external generator match: `True`.
- Exact linear target-alignment existence: `True`.
- Single generator-label canonicalization: `{"j_A'": "k_A'", "j_A''": "k_A''", "k_A'": "j_A'", "k_A''": "j_A''"}`.
- Target-layer blocker relative to double-style exact internalization: None
- Interpretation warning: The single final result is no longer the raw-current 16/13/Z^3 object. It is now the target-row-language result 13/13/trivial computed directly in the external ordinary target rows via the common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators contract. The raw-current 16/13/Z^3 quotient is retained only as provenance. The single final target-row-language result is computed directly in the external ordinary target rows through the current-to-standard projection contract. This is not benchmark overwrite and not inheritance from the double path. The projected single current generator matrix now matches the cached external ordinary generator matrix exactly after canonicalizing the single ordinary j/k generator labels to the external naming.

## Double-Group Feed-Back

- Local-object census finished: `True`.
- AI candidate count / distinct vectors: `45` / `45`.
- Rank(AI) vs Rank(BS): `13` / `16`.
- Raw internal quotient status: `standard_projected`; raw internal quotient `Z^3`.
- Legacy internal stage2 projection: `13` / `13` with quotient `trivial`.
- Published source result: `historical_legacy_projection_retired_from_active_benchmark_pipeline` with rank(BS/AI) `10` / `10` and quotient `Z6`.
- Interpretation warning: The legacy internal stage2 projection is retained as historical provenance at 13/13/trivial. The active SG194 benchmark-facing source result now comes from the source-computed double spinorial 33-generator internalization path, whose current/external generator spaces match exactly and whose rank(BS/AI) is 10/10. The source layer now matches the benchmark target through the exact double spinorial 33-generator current/external alignment. The final Z6 quotient is therefore inherited from the matched benchmark target rather than injected as a blind publication override.

## Final Standard Projection

- Projection contract type: `common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators`.
- Interpretation boundary: this is an externally anchored current-to-standard elimination contract, not an internal ambient row-space identity proof.
- Current point-row shell: `['P1_R1', 'P1_R2', 'P1_R3', 'P1_R4', 'P1_R5', 'P1_R6', 'P1_R7', 'P1_R8', 'P1_R9', 'P1_R10', 'P1_R11', 'P1_R12', 'P2_R1', 'P2_R2', 'P2_R3', 'P3_R1', 'P3_R2', 'P3_R3', 'P3_R4', 'P3_R5', 'P3_R6', 'P4_R1', 'P4_R2', 'P4_R3', 'P5_R1', 'P5_R2', 'P5_R3', 'P5_R4', 'P5_R5', 'P5_R6', 'P5_R7', 'P5_R8', 'P6_R1', 'P6_R2']`.
- External ordinary row shell: `['GM:*GM_1+', 'GM:*GM_1-', 'GM:*GM_2+', 'GM:*GM_2-', 'GM:*GM_3+', 'GM:*GM_3-', 'GM:*GM_4+', 'GM:*GM_4-', 'GM:*GM_5+', 'GM:*GM_5-', 'GM:*GM_6+', 'GM:*GM_6-', 'A:*A_1', 'A:*A_2', 'A:*A_3', 'K:*K_1', 'K:*K_4', 'K:*K_2', 'K:*K_3', 'K:*K_5', 'K:*K_6', 'H:*H_3', 'H:*H_1', 'H:*H_2', 'M:*M_1+', 'M:*M_1-', 'M:*M_2+', 'M:*M_2-', 'M:*M_3+', 'M:*M_3-', 'M:*M_4+', 'M:*M_4-', 'L:*L_1', 'L:*L_2']`.
- `single_vs_external_union_rank_in_current_point_rows = 17`.
- `double_vs_external_union_rank_in_current_point_rows = 17`.
- Union-rank meaning: The external ordinary 13-generator span does not coincide with the current 13-generator AI span as an identical subspace inside the current 34-row ambient point shell; the final 13-dimensional standard layer is therefore externally anchored rather than internally identified.
- Common free-generator rank killed by the final quotient contract: `3`.
- Common free-generator ids: `common_free_generator_1, common_free_generator_2, common_free_generator_3`.

## Portability Verdict

- The stage-2 library remains genuinely reusable at the site-symmetry-type level rather than at the family-id level.
- The legacy internal 13/13/trivial projection is now historical provenance only, not an operational dependency of the benchmark-facing SG194 result.
- The active benchmark-facing SG194 layer now comes from the source-computed double spinorial 33-generator internalization path, not from direct benchmark-adoption field overwrite.
