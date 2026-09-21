# Displacing the surface 4 voxels costs ink in BOTH directions — 20% inward, 4% outward

**2026-09-20.** Registered in
`docs/preregistration/2026-09-20_radial_displacement_on_the_flat_surface.md`, decided by
`scripts/analyse_flat_displacement.py`, both committed before any arm scored.
`reports/flat_displacement_verdict.json`.

## The result

One flat surface (`radial_work_rad0`'s `w120-129_flat`), displaced radially, rendered three times
with the flatten held fixed. All three arms written by one tool; canvas identical (352,131,600 px).

| arm | directory | delta | `total_fg_pixels` | vs ZERO |
|---|---|---:|---:|---:|
| ZERO | `flat_study_zero` | 0 vx | 1,698,914 | — |
| **IN** | `flat_study_in` | **−4 vx** | **1,363,076** | **−19.77%** |
| **OUT** | `flat_study_out` | **+4 vx** | **1,622,775** | **−4.48%** |

The floor's two arms are `radial_work_rad0` and `flat_study_probe`.

Floor F = **0.0014%** (24 px, `reports/holding_the_flatten_fixed_collapses_the_floor.md`). Both
effects clear 3F by three to four orders of magnitude; the margin is not in question.

## Against the registered rule: DIFFERENT EFFECT

**Prediction 2 was "IN loses 5-15%, reproducing the gap fix's −10.35%". It lost 19.77% — a MISS.**
The registered band said that is a *different effect*, not the gap fix's mechanism, and that is what
is reported.

Concretely: the gap fix shifted the surface **3.96 vx inward** and lost **10.35%**. A clean
**4.0 vx inward** shift of the flattened surface loses **19.77%** — **1.91× as much** from the same
displacement. So displacement alone over-explains the gap fix's cost by nearly 2×, which means the
gap fix is *not* a pure radial shift: whatever else it does to the surface **recovers about half** of
what the shift alone would lose.

That is a sharper statement than the observational one it replaces. `reports/the_gap_fix_moves_the_surface_radially.md`
could only say the shift and the loss co-occur. This says the shift is *sufficient* to produce a loss
of that order, and that the fix's actual loss is smaller than the shift predicts.

## The result nobody predicted: OUT loses too

**No prediction was registered for OUT.** It loses **4.48%**.

So moving off the fitted surface costs ink in **both** directions, and asymmetrically: **inward costs
4.4× more than outward** at the same magnitude. The fitted surface is at or near a local maximum of
recovered ink, and the maximum is steep on the inside and shallow on the outside.

Two readings, not distinguished here:

* **The ink layer is asymmetric.** Ink sits on one face of the papyrus, so moving into the sheet
  (toward the fiber core) leaves the ink layer faster than moving away from it into the gap.
* **The scorer's sampling window is asymmetric.** `--num-slices 5` samples a depth band around the
  surface; if the band is not centred, one direction exits it before the other.

The registration said per-voxel sensitivity must not be extrapolated across regions. This adds: it
must not be extrapolated across **directions** either.

## Why this is trustworthy where the first design was not

* **Flatten held fixed.** The first design let the flatten re-solve on displaced input; it moves the
  surface 7.15 vx by itself, larger than the manipulation. Here it runs once and every arm renders the
  same surface — verified by identical canvas across all three.
* **Floor measured, not assumed.** F came from a byte-identical re-render, not from a prior report.
* **Writer-identical arms.** The rebuild's float rounding was measured at 107 px
  (`reports/the_writer_effect_is_real_and_my_prediction_missed.md`) — 0.03% of IN's effect and 0.5%
  of OUT's, and it cancels anyway because all three arms share it.
* **Rule fixed first.** The verdict branches, the 5-15% band and the 3F margin were committed before
  any arm existed; nothing was tuned to a number.

## What it does not show

**One arm per condition.** These are point estimates against a measured floor, not a sampling
distribution. The effects are 3,000× and 14,000× the floor, so the *signs* and *orders* are not in
doubt; the third significant figure is.

**One magnitude.** Two points do not give the shape of the loss curve. Whether 2 vx inward costs 10%
or 2%, and whether the asymmetry holds at 1 vx, are open.

**`total_fg_pixels` is an area count.** 20% less ink is not 20% less readable text; a displaced
surface may shed false positives and true ink at different rates, and this cannot tell them apart.

**One surface, one ROI, one scorer.** The asymmetry in particular is exactly the kind of result that
could be a property of this scorer's depth sampling rather than of the papyrus.

## The limit that matters for villa

Villa's loop optimises `total_fg_pixels` over candidate *fits*. This shows that quantity is
**extremely sensitive to sub-winding radial placement** — 4 voxels, a quarter of the sheet spacing,
moves it 20% — and that the sensitivity is asymmetric. Any change that nudges the fitted surface
inward by a few voxels will read as a large regression on the objective **whether or not the geometry
got better**, which is the pattern `reports/gap_fix_costs_ink_established.md` found with the fix
villa itself shipped.
