# 159.1.6.2 BS family-complete exact v1

本轮只处理 BS exact compatibility family semantics。

## 本轮主结论
- 上一轮的问题是 exact dispatch 依赖 recovered provenance，而不是 Bilbao/published target line family semantics。
- 这轮把 ordinary line family 的 exact/coarse 选择改成 semantic-based dispatch。
- 对 159，`DT/P/PC/Λ/Q/U` 六个 ordinary target families 现在都变成 exact intrinsic rows。
- 对 194.1.12.16，控制组保持不坏：single=13，double=10。
- 当前 remaining blocker 不再是 mixed exact+coarse family；而是 monodromy exact blocks 仍然没有产出 actual equations。
