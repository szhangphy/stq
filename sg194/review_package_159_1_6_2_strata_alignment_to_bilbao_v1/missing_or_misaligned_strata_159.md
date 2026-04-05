# Missing Or Misaligned Strata for 159.1.6.2

After this round, the grouped geometry now materializes the targeted Bilbao semantic layer:

- DT via `L1`
- P via `L2`
- PC via `L3` as a semantic proxy
- Lambda via `L4`
- Q via `L5`
- U via `L6`
- C via `S1`

What still remains misaligned is not the existence of these strata, but their downstream quotient semantics:

- `PC` is not separately named internally; it is represented by `L3 = (2/3,2/3,w)`
- `C` is represented by internal plane coordinates `(v,-2v,w)` rather than Bilbao's `(u,u,w)` notation
- The solver still reports `dBS=9, dAI=4`, so the remaining gap is below grouped geometry and above final quotient semantics
