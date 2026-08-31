# A three-second check separates the cases the ink metrics cannot

**2026-08-31.** Follow-on from `reports/duplicate_coverage_inflates_the_objective.md`, which showed
the spiral ink objective rises 92.47% under fully duplicated coverage that reads no new papyrus. That
report is a criticism. This is the constructive half: the condition is cheaply detectable from the
meshes the pipeline already writes.

## The separation

Five arms off one fit. "Honest" arms add real papyrus or none; "duplicate" arms add rendered surface
whose occupied cells are byte-identical to the baseline, so they read nothing new.

| arm | truth | total_fg_pixels | fg_fraction | line | column | gap>=2 overlap |
|---|---|---:|---:|---:|---:|---:|
| A | honest | 240,088 | 0.00897 | 0.438 | 0.232 | 0.00% |
| B | DUPLICATE | 270,314 | 0.00907 | 0.436 | 0.209 | 10.32% |
| C | honest | 270,899 | 0.00882 | 0.388 | 0.161 | 0.00% |
| D | DUPLICATE | 282,405 | 0.00967 | 0.415 | 0.155 | 8.37% |
| E | DUPLICATE | 462,109 | 0.00853 | 0.409 | 0.192 | 100.00% |

Requiring that the duplicate range and the honest range not overlap:

```
total_fg_pixels       dup [270314, 462109]      honest [240088, 270899]     overlaps
overall_fg_fraction   dup [0.00853, 0.00967]    honest [0.00882, 0.00897]   overlaps
overall_line_score    dup [0.409, 0.436]        honest [0.388, 0.438]       overlaps
overall_column_score  dup [0.155, 0.209]        honest [0.161, 0.232]       overlaps
gap>=2 overlap        dup [8.37%, 100%]         honest [0.00%, 0.00%]       SEPARATES
```

All four numbers the loop is pointed at, or could be pointed at, fail. The geometric check separates
with an 8.37 point gap and no ambiguity.

## Cost

`scripts/measure_winding_overlap.py` on the full 120-winding fit, 11,566,828 surface points:

```
runtime 3 s   (one render + score of ten windings is about 12 minutes)
```

It reads only `x/y/z.tif` from the fitted meshes. No ink volume, no nnU-Net, no GPU, no native VC
binaries. Roughly 0.4% of the cost of one scoring run, and available before any render happens.

## How it works, and why gap>=2

Quantise every valid surface point to a 4-voxel cell and record which winding claims it. A cell
claimed by two windings **two or more apart** cannot be explained by sheet spacing: adjacent sheets
sit `dr_per_winding` apart, 16.17 voxels in this fit, so at 4-voxel cells they land in distinct
cells. Gap-1 coincidences are a quantisation artefact and scale steeply with cell size (12,536 cells
at 4 vx against 808,596 at 16 vx); they are reported separately and are not the signal.

## Limits, and what not to do with it

**Report the number, do not hard-code a threshold.** A converged 120-winding fit here reads 0.09%,
not 0. Ten- and eleven-winding subsets read 0.00%. A universal cut cannot be set from one fit, and
publishing the value beside the score is the honest form, the same discipline ScrollGT uses for its
floors.

**It detects duplicate coverage, not gaming in general.** Any other route to inflating
`total_fg_pixels` is outside its reach. It is one guard, not a sufficient one.

**It cannot tell intent from accident.** A fit that double-covers papyrus through a genuine topology
error scores the same as one that does it to farm the metric. Both are worth surfacing.

**It is not a fit-quality score.** Duplicate coverage is *absent* from the near-unfitted 100-step
configuration and appears only once the fit converges, so a low reading is not evidence of a good
fit. See `reports/spiral_ink_objective_reachability.md`.

## Status

Not reported upstream. The related issues are villa#1658, on metrics the scorer computes that the
loop is never told to read, and villa#1660, on the render path.
