# Working Detector (TimeSformer) — Design Spec

**Date:** 2026-06-26
**Status:** Approved design (pre-implementation)
**Goal:** Productionize the proven Grand-Prize TimeSformer recipe as a first-class
`detector` subpackage that reliably reproduces a **≥ 0.70 held-out, mask-restricted
pixel-AUC** ink detector on our data — a reproducible, calibrated, prize-window-compliant
artifact.

## Background & motivation

The June-2026 localization arc established that the ink-detection bottleneck is our
**model/training stack**, not the data, environment, compute, or 64 px window (FINDINGS.md
"GP-winner replication" Phases 1–4). The proven reference is the winner's TimeSformer
recipe, which reaches **held-out pixel-AUC 0.711 on our exact Fr47→Fr143 split** where our
loop's `resenc_unet` sits at ~0.56. The currently-working but messy proof lives in three
near-duplicate scripts (`repro/gp_winner/train_ours.py`, `train_subset.py`, `train_scaled.py`).

This project consolidates that proven recipe into one clean, first-class detector
subpackage. **Approach A (faithful core, integrated shell):** preserve the proven training
core behavior-for-behavior, wrapped in clean module boundaries and a config dataclass.

Non-goals (explicit): fixing/repointing the autoresearch loop; pushing to legible text;
zarr-native data loading; unifying with the repo's other TimeSformer wrapper. These are
documented follow-ups, not part of this spec.

## Success criteria (definition of done)

1. A one-command `reproduce` (train on `PHercParis2Fr47`, evaluate held-out
   `PHercParis2Fr143`) achieves **≥ 0.70 mask-restricted pixel-AUC** with a single fixed
   seed. Target = the proven 0.711.
2. Produces a **calibrated binarization threshold** (selected by a threshold sweep), a
   rendered held-out thumbnail, and a JSON scorecard (`pixel_auc`, `threshold`,
   `centerline_dice`) written under `reports/`.
3. **Window compliance** is a first-class, asserted property: lateral patch ≤ 64 px / ≤ 0.5 mm.
4. Fast unit tests pass (tiling shapes, smoke train, compliance assertion, determinism,
   eval-metric sanity).
5. Lives entirely under `src/vesuvius_autoresearch/detector/` (+ tests); the autoresearch
   loop is untouched.

## Architecture

New subpackage `src/vesuvius_autoresearch/detector/`, following the existing `fibers/`
pattern (module files + `cli.py` + `__init__.py`). Each unit has one purpose and a
well-defined interface:

| File | Responsibility | Key interface |
|---|---|---|
| `config.py` | `DetectorConfig` dataclass — replaces the winner's global `CFG`. | `DetectorConfig(...)`, `validate_window()` |
| `data.py` | Tiling + augmentation + `Dataset`. | `build_datasets(cfg) -> (train_ds, valid_ds, valid_xyxys, pred_shape)` |
| `model.py` | `DetectorModel` (Lightning) — TimeSformer, depth-as-time. | `DetectorModel(cfg, pred_shape)` |
| `train.py` | Trainer + checkpointing + seed. | `train(cfg) -> checkpoint_path` |
| `infer.py` | Tiled full-segment inference + Gaussian blending. | `infer(cfg, checkpoint_path, fragment_id) -> prob_map (np.ndarray HxW in [0,1])` |
| `eval.py` | pixel-AUC, calibrated threshold, render, scorecard. | `evaluate(prob_map, label, mask, cfg) -> scorecard dict` |
| `cli.py` | `train` / `infer` / `eval` / `reproduce` entry points. | argparse subcommands |
| `__init__.py` | Public exports. | `DetectorConfig`, `train`, `infer`, `evaluate` |

### `config.py`
`DetectorConfig` dataclass with the proven values as defaults:
`in_chans=26, size=64, tile_size=256, stride=tile_size//8 (=32), start_idx=17,
end_idx=43, train_batch_size=32, epochs=12, lr=3e-5, warmup_factor=10, min_lr=1e-6,
weight_decay=1e-6, max_grad_norm=100, num_workers=16, seed=0`; loss weights
(`dice_w=0.5, bce_w=0.5, bce_smooth=0.25`); augmentation probabilities; data root,
`train_fragment_ids=["PHercParis2Fr47"]`, `valid_fragment_id="PHercParis2Fr143"`,
`model_dir`, `reports_dir`. Plus prize-window fields `max_lateral_px=64`,
`um_per_px=8.0`. `validate_window()` asserts `size <= max_lateral_px` and
`size*um_per_px/1000 <= 0.5 + 1e-9`, raising `ValueError` otherwise. Depth (`in_chans`)
is explicitly the through-surface axis and is *not* subject to the lateral window limit.

### `data.py`
Lifted from `read_image_mask` / `worker_function` / `CustomDataset` with globals removed
and `cfg` injected:
- `read_image_mask(cfg, fragment_id)` — load `train_scrolls/{fragment}/layers/{i:02}.tif`
  for `i in [start_idx, end_idx)` (26 slices), `np.clip(img, 0, 200)`, pad to `tile_size`,
  stack to `(H, W, in_chans)`; load `*_inklabels.png` (→ float /255) and `{frag}_mask.png`.
  The winner's hardcoded fragment-flip ID list is preserved but documented as inert for our
  PHercParis2 fragments (not in the list).
- `build_datasets(cfg)` — 256-tile grid at `stride`, keep tiles fully inside the fragment
  mask; for train, skip all-non-ink tiles; subdivide each 256-tile into 64px subtiles.
  Train subtiles → `CustomDataset`; valid subtiles carry `xyxys` for reassembly.
- `CustomDataset` — train path applies 3D rotate + `fourth_augment` (depth crop/cutout) +
  albumentations; label downsampled to `size//16` (4×4) via `F.interpolate`. Valid path:
  resize/normalize only, returns `(image, label_4x4, xyxy)`.

### `model.py`
`DetectorModel(pl.LightningModule)` — behavior identical to `RegressionPLModel`:
`timesformer_pytorch.TimeSformer(dim=512, image_size=64, patch_size=16, num_frames=26,
num_classes=16, channels=1, depth=8, heads=6, dim_head=64, attn_dropout=0.1,
ff_dropout=0.1)`. `forward` adds a channel axis, permutes `(B,C,T,H,W)->(B,T,C,H,W)`,
runs the backbone, reshapes to `(B,1,4,4)`. Loss `0.5*DiceLoss(binary) +
0.5*SoftBCEWithLogitsLoss(smooth=0.25)`. Validation accumulates per-tile predictions into
a full `mask_pred`/`mask_count` buffer (kept for parity); the artifact's scored prediction
comes from `infer.py`.

### `train.py`
`train(cfg) -> checkpoint_path`: seed; `build_datasets`; `DataLoader`s
(`drop_last=True`, pinned); `pl.Trainer(max_epochs, accelerator="gpu", devices=1,
precision="16-mixed", gradient_clip_val=1.0, gradient_clip_algorithm="norm")` with
`GradualWarmupSchedulerV2` over `CosineAnnealingLR`; `ModelCheckpoint` monitoring
`train/total_loss`. Returns the best checkpoint path. `CSVLogger` (matching the proven
script; no wandb dependency in the core).

### `infer.py`
`infer(cfg, checkpoint_path, fragment_id) -> prob_map`: load checkpoint; slide a 64px
window at `stride` over the fragment (within mask); run the model; upsample each 4×4
logit-grid 16× to 64×64; accumulate with `core/villa_inference.GaussianBlender` soft
weights; normalize by the weight map → full-resolution `[0,1]` probability map. Optional
TTA via `VillaTTAWrapper` (config flag, default off for the baseline).

### `eval.py`
`evaluate(prob_map, label, mask, cfg) -> scorecard`: compute mask-restricted pixel-AUC
(reuse `scripts/pixel_auc.py` logic); sweep thresholds, select the calibrated threshold
(max centerline_dice, falling back to Youden's J if centerline metrics are unavailable);
write a thumbnail (reuse `repro/gp_winner/render_eval.py` logic) and a JSON scorecard
(`pixel_auc`, `threshold`, `centerline_dice`) under `cfg.reports_dir`. Does **not** gate on
`skel_dist` (removed as invalid — FINDINGS.md Phase 4b).

## Data flow

```
PHercParis2Fr47/Fr143 (zarr, uint16 ZSTD)
  └─ convert_fragment.py (//256 → 8-bit, cv2-readable)
       └─ train_scrolls/{frag}/layers/{17..42}.tif  +  {frag}_inklabels.png  +  {frag}_mask.png
            └─ data.build_datasets  (256-tile grid, 64px subtiles, depth-as-time, 4×4 labels)
                 └─ model.DetectorModel (TimeSformer)  →  train.train  →  checkpoint
                      └─ infer.infer  (tiled 64px, 16× upsample, Gaussian-blended)  →  prob map (H×W)
                           └─ eval.evaluate  →  pixel-AUC + calibrated threshold + thumbnail + JSON scorecard
```

The `reproduce` CLI command runs convert (if the 8-bit layers are absent) → train → infer
→ eval, then asserts `pixel_auc >= 0.70`.

## Error handling

- Missing converted 8-bit data → clear error naming the `convert` step and expected paths.
- `validate_window()` raises `ValueError` for non-compliant lateral size (e.g. `size=128`).
- Non-finite training loss → logged warning (matching the proven script's NaN guard).
- Fragment label/mask shape mismatch vs. volume → assertion with the offending shapes
  (guards the historical ±32 px / label-misalignment class of bug).
- Missing checkpoint at infer → explicit error.

## Testing

Fast unit tests under `tests/` (no full training):
- `test_detector_config_window` — defaults validate; `size=128` raises `ValueError`.
- `test_detector_data_shapes` — on a tiny synthetic fragment, subtiles are
  `(size,size,in_chans)`, downsampled labels are `(1,4,4)`, valid `xyxys` reassemble to
  `pred_shape`.
- `test_detector_smoke_train` — 1–2 optimizer steps on a tiny synthetic dataset produce a
  finite loss and correct output shape `(B,1,4,4)`.
- `test_detector_determinism` — same seed → identical model init / first-batch loss.
- `test_detector_eval_metric` — a perfect prob map scores AUC 1.0; a constant/chance map ≈ 0.5.

The heavy full reproduction (the ≥ 0.70 AUC bar) is the `reproduce` CLI command with an
assertion, run manually on the GPU — explicitly **not** a unit test (too slow).

## Risks & mitigations

- **Lightning inside `src/`** (rest of repo's `train.py` is plain torch): accepted to
  protect the proven result; isolated to `detector/`; deps already in `pyproject.toml`.
- **Converted-8-bit data path** (not zarr-native): accepted — it is exactly what produced
  0.711; zarr-native is a documented follow-up.
- **Reproduction variance**: the bar is 0.70 with margin under the proven 0.711, single
  fixed seed; if a clean re-run lands below 0.70, treat as a regression and diff against the
  `train_ours.py` baseline rather than re-tuning.
- **Loop interaction**: none — the detector is standalone and the loop remains paused; no
  edits to `run_autoresearch_loop.py` or `scripts/training/train.py`.

## Follow-ups (out of scope)

Zarr-native loading via `vesuvius_loader`; unifying with `vesuvius_model.VesuviusTimeSformer`;
wiring the detector into the autoresearch loop as a searchable architecture; scaling
segments/epochs toward legible text.
