# SG194 BS-vs-AI Separation Report

## 0. Status

This report is a **legacy/stale reference**, not current-snapshot evidence for the live SG194 `194.1.1.1` repo state.

- analysis_status: `legacy_stale_reference`
- active_current_evidence: `False`
- current authoritative note: Current authoritative SG194 evidence now lives in the stage2 closeout outputs, not in this legacy/stale BS-vs-AI separation package.
- current repo point blocks: `P1, P2, P3, P4, P5, P6`
- legacy internal selection blocks used here: `P1, P2, P3, P5, P6, B1`
- status explanation: This script remains a legacy/stale reference. Its internal selection surface still follows the older P1/P2/P3/P5/P6/B1 block choice and therefore must not be treated as the current 194.1.1.1 point-space audit, whose live snapshot uses P1 through P6. It is retained only to preserve the historical BS-vs-AI object-separation diagnosis.
- current authoritative outputs to cite instead: `workflow_portability_report_stage2_194.1.1.1.pdf, workflow_portability_stage2_summary_194.1.1.1.json, current_status_194.1.1.1_stage2.json, handoff_194.1.1.1_stage2.md, review_package_sg194_stage2_closeout_followup_v2.tar.gz`

## 1. Problem Background And Previous Mis-attribution

The previous `external_matrix_final` stage compared internal AI/generator images against cached external matrices and then described the result as a BS-space mismatch. That attribution was too strong. An AI-image mismatch can imply that the current atomic-generator layer is not externally aligned, but it cannot by itself prove that the BS layer is misaligned.

This stage corrects that object confusion by separating:

- AI-only external comparison
- BS-only external comparison

for both single and double.

## 2. Single: AI-only External Comparison

Current single AI is represented by the `45` raw AI candidates restricted to the `34` selected HSP rows. The external comparison object is the cached Bilbao ordinary `34 x 45` generator matrix.

These two matrices live in different row bases but in the same `45`-generator domain after exact generator-id reordering. Therefore the correct invariant is their row-space comparison in
\[
\mathbb{Z}^{45}.
\]

The result is:
- current rank = `13`
- external rank = `13`
- union rank = `14`
- intersection rank = `12`

So the single AI mismatch is exactly one-dimensional.

## 3. Single: BS-only External Comparison

Current single BS is represented by the projected current BS basis in the non-AI-anchored `34`-row point-space used in the v2 stage. The external comparison object is the ordinary SG194 standard symmetry-data span represented by the same cached Bilbao `34 x 45` ordinary generator matrix.

In this ambient `34`-row point-space, one compares column spaces:
\[
\mathrm{Col}(B_{\mathrm{cur}}^{\mathrm{single,HSP}}) \subset \mathbb{Z}^{34},
\qquad
\mathrm{Col}(E_{\mathrm{ord}}) \subset \mathbb{Z}^{34}.
\]

The result is:
- current rank = `18`
- external rank = `13`
- union rank = `26`
- intersection rank = `5`

This is a strong BS-space mismatch, not just an AI mismatch. The old v1 `trivial` must stay retired; the old `Z^5` is only an internal current-point-space BS/AI gap.

## 4. Double: AI-only External Comparison

For double, the exact external object available locally is the cached Bilbao physically irreducible spinorial `56 x 33` generator matrix. The current side can be aligned honestly only in the explicit `2b/2c/2d/6h` problem sector, where the v2 stage already fixed representation-content merges.

In that explicit problem sector:
- current merged rank = `6`
- external rank = `6`
- union rank = `8`
- intersection rank = `4`

Therefore `delta_c1_minus_b1` and `delta_d1_minus_b1` are AI excess directions in the current problem-sector generator image.

## 5. Double: BS-only External Comparison

The BS-only comparison for double is still blocked. The current double BS basis is only available after restriction to the `34` current point coordinates, whereas the cached external spinorial object is an AI generator matrix in a `56`-row Bilbao basis. No BS-only lift
\[
\mathbb{Z}^{34} 	o \mathbb{Z}^{56}
\]
has been fixed without reusing AI anchoring, and there is no independently cached external double BS basis/span.

So the correct conclusion is not “double BS mismatch proven”, but rather:
- double AI mismatch is proven,
- double BS mismatch is not yet separately established.

## 6. Final Diagnosis

- single main issue: `both`
- double main issue: `AI`

Updated interpretation:
- single: both AI and BS are externally misaligned, with the BS mismatch stronger
- double: AI mismatch is proven; BS comparison remains blocked/unresolved

## 7. Implementation Mapping

- single AI-only output: `sg194_single_ai_vs_external.json`
- single BS-only output: `sg194_single_bs_vs_external.json`
- double AI-only output: `sg194_double_ai_vs_external.json`
- double BS-only output: `sg194_double_bs_vs_external.json`
- summary: `sg194_bs_ai_separation_summary.json`
