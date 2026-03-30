# Correctness Audit for 10.4.1.31

## single-group

- `BS_likely_correct = true`
- `AI_likely_complete = true`
- `quotient_interpretation_likely_correct = true`
- raw quotient: `Z2 x Z2`
- suspicion ranking: `AI / AI completeness > quotient interpretation > BS`
- confidence: `medium`
- main issue: No hard contradiction is visible; if forced to pick the weakest layer, the family-level completeness proof is the first one to stress because it depends on the local census assumptions.

### BS layer evidence

- line-only and with-planes summaries are both present, and the nullity drops from 16 to 8 when planes are added
- plane necessity audit reports added rank 13 with shape [30, 31]
- with-planes BS basis has 8 basis columns, matching nullity 8
- the compatibility workflow is explicit and uses integer Smith decomposition rather than a floating nullspace

### AI / completeness evidence

- all 15 families are explicitly listed complete in the completeness summary
- the local site symmetries are all abelian or order-2 antiunitary case-a extensions, which limits hidden missing higher-dimensional local objects
- independent SNF recomputation from AI basis coefficients reproduces Z2 x Z2

### Quotient interpretation evidence

- independent SNF recomputation gives smith diagonal [1, 1, 1, 1, 1, 1, 2, 2]
- the quotient has no free part, so there is no free-vs-finite mixing in this case
- the result remains scoped to the current with-planes basis and unknown ordering, but that is a scope caveat rather than a contradiction

### Evidence files

- `single_group_bs_summary.json`
- `single_group_plane_necessity_summary.json`
- `single_group_bs_with_planes_summary.json`
- `single_group_bs_with_planes_basis_raw.json`
- `single_group_ai_expanded_v3_basis.json`
- `single_group_ai_completeness_summary.json`
- `single_group_ai_completeness_audit.md`
- `single_group_indicator_group_summary.json`
- `single_group_indicator_generators.json`

- recommended next step: If more confidence is needed, independently rederive the local-family census from the site-symmetry data rather than from the current audited library outputs.

## double-group

- `BS_likely_correct = true`
- `AI_likely_complete = true`
- `quotient_interpretation_likely_correct = uncertain`
- raw quotient: `Z^2 x Z2 x Z2 x Z2 x Z2`
- suspicion ranking: `quotient interpretation > AI / AI completeness > BS`
- confidence: `high`
- main issue: The raw mixed quotient is likely real, but the reporting layer still mixes a full raw quotient with indicator language.

### BS layer evidence

- double-group BS summary reports shape [30, 31] with rank 23 and nullity 8
- double-group raw BS basis has 8 basis columns, matching nullity 8
- the k-space backbone audit explicitly redoes line blocks, plane necessity, and with-planes kernel extraction on the double branch

### AI / completeness evidence

- all 15 families are marked complete after combining point-like and parametric double local objects
- the family site symmetries are still only order-2 or simple unitary/antiunitary extensions, which makes the completeness model relatively constrained
- independent SNF recomputation from the AI_v2 basis coefficients reproduces Z^2 x Z2 x Z2 x Z2 x Z2

### Quotient interpretation evidence

- the algebraic quotient extraction itself is well supported by the stored AI basis coefficients
- the recomputed quotient has free rank 2 and finite part [2, 2, 2, 2]
- the interpretation layer is the weak point because the artifact naming still uses indicator-language even though the quotient contains a free part
- Because the quotient contains a free part, the current BS_double/AI_double is not a purely finite indicator group. The honest algebraic result is the full mixed quotient reported here.

### Evidence files

- `double_group_bs_summary_10.4.1.31.json`
- `double_group_bs_basis_raw_10.4.1.31.json`
- `double_group_kspace_backbone_audit_10.4.1.31.md`
- `double_group_plane_necessity_audit_10.4.1.31.md`
- `double_group_ai_v2_basis_10.4.1.31.json`
- `double_group_ai_completeness_summary_10.4.1.31.json`
- `double_group_ai_completeness_audit_10.4.1.31.md`
- `double_group_bs_mod_ai_summary_10.4.1.31.json`
- `double_group_indicator_group_summary_10.4.1.31.json`
- `double_group_indicator_generators_10.4.1.31.json`

- recommended next step: Split the raw quotient into its free and torsion sectors in the primary artifacts, and reserve indicator language for the finite torsion part only.
