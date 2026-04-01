#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from pipeline_v1.utils import tar_directory


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent

DRIVER = ROOT / "run_group_pipeline.py"
OUTPUT_DIR = ROOT / "pipeline_runs" / "sg194_both_all_latest"
TEMPLATE_OUTPUT_DIR = ROOT / "pipeline_runs" / "template_hex_all_latest"

CONSISTENCY_JSON = ROOT / "sg194_pipeline_consistency_checks_v1.json"
CONSISTENCY_MD = ROOT / "sg194_pipeline_consistency_checks_v1.md"
CLEANUP_JSON = ROOT / "sg194_refactor_cleanup_v1.json"
CLEANUP_MD = ROOT / "sg194_refactor_cleanup_v1.md"

PACKAGE_NAME = "review_package_sg194_modular_pipeline_v1"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

STALE_TRACKED_PATHS = [
    "sg194/review_package_sg194_single_jk_pairing_proof_v1",
    "sg194/review_package_sg194_single_jk_pairing_proof_v1.tar.gz",
]

LOCAL_DELETE_TARGETS = [
    "sg194/review_package_sg194_single_jk_pairing_proof_v1",
]

POST_PACKAGE_LOCAL_DELETE_TARGETS = [
    "sg194/pipeline_runs/sg194_both_all_latest",
    "sg194/pipeline_runs/sg194_both_all_latest.tar.gz",
    "sg194/pipeline_runs/template_hex_all_latest",
    "sg194/pipeline_runs",
]


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def repo_rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def run_check(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def git_tracked(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relpath],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def git_exists_in_head(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{relpath}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def run_driver_checks() -> dict[str, Any]:
    commands = [
        run_check(
            [
                "python3",
                repo_rel(DRIVER),
                "--group",
                "sg194",
                "--mode",
                "both",
                "--row-language",
                "all",
                "--output-dir",
                repo_rel(OUTPUT_DIR),
                "--validate",
                "--build-package",
            ]
        ),
        run_check(
            [
                "python3",
                repo_rel(DRIVER),
                "--group",
                "template-hex",
                "--mode",
                "both",
                "--row-language",
                "all",
                "--output-dir",
                repo_rel(TEMPLATE_OUTPUT_DIR),
                "--validate",
            ]
        ),
    ]
    return {
        "commands": commands,
        "all_passed": all(item["passed"] for item in commands),
    }


def execute_cleanup() -> dict[str, Any]:
    git_deleted: list[str] = []
    for relpath in STALE_TRACKED_PATHS:
        if not git_exists_in_head(relpath):
            continue
        if git_tracked(relpath):
            subprocess.run(["git", "rm", "-r", "-f", relpath], cwd=REPO_ROOT, check=True)
        git_deleted.append(relpath)

    local_deleted: list[str] = []
    for relpath in LOCAL_DELETE_TARGETS:
        target = REPO_ROOT / relpath
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        local_deleted.append(relpath)

    return {
        "generated_at": now_iso(),
        "git_deleted": git_deleted,
        "local_deleted": local_deleted,
        "kept_as_sg194_backend": [
            "debug_workflow_portability_194.1.1.1.py",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_standard_space_projection_v1.py",
            "debug_sg194_single_exact_target_alignment_v1.py",
            "debug_sg194_single_jk_pairing_proof_v1.py",
            "debug_sg194_single_exact_alignment_regression_v1.py",
        ],
    }


def delete_local_targets(relpaths: list[str]) -> list[str]:
    deleted: list[str] = []
    for relpath in relpaths:
        target = REPO_ROOT / relpath
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        deleted.append(relpath)
    return deleted


def build_consistency_payload(driver_checks: dict[str, Any]) -> dict[str, Any]:
    final_status = load_json(OUTPUT_DIR / "final_status_summary.json")
    checks = load_json(OUTPUT_DIR / "consistency_checks.json")
    template_checks = load_json(TEMPLATE_OUTPUT_DIR / "consistency_checks.json")
    return {
        "generated_at": now_iso(),
        "entrypoint": repo_rel(DRIVER),
        "driver_checks": driver_checks,
        "sg194_output_dir": repo_rel(OUTPUT_DIR),
        "template_output_dir": repo_rel(TEMPLATE_OUTPUT_DIR),
        "single_final": final_status["single_final"],
        "double_final": final_status["double_final"],
        "same_final_object": final_status["same_final_object"],
        "sg194_checks_passed": checks["all_passed"],
        "template_checks_passed": template_checks["all_passed"],
        "consistency_verdict": (
            "Unified modular driver preserves the accepted SG194 split: single exact target "
            "13/13/trivial and double benchmark-facing 10/10/Z6. Template spec also validates structurally."
        ),
    }


def build_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True)

    copy_map = {
        "architecture_layer": [
            ROOT / "sg194_extensibility_audit_v1.json",
            ROOT / "sg194_extensibility_audit_v1.md",
            ROOT / "sg194_hardcoded_vs_generic_map_v1.json",
            ROOT / "sg194_hardcoded_vs_generic_map_v1.md",
            ROOT / "sg194_modularization_plan_v1.json",
            ROOT / "sg194_modularization_plan_v1.md",
            ROOT / "sg194_module_dependency_graph_v1.json",
            ROOT / "sg194_module_dependency_graph_v1.md",
        ],
        "driver_layer": [
            ROOT / "run_group_pipeline.py",
            ROOT / "sg194_pipeline_driver_spec_v1.json",
            ROOT / "sg194_pipeline_driver_spec_v1.md",
        ],
        "consistency_layer": [
            ROOT / "sg194_pipeline_consistency_checks_v1.json",
            ROOT / "sg194_pipeline_consistency_checks_v1.md",
            ROOT / "current_status_194.1.1.1_stage2.json",
            ROOT / "workflow_portability_stage2_summary_194.1.1.1.json",
            ROOT / "current_status_1941111_benchmark_v1.json",
            ROOT / "current_status_1941111_benchmark_v1.md",
        ],
        "cleanup_layer": [
            ROOT / "sg194_refactor_cleanup_v1.json",
            ROOT / "sg194_refactor_cleanup_v1.md",
        ],
        "pipeline_run_layer": [
            OUTPUT_DIR / "geometry_summary.json",
            OUTPUT_DIR / "geometry_summary.md",
            OUTPUT_DIR / "representation_alignment_summary.json",
            OUTPUT_DIR / "representation_alignment_summary.md",
            OUTPUT_DIR / "bs_results.json",
            OUTPUT_DIR / "ai_results.json",
            OUTPUT_DIR / "quotient_results.json",
            OUTPUT_DIR / "final_status_summary.json",
            OUTPUT_DIR / "consistency_checks.json",
            OUTPUT_DIR / "package_manifest.json",
        ],
    }
    for subdir, items in copy_map.items():
        target_dir = PACKAGE_DIR / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in items:
            shutil.copy2(item, target_dir / item.name)

    shutil.copytree(
        ROOT / "pipeline_v1",
        PACKAGE_DIR / "driver_layer" / "pipeline_v1",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    write_text(
        PACKAGE_DIR / "README.md",
        "\n".join(
            [
                "# Review Package: SG194 Modular Pipeline v1",
                "",
                "- Purpose: package the extensibility audit, new modular driver, unified consistency checks, and current SG194 single/double stable results.",
                "- Unified entrypoint: `run_group_pipeline.py`.",
                "- SG194 single exact target remains `13 / 13 / trivial`.",
                "- SG194 double benchmark-facing target remains `10 / 10 / Z6`.",
            ]
        ),
    )
    write_text(
        PACKAGE_DIR / "REVIEW_MAP.md",
        "\n".join(
            [
                "# Review Map",
                "",
                "1. `architecture_layer/sg194_extensibility_audit_v1.json`",
                "2. `architecture_layer/sg194_hardcoded_vs_generic_map_v1.json`",
                "3. `architecture_layer/sg194_modularization_plan_v1.json`",
                "4. `architecture_layer/sg194_module_dependency_graph_v1.json`",
                "5. `driver_layer/run_group_pipeline.py`",
                "6. `driver_layer/sg194_pipeline_driver_spec_v1.json`",
                "7. `consistency_layer/sg194_pipeline_consistency_checks_v1.json`",
                "8. `consistency_layer/current_status_194.1.1.1_stage2.json`",
                "9. `consistency_layer/current_status_1941111_benchmark_v1.json`",
                "10. `cleanup_layer/sg194_refactor_cleanup_v1.json`",
                "11. `pipeline_run_layer/final_status_summary.json`",
            ]
        ),
    )
    tar_directory(PACKAGE_DIR, PACKAGE_TARBALL)


def validate_outputs() -> None:
    payload = load_json(CONSISTENCY_JSON)
    cleanup = load_json(CLEANUP_JSON)
    assert payload["driver_checks"]["all_passed"] is True
    assert payload["sg194_checks_passed"] is True
    assert payload["template_checks_passed"] is True
    assert payload["single_final"]["dBS"] == 13
    assert payload["single_final"]["dAI"] == 13
    assert payload["single_final"]["classification"] == "trivial"
    assert payload["double_final"]["dBS"] == 10
    assert payload["double_final"]["dAI"] == 10
    assert payload["double_final"]["classification"] == "Z6"
    assert "sg194/review_package_sg194_single_jk_pairing_proof_v1" in cleanup["git_deleted"]
    assert PACKAGE_DIR.exists()
    assert PACKAGE_TARBALL.exists()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated sg194 pipeline consistency outputs")
        return

    driver_checks = run_driver_checks()
    cleanup = execute_cleanup()
    payload = build_consistency_payload(driver_checks)

    write_json(CONSISTENCY_JSON, payload)
    write_text(
        CONSISTENCY_MD,
        "\n".join(
            [
                "# SG194 Pipeline Consistency Checks v1",
                "",
                f"- driver checks passed: `{payload['driver_checks']['all_passed']}`",
                f"- single final: `{payload['single_final']['dBS']}/{payload['single_final']['dAI']}/{payload['single_final']['classification']}`",
                f"- double final: `{payload['double_final']['dBS']}/{payload['double_final']['dAI']}/{payload['double_final']['classification']}`",
                "- unified modular driver preserves the accepted SG194 single/double split without result drift.",
            ]
        ),
    )

    build_package()
    cleanup["local_deleted"].extend(delete_local_targets(POST_PACKAGE_LOCAL_DELETE_TARGETS))
    write_json(CLEANUP_JSON, cleanup)
    write_text(
        CLEANUP_MD,
        "\n".join(
            [
                "# SG194 Refactor Cleanup v1",
                "",
                f"- git deleted: `{cleanup['git_deleted']}`",
                f"- local deleted: `{cleanup['local_deleted']}`",
                f"- retained SG194 backends: `{cleanup['kept_as_sg194_backend']}`",
            ]
        ),
    )
    validate_outputs()
    print("generated sg194 modular pipeline consistency outputs")


if __name__ == "__main__":
    main()
