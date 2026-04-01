# SG194 Single Mode From Double Geometry Fix Attempt v1

## generated_at

```json
"2026-04-01T12:27:55+08:00"
```

## target_group

```json
"194.1.1.1"
```

## single_reused_double_geometry

```json
true
```

## reuse_method

```json
{
  "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
  "helper": "build_shared_kgeometry",
  "single_builder": "build_single_runtime(..., shared_kgeom=shared_kgeom)",
  "double_builder": "build_double_runtime(..., shared_kgeom=shared_kgeom)"
}
```

## object_language_parity_enforced

```json
true
```

## legacy13_removed_from_active_single_ai_path

```json
true
```

## recomputed_single_result

```json
{
  "dBS": 16,
  "dAI": 13,
  "classification": "Z^3",
  "finite_part": [],
  "free_rank": 3,
  "smith_diagonal_nonzero": [
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1
  ]
}
```

## result_changed_after_forcing_shared_geometry

```json
false
```

## verdict

```json
"Recomputing single with the same geometry backbone as double does not change the raw-current single result. It remains 16/13/Z^3, which is therefore a raw-current same-geometry result, not a single-target standard result."
```
