#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pipeline_v1.specs import SG194_SPEC, TEMPLATE_SPEC, list_group_specs


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

AUDIT_JSON = ROOT / "sg194_extensibility_audit_v1.json"
AUDIT_MD = ROOT / "sg194_extensibility_audit_v1.md"
HARDCODED_JSON = ROOT / "sg194_hardcoded_vs_generic_map_v1.json"
HARDCODED_MD = ROOT / "sg194_hardcoded_vs_generic_map_v1.md"
PLAN_JSON = ROOT / "sg194_modularization_plan_v1.json"
PLAN_MD = ROOT / "sg194_modularization_plan_v1.md"
GRAPH_JSON = ROOT / "sg194_module_dependency_graph_v1.json"
GRAPH_MD = ROOT / "sg194_module_dependency_graph_v1.md"
DRIVER_JSON = ROOT / "sg194_pipeline_driver_spec_v1.json"
DRIVER_MD = ROOT / "sg194_pipeline_driver_spec_v1.md"

CORE_SCRIPTS = [
    ROOT / "debug_workflow_portability_194.1.1.1.py",
    ROOT / "debug_workflow_portability_stage2_194.1.1.1.py",
    ROOT / "debug_sg194_standard_space_projection_v1.py",
    ROOT / "debug_sg194_single_exact_target_alignment_v1.py",
    ROOT / "debug_sg194_single_jk_pairing_proof_v1.py",
    ROOT / "debug_sg194_single_exact_alignment_regression_v1.py",
]

PATTERNS = {
    "group_id": re.compile(r"194\\.1\\.1\\.1|194_1_1_1"),
    "benchmark_mapping": re.compile(r"194\\.263|1494|OG 194\\.1\\.1494|BNS 194\\.263"),
    "sg194_pairing": re.compile(r"j_A'|j_A''|k_A'|k_A''"),
    "benchmark_value": re.compile(r"Z6|13\\s*/\\s*13|10\\s*/\\s*10"),
}

MODULES = [
    "pipeline_v1/models.py",
    "pipeline_v1/specs.py",
    "pipeline_v1/legacy_bridge.py",
    "pipeline_v1/geometry.py",
    "pipeline_v1/alignment.py",
    "pipeline_v1/bs_ai.py",
    "pipeline_v1/quotient.py",
    "pipeline_v1/checks.py",
    "pipeline_v1/reporting.py",
    "pipeline_v1/driver.py",
    "run_group_pipeline.py",
]


def load_text(path: Path) -> str:
    return path.read_text()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def scan_hardcoding(path: Path) -> dict[str, Any]:
    text = load_text(path)
    hits: dict[str, list[dict[str, Any]]] = {}
    lines = text.splitlines()
    for name, pattern in PATTERNS.items():
        matches = []
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                matches.append({"line": idx, "text": line.strip()})
        if matches:
            hits[name] = matches[:8]
    return {
        "file": path.name,
        "hardcoded_hit_categories": sorted(hits.keys()),
        "hardcoded_hit_count": sum(len(items) for items in hits.values()),
        "sample_hits": hits,
    }


def build_extensibility_audit() -> dict[str, Any]:
    scans = [scan_hardcoding(path) for path in CORE_SCRIPTS]
    return {
        "target_group": SG194_SPEC.group_id,
        "verdict": (
            "The pre-refactor codebase is not directly extensible to other groups: core math and "
            "matrix routines are reusable, but the workflow is gated by SG194-specific paths, "
            "group ids, benchmark conventions, and status/package side effects. After this round, "
            "the new modular pipeline is structurally extensible, but a new group still needs a "
            "group spec plus geometry/alignment adapters."
        ),
        "current_state_summary": {
            "generic_now": [
                "unified pipeline driver interface",
                "result-object normalization",
                "consistency-check runner",
                "reporting/package manifest writer",
                "template second-group spec path",
            ],
            "still_sg194_specific": [
                "legacy stage1/stage2 builders",
                "external ordinary target cache contract",
                "single j/k canonical pairing normalization",
                "benchmark-facing double target interpretation",
            ],
            "hard_blockers_for_new_group": [
                "no generic geometry adapter beyond SG194 legacy scripts",
                "no group-neutral external cache loader beyond SG194 artifact names",
                "no generic special-rule registry outside the SG194 spec map",
            ],
        },
        "core_script_scans": scans,
        "future_group_readiness": {
            "template_spec_available": True,
            "template_spec_key": TEMPLATE_SPEC.key,
            "next_required_extension_points": list(TEMPLATE_SPEC.special_rules["expected_extension_points"]),
        },
    }


def build_hardcoded_vs_generic_map() -> dict[str, Any]:
    return {
        "target_group": SG194_SPEC.group_id,
        "generic_extracts": [
            {
                "area": "pipeline config and group spec interface",
                "source": ["pipeline_v1/models.py", "pipeline_v1/specs.py"],
                "status": "generic",
            },
            {
                "area": "legacy-state validation bridge",
                "source": ["pipeline_v1/legacy_bridge.py"],
                "status": "generic_with_group_spec_inputs",
            },
            {
                "area": "geometry/result/alignment/quoitent reporting adapters",
                "source": [
                    "pipeline_v1/geometry.py",
                    "pipeline_v1/alignment.py",
                    "pipeline_v1/bs_ai.py",
                    "pipeline_v1/quotient.py",
                    "pipeline_v1/checks.py",
                    "pipeline_v1/reporting.py",
                ],
                "status": "generic_with_group_spec_inputs",
            },
            {
                "area": "unified CLI driver",
                "source": ["pipeline_v1/driver.py", "run_group_pipeline.py"],
                "status": "generic",
            },
        ],
        "sg194_specific_hardcoding": [
            {
                "area": "group identifiers and artifact file names",
                "source": [
                    "debug_workflow_portability_194.1.1.1.py",
                    "debug_workflow_portability_stage2_194.1.1.1.py",
                ],
                "reason": "direct 194.1.1.1 constants and SG194-named JSON outputs",
            },
            {
                "area": "ordinary single j/k canonicalization",
                "source": [
                    "debug_sg194_standard_space_projection_v1.py",
                    "debug_workflow_portability_stage2_194.1.1.1.py",
                    "pipeline_v1/specs.py",
                ],
                "reason": "SG194-specific target-label normalization rule",
            },
            {
                "area": "benchmark-facing double target semantics",
                "source": [
                    "debug_workflow_portability_stage2_194.1.1.1.py",
                    "current_status_1941111_benchmark_v1.json",
                ],
                "reason": "specific to SG194 accepted benchmark object",
            },
        ],
        "legacy_script_strategy": [
            {"script": "debug_workflow_portability_194.1.1.1.py", "decision": "keep_as_backend"},
            {"script": "debug_workflow_portability_stage2_194.1.1.1.py", "decision": "keep_as_backend"},
            {"script": "debug_sg194_standard_space_projection_v1.py", "decision": "keep_as_sg194_special_backend"},
            {"script": "debug_sg194_single_exact_target_alignment_v1.py", "decision": "keep_as_sg194_special_audit"},
            {"script": "debug_sg194_single_jk_pairing_proof_v1.py", "decision": "keep_as_sg194_special_audit"},
            {"script": "debug_sg194_single_exact_alignment_regression_v1.py", "decision": "keep_as_sg194_special_regression"},
        ],
    }


def build_modularization_plan() -> dict[str, Any]:
    return {
        "target_group": SG194_SPEC.group_id,
        "new_modules": [
            {"module": "pipeline_v1/models.py", "role": "shared data contracts"},
            {"module": "pipeline_v1/specs.py", "role": "group spec registry and template spec"},
            {"module": "pipeline_v1/legacy_bridge.py", "role": "legacy producer validation and artifact loading"},
            {"module": "pipeline_v1/geometry.py", "role": "shared geometry summary builder"},
            {"module": "pipeline_v1/alignment.py", "role": "row-language/alignment summary builder"},
            {"module": "pipeline_v1/bs_ai.py", "role": "BS/AI result-object normalization"},
            {"module": "pipeline_v1/quotient.py", "role": "quotient summary normalization"},
            {"module": "pipeline_v1/checks.py", "role": "consistency and regression checks"},
            {"module": "pipeline_v1/reporting.py", "role": "unified JSON/MD outputs and package manifests"},
            {"module": "pipeline_v1/driver.py", "role": "unified orchestrator"},
            {"module": "run_group_pipeline.py", "role": "human-facing entrypoint"},
        ],
        "migration_boundaries": [
            "geometry construction remains in the legacy SG194 backend for now",
            "stage2 accepted semantics remain in the legacy SG194 backend for now",
            "new groups plug in through GroupSpec + legacy/generic adapters instead of new ad hoc debug scripts",
        ],
        "success_criteria": [
            "single exact target remains 13/13/trivial",
            "double benchmark-facing target remains 10/10/Z6",
            "driver emits one consistent output bundle",
            "driver validates both SG194 and a second template spec path",
        ],
    }


def build_dependency_graph() -> dict[str, Any]:
    return {
        "nodes": MODULES,
        "edges": [
            {"from": "run_group_pipeline.py", "to": "pipeline_v1/driver.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/specs.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/legacy_bridge.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/geometry.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/alignment.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/bs_ai.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/quotient.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/checks.py"},
            {"from": "pipeline_v1/driver.py", "to": "pipeline_v1/reporting.py"},
            {"from": "pipeline_v1/alignment.py", "to": "pipeline_v1/sg194_special.py"},
            {"from": "pipeline_v1/legacy_bridge.py", "to": "pipeline_v1/utils.py"},
            {"from": "pipeline_v1/reporting.py", "to": "pipeline_v1/utils.py"},
        ],
        "legacy_backend_boundary": [
            "debug_workflow_portability_194.1.1.1.py",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_standard_space_projection_v1.py",
            "debug_sg194_single_exact_target_alignment_v1.py",
            "debug_sg194_single_jk_pairing_proof_v1.py",
            "debug_sg194_single_exact_alignment_regression_v1.py",
        ],
    }


def build_driver_spec() -> dict[str, Any]:
    return {
        "script": "sg194/run_group_pipeline.py",
        "inputs": {
            "group": ["sg194", "template-hex"],
            "mode": ["single", "double", "both"],
            "row_language": ["raw", "target", "all"],
            "output_dir": "arbitrary writable directory",
            "validate": "run legacy validation bridge + consistency checks",
            "build_package": "tar the per-run output directory",
            "refresh": "rerun legacy SG194 producers instead of validate-only",
        },
        "outputs": [
            "geometry_summary.json/md",
            "representation_alignment_summary.json/md",
            "bs_results.json/md",
            "ai_results.json/md",
            "quotient_results.json/md",
            "final_status_summary.json/md",
            "consistency_checks.json/md",
            "package_manifest.json",
            "optional per-run tarball",
        ],
        "example_commands": [
            "python3 sg194/run_group_pipeline.py --group sg194 --mode both --row-language all --output-dir sg194/pipeline_runs/sg194_both_all_latest --validate --build-package",
            "python3 sg194/run_group_pipeline.py --group template-hex --mode both --row-language all --output-dir sg194/pipeline_runs/template_hex_all_latest --validate",
        ],
        "list_groups": list_group_specs(),
    }


def build_markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines])


def validate_outputs() -> None:
    audit = json.loads(AUDIT_JSON.read_text())
    hardcoded = json.loads(HARDCODED_JSON.read_text())
    plan = json.loads(PLAN_JSON.read_text())
    graph = json.loads(GRAPH_JSON.read_text())
    driver = json.loads(DRIVER_JSON.read_text())
    assert audit["future_group_readiness"]["template_spec_available"] is True
    assert any(item["decision"] == "keep_as_backend" for item in hardcoded["legacy_script_strategy"])
    assert any(item["module"] == "pipeline_v1/driver.py" for item in plan["new_modules"])
    assert any(edge["from"] == "run_group_pipeline.py" for edge in graph["edges"])
    assert driver["script"] == "sg194/run_group_pipeline.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated sg194 extensibility audit outputs")
        return

    audit = build_extensibility_audit()
    hardcoded = build_hardcoded_vs_generic_map()
    plan = build_modularization_plan()
    graph = build_dependency_graph()
    driver = build_driver_spec()

    write_json(AUDIT_JSON, audit)
    write_json(HARDCODED_JSON, hardcoded)
    write_json(PLAN_JSON, plan)
    write_json(GRAPH_JSON, graph)
    write_json(DRIVER_JSON, driver)

    write_text(
        AUDIT_MD,
        build_markdown(
            "SG194 Extensibility Audit v1",
            [
                "- Pre-refactor answer: no, the SG194 workflow was not directly extensible to other groups.",
                "- Post-refactor answer: partially yes; the new driver/spec/reporting/check layers are generic, but new groups still need geometry and alignment adapters.",
                "- Template second-group spec now exists and validates structurally.",
            ],
        ),
    )
    write_text(
        HARDCODED_MD,
        build_markdown(
            "SG194 Hardcoded vs Generic Map v1",
            [
                "- Generic modules now live in `pipeline_v1/` and are driven by `GroupSpec`.",
                "- SG194-specific logic is isolated to SG194 backend scripts and the SG194 spec special-rule map.",
                "- The single j/k canonicalization remains SG194-specific and is no longer scattered through unrelated driver code.",
            ],
        ),
    )
    write_text(
        PLAN_MD,
        build_markdown(
            "SG194 Modularization Plan v1",
            [
                "- Keep geometry and accepted-status production in the SG194 legacy backend for now.",
                "- Normalize outputs through `pipeline_v1/*` and route all orchestration through `run_group_pipeline.py`.",
                "- Use `GroupSpec` plus a template spec as the extension surface for future groups.",
            ],
        ),
    )
    write_text(
        GRAPH_MD,
        build_markdown(
            "SG194 Module Dependency Graph v1",
            [
                "- `run_group_pipeline.py` -> `pipeline_v1/driver.py` is the only public entry edge.",
                "- `pipeline_v1/driver.py` orchestrates legacy validation, summaries, checks, and reporting.",
                "- SG194-specific forensic scripts remain behind the legacy backend boundary.",
            ],
        ),
    )
    write_text(
        DRIVER_MD,
        build_markdown(
            "SG194 Pipeline Driver Spec v1",
            [
                "- entrypoint: `python3 sg194/run_group_pipeline.py`",
                "- supported groups: `sg194`, `template-hex`",
                "- supports `single|double|both` and `raw|target|all`",
                "- emits unified geometry/alignment/BS/AI/quotient/status/check manifests",
            ],
        ),
    )
    validate_outputs()
    print("generated sg194 extensibility audit outputs")


if __name__ == "__main__":
    main()
