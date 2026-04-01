from __future__ import annotations

from .models import GroupSpec
from .utils import now_iso


def build_quotient_summary(records: list[dict[str, object]], spec: GroupSpec) -> dict[str, object]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "builder_prerequisites": [
            {
                "object_id": item["object_id"],
                "current_row_shell_status": item.get("current_row_shell_status"),
                "local_ai_seed_status": item.get("local_ai_seed_status"),
                "quotient_prerequisites_status": item.get("quotient_prerequisites_status"),
            }
            for item in records
            if item.get("current_row_shell_status") is not None
        ],
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "availability": item["availability"],
                "classification": item["classification"],
                "free_rank": item["free_rank"],
                "finite_part": item["finite_part"],
                "quotient_derivation_mode": item["quotient_derivation_mode"],
                "exact_alignment_status": item["exact_alignment_status"],
                "quotient_prerequisites_status": item.get("quotient_prerequisites_status"),
                "blocker": item.get("blocker"),
            }
            for item in records
        ],
    }
