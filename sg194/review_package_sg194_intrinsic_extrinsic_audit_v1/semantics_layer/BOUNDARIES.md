# Semantics

- `coarse`: 旧 `decomposition_on_line_basis` 基线。
- `intrinsic`: 只使用当前 line 的 intrinsic restriction classes，是本轮推荐的 native interpretation。
- `extrinsic`: 把 point-star / plane-incidence 混进 class key，只作 compare，不作推荐 native final builder。
- `legacy special`: 仅作 reference，不参与这轮 builder provenance 结论。
