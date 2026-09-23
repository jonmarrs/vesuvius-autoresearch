# The current tier's fit-only floor, pooled: 0.074 [0.051, 0.134], so 3v3 resolves ~17%, not 21%

**2026-09-22.** The result of `docs/preregistration/2026-09-22_pooled_fit_only_floor.md`, decided by
`scripts/analyse_pooled_fit_only_floor.py` (written before any arm scored). Data:
`reports/pooled_fit_only_floor.json`. The six new arms (`detfit_ns1..ns3`, `detfit_an1..an3`) ran on
one tree (`be09a8503`) and one render image, each with `FLATTEN_DETERMINISTIC=1` and its shim guard
passing. They are pooled with the six `curbase` arms from `detfit_s4..s9`.

## The result

| group | n | deterministic mean | fit-only CV | stock CV |
|---|---:|---:|---:|---:|
| `curbase` | 6 | 3,069,469 | 0.0909 | 0.0742 |
| `nosamecur` | 3 | 2,945,668 | 0.0277 | 0.0127 |
| `anchor10cov` | 3 | 2,872,949 | 0.0544 | 0.0419 |
| **pooled, within group** | 12 | | **0.0736** [0.0506, 0.1344], df = 9 | 0.0590 [0.0406, 0.1077] |

**Registered verdict: BETWEEN** (0.055–0.075): the tier sits between the quiet configs and `curbase`,
so designs sized on `curbase` alone were conservative. **The minimum detectable effect at three fits
per arm is 16.8%**, down from the 20.8% that `curbase` alone implied.

* **Prediction 1** (pooled CV in 0.040–0.075): **met**.
* **Prediction 2** (`curbase` stays the noisiest): **met**.
* **Prediction 3**: withheld by registration (df = 2 per comparison group establishes nothing).
* **df = 9**, not the 11 the registration first stated (twelve arms minus three group means). The
  correction was recorded before this result existed, and the code always computed 9.

## Read the interval, not the band

The point estimate is **0.0014 below** the 0.075 boundary, and its 95% interval (0.051–0.134) covers
**all three** registered bands. BETWEEN is the correct application of the registered rule, and it is
the figure to quote. But the data cannot exclude "`curbase` was representative" (> 0.075) or
"`curbase` was unrepresentative" (< 0.055). **For design, use the interval:** at 3v3 the MDE is
16.8% on the point estimate and ~30% at the interval's upper end.

## What is consistent with today's other results

* **Deterministic CV ≥ stock CV in every group.** This is expected if the flatten does not govern the
  fit spread: same-fit re-layout noise is about 2.5% of the count, about 7% of the fit-only variance
  (`reports/the_flatten_noise_is_local_rescoring.md`, section 5). At n = 3 per group the ordering is
  not evidence of anything by itself.
* **What drives the floor is the fit**, config by config: `nosamecur` fits agree to about 3%,
  `curbase` fits to about 9%.

## What it does not do

* **It does not reopen a published null.** The most favourable end of the interval (CV 0.051) gives
  an MDE at 3v3 of ~11.6%, and the largest observed null effect in the corpus is 5.49%. As registered.
* **It is one tree, one ROI (`w120–w129`), one scorer**, and three configs of one tier.
