# Review Package: 159.1.6.2 Strata Alignment to Bilbao v1

This package captures the round where the grouped geometry for `159.1.6.2` was extended from the previous “8 points + 3 vertical lines” state to a strata layer aligned with Bilbao 159.61 semantics.

## Scope of this round

- Recover family special strata from `swyckoff_k.py` / grouped plane boundaries
- Keep compare-only truth (`dBS=8`, `dAI=8`, `classification=trivial`) out of the active solver path
- Preserve the control group `194.1.12.16` with unchanged BS ranks

## External note

- external object: `P31c (No. 159.61)`
- there is a user-provided external hint `dBS = 8`, `dAI = 8`, `classification = trivial`
- this round does not treat that hint as a trusted target value

The package keeps this note only as an unverified external reference. It is not injected into the generic solver, and the terminal summary reports the solver's own current output instead.
