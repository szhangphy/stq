#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sg194.pipeline_v2 import generic_builders as gb


def json_complex_matrix(rows):
    return [
        [
            {"real": float(complex(value).real), "imag": float(complex(value).imag)}
            for value in row
        ]
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="222.1.1.1")
    parser.add_argument("--mode", choices=["single", "double"], default="single")
    parser.add_argument("--line-id", default="L3")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    port = gb.stage1_backend()
    shared = gb.shared_geometry_bundle(args.group)
    module = gb.ssgreps_module()
    ssg_dict = port.load_ssg_dict(args.group)
    ctx = port.load_context(module, args.group, args.mode, ssg_dict)
    ctx["kgeom"] = shared["kgeom"]
    captures = port.build_manifold_capture(module, args.group, ssg_dict, ctx, args.mode, shared["kgeom"])

    line_obj = next(item for item in shared["grouped"]["lines"] if item["id"] == args.line_id)
    endpoint_entries = [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
        }
        for endpoint in line_obj["endpoints"]
    ]
    line_raw = captures[args.line_id]
    exact_error = None
    try:
        port.build_line_block(line_obj, captures, phase_aware_profile=None)
    except Exception as exc:  # pragma: no cover - diagnostic only
        exact_error = str(exc)

    endpoint_classes = {}
    endpoint_classes_linear = {}
    for endpoint in endpoint_entries:
        point_id = endpoint["point_id"]
        point_raw = captures[endpoint["capture_id"]]
        matched = port.matched_unitary_indices(line_raw, point_raw)
        endpoint_classes[point_id] = port.identical_restriction_classes(
            point_id,
            point_raw,
            matched,
            field="character",
        )
        endpoint_classes_linear[point_id] = port.identical_restriction_classes(
            point_id,
            point_raw,
            matched,
            field="linear_character",
        )

    payload = {
        "group": args.group,
        "mode": args.mode,
        "line_id": args.line_id,
        "exact_build_error": exact_error,
        "line_group_signature": {
            "n_unitary_ops": line_raw["unitary_operation_count"],
            "rep_degree": list(line_raw["rep_degree"]),
            "torsion": list(line_raw["torsion"]),
        },
        "line_character": json_complex_matrix(line_raw["character"]),
        "line_linear_character": json_complex_matrix(line_raw["linear_character"]),
        "endpoint_entries": endpoint_entries,
        "character_restriction_classes": endpoint_classes,
        "linear_character_restriction_classes": endpoint_classes_linear,
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
