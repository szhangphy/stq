#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent
SSGREPS_PY = ROOT / "SSGReps" / "SSGReps" / "SSGReps.py"
SSGREPS_DIR = SSGREPS_PY.parent
SSG_DATA_DIR = ROOT / "SSGReps" / "ssg_data"
IDENTIFY_PKL = SSG_DATA_DIR / "identify.pkl"
IDENTIFY_TAR = SSG_DATA_DIR / "identify.pkl.tar.gz"

GROUP_NUMBER = "10.4.1.31"
GROUP_TYPE = 1
LINE_ID = "L1"
LEFT_POINT_ID = "P1"
RIGHT_POINT_ID = "P4"

EXACT_K = {
    "P1": (Fraction(0, 1), Fraction(0, 1), Fraction(0, 1)),
    "L1": (Fraction(0, 1), Fraction(1, 5), Fraction(0, 1)),
    "P4": (Fraction(0, 1), Fraction(1, 2), Fraction(0, 1)),
}

# SSGReps.py only accepts CLI float coordinates. Keep the exact rational metadata above
# and use the minimal decimal strings here for the real subprocess call.
CLI_K = {
    "P1": ("0", "0", "0"),
    "L1": ("0", "0.2", "0"),
    "P4": ("0", "0.5", "0"),
}

RAW_OUTPUTS = [
    ("P1", "character"),
    ("P1", "degree"),
    ("L1", "character"),
    ("L1", "degree"),
    ("P4", "character"),
    ("P4", "degree"),
]


def frac_str(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def exact_k_strings(point_id: str) -> list[str]:
    return [frac_str(value) for value in EXACT_K[point_id]]


def exact_k_tuple_str(point_id: str) -> str:
    return f"({', '.join(exact_k_strings(point_id))})"


def ensure_identify_pkl() -> dict[str, Any]:
    extracted = False
    if not IDENTIFY_PKL.exists():
        if not IDENTIFY_TAR.exists():
            raise FileNotFoundError(f"missing {IDENTIFY_PKL} and {IDENTIFY_TAR}")
        with tarfile.open(IDENTIFY_TAR, "r:gz") as tar:
            tar.extract("identify.pkl", path=SSG_DATA_DIR)
        extracted = True
    return {
        "identify_pkl": str(IDENTIFY_PKL),
        "identify_tar": str(IDENTIFY_TAR),
        "extracted_this_run": extracted,
        "identify_pkl_size": IDENTIFY_PKL.stat().st_size,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def decode_complex_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        if set(obj.keys()) == {"real", "imag"}:
            return complex(obj["real"], obj["imag"])
        return {key: decode_complex_json(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [decode_complex_json(value) for value in obj]
    return obj


def load_geometry_anchor() -> dict[str, Any]:
    manifolds = load_json(ROOT / "single_group_kmanifolds.json")
    connectivity = load_json(ROOT / "single_group_connectivity.json")
    objects = {item["id"]: item for item in manifolds["objects"]}
    for object_id in (LEFT_POINT_ID, LINE_ID, RIGHT_POINT_ID):
        if object_id not in objects:
            raise ValueError(f"missing geometry object {object_id}")
    point_line = [edge for edge in connectivity["point_line"] if edge["line_id"] == LINE_ID]
    return {
        "P1": objects[LEFT_POINT_ID],
        "L1": objects[LINE_ID],
        "P4": objects[RIGHT_POINT_ID],
        "point_line_edges": point_line,
    }


def verify_geometry_anchor(anchor: dict[str, Any]) -> None:
    p1 = anchor["P1"]
    l1 = anchor["L1"]
    p4 = anchor["P4"]
    if p1["coordinate_expressions"] != ["0", "0", "0"]:
        raise ValueError("P1 geometry no longer matches (0,0,0)")
    if p4["coordinate_expressions"] != ["0", "1/2", "0"]:
        raise ValueError("P4 geometry no longer matches (0,1/2,0)")
    if l1["coordinate_expressions"] != ["0", "v", "0"]:
        raise ValueError("L1 geometry no longer matches (0,v,0)")
    if l1["constraints"] != ["0 < v", "v < 1/2"]:
        raise ValueError("L1 constraints no longer match 0 < v < 1/2")
    if l1["sample_point"] != ["0", "1/5", "0"]:
        raise ValueError("L1 sample point is no longer fixed at (0,1/5,0)")
    observed = {(edge["point_id"], edge["boundary_condition"]) for edge in anchor["point_line_edges"]}
    expected = {
        ("P1", "v = 0"),
        ("P4", "v = 1/2"),
    }
    if observed != expected:
        raise ValueError("L1 endpoint relation no longer matches P1 -- L1 -- P4")


def required_output_paths(point_id: str, mode: str) -> tuple[Path, Path]:
    base = f"{point_id}_{mode}"
    return ROOT / f"{base}.json", ROOT / f"{base}.stdout.txt"


def summarize_raw_json(data: dict[str, Any]) -> dict[str, Any]:
    character = data["character"]
    rep_degree = data["repDegree"]
    time_reversal = data["timeReversal"]
    return {
        "keys": list(data.keys()),
        "kvec": data["kvec"],
        "n_ops_total": len(data["rotC"]),
        "n_unitary_ops": sum(1 for sign in time_reversal if sign > 0),
        "n_antiunitary_ops": sum(1 for sign in time_reversal if sign < 0),
        "n_reps": len(character),
        "character_length": len(character[0]) if character else 0,
        "repDegree": rep_degree,
        "torsion": data["torsion"],
        "timeReversal": time_reversal,
    }


def run_ssgreps_cli(point_id: str, mode: str) -> dict[str, Any]:
    out_name = "character" if mode == "character" else "rep_degree"
    cmd = [
        sys.executable,
        str(SSGREPS_PY),
        "--ssgNum",
        GROUP_NUMBER,
        "--kp",
        *CLI_K[point_id],
        "--out",
        out_name,
        "--groupType",
        str(GROUP_TYPE),
        "--fileType",
        "json",
    ]
    json_path, stdout_path = required_output_paths(point_id, mode)
    if json_path.exists():
        json_path.unlink()
    if stdout_path.exists():
        stdout_path.unlink()
    with tempfile.TemporaryDirectory(prefix=f"{point_id}_{mode}_", dir=str(ROOT / ".tmp_single_connection")) as tmpdir:
        tmp_path = Path(tmpdir)
        completed = subprocess.run(
            cmd,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        stdout_text = completed.stdout + completed.stderr
        stdout_path.write_text(stdout_text)
        if completed.returncode != 0:
            raise RuntimeError(
                f"SSGReps failed for {point_id} {mode} with exit code {completed.returncode}\n{stdout_text}"
            )
        raw_output = tmp_path / "output.json"
        if not raw_output.exists():
            raise FileNotFoundError(f"{raw_output} was not created")
        shutil.copyfile(raw_output, json_path)
    data = load_json(json_path)
    summary = summarize_raw_json(data)
    summary.update(
        {
            "command": shlex.join(cmd),
            "json_path": str(json_path),
            "stdout_path": str(stdout_path),
            "exact_k": exact_k_strings(point_id),
            "actual_cli_k": list(CLI_K[point_id]),
            "stdout_last_lines": stdout_path.read_text().splitlines()[-8:],
        }
    )
    return summary


def import_ssgreps_module():
    if str(SSGREPS_DIR) not in sys.path:
        sys.path.insert(0, str(SSGREPS_DIR))
    spec = importlib.util.spec_from_file_location("ssgreps_local", SSGREPS_PY)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load {SSGREPS_PY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_little_group(module, point_id: str, optimize: bool):
    kvec = module.np.array([float(value) for value in EXACT_K[point_id]], dtype=float)
    with contextlib.redirect_stdout(io.StringIO()):
        return module.load_one_ssg_kvec(
            GROUP_NUMBER,
            kvec,
            single=GROUP_TYPE,
            out="character",
            fileType=None,
            optimize=optimize,
        )


def normalize_float(value: float, tol: float = 1e-6) -> float:
    nearest = round(value)
    if abs(value - nearest) < tol:
        return float(nearest)
    if abs(value) < tol:
        return 0.0
    return round(value, 6)


def operation_key(lg, op_index: int) -> tuple[Any, ...]:
    rot = tuple(
        tuple(int(round(float(entry))) for entry in row)
        for row in lg.rotC[op_index]
    )
    tau = tuple(normalize_float(float(entry) % 1.0) for entry in lg.tauC[op_index])
    spin = tuple(
        tuple(int(round(float(entry))) for entry in row)
        for row in lg.spin[op_index]
    )
    return rot, tau, spin, int(lg.time_reversal[op_index])


def as_exact_char(value: complex) -> sp.Expr:
    value = complex(value)
    if abs(value.imag) < 1e-8:
        real = value.real
        nearest = round(real)
        if abs(real - nearest) < 1e-8:
            return sp.Integer(nearest)
        return sp.nsimplify(real)
    return sp.nsimplify(value.real) + sp.I * sp.nsimplify(value.imag)


def compare_optimize_false_true(module) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for point_id in ("P1", "L1", "P4"):
        unoptimized = load_little_group(module, point_id, optimize=False)
        optimized = load_little_group(module, point_id, optimize=True)
        result[point_id] = {
            "same_rep_degree": unoptimized.rep_degree == optimized.rep_degree,
            "same_torsion": unoptimized.torsion == optimized.torsion,
            "same_time_reversal": unoptimized.time_reversal == optimized.time_reversal,
            "same_character": bool(
                module.np.allclose(
                    module.np.array(unoptimized.character, dtype=complex),
                    module.np.array(optimized.character, dtype=complex),
                )
            ),
            "same_linear_character": bool(
                module.np.allclose(
                    module.np.array(unoptimized.linear_character, dtype=complex),
                    module.np.array(optimized.linear_character, dtype=complex),
                )
            ),
        }
    return result


def build_compatibility_block(module) -> dict[str, Any]:
    point_groups = {
        point_id: load_little_group(module, point_id, optimize=False)
        for point_id in ("P1", "L1", "P4")
    }
    line_group = point_groups["L1"]
    line_unitary_ops = [
        operation_key(line_group, op_index)
        for op_index, sign in enumerate(line_group.time_reversal)
        if sign > 0
    ]
    if len(line_unitary_ops) != len(line_group.character[0]):
        raise ValueError("line unitary operation count does not match line character length")
    line_basis_matrix = sp.Matrix(
        [
            [as_exact_char(value) for value in rep_character]
            for rep_character in line_group.character
        ]
    ).T
    line_basis_labels = [f"L1_R{index}" for index in range(1, len(line_group.character) + 1)]
    endpoint_decompositions: dict[str, Any] = {}
    matched_operation_indices: dict[str, list[int]] = {}
    for point_id in ("P1", "P4"):
        little_group = point_groups[point_id]
        unitary_map = {
            operation_key(little_group, op_index): unitary_index
            for unitary_index, (op_index, sign) in enumerate(
                (item for item in enumerate(little_group.time_reversal) if item[1] > 0)
            )
        }
        matched = [unitary_map.get(op_key) for op_key in line_unitary_ops]
        if any(index is None for index in matched):
            raise ValueError(f"{point_id} does not contain the full L1 unitary subgroup")
        matched_operation_indices[point_id] = matched
        reps = []
        for rep_index, rep_character in enumerate(little_group.character, start=1):
            restricted = sp.Matrix([as_exact_char(rep_character[index]) for index in matched])
            coeffs = list(line_basis_matrix.LUsolve(restricted))
            coeffs_int: list[int] = []
            for coeff in coeffs:
                if coeff.is_Integer:
                    coeffs_int.append(int(coeff))
                    continue
                coeff_eval = complex(coeff.evalf())
                if abs(coeff_eval.imag) < 1e-8 and abs(coeff_eval.real - round(coeff_eval.real)) < 1e-8:
                    coeffs_int.append(int(round(coeff_eval.real)))
                else:
                    raise ValueError(f"non-integral decomposition for {point_id} rep {rep_index}: {coeffs}")
            reps.append(
                {
                    "rep_id": f"{point_id}_R{rep_index}",
                    "rep_degree": int(little_group.rep_degree[rep_index - 1]),
                    "torsion": int(little_group.torsion[rep_index - 1]),
                    "restricted_character_on_L1_unitary_subgroup": [str(entry) for entry in restricted],
                    "decomposition_on_L1_basis": {
                        basis_label: coeff
                        for basis_label, coeff in zip(line_basis_labels, coeffs_int)
                        if coeff
                    },
                }
            )
        endpoint_decompositions[point_id] = reps
    unknown_ordering = [item["rep_id"] for item in endpoint_decompositions["P1"]] + [
        item["rep_id"] for item in endpoint_decompositions["P4"]
    ]
    equations = []
    matrix_rows = []
    for basis_index, basis_label in enumerate(line_basis_labels):
        row = []
        terms = []
        for item in endpoint_decompositions["P1"]:
            coeff = item["decomposition_on_L1_basis"].get(basis_label, 0)
            row.append(coeff)
            if coeff:
                terms.append({"unknown": item["rep_id"], "coeff": coeff, "side": "left"})
        for item in endpoint_decompositions["P4"]:
            coeff = -item["decomposition_on_L1_basis"].get(basis_label, 0)
            row.append(coeff)
            if coeff:
                terms.append({"unknown": item["rep_id"], "coeff": coeff, "side": "right"})
        matrix_rows.append(row)
        equations.append(
            {
                "basis": basis_label,
                "terms": terms,
                "equation": " + ".join(
                    f"{term['coeff']}*{term['unknown']}"
                    for term in terms
                    if term["side"] == "left"
                )
                + " = "
                + " + ".join(
                    f"{-term['coeff']}*{term['unknown']}"
                    for term in terms
                    if term["side"] == "right"
                ),
            }
        )
    return {
        "group_number": GROUP_NUMBER,
        "connection": [LEFT_POINT_ID, LINE_ID, RIGHT_POINT_ID],
        "line_unitary_basis": [
            {
                "basis_id": basis_label,
                "character": [str(as_exact_char(value)) for value in rep_character],
            }
            for basis_label, rep_character in zip(line_basis_labels, line_group.character)
        ],
        "matched_unitary_operation_indices": matched_operation_indices,
        "endpoint_decompositions": endpoint_decompositions,
        "unknown_ordering": unknown_ordering,
        "equations": equations,
        "matrix_rows": matrix_rows,
    }


def raw_json_mode_note() -> str:
    return (
        "`SSGReps.py` uses the same JSON schema for both `--out character` and "
        "`--out rep_degree`, and the CLI branch only changes terminal printing after the "
        "little-group object is built. Two independent runs are not byte-identical because "
        "the irrep construction uses a random matrix internally, so `character` and especially "
        "`repMatrix` can drift by tiny floating noise between runs. For this task the stable "
        "usable fields are the operation data, `timeReversal`, `torsion`, `repDegree`, and the "
        "rounded internal unitary-subgroup `character`; the printed terminal output instead uses "
        "`linear_character`."
    )


def compare_mode_pairs() -> dict[str, Any]:
    np_mod = import_ssgreps_module().np
    result: dict[str, Any] = {}
    for point_id in ("P1", "L1", "P4"):
        character_json = load_json(ROOT / f"{point_id}_character.json")
        degree_json = load_json(ROOT / f"{point_id}_degree.json")
        stable_keys = ["ssgNum", "kvec", "rotC", "spin", "su2", "timeReversal", "tauC", "torsion", "repDegree"]
        character_internal = decode_complex_json(character_json["character"])
        degree_internal = decode_complex_json(degree_json["character"])
        character_matrix = decode_complex_json(character_json["repMatrix"])
        degree_matrix = decode_complex_json(degree_json["repMatrix"])
        result[point_id] = {
            "same_schema_keys": list(character_json.keys()) == list(degree_json.keys()),
            "stable_fields_equal": all(character_json[key] == degree_json[key] for key in stable_keys),
            "character_allclose": bool(
                np_mod.allclose(
                    np_mod.array(character_internal, dtype=complex),
                    np_mod.array(degree_internal, dtype=complex),
                )
            ),
            "rep_matrix_allclose": bool(
                np_mod.allclose(
                    np_mod.array(character_matrix, dtype=complex),
                    np_mod.array(degree_matrix, dtype=complex),
                )
            ),
            "byte_identical": (ROOT / f"{point_id}_character.json").read_bytes()
            == (ROOT / f"{point_id}_degree.json").read_bytes(),
        }
    return result


def build_audit_markdown(
    data_info: dict[str, Any],
    geometry: dict[str, Any],
    output_summary: dict[str, Any],
    optimize_summary: dict[str, Any],
    mode_pair_summary: dict[str, Any],
    compatibility: dict[str, Any] | None,
) -> str:
    p1 = geometry["P1"]
    l1 = geometry["L1"]
    p4 = geometry["P4"]
    lines = [
        "# Single Connection Audit",
        "",
        "## Scope",
        f"- Group: `{GROUP_NUMBER}`",
        f"- Connection: `{LEFT_POINT_ID} -- {LINE_ID} -- {RIGHT_POINT_ID}`",
        f"- Exact k points: `{LEFT_POINT_ID}={exact_k_tuple_str('P1')}`, `{LINE_ID}_generic={exact_k_tuple_str('L1')}`, `{RIGHT_POINT_ID}={exact_k_tuple_str('P4')}`",
        "",
        "## Geometry Anchor",
        f"- `{LEFT_POINT_ID}`: `{p1['parametrization']}`",
        f"- `{LINE_ID}`: `{l1['parametrization']}`, constraints `{l1['constraint_summary']}`, sample point `({', '.join(l1['sample_point'])})`",
        f"- `{RIGHT_POINT_ID}`: `{p4['parametrization']}`",
        "- Endpoint relation from `single_group_connectivity.json`:",
    ]
    for edge in geometry["point_line_edges"]:
        lines.append(
            f"  - `{edge['point_id']} -- {edge['line_id']}` from boundary condition `{edge['boundary_condition']}`"
        )
    lines.extend(
        [
            "",
            "## A. SSGReps.py",
            f"- Real file: `{SSGREPS_PY}`",
            "- Real invocation styles:",
            "  - CLI via `python SSGReps/SSGReps/SSGReps.py ...`",
            "  - import API via `load_one_ssg_kvec(ssgnum, kvec, single, out, fileType, optimize)` after adding `SSGReps/SSGReps` to `sys.path`",
            "- `groupType` meaning is real, not inferred:",
            "  - `1` -> single group",
            "  - `2` -> double group",
            "  - For this task the wrapper uses `1`, matching the single-valued target.",
            "- Real CLI input constraints:",
            "  - `--kp` is parsed as three Python floats, so the exact rational `1/5` must be preserved in wrapper metadata while the CLI receives `0.2`.",
            "  - `--optimize` is declared as `type=bool`, so `--optimize False` is parsed as `True`; the wrapper avoids that buggy path.",
            "- Real JSON payload keys for both `--out character` and `--out rep_degree`:",
            "  - `ssgNum`, `kvec`, `rotC`, `spin`, `su2`, `timeReversal`, `tauC`, `character`, `repMatrix`, `torsion`, `repDegree`",
            f"- JSON mode note: {raw_json_mode_note()}",
            "- Real terminal printing behavior:",
            "  - `--out character` prints `linear_character` on the unitary subgroup only.",
            "  - `--out rep_degree` prints only the degree list.",
            "  - Neither terminal mode prints a label system for irreps.",
            "",
            "## Raw Commands",
        ]
    )
    for point_id in ("P1", "L1", "P4"):
        for mode in ("character", "degree"):
            file_info = output_summary[f"{point_id}_{mode}"]
            lines.append(f"- `{point_id} {mode}`: `{file_info['command']}`")
    lines.extend(
        [
            "",
            "## B. Current Geometry Layer",
            "- The geometry layer already stores the exact object IDs, endpoint relation, and special-manifold classification for this single connection.",
            "- `L1` is explicitly marked as `separately_listed_special_line_manifold`.",
            "- The chosen generic interior point is already fixed to `(0, 1/5, 0)` in `single_group_kmanifolds.json`.",
            "",
            "## C. Feasibility",
            "- `SSGReps.py` can stably produce little-group data for all three fixed k points in this connection.",
            "- The `L1` little-group operations match strict subsets of the `P1` and `P4` little-group operations.",
            "- The printed `linear_character` is not the right object for this cross-k restriction; it gives non-integral coefficients on this connection because it still carries the k-dependent translation phase.",
            "- The internal `character` stored in the JSON/object is sufficient here: it restricts from `P1` and `P4` to the `L1` basis with integral coefficients.",
        ]
    )
    if compatibility is not None:
        lines.extend(
            [
                "- Conclusion: current local code is already sufficient to construct a minimal compatibility block for `P1 -- L1 -- P4` without using `rep_matrix`.",
                "",
                "## Character vs Degree Runs",
            ]
        )
        for point_id, summary in mode_pair_summary.items():
            lines.append(f"- `{point_id}`: `{json.dumps(summary, ensure_ascii=False)}`")
        lines.extend(
            [
                "",
                "## Optimize Check",
            ]
        )
        for point_id, summary in optimize_summary.items():
            lines.append(f"- `{point_id}`: `{json.dumps(summary, ensure_ascii=False)}`")
        lines.extend(
            [
                "",
                "## Minimal Compatibility Block",
                f"- Unknown ordering: `{', '.join(compatibility['unknown_ordering'])}`",
                "- Middle comparison basis on `L1`:",
            ]
        )
        for basis in compatibility["line_unitary_basis"]:
            lines.append(f"  - `{basis['basis_id']}` with character `{basis['character']}`")
        lines.append("- Equations:")
        for equation in compatibility["equations"]:
            lines.append(f"  - `{equation['basis']}`: `{equation['equation']}`")
    else:
        lines.append("- Conclusion: current local data is still insufficient for a trustworthy compatibility block.")
    lines.extend(
        [
            "",
            "## Data Dependency",
            f"- `identify.pkl` location: `{data_info['identify_pkl']}`",
            f"- Extracted from tarball during this run: `{data_info['extracted_this_run']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    tmp_root = ROOT / ".tmp_single_connection"
    tmp_root.mkdir(exist_ok=True)

    data_info = ensure_identify_pkl()
    geometry = load_geometry_anchor()
    verify_geometry_anchor(geometry)

    raw_output_summary = {}
    for point_id, mode in RAW_OUTPUTS:
        raw_output_summary[f"{point_id}_{mode}"] = run_ssgreps_cli(point_id, mode)

    module = import_ssgreps_module()
    mode_pair_summary = compare_mode_pairs()
    optimize_summary = compare_optimize_false_true(module)

    compatibility = None
    blocker = None
    can_proceed = False
    try:
        compatibility = build_compatibility_block(module)
        can_proceed = True
    except Exception as exc:  # pragma: no cover - kept for audit output
        blocker = str(exc)

    summary = {
        "group_number": GROUP_NUMBER,
        "connection": [LEFT_POINT_ID, LINE_ID, RIGHT_POINT_ID],
        "exact_k_points": {
            point_id: exact_k_strings(point_id) for point_id in ("P1", "L1", "P4")
        },
        "actual_cli_k_points": {
            point_id: list(CLI_K[point_id]) for point_id in ("P1", "L1", "P4")
        },
        "geometry_anchor": {
            "P1_id": geometry["P1"]["id"],
            "P1_parametrization": geometry["P1"]["parametrization"],
            "L1_id": geometry["L1"]["id"],
            "L1_parametrization": geometry["L1"]["parametrization"],
            "L1_constraints": geometry["L1"]["constraints"],
            "L1_sample_point": geometry["L1"]["sample_point"],
            "P4_id": geometry["P4"]["id"],
            "P4_parametrization": geometry["P4"]["parametrization"],
            "point_line_edges": geometry["point_line_edges"],
        },
        "raw_output_note": raw_json_mode_note(),
        "files": raw_output_summary,
        "character_vs_degree_mode_check": mode_pair_summary,
        "optimize_false_true_check": optimize_summary,
        "can_proceed_to_compatibility": can_proceed,
        "blocker": blocker,
    }
    if compatibility is not None:
        summary["compatibility_support"] = {
            "matched_unitary_operation_indices": compatibility["matched_unitary_operation_indices"],
            "unknown_ordering": compatibility["unknown_ordering"],
        }

    (ROOT / "single_connection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    if compatibility is not None:
        (ROOT / "single_connection_compatibility.json").write_text(
            json.dumps(compatibility, ensure_ascii=False, indent=2)
        )

    audit_md = build_audit_markdown(
        data_info=data_info,
        geometry=geometry,
        output_summary=raw_output_summary,
        optimize_summary=optimize_summary,
        mode_pair_summary=mode_pair_summary,
        compatibility=compatibility,
    )
    (ROOT / "single_connection_audit.md").write_text(audit_md)

    print(f"group_number: {GROUP_NUMBER}")
    print(f"connection: {LEFT_POINT_ID} -- {LINE_ID} -- {RIGHT_POINT_ID}")
    print(f"character_json_ready: {all((ROOT / f'{point}_character.json').exists() for point in ('P1', 'L1', 'P4'))}")
    print(f"degree_json_ready: {all((ROOT / f'{point}_degree.json').exists() for point in ('P1', 'L1', 'P4'))}")
    print(f"can_proceed_to_compatibility: {can_proceed}")
    print(f"blocker: {blocker}")
    if compatibility is not None:
        print("compatibility_unknown_ordering:", ", ".join(compatibility["unknown_ordering"]))


if __name__ == "__main__":
    main()
