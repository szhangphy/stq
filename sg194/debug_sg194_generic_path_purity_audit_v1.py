#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.utils import now_iso, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
CORE_GENERIC_FILES = [
    "sg194/pipeline_v2/generic_builders.py",
    "sg194/pipeline_v2/geometry.py",
    "sg194/pipeline_v2/alignment.py",
    "sg194/pipeline_v2/bs_ai.py",
    "sg194/pipeline_v2/quotient.py",
    "sg194/pipeline_v2/checks.py",
    "sg194/pipeline_v2/driver.py",
    "sg194/pipeline_v2/specs.py",
    "sg194/pipeline_v2/adapters/ssg222_1_1_1.py",
]
BANNED_TOKENS = [
    "debug_workflow_portability_194.1.1.1.py",
    "debug_sg194_nonabelian_local_library.py",
    "oracle_backed_final",
    "legacy_bridge",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    hits: list[dict[str, Any]] = []
    for relpath in CORE_GENERIC_FILES:
        text = (REPO_ROOT / relpath).read_text()
        bad = [token for token in BANNED_TOKENS if token in text]
        hits.append({"path": relpath, "banned_hits": bad})

    regression = load_json(SG194_DIR / "sg194_194_generic_regression_v1.json") if (SG194_DIR / "sg194_194_generic_regression_v1.json").exists() else {}
    summary_222 = load_json(SG194_DIR / "sg194_222_generic_final_classification_summary_v1.json") if (SG194_DIR / "sg194_222_generic_final_classification_summary_v1.json").exists() else {}
    dropped_222 = load_json(SG194_DIR / "sg194_dropped_ai_candidates_v3.json") if (SG194_DIR / "sg194_dropped_ai_candidates_v3.json").exists() else {}

    single_222_bad = dropped_222.get("single", {}).get("ai_incompatible_candidates", [])
    double_222_bad = dropped_222.get("double", {}).get("ai_incompatible_candidates", [])
    single_222_families = sorted({item.get("family_letter") for item in single_222_bad if item.get("family_letter")})
    double_222_families = sorted({item.get("family_letter") for item in double_222_bad if item.get("family_letter")})

    purity = {
        "generated_at": now_iso(),
        "core_generic_files": hits,
        "backend_free_generic_path": all(not item["banned_hits"] for item in hits),
        "removed_dependencies": [
            "sg194/debug_workflow_portability_194.1.1.1.py",
            "sg194/debug_sg194_nonabelian_local_library.py",
            "oracle_backed_222_final_slots",
            "driver_level_legacy_bridge_dependency_for_generic_specs",
        ],
        "remaining_generic_runtime_modules": [
            "sg194/pipeline_v2/runtime_backend_free.py",
            "sg194/pipeline_v2/runtime_bridge.py",
            "sg194/pipeline_v2/runtime_group_ops.py",
            "sg194/pipeline_v2/local_irreps.py",
        ],
    }

    generality = {
        "generated_at": now_iso(),
        "truly_general": bool(
            purity["backend_free_generic_path"]
            and regression.get("matches_accepted_special", {}).get("single")
            and regression.get("matches_accepted_special", {}).get("double")
            and summary_222.get("single", {}).get("verification_status") not in {None, "failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient"}
            and summary_222.get("double", {}).get("verification_status") not in {None, "failed_due_to_rejected_or_unembedded_ai_candidates_before_final_quotient"}
        ),
        "backend_free_generic_path": purity["backend_free_generic_path"],
        "truly_generic_modules": [
            "sg194/pipeline_v2/generic_builders.py",
            "sg194/pipeline_v2/geometry.py",
            "sg194/pipeline_v2/alignment.py",
            "sg194/pipeline_v2/bs_ai.py",
            "sg194/pipeline_v2/quotient.py",
            "sg194/pipeline_v2/checks.py",
            "sg194/pipeline_v2/driver.py",
            "sg194/pipeline_v2/artifact_io.py",
            "sg194/pipeline_v2/adapters/ssg222_1_1_1.py",
        ],
        "still_fake_generic_modules": [
            "sg194/pipeline_v2/runtime_backend_free.py",
            "sg194/pipeline_v2/runtime_bridge.py",
            "sg194/pipeline_v2/runtime_group_ops.py",
            "sg194/pipeline_v2/local_irreps.py",
            "sg194/pipeline_v2/adapters/sg194.py",
            "sg194/pipeline_v2/specs.py::SG194_SPEC",
        ],
        "remaining_case_specific_modules": [
            "sg194/pipeline_v2/adapters/sg194.py",
            "sg194/pipeline_v2/specs.py::SG194_SPEC",
        ],
        "case_by_case_blockers": [
            {
                "group": "194.1.1.1",
                "mode": "single",
                "status": regression.get("blockers", [{}])[0].get("blocker"),
            },
            {
                "group": "194.1.1.1",
                "mode": "double",
                "status": regression.get("blockers", [{}, {}])[1].get("blocker"),
            },
            {
                "group": "222.1.1.1 / 222.1.1601(OG)",
                "mode": "single",
                "status": (
                    "native_result_provisional_due_to_rejected_ai_candidates_in_families_"
                    + "_".join(single_222_families)
                    if single_222_bad
                    else summary_222.get("single", {}).get("verification_status")
                ),
            },
            {
                "group": "222.1.1.1 / 222.1.1601(OG)",
                "mode": "double",
                "status": (
                    "native_result_provisional_due_to_rejected_ai_candidates_in_families_"
                    + "_".join(double_222_families)
                    if double_222_bad
                    else summary_222.get("double", {}).get("verification_status")
                ),
            },
        ],
    }

    dependency_cut = {
        "generated_at": now_iso(),
        "cut_status": {
            "generic_builders_to_special_backend": True,
            "generic_driver_to_legacy_bridge_for_generic_specs": True,
            "oracle_override_into_native_final_slots": True,
        },
        "remaining_reference_only_dependencies": [
            "sg194/current_status_194.1.1.1_stage2.json",
            "sg194/sg194_topmat_oracle_from_copy_v1.json",
        ],
    }

    case_by_case = {
        "generated_at": now_iso(),
        "map": generality["case_by_case_blockers"],
    }

    write_json(SG194_DIR / "sg194_generic_path_purity_audit_v1.json", purity)
    write_json(SG194_DIR / "sg194_backend_dependency_cut_v1.json", dependency_cut)
    write_json(SG194_DIR / "sg194_generality_verdict_v3.json", generality)
    write_json(SG194_DIR / "sg194_case_by_case_map_v3.json", case_by_case)

    write_text(
        SG194_DIR / "sg194_generic_path_purity_audit_v1.md",
        "\n".join(
            [
                "# Generic Path Purity Audit v1",
                "",
                f"- backend-free generic path: `{purity['backend_free_generic_path']}`",
                *[
                    f"- `{item['path']}` banned hits: `{item['banned_hits']}`"
                    for item in hits
                ],
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_backend_dependency_cut_v1.md",
        "\n".join(
            [
                "# Backend Dependency Cut v1",
                "",
                *[
                    f"- `{key}`: `{value}`"
                    for key, value in dependency_cut["cut_status"].items()
                ],
                "",
                *[
                    f"- reference-only: `{item}`"
                    for item in dependency_cut["remaining_reference_only_dependencies"]
                ],
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_generality_verdict_v3.md",
        "\n".join(
            [
                "# Generality Verdict v3",
                "",
                f"- truly general: `{generality['truly_general']}`",
                f"- backend-free generic path: `{generality['backend_free_generic_path']}`",
                f"- truly generic modules: `{generality['truly_generic_modules']}`",
                f"- still fake-generic modules: `{generality['still_fake_generic_modules']}`",
                f"- remaining case-specific modules: `{generality['remaining_case_specific_modules']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_case_by_case_map_v3.md",
        "\n".join(
            [
                "# Case By Case Map v3",
                "",
                *[
                    f"- `{item['group']}` / `{item['mode']}`: `{item['status']}`"
                    for item in case_by_case["map"]
                ],
            ]
        ),
    )

    if args.validate and not purity["backend_free_generic_path"]:
        raise SystemExit("generic path purity audit still found banned special-backend tokens in core files")


if __name__ == "__main__":
    main()
