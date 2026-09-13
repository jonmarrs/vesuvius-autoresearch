# Cutting 80% of the winding anchors did not change reading — but the measurement is weak

**2026-09-13.** Registered in `docs/preregistration/2026-09-12_anchor_ablation.md`, analysed by
`scripts/analyse_anchor_ablation.py` as committed before any arm was fitted. Gate:
`reports/anchor_gate_verdict.md`. Machine-readable: `reports/anchor_ablation_verdict.json`.

## Result

| arm | `satisfied_area` | `total_fg_pixels` |
|---|---:|---:|
| `anchor10cov_pilot` | 0.8590 | 2,898,843 |
| `anchor10cov_s2` | 0.8598 | **2,722,693** |
| `anchor10cov_s3` | 0.8634 | 2,951,176 |
| `curbase_s1` | 0.8472 | 2,904,520 |
| `curbase_s2` | 0.8494 | 2,901,177 |
| `curbase_s3` | 0.8503 | 2,841,071 |

| endpoint | BASELINE | ABLATED | rel | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 2,882,256 | 2,857,571 | −0.86% | 0.7603 |
| `satisfied_area_fraction` | 0.8490 | 0.8607 | +1.39% | **0.0032** |

**VERDICT: NULL on reading.** All three ablated arms passed the winding-identity gate (10/10 offsets
at zero) and the non-blank control (46.9%, 48.0%, 47.3%). No arm was excluded.

## The ink null is much weaker than the design promised

The registration budgeted for a **2.9%** minimum detectable effect, using the current tier's seed CV
of 0.0125. The data exclude only:

> **−0.86%, 95% CI [−10.21%, +8.50%]** (Welch df = 2.4)

**Because the ablated arm is far noisier than the baselines**: CV **0.0419** against **0.0124**, a
factor of 3.4, driven by `anchor10cov_s2` sitting 6.9% below the other two ablated fits. That arm
passed every registered validity check, so there is no basis for excluding it.

At n=3 per arm the variance difference is **not statistically established** (F(2,2) = 11.4,
p = 0.161) — with two degrees of freedom on each side, almost nothing would be. But it does not need
to be established to widen the interval: the Welch df collapses to 2.4 and the bound follows.

**So the honest claim is "no reading effect larger than about 10%", not the ~3% the design promised.**
The power calculation assumed the manipulation would not change the variance. It appears to, and a
future anchor study should budget from the *ablated* arm's spread, not the baselines'.

## The geometry result is confounded — by my own registration

`satisfied_area` rises 1.39% at p = 0.0032. The registration argued this was interpretable here,
unlike the same-winding study, because that manipulation removed 5,413 of the patches the metric
scores while this one leaves the patch set identical at 38,442.

**That reasoning removed one confound and missed another.** `fit_spiral.py:4345` adds `abs_winding` as
a loss term at weight 5.0, in its own `backward_family`, alongside the patch-fitting losses. The
anchors are a **competing objective**. Removing 40 of 50 of them reduces the pull away from the
patch-optimal solution, so the optimiser satisfies patches better.

**A rise in patch satisfaction when you delete a competing constraint is mechanically expected, and
is not evidence that the geometry improved.** It is the same shape of error as "less left to
satisfy", arrived at by a different route, and I did not see it until after the data were in.

**This is therefore NOT a fifth instance of the geometry/ink decoupling**, and must not be reported
as one. The correct statement is narrower: removing the anchors improves the metric that scores the
constraint they compete with, and does not measurably change reading.

## What villa can take from this

* **Ten anchors read as well as fifty, within ±10%.** villa asks people to draw absolute winding
  annotations by hand and calls automating them the fastest path to scale. On this ROI, at this
  power, cutting 80% of them costs nothing detectable in recovered ink.
* **That bound is wide.** A real 5% loss would have been invisible here. This does not license
  dropping anchors; it says the effect is not large.
* **The companion measurement is tighter.** Removing 5,413 *same-winding* constraints gave
  +0.28%, CI [−2.56%, +3.13%] — because that manipulation did not inflate the variance.

## Registered prediction

**None was registered, on either endpoint** — deliberately, after two consecutive wrong
`satisfied_area` direction calls pointing opposite ways. That decision looks better in hindsight than
it felt: I would have predicted geometry to fall, and it rose for a reason that has nothing to do
with geometry quality.

## Validity

* all three ablated arms at 10/10 winding-identity offsets against `curbase_s1`, both directions;
* non-blank control passed by every arm;
* manipulation verified anchors-only in the fit logs: absolute winding 59 → 10 points, relative
  (2,173), same-winding (5,413) and post-filter patches (38,442) identical;
* all six arms fitted and rendered from one unchanging tree (`spiral-fitting` `be09a8503`, `lasagna`
  and `vesuvius` `d8c5f488a`), written 2026-09-07 and unmodified since;
* arm 3's first render was OOM-killed and retried automatically; the retry completed `rc=0` and its
  output passes the same controls.
