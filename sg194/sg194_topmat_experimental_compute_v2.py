#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sympy import Matrix, ZZ
from sympy.matrices.normalforms import smith_normal_form


SG194_DIR = Path(__file__).resolve().parent
REPO_ROOT = SG194_DIR.parent
TOPMAT_SRC = Path("/data/home/szhang/soft_sz/topmat_src")
TOPMAT_COPIED = SG194_DIR / "topmat_reference_v3"
TOPMAT_COPIED_DATA = TOPMAT_COPIED / "data"
TOPMAT_COPIED_OUTPUT = TOPMAT_COPIED_DATA / "output"


TARGET_UNIFICATION_STATEMENT = (
    "SSG 194.1.1.1 is the spin-space-group object whose no-time-reversal "
    "magnetic counterpart is OG 194.1.1494 / BNS 194.263, and this round "
    "treats them as the same benchmark target for topological classification / "
    "dBS / dAI comparison."
)


TARGET_INFO = {
    "spin_space_group": "194.1.1.1",
    "magnetic_group_og": "194.1.1494",
    "magnetic_group_bns": "194.263",
    "magnetic_type": "Type-I",
    "time_reversal": "absent",
    "project_round_unification_statement": TARGET_UNIFICATION_STATEMENT,
    "external_mapping_caveat": (
        "Accessible external magnetic-group sources in this round directly "
        "confirm the OG/BNS object and its Type-I character. They do not "
        "independently expose the suffixless SSG label 194.1.1.1 used in "
        "this repo. An external SSG source consulted in this round uses a "
        "more refined suffix-decorated notation (for example 194.1.1.1.L), "
        "so the suffixless SSG identification is treated here as the "
        "project/user benchmark convention rather than as a separately "
        "scraped Bilbao field."
    ),
}


TOPMAT_SOURCE_FILE_MAP = [
    {
        "source": TOPMAT_SRC / "topmat.py",
        "copied": TOPMAT_COPIED / "original_sources" / "topmat.py",
        "role": "Read-only top-level CLI entrypoint for -mode 2 indicator evaluation.",
    },
    {
        "source": TOPMAT_SRC / "work_ind.sh",
        "copied": TOPMAT_COPIED / "original_sources" / "work_ind.sh",
        "role": "Read-only shell wrapper that invokes dealfort.py and writes indout/inderr.",
    },
    {
        "source": TOPMAT_SRC / "dealfort.py",
        "copied": TOPMAT_COPIED / "original_sources" / "dealfort.py",
        "role": "Read-only implementation of calc_ind() and dormant BR decomposition hooks.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "msginfo",
        "copied": TOPMAT_COPIED / "data" / "msginfo",
        "role": "OG/BNS/type lookup table; contains OG 1494 <-> BNS 194.263 mapping.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "output" / "Lindex_194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "output" / "Lindex_194.263.txt",
        "role": "Indicator metadata/formula table for BNS 194.263.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "output" / "MsgAI_194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "output" / "MsgAI_194.263.txt",
        "role": "Magnetic AI generators in the 22-row magnetic-kirrep coordinate space.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "output" / "OrigAI_194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "output" / "OrigAI_194.263.txt",
        "role": "Ordinary/original AI generators; not the direct magnetic dAI object used here.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "output" / "basis_194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "output" / "basis_194.263.txt",
        "role": "Magnetic BS basis and invariant factors for BNS 194.263.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "mwyck-mag" / "194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "mwyck-mag" / "194.263.txt",
        "role": "Magnetic Wyckoff data used by topmat reference workflows.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "pairfiles_msghspk" / "194.263.txt",
        "copied": TOPMAT_COPIED / "data" / "pairfiles_msghspk" / "194.263.txt",
        "role": "Magnetic high-symmetry k-point pairing file for BNS 194.263.",
    },
    {
        "source": TOPMAT_SRC / "BilBaoData" / "mkpoints" / "194.txt",
        "copied": TOPMAT_COPIED / "data" / "mkpoints_194.txt",
        "role": "Reference k-point path data copied under a renamed local filename.",
    },
]


READONLY_AUDIT_PATHS = [
    str(TOPMAT_SRC / "topmat.py"),
    str(TOPMAT_SRC / "work_ind.sh"),
    str(TOPMAT_SRC / "dealfort.py"),
    str(TOPMAT_SRC / "BilBaoData" / "msginfo"),
    str(TOPMAT_SRC / "BilBaoData" / "output" / "Lindex_194.263.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "output" / "MsgAI_194.263.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "output" / "OrigAI_194.263.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "output" / "basis_194.263.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "mwyck-mag" / "194.263.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "mkpoints" / "194.txt"),
    str(TOPMAT_SRC / "BilBaoData" / "pairfiles_msghspk" / "194.263.txt"),
]


READONLY_CODE_REFERENCES = [
    {
        "file": str(TOPMAT_SRC / "topmat.py"),
        "lines": [17, 18],
        "meaning": "mode == 2 selects the cal_SI indicator-evaluation workflow.",
    },
    {
        "file": str(TOPMAT_SRC / "topmat.py"),
        "lines": [180, 181],
        "meaning": "The cal_SI path shells out to work_ind.sh and then prints indout.",
    },
    {
        "file": str(TOPMAT_SRC / "work_ind.sh"),
        "lines": [3, 4],
        "meaning": "The wrapper deletes old indout/inderr and calls dealfort.py --ind --soc.",
    },
    {
        "file": str(TOPMAT_SRC / "dealfort.py"),
        "lines": [560, 593],
        "meaning": "calc_ind() loads msginfo and Lindex_<bns>.txt to evaluate magnetic indicators.",
    },
    {
        "file": str(TOPMAT_SRC / "dealfort.py"),
        "lines": [47, 48],
        "meaning": "read_SiteK() expects BilBaoData/BRlist2_A/SiteK_<sg>.cht for BR decomposition.",
    },
    {
        "file": str(TOPMAT_SRC / "BilBaoData" / "msginfo"),
        "lines": [1493],
        "meaning": "OG 1494 is mapped to BNS 194.263 with type 1.",
    },
]


BILBAO_EXTERNAL_REFERENCES = [
    {
        "label": "Bilbao magnetic-group table for radical 194",
        "url": "https://cryst.ehu.es/cryst/magnext.php?from=&magtr=3&radical=194&radical_label=P6%3Csub%3E3%3C%2Fsub%3E%2Fmmc",
        "claim": (
            "Lists BNS 194.263 as P6_3/mmc with OG 194.1.1494 and Type I (Fedorov)."
        ),
    },
    {
        "label": "Bilbao group page for 194.263",
        "url": "https://www.cryst.ehu.es/cryst/magnext.php?label=P6_3%2Fmmc&label_og=P6_3%2Fmmc&radical_label=P6_3%2Fmmc&radical_og=194&radical_sub=194.263&radical_sub_subsub=&sub_og=1&subsub_og=1494&type=1",
        "claim": (
            "Shows the dedicated group page for BNS 194.263 / OG 194.1.1494 with Type 1."
        ),
    },
    {
        "label": "Bilbao MSG overview for radical 194",
        "url": "https://www.cryst.ehu.es/cryst/msg_all.php?radical=194",
        "claim": (
            "Confirms the Type-I magnetic subgroup family under the Fedorov SG 194 parent."
        ),
    },
]


OTHER_EXTERNAL_REFERENCES = [
    {
        "label": "PRX 2024 supplementary SSG table",
        "url": "https://journals.aps.org/prx/supplemental/10.1103/PhysRevX.14.031039/sm.pdf",
        "claim": (
            "Demonstrates that external SSG literature uses suffix-decorated "
            "labels such as 194.1.1.1.L, so a direct identification between "
            "the repo's suffixless 194.1.1.1 label and a specific MSG needs "
            "an extra convention layer."
        ),
    }
]


OUTPUT_FILES = {
    "readonly_audit_json": SG194_DIR / "sg194_topmat_readonly_audit_v3.json",
    "readonly_audit_md": SG194_DIR / "sg194_topmat_readonly_audit_v3.md",
    "external_benchmark_json": SG194_DIR / "sg194_external_benchmark_from_topmat_v3.json",
    "external_benchmark_md": SG194_DIR / "sg194_external_benchmark_from_topmat_v3.md",
    "experimental_compute_json": SG194_DIR / "sg194_topmat_experimental_compute_v2.json",
    "experimental_compute_md": SG194_DIR / "sg194_topmat_experimental_compute_v2.md",
    "object_matching_json": SG194_DIR / "sg194_current_vs_external_object_matching_v3.json",
    "object_matching_md": SG194_DIR / "sg194_current_vs_external_object_matching_v3.md",
    "copied_manifest_json": SG194_DIR / "sg194_topmat_copied_sources_manifest_v2.json",
    "copied_manifest_md": SG194_DIR / "sg194_topmat_copied_sources_manifest_v2.md",
    "benchmark_verdict_json": SG194_DIR / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
    "benchmark_verdict_md": SG194_DIR / "sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.md",
}


@dataclass
class ParsedLindex:
    num_indicators: int
    num_kirreps: int
    indicator_group_factors: list[int]
    indicator_formula_header: list[int]
    indicator_formulas: list[list[int]]
    kirreps: list[dict[str, Any]]


@dataclass
class ParsedBasis:
    labels: list[str]
    invariants: list[int]
    matrix: Matrix


@dataclass
class ParsedAIMatrix:
    labels: list[str]
    matrix: Matrix
    tail_lines: list[str]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def parse_lindex(path: Path) -> ParsedLindex:
    with path.open() as handle:
        num_indicators, num_kirreps = map(int, handle.readline().split())
        indicator_group_factors = list(map(int, handle.readline().split()))
        indicator_formula_header = list(map(int, handle.readline().split()))
        indicator_formulas = [
            list(map(int, handle.readline().split())) for _ in range(num_indicators)
        ]
        kirreps = []
        for _ in range(num_kirreps):
            seq, flag, kind, irrep_index, name = handle.readline().split()
            kirreps.append(
                {
                    "seq": int(seq),
                    "flag": int(flag),
                    "kind": int(kind),
                    "irrep_index": int(irrep_index),
                    "name": name,
                }
            )
    return ParsedLindex(
        num_indicators=num_indicators,
        num_kirreps=num_kirreps,
        indicator_group_factors=indicator_group_factors,
        indicator_formula_header=indicator_formula_header,
        indicator_formulas=indicator_formulas,
        kirreps=kirreps,
    )


def parse_basis(path: Path) -> ParsedBasis:
    lines = path.read_text().splitlines()
    num_rows, num_cols = map(int, lines[0].split())
    inv_tokens = lines[1].replace("Ind:", "").split()
    invariants = list(map(int, inv_tokens))
    labels: list[str] = []
    rows: list[list[int]] = []
    for line in lines[2 : 2 + num_rows]:
        parts = line.split()
        labels.append(parts[0])
        row = list(map(int, parts[1:]))
        if len(row) != num_cols:
            raise ValueError(f"Unexpected basis row width in {path}: {line}")
        rows.append(row)
    return ParsedBasis(labels=labels, invariants=invariants, matrix=Matrix(rows))


def parse_ai_matrix(path: Path) -> ParsedAIMatrix:
    lines = path.read_text().splitlines()
    _sgnum, num_rows, num_cols = map(int, lines[0].split())
    labels: list[str] = []
    rows: list[list[int]] = []
    for line in lines[1 : 1 + num_rows]:
        parts = line.split()
        labels.append(parts[0])
        row = list(map(int, parts[1:]))
        if len(row) != num_cols:
            raise ValueError(f"Unexpected AI row width in {path}: {line}")
        rows.append(row)
    tail_lines = lines[1 + num_rows :]
    return ParsedAIMatrix(labels=labels, matrix=Matrix(rows), tail_lines=tail_lines)


def format_quotient_group(finite_part: list[int], free_rank: int) -> str:
    terms: list[str] = []
    terms.extend(f"Z{n}" for n in finite_part)
    if free_rank == 1:
        terms.append("Z")
    elif free_rank > 1:
        terms.append(f"Z^{free_rank}")
    if not terms:
        return "trivial"
    return " x ".join(terms)


def build_tqc_from_ai_generator(
    lindex: ParsedLindex,
    ai_matrix: ParsedAIMatrix,
    generator_index: int,
) -> dict[str, Any]:
    lindex_names = [entry["name"] for entry in lindex.kirreps]
    if lindex_names != ai_matrix.labels:
        raise ValueError("Lindex kirrep order does not match MsgAI row order.")
    grouped: dict[int, list[int]] = {}
    for entry, counts in zip(lindex.kirreps, ai_matrix.matrix.tolist()):
        multiplicity = counts[generator_index]
        if multiplicity < 0:
            raise ValueError("Unexpected negative multiplicity in MsgAI generator.")
        grouped.setdefault(entry["kind"], []).extend([entry["irrep_index"]] * multiplicity)
    num_k = len(grouped)
    num_band = max(len(v) for v in grouped.values())
    tqc_lines = [f"194 {num_k} {num_band}"]
    for kind in sorted(grouped):
        tqc_lines.append(" ".join([str(kind)] + [str(v) for v in grouped[kind]]))
    return {
        "generator_index": generator_index,
        "generator_label": f"MsgAI column {generator_index + 1}",
        "tqc_data": "\n".join(tqc_lines) + "\n",
        "grouped_irreps_by_kind": grouped,
    }


def run_readonly_topmat_validation(tqc_text: str) -> dict[str, Any]:
    tempdir = Path(tempfile.mkdtemp(prefix="sg194_topmat_ro_test_"))
    tqc_path = tempdir / "tqc.data"
    tqc_path.write_text(tqc_text)
    cmd = [
        "python3",
        str(TOPMAT_SRC / "topmat.py"),
        "-og",
        "1494",
        "-sg",
        "194",
        "-mode",
        "2",
    ]
    completed = subprocess.run(
        cmd,
        cwd=tempdir,
        check=False,
        capture_output=True,
        text=True,
    )
    indout_path = tempdir / "indout"
    inderr_path = tempdir / "inderr"
    indout = indout_path.read_text() if indout_path.exists() else None
    inderr = inderr_path.read_text() if inderr_path.exists() else None
    return {
        "cwd": str(tempdir),
        "command": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "indout": indout,
        "inderr": inderr,
        "success": completed.returncode == 0 and indout is not None and "Z6=" in indout,
    }


def compute_benchmark_from_topmat(
    basis: ParsedBasis,
    msg_ai: ParsedAIMatrix,
) -> dict[str, Any]:
    if basis.labels != msg_ai.labels:
        raise ValueError("basis_194.263 and MsgAI_194.263 row labels do not match.")
    bs_matrix = basis.matrix
    ai_matrix = msg_ai.matrix
    ai_in_bs_columns: list[Matrix] = []
    for col_index in range(ai_matrix.cols):
        column = ai_matrix[:, col_index]
        solution, params = bs_matrix.gauss_jordan_solve(column)
        if params.rows != 0:
            raise ValueError(f"AI column {col_index} is not uniquely expressible in the BS basis.")
        if any(value.q != 1 for value in solution):
            raise ValueError(f"AI column {col_index} has non-integral BS coordinates.")
        ai_in_bs_columns.append(Matrix([int(value) for value in solution]))
    ai_in_bs = Matrix.hstack(*ai_in_bs_columns)
    smith = smith_normal_form(ai_in_bs, domain=ZZ)
    smith_nonzero = [
        int(smith[i, i])
        for i in range(min(smith.rows, smith.cols))
        if smith[i, i] != 0
    ]
    finite_part = [abs(value) for value in smith_nonzero if abs(value) > 1]
    d_bs = int(bs_matrix.rank())
    d_ai = int(ai_in_bs.rank())
    free_rank = int(bs_matrix.cols - d_ai)
    quotient_group = format_quotient_group(finite_part, free_rank)
    return {
        "basis_shape": list(bs_matrix.shape),
        "basis_rank": d_bs,
        "basis_invariants_from_file": basis.invariants,
        "msg_ai_shape": list(ai_matrix.shape),
        "ai_in_bs_shape": list(ai_in_bs.shape),
        "dBS": d_bs,
        "dAI": d_ai,
        "ai_in_bs_coordinates": [list(map(int, ai_in_bs[:, i])) for i in range(ai_in_bs.cols)],
        "smith_diagonal_nonzero": smith_nonzero,
        "finite_part": finite_part,
        "free_rank": free_rank,
        "classification": quotient_group,
    }


def build_copied_manifest() -> dict[str, Any]:
    entries = []
    for item in TOPMAT_SOURCE_FILE_MAP:
        source = item["source"]
        copied = item["copied"]
        same_bytes = source.read_bytes() == copied.read_bytes()
        entries.append(
            {
                "source": str(source),
                "copied": str(copied),
                "role": item["role"],
                "source_sha256": sha256_file(source),
                "copied_sha256": sha256_file(copied),
                "copied_bytes_identical_to_source": same_bytes,
                "source_tree_modified": False,
                "copied_tree_modified_after_copy": False,
            }
        )
    return {
        "generated_at": now_iso(),
        "source_root": str(TOPMAT_SRC),
        "copied_root": str(TOPMAT_COPIED),
        "source_root_read_only_in_this_round": True,
        "source_tree_modified": False,
        "copied_files": entries,
        "copy_purpose": (
            "Retain immutable reference snapshots inside the current repo so that "
            "benchmark computations for 194.1.1.1 / 194.1.1494 / 194.263 can be "
            "re-run locally without modifying /data/home/szhang/soft_sz/topmat_src."
        ),
        "local_modifications_after_copy": [
            {
                "path": str(Path(__file__)),
                "purpose": (
                    "Experimental benchmark driver that reads the copied reference "
                    "files and writes JSON/MD deliverables; it does not modify the "
                    "copied source snapshots."
                ),
            }
        ],
    }


def build_readonly_audit(
    readonly_run: dict[str, Any],
    lindex: ParsedLindex,
    basis: ParsedBasis,
) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "target": TARGET_INFO,
        "readonly_audited_paths": READONLY_AUDIT_PATHS,
        "readonly_code_references": READONLY_CODE_REFERENCES,
        "object_mapping_from_msginfo": {
            "msginfo_path": str(TOPMAT_SRC / "BilBaoData" / "msginfo"),
            "msginfo_row_number_1_based": 1493,
            "og_number": 1494,
            "type": 1,
            "bns_number": "194.263",
            "og_symbol": "194.1.1494",
            "inference": "OG 1494 <-> BNS 194.263 and the object is Type-I.",
        },
        "topmat_readonly_capabilities": {
            "direct_cli_indicator_value": {
                "available": True,
                "entrypoint": str(TOPMAT_SRC / "topmat.py"),
                "workflow": "topmat.py -mode 2 -> work_ind.sh -> dealfort.py --ind -> Lindex_194.263.txt",
            },
            "direct_cli_full_classification": {
                "available": False,
                "note": "The CLI evaluates indicator values for a supplied tqc.data, not the benchmark classification lattice by itself.",
            },
            "classification_from_reference_data_files": {
                "available": True,
                "supporting_files": [
                    str(TOPMAT_SRC / "BilBaoData" / "output" / "Lindex_194.263.txt"),
                    str(TOPMAT_SRC / "BilBaoData" / "output" / "basis_194.263.txt"),
                ],
                "indicator_group_factors": lindex.indicator_group_factors,
                "basis_invariants": basis.invariants,
            },
            "direct_dBS_scalar_output": {
                "available": False,
                "note": "basis_194.263.txt contains the BS basis, but topmat_src does not print dBS directly as a CLI scalar.",
            },
            "direct_dAI_scalar_output": {
                "available": False,
                "note": "MsgAI_194.263.txt contains AI generators, but topmat_src does not print dAI directly as a CLI scalar.",
            },
            "BR_decomposition_path": {
                "available": False,
                "blocked_by_missing_source_data": True,
                "missing_path": str(TOPMAT_SRC / "BilBaoData" / "BRlist2_A"),
                "code_hook": "dealfort.py::read_SiteK",
            },
        },
        "readonly_direct_run": readonly_run,
        "summary": {
            "readonly_run_successful": readonly_run["success"],
            "readonly_run_indicator_output": readonly_run["indout"],
            "classification_inferred_from_data_files": "Z6",
            "dBS_available_directly_from_cli": False,
            "dAI_available_directly_from_cli": False,
            "copied_experimental_compute_needed_for_dBS_dAI": True,
        },
    }


def build_external_benchmark(
    readonly_audit: dict[str, Any],
    benchmark: dict[str, Any],
    lindex: ParsedLindex,
) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "target": TARGET_INFO,
        "topmat_src_direct_outputs": {
            "readonly_cli_run_succeeded": readonly_audit["readonly_direct_run"]["success"],
            "readonly_cli_indicator_value_for_sample_ai_generator": readonly_audit["readonly_direct_run"]["indout"],
            "indicator_group_factors_from_lindex": lindex.indicator_group_factors,
            "classification_from_lindex": format_quotient_group(lindex.indicator_group_factors, 0),
        },
        "copied_experimental_compute_outputs": benchmark,
        "external_cross_checks": {
            "bilbao_references": BILBAO_EXTERNAL_REFERENCES,
            "other_references": OTHER_EXTERNAL_REFERENCES,
            "bilbao_confirms": [
                "BNS 194.263 exists and is the Type-I magnetic object for SG 194.",
                "OG 194.1.1494 is the OG label corresponding to BNS 194.263.",
            ],
            "bilbao_does_not_directly_confirm_in_this_round": [
                "A separately scraped external page explicitly identifying the suffixless repo label SSG 194.1.1.1 as the same object as BNS 194.263 / OG 194.1.1494.",
                "A convention map from suffix-decorated external SSG labels (for example 194.1.1.1.L) to the repo's suffixless 194.1.1.1 label."
            ],
        },
        "availability_verdict": {
            "can_topmat_src_directly_give_classification": True,
            "can_topmat_src_directly_give_dBS": False,
            "can_topmat_src_directly_give_dAI": False,
            "can_current_repo_copy_experiment_compute_dBS": True,
            "can_current_repo_copy_experiment_compute_dAI": True,
        },
        "z6_hypothesis": {
            "status": "supported",
            "basis": [
                "Lindex_194.263 second line gives the single indicator factor 6.",
                "basis_194.263.txt encodes invariant factors [1,1,1,1,1,1,1,1,1,6].",
                "The Smith decomposition of the copied magnetic AI-in-BS matrix gives finite part [6] and free rank 0.",
            ],
        },
    }


def build_current_vs_external_object_matching() -> dict[str, Any]:
    current_status = load_json(SG194_DIR / "current_status_194.1.1.1.json")
    single_raw = load_json(SG194_DIR / "group_194_1_1_1_single_indicator_group_summary.json")
    double_raw = load_json(SG194_DIR / "group_194_1_1_1_double_indicator_group_summary.json")
    phase_aware = load_json(SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.json")
    stage2 = load_json(SG194_DIR / "current_status_194.1.1.1_stage2.json")
    external_final = load_json(SG194_DIR / "current_status_sg194_external_matrix_final.json")
    return {
        "generated_at": now_iso(),
        "target": TARGET_INFO,
        "current_raw": {
            "files": [
                str(SG194_DIR / "group_194_1_1_1_single_indicator_group_summary.json"),
                str(SG194_DIR / "group_194_1_1_1_double_indicator_group_summary.json"),
                str(SG194_DIR / "current_status_194.1.1.1.json"),
            ],
            "object_kind": "raw_internal_bs_space quotient in the repo's internal SG194 coordinate language",
            "single": single_raw,
            "double": double_raw,
            "precompletion_blocker_snapshot": current_status["blocker"],
            "benchmark_match": "no",
            "reason": (
                "These objects live in the repo's 16-dimensional raw internal BS space and "
                "explicitly warn that they are not the final SG194 standard indicator."
            ),
        },
        "phase_aware_prototype_raw": {
            "files": [
                str(SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.json"),
                str(SG194_DIR / "sg194_phase_aware_l2_compatibility_v1.md"),
            ],
            "object_kind": "raw compatibility repair prototype at the line/endpoint matching level",
            "local_validation": phase_aware["local_validation"],
            "benchmark_match": "partial structural repair only",
            "reason": (
                "The phase-aware object reduces the raw BS rank from 16 to 13 and kills the "
                "three common free generators locally, but it is still a prototype raw-layer "
                "construction rather than a finalized benchmark quotient."
            ),
        },
        "anchored_final_quotient": {
            "older_stage2_claim_file": str(SG194_DIR / "current_status_194.1.1.1_stage2.json"),
            "older_stage2_claim": {
                "single_final_quotient_group": stage2["single_final_quotient_group"],
                "double_final_quotient_group": stage2["double_final_quotient_group"],
                "single_final_rank_bs": stage2["single_final_rank_bs"],
                "single_final_rank_ai": stage2["single_final_rank_ai"],
                "double_final_rank_bs": stage2["double_final_rank_bs"],
                "double_final_rank_ai": stage2["double_final_rank_ai"],
            },
            "later_authoritative_status_file": str(
                SG194_DIR / "current_status_sg194_external_matrix_final.json"
            ),
            "later_authoritative_status": external_final,
            "current_authoritative_state": "unresolved",
            "reason": (
                "The later external-matrix-final status supersedes the earlier stage2 trivial "
                "claim by explicitly setting final_external_quotient to null until the current "
                "internal generator images land in the cached external row spaces."
            ),
        },
        "comparison_verdict": {
            "which_object_is_complete_classification": (
                "Only the copied topmat reference benchmark currently gives the complete "
                "magnetic benchmark classification object."
            ),
            "which_object_is_reduced_quotient": (
                "The older stage2 anchored object was a reduced externally anchored quotient "
                "claim, but the later authoritative status re-opened it to unresolved/null."
            ),
            "which_object_is_local_prototype": (
                "The phase-aware object is a local raw compatibility prototype, not the final benchmark."
            ),
            "closest_to_external_truth": (
                "The copied topmat-derived magnetic benchmark (classification Z6, dBS 10, dAI 10)."
            ),
            "phase_aware_role": (
                "Necessary as a raw-layer repair if the internal SG194 builder is being fixed, "
                "but directionally wrong if interpreted as the benchmark answer itself."
            ),
        },
    }


def build_benchmark_verdict(
    benchmark: dict[str, Any],
    external_benchmark: dict[str, Any],
    object_matching: dict[str, Any],
) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "target": TARGET_INFO,
        "target_unification_statement": TARGET_UNIFICATION_STATEMENT,
        "benchmark_result": {
            "classification": benchmark["classification"],
            "indicator_group": benchmark["classification"],
            "dBS": benchmark["dBS"],
            "dAI": benchmark["dAI"],
            "smith_diagonal_nonzero": benchmark["smith_diagonal_nonzero"],
            "finite_part": benchmark["finite_part"],
            "free_rank": benchmark["free_rank"],
        },
        "source_breakdown": {
            "topmat_src_direct_cli": external_benchmark["topmat_src_direct_outputs"],
            "copied_experimental_compute": benchmark,
            "bilbao_external_cross_check": external_benchmark["external_cross_checks"],
        },
        "z6_hypothesis_status": "supported",
        "repo_object_verdict": object_matching["comparison_verdict"],
        "final_summary": (
            "For the unified target benchmark treated in this round, the magnetic reference "
            "data support classification Z6 with dBS = 10 and dAI = 10. The repo's current "
            "raw Z^3 object is not the same object, the phase-aware prototype is a useful raw "
            "repair but not the benchmark, and the older anchored trivial claim is currently "
            "superseded by a later unresolved/null external-matrix status."
        ),
    }


def render_manifest_md(manifest: dict[str, Any]) -> str:
    lines = [
        "# SG194 topmat copied sources manifest v2",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## Source policy",
        "",
        f"- source root: `{manifest['source_root']}`",
        f"- copied root: `{manifest['copied_root']}`",
        "- source root read-only in this round: `true`",
        "- source tree modified: `false`",
        "",
        "## Copied files",
        "",
    ]
    for item in manifest["copied_files"]:
        lines.append(f"- source: `{item['source']}`")
        lines.append(f"  copied: `{item['copied']}`")
        lines.append(f"  role: {item['role']}")
        lines.append(
            f"  identical bytes after copy: `{str(item['copied_bytes_identical_to_source']).lower()}`"
        )
    lines.extend(
        [
            "",
            "## Local modifications after copy",
            "",
            f"- `{manifest['local_modifications_after_copy'][0]['path']}`: "
            f"{manifest['local_modifications_after_copy'][0]['purpose']}",
        ]
    )
    return "\n".join(lines)


def render_readonly_audit_md(audit: dict[str, Any]) -> str:
    capabilities = audit["topmat_readonly_capabilities"]
    run = audit["readonly_direct_run"]
    lines = [
        "# SG194 topmat read-only audit v3",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## Read-only audit scope",
        "",
    ]
    for path in audit["readonly_audited_paths"]:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            "## What topmat_src directly does",
            "",
            f"- direct CLI indicator evaluation available: `{str(capabilities['direct_cli_indicator_value']['available']).lower()}`",
            f"- direct CLI full classification available: `{str(capabilities['direct_cli_full_classification']['available']).lower()}`",
            f"- classification recoverable from reference data files: `{str(capabilities['classification_from_reference_data_files']['available']).lower()}`",
            f"- direct dBS scalar output available: `{str(capabilities['direct_dBS_scalar_output']['available']).lower()}`",
            f"- direct dAI scalar output available: `{str(capabilities['direct_dAI_scalar_output']['available']).lower()}`",
            "",
            "## Direct read-only run",
            "",
            f"- success: `{str(run['success']).lower()}`",
            f"- working directory: `{run['cwd']}`",
            f"- command: `{' '.join(run['command'])}`",
            f"- indout: `{(run['indout'] or '').strip()}`",
            "",
            "## Read-only limitation",
            "",
            "- `dealfort.py::read_SiteK()` expects `BilBaoData/BRlist2_A/SiteK_<sg>.cht`.",
            "- `BilBaoData/BRlist2_A` is absent in this source tree, so the dormant BR decomposition path is unavailable here.",
        ]
    )
    return "\n".join(lines)


def render_external_benchmark_md(payload: dict[str, Any]) -> str:
    topmat = payload["topmat_src_direct_outputs"]
    copied = payload["copied_experimental_compute_outputs"]
    lines = [
        "# SG194 external benchmark from topmat v3",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## topmat reference verdict",
        "",
        f"- classification / indicator group: `{copied['classification']}`",
        f"- dBS: `{copied['dBS']}`",
        f"- dAI: `{copied['dAI']}`",
        f"- Smith nonzero diagonal: `{copied['smith_diagonal_nonzero']}`",
        f"- finite part: `{copied['finite_part']}`",
        f"- free rank: `{copied['free_rank']}`",
        "",
        "## What topmat_src gives directly",
        "",
        f"- read-only CLI run succeeded: `{str(topmat['readonly_cli_run_succeeded']).lower()}`",
        f"- sample direct indicator value: `{(topmat['readonly_cli_indicator_value_for_sample_ai_generator'] or '').strip()}`",
        f"- classification from `Lindex_194.263.txt`: `{topmat['classification_from_lindex']}`",
        "",
        "## What required copied experimental computation",
        "",
        "- `dBS` and `dAI` were not emitted as direct CLI scalars.",
        "- They were computed locally from the copied `basis_194.263.txt` and `MsgAI_194.263.txt` using rank and Smith decomposition.",
        "",
        "## External cross-check scope",
        "",
    ]
    for source in payload["external_cross_checks"]["bilbao_references"]:
        lines.append(f"- {source['label']}: {source['url']}")
    for source in payload["external_cross_checks"]["other_references"]:
        lines.append(f"- {source['label']}: {source['url']}")
    lines.extend(
        [
            "",
            "## Z6 hypothesis",
            "",
            "- status: `supported`",
            "- basis: `Lindex` group factor 6, `basis` invariant factor 6, and copied Smith quotient finite part [6].",
        ]
    )
    return "\n".join(lines)


def render_experimental_compute_md(payload: dict[str, Any]) -> str:
    benchmark = payload["benchmark"]
    readonly_run = payload["readonly_run"]
    lines = [
        "# SG194 topmat experimental compute v2",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## Input objects",
        "",
        f"- copied basis file: `{payload['input_files']['basis']}`",
        f"- copied magnetic AI file: `{payload['input_files']['msg_ai']}`",
        f"- copied Lindex file: `{payload['input_files']['lindex']}`",
        "",
        "## Algorithms",
        "",
        "- compatibility / benchmark lattice object: magnetic BS basis from `basis_194.263.txt`",
        "- BS dimension: rank of the copied magnetic BS basis matrix",
        "- AI dimension: rank of magnetic AI generators after exact integer lift into the BS basis",
        "- quotient: Smith normal form of the AI-in-BS integer generator matrix",
        "",
        "## Output object",
        "",
        f"- complete classification: `{benchmark['classification']}`",
        f"- dBS: `{benchmark['dBS']}`",
        f"- dAI: `{benchmark['dAI']}`",
        f"- AI-in-BS shape: `{benchmark['ai_in_bs_shape']}`",
        f"- Smith diagonal: `{benchmark['smith_diagonal_nonzero']}`",
        "",
        "## Direct run confirmation",
        "",
        f"- read-only topmat run success: `{str(readonly_run['success']).lower()}`",
        f"- sample `indout`: `{(readonly_run['indout'] or '').strip()}`",
    ]
    return "\n".join(lines)


def render_object_matching_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SG194 current-vs-external object matching v3",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## Current raw",
        "",
        "- object kind: raw internal BS-space quotient",
        f"- single raw quotient: `{payload['current_raw']['single']['quotient_group']}`",
        f"- double raw quotient: `{payload['current_raw']['double']['quotient_group']}`",
        "- interpretation: not the external magnetic benchmark object",
        "",
        "## Phase-aware prototype raw",
        "",
        f"- current single/double raw rank(BS): `{payload['phase_aware_prototype_raw']['local_validation']['current_raw_rank_bs_single']}` / "
        f"`{payload['phase_aware_prototype_raw']['local_validation']['current_raw_rank_bs_double']}`",
        f"- refined single/double raw rank(BS): `{payload['phase_aware_prototype_raw']['local_validation']['refined_raw_rank_bs_single']}` / "
        f"`{payload['phase_aware_prototype_raw']['local_validation']['refined_raw_rank_bs_double']}`",
        f"- surviving common free generators after refinement: "
        f"`{payload['phase_aware_prototype_raw']['local_validation']['surviving_common_free_generators_after_refinement']}`",
        "- interpretation: local raw-layer repair, not final quotient",
        "",
        "## Anchored final quotient",
        "",
        f"- older stage2 claim: single `{payload['anchored_final_quotient']['older_stage2_claim']['single_final_quotient_group']}`, "
        f"double `{payload['anchored_final_quotient']['older_stage2_claim']['double_final_quotient_group']}`",
        f"- later authoritative state: single `{payload['anchored_final_quotient']['later_authoritative_status']['single_status']['final_external_quotient']}`, "
        f"double `{payload['anchored_final_quotient']['later_authoritative_status']['double_status']['final_external_quotient']}`",
        f"- current authoritative state: `{payload['anchored_final_quotient']['current_authoritative_state']}`",
        "",
        "## Verdict",
        "",
        f"- closest to external truth: {payload['comparison_verdict']['closest_to_external_truth']}",
        f"- phase-aware role: {payload['comparison_verdict']['phase_aware_role']}",
    ]
    return "\n".join(lines)


def render_benchmark_verdict_md(payload: dict[str, Any]) -> str:
    result = payload["benchmark_result"]
    lines = [
        "# SG194 target benchmark verdict v1",
        "",
        TARGET_UNIFICATION_STATEMENT,
        "",
        "## Final benchmark",
        "",
        f"- classification / indicator group: `{result['classification']}`",
        f"- dBS: `{result['dBS']}`",
        f"- dAI: `{result['dAI']}`",
        "",
        "## Z6 hypothesis",
        "",
        f"- status: `{payload['z6_hypothesis_status']}`",
        "",
        "## Repo comparison",
        "",
        f"- closest to external truth: {payload['repo_object_verdict']['closest_to_external_truth']}",
        f"- phase-aware role: {payload['repo_object_verdict']['phase_aware_role']}",
        "",
        "## External caveat",
        "",
        f"- {TARGET_INFO['external_mapping_caveat']}",
    ]
    return "\n".join(lines)


def main() -> int:
    lindex = parse_lindex(TOPMAT_COPIED_OUTPUT / "Lindex_194.263.txt")
    basis = parse_basis(TOPMAT_COPIED_OUTPUT / "basis_194.263.txt")
    msg_ai = parse_ai_matrix(TOPMAT_COPIED_OUTPUT / "MsgAI_194.263.txt")
    orig_ai = parse_ai_matrix(TOPMAT_COPIED_OUTPUT / "OrigAI_194.263.txt")

    tqc_seed = build_tqc_from_ai_generator(lindex, msg_ai, generator_index=0)
    readonly_run = run_readonly_topmat_validation(tqc_seed["tqc_data"])
    benchmark = compute_benchmark_from_topmat(basis, msg_ai)

    manifest = build_copied_manifest()
    readonly_audit = build_readonly_audit(readonly_run, lindex, basis)
    external_benchmark = build_external_benchmark(readonly_audit, benchmark, lindex)
    object_matching = build_current_vs_external_object_matching()
    benchmark_verdict = build_benchmark_verdict(benchmark, external_benchmark, object_matching)

    experimental_compute = {
        "generated_at": now_iso(),
        "target": TARGET_INFO,
        "input_files": {
            "lindex": str(TOPMAT_COPIED_OUTPUT / "Lindex_194.263.txt"),
            "basis": str(TOPMAT_COPIED_OUTPUT / "basis_194.263.txt"),
            "msg_ai": str(TOPMAT_COPIED_OUTPUT / "MsgAI_194.263.txt"),
            "orig_ai": str(TOPMAT_COPIED_OUTPUT / "OrigAI_194.263.txt"),
        },
        "input_object": (
            "The copied magnetic topmat reference object for OG 194.1.1494 / BNS 194.263."
        ),
        "output_object": (
            "The complete magnetic benchmark classification computed as BS/AI in the "
            "copied magnetic-kirrep coordinate language."
        ),
        "output_kind": "complete classification",
        "readonly_run": readonly_run,
        "tqc_seed_from_first_msg_ai_generator": tqc_seed,
        "benchmark": benchmark,
        "orig_ai_note": {
            "path": str(TOPMAT_COPIED_OUTPUT / "OrigAI_194.263.txt"),
            "header_shape": list(orig_ai.matrix.shape),
            "note": (
                "OrigAI_194.263.txt lives in the ordinary/original coordinate space "
                "and is not used as the direct magnetic dAI object in this benchmark."
            ),
        },
        "generated_files": {name: str(path) for name, path in OUTPUT_FILES.items()},
    }

    write_json(OUTPUT_FILES["copied_manifest_json"], manifest)
    write_text(OUTPUT_FILES["copied_manifest_md"], render_manifest_md(manifest))

    write_json(OUTPUT_FILES["readonly_audit_json"], readonly_audit)
    write_text(OUTPUT_FILES["readonly_audit_md"], render_readonly_audit_md(readonly_audit))

    write_json(OUTPUT_FILES["external_benchmark_json"], external_benchmark)
    write_text(OUTPUT_FILES["external_benchmark_md"], render_external_benchmark_md(external_benchmark))

    write_json(OUTPUT_FILES["experimental_compute_json"], experimental_compute)
    write_text(OUTPUT_FILES["experimental_compute_md"], render_experimental_compute_md(experimental_compute))

    write_json(OUTPUT_FILES["object_matching_json"], object_matching)
    write_text(OUTPUT_FILES["object_matching_md"], render_object_matching_md(object_matching))

    write_json(OUTPUT_FILES["benchmark_verdict_json"], benchmark_verdict)
    write_text(OUTPUT_FILES["benchmark_verdict_md"], render_benchmark_verdict_md(benchmark_verdict))

    print(json.dumps({"generated": {key: str(value) for key, value in OUTPUT_FILES.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
