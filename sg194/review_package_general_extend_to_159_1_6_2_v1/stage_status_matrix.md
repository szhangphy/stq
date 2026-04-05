# 阶段状态矩阵

## 枚举

- `not_present`
- `present_but_wrong_object`
- `implemented_but_unverified`
- `compare_only`
- `blocked`
- `available`

## 194.1.12.16（参考控制组）

| 阶段 | 状态 | 证据 |
|---|---|---|
| geometry | `available` | `geometry_summary.status = built_from_trusted_symmetry_ops` |
| alignment | `available` | `representation_alignment_summary.current_row_shell.status = available` |
| current_row_shell | `available` | current row shell builder 可用 |
| target_row_language | `available` | `target_row_language_availability = available` |
| compatibility | `available` | `compatibility_builder.status = available` |
| quotient | `implemented_but_unverified` | target quotient 已给出 `dBS/dAI/classification`，但 semantic guard 失败 |
| bs_summary | `available` | `bs_results.json` 已输出 target `dBS` |
| ai_summary | `available` | `dAI` 已输出，但与 `dBS` 不一致 |
| final_status | `blocked` | `diagnostic_only / not_final` |
| truth_compare | `not_present` | `truth_compare_available = false` |

## 159.1.6.2（本轮新扩展目标）

| 阶段 | 状态 | 证据 |
|---|---|---|
| geometry | `available` | `geometry_summary.status = built_from_trusted_symmetry_ops` |
| alignment | `blocked` | `blocked_generic_alignment_summary_exception` |
| current_row_shell | `available` | fallback alignment 中 current shell 仍可用 |
| target_row_language | `blocked` | `_build_same_shell_target_row_language` 在 `build_global_compatibility` 报 `KeyError: 'B1_R1'` |
| compatibility | `blocked` | `compatibility_builder.status = blocked` |
| quotient | `blocked` | target quotient 未进入可计算阶段 |
| bs_summary | `blocked` | target `dBS = null` |
| ai_summary | `blocked` | target `dAI = null` |
| final_status | `blocked` | `diagnostic_only / not_final` |
| truth_compare | `compare_only` | external label=`P31c (No. 159.61)`, only double `dBS/dAI` available |

## 当前最深 blocker

`159.1.6.2` 当前最深 blocker 不是 quotient 公式，也不是 final promotion，而是 target compatibility 的列宇宙不一致：

- line-block terms 引入 `B1_R1`
- target point ordering 只覆盖 real `target_point_ids`
- `runtime_backend_free.build_global_compatibility` 在 `unknown_index['B1_R1']` 处抛出 `KeyError`
