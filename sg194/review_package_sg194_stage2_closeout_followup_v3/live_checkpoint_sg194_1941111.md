# Live Checkpoint: SG194 194.1.1.1 Final Standard-Space Closeout

- Last updated: 2026-03-31 20:05:18 +0800
- Branch: `sg194-special`
- Latest synced `sg194-special`: `36a66b7`
- Latest synced `main`: `a7b4e4d`
- Phase: final standard-space projection implemented; validation complete; git commit/push pending

## Latest state

1. The current authoritative physical point-space shell is the 34-row `P1..P6` block ordering.
2. The final ordinary SG194 standard comparison shell is the 34-row `GM/A/K/H/M/L` ordering.
3. The current-to-standard mapping is explicit and no longer missing.
4. The decisive contract kills the three common raw `Z^3` free directions while anchoring onto the external ordinary 13-generator AI basis.
5. The authoritative stage2 outputs now report single final `BS=13`, final `AI=13`, quotient `trivial`.
6. The authoritative stage2 outputs now report double final `BS=13`, final `AI=13`, quotient `trivial`.
7. The stage2 report PDF exists and `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate` passes.

## Latest commands

1. `python3 -m py_compile common/*.py`
2. `python3 -m py_compile sg194/*.py`
3. `python3 sg194/debug_sg194_standard_space_projection_v1.py --validate`
4. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
5. `python3 -c '<load stage2 module, rebuild report tex/pdf from authoritative JSON, run compile_report()>'`
6. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`

## Next

1. Review the staged diff and keep unrelated old review-package directories/tarballs plus LaTeX aux/log files out of the commit.
2. Commit the in-scope source and authoritative outputs on `sg194-special`.
3. Push `origin/sg194-special`.
