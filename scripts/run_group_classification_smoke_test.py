#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.driver import run_pipeline
from sg194.pipeline_v2.group_target_registry import get_group_target_spec
from sg194.pipeline_v2.models import PipelineRunConfig


def _pick_target_object(summary: dict[str, Any], mode: str) -> dict[str, Any]:
    for item in summary["objects"]:
        if item.get("mode") == mode and item.get("row_language_level") == "target":
            return item
    raise ValueError(f"missing target object for mode={mode}")


def _coalesce_target_value(
    final_status: dict[str, Any],
    records: list[dict[str, Any]],
    field: str,
) -> Any:
    if field in final_status and final_status[field] is not None:
        return final_status[field]
    values = {
        item.get(field)
        for item in records
        if item.get("row_language_level") == "target"
    }
    values.discard(None)
    if not values:
        return None
    if len(values) == 1:
        return next(iter(values))
    return sorted(values)


def build_report(target_group: str, result: dict[str, Any]) -> dict[str, Any]:
    target_spec = get_group_target_spec(target_group)
    final_status = result["final_status"]
    alignment = result["alignment"]
    bs_summary = result["bs_summary"]
    ai_summary = result["ai_summary"]
    quotient_summary = result["quotient_summary"]
    target_bs_objects = [
        item for item in bs_summary["objects"] if item.get("row_language_level") == "target"
    ]
    single_bs = _pick_target_object(bs_summary, "single")
    double_bs = _pick_target_object(bs_summary, "double")
    single_ai = _pick_target_object(ai_summary, "single")
    double_ai = _pick_target_object(ai_summary, "double")
    single_quotient = _pick_target_object(quotient_summary, "single")
    double_quotient = _pick_target_object(quotient_summary, "double")
    single_alignment_target = alignment.get("single", {}).get("target", {})
    double_alignment_target = alignment.get("double", {}).get("target", {})
    minimal_blocker = single_bs.get("blocker") or double_bs.get("blocker")
    blocker_evidence = (
        single_bs.get("blocker_evidence")
        or double_bs.get("blocker_evidence")
        or single_alignment_target.get("blocker_evidence")
        or double_alignment_target.get("blocker_evidence")
    )
    return {
        "target_group": target_group,
        "group_target_registry_note": target_spec.note,
        "truth_compare_available": bool(
            final_status.get("truth_compare_available")
            if final_status.get("truth_compare_available") is not None
            else target_spec.truth_compare_available
        ),
        "benchmark_oracle_available": bool(
            final_status.get("benchmark_oracle_available")
            if final_status.get("benchmark_oracle_available") is not None
            else any(item.get("benchmark_oracle_available") for item in target_bs_objects)
        ),
        "final_result_mode": _coalesce_target_value(
            final_status,
            target_bs_objects,
            "final_result_mode",
        ),
        "classification_is_published_final": bool(
            _coalesce_target_value(
                final_status,
                target_bs_objects,
                "classification_is_published_final",
            )
        ),
        "status": str(final_status.get("status") or "not_final"),
        "checks_passed": bool(result["checks"]["checks_passed"]),
        "final_results_available": bool(result["checks"]["final_results_available"]),
        "final_results_verified": bool(result["checks"]["final_results_verified"]),
        "single_target_dBS": single_bs.get("dBS"),
        "single_target_dAI": single_ai.get("dAI"),
        "single_target_ai_image_rank_in_bs": single_ai.get("ai_image_rank_in_bs"),
        "single_target_classification": single_quotient.get("classification"),
        "double_target_dBS": double_bs.get("dBS"),
        "double_target_dAI": double_ai.get("dAI"),
        "double_target_ai_image_rank_in_bs": double_ai.get("ai_image_rank_in_bs"),
        "double_target_classification": double_quotient.get("classification"),
        "single_target_object_kind": single_bs.get("object_kind"),
        "double_target_object_kind": double_bs.get("object_kind"),
        "single_target_blocker": single_bs.get("blocker"),
        "double_target_blocker": double_bs.get("blocker"),
        "current_row_shell_status": alignment.get("current_row_shell", {}).get("status"),
        "local_ai_seed_status": alignment.get("local_ai_seed_builder", {}).get("status"),
        "compatibility_builder_status": alignment.get("compatibility_builder", {}).get("status"),
        "single_target_alignment_builder_status": single_alignment_target.get("target_alignment_builder_status"),
        "double_target_alignment_builder_status": double_alignment_target.get("target_alignment_builder_status"),
        "single_target_exact_alignment_status": single_alignment_target.get("exact_alignment_status"),
        "double_target_exact_alignment_status": double_alignment_target.get("exact_alignment_status"),
        "single_target_generic_builder_ready": bool(single_bs.get("generic_builder_ready", False)),
        "double_target_generic_builder_ready": bool(double_bs.get("generic_builder_ready", False)),
        "single_target_generic_published_classification_ready": bool(
            single_bs.get("generic_published_classification_ready", False)
        ),
        "double_target_generic_published_classification_ready": bool(
            double_bs.get("generic_published_classification_ready", False)
        ),
        "single_target_reported_dai_semantics": single_ai.get("reported_dai_semantics"),
        "double_target_reported_dai_semantics": double_ai.get("reported_dai_semantics"),
        "single_target_classification_derivation_basis": single_quotient.get("classification_derivation_basis"),
        "double_target_classification_derivation_basis": double_quotient.get("classification_derivation_basis"),
        "single_target_same_shell_semantics": single_bs.get("same_shell_semantics"),
        "double_target_same_shell_semantics": double_bs.get("same_shell_semantics"),
        "single_target_verification_status": single_bs.get("verification_status"),
        "double_target_verification_status": double_bs.get("verification_status"),
        "single_target_same_shell_rank_check": single_bs.get("same_shell_rank_check"),
        "double_target_same_shell_rank_check": double_bs.get("same_shell_rank_check"),
        "minimal_blocker": minimal_blocker,
        "structured_blocker_evidence": blocker_evidence,
        "single_final_status": final_status.get("single_final", {}).get("status"),
        "double_final_status": final_status.get("double_final", {}).get("status"),
        "trust_level": result["spec"]["trust_level"],
    }


def build_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Group Engine Mode Report: {report['target_group']}",
            "",
            f"- Truth compare available: `{report['truth_compare_available']}`.",
            f"- Benchmark oracle available: `{report['benchmark_oracle_available']}`.",
            f"- Final result mode: `{report['final_result_mode']}`.",
            f"- Classification is published final: `{report['classification_is_published_final']}`.",
            f"- Status: `{report['status']}`.",
            f"- Checks passed / final results available / final results verified: `{report['checks_passed']}` / `{report['final_results_available']}` / `{report['final_results_verified']}`.",
            f"- Single target dBS / dAI / classification: `{report['single_target_dBS']}` / `{report['single_target_dAI']}` / `{report['single_target_classification']}`.",
            f"- Single target ai_image_rank_in_bs / reported_dai_semantics / same_shell_semantics: `{report['single_target_ai_image_rank_in_bs']}` / `{report['single_target_reported_dai_semantics']}` / `{report['single_target_same_shell_semantics']}`.",
            f"- Double target dBS / dAI / classification: `{report['double_target_dBS']}` / `{report['double_target_dAI']}` / `{report['double_target_classification']}`.",
            f"- Double target ai_image_rank_in_bs / reported_dai_semantics / same_shell_semantics: `{report['double_target_ai_image_rank_in_bs']}` / `{report['double_target_reported_dai_semantics']}` / `{report['double_target_same_shell_semantics']}`.",
            f"- Current row shell / local AI seed / compatibility builder: `{report['current_row_shell_status']}` / `{report['local_ai_seed_status']}` / `{report['compatibility_builder_status']}`.",
            f"- Single / double target-alignment builder status: `{report['single_target_alignment_builder_status']}` / `{report['double_target_alignment_builder_status']}`.",
            f"- Minimal blocker: `{report['minimal_blocker']}`.",
            f"- Structured blocker evidence: `{report['structured_blocker_evidence']}`.",
            f"- Trust level: `{report['trust_level']}`.",
        ]
    )


def assert_expected_contract(report: dict[str, Any]) -> None:
    target_group = report["target_group"]
    if target_group == "194.1.1.1":
        if report["truth_compare_available"] is not True:
            raise SystemExit("194.1.1.1 should keep truth-compare metadata available")
        if report["final_result_mode"] == "benchmark_aligned_final":
            raise SystemExit("194.1.1.1 must no longer use benchmark_aligned_final on the main solver path")
        if report["current_row_shell_status"] != "available":
            raise SystemExit("194.1.1.1 generic current-row shell must be available")
        if report["local_ai_seed_status"] != "available":
            raise SystemExit("194.1.1.1 generic local AI seed must be available")
        if report["compatibility_builder_status"] != "available":
            raise SystemExit("194.1.1.1 generic compatibility builder must be available")
        return
    if target_group == "99.1.1.1":
        if report["truth_compare_available"] is not False:
            raise SystemExit("99.1.1.1 must stay truth-compare free")
        if report["final_result_mode"] == "generic_final":
            if report["classification_is_published_final"] is not True:
                raise SystemExit("99.1.1.1 generic_final must be marked published-final")
            if report["status"] != "success":
                raise SystemExit("99.1.1.1 generic_final must end as success")
            if report["single_target_classification"] is None or report["double_target_classification"] is None:
                raise SystemExit("99.1.1.1 generic_final must expose target classifications")
            if report["single_target_dBS"] != report["single_target_dAI"] or report["double_target_dBS"] != report["double_target_dAI"]:
                raise SystemExit("99.1.1.1 generic_final must satisfy dBS == dAI")
            if report["single_target_verification_status"] != "semantic_pass" or report["double_target_verification_status"] != "semantic_pass":
                raise SystemExit("99.1.1.1 generic_final must pass semantic verification")
            return
        if report["final_result_mode"] != "diagnostic_only":
            raise SystemExit("99.1.1.1 without a same-shell target result must fall back to diagnostic_only")
        if report["classification_is_published_final"] is not False:
            raise SystemExit("99.1.1.1 diagnostic_only must not be marked published-final")
        if report["status"] != "not_final":
            raise SystemExit("99.1.1.1 diagnostic_only must end as not_final")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the group-driven classification smoke test")
    parser.add_argument("--target-group", required=True)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--report-md", type=Path)
    args = parser.parse_args()

    smoke_root = REPO_ROOT / "sg194" / "pipeline_runs_v2"
    smoke_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="group-classification-smoke-", dir=smoke_root) as td:
        config = PipelineRunConfig(
            group=args.target_group,
            mode="both",
            row_language="all",
            output_dir=Path(td),
            validate=False,
            build_package=False,
            refresh=False,
        )
        result = run_pipeline(config, REPO_ROOT)

    report = build_report(args.target_group, result)
    assert_expected_contract(report)

    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    if args.report_md is not None:
        args.report_md.parent.mkdir(parents=True, exist_ok=True)
        args.report_md.write_text(build_markdown(report) + "\n")

    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
