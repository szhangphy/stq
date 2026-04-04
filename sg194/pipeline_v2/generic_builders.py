from __future__ import annotations

import json
import re
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from . import local_irreps as runtime_local_irreps
from . import runtime_backend_free
from .utils import now_iso


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_BACKEND = ROOT / "pipeline_v2" / "runtime_backend_free.py"
LOCAL_IRREP_BACKEND = ROOT / "pipeline_v2" / "local_irreps.py"

GENERIC_CURRENT_ROW_LANGUAGE = "generic_current_row_shell_from_symmetry_ops"
GENERIC_TARGET_ROW_LANGUAGE = "generic_same_shell_published_target"
GENERIC_TARGET_OBJECT_KIND = "generic_same_shell_target_object"
LINE_SAMPLE = Fraction(1, 5)


@lru_cache(maxsize=1)
def stage1_backend():
    return runtime_backend_free


@lru_cache(maxsize=1)
def local_library_backend():
    return runtime_local_irreps


@lru_cache(maxsize=1)
def ssgreps_module():
    return runtime_backend_free.load_ssgreps_module()


def _class_key(restricted_vector: list[dict[str, Any]]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, float):
            if abs(value) < 1e-12:
                return 0
            rounded = round(value)
            if abs(value - rounded) < 1e-12:
                return int(rounded)
            return float(value)
        return value

    return json.dumps(normalize(restricted_vector), sort_keys=True, separators=(",", ":"))


def _parse_line_orbit_coordinate(piece: str, sample: Fraction) -> Fraction:
    token = piece.strip()
    if not token:
        return Fraction(0)
    variable_value = sp.Rational(sample.numerator, sample.denominator)
    locals_map = {
        "u": variable_value,
        "v": variable_value,
        "w": variable_value,
        "t": variable_value,
    }
    expr = parse_expr(
        token,
        local_dict=locals_map,
        transformations=standard_transformations + (implicit_multiplication_application,),
        evaluate=True,
    )
    value = sp.nsimplify(expr)
    if not value.is_rational:
        raise ValueError(f"line orbit coordinate is not rational after sampling: {piece!r}")
    return Fraction(str(value))


def _line_orbit_sample_points(line_obj: dict[str, Any], sample: Fraction = LINE_SAMPLE) -> list[list[float]]:
    orbit = line_obj.get("metadata", {}).get("source_orbit", [])
    points: list[list[float]] = []
    seen: set[tuple[float, float, float]] = set()
    for item in orbit:
        coords = tuple(
            float(_parse_line_orbit_coordinate(piece, sample) % 1)
            for piece in item.split(",")
        )
        if coords in seen:
            continue
        seen.add(coords)
        points.append(list(coords))
    return points


def _line_capture_exact_status(port: Any, line_obj: dict[str, Any], captures: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        port.build_line_block_coarse(line_obj, captures, phase_aware_profile=None)
        return True, None
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, str(exc)


@lru_cache(maxsize=None)
def shared_geometry_bundle(group_id: str) -> dict[str, Any]:
    port = stage1_backend()
    prepared = port.prepare_kgeometry(group_id)
    grouped = prepared["grouped"]
    payload = prepared["payload"]
    kgeom = {"payload": payload, "grouped": grouped, "connectivity": payload}
    synthetic_points = port.build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic_points
    port.augment_connectivity_with_boundary_points(kgeom, synthetic_points)
    port.build_point_instance_entries(kgeom)
    real_point_ids = [item["id"] for item in grouped["points"]]
    all_point_ids = real_point_ids + [item["id"] for item in synthetic_points]
    return {
        "group_id": group_id,
        "kgeom": kgeom,
        "grouped": grouped,
        "payload": payload,
        "synthetic_points": synthetic_points,
        "real_point_ids": real_point_ids,
        "all_point_ids": all_point_ids,
        "target_point_ids": real_point_ids,
    }


def _canonicalize_line_captures(
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    grouped: dict[str, Any],
    captures: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    port = stage1_backend()
    adjusted = dict(captures)
    report: list[dict[str, Any]] = []
    for line_obj in grouped["lines"]:
        line_id = line_obj["id"]
        current_raw = adjusted[line_id]
        current_ok, current_error = _line_capture_exact_status(port, line_obj, adjusted)
        chosen_raw = current_raw
        chosen_source = "default_sample_point"
        chosen_point = line_obj["sample_point"]
        candidate_records = [
            {
                "source": "default_sample_point",
                "sample_point": list(line_obj["sample_point"]),
                "exact_endpoint_subduction": current_ok,
                "error": current_error,
            }
        ]
        if not current_ok:
            for coords in _line_orbit_sample_points(line_obj):
                raw = port.capture_little_group(module, group_id, ssg_dict, ctx, mode, line_id, coords)
                test_captures = dict(adjusted)
                test_captures[line_id] = raw
                ok, error = _line_capture_exact_status(port, line_obj, test_captures)
                candidate_records.append(
                    {
                        "source": "metadata.source_orbit",
                        "sample_point": coords,
                        "exact_endpoint_subduction": ok,
                        "error": error,
                    }
                )
                if ok:
                    chosen_raw = raw
                    chosen_source = "metadata.source_orbit"
                    chosen_point = [str(value) for value in coords]
                    break
        chosen_raw = dict(chosen_raw)
        chosen_raw["capture_sample_point"] = list(chosen_point)
        chosen_raw["capture_canonicalization_source"] = chosen_source
        adjusted[line_id] = chosen_raw
        report.append(
            {
                "line_id": line_id,
                "chosen_sample_point": list(chosen_point),
                "chosen_source": chosen_source,
                "exact_endpoint_subduction": current_ok if chosen_source == "default_sample_point" else True,
                "candidate_records": candidate_records,
            }
        )
    return adjusted, report


def _build_unknown_ordering(captures: dict[str, Any], point_ids: list[str]) -> list[str]:
    ordering = []
    for point_id in point_ids:
        rep_count = len(captures[point_id]["linear_character"])
        for rep_index in range(1, rep_count + 1):
            ordering.append(f"{point_id}_R{rep_index}")
    return ordering


def _build_restriction_class_rows(
    manifold_raw: dict[str, Any],
    endpoint_entries: list[dict[str, Any]],
    captures: dict[str, Any],
    *,
    source_type: str,
    field: str = "linear_character",
    match_provider=None,
    endpoint_label_key: str = "point_id",
) -> dict[str, Any]:
    port = stage1_backend()
    endpoint_classes = {}
    union: dict[str, dict[str, list[str]]] = {}
    vectors_by_key: dict[str, list[dict[str, Any]]] = {}

    for entry in endpoint_entries:
        endpoint_id = str(entry[endpoint_label_key])
        capture_id = entry.get("capture_id", endpoint_id)
        endpoint_raw = captures[capture_id]
        matched = (
            match_provider(manifold_raw, endpoint_raw)
            if match_provider is not None
            else port.matched_unitary_indices(manifold_raw, endpoint_raw)
        )
        classes = port.identical_restriction_classes(endpoint_id, endpoint_raw, matched, field=field)
        endpoint_classes[(endpoint_id, capture_id)] = classes
        for klass in classes:
            key = _class_key(klass["restricted_vector"])
            union.setdefault(key, {})[endpoint_id] = list(klass["rep_ids"])
            vectors_by_key[key] = list(klass["restricted_vector"])

    equations = []
    endpoint_ids = [str(entry[endpoint_label_key]) for entry in endpoint_entries]
    anchor = endpoint_ids[0]
    for class_index, key in enumerate(sorted(union), start=1):
        support = union[key]
        restricted_vector = vectors_by_key[key]
        if source_type == "line":
            if len(endpoint_ids) != 2:
                raise RuntimeError("line compatibility requires exactly two endpoints")
            left, right = endpoint_ids
            terms = []
            for rep_id in support.get(left, []):
                terms.append({"unknown": rep_id, "coeff": 1, "side": "left"})
            for rep_id in support.get(right, []):
                terms.append({"unknown": rep_id, "coeff": -1, "side": "right"})
            if terms:
                equations.append(
                    {
                        "basis_id": f"{source_type}_class_{class_index:02d}",
                        "terms": terms,
                        "restricted_vector": restricted_vector,
                    }
                )
        else:
            for other in endpoint_ids[1:]:
                terms = []
                for rep_id in support.get(anchor, []):
                    terms.append({"unknown": rep_id, "coeff": 1, "side": "anchor"})
                for rep_id in support.get(other, []):
                    terms.append({"unknown": rep_id, "coeff": -1, "side": "corner"})
                if terms:
                    equations.append(
                        {
                            "basis_id": f"{source_type}_class_{class_index:02d}_{anchor}_vs_{other}",
                            "terms": terms,
                            "restricted_vector": restricted_vector,
                            "anchor_point_id": anchor,
                            "other_point_id": other,
                        }
                    )

    return {
        "source_type": source_type,
        "endpoint_classes": endpoint_classes,
        "equations": equations,
    }


def _build_generic_line_block(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    *,
    builder_variant: str,
) -> dict[str, Any]:
    phase_aware_profile = (
        stage1_backend().AUTHORITATIVE_PHASE_AWARE_PROFILE
        if builder_variant in {"authoritative", "coarse"}
        else None
    )
    return stage1_backend().build_line_block(
        line_obj,
        captures,
        phase_aware_profile=phase_aware_profile,
        builder_variant=builder_variant,
    )


def _build_generic_line_block_compare_coarse(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
) -> dict[str, Any]:
    return stage1_backend().build_line_block_coarse(line_obj, captures, phase_aware_profile=None)


def _build_generic_plane_block(
    plane_obj: dict[str, Any],
    corner_entries: list[dict[str, Any]],
    captures: dict[str, Any],
) -> dict[str, Any]:
    return stage1_backend().build_plane_block(plane_obj, corner_entries, captures)


def _build_generic_plane_block_fallback(
    plane_obj: dict[str, Any],
    corner_entries: list[dict[str, Any]],
    captures: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    block = _build_restriction_class_rows(
        captures[plane_obj["id"]],
        corner_entries,
        captures,
        source_type="plane",
        field="character",
    )
    equations = []
    for equation in block["equations"]:
        point_id = equation.get("other_point_id") or equation.get("anchor_point_id")
        equations.append(
            {
                **equation,
                "point_id": point_id,
            }
        )
    local_unknown_ordering = []
    for corner in corner_entries:
        point_id = corner["point_id"]
        point_raw = captures[corner.get("capture_id", point_id)]
        for rep_index in range(1, len(point_raw["linear_character"]) + 1):
            local_unknown_ordering.append(f"{point_id}_R{rep_index}")
    return {
        "status": "fallback_restriction_classes",
        "plane_id": plane_obj["id"],
        "corner_ids": [entry["point_id"] for entry in corner_entries],
        "plane_sample_point": plane_obj["sample_point"],
        "plane_parametrization": plane_obj["parametrization"],
        "plane_symmetry_summary": plane_obj["symmetry_summary"],
        "corner_decompositions": {},
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": [],
        "plane_basis_labels": [],
        "plane_group_signature": {
            "fallback_reason": reason,
            "n_unitary_ops": captures[plane_obj["id"]]["unitary_operation_count"],
        },
    }


def _build_generic_compatibility(
    group_id: str,
    grouped: dict[str, Any],
    point_ids: list[str],
    captures: dict[str, Any],
    *,
    builder_variant: str,
) -> dict[str, Any]:
    port = stage1_backend()
    line_blocks = []
    line_builder_compare = []
    for line in grouped["lines"]:
        block = _build_generic_line_block(line, captures, builder_variant=builder_variant)
        line_blocks.append(block)
        coarse_compare = _build_generic_line_block_compare_coarse(line, captures)
        line_builder_compare.append(
            {
                "line_id": line["id"],
                "builder_variant": builder_variant,
                "primary_builder_kind": block.get(
                    "compatibility_builder_kind",
                    block.get("restriction_class_builder", {}).get("builder_kind", builder_variant),
                ),
                "primary_equation_count": len(block.get("equations", [])),
                "primary_row_count": len(block.get("matrix_rows", [])),
                "coarse_equation_count": len(coarse_compare.get("equations", [])),
                "coarse_matrix_row_count": len(coarse_compare.get("matrix_rows", [])),
                "containing_planes": block.get("restriction_class_builder", {}).get("containing_planes", []),
            }
        )
    line_full = port.build_global_compatibility(line_blocks, point_ids)
    plane_blocks = []
    plane_fallbacks = []
    for plane in grouped["planes"]:
        try:
            block = _build_generic_plane_block(plane, plane["corner_entries"], captures)
        except Exception as exc:
            block = _build_generic_plane_block_fallback(plane, plane["corner_entries"], captures, str(exc))
            plane_fallbacks.append({"plane_id": plane["id"], "reason": str(exc)})
        plane_blocks.append(block)
    with_planes = port.build_with_planes_compatibility(line_full, plane_blocks)
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "builder_variant": builder_variant,
        "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
        "global_unknown_ordering": list(with_planes["global_unknown_ordering"]),
        "global_matrix_rows": list(with_planes["global_matrix_rows"]),
        "global_matrix": [list(row) for row in with_planes["global_matrix"]],
        "line_blocks": line_blocks,
        "plane_blocks": plane_blocks,
        "matrix_shape": [
            len(with_planes["global_matrix"]),
            len(with_planes["global_unknown_ordering"]),
        ],
        "covered_lines": list(with_planes.get("covered_lines", [])),
        "covered_planes": list(with_planes.get("covered_planes", [])),
        "compatibility_builder_kind": {
            "authoritative": stage1_backend().AUTHORITATIVE_COMPATIBILITY_BUILDER_KIND,
            "coarse": "legacy_compare_only_generic_coarse_basis_decomposition_line_builder",
            "intrinsic": stage1_backend().RETIRED_INTRINSIC_BUILDER_KIND,
        }[builder_variant],
        "phase_aware_profile": (
            stage1_backend().AUTHORITATIVE_PHASE_AWARE_PROFILE
            if builder_variant in {"authoritative", "coarse"}
            else "disabled_compare_only"
        ),
        "line_builder_compare": line_builder_compare,
        "plane_fallbacks": plane_fallbacks,
    }


def _build_local_irrep_library(ctx: dict[str, Any], mode: str) -> dict[str, Any]:
    port = stage1_backend()
    local = local_library_backend()
    compose = ctx["group_tables"]["compose"]
    inverse = ctx["group_tables"]["inverse"]
    factor = np.array(ctx["ssg"].factor_su2, dtype=complex) if mode == "double" else None

    by_family = {}
    inventory = []
    cache: dict[str, list[dict[str, Any]]] = {}

    def single_cache_key(record: dict[str, Any]) -> str:
        return json.dumps(
            {
                "type": record["site_symmetry_type_key"],
                "mult_table": record["multiplication_table_local"],
                "parity_local_index": record.get("parity_element_local_index"),
                "rotation_orders": record["rotation_orders"],
                "rotation_determinants": record["rotation_determinants"],
                "rotation_traces": record["rotation_traces"],
            },
            sort_keys=True,
            default=str,
        )

    def double_cache_key(record: dict[str, Any], cocycle: np.ndarray) -> str:
        return json.dumps(
            {
                "type": record["site_symmetry_type_key"],
                "mult_table": record["multiplication_table_local"],
                "parity_local_index": record.get("parity_element_local_index"),
                "cocycle": [
                    [[float(np.real(value)), float(np.imag(value))] for value in row]
                    for row in cocycle.tolist()
                ],
            },
            sort_keys=True,
        )

    for entry in ctx["wyckoff_entries"]:
        bridge_entry = port.bridge.bridge_stabilizer_for_entry(entry, ctx)
        record = local.group_local_record(entry["letter"], entry, bridge_entry, ctx, compose, inverse)
        if mode == "single":
            cache_key = single_cache_key(record)
            irreps = cache.get(cache_key)
            if irreps is None:
                if ctx["group_number"] == "194.1.1.1":
                    irreps = local.ordinary_single_characters_for_record(record)
                else:
                    is_abelian = all(size == 1 for size in record["class_sizes"])
                    if is_abelian:
                        irreps = local.generic_abelian_single_characters_for_record(record)
                    else:
                        irreps = local.generic_regular_single_characters_for_record(record)
                cache[cache_key] = irreps
        else:
            stabilizer = record["stabilizer_indices"]
            cocycle = factor[np.ix_(stabilizer, stabilizer)]
            cache_key = double_cache_key(record, cocycle)
            irreps = cache.get(cache_key)
            if irreps is None:
                blocks = local.twisted_isotypic_blocks(record["multiplication_table_local"], cocycle)
                irreps = local.label_projective_irreps(record, blocks)
                cache[cache_key] = irreps

        family_irreps = []
        for irrep in irreps:
            family_irreps.append(
                {
                    "generator_id": f"{entry['letter']}_{irrep['label']}",
                    "family_letter": entry["letter"],
                    "label": irrep["label"],
                    "dimension": int(irrep["dimension"]),
                    "local_character": {
                        int(global_index): complex(value)
                        for global_index, value in zip(record["stabilizer_indices"], irrep["character"])
                    },
                }
            )
        by_family[entry["letter"]] = family_irreps
        inventory.append(
            {
                "family_letter": entry["letter"],
                "site_symmetry_type_key": record["site_symmetry_type_key"],
                "site_symmetry_type_label": record["site_symmetry_type_label"],
                "generator_count": len(family_irreps),
            }
        )

    return {
        "mode": mode,
        "families": by_family,
        "inventory": inventory,
        "generator_count": sum(len(items) for items in by_family.values()),
    }


def _induce_all_candidates(
    ctx: dict[str, Any],
    captures: dict[str, Any],
    compatibility: dict[str, Any],
    unknown_ordering: list[str],
    local_library: dict[str, Any],
    *,
    point_row_translation: dict[str, Any] | None,
) -> dict[str, Any]:
    port = stage1_backend()
    candidates = []
    failures = []
    for entry in ctx["wyckoff_entries"]:
        for generator in local_library["families"][entry["letter"]]:
            try:
                candidate = port.induce_candidate(
                    entry,
                    generator["local_character"],
                    ctx,
                    captures,
                    unknown_ordering,
                    compatibility["global_matrix"],
                    point_row_translation=point_row_translation,
                )
                candidate["generator_id"] = generator["generator_id"]
                candidate["mode"] = local_library["mode"]
                candidates.append(candidate)
            except Exception as exc:  # pragma: no cover - diagnostic path
                failures.append(
                    {
                        "generator_id": generator["generator_id"],
                        "family_letter": entry["letter"],
                        "error": str(exc),
                    }
                )
    return {
        "mode": local_library["mode"],
        "candidates": candidates,
        "failures": failures,
        "candidate_count": len(candidates),
        "failure_count": len(failures),
    }


def _smith_diagonal(matrix: sp.Matrix) -> list[int]:
    diagonal = []
    for index in range(min(matrix.rows, matrix.cols)):
        value = abs(int(matrix[index, index]))
        if value:
            diagonal.append(value)
    return diagonal


def _quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    if free_rank == 0 and not finite_part:
        return "trivial"
    parts = []
    if free_rank == 1:
        parts.append("Z")
    elif free_rank > 1:
        parts.append(f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts)


def _solve_ai_in_bs_coordinates(bs_matrix: sp.Matrix, vector: list[int]) -> list[int]:
    solution = bs_matrix.gauss_jordan_solve(sp.Matrix(vector))[0]
    coords = []
    for entry in solution:
        if entry.q != 1:
            raise ValueError(f"non-integral AI-in-BS coordinate {entry}")
        coords.append(int(entry))
    return coords


def _point_row_indices(unknown_ordering: list[str], point_ids: list[str]) -> list[int]:
    prefixes = tuple(f"{point_id}_R" for point_id in point_ids)
    return [index for index, unknown in enumerate(unknown_ordering) if unknown.startswith(prefixes)]


def _project_vector_by_indices(vector: list[int], indices: list[int]) -> list[int]:
    return [int(vector[index]) for index in indices]


def _normalize_fraction_coordinates(coords: list[str] | tuple[str, ...] | tuple[Fraction, ...] | list[Fraction]) -> list[str]:
    return [str(Fraction(value)) for value in coords]


def _mod1_fraction_coordinates(coords: list[str] | tuple[str, ...] | tuple[Fraction, ...] | list[Fraction]) -> list[str]:
    return [str(Fraction(value) % 1) for value in coords]


def _target_line_endpoint_key(endpoint: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    return (
        str(endpoint["point_id"]),
        str(endpoint["capture_id"]),
        tuple(_normalize_fraction_coordinates(endpoint["point_coordinates"])),
    )


def _unordered_target_line_pair_key(line_id: str, endpoint_entries: list[dict[str, Any]], *, window_tag: str) -> tuple[str, str, tuple[tuple[str, str, tuple[str, ...]], ...]]:
    return (
        line_id,
        window_tag,
        tuple(sorted(_target_line_endpoint_key(entry) for entry in endpoint_entries)),
    )


def _register_target_capture_entry(
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    *,
    point_id: str,
    capture_id: str,
    point_coordinates: list[str],
) -> None:
    normalized = _normalize_fraction_coordinates(point_coordinates)
    modded = tuple(_mod1_fraction_coordinates(normalized))
    entry = {
        "point_id": point_id,
        "capture_id": capture_id,
        "point_coordinates": normalized,
    }
    existing = catalog.setdefault(modded, [])
    key = _target_line_endpoint_key(entry)
    if any(_target_line_endpoint_key(item) == key for item in existing):
        return
    existing.append(entry)


def _build_target_capture_catalog(
    *,
    shared: dict[str, Any],
) -> tuple[dict[tuple[str, str, str], list[dict[str, Any]]], dict[str, list[str]]]:
    grouped = shared["grouped"]
    point_representatives = {
        point["id"]: _normalize_fraction_coordinates(point["sample_point"])
        for point in grouped["points"]
        if point["id"] in set(shared["target_point_ids"])
    }
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for point_id, coords in point_representatives.items():
        _register_target_capture_entry(
            catalog,
            point_id=point_id,
            capture_id=point_id,
            point_coordinates=coords,
        )
    for instance in shared["kgeom"].get("point_instance_entries", []):
        if instance["point_id"] not in point_representatives:
            continue
        _register_target_capture_entry(
            catalog,
            point_id=instance["point_id"],
            capture_id=instance["capture_id"],
            point_coordinates=list(instance["point_coordinates"]),
        )
    return catalog, point_representatives


def _resolve_target_capture_entry(
    *,
    point_coordinates: list[str],
    allowed_point_ids: set[str],
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    point_representatives: dict[str, list[str]],
    captures: dict[str, Any],
    port: Any,
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
) -> dict[str, Any] | None:
    normalized = _normalize_fraction_coordinates(point_coordinates)
    modded = tuple(_mod1_fraction_coordinates(normalized))
    candidates = [
        entry
        for entry in catalog.get(modded, [])
        if entry["point_id"] in allowed_point_ids
    ]
    if not candidates:
        return None
    exact = next(
        (
            entry
            for entry in candidates
            if entry["point_coordinates"] == normalized
        ),
        None,
    )
    chosen = exact or sorted(
        candidates,
        key=lambda item: (
            item["capture_id"] == item["point_id"],
            item["capture_id"],
        ),
    )[0]
    point_id = str(chosen["point_id"])
    representative = point_representatives[point_id]
    capture_id = point_id if normalized == representative else port.point_capture_id(point_id, normalized)
    if capture_id not in captures:
        captures[capture_id] = port.capture_little_group(
            module,
            group_id,
            ssg_dict,
            ctx,
            mode,
            capture_id,
            [float(Fraction(value)) for value in normalized],
        )
    _register_target_capture_entry(
        catalog,
        point_id=point_id,
        capture_id=capture_id,
        point_coordinates=normalized,
    )
    return {
        "point_id": point_id,
        "capture_id": capture_id,
        "point_coordinates": normalized,
    }


def _build_target_restriction_line_block(
    *,
    source_line: dict[str, Any],
    block_id: str,
    endpoint_entries: list[dict[str, Any]],
    captures: dict[str, Any],
    builder_variant: str,
    endpoint_label_key: str = "point_id",
) -> dict[str, Any]:
    block = _build_restriction_class_rows(
        captures[source_line["id"]],
        endpoint_entries,
        captures,
        source_type="line",
        field="character",
        endpoint_label_key=endpoint_label_key,
    )
    endpoint_decompositions: dict[str, list[dict[str, Any]]] = {}
    local_unknown_ordering: list[str] = []
    for endpoint_entry in endpoint_entries:
        endpoint_id = str(endpoint_entry[endpoint_label_key])
        endpoint_raw = captures[endpoint_entry.get("capture_id", endpoint_id)]
        reps = []
        for rep_index in range(1, len(endpoint_raw["linear_character"]) + 1):
            rep_id = f"{endpoint_id}_R{rep_index}"
            reps.append(
                {
                    "rep_id": rep_id,
                    "rep_degree": int(endpoint_raw["rep_degree"][rep_index - 1]),
                    "torsion": int(endpoint_raw["torsion"][rep_index - 1]),
                    "decomposition_on_line_basis": {},
                }
            )
            local_unknown_ordering.append(rep_id)
        endpoint_decompositions[endpoint_id] = reps
    equations = []
    for equation in block["equations"]:
        equations.append(
            {
                **equation,
                "builder_variant": builder_variant,
                "row_kind": "restriction_class_sum",
                "target_line_block_kind": "real_line",
                "line_window_kind": "ordinary",
                "source_line_family": source_line["id"],
                "source_line_id": source_line["id"],
                "endpoint_capture_ids": [
                    entry.get("capture_id", entry["point_id"])
                    for entry in endpoint_entries
                ],
            }
        )
    matrix_rows = _build_block_matrix_rows_from_equations(
        local_unknown_ordering,
        equations,
        block_id=block_id,
    )
    return {
        "status": "fallback_restriction_classes",
        "line_id": block_id,
        "source_line_id": source_line["id"],
        "endpoint_ids": [str(entry[endpoint_label_key]) for entry in endpoint_entries],
        "line_sample_point": source_line.get("sample_point"),
        "line_parametrization": source_line.get("parametrization"),
        "line_symmetry_summary": source_line.get("symmetry_summary"),
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "line_basis_labels": [],
        "builder_variant": builder_variant,
        "target_line_block_kind": "real_line",
        "compatibility_builder_kind": "generic_same_shell_target_restriction_class_line_builder",
        "restriction_class_builder": {
            "builder_kind": "generic_same_shell_target_restriction_class_line_builder",
            "endpoint_capture_ids": [entry.get("capture_id", entry["point_id"]) for entry in endpoint_entries],
        },
    }


def _ordered_target_capture_ids(
    *,
    shared: dict[str, Any],
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
) -> list[str]:
    target_point_ids = set(shared["target_point_ids"])
    by_capture: dict[str, dict[str, Any]] = {}
    for entries in catalog.values():
        for entry in entries:
            if entry["point_id"] not in target_point_ids:
                continue
            by_capture[str(entry["capture_id"])] = {
                "capture_id": str(entry["capture_id"]),
                "point_id": str(entry["point_id"]),
                "point_coordinates": list(entry["point_coordinates"]),
            }
    ordered = sorted(
        by_capture.values(),
        key=lambda item: (
            item["point_id"],
            item["capture_id"] != item["point_id"],
            item["capture_id"],
            tuple(item["point_coordinates"]),
        ),
    )
    return [item["capture_id"] for item in ordered]


def _build_block_matrix_rows_from_equations(
    local_unknown_ordering: list[str],
    equations: list[dict[str, Any]],
    *,
    block_id: str,
) -> list[list[int]]:
    local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
    matrix_rows: list[list[int]] = []
    for equation in equations:
        row = [0] * len(local_unknown_ordering)
        seen_side_unknown: set[tuple[str, str]] = set()
        for term in equation.get("terms", []):
            unknown = str(term["unknown"])
            side = str(term.get("side", ""))
            coeff = int(term["coeff"])
            if unknown not in local_index:
                raise ValueError(f"{block_id}: unknown {unknown} is outside the local signature universe")
            marker = (side, unknown)
            if marker in seen_side_unknown:
                raise ValueError(f"{block_id}: duplicated same-side insertion for {side}:{unknown}")
            seen_side_unknown.add(marker)
            row[local_index[unknown]] += coeff
        nonzero = [value for value in row if value]
        if not nonzero:
            raise ValueError(f"{block_id}: generated a structurally empty compatibility row")
        if not any(value > 0 for value in nonzero) or not any(value < 0 for value in nonzero):
            raise ValueError(f"{block_id}: compatibility row does not contain both signs")
        matrix_rows.append(row)
    return matrix_rows


def _build_target_line_blocks_for_window(
    *,
    shared: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    builder_variant: str,
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    point_representatives: dict[str, list[str]],
    start_sample: Fraction,
    end_sample: Fraction,
    window_tag: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, tuple[tuple[str, str, tuple[str, ...]], ...]]] = set()
    for line in shared["grouped"]["lines"]:
        allowed_point_ids = {endpoint["point_id"] for endpoint in line["endpoints"]}
        representative_key = _unordered_target_line_pair_key(
            line["id"],
            [
                {
                    "point_id": endpoint["point_id"],
                    "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
                    "point_coordinates": list(endpoint["point_coordinates"]),
                }
                for endpoint in line["endpoints"]
            ],
            window_tag="ordinary",
        )
        if window_tag == "ordinary":
            seen_pairs.add(representative_key)
            blocks.append(_build_generic_line_block(line, captures, builder_variant=builder_variant))
            records.append(
                {
                    "line_id": line["id"],
                    "source_line_id": line["id"],
                    "window_tag": window_tag,
                    "kind": "representative_grouped_line",
                    "endpoints": [
                        {
                            "point_id": endpoint["point_id"],
                            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
                            "point_coordinates": list(endpoint["point_coordinates"]),
                        }
                        for endpoint in line["endpoints"]
                    ],
                }
            )
        for branch_index, orbit_expr in enumerate(line.get("metadata", {}).get("source_orbit", []), start=1):
            pieces = [piece.strip() for piece in orbit_expr.split(",")]
            if len(pieces) != 3:
                continue
            endpoint_entries = []
            for sample in (start_sample, end_sample):
                coords = [
                    str(_parse_line_orbit_coordinate(piece, sample))
                    for piece in pieces
                ]
                entry = _resolve_target_capture_entry(
                    point_coordinates=coords,
                    allowed_point_ids=allowed_point_ids,
                    catalog=catalog,
                    point_representatives=point_representatives,
                    captures=captures,
                    port=stage1_backend(),
                    module=module,
                    group_id=group_id,
                    ssg_dict=ssg_dict,
                    ctx=ctx,
                    mode=mode,
                )
                if entry is None:
                    endpoint_entries = []
                    break
                endpoint_entries.append(entry)
            if len(endpoint_entries) != 2:
                continue
            if len({entry["point_id"] for entry in endpoint_entries}) != 2:
                continue
            pair_key = _unordered_target_line_pair_key(line["id"], endpoint_entries, window_tag=window_tag)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            line_id = f"{line['id']}__{window_tag}_{branch_index:02d}"
            try:
                block = _build_target_restriction_line_block(
                    source_line=line,
                    block_id=line_id,
                    endpoint_entries=endpoint_entries,
                    captures=captures,
                    builder_variant=builder_variant,
                    endpoint_label_key="point_id",
                )
            except Exception as exc:
                records.append(
                    {
                        "line_id": line_id,
                        "source_line_id": line["id"],
                        "window_tag": window_tag,
                        "kind": "orbit_window_skipped",
                        "endpoints": endpoint_entries,
                        "skipped_reason": str(exc),
                    }
                )
                continue
            blocks.append(block)
            records.append(
                {
                    "line_id": line_id,
                    "source_line_id": line["id"],
                    "window_tag": window_tag,
                    "kind": "orbit_window_restriction_class_line",
                    "endpoints": endpoint_entries,
                }
            )
    return blocks, records


def _build_target_real_line_blocks(
    *,
    shared: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    builder_variant: str,
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    point_representatives: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return _build_target_line_blocks_for_window(
        shared=shared,
        captures=captures,
        module=module,
        group_id=group_id,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
        builder_variant=builder_variant,
        catalog=catalog,
        point_representatives=point_representatives,
        start_sample=Fraction(0, 1),
        end_sample=Fraction(1, 1),
        window_tag="ordinary",
    )


def _collect_same_point_monodromy_pairs(
    *,
    shared: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    point_representatives: dict[str, list[str]],
) -> list[dict[str, Any]]:
    target_point_ids = set(shared["target_point_ids"])
    port = stage1_backend()
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, str]]] = set()
    for line in shared["grouped"]["lines"]:
        for branch_index, orbit_expr in enumerate(line.get("metadata", {}).get("source_orbit", []), start=1):
            pieces = [piece.strip() for piece in orbit_expr.split(",")]
            if len(pieces) != 3:
                continue
            endpoint_entries = []
            for sample in (Fraction(0, 1), Fraction(1, 1)):
                coords = [str(_parse_line_orbit_coordinate(piece, sample)) for piece in pieces]
                entry = _resolve_target_capture_entry(
                    point_coordinates=coords,
                    allowed_point_ids=target_point_ids,
                    catalog=catalog,
                    point_representatives=point_representatives,
                    captures=captures,
                    port=port,
                    module=module,
                    group_id=group_id,
                    ssg_dict=ssg_dict,
                    ctx=ctx,
                    mode=mode,
                )
                if entry is None:
                    endpoint_entries = []
                    break
                endpoint_entries.append(entry)
            if len(endpoint_entries) != 2:
                continue
            left_entry, right_entry = endpoint_entries
            if left_entry["point_id"] != right_entry["point_id"]:
                continue
            if left_entry["capture_id"] == right_entry["capture_id"]:
                continue
            key = (
                line["id"],
                left_entry["point_id"],
                tuple(sorted((left_entry["capture_id"], right_entry["capture_id"]))),
            )
            if key in seen:
                continue
            seen.add(key)
            pairs.append(
                {
                    "line_family": line["id"],
                    "source_line_id": line["id"],
                    "branch_index": branch_index,
                    "point_id": left_entry["point_id"],
                    "left_capture_id": left_entry["capture_id"],
                    "right_capture_id": right_entry["capture_id"],
                    "left_coordinates": list(left_entry["point_coordinates"]),
                    "right_coordinates": list(right_entry["point_coordinates"]),
                    "orbit_expr": orbit_expr,
                }
            )
    return pairs


def _sample_branch_point_from_orbit_expr(
    orbit_expr: str,
    sample: Fraction = LINE_SAMPLE,
) -> list[float]:
    pieces = [piece.strip() for piece in orbit_expr.split(",")]
    if len(pieces) != 3:
        raise ValueError(f"invalid orbit expression for line branch sample: {orbit_expr!r}")
    return [float(_parse_line_orbit_coordinate(piece, sample)) for piece in pieces]


def _build_target_monodromy_block_from_pair(
    *,
    pair: dict[str, Any],
    captures: dict[str, Any],
    line_raw: dict[str, Any],
    builder_variant: str,
) -> dict[str, Any]:
    port = stage1_backend()
    point_id = str(pair["point_id"])
    left_capture_id = str(pair["left_capture_id"])
    right_capture_id = str(pair["right_capture_id"])
    left_raw = captures[left_capture_id]
    right_raw = captures[right_capture_id]
    matched_left = port.matched_unitary_indices(line_raw, left_raw)
    matched_right = port.matched_unitary_indices(line_raw, right_raw)
    monodromy_field = "character"
    line_basis_labels = [
        f"{pair['source_line_id']}_M{pair['branch_index']:02d}_R{i}"
        for i in range(1, len(line_raw[monodromy_field]) + 1)
    ]
    line_basis_matrix = port._exact_basis_matrix_from_capture(
        line_raw,
        monodromy_field,
        manifold_id=pair["source_line_id"],
    )
    if len(left_raw["linear_character"]) != len(right_raw["linear_character"]):
        raise ValueError(
            f"same-point monodromy pair {point_id}: mismatched rep counts "
            f"{len(left_raw['linear_character'])} vs {len(right_raw['linear_character'])}"
        )
    local_unknown_ordering = [
        f"{point_id}_R{rep_index}"
        for rep_index in range(1, len(left_raw["linear_character"]) + 1)
    ]
    endpoint_decompositions = {
        point_id: [
            {
                "rep_id": f"{point_id}_R{rep_index}",
                "rep_degree": int(left_raw["rep_degree"][rep_index - 1]),
                "torsion": int(left_raw["torsion"][rep_index - 1]),
                "decomposition_on_line_basis_left": {},
                "decomposition_on_line_basis_right": {},
            }
            for rep_index in range(1, len(left_raw["linear_character"]) + 1)
        ],
    }
    left_decompositions_by_rep: dict[str, dict[str, int]] = {}
    right_decompositions_by_rep: dict[str, dict[str, int]] = {}
    for rep_index in range(1, len(left_raw[monodromy_field]) + 1):
        rep_id = f"{point_id}_R{rep_index}"
        left_restricted = port._exact_restriction_vector(
            line_raw,
            left_raw,
            matched_left,
            field=monodromy_field,
            parent_manifold_id=pair["source_line_id"],
            child_manifold_id=left_capture_id,
            rep_id=rep_id,
        )
        right_restricted = port._exact_restriction_vector(
            line_raw,
            right_raw,
            matched_right,
            field=monodromy_field,
            parent_manifold_id=pair["source_line_id"],
            child_manifold_id=right_capture_id,
            rep_id=rep_id,
        )
        left_coeffs = port.solve_unique_integer_decomposition(
            line_basis_matrix,
            left_restricted,
            mode=port._mode_label_from_raw(left_raw),
            manifold_id=pair["source_line_id"],
            endpoint_id=left_capture_id,
            rep_id=rep_id,
            field=monodromy_field,
        )
        right_coeffs = port.solve_unique_integer_decomposition(
            line_basis_matrix,
            right_restricted,
            mode=port._mode_label_from_raw(right_raw),
            manifold_id=pair["source_line_id"],
            endpoint_id=right_capture_id,
            rep_id=rep_id,
            field=monodromy_field,
        )
        left_decompositions_by_rep[rep_id] = {
            basis_label: coeff
            for basis_label, coeff in zip(line_basis_labels, left_coeffs)
            if coeff
        }
        right_decompositions_by_rep[rep_id] = {
            basis_label: coeff
            for basis_label, coeff in zip(line_basis_labels, right_coeffs)
            if coeff
        }
    for rep in endpoint_decompositions[point_id]:
        rep_id = rep["rep_id"]
        rep["decomposition_on_line_basis_left"] = left_decompositions_by_rep[rep_id]
        rep["decomposition_on_line_basis_right"] = right_decompositions_by_rep[rep_id]
    equations = []
    for basis_label in line_basis_labels:
        coeff_by_unknown: dict[str, int] = {}
        left_support = []
        right_support = []
        for rep_id in local_unknown_ordering:
            left_coeff = int(left_decompositions_by_rep[rep_id].get(basis_label, 0))
            right_coeff = int(right_decompositions_by_rep[rep_id].get(basis_label, 0))
            net = left_coeff - right_coeff
            if left_coeff:
                left_support.append({"rep_id": rep_id, "coeff": left_coeff})
            if right_coeff:
                right_support.append({"rep_id": rep_id, "coeff": right_coeff})
            if net:
                coeff_by_unknown[rep_id] = net
        terms = []
        for rep_id in local_unknown_ordering:
            coeff = coeff_by_unknown.get(rep_id, 0)
            if coeff > 0:
                terms.append({"unknown": rep_id, "coeff": coeff, "side": "left_capture"})
            elif coeff < 0:
                terms.append({"unknown": rep_id, "coeff": coeff, "side": "right_capture"})
        if not terms:
            continue
        equations.append(
            {
                "basis_id": basis_label,
                "terms": terms,
                "row_kind": "same_point_monodromy_line_basis",
                "builder_variant": builder_variant,
                "target_line_block_kind": "monodromy_line",
                "line_window_kind": "monodromy",
                "source_line_family": pair["line_family"],
                "source_line_id": pair["source_line_id"],
                "endpoint_capture_ids": [left_capture_id, right_capture_id],
                "monodromy_field": monodromy_field,
                "monodromy_pair": {
                    "point_id": point_id,
                    "left_capture_id": left_capture_id,
                    "right_capture_id": right_capture_id,
                    "left_coordinates": list(pair["left_coordinates"]),
                    "right_coordinates": list(pair["right_coordinates"]),
                    "line_family": pair["line_family"],
                    "branch_index": int(pair["branch_index"]),
                },
                "left_support": left_support,
                "right_support": right_support,
            }
        )
    block_id = f"{pair['source_line_id']}__monodromy_{point_id}_{pair['branch_index']:02d}"
    matrix_rows = _build_block_matrix_rows_from_equations(
        local_unknown_ordering,
        equations,
        block_id=block_id,
    )
    return {
        "status": "fallback_same_point_monodromy_restriction_classes",
        "line_id": block_id,
        "source_line_id": pair["source_line_id"],
        "endpoint_ids": [point_id],
        "line_sample_point": line_raw.get("capture_sample_point", line_raw.get("sample_point")),
        "line_parametrization": None,
        "line_symmetry_summary": None,
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
        "line_basis_labels": line_basis_labels,
        "builder_variant": builder_variant,
        "target_line_block_kind": "monodromy_line",
        "compatibility_builder_kind": "generic_same_shell_target_monodromy_pair_builder",
        "monodromy_field_used": monodromy_field,
        "restriction_class_builder": {
            "builder_kind": "generic_same_shell_target_monodromy_pair_builder",
            "endpoint_capture_ids": [left_capture_id, right_capture_id],
            "point_id": point_id,
            "monodromy_field": monodromy_field,
        },
    }


def _build_target_monodromy_line_blocks(
    *,
    shared: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    builder_variant: str,
    catalog: dict[tuple[str, str, str], list[dict[str, Any]]],
    point_representatives: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocks: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    port = stage1_backend()
    branch_line_raw_cache: dict[tuple[str, int], dict[str, Any]] = {}
    for pair in _collect_same_point_monodromy_pairs(
        shared=shared,
        captures=captures,
        module=module,
        group_id=group_id,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
        catalog=catalog,
        point_representatives=point_representatives,
    ):
        line_cache_key = (pair["source_line_id"], int(pair["branch_index"]))
        line_raw = branch_line_raw_cache.get(line_cache_key)
        if line_raw is None:
            line_raw = port.capture_little_group(
                module,
                group_id,
                ssg_dict,
                ctx,
                mode,
                pair["source_line_id"],
                _sample_branch_point_from_orbit_expr(pair["orbit_expr"]),
            )
            line_raw = {
                **line_raw,
                "capture_sample_point": _sample_branch_point_from_orbit_expr(pair["orbit_expr"]),
                "capture_canonicalization_source": "generic_same_shell_monodromy_branch_sample",
            }
            branch_line_raw_cache[line_cache_key] = line_raw
        try:
            block = _build_target_monodromy_block_from_pair(
                pair=pair,
                captures=captures,
                line_raw=line_raw,
                builder_variant=builder_variant,
            )
        except Exception as exc:
            records.append(
                {
                    "line_id": f"{pair['source_line_id']}__monodromy_{pair['point_id']}_{pair['branch_index']:02d}",
                    "source_line_id": pair["source_line_id"],
                    "window_tag": "monodromy",
                    "kind": "same_point_monodromy_skipped",
                    "pair": pair,
                    "skipped_reason": str(exc),
                }
            )
            continue
        blocks.append(block)
        records.append(
            {
                "line_id": block["line_id"],
                "source_line_id": pair["source_line_id"],
                "window_tag": "monodromy",
                "kind": "same_point_monodromy_restriction_class_line",
                "pair": pair,
            }
        )
    return blocks, records


def _build_same_shell_target_row_language(
    *,
    shared: dict[str, Any],
    compatibility: dict[str, Any],
    bs_analysis: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    builder_variant: str,
) -> dict[str, Any]:
    port = stage1_backend()
    group_id = str(shared["group_id"])
    current_unknown_ordering = list(bs_analysis["unknown_ordering"])
    target_point_ids = list(shared["target_point_ids"])
    catalog, point_representatives = _build_target_capture_catalog(shared=shared)
    ordinary_line_blocks, ordinary_records = _build_target_real_line_blocks(
        shared=shared,
        captures=captures,
        module=module,
        group_id=group_id,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
        builder_variant=builder_variant,
        catalog=catalog,
        point_representatives=point_representatives,
    )
    monodromy_line_blocks, monodromy_records = _build_target_monodromy_line_blocks(
        shared=shared,
        captures=captures,
        module=module,
        group_id=group_id,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
        builder_variant=builder_variant,
        catalog=catalog,
        point_representatives=point_representatives,
    )
    target_capture_ids = _ordered_target_capture_ids(
        shared=shared,
        catalog=catalog,
    )
    target_line_blocks = ordinary_line_blocks + monodromy_line_blocks
    availability = "available" if target_line_blocks else "blocked"
    blocker_stage = None if target_line_blocks else "generic_target_compatibility_missing_line_blocks"
    blocker = None if target_line_blocks else "generic same-shell published target compatibility could not assemble any target line blocks"
    target_compatibility = None
    target_bs_analysis = None
    target_unknown_ordering: list[str] = []
    if availability == "available":
        target_compatibility = port.build_global_compatibility(target_line_blocks, target_point_ids)
        target_bs_analysis = port.analyze_kernel(target_compatibility)
        target_unknown_ordering = list(target_compatibility["global_unknown_ordering"])
    target_bs_rank = None if target_bs_analysis is None else int(len(target_bs_analysis.get("basis_vectors", [])))
    return {
        "group": group_id,
        "mode": mode,
        "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
        "object_kind": "generic_target_row_language_compatibility",
        "availability": availability,
        "source_unknown_count": len(current_unknown_ordering),
        "current_unknown_count": len(current_unknown_ordering),
        "target_unknown_count": len(target_unknown_ordering),
        "target_unknown_ordering": target_unknown_ordering,
        "target_capture_ids": list(target_capture_ids),
        "projection_indices": None,
        "target_projection_matrix_shape": None,
        "target_projection_matrix": None,
        "compatibility_matrix_shape": list(compatibility.get("matrix_shape", [])),
        "object_semantics": "same_shell_published_target_row_language",
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "target_compatibility": target_compatibility,
        "target_bs_analysis": target_bs_analysis,
        "target_compatibility_shape": (
            list(target_compatibility.get("matrix_shape", []))
            if target_compatibility is not None
            else None
        ),
        "target_bs_rank": target_bs_rank,
        "ordinary_line_block_count": len(ordinary_line_blocks),
        "monodromy_line_block_count": len(monodromy_line_blocks),
        "current_unknown_ordering": current_unknown_ordering,
        "evidence": {
            "target_point_ids": list(target_point_ids),
            "target_capture_ids": list(target_capture_ids),
            "ordinary_line_block_count": len(ordinary_line_blocks),
            "monodromy_line_block_count": len(monodromy_line_blocks),
            "target_compatibility_shape": (
                list(target_compatibility.get("matrix_shape", []))
                if target_compatibility is not None
                else None
            ),
            "target_bs_rank": target_bs_rank,
            "ordinary_target_line_records": ordinary_records,
            "monodromy_line_records": monodromy_records,
        },
        "_compatibility_rows": (
            list(target_compatibility.get("global_matrix_rows", []))
            if target_compatibility is not None
            else []
        ),
    }


def _build_generic_target_row_language(
    *,
    group_id: str,
    mode: str,
    target_point_ids: list[str],
    current_unknown_ordering: list[str],
    compatibility: dict[str, Any],
    point_row_translation: dict[str, Any] | None,
) -> dict[str, Any]:
    del point_row_translation
    return {
        "group": group_id,
        "mode": mode,
        "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
        "object_kind": "generic_target_row_language_compatibility",
        "availability": "blocked",
        "source_unknown_count": len(current_unknown_ordering),
        "current_unknown_count": len(current_unknown_ordering),
        "target_unknown_count": None,
        "target_unknown_ordering": [],
        "projection_indices": None,
        "target_projection_matrix_shape": None,
        "target_projection_matrix": None,
        "compatibility_matrix_shape": list(compatibility.get("matrix_shape", [])),
        "object_semantics": "same_shell_published_target_row_language",
        "blocker_stage": "generic_target_row_language_requires_shared_geometry_bundle",
        "blocker": "generic target row language requires shared geometry plus capture metadata",
        "target_compatibility": None,
        "target_bs_analysis": None,
        "ordinary_line_block_count": 0,
        "monodromy_line_block_count": 0,
        "current_unknown_ordering": list(current_unknown_ordering),
        "evidence": {
            "target_point_ids": list(target_point_ids),
        },
        "_compatibility_rows": [],
    }


def _reindex_candidate_to_target_unknown_ordering(
    candidate: dict[str, Any],
    current_unknown_ordering: list[str],
    target_unknown_ordering: list[str],
) -> list[int]:
    values = {
        label: int(candidate["unknown_vector"][index])
        for index, label in enumerate(current_unknown_ordering)
    }
    return [int(values.get(label, 0)) for label in target_unknown_ordering]


def _target_compatibility_row_payload(
    row_index: int,
    row: dict[str, Any],
    unknown_ordering: list[str],
    residual: int | None = None,
) -> dict[str, Any]:
    nonzero_columns = []
    coefficients = []
    column_labels = []
    for index, (label, coeff) in enumerate(zip(unknown_ordering, row["matrix_row"])):
        coeff_int = int(coeff)
        if coeff_int == 0:
            continue
        nonzero_columns.append(index)
        coefficients.append(coeff_int)
        column_labels.append(label)
    row_kind = row.get("target_line_block_kind") or row.get("equation_metadata", {}).get("target_line_block_kind")
    return {
        "row_index": int(row_index),
        "line_id": row.get("line_id"),
        "source_line_id": row.get("source_line_id", row.get("line_id")),
        "basis_id": row.get("basis_id"),
        "row_kind": row.get("row_kind"),
        "target_line_block_kind": row_kind,
        "nonzero_columns": nonzero_columns,
        "column_labels": column_labels,
        "coefficients": coefficients,
        "signature_label": row.get("basis_id"),
        **({"residual": int(residual)} if residual is not None else {}),
    }


def _build_same_shell_target_quotient(
    *,
    target_row_language: dict[str, Any],
    induced: dict[str, Any],
) -> dict[str, Any]:
    port = stage1_backend()
    if target_row_language.get("availability") != "available":
        return {
            "availability": "blocked",
            "blocker_stage": target_row_language.get("blocker_stage"),
            "blocker": target_row_language.get("blocker"),
            "object_semantics": "generic_target_row_language_quotient_candidate_blocked",
            "reported_dbs_semantics": None,
            "reported_dai_semantics": "unresolved_target_row_language_blocked",
            "classification_derivation_basis": None,
            "same_shell_rank_check": None,
            "verification_status": "target_row_language_blocked",
            "same_shell_semantics": "target_row_language_blocked",
            "quotient_semantics": "blocked_before_target_row_language_quotient",
        }

    target_bs_analysis = target_row_language.get("target_bs_analysis") or {}
    target_compatibility = target_row_language.get("target_compatibility") or {}
    target_unknown_ordering = list(target_row_language.get("target_unknown_ordering", []))
    current_unknown_ordering = list(target_row_language.get("current_unknown_ordering", []))
    compatibility_rows = list(target_compatibility.get("global_matrix_rows", []))
    basis_vectors = [item["vector"] for item in target_bs_analysis.get("basis_vectors", [])]
    target_bs_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in basis_vectors])
        if basis_vectors
        else sp.zeros(len(target_unknown_ordering), 0)
    )
    target_bs_rank = int(target_bs_matrix.cols)

    coords = []
    compatible_candidates = []
    compatible_target_vectors = []
    rejected_candidates = []
    embedding_failures = []
    failing_row_payloads: list[dict[str, Any]] = []
    max_absolute_residual = 0
    for candidate in induced["candidates"]:
        target_vector = _reindex_candidate_to_target_unknown_ordering(
            candidate,
            current_unknown_ordering,
            target_unknown_ordering,
        )
        target_residual_rows = []
        for row_index, item in enumerate(compatibility_rows):
            residual = int(sum(int(left) * int(right) for left, right in zip(item["matrix_row"], target_vector)))
            if residual:
                max_absolute_residual = max(max_absolute_residual, abs(residual))
                target_residual_rows.append(
                    _target_compatibility_row_payload(
                        row_index,
                        item,
                        target_unknown_ordering,
                        residual=residual,
                    )
                )
        if target_residual_rows:
            failing_row_payloads.extend(target_residual_rows)
            rejected_candidates.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "compatibility_zero_in_current_rows": bool(candidate.get("compatibility_zero", False)),
                    "reason": "same_shell_target_compatibility_nonzero",
                    "max_abs_residual": max(abs(item["residual"]) for item in target_residual_rows),
                    "nonzero_residual_rows": target_residual_rows,
                }
            )
            continue
        try:
            coords.append(_solve_ai_in_bs_coordinates(target_bs_matrix, target_vector))
            compatible_candidates.append(candidate)
            compatible_target_vectors.append(target_vector)
        except Exception as exc:  # pragma: no cover - diagnostic path
            embedding_failures.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "reason": f"target_row_language_embedding_failed: {exc}",
                }
            )

    ai_in_bs = sp.Matrix(coords).T if coords else sp.zeros(target_bs_rank, 0)
    smith_data = port.swyckoff_k.smith_normal_form(
        [[int(value) for value in row] for row in ai_in_bs.tolist()]
    )
    smith_matrix = sp.Matrix(smith_data[0]) if ai_in_bs.cols else sp.zeros(target_bs_rank, 0)
    smith_diag = _smith_diagonal(smith_matrix)
    ai_image_rank_in_bs = len(smith_diag)
    target_ai_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_target_vectors])
        if compatible_target_vectors
        else sp.zeros(len(target_unknown_ordering), 0)
    )
    target_ai_rank = int(target_ai_matrix.rank())
    free_rank = int(target_bs_rank - ai_image_rank_in_bs)
    finite_part = [value for value in smith_diag if value > 1]
    classification = _quotient_group_string(free_rank, finite_part)
    availability = "available" if compatible_candidates and not embedding_failures else "blocked"
    blocker_stage = None
    blocker = None
    if induced["failure_count"]:
        blocker_stage = "generic_target_row_language_induction_failure"
        blocker = "generic target quotient induction failed for one or more local-library generators"
    elif embedding_failures:
        blocker_stage = "generic_target_row_language_embedding_failure"
        blocker = "target-row-language AI-in-BS embedding failed for at least one compatibility-zero candidate"
    elif not compatible_candidates:
        blocker_stage = "generic_target_row_language_zero_compatible_candidates"
        blocker = "no induced candidate satisfies the same-shell target compatibility"
    elif rejected_candidates:
        blocker_stage = "generic_target_row_language_nonzero_residual_candidates"
        blocker = "one or more induced candidates violate the same-shell target compatibility"
    verification_status = (
        "semantic_pass"
        if availability == "available" and target_bs_rank == target_ai_rank
        else "semantic_fail_dbs_dai_gap"
        if availability == "available"
        else "target_row_language_quotient_blocked"
    )
    unique_offending_rows: list[dict[str, Any]] = []
    seen_rows: set[int] = set()
    for row in failing_row_payloads:
        row_index = int(row["row_index"])
        if row_index in seen_rows:
            continue
        seen_rows.add(row_index)
        unique_offending_rows.append(row)
        if len(unique_offending_rows) >= 20:
            break
    return {
        "availability": availability,
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "dBS": target_bs_rank,
        "dAI": target_ai_rank,
        "ai_image_rank_in_bs": ai_image_rank_in_bs,
        "dbs_dai_gap": (
            int(target_bs_rank - target_ai_rank)
        ),
        "dbs_minus_ai_image_rank": (
            int(target_bs_rank - ai_image_rank_in_bs)
        ),
        "free_rank": free_rank,
        "finite_part": finite_part,
        "classification": classification,
        "smith_diagonal_nonzero": smith_diag,
        "reported_dbs_semantics": "same_shell_target_row_language_bs_rank",
        "reported_dai_semantics": "same_shell_target_ai_rank",
        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs_on_same_shell_target_row_language",
        "same_shell_rank_check": {
            "dBS": target_bs_rank,
            "dAI": target_ai_rank,
            "ai_image_rank_in_bs": ai_image_rank_in_bs,
        },
        "ai_candidate_count": induced["candidate_count"],
        "ai_candidate_count_used": len(compatible_candidates),
        "ai_failure_count": induced["failure_count"],
        "ai_incompatible_count": len(rejected_candidates),
        "ai_embedding_failure_count": len(embedding_failures),
        "ai_incompatible_candidates": rejected_candidates,
        "failing_candidate_examples": rejected_candidates[:5],
        "target_compatibility_exact_pass_count": len(compatible_candidates),
        "target_compatibility_fail_count": len(rejected_candidates),
        "target_compatibility_max_absolute_residual": int(max_absolute_residual),
        "offending_rows_summary": unique_offending_rows,
        "ai_embedding_failures": embedding_failures,
        "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
        "object_semantics": "same_shell_published_target_quotient_candidate",
        "same_shell_semantics": "published_target_candidate_not_yet_verified",
        "quotient_semantics": "same_shell_published_target_quotient_candidate",
        "verification_status": verification_status,
        "target_unknown_count": len(target_unknown_ordering),
        "target_unknown_ordering": list(target_row_language["target_unknown_ordering"]),
        "target_projection_matrix_shape": target_row_language.get("target_projection_matrix_shape"),
        "target_row_language_evidence": dict(target_row_language.get("evidence", {})),
        "target_compatibility_shape": list(target_compatibility.get("matrix_shape", [])),
        "target_compatibility_row_count": len(compatibility_rows),
    }


def _build_generic_target_quotient(
    *,
    target_row_language: dict[str, Any],
    compatibility: dict[str, Any],
    induced: dict[str, Any],
) -> dict[str, Any]:
    del compatibility
    return _build_same_shell_target_quotient(
        target_row_language=target_row_language,
        induced=induced,
    )


def _build_quotient_from_candidates(
    point_ids: list[str],
    unknown_ordering: list[str],
    bs_analysis: dict[str, Any],
    compatibility: dict[str, Any],
    induced: dict[str, Any],
) -> dict[str, Any]:
    port = stage1_backend()
    basis_vectors = [item["vector"] for item in bs_analysis["basis_vectors"]]
    bs_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in basis_vectors])
        if basis_vectors
        else sp.zeros(len(unknown_ordering), 0)
    )
    point_indices = _point_row_indices(unknown_ordering, point_ids)
    point_unknown_ordering = [unknown_ordering[index] for index in point_indices]
    point_bs_matrix = (
        sp.Matrix.hstack(*[sp.Matrix([int(vector[index]) for index in point_indices]) for vector in basis_vectors])
        if basis_vectors
        else sp.zeros(len(point_indices), 0)
    )
    full_bs_rank = int(bs_matrix.cols)
    bs_rank = int(point_bs_matrix.rank())
    if bs_rank != full_bs_rank:
        raise ValueError(
            "generic point-shell projection lost rank; direct quotient on projected current rows is ambiguous "
            f"(full={full_bs_rank}, point={bs_rank})"
        )
    coords = []
    compatible_candidates = []
    compatible_point_vectors = []
    rejected_candidates = []
    embedding_failures = []
    compatibility_rows = list(compatibility.get("global_matrix_rows", []))
    for candidate in induced["candidates"]:
        if not candidate.get("compatibility_zero", False):
            residual_rows = []
            for item in candidate.get("nonzero_residual_rows", []):
                row_index = int(item["row_index"])
                if 0 <= row_index < len(compatibility_rows):
                    residual_rows.append(
                        {
                            "row_index": row_index,
                            "residual": int(item["residual"]),
                            "row": compatibility_rows[row_index],
                        }
                    )
                else:
                    residual_rows.append(
                        {
                            "row_index": row_index,
                            "residual": int(item["residual"]),
                        }
                    )
            rejected_candidates.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "reason": "nonzero_compatibility_residual_in_native_current_rows",
                    "compatibility_zero": False,
                    "compatibility_residual_norm": candidate.get("compatibility_residual_norm"),
                    "nonzero_residual_rows": residual_rows,
                }
            )
            continue
        point_vector = [int(candidate["unknown_vector"][index]) for index in point_indices]
        try:
            coords.append(_solve_ai_in_bs_coordinates(point_bs_matrix, point_vector))
            compatible_candidates.append(candidate)
            compatible_point_vectors.append(point_vector)
        except Exception as exc:  # pragma: no cover - diagnostic path
            embedding_failures.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "reason": f"target_point_shell_embedding_failed: {exc}",
                }
            )
    ai_in_bs = sp.Matrix(coords).T if coords else sp.zeros(bs_rank, 0)
    smith_data = port.swyckoff_k.smith_normal_form([[int(value) for value in row] for row in ai_in_bs.tolist()])
    smith_matrix = sp.Matrix(smith_data[0]) if ai_in_bs.cols else sp.zeros(bs_rank, 0)
    smith_diag = _smith_diagonal(smith_matrix)
    ai_image_rank_in_bs = len(smith_diag)
    projected_ai_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_point_vectors])
        if compatible_point_vectors
        else sp.zeros(len(point_unknown_ordering), 0)
    )
    projected_target_ai_rank = int(projected_ai_matrix.rank())
    surviving_finite_part = [value for value in smith_diag if value > 1]
    surviving_free_rank = int(bs_rank - ai_image_rank_in_bs)
    surviving_classification = _quotient_group_string(surviving_free_rank, surviving_finite_part)
    final_available = not (rejected_candidates or embedding_failures or induced["failure_count"])
    return {
        "object_semantics": "projected_point_shell_diagnostic_quotient",
        "dBS": bs_rank,
        "dAI": None,
        "ai_image_rank_in_bs": ai_image_rank_in_bs if final_available else None,
        "projected_target_ai_rank": projected_target_ai_rank if final_available else None,
        "dbs_dai_gap": None,
        "dbs_minus_ai_image_rank": int(bs_rank - ai_image_rank_in_bs) if final_available else None,
        "free_rank": surviving_free_rank if final_available else None,
        "finite_part": surviving_finite_part if final_available else [],
        "classification": surviving_classification if final_available else None,
        "surviving_ai_rank": ai_image_rank_in_bs,
        "surviving_dbs_ai_gap": int(bs_rank - ai_image_rank_in_bs),
        "surviving_free_rank": surviving_free_rank,
        "surviving_finite_part": surviving_finite_part,
        "surviving_classification": surviving_classification,
        "final_dai_available": final_available,
        "smith_diagonal_nonzero": smith_diag,
        "reported_dbs_semantics": "projected_point_shell_rank",
        "reported_dai_semantics": "unresolved_do_not_promote_to_target",
        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs_on_projected_point_shell",
        "same_shell_semantics": "diagnostic_projected_point_shell_attempt",
        "quotient_semantics": "projected_point_shell_diagnostic_quotient",
        "same_shell_rank_check": {
            "dBS": bs_rank if final_available else None,
            "dAI": None,
            "ai_image_rank_in_bs": ai_image_rank_in_bs if final_available else None,
            "diagnostic_projected_target_ai_rank": (
                projected_target_ai_rank if final_available else None
            ),
        },
        "ai_candidate_count": induced["candidate_count"],
        "ai_candidate_count_used": len(compatible_candidates),
        "ai_failure_count": induced["failure_count"],
        "ai_incompatible_count": len(rejected_candidates),
        "ai_embedding_failure_count": len(embedding_failures),
        "ai_incompatible_candidates": rejected_candidates,
        "ai_embedding_failures": embedding_failures,
        "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
        "compatibility_check_mode": "point_shell_projection_over_full_kernel_basis",
        "full_shell_rank": full_bs_rank,
        "point_shell_rank": bs_rank,
        "point_unknown_count": len(point_unknown_ordering),
        "point_unknown_ordering": point_unknown_ordering,
        "native_target_point_ids": list(point_ids),
    }


def _structured_projection_rank_loss(message: str) -> dict[str, Any]:
    match = re.search(r"\(full=(\d+), point=(\d+)\)", message)
    evidence: dict[str, Any] = {}
    if match is not None:
        evidence = {
            "full_rank": int(match.group(1)),
            "projected_rank": int(match.group(2)),
        }
    return evidence


def _candidate_residual_payload(
    candidate: dict[str, Any],
    compatibility_rows: list[Any],
) -> dict[str, Any]:
    residual_rows = []
    for item in candidate.get("nonzero_residual_rows", []):
        row_index = int(item["row_index"])
        if 0 <= row_index < len(compatibility_rows):
            residual_rows.append(
                {
                    "row_index": row_index,
                    "residual": int(item["residual"]),
                    "row": compatibility_rows[row_index],
                }
            )
        else:
            residual_rows.append(
                {
                    "row_index": row_index,
                    "residual": int(item["residual"]),
                }
            )
    return {
        "generator_id": candidate.get("generator_id"),
        "family_letter": candidate.get("family_letter"),
        "reason": "nonzero_compatibility_residual_in_native_current_rows",
        "compatibility_zero": False,
        "compatibility_residual_norm": candidate.get("compatibility_residual_norm"),
        "nonzero_residual_rows": residual_rows,
    }


def _build_same_shell_quotient_from_candidates(
    unknown_ordering: list[str],
    bs_analysis: dict[str, Any],
    compatibility: dict[str, Any],
    induced: dict[str, Any],
) -> dict[str, Any]:
    port = stage1_backend()
    basis_vectors = [item["vector"] for item in bs_analysis["basis_vectors"]]
    bs_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in basis_vectors])
        if basis_vectors
        else sp.zeros(len(unknown_ordering), 0)
    )
    bs_rank = int(bs_matrix.cols)
    coords = []
    compatible_candidates = []
    compatible_unknown_vectors = []
    rejected_candidates = []
    embedding_failures = []
    compatibility_rows = list(compatibility.get("global_matrix_rows", []))

    for candidate in induced["candidates"]:
        if not candidate.get("compatibility_zero", False):
            rejected_candidates.append(_candidate_residual_payload(candidate, compatibility_rows))
            continue
        try:
            coords.append(_solve_ai_in_bs_coordinates(bs_matrix, candidate["unknown_vector"]))
            compatible_candidates.append(candidate)
            compatible_unknown_vectors.append([int(value) for value in candidate["unknown_vector"]])
        except Exception as exc:  # pragma: no cover - diagnostic path
            embedding_failures.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "reason": f"same_shell_embedding_failed: {exc}",
                }
            )

    ai_in_bs = sp.Matrix(coords).T if coords else sp.zeros(bs_rank, 0)
    smith_data = port.swyckoff_k.smith_normal_form(
        [[int(value) for value in row] for row in ai_in_bs.tolist()]
    )
    smith_matrix = sp.Matrix(smith_data[0]) if ai_in_bs.cols else sp.zeros(bs_rank, 0)
    smith_diag = _smith_diagonal(smith_matrix)
    ai_image_rank_in_bs = len(smith_diag)
    same_shell_target_matrix = (
        sp.Matrix.hstack(*[sp.Matrix(vector) for vector in compatible_unknown_vectors])
        if compatible_unknown_vectors
        else sp.zeros(len(unknown_ordering), 0)
    )
    same_shell_target_rank = int(same_shell_target_matrix.rank())
    free_rank = int(bs_rank - ai_image_rank_in_bs)
    finite_part = [value for value in smith_diag if value > 1]
    classification = _quotient_group_string(free_rank, finite_part)
    availability = "available" if not embedding_failures and not induced["failure_count"] else "blocked"
    blocker = None
    blocker_stage = None
    if induced["failure_count"]:
        blocker_stage = "generic_same_shell_target_induction_failure"
        blocker = (
            "generic same-shell target induction failed for one or more local-library generators"
        )
    elif embedding_failures:
        blocker_stage = "generic_same_shell_target_embedding_failure"
        blocker = "generic same-shell target AI-in-BS embedding failed for at least one compatibility-zero candidate"
    return {
        "object_semantics": "full_current_shell_diagnostic_quotient",
        "availability": availability,
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "dBS_current_full_shell": bs_rank if availability == "available" else None,
        "dAI_current_full_shell": None,
        "classification_current_full_shell": classification if availability == "available" else None,
        "dBS": None,
        "dAI": None,
        "classification": None,
        "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
        "same_shell_candidate_ai_rank": (
            same_shell_target_rank if availability == "available" else None
        ),
        "dbs_dai_gap": None,
        "dbs_minus_ai_image_rank": int(bs_rank - ai_image_rank_in_bs) if availability == "available" else None,
        "free_rank": free_rank if availability == "available" else None,
        "finite_part": finite_part if availability == "available" else [],
        "smith_diagonal_nonzero": smith_diag,
        "reported_dbs_semantics": "full_current_shell_rank",
        "reported_dai_semantics": "unresolved_do_not_treat_as_target",
        "classification_derivation_basis": "smith_rank_of_ai_image_in_bs_on_full_current_shell",
        "same_shell_rank_check": {
            "dBS": None,
            "dAI": None,
            "ai_image_rank_in_bs": ai_image_rank_in_bs if availability == "available" else None,
            "dBS_current_full_shell": bs_rank if availability == "available" else None,
            "diagnostic_same_shell_candidate_ai_rank": (
                same_shell_target_rank if availability == "available" else None
            ),
        },
        "ai_candidate_count": induced["candidate_count"],
        "ai_candidate_count_used": len(compatible_candidates),
        "ai_failure_count": induced["failure_count"],
        "ai_incompatible_count": len(rejected_candidates),
        "ai_embedding_failure_count": len(embedding_failures),
        "ai_incompatible_candidates": rejected_candidates,
        "ai_embedding_failures": embedding_failures,
        "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
        "compatibility_check_mode": "same_shell_full_current_rows_over_full_kernel_basis",
        "target_unknown_count": len(unknown_ordering),
        "target_unknown_ordering": list(unknown_ordering),
        "verification_status": (
            "generic_same_shell_diagnostic_quotient_available"
            if availability == "available"
            else "generic_same_shell_target_pending_manual_followup"
        ),
        "same_shell_semantics": "full_current_shell_diagnostic_object",
        "quotient_semantics": "full_current_shell_diagnostic_quotient",
    }


def _same_shell_target_semantics_pass(
    *,
    target_row_language: dict[str, Any],
    target_quotient: dict[str, Any],
    projected_point_shell_attempt: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    if target_row_language.get("availability") != "available":
        evidence = {
            "target_row_language_availability": target_row_language.get("availability"),
            "target_row_language_blocker_stage": target_row_language.get("blocker_stage"),
            "projected_point_shell_status": projected_point_shell_attempt.get("status"),
            "projected_point_shell_blocker_stage": projected_point_shell_attempt.get("blocker_stage"),
        }
        return False, "same_shell_target_row_language_not_available", evidence
    if target_quotient.get("availability") != "available":
        evidence = {
            "target_quotient_semantics": target_quotient.get("object_semantics"),
            "target_quotient_verification_status": target_quotient.get("verification_status"),
            "projected_point_shell_status": projected_point_shell_attempt.get("status"),
            "projected_point_shell_blocker_stage": projected_point_shell_attempt.get("blocker_stage"),
        }
        return False, "same_shell_target_quotient_not_available", evidence
    if target_quotient.get("object_semantics") != "same_shell_published_target_quotient_candidate":
        evidence = {
            "target_quotient_semantics": target_quotient.get("object_semantics"),
            "projected_point_shell_status": projected_point_shell_attempt.get("status"),
            "projected_point_shell_blocker_stage": projected_point_shell_attempt.get("blocker_stage"),
        }
        return False, "same_shell_target_quotient_not_published_semantics", evidence
    d_bs = target_quotient.get("dBS")
    d_ai = target_quotient.get("dAI")
    if d_bs is None or d_ai is None:
        evidence = {
            "dBS": d_bs,
            "dAI": d_ai,
            "target_quotient_verification_status": target_quotient.get("verification_status"),
        }
        return False, "same_shell_target_quotient_missing_target_ranks", evidence
    if d_bs != d_ai:
        evidence = {
            "dBS": d_bs,
            "dAI": d_ai,
            "ai_image_rank_in_bs": target_quotient.get("ai_image_rank_in_bs"),
            "projected_point_shell_status": projected_point_shell_attempt.get("status"),
        }
        return False, "same_shell_target_quotient_dbs_dai_gap", evidence
    if target_quotient.get("classification") is None:
        evidence = {
            "dBS": d_bs,
            "dAI": d_ai,
            "classification": target_quotient.get("classification"),
        }
        return False, "same_shell_target_quotient_missing_classification", evidence
    evidence = {
        "target_row_language_semantics": target_row_language.get("object_semantics"),
        "target_quotient_semantics": target_quotient.get("object_semantics"),
        "projected_point_shell_status": projected_point_shell_attempt.get("status"),
        "projected_point_shell_blocker_stage": projected_point_shell_attempt.get("blocker_stage"),
    }
    return True, "same_shell_target_semantics_verified", evidence


def _attempt_projected_point_shell_quotient(
    point_ids: list[str],
    unknown_ordering: list[str],
    bs_analysis: dict[str, Any],
    compatibility: dict[str, Any],
    induced: dict[str, Any],
) -> dict[str, Any]:
    try:
        quotient = _build_quotient_from_candidates(
            point_ids,
            unknown_ordering,
            bs_analysis,
            compatibility,
            induced,
        )
        return {
            "status": "available",
            "attempt_kind": "projected_point_shell",
            "diagnostic_only": True,
            "quotient": quotient,
            "blocker_stage": None,
            "blocker": None,
            "evidence": {
                "full_rank": quotient.get("full_shell_rank"),
                "projected_rank": quotient.get("point_shell_rank"),
            },
        }
    except Exception as exc:
        message = str(exc)
        blocker_stage = "generic_direct_quotient_builder_error"
        evidence: dict[str, Any] = {}
        blocker = message
        if "generic point-shell projection lost rank" in message:
            blocker_stage = "generic_same_shell_target_rank_loss"
            blocker = (
                "generic point-shell projection lost rank; direct quotient on projected current rows is ambiguous"
            )
            evidence = _structured_projection_rank_loss(message)
        return {
            "status": "blocked",
            "attempt_kind": "projected_point_shell",
            "diagnostic_only": True,
            "quotient": None,
            "blocker_stage": blocker_stage,
            "blocker": blocker,
            "evidence": evidence,
            "raw_error": message,
        }


def _build_generic_same_shell_target_object(
    *,
    group_id: str,
    mode: str,
    target_row_language: dict[str, Any],
    target_quotient: dict[str, Any],
    compatibility: dict[str, Any],
    bs_analysis: dict[str, Any],
    induced: dict[str, Any],
    projected_point_shell_attempt: dict[str, Any],
) -> dict[str, Any]:
    full_current_shell_quotient = _build_same_shell_quotient_from_candidates(
        bs_analysis["unknown_ordering"],
        bs_analysis,
        compatibility,
        induced,
    )
    semantic_pass, promotion_reason, semantic_evidence = _same_shell_target_semantics_pass(
        target_row_language=target_row_language,
        target_quotient=target_quotient,
        projected_point_shell_attempt=projected_point_shell_attempt,
    )

    if not semantic_pass:
        blocker_message = {
            "same_shell_target_row_language_not_available": (
                "same-shell target row language is not yet available"
            ),
            "same_shell_target_quotient_not_available": (
                "same-shell target quotient is not yet available"
            ),
            "same_shell_target_quotient_not_published_semantics": (
                "same-shell target quotient does not yet carry published-target semantics"
            ),
            "same_shell_target_quotient_missing_target_ranks": (
                "same-shell target quotient is missing target dBS/dAI ranks"
            ),
            "same_shell_target_quotient_dbs_dai_gap": (
                "same-shell target quotient fails the published-target semantic guard because dBS != dAI"
            ),
            "same_shell_target_quotient_missing_classification": (
                "same-shell target quotient is missing a target classification"
            ),
        }.get(
            promotion_reason,
            "same-shell target object failed semantic verification before published-target promotion",
        )
        blocker_evidence = {
            **semantic_evidence,
            "target_row_language": target_row_language,
            "target_quotient": target_quotient,
            "full_current_shell_quotient": full_current_shell_quotient,
            "projected_point_shell_attempt": projected_point_shell_attempt,
        }
        return {
            "object_id": f"{mode}_target_same_shell",
            "group": group_id,
            "mode": mode,
            "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
            "object_kind": GENERIC_TARGET_OBJECT_KIND,
            "availability": "blocked",
            "exact_alignment_status": "generic_same_shell_target_semantics_fail",
            "generic_builder_ready": True,
            "generic_published_classification_ready": False,
            "target_alignment_builder_status": (
                "available" if target_quotient.get("availability") == "available" else "blocked"
            ),
            "direct_quotient_status": (
                "generic_same_shell_target_semantics_fail"
                if target_quotient.get("availability") == "available"
                else target_quotient.get("blocker_stage", "generic_same_shell_target_semantics_fail")
            ),
            "local_ai_embedding_status": (
                "generic_target_row_language_embedding_success"
                if target_quotient.get("availability") == "available"
                else "generic_target_row_language_embedding_blocked"
            ),
            "dBS": target_quotient.get("dBS"),
            "dAI": target_quotient.get("dAI"),
            "ai_image_rank_in_bs": target_quotient.get("ai_image_rank_in_bs"),
            "dbs_dai_gap": target_quotient.get("dbs_dai_gap"),
            "dbs_minus_ai_image_rank": target_quotient.get("dbs_minus_ai_image_rank"),
            "free_rank": target_quotient.get("free_rank"),
            "finite_part": list(target_quotient.get("finite_part", [])),
            "classification": target_quotient.get("classification"),
            "smith_diagonal_nonzero": list(target_quotient.get("smith_diagonal_nonzero", [])),
            "object_semantics": "generic_same_shell_target_object_blocked_before_published_semantics",
            "reported_dbs_semantics": target_quotient.get("reported_dbs_semantics"),
            "reported_dai_semantics": target_quotient.get("reported_dai_semantics"),
            "classification_derivation_basis": target_quotient.get("classification_derivation_basis"),
            "same_shell_semantics": "not_yet_published_target_object",
            "quotient_semantics": "blocked_before_published_target_semantics",
            "promotion_reason": promotion_reason,
            "same_shell_rank_check": target_quotient.get("same_shell_rank_check"),
            "verification_status": "semantic_fail",
            "source": "generic_symmetry_ops_same_shell_target_builder",
            "blocker_stage": "generic_same_shell_target_semantics_fail",
            "blocker": blocker_message,
            "blocker_evidence": blocker_evidence,
            "target_row_language": target_row_language,
            "target_quotient": target_quotient,
            "full_current_shell_quotient": full_current_shell_quotient,
            "projected_point_shell_attempt": projected_point_shell_attempt,
            "evidence": blocker_evidence,
            "quotient": target_quotient,
        }

    return {
        "object_id": f"{mode}_target_same_shell",
        "group": group_id,
        "mode": mode,
        "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
        "object_kind": GENERIC_TARGET_OBJECT_KIND,
        "availability": "available",
        "exact_alignment_status": "generic_same_shell_target_ready",
        "generic_builder_ready": True,
        "generic_published_classification_ready": True,
        "target_alignment_builder_status": "available",
        "direct_quotient_status": "generic_same_shell_direct_quotient_success",
        "local_ai_embedding_status": "generic_target_row_language_embedding_success",
        "dBS": target_quotient.get("dBS"),
        "dAI": target_quotient.get("dAI"),
        "ai_image_rank_in_bs": target_quotient.get("ai_image_rank_in_bs"),
        "dbs_dai_gap": target_quotient.get("dbs_dai_gap"),
        "dbs_minus_ai_image_rank": target_quotient.get("dbs_minus_ai_image_rank"),
        "free_rank": target_quotient.get("free_rank"),
        "finite_part": list(target_quotient.get("finite_part", [])),
        "classification": target_quotient.get("classification"),
        "smith_diagonal_nonzero": list(target_quotient.get("smith_diagonal_nonzero", [])),
        "object_semantics": "published_target_object",
        "reported_dbs_semantics": target_quotient.get("reported_dbs_semantics"),
        "reported_dai_semantics": target_quotient.get("reported_dai_semantics"),
        "classification_derivation_basis": target_quotient.get("classification_derivation_basis"),
        "same_shell_semantics": "published_target_object",
        "quotient_semantics": "same_shell_published_target_quotient",
        "promotion_reason": promotion_reason,
        "same_shell_rank_check": target_quotient.get("same_shell_rank_check"),
        "verification_status": "semantic_pass",
        "source": "generic_symmetry_ops_same_shell_target_builder",
        "blocker_stage": None,
        "blocker": None,
        "target_row_language": target_row_language,
        "target_quotient": target_quotient,
        "full_current_shell_quotient": full_current_shell_quotient,
        "projected_point_shell_attempt": projected_point_shell_attempt,
        "evidence": {
            "same_shell_rank_check": target_quotient.get("same_shell_rank_check"),
            "target_row_language": target_row_language,
            "target_quotient": target_quotient,
            "full_current_shell_quotient": full_current_shell_quotient,
            "projected_point_shell_attempt": projected_point_shell_attempt,
        },
        "quotient": target_quotient,
    }


def _generic_progress_payload(
    group_id: str,
    mode: str,
    builder_variant: str,
    *,
    shared: dict[str, Any] | None = None,
    compatibility: dict[str, Any] | None = None,
    local_library: dict[str, Any] | None = None,
    induced: dict[str, Any] | None = None,
    quotient: dict[str, Any] | None = None,
    target_row_language: dict[str, Any] | None = None,
    same_shell_target: dict[str, Any] | None = None,
    blocker_stage: str | None = None,
    blocker: str | None = None,
    current_row_shell_status: str = "available",
    local_ai_seed_status: str = "available",
    compatibility_builder_status: str = "blocked",
    target_alignment_builder_status: str = "blocked",
    generic_builder_ready: bool = False,
    generic_published_classification_ready: bool = False,
) -> dict[str, Any]:
    target_point_ids = list((shared or {}).get("target_point_ids", []))
    compatibility_matrix_shape = None
    if compatibility is not None:
        compatibility_matrix_shape = list(compatibility.get("matrix_shape", []))
    candidate_count = None
    failure_count = None
    if induced is not None:
        candidate_count = int(induced.get("candidate_count", 0))
        failure_count = int(induced.get("failure_count", 0))
    family_count = None
    if local_library is not None:
        family_count = len(local_library.get("families", {}))
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "mode": mode,
        "builder_variant": builder_variant,
        "current_row_shell_status": current_row_shell_status,
        "local_ai_seed_status": local_ai_seed_status,
        "compatibility_builder_status": compatibility_builder_status,
        "target_alignment_builder_status": target_alignment_builder_status,
        "generic_builder_ready": generic_builder_ready,
        "generic_published_classification_ready": generic_published_classification_ready,
        "target_point_ids": target_point_ids,
        "compatibility_matrix_shape": compatibility_matrix_shape,
        "local_ai_family_count": family_count,
        "ai_candidate_count": candidate_count,
        "ai_failure_count": failure_count,
        "target_row_language": target_row_language,
        "same_shell_target": same_shell_target,
        "blocker_stage": blocker_stage,
        "blocker": blocker,
        "quotient": quotient,
    }


@lru_cache(maxsize=None)
def generic_mode_progress(group_id: str, mode: str, builder_variant: str = "authoritative") -> dict[str, Any]:
    if mode not in {"single", "double"}:
        raise ValueError(f"unsupported generic mode: {mode}")
    if builder_variant == "extrinsic":
        raise ValueError("extrinsic generic builder is retired and non-authoritative")
    if builder_variant not in {"authoritative", "coarse", "intrinsic"}:
        raise ValueError(f"unsupported builder variant: {builder_variant}")

    port = stage1_backend()
    try:
        shared = shared_geometry_bundle(group_id)
    except Exception as exc:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            blocker_stage="generic_shared_geometry_builder_error",
            blocker=str(exc),
            current_row_shell_status="blocked",
            local_ai_seed_status="blocked",
        )

    try:
        module = ssgreps_module()
        ssg_dict = port.load_ssg_dict(group_id)
        ctx = port.load_context(module, group_id, mode, ssg_dict)
        ctx["kgeom"] = shared["kgeom"]
        captures = port.build_manifold_capture(module, group_id, ssg_dict, ctx, mode, shared["kgeom"])
        captures, line_capture_canonicalization = _canonicalize_line_captures(
            module,
            group_id,
            ssg_dict,
            ctx,
            mode,
            shared["grouped"],
            captures,
        )
    except Exception as exc:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            blocker_stage="generic_capture_builder_error",
            blocker=str(exc),
            current_row_shell_status="available",
            local_ai_seed_status="blocked",
        )

    try:
        compatibility = _build_generic_compatibility(
            group_id,
            shared["grouped"],
            shared["all_point_ids"],
            captures,
            builder_variant=builder_variant,
        )
        bs_analysis = port.analyze_kernel(compatibility)
        point_row_translation = port.build_phase_aware_point_row_translation(
            compatibility["line_blocks"],
            bs_analysis["unknown_ordering"],
            phase_aware_profile=(
                port.AUTHORITATIVE_PHASE_AWARE_PROFILE
                if builder_variant in {"authoritative", "coarse"}
                else None
            ),
        )
    except Exception as exc:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            blocker_stage="generic_current_row_compatibility_builder_error",
            blocker=str(exc),
            current_row_shell_status="available",
            local_ai_seed_status="available",
        )

    try:
        local_library = _build_local_irrep_library(ctx, mode)
    except Exception as exc:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            compatibility=compatibility,
            blocker_stage="generic_local_ai_seed_builder_error",
            blocker=str(exc),
            current_row_shell_status="available",
            local_ai_seed_status="blocked",
            compatibility_builder_status="available",
        )

    try:
        induced = _induce_all_candidates(
            ctx,
            captures,
            compatibility,
            bs_analysis["unknown_ordering"],
            local_library,
            point_row_translation=point_row_translation,
        )
    except Exception as exc:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            compatibility=compatibility,
            local_library=local_library,
            blocker_stage="generic_local_ai_embedding_error",
            blocker=str(exc),
            current_row_shell_status="available",
            local_ai_seed_status="available",
            compatibility_builder_status="available",
        )

    projected_point_shell_attempt = _attempt_projected_point_shell_quotient(
        shared["target_point_ids"],
        bs_analysis["unknown_ordering"],
        bs_analysis,
        compatibility,
        induced,
    )
    target_row_language = _build_same_shell_target_row_language(
        shared=shared,
        compatibility=compatibility,
        bs_analysis=bs_analysis,
        captures=captures,
        module=module,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
        builder_variant=builder_variant,
    )
    target_quotient = _build_same_shell_target_quotient(
        target_row_language=target_row_language,
        induced=induced,
    )
    same_shell_target = _build_generic_same_shell_target_object(
        group_id=group_id,
        mode=mode,
        target_row_language=target_row_language,
        target_quotient=target_quotient,
        compatibility=compatibility,
        bs_analysis=bs_analysis,
        induced=induced,
        projected_point_shell_attempt=projected_point_shell_attempt,
    )
    semantic_ready = bool(
        same_shell_target.get("availability") == "available"
        and same_shell_target.get("verification_status") == "semantic_pass"
        and same_shell_target.get("same_shell_semantics") == "published_target_object"
        and same_shell_target.get("dBS") is not None
        and same_shell_target.get("dAI") is not None
    )
    if semantic_ready:
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            compatibility=compatibility,
            local_library=local_library,
            induced=induced,
            quotient=same_shell_target.get("quotient"),
            target_row_language=target_row_language,
            same_shell_target=same_shell_target,
            blocker_stage=None,
            blocker=None,
            current_row_shell_status="available",
            local_ai_seed_status="available",
            compatibility_builder_status="available",
            target_alignment_builder_status="available",
            generic_builder_ready=True,
            generic_published_classification_ready=semantic_ready,
        )

    return _generic_progress_payload(
        group_id,
        mode,
        builder_variant,
        shared=shared,
        compatibility=compatibility,
        local_library=local_library,
        induced=induced,
        quotient=same_shell_target.get("quotient"),
        target_row_language=target_row_language,
        same_shell_target=same_shell_target,
        blocker_stage=same_shell_target.get("blocker_stage"),
        blocker=same_shell_target.get("blocker"),
        current_row_shell_status="available",
        local_ai_seed_status="available",
        compatibility_builder_status="available",
        target_alignment_builder_status=same_shell_target.get("target_alignment_builder_status", "blocked"),
        generic_builder_ready=bool(same_shell_target.get("generic_builder_ready", False)),
        generic_published_classification_ready=semantic_ready,
    )


@lru_cache(maxsize=None)
def generic_mode_bundle(group_id: str, mode: str, builder_variant: str = "authoritative") -> dict[str, Any]:
    if mode not in {"single", "double"}:
        raise ValueError(f"unsupported generic mode: {mode}")
    if builder_variant == "extrinsic":
        raise ValueError("extrinsic generic builder is retired and non-authoritative")
    if builder_variant not in {"authoritative", "coarse", "intrinsic"}:
        raise ValueError(f"unsupported builder variant: {builder_variant}")

    port = stage1_backend()
    shared = shared_geometry_bundle(group_id)
    module = ssgreps_module()
    ssg_dict = port.load_ssg_dict(group_id)
    ctx = port.load_context(module, group_id, mode, ssg_dict)
    ctx["kgeom"] = shared["kgeom"]
    captures = port.build_manifold_capture(module, group_id, ssg_dict, ctx, mode, shared["kgeom"])
    captures, line_capture_canonicalization = _canonicalize_line_captures(
        module,
        group_id,
        ssg_dict,
        ctx,
        mode,
        shared["grouped"],
        captures,
    )
    compatibility = _build_generic_compatibility(
        group_id,
        shared["grouped"],
        shared["all_point_ids"],
        captures,
        builder_variant=builder_variant,
    )
    bs_analysis = port.analyze_kernel(compatibility)
    point_row_translation = port.build_phase_aware_point_row_translation(
        compatibility["line_blocks"],
        bs_analysis["unknown_ordering"],
        phase_aware_profile=(
            port.AUTHORITATIVE_PHASE_AWARE_PROFILE
            if builder_variant in {"authoritative", "coarse"}
            else None
        ),
    )
    local_library = _build_local_irrep_library(ctx, mode)
    induced = _induce_all_candidates(
        ctx,
        captures,
        compatibility,
        bs_analysis["unknown_ordering"],
        local_library,
        point_row_translation=point_row_translation,
    )
    quotient = _build_quotient_from_candidates(
        shared["target_point_ids"],
        bs_analysis["unknown_ordering"],
        bs_analysis,
        compatibility,
        induced,
    )
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "mode": mode,
        "builder_variant": builder_variant,
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "shared_geometry": shared,
        "compatibility": compatibility,
        "bs_analysis": bs_analysis,
        "local_library": local_library,
        "induced": induced,
        "quotient": quotient,
        "line_capture_canonicalization": line_capture_canonicalization,
        "point_row_translation": point_row_translation,
        "phase_aware_profile": (
            port.AUTHORITATIVE_PHASE_AWARE_PROFILE
            if builder_variant in {"authoritative", "coarse"}
            else None
        ),
    }


def generic_geometry_summary(group_id: str) -> dict[str, Any]:
    shared = shared_geometry_bundle(group_id)
    grouped = shared["grouped"]
    payload = shared["payload"]
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "status": "built_from_trusted_symmetry_ops",
        "shared_backbone_available": True,
        "shared_backbone_mode": "generic_trusted_symmetry_ops_kgeometry",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "object_counts": {
            "points": len(grouped["points"]),
            "lines": len(grouped["lines"]),
            "planes": len(grouped["planes"]),
            "synthetic_boundary_points": len(shared["synthetic_points"]),
        },
        "connectivity_summary": {
            "point_line": len(payload.get("point_line", [])),
            "line_plane": len(payload.get("line_plane", [])),
            "unmatched_line_endpoints": len(payload.get("unmatched_line_endpoints", [])),
            "unmatched_plane_boundaries": len(payload.get("unmatched_plane_boundaries", [])),
        },
        "source": {
            "entrypoint": "common/swyckoff.py",
            "conversion_sources": [
                "common/swyckoff_k.py",
                "common/swyckoff_r.py",
            ],
            "backend_runtime_module": str(RUNTIME_BACKEND.relative_to(ROOT.parent)),
        },
    }


def generic_alignment_summary(group_id: str) -> dict[str, Any]:
    shared = shared_geometry_bundle(group_id)
    single_progress = generic_mode_progress(group_id, "single")
    double_progress = generic_mode_progress(group_id, "double")

    def target_payload(progress: dict[str, Any]) -> dict[str, Any]:
        target = progress.get("same_shell_target") or {}
        target_row_language = progress.get("target_row_language") or target.get("target_row_language") or {}
        target_quotient = target.get("target_quotient") or target.get("quotient") or progress.get("quotient") or {}
        projected = target.get("projected_point_shell_attempt") or (target.get("evidence") or {}).get("projected_point_shell_attempt", {})
        return {
            "row_language_kind": target.get("row_language_kind", GENERIC_TARGET_ROW_LANGUAGE),
            "exact_alignment_status": target.get("exact_alignment_status", progress.get("blocker_stage")),
            "object_kind": target.get("object_kind", GENERIC_TARGET_OBJECT_KIND),
            "availability": target.get("availability", "blocked"),
            "target_row_language_availability": target_row_language.get("availability"),
            "target_unknown_count": target_row_language.get("target_unknown_count"),
            "target_projection_matrix_shape": target_row_language.get("target_projection_matrix_shape"),
            "compatibility_matrix_shape": progress.get("compatibility_matrix_shape"),
            "current_row_compatibility_status": progress.get("compatibility_builder_status"),
            "target_alignment_builder_status": target.get(
                "target_alignment_builder_status",
                progress.get("target_alignment_builder_status"),
            ),
                "local_ai_embedding_status": target.get(
                    "local_ai_embedding_status",
                    (
                        "diagnostic_only_projected_point_shell"
                        if target_quotient
                        else "blocked_before_projected_point_shell_embedding"
                    ),
                ),
            "direct_quotient_status": target.get(
                "direct_quotient_status",
                (
                    "diagnostic_only_projected_point_shell"
                    if target_quotient
                    else progress.get("blocker_stage")
                ),
            ),
            "ai_candidate_count": progress.get("ai_candidate_count"),
            "ai_failure_count": progress.get("ai_failure_count"),
            "dBS": target.get("dBS"),
            "dAI": target.get("dAI"),
            "ai_image_rank_in_bs": target.get("ai_image_rank_in_bs"),
            "dbs_minus_ai_image_rank": target.get("dbs_minus_ai_image_rank"),
            "classification": target.get("classification"),
            "free_rank": target.get("free_rank"),
            "finite_part": list(target.get("finite_part", [])),
            "reported_dbs_semantics": target.get("reported_dbs_semantics"),
            "reported_dai_semantics": target.get("reported_dai_semantics"),
            "classification_derivation_basis": target.get("classification_derivation_basis"),
            "object_semantics": target.get("object_semantics"),
            "same_shell_semantics": target.get("same_shell_semantics"),
            "quotient_semantics": target.get("quotient_semantics"),
            "promotion_reason": target.get("promotion_reason"),
            "same_shell_rank_check": target.get("same_shell_rank_check"),
            "verification_status": target.get("verification_status"),
            "target_row_language": target.get("target_row_language", target_row_language),
            "target_quotient": target.get("target_quotient", target_quotient),
            "full_current_shell_quotient": target.get("full_current_shell_quotient"),
            "projected_point_shell_attempt": target.get("projected_point_shell_attempt"),
            "diagnostic_projected_point_shell_status": projected.get("status"),
            "diagnostic_projected_point_shell_blocker_stage": projected.get("blocker_stage"),
            "diagnostic_projected_point_shell_blocker": projected.get("blocker"),
            "diagnostic_projected_point_shell_evidence": projected.get("evidence"),
            "diagnostic_projected_point_shell_dbs": (projected.get("quotient") or {}).get("dBS"),
            "diagnostic_projected_point_shell_dai": (projected.get("quotient") or {}).get("dAI"),
            "diagnostic_projected_point_shell_ai_image_rank_in_bs": (projected.get("quotient") or {}).get("ai_image_rank_in_bs"),
            "diagnostic_projected_point_shell_classification": (projected.get("quotient") or {}).get("classification"),
            "generic_builder_ready": progress.get("generic_builder_ready", False),
            "generic_published_classification_ready": progress.get(
                "generic_published_classification_ready", False
            ),
            "blocker_stage": target.get("blocker_stage", progress.get("blocker_stage")),
            "blocker": target.get("blocker", progress.get("blocker")),
            "blocker_evidence": target.get("blocker_evidence", target.get("evidence")),
        }

    current_row_shell = {
        "status": "available",
        "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "point_count": len(shared["target_point_ids"]),
        "point_ids": list(shared["target_point_ids"]),
    }
    local_ai_seed_builder = {
        "status": "available",
        "row_language_kind": "generic_local_ai_seed_from_site_symmetry_data",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "realspace_wyckoff_family_count": single_progress.get("local_ai_family_count"),
    }
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "trust_policy": "symmetry_operations_only",
        "current_row_shell": current_row_shell,
        "local_ai_seed_builder": local_ai_seed_builder,
        "compatibility_builder": {
            "status": (
                "available"
                if all(
                    progress.get("compatibility_builder_status") == "available"
                    for progress in (single_progress, double_progress)
                )
                else "blocked"
            ),
            "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
            "single_matrix_shape": single_progress.get("compatibility_matrix_shape"),
            "double_matrix_shape": double_progress.get("compatibility_matrix_shape"),
            "single_builder_stage": single_progress.get("blocker_stage"),
            "double_builder_stage": double_progress.get("blocker_stage"),
            "single_blocker": single_progress.get("blocker"),
            "double_blocker": double_progress.get("blocker"),
        },
        "single": {
            "raw": {
                "row_language_kind": current_row_shell["row_language_kind"],
                "exact_alignment_status": "not_applicable_current_row_shell_only",
                "object_kind": "generic_current_row_shell",
                "availability": "available",
            },
            "target": target_payload(single_progress),
        },
        "double": {
            "raw": {
                "row_language_kind": current_row_shell["row_language_kind"],
                "exact_alignment_status": "not_applicable_current_row_shell_only",
                "object_kind": "generic_current_row_shell",
                "availability": "available",
            },
            "target": target_payload(double_progress),
        },
    }


def generic_result_objects(group_id: str, builder_variant: str = "authoritative") -> list[dict[str, Any]]:
    results = []
    for mode in ("single", "double"):
        progress = generic_mode_progress(group_id, mode, builder_variant=builder_variant)
        target = progress.get("same_shell_target") or {}
        quotient = target.get("quotient") or progress.get("quotient") or {}
        projected = target.get("projected_point_shell_attempt") or (target.get("evidence") or {}).get("projected_point_shell_attempt", {})
        results.append(
            {
                "object_id": f"{mode}_raw_shell",
                "mode": mode,
                "row_language_level": "raw",
                "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
                "object_kind": "generic_current_row_shell",
                "availability": "available",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "quotient_derivation_mode": "not_applicable_current_row_shell_only",
                "exact_alignment_status": "not_applicable_current_row_shell_only",
                "current_row_shell_status": "available",
                "source_files": [str(RUNTIME_BACKEND.relative_to(ROOT.parent))],
            }
        )
        results.append(
            {
                "object_id": target.get("object_id", f"{mode}_target_same_shell"),
                "mode": mode,
                "builder_variant": builder_variant,
                "row_language_level": "target",
                "row_language_kind": target.get("row_language_kind", GENERIC_TARGET_ROW_LANGUAGE),
                "object_kind": target.get("object_kind", GENERIC_TARGET_OBJECT_KIND),
                "availability": target.get("availability", "blocked"),
                "dBS": target.get("dBS"),
                "dAI": target.get("dAI"),
                "ai_image_rank_in_bs": target.get("ai_image_rank_in_bs"),
                "classification": target.get("classification"),
                "free_rank": target.get("free_rank"),
                "finite_part": list(target.get("finite_part", [])),
                "surviving_ai_rank": quotient.get("surviving_ai_rank"),
                "surviving_classification": quotient.get("surviving_classification"),
                "surviving_free_rank": quotient.get("surviving_free_rank"),
                "surviving_finite_part": quotient.get("surviving_finite_part", []),
                "quotient_derivation_mode": target.get(
                    "direct_quotient_status",
                    "blocked_projected_point_shell_is_diagnostic_only",
                ),
                "exact_alignment_status": target.get(
                    "exact_alignment_status",
                    progress.get("blocker_stage"),
                ),
                "current_row_compatibility_status": progress.get("compatibility_builder_status"),
                "target_alignment_status": target.get(
                    "target_alignment_builder_status",
                    progress.get("target_alignment_builder_status"),
                ),
                "local_ai_embedding_status": target.get(
                    "local_ai_embedding_status",
                    (
                        "diagnostic_only_projected_point_shell"
                        if quotient
                        else "blocked_before_projected_point_shell_embedding"
                    ),
                ),
                "direct_quotient_status": target.get(
                    "direct_quotient_status",
                    (
                        "diagnostic_only_projected_point_shell"
                        if quotient
                        else progress.get("blocker_stage")
                    ),
                ),
                "verification_status": target.get(
                    "verification_status",
                    "blocked_projected_point_shell_result_not_published_as_active_object",
                ),
                "ai_candidate_count": progress.get("ai_candidate_count"),
                "ai_candidate_count_used": quotient.get("ai_candidate_count_used"),
                "ai_failure_count": progress.get("ai_failure_count"),
                "ai_incompatible_count": quotient.get("ai_incompatible_count"),
                "ai_embedding_failure_count": quotient.get("ai_embedding_failure_count"),
                "dbs_dai_gap": quotient.get("dbs_dai_gap"),
                "dbs_minus_ai_image_rank": quotient.get("dbs_minus_ai_image_rank"),
                "smith_diagonal_nonzero": quotient.get("smith_diagonal_nonzero"),
                "reported_dbs_semantics": target.get("reported_dbs_semantics"),
                "reported_dai_semantics": target.get("reported_dai_semantics"),
                "classification_derivation_basis": target.get("classification_derivation_basis"),
                "object_semantics": target.get("object_semantics"),
                "same_shell_semantics": target.get("same_shell_semantics"),
                "quotient_semantics": target.get("quotient_semantics"),
                "promotion_reason": target.get("promotion_reason"),
                "same_shell_rank_check": target.get("same_shell_rank_check"),
                "target_row_language": target.get("target_row_language", progress.get("target_row_language")),
                "target_quotient": target.get("target_quotient"),
                "full_current_shell_quotient": target.get("full_current_shell_quotient"),
                "projected_point_shell_attempt": target.get("projected_point_shell_attempt"),
                "ai_incompatible_candidates": quotient.get("ai_incompatible_candidates", []),
                "ai_embedding_failures": quotient.get("ai_embedding_failures", []),
                "ai_filter_mode": quotient.get(
                    "compatibility_check_mode",
                    "diagnostic_point_shell_projection_over_full_kernel_basis",
                ),
                "blocker": target.get("blocker", progress.get("blocker")),
                "blocker_stage": target.get("blocker_stage", progress.get("blocker_stage")),
                "blocker_evidence": target.get("blocker_evidence", target.get("evidence")),
                "generic_builder_ready": progress.get("generic_builder_ready", False),
                "generic_published_classification_ready": progress.get(
                    "generic_published_classification_ready", False
                ),
                "diagnostic_projected_point_shell_status": projected.get("status"),
                "diagnostic_projected_point_shell_blocker_stage": projected.get("blocker_stage"),
                "diagnostic_projected_point_shell_blocker": projected.get("blocker"),
                "diagnostic_projected_point_shell_evidence": projected.get("evidence"),
                "diagnostic_projected_point_shell_dbs": (projected.get("quotient") or {}).get("dBS"),
                "diagnostic_projected_point_shell_dai": (projected.get("quotient") or {}).get("dAI"),
                "diagnostic_projected_point_shell_ai_image_rank_in_bs": (projected.get("quotient") or {}).get("ai_image_rank_in_bs"),
                "diagnostic_projected_point_shell_classification": (projected.get("quotient") or {}).get("classification"),
                "source": target.get("source", "generic_symmetry_ops_same_shell_target_builder"),
                "source_files": [
                    str(RUNTIME_BACKEND.relative_to(ROOT.parent)),
                    str(LOCAL_IRREP_BACKEND.relative_to(ROOT.parent)),
                ],
            }
        )
    return results
