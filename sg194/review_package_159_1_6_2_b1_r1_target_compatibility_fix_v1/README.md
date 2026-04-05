# 159.1.6.2 B1_R1 Target Compatibility Fix v1

本轮只处理 `159.1.6.2` 在 unified pipeline 里的 `B1_R1` / target compatibility 列宇宙不一致。

compare-only facts 仍然是：`dBS=8`, `dAI=8`, `classification=trivial`。这些 facts 只用于 compare，不进入 solver 主路径。

本轮没有硬填最终答案。修补目标仅是让 target row-language / compatibility 从 `KeyError: B1_R1` 继续下沉到更深层 blocker。
