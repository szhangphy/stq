from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sg194.pipeline_v2 import runtime_backend_free as port
from sg194.pipeline_v2.final_object_reduction import (
    build_publication_shell_invariance_audit,
    build_publication_shell_invariance_markdown,
)


DEFAULT_GROUPS = [
    "194.1.1494.1000",
    "159.1.1292.1000",
    "99.1.823.1000",
    "222.1.1601.1000",
]


def build_publication_state(group: str, mode: str) -> dict[str, Any]:
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(group)
    ctx = port.load_context(module, group, mode, ssg_dict)
    prepared = port.prepare_kgeometry(group)
    kgeom = {
        "payload": prepared["payload"],
        "grouped": prepared["grouped"],
        "connectivity": prepared["payload"],
        "runtime_ctx": prepared["ctx"],
        "line_orbit_to_id": prepared["line_orbit_to_id"],
        "plane_orbit_to_id": prepared["plane_orbit_to_id"],
    }
    synthetic = port.build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic
    port.augment_connectivity_with_boundary_points(kgeom, synthetic)
    port.build_point_instance_entries(kgeom)
    ctx["kgeom"] = kgeom
    captures = port.build_manifold_capture(module, group, ssg_dict, ctx, mode, kgeom)
    reduction = port.reduce_final_point_path_shell(kgeom)
    candidate_lines = port.annotate_final_path_lines(
        reduction["candidate_line_specs"],
        kgeom["runtime_ctx"],
        kgeom["line_orbit_to_id"],
        kgeom["plane_orbit_to_id"],
    )
    port.capture_final_path_lines(module, group, ssg_dict, ctx, mode, captures, candidate_lines)
    candidate_blocks = [
        port.build_line_block(
            line,
            captures,
            phase_aware_profile="legacy",
            builder_variant="authoritative",
        )
        for line in candidate_lines
    ]
    analysis = port.analyze_candidate_path_selection(
        reduction,
        port.build_candidate_path_records(reduction, candidate_blocks),
    )
    reduction = port.finalize_reduction_from_candidate_analysis(reduction, analysis)
    publication_shell = port.build_publication_shell_candidate(reduction)
    publication_c = port.build_publication_C_matrix(publication_shell)
    bs = port.analyze_kernel(publication_c)
    audit = build_publication_shell_invariance_audit(publication_shell)
    return {
        "group": group,
        "mode": mode,
        "publication_shell": publication_shell,
        "publication_bs_rank": int(bs["nullity"]),
        "publication_matrix_shape": list(bs["matrix_shape"]),
        "invariance_audit": audit,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publication-shell BS invariance audit")
    parser.add_argument("--groups", nargs="*", default=DEFAULT_GROUPS)
    parser.add_argument(
        "--modes",
        nargs="*",
        choices=["single", "double"],
        default=["single", "double"],
    )
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    for group in args.groups:
        for mode in args.modes:
            state = build_publication_state(group, mode)
            audit = state["invariance_audit"]
            stem = f"publication_bs_invariance_{group.replace('.', '_')}_{mode}"
            json_path = output_dir / f"{stem}.json"
            md_path = output_dir / f"{stem}.md"
            json_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            md_path.write_text(
                build_publication_shell_invariance_markdown(audit),
                encoding="utf-8",
            )
            print(
                f"{group} {mode}: dBS={state['publication_bs_rank']} "
                f"shape={state['publication_matrix_shape']} "
                f"resolved={audit['all_selected_classes_internally_resolved']} "
                f"unresolved={audit['unresolved_class_ids']}"
            )
            summary.append(
                {
                    "group": group,
                    "mode": mode,
                    "dBS": state["publication_bs_rank"],
                    "shape": state["publication_matrix_shape"],
                    "resolved": audit["all_selected_classes_internally_resolved"],
                    "unresolved": list(audit["unresolved_class_ids"]),
                    "canonical_multi_source": list(audit["canonical_multi_source_class_ids"]),
                }
            )
    (output_dir / "publication_bs_invariance_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
