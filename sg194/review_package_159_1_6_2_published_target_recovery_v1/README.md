# 159.1.6.2 published target universe recovery v1

本轮只做一件事：恢复 159.1.6.2 的真实 published target points/captures。

固定前提：
- 不修改 quotient / AI / classification 逻辑
- compare-only facts 仍然只是外部核对：double dBS=8, dAI=8, classification=trivial
- 控制组是 194.1.12.16，本轮要求其 single/double dBS 保持 13/10

本轮结论：
- 159.1.6.2 的 real target points 丢失在 geometry/grouped 层：pick_group_entries() 没有 materialize 出任何 0D points
- 修补方式是在 prepare_kgeometry() 里，从 real special line endpoints 和 special plane corners 通用恢复 missing 0D points
- 修补后 target_point_ids_current 和 target_capture_ids 都不再为空，published_target_universe_resolved=true
- 这轮没有把 compare-only truth 喂回 solver
