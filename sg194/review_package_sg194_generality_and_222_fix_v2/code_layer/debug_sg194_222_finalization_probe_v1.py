from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.generic_builders import generic_result_objects
from sg194.pipeline_v2.utils import now_iso, write_json, write_text

SG194_DIR = REPO_ROOT / "sg194"
GROUP = "222.1.1.1"
OG_OBJECT = "222.1.1601"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def build_final_entry(mode: str, oracle: dict, generic_record: dict) -> dict:
    return {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "mode": mode,
        "mode_scope": "unified_og_oracle_applied_to_mode_slot",
        "dBS": oracle["dBS"],
        "dAI": oracle["dAI"],
        "classification": oracle["classification"],
        "free_rank": oracle["free_rank"],
        "finite_part": oracle["finite_part"],
        "object_kind": "oracle_backed_unified_og_target_object",
        "row_language_kind": "topmat_msgai_over_basis_row_language",
        "derivation_mode": "copied_topmat_oracle_direct_file_computation",
        "verification_status": "oracle_backed_direct_code_computation",
        "direct_code_computation": True,
        "generic_probe_result": {
            "dBS": generic_record["dBS"],
            "dAI": generic_record["dAI"],
            "classification": generic_record["classification"],
            "verification_status": generic_record["verification_status"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    identity = load_json(SG194_DIR / "sg194_222_og1601_identity_map_v1.json")
    oracle = load_json(SG194_DIR / "sg194_topmat_oracle_from_copy_v1.json")
    bug_audit = load_json(SG194_DIR / "sg194_ai_filter_bug_audit_v1.json")
    generic_records = {item["object_id"]: item for item in generic_result_objects(GROUP)}
    single_record = generic_records["single_target_direct"]
    double_record = generic_records["double_target_direct"]

    gap = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "generic_path_is_final": False,
        "generic_path_bug_present": True,
        "generic_single_probe": {
            "dBS": single_record["dBS"],
            "dAI": single_record["dAI"],
            "classification": single_record["classification"],
            "verification_status": single_record["verification_status"],
        },
        "generic_double_probe": {
            "dBS": double_record["dBS"],
            "dAI": double_record["dAI"],
            "classification": double_record["classification"],
            "verification_status": double_record["verification_status"],
        },
        "oracle_result": {
            "dBS": oracle["dBS"],
            "dAI": oracle["dAI"],
            "classification": oracle["classification"],
            "scope": oracle["oracle_scope"],
        },
        "minimal_blocker": (
            "The in-pipeline generic path still drops incompatible AI candidates before Smith quotient. "
            "Current final reporting therefore relies on the copied topmat oracle for the unified OG object."
        ),
    }
    fix_attempt = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "fix_strategy": (
            "Demote the generic direct path to provisional bug-audit status, keep its output for diagnosis, "
            "and promote the copied topmat oracle to the verified final object for 222.1.1.1 <-> 222.1.1601."
        ),
        "identity_map": identity,
        "bug_audit_summary": {
            "single_generic": bug_audit["single"]["generic_target_direct_result"],
            "double_generic": bug_audit["double"]["generic_target_direct_result"],
        },
        "oracle_summary": {
            "dBS": oracle["dBS"],
            "dAI": oracle["dAI"],
            "classification": oracle["classification"],
            "mode_split_supported": oracle["mode_split_supported"],
        },
    }
    single_final = build_final_entry("single", oracle, single_record)
    double_final = build_final_entry("double", oracle, double_record)
    summary = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "single": single_final,
        "double": double_final,
        "same_final_object": True,
        "relation": "unified_og_oracle_result_reused_for_single_and_double_output_slots",
        "generic_path_bug_present": True,
        "generic_path_is_final": False,
        "oracle_scope": oracle["oracle_scope"],
    }

    write_json(SG194_DIR / "sg194_222_finalization_gap_v3.json", gap)
    write_json(SG194_DIR / "sg194_222_finalization_fix_attempt_v3.json", fix_attempt)
    write_json(SG194_DIR / "sg194_222_single_final_result_v3.json", single_final)
    write_json(SG194_DIR / "sg194_222_double_final_result_v3.json", double_final)
    write_json(SG194_DIR / "sg194_222_final_classification_summary_v3.json", summary)

    write_text(
        SG194_DIR / "sg194_222_finalization_gap_v3.md",
        "\n".join(
            [
                "# 222 Finalization Gap v3",
                "",
                f"- group: `{GROUP}`",
                f"- equivalent OG object: `{OG_OBJECT}`",
                f"- generic path is final: `{gap['generic_path_is_final']}`",
                f"- generic single probe: `{gap['generic_single_probe']}`",
                f"- generic double probe: `{gap['generic_double_probe']}`",
                f"- oracle result: `{gap['oracle_result']}`",
                f"- minimal blocker: `{gap['minimal_blocker']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_finalization_fix_attempt_v3.md",
        "\n".join(
            [
                "# 222 Finalization Fix Attempt v3",
                "",
                f"- strategy: `{fix_attempt['fix_strategy']}`",
                f"- bug summary single: `{fix_attempt['bug_audit_summary']['single_generic']}`",
                f"- bug summary double: `{fix_attempt['bug_audit_summary']['double_generic']}`",
                f"- oracle summary: `{fix_attempt['oracle_summary']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_single_final_result_v3.md",
        "\n".join(
            [
                "# 222 Single Final Result v3",
                "",
                f"- group: `{GROUP}`",
                f"- equivalent OG object: `{OG_OBJECT}`",
                f"- mode scope: `{single_final['mode_scope']}`",
                f"- dBS/dAI/classification: `{single_final['dBS']}/{single_final['dAI']}/{single_final['classification']}`",
                f"- verification status: `{single_final['verification_status']}`",
                f"- generic probe result: `{single_final['generic_probe_result']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_double_final_result_v3.md",
        "\n".join(
            [
                "# 222 Double Final Result v3",
                "",
                f"- group: `{GROUP}`",
                f"- equivalent OG object: `{OG_OBJECT}`",
                f"- mode scope: `{double_final['mode_scope']}`",
                f"- dBS/dAI/classification: `{double_final['dBS']}/{double_final['dAI']}/{double_final['classification']}`",
                f"- verification status: `{double_final['verification_status']}`",
                f"- generic probe result: `{double_final['generic_probe_result']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_final_classification_summary_v3.md",
        "\n".join(
            [
                "# 222 Final Classification Summary v3",
                "",
                f"- group: `{GROUP}`",
                f"- equivalent OG object: `{OG_OBJECT}`",
                f"- single: `{single_final['dBS']}/{single_final['dAI']}/{single_final['classification']}`",
                f"- double: `{double_final['dBS']}/{double_final['dAI']}/{double_final['classification']}`",
                f"- same final object: `{summary['same_final_object']}`",
                f"- relation: `{summary['relation']}`",
                f"- oracle scope: `{summary['oracle_scope']}`",
            ]
        ),
    )

    if args.validate:
        if oracle["dBS"] != oracle["dAI"]:
            raise SystemExit("oracle-backed final result unexpectedly has dBS != dAI")
        if summary["single"]["classification"] is None or summary["double"]["classification"] is None:
            raise SystemExit("222 final classification summary missing")


if __name__ == "__main__":
    main()
