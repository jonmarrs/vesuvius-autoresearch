# GP-Winner Phase 2 — Tractable-Subset TimeSformer Retrain — Design

**Date:** 2026-06-20
**Status:** approved (design); pending spec review
**Depends on:** Phase 1 (`2026-06-19-gp-winner-replication-design.md`) = **Outcome A** (the published pipeline reproduces legible ink here).

## Problem & motivation

Phase 1 proved the *published* winning pipeline produces legible ink in this
environment, so our loop's chance-level result is an **upstream data/label/recipe
gap**, not an environment bug. The natural next validation, before diffing our own
data against the winner's, is to confirm **we can train the winner's recipe here on
real labeled Scroll-1 segments and have it learn ink**. A faithful full reproduction
is infeasible: the winner trains on **41 segments, 30 epochs, batch 196** — ~740 GB
of layers and multi-GPU/days — against our **267 GB free / single 24 GB RTX 4090**.
So Phase 2 is a deliberately *tractable subset* retrain: enough to answer "can the
reference recipe learn ink in our environment on real data," not to reach their SOTA.

## Goal

Train the winner's `TimeSformer` recipe on a small set of real labeled Scroll-1
segments (held-out validation) and demonstrate it **learns ink** — validation pixel
discrimination clearly rising above chance across epochs. This confirms we can
reproduce the *training* (not just inference), gating the Phase-3 controlled diff
that swaps in our own PHercParis2 data/labels.

## Scope

- **Train segments (5, labeled ∩ downloadable ∩ in the winner's default train list):**
  `20231210121321` (already downloaded), `20230702185753`, `20230826170124`,
  `20230903193206`, `20231005123336`.
- **Held-out validation segment (1):** `20230820203112` (labeled → AUC computable).
- **Layers:** 17–42 (`start_idx=17 end_idx=43 in_chans=26`), per the script — same
  subset Phase 1 downloaded.
- **Disk:** ~6 segments × ~18 GB ≈ 108 GB (fits 267 GB free).
- **Compute fit:** `train_batch_size=32` (down from 196; VRAM-verified by a smoke),
  `epochs=12` (down from 30). Single 4090, hours→~day. Checkpoint per epoch.

Out of scope: swapping in our PHercParis2 data/labels (**Phase 3**, controlled diff);
the ResNet3D / I3D ensemble; reaching the winner's full SOTA accuracy.

## Architecture & components

Isolation preserved: **vendored code is not edited**; the loop's `.venv` is never used.

1. **`repro/gp_winner/train_subset.py`** — a *copy* of
   `villa/ink-detection/train_timesformer_og.py` with only the `CFG`/dataset config
   changed: the train fragment-id list (the 5 above), `valid_id=20230820203112`,
   `train_batch_size=32`, `valid_batch_size=32`, `epochs=12`, and
   `comp_dataset_path` pointing at `villa/ink-detection/` so it reads
   `train_scrolls/<id>/layers/<17..42>.tif`. Keeping it a copy makes the diff small,
   reviewable, and leaves the winner's file pristine. Run with the existing
   `villa/ink-detection/.venv-gp` (Phase-1 env; torch 2.12 cu130, `cuda True`).
2. **Data download** — fetch layers 17–42 + mask for the 5 missing segments via the
   per-file `rclone copyto` approach proven in Phase 1 (public `registeredusers:only`).
3. **`prepare.py`** (vendored) — inject `all_labels/<id>_inklabels.png` into each
   `train_scrolls/<id>/` folder (training reads `*inklabels.*` per segment).
4. **Evaluation** — after training, run the Phase-1 `inference_timesformer.py` with
   the *best epoch checkpoint* on the held-out `20230820203112`, then
   `repro/gp_winner/render_eval.py --label all_labels/20230820203112_inklabels.png`
   for pixel-AUC + a thumbnail. Also read the per-epoch validation metric the trainer
   already logs.

## Data flow

1. Reuse `.venv-gp`; download the 5 missing segments (layers 17–42 + masks).
2. `prepare.py` → inject inklabels into the 6 segment folders.
3. Write `repro/gp_winner/train_subset.py` (CFG diff); VRAM smoke (≤5 steps) to confirm
   `batch=32` fits — reduce if it OOMs.
4. Pause the autoresearch loop (free GPU).
5. Run `train_subset.py` (12 epochs, checkpoint per epoch); watch the per-epoch val
   metric climb.
6. Inference + `render_eval.py` on held-out `20230820203112` with the best checkpoint
   → pixel-AUC + thumbnail.
7. Restart the loop. Record the verdict in `FINDINGS.md` + a memory file.

## Success criteria

- **Primary:** held-out validation pixel discrimination is **clearly above chance and
  rises across epochs** — the model demonstrably learns ink from real segments+labels
  in our environment. (A flat ~0.5 curve = failure → reproduction/compute problem.)
- **Secondary / stretch (expected weaker than the winner's SOTA at this reduced
  scope):** held-out pixel-AUC ≳0.7 and a partially legible held-out render.
- A written verdict in `FINDINGS.md` + memory, with the held-out thumbnail under
  `reports/`.

## Risks & mitigations

- **VRAM OOM at batch 32** → 5-step smoke first; drop to 16/8 (optionally grad-accum)
  until it fits the 4090; record the used batch.
- **From-scratch on only 5 segments / 12 epochs may under-reach legibility** → success
  is framed as *learning signal* (rising val above chance), not SOTA; legibility is a
  stretch. If the curve is promising but short, note that more segments/epochs would
  extend it (Phase 3+ / larger run).
- **Disk** (~108 GB) → fits; download only layers 17–42; monitor `df`.
- **Label-injection mismatch** (`prepare.py` naming) → after `prepare.py`, verify each
  `train_scrolls/<id>/` has an `*inklabels.*` the trainer's `glob` finds.
- **Training-time dep quirks** (lightning 2.0.9, `warmup_scheduler`) → the `.venv-gp`
  already ran inference; if a training-only import breaks, pin/resolve in `.venv-gp`
  (never the loop's `.venv`).
- **Runtime** → checkpoint per epoch; an early stop still yields the best-so-far model
  and a usable verdict.
- **GPU contention with the loop** → loop paused for the whole training run; restarted
  after.
