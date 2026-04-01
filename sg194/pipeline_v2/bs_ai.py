from __future__ import annotations

from typing import Any

from .models import GroupSpec
from .utils import now_iso


def build_result_objects(spec: GroupSpec, adapter, artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    return adapter.build_result_objects(spec, artifacts)


def filter_result_objects(records: list[dict[str, Any]], mode: str, row_language: str) -> list[dict[str, Any]]:
    selected = records
    if mode != "both":
        selected = [item for item in selected if item["mode"] == mode]
    if row_language != "all":
        selected = [item for item in selected if item["row_language_level"] == row_language]
    return selected


def build_bs_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "availability": item["availability"],
                "dBS": item["dBS"],
                "blocker": item.get("blocker"),
            }
            for item in records
        ],
    }


def build_ai_summary(records: list[dict[str, Any]], spec: GroupSpec) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "group": spec.group_id,
        "objects": [
            {
                "object_id": item["object_id"],
                "mode": item["mode"],
                "row_language_level": item["row_language_level"],
                "row_language_kind": item["row_language_kind"],
                "object_kind": item["object_kind"],
                "availability": item["availability"],
                "dAI": item["dAI"],
                "blocker": item.get("blocker"),
            }
            for item in records
        ],
    }
