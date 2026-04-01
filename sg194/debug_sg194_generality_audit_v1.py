from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.utils import now_iso, write_json, write_text

SG194_DIR = REPO_ROOT / "sg194"


def build_payloads() -> tuple[dict[str, object], dict[str, object]]:
    specs_text = (SG194_DIR / "pipeline_v2" / "specs.py").read_text()
    generic_text = (SG194_DIR / "pipeline_v2" / "generic_builders.py").read_text()
    verdict = {
        "generated_at": now_iso(),
        "verdict": "not_truly_general",
        "reason": (
            "The current pipeline_v2 still mixes truly generic modules with case-by-case registry logic "
            "and fake-generic SG194 backend bridges."
        ),
        "truly_generic_parts": [
            "pipeline_v2/models.py data containers",
            "pipeline_v2/coordinates.py coordinate policy gate for A/B conversions",
            "pipeline_v2/reporting.py output writing",
            "pipeline_v2/driver.py orchestration shell",
        ],
        "sg194_specific_parts": [
            "pipeline_v2/specs.py::SG194_SPEC expected_results and benchmark contract",
            "pipeline_v2/adapters/sg194.py single j/k canonical pairing",
            "pipeline_v2/adapters/sg194.py benchmark-facing double semantics",
        ],
        "fake_generic_parts": [
            {
                "file": "sg194/pipeline_v2/generic_builders.py",
                "location": "STAGE1_BACKEND / stage1_backend()",
                "why_not_generic": "directly imports debug_workflow_portability_194.1.1.1.py",
            },
            {
                "file": "sg194/pipeline_v2/generic_builders.py",
                "location": "LOCAL_LIBRARY_BACKEND / local_library_backend()",
                "why_not_generic": "directly imports debug_sg194_nonabelian_local_library.py",
            },
            {
                "file": "sg194/pipeline_v2/specs.py",
                "location": "GROUP222_SPEC registry entry",
                "why_not_generic": "second-group onboarding is still a case-by-case registry object rather than auto-discovered spec ingestion",
            },
        ],
        "static_evidence": {
            "specs_contains_group222_spec": "GROUP222_SPEC = GroupSpec(" in specs_text,
            "generic_builders_uses_stage1_backend": "STAGE1_BACKEND = ROOT / \"debug_workflow_portability_194.1.1.1.py\"" in generic_text,
            "generic_builders_uses_local_library_backend": "LOCAL_LIBRARY_BACKEND = ROOT / \"debug_sg194_nonabelian_local_library.py\"" in generic_text,
        },
    }
    case_map = {
        "generated_at": now_iso(),
        "group": "222.1.1.1",
        "case_by_case_registry_points": [
            {
                "file": "sg194/pipeline_v2/specs.py",
                "object": "SG194_SPEC",
                "kind": "accepted_special_case",
                "reason": "expected_results, benchmark, producer_commands, and special_rules are hardcoded for SG194.",
            },
            {
                "file": "sg194/pipeline_v2/specs.py",
                "object": "GROUP222_SPEC",
                "kind": "case_by_case_probe_spec",
                "reason": "identity map, oracle artifacts, and producer commands are explicit per-group wiring.",
            },
            {
                "file": "sg194/pipeline_v2/generic_builders.py",
                "object": "shared_geometry_bundle / _build_generic_compatibility / _build_local_irrep_library",
                "kind": "fake_generic_bridge",
                "reason": "all three still route through SG194 stage1/backend helper code.",
            },
        ],
    }
    return verdict, case_map


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    verdict, case_map = build_payloads()
    write_json(SG194_DIR / "sg194_generality_verdict_v1.json", verdict)
    write_json(SG194_DIR / "sg194_case_by_case_map_v1.json", case_map)
    write_text(
        SG194_DIR / "sg194_generality_verdict_v1.md",
        "\n".join(
            [
                "# Generality Verdict",
                "",
                f"- verdict: `{verdict['verdict']}`",
                f"- reason: `{verdict['reason']}`",
                "",
                "- truly generic parts:",
                *[f"  - `{item}`" for item in verdict["truly_generic_parts"]],
                "- SG194-specific parts:",
                *[f"  - `{item}`" for item in verdict["sg194_specific_parts"]],
                "- fake-generic parts:",
                *[
                    f"  - `{item['file']}` / `{item['location']}`: `{item['why_not_generic']}`"
                    for item in verdict["fake_generic_parts"]
                ],
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_case_by_case_map_v1.md",
        "\n".join(
            [
                "# Case By Case Map",
                "",
                *[
                    f"- `{item['file']}` / `{item['object']}`: `{item['kind']}` because `{item['reason']}`"
                    for item in case_map["case_by_case_registry_points"]
                ],
            ]
        ),
    )

    if args.validate:
        if verdict["verdict"] != "not_truly_general":
            raise SystemExit("generality verdict unexpectedly changed")
        if not verdict["fake_generic_parts"]:
            raise SystemExit("expected fake-generic parts were not found")


if __name__ == "__main__":
    main()
