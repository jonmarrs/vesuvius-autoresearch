# Full-Resolution 2.5D ResEncUNet Ink Detector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-pixel (64×64) 2.5D ResEncUNet ink detector to the detector subpackage — beating the TimeSformer's coarse 4×4 mask — reusing Sub-project A's data/infer/eval/metrics, then measure it same-scroll and cross-scroll.

**Architecture:** A new `ResEncDetectorModel` wraps the installed `dynamic_network_architectures.ResidualEncoderUNet` in **2D mode** (depth-as-channels). A `build_model(cfg)` factory selects it via `cfg.architecture`; `data.py` keeps full-resolution 64×64 labels when `cfg.full_res`; `infer.py`'s upsample is generalized to `size=(sz,sz)` so it serves both models. `eval`/`metrics`/`measure` from A are reused unchanged.

**Tech Stack:** PyTorch, pytorch-lightning, dynamic-network-architectures (nnU-Net network lib), segmentation-models-pytorch. All installed.

## Global Constraints

- Window compliance: 64px lateral (`in_chans=26` depth is NOT subject to the lateral limit). `validate_window()` still applies.
- Primary metric `val_f1`; `average_precision` + `ap_prevalence_lift` honest gates; ROC-AUC secondary only (A's contract — `metrics.py` unchanged).
- Isolation: code only under `src/vesuvius_autoresearch/detector/`, `tests/`, `reports/detector/`. Do NOT edit `run_autoresearch_loop.py` or `scripts/training/train.py`.
- Reuse the detector's AdamW + warmup-cosine + `0.5·Dice + 0.5·SoftBCE` (no nnU-Net SGD/poly/deep-supervision).
- No AI-authorship markers in any file, comment, or commit message.
- Run tests: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest <path> -v` (CPU). Commit with `git commit --no-verify`.

## File Structure

- Modify `src/vesuvius_autoresearch/detector/config.py` — add `architecture`, `resenc_n_stages`, `resenc_base_feat`, `full_res` property.
- Create `src/vesuvius_autoresearch/detector/model_resenc.py` — `ResEncDetectorModel`.
- Modify `src/vesuvius_autoresearch/detector/train.py` — `build_model(cfg, pred_shape)` factory; `train` uses it.
- Modify `src/vesuvius_autoresearch/detector/data.py` — full-resolution label when `cfg.full_res`.
- Modify `src/vesuvius_autoresearch/detector/infer.py` — `size=(sz,sz)` upsample.
- Tests: `tests/test_detector_model_resenc.py`, `tests/test_detector_build_model.py`, `tests/test_detector_train_resenc.py`; extend `tests/test_detector_config.py`, `tests/test_detector_data.py`, `tests/test_detector_infer.py`.

---

### Task 1: Config — architecture selector + full_res

**Files:**
- Modify: `src/vesuvius_autoresearch/detector/config.py`
- Test: `tests/test_detector_config.py`

**Interfaces:**
- Produces: `DetectorConfig` gains `architecture: str = "timesformer"`, `resenc_n_stages: int = 5`, `resenc_base_feat: int = 32`, and a read-only property `full_res -> bool` (== `architecture != "timesformer"`).

- [ ] **Step 1: Write the failing test (append to the existing file)**

Append to `tests/test_detector_config.py`:

```python
def test_architecture_defaults_and_full_res_property():
    assert DetectorConfig().architecture == "timesformer"
    assert DetectorConfig().full_res is False
    cfg = DetectorConfig(architecture="resenc")
    assert cfg.full_res is True
    assert cfg.resenc_n_stages == 5
    assert cfg.resenc_base_feat == 32
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_config.py::test_architecture_defaults_and_full_res_property -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'architecture'`

- [ ] **Step 3: Add the fields and property**

In `src/vesuvius_autoresearch/detector/config.py`, add these three fields immediately after the line `um_per_px: float = 8.0`:

```python
    # architecture selection (Sub-project B)
    architecture: str = "timesformer"  # "timesformer" | "resenc"
    resenc_n_stages: int = 5
    resenc_base_feat: int = 32
```

And add this property method immediately after the `validate_window` method (same indentation as `validate_window`):

```python
    @property
    def full_res(self) -> bool:
        """Per-pixel models (resenc) keep full-resolution labels; the TimeSformer uses 4x4."""
        return self.architecture != "timesformer"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_config.py -v`
Expected: PASS (all config tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/detector/config.py tests/test_detector_config.py
git commit --no-verify -m "feat(detector): config architecture selector + full_res property"
```

---

### Task 2: ResEncDetectorModel (2.5D per-pixel)

**Files:**
- Create: `src/vesuvius_autoresearch/detector/model_resenc.py`
- Test: `tests/test_detector_model_resenc.py`

**Interfaces:**
- Consumes: `DetectorConfig` (Task 1), `build_scheduler` from `train.py` (existing).
- Produces: `ResEncDetectorModel(cfg, pred_shape)` — a `pl.LightningModule` with `forward(x) -> Tensor[B,1,64,64]` (accepts the dataset's `(B,1,C,H,W)` or `(B,C,H,W)`) and `loss_func(logits, target) -> Tensor`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detector_model_resenc.py
import torch

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel


def test_resenc_forward_shape_and_finite_loss():
    cfg = DetectorConfig(architecture="resenc")
    model = ResEncDetectorModel(cfg, pred_shape=(64, 64))
    x = torch.randn(2, 1, cfg.in_chans, cfg.size, cfg.size)  # (B,1,C,H,W)
    out = model(x)
    assert out.shape == (2, 1, cfg.size, cfg.size)
    target = torch.rand(2, 1, cfg.size, cfg.size)
    loss = model.loss_func(out, target)
    assert torch.isfinite(loss)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_model_resenc.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vesuvius_autoresearch.detector.model_resenc'`

- [ ] **Step 3: Write the implementation**

```python
# src/vesuvius_autoresearch/detector/model_resenc.py
"""Full-resolution 2.5D ResEncUNet ink detector. Depth slices are input channels (2D convs),
output is a per-pixel 64x64 ink mask (vs the TimeSformer's 4x4 grid). Wraps the installed
dynamic_network_architectures ResidualEncoderUNet in 2D mode.

Constraint: cfg.size must be divisible by 2**(resenc_n_stages-1) (64 = 2**4 * 4 for 5 stages)."""
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import torch
import torch.nn as nn
from dynamic_network_architectures.architectures.unet import ResidualEncoderUNet
from dynamic_network_architectures.building_blocks.helper import (
    convert_dim_to_conv_op,
    get_matching_instancenorm,
)
from torch.optim import AdamW


class ResEncDetectorModel(pl.LightningModule):
    def __init__(self, cfg, pred_shape):
        super().__init__()
        self.cfg = cfg
        self.pred_shape = pred_shape
        self.loss_func1 = smp.losses.DiceLoss(mode="binary")
        self.loss_func2 = smp.losses.SoftBCEWithLogitsLoss(smooth_factor=cfg.bce_smooth)
        n = cfg.resenc_n_stages
        conv2d = convert_dim_to_conv_op(2)
        features = [min(cfg.resenc_base_feat * (2 ** i), 320) for i in range(n)]
        self.backbone = ResidualEncoderUNet(
            input_channels=cfg.in_chans, n_stages=n, features_per_stage=features,
            conv_op=conv2d, kernel_sizes=[[3, 3]] * n,
            strides=[[1, 1]] + [[2, 2]] * (n - 1), n_blocks_per_stage=[2] * n,
            num_classes=1, n_conv_per_stage_decoder=[2] * (n - 1), conv_bias=True,
            norm_op=get_matching_instancenorm(conv2d),
            norm_op_kwargs={"eps": 1e-5, "affine": True}, dropout_op=None,
            nonlin=nn.LeakyReLU, nonlin_kwargs={"inplace": True}, deep_supervision=False,
        )

    def loss_func(self, logits, target):
        return self.cfg.dice_w * self.loss_func1(logits, target) + \
            self.cfg.bce_w * self.loss_func2(logits, target)

    def forward(self, x):
        if x.ndim == 5:
            x = x[:, 0]  # (B,1,C,H,W) -> (B,C,H,W)
        return self.backbone(x)  # (B,1,H,W)

    def training_step(self, batch, batch_idx):
        x, y = batch
        loss = self.loss_func(self(x), y)
        self.log("train/total_loss", loss.item(), on_step=True, on_epoch=True, prog_bar=True)
        return {"loss": loss}

    def validation_step(self, batch, batch_idx):
        x, y, _ = batch
        loss = self.loss_func(self(x), y)
        self.log("val/total_loss", loss.item(), on_step=True, on_epoch=True, prog_bar=True)
        return {"loss": loss}

    def configure_optimizers(self):
        from .train import build_scheduler
        optimizer = AdamW(self.parameters(), lr=self.cfg.lr)
        return [optimizer], [build_scheduler(self.cfg, optimizer)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_model_resenc.py -v`
Expected: PASS (1 passed). CPU forward of a 9M-param UNet on batch=2 takes a few seconds — acceptable.

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/detector/model_resenc.py tests/test_detector_model_resenc.py
git commit --no-verify -m "feat(detector): 2.5D ResEncUNet model (per-pixel 64x64 output)"
```

---

### Task 3: build_model factory in train.py

**Files:**
- Modify: `src/vesuvius_autoresearch/detector/train.py`
- Test: `tests/test_detector_build_model.py`

**Interfaces:**
- Consumes: `DetectorModel` (existing), `ResEncDetectorModel` (Task 2).
- Produces: `build_model(cfg, pred_shape) -> pl.LightningModule` selecting by `cfg.architecture`; `train` uses it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detector_build_model.py
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.train import build_model
from vesuvius_autoresearch.detector.model import DetectorModel
from vesuvius_autoresearch.detector.model_resenc import ResEncDetectorModel


def test_build_model_dispatches_by_architecture():
    assert isinstance(build_model(DetectorConfig(), (64, 64)), DetectorModel)
    assert isinstance(
        build_model(DetectorConfig(architecture="resenc"), (64, 64)), ResEncDetectorModel)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_build_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_model'`

- [ ] **Step 3: Add the factory and use it**

In `src/vesuvius_autoresearch/detector/train.py`, add this function immediately after the existing `build_scheduler` function:

```python
def build_model(cfg, pred_shape):
    if cfg.architecture == "resenc":
        from .model_resenc import ResEncDetectorModel
        return ResEncDetectorModel(cfg, pred_shape=pred_shape)
    return DetectorModel(cfg, pred_shape=pred_shape)
```

Then change the model-construction line inside `train` from:

```python
    model = DetectorModel(cfg, pred_shape=pred_shape)
```

to:

```python
    model = build_model(cfg, pred_shape=pred_shape)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_build_model.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Confirm the existing TimeSformer train smoke still passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_train.py -v`
Expected: PASS (1 passed) — `build_model` returns `DetectorModel` by default.

- [ ] **Step 6: Commit**

```bash
git add src/vesuvius_autoresearch/detector/train.py tests/test_detector_build_model.py
git commit --no-verify -m "feat(detector): build_model factory (timesformer | resenc)"
```

---

### Task 4: Full-resolution labels in data.py

**Files:**
- Modify: `src/vesuvius_autoresearch/detector/data.py`
- Test: `tests/test_detector_data.py`

**Interfaces:**
- Consumes: `DetectorConfig.full_res` (Task 1).
- Produces: `CustomDataset.__getitem__` yields a `(1, size, size)` label when `cfg.full_res`, else the existing `(1, size//16, size//16)` (4×4).

- [ ] **Step 1: Write the failing test (append to the existing file)**

Append to `tests/test_detector_data.py`:

```python
def test_full_res_label_shape(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(data_root=root, architecture="resenc")  # full_res True
    train_ds, valid_ds, _, _ = D.build_datasets(cfg)
    _, label = train_ds[0]
    assert tuple(label.shape) == (1, cfg.size, cfg.size)  # (1,64,64) full-res
    _, vlabel, _ = valid_ds[0]
    assert tuple(vlabel.shape) == (1, cfg.size, cfg.size)
    # default TimeSformer path is still 4x4
    tr2, _, _, _ = D.build_datasets(DetectorConfig(data_root=root))
    _, lab2 = tr2[0]
    assert tuple(lab2.shape) == (1, 4, 4)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_data.py::test_full_res_label_shape -v`
Expected: FAIL on `assert (1,4,4) == (1,64,64)` (full_res not yet honored).

- [ ] **Step 3: Honor full_res in both __getitem__ branches**

In `src/vesuvius_autoresearch/detector/data.py`, in the **valid branch** (the `if self.xyxys is not None:` block), replace:

```python
            data = self.transform(image=image, mask=label)
            image = data["image"].unsqueeze(0)
            label = F.interpolate(data["mask"].unsqueeze(0),
                                  (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
            return image, label, xy
```

with:

```python
            data = self.transform(image=image, mask=label)
            image = data["image"].unsqueeze(0)
            if self.cfg.full_res:
                label = data["mask"]
            else:
                label = F.interpolate(data["mask"].unsqueeze(0),
                                      (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
            return image, label, xy
```

And in the **train branch** (end of the method), replace:

```python
        data = self.transform(image=image, mask=label)
        image = data["image"].unsqueeze(0)
        label = F.interpolate(data["mask"].unsqueeze(0),
                              (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
        return image, label
```

with:

```python
        data = self.transform(image=image, mask=label)
        image = data["image"].unsqueeze(0)
        if self.cfg.full_res:
            label = data["mask"]
        else:
            label = F.interpolate(data["mask"].unsqueeze(0),
                                  (self.cfg.size // 16, self.cfg.size // 16)).squeeze(0)
        return image, label
```

(`data["mask"]` from `ToTensorV2(transpose_mask=True)` is already `(1, size, size)`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_data.py -v`
Expected: PASS (all data tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/detector/data.py tests/test_detector_data.py
git commit --no-verify -m "feat(detector): full-resolution labels when cfg.full_res"
```

---

### Task 5: Architecture-agnostic upsample in infer.py

**Files:**
- Modify: `src/vesuvius_autoresearch/detector/infer.py`
- Test: `tests/test_detector_infer.py`

**Interfaces:**
- Produces: `infer` upsamples each tile's logits to `(sz, sz)` via `size=` (not `scale_factor=16`), serving both the 4×4 TimeSformer and the 64×64 ResEnc output.

- [ ] **Step 1: Write the failing test (append to the existing file)**

Append to `tests/test_detector_infer.py`:

```python
import torch.nn as nn


class _FullResStub(nn.Module):
    """Minimal full-resolution model: (B,1,C,H,W) -> (B,1,H,W)."""
    def __init__(self, cfg):
        super().__init__()
        self.conv = nn.Conv2d(cfg.in_chans, 1, 3, padding=1)

    def forward(self, x):
        return self.conv(x[:, 0])


def test_infer_handles_full_resolution_output(tmp_path):
    root = str(tmp_path)
    _make_fake_fragment(root, "PHercParis2Fr143", h=192, w=192)
    cfg = DetectorConfig(data_root=root, architecture="resenc")
    model = _FullResStub(cfg).eval()
    prob = infer(cfg, checkpoint_path=None, fragment_id="PHercParis2Fr143", model=model)
    assert prob.shape == (192, 192)
    assert float(prob.min()) >= 0.0 and float(prob.max()) <= 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_infer.py::test_infer_handles_full_resolution_output -v`
Expected: FAIL — `scale_factor=16` turns the stub's 64×64 logits into 1024×1024, so the `pred[y:y+sz, x:x+sz] += prob * win` accumulation raises a broadcasting error.

- [ ] **Step 3: Generalize the upsample**

In `src/vesuvius_autoresearch/detector/infer.py`, in the `_flush` inner function, replace:

```python
        ups = F.interpolate(logits, scale_factor=16, mode="bilinear", align_corners=False)
```

with:

```python
        ups = F.interpolate(logits, size=(sz, sz), mode="bilinear", align_corners=False)
```

(`sz = cfg.size` is already in scope in `infer`. For the 4×4 TimeSformer this equals the old `scale_factor=16`; for the 64×64 ResEnc it is a no-op.)

- [ ] **Step 4: Run test to verify it passes**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_infer.py -v`
Expected: PASS (all infer tests — the existing TimeSformer tests stay green because `size=(64,64)` == `scale_factor=16` for 4×4 input, and the new full-res test passes)

- [ ] **Step 5: Commit**

```bash
git add src/vesuvius_autoresearch/detector/infer.py tests/test_detector_infer.py
git commit --no-verify -m "feat(detector): architecture-agnostic infer upsample (size=(sz,sz))"
```

---

### Task 6: ResEnc training smoke (integration)

**Files:**
- Test: `tests/test_detector_train_resenc.py`

**Interfaces:**
- Consumes: `train` + `build_model` (Task 3), `ResEncDetectorModel` (Task 2), full_res data (Task 4), config (Task 1).
- Produces: confidence that the full ResEnc path (factory → full-res labels → per-pixel model → checkpoint) trains end-to-end.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_detector_train_resenc.py
import os

from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector import train as T
from test_detector_data import _make_fake_fragment


def test_resenc_smoke_train_returns_checkpoint(tmp_path):
    root = str(tmp_path / "scrolls")
    _make_fake_fragment(root, "PHercParis2Fr47")
    _make_fake_fragment(root, "PHercParis2Fr143")
    cfg = DetectorConfig(data_root=root, model_dir=str(tmp_path / "models"),
                         architecture="resenc", train_batch_size=2, num_workers=0, seed=0)
    ckpt = T.train(cfg, max_epochs=1, limit_batches=2)
    assert os.path.exists(ckpt)
```

- [ ] **Step 2: Run test to verify it fails (then passes)**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_train_resenc.py -v`
Expected: With Tasks 1–4 already implemented, this should PASS directly (the integration is already wired). If it FAILS, the failure pinpoints a wiring gap between the factory, full-res labels, and the model — fix that gap (do not weaken the test). This is the one task whose test may pass on first run; that is acceptable for an integration smoke test that composes already-built units.

- [ ] **Step 3: Run the full detector suite**

Run: `CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py -q`
Expected: PASS (all detector tests green — TimeSformer and ResEnc paths).

- [ ] **Step 4: Commit**

```bash
git add tests/test_detector_train_resenc.py
git commit --no-verify -m "test(detector): ResEnc end-to-end training smoke"
```

---

### Task 7: Phase 1 — same-scroll ResEnc run (manual, GPU)

**Files:** none (operational); produces `reports/detector/` scorecards + a Phase-1 report.

Run by a human on the GPU — NOT a unit test.

- [ ] **Step 1: Pause the loop.**

Run:
```bash
touch .loop_paused
pkill -TERM -f "python run_autoresearch_loop.py"; pkill -TERM -f "train.py --config config_temp.json"
sleep 4; ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config" | grep -v grep || echo "(loop paused)"
```
Expected: `(loop paused)`; GPU free.

- [ ] **Step 2: Train the ResEnc same-scroll.**

Run:
```bash
uv run python -c "
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.train import train
cfg = DetectorConfig(architecture='resenc', model_dir='models/detector_resenc')
print(train(cfg))
"
```
Expected: trains `cfg.epochs` (12) epochs on `PHercParis2Fr47`, saving per-epoch checkpoints to `models/detector_resenc/`. ~hours.

- [ ] **Step 3: Measure same-scroll vs cross-scroll on the best epoch.**

Pick the last (or any) epoch checkpoint and run A's measure CLI against it:
```bash
CK=$(ls -t models/detector_resenc/detector_epoch=*.ckpt | head -1)
uv run python -m vesuvius_autoresearch.detector.cli measure --checkpoint "$CK"
```
Expected: prints same-scroll (`scroll2_same`) and cross-scroll (`scroll1_cross`) `val_f1`/`ap`/`lift`, writing `reports/detector/cross_scroll_measurement.{md,json}`. Note: this overwrites the TimeSformer measurement file — first copy it aside: `cp reports/detector/cross_scroll_measurement.md reports/detector/cross_scroll_measurement_timesformer.md`.
**Success check:** same-scroll `val_f1` > 0.393 (beats the TimeSformer). Record the cross-scroll lift vs 1.29.

- [ ] **Step 4: Commit the Phase-1 artifacts.**

```bash
git add reports/detector/cross_scroll_measurement.md reports/detector/cross_scroll_measurement.json reports/detector/cross_scroll_measurement_timesformer.md
git commit --no-verify -m "chore(detector): Phase 1 ResEnc same-scroll measurement (val_f1 vs TimeSformer 0.393)"
```

- [ ] **Step 5: If same-scroll `val_f1` <= 0.393,** that is a finding, not a failure — the 2.5D ResEnc with the detector's recipe did not beat the coarse TimeSformer; record it and note candidate levers (nnU-Net training protocol, more epochs, loss weighting) for a follow-up. Do NOT silently re-tune. Leave the loop paused and proceed to Phase 2 only if the same-scroll result is acceptable.

---

### Task 8: Phase 2 — cross-scroll training run (manual, GPU)

**Files:** none (operational); produces a Phase-2 cross-scroll report.

- [ ] **Step 1: Identify usable Scroll-1 training segments.**

Run:
```bash
for d in villa/ink-detection/train_scrolls/2023*; do
  s=$(basename "$d")
  l1=$(ls "$d"/layers/17.tif 2>/dev/null); l2=$(ls "$d"/layers/42.tif 2>/dev/null)
  ink=$(ls "$d"/*inklabels* 2>/dev/null); msk=$(ls "$d"/*mask* 2>/dev/null)
  [ -n "$l1" ] && [ -n "$l2" ] && [ -n "$ink" ] && [ -n "$msk" ] && echo "OK $s"
done
```
Expected: a list of `OK <segment>` — these are the valid Scroll-1 training fragments. Use exactly these.

- [ ] **Step 2: Train the ResEnc on the Scroll-1 segments, hold out Scroll-2.**

Run (replace `SEGS` with the `OK` list from Step 1):
```bash
uv run python -c "
from vesuvius_autoresearch.detector.config import DetectorConfig
from vesuvius_autoresearch.detector.train import train
segs = ['20230702185753', '20230820203112']  # <- the OK list from Step 1
cfg = DetectorConfig(architecture='resenc', model_dir='models/detector_resenc_x',
                     train_fragment_ids=segs, valid_fragment_id='PHercParis2Fr143')
print(train(cfg))
"
```
Expected: trains on the Scroll-1 segments, validates on Scroll-2 `Fr143`. ~hours.

- [ ] **Step 3: Measure cross-scroll (train Scroll-1 → eval Scroll-2).**

```bash
CK=$(ls -t models/detector_resenc_x/detector_epoch=*.ckpt | head -1)
uv run python -m vesuvius_autoresearch.detector.cli measure \
  --checkpoint "$CK" --same PHercParis2Fr143 --cross 20230702185753
```
(Here `--same` is the held-out Scroll-2 fragment the model did NOT train on; `--cross` is a Scroll-1 segment it DID train on — a train-set sanity check. The headline is the held-out Scroll-2 `val_f1`/`lift`.) Writes `reports/detector/cross_scroll_measurement.{md,json}`; copy aside first as in Task 7.
**Success signal:** held-out Scroll-2 `ap_prevalence_lift` > 1.29 (the TimeSformer same-train cross-eval baseline) ⇒ diverse training data improved generalization.

- [ ] **Step 4: Commit the Phase-2 artifacts and resume the loop.**

```bash
cp reports/detector/cross_scroll_measurement.md reports/detector/cross_scroll_phase2.md
git add reports/detector/cross_scroll_phase2.md
git commit --no-verify -m "chore(detector): Phase 2 ResEnc cross-scroll training measurement (vs lift 1.29)"
bash start.sh
```
Expected: loop resumes (`pgrep -f "python run_autoresearch_loop.py"` returns a PID; `.loop_paused` gone).

---

## Self-Review

**Spec coverage:**
- ResEnc model (2.5D, per-pixel, library import, same loss/optim) → Task 2. ✓
- Config selector + full_res → Task 1. ✓
- build_model factory → Task 3. ✓
- Full-res labels → Task 4. ✓
- Architecture-agnostic infer → Task 5. ✓
- eval/metrics/measure reused unchanged → no task needed (A's code), exercised in Tasks 7–8. ✓
- Phase 1 same-scroll (val_f1 > 0.393) → Task 7. ✓
- Phase 2 cross-scroll (vs lift 1.29) → Task 8. ✓
- Tests (model forward/loss, factory dispatch, full-res label, infer generalization, train smoke) → Tasks 1–6. ✓
- Scope boundary (2.5D, no nnU-Net trainer, no new metric code, no search loop) → respected; documented as follow-ups. ✓
- Isolation + loop-pause → Tasks 7/8 Steps + Global Constraints. ✓

**Placeholder scan:** No TBD/TODO; every code step is complete; commands have expected output. The `SEGS`/`segs` list in Task 8 is filled at run time from Task 8 Step 1's verified output (an operational input, not a code placeholder). ✓

**Type consistency:** `DetectorConfig.full_res` (Task 1) consumed by `data.py` (Task 4) and `model_resenc` selection; `build_model(cfg, pred_shape)` (Task 3) matches `ResEncDetectorModel(cfg, pred_shape)` (Task 2) and `DetectorModel(cfg, pred_shape)` (existing); `train` calls `build_model`; `infer`'s `size=(sz,sz)` serves both `(B,1,4,4)` and `(B,1,64,64)` logits; `measure`/`eval`/`metrics` from A unchanged. ✓

**Known follow-ups (out of scope):** nnU-Net training protocol; raw-fragment cross-scroll alignment for a 3rd scroll; 3D variant; Sub-project C search loop.
