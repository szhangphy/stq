# SG194 mismatch localization audit

        This audit does not introduce any new quotient claim. It only localizes the already-separated mismatches to the smallest concrete objects available in the existing raw and external artifacts.

        ## Single
        - AI mismatch dimension: 1
        - Current AI rank / external AI rank: 13 / 13
        - Current-only BS difference dimension: 13
        - External-only BS difference dimension: 8
        - AI-induced BS mismatch dimension: 9
        - Independent BS residual dimension: 4

        The 4 independent residual BS directions are exactly:
        [
  {
    "id": "single_bs_residual_after_ai_fix_01",
    "vector_on_34_point_space": [
      0,
      2,
      -1,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      2,
      -1,
      0,
      0,
      1,
      0,
      0,
      1,
      0,
      0,
      0,
      0
    ],
    "support_on_hsp_rows": [
      {
        "label": "P1_R2",
        "coeff": 2
      },
      {
        "label": "P1_R3",
        "coeff": -1
      },
      {
        "label": "P1_R6",
        "coeff": 1
      },
      {
        "label": "P2_R1",
        "coeff": 1
      },
      {
        "label": "P5_R2",
        "coeff": 2
      },
      {
        "label": "P5_R3",
        "coeff": -1
      },
      {
        "label": "P5_R6",
        "coeff": 1
      },
      {
        "label": "P6_R1",
        "coeff": 1
      }
    ],
    "support_blocks": {
      "A": 1,
      "GM": 3,
      "H": 3,
      "M": 1
    },
    "matching_current_raw_bs_basis_id": "194_1_1_1_single_bs_raw_basis_04"
  },
  {
    "id": "single_bs_residual_after_ai_fix_02",
    "vector_on_34_point_space": [
      0,
      -1,
      1,
      0,
      0,
      -1,
      1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      -1,
      1,
      0,
      0,
      -1,
      1,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "support_on_hsp_rows": [
      {
        "label": "P1_R2",
        "coeff": -1
      },
      {
        "label": "P1_R3",
        "coeff": 1
      },
      {
        "label": "P1_R6",
        "coeff": -1
      },
      {
        "label": "P1_R7",
        "coeff": 1
      },
      {
        "label": "P5_R2",
        "coeff": -1
      },
      {
        "label": "P5_R3",
        "coeff": 1
      },
      {
        "label": "P5_R6",
        "coeff": -1
      },
      {
        "label": "P5_R7",
        "coeff": 1
      }
    ],
    "support_blocks": {
      "GM": 4,
      "H": 4
    },
    "matching_current_raw_bs_basis_id": "194_1_1_1_single_bs_raw_basis_06"
  },
  {
    "id": "single_bs_residual_after_ai_fix_03",
    "vector_on_34_point_space": [
      -1,
      0,
      0,
      1,
      0,
      1,
      -1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "support_on_hsp_rows": [
      {
        "label": "P1_R1",
        "coeff": -1
      },
      {
        "label": "P1_R4",
        "coeff": 1
      },
      {
        "label": "P1_R6",
        "coeff": 1
      },
      {
        "label": "P1_R7",
        "coeff": -1
      }
    ],
    "support_blocks": {
      "GM": 4
    },
    "matching_current_raw_bs_basis_id": "194_1_1_1_single_bs_raw_basis_19"
  },
  {
    "id": "single_bs_residual_after_ai_fix_04",
    "vector_on_34_point_space": [
      -2,
      1,
      0,
      1,
      -1,
      2,
      -1,
      0,
      0,
      0,
      0,
      0,
      1,
      -1,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0
    ],
    "support_on_hsp_rows": [
      {
        "label": "P1_R1",
        "coeff": -2
      },
      {
        "label": "P1_R2",
        "coeff": 1
      },
      {
        "label": "P1_R4",
        "coeff": 1
      },
      {
        "label": "P1_R5",
        "coeff": -1
      },
      {
        "label": "P1_R6",
        "coeff": 2
      },
      {
        "label": "P1_R7",
        "coeff": -1
      },
      {
        "label": "P2_R1",
        "coeff": 1
      },
      {
        "label": "P2_R2",
        "coeff": -1
      }
    ],
    "support_blocks": {
      "A": 2,
      "GM": 6
    },
    "matching_current_raw_bs_basis_id": "194_1_1_1_single_bs_raw_basis_14"
  }
]

        ## Double
        - delta objects: `delta_c1_minus_b1`, `delta_d1_minus_b1`
        - current problem-sector union/intersection rank: 8 / 4
        - current global aligned rank / external spinorial rank: 12 / 10

        Exact localized delta payload:
        {
  "group": "194.1.1.1",
  "group_type": 2,
  "current_raw_ai_rank": 13,
  "current_count_aligned_rank": 12,
  "external_spinorial_rank": 10,
  "problem_sector_current_rank": 6,
  "problem_sector_external_rank": 6,
  "problem_sector_union_rank": 8,
  "problem_sector_intersection_rank": 4,
  "delta_c1_minus_b1": {
    "id": "delta_c1_minus_b1",
    "current_generator_support": [
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
    ],
    "merged_channel_support": [
      {
        "label": "c:E1",
        "coeff": 1
      },
      {
        "label": "b:E1",
        "coeff": -1
      }
    ],
    "relevant_families": [
      "2c",
      "2b"
    ],
    "relevant_local_coreps": [
      "proj_doubleprime_1d_1",
      "proj_doubleprime_1d_2"
    ],
    "support_on_current_hsp_rows": [
      {
        "label": "P3_R1",
        "coeff": -2
      },
      {
        "label": "P3_R3",
        "coeff": -2
      },
      {
        "label": "P3_R5",
        "coeff": 2
      },
      {
        "label": "B1_R1",
        "coeff": 2
      },
      {
        "label": "B1_R3",
        "coeff": -2
      }
    ],
    "support_blocks": {
      "K": 3,
      "L": 2
    },
    "diagnosis": "Exact delta direction between the site-merged E1 channel at 2c and the corresponding 2b reference channel."
  },
  "delta_d1_minus_b1": {
    "id": "delta_d1_minus_b1",
    "current_generator_support": [
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
    ],
    "merged_channel_support": [
      {
        "label": "d:E1",
        "coeff": 1
      },
      {
        "label": "b:E1",
        "coeff": -1
      }
    ],
    "relevant_families": [
      "2d",
      "2b"
    ],
    "relevant_local_coreps": [
      "proj_doubleprime_1d_1",
      "proj_doubleprime_1d_2"
    ],
    "support_on_current_hsp_rows": [
      {
        "label": "P3_R1",
        "coeff": -2
      },
      {
        "label": "P3_R3",
        "coeff": -2
      },
      {
        "label": "P3_R5",
        "coeff": 2
      },
      {
        "label": "B1_R2",
        "coeff": 2
      },
      {
        "label": "B1_R3",
        "coeff": -2
      }
    ],
    "support_blocks": {
      "K": 3,
      "L": 2
    },
    "diagnosis": "Exact delta direction between the site-merged E1 channel at 2d and the corresponding 2b reference channel."
  },
  "exact_problem_sector_current_only_basis": [
    [
      {
        "label": "2b:E3",
        "coeff": 1
      },
      {
        "label": "2c:E3",
        "coeff": 1
      },
      {
        "label": "2d:E3",
        "coeff": 1
      },
      {
        "label": "6h:E",
        "coeff": 2
      }
    ],
    [
      {
        "label": "2c:E1",
        "coeff": -2
      },
      {
        "label": "2c:E3",
        "coeff": 1
      },
      {
        "label": "2d:E1",
        "coeff": -2
      },
      {
        "label": "2d:E3",
        "coeff": 1
      }
    ]
  ],
  "exact_problem_sector_external_only_basis": [
    [
      {
        "label": "2b:E3",
        "coeff": 1
      },
      {
        "label": "2c:E3",
        "coeff": 1
      },
      {
        "label": "2d:E3",
        "coeff": 1
      },
      {
        "label": "6h:E",
        "coeff": 1
      }
    ],
    [
      {
        "label": "2c:E1",
        "coeff": 1
      },
      {
        "label": "2c:E3",
        "coeff": -1
      },
      {
        "label": "2d:E2",
        "coeff": 1
      },
      {
        "label": "2d:E3",
        "coeff": -1
      }
    ]
  ],
  "common_vs_independent_diagnosis": {
    "exact_part": "The two delta vectors are linearly independent current-only AI directions.",
    "heuristic_part": "Both deltas look like one common convention failure in the 2b/2c/2d E1 merge rule, with 2b acting as the anchor and 2c/2d misassigned relative to it."
  }
}

        Minimal correction plan:
        {
  "group": "194.1.1.1",
  "group_type": 2,
  "main_issue": "AI-sector problem-site merge/typing mismatch, not yet a proven BS mismatch",
  "do_not_change_first": [
    "Do not patch BS kernel construction first.",
    "Do not delete BS basis directions first.",
    "Do not touch unrelated families outside 2b/2c/2d/6h first."
  ],
  "minimal_actions": [
    {
      "step": 1,
      "target_object": "2c/2d E1 channel construction",
      "change_type": "merge-rule and typing correction",
      "exact_basis_evidence": [
        {
          "label": "2c:E1",
          "coeff": 1
        },
        {
          "label": "2c:E3",
          "coeff": -1
        },
        {
          "label": "2d:E2",
          "coeff": 1
        },
        {
          "label": "2d:E3",
          "coeff": -1
        }
      ],
      "proposal": "Replace the site-agnostic pair-sum rule `(proj_doubleprime_1d_1 + proj_doubleprime_1d_2) -> E1` at 2c/2d by a Bilbao-content-matched assignment. The 2d pair currently labeled as E1 must be reconsidered against the external `d:E2` channel.",
      "exact_or_heuristic": "heuristic correction proposal backed by exact residual basis support"
    },
    {
      "step": 2,
      "target_object": "6h four-way merge",
      "change_type": "normalization correction",
      "exact_basis_evidence": [
        {
          "label": "2b:E3",
          "coeff": 1
        },
        {
          "label": "2c:E3",
          "coeff": 1
        },
        {
          "label": "2d:E3",
          "coeff": 1
        },
        {
          "label": "6h:E",
          "coeff": 2
        }
      ],
      "proposal": "Reduce the effective 6h coefficient in the mixed E3/h channel from 2 to 1, i.e. stop using the current four-way sum as an unnormalized Bilbao `E` generator.",
      "exact_or_heuristic": "heuristic correction proposal backed by exact current-only basis support"
    },
    {
      "step": 3,
      "target_object": "alignment table in audit/workflow merge logic",
      "change_type": "site-aware alignment table",
      "proposal": "Patch the hardcoded merge tables around the existing pair-sum/four-way-sum rules in `debug_sg194_standard_alignment_v2.py` and any mirrored workflow code. The relevant object is the 2b/2c/2d/6h generator-to-Bilbao channel map, not the BS kernel code.",
      "exact_or_heuristic": "heuristic but directly actionable"
    }
  ],
  "predicted_problem_sector_effect": {
    "current_problem_sector_union_rank": 8,
    "external_problem_sector_rank": 6,
    "expected_rank_after_fix": 6,
    "current_global_count_aligned_rank": 12,
    "expected_global_rank_after_fix": 10
  },
  "delta_explanation": {
    "delta_c1_minus_b1": "current generator support = c:E1 - b:E1 = c_proj_doubleprime_1d_1 + c_proj_doubleprime_1d_2 - b_proj_doubleprime_1d_1 - b_proj_doubleprime_1d_2",
    "delta_d1_minus_b1": "current generator support = d:E1 - b:E1 = d_proj_doubleprime_1d_1 + d_proj_doubleprime_1d_2 - b_proj_doubleprime_1d_1 - b_proj_doubleprime_1d_2"
  },
  "final_diagnosis": "The minimal correction path is at the double AI merge/typing layer. A BS-only patch is not justified yet.",
  "bs_only_status": "blocked",
  "bs_only_blocker": "A BS-only external comparison cannot yet be completed. The cached external spinorial object is a generator matrix in a 56-row Bilbao basis, whereas the current BS basis lives in a 34-row current point-space after restriction. No BS-only lift from the current 34-row point coordinates to the 56-row Bilbao spinorial basis is available without reusing AI/generator alignment machinery."
}
