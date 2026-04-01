from __future__ import annotations

from typing import Any

from .coordinates import build_kspace_geometry, build_realspace_geometry, load_trusted_symmetry_payload
from .generic_builders import generic_geometry_summary
from .models import GroupSpec
from .utils import now_iso


def _manifold_kind(dim: int | None) -> str:
    if dim == 0:
        return "point"
    if dim == 1:
        return "line"
    if dim == 2:
        return "plane"
    return "other"


def _entry_sample(entries: list[dict[str, Any]], coord_key: str, *, include_site_symmetry: bool = False) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    for idx, item in enumerate(entries[:5]):
        payload = {
            "index": idx,
            "dim": item.get("dim"),
            "kind": _manifold_kind(item.get("dim")),
            "mult": item.get("mult"),
            "representative_coordinate": item.get("representative_coordinate"),
            "coordinate_list_size": len(item.get(coord_key, [])) if isinstance(item.get(coord_key), list) else None,
            "basis_vector_count": len(item.get("basis_vecs", [])),
        }
        if include_site_symmetry:
            payload["site_symmetry"] = item.get("site_symmetry")
        sample.append(payload)
    return sample


def _count_object_kinds(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"points": 0, "lines": 0, "planes": 0, "other": 0}
    for item in entries:
        kind = _manifold_kind(item.get("dim"))
        if kind == "point":
            counts["points"] += 1
        elif kind == "line":
            counts["lines"] += 1
        elif kind == "plane":
            counts["planes"] += 1
        else:
            counts["other"] += 1
    return counts


def _is_generic_spec(spec: GroupSpec) -> bool:
    return spec.builder_backend == "generic_symmetry_ops"


def build_geometry_summary(spec: GroupSpec, adapter, artifacts: dict[str, Any]) -> dict[str, Any]:
    if _is_generic_spec(spec):
        summary = generic_geometry_summary(spec.group_id)
        trusted = load_trusted_symmetry_payload(spec.group_id)
        kspace = build_kspace_geometry(spec.group_id)
        realspace = build_realspace_geometry(spec.group_id)
        summary.update(
            {
                "trust_policy": spec.special_rules.get("trust_policy"),
                "symmetry_operation_count": len(trusted["operations"]),
                "crystal_system": trusted.get("crystal_system"),
                "centering_symbol": trusted.get("centering_symbol"),
                "source_centering_symbol": trusted.get("source_centering_symbol"),
                "kspace": {
                    "coord_key": kspace["coord_key"],
                    "entry_count": len(kspace["entries"]),
                    "sample_entries": _entry_sample(kspace["entries"], kspace["coord_key"]),
                },
                "realspace": {
                    "coord_key": realspace["coord_key"],
                    "entry_count": len(realspace["entries"]),
                    "sample_entries": _entry_sample(realspace["entries"], realspace["coord_key"], include_site_symmetry=True),
                },
                "generic_builder_layers": {
                    "geometry": "available",
                    "current_row_shell": "available",
                    "current_row_compatibility": "available",
                    "target_alignment": "available",
                    "local_ai_seed": "available",
                    "local_ai_embedding": "available",
                    "direct_quotient": "available",
                },
            }
        )
        return summary
    return adapter.build_geometry_summary(spec, artifacts)
