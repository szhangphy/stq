#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

CONSISTENCY_JSON = ROOT / "sg194_pipeline_consistency_checks_v2.json"
CONSISTENCY_MD = ROOT / "sg194_pipeline_consistency_checks_v2.md"
CLEANUP_JSON = ROOT / "sg194_refactor_cleanup_v2.json"
CLEANUP_MD = ROOT / "sg194_refactor_cleanup_v2.md"

REVIEW_DIR = ROOT / "review_package_sg194_modular_pipeline_v2"
REVIEW_TAR = ROOT / "review_package_sg194_modular_pipeline_v2.tar.gz"

OLD_GIT_DELETE = [
    ROOT / "review_package_sg194_modular_pipeline_v1",
    ROOT / "review_package_sg194_modular_pipeline_v1.tar.gz",
]
LOCAL_DELETE = [
    ROOT / "pipeline_runs_v2" / "sg194_both_all_latest",
    ROOT / "pipeline_runs_v2" / "sg194_both_all_latest.tar.gz",
    ROOT / "pipeline_runs_v2" / "ssg10_4_1_31_both_all_latest",
    ROOT / "pipeline_runs_v2" / "ssg10_4_1_31_both_all_latest.tar.gz",
    ROOT / "pipeline_runs_v2",
]


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def run_checked(cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def build_review_package() -> None:
    if REVIEW_DIR.exists():
        shutil.rmtree(REVIEW_DIR)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    mapping = {
        "architecture_layer": [
            "sg194_extensibility_audit_v2.json",
            "sg194_extensibility_audit_v2.md",
            "sg194_hardcoded_vs_generic_map_v2.json",
            "sg194_hardcoded_vs_generic_map_v2.md",
            "sg194_modularization_plan_v2.json",
            "sg194_modularization_plan_v2.md",
            "sg194_module_dependency_graph_v2.json",
            "sg194_module_dependency_graph_v2.md",
            "sg194_group_spec_contract_v1.json",
            "sg194_group_spec_contract_v1.md",
        ],
        "driver_layer": [
            "run_group_pipeline.py",
            "pipeline_v2",
            "sg194_pipeline_driver_spec_v2.json",
            "sg194_pipeline_driver_spec_v2.md",
        ],
        "consistency_layer": [
            "sg194_pipeline_consistency_checks_v2.json",
            "sg194_pipeline_consistency_checks_v2.md",
            "current_status_194.1.1.1_stage2.json",
            "current_status_1941111_benchmark_v1.json",
            "workflow_portability_stage2_summary_194.1.1.1.json",
        ],
        "second_group_layer": [
            "sg194_second_group_onboarding_v1.json",
            "sg194_second_group_onboarding_v1.md",
        ],
        "cleanup_layer": [
            "sg194_refactor_cleanup_v2.json",
            "sg194_refactor_cleanup_v2.md",
        ],
    }
    for folder, names in mapping.items():
        target_dir = REVIEW_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            source = ROOT / name
            if source.is_dir():
                shutil.copytree(source, target_dir / source.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            else:
                shutil.copy2(source, target_dir / source.name)
    (REVIEW_DIR / "README.md").write_text(
        "# SG194 Modular Pipeline v2\n\n"
        "- architecture_layer: extensibility audit and spec contract\n"
        "- driver_layer: unified CLI and pipeline_v2 modules\n"
        "- consistency_layer: SG194 regression status and v2 consistency checks\n"
        "- second_group_layer: symmetry-ops-only onboarding for 10.4.1.31\n"
        "- cleanup_layer: retired v1 package and local runtime cleanup\n"
    )
    (REVIEW_DIR / "REVIEW_MAP.md").write_text(
        "# Review Map\n\n"
        "- SG194 final preserved: single `13/13/trivial`, double `10/10/Z6`\n"
        "- Second-group trust policy: symmetry operations only; BS/AI/quotient blocked\n"
        "- Unified entrypoint: `sg194/run_group_pipeline.py`\n"
    )
    if REVIEW_TAR.exists():
        REVIEW_TAR.unlink()
    subprocess.run(["tar", "-czf", str(REVIEW_TAR), REVIEW_DIR.name], cwd=ROOT, check=True)


def cleanup_old_outputs() -> dict[str, Any]:
    git_deleted = []
    for path in OLD_GIT_DELETE:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            git_deleted.append(repo_rel(path))
    local_deleted = []
    for path in LOCAL_DELETE:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            local_deleted.append(repo_rel(path))
    cleanup = {
        "git_deleted": git_deleted,
        "local_deleted": local_deleted,
        "kept_as_backends": [
            "sg194/pipeline_v1",
            "sg194/debug_workflow_portability_194.1.1.1.py",
            "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
            "sg194/debug_sg194_standard_space_projection_v1.py",
            "sg194/debug_sg194_single_exact_target_alignment_v1.py",
            "sg194/debug_sg194_single_jk_pairing_proof_v1.py",
            "sg194/debug_sg194_single_exact_alignment_regression_v1.py",
        ],
    }
    write_json(CLEANUP_JSON, cleanup)
    CLEANUP_MD.write_text(
        "\n".join(
            [
                "# Refactor Cleanup v2",
                "",
                "## Git Deleted",
                "",
                *[f"- `{item}`" for item in cleanup["git_deleted"]],
                "",
                "## Local Deleted",
                "",
                *[f"- `{item}`" for item in cleanup["local_deleted"]],
            ]
        ).rstrip()
        + "\n"
    )
    return cleanup


def main() -> int:
    parser = argparse.ArgumentParser(description="Run modular pipeline v2 consistency checks and build review package.")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        payload = load_json(CONSISTENCY_JSON)
        if not payload["all_passed"]:
            raise SystemExit("consistency payload says all_passed=false")
        if payload["sg194"]["single"] != {"dBS": 13, "dAI": 13, "classification": "trivial"}:
            raise SystemExit("sg194 single drift")
        if payload["sg194"]["double"] != {"dBS": 10, "dAI": 10, "classification": "Z6"}:
            raise SystemExit("sg194 double drift")
        if payload["second_group"]["final_results_available"] is not False:
            raise SystemExit("second-group readiness payload inconsistent")
        if not REVIEW_DIR.exists() or not REVIEW_TAR.exists():
            raise SystemExit("review package missing")
        print("validation_ok")
        return 0

    commands = [
        ["python3", str(ROOT / "debug_sg194_second_group_smoke_test_v1.py")],
        ["python3", str(ROOT / "debug_sg194_extensibility_audit_v2.py")],
        [
            "python3",
            str(ROOT / "run_group_pipeline.py"),
            "--group",
            "sg194",
            "--mode",
            "both",
            "--row-language",
            "all",
            "--output-dir",
            str(ROOT / "pipeline_runs_v2" / "sg194_both_all_latest"),
            "--validate",
            "--build-package",
        ],
        [
            "python3",
            str(ROOT / "run_group_pipeline.py"),
            "--group",
            "10.4.1.31",
            "--mode",
            "both",
            "--row-language",
            "all",
            "--output-dir",
            str(ROOT / "pipeline_runs_v2" / "ssg10_4_1_31_both_all_latest"),
            "--validate",
            "--build-package",
        ],
    ]
    results = [run_checked(command) for command in commands]
    sg194_final = load_json(ROOT / "pipeline_runs_v2" / "sg194_both_all_latest" / "final_status_summary.json")
    second_final = load_json(ROOT / "pipeline_runs_v2" / "ssg10_4_1_31_both_all_latest" / "final_status_summary.json")
    second_onboarding = load_json(ROOT / "sg194_second_group_onboarding_v1.json")

    payload = {
        "driver_script": "sg194/run_group_pipeline.py",
        "commands": results,
        "sg194": {
            "single": {
                "dBS": sg194_final["single_final"]["dBS"],
                "dAI": sg194_final["single_final"]["dAI"],
                "classification": sg194_final["single_final"]["classification"],
            },
            "double": {
                "dBS": sg194_final["double_final"]["dBS"],
                "dAI": sg194_final["double_final"]["dAI"],
                "classification": sg194_final["double_final"]["classification"],
            },
        },
        "second_group": {
            "group": "10.4.1.31",
            "trust_policy": second_onboarding["trust_policy"],
            "final_results_available": False,
            "primary_blocker": second_onboarding["primary_blocker"],
            "missing_generic_builders": second_onboarding["missing_generic_builders"],
            "final_status": second_final,
        },
    }
    payload["all_passed"] = all(item["passed"] for item in results)
    write_json(CONSISTENCY_JSON, payload)
    CONSISTENCY_MD.write_text(
        "\n".join(
            [
                "# Pipeline Consistency Checks v2",
                "",
                f"- all passed: `{payload['all_passed']}`",
                f"- SG194 single: `{payload['sg194']['single']}`",
                f"- SG194 double: `{payload['sg194']['double']}`",
                f"- second group trust policy: `{payload['second_group']['trust_policy']}`",
                f"- second group blocker: `{payload['second_group']['primary_blocker']}`",
            ]
        ).rstrip()
        + "\n"
    )
    cleanup_old_outputs()
    build_review_package()
    print(json.dumps({"status": "ok", "all_passed": payload["all_passed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
