# Raw Matrix-Level Audit

## Scope

- Fixed groups only: `10.4.1.31` and `194.1.1.1`.
- Fixed cases only: single-group and double-group on those two groups.
- This stage exports raw compatibility matrices, raw BS bases, raw AI candidates, reduced AI bases, exact AI->BS matrices, and exact Smith artifacts for `coker(AI -> BS)`.
- The point is independent linear-algebra reproducibility, not a new physical reinterpretation pass.

## Raw-Object Inventory

| case | raw C | raw BS basis | raw AI candidates | reduced AI basis | AI->BS matrix | raw quotient |
| --- | --- | --- | --- | --- | --- | --- |
| `10.4.1.31` / `1` | `raw_10_4_1_31_single_C.json` | `raw_10_4_1_31_single_bs_basis_raw.json` | `raw_10_4_1_31_single_ai_candidates.json` | `raw_10_4_1_31_single_ai_basis.json` | `raw_10_4_1_31_single_ai_in_bs_matrix.json` | `raw_10_4_1_31_single_quotient.json` |
| `10.4.1.31` / `2` | `raw_10_4_1_31_double_C.json` | `raw_10_4_1_31_double_bs_basis_raw.json` | `raw_10_4_1_31_double_ai_candidates.json` | `raw_10_4_1_31_double_ai_basis.json` | `raw_10_4_1_31_double_ai_in_bs_matrix.json` | `raw_10_4_1_31_double_quotient.json` |
| `194.1.1.1` / `1` | `raw_194_1_1_1_single_C.json` | `raw_194_1_1_1_single_bs_basis_raw.json` | `raw_194_1_1_1_single_ai_candidates.json` | `raw_194_1_1_1_single_ai_basis.json` | `raw_194_1_1_1_single_ai_in_bs_matrix.json` | `raw_194_1_1_1_single_quotient.json` |
| `194.1.1.1` / `2` | `raw_194_1_1_1_double_C.json` | `raw_194_1_1_1_double_bs_basis_raw.json` | `raw_194_1_1_1_double_ai_candidates.json` | `raw_194_1_1_1_double_ai_basis.json` | `raw_194_1_1_1_double_ai_in_bs_matrix.json` | `raw_194_1_1_1_double_quotient.json` |

## Exact Recompute Summary

| case | shape(C) | rank(C) | nullity(C) | rank(BS) | rank(AI) | AI subset BS | raw quotient | free rank | finite part | raw-vs-interpreted gap |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | --- | --- |
| `10.4.1.31` / `1` | `30 x 31` | `23` | `8` | `8` | `8` | `True` | `Z2 x Z2` | `0` | `[2, 2]` | `False` |
| `10.4.1.31` / `2` | `30 x 31` | `23` | `8` | `8` | `6` | `True` | `Z^2 x Z2 x Z2 x Z2 x Z2` | `2` | `[2, 2, 2, 2]` | `True` |
| `194.1.1.1` / `1` | `58 x 62` | `33` | `29` | `29` | `13` | `True` | `Z^16` | `16` | `[]` | `True` |
| `194.1.1.1` / `2` | `58 x 62` | `33` | `29` | `29` | `13` | `True` | `Z^16` | `16` | `[]` | `True` |

## Notes By Case

### 10.4.1.31 / groupType=1

- Recomputed directly from raw exported matrices: `rank(C)=23`, `rank(BS)=8`, `rank(AI)=8`.
- Exact inclusion check `AI ⊂ BS`: `True`.
- Raw quotient from exact Smith audit: `Z2 x Z2`.
- Free rank: `0`; finite torsion part: `[2, 2]`.
- Raw-vs-interpreted gap: `False`.
- Interpretation note carried forward from the correctness audit: The single-group quotient is already purely finite (Z2 x Z2), so there is no free-vs-finite mixing in this case.

### 10.4.1.31 / groupType=2

- Recomputed directly from raw exported matrices: `rank(C)=23`, `rank(BS)=8`, `rank(AI)=6`.
- Exact inclusion check `AI ⊂ BS`: `True`.
- Raw quotient from exact Smith audit: `Z^2 x Z2 x Z2 x Z2 x Z2`.
- Free rank: `2`; finite torsion part: `[2, 2, 2, 2]`.
- Raw-vs-interpreted gap: `True`.
- Interpretation note carried forward from the correctness audit: The double-group quotient contains both a free part and a finite torsion part, so the full Z^2 x Z2^4 should not be called a purely finite indicator group.

### 194.1.1.1 / groupType=1

- Recomputed directly from raw exported matrices: `rank(C)=33`, `rank(BS)=29`, `rank(AI)=13`.
- Exact inclusion check `AI ⊂ BS`: `True`.
- Raw quotient from exact Smith audit: `Z^16`.
- Free rank: `16`; finite torsion part: `[]`.
- Raw-vs-interpreted gap: `True`.
- Interpretation note carried forward from the correctness audit: The raw quotient is purely free (Z^16) and no finite torsion part has been isolated.

### 194.1.1.1 / groupType=2

- Recomputed directly from raw exported matrices: `rank(C)=33`, `rank(BS)=29`, `rank(AI)=13`.
- Exact inclusion check `AI ⊂ BS`: `True`.
- Raw quotient from exact Smith audit: `Z^16`.
- Free rank: `16`; finite torsion part: `[]`.
- Raw-vs-interpreted gap: `True`.
- Interpretation note carried forward from the correctness audit: The raw quotient is again purely free (Z^16) and no finite torsion part has been isolated.

## Independent Recompute Path

- The minimal external recompute directory is `independent_recompute_minipack/`.
- It contains a local copy of every `raw_*.json` file needed by the four cases plus a standalone `recompute_from_raw.py` script that only depends on `json` and `sympy`.
- The recompute script redoes `rank(C)`, the kernel rank, the AI rank, the exact check `AI ⊂ BS`, and the Smith decomposition of `coker(AI -> BS)`.
