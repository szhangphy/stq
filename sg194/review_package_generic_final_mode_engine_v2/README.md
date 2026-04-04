# Review Package: Generic Final Mode Engine v2

This package captures the group-driven engine state after upgrading the main flow to explicit result modes:
- `benchmark_aligned_final`
- `generic_final`
- `diagnostic_only`

Positive case:
- `194.1.1.1`: single = `trivial`, double = `Z6`, final mode = `benchmark_aligned_final`.

No-oracle control case:
- `99.1.1.1`: benchmark oracle unavailable, final mode = `diagnostic_only`, status = `not_final`.
- Current builder progress on 99: current row shell = available, local AI seed = available, compatibility builder = available.
- Current minimal blocker on 99: `generic_point_shell_projection_rank_loss` with `full=14`, `point=0`.

Key source files included:
- `sg194/pipeline_v2/group_target_registry.py`
- `sg194/pipeline_v2/benchmark_oracle_registry.py`
- `sg194/pipeline_v2/bs_ai.py`
- `sg194/pipeline_v2/alignment.py`
- `sg194/pipeline_v2/generic_builders.py`
- `sg194/pipeline_v2/checks.py`
- `sg194/pipeline_v2/adapters/generic_diagnostic.py`
- `scripts/run_group_classification_smoke_test.py`
