# Single Group Real-Space Audit

## Scope
- Group: `10.4.1.31`
- Stage: real-space / atomic-side feasibility audit only.
- Out of scope: full AI/EBR/MTQC, all-group generalization, or any final topology classification.

## A. swyckoff_r.py: Real Input / Output
- File audited: `swyckoff_r.py`.
- There is no `swyckoff.py` file in the current repository root, so the real-space audit cannot rely on it.
- Primary programmatic entry point: `compute_wyckoff_output(data_or_ssgnum, kspace=False, basis="primitive", stars=False, fast=False)`.
- For this run it was called as `compute_wyckoff_output("10.4.1.31", fast=True)`.
- Accepted input is either a real-space SSG data dictionary or an SSG number string; the string path goes through `load_irssg_data`.
- Output is a tuple `(wyckoff_entries, coord_key)` with `coord_key = 'orbit_with_moments'` in real-space mode.
- Each entry carries enough real-space geometry for audit use: `letter`, `mult`, `dim`, `x0`, `basis_vecs`, `rep`, `orbit`, `representative_coordinate`.
- It also carries site-symmetry summaries: `stab`, `stab_rotations`, `site_symmetry`, `unitary_site_symmetry`, `site_symmetry_custom`, `site_symmetry_ops`, `spatial_site_symmetry_custom`, `spatial_site_symmetry_ops`.
- It does not directly expose the full stabilizer element list; the program output is a summary plus generator-like descriptors, not a raw stabilizer table.

## B. Real-Space Data Retrieved For 10.4.1.31
- `swyckoff_r.py` returns `15` Wyckoff-like real-space families for `10.4.1.31`.
- The generic family is `o` with multiplicity `16`, dimension `3`, and trivial stabilizer size `1`.
- Special families are `a` through `n`; they are distinguishable from the generic family by smaller multiplicity and larger stabilizer.

| Let | mult | dim | representative_coordinate | site_symmetry | unitary_site_symmetry |
| --- | ---: | ---: | --- | --- | --- |
| o | 16 | 3 | `x, y, z` | `1` | `1` |
| n | 8 | 2 | `x, 1/4, z` | `m'` | `1` |
| m | 8 | 2 | `x, 0, z` | `m` | `?` |
| l | 8 | 1 | `1/2, y, 1/4` | `2` | `?` |
| k | 8 | 1 | `0, y, 1/4` | `2` | `?` |
| j | 8 | 1 | `1/2, y, 0` | `2'` | `1` |
| i | 8 | 1 | `0, y, 0` | `2'` | `1` |
| h | 4 | 0 | `1/2, 1/4, 1/4` | `2/m'` | `?` |
| g | 4 | 0 | `0, 1/4, 1/4` | `2/m'` | `?` |
| f | 4 | 0 | `1/2, 0, 1/4` | `2/m` | `?` |
| e | 4 | 0 | `1/2, 1/4, 0` | `2'/m'` | `?` |
| d | 4 | 0 | `0, 1/4, 0` | `2'/m'` | `?` |
| c | 4 | 0 | `0, 0, 1/4` | `2/m` | `?` |
| b | 4 | 0 | `1/2, 0, 0` | `2'/m` | `?` |
| a | 4 | 0 | `0, 0, 0` | `2'/m` | `?` |

## C. Setting Consistency
- `swyckoff_r.py` and `swyckoff_k.py` do load the same standardized SSG operation list for this group.
- Same SSG number: `True`.
- Same `source_centering_symbol`: `True`.
- Same standardized operations: `True`.
- Same standardized time-reversal tags: `True`.
- Therefore the real-space and k-space geometry layers are aligned at the `swyckoff_r.py` / `swyckoff_k.py` level.
- The separate risk is the bridge to `SSGReps.py`, not the bridge between the two swyckoff modules.

## D. Site Symmetry Availability
- `single_group_site_symmetry_check.json` confirms summary-vs-direct consistency for all `15` families.
- `swyckoff_r.py` is sufficient to provide usable real-space special-position data for this single-group audit.
- It is also sufficient to reconstruct full stabilizers directly because the standardized group operations are available locally.

## E. Prototype Candidates
- Best future starting points for a minimal atomic prototype are the smallest 0D families with purely unitary stabilizers.
- `f`: rep `1/2, 0, 1/4`, multiplicity `4`, site symmetry `2/m`. 0D point family with multiplicity 4 and fully unitary stabilizer; simplest future starting point for a unitary-subgroup atomic prototype.
- `c`: rep `0, 0, 1/4`, multiplicity `4`, site symmetry `2/m`. 0D point family with multiplicity 4 and fully unitary stabilizer; simplest future starting point for a unitary-subgroup atomic prototype.

## F. Why AI Is Still Blocked
- `SSGReps.py` does provide k-side little-group characters and rep degrees, but its internal magnetic-cell convention is not a drop-in real-space convention for `swyckoff_r.py` coordinates.
- Internal `SSGReps` supercell summary: `superCell = [[1, 0, 0], [0, 2, 0], [0, 0, 2]]`, `pure_T = [[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]]`.
- A naive real-space stabilizer check using `SSGReps` internal `rotC/tauC` on `a/c/f` does not reproduce the `swyckoff_r.py` stabilizers, so local-to-k induction is not trustworthy without an explicit basis/gauge bridge.
- That missing bridge is the current blocker, so the present run stops at feasibility audit instead of fabricating an AI vector.
