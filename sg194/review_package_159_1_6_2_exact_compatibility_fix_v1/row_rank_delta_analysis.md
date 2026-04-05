# Row Rank Delta Analysis

## single
- 修补前 matrix shape: []
- 修补前 rank/nullity: rank=None, nullity=9
- 修补前 exact row 数: 0
- 修补后 matrix shape: []
- 修补后 rank/nullity: rank=None, nullity=6
- 修补后 exact row 数: 12
- 变化: target BS rank 从 9 降到 6

## double
- 修补前 matrix shape: []
- 修补前 rank/nullity: rank=None, nullity=9
- 修补前 exact row 数: 0
- 修补后 matrix shape: []
- 修补后 rank/nullity: rank=None, nullity=6
- 修补后 exact row 数: 11
- 变化: target BS rank 从 9 降到 6

## 语义解释
- 之前全部 ordinary rows 都来自 coarse line basis decomposition，因此 target BS 被 underconstrain。
- 本轮 exact 化只覆盖 family-special lines，因此 rank 已下降，但剩余 coarse ordinary lines 和 monodromy rows 仍限制了进一步收敛。
