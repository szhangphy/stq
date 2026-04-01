# SG194 Single Vs Double Geometry Diff v1

## generated_at

```json
"2026-04-01T12:27:55+08:00"
```

## target_group

```json
"194.1.1.1"
```

## shared_geometry_construction

```json
{
  "source_file": "sg194/debug_workflow_portability_stage2_194.1.1.1.py",
  "single_builder": "build_single_runtime(..., shared_kgeom=...)",
  "double_builder": "build_double_runtime(..., shared_kgeom=...)",
  "shared_kgeometry_helper": "build_shared_kgeometry",
  "double_reuses_single_geometry_backbone_by_construction": true
}
```

## geometry_counts

```json
{
  "point_block_count": 6,
  "line_block_count": 7,
  "plane_block_count": 4,
  "synthetic_boundary_point_count": 0
}
```

## point_ids

```json
[
  "P1",
  "P2",
  "P3",
  "P4",
  "P5",
  "P6"
]
```

## line_ids

```json
[
  "L1",
  "L2",
  "L3",
  "L4",
  "L5",
  "L6",
  "L7"
]
```

## plane_ids

```json
[
  "S1",
  "S2",
  "S3",
  "S4"
]
```

## synthetic_boundary_point_ids

```json
[]
```

## point_representative_coordinates

```json
{
  "P1": [
    "0",
    "0",
    "0"
  ],
  "P2": [
    "0",
    "0",
    "1/2"
  ],
  "P3": [
    "1/3",
    "1/3",
    "0"
  ],
  "P4": [
    "2/3",
    "2/3",
    "1/2"
  ],
  "P5": [
    "1/2",
    "0",
    "0"
  ],
  "P6": [
    "1/2",
    "0",
    "1/2"
  ]
}
```

## file_level_parity

```json
{
  "global_unknown_ordering_equal": true,
  "covered_lines_equal": true,
  "covered_planes_equal": true,
  "global_matrix_rows_equal": true,
  "global_matrix_equal": true
}
```

## active_compatibility_structure

```json
{
  "single_matrix_shape": [
    58,
    42
  ],
  "double_matrix_shape": [
    58,
    42
  ],
  "single_unknown_ordering_count": 42,
  "double_unknown_ordering_count": 42,
  "single_bs_rank": 26,
  "double_bs_rank": 26,
  "single_bs_nullity": 16,
  "double_bs_nullity": 16
}
```

## geometry_identical

```json
true
```

## verdict

```json
"Single and double use the same k-space geometry / incidence / endpoint structure and the same 58x42 with-planes compatibility backbone. The representation mode changes, but the geometry backbone does not."
```
