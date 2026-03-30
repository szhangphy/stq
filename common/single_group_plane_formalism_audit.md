# Single Group Plane Formalism Audit

## Scope
- Group: `10.4.1.31`
- Stage: plane formalism audit and torsion audit on top of the existing minimal with-planes prototype.
- Out of scope: AI / EBR / BS/AI / all-group generalization / final topology classification / rep_matrix-based workflows.

## A. Current Minimal Point-Plane Prototype
- Current model: `point -> plane direct restriction onto plane unitary basis`.
- Current with-planes matrix shape / rank / nullity: `30 x 31` / `23` / `8`.
- Current plane unknown ordering: `['S1_R1', 'S1_R2', 'S1_R3', 'S1_R4', 'S2_R1']`.
- Plane basis definitions:
  - `S1_R1` with character `['1', '-1', '-1', '1']` and rep_degree `1`
  - `S1_R2` with character `['1', '-1', '1', '-1']` and rep_degree `1`
  - `S1_R3` with character `['1', '1', '-1', '-1']` and rep_degree `1`
  - `S1_R4` with character `['1', '1', '1', '1']` and rep_degree `1`
  - `S2_R1` with character `['2', '0', '0', '0']` and rep_degree `2`
- Current 20 plane rows:
  - global row `10`: `S1` / `P1` / `S1_R1` gives `1*P1_R2 + 1*P1_R3 = 1*S1_R1`
  - global row `11`: `S1` / `P1` / `S1_R2` gives `1*P1_R1 + 1*P1_R4 = 1*S1_R2`
  - global row `12`: `S1` / `P1` / `S1_R3` gives `1*P1_R6 + 1*P1_R7 = 1*S1_R3`
  - global row `13`: `S1` / `P1` / `S1_R4` gives `1*P1_R5 + 1*P1_R8 = 1*S1_R4`
  - global row `14`: `S1` / `P2` / `S1_R1` gives `1*P2_R2 = 1*S1_R1`
  - global row `15`: `S1` / `P2` / `S1_R2` gives `1*P2_R1 = 1*S1_R2`
  - global row `16`: `S1` / `P2` / `S1_R3` gives `1*P2_R1 = 1*S1_R3`
  - global row `17`: `S1` / `P2` / `S1_R4` gives `1*P2_R2 = 1*S1_R4`
  - global row `18`: `S1` / `P3` / `S1_R1` gives `1*P3_R2 + 1*P3_R3 = 1*S1_R1`
  - global row `19`: `S1` / `P3` / `S1_R2` gives `1*P3_R1 + 1*P3_R4 = 1*S1_R2`
  - global row `20`: `S1` / `P3` / `S1_R3` gives `1*P3_R6 + 1*P3_R7 = 1*S1_R3`
  - global row `21`: `S1` / `P3` / `S1_R4` gives `1*P3_R5 + 1*P3_R8 = 1*S1_R4`
  - global row `22`: `S1` / `P7` / `S1_R1` gives `1*P7_R2 = 1*S1_R1`
  - global row `23`: `S1` / `P7` / `S1_R2` gives `1*P7_R1 = 1*S1_R2`
  - global row `24`: `S1` / `P7` / `S1_R3` gives `1*P7_R1 = 1*S1_R3`
  - global row `25`: `S1` / `P7` / `S1_R4` gives `1*P7_R2 = 1*S1_R4`
  - global row `26`: `S2` / `P4` / `S2_R1` gives `1*P4_R1 + 1*P4_R2 = 1*S2_R1`
  - global row `27`: `S2` / `P5` / `S2_R1` gives `1*P5_R1 + 1*P5_R2 = 1*S2_R1`
  - global row `28`: `S2` / `P6` / `S2_R1` gives `2*P6_R1 = 1*S2_R1`
  - global row `29`: `S2` / `P8` / `S2_R1` gives `2*P8_R1 = 1*S2_R1`

## B. Geometric-Only Boundary Lines Used As Local Check Objects
- These boundary lines are not promoted to global unknown-bearing manifolds.
- They are only used here as local intermediate objects for the chain check `point -> boundary-line -> plane`.
- Exact boundary sample points read from `single_group_connectivity.json`:
  - `S1_bdry_u0`: plane `S1`, boundary `u = 0`, derived line `(0, 0, w)`, sample point `(0, 0, 1/5)`, endpoints `['P1', 'P2']`
  - `S1_bdry_u12`: plane `S1`, boundary `u = 1/2`, derived line `(1/2, 0, w)`, sample point `(1/2, 0, 1/5)`, endpoints `['P3', 'P7']`
  - `S1_bdry_w0`: plane `S1`, boundary `w = 0`, derived line `(u, 0, 0)`, sample point `(1/5, 0, 0)`, endpoints `['P1', 'P3']`
  - `S1_bdry_w12`: plane `S1`, boundary `w = 1/2`, derived line `(u, 0, 1/2)`, sample point `(1/5, 0, 1/2)`, endpoints `['P2', 'P7']`
  - `S2_bdry_u0`: plane `S2`, boundary `u = 0`, derived line `(0, 1/2, w)`, sample point `(0, 1/2, 1/5)`, endpoints `['P4', 'P6']`
  - `S2_bdry_u12`: plane `S2`, boundary `u = 1/2`, derived line `(1/2, 1/2, w)`, sample point `(1/2, 1/2, 1/5)`, endpoints `['P5', 'P8']`
  - `S2_bdry_w0`: plane `S2`, boundary `w = 0`, derived line `(u, 1/2, 0)`, sample point `(1/5, 1/2, 0)`, endpoints `['P4', 'P5']`
  - `S2_bdry_w12`: plane `S2`, boundary `w = 1/2`, derived line `(u, 1/2, 1/2)`, sample point `(1/5, 1/2, 1/2)`, endpoints `['P6', 'P8']`

## C. Boundary-Line character / degree Extraction
- `S1_bdry_u0`: character=`ok`, degree=`ok`, exact_k=`(0, 0, 1/5)`, cli_k=`(0, 0, 0.2)`, `cant find the position` in character stdout=`False`.
- `S1_bdry_u12`: character=`ok`, degree=`ok`, exact_k=`(1/2, 0, 1/5)`, cli_k=`(0.5, 0, 0.2)`, `cant find the position` in character stdout=`False`.
- `S1_bdry_w0`: character=`ok`, degree=`ok`, exact_k=`(1/5, 0, 0)`, cli_k=`(0.2, 0, 0)`, `cant find the position` in character stdout=`False`.
- `S1_bdry_w12`: character=`ok`, degree=`ok`, exact_k=`(1/5, 0, 1/2)`, cli_k=`(0.2, 0, 0.5)`, `cant find the position` in character stdout=`False`.
- `S2_bdry_u0`: character=`ok`, degree=`ok`, exact_k=`(0, 1/2, 1/5)`, cli_k=`(0, 0.5, 0.2)`, `cant find the position` in character stdout=`True`.
- `S2_bdry_u12`: character=`ok`, degree=`ok`, exact_k=`(1/2, 1/2, 1/5)`, cli_k=`(0.5, 0.5, 0.2)`, `cant find the position` in character stdout=`False`.
- `S2_bdry_w0`: character=`ok`, degree=`ok`, exact_k=`(1/5, 1/2, 0)`, cli_k=`(0.2, 0.5, 0)`, `cant find the position` in character stdout=`True`.
- `S2_bdry_w12`: character=`ok`, degree=`ok`, exact_k=`(1/5, 1/2, 1/2)`, cli_k=`(0.2, 0.5, 0.5)`, `cant find the position` in character stdout=`False`.

## D. Boundary-Line vs Plane Signatures
- `S1_bdry_u0` vs `S1`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
- `S1_bdry_u12` vs `S1`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
- `S1_bdry_w0` vs `S1`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
- `S1_bdry_w12` vs `S1`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[1, 1, 1, 1], basis_characters=[['1', '-1', '-1', '1'], ['1', '-1', '1', '-1'], ['1', '1', '-1', '-1'], ['1', '1', '1', '1']]`
- `S2_bdry_u0` vs `S2`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
- `S2_bdry_u12` vs `S2`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
- `S2_bdry_w0` vs `S2`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
- `S2_bdry_w12` vs `S2`: same_signature=`True`, same_basis_characters=`True`, same_rep_degree_pattern=`True`, basis_map_is_identity=`True`.
  - boundary signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`
  - plane signature: `ops=8, unitary=4, antiunitary=4, rep_degree=[2], basis_characters=[['2', '0', '0', '0']]`

## E. Chain Consistency Check
- Question: can the current direct model be reproduced as `point -> boundary-line -> plane`?
- `S1_bdry_u0`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P1`: rep_match=`True`, row_match=`True`
  - `P2`: rep_match=`True`, row_match=`True`
- `S1_bdry_u12`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P3`: rep_match=`True`, row_match=`True`
  - `P7`: rep_match=`True`, row_match=`True`
- `S1_bdry_w0`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P1`: rep_match=`True`, row_match=`True`
  - `P3`: rep_match=`True`, row_match=`True`
- `S1_bdry_w12`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P2`: rep_match=`True`, row_match=`True`
  - `P7`: rep_match=`True`, row_match=`True`
- `S2_bdry_u0`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P4`: rep_match=`True`, row_match=`True`
  - `P6`: rep_match=`True`, row_match=`True`
- `S2_bdry_u12`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P5`: rep_match=`True`, row_match=`True`
  - `P8`: rep_match=`True`, row_match=`True`
- `S2_bdry_w0`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P4`: rep_match=`True`, row_match=`True`
  - `P5`: rep_match=`True`, row_match=`True`
- `S2_bdry_w12`: all endpoint rep checks match direct=`True`, all endpoint row checks match direct=`True`.
  - `P6`: rep_match=`True`, row_match=`True`
  - `P8`: rep_match=`True`, row_match=`True`
- Global chain consistency result: `True`.
- Chain-consistent rows equal the current direct rows: `True`.
- Reading: the current minimal point-plane prototype is supported by the stricter chain check. The geometric-only boundary lines do not need to enter the global unknown ordering to validate the existing point-plane rows.

## F. Smith-Diagonal `2` Torsion Audit
- Full with-planes Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`.
- The nontrivial invariant factor `2` sits at Smith position `23` (1-based).
- Minimal torsion witness rows: `[28, 29]` with support-only Smith diagonal `[1, 2]`.
  - `2*P6_R1 = 1*S2_R1`
  - `2*P8_R1 = 1*S2_R1`
  - support unknowns: `['P6_R1', 'P8_R1', 'S2_R1']`
- Alternative S1-mediated witness rows: `[4, 9, 14, 15, 22, 23]` with support-only Smith diagonal `[1, 1, 1, 1, 1, 2]`.
  - `1*P2_R1 + 1*P2_R2 = 2*P6_R1`
  - `1*P7_R1 + 1*P7_R2 = 2*P8_R1`
  - `1*P2_R2 = 1*S1_R1`
  - `1*P2_R1 = 1*S1_R2`
  - `1*P7_R2 = 1*S1_R1`
  - `1*P7_R1 = 1*S1_R2`
- Row-removal experiments:
  - `line_only_baseline` -> shape `10 x 31`, rank `10`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`
  - `full_current_matrix` -> shape `30 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_S1_rows` -> shape `14 x 31`, rank `14`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_S2_rows` -> shape `26 x 31`, rank `22`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_S2_double_rows_P6_P8` -> shape `28 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_S2_simple_rows_P4_P5` -> shape `28 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_L2` -> shape `29 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_L4` -> shape `29 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `drop_L2_and_L4` -> shape `28 x 31`, rank `23`, Smith `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
  - `only_S2_double_rows` -> shape `2 x 31`, rank `2`, Smith `[1, 2]`
- Chain-consistent row replacement changes the Smith result: `False`.
- Interpretation: The unique 2 is a real parity/evenness constraint in the current integer compatibility lattice. It is absent in the line-only 10 x 26 matrix, but it appears as soon as either plane family is added. A minimal witness is the 2 x 3 subsystem formed by the rows 2*P6_R1 = S2_R1 and 2*P8_R1 = S2_R1, whose Smith diagonal is [1, 2]. An alternative S1-mediated witness is rows L2, L4, P2->S1(R1/R2), and P7->S1(R1/R2), which also produce a single 2. Because the chain audit reproduces the current direct rows exactly, this 2 is not a fake artifact of skipping explicit boundary-line unknowns.

## Final Conclusion
- Conclusion type: `1` (current minimal point-plane prototype is consistent and credible).
- boundary_line_outputs_available=`True`
- chain_check_consistent=`True`
- torsion_2_explained=`True`
- current_plane_model_accepted=`True`
- requires_matrix_update=`False`
- next_blocker: No immediate matrix correction is required at this layer; the remaining blocker is a future fully general connector formalism beyond this single-group local validation.
