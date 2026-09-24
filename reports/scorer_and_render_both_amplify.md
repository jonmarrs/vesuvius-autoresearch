# The scorer amplifies sub-pixel change, and the render's re-sample adds more

**2026-09-24.** The result of `docs/preregistration/2026-09-24_scorer_subpixel.md`, decided by
`scripts/analyse_scorer_subpixel.py` (written before the arm was built). Data:
`reports/scorer_subpixel.json`. One scoring-only arm: `flat_study_zero`'s own strip, interpolated half a
pixel along x as an image (no render), losslessly saved and scored.

## The result

| what changed | per-block rescoring (sd, 2 kpx) | pixels vs reference (covered): mean \|Δ\|, p90, r | ink |
|---|---:|---|---:|
| identical pixels moved (floor) | 0.0001 | identical | 0.003% |
| **image half-pixel shift, no render (`sp_half`)** | **0.030** | 11.1, 39, **0.970** | −0.53% |
| rendered half-pixel re-sample (`rs_t005`) | 0.088 | 12.9, 34, **0.947** | +1.93% |
| two flattens of one surface | 0.135 | — | +3.04% |

**Verdict: BOTH** (0.030 falls between 0.02 and 0.06). **The prediction (SCORER AMPLIFIES) missed**, the
fifth miss in a row on this line.

## What it says

* **The scorer by itself turns sub-pixel change into block-level ink.** A plain half-pixel interpolation
  of identical content re-draws 0.030 per block, about 300× the whole-pixel floor.
* **The render's re-sample changes the pixels more than interpolation does** (r 0.947 vs 0.970).
  Sampling the volume at new points brings in new detail rather than only blurring, and it produces
  about three times the rescoring. Both contribute, and the render's sampling carries the larger
  share.
* **The ink goes in opposite directions:** interpolation's blur lowers the count slightly (−0.5%), the
  rendered re-sample raises it (+1.9%). Neither direction says anything about legibility.

## The chain this week's studies established

1. Two flattens of identical meshes lie on the **same surface** and cover the **same area**, yet score
   ±3% apart, all of it density, as uncorrelated per-block rescoring.
2. Moving **identical** pixels changes nothing (translation-invariant).
3. Re-sampling the same layout by **half a pixel** reproduces two-thirds of the rescoring (no
   distortion needed).
4. Of that, the **scorer alone** accounts for about a third (0.030 of 0.088). The rest comes from what
   the render's re-sample does to the pixels.

**So `total_fg_pixels` carries a sampling term that no fit controls:** any change in where the
ink-prediction volume is sampled re-draws local ink by ~9–13% per 2 kpx block, amplified by a scorer
that reacts to sub-pixel pixel changes.

## Limits

One strip, one region, one model, one sub-pixel magnitude. Linear interpolation is one image
re-sample among many. Round-half-up adds ~+0.25 grey levels, as registered.
