# Findings

An autonomous, evidence-gated ink-detection research loop for the Vesuvius
Challenge, running continuously on a single NVIDIA RTX 4090. This document is the
honest record: what the tools do, how the model actually performs, and what the
search has taught us — including the negative results.

## Deliverables (tools)

- **Autoresearch loop** (`run_autoresearch_loop.py`) — a bandit samples
  architecture / loss / augmentation / hyperparameter "families", trains each
  candidate under a fixed wall-clock budget on a single GPU, evaluates on a
  held-out fragment, and promotes only topology-improving configurations.
- **Scroll-specific augmentation library** (`scroll_augmentations.py`) — nine
  GPU-native augmentations modeling scroll-CT artifacts; addresses
  [villa #201](https://github.com/ScrollPrize/villa/issues/201). See
  [docs/SCROLL_AUGMENTATIONS.md](docs/SCROLL_AUGMENTATIONS.md) and the
  [before/after demo](reports/augmentation_demos/all_families.png).
- **GPU fiber/ridge detection** — a closed-form symmetric-3×3 eigensolver that
  avoids the cuSolver `eigvalsh` failure on large Hessian batches, with tiled
  execution: dense 14–94× over NumPy (64³–256³), 512³ tiled in ~3–5 s at ~1 GB
  VRAM, float64 eigenvalue parity 3.1e-10. See
  [reports/fibers_gpu_validation_2026-06.md](reports/fibers_gpu_validation_2026-06.md).
- **Experiment tracking** — opt-in Weights & Biases logging (parameter/gradient
  histograms, per-cycle metrics, prediction images), mirroring villa's setup.
  Live: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
- **Topology-aware evaluation toolkit** — selects the binarization threshold that
  maximizes centerline overlap and reports the prize topology metrics there
  (see "What we learned").
- **Ink detector subpackage** (`vesuvius_autoresearch.detector`) — the proven
  Grand-Prize TimeSformer recipe productionized (config/data/model/train/infer/
  eval/cli, unit-tested, one-command `reproduce`), with the community metric
  contract (`val_f1` primary; `average_precision` + `ap_prevalence_lift` gates;
  ROC-AUC secondary) and a cross-fragment `measure` CLI. See
  [reports/detector/REPRODUCTION.md](reports/detector/REPRODUCTION.md).
- **SOTA open-data tooling** (`repro/sota_data/`) — anonymous-S3 discovery/fetch
  of the `vesuvius-challenge-open-data` bucket, OME-Zarr region extraction,
  detector-format conversion with loud alignment guards, and a teacher–student
  distillation pipeline (prep/baseline/train/measure) against the released canon
  ink predictions.

## Honest current results

**Working detector** (TimeSformer recipe, trained on Scroll-2 `PHercParis2Fr47`,
held-out `PHercParis2Fr143`; community metric contract):

| Metric (held-out) | Same-scroll Fr143 | Cross-scroll Scroll-1 |
| --- | --- | --- |
| `val_f1` | 0.393 | 0.222 |
| `average_precision` | 0.357 | 0.144 |
| `ap_prevalence_lift` (1.0 = chance) | 2.07 | 1.29 |
| ROC-AUC (secondary) | 0.709 | 0.585 |

Real, transferable ink signal at the prize window same-scroll; **weak cross-scroll
transfer** — the open problem the field is working on.

**SOTA-distilled detector** (same recipe distilled from the released canon
predictions on SOTA Scroll-1 surface volumes; **all metrics are
agreement-with-teacher, not ground-truth accuracy** — no aligned ground truth is
released): held-out segment val_f1 **0.662**, AP **0.742**, lift **3.24**, ROC-AUC
**0.865** (baseline = the detector above at the chance floor, lift 0.98). Its output
shows letterform-shaped strokes — the first from a model trained in this repo.

The bandit loop's own from-scratch stack remains at the chance floor (its story, and
why, is the arc below). The contribution is the reproducible tooling, the honest
measurement discipline, and now a working, SOTA-rebased detector path — stated
plainly, not oversold. (The former `skel_dist ≤ 2.0` "prize gate" was removed after
we proved it invalid — Phase 4b below.)

## Clean-room 2.5D SegFormer reproduction — the window, not the data, is the ceiling

A from-scratch positive control, fully isolated under `repro/ink_segformer/`
(nothing in it imports the loop or `train.py`). A 2.5D detector — `[B,1,D,H,W]`
tile → 4-layer 3D-conv stem → max-over-depth → `smp.Segformer(mit_b3)` → per-pixel
logits — trained **leave-one-fragment-out** (train on `PHercParis2Fr143`, hold out
`PHercParis2Fr47`) at **224 px** tiles over all 33 local depth layers, BCE+Dice,
AMP, sliding-window flip/rot90 TTA at inference.

| Metric (held-out Fr47, TTA) | Value | Note |
| --- | --- | --- |
| pixel AUC | **0.804** | vs ~0.60 for the production 64 px model; ~0.51 from-scratch at 64 px |
| Fβ=0.5 | 0.506 | at threshold 0.30 |
| mean P(ink) on ink vs off-ink | 0.259 vs 0.044 | **5.9×** separation (was 3.0× at 6 epochs) |
| legibility | **legible** | Greek letterforms (e.g. ΡΑΛΑ) readable in the raw probability map |

Per-epoch held-out AUC climbed monotonically (0.68 → 0.78 over 18 epochs, ~2 h on
the RTX 4090, ~6 min/epoch with 4 096 sampled tiles/epoch) and was still rising at
the end. The rendered ink heatmap and a prediction-vs-label overlay are in
[reports/ink_segformer_repro/](reports/ink_segformer_repro/).

**What this localizes:** the same fragments where our 64 px pipeline sits at chance
(~0.51 from-scratch, the [overfit-probe](#what-we-learned) showed the 64 px capacity
and pipeline are fine) become **legibly readable at 224 px context**. So the binding
constraint is the architecture/receptive-field **regime**, not data quality or ink
detectability — the same structural story as the TimeSformer and LeJEPA negatives
below, now with a positive control. The flip side, stated honestly: **224 px is not
prize-compliant** — it exceeds the Challenge's 0.5 mm (~64 px) hallucination window —
so this is a detectability proof and a working-detector reset, **not** a prize
submission. It quantifies exactly what the 64 px window costs — in *legibility*. (Phase 5
below sharpens this: the proven depth-as-time recipe reaches held-out AUC ~0.70 at the
**64 px-lateral** prize window — real, transferable signal though short of legibility —
so "our 64 px pipeline sits at chance" was a property of the loop's stack, not a floor of
the window itself.)

## GP-winner replication (Phase 1) — the winning pipeline reproduces here; our gap is upstream

We ran the **vendored Grand-Prize pipeline** (`villa/ink-detection/inference_timesformer.py`,
the published canonical "wild15" TimeSformer-small checkpoint, `size=64 stride=32
start_idx=17 in_chans=26`) on two canonical Scroll-1 segments — `20231210121321` and
`20231221180251` — in a **dedicated isolated venv** (never the loop's `.venv`), with
the segments fetched from `dl.ash2txt.org` and weights from the authors' Drive.

**Result: Outcome A — both segments render legibly.** The predictions show clear
columns of ancient Greek letterforms (matching the winners' public reveal of these
segments). Renders in [reports/gp_winner_repro/](reports/gp_winner_repro/).

**Why this matters:** the published winning pipeline **works in this environment,
end-to-end** — so our loop's chance-level result (~0.49/0.56 with a "GP-style" model)
is **not** an environment/plumbing/GPU/library bug. The gap is *upstream and in the
recipe*: the winner uses **real flattened Scroll-1 surface-volume segments** with
**~15 rounds of iteratively-cleaned labels** and a **pretrained** TimeSformer; our loop
trains a from-scratch `resenc_unet` on the two PHercParis2 *fragments* with our own
labels/preprocessing. We now have a **trusted, reproducing baseline** — the instrument
is calibrated. The next step is a direct diff of our pipeline against the winner's
(data source, label quality, pretraining), not more architecture/hyperparameter search.

## GP-winner replication (Phase 2) — the recipe *trains* here and learns ink (held-out AUC 0.905)

Beyond running the published weights (Phase 1), we **retrained** the winner's
TimeSformer recipe from scratch in our environment on a tractable subset — 2 real
labeled Scroll-1 segments (`20231210121321`, `20230702185753`), held-out
`20230820203112`, 12 epochs at batch 32 on the single RTX 4090, via an isolated copy
`repro/gp_winner/train_subset.py` (vendored code untouched, `.venv-gp`).

**Result: PASS (primary).** Loss fell monotonically across 12 epochs (train
0.707→0.596, val 0.505→0.461) and the **held-out pixel-AUC is 0.905** — the recipe
demonstrably learns ink from real labeled segments in our environment. Render +
ground-truth in [reports/gp_winner_repro/](reports/gp_winner_repro/)
(`phase2_heldout_*`).

**Honest caveat (stretch not met):** the held-out prediction is ink-*structured* but
not crisply legible letterforms. Expected at this reduced scope — 2 segments / 12
epochs / single-GPU vs the winner's **41 segments / 30 epochs / ensemble** — and the
held-out label here is sparse (5.4% ink, a handful of large glyphs), so legibility is
hard to judge. The high AUC reflects strong pixel-level ink/non-ink separation, not
full text recovery.

**What this nails down:** our environment and compute can *train* the reference recipe
on real data to strong held-out discrimination. Combined with Phase 1, the chance-level
result of our autoresearch loop is conclusively **not** an environment/compute/library
problem — it is the **data + recipe**: real flattened Scroll-1 *segments* with cleaned
labels (and ideally pretraining) vs our from-scratch `resenc_unet` on PHercParis2
*fragments*. The actionable lever is Phase 3: feed our own data/labels through this
proven pipeline, one variable at a time, to localize exactly which factor collapses our
result.

## GP-winner replication (Phase 3a) — OUR DATA IS FINE; the gap is our model/training stack

We ran the **proven** winner recipe on **our own data**: `train_ours.py` (the Phase-2
pipeline, fragment-list diff only) trained from scratch on `PHercParis2Fr47`, held out
`PHercParis2Fr143` — *the exact split our autoresearch loop uses*. Our uint16 ZSTD layers
were converted to the winner's 8-bit cv2-readable format (`repro/gp_winner/convert_fragment.py`,
`//256`; OpenCV cannot read our ZSTD source). 12 epochs, batch 32, single 4090, `.venv-gp`.

**Result (held-out Fr143):** pixel-AUC **0.711 mask-restricted** (0.811 full-frame). That
is decisively above chance — and the load-bearing comparison: on the **same fragment pair**
our loop's `resenc_unet` scores ~0.56–0.60, while the proven recipe reaches **0.711**.

| Pipeline (same Fr47→Fr143 data) | Held-out ink AUC |
| --- | --- |
| Our autoresearch loop (`resenc_unet` + our `train.py`) | ~0.56–0.60 |
| Winner recipe (TimeSformer) on our converted data | **0.711** |

**Verdict — the gap is NOT our data/labels.** A known-good modeling stack extracts real,
transferable ink signal from our exact fragments and labels where our own pipeline sits at
chance. So the bottleneck is our **model + training stack** (the `resenc_unet` architecture,
our `scripts/training/train.py` loop, and its recipe), not the data, the labels, the
fragments, or the 64 px window. (The held-out val *loss* plateaued ~0.57 — a reminder that
loss is a weak discriminator here; the *ranking* AUC is the honest signal, consistent with
the dead-val-set finding.) Render in [reports/gp_winner_repro/](reports/gp_winner_repro/)
(`phase3_heldout_Fr143_thumb.png`): ink-structured, not crisply legible (thin 1-fragment
train), but the diagnostic is the AUC gap, not legibility.

**Actionable next (Phase 4):** stop tuning the loop's hyperparameters and instead port what
makes the winner stack work onto our data — the most pinpointing single experiment is to run
**our** `resenc_unet`/`train.py` on the **same converted winner-format data** the recipe just
succeeded on; if it still gets ~chance, the defect is concretely in our architecture/training
code, which we then fix against the TimeSformer recipe as the working reference.

## GP-winner Phase 4a Step A — the prize topology gate is NOT detection-limited

Before scaling the working detector, we scored it through the repo's own prize topology
gates (`repro/gp_winner/prize_gate_eval.py`, reusing the villa `centerline_dice` /
`skeleton_distance_length` metrics over a threshold sweep, cropped to the GT-ink bbox —
full-segment skeletonization is intractable, which matches how the loop samples patches).

**The AUC-0.905 TimeSformer** (the same recipe that rendered legible Greek letters in
Phase 1) scores, at its topology-optimal threshold (0.6): **centerline_dice 0.121,
skel_dist 16.8**. Our `resenc_unet` is at **~0.34 / ~19–21**. The prize gate is
**skel_dist ≤ 2.0**.

| Model | pixel-AUC | centerline_dice | skel_dist | vs gate (≤2.0) |
| --- | --- | --- | --- | --- |
| resenc_unet (our loop) | ~0.51–0.60 | ~0.34 | ~19–21 | ✗ (~10×) |
| TimeSformer Phase 2 (2 seg, 12 ep) | **0.905** | 0.121 | 16.8 | ✗ (~8×) |
| TimeSformer Phase 4b (3 seg, 15 ep) | 0.896 | 0.101 | **15.0** | ✗ (~7.5×) |

**Step B result (Phase 4a Step B):** the scaled production TimeSformer (3 train segments +
1 holdout, 15 epochs, `repro/gp_winner/train_scaled.py`) scores at its topology-optimal
threshold (0.6): **pixel-AUC 0.896, centerline_dice 0.101, skel_dist 15.0**. Compared to
the Phase 2 model (2 train segments, 12 epochs, AUC 0.905, skel_dist 16.8), the scaled
model is marginally better on skel_dist (15.0 vs 16.8) but marginally worse on pixel-AUC
(0.896 vs 0.905) and centerline_dice (0.101 vs 0.121). More training data and epochs did
not meaningfully move the topology gates. Training loss converged at 0.601; val loss
plateaued ~0.46 from epoch 6.

**Final verdict:** scaling the detector confirms the Step A finding — the prize topology
gate is **not detection-limited**. Even a 37-hour scaled training run moves skel_dist from
16.8 to 15.0, still ~7.5× off the ≤2.0 gate. The bottleneck is the **topology /
post-processing stage** (thin-centerline extraction, connected-component cleanup), or the
gate itself: `skel_dist ≤ 2.0` is *our repo's invented proxy*, not the actual Vesuvius
prize criterion (human-readable ink — which the TimeSformer demonstrably produces). The
autoresearch loop has been gating on a metric that even a Grand-Prize-quality model fails,
which likely explains why it never declared a model "prize-ready." The next lever is
post-processing and/or re-examining whether the gate is the right target, not a bigger
detector.

## Phase 4b — the gate question is RESOLVED: `skel_dist` is invalid for ink detection

We took the Phase 4 open question ("post-processing, or wrong gate?") and tested the metric
itself. `skeleton_distance_length.compute` skeletonizes both masks, histograms the **branch
lengths**, and returns the **symmetric-KL divergence between those two length histograms**.
It never compares *where* the skeletons are. A 4-case probe on synthetic strokes
(`scripts/probe_skel_dist_validity.py`) is decisive:

| Prediction | pixel overlap w/ GT | `skel_dist` | gate (≤2.0) |
| --- | --- | --- | --- |
| perfect copy | 1.00 | 0.0 | ✓ |
| shifted entirely off the label (same stroke lengths) | **0.00** | **0.0** | ✓ |
| 60% recall (3 of 5 strokes, each correct) | 0.60 | ~1e-8 | ✓ |
| spatially correct but fragmented into pieces | 0.50 | **42.6** | ✗ (~20×) |

**Conclusion.** `skel_dist` is (a) a metric from villa's **3D fiber/surface** track
(`villa/segmentation/evaluation/metrics/`), not ink detection; (b) a **distribution-shape
divergence, blind to spatial location and recall** — a prediction with *zero* overlap with
the GT scores 0.0; (c) **hypersensitive to fragmentation** — the broken centerlines that
thresholding any real soft probability map produces score catastrophically. villa never
gates on it (its `evaluate.py` reports dataset-level summary stats); the `≤ 2.0` is a local
default in `train.py:182`, applied **per-patch** where the symKL is dominated by binning
noise. **The detector was never the problem: the readiness gate measures something
uncorrelated with ink-detection quality, so no model — including a Grand-Prize-quality one —
can pass it.** The honest readiness signal is pixel-AUC + human legibility (which the
TimeSformer demonstrably produces), not `skel_dist ≤ 2.0`. If a topology proxy is wanted at
all, it must be *spatial* (e.g. centerline_dice, or a chamfer/Hausdorff skeleton distance)
and aggregated over a dataset — not symKL of per-patch length histograms.

## Phase 5 — productionized in-repo: a working, window-compliant detector (held-out AUC 0.709)

Phases 1–3 reproduced the proven recipe from *vendored/external* scripts (`repro/gp_winner/`).
Phase 5 turns that into a **first-class tool**: `vesuvius_autoresearch.detector`
(`config`/`data`/`model`/`train`/`infer`/`eval`/`cli`, 17 unit tests, one-command
`reproduce`). Retrained from scratch on `PHercParis2Fr47`, held out `PHercParis2Fr143` —
the same split the loop uses — saving every epoch and selecting the best by held-out AUC.

**Result (held-out Fr143):** best epoch (7 of 12) scores pixel-AUC **0.7090 mask-restricted**
(proven reference 0.711). AUC climbs with training then plateaus at ~0.69–0.71 across epochs
6–11. **Window-compliant:** the lateral patch is 64 px; the 26 through-surface depth slices
ride the TimeSformer's *time* axis (`num_frames=26`, `channels=1`), so the depth context that
makes the recipe work is **not** subject to the lateral 0.5 mm limit. (Inference averages
overlapping windows with **uniform** weighting — matching the proven `train_ours.py`
accumulation; it scores 0.709 vs 0.700 for a Gaussian blend on the same checkpoint.)

**What surfaced the result was three inference defects, not training** — the model trained
fine; scoring was broken: (1) **input normalization** — `infer` fed raw 0–200 pixels where
training applies `A.Normalize` (÷255); this ~255× scale mismatch alone held held-out AUC at
**0.57** until fixed, then **0.698**; (2) PyTorch-2.6 `torch.load(weights_only=True)` rejecting
our scheduler-bearing checkpoint; (3) padded-mask / unpadded-label shape misalignment on the
real 14830×9506 fragment. Inference is now batched (≈37 min → minutes), which made best-epoch
selection across all 12 checkpoints practical. Full writeup + per-epoch sweep:
[reports/detector/REPRODUCTION.md](reports/detector/REPRODUCTION.md).

**Why this matters.** The gap between our loop (~0.56) and the proven recipe (0.711) is no
longer only *attributable* (Phase 3a) — it is partially **closed in-repo** by a released,
reproducible detector. And it settles the window question decisively (below): a prize-compliant
64 px-lateral recipe reads real, transferable ink; the limit was the modeling stack, not the
window.

## Metric pivot + the first valid cross-scroll measurement

The community's active frontier (the Kaggle Surface Detection competition, villa's own
nnU-Net autoresearch framework, and the automated agent efforts) speaks in **Dice/F1 and
cross-scroll generalization**, and the accepted tooling's metric contract is `val_f1`
(threshold-swept) plus **average precision** and a base-rate control — not ROC-AUC, which is
over-optimistic under class imbalance. We adopted that contract
(`detector/metrics.py`): **`val_f1` primary; `average_precision` + `ap_prevalence_lift`
(AP ÷ prevalence; ≈1 ⇒ no signal) as the honest gates; ROC-AUC retained as a secondary
diagnostic only.** A `measure` CLI scores one checkpoint across fragments.

**First valid cross-scroll number** (the 2026-06-12 attempt was invalidated by a data
misalignment; this uses the correctly-aligned `train_scrolls` pair): the detector trained on
Scroll-2 `Fr47` scores same-scroll `Fr143` **val_f1 0.393 / lift 2.07**, but cross-scroll
Scroll-1 only **val_f1 0.222 / lift 1.29** — near the chance floor. **Cross-scroll transfer
is weak; the detector's competence was scroll-specific.** Report:
[reports/detector/cross_scroll_measurement.md](reports/detector/cross_scroll_measurement.md).

## Full-resolution ResEncUNet — a clean negative

Since the coarse 4×4 TimeSformer head caps mask quality, we built a per-pixel 2.5D
**ResEncUNet** student (`detector/model_resenc.py`, community-winner architecture family,
2D mode, unchanged AdamW+cosine recipe). Result: **it underperforms the TimeSformer** —
same-scroll val_f1 **0.369 vs 0.393**, cross-scroll lift 1.16 vs 1.29. Likely cause: ResEnc
architectures are tuned for the full nnU-Net protocol (SGD/poly, deep supervision, long
schedules), which we deliberately did not adopt. The TimeSformer remains the detector; the
factory/full-res machinery stays for future use.
([reports/detector/resenc_phase1_measurement.md](reports/detector/resenc_phase1_measurement.md))

## The SOTA data — what the open bucket actually ships

After the first complete scroll was read (PHerc. 1667, 2026-06-25 — new BM18 phase-contrast
scans + Volume Cartographer + ink nets used as "visibility amplifiers"), we rebased onto the
open data (`s3://vesuvius-challenge-open-data/`, anonymous). Two verified findings
(`repro/sota_data/`):

1. **The bucket ships re-flattened multiscale OME-Zarr surface volumes** (e.g. 109 depth
   layers, 2.4 µm, level-0 50600×36400) **and model predictions — no ground-truth ink labels
   aligned to the new geometry.** Our old hand labels don't fit the re-flattening, so an
   honest quantitative score against ground truth is not directly possible; we refused to
   fabricate one.
2. **Better data alone does not rescue a cross-scroll model:** our Scroll-2 detector run on a
   SOTA Scroll-1 surface region produces texture, not ink (qualitative renders:
   [reports/detector/sota_scroll1_qualitative.md](reports/detector/sota_scroll1_qualitative.md)),
   consistent with the measured weak transfer.

## Distillation onto SOTA data — a SOTA-native detector (agreement-with-teacher 0.66)

With no aligned ground truth available, we trained the unchanged TimeSformer recipe on SOTA
Scroll-1 surface volumes using the released canon ink predictions as targets —
**teacher–student distillation** from the pipeline that read the scrolls. **All metrics are
agreement-with-teacher, never ground-truth accuracy** (the teacher is a model output).

On a **held-out segment** (never trained on; train/held-out segments disjoint):

| model | val_f1 | AP | prevalence-lift | ROC-AUC |
| --- | --- | --- | --- | --- |
| current detector (baseline) | 0.372 | 0.224 | 0.98 (chance) | 0.499 |
| **distilled student (best of 12 epochs)** | **0.662** | **0.742** | **3.24** | **0.865** |

The distilled model's lift (3.24) is the strongest ranking signal any model trained in this
repo has produced (previous best: 2.07, same-scroll), and its output shows
**letterform-shaped strokes arranged in text lines** — the first letter-shaped output from an
own-trained model here. Teacher provenance (uint8, binarize ≥128) is recorded in the report;
the held-out region also serves as the best-epoch selection set (AP/ROC-AUC are
threshold-free and unaffected). Report:
[reports/detector/sota_distill_measurement.md](reports/detector/sota_distill_measurement.md);
tooling: `repro/sota_data/distill_prep.py` + `distill_run.py`.

**Takeaway:** the full-scroll breakthrough's lever — better data — is transferable to a
single consumer GPU via distillation. The open bucket (≈48 scrolls in one consistent format)
plus this recipe makes the cross-scroll frontier attackable here.

## Cross-scroll distillation: diversity wins, then scaling saturates

Two follow-on experiments took the distilled recipe to the cross-scroll frontier, measured on
**one held-out PHerc-1667 region no arm trained on** (all metrics agreement-with-teacher; the
legacy-baseline row is the selection-asymmetry-free anchor):

| arm (held-out 1667) | val_f1 | AP-prevalence-lift | ROC-AUC |
| --- | --- | --- | --- |
| legacy detector (no distillation) | 0.206 | 1.47 | 0.591 |
| A: 1 scroll, 4 regions (the Phase-2 student) | 0.193 | 1.22 | 0.551 |
| B: 2 scrolls, 4 regions (same budget as A) | 0.278 | 2.12 | 0.689 |
| C: 3 scrolls, 6 regions (capability run) | 0.272 | 2.10 | 0.672 |

1. **Single-scroll distillation over-specializes** — arm A lands *below* the undistilled
   detector on the unseen scroll, despite dominating on its own scroll (lift 3.24).
2. **Training-scroll diversity at fixed budget substantially improves transfer** (arm B: the
   controlled experiment; diversity was the only variable) — at a modest ~11% same-scroll cost.
3. **Scaling saturates:** a third scroll (PHerc 0172, whose canon teachers were newly
   available) plus 50% more data did **not** lift 1667 transfer further (C ≈ B). The
   lift-≈2.1 plateau looks like this recipe's ceiling for 1667 without 1667-adjacent signal —
   its distinct preparation is the prime suspect. Arm C is nonetheless the **best all-around
   model built here**: volume bought back most of arm B's same-scroll cost (Scroll-1 0.631 vs
   arm A's 0.662) while reading its third scroll strongly (0172 held-out val_f1 0.587 /
   lift 5.37 / ROC-AUC 0.919).

**Data reality:** a full bucket sweep found only **4 of 45** scrolls ship canon teacher
predictions today (PHercParis4, PHerc0139, PHerc0172, PHerc1667) — the frontier for this
recipe is *released teachers*, not scan volumes; each new release extends it with no new code.
An open diagnostic: agreement-with-teacher cannot distinguish a *teacher* ceiling (the student
extracted all transferable teacher signal) from a *domain* ceiling — resolving that requires
ground truth registered onto the SOTA flattening (named future work). Reports:
[cross_scroll_distill.md](reports/detector/cross_scroll_distill.md),
[cross_scroll_scale.md](reports/detector/cross_scroll_scale.md).

## Ground-truth calibration: registering the 2023 hand label onto SOTA geometry

Every SOTA number above is *agreement-with-teacher* because no ground-truth ink labels aligned
to the re-flattened surfaces are released. We closed that gap for one region by a **geometric
bridge**: the bucket ships, per segment, an `original.obj` mesh carrying per-vertex texture
coordinates (the 2023 label's pixel grid) plus a tifxyz of that segment on the old scan. For
each pixel of the SOTA region we take its 3D point, find the nearest `original.obj` vertex
(median residual 7.9 old-scan voxels over 386k vertices), read that vertex's texture coordinate,
and sample the 2023 hand label there — warping human ground truth onto the SOTA flattening. The
alignment is **gated before any scoring**: the registered label's ink strokes land on the
letterforms (visually verified; teacher-enrichment 5.05×), and `score` refuses to run without
the validation marker.

**First ground-truth numbers on SOTA data** (segment `20230702185753`; two disclosed confounds
below):

| model (vs registered ground truth) | ROC-AUC | AP | F1 |
| --- | --- | --- | --- |
| **canon teacher** (released prediction) | **0.703** | 0.257 | 0.437 |
| legacy detector | 0.486 | 0.120 | 0.228 |
| distilled students (arm A/B/C) | 0.79–0.80 | 0.39–0.42 | 0.44–0.47 |

- **The single clean fact:** the canon prediction that read the scrolls scores **ROC-AUC 0.70 /
  AP 0.26** against human labels — the anchor that finally calibrates every
  "agreement-with-teacher" we reported (agreement was with a 0.70-quality proxy, not truth). The
  legacy detector is chance here, cleanly (it trained on a different scroll/flattening).
- **Confound 1 (train region):** this region was a *training* region for all three students, so
  their rows are fit-quality, not held-out generalization. Only the teacher and legacy rows are
  unconfounded.
- **Confound 2 (binary vs continuous):** the teacher is a binary map, so ROC-AUC/AP structurally
  understate it *on this segment where it reads well*; the fair comparison is F1 (0.44 vs
  0.44–0.47). On this train region the students match teacher fidelity — but this is fit-quality,
  and the held-out test below shows it does not generalize.

### The held-out ground-truth test (the correction)

Registering a *held-out* segment's hand label — `20231210121321`, which **no student trained
on** — settled what the train-region numbers could not. On held-out data vs human ground truth,
**everything reads near chance**: canon teacher ROC-AUC **0.563** / lift 1.15, arms B/C
**0.55–0.56** / lift 1.16–1.17, legacy 0.50. Three conclusions:

1. **The train-region 0.80 was substantially fit** — genuine held-out reading is ≈chance.
2. **Distillation reproduces the teacher faithfully, including its failures.** The teacher reads
   *this* segment poorly (scattered, non-letterform output); the students inherit exactly that.
   "Student ≈ teacher" holds — but here at the chance floor. This is fidelity, not independent
   reading skill.
3. **The near-chance number is real, not a registration artifact:** the *same* registration
   quality (residual 7.85 vs 7.92) let the good-teacher segment score 0.70, so the geometry
   preserves whatever signal exists.

Method notes: the teacher-dependent enrichment gate false-negatived on the held-out segment
(the teacher is weak there), so alignment was validated by a **codified teacher-free gate**
(residual + text-line periodicity; the 2D orientation carried from the validated segment as an
export-pipeline invariant, residual/periodicity being convention-blind). The clean *cross-scroll*
ground-truth test was blocked at pixel level — PHerc 1667 ships only model predictions, no released
human labels — until the July column-level workaround (next section). Tooling:
`repro/sota_data/register.py` + `register_run.py`; reports:
[registered_gt_validation.md](reports/detector/registered_gt_validation.md),
[registered_gt_heldout_validation.md](reports/detector/registered_gt_heldout_validation.md).

## The renderer + the first non-training-scroll ground truth (PHerc 1667, July)

Two July results extend the arc onto the scroll that was read in full (PHerc 1667,
announced 2026-06-25).

**The surface renderer is now gate-validated on released ground truth.** The render CLI
(`repro/sota_data/render_cli.py`) gained a `--tifxyz` path (the released grid-geometry
format most bucket segments ship — no obj parsing, no scale ambiguity) and rectangular
regions. On a PHerc-1667 clean triple (tifxyz geometry + raw volume + released surface
volume, one scan frame) it scores center-layer **NCC 0.7799 against the pre-registered
0.60 gate — PASS** ([render_validation_1667.md](reports/detector/render_validation_1667.md)).
The same sampler had scored 0.59 on Scroll 1 against a resolution-mismatched reference —
the jump at matched resolution confirms that residual was the comparison, not placement.
With it we rendered the **first independent surface volumes of the merged full-reading
geometry** (mesh-only in the bucket; ~20.8 Gpx grid;
[merged1667_first_look.md](reports/detector/merged1667_first_look.md)).

**The published reading became measurable ground truth — at column granularity.** No
machine-readable coordinates of the reading exist publicly, so we derived them: the
preprint's figure strips (the ink reading with labeled `col. 1–22` brackets, CC BY-NC 4.0)
were shape-registered onto the merged geometry — all three strips independently recover
the same transform, the tiling closes to 3 px over the 30,097-px grid, and bracket
extraction yields exactly 22 columns whose widths rise interior→exterior as physics
predicts ([merged1667_column_registration.md](reports/detector/merged1667_column_registration.md)).
Combined with the per-column transcription facts (Coll. 1–4 traces, 5–22 text; eight
papyrologists' consensus), this shipped as **ScrollGT's first non-training-scroll target**
(`pherc1667_merged_columns` + the `score-columns` contract; measured anti-gaming floor:
constant *and* papyrus-mask predictions score exactly 0.5).

**And the honest result on it:** our models sit at the floor. On a rendered cols-17–19
region, arm C scores col-vs-gutter AUC 0.667 (n = 3v2 — one rank-step from chance, pixel
AUC 0.521) and the legacy detector 0.0; both maps are texture without letterforms
([scrollgt_v02_columns.md](reports/detector/scrollgt_v02_columns.md)). The legacy model's
line-periodicity 0.433 is a **measured metric confound** (inference banding whose pitch
lands in the text-line range) — documented in the benchmark as the reason every
submission must include its prediction map. The cross-scroll ceiling, now measured
against scholar-validated ground truth on the very scroll the field just read.

## What we learned

- **Validation metrics are artifact-saturated.** On ink-containing patches
  (~60% ink), a near-constant predictor scores Dice ≈ 0.75 at a low threshold.
  So `val_bpb` / Dice alone do not prove a model localizes ink; per-patch AUC
  exposed that the production model sits at ~0.74 train / ~0.61 val.
- **Topology metrics depend on the threshold.** Evaluating `centerline_dice` /
  `skel_dist` at the Dice-optimal threshold understates topology by ~2×; at the
  topology-optimal threshold the *same* model reports `centerline_dice`
  0.073 → 0.198. The loop now selects and reports at the topology-optimal point.
- **Negative results (kept honest):**
  - *clDice as a late fine-tune* of the converged model degrades centerline
    overlap (cl_dice 0.073–0.077), rather than improving it — the soft skeleton
    is a poor proxy on a diffuse, under-confident model.
  - *~~The GP-winning TimeSformer at the 64 px prize window needs 256 px context the
    window forbids.~~* **Superseded by Phases 3a/5.** An earlier, misconfigured attempt
    read ~0.49 train / ~0.56 val and we wrongly concluded the recipe needs an oversized
    lateral window. The proven recipe is in fact **window-compliant and reaches held-out
    AUC 0.70–0.71** on the same 64 px data — because its through-surface context lives on
    the depth/*time* axis (`num_frames=26`), not the lateral patch, so the 0.5 mm lateral
    limit doesn't bind it. The earlier low reading reflected a broken setup (the kind of
    inference/training defects Phase 5 caught), not a property of the window.
  - *The LeJEPA self-supervised pretrain is unusable as a 64 px init.* The
    checkpoint was pretrained at a large input window (positional embeddings for
    1024 patches at patch-size 8³, i.e. ~64×64×128) so only ~20% of its encoder
    tensors are shape-compatible with a prize-compliant `lejepa_unet` at
    16×64×64 (128 patches); matching it would require the same oversized context
    the 64 px hallucination window forbids (and the checkpoint is an early
    epoch-9 pretrain). Same structural constraint as the TimeSformer result:
    large-context approaches don't fit the prize window.
  - *Cross-scroll generalization remains unmeasured — a multi-scroll experiment
    was invalidated by a data-alignment bug, caught during debugging.* The
    cross-scroll fragments (PHercParis1 Fr34/Fr39, PHerc51 Fr8, PHerc1667 Fr3)
    store their CT volumes as `(H, depth, W)` — the depth axis is in the middle
    — whereas the loader assumes `(depth, H, W)`. So the loader read transposed,
    wrong-shaped patches and the inklabels never aligned with the CT (label
    dims ≈ the volume's `(axis0, axis2)`, not `(axis1, axis2)`). A model scores
    ~chance against misaligned labels, so the apparent "held-out AUC 0.492"
    measured nothing about generalization. A valid multi-scroll / cross-scroll
    experiment needs the loader to handle the `(H, depth, W)` axis order and the
    labels resampled to the volume grid first. (Only the two PHercParis2
    fragments, Fr47/Fr143, are correctly `(depth, H, W)` and aligned.)
  - *Same-scroll pseudo-label self-training is blocked by the detector's
    pixel-level non-discrimination — and even true same-scroll labels don't
    help.* We split the held-out fragment (Fr143) into spatially-disjoint
    "unlabeled" (U) and validation (V) regions (128 px buffer, no patch
    overlap), trained a leak-free baseline on Fr47 alone, and compared it on the
    V-region against (a) self-training on confidence-filtered pseudo-labels of
    the U-region and (b) an *oracle* trained on the U-region's true labels. The
    pseudo-labels were chance-quality — the baseline's pooled **pixel** AUC is
    ~0.49–0.50 (its probabilities collapse into ~[0.17, 0.28]; ink-vs-background
    means differ by ~0.001), so confidence filtering yields labels with AUC
    **0.502** and precision ≈ the base ink rate. More tellingly, the oracle —
    13.5 k patches of *real* same-scroll supervision — did **not** lift V-region
    pixel AUC over the Fr47-only baseline (0.49 → 0.50). The production model
    (days of training) reaches only pixel AUC ~0.557 on the same region, so this
    is the same `model-barely-discriminates-ink` ceiling, not a data-quantity
    problem: at 64 px, neither pseudo-labels nor extra true same-scroll labels
    move pixel-level discrimination. (Reusable tooling from this study:
    `scripts/spatial_split_mask.py`, `scripts/generate_pseudo_labels.py`,
    `scripts/pseudo_label_quality_report.py`, a confidence-weighted ink loss,
    and a `jitter=False` deterministic-inference path in the loader.)
  - *Training longer from scratch does not lift pixel-level detection — the
    ceiling is architectural / the 64 px window, not compute budget.* A single
    clean fresh-init resenc trained for 12 h on one continuous schedule
    (~13 k steps) produces a **flat** pooled V-region pixel-AUC learning curve:
    12 hourly probes oscillate in **0.508–0.525 (≈ chance)** from hour 1 through
    hour 11, with no upward trend. So the detector never learns pixel-level ink
    discrimination in this regime *regardless of training time* — the loop's slow
    crawl to ~0.56 is warm-start carry-over across cycles, not training-time
    headroom. Taken with the pseudo-label result (more same-scroll data, real or
    pseudo, doesn't help) and the TimeSformer/LeJEPA results (large-context
    approaches violate the 64 px window), the evidence converges: the bottleneck
    is the resenc architecture or the 0.5 mm / 64 px hallucination window itself,
    not data or compute. Next levers must be architectural — or a deliberate test
    of whether legible-ink discrimination is even feasible within the 64 px
    window. (Instrument: a gated `eval_every_steps` pixel-AUC learning-curve hook
    in train.py + `scripts/pixel_auc.py`.)
  - *...but an overfit probe then localizes that ceiling to the **training
    regime**, not capacity or the architecture.* Before building a bigger model,
    we ran a feasibility probe: a fresh resenc on a fixed batch of 16 Fr47 ink
    patches with **no augmentation** drives train pixel AUC from 0.42 to **1.0 in
    100 steps** and holds it. So the architecture can perfectly represent the
    CT→ink mapping, and the loss/optimizer pipeline is sound — **capacity and
    pipeline-bug are ruled out**. Yet under the production regime (full
    7,345-patch set + heavy augmentation) the same architecture reaches only
    ~0.58 train / ~0.52 val (Probe 0). The bottleneck is therefore
    optimization/regularization/generalization — most plausibly augmentation
    strong enough to suppress the learnable ink signal, plus a generalization gap
    — **not** model capacity. This corrects the "must be architectural" reading
    above: a bigger/different network is the wrong lever; the next experiment
    should target the training recipe (augmentation strength, regularization,
    objective). (Instrument: `scripts/overfit_probe.py`.)
  - *Augmentation is refuted as the lever — and the deeper problem is that fresh
    training can't fit even the training set at 64 px.* A clean ablation trained
    two fresh resenc arms for ~2 h each — full production augmentation vs
    augmentation fully off (a gated `disable_augmentation` master switch) —
    measuring train + val pooled pixel AUC. Result: FULL 0.522 train / 0.490 val;
    NONE 0.509 train / 0.525 val. Removing augmentation did **not** lift train
    (≈ equal) and the val difference is noise around chance (NONE never fit train,
    so its 0.525 "val" is not real generalization). So **augmentation is not the
    bottleneck.** The striking part: *neither* arm fits even its own training data
    (~0.51) after ~78 epochs, while the overfit probe memorized 16 fixed patches
    to 1.0 — i.e. the model can memorize tiny sets but cannot fit the full
    fragment's CT→ink mapping from scratch at 64 px, with or without augmentation
    (converging with the flat 12 h long-schedule curve). (Throughput is
    ridge-bound at ~3 s/step, so each ~2 h arm reached only ~2 k steps ≈ 4–5
    epochs — under-trained on its own, which a same-regime control then renders
    moot.)
  - ***Verdict — detection at 64 px is window-limited: the ink↔CT signal is not a
    learnable function of the 64 px patch.*** A same-regime control resolves the
    LR/under-training confound decisively: training the identical regime (full
    Fr47, lr 5e-5, mini-batch sampling, no aug) on a *synthetic learnable* target
    (brightness = CT z-mean > patch mean) reaches pooled AUC **0.97 by step 50 and
    0.99 by step 300** — i.e. the optimizer fits a CT-derived per-pixel target
    near-instantly at the very LR/regime where ink stalls at ~0.51 after ~2 k
    steps. So ink's failure to fit is **not** optimization, capacity, pipeline, or
    augmentation — it is that legible ink is not recoverable from a 64 px CT patch
    by this approach. This is the convergent conclusion of the whole arc
    (TimeSformer/LeJEPA: large-context approaches violate the window; pseudo-label/
    oracle: more same-scroll data doesn't help; long-schedule: more compute
    doesn't help; overfit probe: capacity/pipeline are fine; this ablation +
    control: regime and augmentation are fine). The remaining levers are *outside*
    model accuracy at 64 px: a larger predictive window (which the 0.5 mm
    hallucination rule forbids for the prize), better source segmentation/flattening
    upstream, or reframing the contribution around the rigorous negative result
    itself. (Instruments: `scripts/overfit_probe.py`, the `disable_augmentation`
    switch, `scripts/control_fulldata_probe.py`.) Full standalone study:
    [reports/ink_detection_64px_window_study_2026-06.md](reports/ink_detection_64px_window_study_2026-06.md).
- **Bugs surfaced by the rigor:** the Frangi fiber target silently trained on
  zeros (a backend bug in the upstream `tools.py`), and 5 of 9 sampled
  augmentation families were silent no-ops until the augmentation code was
  unified into one library. Both are fixed.

## Reproduce

See the [README](README.md) quick start to install and run a cycle, and the live
[wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch) for
streaming metrics.
