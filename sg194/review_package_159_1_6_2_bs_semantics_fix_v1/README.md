# 159.1.6.2 BS semantics fix v1

本轮目标只有一个：修补 `159.1.6.2` 中把 assembly boundary helper universe 误当成 published target BS universe 的语义错误。

- compare-only facts 仍然是：`dBS=8`, `dAI=8`, `classification=trivial`
- compare-only facts 只用于核对，不进入 solver 主路径
- 本轮不硬填最终答案
- 本轮额外验证 `194.1.12.16` 的 single/double `dBS` 不回退
