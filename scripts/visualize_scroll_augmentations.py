#!/usr/bin/env python3
"""Phase 1 of #201 work: visually validate the scroll-specific augmentations.

Loads ink-containing patches from PHercParis2Fr47, applies each scroll
augmentation in isolation with reproducible RNG, and saves a PNG grid for
direct visual comparison against the issue's reference images:
  https://github.com/ScrollPrize/villa/issues/201

This is a *diagnostic* — it does not modify the augmentations themselves
(those live in the scroll_augmentations.py library). Output goes to
reports/augmentation_demos/.

Usage:
    uv run python scripts/visualize_scroll_augmentations.py
    uv run python scripts/visualize_scroll_augmentations.py --out reports/augmentation_demos/all_families.png --n-patches 3
"""

import argparse
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import numpy as np
import torch

from train import ExperimentConfig
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset

TRAIN_URI = "local_data/PHercParis2Fr47/surface_volume.zarr"
TRAIN_LABELS = "local_data/PHercParis2Fr47/inklabels.png"
TRAIN_MASK = "local_data/PHercParis2Fr47/mask.png"


def _resolve_augs(source: str):
    """Return (apply_fn, aug_names) for all nine scroll augmentation families.

    Both legacy source values ('train', 'new') now resolve to the single
    scroll_augmentations.py library that train.py also uses (post-unification).
    """
    from scroll_augmentations import apply_scroll_specific_3d_augmentations as fn

    return fn, [
        "decohesion",
        "warping",
        "squeeze",
        "z_dropout",
        "intensity_drift",
        "sheet_compression",
        "thick_slice",
        "rician_noise",
        "blank_rectangles",
    ]


def _config_with_only(name: str, aug_names) -> ExperimentConfig:
    """Build a config where ONE scroll aug fires with p=1.0 and the rest are off."""
    cfg = ExperimentConfig()
    for n in aug_names:
        setattr(cfg, f"aug_scroll_{n}_p", 0.0)
    setattr(cfg, f"aug_scroll_{name}_p", 1.0)
    return cfg


def _slice(volume_4d: torch.Tensor, axis: str) -> np.ndarray:
    """volume_4d is [C, Z, H, W]; return a 2D numpy slice for imshow."""
    v = volume_4d.detach().cpu().float().numpy()[0]  # take CT channel -> [Z, H, W]
    Z, H, W = v.shape
    if axis == "z":
        return v[Z // 2]  # [H, W]  — mid-axial slice
    if axis == "y":
        return v[
            :, H // 2, :
        ]  # [Z, W]  — mid-coronal-ish slice (shows z-axis behaviour)
    raise ValueError(f"unknown axis {axis!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=None,
        help="Output PNG path (default reports/scroll_aug_visual_<source>.png).",
    )
    parser.add_argument(
        "--source",
        default="new",
        choices=["train", "new"],
        help="Use train.py's existing augs ('train') or scroll_augmentations.py ('new').",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--n-patches",
        type=int,
        default=3,
        help="Number of ink-containing patches to visualize.",
    )
    args = parser.parse_args()

    if not os.path.exists(TRAIN_URI):
        print(f"error: {TRAIN_URI} not found", file=sys.stderr)
        return 1

    apply_fn, AUG_NAMES = _resolve_augs(args.source)
    if args.out is None:
        args.out = "reports/augmentation_demos/all_families.png"

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    ds = VesuviusLabeledDataset(
        TRAIN_URI,
        TRAIN_LABELS,
        TRAIN_MASK if os.path.exists(TRAIN_MASK) else None,
        patch_size=64,
        num_layers=24,
        seed=args.seed,
        use_ridges=False,
        require_ink=True,
    )

    # Evenly-spaced patches across the require_ink coord pool.
    N = args.n_patches
    indices = [(i + 1) * len(ds) // (N + 1) for i in range(N)]
    print(f"# source={args.source}  dataset={len(ds)} ink patches  sampling={indices}")

    # Grid: rows = N patches x 2 views (mid-z, mid-y); columns = original + each aug.
    n_rows = N * 2
    n_cols = 1 + len(AUG_NAMES)
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(n_cols * 2.2, n_rows * 2.2), squeeze=False
    )

    for pi, idx in enumerate(indices):
        patch, label, _fiber = ds[idx]  # patch is [C=1, Z=24, H=64, W=64]
        # Build a batch-of-1 in the shape apply_scroll_specific_3d_augmentations expects:
        # x: [B, C, Z, H, W], target_ink: [B, 1, H, W], target_fiber: [B, 1, 1, H, W]
        x = patch.unsqueeze(0)
        target_ink = label.unsqueeze(0).unsqueeze(0).float()
        target_fiber = torch.zeros((1, 1, 1, patch.shape[-2], patch.shape[-1]))

        # Column 0: original
        for axi, ax_name in enumerate(["z", "y"]):
            row = pi * 2 + axi
            ax = axes[row, 0]
            img = _slice(x[0], ax_name)
            vmax = float(img.max()) if img.max() > 0 else 1.0
            ax.imshow(img, cmap="gray", vmin=0, vmax=vmax, interpolation="nearest")
            if axi == 0:
                ax.set_title(f"patch idx={idx}\noriginal", fontsize=8)
            ax.set_ylabel(f"mid-{ax_name}", fontsize=7)
            ax.set_xticks([])
            ax.set_yticks([])

        # Columns 1..N: each augmentation in isolation, seeded for reproducibility.
        for ci, name in enumerate(AUG_NAMES, start=1):
            cfg = _config_with_only(name, AUG_NAMES)
            # Seed per (patch, aug) so multiple runs of this script are stable
            # AND each aug gets independent randomness across patches.
            torch.manual_seed(args.seed * 1000 + pi * 10 + ci)
            xa, _, _ = apply_fn(
                x.clone(), target_ink.clone(), target_fiber.clone(), cfg
            )
            for axi, ax_name in enumerate(["z", "y"]):
                row = pi * 2 + axi
                ax = axes[row, ci]
                img = _slice(xa[0], ax_name)
                vmax = float(img.max()) if img.max() > 0 else 1.0
                ax.imshow(img, cmap="gray", vmin=0, vmax=vmax, interpolation="nearest")
                if axi == 0:
                    ax.set_title(name, fontsize=8)
                ax.set_xticks([])
                ax.set_yticks([])

    fig.suptitle(
        f"Scroll-specific augmentations on real PHercParis2Fr47 ink-containing patches (source={args.source})\n"
        f"Rows: each patch shown twice — mid-z (axial) then mid-y (coronal/z-stack) slice\n"
        f"Columns: original, {', '.join(AUG_NAMES)}",
        fontsize=9,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"# wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
