from __future__ import annotations

from .generic_diagnostic import GenericDiagnosticAdapter
from .sg194 import SG194Adapter
from .ssg222_1_1_1 import SSG2221111Adapter


ADAPTERS = {
    "generic_diagnostic": GenericDiagnosticAdapter(),
    "sg194": SG194Adapter(),
    "ssg222_generic_probe": SSG2221111Adapter(),
}


def get_adapter(key: str):
    try:
        return ADAPTERS[key]
    except KeyError as exc:
        raise KeyError(f"unsupported adapter: {key}") from exc
