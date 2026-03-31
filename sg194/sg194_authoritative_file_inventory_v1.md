# SG194 authoritative-looking file inventory v1

- benchmark authoritative file: `sg194/current_status_1941111_benchmark_v1.json`

| path | classification | benchmark-authoritative | object kind | current value | notes |
| --- | --- | --- | --- | --- | --- |
| sg194/current_status_1941111_benchmark_v1.json | benchmark_authoritative_status | true | authoritative benchmark status | Z6 / dBS 10 / dAI 10 | Primary benchmark-first status file for SG194 after takeover. |
| sg194/current_status_1941111_benchmark_v1.md | benchmark_authoritative_status | true | human-readable benchmark status | benchmark-first summary | Markdown companion to the authoritative benchmark JSON. |
| sg194/sg194_target_1941111_og1494_bns263_benchmark_verdict_v1.json | benchmark_oracle | false | benchmark oracle payload | Z6 / dBS 10 / dAI 10 | Copied topmat-derived oracle verdict. |
| sg194/sg194_external_benchmark_from_topmat_v3.json | benchmark_oracle_support | false | benchmark support data | topmat direct-vs-copied capability audit | Records what topmat_src gives directly and what had to be computed locally. |
| sg194/sg194_current_vs_external_object_matching_v3.json | reconciliation_support | false | benchmark reconciliation map | raw / phase-aware / stage2 matched against benchmark | Explains which internal objects are not the benchmark. |
| sg194/current_status_194.1.1.1.json | internal_raw_object | false | raw internal status | pre-stage2 blocked current raw object | Raw internal SG194 object before later internal reductions. |
| sg194/group_194_1_1_1_single_indicator_group_summary.json | internal_raw_object | false | single raw quotient summary | Z^3 in raw internal BS space | Not benchmark; internal raw quotient only. |
| sg194/group_194_1_1_1_double_indicator_group_summary.json | internal_raw_object | false | double raw quotient summary | Z^3 in raw internal BS space | Not benchmark; internal raw quotient only. |
| sg194/sg194_phase_aware_l2_compatibility_v1.json | local_prototype | false | phase-aware raw repair prototype | raw BS rank 16 -> 13 locally | Necessary as a raw-layer repair if the internal SG194 builder is being fixed, but directionally wrong if interpreted as the benchmark answer itself. |
| sg194/current_status_194.1.1.1_stage2.json | stale_superseded | false | anchored internal reduced quotient claim | 13 / 13 / trivial | Retained as internal stage2 claim only; superseded for benchmark use. |
| sg194/workflow_portability_stage2_summary_194.1.1.1.json | stale_superseded | false | stage2 workflow summary | 13 / 13 / trivial | Internal stage2 summary; no longer benchmark-final. |
| sg194/group_194_1_1_1_single_ai_completion_summary.json | stale_superseded | false | single internal completion summary | 13 / 13 / trivial | Internal completion summary only; not the benchmark classification. |
| sg194/group_194_1_1_1_double_ai_completion_summary.json | stale_superseded | false | double internal completion summary | 13 / 13 / trivial | Internal completion summary only; not the benchmark classification. |
| sg194/current_status_sg194_external_matrix_final.json | unresolved_mapping_layer | false | mapping-layer unresolved status | single null / double null | Still useful, but only as current-to-external mapping blocker status. |
| sg194/README.md | benchmark_portal | false | repo SG194 entrypoint | benchmark-first index | Should point readers to the new benchmark authoritative status first. |
| sg194/handoff_194.1.1.1_stage2.md | stale_superseded | false | internal stage2 handoff | 13 / 13 / trivial handoff | Retained only as internal stage2 handoff, not benchmark-final. |
| sg194/live_checkpoint_sg194_1941111.json | benchmark_portal | false | rolling checkpoint | benchmark takeover checkpoint | Checkpoint should summarize the benchmark takeover state, not the old stage2 final claim. |
| sg194/live_checkpoint_sg194_1941111.md | benchmark_portal | false | rolling checkpoint markdown | benchmark takeover checkpoint | Human-readable checkpoint companion. |
| sg194/review_package_sg194_stage2_closeout_followup_v3/README.md | stale_package_portal | false | historical stage2 package portal | package says 13 / 13 / trivial | Historical internal package; superseded for benchmark use by the benchmark takeover artifacts. |
| sg194/review_package_sg194_stage2_closeout_followup_v3/handoff_194.1.1.1_stage2.md | stale_package_portal | false | historical stage2 package handoff | package handoff says trivial | Historical internal package handoff; not benchmark authoritative. |
| sg194/review_package_sg194_stage2_closeout_followup_v3/live_checkpoint_sg194_1941111.md | stale_package_portal | false | historical stage2 package checkpoint | package checkpoint says trivial | Historical internal package checkpoint; not benchmark authoritative. |

## Inventory verdict

- benchmark-authoritative file count: `2`
- mandatory paths present: `true`
- stage2 files marked superseded: `true`
