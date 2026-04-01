from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import swyckoff as swyckoff_bridge


COORDINATE_SYSTEM_A = swyckoff_bridge.COORDINATE_SYSTEM_A
COORDINATE_SYSTEM_B = swyckoff_bridge.COORDINATE_SYSTEM_B

A_ONLY_MODULES = ("common/SSGReps.py",)
CONVERSION_AUTHORITY_MODULE = "common/swyckoff.py"
B_ONLY_MODULES = (
    "sg194/pipeline_v2/models.py",
    "sg194/pipeline_v2/specs.py",
    "sg194/pipeline_v2/legacy_bridge.py",
    "sg194/pipeline_v2/geometry.py",
    "sg194/pipeline_v2/alignment.py",
    "sg194/pipeline_v2/bs_ai.py",
    "sg194/pipeline_v2/quotient.py",
    "sg194/pipeline_v2/checks.py",
    "sg194/pipeline_v2/reporting.py",
    "sg194/pipeline_v2/driver.py",
    "sg194/pipeline_v2/adapters/base.py",
    "sg194/pipeline_v2/adapters/sg194.py",
    "sg194/pipeline_v2/adapters/ssg222_1_1_1.py",
)

DIRECT_CONVERSION_IMPORT_PATTERNS = (
    re.compile(r"(^|\n)\s*import\s+swyckoff_k\b"),
    re.compile(r"(^|\n)\s*import\s+swyckoff_r\b"),
    re.compile(r"(^|\n)\s*from\s+common\s+import\s+swyckoff_k\b"),
    re.compile(r"(^|\n)\s*from\s+common\s+import\s+swyckoff_r\b"),
    re.compile(r"(^|\n)\s*from\s+common\.swyckoff_k\s+import\b"),
    re.compile(r"(^|\n)\s*from\s+common\.swyckoff_r\s+import\b"),
)

SSGREPS_IMPORT_PATTERNS = (
    re.compile(r"(^|\n)\s*import\s+SSGReps\b"),
    re.compile(r"(^|\n)\s*from\s+common\s+import\s+SSGReps\b"),
    re.compile(r"(^|\n)\s*from\s+common\.SSGReps\s+import\b"),
)

CORE_FAMILY_PATTERNS = (
    re.compile(r"\bhex\b"),
    re.compile(r"\bcubic\b"),
)


def coordinate_contract() -> dict[str, Any]:
    contract = swyckoff_bridge.coordinate_contract()
    contract["allowed_coordinate_a_modules"] = list(A_ONLY_MODULES)
    contract["allowed_coordinate_b_modules"] = list(B_ONLY_MODULES)
    contract["conversion_authority_module"] = CONVERSION_AUTHORITY_MODULE
    return contract


def load_trusted_symmetry_payload(group_id: str, spin_id: int = 0) -> dict[str, Any]:
    return swyckoff_bridge.load_trusted_symmetry_payload(group_id, spin_id=spin_id)


def build_kspace_geometry(group_id: str, fast: bool = True) -> dict[str, Any]:
    entries, coord_key = swyckoff_bridge.load_kspace_wyckoff_output(group_id, fast=fast)
    return {
        "coordinate_system": COORDINATE_SYSTEM_B,
        "coord_key": coord_key,
        "entries": entries,
        "space": "kspace",
    }


def build_realspace_geometry(group_id: str, fast: bool = True) -> dict[str, Any]:
    entries, coord_key = swyckoff_bridge.load_realspace_wyckoff_output(group_id, fast=fast)
    return {
        "coordinate_system": COORDINATE_SYSTEM_B,
        "coord_key": coord_key,
        "entries": entries,
        "space": "realspace",
    }


def _scan_text(path: Path) -> dict[str, Any]:
    rel = path.relative_to(REPO_ROOT)
    text = path.read_text()
    direct_conversion_hits = [pattern.pattern for pattern in DIRECT_CONVERSION_IMPORT_PATTERNS if pattern.search(text)]
    ssgreps_hits = [pattern.pattern for pattern in SSGREPS_IMPORT_PATTERNS if pattern.search(text)]
    family_hits = [pattern.pattern for pattern in CORE_FAMILY_PATTERNS if pattern.search(text)]
    return {
        "path": str(rel),
        "direct_conversion_hits": direct_conversion_hits,
        "ssgreps_hits": ssgreps_hits,
        "family_hits": family_hits,
    }


def coordinate_usage_audit() -> dict[str, Any]:
    scanned: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for relpath in B_ONLY_MODULES:
        path = REPO_ROOT / relpath
        if not path.exists():
            violations.append({"path": relpath, "problem": "missing_expected_module"})
            continue
        payload = _scan_text(path)
        scanned.append(payload)
        if payload["direct_conversion_hits"]:
            violations.append(
                {
                    "path": payload["path"],
                    "problem": "direct_swyckoff_k_or_r_import",
                    "hits": payload["direct_conversion_hits"],
                }
            )
        if payload["ssgreps_hits"]:
            violations.append(
                {
                    "path": payload["path"],
                    "problem": "direct_ssgreps_import_outside_a_owner",
                    "hits": payload["ssgreps_hits"],
                }
            )
        if payload["family_hits"]:
            violations.append(
                {
                    "path": payload["path"],
                    "problem": "family_name_dependency_in_core",
                    "hits": payload["family_hits"],
                }
            )
    return {
        "coordinate_system_a": COORDINATE_SYSTEM_A,
        "coordinate_system_b": COORDINATE_SYSTEM_B,
        "conversion_authority_module": CONVERSION_AUTHORITY_MODULE,
        "a_only_modules": list(A_ONLY_MODULES),
        "b_only_modules": list(B_ONLY_MODULES),
        "scanned_modules": scanned,
        "violations": violations,
        "all_passed": not violations,
    }
