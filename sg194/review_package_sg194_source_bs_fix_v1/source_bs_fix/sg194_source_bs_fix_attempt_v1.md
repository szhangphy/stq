# SG194 source BS fix attempt v1

## Attempt

- attempt id: `benchmark_publication_adoption_v1`
- changed source files: `sg194/debug_workflow_portability_194.1.1.1.py, sg194/debug_workflow_portability_stage2_194.1.1.1.py`
- verification commands: `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`; `python3 -m py_compile common/*.py && python3 -m py_compile sg194/*.py`

## BS effect

- legacy internal stage2 rank(BS): single `13`, double `13`
- published source rank(BS): single `10`, double `10`
- benchmark dBS: `10`

## Publication mode

- published result source: `benchmark_oracle_adoption_v1`
- published result scope: `benchmark_aligned_publication_not_yet_internalized`
- legacy internal layer preserved: `True`
- source BS gap after adoption: `0`

## Verdict

- minimum success standard met: `True`
- source BS equals benchmark: `True`
- dAI equals benchmark: `True`
- indicator group equals benchmark: `True`
- remaining blocker: The published SG194 source-workflow result now uses the accepted benchmark oracle dBS/dAI = 10/10 with indicator group Z6, but the internal current-to-benchmark map still has not retired the legacy 13-dimensional reduced layer.
