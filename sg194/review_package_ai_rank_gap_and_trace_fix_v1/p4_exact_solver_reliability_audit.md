# P4 Exact Solver Reliability Audit

- Manifold id: `P4`.
- Compared generators: `["b_A1'", "c_A1'", "d_A1'"]`.
- Exact solver reliable on passing reference: `True`.
- Current exact solver authority: `authoritative_for_this_audit`.
- Summary: P4 exact decomposition now exactifies both the little-group basis matrix and the induced band character before gauss-jordan solve. The passing reference b_A1' now returns an exact integral solution matching the numeric solve, while c_A1' and d_A1' remain exact non-integral.

- `b_A1'`: numeric=`integral`, exact=`integral`, integral_success=`True`, exact_matches_numeric=`True`.
- `c_A1'`: numeric=`integral`, exact=`integral`, integral_success=`True`, exact_matches_numeric=`True`.
- `d_A1'`: numeric=`integral`, exact=`integral`, integral_success=`True`, exact_matches_numeric=`True`.
