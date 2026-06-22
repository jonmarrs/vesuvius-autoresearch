# GP-Winner Phase 3a — Our Data Through the Proven Pipeline — Design

**Date:** 2026-06-21
**Status:** approved (design); pending spec review
**Depends on:** Phase 2 (`2026-06-20-gp-winner-phase2-retrain-design.md`) = **PASS** (the winner's recipe trains here and learns ink; held-out AUC 0.905 on real Scroll-1 segments).

## Problem & motivation

Phases 1–2 proved our environment and compute can both **run** and **train** the
published winning recipe to strong held-out results. So the autoresearch loop's
chance-level result is **not** an environment/compute/library problem — it is the
**data + recipe**. Phase 3a runs the *proven* winner pipeline on **our** data and
labels — the exact `PHercParis2Fr47` (train) → `PHercParis2Fr143` (holdout) split the
loop uses — to localize the gap with a single controlled experiment.

The two pipelines label *different physical papyrus*, so we cannot cross our labels
onto the winner's volume or vice-versa. The cleanest separable cut is therefore: hold
the **model + recipe + training code constant** (the winner's, now proven) and swap in
**our data + our labels**.

## Goal

Determine whether a known-good recipe learns ink from **our** fragments + labels:

- **High held-out AUC (≫chance)** → our data/labels are fine; the gap is our **model /
  training code** (`resenc_unet`, our `scripts/training/train.py`). Next: fix our trainer.
- **Chance AUC** → our **data/labels** are the problem. Phase 3b sub-divides
  (label quality/alignment vs volume normalization).

Either outcome localizes the gap to one side of the data/model boundary.

## Scope

- **Train fragment:** `PHercParis2Fr47`. **Held-out:** `PHercParis2Fr143`. (Mirrors the
  loop's split exactly; one training fragment is thin but is the controlled comparison.)
- **Layers:** the winner's loader reads indices 17–42 (`start_idx=17 in_chans=26`); our
  fragments hold layers `16.tif`–`48.tif` (the 33-layer middle slab), so `17.tif`–`42.tif`
  exist and map directly.
- **Recipe:** identical to Phase 2 — TimeSformer, batch 32, 12 epochs, single 4090,
  CSVLogger, from scratch.

Out of scope: Phase 3b sub-isolation (label vs volume), gated on a chance outcome; any
change to our loop / `train.py`; pretraining/warm-start (held from-scratch for a clean
recipe comparison).

## Critical adaptation: data conversion

Our `surface_volume/*.tif` are **uint16 + ZSTD-compressed**. The winner's loader uses
`cv2.imread(path, 0)`, which **returns `None`** on our files (`OpenCV TIFF: ZSTD
compression support is not configured`). The winner's own segment layers are 8-bit.
PIL *does* read our ZSTD uint16 tifs (the SegFormer repro relied on this). So Phase 3a
needs a converter, and its normalization is itself a candidate gap factor — documented
and logged.

**`repro/gp_winner/convert_fragment.py`** — for a fragment `<F>`:
- For each layer index `i` in 17–42: PIL-read `local_data/<F>/surface_volume/{i:02}.tif`
  (uint16), normalize **uint8 = (uint16 >> 8)** i.e. a global `// 256` scale (documented
  choice; the loader's existing `clip(0,200)` then applies), and write a **cv2-readable
  8-bit** TIFF to `villa/ink-detection/train_scrolls/<F>/layers/{i:02}.tif`. Verify
  re-readability with `cv2.imread(...,0)` (must be non-None, dtype uint8).
- Copy `local_data/<F>/inklabels.png` → `train_scrolls/<F>/<F>_inklabels.png` and
  `local_data/<F>/mask.png` → `train_scrolls/<F>/<F>_mask.png` (the winner loader globs
  `*inklabels.*` and reads `{id}_mask.png`).
- Log per-layer min/max before/after conversion (audit trail for the normalization
  variable).

`PIL.Image.MAX_IMAGE_PIXELS = None` to bypass the decompression-bomb guard on large
fragments.

## Architecture & components

Isolation preserved: vendored `villa/ink-detection/` files are **not edited** (copy +
edit); the loop's `.venv` is **never used** (reuse `.venv-gp`).

1. **`repro/gp_winner/convert_fragment.py`** — the converter above (uses `.venv-gp`:
   PIL, numpy, tifffile/cv2). CLI: `--frag <id>` (run once per fragment).
2. **`repro/gp_winner/train_ours.py`** — a copy of the proven
   `repro/gp_winner/train_subset.py` with only the fragment lists changed:
   `get_train_valid_dataset` default → `['PHercParis2Fr47','PHercParis2Fr143']`, and the
   module-level `fragments=['PHercParis2Fr143']` (held-out fold). Everything else
   (batch 32, epochs 12, single-GPU, CSVLogger, no `log_image`) identical to Phase 2.
3. **Evaluation** — `inference_timesformer.py` on held-out `PHercParis2Fr143` with the
   best checkpoint, then `repro/gp_winner/render_eval.py
   --label train_scrolls/PHercParis2Fr143/PHercParis2Fr143_inklabels.png` → pixel-AUC +
   thumbnail. Compare the held-out AUC to (a) chance 0.5, (b) our loop's ~0.56, (c) the
   Phase-2 0.905 reference.

## Data flow

1. Reuse `.venv-gp`. Convert both fragments (`convert_fragment.py --frag PHercParis2Fr47`,
   then `PHercParis2Fr143`) into `train_scrolls/`.
2. Verify each `train_scrolls/<F>/` has 26 cv2-readable 8-bit layers + `<F>_inklabels.png`
   + `<F>_mask.png`.
3. Write `train_ours.py` (fragment-list diff only).
4. Pause the loop (free GPU).
5. Train (12 epochs; checkpoint per epoch; watch per-epoch train/val loss).
6. Held-out inference on `PHercParis2Fr143` + `render_eval.py` → AUC + thumbnail.
7. Restart the loop. Record the verdict in `FINDINGS.md` + a memory file.

## Success criteria

This is a **diagnostic** experiment — both outcomes are informative; the deliverable is
a clear, evidence-backed verdict, not a target AUC:

- Conversion produces cv2-readable 8-bit layers (the pipeline ingests our data at all).
- Training runs to completion; per-epoch loss recorded.
- Held-out pixel-AUC on `PHercParis2Fr143` measured and interpreted against 0.5 / 0.56 /
  0.905:
  - **≫0.5 (e.g. ≳0.75):** data/labels fine → gap is our model/training code.
  - **~0.5–0.56:** data/labels implicated → Phase 3b.
- Written verdict in `FINDINGS.md` + memory, with the held-out thumbnail under `reports/`.

## Risks & mitigations

- **uint16→uint8 normalization fidelity** — `//256` is a documented, simple global map;
  per-layer min/max logged. If the converted 8-bit data is near-empty after the loader's
  `clip(0,200)` (e.g. our intensities concentrate in a different range), that is itself a
  finding (our data needs different normalization) → note it and, in Phase 3b, try a
  percentile/`clip`-matched map. The chosen mapping is part of "our setup," reported
  honestly.
- **cv2 cannot read our source tifs** (ZSTD) — the whole reason for the converter; the
  converter writes plain (uncompressed/LZW) 8-bit tifs and verifies `cv2.imread` non-None.
- **RAM** — 2 fragments (1 train + 1 holdout) ≤ Phase 2's 3-segment ~16 GB footprint; fits
  the 31 GB box. Monitor `free` during the data-read.
- **One training fragment is thin** — intentional (mirrors the loop). The question is
  binary (does a proven recipe beat chance on our data?), not SOTA; a thin-but-real
  train set still answers it. If the result is ambiguous, a second fragment can be added
  in a follow-up.
- **Runtime** — fewer steps/epoch than Phase 2 (one smaller train fragment); checkpoint
  per epoch; stop early once the held-out trend is unambiguous.
- **GPU contention** — loop paused for training/inference, restarted after.
- **Label/mask shape mismatch** — verify `inklabels.png`/`mask.png` match the fragment
  H×W before training (our fragments are aligned `(depth,H,W)`; Fr47/Fr143 are the known-good
  pair).
