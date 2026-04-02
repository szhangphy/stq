# SG194 BS Fix Experiment v1

## Scope

- Target fixed to `194.1.1.1`.
- No Bilbao / magnetic-group / benchmark/internalization inputs were used.
- This experiment only tests the repo-internal BS construction hypothesis.

## Probe 1: Current Authoritative Runtime

- status: `success`
- matrix shape/rank/nullity: `[61, 42]` / `29` / `13`

## Probe 2: L1 Numeric Decomposition

- target channel: `L1 -> P1_R1` under `linear_character`.
- verdict: Both tested L1 sample points admit only complex non-integer coefficients for P1_R1 on the sampled line basis, so the active unique-integer basis-decomposition ansatz is invalid for L1.

| sample | coeff summary | numeric residual | integer residual |
| --- | --- | ---: | ---: |
| `[0.0, 0.0, 0.2]` | `0.904508+0.293893i, 0.095492-0.293893i` | `1.759e-15` | `3.464e+00` |
| `[0.0, 0.0, 0.8]` | `0.095492+0.293893i, 0.904508-0.293893i` | `1.709e-15` | `3.464e+00` |

## Probe 3: Direct Restriction-Class Fallback

- current build before fallback: `success`
- fallback matrix shape/rank/nullity: `[102, 34]` / `27` / `7`
- fallback line rows / plane rows: `43` / `59`
- fallback lines: `['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7']`
- fallback planes: `['S1', 'S2', 'S3', 'S4']`
- basis vector count after fallback: `7`
- same object as intended 42-shell: `False`
- dropped unknowns vs intended 42-shell: `['S1_R1', 'S1_R2', 'S2_R1', 'S2_R2', 'S3_R1', 'S3_R2', 'S4_R1', 'S4_R2']`
- AI candidates still in same object: `False`

## Conclusion

- The active repo failure is real and reproduces directly in the current source at `L1/P1_R1`.
- `linear_character` plus exact unique integer basis decomposition is not automatically correct; L1 needs complex coefficients at both tested sample points.
- A cache-driven direct restriction-class fallback can rebuild a BS matrix, which confirms the sampled-manifold integer decomposition ansatz is the blocker, but that fallback changes the object from the intended 42-shell to a 34-point shell.
- This experiment therefore validates the bug diagnosis but does not yet constitute the final repo patch.
