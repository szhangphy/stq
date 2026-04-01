from __future__ import annotations

from .sg194 import SG194Adapter
from .ssg10_4_1_31 import SSG104131OpsOnlyAdapter


ADAPTERS = {
    "sg194": SG194Adapter(),
    "ssg10_ops_only": SSG104131OpsOnlyAdapter(),
}


def get_adapter(key: str):
    try:
        return ADAPTERS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported adapter: {key}") from exc
