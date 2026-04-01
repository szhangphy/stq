from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .alignment import build_alignment_summary
from .bs_ai import build_ai_summary, build_bs_summary, build_result_objects, filter_result_objects
from .checks import build_consistency_checks
from .geometry import build_geometry_summary
from .legacy_bridge import ensure_legacy_state, load_artifacts
from .models import PipelineRunConfig
from .quotient import build_quotient_summary
from .reporting import finalize_output_package, write_pipeline_outputs
from .specs import get_group_spec, list_group_specs
from .utils import now_iso


def build_final_status(spec, artifacts: dict[str, Any], selected_records: list[dict[str, Any]]) -> dict[str, Any]:
    if not spec.runnable:
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "template_only",
            "single_final": {
                "object_kind": "template_placeholder",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "row_language_kind": None,
            },
            "double_final": {
                "object_kind": "template_placeholder",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "row_language_kind": None,
            },
            "same_final_object": False,
            "note": spec.readiness_note,
        }
    stage2 = artifacts["stage2_status"]
    records = {item["object_id"]: item for item in selected_records}
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "single_final": {
            "object_kind": stage2["single_final_object_kind"],
            "dBS": records["single_target_exact"]["dBS"],
            "dAI": records["single_target_exact"]["dAI"],
            "classification": records["single_target_exact"]["classification"],
            "row_language_kind": records["single_target_exact"]["row_language_kind"],
        },
        "double_final": {
            "object_kind": stage2["double_final_object_kind"],
            "dBS": records["double_target_benchmark_facing"]["dBS"],
            "dAI": records["double_target_benchmark_facing"]["dAI"],
            "classification": records["double_target_benchmark_facing"]["classification"],
            "row_language_kind": records["double_target_benchmark_facing"]["row_language_kind"],
        },
        "same_final_object": stage2["single_double_final_same_target_object"],
        "relation": stage2["single_double_final_relation"],
    }


def default_output_dir(repo_root: Path, spec_key: str, mode: str, row_language: str) -> Path:
    return repo_root / "sg194" / "pipeline_runs" / f"{spec_key}_{mode}_{row_language}_latest"


def run_pipeline(config: PipelineRunConfig, repo_root: Path) -> dict[str, Any]:
    spec = get_group_spec(config.group)
    bridge_status = ensure_legacy_state(spec, repo_root, refresh=config.refresh)
    artifacts = load_artifacts(spec, repo_root)
    geometry = build_geometry_summary(spec, artifacts)
    alignment = build_alignment_summary(spec, artifacts)
    records = build_result_objects(spec, artifacts)
    selected_records = filter_result_objects(records, config.mode, config.row_language)
    bs_summary = build_bs_summary(selected_records, spec)
    ai_summary = build_ai_summary(selected_records, spec)
    quotient_summary = build_quotient_summary(selected_records, spec)
    final_status = build_final_status(spec, artifacts, records if spec.runnable else selected_records)
    checks = build_consistency_checks(spec, artifacts, geometry, alignment, records if spec.runnable else selected_records, bridge_status)
    manifest = write_pipeline_outputs(
        config.output_dir,
        repo_root,
        spec,
        geometry,
        alignment,
        bs_summary,
        ai_summary,
        quotient_summary,
        final_status,
        checks,
    )
    package_tarball = None
    if config.build_package:
        package_tarball = finalize_output_package(config.output_dir, repo_root)
    result = {
        "spec": {
            "key": spec.key,
            "group_id": spec.group_id,
            "runnable": spec.runnable,
        },
        "bridge_status": bridge_status,
        "geometry": geometry,
        "alignment": alignment,
        "bs_summary": bs_summary,
        "ai_summary": ai_summary,
        "quotient_summary": quotient_summary,
        "final_status": final_status,
        "checks": checks,
        "manifest": manifest,
        "package_tarball": package_tarball,
    }
    if config.validate and not checks["all_passed"]:
        raise SystemExit("pipeline consistency checks failed")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified modular group pipeline driver")
    parser.add_argument("--group", default="sg194")
    parser.add_argument("--mode", choices=["single", "double", "both"], default="both")
    parser.add_argument("--row-language", choices=["raw", "target", "all"], default="all")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--build-package", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--list-groups", action="store_true")
    args = parser.parse_args()

    if args.list_groups:
        for item in list_group_specs():
            print(f"{item['key']}: group={item['group_id']} runnable={item['runnable']}")
        return

    repo_root = Path(__file__).resolve().parents[2]
    output_dir = args.output_dir or default_output_dir(repo_root, args.group.replace(".", "_"), args.mode, args.row_language)
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    config = PipelineRunConfig(
        group=args.group,
        mode=args.mode,
        row_language=args.row_language,
        output_dir=output_dir,
        validate=args.validate,
        build_package=args.build_package,
        refresh=args.refresh,
    )
    result = run_pipeline(config, repo_root)
    print(
        f"pipeline ok: group={result['spec']['group_id']} mode={args.mode} row_language={args.row_language} "
        f"all_passed={result['checks']['all_passed']} output_dir={output_dir}"
    )
