# Pre-registration: is there a free offset that inflates the objective without improving the fit?

**Written 2026-09-22, before any arm of this study is built or rendered.** Written from
`docs/preregistration/TEMPLATE.md`.

## The question

`reports/displacing_the_surface_costs_ink_in_both_directions.md` displaced one flattened surface and
found ink falls **both** ways — **−19.77%** at −4 vx, **−4.48%** at +4 vx — so the fitted surface sits
near a local maximum. But the two losses differ by **4.41×**, which is not what a maximum *at* the
fitted surface would give.

If the peak is not at zero, then **rendering at a fixed offset buys objective points with no change
to the fit at all.** That is the duplicate-coverage problem in a new form: a way to move
`total_fg_pixels` that has nothing to do with fitting the scroll better. villa's loop optimises that
number, so whether the lever exists is worth knowing regardless of which way it comes out.

**This is a question about the objective, not about reading.** `total_fg_pixels` is an area count and
the scorer reads texture, not brightness (`reports/the_scorer_reads_texture_not_brightness.md`), so a
positive result means "the metric can be moved", **not** "more text is legible".

## The prediction, derived now from the two measured arms

Assume the response is locally quadratic about an optimum `x0`: `loss(x) ∝ (x − x0)²`. Then

```
sqrt(loss(−4)/loss(+4)) = sqrt(0.19768/0.04482) = 2.100
x0 = 4·(2.100 − 1)/(2.100 + 1) = +1.42 vx
```

**Prediction 1: the ink maximum lies at +1.4 ± 1 vx, i.e. OUTWARD of the fitted surface.**
**Prediction 2: the gain at that maximum is ~1.4% over the fitted surface** (same model:
`k·x0² = 1.36%`).

**What kind of prediction this is, stated plainly:** two points determine one parameter exactly, so
this is a **point prediction with no error bar from the data**, and the quadratic form is an
**assumption**, not a fit. Over ±4 vx it is almost certainly wrong in detail. It is registered
because it is falsifiable and because deriving it *after* seeing the sweep would be worthless.

**Prediction 3 withheld:** whether the optimum is stable across fits. One surface cannot say.

## Reachability — checked before designing the validation

The manipulation is proven: `scripts/build_radial_displacement_arm.py --single` produced −4 and +4
copies whose achieved shift matched the request to 0.000 vx, `z.tif` byte-identical, valid-point
counts unchanged, and villa's `load_tifxyz` accepted both. `RENDER_REUSE_FLATTEN=1` renders them
without re-flattening.

## The floor — measured, not inherited

**F = 0.0014%** (24 px), measured on this exact path: two renders of one byte-identical flat surface
with the flatten held fixed (`reports/holding_the_flatten_fixed_collapses_the_floor.md`). The
predicted 1.4% effect is **~970× the floor**, so single arms are interpretable — the condition the
first displacement design failed.

## Arms

One flat surface (`radial_work_rad0`'s `w120-129_flat`), displaced by `--single`, all written by one
tool, all rendered with `FLATTEN_DETERMINISTIC=1` unnecessary (no flatten runs) and
`RENDER_REUSE_FLATTEN=1` required.

| offset | work dir | status |
|---:|---|---|
| −4 vx | `flat_study_in` | **already scored** 1,363,076 |
| −2 vx | `offset_m2` | to build |
| 0 vx | `flat_study_zero` | **already scored** 1,698,914 |
| +1 vx | `offset_p1` | to build |
| +2 vx | `offset_p2` | to build |
| +3 vx | `offset_p3` | to build |
| +4 vx | `flat_study_out` | **already scored** 1,622,775 |

Seven points, **four new renders**. All seven must share one `VILLA_SHA` and one `RENDER_IMAGE`.

## Decision rule

Fit a parabola to all seven points; report the vertex `x̂0` and the gain at it.

| outcome | conclusion |
|---|---|
| \|x̂0\| ≤ 1 vx **and** gain < 3F | **No free lever.** The fit lands on the ink maximum; villa's objective cannot be moved by a global offset. A clean validation of the fitting. |
| x̂0 in [+0.4, +2.4] and gain ≥ 3F | **Prediction 1 MET, lever exists.** Report the offset and the gain, and flag it as an objective-gaming route in the duplicate-coverage class. |
| \|x̂0\| > 1 but outside the predicted band | **Lever exists, prediction missed.** Report both. |
| the parabola fits badly (R² < 0.8) | **The quadratic assumption is refused by the data.** Report the sweep as a curve and make no vertex claim — this is the branch where my model, not the hypothesis, is what the data speak to. |

## What the result cannot do — computed before it arrives

**It cannot show more text is readable.** A gain in `total_fg_pixels` at an offset is a metric
movement; the scorer reads texture and this study has no legibility endpoint.

**It cannot reopen a published null.** Those are fit comparisons at a ~20% floor; this is a
fixed-surface study at 0.0014%. Different instruments, no bearing.

**It cannot generalise across fits.** One surface, one ROI. An offset optimal here need not be
optimal for another fit — and if it is not, the "free lever" reading weakens accordingly.

## Limits

One surface, one ROI (`w120-w129`), one scorer, one point per offset. The ±4 arms already establish
that per-voxel sensitivity is **not** constant, so the parabola is a local convenience, not a law.
Per-voxel ratios have failed to extrapolate three times in this project.

## Cost

Four renders at ~2 h, serial (~24 GB each), no flatten and no fits: **~8-9 h.** Must not overlap the
pooled-floor chain.
