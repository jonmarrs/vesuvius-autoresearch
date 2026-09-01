"""Per-patch ink-vs-background AUC of a checkpoint on one or more fragment dirs.

A fragment dir holds the CT volume (either `surface_volume.zarr/` or the bare
OME-Zarr `0/` layout) plus `inklabels.png` and `mask.png`. AUC is the honest
ink-discrimination signal (0.5 = chance).

Usage:
    python scripts/measure_ink_auc.py --checkpoint best_model.pt \
        --fragments local_data/PHerc1667Cr1Fr3 [more dirs...] [--device cuda]
"""

import argparse
import os
import sys

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))

from torch.utils.data import DataLoader
from train import ExperimentConfig, load_shape_compatible_state

from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def _volume_uri(frag_dir):
    if os.path.exists(os.path.join(frag_dir, "surface_volume.zarr")):
        return os.path.join(frag_dir, "surface_volume.zarr")
    return os.path.join(frag_dir, "0")  # bare OME-Zarr level 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--fragments", nargs="+", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()

    device = torch.device(args.device)
    chk = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    s = chk.get("config", {})
    arch = s.get("architecture", "resenc_unet")
    ps, nl = s.get("patch_size", 64), s.get("num_layers", 16)
    config = ExperimentConfig.load("config.json")
    model = build_inference_model(
        architecture=arch,
        patch_size=ps,
        num_layers=nl,
        base_feat=s.get("base_feat", 64),
        num_blocks=s.get("num_blocks", 16),
        num_heads=s.get("num_heads", 8),
        dropout=s.get("dropout", 0.0),
        use_ridges=s.get("use_ridges", config.use_ridges),
        multi_task_heads=s.get("multi_task_heads", False),
    ).to(device)
    load_shape_compatible_state(model, chk["model_state_dict"], args.checkpoint)
    model.eval()
    print(f"ckpt={args.checkpoint} arch={arch} use_ridges={s.get('use_ridges')}")

    for frag in args.fragments:
        uri = _volume_uri(frag)
        ds = VesuviusLabeledDataset(
            uri,
            os.path.join(frag, "inklabels.png"),
            os.path.join(frag, "mask.png"),
            ps,
            nl + 8,
            seed=7,
            cache_dir=config.cache_dir,
            use_ridges=s.get("use_ridges", config.use_ridges),
            ridge_sigma=getattr(config, "ridge_sigma", 2.0),
            use_lasagna=False,
            require_ink=True,
        )
        dl = iter(DataLoader(ds, batch_size=8, num_workers=0))
        aucs = []
        with torch.no_grad():
            while len(aucs) < args.n:
                try:
                    x_raw, target, _ = next(dl)
                except StopIteration:
                    break
                x = x_raw[:, :, 4 : 4 + nl].to(device)
                if target is None or target.numel() == 0:
                    continue
                target = target.to(device)
                if target.dim() == 3:
                    target = target.unsqueeze(1)
                if torch.sum(target.float()) < 1.0:
                    continue
                out = model(x)
                if isinstance(out, tuple):
                    out = out[0]
                prob = torch.sigmoid(out).float().cpu().numpy()
                tgt = (target.cpu().numpy() > 0.5).astype(int)
                for bi in range(prob.shape[0]):
                    p, t = prob[bi].ravel(), tgt[bi].ravel()
                    if t.min() != t.max():
                        aucs.append(roc_auc_score(t, p))
        a = np.array(aucs)
        name = os.path.basename(frag.rstrip("/"))
        if len(a):
            print(
                f"{name}: AUC mean={a.mean():.3f} median={np.median(a):.3f} n={len(a)}"
            )
        else:
            print(f"{name}: no usable patches")


if __name__ == "__main__":
    main()
