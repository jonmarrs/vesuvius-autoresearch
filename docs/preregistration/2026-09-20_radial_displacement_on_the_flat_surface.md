# Pre-registration: does radial displacement cause ink loss? (redesigned, on the flattened surface)

**Written 2026-09-20, before the floor is measured and before either treatment arm is rendered.**
Replaces `docs/preregistration/2026-09-19_radial_displacement_causes_ink_loss.md`, whose design was
invalidated by its own control (`reports/the_radial_study_design_is_invalid.md`).

## What changed and why

The first design displaced **input meshes** and let the lasagna flatten re-solve afterwards. That
flatten moves the surface **7.15 vx** between runs on identical input in this region — **1.8× the
4 vx manipulation** — so the treatment arms could not have been interpreted.

This design displaces the **flattened surface** instead. The flatten happens once, upstream of the
branch point, so every arm renders the same surface and its variance is removed **by construction**
rather than averaged down at ~2h per render.

Enabled by `repro/spiral_render/reuse_flatten.patch` (`RENDER_REUSE_FLATTEN=1`), verified by running
it rather than reading it.

## Arms

All three render **one** flat surface — `radial_work_rad0/meshes/concat/w120-129_flat`, already
computed — displaced radially about an axis derived from that surface's own points.

| arm | delta | built | verified |
|---|---:|---|---|
| **ZERO** | 0 vx | `flat_study_probe` (rendering now) | flat is byte-identical to rad0's across `x/y/z.tif` and `meta.json` |
| **IN** | −4 vx | `flat_study/flat-4` | mean r −4.000, `z.tif` byte-identical, 2,564,050 valid pts |
| **OUT** | +4 vx | `flat_study/flat4` | mean r +4.000, `z.tif` byte-identical, 2,564,050 valid pts |

Radial displacement moves only `x,y`, so `z.tif` being byte-identical is a positive control that the
manipulation did what it says. Valid-point counts are unchanged, so no geometry is dropped.

## Amendment, made before any arm scored: the ZERO arm is rebuilt, not reused

The arms table above named `flat_study_probe` as ZERO. **It is demoted to the floor measurement
only**, because it is not writer-identical to IN and OUT.

`build_radial_displacement_arm.py` recomputes coordinates as `cx + dx/r*(r+delta)`. At `delta = 0`
that is algebraically the identity, but **not** bitwise: float32 rounding leaves `x` and `y` differing
from villa's originals by up to **0.000244 vx** (`z` is untouched and byte-identical). The probe
carries villa-written tifs; IN and OUT carry rewritten ones. Comparing them would fold a
writer difference into every effect.

The difference is physically negligible — 16,000× smaller than the 4 vx manipulation and ~2000×
smaller than the 0.535 vx flatten wobble that moves ink 1.42%, implying an effect near 0.0007%. **It
is removed anyway rather than argued away**, because two assumptions of negligibility have already
been wrong today, and the fix costs one render on tooling that already exists.

**So there are two distinct references, and they answer different questions:**

| | arms | what it measures |
|---|---|---|
| **F, the floor** | `flat_study_probe` vs `radial_work_rad0` | render + score noise on **byte-identical** input, flatten held fixed |
| **the effects** | IN and OUT vs `flat_study_zero` | displacement alone, all three written by one tool |

`flat_study_zero` is `flat0` — the same rebuild at `delta = 0`. Verified across all three effect
arms: identical valid-point counts (2,564,050), identical array shapes, **`z.tif` byte-identical**,
and mean radii of exactly +0.000 / −4.000 / +4.000.

Cost rises from two renders to three (~6h). The decision rule is unchanged.

## The floor is measured, not assumed — that is the lesson from the first attempt

The first registration assumed **1.42%** from a report that attributed the spread to the nnU-Net
scorer. The scorer contributes **0.0032%**; the flatten was the source, and nobody had measured it.

So this study **measures its own floor before interpreting anything**. ZERO renders a byte-identical
copy of rad0's flat surface, and `|ZERO − rad0|` **is** the render+score floor with the flatten held
fixed — the first such measurement in this project.

**F is that number. It is not yet known.** Everything below is expressed in multiples of F, so the
rule is fixed before both the floor and the effects.

## A free side-measurement, claimed before the number exists

`flat_study_probe` and `flat_study_zero` are both delta-0 renders of the same flat surface, reusing a
flatten, on one pinned tree. They differ in **exactly one thing**: the probe carries villa's original
tifs, `zero` carries the rebuild, whose float32 rounding leaves `x,y` up to **0.000244 vx** different
(`z` byte-identical).

**So `|probe − zero|` isolates the writer effect**, on top of the render+score floor F = 0.0014%.

**Prediction: they agree to within ~0.002%**, i.e. the writer contributes nothing measurable. The
reasoning is proportional — the 0.535 vx flatten wobble moves ink 1.42%, so 0.000244 vx should move
it ~0.0007%, below F.

**If they disagree by more than ~0.01%, that is a finding and it matters**: it would mean ink
recovery responds to surface changes three orders of magnitude below a voxel, which would make
*every* comparison in this corpus sensitive to float formatting. I do not expect it, and the arms
were rebuilt to be writer-identical precisely so the study does not depend on the answer.

Recorded now because a null here is only meaningful if it was predicted, and because the alternative
would be to notice the agreement afterwards and call it confirmation.

## Decision rule, in multiples of the measured floor F

| outcome | conclusion |
|---|---|
| **F > 1.5%** | **The redesign failed.** Removing the flatten did not buy a tight floor, so `vc_render` itself is noisy. Report F as a finding and do NOT interpret IN/OUT at n=1. |
| IN loss ≥ 3F and within 5-15% | **Displacement is sufficient to cause the gap fix's ink loss.** |
| IN loss ≥ 3F but outside 5-15% | Displacement moves ink, but not by the gap fix's amount — a separate effect, not its mechanism. |
| IN loss < 3F | **Displacement is not the cause** at this magnitude. |

**3F, not "significant":** with one arm per condition there is no sampling distribution, so this is a
margin against a measured floor, not a test. Stated plainly rather than dressed as a p-value.

## Predictions, fixed now

1. **F < 1.5%.** The flatten is removed and the scorer alone is 0.0032%, so what remains is
   `vc_render_tifxyz`, a deterministic sampler. If F comes back large, that is itself worth knowing.
2. **IN loses 5-15%**, reproducing the gap fix's −10.35% from displacement alone.
3. **No prediction for OUT.** Ink could rise (toward better-inked papyrus) or fall (any departure
   from the fitted surface costs). I have been wrong on the direction of an observable repeatedly
   here, most recently on a two-point %/vx law that the third point missed by 6×.

## What it still cannot settle

**Displacement is one channel, not a partition.** A SUFFICIENT verdict shows displacement is enough
to produce the loss; it does not show the gap fix works only that way, since the fix also changes the
fit itself.

**`total_fg_pixels` is an area count.** "Less ink" is not "less readable text", and a displaced
surface may lose true ink and false positives at different rates.

**One surface, one ROI, one magnitude, one scorer.** A sweep would give the sensitivity curve; this
gives one point and the sign of a second — and
`reports/the_flatten_lands_on_different_surfaces.md` already showed that per-voxel sensitivity is
**not** constant across regions, so this result must not be extrapolated to other windings.

## Cost

Two renders at ~2h plus scoring, no fitting and no flattening: **about 5 hours**. ZERO is already in
flight.
