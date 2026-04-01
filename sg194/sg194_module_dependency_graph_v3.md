# Module Dependency Graph V3

- `run_group_pipeline.py` -> `sg194/pipeline_v2/driver.py`
- `sg194/pipeline_v2/driver.py` -> `sg194/pipeline_v2/specs.py, sg194/pipeline_v2/geometry.py, sg194/pipeline_v2/alignment.py, sg194/pipeline_v2/bs_ai.py, sg194/pipeline_v2/quotient.py, sg194/pipeline_v2/checks.py, sg194/pipeline_v2/reporting.py, sg194/pipeline_v2/legacy_bridge.py, sg194/pipeline_v2/adapters/__init__.py`
- `sg194/pipeline_v2/geometry.py` -> `sg194/pipeline_v2/coordinates.py`
- `sg194/pipeline_v2/alignment.py` -> `sg194/pipeline_v2/coordinates.py`
- `sg194/pipeline_v2/checks.py` -> `sg194/pipeline_v2/coordinates.py`
- `sg194/pipeline_v2/coordinates.py` -> `common/swyckoff.py`
- `common/swyckoff.py` -> `common/swyckoff_k.py, common/swyckoff_r.py`
