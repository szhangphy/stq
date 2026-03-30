# Double-Group Feasibility Audit for 10.4.1.31

## Scope

- Group only: `10.4.1.31`.
- Group type only: `2` (double group).
- The single-group line is treated as already closed and is reused only as trusted background.
- This round does not attempt the final double-group indicator group. It only checks feasibility and builds the smallest honest prototype.

## Single-Group Premise Reused Here

- The with-planes k-space basis is already trusted for the single group.
- The single-group AI lattice is already complete and gives BS/AI = Z2 x Z2 at groupType=1.
- The spatial bridge has already been audited with r_conv = P r_mag and P = diag(1,2,2).
- The exported *_character.json files store raw characters, so the Bloch phase must still be restored through exp(-i k · tauC).

## Why The Double-Group Check Starts Here

- The current codebase already contains a genuine double-group branch in SSGReps: factor_su2 is no longer forced to 1 and the raw characters acquire projective phases.
- The real-space scripts already provide stable special positions, stabilizers, and orbit data for the same group.
- Therefore the smallest honest question is no longer whether geometry works; it is whether the existing bridge + induction route can absorb double-valued local characters without first solving the whole repository.

## K-Space Feasibility at groupType=2

- All required single-group manifolds were re-probed at groupType=2: endpoints `P1..P8`, lines `L1..L4`, planes `S1,S2`. Stable extraction succeeded on all of them: `True`.
- `character`, `linear_character`, and `rep_degree` are all available on the tested points, lines, and planes.
- The most visible change from groupType=1 is not the rep-degree pattern but the character phase pattern: order-2 unitary operations now carry double-valued phases such as +/-i.
- Representative example on P1:
  - single-group first raw character row: `[{'real': 1.0, 'imag': -0.0}, {'real': -1.0, 'imag': 0.0}, {'real': -1.0, 'imag': 0.0}, {'real': 1.0, 'imag': -0.0}, {'real': -1.0, 'imag': 0.0}, {'real': 1.0, 'imag': -0.0}, {'real': 1.0, 'imag': -0.0}, {'real': -1.0, 'imag': 0.0}]`
  - double-group first raw character row: `[{'real': 1.0, 'imag': 0.0}, {'real': 0.0, 'imag': -1.0}, {'real': -1.0, 'imag': -0.0}, {'real': -0.0, 'imag': 1.0}, {'real': -1.0, 'imag': -0.0}, {'real': -0.0, 'imag': 1.0}, {'real': 1.0, 'imag': 0.0}, {'real': 0.0, 'imag': -1.0}]`
- On the chosen minimal block P1-L1-P4, the rep counts remain stable while the raw characters change nontrivially. That is exactly the signature expected from a projective/double-valued lift rather than a mere relabeling.
- Current likely k-space blocker for a full rollout: not extraction itself, but the need for a fresh compatibility/block-construction routine that respects the double-valued character phases.

## Real-Space Feasibility at groupType=2

- Chosen minimal family: `c`.
- Reason: Family c is point-like, purely unitary, and has site symmetry 2/m with stabilizer indices [0,3,4,7]. That makes it the safest first double-group prototype because the local double-valued irreps can be built directly from the projective factor table without the extra Wigner-case machinery needed by antiunitary families.
- Real-space special positions from swyckoff_r.py remain usable because the spatial geometry is unchanged. The chosen family has site symmetry `2/m` and stabilizer `[0, 3, 4, 7]`.
- There is still no direct local double-group builder in the current toolchain: SSGReps handles little-group coreps, but not arbitrary real-space site stabilizers as local double representations.
- For the minimal prototype this is still enough because family c is purely unitary. Its unitary stabilizer carries a nontrivial projective factor table, and that factor table already fixes the admissible double-valued local characters.

## Bridge Feasibility at groupType=2

- Spatial bridge reused unchanged: `r_conv = P r_mag`, `P = diag(1,2,2)`.
- Spatial/time-reversal operation matching after basis change still succeeds on all operations: `16 / 16`.
- This is sufficient to reuse orbit representatives, stabilizer indices, and coset data for the minimal prototype.
- However 16/16 spatial matching is not by itself enough to certify the full double-valued bridge. The missing extra layer is the SU2/projective sign convention, which shows up through factor_su2 = -1 on selected products.

## Induction Feasibility at groupType=2

- The single-group induction formula survives with the same structure on the minimal unitary family:
  - use the same orbit/coset sum,
  - use the same Bloch phase exp(-i k · tauC),
  - but replace the single-group local character by a genuinely double-valued/projective local character.
- For family c, the chosen prototype local irrep uses C2 -> +i, inversion -> +1, mirror -> +i, exactly because factor_su2[3,3] = factor_su2[7,7] = -1.
- That prototype induces exact integer multiplicities on the minimal block:
  - P1: `[0, 0, 2, 0, 0, 0, 0, 2]`
  - L1: `[2, 0, 0, 2]`
  - P4: `[0, 2]`
- Each manifold reconstructs its induced band character exactly from the double little-corep linear characters, so the minimal induction prototype is successful.

## Minimal Double Prototype Verdict

- k-space minimal prototype on P1-L1-P4: `True`.
- real-space minimal prototype on family c: `True`.
- bridge usable for the minimal prototype: `True`.
- induction usable for the minimal prototype: `True`.
- minimal double closure completed: `True`.

## Answer To The Required Questions

### A. k-space side

- A1/A2: yes, groupType=2 stably outputs characters and rep_degree on all previously used endpoints, lines, and planes for this group.
- A3: the obvious change is the appearance of double-valued phases in the raw characters while rep-count/rep-degree patterns stay unchanged on the tested manifolds.
- A4: the current compatibility route still applies in principle because the needed character data exists; the restriction solver must just be rerun with the double-valued characters.
- A5: the first likely failure point for a full rollout is the general compatibility-block builder, not little-corep extraction.

### B. real-space side

- B6/B7: yes, the real-space special positions and audited site stabilizers remain usable input.
- B8: the safest starting families are the unitary point-like families c/f. This script picks c.
- B9: there is no direct existing helper that takes an arbitrary real-space site stabilizer and returns a double local irrep/corep census.
- B10: yes, a minimal prototype can still be built manually from stabilizer indices + group-operation matching + the SSGReps projective factor table.

### C. bridge side

- C11: the basis-change bridge is still spatially correct.
- C12/C13/C14: extra spinor checks are still needed in general. The 16/16 spatial match does not by itself prove the full double-valued convention; the projective sign and 2pi-rotation layer must be tracked separately.

### D. induction side

- D15: yes, the same raw-character plus exp(-i k · tauC) logic still works on the minimal double prototype.
- D16: the orbit sum, lattice-fix filter, and decomposition against linear characters all remain unchanged.
- D17: the extra ingredient is only the local double-valued character itself; for antiunitary families that will require a dedicated Wigner/projective local-corep builder.
