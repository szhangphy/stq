# Single Group AI Feasibility Audit

## Scope
- Group: `10.4.1.31`
- Stage: single-group real-space feasibility audit, not final BS/AI and not final topology classification.

## A. Current k-Space Prerequisite
- Current trusted with-planes BS matrix shape: `30 x 31`.
- Integer rank / nullity: `23` / `8`.
- Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`.
- Current with-planes unknown ordering has `31` coordinates and is already a usable target lattice for any future atomic projection.
- The torsion `2` is not the blocker at this stage. It only means any future BS/AI comparison must remain an integer-lattice comparison, not a rational-vector comparison.

## B. Real-Space Data Verdict
- `swyckoff_r.py` is sufficient for this group's real-space special-position enumeration.
- Representative coordinates, orbit data, multiplicity, and site-symmetry summaries are all present.
- The full stabilizer element list is not printed directly, but it can be reconstructed from the standardized operations exposed by the same module.
- Site-symmetry double-check status: `True` across `15` audited families.

## C. What Exists Versus What Is Missing
- Existing and usable:
  - trusted `swyckoff_r.py` real-space families;
  - trusted `swyckoff_k.py` / with-planes BS unknown ordering;
  - `SSGReps.py` k-side little-group characters and rep degrees on the current point/plane representatives.
- Missing or not yet aligned:
  - a direct table of site-symmetry irreps/coreps for the real-space stabilizers;
  - a checked coordinate/gauge bridge from `swyckoff_r.py` real-space operations to `SSGReps.py` raw little-group operations;
  - an existing helper that induces local real-space reps into the current k-space basis without resorting to unreviewed ad hoc translation conventions.

## D. Why The Minimal AI Prototype Stops Here
- Minimal blocker: No trustworthy local-to-k induction path exists yet: swyckoff_r real-space coordinates/stabilizers and SSGReps raw little-group operations are not in a directly matched translation/gauge convention, and the repository exposes no existing helper that aligns them.
- Concrete evidence:
  - `SSGReps` internal cell summary is `[[1, 0, 0], [0, 2, 0], [0, 0, 2]]`, so its translation convention is not the same object that `swyckoff_r.py` exposes as primitive-like fractional coordinates.
  - Naively applying `SSGReps` internal operations to the `a/c/f` real-space coordinates gives stabilizer sizes `{'a': 16, 'c': 8, 'f': 8}`, which do not agree with the double-checked `swyckoff_r.py` stabilizers.
  - A direct exact-key match already fails on a raw P1 little-group operation: `{'raw_operation_index': 2, 'rotation': [['-1', '0', '0'], ['0', '1', '0'], ['0', '0', '-1']], 'translation': ['0', '0', '0']}`.
- Because of that mismatch, any current local-to-k induction result would depend on an unchecked convention choice and would not be a reliable AI prototype.

## E. Best Future Prototype Starting Points
- `f`: multiplicity `4`, rep `1/2, 0, 1/4`, direct site symmetry `2/m`.
- `c`: multiplicity `4`, rep `0, 0, 1/4`, direct site symmetry `2/m`.

## Final Verdict
- `real_space_data_available = true`
- `site_symmetry_double_checked = true`
- `site_symmetry_rep_available = false` in the strict sense required for atomic induction: there is no direct local-rep/corep table tied to the audited real-space stabilizers.
- `can_build_minimal_ai_prototype = false`
- `can_compare_bs_vs_ai_min = false`

## Next Tooling Step
- Implement and validate an explicit bridge between `swyckoff_r.py` real-space operations and the `SSGReps.py` little-group operation convention, including its `superCell/pure_T` translation gauge. Once that bridge exists, start the first minimal induction on the trusted `c` and `f` point families.
