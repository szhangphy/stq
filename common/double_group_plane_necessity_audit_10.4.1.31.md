# Double-Group Plane Necessity Audit for 10.4.1.31

## Scope

- group: `10.4.1.31`
- groupType: `2`
- stage: plane necessity audit on top of the full double-group line layer

## Geometry Premise

- explicit special planes from geometry JSON: `['S1', 'S2']`
- `line_plane`: `[]`
- All plane boundaries are geometric-only boundaries rather than separately listed special lines.
- Because of that, a boundary-line chain through explicit line unknowns is not available here. The minimal viable connector is direct restriction from the corner points to the common plane generic basis.

## Signatures

- `S1` matching lines: `[]`
- `S2` matching lines: `[]`
- new plane generic signature type detected: `True`
- Result: the planes do introduce a new generic signature class relative to the explicit lines, so the with-planes backbone is needed both to include the plane sectors and to impose the extra couplings.

## Rank Test

- line-only matrix shape / rank / nullity: `[10, 26]` / `10` / `16`
- with-planes matrix shape / rank / nullity: `[30, 31]` / `23` / `8`
- added rank beyond the line layer: `13`
- net nullity drop: `8`

## Verdict

- planes required: `True`
- `S1/S2` carry a plane generic signature class that is absent from the explicit line layer, and the associated plane unknowns also add independent couplings between corner-point sectors that remain disconnected in the line-only matrix.
