# SG194 BS-vs-AI Separation Audit

## Status
- analysis_status: `legacy_stale_reference`
- active_current_evidence: `False`
- current repo point blocks: `P1, P2, P3, P4, P5, P6`
- legacy internal selection blocks: `P1, P2, P3, P5, P6, B1`
- status explanation: This script remains a legacy/stale reference. Its internal selection surface still follows the older P1/P2/P3/P5/P6/B1 block choice and therefore must not be treated as the current 194.1.1.1 point-space audit, whose live snapshot uses P1 through P6. It is retained only to preserve the historical BS-vs-AI object-separation diagnosis.

## Previous Mis-attribution
- previous external_matrix_final mixed up AI-image comparison with BS-space comparison.

## Single
- Main issue: `both`
- AI ranks / union: `13`, `13`, `14`
- BS ranks / union: `18`, `13`, `26`

## Double
- Main issue: `AI`
- AI ranks: raw `13`, merged `12`, external `10`
- AI problem-sector union rank: `8`
- BS comparison status: `blocked`

## Updated Conclusions
- Single: AI-only mismatch is one-dimensional in the 45-generator domain, and BS-only mismatch is stronger in the 34-row point-space ambient (current rank 18 vs external rank 13, intersection rank 5).
- Double: AI-only mismatch is proven in the explicit 2b/2c/2d/6h problem sector; BS-only external comparison remains blocked because no BS-only lift to the 56-row Bilbao spinorial basis has been fixed.
