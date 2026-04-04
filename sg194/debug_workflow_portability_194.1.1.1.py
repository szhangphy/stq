#!/usr/bin/env python3
"""Thin wrapper around the authoritative SG194 runtime backend.

This legacy entrypoint is kept only so existing scripts and review workflows can
continue invoking ``debug_workflow_portability_194.1.1.1.py``. All real logic
now lives in ``pipeline_v2.runtime_backend_free`` so the debug driver cannot
drift from the authoritative single/double quotient implementation.
"""

from __future__ import annotations

from pipeline_v2 import runtime_backend_free as _runtime

run = _runtime.run
validate_outputs = _runtime.validate_outputs
build_package = _runtime.build_package
build_current_status = _runtime.build_current_status
build_next_step_prompt = _runtime.build_next_step_prompt
build_handoff = _runtime.build_handoff
build_package_readme = _runtime.build_package_readme
print_terminal_summary = _runtime.print_terminal_summary
main = _runtime.main


if __name__ == "__main__":
    main()
