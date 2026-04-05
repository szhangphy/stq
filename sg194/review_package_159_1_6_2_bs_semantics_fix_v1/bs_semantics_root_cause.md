# BS semantics root cause

之前的 `dBS=9` 在语义上是错的，因为它来自 boundary-augmented assembly kernel，而不是 published target object。

错误链：
1. `_build_target_restriction_line_block(...)` 合法地产生了 `B1_R1..B6_R3` 这类 boundary helper unknown。
2. `_target_global_point_ids_from_line_blocks(...)` 为了让全局装配不报 KeyError，收集了这些 endpoint ids。
3. `_build_same_shell_target_row_language(...)` 直接在这套 assembly universe 上调用 `build_global_compatibility(...)` 和 `analyze_kernel(...)`。
4. 得到的 `target_bs_rank=9` 实际上只是 assembly-stage kernel rank，却被当成了 published target BS。

本轮修补后的定义：
- assembly kernel 仍然会计算，但只记录为 `assembly_bs_rank`
- 只有当真实 published target points/captures 已解析时，才允许把 kernel 提升成 `target_bs_rank`
- 若 published target universe 未解析，则 row language 诚实 blocked
