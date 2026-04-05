# Root Cause

- `B1_R1` 首次不是在 global assembly 随机生成，而是在 `generic_builders._build_target_restriction_line_block(...)` 中，由 endpoint `B1` 的 rep decomposition 生成。
- 对 `159.1.6.2`，geometry 没有 real grouped points，只有 3 条 line、1 个 plane 和 8 个 synthetic boundary points。
- pre-fix 时 `shared_geometry_bundle(...).target_point_ids = real_point_ids`，因此 `target_point_ids=[]`。
- 但 target ordinary line blocks 的 endpoint ids 实际是 `B1..B6`，于是 global assembly 收到的 block terms 包含 `B1_R1..B6_R3`。
- `build_global_compatibility(...)` 的 contract 是：传入的 `point_ids` 必须覆盖所有 block endpoint ids。pre-fix caller 违反了这个 contract。
- 因而 `B1_R1` 的语义判定不是命名 bug，也不是临时消元变量；它是 synthetic boundary point 诱导出来、且在该 target row-language 中应进入全局列宇宙的合法 unknown sector。

# Chosen Fix Direction

选择方向 B：扩展 target ordering，使其包含 target line blocks 实际引用到的合法 boundary sector。

具体落点在 `generic_builders._build_same_shell_target_row_language(...)`：不再直接把 `shared['target_point_ids']` 传给 `build_global_compatibility(...)`，而是先用 `_target_global_point_ids_from_line_blocks(...)` 根据 target line blocks 的 endpoint ids 生成真实 global point universe。
