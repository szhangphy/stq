# Unified Pipeline Call Graph

## Active Unified Entry

```text
python -m sg194.run_group_pipeline --group <group_id> --mode both --row-language all [--build-package]
  -> sg194/run_group_pipeline.py: main
  -> sg194/pipeline_v2/driver.py: main
  -> sg194/pipeline_v2/driver.py: run_pipeline
     -> sg194/pipeline_v2/specs.py: get_group_spec
     -> sg194/pipeline_v2/adapters/__init__.py: get_adapter
     -> sg194/pipeline_v2/artifact_io.py: ensure_producer_state
     -> sg194/pipeline_v2/artifact_io.py: load_artifacts
     -> sg194/pipeline_v2/geometry.py: build_geometry_summary
        -> sg194/pipeline_v2/generic_builders.py: generic_geometry_summary
     -> sg194/pipeline_v2/alignment.py: build_alignment_summary
        -> sg194/pipeline_v2/generic_builders.py: generic_alignment_summary
           -> sg194/pipeline_v2/generic_builders.py: generic_mode_progress
              -> shared_geometry_bundle
              -> _build_generic_compatibility
              -> _build_same_shell_target_row_language
              -> _build_same_shell_target_quotient
              -> _build_generic_same_shell_target_object
     -> sg194/pipeline_v2/bs_ai.py: build_result_objects
        -> sg194/pipeline_v2/generic_builders.py: generic_result_objects
        -> sg194/pipeline_v2/bs_ai.py: _annotate_result_mode
     -> sg194/pipeline_v2/bs_ai.py: filter_result_objects
     -> sg194/pipeline_v2/bs_ai.py: build_bs_summary
     -> sg194/pipeline_v2/bs_ai.py: build_ai_summary
     -> sg194/pipeline_v2/quotient.py: build_quotient_summary
     -> adapter.build_final_status
     -> sg194/pipeline_v2/truth_compare.py: build_truth_compare_report
        -> sg194/pipeline_v2/benchmark_oracle_registry.py: load_group_truth_reference
     -> sg194/pipeline_v2/checks.py: build_consistency_checks
     -> sg194/pipeline_v2/reporting.py: write_pipeline_outputs
     -> sg194/pipeline_v2/reporting.py: finalize_output_package
```

## Compare-Only Path

```text
driver.run_pipeline
  -> build_truth_compare_report(repo_root, group_id, records)
     -> load_group_truth_reference(repo_root, group_id)
        -> load compare-only JSON or full truth files
```

Compare-only 路径发生在 `final_status` 之后；它消费 solver records，但不反向写回 solver builder。

## Result Object Write Points

```text
target dBS/dAI/classification
  -> generic_builders._build_same_shell_target_quotient
  -> generic_builders._build_generic_same_shell_target_object
  -> generic_builders.generic_result_objects
  -> bs_ai.build_result_objects
  -> adapter.build_final_status
```
