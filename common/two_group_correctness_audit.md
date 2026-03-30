# Two-Group Correctness Audit

## Why Re-Audit These Two Groups

- `10.4.1.31` is the current closed reference line for both single and double workflows.
- `194.1.1.1` is the controlled SG 194 portability case, and its reported `Z^16` raw quotient is the strongest warning sign that the interpretation layer may be drifting away from the standard finite-indicator language.
- Therefore this round separates three logically distinct layers for all four cases: `BS`, `AI / completeness`, and `quotient interpretation`.

## Core Verdict Table

| group | groupType | BS likely correct | AI likely complete | quotient interpretation likely correct | top suspicion | confidence |
| --- | ---: | --- | --- | --- | --- | --- |
| 10.4.1.31 | 1 | true | true | true | AI / AI completeness | medium |
| 10.4.1.31 | 2 | true | true | uncertain | quotient interpretation | high |
| 194.1.1.1 | 1 | uncertain | uncertain | false | quotient interpretation | high |
| 194.1.1.1 | 2 | uncertain | uncertain | false | quotient interpretation | medium |

## Suspicion Rankings

### 10.4.1.31 / groupType=1

- ranking: `AI / AI completeness > quotient interpretation > BS`
- confidence: `medium`
- main issue: No hard contradiction is visible; if forced to pick the weakest layer, the family-level completeness proof is the first one to stress because it depends on the local census assumptions.
- raw quotient: `Z2 x Z2`
- free rank: `0`
- finite part: `[2, 2]`

### 10.4.1.31 / groupType=2

- ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `high`
- main issue: The raw mixed quotient is likely real, but the reporting layer still mixes a full raw quotient with indicator language.
- raw quotient: `Z^2 x Z2 x Z2 x Z2 x Z2`
- free rank: `2`
- finite part: `[2, 2, 2, 2]`

### 194.1.1.1 / groupType=1

- ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `high`
- main issue: The raw quotient Z^16 is free-only and therefore cannot be presented as a standard finite topological indicator group.
- raw quotient: `Z^16`
- free rank: `16`
- finite part: `[]`

### 194.1.1.1 / groupType=2

- ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `medium`
- main issue: The double-group result is again a free-only raw quotient Z^16, while the AI completeness claim still depends on the current projective local library.
- raw quotient: `Z^16`
- free rank: `16`
- finite part: `[]`

## Current Most Reasonable Conclusions

- `10.4.1.31` single-group: the current weakest layer is AI/completeness, but there is no visible contradiction; the finite quotient `Z2 x Z2` is presently the least problematic quotient claim.
- `10.4.1.31` double-group: the raw mixed quotient is plausible, but the interpretation layer must separate the free part `Z^2` from the finite torsion part `Z2^4` before using indicator language.
- `194.1.1.1` single-group: the raw quotient `Z^16` should be read as a free-dominated raw quotient, not as a final finite indicator group.
- `194.1.1.1` double-group: same raw-quotient reinterpretation issue as the single case, with extra caution because the projective local library is newer and therefore the AI completeness layer is less settled.
