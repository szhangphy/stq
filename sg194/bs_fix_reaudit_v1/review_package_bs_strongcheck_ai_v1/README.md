# SG194 BS Strongcheck + AI Seed Audit

This package contains the current foreground review handoff for SSG `194.1.1.1`.

Current state:
- The published BS object is the reduced 6-point / 7-path shell.
- The strong BS check now proves the final object keeps one canonical primitive representative for each intrinsic listed special-line family `L1..L7`.
- `point_row_translation` is not published into the current AI seed; the legality audit removed it.
- AI is still `seed_only`, not a complete honest AI lattice.

Package layout:
- `src/`: current runtime source files that implement the reduction and reporting logic.
- `outputs/`: regenerated single/double JSON outputs used by the current published object.
- `reports/`: reduction, strong path-signature, strong equivalence, translation legality, and AI seed audit reports.
- `logs/`: package build note.

Not final:
- `selected_rows_span_full_candidate_row_language` is intentionally `False`; the final object is built from canonical intrinsic line families, not from every composite candidate segment.
- AI still lacks the complete local irrep/corep library and honest AI-in-BS lattice construction.
