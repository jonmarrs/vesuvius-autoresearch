# Overfit / Feasibility Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone overfit probe that classifies the detector's flat ~0.52 pixel-AUC ceiling as capacity / optimization / signal-absent / pipeline-bug, by trying to memorize a tiny fixed batch.

**Architecture:** One focused `scripts/overfit_probe.py` reusing the production model (`build_inference_model`), dataset (`VesuviusLabeledDataset`), and `pooled_pixel_auc`. It builds ONE fixed batch (no dataloader sampling, no augmentation), runs a plain Adam loop on just that batch, and logs train pixel AUC over steps. A `--target real|brightness` flag switches between real ink (Probe 1) and a synthetic learnable control (Probe 2). The overfit loop is self-contained (inlined dice) so it tests fast without importing the heavy `train` module.

**Tech Stack:** Python, PyTorch, NumPy, scikit-learn, pytest. Reuses `scripts/pixel_auc.py`, `vesuvius_autoresearch.core.model_wrappers.build_inference_model`, `VesuviusLabeledDataset`.

**Spec:** `docs/superpowers/specs/2026-06-14-overfit-probe-design.md`

---

## File Structure

- `scripts/overfit_probe.py` (create) — `brightness_control_target`, `overfit`, `build_fixed_batch`, `main`.
- `tests/test_overfit_probe.py` (create) — unit tests for `brightness_control_target` and `overfit` (synthetic separable smoke).
- `experiments/overfit_probe/*.csv` (runtime, gitignored).
- `FINDINGS.md`, memory (modify) — record the classification.

Note: `build_fixed_batch` and `main` do GPU + scroll-data I/O and are validated by the actual probe run (Task 4), not unit tests. The two unit-tested functions (`brightness_control_target`, `overfit`) carry the testable logic.

---

## Task 1: Control-target function (TDD)

**Files:**
- Create: `scripts/overfit_probe.py` (first function only)
- Test: `tests/test_overfit_probe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_overfit_probe.py
import torch

from scripts.overfit_probe import brightness_control_target


def test_brightness_control_target_thresholds_zmean_vs_patch_mean():
    # One patch [K=1, C=1, nl=2, H=2, W=2]. z-mean per pixel, threshold at patch mean.
    x = torch.zeros(1, 1, 2, 2, 2)
    # pixel (0,0): z-mean 0.9 (high), others 0.1 (low) -> patch mean = (0.9+0.1+0.1+0.1)/4 = 0.3
    x[0, 0, :, 0, 0] = 0.9
    x[0, 0, :, 0, 1] = 0.1
    x[0, 0, :, 1, 0] = 0.1
    x[0, 0, :, 1, 1] = 0.1
    t = brightness_control_target(x)
    assert t.shape == (1, 1, 2, 2)
    assert t[0, 0, 0, 0] == 1.0  # 0.9 > 0.3
    assert t[0, 0, 0, 1] == 0.0 and t[0, 0, 1, 0] == 0.0 and t[0, 0, 1, 1] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch && PYTHONPATH=. .venv/bin/python -m pytest tests/test_overfit_probe.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.overfit_probe'`

- [ ] **Step 3: Create `scripts/overfit_probe.py` with the function**

```python
"""Overfit / feasibility probe: can a fresh model memorize a tiny fixed batch?
Classifies the detector's ~0.52 pixel-AUC ceiling as capacity / optimization /
signal-absent / pipeline-bug. Standalone diagnostic — does not touch train.py,
best_model.pt, or the loop. See docs/superpowers/specs/2026-06-14-overfit-probe-design.md
"""

import argparse
import os
import sys

import numpy as np
import torch
import torch.nn.functional as F

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))


def brightness_control_target(x):
    """Synthetic, definitely-learnable per-pixel target from the CT input itself:
    CT channel (0) averaged over z, thresholded at each patch's own mean. Returns
    [K, 1, H, W] float. Used as the Probe 2 control."""
    ct = x[:, 0]  # [K, nl, H, W]
    zmean = ct.mean(dim=1)  # [K, H, W]
    pmean = zmean.mean(dim=(1, 2), keepdim=True)  # [K, 1, 1]
    return (zmean > pmean).float().unsqueeze(1)  # [K, 1, H, W]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_overfit_probe.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/overfit_probe.py tests/test_overfit_probe.py
git commit -m "feat(probe): brightness control target for overfit probe"
```
(ruff-format may reformat+abort the first commit; re-add and re-run if so.)

---

## Task 2: Overfit loop (TDD)

**Files:**
- Modify: `scripts/overfit_probe.py` (add `overfit`)
- Test: `tests/test_overfit_probe.py` (add a synthetic-separable smoke test)

The loop is self-contained (inlined dice, no `train` import) so the test stays fast. This test proves the optimization wiring (loss → backward → step → AUC climbs) is correct *independent of scroll data* — so if the real probe stalls, we know it is the data/model, not the loop.

- [ ] **Step 1: Add the failing test**

```python
# append to tests/test_overfit_probe.py
from torch import nn

from scripts.overfit_probe import overfit


class _TinyNet(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.conv = nn.Conv3d(c, 1, 1)

    def forward(self, x):  # [K,C,nl,H,W] -> [K,1,H,W]
        return self.conv(x).mean(dim=2)


def test_overfit_drives_separable_target_auc_high():
    torch.manual_seed(0)
    K, C, nl, H, W = 2, 1, 4, 8, 8
    x = torch.rand(K, C, nl, H, W)
    target = (x[:, 0].mean(dim=1, keepdim=True) > 0.5).float()  # [K,1,H,W], learnable
    model = _TinyNet(C)
    curve = overfit(model, x, target, steps=500, lr=3e-2, log_every=100)
    # curve: list of (step, pooled_auc, per_patch_auc); final pooled AUC near 1
    assert curve[-1][0] == 500
    assert curve[-1][1] > 0.9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_overfit_probe.py::test_overfit_drives_separable_target_auc_high -v`
Expected: FAIL with `ImportError: cannot import name 'overfit'`

- [ ] **Step 3: Add `overfit` to `scripts/overfit_probe.py`**

Insert after `brightness_control_target`:

```python
def _dice_loss(logits, target, smooth=1e-5):
    """Minimal soft-Dice (inlined to keep this probe standalone and fast — avoids
    importing the heavy train module just for compute_dice_loss)."""
    p = torch.sigmoid(logits)
    inter = (p * target).sum(dim=(-2, -1))
    union = p.sum(dim=(-2, -1)) + target.sum(dim=(-2, -1))
    return (1.0 - (2.0 * inter + smooth) / (union + smooth)).mean()


def overfit(model, x, target, steps=2000, lr=1e-3, log_every=100):
    """Train `model` on the single fixed batch (x, target) for `steps` Adam steps
    (BCE + Dice on the ink logits). Returns a list of (step, pooled_pixel_auc,
    per_patch_auc) sampled every `log_every` steps. No validation, no augmentation."""
    from sklearn.metrics import roc_auc_score

    from scripts.pixel_auc import pooled_pixel_auc

    model.train()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    curve = []
    for step in range(steps + 1):
        out = model(x)
        out = out[0] if isinstance(out, tuple) else out
        loss = F.binary_cross_entropy_with_logits(out, target) + _dice_loss(out, target)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % log_every == 0:
            with torch.no_grad():
                prob = torch.sigmoid(out).detach().cpu().numpy()
                tgt = (target.detach().cpu().numpy() > 0.5).astype(int)
                probs = [prob[i].ravel() for i in range(prob.shape[0])]
                labels = [tgt[i].ravel() for i in range(tgt.shape[0])]
                pooled = pooled_pixel_auc(probs, labels)
                pp = [
                    roc_auc_score(labels[i], probs[i])
                    for i in range(len(labels))
                    if labels[i].min() != labels[i].max()
                ]
                ppm = float(np.mean(pp)) if pp else 0.5
                curve.append((step, pooled, ppm))
                print(f"  step={step} pooled_auc={pooled:.4f} per_patch_auc={ppm:.4f} loss={loss.item():.4f}")
    return curve
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_overfit_probe.py -v`
Expected: PASS (2 passed). If the separable AUC doesn't reach 0.9 in 500 steps, bump the test to `steps=800` (the wiring is what's under test, not the exact step count).

- [ ] **Step 5: Commit**

```bash
git add scripts/overfit_probe.py tests/test_overfit_probe.py
git commit -m "feat(probe): self-contained overfit loop with pixel-AUC curve"
```

---

## Task 3: Fixed-batch builder + CLI

**Files:**
- Modify: `scripts/overfit_probe.py` (add `build_fixed_batch` and `main`)

No unit test (GPU + scroll I/O); validated by the Task 4 run.

- [ ] **Step 1: Add `build_fixed_batch` and `main`**

Append to `scripts/overfit_probe.py`:

```python
def build_fixed_batch(frag_dir, k, num_layers, patch_size, use_ridges, device, seed=7):
    """Load the first `k` ink-containing patches of `frag_dir` into ONE fixed
    batch (jitter=False, no augmentation). Returns (x [K,C,nl,H,W], ink [K,1,H,W])."""
    from measure_ink_auc import _volume_uri

    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ds = VesuviusLabeledDataset(
        _volume_uri(frag_dir),
        os.path.join(frag_dir, "inklabels.png"),
        os.path.join(frag_dir, "mask.png"),
        patch_size,
        num_layers + 8,
        seed=seed,
        cache_dir=None,
        use_ridges=use_ridges,
        ridge_sigma=2.0,
        use_lasagna=False,
        require_ink=True,
        jitter=False,
    )
    xs, ys = [], []
    for i in range(min(k, len(ds))):
        x_raw, t, _ = ds[i]
        xs.append(x_raw[:, 4 : 4 + num_layers])
        ys.append(t.unsqueeze(0) if t.dim() == 2 else t)
    x = torch.stack(xs).to(device)
    ink = torch.stack(ys).to(device).float()
    return x, ink


def main():
    from vesuvius_autoresearch.core.model_wrappers import build_inference_model

    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["real", "brightness"], default="real")
    ap.add_argument("--frag", default="local_data/PHercParis2Fr47")
    ap.add_argument("--k", type=int, default=16)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--num-layers", type=int, default=16)
    ap.add_argument("--patch-size", type=int, default=64)
    ap.add_argument("--out-csv", default="experiments/overfit_probe/probe.csv")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    device = torch.device(args.device)
    model = build_inference_model(
        architecture="resenc_unet",
        patch_size=args.patch_size,
        num_layers=args.num_layers,
        base_feat=64,
        num_blocks=16,
        num_heads=8,
        dropout=0.0,
        use_ridges=True,
        multi_task_heads=False,
    ).to(device)

    x, ink = build_fixed_batch(
        args.frag, args.k, args.num_layers, args.patch_size, True, device
    )
    target = ink if args.target == "real" else brightness_control_target(x)
    print(
        f"probe target={args.target} batch={tuple(x.shape)} "
        f"target_ink_frac={float((target > 0.5).float().mean()):.3f}"
    )

    curve = overfit(model, x, target, steps=args.steps, lr=args.lr, log_every=100)

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    import csv

    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "pooled_auc", "per_patch_auc"])
        w.writerows(curve)
    final = curve[-1][1]
    verdict = "CAN overfit (>=0.9)" if final >= 0.9 else "STALLS (<0.9)"
    print(f"FINAL pooled_auc={final:.4f} -> {verdict}  (csv: {args.out_csv})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the module imports cleanly**

Run: `PYTHONPATH=. .venv/bin/python -c "import scripts.overfit_probe as m; print('ok', hasattr(m,'build_fixed_batch'), hasattr(m,'main'))"`
Expected: `ok True True`

- [ ] **Step 3: Re-run the unit tests (no regression)**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_overfit_probe.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add scripts/overfit_probe.py
git commit -m "feat(probe): fixed-batch builder + overfit CLI"
```

---

## Task 4: Run the probe ladder, classify, record

- [ ] **Step 1: Pause the loop, gitignore artifacts**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 6
nvidia-smi --query-gpu=memory.used --format=csv,noheader
printf '\n# Overfit probe artifacts\nexperiments/overfit_probe/*.csv\n' >> .gitignore
git add .gitignore && git commit -m "chore(probe): gitignore overfit probe artifacts"
```
Expected: GPU near-idle.

- [ ] **Step 2: Probe 1 — overfit REAL ink (~minutes)**

```bash
PYTHONPATH=. .venv/bin/python scripts/overfit_probe.py --target real \
  --frag local_data/PHercParis2Fr47 --k 16 --steps 2000 --lr 1e-3 \
  --out-csv experiments/overfit_probe/real.csv 2>&1 | tail -25
```
Record the `FINAL pooled_auc` and the trajectory. **Read:** `>=0.9` → architecture *can* fit (capacity fine); the full-data ceiling is optimization/augmentation → STOP, classification is "optimization". `<0.9` (stalls) → continue to Probe 2.

- [ ] **Step 3: Probe 2 — control target (ONLY if Probe 1 stalled)**

```bash
PYTHONPATH=. .venv/bin/python scripts/overfit_probe.py --target brightness \
  --frag local_data/PHercParis2Fr47 --k 16 --steps 2000 --lr 1e-3 \
  --out-csv experiments/overfit_probe/control.csv 2>&1 | tail -25
```
**Read:** control `>=0.9` but real `<0.9` → "signal-absent at 64px". control `<0.9` too → "pipeline/loss bug".

- [ ] **Step 4: Classify per the decision table**

| Probe 1 (real) | Probe 2 (control) | Classification | Implied next lever |
| --- | --- | --- | --- |
| ≥ ~0.9 | — | optimization / augmentation | de-augment / objective / LR — not bigger model |
| stalls | ≥ ~0.9 | signal-absent at 64px | no architecture helps; window-feasibility writeup |
| stalls | stalls | pipeline / loss bug | debug the training path |

- [ ] **Step 5: Update FINDINGS.md + memory**

Add a FINDINGS bullet: Probe 0 (train pixel AUC 0.58), Probe 1 final AUC, Probe 2 (if run) final AUC, the classification, and the implied lever. Write a memory file `overfit-probe-result.md` (type project) with the same + link `[[long-schedule-test-result]]`, `[[model-barely-discriminates-ink]]`; add a one-line `MEMORY.md` pointer.

```bash
git add FINDINGS.md
git commit -m "docs(findings): overfit probe classifies the detection ceiling"
git push origin main
```

- [ ] **Step 6: Restore the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 20
ps -eo pid,etime,cmd | grep run_autoresearch_loop | grep -v grep
```
Expected: loop running. `best_model.pt` was never touched (probe uses fresh models only).

---

## Self-Review

**Spec coverage:**
- Probe 1 overfit real ink (16 fixed Fr47 patches, no aug, fresh model, BCE+Dice, Adam 1e-3, 2000 steps, train pixel AUC curve) → Tasks 1-3 + Task 4 Step 2. ✓
- Probe 2 control target (CT z-mean vs patch mean) → Task 1 + Task 4 Step 3. ✓
- `build_fixed_batch` / `brightness_control_target` / `overfit` / `main(--target)` → Tasks 1-3. ✓
- Decision table classification → Task 4 Step 4. ✓
- TDD on `brightness_control_target` + `overfit` (synthetic) → Tasks 1-2. ✓
- Operational safety (loop paused, fresh models, best_model untouched, read-only data) → Task 4. ✓

**Placeholder scan:** None. The one deliberate deviation from the spec — inlining `_dice_loss` instead of importing `compute_dice_loss` — is justified inline (keeps the probe standalone and the unit test fast, avoiding the heavy `train` import); behavior matches `compute_dice_loss`'s formula.

**Type consistency:** `overfit(model, x, target, steps, lr, log_every)` returns `list[(step, pooled_auc, per_patch_auc)]`, consumed consistently in the test (`curve[-1][1]`) and `main` (`curve[-1][1]`, `w.writerows(curve)`); `brightness_control_target(x)->[K,1,H,W]` matches `ink`'s shape so both feed `overfit` identically; model output `[K,1,H,W]` matches `target` `[K,1,H,W]` for BCE/Dice; `pooled_pixel_auc(prob_arrays, label_arrays)` call matches its definition.
