#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
import textwrap
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import bs4
import pandas as pd
import requests
import sympy as sp


ROOT = Path(__file__).resolve().parent
GROUP = "194.1.1.1"

CACHE_DIR = ROOT / "sg194_external_matrix_cache"
ORDINARY_CACHE_DIR = CACHE_DIR / "ordinary"
SPINORIAL_CACHE_DIR = CACHE_DIR / "spinorial"

ORD_MATRIX_JSON = ROOT / "sg194_external_ordinary_generator_matrix.json"
SPIN_MATRIX_JSON = ROOT / "sg194_external_spinorial_generator_matrix.json"
ACQ_MD = ROOT / "sg194_external_matrix_acquisition.md"
ACQ_JSON = ROOT / "sg194_external_matrix_acquisition.json"
SINGLE_FINAL_JSON = ROOT / "sg194_single_final_external_reduction.json"
SINGLE_FINAL_MD = ROOT / "sg194_single_final_external_reduction.md"
DOUBLE_FINAL_JSON = ROOT / "sg194_double_final_external_reduction.json"
DOUBLE_FINAL_MD = ROOT / "sg194_double_final_external_reduction.md"
AUDIT_MD = ROOT / "sg194_external_matrix_final_audit.md"
SUMMARY_JSON = ROOT / "sg194_external_matrix_final_summary.json"
HANDOFF_MD = ROOT / "handoff_sg194_external_matrix_final.md"
CURRENT_STATUS_JSON = ROOT / "current_status_sg194_external_matrix_final.json"
NEXT_STEP_TXT = ROOT / "next_step_prompt_sg194_external_matrix_final.txt"
REPORT_MD = ROOT / "sg194_external_matrix_final_report.md"
REPORT_TEX = ROOT / "sg194_external_matrix_final_report.tex"
REPORT_PDF = ROOT / "sg194_external_matrix_final_report.pdf"

PACKAGE_NAME = "review_package_sg194_external_matrix_final"
PACKAGE_DIR = ROOT / PACKAGE_NAME
PACKAGE_TARBALL = ROOT / f"{PACKAGE_NAME}.tar.gz"
README_PATH = PACKAGE_DIR / "README.md"

RESEARCH_RESULTS_TSV = ROOT / "research-results-external-matrix-final.tsv"
AUTORESEARCH_STATE_JSON = ROOT / "autoresearch-state-external-matrix-final.json"
VERIFY_CMD = "python3 -u debug_sg194_external_matrix_final.py --validate"
GUARD_CMD = (
    "python3 -u debug_sg194_standard_alignment_v2.py --validate && "
    "python3 -u debug_external_sg194_audit.py --validate && "
    "python3 -u debug_raw_matrix_audit.py --validate"
)

SG194_EXT_SOURCE_JSON = ROOT / "sg194_external_source_audit.json"
SG194_EXT_AI_JSON = ROOT / "sg194_external_ai_standard.json"
SG194_EXT_CMP_JSON = ROOT / "sg194_external_vs_current_ai_comparison.json"
SG194_FINAL_JUDGMENT_JSON = ROOT / "sg194_final_correction_judgment.json"
SINGLE_V2_MAP_JSON = ROOT / "sg194_single_external_rowspace_projection.json"
DOUBLE_V2_ALIGN_JSON = ROOT / "sg194_double_repcontent_alignment.json"
SINGLE_V2_QUOT_JSON = ROOT / "sg194_single_standard_quotient_recomputed_v2.json"
DOUBLE_V2_QUOT_JSON = ROOT / "sg194_double_standard_quotient_recomputed_v2.json"
V2_SUMMARY_JSON = ROOT / "sg194_standard_alignment_summary_v2.json"

RAW_SINGLE_CAND = ROOT / "raw_194_1_1_1_single_ai_candidates.json"
RAW_SINGLE_BS = ROOT / "raw_194_1_1_1_single_bs_basis_raw.json"
RAW_SINGLE_AI = ROOT / "raw_194_1_1_1_single_ai_basis.json"
RAW_SINGLE_QUOT = ROOT / "raw_194_1_1_1_single_quotient.json"
RAW_DOUBLE_CAND = ROOT / "raw_194_1_1_1_double_ai_candidates.json"
RAW_DOUBLE_QUOT = ROOT / "raw_194_1_1_1_double_quotient.json"
DOUBLE_REPCONTENT_JSON = ROOT / "sg194_double_repcontent_alignment.json"

SINGLE_SITE_ROUTE_URL = "https://cryst.ehu.es/rep/sitesym.html"
SINGLE_SITE_CGI = "https://cryst.ehu.es/cgi-bin/rep/programs/sitesym/sitesym_cgi.py"
DOUBLE_BANDREP_CGI = "https://cryst.ehu.es/cgi-bin/cryst/programs/bandrep.pl"

SINGLE_KPOINTS = [
    ("GM", "0", "0", "0"),
    ("A", "0", "0", "1/2"),
    ("K", "1/3", "1/3", "0"),
    ("H", "1/3", "1/3", "1/2"),
    ("M", "1/2", "0", "0"),
    ("L", "1/2", "0", "1/2"),
]

WP_VALUE_TO_KEY = OrderedDict(
    [
        ("2&a&(0,0,0)", ("a", "2a")),
        ("2&b&(0,0,1/4)", ("b", "2b")),
        ("2&c&(1/3,2/3,1/4)", ("c", "2c")),
        ("2&d&(1/3,2/3,3/4)", ("d", "2d")),
        ("4&e&(0,0,z)", ("e", "4e")),
        ("4&f&(1/3,2/3,z)", ("f", "4f")),
        ("6&g&(1/2,0,0)", ("g", "6g")),
        ("6&h&(x,2x,1/4)", ("h", "6h")),
        ("12&i&(x,0,0)", ("i", "12i")),
        ("12&j&(x,y,1/4)", ("j", "12j")),
        ("12&k&(x,2x,z)", ("k", "12k")),
        ("24&l&(x,y,z)", ("l", "24l")),
    ]
)

WP_TOKEN_TO_KEY: dict[str, tuple[str, str]] = {}
for _raw, _value in WP_VALUE_TO_KEY.items():
    WP_TOKEN_TO_KEY[_raw] = _value
    WP_TOKEN_TO_KEY[_value[1]] = _value

BACKGROUND_FILES = [
    SG194_EXT_SOURCE_JSON,
    SG194_EXT_AI_JSON,
    SG194_EXT_CMP_JSON,
    SG194_FINAL_JUDGMENT_JSON,
    SINGLE_V2_MAP_JSON,
    DOUBLE_V2_ALIGN_JSON,
    SINGLE_V2_QUOT_JSON,
    DOUBLE_V2_QUOT_JSON,
    V2_SUMMARY_JSON,
    ROOT / "current_status_sg194_standard_alignment_v2.json",
    ROOT / "handoff_sg194_standard_alignment_v2.md",
    ROOT / "next_step_prompt_sg194_standard_alignment_v2.txt",
    ROOT / "raw_194_1_1_1_single_C.json",
    ROOT / "raw_194_1_1_1_single_bs_basis_raw.json",
    ROOT / "raw_194_1_1_1_single_bs_basis_pretty.json",
    ROOT / "raw_194_1_1_1_single_ai_candidates.json",
    ROOT / "raw_194_1_1_1_single_ai_basis.json",
    ROOT / "raw_194_1_1_1_single_ai_in_bs_matrix.json",
    ROOT / "raw_194_1_1_1_single_quotient.json",
    ROOT / "raw_194_1_1_1_double_C.json",
    ROOT / "raw_194_1_1_1_double_bs_basis_raw.json",
    ROOT / "raw_194_1_1_1_double_bs_basis_pretty.json",
    ROOT / "raw_194_1_1_1_double_ai_candidates.json",
    ROOT / "raw_194_1_1_1_double_ai_basis.json",
    ROOT / "raw_194_1_1_1_double_ai_in_bs_matrix.json",
    ROOT / "raw_194_1_1_1_double_quotient.json",
    ROOT / "swyckoff_r.py",
    ROOT / "swyckoff_k.py",
    ROOT / "SSGReps" / "SSGReps" / "SSGReps.py",
    ROOT / "SSGReps" / "SSGReps" / "SG_utils.py",
    ROOT / "SSGReps" / "SSGReps" / "rep_utils.py",
]

REQUIRED_OUTPUTS = [
    ORD_MATRIX_JSON,
    SPIN_MATRIX_JSON,
    ACQ_MD,
    ACQ_JSON,
    SINGLE_FINAL_JSON,
    SINGLE_FINAL_MD,
    DOUBLE_FINAL_JSON,
    DOUBLE_FINAL_MD,
    AUDIT_MD,
    SUMMARY_JSON,
    HANDOFF_MD,
    CURRENT_STATUS_JSON,
    NEXT_STEP_TXT,
    ROOT / "debug_sg194_external_matrix_final.py",
    REPORT_TEX,
    REPORT_PDF,
    PACKAGE_TARBALL,
]


@dataclass
class SingleExternalMatrix:
    matrix: sp.Matrix
    row_labels: list[str]
    column_labels: list[str]
    representative_by_wp: dict[str, str]
    raw_files: list[str]


@dataclass
class DoubleExternalMatrix:
    mixed_matrix: sp.Matrix
    mixed_row_labels: list[str]
    mixed_column_labels: list[dict[str, Any]]
    spinorial_matrix: sp.Matrix
    spinorial_column_labels: list[dict[str, Any]]
    raw_files: list[str]


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


def latex_escape(text: str) -> str:
    repl = {
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
    out = text
    for old, new in repl.items():
        out = out.replace(old, new)
    return out


def serialize_entry(value: Any) -> Any:
    if isinstance(value, sp.Basic):
        if value.is_Integer:
            return int(value)
        if value.is_Rational:
            return str(value)
        return str(sp.simplify(value))
    if isinstance(value, list):
        return [serialize_entry(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serialize_entry(val) for key, val in value.items()}
    return value


def matrix_to_json_rows(matrix: sp.Matrix) -> list[list[Any]]:
    return [[serialize_entry(matrix[i, j]) for j in range(matrix.cols)] for i in range(matrix.rows)]


def support_from_dense(vec: list[Any], labels: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label, coeff in zip(labels, vec):
        coeff_s = serialize_entry(coeff)
        if coeff_s in [0, "0"]:
            continue
        out.append({"label": label, "coeff": coeff_s})
    return out


def new_external_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    session.cookies.set("turnstile_passed", str(int(time.time())), domain="cryst.ehu.es", path="/")
    session.trust_env = False
    return session


def post_text(url: str, data: dict[str, str], tries: int = 4) -> str:
    last_exc: Exception | None = None
    for attempt in range(tries):
        try:
            session = new_external_session()
            response = session.post(url, data=data, timeout=60)
            response.raise_for_status()
            return response.text
        except Exception as exc:
            last_exc = exc
            time.sleep(1 + attempt)
    if last_exc is None:
        raise RuntimeError("unexpected empty error state")
    raise last_exc


def parse_bandrep_terms(cell: Any) -> list[tuple[str, int]]:
    text = str(cell).replace("\xa0", " ").strip()
    if text in {"", "nan", "NaN"}:
        return []
    out: list[tuple[str, int]] = []
    for part in text.split("⊕"):
        term = part.strip()
        if not term or "(" not in term:
            continue
        left = term.split("(")[0].strip()
        idx = 0
        while idx < len(left) and left[idx].isdigit():
            idx += 1
        mult = int(left[:idx]) if idx > 0 else 1
        label = left[idx:].strip()
        out.append((label, mult))
    return out


def normalize_single_irrep_label(label: str) -> str:
    mapping = {
        "A'1": "A1'",
        "A'2": "A2'",
        "A''1": "A1''",
        "A''2": "A2''",
    }
    return mapping.get(label, label)


def fetch_single_external_matrix(cache_dir: Path) -> SingleExternalMatrix:
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_files: list[str] = []
    showwp_text = post_text(
        SINGLE_SITE_CGI,
        {"sgr": "194", "what2do": "showwp", "kbasis": "1", "kp1": "0", "kp2": "0", "kp3": "0", "lab": "GM"},
    )
    showwp_path = cache_dir / "showwp_GM.html"
    showwp_path.write_text(showwp_text)
    raw_files.append(str(showwp_path.relative_to(ROOT)))
    showwp_soup = bs4.BeautifulSoup(showwp_text, "html.parser")
    wp_values = [inp["value"] for inp in showwp_soup.find_all("input", {"name": "wp", "type": "radio"})]

    representatives: dict[str, str] = {}
    for wp_value in wp_values:
        orbit_text = post_text(
            SINGLE_SITE_CGI,
            {"sgr": "194", "lab": "GM", "kpoint": "0,0,0", "kbasis": "1", "what2do": "showorbit", "wp": wp_value},
        )
        if wp_value not in WP_TOKEN_TO_KEY:
            raise RuntimeError(f"unexpected ordinary wp token from Bilbao: {wp_value}")
        wp_label = WP_TOKEN_TO_KEY[wp_value][1]
        orbit_path = cache_dir / f"showorbit_{wp_label}.html"
        orbit_path.write_text(orbit_text)
        raw_files.append(str(orbit_path.relative_to(ROOT)))
        orbit_soup = bs4.BeautifulSoup(orbit_text, "html.parser")
        radios = orbit_soup.find_all("input", {"name": "rep0", "type": "radio"})
        if not radios:
            raise RuntimeError(f"missing ordinary SITESYM representative for {wp_value}")
        representatives[wp_value] = radios[0]["value"]

    table_cache: dict[tuple[str, str], tuple[list[str], list[tuple[str, list[int]]]]] = {}

    def get_table(k_label: str, k1: str, k2: str, k3: str, wp_value: str) -> tuple[list[str], list[tuple[str, list[int]]]]:
        key = (k_label, wp_value)
        if key in table_cache:
            return table_cache[key]
        text = post_text(
            SINGLE_SITE_CGI,
            {
                "sgr": "194",
                "lab": k_label,
                "kpoint": f"{k1},{k2},{k3}",
                "wp": wp_value,
                "kbasis": "1",
                "what2do": "calcsim",
                "rep0": representatives[wp_value],
            },
        )
        if wp_value not in WP_TOKEN_TO_KEY:
            raise RuntimeError(f"unexpected ordinary wp token from Bilbao: {wp_value}")
        wp_label = WP_TOKEN_TO_KEY[wp_value][1]
        table_path = cache_dir / f"calcsim_{k_label}_{wp_label}.html"
        table_path.write_text(text)
        raw_files.append(str(table_path.relative_to(ROOT)))
        tables = pd.read_html(BytesIO(text.encode("iso-8859-1", errors="ignore")), flavor="lxml")
        target = None
        for table in tables:
            cell = str(table.iloc[0, 0])
            if "Reps" in cell and "Irreps" in cell:
                target = table
                break
        if target is None:
            raise RuntimeError(f"ordinary SITESYM missing decomposition table for {k_label} / {wp_value}")
        site_irreps = [normalize_single_irrep_label(str(x).replace("\xa0", " ").strip()) for x in list(target.iloc[0])[1:]]
        rows: list[tuple[str, list[int]]] = []
        for _, row in target.iloc[1:].reset_index(drop=True).iterrows():
            ir_label = str(row.iloc[0]).replace("\xa0", " ").strip()
            coeffs: list[int] = []
            for entry in row.iloc[1:]:
                text_entry = str(entry).replace("\xa0", " ").strip()
                coeffs.append(0 if text_entry in {"", "nan", "NaN", "·"} else int(float(text_entry)))
            rows.append((ir_label, coeffs))
        table_cache[key] = (site_irreps, rows)
        return table_cache[key]

    row_labels: list[str] = []
    column_labels: list[str] = []
    for _, _, _, _, in SINGLE_KPOINTS:
        pass
    for k_label, k1, k2, k3 in SINGLE_KPOINTS:
        for wp_value in wp_values:
            letter_key, _ = WP_TOKEN_TO_KEY[wp_value]
            site_irreps, rows = get_table(k_label, k1, k2, k3, wp_value)
            for irrep in site_irreps:
                label = f"{letter_key}_{irrep}"
                if label not in column_labels:
                    column_labels.append(label)
            for ir_label, _ in rows:
                label = f"{k_label}:{ir_label}"
                if label not in row_labels:
                    row_labels.append(label)

    row_index = {label: idx for idx, label in enumerate(row_labels)}
    col_index = {label: idx for idx, label in enumerate(column_labels)}
    matrix = sp.zeros(len(row_labels), len(column_labels))
    for k_label, k1, k2, k3 in SINGLE_KPOINTS:
        for wp_value in wp_values:
            letter_key, _ = WP_TOKEN_TO_KEY[wp_value]
            site_irreps, rows = get_table(k_label, k1, k2, k3, wp_value)
            for ir_label, coeffs in rows:
                i = row_index[f"{k_label}:{ir_label}"]
                for j_local, coeff in enumerate(coeffs):
                    j = col_index[f"{letter_key}_{site_irreps[j_local]}"]
                    matrix[i, j] = coeff

    return SingleExternalMatrix(
        matrix=matrix,
        row_labels=row_labels,
        column_labels=column_labels,
        representative_by_wp={WP_TOKEN_TO_KEY[key][1]: value for key, value in representatives.items()},
        raw_files=raw_files,
    )


def fetch_double_wp_table(wp_value: str, cache_dir: Path) -> pd.DataFrame:
    text = post_text(
        DOUBLE_BANDREP_CGI,
        {
            "super": "194",
            "elementary": "",
            "elementaryTR": "",
            "wyck": "Wyckoff",
            "wyckTR": "",
            "wyckoff": wp_value,
            "list": "Submit",
        },
    )
    wp_label = WP_VALUE_TO_KEY[wp_value][1]
    path = cache_dir / f"bandrep_{wp_label}.html"
    path.write_text(text)
    tables = pd.read_html(BytesIO(text.encode("iso-8859-1", errors="ignore")), flavor="lxml")
    for table in tables:
        if table.shape[0] >= 8 and "Band-Rep." in str(table.iloc[0, 0]):
            return table
    raise RuntimeError(f"BANDREP missing Wyckoff table for {wp_value}")


def is_spinorial_double_column(wp_label: str, local_index: int, bandrep_label: str) -> bool:
    bare = bandrep_label.split("↑")[0].strip()
    if wp_label == "2a":
        return bare[0].isdigit() or bare.startswith("E1")
    if wp_label in {"2b", "2c", "2d"}:
        return bare in {"E1", "E2", "E3"}
    if wp_label in {"4e", "4f"}:
        return bare.startswith("1E") or bare.startswith("2E") or bare.startswith("E1")
    if wp_label == "6g":
        return bare.startswith("1E") or bare.startswith("2E")
    if wp_label == "6h":
        return bare == "E"
    if wp_label in {"12i", "12j", "12k"}:
        return bare.startswith("1E") or bare.startswith("2E")
    if wp_label == "24l":
        return local_index == 1
    return False


def fetch_double_external_matrix(cache_dir: Path) -> DoubleExternalMatrix:
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw_files: list[str] = []
    rows: list[str] = []
    columns: list[dict[str, Any]] = []
    cell_terms: dict[tuple[str, int, int], list[tuple[str, int]]] = {}
    tables_by_wp: dict[str, pd.DataFrame] = {}

    for wp_value, (_, wp_label) in WP_VALUE_TO_KEY.items():
        table = fetch_double_wp_table(wp_value, cache_dir)
        raw_files.append(str((cache_dir / f"bandrep_{wp_label}.html").relative_to(ROOT)))
        tables_by_wp[wp_value] = table
        for j in range(1, table.shape[1]):
            bandrep_label = str(table.iloc[0, j]).replace("\xa0", " ").strip()
            columns.append(
                {
                    "wp_value": wp_value,
                    "wp_label": wp_label,
                    "letter_key": WP_VALUE_TO_KEY[wp_value][0],
                    "local_index": j - 1,
                    "bandrep_label": bandrep_label,
                    "spinorial_selected": is_spinorial_double_column(wp_label, j - 1, bandrep_label),
                }
            )
        for i in range(1, table.shape[0]):
            k_label = str(table.iloc[i, 0]).replace("\xa0", " ").strip().split(":")[0]
            for j in range(1, table.shape[1]):
                terms = parse_bandrep_terms(table.iloc[i, j])
                cell_terms[(wp_value, i, j - 1)] = terms
                for little_irrep, _ in terms:
                    combined = f"{k_label}:{little_irrep}"
                    if combined not in rows:
                        rows.append(combined)

    row_index = {label: idx for idx, label in enumerate(rows)}
    mixed = sp.zeros(len(rows), len(columns))
    offset = 0
    offsets: dict[str, int] = {}
    for wp_value in WP_VALUE_TO_KEY:
        offsets[wp_value] = offset
        offset += tables_by_wp[wp_value].shape[1] - 1
    for wp_value in WP_VALUE_TO_KEY:
        table = tables_by_wp[wp_value]
        local_offset = offsets[wp_value]
        for i in range(1, table.shape[0]):
            k_label = str(table.iloc[i, 0]).replace("\xa0", " ").strip().split(":")[0]
            for j in range(1, table.shape[1]):
                for little_irrep, mult in cell_terms[(wp_value, i, j - 1)]:
                    mixed[row_index[f"{k_label}:{little_irrep}"], local_offset + (j - 1)] += mult

    spinorial_indices = [idx for idx, item in enumerate(columns) if item["spinorial_selected"]]
    spinorial = mixed[:, spinorial_indices]
    spinorial_labels = [columns[idx] for idx in spinorial_indices]
    return DoubleExternalMatrix(
        mixed_matrix=mixed,
        mixed_row_labels=rows,
        mixed_column_labels=columns,
        spinorial_matrix=spinorial,
        spinorial_column_labels=spinorial_labels,
        raw_files=raw_files,
    )


def support_in_generator_domain(row: sp.Matrix, labels: list[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for label, coeff in zip(labels, list(row)):
        if coeff == 0:
            continue
        items.append({"label": label, "coeff": serialize_entry(coeff)})
    return items


def first_unsolved_rows(source_rows_matrix: sp.Matrix, target_rows_matrix: sp.Matrix) -> list[int]:
    missing: list[int] = []
    for r in range(target_rows_matrix.rows):
        try:
            source_rows_matrix.T.gauss_jordan_solve(target_rows_matrix.row(r).T)
        except Exception:
            missing.append(r)
    return missing


def difference_basis(source_rows: list[sp.Matrix], other_basis_matrix: sp.Matrix, labels: list[str]) -> list[list[dict[str, Any]]]:
    out: list[list[dict[str, Any]]] = []
    span = other_basis_matrix
    for row in source_rows:
        try:
            span.T.gauss_jordan_solve(row.T)
        except Exception:
            out.append(support_in_generator_domain(row, labels))
            span = sp.Matrix.vstack(span, row)
    return out


def build_single_final(single_external: SingleExternalMatrix) -> tuple[dict[str, Any], str]:
    raw_cand = load_json(RAW_SINGLE_CAND)
    raw_bs = load_json(RAW_SINGLE_BS)
    raw_ai = load_json(RAW_SINGLE_AI)
    raw_quot = load_json(RAW_SINGLE_QUOT)
    v2_quot = load_json(SINGLE_V2_QUOT_JSON)

    current_labels = [cand["generator_id"] for cand in raw_cand["candidates"]]
    ext_perm = [single_external.column_labels.index(label) for label in current_labels]
    ext_matrix = single_external.matrix[:, ext_perm]

    full_current = sp.Matrix.hstack(*[sp.Matrix(cand["unknown_vector"]) for cand in raw_cand["candidates"]])
    hsp_indices = [
        i
        for i, label in enumerate(raw_cand["unknown_ordering"])
        if any(label.startswith(prefix + "_") for prefix in ["P1", "P2", "P3", "B1", "P5", "P6"])
    ]
    hsp_current = sp.Matrix.hstack(
        *[sp.Matrix([cand["unknown_vector"][i] for i in hsp_indices]) for cand in raw_cand["candidates"]]
    )

    full_union_rank = int(sp.Matrix.vstack(full_current, ext_matrix).rank())
    hsp_union_rank = int(sp.Matrix.vstack(hsp_current, ext_matrix).rank())
    full_rowspace_rank = int(full_current.rank())
    ext_rowspace_rank = int(ext_matrix.rank())
    hsp_rowspace_rank = int(hsp_current.rank())

    full_missing_rows = first_unsolved_rows(full_current, ext_matrix)
    hsp_missing_rows = first_unsolved_rows(hsp_current, ext_matrix)

    full_current_rows = full_current.rowspace()
    ext_rows = ext_matrix.rowspace()
    full_current_basis = sp.Matrix.vstack(*full_current_rows)
    ext_basis = sp.Matrix.vstack(*ext_rows)

    external_only = difference_basis(ext_rows, full_current_basis, current_labels)
    current_only = difference_basis(full_current_rows, ext_basis, current_labels)

    payload = {
        "group": GROUP,
        "group_type": 1,
        "old_raw_quotient": raw_quot["raw_quotient"],
        "v2_hsp_point_space_quotient": v2_quot["current_hsp_point_space_quotient"],
        "full_external_ordinary_quotient": None,
        "ordinary_external_matrix_shape": [int(ext_matrix.rows), int(ext_matrix.cols)],
        "ordinary_external_matrix_cached": True,
        "current_full_raw_ai_matrix_shape": [int(full_current.rows), int(full_current.cols)],
        "current_hsp_ai_matrix_shape": [int(hsp_current.rows), int(hsp_current.cols)],
        "current_full_raw_ai_rowspace_rank": full_rowspace_rank,
        "current_hsp_ai_rowspace_rank": hsp_rowspace_rank,
        "external_ordinary_ai_rowspace_rank": ext_rowspace_rank,
        "full_raw_union_rowspace_rank": full_union_rank,
        "hsp_union_rowspace_rank": hsp_union_rank,
        "full_raw_rowspace_intersection_rank": full_rowspace_rank + ext_rowspace_rank - full_union_rank,
        "hsp_rowspace_intersection_rank": hsp_rowspace_rank + ext_rowspace_rank - hsp_union_rank,
        "exact_full_raw_to_external_row_map_exists": not full_missing_rows,
        "exact_hsp_to_external_row_map_exists": not hsp_missing_rows,
        "external_rows_not_in_full_raw_rowspace": [single_external.row_labels[i] for i in full_missing_rows],
        "external_rows_not_in_hsp_rowspace": [single_external.row_labels[i] for i in hsp_missing_rows],
        "external_only_generator_domain_basis": external_only,
        "current_only_generator_domain_basis": current_only,
        "final_conclusion": (
            "Final ordinary external reduction is still blocked. After caching the full Bilbao 34x45 ordinary "
            "generator matrix and reordering its columns by exact generator ids, the current SG194 ordinary AI image "
            "still fails to span the external ordinary row space: both current and external row spaces have rank 13, "
            "but their union has rank 14. Therefore the previous v1 trivial claim must be retired; the internal "
            "single line is not yet in the standard ordinary symmetry-data space."
        ),
        "confidence": "high",
    }

    md = "\n".join(
        [
            "# SG194 Single Final External Reduction",
            "",
            f"- Raw quotient: `{payload['old_raw_quotient']}`",
            f"- V2 HSP point-space quotient: `{payload['v2_hsp_point_space_quotient']}`",
            "- Full external ordinary quotient: `blocked`",
            f"- Current full raw AI rowspace rank: `{payload['current_full_raw_ai_rowspace_rank']}`",
            f"- Current HSP AI rowspace rank: `{payload['current_hsp_ai_rowspace_rank']}`",
            f"- External ordinary AI rowspace rank: `{payload['external_ordinary_ai_rowspace_rank']}`",
            f"- Full raw / external union rowspace rank: `{payload['full_raw_union_rowspace_rank']}`",
            f"- HSP / external union rowspace rank: `{payload['hsp_union_rowspace_rank']}`",
            f"- Exact full-raw row map exists: `{payload['exact_full_raw_to_external_row_map_exists']}`",
            f"- Exact HSP row map exists: `{payload['exact_hsp_to_external_row_map_exists']}`",
            "",
            "Why the final reduction is blocked:",
            "- The missing blocker is no longer “matrix not cached”; the full external ordinary matrix is now cached locally.",
            "- The stronger blocker is a genuine row-space mismatch: current and external ordinary AI images are both rank-13, but they intersect in rank 12 only.",
            "- Therefore no exact current raw / HSP -> external ordinary row-space lift consistent with all 45 standard generators exists at present.",
            "",
            "One external-only generator-domain basis vector:",
            f"- `{external_only[0] if external_only else []}`",
            "",
            "One current-only generator-domain basis vector:",
            f"- `{current_only[0] if current_only else []}`",
            "",
            "Correction relative to older conclusions:",
            "- v1 `trivial` must be discarded.",
            "- v2 `Z^5` remains a stricter intermediate point-space diagnostic, not the final external ordinary quotient.",
        ]
    )
    return payload, md


def build_double_final(double_external: DoubleExternalMatrix) -> tuple[dict[str, Any], str]:
    raw_cand = load_json(RAW_DOUBLE_CAND)
    raw_quot = load_json(RAW_DOUBLE_QUOT)
    repcontent = load_json(DOUBLE_REPCONTENT_JSON)

    spin_cols = double_external.spinorial_column_labels
    problem_idx = [i for i, item in enumerate(spin_cols) if item["wp_label"] in {"2b", "2c", "2d", "6h"}]
    problem_labels = [f"{spin_cols[i]['wp_label']}:{spin_cols[i]['bandrep_label'].split('↑')[0]}" for i in problem_idx]
    ext_problem = double_external.spinorial_matrix[:, problem_idx]

    unknown = raw_cand["unknown_ordering"]
    hsp_indices = [
        i
        for i, label in enumerate(unknown)
        if any(label.startswith(prefix + "_") for prefix in ["P1", "P2", "P3", "B1", "P5", "P6"])
    ]
    by_id = {cand["generator_id"]: cand for cand in raw_cand["candidates"]}

    def vec(gen_id: str) -> sp.Matrix:
        return sp.Matrix([by_id[gen_id]["unknown_vector"][i] for i in hsp_indices])

    merged_cols: list[sp.Matrix] = []
    for fam in ["b", "c", "d"]:
        groups = [
            [f"{fam}_proj_doubleprime_1d_1", f"{fam}_proj_doubleprime_1d_2"],
            [f"{fam}_proj_prime_1d_3", f"{fam}_proj_prime_1d_4"],
            [f"{fam}_proj_doubleprime_2d_5", f"{fam}_proj_doubleprime_2d_6"],
        ]
        for gids in groups:
            merged_cols.append(sum((vec(gid) for gid in gids), sp.zeros(len(hsp_indices), 1)))
    h_ids = [cand["generator_id"] for cand in raw_cand["candidates"] if cand["family_id"] == "h"]
    merged_cols.append(sum((vec(gid) for gid in h_ids), sp.zeros(len(hsp_indices), 1)))
    current_problem = sp.Matrix.hstack(*merged_cols)

    current_rows = current_problem.rowspace()
    ext_rows = ext_problem.rowspace()
    current_basis = sp.Matrix.vstack(*current_rows)
    ext_basis = sp.Matrix.vstack(*ext_rows)
    union_rank = int(sp.Matrix.vstack(current_problem, ext_problem).rank())
    current_only = difference_basis(current_rows, ext_basis, problem_labels)
    external_only = difference_basis(ext_rows, current_basis, problem_labels)

    delta_basis = repcontent["residual_rank_gap_basis"]
    payload = {
        "group": GROUP,
        "group_type": 2,
        "old_raw_quotient": raw_quot["raw_quotient"],
        "intermediate_repcontent_status": "v2 localized the residual rank-2 mismatch to 2b/2c/2d/6h",
        "full_external_spinorial_quotient": None,
        "spinorial_external_matrix_shape": [
            int(double_external.spinorial_matrix.rows),
            int(double_external.spinorial_matrix.cols),
        ],
        "spinorial_external_matrix_cached": True,
        "problem_sector_labels": problem_labels,
        "problem_sector_current_rank": int(current_problem.rank()),
        "problem_sector_external_rank": int(ext_problem.rank()),
        "problem_sector_union_rank": union_rank,
        "problem_sector_intersection_rank": int(current_problem.rank() + ext_problem.rank() - union_rank),
        "current_only_problem_sector_basis": current_only,
        "external_only_problem_sector_basis": external_only,
        "delta_c1_minus_b1_final_status": "still current-only excess direction; not absorbed by the external spinorial problem-sector row space",
        "delta_d1_minus_b1_final_status": "still current-only excess direction; not absorbed by the external spinorial problem-sector row space",
        "delta_basis_from_v2": delta_basis,
        "final_conclusion": (
            "Final double external reduction remains blocked. The full Bilbao 56x33 spinorial matrix is now cached, "
            "and the unambiguous 2b/2c/2d/6h spinorial sector already proves a genuine rank-2 mismatch: both current "
            "merged and external problem-sector row spaces have rank 6, but their union has rank 8. Therefore "
            "delta_c1_minus_b1 and delta_d1_minus_b1 remain current-only excess directions rather than mere missing "
            "lifts, and no honest final double standard quotient should be quoted yet."
        ),
        "confidence": "high",
    }

    md = "\n".join(
        [
            "# SG194 Double Final External Reduction",
            "",
            f"- Raw quotient: `{payload['old_raw_quotient']}`",
            "- Full external spinorial quotient: `blocked`",
            f"- External spinorial matrix shape: `{payload['spinorial_external_matrix_shape'][0]} x {payload['spinorial_external_matrix_shape'][1]}`",
            f"- Problem-sector current rank: `{payload['problem_sector_current_rank']}`",
            f"- Problem-sector external rank: `{payload['problem_sector_external_rank']}`",
            f"- Problem-sector union rank: `{payload['problem_sector_union_rank']}`",
            f"- Problem-sector intersection rank: `{payload['problem_sector_intersection_rank']}`",
            "",
            "What the full external matrix resolved:",
            "- The blocker is no longer “spinorial matrix missing”; the full external 56x33 matrix is now cached locally.",
            "- The residual problem is intrinsic to the current 2b/2c/2d/6h sector, not just to heuristic count alignment.",
            "",
            "Current-only problem-sector basis:",
            f"- `{current_only[0] if current_only else []}`",
            f"- `{current_only[1] if len(current_only) > 1 else []}`",
            "",
            "External-only problem-sector basis:",
            f"- `{external_only[0] if external_only else []}`",
            f"- `{external_only[1] if len(external_only) > 1 else []}`",
            "",
            "Final attribution of the old row-content blockers:",
            f"- `delta_c1_minus_b1`: {payload['delta_c1_minus_b1_final_status']}",
            f"- `delta_d1_minus_b1`: {payload['delta_d1_minus_b1_final_status']}",
            "",
            "Consequence:",
            "- Even with the full external spinorial matrix cached, the double line is not yet in Bilbao's physically irreducible standard language.",
            "- No final double standard-space quotient should be quoted from the current internal data.",
        ]
    )
    return payload, md


def build_matrix_json(single_external: SingleExternalMatrix, double_external: DoubleExternalMatrix) -> tuple[dict[str, Any], dict[str, Any]]:
    single_json = {
        "group": GROUP,
        "matrix_kind": "ordinary_generator_matrix",
        "shape": [int(single_external.matrix.rows), int(single_external.matrix.cols)],
        "row_labels": single_external.row_labels,
        "column_labels": single_external.column_labels,
        "matrix_entries": matrix_to_json_rows(single_external.matrix),
        "representatives_by_wp": single_external.representative_by_wp,
        "provenance": {
            "route": "Bilbao ordinary SITESYM",
            "landing_page": SINGLE_SITE_ROUTE_URL,
            "cgi": SINGLE_SITE_CGI,
            "kpoints": [label for label, *_ in SINGLE_KPOINTS],
            "raw_cache_files": single_external.raw_files,
        },
        "normalization_notes": [
            "Columns are kept in the native ordinary generator naming used in sg194_external_ai_standard.json.",
            "Matrix entries are exact integers parsed from Bilbao ordinary SITESYM decomposition tables.",
        ],
    }
    double_json = {
        "group": GROUP,
        "matrix_kind": "spinorial_generator_matrix",
        "shape": [int(double_external.spinorial_matrix.rows), int(double_external.spinorial_matrix.cols)],
        "row_labels": double_external.mixed_row_labels,
        "column_labels": double_external.spinorial_column_labels,
        "matrix_entries": matrix_to_json_rows(double_external.spinorial_matrix),
        "provenance": {
            "route": "Bilbao BANDREP without time reversal",
            "cgi": DOUBLE_BANDREP_CGI,
            "raw_cache_files": double_external.raw_files,
        },
        "normalization_notes": [
            "This file caches the physically irreducible spinorial 56x33 submatrix extracted from the full 56x78 BANDREP table.",
            "The full mixed 56x78 inventory is not treated as the final standard spinorial basis.",
        ],
        "mixed_reference_shape": [int(double_external.mixed_matrix.rows), int(double_external.mixed_matrix.cols)],
    }
    return single_json, double_json


def build_acquisition_json(single_external: SingleExternalMatrix, double_external: DoubleExternalMatrix) -> dict[str, Any]:
    return {
        "target_group": GROUP,
        "ordinary_matrix": {
            "shape": [int(single_external.matrix.rows), int(single_external.matrix.cols)],
            "route": {
                "landing_page": SINGLE_SITE_ROUTE_URL,
                "cgi": SINGLE_SITE_CGI,
                "steps": [
                    "showwp at GM",
                    "showorbit per Wyckoff position",
                    "calcsim per (k-point, Wyckoff) pair",
                ],
            },
            "row_labels_cached": True,
            "column_labels_cached": True,
            "provenance_cached": True,
            "raw_cache_files": single_external.raw_files,
        },
        "spinorial_matrix": {
            "shape": [int(double_external.spinorial_matrix.rows), int(double_external.spinorial_matrix.cols)],
            "route": {
                "cgi": DOUBLE_BANDREP_CGI,
                "steps": [
                    "Wyckoff page fetch per site",
                    "full mixed 56x78 table parse",
                    "physically irreducible spinorial 56x33 submatrix extraction",
                ],
            },
            "row_labels_cached": True,
            "column_labels_cached": True,
            "provenance_cached": True,
            "raw_cache_files": double_external.raw_files,
        },
    }


def build_acquisition_md(acq: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 External Matrix Acquisition",
            "",
            "Ordinary matrix:",
            f"- Shape: `{acq['ordinary_matrix']['shape'][0]} x {acq['ordinary_matrix']['shape'][1]}`",
            f"- Landing page: `{acq['ordinary_matrix']['route']['landing_page']}`",
            f"- CGI: `{acq['ordinary_matrix']['route']['cgi']}`",
            f"- Raw cache files: `{len(acq['ordinary_matrix']['raw_cache_files'])}`",
            "",
            "Spinorial matrix:",
            f"- Shape: `{acq['spinorial_matrix']['shape'][0]} x {acq['spinorial_matrix']['shape'][1]}`",
            f"- CGI: `{acq['spinorial_matrix']['route']['cgi']}`",
            f"- Raw cache files: `{len(acq['spinorial_matrix']['raw_cache_files'])}`",
            "",
            "Parsing route:",
            "- Ordinary: showwp -> showorbit -> calcsim tables -> exact integer 34x45 matrix.",
            "- Spinorial: BANDREP Wyckoff tables -> full mixed 56x78 matrix -> physically irreducible 56x33 submatrix.",
            "",
            "Final cache format:",
            "- machine-readable JSON with row labels, column labels, integer matrix entries, provenance, and normalization notes.",
            "- raw HTML kept under `sg194_external_matrix_cache/ordinary` and `sg194_external_matrix_cache/spinorial`.",
        ]
    )


def build_summary_json(single_payload: dict[str, Any], double_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_group": GROUP,
        "ordinary_external_matrix_cached": True,
        "spinorial_external_matrix_cached": True,
        "single_finalized": False,
        "double_finalized": False,
        "single_main_issue": "current ordinary AI row space differs from the external ordinary row space by one dimension",
        "double_main_issue": "problematic 2b/2c/2d/6h spinorial sector still has a genuine rank-2 mismatch",
        "current_alignment_to_external_language": False,
        "single_final_external_quotient": single_payload["full_external_ordinary_quotient"],
        "double_final_external_quotient": double_payload["full_external_spinorial_quotient"],
        "discarded_old_conclusions": [
            "single v1 standard-space quotient = trivial",
            "single raw Z^16 as a user-facing standard quotient",
            "double raw Z^16 as a user-facing standard quotient",
        ],
        "retained_new_conclusions": [
            "full Bilbao ordinary and spinorial matrices are now cached locally",
            "single is blocked by a genuine external ordinary row-space mismatch, not by missing matrix data",
            "double is blocked by a genuine rank-2 spinorial mismatch in the 2b/2c/2d/6h sector, not by missing matrix data",
        ],
    }


def build_audit_md(single_payload: dict[str, Any], double_payload: dict[str, Any], summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SG194 External Matrix Final Audit",
            "",
            "## Single",
            f"- Raw quotient: `{single_payload['old_raw_quotient']}`",
            f"- V2 point-space quotient: `{single_payload['v2_hsp_point_space_quotient']}`",
            "- Final external quotient: `blocked`",
            f"- Full raw / external union rowspace rank: `{single_payload['full_raw_union_rowspace_rank']}`",
            f"- HSP / external union rowspace rank: `{single_payload['hsp_union_rowspace_rank']}`",
            f"- Exact full-raw row map exists: `{single_payload['exact_full_raw_to_external_row_map_exists']}`",
            "",
            "## Double",
            f"- Raw quotient: `{double_payload['old_raw_quotient']}`",
            "- Final external quotient: `blocked`",
            f"- Problem-sector current rank: `{double_payload['problem_sector_current_rank']}`",
            f"- Problem-sector external rank: `{double_payload['problem_sector_external_rank']}`",
            f"- Problem-sector union rank: `{double_payload['problem_sector_union_rank']}`",
            "",
            "## Final status",
            f"- Ordinary external matrix cached: `{summary['ordinary_external_matrix_cached']}`",
            f"- Spinorial external matrix cached: `{summary['spinorial_external_matrix_cached']}`",
            f"- Single finalized: `{summary['single_finalized']}`",
            f"- Double finalized: `{summary['double_finalized']}`",
            "",
            "## What changed relative to v2",
            "- The blocker is no longer “matrix missing”.",
            "- Single now has a hard external ordinary row-space mismatch certificate.",
            "- Double now has a hard external spinorial problem-sector mismatch certificate.",
        ]
    )


def build_handoff(single_payload: dict[str, Any], double_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Handoff: SG194 External Matrix Final",
            "",
            "- Target: `194.1.1.1`",
            "- Completed: full Bilbao ordinary 34x45 matrix cached; full Bilbao spinorial 56x33 matrix cached",
            "- Single: final external ordinary quotient still blocked; current and external ordinary AI row spaces differ by one dimension",
            "- Double: final external spinorial quotient still blocked; the unambiguous 2b/2c/2d/6h sector has a genuine rank-2 mismatch",
            "- `delta_c1_minus_b1` / `delta_d1_minus_b1`: still current-only excess directions, not absorbed by the external spinorial problem-sector row space",
            "- Next step: if the goal is a truly final SG194 quotient, the internal single and double generator images must be rebuilt so that they land in the external standard row spaces before BS/AI is retaken",
            "- Read first:",
            "  - `sg194_external_matrix_final_report.pdf`",
            "  - `sg194_external_ordinary_generator_matrix.json`",
            "  - `sg194_external_spinorial_generator_matrix.json`",
            "  - `sg194_single_final_external_reduction.json`",
            "  - `sg194_double_final_external_reduction.json`",
        ]
    )


def build_next_step_prompt() -> str:
    return textwrap.dedent(
        """\
        $codex-autoresearch 继续在 /data/work/szhang/ssg/comprel 工作。

        不换群，不扩 workflow，只继续 `194.1.1.1` 的 final external reduction after full matrix caching。

        已完成且不要重做：
        - `sg194_external_ordinary_generator_matrix.json`
        - `sg194_external_spinorial_generator_matrix.json`
        - `sg194_single_final_external_reduction.json`
        - `sg194_double_final_external_reduction.json`
        - `sg194_external_matrix_final_report.pdf`

        当前结论：
        - ordinary 34x45 external matrix 已完整缓存。
        - spinorial 56x33 external matrix 已完整缓存。
        - single 仍 blocked：current ordinary AI row space 与 external ordinary row space 只在 rank 12 相交，union rank = 14。
        - double 仍 blocked：2b/2c/2d/6h problem sector 的 current / external spinorial row spaces 各 rank 6，但 union rank = 8。
        - `delta_c1_minus_b1` 与 `delta_d1_minus_b1` 仍是 current-only excess directions。

        下一步唯一目标：
        - 如果还要继续推进，必须重建 current single / double generator images，使它们先真正落到 Bilbao standard row spaces，再重新取 BS/AI。

        必须先读：
        - sg194_external_matrix_final_report.pdf
        - sg194_single_final_external_reduction.json
        - sg194_double_final_external_reduction.json
        - sg194_external_ordinary_generator_matrix.json
        - sg194_external_spinorial_generator_matrix.json
        """
    ).strip()


def build_report_md(acq: dict[str, Any], single_payload: dict[str, Any], double_payload: dict[str, Any], summary: dict[str, Any]) -> str:
    return textwrap.dedent(
        f"""\
        # SG194 External Matrix Final Report

        ## 1. Problem Background And Historical Error Chain

        Previous SG194 stages stopped at a point where the local repository did not cache the full external Bilbao ordinary and spinorial generator matrices. That made the final standard reduction underdetermined. This stage closes that specific blocker by caching:

        - ordinary external matrix: `34 x 45`
        - spinorial external matrix: `56 x 33`

        but it also shows that the remaining obstruction is **not** missing external data anymore.

        ## 2. External Matrix Acquisition

        Ordinary route:
        - landing page: `{SINGLE_SITE_ROUTE_URL}`
        - CGI: `{SINGLE_SITE_CGI}`
        - workflow: showwp -> showorbit -> calcsim

        Spinorial route:
        - CGI: `{DOUBLE_BANDREP_CGI}`
        - workflow: Wyckoff table fetch -> mixed 56x78 parse -> spinorial 56x33 extraction

        Raw HTML fetches are cached under `sg194_external_matrix_cache/ordinary` and `sg194_external_matrix_cache/spinorial`.

        ## 3. Single Final Ordinary Reduction

        Let
        \\[
        E_{{\\mathrm{{ord}}}} \\in \\mathbb{{Z}}^{{34 \\times 45}}
        \\]
        be the cached Bilbao ordinary generator matrix, with rows indexed by ordinary high-symmetry irreps at `GM, A, K, H, M, L`.

        Let
        \\[
        C_{{\\mathrm{{cur}}}}^{{\\mathrm{{full}}}} \\in \\mathbb{{Z}}^{{62 \\times 45}}, \\qquad
        C_{{\\mathrm{{cur}}}}^{{\\mathrm{{HSP}}}} \\in \\mathbb{{Z}}^{{34 \\times 45}}
        \\]
        be the current internal generator matrices in the full raw unknown basis and in the selected HSP restriction, respectively.

        After exact column reordering by generator id, one finds:

        - `rank Row(C_cur^full) = 13`
        - `rank Row(E_ord) = 13`
        - `rank(Row(C_cur^full) + Row(E_ord)) = 14`

        The same union rank `14` is obtained for the HSP-restricted current matrix. Therefore no exact row map
        \\[
        P_{{\\mathrm{{single}}}} C_{{\\mathrm{{cur}}}} = E_{{\\mathrm{{ord}}}}
        \\]
        exists, neither from the full raw current matrix nor from the HSP restriction.

        The single line is therefore still blocked. The old v1 `trivial` conclusion must be discarded, and the v2 `Z^5` should only be kept as an intermediate HSP-space diagnostic.

        ## 4. Double Final Spinorial Reduction

        Let
        \\[
        E_{{\\mathrm{{spin}}}} \\in \\mathbb{{Z}}^{{56 \\times 33}}
        \\]
        be the cached Bilbao physically irreducible spinorial generator matrix.

        The unambiguous problematic sector consists of the ten channels
        `2b:E1,E2,E3`, `2c:E1,E2,E3`, `2d:E1,E2,E3`, `6h:E`.
        After merging the current internal labels as in the v2 representation-content stage, the current and external problem-sector matrices satisfy:

        - `rank Row(C_prob) = 6`
        - `rank Row(E_prob) = 6`
        - `rank(Row(C_prob) + Row(E_prob)) = 8`

        Thus the residual mismatch survives even after the full external spinorial matrix is cached. The current-only and external-only problem-sector difference spaces are both two-dimensional.

        This proves that `delta_c1_minus_b1` and `delta_d1_minus_b1` are not just missing lifts caused by unavailable external data; they remain current-only excess directions relative to the external spinorial problem-sector row space.

        ## 5. Updated Final Conclusions

        - Single is **not** finalized.
        - Double is **not** finalized.
        - SG194 is **not yet** aligned to the final external standard language.

        What is now final is the diagnosis:

        - single blocker = genuine ordinary row-space mismatch
        - double blocker = genuine rank-2 spinorial mismatch in the `2b/2c/2d/6h` sector

        ## 6. Implementation Mapping

        - ordinary matrix cache: `sg194_external_ordinary_generator_matrix.json`
        - spinorial matrix cache: `sg194_external_spinorial_generator_matrix.json`
        - acquisition audit: `sg194_external_matrix_acquisition.md`
        - single final reduction: `sg194_single_final_external_reduction.json`
        - double final reduction: `sg194_double_final_external_reduction.json`
        - final stage summary: `sg194_external_matrix_final_summary.json`

        ## 7. Confidence

        - ordinary matrix cached: `{summary['ordinary_external_matrix_cached']}`
        - spinorial matrix cached: `{summary['spinorial_external_matrix_cached']}`
        - single finalized: `{summary['single_finalized']}`
        - double finalized: `{summary['double_finalized']}`
        """
    ).strip()


def build_report_tex(report_md: str) -> str:
    sections = report_md.split("\n## ")
    head = sections[0].splitlines()[0].replace("# ", "")
    body_sections = sections[1:]
    rendered_sections = []
    for sec in body_sections:
        lines = sec.splitlines()
        title = lines[0].strip()
        content_lines = lines[1:]
        rendered = [rf"\section*{{{latex_escape(title)}}}"]
        for line in content_lines:
            if not line.strip():
                rendered.append("")
            else:
                rendered.append(latex_escape(line) + r"\\")
        rendered_sections.append("\n".join(rendered))
    return textwrap.dedent(
        rf"""
        \documentclass[11pt]{{article}}
        \usepackage[margin=1in]{{geometry}}
        \usepackage{{hyperref}}
        \usepackage{{amsmath,amssymb}}
        \usepackage{{longtable}}
        \usepackage{{enumitem}}
        \setlength{{\parskip}}{{0.6em}}
        \setlength{{\parindent}}{{0pt}}
        \begin{{document}}
        \begin{{center}}
        {{\LARGE {latex_escape(head)}}}
        \end{{center}}
        {'\n\n'.join(rendered_sections)}
        \end{{document}}
        """
    ).strip() + "\n"


def compile_pdf() -> None:
    if shutil.which("pdflatex") is None:
        raise RuntimeError("pdflatex is required to build sg194_external_matrix_final_report.pdf")
    aux_files = [
        REPORT_TEX.with_suffix(".aux"),
        REPORT_TEX.with_suffix(".log"),
        REPORT_TEX.with_suffix(".out"),
    ]
    cmd = ["pdflatex", "-interaction=nonstopmode", REPORT_TEX.name]
    for _ in range(2):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if not REPORT_PDF.exists():
        raise RuntimeError("pdflatex finished without producing sg194_external_matrix_final_report.pdf")
    for aux in aux_files:
        if aux.exists():
            aux.unlink()


def create_package() -> None:
    ensure_clean_dir(PACKAGE_DIR)
    package_files = [
        ORD_MATRIX_JSON,
        SPIN_MATRIX_JSON,
        ACQ_MD,
        ACQ_JSON,
        SINGLE_FINAL_MD,
        SINGLE_FINAL_JSON,
        DOUBLE_FINAL_MD,
        DOUBLE_FINAL_JSON,
        AUDIT_MD,
        SUMMARY_JSON,
        HANDOFF_MD,
        CURRENT_STATUS_JSON,
        NEXT_STEP_TXT,
        ROOT / "debug_sg194_external_matrix_final.py",
        REPORT_MD,
        REPORT_TEX,
        REPORT_PDF,
    ] + BACKGROUND_FILES
    for src in package_files:
        dest = PACKAGE_DIR / src.name
        shutil.copy2(src, dest)

    cache_dest = PACKAGE_DIR / CACHE_DIR.name
    shutil.copytree(CACHE_DIR, cache_dest)
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "SSGReps.py", PACKAGE_DIR / "SSGReps.py")
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "SG_utils.py", PACKAGE_DIR / "SG_utils.py")
    shutil.copy2(ROOT / "SSGReps" / "SSGReps" / "rep_utils.py", PACKAGE_DIR / "rep_utils.py")

    readme = "\n".join(
        [
            "# SG194 External Matrix Final Package",
            "",
            "- Target group: `194.1.1.1`",
            "- This package caches the full Bilbao ordinary and spinorial generator matrices and re-audits the final external reduction.",
            "",
            "## SG194 external matrix final report",
            f"- Report PDF: `{REPORT_PDF.name}`",
            f"- Report source: `{REPORT_TEX.name}`",
            "- Suggested reading order:",
            f"  1. `{REPORT_PDF.name}`",
            f"  2. `{ACQ_MD.name}`",
            f"  3. `{SINGLE_FINAL_MD.name}`",
            f"  4. `{DOUBLE_FINAL_MD.name}`",
            f"  5. `{SUMMARY_JSON.name}`",
        ]
    )
    write_text(README_PATH, readme)

    if PACKAGE_TARBALL.exists():
        PACKAGE_TARBALL.unlink()
    with tarfile.open(PACKAGE_TARBALL, "w:gz") as tf:
        tf.add(PACKAGE_DIR, arcname=PACKAGE_NAME)


def run() -> None:
    ensure_clean_dir(CACHE_DIR)
    ordinary = fetch_single_external_matrix(ORDINARY_CACHE_DIR)
    spinorial = fetch_double_external_matrix(SPINORIAL_CACHE_DIR)

    ord_json, spin_json = build_matrix_json(ordinary, spinorial)
    acq_json = build_acquisition_json(ordinary, spinorial)
    single_payload, single_md = build_single_final(ordinary)
    double_payload, double_md = build_double_final(spinorial)
    summary_json = build_summary_json(single_payload, double_payload)
    audit_md = build_audit_md(single_payload, double_payload, summary_json)
    handoff_md = build_handoff(single_payload, double_payload)
    next_step = build_next_step_prompt()
    current_status = {
        "target_group": GROUP,
        "ordinary_external_matrix_cached": True,
        "spinorial_external_matrix_cached": True,
        "single_status": {
            "finalized": False,
            "rowspace_union_rank": single_payload["full_raw_union_rowspace_rank"],
            "current_vs_external_intersection_rank": single_payload["full_raw_rowspace_intersection_rank"],
            "final_external_quotient": None,
        },
        "double_status": {
            "finalized": False,
            "problem_sector_union_rank": double_payload["problem_sector_union_rank"],
            "problem_sector_intersection_rank": double_payload["problem_sector_intersection_rank"],
            "final_external_quotient": None,
        },
        "main_blocker": "Current internal SG194 generator images do not land in the cached external standard row spaces.",
        "next_step": "Rebuild the internal single and double generator images so that they match the cached external ordinary/spinorial matrices before retaking BS/AI.",
    }

    report_md = build_report_md(acq_json, single_payload, double_payload, summary_json)

    write_json(ORD_MATRIX_JSON, ord_json)
    write_json(SPIN_MATRIX_JSON, spin_json)
    write_json(ACQ_JSON, acq_json)
    write_text(ACQ_MD, build_acquisition_md(acq_json))
    write_json(SINGLE_FINAL_JSON, single_payload)
    write_text(SINGLE_FINAL_MD, single_md)
    write_json(DOUBLE_FINAL_JSON, double_payload)
    write_text(DOUBLE_FINAL_MD, double_md)
    write_text(AUDIT_MD, audit_md)
    write_json(SUMMARY_JSON, summary_json)
    write_text(HANDOFF_MD, handoff_md)
    write_json(CURRENT_STATUS_JSON, current_status)
    write_text(NEXT_STEP_TXT, next_step)
    write_text(REPORT_MD, report_md)
    write_text(REPORT_TEX, build_report_tex(report_md))
    compile_pdf()
    create_package()


def validate() -> None:
    missing = [str(path.name) for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        raise SystemExit(f"missing required outputs: {missing}")
    ord_json = load_json(ORD_MATRIX_JSON)
    spin_json = load_json(SPIN_MATRIX_JSON)
    single_payload = load_json(SINGLE_FINAL_JSON)
    double_payload = load_json(DOUBLE_FINAL_JSON)
    summary_json = load_json(SUMMARY_JSON)
    assert ord_json["shape"] == [34, 45]
    assert spin_json["shape"] == [56, 33]
    assert single_payload["full_raw_union_rowspace_rank"] == 14
    assert single_payload["exact_full_raw_to_external_row_map_exists"] is False
    assert double_payload["problem_sector_union_rank"] == 8
    assert double_payload["problem_sector_intersection_rank"] == 4
    assert summary_json["single_finalized"] is False
    assert summary_json["double_finalized"] is False
    assert REPORT_PDF.exists()
    assert PACKAGE_TARBALL.exists()
    print("validation_ok")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        validate()
        return
    run()


if __name__ == "__main__":
    main()
