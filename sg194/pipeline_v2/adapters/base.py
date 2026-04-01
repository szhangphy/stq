from __future__ import annotations

from typing import Any, Protocol

from ..models import GroupSpec


class GroupAdapter(Protocol):
    def build_geometry_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]: ...

    def build_alignment_summary(self, spec: GroupSpec, artifacts: dict[str, Any]) -> dict[str, Any]: ...

    def build_result_objects(self, spec: GroupSpec, artifacts: dict[str, Any]) -> list[dict[str, Any]]: ...

    def build_final_status(self, spec: GroupSpec, artifacts: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]: ...

    def build_extra_checks(
        self,
        spec: GroupSpec,
        artifacts: dict[str, Any],
        geometry: dict[str, Any],
        alignment: dict[str, Any],
        records: list[dict[str, Any]],
        final_status: dict[str, Any],
    ) -> list[dict[str, Any]]: ...
