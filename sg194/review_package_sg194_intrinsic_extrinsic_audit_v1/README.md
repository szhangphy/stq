# SG194 Intrinsic / Extrinsic Audit

1. 这轮唯一目标：把 194 的 line compatibility builder 拆成 `coarse / intrinsic / extrinsic` 三套，并证明 `13` 到底来自哪一套。
2. `13` 是否由 intrinsic 得到：single/double = `7` / `7`。
3. `13` 是否由 extrinsic 得到：single/double = `1` / `1`。
4. L2 新增：intrinsic/extrinsic row counts = `5` / `8`。
5. L3 新增：intrinsic/extrinsic row counts = `9` / `16`。
6. final dAI 仍 unavailable 吗：single `None`, double `None`。
7. 先看哪 10 个文件：compare、L2/L3 focus、row provenance、AI rejection provenance、single/double v3 result、consistency、runtime_backend_free.py、generic_builders.py。
