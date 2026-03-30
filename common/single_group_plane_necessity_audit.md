# Single Group Plane Necessity Audit

## Scope
- Group: `10.4.1.31`
- Stage: plane-layer necessity audit on top of the existing explicit special-line BS package.
- Out of scope: AI / EBR / BS/AI / all-group generalization / rep_matrix-based workflows.

## A. Existing Line-Layer BS Structure
- Current global unknown ordering is the 26-point-irrep ordering already stored in `single_group_full_compatibility.json` and `single_group_bs_matrix_analysis.json`.
- Current line-only matrix shape: `10 x 26`.
- The 10 global equations come from the four explicit line blocks only:
  - `L1` / `L1_R1`: `1*P1_R1 + 1*P1_R2 = 1*P4_R2`
  - `L1` / `L1_R2`: `1*P1_R3 + 1*P1_R4 = 1*P4_R1`
  - `L1` / `L1_R3`: `1*P1_R5 + 1*P1_R6 = 1*P4_R1`
  - `L1` / `L1_R4`: `1*P1_R7 + 1*P1_R8 = 1*P4_R2`
  - `L2` / `L2_R1`: `1*P2_R1 + 1*P2_R2 = 2*P6_R1`
  - `L3` / `L3_R1`: `1*P3_R1 + 1*P3_R2 = 1*P5_R2`
  - `L3` / `L3_R2`: `1*P3_R3 + 1*P3_R4 = 1*P5_R1`
  - `L3` / `L3_R3`: `1*P3_R5 + 1*P3_R6 = 1*P5_R1`
  - `L3` / `L3_R4`: `1*P3_R7 + 1*P3_R8 = 1*P5_R2`
  - `L4` / `L4_R1`: `1*P7_R1 + 1*P7_R2 = 2*P8_R1`
- Pretty basis block counts: `{'L1': 6, 'L2': 2, 'L3': 6, 'L4': 2}`.
- Pretty basis is block-wise direct sum by line block: `True`.
- Any cross-line term in the existing rows: `False`.
- Any cross-line support in the existing pretty basis: `False`.
- Reading: the current line-only BS package contains only intra-line compatibility. It does not couple different explicit line blocks to each other.
- Because the line layer is block-separated and the only separately listed higher-dimensional special manifolds are `['S1', 'S2']`, the plane layer is indeed the next unique candidate source of new coupling.

## B. Plane Geometry Readback
- Explicit special plane objects listed in the geometry file: `['S1', 'S2']`.
- `S1`: parametrization `(u, 0, w)`, constraints `0 < u, 0 < w, u < 1/2, w < 1/2`, sample_point `(1/5, 0, 2/5)`, symmetry_summary.generic_point `(1/5, 0, 1/7)`.
- `S2`: parametrization `(u, 1/2, w)`, constraints `0 < u, 0 < w, u < 1/2, w < 1/2`, sample_point `(1/5, 1/2, 2/5)`, symmetry_summary.generic_point `(1/5, 1/2, 1/7)`.
- For this audit the extraction point is the explicit manifold `sample_point` stored in `single_group_kmanifolds.json`; no hand-written generic point was introduced.
- `line_plane = []`: `[]`.
- `single_group_connectivity.json` explains that a line-plane edge is recorded only when a plane boundary exactly matches an existing separately listed line manifold.
- All plane boundaries are therefore geometric-only boundaries here, not explicit special-line objects.
- Consequence: the plane-layer connector cannot reuse the existing explicit line-block route unchanged. The minimal viable connector is direct restriction from each boundary corner point to the common plane unitary-subgroup basis, with the geometric boundary lines used only as incidence geometry.

## C. SSGReps Extraction Status
- `S1`: character=`ok`, degree=`ok`, exact_k=`(1/5, 0, 2/5)`, cli_k=`(0.2, 0, 0.4)`, character warning `cant find the position`=`False`.
- `S2`: character=`ok`, degree=`ok`, exact_k=`(1/5, 1/2, 2/5)`, cli_k=`(0.2, 0.5, 0.4)`, character warning `cant find the position`=`True`.
- Current toolchain sufficiency: yes. Existing geometry JSON + `SSGReps.py --out character/rep_degree` + the existing `debug_single_connection.py` helper routines are sufficient to extract and decode plane generic data.
- Current minimal blocker for a fully formal plane framework is not data extraction. It is the mathematical choice of connector formalism once plane boundaries are classified as geometric-only rather than explicit special lines.

## D. Plane-vs-Line Signature Comparison
- Signature comparison result:
  - `S1` matches line signatures `['L1', 'L3']`.
  - `S2` matches line signatures `['L2', 'L4']`.
- New little-group signature type detected at the plane generic level: `False`.
- Important nuance: `S1/S2` do not introduce new signature types, but that alone does not settle necessity. The real question is whether shared plane unknowns couple previously independent line blocks.

## E. Necessity Judgment
- Conclusion type: `2` (plane adds new independent compatibility constraints).
- Minimal prototype used here:
  - Unknown-bearing manifolds: `S1` with 4 one-dimensional basis irreps, `S2` with 1 two-dimensional basis irrep.
  - Connector model: one point-plane row per `(boundary corner point, plane basis)` pair.
  - Geometric boundary lines stay geometric-only; they are not promoted to independent unknown-bearing line objects in this prototype.

### Representative New Plane Equations
- `1*P1_R2 + 1*P1_R3 = 1*S1_R1`
- `1*P1_R1 + 1*P1_R4 = 1*S1_R2`
- `1*P1_R6 + 1*P1_R7 = 1*S1_R3`
- `1*P1_R5 + 1*P1_R8 = 1*S1_R4`
- `1*P2_R2 = 1*S1_R1`
- `1*P2_R1 = 1*S1_R2`

### Why These Are Genuinely New
- The line-only matrix had no cross-line support at all; every row lived inside one explicit line block.
- The plane prototype introduces shared plane unknowns that simultaneously receive decompositions from four boundary corner-point sets.
- This immediately couples the previously independent line blocks. For example, the S2 scalar plane variable identifies `P4`, `P5`, `P6`, and `P8` sectors that never met in the line-only matrix.
- Extended matrix shape: `30 x 31`.
- Extended rank / nullity: `23` / `8`.
- Added independent rank beyond the line-only embedding: `13`.
- Net nullity drop relative to the line-only BS: `8`.
- Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`.
- Interpretation: the plane layer is necessary for this group already at the compatibility/BS level, even though its generic signatures are not new. The necessity comes from new couplings, not from new generic little-group types.

## Final Conclusion
- `S1` and `S2` generic character/degree extraction succeeded.
- They do not represent new generic signature types relative to `L1-L4`.
- They nevertheless add new independent compatibility constraints because they couple previously disjoint line blocks through shared plane unknowns.
- A minimal plane-layer prototype was therefore required and has been written out as `single_group_full_compatibility_with_planes.json` plus the updated with-planes BS files.
