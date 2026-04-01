# SG194 Module Dependency Graph v1

- `run_group_pipeline.py` -> `pipeline_v1/driver.py` is the only public entry edge.
- `pipeline_v1/driver.py` orchestrates legacy validation, summaries, checks, and reporting.
- SG194-specific forensic scripts remain behind the legacy backend boundary.
