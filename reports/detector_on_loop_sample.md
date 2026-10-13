# The loop's validation sample cannot reward a model that reads ink (finding 88)

**2026-10-13.** Three read-only measurements, each **pre-registered**: its reading rule was committed before it ran.
They ran on CPU, one thread, at the lowest priority, beside the running loop. Scripts and outputs:

| measurement | script | committed before the run | output |
|---|---|---|---|
| A. the loop's 97-patch sample | `scripts/detector_on_loop_sample.py` | `5b5c4e2a` (run at `b8a8fff3`) | `reports/detector_on_loop_sample.json` |
| B. control: random windows | `scripts/detector_random_window_control.py` | `fe76e853` | `reports/detector_random_window_control.json` |
| C. the 400-patch draw, ink-free patches kept | `scripts/detector_on_full_v2_sample.py` | `c59cfa86` | `reports/detector_on_full_v2_sample.json` |

**Question.** The loop promotes on val_f1 (best F1 over thresholds 0.05–0.95, pooled over pixels) on the
ink-containing patches of a fixed 400-patch draw. Finding 86 found the incumbent below the all-ink F1 on that
sample. Is that the model, or can no model score well there? The test: the project's TimeSformer detector
(`models/detector/detector_epoch=7.ckpt`, held-out pixel AUC 0.709 on the whole of Fr143), scored on the same
sample through the same metric.

## A. On the loop's sample, the detector is no better than calling every pixel ink

Protocol `seeded-sample-400-v2+z1-27`: **97** ink-containing patches, **397,312** pixels, ink prevalence
**0.5760**, so calling every pixel ink scores F1 **0.7310**.

| predictor | val_f1 | margin over all-ink | ROC AUC | AP lift |
|---|---:|---:|---:|---:|
| loop incumbent (`best_model.pt`) | 0.7273 | **−0.0037** | 0.5615 | 1.0788 |
| detector, each patch's own 64 px window | 0.7320 | **+0.0010** | 0.5790 | 1.0994 |
| detector, its normal stride-32 tiling | 0.7372 | **+0.0062** | 0.6131 | 1.1644 |
| every pixel ink | 0.7310 | 0 | 0.5000 | 1.0000 |

The detector's primary margin is +0.0010, inside the pre-registered ±0.01 band: **F1 on this sample cannot tell a
model that reads ink from a constant.** Its own normal inference reaches +0.0062. To be promoted, a candidate must
beat the incumbent's 0.7273 by 0.03, that is, reach 0.7573, which is 0.0263 above the all-ink F1: more than four
times what the project's best detector reaches here.

## B. Control: the same pipeline reads ink on random windows of the fragment

Without this, A could be a bug in how the detector was fed. **400** random stride-32 windows inside Fr143's mask
(seed 0, of **93,504**; **115** contain ink), **1,638,400** pixels, prevalence **0.1545**:

| predictor | val_f1 | margin over all-ink | ROC AUC | AP lift |
|---|---:|---:|---:|---:|
| detector, single window | 0.3578 | **+0.0902** | **0.7034** | 1.8831 |
| every pixel ink | 0.2676 | 0 | 0.5000 | 1.0000 |

AUC 0.7034 against the fragment-wide 0.709: the pipeline reads ink (pre-registered bar 0.65). So the compression
in A comes from the sample. A likely reason, not tested here: on ink-containing 64 px patches, 57.6% of whose pixels
are ink, the task is to place ink within a dense text region, and the detector's output is a 4×4 grid per window,
upsampled; across the fragment, much of the signal is whether a window holds text at all.

## C. Keeping the draw's ink-free patches lets F1 separate them

Finding 86's option "add ink-free patches back", on the loop's own draw: all **400** patches of the seed-42 sample,
of which **97** contain ink (the loop keeps only those), **1,638,400** pixels, prevalence **0.1397**, all-ink F1
**0.2451**. The incumbent's probabilities on the 97 ink-containing patches reproduce the loop's (checked in the
script).

| predictor | val_f1 | margin over all-ink | ROC AUC | AP lift |
|---|---:|---:|---:|---:|
| loop incumbent (`best_model.pt`) | 0.2493 | **+0.0042** | 0.5717 | 1.1437 |
| detector, each patch's own 64 px window | 0.3106 | **+0.0655** | 0.6665 | 1.6449 |
| every pixel ink | 0.2451 | 0 | 0.5000 | 1.0000 |

The detector's margin is above +0.03 and the incumbent's is not, so by the pre-registered rule **keeping the
ink-free patches lets the loop's F1 tell a model of the detector's quality from the incumbent.** On this sample
the incumbent would store 0.2493, the bar would be 0.2793 with AP lift above 1.02, and the detector clears both
(0.3106, lift 1.6449).

## What this means

These are the owner's decisions (finding 86, item 4); none was taken here.

* **As configured, the loop cannot promote even a model as good as the project's detector.** Its bar is 0.0263
  above the all-ink F1 on a sample where that detector reaches +0.0010 (+0.0062 tiled). Cycles that do not move the
  incumbent's score by 0.03 are the expected outcome whatever they change.
* **Of finding 86's three options, only keeping the ink-free patches separates the two models here.** On the
  97-patch sample the margin over the floor separates them by 0.0046 and AUC by 0.0174. On the 400-patch draw the
  margin separates them by 0.0613 and AUC by 0.0948.
* **If adopted, it is a new protocol:** the incumbent must be re-scored (its stored 0.7273 is not comparable).
  `F1_NOISE_TOLERANCE` (0.03) was measured on 2026-07-12 under protocol v1 (incumbent 0.468; run-to-run sigma
  0.0120). It has not been measured where val_f1 sits near 0.25–0.31, so `scripts/f1_noise_probe.py` should be run
  under the new protocol before the 0.03 is trusted.

## Caveats

* The detector's epoch was chosen by AUC on Fr143, the loop's validation fragment, so its numbers lean
  optimistic. That strengthens A (even an optimistic detector does not clear the floor) and weakens the
  detector's margins in B and C as estimates of an unbiased model.
* One sample seed, one detector checkpoint, one loop checkpoint. Pixels within a patch are not independent; no
  significance is claimed.
* Not done: the protocol change itself, a re-score under it, and the noise probe. No loop or GPU state was touched.
* The incumbent's numbers in A were recomputed on CPU without autocast. They agree with the GPU re-score
  (`reevaluate_best_model.py`, autocast on: val_f1 0.727323, AUC 0.5615, AP lift 1.0787) within 1e-5 in val_f1
  and 1e-4 in AP lift.
