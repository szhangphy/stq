# Native Generic vs Legacy Special vs Benchmark Compare

- native generic: 只使用 symmetry operations、swyckoff conversion、generic builders、generic compatibility/AI/quotient；这轮 fix 就发生在这一层。
- legacy special: 194 的 accepted special result 只保留作 regression reference，不参与 native compatibility 或 native final result 计算。
- benchmark compare: benchmark/internalization/projection/oracle 在这轮都没有被用来构造 native result；它们只保留为外部比较层。
