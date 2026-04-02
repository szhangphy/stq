# Automatic Final Object Reduction Report

## Counts

- Raw grouped points / lines / planes: `6` / `7` / `4`.
- Candidate paths enumerated: `62`.
- Final kept paths: `7`.
- Discarded duplicate paths: `55`.

## Final Point Shell

- `P1` at `(0, 0, 0)`; aliases: P1@(0, 0, 0).
- `P2` at `(0, 0, 1/2)`; aliases: P2@(0, 0, 1/2).
- `P3` at `(1/3, 1/3, 0)`; aliases: P3@(1/3, 1/3, 0), P3@(2/3, 2/3, 0).
- `P4` at `(2/3, 2/3, 1/2)`; aliases: P4@(2/3, 2/3, 1/2), P4__1d3_1d3_1d2@(1/3, 1/3, 1/2).
- `P5` at `(1/2, 0, 0)`; aliases: P5@(1/2, 0, 0), P5__1d2_1d2_0@(1/2, 1/2, 0), P5__0_1d2_0@(0, 1/2, 0).
- `P6` at `(1/2, 0, 1/2)`; aliases: P6@(1/2, 0, 1/2), P6__1d2_1d2_1d2@(1/2, 1/2, 1/2), P6__0_1d2_1d2@(0, 1/2, 1/2).

## Final Path Shell

- `FPATH01`: `P1 -> P2` from `L1` branch `['0', '0', '-w']` on `w` in `0 .. 1/2`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH02`: `P1 -> P3` from `L4` branch `['v', 'v', '0']` on `v` in `0 .. 1/3`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH03`: `P1 -> P5` from `L3` branch `['-v', '0', '0']` on `v` in `0 .. 1/2`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH04`: `P2 -> P4` from `L7` branch `['v', 'v', '1/2']` on `v` in `0 .. 1/3`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH05`: `P2 -> P6` from `L6` branch `['-v', '0', '1/2']` on `v` in `0 .. 1/2`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH06`: `P3 -> P4` from `L2` branch `['1/3', '1/3', '-w']` on `w` in `0 .. 1/2`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.
- `FPATH07`: `P5 -> P6` from `L5` branch `['1/2', '0', '-w']` on `w` in `0 .. 1/2`; reason: Selected as the simplest available representative for this endpoint pair after deduplicating orbit-equivalent raw/path candidates.

## Discarded Duplicates

- `L1` / `['0', '0', 'w']` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L1` / `['0', '0', 'w']` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L1` / `['0', '0', 'w']` for endpoint pair `P1-P2` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-v', '-v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['v', '-2v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-v', '2v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['2v', '-v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-2v', 'v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['v', '-2v', '0']` for endpoint pair `P1-P3` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['0', '-v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['0', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['v', '0', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['0', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['0', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['u', '0', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['-v', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L3` / `['v', '-v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['v', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-v', '-v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['v', '-2v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-v', '2v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['2v', '-v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['-2v', 'v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L4` / `['v', '-2v', '0']` for endpoint pair `P1-P5` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-v', '-v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['v', '-2v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-v', '2v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['2v', '-v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-2v', 'v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['v', '-2v', '1/2']` for endpoint pair `P2-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['0', '-v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['0', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['v', '0', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['0', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['0', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['u', '0', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['-v', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L6` / `['v', '-v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['v', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-v', '-v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['v', '-2v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-v', '2v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['2v', '-v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['-2v', 'v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L7` / `['v', '-2v', '1/2']` for endpoint pair `P2-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L2` / `['1/3', '1/3', 'w']` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L2` / `['2/3', '2/3', '-w']` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L2` / `['2/3', '2/3', 'w']` for endpoint pair `P3-P4` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['1/2', '0', 'w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['1/2', '1/2', '-w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['1/2', '1/2', 'w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['0', '1/2', '-w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['0', '1/2', 'w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['0', '1/2', 'w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
- `L5` / `['1/2', '-1', 'w']` for endpoint pair `P5-P6` was dropped; reason: Discarded because another candidate with the same final endpoint pair has lower branch complexity or higher selection priority.
