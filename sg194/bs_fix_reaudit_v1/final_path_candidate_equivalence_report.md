# Final Path Candidate Equivalence Report

- Endpoint-pair groups inspected: `7`.
- Selected path classes: `['PCLASS01', 'PCLASS02', 'PCLASS03', 'PCLASS05', 'PCLASS06', 'PCLASS08', 'PCLASS09']`.

## P1-P2

- Candidate count: `4`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS01']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS01` from `L1` (candidate `CANDIDATE_PATH_001`) selected = `True`; row-space rank `6`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.

## P1-P3

- Candidate count: `7`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS02']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS02` from `L4` (candidate `CANDIDATE_PATH_013`) selected = `True`; row-space rank `4`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.

## P1-P5

- Candidate count: `16`.
- Strong path-class count: `2`.
- Selected path classes in this pair: `['PCLASS03']`.
- Verdict: Multiple strong path classes share this endpoint pair; only classes whose row language is needed in the canonical full-span subset are kept.

- `PCLASS03` from `L3` (candidate `CANDIDATE_PATH_007`) selected = `True`; row-space rank `4`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.
- `PCLASS04` from `L4` (candidate `CANDIDATE_PATH_014`) selected = `False`; row-space rank `4`; contained in selected span = `False`; reason: Discarded because another strong path class on the same intrinsic special-line family provides the canonical primitive segment used for the final published object.

## P2-P4

- Candidate count: `7`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS05']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS05` from `L7` (candidate `CANDIDATE_PATH_037`) selected = `True`; row-space rank `1`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.

## P2-P6

- Candidate count: `16`.
- Strong path-class count: `2`.
- Selected path classes in this pair: `['PCLASS06']`.
- Verdict: Multiple strong path classes share this endpoint pair; only classes whose row language is needed in the canonical full-span subset are kept.

- `PCLASS06` from `L6` (candidate `CANDIDATE_PATH_031`) selected = `True`; row-space rank `2`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.
- `PCLASS07` from `L7` (candidate `CANDIDATE_PATH_038`) selected = `False`; row-space rank `1`; contained in selected span = `True`; reason: Discarded because another strong path class on the same intrinsic special-line family provides the canonical primitive segment used for the final published object.

## P3-P4

- Candidate count: `4`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS08']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS08` from `L2` (candidate `CANDIDATE_PATH_003`) selected = `True`; row-space rank `6`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.

## P5-P6

- Candidate count: `8`.
- Strong path-class count: `1`.
- Selected path classes in this pair: `['PCLASS09']`.
- Verdict: All candidates collapse to one strong path class.

- `PCLASS09` from `L5` (candidate `CANDIDATE_PATH_025`) selected = `True`; row-space rank `4`; contained in selected span = `True`; reason: Selected as the canonical primitive representative of its intrinsic special-line family: shortest boundary interval first, then listed-line priority, then branch simplicity.
