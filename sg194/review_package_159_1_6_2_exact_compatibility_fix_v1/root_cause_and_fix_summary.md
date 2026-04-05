# Root Cause And Fix Summary

## Root cause
`159.1.6.2` 的 target row language 已经恢复出正确 strata，但 compatibility rows 仍大面积来自 coarse endpoint decomposition。coarse rows 不包含 representation-level endpoint support、restriction classes、intrinsic fingerprints，因此 BS 约束不足，表现为 `dBS=9` 虚高，而 AI 侧已经降到了更低 rank。

## Fix applied in this round
- 不改全局 authoritative backend 映射，避免破坏 `194.1.12.16`。
- 只对 `recovered_family_special_line` ordinary lines 走 exact restriction-class builder。
- 给 monodromy rows 补充 exact metadata，并允许 exact one-sided rows 通过结构 sanity check。

## Outcome
- `159.1.6.2` single target BS rank: 6
- `159.1.6.2` double target BS rank: 6
- `159.1.6.2` single dAI: 0
- `159.1.6.2` double dAI: 0
- quotient status: still semantic_fail

## Remaining blocker
当前 remaining blocker 不是 geometry/strata，而是 exact compatibility builder 仍只覆盖 3 条 recovered family-special lines；其余 ordinary coarse lines 和 monodromy exact rows 还没有完整接上。
