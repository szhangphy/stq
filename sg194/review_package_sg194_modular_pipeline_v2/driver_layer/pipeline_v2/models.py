from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProducerCommand:
    label: str
    script_relpath: str
    validate_args: tuple[str, ...] = ("--validate",)
    refresh_args: tuple[str, ...] = ()
    note: str | None = None

    def command(self, repo_root: Path, refresh: bool) -> list[str]:
        script = repo_root / self.script_relpath
        args = self.refresh_args if refresh else self.validate_args
        return ["python3", str(script), *args]


@dataclass(frozen=True)
class GroupSpec:
    key: str
    group_id: str
    title: str
    description: str
    home_subdir: str
    adapter_key: str
    modes: tuple[str, ...]
    row_languages: tuple[str, ...]
    artifacts: dict[str, str]
    producer_commands: tuple[ProducerCommand, ...] = ()
    special_rules: dict[str, Any] = field(default_factory=dict)
    expected_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    benchmark: dict[str, Any] = field(default_factory=dict)
    final_object_ids: dict[str, str] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    trust_level: str = "declared_artifacts"
    runnable: bool = True
    readiness_note: str | None = None

    def home_dir(self, repo_root: Path) -> Path:
        return repo_root / self.home_subdir

    def repo_path(self, repo_root: Path, relpath: str) -> Path:
        return repo_root / relpath

    def artifact_path(self, repo_root: Path, key: str) -> Path:
        return self.repo_path(repo_root, self.artifacts[key])


@dataclass(frozen=True)
class PipelineRunConfig:
    group: str
    mode: str
    row_language: str
    output_dir: Path
    validate: bool
    build_package: bool
    refresh: bool
