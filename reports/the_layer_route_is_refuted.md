# Normal surface separation does not move the sampled layer — prediction missed

**2026-09-18.** Registered in `docs/preregistration/2026-09-16_does_normal_shift_move_the_sampled_layer.md`,
written before the statistic was computed. **I predicted CHAIN SUPPORTED and was wrong.**

## Result

Render-clean arms (`s4–s9`), three disjoint pairs, same (z, θ) binning and derived axis as the two
prior studies. Layer centroid `c = Σ(k·ink_k)/Σ(ink_k)` over the five retained depth layers:

| pair | bins | median \|Δc\| | ρ(separation, \|Δc\|) | shuffled 95% | | signed mean |
|---|---:|---:|---:|---|---|---:|
| s4–s7 | 18,171 | 0.0220 | **+0.016** | [−0.015, +0.011] | differs | +0.0000 |
| s5–s8 | 18,234 | 0.0223 | **−0.006** | [−0.013, +0.014] | inside | +0.0011 |
| s6–s9 | 18,190 | 0.0233 | **−0.008** | [−0.013, +0.013] | inside | +0.0007 |

**Median ρ = −0.006 → REFUTED** by the registered rule. **Registered prediction (ρ ≥ +0.30, CHAIN
SUPPORTED): MISSED.**

Two of the three pairs sit *inside* their shuffled null. The one that differs does so at ρ = +0.016,
which is statistically distinguishable and substantively nothing.

The magnitudes say it more plainly than the correlation does: the two arms' layer centroids differ by
a median of **0.022 of a layer index** out of five, and the signed means are **+0.0000, +0.0011,
+0.0007** — no systematic direction, no arm sampling consistently deeper.

## This is the counter-case the registration named

The registration fixed the prediction at CHAIN SUPPORTED but wrote down the alternative and why it
would matter more:

> "the render resamples *relative to each arm's own surface*, in which case both arms centre their
> stack on their own sheet and the centroid difference could be near zero regardless of where those
> sheets sit. **That counter-case is the more interesting outcome**, because it would mean each arm
> reads its own surface consistently and the disagreement is about *which surface is right*, not
> about depth sampling."

That is what happened, and it is worth more than the prediction would have been.

**Each seed reads its own surface consistently.** The detector is not sampling a different depth of
papyrus in one arm than the other; both centre their five-layer stack on whatever sheet their fit
produced. So the disagreement is not "the same surface read at different depths" — it is **two
different surfaces, each read faithfully.**

## Where the mechanism ledger now stands

| contribution | status |
|---|---|
| scorer | **excluded** — re-scoring one strip moves the count 0.0009% |
| tangential surface slide | **excluded** — offsets incoherent |
| depth/layer sampling | **excluded** — this result, ρ = −0.006, centroids differ by 0.02 layers |
| normal surface separation | **present, small** — median ρ = −0.117 |
| small-bin counting noise | **present, substantial** — b = 0.72 against Poisson 0.5 |
| the systematic remainder | **still unattributed** |

Three routes are now closed rather than two, and the `b = 0.72` systematic component still has no
named mechanism. What this rules out is the most mechanically obvious way a surface shift could
change how much ink is found.

## What it leaves

If both arms read their own surface faithfully and neither samples deeper, then whatever scales with
ink content has to act **before** the detector — in what the fit decides the surface *is*, rather than
in how it is sampled. The normal separation result (ρ = −0.117) is the only measured handle on that,
and it is small.

**A note on the miss.** I predicted +0.30 from the reasoning that 3.5–5.0 voxels of separation against
a five-layer stack should move the centroid materially. That ignored the thing the registration's own
counter-case identified: the stack is positioned *relative to each arm's surface*, so separation
between surfaces does not translate into separation between sampling frames. The registration was
better than the prediction, which is the argument for writing counter-cases down before the data
arrives.

## Limits

* It cannot say which arm's surface is correct. There is no positional ground truth on PHercParis4.
* Five layers is a coarse depth probe; a sub-layer shift would not register.
* Three pairs, one scroll region, as throughout this line.
