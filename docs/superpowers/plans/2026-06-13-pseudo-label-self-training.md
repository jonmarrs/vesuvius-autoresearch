# Same-Scroll Pseudo-Label Self-Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lift the detector's held-out ink AUC by training on confidence-filtered pseudo-labels of a spatially-disjoint "unlabeled" region of the same scroll, measured with zero validation leakage and bounded by an oracle run.

**Architecture:** Split Fr143 into disjoint U-region (pseudo-labeled) and V-region (validation) with a 128px buffer. A fresh Fr47-only model is both the honest baseline and the leak-free pseudo-labeler. Self-train (Fr47 + U-pseudo) and oracle (Fr47 + U-true) models are compared against baseline on V-region AUC. The uncertain confidence band is encoded as 0.5 in the pseudo-label PNG and down-weighted in the ink loss via a per-pixel weight `w = 2·|target−0.5|`, recomputed after augmentation (so it survives mixup/affine) and a no-op on true 0/1 labels.

**Tech Stack:** Python, PyTorch, NumPy, Pillow, scikit-learn (`roc_auc_score`), pytest. Reuses `VesuviusLabeledDataset`, `FastVesuviusVolume`, `build_inference_model`, `scripts/measure_ink_auc.py`, and the existing `scripts/training/train.py` loop.

**Spec:** `docs/superpowers/specs/2026-06-13-pseudo-label-self-training-design.md`

---

## File Structure

- `scripts/spatial_split_mask.py` (create) — split a 2D mask PNG into disjoint region masks with a buffer.
- `scripts/generate_pseudo_labels.py` (create) — tiled inference of a checkpoint over a region; write a 3-value (0/128/255) pseudo-label PNG.
- `scripts/pseudo_label_quality_report.py` (create) — compare a pseudo-label PNG against true labels within a region (coverage, AUC, precision/recall).
- `scripts/training/train.py` (modify) — add `use_confidence_weight` config flag + confidence-weighted ink BCE/Dice; add `weight=` to `compute_dice_loss`.
- `experiments/pseudo_label/cfg_baseline.json`, `cfg_selftrain.json`, `cfg_oracle.json` (create) — the three run configs.
- `tests/test_spatial_split_mask.py`, `tests/test_confidence_weighted_loss.py`, `tests/test_generate_pseudo_labels.py`, `tests/test_pseudo_label_quality.py` (create).
- `local_data/PHercParis2Fr143_Uregion/`, `local_data/PHercParis2Fr143_Vregion/` (create at runtime, gitignored) — symlinked volume + region masks + labels.
- `FINDINGS.md`, memory (modify) — record results.

---

## Task 1: Spatial split mask tool

**Files:**
- Create: `scripts/spatial_split_mask.py`
- Test: `tests/test_spatial_split_mask.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spatial_split_mask.py
import numpy as np
from PIL import Image

from scripts.spatial_split_mask import split_mask


def test_split_produces_disjoint_regions_with_buffer():
    # 100-wide full mask (all valid)
    mask = np.ones((20, 100), dtype=bool)
    u, v = split_mask(mask, axis=1, fraction=0.5, buffer=10)
    # U is the left part up to 50 - 5 = 45; V is right from 50 + 5 = 55
    assert u[:, :45].all() and not u[:, 45:].any()
    assert v[:, 55:].all() and not v[:, :55].any()
    # Disjoint: no column is in both
    assert not (u & v).any()
    # Buffer columns [45:55] belong to neither
    assert not u[:, 45:55].any() and not v[:, 45:55].any()


def test_split_respects_original_mask():
    mask = np.zeros((10, 100), dtype=bool)
    mask[:, 10:90] = True  # only middle is valid surface
    u, v = split_mask(mask, axis=1, fraction=0.5, buffer=10)
    # Regions are subsets of the original mask
    assert (u <= mask).all() and (v <= mask).all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch && PYTHONPATH=. .venv/bin/python -m pytest tests/test_spatial_split_mask.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.spatial_split_mask'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/spatial_split_mask.py
"""Split a 2D boolean surface mask into two spatially-disjoint region masks
separated by a discarded buffer strip, so patches sampled from each region
share no pixels (train/predict non-overlap).
"""

import argparse

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def split_mask(mask: np.ndarray, axis: int = 1, fraction: float = 0.5, buffer: int = 128):
    """Return (u_mask, v_mask): the original mask restricted to the low-index
    region and high-index region along `axis`, with a `buffer`-wide gap between
    them removed from both. fraction sets the split point along `axis`.
    """
    n = mask.shape[axis]
    split = int(n * fraction)
    lo_end = split - buffer // 2
    hi_start = split + buffer // 2
    u = mask.copy()
    v = mask.copy()
    idx_u = [slice(None)] * mask.ndim
    idx_v = [slice(None)] * mask.ndim
    idx_u[axis] = slice(lo_end, None)  # zero everything at/after lo_end
    idx_v[axis] = slice(None, hi_start)  # zero everything before hi_start
    u[tuple(idx_u)] = False
    v[tuple(idx_v)] = False
    return u, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mask", required=True, help="path to mask.png")
    ap.add_argument("--out-u", required=True)
    ap.add_argument("--out-v", required=True)
    ap.add_argument("--axis", type=int, default=1)
    ap.add_argument("--fraction", type=float, default=0.5)
    ap.add_argument("--buffer", type=int, default=128)
    args = ap.parse_args()

    mask = np.array(Image.open(args.mask).convert("L")) > 127
    u, v = split_mask(mask, args.axis, args.fraction, args.buffer)
    Image.fromarray((u * 255).astype(np.uint8)).save(args.out_u)
    Image.fromarray((v * 255).astype(np.uint8)).save(args.out_v)
    print(
        f"U maskpx={int(u.sum()):,} V maskpx={int(v.sum()):,} "
        f"disjoint={not bool((u & v).any())}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_spatial_split_mask.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/spatial_split_mask.py tests/test_spatial_split_mask.py
git commit -m "feat(pseudo): spatial mask split tool with disjoint buffer"
```

---

## Task 2: Confidence-weighted ink loss in train.py

**Files:**
- Modify: `scripts/training/train.py` (config dataclass ~line 182; `compute_dice_loss` line 706; ink-loss block line 1685-1699)
- Test: `tests/test_confidence_weighted_loss.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_confidence_weighted_loss.py
import os
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "training"))

from train import compute_dice_loss, confidence_weight  # noqa: E402


def test_confidence_weight_zero_on_uncertain_band():
    # target 0.5 -> weight 0; target 0 or 1 -> weight 1
    target = torch.tensor([[0.0, 0.5, 1.0]])
    w = confidence_weight(target)
    assert torch.allclose(w, torch.tensor([[1.0, 0.0, 1.0]]))


def test_uncertain_pixels_contribute_zero_ink_gradient():
    # A logit map; only the uncertain (0.5) pixel differs from a confident map.
    torch.manual_seed(0)
    logits = torch.randn(1, 1, 4, 4, requires_grad=True)
    target = torch.full((1, 1, 4, 4), 0.5)  # entirely uncertain
    w = confidence_weight(target)
    bce_map = torch.nn.functional.binary_cross_entropy_with_logits(
        logits, target.clamp(0, 1), reduction="none"
    )
    loss = (bce_map * w).sum() / w.sum().clamp_min(1.0)
    loss.backward()
    # All pixels uncertain -> zero weight -> zero gradient everywhere.
    assert torch.allclose(logits.grad, torch.zeros_like(logits.grad))


def test_dice_loss_weight_is_noop_on_binary_target():
    pred = torch.randn(2, 1, 8, 8)
    target = (torch.rand(2, 1, 8, 8) > 0.5).float()
    w = confidence_weight(target)  # all ones for binary target
    assert torch.allclose(
        compute_dice_loss(pred, target, weight=w), compute_dice_loss(pred, target)
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_confidence_weighted_loss.py -v`
Expected: FAIL with `ImportError: cannot import name 'confidence_weight'`

- [ ] **Step 3: Add `confidence_weight` and weight support in `compute_dice_loss`**

In `scripts/training/train.py`, add the helper just above `compute_dice_loss` (line 706):

```python
def confidence_weight(target):
    """Per-pixel confidence weight for soft pseudo-labels: 1.0 where the label
    is confident (0 or 1), 0.0 in the uncertain band (encoded as 0.5). Recomputed
    from the (possibly augmented) target each step, so it survives mixup/affine
    interpolation, and is a no-op on true binary labels."""
    return (2.0 * (target - 0.5).abs()).clamp(0.0, 1.0)
```

Replace `compute_dice_loss` (lines 706-721) with a `weight`-aware version:

```python
def compute_dice_loss(pred_2d, target, smooth=1e-5, weight=None):
    """
    Standard Dice Loss for 2D ink detection. Optional per-pixel `weight`
    down-weights pixels (e.g. uncertain pseudo-label band); weight=None is the
    original unweighted behavior.
    """
    pred_2d = torch.sigmoid(pred_2d)

    if target.dim() == 3:
        target = target.unsqueeze(1)

    if weight is not None:
        if weight.dim() == 3:
            weight = weight.unsqueeze(1)
        pred_2d = pred_2d * weight
        target = target * weight

    intersection = (pred_2d * target).sum(dim=(-2, -1))
    union = pred_2d.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))

    dice = (2.0 * intersection + smooth) / (union + smooth)
    return 1.0 - dice.mean()
```

- [ ] **Step 4: Add the `use_confidence_weight` config flag**

In the `ExperimentConfig` dataclass, next to `label_smoothing` (line ~181), add:

```python
    use_confidence_weight: bool = False
```

- [ ] **Step 5: Apply the weight in the supervised ink-loss block**

Replace the ink BCE + dice block (lines 1685-1699) with:

```python
            # Supervised Losses
            if getattr(config, "use_confidence_weight", False):
                # Soft pseudo-labels encode the uncertain band as 0.5; down-weight
                # those pixels to ~0 so they contribute no gradient. No-op on true
                # binary labels (weight == 1 everywhere).
                conf_w = confidence_weight(target_ink_aug1)
                bce_map = F.binary_cross_entropy_with_logits(
                    out_ink_2d, target_ink_aug1.clamp(0, 1), reduction="none"
                )
                loss_ink = (bce_map * conf_w).sum() / conf_w.sum().clamp_min(1.0)
                loss_dice = compute_dice_loss(
                    out_ink_2d, target_ink_aug1.clamp(0, 1), weight=conf_w
                )
            elif config.label_smoothing > 0:
                smoothed_target = (
                    target_ink_aug1 * (1.0 - config.label_smoothing)
                    + 0.5 * config.label_smoothing
                )
                loss_ink = F.binary_cross_entropy_with_logits(
                    out_ink_2d, smoothed_target
                )
                loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)
            else:
                loss_ink = F.binary_cross_entropy_with_logits(
                    out_ink_2d, target_ink_aug1, pos_weight=None, reduction="mean"
                )
                loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)
```

Then delete the now-duplicated standalone `loss_dice = compute_dice_loss(out_ink_2d, target_ink_aug1)` at the old line 1699 (it is now computed inside every branch above).

- [ ] **Step 6: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_confidence_weighted_loss.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Verify the loop's default path is unchanged**

Run: `PYTHONPATH=. .venv/bin/python -c "import sys; sys.path.insert(0,'scripts/training'); from train import compute_dice_loss, confidence_weight; import torch; t=(torch.rand(1,1,8,8)>0.5).float(); p=torch.randn(1,1,8,8); print('dice noop:', torch.allclose(compute_dice_loss(p,t), compute_dice_loss(p,t,weight=confidence_weight(t))))"`
Expected: `dice noop: True` (confirms binary-label training is byte-identical to before).

- [ ] **Step 8: Commit**

```bash
git add scripts/training/train.py tests/test_confidence_weighted_loss.py
git commit -m "feat(train): confidence-weighted ink loss for pseudo-label uncertainty"
```

---

## Task 2B: `checkpoint_out` isolation (protect loop state)

**Files:**
- Modify: `scripts/training/train.py` (config dataclass ~line 182; persist block lines 2116-2202)

`train.py` saves `best_model.pt`/`last_model.pt` and appends to `history.tsv`/`prize_readiness.tsv` in the CWD, gated by an `is_improvement` comparison against the existing `best_model.pt`. A standalone experiment run validates on the **V-region** (a different val set), so its `val_bpb` is not comparable — it could spuriously "improve" and **clobber the production `best_model.pt`** and pollute loop logs. This task adds a `checkpoint_out` path that, when set, saves only to that file and skips all loop bookkeeping. Default (`None`) behavior is byte-identical to today.

- [ ] **Step 1: Add the config field**

In the `ExperimentConfig` dataclass next to `use_confidence_weight` (Task 2), add:

```python
    checkpoint_out: str | None = None
```

- [ ] **Step 2: Skip the history.tsv append when `checkpoint_out` is set**

Wrap the history block (lines 2116-2128). Change:

```python
    # Log EVERY run to history.tsv for auditability
    history_file = "history.tsv"
```
to:
```python
    # Log EVERY run to history.tsv for auditability — UNLESS this is an isolated
    # experiment run (checkpoint_out set), which must not touch loop state.
    if not getattr(config, "checkpoint_out", None):
      history_file = "history.tsv"
```
and indent the existing `history_header`/`if not os.path.exists`/`with open(history_file, "a")` block (lines 2118-2128) one level under that `if`.

- [ ] **Step 3: Branch the model save on `checkpoint_out`**

Replace the `if is_improvement:` … `last_model.pt` … persistence block (lines 2130-2202) so it begins:

```python
    ckpt_out = getattr(config, "checkpoint_out", None)
    if ckpt_out:
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "val_bpb": val_bpb,
                "avg_skel_dist": avg_skel_dist,
                "avg_centerline_dice": avg_centerline_dice,
                "avg_cc_diff": avg_cc_diff,
                "avg_mean_ap": avg_mean_ap,
                "submittable": submittable,
                "window_ok": window_ok,
                "window_mm": window_mm,
                "villa_metrics_ok": villa_metrics_ok,
                "config": asdict(config),
            },
            ckpt_out,
        )
        print(f"Saved experiment checkpoint to {ckpt_out} (loop state untouched)")
    elif is_improvement:
        print(f"Saving new best model with val_bpb: {val_bpb:.6f}")
        torch.save(
```
(The existing `is_improvement` body and the trailing `else:`/`last_model.pt` branch stay exactly as-is under the new `elif`/`else`.)

- [ ] **Step 4: Verify default behavior is unchanged (syntax + no-op import)**

Run: `PYTHONPATH=. .venv/bin/python -c "import sys; sys.path.insert(0,'scripts/training'); import train; print('import OK')"`
Expected: `import OK` (no syntax/indent error).

- [ ] **Step 5: Commit**

```bash
git add scripts/training/train.py
git commit -m "feat(train): checkpoint_out isolates experiment runs from loop state"
```

---

## Task 3: Pseudo-label generation tool

**Files:**
- Create: `scripts/generate_pseudo_labels.py`
- Test: `tests/test_generate_pseudo_labels.py`

The tool runs a checkpoint over a fragment's region (restricted by a region mask) with sliding-window tiling, averaging overlapping predictions, and writes a 3-value PNG: `255` where prob > τ_high (ink), `0` where prob < τ_low (background), `128` in the uncertain band (loss-ignored via the confidence weight). The core thresholding logic is factored into a pure function so it is unit-testable without a GPU.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_generate_pseudo_labels.py
import numpy as np

from scripts.generate_pseudo_labels import prob_to_pseudo_png


def test_prob_to_pseudo_three_values():
    prob = np.array([[0.05, 0.5, 0.9]], dtype=np.float32)
    region = np.ones_like(prob, dtype=bool)
    out = prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15)
    # 0.05<0.15 -> bg(0); 0.5 in band -> ignore(128); 0.9>0.65 -> ink(255)
    assert out.tolist() == [[0, 128, 255]]


def test_outside_region_is_ignore():
    prob = np.array([[0.9, 0.9]], dtype=np.float32)
    region = np.array([[True, False]])
    out = prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15)
    # Pixel outside the region -> ignore(128) regardless of prob
    assert out.tolist() == [[255, 128]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_generate_pseudo_labels.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.generate_pseudo_labels'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/generate_pseudo_labels.py
"""Generate confidence-filtered pseudo-labels for a fragment region using a
trained checkpoint. Output is a 3-value PNG (0=bg, 255=ink, 128=uncertain/ignore)
consumed as inklabels.png by a region fragment dir; the 128 band is down-weighted
to zero in train.py's confidence-weighted ink loss.
"""

import argparse
import os
import sys

import numpy as np
import torch
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))


def prob_to_pseudo_png(prob, region, tau_high=0.65, tau_low=0.15):
    """Map a [H,W] probability map + boolean region mask to a uint8 pseudo-label:
    255 (ink) where prob>tau_high, 0 (bg) where prob<tau_low, else 128 (ignore).
    Pixels outside `region` are always 128 (ignore)."""
    out = np.full(prob.shape, 128, dtype=np.uint8)
    out[(prob > tau_high) & region] = 255
    out[(prob < tau_low) & region] = 0
    return out


def _infer_region(checkpoint, frag_dir, region_mask_path, device, tau_high, tau_low):
    from train import ExperimentConfig, load_shape_compatible_state

    from vesuvius_autoresearch.core.model_wrappers import build_inference_model
    from vesuvius_autoresearch.core.vesuvius_loader import (
        VesuviusLabeledDataset,
        _volume_uri_for,
    )

    # Reuse measure_ink_auc's volume-uri convention.
    from measure_ink_auc import _volume_uri  # type: ignore

    chk = torch.load(checkpoint, map_location="cpu", weights_only=False)
    s = chk.get("config", {})
    ps, nl = s.get("patch_size", 64), s.get("num_layers", 16)
    config = ExperimentConfig.load("config.json")
    model = build_inference_model(
        architecture=s.get("architecture", "resenc_unet"),
        patch_size=ps,
        num_layers=nl,
        base_feat=s.get("base_feat", 64),
        num_blocks=s.get("num_blocks", 16),
        num_heads=s.get("num_heads", 8),
        dropout=s.get("dropout", 0.0),
        use_ridges=s.get("use_ridges", config.use_ridges),
        multi_task_heads=s.get("multi_task_heads", False),
    ).to(device)
    load_shape_compatible_state(model, chk["model_state_dict"], checkpoint)
    model.eval()

    # Sample patches via the dataset restricted to the region mask, predict, and
    # paint probabilities back into a full-size accumulator (mean over overlaps).
    ds = VesuviusLabeledDataset(
        _volume_uri(frag_dir),
        os.path.join(frag_dir, "inklabels.png"),
        region_mask_path,
        ps,
        nl + 8,
        seed=7,
        cache_dir=config.cache_dir,
        use_ridges=s.get("use_ridges", config.use_ridges),
        ridge_sigma=getattr(config, "ridge_sigma", 2.0),
        use_lasagna=False,
        require_ink=False,  # cover the whole region, not just ink patches
    )
    H, W = ds.shape[1], ds.shape[2]
    prob_sum = np.zeros((H, W), dtype=np.float32)
    prob_cnt = np.zeros((H, W), dtype=np.float32)
    with torch.no_grad():
        for i in range(len(ds)):
            x_raw, _, _ = ds[i]
            y0, x0 = ds.valid_coords[i]
            x = x_raw[:, 4 : 4 + nl].unsqueeze(0).to(device)
            out = model(x)
            out = out[0] if isinstance(out, tuple) else out
            p = torch.sigmoid(out).squeeze().float().cpu().numpy()
            prob_sum[y0 : y0 + ps, x0 : x0 + ps] += p
            prob_cnt[y0 : y0 + ps, x0 : x0 + ps] += 1.0
    prob = np.divide(prob_sum, prob_cnt, out=np.zeros_like(prob_sum), where=prob_cnt > 0)
    region = (np.array(Image.open(region_mask_path).convert("L")) > 127) & (prob_cnt > 0)
    return prob_to_pseudo_png(prob, region, tau_high, tau_low)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--fragment", required=True, help="fragment dir (volume + labels)")
    ap.add_argument("--region-mask", required=True)
    ap.add_argument("--out", required=True, help="output pseudo-label PNG")
    ap.add_argument("--tau-high", type=float, default=0.65)
    ap.add_argument("--tau-low", type=float, default=0.15)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    out = _infer_region(
        args.checkpoint,
        args.fragment,
        args.region_mask,
        torch.device(args.device),
        args.tau_high,
        args.tau_low,
    )
    frac_ink = float((out == 255).mean())
    frac_ign = float((out == 128).mean())
    if frac_ink < 1e-4 or frac_ink > 0.99:
        raise SystemExit(
            f"Degenerate pseudo-labels (ink frac={frac_ink:.4f}); aborting. "
            f"Adjust tau or check the checkpoint."
        )
    Image.fromarray(out).save(args.out)
    print(f"wrote {args.out}: ink={frac_ink:.3f} ignore={frac_ign:.3f}")


if __name__ == "__main__":
    main()
```

Note: if `_volume_uri_for` is not importable from the loader, the `from measure_ink_auc import _volume_uri` line already provides the needed helper; remove the unused loader import. Verify the import resolves in Step 4; fix the import line if the smoke run reports an ImportError.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_generate_pseudo_labels.py -v`
Expected: PASS (2 passed). (The test only exercises `prob_to_pseudo_png`, which needs no GPU.)

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_pseudo_labels.py tests/test_generate_pseudo_labels.py
git commit -m "feat(pseudo): confidence-filtered pseudo-label generation"
```

---

## Task 4: Pseudo-label quality report

**Files:**
- Create: `scripts/pseudo_label_quality_report.py`
- Test: `tests/test_pseudo_label_quality.py`

Because we hold the U-region's true labels, we can quantify how good the pseudo-labels are before trusting any self-train result.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pseudo_label_quality.py
import numpy as np

from scripts.pseudo_label_quality_report import score_pseudo


def test_score_pseudo_perfect_labels():
    true = np.array([[1, 0, 1, 0]], dtype=np.uint8)  # binary truth
    pseudo = np.array([[255, 0, 255, 0]], dtype=np.uint8)  # matches, no ignore
    r = score_pseudo(pseudo, true)
    assert r["coverage"] == 1.0
    assert r["precision"] == 1.0 and r["recall"] == 1.0


def test_score_pseudo_ignores_uncertain_band():
    true = np.array([[1, 1, 0, 0]], dtype=np.uint8)
    pseudo = np.array([[255, 128, 128, 0]], dtype=np.uint8)  # 2 of 4 ignored
    r = score_pseudo(pseudo, true)
    assert r["coverage"] == 0.5  # half the pixels are confident
    # Among confident pixels (255->1, 0->0): both correct
    assert r["precision"] == 1.0 and r["recall"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pseudo_label_quality.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# scripts/pseudo_label_quality_report.py
"""Score confidence-filtered pseudo-labels against known ground truth within a
region: coverage (fraction of confident pixels) and precision/recall/AUC on the
confident subset. Used to judge pseudo-label quality before self-training."""

import argparse

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

Image.MAX_IMAGE_PIXELS = None


def score_pseudo(pseudo, true):
    """pseudo: uint8 [H,W] with values {0,128,255}; true: binary [H,W] (0/1 or
    0/255). Returns coverage + precision/recall/auc over confident pixels."""
    true_bin = (true > 127).astype(int) if true.max() > 1 else true.astype(int)
    confident = pseudo != 128
    coverage = float(confident.mean())
    if confident.sum() == 0:
        return {"coverage": 0.0, "precision": 0.0, "recall": 0.0, "auc": 0.5}
    pred = (pseudo[confident] == 255).astype(int)
    gt = true_bin[confident]
    tp = int(((pred == 1) & (gt == 1)).sum())
    fp = int(((pred == 1) & (gt == 0)).sum())
    fn = int(((pred == 0) & (gt == 1)).sum())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    auc = roc_auc_score(gt, pred) if gt.min() != gt.max() else 0.5
    return {
        "coverage": coverage,
        "precision": precision,
        "recall": recall,
        "auc": float(auc),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pseudo", required=True)
    ap.add_argument("--true", required=True, help="true inklabels.png")
    ap.add_argument("--region-mask", required=True)
    args = ap.parse_args()
    pseudo = np.array(Image.open(args.pseudo).convert("L"))
    true = np.array(Image.open(args.true).convert("L"))
    region = np.array(Image.open(args.region_mask).convert("L")) > 127
    # Restrict scoring to the region; outside-region pixels are 128 anyway.
    pseudo = np.where(region, pseudo, 128).astype(np.uint8)
    r = score_pseudo(pseudo, true)
    print(
        f"coverage={r['coverage']:.3f} precision={r['precision']:.3f} "
        f"recall={r['recall']:.3f} auc={r['auc']:.3f}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pseudo_label_quality.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/pseudo_label_quality_report.py tests/test_pseudo_label_quality.py
git commit -m "feat(pseudo): pseudo-label quality report vs ground truth"
```

---

## Task 5: Build split masks and region fragment dirs

**Files:**
- Create (runtime, not committed): `local_data/PHercParis2Fr143/mask_Uregion.png`, `mask_Vregion.png`; dirs `local_data/PHercParis2Fr143_Uregion/`, `local_data/PHercParis2Fr143_Vregion/`.

These dirs let the existing dir-convention dataloader serve region-restricted masks/labels with no train.py change. The volume is symlinked (it is multi-GB — never copied).

- [ ] **Step 1: Generate the split masks**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
PYTHONPATH=. .venv/bin/python scripts/spatial_split_mask.py \
  --mask local_data/PHercParis2Fr143/mask.png \
  --out-u local_data/PHercParis2Fr143/mask_Uregion.png \
  --out-v local_data/PHercParis2Fr143/mask_Vregion.png \
  --axis 1 --fraction 0.5 --buffer 128
```
Expected: `U maskpx=54,062,594 V maskpx=42,095,796 disjoint=True`

- [ ] **Step 2: Build the V-region fragment dir (validation, true labels)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p local_data/PHercParis2Fr143_Vregion
ln -sf "$(pwd)/local_data/PHercParis2Fr143/surface_volume.zarr" local_data/PHercParis2Fr143_Vregion/surface_volume.zarr
cp local_data/PHercParis2Fr143/inklabels.png local_data/PHercParis2Fr143_Vregion/inklabels.png
cp local_data/PHercParis2Fr143/mask_Vregion.png local_data/PHercParis2Fr143_Vregion/mask.png
```

- [ ] **Step 3: Build the U-region fragment dir scaffold (pseudo labels filled in Task 7)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p local_data/PHercParis2Fr143_Uregion
ln -sf "$(pwd)/local_data/PHercParis2Fr143/surface_volume.zarr" local_data/PHercParis2Fr143_Uregion/surface_volume.zarr
cp local_data/PHercParis2Fr143/mask_Uregion.png local_data/PHercParis2Fr143_Uregion/mask.png
# inklabels.png (pseudo) is written by Task 7; true labels kept for the oracle/quality report:
cp local_data/PHercParis2Fr143/inklabels.png local_data/PHercParis2Fr143_Uregion/inklabels_true.png
```

- [ ] **Step 4: Verify the alignment guard accepts the region fragments**

Run:
```bash
PYTHONPATH=. .venv/bin/python -c "
import os
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset
for d in ['local_data/PHercParis2Fr143_Vregion']:
    ds=VesuviusLabeledDataset(d+'/surface_volume.zarr', d+'/inklabels.png', d+'/mask.png', 64, 24, seed=7, require_ink=True)
    print(d, 'patches=', len(ds))
"
```
Expected: prints a positive patch count (region mask aligns with the volume; the guard added in `eff9698f` passes).

- [ ] **Step 5: Add the runtime dirs to .gitignore (do not commit multi-GB symlinks / generated masks)**

Append to `.gitignore`:
```
local_data/PHercParis2Fr143_Uregion/
local_data/PHercParis2Fr143_Vregion/
local_data/PHercParis2Fr143/mask_Uregion.png
local_data/PHercParis2Fr143/mask_Vregion.png
```

```bash
git add .gitignore
git commit -m "chore(pseudo): gitignore runtime region fragment dirs"
```

---

## Task 6: Pause loop, back up model, write configs

**Files:**
- Create: `experiments/pseudo_label/cfg_baseline.json`, `cfg_selftrain.json`, `cfg_oracle.json`

- [ ] **Step 1: Pause the loop and free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader
```
Expected: GPU memory drops to near-idle (a few hundred MiB). If `train.py` lingers, kill its PID too. The watchdog will not restart while `.loop_paused` exists.

- [ ] **Step 2: Back up the production model**

```bash
cp best_model.pt best_model.pt.prebkup_pseudolabel
ls -la best_model.pt.prebkup_pseudolabel
```
Expected: a copy exists.

- [ ] **Step 3: Write the baseline config** (`experiments/pseudo_label/cfg_baseline.json`)

Derive from the current production config (`recent_configs.json`'s resenc entry), changing only the data + budget + checkpoint-out. Use these exact values:

```json
{
  "uris": ["local_data/PHercParis2Fr47/surface_volume.zarr"],
  "val_uri": "local_data/PHercParis2Fr143_Vregion/surface_volume.zarr",
  "use_ridges": true, "ridge_sigma": 2.0, "use_lasagna": false,
  "batch_size": 16, "patch_size": 64, "num_layers": 16,
  "lr": 5e-05, "weight_decay": 0.01, "time_budget": 1800, "pinned": false,
  "loss_ink_bce": 0.6, "loss_ink_dice": 0.2, "loss_fiber_bce": 0.2, "loss_st": 0.1,
  "label_smoothing": 0.0, "use_confidence_weight": false,
  "aug_mode": "albumentations", "aug_flip_p": 0.5, "aug_brightness_p": 0.75,
  "aug_affine_p": 0.75, "aug_coarse_dropout_p": 0.5, "aug_rotate_limit": 180,
  "aug_scale_limit": 0.15, "target_fiber_source": "frangi", "target_fiber_sigma": 2.0,
  "architecture": "resenc_unet", "base_feat": 64, "num_blocks": 16, "num_heads": 8,
  "dropout": 0.0, "use_uamt": false, "use_wandb": false,
  "checkpoint_out": "experiments/pseudo_label/baseline_model.pt"
}
```

Note: `checkpoint_out` support is added in Task 2B, so this run writes only to `experiments/pseudo_label/baseline_model.pt` and leaves `best_model.pt`/`history.tsv` untouched.

- [ ] **Step 4: Smoke-test the baseline config (short budget)**

Temporarily set `"time_budget": 60` in a copy and run:
```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/pseudo_label/cfg_baseline.json 2>&1 | tail -30
```
Expected: dataset builds (Fr47 train, Fr143_Vregion val), startup OK, loss prints, and `experiments/pseudo_label/baseline_model.pt` is written. No shape/collate crash. **Critically, verify the production model is untouched:** run `ls -la --time-style=full-iso best_model.pt` before and after — its mtime must not change, and `history.tsv` must not gain a row. If either changed, `checkpoint_out` (Task 2B) is not wired correctly — stop and fix before any long run.

- [ ] **Step 5: Write `cfg_selftrain.json` and `cfg_oracle.json`**

`cfg_selftrain.json` = baseline config with:
```json
  "uris": ["local_data/PHercParis2Fr47/surface_volume.zarr",
           "local_data/PHercParis2Fr143_Uregion/surface_volume.zarr"],
  "use_confidence_weight": true,
  "checkpoint_out": "experiments/pseudo_label/selftrain_model.pt"
```
(The `_Uregion` dir's `inklabels.png` — the pseudo-labels — is written in Task 7 before this run.)

`cfg_oracle.json` = `cfg_selftrain.json` but `use_confidence_weight: false` and the `_Uregion` fragment must resolve to TRUE labels. Achieve this by pointing the oracle at a separate dir `local_data/PHercParis2Fr143_Uregion_true/` (built like Task 5 Step 3 but `cp inklabels.png` as the real `inklabels.png`):
```json
  "uris": ["local_data/PHercParis2Fr47/surface_volume.zarr",
           "local_data/PHercParis2Fr143_Uregion_true/surface_volume.zarr"],
  "use_confidence_weight": false,
  "checkpoint_out": "experiments/pseudo_label/oracle_model.pt"
```

- [ ] **Step 6: Commit the configs**

```bash
git add experiments/pseudo_label/cfg_baseline.json experiments/pseudo_label/cfg_selftrain.json experiments/pseudo_label/cfg_oracle.json
git commit -m "chore(pseudo): baseline/selftrain/oracle run configs"
```

---

## Task 7: Run baseline, generate pseudo-labels, quality report

- [ ] **Step 1: Full baseline run (~30min)**

Set `cfg_baseline.json` `time_budget` back to `1800` and run:
```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/pseudo_label/cfg_baseline.json 2>&1 | tee experiments/pseudo_label/baseline.log | tail -5
```
Expected: completes; `experiments/pseudo_label/baseline_model.pt` written.

- [ ] **Step 2: Measure baseline V-region AUC**

```bash
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py \
  --checkpoint experiments/pseudo_label/baseline_model.pt \
  --fragments local_data/PHercParis2Fr143_Vregion
```
Expected: prints `PHercParis2Fr143_Vregion: AUC mean=0.XX ...`. Record this number (baseline).

- [ ] **Step 3: Generate pseudo-labels for the U-region using the baseline model**

```bash
PYTHONPATH=. .venv/bin/python scripts/generate_pseudo_labels.py \
  --checkpoint experiments/pseudo_label/baseline_model.pt \
  --fragment local_data/PHercParis2Fr143_Uregion \
  --region-mask local_data/PHercParis2Fr143/mask_Uregion.png \
  --out local_data/PHercParis2Fr143_Uregion/inklabels.png \
  --tau-high 0.65 --tau-low 0.15
```
Expected: `wrote ...: ink=0.XX ignore=0.XX`. If it aborts as degenerate, lower `--tau-high`/raise `--tau-low` toward the prob distribution (inspect with a quick histogram) and retry.

- [ ] **Step 4: Pseudo-label quality report (vs known truth)**

```bash
PYTHONPATH=. .venv/bin/python scripts/pseudo_label_quality_report.py \
  --pseudo local_data/PHercParis2Fr143_Uregion/inklabels.png \
  --true local_data/PHercParis2Fr143_Uregion/inklabels_true.png \
  --region-mask local_data/PHercParis2Fr143/mask_Uregion.png
```
Expected: prints `coverage=.. precision=.. recall=.. auc=..`. Record these. This is the honest diagnostic of pseudo-label quality.

- [ ] **Step 5: Build the oracle's true-label U-region dir**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p local_data/PHercParis2Fr143_Uregion_true
ln -sf "$(pwd)/local_data/PHercParis2Fr143/surface_volume.zarr" local_data/PHercParis2Fr143_Uregion_true/surface_volume.zarr
cp local_data/PHercParis2Fr143/inklabels.png local_data/PHercParis2Fr143_Uregion_true/inklabels.png
cp local_data/PHercParis2Fr143/mask_Uregion.png local_data/PHercParis2Fr143_Uregion_true/mask.png
echo "local_data/PHercParis2Fr143_Uregion_true/" >> .gitignore
git add .gitignore && git commit -m "chore(pseudo): gitignore oracle true-label U-region dir"
```

---

## Task 8: Self-train and oracle runs

- [ ] **Step 1: Self-train run (~30min)**

```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/pseudo_label/cfg_selftrain.json 2>&1 | tee experiments/pseudo_label/selftrain.log | tail -5
```
Expected: completes; trains on Fr47 + U-region pseudo-labels (ink loss shows the confidence weighting active); `selftrain_model.pt` written. Watch the `Ink:` loss term is finite.

- [ ] **Step 2: Measure self-train V-region AUC**

```bash
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py \
  --checkpoint experiments/pseudo_label/selftrain_model.pt \
  --fragments local_data/PHercParis2Fr143_Vregion
```
Record the AUC (self-train).

- [ ] **Step 3: Oracle run (~30min)**

```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/pseudo_label/cfg_oracle.json 2>&1 | tee experiments/pseudo_label/oracle.log | tail -5
```
Expected: completes; `oracle_model.pt` written.

- [ ] **Step 4: Measure oracle V-region AUC**

```bash
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py \
  --checkpoint experiments/pseudo_label/oracle_model.pt \
  --fragments local_data/PHercParis2Fr143_Vregion
```
Record the AUC (oracle).

---

## Task 9: Analyze, record, restore loop

- [ ] **Step 1: Assemble the comparison**

Tabulate V-region AUC: baseline → self-train → oracle, plus the pseudo-label quality numbers. Decision:
- self-train ≥ baseline + 0.02 → **win** (same-scroll pseudo-labeling helps).
- self-train ≈ baseline but oracle > baseline → pseudo-labels too noisy at τ (data helps, labels don't).
- oracle ≈ baseline → U-region data adds little; the ceiling is elsewhere (document and stop pursuing this lever).

- [ ] **Step 2: Update FINDINGS.md**

Add a bullet under "What we learned" → "Negative results" (or a new positive bullet if it won), stating the three AUCs, pseudo-label coverage/precision, and the conclusion. Honest framing, no overclaiming (same discipline as the existing clDice/TimeSformer/LeJEPA bullets).

- [ ] **Step 3: Update memory**

Write/replace a memory file `pseudo-label-self-training-result.md` (type project) with the AUCs, the verdict, and the reusable tooling (`spatial_split_mask.py`, `generate_pseudo_labels.py`, `confidence_weight` loss). Add a one-line pointer in `MEMORY.md`. Link `[[cross-scroll-gap-quantified]]`, `[[model-barely-discriminates-ink]]`.

- [ ] **Step 4: Commit docs**

```bash
git add FINDINGS.md
git commit -m "docs(findings): same-scroll pseudo-label self-training result"
git push origin main
```

- [ ] **Step 5: Restore the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 20
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader
ps -eo pid,etime,cmd | grep run_autoresearch_loop | grep -v grep
```
Expected: loop running again, GPU active. `best_model.pt` is the original (never overwritten — all runs wrote to `experiments/pseudo_label/*.pt`). If anything overwrote it, restore from `best_model.pt.prebkup_pseudolabel`.

---

## Self-Review

**Spec coverage:**
- Spatial split (U/V, 128px buffer) → Task 1 + Task 5. ✓
- Fr47-only baseline doubling as pseudo-labeler → Task 6/7. ✓
- Confidence filter (τ_high/τ_low) + ignore honored by loss → Task 2 (loss) + Task 3 (generation). ✓
- Self-train + oracle + comparison on V-region AUC → Tasks 8-9. ✓
- Pseudo-label quality report vs truth → Task 4 + Task 7 Step 4. ✓
- Operational safety (pause loop, backup, restore, never overwrite best_model) → Task 6 + Task 9. ✓
- Prize compliance (disjoint buffer, same scroll, 64px) → built into Task 1/5 geometry. ✓

**Placeholder scan:** No TBD/TODO. The `checkpoint_out` risk (clobbering the production model) is now resolved by a dedicated **Task 2B** rather than an in-step hedge, and verified in Task 6 Step 4 (best_model.pt mtime + history.tsv row must not change). The one remaining empirical check is the `_volume_uri` import in `generate_pseudo_labels.py` (Task 3 Step 3), confirmed in Task 3 Step 4 with an explicit fix instruction.

**Type consistency:** `confidence_weight(target)` returns the per-pixel weight used identically in Task 2's loss and tests; `compute_dice_loss(..., weight=)` signature matches all call sites; `prob_to_pseudo_png` / `score_pseudo` signatures match their tests; the 0/128/255 PNG convention is consistent across generation (Task 3), the loss's 0.5-band weighting (Task 2), and quality scoring (Task 4); `checkpoint_out` is consistently set in all three configs (Task 6) and honored in Task 2B's save branch.

**Loop-safety:** Task 2 (`use_confidence_weight`) and Task 2B (`checkpoint_out`) both default off/None, so the running loop's training and persistence are byte-identical until an experiment config opts in. All experiment checkpoints write to `experiments/pseudo_label/*.pt`; `best_model.pt` is never a save target.
