# SG194 194.1.1.1 Final Standard-Space Closeout Report v1

- Current time: 2026-03-31 20:05:18 +0800
- Repo root: `/data/work/szhang/ssg/comprel/stq_repo_export/repo`
- Branch: `sg194-special`
- Latest synced `sg194-special`: `36a66b7`
- Latest synced `main`: `a7b4e4d`

## Scope

This phase is the final standard-space reduction / final BS=13 closeout on top of clean baseline `36a66b7`. It does not reopen:

1. repo-consistency closeout,
2. package/import portability,
3. legacy `bs_ai_separation`,
4. double-complement mathematics.

## Current 34-row point-space

The authoritative runtime ambient is the 42-row ordering
`P1..P6` plus synthetic `S1..S4`.
The physical current point-space shell is the first 34 rows:

1. `P1` with 12 rows,
2. `P2` with 3 rows,
3. `P3` with 6 rows,
4. `P4` with 3 rows,
5. `P5` with 8 rows,
6. `P6` with 2 rows.

The synthetic rows `S1_R1` through `S4_R2` are excluded from the final ordinary projection.

## Final standard ordinary SG194 space

The final ordinary SG194 standard comparison space is the external 34-row row language on:

1. `GM` with 12 rows,
2. `A` with 3 rows,
3. `K` with 6 rows,
4. `H` with 3 rows,
5. `M` with 8 rows,
6. `L` with 2 rows.

This row ordering is stored in `sg194_current_to_standard_row_translation_v1.json` and `sg194_standard_space_projection_summary_v1.json`.

## Mapping object

The current-to-standard mapping is now explicit.

1. Block identification:
   - `P1 -> GM`
   - `P2 -> A`
   - `P3 -> K`
   - `P4 -> H`
   - `P5 -> M`
   - `P6 -> L`
2. Quotient/elimination contract:
   - mapping type = `block_identification_plus_common_bs_quotient_elimination_contract`
   - projection contract = `common_bs_coordinate_projection_anchored_on_external_ordinary_AI_and_killing_common_Z3_free_generators`
3. The projection is a matrix from the common 16-dimensional current BS coordinate space into the external ordinary 34-row standard shell.
4. It is anchored on the common 13-generator AI basis and kills the three shared free generators that had kept the raw internal quotient at `Z^3`.

The three killed directions are:

1. `common_free_generator_1`: `P3_R5:-1, P3_R6:+1`
2. `common_free_generator_2`: `P3_R5:+1, P4_R1:+1`
3. `common_free_generator_3`: `P3_R1:+1, P3_R2:+1, P4_R3:+1`

## Final mechanical results

Single:

1. raw `rank(BS) = 16`
2. raw `rank(AI) = 13`
3. final `rank(BS) = 13`
4. final `rank(AI) = 13`
5. final quotient = `trivial`

Double:

1. raw `rank(BS) = 16`
2. raw `rank(AI) = 13`
3. final `rank(BS) = 13`
4. final `rank(AI) = 13`
5. final quotient = `trivial`

## Verification

1. `python3 -m py_compile common/*.py`
2. `python3 -m py_compile sg194/*.py`
3. `python3 sg194/debug_sg194_standard_space_projection_v1.py --validate`
4. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py`
5. `python3 -c '<load stage2 module, rebuild report tex/pdf from authoritative JSON, run compile_report()>'`
6. `python3 sg194/debug_workflow_portability_stage2_194.1.1.1.py --validate`

## Next

1. Stage only in-scope projection, stage2, and checkpoint outputs.
2. Commit on `sg194-special`.
3. Push `origin/sg194-special`.
