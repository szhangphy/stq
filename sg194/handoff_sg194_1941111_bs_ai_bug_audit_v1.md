# SG194 194.1.1.1 Live Checkpoint

- Current time: 2026-03-31 23:11:58 +0800
- Branch: `sg194-special`
- HEAD: `70fdd3f`

## Confirmed Findings

1. The raw internal BS gap is carried by exactly three common free generators: P3_R5-P3_R6, P3_R5+P4_R1, and P3_R1+P3_R2+P4_R3.
2. Those generators are only touched by the three L2 rows, and no plane row touches P3/P4 at all.
3. build_line_block/build_plane_block use phase-stripped character, while induce_candidate uses linear_character together with explicit Bloch phase exp(-ik·t).
4. The phase/subduction audit therefore points to a little-co-group vs full little-group mismatch as the implementation cause of the missing effective constraints.
5. The extracted v3 package full rerun passed = True and regenerated the expected stage2/projection/report outputs inside the extracted package.

## Commands Run

1. `python3 sg194/debug_sg194_upstream_raw_bs_gap_audit_v1.py`
2. `python3 sg194/debug_sg194_package_full_rerun_test_v1.py`
3. `python3 -m py_compile common/*.py`
4. `python3 -m py_compile sg194/*.py`

## Next Actions

1. Review the in-scope diff for the two new audit scripts and generated audit outputs.
2. Commit the raw-gap / phase / package-full-rerun audit files.
3. Push origin/sg194-special.
