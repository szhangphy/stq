# MD-Strict Rewrite Bundle

This directory is a standalone rewrite workspace. It does not need the live
production package imports.

One-line run:

```bash
python /data/work/szhang/ssg/comprel/md_target_rewrite_bundle/run_md_strict.py --group 34 --mode single --pretty
```

The command executes the standalone md-style BS-only target builder defined in:

- `sg194/pipeline_v2/md_target_rewrite.py`

Current semantics:

- Stages 4-7 of the md workflow are supplied by the copied
  `common/swyckoff_k.py` operation-derived manifold builder, using
  `construct_std_ssg_operations` and the post-supercell primitive reciprocal
  basis.
- Stages 8-16 are assembled explicitly in
  `sg194/pipeline_v2/md_target_rewrite.py`: exact closure-based connectivity,
  maximality by generic little-co-group inclusion, retained-shell selection by
  maximal-containing connected components, monodromy branch construction,
  compatibility matrix assembly, and exact integer projection to BS.
- No `recover*` route, manual phase-character matcher, or legacy path-reduction
  layer is used by the active runner.
- Generic-position rows are included by default and are written before any
  algebraic projection.
- For maximal lines and planes, BS variables are emitted as monodromy-defined
  global branches. For maximal points, local irreps are already global branches.

Current smoke status:

- `group 45`, `single`: runs successfully and currently returns `dBS = 3`
- `group 45`, `double`: runs successfully and currently returns `dBS = 2`
- These are regression checks for the md-strict runner, not benchmark targets

The bundle contains local copies of:

- `common/SSGReps`
- `common/swyckoff_k.py`
- `common/swyckoff_r.py`
- `sg194/pipeline_v2/*`
