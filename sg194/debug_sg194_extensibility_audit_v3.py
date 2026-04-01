#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_v2.coordinates import coordinate_contract
from pipeline_v2.specs import list_group_specs


EXT_JSON = ROOT / "sg194_extensibility_audit_v3.json"
EXT_MD = ROOT / "sg194_extensibility_audit_v3.md"
MAP_JSON = ROOT / "sg194_hardcoded_vs_generic_map_v3.json"
MAP_MD = ROOT / "sg194_hardcoded_vs_generic_map_v3.md"
PLAN_JSON = ROOT / "sg194_modularization_plan_v3.json"
PLAN_MD = ROOT / "sg194_modularization_plan_v3.md"
GRAPH_JSON = ROOT / "sg194_module_dependency_graph_v3.json"
GRAPH_MD = ROOT / "sg194_module_dependency_graph_v3.md"
CONTRACT_JSON = ROOT / "sg194_group_spec_contract_v2.json"
CONTRACT_MD = ROOT / "sg194_group_spec_contract_v2.md"


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n")


def build_outputs() -> None:
    specs = list_group_specs()
    ext = {
        "status": "partially_extensible_not_yet_fully_generic",
        "current_primary_test_groups": ["sg194", "222.1.1.1"],
        "structural_blockers": [
            "legacy_bridge.py still drives SG194 via artifact validation rather than generic builders",
            "generic compatibility builder from trusted symmetry ops is still missing",
            "generic local-AI embedding into current-row language is still missing",
        ],
        "data_adapter_blockers": [
            "new groups still need symmetry-op-backed geometry/current-row/local-AI conventions to be interpreted",
            "target-row-language construction remains group-specific once external contracts appear",
        ],
        "semantic_blockers": [
            "SG194 single j/k canonical pairing remains a spec-scoped normalization hook",
            "SG194 double benchmark-facing contract remains SG194-specific semantics",
        ],
        "group_specs": specs,
    }
    generic_map = {
        "generic_modules": [
            "sg194/pipeline_v2/models.py",
            "sg194/pipeline_v2/geometry.py",
            "sg194/pipeline_v2/alignment.py",
            "sg194/pipeline_v2/bs_ai.py",
            "sg194/pipeline_v2/quotient.py",
            "sg194/pipeline_v2/checks.py",
            "sg194/pipeline_v2/reporting.py",
            "sg194/pipeline_v2/driver.py",
            "sg194/pipeline_v2/coordinates.py",
            "common/swyckoff.py",
        ],
        "sg194_special_modules": [
            "sg194/pipeline_v2/adapters/sg194.py",
            "sg194/debug_workflow_portability_194.1.1.1.py",
            "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
            "sg194/debug_sg194_single_exact_target_alignment_v1.py",
        ],
        "second_group_specific_modules": [
            "sg194/pipeline_v2/adapters/ssg222_1_1_1.py",
        ],
        "deprecated_second_group_modules": [
            "sg194/debug_sg194_second_group_smoke_test_v1.py",
        ],
    }
    plan = {
        "module_layers": [
            "models",
            "specs",
            "coordinates",
            "geometry",
            "alignment",
            "bs_ai",
            "quotient",
            "checks",
            "reporting",
            "driver",
            "adapters",
        ],
        "generic_builder_progress": {
            "geometry_builder_from_symmetry_ops": "available",
            "current_row_shell_builder": "available",
            "local_ai_seed_builder": "available",
            "generic_current_row_compatibility_builder": "missing",
            "generic_local_ai_embedding_builder": "missing",
            "generic_direct_quotient_builder": "missing",
        },
    }
    graph = {
        "nodes": {
            "run_group_pipeline.py": ["sg194/pipeline_v2/driver.py"],
            "sg194/pipeline_v2/driver.py": [
                "sg194/pipeline_v2/specs.py",
                "sg194/pipeline_v2/geometry.py",
                "sg194/pipeline_v2/alignment.py",
                "sg194/pipeline_v2/bs_ai.py",
                "sg194/pipeline_v2/quotient.py",
                "sg194/pipeline_v2/checks.py",
                "sg194/pipeline_v2/reporting.py",
                "sg194/pipeline_v2/legacy_bridge.py",
                "sg194/pipeline_v2/adapters/__init__.py",
            ],
            "sg194/pipeline_v2/geometry.py": ["sg194/pipeline_v2/coordinates.py"],
            "sg194/pipeline_v2/alignment.py": ["sg194/pipeline_v2/coordinates.py"],
            "sg194/pipeline_v2/checks.py": ["sg194/pipeline_v2/coordinates.py"],
            "sg194/pipeline_v2/coordinates.py": ["common/swyckoff.py"],
            "common/swyckoff.py": ["common/swyckoff_k.py", "common/swyckoff_r.py"],
        }
    }
    contract = {
        "required_fields": [
            "key",
            "group_id",
            "title",
            "adapter_key",
            "modes",
            "row_languages",
            "builder_backend",
            "capabilities",
            "coordinate_policy",
            "trust_level",
        ],
        "active_specs": specs,
        "coordinate_policy_reference": coordinate_contract(),
    }

    for path, payload in [
        (EXT_JSON, ext),
        (MAP_JSON, generic_map),
        (PLAN_JSON, plan),
        (GRAPH_JSON, graph),
        (CONTRACT_JSON, contract),
    ]:
        write_json(path, payload)

    write_md(
        EXT_MD,
        [
            "# Extensibility Audit V3",
            "",
            f"- status: `{ext['status']}`",
            f"- primary groups: `{', '.join(ext['current_primary_test_groups'])}`",
            "",
            "## Structural Blockers",
            "",
            *[f"- {item}" for item in ext["structural_blockers"]],
            "",
            "## Data/Adapter Blockers",
            "",
            *[f"- {item}" for item in ext["data_adapter_blockers"]],
            "",
            "## Semantic Blockers",
            "",
            *[f"- {item}" for item in ext["semantic_blockers"]],
        ],
    )
    write_md(
        MAP_MD,
        [
            "# Hardcoded vs Generic Map V3",
            "",
            "## Generic Modules",
            "",
            *[f"- `{item}`" for item in generic_map["generic_modules"]],
            "",
            "## SG194-Special Modules",
            "",
            *[f"- `{item}`" for item in generic_map["sg194_special_modules"]],
            "",
            "## Second-Group Specific Modules",
            "",
            *[f"- `{item}`" for item in generic_map["second_group_specific_modules"]],
        ],
    )
    write_md(
        PLAN_MD,
        [
            "# Modularization Plan V3",
            "",
            "## Module Layers",
            "",
            *[f"- `{item}`" for item in plan["module_layers"]],
            "",
            "## Generic Builder Progress",
            "",
            *[f"- `{key}`: `{value}`" for key, value in plan["generic_builder_progress"].items()],
        ],
    )
    write_md(
        GRAPH_MD,
        [
            "# Module Dependency Graph V3",
            "",
            *[f"- `{node}` -> `{', '.join(edges)}`" for node, edges in graph["nodes"].items()],
        ],
    )
    write_md(
        CONTRACT_MD,
        [
            "# Group Spec Contract V2",
            "",
            "## Required Fields",
            "",
            *[f"- `{item}`" for item in contract["required_fields"]],
            "",
            "## Active Specs",
            "",
            *[f"- `{item['key']}` -> `{item['group_id']}` trust=`{item['trust_level']}`" for item in contract["active_specs"]],
        ],
    )


def validate() -> int:
    for path in (EXT_JSON, EXT_MD, MAP_JSON, MAP_MD, PLAN_JSON, PLAN_MD, GRAPH_JSON, GRAPH_MD, CONTRACT_JSON, CONTRACT_MD):
        if not path.exists():
            print(f"missing {path.name}")
            return 1
    payload = json.loads(EXT_JSON.read_text())
    if "222.1.1.1" not in payload.get("current_primary_test_groups", []):
        print("222.1.1.1 missing from extensibility audit")
        return 1
    print("validated extensibility audit v3 outputs")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate extensibility / modularization / group-spec audit outputs v3.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        return validate()
    build_outputs()
    print(json.dumps({"extensibility": EXT_JSON.name, "contract": CONTRACT_JSON.name}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
