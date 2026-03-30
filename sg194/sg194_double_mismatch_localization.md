# SG194 double mismatch localization

        ## Exact delta localization
        - `delta_c1_minus_b1` support on merged channels: `c:E1 - b:E1`
        - `delta_d1_minus_b1` support on merged channels: `d:E1 - b:E1`

        `delta_c1_minus_b1`:
        {
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
}

        `delta_d1_minus_b1`:
        {
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
}

        ## Minimal correction plan
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
  "final_diagnosis": "The minimal correction path is at the double AI merge/typing layer. A BS-only patch is not justified yet."
}
