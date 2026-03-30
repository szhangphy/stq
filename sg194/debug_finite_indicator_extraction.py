#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
from collections import Counter
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent

REPORT_PDF = ROOT / "finite_indicator_extraction_report.pdf"
REPORT_TEX = ROOT / "finite_indicator_extraction_report.tex"
AUDIT_MD = ROOT / "finite_indicator_extraction_audit.md"
SUMMARY_JSON = ROOT / "finite_indicator_extraction_summary.json"
CLASSIFICATION_JSON = ROOT / "quotient_generator_classification.json"
HANDOFF_MD = ROOT / "handoff_finite_indicator_extraction.md"
CURRENT_STATUS_JSON = ROOT / "current_status_finite_indicator_extraction.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_finite_indicator_extraction.txt"
SCRIPT_PATH = ROOT / "debug_finite_indicator_extraction.py"

REINTERPRET_10_DOUBLE_MD = ROOT / "reinterpretation_10_4_1_31_double_finite_part.md"
REINTERPRET_10_DOUBLE_JSON = ROOT / "reinterpretation_10_4_1_31_double_finite_part.json"
REINTERPRET_194_SINGLE_MD = ROOT / "reinterpretation_194_1_1_1_single_finite_part.md"
REINTERPRET_194_SINGLE_JSON = ROOT / "reinterpretation_194_1_1_1_single_finite_part.json"
REINTERPRET_194_DOUBLE_MD = ROOT / "reinterpretation_194_1_1_1_double_finite_part.md"
REINTERPRET_194_DOUBLE_JSON = ROOT / "reinterpretation_194_1_1_1_double_finite_part.json"

PACKAGE_NAME = "review_package_finite_indicator_extraction"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

RESEARCH_RESULTS_TSV = ROOT / "research-results-finite-indicator.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-finite-indicator.json"

VERIFY_CMD = "python3 -u debug_finite_indicator_extraction.py --validate"
GUARD_CMD = "python3 -u debug_raw_matrix_audit.py --validate"

CASE_SPECS: dict[str, dict[str, Any]] = {
    "10_4_1_31_single": {
        "group": "10.4.1.31",
        "group_type": 1,
        "raw_quotient": ROOT / "raw_10_4_1_31_single_quotient.json",
        "raw_ai_in_bs": ROOT / "raw_10_4_1_31_single_ai_in_bs_matrix.json",
        "raw_bs_basis": ROOT / "raw_10_4_1_31_single_bs_basis_raw.json",
        "indicator_generators": ROOT / "single_group_indicator_generators.json",
        "indicator_group_summary": ROOT / "single_group_indicator_group_summary.json",
        "existing_reinterpretation": ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json",
        "raw_quotient_expected": "Z2 x Z2",
        "finite_part_candidate": "Z2 x Z2",
        "finite_part_confidence": "high",
        "still_missing_step": "none within the current raw/SNF formalism",
        "user_facing_interpretation": "This case is already purely torsion at the raw quotient level, so the finite symmetry-indicator candidate is the same Z2 x Z2.",
        "primary_note": "No free abelian sector is present; the raw quotient already matches the finite indicator candidate.",
    },
    "10_4_1_31_double": {
        "group": "10.4.1.31",
        "group_type": 2,
        "raw_quotient": ROOT / "raw_10_4_1_31_double_quotient.json",
        "raw_ai_in_bs": ROOT / "raw_10_4_1_31_double_ai_in_bs_matrix.json",
        "raw_bs_basis": ROOT / "raw_10_4_1_31_double_bs_basis_raw.json",
        "indicator_generators": ROOT / "double_group_indicator_generators_10.4.1.31.json",
        "indicator_group_summary": ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
        "existing_reinterpretation": ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json",
        "raw_quotient_expected": "Z^2 x Z2 x Z2 x Z2 x Z2",
        "finite_part_candidate": "Z2 x Z2 x Z2 x Z2",
        "finite_part_confidence": "high",
        "still_missing_step": "Only reporting-layer cleanup remains: reserve indicator language for the torsion subgroup and report Z^2 separately as free crystalline invariants.",
        "user_facing_interpretation": "Report the full raw quotient as Z^2 x Z2^4, but call only the exact torsion subgroup Z2^4 the finite symmetry-indicator candidate.",
        "primary_note": "The Smith decomposition canonically splits the raw quotient into free rank 2 and four order-2 torsion slots.",
    },
    "194_1_1_1_single": {
        "group": "194.1.1.1",
        "group_type": 1,
        "raw_quotient": ROOT / "raw_194_1_1_1_single_quotient.json",
        "raw_ai_in_bs": ROOT / "raw_194_1_1_1_single_ai_in_bs_matrix.json",
        "raw_bs_basis": ROOT / "raw_194_1_1_1_single_bs_basis_raw.json",
        "indicator_generators": ROOT / "group_194_1_1_1_single_indicator_generators.json",
        "indicator_group_summary": ROOT / "group_194_1_1_1_single_indicator_group_summary.json",
        "existing_reinterpretation": ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json",
        "raw_quotient_expected": "Z^16",
        "finite_part_candidate": "trivial",
        "finite_part_confidence": "medium",
        "still_missing_step": "A physically justified quotient that mods out the free crystalline subgroup before comparison to standard finite symmetry-indicator tables.",
        "user_facing_interpretation": "The current result is a free-only raw quotient Z^16. In standard finite-indicator language no nontrivial finite torsion sector has been isolated.",
        "primary_note": "The torsion subgroup of coker(AI->BS) is empty. Any further reduction must come from a physical mod-out of free crystalline invariants, not from missed SNF torsion.",
    },
    "194_1_1_1_double": {
        "group": "194.1.1.1",
        "group_type": 2,
        "raw_quotient": ROOT / "raw_194_1_1_1_double_quotient.json",
        "raw_ai_in_bs": ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json",
        "raw_bs_basis": ROOT / "raw_194_1_1_1_double_bs_basis_raw.json",
        "indicator_generators": ROOT / "group_194_1_1_1_double_indicator_generators.json",
        "indicator_group_summary": ROOT / "group_194_1_1_1_double_indicator_group_summary.json",
        "existing_reinterpretation": ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json",
        "raw_quotient_expected": "Z^16",
        "finite_part_candidate": "trivial",
        "finite_part_confidence": "medium",
        "still_missing_step": "A physically justified quotient that removes the 16 free crystalline directions before any comparison to a standard finite double-group indicator table.",
        "user_facing_interpretation": "The current result is again a free-only raw quotient Z^16. The finite symmetry-indicator candidate is trivial unless an additional physical quotient produces residual torsion.",
        "primary_note": "The raw Smith data still show no torsion. The gap is interpretive and physical, not a missing order-2 factor in the current integer linear algebra.",
    },
}

REQUIRED_OUTPUTS = [
    AUDIT_MD,
    SUMMARY_JSON,
    REINTERPRET_10_DOUBLE_MD,
    REINTERPRET_10_DOUBLE_JSON,
    REINTERPRET_194_SINGLE_MD,
    REINTERPRET_194_SINGLE_JSON,
    REINTERPRET_194_DOUBLE_MD,
    REINTERPRET_194_DOUBLE_JSON,
    CLASSIFICATION_JSON,
    HANDOFF_MD,
    CURRENT_STATUS_JSON,
    NEXT_STEP_PROMPT_TXT,
    SCRIPT_PATH,
    REPORT_PDF,
    REPORT_TEX,
    PACKAGE_TARBALL,
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def matrix_from_rows(rows: list[list[int]]) -> sp.Matrix:
    return sp.Matrix([[int(value) for value in row] for row in rows])


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    pieces: list[str] = []
    if free_rank > 0:
        pieces.append("Z" if free_rank == 1 else f"Z^{free_rank}")
    pieces.extend(f"Z{value}" for value in finite_part)
    return " x ".join(pieces) if pieces else "trivial"


def latex_group_string(group: str) -> str:
    if group == "trivial":
        return r"\mathrm{trivial}"
    pieces = []
    for token in group.split(" x "):
        if token.startswith("Z^"):
            pieces.append(rf"\mathrm{{Z}}^{{{token[2:]}}}")
        elif token.startswith("Z") and token[1:].isdigit():
            pieces.append(rf"\mathrm{{Z}}_{{{token[1:]}}}")
        else:
            pieces.append(token)
    return r" \times ".join(pieces)


def latex_escape_text(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "^": r"\textasciicircum{}",
    }
    escaped = text
    for old, new in replacements.items():
        escaped = escaped.replace(old, new)
    return escaped


def support_from_generator(generator: dict[str, Any]) -> list[dict[str, Any]]:
    support = generator.get("support")
    if support:
        return [
            {"unknown": item["unknown"], "coeff": int(item["coeff"])}
            for item in support
        ]
    ordering = generator["unknown_ordering"]
    vector = generator["unknown_vector"]
    return [
        {"unknown": unknown, "coeff": int(coeff)}
        for unknown, coeff in zip(ordering, vector)
        if int(coeff) != 0
    ]


def support_summary(support: list[dict[str, Any]]) -> dict[str, Any]:
    manifolds = Counter()
    sector_families = Counter()
    coeff_l1 = 0
    for item in support:
        manifold = item["unknown"].split("_")[0]
        family = manifold[0]
        manifolds[manifold] += 1
        sector_families[family] += 1
        coeff_l1 += abs(int(item["coeff"]))
    return {
        "support_size": len(support),
        "l1_norm": coeff_l1,
        "manifold_counts": dict(sorted(manifolds.items())),
        "sector_family_counts": dict(sorted(sector_families.items())),
    }


def classify_free_generator(case_key: str, summary: dict[str, Any]) -> tuple[str, str]:
    families = set(summary["sector_family_counts"])
    manifolds = set(summary["manifold_counts"])
    if not families:
        return "unresolved free direction", "Support is empty in the exported vector; keep it as an unclassified free crystalline direction."
    if families == {"P"}:
        if len(manifolds) <= 2:
            return (
                "ordinary Chern-like / point-sector balance",
                "Support lies only in point-like P sectors and is concentrated on a small number of point manifolds, so the direction looks like a point-sector imbalance that behaves like a Chern-style free invariant.",
            )
        return (
            "multi-point crystalline free invariant",
            "Support lies only in point-like P sectors but spans several point manifolds, so this looks like a free crystalline balance direction rather than a finite indicator.",
        )
    if families <= {"B", "S"}:
        return (
            "plane-resolved crystalline free invariant",
            "Support lives only on B/S manifolds, so the direction is naturally interpreted as a plane- or boundary-resolved free crystalline invariant rather than a finite symmetry indicator.",
        )
    if "P" in families and ({"B", "S"} & families):
        return (
            "mixed point-plane crystalline free invariant",
            "Support mixes point and B/S manifolds, so the direction looks like a free crystalline invariant tied to compatibility between point data and plane-resolved sectors.",
        )
    return (
        "other free crystalline invariant",
        "The support pattern does not match a simpler point-only or plane-only template, so keep it as a generic free crystalline invariant direction.",
    )


def classify_torsion_generator(summary: dict[str, Any], order: int) -> tuple[str, str]:
    families = set(summary["sector_family_counts"])
    if families == {"P"}:
        support_hint = "The support sits only on point-like manifolds."
    elif families <= {"B", "S"}:
        support_hint = "The support sits only on B/S manifolds."
    else:
        support_hint = "The support mixes point and B/S manifolds."
    return (
        "finite symmetry-indicator generator",
        f"Exact Smith order {order} torsion slot. {support_hint} In the current formalism this is the canonical finite-indicator candidate sector.",
    )


def recompute_from_ai_in_bs(case_key: str, matrix_rows: list[list[int]]) -> dict[str, Any]:
    matrix = matrix_from_rows(matrix_rows)
    D, U, V = smith_normal_decomp(matrix, domain=ZZ)
    diagonal: list[int] = []
    for idx in range(min(D.rows, D.cols)):
        value = abs(int(D[idx, idx]))
        if value != 0:
            diagonal.append(value)
    rank = len(diagonal)
    free_rank = int(matrix.rows - rank)
    finite_part = [value for value in diagonal if value > 1]
    return {
        "case_key": case_key,
        "rank_ai_in_bs": rank,
        "free_rank": free_rank,
        "finite_part": finite_part,
        "raw_quotient": quotient_group_string(free_rank, finite_part),
        "smith_diagonal_nonzero": diagonal,
        "smith_diagonal_matrix": [[int(D[r, c]) for c in range(D.cols)] for r in range(D.rows)],
        "smith_left": [[int(U[r, c]) for c in range(U.cols)] for r in range(U.rows)],
        "smith_right": [[int(V[r, c]) for c in range(V.cols)] for r in range(V.rows)],
    }


def group_string_from_finite_part(finite_part: list[int]) -> str:
    return quotient_group_string(0, finite_part)


def build_case_summary(case_key: str, raw_quotient_payload: dict[str, Any], recomputed: dict[str, Any]) -> dict[str, Any]:
    spec = CASE_SPECS[case_key]
    raw_quotient = raw_quotient_payload["raw_quotient"]
    free_rank = int(raw_quotient_payload["free_rank"])
    finite_part = [int(value) for value in raw_quotient_payload["finite_part"]]
    if raw_quotient != recomputed["raw_quotient"]:
        raise ValueError(f"{case_key}: raw quotient mismatch between stored payload and exact recompute")
    if free_rank != recomputed["free_rank"]:
        raise ValueError(f"{case_key}: free-rank mismatch between stored payload and exact recompute")
    if finite_part != recomputed["finite_part"]:
        raise ValueError(f"{case_key}: finite-part mismatch between stored payload and exact recompute")

    free_part = "trivial" if free_rank == 0 else ("Z" if free_rank == 1 else f"Z^{free_rank}")
    if finite_part:
        finite_candidate = group_string_from_finite_part(finite_part)
    else:
        finite_candidate = spec["finite_part_candidate"]

    free_mod_out_result = "trivial" if not finite_part else group_string_from_finite_part(finite_part)
    if case_key.startswith("194_"):
        gap = "The raw quotient is free-only, so the standard finite-indicator layer is not directly visible before modding out free crystalline directions."
    elif case_key == "10_4_1_31_double":
        gap = "The raw quotient mixes a free Z^2 sector with the finite torsion subgroup Z2^4; only the latter should be called the finite symmetry-indicator candidate."
    else:
        gap = "No gap: the raw quotient is already purely finite."

    return {
        "group": spec["group"],
        "group_type": spec["group_type"],
        "case_key": case_key,
        "raw_quotient": raw_quotient,
        "free_part": free_part,
        "finite_part_candidate": finite_candidate,
        "finite_part_confidence": spec["finite_part_confidence"],
        "still_missing_step": spec["still_missing_step"],
        "user_facing_interpretation": spec["user_facing_interpretation"],
        "free_rank": free_rank,
        "finite_part": finite_part,
        "free_mod_out_candidate_rank": free_rank,
        "result_after_modding_out_free_part": free_mod_out_result,
        "raw_vs_interpreted_gap": gap,
        "primary_note": spec["primary_note"],
        "exact_smith_diagonal_nonzero": recomputed["smith_diagonal_nonzero"],
    }


def build_generator_classification(case_key: str, raw_quotient_payload: dict[str, Any], bs_basis_payload: dict[str, Any]) -> list[dict[str, Any]]:
    spec = CASE_SPECS[case_key]
    basis_count = len(bs_basis_payload["basis_vectors"])
    entries: list[dict[str, Any]] = []

    for generator in raw_quotient_payload.get("free_generators", []):
        support = support_from_generator(generator)
        summary = support_summary(support)
        physical_type, notes = classify_free_generator(case_key, summary)
        coords = [int(value) for value in generator["bs_basis_coordinates"]]
        if len(coords) != basis_count:
            raise ValueError(f"{case_key}: free generator basis coordinate length mismatch")
        entries.append(
            {
                "generator_id": generator["generator_id"],
                "case_key": case_key,
                "group": spec["group"],
                "group_type": spec["group_type"],
                "sector": "free",
                "order": None,
                "bs_basis_coordinates": coords,
                "unknown_vector": [int(value) for value in generator["unknown_vector"]],
                "support": support,
                "support_summary": summary,
                "tentative_physical_type": physical_type,
                "notes": notes,
            }
        )

    for generator in raw_quotient_payload.get("torsion_generators", []):
        support = support_from_generator(generator)
        summary = support_summary(support)
        order = int(generator["smith_factor"])
        physical_type, notes = classify_torsion_generator(summary, order)
        coords = [int(value) for value in generator["bs_basis_coordinates"]]
        if len(coords) != basis_count:
            raise ValueError(f"{case_key}: torsion generator basis coordinate length mismatch")
        entries.append(
            {
                "generator_id": generator["generator_id"],
                "case_key": case_key,
                "group": spec["group"],
                "group_type": spec["group_type"],
                "sector": "torsion",
                "order": order,
                "bs_basis_coordinates": coords,
                "unknown_vector": [int(value) for value in generator["unknown_vector"]],
                "support": support,
                "support_summary": summary,
                "tentative_physical_type": physical_type,
                "notes": notes,
            }
        )
    return entries


def build_case_markdown_block(item: dict[str, Any]) -> list[str]:
    return [
        f"### {item['group']} / groupType={item['group_type']}",
        "",
        f"- Raw quotient: `{item['raw_quotient']}`.",
        f"- Free crystalline invariant part: `{item['free_part']}`.",
        f"- Finite symmetry-indicator candidate: `{item['finite_part_candidate']}`.",
        f"- Confidence: `{item['finite_part_confidence']}`.",
        f"- Still missing step: {item['still_missing_step']}",
        f"- User-facing interpretation: {item['user_facing_interpretation']}",
        f"- Exact Smith diagonal (nonzero entries): `{item['exact_smith_diagonal_nonzero']}`.",
        "",
    ]


def build_audit_markdown(case_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Finite Indicator Extraction Audit",
        "",
        "## Why Raw Quotients Are Not Final Indicator Groups",
        "",
        "- The raw quotient is the exact integer cokernel `coker(AI -> BS)`.",
        "- Standard symmetry-indicator language is reserved for the finite torsion sector, not for any free abelian crystalline directions that remain in the raw quotient.",
        "- Therefore `Z^n` or `Z^m x finite torsion` cannot be reported to users as a final finite symmetry-indicator group without a clean free/torsion split.",
        "",
        "## Four-Case Summary",
        "",
        "| case | raw quotient | free part | finite indicator candidate | confidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in case_summaries:
        lines.append(
            f"| `{item['group']}` / `{item['group_type']}` | `{item['raw_quotient']}` | `{item['free_part']}` | `{item['finite_part_candidate']}` | `{item['finite_part_confidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Case Notes",
            "",
        ]
    )
    for item in case_summaries:
        lines.extend(build_case_markdown_block(item))
    lines.extend(
        [
            "## Stabilized User-Facing Language",
            "",
            "- `10.4.1.31 / single`: the raw quotient is already finite, so `Z2 x Z2` remains the finite symmetry-indicator candidate.",
            "- `10.4.1.31 / double`: the raw quotient is `Z^2 x Z2^4`, but only `Z2^4` is the finite symmetry-indicator candidate; the `Z^2` sector must be reported separately as free crystalline invariants.",
            "- `194.1.1.1 / single`: the raw quotient is `Z^16`; no finite torsion is present, so the current finite symmetry-indicator candidate is trivial unless a later physical quotient leaves residual torsion.",
            "- `194.1.1.1 / double`: same correction as the single case; do not call `Z^16` a finite indicator group.",
        ]
    )
    return "\n".join(lines)


def build_reinterpretation_md(item: dict[str, Any]) -> str:
    lines = [
        f"# Reinterpretation: {item['group']} / groupType={item['group_type']}",
        "",
        f"- Raw quotient: `{item['raw_quotient']}`.",
        f"- Free part: `{item['free_part']}`.",
        f"- Finite torsion extracted directly from exact Smith audit: `{group_string_from_finite_part(item['finite_part']) if item['finite_part'] else 'trivial'}`.",
        f"- Finite symmetry-indicator candidate: `{item['finite_part_candidate']}`.",
        f"- Confidence: `{item['finite_part_confidence']}`.",
        f"- Result after modding out the full free subgroup candidate: `{item['result_after_modding_out_free_part']}`.",
        "",
        "## Interpretation",
        "",
        item["primary_note"],
        "",
        "## User-Facing Language",
        "",
        item["user_facing_interpretation"],
        "",
        "## Still Missing Step",
        "",
        item["still_missing_step"],
    ]
    return "\n".join(lines)


def build_generator_classification_payload(case_summaries: list[dict[str, Any]], entries: list[dict[str, Any]]) -> dict[str, Any]:
    per_case: dict[str, dict[str, Any]] = {}
    for item in case_summaries:
        case_entries = [entry for entry in entries if entry["case_key"] == item["case_key"]]
        per_case[item["case_key"]] = {
            "group": item["group"],
            "group_type": item["group_type"],
            "free_generator_count": sum(1 for entry in case_entries if entry["sector"] == "free"),
            "torsion_generator_count": sum(1 for entry in case_entries if entry["sector"] == "torsion"),
            "raw_quotient": item["raw_quotient"],
        }
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": per_case,
        "entries": entries,
    }


def build_handoff(case_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Handoff: Finite Indicator Extraction",
        "",
        "## Current Stage",
        "",
        "- The free/torsion reinterpretation layer has been generated for the four fixed cases.",
        "- This stage does not modify BS or AI. It only consumes the existing raw matrix-level artifacts and rewrites the quotient layer into free crystalline invariants plus finite symmetry-indicator candidates.",
        "",
        "## Per-Case Result",
        "",
    ]
    for item in case_summaries:
        lines.append(
            f"- `{item['group']}` / `{item['group_type']}`: raw quotient `{item['raw_quotient']}`, free part `{item['free_part']}`, finite indicator candidate `{item['finite_part_candidate']}`."
        )
    lines.extend(
        [
            "",
            "## Current Blockers",
            "",
            "- `10.4.1.31 / double`: no algebraic blocker remains; only terminology cleanup remains.",
            "- `194.1.1.1 / single,double`: the remaining gap is not missing SNF torsion. It is the lack of an agreed physical quotient beyond the raw `coker(AI -> BS)` layer.",
            "",
            "## Files To Read First",
            "",
            "1. `finite_indicator_extraction_report.pdf`",
            "2. `finite_indicator_extraction_audit.md`",
            "3. `finite_indicator_extraction_summary.json`",
            "4. `quotient_generator_classification.json`",
            "5. `reinterpretation_194_1_1_1_single_finite_part.md` and `reinterpretation_194_1_1_1_double_finite_part.md`",
        ]
    )
    return "\n".join(lines)


def build_current_status(case_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage": "finite_indicator_extraction",
        "verify_command": VERIFY_CMD,
        "guard_command": GUARD_CMD,
        "report_pdf": REPORT_PDF.name,
        "report_source": REPORT_TEX.name,
        "package_tarball": PACKAGE_TARBALL.name,
        "cases": case_summaries,
        "next_step": "If a later review wants stricter physical alignment for SG 194, benchmark the free-only raw quotient against a standard finite indicator table after defining the extra physical mod-out.",
    }


def build_next_step_prompt(case_summaries: list[dict[str, Any]]) -> str:
    case_lines = "\n".join(
        f"- {item['group']} / groupType={item['group_type']}: raw quotient {item['raw_quotient']}, free part {item['free_part']}, finite candidate {item['finite_part_candidate']}"
        for item in case_summaries
    )
    return textwrap.dedent(
        f"""
        上一个会话已经完成 finite-indicator extraction。不要扩群，不要重做 BS / AI / portability。当前固定四个 case 的分层结论是：

        {case_lines}

        优先读取：
        1. finite_indicator_extraction_report.pdf
        2. finite_indicator_extraction_audit.md
        3. finite_indicator_extraction_summary.json
        4. quotient_generator_classification.json
        5. reinterpretation_10_4_1_31_double_finite_part.md
        6. reinterpretation_194_1_1_1_single_finite_part.md
        7. reinterpretation_194_1_1_1_double_finite_part.md

        当前这一轮的目标已经完成。下一轮如果还要继续，只能做更高层的物理对表或外部表格基准，不要回头重算 raw quotient。

        验证当前工件完整性：
        `python3 -u debug_finite_indicator_extraction.py --validate`

        守护 raw 基线：
        `python3 -u debug_raw_matrix_audit.py --validate`
        """
    ).strip() + "\n"


def build_package_readme(case_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Finite Indicator Extraction Package",
        "",
        "## Scope",
        "",
        "- Fixed groups only: `10.4.1.31` and `194.1.1.1`.",
        "- Fixed cases only: single-group and double-group on those two groups.",
        "- This stage does not regenerate BS or AI. It only reinterprets the exported raw quotients as free crystalline invariants plus finite symmetry-indicator candidates.",
        "",
        "## Four-Case Summary",
        "",
    ]
    for item in case_summaries:
        lines.append(
            f"- `{item['group']}` / `{item['group_type']}`: raw quotient `{item['raw_quotient']}`, free part `{item['free_part']}`, finite indicator candidate `{item['finite_part_candidate']}`."
        )
    lines.extend(
        [
            "",
            "## Finite-indicator extraction report",
            "",
            f"- Report file: `{REPORT_PDF.name}`",
            f"- Report source: `{REPORT_TEX.name}`",
            "- Suggested reading order: first the PDF report, then `finite_indicator_extraction_summary.json`, then `quotient_generator_classification.json`, then the case-specific reinterpretation files, and finally the raw quotient JSON files.",
        ]
    )
    return "\n".join(lines)


def build_report_tex(case_summaries: list[dict[str, Any]]) -> str:
    table_rows = "\n".join(
        rf"{item['group']} / {item['group_type']} & ${latex_group_string(item['raw_quotient'])}$ & ${latex_group_string(item['free_part'])}$ & ${latex_group_string(item['finite_part_candidate'])}$ & {latex_escape_text(item['finite_part_confidence'])} \\"
        for item in case_summaries
    )
    detail_blocks = "\n".join(
        textwrap.dedent(
            rf"""
            \subsection*{{{item['group']} / groupType={item['group_type']}}}
            The exact raw quotient is ${latex_group_string(item['raw_quotient'])}$.
            Its free crystalline part is ${latex_group_string(item['free_part'])}$ and the current finite symmetry-indicator candidate is ${latex_group_string(item['finite_part_candidate'])}$.
            The relevant Smith diagonal entries are {latex_escape_text(str(item['exact_smith_diagonal_nonzero']))}.
            The primary note for this case is:
            \begin{{quote}}
            {latex_escape_text(item['primary_note'])}
            \end{{quote}}
            The user-facing wording should be:
            \begin{{quote}}
            {latex_escape_text(item['user_facing_interpretation'])}
            \end{{quote}}
            """
        ).strip()
        for item in case_summaries
    )
    generated_date = datetime.now().strftime("%Y-%m-%d")
    return textwrap.dedent(
        rf"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{amsmath,amssymb,booktabs,longtable}}
        \usepackage[T1]{{fontenc}}
        \usepackage[utf8]{{inputenc}}
        \usepackage{{hyperref}}
        \hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}

        \title{{Finite-Indicator Extraction from Raw Quotients}}
        \author{{Codex finite-indicator audit}}
        \date{{{generated_date}}}

        \begin{{document}}
        \maketitle

        \section{{Task Background and Problem Statement}}
        This stage starts from the already exported raw matrix-level artifacts.  It does not regenerate
        $BS$, $AI$, or the raw cokernel $\mathrm{{coker}}(AI \to BS)$.  Instead, it reinterprets the raw quotient
        into two layers:
        \[
          \mathrm{{coker}}(AI \to BS) \cong \mathbb{{Z}}^r \times T,
        \]
        where $\mathbb{{Z}}^r$ is the free crystalline-invariant sector and $T$ is the finite torsion sector.
        Standard symmetry-indicator language is reserved for the finite abelian part $T$.

        \section{{Raw Quotient vs Finite Indicator}}
        If the raw quotient contains a free part, then it cannot be reported directly as a final finite symmetry-indicator group.
        The free sector must be reported separately as free crystalline invariants, while the finite torsion sector is the natural finite-indicator candidate.

        \section{{Four-Case Raw Quotient Review}}
        \begin{{center}}
        \begin{{tabular}}{{lllll}}
        \toprule
        Case & Raw quotient & Free part & Finite candidate & Confidence \\
        \midrule
        {table_rows}
        \bottomrule
        \end{{tabular}}
        \end{{center}}

        \section{{Free-Generator Classification}}
        The generator classification file records every raw quotient generator together with its exact BS-basis coordinates,
        support in the unknown ordering, and a tentative morphology-based type label.  These labels are intentionally cautious:
        they identify point-sector balance directions, plane-resolved directions, or mixed point-plane directions without claiming a final topological name unless the support pattern is very simple.

        \section{{10.4.1.31 Double: Finite-Part Extraction}}
        For \texttt{{10.4.1.31}} in the double-group case, the exact Smith decomposition gives
        \[
          \mathrm{{coker}}(AI \to BS) \cong \mathbb{{Z}}^2 \times (\mathbb{{Z}}_2)^4.
        \]
        The free $\mathbb{{Z}}^2$ sector must be reported as free crystalline invariants.
        The exact torsion subgroup $(\mathbb{{Z}}_2)^4$ is the finite symmetry-indicator candidate, because it is the canonical torsion subgroup extracted by the exact Smith normal form.

        \section{{194.1.1.1 Single/Double: Why They Still Read as \texttt{{Z\textasciicircum{{}}16}}}}
        For both the single-group and double-group cases on \texttt{{194.1.1.1}}, the exact Smith decomposition gives
        \[
          \mathrm{{coker}}(AI \to BS) \cong \mathbb{{Z}}^{{16}}.
        \]
        No finite torsion is present in the current raw quotient.  Therefore the current finite symmetry-indicator candidate is trivial at the purely algebraic torsion level.
        Any nontrivial finite indicator would require an additional physically justified quotient that removes the 16 free crystalline directions and then leaves residual torsion.  That extra physical reduction is not encoded in the present raw linear-algebra layer.

        \section{{User-Facing Language Correction}}
        The corrected user-facing rule is:
        \begin{{itemize}}
        \item report the full raw quotient as the exact algebraic cokernel;
        \item report the free abelian part separately as free crystalline invariants;
        \item reserve ``finite symmetry-indicator part'' for the torsion subgroup only.
        \end{{itemize}}

        \section{{Case Details}}
        {detail_blocks}

        \section{{Implementation Mapping}}
        The main implementation artifact is \texttt{{debug\_finite\_indicator\_extraction.py}}.
        It reads the exported raw quotient JSON files, the exact AI-in-BS matrix JSON files,
        and the raw BS-basis JSON files produced by the earlier raw-matrix audit.
        It then emits:
        \begin{{itemize}}
        \item \texttt{{finite\_indicator\_extraction\_summary.json}} for the case-level free/torsion split,
        \item \texttt{{quotient\_generator\_classification.json}} for generator-level classification,
        \item three case-specific reinterpretation files for the nontrivial reinterpretation targets,
        \item this PDF report and its \LaTeX{{}} source,
        \item a review package tarball.
        \end{{itemize}}

        \section{{Current Missing Step and Next Advice}}
        The remaining open issue is not a missing Smith decomposition.  It is the physical reduction from the raw quotient to a standard finite symmetry-indicator layer in cases such as \texttt{{194.1.1.1}}, where the raw quotient is free-only.  The next review step, if needed, is to define and justify that additional physical quotient.

        \end{{document}}
        """
    ).strip() + "\n"


def compile_report() -> None:
    tex_name = REPORT_TEX.name
    for _ in range(2):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_name],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )


def build_package(case_summaries: list[dict[str, Any]]) -> None:
    ensure_clean_dir(PACKAGE_DIR)
    write_text(README_PATH, build_package_readme(case_summaries))

    new_files = [
        AUDIT_MD,
        SUMMARY_JSON,
        REINTERPRET_10_DOUBLE_MD,
        REINTERPRET_10_DOUBLE_JSON,
        REINTERPRET_194_SINGLE_MD,
        REINTERPRET_194_SINGLE_JSON,
        REINTERPRET_194_DOUBLE_MD,
        REINTERPRET_194_DOUBLE_JSON,
        CLASSIFICATION_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        SCRIPT_PATH,
        REPORT_PDF,
        REPORT_TEX,
    ]
    background = [
        ROOT / "raw_matrix_level_audit_summary.json",
        ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json",
        ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json",
        ROOT / "two_group_correctness_summary.json",
        ROOT / "audit_10_4_1_31_correctness.json",
        ROOT / "audit_194_1_1_1_correctness.json",
        ROOT / "single_group_indicator_group_summary.json",
        ROOT / "single_group_indicator_generators.json",
        ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
        ROOT / "double_group_indicator_generators_10.4.1.31.json",
        ROOT / "group_194_1_1_1_single_indicator_group_summary.json",
        ROOT / "group_194_1_1_1_single_indicator_generators.json",
        ROOT / "group_194_1_1_1_double_indicator_group_summary.json",
        ROOT / "group_194_1_1_1_double_indicator_generators.json",
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]
    raw_files = sorted(ROOT.glob("raw_*.json"))

    for path in new_files + background + raw_files:
        if not path.exists():
            raise FileNotFoundError(path)
        rel = path.relative_to(ROOT)
        dest = PACKAGE_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def write_outputs(case_summaries: list[dict[str, Any]], classification_payload: dict[str, Any]) -> None:
    write_json(SUMMARY_JSON, {"cases": case_summaries})
    write_json(CLASSIFICATION_JSON, classification_payload)
    write_text(AUDIT_MD, build_audit_markdown(case_summaries))
    write_text(REINTERPRET_10_DOUBLE_MD, build_reinterpretation_md(next(item for item in case_summaries if item["case_key"] == "10_4_1_31_double")))
    write_json(REINTERPRET_10_DOUBLE_JSON, next(item for item in case_summaries if item["case_key"] == "10_4_1_31_double"))
    write_text(REINTERPRET_194_SINGLE_MD, build_reinterpretation_md(next(item for item in case_summaries if item["case_key"] == "194_1_1_1_single")))
    write_json(REINTERPRET_194_SINGLE_JSON, next(item for item in case_summaries if item["case_key"] == "194_1_1_1_single"))
    write_text(REINTERPRET_194_DOUBLE_MD, build_reinterpretation_md(next(item for item in case_summaries if item["case_key"] == "194_1_1_1_double")))
    write_json(REINTERPRET_194_DOUBLE_JSON, next(item for item in case_summaries if item["case_key"] == "194_1_1_1_double"))
    write_text(HANDOFF_MD, build_handoff(case_summaries))
    write_json(CURRENT_STATUS_JSON, build_current_status(case_summaries))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt(case_summaries))
    write_text(REPORT_TEX, build_report_tex(case_summaries))
    compile_report()
    build_package(case_summaries)


def build_all() -> None:
    case_summaries: list[dict[str, Any]] = []
    all_entries: list[dict[str, Any]] = []
    for case_key, spec in CASE_SPECS.items():
        raw_quotient_payload = load_json(spec["raw_quotient"])
        ai_in_bs_payload = load_json(spec["raw_ai_in_bs"])
        bs_basis_payload = load_json(spec["raw_bs_basis"])
        recomputed = recompute_from_ai_in_bs(case_key, ai_in_bs_payload["matrix"])
        case_summary = build_case_summary(case_key, raw_quotient_payload, recomputed)
        case_summaries.append(case_summary)
        all_entries.extend(build_generator_classification(case_key, raw_quotient_payload, bs_basis_payload))

    classification_payload = build_generator_classification_payload(case_summaries, all_entries)
    write_outputs(case_summaries, classification_payload)


def validate() -> None:
    missing = [path.name for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        raise SystemExit(f"missing outputs: {missing}")

    summary = load_json(SUMMARY_JSON)
    if "cases" not in summary or len(summary["cases"]) != 4:
        raise SystemExit("summary does not contain four cases")

    classification = load_json(CLASSIFICATION_JSON)
    if "entries" not in classification:
        raise SystemExit("classification payload missing entries")

    summary_by_case = {item["case_key"]: item for item in summary["cases"]}
    entry_counts = Counter(entry["case_key"] for entry in classification["entries"])
    for case_key, spec in CASE_SPECS.items():
        item = summary_by_case.get(case_key)
        if item is None:
            raise SystemExit(f"summary missing case {case_key}")
        raw_quotient_payload = load_json(spec["raw_quotient"])
        ai_in_bs_payload = load_json(spec["raw_ai_in_bs"])
        recomputed = recompute_from_ai_in_bs(case_key, ai_in_bs_payload["matrix"])
        if item["raw_quotient"] != raw_quotient_payload["raw_quotient"]:
            raise SystemExit(f"{case_key}: summary/raw quotient mismatch")
        if item["raw_quotient"] != recomputed["raw_quotient"]:
            raise SystemExit(f"{case_key}: recomputed/raw quotient mismatch")
        expected_generator_count = len(raw_quotient_payload.get("free_generators", [])) + len(raw_quotient_payload.get("torsion_generators", []))
        if entry_counts[case_key] != expected_generator_count:
            raise SystemExit(f"{case_key}: classification count mismatch")

    if not PACKAGE_TARBALL.exists():
        raise SystemExit("package tarball missing")

    required_tar_members = {
        f"{PACKAGE_NAME}/finite_indicator_extraction_audit.md",
        f"{PACKAGE_NAME}/finite_indicator_extraction_summary.json",
        f"{PACKAGE_NAME}/quotient_generator_classification.json",
        f"{PACKAGE_NAME}/debug_finite_indicator_extraction.py",
        f"{PACKAGE_NAME}/finite_indicator_extraction_report.pdf",
        f"{PACKAGE_NAME}/finite_indicator_extraction_report.tex",
    }
    with tarfile.open(PACKAGE_TARBALL, "r:gz") as tar:
        names = set(tar.getnames())
    missing_members = sorted(required_tar_members - names)
    if missing_members:
        raise SystemExit(f"package missing members: {missing_members}")

    print("validated finite-indicator extraction outputs")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    if args.validate:
        validate()
        return

    build_all()


if __name__ == "__main__":
    main()
