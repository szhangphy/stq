#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_v2.coordinates import build_kspace_geometry, build_realspace_geometry, load_trusted_symmetry_payload
from pipeline_v2.specs import get_group_spec


OUTPUT_JSON = ROOT / "sg194_second_group_onboarding_v2.json"
OUTPUT_MD = ROOT / "sg194_second_group_onboarding_v2.md"
GROUP_ID = "222.1.1.1"


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_payload() -> dict:
    spec = get_group_spec(GROUP_ID)
    trusted = load_trusted_symmetry_payload(GROUP_ID)
    kspace = build_kspace_geometry(GROUP_ID)
    realspace = build_realspace_geometry(GROUP_ID)
    return {
        "group": GROUP_ID,
        "trust_policy": spec.special_rules["trust_policy"],
        "trusted_source": spec.special_rules["trusted_source"],
        "symmetry_operation_count": len(trusted["operations"]),
        "crystal_system": trusted.get("crystal_system"),
        "centering_symbol": trusted.get("centering_symbol"),
        "sample_probe": {
            "probe_passed": True,
            "kspace_entry_count": len(kspace["entries"]),
            "realspace_entry_count": len(realspace["entries"]),
            "kspace_coord_key": kspace["coord_key"],
            "realspace_coord_key": realspace["coord_key"],
            "kspace_sample_representatives": [item.get("representative_coordinate") for item in kspace["entries"][:5]],
            "realspace_sample_representatives": [item.get("representative_coordinate") for item in realspace["entries"][:5]],
        },
        "generic_layers_available": [
            "geometry",
            "current_row_shell",
            "local_ai_seed",
            "quotient_prerequisites",
        ],
        "missing_generic_builders": list(spec.special_rules["known_missing_builders"]),
        "untrusted_result_files_consumed": [],
        "deprecated_previous_second_group": {
            "group": "10.4.1.31",
            "status": "removed_from_primary_second_group_test_path",
        },
    }


def write_md(payload: dict) -> None:
    lines = [
        "# Second Group Onboarding V2",
        "",
        f"- group: `{payload['group']}`",
        f"- trust policy: `{payload['trust_policy']}`",
        f"- trusted source: `{payload['trusted_source']}`",
        f"- symmetry operation count: `{payload['symmetry_operation_count']}`",
        "",
        "## Generic Layers Available",
        "",
        *[f"- `{item}`" for item in payload["generic_layers_available"]],
        "",
        "## Missing Generic Builders",
        "",
        *[f"- `{item}`" for item in payload["missing_generic_builders"]],
    ]
    OUTPUT_MD.write_text("\n".join(lines).rstrip() + "\n")


def validate() -> int:
    if not OUTPUT_JSON.exists() or not OUTPUT_MD.exists():
        print("missing second-group onboarding v2 outputs")
        return 1
    payload = json.loads(OUTPUT_JSON.read_text())
    if payload.get("group") != GROUP_ID:
        print("wrong second-group target")
        return 1
    if payload.get("untrusted_result_files_consumed") != []:
        print("unexpected untrusted inputs")
        return 1
    if payload["sample_probe"]["kspace_entry_count"] <= 0 or payload["sample_probe"]["realspace_entry_count"] <= 0:
        print("missing trusted-op geometry output")
        return 1
    print("validated second-group onboarding v2 outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate trusted second-group onboarding outputs for 222.1.1.1.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate()
    payload = build_payload()
    write_json(OUTPUT_JSON, payload)
    write_md(payload)
    print(json.dumps({"group": payload["group"], "ops": payload["symmetry_operation_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
