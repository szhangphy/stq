# Coarse Row Origin Audit

## 当前 coarse row 的来源函数链
1. `generic_builders._build_target_line_blocks_for_window(...)`
2. `generic_builders._build_generic_line_block(...)`
3. `runtime_backend_free.build_line_block(...)`
4. `runtime_backend_free.build_line_block_coarse(...)`

`runtime_backend_free.build_line_block_coarse(...)` 明确写入：
- `builder_variant = "coarse"`
- `row_kind = "line_basis_decomposition"`
- `uses_extrinsic_data = false`
- `endpoint_support = {}`
- `class_members = []`
- `intrinsic_fingerprint_by_rep = {}`
- `extrinsic_fingerprint_by_rep = {}`

## 本轮 exact 化的接入点
本轮没有改 `runtime_backend_free.py` 的全局 authoritative 分派，而是在
`generic_builders._build_target_restriction_line_block(...)` 中，对 `source_letter == "recovered_family_special_line"` 的 ordinary line 单独走
`stage1_backend().build_line_block_from_intrinsic_restriction_classes(..., field="character")`。

这样做的原因是：
- 直接把所有 authoritative lines 切到 exact builder 会破坏 `194.1.12.16` 控制组。
- 目前最小安全修补是只对 159 新恢复出来的 family-special lines 提升到 exact restriction rows。

## 本轮后仍然 coarse 的部分
- 非 `recovered_family_special_line` 的 ordinary lines 仍然走 coarse builder。
- monodromy lines 本轮只补了 exact metadata，没有替换成新的 global exact row family。
- 因此 `builder_variant="coarse"` 仍然存在，159 的 BS rank 从 9 降到 6，但没有直接到 final。
