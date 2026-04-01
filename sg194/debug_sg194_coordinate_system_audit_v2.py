#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_v2.coordinates import coordinate_contract, coordinate_usage_audit


AUDIT_JSON = ROOT / "sg194_coordinate_system_audit_v2.json"
AUDIT_MD = ROOT / "sg194_coordinate_system_audit_v2.md"
CONTRACT_JSON = ROOT / "sg194_coordinate_conversion_contract_v2.json"
CONTRACT_MD = ROOT / "sg194_coordinate_conversion_contract_v2.md"


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n")


def build_outputs() -> None:
    audit = coordinate_usage_audit()
    contract = coordinate_contract()
    contract["operational_summary"] = {
        "a_only_modules": audit["a_only_modules"],
        "b_only_modules": audit["b_only_modules"],
        "conversion_authority_module": audit["conversion_authority_module"],
        "all_passed": audit["all_passed"],
    }

    write_json(AUDIT_JSON, audit)
    write_json(CONTRACT_JSON, contract)

    write_md(
        AUDIT_MD,
        [
            "# Coordinate System Audit V2",
            "",
            f"- coordinate system A: `{audit['coordinate_system_a']}`",
            f"- coordinate system B: `{audit['coordinate_system_b']}`",
            f"- conversion authority: `{audit['conversion_authority_module']}`",
            f"- all passed: `{audit['all_passed']}`",
            "",
            "## A-Only Modules",
            "",
            *[f"- `{item}`" for item in audit["a_only_modules"]],
            "",
            "## B-Only Modules",
            "",
            *[f"- `{item}`" for item in audit["b_only_modules"]],
            "",
            "## Violations",
            "",
            *(["- none"] if not audit["violations"] else [f"- `{item['path']}`: `{item['problem']}`" for item in audit["violations"]]),
        ],
    )
    write_md(
        CONTRACT_MD,
        [
            "# Coordinate Conversion Contract V2",
            "",
            f"- coordinate system A owner: `{', '.join(contract['a_owner_modules'])}`",
            f"- coordinate system B owner modules: `{len(contract['b_owner_modules'])}` declared entries",
            f"- conversion authority: `{contract['conversion_authority']}`",
            "",
            "## Conversion Sources",
            "",
            f"- k-space: `{contract['conversion_sources']['kspace']['module']}` -> `{', '.join(contract['conversion_sources']['kspace']['functions'])}`",
            f"- real-space: `{contract['conversion_sources']['realspace']['module']}` -> `{', '.join(contract['conversion_sources']['realspace']['functions'])}`",
            "",
            "## Notes",
            "",
            *[f"- {item}" for item in contract["notes"]],
        ],
    )


def validate() -> int:
    for path in (AUDIT_JSON, AUDIT_MD, CONTRACT_JSON, CONTRACT_MD):
        if not path.exists():
            print(f"missing {path.name}")
            return 1
    audit = json.loads(AUDIT_JSON.read_text())
    if audit.get("all_passed") is not True:
        print("coordinate audit failed")
        return 1
    contract = json.loads(CONTRACT_JSON.read_text())
    if contract.get("conversion_authority") != "common/swyckoff.py":
        print("wrong conversion authority")
        return 1
    print("validated coordinate-system audit v2 outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate coordinate-system audit and conversion contract v2.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate()
    build_outputs()
    print(json.dumps({"audit": AUDIT_JSON.name, "contract": CONTRACT_JSON.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
