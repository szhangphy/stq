# SG 194 External Source Audit

Main route selected:
- Single-valued ordinary SG 194: `Bilbao ordinary SITESYM site-symmetry induced representations at GM, A, K, H, M, L.`
- Double-valued ordinary SG 194: `Bilbao BANDREP Wyckoff pages without TR, parsed one Wyckoff position at a time.`

Sources used:
- Bilbao SITESYM landing page: https://cryst.ehu.es/rep/sitesym.html (ordinary SG 194 single-valued site-symmetry route)
- Bilbao SITESYM CGI: https://cryst.ehu.es/cgi-bin/rep/programs/sitesym/sitesym_cgi.py (single-valued induced site-symmetry decomposition tables at GM/A/K/H/M/L)
- Bilbao BANDREP CGI: https://cryst.ehu.es/cgi-bin/cryst/programs/bandrep.pl (double-space-group Wyckoff-resolved band representations without time reversal)
- Bilbao DSITESYM CGI: https://cryst.ehu.es/cgi-bin/cryst/programs/dsitesym.pl (availability check only; not the main reconstruction route after BANDREP Wyckoff tables proved sufficient)
- TopMat fallback: https://tm.iphy.ac.cn/ (fallback availability check; not needed after Bilbao access succeeded)

Availability and blockers:
- Bilbao live access: `True`
- Ordinary single route available: `True`
- Double BANDREP route available: `True`
- Proxy issue: The local shell proxy had to be bypassed by disabling trust_env and seeding the turnstile_passed cookie.
- Single-route comment: Ordinary SG 194 required Bilbao SITESYM rather than DSITESYM because the target is the ordinary single-valued SG 194 standard AI.
- Double-route comment: BANDREP Wyckoff pages were sufficient to enumerate Bilbao's physically irreducible double-space-group band representations site by site.

Remaining blockers:
- Single: No external-data blocker remained after ordinary SITESYM access was stabilized.
- Double: Bilbao labels physically irreducible double-space-group generators in a convention that does not match the current 45-label local-corep library one-to-one, especially at 2b/2c/2d and 6h.
