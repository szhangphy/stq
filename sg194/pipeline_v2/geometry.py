from __future__ import annotations

from typing import Any

from .models import GroupSpec


def build_geometry_summary(spec: GroupSpec, adapter, artifacts: dict[str, Any]) -> dict[str, Any]:
    return adapter.build_geometry_summary(spec, artifacts)
