# Pre-registration: does the scorer alone amplify a half-pixel re-sample?

**Written 2026-09-24 ~02:40, before the arm was built or scored.** Written from
`docs/preregistration/TEMPLATE.md`. Builder `scripts/build_subpixel_image_arm.py`, decision code
`scripts/analyse_scorer_subpixel.py`, tests `tests/test_scorer_subpixel.py`, all committed with this
file.

## The question

`reports/re_sampling_is_enough.md` found that re-sampling the 0 vx surface half a strip pixel (`rs_t005`,
rendered, layout fixed) re-draws **0.088** per 2 kpx block against `flat_study_zero`, while moving
identical pixels re-draws **0.0001** (`reports/the_scorer_is_translation_invariant.md`). What that did
not settle: **is the sensitivity in the render or in the scorer?** Either the rendered pixels change a
lot, or they change a little and the scorer turns small changes into block-level ink.

This separates them **without a render**: take `flat_study_zero`'s own strip, interpolate it half a
pixel along x as an image, and score it.

## The manipulation

`half_pixel_shift_x`: each pixel becomes the rounded mean of itself and its right neighbour, the value
at x + 0.5 by linear interpolation. Same canvas, lossless PNG, re-read and verified. The last column is
kept. Tests pin: a constant image is unchanged; a ramp moves by exactly half a pixel.

**Known small confound, stated now:** round-half-up brightens by ~+0.25 grey levels on average. The
scorer reads texture, not brightness (`reports/the_scorer_reads_texture_not_brightness.md`), so this
is expected to be negligible. It is not corrected.

## Reference and floor

* **Rendered half-pixel re-sample:** 0.0882 per-block sd.
* **Floor:** whole-pixel moves of identical pixels, 0.0001–0.0002.

## Decision rule (per-block sd at 2048 px, `sp_half` vs `flat_study_zero`, same canvas, no offset)

| sd | verdict |
|---|---|
| ≥ 0.06 (two-thirds of the rendered 0.088) | **SCORER AMPLIFIES.** Sub-pixel image changes alone are turned into block-level ink. |
| ≤ 0.02 | **RENDER-SIDE.** The rendered effect comes from how the volume is sampled. |
| otherwise | **BOTH.** |

**Descriptive, not in the verdict:** pixel-level change (mean |Δ|, p90, correlation over covered
pixels) for this arm and for the rendered `rs_t005` (aligned by its 10 px trim) against the
reference. It shows whether the render changed pixels more or less than a plain half-pixel
interpolation does.

## Prediction, fixed now

**SCORER AMPLIFIES (≥ 0.06), confidence low.** The render samples a volume that is coarse relative to
a strip pixel, so its half-pixel re-sample should look much like image interpolation, and the scorer
already proved hypersensitive to it. My last four predictions on scorer and render sensitivity all
missed, so this is recorded to be checked, not trusted.

## What the result cannot do

* **It cannot say which pixels matter or why** a fixed-threshold scorer is this sensitive.
* **An image interpolation is not the render's re-sample.** A verdict of SCORER AMPLIFIES means the
  scorer *suffices* to produce the effect, not that the render contributes nothing.
* **One strip, one region, one model.**

## Cost

One scoring run (~20–30 min), no render. Runs now: the box is idle.
