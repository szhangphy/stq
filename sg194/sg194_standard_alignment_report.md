# SG194 Standard Alignment Report

## 1. Task Background And Current State

The prior external SG 194 AI audit already established that the ordinary single-valued AI inventory is externally complete at rank 13, while the double-valued current library is not aligned to Bilbao's physically irreducible spinorial generator convention. This report resolves the next two hard problems:

1. Single: replace the current enlarged 29-dimensional raw BS ambient space by a standard SG 194 symmetry-data layer.
2. Double: replace the current 45-label local-corep inventory by an explicit Bilbao-style spinorial count convention and measure the remaining mismatch.

## 2. External SG194 AI Audit Recap

- Single external AI rank: `13`
- Double external spinorial AI rank: `10`
- Current raw single AI rank: `13`
- Current raw double AI rank: `13`

The single mismatch is therefore not at the AI layer, while the double mismatch still mixes AI-basis inflation with a non-standard BS ambient space.

## 3. Single: Raw BS vs Standard Symmetry-Data Space

Let the current raw BS basis coordinates be `x \in \mathbb{Q}^{29}`, the current `AI \to BS` matrix be `M \in \mathbb{Z}^{29 \times 13}`, and the external ordinary SG 194 AI basis be `B_{std} \in \mathbb{Z}^{34 \times 13}`. We extend the AI columns of `M` to a full basis `[M\;C]` of the raw BS coordinate space and define

\[
P_{\mathrm{single}} = B_{\mathrm{std}}
\begin{bmatrix} I_{13} & 0 \end{bmatrix}
[M\;C]^{-1}.
\]

This exact rational map satisfies

\[
P_{\mathrm{single}} M = B_{\mathrm{std}}, \qquad
P_{\mathrm{single}} C = 0.
\]

Hence the 16 complement columns in `C` are the explicit enlarged-space directions that were responsible for the raw `Z^{16}`.

Single recomputed result:

- Raw quotient: `Z^16`
- Standard-space quotient: `trivial`

## 4. Double: Current Basis vs Bilbao Spinorial Basis

Bilbao's physically irreducible spinorial BANDREP inventory for ordinary SG 194 contains 33 generators with global rank 10. The current `194.1.1.1` double library contains 45 generators and rank 13.

The explicit count alignment constructed here is:

- `2b`, `2c`, `2d`: merge current `6` labels into Bilbao-style `3` channels by pairing `(1,2)`, `(3,4)`, and `(5,6)`.
- `6h`: merge current `4` labels into one Bilbao-style `E` channel.
- `2a`, `4e`, `4f`, `6g`, `12i`, `12j`, `12k`, `24l`: keep one-to-one.

This yields an explicit `45 \to 33` alignment matrix, but the resulting current span still has rank `12` rather than Bilbao's rank `10`. Therefore the current basis mismatch is only partially removed.

## 5. Standard-Space Quotient Recomputation

Single:

- `rank(BS_{std}) = 13`
- `rank(AI_{std}) = 13`
- `BS_{std} / AI_{std} = trivial`

Double:

- count-aligned current AI rank = `12`
- Bilbao spinorial standard AI rank = `10`
- standard-space quotient = blocked

## 6. User-Facing Conclusions

- Single should no longer be described by the raw `Z^16`; the ordinary standard-space quotient is `trivial` after removing the 16 enlarged-space directions explicitly.
- Double should still not be described by the raw `Z^16`; even after explicit 2b/2c/2d/6h count alignment, the AI layer remains rank-12 vs rank-10 and the BS projection is therefore still not settled.

## 7. Remaining Blocker And Next Step

- Single blocker: none at the ordinary standard-space level.
- Double blocker: resolve the remaining rank-2 gap after count alignment, then build the double standard-space BS projection in the same Bilbao spinorial row basis.

## 8. Implementation Mapping

- Single projection matrix and complement basis: `sg194_single_standard_space_map.json`
- Double 45 -> 33 alignment matrix and sitewise merges: `sg194_double_spinorial_alignment.json`
- Recomputed standard-space quotient summaries: `sg194_single_standard_quotient_recomputed.json`, `sg194_double_standard_quotient_recomputed.json`
- Consolidated audit: `sg194_standard_alignment_audit.md`, `sg194_standard_alignment_summary.json`
