# AI Honest Blocker Report

- Status: `blocked`.
- Blocker stage: `published_shell_obstruction_diagnosis`.
- Local library present / wired: `True` / `True`.
- Failure count: `0`.
- Nonzero-residual candidate count: `34`.
- Failure family ids: `[]`.
- Blocker: Non-abelian local irrep/corep libraries exist and validate, and they are now wired into the AI builder, but only 11 of 45 induced local objects satisfy compatibility on the published full-span augmented 8-path shell. Classification counts across raw42 / 7-path skeleton / published 8-path shells: {'fails_on_raw42': 34, 'compatible_on_published8': 11}. 34 candidates already fail on the diagnostic raw42 shell before any 7-path or 8-path reduction is applied. The extra 8th path is not the dominant single-AI obstruction. No candidate fails first on the reduced 7-path skeleton before the 8th path is added. On the published shell the nonzero residual rows concentrate on path histogram {'FPATH07': 68}.
