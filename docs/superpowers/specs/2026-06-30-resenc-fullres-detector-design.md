# Full-Resolution 2.5D ResEncUNet Ink Detector — Design

**Status:** Approved design (brainstorming). Sub-project B of the "cross-scroll Dice autoresearch" pivot.

## Context & motivation

Sub-project A gave us the honest metric contract (`val_f1` primary, `average_precision` +
`ap_prevalence_lift` gates) and the first valid cross-scroll number: the existing **TimeSformer**
detector (trained on Scroll-2 `PHercParis2Fr47`) scores same-scroll `Fr143` `val_f1` **0.393** /
lift **2.07**, and cross-scroll Scroll-1 `val_f1` **0.222** / lift **1.29**.

The TimeSformer emits a **4×4 ink grid per 64px tile** (`num_classes=16` → `view(-1,1,4,4)`),
upsampled 16×. That coarse output caps mask quality (F1). The Vesuvius community's segmentation
frontier is **full-resolution ResEncUNet/nnU-Net** optimized for Dice. Sub-project B replaces the
coarse head with a **per-pixel (64×64) 2.5D ResEncUNet**, reusing A's data/infer/eval/metrics, to
(1) beat the same-scroll F1 and (2) test whether a crisper architecture and/or more diverse training
data improves cross-scroll transfer.

**Key reuse finding:** `ResidualEncoderUNet` is a class in the installed
`dynamic_network_architectures` library (`.architectures.unet`), constructible standalone in **2D
mode** (`convert_dim_to_conv_op(2)`), so it drops into the detector subpackage with no dependency on
the loop's `scripts/training/train.py` stack.

## Goals / success criteria

1. A unit-tested **2.5D ResEncUNet detector model** producing per-pixel 64×64 masks, trainable via the
   detector's existing recipe (AdamW + warmup-cosine, `0.5·Dice + 0.5·SoftBCE`).
2. **Phase 1 (same-scroll):** trained on Scroll-2 `Fr47`, held-out `Fr143` **`val_f1` > 0.393** (beats
   the TimeSformer); the same model's cross-scroll Scroll-1 `ap_prevalence_lift` reported vs the 1.29
   baseline.
3. **Phase 2 (cross-scroll training):** trained on the 7 Scroll-1 segments, held-out Scroll-2 `Fr143`,
   measured — reporting whether cross-scroll `ap_prevalence_lift` rises above 1.29.

## Non-goals (scope boundary)

- **2.5D only** (depth-as-channels, 2D convs). No 3D volumetric pipeline.
- **No full nnU-Net trainer** — reuse the detector's AdamW + warmup-cosine; no SGD/poly schedule, no
  deep supervision, no region-based loss.
- **No new metric/eval/measure code** — A's `metrics.py`/`eval.py`/`measure.py` are reused unchanged.
- **No search loop** (Sub-project C).
- **No raw-fragment alignment** for a 3rd held-out scroll (PHerc1667 etc.) — aligned data is limited to
  the Scroll-1/Scroll-2 `train_scrolls` pair.

## Architecture & components

All under `src/vesuvius_autoresearch/detector/`, reusing A.

### 1. `config.py` (extend `DetectorConfig`)
Add fields (defaults preserve existing TimeSformer behavior):
- `architecture: str = "timesformer"` — selector (`"timesformer"` | `"resenc"`).
- `resenc_n_stages: int = 5` — UNet stages for a 64px patch (64→64→32→16→8→4 via strides
  `[1,2,2,2,2]`).
- `resenc_base_feat: int = 32` — features at stage 0; `features_per_stage = [min(base*2**i, 320) for i
  in range(n_stages)]`.
- Property `full_res -> bool`: returns `self.architecture != "timesformer"`.

### 2. `model_resenc.py` (new)
`ResEncDetectorModel(pl.LightningModule)`:
- Builds `ResidualEncoderUNet(input_channels=cfg.in_chans, n_stages=cfg.resenc_n_stages,
  features_per_stage=..., conv_op=convert_dim_to_conv_op(2), kernel_sizes=[[3,3]]*n_stages,
  strides=[[1,1]]+[[2,2]]*(n_stages-1), n_blocks_per_stage=[2]*n_stages, num_classes=1,
  n_conv_per_stage_decoder=[2]*(n_stages-1), conv_bias=True,
  norm_op=get_matching_instancenorm(convert_dim_to_conv_op(2)), norm_op_kwargs={"eps":1e-5,
  "affine":True}, dropout_op=None, nonlin=nn.LeakyReLU, nonlin_kwargs={"inplace":True},
  deep_supervision=False)` (imports from `dynamic_network_architectures`).
- `forward(x)`: accept the dataset's `(B,1,C,H,W)`, squeeze dim 1 → `(B,C,H,W)`; return
  `backbone(x)` shaped `(B,1,H,W)`.
- Loss `0.5·DiceLoss(binary) + 0.5·SoftBCEWithLogitsLoss(smooth=cfg.bce_smooth)` (same as
  `DetectorModel`); `loss_func`, `training_step`, `validation_step`, `configure_optimizers` mirror
  `DetectorModel` (reuse `build_scheduler`).

### 3. `data.py` (small change)
`CustomDataset.__getitem__`: when `cfg.full_res`, keep the transformed `(1,size,size)` mask label
(skip the `F.interpolate` to `(size//16, size//16)`), for BOTH train and valid branches. TimeSformer
path (`full_res == False`) is unchanged.

### 4. `train.py` (small change)
Add `build_model(cfg, pred_shape)` factory: `architecture == "resenc"` → `ResEncDetectorModel`, else
`DetectorModel`. `train(...)` calls it instead of constructing `DetectorModel` directly. Everything
else (loaders, trainer, checkpointing, `build_scheduler`) unchanged.

### 5. `infer.py` (one-line generalization)
Replace `F.interpolate(logits, scale_factor=16, mode="bilinear", align_corners=False)` with
`F.interpolate(logits, size=(sz, sz), mode="bilinear", align_corners=False)`. Architecture-agnostic:
4×4→64×64 for the TimeSformer (identical result) and a no-op for the 64×64 ResEnc output. Batching,
uniform weighting, `/255` normalization, crop-to-label all unchanged.

### 6. `eval.py` / `metrics.py` / `measure.py`
Reused unchanged from A.

## Data flow

```
data.CustomDataset (depth-as-channels 64px tiles; full-res 64x64 label when cfg.full_res)
  └─ ResEncDetectorModel.forward (B,1,26,64,64) -> (B,1,64,64)
train.train(cfg) [architecture="resenc"] -> checkpoint
infer.infer(cfg, ckpt, fragment) -> full-res prob map (size=() interpolate is a no-op)
measure.measure(...) -> same-scroll vs cross-scroll val_f1 / AP / prevalence-lift report
```

## Testing

`tests/test_detector_model_resenc.py` (CPU):
- `forward` on `(2,1,26,64,64)` returns `(2,1,64,64)`; `loss_func` on `(2,1,64,64)` logits + target is
  finite.

`tests/test_detector_build_model.py`:
- `build_model(cfg(architecture="timesformer"), (64,64))` is a `DetectorModel`;
  `build_model(cfg(architecture="resenc"), (64,64))` is a `ResEncDetectorModel`.

Extend `tests/test_detector_data.py`:
- With `cfg.architecture="resenc"` (→ `full_res True`), `train_ds[0]` label shape is `(1,64,64)`; the
  default TimeSformer case still yields `(1,4,4)`.

Extend `tests/test_detector_infer.py`:
- A model whose forward returns `(B,1,64,64)` (a tiny stub or the ResEnc) → `infer` returns a prob map
  of the fragment label shape, values in `[0,1]`; the existing TimeSformer infer tests remain green
  (the `size=(sz,sz)` change is equivalent to `scale_factor=16` for 4×4 input).

`tests/test_detector_train_resenc.py`:
- ResEnc smoke train (`cfg.architecture="resenc"`, `max_epochs=1`, `limit_batches=2`, fake fragments)
  returns an existing checkpoint path.

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -v`

## Error handling

- `validate_window()` still applies (64px lateral compliant).
- ResEnc requires the patch size to be divisible by the stage downsampling (64 = 2^4·4, fine for 5
  stages); document the constraint in the model docstring. If a future `size` breaks it, the library
  raises a shape error — surfaced, not swallowed.
- Missing `dynamic_network_architectures` import → clear ImportError at model construction (it is
  installed; this is defensive).

## Operational (the two GPU runs)

Phase-1 and Phase-2 are training runs (~hours each, like the TimeSformer). Pause the loop
(`.loop_paused` + kill; resume `bash start.sh`). Phase 1: `train_fragment_ids=["PHercParis2Fr47"]`,
`valid_fragment_id="PHercParis2Fr143"`, then `measure` (same `Fr143` + cross `20230702185753`). Phase
2: `train_fragment_ids=[the Scroll-1 timestamp segments]`, `valid_fragment_id="PHercParis2Fr143"`,
then `measure`. At run time, verify each Scroll-1 segment has `*_inklabels.*`, `*_mask.png`, and
`layers/17.tif`..`42.tif` (drop any that don't, as in A's Task-4 layer-index check). Commit each
scorecard/report under `reports/detector/`.

## Global constraints

- Window compliance: 64px lateral (depth/`in_chans=26` not subject to the lateral limit).
- Primary metric `val_f1`; AP + prevalence-lift gates; ROC-AUC secondary only (A's contract).
- Isolation: code only under `src/vesuvius_autoresearch/detector/` + `tests/` + `reports/detector/`;
  do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`.
- No AI-authorship markers.

## Follow-ups (out of scope)

- Sub-project C: bandit search over ResEnc config variants optimizing held-out cross-scroll `val_f1`.
- nnU-Net training protocol (SGD/poly, deep supervision, region loss) if v1 underperforms.
- Raw-fragment cross-scroll alignment for a true 3rd held-out scroll.
- 3D volumetric variant if 2.5D plateaus.
