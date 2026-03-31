#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "review_package_sg194_stage2_closeout_followup_v3"
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

FULL_RERUN_JSON = ROOT / "sg194_package_full_rerun_test_v1.json"
FULL_RERUN_MD = ROOT / "sg194_package_full_rerun_test_v1.md"

REQUIRED_OUTPUTS = [
    "sg194_standard_space_projection_summary_v1.json",
    "group_194_1_1_1_single_ai_completion_summary.json",
    "group_194_1_1_1_double_ai_completion_summary.json",
    "workflow_portability_stage2_summary_194.1.1.1.json",
    "current_status_194.1.1.1_stage2.json",
    "workflow_portability_report_stage2_194.1.1.1.tex",
    "workflow_portability_report_stage2_194.1.1.1.pdf",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def summarize_output(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ""
    keywords = [
        "rank(BS/AI)",
        "raw internal quotient",
        "standard quotient",
        "projection contract",
        "single=",
        "double=",
        "workflow_portability_stage2_summary_194.1.1.1.json",
    ]
    for line in reversed(lines):
        if any(keyword in line for keyword in keywords):
            return line
    return lines[-1]


def run_command(command: list[str], cwd: Path) -> dict[str, Any]:
    started = time.time()
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    output = completed.stdout.strip()
    return {
        "command": " ".join(command),
        "cwd": str(cwd),
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "output_excerpt": summarize_output(output),
    }


def summary_checks(package_root: Path) -> dict[str, Any]:
    single = load_json(package_root / "group_194_1_1_1_single_ai_completion_summary.json")
    double = load_json(package_root / "group_194_1_1_1_double_ai_completion_summary.json")
    stage2 = load_json(package_root / "workflow_portability_stage2_summary_194.1.1.1.json")
    projection = load_json(package_root / "sg194_standard_space_projection_summary_v1.json")
    return {
        "single_raw_rank_bs": int(single["rank_bs_raw_internal"]),
        "single_raw_quotient_group": single["raw_internal_quotient_group"],
        "single_final_rank_bs": int(single["final_rank_bs"]),
        "single_final_rank_ai": int(single["final_rank_ai"]),
        "single_final_quotient_group": single["quotient_group"],
        "double_raw_rank_bs": int(double["rank_bs_raw_internal"]),
        "double_raw_quotient_group": double["raw_internal_quotient_group"],
        "double_final_rank_bs": int(double["final_rank_bs"]),
        "double_final_rank_ai": int(double["final_rank_ai"]),
        "double_final_quotient_group": double["quotient_group"],
        "projection_status": projection["status"],
        "projection_contract_type": projection["projection_contract_type"],
        "stage2_standard_projection_status": stage2["standard_space_projection_status"],
    }


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Package Full Rerun Test v1",
        "",
        "## Package Under Test",
        "",
        f"- tarball = `{payload['tarball']}`",
        f"- extracted package root = `{payload['extracted_package_root']}`",
        f"- all passed = `{payload['all_passed']}`",
        "",
        "## Commands",
        "",
    ]
    for item in payload["commands"]:
        lines.extend(
            [
                f"- `{item['command']}`",
                f"  - passed = `{item['passed']}`",
                f"  - returncode = `{item['returncode']}`",
                f"  - duration_seconds = `{item['duration_seconds']}`",
                f"  - output = `{item['output_excerpt']}`",
            ]
        )
    lines.extend(["", "## Output Checks", ""])
    for item in payload["output_checks"]:
        lines.append(f"- `{item['path']}` -> `{item['exists']}`")
    lines.extend(
        [
            "",
            "## Result Checks",
            "",
            f"- summary = `{payload['result_checks']}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    if not PACKAGE_TARBALL.exists():
        raise FileNotFoundError(PACKAGE_TARBALL)

    temp_root = Path(tempfile.mkdtemp(prefix="sg194_pkg_full_rerun_v1_"))
    extracted_root = temp_root / PACKAGE_NAME
    try:
        with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
            tar.extractall(path=temp_root)
        if not extracted_root.exists():
            raise FileNotFoundError(extracted_root)

        commands = [
            ["python3", "debug_sg194_standard_space_projection_v1.py"],
            ["python3", "debug_workflow_portability_stage2_194.1.1.1.py"],
        ]
        command_results = [run_command(command, extracted_root) for command in commands]
        output_checks = [
            {"path": name, "exists": (extracted_root / name).exists()}
            for name in REQUIRED_OUTPUTS
        ]
        results = summary_checks(extracted_root)
        all_passed = (
            all(item["passed"] for item in command_results)
            and all(item["exists"] for item in output_checks)
            and results["single_raw_rank_bs"] == 16
            and results["single_raw_quotient_group"] == "Z^3"
            and results["single_final_rank_bs"] == 13
            and results["single_final_rank_ai"] == 13
            and results["single_final_quotient_group"] == "trivial"
            and results["double_raw_rank_bs"] == 16
            and results["double_raw_quotient_group"] == "Z^3"
            and results["double_final_rank_bs"] == 13
            and results["double_final_rank_ai"] == 13
            and results["double_final_quotient_group"] == "trivial"
            and results["projection_status"] == "implemented"
            and results["stage2_standard_projection_status"] == "implemented"
        )

        payload = {
            "package_name": PACKAGE_NAME,
            "tarball": str(PACKAGE_TARBALL),
            "temp_root": str(temp_root),
            "extracted_package_root": str(extracted_root),
            "commands": command_results,
            "output_checks": output_checks,
            "result_checks": results,
            "all_passed": all_passed,
        }
        write_json(FULL_RERUN_JSON, payload)
        write_text(FULL_RERUN_MD, build_markdown(payload))
        print(f"wrote {FULL_RERUN_JSON.name} and {FULL_RERUN_MD.name}; all_passed={all_passed}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
