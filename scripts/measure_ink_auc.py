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

from vesuvius_autoresearch.core.checkpoint_tools import (
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
    validate_targets,
)
from vesuvius_autoresearch.core.inference import positive_integer
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
    ap.add_argument("--cache-dir")
    args = ap.parse_args()
    positive_integer(args.n, "n")

    device = torch.device(args.device)
    model, settings, _ = load_tool_checkpoint(args.checkpoint, device)
    ps, nl = settings["patch_size"], settings["num_layers"]
    failures = []
    for frag in args.fragments:
        try:
            measure_fragment(model, settings, frag, args.n, device, args.cache_dir)
        except (ValueError, RuntimeError, OSError) as exc:
            failures.append(f"{frag}: {exc}")
            print(f"{frag}: FAILED: {exc}", file=sys.stderr)
    if failures:
        raise SystemExit(1)


def measure_fragment(model, settings, frag, n, device, cache_dir=None):
    ps, nl = settings["patch_size"], settings["num_layers"]
    for name in ("inklabels.png", "mask.png"):
        if not os.path.isfile(os.path.join(frag, name)):
            raise ValueError(f"required measurement file missing: {name}")
    uri = _volume_uri(frag)
    ds = VesuviusLabeledDataset(
        uri,
        os.path.join(frag, "inklabels.png"),
        os.path.join(frag, "mask.png"),
        ps,
        nl + 8,
        seed=7,
        cache_dir=cache_dir,
        use_ridges=settings["use_ridges"],
        ridge_sigma=settings["ridge_sigma"],
        use_lasagna=False,
        require_ink=True,
        jitter=False,
        strict_reads=True,
    )
    if (
        ds.labels is None
        or ds.mask is None
        or ds.labels.shape != ds.shape[1:]
        or ds.mask.shape != ds.shape[1:]
        or not np.isfinite(ds.labels).all()
        or not np.isfinite(ds.mask).all()
        or not np.isin(ds.labels, [0, 1]).all()
    ):
        raise ValueError(
            "measurement requires aligned binary ink labels and a finite mask"
        )
    dl = iter(DataLoader(ds, batch_size=8, num_workers=0))
    offset = 0
    aucs = []
    with torch.no_grad():
        while len(aucs) < n:
            try:
                x_raw, target, _ = next(dl)
            except StopIteration:
                break
            x = validate_batch(x_raw, settings, buffered=True).to(device)
            prob = ink_probabilities(model, x).cpu()
            target = validate_targets(target, prob)
            for bi in range(len(prob)):
                y, x0 = ds.valid_coords[offset + bi]
                if not (0 <= y <= ds.shape[1] - ps and 0 <= x0 <= ds.shape[2] - ps):
                    raise ValueError("patch coordinates exceed the volume")
                mask = ds.mask[y : y + ps, x0 : x0 + ps] > 0.5
                p = prob[bi, 0].numpy()[mask]
                t = (target[bi, 0].numpy()[mask] > 0.5).astype(int)
                if t.size and t.min() != t.max():
                    aucs.append(float(roc_auc_score(t, p)))
                    if len(aucs) == n:
                        break
            offset += len(prob)
    a = np.array(aucs)
    name = os.path.basename(frag.rstrip("/"))
    if 0 < len(a) < n:
        raise ValueError(
            f"only {len(a)}/{n} requested patches have both classes inside the mask"
        )
    if len(a):
        print(f"{name}: AUC mean={a.mean():.3f} median={np.median(a):.3f} n={len(a)}")
    else:
        raise ValueError(
            "no usable patches with both ink and background inside the mask"
        )


if __name__ == "__main__":
    main()
