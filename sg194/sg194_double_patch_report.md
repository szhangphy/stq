# SG194 Double Patch Report

## 1. Problem History and Why Audits Alone Were Insufficient

Previous SG194 rounds localized the double mismatch to the `2b/2c/2d/6h` sector, but the local package still had no source-of-truth builder for the current `33`-column spinorial generators. The only source-level object was the `45`-candidate local-irrep induction output, and every later SG194 double file compensated with downstream hardcoded merges. That is why the mismatch could be diagnosed repeatedly without actually shrinking.

## 2. Finding the Real Bug Source

The raw writer `debug_raw_matrix_audit.py` was not the real bug source. It serializes whatever the stage-2 induction layer gives it. The real missing layer sat in `debug_workflow_portability_stage2_194.1.1.1.py`: stage-2 could induce the `45` local-irrep candidates, but it could not yet build the current SG194 double spinorial generators themselves.

## 3. Concrete Code Patches

The patch adds `build_sg194_double_spinorial_generators(...)` to the stage-2 source layer. Two profiles now exist:

- `legacy`: the old pair-sum / four-way-sum channelization.
- `sg194_double_anchor_patch_v1`: the patched SG194 channelization.

The exact structured solve showed that the heuristic “fix only `2c/2d E1` and rescale `6h`” did not have an exact local-block solution. The smallest exact source-level fix that kills the trusted problem-sector mismatch is:

- `c:E3 -> 2*c:E3 - b:E3`
- `d:E3 -> 2*d:E3 - b:E3`
- `6h:E -> 6h:E - b:E3`

Here `b:E3`, `c:E3`, and `d:E3` are the stage-2 channels obtained from the corresponding pairwise sums of the `proj_doubleprime_2d_5/6` candidates.

## 4. Before/After AI Comparison

Trusted problem-sector metrics:

- before: current/external/problem-union/problem-intersection = `6 / 6 / 8 / 4`
- after: current/external/problem-union/problem-intersection = `6 / 6 / 6 / 6`

Therefore the explicit trusted SG194 double problem-sector mismatch is removed exactly. In particular:

- `delta_c1_minus_b1` disappears.
- `delta_d1_minus_b1` disappears.

## 5. Problem-Sector Rank Changes

The hoped-for direct full-rank collapse from `12` to `10` was **not** achieved in the broader `33`-column current-HSP comparison:

- before full current rank: `12`
- after full current rank: `12`

So the patched current builder removes the trusted localized SG194 bug, but a wider all-sector current/external row-language gap still remains.

## 6. Updated Diagnosis and Next Step

The current round finally moved beyond audit-only work:

- the real source patch is in the stage-2 generator-construction code;
- patched raw artifacts were regenerated;
- the trusted SG194 double problem sector is fixed.

However BS-only is still not the next justified step. The next step is to finish the all-sector current-to-external spinorial canonicalization outside the already fixed `2b/2c/2d/6h` sector, then re-evaluate whether BS-only has become meaningful.

## Implementation Mapping

- source patch: `debug_workflow_portability_stage2_194.1.1.1.py`
- patched driver: `debug_sg194_double_patch.py`
- patched raw artifacts: `raw_194_1_1_1_double_ai_candidates_patched.json`, `raw_194_1_1_1_double_ai_basis_patched.json`, `raw_194_1_1_1_double_ai_in_bs_matrix_patched.json`
- before/after comparison: `sg194_double_ai_patch_before_after.json`
