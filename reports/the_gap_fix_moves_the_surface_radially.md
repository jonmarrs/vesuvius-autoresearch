# The gap fix pulls the scored surface 4 voxels inward, and that is where the 10% of ink went

**2026-09-19.** No new fits. `scripts/measure_radial_displacement.py`, numbers in
`reports/gap_fix_radial_displacement.json`.

## The question this closes

`reports/the_gap_fix_does_not_remove_duplicated_coverage.md` showed the gap-expander fix costs
**10.35%** of `total_fg_pixels` while every coverage measure stays flat — same strip area, same 3D
surface, no drop in duplication. It concluded the fix **relocates or re-samples** the surface, and
left which of those explicitly unsettled.

It re-samples. **The surface moves radially — across the sheet, not along it.**

## The measurement

The two arms' meshes are not point-comparable ((285,613) vs (285,612)), so no displacement field can
be computed. For a spiral it does not need to be: **radial** movement is normal to the sheet (a depth
change), **θ/z** movement is along it (relocation). Those separate with no correspondence at all.

| winding | baseline r | gap133 r | Δr | p |
|---|---:|---:|---:|---:|
| w120 | 2341.31 | 2337.66 | −3.64 | <0.0001 |
| w121 | 2358.93 | 2354.94 | −3.99 | <0.0001 |
| w122 | 2375.40 | 2370.45 | −4.95 | <0.0001 |
| w123 | 2391.27 | 2385.57 | −5.70 | <0.0001 |
| w124 | 2407.22 | 2404.09 | −3.14 | <0.0001 |
| w125 | 2425.04 | 2419.63 | −5.42 | <0.0001 |
| w126 | 2440.97 | 2437.33 | −3.64 | <0.0001 |
| w127 | 2457.33 | 2453.07 | −4.25 | <0.0001 |
| w128 | 2471.33 | 2468.84 | −2.49 | 0.0006 |
| w129 | 2484.98 | 2482.62 | −2.36 | 0.0015 |

**Mean −3.96 voxels. Ten of ten windings, every one significant, all in the same direction.** That is
**24.5% of one winding gap** (16.17 vx) — a fraction of the sheet spacing, so the surface is not
jumping to a neighbouring winding; it is sitting at a different depth within the same one.

And nothing else moved:

| | delta | p |
|---|---:|---:|
| θ span | −0.000 rad (2π both) | 0.586 |
| z max | +0.001 | 0.629 |
| z centre | +5.4 | 0.159 |
| surface points | −0.47% | 0.0002 |

## Two controls that changed the answer

**One derived axis, shared.** A per-arm axis would be worse than a wrong one: axis error is
common-mode and cancels in the delta **only if both arms use the same axis**.
`analyse_placement_mechanism.py` records that a hardcoded axis once halved an effect.

**Sentinel exclusion, which moved the headline 20%.** `z <= 0` marks invalid samples and they are
**5.1% of the surface**. Including them gives −4.65 vx; excluding them, −3.96. They also carry
garbage `x,y` that **displaced the derived axis itself** — the pooled mean radius reads 2550 with them
and 2341 without. Both the estimate and its coordinate frame were contaminated.

## What it means

**About 4 voxels of radial displacement co-occurs with a 10.35% loss of recovered ink.** On this
pipeline, ink recovery is acutely sensitive to where the surface sits across the sheet: a quarter of
one winding gap is the difference between finding that ink and not.

That is consistent with the label work — `reports/label_snapping_feasibility_probe.md` found labels
already sit on the CT surface to within an IQR of 0 against a 6.0 comparison, i.e. a few voxels is
the scale on which surface placement is decided.

**Stated as what it is: observational.** The fix changes the configuration, and both the displacement
and the ink loss follow. This does not isolate displacement as the cause — a study that moved the
surface radially by a controlled amount, holding everything else fixed, would. Nothing here does that,
and the co-occurrence is not a demonstration.

## Tested causally 2026-09-20: displacement alone over-explains the loss

The controlled version ran: one flattened surface shifted **4.0 vx inward** with everything else
fixed loses **19.77%** — `reports/displacing_the_surface_costs_ink_in_both_directions.md`. So the
3.96 vx shift measured here is **sufficient** to produce a loss of this order, and in fact produces
**1.91×** the gap fix's 10.35%. The gap fix is therefore not a pure radial shift; whatever else it
does recovers about half of what the shift alone would cost. Outward displacement also loses (4.48%),
so the fitted surface sits near a local maximum that is steep inward and shallow outward.

## Why the direction is worth noting

The fix **raises** gap-expander capacity 130 → 133, clearing a warning that capacity was short of
`shell_outer_winding_idx = 130`. More capacity to reach outward, and the surface settles **inward**.
Unexplained, and recorded as such rather than rationalised.

## Limits

One dataset, one ROI, `w120-w129`, twelve fits. Mean radius per winding is a summary: it cannot
distinguish a uniform inward shift from a tilt or a partial one, and the per-winding spread
(−2.36 to −5.70) suggests it is not perfectly uniform. `total_fg_pixels` is an area count, so "10%
less ink" is not "10% less readable text".
