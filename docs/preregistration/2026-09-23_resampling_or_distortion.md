# Pre-registration: is the flatten's per-block rescoring re-sampling, or does it need distortion?

**Written 2026-09-23 ~16:00, before either arm was built for rendering or rendered.** Written from
`docs/preregistration/TEMPLATE.md`. Builder `scripts/build_inplane_resampled_arm.py`, decision code
`scripts/analyse_resampling_or_distortion.py`, tests in `tests/`, all committed with this file.

## The question

Two stock flattens of one surface (`rad0`, `rad0b`) lie on the same sheet (0.25 vx along the normal)
and cover the same strip area. Yet the scorer re-reads them by **0.135** (ink-weighted sd per 2048-px
block), which nets to ±3% on the total (`reports/the_flatten_noise_is_local_rescoring.md`). A rigid
translation of one strip re-reads by only **0.0001**
(`reports/the_scorer_is_translation_invariant.md`). What remains are two things a re-parametrisation
does:

1. **distortion:** the layout stretches or shears the sheet differently in strip coordinates;
2. **re-sampling:** every strip pixel samples the ink-prediction volume at a different point.

This separates them by re-sampling **without** re-laying out.

## The manipulation, and why it is clean — checked before registering

`build_inplane_resampled_arm.py` moves every grid point of the 0 vx surface (`flat_study_zero`) a
fraction `t` of a cell **along the sheet** (the strip axis), by Catmull-Rom interpolation. It is the
same grid shape and the same layout geometry. The render uses **10 strip pixels per 20 vx cell**, so:

| arm | t (cell) | moves every sample by | what it tests |
|---|---:|---:|---|
| **`rs_t005` (primary)** | 0.05 | **1.0 vx = 0.50 strip px** | pure re-sampling: every sample falls halfway between the original ones |
| `rs_t05` (secondary) | 0.5 | 10.0 vx = 5.00 strip px | a whole-pixel translation (known not to matter) plus the re-interpolated surface |

Measured on the real surface before registering:

* **The geometry barely changes.** The correction Catmull-Rom applies relative to the straight chord
  is **0.024 vx** at the median (p90 0.098) for t = 0.05, and 0.106 vx for t = 0.5. The round trip
  (two half-cell steps against a one-column shift) errs by 0.13 vx at the median.
* **Valid cells:** 2,551,170 of 2,564,050. The border columns without a full stencil are dropped, a 0.5%
  loss at the strip ends.
* **A trap, avoided:** a half-cell move (t = 0.5) lands every sample exactly 5 px on, on the
  original sample positions, so it barely re-samples anything. That is why the primary arm is t =
  0.05 and not the "obvious" half cell.

The builder's tests pin: zero shift = identity; a straight line reproduced exactly; points stay on a
curved sheet to < 0.01 vx; an invalid neighbour invalidates the cell.

## Floor and reference

* **Floor:** per-block sd between identical content = scorer repeat, **0.0001–0.0002** (translation study).
* **Reference:** per-block sd between two flattens of the same surface, **0.135**.

## Decision rule (primary arm, per-block sd at 2048 px against `flat_study_zero`)

| sd | verdict |
|---|---|
| ≥ 0.07 (half the reference) | **RE-SAMPLING SUFFICES.** No distortion is needed to explain the flatten's rescoring. |
| ≤ 0.02 | **DISTORTION REQUIRED.** Re-sampling alone re-draws little. |
| otherwise | **BOTH CONTRIBUTE.** |

The secondary arm is **descriptive**. It asks whether the re-interpolated surface alone (translation
aside) re-draws blocks.

**Failure branch:** VOID if the arms do not share one `VILLA_SHA`. An arm whose reuse-flatten line does
not name its own work dir is killed by the runner (the fallback silently re-flattens).

## Prediction, fixed now

**BOTH CONTRIBUTE (sd in 0.02–0.07), confidence low.** The ink volume is smooth relative to one strip
pixel, which argues for small re-sampling effects. But a fixed-threshold scorer can flip boundary
pixels on small value changes, and it re-read a 0.25 vx difference at 0.135. My two predictions on the
scorer this week both missed, so I am not confident either way.

## Amendment, 2026-09-23 — made before any arm's score, mask or strip was read

**Timing, stated exactly.** The problem was found ~17:00 from the primary arm's render log (its trim
line) while it was still rendering. The fix was written and installed ~18:00–19:00, which is
**after** the primary arm was scored (17:37). No arm's `metrics.json`, mask or strip had been opened.
The checks below used only the reference arm's (`flat_study_zero`) masks, and the registered analysis
had not run.

**The decision code compared columns without aligning them.** The re-sampled surfaces lose their
border columns (the Catmull-Rom stencil needs neighbours), and the render trims to the valid region.
The primary arm's log shows `rect c=1+8263 r=0+424`: its strip starts **one cell (10 px) later** than
the reference's and has 20 fewer rows at the bottom. On the reference's own masks, a pure 10 px
misalignment fakes a per-block sd of **0.0133**, two-thirds of the 0.02 boundary. That bias favours
"re-sampling", so left in it could have manufactured the verdict.

**Fix:** read each arm's trim (`c`, `r`) from its render log, sum the reference's columns over the rows
both strips share, and compare arm column k with reference column k + 10c + round(10t): 10 px for the
primary arm, 15 for the secondary. The half pixel of the primary arm is the manipulation and is
deliberately not aligned away. The verdict uses the aligned sd; the unaligned sd is still reported.
Checked on real data before adding it: the reference's own masks, trimmed by 10 px, read **0.0
aligned vs 0.0133 unaligned**. Pinned by two new tests (trim parsing; a pure offset reads 0 aligned and
> 0.005 unaligned on run-structured ink). Bands and prediction unchanged.

## What the result cannot do

* **It cannot identify which distortion**, if DISTORTION REQUIRED. It only rules re-sampling in or out.
* **It says nothing about reading.** `total_fg_pixels` is a metric, not legibility.
* **One surface, one region, one render configuration.**

## Cost

Two renders with the flatten reused (~2 h each, ~24 GB, serial) plus scoring. Runs now: the box is
idle (27 GB free, no containers).
