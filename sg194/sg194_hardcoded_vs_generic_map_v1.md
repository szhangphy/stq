# SG194 Hardcoded vs Generic Map v1

- Generic modules now live in `pipeline_v1/` and are driven by `GroupSpec`.
- SG194-specific logic is isolated to SG194 backend scripts and the SG194 spec special-rule map.
- The single j/k canonicalization remains SG194-specific and is no longer scattered through unrelated driver code.
