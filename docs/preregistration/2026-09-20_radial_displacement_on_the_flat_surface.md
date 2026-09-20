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

## The floor is measured, not assumed — that is the lesson from the first attempt

The first registration assumed **1.42%** from a report that attributed the spread to the nnU-Net
scorer. The scorer contributes **0.0032%**; the flatten was the source, and nobody had measured it.

So this study **measures its own floor before interpreting anything**. ZERO renders a byte-identical
copy of rad0's flat surface, and `|ZERO − rad0|` **is** the render+score floor with the flatten held
fixed — the first such measurement in this project.

**F is that number. It is not yet known.** Everything below is expressed in multiples of F, so the
rule is fixed before both the floor and the effects.

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
