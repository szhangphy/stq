# published target recovery root cause

## 根因
159.1.6.2 在 pick_group_entries() 输出里只有 1D/2D/3D manifolds，没有 0D points。
因此 prepare_kgeometry() 之后：
- grouped points = []
- shared_geometry_bundle().target_point_ids = []
- _build_target_capture_catalog() 只能得到空 catalog
- published_target_universe_resolved = false

## 为什么 194 不会出这个问题
194.1.12.16 的 pick_group_entries() 本来就能给出 6 个显式 points，所以 target universe 从 geometry 层开始就是完整的。

## 本轮修补
在 prepare_kgeometry() 里新增 _recover_boundary_special_points()：
- 从所有 special line endpoints 收集 0D boundary coordinates
- 从所有 special plane corners 收集 0D boundary coordinates
- 对未被显式 point 覆盖的坐标，materialize 成真实 P* grouped points
- 然后再继续走 infer connectivity / point instance / capture catalog 这条原有路径

## 为什么这不是把 B1..B6 升级成 published target
修补后 159.1.6.2 的 shared synthetic_points 为空。
也就是说这些坐标不再通过 boundary helper B* 存在，而是在 geometry 层先被恢复成真实 grouped points (P1..P8)；published target universe 读取的是这些 real points/captures，而不是 synthetic helper ids。
