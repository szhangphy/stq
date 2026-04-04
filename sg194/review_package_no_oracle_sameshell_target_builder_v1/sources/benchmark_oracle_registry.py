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
