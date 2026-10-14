# The loop's validation sample cannot reward a model that reads ink (finding 88)

**2026-10-13.** Four read-only measurements, each **pre-registered**: its reading rule was committed before it ran.
They ran on CPU, one thread, at the lowest priority, beside the running loop. Scripts and outputs:

| measurement | script | committed before the run | output |
|---|---|---|---|
| A. the loop's 97-patch sample | `scripts/detector_on_loop_sample.py` | `5b5c4e2a` (run at `b8a8fff3`) | `reports/detector_on_loop_sample.json` |
| B. control: random windows | `scripts/detector_random_window_control.py` | `fe76e853` | `reports/detector_random_window_control.json` |
| C. the 400-patch draw, ink-free patches kept | `scripts/detector_on_full_v2_sample.py` | `c59cfa86` | `reports/detector_on_full_v2_sample.json` |
| D. A and C scaled by the loop candidates' spread | `scripts/loop_candidate_spread.py` | `19aed905` (run at `54256700`) | `reports/loop_candidate_spread.json` |

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

## D. Scaled by the spread of the loop's own candidates, C still separates far better

A and C compare gaps with the fixed tolerance 0.03. What a gap is worth depends on how far apart the loop's
ordinary candidates score, and that spread could differ between the samples. `scripts/snapshot_loop_candidates.sh`
copied each cycle's `last_model.pt` before the next cycle overwrote it. The first **10** snapshots
(`candidate_20261013-155821` to `candidate_20261013-182407`, none excluded) were scored on both samples. The spread
is the SD of their 10 scores; the gap is detector minus incumbent from A and C above.

| metric | sample | gap | spread (SD of 10 candidates) | gap / spread |
|---|---|---:|---:|---:|
| val_f1 | A | 0.0046 | 0.0017 | **2.78** |
| val_f1 | C | 0.0613 | 0.0057 | **10.71** |
| ROC AUC | A | 0.0174 | 0.0037 | 4.76 |
| ROC AUC | C | 0.0948 | 0.0072 | 13.14 |
| AP lift | A | 0.0206 | 0.0061 | 3.37 |
| AP lift | C | 0.5013 | 0.0284 | 17.63 |

The rule: C separates better if its val_f1 ratio is at least twice A's, and A separates better if the reverse
holds. 10.71 ≥ 2 × 2.78 = 5.55, so **C separates a detector-quality model from the loop's ordinary candidates
better, and finding 88's recommendation stands.** ROC AUC and AP lift were reported but not part of the rule; they
point the same way. Checks passed: each candidate reproduces the val_f1 the loop stored within 3.4e-6 (the bar was
1e-3); the incumbent reproduces A and C; the sample has 97 ink-containing patches.

| snapshot | config change | A val_f1 | margin over incumbent | C val_f1 | margin over incumbent | C threshold | C share called ink | promoted under C? |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `20261013-155821` | loss_ink_bce=0.4, lr=0.0005 | 0.7289 | +0.0016 | 0.2623 | +0.0129 | 0.10 | 0.65 | no |
| `20261013-161428` | lr=0.0001 | 0.7269 | −0.0004 | 0.2538 | +0.0045 | 0.10 | 0.50 | no |
| `20261013-163045` | aug_mode=batchgeneratorsv2, lr=0.0005 | 0.7324 | +0.0051 | 0.2717 | +0.0224 | 0.10 | 0.82 | no |
| `20261013-164705` | dropout=0.2, lr=0.0005 | 0.7294 | +0.0021 | 0.2653 | +0.0160 | 0.10 | 0.63 | no |
| `20261013-170319` | lr=0.001 | 0.7295 | +0.0022 | 0.2621 | +0.0127 | 0.10 | 0.61 | no |
| `20261013-171939` | batch_size=16, lr=0.0005 | 0.7287 | +0.0013 | 0.2645 | +0.0151 | 0.10 | 0.62 | no |
| `20261013-173544` | loss_fiber_bce=0.1, lr=0.0005 | 0.7294 | +0.0021 | 0.2629 | +0.0136 | 0.10 | 0.63 | no |
| `20261013-175154` | lr=0.0001 | 0.7262 | −0.0012 | 0.2527 | +0.0034 | 0.10 | 0.48 | no |
| `20261013-180802` | batch_size=8, lr=0.0005 | 0.7296 | +0.0023 | 0.2674 | +0.0180 | 0.10 | 0.60 | no |
| `20261013-182407` | lr=0.0005, ridge_sigma=2.0 | 0.7296 | +0.0022 | 0.2643 | +0.0150 | 0.10 | 0.66 | no |

The config change is relative to the incumbent's stored config (`lr` 0.000125, `depth_band` unset). Every
candidate also sets `depth_band` [1, 27], left out of the table.

Not pre-registered, from the same run:

* **None of the 10 would be promoted under C.** Their margins run from +0.0034 to +0.0224 against a bar of
  +0.03. Adopting C would not, on these candidates, have promoted anything by itself.
* **All 10 score above the incumbent under C** (mean +0.0134); under A, 8 of 10 do (mean +0.0017). Under C every
  candidate's best threshold is 0.10, and it calls 48–82% of pixels ink. The incumbent's is 0.05, and it calls
  96%. The two `lr=0.0001` candidates, trained at the lowest learning rate, have the two smallest C margins.
  So the loop's cycles move the model off "call everything ink" in a way that A does not register. This is one
  candidate per config, so no config effect is claimed, and the candidates remain weak: ROC AUC 0.57–0.59 under C.
* The tolerance 0.03 is 17.9 times the candidates' val_f1 spread under A and 5.2 times it under C.

## What this means

These are the owner's decisions (finding 86, item 4); none was taken here.

* **As configured, the loop cannot promote even a model as good as the project's detector.** Its bar is 0.0263
  above the all-ink F1 on a sample where that detector reaches +0.0010 (+0.0062 tiled). Cycles that do not move the
  incumbent's score by 0.03 are the expected outcome whatever they change.
* **Of finding 86's three options, keeping the ink-free patches separates the two models by far the most.** On the
  97-patch sample the margin over the floor separates them by 0.0046 and AUC by 0.0174. On the 400-patch draw the
  margin separates them by 0.0613 and AUC by 0.0948. Measured against the spread of the loop's own candidates (D),
  the val_f1 gap is 10.71 SDs on the 400-patch draw against 2.78 on the 97-patch sample.
* **If adopted, it is a new protocol:** the incumbent must be re-scored (its stored 0.7273 is not comparable).
  `F1_NOISE_TOLERANCE` (0.03) was measured on 2026-07-12 under protocol v1 (incumbent 0.468; run-to-run sigma
  0.0120). It has not been measured where val_f1 sits near 0.25–0.31, so `scripts/f1_noise_probe.py` (made
  protocol-aware in #57; it only plans unless told to run) should be run under the new protocol before the 0.03 is
  trusted. D's candidate spread is no substitute: it mixes config differences with noise. On D's 10 candidates the
  new protocol would have promoted none.

## Caveats

* The detector's epoch was chosen by AUC on Fr143, the loop's validation fragment, so its numbers lean
  optimistic. That strengthens A (even an optimistic detector does not clear the floor) and weakens the
  detector's margins in B and C as estimates of an unbiased model.
* One sample seed, one detector checkpoint, one loop checkpoint (ten in D). Pixels within a patch are not independent; no
  significance is claimed.
* D's spread mixes the candidates' config differences with run-to-run noise (each cycle draws a fresh
  training-order seed), and every candidate warm-starts from the same checkpoint. It is not the identical-config
  noise probe and not a basis for a tolerance: `train.py` records that an earlier cross-tweak "upper bound"
  understated the true noise.
* 8 of D's 10 candidates (from `20261013-163045` on) trained while these CPU jobs ran beside the loop, at 0.21–0.25
  Mvps against 0.29–0.30 before, so with fewer training steps than an undisturbed cycle. Both samples score the same
  candidates, so the comparison of A with C is paired; the absolute spreads may differ from an undisturbed loop's.
* A `--n 1` smoke run of D's script was stopped before it scored any candidate (disclosed in `54256700`). D's
  numbers come from its one full run.
* Not done: the protocol change itself, a re-score under it, and the noise probe. No loop state or GPU was touched,
  but the CPU jobs slowed the loop's training (above).
* The incumbent's numbers in A were recomputed on CPU without autocast. They agree with the GPU re-score
  (`reevaluate_best_model.py`, autocast on: val_f1 0.727323, AUC 0.5615, AP lift 1.0787) within 1e-5 in val_f1
  and 1e-4 in AP lift.
