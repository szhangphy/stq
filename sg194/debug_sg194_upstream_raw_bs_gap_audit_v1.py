#!/usr/bin/env python3
from __future__ import annotations

import cmath
import json
from pathlib import Path
from typing import Any

import sympy as sp


ROOT = Path(__file__).resolve().parent

SINGLE_BS_JSON = ROOT / "group_194_1_1_1_single_bs_analysis.json"
DOUBLE_BS_JSON = ROOT / "group_194_1_1_1_double_bs_analysis.json"
SINGLE_AI_SUMMARY_JSON = ROOT / "group_194_1_1_1_single_ai_completion_summary.json"
DOUBLE_AI_SUMMARY_JSON = ROOT / "group_194_1_1_1_double_ai_completion_summary.json"
SINGLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_single_indicator_generators.json"
DOUBLE_INDICATOR_GENERATORS_JSON = ROOT / "group_194_1_1_1_double_indicator_generators.json"
SINGLE_LINE_COMPAT_JSON = ROOT / "group_194_1_1_1_single_line_compatibility.json"
SINGLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_single_full_compatibility_with_planes.json"
DOUBLE_WITH_PLANES_JSON = ROOT / "group_194_1_1_1_double_full_compatibility_with_planes.json"
SINGLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_single_little_groups.json"
DOUBLE_LITTLE_GROUPS_JSON = ROOT / "group_194_1_1_1_double_little_groups.json"

STAGE1_SCRIPT = ROOT / "debug_workflow_portability_194.1.1.1.py"
COMMON_SSGREPS = ROOT.parent / "common" / "SSGReps.py"

RAW_GAP_AUDIT_JSON = ROOT / "sg194_upstream_raw_bs_gap_audit_v1.json"
RAW_GAP_AUDIT_MD = ROOT / "sg194_upstream_raw_bs_gap_audit_v1.md"
PHASE_AUDIT_JSON = ROOT / "sg194_phase_and_subduction_audit_v1.json"
PHASE_AUDIT_MD = ROOT / "sg194_phase_and_subduction_audit_v1.md"
FIX_PLAN_MD = ROOT / "sg194_upstream_raw_bs_fix_plan_v1.md"

P3_P4_ROWS = [
    "P3_R1",
    "P3_R2",
    "P3_R3",
    "P3_R4",
    "P3_R5",
    "P3_R6",
    "P4_R1",
    "P4_R2",
    "P4_R3",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def as_exact_char(value: Any) -> sp.Expr:
    if isinstance(value, dict):
        real = float(value["real"])
        imag = float(value["imag"])
    elif isinstance(value, complex):
        real = float(value.real)
        imag = float(value.imag)
    else:
        real = float(value)
        imag = 0.0
    if abs(imag) < 1e-8:
        if abs(real - round(real)) < 1e-8:
            return sp.Integer(int(round(real)))
        return sp.nsimplify(real)
    return sp.nsimplify(real) + sp.I * sp.nsimplify(imag)


def find_line(path: Path, needle: str) -> int | None:
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        if needle in line:
            return line_no
    return None


def operation_key(capture: dict[str, Any], op_index: int) -> tuple[Any, ...]:
    rot = tuple(tuple(int(round(float(entry))) for entry in row) for row in capture["rotC"][op_index])
    tau = tuple(round(float(entry) % 1.0, 8) for entry in capture["tauC"][op_index])
    spin = tuple(tuple(round(float(entry), 8) for entry in row) for row in capture["spin"][op_index])
    return rot, tau, spin, int(capture["timeReversal"][op_index])


def support_from_unknown_vector(ordering: list[str], vector: list[int]) -> list[dict[str, Any]]:
    return [
        {"label": label, "coeff": int(coeff)}
        for label, coeff in zip(ordering, vector)
        if int(coeff) != 0
    ]


def common_free_generators() -> list[dict[str, Any]]:
    single = load_json(SINGLE_INDICATOR_GENERATORS_JSON)["free_generators"]
    double = load_json(DOUBLE_INDICATOR_GENERATORS_JSON)["free_generators"]
    if len(single) != len(double):
        raise RuntimeError("single/double free generator counts diverged")
    out: list[dict[str, Any]] = []
    for idx, (left, right) in enumerate(zip(single, double), start=1):
        if left["bs_basis_coordinates"] != right["bs_basis_coordinates"]:
            raise RuntimeError(f"generator #{idx}: single/double BS coordinates diverged")
        if left["unknown_vector"] != right["unknown_vector"]:
            raise RuntimeError(f"generator #{idx}: single/double support diverged")
        support = support_from_unknown_vector(left["unknown_ordering"], left["unknown_vector"])
        block_support: dict[str, list[str]] = {}
        for item in support:
            block_support.setdefault(item["label"].split("_", 1)[0], []).append(item["label"])
        out.append(
            {
                "generator_id": f"common_free_generator_{idx}",
                "single_indicator_id": left["indicator_id"],
                "double_indicator_id": right["indicator_id"],
                "bs_basis_coordinates": [int(value) for value in left["bs_basis_coordinates"]],
                "support": support,
                "support_blocks": {key: value for key, value in sorted(block_support.items())},
            }
        )
    return out


def p3_p4_sector_summary(with_planes: dict[str, Any]) -> dict[str, Any]:
    ordering = list(with_planes["global_unknown_ordering"])
    indices = [ordering.index(label) for label in P3_P4_ROWS]
    rows = []
    for entry in with_planes["global_matrix_rows"]:
        matrix_row = list(entry["matrix_row"])
        restricted = [int(matrix_row[index]) for index in indices]
        if any(restricted):
            rows.append(
                {
                    "source_type": entry["source_type"],
                    "source_id": entry.get("line_id") or entry.get("plane_id"),
                    "basis_id": entry["basis_id"],
                    "restricted_row": restricted,
                    "restricted_support": [
                        {"label": label, "coeff": coeff}
                        for label, coeff in zip(P3_P4_ROWS, restricted)
                        if coeff
                    ],
                }
            )
    matrix = sp.Matrix([item["restricted_row"] for item in rows]) if rows else sp.zeros(0, len(indices))
    return {
        "sector_rows": P3_P4_ROWS,
        "touching_constraint_rows": rows,
        "touching_source_counts": {
            source: sum(1 for item in rows if item["source_id"] == source)
            for source in sorted({item["source_id"] for item in rows})
        },
        "touching_plane_ids": sorted({item["source_id"] for item in rows if item["source_type"] == "plane"}),
        "touching_line_ids": sorted({item["source_id"] for item in rows if item["source_type"] == "line"}),
        "restricted_matrix_shape": [int(matrix.rows), int(matrix.cols)],
        "restricted_matrix_rank": int(matrix.rank()),
        "restricted_matrix_nullity": int(matrix.cols - matrix.rank()),
    }


def generator_residuals(with_planes: dict[str, Any], generators: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordering = list(with_planes["global_unknown_ordering"])
    matrix = sp.Matrix(with_planes["global_matrix"])
    out: list[dict[str, Any]] = []
    for generator in generators:
        dense = [0] * len(ordering)
        support = {item["label"]: int(item["coeff"]) for item in generator["support"]}
        for idx, label in enumerate(ordering):
            dense[idx] = support.get(label, 0)
        residual = list(matrix * sp.Matrix(dense))
        touched_rows = []
        for row_index, entry in enumerate(with_planes["global_matrix_rows"]):
            row_support = [
                ordering[column_index]
                for column_index, coeff in enumerate(entry["matrix_row"])
                if int(coeff) != 0 and dense[column_index] != 0
            ]
            if row_support:
                touched_rows.append(
                    {
                        "row_index": row_index,
                        "source_type": entry["source_type"],
                        "source_id": entry.get("line_id") or entry.get("plane_id"),
                        "basis_id": entry["basis_id"],
                        "row_support": row_support,
                        "residual": int(residual[row_index]),
                    }
                )
        out.append(
            {
                "generator_id": generator["generator_id"],
                "nonzero_residual_rows": [
                    {
                        "row_index": row_index,
                        "residual": int(value),
                    }
                    for row_index, value in enumerate(residual)
                    if int(value) != 0
                ],
                "touched_rows": touched_rows,
            }
        )
    return out


def l2_equations() -> list[dict[str, Any]]:
    line_payload = load_json(SINGLE_LINE_COMPAT_JSON)
    block = next(item for item in line_payload["line_blocks"] if item["line_id"] == "L2")
    out = []
    for equation, row in zip(block["equations"], block["matrix_rows"]):
        out.append(
            {
                "basis_id": equation["basis_id"],
                "terms": [
                    {"label": label, "coeff": int(coeff)}
                    for label, coeff in zip(block["local_unknown_ordering"], row)
                    if int(coeff) != 0
                ],
            }
        )
    return out


def phase_for_operation(capture: dict[str, Any], op_index: int) -> complex:
    phase_argument = sum(float(k) * float(tau) for k, tau in zip(capture["kconv"], capture["tauC"][op_index]))
    return cmath.exp(-1j * phase_argument)


def phase_relation_report(capture: dict[str, Any]) -> dict[str, Any]:
    ops = []
    for op_index in capture["unitary_capture_indices"]:
        tau = list(capture["tauC"][op_index])
        phase = phase_for_operation(capture, op_index)
        ops.append(
            {
                "operation_index": int(op_index),
                "tau": tau,
                "phase": {"real": round(float(phase.real), 12), "imag": round(float(phase.imag), 12)},
                "phase_is_trivial": abs(phase - 1) < 1e-8,
            }
        )
    checks = []
    for rep_index, (raw_row, linear_row) in enumerate(zip(capture["character_json"], capture["linear_character_json"]), start=1):
        max_error = 0.0
        nontrivial_ops = []
        for op_index in capture["unitary_capture_indices"]:
            phase = phase_for_operation(capture, op_index)
            raw = complex(float(raw_row[op_index]["real"]), float(raw_row[op_index]["imag"]))
            linear = complex(float(linear_row[op_index]["real"]), float(linear_row[op_index]["imag"]))
            err = abs(linear - raw * phase)
            max_error = max(max_error, err)
            if abs(phase - 1) > 1e-8 and abs(raw) > 1e-8:
                nontrivial_ops.append(
                    {
                        "operation_index": int(op_index),
                        "raw_character": {"real": round(float(raw.real), 12), "imag": round(float(raw.imag), 12)},
                        "linear_character": {"real": round(float(linear.real), 12), "imag": round(float(linear.imag), 12)},
                    }
                )
        checks.append(
            {
                "rep_index": rep_index,
                "max_linear_equals_raw_times_phase_error": round(float(max_error), 12),
                "nontrivial_phase_examples": nontrivial_ops[:3],
            }
        )
    return {
        "kconv": [round(float(value), 12) for value in capture["kconv"]],
        "operations": ops,
        "rep_checks": checks,
    }


def line_subduction_audit(little_groups: dict[str, Any], line_id: str, endpoint_ids: list[str], flavor: str) -> dict[str, Any]:
    line_capture = little_groups[line_id]
    line_unitary_ops = [operation_key(line_capture, op_index) for op_index in line_capture["unitary_capture_indices"]]
    line_basis_matrix = sp.Matrix(
        [[as_exact_char(value) for value in rep_character] for rep_character in line_capture[flavor]]
    ).T
    endpoint_reports = []
    for endpoint_id in endpoint_ids:
        endpoint_capture = little_groups[endpoint_id]
        unitary_map = {
            operation_key(endpoint_capture, op_index): unitary_index
            for unitary_index, op_index in enumerate(endpoint_capture["unitary_capture_indices"])
        }
        matched = [unitary_map.get(op_key) for op_key in line_unitary_ops]
        if any(index is None for index in matched):
            raise RuntimeError(f"{endpoint_id} does not contain the full {line_id} unitary subgroup")
        rep_reports = []
        for rep_index, rep_character in enumerate(endpoint_capture[flavor], start=1):
            restricted = sp.Matrix([as_exact_char(rep_character[index]) for index in matched])
            try:
                coeffs = list(line_basis_matrix.LUsolve(restricted))
                integral = True
                serialized = []
                for coeff in coeffs:
                    coeff_eval = complex(coeff.evalf())
                    if abs(coeff_eval.imag) < 1e-8 and abs(coeff_eval.real - round(coeff_eval.real)) < 1e-8:
                        serialized.append(int(round(coeff_eval.real)))
                    else:
                        integral = False
                        serialized.append(str(sp.simplify(coeff)))
                rep_reports.append(
                    {
                        "rep_id": f"{endpoint_id}_R{rep_index}",
                        "status": "ok" if integral else "non_integral",
                        "coefficients": serialized,
                    }
                )
            except Exception as exc:
                rep_reports.append(
                    {
                        "rep_id": f"{endpoint_id}_R{rep_index}",
                        "status": "inconsistent",
                        "error": str(exc),
                    }
                )
        endpoint_reports.append({"endpoint_id": endpoint_id, "rep_reports": rep_reports})
    return {"line_id": line_id, "flavor": flavor, "endpoint_reports": endpoint_reports}


def gap_payload() -> dict[str, Any]:
    single_bs = load_json(SINGLE_BS_JSON)
    double_bs = load_json(DOUBLE_BS_JSON)
    single_summary = load_json(SINGLE_AI_SUMMARY_JSON)
    double_summary = load_json(DOUBLE_AI_SUMMARY_JSON)
    single_with_planes = load_json(SINGLE_WITH_PLANES_JSON)
    double_with_planes = load_json(DOUBLE_WITH_PLANES_JSON)
    generators = common_free_generators()
    sector = p3_p4_sector_summary(single_with_planes)
    return {
        "target_group": "194.1.1.1",
        "raw_rank_bs_single": int(single_bs["nullity"]),
        "raw_rank_bs_double": int(double_bs["nullity"]),
        "raw_rank_ai_single": int(single_summary["rank_ai_raw_internal"]),
        "raw_rank_ai_double": int(double_summary["rank_ai_raw_internal"]),
        "raw_quotient_group_single": single_summary["raw_internal_quotient_group"],
        "raw_quotient_group_double": double_summary["raw_internal_quotient_group"],
        "common_free_generator_count": len(generators),
        "common_free_generators": generators,
        "p3_p4_sector_summary": sector,
        "l2_line_equations": l2_equations(),
        "single_with_planes_generator_residuals": generator_residuals(single_with_planes, generators),
        "double_with_planes_generator_residuals": generator_residuals(double_with_planes, generators),
        "classification": {
            "primary": "missing_effective_constraints_in_P3_P4_sector",
            "secondary": [
                "wrong_use_of_little_co_group_vs_full_little_group_representation",
                "wrong_handling_of_translational_Bloch_phase_e_minus_ik_t_in_compatibility_subduction",
            ],
            "not_supported_by_evidence": [
                "wrong_endpoint_restriction_geometry",
                "wrong_plane_gluing_on_existing_P3_P4_planes",
                "wrong_little_group_representation_construction_in_induction",
            ],
            "verdict": (
                "The three raw free directions survive because the current P3/P4 sector is only seen by the three L2 co-group equations, "
                "and no plane row touches P3/P4 at all. Algebraically this leaves the K/H sector underconstrained; implementation-wise "
                "the compatibility builder is using a phase-stripped character layer rather than a full little-group/projective subduction object."
            ),
        },
    }


def phase_payload() -> dict[str, Any]:
    single_little = load_json(SINGLE_LITTLE_GROUPS_JSON)
    double_little = load_json(DOUBLE_LITTLE_GROUPS_JSON)
    return {
        "target_group": "194.1.1.1",
        "source_code_evidence": {
            "build_line_block_uses_character": {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "line": find_line(STAGE1_SCRIPT, 'line_basis_matrix = sp.Matrix([[as_exact_char(value) for value in rep_character] for rep_character in line_raw["character"]]).T'),
            },
            "build_plane_block_uses_character": {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "line": find_line(STAGE1_SCRIPT, 'plane_basis_matrix = sp.Matrix([[as_exact_char(value) for value in rep_character] for rep_character in plane_raw["character"]]).T'),
            },
            "induce_candidate_explicit_bloch_phase": {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "line": find_line(STAGE1_SCRIPT, "np.exp(-1j * float(np.dot(np.array(info[\"kconv\"], dtype=float), delta)))"),
            },
            "induce_candidate_uses_linear_character": {
                "file": "sg194/debug_workflow_portability_194.1.1.1.py",
                "line": find_line(STAGE1_SCRIPT, 'chars = np.array(info["linear_character"], dtype=complex)'),
            },
            "ssgreps_linear_character_formula": {
                "file": "common/SSGReps.py",
                "line": find_line(COMMON_SSGREPS, "ch.append(rep[uni]* np.exp(-1j * np.dot(k_conv, self.tauC[uni])))"),
            },
        },
        "phase_relation_examples": {
            "single_L2": phase_relation_report(single_little["L2"]),
            "single_P3": phase_relation_report(single_little["P3"]),
            "single_P4": phase_relation_report(single_little["P4"]),
            "double_L2": phase_relation_report(double_little["L2"]),
            "double_P3": phase_relation_report(double_little["P3"]),
            "double_P4": phase_relation_report(double_little["P4"]),
        },
        "subduction_tests": {
            "single_L2_using_character": line_subduction_audit(single_little, "L2", ["P3", "P4"], "character_json"),
            "single_L2_using_linear_character": line_subduction_audit(single_little, "L2", ["P3", "P4"], "linear_character_json"),
            "double_L2_using_character": line_subduction_audit(double_little, "L2", ["P3", "P4"], "character_json"),
            "double_L2_using_linear_character": line_subduction_audit(double_little, "L2", ["P3", "P4"], "linear_character_json"),
        },
        "verdict": {
            "compatibility_builder_uses_phase_stripped_character": True,
            "induction_builder_uses_full_linear_character_with_bloch_phase": True,
            "little_co_group_vs_full_little_group_mismatch_present": True,
            "most_likely_effect": (
                "On the K/H line L2, the current compatibility builder collapses the nonsymmorphic phase-bearing sector to three raw-character equations. "
                "Those equations are exactly the ones that leave the common Z^3 directions alive."
            ),
        },
    }


def build_gap_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Upstream Raw BS Gap Audit v1",
        "",
        "## Summary",
        "",
        f"- raw single rank(BS) = `{payload['raw_rank_bs_single']}`",
        f"- raw double rank(BS) = `{payload['raw_rank_bs_double']}`",
        f"- raw single/double quotient = `{payload['raw_quotient_group_single']}` / `{payload['raw_quotient_group_double']}`",
        f"- common free-generator count = `{payload['common_free_generator_count']}`",
        "",
        "## The Three Common Free Directions",
        "",
    ]
    for item in payload["common_free_generators"]:
        lines.extend(
            [
                f"- `{item['generator_id']}`",
                f"  - support = `{item['support']}`",
                f"  - support blocks = `{item['support_blocks']}`",
                f"  - BS coordinates = `{item['bs_basis_coordinates']}`",
            ]
        )
    sector = payload["p3_p4_sector_summary"]
    lines.extend(
        [
            "",
            "## P3/P4 Constraint Exposure",
            "",
            f"- sector rows = `{sector['sector_rows']}`",
            f"- touching line ids = `{sector['touching_line_ids']}`",
            f"- touching plane ids = `{sector['touching_plane_ids']}`",
            f"- restricted matrix shape/rank/nullity = `{sector['restricted_matrix_shape']}` / `{sector['restricted_matrix_rank']}` / `{sector['restricted_matrix_nullity']}`",
            f"- touching source counts = `{sector['touching_source_counts']}`",
            "",
            "The current full compatibility matrix only sees the P3/P4 sector through the three `L2` rows below:",
            "",
        ]
    )
    for item in payload["l2_line_equations"]:
        lines.append(f"- `{item['basis_id']}`: `{item['terms']}`")
    lines.extend(
        [
            "",
            "## Residual Check",
            "",
            "Every common free generator has zero residual against the full single and double with-planes matrix, but each one is only touched by `L2` rows.",
            "",
            f"- single residuals = `{payload['single_with_planes_generator_residuals']}`",
            f"- double residuals = `{payload['double_with_planes_generator_residuals']}`",
            "",
            "## Classification",
            "",
            f"- primary = `{payload['classification']['primary']}`",
            f"- secondary = `{payload['classification']['secondary']}`",
            f"- ruled out = `{payload['classification']['not_supported_by_evidence']}`",
            f"- verdict: {payload['classification']['verdict']}",
        ]
    )
    return "\n".join(lines)


def build_phase_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 Phase And Subduction Audit v1",
        "",
        "## Source-Level Evidence",
        "",
    ]
    for key, item in payload["source_code_evidence"].items():
        lines.append(f"- `{key}` -> `{item['file']}:{item['line']}`")
    lines.extend(
        [
            "",
            "## L2 Phase Evidence",
            "",
            "The current `linear_character` is not the same object as `character`; `common/SSGReps.py` multiplies the raw character by `exp(-i k·tauC)`.",
            "",
            f"- single L2 phase relation = `{payload['phase_relation_examples']['single_L2']}`",
            f"- single P3 phase relation = `{payload['phase_relation_examples']['single_P3']}`",
            f"- single P4 phase relation = `{payload['phase_relation_examples']['single_P4']}`",
            f"- double L2 phase relation = `{payload['phase_relation_examples']['double_L2']}`",
            "",
            "## Subduction Test On The Implicated Sector",
            "",
            "For `L2 <- {P3,P4}`, the current raw-character subduction succeeds, but the same solve becomes inconsistent once the full `linear_character` is used.",
            "",
            f"- single raw-character subduction = `{payload['subduction_tests']['single_L2_using_character']}`",
            f"- single linear-character subduction = `{payload['subduction_tests']['single_L2_using_linear_character']}`",
            f"- double raw-character subduction = `{payload['subduction_tests']['double_L2_using_character']}`",
            f"- double linear-character subduction = `{payload['subduction_tests']['double_L2_using_linear_character']}`",
            "",
            "## Verdict",
            "",
            f"- compatibility uses phase-stripped character = `{payload['verdict']['compatibility_builder_uses_phase_stripped_character']}`",
            f"- induction uses linear character with Bloch phase = `{payload['verdict']['induction_builder_uses_full_linear_character_with_bloch_phase']}`",
            f"- little-co-group vs full-little-group mismatch = `{payload['verdict']['little_co_group_vs_full_little_group_mismatch_present']}`",
            f"- most likely effect: {payload['verdict']['most_likely_effect']}",
        ]
    )
    return "\n".join(lines)


def build_fix_plan(gap: dict[str, Any], phase: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 Upstream Raw BS Fix Plan v1",
            "",
            "## Diagnosis",
            "",
            "- The raw `Z^3` does not come from the final standard projection layer. It is already present upstream because the current P3/P4 sector is only constrained by the three `L2` equations.",
            "- Those `L2` equations are built in `build_line_block()` from the phase-stripped `character` object, while `induce_candidate()` later uses `linear_character` together with an explicit Bloch phase factor.",
            "- No plane row touches `P3/P4`, so the K/H sector never receives a second-stage gluing constraint inside the current raw builder.",
            "",
            "## Most Likely Repair Direction",
            "",
            "1. Split the compatibility builder into two explicit modes: a raw co-group audit mode and a full phase-aware little-group subduction mode.",
            "2. For the phase-aware mode, stop treating `character` as the authoritative restriction object on nonsymmorphic lines/planes. Use `linear_character` or an equivalent projective/little-group object with a common phase convention.",
            "3. Rework `build_line_block()` and `build_plane_block()` so the endpoint-to-line and point-to-plane solve is done in the same phase convention that `induce_candidate()` uses later.",
            "4. Start with the `L2 <- {P3,P4}` sector only. It is the unique place where the three common free directions live.",
            "5. After the `L2` sector is phase-aware, rerun the raw BS analysis and check whether `rank_bs_raw_internal` drops from `16` to `13` before any external standard projection is applied.",
            "",
            "## Why This Is Not A Small Patch",
            "",
            "- The current raw-character compatibility solve is intentionally integral. Switching to a phase-aware solve changes the object being restricted, not just a coefficient or endpoint lookup.",
            "- The present `linear_character` solve on `L2` is inconsistent under the old integer-only rule, so a direct `character -> linear_character` text swap is not sufficient.",
            "",
            "## Minimal Success Metric",
            "",
            "- Recompute the raw upstream stage without the external standard projection contract.",
            "- Success means: raw `rank(BS)` becomes `13`, raw `quotient_group` becomes finite/trivial as appropriate, and the three current `common_free_generators` disappear from the upstream quotient extraction.",
            "",
            "## Current References",
            "",
            f"- gap audit: `{RAW_GAP_AUDIT_JSON.name}`",
            f"- phase audit: `{PHASE_AUDIT_JSON.name}`",
            f"- stage1 compatibility builder: `sg194/debug_workflow_portability_194.1.1.1.py`",
            f"- phase formula source: `common/SSGReps.py`",
        ]
    )


def main() -> None:
    gap = gap_payload()
    phase = phase_payload()
    write_json(RAW_GAP_AUDIT_JSON, gap)
    write_text(RAW_GAP_AUDIT_MD, build_gap_markdown(gap))
    write_json(PHASE_AUDIT_JSON, phase)
    write_text(PHASE_AUDIT_MD, build_phase_markdown(phase))
    write_text(FIX_PLAN_MD, build_fix_plan(gap, phase))
    print(f"wrote {RAW_GAP_AUDIT_JSON.name}, {PHASE_AUDIT_JSON.name}, and {FIX_PLAN_MD.name}")


if __name__ == "__main__":
    main()
