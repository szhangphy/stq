# Coordinate Conversion Contract V2

- coordinate system A owner: `common/SSGReps.py`
- coordinate system B owner modules: `2` declared entries
- conversion authority: `common/swyckoff.py`

## Conversion Sources

- k-space: `common/swyckoff_k.py` -> `to_reciprocal_op, primitive_matrix_from_centering, change_basis_ops, load_irssg_data, compute_wyckoff_output`
- real-space: `common/swyckoff_r.py` -> `primitive_matrix_from_centering, change_basis_ops, load_irssg_data, compute_wyckoff_output`

## Notes

- Only SSGReps.py is allowed to work in coordinate system A.
- Pipeline modules must consume coordinate-system-B outputs only.
- No pipeline module should import swyckoff_k.py or swyckoff_r.py directly.
