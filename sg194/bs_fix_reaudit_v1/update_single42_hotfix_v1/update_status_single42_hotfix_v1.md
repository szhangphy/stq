# Update Status: single42 hotfix v1

This update stays on the single authoritative `194.1.1.1` hotfix only. The active BS object remains the raw current with-planes 42-unknown shell, not the projected 34-shell diagnostic object.

Current authoritative single status:

- active object: `raw current with-planes 42-unknown shell`
- matrix shape: `[61, 42]`
- rank: `29`
- nullity: `13`
- tail unknowns preserved: `S1_R1`, `S1_R2`, `S2_R1`, `S2_R2`, `S3_R1`, `S3_R2`, `S4_R1`, `S4_R2`

What this round rechecked:

- The active authoritative line builder and plane builder still use `character` on the single hotfix path.
- The single authoritative JSON outputs remain aligned with the current source semantics.
- The external review package was rebuilt after fixing its output snapshot ordering, so it no longer risks shipping a stale `single_line_compatibility.json`.
- The generic/public layer still exposes raw-shell availability and keeps target publication blocked instead of silently publishing the projected quotient as the active object.

What is fixed in the current source semantics:

- Authoritative line builder `linear_character -> character` correction is active.
- Authoritative plane builder `linear_character -> character` correction is active.
- The exact integer decomposition path now accepts the float-snapped captures needed for the authoritative single run.
- Generic/public metadata now distinguishes raw-shell availability from target-pending blockage.

What is still not final:

- This is not a full BS/AI closeout.
- AI completeness remains blocked for the non-abelian SG 194 local library.
- The generic/public target object is still pending a same-shell builder.
- Double mode was only checked non-destructively; no new double repair is claimed here.
- Stage2, benchmark/internalization, Bilbao, and magnetic-group directions remain intentionally out of scope.
