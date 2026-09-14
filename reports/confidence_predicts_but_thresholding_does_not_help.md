# Confidence predicts which ink reproduces — and thresholding on it does not help

**2026-09-14.** Registered in
`docs/preregistration/2026-09-13_does_confidence_predict_reproducibility.md`; analysis committed
before any probability map existed. `reports/confidence_vs_reproducibility.json`.

## The registered result: positive, and robust to binning

Mean detector probability of ink in bins **all three seeds agree on**, against ink **only one seed
found**:

| binning | unanimous | lone-arm | difference | p |
|---|---:|---:|---:|---:|
| 48 × 128 | 0.6696 | 0.5375 | **+0.1321** | <0.001 |
| 96 × 256 | 0.6820 | 0.5315 | **+0.1505** | <0.001 |
| 192 × 512 | 0.6998 | 0.5406 | **+0.1591** | <0.001 |

**VERDICT: CONFIDENCE PREDICTS REPRODUCIBILITY.** Significant at all three binnings, satisfying the
registered bin gate, and — unlike the consensus fraction that moved 89.7% → 43.2% with bin size —
**the effect is stable across it**.

Validity gate passed: re-scored `total_fg_pixels` matched published to −0.0009%, +0.0004%, +0.0005%,
so the probability patch is inert on the default path.

## The practical inference that followed from it is WRONG

The verdict text says *"a higher threshold would preferentially discard the irreproducible ink"*.
That is the obvious next step, and it does not work.

Raising the probability threshold and measuring placement agreement between seeds:

| threshold | ink kept | mean pairwise r |
|---:|---:|---:|
| 0.50 | 100% | **0.702** |
| 0.70 | 34.8% | 0.574 |
| 0.90 | 20.0% | **0.496** |

Reproducibility gets **worse**, not better. But sparser maps correlate worse for a purely mechanical
reason, so that alone proves nothing. **The control that settles it is matched sparsity** — top-N% by
confidence against a *random* N% of the same ink:

| kept | top-by-confidence | random | difference |
|---:|---:|---:|---:|
| 100% | 0.690 | 0.690 | +0.000 |
| 75% | 0.666 | 0.676 | −0.010 |
| 50% | 0.619 | 0.651 | **−0.033** |
| 30% | 0.544 | 0.594 | **−0.050** |
| 20% | 0.492 | 0.554 | **−0.061** |

**Selecting the most confident ink is slightly worse than selecting at random.** Confidence does not
buy reproducibility at fixed density; it costs a little.

## Reconciling the two

Both are true and they are not in tension:

* **Bin-level**: ink in bins all three seeds found is genuinely more confident. Confidence carries
  real information about agreement.
* **Map-level**: selecting by confidence does not produce a more reproducible map, because
  high-confidence ink is **spatially concentrated** — it clusters in strong text regions. Keeping only
  it changes the spatial distribution, and placement correlation is driven by that distribution.
  Random selection thins the map while preserving its shape.

The clustering explanation is a **reading, not a measurement** here. What is measured is that the
matched-density comparison goes the wrong way.

## What this means

**Thresholding is not a free stability lever.** The finding that motivated this — 28% of recovered ink
does not survive a reseed — is not addressable by discarding low-confidence pixels.

**Averaging remains the only lever that works**, and it works as independent-noise theory predicts
(`averaging_seeds_buys_what_noise_theory_predicts.md`, replicated on three triplets at 1.10–1.15×
predicted). It costs 3× the compute, and the cheap alternative has now been tested and does not
substitute for it.

## On the process

The registered study returned a clean positive and its own verdict text drew an actionable conclusion
from it. **That conclusion was not part of the registration and was not tested by it.** One follow-up
control, thirty minutes on data already on disk, refuted it.

A registered result licenses exactly what it measured. The sentence after it is a new claim.
