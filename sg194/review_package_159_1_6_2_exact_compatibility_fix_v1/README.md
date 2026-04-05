# 159.1.6.2 exact compatibility fix v1

本轮只处理 `159.1.6.2` 的 BS exact compatibility，不改 quotient guard，不把 compare-only truth 注入求解器。

## 核心结论
- 之前 `159.1.6.2` 的 target row language 仍主要由 coarse rows 组成，导致 BS underconstrained 并给出虚高的 `dBS=9`。
- 本轮只在 `sg194/pipeline_v2/generic_builders.py` 增加 exact / representation-aware ordinary line builder plumbing，并保住 `194.1.12.16` 控制组的 `dBS(single/double)=13/10`。
- 修补后 `159.1.6.2` 的 target BS rank 从 `9` 降到 `6`；`dAI` 目前落到 `0`，quotient 仍 `semantic_fail`，所以状态仍是 `not_final`。

## 当前 159.1.6.2 结果
- single: `target_bs_rank=6`, `dAI=0`
- double: `target_bs_rank=6`, `dAI=0`
- exact rows: single `12` / double `11`

## 控制组
- `194.1.12.16` single `target_bs_rank=13`
- `194.1.12.16` double `target_bs_rank=10`
- 本轮未改 runtime backend 的全局 authoritative/coarse 分派，因此控制组未回退。
