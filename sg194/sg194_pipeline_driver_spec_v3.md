# Pipeline Driver Spec V3

- entrypoint: `sg194/run_group_pipeline.py`
- primary test groups: `sg194, 222.1.1.1`
- archived previous probe groups: `10.4.1.31`

## CLI Arguments

- `--group`
- `--mode single|double|both`
- `--row-language raw|target|all`
- `--output-dir`
- `--validate`
- `--build-package`

## Outputs

- `geometry_summary`
- `representation_alignment_summary`
- `bs_results`
- `ai_results`
- `quotient_results`
- `final_status_summary`
- `consistency_checks`
- `package_manifest`
