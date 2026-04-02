# Key Diffs

- Before this round:
  - active generic path still exposed retired class-sum branches
  - stage2 still had projection/internalization override semantics in its active path
  - legacy projection still validated against `13/13/trivial`
  - authoritative restriction decomposition still relied on `LUsolve`

- After this round:
  - active path is single-builder only
  - `extrinsic` is retired and raises if invoked through the active runtime path
  - stage2 is consumer-only
  - legacy projection is non-authoritative
  - exact solve now fails loudly with manifold/point/rep/field context
  - the first remaining blocker is representation-layer `L1/P1` under `linear_character`
