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

---

# RESULT, same day: the outcome is saturated. This design cannot work on this data.

Ran on the 12 fetched cubes. Two findings, one fatal.

## 1. Fatal: there is nothing to predict

```
separability_auc over 12 cubes:  min 0.9946   median 0.9992   max 0.9997
```

The label-derived outcome, ROC-AUC of CT intensity separating sheet interior from inter-sheet gap,
is **saturated at ~0.999 in every cube**. Total spread is 0.005. Every annotated cube has cleanly
separable layers.

So there is no difficulty gradient for a CT-only predictor to track. The correlations the script
printed (-0.36 to -0.57) are fitted to a 0.005-wide band of noise and mean nothing.

**This is the annotatability selection effect, arriving exactly where it was predicted.** The
reachability note above said: *"these cubes were hand-annotated, so they were selected for being
annotatable. Regions where layers dissolve entirely are plausibly the ones nobody could label and
are therefore systematically absent."* They are absent. The set contains no bad-quality examples,
so it cannot calibrate a metric whose purpose is to find them.

Worth being precise about what this does and does not say. It does **not** say scan quality is
uniform in Scroll 1; the open-problems doc's own figures show a compressed region before and after
rescanning. It says the *labelled* subset carries none of that variation, and a supervised handle on
scan quality cannot be built from labels that only exist where the scan was already good.

## 2. Incidental, and worth passing on: the cubes mix dtypes

```
00000_02408_04560   uint16   0..65535
00064_02664_04304   uint8    8..255
00768_02152_03536   uint16   0..65535
```

`instance-labels-harmonized` harmonises **instance IDs**, not intensities. The volumes are a mix of
`uint8` and `uint16`, so raw-intensity statistics differ by ~250x across cubes for reasons that have
nothing to do with the scan. Our `intensity_std` ranged 42.7 to 12901.7 purely from this.

Anyone computing intensity features, or training without per-cube normalisation, silently gets a
two-cluster dataset. The name invites the assumption that the cubes are comparable. This is a small,
checkable observation and is the only part of today's work that might be worth reporting upstream.

## What would be needed to do this properly

Labelled examples **from compressed regions**, which by construction barely exist: the regions worth
measuring are the ones nobody could annotate. Options, none cheap:

* use a downstream proxy for difficulty rather than labels, e.g. where a published surface model's
  confidence collapses, accepting that this measures the model as much as the scan;
* use the paired DLS 7.91 um and ESRF 2.4 um acquisitions of the same region as a
  quality contrast, if a registered pair is ever published;
* treat it as unsupervised, and validate against acquisition metadata rather than labels.

## Cost

About two hours, including the reachability check that predicted this failure mode and the
population characterisation that did not catch it. The mask-level outcome (contact fraction) varied
5.3x and looked promising; the CT-level outcome that actually matters does not vary at all. Those
are different quantities and only the second one was ever the target.
