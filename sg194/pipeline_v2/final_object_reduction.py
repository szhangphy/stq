from __future__ import annotations

import json
from fractions import Fraction
from typing import Any, Iterable, Sequence

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

ZERO = Fraction(0, 1)
HALF = Fraction(1, 2)
PARSER_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


def _to_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, sp.Rational):
        return Fraction(int(value.p), int(value.q))
    raise TypeError(f"unsupported fraction value: {value!r}")


def _frac_str(value: Fraction) -> str:
    value = _to_fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _mod1(value: Fraction) -> Fraction:
    value = _to_fraction(value)
    return value - Fraction(value.numerator // value.denominator, 1)


def _jsonable_fraction(value: Fraction) -> str:
    return _frac_str(_to_fraction(value))


def _jsonable_vector(values: Sequence[Fraction]) -> list[str]:
    return [_jsonable_fraction(value) for value in values]


def _parse_coordinate_triplet(text: str) -> list[str]:
    return [item.strip() for item in text.split(",")]


def _parse_branch_expressions(
    coordinate_expressions: Sequence[str],
    parameter_name: str,
) -> tuple[list[sp.Expr], sp.Symbol]:
    symbol = sp.Symbol(parameter_name)
    local_dict = {parameter_name: symbol}
    expressions = [
        parse_expr(entry, local_dict=local_dict, transformations=PARSER_TRANSFORMS)
        for entry in coordinate_expressions
    ]
    return expressions, symbol


def _linear_constant_and_coeff(expression: sp.Expr, symbol: sp.Symbol) -> tuple[sp.Expr, sp.Expr]:
    expanded = sp.expand(expression)
    constant = sp.simplify(expanded.subs(symbol, 0))
    coeff = sp.simplify(sp.diff(expanded, symbol))
    residual = sp.simplify(expanded - constant - coeff * symbol)
    if residual != 0:
        raise ValueError(f"non-linear line orbit expression: {expression}")
    return constant, coeff


def _evaluate_branch_mod1(
    linear_parts: Sequence[tuple[sp.Expr, sp.Expr]],
    parameter_value: Fraction,
) -> list[Fraction]:
    exact_parameter = sp.Rational(parameter_value.numerator, parameter_value.denominator)
    values: list[Fraction] = []
    for constant, coeff in linear_parts:
        exact_value = sp.simplify(constant + coeff * exact_parameter)
        if not exact_value.is_rational:
            exact_value = sp.nsimplify(exact_value)
        if not isinstance(exact_value, sp.Rational):
            raise ValueError(f"non-rational branch value: {exact_value}")
        values.append(_mod1(Fraction(int(exact_value.p), int(exact_value.q))))
    return values


def _matches_point_alias(
    linear_parts: Sequence[tuple[sp.Expr, sp.Expr]],
    parameter_value: Fraction,
    point_coordinates: Sequence[Fraction],
) -> bool:
    return _evaluate_branch_mod1(linear_parts, parameter_value) == list(point_coordinates)


def _candidate_parameter_values_for_alias(
    linear_parts: Sequence[tuple[sp.Expr, sp.Expr]],
    point_coordinates: Sequence[Fraction],
) -> list[Fraction]:
    candidates: set[Fraction] | None = None
    for (constant, coeff), coordinate in zip(linear_parts, point_coordinates):
        exact_coordinate = sp.Rational(coordinate.numerator, coordinate.denominator)
        if coeff == 0:
            matches = [
                sp.simplify(constant - (exact_coordinate + shift)) == 0
                for shift in (-1, 0, 1)
            ]
            if not any(matches):
                return []
            continue
        dimension_candidates: set[Fraction] = set()
        for shift in (-1, 0, 1):
            value = sp.simplify((exact_coordinate + shift - constant) / coeff)
            if value.free_symbols:
                continue
            if not value.is_rational:
                value = sp.nsimplify(value)
            if not isinstance(value, sp.Rational):
                continue
            fraction = Fraction(int(value.p), int(value.q))
            if ZERO <= fraction <= HALF:
                dimension_candidates.add(fraction)
        if not dimension_candidates:
            return []
        candidates = dimension_candidates if candidates is None else candidates & dimension_candidates
        if not candidates:
            return []
    if candidates is None:
        return []
    verified = [
        value
        for value in sorted(candidates)
        if _matches_point_alias(linear_parts, value, point_coordinates)
    ]
    return verified


def _point_coordinate_alias_records(kgeom: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[tuple[str, tuple[str, str, str]], str]]:
    capture_lookup: dict[tuple[str, tuple[str, str, str]], str] = {}
    point_lookup = {point["id"]: point for point in kgeom["grouped"]["points"]}
    for point in kgeom.get("synthetic_boundary_points", []):
        point_lookup[point["id"]] = point
    for point_instance in kgeom.get("point_instance_entries", []):
        key = (point_instance["point_id"], tuple(point_instance["point_coordinates"]))
        capture_lookup[key] = point_instance["capture_id"]
    for line in kgeom["grouped"]["lines"]:
        for endpoint in line.get("endpoints", []):
            key = (endpoint["point_id"], tuple(endpoint["point_coordinates"]))
            capture_lookup[key] = endpoint.get("capture_id", endpoint["point_id"])
    for plane in kgeom["grouped"]["planes"]:
        for corner in plane.get("corner_entries", []):
            key = (corner["point_id"], tuple(corner["point_coordinates"]))
            capture_lookup[key] = corner.get("capture_id", corner["point_id"])

    point_shell: list[dict[str, Any]] = []
    for point in kgeom["grouped"]["points"]:
        alias_records: list[dict[str, Any]] = []
        seen_coords: set[tuple[str, str, str]] = set()
        candidate_aliases = [list(point["sample_point"])]
        for orbit_entry in point.get("metadata", {}).get("source_orbit", []):
            candidate_aliases.append(_parse_coordinate_triplet(orbit_entry))
        for point_instance in kgeom.get("point_instance_entries", []):
            if point_instance["point_id"] == point["id"]:
                candidate_aliases.append(list(point_instance["point_coordinates"]))
        for coords in candidate_aliases:
            coord_key = tuple(coords)
            if coord_key in seen_coords:
                continue
            seen_coords.add(coord_key)
            alias_records.append(
                {
                    "coordinates": list(coords),
                    "capture_id": capture_lookup.get((point["id"], coord_key), point["id"]),
                }
            )
        point_shell.append(
            {
                "point_id": point["id"],
                "label": point.get("label"),
                "representative_coordinates": list(point["sample_point"]),
                "aliases": alias_records,
            }
        )
    return point_shell, capture_lookup


def _branch_complexity(linear_parts: Sequence[tuple[sp.Expr, sp.Expr]]) -> int:
    total = Fraction(0, 1)
    for _constant, coeff in linear_parts:
        coeff = sp.nsimplify(coeff)
        if not isinstance(coeff, sp.Rational):
            raise ValueError(f"non-rational branch coefficient: {coeff}")
        total += abs(Fraction(int(coeff.p), int(coeff.q)))
    return int(total)


def _iter_branch_sources(kgeom: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for line in kgeom["grouped"]["lines"]:
        parameter_name = line["parameters"][0]
        source_orbit = line.get("metadata", {}).get("source_orbit") or [
            ", ".join(line["coordinate_expressions"])
        ]
        for branch_index, orbit_entry in enumerate(source_orbit, start=1):
            coordinate_expressions = _parse_coordinate_triplet(orbit_entry)
            yield {
                "source_kind": "listed_line",
                "source_id": line["id"],
                "source_line_id": line["id"],
                "branch_index": branch_index,
                "parameter_name": parameter_name,
                "coordinate_expressions": coordinate_expressions,
            }
    for plane in kgeom["grouped"]["planes"]:
        for boundary in plane.get("boundary_lines", []):
            matched_line_id = boundary.get("line_id") or boundary.get("special_line_orbit_match")
            if matched_line_id is None:
                continue
            parameter_name = boundary["parameters"][0]
            yield {
                "source_kind": "plane_boundary_orbit_match",
                "source_id": f"{plane['id']}::{boundary['boundary_condition']}",
                "source_line_id": matched_line_id,
                "branch_index": 1,
                "parameter_name": parameter_name,
                "coordinate_expressions": list(boundary["coordinate_expressions"]),
                "plane_id": plane["id"],
                "boundary_condition": boundary["boundary_condition"],
            }


def _enumerate_candidate_segments(kgeom: dict[str, Any], point_shell: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    candidate_index = 0
    for source in _iter_branch_sources(kgeom):
        parameter_name = source["parameter_name"]
        expressions, symbol = _parse_branch_expressions(source["coordinate_expressions"], parameter_name)
        linear_parts = [_linear_constant_and_coeff(expression, symbol) for expression in expressions]
        hits: dict[tuple[str, Fraction], dict[str, Any]] = {}
        for point_entry in point_shell:
            for alias in point_entry["aliases"]:
                point_coordinates = [_to_fraction(value) for value in alias["coordinates"]]
                for parameter_value in _candidate_parameter_values_for_alias(linear_parts, point_coordinates):
                    key = (point_entry["point_id"], parameter_value)
                    existing = hits.get(key)
                    candidate = {
                        "point_id": point_entry["point_id"],
                        "point_coordinates": list(alias["coordinates"]),
                        "capture_id": alias["capture_id"],
                        "parameter_value": parameter_value,
                    }
                    if existing is None or existing["capture_id"] == existing["point_id"]:
                        hits[key] = candidate
        ordered_hits = sorted(hits.values(), key=lambda item: (item["parameter_value"], item["point_id"]))
        if len(ordered_hits) < 2:
            continue
        anchor_hit = ordered_hits[0]
        for right in ordered_hits[1:]:
            left = anchor_hit
            if left["parameter_value"] == right["parameter_value"]:
                continue
            if left["point_id"] == right["point_id"]:
                continue
            candidate_index += 1
            sample_parameter = (left["parameter_value"] + right["parameter_value"]) / 2
            sample_point = _jsonable_vector(_evaluate_branch_mod1(linear_parts, sample_parameter))
            endpoint_pair = tuple(sorted((left["point_id"], right["point_id"])))
            candidates.append(
                {
                    "candidate_id": f"CANDIDATE_PATH_{candidate_index:03d}",
                    "source_kind": source["source_kind"],
                    "source_id": source["source_id"],
                    "source_line_id": source["source_line_id"],
                    "branch_index": int(source["branch_index"]),
                    "parameter_name": parameter_name,
                    "coordinate_expressions": list(source["coordinate_expressions"]),
                    "anchor": _jsonable_vector(
                        _evaluate_branch_mod1(linear_parts, ZERO)
                    ),
                    "basis": _jsonable_vector(
                        [
                            _to_fraction(coeff)
                            for _constant, coeff in linear_parts
                        ]
                    ),
                    "branch_complexity": _branch_complexity(linear_parts),
                    "endpoint_pair": list(endpoint_pair),
                    "endpoint_ids": [left["point_id"], right["point_id"]],
                    "endpoint_coordinates": [
                        list(left["point_coordinates"]),
                        list(right["point_coordinates"]),
                    ],
                    "endpoint_capture_ids": [left["capture_id"], right["capture_id"]],
                    "parameter_interval": [
                        _jsonable_fraction(left["parameter_value"]),
                        _jsonable_fraction(right["parameter_value"]),
                    ],
                    "sample_parameter": _jsonable_fraction(sample_parameter),
                    "sample_point": sample_point,
                    "selection_status": "candidate",
                }
            )
    return candidates


def _selection_rank(segment: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(segment["branch_complexity"]),
        0 if segment["source_kind"] == "listed_line" else 1,
        segment["source_line_id"],
        segment["source_id"],
        int(segment["branch_index"]),
        segment["coordinate_expressions"],
    )


def _final_path_sort_key(segment: dict[str, Any], point_order: dict[str, int]) -> tuple[int, int, str, str]:
    left_id, right_id = segment["endpoint_ids"]
    return (
        min(point_order[left_id], point_order[right_id]),
        max(point_order[left_id], point_order[right_id]),
        segment["source_line_id"],
        segment["source_id"],
    )


def reduce_final_point_path_shell(kgeom: dict[str, Any]) -> dict[str, Any]:
    point_shell, capture_lookup = _point_coordinate_alias_records(kgeom)
    point_order = {point["point_id"]: index for index, point in enumerate(point_shell)}
    candidate_segments = _enumerate_candidate_segments(kgeom, point_shell)

    by_endpoint_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for segment in candidate_segments:
        key = tuple(segment["endpoint_pair"])
        by_endpoint_pair.setdefault(key, []).append(segment)

    kept_segments: list[dict[str, Any]] = []
    discarded_segments: list[dict[str, Any]] = []
    for endpoint_pair, segments in sorted(by_endpoint_pair.items()):
        ranked = sorted(segments, key=_selection_rank)
        winner = dict(ranked[0])
        winner["selection_status"] = "kept_final_representative"
        winner["selection_reason"] = (
            "Selected as the simplest available representative for this endpoint pair "
            "after deduplicating orbit-equivalent raw/path candidates."
        )
        kept_segments.append(winner)
        for duplicate in ranked[1:]:
            dropped = dict(duplicate)
            dropped["selection_status"] = "discarded_duplicate_endpoint_pair"
            dropped["selection_reason"] = (
                "Discarded because another candidate with the same final endpoint pair "
                "has lower branch complexity or higher selection priority."
            )
            discarded_segments.append(dropped)

    final_point_ids = [
        point["point_id"]
        for point in point_shell
        if any(point["point_id"] in segment["endpoint_ids"] for segment in kept_segments)
    ]
    final_point_shell = [
        point
        for point in point_shell
        if point["point_id"] in set(final_point_ids)
    ]

    ordered_segments = sorted(
        kept_segments,
        key=lambda item: _final_path_sort_key(item, point_order),
    )
    final_line_specs: list[dict[str, Any]] = []
    for index, segment in enumerate(ordered_segments, start=1):
        final_path_id = f"FPATH{index:02d}"
        segment["final_path_id"] = final_path_id
        final_line_specs.append(
            {
                "id": final_path_id,
                "source_line_id": segment["source_line_id"],
                "source_kind": segment["source_kind"],
                "source_id": segment["source_id"],
                "branch_index": int(segment["branch_index"]),
                "parameter_name": segment["parameter_name"],
                "parameter_interval": list(segment["parameter_interval"]),
                "coordinate_expressions": list(segment["coordinate_expressions"]),
                "parametrization": f"({', '.join(segment['coordinate_expressions'])})",
                "sample_point": list(segment["sample_point"]),
                "_anchor": list(segment["anchor"]),
                "_basis": [list(segment["basis"])],
                "_params": [segment["parameter_name"]],
                "endpoints": [
                    {
                        "boundary_condition": f"{segment['parameter_name']} = {segment['parameter_interval'][0]}",
                        "point_id": segment["endpoint_ids"][0],
                        "point_coordinates": list(segment["endpoint_coordinates"][0]),
                        "capture_id": segment["endpoint_capture_ids"][0],
                    },
                    {
                        "boundary_condition": f"{segment['parameter_name']} = {segment['parameter_interval'][1]}",
                        "point_id": segment["endpoint_ids"][1],
                        "point_coordinates": list(segment["endpoint_coordinates"][1]),
                        "capture_id": segment["endpoint_capture_ids"][1],
                    },
                ],
                "selection_reason": segment["selection_reason"],
                "selection_source_metadata": {
                    "source_line_id": segment["source_line_id"],
                    "source_kind": segment["source_kind"],
                    "source_id": segment["source_id"],
                    "branch_index": int(segment["branch_index"]),
                    "endpoint_pair": list(segment["endpoint_pair"]),
                    "branch_complexity": int(segment["branch_complexity"]),
                },
            }
        )

    reduction = {
        "reduction_kind": "automatic_reduced_final_point_path_shell_v1",
        "raw_counts": {
            "grouped_point_count": len(kgeom["grouped"]["points"]),
            "grouped_line_count": len(kgeom["grouped"]["lines"]),
            "grouped_plane_count": len(kgeom["grouped"]["planes"]),
            "synthetic_boundary_point_count": len(kgeom.get("synthetic_boundary_points", [])),
            "point_capture_alias_count": len(kgeom.get("point_instance_entries", [])),
            "candidate_path_count": len(candidate_segments),
            "kept_final_path_count": len(final_line_specs),
            "discarded_duplicate_path_count": len(discarded_segments),
        },
        "point_shell": final_point_shell,
        "final_point_ids": list(final_point_ids),
        "candidate_paths": candidate_segments,
        "discarded_paths": discarded_segments,
        "kept_paths": ordered_segments,
        "final_line_specs": final_line_specs,
        "capture_lookup_size": len(capture_lookup),
    }
    return reduction


def build_reduction_report_markdown(reduction: dict[str, Any]) -> str:
    lines = [
        "# Automatic Final Object Reduction Report",
        "",
        "## Counts",
        "",
        f"- Raw grouped points / lines / planes: `{reduction['raw_counts']['grouped_point_count']}` / `{reduction['raw_counts']['grouped_line_count']}` / `{reduction['raw_counts']['grouped_plane_count']}`.",
        f"- Candidate paths enumerated: `{reduction['raw_counts']['candidate_path_count']}`.",
        f"- Final kept paths: `{reduction['raw_counts']['kept_final_path_count']}`.",
        f"- Discarded duplicate paths: `{reduction['raw_counts']['discarded_duplicate_path_count']}`.",
        "",
        "## Final Point Shell",
        "",
    ]
    for point in reduction["point_shell"]:
        alias_summary = ", ".join(
            f"{alias['capture_id']}@({', '.join(alias['coordinates'])})"
            for alias in point["aliases"]
        )
        lines.append(
            f"- `{point['point_id']}` at `({', '.join(point['representative_coordinates'])})`; aliases: {alias_summary}."
        )
    lines.extend(
        [
            "",
            "## Final Path Shell",
            "",
        ]
    )
    for segment in reduction["kept_paths"]:
        lines.append(
            "- "
            + f"`{segment['final_path_id']}`: `{segment['endpoint_ids'][0]} -> {segment['endpoint_ids'][1]}` "
            + f"from `{segment['source_line_id']}` branch `{segment['coordinate_expressions']}` "
            + f"on `{segment['parameter_name']}` in `{segment['parameter_interval'][0]} .. {segment['parameter_interval'][1]}`; "
            + f"reason: {segment['selection_reason']}"
        )
    if reduction["discarded_paths"]:
        lines.extend(["", "## Discarded Duplicates", ""])
        for segment in reduction["discarded_paths"]:
            lines.append(
                "- "
                + f"`{segment['source_line_id']}` / `{segment['coordinate_expressions']}` for endpoint pair "
                + f"`{segment['endpoint_pair'][0]}-{segment['endpoint_pair'][1]}` was dropped; "
                + f"reason: {segment['selection_reason']}"
            )
    return "\n".join(lines)


def compare_reduction_to_expected_pairs(
    reduction: dict[str, Any],
    *,
    expected_point_ids: Sequence[str],
    expected_endpoint_pairs: Sequence[Sequence[str]],
) -> dict[str, Any]:
    actual_point_ids = list(reduction["final_point_ids"])
    actual_pairs = sorted(tuple(sorted(segment["endpoint_pair"])) for segment in reduction["kept_paths"])
    expected_pairs_sorted = sorted(tuple(sorted(pair)) for pair in expected_endpoint_pairs)
    return {
        "actual_point_ids": actual_point_ids,
        "expected_point_ids": list(expected_point_ids),
        "actual_path_pairs": [list(pair) for pair in actual_pairs],
        "expected_path_pairs": [list(pair) for pair in expected_pairs_sorted],
        "point_ids_match": actual_point_ids == list(expected_point_ids),
        "point_count_match": len(actual_point_ids) == len(expected_point_ids),
        "path_pair_set_match": actual_pairs == expected_pairs_sorted,
        "path_count_match": len(actual_pairs) == len(expected_endpoint_pairs),
    }


def build_expected_check_markdown(check: dict[str, Any]) -> str:
    lines = [
        "# Final Object vs Bilbao-Equivalent Sanity Check",
        "",
        f"- Point count match: `{check['point_count_match']}`.",
        f"- Point id order match: `{check['point_ids_match']}`.",
        f"- Path count match: `{check['path_count_match']}`.",
        f"- Path pair set match: `{check['path_pair_set_match']}`.",
        "",
        "## Actual",
        "",
        f"- Final point ids: `{check['actual_point_ids']}`.",
        f"- Final path endpoint pairs: `{check['actual_path_pairs']}`.",
        "",
        "## Expected",
        "",
        f"- Expected point ids: `{check['expected_point_ids']}`.",
        f"- Expected path endpoint pairs: `{check['expected_path_pairs']}`.",
    ]
    return "\n".join(lines)
