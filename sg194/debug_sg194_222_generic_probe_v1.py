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

from sg194.pipeline_v2.generic_builders import generic_mode_bundle, generic_result_objects
from sg194.pipeline_v2.utils import now_iso, write_json, write_text


SG194_DIR = REPO_ROOT / "sg194"
GROUP = "222.1.1.1"
OG_OBJECT = "222.1.1601"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def mode_payload(mode: str) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = generic_mode_bundle(GROUP, mode)
    record = next(
        item
        for item in generic_result_objects(GROUP)
        if item["object_id"] == f"{mode}_target_direct"
    )
    dropped = {
        "mode": mode,
        "ai_incompatible_candidates": bundle["quotient"]["ai_incompatible_candidates"],
        "ai_embedding_failures": bundle["quotient"]["ai_embedding_failures"],
        "ai_incompatible_count": bundle["quotient"]["ai_incompatible_count"],
        "ai_embedding_failure_count": bundle["quotient"]["ai_embedding_failure_count"],
        "incompatible_family_letters": sorted(
            {
                item.get("family_letter")
                for item in bundle["quotient"]["ai_incompatible_candidates"]
                if item.get("family_letter")
            }
        ),
    }
    payload = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "mode": mode,
        "backend_free_generic_path": True,
        "dBS": record.get("dBS"),
        "dAI": record.get("dAI"),
        "classification": record.get("classification"),
        "free_rank": record.get("free_rank"),
        "finite_part": record.get("finite_part"),
        "availability": record.get("availability"),
        "verification_status": record.get("verification_status"),
        "ai_candidate_count": record.get("ai_candidate_count"),
        "ai_candidate_count_used": record.get("ai_candidate_count_used"),
        "ai_incompatible_count": record.get("ai_incompatible_count"),
        "ai_embedding_failure_count": record.get("ai_embedding_failure_count"),
        "source_files": record.get("source_files", []),
    }
    return payload, dropped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    oracle = load_json(SG194_DIR / "sg194_topmat_oracle_from_copy_v1.json")
    identity_map = load_json(SG194_DIR / "sg194_222_og1601_identity_map_v1.json")

    single, single_dropped = mode_payload("single")
    double, double_dropped = mode_payload("double")
    dropped = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "single": single_dropped,
        "double": double_dropped,
    }
    ai_fix = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "silent_drop_removed": True,
        "native_final_uses_oracle_override": False,
        "root_cause": (
            "The old fake-generic path silently reported final quotient data after rejecting AI "
            "candidates. The backend-free path now records every rejected or unembedded candidate "
            "explicitly and keeps native final verification provisional when rejections remain."
        ),
        "remaining_blocker": {
            "single_incompatible_family_letters": single_dropped["incompatible_family_letters"],
            "double_incompatible_family_letters": double_dropped["incompatible_family_letters"],
            "note": (
                "The silent-drop bug is fixed, but the native backend-free path still rejects a/b/g-family "
                "AI candidates on the current compatibility matrix, so the native final object remains provisional."
            ),
        },
        "single": single,
        "double": double,
    }
    quotient_fix = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "quotient_policy": "native_target_point_shell_embedding_without_silent_drop",
        "single": {
            "dBS": single["dBS"],
            "dAI": single["dAI"],
            "classification": single["classification"],
            "ai_incompatible_count": single["ai_incompatible_count"],
            "ai_embedding_failure_count": single["ai_embedding_failure_count"],
            "verification_status": single["verification_status"],
        },
        "double": {
            "dBS": double["dBS"],
            "dAI": double["dAI"],
            "classification": double["classification"],
            "ai_incompatible_count": double["ai_incompatible_count"],
            "ai_embedding_failure_count": double["ai_embedding_failure_count"],
            "verification_status": double["verification_status"],
        },
    }
    summary = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "single": single,
        "double": double,
        "same_native_generic_result": (
            single["dBS"] == double["dBS"]
            and single["dAI"] == double["dAI"]
            and single["classification"] == double["classification"]
        ),
        "identity_map": identity_map,
    }
    oracle_compare = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "identity_map": identity_map,
        "oracle": {
            "dBS": oracle["dBS"],
            "dAI": oracle["dAI"],
            "classification": oracle["classification"],
            "free_rank": oracle["free_rank"],
            "finite_part": oracle["finite_part"],
        },
        "single_generic": {
            "dBS": single["dBS"],
            "dAI": single["dAI"],
            "classification": single["classification"],
            "verification_status": single["verification_status"],
        },
        "double_generic": {
            "dBS": double["dBS"],
            "dAI": double["dAI"],
            "classification": double["classification"],
            "verification_status": double["verification_status"],
        },
        "oracle_override_used": False,
        "matches_oracle": {
            "single": all(single.get(key) == oracle[key] for key in ("dBS", "dAI", "classification")),
            "double": all(double.get(key) == oracle[key] for key in ("dBS", "dAI", "classification")),
        },
    }

    write_json(SG194_DIR / "sg194_ai_filter_bug_fix_v2.json", ai_fix)
    write_json(SG194_DIR / "sg194_dropped_ai_candidates_v3.json", dropped)
    write_json(SG194_DIR / "sg194_native_ai_over_bs_quotient_fix_v2.json", quotient_fix)
    write_json(SG194_DIR / "sg194_222_single_generic_final_result_v1.json", single)
    write_json(SG194_DIR / "sg194_222_double_generic_final_result_v1.json", double)
    write_json(SG194_DIR / "sg194_222_generic_final_classification_summary_v1.json", summary)
    write_json(SG194_DIR / "sg194_222_generic_vs_topmat_oracle_v1.json", oracle_compare)

    write_text(
        SG194_DIR / "sg194_ai_filter_bug_fix_v2.md",
        "\n".join(
            [
                "# 222 AI Filter Bug Fix v2",
                "",
                f"- silent drop removed: `{ai_fix['silent_drop_removed']}`",
                f"- native final uses oracle override: `{ai_fix['native_final_uses_oracle_override']}`",
                f"- root cause: `{ai_fix['root_cause']}`",
                f"- remaining blocker: `{ai_fix['remaining_blocker']}`",
                f"- single: `{single['dBS']}/{single['dAI']}/{single['classification']}` status=`{single['verification_status']}`",
                f"- double: `{double['dBS']}/{double['dAI']}/{double['classification']}` status=`{double['verification_status']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_dropped_ai_candidates_v3.md",
        "\n".join(
            [
                "# Dropped AI Candidates v3",
                "",
                f"- single incompatible count: `{single_dropped['ai_incompatible_count']}`",
                f"- single incompatible families: `{single_dropped['incompatible_family_letters']}`",
                f"- single embedding failure count: `{single_dropped['ai_embedding_failure_count']}`",
                f"- double incompatible count: `{double_dropped['ai_incompatible_count']}`",
                f"- double incompatible families: `{double_dropped['incompatible_family_letters']}`",
                f"- double embedding failure count: `{double_dropped['ai_embedding_failure_count']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_native_ai_over_bs_quotient_fix_v2.md",
        "\n".join(
            [
                "# Native AI Over BS Quotient Fix v2",
                "",
                f"- policy: `{quotient_fix['quotient_policy']}`",
                f"- single: `{quotient_fix['single']}`",
                f"- double: `{quotient_fix['double']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_single_generic_final_result_v1.md",
        "\n".join(
            [
                "# 222 Single Generic Final Result v1",
                "",
                f"- backend-free generic path: `{single['backend_free_generic_path']}`",
                f"- dBS/dAI/classification: `{single['dBS']}/{single['dAI']}/{single['classification']}`",
                f"- availability: `{single['availability']}`",
                f"- verification status: `{single['verification_status']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_double_generic_final_result_v1.md",
        "\n".join(
            [
                "# 222 Double Generic Final Result v1",
                "",
                f"- backend-free generic path: `{double['backend_free_generic_path']}`",
                f"- dBS/dAI/classification: `{double['dBS']}/{double['dAI']}/{double['classification']}`",
                f"- availability: `{double['availability']}`",
                f"- verification status: `{double['verification_status']}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_generic_final_classification_summary_v1.md",
        "\n".join(
            [
                "# 222 Generic Final Classification Summary v1",
                "",
                f"- identity map: `{identity_map}`",
                f"- single: `{single}`",
                f"- double: `{double}`",
            ]
        ),
    )
    write_text(
        SG194_DIR / "sg194_222_generic_vs_topmat_oracle_v1.md",
        "\n".join(
            [
                "# 222 Generic vs Topmat Oracle v1",
                "",
                f"- oracle: `{oracle_compare['oracle']}`",
                f"- single generic: `{oracle_compare['single_generic']}`",
                f"- double generic: `{oracle_compare['double_generic']}`",
                f"- matches oracle: `{oracle_compare['matches_oracle']}`",
                f"- oracle override used: `{oracle_compare['oracle_override_used']}`",
            ]
        ),
    )

    if args.validate:
        if single["dBS"] is None or double["dBS"] is None:
            raise SystemExit("222 generic probe did not produce concrete native generic results")


if __name__ == "__main__":
    main()
