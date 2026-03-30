# SG194 External Matrix Acquisition

Ordinary matrix:
- Shape: `34 x 45`
- Landing page: `https://cryst.ehu.es/rep/sitesym.html`
- CGI: `https://cryst.ehu.es/cgi-bin/rep/programs/sitesym/sitesym_cgi.py`
- Raw cache files: `85`

Spinorial matrix:
- Shape: `56 x 33`
- CGI: `https://cryst.ehu.es/cgi-bin/cryst/programs/bandrep.pl`
- Raw cache files: `12`

Parsing route:
- Ordinary: showwp -> showorbit -> calcsim tables -> exact integer 34x45 matrix.
- Spinorial: BANDREP Wyckoff tables -> full mixed 56x78 matrix -> physically irreducible 56x33 submatrix.

Final cache format:
- machine-readable JSON with row labels, column labels, integer matrix entries, provenance, and normalization notes.
- raw HTML kept under `sg194_external_matrix_cache/ordinary` and `sg194_external_matrix_cache/spinorial`.
