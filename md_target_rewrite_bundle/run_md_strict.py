#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    # Keep the CLI intentionally small: one command should be enough to run the
    # standalone md-style target without importing the live production package.
    parser = argparse.ArgumentParser(
        description="Run the standalone md-strict geometry workflow rewrite."
    )
    parser.add_argument("--group", required=True, help="SG or full SSG number, for example 34 or 34.1.231.1000")
    parser.add_argument(
        "--mode",
        choices=("single", "double"),
        default="single",
        help="Representation mode.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    parser.add_argument(
        "--include-generic",
        action="store_true",
        help="Include generic-position connectors explicitly. They are enabled by default.",
    )
    parser.add_argument(
        "--exclude-generic",
        action="store_true",
        help="Explicitly disable generic-position connectors.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write the JSON payload.",
    )
    args = parser.parse_args()

    bundle_root = Path(__file__).resolve().parent
    if str(bundle_root) not in sys.path:
        sys.path.insert(0, str(bundle_root))

    from sg194.pipeline_v2.md_target_rewrite import build_md_target_rewrite

    payload = build_md_target_rewrite(
        args.group,
        mode=args.mode,
        include_generic=(not args.exclude_generic),
    )
    json_text = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        if args.pretty
        else json.dumps(payload, ensure_ascii=False)
    )
    if args.output:
        Path(args.output).write_text(json_text + "\n", encoding="utf-8")
    print(json_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
