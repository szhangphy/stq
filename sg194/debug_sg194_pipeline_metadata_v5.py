#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.coordinates import coordinate_usage_audit
from sg194.pipeline_v2.utils import now_iso, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
CONSISTENCY_JSON = SG194_DIR / "sg194_pipeline_consistency_checks_v8.json"
CONSISTENCY_MD = SG194_DIR / "sg194_pipeline_consistency_checks_v8.md"
STATUS_JSON = SG194_DIR / "sg194_pipeline_status_semantics_v5.json"
STATUS_MD = SG194_DIR / "sg194_pipeline_status_semantics_v5.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    regression_194 = load_json(SG194_DIR / "sg194_194_generic_regression_v1.json")
    purity = load_json(SG194_DIR / "sg194_generic_path_purity_audit_v1.json")
    generality = load_json(SG194_DIR / "sg194_generality_verdict_v3.json")
    summary_222 = load_json(SG194_DIR / "sg194_222_generic_final_classification_summary_v1.json")
    ai_fix_222 = load_json(SG194_DIR / "sg194_ai_filter_bug_fix_v2.json")
    dropped_222 = load_json(SG194_DIR / "sg194_dropped_ai_candidates_v3.json")
    oracle_222 = load_json(SG194_DIR / "sg194_222_generic_vs_topmat_oracle_v1.json")
    coord_audit = coordinate_usage_audit()

    synthetic_checks = [
        {
            "name": "backend_free_generic_path",
            "passed": purity["backend_free_generic_path"],
            "actual": purity["backend_free_generic_path"],
        },
        {
            "name": "coordinate_contract_audit",
            "passed": coord_audit["all_passed"],
            "actual": coord_audit["violations"],
        },
        {
            "name": "194_single_matches_accepted_special",
            "passed": regression_194["matches_accepted_special"]["single"],
            "actual": regression_194["single"],
        },
        {
            "name": "194_double_matches_accepted_special",
            "passed": regression_194["matches_accepted_special"]["double"],
            "actual": regression_194["double"],
        },
        {
            "name": "222_single_has_no_rejected_ai_candidates",
            "passed": dropped_222["single"]["ai_incompatible_count"] == 0 and dropped_222["single"]["ai_embedding_failure_count"] == 0,
            "actual": dropped_222["single"],
            "required": False,
        },
        {
            "name": "222_double_has_no_rejected_ai_candidates",
            "passed": dropped_222["double"]["ai_incompatible_count"] == 0 and dropped_222["double"]["ai_embedding_failure_count"] == 0,
            "actual": dropped_222["double"],
            "required": False,
        },
        {
            "name": "222_matches_oracle",
            "passed": oracle_222["matches_oracle"]["single"] and oracle_222["matches_oracle"]["double"],
            "actual": oracle_222["matches_oracle"],
            "required": False,
        },
    ]
    required_checks = [item for item in synthetic_checks if item.get("required", True)]
    diagnostic_checks = [item for item in synthetic_checks if not item.get("required", True)]

    consistency = {
        "generated_at": now_iso(),
        "scope": "backend_free_generic_path_v1",
        "backend_free_generic_path": purity["backend_free_generic_path"],
        "truly_general": generality["truly_general"],
        "coordinate_contract_audit": coord_audit,
        "synthetic_checks": synthetic_checks,
        "checks_passed": all(item["passed"] for item in required_checks),
        "diagnostic_checks_passed": all(item["passed"] for item in diagnostic_checks) if diagnostic_checks else True,
        "generic_194_regression": {
            "single": regression_194["single"],
            "double": regression_194["double"],
            "blockers": regression_194["blockers"],
            "matches_accepted_special": regression_194["matches_accepted_special"],
        },
        "generic_222_native_results": {
            "summary": summary_222,
            "ai_filter_fix": ai_fix_222,
            "dropped_candidates": dropped_222,
            "oracle_compare": oracle_222,
        },
        "high_level_verdict": (
            "Core generic path is backend-free, but the 194 target-object builders are not yet extracted and "
            "the 222 native object remains provisional because rejected AI candidates still exist."
        ),
    }

    status_semantics = {
        "generated_at": now_iso(),
        "scope": "pipeline_status_semantics_v5",
        "status_terms": [
            {
                "name": "available",
                "meaning": "The native object was built without rejected or unembedded AI candidates and is internally consistent at the published object layer.",
            },
            {
                "name": "provisional",
                "meaning": "A native object was computed, but it is not a verified final result because a blocker remains at the same object layer.",
            },
            {
                "name": "backend_free_generic_final_available",
                "meaning": "Pipeline final slots are populated from the backend-free native path, not from SG194-special backend code and not from oracle overwrite.",
            },
            {
                "name": "warning_native_generic_result_has_nontrivial_free_part",
                "meaning": "The native path reached a raw quotient with a surviving free part; this is a real computed object, but not the accepted SG194 target object.",
            },
            {
                "name": "failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient",
                "meaning": "The old silent-drop bug is no longer hidden: rejected or unembedded AI candidates remain, so the quotient cannot be claimed as a verified final classification.",
            },
        ],
        "oracle_policy": {
            "native_final_slots_source": "backend_free_generic_path",
            "copied_topmat_role": "compare_only",
            "oracle_override_allowed": False,
        },
        "current_examples": {
            "194.1.1.1": {
                "single": {
                    "availability": regression_194["single"]["availability"],
                    "verification_status": regression_194["single"]["verification_status"],
                    "blocker": regression_194["blockers"][0]["blocker"],
                },
                "double": {
                    "availability": regression_194["double"]["availability"],
                    "verification_status": regression_194["double"]["verification_status"],
                    "blocker": regression_194["blockers"][1]["blocker"],
                },
            },
            "222.1.1.1 / 222.1.1601(OG)": {
                "single": {
                    "availability": summary_222["single"]["availability"],
                    "verification_status": summary_222["single"]["verification_status"],
                },
                "double": {
                    "availability": summary_222["double"]["availability"],
                    "verification_status": summary_222["double"]["verification_status"],
                },
            },
        },
    }

    write_json(CONSISTENCY_JSON, consistency)
    write_json(STATUS_JSON, status_semantics)

    write_text(
        CONSISTENCY_MD,
        "\n".join(
            [
                "# Pipeline Consistency Checks v8",
                "",
                f"- backend-free generic path: `{consistency['backend_free_generic_path']}`",
                f"- truly general: `{consistency['truly_general']}`",
                f"- coordinate contract audit: `{coord_audit['all_passed']}`",
                f"- 194 single: `{regression_194['single']['dBS']}/{regression_194['single']['dAI']}/{regression_194['single']['classification']}`",
                f"- 194 double: `{regression_194['double']['dBS']}/{regression_194['double']['dAI']}/{regression_194['double']['classification']}`",
                f"- 222 single: `{summary_222['single']['dBS']}/{summary_222['single']['dAI']}/{summary_222['single']['classification']}`",
                f"- 222 double: `{summary_222['double']['dBS']}/{summary_222['double']['dAI']}/{summary_222['double']['classification']}`",
                f"- required checks passed / diagnostic checks passed: `{consistency['checks_passed']}` / `{consistency['diagnostic_checks_passed']}`",
                f"- verdict: `{consistency['high_level_verdict']}`",
            ]
        ),
    )
    write_text(
        STATUS_MD,
        "\n".join(
            [
                "# Pipeline Status Semantics v5",
                "",
                *[
                    f"- `{item['name']}`: `{item['meaning']}`"
                    for item in status_semantics["status_terms"]
                ],
                "",
                f"- oracle policy: `{status_semantics['oracle_policy']}`",
                f"- current examples: `{status_semantics['current_examples']}`",
            ]
        ),
    )

    if args.validate:
        if not consistency["backend_free_generic_path"]:
            raise SystemExit("pipeline metadata v5: backend-free generic path check failed")


if __name__ == "__main__":
    main()
