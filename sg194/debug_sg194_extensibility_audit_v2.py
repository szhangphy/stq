#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from pipeline_v2.models import GroupSpec, ProducerCommand
from pipeline_v2.specs import GROUP10_SPEC, SG194_SPEC, list_group_specs


ROOT = Path(__file__).resolve().parent
PIPELINE = ROOT / "pipeline_v2"

EXT_JSON = ROOT / "sg194_extensibility_audit_v2.json"
EXT_MD = ROOT / "sg194_extensibility_audit_v2.md"
MAP_JSON = ROOT / "sg194_hardcoded_vs_generic_map_v2.json"
MAP_MD = ROOT / "sg194_hardcoded_vs_generic_map_v2.md"
PLAN_JSON = ROOT / "sg194_modularization_plan_v2.json"
PLAN_MD = ROOT / "sg194_modularization_plan_v2.md"
GRAPH_JSON = ROOT / "sg194_module_dependency_graph_v2.json"
GRAPH_MD = ROOT / "sg194_module_dependency_graph_v2.md"
DRIVER_JSON = ROOT / "sg194_pipeline_driver_spec_v2.json"
DRIVER_MD = ROOT / "sg194_pipeline_driver_spec_v2.md"
CONTRACT_JSON = ROOT / "sg194_group_spec_contract_v1.json"
CONTRACT_MD = ROOT / "sg194_group_spec_contract_v1.md"

GENERIC_MODULES = [
    "pipeline_v2/models.py",
    "pipeline_v2/utils.py",
    "pipeline_v2/legacy_bridge.py",
    "pipeline_v2/geometry.py",
    "pipeline_v2/alignment.py",
    "pipeline_v2/bs_ai.py",
    "pipeline_v2/quotient.py",
    "pipeline_v2/checks.py",
    "pipeline_v2/reporting.py",
    "pipeline_v2/driver.py",
    "pipeline_v2/adapters/base.py",
]
SG194_SPECIAL_MODULES = [
    "pipeline_v2/adapters/sg194.py",
    "debug_workflow_portability_194.1.1.1.py",
    "debug_workflow_portability_stage2_194.1.1.1.py",
    "debug_sg194_standard_space_projection_v1.py",
    "debug_sg194_single_exact_target_alignment_v1.py",
    "debug_sg194_single_jk_pairing_proof_v1.py",
    "debug_sg194_single_exact_alignment_regression_v1.py",
]
SECOND_GROUP_MODULES = [
    "pipeline_v2/adapters/ssg10_4_1_31.py",
    "debug_sg194_second_group_smoke_test_v1.py",
]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def md_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def import_graph() -> dict[str, Any]:
    nodes = []
    edges = []
    for path in sorted(PIPELINE.rglob("*.py")):
        rel = path.relative_to(ROOT)
        nodes.append(str(rel))
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level == 1:
                    target = str((path.parent / f"{node.module.split('.')[-1]}.py").relative_to(ROOT))
                    if (ROOT / target).exists():
                        edges.append({"from": str(rel), "to": target})
                elif node.level == 2 and path.parent.name == "adapters":
                    target = str((path.parent.parent / f"{node.module.split('.')[-1]}.py").relative_to(ROOT))
                    if (ROOT / target).exists():
                        edges.append({"from": str(rel), "to": target})
    return {"nodes": nodes, "edges": edges}


def spec_contract_payload() -> dict[str, Any]:
    return {
        "group_spec_fields": [{"name": item.name, "type": str(item.type)} for item in fields(GroupSpec)],
        "producer_command_fields": [{"name": item.name, "type": str(item.type)} for item in fields(ProducerCommand)],
        "specs": [
            {
                "key": spec["key"],
                "group_id": spec["group_id"],
                "runnable": spec["runnable"],
                "trust_level": spec["trust_level"],
                "row_languages": spec["row_languages"],
                "modes": spec["modes"],
                "readiness_note": spec["readiness_note"],
            }
            for spec in list_group_specs()
        ],
        "notes": {
            "repo_relative_artifacts": True,
            "producer_commands_are_repo_relative": True,
            "adapter_key_is_the_group_specific_plugin_boundary": True,
        },
    }


def main() -> int:
    graph = import_graph()
    ext = {
        "current_state": "partially_generic_but_now_adapter_pluggable",
        "can_onboard_other_groups_today": "partially",
        "structural_obstacles": [
            "Group adapters still own artifact interpretation and final-object semantics.",
            "No generic builder yet exists from symmetry operations all the way to BS/AI/quotient.",
        ],
        "data_adapter_obstacles": [
            "Each new group still needs a producer or trusted artifact binding.",
            "Target-row-language builders remain group-dependent unless a generic translation layer is added.",
        ],
        "semantic_obstacles": [
            "SG194 double benchmark-facing semantics are still group-specific.",
            "SG194 single j/k canonicalization remains an isolated normalization hook.",
            "10.4.1.31 is only admitted under symmetry-operations-only trust.",
        ],
        "generic_modules": list(GENERIC_MODULES),
        "sg194_special_modules": list(SG194_SPECIAL_MODULES),
        "second_group_modules": list(SECOND_GROUP_MODULES),
        "registered_specs": list_group_specs(),
        "second_group_status": {
            "group": GROUP10_SPEC.group_id,
            "trust_level": GROUP10_SPEC.trust_level,
            "final_results_available": False,
            "why_not": GROUP10_SPEC.readiness_note,
        },
    }
    hardcoded = {
        "generic_modules": list(GENERIC_MODULES),
        "group_specific_modules": {
            "sg194": list(SG194_SPECIAL_MODULES),
            "ssg10_4_1_31": list(SECOND_GROUP_MODULES),
        },
        "structural_hardcodings": [
            "SG194 final object IDs and benchmark contract are encoded in SG194 spec/adapter.",
            "10.4.1.31 onboarding currently trusts only three committed symmetry-op snapshots.",
        ],
        "data_hardcodings": [
            "SG194 artifact filenames remain 194-specific legacy outputs.",
            "10.4.1.31 trusted source files are fixed to P1/L1/P4 operation dumps.",
        ],
        "semantic_hardcodings": [
            "SG194 single j/k canonical pairing is a spec hook.",
            "SG194 double benchmark-facing meaning is a spec hook.",
        ],
    }
    plan = {
        "architecture": "pipeline_v2",
        "layers": [
            "models",
            "specs",
            "legacy_bridge",
            "adapters",
            "geometry",
            "alignment",
            "bs_ai",
            "quotient",
            "checks",
            "reporting",
            "driver",
            "cli entrypoint",
        ],
        "old_script_policy": {
            "keep_as_backend_or_forensic": list(SG194_SPECIAL_MODULES),
            "deprecated_main_orchestration": [
                "pipeline_v1/*",
                "review_package_sg194_modular_pipeline_v1/*",
            ],
        },
    }
    driver = {
        "entrypoint": "sg194/run_group_pipeline.py",
        "backend_driver": "sg194/pipeline_v2/driver.py",
        "cli_args": [
            "--group",
            "--mode single|double|both",
            "--row-language raw|target|all",
            "--output-dir",
            "--validate",
            "--build-package",
            "--refresh",
            "--list-groups",
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
    }
    contract = spec_contract_payload()

    write_json(EXT_JSON, ext)
    write_json(MAP_JSON, hardcoded)
    write_json(PLAN_JSON, plan)
    write_json(GRAPH_JSON, graph)
    write_json(DRIVER_JSON, driver)
    write_json(CONTRACT_JSON, contract)

    EXT_MD.write_text("\n".join(["# Extensibility Audit v2", "", *md_list([
        f"state: `{ext['current_state']}`",
        f"can onboard other groups today: `{ext['can_onboard_other_groups_today']}`",
        f"second group trust level: `{ext['second_group_status']['trust_level']}`",
    ]), "", "## Structural Obstacles", "", *md_list(ext["structural_obstacles"]), "", "## Data / Adapter Obstacles", "", *md_list(ext["data_adapter_obstacles"]), "", "## Semantic Obstacles", "", *md_list(ext["semantic_obstacles"])]).rstrip() + "\n")
    MAP_MD.write_text("\n".join(["# Hardcoded vs Generic Map v2", "", "## Generic Modules", "", *md_list(hardcoded["generic_modules"]), "", "## SG194-special", "", *md_list(hardcoded["group_specific_modules"]["sg194"]), "", "## Second-group ops-only", "", *md_list(hardcoded["group_specific_modules"]["ssg10_4_1_31"])]).rstrip() + "\n")
    PLAN_MD.write_text("\n".join(["# Modularization Plan v2", "", *md_list(plan["layers"])]).rstrip() + "\n")
    GRAPH_MD.write_text("\n".join(["# Module Dependency Graph v2", "", *md_list([f"{edge['from']} -> {edge['to']}" for edge in graph["edges"]])]).rstrip() + "\n")
    DRIVER_MD.write_text("\n".join(["# Pipeline Driver Spec v2", "", "## CLI", "", *md_list(driver["cli_args"]), "", "## Outputs", "", *md_list(driver["outputs"])]).rstrip() + "\n")
    contract_spec_lines = [
        f"{item['key']} -> {item['group_id']} ({item['trust_level']})"
        for item in contract["specs"]
    ]
    CONTRACT_MD.write_text(
        "\n".join(
            [
                "# Group Spec Contract v1",
                "",
                "## GroupSpec Fields",
                "",
                *md_list([item["name"] for item in contract["group_spec_fields"]]),
                "",
                "## Registered Specs",
                "",
                *md_list(contract_spec_lines),
            ]
        ).rstrip()
        + "\n"
    )
    print(json.dumps({"status": "ok", "registered_specs": [item["key"] for item in contract["specs"]]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
