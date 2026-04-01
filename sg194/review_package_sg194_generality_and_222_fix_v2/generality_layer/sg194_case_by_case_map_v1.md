# Case By Case Map

- `sg194/pipeline_v2/specs.py` / `SG194_SPEC`: `accepted_special_case` because `expected_results, benchmark, producer_commands, and special_rules are hardcoded for SG194.`
- `sg194/pipeline_v2/specs.py` / `GROUP222_SPEC`: `case_by_case_probe_spec` because `identity map, oracle artifacts, and producer commands are explicit per-group wiring.`
- `sg194/pipeline_v2/generic_builders.py` / `shared_geometry_bundle / _build_generic_compatibility / _build_local_irrep_library`: `fake_generic_bridge` because `all three still route through SG194 stage1/backend helper code.`
