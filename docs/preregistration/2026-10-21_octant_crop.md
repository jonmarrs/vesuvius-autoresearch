# Pre-registration: is the neural tracer's tolerance-4 deficit on the 256³ in-sample cubes their size?

**Status: REGISTERED 2026-10-21, before any octant has been scored.** CPU only, at nice 19 with the loop running.

## The question

Finding 94 (`reports/tolerance4_rescore.md`) scored villa's neural fiber tracer and our tracer at a 4-voxel tolerance.
The neural tracer leads on all three in-sample 512³ cubes (median 49.50 against 43.69), and still trails on all eight
in-sample 256³ cubes. Finding 91 listed cube size as an untested cause of its in-sample deficit. Here size and scroll
are tangled: the 512³ in-sample cubes are all Scroll 5, and five of the eight 256³ ones are Scroll 1.

**The test separates them.** It cuts the three 512³ cubes into their eight 256³ octants and scores both tracers on
each octant. Both tracers traced the whole cube, so only the scoring scale changes: how long a ground-truth fiber can
run inside the scored volume, and how much of it lies near a face.

## Data, fixed now

* **Cubes:** the three in-sample 512³ cubes (`s5_06494_01994_03994_512`, `s5_06994_00994_04994_512`,
  `s5_07994_01994_05494_512`), each cut into 8 octants of 256³ at offsets 0 and 256 on each axis. That makes 24
  octants.
* **Labellings:**
  * villa's neural tracer: finding 91's `.afv`, rasterised as finding 91 did;
  * our tracer: finding 80's saved instances, the labellings ScrollGT's rows came from.

  Each is cropped to the octant.
* **Ground truth:** each cube's published skeleton, shifted to the octant. A fiber is kept where it has at least two
  nodes inside, as ScrollGT's loader keeps fibers, and the scorer ignores nodes outside. Checked before registration:
  on all 24 octants this keeps the same fibers as ScrollGT's own `in_bounds_mask`.
* **Scoring:** ScrollGT `score_tracing`, scoring version 3, at tolerances 4 and 2.
* **Identity:** each whole cube, scored by the same path at tolerance 4, must reproduce finding 94's merge-penalized
  ERL, coverage, instance count and predicted length for both entrants. Otherwise the status is IDENTITY_FAILED.
* `scripts/octant_crop_rescore.py` writes `reports/octant_crop_rescore.json`.

## Prediction, fixed now

**P1: cropping does not reverse the lead.** At tolerance 4, the neural tracer's merge-penalized ERL is above our
tracer's on at least 16 of the 24 octants. Confidence low.
* **For it:** the lead on these cubes at 4 is wide (a median 1.13×), and crops of one cube share its scan and
  annotation.
* **Against it:** a crop shortens the ground-truth fibers the scorer can follow, which caps a long-run tracer's ERL
  more than a short-run one's.

**Descriptive, no prediction:** the same at tolerance 2; per-cube medians; coverage, merges and the ground truth's
fiber counts per octant.

## Decision rule

| outcome | conclusion |
|---|---|
| a whole cube fails the identity check | IDENTITY_FAILED, no verdict |
| leads on ≥ 16 of 24 (P1 holds) | "cropping does not reverse it: cube size, as scored, is not why the 256³ in-sample cubes trail at tolerance 4". What remains is their scroll (mostly Scroll 1) and annotation. |
| leads on ≤ 8 of 24 | "cropping reverses it: the 256³ cubes' deficit at tolerance 4 may be their size" |
| 9–15 | "inconclusive: cropping weakens the lead without reversing it" |

Any change to ScrollGT is a separate decision by the owner.

## What the result cannot do

* **Crops are not 256³ runs.** The tracers saw the whole 512³ cube. A tracer run on a 256³ cube also loses context at
  its faces, which this does not measure.
* **Three cubes, one scroll.** The crops are all Scroll 5.
* **The octants of one cube are not independent.**
