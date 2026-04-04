from __future__ import annotations

import json
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
GENERIC_TARGET_ROW_LANGUAGE = "generic_target_row_language_pending_same_shell_builder"
GENERIC_TARGET_OBJECT_KIND = "generic_target_object_pending"
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
    return json.dumps(restricted_vector, sort_keys=True, separators=(",", ":"))


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
    surviving_ai_rank = len(smith_diag)
    surviving_finite_part = [value for value in smith_diag if value > 1]
    surviving_free_rank = int(bs_rank - surviving_ai_rank)
    surviving_classification = _quotient_group_string(surviving_free_rank, surviving_finite_part)
    final_available = not (rejected_candidates or embedding_failures or induced["failure_count"])
    return {
        "dBS": bs_rank,
        "dAI": surviving_ai_rank if final_available else None,
        "dbs_dai_gap": int(bs_rank - surviving_ai_rank) if final_available else None,
        "free_rank": surviving_free_rank if final_available else None,
        "finite_part": surviving_finite_part if final_available else [],
        "classification": surviving_classification if final_available else None,
        "surviving_ai_rank": surviving_ai_rank,
        "surviving_dbs_ai_gap": int(bs_rank - surviving_ai_rank),
        "surviving_free_rank": surviving_free_rank,
        "surviving_finite_part": surviving_finite_part,
        "surviving_classification": surviving_classification,
        "final_dai_available": final_available,
        "smith_diagonal_nonzero": smith_diag,
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

    try:
        quotient = _build_quotient_from_candidates(
            shared["target_point_ids"],
            bs_analysis["unknown_ordering"],
            bs_analysis,
            compatibility,
            induced,
        )
    except Exception as exc:
        message = str(exc)
        blocker_stage = "generic_direct_quotient_builder_error"
        if "generic point-shell projection lost rank" in message:
            blocker_stage = "generic_point_shell_projection_rank_loss"
        return _generic_progress_payload(
            group_id,
            mode,
            builder_variant,
            shared=shared,
            compatibility=compatibility,
            local_library=local_library,
            induced=induced,
            blocker_stage=blocker_stage,
            blocker=message,
            current_row_shell_status="available",
            local_ai_seed_status="available",
            compatibility_builder_status="available",
        )

    blocker = "generic/public target semantics still require a same-shell builder; projected point-shell quotient is diagnostic only"
    return _generic_progress_payload(
        group_id,
        mode,
        builder_variant,
        shared=shared,
        compatibility=compatibility,
        local_library=local_library,
        induced=induced,
        quotient=quotient,
        blocker_stage="generic_same_shell_target_builder_missing",
        blocker=blocker,
        current_row_shell_status="available",
        local_ai_seed_status="available",
        compatibility_builder_status="available",
        target_alignment_builder_status="blocked",
        generic_builder_ready=True,
        generic_published_classification_ready=False,
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
        quotient = progress.get("quotient") or {}
        return {
            "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
            "exact_alignment_status": progress.get("blocker_stage"),
            "object_kind": GENERIC_TARGET_OBJECT_KIND,
            "availability": "blocked",
            "compatibility_matrix_shape": progress.get("compatibility_matrix_shape"),
            "current_row_compatibility_status": progress.get("compatibility_builder_status"),
            "target_alignment_builder_status": progress.get("target_alignment_builder_status"),
            "local_ai_embedding_status": (
                "diagnostic_only_projected_point_shell"
                if quotient
                else "blocked_before_projected_point_shell_embedding"
            ),
            "direct_quotient_status": (
                "diagnostic_only_projected_point_shell"
                if quotient
                else progress.get("blocker_stage")
            ),
            "ai_candidate_count": progress.get("ai_candidate_count"),
            "ai_failure_count": progress.get("ai_failure_count"),
            "diagnostic_projected_point_shell_dbs": quotient.get("dBS"),
            "diagnostic_projected_point_shell_dai": quotient.get("dAI"),
            "diagnostic_projected_point_shell_classification": quotient.get("classification"),
            "generic_builder_ready": progress.get("generic_builder_ready", False),
            "generic_published_classification_ready": progress.get(
                "generic_published_classification_ready", False
            ),
            "blocker": progress.get("blocker"),
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
        quotient = progress.get("quotient") or {}
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
                "object_id": f"{mode}_target_pending",
                "mode": mode,
                "builder_variant": builder_variant,
                "row_language_level": "target",
                "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
                "object_kind": GENERIC_TARGET_OBJECT_KIND,
                "availability": "blocked",
                "dBS": None,
                "dAI": None,
                "classification": None,
                "free_rank": None,
                "finite_part": [],
                "surviving_ai_rank": quotient.get("surviving_ai_rank"),
                "surviving_classification": quotient.get("surviving_classification"),
                "surviving_free_rank": quotient.get("surviving_free_rank"),
                "surviving_finite_part": quotient.get("surviving_finite_part", []),
                "quotient_derivation_mode": "blocked_projected_point_shell_is_diagnostic_only",
                "exact_alignment_status": progress.get("blocker_stage"),
                "current_row_compatibility_status": progress.get("compatibility_builder_status"),
                "target_alignment_status": progress.get("target_alignment_builder_status"),
                "local_ai_embedding_status": (
                    "diagnostic_only_projected_point_shell"
                    if quotient
                    else "blocked_before_projected_point_shell_embedding"
                ),
                "direct_quotient_status": (
                    "diagnostic_only_projected_point_shell"
                    if quotient
                    else progress.get("blocker_stage")
                ),
                "verification_status": "blocked_projected_point_shell_result_not_published_as_active_object",
                "ai_candidate_count": progress.get("ai_candidate_count"),
                "ai_candidate_count_used": quotient.get("ai_candidate_count_used"),
                "ai_failure_count": progress.get("ai_failure_count"),
                "ai_incompatible_count": quotient.get("ai_incompatible_count"),
                "ai_embedding_failure_count": quotient.get("ai_embedding_failure_count"),
                "dbs_dai_gap": quotient.get("dbs_dai_gap"),
                "smith_diagonal_nonzero": quotient.get("smith_diagonal_nonzero"),
                "ai_incompatible_candidates": quotient.get("ai_incompatible_candidates", []),
                "ai_embedding_failures": quotient.get("ai_embedding_failures", []),
                "ai_filter_mode": "diagnostic_point_shell_projection_over_full_kernel_basis",
                "blocker": progress.get("blocker"),
                "generic_builder_ready": progress.get("generic_builder_ready", False),
                "generic_published_classification_ready": progress.get(
                    "generic_published_classification_ready", False
                ),
                "diagnostic_projected_point_shell_dbs": quotient.get("dBS"),
                "diagnostic_projected_point_shell_dai": quotient.get("dAI"),
                "diagnostic_projected_point_shell_classification": quotient.get("classification"),
                "source_files": [
                    str(RUNTIME_BACKEND.relative_to(ROOT.parent)),
                    str(LOCAL_IRREP_BACKEND.relative_to(ROOT.parent)),
                ],
            }
        )
    return results
