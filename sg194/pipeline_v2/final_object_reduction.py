from __future__ import annotations

from fractions import Fraction
from itertools import combinations, permutations, product
from typing import Any, Iterable, Sequence

import sympy as sp
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
        record["path_type_key"] = (
            tuple(record["endpoint_pair"]),
            _line_group_signature_key(record["line_group_signature"]),
            _endpoint_decomposition_signature_key(block),
            tuple(tuple(row) for row in local_signature["rref_basis_rows"]),
            tuple(tuple(row) for row in global_signature["rref_basis_rows"]),
            _phase_aware_refinement_key(block.get("phase_aware_refinement", {})),
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
        class_record["representative"]["path_class_id"] = path_class_id
        class_record["representative"]["path_class_candidate_count"] = len(class_record["candidate_records"])

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


def build_reduction_report_markdown(reduction: dict[str, Any]) -> str:
    lines = [
        "# Automatic Final Object Reduction Report",
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


def build_expected_check_markdown(check: dict[str, Any]) -> str:
    lines = [
        "# Final Object vs Bilbao-Equivalent Sanity Check",
        "",
        f"- Point count match: `{check['point_count_match']}`.",
        f"- Point id order match: `{check['point_ids_match']}`.",
        f"- Path count match: `{check['path_count_match']}`.",
        f"- Path pair set match: `{check['path_pair_set_match']}`.",
        f"- Unique path pair set match: `{check['unique_path_pair_set_match']}`.",
        f"- Bilbao-equivalent final-object pass: `{check['bilbao_equivalent_final_object_pass']}`.",
        "",
        "## Actual",
        "",
        f"- Final point ids: `{check['actual_point_ids']}`.",
        f"- Final path endpoint pairs: `{check['actual_path_pairs']}`.",
        f"- Final unique endpoint-pair set: `{check['actual_unique_path_pairs']}`.",
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


def _global_shell_automorphism_search(
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
    for local_solution_index, local_solution in enumerate(local_solutions, start=1):
        varying_endpoints = set(local_solution["endpoint_relabel"])
        broken_path_ids = list(local_solution["broken_selected_path_ids"])
        compensation_points = sorted(
            {
                point_id
                for record in preserved_records
                if record["final_path_id"] in broken_path_ids
                for point_id in record["endpoint_ids"]
                if point_id not in varying_endpoints
            }
        )
        permutation_lists: dict[str, list[tuple[str, ...]]] = {}
        point_permutation_sizes: dict[str, int] = {}
        local_search_space = 1
        oversized_point = None
        for point_id in compensation_points:
            unknowns = point_unknowns.get(point_id, [])
            if len(unknowns) > 7:
                oversized_point = point_id
                break
            permutations_for_point = list(permutations(unknowns))
            permutation_lists[point_id] = permutations_for_point
            point_permutation_sizes[point_id] = len(permutations_for_point)
            local_search_space *= max(1, len(permutations_for_point))
        if oversized_point is not None:
            local_solution_searches.append(
                {
                    "local_solution_index": local_solution_index,
                    "search_enabled": False,
                    "reason": (
                        f"point {oversized_point} has {len(point_unknowns.get(oversized_point, []))} unknowns; "
                        "full-shell compensation permutation search disabled"
                    ),
                    "broken_path_ids": broken_path_ids,
                    "varying_endpoints": sorted(varying_endpoints),
                    "compensation_points": compensation_points,
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
                        f"next local branch requires {local_search_space} permutations"
                    ),
                    "broken_path_ids": broken_path_ids,
                    "varying_endpoints": sorted(varying_endpoints),
                    "compensation_points": compensation_points,
                    "point_permutation_sizes": point_permutation_sizes,
                    "search_space_size": local_search_space,
                    "searched_candidate_count": 0,
                    "global_solution_count": 0,
                    "first_global_solution": None,
                }
            )
            continue
        total_search_space += local_search_space
        point_choices = [
            [(point_id, permuted_unknowns) for permuted_unknowns in permutation_lists[point_id]]
            for point_id in compensation_points
        ]
        branch_solutions: list[dict[str, Any]] = []
        for compensation_choice in product(*point_choices) if point_choices else [()]:
            searched_candidate_count += 1
            combined_relabel = {
                endpoint_id: dict(mapping)
                for endpoint_id, mapping in local_solution["endpoint_relabel"].items()
            }
            compensation_relabel: dict[str, dict[str, str]] = {}
            for point_id, permuted_unknowns in compensation_choice:
                source_unknowns = point_unknowns[point_id]
                compensation_relabel[point_id] = {
                    source_unknown: target_unknown
                    for source_unknown, target_unknown in zip(source_unknowns, permuted_unknowns)
                }
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
                pair_key = tuple(record["endpoint_pair"])
                signature_allowed = relabeled_signature in allowed_pair_signatures.get(pair_key, set())
                preserved_path_status.append(
                    {
                        "final_path_id": record["final_path_id"],
                        "path_class_id": record["path_class_id"],
                        "endpoint_pair": list(pair_key),
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
                "broken_selected_path_ids_from_local_anchor": broken_path_ids,
                "compensation_points": compensation_points,
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
                "compensation_points": compensation_points,
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
        "search_variables_cover_points": sorted(
            {
                point_id
                for point_id in full_shell_search.get("compensation_points", [])
                if point_id is not None
            }
            | set(local_relabel_search.get("varying_rep_ids_by_endpoint", {}))
        ),
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
        f"- Local relabel search space / solution count: `{local_search.get('search_space_size')}` / `{local_search.get('local_solution_count')}`.",
        f"- Full-shell search variables cover points: `{report['search_variables_cover_points']}`.",
        f"- Full-shell compensation points: `{full_shell.get('compensation_points')}`.",
        f"- Point permutation sizes: `{full_shell.get('point_permutation_sizes')}`.",
        f"- Full-shell search space size: `{full_shell.get('search_space_size')}`.",
        f"- Global solution count: `{full_shell.get('global_solution_count')}`.",
        f"- First global solution: `{full_shell.get('first_global_solution')}`.",
        f"- Global automorphism witness found: `{report['global_solution_found']}`.",
        "",
        "## Branch Searches",
        "",
    ]
    for branch in full_shell.get("local_solution_searches", []):
        lines.append(
            "- "
            + f"local branch `{branch['local_solution_index']}`: enabled = `{branch['search_enabled']}`, "
            + f"broken paths = `{branch['broken_path_ids']}`, compensation points = `{branch['compensation_points']}`, "
            + f"search space = `{branch['search_space_size']}`, global solutions = `{branch['global_solution_count']}`, "
            + f"reason = `{branch['reason']}`"
        )
    return "\n".join(lines)


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
    sanity_check: dict[str, Any],
    published_line_full: dict[str, Any],
    published_bs_analysis: dict[str, Any],
) -> dict[str, Any]:
    unknown_ordering = list(published_line_full["global_unknown_ordering"])
    has_auxiliary_unknowns = any(token.startswith("S") and "_R" in token for token in unknown_ordering)
    selected_source_line_ids = [segment["source_line_id"] for segment in reduction["kept_paths"]]
    expected_source_line_ids = list(reduction["listed_source_line_ids"])
    source_line_family_match = sorted(selected_source_line_ids) == sorted(expected_source_line_ids)
    selected_unique_endpoint_pair_count = len({tuple(segment["endpoint_pair"]) for segment in reduction["kept_paths"]})
    target_unique_endpoint_pair_count = int(reduction["target_unique_endpoint_pair_count"])
    row_language_full_span_pass = (
        reduction["selected_rows_span_full_candidate_row_language"]
        and reduction["selected_row_rank"] == reduction["target_row_rank"]
        and not has_auxiliary_unknowns
    )
    bilbao_equivalent_final_object_pass = (
        row_language_full_span_pass
        and sanity_check["point_ids_match"]
        and sanity_check["point_count_match"]
        and sanity_check["path_count_match"]
        and sanity_check["path_pair_set_match"]
    )
    return {
        "selection_algorithm": (
            reduction.get(
                "selection_policy",
                "canonical endpoint-pair skeleton plus deterministic full-span augmentation",
            )
        ),
        "candidate_path_count": reduction["raw_counts"]["candidate_path_count"],
        "candidate_path_class_count": reduction["path_class_count"],
        "selected_path_count": len(reduction["kept_paths"]),
        "selected_point_count": len(reduction["final_point_ids"]),
        "endpoint_pair_skeleton_path_class_ids": list(reduction.get("endpoint_pair_skeleton_path_class_ids", [])),
        "endpoint_pair_skeleton_row_rank": int(reduction.get("endpoint_pair_skeleton_row_rank", 0)),
        "selection_augmentation_path_class_ids": list(reduction.get("selection_augmentation_path_class_ids", [])),
        "target_row_rank": reduction["target_row_rank"],
        "selected_row_rank": reduction["selected_row_rank"],
        "selected_rows_span_full_candidate_row_language": reduction[
            "selected_rows_span_full_candidate_row_language"
        ],
        "target_unique_endpoint_pair_count": target_unique_endpoint_pair_count,
        "selected_unique_endpoint_pair_count": selected_unique_endpoint_pair_count,
        "selected_unique_endpoint_pairs": list(reduction.get("selected_unique_endpoint_pairs", [])),
        "expected_source_line_ids": expected_source_line_ids,
        "selected_source_line_ids_match_intrinsic_line_families": source_line_family_match,
        "published_unknown_count": len(unknown_ordering),
        "published_unknown_ordering": unknown_ordering,
        "published_has_auxiliary_unknowns": has_auxiliary_unknowns,
        "published_bs_matrix_shape": list(published_bs_analysis["matrix_shape"]),
        "published_bs_rank": int(published_bs_analysis["rank"]),
        "published_bs_nullity": int(published_bs_analysis["nullity"]),
        "selected_final_path_ids": [segment["final_path_id"] for segment in reduction["kept_paths"]],
        "selected_final_source_line_ids": selected_source_line_ids,
        "actual_path_pairs": list(sanity_check["actual_path_pairs"]),
        "expected_path_pairs": list(sanity_check["expected_path_pairs"]),
        "path_count_match": bool(sanity_check["path_count_match"]),
        "path_pair_set_match": bool(sanity_check["path_pair_set_match"]),
        "unique_path_pair_set_match": bool(sanity_check["unique_path_pair_set_match"]),
        "row_language_full_span_pass": row_language_full_span_pass,
        "bilbao_equivalent_final_object_pass": bilbao_equivalent_final_object_pass,
        "bs_strong_equivalence_pass": row_language_full_span_pass,
        "bs_strong_equivalence_semantics": "deprecated_alias_row_language_full_span_only",
    }


def build_final_bs_strong_equivalence_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Final BS Strong Equivalence Report",
            "",
            f"- Selection algorithm: {report['selection_algorithm']}.",
            f"- Candidate paths / path classes: `{report['candidate_path_count']}` / `{report['candidate_path_class_count']}`.",
            f"- Selected final points / paths: `{report['selected_point_count']}` / `{report['selected_path_count']}`.",
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
            f"- Unique path pair set match: `{report['unique_path_pair_set_match']}`.",
            f"- Expected source line ids: `{report['expected_source_line_ids']}`.",
            f"- Selected source line ids match intrinsic line families: `{report['selected_source_line_ids_match_intrinsic_line_families']}`.",
            f"- Published unknown count: `{report['published_unknown_count']}`.",
            f"- Published object has auxiliary `S*_R*` unknowns: `{report['published_has_auxiliary_unknowns']}`.",
            f"- Published BS shape/rank/nullity: `{report['published_bs_matrix_shape']}` / `{report['published_bs_rank']}` / `{report['published_bs_nullity']}`.",
            f"- Selected final path ids: `{report['selected_final_path_ids']}`.",
            f"- Selected source line ids: `{report['selected_final_source_line_ids']}`.",
            f"- Row-language full-span pass: `{report['row_language_full_span_pass']}`.",
            f"- Bilbao-equivalent final-object pass: `{report['bilbao_equivalent_final_object_pass']}`.",
            f"- Backward-compatible strong-equivalence alias (`row_language_full_span_only`): `{report['bs_strong_equivalence_pass']}`.",
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
