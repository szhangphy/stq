# Top 5 Bugs

## 1. Authoritative line builder used linear_character where character is required

- priority: `P0`
- function: `build_line_block`
- files: `sg194/debug_workflow_portability_194.1.1.1.py, sg194/pipeline_v2/runtime_backend_free.py`
- why wrong: L1/L2/L5 endpoint restrictions are integer-solvable in character language and non-integral in linear_character, so the old field choice manufactured the first source-layer blocker.
- why this affects BS core: This failure happens inside the live line compatibility builder before any global with-planes matrix exists.
- minimal fix: Switch authoritative line subduction to character language for 194.1.1.1.
- witness: `first failure = mode=single manifold=L1 endpoint=P1 rep=P1_R1 field=linear_character`

Original code:
- `sg194/debug_workflow_portability_194.1.1.1.py:1195`
```python
1193:     endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
1194:     line_raw = captures[line_id]
1195:     field = "linear_character"
1196:     line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
1197:     line_basis_matrix = _exact_basis_matrix_from_capture(line_raw, field, manifold_id=line_id)
```
- `sg194/pipeline_v2/runtime_backend_free.py:1426`
```python
1424:     endpoint_ids = [endpoint["point_id"] for endpoint in endpoint_entries]
1425:     line_raw = captures[line_id]
1426:     field = "linear_character"
1427:     line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
1428:     line_basis_matrix = _exact_basis_matrix_from_capture(
```
Final code:
- `sg194/debug_workflow_portability_194.1.1.1.py:1229`
```python
1227:     # language. The linear_character basis is not integer-solvable on the
1228:     # failing lines and breaks the authoritative BS construction.
1229:     field = "character"
1230:     line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
1231:     line_basis_matrix = _exact_basis_matrix_from_capture(line_raw, field, manifold_id=line_id)
```
- `sg194/pipeline_v2/runtime_backend_free.py:1460`
```python
1458:     # character language. The linear_character basis is not integer-solvable
1459:     # for L1/L2/L5 and S3, which is the active BS-construction failure.
1460:     field = "character"
1461:     line_basis_labels = [f"{line_id}_R{i}" for i in range(1, len(line_raw[field]) + 1)]
1462:     line_basis_matrix = _exact_basis_matrix_from_capture(
```

## 2. Authoritative plane builder used linear_character where character is required

- priority: `P0`
- function: `build_plane_block`
- files: `sg194/debug_workflow_portability_194.1.1.1.py, sg194/pipeline_v2/runtime_backend_free.py`
- why wrong: S3 point-to-plane restrictions admit integer decomposition in character language but not in linear_character, so the old plane builder could not preserve the intended 42-shell.
- why this affects BS core: Plane rows determine whether S1..S4 survive as active unknowns in the with-planes shell.
- minimal fix: Switch authoritative plane subduction to character language.
- witness: `diagnostic evidence = S3/P1_R1 non-integral in linear_character, successful in character`

Original code:
- `sg194/debug_workflow_portability_194.1.1.1.py:1497`
```python
1495:     plane_raw = captures[plane_id]
1496:     plane_unitary_ops = [operation_key_from_capture(plane_raw, op_index) for op_index in plane_raw["unitary_capture_indices"]]
1497:     field = "linear_character"
1498:     plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
1499:     plane_basis_matrix = _exact_basis_matrix_from_capture(plane_raw, field, manifold_id=plane_id)
```
- `sg194/pipeline_v2/runtime_backend_free.py:2002`
```python
2000:     plane_raw = captures[plane_id]
2001:     plane_unitary_ops = [operation_key_from_capture(plane_raw, op_index) for op_index in plane_raw["unitary_capture_indices"]]
2002:     field = "linear_character"
2003:     plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
2004:     plane_basis_matrix = _exact_basis_matrix_from_capture(
```
Final code:
- `sg194/debug_workflow_portability_194.1.1.1.py:1533`
```python
1531:     # Plane auxiliary coordinates stay in the intended 42-shell only in
1532:     # character language; linear_character fails on S3 corner restrictions.
1533:     field = "character"
1534:     plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
1535:     plane_basis_matrix = _exact_basis_matrix_from_capture(plane_raw, field, manifold_id=plane_id)
```
- `sg194/pipeline_v2/runtime_backend_free.py:2038`
```python
2036:     # Plane auxiliary coordinates remain the intended two-label 42-shell only
2037:     # if the point-to-plane subduction is performed in character language.
2038:     field = "character"
2039:     plane_basis_labels = [f"{plane_id}_R{i}" for i in range(1, len(plane_raw[field]) + 1)]
2040:     plane_basis_matrix = _exact_basis_matrix_from_capture(
```

## 3. Exact solver rejected valid integer decompositions on float-snapped captures

- priority: `P0`
- function: `solve_unique_integer_decomposition`
- files: `sg194/debug_workflow_portability_194.1.1.1.py, sg194/pipeline_v2/runtime_backend_free.py`
- why wrong: Even when integer coefficients existed numerically, the symbolic exactness gate rejected them on float-snapped captures and could drive the solver into expensive GMP-heavy paths.
- why this affects BS core: This gate decides whether line and plane rows are emitted at all; false negatives abort the authoritative BS construction.
- minimal fix: Add a numeric integer-certification step before the symbolic fallback.
- witness: `current repaired runtime would otherwise still fail later at L6/P2_R1 with exact reconstruction failed`

Original code:
- `sg194/debug_workflow_portability_194.1.1.1.py:1040`
```python
1038:             f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}: non-unique decomposition"
1039:         )
1040:     if basis_matrix * solution != restricted:
1041:         raise ValueError(
1042:             f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}: exact reconstruction failed"
```
- `sg194/pipeline_v2/runtime_backend_free.py:1139`
```python
1137:             f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}: non-unique decomposition"
1138:         )
1139:     if basis_matrix * solution != restricted:
1140:         raise ValueError(
1141:             f"mode={mode} manifold={manifold_id} endpoint={endpoint_id} rep={rep_id} field={field}: exact reconstruction failed"
```
Final code:
- `sg194/debug_workflow_portability_194.1.1.1.py:928`
```python
926: 
927: 
928: def solve_numeric_integer_decomposition(
929:     basis_matrix: sp.Matrix,
930:     restricted: sp.Matrix,
```
- `sg194/pipeline_v2/runtime_backend_free.py:1027`
```python
1025: 
1026: 
1027: def solve_numeric_integer_decomposition(
1028:     basis_matrix: sp.Matrix,
1029:     restricted: sp.Matrix,
```

## 4. Generic compatibility mislabeled the raw 42-shell as target row language

- priority: `P1`
- function: `_build_generic_compatibility`
- files: `sg194/pipeline_v2/generic_builders.py`
- why wrong: The bundle was still the raw with-planes current shell, so labeling it as a canonical target row language hid the source/target mismatch.
- why this affects BS core: This controls the object-language tag attached to the active compatibility matrix downstream BS/AI summaries publish.
- minimal fix: Publish the active matrix as current-row shell until a same-shell target builder exists.
- witness: `after repair the compatibility shape is [61, 42], so target-row labeling was demonstrably false`

Original code:
- `sg194/pipeline_v2/generic_builders.py:26`
```python
24: LOCAL_IRREP_BACKEND = ROOT / "pipeline_v2" / "local_irreps.py"
25: 
26: GENERIC_TARGET_ROW_LANGUAGE = "generic_canonical_point_row_language_from_symmetry_ops"
27: GENERIC_TARGET_OBJECT_KIND = "generic_direct_point_row_language_object"
28: LINE_SAMPLE = Fraction(1, 5)
```
- `sg194/pipeline_v2/generic_builders.py:397`
```python
395:         "group": group_id,
396:         "builder_variant": builder_variant,
397:         "row_language_kind": GENERIC_TARGET_ROW_LANGUAGE,
398:         "global_unknown_ordering": list(with_planes["global_unknown_ordering"]),
399:         "global_matrix_rows": list(with_planes["global_matrix_rows"]),
```
Final code:
- `sg194/pipeline_v2/generic_builders.py:26`
```python
24: LOCAL_IRREP_BACKEND = ROOT / "pipeline_v2" / "local_irreps.py"
25: 
26: GENERIC_CURRENT_ROW_LANGUAGE = "generic_current_row_shell_from_symmetry_ops"
27: GENERIC_TARGET_ROW_LANGUAGE = "generic_target_row_language_pending_same_shell_builder"
28: GENERIC_TARGET_OBJECT_KIND = "generic_target_object_pending"
```
- `sg194/pipeline_v2/generic_builders.py:398`
```python
396:         "group": group_id,
397:         "builder_variant": builder_variant,
398:         "row_language_kind": GENERIC_CURRENT_ROW_LANGUAGE,
399:         "global_unknown_ordering": list(with_planes["global_unknown_ordering"]),
400:         "global_matrix_rows": list(with_planes["global_matrix_rows"]),
```

## 5. Generic/public result objects published a projected quotient as the active target object

- priority: `P1`
- function: `generic_result_objects`
- files: `sg194/pipeline_v2/generic_builders.py`
- why wrong: The public API exposed projected point-shell diagnostics as if they were the authoritative same-shell BS/AI object, mixing 42-shell compatibility with 34-point-shell quotient semantics.
- why this affects BS core: This changes the externally visible active BS/AI object rather than just packaging text.
- minimal fix: Expose only raw_shell as available and mark target_pending as blocked until a same-language target builder exists.
- witness: `current generic_result_objects now reports single_raw_shell/double_raw_shell available and *_target_pending blocked`

Original code:
- `sg194/pipeline_v2/generic_builders.py:934`
```python
932:         results.append(
933:             {
934:                 "object_id": f"{mode}_target_direct",
935:                 "mode": mode,
936:                 "builder_variant": builder_variant,
```
Final code:
- `sg194/pipeline_v2/generic_builders.py:925`
```python
923:         results.append(
924:             {
925:                 "object_id": f"{mode}_target_pending",
926:                 "mode": mode,
927:                 "builder_variant": builder_variant,
```
