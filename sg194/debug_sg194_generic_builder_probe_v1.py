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


OUTPUT_GAP_JSON = ROOT / "sg194_generic_builder_gap_v1.json"
OUTPUT_GAP_MD = ROOT / "sg194_generic_builder_gap_v1.md"
OUTPUT_FIX_JSON = ROOT / "sg194_generic_builder_fix_attempt_v1.json"
OUTPUT_FIX_MD = ROOT / "sg194_generic_builder_fix_attempt_v1.md"
TMP_DIR = ROOT / "pipeline_runs_v2_tmp" / "ssg222_generic_probe"


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def run_probe() -> dict:
    repo_root = ROOT.parent
    config = PipelineRunConfig(
        group="222.1.1.1",
        mode="both",
        row_language="all",
        output_dir=TMP_DIR,
        validate=True,
        build_package=False,
        refresh=False,
    )
    return run_pipeline(config, repo_root)


def build_outputs() -> None:
    result = run_probe()
    gap = {
        "group": "222.1.1.1",
        "geometry_status": result["geometry"]["status"],
        "current_row_shell_status": result["alignment"]["current_row_shell"]["status"],
        "local_ai_seed_status": result["alignment"]["local_ai_seed_builder"]["status"],
        "single_target_status": result["final_status"]["single_final"]["row_language_kind"],
        "double_target_status": result["final_status"]["double_final"]["row_language_kind"],
        "primary_blocker": result["final_status"]["single_final"]["blocker"],
        "remaining_missing_builders": [
            "generic_current_row_compatibility_builder",
            "generic_target_alignment_builder",
            "generic_local_ai_embedding_builder",
            "generic_direct_quotient_builder_once_bs_ai_exist",
        ],
    }
    fix_attempt = {
        "group": "222.1.1.1",
        "implemented_generic_layers": {
            "geometry": result["geometry"]["status"],
            "current_row_shell": result["alignment"]["current_row_shell"]["status"],
            "local_ai_seed": result["alignment"]["local_ai_seed_builder"]["status"],
            "quotient_prerequisites": result["final_status"]["builder_layers"]["quotient_prerequisites"],
        },
        "still_blocked_layers": {
            "target_alignment": result["final_status"]["builder_layers"]["target_alignment"],
            "single_final": result["final_status"]["single_final"]["blocker"],
            "double_final": result["final_status"]["double_final"]["blocker"],
        },
        "driver_output_dir": str(TMP_DIR.relative_to(ROOT.parent)),
    }
    write_json(OUTPUT_GAP_JSON, gap)
    write_json(OUTPUT_FIX_JSON, fix_attempt)
    OUTPUT_GAP_MD.write_text(
        "\n".join(
            [
                "# Generic Builder Gap V1",
                "",
                f"- group: `{gap['group']}`",
                f"- geometry: `{gap['geometry_status']}`",
                f"- current-row shell: `{gap['current_row_shell_status']}`",
                f"- local-AI seed: `{gap['local_ai_seed_status']}`",
                f"- primary blocker: `{gap['primary_blocker']}`",
                "",
                "## Remaining Missing Builders",
                "",
                *[f"- `{item}`" for item in gap["remaining_missing_builders"]],
            ]
        ).rstrip()
        + "\n"
    )
    OUTPUT_FIX_MD.write_text(
        "\n".join(
            [
                "# Generic Builder Fix Attempt V1",
                "",
                "## Implemented Layers",
                "",
                *[f"- `{key}`: `{value}`" for key, value in fix_attempt["implemented_generic_layers"].items()],
                "",
                "## Still Blocked",
                "",
                *[f"- `{key}`: `{value}`" for key, value in fix_attempt["still_blocked_layers"].items()],
            ]
        ).rstrip()
        + "\n"
    )


def validate() -> int:
    for path in (OUTPUT_GAP_JSON, OUTPUT_GAP_MD, OUTPUT_FIX_JSON, OUTPUT_FIX_MD):
        if not path.exists():
            print(f"missing {path.name}")
            return 1
    gap = json.loads(OUTPUT_GAP_JSON.read_text())
    if gap.get("geometry_status") != "built_from_trusted_symmetry_ops":
        print("geometry builder did not run")
        return 1
    if gap.get("current_row_shell_status") != "available" or gap.get("local_ai_seed_status") != "available":
        print("generic builder prerequisites unavailable")
        return 1
    print("validated generic builder probe v1 outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe generic builders on 222.1.1.1 and write gap/fix outputs.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate()
    build_outputs()
    print(json.dumps({"gap": OUTPUT_GAP_JSON.name, "fix_attempt": OUTPUT_FIX_JSON.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
