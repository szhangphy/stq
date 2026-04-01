from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .models import GroupSpec
from .utils import load_json, repo_rel


def _run_checked(command: list[str], repo_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def ensure_legacy_state(spec: GroupSpec, repo_root: Path, refresh: bool) -> dict[str, Any]:
    if not spec.runnable:
        return {
            "mode": "template_only",
            "commands": [],
            "all_passed": True,
        }

    root_dir = spec.root_dir(repo_root)
    commands: list[dict[str, Any]] = []
    script_paths = [
        spec.script_path(repo_root, spec.legacy_scripts.projection_script),
        spec.script_path(repo_root, spec.legacy_scripts.stage2_script),
        spec.script_path(repo_root, spec.legacy_scripts.exact_alignment_script),
        spec.script_path(repo_root, spec.legacy_scripts.regression_script),
    ]
    for script in script_paths:
        if script is None:
            continue
        command = ["python3", repo_rel(script, repo_root)]
        if not refresh:
            command.append("--validate")
        commands.append(_run_checked(command, repo_root))
    return {
        "mode": "refresh" if refresh else "validate",
        "commands": commands,
        "all_passed": all(item["passed"] for item in commands),
        "root_dir": str(root_dir),
    }


def load_artifacts(spec: GroupSpec, repo_root: Path) -> dict[str, Any]:
    if not spec.runnable:
        return {}
    loaded: dict[str, Any] = {}
    for key, relpath in spec.artifacts.items():
        path = spec.root_dir(repo_root) / relpath
        if path.suffix == ".json" and path.exists():
            loaded[key] = load_json(path)
    return loaded
