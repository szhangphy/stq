# SG194 Upstream Raw BS Fix Plan v1

## Diagnosis

- The raw `Z^3` does not come from the final standard projection layer. It is already present upstream because the current P3/P4 sector is only constrained by the three `L2` equations.
- Those `L2` equations are built in `build_line_block()` from the phase-stripped `character` object, while `induce_candidate()` later uses `linear_character` together with an explicit Bloch phase factor.
- No plane row touches `P3/P4`, so the K/H sector never receives a second-stage gluing constraint inside the current raw builder.

## Most Likely Repair Direction

1. Split the compatibility builder into two explicit modes: a raw co-group audit mode and a full phase-aware little-group subduction mode.
2. For the phase-aware mode, stop treating `character` as the authoritative restriction object on nonsymmorphic lines/planes. Use `linear_character` or an equivalent projective/little-group object with a common phase convention.
3. Rework `build_line_block()` and `build_plane_block()` so the endpoint-to-line and point-to-plane solve is done in the same phase convention that `induce_candidate()` uses later.
4. Start with the `L2 <- {P3,P4}` sector only. It is the unique place where the three common free directions live.
5. After the `L2` sector is phase-aware, rerun the raw BS analysis and check whether `rank_bs_raw_internal` drops from `16` to `13` before any external standard projection is applied.

## Why This Is Not A Small Patch

- The current raw-character compatibility solve is intentionally integral. Switching to a phase-aware solve changes the object being restricted, not just a coefficient or endpoint lookup.
- The present `linear_character` solve on `L2` is inconsistent under the old integer-only rule, so a direct `character -> linear_character` text swap is not sufficient.

## Minimal Success Metric

- Recompute the raw upstream stage without the external standard projection contract.
- Success means: raw `rank(BS)` becomes `13`, raw `quotient_group` becomes finite/trivial as appropriate, and the three current `common_free_generators` disappear from the upstream quotient extraction.

## Current References

- gap audit: `sg194_upstream_raw_bs_gap_audit_v1.json`
- phase audit: `sg194_phase_and_subduction_audit_v1.json`
- stage1 compatibility builder: `sg194/debug_workflow_portability_194.1.1.1.py`
- phase formula source: `common/SSGReps.py`
