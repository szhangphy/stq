# SG194 Double Final External Reduction

- Raw quotient: `Z^16`
- Full external spinorial quotient: `blocked`
- External spinorial matrix shape: `56 x 33`
- Problem-sector current rank: `6`
- Problem-sector external rank: `6`
- Problem-sector union rank: `8`
- Problem-sector intersection rank: `4`

What the full external matrix resolved:
- The blocker is no longer “spinorial matrix missing”; the full external 56x33 matrix is now cached locally.
- The residual problem is intrinsic to the current 2b/2c/2d/6h sector, not just to heuristic count alignment.

Current-only problem-sector basis:
- `[{'label': '2b:E3', 'coeff': 1}, {'label': '2c:E3', 'coeff': 1}, {'label': '2d:E3', 'coeff': 1}, {'label': '6h:E', 'coeff': 2}]`
- `[{'label': '2c:E1', 'coeff': -2}, {'label': '2c:E3', 'coeff': 1}, {'label': '2d:E1', 'coeff': -2}, {'label': '2d:E3', 'coeff': 1}]`

External-only problem-sector basis:
- `[{'label': '2b:E3', 'coeff': 1}, {'label': '2c:E3', 'coeff': 1}, {'label': '2d:E3', 'coeff': 1}, {'label': '6h:E', 'coeff': 1}]`
- `[{'label': '2c:E1', 'coeff': 1}, {'label': '2c:E3', 'coeff': -1}, {'label': '2d:E2', 'coeff': 1}, {'label': '2d:E3', 'coeff': -1}]`

Final attribution of the old row-content blockers:
- `delta_c1_minus_b1`: still current-only excess direction; not absorbed by the external spinorial problem-sector row space
- `delta_d1_minus_b1`: still current-only excess direction; not absorbed by the external spinorial problem-sector row space

Consequence:
- Even with the full external spinorial matrix cached, the double line is not yet in Bilbao's physically irreducible standard language.
- No final double standard-space quotient should be quoted from the current internal data.
