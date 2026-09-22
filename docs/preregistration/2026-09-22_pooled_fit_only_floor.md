# Pre-registration: is ~20% the loop's floor, or is `curbase` unrepresentative?

**Written 2026-09-22, before any arm of this study is launched.** First study to use
`docs/preregistration/TEMPLATE.md`.

## The question

`reports/fit_rng_dominates_the_flatten_was_never_binding.md` measured a fit-only CV of
**0.0909 [0.0568, 0.2230]** on `curbase_s4..s9` and scoped it, the same day, to *that config*:
`curbase` is the current tier's noisiest group on stock flattens (0.0742 vs `nosamecur` 0.0127 and
`anchor10cov` 0.0419) and the only one with a genuine outlier, while the tier's pooled stock figure
(0.0536, df=11) sits below it.

So "the loop resolves ~20% at 3v3" is either **the tier's floor** or **one unrepresentative config's**.
That changes what every future current-tier design costs, and it is answerable from meshes already
on disk.

## Reachability — checked before designing the validation

All six meshes exist with the full `w120`–`w129` range: `nosamecur_s1..s3` and
`anchor10cov_pilot,_s2,_s3`, 10 spliced windings each. The deterministic path is proven on six arms
(`detfit_s4..s9`), all of which cleared the shim-activation guard.

## The floor — measured, not inherited

This study *is* a floor measurement, so there is no floor to inherit. The quantity is the **pooled
within-group CV across three configs** with the flatten's contribution at exactly zero
(byte-identical surfaces, `reports/the_flatten_is_reproducible_when_asked.md`).

**The interval is the result.** At df=11 the chi-square CI spans a factor of **2.4**, against 3.9 at
df=5. Every number below is reported with it.

## Arms

| arm | work dir | what varies | held fixed | verified how |
|---|---|---|---|---|
| `nosamecur_s1..s3` | `detfit_ns1..ns3` | fit seed within config | config, tree `be09a8503`, image | guard + `VILLA_SHA` + `RENDER_IMAGE` |
| `anchor10cov_*` | `detfit_an1..an3` | fit seed within config | as above | as above |

Pooled with the existing `detfit_s4..s9`. **No new fits.** One pinned `VILLA_REF` and one
`RENDER_IMAGE` across all twelve.

## Predictions, fixed now

1. **Pooled fit-only CV in [0.040, 0.075].** Reasoning: `curbase`'s 0.0909 and the two quieter
   groups' stock CVs bracket it, and pooling pulls toward the majority. My last three magnitude
   predictions missed, so this is recorded expecting to be wrong about the value while right about
   the ordering.
2. **`curbase` remains the noisiest of the three** after deterministic re-rendering. Its stock lead
   is 2–6×, and its outlier is a genuine fit outlier (established: `s6` survived re-flattening).
3. **No prediction on whether the difference is significant.** With df=2 per comparison group,
   F-tests establish nothing — that was measured today (p=0.057, 0.518). The pooled figure is the
   deliverable, not a ranking.

## Decision rule

| pooled fit-only CV (df=11) | conclusion |
|---|---|
| **< 0.055** | `curbase` was unrepresentative. The tier floor is better than 20%; quote the pooled figure for current-tier designs. |
| 0.055–0.075 | The tier sits between the quiet groups and `curbase`. Quote the pooled figure; `curbase`-based designs were conservative. |
| **> 0.075** | `curbase` was representative. ~20% at 3v3 stands as the current-tier floor and fit comparisons are expensive, full stop. |

**Failure branch:** if any arm's guard fails, or the twelve do not share one `VILLA_SHA` and
`RENDER_IMAGE`, the pooled figure is not computed — a floor pooled across instruments is not a floor.

## What the result cannot do — computed before it arrives

**It cannot reopen a published null.** At 3v3 even the most favourable band here (CV 0.040) gives an
MDE of **9.2%**, and the largest observed null effect in the corpus is 5.49%. Recomputed rather than
assumed from the earlier study, because that one's bands were different.

**It cannot decompose fit RNG further.** Three configs give a pooled floor, not an attribution.

## Limits

Twelve fits, three configs, one tree, one ROI, one scorer. df=11 still spans 2.4×. Nothing about the
pinned tier. Per-arm wall time 80–160 min, spread entirely in the S3-fetch bands.

## Cost

Six arms, strictly serial (~24 GB per render): **~14 h**. No fits, no new data.
