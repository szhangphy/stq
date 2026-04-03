# Final Path Candidate Equivalence Report

- Endpoint-pair groups inspected: `7`.
- Selected path classes: `['PCLASS01', 'PCLASS02', 'PCLASS03', 'PCLASS04', 'PCLASS05', 'PCLASS06', 'PCLASS08', 'PCLASS09']`.

## P1-P2

- Candidate count: `4`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS01']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS01` from `L1` (candidate `CANDIDATE_PATH_001`) selected = `True`; row-space rank `6`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.

## P1-P3

- Candidate count: `7`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS02']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS02` from `L4` (candidate `CANDIDATE_PATH_013`) selected = `True`; row-space rank `4`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.

## P1-P5

- Candidate count: `16`.
- Strong path-class count: `2`.
- Selected path classes in this pair: `['PCLASS03', 'PCLASS04']`.
- Verdict: Multiple strong path classes share this endpoint pair, and more than one must be retained because the endpoint-pair skeleton alone does not span the full candidate row language.

- `PCLASS03` from `L3` (candidate `CANDIDATE_PATH_007`) selected = `True`; row-space rank `4`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected first as the canonical endpoint-pair skeleton representative, then retained in the published shell together with an additional same-endpoint path class because the skeleton alone did not span the full candidate row language.
- `PCLASS04` from `L4` (candidate `CANDIDATE_PATH_014`) selected = `True`; row-space rank `4`; selection stage = `full_span_augmentation`; contained in selected span = `True`; reason: Added after the canonical endpoint-pair skeleton because it contributes independent row language not present in the skeleton span (rank 23 -> 24).

## P2-P4

- Candidate count: `7`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS05']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS05` from `L7` (candidate `CANDIDATE_PATH_037`) selected = `True`; row-space rank `1`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.

## P2-P6

- Candidate count: `16`.
- Strong path-class count: `2`.
- Selected path classes in this pair: `['PCLASS06']`.
- Verdict: Multiple strong path classes share this endpoint pair; only classes whose row language is already contained in the published full-span shell are discarded.

- `PCLASS06` from `L6` (candidate `CANDIDATE_PATH_031`) selected = `True`; row-space rank `2`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `PCLASS07` from `L7` (candidate `CANDIDATE_PATH_038`) selected = `False`; row-space rank `1`; selection stage = `discarded`; contained in selected span = `True`; reason: Discarded because the published full-span selection already contains its row language after endpoint-pair skeleton selection and rank-closing augmentation.

## P3-P4

- Candidate count: `4`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS08']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS08` from `L2` (candidate `CANDIDATE_PATH_003`) selected = `True`; row-space rank `6`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.

## P5-P6

- Candidate count: `8`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS09']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS09` from `L5` (candidate `CANDIDATE_PATH_025`) selected = `True`; row-space rank `4`; selection stage = `endpoint_pair_skeleton`; contained in selected span = `True`; reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
