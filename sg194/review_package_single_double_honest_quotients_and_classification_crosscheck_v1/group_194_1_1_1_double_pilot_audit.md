# 194.1.1.1 Double-Group Portability Pilot

## Outcome

- All special points, lines, and planes of 194.1.1.1 were captured successfully under `groupType=2`.
- The same synthetic-boundary augmentation used by the single-group pilot also closes the double-group spatial connectivity layer.
- The raw double-group with-planes 42-shell is retained as a diagnostic object, while the published double BS object uses the publication-level `C_pub` quotient.
- Row-language full-span pass on the internal honest shell: `True`.
- Publication Bilbao-equivalent final-object pass: `True`.

## Minimal Prototype

- The first portable real-space witness uses the generic family `l` with trivial stabilizer.
- This shows that the spatial bridge, lattice-fix filter, Bloch phase, and decomposition against double little-coreps all survive the move from 10.4.1.31 to 194.1.1.1.

## Double AI / Quotient Status

- Double local-corep library wired into the AI builder: `True`.
- Double AI candidate count / failures / compatibility-zero candidates: `45` / `0` / `11`.
- Double old verified AI rank / authoritative AI rank: `5` / `10`.
- Double quotient status / group / invariants / SNF diagonal: `success` / `trivial` / `[]` / `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.
- Double classification matches benchmark reference: `False`.
- Double blocker: Double-group quotient extraction completed, but the resulting classification does not match the Bilbao-backed workspace reference.
- Internal vs publication path counts: `8` / `7`.
- The present run now reaches an honest published-shell double AI lattice and quotient.
