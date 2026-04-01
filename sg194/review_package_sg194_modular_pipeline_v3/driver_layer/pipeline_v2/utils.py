from __future__ import annotations

import datetime as dt
import json
import shutil
import tarfile
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def repo_rel(path: Path, repo_root: Path) -> str:
    return str(path.relative_to(repo_root))


def tar_directory(source_dir: Path, tarball: Path) -> None:
    if tarball.exists():
        tarball.unlink()
    with tarfile.open(tarball, "w:gz") as handle:
        handle.add(source_dir, arcname=source_dir.name)


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
