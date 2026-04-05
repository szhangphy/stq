# Review Package: general extend to 159.1.6.2 v1

## 本轮目标

- 保持 `194.1.12.16` 作为当前 generic BS-rank 参考控制组，不回退统一入口。
- 把 `159.1.6.2` 正式接进 unified pipeline。
- 为 `159.1.6.2` 接入 compare-only 外部 rank 参考，但不污染 active solve path。

## 当前对象

- 已通过参考控制组：`194.1.12.16`
- 新扩展对象：`159.1.6.2`
- 外部 compare-only 参考对象：`P31c (No. 159.61)`

## Compare-Only Rank Facts

- `dBS = 8`
- `dAI = 8`

这些数字只存在于 compare/truth/report 层，不是 solver 主路径输入。

## 当前最深 blocker

`159.1.6.2` 已经完成 spec 注册、truth-compare hook、统一入口运行、geometry 输出和 current-row-shell 输出，但在 target compatibility 组装阶段卡住：

- 函数：`sg194.pipeline_v2.generic_builders._build_same_shell_target_row_language`
- 下游调用：`sg194.pipeline_v2.runtime_backend_free.build_global_compatibility`
- 直接错误：`KeyError: 'B1_R1'`

这说明 target line blocks 中出现了 synthetic boundary rep label，但 target compatibility 的 `point_ids` / unknown universe 只覆盖 real target points，列宇宙不一致。

## 本包包含

- patch 后源码
- unified diff
- 命令与原始输出
- 调用链图
- 文件审计表
- 阶段状态矩阵
- compare-only reference note
- control/target 关键 JSON 快照
- 本轮结论摘要
