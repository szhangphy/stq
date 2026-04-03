# Controlled-Case Audit for 194.1.1.1

## Why 194.1.1.1 was selected

- The reference group 10.4.1.31 already closed both the single-group and double-group workflows.
- The current target 194.1.1.1 is a good portability pilot because the local toolchain can identify its spatial operation set as ordinary SG 194 inside the same basis/origin conventions used by the current code.

## Spatial-Operation Check

- `SG_utils.identify_SG_from_symmetry(...)` identifies the spatial part as SG `194 (P6_3/mmc)`.
- Hall number from the local spglib database: `488`.
- Standardized spatial operation-set equality against the hall-database SG 194 representative: `True`.
- Extra operations on the SSG side: `0`.
- Missing operations relative to SG 194: `0`.

## Real-Space / k-Space Geometry Check

- Real-space family-count match: `12` on the SSG side, signature equality = `True`.
- k-space manifold-count match: `18` on the SSG side, signature equality = `True`.
- `source_centering_symbol = P` and the selected origin shift remains zero in the local swyckoff workflow.

## groupType Availability

- representative k-space availability probe: `P1` at `['0', '0', '0']`.
- `groupType=1` direct little-group entry availability: `True`.
- `groupType=2` direct little-group entry availability: `True`.
- No antiunitary operations are present in the standardized spatial data (`time_reversal_count = 0`), so the controlled-case comparison is to an ordinary unitary SG 194 spatial backbone while still allowing a genuine double-group probe through `factor_su2` on the `SSGReps` side.

## Verdict

- `controlled_case_valid = True`.
- Under the current local setting/basis/origin conventions, 194.1.1.1 is not merely similar to SG 194: its standardized spatial operation set matches the local SG 194 hall-database representative exactly, and the real-space/k-space geometry signatures agree as well.
