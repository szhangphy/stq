#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tarfile
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = REPO_ROOT / "sg194" / "bs_fix_reaudit_v1"
PACKAGE_ROOT = ROOT / "external_review_package_ssg194_bs_fix_v1"
ARCHIVE_PATH = ROOT / "external_review_package_ssg194_bs_fix_v1.tar.gz"

SOURCE_FILES = [
    "sg194/debug_workflow_portability_194.1.1.1.py",
    "sg194/pipeline_v2/runtime_backend_free.py",
    "sg194/pipeline_v2/generic_builders.py",
    "sg194/pipeline_v2/bs_ai.py",
    "sg194/bs_fix_reaudit_v1/experiment/debug_sg194_bs_fix_experiment_v1.py",
    "sg194/bs_fix_reaudit_v1/build_external_review_package_v1.py",
]

OUTPUT_FILES = [
    "sg194/group_194_1_1_1_single_ai_trivial_generators.json",
    "sg194/group_194_1_1_1_single_bs_analysis.json",
    "sg194/group_194_1_1_1_single_full_compatibility_with_planes.json",
    "sg194/group_194_1_1_1_single_line_compatibility.json",
    "sg194/group_194_1_1_1_single_little_groups.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def run_command(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=check)


def git_show(repo_relative_path: str) -> str:
    return run_command(["git", "show", f"HEAD:{repo_relative_path}"], cwd=REPO_ROOT).stdout


def load_current_debug_module():
    path = REPO_ROOT / "sg194" / "debug_workflow_portability_194.1.1.1.py"
    spec = importlib.util.spec_from_file_location("sg194_stage1_debug_current", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_original_debug_module():
    source = git_show("sg194/debug_workflow_portability_194.1.1.1.py")
    module = types.ModuleType("sg194_stage1_debug_original")
    module.__file__ = str(REPO_ROOT / "sg194" / "debug_workflow_portability_194.1.1.1.py")
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module


def load_current_generic_builders():
    sys.path.insert(0, str(REPO_ROOT))
    from sg194.pipeline_v2 import generic_builders as module

    return module


def complex_json(values: list[complex]) -> list[dict[str, float]]:
    out = []
    for value in values:
        out.append({"real": float(value.real), "imag": float(value.imag)})
    return out


def decode_complex_tree(payload: Any) -> Any:
    if isinstance(payload, dict):
        if set(payload.keys()) == {"real", "imag"} and all(isinstance(payload[key], (int, float)) for key in ("real", "imag")):
            return complex(payload["real"], payload["imag"])
        return {key: decode_complex_tree(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [decode_complex_tree(value) for value in payload]
    return payload


def load_json_with_complex_numbers(path: Path) -> Any:
    return decode_complex_tree(json.loads(path.read_text()))


def line_numbered_snippet(text: str, line_number: int, *, radius: int = 2) -> str:
    lines = text.splitlines()
    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)
    return "\n".join(f"{index}: {lines[index - 1]}" for index in range(start, end + 1))


def capture_stdout(fn, *args, **kwargs):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = fn(*args, **kwargs)
    return result, stream.getvalue()


def write_file_snapshots(file_list: list[str], *, category: str) -> dict[str, Any]:
    manifest = []
    original_root = PACKAGE_ROOT / category / "original"
    final_root = PACKAGE_ROOT / category / "final"
    for repo_relative_path in file_list:
        final_path = REPO_ROOT / repo_relative_path
        target_final = final_root / repo_relative_path
        target_final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final_path, target_final)
        original_target = original_root / repo_relative_path
        original_target.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            try:
                original_target.write_text(git_show(repo_relative_path))
                original_status = "from_git_head"
            except subprocess.CalledProcessError:
                write_text(original_target.with_suffix(original_target.suffix + ".missing_from_head.txt"), "File not present in HEAD.")
                original_status = "missing_from_head"
        else:
            original_status = "missing_from_worktree"
        manifest.append(
            {
                "path": repo_relative_path,
                "final_snapshot": str(target_final.relative_to(PACKAGE_ROOT)),
                "original_snapshot_status": original_status,
            }
        )
    return {"generated_at": now_iso(), "files": manifest}


def build_patch_artifacts() -> dict[str, Any]:
    patch_root = PACKAGE_ROOT / "patches"
    patch_root.mkdir(parents=True, exist_ok=True)
    tracked = [path for path in run_command(["git", "diff", "--name-only"], cwd=REPO_ROOT).stdout.splitlines() if path]
    untracked = [path for path in SOURCE_FILES if run_command(["git", "ls-files", "--error-unmatch", path], cwd=REPO_ROOT, check=False).returncode != 0]
    overall_parts = []
    if tracked:
        tracked_diff = run_command(["git", "diff", "--"] + tracked, cwd=REPO_ROOT, check=False).stdout
        overall_parts.append(tracked_diff)
        write_text(patch_root / "tracked_modified_files.patch", tracked_diff)
        for repo_relative_path in tracked:
            diff = run_command(["git", "diff", "--", repo_relative_path], cwd=REPO_ROOT, check=False).stdout
            write_text(patch_root / "per_file" / f"{repo_relative_path.replace('/', '__')}.patch", diff)
    for repo_relative_path in untracked:
        file_path = REPO_ROOT / repo_relative_path
        diff = run_command(["git", "diff", "--no-index", "--", "/dev/null", str(file_path)], cwd=REPO_ROOT, check=False).stdout
        overall_parts.append(diff)
        write_text(patch_root / "per_file" / f"{repo_relative_path.replace('/', '__')}.patch", diff)
    overall_patch = "\n".join(part for part in overall_parts if part.strip())
    write_text(patch_root / "overall.patch", overall_patch)
    return {
        "generated_at": now_iso(),
        "tracked_files": tracked,
        "untracked_files": untracked,
        "overall_patch": str((patch_root / "overall.patch").relative_to(PACKAGE_ROOT)),
    }


def write_repro_scripts() -> dict[str, str]:
    repro_root = PACKAGE_ROOT / "repro"
    repro_root.mkdir(parents=True, exist_ok=True)
    first_failure_py = repro_root / "reproduce_original_first_failure.py"
    experiment_sh = repro_root / "run_current_diagnostic_experiment.sh"
    write_text(
        first_failure_py,
        f"""#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path


def decode_complex(payload):
    if isinstance(payload, dict):
        if set(payload.keys()) == {{"real", "imag"}} and all(isinstance(payload[key], (int, float)) for key in ("real", "imag")):
            return complex(payload["real"], payload["imag"])
        return {{key: decode_complex(value) for key, value in payload.items()}}
    if isinstance(payload, list):
        return [decode_complex(value) for value in payload]
    return payload


REPO_ROOT = Path(__file__).resolve().parents[4]
source = subprocess.run(
    ["git", "show", "HEAD:sg194/debug_workflow_portability_194.1.1.1.py"],
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
    check=True,
).stdout
module = types.ModuleType("sg194_stage1_debug_original")
module.__file__ = str(REPO_ROOT / "sg194" / "debug_workflow_portability_194.1.1.1.py")
exec(compile(source, module.__file__, "exec"), module.__dict__)
connectivity = json.loads((REPO_ROOT / "sg194/group_194_1_1_1_single_connectivity.json").read_text())
l1 = next(item for item in connectivity["objects"] if item.get("id") == "L1")
captures = decode_complex(json.loads((REPO_ROOT / "sg194/group_194_1_1_1_single_little_groups.json").read_text()))
module.build_line_block(l1, captures, phase_aware_profile=module.AUTHORITATIVE_PHASE_AWARE_PROFILE)
""",
    )
    write_text(
        experiment_sh,
        """#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
python3 "$REPO_ROOT/sg194/bs_fix_reaudit_v1/experiment/debug_sg194_bs_fix_experiment_v1.py"
""",
    )
    first_failure_py.chmod(0o755)
    experiment_sh.chmod(0o755)
    return {
        "first_failure_command": f"python3 {first_failure_py}",
        "diagnostic_experiment_command": f"bash {experiment_sh}",
    }


def build_first_failure_evidence(original_debug) -> dict[str, Any]:
    evidence_root = PACKAGE_ROOT / "evidence" / "first_failure"
    evidence_root.mkdir(parents=True, exist_ok=True)
    repro_script = PACKAGE_ROOT / "repro" / "reproduce_original_first_failure.py"
    command = f"python3 {repro_script}"
    proc = subprocess.run([sys.executable, str(repro_script)], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    write_text(evidence_root / "command.txt", command)
    write_text(evidence_root / "stdout.txt", proc.stdout)
    write_text(evidence_root / "stderr.txt", proc.stderr)
    write_text(evidence_root / "exit_code.txt", str(proc.returncode))

    connectivity = json.loads((REPO_ROOT / "sg194/group_194_1_1_1_single_connectivity.json").read_text())
    captures = load_json_with_complex_numbers(REPO_ROOT / "sg194/group_194_1_1_1_single_little_groups.json")
    line = next(item for item in connectivity["objects"] if item.get("id") == "L1")
    endpoint = next(item for item in line["endpoints"] if item["point_id"] == "P1")
    line_raw = captures["L1"]
    point_raw = captures[endpoint.get("capture_id", endpoint["point_id"])]
    matched = original_debug.matched_unitary_indices(line_raw, point_raw)
    restricted_exact = original_debug._exact_restriction_vector(
        line_raw,
        point_raw,
        matched,
        field="linear_character",
        parent_manifold_id="L1",
        child_manifold_id="P1",
        rep_id="P1_R1",
    )
    basis_matrix = original_debug._exact_basis_matrix_from_capture(line_raw, "linear_character", manifold_id="L1")
    basis = np.array([[complex(value.evalf()) for value in row] for row in basis_matrix.tolist()], dtype=complex)
    restricted = np.array([complex(value.evalf()) for value in restricted_exact], dtype=complex)
    coeffs, _residuals, _rank, _singular_values = np.linalg.lstsq(basis, restricted, rcond=None)
    nearest = [int(round(value.real)) if abs(value.imag) < 1e-8 and abs(value.real - round(value.real)) < 1e-8 else None for value in coeffs]
    nearest_vector = np.array([value if value is not None else 0 for value in nearest], dtype=complex)
    input_object = {
        "line_object": {
            "id": line["id"],
            "sample_point": list(line["sample_point"]),
            "parametrization": line["parametrization"],
            "symmetry_summary": line.get("symmetry_summary"),
            "endpoints": line["endpoints"],
        },
        "endpoint_entry": endpoint,
        "field": "linear_character",
        "matched_unitary_indices": matched,
        "line_basis_labels": [f"L1_R{i}" for i in range(1, len(line_raw["linear_character"]) + 1)],
        "restricted_vector_for_P1_R1": complex_json(list(restricted)),
        "numeric_coefficients_for_P1_R1": complex_json(list(coeffs)),
        "nearest_integer_coefficients": nearest,
        "nearest_integer_residual_norm": float(np.linalg.norm(basis @ nearest_vector - restricted)),
        "expected_failure": "mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character",
    }
    write_json(evidence_root / "input_object.json", input_object)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout_path": str((evidence_root / "stdout.txt").relative_to(PACKAGE_ROOT)),
        "stderr_path": str((evidence_root / "stderr.txt").relative_to(PACKAGE_ROOT)),
        "exit_code_path": str((evidence_root / "exit_code.txt").relative_to(PACKAGE_ROOT)),
        "input_object_path": str((evidence_root / "input_object.json").relative_to(PACKAGE_ROOT)),
    }


def build_current_active_dump(current_debug) -> dict[str, Any]:
    module = current_debug.load_ssgreps_module()
    ssg_dict = current_debug.load_ssg_dict(current_debug.TARGET_GROUP)
    runtime, stdout = capture_stdout(
        current_debug.build_single_pilot,
        module,
        ssg_dict,
        line_phase_profile=current_debug.AUTHORITATIVE_PHASE_AWARE_PROFILE,
    )
    payload = {
        "stdout": stdout,
        "summary": runtime["summary"],
        "unknown_ordering": runtime["bs_analysis"]["unknown_ordering"],
        "point_row_translation": runtime["point_row_translation"],
    }
    write_json(PACKAGE_ROOT / "evidence" / "current_authoritative_success.json", payload)
    return payload


def build_line_and_plane_dumps(current_debug) -> dict[str, Any]:
    module = current_debug.load_ssgreps_module()
    ssg_dict = current_debug.load_ssg_dict(current_debug.TARGET_GROUP)
    ctx = current_debug.load_context(module, current_debug.TARGET_GROUP, "single", ssg_dict)
    prepared = current_debug.prepare_kgeometry(current_debug.TARGET_GROUP)
    grouped = prepared["grouped"]
    payload = prepared["payload"]
    kgeom = {"payload": payload, "grouped": grouped, "connectivity": payload}
    synthetic = current_debug.build_synthetic_boundary_points(kgeom)
    kgeom["synthetic_boundary_points"] = synthetic
    current_debug.augment_connectivity_with_boundary_points(kgeom, synthetic)
    current_debug.build_point_instance_entries(kgeom)
    ctx["kgeom"] = kgeom
    captures = current_debug.build_manifold_capture(module, current_debug.TARGET_GROUP, ssg_dict, ctx, "single", kgeom)

    l1 = next(item for item in grouped["lines"] if item["id"] == "L1")
    l1_block = current_debug.build_line_block(
        l1,
        captures,
        phase_aware_profile=current_debug.AUTHORITATIVE_PHASE_AWARE_PROFILE,
    )
    p1_endpoint = next(item for item in l1["endpoints"] if item["point_id"] == "P1")
    line_before_basis = np.array(captures["L1"]["linear_character"], dtype=complex).T
    line_before_matched = current_debug.matched_unitary_indices(captures["L1"], captures[p1_endpoint.get("capture_id", "P1")])
    line_before_restricted = np.array(captures[p1_endpoint.get("capture_id", "P1")]["linear_character"][0], dtype=complex)[line_before_matched]
    line_before_coeffs, _residuals, _rank, _sv = np.linalg.lstsq(line_before_basis, line_before_restricted, rcond=None)
    line_dump = {
        "before_linear_character_failure": {
            "field": "linear_character",
            "matched_unitary_indices": line_before_matched,
            "restricted_vector_for_P1_R1": complex_json(list(line_before_restricted)),
            "numeric_coefficients_for_P1_R1": complex_json(list(line_before_coeffs)),
            "nearest_integer_residual_norm": float(
                np.linalg.norm(
                    line_before_basis
                    @ np.array(
                        [int(round(value.real)) if abs(value.imag) < 1e-8 else 0 for value in line_before_coeffs],
                        dtype=complex,
                    )
                    - line_before_restricted
                )
            ),
        },
        "after_character_success": {
            "compatibility_field": l1_block["compatibility_field"],
            "line_basis_labels": l1_block["line_basis_labels"],
            "endpoint_decomposition_P1_R1": next(
                rep for rep in l1_block["endpoint_decompositions"]["P1"] if rep["rep_id"] == "P1_R1"
            ),
            "equations_head": l1_block["equations"][:3],
            "matrix_rows_head": l1_block["matrix_rows"][:3],
        },
    }
    write_json(PACKAGE_ROOT / "dumps" / "l1_line_block_before_after.json", line_dump)

    s3 = next(item for item in grouped["planes"] if item["id"] == "S3")
    s3_block = current_debug.build_plane_block(s3, s3["corner_entries"], captures)
    p1_corner = next(item for item in s3["corner_entries"] if item["point_id"] == "P1")
    plane_basis = np.array(captures["S3"]["linear_character"], dtype=complex).T
    point_raw = captures[p1_corner.get("capture_id", "P1")]
    plane_ops = [current_debug.operation_key_from_capture(captures["S3"], op_index) for op_index in captures["S3"]["unitary_capture_indices"]]
    unitary_map = {
        current_debug.operation_key_from_capture(point_raw, op_index): unitary_index
        for unitary_index, op_index in enumerate(point_raw["unitary_capture_indices"])
    }
    plane_matched = [unitary_map.get(op_key) for op_key in plane_ops]
    plane_restricted = np.array(point_raw["linear_character"][0], dtype=complex)[plane_matched]
    plane_coeffs, _residuals, _rank, _sv = np.linalg.lstsq(plane_basis, plane_restricted, rcond=None)
    plane_dump = {
        "before_linear_character_failure": {
            "field": "linear_character",
            "matched_unitary_indices": plane_matched,
            "restricted_vector_for_P1_R1": complex_json(list(plane_restricted)),
            "numeric_coefficients_for_P1_R1": complex_json(list(plane_coeffs)),
        },
        "after_character_success": {
            "compatibility_field": s3_block["compatibility_field"],
            "plane_basis_labels": s3_block["plane_basis_labels"],
            "equations_head": s3_block["equations"][:4],
            "matrix_rows_head": s3_block["matrix_rows"][:4],
        },
    }
    write_json(PACKAGE_ROOT / "dumps" / "s3_plane_block_before_after.json", plane_dump)
    return {"line_dump": line_dump, "plane_dump": plane_dump}


def build_shape_rank_comparison(active_dump: dict[str, Any]) -> dict[str, Any]:
    experiment = json.loads((ROOT / "experiment" / "bs_fix_experiment_report.json").read_text())
    comparison = {
        "active_42_shell": {
            "matrix_shape": active_dump["summary"]["BS_status"]["matrix_shape"],
            "rank": active_dump["summary"]["BS_status"]["rank"],
            "nullity": active_dump["summary"]["BS_status"]["nullity"],
            "unknown_count": len(active_dump["unknown_ordering"]),
            "unknown_ordering": active_dump["unknown_ordering"],
        },
        "diagnostic_fallback_34_shell": experiment["direct_restriction_class_fallback_probe"]["after"],
        "same_object_as_intended_42_shell": experiment["direct_restriction_class_fallback_probe"]["same_object_as_intended_42_shell"],
        "same_object_judgement_basis": {
            "dropped_unknowns_vs_intended_42_shell": experiment["direct_restriction_class_fallback_probe"]["dropped_unknowns_vs_intended_42_shell"],
            "added_unknowns_vs_intended_42_shell": experiment["direct_restriction_class_fallback_probe"]["added_unknowns_vs_intended_42_shell"],
        },
    }
    write_json(PACKAGE_ROOT / "dumps" / "shape_rank_nullity_comparison.json", comparison)
    return comparison


def build_generic_public_dump() -> dict[str, Any]:
    generic = load_current_generic_builders()
    records = generic.generic_result_objects("194.1.1.1")
    bundle = generic.generic_mode_bundle("194.1.1.1", "single", builder_variant="authoritative")
    payload = {
        "result_objects": records,
        "single_bundle_summary": {
            "compatibility_row_language_kind": bundle["compatibility"]["row_language_kind"],
            "compatibility_matrix_shape": bundle["compatibility"]["matrix_shape"],
            "unknown_ordering_tail": bundle["bs_analysis"]["unknown_ordering"][-8:],
            "quotient_compatibility_check_mode": bundle["quotient"]["compatibility_check_mode"],
            "diagnostic_projected_point_shell_classification": bundle["quotient"]["classification"],
        },
    }
    write_json(PACKAGE_ROOT / "dumps" / "generic_public_status_after.json", payload)
    return payload


def build_top5_bug_docs() -> dict[str, Any]:
    original_text = {
        "sg194/debug_workflow_portability_194.1.1.1.py": git_show("sg194/debug_workflow_portability_194.1.1.1.py"),
        "sg194/pipeline_v2/runtime_backend_free.py": git_show("sg194/pipeline_v2/runtime_backend_free.py"),
        "sg194/pipeline_v2/generic_builders.py": git_show("sg194/pipeline_v2/generic_builders.py"),
    }
    final_text = {
        path: (REPO_ROOT / path).read_text()
        for path in (
            "sg194/debug_workflow_portability_194.1.1.1.py",
            "sg194/pipeline_v2/runtime_backend_free.py",
            "sg194/pipeline_v2/generic_builders.py",
        )
    }
    bugs = [
        {
            "title": "Authoritative line builder used linear_character where character is required",
            "priority": "P0",
            "function": "build_line_block",
            "files": ["sg194/debug_workflow_portability_194.1.1.1.py", "sg194/pipeline_v2/runtime_backend_free.py"],
            "why_wrong": "L1/L2/L5 endpoint restrictions are integer-solvable in character language and non-integral in linear_character, so the old field choice manufactured the first source-layer blocker.",
            "why_bs_affects_core": "This failure happens inside the live line compatibility builder before any global with-planes matrix exists.",
            "minimal_fix": "Switch authoritative line subduction to character language for 194.1.1.1.",
            "witness": "first failure = mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character",
            "original_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 1195},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 1426},
            ],
            "final_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 1229},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 1460},
            ],
        },
        {
            "title": "Authoritative plane builder used linear_character where character is required",
            "priority": "P0",
            "function": "build_plane_block",
            "files": ["sg194/debug_workflow_portability_194.1.1.1.py", "sg194/pipeline_v2/runtime_backend_free.py"],
            "why_wrong": "S3 point-to-plane restrictions admit integer decomposition in character language but not in linear_character, so the old plane builder could not preserve the intended 42-shell.",
            "why_bs_affects_core": "Plane rows determine whether S1..S4 survive as active unknowns in the with-planes shell.",
            "minimal_fix": "Switch authoritative plane subduction to character language.",
            "witness": "diagnostic evidence = S3/P1_R1 non-integral in linear_character, successful in character",
            "original_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 1497},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 2002},
            ],
            "final_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 1533},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 2038},
            ],
        },
        {
            "title": "Exact solver rejected valid integer decompositions on float-snapped captures",
            "priority": "P0",
            "function": "solve_unique_integer_decomposition",
            "files": ["sg194/debug_workflow_portability_194.1.1.1.py", "sg194/pipeline_v2/runtime_backend_free.py"],
            "why_wrong": "Even when integer coefficients existed numerically, the symbolic exactness gate rejected them on float-snapped captures and could drive the solver into expensive GMP-heavy paths.",
            "why_bs_affects_core": "This gate decides whether line and plane rows are emitted at all; false negatives abort the authoritative BS construction.",
            "minimal_fix": "Add a numeric integer-certification step before the symbolic fallback.",
            "witness": "current repaired runtime would otherwise still fail later at L6/P2_R1 with exact reconstruction failed",
            "original_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 1040},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 1139},
            ],
            "final_refs": [
                {"path": "sg194/debug_workflow_portability_194.1.1.1.py", "line": 928},
                {"path": "sg194/pipeline_v2/runtime_backend_free.py", "line": 1027},
            ],
        },
        {
            "title": "Generic compatibility mislabeled the raw 42-shell as target row language",
            "priority": "P1",
            "function": "_build_generic_compatibility",
            "files": ["sg194/pipeline_v2/generic_builders.py"],
            "why_wrong": "The bundle was still the raw with-planes current shell, so labeling it as a canonical target row language hid the source/target mismatch.",
            "why_bs_affects_core": "This controls the object-language tag attached to the active compatibility matrix downstream BS/AI summaries publish.",
            "minimal_fix": "Publish the active matrix as current-row shell until a same-shell target builder exists.",
            "witness": "after repair the compatibility shape is [61, 42], so target-row labeling was demonstrably false",
            "original_refs": [
                {"path": "sg194/pipeline_v2/generic_builders.py", "line": 26},
                {"path": "sg194/pipeline_v2/generic_builders.py", "line": 397},
            ],
            "final_refs": [
                {"path": "sg194/pipeline_v2/generic_builders.py", "line": 26},
                {"path": "sg194/pipeline_v2/generic_builders.py", "line": 398},
            ],
        },
        {
            "title": "Generic/public result objects published a projected quotient as the active target object",
            "priority": "P1",
            "function": "generic_result_objects",
            "files": ["sg194/pipeline_v2/generic_builders.py"],
            "why_wrong": "The public API exposed projected point-shell diagnostics as if they were the authoritative same-shell BS/AI object, mixing 42-shell compatibility with 34-point-shell quotient semantics.",
            "why_bs_affects_core": "This changes the externally visible active BS/AI object rather than just packaging text.",
            "minimal_fix": "Expose only raw_shell as available and mark target_pending as blocked until a same-language target builder exists.",
            "witness": "current generic_result_objects now reports single_raw_shell/double_raw_shell available and *_target_pending blocked",
            "original_refs": [{"path": "sg194/pipeline_v2/generic_builders.py", "line": 934}],
            "final_refs": [{"path": "sg194/pipeline_v2/generic_builders.py", "line": 925}],
        },
    ]
    for bug in bugs:
        bug["original_code_segments"] = [
            {
                "path": ref["path"],
                "line": ref["line"],
                "snippet": line_numbered_snippet(original_text[ref["path"]], ref["line"]),
            }
            for ref in bug["original_refs"]
        ]
        bug["final_code_segments"] = [
            {
                "path": ref["path"],
                "line": ref["line"],
                "snippet": line_numbered_snippet(final_text[ref["path"]], ref["line"]),
            }
            for ref in bug["final_refs"]
        ]
    write_json(PACKAGE_ROOT / "bugs" / "top_5_bugs.json", {"generated_at": now_iso(), "bugs": bugs})
    lines = ["# Top 5 Bugs", ""]
    for index, bug in enumerate(bugs, start=1):
        lines.extend(
            [
                f"## {index}. {bug['title']}",
                "",
                f"- priority: `{bug['priority']}`",
                f"- function: `{bug['function']}`",
                f"- files: `{', '.join(bug['files'])}`",
                f"- why wrong: {bug['why_wrong']}",
                f"- why this affects BS core: {bug['why_bs_affects_core']}",
                f"- minimal fix: {bug['minimal_fix']}",
                f"- witness: `{bug['witness']}`",
                "",
                "Original code:",
            ]
        )
        for segment in bug["original_code_segments"]:
            lines.extend(
                [
                    f"- `{segment['path']}:{segment['line']}`",
                    "```python",
                    segment["snippet"],
                    "```",
                ]
            )
        lines.append("Final code:")
        for segment in bug["final_code_segments"]:
            lines.extend(
                [
                    f"- `{segment['path']}:{segment['line']}`",
                    "```python",
                    segment["snippet"],
                    "```",
                ]
            )
        lines.append("")
    write_text(PACKAGE_ROOT / "bugs" / "top_5_bugs.md", "\n".join(lines))
    return {"generated_at": now_iso(), "bugs": bugs}


def build_readme(
    source_manifest: dict[str, Any],
    output_manifest: dict[str, Any],
    patches: dict[str, Any],
    repro: dict[str, str],
    first_failure: dict[str, Any],
) -> None:
    write_text(
        PACKAGE_ROOT / "README.md",
        "\n".join(
            [
                "# External Review Package: SSG 194.1.1.1 BS Fix v1",
                "",
                "## Purpose",
                "",
                "- Hand off the exact source-level BS/AI bug repair for SSG `194.1.1.1`.",
                "- Provide original vs final source snapshots, unified diffs, first-failure evidence, key object dumps, and one-command repro scripts for line-by-line external code review.",
                "",
                "## One-Command Repro",
                "",
                f"- Original first failure: `{repro['first_failure_command']}`",
                f"- Current diagnostic experiment: `{repro['diagnostic_experiment_command']}`",
                "",
                "## Review Order",
                "",
                "- `bugs/top_5_bugs.md`",
                "- `evidence/first_failure/`",
                "- `dumps/l1_line_block_before_after.json`",
                "- `dumps/s3_plane_block_before_after.json`",
                "- `dumps/shape_rank_nullity_comparison.json`",
                "- `patches/overall.patch`",
                "- `sources/original/` and `sources/final/`",
                "",
                "## Included",
                "",
                f"- Source snapshot count: `{len(source_manifest['files'])}`",
                f"- Output snapshot count: `{len(output_manifest['files'])}`",
                f"- Overall patch: `{patches['overall_patch']}`",
                f"- First failure stderr: `{first_failure['stderr_path']}`",
                f"- First failure exit code: `{first_failure['returncode']}`",
                "",
                "## Scope",
                "",
                "- No Bilbao comparisons.",
                "- No magnetic-group detour.",
                "- No benchmark/internalization mainline.",
                "- Focus is the repo-internal BS construction and generic/public shell semantics for `194.1.1.1`.",
            ]
        ),
    )


def build_manifest(
    source_manifest: dict[str, Any],
    output_manifest: dict[str, Any],
    patch_manifest: dict[str, Any],
    repro_manifest: dict[str, str],
    first_failure: dict[str, Any],
    active_dump: dict[str, Any],
    comparison: dict[str, Any],
) -> None:
    write_json(
        PACKAGE_ROOT / "manifest.json",
        {
            "generated_at": now_iso(),
            "target_group": "194.1.1.1",
            "source_manifest": source_manifest,
            "output_manifest": output_manifest,
            "patch_manifest": patch_manifest,
            "repro_manifest": repro_manifest,
            "first_failure": first_failure,
            "active_after": {
                "matrix_shape": active_dump["summary"]["BS_status"]["matrix_shape"],
                "rank": active_dump["summary"]["BS_status"]["rank"],
                "nullity": active_dump["summary"]["BS_status"]["nullity"],
                "unknown_count": len(active_dump["unknown_ordering"]),
            },
            "diagnostic_fallback": {
                "matrix_shape": comparison["diagnostic_fallback_34_shell"]["matrix_shape"],
                "rank": comparison["diagnostic_fallback_34_shell"]["rank"],
                "nullity": comparison["diagnostic_fallback_34_shell"]["nullity"],
            },
        },
    )


def main() -> None:
    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True)
    (PACKAGE_ROOT / "bugs").mkdir()
    (PACKAGE_ROOT / "dumps").mkdir()

    source_manifest = write_file_snapshots(SOURCE_FILES, category="sources")
    patch_manifest = build_patch_artifacts()
    repro_manifest = write_repro_scripts()
    current_debug = load_current_debug_module()
    original_debug = load_original_debug_module()
    first_failure = build_first_failure_evidence(original_debug)
    active_dump = build_current_active_dump(current_debug)
    build_line_and_plane_dumps(current_debug)
    comparison = build_shape_rank_comparison(active_dump)
    build_generic_public_dump()
    build_top5_bug_docs()
    output_manifest = write_file_snapshots(OUTPUT_FILES, category="outputs")
    build_readme(source_manifest, output_manifest, patch_manifest, repro_manifest, first_failure)
    build_manifest(source_manifest, output_manifest, patch_manifest, repro_manifest, first_failure, active_dump, comparison)

    with tarfile.open(ARCHIVE_PATH, "w:gz") as tar:
        tar.add(PACKAGE_ROOT, arcname=PACKAGE_ROOT.name)

    print(
        json.dumps(
            {
                "package_root": str(PACKAGE_ROOT),
                "archive": str(ARCHIVE_PATH),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
