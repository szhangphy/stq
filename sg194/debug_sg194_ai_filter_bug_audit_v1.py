from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import sympy as sp

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.generic_builders import _point_row_indices, generic_mode_bundle
from sg194.pipeline_v2.utils import now_iso, write_json, write_text

SG194_DIR = REPO_ROOT / "sg194"
GROUP = "222.1.1.1"
OG_OBJECT = "222.1.1601"


def _row_provenance(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    compatibility = bundle["compatibility"]
    rows: list[dict[str, Any]] = []
    for block in compatibility.get("line_blocks", []):
        for eq in block.get("equations", []):
            rows.append(
                {
                    "source_type": "line",
                    "source_id": block.get("line_id"),
                    "basis_id": eq.get("basis_id"),
                    "endpoint_ids": block.get("endpoint_ids"),
                    "equation": eq,
                }
            )
    for block in compatibility.get("plane_blocks", []):
        for eq in block.get("equations", []):
            rows.append(
                {
                    "source_type": "plane",
                    "source_id": block.get("plane_id"),
                    "basis_id": eq.get("basis_id"),
                    "corner_ids": block.get("corner_ids"),
                    "equation": eq,
                }
            )
    return rows


def _point_bs_matrix(bundle: dict[str, Any]) -> tuple[sp.Matrix, list[int]]:
    basis_vectors = [item["vector"] for item in bundle["bs_analysis"]["basis_vectors"]]
    unknown_ordering = bundle["bs_analysis"]["unknown_ordering"]
    point_ids = bundle["shared_geometry"]["point_ids"]
    point_indices = _point_row_indices(unknown_ordering, point_ids)
    if basis_vectors:
        point_bs_matrix = sp.Matrix.hstack(
            *[sp.Matrix([int(vector[index]) for index in point_indices]) for vector in basis_vectors]
        )
    else:
        point_bs_matrix = sp.zeros(len(point_indices), 0)
    return point_bs_matrix, point_indices


def _solve_reason(point_bs_matrix: sp.Matrix, point_vector: list[int]) -> str:
    try:
        solution, parameters = point_bs_matrix.gauss_jordan_solve(sp.Matrix(point_vector))
        if parameters.free_symbols:
            return "parametric_solution"
        for entry in solution:
            if getattr(entry, "q", 1) != 1:
                return f"non_integral:{entry}"
        return "solved"
    except Exception as exc:  # pragma: no cover - diagnostic path
        return str(exc)


def _mode_payload(mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bundle = generic_mode_bundle(GROUP, mode)
    compatibility = bundle["compatibility"]
    provenance = _row_provenance(bundle)
    matrix = sp.Matrix(compatibility["global_matrix"])
    point_bs_matrix, point_indices = _point_bs_matrix(bundle)
    candidate_by_id = {
        candidate["generator_id"]: candidate
        for candidate in bundle["induced"]["candidates"]
    }
    dropped: list[dict[str, Any]] = []
    for item in bundle["quotient"]["ai_incompatible_candidates"]:
        candidate = candidate_by_id[item["generator_id"]]
        residual = matrix * sp.Matrix(candidate["unknown_vector"])
        support = []
        for row_index, value in enumerate(residual):
            intval = int(value)
            if intval == 0:
                continue
            support.append(
                {
                    "row_index": row_index,
                    "residual": intval,
                    "row_descriptor": (
                        compatibility["global_matrix_rows"][row_index]
                        if row_index < len(compatibility.get("global_matrix_rows", []))
                        else None
                    ),
                    "provenance": provenance[row_index] if row_index < len(provenance) else None,
                }
            )
        point_vector = [int(candidate["unknown_vector"][index]) for index in point_indices]
        dropped.append(
            {
                "generator_id": item["generator_id"],
                "family_letter": item.get("family_letter"),
                "solve_reason": _solve_reason(point_bs_matrix, point_vector),
                "compatibility_residual_support": support,
                "full_residual_rank_hint": len(support),
            }
        )
    payload = {
        "mode": mode,
        "generic_target_direct_result": {
            "dBS": bundle["quotient"]["dBS"],
            "dAI": bundle["quotient"]["dAI"],
            "classification": bundle["quotient"]["classification"],
            "dbs_dai_gap": bundle["quotient"]["dbs_dai_gap"],
        },
        "ai_candidate_count": bundle["quotient"]["ai_candidate_count"],
        "ai_candidate_count_used": bundle["quotient"]["ai_candidate_count_used"],
        "ai_incompatible_count": bundle["quotient"]["ai_incompatible_count"],
        "dropped_candidates": dropped,
    }
    return payload, dropped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    single_payload, single_dropped = _mode_payload("single")
    double_payload, double_dropped = _mode_payload("double")
    audit = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "bug_exists": True,
        "root_cause": (
            "The generic 222 quotient path silently drops AI candidates that fail the exact point-shell "
            "embedding solve, then computes Smith quotient on the survivors only. This creates the "
            "observed dBS != dAI gap and fake-final classification."
        ),
        "single": single_payload,
        "double": double_payload,
    }
    dropped = {
        "generated_at": now_iso(),
        "group": GROUP,
        "equivalent_og_object": OG_OBJECT,
        "single": single_dropped,
        "double": double_dropped,
    }

    write_json(SG194_DIR / "sg194_ai_filter_bug_audit_v1.json", audit)
    write_json(SG194_DIR / "sg194_dropped_ai_candidates_v1.json", dropped)
    write_text(
        SG194_DIR / "sg194_ai_filter_bug_audit_v1.md",
        "\n".join(
            [
                "# AI Filter Bug Audit",
                "",
                f"- group: `{GROUP}`",
                f"- equivalent OG object: `{OG_OBJECT}`",
                f"- bug exists: `{audit['bug_exists']}`",
                f"- root cause: `{audit['root_cause']}`",
                f"- single generic target direct: `{single_payload['generic_target_direct_result']}`",
                f"- double generic target direct: `{double_payload['generic_target_direct_result']}`",
            ]
        ),
    )
    dropped_lines = [
        "# Dropped AI Candidates",
        "",
        f"- single dropped count: `{len(single_dropped)}`",
        f"- double dropped count: `{len(double_dropped)}`",
        "",
        "## Single",
        *[
            f"- `{item['generator_id']}`: `{item['solve_reason']}` / support rows `{[entry['row_index'] for entry in item['compatibility_residual_support']]}`"
            for item in single_dropped
        ],
        "",
        "## Double",
        *[
            f"- `{item['generator_id']}`: `{item['solve_reason']}` / support rows `{[entry['row_index'] for entry in item['compatibility_residual_support']]}`"
            for item in double_dropped
        ],
    ]
    write_text(SG194_DIR / "sg194_dropped_ai_candidates_v1.md", "\n".join(dropped_lines))

    if args.validate:
        if single_payload["generic_target_direct_result"]["dBS"] == single_payload["generic_target_direct_result"]["dAI"]:
            raise SystemExit("single generic probe no longer shows the expected dBS != dAI bug")
        if not single_dropped or not double_dropped:
            raise SystemExit("expected dropped AI candidates were not found")


if __name__ == "__main__":
    main()
