from __future__ import annotations

import importlib.util
import json
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp

from .utils import now_iso


ROOT = Path(__file__).resolve().parents[1]
STAGE1_BACKEND = ROOT / "debug_workflow_portability_194.1.1.1.py"
LOCAL_LIBRARY_BACKEND = ROOT / "debug_sg194_nonabelian_local_library.py"

GENERIC_TARGET_ROW_LANGUAGE = "generic_canonical_point_row_language_from_symmetry_ops"
GENERIC_TARGET_OBJECT_KIND = "generic_direct_point_row_language_object"
LINE_SAMPLE = Fraction(1, 5)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load backend module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def stage1_backend():
    return _load_module("sg194_stage1_backend", STAGE1_BACKEND)


@lru_cache(maxsize=1)
def local_library_backend():
    return _load_module("sg194_local_library_backend", LOCAL_LIBRARY_BACKEND)


@lru_cache(maxsize=1)
def ssgreps_module():
    return stage1_backend().load_ssgreps_module()


def _class_key(restricted_vector: list[dict[str, Any]]) -> str:
    return json.dumps(restricted_vector, sort_keys=True, separators=(",", ":"))


def _parse_line_orbit_coordinate(piece: str, sample: Fraction) -> Fraction:
    token = piece.strip()
    if token == "u":
        return sample
    if token == "-u":
        return -sample
    return Fraction(token)


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
        port.build_line_block(line_obj, captures, phase_aware_profile=None)
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
    point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]
    return {
        "group_id": group_id,
        "kgeom": kgeom,
        "grouped": grouped,
        "payload": payload,
        "synthetic_points": synthetic_points,
        "point_ids": point_ids,
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
) -> dict[str, Any]:
    port = stage1_backend()
    endpoint_classes = {}
    union: dict[str, dict[str, list[str]]] = {}
    vectors_by_key: dict[str, list[dict[str, Any]]] = {}

    for entry in endpoint_entries:
        endpoint_id = entry["point_id"]
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
    endpoint_ids = [entry["point_id"] for entry in endpoint_entries]
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


def _build_generic_line_block(line_obj: dict[str, Any], captures: dict[str, Any]) -> dict[str, Any]:
    return stage1_backend().build_line_block(line_obj, captures, phase_aware_profile=None)


def _build_generic_line_block_fallback(
    line_obj: dict[str, Any],
    captures: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    endpoint_entries = [
        {
            "point_id": endpoint["point_id"],
            "point_coordinates": endpoint["point_coordinates"],
            "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
        }
        for endpoint in line_obj["endpoints"]
    ]
    block = _build_restriction_class_rows(
        captures[line_obj["id"]],
        endpoint_entries,
        captures,
        source_type="line",
        field="character",
    )
    endpoint_decompositions = {}
    local_unknown_ordering = []
    for endpoint_entry in endpoint_entries:
        endpoint_id = endpoint_entry["point_id"]
        endpoint_raw = captures[endpoint_entry["capture_id"]]
        reps = [{"rep_id": f"{endpoint_id}_R{rep_index}"} for rep_index in range(1, len(endpoint_raw["linear_character"]) + 1)]
        endpoint_decompositions[endpoint_id] = reps
        local_unknown_ordering.extend(rep["rep_id"] for rep in reps)
    return {
        "status": "fallback_restriction_classes",
        "line_id": line_obj["id"],
        "endpoint_ids": [entry["point_id"] for entry in endpoint_entries],
        "line_sample_point": line_obj["sample_point"],
        "line_parametrization": line_obj["parametrization"],
        "line_symmetry_summary": line_obj["symmetry_summary"],
        "endpoint_decompositions": endpoint_decompositions,
        "local_unknown_ordering": local_unknown_ordering,
        "equations": block["equations"],
        "matrix_rows": [],
        "line_basis_labels": [],
        "line_group_signature": {
            "fallback_reason": reason,
            "n_unitary_ops": captures[line_obj["id"]]["unitary_operation_count"],
        },
        "phase_aware_refinement": {
            "profile": "generic_restriction_class_fallback",
            "selected_endpoint_id": None,
            "restriction_classes_by_endpoint": block["endpoint_classes"],
            "refinement_equations": [],
        },
    }


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
) -> dict[str, Any]:
    port = stage1_backend()
    line_blocks = []
    line_fallbacks = []
    for line in grouped["lines"]:
        try:
            block = _build_generic_line_block(line, captures)
        except Exception as exc:
            block = _build_generic_line_block_fallback(line, captures, str(exc))
            line_fallbacks.append({"line_id": line["id"], "reason": str(exc)})
        line_blocks.append(block)
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
        "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
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
        "compatibility_builder_kind": "generic_extracted_line_and_plane_basis_decomposition",
        "line_fallbacks": line_fallbacks,
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


def _build_quotient_from_candidates(
    point_ids: list[str],
    unknown_ordering: list[str],
    bs_analysis: dict[str, Any],
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
    incompatible_candidates = []
    embedding_failures = []
    for candidate in induced["candidates"]:
        point_vector = [int(candidate["unknown_vector"][index]) for index in point_indices]
        try:
            coords.append(_solve_ai_in_bs_coordinates(point_bs_matrix, point_vector))
            compatible_candidates.append(candidate)
        except Exception as exc:  # pragma: no cover - diagnostic path
            incompatible_candidates.append(
                {
                    "generator_id": candidate.get("generator_id"),
                    "family_letter": candidate.get("family_letter"),
                    "reason": f"point_shell_extension_failed: {exc}",
                }
            )
    ai_in_bs = sp.Matrix(coords).T if coords else sp.zeros(bs_rank, 0)
    smith_data = port.swyckoff_k.smith_normal_form([[int(value) for value in row] for row in ai_in_bs.tolist()])
    smith_matrix = sp.Matrix(smith_data[0]) if ai_in_bs.cols else sp.zeros(bs_rank, 0)
    smith_diag = _smith_diagonal(smith_matrix)
    ai_rank = len(smith_diag)
    finite_part = [value for value in smith_diag if value > 1]
    free_rank = int(bs_rank - ai_rank)
    return {
        "dBS": bs_rank,
        "dAI": ai_rank,
        "free_rank": free_rank,
        "finite_part": finite_part,
        "classification": _quotient_group_string(free_rank, finite_part),
        "smith_diagonal_nonzero": smith_diag,
        "ai_candidate_count": induced["candidate_count"],
        "ai_candidate_count_used": len(compatible_candidates),
        "ai_failure_count": induced["failure_count"],
        "ai_incompatible_count": len(incompatible_candidates),
        "ai_embedding_failure_count": 0,
        "ai_incompatible_candidates": incompatible_candidates,
        "ai_embedding_failures": embedding_failures,
        "ai_in_bs_matrix_shape": [int(ai_in_bs.rows), int(ai_in_bs.cols)],
        "compatibility_check_mode": "point_shell_projection_over_full_kernel_basis",
        "full_shell_rank": full_bs_rank,
        "point_shell_rank": bs_rank,
        "point_unknown_count": len(point_unknown_ordering),
        "point_unknown_ordering": point_unknown_ordering,
    }


@lru_cache(maxsize=None)
def generic_mode_bundle(group_id: str, mode: str) -> dict[str, Any]:
    if mode not in {"single", "double"}:
        raise ValueError(f"unsupported generic mode: {mode}")

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
    compatibility = _build_generic_compatibility(group_id, shared["grouped"], shared["point_ids"], captures)
    bs_analysis = port.analyze_kernel(compatibility)
    local_library = _build_local_irrep_library(ctx, mode)
    induced = _induce_all_candidates(
        ctx,
        captures,
        compatibility,
        bs_analysis["unknown_ordering"],
        local_library,
    )
    quotient = _build_quotient_from_candidates(
        shared["point_ids"],
        bs_analysis["unknown_ordering"],
        bs_analysis,
        induced,
    )
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "mode": mode,
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "shared_geometry": shared,
        "compatibility": compatibility,
        "bs_analysis": bs_analysis,
        "local_library": local_library,
        "induced": induced,
        "quotient": quotient,
        "line_capture_canonicalization": line_capture_canonicalization,
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
            "producer_backend": str(STAGE1_BACKEND.relative_to(ROOT.parent)),
        },
    }


def generic_alignment_summary(group_id: str) -> dict[str, Any]:
    shared = shared_geometry_bundle(group_id)
    single_bundle = generic_mode_bundle(group_id, "single")
    double_bundle = generic_mode_bundle(group_id, "double")

    def target_payload(bundle: dict[str, Any]) -> dict[str, Any]:
        return {
            "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
            "exact_alignment_status": "available",
            "object_kind": GENERIC_TARGET_OBJECT_KIND,
            "availability": "available",
            "compatibility_matrix_shape": bundle["compatibility"]["matrix_shape"],
            "current_row_compatibility_status": "available",
            "target_alignment_builder_status": "available",
            "local_ai_embedding_status": "available",
            "direct_quotient_status": "available",
            "ai_candidate_count": bundle["induced"]["candidate_count"],
            "ai_failure_count": bundle["induced"]["failure_count"],
        }

    current_row_shell = {
        "status": "available",
        "row_language_kind": "generic_current_row_shell_from_symmetry_ops",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "point_count": len(shared["point_ids"]),
        "point_ids": list(shared["point_ids"]),
    }
    local_ai_seed_builder = {
        "status": "available",
        "row_language_kind": "generic_local_ai_seed_from_site_symmetry_data",
        "coordinate_system": "post_supercell_primitive_basis_for_pipeline_modules",
        "realspace_wyckoff_family_count": len(single_bundle["local_library"]["families"]),
    }
    return {
        "generated_at": now_iso(),
        "group": group_id,
        "trust_policy": "symmetry_operations_only",
        "current_row_shell": current_row_shell,
        "local_ai_seed_builder": local_ai_seed_builder,
        "compatibility_builder": {
            "status": "available",
            "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
            "single_matrix_shape": single_bundle["compatibility"]["matrix_shape"],
            "double_matrix_shape": double_bundle["compatibility"]["matrix_shape"],
        },
        "single": {
            "raw": {
                "row_language_kind": current_row_shell["row_language_kind"],
                "exact_alignment_status": "not_applicable_current_row_shell_only",
                "object_kind": "generic_current_row_shell",
                "availability": "available",
            },
            "target": target_payload(single_bundle),
        },
        "double": {
            "raw": {
                "row_language_kind": current_row_shell["row_language_kind"],
                "exact_alignment_status": "not_applicable_current_row_shell_only",
                "object_kind": "generic_current_row_shell",
                "availability": "available",
            },
            "target": target_payload(double_bundle),
        },
    }


def generic_result_objects(group_id: str) -> list[dict[str, Any]]:
    results = []
    for mode in ("single", "double"):
        bundle = generic_mode_bundle(group_id, mode)
        quotient = bundle["quotient"]
        verification_status = "direct_code_computation_internal_consistency_passed"
        if quotient["ai_failure_count"] or quotient["ai_embedding_failure_count"]:
            verification_status = "failed_due_to_incomplete_ai_embedding_or_compatibility"
        elif quotient["ai_incompatible_count"]:
            verification_status = "direct_code_computation_after_exact_embedding_filter"
        results.append(
            {
                "object_id": f"{mode}_raw_shell",
                "mode": mode,
                "row_language_level": "raw",
                "row_language_kind": "generic_current_row_shell_from_symmetry_ops",
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
                "source_files": [str(STAGE1_BACKEND.relative_to(ROOT.parent))],
            }
        )
        results.append(
            {
                "object_id": f"{mode}_target_direct",
                "mode": mode,
                "row_language_level": "target",
                "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
                "object_kind": GENERIC_TARGET_OBJECT_KIND,
                "availability": "available",
                "dBS": quotient["dBS"],
                "dAI": quotient["dAI"],
                "classification": quotient["classification"],
                "free_rank": quotient["free_rank"],
                "finite_part": quotient["finite_part"],
                "quotient_derivation_mode": "direct_generic_bs_over_ai_smith",
                "exact_alignment_status": "available",
                "current_row_compatibility_status": "available",
                "target_alignment_status": "available",
                "local_ai_embedding_status": "available",
                "direct_quotient_status": "available",
                "verification_status": verification_status,
                "ai_candidate_count": quotient["ai_candidate_count"],
                "ai_candidate_count_used": quotient["ai_candidate_count_used"],
                "ai_failure_count": quotient["ai_failure_count"],
                "ai_incompatible_count": quotient["ai_incompatible_count"],
                "ai_embedding_failure_count": quotient["ai_embedding_failure_count"],
                "smith_diagonal_nonzero": quotient["smith_diagonal_nonzero"],
                "ai_incompatible_candidates": quotient["ai_incompatible_candidates"],
                "ai_embedding_failures": quotient["ai_embedding_failures"],
                "ai_filter_mode": "exact_point_shell_embedding_solve",
                "source_files": [
                    str(STAGE1_BACKEND.relative_to(ROOT.parent)),
                    str(LOCAL_LIBRARY_BACKEND.relative_to(ROOT.parent)),
                ],
            }
        )
    return results
