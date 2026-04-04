from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroupTargetSpec:
    group_id: str
    benchmark_available: bool
    generic_builders_expected: bool = True
    expected_final_mode_when_benchmark_available: str = "benchmark_aligned_final"
    no_oracle_default_mode: str = "diagnostic_only"
    note: str | None = None


GROUP_TARGET_REGISTRY: dict[str, GroupTargetSpec] = {
    "194.1.1.1": GroupTargetSpec(
        group_id="194.1.1.1",
        benchmark_available=True,
        generic_builders_expected=False,
        note="Accepted benchmark-aligned positive case.",
    ),
    "99.1.1.1": GroupTargetSpec(
        group_id="99.1.1.1",
        benchmark_available=False,
        generic_builders_expected=True,
        note="Oracle-free control group; must not be promoted to published final without a real generic final builder.",
    ),
}


def get_group_target_spec(group_id: str) -> GroupTargetSpec:
    return GROUP_TARGET_REGISTRY.get(
        group_id,
        GroupTargetSpec(
            group_id=group_id,
            benchmark_available=False,
            generic_builders_expected=True,
            note="Unregistered target-group; default to generic no-oracle policy.",
        ),
    )
