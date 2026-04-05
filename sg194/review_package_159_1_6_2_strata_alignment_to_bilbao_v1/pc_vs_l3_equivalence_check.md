# PC vs L3 Equivalence Check

Bilbao uses `PC = (-1/3,-1/3,-w)`. The current internal grouped object is `L3 = (2/3,2/3,w)`.

These are equivalent at the grouped-strata level because:

1. `2/3 ≡ -1/3 (mod 1)` in the reciprocal lattice.
2. Replacing `w` by `-w` reverses the parametrization direction but does not change the underlying 1D family.
3. The internal line still connects the same maximal-point pair `KA/HA`, so at the target-capture and compatibility-builder level it serves as the same semantic stratum.

Therefore `L3` is currently treated as the internal semantic proxy for Bilbao's `PC`, although the naming/orientation is not yet normalized to Bilbao notation.
