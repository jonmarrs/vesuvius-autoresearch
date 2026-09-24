# Re-sampling is enough: half a pixel re-draws two-thirds of the flatten's rescoring

**2026-09-23 (run finished 19:39).** The result of
`docs/preregistration/2026-09-23_resampling_or_distortion.md`, decided by
`scripts/analyse_resampling_or_distortion.py` **as amended before any arm's result was read** (the
alignment amendment, committed 19:01; the run used it, as its "ALIGNED" output shows). Data:
`reports/resampling_or_distortion.json`.

## The result

| arm | what changed | per-block sd, aligned (unaligned) | ink vs 0 vx |
|---|---|---:|---:|
| **`rs_t005` (primary)** | every sample moved **half a strip pixel** along the sheet, same layout | **0.0882** (0.0902) | +1.93% |
| `rs_t05` (secondary) | 5 px translation + the re-interpolated surface | **0.1067** (0.1090) | +1.91% |
| reference: two flattens of one surface | | 0.135 | +3.04% |
| translation only (`reports/the_scorer_is_translation_invariant.md`) | | 0.0001 | 0.0032% |

**Verdict: RE-SAMPLING SUFFICES** (primary 0.0882 ≥ 0.07). Moving every sample half a pixel, with the
layout geometrically fixed, re-draws **about two-thirds** of the per-block rescoring between two
flattens of the same surface. **No distortion is needed to explain it.**

**The prediction missed.** I predicted BOTH CONTRIBUTE (0.02–0.07, low confidence), reasoning that the
ink volume is smooth relative to a strip pixel. It is not smooth enough, or the scorer's fixed
threshold amplifies small value changes, or both. This does not say which.

## What the pieces now say together

| manipulation | per-block rescoring |
|---|---:|
| identical pixels, moved on the canvas | 0.0001 |
| same layout, samples moved ½ px | **0.088** |
| same surface, re-laid-out by a second flatten | 0.135 |

**The scorer is insensitive to where identical pixels sit, and highly sensitive to where the ink volume
was sampled.** Any change in the sampling points (a re-flatten, a fit change, a different render grid)
re-draws `total_fg_pixels` locally by ~9–13% per 2 kpx block and ~±2–3% on the strip, whatever
happens to the reading.

## The alignment amendment was right, and small here

Aligned 0.0882 against unaligned 0.0902. The measured misalignment artefact (0.013) adds roughly in
quadrature: √(0.088² + 0.013²) ≈ 0.089. It did not decide this verdict, but at a smaller effect it
would have.

## Not explained

* **Why the secondary arm (0.107) re-draws more than the primary.** By construction its samples land
  about 5 px on, roughly on the original sample positions, so I expected it to re-sample *less*. Either
  its re-interpolated surface (a Catmull-Rom correction of 0.106 vx p50 against 0.024 for the primary)
  matters, or the renderer does not sample exactly at 10 px per cell. **Not investigated.**

  **Sharpened 2026-09-24 (exploratory, not registered).** The renderer does sample at 10 px per cell
  (`render_scale=0.5` over a 0.05 grid scale). And by every pixel measure the half-cell arm changed
  **less** than the half-pixel arm, yet re-drew **more**
  (`scripts/describe_rendered_pixel_change.py`, `reports/resampling_or_distortion_pixel_change.json`):

  | arm | mean \|Δ\| | \|Δ\| ≥ 50 | r | per-block rescoring |
  |---|---:|---:|---:|---:|
  | `rs_t005` (½ px) | 12.9 | 7.8% | 0.947 | 0.088 |
  | `rs_t05` (½ cell) | 5.6 | 2.3% | 0.979 | 0.107 |
  | image ½-px shift, no render (`reports/scorer_and_render_both_amplify.md`) | — | — | 0.970 | 0.030 |

  Neither arm is brighter or darker (signed means −0.70 and −0.73, medians 0). **So the scorer's
  block-level rescoring is not predicted by how much the pixels change.** A genuine re-render that
  barely changes the pixels re-draws as much as one that changes them a lot, and far more than an
  image edit of similar size. That points at the *structure* of render changes rather than their
  magnitude. **Untested.** The render also samples 5 slices along each normal, and normals recomputed
  from a re-sampled grid move those slices even where the surface points coincide. That is one
  candidate, not a finding.
* **Whether the effect is in the render or the scorer.** Half-pixel re-sampling changes the strip's
  pixel values, and the scorer reads the change. This does not separate an amplifying scorer from a
  rough volume.

## Limits

One surface, one region, one render configuration, one magnitude of re-sampling. The primary arm also
carries a 0.024 vx (p50) geometric change from interpolation, which is small but not zero.
