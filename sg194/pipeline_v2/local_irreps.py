#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TARGET_GROUP = "194.1.1.1"
REFERENCE_GROUP = "10.4.1.31"

INVENTORY_MD = ROOT / "sg194_nonabelian_site_symmetry_inventory.md"
INVENTORY_JSON = ROOT / "sg194_nonabelian_site_symmetry_inventory.json"
SINGLE_LIBRARY_JSON = ROOT / "sg194_single_local_irrep_library.json"
DOUBLE_LIBRARY_JSON = ROOT / "sg194_double_local_corep_library.json"


def load_stage1_module():
    from . import runtime_backend_free

    return runtime_backend_free


def json_default(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": round(float(value.real), 12), "imag": round(float(value.imag), 12)}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True, default=json_default) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def complex_close(a: complex, b: complex, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol


def complex_to_string(value: complex, tol: float = 1e-8) -> str:
    candidates: list[tuple[complex, str]] = [
        (0j, "0"),
        (1 + 0j, "1"),
        (-1 + 0j, "-1"),
        (1j, "+i"),
        (-1j, "-i"),
        (2 + 0j, "2"),
        (-2 + 0j, "-2"),
        (2j, "+2i"),
        (-2j, "-2i"),
        (0.5 + math.sqrt(3) * 0.5j, "exp(+i*pi/3)"),
        (0.5 - math.sqrt(3) * 0.5j, "exp(-i*pi/3)"),
        (-0.5 + math.sqrt(3) * 0.5j, "exp(+2i*pi/3)"),
        (-0.5 - math.sqrt(3) * 0.5j, "exp(-2i*pi/3)"),
        (math.sqrt(3) + 0j, "sqrt(3)"),
        (-math.sqrt(3) + 0j, "-sqrt(3)"),
        (math.sqrt(3) * 1j, "+i*sqrt(3)"),
        (-math.sqrt(3) * 1j, "-i*sqrt(3)"),
    ]
    for candidate, label in candidates:
        if complex_close(value, candidate, tol):
            return label
    rounded = complex(round(float(value.real), 12), round(float(value.imag), 12))
    return str(rounded)


def normalize_complex(value: complex, tol: float = 1e-10) -> complex:
    real = 0.0 if abs(value.real) < tol else float(value.real)
    imag = 0.0 if abs(value.imag) < tol else float(value.imag)
    return complex(round(real, 12), round(imag, 12))


def group_local_record(
    letter: str,
    entry: dict[str, Any],
    bridge_entry: dict[str, Any],
    ctx_single: dict[str, Any],
    compose_fn,
    inverse_fn,
) -> dict[str, Any]:
    stabilizer = list(bridge_entry["stabilizer_indices"])
    local_index = {index: pos for pos, index in enumerate(stabilizer)}
    mult_table = [
        [local_index[compose_fn(left, right)] for right in stabilizer]
        for left in stabilizer
    ]
    inverse_local = [local_index[inverse_fn[index]] for index in stabilizer]
    rotation_orders = []
    rotation_dets = []
    rotation_traces = []
    for index in stabilizer:
        matrix = np.array(ctx_single["ssg"].rotC[index], dtype=int)
        rotation_dets.append(int(round(np.linalg.det(matrix))))
        rotation_traces.append(int(np.trace(matrix)))
        current = np.eye(3, dtype=int)
        order = None
        for power in range(1, 25):
            current = current @ matrix
            if np.array_equal(current, np.eye(3, dtype=int)):
                order = power
                break
        rotation_orders.append(order)

    abelian = all(mult_table[i][j] == mult_table[j][i] for i in range(len(stabilizer)) for j in range(len(stabilizer)))

    classes: list[list[int]] = []
    seen = set()
    for g in range(len(stabilizer)):
        if g in seen:
            continue
        cls = sorted({mult_table[mult_table[x][g]][inverse_local[x]] for x in range(len(stabilizer))})
        seen.update(cls)
        classes.append(cls)

    center = [
        idx
        for idx in range(len(stabilizer))
        if all(mult_table[idx][j] == mult_table[j][idx] for j in range(len(stabilizer)))
    ]
    det_plus = [idx for idx, det in enumerate(rotation_dets) if det == 1]
    det_minus = [idx for idx, det in enumerate(rotation_dets) if det == -1]
    inversion_like = [
        idx
        for idx, (order, det, trace) in enumerate(zip(rotation_orders, rotation_dets, rotation_traces))
        if order == 2 and det == -1 and trace == -3
    ]
    mirror_like = [
        idx
        for idx, (order, det, trace) in enumerate(zip(rotation_orders, rotation_dets, rotation_traces))
        if order == 2 and det == -1 and trace == 1
    ]
    c3_like = [
        idx
        for idx, (order, det, trace) in enumerate(zip(rotation_orders, rotation_dets, rotation_traces))
        if order == 3 and det == 1 and trace == 0
    ]

    counter = Counter((rotation_orders[i], rotation_dets[i], rotation_traces[i]) for i in range(len(stabilizer)))
    class_sizes = sorted(len(cls) for cls in classes)

    site_field = str(entry.get("site_symmetry") or "")
    type_key = "unknown"
    type_label = "unknown"
    nonabelian = not abelian
    label_scheme = "generic"
    parity_local = None
    order = len(stabilizer)

    if order == 1:
        type_key = "C1"
        type_label = "1"
        label_scheme = "trivial"
    elif order == 2:
        nontrivial = next(idx for idx in range(1, 2))
        if rotation_dets[nontrivial] == 1:
            type_key = "C2"
            type_label = "2"
            label_scheme = "A/B"
        else:
            type_key = "Cs"
            type_label = "m"
            label_scheme = "prime"
    elif order == 4 and abelian:
        if inversion_like:
            type_key = "C2h"
            type_label = "2/m"
            label_scheme = "gu"
            parity_local = inversion_like[0]
        else:
            type_key = "C2v"
            type_label = "mm2"
            label_scheme = "A/B"
    elif order == 6 and class_sizes == [1, 2, 3]:
        type_key = "C3v"
        type_label = "3m"
        label_scheme = "A/E"
    elif order == 12 and class_sizes == [1, 1, 2, 2, 3, 3]:
        if inversion_like:
            type_key = "D3d_like"
            type_label = "-3m"
            label_scheme = "gu"
            parity_local = inversion_like[0]
        elif mirror_like:
            type_key = "D3h_like"
            type_label = "-6m2"
            label_scheme = "prime"
            central_mirrors = [idx for idx in mirror_like if idx in center]
            parity_local = central_mirrors[0] if central_mirrors else mirror_like[0]
        else:
            type_key = "S3xC2_like"
            type_label = "order-12 nonabelian"
            label_scheme = "generic"

    blocker_relevance = "not_blocking"
    if order == 1:
        blocker_relevance = "not_blocking"
    elif abelian:
        blocker_relevance = "secondary_abelian_followon"
    else:
        blocker_relevance = "primary_nonabelian_blocker"

    return {
        "family_id": letter,
        "representative_coordinate": entry["representative_coordinate"],
        "representative_coordinate_raw": entry.get("x0"),
        "dimension": int(entry["dim"]),
        "multiplicity": int(entry["mult"]),
        "site_symmetry_label": entry.get("site_symmetry"),
        "site_symmetry_custom": entry.get("site_symmetry_custom"),
        "unitary_site_symmetry": entry.get("unitary_site_symmetry"),
        "group_order": order,
        "stabilizer_size": int(bridge_entry["bridge_stabilizer_size"]),
        "unitary_count": int(bridge_entry["bridge_unitary_count"]),
        "antiunitary_count": int(bridge_entry["bridge_antiunitary_count"]),
        "stabilizer_indices": stabilizer,
        "rotation_orders": rotation_orders,
        "rotation_determinants": rotation_dets,
        "rotation_traces": rotation_traces,
        "class_sizes": class_sizes,
        "center_local_indices": center,
        "det_plus_local_indices": det_plus,
        "det_minus_local_indices": det_minus,
        "c3_like_local_indices": c3_like,
        "inversion_like_local_indices": inversion_like,
        "mirror_like_local_indices": mirror_like,
        "signature_counter": {str(key): count for key, count in sorted(counter.items())},
        "abelian": abelian,
        "nonabelian": nonabelian,
        "blocker_relevance": blocker_relevance,
        "site_symmetry_type_key": type_key,
        "site_symmetry_type_label": type_label,
        "label_scheme": label_scheme,
        "parity_element_local_index": parity_local,
        "multiplication_table_local": mult_table,
        "inverse_local": inverse_local,
        "conjugacy_classes_local": classes,
    }


def det_plus_subgroup(record: dict[str, Any]) -> list[int]:
    det_plus = list(record["det_plus_local_indices"])
    if not det_plus:
        return [0]
    return det_plus


def s3_class_tag(local_index: int, record: dict[str, Any]) -> str:
    order = record["rotation_orders"][local_index]
    det = record["rotation_determinants"][local_index]
    if local_index == 0:
        return "E"
    if det == 1 and order == 3:
        return "C3"
    return "Sigma"


def _count_distinct_complex(values: list[complex], tol: float = 1e-8) -> int:
    clusters: list[complex] = []
    for value in values:
        if any(abs(value - existing) <= tol for existing in clusters):
            continue
        clusters.append(value)
    return len(clusters)


def generic_abelian_single_characters_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    order = record["group_order"]
    mult_table = record["multiplication_table_local"]
    cocycle = np.ones((order, order), dtype=complex)
    left_regular = build_left_regular_matrices(mult_table, cocycle)

    trials = [
        [complex(index + 1, (index + 1) ** 2) for index in range(order)],
        [complex(2 * index + 1, index + 1) for index in range(order)],
        [complex(index + 1, 3 * index + 2) for index in range(order)],
        [complex(index + 1, (-1) ** index * (index + 2)) for index in range(order)],
    ]

    eigenvectors = None
    for coeffs in trials:
        combo = np.zeros((order, order), dtype=complex)
        for local_index, coeff in enumerate(coeffs):
            combo += coeff * left_regular[local_index]
        eigenvalues, trial_vectors = np.linalg.eig(combo)
        if _count_distinct_complex([complex(value) for value in eigenvalues]) == order:
            eigenvectors = trial_vectors
            break
    if eigenvectors is None:
        raise ValueError("unable to separate abelian local-group characters generically")

    irreps = []
    for column in range(order):
        vector = eigenvectors[:, column]
        norm = np.vdot(vector, vector)
        if abs(norm) <= 1e-12:
            continue
        chars = []
        for regular in left_regular:
            value = np.vdot(vector, regular @ vector) / norm
            chars.append(normalize_complex(value))
        irreps.append({"dimension": 1, "character": chars})

    unique_irreps: list[dict[str, Any]] = []
    for item in irreps:
        if any(
            all(complex_close(left, right) for left, right in zip(item["character"], existing["character"]))
            for existing in unique_irreps
        ):
            continue
        unique_irreps.append(item)

    if len(unique_irreps) != order:
        raise ValueError(
            f"expected {order} distinct abelian single-group characters, got {len(unique_irreps)}"
        )

    unique_irreps.sort(
        key=lambda item: [complex_to_string(value) for value in item["character"]]
    )
    labeled = []
    for index, item in enumerate(unique_irreps, start=1):
        labeled.append(
            {
                "label": f"chi_{index:02d}",
                "dimension": 1,
                "character": item["character"],
                "label_scheme": "generic_abelian_regular_character",
            }
        )
    return labeled


def generic_regular_single_characters_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    order = record["group_order"]
    mult_table = record["multiplication_table_local"]
    cocycle = np.ones((order, order), dtype=complex)
    blocks = twisted_isotypic_blocks(mult_table, cocycle)
    blocks.sort(
        key=lambda item: (
            int(item["dimension"]),
            [complex_to_string(value) for value in item["character"]],
        )
    )
    labeled = []
    for index, block in enumerate(blocks, start=1):
        labeled.append(
            {
                "label": f"chi_{int(block['dimension'])}d_{index:02d}",
                "dimension": int(block["dimension"]),
                "character": list(block["character"]),
                "label_scheme": "generic_regular_decomposition",
            }
        )
    return labeled


def ordinary_single_characters_for_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    order = record["group_order"]
    type_key = record["site_symmetry_type_key"]
    dets = record["rotation_determinants"]
    orders = record["rotation_orders"]
    local_irreps: list[dict[str, Any]] = []

    if type_key == "C1":
        chars = [1 + 0j]
        local_irreps.append({"label": "A", "dimension": 1, "character": chars})
    elif type_key in {"C2", "Cs"}:
        generator = 1
        pos_label, neg_label = ("A", "B") if type_key == "C2" else ("A'", "A''")
        for label, value in ((pos_label, 1), (neg_label, -1)):
            chars = [1 + 0j, complex(value)]
            local_irreps.append({"label": label, "dimension": 1, "character": chars, "generator_local_index": generator})
    elif type_key == "C2h":
        parity = int(record["parity_element_local_index"])
        c2 = next(idx for idx in range(order) if idx not in (0, parity) and dets[idx] == 1)
        labels = [
            ("Ag", 1, 1),
            ("Bg", -1, 1),
            ("Au", 1, -1),
            ("Bu", -1, -1),
        ]
        for label, c2_value, parity_value in labels:
            chars = []
            for idx in range(order):
                if idx == 0:
                    chars.append(1 + 0j)
                elif idx == c2:
                    chars.append(complex(c2_value))
                elif idx == parity:
                    chars.append(complex(parity_value))
                else:
                    chars.append(complex(c2_value * parity_value))
            local_irreps.append({"label": label, "dimension": 1, "character": chars, "c2_local_index": c2, "parity_local_index": parity})
    elif type_key == "C2v":
        c2 = next(idx for idx in range(order) if idx != 0 and dets[idx] == 1)
        mirrors = [idx for idx in range(order) if idx not in (0, c2)]
        m1 = mirrors[0]
        m2 = mirrors[1]
        labels = [
            ("A1", 1, 1),
            ("A2", 1, -1),
            ("B1", -1, 1),
            ("B2", -1, -1),
        ]
        for label, c2_value, m1_value in labels:
            chars = []
            for idx in range(order):
                if idx == 0:
                    chars.append(1 + 0j)
                elif idx == c2:
                    chars.append(complex(c2_value))
                elif idx == m1:
                    chars.append(complex(m1_value))
                else:
                    chars.append(complex(c2_value * m1_value))
            local_irreps.append({"label": label, "dimension": 1, "character": chars, "c2_local_index": c2, "mirror_local_index": m1, "other_mirror_local_index": m2})
    elif type_key == "C3v":
        template = {
            "A1": (1, 1, 1),
            "A2": (1, 1, -1),
            "E": (2, -1, 0),
        }
        for label, (chi_e, chi_c3, chi_sigma) in template.items():
            chars = []
            for idx in range(order):
                tag = s3_class_tag(idx, record)
                chars.append(complex({"E": chi_e, "C3": chi_c3, "Sigma": chi_sigma}[tag]))
            local_irreps.append({"label": label, "dimension": int(chi_e), "character": chars})
    elif type_key in {"D3d_like", "D3h_like"}:
        parity = int(record["parity_element_local_index"])
        subgroup = det_plus_subgroup(record)
        subgroup_set = set(subgroup)
        parity_label_pos, parity_label_neg = ("g", "u") if type_key == "D3d_like" else ("'", "''")
        s3_templates = [
            ("A1", 1, 1, 1),
            ("A2", 1, 1, -1),
            ("E", 2, -1, 0),
        ]
        parity_templates = [(parity_label_pos, 1), (parity_label_neg, -1)]
        parity_multiply = record["multiplication_table_local"][parity]
        for base_label, chi_e, chi_c3, chi_sigma in s3_templates:
            for parity_suffix, parity_value in parity_templates:
                label = f"{base_label}{parity_suffix}"
                chars = []
                for idx in range(order):
                    parity_sign = 1
                    reduced = idx
                    if idx not in subgroup_set:
                        reduced = parity_multiply[idx]
                        parity_sign = parity_value
                    tag = s3_class_tag(reduced, record)
                    base = {"E": chi_e, "C3": chi_c3, "Sigma": chi_sigma}[tag]
                    chars.append(complex(base * parity_sign))
                local_irreps.append({"label": label, "dimension": int(chi_e), "character": chars, "parity_local_index": parity})
    elif record["abelian"]:
        local_irreps.extend(generic_abelian_single_characters_for_record(record))
    else:
        local_irreps.extend(generic_regular_single_characters_for_record(record))

    return local_irreps


def validate_irrep_family(record: dict[str, Any], irreps: list[dict[str, Any]], tol: float = 1e-8) -> dict[str, Any]:
    order = record["group_order"]
    conjugacy_classes = record["conjugacy_classes_local"]
    orthogonality = []
    for i, left in enumerate(irreps):
        row = []
        left_chars = np.array(left["character"], dtype=complex)
        for right in irreps:
            right_chars = np.array(right["character"], dtype=complex)
            inner = np.vdot(left_chars, right_chars) / order
            row.append(normalize_complex(inner))
        orthogonality.append(row)
    chars_constant_on_classes = []
    for irrep in irreps:
        ok = True
        for cls in conjugacy_classes:
            values = [normalize_complex(irrep["character"][idx]) for idx in cls]
            if any(not complex_close(values[0], value, tol) for value in values[1:]):
                ok = False
                break
        chars_constant_on_classes.append(ok)
    return {
        "sum_dimension_squared": int(sum(int(irrep["dimension"]) ** 2 for irrep in irreps)),
        "matches_group_order": int(sum(int(irrep["dimension"]) ** 2 for irrep in irreps)) == order,
        "orthogonality_matrix": [[complex_to_string(value) for value in row] for row in orthogonality],
        "orthogonality_is_identity": all(
            complex_close(orthogonality[i][j], 1 if i == j else 0, tol)
            for i in range(len(orthogonality))
            for j in range(len(orthogonality))
        ),
        "characters_constant_on_conjugacy_classes": chars_constant_on_classes,
    }


def build_left_regular_matrices(mult_table: list[list[int]], cocycle: np.ndarray) -> list[np.ndarray]:
    order = len(mult_table)
    matrices: list[np.ndarray] = []
    for g in range(order):
        mat = np.zeros((order, order), dtype=complex)
        for h in range(order):
            target = mult_table[g][h]
            mat[target, h] = cocycle[g, h]
        matrices.append(mat)
    return matrices


def build_right_regular_matrices(mult_table: list[list[int]], cocycle: np.ndarray) -> list[np.ndarray]:
    order = len(mult_table)
    matrices: list[np.ndarray] = []
    for h in range(order):
        mat = np.zeros((order, order), dtype=complex)
        for g in range(order):
            target = mult_table[g][h]
            mat[target, g] = cocycle[g, h]
        matrices.append(mat)
    return matrices


def center_basis(mult_table: list[list[int]], cocycle: np.ndarray) -> list[np.ndarray]:
    order = len(mult_table)
    equations = []
    for h in range(order):
        for k in range(order):
            coeffs = [0.0] * order
            for g in range(order):
                if mult_table[g][h] == k:
                    coeffs[g] += float(np.real_if_close(cocycle[g, h]))
                if mult_table[h][g] == k:
                    coeffs[g] -= float(np.real_if_close(cocycle[h, g]))
            equations.append(coeffs)
    matrix = np.array(equations, dtype=float)
    _, _, vh = np.linalg.svd(matrix)
    rank = int(np.sum(np.linalg.svd(matrix, compute_uv=False) > 1e-9))
    basis = []
    for row in vh[rank:]:
        vec = row.astype(complex)
        max_abs = np.max(np.abs(vec))
        if max_abs > 0:
            vec = vec / max_abs
        basis.append(vec)
    return basis


def _count_eigenvalue_groups(eigenvalues: np.ndarray, tol: float = 1e-8) -> int:
    groups = 0
    cursor = 0
    while cursor < len(eigenvalues):
        groups += 1
        next_cursor = cursor + 1
        while next_cursor < len(eigenvalues) and abs(eigenvalues[next_cursor] - eigenvalues[cursor]) < tol:
            next_cursor += 1
        cursor = next_cursor
    return groups


def _hermitian_center_components(center_mats: list[np.ndarray]) -> list[np.ndarray]:
    components: list[np.ndarray] = []
    for mat in center_mats:
        hermitian = 0.5 * (mat + mat.conj().T)
        antihermitian = (mat - mat.conj().T) / (2j)
        if np.max(np.abs(hermitian)) > 1e-10:
            components.append(hermitian)
        if np.max(np.abs(antihermitian)) > 1e-10:
            components.append(antihermitian)
    if not components:
        components.append(0.5 * (center_mats[0] + center_mats[0].conj().T))
    return components


def choose_center_separator(center_mats: list[np.ndarray]) -> tuple[np.ndarray, int]:
    if not center_mats:
        raise ValueError("empty center")
    target = len(center_mats)
    components = _hermitian_center_components(center_mats)
    prime_sequences = [
        [1.0],
        [1.0, 2.0],
        [1.0, 2.0, 3.0],
        [1.0, 3.0, 5.0, 7.0],
        [2.0, 5.0, 11.0, 17.0],
        [2.0, 3.0, 5.0, 7.0, 11.0, 13.0],
        [3.0, 5.0, 7.0, 11.0, 13.0, 17.0, 19.0],
    ]
    for seq in prime_sequences:
        hermitian = np.zeros_like(center_mats[0], dtype=complex)
        for idx, mat in enumerate(components):
            hermitian += seq[idx % len(seq)] * mat
        eigenvalues, _ = np.linalg.eigh(hermitian)
        if _count_eigenvalue_groups(eigenvalues) == target:
            return hermitian, target

    rng = np.random.default_rng(0)
    for _ in range(64):
        coeffs = rng.normal(size=len(components))
        hermitian = np.zeros_like(center_mats[0], dtype=complex)
        for coeff, mat in zip(coeffs, components):
            hermitian += float(coeff) * mat
        eigenvalues, _ = np.linalg.eigh(hermitian)
        if _count_eigenvalue_groups(eigenvalues) == target:
            return hermitian, target
    raise ValueError("unable to separate center blocks")


def twisted_isotypic_blocks(mult_table: list[list[int]], cocycle: np.ndarray) -> list[dict[str, Any]]:
    order = len(mult_table)
    left_regular = build_left_regular_matrices(mult_table, cocycle)
    center_vecs = center_basis(mult_table, cocycle)
    center_mats = [sum(vec[g] * left_regular[g] for g in range(order)) for vec in center_vecs]
    hermitian, expected_blocks = choose_center_separator(center_mats)
    eigenvalues, eigenvectors = np.linalg.eigh(hermitian)
    blocks = []
    cursor = 0
    while cursor < len(eigenvalues):
        next_cursor = cursor + 1
        while next_cursor < len(eigenvalues) and abs(eigenvalues[next_cursor] - eigenvalues[cursor]) < 1e-8:
            next_cursor += 1
        vecs = eigenvectors[:, cursor:next_cursor]
        projector = vecs @ vecs.conj().T
        rank = next_cursor - cursor
        dimension = int(round(math.sqrt(rank)))
        if dimension * dimension != rank:
            raise ValueError(f"block rank {rank} is not a perfect square")
        block = {
            "eigenvalue": float(np.real_if_close(eigenvalues[cursor])),
            "rank": rank,
            "dimension": dimension,
            "projector": projector,
        }
        blocks.append(block)
        cursor = next_cursor
    if len(blocks) != expected_blocks:
        raise ValueError("unexpected number of twisted blocks")

    out = []
    for block in blocks:
        projector = block["projector"]
        dimension = block["dimension"]
        character = []
        for regular in left_regular:
            value = np.trace(projector @ regular) / dimension
            character.append(normalize_complex(value))
        out.append(
            {
                "dimension": dimension,
                "character": character,
                "projector": projector,
                "rank": block["rank"],
                "eigenvalue": block["eigenvalue"],
            }
        )
    out.sort(key=lambda item: (item["dimension"], [round(abs(value), 12) for value in item["character"]]))
    return out


def extract_projective_rep_matrices(mult_table: list[list[int]], cocycle: np.ndarray, block: dict[str, Any]) -> dict[str, Any]:
    left_regular = build_left_regular_matrices(mult_table, cocycle)
    right_regular = build_right_regular_matrices(mult_table, cocycle)
    projector = block["projector"]
    dimension = int(block["dimension"])
    eigvals_p, eigvecs_p = np.linalg.eigh(projector)
    keep = [idx for idx, value in enumerate(eigvals_p) if abs(value) > 1e-8]
    block_basis = eigvecs_p[:, keep]
    if block_basis.shape[1] != dimension * dimension:
        raise ValueError("unexpected isotypic block rank")
    if dimension == 1:
        basis = block_basis[:, :1]
    else:
        right_combo = np.zeros((block_basis.shape[1], block_basis.shape[1]), dtype=complex)
        coeffs = [1.0, 2.0, 3.0, 5.0, 7.0]
        for idx, mat in enumerate(right_regular):
            restricted = block_basis.conj().T @ mat @ block_basis
            coeff = coeffs[idx % len(coeffs)]
            right_combo += coeff * (restricted + restricted.conj().T)
        evals_r, evecs_r = np.linalg.eigh(right_combo)
        chosen = None
        cursor = 0
        while cursor < len(evals_r):
            next_cursor = cursor + 1
            while next_cursor < len(evals_r) and abs(evals_r[next_cursor] - evals_r[cursor]) < 1e-8:
                next_cursor += 1
            multiplicity = next_cursor - cursor
            if multiplicity == dimension:
                chosen = evecs_r[:, cursor:next_cursor]
                break
            cursor = next_cursor
        if chosen is None:
            raise ValueError("unable to isolate a minimal left ideal from the right-regular split")
        basis = block_basis @ chosen
    rep_mats = [basis.conj().T @ regular @ basis for regular in left_regular]
    max_error = 0.0
    for g in range(len(mult_table)):
        for h in range(len(mult_table)):
            lhs = rep_mats[g] @ rep_mats[h]
            rhs = cocycle[g, h] * rep_mats[mult_table[g][h]]
            max_error = max(max_error, float(np.max(np.abs(lhs - rhs))))
    return {
        "rep_matrices": rep_mats,
        "max_projective_relation_error": max_error,
    }


def label_projective_irreps(record: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    type_key = record["site_symmetry_type_key"]
    labels = []
    if type_key in {"C2", "Cs"}:
        generator = 1
        ordered = sorted(blocks, key=lambda item: float(item["character"][generator].imag))
        label_names = ["minus_i", "plus_i"]
        for label_name, block in zip(label_names, ordered):
            labels.append((f"proj_{label_name}", block))
    elif type_key == "C2h":
        parity = int(record["parity_element_local_index"])
        ordered = sorted(
            blocks,
            key=lambda item: (round(float(item["character"][parity].real), 6), round(float(item["character"][1].imag), 6)),
        )
        for block in ordered:
            parity_tag = "g" if complex_close(block["character"][parity], 1) else "u"
            spin_tag = complex_to_string(block["character"][1]).replace("+", "p").replace("-", "m")
            labels.append((f"proj_{parity_tag}_{spin_tag}", block))
    elif type_key == "C2v":
        for idx, block in enumerate(sorted(blocks, key=lambda item: (item["dimension"], complex_to_string(item["character"][1]))), start=1):
            labels.append((f"proj_mm2_{idx}", block))
    elif type_key == "C3v":
        for idx, block in enumerate(sorted(blocks, key=lambda item: (item["dimension"], complex_to_string(item["character"][1]))), start=1):
            label = "proj_E_half" if block["dimension"] == 2 else f"proj_1d_{idx}"
            labels.append((label, block))
    elif type_key in {"D3d_like", "D3h_like"}:
        parity = int(record["parity_element_local_index"])
        parity_pos, parity_neg = ("g", "u") if type_key == "D3d_like" else ("prime", "doubleprime")
        ordered = sorted(
            blocks,
            key=lambda item: (item["dimension"], round(float(item["character"][parity].real), 6), complex_to_string(item["character"][1])),
        )
        for idx, block in enumerate(ordered, start=1):
            parity_tag = parity_pos if complex_close(block["character"][parity], 1) else parity_neg
            labels.append((f"proj_{parity_tag}_{block['dimension']}d_{idx}", block))
    else:
        for idx, block in enumerate(blocks, start=1):
            labels.append((f"proj_{idx}", block))
    return [
        {
            "label": label,
            "dimension": int(block["dimension"]),
            "character": block["character"],
            "projector": block["projector"],
        }
        for label, block in labels
    ]


def validation_summary_for_projective(record: dict[str, Any], labeled_blocks: list[dict[str, Any]], cocycle: np.ndarray) -> dict[str, Any]:
    characters = [np.array(item["character"], dtype=complex) for item in labeled_blocks]
    order = record["group_order"]
    orthogonality = []
    for left in characters:
        row = []
        for right in characters:
            row.append(normalize_complex(np.vdot(left, right) / order))
        orthogonality.append(row)
    relation_errors = []
    matrix_part = []
    for item in labeled_blocks:
        extracted = extract_projective_rep_matrices(record["multiplication_table_local"], cocycle, item)
        relation_errors.append(extracted["max_projective_relation_error"])
        matrix_part.append(
            {
                "label": item["label"],
                "dimension": int(item["dimension"]),
                "max_projective_relation_error": round(float(extracted["max_projective_relation_error"]), 12),
                "sample_generator_matrices": [
                    [[complex_to_string(normalize_complex(value)) for value in row] for row in mat.tolist()]
                    for mat in extracted["rep_matrices"][: min(3, len(extracted["rep_matrices"]))]
                ],
            }
        )
    return {
        "sum_dimension_squared": int(sum(int(item["dimension"]) ** 2 for item in labeled_blocks)),
        "matches_group_order": int(sum(int(item["dimension"]) ** 2 for item in labeled_blocks)) == order,
        "orthogonality_matrix": [[complex_to_string(value) for value in row] for row in orthogonality],
        "orthogonality_is_identity": all(
            complex_close(orthogonality[i][j], 1 if i == j else 0)
            for i in range(len(orthogonality))
            for j in range(len(orthogonality))
        ),
        "max_projective_relation_error": round(float(max(relation_errors) if relation_errors else 0.0), 12),
        "matrix_validation_samples": matrix_part,
    }


def serializable_single_irreps(record: dict[str, Any], irreps: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "site_symmetry_type_key": record["site_symmetry_type_key"],
        "site_symmetry_type_label": record["site_symmetry_type_label"],
        "group_order": int(record["group_order"]),
        "class_sizes": list(record["class_sizes"]),
        "label_scheme": record["label_scheme"],
        "families": [],
        "irreps": [
            {
                "label": irrep["label"],
                "dimension": int(irrep["dimension"]),
                "character_vector": [complex_to_string(value) for value in irrep["character"]],
                "character_vector_json": [json_default(value) for value in irrep["character"]],
                "stabilizer_element_ordering_local": list(range(record["group_order"])),
            }
            for irrep in irreps
        ],
        "validation_summary": validation,
    }


def serializable_projective_irreps(record: dict[str, Any], irreps: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "site_symmetry_type_key": record["site_symmetry_type_key"],
        "site_symmetry_type_label": record["site_symmetry_type_label"],
        "group_order": int(record["group_order"]),
        "class_sizes": list(record["class_sizes"]),
        "label_scheme": record["label_scheme"],
        "families": [],
        "projective_irreps_or_coreps": [
            {
                "label": irrep["label"],
                "dimension": int(irrep["dimension"]),
                "type": "projective_local_irrep",
                "origin": "twisted regular decomposition of the stabilizer using the restricted factor_su2 cocycle",
                "character_vector": [complex_to_string(value) for value in irrep["character"]],
                "character_vector_json": [json_default(value) for value in irrep["character"]],
                "stabilizer_element_ordering_local": list(range(record["group_order"])),
            }
            for irrep in irreps
        ],
        "validation_summary": validation,
    }


def build_inventory_and_libraries() -> dict[str, Any]:
    port = load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(TARGET_GROUP)

    ctx_single = port.load_context(module, TARGET_GROUP, "single", ssg_dict)
    ctx_double = port.load_context(module, TARGET_GROUP, "double", ssg_dict)

    inventory_records = []
    single_types: dict[str, dict[str, Any]] = {}
    double_types: dict[str, dict[str, Any]] = {}
    family_single_local_irreps: dict[str, list[dict[str, Any]]] = {}
    family_double_local_irreps: dict[str, list[dict[str, Any]]] = {}

    compose_single = ctx_single["group_tables"]["compose"]
    inverse_single = ctx_single["group_tables"]["inverse"]
    factor = np.array(ctx_double["ssg"].factor_su2, dtype=complex)

    for entry in ctx_single["wyckoff_entries"]:
        letter = entry["letter"]
        bridge_entry_single = port.bridge.bridge_stabilizer_for_entry(entry, ctx_single)
        record = group_local_record(letter, entry, bridge_entry_single, ctx_single, compose_single, inverse_single)
        inventory_records.append(record)

        single_irreps = ordinary_single_characters_for_record(record)
        single_validation = validate_irrep_family(record, single_irreps)
        family_single_local_irreps[letter] = []
        for irrep in single_irreps:
            family_single_local_irreps[letter].append(
                {
                    "family_id": letter,
                    "label": irrep["label"],
                    "dimension": int(irrep["dimension"]),
                    "character_on_unitary_stabilizer": {
                        str(global_index): json_default(value)
                        for global_index, value in zip(record["stabilizer_indices"], irrep["character"])
                    },
                    "character_on_unitary_stabilizer_complex": {
                        int(global_index): complex(value)
                        for global_index, value in zip(record["stabilizer_indices"], irrep["character"])
                    },
                    "site_symmetry_type_key": record["site_symmetry_type_key"],
                    "site_symmetry_type_label": record["site_symmetry_type_label"],
                    "family_dimension": int(record["dimension"]),
                }
            )
        if record["site_symmetry_type_key"] not in single_types:
            single_types[record["site_symmetry_type_key"]] = serializable_single_irreps(record, single_irreps, single_validation)
        single_types[record["site_symmetry_type_key"]]["families"].append(letter)

        stabilizer = record["stabilizer_indices"]
        cocycle = factor[np.ix_(stabilizer, stabilizer)]
        local_blocks = twisted_isotypic_blocks(record["multiplication_table_local"], cocycle)
        labeled_blocks = label_projective_irreps(record, local_blocks)
        projective_validation = validation_summary_for_projective(record, labeled_blocks, cocycle)
        family_double_local_irreps[letter] = []
        for irrep in labeled_blocks:
            family_double_local_irreps[letter].append(
                {
                    "family_id": letter,
                    "label": irrep["label"],
                    "dimension": int(irrep["dimension"]),
                    "character_on_unitary_stabilizer": {
                        str(global_index): json_default(value)
                        for global_index, value in zip(record["stabilizer_indices"], irrep["character"])
                    },
                    "character_on_unitary_stabilizer_complex": {
                        int(global_index): complex(value)
                        for global_index, value in zip(record["stabilizer_indices"], irrep["character"])
                    },
                    "type": "projective_local_irrep",
                    "origin": "twisted_regular_decomposition",
                    "site_symmetry_type_key": record["site_symmetry_type_key"],
                    "site_symmetry_type_label": record["site_symmetry_type_label"],
                    "family_dimension": int(record["dimension"]),
                }
            )
        if record["site_symmetry_type_key"] not in double_types:
            double_types[record["site_symmetry_type_key"]] = serializable_projective_irreps(record, labeled_blocks, projective_validation)
        double_types[record["site_symmetry_type_key"]]["families"].append(letter)

    nonabelian_single_types = {
        key: value
        for key, value in single_types.items()
        if any(next(record for record in inventory_records if record["family_id"] == letter)["nonabelian"] for letter in value["families"])
    }
    nonabelian_double_types = {
        key: value
        for key, value in double_types.items()
        if any(next(record for record in inventory_records if record["family_id"] == letter)["nonabelian"] for letter in value["families"])
    }

    inventory_json = {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "families": [
            {
                "family_id": record["family_id"],
                "representative_coordinate": record["representative_coordinate"],
                "multiplicity": int(record["multiplicity"]),
                "site_symmetry_label": record["site_symmetry_label"],
                "group_order": int(record["group_order"]),
                "unitary_count": int(record["unitary_count"]),
                "antiunitary_count": int(record["antiunitary_count"]),
                "abelian": bool(record["abelian"]),
                "nonabelian": bool(record["nonabelian"]),
                "blocker_relevance": record["blocker_relevance"],
                "site_symmetry_type_key": record["site_symmetry_type_key"],
                "site_symmetry_type_label": record["site_symmetry_type_label"],
            }
            for record in inventory_records
        ],
    }

    single_library_json = {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "nonabelian_site_symmetry_types": nonabelian_single_types,
        "auxiliary_abelian_site_symmetry_types_used_for_ai": {
            key: value for key, value in single_types.items() if key not in nonabelian_single_types
        },
    }
    double_library_json = {
        "reference_group": REFERENCE_GROUP,
        "target_group": TARGET_GROUP,
        "nonabelian_site_symmetry_types": nonabelian_double_types,
        "auxiliary_abelian_site_symmetry_types_used_for_ai": {
            key: value for key, value in double_types.items() if key not in nonabelian_double_types
        },
    }

    md_lines = [
        "# SG 194 Non-Abelian Site-Symmetry Inventory",
        "",
        "## Scope",
        "",
        "- Target group fixed to `194.1.1.1`.",
        "- This inventory is built from the current local `swyckoff_r.py` real-space families plus direct stabilizer recomputation through the audited stage-1 bridge.",
        "",
        "## Family Table",
        "",
        "| family | dim | mult | representative | site symmetry | order | unitary | antiunitary | abelian | nonabelian | blocker relevance |",
        "| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for record in inventory_records:
        md_lines.append(
            f"| `{record['family_id']}` | `{record['dimension']}` | `{record['multiplicity']}` | `{record['representative_coordinate']}` | `{record['site_symmetry_label']}` | `{record['group_order']}` | `{record['unitary_count']}` | `{record['antiunitary_count']}` | `{record['abelian']}` | `{record['nonabelian']}` | `{record['blocker_relevance']}` |"
        )
    md_lines.extend(
        [
            "",
            "## Non-Abelian Site-Symmetry Types",
            "",
        ]
    )
    for key, payload in sorted(nonabelian_single_types.items()):
        md_lines.append(
            f"- `{key}` / `{payload['site_symmetry_type_label']}`: families `{', '.join(payload['families'])}`, irreps `{', '.join(irrep['label'] for irrep in payload['irreps'])}`."
        )
    md_lines.extend(
        [
            "",
            "## Blocker Diagnosis",
            "",
            "- The primary stage-1 blocker source is the non-abelian set `C3v` on `e,f` and the two order-12 non-abelian types on `a,b,c,d`.",
            "- The order-2 / order-4 abelian families are follow-on work for AI closure, but they are not the conceptual reason the stage-1 portability pilot stalled.",
            "- All site symmetries remain purely unitary in the present SG 194 controlled case, so the double-group stage requires projective local irreps, not antiunitary Wigner-corep extensions.",
        ]
    )

    return {
        "inventory_records": inventory_records,
        "inventory_json": inventory_json,
        "inventory_md": "\n".join(md_lines),
        "single_library_json": single_library_json,
        "double_library_json": double_library_json,
        "family_single_local_irreps": family_single_local_irreps,
        "family_double_local_irreps": family_double_local_irreps,
    }


def generate_outputs() -> dict[str, Any]:
    payload = build_inventory_and_libraries()
    write_text(INVENTORY_MD, payload["inventory_md"])
    write_json(INVENTORY_JSON, payload["inventory_json"])
    write_json(SINGLE_LIBRARY_JSON, payload["single_library_json"])
    write_json(DOUBLE_LIBRARY_JSON, payload["double_library_json"])
    return payload


def validate_outputs() -> None:
    inventory = json.loads(INVENTORY_JSON.read_text())
    single = json.loads(SINGLE_LIBRARY_JSON.read_text())
    double = json.loads(DOUBLE_LIBRARY_JSON.read_text())

    nonabelian_families = {
        entry["family_id"]
        for entry in inventory["families"]
        if entry["nonabelian"]
    }
    if nonabelian_families != {"a", "b", "c", "d", "e", "f"}:
        raise ValueError(f"unexpected nonabelian family set: {sorted(nonabelian_families)}")

    single_types = set(single["nonabelian_site_symmetry_types"])
    if single_types != {"C3v", "D3d_like", "D3h_like"}:
        raise ValueError(f"unexpected single nonabelian type set: {sorted(single_types)}")

    double_types = set(double["nonabelian_site_symmetry_types"])
    if double_types != {"C3v", "D3d_like", "D3h_like"}:
        raise ValueError(f"unexpected double nonabelian type set: {sorted(double_types)}")

    for payload in single["nonabelian_site_symmetry_types"].values():
        if not payload["validation_summary"]["matches_group_order"]:
            raise ValueError("single-library dimension-square check failed")
        if not payload["validation_summary"]["orthogonality_is_identity"]:
            raise ValueError("single-library orthogonality check failed")

    for payload in double["nonabelian_site_symmetry_types"].values():
        if not payload["validation_summary"]["matches_group_order"]:
            raise ValueError("double-library dimension-square check failed")
        if not payload["validation_summary"]["orthogonality_is_identity"]:
            raise ValueError("double-library orthogonality check failed")
        if float(payload["validation_summary"]["max_projective_relation_error"]) > 1e-6:
            raise ValueError("double-library projective-relation check failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validated stage-2 SG194 local-library outputs")
        return

    payload = generate_outputs()
    validate_outputs()
    print("1. 194.1.1.1 上真实出现的 non-abelian site symmetries 是哪些？")
    print("   e,f -> C3v / 3m; a -> D3d-like / -3m; b,c,d -> D3h-like / -6m2")
    print("2. single-group non-abelian local-irrep library 是否已实现？")
    print("   True")
    print("3. double-group non-abelian local-corep / projective-irrep library 是否已实现？")
    print("   True")


if __name__ == "__main__":
    main()
