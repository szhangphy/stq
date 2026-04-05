# 文件级审计表

| 文件 | 作用 | group routing | BS 主路径 | 旧群残留 | 本轮修改 | 说明 |
|---|---|---:|---:|---:|---:|---|
| `sg194/README.md` | 顶层说明 | 否 | 否 | 是 | 否 | README 仍偏旧，未提到 `194.1.12.16` 和 `159.1.6.2`。 |
| `sg194/run_group_pipeline.py` | 统一 CLI 入口 | 是 | 间接 | 否 | 否 | 仅转发到 `driver.main`。 |
| `sg194/pipeline_v2/driver.py` | 统一 orchestrator | 是 | 是 | 否 | 否 | 调用链清晰；truth compare 在 final status 之后。 |
| `sg194/pipeline_v2/specs.py` | spec 注册 | 是 | 否 | 是 | 是 | 新增 `ssg194_1_12_16` 和 `ssg159_1_6_2` 正式 spec。 |
| `sg194/pipeline_v2/group_target_registry.py` | target 级策略元数据 | 是 | 间接 | 是 | 是 | 为 `159.1.6.2` 打开 truth compare，声明 compare-only 事实。 |
| `sg194/pipeline_v2/benchmark_oracle_registry.py` | truth/benchmark 读取 | 是 | 否 | 是 | 是 | 降级为 truth/compare registry；新增 compare-only JSON 路径。 |
| `sg194/pipeline_v2/bs_ai.py` | result objects 与 mode 注释 | 否 | 是 | 否 | 是 | 保持 generic records 主路径；显式把 `benchmark_oracle_available=False`。 |
| `sg194/pipeline_v2/truth_compare.py` | compare-only 报告 | 否 | 否 | 否 | 是 | 支持 partial truth，允许只比较 double 的 `dBS/dAI`。 |
| `sg194/pipeline_v2/alignment.py` | alignment 汇总 | 否 | 是 | 否 | 否 | 当前 `159.1.6.2` 在这里接住 generic builder 的 `KeyError` fallback。 |
| `sg194/pipeline_v2/quotient.py` | quotient 摘要输出 | 否 | 是 | 否 | 否 | 本轮未改。 |
| `sg194/pipeline_v2/reporting.py` | JSON/MD 输出与打包 | 否 | 否 | 否 | 是 | truth compare markdown 现在会暴露 external label/scope/note。 |
| `sg194/pipeline_v2/generic_builders.py` | generic solve 主入口 | 否 | 是 | 是 | 否 | 本轮未改数学逻辑；当前 `159.1.6.2` blocker 位于 `_build_same_shell_target_row_language`。 |
| `sg194/pipeline_v2/runtime_backend_free.py` | backend-free 兼容矩阵构造 | 否 | 是 | 否 | 否 | `build_global_compatibility` 在 `unknown_index['B1_R1']` 处报错。 |
| `sg194/pipeline_v2/geometry.py` | geometry summary 封装 | 否 | 间接 | 否 | 否 | `159.1.6.2` geometry 已完成。 |
| `sg194/pipeline_v2/models.py` | 数据模型 | 否 | 否 | 否 | 否 | 本轮未改。 |
| `sg194/pipeline_v2/adapters/__init__.py` | adapter routing | 是 | 间接 | 否 | 否 | 通过 spec 的 `adapter_key` 获取 adapter。 |
| `sg194/pipeline_v2/adapters/generic_diagnostic.py` | generic final status/extra checks | 否 | 间接 | 否 | 是 | 不再把 truth compare 误标成 benchmark oracle。 |
| `sg194/pipeline_v2/adapters/sg194.py` | 旧 SG194 adapter | 是 | 是 | 是 | 否 | 本轮未用作 `159.1.6.2` 或 `194.1.12.16` 的 active adapter。 |
| `sg194/compare_only_rank_reference_159_1_6_2.json` | compare-only 外部事实 | 否 | 否 | 否 | 是 | 只存 `P31c (No. 159.61)` 的 `dBS=8, dAI=8`。 |
| `sg194/current_status*.json` | 历史状态文件 | 否 | 否 | 是 | 否 | 存在大量旧残留；本轮未把它们带入新 package。 |
| `sg194/handoff*.md` | 历史 handoff | 否 | 否 | 是 | 否 | 本轮只做 grep 审计，不接入主路径。 |
| `sg194/review_package_*` | 历史审阅包 | 否 | 否 | 是 | 否 | 仅用于残留审计；本轮 package 独立新建。 |
