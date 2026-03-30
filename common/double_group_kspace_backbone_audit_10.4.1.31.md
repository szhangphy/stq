# Double-Group K-Space Backbone Audit for 10.4.1.31

## Scope

- group: `10.4.1.31`
- groupType: `2`
- This stage does not revisit the closed single-group line or the already accepted minimal double-group prototype.
- The goal here is the full double-group k-space backbone: four explicit line blocks, plane necessity, final C_double, BS_double, and the formal embedding of the existing family-c prototype into that BS lattice.

## Reused Premise

- single-group is already closed, including with-planes BS and BS/AI.
- the minimal double-group prototype already established that the k-space extraction, bridge, and induction all work at least on c -> P1/L1/P4.
- previous double-group feasibility verdict: `True`

## Geometry Audit

- All manifolds are read from the existing geometry JSON rather than handwritten.
- points: `['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8']`
- lines: `['L1', 'L2', 'L3', 'L4']`
- planes: `['S1', 'S2']`
- Sample points and parametrizations are taken directly from `single_group_kmanifolds.json`.

## Double-Group Output Capability

- all manifolds stable under a repeated groupType=2 extraction: `True`
- `character`, `linear_character`, and `rep_degree` are available on every point, line, and plane used in this run.
- The array structure is consistent: rows are coreps, columns are unitary subgroup operations, and the row ordering stays stable under repeated extraction.

## Character Choice

- selected compatibility mode: `character`
- raw character all-block success: `True`
- linear_character all-block success: `False`
- Reason: compatibility must be an exact integer subgroup restriction problem. raw character satisfies that uniformly on all four lines, while linear_character fails on L1/L3 because it keeps the generic-k Bloch phase.
- Consequence: raw character is used for compatibility rows and plane comparison; linear_character is still used later for induced band-character decomposition.

## Reuse vs Rewrite

- Reused from the single-group scripts:
  - geometry / connectivity parsing from the existing JSON files,
  - operation-subgroup matching,
  - integer restriction/decomposition tables,
  - Smith normal form and integer kernel extraction,
  - the geometric conclusion that `line_plane = []` means the boundary-line chain is unavailable.
- Rewritten or made explicitly double-aware:
  - the subgroup-matching key now carries the little-group SU2 matrix in addition to the spatial data,
  - the line/plane restriction solver is run on double-valued raw characters,
  - the character-vs-linear_character choice is audited explicitly instead of inherited,
  - the minimal family-c prototype is extended from the old P1/L1/P4 witness to the final BS_double unknown ordering.

## Line Layer

- line-layer completed: `True`
- line-only matrix shape / rank / nullity: `[10, 26]` / `10` / `16`
- line-only Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`

## Plane Necessity

- planes required: `True`
- S1 matches: `[]`
- S2 matches: `[]`
- added rank beyond line-only: `13`
- Interpretation: the planes do not create a new generic signature class, but they still add independent constraints by coupling point sectors that are otherwise disconnected across the four line blocks.

## Final BS_double

- final matrix source: `with_planes`
- final shape / rank / nullity: `[30, 31]` / `23` / `8`
- Smith diagonal: `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2]`
- BS_double constructed: `True`

## Minimal Real-Space Double Embedding

- reused minimal prototype: family `c`, projective local irrep `c_double_g_plus_i`
- embedded in final BS_double: `True`
- coordinates in raw BS basis: `[-1, 2, 2, 0, 2, 0, 2, 2]`
- coordinates in pretty BS basis: `[1, -2, -2, 0, -2, 0, 2, 2]`

## Verdict

- Conclusion type: `1` (full double-group k-space backbone succeeded).
- Full line-layer compatibility succeeded.
- Plane necessity was re-audited in the double group and the planes remain necessary.
- The with-planes double compatibility matrix was built successfully.
- BS_double was constructed exactly over Z.
- The existing minimal family-c prototype now sits as an explicit vector inside the final BS_double lattice.
