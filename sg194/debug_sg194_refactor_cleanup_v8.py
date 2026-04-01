#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.utils import now_iso, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
OUTPUT_JSON = SG194_DIR / "sg194_refactor_cleanup_v8.json"
OUTPUT_MD = SG194_DIR / "sg194_refactor_cleanup_v8.md"

TRACKED_DELETE_TARGETS = [
    "sg194/debug_sg194_222_finalization_probe_v1.py",
    "sg194/sg194_222_single_final_result_v3.json",
    "sg194/sg194_222_single_final_result_v3.md",
    "sg194/sg194_222_double_final_result_v3.json",
    "sg194/sg194_222_double_final_result_v3.md",
    "sg194/sg194_222_final_classification_summary_v3.json",
    "sg194/sg194_222_final_classification_summary_v3.md",
    "sg194/sg194_222_finalization_fix_attempt_v3.json",
    "sg194/sg194_222_finalization_fix_attempt_v3.md",
    "sg194/sg194_222_finalization_gap_v3.json",
    "sg194/sg194_222_finalization_gap_v3.md",
    "sg194/review_package_sg194_generality_and_222_fix_v2",
    "sg194/review_package_sg194_generality_and_222_fix_v2.tar.gz",
    "sg194/sg194_pipeline_consistency_checks_v1.json",
    "sg194/sg194_pipeline_consistency_checks_v1.md",
    "sg194/sg194_pipeline_consistency_checks_v3.json",
    "sg194/sg194_pipeline_consistency_checks_v3.md",
    "sg194/sg194_pipeline_consistency_checks_v5.json",
    "sg194/sg194_pipeline_consistency_checks_v5.md",
    "sg194/sg194_pipeline_consistency_checks_v6.json",
    "sg194/sg194_pipeline_consistency_checks_v6.md",
    "sg194/sg194_pipeline_status_semantics_v2.json",
    "sg194/sg194_pipeline_status_semantics_v2.md",
    "sg194/sg194_pipeline_status_semantics_v3.json",
    "sg194/sg194_pipeline_status_semantics_v3.md",
    "sg194/sg194_refactor_cleanup_v1.json",
    "sg194/sg194_refactor_cleanup_v1.md",
    "sg194/sg194_refactor_cleanup_v2.json",
    "sg194/sg194_refactor_cleanup_v2.md",
    "sg194/sg194_refactor_cleanup_v3.json",
    "sg194/sg194_refactor_cleanup_v3.md",
    "sg194/sg194_refactor_cleanup_v5.json",
    "sg194/sg194_refactor_cleanup_v5.md",
    "sg194/sg194_refactor_cleanup_v6.json",
    "sg194/sg194_refactor_cleanup_v6.md",
]

LOCAL_DELETE_TARGETS = [
    "sg194/review_package_sg194_generic_builder_222_final_v2",
    "sg194/review_package_sg194_modular_pipeline_v3",
    "sg194/pipeline_runs_v2",
    "autoresearch-state.prev.json",
    "research-results.prev.tsv",
    "sg194/__pycache__",
    "sg194/pipeline_v2/__pycache__",
    "sg194/pipeline_v2/adapters/__pycache__",
]


def git_tracked(relpath: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", relpath],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def git_rm(relpath: str) -> None:
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rm", "-r", "-f", relpath],
        check=True,
    )


def git_status_short() -> list[str]:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    git_deleted: list[str] = []
    for relpath in TRACKED_DELETE_TARGETS:
        if not git_tracked(relpath):
            continue
        git_rm(relpath)
        git_deleted.append(relpath)

    local_deleted: list[str] = []
    for relpath in LOCAL_DELETE_TARGETS:
        path = REPO_ROOT / relpath
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        local_deleted.append(relpath)

    payload = {
        "generated_at": now_iso(),
        "git_deleted": git_deleted,
        "local_deleted": local_deleted,
        "git_status_after_cleanup": git_status_short(),
    }

    write_json(OUTPUT_JSON, payload)
    write_text(
        OUTPUT_MD,
        "\n".join(
            [
                "# Refactor Cleanup v8",
                "",
                *[f"- git deleted: `{item}`" for item in git_deleted],
                *[f"- local deleted: `{item}`" for item in local_deleted],
                "",
                "- git status --short after cleanup:",
                *[f"  - `{line}`" for line in payload["git_status_after_cleanup"]],
            ]
        ),
    )

    if args.validate and not OUTPUT_JSON.exists():
        raise SystemExit("refactor cleanup v8 outputs missing")


if __name__ == "__main__":
    main()
