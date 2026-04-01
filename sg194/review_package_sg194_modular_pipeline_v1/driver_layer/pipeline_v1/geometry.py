from __future__ import annotations

from typing import Any

from .models import GroupSpec
from .utils import now_iso


def build_geometry_summary(spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]:
    if not spec.runnable:
        return {
            "generated_at": now_iso(),
            "group": spec.group_id,
            "status": "template_only",
            "shared_backbone_available": False,
            "note": spec.readiness_note,
        }

    kmanifolds = artifacts["single_kmanifolds"]
    connectivity = artifacts["single_connectivity"]
    compatibility = artifacts["single_full_compatibility"]
    stage2 = artifacts["stage2_status"]

    objects = kmanifolds["objects"]
    object_counts = {
        "points": sum(1 for item in objects if item.get("type") == "point"),
        "lines": sum(1 for item in objects if item.get("type") == "line"),
        "planes": sum(1 for item in objects if item.get("type") == "plane"),
    }
    single_status = stage2["single_status"]
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "shared_backbone_available": True,
        "shared_backbone_mode": single_status.get("geometry_backbone_mode", "shared_with_double_runtime_by_construction"),
        "object_counts": object_counts,
        "connectivity_counts": {
            "point_line": len(connectivity.get("point_line", [])),
            "line_plane": len(connectivity.get("line_plane", [])),
            "unmatched_line_endpoints": len(connectivity.get("unmatched_line_endpoints", [])),
            "unmatched_plane_boundaries": len(connectivity.get("unmatched_plane_boundaries", [])),
        },
        "compatibility_matrix_shape": compatibility.get("matrix_shape", [len(compatibility["global_matrix"]), len(compatibility["global_unknown_ordering"])]),
        "global_unknown_count": len(compatibility["global_unknown_ordering"]),
        "global_row_count": len(compatibility["global_matrix_rows"]),
        "source_files": [
            spec.artifacts["single_kmanifolds"],
            spec.artifacts["single_connectivity"],
            spec.artifacts["single_full_compatibility"],
            spec.artifacts["stage2_status"],
        ],
    }
