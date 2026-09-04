# The bootstrap arm is thinnest exactly where the ink is scored

**2026-09-04, written while arms 3-6 were still fitting, with every endpoint unread.** This is an
input-side property of the datasets. `scripts/check_patch_spatial_balance.py`, tests in
`tests/test_check_patch_spatial_balance.py`.

## Why this was worth measuring

`reports/patch_bootstrap_selection_verified.md` establishes that the arms hold the same total patch
area, 76.36% vs 76.37%. That is a **global** match. The ink endpoint is not global: `total_fg_pixels`
is scored only on **w120-w129**, the outer strip.

A global match can therefore hide the very confound the RANDOM control exists to remove.

## The instrument, and the version of it that was wrong

Patch records carry no winding, and `abs_winding.json` is correction anchors rather than a
patch->winding map, so this uses a radial proxy from each patch's `meta.json` bbox.

**The first version assigned each patch to the band containing its centroid, and that measurement was
invalid.** The median patch spans **602 vx** radially against a median band width of **149 vx**; 37.9%
of patches exceed 1,000 vx across their XY diagonal. A patch four times wider than a band cannot be
located by its midpoint. The corrected version spreads each patch's area across the whole radial
interval its footprint covers.

The pattern below **survived that correction** -- the largest band gap moved from 4.63 to 3.59 points
and the monotone shape held. Reported because a finding that changes under a fixed instrument should
not be trusted, and this one did not.

## The measurement

| band | radius <= | BOOT area% | RAND area% | gap (pts) |
|---:|---:|---:|---:|---:|
| 0 | 834 | 18.68 | 15.09 | **+3.59** |
| 1 | 981 | 6.31 | 5.49 | +0.83 |
| 2 | 1,174 | 9.77 | 8.91 | +0.86 |
| 3 | 1,388 | 12.14 | 11.75 | +0.39 |
| 4 | 1,529 | 8.19 | 8.38 | -0.19 |
| 5 | 1,677 | 8.16 | 8.70 | -0.55 |
| 6 | 1,827 | 7.75 | 8.56 | -0.81 |
| 7 | 1,967 | 6.62 | 7.40 | -0.78 |
| 8 | 2,229 | 10.11 | 11.51 | -1.40 |
| 9 | outermost | 12.26 | 14.21 | **-1.95** |

Monotone in sign: BOOTSTRAP is inner-heavy and outer-light. Mean midpoint radius 1,571 vs 1,655.

**Correction, made the same day against the winding meshes.** This section first read "the outermost
band -- the region w120-w129 is scored on". That identification is wrong. Calibrating radius against
the fitted meshes (`scripts/calibrate_radius_to_winding.py`) shows the scored strip spans radius
**1,593 to 3,311** (p5 to p95, median 2,532), while band 9 is everything beyond 2,229 -- a *subset*
of the scored region, not the same thing. A single winding sweeps a median of 1,683 vx of radius,
because the spiral is not a circle, so **radius orders windings but cannot identify one**.

What survives the correction is the number, because the deficit does not depend on the cut:

| definition of the scored region | BOOT | RAND | relative |
|---|---:|---:|---:|
| strip p5-p95, radius 1,593-3,311 | 41.20% | 46.39% | **-11.2%** |
| strip median outward, radius > 2,532 | 5.05% | 5.97% | -15.4% |
| band 9 as originally quoted, radius > 2,229 | 12.26% | 14.21% | -13.7% |

The originally published -13.7% sits inside the range rather than at its edge, so it was not a
favourable cut, but **-11.2% over the strip's actual radial support is the figure to quote**.

The calibration also validates the proxy's direction: median radius rises without exception from w010
(882) to w129 (2,576) across thirteen sampled windings. Had it not, the band table above would have
had to be withdrawn rather than corrected.

## The mechanism, measured rather than assumed

Satisfaction falls with radius across the full population:

| radial decile | median radius | mean satisfied fraction |
|---:|---:|---:|
| 0 | 676 | 0.9421 |
| 3 | 1,396 | 0.8366 |
| 6 | 1,896 | 0.8086 |
| 9 | 2,613 | **0.7198** |

**Pearson r(radius, satisfied fraction) = -0.21** over 35,963 patches. Outer patches are harder to
reconcile, so a 0.90 threshold removes them preferentially. The spatial skew is not an accident of
this build; it is what selecting on satisfaction *does*.

## The control is not the thing that is skewed

The obvious objection to the table above is that RANDOM, a single draw, might itself be the
unrepresentative one. It is not. Against the full 38,439-patch population on the same band edges:

| | largest band gap |
|---|---:|
| RANDOM vs FULL population | **0.26 points** |
| BOOTSTRAP vs RANDOM | 3.59 points |

Seven of ten bands agree to within 0.12 points. The draw tracks the population it came from, so
BOOTSTRAP vs RANDOM is close to BOOTSTRAP vs everything, and the skew belongs to the selection rather
than to the control.

This measures the dimension `patch_bootstrap_selection_verified.md` explicitly left open, having
discharged only the quality dimension. Provenance and winding proper remain unmeasured; the radial
proxy is not a winding number.

## What this means for the verdict, stated before the verdict exists

1. **The registered decision rule is unaffected.** Outer thinning is a property of the method under
   test, not an error in the experiment. If ink does not rise, the method has not worked, and
   `scripts/analyse_patch_bootstrap.py` will say so regardless of mechanism.
2. **The mechanism behind any ink deficit would be ambiguous.** RANDOM matches BOOTSTRAP on global
   area but not on area *within the scored strip*, so a BOOTSTRAP ink loss could be worse selection
   OR simply less evidence where the measurement happens. This report cannot separate them, and
   neither will the verdict.
3. **The clean design is a control matched inside the scored region**, not globally. That was not
   pre-registered and will not be retrofitted onto this study; it is the honest follow-up if the
   result turns on this point.

Recorded now precisely so that it cannot be produced later as an explanation for an unwelcome
number. The endpoints remain unread: arms 3-6 are still fitting, and the decision rule -- including
that a geometry-only gain is a FAILURE rather than a partial success -- was committed to code before
any arm produced a value.
