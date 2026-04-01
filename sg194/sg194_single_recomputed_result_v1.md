# SG194 Single Recomputed Result v1

## generated_at

```json
"2026-04-01T12:27:55+08:00"
```

## target_group

```json
"194.1.1.1"
```

## result_kind

```json
"single_same_geometry_raw_current_result"
```

## row_language_kind

```json
"raw_current_with_planes_42_unknown_shell"
```

## same_geometry_as_double

```json
true
```

## same_target_row_language_as_benchmark

```json
false
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

## compare_to_previous_single_direct_package

```json
{
  "dBS": 16,
  "dAI": 13,
  "classification": "Z^3",
  "matches_recomputed_result": true,
  "note": "The old package had stale source references, so its evidence chain was flawed even though the raw-current numbers match the new recomputation."
}
```

## compare_to_current_double

```json
{
  "dBS": 10,
  "dAI": 10,
  "classification": "Z6"
}
```

## compare_to_benchmark_oracle

```json
{
  "dBS": 10,
  "dAI": 10,
  "classification": "Z6"
}
```

## verdict

```json
"Recomputing single with the same geometry backbone as double does not change the raw-current single result. It remains 16/13/Z^3, which is therefore a raw-current same-geometry result, not a single-target standard result."
```
