# SG194 mismatch localization report

        ## 1. Historical failure chain and why previous steps did not close
        Earlier SG194 work correctly separated AI-only and BS-only comparisons, but it still stopped at rank statements. The unresolved gap was object localization: no earlier artifact pinned the residuals to exact generators, exact Wyckoff families, exact local irrep/corep labels, exact HSP row blocks, and exact merge-rule candidates. That is why previous steps could say “single both” and “double AI” without yielding a minimal code patch target.

        ## 2. Single AI mismatch localization
        The single AI images have equal rank 13 on both sides, but their union has rank 14. The mismatch is therefore a one-dimensional substitution, not a missing-rank failure.

        Current-only representative on the generator domain:
        `[
  {
    "generator_id": "a_A1g",
    "coeff": 1,
    "family_id": "a",
    "family_kind": "point-like",
    "local_object_label": "A1g",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "b_A2''",
    "coeff": 1,
    "family_id": "b",
    "family_kind": "point-like",
    "local_object_label": "A2''",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "c_A2''",
    "coeff": 1,
    "family_id": "c",
    "family_kind": "point-like",
    "local_object_label": "A2''",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "d_A2''",
    "coeff": 1,
    "family_id": "d",
    "family_kind": "point-like",
    "local_object_label": "A2''",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "e_A1",
    "coeff": 1,
    "family_id": "e",
    "family_kind": "parametric",
    "local_object_label": "A1",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "f_A1",
    "coeff": 1,
    "family_id": "f",
    "family_kind": "parametric",
    "local_object_label": "A1",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "g_Ag",
    "coeff": 1,
    "family_id": "g",
    "family_kind": "point-like",
    "local_object_label": "Ag",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "h_B2",
    "coeff": 1,
    "family_id": "h",
    "family_kind": "parametric",
    "local_object_label": "B2",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "i_A",
    "coeff": 1,
    "family_id": "i",
    "family_kind": "parametric",
    "local_object_label": "A",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "j_A'",
    "coeff": 1,
    "family_id": "j",
    "family_kind": "parametric",
    "local_object_label": "A'",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "k_A''",
    "coeff": 1,
    "family_id": "k",
    "family_kind": "parametric",
    "local_object_label": "A''",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "l_A",
    "coeff": 1,
    "family_id": "l",
    "family_kind": "parametric",
    "local_object_label": "A",
    "local_object_kind": "single_local_irrep"
  }
]`

        External-only representative on the generator domain:
        `[
  {
    "generator_id": "a_A2g",
    "coeff": 1,
    "family_id": "a",
    "family_kind": "point-like",
    "local_object_label": "A2g",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "b_A2'",
    "coeff": 1,
    "family_id": "b",
    "family_kind": "point-like",
    "local_object_label": "A2'",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "c_A2'",
    "coeff": 1,
    "family_id": "c",
    "family_kind": "point-like",
    "local_object_label": "A2'",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "d_A2'",
    "coeff": 1,
    "family_id": "d",
    "family_kind": "point-like",
    "local_object_label": "A2'",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "e_A2",
    "coeff": 1,
    "family_id": "e",
    "family_kind": "parametric",
    "local_object_label": "A2",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "f_A2",
    "coeff": 1,
    "family_id": "f",
    "family_kind": "parametric",
    "local_object_label": "A2",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "g_Bg",
    "coeff": 1,
    "family_id": "g",
    "family_kind": "point-like",
    "local_object_label": "Bg",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "h_B1",
    "coeff": 1,
    "family_id": "h",
    "family_kind": "parametric",
    "local_object_label": "B1",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "i_B",
    "coeff": 1,
    "family_id": "i",
    "family_kind": "parametric",
    "local_object_label": "B",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "j_A'",
    "coeff": 1,
    "family_id": "j",
    "family_kind": "parametric",
    "local_object_label": "A'",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "k_A''",
    "coeff": 1,
    "family_id": "k",
    "family_kind": "parametric",
    "local_object_label": "A''",
    "local_object_kind": "single_local_irrep"
  },
  {
    "generator_id": "l_A",
    "coeff": 1,
    "family_id": "l",
    "family_kind": "parametric",
    "local_object_label": "A",
    "local_object_kind": "single_local_irrep"
  }
]`

        Exact HSP row witnesses:
        - current-only witness: `P1_R3`
        - external-only witness: `GM:*GM_2+`

        Family-by-family interpretation of the representative substitution:
        `[
  "a: current representative uses A1g while external representative uses A2g",
  "b: current representative uses A2'' while external representative uses A2'",
  "c: current representative uses A2'' while external representative uses A2'",
  "d: current representative uses A2'' while external representative uses A2'",
  "e: current representative uses A1 while external representative uses A2",
  "f: current representative uses A1 while external representative uses A2",
  "g: current representative uses Ag while external representative uses Bg",
  "h: current representative uses B2 while external representative uses B1",
  "i: current representative uses A while external representative uses B"
]`

        ## 3. Single BS residual mismatch after AI correction
        Current projected BS rank is 18, while the external ordinary span rank is 13. The raw current-only BS difference has dimension 13, and the external-only BS difference has dimension 8.

        After enlarging the external span by the current AI image, 9 of the current-only BS directions are absorbed. This is the exact AI-induced part of the BS mismatch. The independent residual has dimension 4 and equals the following raw current BS basis ids:
        `[
  "194_1_1_1_single_bs_raw_basis_04",
  "194_1_1_1_single_bs_raw_basis_06",
  "194_1_1_1_single_bs_raw_basis_19",
  "194_1_1_1_single_bs_raw_basis_14"
]`

        The residual object `single_bs_residual_after_ai_fix` is exact and explicit in `sg194_single_bs_mismatch_localization.json`; it is not a heuristic interpretation.

        ## 4. Double delta localization
        The double mismatch remains localized to the two current-only AI excess directions `delta_c1_minus_b1` and `delta_d1_minus_b1`.

        Exact merged-channel supports:
        - `delta_c1_minus_b1 = c:E1 - b:E1`
        - `delta_d1_minus_b1 = d:E1 - b:E1`

        Exact generator supports:
        `[
  {
    "generator_id": "c_proj_doubleprime_1d_1",
    "coeff": 1,
    "family_id": "c",
    "local_object_label": "proj_doubleprime_1d_1"
  },
  {
    "generator_id": "c_proj_doubleprime_1d_2",
    "coeff": 1,
    "family_id": "c",
    "local_object_label": "proj_doubleprime_1d_2"
  },
  {
    "generator_id": "b_proj_doubleprime_1d_1",
    "coeff": -1,
    "family_id": "b",
    "local_object_label": "proj_doubleprime_1d_1"
  },
  {
    "generator_id": "b_proj_doubleprime_1d_2",
    "coeff": -1,
    "family_id": "b",
    "local_object_label": "proj_doubleprime_1d_2"
  }
]`
        `[
  {
    "generator_id": "d_proj_doubleprime_1d_1",
    "coeff": 1,
    "family_id": "d",
    "local_object_label": "proj_doubleprime_1d_1"
  },
  {
    "generator_id": "d_proj_doubleprime_1d_2",
    "coeff": 1,
    "family_id": "d",
    "local_object_label": "proj_doubleprime_1d_2"
  },
  {
    "generator_id": "b_proj_doubleprime_1d_1",
    "coeff": -1,
    "family_id": "b",
    "local_object_label": "proj_doubleprime_1d_1"
  },
  {
    "generator_id": "b_proj_doubleprime_1d_2",
    "coeff": -1,
    "family_id": "b",
    "local_object_label": "proj_doubleprime_1d_2"
  }
]`

        Exact HSP block support:
        - `delta_c1_minus_b1`: `{
  "K": 3,
  "L": 2
}`
        - `delta_d1_minus_b1`: `{
  "K": 3,
  "L": 2
}`

        Exact statement vs heuristic statement:
        - exact: `The two delta vectors are linearly independent current-only AI directions.`
        - heuristic: `Both deltas look like one common convention failure in the 2b/2c/2d E1 merge rule, with 2b acting as the anchor and 2c/2d misassigned relative to it.`

        ## 5. Double minimal correction plan
        The minimal patch target is the double AI merge/typing layer, not the BS kernel. The concrete action sequence is:
        1. patch the 2c/2d E1 channel construction so the local-corep pair at 2c/2d is site-aware instead of forced through a site-agnostic E1 pair-sum;
        2. patch the 6h four-way merge normalization so the mixed E3/6h channel is not over-counted;
        3. re-run only the limited AI-only problem-sector alignment check.

        Predicted effect:
        - current aligned rank: 12
        - target aligned rank after fix: 10

        ## 6. Implementation mapping
        The localization pipeline in this step is:
        - raw files: `raw_194_1_1_1_single_ai_candidates.json`, `raw_194_1_1_1_single_bs_basis_raw.json`, `raw_194_1_1_1_double_ai_candidates.json`, `raw_194_1_1_1_double_ai_basis.json`
        - localized single objects: `sg194_single_ai_mismatch_localization.json`, `sg194_single_bs_mismatch_localization.json`
        - localized double objects: `sg194_double_delta_localization.json`
        - actionable fix proposal: `sg194_double_minimal_correction_plan.json`

        This mapping is the reason the current step is executable: the final correction target is not “the quotient” or “the BS code”, but the 2b/2c/2d/6h merge/typing table in the existing SG194 alignment workflow.

        ## 7. Final diagnosis and concrete next code changes
        - single main issue: both
        - single AI-induced BS mismatch dimension: 9
        - single independent BS residual dimension: 4
        - double main issue: AI
        - next code target: patch the double 2b/2c/2d/6h merge/typing logic before touching any BS construction code
