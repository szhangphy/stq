#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from kgeometry_single import build_demo_text, write_outputs


def main() -> int:
    manifolds, connectivity = write_outputs(Path(".").resolve())
    print(build_demo_text(manifolds, connectivity), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
