# AI Filter Bug Audit

- group: `222.1.1.1`
- equivalent OG object: `222.1.1601`
- bug exists: `True`
- root cause: `The generic 222 quotient path silently drops AI candidates that fail the exact point-shell embedding solve, then computes Smith quotient on the survivors only. This creates the observed dBS != dAI gap and fake-final classification.`
- single generic target direct: `{'dBS': 11, 'dAI': 10, 'classification': 'Z x Z4', 'dbs_dai_gap': 1}`
- double generic target direct: `{'dBS': 11, 'dAI': 10, 'classification': 'Z x Z4', 'dbs_dai_gap': 1}`
