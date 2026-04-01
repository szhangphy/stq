#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
COMMON = REPO_ROOT / "common"

OUTPUT_JSON = ROOT / "sg194_second_group_onboarding_v1.json"
OUTPUT_MD = ROOT / "sg194_second_group_onboarding_v1.md"

TRUSTED_FILES = [
    COMMON / "P1_character.json",
    COMMON / "L1_character.json",
    COMMON / "P4_character.json",
]
OBJECT_KINDS = {
    "P1_character.json": "point",
    "L1_character.json": "line",
    "P4_character.json": "point",
}
MISSING_GENERIC_BUILDERS = [
    "generic_k_geometry_builder_from_symmetry_ops",
    "generic_current_row_compatibility_builder",
    "generic_local_ai_builder_from_site_symmetry_data",
    "generic_direct_quotient_builder_once_bs_ai_exist",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_payload() -> dict[str, Any]:
    objects = []
    for path in TRUSTED_FILES:
        payload = load_json(path)
        objects.append(
            {
                "label": path.stem.replace("_character", ""),
                "kind": OBJECT_KINDS[path.name],
                "file": f"common/{path.name}",
                "kvec": list(payload["kvec"]),
                "n_ops_total": len(payload["rotC"]),
                "n_unitary_ops": sum(1 for value in payload["timeReversal"] if value == 1),
                "n_antiunitary_ops": sum(1 for value in payload["timeReversal"] if value == -1),
                "trusted_fields": ["rotC", "tauC", "timeReversal", "kvec"],
            }
        )
    return {
        "group": "10.4.1.31",
        "trust_policy": "symmetry_operations_only",
        "trusted_source_files": [f"common/{path.name}" for path in TRUSTED_FILES],
        "sample_probe": {
            "anchor_name": "P1-L1-P4 symmetry-ops probe",
            "probe_passed": True,
            "object_counts": {
                "points": sum(1 for item in objects if item["kind"] == "point"),
                "lines": sum(1 for item in objects if item["kind"] == "line"),
                "planes": 0,
            },
            "objects": objects,
        },
        "primary_blocker": "generic_current_row_compatibility_builder",
        "missing_generic_builders": list(MISSING_GENERIC_BUILDERS),
        "untrusted_result_files_consumed": [],
        "readiness_note": (
            "A real second-group spec is now wired into the pipeline, but under a strict "
            "symmetry-operations-only trust policy. Full geometry/current-row/AI/quotient "
            "builders remain unavailable, so the driver must stop at explicit readiness/blocker output."
        ),
    }


def write_markdown(payload: dict[str, Any]) -> None:
    lines = [
        "# Second-Group Onboarding",
        "",
        f"- group: `{payload['group']}`",
        f"- trust policy: `{payload['trust_policy']}`",
        f"- primary blocker: `{payload['primary_blocker']}`",
        "",
        "## Trusted Sources",
        "",
        *[f"- `{item}`" for item in payload["trusted_source_files"]],
        "",
        "## Sample Probe",
        "",
    ]
    for item in payload["sample_probe"]["objects"]:
        lines.append(
            f"- `{item['label']}` ({item['kind']}): k=`{item['kvec']}`, "
            f"ops=`{item['n_ops_total']}`, unitary/antiunitary=`{item['n_unitary_ops']}/{item['n_antiunitary_ops']}`"
        )
    lines.extend(
        [
            "",
            "## Missing Generic Builders",
            "",
            *[f"- `{item}`" for item in payload["missing_generic_builders"]],
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines).rstrip() + "\n")


def validate_outputs() -> int:
    if not OUTPUT_JSON.exists() or not OUTPUT_MD.exists():
        print("missing onboarding outputs")
        return 1
    payload = load_json(OUTPUT_JSON)
    if payload.get("trust_policy") != "symmetry_operations_only":
        print("wrong trust_policy")
        return 1
    if payload.get("untrusted_result_files_consumed") != []:
        print("unexpected untrusted result consumption")
        return 1
    if payload["sample_probe"]["object_counts"] != {"points": 2, "lines": 1, "planes": 0}:
        print("unexpected sample probe object counts")
        return 1
    if len(payload.get("missing_generic_builders", [])) < 3:
        print("missing generic builder blockers not explicit enough")
        return 1
    print("validation_ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate symmetry-ops-only onboarding evidence for 10.4.1.31.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        return validate_outputs()

    payload = build_payload()
    write_json(OUTPUT_JSON, payload)
    write_markdown(payload)
    print(json.dumps({"group": payload["group"], "trust_policy": payload["trust_policy"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
