from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import sympy as sp
from sympy.matrices.normalforms import smith_normal_form

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from sg194.pipeline_v2.utils import now_iso, write_json, write_text

SG194_DIR = REPO_ROOT / "sg194"
SOURCE_ROOT = Path("/data/home/szhang/soft_sz/topmat_src")
COPY_ROOT = SG194_DIR / "external_oracles" / "topmat_src_copy_v1"
OUTPUT_DIR = SG194_DIR


def copy_oracle_files() -> dict[str, object]:
    files = [
        SOURCE_ROOT / "BilBaoData" / "msginfo",
        SOURCE_ROOT / "BilBaoData" / "output" / "Lindex_222.98.txt",
        SOURCE_ROOT / "BilBaoData" / "output" / "basis_222.98.txt",
        SOURCE_ROOT / "BilBaoData" / "output" / "MsgAI_222.98.txt",
        SOURCE_ROOT / "BilBaoData" / "output" / "OrigAI_222.98.txt",
    ]
    entries = []
    for src in files:
        rel = src.relative_to(SOURCE_ROOT)
        dst = COPY_ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        entries.append(
            {
                "source": str(src),
                "copied_to": str(dst),
                "modified_after_copy": False,
            }
        )
    return {
        "generated_at": now_iso(),
        "copied_root": str(COPY_ROOT),
        "entries": entries,
        "modified_files_after_copy": [],
    }


def parse_basis(path: Path) -> tuple[list[int], list[tuple[str, list[int]]]]:
    lines = [line.rstrip() for line in path.read_text().splitlines() if line.strip()]
    dims = [int(token) for token in lines[0].split()]
    rows: list[tuple[str, list[int]]] = []
    for line in lines[2:]:
        parts = line.split()
        rows.append((parts[0], [int(token) for token in parts[1:]]))
    return dims, rows


def parse_ai(path: Path) -> tuple[list[int], list[tuple[str, list[int]]], list[str]]:
    lines = path.read_text().splitlines()
    header = [int(token) for token in lines[0].split()]
    nrows = header[1]
    rows: list[tuple[str, list[int]]] = []
    index = 1
    while len(rows) < nrows and index < len(lines):
        line = lines[index].rstrip()
        if not line.strip():
            break
        parts = line.split()
        rows.append((parts[0], [int(token) for token in parts[1:]]))
        index += 1
    labels = [line.strip() for line in lines[index + 1 :] if line.strip()]
    return header, rows, labels


def parse_msginfo_line() -> str:
    for line in (COPY_ROOT / "BilBaoData" / "msginfo").read_text().splitlines():
        if "222.1.1601" in line:
            return line.rstrip()
    raise RuntimeError("unable to find 222.1.1601 in copied topmat msginfo")


def classification_string(free_rank: int, finite_part: list[int]) -> str:
    if free_rank == 0 and not finite_part:
        return "trivial"
    parts: list[str] = []
    if free_rank == 1:
        parts.append("Z")
    elif free_rank > 1:
        parts.append(f"Z^{free_rank}")
    parts.extend(f"Z{value}" for value in finite_part)
    return " x ".join(parts)


def build_oracle_result() -> dict[str, object]:
    _, basis_rows = parse_basis(COPY_ROOT / "BilBaoData" / "output" / "basis_222.98.txt")
    _, msgai_rows, msgai_labels = parse_ai(COPY_ROOT / "BilBaoData" / "output" / "MsgAI_222.98.txt")
    _, origai_rows, _ = parse_ai(COPY_ROOT / "BilBaoData" / "output" / "OrigAI_222.98.txt")

    basis_matrix = sp.Matrix([values for _, values in basis_rows])
    msgai_matrix = sp.Matrix([values for _, values in msgai_rows])
    coords: list[list[int]] = []
    failures: list[dict[str, object]] = []
    for column in range(msgai_matrix.cols):
        vector = msgai_matrix[:, column]
        try:
            solution, parameters = basis_matrix.gauss_jordan_solve(vector)
            if parameters.free_symbols:
                failures.append(
                    {
                        "column": column,
                        "label": msgai_labels[column] if column < len(msgai_labels) else None,
                        "reason": "parametric_solution",
                    }
                )
                continue
            coord = []
            ok = True
            for entry in solution:
                if getattr(entry, "q", 1) != 1:
                    failures.append(
                        {
                            "column": column,
                            "label": msgai_labels[column] if column < len(msgai_labels) else None,
                            "reason": f"non_integral:{entry}",
                        }
                    )
                    ok = False
                    break
                coord.append(int(entry))
            if ok:
                coords.append(coord)
        except Exception as exc:  # pragma: no cover - diagnostic path
            failures.append(
                {
                    "column": column,
                    "label": msgai_labels[column] if column < len(msgai_labels) else None,
                    "reason": str(exc),
                }
            )
    coords_matrix = sp.Matrix(coords).T if coords else sp.zeros(basis_matrix.cols, 0)
    smith = smith_normal_form(coords_matrix, domain=sp.ZZ)
    diagonal = []
    for index in range(min(smith.rows, smith.cols)):
        value = abs(int(smith[index, index]))
        if value:
            diagonal.append(value)
    finite_part = [value for value in diagonal if value > 1]
    free_rank = int(basis_matrix.rank()) - len(diagonal)
    return {
        "generated_at": now_iso(),
        "group": "222.1.1.1",
        "equivalent_og_object": "222.1.1601",
        "equivalent_topmat_msg_key": "222.98",
        "oracle_scope": "unified_og_object_not_mode_split",
        "mode_split_supported": False,
        "supports_final_classification": True,
        "basis_file": "sg194/external_oracles/topmat_src_copy_v1/BilBaoData/output/basis_222.98.txt",
        "msgai_file": "sg194/external_oracles/topmat_src_copy_v1/BilBaoData/output/MsgAI_222.98.txt",
        "origai_file": "sg194/external_oracles/topmat_src_copy_v1/BilBaoData/output/OrigAI_222.98.txt",
        "msginfo_line": parse_msginfo_line(),
        "basis_shape": [int(basis_matrix.rows), int(basis_matrix.cols)],
        "basis_rank": int(basis_matrix.rank()),
        "msgai_shape": [int(msgai_matrix.rows), int(msgai_matrix.cols)],
        "msgai_row_labels_match_basis": [row[0] for row in msgai_rows] == [row[0] for row in basis_rows],
        "origai_shape": [len(origai_rows), len(origai_rows[0][1]) if origai_rows else 0],
        "origai_row_labels_match_basis": [row[0] for row in origai_rows] == [row[0] for row in basis_rows],
        "dBS": int(basis_matrix.rank()),
        "dAI": len(diagonal),
        "classification": classification_string(free_rank, finite_part),
        "smith_diagonal_nonzero": diagonal,
        "finite_part": finite_part,
        "free_rank": free_rank,
        "ai_candidate_count": int(msgai_matrix.cols),
        "ai_candidate_count_used": int(coords_matrix.cols),
        "ai_failures": failures,
        "origai_note": "OrigAI_222.98.txt is not directly comparable to basis_222.98.txt because its row labels do not match the basis row language.",
    }


def write_md_files(identity: dict[str, object], oracle: dict[str, object], copy_log: dict[str, object]) -> None:
    write_text(
        OUTPUT_DIR / "sg194_222_og1601_identity_map_v1.md",
        "\n".join(
            [
                "# 222 / OG1601 Identity Map",
                "",
                f"- target group id: `{identity['target_group_id']}`",
                f"- equivalent OG object: `{identity['equivalent_og_object']}`",
                f"- equivalent topmat key: `{identity['equivalent_topmat_msg_key']}`",
                f"- relation: `{identity['relation']}`",
                f"- msginfo line: `{identity['msginfo_line']}`",
            ]
        ),
    )
    write_text(
        OUTPUT_DIR / "sg194_topmat_oracle_from_copy_v1.md",
        "\n".join(
            [
                "# Topmat Oracle From Copy",
                "",
                f"- group: `{oracle['group']}`",
                f"- equivalent OG object: `{oracle['equivalent_og_object']}`",
                f"- oracle scope: `{oracle['oracle_scope']}`",
                f"- mode split supported: `{oracle['mode_split_supported']}`",
                f"- dBS: `{oracle['dBS']}`",
                f"- dAI: `{oracle['dAI']}`",
                f"- classification: `{oracle['classification']}`",
                f"- smith nonzero diagonal: `{oracle['smith_diagonal_nonzero']}`",
                f"- MsgAI row labels match basis: `{oracle['msgai_row_labels_match_basis']}`",
                f"- supports final classification: `{oracle['supports_final_classification']}`",
                f"- note: `{oracle['origai_note']}`",
            ]
        ),
    )
    write_text(
        OUTPUT_DIR / "sg194_topmat_copy_modification_log_v1.md",
        "\n".join(
            [
                "# Topmat Copy Modification Log",
                "",
                f"- copied root: `{copy_log['copied_root']}`",
                f"- modified after copy: `{copy_log['modified_files_after_copy']}`",
                "",
                *[
                    f"- copied: `{entry['source']}` -> `{entry['copied_to']}`"
                    for entry in copy_log["entries"]
                ],
            ]
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    copy_log = copy_oracle_files()
    identity = {
        "generated_at": now_iso(),
        "target_group_id": "222.1.1.1",
        "equivalent_og_object": "222.1.1601",
        "equivalent_topmat_msg_key": "222.98",
        "relation": "same_object",
        "msginfo_line": parse_msginfo_line(),
    }
    oracle = build_oracle_result()

    write_json(OUTPUT_DIR / "sg194_topmat_copy_modification_log_v1.json", copy_log)
    write_json(OUTPUT_DIR / "sg194_222_og1601_identity_map_v1.json", identity)
    write_json(OUTPUT_DIR / "sg194_topmat_oracle_from_copy_v1.json", oracle)
    write_md_files(identity, oracle, copy_log)

    if args.validate:
        if not oracle["msgai_row_labels_match_basis"]:
            raise SystemExit("MsgAI row labels do not match basis rows for topmat oracle")
        if oracle["dBS"] != oracle["dAI"]:
            raise SystemExit("topmat oracle unexpectedly produced dBS != dAI")
        if oracle["classification"] is None:
            raise SystemExit("topmat oracle classification missing")


if __name__ == "__main__":
    main()
