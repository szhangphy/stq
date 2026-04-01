# SG194 Modularization Plan v1

- Keep geometry and accepted-status production in the SG194 legacy backend for now.
- Normalize outputs through `pipeline_v1/*` and route all orchestration through `run_group_pipeline.py`.
- Use `GroupSpec` plus a template spec as the extension surface for future groups.
