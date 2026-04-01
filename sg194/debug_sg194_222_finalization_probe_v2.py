#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sg194.pipeline_v2 import generic_builders as gb


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="222.1.1.1")
    parser.add_argument("--mode", choices=["single", "double"], default="single")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    bundle = gb.generic_mode_bundle(args.group, args.mode)
    quotient = bundle["quotient"]
    payload = {
        "group": args.group,
        "mode": args.mode,
        "line_capture_canonicalization": bundle["line_capture_canonicalization"],
        "compatibility_matrix_shape": bundle["compatibility"]["matrix_shape"],
        "line_fallbacks": bundle["compatibility"]["line_fallbacks"],
        "plane_fallbacks": bundle["compatibility"]["plane_fallbacks"],
        "dBS": quotient["dBS"],
        "dAI": quotient["dAI"],
        "classification": quotient["classification"],
        "free_rank": quotient["free_rank"],
        "finite_part": quotient["finite_part"],
        "smith_diagonal_nonzero": quotient["smith_diagonal_nonzero"],
        "ai_candidate_count": quotient["ai_candidate_count"],
        "ai_candidate_count_used": quotient["ai_candidate_count_used"],
        "ai_failure_count": quotient["ai_failure_count"],
        "ai_incompatible_count": quotient["ai_incompatible_count"],
        "ai_embedding_failure_count": quotient["ai_embedding_failure_count"],
        "compatibility_check_mode": quotient.get("compatibility_check_mode"),
        "full_shell_rank": quotient.get("full_shell_rank"),
        "point_shell_rank": quotient.get("point_shell_rank"),
        "ai_incompatible_candidates": quotient.get("ai_incompatible_candidates", []),
        "ai_embedding_failures": quotient.get("ai_embedding_failures", []),
        "induction_failures": bundle["induced"]["failures"],
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
