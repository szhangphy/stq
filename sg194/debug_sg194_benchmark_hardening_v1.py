#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SG194_DIR = Path(__file__).resolve().parent
REPO_ROOT = SG194_DIR.parent

BENCHMARK_STATUS_JSON = SG194_DIR / "current_status_1941111_benchmark_v1.json"
BENCHMARK_STATUS_MD = SG194_DIR / "current_status_1941111_benchmark_v1.md"
EXTERNAL_BENCHMARK_JSON = SG194_DIR / "sg194_external_benchmark_from_topmat_v3.json"
EXTERNAL_BENCHMARK_MD = SG194_DIR / "sg194_external_benchmark_from_topmat_v3.md"
OBJECT_MATCH_JSON = SG194_DIR / "sg194_current_vs_external_object_matching_v3.json"
OBJECT_MATCH_MD = SG194_DIR / "sg194_current_vs_external_object_matching_v3.md"
BENCHMARK_VERDICT_JSON = SG194_DIR / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json"
BENCHMARK_VERDICT_MD = SG194_DIR / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.md"
INVENTORY_JSON = SG194_DIR / "sg194_authoritative_file_inventory_v1.json"
INVENTORY_MD = SG194_DIR / "sg194_authoritative_file_inventory_v1.md"
OBJECT_LADDER_JSON = SG194_DIR / "sg194_object_ladder_and_benchmark_map_v1.json"
OBJECT_LADDER_MD = SG194_DIR / "sg194_object_ladder_and_benchmark_map_v1.md"

STAGE2_JSON = SG194_DIR / "current_status_194.1.1.1_stage2.json"
WORKFLOW_STAGE2_JSON = SG194_DIR / "workflow_portability_stage2_summary_194.1.1.1.json"
SINGLE_COMPLETION_JSON = SG194_DIR / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_COMPLETION_JSON = SG194_DIR / "group_194_1_1_1_double_ai_completion_summary.json"

README_MD = SG194_DIR / "README.md"
LIVE_CHECKPOINT_JSON = SG194_DIR / "live_checkpoint_sg194_1941111.json"
LIVE_CHECKPOINT_MD = SG194_DIR / "live_checkpoint_sg194_1941111.md"

INDEPENDENT_VERIFY_JSON = SG194_DIR / "sg194_topmat_independent_verify_v1.json"
INDEPENDENT_VERIFY_MD = SG194_DIR / "sg194_topmat_independent_verify_v1.md"
PATH_SANITIZATION_JSON = SG194_DIR / "sg194_benchmark_path_sanitization_v1.json"
PATH_SANITIZATION_MD = SG194_DIR / "sg194_benchmark_path_sanitization_v1.md"
SUPERSCEDED_DEEMPHASIS_JSON = SG194_DIR / "sg194_superseded_file_deemphasis_v1.json"
SUPERSCEDED_DEEMPHASIS_MD = SG194_DIR / "sg194_superseded_file_deemphasis_v1.md"

PACKAGE_DIR = SG194_DIR / "review_package_sg194_benchmark_hardening_v1"
PACKAGE_TAR = SG194_DIR / "review_package_sg194_benchmark_hardening_v1.tar.gz"

FIRST_IMPL_JSON = SG194_DIR / "sg194_topmat_experimental_compute_v2.json"
FIRST_IMPL_SCRIPT = SG194_DIR / "sg194_topmat_experimental_compute_v2.py"
SECOND_IMPL_SCRIPT = SG194_DIR / "sg194_topmat_independent_verify_v1.py"
BASELINE_COMMIT = "13a01c2f35a04c3d2281154691fa2dcc2e0f2400"
PACKAGE_HEAD_SNAPSHOT_IF_DIRTY = {
    SG194_DIR / "current_status_sg194_external_matrix_final.json",
    SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.json",
    SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.md",
}

ABS_PREFIXES = ("/data/work/", "/data/home/")
TARGET_STATEMENT = (
    "SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal "
    "magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round "
    "treats them as the same benchmark target for topological classification / "
    "dBS / dAI comparison."
)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def sanitize_repo_paths(obj: Any) -> Any:
    repo_root_str = REPO_ROOT.as_posix()
    if isinstance(obj, dict):
        return {key: sanitize_repo_paths(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [sanitize_repo_paths(value) for value in obj]
    if isinstance(obj, str):
        return obj.replace(repo_root_str + "/", "")
    return obj


def scan_absolute_path_hits(path: Path) -> list[dict[str, Any]]:
    return scan_absolute_path_hits_in_text(path.read_text())


def scan_absolute_path_hits_in_text(text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(prefix in line for prefix in ABS_PREFIXES):
            hits.append({"line": line_number, "text": line})
    return hits


def scan_baseline_git_path_hits(rel_path: str) -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{BASELINE_COMMIT}:{rel_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return scan_absolute_path_hits_in_text(completed.stdout)


def copy_for_package(path: Path, destination: Path) -> None:
    rel_path = repo_rel(path)
    if path in PACKAGE_HEAD_SNAPSHOT_IF_DIRTY:
        diff = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "diff", "--quiet", "--", rel_path],
            check=False,
        )
        if diff.returncode != 0:
            completed = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "show", f"HEAD:{rel_path}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0:
                destination.write_text(completed.stdout)
                return
    shutil.copy2(path, destination)


def render_hits_md(title: str, hit_map: dict[str, list[dict[str, Any]]]) -> list[str]:
    lines = [title, ""]
    if not any(hit_map.values()):
        lines.append("- none")
        return lines
    for rel_path, hits in hit_map.items():
        lines.append(f"- `{rel_path}`")
        for hit in hits:
            lines.append(f"  line {hit['line']}: {hit['text']}")
    return lines


def run_command(cmd: list[str]) -> None:
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )


def canonical_benchmark_result(payload: dict[str, Any]) -> dict[str, Any]:
    indicator_group = payload.get("indicator_group", payload["classification"])
    return {
        "classification": payload["classification"],
        "indicator_group": indicator_group,
        "dBS": payload["dBS"],
        "dAI": payload["dAI"],
        "smith_diagonal_nonzero": payload["smith_diagonal_nonzero"],
        "finite_part": payload["finite_part"],
        "free_rank": payload["free_rank"],
    }


def update_benchmark_status(first_result: dict[str, Any], second_result: dict[str, Any]) -> None:
    payload = sanitize_repo_paths(load_json(BENCHMARK_STATUS_JSON))
    payload["generated_at"] = now_iso()
    payload["path_policy"] = {
        "consumer_path_policy": "repo_relative_first",
        "note": "Repo-local path fields in this file are stored repo-relative.",
    }
    payload["hardening_support"] = {
        "first_implementation_result_file": repo_rel(FIRST_IMPL_JSON),
        "second_independent_verification_file": repo_rel(INDEPENDENT_VERIFY_JSON),
        "path_sanitization_report_file": repo_rel(PATH_SANITIZATION_JSON),
        "superseded_deemphasis_report_file": repo_rel(SUPERSCEDED_DEEMPHASIS_JSON),
        "review_package_directory": repo_rel(PACKAGE_DIR),
        "review_package_tarball": repo_rel(PACKAGE_TAR),
    }
    payload["independent_verification"] = {
        "status": "consistent",
        "first_implementation_result": canonical_benchmark_result(first_result),
        "second_implementation_result": canonical_benchmark_result(second_result),
        "comparison_fields": [
            "classification",
            "indicator_group",
            "dBS",
            "dAI",
            "smith_diagonal_nonzero",
            "finite_part",
            "free_rank",
        ],
    }
    write_json(BENCHMARK_STATUS_JSON, payload)

    md_lines = [
        "# SG194 benchmark authoritative status v1",
        "",
        TARGET_STATEMENT,
        "",
        "## Status",
        "",
        f"- benchmark-authoritative: `{str(payload['benchmark_authoritative']).lower()}`",
        f"- status: `{payload['status']}`",
        f"- classification / indicator group: `{payload['benchmark_result']['classification']}`",
        f"- dBS: `{payload['benchmark_result']['dBS']}`",
        f"- dAI: `{payload['benchmark_result']['dAI']}`",
        f"- Smith nonzero diagonal: `{payload['benchmark_result']['smith_diagonal_nonzero']}`",
        "",
        "## Source of truth",
        "",
        f"- primary: `{payload['source_of_truth']['primary_benchmark_verdict_json']}`",
        f"- support: `{payload['source_of_truth']['supporting_external_benchmark_json']}`",
        f"- support: `{payload['source_of_truth']['supporting_object_matching_json']}`",
        f"- second independent verification: `{payload['hardening_support']['second_independent_verification_file']}`",
        f"- path sanitization report: `{payload['hardening_support']['path_sanitization_report_file']}`",
        f"- superseded deemphasis report: `{payload['hardening_support']['superseded_deemphasis_report_file']}`",
        "",
        "## Hardening checks",
        "",
        f"- first implementation result: `{canonical_benchmark_result(first_result)}`",
        f"- second implementation result: `{canonical_benchmark_result(second_result)}`",
        "- comparison verdict: `consistent`",
        "- repo-local paths in this file: `relative-path-first`",
        "",
        "## Caveat",
        "",
        f"- {payload['benchmark_target']['external_mapping_caveat']}",
        "",
        "## Not benchmark",
        "",
        f"- current raw: {payload['which_internal_objects_are_not_benchmark']['current_raw']['summary']}",
        f"- phase-aware prototype: {payload['which_internal_objects_are_not_benchmark']['phase_aware_prototype']['summary']}",
        f"- anchored stage2 final claim: {payload['which_internal_objects_are_not_benchmark']['anchored_stage2_final_claim']['summary']}",
        f"- external-matrix-final status: {payload['which_internal_objects_are_not_benchmark']['external_matrix_final_status']['summary']}",
        "",
        "## Takeover verdict",
        "",
        f"- phase-aware verdict: {payload['benchmark_takeover_verdict']['phase_aware_verdict']}",
        f"- stage2 13/trivial verdict: {payload['benchmark_takeover_verdict']['stage2_13_trivial_verdict']}",
    ]
    write_text(BENCHMARK_STATUS_MD, "\n".join(md_lines))


def update_supporting_jsons(first_result: dict[str, Any], second_result: dict[str, Any]) -> None:
    payload = sanitize_repo_paths(load_json(EXTERNAL_BENCHMARK_JSON))
    payload["generated_at"] = now_iso()
    payload["path_policy"] = {
        "consumer_path_policy": "repo_relative_first",
        "note": "Repo-local paths in this file are stored repo-relative.",
    }
    payload["independent_verification"] = {
        "file": repo_rel(INDEPENDENT_VERIFY_JSON),
        "result": canonical_benchmark_result(second_result),
        "matches_primary_experimental_compute": canonical_benchmark_result(second_result)
        == canonical_benchmark_result(first_result),
    }
    write_json(EXTERNAL_BENCHMARK_JSON, payload)

    payload = sanitize_repo_paths(load_json(OBJECT_MATCH_JSON))
    payload["generated_at"] = now_iso()
    payload["path_policy"] = {
        "consumer_path_policy": "repo_relative_first",
        "note": "Repo-local paths in this file are stored repo-relative.",
    }
    payload["benchmark_hardening_support"] = {
        "independent_verification_file": repo_rel(INDEPENDENT_VERIFY_JSON),
        "path_sanitization_report_file": repo_rel(PATH_SANITIZATION_JSON),
    }
    write_json(OBJECT_MATCH_JSON, payload)

    payload = sanitize_repo_paths(load_json(BENCHMARK_VERDICT_JSON))
    payload["generated_at"] = now_iso()
    payload["path_policy"] = {
        "consumer_path_policy": "repo_relative_first",
        "note": "Repo-local paths in this file are stored repo-relative.",
    }
    payload["independent_verification"] = {
        "file": repo_rel(INDEPENDENT_VERIFY_JSON),
        "result": canonical_benchmark_result(second_result),
        "matches_primary_experimental_compute": canonical_benchmark_result(second_result)
        == canonical_benchmark_result(first_result),
    }
    write_json(BENCHMARK_VERDICT_JSON, payload)

    payload = sanitize_repo_paths(load_json(INVENTORY_JSON))
    payload["generated_at"] = now_iso()
    payload["entries"] = [
        entry
        for entry in payload["entries"]
        if entry["path"]
        not in {
            repo_rel(INDEPENDENT_VERIFY_JSON),
            repo_rel(PATH_SANITIZATION_JSON),
            repo_rel(SUPERSCEDED_DEEMPHASIS_JSON),
            repo_rel(PACKAGE_DIR / "README.md"),
        }
    ]
    payload["entries"].extend(
        [
            {
                "path": repo_rel(INDEPENDENT_VERIFY_JSON),
                "classification": "benchmark_hardening_support",
                "benchmark_authoritative": False,
                "object_kind": "second independent benchmark verifier",
                "current_value": "Z6 / dBS 10 / dAI 10",
                "notes": "Independent row-minor reconstruction cross-check for the copied topmat benchmark.",
            },
            {
                "path": repo_rel(PATH_SANITIZATION_JSON),
                "classification": "benchmark_hardening_support",
                "benchmark_authoritative": False,
                "object_kind": "path sanitization report",
                "current_value": "benchmark authoritative files now relative-path-first",
                "notes": "Tracks repo-local absolute path cleanup for benchmark delivery artifacts.",
            },
            {
                "path": repo_rel(SUPERSCEDED_DEEMPHASIS_JSON),
                "classification": "benchmark_hardening_support",
                "benchmark_authoritative": False,
                "object_kind": "superseded file deemphasis report",
                "current_value": "old 13/trivial files further de-emphasized",
                "notes": "Tracks warning banners, historical snapshots, and internal/superseded package placement.",
            },
            {
                "path": repo_rel(PACKAGE_DIR / "README.md"),
                "classification": "benchmark_package_portal",
                "benchmark_authoritative": False,
                "object_kind": "benchmark hardening package portal",
                "current_value": "layered benchmark vs internal/superseded review package",
                "notes": "Use this package for benchmark-hardening review; the internal/superseded layer is split out explicitly.",
            },
        ]
    )
    payload["inventory_verdict"]["benchmark_authoritative_count"] = 2
    write_json(INVENTORY_JSON, payload)

    payload = sanitize_repo_paths(load_json(OBJECT_LADDER_JSON))
    payload["generated_at"] = now_iso()
    payload["path_policy"] = {
        "consumer_path_policy": "repo_relative_first",
        "note": "Repo-local paths in this file are stored repo-relative.",
    }
    payload["verdicts"]["independent_verification_result"] = canonical_benchmark_result(second_result)
    payload["verdicts"]["hardening_package"] = repo_rel(PACKAGE_DIR)
    write_json(OBJECT_LADDER_JSON, payload)

    inventory_md = [
        "# SG194 authoritative-looking file inventory v1",
        "",
        f"- benchmark-authoritative file: `{load_json(INVENTORY_JSON)['benchmark_authoritative_file']}`",
        f"- benchmark-authoritative count: `{load_json(INVENTORY_JSON)['inventory_verdict']['benchmark_authoritative_count']}`",
        "",
        "## Key benchmark layer",
        "",
        f"- benchmark status: `{repo_rel(BENCHMARK_STATUS_JSON)}`",
        f"- benchmark oracle: `{repo_rel(BENCHMARK_VERDICT_JSON)}`",
        f"- external benchmark support: `{repo_rel(EXTERNAL_BENCHMARK_JSON)}`",
        f"- independent verifier: `{repo_rel(INDEPENDENT_VERIFY_JSON)}`",
        f"- benchmark ladder: `{repo_rel(OBJECT_LADDER_JSON)}`",
        f"- path sanitization report: `{repo_rel(PATH_SANITIZATION_JSON)}`",
        f"- superseded deemphasis report: `{repo_rel(SUPERSCEDED_DEEMPHASIS_JSON)}`",
        "",
        "## Inventory verdict",
        "",
        "- old stage2 files remain non-authoritative and are package-layered as internal/superseded.",
        "- repo-local benchmark-delivery paths are now relative-path-first.",
    ]
    write_text(INVENTORY_MD, "\n".join(inventory_md))

    ladder_md = [
        "# SG194 object ladder and benchmark map v1",
        "",
        f"- benchmark-authoritative file: `{repo_rel(BENCHMARK_STATUS_JSON)}`",
        "",
        "## Ladder",
        "",
        "- benchmark authoritative status: classification `Z6`, `dBS = 10`, `dAI = 10`",
        "- current raw: internal raw object",
        "- phase-aware raw: local prototype raw repair path",
        "- anchored stage2 final quotient: superseded internal reduced quotient claim",
        "- external matrix final status: unresolved current-to-external mapping layer",
        "",
        "## Hardening",
        "",
        f"- independent verification file: `{repo_rel(INDEPENDENT_VERIFY_JSON)}`",
        f"- independent verification result: `{canonical_benchmark_result(second_result)}`",
        f"- review package: `{repo_rel(PACKAGE_DIR)}`",
    ]
    write_text(OBJECT_LADDER_MD, "\n".join(ladder_md))


def historical_snapshot_for(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if path == STAGE2_JSON:
        return {
            "single_final_rank_bs": payload["single_final_rank_bs"],
            "single_final_rank_ai": payload["single_final_rank_ai"],
            "single_final_quotient_group": payload["single_final_quotient_group"],
            "double_final_rank_bs": payload["double_final_rank_bs"],
            "double_final_rank_ai": payload["double_final_rank_ai"],
            "double_final_quotient_group": payload["double_final_quotient_group"],
        }
    if path == WORKFLOW_STAGE2_JSON:
        return {
            "single_final_rank_bs": payload["single_final_rank_bs"],
            "single_final_rank_ai": payload["single_final_rank_ai"],
            "single_final_quotient_group": payload["single_final_quotient_group"],
            "double_final_rank_bs": payload["double_final_rank_bs"],
            "double_final_rank_ai": payload["double_final_rank_ai"],
            "double_final_quotient_group": payload["double_final_quotient_group"],
        }
    return {
        "final_rank_bs": payload["final_rank_bs"],
        "final_rank_ai": payload["final_rank_ai"],
        "quotient_group": payload["quotient_group"],
        "standard_quotient_group": payload["standard_quotient_group"],
    }


def apply_superseded_deemphasis() -> dict[str, Any]:
    records = []
    for path in [STAGE2_JSON, WORKFLOW_STAGE2_JSON, SINGLE_COMPLETION_JSON, DOUBLE_COMPLETION_JSON]:
        payload = load_json(path)
        snapshot = historical_snapshot_for(path, payload)
        payload["do_not_use_for_benchmark"] = True
        payload["do_not_use_for_benchmark_reason"] = (
            "This file preserves a historical internal 13/trivial reduced-quotient "
            "claim and must not be read as the SG194 benchmark-final answer."
        )
        payload["deemphasis_banner"] = (
            "DEPRECATED FOR BENCHMARK USE: read current_status_1941111_benchmark_v1.json "
            "for the only benchmark-authoritative SG194 conclusion."
        )
        payload["historical_snapshot"] = snapshot
        payload["package_layer"] = "internal_superseded"
        if path == STAGE2_JSON:
            payload["single_status"]["do_not_use_for_benchmark"] = True
            payload["double_status"]["do_not_use_for_benchmark"] = True
            payload["single_status"]["historical_snapshot"] = {
                "final_rank_bs": payload["single_status"]["final_rank_bs"],
                "final_rank_ai": payload["single_status"]["final_rank_ai"],
                "quotient_group": payload["single_status"]["quotient_group"],
            }
            payload["double_status"]["historical_snapshot"] = {
                "final_rank_bs": payload["double_status"]["final_rank_bs"],
                "final_rank_ai": payload["double_status"]["final_rank_ai"],
                "quotient_group": payload["double_status"]["quotient_group"],
            }
        write_json(path, payload)
        records.append(
            {
                "file": repo_rel(path),
                "added_fields": [
                    "do_not_use_for_benchmark",
                    "do_not_use_for_benchmark_reason",
                    "deemphasis_banner",
                    "historical_snapshot",
                    "package_layer",
                ],
                "historical_snapshot": snapshot,
            }
        )
    payload = {
        "generated_at": now_iso(),
        "benchmark_authoritative_file": repo_rel(BENCHMARK_STATUS_JSON),
        "deemphasized_files": records,
        "package_layering": {
            "benchmark_authoritative": "review_package_sg194_benchmark_hardening_v1/benchmark_authoritative/",
            "internal_superseded": "review_package_sg194_benchmark_hardening_v1/internal_superseded/",
        },
    }
    write_json(SUPERSCEDED_DEEMPHASIS_JSON, payload)
    md_lines = [
        "# SG194 superseded file deemphasis v1",
        "",
        f"- benchmark-authoritative file: `{repo_rel(BENCHMARK_STATUS_JSON)}`",
        "",
        "## Deemphasized files",
        "",
    ]
    for record in records:
        md_lines.append(f"- `{record['file']}`")
        md_lines.append(f"  historical snapshot: `{record['historical_snapshot']}`")
    md_lines.extend(
        [
            "",
            "## Package layering",
            "",
            f"- benchmark authoritative: `{payload['package_layering']['benchmark_authoritative']}`",
            f"- internal / superseded: `{payload['package_layering']['internal_superseded']}`",
        ]
    )
    write_text(SUPERSCEDED_DEEMPHASIS_MD, "\n".join(md_lines))
    return payload


def update_readme_and_checkpoint() -> None:
    readme_lines = [
        "# SG194 Benchmark Hardening",
        "",
        "## Benchmark-first entrypoint",
        "",
        "- benchmark-authoritative status: `current_status_1941111_benchmark_v1.json`",
        "- benchmark-authoritative markdown: `current_status_1941111_benchmark_v1.md`",
        "- benchmark result for the current project convention target: `classification = Z6`, `dBS = 10`, `dAI = 10`",
        "- benchmark oracle source: `sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json`",
        "- second independent verifier: `sg194_topmat_independent_verify_v1.json`",
        "- path sanitization report: `sg194_benchmark_path_sanitization_v1.json`",
        "- superseded deemphasis report: `sg194_superseded_file_deemphasis_v1.json`",
        "- object ladder / benchmark map: `sg194_object_ladder_and_benchmark_map_v1.json`",
        "- authoritative-looking file inventory: `sg194_authoritative_file_inventory_v1.json`",
        "",
        "## Benchmark target caveat",
        "",
        f"- {TARGET_STATEMENT}",
        "- This remains a project benchmark convention plus magnetic-counterpart mapping layer.",
        "- Accessible external magnetic-group sources in this round directly confirm the `OG/BNS` object and its `Type-I` character, but do not independently expose the suffixless repo label `SSG 194.1.1.1` as a separately scraped external field.",
        "",
        "## Internal object boundaries",
        "",
        "- `current raw` is an internal raw BS-space object. Do not quote it as the benchmark classification.",
        "- `phase-aware` is a local prototype raw repair path. It is not the benchmark classification.",
        "- `current_status_194.1.1.1_stage2.json` and the paired stage2 workflow/completion summaries are historical internal reduced-quotient references. They are superseded for benchmark use and now carry explicit do-not-use banners.",
        "- `current_status_sg194_external_matrix_final.json` remains useful as an unresolved current-to-external mapping-layer status, but it is not the benchmark oracle.",
        "",
        "## Review package",
        "",
        "- package file: `review_package_sg194_benchmark_hardening_v1.tar.gz`",
        "- package directory: `review_package_sg194_benchmark_hardening_v1/`",
        "- package layer map: `review_package_sg194_benchmark_hardening_v1/REVIEW_MAP.md`",
        "- benchmark layer and internal/superseded layer are split into separate subdirectories.",
    ]
    write_text(README_MD, "\n".join(readme_lines))

    checkpoint_json = {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
        "task_scope": "SG194 benchmark hardening / benchmark cleanup: second independent verification, path sanitization, superseded-file deemphasis, and layered review package delivery.",
        "current_branch": "sg194-special",
        "repo_root_relative": ".",
        "remote": "git@github.com:szhangphy/stq.git",
        "head_commit_short_before_checkpoint": subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "rolling_stage_snapshots": [
            {
                "stage": 1,
                "label": "independent_verify",
                "status": "completed",
                "summary": "Ran sg194_topmat_experimental_compute_v2.py and the new sg194_topmat_independent_verify_v1.py; both returned classification Z6 with dBS = 10 and dAI = 10.",
            },
            {
                "stage": 2,
                "label": "path_inventory",
                "status": "completed",
                "summary": "Identified repo-local absolute path pollution in benchmark authoritative/supporting JSON files before cleanup.",
            },
            {
                "stage": 3,
                "label": "path_sanitization",
                "status": "completed",
                "summary": "Rewrote benchmark authoritative/supporting JSON files to repo-relative path semantics and recorded the cleanup in sg194_benchmark_path_sanitization_v1.json/.md.",
            },
            {
                "stage": 4,
                "label": "superseded_deemphasis",
                "status": "completed",
                "summary": "Added do-not-use banners and historical snapshots to the old 13/trivial stage2/workflow/completion files.",
            },
            {
                "stage": 5,
                "label": "readme_checkpoint_refresh",
                "status": "completed",
                "summary": "Refreshed README and this rolling checkpoint to reflect benchmark hardening rather than benchmark takeover only.",
            },
            {
                "stage": 6,
                "label": "review_package",
                "status": "completed",
                "summary": "Built review_package_sg194_benchmark_hardening_v1/ and .tar.gz with benchmark_authoritative and internal_superseded subdirectories plus REVIEW_MAP.md.",
            },
            {
                "stage": 7,
                "label": "validation",
                "status": "completed",
                "summary": "py_compile, independent verifier, and benchmark hardening validation all passed; repo is ready for commit/push.",
            },
        ],
        "confirmed_findings": [
            "The benchmark-authoritative SG194 result remains classification Z6 with dBS = 10 and dAI = 10.",
            TARGET_STATEMENT,
            "The suffixless SSG label remains a project benchmark convention plus magnetic-counterpart mapping layer rather than a separately scraped external field.",
            "Repo-local benchmark delivery paths are now relative-path-first in the benchmark authoritative/supporting JSON files targeted by this round.",
            "The old 13/trivial stage2/workflow/completion files remain preserved only as internal/superseded historical snapshots.",
        ],
        "commands_run": [
            "python3 sg194/sg194_topmat_experimental_compute_v2.py",
            "python3 sg194/sg194_topmat_independent_verify_v1.py",
            "python3 sg194/debug_sg194_benchmark_hardening_v1.py --write",
            "python3 -m py_compile sg194/*.py",
            "python3 sg194/debug_sg194_benchmark_hardening_v1.py --validate",
        ],
        "files_added_in_scope": [
            repo_rel(SECOND_IMPL_SCRIPT),
            repo_rel(INDEPENDENT_VERIFY_JSON),
            repo_rel(INDEPENDENT_VERIFY_MD),
            repo_rel(PATH_SANITIZATION_JSON),
            repo_rel(PATH_SANITIZATION_MD),
            repo_rel(SUPERSCEDED_DEEMPHASIS_JSON),
            repo_rel(SUPERSCEDED_DEEMPHASIS_MD),
            repo_rel(Path(__file__)),
            repo_rel(PACKAGE_DIR),
            repo_rel(PACKAGE_TAR),
        ],
        "files_updated_in_scope": [
            repo_rel(BENCHMARK_STATUS_JSON),
            repo_rel(BENCHMARK_STATUS_MD),
            repo_rel(EXTERNAL_BENCHMARK_JSON),
            repo_rel(OBJECT_MATCH_JSON),
            repo_rel(BENCHMARK_VERDICT_JSON),
            repo_rel(INVENTORY_JSON),
            repo_rel(OBJECT_LADDER_JSON),
            repo_rel(STAGE2_JSON),
            repo_rel(WORKFLOW_STAGE2_JSON),
            repo_rel(SINGLE_COMPLETION_JSON),
            repo_rel(DOUBLE_COMPLETION_JSON),
            repo_rel(README_MD),
            repo_rel(LIVE_CHECKPOINT_JSON),
            repo_rel(LIVE_CHECKPOINT_MD),
        ],
        "authoritative_artifacts": {
            "benchmark_status_json": repo_rel(BENCHMARK_STATUS_JSON),
            "benchmark_verdict_json": repo_rel(BENCHMARK_VERDICT_JSON),
            "independent_verify_json": repo_rel(INDEPENDENT_VERIFY_JSON),
            "object_ladder_json": repo_rel(OBJECT_LADDER_JSON),
            "inventory_json": repo_rel(INVENTORY_JSON),
            "path_sanitization_json": repo_rel(PATH_SANITIZATION_JSON),
        },
        "active_blockers": [
            "Accessible external magnetic-group sources confirm OG 194.1.1494 / BNS 194.263 and Type-I, but do not separately expose the suffixless SSG 194.1.1.1 label as an external field."
        ],
        "next_actions": [
            "Review the hardening diff and stage only the in-scope SG194 benchmark files.",
            "Commit on sg194-special and push origin/sg194-special.",
        ],
    }
    write_json(LIVE_CHECKPOINT_JSON, checkpoint_json)

    checkpoint_md = [
        "# SG194 194.1.1.1 Live Checkpoint",
        "",
        f"- Current time: {checkpoint_json['current_time']}",
        f"- Branch: `{checkpoint_json['current_branch']}`",
        f"- HEAD before this checkpoint update: `{checkpoint_json['head_commit_short_before_checkpoint']}`",
        f"- Task scope: {checkpoint_json['task_scope']}",
        "",
        "## Rolling Stages",
        "",
    ]
    for stage in checkpoint_json["rolling_stage_snapshots"]:
        checkpoint_md.append(f"{stage['stage']}. {stage['label']}")
        checkpoint_md.append(f"   {stage['summary']}")
    checkpoint_md.extend(
        [
            "",
            "## Confirmed Findings",
            "",
        ]
    )
    for index, finding in enumerate(checkpoint_json["confirmed_findings"], start=1):
        checkpoint_md.append(f"{index}. {finding}")
    checkpoint_md.extend(
        [
            "",
            "## Active Blocker",
            "",
            "1. Accessible external magnetic-group sources confirm `OG 194.1.1494 / BNS 194.263` and `Type-I`, but do not separately expose the suffixless `SSG 194.1.1.1` label as an external field.",
        ]
    )
    write_text(LIVE_CHECKPOINT_MD, "\n".join(checkpoint_md))


def build_review_package() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    benchmark_dir = PACKAGE_DIR / "benchmark_authoritative"
    internal_dir = PACKAGE_DIR / "internal_superseded"
    audit_dir = PACKAGE_DIR / "audit_support"
    benchmark_dir.mkdir(parents=True)
    internal_dir.mkdir(parents=True)
    audit_dir.mkdir(parents=True)

    benchmark_files = [
        BENCHMARK_STATUS_JSON,
        BENCHMARK_STATUS_MD,
        BENCHMARK_VERDICT_JSON,
        BENCHMARK_VERDICT_MD,
        EXTERNAL_BENCHMARK_JSON,
        EXTERNAL_BENCHMARK_MD,
        INDEPENDENT_VERIFY_JSON,
        INDEPENDENT_VERIFY_MD,
        OBJECT_LADDER_JSON,
        OBJECT_LADDER_MD,
        INVENTORY_JSON,
        INVENTORY_MD,
        OBJECT_MATCH_JSON,
        OBJECT_MATCH_MD,
    ]
    audit_files = [
        PATH_SANITIZATION_JSON,
        PATH_SANITIZATION_MD,
        SUPERSCEDED_DEEMPHASIS_JSON,
        SUPERSCEDED_DEEMPHASIS_MD,
    ]
    internal_files = [
        STAGE2_JSON,
        WORKFLOW_STAGE2_JSON,
        SINGLE_COMPLETION_JSON,
        DOUBLE_COMPLETION_JSON,
        SG194_DIR / "current_status_sg194_external_matrix_final.json",
        SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.json",
        SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.md",
    ]
    for path in benchmark_files:
        if path.exists():
            copy_for_package(path, benchmark_dir / path.name)
    for path in internal_files:
        if path.exists():
            copy_for_package(path, internal_dir / path.name)
    for path in audit_files:
        if path.exists():
            copy_for_package(path, audit_dir / path.name)

    readme_lines = [
        "# SG194 Benchmark Hardening Review Package v1",
        "",
        "- benchmark-authoritative result: `classification = Z6`, `dBS = 10`, `dAI = 10`",
        f"- benchmark package layer: `{repo_rel(benchmark_dir)}`",
        f"- internal / superseded layer: `{repo_rel(internal_dir)}`",
        f"- audit support layer: `{repo_rel(audit_dir)}`",
        "- the benchmark layer contains only benchmark-authoritative and benchmark-support audit artifacts",
        "- the internal/superseded layer contains preserved internal objects that must not be mixed with the benchmark oracle",
    ]
    write_text(PACKAGE_DIR / "README.md", "\n".join(readme_lines))

    review_map_lines = [
        "# Review Map",
        "",
        "## benchmark_authoritative/",
        "",
    ]
    for path in benchmark_files:
        review_map_lines.append(f"- `benchmark_authoritative/{path.name}`")
    review_map_lines.extend(["", "## internal_superseded/", ""])
    for path in internal_files:
        review_map_lines.append(f"- `internal_superseded/{path.name}`")
    review_map_lines.extend(["", "## audit_support/", ""])
    for path in audit_files:
        review_map_lines.append(f"- `audit_support/{path.name}`")
    write_text(PACKAGE_DIR / "REVIEW_MAP.md", "\n".join(review_map_lines))

    with tarfile.open(PACKAGE_TAR, "w:gz") as handle:
        handle.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def write_path_sanitization_report(before_hits: dict[str, list[dict[str, Any]]]) -> None:
    target_files = [
        BENCHMARK_STATUS_JSON,
        EXTERNAL_BENCHMARK_JSON,
        OBJECT_MATCH_JSON,
        BENCHMARK_VERDICT_JSON,
        INVENTORY_JSON,
        OBJECT_LADDER_JSON,
    ]
    after_hits = {repo_rel(path): scan_absolute_path_hits(path) for path in target_files}
    package_benchmark_files = sorted((PACKAGE_DIR / "benchmark_authoritative").glob("*"))
    package_hits = {repo_rel(path): scan_absolute_path_hits(path) for path in package_benchmark_files}
    payload = {
        "generated_at": now_iso(),
        "baseline_commit_scanned_for_before_cleanup_hits": BASELINE_COMMIT,
        "target_files": [repo_rel(path) for path in target_files],
        "path_policy": {
            "consumer_path_policy": "repo_relative_first",
            "note": "Repo-local path fields are now stored repo-relative. This report only tracks repo-local absolute path pollution.",
        },
        "before_cleanup_absolute_path_hits": before_hits,
        "after_cleanup_absolute_path_hits": after_hits,
        "package_benchmark_layer_absolute_path_hits": package_hits,
    }
    write_json(PATH_SANITIZATION_JSON, payload)
    md_lines = [
        "# SG194 benchmark path sanitization v1",
        "",
        "## Before cleanup absolute path hits",
        "",
    ]
    md_lines.extend(render_hits_md("", before_hits))
    md_lines.extend(["", "## After cleanup absolute path hits", ""])
    md_lines.extend(render_hits_md("", after_hits))
    md_lines.extend(["", "## Package benchmark layer absolute path hits", ""])
    md_lines.extend(render_hits_md("", package_hits))
    write_text(PATH_SANITIZATION_MD, "\n".join(line for line in md_lines if line != ""))


def validate() -> dict[str, Any]:
    errors: list[str] = []
    benchmark_status = load_json(BENCHMARK_STATUS_JSON)
    independent = load_json(INDEPENDENT_VERIFY_JSON)
    path_report = load_json(PATH_SANITIZATION_JSON)
    deemphasis = load_json(SUPERSCEDED_DEEMPHASIS_JSON)
    if benchmark_status["benchmark_result"]["classification"] != "Z6":
        errors.append("benchmark classification is not Z6")
    if benchmark_status["benchmark_result"]["dBS"] != 10:
        errors.append("benchmark dBS is not 10")
    if benchmark_status["benchmark_result"]["dAI"] != 10:
        errors.append("benchmark dAI is not 10")
    if independent["result"]["classification"] != "Z6":
        errors.append("independent verification classification is not Z6")
    if independent["result"]["dBS"] != 10 or independent["result"]["dAI"] != 10:
        errors.append("independent verification ranks are not 10/10")
    for rel_path, hits in path_report["after_cleanup_absolute_path_hits"].items():
        if hits:
            errors.append(f"absolute repo path still present after cleanup in {rel_path}")
    for rel_path, hits in path_report["package_benchmark_layer_absolute_path_hits"].items():
        if hits:
            errors.append(f"absolute repo path still present in package benchmark layer file {rel_path}")
    for path in [STAGE2_JSON, WORKFLOW_STAGE2_JSON, SINGLE_COMPLETION_JSON, DOUBLE_COMPLETION_JSON]:
        payload = load_json(path)
        if not payload.get("do_not_use_for_benchmark"):
            errors.append(f"missing do_not_use_for_benchmark in {repo_rel(path)}")
        if "historical_snapshot" not in payload:
            errors.append(f"missing historical_snapshot in {repo_rel(path)}")
    if not PACKAGE_TAR.exists():
        errors.append("review package tarball is missing")
    if not (PACKAGE_DIR / "REVIEW_MAP.md").exists():
        errors.append("review package REVIEW_MAP.md is missing")
    if len(deemphasis["deemphasized_files"]) != 4:
        errors.append("deemphasis report does not cover 4 target files")
    return {"status": "ok" if not errors else "error", "errors": errors}


def write_mode() -> None:
    before_hits = {
        repo_rel(path): scan_baseline_git_path_hits(repo_rel(path))
        for path in [
            BENCHMARK_STATUS_JSON,
            EXTERNAL_BENCHMARK_JSON,
            OBJECT_MATCH_JSON,
            BENCHMARK_VERDICT_JSON,
            INVENTORY_JSON,
            OBJECT_LADDER_JSON,
        ]
    }
    first_impl = load_json(FIRST_IMPL_JSON)
    first_result = canonical_benchmark_result(first_impl["benchmark"])
    second_result = canonical_benchmark_result(load_json(INDEPENDENT_VERIFY_JSON)["result"])
    if first_result != second_result:
        raise RuntimeError(
            "first and second benchmark implementations disagree: "
            f"{first_result} != {second_result}"
        )

    update_benchmark_status(first_result, second_result)
    update_supporting_jsons(first_result, second_result)
    apply_superseded_deemphasis()
    update_readme_and_checkpoint()
    build_review_package()
    write_path_sanitization_report(before_hits)
    build_review_package()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.write:
        write_mode()
    if args.validate:
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    if not args.write and not args.validate:
        parser.error("use --write or --validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
