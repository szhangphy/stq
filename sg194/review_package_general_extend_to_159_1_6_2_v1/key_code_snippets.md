# 关键代码片段

## 1. `194.1.12.16` 控制组 spec 注册

文件：`sg194/pipeline_v2/specs.py:50-90`

```python
GROUP194_1_12_16_SPEC = GroupSpec(
    key="ssg194_1_12_16",
    group_id="194.1.12.16",
    adapter_key="generic_diagnostic",
    builder_backend="generic_symmetry_ops",
    trust_level="generic_symmetry_ops_reference_control_for_bs_rank",
)
```

简注：控制组进入统一 spec 表，而不是借壳旧错群。

## 2. `159.1.6.2` 新目标 spec 注册

文件：`sg194/pipeline_v2/specs.py:93-134`

```python
GROUP159_1_6_2_SPEC = GroupSpec(
    key="ssg159_1_6_2",
    group_id="159.1.6.2",
    adapter_key="generic_diagnostic",
    builder_backend="generic_symmetry_ops",
    trust_level="generic_symmetry_ops_extension_target_with_compare_only_rank_reference",
)
```

简注：`159.1.6.2` 现在是正式可调用对象。

## 3. target registry 中声明 compare-only 能力

文件：`sg194/pipeline_v2/group_target_registry.py:31-44`

```python
"159.1.6.2": GroupTargetSpec(
    group_id="159.1.6.2",
    truth_compare_available=True,
    generic_builders_expected=True,
    require_same_shell_target_builder_for_generic_final=True,
)
```

简注：这里只打开 truth compare 能力，不写 solver 结果。

## 4. compare-only reference hook

文件：`sg194/pipeline_v2/benchmark_oracle_registry.py:29-36`

```python
"159.1.6.2": BenchmarkOracleSpec(
    target_group="159.1.6.2",
    benchmark_status_file=None,
    benchmark_verdict_file=None,
    truth_reference_file="sg194/compare_only_rank_reference_159_1_6_2.json",
    source_kind="external_compare_only_rank_reference",
    external_object_label="P31c (No. 159.61)",
),
```

简注：接入 compare-only 参考，但不接 benchmark solver payload。

## 5. compare-only JSON 本体

文件：`sg194/compare_only_rank_reference_159_1_6_2.json:1-13`

```json
{
  "target_group": "159.1.6.2",
  "external_object_label": "P31c (No. 159.61)",
  "reference_scope": "double_only_rank_reference",
  "double_truth": { "dBS": 8, "dAI": 8, "classification": null }
}
```

简注：这里只有外部核对事实，不是 active solver input。

## 6. partial truth compare 允许只比较已知字段

文件：`sg194/pipeline_v2/truth_compare.py:17-50`

```python
field_matches = {
    field: (
        None
        if truth.get(field) is None
        else record.get(field) == truth.get(field)
    )
    for field in comparable_fields
}
```

简注：`classification` 未知时不会被强行判错。

## 7. 统一 orchestrator 中 compare 在 final 之后

文件：`sg194/pipeline_v2/driver.py:24-63`

```python
records = build_result_objects(spec, adapter, artifacts, geometry, alignment)
final_status = adapter.build_final_status(spec, artifacts, records)
truth_compare = build_truth_compare_report(repo_root, spec.group_id, records)
```

简注：compare-only 是下游消费者，不是 solver 上游输入。

## 8. generic result object 仍由 generic builders 产生

文件：`sg194/pipeline_v2/bs_ai.py:177-196`

```python
if _is_generic_spec(spec):
    records = generic_result_objects(spec.group_id)
    return _annotate_result_mode(records, spec)
```

简注：`159.1.6.2` 不走 adapter 注入结果，而走 generic builders 主路径。

## 9. generic path 的 target row language 真实组装点

文件：`sg194/pipeline_v2/generic_builders.py:1438-1448`

```python
target_line_blocks = ordinary_line_blocks + monodromy_line_blocks
target_compatibility = port.build_global_compatibility(target_line_blocks, target_point_ids)
target_bs_analysis = port.analyze_kernel(target_compatibility)
```

简注：`159.1.6.2` 当前就在这里卡住。

## 10. `B1_R1` 报错真正发生点

文件：`sg194/pipeline_v2/runtime_backend_free.py:2068-2078`

```python
ordering = []
for point_id in point_ids:
    ordering.extend(per_point_ids.get(point_id, []))
unknown_index = {unknown: index for index, unknown in enumerate(ordering)}
...
row[unknown_index[term["unknown"]]] += int(term["coeff"])
```

简注：当 line block 引入 synthetic boundary rep label 而 ordering 没有该列时，就会直接 `KeyError`。

## 11. result mode 注释层已切断 benchmark 污染

文件：`sg194/pipeline_v2/bs_ai.py:162-174`

```python
item["truth_compare_available"] = target_spec.truth_compare_available
item["benchmark_oracle_available"] = False
item["final_result_mode"] = mode
```

简注：即使 `159.1.6.2` 有 compare-only reference，也不会被标成 benchmark-backed。

## 12. truth compare markdown 现在暴露 external label

文件：`sg194/pipeline_v2/reporting.py:178-194`

```python
f"external object label: `{truth_compare.get('external_object_label')}`",
f"reference scope: `{truth_compare.get('reference_scope')}`",
f"note: `{truth_compare.get('note')}`",
```

简注：外部参考对象已经在输出层可见，便于后续人工审阅。
