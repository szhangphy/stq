#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_v2.driver import run_pipeline
from pipeline_v2.models import PipelineRunConfig


DRIVER_SPEC_JSON = ROOT / "sg194_pipeline_driver_spec_v3.json"
DRIVER_SPEC_MD = ROOT / "sg194_pipeline_driver_spec_v3.md"
CONSISTENCY_JSON = ROOT / "sg194_pipeline_consistency_checks_v3.json"
CONSISTENCY_MD = ROOT / "sg194_pipeline_consistency_checks_v3.md"


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def run_one(group: str, mode: str, row_language: str, output_name: str) -> dict:
    repo_root = ROOT.parent
    config = PipelineRunConfig(
        group=group,
        mode=mode,
        row_language=row_language,
        output_dir=ROOT / "pipeline_runs_v2_tmp" / output_name,
        validate=True,
        build_package=False,
        refresh=False,
    )
    return run_pipeline(config, repo_root)


def build_outputs() -> None:
    sg194 = run_one("sg194", "both", "all", "sg194_consistency_v3")
    ssg222 = run_one("222.1.1.1", "both", "all", "ssg222_consistency_v3")
    driver_spec = {
        "entrypoint": "sg194/run_group_pipeline.py",
        "cli": {
            "arguments": [
                "--group",
                "--mode single|double|both",
                "--row-language raw|target|all",
                "--output-dir",
                "--validate",
                "--build-package",
            ],
            "outputs": [
                "geometry_summary",
                "representation_alignment_summary",
                "bs_results",
                "ai_results",
                "quotient_results",
                "final_status_summary",
                "consistency_checks",
                "package_manifest",
            ],
        },
        "primary_test_groups": ["sg194", "222.1.1.1"],
        "deprecated_second_group": "10.4.1.31",
    }
    consistency = {
        "sg194": {
            "checks_passed": sg194["checks"]["all_passed"],
            "single_final": sg194["final_status"]["single_final"],
            "double_final": sg194["final_status"]["double_final"],
            "output_dir": sg194["manifest"]["output_dir"],
        },
        "ssg222_1_1_1": {
            "checks_passed": ssg222["checks"]["all_passed"],
            "status": ssg222["final_status"]["status"],
            "builder_layers": ssg222["final_status"]["builder_layers"],
            "single_final": ssg222["final_status"]["single_final"],
            "double_final": ssg222["final_status"]["double_final"],
            "output_dir": ssg222["manifest"]["output_dir"],
        },
        "all_passed": sg194["checks"]["all_passed"] and ssg222["checks"]["all_passed"],
    }
    write_json(DRIVER_SPEC_JSON, driver_spec)
    write_json(CONSISTENCY_JSON, consistency)
    DRIVER_SPEC_MD.write_text(
        "\n".join(
            [
                "# Pipeline Driver Spec V3",
                "",
                f"- entrypoint: `{driver_spec['entrypoint']}`",
                f"- primary test groups: `{', '.join(driver_spec['primary_test_groups'])}`",
                f"- deprecated second group: `{driver_spec['deprecated_second_group']}`",
                "",
                "## CLI Arguments",
                "",
                *[f"- `{item}`" for item in driver_spec["cli"]["arguments"]],
                "",
                "## Outputs",
                "",
                *[f"- `{item}`" for item in driver_spec["cli"]["outputs"]],
            ]
        ).rstrip()
        + "\n"
    )
    CONSISTENCY_MD.write_text(
        "\n".join(
            [
                "# Pipeline Consistency Checks V3",
                "",
                f"- all passed: `{consistency['all_passed']}`",
                f"- SG194 single: `{consistency['sg194']['single_final']['dBS']}/{consistency['sg194']['single_final']['dAI']}/{consistency['sg194']['single_final']['classification']}`",
                f"- SG194 double: `{consistency['sg194']['double_final']['dBS']}/{consistency['sg194']['double_final']['dAI']}/{consistency['sg194']['double_final']['classification']}`",
                f"- 222 status: `{consistency['ssg222_1_1_1']['status']}`",
                f"- 222 builder layers: `{consistency['ssg222_1_1_1']['builder_layers']}`",
            ]
        ).rstrip()
        + "\n"
    )


def validate() -> int:
    for path in (DRIVER_SPEC_JSON, DRIVER_SPEC_MD, CONSISTENCY_JSON, CONSISTENCY_MD):
        if not path.exists():
            print(f"missing {path.name}")
            return 1
    payload = json.loads(CONSISTENCY_JSON.read_text())
    if payload.get("all_passed") is not True:
        print("consistency checks not passing")
        return 1
    sg194 = payload["sg194"]
    if (sg194["single_final"]["dBS"], sg194["single_final"]["dAI"], sg194["single_final"]["classification"]) != (13, 13, "trivial"):
        print("sg194 single drifted")
        return 1
    if (sg194["double_final"]["dBS"], sg194["double_final"]["dAI"], sg194["double_final"]["classification"]) != (10, 10, "Z6"):
        print("sg194 double drifted")
        return 1
    print("validated pipeline consistency v3 outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run pipeline consistency checks for SG194 and 222.1.1.1.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate()
    build_outputs()
    print(json.dumps({"driver_spec": DRIVER_SPEC_JSON.name, "consistency": CONSISTENCY_JSON.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
