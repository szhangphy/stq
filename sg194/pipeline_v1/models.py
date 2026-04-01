from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LegacyScriptSet:
    stage1_script: str | None = None
    stage2_script: str | None = None
    projection_script: str | None = None
    exact_alignment_script: str | None = None
    pairing_proof_script: str | None = None
    regression_script: str | None = None


@dataclass(frozen=True)
class GroupSpec:
    key: str
    group_id: str
    title: str
    description: str
    root_subdir: str
    modes: tuple[str, ...]
    row_languages: tuple[str, ...]
    artifacts: dict[str, str]
    legacy_scripts: LegacyScriptSet
    special_rules: dict[str, Any] = field(default_factory=dict)
    expected_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    benchmark: dict[str, Any] = field(default_factory=dict)
    runnable: bool = True
    readiness_note: str | None = None

    def root_dir(self, repo_root: Path) -> Path:
        return repo_root / self.root_subdir

    def artifact_path(self, repo_root: Path, key: str) -> Path:
        return self.root_dir(repo_root) / self.artifacts[key]

    def script_path(self, repo_root: Path, relpath: str | None) -> Path | None:
        if relpath is None:
            return None
        return self.root_dir(repo_root) / relpath


@dataclass(frozen=True)
class PipelineRunConfig:
    group: str
    mode: str
    row_language: str
    output_dir: Path
    validate: bool
    build_package: bool
    refresh: bool
