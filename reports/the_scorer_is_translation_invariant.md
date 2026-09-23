# The scorer is translation-invariant: moving a strip on its canvas changes nothing

**2026-09-23.** The result of `docs/preregistration/2026-09-22_scorer_translation.md`, decided by
`scripts/analyse_scorer_translation.py` (written before any arm existed). Data:
`reports/scorer_translation.json`. Ten scoring-only arms of `radial_work_rad0`'s strip, decoded exactly
as the scorer decodes it, padded with black by (dy, dx), and saved as lossless PNG (every source pixel
re-read and verified).

## The result

| arm | dx | dy | `total_fg_pixels` | vs unshifted | per-block sd vs `stx_d0a` |
|---|---:|---:|---:|---:|---:|
| `stx_d0a` | 0 | 0 | 1,698,796 | −0.0006% | — |
| `stx_d0b` | 0 | 0 | 1,698,815 | +0.0006% | 0.00015 |
| `stx_x1` | 1 | 0 | 1,698,809 | +0.0002% | 0.00012 |
| `stx_x2` | 2 | 0 | 1,698,842 | +0.0021% | 0.00012 |
| `stx_x8` | 8 | 0 | 1,698,814 | +0.0005% | 0.00013 |
| `stx_x64` | 64 | 0 | 1,698,828 | +0.0013% | 0.00013 |
| `stx_x512` | 512 | 0 | 1,698,813 | +0.0004% | 0.00017 |
| `stx_y1` | 0 | 1 | 1,698,787 | −0.0011% | 0.00010 |
| `stx_y8` | 0 | 8 | 1,698,811 | +0.0003% | 0.00020 |
| `stx_y64` | 0 | 64 | 1,698,833 | +0.0016% | 0.00012 |

* **Spread over all ten arms: 0.0032%**, under 3 × the floor (0.0042%). **Verdict: INSENSITIVE.**
* **Per 2 kpx block, every shifted arm matches the unshifted one to 0.0001–0.0002**, against **0.135**
  between two layouts of the same surface (`reports/the_flatten_noise_is_local_rescoring.md`).
* Pipeline check: the PNG copy scores −0.0015% against the source's JPEG score (1,698,831), so the
  lossless re-encoding moved nothing.

## Both predictions missed

* **Registered:** "SENSITIVE, SMALL" (between 3F and 1%). **Missed.**
* **Dated revision, made before any arm existed:** "LAYOUT-SENSITIVE (≥ 1%)", on the grounds that a
  shift might re-draw the 0.135 block rescoring. **Missed**, and this is the more informative miss.
  Even a 512 px shift, half a tile stride and the most the tile grid can move relative to the
  content, leaves every block unchanged.

## What this settles, and what it leaves

**Tile placement is not the mechanism.** A rigid shift of identical pixels, across the whole range of
grid-to-content alignments, changes neither the total nor any block. The scorer's sliding window
(768 × 2048 patch, 50% overlap, Gaussian blending, mirroring TTA) is effectively translation-invariant
at this scale.

**So the ±13% per-block rescoring between two flattens of the same surface comes from the strip's
content changing**, not from where the content sits. A re-parametrisation does two things this test
cannot separate:

1. **local distortion:** the sheet is stretched or sheared differently in strip coordinates, so the
   texture the scorer reads has a different local scale and shape;
2. **re-sampling:** each strip pixel samples the ink-prediction volume at a different point, so
   interpolation changes the pixel values themselves.

The registered verdict text names only (1). Both remain candidates.

## Implications

* **Scoring is stable to presentation:** padding, cropping offsets and canvas-size differences do not
  perturb villa's objective.
* **Layout noise lives upstream of the scorer**, in how the flatten maps the volume onto the strip.
  A test that holds the layout fixed and perturbs only the sampling (for example, sub-voxel
  interpolation changes) would separate (1) from (2). Not done here.

## Limits

One strip, one region, one model. Shifts up to 512 px along and 64 px across the strip.
