# Clean-Room 2.5D SegFormer Ink-Detection Reproduction — Design

**Date:** 2026-06-18
**Status:** approved
**Goal:** Reproduce a known-successful Vesuvius ink-detection method (the Kaggle
2023 1st-place 2.5D SegFormer recipe, single-model) on the canonical Kaggle
fragments, to establish a **working ink detector** — held-out-fragment pixel AUC
≥ 0.75 and visually legible ink — as a baseline reset before pursuing SOTA and
then our own contributions.

## Context & reconciliation

Our prior arc concluded direct supervised ink detection is learnability-limited at
the prize's 64 px window. But others demonstrably read ink and won prizes, so the
likeliest explanation is that *our approach* differs from what works, not that ink
is undetectable. The Kaggle 1st-place recipe ([ryches writeup](https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection/writeups/ryches-1st-place-solution))
differs on three axes that all matter: **2.5D** (a shallow 3D-conv stem over the
depth stack, then max-over-z collapses depth into feature channels — depth
invariant), **large spatial context** (big tiles into a SegFormer that predicts at
lower resolution and upscales), and **SegFormer**, not a from-scratch ResEnc at
64 px. This reproduction tests the working approach directly.

The work is a **clean-room** build (own dir, modern deps) — deliberately isolated
from our `train.py` pipeline, which has a history of silent bugs. If the clean-room
recipe detects ink and our pipeline doesn't, that localizes the problem to our
pipeline, not the task.

## Prerequisite (needs the user)

The canonical Kaggle "Ink Detection" fragments are **not local** and there is no
`kaggle` CLI installed. Acquiring them needs the user's Kaggle account/API token
(`kaggle competitions download -c vesuvius-challenge-ink-detection`, after
accepting the rules) **or** a direct download URL from the ScrollPrize data mirror.
Expected layout per fragment: `surface_volume/` (65 `.tif` depth layers),
`inklabels.png` (binary ink), `mask.png` (papyrus vs background). Target location:
`local_data/kaggle_ink/{1,2,3}/`. This is step 0; nothing else can run without it.

## Architecture (minimal, clean-room)

Input is a tile of shape `[B, 1, D, H, W]` (D = middle depth layers).

1. **3D-conv stem** — ~4 `Conv3d` layers (1 → 16 → 32 → 32 → C, BN + ReLU),
   preserving H×W, then **max over the depth axis** → `[B, C, H, W]`. This is the
   1st-place "3D conv then max across z; depth replaced by feature dims",
   depth-invariant.
2. **2D segmenter** — `smp.Segformer(encoder_name="mit_b3", in_channels=C,
   classes=1, encoder_weights="imagenet")` (verified to build in the installed
   smp 0.5.0; ImageNet-pretrained mit-b3 encoder, first conv adapted for C
   channels).
3. **Head** — bilinear upsample logits to the tile H×W.

Defaults (configurable): D = 32 middle layers (z 16–48 of 0–64), C = 32, tile
224×224, stride 112. Loss = BCE + Dice (the multi-class nothing/papyrus/ink
variant is an optional refinement, out of scope for the first confirmation).

## Data flow & components

Each unit is independently testable.

- **`dataset.py`** — given a fragment dir, lazily reads the middle D `.tif` layers,
  tiles the masked surface into `tile×tile` windows (stride = tile/2), returns
  `(volume_tile [1,D,H,W], ink_tile [1,H,W], papyrus_mask_tile)`. Only tiles with
  sufficient papyrus coverage are sampled. Per-layer min-max or mean/std
  normalization. Unit-testable on a synthetic tiny fragment.
- **`model.py`** — the stem + `smp.Segformer` module above. Unit test: forward a
  `[2,1,32,224,224]` tensor → `[2,1,224,224]` logits.
- **`train.py`** (repro-local, not the loop's) — leave-one-fragment-out: train on
  two fragments, validate on the held-out third. AdamW + cosine, AMP, BCE+Dice,
  geometric augs (flips/rot90/scale; hand-rolled or `albumentations` if installed).
- **`infer.py`** — sliding-window inference over a full held-out fragment with
  overlap-averaging and flip/rot90 **TTA**, producing a full-resolution ink
  probability map.
- **`evaluate.py`** — pooled pixel AUC + Fβ(0.5) at a swept threshold over the
  held-out fragment, and a rendered **ink-prediction PNG** (probability heatmap +
  thresholded) for visual legibility.

Lives under `repro/ink_segformer/`. Reuses the existing `.venv` (smp 0.5 + timm
1.0 present); add `albumentations` only if used (augs can be hand-rolled to avoid
the dep). No import of, or change to, `scripts/training/train.py` or the loop.

## Success criterion

- **Quantitative:** held-out-fragment pooled **pixel AUC ≥ 0.75** (0.5 = chance;
  a single non-ensemble SegFormer clears this comfortably when the pipeline is
  correct). Fβ(0.5) reported for comparison to the public leaderboard.
- **Qualitative:** the rendered ink prediction is **visually legible** — strokes /
  letter-like structure visible on the held-out fragment, not noise.

Meeting both = "we can actually detect ink with a proven recipe," and the reset
has succeeded. Failing both *on canonical data with this recipe* would instead
point at the environment/data, which is itself diagnostic.

## Reconciliation check (secondary, after success)

Once the model works, evaluate it (or a variant) under a restricted ~64 px
receptive context on the same data to confirm our earlier negative result was the
window/approach, not impossibility — closing the loop honestly. Out of scope if
time-constrained.

## Operational / safety

- Training/inference need the RTX 4090 → pause the autoresearch loop during runs
  (`.loop_paused` + kill PIDs; verify GPU free via `nvidia-smi`; restart after).
- Fully independent of the loop and `best_model.pt`; only writes under
  `repro/ink_segformer/` and `local_data/kaggle_ink/`.

## Testing

- `dataset` tiling + normalization on a synthetic tiny fragment (shapes, mask
  gating, label alignment).
- `model` forward shape test.
- A short overfit smoke (a handful of tiles → train pixel AUC → ~1.0) proving the
  clean-room pipeline can learn — the same probe discipline that served the prior
  arc.

## Out of scope

- The full 9-model ensemble / 2-stage 1st-place system (single model first).
- Integrating SegFormer into the autoresearch loop or `train.py`.
- Scroll-segment inference / the 0.5 mm prize-window constraint (this is the
  unconstrained "can we detect ink at all" reset).
- Multi-class output, the surface-detection competition.
