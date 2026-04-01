# Generality Verdict

- verdict: `not_truly_general`
- reason: `The current pipeline_v2 still mixes truly generic modules with case-by-case registry logic and fake-generic SG194 backend bridges.`

- truly generic parts:
  - `pipeline_v2/models.py data containers`
  - `pipeline_v2/coordinates.py coordinate policy gate for A/B conversions`
  - `pipeline_v2/reporting.py output writing`
  - `pipeline_v2/driver.py orchestration shell`
- SG194-specific parts:
  - `pipeline_v2/specs.py::SG194_SPEC expected_results and benchmark contract`
  - `pipeline_v2/adapters/sg194.py single j/k canonical pairing`
  - `pipeline_v2/adapters/sg194.py benchmark-facing double semantics`
- fake-generic parts:
  - `sg194/pipeline_v2/generic_builders.py` / `STAGE1_BACKEND / stage1_backend()`: `directly imports debug_workflow_portability_194.1.1.1.py`
  - `sg194/pipeline_v2/generic_builders.py` / `LOCAL_LIBRARY_BACKEND / local_library_backend()`: `directly imports debug_sg194_nonabelian_local_library.py`
  - `sg194/pipeline_v2/specs.py` / `GROUP222_SPEC registry entry`: `second-group onboarding is still a case-by-case registry object rather than auto-discovered spec ingestion`
