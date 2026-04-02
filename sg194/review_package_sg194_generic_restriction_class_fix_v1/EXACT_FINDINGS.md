# Exact Findings

- single 和 double 的 native BS nullity 都从 `16` 变成了 `13`。
- primary line builder 不再走 old coarse success path；restriction classes 现在是默认主路径。
- 几何/连通性修正点不是 family/spec，而是 point-instance 语义：不能把同一 orbit point_id 的不同坐标实例混成一个 endpoint star。
- 需要识别 plane 内部 special lines；当前已显式记录 `L4 in S2` 和 `L7 in S4` 的 interior incidence。
- 修后的 AI 仍有 blocker：single rejected=`24`，double rejected=`24`。
