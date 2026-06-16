"""Same-regime control: can the production training regime (full-fragment
mini-batch sampling, no augmentation, lr 5e-5) fit a *synthetic learnable*
target? Trains a fresh resenc on full Fr47 with the brightness target
(CT z-mean > patch mean) and logs train pixel AUC over steps.

Disambiguates the augmentation-ablation finding ("fresh training can't fit even
train at 64px") between signal-weakness and the optimization regime:
- fits brightness but ink doesn't  -> 64px ink signal is too weak (window-limited)
- can't fit brightness either       -> the regime (LR/schedule) is the lever
See docs/superpowers/specs/2026-06-14-augmentation-ablation-design.md follow-up.
"""

import argparse
import os
import sys

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))

from scripts.overfit_probe import _dice_loss, brightness_control_target  # noqa: E402
from scripts.pixel_auc import pooled_pixel_auc  # noqa: E402


def _auc(out, target):
    prob = torch.sigmoid(out).detach().cpu().numpy()
    tgt = (target.detach().cpu().numpy() > 0.5).astype(int)
    probs = [prob[i].ravel() for i in range(prob.shape[0])]
    labels = [tgt[i].ravel() for i in range(tgt.shape[0])]
    return pooled_pixel_auc(probs, labels)


def main():
    from measure_ink_auc import _volume_uri

    from vesuvius_autoresearch.core.model_wrappers import build_inference_model
    from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

    ap = argparse.ArgumentParser()
    ap.add_argument("--frag", default="local_data/PHercParis2Fr47")
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--num-layers", type=int, default=16)
    ap.add_argument("--patch-size", type=int, default=64)
    ap.add_argument("--eval-every", type=int, default=250)
    ap.add_argument(
        "--out-csv", default="experiments/aug_ablation/control_brightness.csv"
    )
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    dev = torch.device(args.device)
    nl, ps = args.num_layers, args.patch_size

    model = build_inference_model(
        architecture="resenc_unet",
        patch_size=ps,
        num_layers=nl,
        base_feat=64,
        num_blocks=16,
        num_heads=8,
        dropout=0.0,
        use_ridges=True,
        multi_task_heads=False,
    ).to(dev)

    ds = VesuviusLabeledDataset(
        _volume_uri(args.frag),
        os.path.join(args.frag, "inklabels.png"),
        os.path.join(args.frag, "mask.png"),
        ps,
        nl + 8,
        seed=7,
        cache_dir=None,
        use_ridges=True,
        ridge_sigma=2.0,
        use_lasagna=False,
        require_ink=False,
        jitter=True,
    )
    dl = DataLoader(
        ds, batch_size=args.batch, shuffle=True, num_workers=0, drop_last=True
    )

    # Fixed eval batch (first batch, no jitter would be ideal but DataLoader reuse is fine):
    eval_x, _, _ = next(
        iter(DataLoader(ds, batch_size=64, shuffle=False, num_workers=0))
    )
    eval_x = eval_x[:, :, 4 : 4 + nl].to(dev)
    eval_target = brightness_control_target(eval_x)

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    it = iter(dl)
    curve = []
    model.train()
    for step in range(args.steps + 1):
        try:
            x_raw, _, _ = next(it)
        except StopIteration:
            it = iter(dl)
            x_raw, _, _ = next(it)
        x = x_raw[:, :, 4 : 4 + nl].to(dev)
        target = brightness_control_target(x)
        out = model(x)
        out = out[0] if isinstance(out, tuple) else out
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            out, target
        ) + _dice_loss(out, target)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % args.eval_every == 0:
            model.eval()
            with torch.no_grad():
                eo = model(eval_x)
                eo = eo[0] if isinstance(eo, tuple) else eo
                a = _auc(eo, eval_target)
            model.train()
            curve.append((step, a))
            print(f"  step={step} train_brightness_auc={a:.4f} loss={loss.item():.4f}")

    os.makedirs(os.path.dirname(args.out_csv), exist_ok=True)
    import csv

    with open(args.out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "brightness_auc"])
        w.writerows(curve)
    final = curve[-1][1]
    verdict = (
        "REGIME CAN FIT (ink signal is the weak link)"
        if final >= 0.9
        else "REGIME CANNOT FIT (LR/schedule is the lever)"
    )
    print(f"FINAL brightness_auc={final:.4f} -> {verdict}")


if __name__ == "__main__":
    main()
