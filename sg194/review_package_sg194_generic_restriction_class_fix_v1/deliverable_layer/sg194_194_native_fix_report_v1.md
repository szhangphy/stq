# 194 Native Fix Report v1

这一步之前一直卡住，不是因为 quotient 后处理不够，而是因为 native compatibility builder 还没有真的 general：
- 主路径仍然先走 old coarse decomposition line builder，restriction classes 只在 fallback 才启用。
- endpoint star 是按 orbit-level point_id 聚合的，把同一 orbit 上不同坐标实例混在了一起，直接伪造 continuation。
- geometry/connectivity 只显式认 plane boundary，没有把 plane 内部的 special lines 记成真实 incidence。

这次真正改动的是 native compatibility builder 本身：
- 所有 line 默认都走 restriction-class primary builder，不再把 old coarse builder 当 success path。
- restriction fingerprint 统一到 linear_character，并补上 instance-level point-star continuation。
- endpoint star 现在按 capture_id/坐标实例建，不再把 P5/P6 这类 orbit label 的不同实例混成一个点。
- plane 内部 special lines 现在显式登记；当前 194 审计里能看到 `L4 in S2`、`L7 in S4` 的 interior incidence。

结果是：single BS nullity `16 -> 13`，double BS nullity `16 -> 13`。这说明核心 bug 已经在 C 矩阵层被碰到了，而不是靠后处理把 16 压成 13。
- 新 rows 一共把 old kernel 杀掉 3 个方向；kernel localization 审计显示其中 1 个方向纯支撑在 `P3/P4`，另外 2 个方向混合支撑在 `P1/P5` 与 plane blocks 上，对应的正是新加的 `L2` 和 `L3` restriction-class relations。

但 194 现在还没有变成 accepted final result。原因已经从 BS 层转移到了 AI 层：
- single 现在是 `13/7/Z^6`，rejected AI candidates=`24`。
- double 现在是 `13/7/Z^6`，rejected AI candidates=`24`。
- 这些 rejection 主要集中在 `L2_restriction_class_P4_01` 和 `L3_restriction_class_P5_01..04`。

所以这一步的诚实结论是：BS 侧已经修对到 13；如果后面还要追 accepted final result，下一步该处理的是 AI seeds 与修后 compatibility 的一致性，而不是再回头补 projection/spec/adapter。
