# Scan-quality metric: is the target reachable? Yes, with one correction to the design

**2026-08-30.** The check run *before* building anything, which is the lesson from the sheet-switch
detector: that study pre-registered how to validate a detector and never asked whether the condition
it detects is reachable.

## Why this target

villa's bottleneck table, first row: *Compressed or highly curved regions ... What would help:*
**scan-quality metrics**, *and scroll-specific acquisition recipes.* The open-problems doc explains
the mechanism (fiber-level decoherence producing local haze) and states the property that makes a
metric worth having: *"scan quality is local. A scan can hold excellent regions and
nearly-impossible-to-unwrap ones in the very same volume."*

Unclaimed as far as can be checked: searches across villa issues and PRs for scan quality,
compressed regions, and haze return only #191 itself. `sheet-topo-bench` (#1546) covers sheet
switch/merger benchmarking and `scroll-audit` (#1635) covers catalogue integrity; neither touches
this.

## Reachability, established before building

**The data needs no registration bridge.** `volumetric-instance-labels/instance-labels-harmonized/`
ships 80 cubes, each a self-contained pair: `<cube>_volume.nrrd` (raw CT) and `<cube>_mask.nrrd`
(hand-annotated per-sheet instance IDs), in one coordinate space, 256^3, about 34 MB per cube.

This matters specifically. Our worst published error, the "everything reads at chance" retraction,
was a coordinate bridge that was wrong in a way its own internal checks could not see. Here there is
no bridge to get wrong.

**The outcome varies**, measured over all 80 masks:

| statistic | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| sheets per cube | 6 | 10 | 13 | 14 | 18 |
| labelled % | 14.0 | 28.3 | 30.9 | 33.4 | 47.4 |
| **contact %** | 0.000 | 0.454 | 0.663 | 1.048 | **3.166** |
| thickness proxy | 1.79 | 2.59 | 2.96 | 3.29 | 5.69 |

Contact fraction spans 0 to 3.17%, `p90/p10` = 5.3x, one cube at exactly zero and 24 above 1%. A
12-cube sample had topped out at 1.10%, so the small sample understated the range by 3x, which is
itself a reason to characterise populations rather than samples.

**One measure carries no signal and is discarded:** the 10th-percentile inter-sheet gap is exactly
1.00 voxel in every cube. That is a quantisation floor, not a measurement.

## The correction: contact fraction is geometry, not scan quality

Difficulty here has two sources and they must not be conflated:

* **geometry**: sheets physically touching or thin, which `contact %` and the thickness proxy measure;
* **scan quality**: haze blurring layer boundaries *even where sheets are separate*, which is what the
  bottleneck row is about and what an acquisition recipe could act on.

Using contact fraction as the outcome would measure the first and call it the second. The right
outcome is **boundary definition in the CT**: for labelled inter-sheet boundaries, how sharp is the
CT transition across them. Blurred boundaries where the label says two distinct sheets meet is
exactly the haze the doc describes.

That gives a well-posed problem:

* **outcome** (needs labels, available on these 80 cubes): CT contrast across labelled sheet boundaries;
* **predictor** (CT only, so it generalises to unlabelled volume): a local texture statistic;
* **claim to test**: the predictor tracks the outcome, so scan quality can be estimated where no
  labels exist.

## The limitation to state now, not later

**These cubes were hand-annotated, so they were selected for being annotatable.** Regions where
layers dissolve entirely, the worst of the compressed-region problem, are plausibly the ones nobody
could label and are therefore systematically absent. Any relationship found here is measured on the
tractable end of the difficulty range, and the write-up must say so wherever a number is quoted.

## Status

Reachability: **established**. Data is public, self-contained, needs no registration, and the
outcome varies 5.3x. Nothing is built yet, and the next step is to measure boundary definition
against a CT-only predictor on the 12 cubes already fetched.
