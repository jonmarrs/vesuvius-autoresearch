# Float rounding moves the ink count by 107 pixels — my registered prediction missed by 3×

**2026-09-20.** The side-measurement registered in
`docs/preregistration/2026-09-20_radial_displacement_on_the_flat_surface.md` **before this number
existed**. Reported because a missed prediction is worth more than an unregistered null.

## The measurement

Three delta-0 renders of one flat surface, canvas identical across all three (352,131,600 px):

| arm | tifs | flatten | `total_fg_pixels` |
|---|---|---|---:|
| `radial_work_rad0` | villa's | its own | 1,698,831 |
| `flat_study_probe` | villa's | reused | 1,698,807 |
| `flat_study_zero` | **rebuilt** | reused | 1,698,914 |

| comparison | isolates | difference |
|---|---|---:|
| `probe` vs `rad0` | render + score | **0.0014%** (24 px) |
| `zero` vs `probe` | **the writer** | **0.0063%** (107 px) |

The rebuild differs from villa's tifs by at most **0.000244 vx** in `x,y` — float32 ULP — with `z`
byte-identical.

## The prediction, and the miss

**Registered: agree within ~0.002%.** Observed **0.0063%** — **3× the bound, 4.5× the render floor.**
Recorded as a **MISS**.

It did not reach the **0.01%** threshold I registered for "this would matter", so nothing is alarming
here. But the reasoning that produced the prediction was wrong, and that is the part worth keeping.

## Why the proportional reasoning failed

I scaled the inner flatten pair's 2.65 %/vx down to 0.000244 vx and got ~0.0007%. The implied
sensitivity is instead **25.8 %/vx**:

| source | displacement | ink | %/vx |
|---|---:|---:|---:|
| inner flatten pair | 0.535 vx | 1.42% | 2.65 |
| outer flatten pair | 7.151 vx | 3.04% | 0.43 |
| gap-expander fix | 3.96 vx | 10.35% | 2.61 |
| **writer ULP** | **0.000244 vx** | **0.0063%** | **25.82** |

**These are different mechanisms, not one curve.** A coherent shift moves the whole surface together;
ULP rounding is *independent jitter per point*, which flips which voxel each sample lands in near
threshold boundaries. A `%/vx` figure does not transfer between them.

**This is the third time today a per-voxel ratio has failed to extrapolate** — the first killed a
two-point "law" (`reports/the_flatten_lands_on_different_surfaces.md`), the second was the
region-dependence between 2.65 and 0.43, and this is the third. The ratio is not a property of the
pipeline and should stop being computed as if it were.

## What it changes

**It vindicates rebuilding the ZERO arm.** The registration originally used `probe` as ZERO, and I
replaced it with a writer-identical rebuild on the argument that the ULP difference was negligible —
16,000× smaller than the manipulation — while saying explicitly that it was being *removed rather
than argued away*. Had it stayed, IN and OUT would each carry a **107 px** writer artifact of unknown
sign. The decision was right, and it is now measured instead of assumed.

**It does not threaten the study.** 107 px is **1,600× smaller** than the ~170,000 px a 10% effect
would move, and IN/OUT/ZERO all share one writer, so no writer difference enters them at all. The
floor for the effect comparisons remains F = **0.0014%**.

## Limits

One pair per comparison, so both 24 px and 107 px are point estimates with no intervals. The
mechanism offered for the miss — incoherent jitter versus coherent displacement — is an explanation
consistent with the numbers, **not something this measurement tests**. Distinguishing it would need a
deliberately jittered surface at a controlled amplitude.
