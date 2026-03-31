#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PACKAGE_NAME = "review_package_sg194_stage2_closeout_followup_v3"
AUDIT_JSON = ROOT / "sg194_stage2_package_dependency_audit_v1.json"
AUDIT_MD = ROOT / "sg194_stage2_package_dependency_audit_v1.md"
PACKAGE_MANIFEST_MD_NAME = "REPRODUCIBILITY_MANIFEST.md"
PACKAGE_MANIFEST_JSON_NAME = "reproducibility_manifest_v1.json"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def unique_preserve(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


SCRIPT_SPECS = [
    {
        "script": "debug_sg194_standard_space_projection_v1.py",
        "role": "projection_and_final_closeout",
        "smoke_test_command": "python3 debug_sg194_standard_space_projection_v1.py --validate",
        "validate_dependencies": [
            "debug_sg194_standard_space_projection_v1.py",
            "sg194_current_point_space_snapshot_v1.json",
            "sg194_current_to_standard_row_translation_v1.json",
            "sg194_standard_space_projection_summary_v1.json",
            "sg194_final_bs_ai_closeout_report_v1.md",
            "sg194_final_bs_ai_closeout_status_v1.json",
            "sg194_final_bs_ai_closeout_next_step_prompt_v1.txt",
        ],
            "rerun_dependencies": [
            "debug_sg194_standard_space_projection_v1.py",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_workflow_portability_194.1.1.1.py",
            "debug_sg194_nonabelian_local_library.py",
            "sg194_external_ordinary_generator_matrix.json",
            "group_194_1_1_1_single_indicator_generators.json",
            "group_194_1_1_1_double_indicator_generators.json",
            "group_194_1_1_1_single_bs_analysis.json",
            "group_194_1_1_1_double_bs_analysis.json",
            "debug_sg194_stage2_package_dependency_audit_v1.py",
        ],
        "expected_outputs": [
            "sg194_current_point_space_snapshot_v1.json",
            "sg194_current_to_standard_row_translation_v1.json",
            "sg194_standard_space_projection_summary_v1.json",
            "sg194_final_bs_ai_closeout_report_v1.md",
            "sg194_final_bs_ai_closeout_status_v1.json",
            "sg194_final_bs_ai_closeout_next_step_prompt_v1.txt",
        ],
    },
    {
        "script": "debug_workflow_portability_stage2_194.1.1.1.py",
        "role": "authoritative_stage2_closeout",
        "smoke_test_command": "python3 debug_workflow_portability_stage2_194.1.1.1.py --validate",
        "validate_dependencies": [
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_standard_space_projection_v1.py",
            "debug_sg194_stage2_package_dependency_audit_v1.py",
            "debug_sg194_nonabelian_local_library.py",
            "sg194_nonabelian_site_symmetry_inventory.md",
            "sg194_nonabelian_site_symmetry_inventory.json",
            "sg194_single_local_irrep_library.json",
            "sg194_double_local_corep_library.json",
            "group_194_1_1_1_single_ai_completion_summary.json",
            "group_194_1_1_1_double_ai_completion_summary.json",
            "workflow_portability_stage2_audit_194.1.1.1.md",
            "workflow_portability_stage2_summary_194.1.1.1.json",
            "handoff_194.1.1.1_stage2.md",
            "current_status_194.1.1.1_stage2.json",
            "next_step_prompt_194.1.1.1_stage2.txt",
            "workflow_portability_report_stage2_194.1.1.1.tex",
            "workflow_portability_report_stage2_194.1.1.1.pdf",
            "sg194_current_point_space_snapshot_v1.json",
            "sg194_current_to_standard_row_translation_v1.json",
            "sg194_standard_space_projection_summary_v1.json",
            "sg194_final_bs_ai_closeout_report_v1.md",
            "sg194_final_bs_ai_closeout_status_v1.json",
            "sg194_final_bs_ai_closeout_next_step_prompt_v1.txt",
        ],
        "rerun_dependencies": [
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_standard_space_projection_v1.py",
            "debug_sg194_nonabelian_local_library.py",
            "debug_workflow_portability_194.1.1.1.py",
            "workflow_portability_summary_194.1.1.1.json",
            "group_194_1_1_1_single_pilot_summary.json",
            "group_194_1_1_1_single_pilot_audit.md",
            "group_194_1_1_1_double_pilot_summary.json",
            "group_194_1_1_1_double_pilot_audit.md",
            "controlled_case_audit_194.1.1.1.md",
            "current_status_194.1.1.1.json",
            "handoff_194.1.1.1.md",
            "next_step_prompt_194.1.1.1.txt",
            "double_group_ai_completeness_audit_10.4.1.31.md",
            "double_group_ai_completeness_summary_10.4.1.31.json",
            "double_group_indicator_group_summary_10.4.1.31.json",
            "double_group_indicator_generators_10.4.1.31.json",
            "double_group_bs_mod_ai_summary_10.4.1.31.json",
            "double_group_bs_summary_10.4.1.31.json",
            "double_group_bs_basis_raw_10.4.1.31.json",
            "double_group_bs_basis_pretty_10.4.1.31.json",
            "double_group_full_compatibility_with_planes_10.4.1.31.json",
            "single_group_ai_completeness_audit.md",
            "single_group_ai_completeness_summary.json",
            "single_group_indicator_group_summary.json",
            "single_group_indicator_generators.json",
            "single_group_bs_mod_ai_single_summary.json",
            "sg194_external_ordinary_generator_matrix.json",
            "group_194_1_1_1_single_indicator_generators.json",
            "group_194_1_1_1_double_indicator_generators.json",
            "debug_sg194_stage2_package_dependency_audit_v1.py",
            "common/debug_single_group_ai_bridge.py",
            "common/debug_single_group_ai_expanded.py",
            "swyckoff_r.py",
            "swyckoff_k.py",
            "common/SSGReps/SSGReps/SSGReps.py",
            "common/SSGReps/SSGReps/SG_utils.py",
            "common/SSGReps/SSGReps/rep_utils.py",
            "common/SSGReps/ssg_data/identify.pkl.tar.gz",
        ],
        "expected_outputs": [
            "group_194_1_1_1_single_ai_completion_summary.json",
            "group_194_1_1_1_double_ai_completion_summary.json",
            "workflow_portability_stage2_audit_194.1.1.1.md",
            "workflow_portability_stage2_summary_194.1.1.1.json",
            "handoff_194.1.1.1_stage2.md",
            "current_status_194.1.1.1_stage2.json",
            "next_step_prompt_194.1.1.1_stage2.txt",
            "workflow_portability_report_stage2_194.1.1.1.tex",
            "workflow_portability_report_stage2_194.1.1.1.pdf",
        ],
    },
]

AUXILIARY_EXECUTABLE_SPECS = [
    {
        "script": "debug_sg194_nonabelian_local_library.py",
        "role": "helper_nonabelian_local_library_builder",
        "smoke_test_command": None,
        "direct_dependencies": [
            "debug_sg194_nonabelian_local_library.py",
            "debug_workflow_portability_194.1.1.1.py",
            "workflow_portability_summary_194.1.1.1.json",
            "group_194_1_1_1_single_pilot_summary.json",
            "group_194_1_1_1_single_pilot_audit.md",
            "group_194_1_1_1_double_pilot_summary.json",
            "group_194_1_1_1_double_pilot_audit.md",
            "controlled_case_audit_194.1.1.1.md",
            "current_status_194.1.1.1.json",
            "handoff_194.1.1.1.md",
            "next_step_prompt_194.1.1.1.txt",
            "swyckoff_r.py",
            "swyckoff_k.py",
            "common/debug_single_group_ai_bridge.py",
            "common/debug_single_group_ai_expanded.py",
            "common/SSGReps/SSGReps/SSGReps.py",
            "common/SSGReps/SSGReps/SG_utils.py",
            "common/SSGReps/SSGReps/rep_utils.py",
            "common/SSGReps/ssg_data/identify.pkl.tar.gz",
        ],
    },
    {
        "script": "debug_workflow_portability_194.1.1.1.py",
        "role": "upstream_stage1_portability_pilot",
        "smoke_test_command": None,
        "direct_dependencies": [
            "debug_workflow_portability_194.1.1.1.py",
            "workflow_portability_summary_194.1.1.1.json",
            "group_194_1_1_1_single_pilot_summary.json",
            "group_194_1_1_1_single_pilot_audit.md",
            "group_194_1_1_1_double_pilot_summary.json",
            "group_194_1_1_1_double_pilot_audit.md",
            "controlled_case_audit_194.1.1.1.md",
            "current_status_194.1.1.1.json",
            "handoff_194.1.1.1.md",
            "next_step_prompt_194.1.1.1.txt",
            "double_group_ai_completeness_audit_10.4.1.31.md",
            "double_group_ai_completeness_summary_10.4.1.31.json",
            "double_group_indicator_group_summary_10.4.1.31.json",
            "double_group_indicator_generators_10.4.1.31.json",
            "double_group_bs_mod_ai_summary_10.4.1.31.json",
            "double_group_bs_summary_10.4.1.31.json",
            "double_group_bs_basis_raw_10.4.1.31.json",
            "double_group_bs_basis_pretty_10.4.1.31.json",
            "double_group_full_compatibility_with_planes_10.4.1.31.json",
            "single_group_ai_completeness_audit.md",
            "single_group_ai_completeness_summary.json",
            "single_group_indicator_group_summary.json",
            "single_group_indicator_generators.json",
            "single_group_bs_mod_ai_single_summary.json",
            "swyckoff_r.py",
            "swyckoff_k.py",
            "common/debug_single_group_ai_bridge.py",
            "common/debug_single_group_ai_expanded.py",
            "common/SSGReps/SSGReps/SSGReps.py",
            "common/SSGReps/SSGReps/SG_utils.py",
            "common/SSGReps/SSGReps/rep_utils.py",
            "common/SSGReps/ssg_data/identify.pkl.tar.gz",
        ],
    },
    {
        "script": "debug_sg194_stage2_package_dependency_audit_v1.py",
        "role": "package_dependency_audit_and_manifest_builder",
        "smoke_test_command": None,
        "direct_dependencies": [
            "debug_sg194_stage2_package_dependency_audit_v1.py",
            "debug_sg194_standard_space_projection_v1.py",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "REPRODUCIBILITY_MANIFEST.md",
            "reproducibility_manifest_v1.json",
        ],
    },
    {
        "script": "common/debug_single_group_ai_bridge.py",
        "role": "reference_single_group_bridge_helper",
        "smoke_test_command": None,
        "direct_dependencies": [
            "common/debug_single_group_ai_bridge.py",
            "swyckoff_r.py",
            "common/SSGReps/SSGReps/SSGReps.py",
            "common/SSGReps/ssg_data/identify.pkl.tar.gz",
        ],
    },
    {
        "script": "common/debug_single_group_ai_expanded.py",
        "role": "reference_single_group_expanded_ai_helper",
        "smoke_test_command": None,
        "direct_dependencies": [
            "common/debug_single_group_ai_expanded.py",
            "common/debug_single_group_ai_bridge.py",
            "swyckoff_r.py",
            "common/SSGReps/SSGReps/SSGReps.py",
            "common/SSGReps/ssg_data/identify.pkl.tar.gz",
        ],
    },
]

REVIEW_ONLY_FILES = [
    "workflow_portability_report_stage2_194.1.1.1.pdf",
    "workflow_portability_report_stage2_194.1.1.1.tex",
    "workflow_portability_stage2_audit_194.1.1.1.md",
    "workflow_portability_stage2_summary_194.1.1.1.json",
    "current_status_194.1.1.1_stage2.json",
    "handoff_194.1.1.1_stage2.md",
    "next_step_prompt_194.1.1.1_stage2.txt",
    "sg194_final_bs_ai_closeout_report_v1.md",
]

SUGGESTED_REVIEW_ORDER = [
    "sg194_standard_space_projection_summary_v1.json",
    "sg194_current_to_standard_row_translation_v1.json",
    "workflow_portability_stage2_summary_194.1.1.1.json",
    "current_status_194.1.1.1_stage2.json",
    "workflow_portability_report_stage2_194.1.1.1.pdf",
    "REPRODUCIBILITY_MANIFEST.md",
    "group_194_1_1_1_single_ai_completion_summary.json",
    "group_194_1_1_1_double_ai_completion_summary.json",
    "debug_sg194_standard_space_projection_v1.py",
    "debug_workflow_portability_stage2_194.1.1.1.py",
]


def audit_payload(package_dir: Path) -> dict[str, Any]:
    validate_required = unique_preserve(
        [item for spec in SCRIPT_SPECS for item in spec["validate_dependencies"]]
    )
    rerun_required = unique_preserve(
        [item for spec in SCRIPT_SPECS for item in spec["rerun_dependencies"]]
    )
    expected_outputs = unique_preserve(
        [item for spec in SCRIPT_SPECS for item in spec["expected_outputs"]]
    )
    all_required = unique_preserve(validate_required + rerun_required + expected_outputs)
    missing = [item for item in all_required if not (package_dir / item).exists()]
    return {
        "package_name": package_dir.name,
        "package_root": package_dir.name + "/",
        "all_required_present": not missing,
        "missing_files": missing,
        "validate_required_files": validate_required,
        "rerun_required_files": rerun_required,
        "expected_outputs": expected_outputs,
        "review_only_files": REVIEW_ONLY_FILES,
        "suggested_review_order": SUGGESTED_REVIEW_ORDER,
        "scripts": SCRIPT_SPECS,
        "included_executable_scripts": SCRIPT_SPECS + AUXILIARY_EXECUTABLE_SPECS,
        "smoke_test_commands": [
            spec["smoke_test_command"]
            for spec in SCRIPT_SPECS
            if spec.get("smoke_test_command")
        ],
    }


def build_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Stage-2 Package Dependency Audit v1",
        "",
        f"- Package: `{payload['package_name']}`",
        f"- All required files present: `{payload['all_required_present']}`",
        f"- Missing files: `{payload['missing_files']}`",
        "",
        "## Executable Scripts",
        "",
    ]
    for spec in payload["scripts"]:
        lines.extend(
            [
                f"### `{spec['script']}`",
                f"- role: `{spec['role']}`",
                f"- smoke-test command: `{spec['smoke_test_command']}`",
                "- validate dependencies:",
            ]
        )
        lines.extend(f"  - `{item}`" for item in spec["validate_dependencies"])
        lines.append("- rerun dependencies:")
        lines.extend(f"  - `{item}`" for item in spec["rerun_dependencies"])
        lines.append("- expected outputs:")
        lines.extend(f"  - `{item}`" for item in spec["expected_outputs"])
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "- Read-only review path: inspect the PDF/JSON/Markdown outputs and run the two `--validate` smoke-test commands.",
            "- Rerun path: the package includes the direct script/data/runtime dependencies needed to rerun the standard projection and stage-2 authoritative pipeline locally inside the extracted package directory.",
            "- The package is self-contained for package-local execution; it must not rely on `/data/work/...` absolute paths.",
        ]
    )
    return "\n".join(lines)


def build_repro_manifest_json(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_name": payload["package_name"],
        "recommended_review_order": payload["suggested_review_order"],
        "smoke_test_commands": payload["smoke_test_commands"],
        "scripts": payload["included_executable_scripts"],
        "review_only_files": payload["review_only_files"],
        "read_only_boundary": {
            "supported_commands": payload["smoke_test_commands"],
            "description": "These commands only validate package-local outputs and do not regenerate the full pipeline.",
        },
        "rerun_boundary": {
            "description": "Full reruns are supported package-locally for the standard projection and authoritative stage-2 scripts; reruns overwrite package-local outputs only.",
            "primary_scripts": [
                "debug_sg194_standard_space_projection_v1.py",
                "debug_workflow_portability_stage2_194.1.1.1.py",
            ],
        },
    }


def build_repro_manifest_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Reproducibility Manifest",
        "",
        "## Recommended Verification Order",
        "",
    ]
    lines.extend(f"{idx}. `{item}`" for idx, item in enumerate(payload["suggested_review_order"], start=1))
    lines.extend(
        [
            "",
            "## Minimal Smoke Tests",
            "",
        ]
    )
    lines.extend(f"- `{command}`" for command in payload["smoke_test_commands"])
    lines.extend(
        [
            "",
            "## Read-Only Boundary",
            "",
            "- Supported and smoke-tested: the two `--validate` commands above plus direct inspection of the package-local JSON/MD/PDF outputs.",
            "- These commands do not depend on the original repo absolute paths and do not need the package tarball beside them.",
            "",
            "## Rerun Boundary",
            "",
            "- Full reruns may be launched from the extracted package directory with `python3 debug_sg194_standard_space_projection_v1.py` and `python3 debug_workflow_portability_stage2_194.1.1.1.py`.",
            "- Full reruns overwrite package-local outputs only and require local `pdflatex` for the stage-2 PDF build.",
            "- Direct runtime dependencies for those reruns are listed in `reproducibility_manifest_v1.json` and in the dependency audit.",
            "",
            "## Included Executable Scripts",
            "",
        ]
    )
    for spec in payload["included_executable_scripts"]:
        lines.append(f"### `{spec['script']}`")
        lines.append(f"- role: `{spec['role']}`")
        if spec.get("smoke_test_command"):
            lines.append(f"- smoke-test command: `{spec['smoke_test_command']}`")
        else:
            lines.append("- smoke-test command: `not part of the minimal extracted-package smoke test`")
        dep_key = "direct_dependencies" if "direct_dependencies" in spec else "rerun_dependencies"
        lines.append("- direct dependencies:")
        lines.extend(f"  - `{item}`" for item in spec[dep_key])
        lines.append("")
    return "\n".join(lines)


def write_outputs(package_dir: Path, payload: dict[str, Any]) -> None:
    write_json(AUDIT_JSON, payload)
    write_text(AUDIT_MD, build_audit_markdown(payload))
    write_json(package_dir / PACKAGE_MANIFEST_JSON_NAME, build_repro_manifest_json(payload))
    write_text(package_dir / PACKAGE_MANIFEST_MD_NAME, build_repro_manifest_markdown(payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", default=str(ROOT / PACKAGE_NAME))
    args = parser.parse_args()
    package_dir = Path(args.package_dir)
    payload = audit_payload(package_dir)
    write_outputs(package_dir, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
