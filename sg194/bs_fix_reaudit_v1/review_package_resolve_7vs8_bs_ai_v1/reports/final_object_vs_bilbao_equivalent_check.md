# Final Object vs Bilbao-Equivalent Sanity Check

- Point count match: `True`.
- Point id order match: `True`.
- Path count match: `False`.
- Path pair set match: `False`.
- Unique path pair set match: `True`.
- Bilbao-equivalent final-object pass: `False`.

## Actual

- Final point ids: `['P1', 'P2', 'P3', 'P4', 'P5', 'P6']`.
- Final path endpoint pairs: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.
- Final unique endpoint-pair set: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.

## Expected

- Expected point ids: `['P1', 'P2', 'P3', 'P4', 'P5', 'P6']`.
- Expected path endpoint pairs: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.
