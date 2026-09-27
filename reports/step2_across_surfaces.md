# The post-#1146 slice step raises `total_fg_pixels` by +5.0% to +9.2% across four surfaces

**2026-09-27.** Result of `docs/preregistration/2026-09-27_step2_across_surfaces.md`, summarised by
`scripts/analyse_step2_surfaces.py` (committed at `8a085633` before any arm rendered). Data:
`reports/step2_across_surfaces.json`.

## Result

Same saved flat surface per row, same pinned Python stage, image and scorer. Only the slice step
differs: the published image at step 1 (its default) versus step 2, which reproduces a post-#1146
villa build to rounding (finding 65).

| surface | step 1 (published) | step 2 (= post-#1146) | effect |
|---|---:|---:|---:|
| up1 | 3,279,498 | 3,453,819 (source build) | **+5.32%** |
| s4 | 3,164,499 | 3,368,620 | **+6.45%** |
| s5 | 2,963,832 | 3,236,196 | **+9.19%** |
| s6 | 3,583,420 | 3,761,359 | **+4.97%** |
| **mean** | | | **+6.48%**, range [+4.97%, +9.19%] |

* Every effect is positive and clears 10× the re-score floor (59 px on 3.28 M).
* All three new arms really sampled (no `all slices exist` in any log).
* Each flat was byte-checked against its source dir before rendering.

**The prediction was "all positive, 2–10%", with moderate confidence on the sign and low on the
size.** It held.

## What it means

* **The install-route effect is as large as the fit-to-fit noise.** The pooled fit-only CV is 0.074.
  A villa autoresearch run scored with a current source build against a baseline scored with the
  published image (or the reverse) would see a spurious **~5–9%** change. That is the size of the
  gains the loop chases, and larger than the ±3% bound our same-winding null achieved.
* **It is not a constant.** It spans 4.2 points across four surfaces from the same region and code, so
  no single correction factor would reconcile the routes. Only rendering both sides with one build does.
* **Not over-read:** with n = 4, the apparent pattern (the lowest-ink surface gains most, the highest
  least) is noted and nothing more.

## Limits

* One region, one ink volume and one scorer; four surfaces, three of them seeds of one config.
* The step-2 arms are the published binary at `--slice-step 2`, verified equal to a post-#1146 build
  only on `up1` (to rounding). It is assumed, not re-verified, on the other three.

## Outward

Nothing further posted. The reply on villa #1588 already states the mechanism and its single-surface
size, with the caveat that it "will vary with how much ink sits just off the surface". Adding to that
thread is against this project's no-nudge rule.
