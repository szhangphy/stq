# Publication Shell Reduction Report

- Internal honest shell path count: `8`.
- Publication point count: `6`.
- Publication path-class count: `8`.
- Publication selected path count: `7`.
- Publication actual path pairs: `[['P1', 'P2'], ['P1', 'P3'], ['P1', 'P5'], ['P2', 'P4'], ['P2', 'P6'], ['P3', 'P4'], ['P5', 'P6']]`.
- Publication unknown count: `34`.

## Publication Path Classes

- `PUBCLASS01` pair `['P1', 'P2']` members `['PCLASS01']` from raw lines `['L1']`; selected = `True`; aggregate rank `6`, selected-basis rank `6`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 6).
- `PUBCLASS02` pair `['P1', 'P3']` members `['PCLASS02']` from raw lines `['L4']`; selected = `True`; aggregate rank `4`, selected-basis rank `4`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 4).
- `PUBCLASS03` pair `['P1', 'P5']` members `['PCLASS03', 'PCLASS04']` from raw lines `['L3', 'L4']`; selected = `True`; aggregate rank `6`, selected-basis rank `6`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 6).
- `PUBCLASS04` pair `['P2', 'P4']` members `['PCLASS05']` from raw lines `['L7']`; selected = `True`; aggregate rank `1`, selected-basis rank `1`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 1).
- `PUBCLASS05` pair `['P2', 'P6']` members `['PCLASS06']` from raw lines `['L6']`; selected = `True`; aggregate rank `2`, selected-basis rank `2`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 2).
- `PUBCLASS06` pair `['P2', 'P6']` members `['PCLASS07']` from raw lines `['L7']`; selected = `False`; aggregate rank `1`, selected-basis rank `1`; reason: Discarded at the publication level because its aggregated canonical row language is already contained in an earlier selected publication path class for the same endpoint pair.
- `PUBCLASS07` pair `['P3', 'P4']` members `['PCLASS08']` from raw lines `['L2']`; selected = `True`; aggregate rank `6`, selected-basis rank `6`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 6).
- `PUBCLASS08` pair `['P5', 'P6']` members `['PCLASS09']` from raw lines `['L5']`; selected = `True`; aggregate rank `4`, selected-basis rank `4`; reason: Retained as the publication-level representative for this endpoint pair because its aggregated canonical row language adds independent compatibility rows within the pair (rank 0 -> 4).
