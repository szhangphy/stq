# 159 vs 194 target point recovery diff

## 159.1.6.2
- grouped points: 8
- target_point_ids: ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8']
- target_capture_ids: ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8']
- synthetic boundary points: []
- target row language availability: available
- target_bs_rank(single/double): 9 / 9

## 194.1.12.16
- grouped points: 6
- target_point_ids: ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
- target_capture_ids count: 11
- synthetic boundary points: []
- target row language availability: available
- target_bs_rank(single/double): 13 / 10

## 代码级差异
- 194 原本就有显式 0D grouped points，所以 target_point_ids 直接来自 grouped points
- 159 原本没有显式 0D grouped points，导致 target_point_ids 和 catalog 都空
- 本轮修补后，159 的 grouped points 在 geometry 层被 boundary-derived real points 补回；194 因已有显式 points，修补对其是 no-op
