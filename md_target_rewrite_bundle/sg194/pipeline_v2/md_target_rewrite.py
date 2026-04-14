from __future__ import annotations

import datetime as dt
from functools import lru_cache
from fractions import Fraction
from itertools import product
from typing import Any

import sympy as sp

try:
    from scipy.optimize import linprog
except Exception:  # pragma: no cover - optional runtime dependency
    linprog = None

from . import runtime_backend_free


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def stage1_backend():
    return runtime_backend_free


@lru_cache(maxsize=1)
def ssgreps_module():
    return runtime_backend_free.load_ssgreps_module()


@lru_cache(maxsize=None)
def _build_md_geometry_bundle(group_id: str) -> dict[str, Any]:
    port = stage1_backend()
    grouped = port.pick_group_entries(group_id)
    lines = grouped["lines"]
    planes = grouped["planes"]
    ctx = port.load_reciprocal_context(group_id)
    line_orbit_to_id, plane_orbit_to_id = port.subspace_orbit_id_maps(lines, planes, ctx)
    port.annotate_special_manifolds(lines, planes, ctx, line_orbit_to_id, plane_orbit_to_id)
    kgeom = {
        "grouped": grouped,
        "runtime_ctx": ctx,
        "line_orbit_to_id": line_orbit_to_id,
        "plane_orbit_to_id": plane_orbit_to_id,
    }
    return {
        "group_id": group_id,
        "kgeom": kgeom,
        "grouped": grouped,
        "geometry_construction_provenance": {
            "source_module": "common.swyckoff_k",
            "entrypoint": "compute_wyckoff_output(kspace=True, basis='primitive', fast=False)",
            "operation_derived_pipeline": [
                "load_irssg_data",
                "construct_std_ssg_operations",
                "derive_wyckoff",
                "rotation_subgroup_reps_from_point_group",
                "fixed_subspaces_for_subgroup",
                "closure_under_stabilizer",
                "subspace_orbit_key",
                "generic_point_on_subspace",
            ],
        },
    }


def _empty_full_compatibility() -> dict[str, Any]:
    """Return an explicit empty matrix payload.

    The standalone rewrite keeps matrix assembly explicit at every stage.  When a
    connector class is absent we still return a full compatibility payload so the
    downstream projection logic can stay purely matrix-based instead of branching
    on `None`.
    """
    return {
        "global_unknown_ordering": [],
        "global_matrix_rows": [],
        "global_matrix": [],
        "matrix_shape": [0, 0],
        "covered_lines": [],
        "covered_planes": [],
        "compatibility_semantics": "empty_md_target_rewrite_full_compatibility",
    }


def _seed_full_compatibility_with_unknowns(unknowns: list[str]) -> dict[str, Any]:
    """Create a zero-row matrix that already knows the maximal-manifold unknowns.

    This is the md counterpart of a geometry shell with no retained
    intermediate rows.  It matters for cases like `44`, where the md rules can
    legitimately drop the generic connector and leave only the maximal-manifold
    total-band condition.
    """
    return {
        "global_unknown_ordering": list(unknowns),
        "global_matrix_rows": [],
        "global_matrix": [],
        "matrix_shape": [0, len(unknowns)],
        "covered_lines": [],
        "covered_planes": [],
        "compatibility_semantics": "seeded_empty_md_target_rewrite_full_compatibility",
    }


def _global_row_kind_histogram(matrix_payload: dict[str, Any]) -> dict[str, int]:
    """Summarize the row families that survive into one assembled matrix payload."""
    histogram: dict[str, int] = {}
    for row in matrix_payload.get("global_matrix_rows", []):
        row_kind = str(
            row.get("row_kind")
            or (row.get("equation_metadata") or {}).get("row_kind")
            or "unknown"
        )
        histogram[row_kind] = histogram.get(row_kind, 0) + 1
    return dict(sorted(histogram.items()))


def _build_block_matrix_rows_from_equations(
    local_unknown_ordering: list[str],
    equations: list[dict[str, Any]],
) -> list[list[int]]:
    local_index = {
        str(unknown): index
        for index, unknown in enumerate(local_unknown_ordering)
    }
    rows: list[list[int]] = []
    for equation in equations:
        row = [0] * len(local_unknown_ordering)
        for term in equation.get("terms", []):
            row[local_index[str(term["unknown"])]] += int(term["coeff"])
        rows.append(row)
    return rows


def _assemble_line_compatibility(
    line_blocks: list[dict[str, Any]],
    point_ids: list[str],
) -> dict[str, Any]:
    per_point_ids: dict[str, list[str]] = {}
    for block in line_blocks:
        for endpoint_id in block["endpoint_ids"]:
            rep_ids = [item["rep_id"] for item in block["endpoint_decompositions"].get(endpoint_id, [])]
            existing = per_point_ids.get(endpoint_id)
            if existing is None:
                per_point_ids[endpoint_id] = rep_ids
            elif existing != rep_ids:
                raise ValueError(f"inconsistent rep ordering for {endpoint_id}")

    ordering: list[str] = []
    for point_id in point_ids:
        ordering.extend(per_point_ids.get(str(point_id), []))
    for block in line_blocks:
        for unknown in block.get("full_local_unknown_ordering", block.get("local_unknown_ordering", [])):
            unknown = str(unknown)
            if unknown not in ordering:
                ordering.append(unknown)

    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    global_rows: list[dict[str, Any]] = []
    for block in line_blocks:
        equations = list(block.get("full_equations", block.get("equations", [])))
        for row_index, equation in enumerate(equations):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[str(term["unknown"])]] += int(term["coeff"])
            metadata = {key: value for key, value in equation.items() if key != "terms"}
            global_rows.append(
                {
                    "source_type": "line",
                    "line_id": block["line_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "equation_metadata": metadata,
                    **metadata,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": global_rows,
        "global_matrix": [list(row["matrix_row"]) for row in global_rows],
        "matrix_shape": [len(global_rows), len(ordering)],
    }


def _append_plane_blocks_to_compatibility(
    compatibility: dict[str, Any],
    plane_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    ordering = list(compatibility["global_unknown_ordering"])
    for block in plane_blocks:
        for unknown in block["local_unknown_ordering"]:
            if unknown not in ordering:
                ordering.append(str(unknown))
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    width_delta = len(ordering) - len(compatibility["global_unknown_ordering"])
    rows = [
        {**row, "matrix_row": list(row["matrix_row"]) + [0] * width_delta}
        for row in compatibility["global_matrix_rows"]
    ]
    for block in plane_blocks:
        for row_index, equation in enumerate(block["equations"]):
            row = [0] * len(ordering)
            for term in equation["terms"]:
                row[unknown_index[str(term["unknown"])]] += int(term["coeff"])
            metadata = {key: value for key, value in equation.items() if key != "terms"}
            rows.append(
                {
                    "source_type": "plane",
                    "plane_id": block["plane_id"],
                    "basis_id": equation["basis_id"],
                    "row_index_within_source": row_index,
                    "equation_metadata": metadata,
                    **metadata,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": rows,
        "global_matrix": [list(row["matrix_row"]) for row in rows],
        "matrix_shape": [len(rows), len(ordering)],
    }


def _append_generic_blocks_to_compatibility(
    compatibility: dict[str, Any],
    generic_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not generic_blocks:
        return compatibility
    ordering = list(compatibility["global_unknown_ordering"])
    for block in generic_blocks:
        for unknown in block["local_unknown_ordering"]:
            unknown = str(unknown)
            if unknown not in ordering:
                ordering.append(unknown)
    unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
    width_delta = len(ordering) - len(compatibility["global_unknown_ordering"])
    rows = [
        {**row, "matrix_row": list(row["matrix_row"]) + [0] * width_delta}
        for row in compatibility["global_matrix_rows"]
    ]
    for block in generic_blocks:
        local_unknown_ordering = [str(unknown) for unknown in block.get("local_unknown_ordering", [])]
        for row_index, (equation, local_row) in enumerate(zip(block.get("equations", []), block.get("matrix_rows", []))):
            row = [0] * len(ordering)
            for unknown, coeff in zip(local_unknown_ordering, local_row):
                coeff = int(coeff)
                if coeff == 0:
                    continue
                row[unknown_index[unknown]] += coeff
            if not any(row):
                continue
            metadata = {key: value for key, value in equation.items() if key != "terms"}
            rows.append(
                {
                    "source_type": "generic",
                    "basis_id": str(equation.get("basis_id", f"{block['generic_id']}__ROW_{row_index + 1:02d}")),
                    "row_index_within_source": row_index,
                    "equation_metadata": metadata,
                    **metadata,
                    "matrix_row": row,
                }
            )
    return {
        "global_unknown_ordering": ordering,
        "global_matrix_rows": rows,
        "global_matrix": [list(row["matrix_row"]) for row in rows],
        "matrix_shape": [len(rows), len(ordering)],
    }


def _render_equation_records(matrix_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Render sparse row records in terms of the payload's current unknown basis."""
    unknown_ordering = [str(item) for item in matrix_payload.get("global_unknown_ordering", [])]
    rendered: list[dict[str, Any]] = []
    for row in matrix_payload.get("global_matrix_rows", []):
        coeffs = [int(value) for value in row.get("matrix_row", [])]
        terms = [
            {"unknown": unknown_ordering[index], "coeff": coeff}
            for index, coeff in enumerate(coeffs)
            if coeff != 0
        ]
        rendered.append(
            {
                "equation_id": str(row.get("basis_id") or ""),
                "row_kind": str(
                    row.get("row_kind")
                    or (row.get("equation_metadata") or {}).get("row_kind")
                    or "unknown"
                ),
                "terms": terms,
            }
        )
    return rendered


def _render_basis_vectors(kernel_payload: dict[str, Any]) -> list[dict[str, Any]]:
    unknown_ordering = [str(item) for item in kernel_payload.get("unknown_ordering", [])]
    rendered: list[dict[str, Any]] = []
    for basis in kernel_payload.get("basis_vectors", []):
        vector = [int(value) for value in basis.get("vector", [])]
        rendered.append(
            {
                "basis_id": str(basis.get("id") or ""),
                "terms": [
                    {"unknown": unknown_ordering[index], "coeff": coeff}
                    for index, coeff in enumerate(vector)
                    if coeff != 0
                ],
            }
        )
    return rendered


def _render_seitz_operations(runtime_ctx: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for index, op in enumerate(runtime_ctx.get("ops", []), start=1):
        operations.append(
            {
                "op_id": f"g{index:03d}",
                "rotation": [[_frac_str(value) for value in row] for row in op.W],
                "translation": [_frac_str(value) for value in op.t],
            }
        )
    return operations


def _render_point_group_rotations(runtime_ctx: dict[str, Any]) -> list[list[list[str]]]:
    rendered: list[list[list[str]]] = []
    seen: set[tuple[tuple[Fraction, ...], ...]] = set()
    for op in runtime_ctx.get("ops", []):
        rotation = tuple(tuple(_fraction(value) for value in row) for row in op.W)
        if rotation in seen:
            continue
        seen.add(rotation)
        rendered.append([[_frac_str(value) for value in row] for row in rotation])
    return rendered


def _compose_runtime_ops(left: Any, right: Any) -> tuple[tuple[tuple[Fraction, ...], ...], tuple[Fraction, Fraction, Fraction]]:
    rotation = tuple(
        tuple(
            sum(Fraction(left.W[row][mid]) * Fraction(right.W[mid][col]) for mid in range(3))
            for col in range(3)
        )
        for row in range(3)
    )
    translation = tuple(
        _mod1_fraction(
            sum(Fraction(left.W[row][mid]) * Fraction(right.t[mid]) for mid in range(3))
            + Fraction(left.t[row])
        )
        for row in range(3)
    )
    return rotation, translation


def _op_signature(op: Any) -> tuple[tuple[tuple[Fraction, ...], ...], tuple[Fraction, Fraction, Fraction]]:
    rotation = tuple(tuple(Fraction(value) for value in row) for row in op.W)
    translation = tuple(_mod1_fraction(Fraction(value)) for value in op.t)
    return rotation, translation


def _validate_seitz_operations(runtime_ctx: dict[str, Any]) -> dict[str, Any]:
    ops = list(runtime_ctx.get("ops", []))
    signatures = {_op_signature(op) for op in ops}
    identity_rotation = (
        (Fraction(1), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(1)),
    )
    identity_signature = (
        identity_rotation,
        (Fraction(0), Fraction(0), Fraction(0)),
    )
    closure_ok = True
    inverse_ok = True
    for left in ops:
        inverse_found = False
        for right in ops:
            if _compose_runtime_ops(left, right) == identity_signature and _compose_runtime_ops(right, left) == identity_signature:
                inverse_found = True
                break
        if not inverse_found:
            inverse_ok = False
            break
    for left in ops:
        for right in ops:
            if _compose_runtime_ops(left, right) not in signatures:
                closure_ok = False
                break
        if not closure_ok:
            break
    return {
        "operation_count": len(ops),
        "has_identity": identity_signature in signatures,
        "closed_under_composition": closure_ok,
        "all_inverses_present": inverse_ok,
    }


def _render_local_irreps(
    *,
    manifolds: list[dict[str, Any]],
    captures: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for manifold in manifolds:
        manifold_id = str(manifold["id"])
        raw = captures.get(manifold_id) or {}
        rep_degrees = [int(value) for value in raw.get("rep_degree", [])]
        torsion = [int(value) for value in raw.get("torsion", [])]
        character_rows = list(raw.get("character_json", []))
        linear_character_rows = list(raw.get("linear_character_json", []))
        local_irreps = [
            {
                "irrep_id": f"{manifold_id}_R{rep_index}",
                "rep_degree": rep_degrees[rep_index - 1],
                "torsion": torsion[rep_index - 1] if rep_index - 1 < len(torsion) else 0,
                "character": (
                    character_rows[rep_index - 1]
                    if rep_index - 1 < len(character_rows)
                    else []
                ),
                "linear_character": (
                    linear_character_rows[rep_index - 1]
                    if rep_index - 1 < len(linear_character_rows)
                    else []
                ),
            }
            for rep_index in range(1, len(rep_degrees) + 1)
        ]
        records.append(
            {
                "manifold_id": manifold_id,
                "manifold_kind": str(manifold.get("kind") or ""),
                "local_irreps": local_irreps,
            }
        )
    return records


def _render_local_irrep_branch_table(
    *,
    manifolds: list[dict[str, Any]],
    captures: dict[str, Any],
    branch_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    branches_by_host: dict[str, list[dict[str, Any]]] = {}
    for record in branch_records:
        branches_by_host.setdefault(str(record["host_manifold_id"]), []).append(record)
    table: list[dict[str, Any]] = []
    for manifold in manifolds:
        manifold_id = str(manifold["id"])
        branches = branches_by_host.get(manifold_id, [])
        raw = captures.get(manifold_id) or {}
        raw_local_irreps = [
            f"{manifold_id}_R{rep_index}"
            for rep_index in range(1, len(list(raw.get("rep_degree", []))) + 1)
        ]
        table.append(
            {
                "manifold_id": manifold_id,
                "manifold_kind": str(manifold.get("kind") or ""),
                "generic_local_irreps": raw_local_irreps,
                "monodromy_action": [
                    list(branch.get("local_irrep_labels", []))
                    for branch in branches
                ],
                "monodromy_orbits": [
                    list(branch.get("local_irrep_labels", []))
                    for branch in branches
                ],
                "global_branches": [
                    {
                        "branch_id": str(branch["branch_id"]),
                        "local_irrep_orbit": list(branch.get("local_irrep_labels", [])),
                    }
                    for branch in branches
                ],
            }
        )
    return table


def _complex_row_key(row: list[Any]) -> tuple[tuple[float, float], ...]:
    keyed: list[tuple[float, float]] = []
    for value in row:
        comp = complex(value)
        keyed.append((round(float(comp.real), 8), round(float(comp.imag), 8)))
    return tuple(keyed)


def _match_capture_permutation_by_exact_rows(
    reference_raw: dict[str, Any],
    shifted_raw: dict[str, Any],
    *,
    field: str,
) -> dict[str, Any]:
    reference_rows = [_complex_row_key(row) for row in reference_raw.get(field, [])]
    shifted_rows = [_complex_row_key(row) for row in shifted_raw.get(field, [])]
    if len(reference_rows) != len(shifted_rows):
        return {"complete": False, "permutation": [], "cycles": []}

    available: dict[tuple[tuple[float, float], ...], list[int]] = {}
    for index, row_key in enumerate(reference_rows, start=1):
        available.setdefault(row_key, []).append(index)

    permutation: list[int] = []
    for row_key in shifted_rows:
        choices = available.get(row_key) or []
        if not choices:
            return {"complete": False, "permutation": [], "cycles": []}
        permutation.append(choices.pop(0))

    visited: set[int] = set()
    cycles: list[list[int]] = []
    for start in range(1, len(permutation) + 1):
        if start in visited:
            continue
        cycle: list[int] = []
        current = start
        while current not in visited:
            visited.add(current)
            cycle.append(current)
            current = permutation[current - 1]
        if len(cycle) > 1:
            cycles.append(cycle)

    return {"complete": True, "permutation": permutation, "cycles": cycles}


def _line_monodromy_debug_payload(
    module: Any,
    resolved_group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    line_obj: dict[str, Any],
    line_raw: dict[str, Any],
) -> dict[str, Any]:
    port = stage1_backend()
    basis_vectors = list(line_obj.get("_basis", []))
    sample_point = [Fraction(str(value)) for value in line_obj.get("sample_point", [])]
    linear_character_cycles: list[list[int]] = []
    for basis_index, basis in enumerate(basis_vectors, start=1):
        shifted_sample = [
            float(sample_point[coord_index] + Fraction(str(basis[coord_index])))
            for coord_index in range(3)
        ]
        shifted_raw = port.capture_little_group(
            module,
            resolved_group_id,
            ssg_dict,
            ctx,
            mode,
            f"{line_obj['id']}__mono_shift{basis_index:02d}",
            shifted_sample,
        )
        match_debug = _match_capture_permutation_by_exact_rows(
            line_raw,
            shifted_raw,
            field="linear_character",
        )
        if not bool(match_debug.get("complete")):
            continue
        for cycle in match_debug.get("cycles", []):
            if len(cycle) > 1:
                linear_character_cycles.append([int(index) for index in cycle])
    return {"linear_character_cycles": linear_character_cycles}


def _plane_monodromy_basis_orbits(
    *,
    representative_plane: dict[str, Any],
    representative_raw: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
) -> list[list[int]]:
    parent: list[int] = list(range(len(list(representative_raw.get("rep_degree", [])))))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    base_sample = [Fraction(value) for value in representative_plane.get("sample_point", [])]
    port = stage1_backend()
    for basis_index, basis in enumerate(representative_plane.get("_basis", []), start=1):
        shifted_sample = [
            float(base_sample[coord_index] + Fraction(basis[coord_index]))
            for coord_index in range(3)
        ]
        shifted_raw = port.capture_little_group(
            module,
            group_id,
            ssg_dict,
            ctx,
            mode,
            f"{representative_plane['id']}__mono_shift{basis_index:02d}",
            shifted_sample,
        )
        match_debug = _match_capture_permutation_by_exact_rows(
            representative_raw,
            shifted_raw,
            field="linear_character",
        )
        if not bool(match_debug.get("complete")):
            continue
        for cycle in match_debug.get("cycles", []):
            cycle = [int(index) for index in cycle]
            if len(cycle) <= 1:
                continue
            anchor = cycle[0] - 1
            for other in cycle[1:]:
                union(anchor, other - 1)

    orbit_members: dict[int, list[int]] = {}
    for index in range(len(parent)):
        orbit_members.setdefault(find(index), []).append(index + 1)
    return [members for _root, members in sorted(orbit_members.items())]


def _md_validation_report(
    *,
    geometry_report: dict[str, Any],
    retained_shell: dict[str, Any],
    full_compatibility: dict[str, Any],
    projected: dict[str, Any],
) -> dict[str, Any]:
    manifolds = list(geometry_report.get("manifolds", []))
    manifold_source_kinds = {
        str(item.get("source_kind") or "")
        for item in manifolds
    }
    connections = list(geometry_report.get("connections_full", []))
    full_row_kinds = set(_global_row_kind_histogram(full_compatibility))
    projected_row_kinds = set(_global_row_kind_histogram(projected))
    generic_present = "listed_generic" in manifold_source_kinds
    manifold_by_id = {
        str(item["id"]): item
        for item in manifolds
    }
    adjacency = _adjacency_from_connections(connections)
    maximal_ids = [
        str(item["id"])
        for item in geometry_report.get("maximal_manifolds", [])
    ]
    component_map = {
        str(key): [str(item) for item in value]
        for key, value in (geometry_report.get("connected_components") or {}).items()
    }
    expected_retained_ids: set[str] = set()
    for maximal_id in maximal_ids:
        expected_retained_ids.update(component_map.get(maximal_id) or [maximal_id])
    actual_retained_ids = {
        str(item)
        for item in retained_shell.get("retained_manifold_ids", [])
    }
    maximality_consistent = True
    for manifold in manifolds:
        manifold_id = str(manifold["id"])
        manifold_rotation_keys = {
            tuple(tuple(row) for row in rotation)
            for rotation in manifold.get("rotation_keys", [])
        }
        expected_maximal = True
        for connection in adjacency.get(manifold_id, []):
            neighbor_id = connection["right"] if connection["left"] == manifold_id else connection["left"]
            neighbor = manifold_by_id.get(str(neighbor_id))
            if neighbor is None:
                continue
            neighbor_rotation_keys = {
                tuple(tuple(row) for row in rotation)
                for rotation in neighbor.get("rotation_keys", [])
            }
            if manifold_rotation_keys and neighbor_rotation_keys and manifold_rotation_keys < neighbor_rotation_keys:
                expected_maximal = False
                break
        if bool(manifold.get("maximal")) != expected_maximal:
            maximality_consistent = False
            break
    checks = [
        {
            "id": "connections_use_exact_closure_symmetry_image_definition",
            "passed": all(
                str(connection.get("detail") or "") == "exact_closure_symmetry_image_intersection"
                and bool(connection.get("via_closure"))
                for connection in connections
            ),
        },
        {
            "id": "maximality_is_determined_by_generic_little_cogroup_inclusion",
            "passed": maximality_consistent,
        },
        {
            "id": "retained_shell_covers_every_maximal_containing_connected_component",
            "passed": actual_retained_ids == expected_retained_ids,
        },
        {
            "id": "full_compatibility_matrix_contains_generic_rows_before_projection",
            "passed": (not generic_present)
            or any(row_kind.startswith("generic_") for row_kind in full_row_kinds),
        },
        {
            "id": "projection_eliminates_auxiliary_unknowns_exactly",
            "passed": projected_row_kinds <= {"exact_auxiliary_elimination", "rowspace_basis_without_auxiliary_unknowns"},
        },
    ]
    return {
        "passed": all(bool(check["passed"]) for check in checks),
        "checks": checks,
    }


def _node_sort_key(entry: dict[str, Any]) -> tuple[int, int | str]:
    kind_rank = {"point": 0, "line": 1, "plane": 2, "generic": 3}.get(
        str(entry.get("kind") or ""),
        99,
    )
    entry_id = str(entry.get("id") or "")
    suffix = entry_id[1:] if len(entry_id) > 1 else entry_id
    if suffix.isdigit():
        return (kind_rank, (0, int(suffix)))
    return (kind_rank, (1, entry_id))


def _frac_str(value: Any) -> str:
    value = Fraction(str(value))
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _parse_constraint_tokens(constraints: list[str]) -> list[dict[str, str]]:
    tokens: list[dict[str, str]] = []
    for raw in constraints:
        constraint = str(raw).strip()
        if "<" in constraint:
            left, right = [item.strip() for item in constraint.split("<", 1)]
            if left and right:
                if left[0].isalpha():
                    tokens.append({"parameter": left, "relation": "<", "value": right})
                elif right[0].isalpha():
                    tokens.append({"parameter": right, "relation": ">", "value": left})
        elif "=" in constraint:
            left, right = [item.strip() for item in constraint.split("=", 1)]
            if left and right and left[0].isalpha():
                tokens.append({"parameter": left, "relation": "=", "value": right})
    return tokens


def _closure_domain_from_constraints(
    parameters: list[str],
    constraints: list[str],
) -> dict[str, dict[str, Any]]:
    bounds = {
        str(parameter): {
            "lower": None,
            "upper": None,
            "lower_inclusive": False,
            "upper_inclusive": False,
            "equal": None,
        }
        for parameter in parameters
    }
    for token in _parse_constraint_tokens(constraints):
        parameter = token["parameter"]
        if parameter not in bounds:
            continue
        value = _frac_str(token["value"])
        if token["relation"] == "<":
            bounds[parameter]["upper"] = value
            bounds[parameter]["upper_inclusive"] = False
        elif token["relation"] == ">":
            bounds[parameter]["lower"] = value
            bounds[parameter]["lower_inclusive"] = False
        elif token["relation"] == "=":
            bounds[parameter]["equal"] = value
            bounds[parameter]["lower"] = value
            bounds[parameter]["upper"] = value
            bounds[parameter]["lower_inclusive"] = True
            bounds[parameter]["upper_inclusive"] = True
    closure = {}
    for parameter, record in bounds.items():
        closure[parameter] = {
            "lower": record["lower"],
            "upper": record["upper"],
            "lower_inclusive": bool(record["lower"] is not None),
            "upper_inclusive": bool(record["upper"] is not None),
            "equal": record["equal"],
        }
    return closure


def _param_domain_source(kind: str, constraints: list[str]) -> str:
    if kind == "point":
        return "point_trivial_domain"
    if constraints:
        return "listed_independent_parameter_range"
    return "missing_requires_canonical_star_construction"


def _rotation_keys_from_capture(raw: dict[str, Any] | None) -> list[list[list[int]]]:
    if not raw:
        return []
    rotations = raw.get("rotC") or []
    unitary_capture_indices = raw.get("unitary_capture_indices") or []
    keys: list[list[list[int]]] = []
    seen: set[tuple[tuple[int, ...], ...]] = set()
    for index in unitary_capture_indices:
        if int(index) < 0 or int(index) >= len(rotations):
            continue
        rotation_key = tuple(
            tuple(int(round(float(entry))) for entry in row)
            for row in rotations[int(index)]
        )
        if rotation_key in seen:
            continue
        seen.add(rotation_key)
        keys.append([list(row) for row in rotation_key])
    keys.sort()
    return keys


def _ensure_capture(
    *,
    captures: dict[str, Any],
    ctx: dict[str, Any],
    group_id: str,
    mode: str,
    point_id: str,
    sample_point: list[str],
) -> dict[str, Any]:
    raw = captures.get(point_id)
    if raw is not None:
        return raw
    port = stage1_backend()
    module = ssgreps_module()
    ssg_dict = port.load_ssg_dict(group_id)
    raw = port.capture_little_group(
        module,
        group_id,
        ssg_dict,
        ctx,
        mode,
        point_id,
        [float(Fraction(str(value))) for value in sample_point],
    )
    captures[point_id] = raw
    return raw


def _manifold_entry(
    *,
    entry: dict[str, Any],
    kind: str,
    entry_id: str,
    source_kind: str,
    capture: dict[str, Any] | None,
) -> dict[str, Any]:
    parameters = [str(value) for value in entry.get("parameters", [])]
    constraints = [str(value) for value in entry.get("constraints", [])]
    affine_anchor = [_frac_str(value) for value in entry.get("_anchor", entry.get("sample_point", []))]
    affine_basis = [
        [_frac_str(value) for value in row]
        for row in entry.get("_basis", [])
    ]
    metadata = entry.get("metadata") or {}
    param_domain_source = _param_domain_source(kind, constraints)
    rotation_keys = _rotation_keys_from_capture(capture)
    unitary_rotations = [
        [[_frac_str(value) for value in row] for row in rotation]
        for rotation in (capture or {}).get("unitary_rotations", [])
    ]
    unitary_translations = [
        [_frac_str(value) for value in translation]
        for translation in (capture or {}).get("unitary_translations", [])
    ]
    return {
        "id": entry_id,
        "label": str(entry.get("label") or entry_id),
        "kind": kind,
        "dim": int(entry.get("dimension", -1)),
        "source_kind": source_kind,
        "coordinate_expressions": [str(value) for value in entry.get("coordinate_expressions", [])],
        "parameters": parameters,
        "constraints": constraints,
        "param_domain": {
            "raw_constraints": list(constraints),
        },
        "param_domain_source": param_domain_source,
        "param_domain_complete": param_domain_source != "missing_requires_canonical_star_construction",
        "closure_domain": _closure_domain_from_constraints(parameters, constraints),
        "parametrization": str(entry.get("parametrization") or ""),
        "sample_point": [_frac_str(value) for value in entry.get("sample_point", [])],
        "affine_form": {
            "anchor": affine_anchor,
            "basis": affine_basis,
        },
        "source_letter": str(metadata.get("source_letter") or ""),
        "source_orbit": [str(value) for value in metadata.get("source_orbit", [])],
        "metadata": dict(metadata),
        "star_size": metadata.get("source_mult"),
        "symmetry_summary": dict(entry.get("symmetry_summary") or {}),
        "rotation_keys": rotation_keys,
        "rotation_key_count": len(rotation_keys),
        "generic_little_cogroup": {
            "rotation_keys": rotation_keys,
            "order": len(rotation_keys),
        },
        "generic_little_cogroup_generators": {
            "rotation_keys": rotation_keys,
        },
        "generic_full_little_group": {
            "unitary_rotations": unitary_rotations,
            "unitary_translations": unitary_translations,
        },
        "full_little_group_generators": {
            "unitary_rotations": unitary_rotations,
            "unitary_translations": unitary_translations,
        },
        "incident_lines": [str(item) for item in entry.get("incident_lines", [])],
        "incident_planes": [str(item) for item in entry.get("incident_planes", [])],
        "maximal": None,
        "maximal_blockers": [],
    }


def _closure_record(manifold: dict[str, Any], parameter: str) -> dict[str, Any]:
    return dict((manifold.get("closure_domain") or {}).get(str(parameter), {}))


def _closure_bounds(record: dict[str, Any]) -> tuple[Fraction | None, bool, Fraction | None, bool]:
    lower = record.get("lower")
    upper = record.get("upper")
    return (
        Fraction(str(lower)) if lower is not None else None,
        bool(record.get("lower_inclusive", False)),
        Fraction(str(upper)) if upper is not None else None,
        bool(record.get("upper_inclusive", False)),
    )


def _fraction(value: Any) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def _mod1_fraction(value: Fraction) -> Fraction:
    wrapped = value % 1
    if wrapped < 0:
        wrapped += 1
    return wrapped


def _manifold_affine_data(
    manifold: dict[str, Any],
) -> tuple[list[Fraction], list[list[Fraction]], list[tuple[Fraction | None, Fraction | None]]]:
    affine_form = manifold.get("affine_form") or {}
    anchor = [_fraction(value) for value in affine_form.get("anchor", [])]
    basis = [
        [_fraction(value) for value in row]
        for row in affine_form.get("basis", [])
    ]
    intervals: list[tuple[Fraction | None, Fraction | None]] = []
    for parameter in [str(value) for value in manifold.get("parameters", [])]:
        lower, _lower_inc, upper, _upper_inc = _closure_bounds(_closure_record(manifold, parameter))
        intervals.append((lower, upper))
    return anchor, basis, intervals


def _rotate_vector(
    vector: list[Fraction],
    rotation: tuple[tuple[Fraction, ...], ...],
) -> list[Fraction]:
    return [
        sum(rotation[row][column] * vector[column] for column in range(3))
        for row in range(3)
    ]


def _coordinate_interval(
    anchor: list[Fraction],
    basis: list[list[Fraction]],
    intervals: list[tuple[Fraction | None, Fraction | None]],
    coordinate_index: int,
) -> tuple[Fraction, Fraction] | None:
    minimum = anchor[coordinate_index]
    maximum = anchor[coordinate_index]
    for basis_vector, (lower, upper) in zip(basis, intervals):
        if lower is None or upper is None:
            return None
        coeff = basis_vector[coordinate_index]
        if coeff >= 0:
            minimum += coeff * lower
            maximum += coeff * upper
        else:
            minimum += coeff * upper
            maximum += coeff * lower
    return minimum, maximum


def _integer_shift_candidates(
    left_anchor: list[Fraction],
    left_basis: list[list[Fraction]],
    left_intervals: list[tuple[Fraction | None, Fraction | None]],
    right_anchor: list[Fraction],
    right_basis: list[list[Fraction]],
    right_intervals: list[tuple[Fraction | None, Fraction | None]],
) -> list[tuple[int, int, int]]:
    ranges: list[range] = []
    for coordinate_index in range(3):
        left_bounds = _coordinate_interval(left_anchor, left_basis, left_intervals, coordinate_index)
        right_bounds = _coordinate_interval(right_anchor, right_basis, right_intervals, coordinate_index)
        if left_bounds is None or right_bounds is None:
            return []
        left_min, left_max = left_bounds
        right_min, right_max = right_bounds
        shift_min = (left_min - right_max).__ceil__()
        shift_max = (left_max - right_min).__floor__()
        if shift_min > shift_max:
            return []
        ranges.append(range(int(shift_min), int(shift_max) + 1))
    return [
        (int(shift_x), int(shift_y), int(shift_z))
        for shift_x, shift_y, shift_z in product(*ranges)
    ]


def _sympy_fraction(expr: sp.Expr) -> Fraction:
    simplified = sp.simplify(expr)
    if simplified == 0:
        return Fraction(0)
    if simplified.is_Rational:
        return Fraction(int(simplified.p), int(simplified.q))
    raise ValueError(f"expected exact rational expression, got {simplified!r}")


def _fourier_motzkin_feasible(
    inequalities: list[tuple[list[Fraction], Fraction]],
    variable_count: int,
) -> bool:
    if variable_count == 0:
        return all(bound >= 0 for _coeffs, bound in inequalities)

    zero_coeff: list[tuple[list[Fraction], Fraction]] = []
    positive_coeff: list[tuple[Fraction, list[Fraction], Fraction]] = []
    negative_coeff: list[tuple[Fraction, list[Fraction], Fraction]] = []
    pivot_index = variable_count - 1
    for coeffs, bound in inequalities:
        pivot = coeffs[pivot_index]
        rest = list(coeffs[:pivot_index])
        if pivot == 0:
            zero_coeff.append((rest, bound))
        elif pivot > 0:
            positive_coeff.append((pivot, rest, bound))
        else:
            negative_coeff.append((pivot, rest, bound))

    reduced = list(zero_coeff)
    if positive_coeff and negative_coeff:
        for positive, pos_rest, pos_bound in positive_coeff:
            for negative, neg_rest, neg_bound in negative_coeff:
                reduced.append(
                    (
                        [
                            (-negative) * pos_value + positive * neg_value
                            for pos_value, neg_value in zip(pos_rest, neg_rest)
                        ],
                        (-negative) * pos_bound + positive * neg_bound,
                    )
                )
    return _fourier_motzkin_feasible(reduced, variable_count - 1)


def _linear_solution_terms(
    solution: sp.Matrix,
) -> tuple[list[sp.Symbol], list[Fraction], list[list[Fraction]]]:
    free_symbols = sorted(
        {symbol for expr in list(solution) for symbol in expr.free_symbols},
        key=lambda item: item.name,
    )
    zero_assignment = {symbol: sp.Integer(0) for symbol in free_symbols}
    constants = [
        _sympy_fraction(expr.subs(zero_assignment))
        for expr in list(solution)
    ]
    coefficients = [
        [
            _sympy_fraction(sp.expand(expr).coeff(symbol))
            for symbol in free_symbols
        ]
        for expr in list(solution)
    ]
    return free_symbols, constants, coefficients


def _closure_inequalities_from_solution_terms(
    *,
    constants: list[Fraction],
    coefficients: list[list[Fraction]],
    parameter_intervals: list[tuple[Fraction | None, Fraction | None]],
) -> list[tuple[list[Fraction], Fraction]]:
    inequalities: list[tuple[list[Fraction], Fraction]] = []
    for constant, coeffs, (lower, upper) in zip(constants, coefficients, parameter_intervals):
        if upper is not None:
            inequalities.append((list(coeffs), upper - constant))
        if lower is not None:
            inequalities.append(([-value for value in coeffs], constant - lower))
    return inequalities


def _solution_feasible_in_closure(
    solution: sp.Matrix,
    *,
    parameter_intervals: list[tuple[Fraction | None, Fraction | None]],
) -> bool:
    free_symbols, constants, coefficients = _linear_solution_terms(solution)
    if not free_symbols:
        for value, (lower, upper) in zip(constants, parameter_intervals):
            if lower is not None and value < lower:
                return False
            if upper is not None and value > upper:
                return False
        return True

    inequalities = _closure_inequalities_from_solution_terms(
        constants=constants,
        coefficients=coefficients,
        parameter_intervals=parameter_intervals,
    )
    return _fourier_motzkin_feasible(inequalities, len(free_symbols))


def _solution_witness_in_closure(
    solution: sp.Matrix,
    *,
    parameter_intervals: list[tuple[Fraction | None, Fraction | None]],
) -> list[Fraction] | None:
    free_symbols, constants, coefficients = _linear_solution_terms(solution)
    if not free_symbols:
        return list(constants)
    if linprog is None:
        return None

    inequalities = _closure_inequalities_from_solution_terms(
        constants=constants,
        coefficients=coefficients,
        parameter_intervals=parameter_intervals,
    )
    if not inequalities:
        free_values = [0.0] * len(free_symbols)
    else:
        result = linprog(
            c=[0.0] * len(free_symbols),
            A_ub=[[float(value) for value in coeffs] for coeffs, _bound in inequalities],
            b_ub=[float(bound) for _coeffs, bound in inequalities],
            bounds=[(None, None)] * len(free_symbols),
            method="highs",
        )
        if not result.success:
            return None
        free_values = [float(value) for value in result.x]

    witness: list[Fraction] = []
    for constant, coeffs in zip(constants, coefficients):
        value = float(constant) + sum(float(coeff) * free_value for coeff, free_value in zip(coeffs, free_values))
        witness.append(Fraction(value).limit_denominator(1024))
    return witness


def _contact_type_from_witness(
    *,
    intervals: list[tuple[Fraction | None, Fraction | None]],
    witness: list[Fraction] | None,
) -> str:
    if witness is None:
        return "unknown"
    if not witness:
        return "boundary"
    for value, (lower, upper) in zip(witness, intervals):
        if lower is not None and value == lower:
            return "boundary"
        if upper is not None and value == upper:
            return "boundary"
    return "interior"


def _pair_relation_kind(left_kind: str, right_kind: str) -> str:
    kinds = tuple(sorted((left_kind, right_kind)))
    if "generic" in kinds:
        other_kind = right_kind if left_kind == "generic" else left_kind
        return f"generic_{other_kind}_closure_incidence"
    if kinds == ("line", "plane"):
        return "line_plane_geometric_incidence"
    if kinds == ("line", "point"):
        return "point_line_geometric_incidence"
    if kinds == ("plane", "point"):
        return "point_plane_geometric_incidence"
    return f"{kinds[0]}_{kinds[1]}_geometric_incidence"


def _is_maximal_intermediate_edge(
    left_id: str,
    right_id: str,
    *,
    maximal_ids: set[str],
) -> bool:
    return (left_id in maximal_ids) != (right_id in maximal_ids)


def _pair_connection_metadata(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    rotation: tuple[tuple[Fraction, ...], ...],
    shift: tuple[int, int, int],
    contact_type: str,
    left_witness: list[Fraction] | None = None,
    right_witness: list[Fraction] | None = None,
    k_contact: list[Fraction] | None = None,
) -> dict[str, Any]:
    left_parameters = [str(value) for value in left.get("parameters", [])]
    right_parameters = [str(value) for value in right.get("parameters", [])]
    return {
        "left": str(left["id"]),
        "right": str(right["id"]),
        "relation_kind": _pair_relation_kind(
            str(left.get("kind") or ""),
            str(right.get("kind") or ""),
        ),
        "detail": "exact_closure_symmetry_image_intersection",
        "symmetry_image_used": [[int(value) for value in row] for row in rotation],
        "reciprocal_shift": [int(value) for value in shift],
        "contact_type": str(contact_type),
        "boundary_solution": {
            "left_parameters": (
                {
                    parameter: _frac_str(value)
                    for parameter, value in zip(left_parameters, left_witness)
                }
                if left_witness is not None
                else {}
            ),
            "right_parameters": (
                {
                    parameter: _frac_str(value)
                    for parameter, value in zip(right_parameters, right_witness)
                }
                if right_witness is not None
                else {}
            ),
        },
        "k_contact": (
            [_frac_str(value) for value in k_contact]
            if k_contact is not None
            else []
        ),
        "via_closure": True,
    }


def _find_exact_connection(
    left: dict[str, Any],
    right: dict[str, Any],
    rotations: list[tuple[tuple[Fraction, ...], ...]],
) -> dict[str, Any] | None:
    left_anchor, left_basis, left_intervals = _manifold_affine_data(left)
    right_anchor, right_basis, right_intervals = _manifold_affine_data(right)
    left_dim = len(left_basis)
    right_dim = len(right_basis)
    for rotation in rotations:
        rotated_anchor = _rotate_vector(right_anchor, rotation)
        rotated_basis = [
            _rotate_vector(vector, rotation)
            for vector in right_basis
        ]
        shift_candidates = _integer_shift_candidates(
            left_anchor,
            left_basis,
            left_intervals,
            rotated_anchor,
            rotated_basis,
            right_intervals,
        )
        if not shift_candidates:
            continue
        for shift in shift_candidates:
            if left_dim + right_dim == 0:
                if all(
                    left_anchor[index] == rotated_anchor[index] + Fraction(shift[index])
                    for index in range(3)
                ):
                    return _pair_connection_metadata(left, right, rotation=rotation, shift=shift)
                continue

            matrix = sp.Matrix(
                [
                    [
                        *[
                            sp.Rational(left_basis[column][row].numerator, left_basis[column][row].denominator)
                            for column in range(left_dim)
                        ],
                        *[
                            sp.Rational(
                                (-rotated_basis[column][row]).numerator,
                                (-rotated_basis[column][row]).denominator,
                            )
                            for column in range(right_dim)
                        ],
                    ]
                    for row in range(3)
                ]
            )
            rhs = sp.Matrix(
                [
                    sp.Rational(
                        (rotated_anchor[row] + Fraction(shift[row]) - left_anchor[row]).numerator,
                        (rotated_anchor[row] + Fraction(shift[row]) - left_anchor[row]).denominator,
                    )
                    for row in range(3)
                ]
            )
            try:
                solution, _params = matrix.gauss_jordan_solve(rhs)
            except Exception:
                continue
            parameter_intervals = [*left_intervals, *right_intervals]
            if _solution_feasible_in_closure(
                solution,
                parameter_intervals=parameter_intervals,
            ):
                witness = _solution_witness_in_closure(
                    solution,
                    parameter_intervals=parameter_intervals,
                )
                left_witness = witness[:left_dim] if witness is not None else None
                right_witness = witness[left_dim:] if witness is not None else None
                k_contact = None
                if left_witness is not None:
                    k_contact = [
                        _mod1_fraction(
                            left_anchor[row]
                            + sum(
                                left_basis[column][row] * left_witness[column]
                                for column in range(left_dim)
                            )
                        )
                        for row in range(3)
                    ]
                left_contact_type = _contact_type_from_witness(
                    intervals=left_intervals,
                    witness=left_witness,
                )
                right_contact_type = _contact_type_from_witness(
                    intervals=right_intervals,
                    witness=right_witness,
                )
                contact_type = (
                    "interior"
                    if left_contact_type == right_contact_type == "interior"
                    else "boundary"
                )
                return _pair_connection_metadata(
                    left,
                    right,
                    rotation=rotation,
                    shift=shift,
                    contact_type=contact_type,
                    left_witness=left_witness,
                    right_witness=right_witness,
                    k_contact=k_contact,
                )
    return None


def _build_connections(
    *,
    shared: dict[str, Any],
    manifolds: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifold_by_id = {str(item["id"]): item for item in manifolds}
    connections: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    runtime_ctx = (shared.get("kgeom") or {}).get("runtime_ctx") or {}
    rotations: list[tuple[tuple[Fraction, ...], ...]] = []
    seen_rotations: set[tuple[tuple[Fraction, ...], ...]] = set()
    for op in runtime_ctx.get("ops", []):
        rotation = tuple(
            tuple(_fraction(value) for value in row)
            for row in op.W
        )
        if rotation in seen_rotations:
            continue
        seen_rotations.add(rotation)
        rotations.append(rotation)
    if not rotations:
        rotations = [
            (
                (Fraction(1), Fraction(0), Fraction(0)),
                (Fraction(0), Fraction(1), Fraction(0)),
                (Fraction(0), Fraction(0), Fraction(1)),
            )
        ]

    def add(connection: dict[str, Any]) -> None:
        left_id = str(connection["left"])
        right_id = str(connection["right"])
        if left_id not in manifold_by_id or right_id not in manifold_by_id:
            return
        pair = tuple(sorted((left_id, right_id)))
        key = (
            pair[0],
            pair[1],
            str(connection.get("relation_kind") or ""),
            str(connection.get("detail") or ""),
            str(connection.get("symmetry_image_used") or ""),
            str(connection.get("reciprocal_shift") or ""),
            str(connection.get("boundary_solution") or ""),
        )
        if key in seen:
            return
        seen.add(key)
        connections.append(dict(connection))

    ordered_manifolds = sorted(manifolds, key=_node_sort_key)
    for left_index, left in enumerate(ordered_manifolds):
        for right in ordered_manifolds[left_index + 1 :]:
            connection = _find_exact_connection(left, right, rotations)
            if connection is not None:
                add(connection)

    connections.sort(
        key=lambda item: (
            _node_sort_key(manifold_by_id[item["left"]]),
            _node_sort_key(manifold_by_id[item["right"]]),
            str(item["relation_kind"]),
            str(item["detail"]),
        )
    )
    return connections


def _public_manifold_record(item: dict[str, Any]) -> dict[str, Any]:
    """Project an internal manifold entry into the md-facing JSON language."""
    return {
        "id": str(item["id"]),
        "label": str(item.get("label") or item["id"]),
        "kind": str(item["kind"]),
        "dim": int(item["dim"]),
        "affine_form": dict(item.get("affine_form") or {}),
        "generic_k": [str(value) for value in item.get("sample_point", [])],
        "independent_domain": dict(item.get("param_domain") or {}),
        "closure_domain": dict(item.get("closure_domain") or {}),
        "star_size": item.get("star_size"),
        "generic_little_cogroup": dict(item.get("generic_little_cogroup") or {}),
        "generic_little_cogroup_generators": dict(item.get("generic_little_cogroup_generators") or {}),
        "generic_full_little_group": dict(item.get("generic_full_little_group") or {}),
        "full_little_group_generators": dict(item.get("full_little_group_generators") or {}),
        "symmetry_summary": dict(item.get("symmetry_summary") or {}),
        "maximal": item.get("maximal"),
    }


def _public_connection_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "from": str(item["left"]),
        "to": str(item["right"]),
        "symmetry_image_used": list(item.get("symmetry_image_used", [])),
        "boundary_solution": dict(item.get("boundary_solution") or {}),
        "k_contact": list(item.get("k_contact") or []),
        "contact_type": str(item.get("contact_type") or ""),
    }


def _decorate_maximal_manifolds_with_branch_counts(
    maximal_manifolds: list[dict[str, Any]],
    branch_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    branches_by_host: dict[str, list[dict[str, Any]]] = {}
    for record in branch_records:
        branches_by_host.setdefault(str(record["host_manifold_id"]), []).append(record)
    enriched: list[dict[str, Any]] = []
    for manifold in maximal_manifolds:
        manifold_id = str(manifold["id"])
        branches = branches_by_host.get(manifold_id, [])
        enriched.append(
            {
                **_public_manifold_record(manifold),
                "global_branch_count": len(branches),
                "branch_ids": [str(item["branch_id"]) for item in branches],
            }
        )
    return enriched


def _public_branch_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record["branch_id"]),
        "host_maximal_manifold": str(record["host_maximal_manifold"]),
        "host_manifold_kind": str(record.get("host_manifold_kind") or ""),
        "local_irrep_orbit": list(record.get("local_irrep_orbit", [])),
        "representative_local_irrep": record.get("representative_local_irrep"),
        "orbit_size": int(record.get("orbit_size", 0)),
    }


def _adjacency_from_connections(connections: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for connection in connections:
        adjacency.setdefault(str(connection["left"]), []).append(connection)
        adjacency.setdefault(str(connection["right"]), []).append(connection)
    return adjacency


def _connected_components(
    manifolds: list[dict[str, Any]],
    connections: list[dict[str, Any]],
) -> dict[str, list[str]]:
    adjacency = _adjacency_from_connections(connections)
    manifold_by_id = {str(item["id"]): item for item in manifolds}
    components: dict[str, list[str]] = {}
    visited: set[str] = set()
    for manifold in manifolds:
        start_id = str(manifold["id"])
        if start_id in visited:
            continue
        stack = [start_id]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for connection in adjacency.get(current, []):
                neighbor_id = connection["right"] if connection["left"] == current else connection["left"]
                if neighbor_id not in visited:
                    stack.append(neighbor_id)
        component.sort(key=lambda item: _node_sort_key(manifold_by_id[item]))
        for node_id in component:
            components[node_id] = list(component)
    return components


def _classify_maximal_manifolds(
    manifolds: list[dict[str, Any]],
    connections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify maximal manifolds by generic little-co-group inclusion."""
    adjacency = _adjacency_from_connections(connections)
    manifold_by_id = {str(item["id"]): item for item in manifolds}
    updated: list[dict[str, Any]] = []
    for manifold in manifolds:
        manifold_id = str(manifold["id"])
        manifold_rotation_keys = {
            tuple(tuple(row) for row in rotation)
            for rotation in manifold.get("rotation_keys", [])
        }
        blockers: list[dict[str, Any]] = []
        for connection in adjacency.get(manifold_id, []):
            neighbor_id = connection["right"] if connection["left"] == manifold_id else connection["left"]
            neighbor = manifold_by_id.get(str(neighbor_id))
            if neighbor is None:
                continue
            neighbor_rotation_keys = {
                tuple(tuple(row) for row in rotation)
                for rotation in neighbor.get("rotation_keys", [])
            }
            if manifold_rotation_keys and neighbor_rotation_keys and manifold_rotation_keys < neighbor_rotation_keys:
                blockers.append(
                    {
                        "neighbor_id": str(neighbor_id),
                        "neighbor_kind": str(neighbor.get("kind") or ""),
                        "relation_kind": str(connection.get("relation_kind") or ""),
                        "node_rotation_key_count": len(manifold_rotation_keys),
                        "neighbor_rotation_key_count": len(neighbor_rotation_keys),
                    }
                )
        updated.append(
            {
                **manifold,
                "maximal": not blockers,
                "maximal_blockers": blockers,
            }
        )
    return updated


def _prepare_capture_context(group_id: str, mode: str) -> tuple[str, dict[str, Any], dict[str, Any], Any, dict[str, Any], dict[str, Any]]:
    """Build the minimal low-level context needed by the standalone rewrite.

    The md rewrite stays independent from older orchestration paths, but still
    reuses the low-level capture machinery:
    resolved group id, auxiliary k-geometry, loaded SSGReps module, runtime
    context, and canonicalized manifold captures.
    """
    port = stage1_backend()
    resolved_group_id = port.resolve_group_number(group_id)
    shared = _build_md_geometry_bundle(resolved_group_id)
    kgeom = dict(shared["kgeom"])
    kgeom["synthetic_boundary_points"] = []
    grouped = kgeom["grouped"]
    kgeom["generic_representatives"] = stage1_backend().build_generic_representative_points(
        grouped,
        kgeom["runtime_ctx"],
    )
    module = ssgreps_module()
    ssg_dict = port.load_ssg_dict(resolved_group_id)
    ctx = port.load_context(module, resolved_group_id, mode, ssg_dict)
    ctx["kgeom"] = kgeom
    captures = port.build_manifold_capture(module, resolved_group_id, ssg_dict, ctx, mode, kgeom)
    adjusted_captures = dict(captures)
    for line_obj in grouped.get("lines", []):
        line_id = str(line_obj["id"])
        raw = dict(adjusted_captures.get(line_id) or {})
        if not raw:
            continue
        monodromy_debug = _line_monodromy_debug_payload(
            module,
            resolved_group_id,
            ssg_dict,
            ctx,
            mode,
            line_obj,
            raw,
        )
        raw["capture_sample_point"] = list(line_obj.get("sample_point", []))
        raw["capture_canonicalization_source"] = "default_sample_point"
        raw["line_monodromy_debug"] = monodromy_debug
        raw["line_monodromy_basis_orbits"] = [
            [f"{line_id}_R{rep_index}" for rep_index in cycle]
            for cycle in monodromy_debug.get("linear_character_cycles", [])
            if cycle
        ]
        adjusted_captures[line_id] = raw
    captures = adjusted_captures
    return resolved_group_id, shared, kgeom, module, ctx, captures


def _build_md_geometry_report(
    *,
    requested_group_id: str,
    resolved_group_id: str,
    shared: dict[str, Any],
    kgeom: dict[str, Any],
    ctx: dict[str, Any],
    captures: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """Build the md manifold shell from listed operation-derived manifolds."""
    generic_representatives = {
        str(item["id"]): item
        for item in kgeom.get("generic_representatives", [])
    }
    grouped = shared["grouped"]
    manifolds: list[dict[str, Any]] = []
    for point in grouped.get("points", []):
        point_id = str(point["id"])
        capture = _ensure_capture(
            captures=captures,
            ctx=ctx,
            group_id=resolved_group_id,
            mode=mode,
            point_id=point_id,
            sample_point=[str(value) for value in point.get("sample_point", [])],
        )
        manifolds.append(
            _manifold_entry(
                entry=point,
                kind="point",
                entry_id=point_id,
                source_kind="listed_point",
                capture=capture,
            )
        )
    for line in grouped.get("lines", []):
        line_id = str(line["id"])
        manifolds.append(
            _manifold_entry(
                entry=line,
                kind="line",
                entry_id=line_id,
                source_kind="listed_line",
                capture=captures.get(line_id),
            )
        )
    for plane in grouped.get("planes", []):
        plane_id = str(plane["id"])
        manifolds.append(
            _manifold_entry(
                entry=plane,
                kind="plane",
                entry_id=plane_id,
                source_kind="listed_plane",
                capture=captures.get(plane_id),
            )
        )
    for index, generic in enumerate(grouped.get("generic", []), start=1):
        representative = generic_representatives.get(f"G{index}") or {}
        generic_id = str(representative.get("id") or f"G{index}")
        generic_entry = dict(generic)
        generic_entry.setdefault("label", generic_id)
        generic_entry.setdefault("sample_point", representative.get("sample_point", generic.get("sample_point", [])))
        generic_entry.setdefault("_anchor", generic.get("_anchor", [0, 0, 0]))
        generic_entry.setdefault("_basis", generic.get("_basis", []))
        generic_entry.setdefault("symmetry_summary", representative.get("symmetry_summary", generic.get("symmetry_summary", {})))
        capture = _ensure_capture(
            captures=captures,
            ctx=ctx,
            group_id=resolved_group_id,
            mode=mode,
            point_id=generic_id,
            sample_point=[str(value) for value in generic_entry.get("sample_point", [])],
        )
        manifolds.append(
            _manifold_entry(
                entry=generic_entry,
                kind="generic",
                entry_id=generic_id,
                source_kind="listed_generic",
                capture=capture,
            )
        )
    manifolds.sort(key=_node_sort_key)
    strict_shared = {
        **shared,
        "kgeom": kgeom,
        "synthetic_points": [],
    }
    connections = _build_connections(
        shared=strict_shared,
        manifolds=manifolds,
    )
    components = _connected_components(manifolds, connections)
    manifolds = _classify_maximal_manifolds(manifolds, connections)
    maximal_manifolds = [
        dict(item)
        for item in manifolds
        if bool(item.get("maximal"))
    ]
    return {
        "generated_at": now_iso(),
        "requested_group": str(requested_group_id),
        "resolved_group": str(resolved_group_id),
        "mode": mode,
        "workflow_kind": "md_geometry_manifold_shell",
        "coordinate_system": "post_supercell_primitive_reciprocal_basis_from_swyckoff_k_construct_std_ssg_operations",
        "manifolds": manifolds,
        "maximal_manifolds": maximal_manifolds,
        "connections_full": connections,
        "connected_components": components,
    }


def _retained_component_shell(
    *,
    geometry_report: dict[str, Any],
    grouped: dict[str, Any],
) -> dict[str, Any]:
    """Select the manifold shell that the latest md wants in the full matrix.

    The md workflow retains non-maximal manifolds that are connected to maximal
    manifolds, then writes the full compatibility matrix on that retained shell,
    and only afterwards projects to BS variables.
    """
    manifolds = list(geometry_report.get("manifolds", []))
    connections = list(geometry_report.get("connections_full", []))
    maximal_ids = [str(item["id"]) for item in geometry_report.get("maximal_manifolds", [])]
    maximal_set = set(maximal_ids)
    manifold_order = {
        str(item["id"]): index
        for index, item in enumerate(manifolds)
    }
    manifold_by_id = {
        str(item["id"]): item
        for item in manifolds
    }
    grouped_point_ids = [
        str(item["id"])
        for item in manifolds
        if str(item.get("kind") or "") == "point"
    ]
    grouped_line_ids = [str(line["id"]) for line in grouped.get("lines", [])]
    grouped_plane_ids = [str(plane["id"]) for plane in grouped.get("planes", [])]
    grouped_line_id_set = set(grouped_line_ids)
    grouped_plane_id_set = set(grouped_plane_ids)

    # The md shell keeps every non-maximal manifold that belongs to a connected
    # component containing at least one maximal manifold.  Restricting to one-hop
    # neighbors would delete genuine intermediate manifolds before the full
    # compatibility matrix is written.
    component_map = dict(geometry_report.get("connected_components") or {})
    retained_ids: set[str] = set()
    for maximal_id in maximal_ids:
        component_ids = component_map.get(maximal_id) or [maximal_id]
        retained_ids.update(str(item) for item in component_ids)

    retained_manifolds = [
        item
        for item in manifolds
        if str(item["id"]) in retained_ids
    ]
    retained_connections = [
        connection
        for connection in connections
        if str(connection["left"]) in retained_ids and str(connection["right"]) in retained_ids
    ]
    retained_component_map = _connected_components(
        retained_manifolds,
        retained_connections,
    )

    component_records: list[dict[str, Any]] = []
    seen_component_keys: set[tuple[str, ...]] = set()
    for manifold_id in sorted(retained_ids, key=lambda item: manifold_order.get(str(item), 10**9)):
        component_ids = list(retained_component_map.get(manifold_id) or [manifold_id])
        component_key = tuple(sorted(component_ids))
        if component_key in seen_component_keys:
            continue
        seen_component_keys.add(component_key)
        component_records.append(
            {
                "component_ids": sorted(
                    component_ids,
                    key=lambda item: manifold_order.get(str(item), 10**9),
                ),
                "maximal_ids": sorted(
                    [item for item in component_ids if item in maximal_set],
                    key=lambda item: manifold_order.get(str(item), 10**9),
                ),
                "point_ids": [
                    item for item in grouped_point_ids
                    if item in component_ids
                ],
                "line_ids": [
                    item for item in grouped_line_ids
                    if item in component_ids
                ],
                "plane_ids": [
                    item for item in grouped_plane_ids
                    if item in component_ids
                ],
                "generic_ids": [
                    str(item["id"])
                    for item in manifolds
                    if str(item["id"]) in component_ids
                    and str(item.get("kind") or "") == "generic"
                ],
            }
        )

    retained_line_ids = [line_id for line_id in grouped_line_ids if line_id in retained_ids]
    retained_plane_ids = [plane_id for plane_id in grouped_plane_ids if plane_id in retained_ids]
    retained_point_ids = [point_id for point_id in grouped_point_ids if point_id in retained_ids]
    retained_generic_ids = [
        str(item["id"])
        for item in manifolds
        if str(item.get("kind") or "") == "generic"
        and str(item["id"]) in retained_ids
    ]
    intermediate_manifolds = [
        {
            **_public_manifold_record(item),
            "role_in_compatibility": (
                "generic_connector_manifold"
                if str(item.get("kind") or "") == "generic"
                else f"{str(item.get('kind') or '')}_intermediate_manifold"
            ),
        }
        for item in manifolds
        if (
            str(item["id"]) not in maximal_set
            and str(item.get("kind") or "") in {"point", "line", "plane", "generic"}
            and str(item["id"]) in retained_ids
        )
    ]
    return {
        "component_records": component_records,
        "retained_point_ids": retained_point_ids,
        "retained_line_ids": retained_line_ids,
        "retained_plane_ids": retained_plane_ids,
        "retained_generic_ids": retained_generic_ids,
        "intermediate_manifolds": intermediate_manifolds,
        "retained_manifold_ids": sorted(
            retained_ids,
            key=lambda item: manifold_order.get(str(item), 10**9),
        ),
        "retained_manifold_kinds": {
            manifold_id: str((manifold_by_id.get(manifold_id) or {}).get("kind") or "")
            for manifold_id in sorted(
                retained_ids,
                key=lambda item: manifold_order.get(str(item), 10**9),
            )
        },
        "grouped_line_id_set": grouped_line_id_set,
        "grouped_plane_id_set": grouped_plane_id_set,
    }


def _selected_line_blocks(
    *,
    grouped: dict[str, Any],
    captures: dict[str, Any],
    line_ids: set[str],
    point_ids: set[str],
    connections: list[dict[str, Any]],
    maximal_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build md line blocks using only actual listed point manifolds."""
    port = stage1_backend()
    blocks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    adjacency = _adjacency_from_connections(connections)
    for line in grouped.get("lines", []):
        line_id = str(line["id"])
        if line_id not in line_ids:
            continue
        try:
            line_raw = captures[line_id]
            field = "character"
            line_basis_labels = [
                f"{line_id}_R{rep_index}"
                for rep_index in range(1, len(line_raw.get(field, [])) + 1)
            ]
            local_unknown_ordering: list[str] = []
            full_equations: list[dict[str, Any]] = []
            full_matrix_rows: list[list[int]] = []
            line_basis_matrix = port._exact_basis_matrix_from_capture(
                line_raw,
                field,
                manifold_id=line_id,
            )

            point_decompositions: dict[str, list[dict[str, Any]]] = {}
            point_edges = sorted(
                [
                    connection
                    for connection in adjacency.get(line_id, [])
                    if (
                        str(connection.get("relation_kind") or "") == "point_line_geometric_incidence"
                        and (
                            str(connection["right"]) if str(connection["left"]) == line_id else str(connection["left"])
                        ) in point_ids
                        and _is_maximal_intermediate_edge(
                            line_id,
                            str(connection["right"]) if str(connection["left"]) == line_id else str(connection["left"]),
                            maximal_ids=maximal_ids,
                        )
                    )
                ],
                key=lambda item: (
                    str(item.get("symmetry_image_used") or ""),
                    str(item.get("boundary_solution") or ""),
                    str(item.get("reciprocal_shift") or ""),
                ),
            )
            point_child_ids = [
                str(connection["right"]) if str(connection["left"]) == line_id else str(connection["left"])
                for connection in point_edges
            ]
            for point_id in sorted(set(point_child_ids)):
                point_raw = captures.get(point_id)
                if point_raw is None:
                    continue
                matched = port.matched_unitary_indices(line_raw, point_raw)
                reps: list[dict[str, Any]] = []
                for rep_index in range(1, len(point_raw.get(field, [])) + 1):
                    rep_id = f"{point_id}_R{rep_index}"
                    restricted = port._exact_restriction_vector(
                        line_raw,
                        point_raw,
                        matched,
                        field=field,
                        parent_manifold_id=line_id,
                        child_manifold_id=point_id,
                        rep_id=rep_id,
                    )
                    coeffs_int = port.solve_unique_integer_decomposition(
                        line_basis_matrix,
                        restricted,
                        mode="md_line_point_decomposition",
                        manifold_id=line_id,
                        endpoint_id=point_id,
                        rep_id=rep_id,
                        field=field,
                    )
                    reps.append(
                        {
                            "rep_id": rep_id,
                            "decomposition_on_line_basis": {
                                label: coeff
                                for label, coeff in zip(line_basis_labels, coeffs_int)
                                if coeff
                            },
                        }
                    )
                    local_unknown_ordering.append(rep_id)
                point_decompositions[point_id] = reps

            full_local_unknown_ordering = list(local_unknown_ordering)
            full_local_unknown_ordering.extend(line_basis_labels)
            full_local_index = {
                str(unknown): index
                for index, unknown in enumerate(full_local_unknown_ordering)
            }
            for edge_index, connection in enumerate(point_edges, start=1):
                point_id = str(connection["right"]) if str(connection["left"]) == line_id else str(connection["left"])
                reps = point_decompositions.get(point_id, [])
                for basis_label in line_basis_labels:
                    row = [0] * len(full_local_unknown_ordering)
                    terms: list[dict[str, Any]] = []
                    for rep in reps:
                        coeff = int(rep["decomposition_on_line_basis"].get(basis_label, 0))
                        if coeff == 0:
                            continue
                        row[full_local_index[rep["rep_id"]]] += coeff
                        terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": "point"})
                    row[full_local_index[basis_label]] -= 1
                    terms.append({"unknown": basis_label, "coeff": -1, "side": "line"})
                    if any(row):
                        full_equations.append(
                            {
                                "basis_id": f"{line_id}_{point_id}_E{edge_index:02d}_{basis_label}",
                                "row_kind": "line_point_decomposition",
                                "point_id": point_id,
                                "line_id": line_id,
                                "source_line_id": line_id,
                                "connection_edge": dict(connection),
                                "line_basis_id": basis_label,
                                "terms": terms,
                            }
                        )
                        full_matrix_rows.append(row)

            for orbit_index, orbit in enumerate(line_raw.get("line_monodromy_basis_orbits", []), start=1):
                orbit_labels = [str(label) for label in orbit if str(label) in full_local_index]
                if len(orbit_labels) <= 1:
                    continue
                anchor = orbit_labels[0]
                for other_index, other in enumerate(orbit_labels[1:], start=1):
                    row = [0] * len(full_local_unknown_ordering)
                    row[full_local_index[anchor]] += 1
                    row[full_local_index[other]] -= 1
                    full_equations.append(
                        {
                            "basis_id": f"{line_id}_MONO_ORBIT_{orbit_index:02d}_{other_index:02d}",
                            "row_kind": "line_basis_orbit_delta",
                            "point_id": None,
                            "line_id": line_id,
                            "source_line_id": line_id,
                            "monodromy_basis_orbit": list(orbit_labels),
                            "terms": [
                                {"unknown": anchor, "coeff": 1, "side": "line"},
                                {"unknown": other, "coeff": -1, "side": "line"},
                            ],
                        }
                    )
                    full_matrix_rows.append(row)

            blocks.append(
                {
                    "line_id": line_id,
                    "source_line_id": line_id,
                    "line_basis_labels": list(line_basis_labels),
                    "endpoint_ids": list(point_child_ids),
                    "endpoint_decompositions": dict(point_decompositions),
                    "local_unknown_ordering": list(local_unknown_ordering),
                    "full_local_unknown_ordering": full_local_unknown_ordering,
                    "full_equations": full_equations,
                    "full_matrix_rows": full_matrix_rows,
                    "full_auxiliary_unknowns": list(line_basis_labels),
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "connector_id": line_id,
                    "connector_kind": "line",
                    "error": str(exc),
                }
            )
    return blocks, failures


def _selected_plane_family_blocks(
    *,
    grouped: dict[str, Any],
    kgeom: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    resolved_group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    line_ids: set[str],
    point_ids: set[str],
    plane_ids: set[str],
    connections: list[dict[str, Any]],
    maximal_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build md plane blocks using only actual listed line/point manifolds."""
    if not plane_ids:
        return [], []
    port = stage1_backend()
    blocks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    adjacency = _adjacency_from_connections(connections)
    for plane in grouped.get("planes", []):
        plane_id = str(plane["id"])
        if plane_id not in plane_ids:
            continue
        try:
            plane_raw = captures[plane_id]
            field = "character"
            plane_basis_labels = [
                f"{plane_id}_R{rep_index}"
                for rep_index in range(1, len(plane_raw.get(field, [])) + 1)
            ]
            plane_basis_matrix = port._exact_basis_matrix_from_capture(
                plane_raw,
                field,
                manifold_id=plane_id,
            )
            local_unknown_ordering: list[str] = []
            equations: list[dict[str, Any]] = []
            matrix_rows: list[list[int]] = []

            point_edges = sorted(
                [
                    connection
                    for connection in adjacency.get(plane_id, [])
                    if (
                        str(connection.get("relation_kind") or "") == "point_plane_geometric_incidence"
                        and (
                            str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"])
                        ) in point_ids
                        and _is_maximal_intermediate_edge(
                            plane_id,
                            str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"]),
                            maximal_ids=maximal_ids,
                        )
                    )
                ],
                key=lambda item: (
                    str(item.get("symmetry_image_used") or ""),
                    str(item.get("boundary_solution") or ""),
                    str(item.get("reciprocal_shift") or ""),
                ),
            )
            point_child_ids = [
                str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"])
                for connection in point_edges
            ]
            line_edges = sorted(
                [
                    connection
                    for connection in adjacency.get(plane_id, [])
                    if (
                        str(connection.get("relation_kind") or "") == "line_plane_geometric_incidence"
                        and (
                            str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"])
                        ) in line_ids
                        and _is_maximal_intermediate_edge(
                            plane_id,
                            str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"]),
                            maximal_ids=maximal_ids,
                        )
                    )
                ],
                key=lambda item: (
                    str(item.get("symmetry_image_used") or ""),
                    str(item.get("boundary_solution") or ""),
                    str(item.get("reciprocal_shift") or ""),
                ),
            )
            line_child_ids = [
                str(connection["right"]) if str(connection["left"]) == plane_id else str(connection["left"])
                for connection in line_edges
            ]

            child_decompositions: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for child_id, child_kind in (
                [(item, "point") for item in sorted(set(point_child_ids))]
                + [(item, "line") for item in sorted(set(line_child_ids))]
            ):
                child_raw = captures.get(child_id)
                if child_raw is None:
                    continue
                matched = port.matched_unitary_indices(plane_raw, child_raw)
                reps: list[dict[str, Any]] = []
                for rep_index in range(1, len(child_raw.get(field, [])) + 1):
                    rep_id = f"{child_id}_R{rep_index}"
                    restricted = port._exact_restriction_vector(
                        plane_raw,
                        child_raw,
                        matched,
                        field=field,
                        parent_manifold_id=plane_id,
                        child_manifold_id=child_id,
                        rep_id=rep_id,
                    )
                    coeffs_int = port.solve_unique_integer_decomposition(
                        plane_basis_matrix,
                        restricted,
                        mode="md_plane_child_decomposition",
                        manifold_id=plane_id,
                        endpoint_id=child_id,
                        rep_id=rep_id,
                        field=field,
                    )
                    reps.append(
                        {
                            "rep_id": rep_id,
                            "decomposition_on_plane_basis": {
                                label: coeff
                                for label, coeff in zip(plane_basis_labels, coeffs_int)
                                if coeff
                            },
                        }
                    )
                    local_unknown_ordering.append(rep_id)
                child_decompositions[(child_kind, child_id)] = reps

            local_unknown_ordering.extend(plane_basis_labels)
            local_index = {
                str(unknown): index
                for index, unknown in enumerate(local_unknown_ordering)
            }

            edge_records = [
                *[("point", connection) for connection in point_edges],
                *[("line", connection) for connection in line_edges],
            ]
            for edge_index, (child_kind, connection) in enumerate(edge_records, start=1):
                child_id = (
                    str(connection["right"])
                    if str(connection["left"]) == plane_id
                    else str(connection["left"])
                )
                reps = child_decompositions.get((child_kind, child_id), [])
                row_kind = (
                    "plane_point_decomposition"
                    if child_kind == "point"
                    else "plane_line_decomposition"
                )
                for basis_label in plane_basis_labels:
                    row = [0] * len(local_unknown_ordering)
                    terms: list[dict[str, Any]] = []
                    for rep in reps:
                        coeff = int(rep["decomposition_on_plane_basis"].get(basis_label, 0))
                        if coeff == 0:
                            continue
                        row[local_index[rep["rep_id"]]] += coeff
                        terms.append({"unknown": rep["rep_id"], "coeff": coeff, "side": child_kind})
                    row[local_index[basis_label]] -= 1
                    terms.append({"unknown": basis_label, "coeff": -1, "side": "plane"})
                    if any(row):
                        equations.append(
                            {
                                "point_id": child_id if child_kind == "point" else None,
                                "line_id": child_id if child_kind == "line" else None,
                                "capture_id": child_id if child_kind == "point" else None,
                                "point_coordinates": [] if child_kind == "point" else None,
                                "basis_id": f"{basis_label}_E{edge_index:02d}",
                                "row_kind": row_kind,
                                "connection_edge": dict(connection),
                                "terms": terms,
                            }
                        )
                        matrix_rows.append(row)

            monodromy_basis_orbits = _plane_monodromy_basis_orbits(
                representative_plane=plane,
                representative_raw=plane_raw,
                module=module,
                group_id=resolved_group_id,
                ssg_dict=ssg_dict,
                ctx=ctx,
                mode=mode,
            )
            for orbit_index, orbit in enumerate(monodromy_basis_orbits, start=1):
                if len(orbit) <= 1:
                    continue
                anchor_label = plane_basis_labels[orbit[0] - 1]
                for other_index, other in enumerate(orbit[1:], start=1):
                    other_label = plane_basis_labels[other - 1]
                    row = [0] * len(local_unknown_ordering)
                    row[local_index[anchor_label]] += 1
                    row[local_index[other_label]] -= 1
                    equations.append(
                        {
                            "basis_id": f"{plane_id}_MONO_{orbit_index:02d}_{other_index:02d}",
                            "row_kind": "plane_linear_monodromy_orbit_delta",
                            "point_id": None,
                            "capture_id": None,
                            "point_coordinates": [],
                            "terms": [
                                {"unknown": anchor_label, "coeff": 1, "side": "plane"},
                                {"unknown": other_label, "coeff": -1, "side": "plane"},
                            ],
                        }
                    )
                    matrix_rows.append(row)

            blocks.append(
                {
                    "plane_id": plane_id,
                    "point_ids": list(point_child_ids),
                    "line_ids": list(line_child_ids),
                    "local_unknown_ordering": local_unknown_ordering,
                    "equations": equations,
                    "matrix_rows": matrix_rows,
                    "plane_basis_labels": plane_basis_labels,
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "connector_id": plane_id,
                    "connector_kind": "plane",
                    "error": str(exc),
                }
            )
    return blocks, failures


def _build_generic_to_connected_blocks(
    *,
    grouped: dict[str, Any],
    kgeom: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    resolved_group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    component_records: list[dict[str, Any]],
    generic_ids: list[str],
    manifold_kind_by_id: dict[str, str],
    connections: list[dict[str, Any]],
    maximal_ids: set[str],
) -> list[dict[str, Any]]:
    """Build GP-to-connected-manifold blocks for every retained component.

    The md workflow writes compatibility rows edge-by-edge.  For GP this means
    we should only write restrictions along genuine geometry connections, not to
    every manifold that merely sits in the same connected component.
    """
    port = stage1_backend()
    adjacency = _adjacency_from_connections(connections)
    generic_representatives = {
        str(item["id"]): item
        for item in port.build_generic_representative_points(grouped, kgeom["runtime_ctx"])
    }
    generic_id_set = {str(item) for item in generic_ids}
    blocks: list[dict[str, Any]] = []
    for component in component_records:
        component_generic_ids = [
            str(item)
            for item in component.get("generic_ids", [])
            if str(item) in generic_id_set
        ]
        component_target_ids = [
            *[str(item) for item in component.get("point_ids", [])],
            *[str(item) for item in component.get("line_ids", [])],
            *[str(item) for item in component.get("plane_ids", [])],
        ]
        component_target_id_set = set(component_target_ids)
        for generic_id in component_generic_ids:
            generic = generic_representatives.get(generic_id)
            if generic is None:
                continue
            generic_raw = captures.get(generic_id)
            if generic_raw is None:
                generic_raw = port.capture_little_group(
                    module,
                    resolved_group_id,
                    ssg_dict,
                    ctx,
                    mode,
                    generic_id,
                    [float(Fraction(str(value))) for value in generic["sample_point"]],
                )
                captures[generic_id] = generic_raw
            field = "character"
            generic_basis_labels = [
                f"{generic_id}_R{rep_index}"
                for rep_index in range(1, len(generic_raw.get(field, [])) + 1)
            ]
            if not generic_basis_labels:
                continue
            generic_basis_matrix = port._exact_basis_matrix_from_capture(
                generic_raw,
                field,
                manifold_id=generic_id,
            )
            local_unknown_ordering: list[str] = []
            equations: list[dict[str, Any]] = []
            retained_target_ids: list[str] = []
            direct_edges = sorted(
                [
                    connection
                    for connection in adjacency.get(generic_id, [])
                    if (
                        (
                            str(connection["right"])
                            if str(connection["left"]) == generic_id
                            else str(connection["left"])
                        ) in component_target_id_set
                        and _is_maximal_intermediate_edge(
                            generic_id,
                            str(connection["right"])
                            if str(connection["left"]) == generic_id
                            else str(connection["left"]),
                            maximal_ids=maximal_ids,
                        )
                    )
                ],
                key=lambda item: (
                    component_target_ids.index(
                        str(item["right"]) if str(item["left"]) == generic_id else str(item["left"])
                    ),
                    str(item.get("symmetry_image_used") or ""),
                    str(item.get("boundary_solution") or ""),
                    str(item.get("reciprocal_shift") or ""),
                ),
            )
            unique_target_ids = sorted(
                {
                    str(connection["right"])
                    if str(connection["left"]) == generic_id
                    else str(connection["left"])
                    for connection in direct_edges
                },
                key=lambda item: component_target_ids.index(item),
            )
            for manifold_id in unique_target_ids:
                manifold_raw = captures.get(manifold_id)
                if manifold_raw is None:
                    continue
                manifold_basis_labels = [
                    f"{manifold_id}_R{rep_index}"
                    for rep_index in range(1, len(manifold_raw.get(field, [])) + 1)
                ]
                if not manifold_basis_labels:
                    continue
                for label in manifold_basis_labels:
                    if label not in local_unknown_ordering:
                        local_unknown_ordering.append(label)
            for edge_index, connection in enumerate(direct_edges, start=1):
                manifold_id = (
                    str(connection["right"])
                    if str(connection["left"]) == generic_id
                    else str(connection["left"])
                )
                manifold_raw = captures.get(manifold_id)
                if manifold_raw is None:
                    continue
                manifold_kind = str(manifold_kind_by_id.get(manifold_id) or "manifold")
                matched = port.matched_unitary_indices(generic_raw, manifold_raw)
                manifold_basis_labels = [
                    f"{manifold_id}_R{rep_index}"
                    for rep_index in range(1, len(manifold_raw.get(field, [])) + 1)
                ]
                if not manifold_basis_labels:
                    continue
                retained_target_ids.append(manifold_id)
                coeffs_by_generic_label = {
                    basis_label: {}
                    for basis_label in generic_basis_labels
                }
                for rep_index, rep_label in enumerate(manifold_basis_labels, start=1):
                    restricted = port._exact_restriction_vector(
                        generic_raw,
                        manifold_raw,
                        matched,
                        field=field,
                        parent_manifold_id=generic_id,
                        child_manifold_id=manifold_id,
                        rep_id=rep_label,
                    )
                    coeffs = port.solve_unique_integer_decomposition(
                        generic_basis_matrix,
                        restricted,
                        mode=mode,
                        manifold_id=generic_id,
                        endpoint_id=manifold_id,
                        rep_id=rep_label,
                        field=field,
                    )
                    for basis_label, coeff in zip(generic_basis_labels, coeffs):
                        coeff_int = int(coeff)
                        if coeff_int == 0:
                            continue
                        coeffs_by_generic_label[basis_label][rep_label] = coeff_int
                for generic_basis_index, basis_label in enumerate(generic_basis_labels, start=1):
                    support = coeffs_by_generic_label.get(basis_label) or {}
                    if not support:
                        continue
                    equations.append(
                        {
                            "basis_id": f"{generic_id}__{manifold_id}_E{edge_index:02d}_G{generic_basis_index:02d}",
                            "row_kind": f"generic_{manifold_kind}_decomposition",
                            "generic_id": generic_id,
                            "target_manifold_id": manifold_id,
                            "target_manifold_kind": manifold_kind,
                            "connection_edge": dict(connection),
                            "generic_basis_label": basis_label,
                            "terms": [
                                *[
                                    {"unknown": rep_label, "coeff": int(coeff), "side": manifold_kind}
                                    for rep_label, coeff in support.items()
                                ],
                                {"unknown": basis_label, "coeff": -1, "side": "generic"},
                            ],
                        }
                    )
            if not equations:
                continue
            local_unknown_ordering.extend(
                [label for label in generic_basis_labels if label not in local_unknown_ordering]
            )
            matrix_rows = _build_block_matrix_rows_from_equations(
                local_unknown_ordering,
                equations,
            )
            blocks.append(
                {
                    "generic_id": generic_id,
                    "local_unknown_ordering": local_unknown_ordering,
                    "generic_basis_labels": generic_basis_labels,
                    "equations": equations,
                    "matrix_rows": matrix_rows,
                    "target_manifold_ids": retained_target_ids,
                }
            )
    return blocks


def _selected_generic_blocks(
    *,
    grouped: dict[str, Any],
    kgeom: dict[str, Any],
    captures: dict[str, Any],
    module: Any,
    resolved_group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
    component_records: list[dict[str, Any]],
    generic_ids: list[str],
    manifold_kind_by_id: dict[str, str],
    connections: list[dict[str, Any]],
    maximal_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build generic blocks component-by-component.

    The latest md treats GP as an ordinary retained intermediate manifold: it
    must enter the full compatibility matrix before any algebraic projection is
    attempted.  We therefore keep generic blocks whenever the retained shell has
    a generic manifold, but we still split by connected component so one GP block
    never spuriously ties together disconnected maximal shells.
    """
    if not generic_ids:
        return [], []
    try:
        blocks = _build_generic_to_connected_blocks(
            grouped=grouped,
            kgeom=kgeom,
            captures=captures,
            module=module,
            resolved_group_id=resolved_group_id,
            ssg_dict=ssg_dict,
            ctx=ctx,
            mode=mode,
            component_records=component_records,
            generic_ids=generic_ids,
            manifold_kind_by_id=manifold_kind_by_id,
            connections=connections,
            maximal_ids=maximal_ids,
        )
    except Exception as exc:
        return [], [
            {
                "connector_id": ",".join(generic_ids),
                "connector_kind": "generic",
                "component_maximal_ids": [
                    str(item)
                    for component in component_records
                    for item in component.get("maximal_ids", [])
                ],
                "error": str(exc),
            }
        ]
    return blocks, []


def _keep_unknowns_for_maximal_manifolds(
    *,
    maximal_ids: list[str],
    captures: dict[str, Any],
) -> list[str]:
    """Collect the maximal-manifold unknown basis kept after exact elimination."""
    keep_unknowns: list[str] = []
    for manifold_id in maximal_ids:
        raw = captures.get(str(manifold_id))
        if raw is None:
            continue
        keep_unknowns.extend(
            f"{manifold_id}_R{rep_index}"
            for rep_index in range(
                1,
                len(list(raw.get("rep_degree", []))) + 1,
            )
    )
    return keep_unknowns


def _normalized_line_orbits(
    manifold_id: str,
    raw: dict[str, Any],
) -> list[list[str]]:
    """Normalize captured line monodromy orbits onto the explicit local labels."""
    raw_labels = [
        f"{manifold_id}_R{rep_index}"
        for rep_index in range(1, len(list(raw.get("rep_degree", []))) + 1)
    ]
    if not raw_labels:
        return []
    raw_orbits = list(raw.get("line_monodromy_basis_orbits", []))
    if not raw_orbits:
        return [[label] for label in raw_labels]
    label_set = set(raw_labels)
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
    for label in raw_labels:
        if label not in seen:
            normalized.append([label])
    return normalized


def _normalized_plane_orbits(
    *,
    manifold_id: str,
    plane_obj: dict[str, Any],
    raw: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
) -> list[list[str]]:
    """Recover maximal-plane branch orbits from the copied workflow-v2 helper."""
    raw_labels = [
        f"{manifold_id}_R{rep_index}"
        for rep_index in range(1, len(list(raw.get("rep_degree", []))) + 1)
    ]
    if not raw_labels:
        return []
    raw_orbits = _plane_monodromy_basis_orbits(
        representative_plane=plane_obj,
        representative_raw=raw,
        module=module,
        group_id=group_id,
        ssg_dict=ssg_dict,
        ctx=ctx,
        mode=mode,
    )
    if not raw_orbits:
        return [[label] for label in raw_labels]
    normalized: list[list[str]] = []
    seen: set[str] = set()
    for orbit in raw_orbits:
        cleaned: list[str] = []
        for rep_index in orbit:
            if not 1 <= int(rep_index) <= len(raw_labels):
                continue
            label = raw_labels[int(rep_index) - 1]
            if label in seen:
                continue
            seen.add(label)
            cleaned.append(label)
        if cleaned:
            normalized.append(cleaned)
    for label in raw_labels:
        if label not in seen:
            normalized.append([label])
    return normalized


def _build_maximal_branch_spec(
    *,
    maximal_manifolds: list[dict[str, Any]],
    captures: dict[str, Any],
    grouped: dict[str, Any],
    module: Any,
    group_id: str,
    ssg_dict: dict[str, Any],
    ctx: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """Translate maximal-manifold local-irrep labels into md-style branch variables.

    The latest md defines BS variables as global branches on maximal manifolds.
    For maximal lines we can already realize that semantics directly from the
    captured line monodromy orbits.  Other maximal kinds currently stay as
    singleton branch orbits when the retained shell carries no nontrivial
    monodromy identification for them.
    """
    raw_to_branch: dict[str, str] = {}
    branch_unknowns: list[str] = []
    branch_records: list[dict[str, Any]] = []
    raw_keep_unknowns: list[str] = []
    plane_lookup = {
        str(item["id"]): item
        for item in grouped.get("planes", [])
    }
    for manifold in maximal_manifolds:
        manifold_id = str(manifold["id"])
        manifold_kind = str(manifold.get("kind") or "")
        raw = captures.get(manifold_id) or {}
        rep_degrees = [int(value) for value in raw.get("rep_degree", [])]
        raw_labels = [
            f"{manifold_id}_R{rep_index}"
            for rep_index in range(1, len(rep_degrees) + 1)
        ]
        raw_keep_unknowns.extend(raw_labels)
        if manifold_kind == "line":
            orbit_labels = _normalized_line_orbits(manifold_id, raw)
            branch_semantics = "line_monodromy_global_branch"
        elif manifold_kind == "plane":
            orbit_labels = _normalized_plane_orbits(
                manifold_id=manifold_id,
                plane_obj=plane_lookup.get(manifold_id) or {"id": manifold_id, "_basis": [], "sample_point": []},
                raw=raw,
                module=module,
                group_id=group_id,
                ssg_dict=ssg_dict,
                ctx=ctx,
                mode=mode,
            )
            branch_semantics = "plane_monodromy_global_branch"
        elif manifold_kind == "point":
            orbit_labels = [[label] for label in raw_labels]
            branch_semantics = "point_local_irrep_equals_global_branch"
        else:
            orbit_labels = [[label] for label in raw_labels]
            branch_semantics = "singleton_global_branch_for_maximal_manifold"
        rep_degree_by_label = {
            label: rep_degrees[index]
            for index, label in enumerate(raw_labels)
        }
        for orbit_index, orbit in enumerate(orbit_labels, start=1):
            branch_id = f"{manifold_id}_B{orbit_index}"
            branch_unknowns.append(branch_id)
            for label in orbit:
                raw_to_branch[label] = branch_id
            branch_records.append(
                {
                    "branch_id": branch_id,
                    "host_manifold_id": manifold_id,
                    "host_maximal_manifold": manifold_id,
                    "host_manifold_kind": manifold_kind,
                    "local_irrep_orbit": list(orbit),
                    "local_irrep_labels": list(orbit),
                    "representative_local_irrep": orbit[0] if orbit else None,
                    "orbit_size": len(orbit),
                    "monodromy_collapsed": len(orbit) > 1,
                    "branch_band_degree": sum(
                        int(rep_degree_by_label.get(label, 0))
                        for label in orbit
                    ),
                    "local_rep_degrees": [
                        int(rep_degree_by_label.get(label, 0))
                        for label in orbit
                    ],
                    "branch_semantics": branch_semantics,
                }
            )
    return {
        "raw_to_branch": raw_to_branch,
        "branch_unknowns": branch_unknowns,
        "branch_records": branch_records,
        "raw_keep_unknowns": raw_keep_unknowns,
    }


def _compress_global_unknowns(
    matrix_payload: dict[str, Any],
    *,
    unknown_merge_map: dict[str, str],
    source_type: str,
) -> dict[str, Any]:
    """Merge selected columns exactly, preserving one common full row system.

    This is the column-space counterpart of the md branch definition: several
    local-irrep columns on a maximal manifold are identified as one global-branch
    variable.  Rows are not filtered here; only the variable language changes.
    """
    original_unknown_ordering = [
        str(unknown) for unknown in matrix_payload.get("global_unknown_ordering", [])
    ]
    compressed_unknown_ordering: list[str] = []
    compressed_index: dict[str, int] = {}
    for unknown in original_unknown_ordering:
        target = str(unknown_merge_map.get(unknown, unknown))
        if target in compressed_index:
            continue
        compressed_index[target] = len(compressed_unknown_ordering)
        compressed_unknown_ordering.append(target)

    compressed_rows: list[dict[str, Any]] = []
    for row_record in matrix_payload.get("global_matrix_rows", []):
        original_row = [int(value) for value in row_record.get("matrix_row", [])]
        compressed_row = [0] * len(compressed_unknown_ordering)
        for column_index, coeff in enumerate(original_row):
            if coeff == 0:
                continue
            source_unknown = original_unknown_ordering[column_index]
            target_unknown = str(unknown_merge_map.get(source_unknown, source_unknown))
            compressed_row[compressed_index[target_unknown]] += int(coeff)
        compressed_rows.append(
            {
                **row_record,
                "matrix_row": compressed_row,
                "column_compression_source_type": source_type,
            }
        )

    return {
        **matrix_payload,
        "global_unknown_ordering": compressed_unknown_ordering,
        "global_matrix_rows": compressed_rows,
        "global_matrix": [list(row["matrix_row"]) for row in compressed_rows],
        "matrix_shape": [
            len(compressed_rows),
            len(compressed_unknown_ordering),
        ],
        "column_compression_source_type": source_type,
        "original_global_unknown_ordering": original_unknown_ordering,
        "unknown_merge_map": dict(unknown_merge_map),
    }


def _reorder_global_unknowns(
    matrix_payload: dict[str, Any],
    *,
    leading_unknowns: list[str],
) -> dict[str, Any]:
    original_ordering = [str(item) for item in matrix_payload.get("global_unknown_ordering", [])]
    leading = [str(item) for item in leading_unknowns if str(item) in original_ordering]
    trailing = [item for item in original_ordering if item not in set(leading)]
    reordered = leading + trailing
    if reordered == original_ordering:
        return {
            **matrix_payload,
            "global_unknown_ordering": reordered,
            "global_matrix_rows": [
                {**row, "matrix_row": list(row.get("matrix_row", []))}
                for row in matrix_payload.get("global_matrix_rows", [])
            ],
            "global_matrix": [list(row) for row in matrix_payload.get("global_matrix", [])],
        }
    original_index = {unknown: index for index, unknown in enumerate(original_ordering)}
    reordered_rows = []
    for row in matrix_payload.get("global_matrix_rows", []):
        original_row = [int(value) for value in row.get("matrix_row", [])]
        reordered_rows.append(
            {
                **row,
                "matrix_row": [original_row[original_index[unknown]] for unknown in reordered],
            }
        )
    return {
        **matrix_payload,
        "global_unknown_ordering": reordered,
        "global_matrix_rows": reordered_rows,
        "global_matrix": [list(row["matrix_row"]) for row in reordered_rows],
        "matrix_shape": [len(reordered_rows), len(reordered)],
    }


def build_md_target_rewrite(
    group_id: str,
    mode: str = "single",
    *,
    include_generic: bool = True,
) -> dict[str, Any]:
    """Execute the md geometry-to-BS workflow on the standalone rewrite path."""
    resolved_group_id, shared, kgeom, module, ctx, captures = _prepare_capture_context(group_id, mode)
    grouped = kgeom["grouped"]
    port = stage1_backend()
    geometry_report = _build_md_geometry_report(
        requested_group_id=str(group_id),
        resolved_group_id=resolved_group_id,
        shared=shared,
        kgeom=kgeom,
        ctx=ctx,
        captures=captures,
        mode=mode,
    )

    maximal_ids = [
        str(item["id"])
        for item in geometry_report["maximal_manifolds"]
    ]
    retained_shell = _retained_component_shell(
        geometry_report=geometry_report,
        grouped=grouped,
    )
    retained_point_ids = set(retained_shell["retained_point_ids"])
    retained_line_ids = set(retained_shell["retained_line_ids"])
    retained_plane_ids = set(retained_shell["retained_plane_ids"])
    retained_generic_ids = list(retained_shell["retained_generic_ids"])
    component_records = list(retained_shell["component_records"])
    manifold_kind_by_id = {
        str(item["id"]): str(item.get("kind") or "")
        for item in geometry_report["manifolds"]
    }
    line_blocks, line_failures = _selected_line_blocks(
        grouped=grouped,
        captures=captures,
        line_ids=retained_line_ids,
        point_ids=retained_point_ids,
        connections=list(geometry_report["connections_full"]),
        maximal_ids=set(maximal_ids),
    )
    point_ids = list(retained_point_ids)
    full_compatibility = (
        _assemble_line_compatibility(line_blocks, point_ids)
        if line_blocks
        else _empty_full_compatibility()
    )

    plane_blocks, plane_failures = _selected_plane_family_blocks(
        grouped=grouped,
        kgeom=kgeom,
        captures=captures,
        module=module,
        resolved_group_id=resolved_group_id,
        ssg_dict=port.load_ssg_dict(resolved_group_id),
        ctx=ctx,
        mode=mode,
        line_ids=retained_line_ids,
        point_ids=retained_point_ids,
        plane_ids=retained_plane_ids,
        connections=list(geometry_report["connections_full"]),
        maximal_ids=set(maximal_ids),
    )
    if plane_blocks:
        full_compatibility = _append_plane_blocks_to_compatibility(
            full_compatibility,
            plane_blocks,
        )

    keep_unknowns = _keep_unknowns_for_maximal_manifolds(
        maximal_ids=maximal_ids,
        captures=captures,
    )
    if not keep_unknowns:
        return {
            "Metadata": {
                "generated_at": now_iso(),
                "requested_group": str(group_id),
                "resolved_group": resolved_group_id,
                "mode": mode,
            },
            "blocker_stage": "md_target_rewrite_no_maximal_unknowns",
            "blocker": "no maximal-manifold unknowns were available for projection",
            "maximal_ids": maximal_ids,
            "retained_manifold_ids": {
                "line": sorted(retained_line_ids),
                "plane": sorted(retained_plane_ids),
                "generic": list(retained_generic_ids),
            },
            "block_failures": line_failures + plane_failures,
        }

    if not full_compatibility.get("global_unknown_ordering"):
        full_compatibility = _seed_full_compatibility_with_unknowns(keep_unknowns)

    generic_blocks: list[dict[str, Any]] = []
    generic_failures: list[dict[str, Any]] = []
    if include_generic:
        generic_blocks, generic_failures = _selected_generic_blocks(
            grouped=grouped,
            kgeom=kgeom,
            captures=captures,
            module=module,
            resolved_group_id=resolved_group_id,
            ssg_dict=port.load_ssg_dict(resolved_group_id),
            ctx=ctx,
            mode=mode,
            component_records=component_records,
            generic_ids=retained_generic_ids,
            manifold_kind_by_id=manifold_kind_by_id,
            connections=list(geometry_report["connections_full"]),
            maximal_ids=set(maximal_ids),
        )
        if generic_blocks:
            full_compatibility = _append_generic_blocks_to_compatibility(
                full_compatibility,
                generic_blocks,
            )

    maximal_branch_spec = _build_maximal_branch_spec(
        maximal_manifolds=list(geometry_report["maximal_manifolds"]),
        captures=captures,
        grouped=grouped,
        module=module,
        group_id=resolved_group_id,
        ssg_dict=port.load_ssg_dict(resolved_group_id),
        ctx=ctx,
        mode=mode,
    )
    compressed_compatibility = _compress_global_unknowns(
        full_compatibility,
        unknown_merge_map=maximal_branch_spec["raw_to_branch"],
        source_type="md_target_rewrite_maximal_branch_compression",
    )
    compatibility_matrix = _reorder_global_unknowns(
        compressed_compatibility,
        leading_unknowns=list(maximal_branch_spec["branch_unknowns"]),
    )
    projected = port.exact_project_keep_unknowns(
        compatibility_matrix,
        keep_unknowns=maximal_branch_spec["branch_unknowns"],
        source_type="md_target_rewrite_projection",
    )
    bs_analysis = port.analyze_kernel(projected)
    md_validations = _md_validation_report(
        geometry_report=geometry_report,
        retained_shell=retained_shell,
        full_compatibility=full_compatibility,
        projected=projected,
    )

    result = {
        "Metadata": {
            "generated_at": now_iso(),
            "requested_group": str(group_id),
            "resolved_group": resolved_group_id,
            "mode": mode,
            "coordinate_system": str(geometry_report.get("coordinate_system") or ""),
            "geometry_construction_provenance": dict(shared.get("geometry_construction_provenance") or {}),
        },
        "SeitzOperations": _render_seitz_operations(kgeom["runtime_ctx"]),
        "OperationChecks": _validate_seitz_operations(kgeom["runtime_ctx"]),
        "PointGroup": _render_point_group_rotations(kgeom["runtime_ctx"]),
        "M_all": [
            _public_manifold_record(item)
            for item in geometry_report["manifolds"]
        ],
        "M_max": _decorate_maximal_manifolds_with_branch_counts(
            list(geometry_report["maximal_manifolds"]),
            list(maximal_branch_spec["branch_records"]),
        ),
        "M_int": list(retained_shell["intermediate_manifolds"]),
        "Connections": [
            _public_connection_record(item)
            for item in geometry_report["connections_full"]
        ],
        "X_BS": [
            _public_branch_record(record)
            for record in maximal_branch_spec["branch_records"]
        ],
        "LocalIrreps": _render_local_irreps(
            manifolds=list(geometry_report["maximal_manifolds"]) + list(retained_shell["intermediate_manifolds"]),
            captures=captures,
        ),
        "LocalIrrepGlobalBranchTable": _render_local_irrep_branch_table(
            manifolds=list(geometry_report["maximal_manifolds"]) + list(retained_shell["intermediate_manifolds"]),
            captures=captures,
            branch_records=list(maximal_branch_spec["branch_records"]),
        ),
        "CompatibilityVariableOrdering": list(compatibility_matrix.get("global_unknown_ordering", [])),
        "CompatibilityVariableBlocks": {
            "x": list(maximal_branch_spec["branch_unknowns"]),
            "y": [
                str(item)
                for item in compatibility_matrix.get("global_unknown_ordering", [])
                if str(item) not in set(maximal_branch_spec["branch_unknowns"])
            ],
        },
        "CompatibilityMatrix": [list(row) for row in compatibility_matrix.get("global_matrix", [])],
        "CompatibilityEquations": _render_equation_records(compatibility_matrix),
        "BSVariableOrdering": list(projected.get("global_unknown_ordering", [])),
        "BSConstraints": _render_equation_records(projected),
        "BSBasis": _render_basis_vectors(bs_analysis),
        "dBS": len(bs_analysis.get("basis_vectors", [])),
    }
    if md_validations.get("passed") is not True:
        result["WorkflowValidations"] = md_validations
    block_failures = [
            *line_failures,
            *plane_failures,
            *generic_failures,
        ]
    if block_failures:
        result["block_failures"] = block_failures
    return result
