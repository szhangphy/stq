from __future__ import annotations

from functools import lru_cache
from typing import Any

from . import swyckoff_k as _swyckoff_k
from . import swyckoff_r as _swyckoff_r


COORDINATE_SYSTEM_A = "pre_supercell_nonmagnetic_primitive_basis_for_SSGReps_only"
COORDINATE_SYSTEM_B = "post_supercell_primitive_basis_for_pipeline_modules"


def coordinate_contract() -> dict[str, Any]:
    return {
        "coordinate_system_a": COORDINATE_SYSTEM_A,
        "coordinate_system_b": COORDINATE_SYSTEM_B,
        "a_owner_modules": ["common/SSGReps.py"],
        "b_owner_modules": ["sg194/pipeline_v2/**", "sg194/debug_*"],
        "conversion_authority": "common/swyckoff.py",
        "conversion_sources": {
            "kspace": {
                "module": "common/swyckoff_k.py",
                "functions": [
                    "to_reciprocal_op",
                    "primitive_matrix_from_centering",
                    "change_basis_ops",
                    "load_irssg_data",
                    "compute_wyckoff_output",
                ],
            },
            "realspace": {
                "module": "common/swyckoff_r.py",
                "functions": [
                    "primitive_matrix_from_centering",
                    "change_basis_ops",
                    "load_irssg_data",
                    "compute_wyckoff_output",
                ],
            },
        },
        "notes": [
            "Only SSGReps.py is allowed to work in coordinate system A.",
            "Pipeline modules must consume coordinate-system-B outputs only.",
            "No pipeline module should import swyckoff_k.py or swyckoff_r.py directly.",
        ],
    }


@lru_cache(maxsize=None)
def load_trusted_symmetry_payload(group_id: str, spin_id: int = 0) -> dict[str, Any]:
    payload, _ = _swyckoff_k.load_irssg_data(group_id, spin_id)
    return payload


@lru_cache(maxsize=None)
def load_kspace_wyckoff_output(group_id: str, fast: bool = True) -> tuple[list[dict[str, Any]], str]:
    return _swyckoff_k.compute_wyckoff_output(group_id, kspace=True, fast=fast)


@lru_cache(maxsize=None)
def load_realspace_wyckoff_output(group_id: str, fast: bool = True) -> tuple[list[dict[str, Any]], str]:
    return _swyckoff_r.compute_wyckoff_output(group_id, fast=fast)


def kspace_conversion_functions() -> dict[str, Any]:
    return {
        "to_reciprocal_op": _swyckoff_k.to_reciprocal_op.__name__,
        "primitive_matrix_from_centering": _swyckoff_k.primitive_matrix_from_centering.__name__,
        "change_basis_ops": _swyckoff_k.change_basis_ops.__name__,
    }


def realspace_conversion_functions() -> dict[str, Any]:
    return {
        "primitive_matrix_from_centering": _swyckoff_r.primitive_matrix_from_centering.__name__,
        "change_basis_ops": _swyckoff_r.change_basis_ops.__name__,
    }
