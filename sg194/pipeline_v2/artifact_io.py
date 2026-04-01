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


def ensure_producer_state(spec: GroupSpec, repo_root: Path, refresh: bool) -> dict[str, Any]:
    if spec.builder_backend == "generic_symmetry_ops":
        return {
            "mode": "backend_free_generic_runtime",
            "commands": [],
            "all_passed": True,
        }
    if not spec.producer_commands:
        return {
            "mode": "no_producers",
            "commands": [],
            "all_passed": True,
        }
    commands = [
        _run_checked(producer.command(repo_root, refresh), repo_root)
        for producer in spec.producer_commands
    ]
    return {
        "mode": "refresh" if refresh else "validate",
        "commands": commands,
        "all_passed": all(item["passed"] for item in commands),
    }


def load_artifacts(spec: GroupSpec, repo_root: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for key, relpath in spec.artifacts.items():
        path = repo_root / relpath
        if path.suffix == ".json" and path.exists():
            loaded[key] = load_json(path)
        elif path.suffix == ".md" and path.exists():
            loaded[key] = path.read_text()
    loaded["_artifact_paths"] = {
        key: repo_rel(repo_root / relpath, repo_root)
        for key, relpath in spec.artifacts.items()
    }
    return loaded
