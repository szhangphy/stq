from __future__ import annotations

from .models import GroupSpec


def special_rule_summary(spec: GroupSpec) -> dict[str, object]:
    return {
        "group_specific_rules": spec.special_rules,
        "group_specific_rule_count": len(spec.special_rules),
        "has_single_target_label_normalization": "single_target_label_normalization" in spec.special_rules,
    }
