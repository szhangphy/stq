# SG194 Double Problem-Sector Lift

        ## Inventory

        - current problem matrix shape: `[34, 10]`
        - external problem matrix shape: `[56, 10]`
        - generator label ordering: `['b:E1↑G(4)', 'b:E2↑G(4)', 'b:E3↑G(4)', 'c:E1↑G(4)', 'c:E2↑G(4)', 'c:E3↑G(4)', 'd:E1↑G(4)', 'd:E2↑G(4)', 'd:E3↑G(4)', 'h:E↑G(12)']`

        ## Why the v2 proxy was still insufficient

        The v2 metric used column-space comparison on the transposed matrices. That showed equality of row spaces in the shared generator-label ambient, but it did not exhibit an explicit map from current HSP rows to external spinorial rows. This round constructs that map directly.

        ## Explicit lift

        - rational lift exists: `True`
        - integer lift exists: `False`
        - coefficient field used for the honest lift: `Q`
        - ambient lift shape: `[56, 34]`
        - common denominator lcm: `2`
        - exact verification `L * C = E`: `True`

        ## Row bases

        - current basis row `0` = `P1_R1`
- current basis row `1` = `P1_R2`
- current basis row `8` = `P1_R9`
- current basis row `15` = `P3_R1`
- current basis row `16` = `P3_R2`
- current basis row `31` = `B1_R1`
- external basis row `3` = `A:A5`
- external basis row `5` = `A:A6`
- external basis row `20` = `Γ:Γ8`
- external basis row `27` = `H:H5`
- external basis row `28` = `H:H7`
- external basis row `40` = `K:K8`

        ## Integer obstruction

        - Smith diagonal: `[1, 1, 1, 2, 2, 2]`
- obstruction rank mod 2: `3`
- representative row `27` `H:H5` with tail parity `[1, 0, 1]`
- representative row `28` `H:H7` with tail parity `[0, 1, 1]`
- representative row `40` `K:K8` with tail parity `[1, 0, 0]`

        ## Exact matrix entries

        The full exact rational ambient lift matrix is serialized in `sg194_double_problem_sector_lift.json` under `lift.ambient_lift_matrix`. The basis-level matrices are also included there under `row_basis`.
