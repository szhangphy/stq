#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path


def decode_complex(payload):
    if isinstance(payload, dict):
        if set(payload.keys()) == {"real", "imag"} and all(isinstance(payload[key], (int, float)) for key in ("real", "imag")):
            return complex(payload["real"], payload["imag"])
        return {key: decode_complex(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [decode_complex(value) for value in payload]
    return payload


REPO_ROOT = Path(__file__).resolve().parents[4]
source = subprocess.run(
    ["git", "show", "HEAD:sg194/debug_workflow_portability_194.1.1.1.py"],
    cwd=REPO_ROOT,
    capture_output=True,
    text=True,
    check=True,
).stdout
module = types.ModuleType("sg194_stage1_debug_original")
module.__file__ = str(REPO_ROOT / "sg194" / "debug_workflow_portability_194.1.1.1.py")
exec(compile(source, module.__file__, "exec"), module.__dict__)
connectivity = json.loads((REPO_ROOT / "sg194/group_194_1_1_1_single_connectivity.json").read_text())
l1 = next(item for item in connectivity["objects"] if item.get("id") == "L1")
captures = decode_complex(json.loads((REPO_ROOT / "sg194/group_194_1_1_1_single_little_groups.json").read_text()))
module.build_line_block(l1, captures, phase_aware_profile=module.AUTHORITATIVE_PHASE_AWARE_PROFILE)
