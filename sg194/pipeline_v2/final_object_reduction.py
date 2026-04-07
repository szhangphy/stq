from __future__ import annotations

from fractions import Fraction
from itertools import combinations, permutations, product
from math import factorial, gcd
from typing import Any, Iterable, Sequence

import sympy as sp
from common import swyckoff_k
from sympy.matrices.normalforms import smith_normal_form
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


def _symmetry_summary_signature(summary: dict[str, Any] | None) -> tuple[Any, ...]:
    summary = summary or {}
    return (
        int(summary.get("generic_rotation_stabilizer_size", -1)),
        int(summary.get("generic_stabilizer_size", -1)),
        int(summary.get("pointwise_rotation_stabilizer_size", -1)),
        int(summary.get("pointwise_stabilizer_size", -1)),
        str(summary.get("site_symmetry") or ""),
        str(summary.get("unitary_site_symmetry") or ""),
        str(summary.get("site_symmetry_custom") or ""),
    )


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


def _point_coordinate_alias_records(
    kgeom: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[tuple[str, tuple[str, str, str]], str]]:
    runtime_ctx = kgeom.get("runtime_ctx") or kgeom.get("ctx") or {}
    reciprocal_ops = runtime_ctx.get("ops") or []

    def symmetry_summary_key(summary: dict[str, Any] | None) -> tuple[Any, ...]:
        summary = summary or {}
        return (
            int(summary.get("generic_rotation_stabilizer_size", -1)),
            int(summary.get("generic_stabilizer_size", -1)),
            int(summary.get("pointwise_rotation_stabilizer_size", -1)),
            int(summary.get("pointwise_stabilizer_size", -1)),
            str(summary.get("site_symmetry") or ""),
            str(summary.get("unitary_site_symmetry") or ""),
            str(summary.get("site_symmetry_custom") or ""),
        )

    def line_family_key(line: dict[str, Any] | None) -> tuple[Any, ...]:
        if line is None:
            return ("line", None)
        return (
            "line",
            tuple(line.get("parameters", [])),
            symmetry_summary_key(line.get("symmetry_summary")),
        )

    def plane_family_key(plane: dict[str, Any] | None) -> tuple[Any, ...]:
        if plane is None:
            return ("plane", None)
        return (
            "plane",
            tuple(plane.get("parameters", [])),
            symmetry_summary_key(plane.get("symmetry_summary")),
        )

    def recovered_boundary_source_signature(point: dict[str, Any]) -> tuple[Any, ...] | None:
        metadata = point.get("metadata", {})
        if metadata.get("source_letter") != "recovered_boundary_point":
            return None
        source_records = (
            metadata.get("recovered_from_boundary_manifolds")
            or point.get("recovery_sources")
            or []
        )
        normalized: list[tuple[Any, ...]] = []
        for source in source_records:
            source_kind = str(source.get("source_kind"))
            if source_kind == "line_endpoint":
                normalized.append(
                    (
                        source_kind,
                        line_family_key(line_lookup.get(source.get("line_id"))),
                        str(source.get("boundary_condition") or ""),
                    )
                )
                continue
            if source_kind == "plane_corner":
                normalized.append(
                    (
                        source_kind,
                        plane_family_key(plane_lookup.get(source.get("plane_id"))),
                        tuple(str(value) for value in (source.get("boundary_coefficients") or [])),
                    )
                )
                continue
            normalized.append(
                (
                    source_kind,
                    tuple(
                        sorted(
                            (str(key), repr(value))
                            for key, value in source.items()
                            if key != "source_kind"
                        )
                    ),
                )
            )
        return tuple(sorted(normalized))

    def recovered_boundary_point_family_key(point: dict[str, Any]) -> tuple[Any, ...] | None:
        source_signature = recovered_boundary_source_signature(point)
        if source_signature is None:
            return None
        incident_line_signature = tuple(
            sorted(line_family_key(line_lookup.get(line_id)) for line_id in point.get("incident_lines", []))
        )
        incident_plane_signature = tuple(
            sorted(plane_family_key(plane_lookup.get(plane_id)) for plane_id in point.get("incident_planes", []))
        )
        return (
            "recovered_boundary_point_family",
            symmetry_summary_key(point.get("symmetry_summary")),
            incident_line_signature,
            incident_plane_signature,
            source_signature,
        )

    def publication_point_family_key(point: dict[str, Any]) -> tuple[Any, ...]:
        anchor = point.get("_anchor")
        if anchor is None:
            anchor = [_to_fraction(value) for value in point.get("sample_point", [])]
        else:
            anchor = [_to_fraction(value) for value in anchor]
        if reciprocal_ops:
            orbit_key = swyckoff_k.subspace_orbit_key(anchor, [], reciprocal_ops)
            return (
                "publication_point_orbit_family",
                orbit_key,
                symmetry_summary_key(point.get("symmetry_summary")),
            )
        recovered_key = recovered_boundary_point_family_key(point)
        if recovered_key is not None:
            return recovered_key
        return ("point_id", point["id"])

    capture_lookup: dict[tuple[str, tuple[str, str, str]], str] = {}
    point_lookup = {point["id"]: point for point in kgeom["grouped"]["points"]}
    line_lookup = {line["id"]: line for line in kgeom["grouped"]["lines"]}
    plane_lookup = {plane["id"]: plane for plane in kgeom["grouped"]["planes"]}
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

    grouped_candidates: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for point in kgeom["grouped"]["points"]:
        grouped_candidates.setdefault(publication_point_family_key(point), []).append(point)

    canonical_point_id_by_member: dict[str, str] = {}
    for members in grouped_candidates.values():
        canonical_members = sorted(
            members,
            key=lambda item: (
                int(item["id"][1:]) if item["id"].startswith("P") and item["id"][1:].isdigit() else item["id"]
            ),
        )
        root_id = canonical_members[0]["id"]
        for point in canonical_members:
            canonical_point_id_by_member[point["id"]] = root_id

    grouped_point_members: dict[str, list[dict[str, Any]]] = {}
    grouped_point_order: list[str] = []
    for point in kgeom["grouped"]["points"]:
        root_id = canonical_point_id_by_member.get(point["id"], point["id"])
        if root_id not in grouped_point_members:
            grouped_point_members[root_id] = []
            grouped_point_order.append(root_id)
        grouped_point_members[root_id].append(point)

    point_shell: list[dict[str, Any]] = []
    for root_id in grouped_point_order:
        members = grouped_point_members[root_id]
        point = next(item for item in members if item["id"] == root_id)
        alias_records: list[dict[str, Any]] = []
        seen_coords: set[tuple[str, str, str]] = set()
        for member in members:
            candidate_aliases = [list(member["sample_point"])]
            for orbit_entry in member.get("metadata", {}).get("source_orbit", []):
                candidate_aliases.append(_parse_coordinate_triplet(orbit_entry))
            for point_instance in kgeom.get("point_instance_entries", []):
                if point_instance["point_id"] == member["id"]:
                    candidate_aliases.append(list(point_instance["point_coordinates"]))
            for coords in candidate_aliases:
                coord_key = tuple(coords)
                if coord_key in seen_coords:
                    continue
                seen_coords.add(coord_key)
                alias_records.append(
                    {
                        "coordinates": list(coords),
                        "capture_id": capture_lookup.get((member["id"], coord_key), member["id"]),
                    }
                )
        point_shell.append(
            {
                "point_id": root_id,
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


def _enumerate_candidate_segments(
    kgeom: dict[str, Any],
    point_shell: list[dict[str, Any]],
) -> list[dict[str, Any]]:
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
                    "anchor": _jsonable_vector(_evaluate_branch_mod1(linear_parts, ZERO)),
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
        tuple(segment["coordinate_expressions"]),
    )


def _final_path_sort_key(
    segment: dict[str, Any],
    point_order: dict[str, int],
) -> tuple[int, int, str, str, int]:
    left_id, right_id = segment["endpoint_ids"]
    return (
        min(point_order[left_id], point_order[right_id]),
        max(point_order[left_id], point_order[right_id]),
        segment["source_line_id"],
        segment["source_id"],
        int(segment["branch_index"]),
    )


def _segment_to_line_spec(segment: dict[str, Any], *, line_id: str | None = None) -> dict[str, Any]:
    actual_id = line_id or segment["candidate_id"]
    return {
        "id": actual_id,
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
        "selection_source_metadata": {
            "candidate_id": segment["candidate_id"],
            "source_line_id": segment["source_line_id"],
            "source_kind": segment["source_kind"],
            "source_id": segment["source_id"],
            "branch_index": int(segment["branch_index"]),
            "endpoint_pair": list(segment["endpoint_pair"]),
            "branch_complexity": int(segment["branch_complexity"]),
        },
    }


def _interval_length(segment: dict[str, Any]) -> Fraction:
    left, right = (_to_fraction(value) for value in segment["parameter_interval"])
    return right - left


def _entry_str(value: Any) -> str:
    if isinstance(value, (int, Fraction)):
        return str(value)
    if isinstance(value, sp.Basic):
        value = sp.nsimplify(value)
        return str(value)
    return str(value)


def _row_rank(rows: Sequence[Sequence[int]]) -> int:
    if not rows:
        return 0
    return int(sp.Matrix(rows).rank())


def _rref_basis_rows(rows: Sequence[Sequence[int]]) -> list[list[str]]:
    if not rows:
        return []
    rref_matrix, _ = sp.Matrix(rows).rref()
    basis_rows: list[list[str]] = []
    for row in rref_matrix.tolist():
        if any(value != 0 for value in row):
            basis_rows.append([_entry_str(value) for value in row])
    return basis_rows


def _rref_signature(rows: Sequence[Sequence[int]]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(row) for row in _rref_basis_rows(rows))


def _smith_diagonal(rows: Sequence[Sequence[int]]) -> list[str]:
    if not rows:
        return []
    smith = smith_normal_form(sp.Matrix(rows))
    diagonal: list[str] = []
    for index in range(min(smith.rows, smith.cols)):
        value = smith[index, index]
        if value != 0:
            diagonal.append(_entry_str(abs(value)))
    return diagonal


def _row_space_signature(rows: Sequence[Sequence[int]]) -> dict[str, Any]:
    return {
        "row_count": len(rows),
        "row_rank": _row_rank(rows),
        "smith_diagonal": _smith_diagonal(rows),
        "rref_basis_rows": _rref_basis_rows(rows),
    }


def _apply_column_permutation(
    rows: Sequence[Sequence[int]],
    column_map: Sequence[int],
) -> list[list[int]]:
    return [[int(row[column_map[index]]) for index in range(len(column_map))] for row in rows]


def _line_group_signature_key(signature: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(signature["n_ops_total"]),
        int(signature["n_unitary_ops"]),
        int(signature["n_antiunitary_ops"]),
        tuple(int(value) for value in signature["rep_degree"]),
        tuple(int(value) for value in signature["torsion"]),
    )


def _endpoint_decomposition_signature(block: dict[str, Any]) -> list[dict[str, Any]]:
    signature: list[dict[str, Any]] = []
    for endpoint_id in sorted(block["endpoint_decompositions"]):
        reps = []
        for rep in block["endpoint_decompositions"][endpoint_id]:
            reps.append(
                {
                    "rep_id": rep["rep_id"],
                    "rep_degree": int(rep["rep_degree"]),
                    "torsion": int(rep["torsion"]),
                    "decomposition_on_line_basis": {
                        label: int(value)
                        for label, value in sorted(rep["decomposition_on_line_basis"].items())
                    },
                }
            )
        signature.append({"endpoint_id": endpoint_id, "reps": reps})
    return signature


def _endpoint_decomposition_signature_key(block: dict[str, Any]) -> tuple[Any, ...]:
    line_basis_labels = list(block["line_basis_labels"])
    return tuple(
        (
            endpoint["endpoint_id"],
            tuple(
                (
                    rep["rep_id"],
                    int(rep["rep_degree"]),
                    int(rep["torsion"]),
                    tuple(
                        int(rep["decomposition_on_line_basis"].get(label, 0))
                        for label in line_basis_labels
                    ),
                )
                for rep in endpoint["reps"]
            ),
        )
        for endpoint in _endpoint_decomposition_signature(block)
    )


def _phase_aware_refinement_signature(refinement: dict[str, Any]) -> dict[str, Any]:
    classes = []
    for endpoint_id in sorted(refinement.get("restriction_classes_by_endpoint", {})):
        endpoint_classes = []
        for entry in refinement["restriction_classes_by_endpoint"][endpoint_id]:
            endpoint_classes.append(
                {
                    "rep_ids": list(entry["rep_ids"]),
                    "class_size": int(entry["class_size"]),
                }
            )
        classes.append({"endpoint_id": endpoint_id, "restriction_classes": endpoint_classes})
    return {
        "profile": refinement.get("profile", "legacy"),
        "selected_endpoint_id": refinement.get("selected_endpoint_id"),
        "restriction_classes": classes,
    }


def _phase_aware_refinement_key(refinement: dict[str, Any]) -> tuple[Any, ...]:
    signature = _phase_aware_refinement_signature(refinement)
    return (
        signature["profile"],
        signature["selected_endpoint_id"],
        tuple(
            (
                entry["endpoint_id"],
                tuple(
                    (tuple(item["rep_ids"]), int(item["class_size"]))
                    for item in entry["restriction_classes"]
                ),
            )
            for entry in signature["restriction_classes"]
        ),
    )


def _block_rows_on_point_shell(
    block: dict[str, Any],
    ordering: Sequence[str],
) -> list[list[int]]:
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    rows: list[list[int]] = []
    for equation in block["equations"]:
        row = [0] * len(ordering)
        for term in equation["terms"]:
            row[unknown_index[term["unknown"]]] += int(term["coeff"])
        rows.append(row)
    return rows


def _normalized_line_basis_labels(record: dict[str, Any]) -> list[str]:
    labels = [str(label) for label in record.get("line_basis_labels", [])]
    if labels:
        return labels
    discovered: list[str] = []
    seen: set[str] = set()
    for endpoint in record.get("endpoint_decomposition_signature", []):
        for rep in endpoint.get("reps", []):
            for label in rep.get("decomposition_on_line_basis", {}):
                label = str(label)
                if label in seen:
                    continue
                seen.add(label)
                discovered.append(label)
    return discovered


def _normalized_line_monodromy_basis_orbits(record: dict[str, Any]) -> list[list[str]]:
    labels = _normalized_line_basis_labels(record)
    if not labels:
        return []
    raw_orbits = list(record.get("line_monodromy_basis_orbits", []))
    if not raw_orbits:
        return [[label] for label in labels]
    label_set = set(labels)
    normalized: list[list[str]] = []
    seen: set[str] = set()
    for orbit in raw_orbits:
        cleaned: list[str] = []
        for label in orbit:
            label = str(label)
            if label not in label_set or label in seen:
                continue
            seen.add(label)
            cleaned.append(label)
        if cleaned:
            normalized.append(cleaned)
    for label in labels:
        if label not in seen:
            normalized.append([label])
    return normalized


def _nontrivial_monodromy_orbit_count(record: dict[str, Any]) -> int:
    return sum(
        1
        for orbit in _normalized_line_monodromy_basis_orbits(record)
        if len(orbit) > 1
    )


def _line_basis_rep_degree_map(record: dict[str, Any]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for endpoint in record.get("endpoint_decomposition_signature", []):
        for rep in endpoint.get("reps", []):
            degree = int(rep.get("rep_degree", 0))
            for basis_label, coeff in rep.get("decomposition_on_line_basis", {}).items():
                if int(coeff) == 0:
                    continue
                label = str(basis_label)
                existing = mapping.get(label)
                if existing is None or degree > existing:
                    mapping[label] = degree
    return mapping


def _single_multidimensional_monodromy_orbit_available(record: dict[str, Any]) -> bool:
    basis_orbits = _normalized_line_monodromy_basis_orbits(record)
    nontrivial_orbits = [orbit for orbit in basis_orbits if len(orbit) > 1]
    if len(nontrivial_orbits) != 1:
        return False
    if sum(len(orbit) for orbit in basis_orbits) != len(nontrivial_orbits[0]):
        return False
    rep_degree_by_label = _line_basis_rep_degree_map(record)
    orbit = nontrivial_orbits[0]
    if not orbit:
        return False
    return all(int(rep_degree_by_label.get(label, 0)) > 1 for label in orbit)


def _raw_rows_are_pure_endpoint_branch_differences(record: dict[str, Any]) -> bool:
    endpoint_signatures = list(record.get("endpoint_decomposition_signature", []))
    if len(endpoint_signatures) != 2:
        return False
    endpoint_rep_sets = [
        {str(rep["rep_id"]) for rep in endpoint.get("reps", [])}
        for endpoint in endpoint_signatures
    ]
    unknown_ordering = [str(item) for item in record.get("global_unknown_ordering", [])]
    if not all(endpoint_rep_sets):
        return False
    row_records = list(record.get("global_matrix_row_records", []))
    if not row_records:
        return False
    for row_record in row_records:
        row = [int(value) for value in row_record.get("matrix_row", [])]
        support = [
            (unknown_ordering[column_index], int(value))
            for column_index, value in enumerate(row)
            if int(value) != 0
        ]
        if len(support) != 2:
            return False
        coeffs = {coeff for _, coeff in support}
        if coeffs != {1, -1}:
            return False
        endpoint_hits = [0, 0]
        for unknown, _ in support:
            if unknown in endpoint_rep_sets[0]:
                endpoint_hits[0] += 1
            elif unknown in endpoint_rep_sets[1]:
                endpoint_hits[1] += 1
            else:
                return False
        if endpoint_hits != [1, 1]:
            return False
    return True


def _monodromy_compressed_row_records(
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    basis_labels = _normalized_line_basis_labels(record)
    basis_orbits = _normalized_line_monodromy_basis_orbits(record)
    if not basis_labels or not basis_orbits or all(len(orbit) <= 1 for orbit in basis_orbits):
        return list(record["global_matrix_row_records"])
    unknown_ordering = list(record["global_unknown_ordering"])
    unknown_index = {unknown: index for index, unknown in enumerate(unknown_ordering)}
    basis_unknown_count = len(basis_labels)
    basis_unknown_index = {
        label: len(unknown_ordering) + basis_index
        for basis_index, label in enumerate(basis_labels)
    }
    incidence_rows: list[list[int]] = []
    incidence_metadata: list[dict[str, Any]] = []
    for endpoint in record["endpoint_decomposition_signature"]:
        endpoint_id = endpoint["endpoint_id"]
        for basis_label in basis_labels:
            row = [0] * (len(unknown_ordering) + basis_unknown_count)
            support_terms: list[dict[str, Any]] = []
            for rep in endpoint["reps"]:
                coeff = int(rep["decomposition_on_line_basis"].get(basis_label, 0))
                if coeff == 0:
                    continue
                row[unknown_index[rep["rep_id"]]] += int(coeff)
                support_terms.append(
                    {
                        "rep_id": rep["rep_id"],
                        "coeff": int(coeff),
                    }
                )
            if not support_terms:
                continue
            row[basis_unknown_index[basis_label]] = -1
            incidence_rows.append(row)
            incidence_metadata.append(
                {
                    "endpoint_id": endpoint_id,
                    "basis_label": basis_label,
                    "support_terms": support_terms,
                }
            )
    for orbit in basis_orbits:
        if len(orbit) <= 1:
            continue
        anchor = orbit[0]
        for other in orbit[1:]:
            row = [0] * (len(unknown_ordering) + basis_unknown_count)
            row[basis_unknown_index[anchor]] = 1
            row[basis_unknown_index[other]] = -1
            incidence_rows.append(row)
            incidence_metadata.append(
                {
                    "endpoint_id": None,
                    "basis_label": f"{anchor}__{other}",
                    "support_terms": [],
                    "monodromy_equation": {
                        "anchor_basis_label": anchor,
                        "other_basis_label": other,
                    },
                }
            )
    if not incidence_rows:
        return list(record["global_matrix_row_records"])
    incidence_matrix = sp.Matrix(incidence_rows)
    aux_block = incidence_matrix[:, len(unknown_ordering):]
    left_nullspace = aux_block.T.nullspace()
    if not left_nullspace:
        return list(record["global_matrix_row_records"])
    candidate_rows: list[dict[str, Any]] = []
    for relation_index, coefficients in enumerate(left_nullspace, start=1):
        combined = coefficients.T * incidence_matrix
        point_row = list(combined.tolist()[0][: len(unknown_ordering)])
        primitive = _primitive_integer_row(point_row)
        if not any(primitive):
            continue
        support_incidence_rows = [
            incidence_metadata[row_index]
            for row_index, value in enumerate(coefficients)
            if sp.nsimplify(value) != 0
        ]
        candidate_rows.append(
            {
                "row_index_within_candidate_block": relation_index - 1,
                "basis_id": f"{record['candidate_id']}_MONO_{relation_index:02d}",
                "row_kind": "line_monodromy_orbit_compressed_basis",
                "matrix_row": primitive,
                "monodromy_basis_orbits": [list(orbit) for orbit in basis_orbits],
                "monodromy_support_rows": support_incidence_rows,
            }
        )
    candidate_rows.sort(key=lambda item: (tuple(item["matrix_row"]), item["basis_id"]))
    selected_rows, _ = _rank_gaining_row_records(candidate_rows)
    return selected_rows or list(record["global_matrix_row_records"])


def build_candidate_path_records(
    reduction: dict[str, Any],
    candidate_line_blocks: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    point_ids = [point["point_id"] for point in reduction["point_shell"]]
    block_by_id = {block["line_id"]: block for block in candidate_line_blocks}
    per_point_ids: dict[str, list[str]] = {}
    for block in candidate_line_blocks:
        for endpoint_id in block["endpoint_ids"]:
            rep_ids = [
                item["rep_id"]
                for item in block["endpoint_decompositions"][endpoint_id]
            ]
            existing = per_point_ids.get(endpoint_id)
            if existing is None:
                per_point_ids[endpoint_id] = rep_ids
            elif existing != rep_ids:
                raise ValueError(f"inconsistent point-shell rep ordering for {endpoint_id}")
    global_unknown_ordering: list[str] = []
    for point_id in point_ids:
        global_unknown_ordering.extend(per_point_ids.get(point_id, []))
    records: list[dict[str, Any]] = []
    for segment in reduction["candidate_paths"]:
        block = block_by_id[segment["candidate_id"]]
        global_rows = _block_rows_on_point_shell(block, global_unknown_ordering)
        global_row_records = [
            {
                "row_index_within_candidate_block": row_index,
                "basis_id": equation["basis_id"],
                "row_kind": equation.get("row_kind", "line_basis_decomposition"),
                "matrix_row": list(row),
            }
            for row_index, (equation, row) in enumerate(zip(block["equations"], global_rows))
        ]
        local_signature = _row_space_signature(block["matrix_rows"])
        global_signature = _row_space_signature(global_rows)
        record = {
            **segment,
            "line_group_signature": block["line_group_signature"],
            "line_basis_labels": list(block.get("line_basis_labels", [])),
            "line_monodromy_debug": dict(block.get("line_monodromy_debug", {})),
            "line_monodromy_basis_orbits": [
                list(item) for item in block.get("line_monodromy_basis_orbits", [])
            ],
            "endpoint_decomposition_signature": _endpoint_decomposition_signature(block),
            "local_row_space_signature": local_signature,
            "global_row_space_signature": global_signature,
            "phase_aware_profile_used": block.get("phase_aware_profile_used", "legacy"),
            "phase_aware_refinement_signature": _phase_aware_refinement_signature(
                block.get("phase_aware_refinement", {})
            ),
            "selection_rank": list(_selection_rank(segment)),
            "global_unknown_ordering": list(global_unknown_ordering),
            "global_matrix_rows": global_rows,
            "global_matrix_row_records": global_row_records,
        }
        compressed_row_records = _monodromy_compressed_row_records(record)
        record["monodromy_compressed_global_matrix_row_records"] = compressed_row_records
        record["monodromy_compressed_global_matrix_rows"] = [
            list(row_record["matrix_row"]) for row_record in compressed_row_records
        ]
        record["monodromy_compressed_global_row_space_signature"] = _row_space_signature(
            record["monodromy_compressed_global_matrix_rows"]
        )
        record["line_monodromy_nontrivial_orbit_count"] = _nontrivial_monodromy_orbit_count(record)
        record["raw_rows_are_pure_endpoint_branch_differences"] = (
            _raw_rows_are_pure_endpoint_branch_differences(record)
        )
        record["line_monodromy_compression_available"] = (
            compressed_row_records != global_row_records
            and record["raw_rows_are_pure_endpoint_branch_differences"]
            and (
                record["line_monodromy_nontrivial_orbit_count"] >= 2
                or _single_multidimensional_monodromy_orbit_available(record)
            )
        )
        record["path_type_key"] = (
            tuple(record["endpoint_pair"]),
            str(record["source_kind"]),
            str(record["source_line_id"]),
            _line_group_signature_key(record["line_group_signature"]),
        )
        records.append(record)
    return records


def _stack_rows(records: Sequence[dict[str, Any]]) -> list[list[int]]:
    rows: list[list[int]] = []
    for record in records:
        rows.extend(record["global_matrix_rows"])
    return rows


def _rows_rank_after_append(
    base_rows: Sequence[Sequence[int]],
    extra_rows: Sequence[Sequence[int]],
) -> tuple[int, int]:
    before_rank = _row_rank(base_rows)
    after_rank = _row_rank(list(base_rows) + list(extra_rows))
    return before_rank, after_rank


def _unique_endpoint_pair_keys(
    records: Sequence[dict[str, Any]],
) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    ordered: list[tuple[str, str]] = []
    for record in records:
        pair = tuple(record["endpoint_pair"])
        if pair in seen:
            continue
        seen.add(pair)
        ordered.append(pair)
    return ordered


def _first_rank_gaining_row_record(
    base_rows: Sequence[Sequence[int]],
    row_records: Sequence[dict[str, Any]],
) -> tuple[int | None, dict[str, Any] | None, int, int]:
    running_rows = [list(row) for row in base_rows]
    running_rank = _row_rank(running_rows)
    for row_index, row_record in enumerate(row_records):
        candidate_rank = _row_rank(running_rows + [list(row_record["matrix_row"])])
        if candidate_rank > running_rank:
            return row_index, row_record, running_rank, candidate_rank
    return None, None, running_rank, running_rank


def _candidate_sort_key(
    record: dict[str, Any],
    point_order: dict[str, int],
) -> tuple[Any, ...]:
    return _final_path_sort_key(record, point_order) + _selection_rank(record)


def analyze_candidate_path_selection(
    reduction: dict[str, Any],
    candidate_records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    point_order = {
        point["point_id"]: index
        for index, point in enumerate(reduction["point_shell"])
    }
    by_path_type: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for record in candidate_records:
        by_path_type.setdefault(record["path_type_key"], []).append(record)

    class_records: list[dict[str, Any]] = []
    for path_type_key, records in by_path_type.items():
        ranked = sorted(records, key=lambda item: _candidate_sort_key(item, point_order))
        representative = ranked[0]
        class_records.append(
            {
                "path_type_key": path_type_key,
                "endpoint_pair": list(representative["endpoint_pair"]),
                "representative": representative,
                "candidate_records": ranked,
                "class_row_rank": representative["global_row_space_signature"]["row_rank"],
                "class_sort_key": _candidate_sort_key(representative, point_order),
            }
        )

    class_records.sort(key=lambda item: item["class_sort_key"])
    for class_index, class_record in enumerate(class_records, start=1):
        path_class_id = f"PCLASS{class_index:02d}"
        class_record["path_class_id"] = path_class_id
        for candidate_record in class_record["candidate_records"]:
            candidate_record["path_class_id"] = path_class_id
            candidate_record["path_class_candidate_count"] = len(class_record["candidate_records"])

    target_rank = _row_rank(_stack_rows([item["representative"] for item in class_records]))
    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for class_record in class_records:
        by_pair.setdefault(tuple(class_record["endpoint_pair"]), []).append(class_record)

    endpoint_pair_skeleton = [
        min(by_pair[pair_key], key=lambda item: item["class_sort_key"])
        for pair_key in sorted(by_pair)
    ]
    endpoint_pair_skeleton.sort(key=lambda item: item["class_sort_key"])
    endpoint_pair_skeleton_ids = [item["path_class_id"] for item in endpoint_pair_skeleton]

    selected_classes = list(endpoint_pair_skeleton)
    selected_rows = _stack_rows([item["representative"] for item in selected_classes])
    selected_rank = _row_rank(selected_rows)
    endpoint_pair_skeleton_rank = selected_rank

    augmentation_classes: list[dict[str, Any]] = []
    if selected_rank < target_rank:
        for class_record in class_records:
            if class_record["path_class_id"] in endpoint_pair_skeleton_ids:
                continue
            before_rank, after_rank = _rows_rank_after_append(
                selected_rows,
                class_record["representative"]["global_matrix_rows"],
            )
            if after_rank > before_rank:
                selected_classes.append(class_record)
                augmentation_classes.append(class_record)
                selected_rows.extend(class_record["representative"]["global_matrix_rows"])
                selected_rank = after_rank
            if selected_rank == target_rank:
                break

    if selected_rank != target_rank:
        raise RuntimeError(
            "final point/path reduction failed to span the full candidate row language "
            f"(selected_rank={selected_rank}, target_rank={target_rank})"
        )

    selected_class_ids = {item["path_class_id"] for item in selected_classes}
    augmentation_class_ids = {item["path_class_id"] for item in augmentation_classes}
    pair_selection_count: dict[tuple[str, str], int] = {}
    for class_record in selected_classes:
        pair_key = tuple(class_record["endpoint_pair"])
        pair_selection_count[pair_key] = pair_selection_count.get(pair_key, 0) + 1

    path_classes: list[dict[str, Any]] = []
    for class_record in class_records:
        path_class_id = class_record["path_class_id"]
        representative = dict(class_record["representative"])
        class_rows = representative["global_matrix_rows"]
        contained = _row_rank(selected_rows + class_rows) == selected_rank
        selection_stage = (
            "full_span_augmentation"
            if path_class_id in augmentation_class_ids
            else (
                "endpoint_pair_skeleton"
                if path_class_id in selected_class_ids
                else "discarded"
            )
        )
        pair_key = tuple(class_record["endpoint_pair"])
        if selection_stage == "endpoint_pair_skeleton":
            if pair_selection_count[pair_key] > 1:
                selection_reason = (
                    "Selected first as the canonical endpoint-pair skeleton representative, "
                    "then retained in the published shell together with an additional "
                    "same-endpoint path class because the skeleton alone did not span the "
                    "full candidate row language."
                )
            else:
                selection_reason = (
                    "Selected as the canonical endpoint-pair skeleton representative: "
                    "shortest primitive segment first, then listed-line priority, then "
                    "branch simplicity."
                )
        elif selection_stage == "full_span_augmentation":
            rank_before, rank_after = _rows_rank_after_append(
                _stack_rows([item["representative"] for item in endpoint_pair_skeleton]),
                class_rows,
            )
            selection_reason = (
                "Added after the canonical endpoint-pair skeleton because it contributes "
                f"independent row language not present in the skeleton span (rank {rank_before} -> {rank_after})."
            )
        else:
            selection_reason = (
                "Discarded because the published full-span selection already contains its "
                "row language after endpoint-pair skeleton selection and rank-closing augmentation."
            )
        path_classes.append(
            {
                "path_class_id": path_class_id,
                "endpoint_pair": list(class_record["endpoint_pair"]),
                "selected_as_final": path_class_id in selected_class_ids,
                "path_class_candidate_count": len(class_record["candidate_records"]),
                "candidate_ids": [item["candidate_id"] for item in class_record["candidate_records"]],
                "representative_candidate_id": representative["candidate_id"],
                "representative_source_line_id": representative["source_line_id"],
                "representative_source_kind": representative["source_kind"],
                "representative_source_id": representative["source_id"],
                "representative_branch_index": int(representative["branch_index"]),
                "line_group_signature": representative["line_group_signature"],
                "endpoint_decomposition_signature": representative["endpoint_decomposition_signature"],
                "local_row_space_signature": representative["local_row_space_signature"],
                "global_row_space_signature": representative["global_row_space_signature"],
                "phase_aware_profile_used": representative["phase_aware_profile_used"],
                "phase_aware_refinement_signature": representative["phase_aware_refinement_signature"],
                "selection_stage": selection_stage,
                "selection_reason": selection_reason,
                "row_space_contained_in_selected_span": contained,
                "candidate_records": class_record["candidate_records"],
            }
        )

    path_class_payload_by_id = {payload["path_class_id"]: payload for payload in path_classes}
    ordered_selected = sorted(
        [path_class_payload_by_id[class_record["path_class_id"]] for class_record in selected_classes],
        key=lambda item: _final_path_sort_key(item["candidate_records"][0], point_order),
    )
    final_line_specs: list[dict[str, Any]] = []
    kept_paths: list[dict[str, Any]] = []
    running_rows: list[list[int]] = []
    for index, class_payload in enumerate(ordered_selected, start=1):
        representative = dict(class_payload["candidate_records"][0])
        final_path_id = f"FPATH{index:02d}"
        before_rank = _row_rank(running_rows)
        running_rows.extend(representative["global_matrix_rows"])
        after_rank = _row_rank(running_rows)
        representative["final_path_id"] = final_path_id
        representative["selection_status"] = "kept_final_representative"
        representative["selection_reason"] = class_payload["selection_reason"]
        representative["selection_stage"] = class_payload["selection_stage"]
        representative["rank_gain_within_final_order"] = after_rank - before_rank
        representative["path_class_id"] = class_payload["path_class_id"]
        kept_paths.append(representative)
        final_line_specs.append(_segment_to_line_spec(representative, line_id=final_path_id))

    discarded_paths: list[dict[str, Any]] = []
    selected_candidate_ids = {
        item["candidate_records"][0]["candidate_id"]
        for item in ordered_selected
    }
    for class_payload in path_classes:
        representative_id = class_payload["representative_candidate_id"]
        for record in class_payload["candidate_records"]:
            dropped = dict(record)
            dropped["path_class_id"] = class_payload["path_class_id"]
            if record["candidate_id"] == representative_id and record["candidate_id"] in selected_candidate_ids:
                continue
            if record["candidate_id"] == representative_id:
                dropped["selection_status"] = "discarded_redundant_path_class"
                dropped["selection_reason"] = class_payload["selection_reason"]
            else:
                dropped["selection_status"] = "discarded_duplicate_path_class_member"
                dropped["selection_reason"] = (
                    "Discarded because another candidate in the same path class was chosen "
                    "as the canonical representative before the final path-class selection."
                )
            discarded_paths.append(dropped)

    final_point_ids = sorted(
        {
            point_id
            for record in kept_paths
            for point_id in record["endpoint_ids"]
        },
        key=point_order.get,
    )
    return {
        "candidate_path_records": list(candidate_records),
        "path_classes": path_classes,
        "selected_path_classes": ordered_selected,
        "redundant_path_classes": [payload for payload in path_classes if not payload["selected_as_final"]],
        "selection_policy": (
            "canonical endpoint-pair skeleton first, then deterministic rank-closing "
            "augmentation classes until the full candidate row language is spanned"
        ),
        "endpoint_pair_skeleton_path_class_ids": endpoint_pair_skeleton_ids,
        "endpoint_pair_skeleton_row_rank": endpoint_pair_skeleton_rank,
        "selection_augmentation_path_class_ids": [item["path_class_id"] for item in augmentation_classes],
        "selected_source_line_ids": [item["representative"]["source_line_id"] for item in selected_classes],
        "target_row_rank": target_rank,
        "selected_row_rank": selected_rank,
        "selected_rows_span_full_candidate_row_language": selected_rank == target_rank,
        "target_unique_endpoint_pair_count": len(by_pair),
        "selected_unique_endpoint_pairs": [list(pair) for pair in _unique_endpoint_pair_keys(kept_paths)],
        "selected_unique_endpoint_pair_count": len(_unique_endpoint_pair_keys(kept_paths)),
        "final_point_ids": final_point_ids,
        "final_line_specs": final_line_specs,
        "kept_paths": kept_paths,
        "discarded_paths": discarded_paths,
    }


def finalize_reduction_from_candidate_analysis(
    reduction: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    reduction = dict(reduction)
    reduction["reduction_kind"] = "automatic_reduced_final_point_path_shell_v3_fullspan_augmented"
    reduction["path_class_count"] = len(analysis["path_classes"])
    reduction["selected_path_class_count"] = len(analysis["selected_path_classes"])
    reduction["candidate_path_records"] = analysis["candidate_path_records"]
    reduction["path_classes"] = analysis["path_classes"]
    reduction["selection_policy"] = analysis["selection_policy"]
    reduction["endpoint_pair_skeleton_path_class_ids"] = analysis["endpoint_pair_skeleton_path_class_ids"]
    reduction["endpoint_pair_skeleton_row_rank"] = analysis["endpoint_pair_skeleton_row_rank"]
    reduction["selection_augmentation_path_class_ids"] = analysis["selection_augmentation_path_class_ids"]
    reduction["target_row_rank"] = analysis["target_row_rank"]
    reduction["selected_row_rank"] = analysis["selected_row_rank"]
    reduction["selected_rows_span_full_candidate_row_language"] = analysis[
        "selected_rows_span_full_candidate_row_language"
    ]
    reduction["target_unique_endpoint_pair_count"] = analysis["target_unique_endpoint_pair_count"]
    reduction["selected_unique_endpoint_pairs"] = analysis["selected_unique_endpoint_pairs"]
    reduction["selected_unique_endpoint_pair_count"] = analysis["selected_unique_endpoint_pair_count"]
    reduction["final_point_ids"] = analysis["final_point_ids"]
    reduction["kept_paths"] = analysis["kept_paths"]
    reduction["discarded_paths"] = analysis["discarded_paths"]
    reduction["final_line_specs"] = analysis["final_line_specs"]
    reduction["raw_counts"]["path_class_count"] = len(analysis["path_classes"])
    reduction["raw_counts"]["kept_final_path_count"] = len(analysis["final_line_specs"])
    reduction["raw_counts"]["discarded_duplicate_path_count"] = len(analysis["discarded_paths"])
    return reduction


def reduce_final_point_path_shell(kgeom: dict[str, Any]) -> dict[str, Any]:
    point_shell, capture_lookup = _point_coordinate_alias_records(kgeom)
    candidate_segments = _enumerate_candidate_segments(kgeom, point_shell)
    reduction = {
        "reduction_kind": "automatic_reduced_final_point_path_shell_candidates_v2",
        "raw_counts": {
            "grouped_point_count": len(kgeom["grouped"]["points"]),
            "grouped_line_count": len(kgeom["grouped"]["lines"]),
            "grouped_plane_count": len(kgeom["grouped"]["planes"]),
            "synthetic_boundary_point_count": len(kgeom.get("synthetic_boundary_points", [])),
            "point_capture_alias_count": len(kgeom.get("point_instance_entries", [])),
            "candidate_path_count": len(candidate_segments),
            "path_class_count": None,
            "kept_final_path_count": 0,
            "discarded_duplicate_path_count": 0,
        },
        "point_shell": point_shell,
        "listed_source_line_ids": [line["id"] for line in kgeom["grouped"]["lines"]],
        "final_point_ids": [],
        "candidate_paths": candidate_segments,
        "candidate_line_specs": [_segment_to_line_spec(segment) for segment in candidate_segments],
        "candidate_path_records": [],
        "path_classes": [],
        "kept_paths": [],
        "discarded_paths": [],
        "final_line_specs": [],
        "capture_lookup_size": len(capture_lookup),
    }
    return reduction


def _candidate_record_unknown_ordering(
    reduction: dict[str, Any],
) -> list[str]:
    candidate_records = list(reduction.get("candidate_path_records", []))
    if not candidate_records:
        return []
    ordering = list(candidate_records[0]["global_unknown_ordering"])
    for record in candidate_records[1:]:
        if list(record["global_unknown_ordering"]) != ordering:
            raise ValueError("candidate path records disagree on global unknown ordering")
    return ordering


def build_publication_point_shell(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    point_shell = [
        {
            "point_id": point["point_id"],
            "label": point.get("label"),
            "representative_coordinates": list(point["representative_coordinates"]),
            "aliases": list(point.get("aliases", [])),
        }
        for point in reduction.get("point_shell", [])
    ]
    unknown_ordering = _candidate_record_unknown_ordering(reduction)
    point_unknown_ordering = _point_unknown_ordering(unknown_ordering)
    publication_point_ids = [point["point_id"] for point in point_shell]
    return {
        "object_kind": "publication_point_shell",
        "point_ids": publication_point_ids,
        "points": point_shell,
        "unknown_ordering": unknown_ordering,
        "point_unknown_ordering": {
            point_id: list(point_unknown_ordering.get(point_id, []))
            for point_id in publication_point_ids
        },
        "unknown_count": len(unknown_ordering),
    }


def _canonical_line_restriction_key(
    record: dict[str, Any],
) -> tuple[Any, ...]:
    basis_ids = _record_basis_ids(record)
    basis_count = len(basis_ids)
    endpoint_rows: list[tuple[str, list[tuple[int, int, tuple[int, ...]]]]] = []
    for endpoint in record["endpoint_decomposition_signature"]:
        rows: list[tuple[int, int, tuple[int, ...]]] = []
        for rep in endpoint["reps"]:
            vector = tuple(
                int(rep["decomposition_on_line_basis"].get(basis_id, 0))
                for basis_id in basis_ids
            )
            rows.append((int(rep["rep_degree"]), int(rep["torsion"]), vector))
        endpoint_rows.append((endpoint["endpoint_id"], rows))

    best_key = None
    best_payload = None
    for permutation in permutations(range(basis_count)):
        endpoint_payload = []
        endpoint_key = []
        for endpoint_id, rows in endpoint_rows:
            transformed_rows = sorted(
                (
                    degree,
                    torsion,
                    tuple(vector[index] for index in permutation),
                )
                for degree, torsion, vector in rows
            )
            endpoint_payload.append(
                {
                    "endpoint_id": endpoint_id,
                    "rep_rows": [
                        {
                            "rep_degree": int(degree),
                            "torsion": int(torsion),
                            "line_basis_vector": list(vector),
                        }
                        for degree, torsion, vector in transformed_rows
                    ],
                }
            )
            endpoint_key.append((endpoint_id, tuple(transformed_rows)))
        candidate_key = (
            tuple(record["endpoint_pair"]),
            _line_group_signature_key(record["line_group_signature"]),
            tuple(endpoint_key),
        )
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_payload = endpoint_payload
    if best_key is None or best_payload is None:
        raise ValueError("failed to canonicalize line restriction signature")
    return best_key + (tuple(tuple(item["rep_rows"][row_index]["line_basis_vector"] for row_index in range(len(item["rep_rows"]))) for item in best_payload),)


def canonicalize_line_restriction_signature(
    record: dict[str, Any],
) -> dict[str, Any]:
    basis_ids = _record_basis_ids(record)
    basis_count = len(basis_ids)
    endpoint_rows: list[tuple[str, list[tuple[int, int, tuple[int, ...]]]]] = []
    for endpoint in record["endpoint_decomposition_signature"]:
        rows: list[tuple[int, int, tuple[int, ...]]] = []
        for rep in endpoint["reps"]:
            vector = tuple(
                int(rep["decomposition_on_line_basis"].get(basis_id, 0))
                for basis_id in basis_ids
            )
            rows.append((int(rep["rep_degree"]), int(rep["torsion"]), vector))
        endpoint_rows.append((endpoint["endpoint_id"], rows))

    best_key = None
    best_payload = None
    for permutation in permutations(range(basis_count)):
        endpoint_payload = []
        endpoint_key = []
        for endpoint_id, rows in endpoint_rows:
            transformed_rows = sorted(
                (
                    degree,
                    torsion,
                    tuple(vector[index] for index in permutation),
                )
                for degree, torsion, vector in rows
            )
            endpoint_payload.append(
                {
                    "endpoint_id": endpoint_id,
                    "rep_rows": [
                        {
                            "rep_degree": int(degree),
                            "torsion": int(torsion),
                            "line_basis_vector": list(vector),
                        }
                        for degree, torsion, vector in transformed_rows
                    ],
                }
            )
            endpoint_key.append((endpoint_id, tuple(transformed_rows)))
        candidate_key = (
            tuple(record["endpoint_pair"]),
            _line_group_signature_key(record["line_group_signature"]),
            tuple(endpoint_key),
        )
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_payload = endpoint_payload
    if best_key is None or best_payload is None:
        raise ValueError("failed to canonicalize line restriction signature")
    return {
        "endpoint_pair": list(record["endpoint_pair"]),
        "line_group_signature": record["line_group_signature"],
        "basis_count": basis_count,
        "basis_permutation_count": factorial(basis_count),
        "canonical_endpoint_signatures": best_payload,
        "canonical_signature_key": repr(best_key),
    }


def _publication_source_row_records(record: dict[str, Any]) -> list[dict[str, Any]]:
    if record.get("line_monodromy_compression_available"):
        rows = list(record.get("monodromy_compressed_global_matrix_row_records", []))
        if rows:
            return rows
    return list(record["global_matrix_row_records"])


def _rank_gaining_row_records(
    row_records: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[list[int]]]:
    selected: list[dict[str, Any]] = []
    running_rows: list[list[int]] = []
    running_rank = 0
    for row_record in row_records:
        row = [int(value) for value in row_record["matrix_row"]]
        candidate_rank = _row_rank(running_rows + [row])
        if candidate_rank > running_rank:
            selected.append(
                {
                    **row_record,
                    "matrix_row": list(row),
                    "rank_gain": candidate_rank - running_rank,
                }
            )
            running_rows.append(list(row))
            running_rank = candidate_rank
    return selected, running_rows


def _publication_group_sort_key(
    payload: dict[str, Any],
    point_order: dict[str, int],
) -> tuple[Any, ...]:
    endpoint_pair = payload["endpoint_pair"]
    left_id, right_id = endpoint_pair
    return (
        min(point_order[left_id], point_order[right_id]),
        max(point_order[left_id], point_order[right_id]),
        tuple(payload["member_source_line_ids"]),
        tuple(payload["member_internal_path_class_ids"]),
    )


def build_publication_path_classes(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    point_order = {
        point["point_id"]: index
        for index, point in enumerate(reduction.get("point_shell", []))
    }
    unknown_ordering = _candidate_record_unknown_ordering(reduction)
    point_unknown_ordering = _point_unknown_ordering(unknown_ordering)
    point_capture_permutations = _build_publication_point_capture_permutations(
        reduction,
        point_unknown_ordering,
    )
    grouped_by_family: dict[tuple[Any, ...], list[tuple[dict[str, Any], list[dict[str, Any]]]]] = {}
    for payload in reduction.get("path_classes", []):
        representative = payload["candidate_records"][0]
        publication_signature = canonicalize_line_restriction_signature(representative)
        representative_rows = _transform_publication_row_records_to_point_family_basis(
            representative,
            _publication_source_row_records(representative),
            point_unknown_ordering,
            point_capture_permutations,
        )
        publication_key = (
            tuple(payload["endpoint_pair"]),
            _line_group_signature_key(payload["line_group_signature"]),
            publication_signature["canonical_signature_key"],
        )
        grouped_by_family.setdefault(publication_key, []).append((payload, representative_rows))

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for publication_key, entries in grouped_by_family.items():
        source_line_ids = [
            entry[0]["representative_source_line_id"]
            for entry in entries
        ]
        source_kinds = {
            str(entry[0]["representative_source_kind"])
            for entry in entries
        }
        split_by_rowspace = (
            source_kinds == {"listed_line"}
            and len(set(source_line_ids)) == len(source_line_ids)
        )
        if not split_by_rowspace:
            grouped[publication_key] = [entry[0] for entry in entries]
            continue
        for payload, representative_rows in entries:
            rowspace_key = publication_key + (
                _rref_signature([list(row_record["matrix_row"]) for row_record in representative_rows]),
            )
            grouped.setdefault(rowspace_key, []).append(payload)

    publication_classes: list[dict[str, Any]] = []
    for class_index, key in enumerate(
        sorted(grouped, key=lambda item: _candidate_sort_key(grouped[item][0]["candidate_records"][0], point_order)),
        start=1,
    ):
        members = sorted(
            grouped[key],
            key=lambda payload: _candidate_sort_key(payload["candidate_records"][0], point_order),
        )
        representative = members[0]["candidate_records"][0]
        canonical_signature = canonicalize_line_restriction_signature(representative)
        combined_row_records: list[dict[str, Any]] = []
        combined_rows: list[list[int]] = []
        member_row_record_sets: list[list[dict[str, Any]]] = []
        member_row_sets: list[list[list[int]]] = []
        for member in members:
            member_record = member["candidate_records"][0]
            transformed_member_row_records = _transform_publication_row_records_to_point_family_basis(
                member_record,
                _publication_source_row_records(member_record),
                point_unknown_ordering,
                point_capture_permutations,
            )
            member_row_record_sets.append(transformed_member_row_records)
            member_row_sets.append(
                [list(row_record["matrix_row"]) for row_record in transformed_member_row_records]
            )
            for row_record in transformed_member_row_records:
                payload = {
                    **row_record,
                    "matrix_row": list(row_record["matrix_row"]),
                    "member_internal_path_class_id": member["path_class_id"],
                    "member_candidate_id": member["representative_candidate_id"],
                    "member_source_line_id": member["representative_source_line_id"],
                    "member_source_kind": member["representative_source_kind"],
                    "member_source_id": member["representative_source_id"],
                    "member_branch_index": int(member["representative_branch_index"]),
                }
                combined_row_records.append(payload)
                combined_rows.append(list(row_record["matrix_row"]))
        # Publication-level path classes should be represented by a single
        # canonical listed family, not by the union of every star-equivalent
        # raw member that happens to survive internal reduction.  The full
        # member-union row space is still kept for diagnostics, but the
        # published C-matrix is built from the canonical representative only.
        representative_row_records = [
            {
                **row_record,
                "matrix_row": list(row_record["matrix_row"]),
                "member_internal_path_class_id": members[0]["path_class_id"],
                "member_candidate_id": members[0]["representative_candidate_id"],
                "member_source_line_id": members[0]["representative_source_line_id"],
                "member_source_kind": members[0]["representative_source_kind"],
                "member_source_id": members[0]["representative_source_id"],
                "member_branch_index": int(members[0]["representative_branch_index"]),
            }
            for row_record in member_row_record_sets[0]
        ]
        representative_rows = [list(row_record["matrix_row"]) for row_record in representative_row_records]
        common_rows = _row_space_intersection_basis(member_row_sets)
        if not common_rows:
            common_rows = representative_rows
        representative_rank = _row_rank(representative_rows)
        common_rank = _row_rank(common_rows)
        aggregate_rank = _row_rank(combined_rows)
        endpoint_capture_variation = False
        for endpoint_position, point_id in enumerate(members[0]["endpoint_pair"]):
            point_entry = next(
                (item for item in reduction.get("point_shell", []) if item["point_id"] == point_id),
                None,
            )
            if point_entry is None or len(point_entry.get("aliases", [])) <= 1:
                continue
            capture_ids = {
                member["candidate_records"][0]["endpoint_capture_ids"][endpoint_position]
                for member in members
                if endpoint_position < len(member["candidate_records"][0].get("endpoint_capture_ids", []))
            }
            if len(capture_ids) > 1:
                endpoint_capture_variation = True
                break
        member_row_space_signatures = {
            _rref_signature(rows)
            for rows in member_row_sets
        }
        member_row_space_reports = [
            {
                "member_internal_path_class_id": members[index]["path_class_id"],
                "member_source_line_id": members[index]["representative_source_line_id"],
                "member_source_kind": members[index]["representative_source_kind"],
                "member_candidate_id": members[index]["representative_candidate_id"],
                "row_rank": _row_rank(rows),
                "row_space_signature": [list(row) for row in _rref_signature(rows)],
            }
            for index, rows in enumerate(member_row_sets)
        ]
        same_source_line_family = (
            len({member["representative_source_line_id"] for member in members}) == 1
        )
        alias_only_row_space_variation = (
            aggregate_rank == representative_rank + 1
            and common_rank + 1 == representative_rank
        )
        use_common_row_language = (
            endpoint_capture_variation
            and len(member_row_space_signatures) > 1
            and same_source_line_family
            and alias_only_row_space_variation
        )
        common_row_records = [
            {
                "row_index_within_candidate_block": local_row_index,
                "basis_id": f"PUBCLASS{class_index:02d}_COMMON_{local_row_index + 1:02d}",
                "row_kind": "publication_common_path_basis",
                "matrix_row": list(row),
                "member_internal_path_class_id": None,
                "member_candidate_id": None,
                "member_source_line_id": None,
                "member_source_kind": "publication_common_intersection",
                "member_source_id": None,
                "member_branch_index": 0,
            }
            for local_row_index, row in enumerate(common_rows)
        ]
        selected_basis_rows = common_rows if use_common_row_language else representative_rows
        selected_basis_row_records = (
            common_row_records if use_common_row_language else representative_row_records
        )
        selected_rows_contained_by_member = [
            _row_rank(rows + selected_basis_rows) == _row_rank(rows)
            for rows in member_row_sets
        ]
        selected_rows_contained_in_all_members = all(selected_rows_contained_by_member)
        representative_rows_equal_all_members = all(
            _rref_signature(rows) == _rref_signature(representative_rows)
            for rows in member_row_sets
        )
        publication_classes.append(
            {
                "publication_path_class_id": f"PUBCLASS{class_index:02d}",
                "endpoint_pair": list(members[0]["endpoint_pair"]),
                "line_group_signature": members[0]["line_group_signature"],
                "canonicalized_restriction_signature": canonical_signature,
                "member_internal_path_class_ids": [member["path_class_id"] for member in members],
                "member_candidate_ids": [member["representative_candidate_id"] for member in members],
                "member_source_line_ids": [member["representative_source_line_id"] for member in members],
                "member_source_kinds": [member["representative_source_kind"] for member in members],
                "member_source_ids": [member["representative_source_id"] for member in members],
                "aggregate_row_count": len(combined_rows),
                "aggregate_row_rank": aggregate_rank,
                "aggregate_row_space_signature": _row_space_signature(combined_rows),
                "representative_basis_row_count": len(representative_rows),
                "representative_basis_row_rank": representative_rank,
                "representative_basis_row_records": representative_row_records,
                "representative_basis_rows": representative_rows,
                "selected_basis_row_count": len(selected_basis_rows),
                "selected_basis_row_rank": _row_rank(selected_basis_rows),
                "selected_basis_row_records": selected_basis_row_records,
                "selected_basis_rows": selected_basis_rows,
                "used_common_publication_row_language": use_common_row_language,
                "endpoint_capture_variation": endpoint_capture_variation,
                "member_row_space_signature_count": len(member_row_space_signatures),
                "same_source_line_family": same_source_line_family,
                "common_basis_row_rank": common_rank,
                "alias_only_row_space_variation": alias_only_row_space_variation,
                "member_row_space_reports": member_row_space_reports,
                "selected_rows_contained_by_member": selected_rows_contained_by_member,
                "selected_rows_contained_in_all_members": selected_rows_contained_in_all_members,
                "representative_rows_equal_all_members": representative_rows_equal_all_members,
                "publication_point_basis_permutations_used": {
                    point_id: {
                        capture_id: {
                            "default": [int(index) for index in payload.get("default", ())]
                            if any(
                                index != local_index
                                for local_index, index in enumerate(payload.get("default", ()))
                            )
                            else None,
                            "by_context": {
                                repr(context_key): [int(index) for index in permutation]
                                for context_key, permutation in payload.get("by_context", {}).items()
                                if any(index != local_index for local_index, index in enumerate(permutation))
                            },
                        }
                        for capture_id, payload in capture_map.items()
                        if (
                            any(
                                index != local_index
                                for local_index, index in enumerate(payload.get("default", ()))
                            )
                            or any(
                                any(index != local_index for local_index, index in enumerate(permutation))
                                for permutation in payload.get("by_context", {}).values()
                            )
                        )
                    }
                    for point_id, capture_map in point_capture_permutations.items()
                },
                "publication_equivalence_reason": (
                    "Raw strong path classes were grouped because they share the same publication-level "
                    "endpoint pair, line little-group type, and canonicalized endpoint restriction signature "
                    "after basis-label permutations and endpoint-side relabel canonicalization. "
                    "All grouped members are first rewritten into a common publication point-family basis. "
                    "When the grouped members still disagree because they use genuinely different alias-capture "
                    "frames for the same published point family, the published path class keeps only the common "
                    "row language across those frames; otherwise it uses the canonical representative row span."
                ),
                "selected_as_publication": False,
                "selection_reason": None,
            }
        )

    by_pair: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for payload in publication_classes:
        by_pair.setdefault(tuple(payload["endpoint_pair"]), []).append(payload)

    selected_classes: list[dict[str, Any]] = []
    discarded_classes: list[dict[str, Any]] = []
    for pair_key in sorted(by_pair):
        running_rows: list[list[int]] = []
        pair_classes = sorted(
            by_pair[pair_key],
            key=lambda payload: _publication_group_sort_key(payload, point_order),
        )
        for payload in pair_classes:
            before_rank = _row_rank(running_rows)
            after_rank = _row_rank(running_rows + payload["selected_basis_rows"])
            if after_rank > before_rank:
                payload["selected_as_publication"] = True
                payload["selection_reason"] = (
                    "Retained as the publication-level representative for this endpoint pair because "
                    "its aggregated canonical row language adds independent compatibility rows "
                    f"within the pair (rank {before_rank} -> {after_rank})."
                )
                selected_classes.append(payload)
                running_rows.extend(payload["selected_basis_rows"])
            else:
                payload["selection_reason"] = (
                    "Discarded at the publication level because its aggregated canonical row language "
                    "is already contained in an earlier selected publication path class for the same endpoint pair."
                )
                discarded_classes.append(payload)

    selected_classes.sort(key=lambda payload: _publication_group_sort_key(payload, point_order))
    publication_paths: list[dict[str, Any]] = []
    for path_index, payload in enumerate(selected_classes, start=1):
        publication_paths.append(
            {
                "publication_path_id": f"PPATH{path_index:02d}",
                "publication_path_class_id": payload["publication_path_class_id"],
                "endpoint_pair": list(payload["endpoint_pair"]),
                "line_group_signature": payload["line_group_signature"],
                "member_internal_path_class_ids": list(payload["member_internal_path_class_ids"]),
                "member_source_line_ids": list(payload["member_source_line_ids"]),
                "member_candidate_ids": list(payload["member_candidate_ids"]),
                "canonicalized_restriction_signature": payload["canonicalized_restriction_signature"],
                "selected_basis_row_records": list(payload["selected_basis_row_records"]),
                "selected_basis_rows": list(payload["selected_basis_rows"]),
                "selection_reason": payload["selection_reason"],
            }
        )

    return {
        "publication_path_class_count": len(publication_classes),
        "selected_publication_path_count": len(publication_paths),
        "publication_path_classes": publication_classes,
        "selected_publication_path_classes": selected_classes,
        "discarded_publication_path_classes": discarded_classes,
        "publication_paths": publication_paths,
    }


def build_publication_shell_candidate(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    publication_point_shell = build_publication_point_shell(reduction)
    publication_path_payload = build_publication_path_classes(reduction)
    return {
        "object_kind": "publication_level_point_path_shell_v1",
        "publication_point_shell": publication_point_shell,
        "publication_point_ids": list(publication_point_shell["point_ids"]),
        "publication_unknown_ordering": list(publication_point_shell["unknown_ordering"]),
        "publication_unknown_count": int(publication_point_shell["unknown_count"]),
        **publication_path_payload,
        "publication_actual_path_pairs": [
            list(path["endpoint_pair"])
            for path in publication_path_payload["publication_paths"]
        ],
    }


def build_publication_C_matrix(
    publication_shell: dict[str, Any],
) -> dict[str, Any]:
    unknown_ordering = list(publication_shell["publication_unknown_ordering"])
    publication_blocks: list[dict[str, Any]] = []
    global_matrix: list[list[int]] = []
    row_provenance: list[dict[str, Any]] = []
    for path in publication_shell["publication_paths"]:
        equations = []
        for local_row_index, row_record in enumerate(path["selected_basis_row_records"]):
            row = [int(value) for value in row_record["matrix_row"]]
            terms = [
                {"unknown": unknown_ordering[column_index], "coeff": int(value)}
                for column_index, value in enumerate(row)
                if int(value) != 0
            ]
            equation = {
                "basis_id": row_record["basis_id"],
                "row_kind": row_record.get("row_kind", "publication_path_basis"),
                "terms": terms,
                "row_index_within_publication_path": local_row_index,
                "member_internal_path_class_id": row_record["member_internal_path_class_id"],
                "member_source_line_id": row_record["member_source_line_id"],
                "member_candidate_id": row_record["member_candidate_id"],
            }
            equations.append(equation)
            row_provenance.append(
                {
                    "publication_path_id": path["publication_path_id"],
                    "publication_path_class_id": path["publication_path_class_id"],
                    "endpoint_pair": list(path["endpoint_pair"]),
                    "member_internal_path_class_id": row_record["member_internal_path_class_id"],
                    "member_source_line_id": row_record["member_source_line_id"],
                    "member_candidate_id": row_record["member_candidate_id"],
                    "basis_id": row_record["basis_id"],
                    "row_kind": row_record.get("row_kind", "publication_path_basis"),
                    "matrix_row": list(row),
                }
            )
            global_matrix.append(list(row))
        publication_blocks.append(
            {
                "line_id": path["publication_path_id"],
                "path_id": path["publication_path_id"],
                "publication_path_class_id": path["publication_path_class_id"],
                "endpoint_pair": list(path["endpoint_pair"]),
                "member_internal_path_class_ids": list(path["member_internal_path_class_ids"]),
                "member_source_line_ids": list(path["member_source_line_ids"]),
                "equations": equations,
            }
        )
    return {
        "object_role": "publication_level_C_matrix",
        "publication_status": "published_final_object",
        "global_unknown_ordering": unknown_ordering,
        "global_matrix": global_matrix,
        "line_blocks": publication_blocks,
        "publication_path_blocks": publication_blocks,
        "row_provenance": row_provenance,
    }


def compare_publication_shell_to_bilbao_expected(
    publication_shell: dict[str, Any],
    *,
    expected_point_ids: Sequence[str],
    expected_endpoint_pairs: Sequence[Sequence[str]],
) -> dict[str, Any]:
    actual_point_ids = list(publication_shell["publication_point_ids"])
    actual_pairs = sorted(tuple(sorted(pair)) for pair in publication_shell["publication_actual_path_pairs"])
    expected_pairs_sorted = sorted(tuple(sorted(pair)) for pair in expected_endpoint_pairs)
    bilbao_equivalent_publication_pass = (
        actual_point_ids == list(expected_point_ids)
        and len(actual_pairs) == len(expected_pairs_sorted)
        and actual_pairs == expected_pairs_sorted
    )
    return {
        "actual_point_ids": actual_point_ids,
        "expected_point_ids": list(expected_point_ids),
        "actual_path_pairs": [list(pair) for pair in actual_pairs],
        "expected_path_pairs": [list(pair) for pair in expected_pairs_sorted],
        "point_ids_match": actual_point_ids == list(expected_point_ids),
        "point_count_match": len(actual_point_ids) == len(expected_point_ids),
        "path_pair_set_match": actual_pairs == expected_pairs_sorted,
        "path_count_match": len(actual_pairs) == len(expected_pairs_sorted),
        "bilbao_equivalent_publication_pass": bilbao_equivalent_publication_pass,
    }


def build_reduction_report_markdown(reduction: dict[str, Any]) -> str:
    lines = [
        "# Internal Honest Shell Reduction Report",
        "",
        "## Counts",
        "",
        f"- Raw grouped points / lines / planes: `{reduction['raw_counts']['grouped_point_count']}` / `{reduction['raw_counts']['grouped_line_count']}` / `{reduction['raw_counts']['grouped_plane_count']}`.",
        f"- Candidate paths enumerated: `{reduction['raw_counts']['candidate_path_count']}`.",
        f"- Candidate path classes after strong signature collapse: `{reduction['raw_counts']['path_class_count']}`.",
        f"- Canonical endpoint-pair skeleton row rank: `{reduction['endpoint_pair_skeleton_row_rank']}`.",
        f"- Full candidate row-language target rank: `{reduction['target_row_rank']}`.",
        f"- Final kept paths: `{reduction['raw_counts']['kept_final_path_count']}`.",
        f"- Discarded candidate rows / duplicates: `{reduction['raw_counts']['discarded_duplicate_path_count']}`.",
        f"- Selection augmentation path classes: `{reduction['selection_augmentation_path_class_ids']}`.",
        f"- Row-language full-span pass: `{reduction.get('row_language_full_span_pass')}`.",
        f"- Bilbao-equivalent final-object pass: `{reduction.get('bilbao_equivalent_final_object_pass')}`.",
        "",
        "## Internal Point Shell",
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
            "## Internal Honest Path Shell",
            "",
        ]
    )
    for segment in reduction["kept_paths"]:
        lines.append(
            "- "
            + f"`{segment['final_path_id']}`: `{segment['endpoint_ids'][0]} -> {segment['endpoint_ids'][1]}` "
            + f"from `{segment['source_line_id']}` branch `{segment['coordinate_expressions']}` "
            + f"(class `{segment['path_class_id']}`, stage `{segment['selection_stage']}`, rank gain `{segment['rank_gain_within_final_order']}`); "
            + f"reason: {segment['selection_reason']}"
        )
    if reduction["discarded_paths"]:
        lines.extend(["", "## Discarded Candidates", ""])
        for segment in reduction["discarded_paths"]:
            lines.append(
                "- "
                + f"`{segment['candidate_id']}` from `{segment['source_line_id']}` for endpoint pair "
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
    actual_unique_pairs = sorted(set(actual_pairs))
    expected_pairs_sorted = sorted(tuple(sorted(pair)) for pair in expected_endpoint_pairs)
    bilbao_equivalent_final_object_pass = (
        actual_point_ids == list(expected_point_ids)
        and len(actual_point_ids) == len(expected_point_ids)
        and actual_pairs == expected_pairs_sorted
        and len(actual_pairs) == len(expected_endpoint_pairs)
    )
    return {
        "actual_point_ids": actual_point_ids,
        "expected_point_ids": list(expected_point_ids),
        "actual_path_pairs": [list(pair) for pair in actual_pairs],
        "actual_unique_path_pairs": [list(pair) for pair in actual_unique_pairs],
        "expected_path_pairs": [list(pair) for pair in expected_pairs_sorted],
        "point_ids_match": actual_point_ids == list(expected_point_ids),
        "point_count_match": len(actual_point_ids) == len(expected_point_ids),
        "path_pair_set_match": actual_pairs == expected_pairs_sorted,
        "unique_path_pair_set_match": actual_unique_pairs == expected_pairs_sorted,
        "path_count_match": len(actual_pairs) == len(expected_endpoint_pairs),
        "bilbao_equivalent_final_object_pass": bilbao_equivalent_final_object_pass,
    }


def build_publication_shell_reduction_report(
    reduction: dict[str, Any],
    publication_shell: dict[str, Any],
) -> dict[str, Any]:
    return {
        "internal_honest_shell_path_count": len(reduction.get("kept_paths", [])),
        "internal_honest_shell_path_pairs": [
            list(path["endpoint_pair"])
            for path in reduction.get("kept_paths", [])
        ],
        "publication_point_count": len(publication_shell["publication_point_ids"]),
        "publication_path_class_count": publication_shell["publication_path_class_count"],
        "publication_selected_path_count": publication_shell["selected_publication_path_count"],
        "publication_actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
        "publication_unknown_count": int(publication_shell["publication_unknown_count"]),
        "raw_line_count": int(reduction["raw_counts"]["grouped_line_count"]),
        "candidate_path_count": int(reduction["raw_counts"]["candidate_path_count"]),
        "publication_path_classes": [
            {
                "publication_path_class_id": payload["publication_path_class_id"],
                "endpoint_pair": list(payload["endpoint_pair"]),
                "selected_as_publication": bool(payload["selected_as_publication"]),
                "member_internal_path_class_ids": list(payload["member_internal_path_class_ids"]),
                "member_source_line_ids": list(payload["member_source_line_ids"]),
                "aggregate_row_rank": int(payload["aggregate_row_rank"]),
                "selected_basis_row_rank": int(payload["selected_basis_row_rank"]),
                "selection_reason": payload["selection_reason"],
            }
            for payload in publication_shell["publication_path_classes"]
        ],
    }


def build_publication_shell_reduction_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Publication Shell Reduction Report",
        "",
        f"- Internal honest shell path count: `{report['internal_honest_shell_path_count']}`.",
        f"- Publication point count: `{report['publication_point_count']}`.",
        f"- Publication path-class count: `{report['publication_path_class_count']}`.",
        f"- Publication selected path count: `{report['publication_selected_path_count']}`.",
        f"- Publication actual path pairs: `{report['publication_actual_path_pairs']}`.",
        f"- Publication unknown count: `{report['publication_unknown_count']}`.",
        "",
        "## Publication Path Classes",
        "",
    ]
    for payload in report["publication_path_classes"]:
        lines.append(
            "- "
            + f"`{payload['publication_path_class_id']}` pair `{payload['endpoint_pair']}` "
            + f"members `{payload['member_internal_path_class_ids']}` from raw lines "
            + f"`{payload['member_source_line_ids']}`; selected = `{payload['selected_as_publication']}`; "
            + f"aggregate rank `{payload['aggregate_row_rank']}`, selected-basis rank "
            + f"`{payload['selected_basis_row_rank']}`; reason: {payload['selection_reason']}"
        )
    return "\n".join(lines)


def build_publication_shell_invariance_audit(
    publication_shell: dict[str, Any],
) -> dict[str, Any]:
    class_reports: list[dict[str, Any]] = []
    unresolved_class_ids: list[str] = []
    multi_source_class_ids: list[str] = []
    alias_only_class_ids: list[str] = []
    invariant_class_ids: list[str] = []
    for payload in publication_shell["publication_path_classes"]:
        if payload["member_row_space_signature_count"] == 1:
            verdict = "member_row_space_invariant"
            invariant_class_ids.append(payload["publication_path_class_id"])
        elif (
            payload["used_common_publication_row_language"]
            and payload["selected_rows_contained_in_all_members"]
        ):
            verdict = "alias_only_common_invariant"
            alias_only_class_ids.append(payload["publication_path_class_id"])
        elif not payload["same_source_line_family"]:
            verdict = "canonical_multi_source_publication_family"
            multi_source_class_ids.append(payload["publication_path_class_id"])
        else:
            verdict = "unresolved_publication_row_space_variation"
            unresolved_class_ids.append(payload["publication_path_class_id"])
        class_reports.append(
            {
                "publication_path_class_id": payload["publication_path_class_id"],
                "endpoint_pair": list(payload["endpoint_pair"]),
                "selected_as_publication": bool(payload["selected_as_publication"]),
                "member_internal_path_class_ids": list(payload["member_internal_path_class_ids"]),
                "member_source_line_ids": list(payload["member_source_line_ids"]),
                "used_common_publication_row_language": bool(payload["used_common_publication_row_language"]),
                "endpoint_capture_variation": bool(payload["endpoint_capture_variation"]),
                "member_row_space_signature_count": int(payload["member_row_space_signature_count"]),
                "same_source_line_family": bool(payload["same_source_line_family"]),
                "alias_only_row_space_variation": bool(payload["alias_only_row_space_variation"]),
                "representative_basis_row_rank": int(payload["representative_basis_row_rank"]),
                "common_basis_row_rank": int(payload["common_basis_row_rank"]),
                "aggregate_row_rank": int(payload["aggregate_row_rank"]),
                "selected_basis_row_rank": int(payload["selected_basis_row_rank"]),
                "selected_rows_contained_in_all_members": bool(payload["selected_rows_contained_in_all_members"]),
                "representative_rows_equal_all_members": bool(payload["representative_rows_equal_all_members"]),
                "member_row_space_reports": list(payload["member_row_space_reports"]),
                "verdict": verdict,
            }
        )
    return {
        "publication_path_class_count": len(class_reports),
        "selected_publication_path_count": len(publication_shell["publication_paths"]),
        "invariant_class_ids": invariant_class_ids,
        "alias_only_common_class_ids": alias_only_class_ids,
        "canonical_multi_source_class_ids": multi_source_class_ids,
        "unresolved_class_ids": unresolved_class_ids,
        "all_selected_classes_internally_resolved": len(unresolved_class_ids) == 0,
        "class_reports": class_reports,
    }


def build_publication_shell_invariance_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Publication Shell Invariance Audit",
        "",
        f"- Publication path-class count: `{audit['publication_path_class_count']}`.",
        f"- Selected publication path count: `{audit['selected_publication_path_count']}`.",
        f"- Invariant classes: `{audit['invariant_class_ids']}`.",
        f"- Alias-only common classes: `{audit['alias_only_common_class_ids']}`.",
        f"- Canonical multi-source classes: `{audit['canonical_multi_source_class_ids']}`.",
        f"- Unresolved classes: `{audit['unresolved_class_ids']}`.",
        f"- All selected classes internally resolved: `{audit['all_selected_classes_internally_resolved']}`.",
        "",
        "## Class Verdicts",
        "",
    ]
    for payload in audit["class_reports"]:
        lines.append(
            "- "
            + f"`{payload['publication_path_class_id']}` pair `{payload['endpoint_pair']}` "
            + f"verdict `{payload['verdict']}`; selected=`{payload['selected_as_publication']}`; "
            + f"source lines `{payload['member_source_line_ids']}`; "
            + f"member-row signatures `{payload['member_row_space_signature_count']}`; "
            + f"representative/common/aggregate ranks `{payload['representative_basis_row_rank']}`/"
            + f"`{payload['common_basis_row_rank']}`/`{payload['aggregate_row_rank']}`."
        )
    return "\n".join(lines)


def build_publication_shell_vs_bilbao_markdown(check: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Publication Shell vs Bilbao Check",
            "",
            f"- Point count match: `{check['point_count_match']}`.",
            f"- Point id order match: `{check['point_ids_match']}`.",
            f"- Path count match: `{check['path_count_match']}`.",
            f"- Path pair set match: `{check['path_pair_set_match']}`.",
            f"- Bilbao-equivalent publication pass: `{check['bilbao_equivalent_publication_pass']}`.",
            "",
            f"- Actual publication point ids: `{check['actual_point_ids']}`.",
            f"- Actual publication path pairs: `{check['actual_path_pairs']}`.",
            f"- Expected point ids: `{check['expected_point_ids']}`.",
            f"- Expected path pairs: `{check['expected_path_pairs']}`.",
        ]
    )


def build_internal_vs_publication_object_report(
    reduction: dict[str, Any],
    publication_shell: dict[str, Any],
    internal_bs_analysis: dict[str, Any],
    publication_bs_analysis: dict[str, Any],
) -> dict[str, Any]:
    return {
        "internal_honest_shell_path_count": len(reduction.get("kept_paths", [])),
        "internal_honest_shell_rank": int(internal_bs_analysis["rank"]),
        "internal_honest_shell_matrix_shape": list(internal_bs_analysis["matrix_shape"]),
        "internal_honest_shell_actual_path_pairs": [
            list(path["endpoint_pair"])
            for path in reduction.get("kept_paths", [])
        ],
        "publication_shell_path_count": len(publication_shell["publication_paths"]),
        "publication_shell_rank": int(publication_bs_analysis["rank"]),
        "publication_shell_matrix_shape": list(publication_bs_analysis["matrix_shape"]),
        "publication_shell_actual_path_pairs": list(publication_shell["publication_actual_path_pairs"]),
        "objects_explicitly_separated": True,
        "internal_usage": [
            "diagnostic full-span bookkeeping",
            "raw path-class obstruction analysis",
            "phase-aware translation retirement diagnostics",
            "AI obstruction debugging against the internal shell",
        ],
        "publication_usage": [
            "published final C matrix",
            "published BS kernel analysis",
            "Bilbao-level point/path sanity check",
            "published-shell AI compatibility testing",
        ],
        "separation_reason": (
            "The internal honest shell is a fixed-label full-span diagnostic object; the publication shell "
            "is a quotient over publication path classes built directly from raw line data and is the only "
            "object that should be compared to Bilbao-facing semantics."
        ),
    }


def build_internal_vs_publication_object_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Internal vs Publication Object Report",
        "",
        f"- Internal honest shell path count / rank: `{report['internal_honest_shell_path_count']}` / `{report['internal_honest_shell_rank']}`.",
        f"- Publication shell path count / rank: `{report['publication_shell_path_count']}` / `{report['publication_shell_rank']}`.",
        f"- Objects explicitly separated: `{report['objects_explicitly_separated']}`.",
        f"- Separation reason: {report['separation_reason']}",
        "",
        "## Internal Usage",
        "",
    ]
    for item in report["internal_usage"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Publication Usage", ""])
    for item in report["publication_usage"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def build_expected_check_markdown(check: dict[str, Any]) -> str:
    unique_path_pair_set_match = check.get("unique_path_pair_set_match", check["path_pair_set_match"])
    actual_unique_path_pairs = check.get("actual_unique_path_pairs", check["actual_path_pairs"])
    lines = [
        "# Publication Object vs Bilbao-Equivalent Sanity Check",
        "",
        f"- Point count match: `{check['point_count_match']}`.",
        f"- Point id order match: `{check['point_ids_match']}`.",
        f"- Path count match: `{check['path_count_match']}`.",
        f"- Path pair set match: `{check['path_pair_set_match']}`.",
        f"- Unique path pair set match: `{unique_path_pair_set_match}`.",
        f"- Bilbao-equivalent publication pass: `{check.get('bilbao_equivalent_publication_pass', check.get('bilbao_equivalent_final_object_pass'))}`.",
        "",
        "## Actual",
        "",
        f"- Publication point ids: `{check['actual_point_ids']}`.",
        f"- Publication path endpoint pairs: `{check['actual_path_pairs']}`.",
        f"- Publication unique endpoint-pair set: `{actual_unique_path_pairs}`.",
        "",
        "## Expected",
        "",
        f"- Expected point ids: `{check['expected_point_ids']}`.",
        f"- Expected path endpoint pairs: `{check['expected_path_pairs']}`.",
    ]
    return "\n".join(lines)


def build_final_path_signature_report(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    return {
        "final_point_count": len(reduction["final_point_ids"]),
        "final_point_ids": list(reduction["final_point_ids"]),
        "final_path_count": len(reduction["kept_paths"]),
        "final_paths": [
            {
                "final_path_id": segment["final_path_id"],
                "path_class_id": segment["path_class_id"],
                "candidate_id": segment["candidate_id"],
                "endpoint_pair": list(segment["endpoint_pair"]),
                "endpoint_ids": list(segment["endpoint_ids"]),
                "source_line_id": segment["source_line_id"],
                "source_kind": segment["source_kind"],
                "source_id": segment["source_id"],
                "branch_index": int(segment["branch_index"]),
                "coordinate_expressions": list(segment["coordinate_expressions"]),
                "parameter_interval": list(segment["parameter_interval"]),
                "line_group_signature": segment["line_group_signature"],
                "endpoint_decomposition_signature": segment["endpoint_decomposition_signature"],
                "phase_aware_profile_used": segment["phase_aware_profile_used"],
                "phase_aware_refinement_signature": segment["phase_aware_refinement_signature"],
                "local_row_space_signature": segment["local_row_space_signature"],
                "global_row_space_signature": segment["global_row_space_signature"],
                "selection_stage": segment["selection_stage"],
                "selection_reason": segment["selection_reason"],
                "rank_gain_within_final_order": int(segment["rank_gain_within_final_order"]),
            }
            for segment in reduction["kept_paths"]
        ],
    }


def build_final_path_signature_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Path Signature Report",
        "",
        f"- Final point count: `{report['final_point_count']}`.",
        f"- Final path count: `{report['final_path_count']}`.",
        "",
    ]
    for path in report["final_paths"]:
        lines.extend(
            [
                f"## {path['final_path_id']}",
                "",
                f"- Path class: `{path['path_class_id']}`.",
                f"- Source: `{path['source_line_id']}` / `{path['source_kind']}` / `{path['source_id']}` branch `{path['branch_index']}`.",
                f"- Endpoint pair: `{path['endpoint_pair']}`.",
                f"- Line little-group signature: `{path['line_group_signature']}`.",
                f"- Phase-aware profile: `{path['phase_aware_profile_used']}`.",
                f"- Selection stage: `{path['selection_stage']}`.",
                f"- Local row-space signature: rank `{path['local_row_space_signature']['row_rank']}` over `{path['local_row_space_signature']['row_count']}` rows; Smith diagonal `{path['local_row_space_signature']['smith_diagonal']}`.",
                f"- Global row-space signature: rank `{path['global_row_space_signature']['row_rank']}` over `{path['global_row_space_signature']['row_count']}` rows; Smith diagonal `{path['global_row_space_signature']['smith_diagonal']}`.",
                f"- Rank gain inside final order: `{path['rank_gain_within_final_order']}`.",
                f"- Selection reason: {path['selection_reason']}",
                "",
            ]
        )
    return "\n".join(lines)


def build_final_path_candidate_equivalence_report(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    class_payloads = reduction.get("path_classes", [])
    selected_path_class_ids = {
        segment["path_class_id"]
        for segment in reduction["kept_paths"]
    }
    for class_payload in class_payloads:
        pair_key = tuple(class_payload["endpoint_pair"])
        entry = by_pair.setdefault(
            pair_key,
            {
                "endpoint_pair": list(pair_key),
                "candidate_count": 0,
                "path_class_count": 0,
                "selected_path_class_ids": [],
                "candidate_path_classes": [],
            },
        )
        entry["candidate_count"] += len(class_payload["candidate_ids"])
        entry["path_class_count"] += 1
        if class_payload["path_class_id"] in selected_path_class_ids:
            entry["selected_path_class_ids"].append(class_payload["path_class_id"])
        entry["candidate_path_classes"].append(
            {
                "path_class_id": class_payload["path_class_id"],
                "selected_as_final": class_payload["path_class_id"] in selected_path_class_ids,
                "selection_reason": class_payload["selection_reason"],
                "representative_candidate_id": class_payload["representative_candidate_id"],
                "representative_source_line_id": class_payload["representative_source_line_id"],
                "representative_source_kind": class_payload["representative_source_kind"],
                "representative_source_id": class_payload["representative_source_id"],
                "representative_branch_index": class_payload["representative_branch_index"],
                "candidate_ids": list(class_payload["candidate_ids"]),
                "line_group_signature": class_payload["line_group_signature"],
                "endpoint_decomposition_signature": class_payload["endpoint_decomposition_signature"],
                "local_row_space_signature": class_payload["local_row_space_signature"],
                "global_row_space_signature": class_payload["global_row_space_signature"],
                "phase_aware_profile_used": class_payload["phase_aware_profile_used"],
                "selection_stage": class_payload["selection_stage"],
                "row_space_contained_in_selected_span": class_payload["row_space_contained_in_selected_span"],
            }
        )
    report_pairs = []
    for pair_key in sorted(by_pair):
        entry = by_pair[pair_key]
        if len(entry["candidate_path_classes"]) == 1:
            verdict = "All candidates collapse to one strong path class."
        elif sum(int(item["selected_as_final"]) for item in entry["candidate_path_classes"]) > 1:
            verdict = (
                "Multiple strong path classes share this endpoint pair, and more than one "
                "must be retained because the endpoint-pair skeleton alone does not span "
                "the full candidate row language."
            )
        else:
            verdict = (
                "Multiple strong path classes share this endpoint pair; only classes whose "
                "row language is already contained in the published full-span shell are discarded."
            )
        entry["pair_verdict"] = verdict
        report_pairs.append(entry)
    return {
        "endpoint_pair_count": len(report_pairs),
        "selected_path_class_ids": sorted(selected_path_class_ids),
        "endpoint_pairs": report_pairs,
    }


def build_final_path_candidate_equivalence_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Final Path Candidate Equivalence Report",
        "",
        f"- Endpoint-pair groups inspected: `{report['endpoint_pair_count']}`.",
        f"- Selected path classes: `{report['selected_path_class_ids']}`.",
        "",
    ]
    for pair in report["endpoint_pairs"]:
        lines.extend(
            [
                f"## {pair['endpoint_pair'][0]}-{pair['endpoint_pair'][1]}",
                "",
                f"- Candidate count: `{pair['candidate_count']}`.",
                f"- Strong path-class count: `{pair['path_class_count']}`.",
                f"- Selected path classes in this pair: `{pair['selected_path_class_ids']}`.",
                f"- Verdict: {pair['pair_verdict']}",
                "",
            ]
        )
        for path_class in pair["candidate_path_classes"]:
            lines.append(
                "- "
                + f"`{path_class['path_class_id']}` from `{path_class['representative_source_line_id']}` "
                + f"(candidate `{path_class['representative_candidate_id']}`) selected = "
                + f"`{path_class['selected_as_final']}`; row-space rank "
                + f"`{path_class['global_row_space_signature']['row_rank']}`; "
                + f"selection stage = `{path_class['selection_stage']}`; "
                + f"contained in selected span = `{path_class['row_space_contained_in_selected_span']}`; "
                + f"reason: {path_class['selection_reason']}"
            )
        lines.append("")
    return "\n".join(lines)


def _record_by_path_class_id(reduction: dict[str, Any], path_class_id: str) -> dict[str, Any]:
    for payload in reduction.get("path_classes", []):
        if payload["path_class_id"] == path_class_id:
            return payload["candidate_records"][0]
    raise KeyError(f"unknown path class id: {path_class_id}")


def _record_basis_ids(record: dict[str, Any]) -> list[str]:
    return [entry["basis_id"] for entry in record.get("global_matrix_row_records", [])]


def _endpoint_decomposition_vectors(record: dict[str, Any]) -> dict[str, dict[str, tuple[int, ...]]]:
    basis_ids = _record_basis_ids(record)
    vectors: dict[str, dict[str, tuple[int, ...]]] = {}
    for endpoint in record["endpoint_decomposition_signature"]:
        endpoint_vectors: dict[str, tuple[int, ...]] = {}
        for rep in endpoint["reps"]:
            endpoint_vectors[rep["rep_id"]] = tuple(
                int(rep["decomposition_on_line_basis"].get(basis_id, 0))
                for basis_id in basis_ids
            )
        vectors[endpoint["endpoint_id"]] = endpoint_vectors
    return vectors


def _candidate_endpoint_relabel_rep_ids(
    reference_record: dict[str, Any],
    candidate_record: dict[str, Any],
) -> dict[str, list[str]]:
    reference_vectors = _endpoint_decomposition_vectors(reference_record)
    candidate_vectors = _endpoint_decomposition_vectors(candidate_record)
    differing: dict[str, list[str]] = {}
    for endpoint_id in sorted(reference_vectors):
        endpoint_differences = []
        for rep_id in sorted(reference_vectors[endpoint_id]):
            if reference_vectors[endpoint_id][rep_id] != candidate_vectors[endpoint_id][rep_id]:
                endpoint_differences.append(rep_id)
        differing[endpoint_id] = endpoint_differences
    return differing


def _build_endpoint_column_map(
    unknown_ordering: Sequence[str],
    endpoint_relabel: dict[str, dict[str, str]],
) -> list[int]:
    index = {unknown: position for position, unknown in enumerate(unknown_ordering)}
    column_map = list(range(len(unknown_ordering)))
    for relabel in endpoint_relabel.values():
        for source_unknown, target_unknown in relabel.items():
            column_map[index[source_unknown]] = index[target_unknown]
    return column_map


def _endpoint_relabel_search(
    reference_record: dict[str, Any],
    candidate_record: dict[str, Any],
    preserved_records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    unknown_ordering = list(reference_record["global_unknown_ordering"])
    if unknown_ordering != list(candidate_record["global_unknown_ordering"]):
        raise ValueError("reference/candidate records use different global unknown ordering")
    differing = _candidate_endpoint_relabel_rep_ids(reference_record, candidate_record)
    varying_endpoints = [endpoint_id for endpoint_id, rep_ids in differing.items() if rep_ids]
    reference_signature = _rref_signature(reference_record["global_matrix_rows"])
    search_space_size = 1
    endpoint_permutations: list[tuple[str, list[str], list[tuple[str, ...]]]] = []
    for endpoint_id in varying_endpoints:
        rep_ids = differing[endpoint_id]
        if len(rep_ids) > 6:
            return {
                "searched": False,
                "reason": f"endpoint {endpoint_id} has {len(rep_ids)} varying reps; exhaustive relabel search disabled",
                "varying_rep_ids_by_endpoint": differing,
                "search_space_size": None,
                "local_solution_count": 0,
                "shell_preserving_solution_count": 0,
                "local_solutions": [],
                "shell_preserving_solutions": [],
            }
        permutations_for_endpoint = list(permutations(rep_ids))
        endpoint_permutations.append((endpoint_id, rep_ids, permutations_for_endpoint))
        search_space_size *= len(permutations_for_endpoint)
        if search_space_size > 200000:
            return {
                "searched": False,
                "reason": f"search space {search_space_size} too large for exhaustive relabel search",
                "varying_rep_ids_by_endpoint": differing,
                "search_space_size": search_space_size,
                "local_solution_count": 0,
                "shell_preserving_solution_count": 0,
                "local_solutions": [],
                "shell_preserving_solutions": [],
            }

    preserved_signatures = {
        record["final_path_id"]: _rref_signature(record["global_matrix_rows"])
        for record in preserved_records
    }
    local_solutions: list[dict[str, Any]] = []
    shell_preserving_solutions: list[dict[str, Any]] = []
    cartesian_choices = [
        [(endpoint_id, rep_ids, permuted_rep_ids) for permuted_rep_ids in endpoint_permutation_list]
        for endpoint_id, rep_ids, endpoint_permutation_list in endpoint_permutations
    ]
    for relabel_choice in product(*cartesian_choices) if cartesian_choices else [()]:
        endpoint_relabel: dict[str, dict[str, str]] = {}
        for endpoint_id, rep_ids, permuted_rep_ids in relabel_choice:
            endpoint_relabel[endpoint_id] = {
                f"{endpoint_id}_{rep_id.split('_', 1)[1]}": f"{endpoint_id}_{target_rep_id.split('_', 1)[1]}"
                for rep_id, target_rep_id in zip(rep_ids, permuted_rep_ids)
            }
        column_map = _build_endpoint_column_map(unknown_ordering, endpoint_relabel)
        relabeled_candidate_rows = _apply_column_permutation(
            candidate_record["global_matrix_rows"],
            column_map,
        )
        if _rref_signature(relabeled_candidate_rows) != reference_signature:
            continue
        broken_path_ids = [
            path_id
            for path_id, preserved_signature in preserved_signatures.items()
            if _rref_signature(
                _apply_column_permutation(
                    next(record["global_matrix_rows"] for record in preserved_records if record["final_path_id"] == path_id),
                    column_map,
                )
            )
            != preserved_signature
        ]
        solution = {
            "endpoint_relabel": endpoint_relabel,
            "broken_selected_path_ids": broken_path_ids,
            "preserves_other_selected_shell": not broken_path_ids,
        }
        local_solutions.append(solution)
        if not broken_path_ids:
            shell_preserving_solutions.append(solution)
    return {
        "searched": True,
        "reason": None,
        "varying_rep_ids_by_endpoint": differing,
        "search_space_size": search_space_size,
        "local_solution_count": len(local_solutions),
        "shell_preserving_solution_count": len(shell_preserving_solutions),
        "local_solutions": local_solutions,
        "shell_preserving_solutions": shell_preserving_solutions,
    }


def _selected_pair_signature_sets(
    reduction: dict[str, Any],
) -> dict[tuple[str, str], set[tuple[tuple[str, ...], ...]]]:
    by_pair: dict[tuple[str, str], set[tuple[tuple[str, ...], ...]]] = {}
    for record in reduction.get("kept_paths", []):
        pair_key = tuple(record["endpoint_pair"])
        by_pair.setdefault(pair_key, set()).add(_rref_signature(record["global_matrix_rows"]))
    return by_pair


def _point_unknown_ordering(
    unknown_ordering: Sequence[str],
) -> dict[str, list[str]]:
    per_point: dict[str, list[str]] = {}
    for unknown in unknown_ordering:
        point_id = unknown.split("_", 1)[0]
        per_point.setdefault(point_id, []).append(unknown)
    return per_point


def _canonical_basis_permutation_for_record(record: dict[str, Any]) -> tuple[int, ...]:
    basis_ids = _record_basis_ids(record)
    basis_count = len(basis_ids)
    endpoint_rows: list[tuple[str, list[tuple[int, int, tuple[int, ...]]]]] = []
    for endpoint in record["endpoint_decomposition_signature"]:
        rows: list[tuple[int, int, tuple[int, ...]]] = []
        for rep in endpoint["reps"]:
            vector = tuple(
                int(rep["decomposition_on_line_basis"].get(basis_id, 0))
                for basis_id in basis_ids
            )
            rows.append((int(rep["rep_degree"]), int(rep["torsion"]), vector))
        endpoint_rows.append((endpoint["endpoint_id"], rows))

    best_key = None
    best_permutation: tuple[int, ...] | None = None
    for permutation in permutations(range(basis_count)):
        endpoint_key = []
        for endpoint_id, rows in endpoint_rows:
            transformed_rows = sorted(
                (
                    degree,
                    torsion,
                    tuple(vector[index] for index in permutation),
                )
                for degree, torsion, vector in rows
            )
            endpoint_key.append((endpoint_id, tuple(transformed_rows)))
        candidate_key = (
            tuple(record["endpoint_pair"]),
            _line_group_signature_key(record["line_group_signature"]),
            tuple(endpoint_key),
        )
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_permutation = tuple(permutation)
    if best_permutation is None:
        return tuple(range(basis_count))
    return best_permutation


def _endpoint_rep_fingerprints_on_canonical_line_basis(
    record: dict[str, Any],
) -> dict[str, list[tuple[tuple[Any, ...], int, int, tuple[int, ...]]]]:
    basis_permutation = _canonical_basis_permutation_for_record(record)
    endpoint_pair = list(record["endpoint_pair"])
    endpoint_capture_ids = list(record.get("endpoint_capture_ids", []))
    capture_by_point = {
        endpoint_pair[index]: endpoint_capture_ids[index]
        for index in range(min(len(endpoint_pair), len(endpoint_capture_ids)))
    }
    fingerprints: dict[str, list[tuple[tuple[Any, ...], int, int, tuple[int, ...]]]] = {}
    for endpoint in record["endpoint_decomposition_signature"]:
        point_id = endpoint["endpoint_id"]
        other_endpoint_id = next(item for item in endpoint_pair if item != point_id)
        capture_id = capture_by_point.get(point_id, point_id)
        family_key = (
            str(record["source_line_id"]),
            other_endpoint_id,
            _line_group_signature_key(record["line_group_signature"]),
        )
        rep_fingerprints: list[tuple[tuple[Any, ...], int, int, tuple[int, ...]]] = []
        for rep in endpoint["reps"]:
            vector = tuple(
                int(rep["decomposition_on_line_basis"].get(basis_id, 0))
                for basis_id in _record_basis_ids(record)
            )
            transformed = tuple(vector[index] for index in basis_permutation)
            rep_fingerprints.append(
                (
                    family_key,
                    int(rep["rep_degree"]),
                    int(rep["torsion"]),
                    transformed,
                )
            )
        fingerprints[capture_id] = rep_fingerprints
    return fingerprints


def _score_capture_permutation(
    canonical_fingerprints: Sequence[tuple[Any, ...]],
    alias_fingerprints: Sequence[tuple[Any, ...]],
    permutation: Sequence[int],
) -> tuple[int, int]:
    exact_matches = 0
    overlap = 0
    for local_index, canonical_index in enumerate(permutation):
        alias_fp = alias_fingerprints[local_index]
        canonical_fp = canonical_fingerprints[canonical_index]
        if alias_fp == canonical_fp:
            exact_matches += 1
            overlap += len(alias_fp)
            continue
            overlap += len(set(alias_fp) & set(canonical_fp))
    return exact_matches, overlap


def _best_capture_permutation_by_exact_matches(
    canonical_fingerprints: Sequence[tuple[Any, ...]],
    alias_fingerprints: Sequence[tuple[Any, ...]],
) -> tuple[int, ...]:
    rep_count = len(alias_fingerprints)
    if rep_count <= 1:
        return tuple(range(rep_count))
    score_matrix: list[list[tuple[int, int]]] = []
    for alias_fp in alias_fingerprints:
        row_scores: list[tuple[int, int]] = []
        for canonical_fp in canonical_fingerprints:
            exact_matches = 1 if alias_fp == canonical_fp else 0
            overlap = len(alias_fp) if exact_matches else 0
            row_scores.append((exact_matches, overlap))
        score_matrix.append(row_scores)

    memo: dict[tuple[int, int], tuple[tuple[int, int], tuple[int, ...]]] = {}

    def solve(local_index: int, used_mask: int) -> tuple[tuple[int, int], tuple[int, ...]]:
        key = (local_index, used_mask)
        cached = memo.get(key)
        if cached is not None:
            return cached
        if local_index >= rep_count:
            result = ((0, 0), tuple())
            memo[key] = result
            return result

        best_score: tuple[int, int] | None = None
        best_suffix: tuple[int, ...] | None = None
        for canonical_index in range(rep_count):
            if used_mask & (1 << canonical_index):
                continue
            tail_score, tail_suffix = solve(local_index + 1, used_mask | (1 << canonical_index))
            pair_score = score_matrix[local_index][canonical_index]
            candidate_score = (
                pair_score[0] + tail_score[0],
                pair_score[1] + tail_score[1],
            )
            candidate_suffix = (canonical_index,) + tail_suffix
            if (
                best_score is None
                or candidate_score > best_score
                or (
                    candidate_score == best_score
                    and best_suffix is not None
                    and candidate_suffix < best_suffix
                )
            ):
                best_score = candidate_score
                best_suffix = candidate_suffix
        assert best_score is not None and best_suffix is not None
        result = (best_score, best_suffix)
        memo[key] = result
        return result

    return tuple(int(index) for index in solve(0, 0)[1])


def _permute_fingerprint_slots(
    slot_payload: Sequence[Sequence[tuple[Any, ...]]],
    permutation: Sequence[int],
) -> list[tuple[Any, ...]]:
    remapped: list[tuple[Any, ...]] = [tuple() for _ in range(len(slot_payload))]
    for local_index, canonical_index in enumerate(permutation):
        remapped[canonical_index] = tuple(slot_payload[local_index])
    return remapped


def _canonical_context_slot_payload(
    context_payload: dict[tuple[Any, ...], dict[int, list[tuple[Any, ...]]]],
    rep_count: int,
) -> list[tuple[tuple[Any, ...], tuple[Any, ...]]]:
    canonical_payload: list[tuple[tuple[Any, ...], tuple[Any, ...]]] = []
    for context_key in sorted(context_payload):
        slot_payload = [
            tuple(sorted(context_payload[context_key].get(rep_index, [])))
            for rep_index in range(1, rep_count + 1)
        ]
        canonical_payload.append((context_key, tuple(slot_payload)))
    return canonical_payload


def _choose_canonical_capture_default_permutation(
    context_payload: dict[tuple[Any, ...], dict[int, list[tuple[Any, ...]]]],
    rep_count: int,
) -> tuple[int, ...]:
    if rep_count <= 1:
        return tuple(range(rep_count))
    canonical_payload = _canonical_context_slot_payload(context_payload, rep_count)
    if not canonical_payload:
        return tuple(range(rep_count))
    local_signatures: list[tuple[Any, ...]] = []
    for local_index in range(rep_count):
        signature = []
        for context_key, slot_payload in canonical_payload:
            signature.append((context_key, slot_payload[local_index]))
        local_signatures.append(tuple(signature))
    sorted_local_indices = sorted(
        range(rep_count),
        key=lambda local_index: (local_signatures[local_index], local_index),
    )
    permutation = [0] * rep_count
    for canonical_index, local_index in enumerate(sorted_local_indices):
        permutation[local_index] = canonical_index
    return tuple(permutation)


def _publication_point_permutation_context_key(
    record: dict[str, Any],
    point_id: str,
) -> tuple[Any, ...]:
    endpoint_pair = list(record["endpoint_pair"])
    other_endpoint_id = next(item for item in endpoint_pair if item != point_id)
    return (
        str(record["source_line_id"]),
        other_endpoint_id,
        _line_group_signature_key(record["line_group_signature"]),
    )


def _build_publication_point_capture_permutations(
    reduction: dict[str, Any],
    point_unknown_ordering: dict[str, list[str]],
) -> dict[str, dict[str, dict[str, Any]]]:
    candidate_records = list(reduction.get("candidate_path_records", []))
    by_point_capture: dict[str, dict[str, dict[int, list[tuple[Any, ...]]]]] = {}
    by_point_capture_context: dict[
        str,
        dict[str, dict[tuple[Any, ...], dict[int, list[tuple[Any, ...]]]]],
    ] = {}
    for record in candidate_records:
        endpoint_pair = list(record["endpoint_pair"])
        endpoint_capture_ids = list(record.get("endpoint_capture_ids", []))
        fingerprints_by_capture = _endpoint_rep_fingerprints_on_canonical_line_basis(record)
        for endpoint_index, point_id in enumerate(endpoint_pair):
            if endpoint_index >= len(endpoint_capture_ids):
                continue
            capture_id = endpoint_capture_ids[endpoint_index]
            rep_fingerprints = fingerprints_by_capture.get(capture_id)
            if rep_fingerprints is None:
                continue
            capture_payload = by_point_capture.setdefault(point_id, {}).setdefault(capture_id, {})
            context_key = _publication_point_permutation_context_key(record, point_id)
            context_payload = (
                by_point_capture_context
                .setdefault(point_id, {})
                .setdefault(capture_id, {})
                .setdefault(context_key, {})
            )
            for rep_index, rep_fingerprint in enumerate(rep_fingerprints, start=1):
                capture_payload.setdefault(rep_index, []).append(rep_fingerprint)
                context_payload.setdefault(rep_index, []).append(rep_fingerprint)

    permutations_by_point: dict[str, dict[str, dict[str, Any]]] = {}
    for point in reduction.get("point_shell", []):
        point_id = point["point_id"]
        rep_unknowns = point_unknown_ordering.get(point_id, [])
        rep_count = len(rep_unknowns)
        if rep_count <= 1:
            continue
        alias_capture_ids = [alias["capture_id"] for alias in point.get("aliases", [])]
        canonical_capture_id = point_id if point_id in alias_capture_ids else alias_capture_ids[0]
        capture_payload = by_point_capture.get(point_id, {})
        capture_context_payload = by_point_capture_context.get(point_id, {})
        canonical_context_payload = capture_context_payload.get(canonical_capture_id, {})
        canonical_default_permutation = tuple(range(rep_count))
        canonical_payload = capture_payload.get(canonical_capture_id, {})
        canonical_fingerprints = _permute_fingerprint_slots(
            [
                tuple(sorted(canonical_payload.get(rep_index, [])))
                for rep_index in range(1, rep_count + 1)
            ],
            canonical_default_permutation,
        )
        point_permutations: dict[str, dict[str, Any]] = {
            canonical_capture_id: {
                "default": canonical_default_permutation,
                "by_context": {},
            }
        }
        for capture_id in alias_capture_ids:
            best_permutation = tuple(range(rep_count))
            if capture_id != canonical_capture_id:
                alias_payload = capture_payload.get(capture_id, {})
                alias_fingerprints = [
                    tuple(sorted(alias_payload.get(rep_index, [])))
                    for rep_index in range(1, rep_count + 1)
                ]
                best_permutation = _best_capture_permutation_by_exact_matches(
                    canonical_fingerprints,
                    alias_fingerprints,
                )
            context_permutations: dict[tuple[Any, ...], tuple[int, ...]] = {}
            context_keys = set(capture_context_payload.get(capture_id, {}).keys())
            context_keys.update(capture_context_payload.get(canonical_capture_id, {}).keys())
            for context_key in context_keys:
                canonical_context_payload = capture_context_payload.get(canonical_capture_id, {}).get(context_key, {})
                alias_context_payload = capture_context_payload.get(capture_id, {}).get(context_key, {})
                if not canonical_context_payload or not alias_context_payload:
                    continue
                canonical_context_fingerprints = _permute_fingerprint_slots(
                    [
                        tuple(sorted(canonical_context_payload.get(rep_index, [])))
                        for rep_index in range(1, rep_count + 1)
                    ],
                    canonical_default_permutation,
                )
                alias_context_fingerprints = [
                    tuple(sorted(alias_context_payload.get(rep_index, [])))
                    for rep_index in range(1, rep_count + 1)
                ]
                best_context_permutation = _best_capture_permutation_by_exact_matches(
                    canonical_context_fingerprints,
                    alias_context_fingerprints,
                )
                context_permutations[context_key] = best_context_permutation
            point_permutations[capture_id] = {
                "default": best_permutation,
                "by_context": context_permutations,
            }
        if point_permutations:
            permutations_by_point[point_id] = point_permutations
    return permutations_by_point


def _lookup_publication_point_capture_permutation(
    record: dict[str, Any],
    point_id: str,
    capture_id: str,
    point_capture_permutations: dict[str, dict[str, dict[str, Any]]],
) -> tuple[int, ...] | None:
    capture_entry = point_capture_permutations.get(point_id, {}).get(capture_id)
    if capture_entry is None:
        return None
    context_key = _publication_point_permutation_context_key(record, point_id)
    context_permutations = capture_entry.get("by_context", {})
    if context_key in context_permutations:
        return tuple(int(index) for index in context_permutations[context_key])
    default_permutation = capture_entry.get("default")
    if default_permutation is None:
        return None
    return tuple(int(index) for index in default_permutation)


def _transform_publication_row_records_to_point_family_basis(
    record: dict[str, Any],
    row_records: Sequence[dict[str, Any]],
    point_unknown_ordering: dict[str, list[str]],
    point_capture_permutations: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    unknown_ordering = list(record["global_unknown_ordering"])
    unknown_index = {unknown: index for index, unknown in enumerate(unknown_ordering)}
    endpoint_pair = list(record["endpoint_pair"])
    endpoint_capture_ids = list(record.get("endpoint_capture_ids", []))
    capture_by_point = {
        endpoint_pair[index]: endpoint_capture_ids[index]
        for index in range(min(len(endpoint_pair), len(endpoint_capture_ids)))
    }
    transformed_records: list[dict[str, Any]] = []
    for row_record in row_records:
        row = list(row_record["matrix_row"])
        transformed_row = list(row)
        transforms_applied: list[dict[str, Any]] = []
        for point_id, capture_id in capture_by_point.items():
            permutation = _lookup_publication_point_capture_permutation(
                record,
                point_id,
                capture_id,
                point_capture_permutations,
            )
            if permutation is None or all(index == local_index for local_index, index in enumerate(permutation)):
                continue
            block_unknowns = point_unknown_ordering.get(point_id, [])
            if len(block_unknowns) != len(permutation):
                continue
            block_values = [row[unknown_index[unknown]] for unknown in block_unknowns]
            remapped_values = [0] * len(block_values)
            for local_index, canonical_index in enumerate(permutation):
                remapped_values[canonical_index] += int(block_values[local_index])
            for position, unknown in enumerate(block_unknowns):
                transformed_row[unknown_index[unknown]] = remapped_values[position]
            transforms_applied.append(
                {
                    "point_id": point_id,
                    "capture_id": capture_id,
                    "context_key": [
                        str(item)
                        for item in _publication_point_permutation_context_key(record, point_id)
                    ],
                    "local_to_canonical_permutation": [int(index) for index in permutation],
                }
            )
        transformed_records.append(
            {
                **row_record,
                "matrix_row": transformed_row,
                "publication_point_basis_transforms": transforms_applied,
            }
        )
    return transformed_records


def _publication_point_id_by_capture(
    reduction: dict[str, Any],
) -> dict[str, str]:
    capture_to_point: dict[str, str] = {}
    for point in reduction.get("point_shell", []):
        point_id = str(point["point_id"])
        capture_to_point[point_id] = point_id
        for alias in point.get("aliases", []):
            capture_id = str(alias.get("capture_id", point_id))
            capture_to_point[capture_id] = point_id
    return capture_to_point


def _lookup_publication_point_default_permutation(
    point_id: str,
    capture_id: str,
    point_capture_permutations: dict[str, dict[str, dict[str, Any]]],
    rep_count: int,
) -> tuple[int, ...]:
    capture_entry = point_capture_permutations.get(point_id, {}).get(capture_id)
    if capture_entry is None:
        return tuple(range(rep_count))
    default = capture_entry.get("default")
    if default is None:
        return tuple(range(rep_count))
    permutation = tuple(int(index) for index in default)
    if len(permutation) != rep_count:
        return tuple(range(rep_count))
    return permutation


def _transform_plane_equation_to_publication_point_row(
    equation: dict[str, Any],
    unknown_ordering: Sequence[str],
    point_unknown_ordering: dict[str, list[str]],
    capture_to_point: dict[str, str],
    point_capture_permutations: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    capture_id = str(equation.get("capture_id", equation["point_id"]))
    publication_point_id = capture_to_point.get(capture_id) or capture_to_point.get(str(equation["point_id"]))
    if publication_point_id is None:
        return None
    publication_unknowns = point_unknown_ordering.get(publication_point_id, [])
    if not publication_unknowns:
        return None
    permutation = _lookup_publication_point_default_permutation(
        publication_point_id,
        capture_id,
        point_capture_permutations,
        len(publication_unknowns),
    )
    unknown_index = {unknown: index for index, unknown in enumerate(unknown_ordering)}
    row = [0] * len(unknown_ordering)
    for term in equation["terms"]:
        if term.get("side") != "point":
            continue
        raw_unknown = str(term["unknown"])
        local_index = int(raw_unknown.split("_R", 1)[1]) - 1
        if local_index < 0 or local_index >= len(publication_unknowns):
            raise ValueError(
                f"plane equation {equation['basis_id']} references rep index {local_index + 1} "
                f"outside publication point {publication_point_id} basis size {len(publication_unknowns)}"
            )
        canonical_index = permutation[local_index]
        unknown = publication_unknowns[canonical_index]
        row[unknown_index[unknown]] += int(term["coeff"])
    if not any(row):
        return None
    return {
        "basis_id": equation["basis_id"],
        "row_kind": equation.get("row_kind", "publication_plane_corner_basis"),
        "publication_point_id": publication_point_id,
        "raw_point_id": str(equation["point_id"]),
        "capture_id": capture_id,
        "point_coordinates": list(equation.get("point_coordinates", [])),
        "matrix_row": row,
        "publication_point_basis_permutation": [int(index) for index in permutation],
    }


def _publication_plane_relation_sort_key(
    row_record: dict[str, Any],
    point_order: dict[str, int],
) -> tuple[Any, ...]:
    left_id = row_record["left_publication_point_id"]
    right_id = row_record["right_publication_point_id"]
    return (
        min(point_order[left_id], point_order[right_id]),
        max(point_order[left_id], point_order[right_id]),
        row_record["plane_id"],
        row_record["plane_basis_id"],
        row_record["left_capture_id"],
        row_record["right_capture_id"],
    )


def _publication_plane_group_sort_key(
    payload: dict[str, Any],
    point_order: dict[str, int],
) -> tuple[Any, ...]:
    corner_ids = list(payload["publication_corner_ids"])
    ordered_corners = tuple(sorted((point_order[item], item) for item in corner_ids))
    return (
        ordered_corners,
        tuple(payload["member_plane_ids"]),
        payload["publication_plane_class_id"],
    )


def build_publication_plane_classes(
    reduction: dict[str, Any],
    publication_point_shell: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plane_blocks = list(reduction.get("plane_blocks", []))
    if not plane_blocks:
        return {
            "publication_plane_class_count": 0,
            "selected_publication_plane_count": 0,
            "publication_plane_classes": [],
            "selected_publication_plane_classes": [],
            "publication_planes": [],
        }
    publication_point_shell = publication_point_shell or build_publication_point_shell(reduction)
    unknown_ordering = list(publication_point_shell["unknown_ordering"])
    point_unknown_ordering = {
        point_id: list(unknowns)
        for point_id, unknowns in publication_point_shell["point_unknown_ordering"].items()
    }
    point_order = {
        point_id: index
        for index, point_id in enumerate(publication_point_shell["point_ids"])
    }
    capture_to_point = _publication_point_id_by_capture(reduction)
    point_capture_permutations = _build_publication_point_capture_permutations(
        reduction,
        point_unknown_ordering,
    )

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for block in plane_blocks:
        equations_by_basis: dict[str, list[dict[str, Any]]] = {}
        publication_corner_ids: set[str] = set()
        for equation in block.get("equations", []):
            transformed = _transform_plane_equation_to_publication_point_row(
                equation,
                unknown_ordering,
                point_unknown_ordering,
                capture_to_point,
                point_capture_permutations,
            )
            if transformed is None:
                continue
            equations_by_basis.setdefault(str(equation["basis_id"]), []).append(transformed)
            publication_corner_ids.add(transformed["publication_point_id"])
        if len(publication_corner_ids) < 2:
            continue

        candidate_row_records: list[dict[str, Any]] = []
        for basis_id, entries in equations_by_basis.items():
            entries = sorted(
                entries,
                key=lambda item: (
                    point_order[item["publication_point_id"]],
                    item["capture_id"],
                    item["raw_point_id"],
                ),
            )
            basis_candidate_rows: list[dict[str, Any]] = []
            for relation_index, (left, right) in enumerate(combinations(entries, 2), start=1):
                if left["publication_point_id"] == right["publication_point_id"]:
                    continue
                diff_row = [
                    int(left_value) - int(right_value)
                    for left_value, right_value in zip(left["matrix_row"], right["matrix_row"])
                ]
                if not any(diff_row):
                    continue
                basis_candidate_rows.append(
                    {
                        "basis_id": f"{block['plane_id']}::{basis_id}::{relation_index:02d}",
                        "row_kind": "publication_plane_family_basis",
                        "plane_id": block["plane_id"],
                        "plane_basis_id": basis_id,
                        "left_publication_point_id": left["publication_point_id"],
                        "right_publication_point_id": right["publication_point_id"],
                        "left_capture_id": left["capture_id"],
                        "right_capture_id": right["capture_id"],
                        "left_raw_point_id": left["raw_point_id"],
                        "right_raw_point_id": right["raw_point_id"],
                        "matrix_row": diff_row,
                    }
                )
            seen_row_signatures: set[tuple[int, ...]] = set()
            for row_record in sorted(
                basis_candidate_rows,
                key=lambda item: _publication_plane_relation_sort_key(item, point_order),
            ):
                row_signature = tuple(_primitive_integer_row(row_record["matrix_row"]))
                if row_signature in seen_row_signatures:
                    continue
                seen_row_signatures.add(row_signature)
                candidate_row_records.append(
                    {
                        **row_record,
                        "matrix_row": list(row_signature),
                    }
                )

        if not candidate_row_records:
            continue

        candidate_row_records.sort(key=lambda item: _publication_plane_relation_sort_key(item, point_order))
        selected_rows = [list(item["matrix_row"]) for item in candidate_row_records]
        group_key = (
            tuple(sorted(publication_corner_ids, key=point_order.get)),
            _symmetry_summary_signature(block.get("plane_symmetry_summary")),
            len(block.get("plane_basis_labels", [])),
            _rref_signature(selected_rows),
        )
        grouped.setdefault(group_key, []).append(
            {
                "plane_id": block["plane_id"],
                "publication_corner_ids": sorted(publication_corner_ids, key=point_order.get),
                "selected_basis_row_records": candidate_row_records,
                "selected_basis_rows": selected_rows,
                "selected_basis_row_rank": _row_rank(selected_rows),
                "plane_basis_labels": list(block.get("plane_basis_labels", [])),
                "plane_symmetry_summary": block.get("plane_symmetry_summary"),
            }
        )

    publication_plane_classes: list[dict[str, Any]] = []
    for class_index, group_key in enumerate(
        sorted(
            grouped,
            key=lambda item: (
                tuple(point_order[point_id] for point_id in grouped[item][0]["publication_corner_ids"]),
                grouped[item][0]["plane_id"],
            ),
        ),
        start=1,
    ):
        members = sorted(grouped[group_key], key=lambda item: item["plane_id"])
        representative = members[0]
        publication_plane_classes.append(
            {
                "publication_plane_class_id": f"PUBPLANECLASS{class_index:02d}",
                "member_plane_ids": [member["plane_id"] for member in members],
                "publication_corner_ids": list(representative["publication_corner_ids"]),
                "selected_basis_row_count": len(representative["selected_basis_rows"]),
                "selected_basis_row_rank": int(representative["selected_basis_row_rank"]),
                "selected_basis_row_records": list(representative["selected_basis_row_records"]),
                "selected_basis_rows": list(representative["selected_basis_rows"]),
                "plane_symmetry_summary": representative.get("plane_symmetry_summary"),
            }
        )

    publication_plane_classes.sort(key=lambda item: _publication_plane_group_sort_key(item, point_order))
    publication_planes: list[dict[str, Any]] = []
    for plane_index, payload in enumerate(publication_plane_classes, start=1):
        publication_planes.append(
            {
                "publication_plane_id": f"PPLANE{plane_index:02d}",
                "publication_plane_class_id": payload["publication_plane_class_id"],
                "publication_corner_ids": list(payload["publication_corner_ids"]),
                "member_plane_ids": list(payload["member_plane_ids"]),
                "selected_basis_row_records": list(payload["selected_basis_row_records"]),
                "selected_basis_rows": list(payload["selected_basis_rows"]),
            }
        )
    return {
        "publication_plane_class_count": len(publication_plane_classes),
        "selected_publication_plane_count": len(publication_planes),
        "publication_plane_classes": publication_plane_classes,
        "selected_publication_plane_classes": publication_plane_classes,
        "publication_planes": publication_planes,
    }


def _primitive_integer_row(row: Sequence[Any]) -> list[int]:
    exact_row = [sp.nsimplify(value) for value in row]
    denominator_lcm = 1
    for value in exact_row:
        if isinstance(value, sp.Rational):
            denominator_lcm = sp.ilcm(denominator_lcm, int(value.q))
    integer_row = [int(sp.nsimplify(value * denominator_lcm)) for value in exact_row]
    common_divisor = 0
    for value in integer_row:
        common_divisor = gcd(common_divisor, abs(int(value)))
    if common_divisor > 1:
        integer_row = [int(value // common_divisor) for value in integer_row]
    for value in integer_row:
        if value == 0:
            continue
        if value < 0:
            integer_row = [-item for item in integer_row]
        break
    return integer_row


def _rank_gaining_rows(rows: Sequence[Sequence[int]]) -> list[list[int]]:
    selected: list[list[int]] = []
    running_rows: list[list[int]] = []
    running_rank = 0
    for row in rows:
        candidate = [int(value) for value in row]
        candidate_rank = _row_rank(running_rows + [candidate])
        if candidate_rank > running_rank:
            selected.append(candidate)
            running_rows.append(candidate)
            running_rank = candidate_rank
    return selected


def _pairwise_row_space_intersection(
    left_rows: Sequence[Sequence[int]],
    right_rows: Sequence[Sequence[int]],
) -> list[list[int]]:
    if not left_rows or not right_rows:
        return []
    left = sp.Matrix(left_rows)
    right = sp.Matrix(right_rows)
    complement_basis = left.nullspace() + right.nullspace()
    if complement_basis:
        intersection_basis = sp.Matrix.hstack(*complement_basis).T.nullspace()
        rows = [_primitive_integer_row(vector) for vector in intersection_basis]
    else:
        rows = [_primitive_integer_row(row) for row in left.rowspace()]
    return _rank_gaining_rows(rows)


def _row_space_intersection_basis(
    member_row_sets: Sequence[Sequence[Sequence[int]]],
) -> list[list[int]]:
    if not member_row_sets:
        return []
    current_rows = _rank_gaining_rows(member_row_sets[0])
    for rows in member_row_sets[1:]:
        current_rows = _pairwise_row_space_intersection(current_rows, rows)
        if not current_rows:
            break
    return current_rows


def _record_point_rep_signature(
    record: dict[str, Any],
    point_id: str,
) -> tuple[tuple[int, int], ...] | None:
    for endpoint in record.get("endpoint_decomposition_signature", []):
        if endpoint["endpoint_id"] != point_id:
            continue
        return tuple(
            sorted(
                (
                    int(rep["rep_degree"]),
                    int(rep["torsion"]),
                )
                for rep in endpoint["reps"]
            )
        )
    return None


def _point_shell_search_metadata(
    reduction: dict[str, Any],
    unknown_ordering: Sequence[str],
) -> dict[str, dict[str, Any]]:
    point_unknowns = _point_unknown_ordering(unknown_ordering)
    metadata: dict[str, dict[str, Any]] = {}
    rep_signatures: dict[str, set[tuple[tuple[int, int], ...]]] = {}
    for payload in reduction.get("path_classes", []):
        for record in payload.get("candidate_records", [])[:1]:
            for endpoint in record.get("endpoint_decomposition_signature", []):
                point_id = endpoint["endpoint_id"]
                rep_signatures.setdefault(point_id, set()).add(
                    tuple(
                        sorted(
                            (
                                int(rep["rep_degree"]),
                                int(rep["torsion"]),
                            )
                            for rep in endpoint["reps"]
                        )
                    )
                )
    path_incidence: dict[str, list[dict[str, Any]]] = {}
    for kept in reduction.get("kept_paths", []):
        for endpoint_id in kept.get("endpoint_ids", []):
            other_endpoint = next(
                point for point in kept["endpoint_ids"] if point != endpoint_id
            )
            path_incidence.setdefault(endpoint_id, []).append(
                {
                    "final_path_id": kept["final_path_id"],
                    "path_class_id": kept["path_class_id"],
                    "source_line_id": kept["source_line_id"],
                    "other_endpoint_id": other_endpoint,
                    "endpoint_pair": list(kept["endpoint_pair"]),
                    "selection_stage": kept["selection_stage"],
                }
            )
    for point in reduction.get("point_shell", []):
        point_id = point["point_id"]
        point_rep_signatures = rep_signatures.get(point_id, set())
        if len(point_rep_signatures) > 1:
            raise ValueError(
                f"inconsistent point-shell rep signature for {point_id}: {sorted(point_rep_signatures)}"
            )
        rep_signature = next(iter(point_rep_signatures), tuple())
        metadata[point_id] = {
            "point_id": point_id,
            "unknown_ordering": list(point_unknowns.get(point_id, [])),
            "unknown_count": len(point_unknowns.get(point_id, [])),
            "rep_signature": [[degree, torsion] for degree, torsion in rep_signature],
            "coarse_search_signature": {
                "unknown_count": len(point_unknowns.get(point_id, [])),
                "rep_degree_torsion_multiset": [[degree, torsion] for degree, torsion in rep_signature],
            },
            "incident_final_path_ids": [entry["final_path_id"] for entry in path_incidence.get(point_id, [])],
            "incident_source_line_ids": [entry["source_line_id"] for entry in path_incidence.get(point_id, [])],
            "incident_endpoint_pairs": [entry["endpoint_pair"] for entry in path_incidence.get(point_id, [])],
            "incident_path_classes": [entry["path_class_id"] for entry in path_incidence.get(point_id, [])],
        }
    return metadata


def _point_search_equivalence_classes(
    reduction: dict[str, Any],
    unknown_ordering: Sequence[str],
    *,
    exclude_points: Sequence[str] = (),
) -> list[dict[str, Any]]:
    point_metadata = _point_shell_search_metadata(reduction, unknown_ordering)
    excluded = set(exclude_points)
    by_signature: dict[tuple[Any, ...], list[str]] = {}
    for point_id, metadata in point_metadata.items():
        if point_id in excluded:
            continue
        signature = (
            int(metadata["coarse_search_signature"]["unknown_count"]),
            tuple(
                tuple(item)
                for item in metadata["coarse_search_signature"]["rep_degree_torsion_multiset"]
            ),
        )
        by_signature.setdefault(signature, []).append(point_id)
    classes: list[dict[str, Any]] = []
    for class_index, signature in enumerate(sorted(by_signature), start=1):
        point_ids = sorted(by_signature[signature])
        classes.append(
            {
                "point_class_id": f"POINTCLASS{class_index:02d}",
                "point_ids": point_ids,
                "signature": {
                    "unknown_count": int(signature[0]),
                    "rep_degree_torsion_multiset": [list(item) for item in signature[1]],
                },
                "search_enabled": len(point_ids) > 1,
            }
        )
    return classes


def _transport_endpoint_pair(
    endpoint_pair: Sequence[str],
    point_id_mapping: dict[str, str],
) -> tuple[str, str]:
    return tuple(sorted(point_id_mapping.get(point_id, point_id) for point_id in endpoint_pair))


def _global_shell_automorphism_search(
    reduction: dict[str, Any],
    reference_record: dict[str, Any],
    candidate_record: dict[str, Any],
    preserved_records: Sequence[dict[str, Any]],
    local_relabel_search: dict[str, Any],
    *,
    allowed_pair_signatures: dict[tuple[str, str], set[tuple[tuple[str, ...], ...]]],
    search_space_cap: int = 200000,
) -> dict[str, Any]:
    unknown_ordering = list(reference_record["global_unknown_ordering"])
    if unknown_ordering != list(candidate_record["global_unknown_ordering"]):
        raise ValueError("reference/candidate records use different global unknown ordering")
    point_unknowns = _point_unknown_ordering(unknown_ordering)
    point_metadata = _point_shell_search_metadata(reduction, unknown_ordering)
    reference_signature = _rref_signature(reference_record["global_matrix_rows"])
    local_solutions = list(local_relabel_search.get("local_solutions", []))
    if not local_solutions:
        return {
            "searched": False,
            "reason": "no local P1/P5 relabel witness exists to anchor the global shell search",
            "local_solution_count": 0,
            "local_solution_search_space": 0,
            "search_space_size": 0,
            "searched_candidate_count": 0,
            "point_id_permutations_enabled": True,
            "point_shell_equivalence_classes": _point_search_equivalence_classes(reduction, unknown_ordering),
            "active_point_shell_equivalence_classes": [],
            "compensation_points": [],
            "point_permutation_sizes": {},
            "local_solution_searches": [],
            "global_solution_count": 0,
            "first_global_solution": None,
            "all_global_solutions": [],
        }

    total_search_space = 0
    searched_candidate_count = 0
    local_solution_searches: list[dict[str, Any]] = []
    global_solutions: list[dict[str, Any]] = []
    all_equivalence_classes = _point_search_equivalence_classes(reduction, unknown_ordering)
    for local_solution_index, local_solution in enumerate(local_solutions, start=1):
        varying_endpoints = set(local_solution["endpoint_relabel"])
        broken_path_ids = list(local_solution.get("broken_selected_path_ids", []))
        active_classes = [
            point_class
            for point_class in _point_search_equivalence_classes(
                reduction,
                unknown_ordering,
                exclude_points=sorted(varying_endpoints),
            )
            if point_class["search_enabled"]
        ]
        point_permutation_sizes: dict[str, int] = {}
        local_search_space = 1
        oversized_class = None
        for point_class in active_classes:
            point_ids = list(point_class["point_ids"])
            if any(len(point_unknowns.get(point_id, [])) > 7 for point_id in point_ids):
                oversized_class = point_class["point_class_id"]
                break
            class_search_space = factorial(len(point_ids))
            for point_id in point_ids:
                class_search_space *= factorial(len(point_unknowns.get(point_id, [])))
                point_permutation_sizes[point_id] = factorial(len(point_unknowns.get(point_id, [])))
            point_class["search_space_size"] = int(class_search_space)
            local_search_space *= max(1, int(class_search_space))
        if oversized_class is not None:
            local_solution_searches.append(
                {
                    "local_solution_index": local_solution_index,
                    "search_enabled": False,
                    "reason": (
                        f"point-shell class {oversized_class} contains a point with more than 7 unknowns; "
                        "full point-shell automorphism search disabled"
                    ),
                    "broken_path_ids": broken_path_ids,
                    "varying_endpoints": sorted(varying_endpoints),
                    "compensation_points": sorted(
                        {
                            point_id
                            for point_class in active_classes
                            for point_id in point_class["point_ids"]
                        }
                    ),
                    "active_point_shell_equivalence_classes": active_classes,
                    "point_permutation_sizes": point_permutation_sizes,
                    "search_space_size": None,
                    "searched_candidate_count": 0,
                    "global_solution_count": 0,
                    "first_global_solution": None,
                }
            )
            continue
        if total_search_space + local_search_space > search_space_cap:
            local_solution_searches.append(
                {
                    "local_solution_index": local_solution_index,
                    "search_enabled": False,
                    "reason": (
                        f"cumulative search space would exceed cap {search_space_cap}; "
                        f"next local branch requires {local_search_space} permutations "
                        "after enabling point-ID permutations inside the active point-shell classes"
                    ),
                    "broken_path_ids": broken_path_ids,
                    "varying_endpoints": sorted(varying_endpoints),
                    "compensation_points": sorted(
                        {
                            point_id
                            for point_class in active_classes
                            for point_id in point_class["point_ids"]
                        }
                    ),
                    "active_point_shell_equivalence_classes": active_classes,
                    "point_permutation_sizes": point_permutation_sizes,
                    "search_space_size": local_search_space,
                    "searched_candidate_count": 0,
                    "global_solution_count": 0,
                    "first_global_solution": None,
                }
            )
            continue
        total_search_space += local_search_space
        class_choice_lists = []
        for point_class in active_classes:
            point_ids = list(point_class["point_ids"])
            class_choices = []
            for permuted_point_ids in permutations(point_ids):
                target_unknown_permutations = [
                    list(permutations(point_unknowns[target_point_id]))
                    for target_point_id in permuted_point_ids
                ]
                for permuted_unknown_lists in product(*target_unknown_permutations):
                    point_id_mapping = {
                        source_point_id: target_point_id
                        for source_point_id, target_point_id in zip(point_ids, permuted_point_ids)
                    }
                    class_relabel = {}
                    for source_point_id, permuted_unknowns in zip(point_ids, permuted_unknown_lists):
                        class_relabel[source_point_id] = {
                            source_unknown: target_unknown
                            for source_unknown, target_unknown in zip(
                                point_unknowns[source_point_id],
                                permuted_unknowns,
                            )
                        }
                    class_choices.append(
                        {
                            "point_class_id": point_class["point_class_id"],
                            "point_id_mapping": point_id_mapping,
                            "class_relabel": class_relabel,
                            "permuted_point_ids": list(permuted_point_ids),
                        }
                    )
            class_choice_lists.append(class_choices)
        branch_solutions: list[dict[str, Any]] = []
        for class_choices in product(*class_choice_lists) if class_choice_lists else [()]:
            searched_candidate_count += 1
            combined_relabel = {
                endpoint_id: dict(mapping)
                for endpoint_id, mapping in local_solution["endpoint_relabel"].items()
            }
            compensation_relabel: dict[str, dict[str, str]] = {}
            point_id_mapping: dict[str, str] = {}
            for class_choice in class_choices:
                point_id_mapping.update(class_choice["point_id_mapping"])
                compensation_relabel.update(class_choice["class_relabel"])
            combined_relabel.update(compensation_relabel)
            column_map = _build_endpoint_column_map(unknown_ordering, combined_relabel)
            relabeled_candidate_signature = _rref_signature(
                _apply_column_permutation(candidate_record["global_matrix_rows"], column_map)
            )
            if relabeled_candidate_signature != reference_signature:
                continue
            preserved_path_status = []
            preserves_full_shell = True
            for record in preserved_records:
                relabeled_signature = _rref_signature(
                    _apply_column_permutation(record["global_matrix_rows"], column_map)
                )
                pair_key = _transport_endpoint_pair(record["endpoint_pair"], point_id_mapping)
                signature_allowed = relabeled_signature in allowed_pair_signatures.get(pair_key, set())
                preserved_path_status.append(
                    {
                        "final_path_id": record["final_path_id"],
                        "path_class_id": record["path_class_id"],
                        "original_endpoint_pair": list(record["endpoint_pair"]),
                        "transported_endpoint_pair": list(pair_key),
                        "signature_allowed": signature_allowed,
                    }
                )
                if not signature_allowed:
                    preserves_full_shell = False
            if not preserves_full_shell:
                continue
            solution = {
                "endpoint_relabel": combined_relabel,
                "local_endpoint_relabel": local_solution["endpoint_relabel"],
                "compensation_point_relabel": compensation_relabel,
                "point_id_mapping": point_id_mapping,
                "broken_selected_path_ids_from_local_anchor": broken_path_ids,
                "compensation_points": sorted(compensation_relabel),
                "preserved_path_status": preserved_path_status,
                "preserves_full_shell": True,
            }
            branch_solutions.append(solution)
            global_solutions.append(solution)
        local_solution_searches.append(
            {
                "local_solution_index": local_solution_index,
                "search_enabled": True,
                "reason": None,
                "broken_path_ids": broken_path_ids,
                "varying_endpoints": sorted(varying_endpoints),
                "compensation_points": sorted(
                    {
                        point_id
                        for point_class in active_classes
                        for point_id in point_class["point_ids"]
                    }
                ),
                "active_point_shell_equivalence_classes": active_classes,
                "point_permutation_sizes": point_permutation_sizes,
                "search_space_size": local_search_space,
                "searched_candidate_count": local_search_space,
                "global_solution_count": len(branch_solutions),
                "first_global_solution": branch_solutions[0] if branch_solutions else None,
            }
        )
    compensation_points_union = sorted(
        {
            point_id
            for branch in local_solution_searches
            for point_id in branch.get("compensation_points", [])
        }
    )
    point_permutation_sizes_union: dict[str, int] = {}
    for branch in local_solution_searches:
        for point_id, size in branch.get("point_permutation_sizes", {}).items():
            point_permutation_sizes_union[point_id] = int(size)
    return {
        "searched": any(branch.get("search_enabled") for branch in local_solution_searches),
        "reason": None if local_solution_searches else "no local search branches available",
        "point_id_permutations_enabled": True,
        "point_shell_equivalence_classes": [
            {
                **point_class,
                "point_metadata": [point_metadata[point_id] for point_id in point_class["point_ids"]],
            }
            for point_class in all_equivalence_classes
        ],
        "local_solution_count": len(local_solutions),
        "local_solution_search_space": int(local_relabel_search.get("search_space_size") or 0),
        "search_space_size": total_search_space,
        "searched_candidate_count": searched_candidate_count,
        "compensation_points": compensation_points_union,
        "point_permutation_sizes": point_permutation_sizes_union,
        "local_solution_searches": local_solution_searches,
        "global_solution_count": len(global_solutions),
        "first_global_solution": global_solutions[0] if global_solutions else None,
        "all_global_solutions": global_solutions,
    }


def build_full_shell_automorphism_search_report(reduction: dict[str, Any]) -> dict[str, Any]:
    selected_classes = [
        payload
        for payload in reduction.get("path_classes", [])
        if payload["selected_as_final"] and payload["endpoint_pair"] == ["P1", "P5"]
    ]
    selected_classes.sort(key=lambda payload: (payload["selection_stage"], payload["path_class_id"]))
    if len(selected_classes) != 2:
        return {
            "endpoint_pair": ["P1", "P5"],
            "status": "not_applicable",
            "reason": f"expected exactly two selected P1-P5 path classes, found {len(selected_classes)}",
        }

    reference_payload, candidate_payload = selected_classes
    reference_record = reference_payload["candidate_records"][0]
    candidate_record = candidate_payload["candidate_records"][0]
    preserved_records = [
        kept
        for kept in reduction.get("kept_paths", [])
        if kept["path_class_id"] != candidate_payload["path_class_id"]
    ]
    local_relabel_search = _endpoint_relabel_search(reference_record, candidate_record, preserved_records)
    full_shell_search = _global_shell_automorphism_search(
        reduction,
        reference_record,
        candidate_record,
        preserved_records,
        local_relabel_search,
        allowed_pair_signatures=_selected_pair_signature_sets(reduction),
    )
    return {
        "endpoint_pair": ["P1", "P5"],
        "reference_path_class_id": reference_payload["path_class_id"],
        "reference_source_line_id": reference_payload["representative_source_line_id"],
        "candidate_path_class_id": candidate_payload["path_class_id"],
        "candidate_source_line_id": candidate_payload["representative_source_line_id"],
        "point_id_permutations_enabled": bool(full_shell_search.get("point_id_permutations_enabled")),
        "search_variables_cover_points": sorted(
            {
                point_id
                for point_id in full_shell_search.get("compensation_points", [])
                if point_id is not None
            }
            | set(local_relabel_search.get("varying_rep_ids_by_endpoint", {}))
        ),
        "point_shell_equivalence_classes": full_shell_search.get("point_shell_equivalence_classes", []),
        "local_relabel_search": local_relabel_search,
        "full_shell_search": full_shell_search,
        "global_solution_found": full_shell_search.get("global_solution_count", 0) > 0,
    }


def build_full_shell_automorphism_search_markdown(report: dict[str, Any]) -> str:
    if report.get("status") == "not_applicable":
        return "\n".join(
            [
                "# Full-Shell Automorphism Search Report",
                "",
                f"- Status: `{report['status']}`.",
                f"- Reason: {report['reason']}",
            ]
        )
    full_shell = report["full_shell_search"]
    local_search = report["local_relabel_search"]
    lines = [
        "# Full-Shell Automorphism Search Report",
        "",
        f"- Endpoint pair under resolution: `{report['endpoint_pair']}`.",
        f"- Reference class/source: `{report['reference_path_class_id']}` / `{report['reference_source_line_id']}`.",
        f"- Candidate class/source: `{report['candidate_path_class_id']}` / `{report['candidate_source_line_id']}`.",
        f"- Point-ID permutations enabled: `{report['point_id_permutations_enabled']}`.",
        f"- Local relabel search space / solution count: `{local_search.get('search_space_size')}` / `{local_search.get('local_solution_count')}`.",
        f"- Full-shell search variables cover points: `{report['search_variables_cover_points']}`.",
        f"- Full-shell compensation points: `{full_shell.get('compensation_points')}`.",
        f"- Point permutation sizes: `{full_shell.get('point_permutation_sizes')}`.",
        f"- Full-shell search space size: `{full_shell.get('search_space_size')}`.",
        f"- Global solution count: `{full_shell.get('global_solution_count')}`.",
        f"- First global solution: `{full_shell.get('first_global_solution')}`.",
        f"- Global automorphism witness found: `{report['global_solution_found']}`.",
        "",
        "## Point-Shell Equivalence Classes",
        "",
    ]
    for point_class in report.get("point_shell_equivalence_classes", []):
        lines.append(
            "- "
            + f"`{point_class['point_class_id']}`: points = `{point_class['point_ids']}`, "
            + f"signature = `{point_class['signature']}`, search_enabled = `{point_class['search_enabled']}`."
        )
    lines.extend(
        [
            "",
        "## Branch Searches",
        "",
        ]
    )
    for branch in full_shell.get("local_solution_searches", []):
        lines.append(
            "- "
            + f"local branch `{branch['local_solution_index']}`: enabled = `{branch['search_enabled']}`, "
            + f"broken paths = `{branch['broken_path_ids']}`, compensation points = `{branch['compensation_points']}`, "
            + f"search space = `{branch['search_space_size']}`, global solutions = `{branch['global_solution_count']}`, "
            + f"reason = `{branch['reason']}`"
        )
    return "\n".join(lines)


def build_full_point_shell_automorphism_search_report(reduction: dict[str, Any]) -> dict[str, Any]:
    return build_full_shell_automorphism_search_report(reduction)


def build_full_point_shell_automorphism_search_markdown(report: dict[str, Any]) -> str:
    return build_full_shell_automorphism_search_markdown(report)


def build_p1_p5_doubleclass_resolution_report(reduction: dict[str, Any]) -> dict[str, Any]:
    selected_classes = [
        payload
        for payload in reduction.get("path_classes", [])
        if payload["selected_as_final"] and payload["endpoint_pair"] == ["P1", "P5"]
    ]
    selected_classes.sort(key=lambda payload: (payload["selection_stage"], payload["path_class_id"]))
    if len(selected_classes) != 2:
        return {
            "endpoint_pair": ["P1", "P5"],
            "status": "not_applicable",
            "reason": f"expected exactly two selected P1-P5 path classes, found {len(selected_classes)}",
        }

    reference_payload, candidate_payload = selected_classes
    reference_record = reference_payload["candidate_records"][0]
    candidate_record = candidate_payload["candidate_records"][0]
    preserved_records = [
        kept
        for kept in reduction.get("kept_paths", [])
        if kept["path_class_id"] != candidate_payload["path_class_id"]
    ]
    relabel_search = _endpoint_relabel_search(reference_record, candidate_record, preserved_records)
    full_shell_report = build_full_shell_automorphism_search_report(reduction)
    local_solution = relabel_search["local_solutions"][0] if relabel_search["local_solutions"] else None
    shell_preserving_solution = (
        relabel_search["shell_preserving_solutions"][0]
        if relabel_search["shell_preserving_solutions"]
        else None
    )
    global_solution_count = int(full_shell_report.get("full_shell_search", {}).get("global_solution_count", 0))
    if global_solution_count > 0:
        resolution_status = "globally_automorphism_equivalent"
        resolution_reason = (
            "A full-shell automorphism witness exists: the augmentation class can be mapped "
            "into the skeleton class while the entire selected shell stays inside the allowed "
            "endpoint-pair row-language classes."
        )
    else:
        resolution_status = "both_retained_honest_8_path"
        if relabel_search["local_solution_count"] > 0:
            resolution_reason = (
                "A local P1/P5 endpoint relabel can map the augmentation class into the skeleton "
                "class, but no full-shell automorphism witness extends that relabel across the "
                "rest of the selected shell. The class split is therefore not globally collapsible "
                "on the published shell."
            )
        else:
            resolution_reason = (
                "No endpoint-side relabel maps the augmentation class into the skeleton class, "
                "so the two P1-P5 classes are genuinely distinct even before global-shell checks."
            )
    return {
        "endpoint_pair": ["P1", "P5"],
        "reference_path_class_id": reference_payload["path_class_id"],
        "reference_source_line_id": reference_payload["representative_source_line_id"],
        "candidate_path_class_id": candidate_payload["path_class_id"],
        "candidate_source_line_id": candidate_payload["representative_source_line_id"],
        "point_id_permutations_enabled": bool(full_shell_report.get("point_id_permutations_enabled")),
        "line_group_signature_equal": (
            reference_payload["line_group_signature"] == candidate_payload["line_group_signature"]
        ),
        "local_row_space_signature_equal": (
            reference_payload["local_row_space_signature"] == candidate_payload["local_row_space_signature"]
        ),
        "global_row_space_signature_equal": (
            reference_payload["global_row_space_signature"] == candidate_payload["global_row_space_signature"]
        ),
        "endpoint_decomposition_signature_equal": (
            reference_payload["endpoint_decomposition_signature"]
            == candidate_payload["endpoint_decomposition_signature"]
        ),
        "local_relabel_search": relabel_search,
        "full_shell_automorphism_search": full_shell_report.get("full_shell_search"),
        "first_local_solution": local_solution,
        "first_shell_preserving_solution": shell_preserving_solution,
        "first_global_shell_solution": full_shell_report.get("full_shell_search", {}).get("first_global_solution"),
        "selected_shell_preservation_checked_against_path_ids": [
            record["final_path_id"] for record in preserved_records
        ],
        "resolution_status": resolution_status,
        "resolution_reason": resolution_reason,
    }


def build_p1_p5_doubleclass_resolution_markdown(report: dict[str, Any]) -> str:
    if report.get("status") == "not_applicable":
        return "\n".join(
            [
                "# P1-P5 Double-Class Resolution Report",
                "",
                f"- Status: `{report['status']}`.",
                f"- Reason: {report['reason']}",
            ]
        )
    local_search = report["local_relabel_search"]
    return "\n".join(
        [
            "# P1-P5 Double-Class Resolution Report",
            "",
            f"- Reference class/source: `{report['reference_path_class_id']}` / `{report['reference_source_line_id']}`.",
            f"- Candidate class/source: `{report['candidate_path_class_id']}` / `{report['candidate_source_line_id']}`.",
            f"- Point-ID permutations enabled in the full-shell search: `{report['point_id_permutations_enabled']}`.",
            f"- Line-group signatures equal: `{report['line_group_signature_equal']}`.",
            f"- Local row-space signatures equal: `{report['local_row_space_signature_equal']}`.",
            f"- Global row-space signatures equal: `{report['global_row_space_signature_equal']}`.",
            f"- Endpoint decomposition signatures equal: `{report['endpoint_decomposition_signature_equal']}`.",
            f"- Exhaustive local relabel search executed: `{local_search['searched']}`.",
            f"- Varying rep ids by endpoint: `{local_search['varying_rep_ids_by_endpoint']}`.",
            f"- Local solution count: `{local_search['local_solution_count']}`.",
            f"- Shell-preserving solution count: `{local_search['shell_preserving_solution_count']}`.",
            f"- Full-shell automorphism search summary: `{report.get('full_shell_automorphism_search')}`.",
            f"- First local solution: `{report['first_local_solution']}`.",
            f"- First shell-preserving solution: `{report['first_shell_preserving_solution']}`.",
            f"- First global shell solution: `{report.get('first_global_shell_solution')}`.",
            f"- Selected-shell preservation was checked against: `{report['selected_shell_preservation_checked_against_path_ids']}`.",
            f"- Resolution status: `{report['resolution_status']}`.",
            f"- Resolution reason: {report['resolution_reason']}",
        ]
    )


def build_final_bs_strong_equivalence_report(
    reduction: dict[str, Any],
    publication_shell: dict[str, Any],
    publication_check: dict[str, Any],
    published_line_full: dict[str, Any],
    published_bs_analysis: dict[str, Any],
    internal_bs_analysis: dict[str, Any],
) -> dict[str, Any]:
    unknown_ordering = list(published_line_full["global_unknown_ordering"])
    has_auxiliary_unknowns = any(token.startswith("S") and "_R" in token for token in unknown_ordering)
    row_language_full_span_pass = (
        reduction["selected_rows_span_full_candidate_row_language"]
        and reduction["selected_row_rank"] == reduction["target_row_rank"]
    )
    bilbao_equivalent_final_object_pass = (
        publication_check["point_ids_match"]
        and publication_check["point_count_match"]
        and publication_check["path_count_match"]
        and publication_check["path_pair_set_match"]
        and not has_auxiliary_unknowns
    )
    return {
        "internal_selection_algorithm": (
            reduction.get(
                "selection_policy",
                "canonical endpoint-pair skeleton plus deterministic full-span augmentation",
            )
        ),
        "candidate_path_count": reduction["raw_counts"]["candidate_path_count"],
        "internal_candidate_path_class_count": reduction["path_class_count"],
        "internal_selected_path_count": len(reduction["kept_paths"]),
        "internal_selected_point_count": len(reduction["final_point_ids"]),
        "endpoint_pair_skeleton_path_class_ids": list(reduction.get("endpoint_pair_skeleton_path_class_ids", [])),
        "endpoint_pair_skeleton_row_rank": int(reduction.get("endpoint_pair_skeleton_row_rank", 0)),
        "selection_augmentation_path_class_ids": list(reduction.get("selection_augmentation_path_class_ids", [])),
        "target_row_rank": reduction["target_row_rank"],
        "selected_row_rank": reduction["selected_row_rank"],
        "selected_rows_span_full_candidate_row_language": reduction[
            "selected_rows_span_full_candidate_row_language"
        ],
        "target_unique_endpoint_pair_count": int(reduction["target_unique_endpoint_pair_count"]),
        "selected_unique_endpoint_pair_count": len({tuple(segment["endpoint_pair"]) for segment in reduction["kept_paths"]}),
        "selected_unique_endpoint_pairs": list(reduction.get("selected_unique_endpoint_pairs", [])),
        "internal_selected_final_path_ids": [segment["final_path_id"] for segment in reduction["kept_paths"]],
        "internal_selected_source_line_ids": [segment["source_line_id"] for segment in reduction["kept_paths"]],
        "publication_path_count": len(publication_shell["publication_paths"]),
        "publication_point_count": len(publication_shell["publication_point_ids"]),
        "publication_path_ids": [path["publication_path_id"] for path in publication_shell["publication_paths"]],
        "publication_member_source_line_ids": [list(path["member_source_line_ids"]) for path in publication_shell["publication_paths"]],
        "publication_unknown_count": len(unknown_ordering),
        "published_unknown_ordering": unknown_ordering,
        "published_has_auxiliary_unknowns": has_auxiliary_unknowns,
        "internal_bs_matrix_shape": list(internal_bs_analysis["matrix_shape"]),
        "internal_bs_rank": int(internal_bs_analysis["rank"]),
        "internal_bs_nullity": int(internal_bs_analysis["nullity"]),
        "publication_bs_matrix_shape": list(published_bs_analysis["matrix_shape"]),
        "publication_bs_rank": int(published_bs_analysis["rank"]),
        "publication_bs_nullity": int(published_bs_analysis["nullity"]),
        "actual_path_pairs": list(publication_check["actual_path_pairs"]),
        "expected_path_pairs": list(publication_check["expected_path_pairs"]),
        "path_count_match": bool(publication_check["path_count_match"]),
        "path_pair_set_match": bool(publication_check["path_pair_set_match"]),
        "row_language_full_span_pass": row_language_full_span_pass,
        "bilbao_equivalent_final_object_pass": bilbao_equivalent_final_object_pass,
        "bs_strong_equivalence_pass": bilbao_equivalent_final_object_pass,
        "bs_strong_equivalence_semantics": "publication_object_semantics_only",
    }


def build_final_bs_strong_equivalence_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Final BS Strong Equivalence Report",
            "",
            f"- Internal selection algorithm: {report['internal_selection_algorithm']}.",
            f"- Candidate paths / internal path classes: `{report['candidate_path_count']}` / `{report['internal_candidate_path_class_count']}`.",
            f"- Internal honest points / paths: `{report['internal_selected_point_count']}` / `{report['internal_selected_path_count']}`.",
            f"- Publication points / paths: `{report['publication_point_count']}` / `{report['publication_path_count']}`.",
            f"- Endpoint-pair skeleton path classes / rank: `{report['endpoint_pair_skeleton_path_class_ids']}` / `{report['endpoint_pair_skeleton_row_rank']}`.",
            f"- Full-span augmentation path classes: `{report['selection_augmentation_path_class_ids']}`.",
            f"- Target row rank: `{report['target_row_rank']}`.",
            f"- Selected row rank: `{report['selected_row_rank']}`.",
            f"- Selected rows span full candidate row language: `{report['selected_rows_span_full_candidate_row_language']}`.",
            f"- Selected unique endpoint pairs / target unique endpoint pairs: `{report['selected_unique_endpoint_pair_count']}` / `{report['target_unique_endpoint_pair_count']}`.",
            f"- Actual path pairs: `{report['actual_path_pairs']}`.",
            f"- Expected path pairs: `{report['expected_path_pairs']}`.",
            f"- Path count match: `{report['path_count_match']}`.",
            f"- Path pair set match: `{report['path_pair_set_match']}`.",
            f"- Published unknown count: `{report['publication_unknown_count']}`.",
            f"- Published object has auxiliary `S*_R*` unknowns: `{report['published_has_auxiliary_unknowns']}`.",
            f"- Internal BS shape/rank/nullity: `{report['internal_bs_matrix_shape']}` / `{report['internal_bs_rank']}` / `{report['internal_bs_nullity']}`.",
            f"- Publication BS shape/rank/nullity: `{report['publication_bs_matrix_shape']}` / `{report['publication_bs_rank']}` / `{report['publication_bs_nullity']}`.",
            f"- Internal selected final path ids: `{report['internal_selected_final_path_ids']}`.",
            f"- Publication path ids: `{report['publication_path_ids']}`.",
            f"- Row-language full-span pass: `{report['row_language_full_span_pass']}`.",
            f"- Bilbao-equivalent final-object pass: `{report['bilbao_equivalent_final_object_pass']}`.",
            f"- Strong-equivalence pass (`publication_object_semantics_only`): `{report['bs_strong_equivalence_pass']}`.",
        ]
    )


def build_missing_row_language_witness_report(
    reduction: dict[str, Any],
) -> dict[str, Any]:
    path_classes = {
        payload["path_class_id"]: payload
        for payload in reduction.get("path_classes", [])
    }
    pair_skeleton_ids = list(reduction.get("endpoint_pair_skeleton_path_class_ids", []))
    augmentation_ids = list(reduction.get("selection_augmentation_path_class_ids", []))
    pair_skeleton_records = [
        path_classes[path_class_id]["candidate_records"][0]
        for path_class_id in pair_skeleton_ids
    ]
    target_records = [
        payload["candidate_records"][0]
        for payload in reduction.get("path_classes", [])
    ]
    pair_skeleton_rows = _stack_rows(pair_skeleton_records)
    target_rows = _stack_rows(target_records)
    witness_entries = []
    running_rows = list(pair_skeleton_rows)
    for augmentation_order, path_class_id in enumerate(augmentation_ids, start=1):
        payload = path_classes[path_class_id]
        representative = payload["candidate_records"][0]
        row_index, row_record, rank_before, rank_after = _first_rank_gaining_row_record(
            running_rows,
            representative.get("global_matrix_row_records", []),
        )
        witness_entries.append(
            {
                "augmentation_order": augmentation_order,
                "path_class_id": path_class_id,
                "source_line_id": payload["representative_source_line_id"],
                "candidate_id": payload["representative_candidate_id"],
                "endpoint_pair": list(payload["endpoint_pair"]),
                "basis_id": None if row_record is None else row_record["basis_id"],
                "row_kind": None if row_record is None else row_record["row_kind"],
                "row_index_within_candidate_block": row_index,
                "rank_before": rank_before,
                "rank_after": rank_after,
                "witness_row": None if row_record is None else list(row_record["matrix_row"]),
                "witness_in_previous_span": row_record is None,
            }
        )
        running_rows.extend(representative["global_matrix_rows"])
    return {
        "baseline_selection_kind": "canonical_endpoint_pair_skeleton",
        "baseline_selected_path_class_ids": pair_skeleton_ids,
        "baseline_selected_row_rank": int(reduction.get("endpoint_pair_skeleton_row_rank", 0)),
        "published_selected_path_class_ids": [segment["path_class_id"] for segment in reduction.get("kept_paths", [])],
        "published_selected_row_rank": int(reduction.get("selected_row_rank", 0)),
        "target_row_rank": int(reduction.get("target_row_rank", 0)),
        "missing_rank_before_augmentation": int(reduction.get("target_row_rank", 0)) - int(
            reduction.get("endpoint_pair_skeleton_row_rank", 0)
        ),
        "augmentation_path_class_ids": augmentation_ids,
        "augmentation_witnesses": witness_entries,
        "baseline_rref_basis_rows": _rref_basis_rows(pair_skeleton_rows),
        "published_rref_basis_rows": _rref_basis_rows(_stack_rows(reduction.get("kept_paths", []))),
        "target_rref_basis_rows": _rref_basis_rows(target_rows),
        "published_selection_resolves_gap": bool(reduction.get("selected_rows_span_full_candidate_row_language")),
    }


def build_missing_row_language_witness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Missing Row-Language Witness Report",
        "",
        f"- Baseline selection kind: `{report['baseline_selection_kind']}`.",
        f"- Baseline selected path classes: `{report['baseline_selected_path_class_ids']}`.",
        f"- Baseline selected row rank: `{report['baseline_selected_row_rank']}`.",
        f"- Target row rank: `{report['target_row_rank']}`.",
        f"- Missing rank before augmentation: `{report['missing_rank_before_augmentation']}`.",
        f"- Augmentation path classes: `{report['augmentation_path_class_ids']}`.",
        f"- Published selection resolves the gap: `{report['published_selection_resolves_gap']}`.",
        "",
    ]
    for witness in report["augmentation_witnesses"]:
        lines.extend(
            [
                f"## {witness['path_class_id']}",
                "",
                f"- Source line id: `{witness['source_line_id']}`.",
                f"- Endpoint pair: `{witness['endpoint_pair']}`.",
                f"- Candidate id: `{witness['candidate_id']}`.",
                f"- Witness basis id / row kind / row index: `{witness['basis_id']}` / `{witness['row_kind']}` / `{witness['row_index_within_candidate_block']}`.",
                f"- Rank before / after adding the witness row: `{witness['rank_before']}` / `{witness['rank_after']}`.",
                f"- Witness row already in previous span: `{witness['witness_in_previous_span']}`.",
                f"- Witness row: `{witness['witness_row']}`.",
                "",
            ]
        )
    return "\n".join(lines)
