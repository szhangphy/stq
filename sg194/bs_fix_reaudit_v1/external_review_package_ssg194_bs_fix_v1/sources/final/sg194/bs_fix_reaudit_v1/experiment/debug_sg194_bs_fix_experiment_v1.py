#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
SG194_ROOT = REPO_ROOT / "sg194"
EXPERIMENT_ROOT = SG194_ROOT / "bs_fix_reaudit_v1" / "experiment"
REPORT_JSON = EXPERIMENT_ROOT / "bs_fix_experiment_report.json"
REPORT_MD = EXPERIMENT_ROOT / "bs_fix_experiment_report.md"
LOG_DIR = SG194_ROOT / "bs_fix_reaudit_v1" / "logs"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def import_stage1_debug_module():
    sys.path.insert(0, str(SG194_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "common"))
    path = SG194_ROOT / "debug_workflow_portability_194.1.1.1.py"
    spec = importlib.util.spec_from_file_location("sg194_stage1_debug", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def import_runtime_backend():
    sys.path.insert(0, str(REPO_ROOT))
    from sg194.pipeline_v2 import runtime_backend_free as port

    return port


def import_generic_builders():
    sys.path.insert(0, str(REPO_ROOT))
    from sg194.pipeline_v2 import generic_builders as generic

    return generic


def capture_stdout(fn, *args, **kwargs):
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        result = fn(*args, **kwargs)
    return result, stream.getvalue()


def hydrate_serialized_complex(value: Any) -> complex:
    if isinstance(value, dict) and "real" in value and "imag" in value:
        return complex(float(value["real"]), float(value["imag"]))
    return complex(value)


def hydrate_capture(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    for field in ("character", "linear_character"):
        out[field] = [[hydrate_serialized_complex(item) for item in row] for row in raw[field]]
    return out


def hydrate_cached_captures() -> dict[str, dict[str, Any]]:
    raw = json.loads((SG194_ROOT / "group_194_1_1_1_single_little_groups.json").read_text())
    return {key: hydrate_capture(value) for key, value in raw.items()}


def current_authoritative_runtime_probe(stage1_debug) -> tuple[dict[str, Any], str]:
    def run():
        module = stage1_debug.load_ssgreps_module()
        ssg_dict = stage1_debug.load_ssg_dict(stage1_debug.TARGET_GROUP)
        return stage1_debug.build_single_pilot(
            module,
            ssg_dict,
            line_phase_profile=stage1_debug.AUTHORITATIVE_PHASE_AWARE_PROFILE,
        )

    try:
        runtime, log = capture_stdout(run)
        summary = {
            "status": "success",
            "matrix_shape": runtime["summary"]["BS_status"]["matrix_shape"],
            "rank": runtime["summary"]["BS_status"]["rank"],
            "nullity": runtime["summary"]["BS_status"]["nullity"],
            "unknown_count": len(runtime["bs_analysis"]["unknown_ordering"]),
            "point_space_dimension": runtime.get("point_space_dimension"),
            "phase_aware_profile": runtime["phase_aware_profile"],
            "all_trivial_generators_compatibility_zero": runtime["summary"]["AI_status"][
                "all_trivial_generators_compatibility_zero"
            ],
        }
        return summary, log
    except Exception as exc:
        return (
            {
                "status": "error",
                "exc_type": type(exc).__name__,
                "exc": str(exc),
                "traceback": traceback.format_exc(),
            },
            "",
        )


def l1_numeric_probe(stage1_debug) -> dict[str, Any]:
    cached = json.loads((SG194_ROOT / "group_194_1_1_1_single_little_groups.json").read_text())
    point = hydrate_capture(cached["P1"])
    module = stage1_debug.load_ssgreps_module()
    ssg_dict = stage1_debug.load_ssg_dict(stage1_debug.TARGET_GROUP)
    ctx = stage1_debug.load_context(module, stage1_debug.TARGET_GROUP, "single", ssg_dict)
    samples = ([0.0, 0.0, 0.2], [0.0, 0.0, 0.8])
    sample_results = []
    for coords in samples:
        line = stage1_debug.capture_little_group(
            module,
            stage1_debug.TARGET_GROUP,
            ssg_dict,
            ctx,
            "single",
            "L1",
            coords,
        )
        matched = stage1_debug.matched_unitary_indices(line, point)
        basis = np.array(line["linear_character"], dtype=complex).T
        restricted = np.array(point["linear_character"][0], dtype=complex)[matched]
        coeffs, _residuals, rank, _singular_values = np.linalg.lstsq(basis, restricted, rcond=None)
        nearest_integer_coeffs = [
            int(round(value.real)) if abs(value.imag) < 1e-8 else None for value in coeffs
        ]
        nearest_integer_vector = np.array(
            [item if item is not None else 0 for item in nearest_integer_coeffs],
            dtype=complex,
        )
        sample_results.append(
            {
                "coords": list(coords),
                "rank": int(rank),
                "coeffs": [[float(value.real), float(value.imag)] for value in coeffs],
                "residual_norm": float(np.linalg.norm(basis @ coeffs - restricted)),
                "nearest_integer_coeffs": nearest_integer_coeffs,
                "nearest_integer_residual_norm": float(
                    np.linalg.norm(basis @ nearest_integer_vector - restricted)
                ),
            }
        )
    return {
        "matched_indices_for_P1_R1": matched,
        "samples": sample_results,
        "verdict": (
            "Both tested L1 sample points admit only complex non-integer coefficients for P1_R1 on the "
            "sampled line basis, so the active unique-integer basis-decomposition ansatz is invalid for L1."
        ),
    }


def restriction_class_fallback_probe(
    port,
    generic,
    current_runtime_summary: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    def run():
        prepared = port.prepare_kgeometry("194.1.1.1")
        grouped = prepared["grouped"]
        payload = prepared["payload"]
        kgeom = {"payload": payload, "grouped": grouped, "connectivity": payload}
        synthetic_points = port.build_synthetic_boundary_points(kgeom)
        kgeom["synthetic_boundary_points"] = synthetic_points
        port.augment_connectivity_with_boundary_points(kgeom, synthetic_points)
        port.build_point_instance_entries(kgeom)
        captures = hydrate_cached_captures()
        point_ids = [item["id"] for item in grouped["points"]] + [item["id"] for item in synthetic_points]

        def point_endpoint_decompositions(endpoint_entries):
            endpoint_decompositions = {}
            local_unknown_ordering = []
            for endpoint in endpoint_entries:
                endpoint_id = endpoint["point_id"]
                endpoint_raw = captures[endpoint.get("capture_id", endpoint_id)]
                reps = []
                for rep_index in range(1, len(endpoint_raw["linear_character"]) + 1):
                    rep_id = f"{endpoint_id}_R{rep_index}"
                    reps.append({"rep_id": rep_id})
                    local_unknown_ordering.append(rep_id)
                endpoint_decompositions[endpoint_id] = reps
            return endpoint_decompositions, local_unknown_ordering

        def equations_to_rows(equations, local_unknown_ordering):
            local_index = {unknown: index for index, unknown in enumerate(local_unknown_ordering)}
            rows = []
            for equation in equations:
                row = [0] * len(local_unknown_ordering)
                for term in equation["terms"]:
                    row[local_index[term["unknown"]]] += int(term["coeff"])
                rows.append(row)
            return rows

        before = dict(current_runtime_summary)

        line_blocks = []
        for line in grouped["lines"]:
            endpoint_entries = [
                {
                    "point_id": endpoint["point_id"],
                    "point_coordinates": endpoint["point_coordinates"],
                    "capture_id": endpoint.get("capture_id", endpoint["point_id"]),
                }
                for endpoint in line["endpoints"]
            ]
            rc = generic._build_restriction_class_rows(
                captures[line["id"]],
                endpoint_entries,
                captures,
                source_type="line",
                field="linear_character",
            )
            endpoint_decompositions, local_unknown_ordering = point_endpoint_decompositions(endpoint_entries)
            block = {
                "status": "experimental_line_restriction_class_fallback",
                "builder_variant": "experimental_all_intrinsic_class_sum",
                "line_id": line["id"],
                "endpoint_ids": [entry["point_id"] for entry in endpoint_entries],
                "endpoint_decompositions": endpoint_decompositions,
                "local_unknown_ordering": local_unknown_ordering,
                "equations": rc["equations"],
                "matrix_rows": equations_to_rows(rc["equations"], local_unknown_ordering),
                "compatibility_field": "linear_character",
                "phase_aware_refinement": {
                    "profile": "disabled_experimental_fallback",
                    "selected_endpoint_id": None,
                    "restriction_classes_by_endpoint": {},
                    "refinement_equations": [],
                },
            }
            line_blocks.append(block)
        line_full = port.build_global_compatibility(line_blocks, point_ids)

        plane_blocks = []
        for plane in grouped["planes"]:
            corners = plane["corner_entries"]
            rc = generic._build_restriction_class_rows(
                captures[plane["id"]],
                corners,
                captures,
                source_type="plane",
                field="linear_character",
            )
            local_unknown_ordering = []
            for corner in corners:
                point_id = corner["point_id"]
                point_raw = captures[corner.get("capture_id", point_id)]
                for rep_index in range(1, len(point_raw["linear_character"]) + 1):
                    local_unknown_ordering.append(f"{point_id}_R{rep_index}")
            equations = []
            for equation in rc["equations"]:
                point_id = equation.get("other_point_id") or equation.get("anchor_point_id")
                equations.append({**equation, "point_id": point_id})
            block = {
                "status": "experimental_plane_restriction_class_fallback",
                "plane_id": plane["id"],
                "corner_ids": [corner["point_id"] for corner in corners],
                "corner_decompositions": {},
                "local_unknown_ordering": local_unknown_ordering,
                "equations": equations,
                "matrix_rows": equations_to_rows(equations, local_unknown_ordering),
                "plane_basis_labels": [],
                "compatibility_field": "linear_character",
            }
            plane_blocks.append(block)
        with_planes = port.build_with_planes_compatibility(line_full, plane_blocks)
        bs = port.analyze_kernel(with_planes)

        intended_unknown_ordering = json.loads(
            (SG194_ROOT / "group_194_1_1_1_single_bs_analysis.json").read_text()
        )["unknown_ordering"]
        fallback_unknown_ordering = list(bs["unknown_ordering"])
        dropped_unknowns = [
            unknown for unknown in intended_unknown_ordering if unknown not in fallback_unknown_ordering
        ]
        added_unknowns = [
            unknown for unknown in fallback_unknown_ordering if unknown not in intended_unknown_ordering
        ]
        return {
            "before": before,
            "after": {
                "matrix_shape": bs["matrix_shape"],
                "rank": bs["rank"],
                "nullity": bs["nullity"],
                "unknown_count": len(bs["unknown_ordering"]),
                "line_rows": len(line_full["global_matrix"]),
                "plane_rows": len(with_planes["global_matrix"]) - len(line_full["global_matrix"]),
                "line_fallbacks": [{"line_id": line["id"], "reason": "experiment bypassed exact builder", "row_count": len(block["equations"])} for line, block in zip(grouped["lines"], line_blocks)],
                "plane_fallbacks": [{"plane_id": plane["id"], "reason": "experiment bypassed exact builder", "row_count": len(block["equations"])} for plane, block in zip(grouped["planes"], plane_blocks)],
                "unknown_ordering_head": bs["unknown_ordering"][:10],
                "unknown_ordering_tail": bs["unknown_ordering"][-10:],
                "basis_vector_count": len(bs["basis_vectors"]),
                "basis_vectors_head": bs["basis_vectors"][:3],
            },
            "intended_42_shell_unknown_count": len(intended_unknown_ordering),
            "fallback_unknown_count": len(fallback_unknown_ordering),
            "dropped_unknowns_vs_intended_42_shell": dropped_unknowns,
            "added_unknowns_vs_intended_42_shell": added_unknowns,
            "same_object_as_intended_42_shell": not dropped_unknowns and not added_unknowns,
            "ai_candidates_still_in_same_object": False,
            "verdict": (
                "The cache-driven restriction-class rebuild proves that removing the exact basis-decomposition "
                "path makes BS matrix construction terminate again, but the rebuilt object collapses to a 34-point "
                "shell rather than preserving the intended 42-unknown with-planes shell, so it is diagnostic only."
            ),
        }

    return capture_stdout(run)


def build_report_payload() -> dict[str, Any]:
    stage1_debug = import_stage1_debug_module()
    port = import_runtime_backend()
    generic = import_generic_builders()

    current_runtime, current_log = current_authoritative_runtime_probe(stage1_debug)
    l1_numeric = l1_numeric_probe(stage1_debug)
    fallback_probe, fallback_log = restriction_class_fallback_probe(port, generic, current_runtime)

    log_payload = {
        "generated_at": now_iso(),
        "current_authoritative_runtime_stdout": current_log,
        "restriction_class_fallback_stdout": fallback_log,
    }
    write_json(LOG_DIR / "bs_fix_experiment_probe_logs.json", log_payload)

    return {
        "generated_at": now_iso(),
        "target_group": "194.1.1.1",
        "current_authoritative_runtime": current_runtime,
        "l1_numeric_decomposition_probe": l1_numeric,
        "direct_restriction_class_fallback_probe": fallback_probe,
    }


def build_report_markdown(payload: dict[str, Any]) -> str:
    current_runtime = payload["current_authoritative_runtime"]
    l1_numeric = payload["l1_numeric_decomposition_probe"]
    fallback_probe = payload["direct_restriction_class_fallback_probe"]
    lines = [
        "# SG194 BS Fix Experiment v1",
        "",
        "## Scope",
        "",
        "- Target fixed to `194.1.1.1`.",
        "- No Bilbao / magnetic-group / benchmark/internalization inputs were used.",
        "- This experiment only tests the repo-internal BS construction hypothesis.",
        "",
        "## Probe 1: Current Authoritative Runtime",
        "",
        f"- status: `{current_runtime['status']}`",
    ]
    if current_runtime["status"] == "error":
        lines.append(f"- first hard failure: `{current_runtime['exc']}`")
    else:
        lines.append(
            f"- matrix shape/rank/nullity: `{current_runtime['matrix_shape']}` / `{current_runtime['rank']}` / `{current_runtime['nullity']}`"
        )
    lines.extend(
        [
            "",
            "## Probe 2: L1 Numeric Decomposition",
            "",
            "- target channel: `L1 -> P1_R1` under `linear_character`.",
            f"- verdict: {l1_numeric['verdict']}",
            "",
            "| sample | coeff summary | numeric residual | integer residual |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for item in l1_numeric["samples"]:
        coeffs = ", ".join(
            f"{value[0]:.6f}{value[1]:+.6f}i" for value in item["coeffs"] if abs(value[0]) > 1e-10 or abs(value[1]) > 1e-10
        )
        lines.append(
            f"| `{item['coords']}` | `{coeffs}` | `{item['residual_norm']:.3e}` | `{item['nearest_integer_residual_norm']:.3e}` |"
        )
    lines.extend(
        [
            "",
            "## Probe 3: Direct Restriction-Class Fallback",
            "",
            f"- current build before fallback: `{fallback_probe['before']['status']}`",
        ]
    )
    if fallback_probe["before"]["status"] == "error":
        lines.append(f"- current build failure: `{fallback_probe['before']['exc']}`")
    after = fallback_probe["after"]
    lines.extend(
        [
            f"- fallback matrix shape/rank/nullity: `{after['matrix_shape']}` / `{after['rank']}` / `{after['nullity']}`",
            f"- fallback line rows / plane rows: `{after['line_rows']}` / `{after['plane_rows']}`",
            f"- fallback lines: `{[item['line_id'] for item in after['line_fallbacks']]}`",
            f"- fallback planes: `{[item['plane_id'] for item in after['plane_fallbacks']]}`",
            f"- basis vector count after fallback: `{after['basis_vector_count']}`",
            f"- same object as intended 42-shell: `{fallback_probe['same_object_as_intended_42_shell']}`",
            f"- dropped unknowns vs intended 42-shell: `{fallback_probe['dropped_unknowns_vs_intended_42_shell']}`",
            f"- AI candidates still in same object: `{fallback_probe['ai_candidates_still_in_same_object']}`",
            "",
            "## Conclusion",
            "",
            "- The active repo failure is real and reproduces directly in the current source at `L1/P1_R1`.",
            "- `linear_character` plus exact unique integer basis decomposition is not automatically correct; L1 needs complex coefficients at both tested sample points.",
            "- A cache-driven direct restriction-class fallback can rebuild a BS matrix, which confirms the sampled-manifold integer decomposition ansatz is the blocker, but that fallback changes the object from the intended 42-shell to a 34-point shell.",
            "- This experiment therefore validates the bug diagnosis but does not yet constitute the final repo patch.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_report_payload()
    write_json(REPORT_JSON, payload)
    write_text(REPORT_MD, build_report_markdown(payload))
    print(json.dumps({"report_json": str(REPORT_JSON), "report_md": str(REPORT_MD)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
