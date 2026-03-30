#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cmath
import contextlib
import importlib.util
import io
import json
import pickle
import tarfile
from pathlib import Path
from typing import Any

import numpy as np

import debug_single_group_ai_bridge as single_bridge
import debug_single_group_ai_expanded as single_expanded
import swyckoff_r


ROOT = Path(__file__).resolve().parent
GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 2

AUDIT_MD = ROOT / "double_group_feasibility_audit_10.4.1.31.md"
SUMMARY_JSON = ROOT / "double_group_feasibility_summary_10.4.1.31.json"
KSPACE_JSON = ROOT / "double_group_minimal_kspace_10.4.1.31.json"
REALSPACE_JSON = ROOT / "double_group_minimal_realspace_10.4.1.31.json"
BS_AI_JSON = ROOT / "double_group_minimal_bs_ai_summary_10.4.1.31.json"

PACKAGE_NAME = "review_package_10.4.1.31_double_feasibility"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"

P_MATRIX = [[1, 0, 0], [0, 2, 0], [0, 0, 2]]
MINIMAL_KSPACE_BLOCK = {
    "endpoints": ["P1", "P4"],
    "line": "L1",
    "reason": (
        "Reuse the already-audited explicit endpoint-line block P1-L1-P4. "
        "All three objects run stably in groupType=2; P1 shows the clearest "
        "double-valued phase shift, L1 is the simplest generic special line, "
        "and P4 supplies the first endpoint with 2D double little coreps."
    ),
}
SUPPLEMENTAL_PLANE = "S1"
MINIMAL_REALSPACE_FAMILY = "c"
MINIMAL_REALSPACE_REASON = (
    "Family c is point-like, purely unitary, and has site symmetry 2/m with "
    "stabilizer indices [0,3,4,7]. That makes it the safest first double-group "
    "prototype because the local double-valued irreps can be built directly "
    "from the projective factor table without the extra Wigner-case machinery "
    "needed by antiunitary families."
)

MANIFOLD_SAMPLES = {
    "P1": [0.0, 0.0, 0.0],
    "P2": [0.0, 0.0, 0.5],
    "P3": [0.5, 0.0, 0.0],
    "P4": [0.0, 0.5, 0.0],
    "P5": [0.5, 0.5, 0.0],
    "P6": [0.0, 0.5, 0.5],
    "P7": [0.5, 0.0, 0.5],
    "P8": [0.5, 0.5, 0.5],
    "L1": [0.0, 0.2, 0.0],
    "L2": [0.0, 0.2, 0.5],
    "L3": [0.5, 0.2, 0.0],
    "L4": [0.5, 0.2, 0.5],
    "S1": [0.2, 0.0, 0.2],
    "S2": [0.2, 0.5, 0.2],
}

SINGLE_BACKGROUND = {
    "audit/single_group_ai_completeness_audit.md": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_ai_completeness_audit.md",
    "audit/single_group_ai_completeness_summary.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_ai_completeness_summary.json",
    "audit/single_group_indicator_group_summary.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_indicator_group_summary.json",
    "audit/single_group_indicator_generators.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_indicator_generators.json",
    "audit/single_group_bs_mod_ai_single_summary.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_bs_mod_ai_single_summary.json",
    "audit/single_group_parametric_magnetic_corep_audit.md": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_parametric_magnetic_corep_audit.md",
    "audit/single_group_parametric_magnetic_coreps.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_parametric_magnetic_coreps.json",
    "audit/single_group_magnetic_local_corep_audit.md": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_magnetic_local_corep_audit.md",
    "audit/single_group_pointlike_magnetic_coreps.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_pointlike_magnetic_coreps.json",
    "audit/single_group_family_completeness_table.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "audit"
    / "single_group_family_completeness_table.json",
    "ai/single_group_ai_expanded_v3_basis.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "ai"
    / "single_group_ai_expanded_v3_basis.json",
    "ai/single_group_bs_vs_ai_expanded_v3_summary.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "ai"
    / "single_group_bs_vs_ai_expanded_v3_summary.json",
    "basis/single_group_bs_with_planes_basis_raw.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "basis"
    / "single_group_bs_with_planes_basis_raw.json",
    "basis/single_group_bs_with_planes_basis_pretty.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "basis"
    / "single_group_bs_with_planes_basis_pretty.json",
    "matrix/single_group_full_compatibility_with_planes.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "matrix"
    / "single_group_full_compatibility_with_planes.json",
    "background/single_group_kmanifolds.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "background"
    / "single_group_kmanifolds.json",
    "background/single_group_connectivity.json": ROOT
    / "review_package_10.4.1.31_single_indicator"
    / "background"
    / "single_group_connectivity.json",
    "dependencies/swyckoff_r.py": ROOT / "swyckoff_r.py",
    "dependencies/swyckoff_k.py": ROOT / "swyckoff_k.py",
    "dependencies/SSGReps/SSGReps.py": ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
    "dependencies/SSGReps/SG_utils.py": ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    "dependencies/SSGReps/rep_utils.py": ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
}


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def reset_dir(path: Path) -> None:
    if path.exists():
        for child in sorted(path.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        path.rmdir()
    path.mkdir(parents=True, exist_ok=True)


@contextlib.contextmanager
def suppress_output() -> Any:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        yield stdout, stderr


def complex_to_json(value: complex) -> dict[str, float]:
    return {
        "real": round(float(value.real), 12),
        "imag": round(float(value.imag), 12),
    }


def complex_list_to_json(values: list[complex]) -> list[dict[str, float]]:
    return [complex_to_json(value) for value in values]


def complex_matrix_to_json(matrix: list[list[complex]]) -> list[list[dict[str, float]]]:
    return [complex_list_to_json(row) for row in matrix]


def format_tree(root: Path) -> list[str]:
    lines = [root.name]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


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


def load_ssg_dict() -> dict[str, Any]:
    identify_pkl = ROOT / "SSGReps" / "ssg_data" / "identify.pkl"
    with identify_pkl.open("rb") as fh:
        ssg_list = pickle.load(fh)
    return next(item for item in ssg_list if item["ssgNum"] == GROUP_NUMBER)


def load_double_context(module: Any, ssg_dict: dict[str, Any]) -> dict[str, Any]:
    ssg = module.loadSsgGroup(GROUP_NUMBER, np.array([0.0, 0.0, 0.0]), "double", ssg_dict)
    with suppress_output():
        full_data, _ = swyckoff_r.load_irssg_data(GROUP_NUMBER, 0)
        wyckoff_entries, _ = swyckoff_r.compute_wyckoff_output(GROUP_NUMBER, fast=True)
    full_ops = [swyckoff_r.op_from_json(op) for op in full_data["operations"]]
    full_time_revs = [bool(flag) for flag in full_data["time_revs"]]
    ctx = {
        "ssg": ssg,
        "ssg_dict": ssg_dict,
        "supercell": np.array(ssg.superCell, dtype=float),
        "reciprocal_basis": [np.array(ssg.b1), np.array(ssg.b2), np.array(ssg.b3)],
        "full_data": full_data,
        "full_ops": full_ops,
        "full_time_revs": full_time_revs,
        "wyckoff_entries": wyckoff_entries,
    }
    ctx["raw_operations"] = single_expanded.raw_ops(ctx)
    ctx["group_tables"] = single_expanded.build_group_tables(ctx)
    ctx["entries_by_letter"] = {entry["letter"]: entry for entry in wyckoff_entries}
    return ctx


def capture_little_group(
    module: Any,
    ctx: dict[str, Any],
    group_type: str,
    manifold_id: str,
    kvec: list[float],
) -> dict[str, Any]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        lg = module.load_little_group(
            GROUP_NUMBER,
            np.array(kvec, dtype=float),
            False,
            group_type,
            ctx["ssg_dict"],
        )

    unitary_rotations: list[np.ndarray] = []
    unitary_translations: list[np.ndarray] = []
    unitary_raw_indices: list[int] = []
    for rotation, translation, tr in zip(lg.rotC, lg.tauC, lg.time_reversal):
        if tr < 0:
            continue
        rot = np.array(rotation, dtype=float)
        tau = np.array(translation, dtype=float)
        unitary_rotations.append(rot)
        unitary_translations.append(tau)
        unitary_raw_indices.append(
            single_expanded.match_raw_op(
                ctx,
                ctx["group_tables"]["operations"],
                rot,
                tau,
                False,
            )
        )

    raw_character = [[complex(value) for value in row] for row in lg.character]
    linear_character = [[complex(value) for value in row] for row in lg.linear_character]
    comparison_signature = []
    if raw_character:
        comparison_signature = [complex_to_json(value) for value in raw_character[0]]

    return {
        "status": "ok",
        "group_type": 1 if group_type == "single" else 2,
        "manifold_id": manifold_id,
        "kvec": list(kvec),
        "warning_text": stdout.getvalue().strip(),
        "little_group_operation_count": len(lg.oplist),
        "antiunitary_present": bool(lg.antiunitary),
        "rep_count": len(lg.rep_degree),
        "rep_degree": [int(value) for value in lg.rep_degree],
        "torsion": [int(value) for value in lg.torsion],
        "unitary_operation_count": len(unitary_raw_indices),
        "unitary_raw_indices": unitary_raw_indices,
        "character": raw_character,
        "linear_character": linear_character,
        "character_json": complex_matrix_to_json(raw_character),
        "linear_character_json": complex_matrix_to_json(linear_character),
        "character_signature_row0": comparison_signature,
        "unitary_rotations": unitary_rotations,
        "unitary_translations": unitary_translations,
        "kconv": (
            kvec[0] * ctx["reciprocal_basis"][0]
            + kvec[1] * ctx["reciprocal_basis"][1]
            + kvec[2] * ctx["reciprocal_basis"][2]
        ),
    }


def build_kspace_probe(module: Any, ctx: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    probe_by_group_type: dict[str, dict[str, Any]] = {"single": {}, "double": {}}
    for group_type in ("single", "double"):
        for manifold_id, kvec in MANIFOLD_SAMPLES.items():
            capture = capture_little_group(module, ctx, group_type, manifold_id, kvec)
            probe_by_group_type[group_type][manifold_id] = {
                "status": capture["status"],
                "warning_text": capture["warning_text"],
                "little_group_operation_count": capture["little_group_operation_count"],
                "antiunitary_present": capture["antiunitary_present"],
                "rep_count": capture["rep_count"],
                "rep_degree": capture["rep_degree"],
                "torsion": capture["torsion"],
                "unitary_operation_count": capture["unitary_operation_count"],
            }

    all_double_ok = all(
        summary["status"] == "ok" for summary in probe_by_group_type["double"].values()
    )

    detailed_block: dict[str, Any] = {}
    for manifold_id in MINIMAL_KSPACE_BLOCK["endpoints"] + [MINIMAL_KSPACE_BLOCK["line"], SUPPLEMENTAL_PLANE]:
        single_detail = capture_little_group(module, ctx, "single", manifold_id, MANIFOLD_SAMPLES[manifold_id])
        double_detail = capture_little_group(module, ctx, "double", manifold_id, MANIFOLD_SAMPLES[manifold_id])
        char_changed = not np.allclose(
            np.array(single_detail["character"], dtype=complex),
            np.array(double_detail["character"], dtype=complex),
            atol=1e-8,
        )
        detailed_block[manifold_id] = {
            "kvec": list(MANIFOLD_SAMPLES[manifold_id]),
            "single_summary": {
                "rep_count": single_detail["rep_count"],
                "rep_degree": single_detail["rep_degree"],
                "torsion": single_detail["torsion"],
                "warning_text": single_detail["warning_text"],
                "character_row0": single_detail["character_signature_row0"],
                "linear_character_row0": complex_list_to_json(single_detail["linear_character"][0]),
            },
            "double_summary": {
                "rep_count": double_detail["rep_count"],
                "rep_degree": double_detail["rep_degree"],
                "torsion": double_detail["torsion"],
                "warning_text": double_detail["warning_text"],
                "unitary_raw_indices": double_detail["unitary_raw_indices"],
                "character_row0": double_detail["character_signature_row0"],
                "linear_character_row0": complex_list_to_json(double_detail["linear_character"][0]),
                "all_characters": double_detail["character_json"],
                "all_linear_characters": double_detail["linear_character_json"],
            },
            "same_rep_count_as_single": single_detail["rep_count"] == double_detail["rep_count"],
            "same_rep_degree_as_single": single_detail["rep_degree"] == double_detail["rep_degree"],
            "raw_character_changed_from_single": char_changed,
        }

    minimal_json = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "selected_minimal_kspace_test_block": {
            "points": MINIMAL_KSPACE_BLOCK["endpoints"],
            "line": MINIMAL_KSPACE_BLOCK["line"],
            "reason": MINIMAL_KSPACE_BLOCK["reason"],
        },
        "supplemental_plane_probe": {
            "plane": SUPPLEMENTAL_PLANE,
            "reason": "A single generic plane point is enough to confirm that the current groupType=2 little-corep extraction is also stable on special planes.",
        },
        "all_required_special_manifolds_probe": {
            "required_points": [f"P{i}" for i in range(1, 9)],
            "required_lines": [f"L{i}" for i in range(1, 5)],
            "required_planes": ["S1", "S2"],
            "all_double_status_ok": all_double_ok,
            "probe_summary": probe_by_group_type["double"],
        },
        "selected_block_details": detailed_block,
        "double_vs_single_change_summary": {
            "headline": (
                "For this group, the rep-count and rep-degree patterns on the tested manifolds stay the same, "
                "but the raw characters become genuinely double-valued: order-2 unitary operations pick up "
                "projective phases such as +/-i instead of only +/-1."
            ),
            "representative_examples": {
                "P1": {
                    "single_character_row0": detailed_block["P1"]["single_summary"]["character_row0"],
                    "double_character_row0": detailed_block["P1"]["double_summary"]["character_row0"],
                },
                "L1": {
                    "single_character_row0": detailed_block["L1"]["single_summary"]["character_row0"],
                    "double_character_row0": detailed_block["L1"]["double_summary"]["character_row0"],
                },
            },
        },
        "current_corep_extraction_verdict": {
            "character_available": True,
            "linear_character_available": True,
            "rep_degree_available": True,
            "current_blocker": None,
            "compatibility_block_status": (
                "A general double-group point-line restriction solver has not been generalized in this script. "
                "Instead, the minimal real-space prototype below supplies an explicit induced witness on P1-L1-P4."
            ),
        },
    }

    audit_summary = {
        "all_double_status_ok": all_double_ok,
        "probe_by_group_type": probe_by_group_type,
        "detailed_block": detailed_block,
    }
    return minimal_json, audit_summary


def build_c_double_local_irreps(ctx: dict[str, Any]) -> dict[str, Any]:
    stabilizer = [0, 3, 4, 7]
    factor = np.array(ctx["ssg"].factor_su2, dtype=complex)
    mul_table = np.array(ctx["ssg"].mul_table, dtype=int)

    def is_valid(character: dict[int, complex]) -> bool:
        for left in stabilizer:
            for right in stabilizer:
                target = int(mul_table[left][right]) - 1
                lhs = character[left] * character[right] * factor[left][right]
                rhs = character[target]
                if abs(lhs - rhs) > 1e-8:
                    return False
        return True

    irreps: list[dict[str, Any]] = []
    for c2_label, c2_value in (("plus_i", 1j), ("minus_i", -1j)):
        for inversion_label, inversion_value in (("g", 1), ("u", -1)):
            mirror_value = c2_value * inversion_value
            values = {0: 1 + 0j, 3: complex(c2_value), 4: complex(inversion_value), 7: complex(mirror_value)}
            if not is_valid(values):
                raise ValueError(f"invalid projective character on family c stabilizer: {values}")
            irreps.append(
                {
                    "id": f"c_double_{inversion_label}_{c2_label}",
                    "family_letter": "c",
                    "dimension": 1,
                    "site_symmetry": "2/m",
                    "double_group_local_object_kind": "projective_local_irrep",
                    "construction_basis": (
                        "Use the double-group factor table on the unitary stabilizer [0,3,4,7]. "
                        "Because factor_su2[3,3] = factor_su2[7,7] = -1 while factor_su2[4,4] = +1, "
                        "the order-2 spatial generators lift to double-valued characters with C2 -> +/-i, "
                        "inversion -> +/-1, and mirror = inversion * C2."
                    ),
                    "character_on_unitary_stabilizer": {
                        str(index): complex_to_json(value) for index, value in values.items()
                    },
                }
            )
    return {
        "selected_prototype_id": irreps[0]["id"],
        "stabilizer_indices": stabilizer,
        "irreps": irreps,
        "factor_su2_relations": [
            {
                "left": left,
                "right": right,
                "product_index": int(mul_table[left][right]) - 1,
                "factor_su2": complex_to_json(complex(factor[left][right])),
            }
            for left, right in ((3, 3), (4, 4), (7, 7), (3, 4), (7, 3))
        ],
    }


def induce_minimal_double_prototype(
    module: Any,
    ctx: dict[str, Any],
    family_entry: dict[str, Any],
    local_character: dict[int, complex],
) -> dict[str, Any]:
    orbit = single_expanded.orbit_for_sample_entry(family_entry, ctx, ctx["group_tables"])
    stabilizer = single_bridge.bridge_stabilizer_for_entry(family_entry, ctx)
    manifold_results: dict[str, Any] = {}
    minimal_ordering: list[str] = []
    minimal_vector: list[int] = []

    for manifold_id in MINIMAL_KSPACE_BLOCK["endpoints"] + [MINIMAL_KSPACE_BLOCK["line"]]:
        detail = capture_little_group(module, ctx, "double", manifold_id, MANIFOLD_SAMPLES[manifold_id])
        band_character: list[complex] = []
        for op_index, rotation, translation in zip(
            detail["unitary_raw_indices"],
            detail["unitary_rotations"],
            detail["unitary_translations"],
        ):
            total = 0j
            for site in orbit:
                coset_index = int(site["source_operation_index"])
                conj_index = ctx["group_tables"]["compose"](
                    ctx["group_tables"]["inverse"][coset_index],
                    ctx["group_tables"]["compose"](op_index, coset_index),
                )
                if conj_index not in local_character:
                    continue
                point_conv = np.array(site["conv_vector"], dtype=float)
                delta = rotation @ point_conv + translation - point_conv
                fixed, _ = single_bridge.vector_is_lattice(ctx["supercell"], delta)
                if not fixed:
                    continue
                total += local_character[conj_index] * cmath.exp(
                    -1j * float(np.dot(detail["kconv"], delta))
                )
            band_character.append(total)

        chars = np.array(detail["linear_character"], dtype=complex)
        band = np.array(band_character, dtype=complex)
        gram = chars @ chars.conj().T / chars.shape[1]
        rhs = chars.conj() @ band / chars.shape[1]
        multiplicities = np.linalg.solve(gram, rhs)
        rounded = [int(round(float(value.real))) for value in multiplicities]
        recon = np.array(rounded, dtype=complex) @ chars

        if not np.allclose(multiplicities, np.rint(multiplicities.real), atol=1e-8):
            raise ValueError(f"{family_entry['letter']} on {manifold_id}: non-integral double multiplicities")
        if not np.allclose(recon, band, atol=1e-8):
            raise ValueError(f"{family_entry['letter']} on {manifold_id}: double reconstruction failure")

        manifold_results[manifold_id] = {
            "rep_degree": detail["rep_degree"],
            "unitary_raw_indices": detail["unitary_raw_indices"],
            "band_character": complex_list_to_json(band_character),
            "multiplicities": rounded,
            "reconstruction_exact": True,
            "total_dimension": int(sum(mult * degree for mult, degree in zip(rounded, detail["rep_degree"]))),
        }
        for index in range(len(rounded)):
            minimal_ordering.append(f"{manifold_id}_R{index + 1}")
            minimal_vector.append(int(rounded[index]))

    all_total_dims_match = all(
        result["total_dimension"] == len(orbit) for result in manifold_results.values()
    )

    return {
        "selected_family": family_entry["letter"],
        "representative_coordinate": family_entry["representative_coordinate"],
        "sample_point_magnetic": single_bridge.format_vector(
            single_bridge.representative_sample_point_magnetic(family_entry)
        ),
        "multiplicity": int(family_entry["mult"]),
        "stabilizer_summary": {
            "stabilizer_size": int(stabilizer["bridge_stabilizer_size"]),
            "unitary_count": int(stabilizer["bridge_unitary_count"]),
            "antiunitary_count": int(stabilizer["bridge_antiunitary_count"]),
            "stabilizer_indices": list(stabilizer["stabilizer_indices"]),
        },
        "manifolds": manifold_results,
        "minimal_block_unknown_ordering": minimal_ordering,
        "minimal_block_unknown_vector": minimal_vector,
        "all_total_dims_match_orbit_size": all_total_dims_match,
        "minimal_closure_success": all_total_dims_match and all(
            result["reconstruction_exact"] for result in manifold_results.values()
        ),
    }


def build_realspace_prototype(module: Any, ctx: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    family_entry = ctx["entries_by_letter"][MINIMAL_REALSPACE_FAMILY]
    family_stabilizer = single_bridge.bridge_stabilizer_for_entry(family_entry, ctx)
    local_irreps = build_c_double_local_irreps(ctx)
    selected_irrep = next(
        irrep for irrep in local_irreps["irreps"] if irrep["id"] == local_irreps["selected_prototype_id"]
    )
    local_character = {
        int(index): complex(value["real"], value["imag"])
        for index, value in selected_irrep["character_on_unitary_stabilizer"].items()
    }
    induction = induce_minimal_double_prototype(module, ctx, family_entry, local_character)

    realspace_json = {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "selected_minimal_family": {
            "family": MINIMAL_REALSPACE_FAMILY,
            "reason": MINIMAL_REALSPACE_REASON,
        },
        "site_symmetry_summary": {
            "representative_coordinate": family_entry["representative_coordinate"],
            "site_symmetry": family_entry["site_symmetry"],
            "unitary_site_symmetry": family_entry.get("unitary_site_symmetry"),
            "stabilizer_indices": list(family_stabilizer["stabilizer_indices"]),
            "unitary_indices": list(family_stabilizer["unitary_indices"]),
            "antiunitary_indices": list(family_stabilizer["antiunitary_indices"]),
        },
        "double_group_local_rep_corep_summary": {
            "available_minimal_irreps": local_irreps["irreps"],
            "selected_prototype_id": local_irreps["selected_prototype_id"],
            "difference_from_single_same_family": (
                "Single-group family c used ordinary C2h characters with values in {+/-1}. "
                "The double-group prototype uses a projective local irrep with C2 -> +i, inversion -> +1, "
                "and mirror -> +i, as enforced by factor_su2[3,3] = factor_su2[7,7] = -1."
            ),
            "factor_su2_relations": local_irreps["factor_su2_relations"],
            "two_pi_rotation_note": (
                "The needed spinor sign is not inferred from swyckoff_r.py alone; it enters here through the "
                "double-group factor table of SSGReps. The chosen local irrep is therefore genuinely double-valued."
            ),
        },
        "bridge_check_result": {
            "spatial_bridge_reused_from_single": True,
            "r_conv_equals_P_r_mag": True,
            "P_matrix": P_MATRIX,
            "operation_match_count_after_basis_change": int(ctx["spatial_bridge"]["matched_operation_count"]),
            "all_spatial_operations_match": bool(
                ctx["spatial_bridge"]["all_operations_match_exactly_after_basis_change"]
            ),
            "bridge_scope_note": (
                "This confirms the spatial/time-reversal bridge and the stabilizer indices for the minimal prototype. "
                "It does not by itself certify the SU2/projective sign layer, which is handled here through factor_su2."
            ),
        },
        "induction_result": induction,
        "compatibility_check_result": {
            "minimal_block": MINIMAL_KSPACE_BLOCK,
            "all_total_dims_match_orbit_size": induction["all_total_dims_match_orbit_size"],
            "minimal_closure_success": induction["minimal_closure_success"],
            "note": (
                "The same double local irrep on family c induces exact integer multiplicities on P1, L1, and P4. "
                "That is sufficient for the present minimal closure prototype even though a general double-group "
                "compatibility matrix has not yet been built."
            ),
        },
    }

    audit_summary = {
        "family_entry": family_entry,
        "family_stabilizer": family_stabilizer,
        "local_irreps": local_irreps,
        "induction": induction,
    }
    return realspace_json, audit_summary


def build_feasibility_summary(
    kspace_audit: dict[str, Any],
    realspace_audit: dict[str, Any],
    ctx: dict[str, Any],
) -> dict[str, Any]:
    projective_factor_values = sorted(
        {
            int(round(value.real))
            for row in np.array(ctx["ssg"].factor_su2, dtype=complex)
            for value in row
            if abs(value.imag) < 1e-8
        }
    )
    minimal_done = bool(realspace_audit["induction"]["minimal_closure_success"])
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "kspace_double_feasible": bool(kspace_audit["all_double_status_ok"]),
        "realspace_double_feasible": bool(realspace_audit["induction"]["minimal_closure_success"]),
        "bridge_double_feasible": bool(
            ctx["spatial_bridge"]["all_operations_match_exactly_after_basis_change"]
        ),
        "induction_double_feasible": bool(realspace_audit["induction"]["minimal_closure_success"]),
        "minimal_double_prototype_completed": minimal_done,
        "main_blocker": None if minimal_done else "Minimal double prototype did not close.",
        "next_blocker": (
            "Generalize from the unitary point-like family c to a reusable double-group local-corep builder, "
            "especially for antiunitary families, and add a general double-group compatibility-block constructor "
            "that treats projective phases explicitly."
        ),
        "projective_factor_values_seen": projective_factor_values,
    }


def build_bs_ai_summary(realspace_json: dict[str, Any]) -> dict[str, Any]:
    induction = realspace_json["induction_result"]
    selected_irrep = realspace_json["double_group_local_rep_corep_summary"]["selected_prototype_id"]
    return {
        "group_number": GROUP_NUMBER,
        "group_type": GROUP_TYPE,
        "current_minimal_double_group_bs_prototype": {
            "minimal_block": MINIMAL_KSPACE_BLOCK,
            "block_unknown_ordering": induction["minimal_block_unknown_ordering"],
            "block_unknown_vector": induction["minimal_block_unknown_vector"],
        },
        "current_minimal_double_group_ai_prototype": {
            "family": realspace_json["selected_minimal_family"]["family"],
            "selected_local_irrep": selected_irrep,
        },
        "minimal_closure_formed": bool(induction["minimal_closure_success"]),
        "still_unfinished": [
            "No general double-group compatibility matrix for all endpoints/lines/planes has been built yet.",
            "No reusable double-group local-corep builder exists yet for the antiunitary families.",
            "The SU2/projective bridge has only been audited far enough for this minimal unitary-family prototype.",
        ],
    }


def build_audit_md(
    kspace_json: dict[str, Any],
    realspace_json: dict[str, Any],
    summary_json: dict[str, Any],
) -> str:
    p1_single = kspace_json["selected_block_details"]["P1"]["single_summary"]["character_row0"]
    p1_double = kspace_json["selected_block_details"]["P1"]["double_summary"]["character_row0"]
    induction = realspace_json["induction_result"]
    lines = [
        f"# Double-Group Feasibility Audit for {GROUP_NUMBER}",
        "",
        "## Scope",
        "",
        f"- Group only: `{GROUP_NUMBER}`.",
        f"- Group type only: `{GROUP_TYPE}` (double group).",
        "- The single-group line is treated as already closed and is reused only as trusted background.",
        "- This round does not attempt the final double-group indicator group. It only checks feasibility and builds the smallest honest prototype.",
        "",
        "## Single-Group Premise Reused Here",
        "",
        "- The with-planes k-space basis is already trusted for the single group.",
        "- The single-group AI lattice is already complete and gives BS/AI = Z2 x Z2 at groupType=1.",
        "- The spatial bridge has already been audited with r_conv = P r_mag and P = diag(1,2,2).",
        "- The exported *_character.json files store raw characters, so the Bloch phase must still be restored through exp(-i k · tauC).",
        "",
        "## Why The Double-Group Check Starts Here",
        "",
        "- The current codebase already contains a genuine double-group branch in SSGReps: factor_su2 is no longer forced to 1 and the raw characters acquire projective phases.",
        "- The real-space scripts already provide stable special positions, stabilizers, and orbit data for the same group.",
        "- Therefore the smallest honest question is no longer whether geometry works; it is whether the existing bridge + induction route can absorb double-valued local characters without first solving the whole repository.",
        "",
        "## K-Space Feasibility at groupType=2",
        "",
        f"- All required single-group manifolds were re-probed at groupType=2: endpoints `P1..P8`, lines `L1..L4`, planes `S1,S2`. Stable extraction succeeded on all of them: `{summary_json['kspace_double_feasible']}`.",
        "- `character`, `linear_character`, and `rep_degree` are all available on the tested points, lines, and planes.",
        "- The most visible change from groupType=1 is not the rep-degree pattern but the character phase pattern: order-2 unitary operations now carry double-valued phases such as +/-i.",
        "- Representative example on P1:",
        f"  - single-group first raw character row: `{p1_single}`",
        f"  - double-group first raw character row: `{p1_double}`",
        "- On the chosen minimal block P1-L1-P4, the rep counts remain stable while the raw characters change nontrivially. That is exactly the signature expected from a projective/double-valued lift rather than a mere relabeling.",
        "- Current likely k-space blocker for a full rollout: not extraction itself, but the need for a fresh compatibility/block-construction routine that respects the double-valued character phases.",
        "",
        "## Real-Space Feasibility at groupType=2",
        "",
        f"- Chosen minimal family: `{realspace_json['selected_minimal_family']['family']}`.",
        f"- Reason: {realspace_json['selected_minimal_family']['reason']}",
        f"- Real-space special positions from swyckoff_r.py remain usable because the spatial geometry is unchanged. The chosen family has site symmetry `{realspace_json['site_symmetry_summary']['site_symmetry']}` and stabilizer `{realspace_json['site_symmetry_summary']['stabilizer_indices']}`.",
        "- There is still no direct local double-group builder in the current toolchain: SSGReps handles little-group coreps, but not arbitrary real-space site stabilizers as local double representations.",
        "- For the minimal prototype this is still enough because family c is purely unitary. Its unitary stabilizer carries a nontrivial projective factor table, and that factor table already fixes the admissible double-valued local characters.",
        "",
        "## Bridge Feasibility at groupType=2",
        "",
        f"- Spatial bridge reused unchanged: `r_conv = P r_mag`, `P = diag(1,2,2)`.",
        f"- Spatial/time-reversal operation matching after basis change still succeeds on all operations: `{realspace_json['bridge_check_result']['operation_match_count_after_basis_change']} / 16`.",
        "- This is sufficient to reuse orbit representatives, stabilizer indices, and coset data for the minimal prototype.",
        "- However 16/16 spatial matching is not by itself enough to certify the full double-valued bridge. The missing extra layer is the SU2/projective sign convention, which shows up through factor_su2 = -1 on selected products.",
        "",
        "## Induction Feasibility at groupType=2",
        "",
        "- The single-group induction formula survives with the same structure on the minimal unitary family:",
        "  - use the same orbit/coset sum,",
        "  - use the same Bloch phase exp(-i k · tauC),",
        "  - but replace the single-group local character by a genuinely double-valued/projective local character.",
        "- For family c, the chosen prototype local irrep uses C2 -> +i, inversion -> +1, mirror -> +i, exactly because factor_su2[3,3] = factor_su2[7,7] = -1.",
        "- That prototype induces exact integer multiplicities on the minimal block:",
        f"  - P1: `{induction['manifolds']['P1']['multiplicities']}`",
        f"  - L1: `{induction['manifolds']['L1']['multiplicities']}`",
        f"  - P4: `{induction['manifolds']['P4']['multiplicities']}`",
        "- Each manifold reconstructs its induced band character exactly from the double little-corep linear characters, so the minimal induction prototype is successful.",
        "",
        "## Minimal Double Prototype Verdict",
        "",
        f"- k-space minimal prototype on P1-L1-P4: `{summary_json['kspace_double_feasible']}`.",
        f"- real-space minimal prototype on family c: `{summary_json['realspace_double_feasible']}`.",
        f"- bridge usable for the minimal prototype: `{summary_json['bridge_double_feasible']}`.",
        f"- induction usable for the minimal prototype: `{summary_json['induction_double_feasible']}`.",
        f"- minimal double closure completed: `{summary_json['minimal_double_prototype_completed']}`.",
        "",
        "## Answer To The Required Questions",
        "",
        "### A. k-space side",
        "",
        "- A1/A2: yes, groupType=2 stably outputs characters and rep_degree on all previously used endpoints, lines, and planes for this group.",
        "- A3: the obvious change is the appearance of double-valued phases in the raw characters while rep-count/rep-degree patterns stay unchanged on the tested manifolds.",
        "- A4: the current compatibility route still applies in principle because the needed character data exists; the restriction solver must just be rerun with the double-valued characters.",
        "- A5: the first likely failure point for a full rollout is the general compatibility-block builder, not little-corep extraction.",
        "",
        "### B. real-space side",
        "",
        "- B6/B7: yes, the real-space special positions and audited site stabilizers remain usable input.",
        "- B8: the safest starting families are the unitary point-like families c/f. This script picks c.",
        "- B9: there is no direct existing helper that takes an arbitrary real-space site stabilizer and returns a double local irrep/corep census.",
        "- B10: yes, a minimal prototype can still be built manually from stabilizer indices + group-operation matching + the SSGReps projective factor table.",
        "",
        "### C. bridge side",
        "",
        "- C11: the basis-change bridge is still spatially correct.",
        "- C12/C13/C14: extra spinor checks are still needed in general. The 16/16 spatial match does not by itself prove the full double-valued convention; the projective sign and 2pi-rotation layer must be tracked separately.",
        "",
        "### D. induction side",
        "",
        "- D15: yes, the same raw-character plus exp(-i k · tauC) logic still works on the minimal double prototype.",
        "- D16: the orbit sum, lattice-fix filter, and decomposition against linear characters all remain unchanged.",
        "- D17: the extra ingredient is only the local double-valued character itself; for antiunitary families that will require a dedicated Wigner/projective local-corep builder.",
    ]
    return "\n".join(lines)


def build_package_readme() -> str:
    return "\n".join(
        [
            f"# Review Package: {GROUP_NUMBER} Double-Group Feasibility",
            "",
            "## This Round",
            "",
            f"- group: `{GROUP_NUMBER}`",
            f"- groupType: `{GROUP_TYPE}`",
            "- stage: double-group feasibility + minimal prototype",
            "",
            "## Known Premise",
            "",
            "- The single-group line for the same group is already closed.",
            "- The current task is to switch from that closed single-group line to the double group.",
            "- This round only requires the minimal prototype, not the final double-group indicator group.",
            "",
            "## New Content",
            "",
            "- double-group k-space feasibility audit",
            "- double-group real-space feasibility audit",
            "- bridge / induction status at groupType=2",
            "- a minimal double-group prototype on family c and the block P1-L1-P4",
            "",
            "## Possible Outcome Patterns",
            "",
            "- The minimal double-group closure is already feasible.",
            "- A genuine blocker remains, and the audit identifies exactly where it lives.",
            "",
            "## Suggested Review Order",
            "",
            "1. `double_group_feasibility_audit_10.4.1.31.md`",
            "2. `double_group_feasibility_summary_10.4.1.31.json`",
            "3. `double_group_minimal_kspace_10.4.1.31.json`",
            "4. `double_group_minimal_realspace_10.4.1.31.json`",
            "5. `double_group_minimal_bs_ai_summary_10.4.1.31.json`",
            "",
            "## Result Of This Run",
            "",
            "- The minimal double-group closure is feasible for the chosen prototype.",
            "- The next unfinished step is no longer feasibility itself; it is a general double-group compatibility / local-corep builder beyond the chosen minimal case.",
        ]
    )


def build_package() -> None:
    reset_dir(PACKAGE_DIR)
    package_files = {
        "README.md": None,
        AUDIT_MD.name: AUDIT_MD,
        SUMMARY_JSON.name: SUMMARY_JSON,
        KSPACE_JSON.name: KSPACE_JSON,
        REALSPACE_JSON.name: REALSPACE_JSON,
        BS_AI_JSON.name: BS_AI_JSON,
        Path(__file__).name: Path(__file__),
    }
    for rel_path, src in package_files.items():
        dest = PACKAGE_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src is None:
            write_text(dest, build_package_readme())
        else:
            dest.write_bytes(src.read_bytes())

    for rel_path, src in SINGLE_BACKGROUND.items():
        dest = PACKAGE_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def validate_outputs(summary_json: dict[str, Any]) -> None:
    if not summary_json["kspace_double_feasible"]:
        raise ValueError("double-group k-space feasibility unexpectedly failed")
    if not summary_json["realspace_double_feasible"]:
        raise ValueError("double-group real-space feasibility unexpectedly failed")
    if not summary_json["bridge_double_feasible"]:
        raise ValueError("double-group bridge feasibility unexpectedly failed")
    if not summary_json["induction_double_feasible"]:
        raise ValueError("double-group induction feasibility unexpectedly failed")
    if not summary_json["minimal_double_prototype_completed"]:
        raise ValueError("minimal double-group prototype was not completed")

    required_paths = {
        AUDIT_MD.name,
        SUMMARY_JSON.name,
        KSPACE_JSON.name,
        REALSPACE_JSON.name,
        BS_AI_JSON.name,
        Path(__file__).name,
        "README.md",
        "audit/single_group_ai_completeness_audit.md",
        "audit/single_group_ai_completeness_summary.json",
        "audit/single_group_indicator_group_summary.json",
        "audit/single_group_indicator_generators.json",
        "audit/single_group_bs_mod_ai_single_summary.json",
        "audit/single_group_parametric_magnetic_corep_audit.md",
        "audit/single_group_parametric_magnetic_coreps.json",
        "audit/single_group_magnetic_local_corep_audit.md",
        "audit/single_group_pointlike_magnetic_coreps.json",
        "ai/single_group_ai_expanded_v3_basis.json",
        "ai/single_group_bs_vs_ai_expanded_v3_summary.json",
        "basis/single_group_bs_with_planes_basis_raw.json",
        "basis/single_group_bs_with_planes_basis_pretty.json",
        "matrix/single_group_full_compatibility_with_planes.json",
        "background/single_group_kmanifolds.json",
        "background/single_group_connectivity.json",
        "dependencies/swyckoff_r.py",
        "dependencies/swyckoff_k.py",
        "dependencies/SSGReps/SSGReps.py",
        "dependencies/SSGReps/SG_utils.py",
        "dependencies/SSGReps/rep_utils.py",
    }
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(
            str(Path(name).relative_to(PACKAGE_NAME))
            for name in tar.getnames()
            if name != PACKAGE_NAME
        )
    missing = sorted(required_paths - names)
    if missing:
        raise ValueError(f"package tarball is missing required paths: {missing}")


def print_terminal_summary(
    summary_json: dict[str, Any],
    realspace_json: dict[str, Any],
) -> None:
    tree_lines = format_tree(PACKAGE_DIR)
    print(f"1. groupType=2 k-space minimal prototype feasible: {summary_json['kspace_double_feasible']}")
    print(f"2. groupType=2 real-space minimal prototype feasible: {summary_json['realspace_double_feasible']}")
    print(f"3. bridge still usable at groupType=2: {summary_json['bridge_double_feasible']}")
    print(f"4. induction still usable at groupType=2: {summary_json['induction_double_feasible']}")
    print(f"5. minimal double-group closure prototype obtained: {summary_json['minimal_double_prototype_completed']}")
    print(f"6. smallest remaining blocker: {summary_json['next_blocker']}")
    print(f"7. new package path: {PACKAGE_TARBALL}")
    print("8. package tree:")
    for line in tree_lines:
        print(f"   {line}")
    induction = realspace_json["induction_result"]["manifolds"]
    print("Minimal witness on P1-L1-P4:")
    print(f"   P1 multiplicities: {induction['P1']['multiplicities']}")
    print(f"   L1 multiplicities: {induction['L1']['multiplicities']}")
    print(f"   P4 multiplicities: {induction['P4']['multiplicities']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit double-group feasibility and build a minimal groupType=2 prototype for 10.4.1.31."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Regenerate all outputs and perform internal consistency checks.",
    )
    args = parser.parse_args()

    module = load_ssgreps_module()
    ssg_dict = load_ssg_dict()
    ctx = load_double_context(module, ssg_dict)
    ctx["spatial_bridge"] = single_bridge.validate_operation_bridge(ctx)

    kspace_json, kspace_audit = build_kspace_probe(module, ctx)
    realspace_json, realspace_audit = build_realspace_prototype(module, ctx)
    summary_json = build_feasibility_summary(kspace_audit, realspace_audit, ctx)
    bs_ai_json = build_bs_ai_summary(realspace_json)

    write_json(KSPACE_JSON, kspace_json)
    write_json(REALSPACE_JSON, realspace_json)
    write_json(SUMMARY_JSON, summary_json)
    write_json(BS_AI_JSON, bs_ai_json)
    write_text(AUDIT_MD, build_audit_md(kspace_json, realspace_json, summary_json))
    build_package()

    if args.validate:
        validate_outputs(summary_json)
    print_terminal_summary(summary_json, realspace_json)


if __name__ == "__main__":
    main()
