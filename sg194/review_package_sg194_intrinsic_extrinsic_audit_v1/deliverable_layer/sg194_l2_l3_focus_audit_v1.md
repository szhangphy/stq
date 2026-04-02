# SG194 194.1.1.1 L2 / L3 Focus Audit

## 目标

- 比较 `coarse / intrinsic / extrinsic` 三套 builder 在 `L2` 和 `L3` 上到底加了什么。
- 明确哪些行是纯当前 line intrinsic restriction 关系，哪些行只有 extrinsic star/plane augmentation 才会出现。

## single

- `L2` row counts: coarse `3`, intrinsic `5`, extrinsic `8`.
- `L3` row counts: coarse `4`, intrinsic `9`, extrinsic `16`.

### L2

- `intrinsic`:
`L2_intrinsic_class_01`  class_members=['P4_R3']  uses_extrinsic=False
`L2_intrinsic_class_02`  class_members=['P3_R5', 'P3_R6']  uses_extrinsic=False
`L2_intrinsic_class_03`  class_members=['P3_R2', 'P3_R3']  uses_extrinsic=False
`L2_intrinsic_class_04`  class_members=['P3_R1', 'P3_R4']  uses_extrinsic=False
`L2_intrinsic_class_05`  class_members=['P4_R1', 'P4_R2']  uses_extrinsic=False
- `extrinsic`:
`L2_extrinsic_class_01`  class_members=['P3_R3']  uses_extrinsic=True
`L2_extrinsic_class_02`  class_members=['P3_R1']  uses_extrinsic=True
`L2_extrinsic_class_03`  class_members=['P3_R2']  uses_extrinsic=True
`L2_extrinsic_class_04`  class_members=['P3_R4']  uses_extrinsic=True
`L2_extrinsic_class_05`  class_members=['P3_R5']  uses_extrinsic=True
`L2_extrinsic_class_06`  class_members=['P3_R6']  uses_extrinsic=True
`L2_extrinsic_class_07`  class_members=['P4_R3']  uses_extrinsic=True
`L2_extrinsic_class_08`  class_members=['P4_R1', 'P4_R2']  uses_extrinsic=True

### L3

- `intrinsic`:
`L3_intrinsic_class_01`  class_members=['P1_R1', 'P1_R8']  uses_extrinsic=False
`L3_intrinsic_class_02`  class_members=['P1_R2', 'P1_R7']  uses_extrinsic=False
`L3_intrinsic_class_03`  class_members=['P5_R3', 'P5_R6']  uses_extrinsic=False
`L3_intrinsic_class_04`  class_members=['P1_R10', 'P1_R11']  uses_extrinsic=False
`L3_intrinsic_class_05`  class_members=['P1_R4', 'P1_R5', 'P5_R4', 'P5_R5']  uses_extrinsic=False
`L3_intrinsic_class_06`  class_members=['P1_R3', 'P1_R6']  uses_extrinsic=False
`L3_intrinsic_class_07`  class_members=['P5_R2', 'P5_R7']  uses_extrinsic=False
`L3_intrinsic_class_08`  class_members=['P5_R1', 'P5_R8']  uses_extrinsic=False
`L3_intrinsic_class_09`  class_members=['P1_R9', 'P1_R12']  uses_extrinsic=False
- `extrinsic`:
`L3_extrinsic_class_01`  class_members=['P1_R2']  uses_extrinsic=True
`L3_extrinsic_class_02`  class_members=['P1_R3']  uses_extrinsic=True
`L3_extrinsic_class_03`  class_members=['P1_R1']  uses_extrinsic=True
`L3_extrinsic_class_04`  class_members=['P1_R4']  uses_extrinsic=True
`L3_extrinsic_class_05`  class_members=['P1_R6']  uses_extrinsic=True
`L3_extrinsic_class_06`  class_members=['P1_R7']  uses_extrinsic=True
`L3_extrinsic_class_07`  class_members=['P1_R5']  uses_extrinsic=True
`L3_extrinsic_class_08`  class_members=['P1_R8']  uses_extrinsic=True
`L3_extrinsic_class_09`  class_members=['P1_R10']  uses_extrinsic=True
`L3_extrinsic_class_10`  class_members=['P1_R9']  uses_extrinsic=True
`L3_extrinsic_class_11`  class_members=['P1_R11']  uses_extrinsic=True
`L3_extrinsic_class_12`  class_members=['P1_R12']  uses_extrinsic=True
`L3_extrinsic_class_13`  class_members=['P5_R2', 'P5_R7']  uses_extrinsic=True
`L3_extrinsic_class_14`  class_members=['P5_R3', 'P5_R6']  uses_extrinsic=True
`L3_extrinsic_class_15`  class_members=['P5_R4', 'P5_R5']  uses_extrinsic=True
`L3_extrinsic_class_16`  class_members=['P5_R1', 'P5_R8']  uses_extrinsic=True

- `L2` 是否依赖 extrinsic star/plane 信息：`True`。
- `L3` 是否依赖 extrinsic star/plane 信息：`True`。

## double

- `L2` row counts: coarse `3`, intrinsic `5`, extrinsic `8`.
- `L3` row counts: coarse `4`, intrinsic `9`, extrinsic `16`.

### L2

- `intrinsic`:
`L2_intrinsic_class_01`  class_members=['P3_R1', 'P3_R4']  uses_extrinsic=False
`L2_intrinsic_class_02`  class_members=['P3_R2', 'P3_R3']  uses_extrinsic=False
`L2_intrinsic_class_03`  class_members=['P4_R3']  uses_extrinsic=False
`L2_intrinsic_class_04`  class_members=['P4_R1', 'P4_R2']  uses_extrinsic=False
`L2_intrinsic_class_05`  class_members=['P3_R5', 'P3_R6']  uses_extrinsic=False
- `extrinsic`:
`L2_extrinsic_class_01`  class_members=['P3_R1']  uses_extrinsic=True
`L2_extrinsic_class_02`  class_members=['P3_R3']  uses_extrinsic=True
`L2_extrinsic_class_03`  class_members=['P3_R4']  uses_extrinsic=True
`L2_extrinsic_class_04`  class_members=['P3_R2']  uses_extrinsic=True
`L2_extrinsic_class_05`  class_members=['P3_R5']  uses_extrinsic=True
`L2_extrinsic_class_06`  class_members=['P3_R6']  uses_extrinsic=True
`L2_extrinsic_class_07`  class_members=['P4_R3']  uses_extrinsic=True
`L2_extrinsic_class_08`  class_members=['P4_R1', 'P4_R2']  uses_extrinsic=True

### L3

- `intrinsic`:
`L3_intrinsic_class_01`  class_members=['P1_R1', 'P1_R8', 'P5_R1', 'P5_R8']  uses_extrinsic=False
`L3_intrinsic_class_02`  class_members=['P1_R4', 'P1_R5']  uses_extrinsic=False
`L3_intrinsic_class_03`  class_members=['P5_R2', 'P5_R7']  uses_extrinsic=False
`L3_intrinsic_class_04`  class_members=['P1_R9', 'P1_R12']  uses_extrinsic=False
`L3_intrinsic_class_05`  class_members=['P1_R10', 'P1_R11']  uses_extrinsic=False
`L3_intrinsic_class_06`  class_members=['P5_R4', 'P5_R5']  uses_extrinsic=False
`L3_intrinsic_class_07`  class_members=['P1_R3', 'P1_R6']  uses_extrinsic=False
`L3_intrinsic_class_08`  class_members=['P5_R3', 'P5_R6']  uses_extrinsic=False
`L3_intrinsic_class_09`  class_members=['P1_R2', 'P1_R7']  uses_extrinsic=False
- `extrinsic`:
`L3_extrinsic_class_01`  class_members=['P1_R2']  uses_extrinsic=True
`L3_extrinsic_class_02`  class_members=['P1_R3']  uses_extrinsic=True
`L3_extrinsic_class_03`  class_members=['P1_R1']  uses_extrinsic=True
`L3_extrinsic_class_04`  class_members=['P1_R4']  uses_extrinsic=True
`L3_extrinsic_class_05`  class_members=['P1_R6']  uses_extrinsic=True
`L3_extrinsic_class_06`  class_members=['P1_R7']  uses_extrinsic=True
`L3_extrinsic_class_07`  class_members=['P1_R5']  uses_extrinsic=True
`L3_extrinsic_class_08`  class_members=['P1_R8']  uses_extrinsic=True
`L3_extrinsic_class_09`  class_members=['P1_R10']  uses_extrinsic=True
`L3_extrinsic_class_10`  class_members=['P1_R9']  uses_extrinsic=True
`L3_extrinsic_class_11`  class_members=['P1_R11']  uses_extrinsic=True
`L3_extrinsic_class_12`  class_members=['P1_R12']  uses_extrinsic=True
`L3_extrinsic_class_13`  class_members=['P5_R2', 'P5_R7']  uses_extrinsic=True
`L3_extrinsic_class_14`  class_members=['P5_R3', 'P5_R6']  uses_extrinsic=True
`L3_extrinsic_class_15`  class_members=['P5_R4', 'P5_R5']  uses_extrinsic=True
`L3_extrinsic_class_16`  class_members=['P5_R1', 'P5_R8']  uses_extrinsic=True

- `L2` 是否依赖 extrinsic star/plane 信息：`True`。
- `L3` 是否依赖 extrinsic star/plane 信息：`True`。
