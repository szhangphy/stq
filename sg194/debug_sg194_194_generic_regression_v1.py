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

from sg194.pipeline_v2.generic_builders import generic_result_objects
from sg194.pipeline_v2.utils import now_iso, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
GROUP = "194.1.1.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def record_payload(record: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "object_id": record["object_id"],
        "mode": record["mode"],
        "row_language_kind": record["row_language_kind"],
        "object_kind": record["object_kind"],
        "availability": record["availability"],
        "verification_status": record.get("verification_status"),
        "dBS": record.get("dBS"),
        "dAI": record.get("dAI"),
        "classification": record.get("classification"),
        "free_rank": record.get("free_rank"),
        "finite_part": record.get("finite_part"),
        "quotient_derivation_mode": record.get("quotient_derivation_mode"),
        "ai_candidate_count": record.get("ai_candidate_count"),
        "ai_candidate_count_used": record.get("ai_candidate_count_used"),
        "ai_incompatible_count": record.get("ai_incompatible_count"),
        "ai_embedding_failure_count": record.get("ai_embedding_failure_count"),
        "source_files": record.get("source_files", []),
        "accepted_special_reference": expected,
        "matches_accepted_special": all(record.get(key) == value for key, value in expected.items()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    stage2 = load_json(SG194_DIR / "current_status_194.1.1.1_stage2.json")
    records = {item["object_id"]: item for item in generic_result_objects(GROUP)}

    expected_single = {"dBS": 13, "dAI": 13, "classification": "trivial"}
    expected_double = {"dBS": 10, "dAI": 10, "classification": "Z6"}
    single = record_payload(records["single_target_direct"], expected_single)
    double = record_payload(records["double_target_direct"], expected_double)

    special_to_generic_map = {
        "generated_at": now_iso(),
        "group": GROUP,
        "layers": [
            {
                "layer": "geometry",
                "generic_path_status": "implemented_in_backend_free_runtime_module",
                "special_reference_status": "retained_in_current_status_194.1.1.1_stage2.json",
            },
            {
                "layer": "current_row_shell",
                "generic_path_status": "generic_current_row_shell_from_symmetry_ops",
                "special_reference_status": stage2["single_status"]["geometry_backbone_mode"],
            },
            {
                "layer": "compatibility",
                "generic_path_status": "generic_current_row_compatibility_from_runtime_backend_free",
                "special_reference_status": "group_specific_stage2_reference_only",
            },
            {
                "layer": "target_alignment",
                "generic_path_status": "raw_current_point_object_only_backend_free_sg194_target_projection_not_yet_extracted",
                "special_reference_status": "single_exact_target_alignment_and_double_benchmark_internalization",
            },
            {
                "layer": "local_ai_embedding",
                "generic_path_status": "generic_local_irrep_library_in_pipeline_v2",
                "special_reference_status": "group_specific_stage2_reference_only",
            },
            {
                "layer": "quotient",
                "generic_path_status": "native_target_point_shell_embedding_without_silent_drop",
                "special_reference_status": "single_exact_target_quotient_plus_double_internalized_benchmark_quotient",
            },
            {
                "layer": "consistency_checks",
                "generic_path_status": "raw_current_consistency_only_sg194_target_object_regression_not_yet_closed",
                "special_reference_status": "accepted_special_path_regression_reference_available",
            },
            {
                "layer": "final_status_generation",
                "generic_path_status": "backend_free_raw_current_results_only_no_sg194_target_final_object_builder",
                "special_reference_status": "accepted_group_specific_final_objects",
            },
        ],
    }

    regression = {
        "generated_at": now_iso(),
        "group": GROUP,
        "backend_free_generic_path": True,
        "single": single,
        "double": double,
        "accepted_special_reference": {
            "single": expected_single,
            "double": expected_double,
        },
        "matches_accepted_special": {
            "single": single["matches_accepted_special"],
            "double": double["matches_accepted_special"],
        },
        "blockers": [
            {
                "mode": "single",
                "blocker": (
                    None
                    if single["matches_accepted_special"]
                    else (
                        "backend_free_generic_path_currently_stops_at_raw_current_point_object_16_13_Z3; "
                        "sg194_single_exact_target_projection_builder_not_yet_extracted_into_pipeline_v2"
                    )
                ),
            },
            {
                "mode": "double",
                "blocker": (
                    None
                    if double["matches_accepted_special"]
                    else (
                        "backend_free_generic_path_currently_stops_at_raw_current_point_object_16_13_Z3; "
                        "sg194_double_spinorial_33_channel_internalization_builder_not_yet_extracted_into_pipeline_v2"
                    )
                ),
            },
        ],
    }

    summary = {
        "generated_at": now_iso(),
        "group": GROUP,
        "single": {
            "dBS": single["dBS"],
            "dAI": single["dAI"],
            "classification": single["classification"],
            "matches_accepted_special": single["matches_accepted_special"],
        },
        "double": {
            "dBS": double["dBS"],
            "dAI": double["dAI"],
            "classification": double["classification"],
            "matches_accepted_special": double["matches_accepted_special"],
        },
        "accepted_special_reference": {
            "single": expected_single,
            "double": expected_double,
        },
    }

    write_json(SG194_DIR / "sg194_194_special_to_generic_map_v1.json", special_to_generic_map)
    write_json(SG194_DIR / "sg194_194_generic_regression_v1.json", regression)
    write_json(SG194_DIR / "sg194_194_single_generic_final_result_v1.json", single)
    write_json(SG194_DIR / "sg194_194_double_generic_final_result_v1.json", double)
    write_json(SG194_DIR / "sg194_194_generic_final_classification_summary_v1.json", summary)

    write_text(
        SG194_DIR / "sg194_194_special_to_generic_map_v1.md",
        "\n".join(
            [
                "# 194 Special To Generic Map v1",
                "",
                *[
                    f"- `{item['layer']}`: generic=`{item['generic_path_status']}` / special=`{item['special_reference_status']}`"
                    for item in special_to_generic_map["layers"]
                ],
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_194_generic_regression_v1.md",
        "\n".join(
            [
                "# 194 Generic Regression v1",
                "",
                f"- backend-free generic path: `{regression['backend_free_generic_path']}`",
                f"- single generic: `{single['dBS']}/{single['dAI']}/{single['classification']}` match=`{single['matches_accepted_special']}`",
                f"- double generic: `{double['dBS']}/{double['dAI']}/{double['classification']}` match=`{double['matches_accepted_special']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_194_single_generic_final_result_v1.md",
        "\n".join(
            [
                "# 194 Single Generic Final Result v1",
                "",
                f"- dBS/dAI/classification: `{single['dBS']}/{single['dAI']}/{single['classification']}`",
                f"- availability: `{single['availability']}`",
                f"- verification status: `{single['verification_status']}`",
                f"- matches accepted special: `{single['matches_accepted_special']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_194_double_generic_final_result_v1.md",
        "\n".join(
            [
                "# 194 Double Generic Final Result v1",
                "",
                f"- dBS/dAI/classification: `{double['dBS']}/{double['dAI']}/{double['classification']}`",
                f"- availability: `{double['availability']}`",
                f"- verification status: `{double['verification_status']}`",
                f"- matches accepted special: `{double['matches_accepted_special']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_194_generic_final_classification_summary_v1.md",
        "\n".join(
            [
                "# 194 Generic Final Classification Summary v1",
                "",
                f"- single: `{summary['single']}`",
                f"- double: `{summary['double']}`",
                f"- accepted special reference: `{summary['accepted_special_reference']}`",
            ]
        ),
    )

    if args.validate:
        if single["dBS"] is None or double["dBS"] is None:
            raise SystemExit("194 generic regression did not produce concrete dBS values")


if __name__ == "__main__":
    main()
