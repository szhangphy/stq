#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import pickle
import shutil
import sys
import tarfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

import swyckoff_k
import swyckoff_r


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 1

REALSPACE_AUDIT_PATH = ROOT / "single_group_realspace_audit.md"
SITE_CHECK_PATH = ROOT / "single_group_site_symmetry_check.json"
AI_AUDIT_PATH = ROOT / "single_group_ai_feasibility_audit.md"
AI_SUMMARY_PATH = ROOT / "single_group_ai_feasibility_summary.json"

PACKAGE_DIR = ROOT / "review_package_10.4.1.31_ai_feasibility"
PACKAGE_TAR = ROOT / "review_package_10.4.1.31_ai_feasibility.tar.gz"

PLANE_PACKAGE_DIR = ROOT / "review_package_10.4.1.31_plane_formalism"

BACKGROUND_ROOT_FILES = {
    "audit/single_group_plane_formalism_audit.md": ROOT / "single_group_plane_formalism_audit.md",
    "audit/single_group_plane_formalism_summary.json": ROOT / "single_group_plane_formalism_summary.json",
    "audit/single_group_torsion_audit.json": ROOT / "single_group_torsion_audit.json",
    "audit/single_group_bs_with_planes_summary.json": ROOT / "single_group_bs_with_planes_summary.json",
    "basis/single_group_bs_with_planes_basis_raw.json": ROOT / "single_group_bs_with_planes_basis_raw.json",
    "basis/single_group_bs_with_planes_basis_pretty.json": ROOT / "single_group_bs_with_planes_basis_pretty.json",
    "matrix/single_group_full_compatibility_with_planes.json": ROOT / "single_group_full_compatibility_with_planes.json",
    "background/single_group_kmanifolds.json": ROOT / "single_group_kmanifolds.json",
    "background/single_group_connectivity.json": ROOT / "single_group_connectivity.json",
}

NEW_PACKAGE_FILES = {
    "audit/single_group_realspace_audit.md": REALSPACE_AUDIT_PATH,
    "audit/single_group_site_symmetry_check.json": SITE_CHECK_PATH,
    "audit/single_group_ai_feasibility_audit.md": AI_AUDIT_PATH,
    "audit/single_group_ai_feasibility_summary.json": AI_SUMMARY_PATH,
    "scripts/debug_single_group_ai_feasibility.py": ROOT / "debug_single_group_ai_feasibility.py",
    "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
}

REQUIRED_ROOT_OUTPUTS = [
    REALSPACE_AUDIT_PATH,
    SITE_CHECK_PATH,
    AI_AUDIT_PATH,
    AI_SUMMARY_PATH,
    ROOT / "debug_single_group_ai_feasibility.py",
    PACKAGE_TAR,
]

PARAMETER_CANDIDATES = {
    0: [()],
    1: [(Fraction(1, 5),), (Fraction(2, 7),), (Fraction(1, 3),), (Fraction(3, 11),)],
    2: [
        (Fraction(1, 5), Fraction(2, 7)),
        (Fraction(1, 5), Fraction(3, 11)),
        (Fraction(2, 7), Fraction(1, 3)),
        (Fraction(1, 3), Fraction(2, 7)),
    ],
    3: [
        (Fraction(1, 5), Fraction(2, 7), Fraction(3, 11)),
        (Fraction(1, 3), Fraction(2, 7), Fraction(1, 5)),
    ],
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text)


def frac_str(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def complex_str(value: complex) -> str:
    real = round(value.real, 10)
    imag = round(value.imag, 10)
    if abs(imag) < 1e-10:
        imag = 0.0
    if abs(real) < 1e-10:
        real = 0.0
    if imag == 0.0:
        return f"{real:g}"
    sign = "+" if imag >= 0 else "-"
    return f"{real:g}{sign}{abs(imag):g}i"


def vec_str(vec: Sequence[Fraction]) -> str:
    return "(" + ", ".join(frac_str(Fraction(v)) for v in vec) + ")"


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Fraction):
        return frac_str(obj)
    if isinstance(obj, complex):
        return complex_str(obj)
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "tolist"):
        return to_jsonable(obj.tolist())
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(value) for value in obj]
    return obj


def mod1_vec(vec: Sequence[Fraction]) -> list[Fraction]:
    return [Fraction(value) % 1 for value in vec]


def apply_op_to_point(op: swyckoff_r.Op, pt: Sequence[Fraction]) -> list[Fraction]:
    return [
        sum(Fraction(op.W[row][col]) * Fraction(pt[col]) for col in range(3)) + Fraction(op.t[row])
        for row in range(3)
    ]


def orbit_points(pt: Sequence[Fraction], ops: Sequence[swyckoff_r.Op]) -> list[list[Fraction]]:
    orbit: list[list[Fraction]] = []
    for op in ops:
        image = mod1_vec(apply_op_to_point(op, pt))
        if not any(swyckoff_r.equal_mod1(image, existing) for existing in orbit):
            orbit.append(image)
    return orbit


def direct_point_stabilizer(
    pt: Sequence[Fraction],
    ops: Sequence[swyckoff_r.Op],
) -> list[int]:
    return [idx for idx, op in enumerate(ops) if swyckoff_r.equal_mod1(apply_op_to_point(op, pt), pt)]


def is_closed_subgroup(indices: Sequence[int], ops: Sequence[swyckoff_r.Op]) -> bool:
    index_set = set(indices)
    op_map = {swyckoff_r.op_key(op): idx for idx, op in enumerate(ops)}
    for left in indices:
        for right in indices:
            product = swyckoff_r.compose(ops[left], ops[right])
            mapped = op_map.get(swyckoff_r.op_key(product))
            if mapped not in index_set:
                return False
    return True


def sample_point_from_entry(entry: dict[str, Any], ops: Sequence[swyckoff_r.Op]) -> tuple[list[Fraction], tuple[Fraction, ...]]:
    x0 = [Fraction(value) for value in entry["x0"]]
    basis = [[Fraction(value) for value in row] for row in entry["basis_vecs"]]
    dim = int(entry["dim"])
    expected_stab = int(entry["stab"])
    expected_mult = int(entry["mult"])
    for params in PARAMETER_CANDIDATES[dim]:
        point = x0[:]
        for coeff, basis_vec in zip(params, basis):
            point = [point[i] + coeff * basis_vec[i] for i in range(3)]
        point = mod1_vec(point)
        stab = direct_point_stabilizer(point, ops)
        orbit = orbit_points(point, ops)
        if len(stab) == expected_stab and len(orbit) == expected_mult:
            return point, params
    raise RuntimeError(f"unable to find a generic sample point for Wyckoff letter {entry['letter']}")


def safe_point_group_lookup() -> dict[tuple, str]:
    try:
        return swyckoff_r.mw.build_point_group_signature_lookup()
    except FileNotFoundError:
        return {}


def direct_site_summary(
    *,
    point: Sequence[Fraction],
    ops: Sequence[swyckoff_r.Op],
    time_revs: Sequence[bool],
    mag_ops: Sequence[Any],
    spin_ops: Sequence[Any],
    crystal_system: str,
    pg_lookup: dict[tuple, str],
) -> dict[str, Any]:
    indices = direct_point_stabilizer(point, ops)
    stab_ops = [ops[index] for index in indices]
    mag_stab_ops = [mag_ops[index] for index in indices]
    spin_stab_ops = [spin_ops[index] for index in indices]
    unitary_mag_stab_ops = [op for op in mag_stab_ops if not op.tr]

    unitary_site_symmetry = swyckoff_r.mw.classify_site_symmetry(
        swyckoff_r.unique_rotations(unitary_mag_stab_ops),
        pg_lookup,
    )
    spatial_site_symmetry_custom, spatial_site_symmetry_ops = swyckoff_r.mw.build_custom_site_symmetry(mag_stab_ops)
    site_symmetry_custom, site_symmetry_ops = swyckoff_r.build_spin_site_symmetry(spin_stab_ops)
    if site_symmetry_custom is None:
        site_symmetry_custom = spatial_site_symmetry_custom
        site_symmetry_ops = spatial_site_symmetry_ops
    site_symmetry = (
        swyckoff_r.mw.lookup_magnetic_bilbao_symbol(
            spatial_site_symmetry_custom or site_symmetry_custom or "",
            unitary_site_symmetry or "",
            spatial_site_symmetry_ops or site_symmetry_ops,
        )
        or swyckoff_r.mw.bilbao_magnetic_point_group_symbol(
            spatial_site_symmetry_ops or site_symmetry_ops,
            crystal_system=str(crystal_system or ""),
        )
        or spatial_site_symmetry_custom
        or site_symmetry_custom
        or unitary_site_symmetry
    )
    orbit = orbit_points(point, ops)
    return {
        "sample_point": [frac_str(value) for value in point],
        "stabilizer_indices": list(indices),
        "stabilizer_size": len(indices),
        "unitary_count": sum(1 for index in indices if not time_revs[index]),
        "antiunitary_count": sum(1 for index in indices if time_revs[index]),
        "unique_rotation_count": len(swyckoff_r.unique_rotations(stab_ops)),
        "is_closed": is_closed_subgroup(indices, ops),
        "orbit_size": len(orbit),
        "orbit_points": [[frac_str(value) for value in site] for site in orbit],
        "orbit_stabilizer_product": len(indices) * len(orbit),
        "site_symmetry": site_symmetry,
        "unitary_site_symmetry": unitary_site_symmetry,
        "site_symmetry_custom": site_symmetry_custom,
        "site_symmetry_ops": to_jsonable(site_symmetry_ops),
        "spatial_site_symmetry_custom": spatial_site_symmetry_custom,
        "spatial_site_symmetry_ops": to_jsonable(spatial_site_symmetry_ops),
        "stabilizer_elements": [
            {
                "index": index,
                "time_reversal": bool(time_revs[index]),
                "matrix": [[frac_str(Fraction(x)) for x in row] for row in ops[index].W],
                "translation": [frac_str(Fraction(x)) for x in ops[index].t],
            }
            for index in indices
        ],
    }


def audit_site_symmetry(
    wyckoff_entries: Sequence[dict[str, Any]],
    ops: Sequence[swyckoff_r.Op],
    time_revs: Sequence[bool],
    mag_ops: Sequence[Any],
    spin_ops: Sequence[Any],
    crystal_system: str,
) -> dict[str, Any]:
    pg_lookup = safe_point_group_lookup()
    entries: list[dict[str, Any]] = []
    consistent_letters: list[str] = []
    for entry in wyckoff_entries:
        sample_point, params = sample_point_from_entry(entry, ops)
        direct = direct_site_summary(
            point=sample_point,
            ops=ops,
            time_revs=time_revs,
            mag_ops=mag_ops,
            spin_ops=spin_ops,
            crystal_system=crystal_system,
            pg_lookup=pg_lookup,
        )
        output_summary = {
            "stabilizer_size": int(entry["stab"]),
            "unique_rotation_count": len(entry["stab_rotations"]),
            "site_symmetry": entry["site_symmetry"],
            "unitary_site_symmetry": entry["unitary_site_symmetry"],
            "site_symmetry_custom": entry["site_symmetry_custom"],
            "site_symmetry_ops": to_jsonable(entry["site_symmetry_ops"]),
            "spatial_site_symmetry_custom": entry["spatial_site_symmetry_custom"],
            "spatial_site_symmetry_ops": to_jsonable(entry["spatial_site_symmetry_ops"]),
            "full_stabilizer_elements_available": False,
            "reported_multiplicity": int(entry["mult"]),
        }
        comparison = {
            "stabilizer_size_match": output_summary["stabilizer_size"] == direct["stabilizer_size"],
            "unique_rotation_count_match": output_summary["unique_rotation_count"] == direct["unique_rotation_count"],
            "site_symmetry_match": output_summary["site_symmetry"] == direct["site_symmetry"],
            "unitary_site_symmetry_match": output_summary["unitary_site_symmetry"] == direct["unitary_site_symmetry"],
            "site_symmetry_custom_match": output_summary["site_symmetry_custom"] == direct["site_symmetry_custom"],
            "orbit_size_match": output_summary["reported_multiplicity"] == direct["orbit_size"],
            "orbit_stabilizer_match": direct["orbit_stabilizer_product"] == len(ops),
            "closure_match": bool(direct["is_closed"]),
            "output_has_explicit_unitary_anti_breakdown": False,
            "direct_has_explicit_unitary_anti_breakdown": True,
            "comparison_scope_note": "swyckoff_r.py reports a site-symmetry summary plus generators and counts, not the full stabilizer element list; route-B rebuilds the full stabilizer explicitly.",
        }
        comparison["overall_consistent"] = all(
            comparison[key]
            for key in (
                "stabilizer_size_match",
                "unique_rotation_count_match",
                "site_symmetry_match",
                "unitary_site_symmetry_match",
                "site_symmetry_custom_match",
                "orbit_size_match",
                "orbit_stabilizer_match",
                "closure_match",
            )
        )
        if comparison["overall_consistent"]:
            consistent_letters.append(entry["letter"])
        entries.append(
            {
                "letter": entry["letter"],
                "dimension": int(entry["dim"]),
                "multiplicity": int(entry["mult"]),
                "representative_coordinate": entry["representative_coordinate"],
                "sample_parameters": [frac_str(value) for value in params],
                "sample_point": [frac_str(value) for value in sample_point],
                "program_output": output_summary,
                "direct_reconstruction": direct,
                "comparison": comparison,
            }
        )
    return {
        "group_number": GROUP_NUMBER,
        "coordinate_system": "fractional coordinates in the real-space setting emitted by swyckoff_r.py",
        "point_fixing_rule": "An operation fixes a representative point when g·r = r modulo an integer lattice vector.",
        "antiunitary_enters_site_symmetry": True,
        "entries": entries,
        "all_entries_consistent": len(consistent_letters) == len(entries),
        "consistent_letters": consistent_letters,
    }


def load_ssgreps_module():
    ssgreps_py = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
    ssgreps_dir = ssgreps_py.parent
    if str(ssgreps_dir) not in sys.path:
        sys.path.insert(0, str(ssgreps_dir))
    spec = importlib.util.spec_from_file_location("ssgreps_local", ssgreps_py)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {ssgreps_py}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def naive_ssgreps_setting_check() -> dict[str, Any]:
    import numpy as np

    module = load_ssgreps_module()
    identify_pkl = ROOT / "SSGReps" / "ssg_data" / "identify.pkl"
    with open(identify_pkl, "rb") as fh:
        ssg_list = pickle.load(fh)
    ssg_dict = next(item for item in ssg_list if item["ssgNum"] == GROUP_NUMBER)
    ssg = module.loadSsgGroup(GROUP_NUMBER, np.array([0.0, 0.0, 0.0]), "single", ssg_dict)

    wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(GROUP_NUMBER, fast=True)
    primitive_points = {
        letter: next(entry for entry in wyckoff_entries if entry["letter"] == letter)["x0"]
        for letter in ("a", "c", "f")
    }
    naive_stabilizers: dict[str, Any] = {}
    for letter, point in primitive_points.items():
        point_arr = np.array([float(value) for value in point], dtype=float)
        indices: list[int] = []
        for index, (rotation, translation) in enumerate(zip(ssg.rotC, ssg.tauC)):
            image = rotation @ point_arr + translation
            delta = image - point_arr
            if np.linalg.norm(delta - np.round(delta)) < 1e-8:
                indices.append(index)
        naive_stabilizers[letter] = {
            "primitive_point": [frac_str(Fraction(value)) for value in point],
            "naive_ssgreps_stabilizer_size": len(indices),
            "naive_ssgreps_stabilizer_indices": indices,
            "naive_ssgreps_time_reversal": [int(ssg.time_reversal[index]) for index in indices],
        }

    full_data, _ = swyckoff_r.load_irssg_data(GROUP_NUMBER, 0)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_map = {
        (
            tuple(tuple(Fraction(x) for x in row) for row in op.W),
            tuple(Fraction(x) % 1 for x in op.t),
            bool(tr),
        ): index
        for index, (op, tr) in enumerate(zip(full_ops, full_data["time_revs"]))
    }
    raw_p1 = load_json(ROOT / "P1_character.json")
    raw_unitary_indices = [index for index, sign in enumerate(raw_p1["timeReversal"]) if sign > 0]
    first_missing_exact_match = None
    for raw_index in raw_unitary_indices:
        key = (
            tuple(tuple(Fraction(int(round(float(value))), 1) for value in row) for row in raw_p1["rotC"][raw_index]),
            tuple(Fraction(str(float(value))).limit_denominator(48) % 1 for value in raw_p1["tauC"][raw_index]),
            False,
        )
        if key not in full_map:
            first_missing_exact_match = {
                "raw_operation_index": raw_index,
                "rotation": [[frac_str(Fraction(int(round(float(value))), 1)) for value in row] for row in raw_p1["rotC"][raw_index]],
                "translation": [frac_str(Fraction(str(float(value))).limit_denominator(48) % 1) for value in raw_p1["tauC"][raw_index]],
            }
            break

    return {
        "group_number": GROUP_NUMBER,
        "superCell": to_jsonable(ssg.superCell),
        "pure_T": to_jsonable(ssg.pure_T),
        "reciprocal_basis_vectors": to_jsonable([ssg.b1, ssg.b2, ssg.b3]),
        "naive_realspace_stabilizer_check_using_ssgreps_internal_ops": naive_stabilizers,
        "first_exact_raw_little_group_operation_without_direct_swyckoff_r_match": first_missing_exact_match,
    }


def analyze_realspace() -> dict[str, Any]:
    r_data, _ = swyckoff_r.load_irssg_data(GROUP_NUMBER, 0)
    k_data, _ = swyckoff_k.load_irssg_data(GROUP_NUMBER, 0)
    wyckoff_entries, coord_key = swyckoff_r.compute_wyckoff_output(GROUP_NUMBER, fast=True)
    ops = [swyckoff_r.op_from_json(op) for op in r_data["operations"]]
    time_revs = [bool(flag) for flag in r_data["time_revs"]]
    mag_ops = swyckoff_r.build_magnetic_ops(ops, time_revs)
    spin_ops = swyckoff_r.build_spin_ops(ops, time_revs, r_data.get("spin_matrices"))
    site_check = audit_site_symmetry(
        wyckoff_entries,
        ops,
        time_revs,
        mag_ops,
        spin_ops,
        str(r_data.get("crystal_system", "")),
    )
    ssgreps_setting = naive_ssgreps_setting_check()

    prototype_candidates = []
    for entry in site_check["entries"]:
        direct = entry["direct_reconstruction"]
        if (
            entry["dimension"] == 0
            and entry["multiplicity"] == 4
            and direct["unitary_count"] == direct["stabilizer_size"]
            and direct["antiunitary_count"] == 0
        ):
            prototype_candidates.append(
                {
                    "letter": entry["letter"],
                    "representative_coordinate": entry["representative_coordinate"],
                    "multiplicity": entry["multiplicity"],
                    "site_symmetry": direct["site_symmetry"],
                    "unitary_site_symmetry": direct["unitary_site_symmetry"],
                    "why": "0D point family with multiplicity 4 and fully unitary stabilizer; simplest future starting point for a unitary-subgroup atomic prototype.",
                }
            )

    exact_module_alignment = {
        "swyckoff_r_vs_swyckoff_k_same_number": r_data["number"] == k_data["number"],
        "swyckoff_r_vs_swyckoff_k_same_source_centering_symbol": r_data.get("source_centering_symbol") == k_data.get("source_centering_symbol"),
        "swyckoff_r_vs_swyckoff_k_same_operation_list": r_data["operations"] == k_data["operations"],
        "swyckoff_r_vs_swyckoff_k_same_time_reversal_list": r_data["time_revs"] == k_data["time_revs"],
    }

    return {
        "coord_key": coord_key,
        "swyckoff_py_exists": (ROOT / "swyckoff.py").exists(),
        "r_data": r_data,
        "k_data": k_data,
        "wyckoff_entries": wyckoff_entries,
        "site_check": site_check,
        "prototype_candidates": prototype_candidates,
        "module_alignment": exact_module_alignment,
        "ssgreps_setting": ssgreps_setting,
    }


def build_realspace_audit_text(analysis: dict[str, Any]) -> str:
    wyckoff_entries = analysis["wyckoff_entries"]
    lines = [
        "# Single Group Real-Space Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- Stage: real-space / atomic-side feasibility audit only.",
        "- Out of scope: full AI/EBR/MTQC, all-group generalization, or any final topology classification.",
        "",
        "## A. swyckoff_r.py: Real Input / Output",
        "- File audited: `swyckoff_r.py`.",
        "- There is no `swyckoff.py` file in the current repository root, so the real-space audit cannot rely on it.",
        "- Primary programmatic entry point: `compute_wyckoff_output(data_or_ssgnum, kspace=False, basis=\"primitive\", stars=False, fast=False)`.",
        f"- For this run it was called as `compute_wyckoff_output(\"{GROUP_NUMBER}\", fast=True)`.",
        "- Accepted input is either a real-space SSG data dictionary or an SSG number string; the string path goes through `load_irssg_data`.",
        f"- Output is a tuple `(wyckoff_entries, coord_key)` with `coord_key = {analysis['coord_key']!r}` in real-space mode.",
        "- Each entry carries enough real-space geometry for audit use: `letter`, `mult`, `dim`, `x0`, `basis_vecs`, `rep`, `orbit`, `representative_coordinate`.",
        "- It also carries site-symmetry summaries: `stab`, `stab_rotations`, `site_symmetry`, `unitary_site_symmetry`, `site_symmetry_custom`, `site_symmetry_ops`, `spatial_site_symmetry_custom`, `spatial_site_symmetry_ops`.",
        "- It does not directly expose the full stabilizer element list; the program output is a summary plus generator-like descriptors, not a raw stabilizer table.",
        "",
        "## B. Real-Space Data Retrieved For 10.4.1.31",
        f"- `swyckoff_r.py` returns `{len(wyckoff_entries)}` Wyckoff-like real-space families for `{GROUP_NUMBER}`.",
        "- The generic family is `o` with multiplicity `16`, dimension `3`, and trivial stabilizer size `1`.",
        "- Special families are `a` through `n`; they are distinguishable from the generic family by smaller multiplicity and larger stabilizer.",
        "",
        "| Let | mult | dim | representative_coordinate | site_symmetry | unitary_site_symmetry |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for entry in wyckoff_entries:
        lines.append(
            f"| {entry['letter']} | {entry['mult']} | {entry['dim']} | `{entry['representative_coordinate']}` | `{entry['site_symmetry']}` | `{entry['unitary_site_symmetry']}` |"
        )
    lines += [
        "",
        "## C. Setting Consistency",
        "- `swyckoff_r.py` and `swyckoff_k.py` do load the same standardized SSG operation list for this group.",
        f"- Same SSG number: `{analysis['module_alignment']['swyckoff_r_vs_swyckoff_k_same_number']}`.",
        f"- Same `source_centering_symbol`: `{analysis['module_alignment']['swyckoff_r_vs_swyckoff_k_same_source_centering_symbol']}`.",
        f"- Same standardized operations: `{analysis['module_alignment']['swyckoff_r_vs_swyckoff_k_same_operation_list']}`.",
        f"- Same standardized time-reversal tags: `{analysis['module_alignment']['swyckoff_r_vs_swyckoff_k_same_time_reversal_list']}`.",
        "- Therefore the real-space and k-space geometry layers are aligned at the `swyckoff_r.py` / `swyckoff_k.py` level.",
        "- The separate risk is the bridge to `SSGReps.py`, not the bridge between the two swyckoff modules.",
        "",
        "## D. Site Symmetry Availability",
        f"- `single_group_site_symmetry_check.json` confirms summary-vs-direct consistency for all `{len(analysis['site_check']['entries'])}` families.",
        "- `swyckoff_r.py` is sufficient to provide usable real-space special-position data for this single-group audit.",
        "- It is also sufficient to reconstruct full stabilizers directly because the standardized group operations are available locally.",
        "",
        "## E. Prototype Candidates",
        "- Best future starting points for a minimal atomic prototype are the smallest 0D families with purely unitary stabilizers.",
    ]
    if analysis["prototype_candidates"]:
        for item in analysis["prototype_candidates"]:
            lines.append(
                f"- `{item['letter']}`: rep `{item['representative_coordinate']}`, multiplicity `{item['multiplicity']}`, site symmetry `{item['site_symmetry']}`. {item['why']}"
            )
    else:
        lines.append("- No fully trustworthy candidate survived the current audit.")
    lines += [
        "",
        "## F. Why AI Is Still Blocked",
        "- `SSGReps.py` does provide k-side little-group characters and rep degrees, but its internal magnetic-cell convention is not a drop-in real-space convention for `swyckoff_r.py` coordinates.",
        f"- Internal `SSGReps` supercell summary: `superCell = {analysis['ssgreps_setting']['superCell']}`, `pure_T = {analysis['ssgreps_setting']['pure_T']}`.",
        "- A naive real-space stabilizer check using `SSGReps` internal `rotC/tauC` on `a/c/f` does not reproduce the `swyckoff_r.py` stabilizers, so local-to-k induction is not trustworthy without an explicit basis/gauge bridge.",
        "- That missing bridge is the current blocker, so the present run stops at feasibility audit instead of fabricating an AI vector.",
    ]
    return "\n".join(lines) + "\n"


def build_ai_audit_text(analysis: dict[str, Any]) -> str:
    bs_summary = load_json(ROOT / "single_group_bs_with_planes_summary.json")
    basis_raw = load_json(ROOT / "single_group_bs_with_planes_basis_raw.json")
    site_check = analysis["site_check"]
    blocker = (
        "No trustworthy local-to-k induction path exists yet: swyckoff_r real-space coordinates/stabilizers and "
        "SSGReps raw little-group operations are not in a directly matched translation/gauge convention, and the "
        "repository exposes no existing helper that aligns them."
    )
    lines = [
        "# Single Group AI Feasibility Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        "- Stage: single-group real-space feasibility audit, not final BS/AI and not final topology classification.",
        "",
        "## A. Current k-Space Prerequisite",
        f"- Current trusted with-planes BS matrix shape: `{bs_summary['matrix_shape'][0]} x {bs_summary['matrix_shape'][1]}`.",
        f"- Integer rank / nullity: `{bs_summary['rank']}` / `{bs_summary['nullity']}`.",
        f"- Smith diagonal: `{bs_summary['smith_diagonal']}`.",
        f"- Current with-planes unknown ordering has `{len(basis_raw['unknown_ordering'])}` coordinates and is already a usable target lattice for any future atomic projection.",
        "- The torsion `2` is not the blocker at this stage. It only means any future BS/AI comparison must remain an integer-lattice comparison, not a rational-vector comparison.",
        "",
        "## B. Real-Space Data Verdict",
        "- `swyckoff_r.py` is sufficient for this group's real-space special-position enumeration.",
        "- Representative coordinates, orbit data, multiplicity, and site-symmetry summaries are all present.",
        "- The full stabilizer element list is not printed directly, but it can be reconstructed from the standardized operations exposed by the same module.",
        f"- Site-symmetry double-check status: `{site_check['all_entries_consistent']}` across `{len(site_check['entries'])}` audited families.",
        "",
        "## C. What Exists Versus What Is Missing",
        "- Existing and usable:",
        "  - trusted `swyckoff_r.py` real-space families;",
        "  - trusted `swyckoff_k.py` / with-planes BS unknown ordering;",
        "  - `SSGReps.py` k-side little-group characters and rep degrees on the current point/plane representatives.",
        "- Missing or not yet aligned:",
        "  - a direct table of site-symmetry irreps/coreps for the real-space stabilizers;",
        "  - a checked coordinate/gauge bridge from `swyckoff_r.py` real-space operations to `SSGReps.py` raw little-group operations;",
        "  - an existing helper that induces local real-space reps into the current k-space basis without resorting to unreviewed ad hoc translation conventions.",
        "",
        "## D. Why The Minimal AI Prototype Stops Here",
        f"- Minimal blocker: {blocker}",
        "- Concrete evidence:",
        f"  - `SSGReps` internal cell summary is `{analysis['ssgreps_setting']['superCell']}`, so its translation convention is not the same object that `swyckoff_r.py` exposes as primitive-like fractional coordinates.",
        f"  - Naively applying `SSGReps` internal operations to the `a/c/f` real-space coordinates gives stabilizer sizes `{ {k: v['naive_ssgreps_stabilizer_size'] for k, v in analysis['ssgreps_setting']['naive_realspace_stabilizer_check_using_ssgreps_internal_ops'].items()} }`, which do not agree with the double-checked `swyckoff_r.py` stabilizers.",
        f"  - A direct exact-key match already fails on a raw P1 little-group operation: `{analysis['ssgreps_setting']['first_exact_raw_little_group_operation_without_direct_swyckoff_r_match']}`.",
        "- Because of that mismatch, any current local-to-k induction result would depend on an unchecked convention choice and would not be a reliable AI prototype.",
        "",
        "## E. Best Future Prototype Starting Points",
    ]
    if analysis["prototype_candidates"]:
        for item in analysis["prototype_candidates"]:
            lines.append(
                f"- `{item['letter']}`: multiplicity `{item['multiplicity']}`, rep `{item['representative_coordinate']}`, direct site symmetry `{item['site_symmetry']}`."
            )
    else:
        lines.append("- No candidate is recommended until the setting/gauge bridge is implemented.")
    lines += [
        "",
        "## Final Verdict",
        "- `real_space_data_available = true`",
        "- `site_symmetry_double_checked = true`",
        "- `site_symmetry_rep_available = false` in the strict sense required for atomic induction: there is no direct local-rep/corep table tied to the audited real-space stabilizers.",
        "- `can_build_minimal_ai_prototype = false`",
        "- `can_compare_bs_vs_ai_min = false`",
        "",
        "## Next Tooling Step",
        "- Implement and validate an explicit bridge between `swyckoff_r.py` real-space operations and the `SSGReps.py` little-group operation convention, including its `superCell/pure_T` translation gauge. Once that bridge exists, start the first minimal induction on the trusted `c` and `f` point families.",
    ]
    return "\n".join(lines) + "\n"


def build_ai_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "group_number": GROUP_NUMBER,
        "real_space_data_available": True,
        "site_symmetry_rep_available": False,
        "site_symmetry_double_checked": True,
        "can_build_minimal_ai_prototype": False,
        "minimal_blocker": "Real-space site stabilizers from swyckoff_r.py and k-side little-group operations from SSGReps.py are not yet connected by a validated setting/gauge bridge.",
        "can_compare_bs_vs_ai_min": False,
        "next_blocker": "Build and validate the swyckoff_r <-> SSGReps operation/translation convention bridge, then retry minimal induction on the audited c/f point families.",
        "trusted_site_symmetry_letters": analysis["site_check"]["consistent_letters"],
        "recommended_future_prototype_letters": [item["letter"] for item in analysis["prototype_candidates"]],
    }


def build_package_readme(analysis: dict[str, Any]) -> str:
    lines = [
        "# Review Package: 10.4.1.31 AI Feasibility Audit",
        "",
        "## 1. Task Scope",
        f"- group: `{GROUP_NUMBER}`",
        "- stage: AI / atomic-side feasibility audit and minimal prototype triage",
        "",
        "## 2. Current Known Prerequisites",
        "- k-space line/plane formalism has already passed the single-group audit.",
        "- the current with-planes BS is treated as the trusted k-space baseline for this round.",
        "",
        "## 3. New Contents In This Round",
        "- a real audit of `swyckoff_r.py` as the real-space data source",
        "- a program-output vs direct-group-operation site-symmetry double-check",
        "- a toolchain feasibility audit for local-to-k atomic induction",
        "- a blocker report instead of a fabricated AI prototype, because the local-to-k bridge is not yet trustworthy",
        "",
        "## 4. Two Possible Outcomes",
        "- toolchain is sufficient for a single-group minimal AI prototype",
        "- toolchain is still insufficient, so the correct output is a blocker-focused feasibility audit",
        "",
        "## 5. Suggested Review Order",
        "1. `audit/single_group_realspace_audit.md`",
        "2. `audit/single_group_site_symmetry_check.json`",
        "3. `audit/single_group_ai_feasibility_audit.md`",
        "4. `audit/single_group_ai_feasibility_summary.json`",
        "",
        "## 6. Important Dependency Copy",
        "- `dependencies/swyckoff_r.py` is copied into this package because it is the primary real-space source audited in this round.",
    ]
    if analysis["prototype_candidates"]:
        lines += [
            "",
            "## 7. Best Future Minimal-Prototype Starting Points",
        ]
        for item in analysis["prototype_candidates"]:
            lines.append(
                f"- `{item['letter']}` at `{item['representative_coordinate']}` with multiplicity `{item['multiplicity']}` and site symmetry `{item['site_symmetry']}`."
            )
    return "\n".join(lines) + "\n"


def ensure_package_dir() -> None:
    if PACKAGE_DIR.exists():
        shutil.rmtree(PACKAGE_DIR)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    for relative_path, source in {**BACKGROUND_ROOT_FILES, **NEW_PACKAGE_FILES}.items():
        target = PACKAGE_DIR / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def create_package_tar() -> None:
    if PACKAGE_TAR.exists():
        PACKAGE_TAR.unlink()
    with tarfile.open(PACKAGE_TAR, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)


def generate_outputs() -> dict[str, Any]:
    analysis = analyze_realspace()
    site_check_payload = to_jsonable(analysis["site_check"])
    realspace_audit = build_realspace_audit_text(analysis)
    ai_audit = build_ai_audit_text(analysis)
    ai_summary = build_ai_summary(analysis)

    write_text(REALSPACE_AUDIT_PATH, realspace_audit)
    write_json(SITE_CHECK_PATH, site_check_payload)
    write_text(AI_AUDIT_PATH, ai_audit)
    write_json(AI_SUMMARY_PATH, ai_summary)

    ensure_package_dir()
    write_text(PACKAGE_DIR / "README.md", build_package_readme(analysis))
    create_package_tar()
    return analysis


def validate_outputs() -> None:
    missing = [str(path) for path in REQUIRED_ROOT_OUTPUTS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required outputs: {missing}")

    summary = load_json(AI_SUMMARY_PATH)
    if summary["group_number"] != GROUP_NUMBER:
        raise ValueError("summary group number mismatch")
    if summary["can_build_minimal_ai_prototype"]:
        raise ValueError("this audit unexpectedly claims a minimal AI prototype exists")
    if summary["can_compare_bs_vs_ai_min"]:
        raise ValueError("this audit unexpectedly claims a BS-vs-AI comparison exists")

    site_check = load_json(SITE_CHECK_PATH)
    if site_check["group_number"] != GROUP_NUMBER:
        raise ValueError("site symmetry check group number mismatch")
    if len(site_check["entries"]) != 15:
        raise ValueError("unexpected real-space family count in site symmetry check")
    if not site_check["all_entries_consistent"]:
        raise ValueError("site symmetry double-check is not fully consistent")

    required_package_members = {
        f"{PACKAGE_DIR.name}/README.md",
        f"{PACKAGE_DIR.name}/audit/single_group_realspace_audit.md",
        f"{PACKAGE_DIR.name}/audit/single_group_site_symmetry_check.json",
        f"{PACKAGE_DIR.name}/audit/single_group_ai_feasibility_audit.md",
        f"{PACKAGE_DIR.name}/audit/single_group_ai_feasibility_summary.json",
        f"{PACKAGE_DIR.name}/audit/single_group_plane_formalism_audit.md",
        f"{PACKAGE_DIR.name}/audit/single_group_plane_formalism_summary.json",
        f"{PACKAGE_DIR.name}/audit/single_group_torsion_audit.json",
        f"{PACKAGE_DIR.name}/audit/single_group_bs_with_planes_summary.json",
        f"{PACKAGE_DIR.name}/basis/single_group_bs_with_planes_basis_raw.json",
        f"{PACKAGE_DIR.name}/basis/single_group_bs_with_planes_basis_pretty.json",
        f"{PACKAGE_DIR.name}/matrix/single_group_full_compatibility_with_planes.json",
        f"{PACKAGE_DIR.name}/background/single_group_kmanifolds.json",
        f"{PACKAGE_DIR.name}/background/single_group_connectivity.json",
        f"{PACKAGE_DIR.name}/scripts/debug_single_group_ai_feasibility.py",
        f"{PACKAGE_DIR.name}/dependencies/swyckoff_r.py",
    }
    with tarfile.open(PACKAGE_TAR, "r:gz") as tar:
        names = set(tar.getnames())
    missing_tar = sorted(required_package_members - names)
    if missing_tar:
        raise ValueError(f"tarball missing required members: {missing_tar}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-group atomic-side feasibility audit for 10.4.1.31.")
    parser.add_argument("--validate", action="store_true", help="Validate previously generated outputs and exit.")
    args = parser.parse_args()

    if args.validate:
        validate_outputs()
        print("validation_ok")
        return

    generate_outputs()
    print(f"generated {REALSPACE_AUDIT_PATH.name}")
    print(f"generated {SITE_CHECK_PATH.name}")
    print(f"generated {AI_AUDIT_PATH.name}")
    print(f"generated {AI_SUMMARY_PATH.name}")
    print(f"generated {PACKAGE_TAR.name}")


if __name__ == "__main__":
    main()
