# Control Group Regression Check

控制组固定为 `194.1.12.16`。

## target BS rank
- single: 13
- double: 10

## final status
- overall status: not_final
- single final_result_mode: diagnostic_only
- double final_result_mode: diagnostic_only

## row builder audit
- single exact row 数: 3
- double exact row 数: 3
- single builder variants: ['coarse']
- double builder variants: ['coarse']

结论：这轮最小修补没有改变控制组 dBS(single/double)=13/10，因此控制组未被带坏。
