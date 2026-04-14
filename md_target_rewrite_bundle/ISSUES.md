# Current Issues

The active runner

```bash
python /data/work/szhang/ssg/comprel/md_target_rewrite_bundle/run_md_strict.py --group <id> --mode <single|double> --pretty
```

now follows the md workflow structure intentionally:

- geometry manifolds are operation-derived from the copied `common/swyckoff_k.py`
  path using `construct_std_ssg_operations`
- connectivity is rebuilt in `md_target_rewrite.py` by exact closure solves with
  symmetry images and reciprocal shifts
- `M_int` keeps every non-maximal manifold in a connected component containing a
  maximal manifold
- GP rows are written before projection
- BS variables are built from maximal-manifold global branches
- the final `dBS` comes from exact integer elimination / kernel analysis

There are no known deliberate semantic deviations from
`/data/home/szhang/bs_geometry_workflow.md` in the active runner.

The remaining work is practical rather than structural:

## 1. Group-by-group regression is still incomplete

- The bundle has been smoke-tested on `group 45` in `single` and `double` mode
  after the latest retained-shell and monodromy cleanup.
- Broader regression over the previously discussed group list still needs to be
  rerun before declaring the whole bundle stable.

## 2. Site-symmetry labels depend on optional lookup data

- In the current environment, `swyckoff_k.py` prints
  `space_groups_json not found; site-symmetry labels may be less specific`.
- This does not block manifold construction, connectivity, or the BS matrix, but
  some human-readable point-group labels can be less specific than in a fully
  provisioned environment.

## 3. The geometry engine is reused, not duplicated

- This is by design: the bundle keeps `common/swyckoff_k.py` and
  `common/SSGReps` as copied dependencies and builds the md runner on top of
  them.
- If a future cleanup wants every md stage to live under one minimal file tree,
  the next step would be code motion, not a semantic rewrite.
