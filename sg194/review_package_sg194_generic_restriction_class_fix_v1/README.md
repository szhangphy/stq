# SG194 Generic Restriction-Class Fix v1

1. 这轮唯一目标是把 194.1.1.1 backend-free generic path 的 native compatibility builder 修成真正的 restriction-class primary builder，并先把 BS nullity 从 16 修回 13。
2. BS nullity 16 -> 13: single=`16->13`，double=`16->13`。
3. native 194 single 现在是 `13/7/Z^6`，availability=`provisional`。
4. native 194 double 现在是 `13/7/Z^6`，availability=`provisional`。
5. 当前 blocker 不是 BS，而是 AI：修后的 native compatibility 会拒掉一批旧的 AI candidates，主要落在 `L2` 和 `L3` 的新 restriction-class rows。
6. 建议先看：`audit_layer/sg194_generic_line_builder_compare_v1.json`、`audit_layer/sg194_line_restriction_class_audit_v1.json`、`audit_layer/sg194_194_native_kernel_localization_after_fix_v1.json`、`audit_layer/sg194_194_native_fix_report_v1.md`。
