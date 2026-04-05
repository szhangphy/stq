# Published target universe decision

结论：本轮采用“assembly universe 与 published target universe 分离”的修补。

- `assembly_global_point_ids` 可以包含 `B1..B6`，因为 line-block 装配确实引用了这些 synthetic boundary endpoints。
- 但 `published target universe` 必须由真实 published target points / captures 支撑。
- 对 `159.1.6.2`，当前 `target_point_ids_current=[]` 且 `target_capture_ids=[]`，说明 published target universe 还未解析出来。
- 因此本轮选择：assembly compatibility 继续可用，但 published target row language 不再 `available`，并把 `target_bs_rank` 置空，阻塞点写成 `generic_published_target_universe_unresolved`。
- 这保证了 `B1..B6` 不再被直接当成 published target dBS 的列宇宙。
