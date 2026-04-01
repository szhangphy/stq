#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

STAGE2_SCRIPT = ROOT / "debug_workflow_portability_stage2_194.1.1.1.py"
EXACT_ALIGN_SCRIPT = ROOT / "debug_sg194_single_exact_target_alignment_v1.py"

CURRENT_STAGE2_JSON = ROOT / "current_status_194.1.1.1_stage2.json"
PAIRING_PROOF_JSON = ROOT / "sg194_single_jk_pairing_proof_v1.json"
UNIQUENESS_JSON = ROOT / "sg194_single_jk_pairing_uniqueness_v1.json"
REGRESSION_JSON = ROOT / "sg194_single_exact_alignment_regression_v1.json"
REGRESSION_MD = ROOT / "sg194_single_exact_alignment_regression_v1.md"


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def run_check(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def build_payload() -> dict[str, Any]:
    current = load_json(CURRENT_STAGE2_JSON)
    proof = load_json(PAIRING_PROOF_JSON)
    uniqueness = load_json(UNIQUENESS_JSON)
    single = current["single_status"]
    double = current["double_status"]

    command_checks = [
        {
            "name": "stage2_validate",
            **run_check(["python3", repo_rel(STAGE2_SCRIPT), "--validate"]),
        },
        {
            "name": "single_exact_alignment_validate",
            **run_check(["python3", repo_rel(EXACT_ALIGN_SCRIPT), "--validate"]),
        },
    ]

    semantic_checks = [
        {
            "name": "single_exact_alignment_exists",
            "passed": single["single_target_exact_generator_identity_status"] == "available"
            and single["single_target_projection_mismatch_rank"] == 0,
            "actual": {
                "single_target_exact_generator_identity_status": single["single_target_exact_generator_identity_status"],
                "single_target_projection_mismatch_rank": single["single_target_projection_mismatch_rank"],
            },
        },
        {
            "name": "raw_pairing_still_fails",
            "passed": proof["raw_pairing_failure"]["mismatch_rank"] == 1,
            "actual": proof["raw_pairing_failure"]["mismatch_rank"],
        },
        {
            "name": "canonical_pairing_exact",
            "passed": proof["canonical_pairing_success"]["mismatch_rank"] == 0,
            "actual": proof["canonical_pairing_success"]["mismatch_rank"],
        },
        {
            "name": "pairing_uniqueness",
            "passed": uniqueness["unique_under_permutation"] and uniqueness["unique_under_signed_permutation"],
            "actual": {
                "unique_under_permutation": uniqueness["unique_under_permutation"],
                "unique_under_signed_permutation": uniqueness["unique_under_signed_permutation"],
            },
        },
        {
            "name": "single_final_stable",
            "passed": (
                current["single_final_rank_bs"] == 13
                and current["single_final_rank_ai"] == 13
                and current["single_final_quotient_group"] == "trivial"
            ),
            "actual": {
                "dBS": current["single_final_rank_bs"],
                "dAI": current["single_final_rank_ai"],
                "classification": current["single_final_quotient_group"],
            },
        },
        {
            "name": "double_final_stable",
            "passed": (
                current["double_final_rank_bs"] == 10
                and current["double_final_rank_ai"] == 10
                and current["double_final_quotient_group"] == "Z6"
            ),
            "actual": {
                "dBS": current["double_final_rank_bs"],
                "dAI": current["double_final_rank_ai"],
                "classification": current["double_final_quotient_group"],
            },
        },
        {
            "name": "single_double_not_conflated",
            "passed": current["single_double_final_same_target_object"] is False,
            "actual": current["single_double_final_relation"],
        },
    ]

    all_passed = all(item["passed"] for item in command_checks + semantic_checks)
    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "command_checks": command_checks,
        "semantic_checks": semantic_checks,
        "single_final": {
            "dBS": current["single_final_rank_bs"],
            "dAI": current["single_final_rank_ai"],
            "classification": current["single_final_quotient_group"],
        },
        "double_final": {
            "dBS": current["double_final_rank_bs"],
            "dAI": current["double_final_rank_ai"],
            "classification": current["double_final_quotient_group"],
        },
        "all_passed": all_passed,
    }


def validate_outputs() -> None:
    payload = load_json(REGRESSION_JSON)
    assert payload["all_passed"] is True
    assert payload["single_final"] == {"dBS": 13, "dAI": 13, "classification": "trivial"}
    assert payload["double_final"] == {"dBS": 10, "dAI": 10, "classification": "Z6"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated sg194 single exact alignment regression outputs")
        return

    payload = build_payload()
    write_json(REGRESSION_JSON, payload)
    write_text(
        REGRESSION_MD,
        "\n".join(
            [
                "# SG194 Single Exact Alignment Regression v1",
                "",
                f"- all passed: `{payload['all_passed']}`",
                f"- single final: `{payload['single_final']['dBS']}/{payload['single_final']['dAI']}/{payload['single_final']['classification']}`",
                f"- double final: `{payload['double_final']['dBS']}/{payload['double_final']['dAI']}/{payload['double_final']['classification']}`",
                "- regression checks enforce canonical j/k pairing, exact single target alignment, and stable single/double status split.",
            ]
        ),
    )
    validate_outputs()
    print("generated sg194 single exact alignment regression outputs")


if __name__ == "__main__":
    main()
