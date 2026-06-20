# Clean-Room 2.5D SegFormer Ink-Detection Reproduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean-room 2.5D SegFormer ink detector that achieves held-out-fragment pixel AUC ≥ 0.75 and visually legible ink on the canonical Kaggle fragments — a working-detector reset.

**Architecture:** `[B,1,D,H,W]` tile → 3D-conv stem → max-over-z → `[B,C,H,W]` → `smp.Segformer(mit_b3, in_channels=C)` → upsample → `[B,1,H,W]` logits. Leave-one-fragment-out training, sliding-window TTA inference, pixel-AUC + Fβ evaluation with a rendered ink PNG. Fully isolated under `repro/ink_segformer/`.

**Tech Stack:** Python, PyTorch, `segmentation_models_pytorch` 0.5 (`smp.Segformer`, present), `timm` (present), PIL, NumPy, scikit-learn, pytest. Reuses `scripts/pixel_auc.py` (`pooled_pixel_auc`).

**Spec:** `docs/superpowers/specs/2026-06-18-ink-detection-reproduction-design.md`

**Isolation note:** all new code lives under `repro/ink_segformer/`; tests under `tests/`. Nothing imports or modifies `scripts/training/train.py` or the autoresearch loop. Runs use the existing `.venv`.

---

## File Structure

- `repro/ink_segformer/__init__.py`, `config.py` — package + config dataclass.
- `repro/ink_segformer/dataset.py` — layer reading, tiling, `InkTileDataset`.
- `repro/ink_segformer/model.py` — `Stem3D` + `InkSegformer`.
- `repro/ink_segformer/losses.py` — `bce_dice_loss`.
- `repro/ink_segformer/train.py` — leave-one-fragment-out trainer.
- `repro/ink_segformer/infer.py` — sliding-window TTA inference.
- `repro/ink_segformer/evaluate.py` — AUC/Fβ + ink-PNG render.
- `tests/test_ink_repro_dataset.py`, `tests/test_ink_repro_model.py`, `tests/test_ink_repro_losses.py`.
- Data: `local_data/kaggle_ink/{1,2,3}/` (acquired in Task 0). Outputs: `repro/ink_segformer/runs/` (gitignored).

---

## Task 0: Verify the local fragment data (NO download needed)

**Files:** none. The canonical Kaggle ink-detection fragments map directly to the PHerc fragments we already have: **Kaggle Frag1 = PHercParis2Fr47** (train), **Frag2 = PHercParis2Fr143** (val) — both local, clean, aligned, in flat tif format. (Frag3-6 = PHercParis1Fr34/Fr39, PHerc1667Fr3, PHerc51Fr8 are also local but in the misaligned `(H,depth,W)` copies; not needed for this 2-fragment first run. If wanted later, pristine copies download with no Kaggle account from `https://dl.ash2txt.org/fragments/Frag{3..6}/` using basic-auth `registeredusers:only`.)

- [ ] **Step 1: Verify Fr47 (train) and Fr143 (val) layout**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
for d in PHercParis2Fr47 PHercParis2Fr143; do
  p=local_data/$d
  echo "$d: layers=$(ls $p/surface_volume/*.tif 2>/dev/null | wc -l) ink=$(test -f $p/inklabels.png && echo yes) mask=$(test -f $p/mask.png && echo yes)"
done
```
Expected: each shows `layers=33 ink=yes mask=yes` (the local copies hold the middle 33 depth layers, `16.tif`–`48.tif` — already the useful slab the winners used). The code reads however many tif layers exist, so 33 is fine. No download; proceed directly. (Tasks 1-7 build/test on synthetic fixtures regardless; only the Task 8 run needs this data.)

---

## Task 1: Package scaffold + config

**Files:**
- Create: `repro/ink_segformer/__init__.py`, `repro/ink_segformer/config.py`

- [ ] **Step 1: Create the package**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p repro/ink_segformer/runs
touch repro/ink_segformer/__init__.py
printf 'repro/ink_segformer/runs/\n' >> .gitignore
```

- [ ] **Step 2: Write `config.py`**

```python
# repro/ink_segformer/config.py
from dataclasses import dataclass


@dataclass
class ReproConfig:
    data_root: str = "local_data/kaggle_ink/train"  # contains 1/ 2/ 3/
    tile: int = 224
    stride: int = 112
    z_start: int = 16       # middle 32 of the 65 depth layers
    z_count: int = 32
    stem_channels: int = 32
    encoder: str = "mit_b3"
    batch_size: int = 8
    lr: float = 1e-4
    weight_decay: float = 1e-4
    epochs: int = 25
    min_papyrus: float = 0.05  # min fraction of papyrus mask in a sampled tile
    seed: int = 7
```

- [ ] **Step 3: Commit**

```bash
git add repro/ink_segformer/__init__.py repro/ink_segformer/config.py .gitignore
git commit -m "feat(repro): ink_segformer package scaffold + config"
```

---

## Task 2: Dataset (tiling + middle layers) — TDD

**Files:**
- Create: `repro/ink_segformer/dataset.py`
- Test: `tests/test_ink_repro_dataset.py`

- [ ] **Step 1: Write the failing test (synthetic fragment fixture)**

```python
# tests/test_ink_repro_dataset.py
import numpy as np
from PIL import Image

from repro.ink_segformer.dataset import InkTileDataset, compute_tile_origins


def _make_fragment(tmp_path, h=64, w=48, layers=20):
    d = tmp_path / "frag"
    (d / "surface_volume").mkdir(parents=True)
    for i in range(layers):
        Image.fromarray((np.full((h, w), i * 10, dtype=np.uint16))).save(
            d / "surface_volume" / f"{i:02d}.tif"
        )
    ink = np.zeros((h, w), dtype=np.uint8)
    ink[10:30, 5:25] = 255
    Image.fromarray(ink).save(d / "inklabels.png")
    mask = np.full((h, w), 255, dtype=np.uint8)
    Image.fromarray(mask).save(d / "mask.png")
    return str(d)


def test_compute_tile_origins_covers_masked_area_with_stride():
    mask = np.ones((64, 48), dtype=bool)
    origins = compute_tile_origins(mask, tile=32, stride=16, min_papyrus=0.05)
    # origins are clamped so a full 32-tile fits; (0,0) present, all in-bounds
    assert (0, 0) in origins
    assert all(0 <= y <= 64 - 32 and 0 <= x <= 48 - 32 for y, x in origins)


def test_dataset_returns_aligned_shapes(tmp_path):
    frag = _make_fragment(tmp_path)
    ds = InkTileDataset([frag], tile=32, stride=16, z_start=4, z_count=8, min_papyrus=0.0)
    vol, ink, pmask = ds[0]
    assert vol.shape == (1, 8, 32, 32)
    assert ink.shape == (1, 32, 32) and pmask.shape == (1, 32, 32)
    assert vol.dtype.__str__() == "torch.float32"
    assert float(ink.max()) <= 1.0 and float(ink.min()) >= 0.0
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError: repro.ink_segformer.dataset`)

Run: `cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch && PYTHONPATH=. .venv/bin/python -m pytest tests/test_ink_repro_dataset.py -v`

- [ ] **Step 3: Write `dataset.py`**

```python
# repro/ink_segformer/dataset.py
import os

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

Image.MAX_IMAGE_PIXELS = None


def read_middle_layers(frag_dir, z_start, z_count):
    """Read z_count depth layers starting at z_start from <frag>/surface_volume/*.tif
    into a normalized float32 array [D, H, W] (uint16 -> /65535, uint8 -> /255)."""
    files = sorted(
        f for f in os.listdir(os.path.join(frag_dir, "surface_volume")) if f.endswith(".tif")
    )
    files = files[z_start : z_start + z_count]
    layers = []
    for f in files:
        a = np.array(Image.open(os.path.join(frag_dir, "surface_volume", f)))
        denom = 65535.0 if a.dtype == np.uint16 else 255.0
        layers.append(a.astype(np.float32) / denom)
    return np.stack(layers, axis=0)


def compute_tile_origins(mask, tile, stride, min_papyrus=0.05):
    """List of (y, x) top-left origins on a grid (stride), clamped so a full tile
    fits, keeping only tiles whose papyrus-mask coverage >= min_papyrus."""
    h, w = mask.shape
    ys = list(range(0, max(1, h - tile + 1), stride))
    xs = list(range(0, max(1, w - tile + 1), stride))
    if ys[-1] != h - tile:
        ys.append(max(0, h - tile))
    if xs[-1] != w - tile:
        xs.append(max(0, w - tile))
    origins = []
    for y in ys:
        for x in xs:
            if mask[y : y + tile, x : x + tile].mean() >= min_papyrus:
                origins.append((y, x))
    return origins


class InkTileDataset(Dataset):
    """Tiles of one or more fragments. __getitem__ -> (vol[1,D,H,W], ink[1,H,W],
    pmask[1,H,W]) as float32 torch tensors. Volumes are loaded once per fragment
    and held in memory (Kaggle fragments fit)."""

    def __init__(self, frag_dirs, tile, stride, z_start, z_count, min_papyrus=0.05, augment=False):
        self.tile, self.augment = tile, augment
        self.items = []  # (frag_index, y, x)
        self.vols, self.inks, self.masks = [], [], []
        for fi, d in enumerate(frag_dirs):
            vol = read_middle_layers(d, z_start, z_count)  # [D,H,W]
            ink = (np.array(Image.open(os.path.join(d, "inklabels.png")).convert("L")) > 127).astype(np.float32)
            mask = (np.array(Image.open(os.path.join(d, "mask.png")).convert("L")) > 127).astype(np.float32)
            self.vols.append(vol)
            self.inks.append(ink)
            self.masks.append(mask)
            for (y, x) in compute_tile_origins(mask > 0.5, tile, stride, min_papyrus):
                self.items.append((fi, y, x))

    def __len__(self):
        return len(self.items)

    def __getitem__(self, idx):
        fi, y, x = self.items[idx]
        t = self.tile
        vol = self.vols[fi][:, y : y + t, x : x + t]      # [D,t,t]
        ink = self.inks[fi][y : y + t, x : x + t]          # [t,t]
        pmask = self.masks[fi][y : y + t, x : x + t]       # [t,t]
        if self.augment:
            k = np.random.randint(0, 4)
            vol = np.rot90(vol, k, axes=(1, 2)).copy()
            ink = np.rot90(ink, k).copy()
            pmask = np.rot90(pmask, k).copy()
            if np.random.rand() < 0.5:
                vol, ink, pmask = vol[:, ::-1].copy(), ink[::-1].copy(), pmask[::-1].copy()
        vol = torch.from_numpy(vol).unsqueeze(0).float()   # [1,D,t,t]
        ink = torch.from_numpy(ink).unsqueeze(0).float()   # [1,t,t]
        pmask = torch.from_numpy(pmask).unsqueeze(0).float()
        return vol, ink, pmask
```

- [ ] **Step 4: Run it — PASS (3 passed)**

- [ ] **Step 5: Commit**

```bash
git add repro/ink_segformer/dataset.py tests/test_ink_repro_dataset.py
git commit -m "feat(repro): ink tile dataset (middle layers + papyrus-gated tiling)"
```

---

## Task 3: Model (3D stem + max-z + SegFormer) — TDD

**Files:**
- Create: `repro/ink_segformer/model.py`
- Test: `tests/test_ink_repro_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ink_repro_model.py
import torch

from repro.ink_segformer.model import InkSegformer, Stem3D


def test_stem_collapses_depth_to_channels():
    stem = Stem3D(out_channels=16)
    out = stem(torch.rand(2, 1, 8, 64, 64))  # [B,1,D,H,W]
    assert out.shape == (2, 16, 64, 64)      # depth gone, C=16, H/W preserved


def test_inksegformer_forward_shape():
    # encoder_weights=None to avoid a pretrained-weight download in tests
    model = InkSegformer(stem_channels=16, encoder="mit_b3", encoder_weights=None)
    out = model(torch.rand(2, 1, 8, 224, 224))
    assert out.shape == (2, 1, 224, 224)
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError`)

- [ ] **Step 3: Write `model.py`**

```python
# repro/ink_segformer/model.py
import segmentation_models_pytorch as smp
import torch
import torch.nn.functional as F
from torch import nn


class Stem3D(nn.Module):
    """4-layer 3D-conv stem over the depth stack, then max over the depth axis —
    collapses depth into feature channels (the 1st-place '3D conv then max-z',
    depth-invariant)."""

    def __init__(self, out_channels=32):
        super().__init__()
        chans = [1, 16, 32, 32, out_channels]
        layers = []
        for i in range(4):
            layers += [
                nn.Conv3d(chans[i], chans[i + 1], kernel_size=3, padding=1),
                nn.BatchNorm3d(chans[i + 1]),
                nn.ReLU(inplace=True),
            ]
        self.net = nn.Sequential(*layers)

    def forward(self, x):  # x: [B,1,D,H,W]
        x = self.net(x)          # [B,C,D,H,W]
        return x.max(dim=2).values  # [B,C,H,W]


class InkSegformer(nn.Module):
    def __init__(self, stem_channels=32, encoder="mit_b3", encoder_weights="imagenet"):
        super().__init__()
        self.stem = Stem3D(out_channels=stem_channels)
        self.seg = smp.Segformer(
            encoder_name=encoder,
            in_channels=stem_channels,
            classes=1,
            encoder_weights=encoder_weights,
        )

    def forward(self, x):  # [B,1,D,H,W] -> [B,1,H,W]
        h, w = x.shape[-2], x.shape[-1]
        feat = self.stem(x)
        out = self.seg(feat)
        if out.shape[-2:] != (h, w):
            out = F.interpolate(out, size=(h, w), mode="bilinear", align_corners=False)
        return out
```

- [ ] **Step 4: Run it — PASS (2 passed)**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_ink_repro_model.py -v`

- [ ] **Step 5: Commit**

```bash
git add repro/ink_segformer/model.py tests/test_ink_repro_model.py
git commit -m "feat(repro): 2.5D InkSegformer (3D stem + max-z + smp.Segformer)"
```

---

## Task 4: Loss + overfit smoke (pipeline learns) — TDD

**Files:**
- Create: `repro/ink_segformer/losses.py`
- Test: `tests/test_ink_repro_losses.py`

- [ ] **Step 1: Write the failing test** (loss correctness + a synthetic overfit proving train wiring)

```python
# tests/test_ink_repro_losses.py
import torch

from repro.ink_segformer.losses import bce_dice_loss
from repro.ink_segformer.model import InkSegformer


def test_bce_dice_zero_on_perfect_prediction():
    target = (torch.rand(2, 1, 16, 16) > 0.5).float()
    logits = torch.where(target > 0.5, 12.0, -12.0)  # near-perfect logits
    assert bce_dice_loss(logits, target).item() < 0.05


def test_overfits_a_tiny_separable_batch():
    # ink = whether the depth-mean pixel exceeds 0.5 -> learnable from the input
    torch.manual_seed(0)
    x = torch.rand(2, 1, 8, 64, 64)
    target = (x[:, 0].mean(1, keepdim=True) > 0.5).float()  # [2,1,64,64]
    model = InkSegformer(stem_channels=8, encoder="mit_b3", encoder_weights=None)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    for _ in range(60):
        opt.zero_grad()
        loss = bce_dice_loss(model(x), target)
        loss.backward()
        opt.step()
    with torch.no_grad():
        acc = ((torch.sigmoid(model(x)) > 0.5).float() == target).float().mean()
    assert acc.item() > 0.85  # the clean-room pipeline can learn
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError: repro.ink_segformer.losses`)

- [ ] **Step 3: Write `losses.py`**

```python
# repro/ink_segformer/losses.py
import torch
import torch.nn.functional as F


def bce_dice_loss(logits, target, mask=None, smooth=1.0):
    """BCE + soft Dice on ink logits. Optional papyrus `mask` restricts both terms
    to masked pixels (background excluded)."""
    if mask is None:
        bce = F.binary_cross_entropy_with_logits(logits, target)
    else:
        bce_map = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        bce = (bce_map * mask).sum() / mask.sum().clamp_min(1.0)
    p = torch.sigmoid(logits)
    if mask is not None:
        p, target = p * mask, target * mask
    inter = (p * target).sum(dim=(-2, -1))
    union = p.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    dice = 1.0 - (2.0 * inter + smooth) / (union + smooth)
    return bce + dice.mean()
```

- [ ] **Step 4: Run it — PASS (2 passed)** (the overfit test takes ~20-40 s on CPU; fine)

- [ ] **Step 5: Commit**

```bash
git add repro/ink_segformer/losses.py tests/test_ink_repro_losses.py
git commit -m "feat(repro): bce+dice loss + synthetic overfit proof"
```

---

## Task 5: Trainer (leave-one-fragment-out)

**Files:**
- Create: `repro/ink_segformer/train.py`

No unit test (full GPU run); validated by the Task 6 training run. Reuses `scripts/pixel_auc.py` for the honest val metric.

- [ ] **Step 1: Write `train.py`**

```python
# repro/ink_segformer/train.py
import argparse
import os
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _R)

from repro.ink_segformer.config import ReproConfig
from repro.ink_segformer.dataset import InkTileDataset
from repro.ink_segformer.losses import bce_dice_loss
from repro.ink_segformer.model import InkSegformer
from scripts.pixel_auc import pooled_pixel_auc


def _frag_dirs(cfg, ids):
    return [os.path.join(cfg.data_root, str(i)) for i in ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--val", type=int, default=1, help="held-out fragment id (1/2/3)")
    ap.add_argument("--epochs", type=int, default=ReproConfig.epochs)
    ap.add_argument("--out", default="repro/ink_segformer/runs/model_val{val}.pt")
    args = ap.parse_args()
    cfg = ReproConfig(epochs=args.epochs)
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    dev = torch.device("cuda")

    train_ids = [i for i in (1, 2, 3) if i != args.val]
    tr = InkTileDataset(_frag_dirs(cfg, train_ids), cfg.tile, cfg.stride, cfg.z_start, cfg.z_count, cfg.min_papyrus, augment=True)
    va = InkTileDataset(_frag_dirs(cfg, [args.val]), cfg.tile, cfg.stride, cfg.z_start, cfg.z_count, cfg.min_papyrus, augment=False)
    tl = DataLoader(tr, batch_size=cfg.batch_size, shuffle=True, num_workers=4, drop_last=True, pin_memory=True)
    vl = DataLoader(va, batch_size=cfg.batch_size, shuffle=False, num_workers=4)
    print(f"train tiles={len(tr)} (frags {train_ids})  val tiles={len(va)} (frag {args.val})")

    model = InkSegformer(cfg.stem_channels, cfg.encoder, encoder_weights="imagenet").to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs * len(tl))
    scaler = torch.cuda.amp.GradScaler()

    best = 0.0
    out_path = args.out.format(val=args.val)
    for ep in range(cfg.epochs):
        model.train()
        for vol, ink, pmask in tl:
            vol, ink, pmask = vol.to(dev), ink.to(dev), pmask.to(dev)
            opt.zero_grad()
            with torch.cuda.amp.autocast():
                loss = bce_dice_loss(model(vol), ink, mask=pmask)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
        # validation: pooled pixel AUC over masked pixels
        model.eval()
        probs, labels = [], []
        with torch.no_grad():
            for vol, ink, pmask in vl:
                p = torch.sigmoid(model(vol.to(dev))).cpu().numpy()
                m = pmask.numpy() > 0.5
                for b in range(p.shape[0]):
                    sel = m[b, 0]
                    if sel.sum() > 0:
                        probs.append(p[b, 0][sel].ravel())
                        labels.append(ink[b, 0].numpy()[sel].ravel())
        auc = pooled_pixel_auc(probs, labels) if probs else 0.5
        print(f"epoch {ep+1}/{cfg.epochs}  loss={loss.item():.4f}  val_pixel_auc={auc:.4f}")
        if auc > best:
            best = auc
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            torch.save({"model": model.state_dict(), "cfg": vars(cfg), "val_auc": auc, "val_frag": args.val}, out_path)
    print(f"BEST val_pixel_auc={best:.4f}  saved {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add repro/ink_segformer/train.py
git commit -m "feat(repro): leave-one-fragment-out SegFormer trainer"
```

---

## Task 6: Inference (sliding-window + TTA)

**Files:**
- Create: `repro/ink_segformer/infer.py`

- [ ] **Step 1: Write `infer.py`**

```python
# repro/ink_segformer/infer.py
import os
import sys

import numpy as np
import torch

_R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _R)

from repro.ink_segformer.dataset import compute_tile_origins, read_middle_layers
from PIL import Image


def predict_fragment(model, frag_dir, cfg, device, tta=True):
    """Sliding-window inference over a full fragment with overlap-averaging and
    flip/rot90 TTA. Returns a float32 probability map [H, W]."""
    vol = read_middle_layers(frag_dir, cfg.z_start, cfg.z_count)  # [D,H,W]
    mask = (np.array(Image.open(os.path.join(frag_dir, "mask.png")).convert("L")) > 127)
    H, W = mask.shape
    acc = np.zeros((H, W), np.float32)
    cnt = np.zeros((H, W), np.float32)
    t = cfg.tile
    model.eval()
    for (y, x) in compute_tile_origins(mask, t, cfg.stride, min_papyrus=0.0):
        chunk = torch.from_numpy(vol[:, y : y + t, x : x + t]).unsqueeze(0).unsqueeze(0).float().to(device)
        views = [chunk]
        if tta:
            views += [torch.rot90(chunk, k, dims=(-2, -1)) for k in (1, 2, 3)]
            views.append(torch.flip(chunk, dims=(-1,)))
        preds = []
        with torch.no_grad():
            for i, v in enumerate(views):
                p = torch.sigmoid(model(v))
                if tta and 1 <= i <= 3:
                    p = torch.rot90(p, -i, dims=(-2, -1))
                elif tta and i == 4:
                    p = torch.flip(p, dims=(-1,))
                preds.append(p)
        p = torch.stack(preds).mean(0)[0, 0].cpu().numpy()
        acc[y : y + t, x : x + t] += p
        cnt[y : y + t, x : x + t] += 1.0
    prob = np.divide(acc, cnt, out=np.zeros_like(acc), where=cnt > 0)
    return prob * mask
```

- [ ] **Step 2: Smoke-check it imports**

Run: `PYTHONPATH=. .venv/bin/python -c "import repro.ink_segformer.infer as m; print('ok', hasattr(m,'predict_fragment'))"`
Expected: `ok True`

- [ ] **Step 3: Commit**

```bash
git add repro/ink_segformer/infer.py
git commit -m "feat(repro): sliding-window TTA inference"
```

---

## Task 7: Evaluation (AUC + Fβ + ink PNG)

**Files:**
- Create: `repro/ink_segformer/evaluate.py`

- [ ] **Step 1: Write `evaluate.py`**

```python
# repro/ink_segformer/evaluate.py
import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

Image.MAX_IMAGE_PIXELS = None


def evaluate_fragment(prob, ink_png, mask_png):
    """Pixel AUC + best-Fβ(0.5) over masked pixels. Returns a dict."""
    ink = (np.array(Image.open(ink_png).convert("L")) > 127).astype(int)
    mask = (np.array(Image.open(mask_png).convert("L")) > 127)
    p, y = prob[mask].ravel(), ink[mask].ravel()
    auc = float(roc_auc_score(y, p)) if y.min() != y.max() else 0.5
    best_f, best_t = 0.0, 0.5
    for t in np.linspace(0.1, 0.9, 17):
        pred = (p > t).astype(int)
        tp = int((pred & y).sum()); fp = int((pred & (1 - y)).sum()); fn = int(((1 - pred) & y).sum())
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        b2 = 0.25
        f = (1 + b2) * prec * rec / (b2 * prec + rec) if (b2 * prec + rec) else 0.0
        if f > best_f:
            best_f, best_t = f, float(t)
    return {"pixel_auc": auc, "fbeta0.5": best_f, "threshold": best_t}


def save_ink_png(prob, out_path, threshold=None):
    """Save the probability heatmap (and a thresholded version) as PNGs for visual
    legibility inspection."""
    Image.fromarray((np.clip(prob, 0, 1) * 255).astype(np.uint8)).save(out_path)
    if threshold is not None:
        Image.fromarray(((prob > threshold) * 255).astype(np.uint8)).save(
            out_path.replace(".png", f"_thr{threshold:.2f}.png")
        )
```

- [ ] **Step 2: Smoke-check on synthetic arrays**

Run:
```bash
PYTHONPATH=. .venv/bin/python -c "
import numpy as np, tempfile, os; from PIL import Image
from repro.ink_segformer.evaluate import evaluate_fragment, save_ink_png
d=tempfile.mkdtemp(); ink=np.zeros((20,20),np.uint8); ink[5:15,5:15]=255
Image.fromarray(ink).save(d+'/i.png'); Image.fromarray(np.full((20,20),255,np.uint8)).save(d+'/m.png')
prob=(ink>0).astype(np.float32)*0.9+0.05
r=evaluate_fragment(prob, d+'/i.png', d+'/m.png'); print(r); assert r['pixel_auc']>0.99
save_ink_png(prob, d+'/o.png', r['threshold']); print('png ok', os.path.exists(d+'/o.png'))
"
```
Expected: dict with `pixel_auc` ~1.0, `png ok True`.

- [ ] **Step 3: Commit**

```bash
git add repro/ink_segformer/evaluate.py
git commit -m "feat(repro): pixel-AUC/Fbeta eval + ink-PNG render"
```

---

## Task 8: Run the reproduction + success check + record (GPU, data-gated)

Requires Task 0 data. Pause the loop first.

- [ ] **Step 1: Pause the loop, free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 6
nvidia-smi --query-gpu=memory.used --format=csv,noheader
```

- [ ] **Step 2: Train (held out fragment 1; ~hours)**

```bash
PYTHONPATH=. .venv/bin/python repro/ink_segformer/train.py --val 1 2>&1 | tee repro/ink_segformer/runs/train_val1.log | tail -5
```
Watch `val_pixel_auc` climb across epochs. Expected: clearly above 0.5 (target ≥ 0.75).

- [ ] **Step 3: Infer + evaluate the held-out fragment + render the ink PNG**

```bash
PYTHONPATH=. .venv/bin/python - <<'PYEOF'
import os, sys, json, torch, numpy as np
sys.path.insert(0, ".")
from repro.ink_segformer.config import ReproConfig
from repro.ink_segformer.model import InkSegformer
from repro.ink_segformer.infer import predict_fragment
from repro.ink_segformer.evaluate import evaluate_fragment, save_ink_png
cfg = ReproConfig(); dev = torch.device("cuda")
ck = torch.load("repro/ink_segformer/runs/model_val1.pt", map_location="cpu")
m = InkSegformer(cfg.stem_channels, cfg.encoder, encoder_weights=None).to(dev)
m.load_state_dict(ck["model"]); m.eval()
frag = os.path.join(cfg.data_root, "1")
prob = predict_fragment(m, frag, cfg, dev, tta=True)
r = evaluate_fragment(prob, frag + "/inklabels.png", frag + "/mask.png")
print("HELD-OUT FRAGMENT 1:", json.dumps(r))
save_ink_png(prob, "repro/ink_segformer/runs/ink_frag1.png", r["threshold"])
print("rendered repro/ink_segformer/runs/ink_frag1.png (+ thresholded)")
PYEOF
```

- [ ] **Step 4: Success check**

Open `repro/ink_segformer/runs/ink_frag1.png` (and the `_thr` version). Success = **pixel_auc ≥ 0.75 AND visibly legible ink** (strokes/letters, not noise). If AUC is high but the image is noise, or vice versa, investigate (normalization, layer range, tile size) before declaring success. Optionally repeat `--val 2` / `--val 3` for a full leave-one-out picture.

- [ ] **Step 5: Record + restore loop**

Write a FINDINGS.md bullet and a memory file `ink-detection-reproduction-result.md` (type project) with the held-out AUC/Fβ, whether ink was legible, and the verdict (did the clean-room recipe detect ink where our 64px pipeline could not?). Add the ink PNG to the repo under `reports/` if legible. Then:
```bash
git add FINDINGS.md
git commit -m "docs(findings): clean-room SegFormer ink-detection reproduction result"
git push origin main
rm -f .loop_paused && bash start.sh
```

---

## Self-Review

**Spec coverage:**
- Data acquisition (Kaggle, user-gated, expected layout) → Task 0. ✓
- 3D-stem + max-z + smp.Segformer architecture → Task 3. ✓
- Tiled dataset (middle layers, papyrus-gated, leave-one-out via frag dirs) → Task 2 + Task 5. ✓
- BCE+Dice, augment, AMP, leave-one-fragment-out trainer → Tasks 4-5. ✓
- Sliding-window TTA inference → Task 6. ✓
- Pixel AUC + Fβ + ink PNG evaluator → Task 7. ✓
- Success criterion (held-out AUC ≥ 0.75 + legible ink) → Task 8 Step 4. ✓
- Overfit smoke proving the pipeline learns → Task 4 (synthetic). ✓
- Isolation (own dir, reuse venv, no loop/train.py imports) + loop-paused GPU runs → structure + Task 8. ✓
- Reuse `scripts/pixel_auc.py` → Task 5. ✓

**Placeholder scan:** None. Synthetic fixtures make Tasks 2-4 + 7 runnable without the Kaggle data; only Task 8 (and Task 0) need it.

**Type consistency:** `InkTileDataset(frag_dirs, tile, stride, z_start, z_count, min_papyrus, augment)` is constructed identically in tests and trainer; `InkSegformer(stem_channels, encoder, encoder_weights)` signature matches tests/trainer/infer; dataset returns `(vol[1,D,H,W], ink[1,H,W], pmask[1,H,W])` consumed consistently by loss (`mask=pmask`) and trainer; `predict_fragment(model, frag_dir, cfg, device, tta)` and `evaluate_fragment(prob, ink_png, mask_png)` signatures match their call sites in Task 8; `pooled_pixel_auc(prob_arrays, label_arrays)` reused as defined.

**Known risk:** the exact Kaggle mirror layout (`train/{1,2,3}` vs `{1,2,3}`) — Task 0 Step 4 verifies and `config.data_root` absorbs the difference. `encoder_weights="imagenet"` downloads mit-b3 weights on first train run (network needed once); tests use `encoder_weights=None`.
