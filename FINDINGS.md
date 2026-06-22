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

## Honest current results

Production model: `resenc_unet`, evaluated on held-out `PHercParis2Fr143`
(disjoint from the `PHercParis2Fr47` training fragment).

| Metric | Value | Note |
| --- | --- | --- |
| `val_bpb` | 0.2627 | 1 − Dice at the Dice-optimal threshold |
| `centerline_dice` | ~0.30 | at the topology-optimal threshold; up from 0.198 |
| `skel_dist` | ~19.8 | prize gate is 2.0 — large remaining headroom |
| ink AUC (train Fr47) | 0.74 | per-patch ink-vs-background discrimination |
| ink AUC (val Fr143) | 0.61 | 0.5 = chance |

This is a mediocre-but-improving detector, stated plainly (over the recent cycle
window: train AUC 0.70→0.74, val 0.60→0.61, `centerline_dice` 0.198→0.30). The
contribution is the reproducible, evidence-gated search process and the tooling
around it — not a state-of-the-art model.

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
submission. It quantifies exactly what the 64 px window costs.

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
  - *The GP-winning TimeSformer at the 64 px prize window* reaches only AUC
    ~0.49 train / ~0.56 val. Its strength needs the 256 px context that the
    Challenge's 0.5 mm (~64 px) hallucination window forbids; at 64 px a CNN
    that emits full-resolution per-pixel output is the better fit.
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
