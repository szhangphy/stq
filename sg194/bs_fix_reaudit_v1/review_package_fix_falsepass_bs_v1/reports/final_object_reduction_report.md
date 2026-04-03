# Automatic Final Object Reduction Report

## Counts

- Raw grouped points / lines / planes: `6` / `7` / `4`.
- Candidate paths enumerated: `62`.
- Candidate path classes after strong signature collapse: `9`.
- Canonical endpoint-pair skeleton row rank: `23`.
- Full candidate row-language target rank: `24`.
- Final kept paths: `8`.
- Discarded candidate rows / duplicates: `54`.
- Selection augmentation path classes: `['PCLASS04']`.

## Final Point Shell

- `P1` at `(0, 0, 0)`; aliases: P1@(0, 0, 0).
- `P2` at `(0, 0, 1/2)`; aliases: P2@(0, 0, 1/2).
- `P3` at `(1/3, 1/3, 0)`; aliases: P3@(1/3, 1/3, 0), P3@(2/3, 2/3, 0).
- `P4` at `(2/3, 2/3, 1/2)`; aliases: P4@(2/3, 2/3, 1/2), P4__1d3_1d3_1d2@(1/3, 1/3, 1/2).
- `P5` at `(1/2, 0, 0)`; aliases: P5@(1/2, 0, 0), P5__1d2_1d2_0@(1/2, 1/2, 0), P5__0_1d2_0@(0, 1/2, 0).
- `P6` at `(1/2, 0, 1/2)`; aliases: P6@(1/2, 0, 1/2), P6__1d2_1d2_1d2@(1/2, 1/2, 1/2), P6__0_1d2_1d2@(0, 1/2, 1/2).

## Final Path Shell

- `FPATH01`: `P1 -> P2` from `L1` branch `['0', '0', '-w']` (class `PCLASS01`, stage `endpoint_pair_skeleton`, rank gain `6`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `FPATH02`: `P1 -> P3` from `L4` branch `['v', '-2v', '0']` (class `PCLASS02`, stage `endpoint_pair_skeleton`, rank gain `4`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `FPATH03`: `P1 -> P5` from `L3` branch `['-v', 'v', '0']` (class `PCLASS03`, stage `endpoint_pair_skeleton`, rank gain `4`); reason: Selected first as the canonical endpoint-pair skeleton representative, then retained in the published shell together with an additional same-endpoint path class because the skeleton alone did not span the full candidate row language.
- `FPATH04`: `P1 -> P5` from `L4` branch `['v', '-2v', '0']` (class `PCLASS04`, stage `full_span_augmentation`, rank gain `2`); reason: Added after the canonical endpoint-pair skeleton because it contributes independent row language not present in the skeleton span (rank 23 -> 24).
- `FPATH05`: `P2 -> P4` from `L7` branch `['v', '-2v', '1/2']` (class `PCLASS05`, stage `endpoint_pair_skeleton`, rank gain `1`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `FPATH06`: `P2 -> P6` from `L6` branch `['-v', 'v', '1/2']` (class `PCLASS06`, stage `endpoint_pair_skeleton`, rank gain `2`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `FPATH07`: `P3 -> P4` from `L2` branch `['1/3', '1/3', '-w']` (class `PCLASS08`, stage `endpoint_pair_skeleton`, rank gain `4`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.
- `FPATH08`: `P5 -> P6` from `L5` branch `['1/2', '0', '-w']` (class `PCLASS09`, stage `endpoint_pair_skeleton`, rank gain `1`); reason: Selected as the canonical endpoint-pair skeleton representative: shortest primitive segment first, then listed-line priority, then branch simplicity.

## Discarded Candidates

- `CANDIDATE_PATH_002` from `L1` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_049` from `L1` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_055` from `L1` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_015` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_017` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_019` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_021` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_023` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_057` from `L4` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_008` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_009` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_010` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_011` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_012` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_051` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_053` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_054` from `L3` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_016` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_018` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_020` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_022` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_024` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_058` from `L4` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_039` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_041` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_043` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_045` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_047` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_059` from `L7` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_032` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_033` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_034` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_035` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_036` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_052` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_061` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_062` from `L6` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_038` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because the published full-span selection already contains its row language after endpoint-pair skeleton selection and rank-closing augmentation.
- `CANDIDATE_PATH_040` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_042` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_044` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_046` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_048` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_060` from `L7` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_004` from `L2` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_005` from `L2` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_006` from `L2` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_026` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_027` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_028` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_029` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_030` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_050` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
- `CANDIDATE_PATH_056` from `L5` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate in the same path class was chosen as the canonical representative before the final path-class selection.
