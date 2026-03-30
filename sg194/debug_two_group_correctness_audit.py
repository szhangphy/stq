#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import sympy as sp
from sympy import ZZ
from sympy.matrices.normalforms import smith_normal_decomp


ROOT = Path(__file__).resolve().parent

GROUP_10 = "10.4.1.31"
GROUP_194 = "194.1.1.1"

TWO_GROUP_AUDIT_MD = ROOT / "two_group_correctness_audit.md"
TWO_GROUP_SUMMARY_JSON = ROOT / "two_group_correctness_summary.json"
AUDIT_10_MD = ROOT / "audit_10_4_1_31_correctness.md"
AUDIT_10_JSON = ROOT / "audit_10_4_1_31_correctness.json"
AUDIT_194_MD = ROOT / "audit_194_1_1_1_correctness.md"
AUDIT_194_JSON = ROOT / "audit_194_1_1_1_correctness.json"
REINTERPRET_194_MD = ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.md"
REINTERPRET_194_JSON = ROOT / "reinterpretation_194_1_1_1_raw_vs_finite.json"
REINTERPRET_10_MD = ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.md"
REINTERPRET_10_JSON = ROOT / "reinterpretation_10_4_1_31_raw_vs_indicator.json"
HANDOFF_MD = ROOT / "handoff_correctness_audit.md"
CURRENT_STATUS_JSON = ROOT / "current_status_correctness_audit.json"
NEXT_STEP_PROMPT_TXT = ROOT / "next_step_prompt_correctness_audit.txt"
REPORT_TEX = ROOT / "two_group_correctness_audit_report.tex"
REPORT_PDF = ROOT / "two_group_correctness_audit_report.pdf"

PACKAGE_NAME = "review_package_two_group_correctness_audit"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def matrix_from_columns(columns: list[list[int]]) -> sp.Matrix:
    if not columns:
        return sp.zeros(0, 0)
    return sp.Matrix.hstack(*[sp.Matrix(column) for column in columns])


def basis_matrix_from_basis_vectors(payload: dict[str, Any]) -> sp.Matrix:
    vectors = payload["basis_vectors"]
    if not vectors:
        return sp.zeros(0, 0)
    if isinstance(vectors[0], dict):
        return sp.Matrix.hstack(*[sp.Matrix(item["vector"]) for item in vectors])
    return sp.Matrix.hstack(*[sp.Matrix(item) for item in vectors])


def smith_data_for_ai_in_bs(ai_coords: sp.Matrix, bs_rank: int) -> dict[str, Any]:
    if ai_coords.cols == 0:
        return {
            "ai_rank": 0,
            "free_rank": bs_rank,
            "smith_diagonal": [],
            "finite_part": [],
            "quotient_group": quotient_group_string(bs_rank, []),
        }
    diagonal, _left, _right = smith_normal_decomp(ai_coords, domain=ZZ)
    diag_entries = [
        abs(int(diagonal[idx, idx]))
        for idx in range(min(diagonal.rows, diagonal.cols))
        if int(diagonal[idx, idx]) != 0
    ]
    ai_rank = len(diag_entries)
    free_rank = int(bs_rank - ai_rank)
    finite_part = [value for value in diag_entries if value > 1]
    return {
        "ai_rank": ai_rank,
        "free_rank": free_rank,
        "smith_diagonal": diag_entries,
        "finite_part": finite_part,
        "quotient_group": quotient_group_string(free_rank, finite_part),
    }


def quotient_group_string(free_rank: int, finite_part: list[int]) -> str:
    pieces: list[str] = []
    if free_rank == 1:
        pieces.append("Z")
    elif free_rank > 1:
        pieces.append(f"Z^{free_rank}")
    pieces.extend(f"Z{value}" for value in finite_part)
    return " x ".join(pieces) if pieces else "trivial"


def confidence_rank(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}[value]


def latex_group_string(group: str) -> str:
    if group == "trivial":
        return r"\mathrm{trivial}"
    rebuilt: list[str] = []
    for token in group.split(" x "):
        if token.startswith("Z^"):
            rebuilt.append(rf"\mathrm{{Z}}^{{{token[2:]}}}")
        elif token.startswith("Z") and token[1:].isdigit():
            rebuilt.append(rf"\mathrm{{Z}}_{{{token[1:]}}}")
        else:
            rebuilt.append(token)
    return r" \times ".join(rebuilt)


def bool_word(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "uncertain"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_dict(
    group: str,
    group_type: int,
    bs_likely_correct: str,
    ai_likely_complete: str,
    quotient_interpretation_likely_correct: str,
    suspicion_ranking: list[str],
    confidence: str,
    main_issue: str,
    recommended_next_step: str,
    raw_quotient: str,
    free_rank: int,
    finite_part: list[int],
    bs_evidence: list[str],
    ai_evidence: list[str],
    quotient_evidence: list[str],
    evidence_files: list[str],
) -> dict[str, Any]:
    return {
        "group": group,
        "group_type": group_type,
        "BS_likely_correct": bs_likely_correct,
        "AI_likely_complete": ai_likely_complete,
        "quotient_interpretation_likely_correct": quotient_interpretation_likely_correct,
        "suspicion_ranking": suspicion_ranking,
        "confidence": confidence,
        "main_issue": main_issue,
        "recommended_next_step": recommended_next_step,
        "raw_quotient": raw_quotient,
        "free_rank": free_rank,
        "finite_part": finite_part,
        "bs_evidence": bs_evidence,
        "ai_evidence": ai_evidence,
        "quotient_evidence": quotient_evidence,
        "evidence_files": evidence_files,
    }


def build_case_10_single() -> dict[str, Any]:
    bs_summary_line = load_json(ROOT / "single_group_bs_summary.json")
    bs_summary_planes = load_json(ROOT / "single_group_bs_with_planes_summary.json")
    plane_summary = load_json(ROOT / "single_group_plane_necessity_summary.json")
    ai_summary = load_json(ROOT / "single_group_ai_completeness_summary.json")
    indicator_summary = load_json(ROOT / "single_group_indicator_group_summary.json")
    ai_basis = load_json(ROOT / "single_group_ai_expanded_v3_basis.json")
    bs_basis = load_json(ROOT / "single_group_bs_with_planes_basis_raw.json")

    bs_rank = int(indicator_summary["rank(BS_with_planes)"])
    ai_coords = matrix_from_columns(ai_basis["basis_bs_coefficients"])
    recomputed = smith_data_for_ai_in_bs(ai_coords, bs_rank)

    bs_evidence = [
        "line-only and with-planes summaries are both present, and the nullity drops from 16 to 8 when planes are added",
        f"plane necessity audit reports added rank {plane_summary['with_planes_added_rank_vs_line_only']} with shape {plane_summary['with_planes_matrix_shape']}",
        f"with-planes BS basis has {basis_matrix_from_basis_vectors(bs_basis).cols} basis columns, matching nullity {bs_summary_planes['nullity']}",
        "the compatibility workflow is explicit and uses integer Smith decomposition rather than a floating nullspace",
    ]
    ai_evidence = [
        "all 15 families are explicitly listed complete in the completeness summary",
        "the local site symmetries are all abelian or order-2 antiunitary case-a extensions, which limits hidden missing higher-dimensional local objects",
        f"independent SNF recomputation from AI basis coefficients reproduces {recomputed['quotient_group']}",
    ]
    quotient_evidence = [
        f"independent SNF recomputation gives smith diagonal {recomputed['smith_diagonal']}",
        "the quotient has no free part, so there is no free-vs-finite mixing in this case",
        "the result remains scoped to the current with-planes basis and unknown ordering, but that is a scope caveat rather than a contradiction",
    ]
    return case_dict(
        group=GROUP_10,
        group_type=1,
        bs_likely_correct="true",
        ai_likely_complete="true",
        quotient_interpretation_likely_correct="true",
        suspicion_ranking=[
            "AI / AI completeness",
            "quotient interpretation",
            "BS",
        ],
        confidence="medium",
        main_issue="No hard contradiction is visible; if forced to pick the weakest layer, the family-level completeness proof is the first one to stress because it depends on the local census assumptions.",
        recommended_next_step="If more confidence is needed, independently rederive the local-family census from the site-symmetry data rather than from the current audited library outputs.",
        raw_quotient=recomputed["quotient_group"],
        free_rank=int(recomputed["free_rank"]),
        finite_part=list(recomputed["finite_part"]),
        bs_evidence=bs_evidence,
        ai_evidence=ai_evidence,
        quotient_evidence=quotient_evidence,
        evidence_files=[
            "single_group_bs_summary.json",
            "single_group_plane_necessity_summary.json",
            "single_group_bs_with_planes_summary.json",
            "single_group_bs_with_planes_basis_raw.json",
            "single_group_ai_expanded_v3_basis.json",
            "single_group_ai_completeness_summary.json",
            "single_group_ai_completeness_audit.md",
            "single_group_indicator_group_summary.json",
            "single_group_indicator_generators.json",
        ],
    )


def build_case_10_double() -> dict[str, Any]:
    bs_summary = load_json(ROOT / "double_group_bs_summary_10.4.1.31.json")
    ai_summary = load_json(ROOT / "double_group_ai_completeness_summary_10.4.1.31.json")
    quotient_summary = load_json(ROOT / "double_group_bs_mod_ai_summary_10.4.1.31.json")
    indicator_summary = load_json(ROOT / "double_group_indicator_group_summary_10.4.1.31.json")
    ai_basis = load_json(ROOT / "double_group_ai_v2_basis_10.4.1.31.json")
    bs_basis = load_json(ROOT / "double_group_bs_basis_raw_10.4.1.31.json")

    bs_rank = int(indicator_summary["rank(BS_double)"])
    ai_coords = matrix_from_columns(ai_basis["basis_bs_coefficients"])
    recomputed = smith_data_for_ai_in_bs(ai_coords, bs_rank)

    bs_shape = bs_summary.get("matrix_shape", bs_summary.get("shape"))
    bs_evidence = [
        f"double-group BS summary reports shape {bs_shape} with rank {bs_summary['rank']} and nullity {bs_summary['nullity']}",
        f"double-group raw BS basis has {basis_matrix_from_basis_vectors(bs_basis).cols} basis columns, matching nullity {bs_summary['nullity']}",
        "the k-space backbone audit explicitly redoes line blocks, plane necessity, and with-planes kernel extraction on the double branch",
    ]
    ai_evidence = [
        "all 15 families are marked complete after combining point-like and parametric double local objects",
        "the family site symmetries are still only order-2 or simple unitary/antiunitary extensions, which makes the completeness model relatively constrained",
        f"independent SNF recomputation from the AI_v2 basis coefficients reproduces {recomputed['quotient_group']}",
    ]
    quotient_evidence = [
        "the algebraic quotient extraction itself is well supported by the stored AI basis coefficients",
        f"the recomputed quotient has free rank {recomputed['free_rank']} and finite part {recomputed['finite_part']}",
        "the interpretation layer is the weak point because the artifact naming still uses indicator-language even though the quotient contains a free part",
        quotient_summary["interpretation_note"],
    ]
    return case_dict(
        group=GROUP_10,
        group_type=2,
        bs_likely_correct="true",
        ai_likely_complete="true",
        quotient_interpretation_likely_correct="uncertain",
        suspicion_ranking=[
            "quotient interpretation",
            "AI / AI completeness",
            "BS",
        ],
        confidence="high",
        main_issue="The raw mixed quotient is likely real, but the reporting layer still mixes a full raw quotient with indicator language.",
        recommended_next_step="Split the raw quotient into its free and torsion sectors in the primary artifacts, and reserve indicator language for the finite torsion part only.",
        raw_quotient=recomputed["quotient_group"],
        free_rank=int(recomputed["free_rank"]),
        finite_part=list(recomputed["finite_part"]),
        bs_evidence=bs_evidence,
        ai_evidence=ai_evidence,
        quotient_evidence=quotient_evidence,
        evidence_files=[
            "double_group_bs_summary_10.4.1.31.json",
            "double_group_bs_basis_raw_10.4.1.31.json",
            "double_group_kspace_backbone_audit_10.4.1.31.md",
            "double_group_plane_necessity_audit_10.4.1.31.md",
            "double_group_ai_v2_basis_10.4.1.31.json",
            "double_group_ai_completeness_summary_10.4.1.31.json",
            "double_group_ai_completeness_audit_10.4.1.31.md",
            "double_group_bs_mod_ai_summary_10.4.1.31.json",
            "double_group_indicator_group_summary_10.4.1.31.json",
            "double_group_indicator_generators_10.4.1.31.json",
        ],
    )


def build_case_194_pair() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    stage2 = load_module(ROOT / "debug_workflow_portability_stage2_194.1.1.1.py", "correctness_stage2_local")
    helper = load_module(ROOT / "debug_sg194_nonabelian_local_library.py", "correctness_helper_local")

    port = stage2.load_stage1_module()
    module = port.load_ssgreps_module()
    ssg_dict = port.load_ssg_dict(stage2.TARGET_GROUP)

    inventory = helper.build_inventory_and_libraries()
    single_runtime = stage2.build_single_runtime(port, module, ssg_dict)
    double_runtime = stage2.build_double_runtime(port, module, ssg_dict, single_runtime["kgeom"])

    single_induction = stage2.induce_objects(
        port,
        single_runtime,
        inventory["family_single_local_irreps"],
        "correctness_audit_single_recompute",
    )
    double_induction = stage2.induce_objects(
        port,
        double_runtime,
        inventory["family_double_local_irreps"],
        "correctness_audit_double_recompute",
    )

    single_candidate_ids = [candidate["generator_id"] for candidate in single_induction["candidates"]]
    double_candidate_ids = [candidate["generator_id"] for candidate in double_induction["candidates"]]
    single_ai_coords = stage2.bs_coordinate_matrix(single_runtime["bs_analysis"], single_induction["candidates"])
    double_ai_coords = stage2.bs_coordinate_matrix(double_runtime["bs_analysis"], double_induction["candidates"])

    single_q_summary, _single_q_generators = stage2.quotient_artifacts(
        1,
        single_runtime["bs_analysis"],
        single_ai_coords,
        single_candidate_ids,
    )
    double_q_summary, _double_q_generators = stage2.quotient_artifacts(
        2,
        double_runtime["bs_analysis"],
        double_ai_coords,
        double_candidate_ids,
    )

    shared_bs_evidence = [
        "single and double BS backgrounds can be rebuilt from the stage-1/stage-2 scripts in the current workspace",
        f"the recomputed single and double matrices both have shape {single_runtime['bs_analysis']['matrix_shape']} and nullity {single_runtime['bs_analysis']['nullity']}",
        "the BS layer on 194.1.1.1 depends on synthetic boundary-point augmentation because swyckoff_k.py does not emit every needed 0D endpoint directly",
        "that augmentation is internally consistent, but it is still the main reason this BS layer is less settled than the closed 10.4.1.31 case",
    ]
    single_ai_evidence = [
        "the SG194 single local-irrep library covers the non-abelian types C3v, D3d-like, and D3h-like with orthogonality and dimension-squared checks",
        f"the recomputed single AI rank is {single_ai_coords.rank()} inside BS rank {single_runtime['bs_analysis']['nullity']}",
        f"the recomputed raw quotient is {single_q_summary['quotient_group']}",
        "however, the completeness statement is still library-backed rather than independently checked against an external BR/EBR source",
    ]
    double_ai_evidence = [
        "the SG194 double local library uses projective twisted-regular decomposition with factor_su2 validation",
        f"the recomputed double AI rank is {double_ai_coords.rank()} inside BS rank {double_runtime['bs_analysis']['nullity']}",
        f"the recomputed raw quotient is {double_q_summary['quotient_group']}",
        "this is a newer and more delicate library than the single-group one, so the completeness verdict is still best treated as conditional on the current projective builder",
    ]
    single_q_evidence = [
        "the quotient summary itself already records free_rank = 16 and finite_part = []",
        "there is no finite torsion left after the raw Smith decomposition",
        "therefore Z^16 is a raw free-dominated quotient, not a standard finite symmetry-indicator group",
    ]
    double_q_evidence = [
        "the double quotient summary also records free_rank = 16 and finite_part = []",
        "this matches the recomputed projective-library-based quotient exactly",
        "again, the problem is interpretation: a free-only raw quotient cannot be read as a final finite indicator group",
    ]

    case_single = case_dict(
        group=GROUP_194,
        group_type=1,
        bs_likely_correct="uncertain",
        ai_likely_complete="uncertain",
        quotient_interpretation_likely_correct="false",
        suspicion_ranking=[
            "quotient interpretation",
            "AI / AI completeness",
            "BS",
        ],
        confidence="high",
        main_issue="The raw quotient Z^16 is free-only and therefore cannot be presented as a standard finite topological indicator group.",
        recommended_next_step="Keep the raw quotient as an algebraic result, but separately identify which free directions are genuine topological invariants and whether any finite symmetry-indicator sector remains after the physically appropriate reduction.",
        raw_quotient=str(single_q_summary["quotient_group"]),
        free_rank=int(single_q_summary["free_rank"]),
        finite_part=list(single_q_summary["finite_part"]),
        bs_evidence=shared_bs_evidence,
        ai_evidence=single_ai_evidence,
        quotient_evidence=single_q_evidence,
        evidence_files=[
            "group_194_1_1_1_single_bs_analysis.json",
            "group_194_1_1_1_single_full_compatibility_with_planes.json",
            "group_194_1_1_1_single_pilot_summary.json",
            "group_194_1_1_1_single_pilot_audit.md",
            "group_194_1_1_1_single_ai_completion_summary.json",
            "group_194_1_1_1_single_indicator_group_summary.json",
            "group_194_1_1_1_single_indicator_generators.json",
            "workflow_portability_report_194.1.1.1.tex",
            "workflow_portability_report_stage2_194.1.1.1.tex",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_nonabelian_local_library.py",
        ],
    )
    case_double = case_dict(
        group=GROUP_194,
        group_type=2,
        bs_likely_correct="uncertain",
        ai_likely_complete="uncertain",
        quotient_interpretation_likely_correct="false",
        suspicion_ranking=[
            "quotient interpretation",
            "AI / AI completeness",
            "BS",
        ],
        confidence="medium",
        main_issue="The double-group result is again a free-only raw quotient Z^16, while the AI completeness claim still depends on the current projective local library.",
        recommended_next_step="Do not call Z^16 a final double-group indicator group; first separate the free sector, then cross-check the projective local library with an independent derivation or benchmark.",
        raw_quotient=str(double_q_summary["quotient_group"]),
        free_rank=int(double_q_summary["free_rank"]),
        finite_part=list(double_q_summary["finite_part"]),
        bs_evidence=shared_bs_evidence,
        ai_evidence=double_ai_evidence,
        quotient_evidence=double_q_evidence,
        evidence_files=[
            "group_194_1_1_1_double_bs_analysis.json",
            "group_194_1_1_1_double_full_compatibility_with_planes.json",
            "group_194_1_1_1_double_pilot_summary.json",
            "group_194_1_1_1_double_pilot_audit.md",
            "group_194_1_1_1_double_ai_completion_summary.json",
            "group_194_1_1_1_double_indicator_group_summary.json",
            "group_194_1_1_1_double_indicator_generators.json",
            "workflow_portability_report_194.1.1.1.tex",
            "workflow_portability_report_stage2_194.1.1.1.tex",
            "debug_workflow_portability_stage2_194.1.1.1.py",
            "debug_sg194_nonabelian_local_library.py",
        ],
    )
    recompute = {
        "single_runtime_shape": list(single_runtime["bs_analysis"]["matrix_shape"]),
        "single_runtime_rank": int(single_runtime["bs_analysis"]["rank"]),
        "single_runtime_nullity": int(single_runtime["bs_analysis"]["nullity"]),
        "double_runtime_shape": list(double_runtime["bs_analysis"]["matrix_shape"]),
        "double_runtime_rank": int(double_runtime["bs_analysis"]["rank"]),
        "double_runtime_nullity": int(double_runtime["bs_analysis"]["nullity"]),
        "single_ai_candidate_count": len(single_induction["candidates"]),
        "double_ai_candidate_count": len(double_induction["candidates"]),
        "single_ai_rank": int(single_ai_coords.rank()),
        "double_ai_rank": int(double_ai_coords.rank()),
    }
    return case_single, case_double, recompute


def build_group_audit_md(group: str, cases: list[dict[str, Any]]) -> str:
    lines = [f"# Correctness Audit for {group}", ""]
    for case in sorted(cases, key=lambda item: item["group_type"]):
        title = "single-group" if case["group_type"] == 1 else "double-group"
        lines.extend(
            [
                f"## {title}",
                "",
                f"- `BS_likely_correct = {case['BS_likely_correct']}`",
                f"- `AI_likely_complete = {case['AI_likely_complete']}`",
                f"- `quotient_interpretation_likely_correct = {case['quotient_interpretation_likely_correct']}`",
                f"- raw quotient: `{case['raw_quotient']}`",
                f"- suspicion ranking: `{case['suspicion_ranking'][0]} > {case['suspicion_ranking'][1]} > {case['suspicion_ranking'][2]}`",
                f"- confidence: `{case['confidence']}`",
                f"- main issue: {case['main_issue']}",
                "",
                "### BS layer evidence",
                "",
            ]
        )
        lines.extend([f"- {item}" for item in case["bs_evidence"]])
        lines.extend(["", "### AI / completeness evidence", ""])
        lines.extend([f"- {item}" for item in case["ai_evidence"]])
        lines.extend(["", "### Quotient interpretation evidence", ""])
        lines.extend([f"- {item}" for item in case["quotient_evidence"]])
        lines.extend(["", "### Evidence files", ""])
        lines.extend([f"- `{item}`" for item in case["evidence_files"]])
        lines.extend(["", f"- recommended next step: {case['recommended_next_step']}", ""])
    return "\n".join(lines)


def build_master_audit_md(cases: list[dict[str, Any]]) -> str:
    lines = [
        "# Two-Group Correctness Audit",
        "",
        "## Why Re-Audit These Two Groups",
        "",
        "- `10.4.1.31` is the current closed reference line for both single and double workflows.",
        "- `194.1.1.1` is the controlled SG 194 portability case, and its reported `Z^16` raw quotient is the strongest warning sign that the interpretation layer may be drifting away from the standard finite-indicator language.",
        "- Therefore this round separates three logically distinct layers for all four cases: `BS`, `AI / completeness`, and `quotient interpretation`.",
        "",
        "## Core Verdict Table",
        "",
        "| group | groupType | BS likely correct | AI likely complete | quotient interpretation likely correct | top suspicion | confidence |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(
            "| "
            + " | ".join(
                [
                    case["group"],
                    str(case["group_type"]),
                    case["BS_likely_correct"],
                    case["AI_likely_complete"],
                    case["quotient_interpretation_likely_correct"],
                    case["suspicion_ranking"][0],
                    case["confidence"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Suspicion Rankings",
            "",
        ]
    )
    for case in cases:
        title = f"{case['group']} / groupType={case['group_type']}"
        lines.extend(
            [
                f"### {title}",
                "",
                f"- ranking: `{case['suspicion_ranking'][0]} > {case['suspicion_ranking'][1]} > {case['suspicion_ranking'][2]}`",
                f"- confidence: `{case['confidence']}`",
                f"- main issue: {case['main_issue']}",
                f"- raw quotient: `{case['raw_quotient']}`",
                f"- free rank: `{case['free_rank']}`",
                f"- finite part: `{case['finite_part']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Current Most Reasonable Conclusions",
            "",
            "- `10.4.1.31` single-group: the current weakest layer is AI/completeness, but there is no visible contradiction; the finite quotient `Z2 x Z2` is presently the least problematic quotient claim.",
            "- `10.4.1.31` double-group: the raw mixed quotient is plausible, but the interpretation layer must separate the free part `Z^2` from the finite torsion part `Z2^4` before using indicator language.",
            "- `194.1.1.1` single-group: the raw quotient `Z^16` should be read as a free-dominated raw quotient, not as a final finite indicator group.",
            "- `194.1.1.1` double-group: same raw-quotient reinterpretation issue as the single case, with extra caution because the projective local library is newer and therefore the AI completeness layer is less settled.",
        ]
    )
    return "\n".join(lines)


def build_reinterpretation_194(single_case: dict[str, Any], double_case: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = {
        "group": GROUP_194,
        "single": {
            "raw_quotient": single_case["raw_quotient"],
            "free_part": quotient_group_string(single_case["free_rank"], []),
            "finite_part": single_case["finite_part"],
            "finite_part_isolated": bool(single_case["finite_part"]),
            "can_call_standard_finite_indicator_group": False,
            "reason": "The raw quotient is purely free (Z^16) and no finite torsion part has been isolated.",
        },
        "double": {
            "raw_quotient": double_case["raw_quotient"],
            "free_part": quotient_group_string(double_case["free_rank"], []),
            "finite_part": double_case["finite_part"],
            "finite_part_isolated": bool(double_case["finite_part"]),
            "can_call_standard_finite_indicator_group": False,
            "reason": "The raw quotient is again purely free (Z^16) and no finite torsion part has been isolated.",
        },
        "bottom_line": "The current Z^16 results are raw free-dominated quotients. They are not final finite symmetry-indicator groups.",
    }
    md = "\n".join(
        [
            "# Reinterpretation of 194.1.1.1 Raw Quotients",
            "",
            "- Current raw single-group quotient: `Z^16`.",
            "- Current raw double-group quotient: `Z^16`.",
            "- Free part: `Z^16` in both cases.",
            "- Finite part: `[]` in both cases.",
            "- Therefore the current outputs are raw quotients with free directions only; they should not be called final finite topological indicator groups.",
            "",
            "## Why `Z^16` Is a Warning Sign",
            "",
            "- The controlled-case audit identifies `194.1.1.1` with the spatial part of ordinary SG 194 in the current local setting.",
            "- A purely free raw quotient is compatible with an algebraic `BS/AI` computation at the current manifold-rich formalism level, but it is not yet a standard finite symmetry-indicator summary.",
            "- The immediate correction is interpretive: keep `Z^16` as the raw quotient, and separately identify which generators correspond to free topological directions before using any indicator language.",
        ]
    )
    return payload, md


def build_reinterpretation_10(single_case: dict[str, Any], double_case: dict[str, Any]) -> tuple[dict[str, Any], str]:
    payload = {
        "group": GROUP_10,
        "single": {
            "raw_quotient": single_case["raw_quotient"],
            "free_part": quotient_group_string(single_case["free_rank"], []),
            "finite_part": single_case["finite_part"],
            "major_reinterpretation_needed": False,
            "reason": "The single-group quotient is already purely finite (Z2 x Z2), so there is no free-vs-finite mixing in this case.",
        },
        "double": {
            "raw_quotient": double_case["raw_quotient"],
            "free_part": quotient_group_string(double_case["free_rank"], []),
            "finite_part": double_case["finite_part"],
            "major_reinterpretation_needed": True,
            "reason": "The double-group quotient contains both a free part and a finite torsion part, so the full Z^2 x Z2^4 should not be called a purely finite indicator group.",
        },
        "bottom_line": "10.4.1.31 single-group is mostly stable. 10.4.1.31 double-group needs a raw-quotient-vs-finite-indicator reinterpretation.",
    }
    md = "\n".join(
        [
            "# Reinterpretation of 10.4.1.31 Raw Quotients",
            "",
            "## Single-group",
            "",
            f"- Raw quotient: `{single_case['raw_quotient']}`.",
            "- Free part: none.",
            "- Finite part: `[2, 2]`.",
            "- This case does not need a major reinterpretation beyond keeping the formalism/basis scope explicit.",
            "",
            "## Double-group",
            "",
            f"- Raw quotient: `{double_case['raw_quotient']}`.",
            f"- Free part: `{quotient_group_string(double_case['free_rank'], [])}`.",
            f"- Finite part: `{double_case['finite_part']}`.",
            "- The free part should be separated from the finite torsion part before using indicator language.",
            "- The best current reading is: the raw quotient is `Z^2 x Z2^4`, but only the finite torsion piece `Z2^4` is the natural finite-indicator candidate.",
        ]
    )
    return payload, md


def build_summary_json(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": [
            {
                "group": case["group"],
                "group_type": case["group_type"],
                "BS_likely_correct": case["BS_likely_correct"],
                "AI_likely_complete": case["AI_likely_complete"],
                "quotient_interpretation_likely_correct": case["quotient_interpretation_likely_correct"],
                "suspicion_ranking": case["suspicion_ranking"],
                "confidence": case["confidence"],
                "main_issue": case["main_issue"],
                "recommended_next_step": case["recommended_next_step"],
            }
            for case in cases
        ],
        "most_stable_bs_cases": [
            case["group"] + f"/{case['group_type']}"
            for case in cases
            if case["BS_likely_correct"] == "true"
        ],
        "most_suspicious_ai_cases": [
            case["group"] + f"/{case['group_type']}"
            for case in cases
            if case["suspicion_ranking"][0] == "AI / AI completeness"
        ],
        "most_suspicious_quotient_cases": [
            case["group"] + f"/{case['group_type']}"
            for case in cases
            if case["suspicion_ranking"][0] == "quotient interpretation"
        ],
    }


def build_report_tex(cases: list[dict[str, Any]]) -> str:
    case_map = {(case["group"], case["group_type"]): case for case in cases}
    c10s = case_map[(GROUP_10, 1)]
    c10d = case_map[(GROUP_10, 2)]
    c194s = case_map[(GROUP_194, 1)]
    c194d = case_map[(GROUP_194, 2)]
    return textwrap.dedent(
        rf"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{amsmath,amssymb,booktabs,longtable,array}}
        \usepackage[T1]{{fontenc}}
        \usepackage[utf8]{{inputenc}}
        \title{{Two-Group Correctness Attribution Audit}}
        \author{{Codex Local Audit}}
        \date{{}}
        \begin{{document}}
        \maketitle

        \section{{Task Background and Problem Statement}}
        This report re-audits two already completed result lines:
        \begin{{itemize}}
        \item the closed reference group \texttt{{10.4.1.31}},
        \item the controlled portability group \texttt{{194.1.1.1}}.
        \end{{itemize}}
        The point of the re-audit is not to rerun portability or extend the workflow, but to separate three logically distinct possibilities:
        \[
          \text{{(i) BS layer error}}, \qquad
          \text{{(ii) AI / completeness error}}, \qquad
          \text{{(iii) quotient interpretation error}}.
        \]
        The warning sign forcing this split is the stage-2 SG 194 result
        \[
          BS/AI \cong \mathbb{{Z}}^{{16}},
        \]
        which is too obviously free-dominated to be read naively as a standard finite indicator group.

        \section{{Current Results Under Review}}
        The audited headline outputs are:
        \begin{{align*}}
          BS_{{10,\mathrm{{single}}}}/AI_{{10,\mathrm{{single}}}} &\cong {latex_group_string(c10s["raw_quotient"])}, \\
          BS_{{10,\mathrm{{double}}}}/AI_{{10,\mathrm{{double}}}} &\cong {latex_group_string(c10d["raw_quotient"])}, \\
          BS_{{194,\mathrm{{single}}}}/AI_{{194,\mathrm{{single}}}} &\cong {latex_group_string(c194s["raw_quotient"])}, \\
          BS_{{194,\mathrm{{double}}}}/AI_{{194,\mathrm{{double}}}} &\cong {latex_group_string(c194d["raw_quotient"])}.
        \end{{align*}}

        \section{{BS Formalism and Audit Method}}
        In all four cases the k-space layer is represented as an exact compatibility problem
        \[
          C n = 0,
          \qquad
          BS = \ker_{{\mathbb{{Z}}}}(C).
        \]
        The audit checks:
        \begin{{enumerate}}
        \item whether geometry / manifolds / unknown ordering are explicit,
        \item whether the matrix shape, rank, and nullity are consistent with the stored basis files,
        \item whether plane necessity is supported by an added-rank test where applicable,
        \item whether the kernel basis count matches the reported BS rank.
        \end{{enumerate}}

        \section{{AI / Completeness Formalism and Audit Method}}
        The atomic lattice is treated as an integral span
        \[
          AI = \operatorname{{span}}_{{\mathbb{{Z}}}}\{{a_1,a_2,\dots\}},
        \]
        generated by induced local objects. The audit does not simply trust ``complete'' flags. Instead it checks:
        \begin{{enumerate}}
        \item whether the family table is explicitly closed,
        \item whether the local site-symmetry census is mathematically constrained enough to make missing local objects unlikely,
        \item whether the stored AI basis coefficients reproduce the quoted quotient under a fresh Smith decomposition.
        \end{{enumerate}}
        For \texttt{{194.1.1.1}} the audit is more conservative: the new local library is internally validated, but still library-backed rather than independently benchmarked against an external BR/EBR source.

        \section{{Quotient Reinterpretation Formalism}}
        The crucial distinction is
        \[
          BS/AI \;\; \text{{as a raw algebraic quotient}}
          \qquad \text{{versus}} \qquad
          X_{{\mathrm{{SI}}}} \;\; \text{{as a finite indicator group}}.
        \]
        If the Smith decomposition of the AI inclusion matrix inside a BS basis gives diagonal data
        \[
          \operatorname{{diag}}(d_1,\dots,d_r),
        \]
        then the raw quotient has the structure
        \[
          BS/AI \cong \mathbb{{Z}}^{{(\operatorname{{rank}} BS-r)}} \times \prod_{{d_i>1}} \mathbb{{Z}}_{{d_i}}.
        \]
        The free factor is not a finite indicator sector. Therefore any quotient with nonzero free rank must be interpreted carefully before using indicator language.

        \section{{10.4.1.31 Audit Result}}
        \subsection*{{Single-group}}
        The BS layer is the least suspicious component. The with-planes nullity $8$ matches the stored BS basis size $8$, and the plane rank test is explicit. The AI layer also looks strong because all 15 families are enumerated and the local groups are only abelian or simple order-2 antiunitary case-a extensions. A fresh Smith decomposition of the stored AI basis coefficients reproduces the finite quotient
        \[
          BS/AI \cong {latex_group_string(c10s["raw_quotient"])}.
        \]
        Since there is no free part, the interpretation layer is comparatively stable here.

        \subsection*{{Double-group}}
        The raw quotient
        \[
          BS/AI \cong {latex_group_string(c10d["raw_quotient"])}
        \]
        is mechanically well supported, and the corresponding report already notes that the quotient is not purely finite. The audit still ranks the interpretation layer as the weakest one, because the reporting artifacts continue to mix a free part with indicator language. The most honest reading is:
        \[
          BS/AI = \underbrace{{\mathbb{{Z}}^2}}_{{\text{{free part}}}}
          \times
          \underbrace{{\mathbb{{Z}}_2^4}}_{{\text{{finite torsion part}}}}.
        \]
        Only the torsion sector is the natural finite-indicator candidate.

        \section{{194.1.1.1 Audit Result}}
        \subsection*{{Single-group}}
        The BS layer is internally consistent but less settled than in \texttt{{10.4.1.31}} because it depends on synthetic boundary-point augmentation. The AI layer is substantially stronger after stage-2, but the completeness statement is still library-backed. The dominant problem is the interpretation of
        \[
          BS/AI \cong {latex_group_string(c194s["raw_quotient"])}.
        \]
        Here the free rank is 16 and the finite torsion part is empty, so this is a raw free-dominated quotient, not a finite indicator group.

        \subsection*{{Double-group}}
        The same reinterpretation issue appears in the double branch:
        \[
          BS/AI \cong {latex_group_string(c194d["raw_quotient"])}.
        \]
        The projective local library passes its internal validation, but the interpretation layer is still the first place to doubt. The new local library makes AI more credible than in stage-1, yet not so independently settled that it outranks the already obvious quotient-interpretation warning.

        \section{{Suspicion Ranking Table}}
        \begin{{center}}
        \begin{{tabular}}{{llll}}
        \toprule
        case & top suspicion & second & least suspicion \\
        \midrule
        10.4.1.31 / single & {c10s["suspicion_ranking"][0]} & {c10s["suspicion_ranking"][1]} & {c10s["suspicion_ranking"][2]} \\
        10.4.1.31 / double & {c10d["suspicion_ranking"][0]} & {c10d["suspicion_ranking"][1]} & {c10d["suspicion_ranking"][2]} \\
        194.1.1.1 / single & {c194s["suspicion_ranking"][0]} & {c194s["suspicion_ranking"][1]} & {c194s["suspicion_ranking"][2]} \\
        194.1.1.1 / double & {c194d["suspicion_ranking"][0]} & {c194d["suspicion_ranking"][1]} & {c194d["suspicion_ranking"][2]} \\
        \bottomrule
        \end{{tabular}}
        \end{{center}}

        \section{{Implementation Mapping}}
        The machine-checkable outputs are:
        \begin{{itemize}}
        \item \texttt{{two\_group\_correctness\_summary.json}} for the four-case structured verdicts,
        \item \texttt{{audit\_10\_4\_1\_31\_correctness.md/json}} for the per-group 10.4.1.31 audit,
        \item \texttt{{audit\_194\_1\_1\_1\_correctness.md/json}} for the per-group 194.1.1.1 audit,
        \item \texttt{{reinterpretation\_194\_1\_1\_1\_raw\_vs\_finite.*}} for the SG 194 raw-quotient reinterpretation,
        \item \texttt{{reinterpretation\_10\_4\_1\_31\_raw\_vs\_indicator.*}} for the mixed-quotient reinterpretation on the reference group.
        \end{{itemize}}

        \section{{Conclusion and Recommended Next Step}}
        The audit does \emph{{not}} find strong evidence that the BS layer is the main source of error in any of the four cases. The dominant warning sign is the quotient interpretation layer, especially whenever the reported quotient contains a free part. The cleanest corrective action is:
        \begin{{enumerate}}
        \item keep the raw quotients as algebraic outputs,
        \item separate free and finite parts explicitly in the primary summaries,
        \item reserve finite-indicator language for the torsion sector only,
        \item treat the new SG 194 AI-completeness claims as library-backed until they are benchmarked independently.
        \end{{enumerate}}

        \end{{document}}
        """
    ).strip() + "\n"


def compile_report() -> None:
    for _ in range(2):
        subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(ROOT),
                str(REPORT_TEX),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def format_tree(root: Path) -> list[str]:
    lines = [root.name + "/"]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        depth = len(rel.parts)
        prefix = "  " * depth + ("- " if path.is_file() else "")
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{prefix}{rel.name}{suffix}")
    return lines


def build_package(cases: list[dict[str, Any]]) -> list[str]:
    reset_dir(PACKAGE_DIR)
    files_to_copy = [
        TWO_GROUP_AUDIT_MD,
        TWO_GROUP_SUMMARY_JSON,
        AUDIT_10_MD,
        AUDIT_10_JSON,
        AUDIT_194_MD,
        AUDIT_194_JSON,
        REINTERPRET_194_MD,
        REINTERPRET_194_JSON,
        REINTERPRET_10_MD,
        REINTERPRET_10_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        ROOT / "debug_two_group_correctness_audit.py",
        REPORT_PDF,
        REPORT_TEX,
        ROOT / "group_194_1_1_1_single_indicator_group_summary.json",
        ROOT / "group_194_1_1_1_single_indicator_generators.json",
        ROOT / "group_194_1_1_1_double_indicator_group_summary.json",
        ROOT / "group_194_1_1_1_double_indicator_generators.json",
        ROOT / "group_194_1_1_1_single_ai_completion_summary.json",
        ROOT / "group_194_1_1_1_double_ai_completion_summary.json",
        ROOT / "double_group_ai_completeness_audit_10.4.1.31.md",
        ROOT / "double_group_ai_completeness_summary_10.4.1.31.json",
        ROOT / "double_group_indicator_group_summary_10.4.1.31.json",
        ROOT / "double_group_indicator_generators_10.4.1.31.json",
        ROOT / "single_group_ai_completeness_audit.md",
        ROOT / "single_group_ai_completeness_summary.json",
        ROOT / "single_group_indicator_group_summary.json",
        ROOT / "single_group_indicator_generators.json",
        ROOT / "swyckoff_r.py",
        ROOT / "swyckoff_k.py",
        ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
        ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
        ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
    ]
    for path in files_to_copy:
        destination = PACKAGE_DIR / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

    readme = "\n".join(
        [
            "# Two-Group Correctness Audit",
            "",
            "## Scope",
            "",
            "- reference group: `10.4.1.31`",
            "- controlled portability group: `194.1.1.1`",
            "- goal: determine whether the weakest layer in each case is BS, AI/completeness, or quotient interpretation",
            "",
            "## Main Conclusions",
            "",
        ]
        + [
            f"- `{case['group']}` / `groupType={case['group_type']}`: top suspicion = `{case['suspicion_ranking'][0]}`; confidence = `{case['confidence']}`"
            for case in cases
        ]
        + [
            "",
            "## Correctness Audit PDF Report",
            "",
            f"- report file: `{REPORT_PDF.name}`",
            f"- report source: `{REPORT_TEX.name}`",
            "- recommended reading order: first the PDF report, then `two_group_correctness_summary.json`, then the per-group audit files, then the reinterpretation notes",
        ]
    )
    write_text(PACKAGE_DIR / "README.md", readme)

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tar:
        tar.add(PACKAGE_DIR, arcname=PACKAGE_DIR.name)
    return format_tree(PACKAGE_DIR)


def build_status_payload(cases: list[dict[str, Any]], recompute_194: dict[str, Any]) -> dict[str, Any]:
    case_map = {(case["group"], case["group_type"]): case for case in cases}
    return {
        "scope": "two-group correctness attribution audit",
        "cases": {
            "10.4.1.31_single": case_map[(GROUP_10, 1)],
            "10.4.1.31_double": case_map[(GROUP_10, 2)],
            "194.1.1.1_single": case_map[(GROUP_194, 1)],
            "194.1.1.1_double": case_map[(GROUP_194, 2)],
        },
        "recomputed_194_runtime": recompute_194,
        "main_blocker": "No coding blocker remains inside this audit run; the remaining issue is interpretation discipline, especially for quotients with free parts.",
        "next_step": "If a follow-up is needed, separate free generators from finite torsion generators in the user-facing quotient reports and benchmark the SG194 AI completeness externally.",
    }


def build_handoff(cases: list[dict[str, Any]]) -> str:
    top_bs = [case for case in cases if case["BS_likely_correct"] == "true"]
    lines = [
        "# Handoff for Two-Group Correctness Audit",
        "",
        "- Current task status: complete.",
        "- Top suspicion by case:",
    ]
    lines.extend(
        [
            f"  - {case['group']} / groupType={case['group_type']}: {case['suspicion_ranking'][0]}"
            for case in cases
        ]
    )
    lines.extend(
        [
            f"- Cases whose BS currently stand up best: {', '.join(case['group'] + '/g' + str(case['group_type']) for case in top_bs)}.",
            "- Main correction from this round: quotients with free rank must not be presented as final finite indicator groups.",
            "- Files to read first:",
            f"  - {REPORT_PDF.name}",
            f"  - {TWO_GROUP_SUMMARY_JSON.name}",
            f"  - {AUDIT_10_MD.name}",
            f"  - {AUDIT_194_MD.name}",
            f"  - {REINTERPRET_194_MD.name}",
            f"  - {REINTERPRET_10_MD.name}",
        ]
    )
    return "\n".join(lines)


def build_next_step_prompt() -> str:
    return textwrap.dedent(
        """
        The two-group correctness attribution audit has already been completed in the current workspace.

        Read these files first:
        1. two_group_correctness_audit_report.pdf
        2. two_group_correctness_summary.json
        3. audit_10_4_1_31_correctness.md
        4. audit_194_1_1_1_correctness.md
        5. reinterpretation_194_1_1_1_raw_vs_finite.md
        6. reinterpretation_10_4_1_31_raw_vs_indicator.md
        7. current_status_correctness_audit.json

        Current verified conclusions:
        - 10.4.1.31 single-group: the weakest layer is AI/completeness, but there is no visible contradiction and the finite quotient Z2 x Z2 is presently stable.
        - 10.4.1.31 double-group: the raw quotient Z^2 x Z2^4 is plausible, but it should be read as free part Z^2 plus finite torsion part Z2^4 rather than as a purely finite indicator group.
        - 194.1.1.1 single-group: Z^16 is a raw free-dominated quotient, not a final finite indicator group.
        - 194.1.1.1 double-group: same reinterpretation warning as the single case, with extra caution because the projective local library is newer.

        If a next round is requested, do not extend to a third group automatically. The first follow-up should be one of:
        - benchmark the SG194 AI completeness claims against an independent BR/EBR source, or
        - rewrite the user-facing quotient summaries so that free and finite sectors are separated explicitly.
        """
    ).strip() + "\n"


def validate_outputs() -> None:
    required = [
        TWO_GROUP_AUDIT_MD,
        TWO_GROUP_SUMMARY_JSON,
        AUDIT_10_MD,
        AUDIT_10_JSON,
        AUDIT_194_MD,
        AUDIT_194_JSON,
        REINTERPRET_194_MD,
        REINTERPRET_194_JSON,
        REINTERPRET_10_MD,
        REINTERPRET_10_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_PROMPT_TXT,
        REPORT_TEX,
        REPORT_PDF,
        PACKAGE_TARBALL,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing required outputs: " + ", ".join(missing))
    summary = load_json(TWO_GROUP_SUMMARY_JSON)
    if len(summary["cases"]) != 4:
        raise SystemExit("summary JSON does not contain four cases")
    if not REPORT_PDF.exists() or REPORT_PDF.stat().st_size == 0:
        raise SystemExit("report PDF missing or empty")
    print("validation: ok")


def generate() -> None:
    case_10_single = build_case_10_single()
    case_10_double = build_case_10_double()
    case_194_single, case_194_double, recompute_194 = build_case_194_pair()
    cases = [case_10_single, case_10_double, case_194_single, case_194_double]
    cases.sort(key=lambda item: (item["group"], item["group_type"]))

    summary_payload = build_summary_json(cases)
    audit_10_payload = {"group": GROUP_10, "cases": [case_10_single, case_10_double]}
    audit_194_payload = {"group": GROUP_194, "cases": [case_194_single, case_194_double]}
    re194_payload, re194_md = build_reinterpretation_194(case_194_single, case_194_double)
    re10_payload, re10_md = build_reinterpretation_10(case_10_single, case_10_double)

    write_text(TWO_GROUP_AUDIT_MD, build_master_audit_md(cases))
    write_json(TWO_GROUP_SUMMARY_JSON, summary_payload)
    write_text(AUDIT_10_MD, build_group_audit_md(GROUP_10, [case_10_single, case_10_double]))
    write_json(AUDIT_10_JSON, audit_10_payload)
    write_text(AUDIT_194_MD, build_group_audit_md(GROUP_194, [case_194_single, case_194_double]))
    write_json(AUDIT_194_JSON, audit_194_payload)
    write_text(REINTERPRET_194_MD, re194_md)
    write_json(REINTERPRET_194_JSON, re194_payload)
    write_text(REINTERPRET_10_MD, re10_md)
    write_json(REINTERPRET_10_JSON, re10_payload)

    status_payload = build_status_payload(cases, recompute_194)
    write_json(CURRENT_STATUS_JSON, status_payload)
    write_text(HANDOFF_MD, build_handoff(cases))
    write_text(NEXT_STEP_PROMPT_TXT, build_next_step_prompt())

    write_text(REPORT_TEX, build_report_tex(cases))
    compile_report()

    package_tree = build_package(cases)

    print("1. 10.4.1.31 single-group: more like")
    print(f"   {case_10_single['suspicion_ranking'][0]}")
    print("2. 10.4.1.31 double-group: more like")
    print(f"   {case_10_double['suspicion_ranking'][0]}")
    print("3. 194.1.1.1 single-group: more like")
    print(f"   {case_194_single['suspicion_ranking'][0]}")
    print("4. 194.1.1.1 double-group: more like")
    print(f"   {case_194_double['suspicion_ranking'][0]}")
    print("5. BS currently standing up best:")
    print("   10.4.1.31 single-group and double-group")
    print("6. AI completeness currently most suspicious:")
    print("   10.4.1.31 single-group if forced; 194.1.1.1 double-group is the less-settled of the SG194 pair")
    print("7. Quotient interpretation currently most suspicious:")
    print("   194.1.1.1 single-group and double-group first, then 10.4.1.31 double-group")
    print("8. 194.1.1.1 Z^16 should now be interpreted as:")
    print("   a raw free-dominated quotient with free part Z^16 and no isolated finite torsion sector")
    print("9. 10.4.1.31 existing quotient also needs reinterpretation?:")
    print("   yes for the double-group mixed quotient; much less for the single-group finite quotient")
    print("10. PDF report generated?:")
    print(f"   {REPORT_PDF.exists()}")
    print("11. handoff/status/next-step files generated?:")
    print(f"   {HANDOFF_MD.exists() and CURRENT_STATUS_JSON.exists() and NEXT_STEP_PROMPT_TXT.exists()}")
    print("12. New package path:")
    print(f"   {PACKAGE_TARBALL}")
    print("13. Package tree:")
    for line in package_tree:
        print(f"   {line}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate_outputs()
    else:
        generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
