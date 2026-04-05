# Compare-Only Rank Reference: 159.1.6.2

- target group: `159.1.6.2`
- external object label: `P31c (No. 159.61)`
- reference scope: `double_only_rank_reference`
- compare-only `dBS`: `8`
- compare-only `dAI`: `8`

## 语义边界

这两个 rank 事实来自外部 compare-only 参考层，仅用于：

- truth compare summary
- review package
- 后续人工核对

它们不允许进入：

- generic geometry builder
- generic alignment builder
- compatibility builder
- quotient builder
- final result promotion

## 当前实现证据

- compare-only 数据文件：`sg194/compare_only_rank_reference_159_1_6_2.json`
- 读取路径：`truth_compare.build_truth_compare_report -> benchmark_oracle_registry.load_group_truth_reference`
- `driver.run_pipeline` 中 compare 发生在 `final_status` 之后
- `bs_ai._annotate_result_mode` 对 generic spec 强制 `benchmark_oracle_available=False`
