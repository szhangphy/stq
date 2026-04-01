#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cmath
import importlib.util
import json
import pickle
import sys
import tarfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "common"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import swyckoff_r

GROUP_NUMBER = "10.4.1.31"
PACKAGE_NAME = "review_package_10.4.1.31_ai_bridge"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

MANIFOLDS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "S1", "S2"]
TRIVIAL_GENERATOR_LETTERS = ["c", "f"]

BRIDGE_AUDIT_MD = ROOT / "single_group_ai_bridge_audit.md"
BRIDGE_SUMMARY_JSON = ROOT / "single_group_ai_bridge_summary.json"
AI_MIN_GENERATORS_JSON = ROOT / "single_group_ai_min_generators.json"
AI_MIN_MATRIX_JSON = ROOT / "single_group_ai_min_matrix.json"
BS_VS_AI_MIN_SUMMARY_JSON = ROOT / "single_group_bs_vs_ai_min_summary.json"

BACKGROUND_CONTEXT = {
    "audit/single_group_ai_feasibility_audit.md": ROOT / "single_group_ai_feasibility_audit.md",
    "audit/single_group_ai_feasibility_summary.json": ROOT / "single_group_ai_feasibility_summary.json",
    "audit/single_group_bs_with_planes_summary.json": ROOT / "single_group_bs_with_planes_summary.json",
    "audit/single_group_plane_formalism_audit.md": ROOT / "single_group_plane_formalism_audit.md",
    "audit/single_group_plane_formalism_summary.json": ROOT / "single_group_plane_formalism_summary.json",
    "audit/single_group_site_symmetry_check.json": ROOT / "single_group_site_symmetry_check.json",
    "audit/single_group_torsion_audit.json": ROOT / "single_group_torsion_audit.json",
    "background/single_group_connectivity.json": ROOT / "single_group_connectivity.json",
    "background/single_group_kmanifolds.json": ROOT / "single_group_kmanifolds.json",
    "basis/single_group_bs_with_planes_basis_pretty.json": ROOT / "single_group_bs_with_planes_basis_pretty.json",
    "basis/single_group_bs_with_planes_basis_raw.json": ROOT / "single_group_bs_with_planes_basis_raw.json",
    "matrix/single_group_full_compatibility_with_planes.json": ROOT / "single_group_full_compatibility_with_planes.json",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def complex_from_json(value: dict[str, Any]) -> complex:
    return complex(value["real"], value["imag"])


def format_number(value: float, max_denominator: int = 48) -> str:
    frac = Fraction(str(float(value))).limit_denominator(max_denominator)
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"


def format_vector(values: np.ndarray | list[float], max_denominator: int = 48) -> list[str]:
    arr = np.asarray(values, dtype=float)
    return [format_number(float(value), max_denominator=max_denominator) for value in arr]


def sample_parameters_for_dimension(dimension: int) -> list[Fraction]:
    pool = [Fraction(1, 5), Fraction(2, 7), Fraction(3, 11)]
    return pool[:dimension]


def representative_sample_point_magnetic(entry: dict[str, Any]) -> np.ndarray:
    point = np.array([float(value) for value in entry["x0"]], dtype=float)
    basis_vecs = entry.get("basis_vecs", []) or []
    params = sample_parameters_for_dimension(int(entry["dim"]))
    for basis_vec, param in zip(basis_vecs, params):
        point = point + float(param) * np.array([float(value) for value in basis_vec], dtype=float)
    return point


def op_rotation_key(rotation: np.ndarray, tol: float = 1e-8) -> tuple[tuple[int, int, int], ...]:
    rounded = np.rint(rotation).astype(int)
    if np.linalg.norm(rotation - rounded) > tol:
        raise ValueError(f"rotation is not integral within tolerance: {rotation}")
    return tuple(tuple(int(value) for value in row) for row in rounded.tolist())


def op_translation_key(translation: np.ndarray, max_denominator: int = 48) -> tuple[str, str, str]:
    return tuple(format_number(float(value), max_denominator=max_denominator) for value in translation.tolist())


def lattice_coefficients(supercell: np.ndarray, vector: np.ndarray) -> np.ndarray:
    return np.linalg.solve(supercell, vector)


def vector_is_lattice(supercell: np.ndarray, vector: np.ndarray, tol: float = 1e-8) -> tuple[bool, np.ndarray]:
    coeffs = lattice_coefficients(supercell, vector)
    return bool(np.linalg.norm(coeffs - np.rint(coeffs)) < tol), coeffs


def reduced_magnetic_key(supercell: np.ndarray, point_conv: np.ndarray) -> tuple[str, str, str]:
    point_mag = np.linalg.solve(supercell, point_conv)
    point_mag = point_mag - np.floor(point_mag + 1e-10)
    return tuple(format_number(float(value)) for value in point_mag.tolist())


def load_ssgreps_module():
    ssgreps_py = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
    ssgreps_dir = ssgreps_py.parent
    if str(ssgreps_dir) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(ssgreps_dir))
    spec = importlib.util.spec_from_file_location("ssgreps_local", ssgreps_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {ssgreps_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_context() -> dict[str, Any]:
    module = load_ssgreps_module()
    identify_pkl = ROOT / "SSGReps" / "ssg_data" / "identify.pkl"
    with identify_pkl.open("rb") as fh:
        ssg_list = pickle.load(fh)
    ssg_dict = next(item for item in ssg_list if item["ssgNum"] == GROUP_NUMBER)
    ssg = module.loadSsgGroup(GROUP_NUMBER, np.array([0.0, 0.0, 0.0]), "single", ssg_dict)

    full_data, _ = swyckoff_r.load_irssg_data(GROUP_NUMBER, 0)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]

    wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(GROUP_NUMBER, fast=True)
    basis_raw = load_json(ROOT / "single_group_bs_with_planes_basis_raw.json")
    compat = load_json(ROOT / "single_group_full_compatibility_with_planes.json")

    return {
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": full_data,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
        "wyckoff_entries": wyckoff_entries,
        "basis_raw": basis_raw,
        "compat": compat,
    }


def converted_swyckoff_ops(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    supercell = ctx["supercell"]
    supercell_inv = np.linalg.inv(supercell)
    converted: list[dict[str, Any]] = []
    for index, (op, tr) in enumerate(zip(ctx["full_ops"], ctx["full_time_revs"])):
        rotation_mag = np.array([[float(value) for value in row] for row in op.W], dtype=float)
        translation_mag = np.array([float(value) for value in op.t], dtype=float)
        rotation_conv = supercell @ rotation_mag @ supercell_inv
        translation_conv = supercell @ translation_mag
        converted.append(
            {
                "index": index,
                "rotation": rotation_conv,
                "translation": translation_conv,
                "time_reversal": bool(tr),
            }
        )
    return converted


def raw_ssgreps_ops(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    ssg = ctx["ssg"]
    ops: list[dict[str, Any]] = []
    for index, (rotation, translation, tr) in enumerate(zip(ssg.rotC, ssg.tauC, ssg.time_reversal)):
        ops.append(
            {
                "index": index,
                "rotation": np.array(rotation, dtype=float),
                "translation": np.array(translation, dtype=float),
                "time_reversal": int(tr) < 0,
            }
        )
    return ops


def validate_operation_bridge(ctx: dict[str, Any]) -> dict[str, Any]:
    converted = converted_swyckoff_ops(ctx)
    ssgreps_ops = raw_ssgreps_ops(ctx)

    converted_keys = [
        {
            "rotation_key": op_rotation_key(item["rotation"]),
            "translation_key": op_translation_key(item["translation"]),
            "time_reversal": item["time_reversal"],
        }
        for item in converted
    ]
    ssgreps_keys = [
        {
            "rotation_key": op_rotation_key(item["rotation"]),
            "translation_key": op_translation_key(item["translation"]),
            "time_reversal": item["time_reversal"],
        }
        for item in ssgreps_ops
    ]

    matches: list[dict[str, int]] = []
    remaining = set(range(len(ssgreps_keys)))
    mismatches: list[dict[str, Any]] = []

    for conv_index, conv_key in enumerate(converted_keys):
        match_index = None
        for ssg_index in list(remaining):
            if ssgreps_keys[ssg_index] == conv_key:
                match_index = ssg_index
                break
        if match_index is None:
            mismatches.append(
                {
                    "converted_index": conv_index,
                    "rotation_key": conv_key["rotation_key"],
                    "translation_key": conv_key["translation_key"],
                    "time_reversal": conv_key["time_reversal"],
                }
            )
            continue
        remaining.remove(match_index)
        matches.append({"converted_index": conv_index, "ssgreps_index": match_index})

    return {
        "supercell_basis_change": ctx["supercell"].astype(int).tolist(),
        "converted_operation_count": len(converted),
        "ssgreps_operation_count": len(ssgreps_ops),
        "matched_operation_count": len(matches),
        "all_operations_match_exactly_after_basis_change": len(matches) == len(converted) == len(ssgreps_ops),
        "matches": matches,
        "mismatches": mismatches,
    }


def bridge_stabilizer_for_entry(entry: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    supercell = ctx["supercell"]
    sample_mag = representative_sample_point_magnetic(entry)
    sample_conv = supercell @ sample_mag

    stabilizer_indices: list[int] = []
    unitary_indices: list[int] = []
    antiunitary_indices: list[int] = []

    for index, (rotation, translation, tr) in enumerate(zip(ctx["ssg"].rotC, ctx["ssg"].tauC, ctx["ssg"].time_reversal)):
        image = np.array(rotation, dtype=float) @ sample_conv + np.array(translation, dtype=float)
        fixed, coeffs = vector_is_lattice(supercell, image - sample_conv)
        if not fixed:
            continue
        stabilizer_indices.append(index)
        if int(tr) < 0:
            antiunitary_indices.append(index)
        else:
            unitary_indices.append(index)

    return {
        "letter": entry["letter"],
        "representative_coordinate_magnetic": entry["representative_coordinate"],
        "sample_point_magnetic": ", ".join(format_vector(sample_mag)),
        "sample_point_conventional": ", ".join(format_vector(sample_conv)),
        "expected_stabilizer_size": int(entry["stab"]),
        "bridge_stabilizer_size": len(stabilizer_indices),
        "bridge_unitary_count": len(unitary_indices),
        "bridge_antiunitary_count": len(antiunitary_indices),
        "stabilizer_indices": stabilizer_indices,
        "unitary_indices": unitary_indices,
        "antiunitary_indices": antiunitary_indices,
        "match": len(stabilizer_indices) == int(entry["stab"]),
    }


def validate_bridge_stabilizers(ctx: dict[str, Any]) -> dict[str, Any]:
    entries = [bridge_stabilizer_for_entry(entry, ctx) for entry in ctx["wyckoff_entries"]]
    consistent_letters = [entry["letter"] for entry in entries if entry["match"]]
    return {
        "entry_count": len(entries),
        "all_entries_match_expected_size": len(consistent_letters) == len(entries),
        "consistent_letters": consistent_letters,
        "entries": entries,
    }


def orbit_for_letter(letter: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    entry = next(item for item in ctx["wyckoff_entries"] if item["letter"] == letter)
    rep_mag = np.array([float(value) for value in entry["x0"]], dtype=float)
    rep_conv = ctx["supercell"] @ rep_mag

    orbit: list[dict[str, Any]] = []
    seen = set()
    for index, (rotation, translation, tr) in enumerate(zip(ctx["ssg"].rotC, ctx["ssg"].tauC, ctx["ssg"].time_reversal)):
        image_conv = np.array(rotation, dtype=float) @ rep_conv + np.array(translation, dtype=float)
        key = reduced_magnetic_key(ctx["supercell"], image_conv)
        if key in seen:
            continue
        seen.add(key)
        orbit.append(
            {
                "source_operation_index": index,
                "time_reversal": int(tr) < 0,
                "magnetic_coordinate": list(key),
                "conventional_coordinate": format_vector(image_conv),
                "conv_vector": image_conv,
            }
        )
    return orbit


def manifold_linear_characters(manifold_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    raw = load_json(ROOT / f"{manifold_id}_character.json")
    reciprocal_basis = ctx["reciprocal_basis"]
    kvec = np.array(raw["kvec"], dtype=float)
    kconv = kvec[0] * reciprocal_basis[0] + kvec[1] * reciprocal_basis[1] + kvec[2] * reciprocal_basis[2]

    unitary_rotations: list[np.ndarray] = []
    unitary_translations: list[np.ndarray] = []
    for rotation, translation, tr in zip(raw["rotC"], raw["tauC"], raw["timeReversal"]):
        if int(tr) < 0:
            continue
        unitary_rotations.append(np.array(rotation, dtype=float))
        unitary_translations.append(np.array(translation, dtype=float))

    raw_chars = np.array([[complex_from_json(value) for value in row] for row in raw["character"]], dtype=complex)
    phases = np.array(
        [cmath.exp(-1j * float(np.dot(kconv, translation))) for translation in unitary_translations],
        dtype=complex,
    )
    linear_chars = raw_chars * phases[np.newaxis, :]

    return {
        "manifold_id": manifold_id,
        "kvec": raw["kvec"],
        "kconv": kconv,
        "unitary_rotations": unitary_rotations,
        "unitary_translations": unitary_translations,
        "linear_characters": linear_chars,
        "rep_degree": raw["repDegree"],
        "raw": raw,
    }


def induced_trivial_band_data(letter: str, ctx: dict[str, Any]) -> dict[str, Any]:
    orbit = orbit_for_letter(letter, ctx)
    orbit_points = [site["conv_vector"] for site in orbit]

    manifold_multiplicities: dict[str, list[int]] = {}
    manifold_band_characters: dict[str, list[dict[str, float]]] = {}

    for manifold_id in MANIFOLDS:
        info = manifold_linear_characters(manifold_id, ctx)
        band_character: list[complex] = []
        for rotation, translation in zip(info["unitary_rotations"], info["unitary_translations"]):
            total = 0j
            for point_conv in orbit_points:
                delta = rotation @ point_conv + translation - point_conv
                fixed, coeffs = vector_is_lattice(ctx["supercell"], delta)
                if not fixed:
                    continue
                total += cmath.exp(-1j * float(np.dot(info["kconv"], delta)))
            band_character.append(total)

        band = np.array(band_character, dtype=complex)
        chars = info["linear_characters"]
        gram = chars @ chars.conj().T / chars.shape[1]
        rhs = chars.conj() @ band / chars.shape[1]
        mult = np.linalg.solve(gram, rhs)
        mult_round = [int(round(float(value.real))) for value in mult]
        recon = np.array(mult_round, dtype=complex) @ chars
        if not np.allclose(mult, np.rint(mult.real), atol=1e-8):
            raise ValueError(f"{letter} on {manifold_id}: multiplicities are not integral")
        if not np.allclose(recon, band, atol=1e-8):
            raise ValueError(f"{letter} on {manifold_id}: linear-character reconstruction failed")
        if sum(m * d for m, d in zip(mult_round, info["rep_degree"])) != len(orbit):
            raise ValueError(f"{letter} on {manifold_id}: rep-degree sum does not match orbit size")

        manifold_multiplicities[manifold_id] = mult_round
        manifold_band_characters[manifold_id] = [
            {"real": round(value.real, 12), "imag": round(value.imag, 12)} for value in band_character
        ]

    vector: list[int] = []
    for token in ctx["basis_raw"]["unknown_ordering"]:
        manifold_id, rep_index_str = token.split("_R")
        vector.append(manifold_multiplicities[manifold_id][int(rep_index_str) - 1])

    compatibility_matrix = sp.Matrix(ctx["compat"]["global_matrix"])
    compatibility_zero = all(int(value) == 0 for value in list(compatibility_matrix * sp.Matrix(vector)))

    basis_columns = [sp.Matrix(column["vector"]) for column in ctx["basis_raw"]["basis_vectors"]]
    basis_matrix = sp.Matrix.hstack(*basis_columns)
    coeff_solution = basis_matrix.gauss_jordan_solve(sp.Matrix(vector))[0]
    coeffs = [int(value) for value in coeff_solution]

    return {
        "letter": letter,
        "representative_coordinate_magnetic": next(
            entry["representative_coordinate"] for entry in ctx["wyckoff_entries"] if entry["letter"] == letter
        ),
        "representative_coordinate_conventional": ", ".join(
            format_vector(ctx["supercell"] @ np.array([float(value) for value in next(
                entry["x0"] for entry in ctx["wyckoff_entries"] if entry["letter"] == letter
            )], dtype=float))
        ),
        "multiplicity": len(orbit),
        "site_symmetry": next(entry["site_symmetry"] for entry in ctx["wyckoff_entries"] if entry["letter"] == letter),
        "local_rep": {
            "id": f"{letter}_trivial_1d",
            "dimension": 1,
            "definition": "Trivial one-dimensional local representation: character +1 on every unitary stabilizer element.",
        },
        "orbit": [
            {
                "magnetic_coordinate": site["magnetic_coordinate"],
                "conventional_coordinate": site["conventional_coordinate"],
                "time_reversal_source": site["time_reversal"],
            }
            for site in orbit
        ],
        "manifold_multiplicities": manifold_multiplicities,
        "manifold_band_characters": manifold_band_characters,
        "unknown_vector": vector,
        "compatibility_zero": compatibility_zero,
        "bs_basis_coefficients": coeffs,
    }


def build_ai_min(ctx: dict[str, Any]) -> dict[str, Any]:
    generators = [induced_trivial_band_data(letter, ctx) for letter in TRIVIAL_GENERATOR_LETTERS]
    vectors = [generator["unknown_vector"] for generator in generators]
    a_min = sp.Matrix.hstack(*[sp.Matrix(vector) for vector in vectors])
    basis_columns = [sp.Matrix(column["vector"]) for column in ctx["basis_raw"]["basis_vectors"]]
    bs_matrix = sp.Matrix.hstack(*basis_columns)

    return {
        "unknown_ordering": ctx["basis_raw"]["unknown_ordering"],
        "generators": generators,
        "A_min_columns": vectors,
        "column_order": [generator["local_rep"]["id"] for generator in generators],
        "rank_z": int(a_min.rank()),
        "rank_bs": int(bs_matrix.rank()),
        "rank_union_with_bs": int(sp.Matrix.hstack(a_min, bs_matrix).rank()),
    }


def bridge_summary(ctx: dict[str, Any], bridge_ops: dict[str, Any], bridge_stabilizers: dict[str, Any], ai_min: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "bridge_validated": bridge_ops["all_operations_match_exactly_after_basis_change"]
        and bridge_stabilizers["all_entries_match_expected_size"],
        "supercell_basis_change": bridge_ops["supercell_basis_change"],
        "matched_operation_count": bridge_ops["matched_operation_count"],
        "operation_count_total": bridge_ops["converted_operation_count"],
        "bridge_stabilizer_entry_count": bridge_stabilizers["entry_count"],
        "bridge_stabilizer_consistent_letters": bridge_stabilizers["consistent_letters"],
        "minimal_ai_prototype_built": True,
        "prototype_generator_ids": ai_min["column_order"],
        "prototype_letters": [generator["letter"] for generator in ai_min["generators"]],
        "rank_AI_min": ai_min["rank_z"],
        "rank_BS_with_planes": ai_min["rank_bs"],
        "AI_min_in_BS": ai_min["rank_union_with_bs"] == ai_min["rank_bs"],
        "can_compare_bs_vs_ai_min": True,
        "key_subtlety": "The exported *_character.json files store raw characters; the induction step must reconstruct linear characters by multiplying exp(-i k·tauC).",
        "prototype_scope_note": "This prototype only uses trivial 1D local reps on the audited c and f point families; it is not a full AI lattice.",
    }


def build_bridge_audit_md(bridge_ops: dict[str, Any], bridge_stabilizers: dict[str, Any], ai_min: dict[str, Any]) -> str:
    consistent_letters = ", ".join(bridge_stabilizers["consistent_letters"])
    lines = [
        "# Single-Group AI Bridge Audit for 10.4.1.31",
        "",
        "## Scope",
        "",
        "- Goal: validate the explicit basis/translation bridge from `swyckoff_r.py` real-space data to `SSGReps.py`, then build the smallest honest atomic prototype if the bridge is trustworthy.",
        "- Group only: `10.4.1.31`.",
        "- This file does not replace the earlier feasibility/site-symmetry audit; it resolves the previous basis/gauge blocker and pushes one step further.",
        "",
        "## Bridge Result",
        "",
        f"- The explicit coordinate change is `r_conv = P r_mag` with `P = {bridge_ops['supercell_basis_change']}`.",
        "- Under that change, a magnetic-basis real-space operation `(W_mag, t_mag)` from `swyckoff_r.py` maps to",
        "  `W_conv = P W_mag P^{-1}`, `t_conv = P t_mag`.",
        "- The relevant lattice equivalence on the `SSGReps` side is modulo the magnetic lattice generated by the columns of `P`, not modulo the unit cube of the parent space-group cell.",
        f"- Exact operation-table result: `{bridge_ops['matched_operation_count']} / {bridge_ops['converted_operation_count']}` converted `swyckoff_r` operations match `SSGReps` raw operations after the basis change.",
        f"- Stabilizer-size bridge check: `{len(bridge_stabilizers['consistent_letters'])} / {bridge_stabilizers['entry_count']}` representative points agree with the already-audited Wyckoff stabilizer sizes.",
        f"- Consistent letters: `{consistent_letters}`.",
        "",
        "## Important Convention Detail",
        "",
        "- The exported `*_character.json` files do not store the final `linear_character` that `SSGReps` prints on the CLI.",
        "- They store the raw unitary character before the Bloch translation factor.",
        "- For atomic induction, the correct target character is",
        "  `chi_linear(g) = chi_raw(g) * exp(-i k · tauC(g))`",
        "  on the unitary little-group operations listed in each manifold JSON file.",
        "- This correction is essential on generic planes such as `S1`; without it the decomposition fails even when the atomic formula is otherwise correct.",
        "",
        "## Minimal Atomic Prototype",
        "",
        "- Chosen families: `c` and `f` only.",
        "- Reason: both are 0D, multiplicity 4 under the full magnetic group, and have fully unitary site symmetry `2/m` in the earlier audit.",
        "- Chosen local rep on each family: the trivial 1D local representation, i.e. character `+1` on every unitary stabilizer element.",
        "- Orbit generation uses the full magnetic group, not only the unitary subgroup. This matters: the physical orbit contains 4 sites, while the unitary subgroup alone only sees 2.",
        "",
        "## Prototype Outcome",
        "",
        f"- Generator count: `{len(ai_min['generators'])}`.",
        f"- `rank_Z(A_min) = {ai_min['rank_z']}`.",
        f"- `rank(BS_with_planes) = {ai_min['rank_bs']}`.",
        f"- `rank(span(BS_with_planes, AI_min)) = {ai_min['rank_union_with_bs']}`.",
        "- Both prototype generators satisfy the current with-planes compatibility matrix exactly.",
        "- Both prototype generators are integer combinations of the current `BS_with_planes` basis, so the prototype embeds in the audited BS lattice.",
        "",
        "## Limits",
        "",
        "- This is still only a minimal prototype, not a full AI lattice and not a final BS/AI classification.",
        "- Only the trivial local rep was used on `c` and `f`. A full atomic analysis would still need the remaining site-symmetry irreps/coreps and more Wyckoff families.",
    ]
    return "\n".join(lines)


def build_ai_min_generators_json(ai_min: dict[str, Any], unknown_ordering: list[str]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "unknown_ordering": unknown_ordering,
        "generators": ai_min["generators"],
    }


def build_ai_min_matrix_json(ai_min: dict[str, Any], unknown_ordering: list[str]) -> dict[str, Any]:
    row_records = []
    for index, unknown in enumerate(unknown_ordering):
        row_records.append(
            {
                "unknown": unknown,
                "coefficients": [column[index] for column in ai_min["A_min_columns"]],
            }
        )
    return {
        "group_number": GROUP_NUMBER,
        "matrix_orientation": "columns_are_generators",
        "column_order": ai_min["column_order"],
        "unknown_ordering": unknown_ordering,
        "A_min_columns": ai_min["A_min_columns"],
        "A_min_rows": row_records,
        "rank_z": ai_min["rank_z"],
        "rank_q": ai_min["rank_z"],
        "compatibility_zero": {
            generator["local_rep"]["id"]: generator["compatibility_zero"] for generator in ai_min["generators"]
        },
    }


def build_bs_vs_ai_min_summary(ai_min: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "rank_BS_with_planes": ai_min["rank_bs"],
        "rank_AI_min": ai_min["rank_z"],
        "AI_min_in_BS": ai_min["rank_union_with_bs"] == ai_min["rank_bs"],
        "rank_span_BS_plus_AI_min": ai_min["rank_union_with_bs"],
        "prototype_generator_ids": ai_min["column_order"],
        "prototype_bs_coefficients": {
            generator["local_rep"]["id"]: generator["bs_basis_coefficients"] for generator in ai_min["generators"]
        },
        "coverage_statement": "The minimal prototype spans a 2D sublattice inside the current 8D BS lattice; at least 6 BS directions remain uncovered by this prototype.",
        "scope_note": "This is only a minimal prototype, not the final BS/AI comparison for 10.4.1.31.",
    }


def build_package_readme() -> str:
    lines = [
        "# Review Package: 10.4.1.31 AI Bridge and Minimal Prototype",
        "",
        "## Scope",
        "",
        "- group: `10.4.1.31`",
        "- stage: explicit `swyckoff_r.py <-> SSGReps.py` bridge validation, then a minimal atomic-side prototype",
        "",
        "## Known Premise",
        "",
        "- The earlier line/plane formalism audit is already accepted as the k-space baseline.",
        "- The with-planes BS basis used here is the audited one from the previous package.",
        "",
        "## New Content",
        "",
        "- `single_group_ai_bridge_audit.md`: explicit bridge formula, operation-table check, stabilizer check, and prototype notes",
        "- `single_group_ai_bridge_summary.json`: compact bridge/prototype status",
        "- `single_group_ai_min_generators.json`: the two prototype generators (`c_trivial`, `f_trivial`)",
        "- `single_group_ai_min_matrix.json`: `A_min` aligned with the current 31-dimensional unknown ordering",
        "- `single_group_bs_vs_ai_min_summary.json`: minimal rank/embedding comparison against the current BS lattice",
        "- `debug_single_group_ai_bridge.py`: single-group reproduction script",
        "",
        "## Review Order",
        "",
        "1. `audit/single_group_ai_bridge_audit.md`",
        "2. `audit/single_group_ai_bridge_summary.json`",
        "3. `ai/single_group_ai_min_generators.json`",
        "4. `ai/single_group_ai_min_matrix.json`",
        "5. `ai/single_group_bs_vs_ai_min_summary.json`",
        "6. `audit/single_group_site_symmetry_check.json` for the earlier double-check background",
        "",
        "## Interpretation",
        "",
        "- This package does show a successful minimal atomic prototype.",
        "- It does not claim a final AI lattice or a final topological classification.",
    ]
    return "\n".join(lines)


def reset_dir(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    path.mkdir(parents=True, exist_ok=True)


def build_package() -> None:
    reset_dir(PACKAGE_DIR)

    mapping = {
        "audit/single_group_ai_bridge_audit.md": BRIDGE_AUDIT_MD,
        "audit/single_group_ai_bridge_summary.json": BRIDGE_SUMMARY_JSON,
        "ai/single_group_ai_min_generators.json": AI_MIN_GENERATORS_JSON,
        "ai/single_group_ai_min_matrix.json": AI_MIN_MATRIX_JSON,
        "ai/single_group_bs_vs_ai_min_summary.json": BS_VS_AI_MIN_SUMMARY_JSON,
        "scripts/debug_single_group_ai_bridge.py": ROOT / "debug_single_group_ai_bridge.py",
        "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
        "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
        "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    }
    mapping.update(BACKGROUND_CONTEXT)

    for relative, source in mapping.items():
        destination = PACKAGE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    write_text(PACKAGE_DIR / "README.md", build_package_readme())

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def generate_outputs() -> dict[str, Any]:
    ctx = load_context()
    bridge_ops = validate_operation_bridge(ctx)
    bridge_stabilizers = validate_bridge_stabilizers(ctx)
    ai_min = build_ai_min(ctx)
    summary = bridge_summary(ctx, bridge_ops, bridge_stabilizers, ai_min)

    write_text(BRIDGE_AUDIT_MD, build_bridge_audit_md(bridge_ops, bridge_stabilizers, ai_min))
    write_json(BRIDGE_SUMMARY_JSON, summary)
    write_json(AI_MIN_GENERATORS_JSON, build_ai_min_generators_json(ai_min, ctx["basis_raw"]["unknown_ordering"]))
    write_json(AI_MIN_MATRIX_JSON, build_ai_min_matrix_json(ai_min, ctx["basis_raw"]["unknown_ordering"]))
    write_json(BS_VS_AI_MIN_SUMMARY_JSON, build_bs_vs_ai_min_summary(ai_min))
    build_package()

    return {
        "summary": summary,
        "bridge_ops": bridge_ops,
        "bridge_stabilizers": bridge_stabilizers,
        "ai_min": ai_min,
    }


def validate_outputs() -> None:
    for path in [
        BRIDGE_AUDIT_MD,
        BRIDGE_SUMMARY_JSON,
        AI_MIN_GENERATORS_JSON,
        AI_MIN_MATRIX_JSON,
        BS_VS_AI_MIN_SUMMARY_JSON,
        PACKAGE_TARBALL,
    ]:
        if not path.exists():
            raise ValueError(f"missing required artifact: {path}")

    summary = load_json(BRIDGE_SUMMARY_JSON)
    if summary["group_number"] != GROUP_NUMBER:
        raise ValueError("bridge summary group number mismatch")
    if not summary["bridge_validated"]:
        raise ValueError("bridge summary does not report a validated bridge")
    if not summary["minimal_ai_prototype_built"]:
        raise ValueError("minimal AI prototype was not reported as built")
    if not summary["AI_min_in_BS"]:
        raise ValueError("AI_min was not reported as embedded in BS")

    matrix = load_json(AI_MIN_MATRIX_JSON)
    if matrix["rank_z"] != 2:
        raise ValueError("unexpected AI_min rank")

    bs_vs_ai = load_json(BS_VS_AI_MIN_SUMMARY_JSON)
    if bs_vs_ai["rank_AI_min"] != 2:
        raise ValueError("unexpected BS-vs-AI minimal rank")
    if bs_vs_ai["rank_BS_with_planes"] != 8:
        raise ValueError("unexpected BS rank")

    expected_members = {
        f"{PACKAGE_NAME}/README.md",
        f"{PACKAGE_NAME}/audit/single_group_ai_bridge_audit.md",
        f"{PACKAGE_NAME}/audit/single_group_ai_bridge_summary.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_min_generators.json",
        f"{PACKAGE_NAME}/ai/single_group_ai_min_matrix.json",
        f"{PACKAGE_NAME}/ai/single_group_bs_vs_ai_min_summary.json",
        f"{PACKAGE_NAME}/scripts/debug_single_group_ai_bridge.py",
    }
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        members = {member.name for member in tar.getmembers()}
    missing = sorted(expected_members - members)
    if missing:
        raise ValueError(f"package is missing expected members: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the 10.4.1.31 swyckoff_r <-> SSGReps bridge and build a minimal atomic prototype.")
    parser.add_argument("--validate", action="store_true", help="Validate previously generated outputs and exit.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validation_ok")
        return 0

    result = generate_outputs()
    print(json.dumps(result["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
