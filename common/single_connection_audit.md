# Single Connection Audit

## Scope
- Group: `10.4.1.31`
- Connection: `P1 -- L1 -- P4`
- Exact k points: `P1=(0, 0, 0)`, `L1_generic=(0, 1/5, 0)`, `P4=(0, 1/2, 0)`

## Geometry Anchor
- `P1`: `(0, 0, 0)`
- `L1`: `(0, v, 0)`, constraints `0 < v < 1/2`, sample point `(0, 1/5, 0)`
- `P4`: `(0, 1/2, 0)`
- Endpoint relation from `single_group_connectivity.json`:
  - `P1 -- L1` from boundary condition `v = 0`
  - `P4 -- L1` from boundary condition `v = 1/2`

## A. SSGReps.py
- Real file: `/data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py`
- Real invocation styles:
  - CLI via `python SSGReps/SSGReps/SSGReps.py ...`
  - import API via `load_one_ssg_kvec(ssgnum, kvec, single, out, fileType, optimize)` after adding `SSGReps/SSGReps` to `sys.path`
- `groupType` meaning is real, not inferred:
  - `1` -> single group
  - `2` -> double group
  - For this task the wrapper uses `1`, matching the single-valued target.
- Real CLI input constraints:
  - `--kp` is parsed as three Python floats, so the exact rational `1/5` must be preserved in wrapper metadata while the CLI receives `0.2`.
  - `--optimize` is declared as `type=bool`, so `--optimize False` is parsed as `True`; the wrapper avoids that buggy path.
- Real JSON payload keys for both `--out character` and `--out rep_degree`:
  - `ssgNum`, `kvec`, `rotC`, `spin`, `su2`, `timeReversal`, `tauC`, `character`, `repMatrix`, `torsion`, `repDegree`
- JSON mode note: `SSGReps.py` uses the same JSON schema for both `--out character` and `--out rep_degree`, and the CLI branch only changes terminal printing after the little-group object is built. Two independent runs are not byte-identical because the irrep construction uses a random matrix internally, so `character` and especially `repMatrix` can drift by tiny floating noise between runs. For this task the stable usable fields are the operation data, `timeReversal`, `torsion`, `repDegree`, and the rounded internal unitary-subgroup `character`; the printed terminal output instead uses `linear_character`.
- Real terminal printing behavior:
  - `--out character` prints `linear_character` on the unitary subgroup only.
  - `--out rep_degree` prints only the degree list.
  - Neither terminal mode prints a label system for irreps.

## Raw Commands
- `P1 character`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0 0 --out character --groupType 1 --fileType json`
- `P1 degree`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0 0 --out rep_degree --groupType 1 --fileType json`
- `L1 character`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0.2 0 --out character --groupType 1 --fileType json`
- `L1 degree`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0.2 0 --out rep_degree --groupType 1 --fileType json`
- `P4 character`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0.5 0 --out character --groupType 1 --fileType json`
- `P4 degree`: `/data/home/szhang/anaconda3/bin/python /data/work/szhang/ssg/comprel/SSGReps/SSGReps/SSGReps.py --ssgNum 10.4.1.31 --kp 0 0.5 0 --out rep_degree --groupType 1 --fileType json`

## B. Current Geometry Layer
- The geometry layer already stores the exact object IDs, endpoint relation, and special-manifold classification for this single connection.
- `L1` is explicitly marked as `separately_listed_special_line_manifold`.
- The chosen generic interior point is already fixed to `(0, 1/5, 0)` in `single_group_kmanifolds.json`.

## C. Feasibility
- `SSGReps.py` can stably produce little-group data for all three fixed k points in this connection.
- The `L1` little-group operations match strict subsets of the `P1` and `P4` little-group operations.
- The printed `linear_character` is not the right object for this cross-k restriction; it gives non-integral coefficients on this connection because it still carries the k-dependent translation phase.
- The internal `character` stored in the JSON/object is sufficient here: it restricts from `P1` and `P4` to the `L1` basis with integral coefficients.
- Conclusion: current local code is already sufficient to construct a minimal compatibility block for `P1 -- L1 -- P4` without using `rep_matrix`.

## Character vs Degree Runs
- `P1`: `{"same_schema_keys": true, "stable_fields_equal": true, "character_allclose": true, "rep_matrix_allclose": true, "byte_identical": false}`
- `L1`: `{"same_schema_keys": true, "stable_fields_equal": true, "character_allclose": true, "rep_matrix_allclose": true, "byte_identical": false}`
- `P4`: `{"same_schema_keys": true, "stable_fields_equal": true, "character_allclose": true, "rep_matrix_allclose": false, "byte_identical": false}`

## Optimize Check
- `P1`: `{"same_rep_degree": true, "same_torsion": true, "same_time_reversal": true, "same_character": true, "same_linear_character": true}`
- `L1`: `{"same_rep_degree": true, "same_torsion": true, "same_time_reversal": true, "same_character": true, "same_linear_character": true}`
- `P4`: `{"same_rep_degree": true, "same_torsion": true, "same_time_reversal": true, "same_character": true, "same_linear_character": true}`

## Minimal Compatibility Block
- Unknown ordering: `P1_R1, P1_R2, P1_R3, P1_R4, P1_R5, P1_R6, P1_R7, P1_R8, P4_R1, P4_R2`
- Middle comparison basis on `L1`:
  - `L1_R1` with character `['1', '-1', '-1', '1']`
  - `L1_R2` with character `['1', '-1', '1', '-1']`
  - `L1_R3` with character `['1', '1', '-1', '-1']`
  - `L1_R4` with character `['1', '1', '1', '1']`
- Equations:
  - `L1_R1`: `1*P1_R1 + 1*P1_R2 = 1*P4_R2`
  - `L1_R2`: `1*P1_R3 + 1*P1_R4 = 1*P4_R1`
  - `L1_R3`: `1*P1_R5 + 1*P1_R6 = 1*P4_R1`
  - `L1_R4`: `1*P1_R7 + 1*P1_R8 = 1*P4_R2`

## Data Dependency
- `identify.pkl` location: `/data/work/szhang/ssg/comprel/SSGReps/ssg_data/identify.pkl`
- Extracted from tarball during this run: `False`
