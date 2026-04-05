from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GroupTargetSpec:
    group_id: str
    truth_compare_available: bool = False
    generic_builders_expected: bool = True
    require_same_shell_target_builder_for_generic_final: bool = True
    default_nonfinal_mode: str = "diagnostic_only"
    note: str | None = None


GROUP_TARGET_REGISTRY: dict[str, GroupTargetSpec] = {
    "194.1.1.1": GroupTargetSpec(
        group_id="194.1.1.1",
        truth_compare_available=True,
        generic_builders_expected=True,
        require_same_shell_target_builder_for_generic_final=True,
        note="Truth files are available for post-solve comparison only; the main solver must stay generic.",
    ),
    "99.1.1.1": GroupTargetSpec(
        group_id="99.1.1.1",
        truth_compare_available=False,
        generic_builders_expected=True,
        require_same_shell_target_builder_for_generic_final=True,
        note="Oracle-free control group; promotion requires a real generic same-shell published target builder.",
    ),
    "194.1.12.16": GroupTargetSpec(
        group_id="194.1.12.16",
        truth_compare_available=False,
        generic_builders_expected=True,
        require_same_shell_target_builder_for_generic_final=True,
        note="Generic BS-rank reference control for this round; used to verify the unified path has not regressed.",
    ),
    "159.1.6.2": GroupTargetSpec(
        group_id="159.1.6.2",
        truth_compare_available=True,
        generic_builders_expected=True,
        require_same_shell_target_builder_for_generic_final=True,
        note="Active generic extension target; compare-only external rank facts come from P31c (No. 159.61) with dBS=8 and dAI=8.",
    ),
}


def get_group_target_spec(group_id: str) -> GroupTargetSpec:
    return GROUP_TARGET_REGISTRY.get(
        group_id,
        GroupTargetSpec(
            group_id=group_id,
            truth_compare_available=False,
            generic_builders_expected=True,
            require_same_shell_target_builder_for_generic_final=True,
            note="Unregistered target-group; default to generic no-oracle policy.",
        ),
    )
