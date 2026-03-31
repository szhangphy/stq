# SG 194 Non-Abelian Site-Symmetry Inventory

## Scope

- Target group fixed to `194.1.1.1`.
- This inventory is built from the current local `swyckoff_r.py` real-space families plus direct stabilizer recomputation through the audited stage-1 bridge.

## Family Table

| family | dim | mult | representative | site symmetry | order | unitary | antiunitary | abelian | nonabelian | blocker relevance |
| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `l` | `3` | `24` | `x, y, z` | `1` | `1` | `1` | `0` | `True` | `False` | `not_blocking` |
| `k` | `2` | `12` | `x, y, 1/4` | `m[z]` | `2` | `2` | `0` | `True` | `False` | `secondary_abelian_followon` |
| `j` | `2` | `12` | `x, -x, z` | `m[110]` | `2` | `2` | `0` | `True` | `False` | `secondary_abelian_followon` |
| `i` | `1` | `12` | `x, 0, 0` | `2[x]` | `2` | `2` | `0` | `True` | `False` | `secondary_abelian_followon` |
| `h` | `1` | `6` | `x, -x, 1/4` | `m[z] * 2[1-10] * m[110]` | `4` | `4` | `0` | `True` | `False` | `secondary_abelian_followon` |
| `g` | `0` | `6` | `1/2, 0, 0` | `2[x] * m[x] * -1` | `4` | `4` | `0` | `True` | `False` | `secondary_abelian_followon` |
| `f` | `1` | `4` | `1/3, 2/3, z` | `m[x] * m[y] * 3[z] * m[110]` | `6` | `6` | `0` | `False` | `True` | `primary_nonabelian_blocker` |
| `e` | `1` | `4` | `0, 0, z` | `m[x] * m[y] * 3[z] * m[110]` | `6` | `6` | `0` | `False` | `True` | `primary_nonabelian_blocker` |
| `d` | `0` | `2` | `1/3, 2/3, 3/4` | `m[x] * m[y] * 3[z] * m[z] * -6[z] * 2[1-10] * m[110] * 2[120] * 2[210]` | `12` | `12` | `0` | `False` | `True` | `primary_nonabelian_blocker` |
| `c` | `0` | `2` | `1/3, 2/3, 1/4` | `m[x] * m[y] * 3[z] * m[z] * -6[z] * 2[1-10] * m[110] * 2[120] * 2[210]` | `12` | `12` | `0` | `False` | `True` | `primary_nonabelian_blocker` |
| `b` | `0` | `2` | `0, 0, 1/4` | `m[x] * m[y] * 3[z] * m[z] * -6[z] * 2[1-10] * m[110] * 2[120] * 2[210]` | `12` | `12` | `0` | `False` | `True` | `primary_nonabelian_blocker` |
| `a` | `0` | `2` | `0, 0, 0` | `2[x] * m[x] * 2[y] * m[y] * 3[z] * -3[z] * 2[110] * m[110] * -1` | `12` | `12` | `0` | `False` | `True` | `primary_nonabelian_blocker` |

## Non-Abelian Site-Symmetry Types

- `C3v` / `3m`: families `f, e`, irreps `A1, A2, E`.
- `D3d_like` / `-3m`: families `a`, irreps `A1g, A1u, A2g, A2u, Eg, Eu`.
- `D3h_like` / `-6m2`: families `d, c, b`, irreps `A1', A1'', A2', A2'', E', E''`.

## Blocker Diagnosis

- The primary stage-1 blocker source is the non-abelian set `C3v` on `e,f` and the two order-12 non-abelian types on `a,b,c,d`.
- The order-2 / order-4 abelian families are follow-on work for AI closure, but they are not the conceptual reason the stage-1 portability pilot stalled.
- All site symmetries remain purely unitary in the present SG 194 controlled case, so the double-group stage requires projective local irreps, not antiunitary Wigner-corep extensions.
