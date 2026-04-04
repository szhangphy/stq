from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkOracleSpec:
    target_group: str
    benchmark_status_file: str | None
    benchmark_verdict_file: str | None
    source_kind: str
    expected_classification: str | None = None
    truth_compare_only: bool = True


GROUP_BENCHMARK_ORACLE_REGISTRY: dict[str, BenchmarkOracleSpec] = {
    "194.1.1.1": BenchmarkOracleSpec(
        target_group="194.1.1.1",
        benchmark_status_file="sg194/current_status_1941111_benchmark_v1.json",
        benchmark_verdict_file="sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json",
        source_kind="benchmark_oracle_exact_double_spinorial_alignment",
        expected_classification="Z6",
    ),
}


def get_benchmark_oracle_spec(target_group: str) -> BenchmarkOracleSpec | None:
    return GROUP_BENCHMARK_ORACLE_REGISTRY.get(target_group)


def benchmark_oracle_available(target_group: str) -> bool:
    return get_benchmark_oracle_spec(target_group) is not None


def truth_compare_available(target_group: str) -> bool:
    return get_benchmark_oracle_spec(target_group) is not None


def benchmark_oracle_source_kind(target_group: str) -> str | None:
    spec = get_benchmark_oracle_spec(target_group)
    return None if spec is None else spec.source_kind


def load_group_benchmark_oracle(
    repo_root: Path,
    target_group: str,
) -> dict[str, Any] | None:
    spec = get_benchmark_oracle_spec(target_group)
    if spec is None or spec.benchmark_verdict_file is None:
        return None

    verdict_path = repo_root / spec.benchmark_verdict_file
    verdict = json.loads(verdict_path.read_text())

    benchmark_status = None
    if spec.benchmark_status_file is not None:
        benchmark_status_path = repo_root / spec.benchmark_status_file
        benchmark_status = json.loads(benchmark_status_path.read_text())

    compute = verdict["source_breakdown"]["copied_experimental_compute"]
    raw_ai_in_bs_coordinates = compute["ai_in_bs_coordinates"]
    raw_ai_in_bs_shape = list(compute["ai_in_bs_shape"])
    raw_matrix_shape = [
        len(raw_ai_in_bs_coordinates),
        len(raw_ai_in_bs_coordinates[0]) if raw_ai_in_bs_coordinates else 0,
    ]
    expected_classification = str(
        compute.get("classification")
        or compute.get("indicator_group")
        or (benchmark_status or {}).get("benchmark_result", {}).get("indicator_group")
        or spec.expected_classification
    )
    expected_snf_diagonal = list(
        compute.get("basis_invariants_from_file")
        or (benchmark_status or {}).get("benchmark_result", {}).get("smith_diagonal_nonzero")
        or []
    )
    return {
        "target_group": target_group,
        "source_kind": spec.source_kind,
        "truth_compare_only": spec.truth_compare_only,
        "registry_status": "registered",
        "benchmark_status_file": spec.benchmark_status_file,
        "benchmark_verdict_file": spec.benchmark_verdict_file,
        "classification_reference_source": (
            f"{Path(spec.benchmark_verdict_file).name}::source_breakdown.copied_experimental_compute"
        ),
        "raw_ai_in_bs_coordinates": raw_ai_in_bs_coordinates,
        "raw_ai_in_bs_shape": raw_ai_in_bs_shape,
        "raw_matrix_shape": raw_matrix_shape,
        "expected_snf_diagonal": expected_snf_diagonal,
        "expected_classification": expected_classification,
        "expected_dAI": int(compute["dAI"]),
        "expected_dBS": int(compute["dBS"]),
    }


def load_group_truth_reference(
    repo_root: Path,
    target_group: str,
) -> dict[str, Any] | None:
    spec = get_benchmark_oracle_spec(target_group)
    if spec is None:
        return None

    status_payload = None
    verdict_payload = None
    if spec.benchmark_status_file is not None:
        status_payload = json.loads((repo_root / spec.benchmark_status_file).read_text())
    if spec.benchmark_verdict_file is not None:
        verdict_payload = json.loads((repo_root / spec.benchmark_verdict_file).read_text())

    published_source = (
        ((status_payload or {}).get("source_workflow_alignment") or {}).get("published_source_result")
        or {}
    )
    single_truth = published_source.get("single_target_result") or {}
    double_truth = (
        published_source.get("double_internalized_result")
        or ((status_payload or {}).get("benchmark_result") or {})
        or ((verdict_payload or {}).get("benchmark_result") or {})
    )
    return {
        "target_group": target_group,
        "truth_compare_only": spec.truth_compare_only,
        "source_kind": spec.source_kind,
        "status_file": spec.benchmark_status_file,
        "verdict_file": spec.benchmark_verdict_file,
        "single_truth": {
            "dBS": single_truth.get("dBS"),
            "dAI": single_truth.get("dAI"),
            "classification": single_truth.get("classification"),
        },
        "double_truth": {
            "dBS": double_truth.get("dBS"),
            "dAI": double_truth.get("dAI"),
            "classification": double_truth.get("classification") or double_truth.get("indicator_group"),
        },
    }
