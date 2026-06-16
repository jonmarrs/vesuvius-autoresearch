# Is ink learnable at 0.5 mm? A reproducible study of the Vesuvius prize's hallucination window

**A fresh model memorizes ink patches trivially, yet cannot learn ink from a full
fragment at 64 px — while the same training regime fits a synthetic CT-derived
target to 0.99 AUC almost immediately. So direct supervised ink detection is
learnability-limited by the 64 px window, not by model capacity, data, compute,
augmentation, or optimization.** This report documents the experiments and
controls behind that conclusion, with commands to reproduce each.

---

## 1. The question, and why it is binding

The Vesuvius Challenge prize rules cap the predictive context a model may use: a
prediction for a pixel may depend on at most a **≤ 64 × 64 px neighborhood at 8 µm
resolution (~0.5 mm)**, with no overlap between training and prediction regions.
This "hallucination window" exists to prevent a model from inventing letters from
long-range priors rather than reading them from the CT.

The rule is binding because the approaches that win at ink detection lean on large
spatial context. The 2023 Grand-Prize-winning TimeSformer operates at a 256 px
context; retrained at 64 px it loses its advantage. So a *prize-compliant* detector
must extract ink from a 64 px patch. This study asks the prior question directly:
**is that signal there to be learned at all?**

## 2. Method and rigor

Three choices make the results trustworthy:

- **Pooled pixel AUC is the honest metric.** On ink-rich patches (~60 % ink), a
  near-constant predictor scores Dice ≈ 0.75, so Dice and `val_bpb` are
  artifact-saturated — they do not prove a model localizes ink. We report pooled
  pixel-level ROC-AUC over a fixed patch sample (0.5 = chance), computed by
  `scripts/pixel_auc.py`.
- **Leak-free held-out splits.** The held-out fragment (PHercParis2 Fr143) is split
  into spatially-disjoint "unlabeled" (U) and validation (V) regions separated by a
  **128 px buffer**, so no 64 px patch can straddle the boundary or share receptive
  field (`scripts/spatial_split_mask.py`).
- **Fresh-init controls.** Where a clean measurement is needed, the production
  checkpoint is moved aside so models train from random init — no warm-start
  leakage. A gated `eval_every_steps` hook logs the pixel-AUC learning curve during
  training.

## 3. The evidence chain

Each experiment rules out a different explanation for the ceiling.

**Large context is forbidden, not just unhelpful (TimeSformer, LeJEPA).** The
GP-winning TimeSformer, retrained at the 64 px window, reaches only per-patch AUC
~0.49 train / ~0.56 val — it needs the 256 px context the rule forbids. A
self-supervised LeJEPA checkpoint is likewise unusable as a 64 px initializer: it
was pretrained at a large input window, so only ~20 % of its encoder tensors are
shape-compatible at 64 px. Large-context transfer is off the table by construction.

**More same-scroll data does not help (pseudo-label + oracle).** Training a fresh
model on Fr47 and measuring the held-out V-region gives pooled pixel AUC ~0.49.
Self-training on confidence-filtered pseudo-labels of the U-region is futile — the
pseudo-labels score AUC 0.502 against ground truth (chance). Crucially, an *oracle*
trained on the U-region's **true** labels reached only 0.50 on the V-region — no
lift. Adding real, same-scroll supervision did not move the needle.

**More compute does not help (12 h schedule).** A single fresh model trained for
12 hours on one continuous schedule produces a **flat** pooled pixel-AUC curve:
twelve hourly probes oscillate within 0.508–0.525, with no upward trend from hour 1
to hour 11. Training longer is not a lever.

**Capacity and pipeline are fine (overfit probe).** A fresh model handed a fixed
batch of 16 ink patches with no augmentation drives train pixel AUC from 0.42 to
**1.0 in 100 steps** and holds it. The architecture can perfectly represent a
CT→ink mapping, and the loss/optimizer pipeline is sound — memorization is trivial.

**Augmentation is not the bottleneck (ablation).** Two fresh arms — full production
augmentation vs augmentation fully disabled — both land near chance: 0.522 train /
0.490 val with augmentation, 0.509 train / 0.525 val without. Removing augmentation
did not let the model fit even its own training data. Neither arm learned ink.

**The decisive control: the regime fits a learnable target instantly.** The
augmentation arms left one confound — the overfit probe used a high learning rate on
a fixed batch, while the full-dataset arms used the production rate (5e-5). To
separate "the 64 px ink signal is too weak" from "the optimization regime is wrong,"
we trained the **identical regime** (full Fr47, lr 5e-5, mini-batch sampling, no
augmentation) on a *synthetic, definitely-learnable* target — each pixel labeled by
whether its z-averaged CT intensity exceeds the patch mean. It reached pooled AUC
**0.97 by step 50 and 0.99 by step 300**, while real ink stalls at ~0.51 under the
exact same settings. The regime fits a CT-derived per-pixel target near-instantly.
Ink's failure to fit is therefore not optimization, learning rate, capacity,
pipeline, or augmentation — it is that ink is not recoverable from the 64 px CT
patch the way a simple intensity feature is.

## 4. Verdict and honest scope

At the 0.5 mm / 64 px window, **ink is not a learnable function of the CT patch for
direct supervised detection with this preprocessing.** Capacity, pipeline, data
quantity, compute, augmentation, and the optimization regime are each ruled out by a
control; the binding constraint is the window itself.

The scope is deliberately narrow. This is **not** a claim that no method can read
ink at 0.5 mm — a different input representation, better surface
segmentation/flattening upstream, or a fundamentally different objective might
surface signal this pipeline cannot. It is a claim about *direct supervised pixel
detection from 64 px flattened CT*, the prize-compliant regime, measured honestly.

One number invites a caveat: a long-running search loop's production checkpoint
reaches ~0.557 pixel AUC. That is not a fresh-trainable signal — it is accumulation
across many warm-started cycles, and it sits only marginally above the chance floor
the fresh experiments establish.

The practical implication: the remaining levers are **outside model accuracy at
64 px** — a larger predictive window (which the hallucination rule forbids for the
prize), or better upstream segmentation/flattening so that more ink signal lands
inside a compliant patch in the first place.

## 5. Reproduce

```bash
# capacity/pipeline — can a fresh model memorize a tiny ink set? (expect ~1.0)
PYTHONPATH=. python scripts/overfit_probe.py --target real --k 16 --steps 2000

# the decisive control — does the production regime fit a learnable target? (expect ~0.99)
PYTHONPATH=. python scripts/control_fulldata_probe.py --steps 300 --eval-every 50

# the leak-free held-out spatial split (128 px buffer, disjoint regions)
PYTHONPATH=. python scripts/spatial_split_mask.py \
  --mask local_data/PHercParis2Fr143/mask.png \
  --out-u /tmp/u.png --out-v /tmp/v.png --axis 1 --fraction 0.5 --buffer 128
```

Pooled pixel AUC is computed by `scripts/pixel_auc.py`; the in-training learning
curve is logged by the `eval_every_steps` hook in `scripts/training/train.py`. The
augmentation kill-switch is the `disable_augmentation` config flag.

## 6. Links

- Full honest results / methodology / negative results: [FINDINGS.md](../FINDINGS.md)
- Repository (MIT): https://github.com/jonmarrs/vesuvius-autoresearch
- Tooling: `scripts/overfit_probe.py`, `scripts/control_fulldata_probe.py`,
  `scripts/spatial_split_mask.py`, `scripts/pixel_auc.py`
