# Key Diffs

- `runtime_backend_free.py`: line builder 显式拆成 `coarse / intrinsic / extrinsic`。
- `generic_builders.py`: generic path 支持 `builder_variant`，结果语义区分 `surviving_ai_rank` 与 `final_dAI`。
- 本轮新增 compare/provenance/result/consistency artifacts，并用统一脚本重建 package。
