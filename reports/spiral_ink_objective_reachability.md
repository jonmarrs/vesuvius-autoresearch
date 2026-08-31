# The spiral ink objective: what is checkable here, and where it stops

**2026-08-30.** villa's spiral-fitting track runs its own LLM loop
(`spiral-fitting/autoresearch.md`) that optimises a frozen scorer. We have been wrong about a frozen
scorer twice, in both directions: `val_bpb` was dead and we selected on it for weeks, and `skel_dist`
turned out uncorrelated with detection quality so that a zero-overlap shifted prediction scored 0.0
and passed. That is the reason to look here, and also the reason to be careful about what gets
claimed.

Result: **the direction is stopped at a reachability wall**, with two verifiable documentation
findings and one measurement banked on the way.

## Catalogue check first, per the standing policy

Nearest existing work: **spiralcheck** (held-out evaluation of finished fits from output meshes
alone, leakage measurement, ground-truth-free winding-order checks), **TIFXYZ Doctor** (grid QA, an
overlap-component-isolated benchmark), **spiral-fit-consumer-gpu** (the fitter on a 12 GB GPU, which
overlaps our own setup-guide work). None of them examine the ink-coverage objective the loop
optimises.

## Reachability: the objective is not measurable on this machine

`run_single.py` chains fit, then `render_ink.py`, then the scorer. Checked in order:

| requirement | status |
|---|---|
| the fit | runs here, 30k steps, one 4090 |
| scorer model `scrollprize/ink-coverage-32um` | **public and ungated** |
| `vc_render_tifxyz`, `flatboi`, `vc_tifxyz2obj`, `vc_obj2tifxyz`, `vc_obj_uv_lift` | **all absent** |

Render needs five native VC binaries, none of them built here. Without strips there is no
`total_fg_pixels`, so no claim about the objective can be *demonstrated* from this machine. Asking
this before building is the sheet-switch-detector lesson: that probe was pre-registered in full
before anyone checked whether its premise was reachable, and the premise was not.

## Two documentation findings, verifiable without running anything

**1. `autoresearch.md` names a file that does not exist.** It refers to `get_ink_coverage.py` at four
places (lines 24, 41, 60, 74). No such file is in the repo. The scorer is `get_ink_metrics.py`.

**2. The scorer computes two structure metrics the loop is never told about.**
`get_ink_metrics.py` persists `overall_line_score` (text-line pitch periodicity, expected band
80-120 strip px) and `overall_column_score` (column width, expected 850 px) into `metrics.json`.
`autoresearch.md` mentions them zero times: it directs the loop to `total_fg_pixels`, then
`overall_fg_fraction` as the anti-gaming guard, then the satisfaction metrics as diagnostics.

## An argument about the guard, which is reasoning and not a measurement

`autoresearch.md` says `overall_fg_fraction` "guards against gaming: if a change balloons
`total_fg_pixels` only by inflating the surface with garbage geometry, the fraction will collapse."

That holds for surface added over *blank* papyrus. It does not hold for surface added over *inked*
papyrus that is already counted: duplicate coverage raises fg_pixels and total_pixels together and
leaves the ratio flat. The doc classifies precisely that signature as a win, "lifts total while
holding fraction roughly steady, is a real win".

Three things keep this from being an accusation:

* it is not demonstrated, and cannot be from here, for the reason above;
* the baseline fit shows the mechanism at 0.1% (below), so there is no evidence the loop is
  currently exploiting anything;
* the doc also directs the loop to watch the satisfaction metrics, an additional check whose
  strength against this particular failure is unquantified.

## The measurement: duplicate winding coverage in a real fit

`scripts/measure_winding_overlap.py`, needing only fitted meshes, no ink volume, no scorer, no
native binaries. Both runs are 120 spliced windings, w010..w129, ~11.5M valid surface points.
`render_ink.py` filters to `'_spliced' in name`, so the plain/spliced pair of each winding is *not*
double-rendered; that trivial reading was checked and is wrong.

Quantised to 4 voxels, well under the fit's 16.17-voxel sheet spacing:

| run | occupied cells | multiply claimed | claimed by windings >=2 apart |
|---|---:|---:|---:|
| baseline01 | 11,539,167 | 22,881 (0.20%) | 10,345 (0.09%) |
| seed02 | 11,559,283 | 24,248 (0.21%) | 11,895 (0.10%) |

Adjacent-winding (gap 1) overlap scales steeply with quantisation, 12,536 cells at 4 vx to 808,596
at 16 vx, which is the signature of sheets 16 vx apart merging as the cell size approaches their
spacing. It is an artefact and not a defect. The gap>=2 count is the part that cannot be explained
by sheet spacing.

**Seed control.** The rate reproduces; the locations largely do not.

```
baseline01 gap>=2 cells 10,345    seed02 11,895
intersection 584   union 21,656   observed Jaccard 0.0270
uniform-chance Jaccard 0.000479   enrichment x54.8
```

The uniform null is generous, since duplicate coverage is surely concentrated in geometrically hard
regions and two unrelated processes confined to the same regions would also show enrichment. So the
defensible statement is the weak one: **the rate is stable across seeds, the specific cells mostly
are not.** For contrast, the sheet-switch flags reached Jaccard 0.9696 across seeds; this is a
different regime entirely.

**Quality control, which reversed the reading.** The 100-step smoke run is the same dataset and the
same 120 windings, fitted almost not at all: satisfied-area fraction 0.100 against 0.840 for both
converged runs. I expected a worse fit to show more duplicate coverage. It shows none.

| run | steps | satisfied area | occupied cells | multi-claimed | gap>=2 |
|---|---:|---:|---:|---:|---:|
| smoke01 | 100 | 0.100 | 11,360,032 | 2,535 (0.02%) | **0** (0.00%) |
| baseline01 | 30,000 | 0.840 | 11,539,167 | 22,881 (0.20%) | 10,345 (0.09%) |
| seed02 | 30,000 | 0.840 | 11,559,283 | 24,248 (0.21%) | 11,895 (0.10%) |

The obvious confound is that the near-unfitted run might simply be more spread out, so
`scripts/measure_spiral_comparability.py` checks it. It cuts the other way:

```
smoke01      centre ( 4362.2, 4841.0)  radius  354.8..2261.3  median inter-winding step 16.62  monotone 119/119
baseline01   centre ( 4348.8, 4844.4)  radius  389.3..2503.6  median inter-winding step 17.79  monotone 119/119
seed02       centre ( 4348.6, 4844.2)  radius  389.0..2503.6  median inter-winding step 17.94  monotone 119/119
```

Same spiral, same centre, all three monotone in winding order. The smoke run's windings are packed
*tighter* (16.62 vs 17.79), which makes overlap more likely at a fixed 4-voxel cell, not less. It
still has exactly zero.

So the direction is the opposite of what I assumed when I wrote this section: **duplicate coverage is
absent from the starting configuration and is introduced by fitting.** The patch observations the fit
begins from are distinct surfaces that do not double-cover; 30,000 steps of optimisation put 0.09% of
the surface into a state where two windings two or more apart claim the same papyrus.

## What this is and is not

The reference value I said was missing turned out to be available without the render path, and it is
zero: the 100-step configuration has no far-overlap at all. That makes this more than a bare
measurement. What it still is **not** is a demonstration that the double coverage costs anything.
0.09% of surface is small, nothing here connects it to ink recovery, and the quantity that would
connect it is `total_fg_pixels`, which is exactly what the missing binaries block. A fit that
double-covers 0.09% of the papyrus may be paying nothing for it.

Two readings remain open and this measurement does not separate them: the fit is making a
topological error in those places, or the fit is correctly representing genuinely ambiguous
geometry that the input patches simply left unresolved.

## To go further, someone needs

The five native VC binaries built, and the ink volume. With those, the test is direct: render and
score a fit, then render and score the same fit with a region deliberately double-covered, and read
`total_fg_pixels`, `overall_fg_fraction`, `overall_line_score` and `overall_column_score` off both.
That experiment is specified but unrun, and should not be written up as though the answer is known.
